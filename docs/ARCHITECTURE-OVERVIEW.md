# Polaris architecture overview

**Audience:** an engineer or auditor evaluating Polaris.
**Goal:** understand what Polaris IS, what it is NOT, what the layers
are, and how to navigate the codebase.
**Length:** ~5000 words; ~20 minutes to read.

This document is the architect-tier brief that pairs with
`docs/QUICKSTART.md` (operator quickstart). Quickstart gets a stack
running; this document explains why each piece looks the way it does.

---

## §I. What Polaris is

Polaris is a reference implementation of a national identity token
system. It demonstrates a substrate where:

- **One identity per person** is enforced by a partial unique index,
  not by application logic.
- **Audit-of-record** is enforced by append-only triggers, not by
  developer discipline.
- **Zero-knowledge verification** is enforced by a server-side trigger,
  not by client-side cooperation.
- **Post-quantum cryptography** is at the substrate, not as a future
  migration path.

The phrase "by construction" appears throughout. It is shorthand for:
the system cannot be operated in a way that violates the constraint,
because the constraint is enforced before any application code runs.

Polaris is built for SCS-230 (Database Management Systems) at Seton
Hill University, by Egor Khaklin (VANTA). The version trajectory is
v1 (course assignment: schema + Flask) through v9.x (current reference
implementation with cognitive substrate). This document covers the
v9.x architecture as of v9.23 (2026-05-15).

---

## §II. What Polaris is NOT

Equally important. Polaris does not:

- **Hold money.** No transactions, no balances, no merchant codes.
  C10 ("Identity is not money") is constitutional. A separate
  swarm-currency ledger (Denarius) lives in `polaris_swarm/civitas/`
  but is structurally segregated from identity tokens.
- **Aggregate across individuals.** v9.19 ontology layer refused
  cross-individual aggregation primitives with a structural
  regression guard. Object Cards are single-entity-focused.
- **Provide notebook authoring or predictive scoring.** Refused
  patterns documented in v9.19 ship.
- **Run with multi-region failover.** v9.16 RESERVED-NOT-PLANNED for
  Arc G (Empire / multi-region). Single-region only.
- **Carry a state-level surveillance API.** The verification graph is
  structurally inaccessible at the ZERO_KNOWLEDGE disclosure level
  (C2 trigger enforces `token_id IS NULL`).

Each of these is a deliberate constitutional decision, recorded in
Sanctum files (`sanctum/` directory). The Architect + Anti-Architect
protocol (v9.11) exists specifically to catch any drift toward these
refused patterns; the Anti-Architect's 8-pattern catalog (AP1-AP8 in
`meta/architect.md`) names the failure modes.

---

## §III. The vocation

Above the ten hard constraints (C1-C10) sits the vocation, named in
v9.11: **anti-coercion**. Every constraint serves this vocation:

- C1 (audit-of-record): a coerced operator's actions leave evidence
- C2 (zero-knowledge): the verification graph is not a coercion
  surface
- C3 (one identity per person): a coerced individual cannot be
  duplicated to bypass quotas
- C4 (atomic failed-login counter): a coerced operator cannot be
  used as a credential-stuffing oracle without trace
- C5 (CSP forbids inline scripts): a coerced operator's session is
  not exploitable via injection
- C6 (server-side disclosure enforcement): a coerced client cannot
  unilaterally upgrade their disclosure level
- C7 (no hardcoded crypto): a coerced operator can rotate algorithms
  without invalidating existing identity claims
- C8 (bounded result sets): a coerced operator cannot extract the
  whole population via /api/atlas/* endpoints
- C9 (concurrency hazards tested with real threading): a coerced
  operator cannot rely on race-condition exploits documented in
  the test suite
- C10 (identity is not money): a coerced operator cannot be used to
  forge financial state via the identity rail

Anti-coercion is the deepest constraint — explicitly above C1-C10 in
`MISSION.md §"Vocation"`. The Anti-Architect's AP5 (vocation drift)
fires when any proposal moves the system away from this alignment.

---

## §IV. The layers

Polaris has three concentric layers and a fourth perpendicular layer:

### Layer 1: Data substrate (`polaris_sql/`)

PostgreSQL 16. 27 tables, 14 stored procedures, 20 triggers, 12
audit-of-record instances (9 schema + 3 filesystem), 33 schema-level
guards (G-guards G1-G33). Migrations framework (v8.95) records
SHA-256 hashes; append-only by trigger.

The schema is the constitution. The Flask application is a UI on top
of the schema. The schema can be operated via raw SQL (the
`/sql` route is an authenticated console) and the constraints still
hold — they are not mediated by the application.

Key tables (27 total, partial list):
- `IdentityToken` — the central object
- `Individual` — the person an identity is bound to
- `Agency` — the issuer of an identity
- `CryptographicAlgorithm` — algorithm-rotation substrate (C7)
- `TokenLifecycleEvent` — append-only audit (C1)
- `VerificationEvent` — append-only audit (C1, C2)
- `EnrollmentStatusEvent` — append-only audit (R11-4)
- `TokenSignature` — multi-sig migration substrate (R11-1)
- `AnchorBatch` — Merkle anchoring substrate (R10-2)
- `AgencyTrustAttestation` — federation substrate (R11-3)
- `DuressEvent` — duress code substrate (R11-5)
- `QuantumObserverBinding` — SCAFFOLD; RESERVED-NOT-PLANNED (v9.23)
- `AuditAccessLog` — meta-audit (v9.20); append-only
- `OperatorWebauthnCredential` — operator MFA substrate (v8.97)
- `schema_version` — migration registry (v8.95)
- `Pheromone` — Mycelium substrate (v8.62+)
- `LifecyclePheromoneCheckpoint` — Pheromone rotation (v9.07)
- ...

### Layer 2: Application (`polaris_web/`)

Python 3 / Flask / gunicorn. ~4,298 lines of `app.py`. ~851 lines of
`security.py`. ~459 lines of `webauthn_auth.py`. Templates use Jinja2.
CSS is hand-rolled (no Tailwind), navy/gold intelligence-report
aesthetic. JavaScript is external-only (no inline scripts; CSP
enforces). The atlas globe uses D3 + topojson, no CDN dependency.

Application architecture is straightforward: routes map to UC stored
procedures; the application does authentication, CSRF, rate-limiting,
and rendering; the SQL layer enforces correctness.

### Layer 3: Cognitive substrate (`polaris_hydra/`, `polaris_swarm/`, `polaris_foresight/`)

This is the unusual layer. Polaris has a cognitive substrate that
monitors itself:

- **HYDRA**: 9 watcher modules (schema, cognitive, security, mission,
  adversary, performance, trajectory, ant_colony, civitas) + CM
  (Constitutional Meta-constraint, the immortal 10th head). Each
  watcher scans the running system and emits findings. The
  CorrelationEngine aggregates findings across watchers. Brief is
  the per-session synthesis output, archived to `journal/hydra/`.

- **Mycelium**: 33 commander ants across 11 manifest legions + 1
  reserved (twelfth-legion slot, RESERVED), 9 soldier classes (8
  workers + 1 priest `soldier_swarm_witness` added v9.11), 6 citizens
  (Plebs, Equites, Augures, Censores, Quaestores, Tribuni Plebis),
  and a Treasury (Denarius ledger). High-cadence empirical
  observation; writes Pheromone rows to the substrate.

- **Foresight surface** (v9.12): minimum-viable forward-looking
  research surface. ForesightAgent emits Brief with 5 sections; §IV
  (vocation-aligned-gaps) is STRUCTURALLY required at construction
  time. FS-XXXXXXXX promotion module promotes candidates to ROADMAP
  with vocation-alignment required. Empirical-graduation rule: 50%
  acceptance over 6 distinct months; below threshold triggers SUNSET.

The cognitive substrate has three time-scales:
- High-cadence (Mycelium): continuous; per-ant deposits at sub-second
  cadence; writes to the substrate
- Mid-cadence (HYDRA): per-session synthesis; reads the substrate;
  writes briefs
- Low-cadence (Sanctum / Architect / Anti-Architect): per-decision;
  reads everything; writes constitutional records

The substrate (Mycelium) → lens (HYDRA) → unified brief is the
distinguishing v9.x architectural contribution.

### Layer 4 (perpendicular): Operator scripts (`scripts/`)

29 `ai-*.sh` scripts (the agent-facing cognitive layer) plus 17
`polaris-*.sh` scripts (the operator-facing operational layer). The
`ai-*` scripts mediate agent-operator collaboration; the `polaris-*`
scripts mediate operator-system collaboration.

The `polaris-*` scripts are documented one-per-file with full usage
in the script header. Examples:
- `polaris-deploy.sh` — bring up production stack
- `polaris-backup.sh` — atomic full-system backup
- `polaris-restore.sh` — recovery from backup
- `polaris-migrate.sh` — apply or roll back migrations
- `polaris-rotate-secret.sh` — rotate secrets without downtime
- `polaris-archive.sh` — export audit-log rows to cold storage
- `polaris-recover-admin.sh` — emergency unlock for locked-out admin
- `polaris-cron-install.sh` (v9.23) — install operator crontab
- `polaris-set-webauthn-deadline.sh` (v9.23) — set WebAuthn deadline
- `polaris-loadtest-tokens.sh` (v9.23) — token-volume load simulator

---

## §V. Identity flow (concrete walkthrough)

The five stages of an identity:

1. **Enrollment** (`uc4_activate_reserve`): an individual is added
   to the system; their `IdentityToken` row starts in `RESERVED`
   state. Tier-A vs Tier-B enrollment (R11-4) determines the
   level of attestation required.

2. **Issuance** (`uc1_issue_and_activate`): the token transitions
   from `RESERVED` to `ACTIVE`. A signing key from
   `CryptographicAlgorithm` is bound. A `TokenLifecycleEvent` row
   is written (C1).

3. **Verification**: a relying party submits a verification request.
   The disclosure level is one of `ZERO_KNOWLEDGE`, `EXISTS_AT_ALL`,
   `PARTIAL`, `FULL`. Server-side enforcement (C6) sets
   `token_id` to NULL on ZERO_KNOWLEDGE events (C2). A
   `VerificationEvent` row is written (C1). The new
   `requesting_purpose_text` column (v9.20) records the stated
   purpose.

4. **Revocation** (`uc8_revoke_token`): the token transitions from
   `ACTIVE` to `REVOKED`. Issuer-discretion bounds (R11-6) apply.
   A `TokenLifecycleEvent` row is written (C1).

5. **Anchoring** (R10-2 / M2-2): periodically, the running set of
   active tokens is hashed into a Merkle tree; the root is anchored
   to an external substrate; each token gets an inclusion proof.
   The ZK-SNARK (R10-1 / M2-1) proves epoch membership without
   revealing which token.

The duress flow (R11-5 / M2-10): an individual under coercion
provides their duress code instead of their primary code; the
verification appears to succeed to the coercer but a `DuressEvent`
row appears in the audit table.

---

## §VI. Cryptographic substrate

- **ML-DSA-65** (NIST FIPS 204): lattice-based signatures.
  Post-quantum secure under the Module-LWE assumption.
- **Plonky2 ZK-SNARK** (FRI-based, transparent setup, hash-only
  commitments): proves epoch membership.
- **SHA3-256 Merkle commitments**: anchor-set batching with
  logarithmic-per-leaf inclusion proofs.
- **M-of-N multi-sig migration** (R11-1): per-token signature
  schemes; algorithm rotation without invalidating existing tokens.
- **Constant-time duress code check** (R11-5): coercer-visible flow
  is identical to legitimate flow.
- **Per-context trust attestations** (R11-3 federation): Agency V
  accepts agency I for context C until date D; no transitive trust.

The crypto is REAL, not stubbed. The Plonky2 SNARK has a working
prover/verifier in Rust (`polaris_zk/`). Signature verification is a
live FIPS 204 path. The Merkle anchoring batches actual tokens.

The constraint C7 (no hardcoded cryptography) means algorithm
parameters flow through the `CryptographicAlgorithm` table. To
rotate, an operator updates the table; no schema migration required.

---

## §VII. The cognitive layer in depth

### HYDRA

`polaris_hydra/host.py` orchestrates 9 watchers. Each watcher
inherits from a base class, scans a designated surface, and emits
findings into a SQLite cache. CorrelationEngine groups findings by
node_id (with v9.10's additive shared-surface design: findings can
have `additional_node_ids` for cross-watcher correlation). The
synthesis output is a structured brief.

Briefs are archived to `journal/hydra/<YYYY-MM-DD>-<HHMM>.md` via
`ai-hydra.sh --full --save`.

### Mycelium

`polaris_swarm/` contains the swarm orchestrator + per-legion logic.
Manifest legions (11):
- Republican: schema, cognitive, security, mission, adversary,
  performance, trajectory, substrate, docs (9)
- Imperial: Praetorian, Engineer (2 added v8.71)

Reserved (1): twelfth-legion slot, held in deliberate reserve
(`meta/twelfth-legion.md`) until operational need surfaces.

Soldier classes (9):
- 8 worker classes: each maps to a specific scan
- 1 priest class: `soldier_swarm_witness` (v9.11) gives the substrate
  internal self-knowledge by reading recent Pheromone deposits and
  emitting meta-pheromone under `witness:swarm:*`

Citizens (6): Plebs, Equites, Augures, Censores, Quaestores, Tribuni
Plebis. Each handles a different aspect of swarm governance.

The brain-map (`scripts/ai-brain-map.sh` → `meta/brain-map/`)
visualizes the full cross-tier system as a graph (383 nodes since
v9.15). The swarm-map (`scripts/ai-swarm-map.sh` → `meta/swarm-map/`)
visualizes the Mycelium tier specifically.

### Foresight surface (v9.12)

`polaris_foresight/` package. ForesightAgent emits Brief with 5
sections (§I-§V). §IV (vocation-aligned-gaps) is STRUCTURALLY
required at construction time via `Brief.__post_init__`. The agent
does not call out to an LLM and does not fetch external data; it is
deterministic over local state.

FS-XXXXXXXX promotion module promotes candidates to ROADMAP.md as
candidate items. Vocation-alignment is REQUIRED; non-anti-coercion
candidates are silently skipped (`skipped_no_vocation` counter).
Idempotent — re-promotion adds nothing.

Empirical-graduation rule (Anti-Architect modification): the
`_acceptance_log.json` tracker counts distinct calendar months
(deduped per v9.13 fix); if 6 distinct months have elapsed and
acceptance rate is < 50%, the surface fails the empirical-
graduation test and the SUNSET clause fires.

### The Sanctum protocol

For MEDIUM/HIGH-risk strategic decisions — opening a new arc,
modifying the cognitive layer itself, changing what Polaris IS or IS
NOT — the agent does NOT present an ad-hoc recommendation in chat.
The agent enters the Sanctum (`scripts/ai-sanctum.sh`).

The Sanctum protocol is a 4-state lifecycle: OPEN → DECIDING →
DECIDED → SHIPPED (CLOSED canonical synonym for SHIPPED). Optional
intermediate states. The Sanctum file is itself an audit-of-record
instance (constitutional record).

The Architect + Anti-Architect protocol (v9.11) is layered on top
of Sanctum. The Architect generates a forecast / position from live
repo state; the Anti-Architect contests it under the 8-pattern
catalog; both converge or escalate to operator.

Pattern #20 Constitutional Discipline (18 instances) records every
Sanctum decision and its outcome.

---

## §VIII. What the test suite covers

- ~1063 Python tests across 165 TestCase classes
- 19 Hypothesis property tests for C1, C2, C3
- 62 schema-CHECK regression tests
- 882 structural-invariant tests
- 171 SQL self-tests in 08_tests.sql + section S in 08_tests.sql +
  section T in 12_v7_constraints.sql

Run via `./scripts/ai-test.sh` (or `quick` mode that skips
concurrency/property tests).

The structural-invariant tests are unusual: they verify that the
codebase IS A CERTAIN SHAPE, not just that it does the right thing
on a given input. Examples:

- `test_polaris_version_is_canonical`: app.py imports version from
  `__version__.py` rather than redefining
- `test_dockerfile_covers_all_runtime_app_modules`: every
  top-level import in app.py is COPY'd by both Dockerfiles
- `test_no_mythic_agents_in_foresight_package`: the v9.12 Anti-
  Architect modification is structurally pinned
- `test_ontology_refuses_cross_entity_aggregation`: v9.19 surveillance
  pattern refusal pinned

A new TestWaveNN_VNNN class is added per ship to pin the ship's
specific invariants.

---

## §IX. Deployment

Three deployment paths (see `docs/DEPLOYMENT.md`):

1. **Single-host Docker (the reference path)**: Docker Compose
   orchestrates Caddy + Postgres + Redis + gunicorn. The
   `polaris-deploy.sh prod` script automates this end-to-end.
2. **Kubernetes**: Helm chart deferred until Arc G triggers fire
   (v9.16).
3. **Bare-metal**: documented but not automated.

For each path: TLS via Caddy + Let's Encrypt; secrets via
`polaris-generate-secrets.sh`; backup via `polaris-backup.sh`;
restore via `polaris-restore.sh` (see `DR-SINGLE-REGION.md`).

Production checklist:
- Change all demo passwords
- Set `webauthn_required_after` on all admin accounts
- Configure backup destination + cron
- Set up off-host backup replication
- Configure quarterly DR drill (in crontab)
- Subscribe to security advisories
- Review threat models (`DEVNOTES/threat-model.md` + cognitive)

---

## §X. The structural-architecture insight

`meta/structural-architecture.md` documents the philosophy: every
claim Polaris makes is enforced by a structural primitive (trigger,
constraint, index), not by a policy primitive (developer discipline,
review process). The Removable Test asks: "if I remove this
structural primitive, does the claim still hold?" If yes, the
primitive is redundant; if no, the primitive is load-bearing.

The structural primitives are documented in
`meta/structural-constants.json`. The C1-C10 constraints map to a
10-node lattice (`meta/constraint-lattice.md`). The 22-pattern
catalog (`scripts/ai-pattern.sh`) documents recurring constructive
shapes.

---

## §XI. The constitutional moment

The post-v2 declaration (`sanctum/2026-05-12-post-v2-steady-state-
declaration.md`) records that Polaris reached steady-state on
2026-05-12. The default posture for ambiguous requests is
DECLINE-AND-SURFACE: the agent does not silently expand into new
mission scope. New scope requires explicit operator authorization
via Sanctum.

This is itself an anti-coercion primitive: a coerced operator cannot
direct the agent into unbounded mission expansion without an
audit-of-record. The constraint binds the agent, not the operator;
the operator may authorize new scope at any time.

---

## §XII. What v9.x represents

The v9.x trajectory closed the gap between architectural sophistication
(v8.x) and operational reality (Arc B production deployment +
cognitive-layer self-monitoring + Sanctum protocol maturity). The
distinguishing v9.x contribution is **substrate → lens → unified
brief**: the cognitive layer can read its own observation substrate
and produce coherent self-assessment.

v9.11 named the vocation. v9.12 added foresight. v9.19 added the
investigative surface. v9.20 added meta-audit primitives. v9.23 (this
ship) adds operator-facing rollout + DR + cognitive threat model +
top-level GitHub conventions.

The next iteration's scope depends on which Arc B triggers fire (per
v9.16): production-deployment incident, partner integration,
federation requirement, or ≥10× verification volume.

---

## Further reading

- `MISSION.md` — the constitution
- `CLAUDE.md` — agent runbook (doubles as developer onboarding)
- `meta/cognitive-loop.md` — cognitive layer in depth
- `meta/autonomy-architecture.md` — risk classes + agent autonomy
- `meta/sanctum-protocol.md` — Sanctum protocol spec
- `meta/architect.md` — Architect persona + 8-pattern catalog
- `DEVNOTES/style.md` — VANTA's standing instructions
- `DEVNOTES/threat-model.md` — schema/runtime STRIDE model
- `DEVNOTES/threat-model-cognitive.md` (v9.23) — cognitive-substrate
  threats
- `docs/operator/OPERATIONS.md` — day-2 runbook
- `docs/operator/DR-SINGLE-REGION.md` (v9.23) — disaster recovery
- `docs/operator/WEBAUTHN-ROLLOUT.md` (v9.23) — WebAuthn rollout
- `docs/RED-TEAM-SCOPE.md` (v9.23) — external red-team scope

---

*Per BIG MISSION Sanctum, 2026-05-15. v9.23.*
