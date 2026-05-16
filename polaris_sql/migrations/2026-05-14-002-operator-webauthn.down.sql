-- ============================================================================
-- 2026-05-14-002-operator-webauthn.down.sql
--
-- Revert of 2026-05-14-002-operator-webauthn.up.sql.
--
-- DROPs the OperatorWebauthnCredential table, DROPs the
-- AppUser.webauthn_required_after column, restores the pre-v8.97
-- AuthAuditLog.chk_authaudit_event_type CHECK enum.
--
-- IRREVERSIBILITY CAVEAT:
--   Any AuthAuditLog rows already written with one of the five WebAuthn
--   event types (WEBAUTHN_REGISTERED / WEBAUTHN_ASSERTED /
--   WEBAUTHN_ASSERTION_FAILED / WEBAUTHN_DEREGISTERED /
--   EMERGENCY_PASSWORD_LOGIN_AUTHORIZED) would fail the restored CHECK.
--   Per Sanctum §IV.3 (append-only audit) we cannot DELETE them; per
--   Sanctum §V (this CHECK swap is reversible) we DO need the restored
--   constraint to hold.
--
--   Resolution: this .down.sql intentionally REFUSES to drop the new
--   event types from the enum if any row uses them. The operator must
--   either:
--     (a) accept that revert is now blocked until those rows age out of
--         the hot tables via archive+purge (v8.87 cycle), OR
--     (b) manually run polaris-archive.sh + uc_archive_purge for the
--         affected rows BEFORE running --down 1
--
--   The transactional shape: this .down.sql wraps in BEGIN..COMMIT via
--   the runner, so the assertion-fail rolls back the table+column
--   DROPs as well. The result is a clean refusal: no half-revert.
--
-- ADDITIVE (data side): yes — no existing data mutated (the table is
-- dropped wholesale, the column is dropped wholesale).
-- LOCK: brief ACCESS EXCLUSIVE on AppUser + AuthAuditLog.
-- ============================================================================

-- (1) Refusal check: assert no WebAuthn audit rows exist.
DO $$
DECLARE
    webauthn_row_count INTEGER;
BEGIN
    SELECT count(*) INTO webauthn_row_count
    FROM AuthAuditLog
    WHERE event_type IN (
        'WEBAUTHN_REGISTERED', 'WEBAUTHN_ASSERTED',
        'WEBAUTHN_ASSERTION_FAILED', 'WEBAUTHN_DEREGISTERED',
        'EMERGENCY_PASSWORD_LOGIN_AUTHORIZED'
    );

    IF webauthn_row_count > 0 THEN
        RAISE EXCEPTION
            'Revert refused: AuthAuditLog has % WebAuthn-class rows that '
            'would fail the restored CHECK constraint. Per Sanctum '
            '§IV.3 (append-only audit) these rows cannot be deleted; '
            'archive+purge them via polaris-archive.sh + uc_archive_purge '
            'first, then re-run --down 1.',
            webauthn_row_count
            USING ERRCODE = 'check_violation';
    END IF;
END $$;

-- (2) Restore the pre-v8.97 CHECK constraint on AuthAuditLog.event_type.
ALTER TABLE AuthAuditLog
    DROP CONSTRAINT chk_authaudit_event_type;

ALTER TABLE AuthAuditLog
    ADD CONSTRAINT chk_authaudit_event_type
        CHECK (event_type IN (
            'LOGIN_SUCCESS', 'LOGIN_FAILED', 'LOGIN_LOCKED',
            'LOGOUT',
            'PASSWORD_CHANGED', 'ACCOUNT_CREATED', 'ACCOUNT_DEACTIVATED',
            'CSRF_REJECTED', 'AUTH_REQUIRED', 'AUTHZ_DENIED',
            'RATE_LIMITED'
        ));

-- (3) Drop the AppUser.webauthn_required_after column.
ALTER TABLE AppUser
    DROP COLUMN webauthn_required_after;

-- (4) Drop the OperatorWebauthnCredential table.
DROP TABLE OperatorWebauthnCredential;
