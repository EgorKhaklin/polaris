# proposals/R11-4-tiered-enrollment.md

**Risk class:** MEDIUM (propose-and-wait)
**Mission link:** v2 M2-9 (open problems, PDF §9 "Population coverage")
**Status:** PROPOSED, awaiting VANTA approval
**Effort:** ~1–2 sessions

## Problem

The PDF flags this directly under §9 *Limitations and Open Problems*:

> *"Population coverage. The schema assumes every individual holds
> exactly one active token; in practice newborns, undocumented residents,
> unhoused people, people without reliable access to reissuance
> infrastructure, and people whose biometrics do not register reliably
> with available hardware would all be outside the system. A production
> deployment would need either a tiered enrollment model or an accepted
> path for unregistered persons to participate in civic life without
> tokens."*

The schema already permits an `Individual` row without an `IdentityToken`
— the partial unique index `uq_one_active_per_person` allows zero
ACTIVE tokens per person. **The mechanical affordance exists; the
structural vocabulary does not.** Today there is no first-class way to:

- Distinguish "never enrolled" from "was enrolled, now lapsed."
- Mark a person as **EXEMPT** — recognized as a civic participant but
  deliberately not token-bound (biometric-incompatible, religious
  exemption, principled non-enrollment).
- Audit the policy decisions that move a person between enrollment
  states.
- Query civic-policy questions like "how many residents in this
  jurisdiction need outreach?" without conflating "newborn pending
  enrollment" with "lapsed token-holder" with "policy-exempt."

R11-4 turns the implicit absence into an explicit state machine, with
audit, so the system can be **honest about who is and isn't in it**
without making the system the gatekeeper of who counts.

## "Tiered enrollment," not "Polaris decides who counts"

The MISSION constraint *"Polaris is NOT an authority"* is the central
sensitivity for this proposal. R11-4 is precisely the kind of work
where the schema could overstep — and the proposal is calibrated
explicitly against that risk.

R11-4 **adds vocabulary**, not decisions:

- The enum names states (`NOT_ENROLLED`, `PENDING_ENROLLMENT`,
  `ENROLLED`, `EXEMPT`, `LAPSED`). It does not decide *who* should be
  in which state.
- The `EXEMPT` category is the explicit "civic participant without
  token" vocabulary the PDF's second clause names. It signals
  recognition, not subordination.
- The schema does **not** create a "who must enroll" register.
  External civic policy decides what services require tokens;
  external civic processes initiate enrollment. R11-4 records the
  state these processes produce.

Parallels in the existing schema:

- **C3** (one ACTIVE per individual) constrains *issuance behavior*,
  not the holder. R11-4 records *enrollment state*, not a verdict.
- **C7** (algorithm metadata via table) gives the schema *vocabulary*
  for cryptographic choices without making the schema the decider.
  R11-4 gives the schema vocabulary for enrollment states.
- **R11-6** (issuer-discretion bounds) constrains the *shape* of
  agency revocation behavior. R11-4 makes the *shape* of population
  coverage visible.

The hardest design choice (see "What this is NOT") is that the
default state for a new `Individual` row is **`NOT_ENROLLED`** — the
*absence* of enrollment, not a positive flag. The schema does not
weaponize the absence.

## Why MEDIUM

LOW would be wrong: a new vocabulary for who-is-and-isn't-in-the-system
is a sociotechnical surface that affects civic-policy queries written
against the database. Naming the states wrongly today is hard to
undo later. The acceptance criteria explicitly call out the
sociotechnical tradeoff for documentation.

HIGH would be over-cautious: the change is well-bounded (one new
table, one new view, one transition-trigger, one civic-query
function). No existing data is modified; no existing constraints are
relaxed.

## Game-theoretic structure

- **Game type:** Population coordination — Schelling-point enrollment.
  Civic life has multiple stable equilibria (high enrollment, low
  enrollment, deliberate plurality). The schema's choice of vocabulary
  *suggests* a preferred equilibrium without enforcing one.

- **Defender's claim:** The schema accommodates non-enrolled persons
  as first-class entities. `Individual` rows can exist indefinitely
  without `IdentityToken` rows. Civic queries can answer "is this
  person known" without requiring enrollment.

- **Attacker's optimal response:** Coerce enrollment by making
  non-enrollment civically incompatible — "no token, no healthcare;
  no token, no schooling." This converts an opt-in identity layer
  into an opt-out one through external policy gradient.

- **Equilibrium the defender is reaching for:** The schema *records*
  enrollment state without privileging any value of it. External
  civic policy decides what services require tokens; R11-4 just makes
  the policy's input legible. The `EXEMPT` category specifically
  enables a recognized non-token path so coercion doesn't have an
  uncontested gradient.

- **Second-best attack:** Treat `NOT_ENROLLED` as a *positive marker*
  for surveillance — "build a list of everyone who hasn't enrolled."
  This is the failure mode where R11-4's well-meant vocabulary
  becomes the substrate for the very abuse it was meant to make
  visible.

  Defender's response (this proposal): `NOT_ENROLLED` is the
  *default*, not a tag. Every `Individual` row begins as
  `NOT_ENROLLED` automatically (via the
  `seed_default_enrollment_status` trigger). Querying for it is
  trivial today (`WHERE individual_id NOT IN (SELECT
  individual_id FROM IdentityToken WHERE status <> 'REVOKED'…)`)
  and R11-4 does not make it materially easier. What R11-4 *does*
  make easier is `EXEMPT` — the positive vocabulary for
  non-enrollment-as-civic-recognition. The asymmetry is
  intentional: it should be easier to record someone's protected
  non-enrollment than to enumerate the unenrolled.

  Belt-and-suspenders mitigation: the civic-query function
  `civic_enrollment_summary()` returns **counts only, by
  jurisdiction**. Per-individual enumeration of NOT_ENROLLED is
  not a first-class query.

- **Defender's cost:** Some legitimate civic policy uses
  (vaccination outreach, voter registration drives) do need to
  enumerate the unenrolled. R11-4 does not prevent this; an
  operator with admin role can write the join directly. The cost
  is that doing so is *explicit*, not implicit-via-omission.

- **Mechanism-design note:** This is the hardest sociotechnical
  item in the v2 list. The PDF flags it honestly. R11-4's
  contribution is *visibility*: the misuse becomes a deliberate
  query against a named state, not an inferred query against
  table absence. The schema cannot prevent misuse, but it can
  make misuse named — which is the precondition for governance
  catching it.

Touches **C3** (one ACTIVE per individual) — preserves intact. The
partial unique index already permits zero ACTIVE; R11-4 doesn't
change that; it names the zero.

## Recommended approach

Four pieces:

1. **`EnrollmentStatusEvent` table** — append-only, mirrors the
   `TokenLifecycleEvent` pattern. One row per status transition,
   carrying the reason and the recording agency. Five valid statuses
   in a CHECK enum.
2. **`IndividualCurrentEnrollment` view** — derived "current status"
   per individual, computed from the latest EnrollmentStatusEvent.
   For individuals with zero events (legacy / pristine sample),
   returns `NOT_ENROLLED` as the implicit default.
3. **Seed trigger** (`AFTER INSERT ON Individual`) — auto-emits a
   `NOT_ENROLLED` event on every new `Individual` row, so every
   individual has an explicit baseline event from inception.
4. **`civic_enrollment_summary(jurisdiction)` function** — returns
   *counts by status* for a jurisdiction. Per-individual enumeration
   is not first-class; an admin who needs it writes the join
   directly, leaving an `AuthAuditLog` trace.

The state-machine transitions are *not* enforced by trigger. R11-4
treats enrollment as a policy concern: any operator with the
appropriate role can record a transition, but the order is
documented (e.g., a `LAPSED` event without a prior `ENROLLED` event
is *unusual* and should be flagged in the application layer, not
rejected by the database). This is the same posture as
`TokenLifecycleEvent.event_type` — the schema records, the
application enforces sequencing where it matters.

## Implementation sketch

### Schema (`polaris_sql/01_schema.sql`)

```sql
CREATE TABLE EnrollmentStatusEvent (
    event_id           SERIAL    PRIMARY KEY,
    individual_id      INTEGER   NOT NULL REFERENCES Individual(individual_id),
    status             VARCHAR(20) NOT NULL
        CHECK (status IN ('NOT_ENROLLED',
                          'PENDING_ENROLLMENT',
                          'ENROLLED',
                          'EXEMPT',
                          'LAPSED')),
    transition_reason  VARCHAR(60) NOT NULL,
    recorded_by_agency_id INTEGER REFERENCES Agency(agency_id),  -- nullable: SYSTEM seed events
    event_timestamp    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    notes              TEXT
);

COMMENT ON TABLE EnrollmentStatusEvent IS
  'Append-only log of enrollment-state transitions per Individual '
  '(R11-4 / M2-9). Records civic enrollment vocabulary without making '
  'the schema the gatekeeper. Five states: NOT_ENROLLED (default), '
  'PENDING_ENROLLMENT, ENROLLED, EXEMPT, LAPSED. State transitions are '
  'policy events recorded here; the schema does not enforce sequencing.';
```

The append-only invariant is added to the `reject_audit_modification`
trigger in `06_triggers.sql` (extending it to this table; same
mechanism already protects `TokenLifecycleEvent` and
`VerificationEvent`).

### Indexes (`polaris_sql/02_indexes.sql`)

```sql
-- "Latest status per individual" query (for IndividualCurrentEnrollment view).
CREATE INDEX idx_enrollment_status_event_individual_time
    ON EnrollmentStatusEvent (individual_id, event_timestamp DESC);

-- Jurisdiction-rollup counts (for civic_enrollment_summary).
-- The join goes through Individual.jurisdiction, but this index speeds
-- the per-status filtering inside the rollup.
CREATE INDEX idx_enrollment_status_event_status
    ON EnrollmentStatusEvent (status);
```

### Derived view (`polaris_sql/03_view.sql`)

```sql
CREATE OR REPLACE VIEW IndividualCurrentEnrollment AS
WITH latest AS (
    SELECT DISTINCT ON (individual_id)
           individual_id,
           status,
           transition_reason,
           recorded_by_agency_id,
           event_timestamp
    FROM   EnrollmentStatusEvent
    ORDER BY individual_id, event_timestamp DESC, event_id DESC
)
SELECT  i.individual_id,
        i.legal_name,
        i.jurisdiction,
        COALESCE(l.status, 'NOT_ENROLLED')         AS current_status,
        COALESCE(l.event_timestamp, i.enrollment_date) AS last_status_change,
        l.transition_reason                        AS last_transition_reason,
        l.recorded_by_agency_id                    AS last_recording_agency
FROM    Individual i
LEFT JOIN latest l USING (individual_id);

COMMENT ON VIEW IndividualCurrentEnrollment IS
  'Per-individual current enrollment status (R11-4). Individuals with no '
  'EnrollmentStatusEvent rows are NOT_ENROLLED by COALESCE — the absence '
  'is itself the default, not a positive flag.';
```

### Seed trigger (`polaris_sql/06_triggers.sql`)

```sql
CREATE OR REPLACE FUNCTION seed_default_enrollment_status()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    -- Every new Individual gets an explicit NOT_ENROLLED event at birth
    -- of the row, so the absence is materialized rather than inferred.
    INSERT INTO EnrollmentStatusEvent
        (individual_id, status, transition_reason, recorded_by_agency_id)
    VALUES
        (NEW.individual_id, 'NOT_ENROLLED', 'INDIVIDUAL_ROW_CREATED', NULL);
    RETURN NEW;
END$$;

CREATE TRIGGER trg_seed_default_enrollment_status
    AFTER INSERT ON Individual
    FOR EACH ROW EXECUTE FUNCTION seed_default_enrollment_status();
```

### Civic-query function (`polaris_sql/07_queries.sql` or a new file)

```sql
CREATE OR REPLACE FUNCTION civic_enrollment_summary(
    p_jurisdiction VARCHAR(10) DEFAULT NULL  -- NULL = all jurisdictions
)
RETURNS TABLE (
    jurisdiction  VARCHAR(10),
    status        VARCHAR(20),
    n_individuals INTEGER
)
LANGUAGE plpgsql AS $$
BEGIN
    RETURN QUERY
    SELECT  ice.jurisdiction,
            ice.current_status,
            count(*)::INTEGER
    FROM    IndividualCurrentEnrollment ice
    WHERE   (p_jurisdiction IS NULL OR ice.jurisdiction = p_jurisdiction)
    GROUP BY ice.jurisdiction, ice.current_status
    ORDER BY ice.jurisdiction, ice.current_status;
END$$;

COMMENT ON FUNCTION civic_enrollment_summary IS
  'Per-jurisdiction counts of individuals in each enrollment status. '
  'Counts only — per-individual enumeration is not a first-class query. '
  'Implements PDF §9 population-coverage civic-query requirement (R11-4).';
```

### Sample data (`polaris_sql/04_data.sql`)

Three new individuals demonstrating non-ENROLLED states:

```sql
-- Sample non-enrolled individuals demonstrating the vocabulary R11-4
-- gives the schema. These are policy examples, not real holders.
INSERT INTO Individual (legal_name, date_of_birth, jurisdiction) VALUES
    ('Newborn TestCase',        '2026-04-15', 'US-PA'),  -- pre-enrollment
    ('Resident Exempt-Sample',  '1955-03-20', 'US-CA'),  -- biometric-incompatible exemption
    ('Lapsed TestCase';         '1980-08-12', 'US-NY'); -- lapsed enrollment

-- The seed trigger emits NOT_ENROLLED for all three. The next two get
-- additional events demonstrating the state machine.
INSERT INTO EnrollmentStatusEvent
    (individual_id, status, transition_reason, recorded_by_agency_id, notes) VALUES
    -- The Exempt-Sample individual: civic policy decision recorded.
    ((SELECT individual_id FROM Individual WHERE legal_name='Resident Exempt-Sample'),
     'EXEMPT', 'BIOMETRIC_INCOMPATIBILITY', 3,
     'Sample row demonstrating EXEMPT category — recognized civic '
     'participation without token, per local policy review.'),
    -- The Lapsed individual: had an active token historically, now does not.
    ((SELECT individual_id FROM Individual WHERE legal_name='Lapsed TestCase'),
     'ENROLLED', 'HISTORICAL_ENROLLMENT', 1, 'Sample seed of prior ENROLLED state'),
    ((SELECT individual_id FROM Individual WHERE legal_name='Lapsed TestCase'),
     'LAPSED', 'TOKEN_EXPIRED_NOT_RENEWED', 1, 'Sample LAPSED transition for state-machine demonstration');
```

(The 04_data.sql block above is illustrative; final form will use
proper sequencing and clean up the typo.)

### Tests (`polaris_web/test_app.py`)

`TieredEnrollmentTests` class (≥9 tests):

- Every new `Individual` row gets a `NOT_ENROLLED` event via the seed
  trigger. Verified by inserting a fresh Individual and asserting one
  `EnrollmentStatusEvent` row exists with `status='NOT_ENROLLED'`.
- `IndividualCurrentEnrollment` view returns the latest status per
  individual; multiple events resolve to the most recent.
- An Individual with no events (theoretical) returns `NOT_ENROLLED`
  via the `COALESCE`. (Construct by direct INSERT bypassing the
  trigger via `ALTER TABLE … DISABLE TRIGGER`, then re-enable.)
- `civic_enrollment_summary(NULL)` returns rows for every jurisdiction
  × status combination present in the data.
- `civic_enrollment_summary('US-PA')` returns only PA rows.
- Sample data has at least one row in `EXEMPT` status.
- Sample data has at least one row in `LAPSED` status.
- CHECK constraint rejects invalid status values.
- Append-only invariant: UPDATE on `EnrollmentStatusEvent` is rejected
  by the trigger that already protects `TokenLifecycleEvent` and
  `VerificationEvent` (extended to this table).
- DELETE on `EnrollmentStatusEvent` is rejected by the same trigger.

SQL self-tests (`polaris_sql/08_tests.sql` — section L):

- L.1: `EnrollmentStatusEvent` table exists with the five-status CHECK.
- L.2: Seed trigger creates a NOT_ENROLLED event on Individual insert.
- L.3: `IndividualCurrentEnrollment` view returns one row per
  individual.
- L.4: `civic_enrollment_summary` returns count(*) > 0 for at least
  one (jurisdiction, status) tuple.
- L.5: Direct UPDATE on `EnrollmentStatusEvent` is rejected
  (append-only).

## Predicted blast radius

- `polaris_sql/01_schema.sql` — `EnrollmentStatusEvent` table (~30
  lines). Schema goes to 16 tables.
- `polaris_sql/02_indexes.sql` — two indexes on the new table (~10
  lines).
- `polaris_sql/03_view.sql` — `IndividualCurrentEnrollment` view
  (~20 lines).
- `polaris_sql/06_triggers.sql` — `seed_default_enrollment_status`
  trigger (~20 lines) and extending the append-only trigger to cover
  `EnrollmentStatusEvent` (~5 lines).
- `polaris_sql/07_queries.sql` — `civic_enrollment_summary` function
  (~30 lines).
- `polaris_sql/04_data.sql` — 3 new sample individuals + 2 additional
  enrollment events (~25 lines).
- `polaris_sql/08_tests.sql` — section L: 5 SQL self-tests (~80 lines).
- `polaris_web/app.py` — new `/individuals/enrollment` route showing
  the civic-summary table (~40 lines); per-individual enrollment
  history shown on the existing `/individuals/<id>` detail page
  (~30 lines).
- `polaris_web/templates/individuals_enrollment.html` (new, ~60 lines).
- `polaris_web/templates/individuals_detail.html` — add an Enrollment
  Timeline section (~30 lines).
- `polaris_web/test_app.py` — `TieredEnrollmentTests` (≥9 tests,
  ~220 lines).
- `DEVNOTES/tiered-enrollment.md` (new) — state-machine documentation,
  the EXEMPT-vs-NOT_ENROLLED asymmetry, the second-best-attack analysis,
  and the sociotechnical tradeoff explicitly named.
- `MISSION.md` — mark M2-9 ✅.
- `ROADMAP.md` — mark R11-4 ✅.
- `docs/DATA-MODEL.md` — `EnrollmentStatusEvent` +
  `IndividualCurrentEnrollment` section.
- `docs/API.md` — `civic_enrollment_summary` function + new routes.
- `docs/PRIVACY.md` — population-coverage subsection citing PDF §9
  and documenting the count-only civic-query design.

## Acceptance criteria

- ✅ `EnrollmentStatusEvent` table with the 5-status CHECK and
  the FK to `Individual` (cascade on delete is FORBIDDEN — the
  Individual table has no DELETE path for this exact reason).
- ✅ `IndividualCurrentEnrollment` view returns one row per
  `Individual`, defaulting to `NOT_ENROLLED` for individuals with no
  events.
- ✅ Seed trigger emits a `NOT_ENROLLED` event for every new
  `Individual` row.
- ✅ Append-only invariant applies to `EnrollmentStatusEvent`
  (extension of the existing `reject_audit_modification` trigger).
- ✅ `civic_enrollment_summary(jurisdiction)` returns *counts only*;
  no per-individual enumeration is exposed as a first-class function.
- ✅ Sample data includes at least one individual in `EXEMPT` and
  one in `LAPSED`.
- ✅ State-machine transitions are NOT trigger-enforced — application
  policy may record any state transition, with reason recorded.
- ✅ The civic-query route renders the count table by jurisdiction;
  per-individual enrollment history shown only on the existing
  individual detail page (gated by admin/auditor role).
- ✅ ≥ 9 Python tests in `TieredEnrollmentTests`.
- ✅ ≥ 5 SQL self-tests in section L.
- ✅ `DEVNOTES/tiered-enrollment.md` documents the state machine,
  the EXEMPT/NOT_ENROLLED asymmetry, the count-only civic-query
  design, the sociotechnical tradeoff, and PDF §9 anchoring.
- ✅ **C3 (one ACTIVE per individual) preserved.** R11-4 does not
  change the partial unique index.
- ✅ **C1 (append-only audit) extended.** `EnrollmentStatusEvent`
  becomes the third append-only table alongside `TokenLifecycleEvent`
  and `VerificationEvent`.
- ✅ C10 (identity ≠ money) untouched.

## What this is NOT

- **Not Polaris deciding who counts.** R11-4 records enrollment state;
  external civic policy decides who *should be* in which state. The
  default for a new `Individual` row is the *absence* of enrollment,
  materialized only so it can be transitioned out of.
- **Not a coercive-enrollment register.** R11-4 does not maintain a
  list of "people who must enroll." `NOT_ENROLLED` is the absence;
  the schema's posture is that absence is fine.
- **Not a database-enforced state machine.** Application policy
  enforces sequencing where it matters; the schema records what
  policy claims. This mirrors the existing `TokenLifecycleEvent`
  posture.
- **Not a replacement for civic-policy systems.** R11-4 gives the
  vocabulary for external policy to record its decisions; it does
  not make those decisions.
- **Not enumeration of NOT_ENROLLED as first-class.** The
  `civic_enrollment_summary` function returns counts only.
  Per-individual enumeration is possible (an admin can write the
  join) but is NOT exposed as a function — making the misuse
  case named and audit-visible.
- **Not auto-derived from IdentityToken state.** R11-4 deliberately
  *does not* auto-emit `ENROLLED` when a token transitions to ACTIVE,
  or `LAPSED` when all tokens terminal. The enrollment vocabulary is
  about *policy state*, not derivable token state. A person with no
  ACTIVE token may still be `ENROLLED` (RESERVE), `EXEMPT` (policy
  decision), or `LAPSED` (policy decision). Auto-derivation would
  collapse this distinction.
- **Not a sociotechnical neutral.** The schema *has* a posture: it
  makes recording `EXEMPT` (positive non-enrollment) frictionless and
  recording mass-enumeration of `NOT_ENROLLED` deliberate. This is
  not neutral; it is the schema's stance on the failure mode it
  exists to prevent.

## What this needs from you

"Yes do R11-4" plus:

1. **The five-status enum.** Recommend
   `NOT_ENROLLED`, `PENDING_ENROLLMENT`, `ENROLLED`, `EXEMPT`,
   `LAPSED`. Alternatives considered: a six-state version splitting
   `ENROLLED` into `ENROLLED_RESERVE` / `ENROLLED_ACTIVE`. Rejected
   because that information is already in `IdentityToken.status` and
   would duplicate.
2. **Auto-derivation policy.** Recommend **no auto-derivation** from
   IdentityToken state changes. R11-4 records *policy state*, not
   *token state*. Alternative: auto-emit `LAPSED` when an individual's
   last non-terminal token transitions to terminal. Rejected because
   it conflates "token lost" with "civic enrollment ended" — these
   are different.
3. **State-machine enforcement.** Recommend **application-layer
   enforcement, not trigger.** The schema records what policy
   claims; sequencing checks belong with the policy layer. Alternative:
   a trigger enforcing transitions (e.g., LAPSED only after
   ENROLLED). Rejected because it makes the schema a policy
   participant.
4. **Sociotechnical doc tone.** Recommend the
   `DEVNOTES/tiered-enrollment.md` text *names* the failure mode
   ("NOT_ENROLLED weaponized as a surveillance marker") and
   *defends against it* by the asymmetric design (EXEMPT
   frictionless, mass-NOT_ENROLLED-enumeration deliberate). A more
   neutral framing exists but would dodge the question the PDF
   raises.
5. **EXEMPT reason vocabulary.** Recommend a free-text
   `transition_reason VARCHAR(60)` rather than a CHECK-constrained
   enum. The space of legitimate exemption reasons (biometric
   incompatibility, religious exemption, conscientious objection,
   recognized civic alternative path) is open-ended; a closed
   vocabulary would itself become a policy decision.
