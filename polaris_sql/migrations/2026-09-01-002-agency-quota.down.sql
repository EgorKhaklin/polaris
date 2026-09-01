-- ============================================================================
-- 2026-09-01-002-agency-quota.down.sql
--
-- Revert of 2026-09-01-002-agency-quota.up.sql (v9.190 / P1.8). Removes the
-- three quota triggers, the function, the two window indexes, and the
-- AgencyQuota table. Any caps an operator had set are discarded (they are
-- policy rows, not audit-of-record); every agency is unlimited afterwards.
-- ============================================================================

DROP TRIGGER IF EXISTS trg_quota_issue  ON IdentityToken;
DROP TRIGGER IF EXISTS trg_quota_revoke ON IdentityToken;
DROP TRIGGER IF EXISTS trg_quota_verify ON VerificationEvent;
DROP FUNCTION IF EXISTS enforce_agency_quota();
DROP INDEX IF EXISTS idx_token_agency_issued;
DROP INDEX IF EXISTS idx_verification_agency_time;
DROP TABLE IF EXISTS AgencyQuota;
