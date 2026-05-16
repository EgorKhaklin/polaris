-- ============================================================================
-- 2026-05-15-001-pheromone-rotation.up.sql
--
-- Wave 3 implementation of v9.06 Sanctum 2026-05-15-pheromone-rotation.md
-- Position A: mirror v8.84+v8.87 audit-log archive+purge framework for the
-- Pheromone table. Same constitutional carve-out shape; same operator
-- workflow; G32+G33 added (parallel to G30+G31).
--
-- What this migration ships:
--   1. LifecyclePheromoneCheckpoint table — strictly append-only AoR
--      for archive+purge cycles. NO GUC carve-out at the checkpoint
--      layer (G32 parallel to G30).
--   2. reject_pheromone_modification() trigger function — replaces the
--      generic reject_audit_modification() on Pheromone. Uses its OWN
--      GUC `polaris.pheromone_purge_in_progress` so audit-log carve-
--      out (polaris.purge_in_progress) does NOT cross-contaminate.
--   3. reject_pheromone_checkpoint_modification() trigger function —
--      strictly append-only on the new checkpoint table.
--   4. uc_pheromone_archive_purge() procedure — the SINGLE sanctioned
--      DELETE path on Pheromone. Validates cutoff + SHA-256 + admin
--      role + sets LOCAL GUC + DELETEs in same txn + INSERTs
--      checkpoint.
--   5. trg_pheromone_append_only retargeted to the new function.
--
-- After this migration:
--   - DELETE from Pheromone (raw) → REJECTED (insufficient_privilege)
--   - UPDATE on Pheromone (raw) → REJECTED (insufficient_privilege)
--   - DELETE from LifecyclePheromoneCheckpoint → REJECTED
--   - UPDATE on LifecyclePheromoneCheckpoint → REJECTED
--   - CALL uc_pheromone_archive_purge(cutoff, uri, sha256, actor)
--     within an open BEGIN..COMMIT → opens carve-out, DELETEs old rows,
--     INSERTs checkpoint, closes carve-out (SET LOCAL evaporates at COMMIT).
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 1. LifecyclePheromoneCheckpoint table
-- ----------------------------------------------------------------------------
CREATE TABLE LifecyclePheromoneCheckpoint (
    checkpoint_id      BIGSERIAL PRIMARY KEY,
    purged_at          TIMESTAMPTZ  NOT NULL DEFAULT now(),
    cutoff_timestamp   TIMESTAMPTZ  NOT NULL,
    archive_uri        VARCHAR(512) NOT NULL,
    archive_sha256     VARCHAR(64)  NOT NULL,
    actor_user_id      INTEGER      NOT NULL,
    rows_purged        INTEGER      NOT NULL DEFAULT 0,

    CONSTRAINT pheromone_archive_sha256_is_hex CHECK (
        archive_sha256 ~ '^[0-9a-fA-F]{64}$'
    ),
    CONSTRAINT pheromone_cutoff_in_past CHECK (
        cutoff_timestamp <= now()
    ),
    CONSTRAINT pheromone_rows_purged_nonneg CHECK (
        rows_purged >= 0
    )
);

COMMENT ON TABLE LifecyclePheromoneCheckpoint IS
    'Audit-of-record for Pheromone archive+purge cycles (v9.07 / D5-impl, '
    'parallel to v8.87 LifecycleArchiveCheckpoint). Strictly append-only — '
    'NO GUC carve-out at the checkpoint layer (G32 parallel to G30). '
    'Constitutional carve-out for the Pheromone table itself: '
    'sanctum/2026-05-15-pheromone-rotation.md (Position A).';

CREATE INDEX idx_pheromone_checkpoint_purged_at_desc
    ON LifecyclePheromoneCheckpoint (purged_at DESC);

-- ----------------------------------------------------------------------------
-- 2. reject_pheromone_modification() — Pheromone table append-only with
--    GUC-keyed DELETE carve-out. Uses its OWN GUC; does NOT share with
--    the audit-log carve-out (polaris.purge_in_progress).
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION reject_pheromone_modification()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    v_purge_in_progress TEXT;
BEGIN
    -- v9.07 / D5-impl constitutional carve-out (Position A, DECIDED in
    -- sanctum/2026-05-15-pheromone-rotation.md):
    --   Applies ONLY to DELETE (TG_OP = 'DELETE'). UPDATE still rejects.
    --   The GUC is `polaris.pheromone_purge_in_progress`. SET LOCAL means
    --   it evaporates at the transaction boundary; cannot leak.
    --   Distinct from the v8.87 audit-log GUC `polaris.purge_in_progress`
    --   so the two carve-out paths cannot cross-contaminate.
    IF TG_OP = 'DELETE' THEN
        v_purge_in_progress :=
            current_setting('polaris.pheromone_purge_in_progress', true);
        IF v_purge_in_progress = 'TRUE' THEN
            RETURN OLD;
        END IF;
    END IF;

    RAISE EXCEPTION
        'Pheromone is append-only (Arc E / E1 / v8.62; carve-out via '
        'uc_pheromone_archive_purge). Operation % rejected.', TG_OP
    USING ERRCODE = 'insufficient_privilege';
END;
$$;

COMMENT ON FUNCTION reject_pheromone_modification IS
    'Pheromone table append-only trigger function with v9.07 GUC-keyed '
    'DELETE carve-out for uc_pheromone_archive_purge. UPDATE always '
    'rejects. DELETE rejects unless polaris.pheromone_purge_in_progress '
    'is set to TRUE in the current transaction.';

-- ----------------------------------------------------------------------------
-- 3. reject_pheromone_checkpoint_modification() — strictly append-only
--    on the checkpoint table. NO carve-out (G32 parallel to G30 — once
--    a checkpoint is written, it cannot be rewritten or deleted).
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION reject_pheromone_checkpoint_modification()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    RAISE EXCEPTION
        'LifecyclePheromoneCheckpoint is strictly append-only (G32 / v9.07). '
        'Operation % rejected.', TG_OP
    USING ERRCODE = 'insufficient_privilege';
END;
$$;

COMMENT ON FUNCTION reject_pheromone_checkpoint_modification IS
    'Checkpoint table strictly append-only — no GUC carve-out at this '
    'layer. The non-repudiation chain over Pheromone purges depends on '
    'this. G32 parallel to G30.';

-- ----------------------------------------------------------------------------
-- 4. Retarget the existing Pheromone trigger to the new function.
--    Pre-v9.07 it pointed at the generic reject_audit_modification()
--    which (via the v8.87 carve-out) would have honored
--    polaris.purge_in_progress — meaning the audit-log purge GUC could
--    accidentally allow Pheromone DELETEs. v9.07 fixes that.
-- ----------------------------------------------------------------------------
DROP TRIGGER IF EXISTS trg_pheromone_append_only ON Pheromone;
CREATE TRIGGER trg_pheromone_append_only
    BEFORE UPDATE OR DELETE ON Pheromone
    FOR EACH ROW EXECUTE FUNCTION reject_pheromone_modification();

-- Checkpoint trigger
DROP TRIGGER IF EXISTS trg_pheromone_checkpoint_append_only
    ON LifecyclePheromoneCheckpoint;
CREATE TRIGGER trg_pheromone_checkpoint_append_only
    BEFORE UPDATE OR DELETE ON LifecyclePheromoneCheckpoint
    FOR EACH ROW EXECUTE FUNCTION reject_pheromone_checkpoint_modification();

-- ----------------------------------------------------------------------------
-- 5. uc_pheromone_archive_purge() — the SINGLE sanctioned DELETE path
--    on Pheromone (G33 parallel to G31).
--
-- Operator workflow:
--   1. Run polaris-pheromone-archive.sh which exports old rows to a
--      manifest-hashed tarball (returns SHA-256).
--   2. Run polaris-pheromone-purge.sh --cutoff <ts> --archive-uri <uri>
--      --archive-sha256 <hex> --actor-user-id <id> which calls this
--      procedure inside a transaction.
--
-- This procedure does NOT verify the archive itself — that's the
-- script's job. It validates that the cutoff is in the past + SHA-256
-- is well-formed hex + actor exists + has admin role; sets the carve-
-- out GUC; DELETEs Pheromone rows older than cutoff; counts; INSERTs
-- the checkpoint. SET LOCAL means the GUC evaporates at COMMIT.
-- ----------------------------------------------------------------------------
CREATE OR REPLACE PROCEDURE uc_pheromone_archive_purge(
    p_cutoff_timestamp TIMESTAMPTZ,
    p_archive_uri      VARCHAR(512),
    p_archive_sha256   VARCHAR(64),
    p_actor_user_id    INTEGER
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_actor_role     VARCHAR(50);
    v_rows_purged    INTEGER;
BEGIN
    -- Validate cutoff
    IF p_cutoff_timestamp > now() THEN
        RAISE EXCEPTION
            'cutoff_timestamp must be in the past (got %)',
            p_cutoff_timestamp
        USING ERRCODE = 'invalid_parameter_value';
    END IF;

    -- Validate SHA-256 shape
    IF p_archive_sha256 !~ '^[0-9a-fA-F]{64}$' THEN
        RAISE EXCEPTION
            'archive_sha256 must be 64 hex chars (got %)',
            p_archive_sha256
        USING ERRCODE = 'invalid_parameter_value';
    END IF;

    -- Validate actor exists + has admin role
    SELECT role INTO v_actor_role
      FROM AppUser
     WHERE user_id = p_actor_user_id;
    IF v_actor_role IS NULL THEN
        RAISE EXCEPTION
            'actor_user_id % does not exist in AppUser', p_actor_user_id
        USING ERRCODE = 'invalid_parameter_value';
    END IF;
    IF v_actor_role <> 'admin' THEN
        RAISE EXCEPTION
            'actor_user_id % has role %; admin required for purge',
            p_actor_user_id, v_actor_role
        USING ERRCODE = 'insufficient_privilege';
    END IF;

    -- Open the carve-out (txn-scoped)
    PERFORM set_config('polaris.pheromone_purge_in_progress', 'TRUE', true);

    -- Execute the purge
    DELETE FROM Pheromone
     WHERE deposited_at < p_cutoff_timestamp;
    GET DIAGNOSTICS v_rows_purged = ROW_COUNT;

    -- Write checkpoint
    INSERT INTO LifecyclePheromoneCheckpoint (
        cutoff_timestamp, archive_uri, archive_sha256,
        actor_user_id, rows_purged
    ) VALUES (
        p_cutoff_timestamp, p_archive_uri, p_archive_sha256,
        p_actor_user_id, v_rows_purged
    );

    -- Note: SET LOCAL evaporates at COMMIT. The carve-out is closed
    -- automatically; subsequent raw DELETEs (in this OR any other
    -- transaction) will be rejected by trg_pheromone_append_only.
END;
$$;

COMMENT ON PROCEDURE uc_pheromone_archive_purge IS
    'Wave 3 / D5-impl — the single sanctioned Pheromone DELETE path '
    '(G33 parallel to G31 — uc_archive_purge for the audit-log). '
    'Validates cutoff + SHA-256 hex + admin role; opens GUC carve-out; '
    'DELETEs old Pheromone rows; writes checkpoint; SET LOCAL evaporates '
    'at COMMIT. Constitutional carve-out: sanctum/2026-05-15-pheromone-rotation.md.';
