-- ============================================================================
-- 2026-05-15-003-audit-access-log.down.sql
--
-- Revert: drop the append-only trigger, drop the indexes, drop the
-- table. This irrecoverably loses any meta-audit history. The
-- Architect's caution: down-migrating an audit table destroys
-- accountability data. Operator should consider whether this revert
-- is actually what they want — most schema rollbacks are scoped to
-- pre-deployment validation; rolling back AuditAccessLog after it
-- has been live is a constitutional weight matter.
-- ============================================================================

DROP TRIGGER IF EXISTS trg_audit_access_append_only ON AuditAccessLog;
DROP INDEX IF EXISTS idx_audit_access_table_time;
DROP INDEX IF EXISTS idx_audit_access_actor_time;
DROP TABLE IF EXISTS AuditAccessLog;
