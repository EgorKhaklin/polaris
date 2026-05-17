# MISSION.md — what Polaris is, and what it isn't

This is the constitution. Every architectural decision, every feature
addition, every refactor must be checkable against this document.
When something here conflicts with a request, the request is wrong —
or the mission needs explicit, deliberate amendment.

`scripts/ai-status.sh` reads this file to score current state against
mission. `scripts/ai-propose.sh` reads it to score backlog items.
`scripts/ai-mission.sh` prints it back so the agent re-grounds at the
start of every session.

---

## Freeze line — definition of done (v9.27, amended once v9.29)

**Per BIG MISSION Tier 8 #12 Sanctum (`sanctum/2026-05-16-tier-7-8-thesis-test-and-freeze-line.md`):**

**AMENDMENT LOG (per `meta/freeze-amendment-protocol.md`):**

| Date         | Old → New          | Cost                | Sanctum |
|--------------|--------------------| ------------------- |---------|
| 2026-05-16   | v9.30 → v9.31      | one ship slip       | [v9.29](sanctum/2026-05-16-v9-29-constitution-sanctum-cm.md) |

The amendment is logged once, with stated cost. No further amendments
are pre-authorized. The next amendment requires another Sanctum + the
operator routing through the external referent.

---

The core is **done at v9.31** when ALL of the following are true,
mechanically verifiable from outside the cognitive layer by `grep`
and one-line `bash` checks:

1. All 10 hard constraints (C1–C10) are enforced at the schema level
   (verifiable: `polaris_sql/01_schema.sql` + `06_triggers.sql` +
   `polaris_web/test_structural_invariants.py` ≥5 invariants per
   constraint).
2. The kill test (`scripts/polaris-swarm-killtest.sh`) catches 5/5
   defects in 1 pass at v9.31 (verifiable: exit code 0).
3. The chaos test (`scripts/polaris-chaos-test.sh`) reports 3/3
   fail-safe at v9.31 (verifiable: exit code 0).
4. The MTTR ledger (`meta/swarm-mttr.json`) has at least 3 resolved
   findings recorded between v9.25 and v9.31 (verifiable: count of
   entries with non-null `resolved_at_utc`).
5. The v9.30 binding clause has fired its check (`polaris-swarm-mttr.sh
   check-v9-30`) and either passed OR the cognitive-layer-deletion
   Sanctum has shipped. (Note: the v9.30 binding clause's NAME is
   unchanged; only the freeze-version target moved per the amendment
   above.)
6. The application observability surface (`polaris_web/observability.py`
   + `/api/metrics`) is wired into `app.py` + `security.py`.
7. `POLARIS_VERSION` is `9.31`.

**From v9.32 forward, all work is one of:**

- **(a) Hardening** — security fixes, dependency updates, bug fixes
  against the existing surface.
- **(b) Measurement** — extensions to the kill test, scorecard, chaos
  test, MTTR ledger, observability metrics.
- **(c) Thesis cold-read evidence** — an independent external party
  attempts the cold-read test (per `docs/THESIS.md`) and the result
  is documented.

**New arcs require a Sanctum that explicitly names an external
trigger** (operator-side event in the world, not agent-internal
observation). The triggers are NOT pre-catalogued; they are named
in real time by the operator when they occur.

**The abandonment clause:** if no cold-read attempt occurs by v9.40
(per `docs/THESIS.md` terminus), the thesis is documented as
inconclusive and the strong claim is retired permanently. The system
is kept as good tooling.

**This is the freeze line. It is mechanical, not aspirational. It is
externally verifiable. It includes the abandonment condition.**

The freeze line is the operational answer to "this stops being
infinite." If this section ever gets edited to soften a condition,
remove the abandonment clause, or add unproven thesis claims, the
constitutional contract is broken; future operators should treat
that edit as a fork.

---

## Vocation

**Polaris is the anti-coercion identity substrate. The deepest
constraint, deeper than C1-C10, is that no person be compellable into
renouncing, transferring, or surrendering their identity against their
will.**

This vocation was named in v9.11 by
[`sanctum/2026-05-15-vocation-anti-coercion.md`](sanctum/2026-05-15-vocation-anti-coercion.md).
It ratifies what the codebase already implements; it does not impose
a new requirement. Reading the seven load-bearing primitives forward,
the vocation has been operative since v8.24:

- TokenSignature backfill (v8.18 / R11-1) — every token sealed
- Multi-signature migration (R11-1) — no single-point compromise window
- WebAuthn-MFA (v8.97) — second factor not phishable remotely
- Federation trust graph (R11-3) — identity portable across attesting
  agencies; no monopoly
- Redaction-proof discipline (M2-12) — adversary-modeled
  non-derivability of redacted fields
- Audit-of-record (v8.20) — every state change recorded; no silent
  revision
- **Duress-code primitive (R11-5)** — the secret name that signals
  coercion without revealing the signal

C1-C10 below become *derivatives* of this vocation. Every future
feature is judged: does it advance anti-coercion, even by a margin?
If yes, it earns its place. If no, it is elaboration of structure
without service of purpose.

The Anti-Architect persona ([`meta/anti-architect.md`](meta/anti-architect.md))
references this section to detect AP5 (vocation drift) — proposals
not traceable to this vocation surface as dissents.

---

## Why Polaris exists

Polaris is a reference implementation of a national identity token
system — what a sovereign-grade identity layer would look like if you
designed it from first principles in 2026, knowing what we now know
about post-quantum cryptography, zero-knowledge proofs, append-only
audit, and the failure modes of every CBDC pilot.

It is built as VANTA's portfolio piece for SCS-230 (Database
Management Systems) at Seton Hill, but the engineering bar is
production-grade. The course is the occasion. The mission is bigger.

---

## What Polaris IS

1. **An identity attestation layer.** A token that proves "this person
   is who they say they are, in this context, at this moment." Nothing
   more.

2. **Post-quantum by default.** ML-DSA primary, SLH-DSA fallback. RSA
   and ECDSA exist in the schema for migration semantics; they should
   not be issued for new tokens.

3. **Append-only at the audit layer.** Every state transition writes a
   `TokenLifecycleEvent`; every verification writes a
   `VerificationEvent`. Both tables have triggers that REJECT
   `UPDATE` and `DELETE`. This is non-negotiable. The audit invariant
   (NFR-4) is the load-bearing security claim.

4. **Context-scoped.** A token used for HEALTHCARE verification cannot
   be replayed against BANKING verification. Each
   `VerificationContext` defines its own permitted disclosure
   semantics.

5. **Three disclosure levels with strict typing:**
   - `ZERO_KNOWLEDGE` — proves "valid token exists" without revealing
     identity. `token_id` MUST be NULL on these events. Enforced by
     trigger.
   - `SELECTIVE` — reveals named attributes only.
   - `FULL` — reveals identity. Logged for audit; rate-limited.

6. **Succession by reference, never overwrite.** When a token is
   replaced, the new token's `predecessor_token_id` points at the old.
   The old token stays in the database with its terminal status. Lost
   tokens are LOST forever; their data is not erased.

7. **One ACTIVE token per individual.** Enforced by the partial unique
   index `uq_one_active_per_person`. This is a database-level
   guarantee, not an application convention.

---

## What Polaris IS NOT

1. **Polaris is NOT money.** A `MonetaryClaim` table does not belong in
   this schema. Identity attestation and value transfer are separate
   concerns; conflating them turns an administrative paperwork error
   into an existential bank-balance error. If banking-on-Polaris is
   ever built, it lives in a separate repository that consumes
   verification proofs over an HTTP boundary. The boundary itself is
   load-bearing.

2. **Polaris is NOT an authority.** It does not decide who can vote,
   borrow, or cross a border. Those decisions are made by external
   systems that consume Polaris verification proofs. Polaris answers
   "is this token valid for this context?" — not "should this person
   be allowed to do X?"

3. **Polaris is NOT a surveillance backbone.** `ZERO_KNOWLEDGE`
   verifications produce no `token_id` and no holder reference. The
   verification graph cannot be reconstructed from `ZERO_KNOWLEDGE`
   events alone. This is intentional and architecturally enforced.

4. **Polaris is NOT a CBDC pilot.** It does not solve "programmable
   money." It solves identity, deliberately, in isolation, so that
   programmability gravity does not accrete politically-contested
   constraints into the identity layer.

5. **Polaris is NOT a key escrow system.** Private signing keys are
   not held by the issuer post-issuance. Revocation works via the
   `RevocationList`, not by reissuing the token under a new key.

6. **Polaris is NOT a workaround.** Every architectural decision
   should be defensible from first principles. If a feature exists
   only because "the v1 author did it that way," it is wrong and
   should be rewritten or removed.

---

## The hard constraints (do not violate)

These are the lines that, if crossed, mean Polaris has been
fundamentally broken regardless of what tests still pass.

| # | Constraint | Where enforced |
|---|------------|----------------|
| C1 | `VerificationEvent` and `TokenLifecycleEvent` are append-only — UPDATE and DELETE are rejected by trigger | `06_triggers.sql::reject_update_delete()` |
| C2 | `ZERO_KNOWLEDGE` events have `token_id IS NULL` | `01_schema.sql::disclosure_consistency` CHECK constraint + form-layer coercion |
| C3 | At most one `ACTIVE` token per `Individual` | `01_schema.sql::uq_one_active_per_person` partial unique index |
| C4 | Failed login increments are atomic (no TOCTOU) | `security.py::authenticate()` uses `UPDATE … SET col = col + 1 RETURNING …` |
| C5 | CSP is `script-src 'self'` — no `'unsafe-inline'` for production scripts | `security.py::secure_headers()` |
| C6 | Disclosure level is enforced server-side; client cannot upgrade | `verifications_new` route + `enforce_zk_typing` trigger |
| C7 | Cryptographic algorithm metadata flows through `CryptographicAlgorithm` — never hardcoded in app code | `01_schema.sql::CryptographicAlgorithm` table |
| C8 | All `/api/atlas/*` endpoints have hard caps preventing unbounded result sets | `app.py::_ATLAS_MAX_*` constants |
| C9 | Tests for concurrency hazards use real threading, not mocks | `test_app.py::ConcurrencyTests` |
| C10 | Identity attestation never carries spending authority | architectural — no `MonetaryClaim` table |

When `ai-status.sh` runs, it greps each of these into existence and
flags anything missing.

---



### Constraint lattice (v8.8)

The 10 hard constraints map onto a fixed 10-node lattice — three
pillars (expand / contract / balance) by four tiers — encoding the
structural claim that the constraint set is COMPLETE and
INTERDEPENDENT. Removing any constraint cascades through the others.
See `meta/constraint-lattice.md` for the per-constraint mapping and
the dependency walk.

| Lattice position | Constraint | Pillar |
|---|---|---|
| APEX | C10 identity ≠ money | center top |
| EXPAND·1 | C7 algorithm metadata | right (expansive) |
| CONTRACT·1 | C2 ZK→token NULL | left (contractive) |
| EXPAND·2 | C5 CSP 'self' | right |
| CONTRACT·2 | C4 atomic increment | left |
| BALANCE·2 | C3 one ACTIVE per individual | center |
| EXPAND·3 | C8 atlas hard caps | right (lower) |
| CONTRACT·3 | C6 server-side disclosure | left (lower) |
| BALANCE·3 | C1 append-only audit | center |
| MANIFEST | C9 real-threading tests | bottom |

Adding C11 requires extending the topology (or replacing one of
C1-C10). The previously-reserved meta-slot is now filled by **CM**,
a meta-constraint at a different abstraction level (see below).

Walk the lattice from any node with `scripts/ai-lattice.sh <Cn>` —
surfaces tier neighbors, polarity complement, and dependency
cascade. The etymology of the structural insight (which older
frameworks it's drawn from) is in `meta/lineage.md`.

### CM — the meta-constraint (v8.9)

| # | Constraint | Where enforced |
|---|------------|----------------|
| CM | The cognitive layer self-monitors via executable checks | `scripts/ai-meta.sh` + `polaris_web/test_structural_invariants.py` |

CM is at a different abstraction level from C1-C10. C1-C10 are
claims about Polaris's data and security properties. CM is a claim
about the cognitive layer that monitors C1-C10. Mixing them would
conflate "the data is consistent" with "the cognitive layer that
checks consistency is consistent."

CM is enforced by `scripts/ai-meta.sh`, which runs six executable
checks:

1. Every ai-* script in CLAUDE.md exists on disk and is documented
2. The 22-pattern catalog has at least one warm pattern (actually used)
3. Each C1-C10 has been touched in code in the last 30 days (no
   constraint is dead)
4. ai-help.sh and ai-done.sh references match disk
5. The meta-slot is filled (CM is named in both lattice and MISSION)
6. **Sanctum integrity** (added v8.20): no stale-OPEN sessions
   (>7 days), no lifecycle violations (CLOSED without §VII Outcome;
   REJECTED without §VI Decision), no index drift between
   `sanctum/` and `meta/sanctum-index.md`. This is CM's first scope
   extension since CM was defined in v8.9; it brings the
   cognitive-layer audit-of-record (the Sanctum) under the same
   self-monitoring discipline that already covers C1-C10.

If any check fails, the cognitive layer has drifted from its own
claims. This is the failure mode CM exists to prevent.

**The immortal 10th head.** The cognitive substrate's swarm
metaphor (HYDRA + Mycelium) gives CM a mythological reading: the
nine HYDRA watchers (post-v8.72 mythology relocation; see
`meta/arc-d-hydra.md` + the v8.72 Sanctum) are the nine cuttable
mortal heads of the Lernaean Hydra. The **immortal 10th head** —
the one Heracles could not sever — is **CM**. CM is the head that
does not regrow because it does not get cut: removing it would
remove the self-monitoring discipline that lets every other
constraint be verified. The substitutability clause (v8.30) that
applies to every other cognitive-layer element does **not** apply
to CM. The mythology gives a name to the structural truth v8.9
established when CM was first introduced.

CM is one of four principles named in **"The cognitive substrate
(the agent contract)"** further below in this document (added v8.30).
The other three — the Sanctum protocol, audit-of-record, and risk
classes — together constitute the agent contract that CM monitors.
Before v8.30, CM was the constitution's only acknowledgement of the
cognitive layer; the §"cognitive substrate" section now names the
broader contract whose preservation CM enforces.

## The architectural soul (the "why" beneath the "what")

Why these constraints exist, in three sentences each.

### Append-only audit (C1)

A national identity system cannot retroactively rewrite history. The
audit trail is the load-bearing claim that tokens were issued under
the procedures the public was told they would be issued under. UPDATE
and DELETE are rejected by trigger because making them application
errors is not enough — a sufficiently-motivated insider with database
access could bypass an application-layer check.

### ZK token-id NULL invariant (C2)

The point of `ZERO_KNOWLEDGE` is plausible deniability. If
verification events recorded the token-id even for ZK verifications,
the verification graph could be reconstructed by anyone with read
access — defeating the privacy claim. The NULL invariant is enforced
at the trigger layer because a verification event with both
disclosure='ZERO_KNOWLEDGE' and a non-null token_id is not just an
application bug; it's a privacy violation that should never be
storable.

### One ACTIVE per individual (C3)

Two simultaneously-active tokens for the same person opens a class of
attacks where one token is used to authorize a transaction, the other
to repudiate it ("that wasn't me, that was the other token"). The
partial unique index resolves this in the deepest layer of the system,
not as an application convention. Two operators activating two reserve
tokens for the same holder simultaneously will find that exactly one
of them gets a `UniqueViolation`.

### Identity ≠ money (C10)

The single most consequential architectural decision. CBDCs that
conflate identity and money inherit programmability gravity:
constraints accrete onto the identity token politically, until one
day the system can be told "this person cannot buy gasoline." Polaris
deliberately separates the layers. If a value system is built on top,
it lives in a separate database with FK references that PROVE the
separation, not just claim it.

---

## The cognitive substrate (the agent contract)

Polaris is built and maintained by an agent operating under a
contract. This section names that contract.

The contract has **principles**, not implementations. The principles
are load-bearing — removing any cascades through the others. The
*current* implementation lives in `scripts/`, `meta/`, `DEVNOTES/`,
`patterns/`, `sanctum/`, and `journal/`. The implementation is
substitutable. A future agent may use a different cognitive substrate
so long as it preserves all four principles.

### Principle 1 — The Sanctum protocol

MEDIUM-risk and HIGH-risk decisions are recorded as audit-of-record
sessions in `sanctum/`. The session is a structured agent-operator
strategic consultation: §I the Matter, §II Preparation, §III
Alternatives, §IV Recommendation, §V Ask, §VI Decision (verbatim
from VANTA), §VII Outcome (filled by agent after execution). Routine
LOW-risk work does NOT produce a Sanctum. The full protocol is in
`meta/sanctum-protocol.md`; sessions are indexed at
`meta/sanctum-index.md`.

A Sanctum exists for the same reason `TokenLifecycleEvent` exists:
when a state-changing decision happens, the audit-of-record principle
demands a row. Strategic decisions are state-changing.

### Principle 2 — Audit-of-record

Every primitive that changes state has a schema element + invariants
that fully reconstruct operation history without a separate event-log
table. Append-only at the data-content level, with bounded mutation
(e.g., revocation as a state transition, not a delete). Currently
**nine schema instances + three filesystem instances**: schema —
`TokenLifecycleEvent`, `VerificationEvent`, `RecoveryRequest`,
`EnrollmentStatusEvent`, `TokenSignature`, `AnchorBatch`,
`AgencyTrustAttestation`, `TokenStateEpoch`, `DuressEvent` —
collectively the v2 mission substrate; filesystem — `sanctum/*.md`
sessions, `polaris_swarm/civitas/census-roll.json` (Arc E civitas
registry; v8.66), and `polaris_swarm/civitas/treasury-roll.json`
(Arc F denarii ledger; v8.68) (convention-enforced via `ai-meta.sh`
CM check #6). The principle is canonicalized in
`DEVNOTES/audit-of-record.md`. New schema-touching ships extend the
catalog; the principle is what gates them.

### Principle 3 — Risk classes

Three risk classes gate agent autonomy:

- **LOW** — autonomous-eligible. The agent ships without
  propose-and-wait.
- **MEDIUM** — propose-and-wait. The agent drafts a proposal or
  brief and presents it; VANTA approves before execution.
- **HIGH** — explicit human approval required. No execution without
  VANTA naming the item.

Specified in `meta/autonomy-architecture.md`. Risk class is the
default sort order in `ai-propose`; it is what makes
MEDIUM/HIGH-risk Sanctum-triggering rather than execution-triggering.

### Principle 4 — CM (the meta-constraint)

The cognitive layer self-monitors via executable checks. Where
C1–C10 are claims about Polaris's data and security properties, CM
is a claim about the cognitive layer that monitors C1–C10. CM is
defined in `## The hard constraints` above; it is enforced by
`scripts/ai-meta.sh` (six checks) and
`polaris_web/test_structural_invariants.py`.

The four principles are nested: the Sanctum protocol relies on
audit-of-record, audit-of-record relies on risk-class gating to
decide when a Sanctum is needed, and CM monitors the whole stack.
Removing any of the four cascades through the others — the same
Removable Test applied to C1–C10 in `meta/structural-architecture.md`.

### What this section is NOT

This section names principles, not implementations. The following
are **current implementation**, not constitutional:

- The 39 ai-* scripts in `scripts/` (the executable cognitive layer; v8.37 added ai-hydra, v8.52 added ai-brain-map)
- The 22-pattern catalog in `scripts/ai-pattern.sh`
- The Architect persona in `meta/architect.md` + `scripts/ai-architect.sh`
- The constraint lattice in `meta/constraint-lattice.md`
- The doc structure under `DEVNOTES/` / `patterns/` / `meta/`
- **The HYDRA swarm in `polaris_hydra/`** and its nine watchers
  — the canonical Hydra heads. Originally 7 (schema, cognitive,
  security, mission, adversary, performance, trajectory); expanded
  to 9 in v8.72 with the addition of `ant_colony` (observes the
  Mycelium swarm runtime) and `civitas` (observes the citizen-
  layer runtime). HYDRA aggregates watcher reports and is the
  only LLM caller in the cognitive layer; watchers themselves are
  read-only and deterministic. Authorized by
  `sanctum/2026-05-12-new-chapter-swarm-hydra-arc-opening.md`
  (Arc D opening), named here by
  `sanctum/2026-05-12-hydra-constitutional-integration.md`,
  extended to 7 watchers by
  `sanctum/2026-05-13-trajectory-watcher-7th-channel.md`, and
  expanded to 9 — the canonical Hydra-9 count — by
  `sanctum/2026-05-13-hydra-mythology-relocation-to-watchers.md`
  (relocating the Hydra-9 mythology from Mycelium legions to its
  etymological home).

Any of these may be substituted, renamed, restructured, or replaced
without violating the constitution — as long as the four principles
above remain preserved and the CM check still passes. **A future
agent may replace the HYDRA swarm with a different synthesis pattern
without amending this section, provided the four principles still
hold.** This is structurally analogous to how C10 names the property
("identity ≠ money") without naming the mechanism (the absence of a
`MonetaryClaim` table is the *current* mechanism; a different
mechanism preserving the property would still satisfy C10).

### Why this section exists

Before v8.30, the cognitive layer was load-bearing but unnamed in
the constitution. CM was the only constitutional reference. The
Architect surfaced this gap in every brief from v8.20 onward; the
v8.29 audit pass made the gap explicit. This section closes that
gap. The Sanctum that authorized it is
`sanctum/2026-05-12-cognitive-layer-constitutional-elevation.md`.

---

## What "done" looks like for Polaris

The done-list has two epochs. The v1 done-list (the SCS-230 deliverable
arc) closed on 2026-05-09 with 12 of 15 items shipped and 3 retired
(items 13–15, v8.27). The v2 done-list extended Polaris from "the
schema implements the design" to "the system stands behind the
design's claims" — the combination of substrate-level demonstrations
(PDF Appendices E and F as code) and the open problems the report
itself names as deferred (PDF §9). **v2 closed 2026-05-12 at 12/12 ✅
with the v8.28 UI graduation phase** (Option 3 close-out: dashboard
substrate tiles, `/anchors` / `/epochs` / `/federation` viewers, token
detail v2 state section). Both epochs are listed below: v1 as the
historical record, v2 as the closed mission. The arcs that were
considered and not chosen for v2 are documented in
`meta/missions-considered.md`.

### Post-v2 strategic moment

With both done-lists closed (v1 + v2 + Arcs D/E/F/G), Polaris
moved through two posture phases. The constitutional core
(C1-C10, the four cognitive-substrate principles, G-guards) is
preserved across both; only the agent's default response shape
to ambiguous requests changes.

**Phase 1 — Post-v2 steady-state (2026-05-12 → 2026-05-14):**
**Resolved 2026-05-12: steady-state** by
`sanctum/2026-05-12-post-v2-steady-state-declaration.md`.
Default posture: **decline-and-surface**. The agent shipped
LOW-risk maintenance only; the Architect surfaced drift, not
new scope. Arc B (prod-deploy) / Arc C (partner) / novel arc
were the only named triggers that would open new mission scope.

**Phase 2 — Heavy-production (2026-05-14 → present):**
**Active.** Revoked the steady-state contract via
`sanctum/2026-05-14-steady-state-revocation-heavy-production.md`
(HIGH-risk, DECIDED). The third v8.31 trigger condition
(*novel arc with documented external cause*) fired in-chat:
VANTA's directive *"polaris and the sub projects are currently
far from being complete… do the whole thing… boil the ocean."*
First manifestation: Arc B Phase 1 (production deployment)
shipped same day as v8.77. By v8.85 the day's ledger reads ten
ships across Arc B Phases 1, 1.5, 2 + ARCH-002/003/004
(docs, UX, test-depth) + an OPEN Sanctum for the constitutional
question on audit-log deletion-from-hot.

**Default posture under heavy-production: active-production.**
The agent ships the complete thing per the standing-
instructions block (`DEVNOTES/style.md`): *do the whole thing,
do it right, do it with tests, do it with documentation, ship
the complete thing, the marginal cost of completeness is near
zero with AI*. The Architect surfaces drift AND production-
readiness gaps. Constitutional questions still go through
Sanctum (Pattern #20 Constitutional Discipline, first instance
shipped v8.84) — heavy-production accelerates execution, it
does not skip the protocol.

**What does NOT change under heavy-production:**

- **C1-C10** preserved verbatim
- **The four cognitive-substrate principles** (Sanctum, AoR,
  risk classes, CM) preserved verbatim
- **G-guards G1-G33** all in force (G27/G28/G29 added v8.77 for the
  production-stack surface; G30/G31 added v8.87 for the audit-log
  archive+purge constitutional carve-out; **G32/G33 added v9.07 for
  the parallel Pheromone archive+purge framework — G32: Lifecycle
  PheromoneCheckpoint is strictly append-only with NO GUC carve-out
  at the checkpoint layer; G33: uc_pheromone_archive_purge is the
  only sanctioned DELETE path on Pheromone**)
- **Audit-of-record discipline** (v8.20) — every ship still
  produces a CHANGELOG entry; every MEDIUM/HIGH decision still
  gets a Sanctum (the protocol is faster — DECIDED-on-arrival
  when the directive is unambiguous — not skipped)
- **The override pattern audit-of-record** still recorded in
  §IX of relevant Sanctums; no override is invisible

**Both contracts are operator-revocable.** VANTA may return to
steady-state at any time via a fresh Sanctum; the agent does
not unilaterally adopt or change postures. The constraint is on
the *agent*, not on VANTA.

### v1 done-list (closed 2026-05-09)

1. ✅ Schema models the full lifecycle of an identity token (achieved v1)
2. ✅ Stored procedures cover UC-1 through UC-7 (achieved v1)
3. ✅ Application layer enforces context-scoped verification (achieved v3)
4. ✅ Cybersecurity controls: CSP, CSRF, rate-limit, role-based auth (achieved v4)
5. ✅ Concurrency hazards identified and sealed with tests (achieved v6)
6. ✅ Scales to 2M+ events with bounded API responses (achieved v6)
7. ✅ Test coverage: 1077 Python (12 test classes incl. property + redaction-property) + 171 SQL self-tests (achieved v6/v7; growing each release — last counted via ai-test-counts.sh)
8. ✅ Threat model: STRIDE-categorized, every threat mapped to a control (DEVNOTES/threat-model.md)
9. ✅ Antimeridian-spanning bbox queries (wrap-aware predicate; 11_atlas.sql)
10. ✅ Cursor pagination on list pages (achieved v7.4 — keyset cursors on /tokens and /verifications)
11. ✅ Property-based tests for invariants (10 Hypothesis tests on C1, C2, C3 in test_invariants_property.py)
12. ✅ Multi-process rate limiter (Redis-backed) (achieved v7.5 — `InMemoryRateLimiter` + `RedisRateLimiter` with auto-selection)
13. ✗ External IdP integration (OIDC) — RETIRED 2026-05-09 (out of v1 scope; not on v2; do not auto-propose)
14. ✗ Banking-on-Polaris reference architecture (separate repo) — RETIRED 2026-05-09 (correct answer is a separate repo consuming Polaris over HTTP; tracked in `memory/deferred_items.md`; not on v2)
15. ✗ Linux + Windows variant of the launcher — RETIRED 2026-05-09 (macOS launcher is the SCS-230 deliverable surface; cross-platform is an operational concern, not a mission item)

**Note on retirement.** Items 13–15 were marked `⏸ DEFERRED` from
2026-05-09 to v8.26, then re-classified as `✗ RETIRED` once it
became clear (after the v2 close-out) that they were not paused
pending a future epoch — they were outside the mission scope.
Memory file `memory/deferred_items.md` binds `ai-propose` to skip
them. Audit-of-record: the `DEFERRED 2026-05-09` history is
preserved in this annotation; nothing was deleted.

### v2 done-list (closed 2026-05-12 at 12/12 ✅, opened 2026-05-09)

The v2 arc is **D + A** (substrate-level demonstrations + the report's
open problems). See `meta/missions-considered.md` for the full set of
arcs evaluated and the case for this combination.

**Substrate-level demonstrations (D — make Appendices E and F concrete):**

M2-1. ✅ **Real ZK-SNARK for ZERO_KNOWLEDGE verifications** (achieved
       v8.23 / R10-1 — `TokenStateEpoch` table is the 7th audit-of-record;
       Plonky2 SNARK (FRI-based, post-quantum-comfortable) proves Merkle
       inclusion bound to `(epoch_id, context_id, nonce)` public inputs;
       Rust crate `polaris_zk/` provides the prover/verifier CLI;
       `polaris_web/zk.py` is the subprocess wrapper; `uc11_close_epoch`
       procedure with per-procedure advisory lock (6th catalog entry);
       three `/api/zk/*` routes (epoch close, get, verify); 5 SQL self-
       tests in section P, 15+ Python `ZKSnarkTests`, 3 Rust unit tests
       (honest prover, replay, cross-epoch), 2 concurrency tests. C3+A4+B3
       picked by VANTA at the M2-1 exploration Sanctum: transparent setup,
       Plonky2, hybrid-Merkle reusing R10-2. **Substrate-D arc closed
       5/5** — every primitive named in PDF Appendices E and F is now
       in-tree or scaffolded.).

M2-2. ✅ **Functional DID anchoring** (achieved v8.21 / R10-2 —
       `AnchorBatch` table is the off-chain audit-of-record;
       `close_anchor_batch(algorithm_id, root, proofs)` procedure
       groups pending `BlockchainAnchor` rows by signature algorithm
       under a per-algorithm advisory-lock (4th entry in the catalog);
       `polaris_web/anchoring.py` Merkle helper (SHA3-256 default, sort
       by anchor_id for publish-then-fork resistance); three Flask
       routes (`/api/anchor/batch`, `/api/anchor/<token_id>`,
       `/api/anchor/verify/<token_id>`) — the last one server-side
       reconstructs the Merkle root from leaf + proof and rejects
       tampered logs; 5 SQL self-tests in section O, 15 Python tests in
       `AnchorBatchTests`, 2 concurrency tests for the lock contract.
       Substrate-D arc closed 5/5 — M2-1 ZK-SNARK delivered v8.23).

M2-3. ✅ **Substrate-dependency manifest** (achieved v8 —
       `DEVNOTES/substrate.md` is the prose form; `SystemDependency` view
       in `polaris_sql/13_substrate.sql` is the queryable mirror; 27 rows
       across 7 layers (crypto, network, storage, runtime, standards,
       hardware, human); `SubstrateManifestTests` confirms the prose and
       SQL forms agree).

M2-4. ✅ **GenomicAnchor schema (Appendix F.1)** (achieved v8 — table with
       three CHECK constraints: hex-only, algorithm-specific length, and
       genomic-alphabet refusal; 11 tests in `GenomicAnchorTests`).

M2-5. ✅ **QuantumObserverBinding scaffold (Appendix F.2).** Schema
       scaffold with explicit DEFERRED markers on functional fields, and
       a rationale doc explaining what the binding becomes when
       quantum-observer hardware is real. Acceptance: table exists,
       comments explain the deferred state, schema does not block the
       eventual functional implementation.

**The PDF's open problems (A — close the loops §9 explicitly opens):**

M2-6. ✅ **Multi-signature transitional state** (achieved v8.18 /
       R11-1 — `TokenSignature` M:N table with UNIQUE composite key
       and deprecation_after_signed CHECK; partial index on active
       set; two triggers — `enforce_token_has_active_signature`
       (≥ 1 active per token) and `enforce_token_signature_immutability`
       (write-once except for one-way deprecation_date);
       `uc6_migrate_algorithm` procedure with `pg_advisory_xact_lock`
       on token_id for C9 correctness; UC-1 and UC-9 extended to
       insert TokenSignature alongside the new IdentityToken; backfill
       block for v1 sample tokens; verification path + dashboard
       Post-Quantum panel read from TokenSignature; 16 tests in
       `MultiSignatureTests` + 3 in `ConcurrencyTests` (per-token race,
       verify+migrate snapshot consistency, cross-token parallelism)
       + 5 SQL self-tests in section N; `DEVNOTES/ships/multi-sig-migration.md`
       documents the adversary walk, the verification consistency
       model, the no-auto-derivation argument, and the
       issuer-trust-concentration triad positioning. Closes the
       cryptographic-diversity leg of PDF §9 alongside R11-6 ✅;
       M2-8 federation remains the unbuilt third leg.)

M2-7. ✅ **Catastrophic-loss recovery — UC-9** (achieved v8.17 /
       R11-2 — `RecoveryRequest` table with four CHECK constraints
       encoding the mechanism: 48h cool-down minimum, three-channel
       OOB verification required for APPROVED, decided_at after
       cool-down, approver ≠ requester; partial unique index
       `uq_one_pending_recovery_per_individual` for one PENDING per
       individual; two-phase procedures `uc9_initiate_recovery`
       (operator) + `uc9_complete_recovery` (admin only, RAISE
       EXCEPTION enforced); `pg_advisory_xact_lock` on
       claimed_individual_id for C9 correctness; APPROVED branch
       transitions non-terminal tokens to LOST + publishes each to
       RevocationList + issues new ACTIVE token with
       predecessor_token_id=NULL + tags all lifecycle rows with
       `[RECOVERY:<id>]`; three Flask routes + templates;
       15 CatastrophicLossRecoveryTests + 2 ConcurrencyTests; 5 SQL
       self-tests in section M; `DEVNOTES/ships/recovery-ceremony.md`
       documents the adversary walk, mechanism design, and the
       administrative-vs-operational grace-period framing. The third
       leg of the "schema doesn't weaponize itself against the
       holder" triad (entry R11-4, exit R11-6, recovery this).)

M2-8. ✅ **Issuer federation model** (achieved v8.22 / R11-3 —
       `AgencyTrustAttestation` table is the 6th audit-of-record;
       `enforce_attestation_immutability` trigger enforces one-way
       revocation; `uc10_attest_trust` + `uc10_revoke_attestation`
       procedures with per-attesting-agency advisory lock (5th catalog
       entry); explicit-only federation (NO transitive trust);
       verification flow gates SUCCESS outcomes by `_federation_trust_holds`
       check; `/api/federation/attest` + `/api/federation/revoke`
       routes (admin); 6-row seed graph explains existing demo
       verifications; 15 `IssuerFederationTests` + 2 concurrency tests
       + 5 SQL self-tests in section P. Closes the issuer-trust-
       concentration triad to 3/3 (after R11-1 cryptographic diversity
       and R11-6 constitutional limits).

M2-9. ✅ **Tiered enrollment / population coverage** (achieved v8.16 /
       R11-4 — `EnrollmentStatusEvent` table with 5-status CHECK enum;
       `IndividualCurrentEnrollment` view returns latest event per
       individual with COALESCE fallback to `NOT_ENROLLED`;
       `seed_default_enrollment_status` trigger materializes the
       default state on every new Individual; append-only invariant
       extended to the new table; `civic_enrollment_summary` function
       returns per-jurisdiction × status counts only — per-individual
       NOT_ENROLLED enumeration deliberately not first-class;
       10 tests in `TieredEnrollmentTests` + 5 SQL self-tests in
       section L; `DEVNOTES/ships/tiered-enrollment.md` documents the
       asymmetric design (EXEMPT frictionless, mass-NOT_ENROLLED
       enumeration deliberate) and the PDF §9 anchoring.)

M2-10. ✅ **Compulsion resistance — duress codes (§9.5)** (achieved
       v8.24 / R11-5 — `IdentityToken.duress_code_hash` Werkzeug scrypt
       commitment; `DuressEvent` table is the 8th audit-of-record
       (append-only via `reject_audit_modification`);
       `uc12_record_duress` procedure with no advisory lock (pure
       append, no contention); `_check_and_record_duress` helper uses
       `werkzeug.security.check_password_hash` for constant-time
       comparison; the verification flow proceeds identically to the
       coercer (R2 audit refinement) while silently writing the
       DuressEvent; `/api/duress/events` (admin/auditor) is the OOB
       dashboard; `/verifications` operator list does NOT join to
       DuressEvent (R6 anti-revealing posture); 5 SQL self-tests in
       section R + 13 `DuressCodeTests`. **The v2 mission-closer —
       v2 done-list = 12/12 ✅.**).

M2-11. ✅ **Issuer-discretion bounds** (achieved v8.15 / R11-6 —
       `IssuerDiscretionPolicy` table for per-agency overrides;
       `uc8_revoke_token` stored procedure enforces a rolling N%/W-day
       cap with optional higher-authority co-signer; system defaults
       N=5.00% / W=30 days set via `ALTER DATABASE` GUCs;
       `enforce_revocation_velocity_bound` belt-and-suspenders trigger
       rejects raw UPDATEs; `pg_advisory_xact_lock` per agency_id
       serializes concurrent boundary races for C9 correctness;
       11 tests in `IssuerDiscretionBoundsTests` + 2 in
       `ConcurrencyTests` + 7 SQL self-tests in section K;
       `DEVNOTES/ships/issuer-discretion.md` documents the policy choices,
       adversary walk, and PDF §9 anchoring).

M2-12. ✅ **Verification-graph redaction proof** (achieved v8 —
       `meta/redaction-proof.md` documents the adversary model and the
       five enumerated side-channels; `test_redaction_property.py`
       instantiates a `UniformGuessAdversary` against ZK-only sequences
       and confirms the privacy bound, plus a `TemporalCorrelationAdversary`
       and `SpatialUniquenessAdversary` that prove CE-1 and CE-2 succeed
       — the documented operational limitations the schema cannot
       mitigate; 6 tests in `RedactionPropertyTests`).

Items M2-1..M2-5 are the substrate arc (D); M2-6..M2-12 are the open-
problems arc (A). Roadmap sequencing in `ROADMAP.md` (R10-* for D items,
R11-* for A items). Risk classes range from LOW (M2-3, M2-5, M2-12) to
HIGH (M2-1: cryptographic rabbit hole; M2-8: cross-jurisdiction trust
model). The agent should treat MEDIUM/HIGH items as propose-and-wait
unless the user has explicitly authorized autonomous execution for the
specific item.

### Arc D — Swarm / HYDRA (closed 2026-05-12 at 8/8 ✅, opened 2026-05-12)

HYDRA host (`polaris_hydra/host.py`) + 7 watchers (expanded to 9
in v8.72 — see Arc G + the v8.72 mythology relocation). The swarm's
centralized-synthesis layer; aggregates N specialist watchers into
a single Architect-voice brief for VANTA. Built against
prior-art reference codebases (BettaFish + MiroFish; studied for
pattern, not vendored).

**Done-list:** H1–H8 all ✅. R12-* sequence in `ROADMAP.md`.

For the per-item record, the watcher cohort detail, the boundary
discipline, and post-Arc-D extensions (TrajectoryWatcher v8.49;
AntColonyWatcher + CivitasWatcher v8.72), see
**`meta/arc-d-hydra.md`**. For the operational guide, see
`polaris_hydra/README.md`.

---

### Arc E — Mycelium / genuine swarm intelligence (active, opened 2026-05-13)

Decentralized swarm substrate underneath HYDRA. Tiny ants deposit
**pheromones** onto brain-map nodes via the append-only `Pheromone`
table (an additional audit-of-record beyond the canonical 12; has
archive+purge framework per v9.07). Synthesis EMERGES from
pheromone density across the brain-map graph; no host calls in
Phase 1. Operators read the heatmap via `scripts/ai-swarm-bloom.sh`.

Roman organizational metaphor extended through the arc:
**Legions** (military) under TESTUDO / TRIPLEX_ACIES / CUNEUS /
VEXILLATIO / AUXILIA tactical doctrines; **Civitas** (civilian) with
Plebs / Equites / Augures / Censores citizen classes; **Cursus
Honorum** (career path) feeding into Arc F's economic dimension.

**Done-list:** E1, E2, E6, E7, E8, E9, E10 ✅ (7/10). E3, E4, E5
deferred (bloom integration; deliberation threshold; HYDRA-vs-
Mycelium decision Sanctum). R13-* sequence in `ROADMAP.md`.

For the per-item record (E1–E10 narratives, legion structure +
Roman tactics, Civitas details, the 100-year-architect-report
findings, the acceleration + consciousness expansion), see
**`meta/arc-e-mycelium.md`**. For the Polaris-as-Civitas concept
mapping, see `meta/civitas.md`. For the operational guide, see
`polaris_swarm/README.md`.

---

### Arc G — Roman Empire opening (active multi-day, opened 2026-05-13)

Empire-pattern expansion of the Mycelium swarm: new military
**Imperial legions** (Praetorian, Engineer) + new civilian class
(**Tribuni Plebis**) + **Via Appia** priority property on
AntFinding. Architect recommended Option A (decline; revisit with
operational data); VANTA chose Option C (ship Phase 1 in full).
The override is on record; the Architect's Empire-metaphor caution
(§IV of the opening Sanctum) stands as the prediction-vs-reality
reference for future `--reflect` runs.

**Done-list:** G1 ✅ (Phase 1 foundations). G2, G3 deferred.
R15-* sequence in `ROADMAP.md`.

For the per-item record (Phase 1 ant + citizen + Via Appia detail,
G21-G25 G-guards, the Empire-metaphor caution), see
**`meta/arc-g-empire.md`**.


### Arc F — the Denarius (active, opened 2026-05-13; closed 4/4 then reopened with F5 amendment)

Economic dimension of the Civitas. The **denarius** distinguishes
ants whose pheromones lead to drift resolution from ants whose
pheromones decay unread. **The pomerium holds:** denarius is SWARM
currency, not Polaris currency; C10 (*identity ≠ money*) preserved
verbatim. New 5th citizen class (`quaestor_treasurer`) + new
filesystem-AoR (`treasury-roll.json`, the 3rd FS-AoR) + Cursus
Honorum multipliers (eques 1.5×, patrician 2.0×).

**Done-list:** F1, F2, F3, F4, F5 ✅ (5/5; arc reopened with F5
amendment after the post-v8.72 100-year simulation surfaced the
reward-function flaw). R14-* sequence in `ROADMAP.md`.

For the per-item record (F1–F5 narratives, the F2 chaos test, the
F3 proposal-loop closure, the F4 Cursus Honorum activation, the
F5 reward-function exemption fix), see **`meta/arc-f-denarius.md`**.
For the deeper economic theory (property classes, Cursus Honorum,
Goodhart's Law mitigation), see `meta/denarius.md`.

### Arc B — Production deployment (active multi-phase, opened 2026-05-14)

Production-readiness arc. Polaris was, before v8.77,
**architecturally rich but productionally thin** — cryptography,
schema, audit-of-record, and cognitive substrate were
production-grade, but the deployment story was the dev launcher.
A reference implementation that no operator can deploy is not
actually a reference. Arc B closes that gap.

**Phase 1 (✅ shipped 2026-05-14 as v8.77):** TLS via Caddy
(Let's Encrypt auto), file-mounted secrets (Docker secrets at
`/run/secrets/`), structured `/api/health` JSON with per-component
checks, multi-stage non-root Dockerfile.prod, idempotent
`polaris-deploy.sh` with rollback-on-fail, manifest-verified
`polaris-backup.sh`, secret-rotation tooling, and the operator
runbook + secrets primer. **G27** (TLS required), **G28** (no
sensitive env-var literals in prod compose), **G29** (structured
health JSON) added.

**Phase 2 (⬜ deferred):** WebAuthn + hardware-token operator auth;
audit-log archive policy (S3 / Glacier rotation); multi-instance
scaling (pgbouncer + gunicorn tuning + Redis cluster);
`polaris-restore.sh` recovery-from-backup with validation.

**Phase 3 (⬜ deferred):** Multi-region deployment patterns;
disaster-recovery runbook (RPO/RTO targets); SOC 2 readiness
checklist.

**Done-list:** R16-1..R16-10 (Phase 1) all ✅. R16-* sequence in
`ROADMAP.md`.

For the strategic record, per-item rationale, and what Phase 2 / 3
open conditions look like, see **`meta/arc-b-production.md`**.
For the operator-facing runbook, see `docs/operator/OPERATIONS.md`
and `docs/operator/SECRETS.md`.

---

## The agent's relationship to this mission

When the agent picks up Polaris in a fresh session:

1. Read this file first. It's the canonical statement of intent.
2. Anything in `ROADMAP.md` should trace back to a ⬜ in the v2
   done-list (M2-1..M2-12), or to a maintenance / hardening concern
   that supports the existing v1 work without violating C1–C10.
3. Anything in `docs/BACKLOG.md` should be a candidate for promotion to
   ROADMAP, contingent on mission alignment.
4. When the agent proposes work via `scripts/ai-propose.sh`, the
   proposal includes a one-line **mission alignment** justification
   (which v2 item; or which v1 constraint the work strengthens).
5. When the agent executes work, the post-execution journal entry
   notes which mission item moved (e.g. "advanced M2-3 from ⬜ to
   ✅" or "advanced item 10 from 🟡 to ✅").
6. When `scripts/ai-status.sh` runs, it scores current state against
   the constraints (C1–C10) and BOTH done-lists (v1: items 1-15;
   v2: M2-1..M2-12).
7. v1 items 13–15 are **RETIRED** (v8.27), not paused. They were
   `⏸ DEFERRED` from 2026-05-09 through v8.26; once v2 closed and
   the items were re-examined, they proved to be out-of-scope rather
   than waiting on a future epoch. `ai-propose` skips them under
   either marker. They reappear on the active queue only if the user
   explicitly resurrects them — see `memory/deferred_items.md` and
   the v8.27 entry in CHANGELOG.md for the audit annotation.
8. The arcs that were considered for v2 and not chosen (B —
   adversarial hardening; C — Polaris-as-platform) live in
   `meta/missions-considered.md`. A future session can resurrect them
   if the chosen arc completes or context shifts; the analysis is
   already done.

The mission is the agent's reward function. The reward signal is:
"did this advance Polaris toward the v2 done-list (or close a v1
deferred item the user has resurrected) without violating any C1–C10
hard constraint?"
