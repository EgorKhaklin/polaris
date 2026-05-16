# The four principles

The constitutional substrate of Polaris. Named in [`MISSION.md`](../../MISSION.md), elevated in v8.30, preserved verbatim through every subsequent ship.

The principles are not the implementation. They are what the implementation must serve. A future agent may replace every script, watcher, persona, and pattern Polaris currently ships with, and the principles still hold.

Read this document before changing anything that touches `meta/`, `MISSION.md`, or the cognitive substrate.

---

## I. The Sanctum protocol

> _Every non-routine decision produces a structured record. The record is written at the moment of decision, not reconstructed afterward._

**What it solves.** Software systems decay because the reasoning behind their decisions is lost. A year after a controversial design call, the team remembers _what_ they decided but no longer _why_; the alternatives are gone; the constraints that ruled them out are gone; the second-best option is unknown. The next maintainer either re-litigates the decision (wasting time) or accepts it without understanding it (accepting drift).

The Sanctum protocol forces the decision graph to be a real graph, on disk, in audit-of-record form.

**When it triggers.** MEDIUM-risk and HIGH-risk decisions. Cross-arc moves. Any structural change to the cognitive layer itself. The trigger is documented at [`meta/sanctum-protocol.md`](../../meta/sanctum-protocol.md) §II.

LOW-risk work (autonomous bug fixes, documentation drift, dependency bumps within named constraints) does not produce a Sanctum.

**What a session contains.** Seven sections, enforced by structural-invariant test:

| Section | Purpose |
|---|---|
| I. Premise | What is being decided and why now. |
| II. Architect's recommendation | The synthesis voice (`meta/architect.md`) names the recommended path and scores it. |
| III. Alternatives | The options not chosen, each with a defender's claim and an attacker's response. |
| IV. Constraints / clauses | The non-negotiable boundaries; e.g., "the agent does NOT execute `git push`." |
| V. Suggestions | Refinements to the recommendation. |
| VI. Operator decision | VANTA's verbatim reply. |
| VII. Outcome | What was actually built, with refinement counts and cross-references. |

**How it's enforced.** `scripts/ai-sanctum.sh` orchestrates the session. `scripts/ai-meta.sh check_sanctum` (CM check #6, added v8.20) catches drift between the directory and the index. Two structural-invariant tests pin the seven-section shape and the indexed count.

**Where to read more.**
- The protocol: [`meta/sanctum-protocol.md`](../../meta/sanctum-protocol.md)
- The index: [`meta/sanctum-index.md`](../../meta/sanctum-index.md)
- The 17 closed sessions: [`sanctum/`](../../sanctum/)
- The story of how it emerged: [`docs/story/STORY.md`](../story/STORY.md) §III

---

## II. Audit-of-record

> _The system writes evidence at the moment of decision. The evidence is append-only. Nothing is rewritten or back-dated._

**What it solves.** The temptation in any software system is to keep state mutable. Mutable state is convenient: you can fix mistakes by correcting the row, you can clean up old data by deleting it, you can refactor history by amending the commit. Convenience compounds into corruption: a system that retroactively rewrites its own claims has no defensible audit trail. Auditors, regulators, and future maintainers cannot trust state that may have been modified after the fact.

The audit-of-record principle says: for the consequential surfaces, write evidence at the moment of decision and never rewrite it.

**The ten instances.** Polaris carries ten audit-of-record surfaces. Nine schema tables and one filesystem directory.

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
| 10 | The `sanctum/` directory | Filesystem convention; checked by `ai-meta.sh check_sanctum` |

**The no-CASCADE rule (v8.50).** Polaris schema files contain zero `ON DELETE CASCADE` or `ON UPDATE CASCADE` clauses. A cascade would silently destroy audit-of-record evidence; the principle forbids any mechanism that erases history without explicit operator action. The rule is enforced by `test_no_fk_cascade_in_polaris_sql`. There is no allowlist; future need for cascade would be a Sanctum-class amendment.

**The advisory-lock catalog.** Six contention granularities now exist (per-token, per-individual-claim, per-algorithm, per-attesting-agency, per-procedure, plus the v8.50 additions). Each lock granularity exists because some audit-of-record surface required serialization at that scope to keep its evidence consistent. Documented in [`DEVNOTES/concurrency.md`](../../DEVNOTES/concurrency.md).

**Where to read more.**
- The principle and the ten instances: [`DEVNOTES/audit-of-record.md`](../../DEVNOTES/audit-of-record.md)
- The concurrency catalog: [`DEVNOTES/concurrency.md`](../../DEVNOTES/concurrency.md)
- The trigger source: [`polaris_sql/06_triggers.sql`](../../polaris_sql/06_triggers.sql)

---

## III. Risk classes

> _Three tiers govern what an agent may do autonomously and what requires explicit human approval. The line is named, not implicit._

**What it solves.** An AI agent maintaining a codebase faces a continuous question: which moves should the agent make unilaterally, and which should the agent surface for operator approval first? The two failure modes are symmetric. Too autonomous: the agent ships changes the operator would have vetoed, and the relationship becomes adversarial. Too cautious: the agent stalls on trivial work, and the operator becomes the bottleneck. Neither is sustainable.

The risk classes resolve the ambiguity by naming the line explicitly.

**The three tiers.**

| Tier | What it covers | Posture |
|---|---|---|
| **LOW** | Drift resolution; documentation gaps; pre-existing soft signals from coherence checks; structural-invariant-suite expansion; pattern catalog warming. | Autonomous. The agent ships; the changelog records; the next session continues. |
| **MEDIUM** | New ROADMAP-item ship; opening or closing a v2 arc; structural change to the cognitive layer itself; license selection; first-publication readiness. | Enter the Sanctum. Architect surfaces options; operator decides; outcome recorded. |
| **HIGH** | Cross-arc strategic decisions; introducing or removing a constitutional principle; any change to MISSION.md sections C1–C10 or the cognitive-substrate clause; constitutional posture refresh. | Enter the Sanctum. Architect surfaces options with second-best-attack analysis; operator decides; reflection cycle follows. |

**The bug-fix carve-out (v8.31).** Correctness regressions reported by the operator do not respect tier boundaries. A user-reported bug that breaks a previously-working surface ships as a LOW-risk autonomous fix even if the surface is constitutionally weighted, because the alternative is leaving the regression in place. v8.51, v8.55, v8.56, and v8.58 all shipped under this carve-out.

**The decline-and-surface default (v8.31).** For ambiguous requests, the agent's default is to decline the request and surface the question: explain why the request crosses a tier boundary, name the trigger that would be needed to authorize it, wait for explicit operator authorization. The contract is operator-revocable: VANTA may name a trigger or open a new arc at any time. The constraint is on the agent.

**Where to read more.**
- The architecture: [`meta/autonomy-architecture.md`](../../meta/autonomy-architecture.md)
- The post-v2 declaration: [`sanctum/2026-05-12-post-v2-steady-state-declaration.md`](../../sanctum/2026-05-12-post-v2-steady-state-declaration.md)
- The CLAUDE.md operator-side mirror: [`CLAUDE.md`](../../CLAUDE.md) §"Post-v2 default posture"

---

## IV. CM — the meta-constraint

> _The cognitive layer guards itself. Six executable checks catch drift between the layer's claims and the running system._

**What it solves.** A system that audits its application code while leaving its own auditing infrastructure unaudited has a blind spot. The cognitive layer of Polaris (39 ai-* scripts, 22-pattern catalog, 4 meta docs, 9 watchers, 59 Sanctums, 882 structural invariants) is substantial enough to need its own self-monitoring. Without that, scripts get referenced in CLAUDE.md but stop existing on disk; patterns sit in the catalog never invoked; constraints are claimed in MISSION.md but never exercised; structural-invariant tests get retired without leaving a trace. The drift is observable, accumulates silently, and erodes trust in the layer faster than any single ship.

CM (the meta-constraint, named in MISSION.md alongside C1–C10) closes the blind spot.

**The six executable checks.** Each runs as a function in `scripts/ai-meta.sh`. The full suite runs on `ai-done` (pre-ship gate) and on every HYDRA sweep.

| Check | What it catches |
|---|---|
| 1. `check_scripts_exist` | Every script CLAUDE.md names is actually on disk. |
| 2. `check_pattern_warmth` | Every pattern in the 22-pattern catalog has been invoked at least once in the journal. |
| 3. `check_mission_rollup` | The v1 / v2 / Arc D done-list arithmetic in MISSION.md matches the ✓ / ✗ counts. |
| 4. `check_ai_help_completeness` | `ai-help.sh` knows about every `ai-*` script in `scripts/`. |
| 5. `check_soft_coherence` | The soft-signal output of `ai-coherence.sh` is acceptable. |
| 6. `check_sanctum` (v8.20) | The `sanctum/` directory and `meta/sanctum-index.md` agree. |

**The closure constraint.** Polaris currently has C1 through C10 as hard constraints plus CM as the one meta-constraint. Adding a constitutional principle (a hypothetical C11 or CM2) requires extending the 10-node lattice topology in `meta/constraint-lattice.md`, which forces explicit justification. The closure is the test: a future agent cannot quietly add a principle without restructuring the topology and surfacing the change.

**How CM stays honest.** The drift modes CM exists to catch are themselves audited. v8.45 launched a multi-agent scan that surfaced ~65 drift items spanning all six check domains. v8.57 closed 15 of them in a doc-only ship. The pattern (multi-agent scan as a force function for CM drift discovery) is named in the CHANGELOG and runs against the layer on demand.

**Where to read more.**
- The MISSION.md clause: [`MISSION.md`](../../MISSION.md) §CM
- The executable: [`scripts/ai-meta.sh`](../../scripts/ai-meta.sh)
- The lattice: [`meta/constraint-lattice.md`](../../meta/constraint-lattice.md)
- The structural philosophy: [`meta/structural-architecture.md`](../../meta/structural-architecture.md)

---

## On substitutability

The four principles are stable. The implementations are not.

As of v8.30, MISSION.md §"The cognitive substrate" explicitly marks the following as **substitutable**:

- The 39 `ai-*` shell scripts (could be Python, Go, or any language)
- The 22-pattern catalog (could be a different taxonomy, e.g., a 36-pattern decanate-style or a 12-pattern zodiac-style)
- The HYDRA swarm with 9 watchers (could be a single LLM call, a CRDT, a deterministic introspection function)
- The Architect persona (could be a different synthesis voice)
- The constraint lattice (could use a different mapping topology)
- The brain map (could be a different visualization paradigm)

v8.43 added the explicit clause: _"A future agent may replace the HYDRA swarm with a different synthesis pattern without amending this section, provided the four principles still hold."_

The substitutability principle is itself not a fifth principle. It is a property of how the four principles are stated. Stating the principles abstractly (rather than naming their current implementations as constitutional) is what makes them survive implementation changes.

If a future maintainer of Polaris finds a better synthesis pattern, a better risk-class boundary, a better audit-of-record mechanism, a better self-monitoring discipline — they have constitutional permission to swap the implementation without amending the constitution. The amendment is reserved for changes to the principles themselves.

---

## How to use this document

If you are an AI agent priming on Polaris: read this once, then read [CLAUDE.md](../../CLAUDE.md).

If you are a maintainer about to make a change: identify which principle the change touches, and follow the trigger for that tier. If you cannot identify the principle, the change is probably LOW-risk and ships autonomously.

If you are a reviewer evaluating Polaris as an academic or professional artifact: the principles are the answer to "what makes this different from other identity-system reference implementations." The cryptographic substrate is the visible deliverable. The principles are the operating model that produced it.

If you are an operator inheriting maintenance: read [STORY.md](../story/STORY.md) for context, this document for the contract, and [CLAUDE.md](../../CLAUDE.md) for the runbook.

The principles are the contract under which Polaris was built. They are also the contract under which it can be maintained without drift.
