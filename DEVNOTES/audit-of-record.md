# DEVNOTES/audit-of-record.md

**Introduced:** v8.20 (this file). The principle predates the file — it
governs the design of four schema elements that shipped between v6 and
v8.19. This document is the retroactive codification, written after
the v8.19 self-audit named the phrase as load-bearing vocabulary
without canonical definition.

---

## The principle

An **audit-of-record** is a schema element (table, document, or
event) whose own state — combined with append-only or strictly-bounded
mutation invariants on that state — fully reconstructs the history of
the operation it records, **without requiring a separate event-log
table**.

In other words: the artifact and its audit trail are the same object.
The row's immutability is the audit. There is no "X happened" event
that lives alongside the row; the row's existence and its
constrained-mutation rules together *are* the record that X happened.

## Why the principle exists

Polaris tracks several kinds of operations that need full
reconstruct-ability: token lifecycle transitions, signature
migrations, recovery ceremonies, strategic consultations. The naive
design for each is "primary table + event-log table" (e.g.,
`Recovery + RecoveryEvent`). This double-records state and creates
drift opportunities: the primary table can disagree with the event
log; one can be edited while the other is locked; one can be deleted
while the other persists.

The audit-of-record principle collapses the redundancy. If the
primary table is *itself* append-only-with-bounded-mutation, no
parallel event log is needed. The primary table IS the event log.

This is not a discovery. It's a design pattern. Polaris just happens
to apply it consistently enough that giving it a name is worth more
than leaving the term informal across several different files.

## Required properties

A schema element qualifies as an audit-of-record if and only if:

1. **Bounded mutation surface.** The set of allowed UPDATEs is
   enumerable and *narrow*. "No UPDATEs allowed" qualifies; "any
   UPDATE to any column" disqualifies. A single mutable field is
   the typical shape (e.g., `deprecation_date` on `TokenSignature`,
   or `decided_at` + `decided_by_user_id` on `RecoveryRequest`).

2. **DELETE forbidden.** Rows cannot be removed. The history must
   accumulate even when its content becomes stale or wrong.
   Corrections happen by *adding new rows*, not by mutating or
   deleting old ones.

3. **Trigger-enforced, not convention.** The append-only and bounded-
   mutation invariants are enforced by trigger or schema constraint,
   not by application code. A sufficiently-motivated insider with
   direct DB access must not be able to bypass the audit.

4. **One-way state transitions** for the mutable fields. If
   `deprecation_date` can be set NULL → timestamp, it cannot then
   transition back to NULL or earlier. State accumulates; it does
   not reverse.

5. **Reconstruction without external context.** Reading the table
   in isolation must answer: "What happened to entity X, in what
   order, recorded by whom, when?" If the answer requires joining
   to a separate event-log table, the element is not an
   audit-of-record.

## The current instances (9 schema tables)

Count corrected in v8.32 maintenance pass (8 → 10), then settled
at the nine schema tables below once the non-schema candidates were
reclassified as derived caches (they reconstruct from the schema and
source code, so they fail the AoR criterion "fully reconstructs
operation history without joining elsewhere").

The canonical nine are listed in the order the principle was applied.

| # | Element | Operation it records | Bounded mutation | DELETE rule |
|---|---|---|---|---|
| 1 | **`TokenLifecycleEvent`** | Token state transitions (RESERVE → ACTIVE → REVOKED etc.) | None, fully append-only | Forbidden by `reject_audit_modification` trigger |
| 2 | **`VerificationEvent`** | Verification outcomes per token × context | None, fully append-only | Forbidden by `reject_audit_modification` trigger |
| 3 | **`EnrollmentStatusEvent`** (R11-4) | Civic-enrollment status transitions (NOT_ENROLLED → ENROLLED → LAPSED → EXEMPT) | None, fully append-only | Forbidden by `trg_enrollment_event_append_only` trigger |
| 4 | **`RecoveryRequest`** | Catastrophic-loss recovery ceremonies (PENDING → APPROVED/REJECTED/EXPIRED) | `decided_at`, `decided_by_user_id`, `decision_reason`, `resulting_token_id`, `status` — only as part of `uc9_complete_recovery` | Not enforced by trigger; partial unique index `uq_one_pending_recovery_per_individual` prevents new PENDING during open one |
| 5 | **`TokenSignature`** | Algorithm migrations (signature added, optionally deprecated) | Only `deprecation_date`, one-way NULL → timestamp | Forbidden by `enforce_token_signature_immutability` trigger |
| 6 | **`AnchorBatch`** (v8.21 / R10-2 / M2-2) | Per-batch Merkle commitments of `BlockchainAnchor` leaves | None, fully append-only (operator-set `committed_to_chain` / `external_chain` are out-of-scope future-fields, NOT yet wired) | Forbidden by `reject_audit_modification` trigger |
| 7 | **`AgencyTrustAttestation`** (v8.22 / R11-3 / M2-8) | Federation trust graph (cross-agency mutual recognition per context) | `revocation_date` + `revocation_reason` pair — one-way NULL → timestamp + non-NULL reason ≥ 8 chars | Forbidden by `enforce_attestation_immutability` trigger |
| 8 | **`TokenStateEpoch`** (v8.23 / R10-1 / M2-1) | Per-epoch Merkle commitment of the active-token set (ZK-SNARK base) | None, fully append-only after closure | Forbidden by `enforce_epoch_immutability` trigger |
| 9 | **`DuressEvent`** (v8.24 / R11-5 / M2-10) | Detected compulsion signals (silent OOB alert for verifier under coercion) | `oob_notified_at` only — set once when a responder acknowledges (forward-only) | Forbidden by `reject_audit_modification` trigger |

### Conformance grading

**Eight of the nine instances are fully trigger-enforced**
(`TokenLifecycleEvent`, `VerificationEvent`, `EnrollmentStatusEvent`,
`TokenSignature`, `AnchorBatch`, `AgencyTrustAttestation`,
`TokenStateEpoch`, `DuressEvent`). The ninth (`RecoveryRequest`) has
partial enforcement via partial unique index + procedure discipline.
This asymmetry is honest, not aspirational:

- `RecoveryRequest` could be tightened with a dedicated trigger
  similar to `enforce_token_signature_immutability`, a future
  hardening pass. The procedure `uc9_complete_recovery` is the
  only sanctioned mutation path today, but raw UPDATEs are not
  refused at the schema level.

## What the principle is NOT

- **Not all-or-nothing.** Conformance is a spectrum. The instances
  above are in different positions on it; that's OK
  as long as the position is named honestly.
- **Not unique to Polaris.** ADR/RFC processes are also
  audit-of-record patterns. Block-chain transaction logs are an
  extreme version (mutation forbidden absolutely, not just bounded).
  The principle is being named here because Polaris applies it
  consistently; not claiming originality.
- **Not a substitute for application-level event sourcing.** If a
  use case genuinely needs *cross-entity* event reconstruction
  (e.g., "what was the full state of the system at 3pm on Tuesday?"),
  a separate event-sourcing layer might still be warranted. The
  audit-of-record collapses *per-entity* redundancy; it doesn't
  replace cross-cutting audit.
- **Not append-only in the strict sense for every instance.**
  Append-only means "no UPDATE, no DELETE." Audit-of-record allows
  *bounded* UPDATE — typically a single one-way field — because the
  bound is what makes the row a *living state record* rather than
  an immutable snapshot. The mutation surface must be narrow enough
  that the row's future state is fully predictable from its
  current state plus the allowed transitions.

## When to apply the principle

When designing a new schema element that records an operation, ask:

1. Is there a natural "primary entity" for this operation? (yes →
   maybe audit-of-record applies)
2. Does the operation have a small, enumerable set of state
   transitions? (yes → audit-of-record applies)
3. Would the parallel event-log table be largely a denormalization
   of the primary table's state-change history? (yes →
   audit-of-record is strictly cleaner)
4. Can append-only / bounded-mutation be enforced at the schema
   layer? (yes → ship it as audit-of-record)

If the answers are "no" to #2 or #4, consider a separate event-log
table instead. The principle is not a hammer.

## No FK CASCADE — ever (v8.50)

A corollary of the principle, codified after the v8.45 schema-scan
agent surfaced it as an implicit-but-unnamed rule:

**No foreign-key relationship in any Polaris schema file uses
`ON DELETE CASCADE` or `ON UPDATE CASCADE`.** Every FK either omits
the action clause entirely (defaulting to `NO ACTION` in PostgreSQL)
or explicitly says `NO ACTION` / `RESTRICT`.

### Why

CASCADE on a parent row's delete would silently propagate the
delete to dependent rows in audit-of-record tables. That violates
the principle's *appendOnly* property at the same row level:
`TokenLifecycleEvent` rows for a deleted token would vanish along
with the token, leaving no trace the lifecycle existed.

The default `NO ACTION` semantic is exactly the right answer:
the parent DELETE fails if any dependent row exists. The operator
must either (a) explicitly transition the dependent state (e.g.,
revoke the token, recording the revocation event) before the
parent can be deleted, or (b) accept that the parent is
effectively undeletable. Both paths preserve the audit trail.

For non-AoR tables (e.g., `Individual`, `Agency`, `CryptographicAlgorithm`,
`VerificationContext`), the same rule applies for consistency:
referenced principals are effectively undeletable once their
identifiers appear in any audit row. That's *correct* — deleting
the issuing agency of a verification event would erase
information needed to interpret the event later.

### How the rule is enforced

- **Convention** at code-review time. Every `FOREIGN KEY` clause
  in `polaris_sql/*.sql` is reviewed for absence of CASCADE.
- **Structural-invariant check** at CI time (added v8.50): scans
  every `.sql` file under `polaris_sql/` for the substrings
  `ON DELETE CASCADE` and `ON UPDATE CASCADE`. Fails if any match.
  See `check_no_fk_cascade` in `polaris_checks/checks.py`.
- **No allowlist mechanism.** If a future schema genuinely needs
  CASCADE semantics (very unlikely, since Polaris's identity model
  rejects it constitutionally), the right path is an amendment to
  this principle, not a per-file bypass.

### What the rule is NOT

- Not a ban on application-level cascading. The `uc8_revoke_token`
  procedure can record a revocation event AND mark dependent rows
  REVOKED in one transaction; that's an explicit, audited
  cascade in code, not a silent FK cascade.
- Not a ban on `ON DELETE SET NULL`. The rule names CASCADE
  specifically because SET NULL also destroys evidence
  (information about WHICH parent the dependent referenced is
  lost). But the structural test guards CASCADE only, leaving
  SET NULL as a convention-level concern. Add it to the check if a
  future ship needs to lock it down.

## Cross-references

- `polaris_sql/01_schema.sql` — TokenLifecycleEvent, RecoveryRequest,
  TokenSignature definitions.
- `polaris_sql/06_triggers.sql` — `reject_audit_modification`,
  `enforce_token_signature_immutability`, the trigger enforcement
  layer.
- `polaris_checks/checks.py` — `check_no_fk_cascade`, the
  machine-checked enforcement of the no-CASCADE corollary.
- `DEVNOTES/concurrency.md` — adjacent principle: per-entity
  advisory locks are the concurrency complement to audit-of-record.
- v8.19 self-audit — the audit that named this principle as
  load-bearing-but-undefined vocabulary.
