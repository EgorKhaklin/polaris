# Tiered enrolment

**Reader:** an engineer or an assessor. **Job:** The evidence tiers behind an issued token.

---

## What this is

A first-class vocabulary for enrollment state. Every `Individual` row
has a current enrollment status drawn from a five-value enum:

| Status | Meaning |
|---|---|
| `NOT_ENROLLED` | Default. The absence of enrollment, materialized via the seed trigger. Newborns, undocumented residents, the unhoused. |
| `PENDING_ENROLLMENT` | Enrollment process initiated; biometrics or documentation in progress. |
| `ENROLLED` | Holds at least one non-terminal IdentityToken (RESERVE or ACTIVE). Recorded as a *policy event*, never auto-derived from token state. |
| `EXEMPT` | Civic-policy recognition of non-token participation: biometric incompatibility, religious exemption, conscientious objection, an alternative-path participant. |
| `LAPSED` | Was ENROLLED, now isn't, by policy event. Distinct from NOT_ENROLLED. |

Transitions are recorded in `EnrollmentStatusEvent` (append-only). The
`IndividualCurrentEnrollment` view returns the latest event's status
per individual, falling back to `NOT_ENROLLED` via `COALESCE` if no
events exist. implements the schema's answer to the PDF §9 second clause:
*"an accepted path for unregistered persons to participate in civic
life without tokens."* `EXEMPT` is that path made first-class.

## What this is NOT is **not Polaris deciding who counts.** It adds *vocabulary*
for policy state, never *decisions* about which state a person
should be in. The MISSION constraint *"Polaris is NOT an authority"*
is the central sensitivity here; the design is calibrated against
overreach in three places:

1. **`NOT_ENROLLED` is the default**, not a positive flag. The
   absence of enrollment is materialized only so it can be
   transitioned out of cleanly.
2. **No auto-derivation from token state.** A person with no ACTIVE
   token may be ENROLLED (RESERVE), EXEMPT, or LAPSED — these are
   different policy events with different meanings, and auto-deriving
   would collapse the distinction.
3. **No trigger-enforced state machine.** Sequencing checks belong
   with policy code; the schema records what policy claims. Same
   posture as `TokenLifecycleEvent`.

## The asymmetric design

The hardest design choice in is the *asymmetry between EXEMPT
and NOT_ENROLLED*. They look superficially similar — both are "no
token" — but they're treated differently on purpose.

**EXEMPT is frictionless.** Recording an individual as EXEMPT is a
single `INSERT INTO EnrollmentStatusEvent`. The vocabulary exists,
the route exists in the UI roadmap, the audit row is a positive
recognition event. The PDF's "accepted path without tokens" gets
first-class affordance.

**Mass enumeration of NOT_ENROLLED is deliberate.** The civic-query
function `civic_enrollment_summary(jurisdiction)` returns *counts
only*, by (jurisdiction, status). Per-individual enumeration is
possible — an admin can write the join against
`IndividualCurrentEnrollment` directly — but it is NOT exposed as a
function and shows up in `AuthAuditLog` when an admin runs it.

Why this matters: the second-best attack against (after the
primary vocabulary defense holds) is to *weaponize NOT_ENROLLED as a
surveillance marker*. "Build me a list of everyone in this
jurisdiction who hasn't enrolled." The asymmetry says: that query is
*possible* but it is *named, deliberate, and audit-visible* — not
inferred via implicit-from-absence, the way the pre- schema
forced you to write the query.

The schema cannot prevent the misuse. It can make the misuse named.
Naming is the precondition for governance catching it.

## Adversary walk

1. **Defender's claim:** The schema accommodates non-enrolled
   persons as first-class entities. `Individual` rows exist
   indefinitely without `IdentityToken` rows. Civic queries answer
   "is this person known" without requiring enrollment.

2. **Attacker's optimal response:** Coerce enrollment by making
   non-enrollment civically incompatible — "no token, no
   healthcare; no token, no schooling." Convert an opt-in identity
   layer into an opt-out one through external policy gradient.

3. **Equilibrium:** The schema records enrollment state without
   privileging any value of it. External civic policy decides what
   services require tokens; just makes the policy's input
   legible. `EXEMPT` provides a recognized non-token path so
   coercion doesn't have an uncontested gradient.

4. **Second-best attack:** Treat `NOT_ENROLLED` as a positive
   marker — "build a list of everyone who hasn't enrolled."

5. **Defender's response:** The asymmetric design above. EXEMPT
   easy, mass-NOT_ENROLLED-enumeration deliberate.

6. **Defender's cost:** Some legitimate civic uses (vaccination
   outreach, voter-registration drives) do need to enumerate the
   unenrolled. doesn't prevent this; it makes it *explicit*,
   not implicit-via-omission.

7. **Mechanism-design note:** This is the sociotechnically
   hardest item in the v2 list. The PDF flags it honestly. The
   contribution is *visibility* — the misuse becomes a deliberate
   query against a named state.

## Why "no auto-derivation" matters

The temptation is real: emit `ENROLLED` automatically when an
individual gets a non-terminal token, emit `LAPSED` automatically
when their last non-terminal token goes terminal. It would save
hand-recording. deliberately rejects this. Three reasons:

1. **A person can be EXEMPT regardless of token state.** Someone
   recognized as a civic participant under an alternative path
   might still have a historical token; auto-deriving from token
   state would clobber their EXEMPT marker.
2. **PENDING_ENROLLMENT is a real state** that exists between
   "person known to the system" and "person holds a token." It
   describes the biometric-intake window. Auto-derivation would
   skip it.
3. **LAPSED is a policy event with a reason.** Auto-deriving
   "tokens went terminal therefore civic enrollment ended" is
   exactly the conflation the schema should not make. A token
   being administratively revoked is not the same as the
   individual being civically un-enrolled.

The cost is hand-recording. The benefit is the schema doesn't
make policy decisions.

## Where the seed trigger fires

`trg_seed_default_enrollment_status` is an `AFTER INSERT ON
Individual` trigger that inserts a `NOT_ENROLLED` event with
`transition_reason='INDIVIDUAL_ROW_CREATED'` and
`recorded_by_agency_id=NULL` (SYSTEM event).

It fires AFTER INSERT specifically so `individual_id` (a `SERIAL`)
is populated by the time the trigger runs. A BEFORE INSERT trigger
would see `NULL`.

The trigger fires for *every* Individual INSERT, including the v1
sample data when loaded fresh. This is correct: the seeded sample
individuals all begin in the default state, and the 04_data.sql
load then layers on additional events (ENROLLED for the token
holders, LAPSED for David's case, etc.) on top of the seed events.

If a future migration needs to insert Individual rows WITHOUT the
default event (e.g., importing pre-existing enrollment data from a
predecessor system), the trigger can be disabled with `ALTER TABLE
… DISABLE TRIGGER trg_seed_default_enrollment_status` for the
duration of the import. Requires table-owner privileges; `polaris_app`
doesn't have them, so this is a DBA operation.

## Cross-references

- PDF §9 "Population coverage" — original problem statement.
- `MISSION.md` *Polaris is NOT an authority* — the constraint calibrates against.
- `proposals/-tiered-enrollment.md` — the original proposal
  with the alignment audit.
- `docs/operator/PRIVACY.md` — Population-coverage subsection citing this
  document.
- / `docs/design/issuer-discretion.md` — the *exit* leg of the
  "schema doesn't weaponize itself against the holder" triad; is the *entry* leg., when shipped, will be the
  *recovery* leg.)
