-- ============================================================================
-- 2026-09-05-002-per-class-purge-cutoffs.up.sql
--
-- v9.235 / roadmap P1.11 (retention and lifecycle engine), ship 2: the
-- per-class retention schedule reaches the purge.
--
-- THE GAP: v9.234 made retention a per-class decision, but uc_archive_purge
-- still took one cutoff for all four classes. Under MINIMIZED, verification
-- history older than two years is purgeable while the token lifecycle is held
-- for five, and a single cutoff can express only one of those. The five-year
-- purge left two years of verification history the schedule said could go, and
-- a two-year purge was refused outright. Half the engine was unusable.
--
-- ADDS: LifecycleArchiveCheckpoint.cutoff_source, .jurisdiction, and the four
-- per-class cutoffs. The checkpoint is the audit of record for the deletion
-- carve-out, so it must say what the cutoff actually was for each class, not
-- one scalar that no longer describes the purge. Existing rows take
-- cutoff_source='FLAG' and NULL per-class cutoffs, which is accurate: policy
-- mode did not exist and cutoff_timestamp was the whole story.
-- CHANGES: uc_archive_purge gains p_class_cutoffs. NULL (the default) is
-- v9.234's behavior exactly, including the refusal. Supplied, it purges each
-- class at the cutoff the archive's manifest records for it, each still
-- checked against that class's retention window.
--
-- The canonical copies live in 01_schema.sql / 05_procedures.sql (a fresh
-- build and --sync-objects install them); this migration brings a deployed
-- database to the same shape. REVERSIBLE: the .down.sql drops the columns and
-- restores the six-parameter procedure. ADDITIVE: yes. No row is rewritten.
-- ============================================================================

ALTER TABLE LifecycleArchiveCheckpoint
    ADD COLUMN IF NOT EXISTS cutoff_source       VARCHAR(6) NOT NULL DEFAULT 'FLAG',
    ADD COLUMN IF NOT EXISTS jurisdiction        VARCHAR(10),
    ADD COLUMN IF NOT EXISTS cutoff_lifecycle    TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS cutoff_verification TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS cutoff_enrollment   TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS cutoff_authaudit    TIMESTAMPTZ;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'cutoff_source_known') THEN
        ALTER TABLE LifecycleArchiveCheckpoint
            ADD CONSTRAINT cutoff_source_known CHECK (cutoff_source IN ('FLAG', 'POLICY'));
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'per_class_cutoffs_in_past') THEN
        ALTER TABLE LifecycleArchiveCheckpoint
            ADD CONSTRAINT per_class_cutoffs_in_past CHECK (
                (cutoff_lifecycle    IS NULL OR cutoff_lifecycle    <= now()) AND
                (cutoff_verification IS NULL OR cutoff_verification <= now()) AND
                (cutoff_enrollment   IS NULL OR cutoff_enrollment   <= now()) AND
                (cutoff_authaudit    IS NULL OR cutoff_authaudit    <= now())
            );
    END IF;
END $$;

-- The procedure body is canonical in 05_procedures.sql; --sync-objects
-- installs it. The drop below removes the v9.234 signature so the new
-- parameter does not produce an overload.
DROP PROCEDURE IF EXISTS uc_archive_purge(
    timestamptz, varchar, varchar, integer, varchar, bigint);

-- ----------------------------------------------------------------------------
-- Verification: the columns exist and the source is constrained.
-- ----------------------------------------------------------------------------
DO $$
DECLARE v_cols INTEGER;
BEGIN
    SELECT count(*) INTO v_cols
      FROM information_schema.columns
     WHERE table_name = 'lifecyclearchivecheckpoint'
       AND column_name IN ('cutoff_source', 'jurisdiction', 'cutoff_lifecycle',
                           'cutoff_verification', 'cutoff_enrollment', 'cutoff_authaudit');
    IF v_cols <> 6 THEN
        RAISE EXCEPTION 'migration self-check failed: % of 6 checkpoint columns present', v_cols;
    END IF;

    BEGIN
        INSERT INTO LifecycleArchiveCheckpoint
            (cutoff_timestamp, archive_uri, archive_sha256, actor_user_id, cutoff_source)
        VALUES (now() - interval '1 day', 'file:///migration-self-check',
                repeat('0', 64), 1, 'GUESS');
        RAISE EXCEPTION 'migration self-check failed: an unknown cutoff_source was accepted';
    EXCEPTION WHEN check_violation THEN
        NULL;   -- expected
    END;

    RAISE NOTICE 'per-class purge cutoffs: six columns present, cutoff_source constrained.';
END $$;
