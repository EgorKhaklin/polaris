-- ============================================================================
-- 2026-09-05-001-retention-policy.down.sql
--
-- Revert of 2026-09-05-001-retention-policy.up.sql (v9.234 / P1.11). Removes
-- the retention engine: the immutability trigger and its function, the two
-- resolver functions, the template procedure, the partial unique index, and
-- the RetentionPolicy table with every policy row an operator recorded.
--
-- This file DROPS uc_archive_purge rather than restoring it. Reverting leaves
-- the database with no purge procedure until 05_procedures.sql is re-applied
-- from the previous release (`polaris-migrate.sh --sync-objects` against that
-- checkout), which installs the pre-P1.11 form. The drop is what makes that
-- re-apply clean: the retention-aware signature and the older one cannot
-- coexist, and an overload would make which one runs a matter of argument
-- inference. The up.sql's header says "restores", which is the effect of the
-- two steps together, not of this file alone.
--
-- What reverting COSTS: after this, uc_archive_purge accepts any cutoff in the
-- past again, including one inside what was the retention window. The floor
-- was the point of the migration.
-- ============================================================================

DROP TRIGGER IF EXISTS trg_retention_policy_immutable ON RetentionPolicy;
DROP FUNCTION IF EXISTS enforce_retention_policy_immutability();
DROP PROCEDURE IF EXISTS uc_apply_retention_template(varchar, varchar, integer);
DROP PROCEDURE IF EXISTS uc_archive_purge(timestamptz, varchar, varchar, integer, varchar, bigint);
DROP FUNCTION IF EXISTS retention_cutoff(varchar, varchar);
DROP FUNCTION IF EXISTS retention_days_for(varchar, varchar);
DROP INDEX IF EXISTS uq_effective_retention_policy;
DROP TABLE IF EXISTS RetentionPolicy;
