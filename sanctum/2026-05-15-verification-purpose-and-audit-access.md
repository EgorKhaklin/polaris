# Sanctum: verification-purpose-and-audit-access

**Date:** 2026-05-15
**Petitioner:** agent (Claude, Opus 4.7) speaking as the Architect;
with the Anti-Architect (v9.11) contesting
**Principal:** VANTA
**Trigger:** v9.19 architecture study identified two vocation-direct
anti-coercion advances that touch the audit-of-record contract
constitutionally. Both were flagged as Sanctum-class because they
modify the *meaning* of audit records (adding required fields) and
add a new audit table that audits its own readers. VANTA: *"proceed
with the joint recommendation."*
**Risk class:** MEDIUM-HIGH (touches v8.20 audit-of-record contract;
modifies VerificationEvent semantics; introduces meta-audit table).
**Status:** DECIDED + CLOSED 2026-05-15 — Position A (ship both per
the joint recommendation; schema migrations added; both vocation-
direct; both pinned by structural invariants) selected per heavy-
production posture (v8.31 §III.6) following VANTA's *"proceed with
the joint recommendation"*.

---

## I. The Matter

The v9.19 ship adopted items 1+2+5 from the architecture-study
recommendation (ontology + Object Card + authz-audit). Items 3 and
6 were held back as Sanctum-class:

**Item 3 — Verification-purpose lineage.** Every `VerificationEvent`
records `requesting_agency_id` and `context_id` but does *not* record
the *specific stated purpose* of this particular verification.
A coercive verification's evidentiary chain currently shows WHO
requested + WHAT context — but not WHY this specific check, from this
specific operator, at this specific moment. Adding an
operator-supplied `requesting_purpose_text` field gives that
evidentiary chain.

**Item 6 — Audit-access audit trail.** Polaris's audit tables
(`TokenLifecycleEvent`, `VerificationEvent`, `AuthAuditLog`) are
append-only on writes. *Reads* are not currently recorded. Subtle
surveillance often takes the form of insiders silently querying
audit logs to learn who-knows-what about a target. A meta-audit
table that records who-queried-audit-when adds accountability for
the watchers.

Both modify the audit-of-record contract. Both directly advance the
anti-coercion vocation. Both warrant a Sanctum.

## I.0 Vocation alignment

Both items are **directly vocation-aligned**:

- **Item 3** advances anti-coercion: a coerced verification leaves a
  stated-purpose trail. Lying about purpose-of-verification becomes
  a separate offense recorded permanently. The duress-code primitive
  (R11-5) gives the holder a way to signal coercion silently; the
  verification-purpose field gives the system a way to record the
  coercer's stated context. Two complementary anti-coercion surfaces.

- **Item 6** advances anti-coercion: makes silent surveillance
  visible. Insiders querying audit logs without legitimate purpose
  is a class of attack. Logging the meta-access creates accountability
  for the watchers — the audit's audit.

## II. The architect's positions

### Position A — Ship both items as a v9.20 composite — joint recommendation

Two new migrations:
- `2026-05-15-002-verification-purpose.up.sql` — adds
  `VerificationEvent.requesting_purpose_text VARCHAR(280)` (nullable
  initially; future Sanctum may make NOT NULL once backfilled). The
  append-only trigger on VerificationEvent already protects this
  column from UPDATE/DELETE.
- `2026-05-15-003-audit-access-log.up.sql` — adds new table
  `AuditAccessLog` (read-of-audit records) with append-only trigger
  (mirrors existing audit-table pattern). Schema: `access_id`,
  `accessed_at`, `actor_user_id` FK to AppUser, `accessed_table`
  (TokenLifecycleEvent | VerificationEvent | AuthAuditLog),
  `filter_criteria_jsonb`, `result_row_count`.

App layer wiring:
- Verification-purpose: new optional form field on `/verifications/new`;
  passed through to `uc8_verify_token` (or equivalent verification
  procedure); stored on the VerificationEvent row. When empty,
  field is NULL (operators using legacy paths don't break).
- Audit-access: new helper `security.record_audit_access(table, filter)`
  called by every route that SELECTs from the audit tables. Helper
  is *fail-open* (logging failure does not block the actual query —
  the audit-access log corrupts gracefully rather than blocking
  operator access to legitimate audit data).

**Strengths:**
- Both vocation-direct
- Schema-change isolated to migrations (no 01_schema.sql edit;
  preserves v8.20 migration-as-only-DDL-evolution-path)
- Audit-access log is itself append-only (no infinite regress: reads
  of AuditAccessLog are NOT logged; the regress stops there
  explicitly — this is the Anti-Architect's required boundary)

**Weaknesses:**
- Two schema migrations in one composite — touches the migration
  framework's invariants for the first time with multiple migrations
  per ship
- The audit-access log itself becomes a target (insider could query
  it; that read is *not* logged by design)
- VerificationEvent.requesting_purpose_text adds nullable field for
  now; future ship may need to NOT NULL it

### Position B — Ship only item 3 (verification-purpose); defer item 6

Item 3 alone. Item 6 (audit-access audit) deferred until a real
incident motivates it.

**Strengths:**
- Smaller scope; one migration
- Lower constitutional weight

**Weaknesses:**
- Item 6 is vocation-direct; deferring is choosing not to advance
  the vocation when the work is ready
- The "wait for an incident to motivate" pattern is exactly the
  AP1 trap (self-observation-without-ground-touch in reverse: wait
  for ground-touch before instrumenting observation, which means
  observation never lands)

### Position C — Defer both; reopen later

Architectural conservatism. Both items wait for stronger demand.

**Strengths:** Zero work.

**Weaknesses:** Both items are ready; both are vocation-direct;
deferring both means the v9.19 architecture-study work was
half-realized.

## III. Architect's recommendation + Anti-Architect's contest

**Architect recommends Position A.** Both items are vocation-direct.
Both schemas are clean. Both have clear boundaries (verification-
purpose is nullable + append-only; audit-access regress stops at
itself).

**Anti-Architect's contest:**

- **On Item 3 (verification-purpose):** ENDORSED. The nullable column
  + append-only trigger combination is the right shape. The
  Anti-Architect's only caution: the field is operator-supplied
  free-text; future ships should NOT add LLM-based "purpose
  classification" or "purpose validation" — that's the AI-classifying-
  intent pattern that creates a new attack surface on the field's
  meaning.

- **On Item 6 (audit-access audit):** ENDORSED with the regress
  boundary made explicit. The Sanctum must record that
  AuditAccessLog reads are NOT logged (the regress stops there).
  Architect's draft already includes this. Anti-Architect accepts.

- **On the composite shape:** the two-migrations-in-one-ship pattern
  is new. The Anti-Architect endorses *for this ship* because both
  migrations are vocation-direct + independently load-bearing. For
  future ships, this pattern should not be treated as a template
  (AP7 risk: "the v9.20 ship had two migrations, therefore future
  ships can too" is a slippery generalization).

**Joint convergence on Position A** with the explicit boundary that
AuditAccessLog reads are not themselves logged.

## IV. Open questions for VANTA

1. **Position?** A (ship both) / B (item 3 only) / C (defer both)
2. **If A:** confirm the AuditAccessLog regress boundary (reads of
   AuditAccessLog are NOT logged; the regress stops there). Architect
   recommends; Anti-Architect requires.
3. **If A:** confirm operator-supplied free-text purpose field
   (no LLM classification; no validation beyond max-length). Architect
   recommends; Anti-Architect requires.

## V. Decision

**Position A (ship both items as v9.20 composite).** VANTA in-chat
2026-05-15: *"proceed with the joint recommendation"* — authorizing
both items per the joint recommendation, including the boundary
that AuditAccessLog reads are not themselves logged.

Three §IV resolutions per joint-recommended defaults:
- §IV.1 — Position A
- §IV.2 — AuditAccessLog regress boundary explicit (reads of the
  table are not logged); structurally enforced by *not adding* a
  `record_audit_access` call to the route that reads AuditAccessLog
  itself (if such a route exists in the future, it must NOT call
  the audit-access logger; tested as a structural invariant)
- §IV.3 — operator-supplied free-text purpose; no LLM classification
  or validation beyond length CHECK (280 chars max)

## VI. Outcome

Shipped as v9.20 same surface as decision.

**Records:**
- This file (`sanctum/2026-05-15-verification-purpose-and-audit-access.md`;
  DECIDED + CLOSED)
- New migration: `polaris_sql/migrations/2026-05-15-002-verification-purpose.up.sql`
  (+ .down.sql)
- New migration: `polaris_sql/migrations/2026-05-15-003-audit-access-log.up.sql`
  (+ .down.sql)
- Updated `polaris_web/security.py` — `record_audit_access()` helper
- Updated `polaris_web/app.py` — verification-purpose form field +
  audit-access logging on read routes
- `meta/sanctum-index.md` entry added
- v9.20 CHANGELOG entry references this Sanctum
- TestWave20V920 structural invariants pin both schemas + boundaries

**Pattern #20 Constitutional Discipline 17th instance** — joint
Architect + Anti-Architect recommendation closed by ship. The
Anti-Architect's required boundaries (AuditAccessLog regress stops at
itself; no LLM purpose classification) are structurally pinned by
TestWave20V920, not advisory.

## VII. Cross-references

- v9.11 vocation Sanctum (`sanctum/2026-05-15-vocation-anti-coercion.md`)
  — the anti-coercion principle these items directly advance
- v9.19 CHANGELOG entry — the architecture-study ship that surfaced
  these items as Sanctum-class
- v8.84 / v8.87 archive-purge Sanctum — the prior precedent for
  audit-table schema changes via migration + per-table append-only
  triggers; this ship mirrors that pattern exactly
- v8.20 audit-of-record principle (`DEVNOTES/audit-of-record.md`) —
  the constitutional contract both migrations preserve + extend
