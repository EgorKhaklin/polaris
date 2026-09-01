-- ============================================================================
-- 2026-09-01-002-agency-quota.up.sql
--
-- v9.190 / roadmap P1.8 (abuse controls): opt-in per-agency quotas.
--
-- ADDS (1): AgencyQuota, per-agency caps on issuances per rolling day,
-- revocations per rolling day, and verifications per rolling hour. NULL = no
-- cap of that kind; no row = no caps. A sibling of IssuerDiscretionPolicy:
-- a bound on what an AGENCY may do, never on a person.
-- ADDS (2): enforce_agency_quota() and its three BEFORE triggers on
-- IdentityToken (insert = issue, update into REVOKED = revoke) and
-- VerificationEvent (insert = verify): every write path meets the bound, a
-- capped write is serialized per (kind, agency) by an advisory lock so the
-- cap is exact under concurrency (C9), and an uncapped agency pays one
-- primary-key lookup. The refusal message starts with "quota exceeded:" and
-- the app maps it to HTTP 429 + polaris_quota_refusals_total.
-- ADDS (3): the two indexes that keep the window counts an index range scan.
--
-- The canonical copies live in 01_schema.sql / 02_indexes.sql /
-- 06_triggers.sql (a fresh build and --sync-objects install them); this
-- migration brings a deployed database to the same shape. REVERSIBLE: the
-- .down.sql drops the triggers, function, indexes, and table. ADDITIVE
-- (data side): yes. Idempotent: IF NOT EXISTS / OR REPLACE / DROP-then-CREATE.
-- ============================================================================

CREATE TABLE IF NOT EXISTS AgencyQuota (
    agency_id          INTEGER      PRIMARY KEY
                       REFERENCES Agency(agency_id),
    issue_per_day      INTEGER      CHECK (issue_per_day   IS NULL OR issue_per_day   > 0),
    revoke_per_day     INTEGER      CHECK (revoke_per_day  IS NULL OR revoke_per_day  > 0),
    verify_per_hour    INTEGER      CHECK (verify_per_hour IS NULL OR verify_per_hour > 0),
    set_by_admin       VARCHAR(50)  NOT NULL,
    set_at             TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    justification      TEXT         NOT NULL
                       CHECK (length(justification) >= 20)
);

COMMENT ON TABLE AgencyQuota IS
  'Opt-in per-agency caps (v9.190 / P1.8): issuances per rolling day, '
  'revocations per rolling day, verifications per rolling hour. Enforced by '
  'the enforce_agency_quota trigger on every write path. NULL = no cap of '
  'that kind; no row = no caps. justification >= 20 chars so any cap is '
  'auditable from the row alone. Set with `polaris quota-set`.';

GRANT SELECT, INSERT, UPDATE, DELETE ON AgencyQuota TO polaris_app;

CREATE INDEX IF NOT EXISTS idx_token_agency_issued
    ON IdentityToken (issuing_agency_id, issued_date DESC);
CREATE INDEX IF NOT EXISTS idx_verification_agency_time
    ON VerificationEvent (requesting_agency_id, event_timestamp DESC);

-- ----------------------------------------------------------------------------
-- v9.190 / roadmap P1.8 — per-agency quotas. One function, three triggers:
--
--   trg_quota_issue   BEFORE INSERT ON IdentityToken       (issuing_agency_id, 1 day)
--   trg_quota_revoke  BEFORE UPDATE OF status ON IdentityToken, into REVOKED
--                                                          (issuing_agency_id, 1 day)
--   trg_quota_verify  BEFORE INSERT ON VerificationEvent   (requesting_agency_id, 1 hour)
--
-- The cap comes from AgencyQuota (NULL / no row = unlimited, and the function
-- returns before taking any lock or counting anything, so an uncapped agency
-- pays one primary-key lookup per write). A capped write takes a per-(kind,
-- agency) transaction-scoped advisory lock, counts the window from the
-- audit-of-record tables, and refuses the (cap + 1)th with a message the app
-- maps to HTTP 429 and a polaris_quota_refusals_total increment. The lock is
-- what makes the cap exact under concurrent writers (C9): the loser of the
-- race sees the winner's committed row when its count runs.
--
-- Unlike enforce_revocation_velocity_bound there is NO opt-out GUC: a quota
-- is a bound on what an agency may do, and a sanctioned procedure is still
-- the agency doing it. The count-based cap and the percentage bound compose;
-- whichever trips first refuses.
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION enforce_agency_quota()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
DECLARE
    v_kind      TEXT := TG_ARGV[0];      -- 'issue' | 'revoke' | 'verify'
    v_agency_id INTEGER;
    v_cap       INTEGER;
    v_window    INTERVAL;
    v_count     INTEGER;
BEGIN
    IF v_kind = 'verify' THEN
        v_agency_id := NEW.requesting_agency_id;
    ELSE
        v_agency_id := NEW.issuing_agency_id;
    END IF;

    -- Only a NEW transition into REVOKED is a revocation. Nested on purpose:
    -- PL/pgSQL compiles the whole condition, and VerificationEvent rows have
    -- no status column, so a flat `v_kind = 'revoke' AND NEW.status ...`
    -- raised "record new has no field status" on every verification.
    IF v_kind = 'revoke' THEN
        IF NEW.status <> 'REVOKED' OR OLD.status = 'REVOKED' THEN
            RETURN NEW;
        END IF;
    END IF;

    -- Cheap exit: no quota row, or no cap of this kind.
    SELECT CASE v_kind
               WHEN 'issue'  THEN issue_per_day
               WHEN 'revoke' THEN revoke_per_day
               ELSE               verify_per_hour
           END
      INTO v_cap
      FROM AgencyQuota
     WHERE agency_id = v_agency_id;
    IF v_cap IS NULL THEN
        RETURN NEW;
    END IF;

    v_window := CASE v_kind WHEN 'verify' THEN INTERVAL '1 hour' ELSE INTERVAL '1 day' END;

    -- C9: serialize the count-then-write per (kind, agency).
    PERFORM pg_advisory_xact_lock(
        hashtext('polaris.quota.' || v_kind || '.' || v_agency_id::TEXT));

    IF v_kind = 'issue' THEN
        SELECT count(*) INTO v_count
          FROM IdentityToken
         WHERE issuing_agency_id = v_agency_id
           AND issued_date > CURRENT_TIMESTAMP - v_window;
    ELSIF v_kind = 'revoke' THEN
        SELECT count(*) INTO v_count
          FROM TokenLifecycleEvent e
          JOIN IdentityToken t ON t.token_id = e.token_id
         WHERE t.issuing_agency_id = v_agency_id
           AND e.event_type = 'REVOKED'
           AND e.event_timestamp > CURRENT_TIMESTAMP - v_window;
    ELSE
        SELECT count(*) INTO v_count
          FROM VerificationEvent
         WHERE requesting_agency_id = v_agency_id
           AND event_timestamp > CURRENT_TIMESTAMP - v_window;
    END IF;

    IF v_count + 1 > v_cap THEN
        RAISE EXCEPTION
            'quota exceeded: agency % has reached its % quota of % per % (AgencyQuota)',
            v_agency_id, v_kind, v_cap,
            CASE v_kind WHEN 'verify' THEN 'hour' ELSE 'day' END
            USING ERRCODE = 'check_violation';
    END IF;

    RETURN NEW;
END$$;

DROP TRIGGER IF EXISTS trg_quota_issue ON IdentityToken;
CREATE TRIGGER trg_quota_issue
    BEFORE INSERT ON IdentityToken
    FOR EACH ROW
    EXECUTE FUNCTION enforce_agency_quota('issue');

DROP TRIGGER IF EXISTS trg_quota_revoke ON IdentityToken;
CREATE TRIGGER trg_quota_revoke
    BEFORE UPDATE OF status ON IdentityToken
    FOR EACH ROW
    EXECUTE FUNCTION enforce_agency_quota('revoke');

DROP TRIGGER IF EXISTS trg_quota_verify ON VerificationEvent;
CREATE TRIGGER trg_quota_verify
    BEFORE INSERT ON VerificationEvent
    FOR EACH ROW
    EXECUTE FUNCTION enforce_agency_quota('verify');

COMMENT ON FUNCTION enforce_agency_quota IS
  'v9.190 / P1.8 per-agency quota enforcement. Reads AgencyQuota (NULL or no '
  'row = unlimited, returned before any lock), serializes per (kind, agency) '
  'with a transaction-scoped advisory lock, counts the rolling window from '
  'the audit-of-record tables, and refuses the (cap + 1)th write with '
  '"quota exceeded: ..." (check_violation), which the app maps to HTTP 429.';

