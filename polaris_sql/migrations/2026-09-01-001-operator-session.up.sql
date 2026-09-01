-- ============================================================================
-- 2026-09-01-001-operator-session.up.sql
--
-- v9.189 / roadmap P1.7 (session and origin hardening).
--
-- ADDS (1): OperatorSession, the server-side registry of operator web
-- sessions. Until v9.189 a Polaris session existed only as a signed cookie:
-- the server could not count, expire, or revoke one, and a deactivated
-- account kept its live session until the cookie aged out. Every login now
-- writes a row here and every authenticated request consults it, so a
-- session can be capped per role (the least-recently-seen seat is evicted),
-- idled out, ended when the account is deactivated or the client's address
-- leaves the role's network policy, and revoked by an operator. Rows are
-- working state (updated in place, purged after 30 days), NOT audit-of-
-- record: every eviction, expiry, and policy denial is written to
-- AuthAuditLog, which stays append-only.
--
-- REPLACES (2): AuthAuditLog.chk_authaudit_event_type, extending the
-- event_type CHECK with the five v9.189 session/origin events:
--   NETWORK_POLICY_DENIED, SESSION_EVICTED, SESSION_EXPIRED,
--   SESSION_REVOKED, WEBAUTHN_REGISTRATION_REFUSED
--
-- REVERSIBLE: yes. The .down.sql restores the v8.97 CHECK (refusing while
-- rows carry the new event types, same procedure as the v8.97 revert) and
-- removes the registry table.
-- ADDITIVE (data side): yes. LOCK: brief ACCESS EXCLUSIVE on AuthAuditLog
-- for the constraint swap; the new table is independent. Idempotent: the
-- table and indexes use IF NOT EXISTS and the CHECK swap installs a strict
-- superset, so --sync-objects re-application is safe.
-- ============================================================================

-- (1) The session registry.
--
-- session_id is 32 random bytes as hex, minted by security.register_session
-- and carried in the signed cookie; the cookie alone no longer authenticates.
-- client_ip is the address the session was established from (X-Forwarded-For
-- honoured only behind POLARIS_TRUST_PROXY, as for AuthAuditLog.ip_address).
CREATE TABLE IF NOT EXISTS OperatorSession (
    session_id      VARCHAR(64)   PRIMARY KEY,
    -- ON DELETE NO ACTION (the schema-wide default): operators are
    -- deactivated, never deleted, and a live registry row must not vanish
    -- silently under a cookie.
    user_id         INTEGER       NOT NULL
                        REFERENCES AppUser(user_id) ON DELETE NO ACTION,
    role            VARCHAR(20)   NOT NULL,
    client_ip       VARCHAR(45),
    created_at      TIMESTAMPTZ   NOT NULL DEFAULT now(),
    last_seen_at    TIMESTAMPTZ   NOT NULL DEFAULT now(),
    revoked_at      TIMESTAMPTZ,
    revoke_reason   VARCHAR(20),

    CONSTRAINT chk_opsession_id_format
        CHECK (session_id ~ '^[0-9a-f]{64}$'),
    CONSTRAINT chk_opsession_role
        CHECK (role IN ('admin', 'operator', 'auditor')),
    CONSTRAINT chk_opsession_revoke_reason
        CHECK (revoke_reason IS NULL OR revoke_reason IN
               ('logout', 'evicted', 'idle', 'deactivated',
                'network_policy', 'password_changed', 'operator')),
    CONSTRAINT chk_opsession_revoked_pair
        CHECK ((revoked_at IS NULL) = (revoke_reason IS NULL))
);

-- The per-request lookup is by primary key; the cap query walks one account's
-- live rows by recency; the 30-day purge walks by last activity.
CREATE INDEX IF NOT EXISTS idx_opsession_user_live
    ON OperatorSession(user_id, last_seen_at)
    WHERE revoked_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_opsession_last_seen
    ON OperatorSession(last_seen_at);

COMMENT ON TABLE OperatorSession IS
    'Server-side registry of operator web sessions (v9.189 / roadmap P1.7). '
    'One row per login; consulted on every authenticated request. Working '
    'state, not audit-of-record: evictions, expiries, and policy denials are '
    'recorded in AuthAuditLog. Rows are purged 30 days after last activity.';

COMMENT ON COLUMN OperatorSession.session_id IS
    '32 random bytes as hex, minted at login and carried in the signed cookie.';

COMMENT ON COLUMN OperatorSession.revoke_reason IS
    'Why the session ended: logout, evicted (per-role cap), idle (per-role '
    'idle timeout), deactivated (account), network_policy (address left the '
    'role''s allow-list), password_changed (CLI user-passwd), operator (manual).';

-- The app role reads, writes, and purges its own registry. (09_grants.sql''s
-- default privileges already cover new tables; this keeps the grant explicit.)
GRANT SELECT, INSERT, UPDATE, DELETE ON OperatorSession TO polaris_app;

-- (2) Extend AuthAuditLog.event_type with the v9.189 events.
--
-- DROP + ADD of a strict superset, exactly as v8.97 did; existing rows
-- conform to the old list so the swap cannot fail.
ALTER TABLE AuthAuditLog
    DROP CONSTRAINT chk_authaudit_event_type;

ALTER TABLE AuthAuditLog
    ADD CONSTRAINT chk_authaudit_event_type
        CHECK (event_type IN (
            -- Pre-v8.97 set (11 values):
            'LOGIN_SUCCESS', 'LOGIN_FAILED', 'LOGIN_LOCKED',
            'LOGOUT',
            'PASSWORD_CHANGED', 'ACCOUNT_CREATED', 'ACCOUNT_DEACTIVATED',
            'CSRF_REJECTED', 'AUTH_REQUIRED', 'AUTHZ_DENIED',
            'RATE_LIMITED',
            -- v8.97 WebAuthn additions (5 values):
            'WEBAUTHN_REGISTERED',
            'WEBAUTHN_ASSERTED',
            'WEBAUTHN_ASSERTION_FAILED',
            'WEBAUTHN_DEREGISTERED',
            'EMERGENCY_PASSWORD_LOGIN_AUTHORIZED',
            -- v9.189 session/origin hardening (5 values):
            'NETWORK_POLICY_DENIED',
            'SESSION_EVICTED',
            'SESSION_EXPIRED',
            'SESSION_REVOKED',
            'WEBAUTHN_REGISTRATION_REFUSED'
        ));

COMMENT ON CONSTRAINT chk_authaudit_event_type ON AuthAuditLog IS
    'Allowed event_type values. Extended in v8.97 with five WebAuthn '
    'lifecycle events and in v9.189 with five session/origin events '
    '(per-role network policy, session cap/idle/revocation, attestation '
    'policy refusals).';
