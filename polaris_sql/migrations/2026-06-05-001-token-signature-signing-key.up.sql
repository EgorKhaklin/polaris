-- ============================================================================
-- 2026-06-05-001-token-signature-signing-key.up.sql
--
-- v9.117 (production-readiness, Wave 2 cont.): store the issuer public key WITH
-- each TokenSignature so verification at use is self-contained — no live
-- POLARIS_PQC_SIGNING_KEY_FILE lookup, and it survives signing-key rotation.
--
-- signing_public_key_hex is nullable and write-once:
--   - NULL     => a deterministic SHA3-256 placeholder signature (no key).
--   - non-NULL => a real ML-DSA-65 signature verifiable against this public key.
-- The null-vs-not status also captures the signature SCHEME, which algorithm_id
-- (the crypto algorithm, C7) cannot express.
--
-- Reversibility: additive, idempotent. ACCESS EXCLUSIVE only briefly (ADD COLUMN
-- with no default is metadata-only in PG11+). The trigger is replaced to make the
-- new column write-once (it is compared IS DISTINCT FROM because it is nullable).
-- ============================================================================

ALTER TABLE TokenSignature
    ADD COLUMN IF NOT EXISTS signing_public_key_hex TEXT;

COMMENT ON COLUMN TokenSignature.signing_public_key_hex IS
  'v9.117. Issuer public key (hex) that produced signature_bytes; NULL for a '
  'deterministic SHA3-256 placeholder. Stored with the signature so verify-at-use '
  'is self-contained and survives key rotation. Write-once.';

-- Replace the immutability trigger so signing_public_key_hex is write-once.
CREATE OR REPLACE FUNCTION enforce_token_signature_immutability()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION
            'DELETE on TokenSignature is forbidden (audit-of-record for migrations)'
            USING ERRCODE = 'insufficient_privilege';
    END IF;

    IF NEW.signature_id      <> OLD.signature_id
       OR NEW.token_id        <> OLD.token_id
       OR NEW.algorithm_id    <> OLD.algorithm_id
       OR NEW.signature_bytes <> OLD.signature_bytes
       OR NEW.signing_public_key_hex IS DISTINCT FROM OLD.signing_public_key_hex
       OR NEW.signed_at       <> OLD.signed_at THEN
        RAISE EXCEPTION
            'TokenSignature is append-only except for deprecation_date'
            USING ERRCODE = 'insufficient_privilege';
    END IF;

    IF OLD.deprecation_date IS NOT NULL THEN
        IF NEW.deprecation_date IS NULL THEN
            RAISE EXCEPTION
                'deprecation_date cannot be un-set once recorded'
                USING ERRCODE = 'insufficient_privilege';
        END IF;
        IF NEW.deprecation_date < OLD.deprecation_date THEN
            RAISE EXCEPTION
                'deprecation_date cannot be moved earlier once recorded'
                USING ERRCODE = 'insufficient_privilege';
        END IF;
    END IF;

    RETURN NEW;
END$$;
