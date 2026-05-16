-- ============================================================================
-- 2026-05-14-003-recovery-code-hash.down.sql
--
-- Revert of 2026-05-14-003-recovery-code-hash.up.sql.
--
-- DROPs the AppUser.recovery_code_hash column.
--
-- DATA-LOSS WARNING:
--   Any operator-bound recovery codes are LOST on revert. The
--   bound codes can be re-bound after a re-apply by re-running
--   polaris-generate-recovery-code.sh --bind-to <username> for
--   each affected operator (the operator must use the same printed
--   mnemonic — if they no longer have it, they must generate a
--   new one and re-print).
--
-- This .down.sql does NOT preserve the bound codes; that would
-- require an out-of-band export step that operators may legitimately
-- want to skip. If the operator is reverting because they want to
-- abandon the recovery-code flow entirely, the column drop is
-- intentional + correct. If they're reverting to fix a different
-- problem and want to preserve codes, the operator should pg_dump
-- the AppUser table BEFORE running --down 1, then restore the
-- recovery_code_hash column values after re-applying.
--
-- This .down.sql does NOT refuse based on whether any operators
-- have bound codes. The migration column itself is operator-data
-- (not append-only audit), so the data-loss is the operator's
-- choice; we don't gate it the way we gate AuthAuditLog purges.
-- ============================================================================

ALTER TABLE AppUser
    DROP CONSTRAINT IF EXISTS chk_recovery_code_hash_format;

ALTER TABLE AppUser
    DROP COLUMN IF EXISTS recovery_code_hash;
