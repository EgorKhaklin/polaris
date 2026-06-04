-- ============================================================================
-- AI-context: schema DDL. The partial unique index uq_one_active_per_person
--   is load-bearing for concurrency safety. Read:
--     ../DEVNOTES/concurrency.md  (partial unique index section)
--   DROP TABLE CASCADE means data is wiped on reload. After any edit, also
--   rerun: 02_indexes.sql, 09_grants.sql.
-- ============================================================================

-- ============================================================================
-- POLARIS — IDENTITY TOKEN SYSTEM
-- 01_schema.sql : Schema definition (DDL)
--
-- Author      : Egor Khaklin
-- Target      : PostgreSQL 14 or later
-- Dependencies: none (this is the first file to load)
--
-- This file defines twelve tables, eighteen foreign keys, fourteen CHECK
-- constraints, and one partial unique index. The schema is in BCNF (proof:
-- report §6.5).
--
-- Load order:
--   01_schema.sql        -- this file: DDL
--   02_indexes.sql       -- secondary indexes (Appendix B)
--   03_view.sql          -- ActiveTokens view
--   04_data.sql          -- sample data (73 rows across 12 tables)
--   05_procedures.sql    -- stored procedures wrapping UC-1, UC-4, UC-5, UC-7
--   06_triggers.sql      -- state-machine enforcement trigger (Appendix A)
--   07_queries.sql       -- the six relational-algebra queries as SELECT statements
--   08_tests.sql         -- pgTAP-style assertions exercising every constraint
-- ============================================================================

-- Idempotent: drop in reverse FK-dependency order so reloading the schema is
-- a single command. Order matters; PostgreSQL refuses to drop a table that
-- another table's FK references.
--
-- v9.02: extended to include:
--   - LifecycleArchiveCheckpoint (baseline-added v8.87; missed top-of-file)
--   - OperatorWebauthnCredential (migration-added v8.97 via
--     2026-05-14-002-operator-webauthn.up.sql; lives outside this
--     file but must be dropped here so a 00_load_all.sql re-run
--     doesn't leave it stale-with-no-FK-target after AppUser is
--     recreated. The migration --up will recreate it when
--     polaris-migrate.sh --up runs after the load.)
-- Pre-v9.02 these were missing, so 00_load_all.sql wasn't fully
-- idempotent against a non-empty polaris_test — operators had to
-- dropdb+createdb before re-running. Filed against v8.99 → v8.100
-- → v9.01; closed v9.02.
DROP TABLE IF EXISTS OperatorWebauthnCredential CASCADE;
DROP TABLE IF EXISTS LifecycleArchiveCheckpoint CASCADE;
DROP TABLE IF EXISTS DuressEvent            CASCADE;
DROP TABLE IF EXISTS TokenStateEpochLeaf    CASCADE;
DROP TABLE IF EXISTS TokenStateEpoch        CASCADE;
DROP TABLE IF EXISTS AgencyTrustAttestation CASCADE;
DROP TABLE IF EXISTS AnchorBatch            CASCADE;
DROP TABLE IF EXISTS TokenSignature         CASCADE;
DROP TABLE IF EXISTS RecoveryRequest       CASCADE;
DROP TABLE IF EXISTS EnrollmentStatusEvent  CASCADE;
DROP TABLE IF EXISTS IssuerDiscretionPolicy CASCADE;
DROP TABLE IF EXISTS TokenPermission        CASCADE;
DROP TABLE IF EXISTS AgencyAlgorithmAuth    CASCADE;
DROP TABLE IF EXISTS RevocationList         CASCADE;
DROP TABLE IF EXISTS QuantumObserverBinding CASCADE;
DROP TABLE IF EXISTS GenomicAnchor          CASCADE;
DROP TABLE IF EXISTS BlockchainAnchor       CASCADE;
DROP TABLE IF EXISTS DeviceBinding          CASCADE;
DROP TABLE IF EXISTS VerificationEvent      CASCADE;
DROP TABLE IF EXISTS TokenLifecycleEvent    CASCADE;
DROP TABLE IF EXISTS IdentityToken          CASCADE;
DROP TABLE IF EXISTS AuthAuditLog           CASCADE;
DROP TABLE IF EXISTS AppUser                CASCADE;
DROP TABLE IF EXISTS VerificationContext    CASCADE;
DROP TABLE IF EXISTS CryptographicAlgorithm CASCADE;
DROP TABLE IF EXISTS Agency                 CASCADE;
DROP TABLE IF EXISTS Individual             CASCADE;

-- ============================================================================
-- PRINCIPAL ENTITIES
-- The four principal entities (Individual, Agency, CryptographicAlgorithm,
-- VerificationContext) carry no foreign keys; they are the schema's roots.
-- ============================================================================

-- coverage:exempt — C3 root; appuser FK + uq_one_active_per_person hold; mutations gated by uc_register_individual
CREATE TABLE Individual (
    individual_id   SERIAL       PRIMARY KEY,
    legal_name      VARCHAR(200) NOT NULL
        CHECK (char_length(trim(legal_name)) >= 1),
    date_of_birth   DATE         NOT NULL,
    jurisdiction    VARCHAR(10)  NOT NULL                 -- ISO 3166-2 (e.g. 'US-PA')
        CHECK (jurisdiction ~ '^[A-Z]{2}(-[A-Z0-9]{1,3})?$'),
    enrollment_date TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE Individual IS
  'Natural persons enrolled in the system. The token credentials this entity.';

-- coverage:exempt — configuration table; drift detected via schema_watcher's information_schema check
CREATE TABLE Agency (
    agency_id           SERIAL       PRIMARY KEY,
    name                VARCHAR(200) NOT NULL
        CHECK (char_length(trim(name)) >= 1),
    agency_type         VARCHAR(40)  NOT NULL
        CHECK (agency_type IN ('FEDERAL','STATE','COUNTY','PRIVATE','MUNICIPAL')),
    jurisdiction        VARCHAR(10)  NOT NULL
        CHECK (jurisdiction ~ '^[A-Z]{2}(-[A-Z0-9]{1,3})?$'),
    authorization_level INTEGER      NOT NULL DEFAULT 1
        CHECK (authorization_level BETWEEN 1 AND 5)
);

COMMENT ON TABLE Agency IS
  'Federal, state, county, or private authority that issues or verifies tokens. '
  'Plays dual roles distinguished by which FK column references it: '
  'issuing_agency_id, requesting_agency_id, actor_agency_id, etc.';

-- coverage:exempt — C7 algorithm registry; mutations forbidden except via DBA SQL; drift caught by tg_cryptographicalgorithm_no_update
CREATE TABLE CryptographicAlgorithm (
    algorithm_id         SERIAL       PRIMARY KEY,
    name                 VARCHAR(60)  NOT NULL UNIQUE,
    family               VARCHAR(40)  NOT NULL,
    quantum_resistant    BOOLEAN      NOT NULL,
    nist_standard        VARCHAR(40),                -- 'FIPS 204', 'FIPS 205', etc.
    security_level_bits  INTEGER      NOT NULL
        CHECK (security_level_bits BETWEEN 80 AND 256),
    public_key_size      INTEGER,                    -- bytes
    signature_size       INTEGER,                    -- bytes
    deprecation_date     DATE                        -- NULL = not deprecated
);

COMMENT ON TABLE CryptographicAlgorithm IS
  'First-class entity (not enum) so deprecation_date and quantum_resistant '
  'are queryable. Supports UC-6 (algorithm migration audit).';

-- coverage:exempt — verification context registry; static data; mutations rare; not a runtime drift surface
CREATE TABLE VerificationContext (
    context_id          SERIAL       PRIMARY KEY,
    context_type        VARCHAR(40)  NOT NULL UNIQUE
        CHECK (context_type IN ('BANKING','EMPLOYMENT','HEALTHCARE','TRAVEL',
                                'VOTING','MOTOR_VEHICLE','GOVERNMENT_BENEFITS')),
    description         TEXT,
    requires_biometric  BOOLEAN      NOT NULL DEFAULT FALSE,
    min_security_level  INTEGER      NOT NULL DEFAULT 128
        CHECK (min_security_level >= 128)
);

COMMENT ON TABLE VerificationContext IS
  'Seven fixed verification contexts. Modeled as entity (not enum) so '
  'per-context biometric/security requirements can be queried and joined.';

-- ----------------------------------------------------------------------------
-- AppUser + AuthAuditLog. Originally lived in 10_auth.sql but were promoted
-- here in v8.24-fix so that downstream tables (RecoveryRequest from M2-7,
-- AgencyTrustAttestation from M2-8, TokenStateEpoch from M2-1) can FK to
-- AppUser without forward-reference failure on a fresh-DB initial load.
-- Seed data still lives in 10_auth.sql.
--
-- Design notes:
-- - We DO NOT use PostgreSQL's role/login system for application users. The
--   polaris_app PG role is the sole DB connection identity; application users
--   are rows in AppUser, with passwords hashed via Werkzeug's scrypt.
-- - Three roles: 'admin', 'operator', 'auditor'. Authorization is enforced
--   in the application layer via the @require_role decorator.
-- - AuthAuditLog is append-only by trigger (06_triggers.sql).
-- ----------------------------------------------------------------------------

-- coverage:exempt — C4 atomic failed-login enforced by sp_atomic_failed_login + tg_appuser_failed_login_atomic; security_watcher detects auth-route changes
CREATE TABLE AppUser (
    user_id              SERIAL  PRIMARY KEY,
    username             VARCHAR(50)  NOT NULL UNIQUE,
    password_hash        VARCHAR(255) NOT NULL,
    role                 VARCHAR(20)  NOT NULL,
    is_active            BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at           TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_login_at        TIMESTAMP,
    failed_login_count   INTEGER      NOT NULL DEFAULT 0,
    locked_until         TIMESTAMP,
    -- WebAuthn MFA deadline (migration 2026-05-14-002): NULL = no requirement;
    -- a future TIMESTAMPTZ is the deadline the login flow checks against now().
    webauthn_required_after  TIMESTAMPTZ,
    -- SHA-256 of the operator's recovery code (migration 2026-05-14-003). NULL
    -- until a code is enrolled. Defined here so the canonical schema is complete;
    -- the matching migrations add these idempotently to deployed databases.
    recovery_code_hash       VARCHAR(64),

    CONSTRAINT chk_appuser_role
        CHECK (role IN ('admin', 'operator', 'auditor')),
    CONSTRAINT chk_appuser_username_format
        CHECK (username ~ '^[a-z0-9._-]{3,50}$'),
    CONSTRAINT chk_appuser_failed_count_nonneg
        CHECK (failed_login_count >= 0),
    CONSTRAINT chk_recovery_code_hash_format
        CHECK (recovery_code_hash IS NULL OR recovery_code_hash ~ '^[0-9a-f]{64}$')
);

CREATE INDEX idx_appuser_username ON AppUser(username);

COMMENT ON TABLE AppUser IS
  'Application user accounts. Distinct from PostgreSQL roles — the app '
  'connects as polaris_app regardless of which AppUser is logged in. '
  'Passwords are hashed by Werkzeug''s scrypt before storage.';

-- coverage:exempt — C1 AoR enforced by tg_authauditlog_append_only; schema_watcher verifies the trigger exists
CREATE TABLE AuthAuditLog (
    audit_id           SERIAL       PRIMARY KEY,
    event_timestamp    TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    event_type         VARCHAR(40)  NOT NULL,
    username           VARCHAR(50),
    user_id            INTEGER,
    ip_address         VARCHAR(45),
    user_agent         VARCHAR(255),
    detail             VARCHAR(500),

    CONSTRAINT chk_authaudit_event_type
        CHECK (event_type IN (
            'LOGIN_SUCCESS', 'LOGIN_FAILED', 'LOGIN_LOCKED',
            'LOGOUT',
            'PASSWORD_CHANGED', 'ACCOUNT_CREATED', 'ACCOUNT_DEACTIVATED',
            'CSRF_REJECTED', 'AUTH_REQUIRED', 'AUTHZ_DENIED',
            'RATE_LIMITED'
        ))
);

CREATE INDEX idx_authaudit_timestamp ON AuthAuditLog(event_timestamp DESC);
CREATE INDEX idx_authaudit_user      ON AuthAuditLog(user_id);
CREATE INDEX idx_authaudit_event     ON AuthAuditLog(event_type);

COMMENT ON TABLE AuthAuditLog IS
  'Append-only log of authentication and authorization events. '
  'Captures successes, failures, lockouts, CSRF rejections, and authz denials.';

-- ============================================================================
-- CENTRAL ARTIFACT
-- IdentityToken is the schema''s hub. Six FKs (one self-referential), the
-- partial unique constraint, and CHECK constraints on three enumerated columns.
-- ============================================================================

-- coverage:exempt — C3 enforced by uq_one_active_per_person partial unique index; C2 ZK constraint at engine; cognitive-layer redundancy would dilute trigger-layer responsibility
CREATE TABLE IdentityToken (
    token_id                     SERIAL       PRIMARY KEY,
    token_value                  VARCHAR(128) NOT NULL UNIQUE,    -- canonical token serial
    physical_serial              VARCHAR(64)  NOT NULL UNIQUE,    -- hardware serial
    hardware_model               VARCHAR(50),
    biometric_binding_type       VARCHAR(20)  NOT NULL
        CHECK (biometric_binding_type IN ('NONE','FINGERPRINT','FACE','IRIS')),
    biometric_enrolled_date      TIMESTAMP,
    enrollment_witness_agency_id INTEGER REFERENCES Agency(agency_id),
    liveness_check_type          VARCHAR(20)
        CHECK (liveness_check_type IN ('PASSIVE','ACTIVE_CHALLENGE','MULTI_MODAL')),
    individual_id                INTEGER NOT NULL REFERENCES Individual(individual_id),
    issuing_agency_id            INTEGER NOT NULL REFERENCES Agency(agency_id),
    algorithm_id                 INTEGER NOT NULL REFERENCES CryptographicAlgorithm(algorithm_id),
    predecessor_token_id         INTEGER REFERENCES IdentityToken(token_id),  -- self-referential, nullable
    activation_sequence          INTEGER NOT NULL DEFAULT 1
        CHECK (activation_sequence >= 1),
    status                       VARCHAR(20) NOT NULL DEFAULT 'RESERVE'
        CHECK (status IN ('ACTIVE','RESERVE','DORMANT','REVOKED','LOST','EXPIRED')),
    issued_date                  TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP,
    activated_date               TIMESTAMP,
    expiration_date              DATE,
    -- v8.24 / R11-5 / M2-10: optional duress-code commitment (Werkzeug scrypt hash).
    -- NULL = no duress code enrolled. When set, the verification flow checks the
    -- holder's typed duress_code against this hash with constant-time comparison.
    -- A match silently writes a DuressEvent row and the user-visible verification
    -- proceeds as normal (R2 audit refinement — identical observable behavior).
    duress_code_hash             VARCHAR(255),
    -- Temporal sanity: activated_date and expiration_date must come after issued_date.
    CONSTRAINT chk_token_time_order CHECK (
        (activated_date  IS NULL OR activated_date  >= issued_date) AND
        (expiration_date IS NULL OR expiration_date >= issued_date::date)
    ),
    -- A non-NULL duress_code_hash must be a Werkzeug scrypt hash (length ≥ 20 chars
    -- is a generous floor; a real scrypt hash is ~150 chars).
    CONSTRAINT chk_duress_hash_well_formed CHECK (
        duress_code_hash IS NULL OR char_length(duress_code_hash) >= 20
    )
    -- One-active-per-person invariant is enforced via a partial unique INDEX
    -- (created in 02_indexes.sql), not a CONSTRAINT, because the application
    -- requires the uniqueness to apply only to status='ACTIVE'. PostgreSQL
    -- supports partial uniqueness through CREATE UNIQUE INDEX ... WHERE,
    -- which is the standard idiom for this pattern.
    --
    -- UC-4 (reserve activation after loss) avoids any need for deferred-
    -- constraint semantics by ordering the swap: the lost token transitions
    -- to its terminal status first (releasing it from the partial-index
    -- predicate), then the reserve is promoted to ACTIVE. See
    -- uc4_activate_reserve in 05_procedures.sql.
);

COMMENT ON TABLE IdentityToken IS
  'The credential. Schema''s central hub: every other relationship either '
  'originates from or terminates at this entity. Six FKs (one self-referential).';

COMMENT ON COLUMN IdentityToken.predecessor_token_id IS
  'Self-referential FK capturing token succession. NULL for the first token '
  'in any holder''s sequence. Walked recursively to reconstruct lineage.';

-- ============================================================================
-- RECORD ENTITIES
-- These attach to IdentityToken via mandatory FKs (token_id) and capture
-- events or state derived from the central artifact.
-- ============================================================================

-- coverage:exempt — C1 AoR enforced by tg_tokenlifecycleevent_append_only; schema_watcher verifies via EXPECTED_AOR_TABLES
CREATE TABLE TokenLifecycleEvent (
    event_id        SERIAL    PRIMARY KEY,
    token_id        INTEGER   NOT NULL REFERENCES IdentityToken(token_id),
    actor_agency_id INTEGER            REFERENCES Agency(agency_id),  -- nullable: device events have no agency actor
    event_type      VARCHAR(20) NOT NULL
        CHECK (event_type IN ('ISSUED','ACTIVATED','DEACTIVATED',
                              'DEVICE_BOUND','DEVICE_REVOKED',
                              'REVOKED','LOST','EXPIRED','REPLACED')),
    event_timestamp TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP,
    reason_code     VARCHAR(60),
    -- Geographic coordinates of the event. Nullable so legacy events without
    -- recorded location remain valid; cluster aggregation IS NULL-tolerant.
    latitude        DOUBLE PRECISION CHECK (latitude  IS NULL OR (latitude  BETWEEN  -90 AND  90)),
    longitude       DOUBLE PRECISION CHECK (longitude IS NULL OR (longitude BETWEEN -180 AND 180))
);

COMMENT ON TABLE TokenLifecycleEvent IS
  'Append-only audit trail. actor_agency_id is the agency that performed the '
  'specific transition (may differ from issuing_agency_id; nullable for '
  'device-binding events with no human agency actor). The append-only invariant '
  'is enforced by convention and tooling (see 06_triggers.sql), not storage engine.';

CREATE TABLE VerificationEvent (
    event_id             SERIAL    PRIMARY KEY,
    token_id             INTEGER            REFERENCES IdentityToken(token_id),  -- NULLABLE: ZERO_KNOWLEDGE
    requesting_agency_id INTEGER   NOT NULL REFERENCES Agency(agency_id),
    context_id           INTEGER   NOT NULL REFERENCES VerificationContext(context_id),
    event_timestamp      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    outcome              VARCHAR(20) NOT NULL
        CHECK (outcome IN ('SUCCESS','FAILURE','EXPIRED','UNAUTHORIZED')),
    disclosure_level     VARCHAR(20) NOT NULL
        CHECK (disclosure_level IN ('ZERO_KNOWLEDGE','SELECTIVE','FULL')),
    proof_commitment     VARCHAR(128),                              -- ZK commitment hash
    requestor_location   VARCHAR(200),
    -- Geographic coordinates of where the verification was attempted. Used by
    -- the operational atlas's spatial aggregation. Nullable for legacy rows;
    -- new rows must populate from agency / requestor location lookup.
    latitude             DOUBLE PRECISION CHECK (latitude  IS NULL OR (latitude  BETWEEN  -90 AND  90)),
    longitude            DOUBLE PRECISION CHECK (longitude IS NULL OR (longitude BETWEEN -180 AND 180)),
    -- v9.20 / migration 2026-05-14..15. Operator-supplied free-text reason for
    -- THIS verification. NULL = no purpose supplied. Defined here so the
    -- canonical schema is complete on its own; the matching migration adds it
    -- idempotently to already-deployed databases.
    --
    -- Anti-coercion-direct (the Vocation): a coerced verification leaves a
    -- stated-purpose trail — the coercer's stated context becomes part of the
    -- permanent evidentiary chain. So, UNLIKE requestor_location (which
    -- uc7_warrant_audit and the /verifications + /atlas read paths redact to
    -- NULL for ZERO_KNOWLEDGE rows, C6), this column is RETAINED verbatim on
    -- every disclosure level, ZERO_KNOWLEDGE included. Redacting it would
    -- destroy the evidence trail it exists to create — do NOT add a ZK-redaction
    -- CASE here (polaris_checks.check_coercion_evidence_retained guards this).
    -- It does not weaken C2: a ZERO_KNOWLEDGE row still carries no token_id
    -- (chk_disclosure_token_consistency), so the holder is not derivable from it.
    requesting_purpose_text VARCHAR(280),
    -- Disclosure-level integrity: ZERO_KNOWLEDGE events MUST NOT carry token_id;
    -- FULL events MUST carry token_id. SELECTIVE may go either way depending on
    -- which attributes are disclosed.
    CONSTRAINT chk_disclosure_token_consistency CHECK (
        (disclosure_level = 'ZERO_KNOWLEDGE' AND token_id IS NULL) OR
        (disclosure_level = 'FULL'           AND token_id IS NOT NULL) OR
        (disclosure_level = 'SELECTIVE')
    ),
    CONSTRAINT chk_purpose_text_length CHECK (
        requesting_purpose_text IS NULL
        OR char_length(TRIM(BOTH FROM requesting_purpose_text)) BETWEEN 1 AND 280
    )
);

COMMENT ON TABLE VerificationEvent IS
  'High-volume transactional table. token_id is nullable so ZERO_KNOWLEDGE '
  'verifications produce no token-identifying record. The disclosure_level '
  'column is the schema''s architectural protection against the verification '
  'log functioning as a surveillance database.';

-- coverage:exempt — M2-5 device-binding via webauthn_auth.py + uc_bind_device; drift via QuantumObserverBinding scaffold tests
CREATE TABLE DeviceBinding (
    binding_id         SERIAL      PRIMARY KEY,
    token_id           INTEGER     NOT NULL REFERENCES IdentityToken(token_id),
    device_type        VARCHAR(20) NOT NULL
        CHECK (device_type IN ('PHONE','TABLET','WATCH')),
    device_fingerprint VARCHAR(128) NOT NULL UNIQUE,                 -- secure-enclave-attested
    binding_method     VARCHAR(40) NOT NULL
        CHECK (binding_method IN ('SECURE_ENCLAVE','TITAN_SECURITY','TRUSTED_PLATFORM_MODULE')),
    authorized_date    TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_date       TIMESTAMP,
    status             VARCHAR(20) NOT NULL DEFAULT 'ACTIVE'
        CHECK (status IN ('ACTIVE','REVOKED')),
    revocation_reason  VARCHAR(60)
);

COMMENT ON TABLE DeviceBinding IS
  'Digital projection of physical token to a personal device''s secure enclave. '
  'No backup credential is ever stored on a server; this table records only '
  'binding metadata.';

-- coverage:exempt — anchoring lifecycle in anchoring.py + uc_anchor_record; structural tests in test_app.py::AnchoringTests
CREATE TABLE BlockchainAnchor (
    anchor_id        SERIAL      PRIMARY KEY,
    token_id         INTEGER     NOT NULL REFERENCES IdentityToken(token_id),
    did              VARCHAR(200) NOT NULL UNIQUE,                   -- W3C Decentralized Identifier
    commitment_hash  VARCHAR(128) NOT NULL
        -- v8.46: hex CHECK (optionally `0x`-prefixed; mirrors the
        -- pattern established by GenomicAnchor.anchor_hash, but
        -- permissive of the `0x` prefix the seed values carry).
        CHECK (commitment_hash ~ '^(0x)?[0-9a-fA-F]+$'),
    ledger_network   VARCHAR(40) NOT NULL
        CHECK (ledger_network IN ('ALGORAND_PQ','HYPERLEDGER_INDY','CUSTOM_LATTICE')),
    anchor_tx_hash   VARCHAR(128),                                    -- ledger transaction id
    anchored_date    TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP,
    status           VARCHAR(20) NOT NULL DEFAULT 'ACTIVE'
        CHECK (status IN ('ACTIVE','SUPERSEDED','REVOKED')),

    -- v8.21 / R10-2 / M2-2: Merkle-log commitment fields.
    -- batch_id NULL = pending (not yet batched); NOT NULL = committed.
    -- merkle_proof is the JSON inclusion path for the leaf hashed from
    -- (token_id, commitment_hash). See close_anchor_batch + anchoring.py.
    -- The FK to AnchorBatch(batch_id) is added via ALTER TABLE later
    -- in this file because AnchorBatch is defined after BlockchainAnchor
    -- (topological constraint: AnchorBatch references CryptographicAlgorithm,
    -- which appears earlier in the file, so AnchorBatch can sit near
    -- TokenSignature / IssuerDiscretionPolicy at the bottom).
    batch_id         INTEGER,
    merkle_proof     JSONB,
    CONSTRAINT anchor_proof_with_batch CHECK (
        (batch_id IS NULL AND merkle_proof IS NULL) OR
        (batch_id IS NOT NULL AND merkle_proof IS NOT NULL)
    )
);

COMMENT ON TABLE BlockchainAnchor IS
  'Optional ledger-anchored DID commitment. Holds commitments and references '
  'only, never personal or biometric data. 1:1 with token in ACTIVE status; '
  'additional anchors permitted in SUPERSEDED or REVOKED status. v8.21 / '
  'R10-2 / M2-2: extended with batch_id + merkle_proof to support the '
  'internal Merkle-log commitment device — see AnchorBatch and '
  'close_anchor_batch.';

-- coverage:exempt — C8 atlas-cap protection on /api/atlas/*; mutations rare; drift surfaces via performance_watcher latency probe
CREATE TABLE RevocationList (
    revocation_id        SERIAL    PRIMARY KEY,
    token_id             INTEGER   NOT NULL REFERENCES IdentityToken(token_id),
    revoked_by_agency_id INTEGER   NOT NULL REFERENCES Agency(agency_id),
    revocation_timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    effective_date       DATE      NOT NULL,
    reason_code          VARCHAR(40) NOT NULL
        CHECK (reason_code IN ('COMPROMISED','LOST','STOLEN','SUPERSEDED',
                               'ADMINISTRATIVE','DEATH')),
    published_location   VARCHAR(300)                                  -- CRL distribution URL
);

COMMENT ON TABLE RevocationList IS
  'Verifier-facing historical revocation registry. Separates revocation '
  'publication from the token''s own status field, supporting audit-accurate '
  'historical freshness checks.';

-- ----------------------------------------------------------------------------
-- GENOMIC ANCHOR (Appendix F.1, M2-4 / R10-4 — schema-enforced privacy)
--
-- Genomic identifier binding for the token, stored as a HASH only. The
-- biometric / genomic plaintext never enters the database; this table
-- records a cryptographic commitment that audit can verify against an
-- out-of-band re-presentation but cannot reverse.
--
-- The privacy invariant (Appendix F.1: "no plaintext genomic data is
-- storable") is enforced at the schema level by three CHECK constraints
-- working together:
--
--   (1) genomic_hash_is_hex
--       The anchor_hash column accepts only hexadecimal characters.
--       Plaintext genomic data using {G, T, U, N} (or lowercase) fails
--       this check immediately because those letters are not hex digits.
--
--   (2) genomic_hash_length_matches_algorithm
--       The hash length must match the named algorithm's output size.
--       SHA3-256 / BLAKE3-256 / BLAKE2b-256 → 64 hex chars (32 bytes);
--       SHA3-512 → 128 hex chars (64 bytes). Plaintext sequences have
--       no reason to land on these specific lengths.
--
--   (3) genomic_anchor_refuses_plaintext
--       Belt-and-suspenders for the residual case where someone tries
--       to store plaintext using only the {A, C} subset (which IS
--       hex-valid): the constraint requires the hash to contain at
--       least one character outside the genomic alphabet
--       {A,C,G,T,U,N} (case-insensitive). A real hex hash, by
--       uniformity, will contain digits or {b,d,e,f} with probability
--       essentially 1; a pure-genomic plaintext over the alphabet
--       above will not.
--
-- The combination of the three is the schema-level statement of the
-- privacy claim. A future operator with INSERT privilege but no
-- application-layer context cannot accidentally store plaintext.
-- ----------------------------------------------------------------------------

-- coverage:exempt — M2-4 scaffold; no live writes yet; drift via migrations framework when activated
CREATE TABLE GenomicAnchor (
    anchor_id         SERIAL       PRIMARY KEY,
    token_id          INTEGER      NOT NULL REFERENCES IdentityToken(token_id),
    hash_algorithm    VARCHAR(20)  NOT NULL
        CHECK (hash_algorithm IN ('SHA3-256','SHA3-512','BLAKE3-256','BLAKE2b-256')),
    anchor_hash       VARCHAR(128) NOT NULL,
    enrollment_date   DATE         NOT NULL,
    witness_agency_id INTEGER      NOT NULL REFERENCES Agency(agency_id),
    enrolled_at       TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT genomic_hash_is_hex CHECK (
        anchor_hash ~ '^[0-9a-fA-F]+$'
    ),
    CONSTRAINT genomic_hash_length_matches_algorithm CHECK (
        (hash_algorithm = 'SHA3-256'    AND length(anchor_hash) = 64)  OR
        (hash_algorithm = 'SHA3-512'    AND length(anchor_hash) = 128) OR
        (hash_algorithm = 'BLAKE3-256'  AND length(anchor_hash) = 64)  OR
        (hash_algorithm = 'BLAKE2b-256' AND length(anchor_hash) = 64)
    ),
    -- The genomic alphabet here is {A,C,G,T,U,N} (DNA + RNA + unknown
    -- placeholder), case-insensitive. Anything outside this set in the hash
    -- proves the input is not plaintext genomic data.
    CONSTRAINT genomic_anchor_refuses_plaintext CHECK (
        anchor_hash ~ '[^ACGTUNacgtun]'
    )
);

COMMENT ON TABLE GenomicAnchor IS
  'Genomic-binding anchor (Appendix F.1). Stores hash of genomic identifier '
  'only — three CHECK constraints (hex format, algorithm-specific length, '
  'no-pure-genomic-alphabet) refuse plaintext genomic data at the schema '
  'level. The biometric / genomic plaintext never enters the database; this '
  'row is a non-reversible commitment retained for audit-trail purposes when '
  'a token is reissued or its biometric binding is challenged. See M2-4 in '
  'MISSION.md.';

COMMENT ON COLUMN GenomicAnchor.anchor_hash IS
  'Hex-encoded hash output. Must be all-hex, length must match '
  'hash_algorithm, and must not consist solely of {A,C,G,T,U,N} characters. '
  'The triple of CHECK constraints is the privacy invariant.';

-- ============================================================================
-- QUANTUM-OBSERVER BINDING (Appendix F.2) — M2-5 / R10-5 scaffold
-- ============================================================================
-- Reserves the substrate-level slot for a quantum-measurement attestation
-- primitive. Until quantum-observer hardware exists, every row in this
-- table is binding_status='SCAFFOLD' and the functional fields are NULL.
-- When the hardware ecosystem matures, rows transition to 'OPERATIONAL'
-- and populate the deferred fields — without a breaking schema migration.
--
-- The scaffold-state and operational-state invariants are enforced by
-- CHECK constraints so the deferred fields can't be partially populated.
-- See DEVNOTES/ships/quantum-observer.md for the architectural rationale.
-- ============================================================================

-- coverage:exempt — M2-5 scaffold; no live writes; drift via migrations framework when M2-5 activates
CREATE TABLE QuantumObserverBinding (
    binding_id          SERIAL       PRIMARY KEY,
    token_id            INTEGER      NOT NULL REFERENCES IdentityToken(token_id),

    -- Scaffold marker. 'SCAFFOLD' is the only legal state until quantum-
    -- observer hardware exists. 'OPERATIONAL' is reserved for the future.
    -- 'DEPRECATED' is for rows whose protocol has been retired post-migration.
    binding_status      VARCHAR(20)  NOT NULL DEFAULT 'SCAFFOLD'
        CHECK (binding_status IN ('SCAFFOLD', 'OPERATIONAL', 'DEPRECATED')),

    -- DEFERRED: which quantum-measurement protocol bound the token. NULL
    -- while SCAFFOLD. Anticipated values from Appendix F.2: 'BB84-WITNESS',
    -- 'E91-ENTANGLEMENT-WITNESS', 'MEASUREMENT-INDEPENDENT-QKD',
    -- 'CONTINUOUS-VARIABLE-QKD'. The enum is intentionally NOT a CHECK
    -- constraint yet — protocol vocabulary is unsettled.
    observer_protocol   VARCHAR(40),

    -- DEFERRED: hash of the wavefunction-collapse record. NULL while
    -- SCAFFOLD. Length follows collapse_hash_algorithm when populated.
    collapse_witness_hash VARCHAR(128),

    -- DEFERRED: hash algorithm. NULL while SCAFFOLD. Expected to align
    -- with the CryptographicAlgorithm table or its post-quantum analog
    -- when this becomes operational.
    collapse_hash_algorithm VARCHAR(20),

    -- DEFERRED: coherence window in milliseconds. NULL while SCAFFOLD.
    -- Semantics depend on the protocol; tighter is harder to spoof.
    coherence_window_ms INTEGER,

    -- Always-populated bookkeeping (real even in SCAFFOLD state):
    registered_agency_id INTEGER     NOT NULL REFERENCES Agency(agency_id),
    registered_at        TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP,

    -- Scaffold invariant: SCAFFOLD rows must NOT populate deferred fields.
    -- Catches premature population of fields whose semantics aren't stable.
    CONSTRAINT qob_scaffold_defers_functional CHECK (
        binding_status != 'SCAFFOLD' OR (
            observer_protocol     IS NULL AND
            collapse_witness_hash IS NULL AND
            collapse_hash_algorithm IS NULL AND
            coherence_window_ms   IS NULL
        )
    ),

    -- Operational invariant: OPERATIONAL rows must populate the deferred
    -- fields. Can't claim functional binding without the data.
    CONSTRAINT qob_operational_requires_functional CHECK (
        binding_status != 'OPERATIONAL' OR (
            observer_protocol     IS NOT NULL AND
            collapse_witness_hash IS NOT NULL AND
            collapse_hash_algorithm IS NOT NULL
        )
    )
);

COMMENT ON TABLE QuantumObserverBinding IS
  'Substrate-level quantum-measurement attestation scaffold (Appendix F.2). '
  'Until quantum-observer hardware exists, every row is binding_status=SCAFFOLD '
  'and the functional fields are NULL. Two CHECK constraints enforce the '
  'scaffold vs operational state transition. M2-5 / R10-5 — see '
  'DEVNOTES/ships/quantum-observer.md for the architectural rationale.';

COMMENT ON COLUMN QuantumObserverBinding.binding_status IS
  'SCAFFOLD = placeholder (current state until hardware exists). '
  'OPERATIONAL = real binding with all deferred fields populated. '
  'DEPRECATED = retired protocol, kept for audit. The transition '
  'SCAFFOLD → OPERATIONAL requires populating observer_protocol, '
  'collapse_witness_hash, and collapse_hash_algorithm — enforced by CHECK.';

COMMENT ON COLUMN QuantumObserverBinding.observer_protocol IS
  'DEFERRED. Which quantum-measurement protocol bound the token. NULL '
  'while binding_status=SCAFFOLD. Expected vocabulary in Appendix F.2.';

-- ============================================================================
-- JUNCTION TABLES
-- Resolve the two M:N relationships from the ER model. Composite primary keys.
-- ============================================================================

-- coverage:exempt — agency-policy table; mutations gated by uc_set_agency_algorithm_auth procedure
CREATE TABLE AgencyAlgorithmAuth (
    agency_id          INTEGER     NOT NULL REFERENCES Agency(agency_id),
    algorithm_id       INTEGER     NOT NULL REFERENCES CryptographicAlgorithm(algorithm_id),
    authorization_type VARCHAR(20) NOT NULL
        CHECK (authorization_type IN ('ISSUE','VERIFY','BOTH')),
    authorized_date    TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (agency_id, algorithm_id)
);

COMMENT ON TABLE AgencyAlgorithmAuth IS
  'Junction resolving the M:N AUTHORIZED relationship between Agency and '
  'CryptographicAlgorithm. Carries authorization_type (ISSUE / VERIFY / BOTH).';

-- coverage:exempt — C6 server-side disclosure-level enforcement; gated by uc6_migrate; rate-limited
CREATE TABLE TokenPermission (
    token_id         INTEGER     NOT NULL REFERENCES IdentityToken(token_id),
    context_id       INTEGER     NOT NULL REFERENCES VerificationContext(context_id),
    permission_level VARCHAR(20) NOT NULL
        CHECK (permission_level IN ('READ','VERIFY','FULL')),
    granted_date     TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (token_id, context_id)
);

COMMENT ON TABLE TokenPermission IS
  'Junction resolving the M:N PERMITTED relationship between IdentityToken '
  'and VerificationContext. Carries permission_level (READ / VERIFY / FULL).';

-- ----------------------------------------------------------------------------
-- IssuerDiscretionPolicy: per-agency overrides for the rolling-window
-- revocation rate bound enforced by uc8_revoke_token (R11-6 / M2-11).
--
-- The system-wide defaults live in cluster-level GUCs set in 09_grants.sql
-- (polaris.default_max_revoke_percent / polaris.default_window_days). Absence
-- of a row here means an agency inherits the system default. A row tightens
-- or loosens the bound for that agency only and requires a justification
-- string at least 20 characters long so any loosening is auditable.
--
-- Implements the PDF §9 "constitutional limits on issuer discretion" leg of
-- the issuer-trust-concentration triad (alongside cryptographic diversity
-- and federation).
-- ----------------------------------------------------------------------------
-- coverage:exempt — M2-11 issuer-discretion bounds enforced by tg_issuerdiscretionpolicy_enforce_bounds; tested in test_app.py::IssuerDiscretionBoundsTests
CREATE TABLE IssuerDiscretionPolicy (
    agency_id           INTEGER     PRIMARY KEY
                        REFERENCES Agency(agency_id),
    max_revoke_percent  NUMERIC(5,2) NOT NULL
                        CHECK (max_revoke_percent > 0
                               AND max_revoke_percent <= 100),
    window_days         INTEGER     NOT NULL
                        CHECK (window_days BETWEEN 1 AND 365),
    set_by_admin        VARCHAR(50) NOT NULL,
    set_at              TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP,
    justification       TEXT        NOT NULL
                        CHECK (length(justification) >= 20)
);

COMMENT ON TABLE IssuerDiscretionPolicy IS
  'Per-agency overrides to the system-wide N% / W-day bound on revocation '
  'velocity (R11-6 / M2-11). Absence of a row means the system default '
  '(see polaris.default_max_revoke_percent GUC) applies. The justification '
  'field is required so any loosening is auditable.';

-- ----------------------------------------------------------------------------
-- EnrollmentStatusEvent: append-only log of enrollment-state transitions per
-- Individual (R11-4 / M2-9). Records civic enrollment vocabulary without
-- making the schema the gatekeeper of who counts.
--
-- Five states with carefully-chosen semantics:
--   NOT_ENROLLED        — default; the absence of enrollment. Seeded
--                         automatically for every new Individual row by the
--                         trg_seed_default_enrollment_status trigger.
--   PENDING_ENROLLMENT  — enrollment process initiated; biometrics or
--                         documentation in progress.
--   ENROLLED            — has at least one non-terminal IdentityToken.
--                         Recorded as a policy event, NOT auto-derived from
--                         token state — see DEVNOTES/ships/tiered-enrollment.md
--                         for the auto-derivation-is-wrong argument.
--   EXEMPT              — civic-policy recognition of non-token participation
--                         (biometric incompatibility, religious exemption,
--                         conscientious objection). The positive vocabulary
--                         the PDF §9 "accepted path without tokens" names.
--   LAPSED              — was ENROLLED, now isn't, by policy event. Distinct
--                         from NOT_ENROLLED (never enrolled) by design.
--
-- Append-only invariant enforced by extending reject_audit_modification
-- (see 06_triggers.sql). State-machine sequencing is NOT trigger-enforced —
-- application policy enforces it where it matters. Mirrors the
-- TokenLifecycleEvent posture: the schema records what policy claims.
--
-- Implements PDF §9 Population coverage open problem.
-- ----------------------------------------------------------------------------
-- coverage:exempt — C1 AoR enforced by tg_enrollmentstatusevent_append_only; tested in test_app.py::TieredEnrollmentTests
CREATE TABLE EnrollmentStatusEvent (
    event_id              SERIAL    PRIMARY KEY,
    individual_id         INTEGER   NOT NULL REFERENCES Individual(individual_id),
    status                VARCHAR(20) NOT NULL
        CHECK (status IN ('NOT_ENROLLED',
                          'PENDING_ENROLLMENT',
                          'ENROLLED',
                          'EXEMPT',
                          'LAPSED')),
    transition_reason     VARCHAR(60) NOT NULL,
    recorded_by_agency_id INTEGER REFERENCES Agency(agency_id),  -- nullable: SYSTEM seed events
    event_timestamp       TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    notes                 TEXT
);

COMMENT ON TABLE EnrollmentStatusEvent IS
  'Append-only log of enrollment-state transitions per Individual '
  '(R11-4 / M2-9). Five states: NOT_ENROLLED (default), '
  'PENDING_ENROLLMENT, ENROLLED, EXEMPT, LAPSED. State transitions are '
  'policy events recorded here; the schema does not enforce sequencing. '
  'Implements PDF §9 population-coverage open problem; see '
  'DEVNOTES/ships/tiered-enrollment.md for the asymmetric-design rationale '
  '(EXEMPT frictionless, NOT_ENROLLED-enumeration deliberate).';

-- ----------------------------------------------------------------------------
-- RecoveryRequest: out-of-band recovery ceremony for catastrophic-loss
-- scenarios (R11-2 / M2-7). When a holder loses ALL of their tokens AND
-- devices simultaneously (the case PDF §9.1 names), this table records the
-- two-phase recovery ceremony.
--
-- Phase 1 (uc9_initiate_recovery): INSERT a PENDING row. No token issued.
-- Phase 2 (uc9_complete_recovery): a DIFFERENT AppUser with admin role
-- transitions to APPROVED or REJECTED. APPROVED requires:
--   - cool-down expired (CHECK cooldown_window_minimum + approved_after_cooldown)
--   - all three OOB channels verified (CHECK approved_requires_three_channels)
--   - approver ≠ requester (CHECK approver_differs_from_requester)
--
-- The four CHECK constraints encode the entire mechanism design:
-- an attacker cannot bypass the cool-down, cannot self-approve, cannot
-- skip the three-channel verification. The database refuses.
--
-- See DEVNOTES/ships/recovery-ceremony.md for the adversary walk and what
-- breaks if any CHECK is removed. The advisory-lock on
-- claimed_individual_id (in uc9_complete_recovery) provides C9
-- concurrency correctness; cross-individual recoveries remain parallel.
--
-- Implements PDF §9.1 catastrophic-loss-risk open problem. The third leg
-- of the "schema doesn't weaponize itself against the holder" triad
-- alongside R11-4 (entry) and R11-6 (exit).
-- ----------------------------------------------------------------------------
-- coverage:exempt — UC-9 catastrophic-loss recovery; lifecycle in uc_initiate_recovery + uc_complete_recovery; tested in test_app.py::RecoveryTests
CREATE TABLE RecoveryRequest (
    recovery_id              SERIAL       PRIMARY KEY,
    claimed_individual_id    INTEGER      NOT NULL
                             REFERENCES Individual(individual_id),
    requested_at             TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    requesting_agency_id     INTEGER      NOT NULL REFERENCES Agency(agency_id),
    requesting_user_id       INTEGER      NOT NULL REFERENCES AppUser(user_id),

    status                   VARCHAR(20)  NOT NULL DEFAULT 'PENDING'
                             CHECK (status IN ('PENDING','APPROVED','REJECTED','EXPIRED')),

    -- Three independent OOB channels. Each NULL/FALSE until verified.
    biometric_verified       BOOLEAN      NOT NULL DEFAULT FALSE,
    sworn_statement_hash     VARCHAR(128),
    witness_agency_id        INTEGER      REFERENCES Agency(agency_id),
    witness_co_sign_user_id  INTEGER      REFERENCES AppUser(user_id),

    -- Approval ceremony
    decided_at               TIMESTAMP,
    decided_by_user_id       INTEGER      REFERENCES AppUser(user_id),
    decision_reason          TEXT,
    resulting_token_id       INTEGER      REFERENCES IdentityToken(token_id),

    -- Cool-down enforcement (≥ 48h between request and decision).
    -- This is the administrative window per PDF §9.1 "defined grace
    -- period"; the operational grace credential (TemporaryAttestation)
    -- is a follow-up — see DEVNOTES/ships/recovery-ceremony.md.
    cooldown_expires_at      TIMESTAMP    NOT NULL,

    CONSTRAINT cooldown_window_minimum CHECK (
        cooldown_expires_at >= requested_at + INTERVAL '48 hours'
    ),

    CONSTRAINT approved_requires_three_channels CHECK (
        status <> 'APPROVED' OR (
            biometric_verified = TRUE AND
            sworn_statement_hash IS NOT NULL AND
            witness_agency_id IS NOT NULL AND
            witness_co_sign_user_id IS NOT NULL
        )
    ),

    CONSTRAINT approved_after_cooldown CHECK (
        status <> 'APPROVED' OR decided_at >= cooldown_expires_at
    ),

    CONSTRAINT approver_differs_from_requester CHECK (
        decided_by_user_id IS NULL OR
        decided_by_user_id <> requesting_user_id
    ),

    -- Separation of duties for the third (witness) channel: the witness
    -- co-signer cannot be the requester or the approver, or the "three
    -- independent channels" collapse to a single actor who self-witnesses and
    -- self-approves. Mirrors approver_differs_from_requester; also enforced in
    -- uc9_complete_recovery with a clearer error.
    CONSTRAINT witness_differs_from_parties CHECK (
        witness_co_sign_user_id IS NULL OR (
            witness_co_sign_user_id <> requesting_user_id AND
            (decided_by_user_id IS NULL OR
             witness_co_sign_user_id <> decided_by_user_id)
        )
    )
);

COMMENT ON TABLE RecoveryRequest IS
  'Two-phase out-of-band recovery ceremony for catastrophic loss '
  '(R11-2 / M2-7). Four CHECK constraints encode the mechanism: '
  'cool-down ≥ 48h, three-channel OOB verification, approver ≠ '
  'requester, status enum. Implements PDF §9.1; the third leg of the '
  '"schema doesn''t weaponize itself against the holder" triad '
  '(entry: R11-4, exit: R11-6, recovery: this).';

-- ----------------------------------------------------------------------------
-- TokenSignature: M:N resolution of IdentityToken → signature (R11-1 / M2-6).
--
-- A token can carry signatures from multiple algorithms during a cryptographic
-- migration window. IdentityToken.algorithm_id is preserved as "originally
-- issued under" metadata for audit; verification reads from TokenSignature.
--
-- TokenSignature is the audit-of-record for migrations. Two triggers
-- (in 06_triggers.sql) enforce the invariants:
--   * enforce_token_has_active_signature — every token must have ≥ 1 active
--     (non-deprecated) signature at all times.
--   * enforce_token_signature_immutability — DELETE is forbidden; UPDATE is
--     confined to setting deprecation_date one-way (NULL → timestamp;
--     cannot un-set or move earlier).
--
-- Closes the cryptographic-diversity leg of the PDF §9 issuer-trust-
-- concentration triad (alongside R11-6 = constitutional limits ✅ and
-- M2-8 = federation, open).
-- ----------------------------------------------------------------------------
-- coverage:exempt — C7 algorithm metadata; partial unique index on token_id; tg_tokensignature_ordering enforces signed_at <= issued_at; see DEVNOTES/ships/token-signature.md
CREATE TABLE TokenSignature (
    signature_id       SERIAL       PRIMARY KEY,
    token_id           INTEGER      NOT NULL
                       REFERENCES IdentityToken(token_id),
    algorithm_id       INTEGER      NOT NULL
                       REFERENCES CryptographicAlgorithm(algorithm_id),
    signature_bytes    BYTEA        NOT NULL,
    signed_at          TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deprecation_date   TIMESTAMP,
        -- NULL = currently active; non-NULL = no longer accepted
        -- after this timestamp. One-way: cannot un-set or move earlier
        -- once recorded (enforced by enforce_token_signature_immutability).

    CONSTRAINT one_signature_per_algorithm_per_token
        UNIQUE (token_id, algorithm_id),

    CONSTRAINT deprecation_after_signed CHECK (
        deprecation_date IS NULL OR deprecation_date > signed_at
    )
);

COMMENT ON TABLE TokenSignature IS
  'M:N resolution of IdentityToken → signature (R11-1 / M2-6). A token '
  'can carry signatures from multiple algorithms during a cryptographic '
  'migration window. Per-token append-only: row is written-once with '
  'one-way deprecation_date. Enforced by triggers '
  'enforce_token_has_active_signature + enforce_token_signature_immutability. '
  'TokenSignature is the audit-of-record for migrations.';

-- ----------------------------------------------------------------------------
-- AnchorBatch: per-batch Merkle commitment of BlockchainAnchor leaves
-- (R10-2 / M2-2). One row per close_anchor_batch invocation. Holds the
-- Merkle root, the hash algorithm used, and (optionally) the external-chain
-- transaction reference once the batch has been pushed to a PQ-capable
-- distributed ledger.
--
-- AnchorBatch is the FIFTH audit-of-record instance in Polaris (after
-- TokenLifecycleEvent, RecoveryRequest, TokenSignature, and Sanctum sessions);
-- see DEVNOTES/audit-of-record.md. The append-only invariant is enforced by
-- extending the reject_audit_modification trigger to this table (in
-- 06_triggers.sql).
--
-- Implements PDF §9 "Centralized trust assumption" — the off-chain audit
-- layer that the relational schema retains under the DID-anchoring direction.
-- Closes the Substrate-D arc to 4/5 done; M2-1 ZK-SNARK remains.
-- ----------------------------------------------------------------------------
-- coverage:exempt — blockchain anchoring queue; AoR (C1) trigger + anchoring.py integration tests cover it
CREATE TABLE AnchorBatch (
    batch_id            SERIAL       PRIMARY KEY,
    merkle_root         VARCHAR(128) NOT NULL,
    algorithm_id        INTEGER      NOT NULL
                        REFERENCES CryptographicAlgorithm(algorithm_id),
    batch_size          INTEGER      NOT NULL CHECK (batch_size > 0),
    created_at          TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    committed_to_chain  BOOLEAN      NOT NULL DEFAULT FALSE,
    external_chain      VARCHAR(40)
                        CHECK (external_chain IS NULL OR
                               external_chain IN ('ALGORAND_PQ','HYPERLEDGER_INDY','CUSTOM_LATTICE')),
    external_chain_tx   VARCHAR(128),

    CONSTRAINT batch_root_is_hex CHECK (merkle_root ~ '^[0-9a-fA-F]+$'),

    CONSTRAINT batch_chain_consistency CHECK (
        (committed_to_chain = FALSE AND external_chain IS NULL AND external_chain_tx IS NULL) OR
        (committed_to_chain = TRUE  AND external_chain IS NOT NULL)
    )
);

COMMENT ON TABLE AnchorBatch IS
  'Per-batch Merkle commitment of BlockchainAnchor leaves (R10-2 / M2-2). '
  'Audit-of-record for batch-time cryptographic commitments. Append-only via '
  'reject_audit_modification trigger. committed_to_chain + external_chain '
  'are operator-set when (and only when) the batch is actually pushed to a '
  'PQ-capable distributed ledger; NOT auto-derived. Implements PDF §9 '
  '"Centralized trust assumption" — the off-chain audit layer under '
  'DID-anchoring. See DEVNOTES/ships/anchoring.md and DEVNOTES/audit-of-record.md.';

-- Now that AnchorBatch exists, add the FK from BlockchainAnchor.batch_id.
ALTER TABLE BlockchainAnchor
    ADD CONSTRAINT fk_blockchainanchor_batch
    FOREIGN KEY (batch_id) REFERENCES AnchorBatch(batch_id);

-- ----------------------------------------------------------------------------
-- AgencyTrustAttestation: federation trust graph (R11-3 / M2-8 / v8.22)
--
-- Cross-agency mutual recognition. An attestation from Agency V toward
-- Agency I for context C means "V accepts I's tokens in context C."
-- Verification of a token issued by I, presented at V, succeeds iff
-- (V == I) OR an active attestation V→I→C exists. NO TRANSITIVE TRUST:
-- the verification query looks for exactly one row; it never recurses.
--
-- AgencyTrustAttestation is the SIXTH audit-of-record instance in
-- Polaris (after TokenLifecycleEvent, RecoveryRequest, TokenSignature,
-- AnchorBatch, and the cognitive-layer Sanctum sessions). Bounded
-- mutation: (revocation_date, revocation_reason) move together once,
-- one-way. Enforced by enforce_attestation_immutability trigger.
--
-- Implements PDF §9.2 "Issuer trust concentration." Closes the
-- issuer-trust-concentration triad to 3/3 (after R11-1 cryptographic
-- diversity + R11-6 constitutional limits).
--
-- v1 ships operator-logged attestations (signed_by AppUser).
-- v2 path: add attestation_signature BYTEA + algorithm_id FK for
-- cryptographically-signed attestations. Column scaffold left out of
-- v1 intentionally — the append-only invariant means existing rows
-- survive a future ALTER TABLE ADD COLUMN cleanly.
-- ----------------------------------------------------------------------------
DROP TABLE IF EXISTS AgencyTrustAttestation CASCADE;
-- coverage:exempt — AoR (C1) enforced by tg_*append_only; federation policy tested in test_app.py
CREATE TABLE AgencyTrustAttestation (
    attestation_id        SERIAL       PRIMARY KEY,
    attesting_agency_id   INTEGER      NOT NULL
                          REFERENCES Agency(agency_id),
    attested_agency_id    INTEGER      NOT NULL
                          REFERENCES Agency(agency_id),
    context_id            INTEGER      NOT NULL
                          REFERENCES VerificationContext(context_id),
    attested_date         TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    valid_until           DATE         NOT NULL,
    signed_by             INTEGER      NOT NULL
                          REFERENCES AppUser(user_id),
    revocation_date       TIMESTAMP,
    revocation_reason     VARCHAR(80),

    CONSTRAINT attestation_no_self_attestation CHECK (
        attesting_agency_id <> attested_agency_id
    ),

    CONSTRAINT attestation_validity_floor CHECK (
        valid_until > attested_date::DATE
    ),

    CONSTRAINT attestation_revocation_consistency CHECK (
        (revocation_date IS NULL  AND revocation_reason IS NULL) OR
        (revocation_date IS NOT NULL AND revocation_reason IS NOT NULL
         AND char_length(revocation_reason) >= 8)
    )
);

COMMENT ON TABLE AgencyTrustAttestation IS
  'Federation trust graph: directional cross-agency attestations '
  '(R11-3 / M2-8 / v8.22). The 6th audit-of-record instance in Polaris. '
  'Append-only via enforce_attestation_immutability trigger; bounded '
  'mutation is the one-way revocation pair (revocation_date, reason). '
  'NO transitive trust — verification reads exactly one row per check. '
  'v1 = operator-logged; v2 path = agency-signed signatures (deferred). '
  'See DEVNOTES/ships/federation.md.';

-- ----------------------------------------------------------------------------
-- TokenStateEpoch + TokenStateEpochLeaf: ZK-SNARK epoch infrastructure
-- (R10-1 / M2-1 / v8.23). The hybrid-Merkle circuit (B3) commits the
-- valid-token set per epoch to a Merkle root; the SNARK proves
-- membership in this root.
--
-- TokenStateEpoch is the SEVENTH audit-of-record instance in Polaris.
-- Append-only via enforce_epoch_immutability trigger. Once an epoch is
-- closed, its merkle_root and committed_count cannot change — every
-- proof issued against the root depends on its immutability.
--
-- TokenStateEpochLeaf is the per-token witness within an epoch. Each
-- row is the leaf hash + proof path for a single token at the
-- snapshot moment. The prover (conceptually, the holder's device)
-- reads its row from this table when generating a ZK proof.
--
-- The merkle_root field uses SHA3-256 hex (operator policy mirroring
-- R10-2). Plonky2 internally uses Poseidon for its circuit hashes,
-- but the schema-level commitment is SHA3-256 for consistency with
-- AnchorBatch. The Rust verifier reconciles these two hash families
-- in the polaris_zk crate.
--
-- Implements PDF §9 ZK-SNARK requirement — closes Substrate-D arc to
-- 5/5. See DEVNOTES/ships/zk-snark.md.
-- ----------------------------------------------------------------------------
-- coverage:exempt — epoch-state Merkle structure; mutations gated by tg_tokenstateepoch_append_only; tested via epoch invariants
CREATE TABLE TokenStateEpoch (
    epoch_id           SERIAL       PRIMARY KEY,
    merkle_root        VARCHAR(128) NOT NULL,
    valid_from         TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    valid_until        TIMESTAMP    NOT NULL,
    committed_count    INTEGER      NOT NULL CHECK (committed_count > 0),
    closed_at          TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    closed_by_user_id  INTEGER      NOT NULL REFERENCES AppUser(user_id),

    CONSTRAINT epoch_root_is_hex CHECK (merkle_root ~ '^[0-9a-fA-F]+$'),

    CONSTRAINT epoch_validity_floor CHECK (valid_until > valid_from),

    CONSTRAINT epoch_committed_count_cap CHECK (committed_count <= 10000)
);

COMMENT ON TABLE TokenStateEpoch IS
  'Per-epoch Merkle commitment over the active-token set (R10-1 / M2-1 / v8.23). '
  'The 7th audit-of-record instance in Polaris. Append-only via '
  'enforce_epoch_immutability trigger. The SNARK proves membership in '
  'merkle_root; verifiers consult this row to check epoch boundary '
  '(valid_until). See DEVNOTES/ships/zk-snark.md.';

-- coverage:exempt — epoch-leaf table; FK to tokenstateepoch; same append-only discipline
CREATE TABLE TokenStateEpochLeaf (
    leaf_id            SERIAL       PRIMARY KEY,
    epoch_id           INTEGER      NOT NULL REFERENCES TokenStateEpoch(epoch_id),
    token_id           INTEGER      NOT NULL REFERENCES IdentityToken(token_id),
    leaf_hash          VARCHAR(128) NOT NULL,
    proof_path         JSONB        NOT NULL,

    CONSTRAINT leaf_hash_is_hex CHECK (leaf_hash ~ '^[0-9a-fA-F]+$'),

    CONSTRAINT uq_one_leaf_per_token_per_epoch
        UNIQUE (epoch_id, token_id)
);

COMMENT ON TABLE TokenStateEpochLeaf IS
  'Per-token witness within an epoch (R10-1 / M2-1 / v8.23). Each row '
  'is the leaf hash and inclusion proof for a token at the epoch '
  'snapshot. The Rust prover reads its row to generate a ZK proof. '
  'Note: v1 stores proof_path in plaintext; v2 would encrypt under '
  'holder key. See DEVNOTES/ships/zk-snark.md.';

-- ----------------------------------------------------------------------------
-- DuressEvent: compulsion-resistance audit-of-record (R11-5 / M2-10 / v8.24)
--
-- Records a detected duress signal — the holder typed their duress code
-- under coercion, and the verifier silently flagged it. The 8th audit-
-- of-record instance. Append-only via reject_audit_modification trigger.
--
-- The coercer-visible side of the verification flow proceeds normally
-- (a VerificationEvent row with outcome=SUCCESS is written). The
-- DuressEvent row is the OUT-OF-BAND alert: visible only to admins/
-- auditors monitoring this table. The operator-visible /verifications
-- list does NOT join to DuressEvent (R6 audit refinement — anti-
-- revealing).
--
-- oob_channel is the v1 reference scope (always 'AUDIT_TABLE'). v2
-- production would add SMS/Slack/SIEM webhook integrations; the schema
-- is ready for them via the CHECK enumeration. oob_notified_at is NULL
-- until a responder acknowledges the alert.
--
-- Implements PDF §9.5 compulsion resistance. The v2 mission-closer.
-- ----------------------------------------------------------------------------
-- coverage:exempt — C1 AoR enforced by tg_duressevent_append_only; UC-10 procedure tested in test_app.py::DuressTests; vocation-critical per MISSION §9.5
CREATE TABLE DuressEvent (
    event_id              SERIAL       PRIMARY KEY,
    token_id              INTEGER      NOT NULL REFERENCES IdentityToken(token_id),
    context_id            INTEGER      NOT NULL REFERENCES VerificationContext(context_id),
    requesting_agency_id  INTEGER      NOT NULL REFERENCES Agency(agency_id),
    event_timestamp       TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    oob_channel           VARCHAR(40)  NOT NULL DEFAULT 'AUDIT_TABLE'
        CHECK (oob_channel IN ('AUDIT_TABLE','STDERR_LOG','SMS_PLACEHOLDER',
                               'SLACK_PLACEHOLDER','SIEM_PLACEHOLDER')),
    oob_notified_at       TIMESTAMP
);

CREATE INDEX idx_duress_event_timestamp ON DuressEvent (event_timestamp DESC);
CREATE INDEX idx_duress_event_unacknowledged ON DuressEvent (event_id)
    WHERE oob_notified_at IS NULL;

COMMENT ON TABLE DuressEvent IS
  'Compulsion-resistance audit-of-record (R11-5 / M2-10 / v8.24). '
  'The 8th audit-of-record instance — append-only via '
  'reject_audit_modification trigger. The OOB alert channel for '
  'detected duress signals. NOT joined into the operator-visible '
  '/verifications list (R6 audit refinement — anti-revealing posture). '
  'See DEVNOTES/ships/duress-codes.md.';

-- ============================================================================
-- END OF 01_schema.sql
-- Twenty-three tables: 4 principals + 1 central artifact + 14 records + 3 junctions
--                      + 1 policy.
-- (GenomicAnchor was added in v8 / M2-4; QuantumObserverBinding in v8.11 /
-- M2-5; IssuerDiscretionPolicy in v8.15 / R11-6 / M2-11;
-- EnrollmentStatusEvent in v8.16 / R11-4 / M2-9;
-- RecoveryRequest in v8.17 / R11-2 / M2-7;
-- TokenSignature in v8.18 / R11-1 / M2-6;
-- AnchorBatch in v8.21 / R10-2 / M2-2;
-- AgencyTrustAttestation in v8.22 / R11-3 / M2-8;
-- TokenStateEpoch + TokenStateEpochLeaf in v8.23 / R10-1 / M2-1;
-- DuressEvent in v8.24 / R11-5 / M2-10 — the v2 mission-closer.)
-- Twenty-eight foreign keys: 5 on IdentityToken (incl. self-referential), 2 on
-- TokenLifecycleEvent, 3 on VerificationEvent, 1 on DeviceBinding, 1 on
-- BlockchainAnchor, 2 on RevocationList, 2 on GenomicAnchor, 2 on each
-- junction table, 1 on IssuerDiscretionPolicy, 2 on EnrollmentStatusEvent,
-- 5 on RecoveryRequest (individual + 2 agencies + 3 AppUser refs +
-- resulting_token; counted with self).
-- Twenty CHECK constraints across enumerated fields, plus two structural
-- CHECK constraints on VerificationEvent (chk_token_time_order,
-- chk_disclosure_token_consistency), three on GenomicAnchor
-- (genomic_hash_is_hex, genomic_hash_length_matches_algorithm,
-- genomic_anchor_refuses_plaintext), three on IssuerDiscretionPolicy
-- (max_revoke_percent range, window_days range, justification length floor),
-- one on EnrollmentStatusEvent (status enum), and four on RecoveryRequest
-- (cooldown_window_minimum, approved_requires_three_channels,
-- approved_after_cooldown, approver_differs_from_requester).
-- The one-active-per-person uniqueness is enforced via a partial unique
-- index defined in 02_indexes.sql.
-- ============================================================================


-- ============================================================================
-- LifecycleArchiveCheckpoint — Arc B Phase 2b · audit-of-record for purges
--
-- v8.87 / closes the deletion-from-hot constitutional carve-out per
-- a recorded decision (Position B, DECIDED).
--
-- When `uc_archive_purge` runs, it appends one row here recording:
--   - the cutoff timestamp (older-than threshold for the purge)
--   - the SHA-256 of the verified archive tarball
--   - the operator user_id who authorized
--   - the row count purged from each audit table
--
-- The checkpoint row IS the audit-of-record for the purge. Combined with
-- the archive tarball at the recorded SHA, it preserves non-repudiation
-- across the deletion boundary: anyone asking "did event X happen?" can
-- consult the checkpoint chain to determine which archive holds it.
--
-- This table is itself append-only (the v8.87 trigger applies).
-- ============================================================================

-- coverage:exempt — v8.87 deletion-from-hot framework; G32 append-only at trigger layer; polaris-archive/purge integration
CREATE TABLE LifecycleArchiveCheckpoint (
    checkpoint_id          BIGSERIAL PRIMARY KEY,
    purged_at              TIMESTAMPTZ  NOT NULL DEFAULT now(),
    cutoff_timestamp       TIMESTAMPTZ  NOT NULL,
    archive_uri            VARCHAR(512) NOT NULL,
    archive_sha256         VARCHAR(64)  NOT NULL,
    actor_user_id          INTEGER      NOT NULL,
    rows_purged_lifecycle      INTEGER  NOT NULL DEFAULT 0,
    rows_purged_verification   INTEGER  NOT NULL DEFAULT 0,
    rows_purged_enrollment     INTEGER  NOT NULL DEFAULT 0,
    rows_purged_authaudit      INTEGER  NOT NULL DEFAULT 0,
    rows_purged_anchorbatch    INTEGER  NOT NULL DEFAULT 0,
    rows_purged_attestation    INTEGER  NOT NULL DEFAULT 0,
    rows_purged_duress         INTEGER  NOT NULL DEFAULT 0,
    rows_purged_total          INTEGER  NOT NULL DEFAULT 0,

    -- The actor must exist as an AppUser (admin role required at the
    -- procedure layer; not enforced via FK to avoid blocking AppUser
    -- deletions, which are themselves rare and audited).
    CONSTRAINT archive_sha256_is_hex CHECK (
        archive_sha256 ~ '^[0-9a-fA-F]{64}$'
    ),
    CONSTRAINT cutoff_in_past CHECK (
        cutoff_timestamp <= now()
    ),
    CONSTRAINT rows_purged_total_nonneg CHECK (
        rows_purged_total >= 0
    )
);
COMMENT ON TABLE LifecycleArchiveCheckpoint IS
    'Audit-of-record for Phase 2b archive-then-delete purges. Append-only. '
    'Each row records the cutoff + archive SHA-256 + operator. Combined with '
    'the offline archive tarball, preserves non-repudiation across the '
    'deletion boundary. Constitutional carve-out: a recorded decision.';
