-- ============================================================================
-- 2026-09-01-001-operator-session.down.sql
--
-- Revert of 2026-09-01-001-operator-session.up.sql (v9.189 / P1.7).
--
-- Restores the v8.97 AuthAuditLog.chk_authaudit_event_type list and removes
-- the OperatorSession registry. Removing the registry logs every operator
-- out (the app treats a cookie without a registry row as anonymous), which
-- is the correct effect of reverting a session control.
--
-- IRREVERSIBILITY CAVEAT (same shape as the v8.97 revert): AuthAuditLog rows
-- written with one of the five v9.189 event types would fail the restored
-- CHECK. They are append-only (C1) and cannot be deleted here, so this
-- revert REFUSES while any exist; archive+purge them first
-- (polaris-archive.sh + uc_archive_purge), then re-run --down 1. The
-- runner wraps this file in a transaction, so the refusal is clean.
-- ============================================================================

-- (1) Refusal check: no v9.189-class audit rows may exist.
DO $$
DECLARE
    v9189_row_count INTEGER;
BEGIN
    SELECT count(*) INTO v9189_row_count
    FROM AuthAuditLog
    WHERE event_type IN (
        'NETWORK_POLICY_DENIED', 'SESSION_EVICTED', 'SESSION_EXPIRED',
        'SESSION_REVOKED', 'WEBAUTHN_REGISTRATION_REFUSED'
    );

    IF v9189_row_count > 0 THEN
        RAISE EXCEPTION
            'Revert refused: AuthAuditLog has % v9.189 session/origin rows '
            'that would fail the restored CHECK constraint. They are '
            'append-only (C1); archive+purge them via polaris-archive.sh + '
            'uc_archive_purge first, then re-run --down 1.',
            v9189_row_count
            USING ERRCODE = 'check_violation';
    END IF;
END $$;

-- (2) Restore the v8.97 CHECK (16 values).
ALTER TABLE AuthAuditLog
    DROP CONSTRAINT chk_authaudit_event_type;

ALTER TABLE AuthAuditLog
    ADD CONSTRAINT chk_authaudit_event_type
        CHECK (event_type IN (
            'LOGIN_SUCCESS', 'LOGIN_FAILED', 'LOGIN_LOCKED',
            'LOGOUT',
            'PASSWORD_CHANGED', 'ACCOUNT_CREATED', 'ACCOUNT_DEACTIVATED',
            'CSRF_REJECTED', 'AUTH_REQUIRED', 'AUTHZ_DENIED',
            'RATE_LIMITED',
            'WEBAUTHN_REGISTERED',
            'WEBAUTHN_ASSERTED',
            'WEBAUTHN_ASSERTION_FAILED',
            'WEBAUTHN_DEREGISTERED',
            'EMERGENCY_PASSWORD_LOGIN_AUTHORIZED'
        ));

-- (3) Remove the session registry.
DROP TABLE IF EXISTS OperatorSession;
