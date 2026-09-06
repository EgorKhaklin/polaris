-- ============================================================================
-- 2026-09-06-001-bulk-enrollment.down.sql
--
-- Revert of 2026-09-06-001 (v9.247 / P2.4). Drops the bulk staging + batch
-- tables and the procedure. Issued tokens are untouched (they are real
-- IdentityToken rows); only the staging scaffolding goes.
-- ============================================================================
DROP PROCEDURE IF EXISTS uc_bulk_issue(INTEGER, INTEGER);
DROP TABLE IF EXISTS BulkEnrollmentStaging CASCADE;
DROP TABLE IF EXISTS BulkEnrollmentBatch CASCADE;
