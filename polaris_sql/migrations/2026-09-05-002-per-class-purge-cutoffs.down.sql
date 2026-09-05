-- ============================================================================
-- 2026-09-05-002-per-class-purge-cutoffs.down.sql
--
-- Reverses the v9.235 per-class purge cutoffs. Drops the six checkpoint
-- columns and the two constraints, and drops the seven-parameter procedure so
-- that re-applying 05_procedures.sql from a v9.234 tree leaves no overload.
--
-- What is lost: the record of which cutoff applied to which class on purges
-- run while this migration was in force. The scalar cutoff_timestamp and every
-- row count survive, so the non-repudiation chain stays intact; only the
-- per-class detail goes.
-- ============================================================================

DROP PROCEDURE IF EXISTS uc_archive_purge(
    timestamptz, varchar, varchar, integer, varchar, timestamptz[], bigint);

ALTER TABLE LifecycleArchiveCheckpoint
    DROP CONSTRAINT IF EXISTS cutoff_source_known,
    DROP CONSTRAINT IF EXISTS per_class_cutoffs_in_past;

ALTER TABLE LifecycleArchiveCheckpoint
    DROP COLUMN IF EXISTS cutoff_source,
    DROP COLUMN IF EXISTS jurisdiction,
    DROP COLUMN IF EXISTS cutoff_lifecycle,
    DROP COLUMN IF EXISTS cutoff_verification,
    DROP COLUMN IF EXISTS cutoff_enrollment,
    DROP COLUMN IF EXISTS cutoff_authaudit;
