-- ============================================================================
-- 2026-05-15-003-audit-access-log.up.sql
--
-- v9.20 / item 6 of the architecture-study joint recommendation.
-- Per Sanctum sanctum/2026-05-15-verification-purpose-and-audit-access.md
-- Position A.
--
-- Adds AuditAccessLog — the meta-audit table that records WHO QUERIED
-- the audit tables (TokenLifecycleEvent / VerificationEvent / AuthAuditLog).
-- Anti-coercion-direct: makes silent surveillance by insiders visible.
-- Insiders querying audit logs without legitimate purpose is a class
-- of attack; logging the meta-access creates accountability for the
-- watchers (the audit's audit).
--
-- Constitutional contract (per Sanctum §IV.2):
--   - AuditAccessLog itself is append-only (existing audit-table pattern)
--   - Reads of AuditAccessLog are NOT logged (the regress stops there)
--   - actor_user_id FK to AppUser; system reads (no logged-in user)
--     allowed via NULL with a sourced operator-tag in filter_criteria_jsonb
--   - accessed_table is a CHECK-bounded enum of the three audit tables
-- ============================================================================

CREATE TABLE AuditAccessLog (
    access_id           BIGSERIAL    PRIMARY KEY,
    accessed_at         TIMESTAMPTZ  NOT NULL DEFAULT now(),
    actor_user_id       INTEGER          REFERENCES AppUser(user_id),
                        -- NULLABLE: NULL = system access (cron, CLI tools);
                        -- actor identity captured in filter_criteria_jsonb
    accessed_table      VARCHAR(40)  NOT NULL,
    filter_criteria_jsonb JSONB      NOT NULL DEFAULT '{}'::jsonb,
                        -- e.g., {"token_id": 42, "limit": 100} or
                        -- {"actor_source": "ai-hydra.sh"} for system access
    result_row_count    INTEGER          NULL,
                        -- the actual row count returned (NULL if not
                        -- measurable; the helper records when available)

    CONSTRAINT chk_accessed_table CHECK (
        accessed_table IN ('TokenLifecycleEvent', 'VerificationEvent',
                           'AuthAuditLog', 'DuressEvent')
    ),
    CONSTRAINT chk_row_count_nonneg CHECK (
        result_row_count IS NULL OR result_row_count >= 0
    )
);

COMMENT ON TABLE AuditAccessLog IS
    'v9.20 / meta-audit table per Sanctum 2026-05-15-verification-purpose-'
    'and-audit-access.md. Records WHO queried the audit tables. '
    'Strictly append-only (no GUC carve-out at this layer; no insert via '
    'archive-purge; no UPDATE; no DELETE). Reads of AuditAccessLog '
    'itself are NOT logged here (the regress stops by construction; '
    'enforced as a structural invariant). Anti-coercion-direct: makes '
    'silent surveillance by insiders visible.';

-- Indexes for the two most-likely query shapes:
--   1. "who accessed audit X in last 24h" → (accessed_table, accessed_at)
--   2. "what did user N access ever" → (actor_user_id, accessed_at)
CREATE INDEX idx_audit_access_table_time
    ON AuditAccessLog (accessed_table, accessed_at DESC);

CREATE INDEX idx_audit_access_actor_time
    ON AuditAccessLog (actor_user_id, accessed_at DESC)
    WHERE actor_user_id IS NOT NULL;

-- Append-only enforcement: reuse the existing reject_audit_modification
-- pattern (consistent with other audit tables — TLE, VE, AAL). The
-- trigger function already raises insufficient_privilege on UPDATE/DELETE.
-- We just attach it to the new table.
DROP TRIGGER IF EXISTS trg_audit_access_append_only ON AuditAccessLog;
CREATE TRIGGER trg_audit_access_append_only
    BEFORE UPDATE OR DELETE ON AuditAccessLog
    FOR EACH ROW EXECUTE FUNCTION reject_audit_modification();

-- ============================================================================
-- Smoke (idempotent; runs at migration apply time only)
-- ============================================================================
DO $audit_access_smoke$
DECLARE
    v_table_exists BOOLEAN;
    v_trigger_exists BOOLEAN;
BEGIN
    SELECT EXISTS (
        SELECT 1 FROM information_schema.tables
         WHERE table_name = 'auditaccesslog'
    ) INTO v_table_exists;
    IF NOT v_table_exists THEN
        RAISE EXCEPTION '2026-05-15-003-audit-access-log: table not created';
    END IF;

    SELECT EXISTS (
        SELECT 1 FROM information_schema.triggers
         WHERE trigger_name = 'trg_audit_access_append_only'
    ) INTO v_trigger_exists;
    IF NOT v_trigger_exists THEN
        RAISE EXCEPTION '2026-05-15-003-audit-access-log: append-only trigger missing';
    END IF;

    -- Verify the append-only trigger actually rejects DELETE.
    -- Insert a probe row, attempt DELETE, expect insufficient_privilege.
    INSERT INTO AuditAccessLog (accessed_table, filter_criteria_jsonb,
                                result_row_count)
    VALUES ('VerificationEvent', '{"test": "smoke"}'::jsonb, 0);

    BEGIN
        DELETE FROM AuditAccessLog
         WHERE filter_criteria_jsonb @> '{"test": "smoke"}';
        RAISE EXCEPTION 'append-only smoke: DELETE was not rejected';
    EXCEPTION WHEN insufficient_privilege THEN
        -- Expected. Clean up the probe row via a TRUNCATE-equivalent we
        -- cannot use (also append-only); leave the row in place as
        -- audit-of-record (the probe row is itself a meta-audit record).
        NULL;
    END;

    RAISE NOTICE '2026-05-15-003-audit-access-log: table + indexes + append-only trigger + smoke OK';
END;
$audit_access_smoke$;
