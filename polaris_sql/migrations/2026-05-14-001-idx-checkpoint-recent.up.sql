-- ============================================================================
-- 2026-05-14-001-idx-checkpoint-recent.up.sql
--
-- First migration shipped under the v8.95 framework (Position C of
-- a recorded decision).
--
-- ADD: index on LifecycleArchiveCheckpoint(purged_at DESC).
--
-- WHY:
--   LifecycleArchiveCheckpoint (added v8.87, Arc B Phase 2b) currently has
--   only the BIGSERIAL PRIMARY KEY on checkpoint_id. The natural operator
--   query — "show me recent purges" / "what was the cutoff of the last
--   purge?" — orders by purged_at DESC. Without an index, the planner
--   sequentially scans the table and sorts in memory. The table is small
--   today (≤ ~one row per purge cycle), but it is append-only and grows
--   monotonically, so this index pays off forever and costs effectively
--   nothing now.
--
-- SHAPE:
--   B-tree DESC index. The DESC direction makes "ORDER BY purged_at DESC
--   LIMIT N" able to terminate after the first N entries instead of
--   reading the whole table.
--
-- REVERSIBLE: yes (DROP INDEX in the .down.sql).
-- ADDITIVE:   yes (creates only; no data change).
-- LOCK:       brief ACCESS EXCLUSIVE on LifecycleArchiveCheckpoint while
--             the index is built; table is small so this is sub-second.
--             Not run with CREATE INDEX CONCURRENTLY because the runner
--             wraps each migration in a single transaction (Sanctum §III).
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_checkpoint_purged_at_desc
    ON LifecycleArchiveCheckpoint (purged_at DESC);

COMMENT ON INDEX idx_checkpoint_purged_at_desc IS
    'Recent-purge lookup: ORDER BY purged_at DESC LIMIT N terminates early. '
    'Added by migration 2026-05-14-001 (first migration under v8.95 framework).';
