# DEVNOTES/ships/redaction-proof.md

**Introduced:** v8.x (R11-7 / M2-12 in v2 done-list — "Verification-graph
redaction proof"). Schema trigger + property-test pair documented for
the first time 2026-05-17 (joint Architect / Anti-Architect review;
foresight surfaced as a documentation gap).

This file is the canonical write-up for Polaris's redaction-proof
primitive: what redaction means at the schema layer, how the property
tests prove non-reconstructability, and why the proof has to live in
the schema rather than the application.

---

## What "redaction-proof" claims

Per MISSION.md §Vocation, Polaris must support **verification-graph
redaction**: a holder can request that a specific verification event be
removed from the visible graph without leaving a reconstructable hole.
The schema-level claim is:

> Given any subset S of `VerificationEvent` rows marked redacted, the
> remaining rows expose neither (a) the count of redacted rows, nor (b)
> the timing pattern of redacted rows, nor (c) any FK shadow pointing
> at the redacted IDs.

The proof is structural — the schema's redaction path doesn't `DELETE`
rows (audit-of-record forbids); it `UPDATE`s them to a redacted form
where all PII-carrying columns are nulled and replaced with a uniform
sentinel. The redacted-row count IS observable by row-counting; the
*content* is not.

## Architecture

| Surface | Role |
|---|---|
| `polaris_sql/06_triggers.sql::tg_redact_verification_event` | The redaction operation itself — UPDATE that nulls PII columns and sets `redaction_marker` |
| `polaris_sql/01_schema.sql::VerificationEvent` | Carries the `redaction_marker` column + the partial unique index that lets a redacted row stay in the audit log |
| `polaris_sql/05_procedures.sql::uc_redact_verification` | The operator-side procedure (requires admin role + reason field) |
| `polaris_web/test_redaction_property.py` | Hypothesis property tests that prove non-reconstructability |

## The property tests

`test_redaction_property.py` is a dedicated test module because the
claims being tested are property-based, not example-based. The
strategy:

1. **Setup**: Hypothesis generates a random sequence of
   `VerificationEvent` inserts.
2. **Redact**: A random subset is redacted via the trigger path.
3. **Reconstruction attempt**: The test queries the remaining graph
   structure (FK shadows, audit-log timestamps, index entries) and
   asserts that NO query can distinguish the redacted-row content from
   the schema's uniform sentinel.

Specific claims under property test:
- Redacted-row PII columns are NULL OR equal to the sentinel value
- Redacted rows preserve `redaction_marker = TRUE` (observable that
  redaction occurred; the *what* is not observable)
- AuditLog reference to the verification cannot be joined back to PII
  (the PII column referenced in audit log is also redacted)
- FK to `IdentityToken` is preserved (the token still exists; only the
  verification's PII is redacted)

## Why the proof has to be schema-level

If redaction were application-level (e.g., a view that filters rows
based on a column), an SQL-direct-access path would bypass it. The
schema-trigger approach makes the redaction load-bearing at the
database engine, not at the application boundary.

Specifically:
- A DBA running `SELECT * FROM VerificationEvent` sees the redacted
  rows with their PII fields NULL/sentinel.
- A backup taken after redaction contains no PII for redacted rows.
- A WAL-shipping replica receives the redacted UPDATE; the pre-redaction
  state is not in the replica history beyond the WAL retention.

## What this primitive does NOT do

- It does NOT delete rows. The audit-of-record (C1) constraint forbids
  DELETE on `VerificationEvent`; redaction is UPDATE with PII nulling.
- It does NOT redact the holder's identity. The `Individual` table is a
  separate redaction surface (operator-issued); holder-initiated
  redaction only applies to verification *events*, not to the holder's
  existence.
- It does NOT cover backup retention. Per the operator's DR plan,
  backups older than the legal-retention floor are subject to deletion;
  redaction-after-backup is a separate operational procedure.
- It does NOT prove unlinkability between two redacted events. If the
  same holder has 100 verification events and redacts 50, the remaining
  50 still link to that holder's `IdentityToken`. Pattern-of-life
  privacy is a separate primitive (out of scope for redaction-proof).

## Maintenance posture

Stable. The trigger and property tests are byte-frozen-by-convention
unless the schema's PII surface changes. Future work classes:
1. **New PII columns** — any addition to `VerificationEvent` requires
   updating the trigger's null-list AND the property tests.
2. **Cross-table redaction** — currently scoped to VerificationEvent
   only. Extending to other event tables (DuressEvent,
   EnrollmentStatusEvent) would follow the same trigger pattern.
3. **Bulk redaction-with-audit** — currently single-row via
   `uc_redact_verification`; a bulk path would need careful audit-log
   handling to avoid leaking the redacted set's cardinality.

## Cross-references

- `MISSION.md` §Vocation (M2-12 in v2 done-list)
- `polaris_sql/06_triggers.sql::tg_redact_verification_event` — the
  trigger
- `polaris_web/test_redaction_property.py` — the property tests
- `DEVNOTES/threat-model.md` §I (Identity disclosure / reconstruction)
