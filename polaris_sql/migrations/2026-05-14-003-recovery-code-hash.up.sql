-- ============================================================================
-- 2026-05-14-003-recovery-code-hash.up.sql
--
-- v9.02 / closes the v8.97 Sanctum §V deferred-pending-demand item:
-- the in-app recovery-code verification flow.
--
-- v8.97 shipped:
--   - polaris-generate-recovery-code.sh (mnemonic generator that
--     prints a 16-word ~128-bit BIP-39-style code + SHA-256 digest)
--   - polaris-recover-admin.sh (second-admin pairing flow)
--
-- v8.97 §V explicitly deferred:
--   - "the in-app verification flow (recovery_code_hash storage
--     column + the --recovery-code argument on polaris-recover-
--     admin.sh) is deferred to a follow-up gated on operator demand"
--
-- v9.02 closes this gap. The matching artifacts in the same ship:
--   - polaris-generate-recovery-code.sh gains --bind-to <username>
--     to persist the SHA-256 hash into AppUser.recovery_code_hash
--   - polaris-recover-admin.sh gains --recovery-code [-|<code>] to
--     verify a supplied mnemonic against the stored hash, opening
--     the emergency-login window without requiring a second admin
--
-- ADDS: AppUser.recovery_code_hash VARCHAR(64) NULL — SHA-256 of the
--       printed mnemonic; NULL = no recovery code bound to this user
--       (the user relies on second-admin pairing exclusively).
--
-- REVERSIBLE: yes (DROP COLUMN in .down.sql; loses bound recovery
-- codes — operators MUST re-bind via polaris-generate-recovery-code.sh
-- after revert. Documented in .down.sql header).
-- LOCK: brief ACCESS EXCLUSIVE on AppUser; column add is fast.
-- ADDITIVE (data side): yes — no existing rows mutated.
-- ============================================================================

-- Idempotent: recovery_code_hash (+ its CHECK) is also declared in
-- 01_schema.sql so the canonical schema is complete; on a fresh 00_load_all
-- build it already exists and these are no-ops, while on an older deployed DB
-- they add it.
ALTER TABLE AppUser
    ADD COLUMN IF NOT EXISTS recovery_code_hash VARCHAR(64);

-- The hash is stored hex-encoded SHA-256 of the operator's printed
-- mnemonic (joined with single spaces, lowercased; matching the
-- generator's digest computation). NULL is the default — operators
-- bind a code via `polaris-generate-recovery-code.sh --bind-to
-- <username>` only when solo-deployment recovery is required.
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'chk_recovery_code_hash_format'
    ) THEN
        ALTER TABLE AppUser
            ADD CONSTRAINT chk_recovery_code_hash_format CHECK (
                recovery_code_hash IS NULL
                OR recovery_code_hash ~ '^[0-9a-f]{64}$'
            );
    END IF;
END $$;

COMMENT ON COLUMN AppUser.recovery_code_hash IS
    'SHA-256 (lowercase hex) of operator-printed recovery mnemonic. '
    'v9.02 / Sanctum 2026-05-14-webauthn-operator-auth.md §V deferred-'
    'item closure. NULL = operator relies on second-admin pairing '
    'recovery flow exclusively (polaris-recover-admin.sh --authorizing-'
    'user-id N). Non-NULL = polaris-recover-admin.sh --recovery-code '
    'verifies against this hash + opens the emergency-login window.';
