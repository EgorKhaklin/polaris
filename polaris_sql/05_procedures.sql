-- ============================================================================
-- AI-context: stored procedures with concurrency hazards. Read before editing:
--     ../DEVNOTES/concurrency.md             ← hazard inventory + protections
--     ../patterns/concurrency-fix.md         ← canonical recipe
--     ../patterns/new-uc-procedure.md        ← if adding a new use case
--   Or:  ../scripts/ai-where.sh polaris_sql/05_procedures.sql
-- After editing, RELOAD: psql -d $DB -f polaris_sql/05_procedures.sql
-- ============================================================================

-- ============================================================================
-- POLARIS — IDENTITY TOKEN SYSTEM
-- 05_procedures.sql : Stored procedures for the use cases
--
-- Stored procedures wrap the four UCs that perform multi-statement state
-- transitions, providing the production enforcement mechanism described in
-- the report's "Production Enforcement of the State Machine" subsection
-- (Appendix A). Each procedure is the named, logged, atomic operation that
-- application code should call rather than issuing direct UPDATE/INSERT.
--
-- UC-2 and UC-3 (verification) are not wrapped because they involve only a
-- single INSERT into VerificationEvent; the integrity is enforced by the
-- disclosure-consistency CHECK constraint, not by procedural logic.
-- UC-6 (algorithm migration audit) is read-only; expressed as a query in
-- 07_queries.sql instead of a procedure.
-- ============================================================================

-- ----------------------------------------------------------------------------
-- UC-1: New Token Issuance and Initial Activation
--   Argument flow:
--     p_legal_name, p_dob, p_jurisdiction      -- individual identification
--     p_issuing_agency_id                      -- the agency performing issuance
--     p_algorithm_id                           -- the signing algorithm
--     p_biometric_binding_type                 -- enrollment biometric method
--     p_witness_agency_id                      -- enrollment witness
--     p_liveness_check_type                    -- enrollment liveness method
--     p_token_value, p_physical_serial         -- canonical and hardware serials
--     p_permitted_contexts                     -- ARRAY of context_ids to grant VERIFY on
--   Returns: token_id of the new ACTIVE token.
--
--   Validates that issuing agency holds ISSUE or BOTH on the chosen algorithm
--   before any writes (UC-1 step 1). Enforces the full transaction in one
--   procedure so partial-state issuance is impossible.
-- ----------------------------------------------------------------------------

CREATE OR REPLACE FUNCTION uc1_issue_and_activate(
    p_legal_name              VARCHAR(200),
    p_dob                     DATE,
    p_jurisdiction            VARCHAR(10),
    p_issuing_agency_id       INTEGER,
    p_algorithm_id            INTEGER,
    p_biometric_binding_type  VARCHAR(20),
    p_witness_agency_id       INTEGER,
    p_liveness_check_type     VARCHAR(20),
    p_token_value             VARCHAR(128),
    p_physical_serial         VARCHAR(64),
    p_hardware_model          VARCHAR(50),
    p_permitted_contexts      INTEGER[]
) RETURNS INTEGER
LANGUAGE plpgsql
AS $$
DECLARE
    v_individual_id  INTEGER;
    v_token_id       INTEGER;
    v_auth_type      VARCHAR(20);
    v_context_id     INTEGER;
BEGIN
    -- Step 1: validate the issuing agency's authorization (UC-1 step 1).
    SELECT authorization_type INTO v_auth_type
    FROM AgencyAlgorithmAuth
    WHERE agency_id    = p_issuing_agency_id
      AND algorithm_id = p_algorithm_id;
    IF NOT FOUND OR v_auth_type NOT IN ('ISSUE','BOTH') THEN
        RAISE EXCEPTION 'Agency % is not authorized to issue under algorithm %',
            p_issuing_agency_id, p_algorithm_id
            USING ERRCODE = 'insufficient_privilege';
    END IF;

    -- Step 2: insert Individual if no existing record (UC-1 step 2).
    --   The application normally checks for an existing individual first;
    --   this procedure simplifies by always inserting a new individual,
    --   matching the UC-1 sample transaction in the report.
    INSERT INTO Individual (legal_name, date_of_birth, jurisdiction)
    VALUES (p_legal_name, p_dob, p_jurisdiction)
    RETURNING individual_id INTO v_individual_id;

    -- Step 3-4: insert IdentityToken in RESERVE + lifecycle ISSUED (UC-1 steps 3-4).
    INSERT INTO IdentityToken
        (token_value, physical_serial, hardware_model,
         biometric_binding_type, individual_id, issuing_agency_id, algorithm_id,
         status, issued_date, expiration_date)
    VALUES
        (p_token_value, p_physical_serial, p_hardware_model,
         p_biometric_binding_type, v_individual_id, p_issuing_agency_id, p_algorithm_id,
         'RESERVE', CURRENT_TIMESTAMP, (CURRENT_DATE + INTERVAL '10 years')::date)
    RETURNING token_id INTO v_token_id;

    -- R11-1 / M2-6: issue a TokenSignature row alongside the IdentityToken
    -- so the M:N invariant (every token has ≥ 1 active signature) is
    -- satisfied from the moment the token exists. In production, the
    -- signature bytes would come from a hardware-attested signing
    -- ceremony; for the reference implementation we record a deterministic
    -- placeholder. The procedure does not accept a signature_bytes
    -- parameter because the cryptographic-ceremony layer is outside the
    -- database; future versions could lift this to a CLI param.
    INSERT INTO TokenSignature (token_id, algorithm_id, signature_bytes)
    VALUES (v_token_id, p_algorithm_id,
            ('UC1_ISSUE_PLACEHOLDER_' || v_token_id::TEXT)::BYTEA);

    INSERT INTO TokenLifecycleEvent
        (token_id, actor_agency_id, event_type, reason_code)
    VALUES
        (v_token_id, p_issuing_agency_id, 'ISSUED', 'INITIAL_ENROLLMENT');

    -- Step 5: hardware-binding ceremony (UC-1 step 5).
    --   Update biometric metadata fields and witness reference.
    UPDATE IdentityToken
       SET biometric_enrolled_date      = CURRENT_TIMESTAMP,
           enrollment_witness_agency_id = p_witness_agency_id,
           liveness_check_type          = p_liveness_check_type
     WHERE token_id = v_token_id;

    -- Step 6-7: activate (UC-1 steps 6-7). Set the audit-trigger context GUCs
    -- so the AFTER UPDATE trigger writes a properly-attributed lifecycle event.
    -- This replaces the explicit INSERT INTO TokenLifecycleEvent that used to
    -- live here — the database now guarantees the audit row.
    PERFORM set_config('polaris.actor_agency_id', p_issuing_agency_id::TEXT, true);
    PERFORM set_config('polaris.reason_code',     'POST_BIOMETRIC_ENROLLMENT', true);

    UPDATE IdentityToken
       SET status         = 'ACTIVE',
           activated_date = CURRENT_TIMESTAMP
     WHERE token_id = v_token_id;

    -- Step 8: insert default permissions (UC-1 step 8).
    FOREACH v_context_id IN ARRAY p_permitted_contexts LOOP
        INSERT INTO TokenPermission (token_id, context_id, permission_level)
        VALUES (v_token_id, v_context_id, 'VERIFY');
    END LOOP;

    RETURN v_token_id;
END;
$$;

COMMENT ON FUNCTION uc1_issue_and_activate IS
  'UC-1: New Token Issuance and Initial Activation. Atomic over Individual '
  'insert, IdentityToken creation, biometric binding, activation, and '
  'permission grants. Validates agency authorization before any writes.';

-- ----------------------------------------------------------------------------
-- UC-4: Reserve Token Activation After Loss
--   Argument flow:
--     p_lost_token_id        -- the active token being lost
--     p_actor_agency_id      -- the agency performing the action
--     p_reason_code          -- LOST, STOLEN, COMPROMISED, etc.
--     p_reserve_token_id     -- the reserve to promote
--     p_published_location   -- CRL distribution URL
--   Returns: token_id of the newly active token (same as p_reserve_token_id).
--
--   Order of operations: transition lost token to terminal status FIRST
--   (releasing it from the partial unique index), then promote the reserve.
--   This avoids needing DEFERRABLE constraint semantics; the partial unique
--   index on status='ACTIVE' is never violated mid-transaction.
-- ----------------------------------------------------------------------------

CREATE OR REPLACE FUNCTION uc4_activate_reserve(
    p_lost_token_id      INTEGER,
    p_actor_agency_id    INTEGER,
    p_reason_code        VARCHAR(40),
    p_reserve_token_id   INTEGER,
    p_published_location VARCHAR(300)
) RETURNS INTEGER
LANGUAGE plpgsql
AS $$
DECLARE
    v_lost_individual_id     INTEGER;
    v_reserve_individual_id  INTEGER;
    v_lost_status            VARCHAR(20);
    v_reserve_status         VARCHAR(20);
    v_terminal_status        VARCHAR(20);
    v_lifecycle_event_type   VARCHAR(20);
BEGIN
    -- Validate: lost token is currently ACTIVE.
    SELECT individual_id, status INTO v_lost_individual_id, v_lost_status
    FROM IdentityToken WHERE token_id = p_lost_token_id;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Lost token % does not exist', p_lost_token_id
            USING ERRCODE = 'no_data_found';
    END IF;
    IF v_lost_status <> 'ACTIVE' THEN
        RAISE EXCEPTION 'Token % is not ACTIVE (current status: %)',
            p_lost_token_id, v_lost_status
            USING ERRCODE = 'invalid_parameter_value';
    END IF;

    -- Validate: reserve token is currently RESERVE and belongs to same individual.
    SELECT individual_id, status INTO v_reserve_individual_id, v_reserve_status
    FROM IdentityToken WHERE token_id = p_reserve_token_id;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Reserve token % does not exist', p_reserve_token_id
            USING ERRCODE = 'no_data_found';
    END IF;
    IF v_reserve_status <> 'RESERVE' THEN
        RAISE EXCEPTION 'Token % is not in RESERVE state (current status: %)',
            p_reserve_token_id, v_reserve_status
            USING ERRCODE = 'invalid_parameter_value';
    END IF;
    IF v_reserve_individual_id <> v_lost_individual_id THEN
        RAISE EXCEPTION 'Reserve token % belongs to a different individual than lost token %',
            p_reserve_token_id, p_lost_token_id
            USING ERRCODE = 'integrity_constraint_violation';
    END IF;

    -- Map reason_code to terminal status and lifecycle event_type.
    v_terminal_status := CASE p_reason_code
        WHEN 'LOST'         THEN 'LOST'
        WHEN 'STOLEN'       THEN 'LOST'
        WHEN 'COMPROMISED'  THEN 'REVOKED'
        WHEN 'SUPERSEDED'   THEN 'REVOKED'
        WHEN 'ADMINISTRATIVE' THEN 'REVOKED'
        ELSE 'REVOKED'
    END;
    v_lifecycle_event_type := CASE v_terminal_status
        WHEN 'LOST'    THEN 'LOST'
        WHEN 'REVOKED' THEN 'REVOKED'
    END;

    -- Concurrency hardening: serialize all UC-4 activations for the same
    -- holder by acquiring a row lock on the Individual record. Two operators
    -- running this procedure simultaneously for the same holder will queue;
    -- the second one observes the post-T1 state and either succeeds or fails
    -- cleanly with a domain error rather than producing inconsistent data.
    PERFORM 1
       FROM Individual
      WHERE individual_id = v_lost_individual_id
      FOR UPDATE;

    -- Compute the next activation sequence atomically inside the locked
    -- region. The previous code hardcoded `activation_sequence = 2`, which
    -- was wrong for any holder past their second active token AND raced
    -- if two procedures read the table at the same time. Now we read the
    -- max under the row lock above, eliminating both bugs.
    DECLARE v_next_seq INTEGER; BEGIN
    SELECT COALESCE(MAX(activation_sequence), 0) + 1
      INTO v_next_seq
      FROM IdentityToken
     WHERE individual_id = v_lost_individual_id;

    -- Step 1: transition the lost token to its terminal status FIRST.
    -- This releases the partial unique index on status='ACTIVE' for this individual.
    -- Set audit-trigger GUCs so the AFTER UPDATE trigger writes a properly-
    -- attributed lifecycle event automatically.
    PERFORM set_config('polaris.actor_agency_id', p_actor_agency_id::TEXT, true);
    PERFORM set_config('polaris.reason_code',     'HOLDER_REPORTED_' || p_reason_code, true);

    UPDATE IdentityToken
       SET status = v_terminal_status
     WHERE token_id = p_lost_token_id;

    -- Step 2: publish to revocation list.
    INSERT INTO RevocationList
        (token_id, revoked_by_agency_id, effective_date, reason_code, published_location)
    VALUES
        (p_lost_token_id, p_actor_agency_id, CURRENT_DATE,
         p_reason_code, p_published_location);

    -- Step 3: promote the reserve to ACTIVE with predecessor pointer.
    -- Update the GUC reason for this transition; agency stays the same.
    PERFORM set_config('polaris.reason_code', 'RESERVE_PROMOTION', true);

    UPDATE IdentityToken
       SET status                 = 'ACTIVE',
           predecessor_token_id   = p_lost_token_id,
           activation_sequence    = v_next_seq,
           activated_date         = CURRENT_TIMESTAMP
     WHERE token_id = p_reserve_token_id;

    RETURN p_reserve_token_id;
    END;
END;
$$;

COMMENT ON FUNCTION uc4_activate_reserve IS
  'UC-4: Reserve Token Activation After Loss. Transitions the lost token to '
  'its terminal status, publishes to RevocationList, and promotes the reserve '
  'to ACTIVE with predecessor_token_id pointing to the lost token. The order '
  '(transition lost first, then promote reserve) avoids the need for '
  'DEFERRABLE constraint semantics.';

-- ----------------------------------------------------------------------------
-- UC-5: Device Binding (Digital Projection to a Personal Device)
--   Argument flow:
--     p_token_id              -- the token to bind to
--     p_device_type           -- PHONE, TABLET, WATCH
--     p_device_fingerprint    -- secure-enclave-attested fingerprint
--     p_binding_method        -- enclave technology
--     p_validity_months       -- binding lifetime in months
--   Returns: binding_id.
-- ----------------------------------------------------------------------------

CREATE OR REPLACE FUNCTION uc5_bind_device(
    p_token_id           INTEGER,
    p_device_type        VARCHAR(20),
    p_device_fingerprint VARCHAR(128),
    p_binding_method     VARCHAR(40),
    p_validity_months    INTEGER DEFAULT 12
) RETURNS INTEGER
LANGUAGE plpgsql
AS $$
DECLARE
    v_token_status VARCHAR(20);
    v_binding_id   INTEGER;
BEGIN
    -- Validate: token is ACTIVE.
    SELECT status INTO v_token_status
    FROM IdentityToken WHERE token_id = p_token_id;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Token % does not exist', p_token_id
            USING ERRCODE = 'no_data_found';
    END IF;
    IF v_token_status <> 'ACTIVE' THEN
        RAISE EXCEPTION 'Token % is not ACTIVE (current status: %); cannot bind device',
            p_token_id, v_token_status
            USING ERRCODE = 'invalid_parameter_value';
    END IF;

    INSERT INTO DeviceBinding
        (token_id, device_type, device_fingerprint, binding_method,
         authorized_date, expires_date, status)
    VALUES
        (p_token_id, p_device_type, p_device_fingerprint, p_binding_method,
         CURRENT_TIMESTAMP,
         CURRENT_TIMESTAMP + (p_validity_months || ' months')::INTERVAL,
         'ACTIVE')
    RETURNING binding_id INTO v_binding_id;

    INSERT INTO TokenLifecycleEvent
        (token_id, actor_agency_id, event_type, reason_code)
    VALUES
        (p_token_id, NULL, 'DEVICE_BOUND',
         'DEVICE_TYPE_' || p_device_type);

    RETURN v_binding_id;
END;
$$;

COMMENT ON FUNCTION uc5_bind_device IS
  'UC-5: Device Binding. Validates token is ACTIVE before creating the '
  'DeviceBinding record. Lifecycle event records the binding with no agency '
  'actor (the holder, not an agency, initiates the binding).';

-- ----------------------------------------------------------------------------
-- UC-7: Warrant-Authorized Verification History Review
--   Returns a SETOF rows from VerificationEvent restricted to the warrant's
--   parameters. The disclosure model is enforced by the SELECT itself:
--     ZERO_KNOWLEDGE rows are aggregated to a count (returned with token_id
--                     NULL, no token-identifying data)
--     SELECTIVE rows return their disclosed attributes
--     FULL rows return complete records
-- ----------------------------------------------------------------------------

CREATE OR REPLACE FUNCTION uc7_warrant_audit(
    p_individual_id      INTEGER,
    p_window_start       TIMESTAMP DEFAULT '1970-01-01',
    p_window_end         TIMESTAMP DEFAULT 'infinity',
    p_context_filter     VARCHAR(40) DEFAULT NULL  -- if non-null, restrict to one context
) RETURNS TABLE (
    event_id           INTEGER,
    event_timestamp    TIMESTAMP,
    context_type       VARCHAR(40),
    requesting_agency  VARCHAR(200),
    outcome            VARCHAR(20),
    disclosure_level   VARCHAR(20),
    requestor_location VARCHAR(200),
    token_id           INTEGER,
    legal_name         VARCHAR(200)
)
LANGUAGE plpgsql
AS $$
BEGIN
    -- Identifying disclosure: SELECTIVE and FULL events return the named columns.
    -- ZERO_KNOWLEDGE events are returned with token_id and legal_name NULL.
    RETURN QUERY
    SELECT  ve.event_id,
            ve.event_timestamp,
            vc.context_type,
            ag.name                                           AS requesting_agency,
            ve.outcome,
            ve.disclosure_level,
            CASE WHEN ve.disclosure_level = 'ZERO_KNOWLEDGE'
                 THEN NULL ELSE ve.requestor_location END     AS requestor_location,
            CASE WHEN ve.disclosure_level = 'ZERO_KNOWLEDGE'
                 THEN NULL ELSE ve.token_id END               AS token_id,
            CASE WHEN ve.disclosure_level = 'ZERO_KNOWLEDGE'
                 THEN NULL ELSE ind.legal_name END            AS legal_name
    FROM    VerificationEvent ve
    JOIN    VerificationContext vc ON ve.context_id = vc.context_id
    JOIN    Agency              ag ON ve.requesting_agency_id = ag.agency_id
    LEFT JOIN IdentityToken     it  ON ve.token_id = it.token_id
    LEFT JOIN Individual        ind ON it.individual_id = ind.individual_id
    WHERE   (it.individual_id = p_individual_id)
      AND   ve.event_timestamp BETWEEN p_window_start AND p_window_end
      AND   (p_context_filter IS NULL OR vc.context_type = p_context_filter);
END;
$$;

COMMENT ON FUNCTION uc7_warrant_audit IS
  'UC-7: Warrant-Authorized Verification History Review. Returns identifying '
  'data only for SELECTIVE and FULL disclosure events; ZERO_KNOWLEDGE events '
  'are matched to the warrant''s individual via the join (which fails for '
  'NULL token_id rows) but never return token-identifying data. The schema '
  'permits the warrant query; the disclosure level governs what it returns.';

-- ----------------------------------------------------------------------------
-- UC-8: Bounded Revocation (R11-6 / M2-11)
--
--   The single sanctioned revocation path. Enforces the rolling-window
--   N% / W-day rate against the issuing agency. If the bound would be
--   exceeded, a co-signer is required; the co-signer must hold BOTH
--   authorization on the token's algorithm and must differ from the actor.
--   Mirrors the UC-4 pattern: transitions the token to REVOKED AND
--   publishes to RevocationList in the same transaction.
--
--   C9: serialized per-agency via pg_advisory_xact_lock so the
--   read-then-write rate check is atomic across concurrent calls.
--   Cross-agency revocations don't conflict — the lock key is agency-scoped.
--
--   Implements the PDF §9 "constitutional limits on issuer discretion" leg
--   of the issuer-trust-concentration triad (alongside cryptographic
--   diversity in R11-1 and federation in R11-8/M2-8).
-- ----------------------------------------------------------------------------

CREATE OR REPLACE PROCEDURE uc8_revoke_token(
    p_token_id            INTEGER,
    p_actor_agency_id     INTEGER,
    p_reason_code         VARCHAR(40),
    p_published_location  VARCHAR(300),
    p_cosigner_agency_id  INTEGER DEFAULT NULL
)
LANGUAGE plpgsql AS $$
DECLARE
    v_issuing_agency_id INTEGER;
    v_current_status    VARCHAR(20);
    v_outstanding       INTEGER;
    v_recent_revokes    INTEGER;
    v_max_percent       NUMERIC(5,2);
    v_window_days       INTEGER;
    v_observed_percent  NUMERIC(8,4);
    v_cosigner_auth     VARCHAR(20);
BEGIN
    -- C9: serialize concurrent revocations by the SAME agency so the
    -- read-then-write rate check is atomic. Two threads racing the
    -- (N+1)th call against the same agency block each other on this
    -- lock; the loser sees the winner's row when its rate read runs.
    -- Transaction-scoped — released at COMMIT/ROLLBACK automatically.
    PERFORM pg_advisory_xact_lock(
        hashtext('polaris.revoke.' ||
            (SELECT issuing_agency_id::TEXT
             FROM IdentityToken WHERE token_id = p_token_id)));

    -- Resolve token state. The bound applies to the *issuing* agency
    -- (not necessarily the actor). Reject already-terminal tokens so
    -- a token cannot be double-revoked or revoked-after-LOST.
    SELECT issuing_agency_id, status
      INTO v_issuing_agency_id, v_current_status
    FROM IdentityToken WHERE token_id = p_token_id;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Token % does not exist', p_token_id;
    END IF;
    IF v_current_status IN ('REVOKED','LOST','EXPIRED') THEN
        RAISE EXCEPTION 'Token % is already terminal (%); cannot revoke',
            p_token_id, v_current_status;
    END IF;

    -- Resolve effective policy (per-agency override or system default).
    -- current_setting(..., true) returns NULL for missing GUCs; COALESCE
    -- to hardcoded 5.00 / 30 so a missing GUC degrades to defaults.
    SELECT max_revoke_percent, window_days
      INTO v_max_percent, v_window_days
    FROM IssuerDiscretionPolicy
    WHERE agency_id = v_issuing_agency_id;
    IF NOT FOUND THEN
        v_max_percent := COALESCE(
            NULLIF(current_setting('polaris.default_max_revoke_percent', true), '')::NUMERIC,
            5.00);
        v_window_days := COALESCE(
            NULLIF(current_setting('polaris.default_window_days', true), '')::INTEGER,
            30);
    END IF;

    -- Outstanding = ever-issued by this agency (lifetime denominator).
    SELECT count(*) INTO v_outstanding
    FROM IdentityToken
    WHERE issuing_agency_id = v_issuing_agency_id;

    -- Numerator = revocations in window, INCLUDING this one.
    SELECT count(*) + 1 INTO v_recent_revokes
    FROM TokenLifecycleEvent e
    JOIN IdentityToken t ON t.token_id = e.token_id
    WHERE t.issuing_agency_id = v_issuing_agency_id
      AND e.event_type = 'REVOKED'
      AND e.event_timestamp > CURRENT_TIMESTAMP - (v_window_days || ' days')::INTERVAL;

    v_observed_percent := CASE
        WHEN v_outstanding = 0 THEN 100  -- empty agency: any revocation trips bound
        ELSE (v_recent_revokes::NUMERIC / v_outstanding) * 100
    END;

    IF v_observed_percent > v_max_percent THEN
        IF p_cosigner_agency_id IS NULL THEN
            RAISE EXCEPTION
                'Revocation rate for agency % would reach % percent in % day window (bound: % percent); co-signer required',
                v_issuing_agency_id, v_observed_percent,
                v_window_days, v_max_percent
                USING ERRCODE = 'check_violation';
        END IF;

        -- Co-signer must be a *different* agency.
        IF p_cosigner_agency_id = p_actor_agency_id THEN
            RAISE EXCEPTION 'Co-signer must differ from actor';
        END IF;

        -- Co-signer must hold BOTH on the token's algorithm.
        SELECT aa.authorization_type INTO v_cosigner_auth
        FROM AgencyAlgorithmAuth aa
        JOIN IdentityToken      t ON t.algorithm_id = aa.algorithm_id
        WHERE aa.agency_id = p_cosigner_agency_id
          AND t.token_id    = p_token_id;
        IF NOT FOUND OR v_cosigner_auth <> 'BOTH' THEN
            RAISE EXCEPTION
                'Co-signer agency % lacks BOTH authorization on the relevant algorithm',
                p_cosigner_agency_id;
        END IF;
    END IF;

    -- Step 1: transition the token to REVOKED. Set audit-trigger GUCs
    -- so the AFTER UPDATE trigger writes a properly-attributed lifecycle
    -- event automatically (same pattern as UC-4). The co-signer tag
    -- lives in the lifecycle event reason_code (VARCHAR(60), not domain-
    -- checked), keeping the verifier-facing RevocationList row in the
    -- canonical reason-code vocabulary.
    PERFORM set_config('polaris.actor_agency_id', p_actor_agency_id::TEXT, true);
    PERFORM set_config('polaris.reason_code',
        CASE WHEN p_cosigner_agency_id IS NULL
             THEN p_reason_code
             ELSE p_reason_code || ' [COSIGN:' || p_cosigner_agency_id::TEXT || ']'
        END,
        true);
    -- Signal to the belt-and-suspenders trigger that the bound has
    -- been checked under this transaction (see 06_triggers.sql).
    PERFORM set_config('polaris.revoke_check_done', '1', true);

    UPDATE IdentityToken
       SET status = 'REVOKED'
     WHERE token_id = p_token_id;

    -- Step 2: publish to the verifier-facing revocation list (UC-4
    -- pattern). Without this, the token state would diverge from
    -- the published CRL.
    INSERT INTO RevocationList
        (token_id, revoked_by_agency_id, effective_date,
         reason_code, published_location)
    VALUES
        (p_token_id, p_actor_agency_id, CURRENT_DATE,
         p_reason_code, p_published_location);
END$$;

COMMENT ON PROCEDURE uc8_revoke_token(INTEGER, INTEGER, VARCHAR, VARCHAR, INTEGER) IS
  'UC-8: Bounded Revocation. The single sanctioned revocation path. '
  'Enforces a rolling N%/W-day cap on revocations per issuing agency '
  '(R11-6/M2-11); above the bound a co-signer is required who holds '
  'BOTH on the algorithm and differs from the actor. Mirrors UC-4: '
  'updates IdentityToken.status to REVOKED and inserts into '
  'RevocationList in the same transaction. Serializes per-agency via '
  'pg_advisory_xact_lock for C9 correctness under concurrency.';

-- ============================================================================
-- UC-9: Catastrophic-Loss Recovery (R11-2 / M2-7)
--
-- Two-phase out-of-band recovery ceremony for the case PDF §9.1 names:
-- a holder loses ALL of their tokens and devices simultaneously.
--
-- Phase 1 — uc9_initiate_recovery:
--   Operator submits a recovery request. INSERT a PENDING RecoveryRequest
--   row. Rejects if the individual already has an ACTIVE token (UC-4 is
--   the right path then) or already has a PENDING recovery (the partial
--   unique index uq_one_pending_recovery_per_individual would also catch
--   this, but the procedure rejects first with a clearer error).
--
-- Phase 2 — uc9_complete_recovery:
--   Admin user transitions PENDING to APPROVED or REJECTED.
--   - pg_advisory_xact_lock keyed on claimed_individual_id (C9)
--   - admin role required (RAISE EXCEPTION if not)
--   - cool-down expired
--   - approver ≠ requester (also schema CHECK)
--   - if APPROVED: three channels verified, then transition non-terminal
--     tokens to LOST + publish to RevocationList (UC-4 pattern) + issue
--     new ACTIVE token with predecessor_token_id=NULL (chain was lost) +
--     audit rows tagged [RECOVERY:<id>]
--   - if REJECTED: just status update, no token issuance
--
-- Implements PDF §9.1 catastrophic-loss-risk open problem. The third
-- leg of the "schema doesn't weaponize itself against the holder"
-- triad (entry: R11-4, exit: R11-6, recovery: this).
-- ----------------------------------------------------------------------------

CREATE OR REPLACE PROCEDURE uc9_initiate_recovery(
    p_individual_id      INTEGER,
    p_requesting_agency  INTEGER,
    p_requesting_user    INTEGER,
    p_cooldown_hours     INTEGER DEFAULT 48
)
LANGUAGE plpgsql AS $$
DECLARE
    v_active_count   INTEGER;
    v_pending_count  INTEGER;
    v_new_id         INTEGER;
BEGIN
    -- Reject if an ACTIVE token already exists — UC-4 is the right path.
    SELECT count(*) INTO v_active_count
    FROM IdentityToken
    WHERE individual_id = p_individual_id AND status = 'ACTIVE';
    IF v_active_count > 0 THEN
        RAISE EXCEPTION
            'Individual % has an ACTIVE token; use UC-4 reserve activation, not UC-9 recovery',
            p_individual_id
            USING ERRCODE = 'check_violation';
    END IF;

    -- Reject if a PENDING recovery already exists for this individual.
    SELECT count(*) INTO v_pending_count
    FROM RecoveryRequest
    WHERE claimed_individual_id = p_individual_id AND status = 'PENDING';
    IF v_pending_count > 0 THEN
        RAISE EXCEPTION
            'A PENDING recovery already exists for individual %',
            p_individual_id
            USING ERRCODE = 'unique_violation';
    END IF;

    INSERT INTO RecoveryRequest
        (claimed_individual_id, requesting_agency_id, requesting_user_id,
         cooldown_expires_at)
    VALUES
        (p_individual_id, p_requesting_agency, p_requesting_user,
         CURRENT_TIMESTAMP + (p_cooldown_hours || ' hours')::INTERVAL)
    RETURNING recovery_id INTO v_new_id;

    -- Surface the new id via NOTICE so callers without RETURNING can see it.
    RAISE NOTICE 'Created RecoveryRequest #%', v_new_id;
END$$;

COMMENT ON PROCEDURE uc9_initiate_recovery(INTEGER, INTEGER, INTEGER, INTEGER) IS
  'UC-9 phase 1: initiate a catastrophic-loss recovery ceremony. Rejects '
  'if the individual already has an ACTIVE token (UC-4 is the right path) '
  'or already has a PENDING recovery. Returns the new recovery_id via '
  'NOTICE; callers wanting the id directly should use the function '
  'variant or read currval(''RecoveryRequest_recovery_id_seq'').';


CREATE OR REPLACE PROCEDURE uc9_complete_recovery(
    p_recovery_id        INTEGER,
    p_deciding_user      INTEGER,
    p_decision           VARCHAR,   -- 'APPROVED' or 'REJECTED'
    p_reason             TEXT,
    p_new_token_value    VARCHAR DEFAULT NULL,
    p_new_serial         VARCHAR DEFAULT NULL,
    p_algorithm_id       INTEGER DEFAULT NULL,
    p_biometric_binding  VARCHAR DEFAULT NULL,
    p_liveness_check     VARCHAR DEFAULT NULL,
    p_published_location VARCHAR DEFAULT NULL
)
LANGUAGE plpgsql AS $$
DECLARE
    v_individual_id     INTEGER;
    v_requesting_agency INTEGER;
    v_requesting_user   INTEGER;
    v_status            VARCHAR(20);
    v_cooldown_at       TIMESTAMP;
    v_biometric         BOOLEAN;
    v_sworn             VARCHAR(128);
    v_witness_agency    INTEGER;
    v_witness_user      INTEGER;
    v_role              VARCHAR(20);
    v_active_flag       BOOLEAN;
    v_lost_token        RECORD;
    v_new_token_id      INTEGER;
BEGIN
    -- C9: serialize concurrent completions of the same recovery (and any
    -- other recoveries for the same individual). Two threads racing this
    -- procedure for the same recovery_id would each pass the cool-down +
    -- three-channel CHECKs and both attempt the UPDATE+INSERT chain; the
    -- per-individual advisory lock makes them wait for each other so the
    -- second sees the post-commit APPROVED state and aborts cleanly.
    PERFORM pg_advisory_xact_lock(
        hashtext('polaris.recovery.' ||
            (SELECT claimed_individual_id::TEXT
             FROM RecoveryRequest WHERE recovery_id = p_recovery_id)));

    -- Belt-and-suspenders: deciding user must hold admin role.
    SELECT role, is_active INTO v_role, v_active_flag
    FROM AppUser WHERE user_id = p_deciding_user;
    IF NOT FOUND OR v_role <> 'admin' OR v_active_flag <> TRUE THEN
        RAISE EXCEPTION
            'Recovery decision requires admin role (user % has role=%)',
            p_deciding_user, COALESCE(v_role, 'NONE')
            USING ERRCODE = 'insufficient_privilege';
    END IF;

    -- Load the recovery request with FOR UPDATE so we observe the
    -- post-lock state if another thread already mutated it.
    SELECT claimed_individual_id, requesting_agency_id, requesting_user_id,
           status, cooldown_expires_at, biometric_verified,
           sworn_statement_hash, witness_agency_id, witness_co_sign_user_id
      INTO v_individual_id, v_requesting_agency, v_requesting_user,
           v_status, v_cooldown_at, v_biometric,
           v_sworn, v_witness_agency, v_witness_user
    FROM RecoveryRequest
    WHERE recovery_id = p_recovery_id
    FOR UPDATE;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Recovery request % does not exist', p_recovery_id;
    END IF;
    IF v_status <> 'PENDING' THEN
        RAISE EXCEPTION
            'Recovery request % is already in status % (not PENDING)',
            p_recovery_id, v_status;
    END IF;

    -- Approver ≠ requester (also CHECK on the table, but procedure errors
    -- earlier with a clearer message).
    IF p_deciding_user = v_requesting_user THEN
        RAISE EXCEPTION
            'Approver (user %) must differ from requester (user %)',
            p_deciding_user, v_requesting_user;
    END IF;

    -- Validate decision argument.
    IF p_decision NOT IN ('APPROVED', 'REJECTED') THEN
        RAISE EXCEPTION 'Decision must be APPROVED or REJECTED, got %',
            p_decision;
    END IF;

    IF p_decision = 'APPROVED' THEN
        -- Cool-down check (also enforced by approved_after_cooldown CHECK).
        IF CURRENT_TIMESTAMP < v_cooldown_at THEN
            RAISE EXCEPTION
                'Cool-down has not expired (until %); cannot approve yet',
                v_cooldown_at
                USING ERRCODE = 'check_violation';
        END IF;

        -- Three-channel check (also enforced by approved_requires_three_channels CHECK).
        IF v_biometric IS NOT TRUE OR v_sworn IS NULL
           OR v_witness_agency IS NULL OR v_witness_user IS NULL THEN
            RAISE EXCEPTION
                'APPROVED requires all three OOB channels (biometric, sworn statement, witness agency co-sign)'
                USING ERRCODE = 'check_violation';
        END IF;

        -- Validate the new-token parameters.
        IF p_new_token_value IS NULL OR p_new_serial IS NULL
           OR p_algorithm_id IS NULL OR p_biometric_binding IS NULL
           OR p_liveness_check IS NULL OR p_published_location IS NULL THEN
            RAISE EXCEPTION
                'APPROVED recovery requires new token parameters '
                '(p_new_token_value, p_new_serial, p_algorithm_id, '
                'p_biometric_binding, p_liveness_check, p_published_location)';
        END IF;

        -- Step 1: transition all non-terminal tokens to LOST, with the
        -- recovery-tagged reason. Publish each to RevocationList.
        PERFORM set_config('polaris.actor_agency_id', v_requesting_agency::TEXT, true);
        PERFORM set_config('polaris.reason_code',
            'LOST_BY_RECOVERY [RECOVERY:' || p_recovery_id::TEXT || ']', true);

        FOR v_lost_token IN
            SELECT token_id FROM IdentityToken
            WHERE individual_id = v_individual_id
              AND status NOT IN ('LOST','EXPIRED','REVOKED')
        LOOP
            UPDATE IdentityToken
               SET status = 'LOST'
             WHERE token_id = v_lost_token.token_id;

            INSERT INTO RevocationList
                (token_id, revoked_by_agency_id, effective_date,
                 reason_code, published_location)
            VALUES
                (v_lost_token.token_id, v_requesting_agency, CURRENT_DATE,
                 'LOST', p_published_location);
        END LOOP;

        -- Step 2: insert the new IdentityToken. predecessor_token_id is
        -- NULL because the prior chain was lost (distinct from UC-4's
        -- reserve activation, which DOES set predecessor). The auto-audit
        -- trigger will emit a lifecycle row with the recovery tag once
        -- we set reason_code below and UPDATE the new token's status.
        INSERT INTO IdentityToken
            (token_value, physical_serial, hardware_model,
             biometric_binding_type, individual_id, issuing_agency_id,
             algorithm_id, status, issued_date, expiration_date,
             liveness_check_type)
        VALUES
            (p_new_token_value, p_new_serial, 'TitanQ-3',
             p_biometric_binding, v_individual_id, v_requesting_agency,
             p_algorithm_id, 'RESERVE', CURRENT_TIMESTAMP,
             (CURRENT_DATE + INTERVAL '10 years')::DATE,
             p_liveness_check)
        RETURNING token_id INTO v_new_token_id;

        -- R11-1 / M2-6: issue a TokenSignature row alongside the new
        -- IdentityToken so the M:N invariant is satisfied. Tagged with
        -- the recovery context in the placeholder so audit replay can
        -- identify recovery-issued signatures.
        INSERT INTO TokenSignature (token_id, algorithm_id, signature_bytes)
        VALUES (v_new_token_id, p_algorithm_id,
                ('UC9_RECOVERY_PLACEHOLDER_' || p_recovery_id::TEXT
                 || '_TOKEN_' || v_new_token_id::TEXT)::BYTEA);

        -- Step 3: promote the new token to ACTIVE with the recovery tag.
        PERFORM set_config('polaris.reason_code',
            'RECOVERY_ISSUED [RECOVERY:' || p_recovery_id::TEXT || ']', true);
        UPDATE IdentityToken
           SET status = 'ACTIVE',
               activated_date = CURRENT_TIMESTAMP,
               biometric_enrolled_date = CURRENT_TIMESTAMP,
               enrollment_witness_agency_id = v_witness_agency
         WHERE token_id = v_new_token_id;

        -- Step 4: close out the RecoveryRequest.
        UPDATE RecoveryRequest
           SET status = 'APPROVED',
               decided_at = CURRENT_TIMESTAMP,
               decided_by_user_id = p_deciding_user,
               decision_reason = p_reason,
               resulting_token_id = v_new_token_id
         WHERE recovery_id = p_recovery_id;

        RAISE NOTICE 'Recovery #% APPROVED; new ACTIVE token #%',
            p_recovery_id, v_new_token_id;

    ELSE  -- REJECTED
        UPDATE RecoveryRequest
           SET status = 'REJECTED',
               decided_at = CURRENT_TIMESTAMP,
               decided_by_user_id = p_deciding_user,
               decision_reason = p_reason
         WHERE recovery_id = p_recovery_id;

        RAISE NOTICE 'Recovery #% REJECTED', p_recovery_id;
    END IF;
END$$;

COMMENT ON PROCEDURE uc9_complete_recovery(INTEGER, INTEGER, VARCHAR, TEXT,
    VARCHAR, VARCHAR, INTEGER, VARCHAR, VARCHAR, VARCHAR) IS
  'UC-9 phase 2: transition a PENDING RecoveryRequest to APPROVED or '
  'REJECTED. APPROVED requires admin role, expired cool-down, three OOB '
  'channels, and full new-token parameters. Old non-terminal tokens '
  'transition to LOST and publish to RevocationList (UC-4 pattern). '
  'Serializes per-individual via pg_advisory_xact_lock (C9 correctness).';

-- ----------------------------------------------------------------------------
-- UC-6: Algorithm Migration (R11-1 / M2-6)
--
-- Migrate a token to a new cryptographic algorithm by adding a new
-- TokenSignature row under the new algorithm. Optionally deprecate the
-- old signature(s). The old signature continues to verify until its
-- deprecation_date passes — this is the migration window.
--
-- Concurrency (C9): opens with pg_advisory_xact_lock keyed on token_id
-- so two threads racing the migration of the same token serialize
-- cleanly. Cross-token migrations remain parallel.
--
-- Audit: TokenSignature row IS the audit-of-record for migrations. No
-- TokenLifecycleEvent row is written — the procedure does not change
-- IdentityToken.status. The TokenSignature row's signed_at and the
-- append-only invariant together constitute the migration record.
--
-- Implements PDF §9.4 multi-signature transitional state — the
-- cryptographic-diversity leg of the issuer-trust-concentration triad
-- (alongside R11-6 = constitutional limits ✅ and M2-8 = federation, open).
-- ----------------------------------------------------------------------------

CREATE OR REPLACE PROCEDURE uc6_migrate_algorithm(
    p_token_id        INTEGER,
    p_new_algorithm   INTEGER,
    p_new_signature   BYTEA,
    p_deprecate_old   BOOLEAN DEFAULT FALSE
)
LANGUAGE plpgsql AS $$
DECLARE
    v_token_exists  INTEGER;
    v_alg_exists    INTEGER;
    v_new_sig_id    INTEGER;
    v_old_count     INTEGER;
BEGIN
    -- C9: per-token serialization. Two threads racing on the same token
    -- block each other on this lock; the loser sees the winner's row
    -- when its checks re-run.
    PERFORM pg_advisory_xact_lock(
        hashtext('polaris.migrate.' || p_token_id::TEXT));

    -- Validate the token exists.
    SELECT count(*) INTO v_token_exists
    FROM IdentityToken WHERE token_id = p_token_id;
    IF v_token_exists = 0 THEN
        RAISE EXCEPTION 'Token % does not exist', p_token_id;
    END IF;

    -- Validate the new algorithm exists and is not deprecated.
    SELECT count(*) INTO v_alg_exists
    FROM CryptographicAlgorithm
    WHERE algorithm_id = p_new_algorithm
      AND (deprecation_date IS NULL OR deprecation_date > CURRENT_TIMESTAMP);
    IF v_alg_exists = 0 THEN
        RAISE EXCEPTION
            'Algorithm % does not exist or is itself deprecated',
            p_new_algorithm;
    END IF;

    -- Insert the new TokenSignature row. The UNIQUE constraint
    -- (token_id, algorithm_id) rejects duplicate-algorithm migrations.
    INSERT INTO TokenSignature
        (token_id, algorithm_id, signature_bytes)
    VALUES
        (p_token_id, p_new_algorithm, p_new_signature)
    RETURNING signature_id INTO v_new_sig_id;

    -- Optionally deprecate the OLD signatures (every active sig other
    -- than the one just inserted). Setting deprecation_date is the
    -- one-way operation enforced by enforce_token_signature_immutability.
    IF p_deprecate_old THEN
        UPDATE TokenSignature
           SET deprecation_date = CURRENT_TIMESTAMP + INTERVAL '1 second'
         WHERE token_id = p_token_id
           AND signature_id <> v_new_sig_id
           AND deprecation_date IS NULL;
        -- The +1 second is required to satisfy the deprecation_after_signed
        -- CHECK; an instantaneous "deprecated at creation" doesn't make
        -- sense and the constraint refuses it.
    END IF;

    -- The enforce_token_has_active_signature trigger fired on the INSERT
    -- and the optional UPDATE; if either left the token with zero active
    -- signatures, the procedure would have already aborted. We're safe.

    RAISE NOTICE 'UC-6 migrated token %: new signature_id=% under algorithm %',
        p_token_id, v_new_sig_id, p_new_algorithm;
END$$;

COMMENT ON PROCEDURE uc6_migrate_algorithm(INTEGER, INTEGER, BYTEA, BOOLEAN) IS
  'UC-6 / R11-1 / M2-6: migrate a token to a new algorithm. Adds a new '
  'TokenSignature row; optionally deprecates the old signature(s). The '
  'old signature continues to verify until its deprecation_date passes — '
  'this is the migration window. Per-token serialization via '
  'pg_advisory_xact_lock (C9). TokenSignature row is the audit-of-record.';

-- ----------------------------------------------------------------------------
-- close_anchor_batch (R10-2 / M2-2)
--
-- Closes a Merkle batch for the pending BlockchainAnchor rows of a given
-- algorithm. The Merkle root is computed by the Python helper
-- (polaris_web/anchoring.py) and passed in as p_merkle_root — keeping the
-- procedure portable (no plpython3u dependency).
--
-- C9: per-algorithm advisory-lock. Same-algorithm batch-closes serialize
-- to prevent phantom AnchorBatch rows; cross-algorithm batch-closes
-- parallelize. Per-algorithm scope is natural: different algorithms have
-- disjoint leaf sets.
--
-- AnchorBatch is the 5th audit-of-record instance in Polaris — append-only,
-- once created the merkle_root cannot be rewritten (every inclusion proof
-- issued against it depends on its immutability). See
-- DEVNOTES/audit-of-record.md.
--
-- Implements PDF §9 "Centralized trust assumption" leg — the relational
-- schema as the off-chain commitment-record layer.
-- ----------------------------------------------------------------------------
CREATE OR REPLACE PROCEDURE close_anchor_batch(
    p_algorithm_id  INTEGER,
    p_merkle_root   VARCHAR(128),
    -- proofs is a JSON object: { "<anchor_id>": <proof_json>, ... }
    -- pre-computed by anchoring.py in the same call.
    p_proofs        JSONB
)
LANGUAGE plpgsql AS $$
DECLARE
    v_pending_count   INTEGER;
    v_new_batch_id    INTEGER;
    v_alg_exists      INTEGER;
BEGIN
    -- C9: per-algorithm advisory lock. See DEVNOTES/concurrency.md
    -- ("Per-algorithm advisory-lock") for the rationale.
    PERFORM pg_advisory_xact_lock(
        hashtext('polaris.anchor.close-batch.' || p_algorithm_id::TEXT));

    -- Validate algorithm exists and is not deprecated.
    SELECT count(*) INTO v_alg_exists
    FROM CryptographicAlgorithm
    WHERE algorithm_id = p_algorithm_id
      AND (deprecation_date IS NULL OR deprecation_date > CURRENT_TIMESTAMP);
    IF v_alg_exists = 0 THEN
        RAISE EXCEPTION
            'Algorithm % does not exist or is deprecated; cannot close batch',
            p_algorithm_id;
    END IF;

    -- Count pending anchors for this algorithm. The leaf set is the
    -- BlockchainAnchor rows whose underlying token was signed under
    -- algorithm p_algorithm_id (via IdentityToken.algorithm_id) AND
    -- which are not yet batched.
    SELECT count(*) INTO v_pending_count
    FROM BlockchainAnchor a
    JOIN IdentityToken    t ON a.token_id = t.token_id
    WHERE a.batch_id IS NULL
      AND t.algorithm_id = p_algorithm_id;

    IF v_pending_count = 0 THEN
        RAISE EXCEPTION
            'No pending BlockchainAnchor rows for algorithm %; nothing to batch',
            p_algorithm_id
            USING ERRCODE = 'no_data_found';
    END IF;

    -- Hard cap per the proposal: 10,000 leaves per batch.
    IF v_pending_count > 10000 THEN
        RAISE EXCEPTION
            'Pending anchors (%) exceeds batch-size cap of 10000; close in multiple batches',
            v_pending_count;
    END IF;

    -- Create the AnchorBatch row. The append-only trigger on AnchorBatch
    -- will prevent any future UPDATE to merkle_root or DELETE.
    INSERT INTO AnchorBatch (merkle_root, algorithm_id, batch_size)
    VALUES (p_merkle_root, p_algorithm_id, v_pending_count)
    RETURNING batch_id INTO v_new_batch_id;

    -- Assign batch_id + per-leaf merkle_proof to every pending anchor of
    -- this algorithm. Deterministic leaf order (sort by anchor_id) defeats
    -- the publish-then-fork attack; the Python helper uses the same order
    -- when computing the proofs.
    UPDATE BlockchainAnchor a
       SET batch_id = v_new_batch_id,
           merkle_proof = (p_proofs ->> a.anchor_id::TEXT)::JSONB
      FROM IdentityToken t
     WHERE a.token_id = t.token_id
       AND a.batch_id IS NULL
       AND t.algorithm_id = p_algorithm_id;

    RAISE NOTICE 'close_anchor_batch: created batch_id=%, % leaves under algorithm %',
        v_new_batch_id, v_pending_count, p_algorithm_id;
END$$;

COMMENT ON PROCEDURE close_anchor_batch(INTEGER, VARCHAR, JSONB) IS
  'R10-2 / M2-2. Closes a Merkle batch for pending BlockchainAnchor rows '
  'of a given algorithm. Uses pg_advisory_xact_lock per algorithm_id for C9 '
  'correctness. The merkle_root and per-leaf proofs are pre-computed in '
  'polaris_web/anchoring.py and passed in. Hard batch-size cap: 10000.';

-- ----------------------------------------------------------------------------
-- uc10_attest_trust (R11-3 / M2-8)
--
-- Creates a new attestation in the federation trust graph. Per-attesting-
-- agency advisory lock (the 5th catalog entry) prevents same-agency
-- parallel attest/revoke races; cross-agency operations parallelize.
--
-- Constraints validated:
--   - both agencies and the context exist
--   - signing user has admin role (federation is an admin decision)
--   - valid_until is strictly in the future (DATE > today)
--   - schema-layer self-attestation rejection takes care of A==A
--   - schema-layer unique-active index takes care of duplicate active
--     attestation (raises unique_violation; we surface a readable message)
--
-- NO transitive trust: this procedure creates exactly one edge in the
-- graph. The verification flow looks up exactly one row. R1 audit
-- refinement; see DEVNOTES/ships/federation.md.
-- ----------------------------------------------------------------------------
CREATE OR REPLACE PROCEDURE uc10_attest_trust(
    p_attesting_id  INTEGER,
    p_attested_id   INTEGER,
    p_context_id    INTEGER,
    p_valid_until   DATE,
    p_signed_by     INTEGER
)
LANGUAGE plpgsql AS $$
DECLARE
    v_user_role TEXT;
BEGIN
    -- C9: per-attesting-agency advisory lock. The 5th catalog entry.
    -- Cross-attesting-agency operations run in parallel; same-attesting-
    -- agency operations serialize.
    PERFORM pg_advisory_xact_lock(
        hashtext('polaris.federation.attest.' || p_attesting_id::TEXT));

    -- Validate admin role on signer.
    SELECT role INTO v_user_role FROM AppUser WHERE user_id = p_signed_by;
    IF v_user_role IS NULL THEN
        RAISE EXCEPTION 'AppUser % not found', p_signed_by
            USING ERRCODE = 'no_data_found';
    END IF;
    IF v_user_role <> 'admin' THEN
        RAISE EXCEPTION
            'Federation attestation requires admin role (signer % has role %)',
            p_signed_by, v_user_role
            USING ERRCODE = 'insufficient_privilege';
    END IF;

    -- Validate valid_until is in the future.
    IF p_valid_until <= CURRENT_DATE THEN
        RAISE EXCEPTION
            'valid_until must be strictly in the future; got %', p_valid_until;
    END IF;

    -- Insert. The schema's three CHECK constraints and the partial unique
    -- index handle the rest:
    --   - attestation_no_self_attestation (CHECK)  → if A==A
    --   - attestation_validity_floor (CHECK)       → if validity is zero/neg
    --   - attestation_revocation_consistency (CHECK) → not triggered on INSERT
    --   - uq_active_attestation (partial unique)   → if duplicate active row
    BEGIN
        INSERT INTO AgencyTrustAttestation
            (attesting_agency_id, attested_agency_id, context_id,
             valid_until, signed_by)
        VALUES
            (p_attesting_id, p_attested_id, p_context_id,
             p_valid_until, p_signed_by);
    EXCEPTION
        WHEN unique_violation THEN
            RAISE EXCEPTION
                'An active attestation already exists for (attesting=%, attested=%, context=%); revoke it before re-attesting',
                p_attesting_id, p_attested_id, p_context_id
                USING ERRCODE = 'unique_violation';
    END;

    RAISE NOTICE 'uc10_attest_trust: %→% for context % until %',
        p_attesting_id, p_attested_id, p_context_id, p_valid_until;
END$$;

COMMENT ON PROCEDURE uc10_attest_trust(INTEGER, INTEGER, INTEGER, DATE, INTEGER) IS
  'R11-3 / M2-8. Records a federation trust edge (attesting → attested for '
  'context, valid until date). Per-attesting-agency advisory lock for C9. '
  'Admin role required. NO transitive trust — single-row insert; verification '
  'reads single row. See DEVNOTES/ships/federation.md.';

-- ----------------------------------------------------------------------------
-- uc10_revoke_attestation (R11-3 / M2-8)
--
-- Sets revocation_date + revocation_reason on an existing active attestation.
-- One-way mutation enforced by enforce_attestation_immutability trigger.
-- Per-attesting-agency advisory lock (same as uc10_attest_trust) prevents
-- concurrent attest+revoke races on the same agency.
--
-- "Schema records, agencies decide" framing (R2 audit refinement):
-- the revocation is forward-looking. Past VerificationEvent rows are
-- NOT retroactively invalidated — they remain in the append-only audit
-- log as the historical record of "this verification happened at time T."
-- New verifications after revocation see the revoked state.
-- ----------------------------------------------------------------------------
CREATE OR REPLACE PROCEDURE uc10_revoke_attestation(
    p_attestation_id    INTEGER,
    p_revocation_reason VARCHAR(80),
    p_signed_by         INTEGER
)
LANGUAGE plpgsql AS $$
DECLARE
    v_attesting_id  INTEGER;
    v_already_rev   TIMESTAMP;
    v_user_role     TEXT;
BEGIN
    SELECT attesting_agency_id, revocation_date
      INTO v_attesting_id, v_already_rev
      FROM AgencyTrustAttestation
     WHERE attestation_id = p_attestation_id;

    IF v_attesting_id IS NULL THEN
        RAISE EXCEPTION
            'Attestation % does not exist', p_attestation_id
            USING ERRCODE = 'no_data_found';
    END IF;

    IF v_already_rev IS NOT NULL THEN
        RAISE EXCEPTION
            'Attestation % is already revoked at %', p_attestation_id, v_already_rev;
    END IF;

    -- C9: per-attesting-agency advisory lock. Same key as uc10_attest_trust
    -- so attest+revoke on the same agency serialize.
    PERFORM pg_advisory_xact_lock(
        hashtext('polaris.federation.attest.' || v_attesting_id::TEXT));

    -- Validate admin role on signer.
    SELECT role INTO v_user_role FROM AppUser WHERE user_id = p_signed_by;
    IF v_user_role IS NULL THEN
        RAISE EXCEPTION 'AppUser % not found', p_signed_by
            USING ERRCODE = 'no_data_found';
    END IF;
    IF v_user_role <> 'admin' THEN
        RAISE EXCEPTION
            'Federation revocation requires admin role (signer % has role %)',
            p_signed_by, v_user_role
            USING ERRCODE = 'insufficient_privilege';
    END IF;

    -- The schema's revocation_consistency CHECK enforces the 8-char
    -- reason floor; we let the constraint surface the readable error.
    UPDATE AgencyTrustAttestation
       SET revocation_date   = CURRENT_TIMESTAMP,
           revocation_reason = p_revocation_reason
     WHERE attestation_id = p_attestation_id;

    RAISE NOTICE 'uc10_revoke_attestation: revoked attestation %', p_attestation_id;
END$$;

COMMENT ON PROCEDURE uc10_revoke_attestation(INTEGER, VARCHAR, INTEGER) IS
  'R11-3 / M2-8. Revokes an active federation attestation. Per-attesting-agency '
  'advisory lock for C9. Admin role required. One-way revocation enforced by '
  'enforce_attestation_immutability trigger. Forward-looking — past '
  'VerificationEvent rows survive. See DEVNOTES/ships/federation.md.';

-- ----------------------------------------------------------------------------
-- uc11_close_epoch (R10-1 / M2-1)
--
-- Closes a ZK-SNARK epoch: snapshots the active-token set, computes
-- per-token leaf hashes, builds a Merkle commitment, writes
-- TokenStateEpoch + TokenStateEpochLeaf rows. The Merkle root is the
-- cryptographic commitment that subsequent ZK proofs prove membership
-- in. Once written, the epoch is immutable (enforce_epoch_immutability
-- trigger); future verification reads the merkle_root and consults
-- valid_until for boundary check.
--
-- C9: per-epoch-id advisory lock (6th catalog entry). Conceptually the
-- "epoch_id" is the next-to-be-created SERIAL, so we lock on a known
-- key tied to admin operations on the table. We use the table name as
-- the lock domain since concurrent epoch-closures would race on the
-- INSERT and produce gapped epoch_id values.
--
-- The actual Merkle root and per-leaf inclusion paths are pre-computed
-- by the Python helper polaris_web/zk.py (which itself shells out to
-- the polaris_zk Rust binary or computes them directly using SHA3-256
-- for the schema-level commitment). They are passed in as arguments —
-- same posture as close_anchor_batch.
--
-- v1 scope: validity predicates (ACTIVE status, has-context-permission,
-- not-revoked) are checked at epoch-commitment time by the caller. The
-- procedure does NOT re-validate; it trusts the caller's filtered token
-- list. This is the B3 hybrid contract.
-- ----------------------------------------------------------------------------
CREATE OR REPLACE PROCEDURE uc11_close_epoch(
    p_merkle_root      VARCHAR(128),
    p_valid_until      TIMESTAMP,
    p_closed_by        INTEGER,
    -- token_leaves: JSON array of objects [{"token_id": int, "leaf_hash": hex, "proof_path": [...]}, ...]
    p_token_leaves     JSONB
)
LANGUAGE plpgsql AS $$
DECLARE
    v_new_epoch_id  INTEGER;
    v_count         INTEGER;
    v_user_role     TEXT;
    v_leaf          JSONB;
BEGIN
    -- C9: per-procedure advisory lock — serializes epoch closures (otherwise
    -- two concurrent calls would race on the INSERT).
    PERFORM pg_advisory_xact_lock(
        hashtext('polaris.zk.close-epoch'));

    -- Validate admin role.
    SELECT role INTO v_user_role FROM AppUser WHERE user_id = p_closed_by;
    IF v_user_role IS NULL THEN
        RAISE EXCEPTION 'AppUser % not found', p_closed_by
            USING ERRCODE = 'no_data_found';
    END IF;
    IF v_user_role <> 'admin' THEN
        RAISE EXCEPTION
            'Epoch closure requires admin role (signer % has role %)',
            p_closed_by, v_user_role
            USING ERRCODE = 'insufficient_privilege';
    END IF;

    -- Count leaves.
    SELECT jsonb_array_length(p_token_leaves) INTO v_count;
    IF v_count IS NULL OR v_count = 0 THEN
        RAISE EXCEPTION
            'Cannot close an empty epoch (zero valid tokens to commit)'
            USING ERRCODE = 'no_data_found';
    END IF;
    IF v_count > 10000 THEN
        RAISE EXCEPTION
            'Epoch size (%) exceeds cap of 10000; split into multiple epochs', v_count;
    END IF;

    -- Create the epoch row. The CHECK constraints enforce hex format,
    -- valid_until > valid_from, count cap.
    INSERT INTO TokenStateEpoch
        (merkle_root, valid_until, committed_count, closed_by_user_id)
    VALUES (p_merkle_root, p_valid_until, v_count, p_closed_by)
    RETURNING epoch_id INTO v_new_epoch_id;

    -- Write per-leaf rows. Iterate over the JSON array.
    FOR v_leaf IN SELECT * FROM jsonb_array_elements(p_token_leaves)
    LOOP
        INSERT INTO TokenStateEpochLeaf
            (epoch_id, token_id, leaf_hash, proof_path)
        VALUES (
            v_new_epoch_id,
            (v_leaf ->> 'token_id')::INTEGER,
            v_leaf ->> 'leaf_hash',
            v_leaf -> 'proof_path'
        );
    END LOOP;

    RAISE NOTICE 'uc11_close_epoch: created epoch_id=%, % leaves, valid_until=%',
        v_new_epoch_id, v_count, p_valid_until;
END$$;

COMMENT ON PROCEDURE uc11_close_epoch(VARCHAR, TIMESTAMP, INTEGER, JSONB) IS
  'R10-1 / M2-1. Closes a ZK-SNARK epoch with pre-computed Merkle root + '
  'per-leaf proof paths. Admin-only. Per-procedure advisory lock (6th catalog '
  'entry) prevents concurrent epoch closures. Hard cap: 10000 leaves. '
  'See DEVNOTES/ships/zk-snark.md.';

-- ----------------------------------------------------------------------------
-- uc12_record_duress (R11-5 / M2-10 / v8.24)
--
-- Records a detected duress event. Called from the verification flow
-- (verifications_new in app.py) after constant-time hash comparison of
-- the holder's typed duress code against IdentityToken.duress_code_hash
-- has matched. The actual hash comparison happens in Python via
-- werkzeug.security.check_password_hash; this procedure is just the
-- audit-of-record write.
--
-- No advisory lock — DuressEvent rows do not contend (each row is
-- independent, append-only, no per-entity coordination needed).
--
-- The coercer-visible verification flow continues normally; this
-- procedure writes the SILENT alert that operators/auditors see via
-- the /duress dashboard or direct SQL queries against DuressEvent.
-- R6 audit refinement: the operator-visible /verifications list does
-- NOT join to DuressEvent — only auditors with explicit access see
-- duress events.
-- ----------------------------------------------------------------------------
CREATE OR REPLACE PROCEDURE uc12_record_duress(
    p_token_id              INTEGER,
    p_context_id            INTEGER,
    p_requesting_agency_id  INTEGER,
    p_oob_channel           VARCHAR(40) DEFAULT 'AUDIT_TABLE'
)
LANGUAGE plpgsql AS $$
BEGIN
    -- Validate that the token actually has a duress_code_hash enrolled.
    -- If the caller invoked this procedure for a token that hasn't enrolled
    -- duress, that's a programming error — fail loudly rather than write a
    -- nonsensical row.
    IF NOT EXISTS (
        SELECT 1 FROM IdentityToken
         WHERE token_id = p_token_id
           AND duress_code_hash IS NOT NULL
    ) THEN
        RAISE EXCEPTION
            'Token % has no duress code enrolled; cannot record duress event',
            p_token_id
            USING ERRCODE = 'no_data_found';
    END IF;

    INSERT INTO DuressEvent
        (token_id, context_id, requesting_agency_id, oob_channel)
    VALUES
        (p_token_id, p_context_id, p_requesting_agency_id, p_oob_channel);

    -- Server-side log (the operator's stderr is one of the v1 OOB channels;
    -- production would wire SMS/Slack/SIEM via oob_channel dispatching).
    RAISE NOTICE 'DURESS DETECTED: token_id=%, context_id=%, requesting_agency=%, channel=%',
        p_token_id, p_context_id, p_requesting_agency_id, p_oob_channel;
END$$;

COMMENT ON PROCEDURE uc12_record_duress(INTEGER, INTEGER, INTEGER, VARCHAR) IS
  'R11-5 / M2-10. Records a detected duress event in DuressEvent (8th audit-of-'
  'record). Called by verifications_new after constant-time hash match. NO '
  'advisory lock — DuressEvent rows do not contend. The coercer-visible flow '
  'proceeds normally; this is the silent OOB alert. See DEVNOTES/ships/duress-codes.md.';

-- ============================================================================
-- END OF 05_procedures.sql
-- 13 stored procedures: uc1_issue_and_activate, uc4_activate_reserve,
-- uc5_bind_device, uc6_migrate_algorithm, uc7_warrant_audit,
-- uc8_revoke_token, uc9_initiate_recovery, uc9_complete_recovery,
-- close_anchor_batch, uc10_attest_trust, uc10_revoke_attestation,
-- uc11_close_epoch, uc12_record_duress.
-- UC-2, UC-3 are expressed as queries in 07_queries.sql (no
-- procedural state changes required).
-- ============================================================================


-- ============================================================================
-- uc_archive_purge — Arc B Phase 2b · constitutional carve-out for archive-
--                    then-delete (v8.87)
--
-- Closes the deletion-from-hot question per the OPEN Sanctum at
-- sanctum/2026-05-14-audit-log-deletion-from-hot.md (Position B, DECIDED).
--
-- This procedure is THE ONLY legitimate path through which DELETE may
-- issue against the four audit tables (TokenLifecycleEvent,
-- VerificationEvent, EnrollmentStatusEvent, AnchorBatch). The
-- reject_audit_modification() trigger checks `polaris.purge_in_progress`
-- and only honors DELETE when that GUC is set to 'TRUE' inside this
-- procedure's transaction.
--
-- Parameters:
--   p_cutoff_timestamp   — older-than threshold for the purge. Rows
--                          older than this are eligible.
--   p_archive_uri        — operator-set URI of the archive tarball that
--                          contains the rows being purged (filesystem
--                          path, S3 URL, etc.). Stored verbatim in the
--                          checkpoint.
--   p_archive_sha256     — 64-char hex SHA-256 of the archive tarball.
--                          Operator computes this from the file before
--                          calling this procedure. The trigger constraint
--                          on the checkpoint table enforces format.
--   p_actor_user_id      — AppUser.user_id of the operator authorizing.
--                          Must be present in AppUser (validated below).
--
-- Returns: the new checkpoint_id.
--
-- Pre-conditions enforced by this procedure:
--   1. Cutoff must be in the past.
--   2. SHA-256 must look like a 64-char hex string.
--   3. The actor must exist and have role='admin'.
--
-- Post-conditions guaranteed:
--   4. Rows older than the cutoff are DELETEd from the 4 audit tables.
--   5. A LifecycleArchiveCheckpoint row is appended in the SAME
--      transaction, recording the cutoff + SHA-256 + actor + per-table
--      row counts. If the procedure rolls back, both the deletions and
--      the checkpoint roll back atomically.
--   6. The `polaris.purge_in_progress` GUC is set LOCAL (transaction-
--      scoped); it cannot leak past the procedure boundary.
--
-- Constitutional note: this procedure is the audit-of-record discipline
-- (v8.20) applied to the deletion boundary. The checkpoint row IS the
-- record; the offline archive tarball at the recorded SHA-256 IS the
-- materialized referent.
-- ============================================================================

CREATE OR REPLACE PROCEDURE uc_archive_purge(
    p_cutoff_timestamp  TIMESTAMPTZ,
    p_archive_uri       VARCHAR(512),
    p_archive_sha256    VARCHAR(64),
    p_actor_user_id     INTEGER,
    INOUT  checkpoint_id_out  BIGINT DEFAULT NULL
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_actor_role         VARCHAR(64);
    v_lifecycle_purged   INTEGER := 0;
    v_verification_purged INTEGER := 0;
    v_enrollment_purged  INTEGER := 0;
    v_authaudit_purged   INTEGER := 0;
    v_anchorbatch_purged INTEGER := 0;
    v_attestation_purged INTEGER := 0;
    v_duress_purged      INTEGER := 0;
    v_total_purged       INTEGER := 0;
BEGIN
    -- 1. Validate cutoff is in the past.
    IF p_cutoff_timestamp > now() THEN
        RAISE EXCEPTION 'uc_archive_purge: cutoff_timestamp (%) is in the future; refusing.',
            p_cutoff_timestamp
            USING ERRCODE = 'check_violation';
    END IF;

    -- 2. Validate SHA-256 format.
    IF p_archive_sha256 IS NULL OR length(p_archive_sha256) <> 64
       OR p_archive_sha256 !~ '^[0-9a-fA-F]{64}$' THEN
        RAISE EXCEPTION 'uc_archive_purge: archive_sha256 must be 64 hex chars; got %',
            p_archive_sha256
            USING ERRCODE = 'check_violation';
    END IF;

    -- 3. Validate actor is admin (the procedure is admin-only).
    SELECT role INTO v_actor_role FROM AppUser WHERE user_id = p_actor_user_id;
    IF v_actor_role IS NULL THEN
        RAISE EXCEPTION 'uc_archive_purge: actor_user_id (%) does not exist.',
            p_actor_user_id
            USING ERRCODE = 'foreign_key_violation';
    END IF;
    IF v_actor_role <> 'admin' THEN
        RAISE EXCEPTION 'uc_archive_purge: actor_user_id (%) has role %, must be admin.',
            p_actor_user_id, v_actor_role
            USING ERRCODE = 'insufficient_privilege';
    END IF;

    -- 4. Open the carve-out. SET LOCAL is transaction-scoped; it
    --    cannot leak past COMMIT/ROLLBACK.
    SET LOCAL polaris.purge_in_progress = 'TRUE';

    -- 5. Issue the deletes. ORDER MATTERS for referential integrity:
    --    delete leaves before epochs (if Phase 2.5 ever extends purge
    --    to TokenStateEpoch); delete event tables in any order since
    --    they reference IdentityToken which is not purged.

    DELETE FROM TokenLifecycleEvent
        WHERE event_timestamp < p_cutoff_timestamp;
    GET DIAGNOSTICS v_lifecycle_purged = ROW_COUNT;

    DELETE FROM VerificationEvent
        WHERE event_timestamp < p_cutoff_timestamp;
    GET DIAGNOSTICS v_verification_purged = ROW_COUNT;

    DELETE FROM EnrollmentStatusEvent
        WHERE event_timestamp < p_cutoff_timestamp;
    GET DIAGNOSTICS v_enrollment_purged = ROW_COUNT;

    DELETE FROM AuthAuditLog
        WHERE event_timestamp < p_cutoff_timestamp;
    GET DIAGNOSTICS v_authaudit_purged = ROW_COUNT;

    -- AnchorBatch is intentionally excluded from v8.87 Phase 2b
    -- because BlockchainAnchor.batch_id holds an FK reference;
    -- cleanly handling the cascade requires either NULLing the
    -- per-token anchor's batch_id (preserving the row but
    -- disconnecting the batch reference) or purging both together.
    -- Phase 2c will resolve this. AnchorBatch is low-volume (one
    -- row per algorithm-batch, not per token) so the storage
    -- pressure that motivated Phase 2b doesn't accrue here in any
    -- case. The checkpoint column is preserved for forward-compat.
    v_anchorbatch_purged := 0;

    -- AgencyTrustAttestation has its own enforce_attestation_immutability
    -- trigger (separate from reject_audit_modification); DuressEvent has
    -- its own enforce_duress_event_immutability. Both are deliberately
    -- strict and the v8.87 GUC carve-out does NOT apply to them. They
    -- stay out of Phase 2b's purge surface; Phase 2c can extend the
    -- carve-out pattern to their triggers if/when needed. For now,
    -- federation attestations and duress events stay in hot forever
    -- (operationally fine — both are low-volume audit-class).
    v_attestation_purged := 0;
    v_duress_purged := 0;

    v_total_purged := v_lifecycle_purged + v_verification_purged
                    + v_enrollment_purged + v_authaudit_purged
                    + v_anchorbatch_purged + v_attestation_purged
                    + v_duress_purged;

    -- 6. Write the checkpoint row. SAME transaction, so atomic
    --    with the deletes.
    INSERT INTO LifecycleArchiveCheckpoint (
        cutoff_timestamp,
        archive_uri,
        archive_sha256,
        actor_user_id,
        rows_purged_lifecycle,
        rows_purged_verification,
        rows_purged_enrollment,
        rows_purged_authaudit,
        rows_purged_anchorbatch,
        rows_purged_attestation,
        rows_purged_duress,
        rows_purged_total
    ) VALUES (
        p_cutoff_timestamp,
        p_archive_uri,
        lower(p_archive_sha256),
        p_actor_user_id,
        v_lifecycle_purged,
        v_verification_purged,
        v_enrollment_purged,
        v_authaudit_purged,
        v_anchorbatch_purged,
        v_attestation_purged,
        v_duress_purged,
        v_total_purged
    )
    RETURNING checkpoint_id INTO checkpoint_id_out;

    -- The GUC evaporates at transaction end; no explicit reset needed.
END;
$$;

COMMENT ON PROCEDURE uc_archive_purge IS
    'Arc B Phase 2b constitutional carve-out (v8.87). The ONLY legitimate '
    'path for DELETE against audit tables. Enforces: cutoff-in-past + '
    'SHA-256 format + admin-role actor. Writes LifecycleArchiveCheckpoint '
    'in the same transaction. Reference: sanctum/2026-05-14-audit-log-deletion-from-hot.md.';
