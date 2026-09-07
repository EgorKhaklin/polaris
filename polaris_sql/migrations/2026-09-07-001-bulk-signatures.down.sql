-- ============================================================================
-- 2026-09-07-001-bulk-signatures.down.sql  (revert of the .up)
-- Restores the prior uc_bulk_issue (placeholder signature) and drops the
-- staging signature columns. For rollback only; the prior behavior is the very
-- integrity gap the .up closes.
-- ============================================================================

CREATE OR REPLACE PROCEDURE uc_bulk_issue(p_batch_id INTEGER, INOUT p_rows_issued INTEGER DEFAULT NULL)
LANGUAGE plpgsql AS $$
DECLARE
    v_agency INTEGER; v_algo INTEGER; v_auth VARCHAR(20); v_n INTEGER;
BEGIN
    SELECT issuing_agency_id, algorithm_id INTO v_agency, v_algo
      FROM BulkEnrollmentBatch WHERE batch_id = p_batch_id;
    IF NOT FOUND THEN RAISE EXCEPTION 'uc_bulk_issue: batch % does not exist', p_batch_id; END IF;
    IF EXISTS (SELECT 1 FROM BulkEnrollmentBatch WHERE batch_id = p_batch_id AND issued_at IS NOT NULL) THEN
        RAISE EXCEPTION 'uc_bulk_issue: batch % was already issued', p_batch_id USING ERRCODE = 'invalid_parameter_value';
    END IF;

    -- the same authorization uc1 checks, once for the batch (one agency, one algorithm)
    SELECT authorization_type INTO v_auth FROM AgencyAlgorithmAuth
     WHERE agency_id = v_agency AND algorithm_id = v_algo;
    IF NOT FOUND OR v_auth NOT IN ('ISSUE','BOTH') THEN
        RAISE EXCEPTION 'uc_bulk_issue: agency % is not authorized to issue under algorithm %', v_agency, v_algo
            USING ERRCODE = 'insufficient_privilege';
    END IF;
    PERFORM 1 FROM CryptographicAlgorithm WHERE algorithm_id = v_algo
       AND (deprecation_date IS NULL OR deprecation_date > CURRENT_TIMESTAMP);
    IF NOT FOUND THEN
        RAISE EXCEPTION 'uc_bulk_issue: algorithm % is deprecated; cannot issue under it', v_algo
            USING ERRCODE = 'invalid_parameter_value';
    END IF;

    SELECT count(*) INTO v_n FROM BulkEnrollmentStaging WHERE batch_id = p_batch_id;
    IF v_n = 0 THEN RAISE EXCEPTION 'uc_bulk_issue: batch % has no staged rows', p_batch_id; END IF;

    -- Pre-assign the primary keys so the multi-table inserts correlate set-based.
    -- A staged individual_id LEFT NULL is a new person (first enrollment): it gets
    -- a fresh id and a new Individual row. A staged individual_id SET correlates the
    -- row to an existing person (a re-card of someone whose prior token is no longer
    -- active): it keeps its id and inserts no duplicate Individual. C3
    -- (uq_one_active_per_person) is what enforces "no longer active" -- a re-card of
    -- someone who still holds an active token fails at activation and rolls the batch
    -- back, exactly as two staged rows for one person do.
    UPDATE BulkEnrollmentStaging
       SET individual_id = COALESCE(individual_id, nextval(pg_get_serial_sequence('individual','individual_id')))
     WHERE batch_id = p_batch_id;
    INSERT INTO Individual (individual_id, legal_name, date_of_birth, jurisdiction)
      SELECT individual_id, legal_name, date_of_birth, jurisdiction FROM BulkEnrollmentStaging s
       WHERE batch_id = p_batch_id
         AND NOT EXISTS (SELECT 1 FROM Individual i WHERE i.individual_id = s.individual_id);
    -- (the AFTER-INSERT trigger seeds a NOT_ENROLLED EnrollmentStatusEvent per NEW row;
    --  correlated rows keep the existing person's enrollment history untouched)

    UPDATE BulkEnrollmentStaging SET token_id = nextval(pg_get_serial_sequence('identitytoken','token_id'))
     WHERE batch_id = p_batch_id;
    INSERT INTO IdentityToken (token_id, token_value, physical_serial, hardware_model, biometric_binding_type,
                               individual_id, issuing_agency_id, algorithm_id, status, issued_date, expiration_date,
                               biometric_enrolled_date, enrollment_witness_agency_id, liveness_check_type)
      SELECT token_id, token_value, physical_serial, hardware_model, biometric_binding_type,
             individual_id, v_agency, v_algo, 'RESERVE', CURRENT_TIMESTAMP, (CURRENT_DATE + INTERVAL '10 years')::date,
             CURRENT_TIMESTAMP, witness_agency_id, liveness_check_type
        FROM BulkEnrollmentStaging WHERE batch_id = p_batch_id;
    -- (FKs, CHECKs, and the token_value/physical_serial UNIQUE constraints hold per row)

    INSERT INTO TokenSignature (token_id, algorithm_id, signature_bytes, signing_public_key_hex)
      SELECT token_id, v_algo, ('BULK_ISSUE_' || token_id::TEXT)::BYTEA, NULL
        FROM BulkEnrollmentStaging WHERE batch_id = p_batch_id;
    -- (enforce_token_has_active_signature is satisfied: every token gets a signature)

    INSERT INTO TokenLifecycleEvent (token_id, actor_agency_id, event_type, reason_code)
      SELECT token_id, v_agency, 'ISSUED', 'BULK_ENROLLMENT' FROM BulkEnrollmentStaging WHERE batch_id = p_batch_id;

    -- Activate. The audit trigger writes an ACTIVATED lifecycle row per token from
    -- the batch's agency (one agency per batch), and the state-machine trigger
    -- validates RESERVE -> ACTIVE per row.
    PERFORM set_config('polaris.actor_agency_id', v_agency::TEXT, true);
    PERFORM set_config('polaris.reason_code', 'BULK_POST_ENROLLMENT', true);
    UPDATE IdentityToken t SET status = 'ACTIVE', activated_date = CURRENT_TIMESTAMP
      FROM BulkEnrollmentStaging s WHERE t.token_id = s.token_id AND s.batch_id = p_batch_id;
    -- (uq_one_active_per_person, C3, holds across the batch: two active tokens for
    --  one person fail here and roll back every row)

    INSERT INTO TokenPermission (token_id, context_id, permission_level)
      SELECT token_id, unnest(permitted_contexts), 'VERIFY' FROM BulkEnrollmentStaging WHERE batch_id = p_batch_id;

    UPDATE BulkEnrollmentBatch SET issued_at = CURRENT_TIMESTAMP, rows_issued = v_n WHERE batch_id = p_batch_id;
    p_rows_issued := v_n;
END $$;

ALTER TABLE BulkEnrollmentStaging
    DROP COLUMN IF EXISTS signature_bytes,
    DROP COLUMN IF EXISTS signing_public_key_hex;
