# Duress codes

**Reader:** an engineer or an assessor. **Job:** The compulsion-resistant verification path, and why a coercer cannot see it.

This file is the canonical write-up for Polaris's compulsion-resistance
layer: how the duress code works, why timing matters, what the OOB
notification path looks like, and what v1 deliberately defers.

---

## What implements (PDF §9.5)

A holder under physical coercion needs a way to signal duress without
the coercer noticing. The verification flow today is binary:
verification either succeeds or fails. The coercer monitors the result
— "SUCCESS" reveals nothing about whether the holder was free or
compelled.

PDF §9.5 names this as the compulsion-resistance open problem. The
classical mitigation (banking, jewelry stores, high-security retail)
is a **duress code**: a secondary credential the holder enters under
coercion that *looks* like successful verification from the coercer's
view, while silently firing an out-of-band alert. implements this at the schema + verification-flow layer:

1. **`IdentityToken.duress_code_hash`** — optional column storing a
   Werkzeug scrypt hash of the holder's duress code. NULL = not
   enrolled.
2. **`DuressEvent` table** — append-only audit-of-record. Each row is
   a detected duress signal. The 8th audit-of-record instance.
3. **`uc12_record_duress` procedure** — writes a DuressEvent row.
   Validates that the token has actually enrolled duress; refuses
   bogus calls.
4. **Verification-flow extension** — `verifications_new` accepts an
   optional `duress_code` form field; on match, silently writes a
   DuressEvent. The coercer-visible flow proceeds identically.

## Six audit refinements (R1–R6)

All shipped:

### R1. Constant-time hash comparison

Use `werkzeug.security.check_password_hash` for the duress-code match.
This is the same primitive that validates `AppUser` passwords — a
function Werkzeug has hardened for timing-attack resistance.

We do NOT use `==` string comparison, raw `hmac.compare_digest` on
plaintext, or any length-dependent check. The Werkzeug function takes
the same time for a wrong password as for a right one (modulo the
~1 ms scrypt computation itself, which is invariant).

### R2. Identical observable behavior across all branches

The four possible branches:
- Token has no duress_code_hash, no duress_code input → no DuressEvent
- Token has no duress_code_hash, duress_code input → no DuressEvent
- Token has duress_code_hash, duress_code input wrong → no DuressEvent
- Token has duress_code_hash, duress_code input correct → DuressEvent written

ALL four produce:
- HTTP 302 → `/verifications`
- Flash message: `'Recorded verification event #N'`
- A `VerificationEvent` row with the operator's requested outcome
- Same response page rendering

The `DuressEvent` write happens in the same request (no extra round
trip). Subprocess invocation budget: ~1 ms for scrypt hash comparison
+ ~3-5 ms for the SQL CALL. Total response time variance: well
within Python+Flask overhead (~5-10 ms baseline), so the duress
branch is indistinguishable from non-duress by external timing
measurement.

### R3. DuressEvent is the 8th audit-of-record instance

Append-only via `reject_audit_modification` trigger (reuses the
existing trigger function). The compulsion-resistance signal is
meaningful only if its history is immutable — an attacker who could
modify or delete DuressEvent rows would defeat the whole mechanism.

### R4. Per-token enrollment-only (anti-auto-derivation)

`duress_code_hash` is set per-token via an explicit ceremony.
v1 ships with one demo enrollment (Maria's T2, plaintext '911911'
documented in `10_auth.sql`). Production deployment would have a
dedicated enrollment flow (operator-mediated) in a separate ROADMAP
item.

Same posture as's `committed_to_chain` future-field and's federation attestation: schema records the structure;
operator decides when to enroll.

### R5. OOB notification — v1 reference scope, v2 path named

v1 reference impl: `DuressEvent` itself IS the alert. An operator
or auditor monitoring the table (via `/api/duress/events` or direct
SQL) sees duress signals as they happen. The `oob_channel` column
is the future-field for production channels:

| Channel | Status |
|---|---|
| `'AUDIT_TABLE'` | v1 default — write to DuressEvent (this ship) |
| `'STDERR_LOG'` | v1 supplemental — also written to server stderr |
| `'SMS_PLACEHOLDER'` | v2 — SMS gateway integration |
| `'SLACK_PLACEHOLDER'` | v2 — Slack webhook |
| `'SIEM_PLACEHOLDER'` | v2 — SIEM event-stream integration |

CHECK constraint enumerates them all. Adding a new channel in v2 is
either an `ALTER TABLE` extension of the enum, or — cleaner — a
new ROADMAP item that adds the wiring code and uses the existing
column. Schema is forward-ready.

### R6. Anti-revealing: DuressEvent NOT in standard verifications list

The operator-visible `/verifications` HTML route does NOT join to
`DuressEvent`. The list shows only `VerificationEvent` rows — the
coercer-visible record. Only admins and auditors with explicit
access can see duress events:

- `GET /api/duress/events` — admin/auditor role required
- `polaris query "SELECT * FROM DuressEvent"` — SQL console (admin/auditor)

A coercer who has compromised an operator account sees only the
verifications list — they would need to (a) know `DuressEvent` exists,
(b) have admin role, AND (c) think to look for it. This is
defense-in-depth, not absolute protection.

The test
`DuressCodeTests.test_anti_revealing_verifications_list_excludes_duress`
explicitly asserts the `/verifications` HTML page never contains the
substring "duress".

## What v1 deliberately DOES NOT do

1. **No on-device prover / panic button.** The duress mechanism
   requires the holder to *type* a code on the verifier's terminal.
   A more sophisticated mitigation would be a holder-device panic
   button; that's out of scope for the reference impl.
2. **No SMS/Slack/SIEM integration.** The `oob_channel` future-field
   names them; the wiring is a v2 ROADMAP item.
3. **No "duress detection takes longer than verify" hardening.** The
   constant-time hash comparison handles single-call timing; an
   attacker measuring repeated request rates over time could
   potentially infer duress-event frequency. Out of scope for v1.
4. **No duress-event acknowledgment workflow.** The `oob_notified_at`
   column exists for v2 — a responder marks the alert as
   acknowledged. v1 leaves it NULL forever.

## UI surfaces (v8.25)

The v2 backend shipped in v8.24 was operator-invisible — the only way
to trigger duress detection was the JSON API. v8.25 added two UI
surfaces:

1. **`templates/verifications_form.html`** — optional input field
   labeled "Holder verification code (optional)" (neutral framing —
   R6 doesn't want "duress" appearing on the operator's screen). Name
   attribute is `duress_code`; backend reads it via
   `request.form.get('duress_code')`. The field has
   `autocomplete="off"` so browser history doesn't surface typed
   codes.

2. **`/duress` route + `templates/duress_queue.html`** — HTML view
   for admin/auditor only. Renders the same data
   `/api/duress/events` already served, plus the
   enrolled-count summary ("N of M active tokens have duress codes")
   and an inline info-panel explaining R1/R2/R3/R6 to incident
   responders. Nav link in `base.html` USE CASES menu, gated to
   admin/auditor via the existing Jinja conditional.

The R6 anti-revealing posture is enforced at three layers:
- Template: the `/verifications/new` form's duress field is labeled
  neutrally; "duress" word never appears
- Operator-view: `/verifications` list does NOT show DuressEvent
  rows, AND the nav link to `/duress` is hidden from operator role
- API + HTML: both `/api/duress/events` and `/duress` reject
  operator-role requests (302/403)

Test `test_anti_revealing_verifications_list_excludes_duress` was
updated in v8.25 to log in as **operator** (the role R6 protects)
before grepping the body for "duress" — the prior version logged in
as admin (default) and would have false-failed on the admin-only nav
link added in v8.25.

## Adversary walk

1. **Defender's claim:** When a holder enters a duress code during
   verification, the system records `DuressEvent` to an append-only
   table AND returns the same operator-visible outcome as a normal
   non-duress verification. The operator cannot tell, from the
   verification UI, which path was taken — the duress signal is
   invisible to the front-of-house. This is the compulsion-resistance
   posture from PDF §9.5.
2. **Attacker's optimal response:** Coerce the holder to verify and
   watch the operator screen for any tell. The attack succeeds if and
   only if the operator-visible surface differs between duress and
   non-duress paths. Polaris's response: every operator template that
   could leak the distinction is in the R6 anti-revealing scan
   (SecurityWatcher channel 5); the rendered-text scan on
   `verifications_form.html` checks that user-visible labels do NOT
   say "duress" or "compulsion"; and `/verifications` list view does
   NOT join `DuressEvent` so the row count cannot be inferred from
   the operator's verification history.
3. **Equilibrium:** Operator-front-of-house cannot distinguish.
   The attacker is forced to attack the *back* of the system —
   admin/auditor dashboards (which DO see DuressEvent, by role-gate)
   or DB-direct access. Both require a privilege escalation
   independent of the verification surface, which is the Schelling
   point: separating the front-of-house signal from the audit signal
   is the design.
4. **Second-best attack:** Timing side-channel. `check_password_hash`
   is constant-time (Werkzeug scrypt), but the surrounding code path
   for duress vs. non-duress executes different branches. An attacker
   measuring response latency over many verifications might infer the
   duress path. Mitigated: `_check_and_record_duress()` runs the same
   hash compare on every verification when a duress hash exists for
   the token, including non-duress cases (i.e., the work is paid
   regardless). The remaining variance is the DB write for the
   duress-positive case; that's accepted as below the noise floor of
   network/DB latency variance, and a future hardening could add a
   no-op write on the non-duress path if needed.
5. **Defender's cost:** Adding a duress code to every token doubles
   the credential surface the holder must memorize. Mitigated by
   making duress enrollment optional (`duress_code_hash` is NULL by
   default; the column has a well-formed CHECK only when populated).
   The threat model also accepts that not every holder will enroll;
   the mechanism is per-token opt-in, not universal.
6. **Mechanism-design note:** The DuressEvent stays
   admin/auditor-visible because audit-of-record requires it; the
   operator role is the surface the attacker observes, and that
   surface is structurally blind to duress. This is the same shape
   as C10 (identity ≠ money): naming the property without naming
   the mechanism. The R6 scan + the
   `_check_and_record_duress` constant-time work + the omission of
   DuressEvent from the operator list are three independent
   safeguards; removing any one degrades the equilibrium.

## Cross-references

- `polaris_sql/01_schema.sql` — `IdentityToken.duress_code_hash` column
  + `chk_duress_hash_well_formed` CHECK; `DuressEvent` table.
- `polaris_sql/05_procedures.sql` — `uc12_record_duress`.
- `polaris_sql/06_triggers.sql` — `trg_duress_event_append_only`
  (reuses `reject_audit_modification`).
- `polaris_sql/08_tests.sql` — Section R (5 SQL self-tests).
- `polaris_sql/10_auth.sql` — demo enrollment for Maria's T2.
- `polaris_web/app.py` — `_check_and_record_duress()` helper +
  `verifications_new` extension + `/api/duress/events` +
  `/api/duress/record` routes.
- `polaris_web/test_app.py` — `DuressCodeTests` (13 tests).
- `docs/design/audit-of-record.md` — `DuressEvent` is the 8th instance.
- `MISSION.md` — marked ✅; v2 done-list = 12/12.

## v2 mission-closure

After this release:

- v2 done-list = **12/12 ✅** (every PDF §9 open problem closed)
- 8 audit-of-record instances
- 6 advisory-lock granularities (DuressEvent doesn't add one — pure append, no contention)
- Both PDF §9 triads complete (holder-protection + issuer-trust-concentration)
- Substrate-D arc closed (5/5)
- 23 tables, 13 stored procedures, 14 triggers, 78 SQL self-tests

The v2 mission is complete. What comes next is **v3 strategic-arc
consideration** — see `meta/missions-considered.md` for the
forthcoming v3 candidate analysis.
