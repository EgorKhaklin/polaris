# The principles

The thesis substrate of Polaris. Named in [`MISSION.md`](../../MISSION.md), preserved verbatim through every subsequent ship.

The principles are not the implementation. They are what the implementation must serve. A future maintainer may replace every script Polaris currently ships with, and the principles still hold.

Read this document before changing anything that touches `meta/`, `polaris_sql/`, or `MISSION.md`.

---

## I. The constitution: ten hard constraints, enforced at the schema level

> _Ten invariants (C1–C10) define what Polaris is. Each is enforced where it cannot be bypassed by policy: in the database, by trigger, partial unique index, or CHECK constraint._

**What it solves.** A policy is a promise. A schema constraint is a fact. Most identity systems state their guarantees in documentation and enforce them in application code, where a future feature, a hotfix, or an operator under pressure can quietly route around them. Polaris moves the guarantees down to the layer that cannot lie: the constraints hold for every code path that touches the database, including paths nobody has written yet.

The ten constraints are stated in [`MISSION.md`](../../MISSION.md). In summary:

| Constraint | What it holds | Enforced by |
|---|---|---|
| **C1** | Audit-of-record is append-only | Triggers reject UPDATE and DELETE |
| **C2** | Zero-knowledge: `ZERO_KNOWLEDGE` events carry no `token_id` | CHECK constraint + form-layer coercion |
| **C3** | One identity per person | Partial unique index |
| **C4** | Failed-login counter is atomic | Single-statement counter under lock |
| **C5** | CSP forbids inline scripts | `script-src 'self'`, no `'unsafe-inline'` |
| **C6** | Disclosure is enforced server-side | Server-side redaction, not client trust |
| **C7** | No hardcoded cryptography | Algorithm named in `CryptographicAlgorithm` |
| **C8** | `/api/atlas/*` result sets are bounded | LIMIT enforced in procedures |
| **C9** | Concurrency is tested with real threading | Threaded test suite |
| **C10** | Identity is not money | No `MonetaryClaim` table; architectural |

**How it's checked.** [`polaris_checks/checks.py`](../../polaris_checks/checks.py) binds a machine-checkable `check_*` function to each constraint and gates CI (`python3 -m polaris_checks.run`). The structural claim that the ten constraints form a complete, interdependent set is worked out in [`meta/constraint-lattice.md`](../../meta/constraint-lattice.md) and [`meta/structural-architecture.md`](../../meta/structural-architecture.md).

**Where to read more.**
- The constitution: [`MISSION.md`](../../MISSION.md)
- The check layer: [`polaris_checks/checks.py`](../../polaris_checks/checks.py)
- The constraint lattice: [`meta/constraint-lattice.md`](../../meta/constraint-lattice.md)

---

## II. Audit-of-record (C1)

> _The system writes evidence at the moment of decision. The evidence is append-only. Nothing is rewritten or back-dated._

**What it solves.** The temptation in any software system is to keep state mutable. Mutable state is convenient: you can fix mistakes by correcting the row, you can clean up old data by deleting it, you can refactor history by amending the commit. Convenience compounds into corruption: a system that retroactively rewrites its own claims has no defensible audit trail. Auditors, regulators, and future maintainers cannot trust state that may have been modified after the fact.

The audit-of-record principle says: for the consequential surfaces, write evidence at the moment of decision and never rewrite it. This is the substance of constraint C1.

**The nine instances.** Polaris carries nine audit-of-record surfaces, all schema tables.

| # | Instance | Append-only by |
|---|---|---|
| 1 | `TokenLifecycleEvent` | Trigger `trg_token_lifecycle_event_append_only` |
| 2 | `VerificationEvent` | Trigger `trg_verification_event_append_only` |
| 3 | `EnrollmentStatusEvent` (R11-4) | Trigger `trg_enrollment_event_append_only` |
| 4 | `AnchorBatch` (R10-2) | Trigger `trg_anchor_batch_append_only` |
| 5 | `AgencyTrustAttestation` (R11-3) | Trigger `trg_enforce_attestation_immutability` |
| 6 | `TokenStateEpoch` + `TokenStateEpochLeaf` (R10-1) | Trigger `trg_enforce_epoch_immutability` |
| 7 | `DuressEvent` (R11-5) | Trigger `trg_duress_event_append_only` |
| 8 | `RecoveryRequest` (R11-2) | Two-phase ceremony; rows transition only via UC-9 |
| 9 | `TokenSignature` (R11-1) | Trigger `trg_token_signature_immutability` (with active-signature invariant) |

**The no-CASCADE rule (v8.50).** Polaris schema files contain zero `ON DELETE CASCADE` or `ON UPDATE CASCADE` clauses. A cascade would silently destroy audit-of-record evidence; the principle forbids any mechanism that erases history without explicit operator action. The rule is enforced by `test_no_fk_cascade_in_polaris_sql`. There is no allowlist; future need for cascade would be a constitutional amendment.

**The advisory-lock catalog.** Six contention granularities now exist (per-token, per-individual-claim, per-algorithm, per-attesting-agency, per-procedure, plus the v8.50 additions). Each lock granularity exists because some audit-of-record surface required serialization at that scope to keep its evidence consistent. Documented in [`DEVNOTES/concurrency.md`](../../DEVNOTES/concurrency.md).

**Where to read more.**
- The principle and the instances: [`DEVNOTES/audit-of-record.md`](../../DEVNOTES/audit-of-record.md)
- The concurrency catalog: [`DEVNOTES/concurrency.md`](../../DEVNOTES/concurrency.md)
- The trigger source: [`polaris_sql/06_triggers.sql`](../../polaris_sql/06_triggers.sql)

---

## III. The Vocation: anti-coercion

> _No person should be compellable into surveillance through this system. This constraint sits above C1–C10; the ten constraints are its derivatives._

**What it solves.** An identity system is a point of leverage. Whoever controls it can, in principle, compel the people enrolled in it: demand disclosure, aggregate movements, retain records indefinitely, and make participation a precondition of ordinary life. The failure is not technical. A system can satisfy every cryptographic guarantee and still be an instrument of coercion if its design assumes a cooperative subject and an authority that always acts in good faith.

The Vocation, named in v9.11, states the deeper constraint: no person should be compellable into surveillance through this system. The zero-knowledge proofs (C2), the server-side disclosure enforcement (C6), the bounded result sets (C8), and the identity-is-not-money rule (C10) are not independent features. They are the concrete mechanisms by which the Vocation is made real.

**How it governs change.** Any proposed change is held against the Vocation. A feature that moves Polaris toward surveillance, centralized aggregation, or unbounded retention is refused on sight, regardless of how convenient or how technically sound it is. This is the one constraint that is not negotiated; it is the reason the rest of the constraints exist.

**Where to read more.**
- The Vocation: [`MISSION.md`](../../MISSION.md) §Vocation
- The threat model it answers: [`DEVNOTES/threat-model.md`](../../DEVNOTES/threat-model.md)

---

## On substitutability

The principles are stable. The implementations are not.

MISSION.md states the principles abstractly. A future maintainer may replace the scripts that enforce them (the check layer could be Python, Go, or any language; a constraint could be enforced by a different schema mechanism) without amending the principles. The amendment is reserved for changes to the principles themselves.

If a future maintainer of Polaris finds a better audit-of-record mechanism, a stronger schema-level enforcement, or a cleaner way to hold a constraint, they have permission to swap the implementation without changing the constitution.

---

## How to use this document

If you are priming on Polaris: read this once, then read [CLAUDE.md](../../CLAUDE.md).

If you are about to make a change: identify which constraint the change touches, and confirm the schema-level enforcement and the matching `check_*` still hold. If the change moves Polaris toward surveillance or aggregation, stop; it is held against the Vocation.

If you are a reviewer evaluating Polaris as an academic or professional artifact: the principles are the answer to "what makes this different from other identity-system reference implementations." The cryptographic substrate is the visible deliverable. The constitution and the Vocation are the operating model that produced it.

If you are an operator inheriting maintenance: read [MISSION.md](../../MISSION.md) for context, this document for the thesis, and [CLAUDE.md](../../CLAUDE.md) for the runbook.

The principles are the contract under which Polaris was built. They are also the contract under which it can be maintained without drift.
