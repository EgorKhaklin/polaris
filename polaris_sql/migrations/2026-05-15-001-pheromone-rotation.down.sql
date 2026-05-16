-- ============================================================================
-- 2026-05-15-001-pheromone-rotation.down.sql
--
-- Reverse the Wave 3 / D5-impl Pheromone rotation framework.
-- Refuses to apply if any LifecyclePheromoneCheckpoint rows exist (the
-- non-repudiation chain would be broken).
--
-- Restores the pre-v9.07 state: Pheromone trigger points back at the
-- generic reject_audit_modification function; new table + new functions
-- + new procedure dropped.
--
-- WARNING: this migration is non-trivial to reverse-of-reverse. If
-- LifecyclePheromoneCheckpoint contains any rows, the down migration
-- would orphan them. Refuses by design.
-- ============================================================================

DO $$
DECLARE
    v_checkpoint_count INTEGER;
BEGIN
    SELECT count(*) INTO v_checkpoint_count
      FROM LifecyclePheromoneCheckpoint;
    IF v_checkpoint_count > 0 THEN
        RAISE EXCEPTION
            'Cannot down-migrate: LifecyclePheromoneCheckpoint has % '
            'row(s). The non-repudiation chain over Pheromone purges '
            'would be broken. Manual operator intervention required.',
            v_checkpoint_count
        USING ERRCODE = 'insufficient_privilege';
    END IF;
END;
$$;

-- Restore pre-v9.07 trigger
DROP TRIGGER IF EXISTS trg_pheromone_append_only ON Pheromone;
CREATE TRIGGER trg_pheromone_append_only
    BEFORE UPDATE OR DELETE ON Pheromone
    FOR EACH ROW EXECUTE FUNCTION reject_audit_modification();

-- Drop new objects
DROP TRIGGER IF EXISTS trg_pheromone_checkpoint_append_only
    ON LifecyclePheromoneCheckpoint;
DROP PROCEDURE IF EXISTS uc_pheromone_archive_purge(
    TIMESTAMPTZ, VARCHAR, VARCHAR, INTEGER
);
DROP FUNCTION IF EXISTS reject_pheromone_modification();
DROP FUNCTION IF EXISTS reject_pheromone_checkpoint_modification();
DROP TABLE IF EXISTS LifecyclePheromoneCheckpoint;
