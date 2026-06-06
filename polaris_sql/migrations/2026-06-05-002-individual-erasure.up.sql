-- ============================================================================
-- 2026-06-05-002-individual-erasure.up.sql
--
-- v9.125 (production-readiness, Wave 3): the right-to-erasure mechanism. Polaris
-- cannot DELETE a holder (C1 is non-negotiable); the supported erasure is to
-- pseudonymize Individual.legal_name. This migration adds:
--   - IndividualErasureEvent (append-only log of pseudonymizations: who/when/why,
--     NOT the prior name or a hash of it),
--   - its append-only trigger + the polaris_app REVOKE,
--   - uc_pseudonymize_individual (the only writer).
--
-- Reversibility: additive. The table + procedure are dropped by the .down. No
-- existing data is rewritten. Idempotent (IF NOT EXISTS / OR REPLACE / DROP-then-
-- CREATE) so --sync-objects re-application is safe.
-- ============================================================================

CREATE TABLE IF NOT EXISTS IndividualErasureEvent (
    erasure_id          SERIAL       PRIMARY KEY,
    individual_id       INTEGER      NOT NULL REFERENCES Individual(individual_id),
    pseudonym_assigned  VARCHAR(200) NOT NULL,
    erased_by_user_id   INTEGER      NOT NULL REFERENCES AppUser(user_id),
    reason              VARCHAR(200) NOT NULL
        CHECK (char_length(trim(reason)) >= 1),
    event_timestamp     TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_erasure_individual ON IndividualErasureEvent(individual_id);

COMMENT ON TABLE IndividualErasureEvent IS
  'Append-only log of right-to-erasure pseudonymizations (v9.125). One row per '
  'time an operator pseudonymizes an Individual.legal_name via '
  'uc_pseudonymize_individual. Records who/when/why, NOT the prior name or a '
  'hash of it (storing either would defeat the erasure). The append-only '
  'invariant is enforced by reject_audit_modification; see PRIVACY.md.';

-- Append-only: the erasure record is itself audit-of-record.
DROP TRIGGER IF EXISTS trg_erasure_append_only ON IndividualErasureEvent;
CREATE TRIGGER trg_erasure_append_only
    BEFORE UPDATE OR DELETE ON IndividualErasureEvent
    FOR EACH ROW
    EXECUTE FUNCTION reject_audit_modification();

-- polaris_app INSERTs an erasure record but must not edit or remove one.
REVOKE UPDATE, DELETE ON IndividualErasureEvent FROM polaris_app;

-- The only writer. Pseudonymizes legal_name and records the act. Admin-gated by
-- parameter; issues no DELETE; the Individual row and all audit/token references
-- survive (non-repudiation). Not SECURITY DEFINER: polaris_app holds UPDATE on
-- Individual and INSERT on the event table, so no elevation is needed.
CREATE OR REPLACE PROCEDURE uc_pseudonymize_individual(
    p_individual_id   INTEGER,
    p_actor_user_id   INTEGER,
    p_reason          VARCHAR(200)
)
LANGUAGE plpgsql AS $$
DECLARE
    v_actor_role   VARCHAR(64);
    v_actor_active BOOLEAN;
    v_current_name VARCHAR(200);
    v_already      INTEGER;
    v_pseudonym    VARCHAR(200) := 'PSEUDONYMIZED-' || p_individual_id;
BEGIN
    SELECT legal_name INTO v_current_name
        FROM Individual WHERE individual_id = p_individual_id;
    IF v_current_name IS NULL THEN
        RAISE EXCEPTION 'uc_pseudonymize_individual: individual_id (%) does not exist.',
            p_individual_id
            USING ERRCODE = 'foreign_key_violation';
    END IF;

    SELECT role, is_active INTO v_actor_role, v_actor_active
        FROM AppUser WHERE user_id = p_actor_user_id;
    IF v_actor_role IS NULL THEN
        RAISE EXCEPTION 'uc_pseudonymize_individual: actor_user_id (%) does not exist.',
            p_actor_user_id
            USING ERRCODE = 'foreign_key_violation';
    END IF;
    IF v_actor_role <> 'admin' THEN
        RAISE EXCEPTION 'uc_pseudonymize_individual: actor_user_id (%) has role %, must be admin.',
            p_actor_user_id, v_actor_role
            USING ERRCODE = 'insufficient_privilege';
    END IF;
    IF v_actor_active IS NOT TRUE THEN
        RAISE EXCEPTION 'uc_pseudonymize_individual: actor_user_id (%) is not an active account.',
            p_actor_user_id
            USING ERRCODE = 'insufficient_privilege';
    END IF;

    IF p_reason IS NULL OR char_length(trim(p_reason)) = 0 THEN
        RAISE EXCEPTION 'uc_pseudonymize_individual: a non-empty reason is required.'
            USING ERRCODE = 'check_violation';
    END IF;

    -- Refuse to double-erase by consulting the AUTHORITATIVE log, not the name
    -- (legal_name has no format constraint beyond non-empty).
    SELECT count(*) INTO v_already
        FROM IndividualErasureEvent WHERE individual_id = p_individual_id;
    IF v_already > 0 THEN
        RAISE EXCEPTION 'uc_pseudonymize_individual: individual_id (%) is already pseudonymized (% prior record(s)).',
            p_individual_id, v_already
            USING ERRCODE = 'check_violation';
    END IF;

    UPDATE Individual
        SET legal_name = v_pseudonym
        WHERE individual_id = p_individual_id;

    -- No RAISE NOTICE: the IndividualErasureEvent row is the authoritative
    -- record; re-emitting it to the server log is an uncontrolled sink.
    INSERT INTO IndividualErasureEvent
        (individual_id, pseudonym_assigned, erased_by_user_id, reason)
    VALUES
        (p_individual_id, v_pseudonym, p_actor_user_id, trim(p_reason));
END$$;
