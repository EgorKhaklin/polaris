-- ============================================================================
-- 2026-05-14-002-operator-webauthn.up.sql
--
-- v8.97 / Position B from a recorded decision
-- (DECIDED by VANTA in-chat "B").
--
-- The FIRST non-example migration shipped under the v8.95 framework.
-- Validates that the framework handles a real schema change with:
--   - one new table
--   - one new column on an existing table
--   - one CHECK constraint replacement on an existing table
--
-- ADDS (1): OperatorWebauthnCredential — stores enrolled WebAuthn
-- credentials per AppUser. Each row is a (user_id, credential_id) pair
-- with the public key + signature counter + transport list. The library
-- (Duo Labs `webauthn` Python package) verifies registration attestation
-- before we INSERT, so by the time a row exists here, the credential
-- has been validated against W3C WebAuthn Level 3 / FIDO2 CTAP2.
--
-- ADDS (2): AppUser.webauthn_required_after — the deadline by which an
-- admin user MUST have enrolled at least one credential. Before deadline,
-- password-only login allowed (grace period). After deadline + no
-- credential = login refused. After deadline + credential enrolled =
-- both factors required (password + WebAuthn assertion).
--
-- REPLACES (3): AuthAuditLog.chk_authaudit_event_type — extends the
-- event_type CHECK to include the five new WebAuthn event types:
--   WEBAUTHN_REGISTERED, WEBAUTHN_ASSERTED, WEBAUTHN_ASSERTION_FAILED,
--   WEBAUTHN_DEREGISTERED, EMERGENCY_PASSWORD_LOGIN_AUTHORIZED
--
-- REVERSIBLE: yes
--   - .down.sql DROPs the new table, DROPs the new column, restores the
--     prior CHECK constraint (purges any new event-type rows first or
--     the CHECK will fail; see .down.sql header for the procedure).
--
-- ADDITIVE (data side): yes — no existing data mutated.
-- LOCK: brief ACCESS EXCLUSIVE on AppUser + AuthAuditLog while the
-- column add + constraint swap run. New table creation is independent.
-- ============================================================================

-- (1) New table: OperatorWebauthnCredential
--
-- credential_id format: base64url-encoded raw bytes as returned by
-- navigator.credentials.create()'s rawId field; VARCHAR(255) gives
-- headroom for the longest realistic credentials (~127 bytes encoded).
-- It is the WebAuthn-spec-mandated lookup key for the credential and
-- is unique across all authenticators.
--
-- public_key BYTEA stores the COSE-encoded public key returned during
-- the registration attestation. The webauthn library encodes/decodes
-- this; the app does NOT manipulate the bytes directly.
--
-- sign_count BIGINT tracks the authenticator's monotonic counter; on
-- every assertion the new counter must be > the stored value (CTAP2
-- replay-protection). Some authenticators always emit 0 (e.g.,
-- platform authenticators on iOS); that case is documented and the
-- assertion verifier accepts it as long as both are 0.
CREATE TABLE OperatorWebauthnCredential (
    credential_id          VARCHAR(255)  PRIMARY KEY,
    -- ON DELETE NO ACTION (the schema-wide default): deletion is explicit, never
    -- a silent cascade. An operator with enrolled credentials cannot be deleted
    -- until those credentials are explicitly removed (delete_credential), so a
    -- stray AppUser delete can never silently drop MFA state. Operators are
    -- deactivated (is_active=FALSE), not deleted, in normal operation.
    user_id                INTEGER       NOT NULL
                               REFERENCES AppUser(user_id) ON DELETE NO ACTION,
    public_key             BYTEA         NOT NULL,
    sign_count             BIGINT        NOT NULL DEFAULT 0,
    transports             VARCHAR(120),
    attestation_format     VARCHAR(40),
    aaguid                 UUID,
    device_label           VARCHAR(100),
    enrolled_at            TIMESTAMPTZ   NOT NULL DEFAULT now(),
    last_used_at           TIMESTAMPTZ,

    CONSTRAINT chk_webauthn_sign_count_nonneg
        CHECK (sign_count >= 0),
    CONSTRAINT chk_webauthn_credential_id_format
        CHECK (credential_id ~ '^[A-Za-z0-9_-]+={0,2}$')
);

CREATE INDEX idx_webauthn_credential_user
    ON OperatorWebauthnCredential(user_id);

CREATE INDEX idx_webauthn_credential_last_used
    ON OperatorWebauthnCredential(last_used_at DESC)
    WHERE last_used_at IS NOT NULL;

COMMENT ON TABLE OperatorWebauthnCredential IS
    'Per-AppUser WebAuthn credentials (v8.97 / Position B of '
    'a recorded decision). One row per enrolled '
    'authenticator. The webauthn library validates registration attestation '
    'before insert; the app does not manipulate public_key bytes directly.';

COMMENT ON COLUMN OperatorWebauthnCredential.credential_id IS
    'WebAuthn rawId base64url-encoded; the spec-mandated lookup key.';

COMMENT ON COLUMN OperatorWebauthnCredential.public_key IS
    'COSE-encoded public key from registration attestation. Opaque to the app.';

COMMENT ON COLUMN OperatorWebauthnCredential.sign_count IS
    'Authenticator signature counter (CTAP2). Monotonic per assertion. '
    'Platform authenticators may always emit 0; that case is accepted.';

-- (2) New column on AppUser: webauthn_required_after
--
-- NULL = no MFA requirement (e.g., auditor accounts, or pre-deadline).
-- Future TIMESTAMPTZ = deadline; login flow checks this against now().
--
-- The polaris-create-operator.sh script (v8.93) will be updated in this
-- same ship to set this to now()+30d for new admin accounts.
-- Idempotent: webauthn_required_after is also declared in 01_schema.sql so the
-- canonical schema is complete; on a fresh 00_load_all build it already exists
-- and this is a no-op, while on an older deployed DB it adds the column.
ALTER TABLE AppUser
    ADD COLUMN IF NOT EXISTS webauthn_required_after TIMESTAMPTZ;

COMMENT ON COLUMN AppUser.webauthn_required_after IS
    'WebAuthn enrollment deadline (v8.97 / Position B). NULL = no MFA '
    'requirement. Past-now() = login requires at least one enrolled '
    'OperatorWebauthnCredential AND a verified assertion.';

-- (3) Extend AuthAuditLog event_type enum with WebAuthn events
--
-- The CHECK constraint is a CHECK-IN list; we DROP + ADD to extend it.
-- Existing rows already conform to the old enum; the new enum is a
-- strict superset, so the constraint swap cannot fail.
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
            'EMERGENCY_PASSWORD_LOGIN_AUTHORIZED'
        ));

COMMENT ON CONSTRAINT chk_authaudit_event_type ON AuthAuditLog IS
    'Allowed event_type values. Extended in v8.97 with five WebAuthn '
    'lifecycle events per Position B of the WebAuthn Sanctum.';
