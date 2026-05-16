# GLOSSARY.md

Defined terms used across the Polaris codebase and documentation.
Where a term has a specific meaning that differs from common usage,
the Polaris-specific meaning is the one that applies.

Sections:

- [Identity-system primitives](#identity-system-primitives) — the
  Polaris core: tokens, individuals, agencies, events, contexts
- [Cryptographic primitives](#cryptographic-primitives) — ZK-SNARK,
  Merkle, multi-sig, duress codes, post-quantum
- [Schema invariants & enforcement](#schema-invariants--enforcement) —
  audit-of-record, append-only, partial unique index, CHECK constraints
- [Web app & operator concerns](#web-app--operator-concerns) — CSP,
  CSRF, rate limits, atlas, sessions
- [Production deployment (Arc B)](#production-deployment-arc-b) —
  Caddy, TLS, Docker secrets, /api/health
- [Cognitive substrate](#cognitive-substrate) — Sanctum, AoR, risk
  classes, CM (the four principles in MISSION.md)
- [HYDRA + Mycelium + Civitas](#hydra--mycelium--civitas) — watchers,
  ants, legions, citizens, pheromones
- [Arcs & versions](#arcs--versions) — Arc A/B/C/D/E/F/G + v1/v2
- [Governance & meta](#governance--meta) — risk classes, larping,
  patterns, override, parking-vs-deciding

---

## Identity-system primitives

**Active token** — a token whose `status = 'ACTIVE'`. Constraint C3
guarantees at most one per individual via partial unique index.

**Actor agency** — the agency that performed a specific lifecycle
event. Stored in `TokenLifecycleEvent.actor_agency_id`. May differ
from the issuing agency. Nullable for events with no human actor
(e.g. device-binding).

**Agency** — a government body or authorized organization. May
issue, deactivate, or verify tokens. See `Agency` table.

**Algorithm metadata** — cryptographic algorithm parameters
(name, family, key size, post-quantum status) stored in the
`CryptographicAlgorithm` table. Tokens reference an entry here;
algorithm choice is never hardcoded in app code (constraint C7).

**Context** — see `VerificationContext`. The purpose for which a
verification is performed (HEALTHCARE, BANKING, TRAVEL, etc.). A
verification recorded for one context cannot be replayed against
another. C9.

**Device binding** — the process of linking a physical hardware
token to a Polaris token. UC-3.

**Disclosure level** — how much information a verification reveals.
One of: `ZERO_KNOWLEDGE` (proves valid token exists, no identity
revealed), `SELECTIVE` (named attributes only), `FULL` (full
identity). Constraint C2 enforces `ZK → token_id NULL`.

**Holder** — the natural person to whom a token is issued. Same
referent as `Individual`; "holder" is the term used in user-facing
contexts.

**Individual** — see `Individual` table. The natural person.

**Issuing agency** — the agency that originally issued the token.
Stored in `IdentityToken.issuing_agency_id`. Distinct from the
actor agency for any subsequent lifecycle event.

**Legal transition** — a state-machine edge between two
`IdentityToken.status` values that the trigger
`enforce_token_state_machine` permits. The legal set is in
`06_triggers.sql`.

**Lifecycle event** — a row in `TokenLifecycleEvent`. Every status
change of a token writes one (auto-emitted by trigger).

**LOST** — a terminal token status indicating the physical token is
unrecoverable. The token is NOT deleted; the row stays with status
LOST forever. The data is not erased.

**Operator** — a person logged into the Polaris web app to perform
identity-management work. Distinct from holder. AppUser.role values:
`admin`, `operator`, `auditor`.

**Predecessor** — for tokens issued via succession (UC-7), the prior
token whose role this one replaces. `IdentityToken.predecessor_token_id`
references the prior. The prior token stays in the database with its
terminal status.

**RESERVE** — a non-active token status. The legal first state of a
newly-issued token (before activation). Multiple RESERVE tokens per
individual are permitted (the partial unique index only fires on
ACTIVE).

**Succession** — UC-7. Issuing a new token as a successor to a
previous one. The previous token stays in the database with its
terminal status; the new token references it via
`predecessor_token_id`.

**Token (full: identity token)** — see `IdentityToken` table. The
core state-bearing object.

**Token value** — the canonical token serial. `IdentityToken.token_value`,
UNIQUE.

**UC-N** — Use Case N. Defined in the original SCS-230 report.
UC-1 (Issue), UC-3 (Bind device), UC-4 (Revoke), UC-5 (Report lost),
UC-6 (Lookup), UC-7 (Succession), UC-8 (Multi-sig migration),
UC-9 (Recovery), UC-10 (Federation), UC-11 (ZK epoch),
UC-12 (Duress).

**Verification context** — see Context.

**Verification event** — a row in `VerificationEvent`. Recorded
every time a token is verified.

---

## Cryptographic primitives

**Anchor batch** — an `AnchorBatch` row, the per-batch Merkle
commitment of one or more `BlockchainAnchor` leaves of the same
signature algorithm. Added v8.21 / R10-2 / M2-2. The 5th
audit-of-record instance; append-only via
`trg_anchor_batch_append_only`. See `DEVNOTES/ships/anchoring.md`.

**Attestation** — in Polaris context: a row in
`AgencyTrustAttestation` recording that agency V accepts agency I's
tokens for context C until date D. Federation primitive, R11-3 / M2-8
/ v8.22. Append-only with one-way revocation. See
`DEVNOTES/ships/federation.md`.

**DID anchoring** — the practice of writing a per-token DID +
commitment hash to an external verifiable record. Polaris records
the per-token side in `BlockchainAnchor` (v1+) and the
batch-commitment side in `AnchorBatch` (v8.21 / R10-2 / M2-2). The
external-ledger leg is operator-discretion: `committed_to_chain` /
`external_chain` / `external_chain_tx` are ready to be filled but
not auto-derived.

**Duress code** — a secondary credential the holder types under
coercion (PDF §9.5; R11-5 / M2-10 / v8.24). On match, the system
silently records a `DuressEvent` row while the coercer-visible
verification flow proceeds identically (R2 audit refinement —
identical observable behavior). Stored as a Werkzeug scrypt hash in
`IdentityToken.duress_code_hash`; comparison is constant-time via
`check_password_hash`. See `DEVNOTES/ships/duress-codes.md`.

**Epoch (ZK epoch)** — a row in `TokenStateEpoch` (R10-1 / M2-1 /
v8.23). Per-epoch Merkle commitment over the active-token set; the
ZK-SNARK proves membership in the epoch's `merkle_root` bound to
`(epoch_id, context_id, nonce)` public inputs. Append-only after
closure. See `DEVNOTES/ships/zk-snark.md`.

**Federation (issuer federation)** — the cross-agency trust model
implemented in v8.22 (R11-3 / M2-8). A verifying agency declares
which issuing agencies it accepts for which contexts via
`AgencyTrustAttestation` rows. Verification of a token issued by
agency I at a checkpoint operated by agency V succeeds iff V == I OR
an active V→I attestation exists for the relevant context. NO
transitive trust. See `DEVNOTES/ships/federation.md`.

**Merkle tree / Merkle root** — binary hash tree where each non-leaf
node is the hash of its two children. The root is a compact
commitment to the entire leaf set. Polaris uses SHA3-256 by default
(operator-policy choice, see `DEVNOTES/ships/anchoring.md`). Leaves
are ordered by `anchor_id` ascending to defeat the
publish-then-fork attack. A per-leaf inclusion proof is logarithmic
in the leaf count.

**ML-DSA-65** — NIST FIPS 204 lattice-based digital-signature
algorithm. Polaris's default issuing algorithm. Post-quantum
secure under the Module Learning With Errors (MLWE) assumption.

**Multi-sig migration (M:N)** — R11-1 / M2-7 / v8.18. Per-token
support for `M-of-N` signature schemes recorded in `TokenSignature`
rows. A migration replaces the prior signature set with a new one;
the prior set is preserved as inactive rows for audit. The
consistency model is documented in
`DEVNOTES/ships/multi-sig-migration.md`.

**Plonky2** — a FRI-based ZK-SNARK family (Polygon's
`mir-protocol/plonky2`). Chosen for R10-1 / M2-1 (v8.23) because:
(a) no trusted-setup ceremony required (transparent setup, C3
axis); (b) hash-only commitments (Poseidon over Goldilocks field)
align with Polaris's post-quantum mission at the SNARK layer.
Implemented in the in-tree `polaris_zk/` Rust crate. See
`DEVNOTES/ships/zk-snark.md`.

**Post-quantum (PQ)** — cryptographic algorithms believed resistant
to attack by sufficiently large quantum computers. Polaris's
default issuing algorithm is ML-DSA-65 (NIST FIPS 204); the ZK-SNARK
layer is Plonky2 (FRI + hash-only commitments).

**ZK / ZERO_KNOWLEDGE** — disclosure level proving "valid token
exists" without revealing identity. `token_id IS NULL` enforced by
CHECK constraint and trigger. The verification graph cannot be
reconstructed from ZK events alone.

**ZK-SNARK** — Zero-Knowledge Succinct Non-Interactive Argument of
Knowledge. Polaris ships a real ZK-SNARK in v8.23 (R10-1 / M2-1)
using Plonky2 + a hybrid-Merkle circuit (C3+A4+B3 from the M2-1
exploration Sanctum). The prover proves "I hold a token in this
epoch's Merkle root" without revealing which token, bound to
`(epoch_id, context_id, nonce)` public inputs. See
`DEVNOTES/ships/zk-snark.md`.

---

## Schema invariants & enforcement

**Antimeridian** — the 180° meridian (date line). Bboxes that span
this line have `min_lon > max_lon`. Supported as of v7 via
wrap-aware predicates in atlas SQL functions.

**Append-only** — a table whose rows can be inserted but not
modified or deleted. Enforced by trigger
(`reject_audit_modification`). Constraint C1 covers
`TokenLifecycleEvent`, `VerificationEvent`,
`EnrollmentStatusEvent`, and (as of v8.21) `AnchorBatch`.

**Audit-of-record** — a schema element whose own state plus
append-only or bounded-mutation invariants fully reconstructs the
operation it records, without a separate event-log table.
Canonicalized in `DEVNOTES/audit-of-record.md`. **Twelve current
instances** (post v8.20): 9 schema instances —
`TokenLifecycleEvent`, `VerificationEvent`, `EnrollmentStatusEvent`,
`AnchorBatch`, `RecoveryRequest`, `TokenSignature`,
`AgencyTrustAttestation`, `TokenStateEpoch`, `DuressEvent` — and 3
filesystem instances: `sanctum/*.md` strategic-consultation
sessions, `polaris_swarm/civitas/treasury-roll.json` (Arc F denarii
ledger), `polaris_swarm/civitas/census-roll.json` (Arc E civitas
registry).

**CHECK constraint** — a row-level invariant declared in the
schema. Polaris has 41 CHECK constraints across its 25 tables; they
enforce things like "`disclosure_level = 'ZERO_KNOWLEDGE'` implies
`token_id IS NULL`."

**Constraint (Cn)** — one of MISSION.md's 10 hard constraints. C1
through C10. Violation means Polaris is broken regardless of what
tests still pass.

**FK** — foreign key.

**Hard cap** — a maximum result size enforced at the SQL function
level that the API caller cannot exceed. Constraint C8 covers
`/api/atlas/*` endpoints.

**Partial unique index** — a unique index with a WHERE clause.
`uq_one_active_per_person` is `UNIQUE (individual_id) WHERE
status = 'ACTIVE'`. Enforces C3.

---

## Web app & operator concerns

**Atlas** — the operational situational-awareness page. Renders
verifications and lifecycle events on a globe with bbox-scoped
spatial aggregation. Backed by `/api/atlas/*` endpoints.

**Cluster** — in atlas terminology, a spatial bin (grid cell)
aggregating multiple events into one displayable summary. Computed
server-side by `atlas_clusters_*` functions.

**CSP** — Content-Security-Policy header. Polaris uses
`script-src 'self'`. Constraint C5.

**CSRF** — cross-site request forgery. Polaris protects against
this via `@security.csrf_protect` on every state-changing route.

**Cursor pagination** — pagination scheme using a "where am I"
cursor instead of OFFSET. O(log n) per page vs O(offset).
Implemented in `/api/atlas/events`.

**Rate limiter** — R8-2 / v7.5 mechanism guarding login + sensitive
endpoints against brute-force. In-memory backend for single-worker
deployments; Redis backend for multi-worker. Selected automatically
in `security.py`; surfaced in `/api/health.checks.redis`.

**Session fixation** — a session-related attack where an attacker
plants a session ID. Defended via `session.regenerate()` on login
(threat T-S2 in `DEVNOTES/threat-model.md`).

**Stress data** — synthetic 2M-row dataset for performance testing.
Generated by `polaris_sql/_stress_seed.sql`.

**TOCTOU** — time-of-check-to-time-of-use. A race where a check
(read) is followed by a use (write) without an atomic operation
between them. C4 prevents this in `failed_login_count` via
`UPDATE … SET col = col + 1 RETURNING …`.

---

## Production deployment (Arc B)

**Caddy** — the reverse-proxy + TLS-terminator used in production.
Caddy 2 in the `caddy:2-alpine` image. Auto-provisions Let's
Encrypt certificates for the `{$POLARIS_DOMAIN}` site block. Sets
the canonical security-header set (HSTS, X-Frame, X-Content-Type,
Referrer-Policy, Permissions-Policy, Cross-Origin) at the edge.

**Docker secrets** — Docker's file-mounted secret mechanism. In the
production stack, secrets are mounted at `/run/secrets/<name>` from
the host filesystem (`polaris_web/secrets/<name>` mode 0600). The
app reads them via the `*_FILE` env-var convention (G28).
`POLARIS_SECRET_KEY_FILE` and `POLARIS_DB_PASSWORD_FILE` are the
two file-mounted secrets in the prod stack.

**File-mounted secret** — a credential stored on the host
filesystem (mode 0600) and bind-mounted into a container at
`/run/secrets/<name>`. The app reads the secret from the file
instead of from an environment variable. Enforced by G28. The
secret never appears in `docker inspect`, `ps -e`, or container
logs.

**G27 (TLS required)** — Production deployment requires TLS. The
Caddyfile or equivalent reverse-proxy with TLS must be present in
any production-targeted deploy. Enforced by
`test_g27_caddyfile_declares_tls` in
`polaris_web/test_structural_invariants.py`. Added v8.77 / Arc B
Phase 1.

**G28 (no env-secrets in prod)** — Sensitive secrets do not appear
as environment-variable literals in `docker-compose.prod.yml`.
Production uses file-mounted Docker secrets via the `*_FILE`
env-var convention. Enforced by
`test_g28_no_sensitive_env_in_prod_compose`. Added v8.77.

**G29 (structured /api/health)** — The `/api/health` endpoint
returns structured JSON with `status` ∈ {`healthy`, `degraded`,
`unhealthy`}, `version`, `uptime_seconds`, `checks` (database /
redis / zk_binary / disk), and `timestamp`. HTTP 200 on
healthy/degraded; 503 on unhealthy. Enforced by
`test_g29_health_endpoint_contract`. Added v8.77.

**Let's Encrypt** — the certificate authority Caddy uses to
auto-provision TLS certificates via the ACME HTTP-01 challenge.
Renews automatically ~30 days before expiry.

**POLARIS_DOMAIN** — the public DNS name the production stack is
served from. Set as an environment variable before `docker compose
up`; consumed by both the Caddyfile (for TLS issuance) and the app
(for absolute-URL construction). The Caddyfile site block keys on
`{$POLARIS_DOMAIN}`.

**TLS** — Transport Layer Security. The protocol underneath HTTPS.
Polaris's production stack terminates TLS at Caddy; internal
traffic (Caddy → app → Postgres/Redis) is plaintext over the
isolated Docker network. G27 requires TLS for any
production-targeted deploy.

**/api/health** — the structured health endpoint (v8.77 / G29).
Returns overall + per-component status. Consumed by Caddy's
upstream health check, load-balancer probes, and external uptime
monitors. See `docs/operator/OPERATIONS.md` § Monitoring.

**WebAuthn** — the W3C standard for hardware-bound authentication
(security keys, platform authenticators, biometrics). Polaris does
not currently use WebAuthn for operator auth — it's a deferred Arc
B Phase 2 item. The architectural intent is that hardware-token
operator auth replaces the password+session model for
high-privilege roles.

---

## Cognitive substrate

The four-principle structure declared verbatim in MISSION.md.
These are the cognitive layer that every other principle depends
on. Their substitutability is preserved by the v8.30 clause.

**1. Sanctum** — the formal agent-operator strategic consultation
protocol. Each session is a file in `sanctum/<date>-<topic>.md`
with a fixed structure (Matter / Phase scope / Design /
Recommendation / Alternatives / Decision / Outcome). MEDIUM- or
HIGH-risk decisions require a Sanctum. Spec:
`meta/sanctum-protocol.md`. Index: `meta/sanctum-index.md`.

**2. AoR (audit-of-record)** — see "Audit-of-record" above.

**3. Risk class** — see "Risk class" below.

**4. CM (constitutional meta-constraint)** — the immortal 10th
head. Distinct from C1-C10: CM is the meta-constraint that
*evaluates the system against C1-C10*. Implemented as
`scripts/ai-meta.sh`, which runs 6 self-checks on every session
(C-mention coverage, script-vs-doc drift, meta-slot status,
Sanctum integrity, audit-of-record discipline, Tribuni Plebis
state). Self-monitoring is the part of the system that survives if
every other layer fails.

**Architect** — the agent's strategic-advisor persona. Voiced via
`scripts/ai-architect.sh`. Specification: `meta/architect.md`.
Conducts macro scans, surfaces drift, recommends moves. Distinct
from the executor; the same agent may invoke either voice.

---

## HYDRA + Mycelium + Civitas

The three runtime-observation layers of the cognitive substrate.
HYDRA is the synthesis layer; Mycelium is the autonomous-action
layer; Civitas is the political layer.

**HYDRA** — the 9-watcher runtime synthesis layer. Each watcher
observes one constraint domain and reports findings. The canonical
mortal-head count is **Hydra-9**: schema, cognitive, security,
mission, adversary, performance, trajectory, ant_colony, civitas.
**CM is the immortal 10th head.** Voiced via
`scripts/ai-hydra.sh`. Code in `polaris_hydra/`. Read-only by
construction (G3); deterministic (G2).

**Watcher** — a HYDRA component implementing one constraint-domain
observation. Reads runtime state; emits structured findings.
Examples: `SchemaWatcher` (C1-C9 schema invariants),
`SecurityWatcher` (CSP, CSRF, inline JS), `TrajectoryWatcher`
(ship pacing, parking patterns, file churn).

**Mycelium** — the autonomous-action swarm layer. 33 ants across
11 legions (9 Republican + 2 Imperial). Each ant scans one
specific drift surface and lays a pheromone in
`polaris_swarm/pheromones.db` when it finds something. Code in
`polaris_swarm/`. Read-only at the substrate level (G6); ant
findings drive operator attention via the bloom heatmap.

**Ant** — a single autonomous Mycelium scanner. Each ant has a
narrow specialization: one drift surface, one finding shape.
33 ants total as of v8.71. Steady-state ants are exempt from
rewards/penalties (F5 / G26).

**Legion** — a Mycelium grouping of related ants. **9 Republican
legions** (schema, cognitive, security, mission, adversary,
performance, trajectory, substrate, docs) + **2 Imperial legions**
(Praetorian, Engineer; v8.71 / Arc G). Each legion uses one of 5
Roman tactics (TESTUDO, TRIPLEX_ACIES, CUNEUS, VEXILLATIO,
AUXILIA) to coordinate its ants.

**Pheromone** — a structured drift signal laid by an ant. Recorded
in the `pheromones.db` SQLite store with intensity, decay rate,
provenance (which ant deposited it). Read by the bloom-renderer to
produce the operator-facing heatmap. The 11th audit-of-record
candidate; not a schema AoR but a runtime AoR.

**Civitas** — the citizen layer. 6 civilian classes parallel to the
9 Republican legions: Plebs, Equites, Augures, Censores,
Quaestores, Tribuni Plebis. Citizens aggregate ant findings into
higher-level political signals (e.g., Plebs aggregate burst
pheromones into a forum-imbalance signal). Code in
`polaris_swarm/civitas/`.

**Citizen** — a Civitas member. Implementation: each citizen class
is a Python module that consumes ant findings and emits a synthesis
finding. The 6 classes are below.

**Plebs (Plebeians)** — Civitas citizens who aggregate burst-class
ant findings into forum-imbalance signals. The default class.

**Equites (Knights)** — Civitas citizens who pair complementary
finding types (e.g., Mission + Trajectory) into integrated
signals.

**Augur** — Civitas citizen of the auspicious-pattern class.
Detects uncovered namespaces (e.g., proposals/ without ant
coverage) and emits `proposal_new_ant` findings. Closes the
proposal-driven autogenesis loop (G13).

**Censor** — Civitas citizen of the registry class. Maintains the
`census-roll.json` filesystem audit-of-record. Tracks which
ants/citizens are active; surfaces ant churn.

**Quaestor (Treasurer)** — Civitas citizen of the financial class.
Maintains the `treasury-roll.json` denarius ledger. Records
reward/penalty events as Treasury rolls.

**Tribuni Plebis** — Civitas citizen of the watchdog class
(v8.71 / Arc G). The 6th citizen. Monitors the Sanctum protocol
itself for drift, parking patterns, and override-pattern frequency.
Voiced via `polaris_swarm/civitas/tribuni_plebis_watcher.py`.

**Denarius** — the swarm currency. NOT Polaris currency (C10 /
pomerium preserved). Earned by ants whose pheromones lead to drift
resolution; lost by ants whose pheromones decay unread.
Implementation: `polaris_swarm/civitas/treasury.py`. Ledger:
`treasury-roll.json` (the 3rd filesystem AoR; Arc F / v8.68).

**Treasury** — the denarius accounting layer. Two-form: in-memory
state in `treasury.py` + persisted ledger in `treasury-roll.json`.
Every reward/penalty event is recorded in both forms; reload
reconstructs from the ledger.

**Census** — the citizen-registry layer. `census-roll.json` is the
4th filesystem AoR (Arc E / v8.66). Records each citizen's
activation events.

**Cursus Honorum** — Roman class advancement system applied to
ants. Three classes: Plebs (0-100 denarii, 1.0× multiplier), Eques
(101-10,000 denarii, 1.5× multiplier), Patrician (10,001+ denarii,
2.0× multiplier; Sanctum-chair eligible). Implemented in
`treasury.py` (F4 / v8.70). G19 monotonic; G20 strict-Civitas
(eligibility derives only from balance, never Polaris identity).

**Hydra-9** — the canonical 9-watcher count for the HYDRA
synthesis layer. Established v8.72 by relocating the Hydra
mythology from Mycelium legions (where it was a v8.65-era
miscount) to HYDRA watchers (the etymological home). CM remains
the immortal 10th head.

**CM** — the constitutional meta-constraint. See [Cognitive
substrate](#cognitive-substrate) above.

**G-guards** — the lattice of structural enforcement guards
preventing drift. G1-G29 as of v8.77. Each guard names one
invariant that the test suite mechanically enforces. Examples: G3
(watchers must be read-only), G13 (proposal-driven autogenesis),
G26 (STEADY_STATE_ANTS allowlist requires Sanctum), G27 (TLS in
prod), G28 (no env-secrets in prod), G29 (structured /api/health).

---

## Arcs & versions

Arcs are strategic-thematic groupings of related ships. They open
via Sanctum, accumulate ships across many versions, and close when
their done-list is complete. Each arc has its own
`meta/arc-<letter>-*.md` strategic record.

**Arc A** — open-problems arc (v2 / v11). The 5 cryptographic
primitives M2-1..M2-12. Closed at 12/12 ✅ on 2026-05-12.

**Arc B** — production-deployment arc (opened 2026-05-14). Phase 1
shipped as v8.77 (10 deliverables: OPERATIONS.md, SECRETS.md,
Dockerfile.prod, docker-compose.prod.yml, Caddyfile, structured
/api/health, deploy script, backup script, generate/rotate-secret
scripts, strategic record). G27-G29 introduced. Phase 2
(WebAuthn / archive policy / multi-instance) and Phase 3
(multi-region / DR / SOC 2) deferred. Strategic record:
`meta/arc-b-production.md`.

**Arc C** — the partner-consumer arc (banking ledger, OIDC
integration). Considered for v2 but deferred 2026-05-09. See
`memory/deferred_items.md`.

**Arc D** — HYDRA arc (opened + closed 2026-05-12). 8 ships (H1-H8)
delivered the 9-watcher synthesis layer. Strategic record:
`meta/arc-d-hydra.md`.

**Arc E** — Mycelium arc (opened 2026-05-13; cohort active). 10
ships (E1-E10) delivered the 33-ant swarm + 6-citizen Civitas
layer. Strategic record: `meta/arc-e-mycelium.md`.

**Arc F** — Denarius arc (opened 2026-05-13). 5 ships (F1-F5)
delivered the swarm-currency layer with Cursus Honorum + Sanctum-
chair eligibility. Strategic record: `meta/arc-f-denarius.md`.

**Arc G** — Roman Empire arc (opened 2026-05-13). G1 shipped the
2 Imperial legions + Tribuni Plebis + Via Appia priority. G21-G25
introduced. Strategic record: `meta/arc-g-empire.md`.

**Arc H** — analytical-layer arc (parked). The
swarm-as-analytical-layer for tokens/verification data. Parked per
VANTA directive 2026-05-13: "not now because it's not ready but
we want to actively work and get it ready."

---

## Governance & meta

**Bounded autonomy** — the framework defined in
`meta/autonomy-architecture.md`. The agent acts autonomously on
LOW-risk roadmap items and proposes-and-waits for MEDIUM/HIGH
risk. Heavy-production posture (v8.77) reasserts the bias toward
shipping the complete thing.

**DEFERRED** — a threat in `DEVNOTES/threat-model.md` whose
mitigation is acknowledged but not yet implemented. Distinct from
ACCEPTED (a threat the system explicitly tolerates).

**Done-list** — the checklist in MISSION.md that defines what
"done" means for Polaris. The agent's reward function. v1 closed
2026-05-09; v2 closed 2026-05-12 at 12/12 ✅. Arc-specific
done-lists live in `meta/arc-<letter>-*.md`.

**Empirical-iteration cycle** — the pattern observation → finding
→ fix → audit-of-record. Codified in `meta/architect.md`.
Examples: v8.72 → 100yr-sim → F5; v8.75 macro-scan → v8.76
parser fix.

**Episodic memory** — in the cognitive layer, the journal entries
in `journal/YYYY-MM-DD.md`. Captures what happened in each
session.

**Forward priming** — reading the relevant DEVNOTES, patterns,
and journal entries BEFORE editing a file. Done via
`scripts/ai-where.sh FILE`. Brain analog: walking into the
kitchen reminds you that you wanted water.

**Heavy-production posture** — the operating mode adopted via
`sanctum/2026-05-14-steady-state-revocation-heavy-production.md`.
Replaces the v8.31 post-v2 steady-state decline-and-surface
default with an active-production "ship the complete thing"
default. The four cognitive-substrate principles, C1-C10, and
G1-G26 are preserved verbatim; only the default response shape
changes.

**Larping** — a recurring failure mode VANTA flagged early on:
substituting feelings of significance for actual output. Tracked
in `DEVNOTES/style.md`. The cognitive layer has standing
instructions to name this pattern when it appears.

**Mission** — the constitution defined in `MISSION.md`. What
Polaris is, what it isn't, and the 10 hard constraints. The agent
re-grounds against this at the start of every session.

**Override pattern** — a pattern (#14: Workaround Risk; recorded
in `DEVNOTES/style.md`) describing how a quick fix can mask the
need for a real fix. The Sanctum protocol's "alternatives" section
exists partly to force naming of overrides before they become the
fix.

**Parking-vs-deciding** — the discipline of distinguishing
"deferred to a named future trigger" (parking) from "decided not
to do" (rejection). Parked items live in
`memory/deferred_items.md`; rejected items live in
`meta/rejected.md` (if/when populated).

**Pattern** — a recurring cognitive shape recorded in
`DEVNOTES/style.md`. Examples: #14 Workaround Risk, #19 Clarity,
#21 Closure, #23 Empirical Iteration.

**Procedural memory** — in the cognitive layer, the recipes in
`patterns/*.md` and the executable scripts in `scripts/ai-*.sh`.
Captures how to do recurring tasks.

**Reflex / reflection** — the consolidation step where in-session
journal learnings are promoted to durable DEVNOTES or patterns.
Triggered by `scripts/ai-reflect.sh`.

**Risk class** — see `meta/autonomy-architecture.md`. LOW
(autonomous-eligible), MEDIUM (propose-and-wait, often Sanctum),
HIGH (explicit human approval, always Sanctum).

**Roadmap** — the prioritized list of next-version items in
`ROADMAP.md`. Items reference mission, risk class, effort, and
acceptance.

**Self-improving loop** — the cycle: status → propose → execute
→ journal → reflect. Each iteration advances the mission and
refines the cognitive layer. Documented in
`meta/cognitive-loop.md`.

**Semantic memory** — in the cognitive layer, the DEVNOTES files
(`concurrency.md`, `atlas-scaling.md`, `known-gotchas.md`,
`style.md`, `threat-model.md`). Captures stable facts about the
system.

**Steady-state contract (v8.31)** — the post-v2 default posture
adopted 2026-05-12 (Sanctum
`sanctum/2026-05-12-post-v2-steady-state-declaration.md`).
Decline-and-surface for ambiguous expansion. **Revoked 2026-05-14**
in favor of heavy-production posture; the constitutional core was
preserved.

**STRIDE** — Microsoft's threat-modeling framework: Spoofing,
Tampering, Repudiation, Information Disclosure, Denial of service,
Elevation of privilege. `DEVNOTES/threat-model.md` enumerates
Polaris's threats by STRIDE category.

**Tribuni Plebis monitoring** — the Sanctum-protocol watchdog
mechanism described in `meta/sanctum-protocol.md`. The Tribuni
Plebis citizen fires on burst-Sanctum patterns, stale-OPEN
Sanctums, and override-pattern frequency.

---

## Etymology

**Polaris** — the project. Named for the celestial pole star —
fixed reference point in the night sky. Constitutional in spirit
(the constants), navigational in function (operator orients
against it), unchanging from the holder's perspective.
