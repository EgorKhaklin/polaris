# proposals/R11-6-issuer-discretion-bounds.md

**Risk class:** MEDIUM (propose-and-wait)
**Mission link:** v2 M2-11 (open problems; defends UC-1 failure-mode
concern about denaturalization-style mass revocation)
**Status:** PROPOSED, awaiting VANTA approval
**Effort:** ~1 session

## Problem

A single agency that holds ISSUE authorization can also drive
revocation through the lifecycle state machine. Nothing in the schema
stops an agency that decides to denaturalize a class of holders from
flipping every one of its issued tokens to `REVOKED` in a single
batch. The append-only audit trail captures *that* it happened, not
*that it was disallowed.*

UC-1's failure-mode analysis flags this. The audit trail is necessary
but not sufficient: a regime that controls the audit reviewer is
unconstrained, and even an honest audit only catches the abuse after
the fact. M2-11 says: encode the bound in the schema itself, so the
mass-revocation pattern is rejected by the database before any
auditor is in the loop.

The shape we want: a single agency cannot revoke more than **N%** of
its outstanding issued tokens in any rolling **W-day window** without
a higher-authority **co-signature**.

## Why MEDIUM

The change touches the token state machine (every revocation goes
through the new check) and introduces a new persistent policy
surface. The numbers N and W are policy choices that an operator
in production would tune; the v1 reference values must be defensible.

LOW would be wrong: the new constraint can reject legitimate-looking
operational behavior when an agency happens to revoke at scale
(e.g., a bulk recall of compromised hardware). The bound must be
chosen so it does not interfere with that case.

HIGH would be over-cautious: the change is well-bounded (one new
table, one new procedure, one new trigger, one new test class). No
breaking schema migration; existing rows continue to behave the
same way as long as agency revocation rates stay under the bound.

## "Constitutional limits on issuer discretion," not "Polaris becomes an authority"

The PDF's §9 names the production requirement as **"constitutional limits
on issuer discretion."** That phrase is precise and load-bearing. R11-6 is
a structural constraint on the *issuing agency's procedural behavior*, not
a Polaris-side decision about any individual holder.

This matters because MISSION.md's "Polaris is NOT an authority" rules out
Polaris deciding "this person cannot vote / borrow / cross a border." It
does not rule out structural constraints on how *agencies* may operate
inside Polaris — which is the same category as **C3** (one ACTIVE per
individual: a constraint on issuance behavior, not a holder verdict) and
**C7** (algorithm metadata via table: a constraint on what an agency may
sign with). R11-6 sits in that same category: a constraint on the rate
and approval pattern of agency-driven revocation.

The agency still makes the revocation decision. Polaris simply refuses
to record an unapproved mass-revocation pattern. The decision authority
remains with the agency; the procedural authority (over the *shape* of
agency behavior) is what the polity exercises through the schema.

## Game-theoretic structure

- **Game type:** Principal-agent monitoring. The polity is the
  principal; the issuing agency is the agent. The agent has private
  information (which token belongs to whom) and operational latitude
  (timing of revocations). The principal wants a credible bound on
  the agent's discretion without policing every individual revocation.

- **Defender's claim:** No single agency can revoke more than N% of
  its outstanding issued tokens in any W-day window unless a
  higher-authority co-signer authorizes the action.

- **Attacker's optimal response:** Spread revocations evenly to stay
  just under N% per window indefinitely. For N=5% / W=30 days, an
  agency can still revoke ~60% of its outstanding population per
  year — slowly, observably, against a trend that human auditors
  and downstream systems can see.

- **Equilibrium the defender is reaching for:** Mass revocation is
  either co-signed (and thus traceable to two agencies, not one) or
  rate-limited to a pace that defeats the surprise element of
  denaturalization. Either outcome is acceptable.

- **Second-best attack:** Compromise the co-signer. If the co-signer
  is a single fixed agency, that agency becomes the new single
  point of failure. Defender's response (this proposal): the
  co-signer is *any* agency holding the `BOTH` authorization for
  the algorithm of the revoked tokens — a non-empty set in
  practice — and the co-signer's identity is recorded in the
  audit row. A third-party auditor can detect a single co-signer
  appearing repeatedly across mass-revocation events.

- **Mechanism-design note:** This is a Schelling-point problem on N
  and W. Too low and legitimate operational revocations get
  blocked. Too high and the bound is not a meaningful constraint.
  v1 reference: N=5% / W=30 days. v2 reference values are operator-
  tunable per agency via `IssuerDiscretionPolicy`.

Strengthens **C5** (audit-trail completeness) — the audit row now
encodes the co-signer when one is required, making the constraint
visible from the lifecycle event alone.

## Recommended approach

Three pieces:

1. **`IssuerDiscretionPolicy` table** — per-agency overrides over
   the system defaults for N and W. Empty row implies the system
   default applies. Lets a production deployment tune the bound
   for an agency that has legitimate large-volume revocation
   workflows without weakening the global default.
2. **`uc8_revoke_token(...)` stored procedure** — the single
   sanctioned path for revocation. Acquires a per-agency
   `pg_advisory_xact_lock` so the read-then-write rate check is
   atomic across concurrent calls (C9). Runs the rate check,
   accepts an optional `p_cosigner_agency_id`, validates the
   co-signer's authorization, transitions the token to REVOKED,
   AND publishes to `RevocationList` (mirroring UC-4). The
   TokenLifecycleEvent row gets `reason_code` extended to carry
   the co-signer reference; the RevocationList row keeps the
   standard verifier-facing reason-code vocabulary.
3. **Belt-and-suspenders trigger** — a BEFORE-UPDATE trigger on
   `IdentityToken.status` that fires when transitioning into
   `REVOKED`. If a per-txn `polaris.revoke_check_done` GUC is
   absent, the trigger raises. This catches direct UPDATEs that
   bypass the procedure.

The co-signer is *recorded*, not validated cryptographically. v1
treats co-signature as a procedural and audit primitive; a real
deployment would tie it to a hardware-attested signing operation
from the co-signer. R11-6 is the schema-level Schelling point that
makes the cryptographic version possible later.

The advisory-lock approach is preferred over SERIALIZABLE-with-retry
because (a) the contention is naturally agency-scoped (cross-agency
revocations don't conflict), (b) it composes with the rest of the
schema's READ COMMITTED isolation, and (c) the lock is automatically
released at transaction end with no application-side retry logic
required.

## Implementation sketch

### Schema (`polaris_sql/01_schema.sql`)

```sql
-- System defaults live in GUC-like settings rather than a row, so
-- they cannot be deleted. Per-agency overrides go in this table.
CREATE TABLE IssuerDiscretionPolicy (
    agency_id           INTEGER PRIMARY KEY
                        REFERENCES Agency(agency_id),
    max_revoke_percent  NUMERIC(5,2) NOT NULL
                        CHECK (max_revoke_percent > 0
                               AND max_revoke_percent <= 100),
    window_days         INTEGER NOT NULL
                        CHECK (window_days BETWEEN 1 AND 365),
    set_by_admin        VARCHAR(50) NOT NULL,
    set_at              TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    -- A policy that loosens the system default requires its own
    -- justification recorded inline.
    justification       TEXT NOT NULL
                        CHECK (length(justification) >= 20)
);

COMMENT ON TABLE IssuerDiscretionPolicy IS
  'Per-agency overrides to the system-wide N% / W-day bound on '
  'revocation velocity. Absence of a row means the system default '
  '(5% / 30 days) applies. Justification field is required so any '
  'loosening is auditable.';
```

System defaults are set as PostgreSQL custom GUCs at cluster init
(driven from `09_grants.sql` or a new dedicated file):

```sql
ALTER DATABASE polaris SET polaris.default_max_revoke_percent = 5.00;
ALTER DATABASE polaris SET polaris.default_window_days       = 30;
```

### Procedure (`polaris_sql/05_procedures.sql`)

```sql
-- UC-8: Bounded Revocation
--
-- The single sanctioned revocation path. Enforces the rolling-window
-- N% / W-day rate against the issuing agency. If the bound would be
-- exceeded, a co-signer is required; the co-signer must hold BOTH
-- authorization on the token's algorithm and must differ from the
-- actor. Mirrors the UC-4 pattern: transitions the token to REVOKED
-- AND publishes to RevocationList in the same transaction.
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

    -- Resolve token state. Bound applies to the *issuing* agency
    -- (not necessarily the actor). Reject already-terminal tokens
    -- so a token cannot be double-revoked or revoked-after-LOST,
    -- matching the UC-4 pattern.
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
    SELECT max_revoke_percent, window_days
      INTO v_max_percent, v_window_days
    FROM IssuerDiscretionPolicy
    WHERE agency_id = v_issuing_agency_id;
    IF NOT FOUND THEN
        v_max_percent := current_setting('polaris.default_max_revoke_percent')::NUMERIC;
        v_window_days := current_setting('polaris.default_window_days')::INTEGER;
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

    v_observed_percent := (v_recent_revokes::NUMERIC / v_outstanding) * 100;

    IF v_observed_percent > v_max_percent THEN
        IF p_cosigner_agency_id IS NULL THEN
            RAISE EXCEPTION
                'Revocation rate for agency % would reach %% in window %d (bound %%); co-signer required',
                v_issuing_agency_id, v_observed_percent,
                v_window_days, v_max_percent
                USING ERRCODE = 'check_violation';
        END IF;

        -- Co-signer must be a *different* agency with BOTH on the
        -- algorithm of the token being revoked.
        IF p_cosigner_agency_id = p_actor_agency_id THEN
            RAISE EXCEPTION
                'Co-signer must differ from actor';
        END IF;

        SELECT aa.authorization_type INTO v_cosigner_auth
        FROM AgencyAlgorithmAuth aa
        JOIN IdentityToken t ON t.algorithm_id = aa.algorithm_id
        WHERE aa.agency_id = p_cosigner_agency_id
          AND t.token_id    = p_token_id;
        IF NOT FOUND OR v_cosigner_auth <> 'BOTH' THEN
            RAISE EXCEPTION
                'Co-signer agency % lacks BOTH authorization on the relevant algorithm',
                p_cosigner_agency_id;
        END IF;
    END IF;

    -- Step 1: transition the token to REVOKED. Set audit-trigger GUCs
    -- so the AFTER UPDATE trigger writes a properly-attributed
    -- lifecycle event automatically (same pattern as UC-4).
    PERFORM set_config('polaris.actor_agency_id', p_actor_agency_id::TEXT, true);
    PERFORM set_config('polaris.reason_code',
        CASE WHEN p_cosigner_agency_id IS NULL
             THEN p_reason_code
             ELSE p_reason_code || ' [COSIGN:' || p_cosigner_agency_id::TEXT || ']'
        END,
        true);
    -- Signal to the belt-and-suspenders trigger that the bound has
    -- been checked under this transaction.
    PERFORM set_config('polaris.revoke_check_done', '1', true);

    UPDATE IdentityToken
       SET status = 'REVOKED'
     WHERE token_id = p_token_id;

    -- Step 2: publish to the verifier-facing revocation list (UC-4
    -- pattern). Without this, verifier-side freshness checks would
    -- not see the revocation; the token state would diverge from
    -- the published CRL.
    INSERT INTO RevocationList
        (token_id, revoked_by_agency_id, effective_date,
         reason_code, published_location)
    VALUES
        (p_token_id, p_actor_agency_id, CURRENT_DATE,
         p_reason_code, p_published_location);
END$$;
```

Note: `p_reason_code` is `VARCHAR(40)` rather than `VARCHAR(60)` to
match the existing `RevocationList.reason_code` CHECK domain. The
co-signer tag lives in the *lifecycle event* `reason_code` (which is
`VARCHAR(60)` and not domain-checked), not in the RevocationList row
— so the verifier-facing CRL stays in the standard reason-code
vocabulary while the audit trail carries the procedural metadata.

### Trigger (`polaris_sql/06_triggers.sql`)

```sql
CREATE OR REPLACE FUNCTION enforce_revocation_velocity_bound()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    -- Only fire on transitions INTO 'REVOKED'
    IF NEW.status <> 'REVOKED' OR OLD.status = 'REVOKED' THEN
        RETURN NEW;
    END IF;

    -- Procedure path sets this GUC. If absent, this is a raw UPDATE
    -- and we must re-enforce the bound the hard way.
    IF current_setting('polaris.revoke_check_done', true) = '1' THEN
        RETURN NEW;
    END IF;

    RAISE EXCEPTION
        'Direct UPDATE to status=REVOKED is not allowed. Use uc8_revoke_token().';
END$$;

CREATE TRIGGER trg_enforce_revocation_velocity
    BEFORE UPDATE OF status ON IdentityToken
    FOR EACH ROW
    EXECUTE FUNCTION enforce_revocation_velocity_bound();
```

Belt-and-suspenders: the trigger does not re-do the rate math (the
procedure already did it within the same transaction). It simply
refuses raw UPDATEs that bypass the procedure. Any production path
that needs to revoke must call `uc8_revoke_token`.

### Tests (`polaris_web/test_app.py`)

`IssuerDiscretionBoundsTests` class:

- Revoking a single token under the bound succeeds without
  co-signer. **Verifies both** `IdentityToken.status='REVOKED'`
  **and** the new `RevocationList` row exist.
- Revoking the (N+1)th token in window W without co-signer raises
  `check_violation`; no `RevocationList` row appears (atomicity).
- Revoking the (N+1)th token in window W with a valid co-signer
  succeeds; the audit row carries `[COSIGN:<id>]` and the
  `RevocationList` row uses the plain reason-code vocabulary.
- Co-signer = actor agency → procedure rejects.
- Co-signer without BOTH authorization on the token's algorithm →
  procedure rejects.
- Already-terminal token (REVOKED / LOST / EXPIRED) → procedure
  rejects with "already terminal" message.
- Per-agency override (set via `IssuerDiscretionPolicy`) loosens
  or tightens the bound for that agency without affecting others.
- Direct `UPDATE IdentityToken SET status='REVOKED'` raises (the
  belt-and-suspenders trigger catches it; no audit row written).
- Synthetic mass-revocation attempt: agency tries to revoke 100
  tokens in one transaction; first ~N succeed, (N+1) raises, txn
  rolls back; final state has zero revocations and zero
  `RevocationList` rows.
- Legitimate operational revocation under the bound proceeds
  normally across days/months in a property test.
- After window expires, the rolling count resets and revocation
  proceeds again at the same pace.

**Concurrency test (C9, in `ConcurrencyTests`):**

- **Race the boundary with real threads.** Set up an agency at
  exactly the Nth revocation in window W. Spawn `T` real threads
  (T ≥ 5), each attempting the (N+1)th revocation on a different
  token without a co-signer. Use `concurrent.futures.ThreadPoolExecutor`
  with `psycopg2` connections per thread (mocks are forbidden by
  C9). Expected outcome: **exactly zero** of the T threads succeed
  — the first to acquire `pg_advisory_xact_lock` reads the rate
  pre-its-own-insert and finds itself at the boundary; subsequent
  threads see the post-commit state and find themselves over.
  Without the lock, two threads could both pass the check and
  both insert, breaking the bound. The test asserts the final
  revocation count equals N (not N+1, not N+T).
- **Cross-agency revocations do not block each other.** Two
  threads, two different agencies, both at their respective
  boundaries. Both should complete in parallel (lock is
  agency-scoped via `hashtext('polaris.revoke.' || agency_id)`).
  Assert wall-clock time < (single-thread time × 1.5) to confirm
  parallelism.

## Predicted blast radius

- `polaris_sql/01_schema.sql` — `IssuerDiscretionPolicy` table
  (~25 lines)
- `polaris_sql/05_procedures.sql` — `uc8_revoke_token` with
  advisory-lock + RevocationList insert (~120 lines)
- `polaris_sql/06_triggers.sql` — `enforce_revocation_velocity_bound`
  trigger (~25 lines)
- `polaris_sql/09_grants.sql` — `ALTER DATABASE ... SET
  polaris.default_max_revoke_percent` / `polaris.default_window_days`
  cluster GUCs (~5 lines)
- `polaris_sql/04_data.sql` — one or two `IssuerDiscretionPolicy`
  override rows for sample agencies that need them (~15 lines)
- `polaris_sql/08_tests.sql` — 4–6 SQL-side tests covering the
  trigger and procedure (~80 lines)
- `polaris_web/app.py` — add `/uc8/revoke` route plus template
  (~70 lines) — keeps the surface symmetric with UC-1, UC-4, UC-5,
  UC-7
- `polaris_web/test_app.py` — `IssuerDiscretionBoundsTests` class
  (~320 lines, ~12 tests) + two new tests in `ConcurrencyTests`
  for the advisory-lock behavior (~80 lines)
- `polaris_web/templates/uc8_revoke.html` — minimal form with
  optional co-signer field and required published_location
  (~70 lines)
- `DEVNOTES/issuer-discretion.md` (new) — N/W choices, alternatives
  considered, adversary walk, operator-tuning guide, advisory-lock
  rationale
- `DEVNOTES/concurrency.md` — append a new section documenting
  the `pg_advisory_xact_lock('polaris.revoke.' || agency_id)`
  pattern alongside the existing concurrency invariants
- `MISSION.md` — mark M2-11 ✅
- `ROADMAP.md` — mark R11-6 ✅
- `docs/DATA-MODEL.md` — `IssuerDiscretionPolicy` section
- `docs/API.md` — `/uc8/revoke` endpoint
- `docs/SECURITY.md` — denaturalization-resistance subsection
  citing PDF §9 "constitutional limits on issuer discretion"

## Acceptance criteria

- ✅ `IssuerDiscretionPolicy` table with the percent + window CHECKs
  and the justification length floor.
- ✅ `uc8_revoke_token` procedure enforces the rolling-window rate
  check with an optional co-signer escape hatch.
- ✅ `uc8_revoke_token` **publishes to `RevocationList` in the same
  transaction** as the `IdentityToken.status='REVOKED'` update
  (mirrors UC-4; verifier-side CRL stays in sync with token state).
- ✅ The audit row produced by a co-signed revocation contains the
  `[COSIGN:<agency_id>]` tag in `reason_code`. The `RevocationList`
  row uses only the canonical reason-code vocabulary.
- ✅ Already-terminal tokens (`REVOKED`/`LOST`/`EXPIRED`) cannot be
  revoked again — procedure rejects with explicit error.
- ✅ Trigger rejects raw UPDATE-to-REVOKED that bypasses the
  procedure.
- ✅ **Concurrency: real-threading test** (C9) confirms the
  advisory-lock prevents two simultaneous (N+1)th revocations from
  both succeeding. Final revocation count = N, never N+1 or N+T.
- ✅ **Concurrency: cross-agency revocations run in parallel.** The
  lock granularity is `(agency_id)`, not global; two different
  agencies revoking at the same time do not block each other.
- ✅ Synthetic mass-revocation test: 100-token batch rolls back
  cleanly at the (N+1)th call; final state has zero
  `RevocationList` rows from the attempt.
- ✅ Legitimate operational revocation (≤ N% per agency per W days)
  proceeds without co-signer.
- ✅ Per-agency override (in `IssuerDiscretionPolicy`) takes effect
  for that agency only.
- ✅ Co-signer = actor agency rejected.
- ✅ Co-signer without BOTH authorization rejected.
- ✅ ≥ 11 new tests in `IssuerDiscretionBoundsTests` + ≥ 2 new
  tests in `ConcurrencyTests`.
- ✅ `DEVNOTES/issuer-discretion.md` documents the N/W choices,
  the adversary walk, the advisory-lock rationale, and the PDF
  §9 anchoring.
- ✅ **C1 (append-only audit) preserved AND strengthened** — the
  co-signer is now visible in the lifecycle event `reason_code`.
- ✅ **C7 (algorithm metadata via table) preserved AND strengthened**
  — co-signer authorization is resolved via `AgencyAlgorithmAuth`.
- ✅ **C9 (concurrency tests use real threading) honored** — the
  advisory-lock race test uses `psycopg2` connections per thread.
- ✅ C10 (identity ≠ money) untouched.

## What this is NOT

- **Not Polaris becoming an authority over the holder.** Polaris
  does not decide whether *this person* should retain a token. The
  agency makes that decision. Polaris constrains the *shape* of
  agency behavior — specifically, the rate and approval pattern of
  agency-driven revocation. The PDF's exact framing is
  "constitutional limits on issuer discretion."
- Not a real cryptographic co-signature. v1 records the co-signer
  procedurally. R12+ can layer hardware-attested signing on top.
- Not protection against selective revocation under the bound (an
  agency that revokes 4.99%/month for a year still gets to ~60%).
  That pattern is observably-slow and is meant to be caught by
  audit + downstream systems, not by the schema.
- Not protection against system-wide collusion (every agency
  captured). The schema's leverage ends when every authorized
  signer is compromised. M2-11 covers single-agency abuse, which
  is the case UC-1 and PDF §9 name.
- Not a re-instatement procedure. Reversing a wrongful revocation
  is out of scope here; R11-2 (catastrophic-loss recovery) is the
  adjacent proposal that overlaps.
- Not extended to `LOST` or `EXPIRED` events. Those are
  individual-scale lifecycle transitions, not bulk operational
  ones. If a real abuse pattern emerged using `LOST` as a
  laundered revocation, a follow-up would extend the bound.
- Not a replacement for the existing `RevocationList` publication
  path. UC-8 *adds* the velocity check and co-signer requirement
  ON TOP of the existing publish-to-CRL behavior; the CRL row
  shape is unchanged.

## What this needs from you

"Yes do R11-6" plus:

1. **N (max revoke percent per window).** Recommend **5.00**. Cap
   on what a single agency can revoke without co-sign in a month.
   Trade-off: lower = stronger bound but more friction on
   legitimate bulk recalls. Higher = denaturalization fits inside
   the bound.
2. **W (window days).** Recommend **30**. Rolling 30-day window
   matches operational reporting cadence.
3. **Co-signer eligibility.** Recommend **any agency with `BOTH`
   on the token's algorithm and not equal to the actor**. Wider
   eligibility = more resilience against compromise of a fixed
   co-signer. Narrower = more legible audit but single point of
   failure.
4. **Whether to enforce on LOST events too.** Recommend **no** for
   v1; revisit if abuse pattern emerges. (LOST is supposed to be
   individual-driven; bulk LOST is itself a red flag the audit
   surface can catch.)
5. **Where the system defaults live.** Recommend **`ALTER DATABASE`
   GUCs** so the default cannot be silently mutated by a single
   row-level DELETE, but is still operator-tunable via a SET.
   Alternative: a single `SystemDefault` row with a CHECK; less
   PostgreSQL-idiomatic but more discoverable from `\dt`.
