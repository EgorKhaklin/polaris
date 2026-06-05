-- ============================================================================
-- 2026-06-05-001-token-signature-signing-key.down.sql
--
-- Revert v9.117: restore the pre-signing_public_key_hex immutability trigger and
-- drop the column. Dropping the column discards the stored issuer public keys;
-- after revert, verification falls back to the live trust anchor only.
-- ============================================================================

-- Restore the immutability trigger to its pre-v9.117 form (no signing_public_key_hex check).
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

ALTER TABLE TokenSignature DROP COLUMN IF EXISTS signing_public_key_hex;
