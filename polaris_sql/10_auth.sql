-- ============================================================================
-- POLARIS — IDENTITY TOKEN SYSTEM
-- 10_auth.sql : Seed data for AppUser + AuthAuditLog (+ v2 admin-mediated rows)
--
-- The AppUser + AuthAuditLog DDL now lives in 01_schema.sql (v8.24-fix —
-- promoted there so RecoveryRequest, AgencyTrustAttestation, and
-- TokenStateEpoch can FK to AppUser on a clean-DB initial load). This
-- file is now seed-only — it TRUNCATEs the auth tables and re-inserts
-- the three demo accounts plus the v2 admin-mediated demo rows
-- (RecoveryRequest, AgencyTrustAttestation, TokenStateEpoch +
-- TokenStateEpochLeaf, IdentityToken duress enrollment).
--
-- Design notes:
-- - We DO NOT use PostgreSQL's role/login system for application users. The
--   polaris_app PG role is the sole DB connection identity; application users
--   are rows in AppUser, with passwords hashed via Werkzeug's scrypt.
-- - Three roles: 'admin', 'operator', 'auditor'. Authorization is enforced
--   in the application layer via the @require_role decorator.
-- - Account lockout: 5 failed attempts within 10 minutes locks the account
--   for 15 minutes. Failed login counter resets on a successful login.
-- - TRUNCATE CASCADE makes this file idempotent across re-runs.
-- - v8.97 (Position B WebAuthn-MFA): AppUser gains `webauthn_required_after`
--   (added by migration 2026-05-14-002-operator-webauthn). Seed admin keeps
--   it NULL so dev tests are not time-dependent. Production admin accounts
--   should be created via scripts/polaris-create-operator.sh which sets a
--   30-day deadline by default (per Sanctum §IV.4 architect-recommended
--   resolution). See a recorded decision.
-- ============================================================================

-- TRUNCATE auth tables; CASCADE clears the v2 admin-mediated seed rows
-- (RecoveryRequest, AgencyTrustAttestation, TokenStateEpoch +
-- TokenStateEpochLeaf via signed_by/closed_by_user_id FKs).
TRUNCATE TABLE AuthAuditLog, AppUser RESTART IDENTITY CASCADE;

-- ----------------------------------------------------------------------------
-- Seed three test accounts. Passwords are scrypt hashes of:
--   admin    / Admin@123!    (hash generated via werkzeug)
--   operator / Operator@123! (hash generated via werkzeug)
--   auditor  / Auditor@123!  (hash generated via werkzeug)
-- These are DEVELOPMENT-ONLY credentials. Production deployments must rotate
-- them via the polaris.py CLI (`polaris user-create`, `polaris user-passwd`)
-- or via direct SQL with a freshly-generated hash.
-- ----------------------------------------------------------------------------

INSERT INTO AppUser (username, password_hash, role) VALUES
    ('admin',
     'scrypt:32768:8:1$xpBVtRX9UqF5Ty66$0cee11c89567b0cef1e075cf4ae2dfaeccfd686406d51ab7df1db6de673190ff454f28fea576b9bd0be62d9100a1d3276bbc21b1c58c326640c5126700bfeadd',
     'admin'),
    ('operator',
     'scrypt:32768:8:1$4sRNKl66N1ykoHuB$fd43b1b5b00fdbd6a8c3e098e37e2edfdae7e5b277415b56b02cc6b351f03382c77adbb74fdddfcb1946ceeb348d61f3b9d5edc07f3a1e9a789a9254280fbd01',
     'operator'),
    ('auditor',
     'scrypt:32768:8:1$bIX6L7ow7TwaB9f5$a8b9409f573299825b49f3437148735cad5b4c6797dd3a8b50a859f4fd4c74a2594eacd512bcc3dc274b81fdd284fb09263f6db069e47d31e7e9c41a4727601d',
     'auditor');

-- ----------------------------------------------------------------------------
-- v8.17 / R11-2 / M2-7 — Sample PENDING RecoveryRequest for the
-- /uc9/queue demo. Seeded here (not in 04_data.sql) because the FK
-- requesting_user_id → AppUser needs AppUser rows to exist first;
-- 04_data.sql runs before 10_auth.sql.
--
-- Sample scenario: David Okafor (individual 5) whose T5 was
-- administratively revoked and who is now LAPSED. The operator (user 2)
-- has filed a recovery request that's past its 48h cool-down but no
-- decision has been recorded yet — a perfect queue row for admins to
-- inspect.
--
-- The OOB-channel fields are pre-populated so the demo can exercise
-- the APPROVED path end-to-end. In production these are set by the
-- out-of-band verification processes that happen between phase 1 and
-- phase 2.
-- ----------------------------------------------------------------------------
INSERT INTO RecoveryRequest
    (claimed_individual_id, requested_at, requesting_agency_id,
     requesting_user_id, biometric_verified, sworn_statement_hash,
     witness_agency_id, witness_co_sign_user_id, cooldown_expires_at)
VALUES
    (5,                                                  -- David Okafor
     CURRENT_TIMESTAMP - INTERVAL '50 hours',            -- requested 50h ago
     1,                                                  -- federal issuer
     (SELECT user_id FROM AppUser WHERE username='operator'),
     TRUE,
     '7f3a8e1b4c9d2e5f6a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f',
     3,                                                  -- CA Identity Office witnesses
     (SELECT user_id FROM AppUser WHERE username='admin'),
     CURRENT_TIMESTAMP - INTERVAL '2 hours');            -- cool-down past

-- ----------------------------------------------------------------------------
-- v8.22 / R11-3 / M2-8 — Federation trust graph seed (6 attestations).
-- Seeded here (not in 04_data.sql) for the same reason RecoveryRequest
-- is: signed_by → AppUser(user_id) needs AppUser to exist first.
--
-- The graph makes the existing 8 demo verification events explicable
-- through federation rather than implicit hard-coded trust:
--   TSA (Agency 4) accepts TRAVEL tokens issued by federal (1), PA (2),
--     and CA (3) issuers.
--   Bank (Agency 5) accepts BANKING tokens from the same three issuers.
-- No HEALTHCARE attestations: T2 (Maria, CA-issued) is the only token
-- with HEALTHCARE permissions, and HEALTHCARE verifications happen at
-- same-agency (CA) checkpoints in the demo data — same-agency trust
-- is implicit, no attestation row needed.
-- ----------------------------------------------------------------------------
WITH admin_user AS (SELECT user_id FROM AppUser WHERE username='admin')
INSERT INTO AgencyTrustAttestation
    (attesting_agency_id, attested_agency_id, context_id,
     attested_date, valid_until, signed_by)
VALUES
    -- TSA (4) → federal NY (1), TRAVEL
    (4, 1, (SELECT context_id FROM VerificationContext WHERE context_type='TRAVEL'),
     '2026-01-15 09:00:00', '2027-01-15',
     (SELECT user_id FROM admin_user)),
    -- TSA (4) → PA (2), TRAVEL
    (4, 2, (SELECT context_id FROM VerificationContext WHERE context_type='TRAVEL'),
     '2026-01-15 09:00:00', '2027-01-15',
     (SELECT user_id FROM admin_user)),
    -- TSA (4) → CA (3), TRAVEL
    (4, 3, (SELECT context_id FROM VerificationContext WHERE context_type='TRAVEL'),
     '2026-01-15 09:00:00', '2027-01-15',
     (SELECT user_id FROM admin_user)),
    -- Bank (5) → federal NY (1), BANKING
    (5, 1, (SELECT context_id FROM VerificationContext WHERE context_type='BANKING'),
     '2026-01-15 09:00:00', '2027-01-15',
     (SELECT user_id FROM admin_user)),
    -- Bank (5) → PA (2), BANKING
    (5, 2, (SELECT context_id FROM VerificationContext WHERE context_type='BANKING'),
     '2026-01-15 09:00:00', '2027-01-15',
     (SELECT user_id FROM admin_user)),
    -- Bank (5) → CA (3), BANKING
    (5, 3, (SELECT context_id FROM VerificationContext WHERE context_type='BANKING'),
     '2026-01-15 09:00:00', '2027-01-15',
     (SELECT user_id FROM admin_user));

-- ----------------------------------------------------------------------------
-- v8.23 / R10-1 / M2-1 — Demo ZK epoch (1 epoch over the 3 ACTIVE BANKING
-- tokens).
--
-- Pre-computed by polaris_web/zk.py against the Plonky2 Poseidon hasher:
-- the Merkle root is the commitment for an epoch covering T2 (Maria),
-- T3 (James), T4 (Priya) in context_id=1 (BANKING). Per-leaf inclusion
-- proofs are stored verbatim — the prover for token T2 would read its
-- row from TokenStateEpochLeaf, generate a SNARK proof, and the
-- verifier would check it against the Merkle root.
--
-- Seeded here (not in 04_data.sql) because TokenStateEpoch.closed_by_user_id
-- FKs to AppUser which is created in 10_auth.sql.
-- ----------------------------------------------------------------------------
INSERT INTO TokenStateEpoch
    (merkle_root, valid_from, valid_until, committed_count, closed_at, closed_by_user_id)
VALUES
    ('58789f9222b8c091b73abe60dbc24585a28c7efa99bd73f486559fdb07a6bfa5',
     '2026-02-10 12:00:00',
     '2027-02-10 12:00:00',
     3,
     '2026-02-10 12:00:00',
     (SELECT user_id FROM AppUser WHERE username='admin'));

INSERT INTO TokenStateEpochLeaf (epoch_id, token_id, leaf_hash, proof_path)
VALUES
    (1, 2, 'ffe9e61a4aac4374de645d05d8eadf2138ab3b9d04640ff2f7e395708855cc75',
     '["0f92d06c8910a57cc3cc305d74cc70f91384c96429111df247a62a0b98cb8804","cbf0b121a879450f5f39da11d207acd0b786a47fc525d4ea6f677d8b4e525f87","cc4ff1aad14a1ab6cfb201991b58858df20aa362d79a8fde03e58a3241fc9621","5ae05c29f70ae06164dea29dc57c249a5fc056e9bf94fb4642a53cc70c3a7067"]'::JSONB),
    (1, 3, '0f92d06c8910a57cc3cc305d74cc70f91384c96429111df247a62a0b98cb8804',
     '["ffe9e61a4aac4374de645d05d8eadf2138ab3b9d04640ff2f7e395708855cc75","cbf0b121a879450f5f39da11d207acd0b786a47fc525d4ea6f677d8b4e525f87","cc4ff1aad14a1ab6cfb201991b58858df20aa362d79a8fde03e58a3241fc9621","5ae05c29f70ae06164dea29dc57c249a5fc056e9bf94fb4642a53cc70c3a7067"]'::JSONB),
    (1, 4, '0fb33e4fa39de33481b6246daf449a70aeb969f2260202d7838aec546db77e63',
     '["0000000000000000000000000000000000000000000000000000000000000000","f1fa74f75873adff79a53c306bdbe258abe66c869918c9ba4a7e54a1ba26e956","cc4ff1aad14a1ab6cfb201991b58858df20aa362d79a8fde03e58a3241fc9621","5ae05c29f70ae06164dea29dc57c249a5fc056e9bf94fb4642a53cc70c3a7067"]'::JSONB);

-- ----------------------------------------------------------------------------
-- v8.24 / R11-5 / M2-10 — Demo duress-code enrollment.
--
-- Maria's T2 (BANKING-eligible ACTIVE token) gets a demo duress code
-- enrolled. The plaintext code is '911911' — documented here in the
-- reference impl because the seed is a teaching aid. The hash below is
-- the Werkzeug scrypt commitment; the constant-time check_password_hash
-- function validates a typed code against it.
--
-- Seeded here (not in 04_data.sql) for symmetry with the other v8.2x
-- post-load seeds (RecoveryRequest, AgencyTrustAttestation,
-- TokenStateEpoch). No FK to AppUser, but the convention is to keep
-- "advanced feature" enrollment in the auth/admin file.
-- ----------------------------------------------------------------------------
UPDATE IdentityToken
   SET duress_code_hash = 'scrypt:32768:8:1$Fo0c5pSq6RSNmuh6$decd33dc8ee41de9a89dc6b6acf0832df8dec18c6b052374463cf505627749a3924e827fdb3899ee9a3b1527a8d97e8dd0b1def5abed01dca00c94b9fff6df8f'
 WHERE token_id = 2;

-- ============================================================================
-- END OF 10_auth.sql
-- ============================================================================
