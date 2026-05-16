# Proposal: Swarm as Analytical Layer for Polaris Core

**Date opened:** 2026-05-13
**Status:** PARKED (BACKLOG; future-arc candidate; pre-conditions not yet met)
**Originator:** VANTA in-chat strategic vision
**Architect synthesis:** Claude Opus 4.7 speaking as the Architect
**Risk class (if/when activated):** HIGH (introduces analytical reads against IDENTITY-LAYER data; touches the C10 pomerium structurally)
**Not an arc yet.** This proposal exists so the vision is captured in audit-of-record form; when pre-conditions are met (see §V), a Sanctum can open the arc.

---

## Origin — VANTA's vision (preserved verbatim)

> The swarm (Mycelium ants + HYDRA) was originally built as a
> maintenance and integrity layer for the project itself. But it
> has real potential to evolve into an intelligence and analysis
> layer for the actual tokens and verification data that Polaris
> produces.

VANTA proposed five tracks of analytical capability:

1. **Anomaly & Fraud Detection.** Live token-behavior monitoring;
   unusual verification patterns; replay/cloning attempts;
   context-misuse signals; rate-limit-abuse / disclosure-level
   violations.
2. **Privacy-Preserving Usage Analytics.** Aggregate behavior
   without compromising individual privacy; context-usage
   distributions; token-lifespan curves; disclosure-level
   frequencies; jurisdictional patterns.
3. **Behavioral Drift Detection.** Gradual shifts in usage;
   emerging attack patterns; verifier-behavior changes; gaming
   signals.
4. **Self-Improving System (the meta use case).** Suggest better
   context scopes; identify best-performing cryptographic
   algorithms; tune revocation policies; propose new ant types
   based on emerging patterns; help tune the Denarius reward
   function.
5. **Adversarial Simulation & Red Teaming.** Continuous
   game-theoretic simulation against anonymized data; second-best
   attack discovery.

VANTA's architectural distinction:

> **Polaris Core** — The identity token system (tokens,
> verifications, audit logs)
> **Polaris Swarm** — An intelligent analysis and monitoring
> layer that watches the data Polaris produces, detects problems
> and opportunities, helps the system evolve intelligently, and
> maintains the philosophical integrity of the project at
> runtime.

## I. Architect's reading — what else the system would need

VANTA's five tracks are well-formed. The Architect's analytical
addition: **twelve more capabilities** the substrate would need
to make the analytical-layer vision real, organized by surface.

### Detection / Analytics surface (extending VANTA's 1-3)

**6. Cross-domain correlation.** Different identity contexts
(healthcare, banking, government, federation) generate different
verification patterns. A swarm could correlate across domains to
find: identity fraud spanning multiple contexts, coordinated
attacks that look benign in isolation, cross-jurisdictional
organized misuse.

**7. Operator behavior monitoring.** Polaris has operators
(humans) running agencies, issuing tokens, ratifying recovery
ceremonies. The analytical swarm could observe: operator
consistency with policy, insider-threat patterns,
operator-fatigue affecting issuance quality. This is
trust-but-verify applied to the trust layer.

**8. Temporal / seasonal analysis.** Identity systems have
rhythms — tax-season patterns, holiday anomalies,
time-of-day distributions. Forecasting these helps both capacity
planning AND fraud detection (an anomaly during expected
high-traffic looks different from the same anomaly during
low-traffic).

**9. Cohort analytics for trust scoring.** Without identifying
individuals: score COHORTS on aggregate trust metrics; identify
which agencies issue tokens with longest lifespans / lowest
fraud rates; surface accreditation signals for the federation
layer (R11-3) without breaking privacy.

### Policy / System surface (extending VANTA's 4)

**10. Regression detection in policy enforcement.** When Polaris
ships a new revocation policy or attestation rule, the swarm
could verify the policy has the intended effect, surface
unintended consequences, compare actual outcomes against
predicted outcomes from the design Sanctum. **This closes the
ai-architect.sh --reflect loop at the policy level** — same
prediction-vs-reality pattern the cognitive layer already uses
for its own ships.

**11. Cryptographic algorithm performance monitoring.** Polaris
supports multiple cryptographic algorithms (ed25519, BLAKE3,
Plonky2 for ZK-SNARKs). The swarm could detect which algorithms
are slow in practice, surface signature-verification latency
anomalies, identify algorithm-specific failure modes. Feeds back
into M2-6 (multi-sig migration) decisions.

**12. ZK proof health monitoring.** ZERO_KNOWLEDGE verifications
produce proofs. The swarm could verify proof-generation times
are stable, detect proof-verification failures (which could
indicate tampering or implementation drift), surface circuit
complexity drift as the system grows.

**13. Federated trust graph health.** R11-3 federation
introduces trust attestations between agencies. The analytical
swarm could monitor trust-graph topology, detect emerging trust
monopolies (one agency becoming a critical node), surface
federation drift (attestations going stale, agencies
de-federating).

**14. Recovery ceremony stress monitoring.** R11-2
catastrophic-loss recovery has a multi-phase ceremony. The
swarm could detect recovery-request bursts (mass-loss event,
fraud campaign), identify ceremony-completion friction, surface
jurisdictions with high recovery rates (might indicate systemic
problem).

### Self-improvement surface (extending VANTA's 4)

**15. Sanctum-protocol echoes from real data.** When an agency
starts behaving anomalously OR a policy regression is detected,
the analytical swarm could AUTO-OPEN a Sanctum for human review.
This makes the Sanctum protocol *responsive to real-world data*,
not just to agent reflection. The swarm becomes an automated
petitioner.

**16. Cross-layer learning between Mycelium and HYDRA.** The
9 HYDRA watchers (post-v8.72) observe substrate state; Mycelium
observes project artifacts; the analytical swarm would observe
real token data. If HYDRA's CivitasWatcher detects something at
the substrate level that corresponds to an anomaly in token
verification patterns, the **cross-correlation IS the insight.**
This is the v8.30 substitutability clause working in three
dimensions.

### Operator-experience surface (extending VANTA's vision)

**17. Operator-friction analytics applied to Polaris operators.**
Tribuni Plebis (v8.71) watches the cognitive layer's usability
surface. The same pattern could be applied to Polaris operators:
are they running into friction with the UI, the policies, the
federation handshakes, the recovery ceremony? This generates
real product-improvement signals from real operational pain.

## II. Constitutional implications — the pomerium question

The single most important architectural decision in this proposal:
**does the swarm crossing into IDENTITY-LAYER data expand the
pomerium, and if so, how?**

Currently (post-v8.72):

- **C10 (the pomerium):** identity ≠ money. The Denarius is
  SWARM currency only; it never crosses into Polaris identity.
- **G15-G20 + G26:** treasury is FS-AoR; reward function is
  deterministic; multipliers are monotonic; Sanctum-chair
  eligibility derives only from denarii balance; allowlist
  changes require Sanctum.
- **The swarm reads project metadata** (file mtimes, source
  text, structural-constants, Sanctum files, etc.) — NOT
  identity-layer data (`Individual`, `IdentityToken`,
  `VerificationEvent`, `TokenLifecycleEvent`, `DuressEvent`).
- The CivitasWatcher (v8.72) observes runtime state of
  CITIZEN findings, not real identity transactions.

This proposal **fundamentally changes that boundary.** An
analytical swarm reads `VerificationEvent`. That's
identity-layer access. **The pomerium must move.**

The Architect's structural read: this is the kind of expansion
that needs its own constitutional Sanctum BEFORE any code
ships. Three options for handling C10 at activation time:

- **C10 stays verbatim; new C11 introduced** explicitly
  authorizing analytical reads with privacy preconditions
  (k-anonymity, differential privacy, ZK aggregation). This
  is the cleanest move: C10's existing claim ("identity ≠
  money") is structurally narrow; a parallel C11 handles
  "identity ≠ analytics" with its own enforcement mechanism.
- **C10 expands to read-with-privacy.** The existing constraint
  is reinterpreted to allow analytical reads as long as they
  don't reveal individual identity. Requires careful re-
  derivation of all existing C10 tests; high refactor cost.
- **New "analytical pomerium" introduced as a sub-boundary.**
  Identity-data reads are allowed only inside a sandbox with
  enforced privacy guarantees; outside that sandbox the
  classical C10 holds. Strong technical surface area; high
  implementation complexity.

The Architect's preference: **Option 1 (new C11).** It's the
move that least disturbs the existing structure.

### New G-guards required (G27+)

If the analytical-layer arc opens, structural guards needed:

- **G-NEW: Analytical swarm reads are LOG-ONLY** — analytical
  ants cannot modify Polaris core data; the swarm side is
  observer, never actor on identity-layer state.
- **G-NEW: Aggregation respects privacy** — analytical
  aggregations must respect privacy floor (k-anonymity ≥ K
  with K Sanctum-set; or differential-privacy ε ≤ epsilon
  Sanctum-set).
- **G-NEW: ZK-protected events stay ZK-protected** — the
  analytical swarm can count `zk_proofs_per_day` but cannot
  peek inside any proof. Enforced by source-scan forbidding
  imports of the ZK prover's witness-side API.
- **G-NEW: Cross-domain correlation requires explicit
  mechanism** — k-anonymity, differential privacy, or
  limited-precision aggregation must be the enforcement;
  free-form cross-domain joins forbidden.
- **G-NEW: Auto-opened Sanctums (per VANTA's track 5 + my
  item 15) require human ratification before any
  consequence ships.** The swarm can OPEN a Sanctum but
  cannot DECIDE it; the agent-operator decision protocol
  preserves human-in-the-loop.

### Four cognitive-substrate principles re-examined

The four principles from v8.30:

1. **Sanctum protocol** — extends. The Sanctum becomes both
   the agent-operator decision venue AND the auto-opened
   alert pipeline from analytical findings. The protocol's
   verbiage may need refinement around "auto-petitioner"
   semantics.
2. **Audit-of-record** — extends naturally. All analytical
   findings become AoR entries; existing FS-AoR / DB-AoR
   pattern carries forward. The challenge is privacy-
   preservation of those AoR entries — aggregates only,
   never identifying individuals.
3. **Risk classes** — entire arc is HIGH-risk by default;
   individual ship items within it earn their own classification
   per the existing v8.31 framework.
4. **CM** — still applies. The meta-constraint extends to:
   "the analytical swarm self-monitors its own privacy
   preservation; if it detects its own aggregations leaking
   identifying signal, it alerts."

## III. Phasing — when each track could ship

The five VANTA tracks + twelve Architect additions divide
naturally into FOUR phases. Each phase requires its own Sanctum
at activation; this proposal sketches the *order*, not the
schedule.

### Phase H1 — Read-only baseline analytics (lowest risk)

- **Track 2** (privacy-preserving aggregates) — count
  verifications per context; count tokens per disclosure
  level; count revocation-vs-recovery distributions. All
  aggregated; no individual identification.
- **Item 8** (temporal / seasonal) — read-only time-series.
- **Item 11** (crypto algorithm performance) — latency
  histograms only, no payload inspection.
- **Item 12** (ZK proof health) — proof-generation timing,
  proof-verification success rate; never inside the proof.

Required: C11 (analytical pomerium) + G-NEW guards above
(read-only, privacy-respecting). No Sanctum-auto-opening yet.

### Phase H2 — Anomaly & drift detection (medium risk)

- **Track 1** (anomaly / fraud) — pattern-recognition over
  the H1 aggregates; rule-set + statistical thresholds.
- **Track 3** (behavioral drift) — long-window drift
  detection over the H1 aggregates.
- **Item 6** (cross-domain correlation) — requires explicit
  privacy mechanism per G-NEW.
- **Item 9** (cohort trust scoring) — aggregate-only.
- **Item 13** (federation trust-graph health) — topology
  reads; agency-level, not individual.
- **Item 14** (recovery stress) — burst detection; rate
  surfaces.

Required: Phase H1 must be operational for ≥30 days; baseline
data must exist before drift detection can be meaningful.

### Phase H3 — Self-improvement loop (high risk)

- **Track 4** (self-improving) — suggestions for context
  scopes, algorithm performance, revocation policy tuning.
- **Item 7** (operator behavior monitoring) — sensitive
  category; requires separate Sanctum.
- **Item 10** (policy regression detection) — closes the
  --reflect loop for shipped policies.
- **Item 15** (auto-opened Sanctums) — agent becomes its own
  petitioner.
- **Item 17** (operator-friction analytics) — Tribuni Plebis
  applied to real operators.

Required: Phase H2 must be operational for ≥90 days; a clean
human-in-the-loop for auto-opened Sanctums must be designed
and tested.

### Phase H4 — Adversarial layer (medium-high risk)

- **Track 5** (adversarial simulation + red-teaming) —
  permanent Colosseum-class testing.
- **Item 16** (cross-layer Mycelium ↔ HYDRA correlation) —
  observability into the swarm's own correlations.

Required: Phase H3 must demonstrate stable auto-Sanctum
ratification before adversarial layer ships.

## IV. Pre-conditions that must be met BEFORE this arc opens

The Architect names these explicitly so future agents reading
this proposal can determine readiness empirically:

1. **Arc B (production deployment) must be opened.** Today
   Polaris has no real users. An analytical layer over an empty
   identity system is academic. Arc B's prod-deploy trigger
   (per v8.31) is a hard pre-condition.

2. **Sustained operational data of ≥3 months.** The analytical
   patterns the swarm would detect require real-world signal
   accumulation. Detection rules tuned on synthetic data are
   fragile.

3. **F5 (steady-state-ants reward exemption, v8.73) must be
   operational for ≥30 days.** Per the F5 100-year simulation:
   we don't yet know if F5 enables Cursus Honorum reachability.
   Adding analytical-layer Cursus Honorum mechanics on top of
   an unproven reward function compounds risk.

4. **R2 (legion split, deferred from v8.73) decided.** If we
   ship analytical-class ants, they would join legions; the
   legion structure should be settled first.

5. **The R11-2 catastrophic-loss recovery ceremony exercised
   in production.** Item 14 (recovery stress monitoring) only
   becomes valuable when there's recovery to monitor.

6. **A privacy-preservation framework decided at C11-Sanctum
   time** — k-anonymity vs differential privacy vs ZK
   aggregation. This is its own arc-opening Sanctum;
   shouldn't be deferred to in-Phase decisions.

7. **External user expectations clarified.** Who is the
   audience for these analytics? Internal Polaris operators
   only? Federated agencies? End users (holders) themselves?
   The audience shapes the privacy floor.

## V. Why this is parked, not pursued

VANTA's directive: *"not now because its not ready."* Architect agrees:

- Pre-conditions 1-7 above are all unmet today (2026-05-13).
- Today already shipped 6 versions; the swarm is in mid-
  digest of its own structural shifts.
- The Cursus Honorum reachability question is open; analytics-
  layer Cursus Honorum mechanics would be triple-stacked on
  unproven foundations.
- Arc G (Roman Empire) opened earlier today; its Phase 2
  remains deferred. Stacking Arc H over Arc G Phase 2 unmet
  is structurally premature.

When Arc B opens (production deployment trigger), this
proposal becomes immediately re-evaluable. The Architect should
open a Sanctum at that point asking: *"with the empirical data
Arc B will generate, is this analytical-layer arc the right
next move?"*

## VI. Cross-references

- `MISSION.md` §"What this section is NOT" — substitutability
  clause; the analytical layer is a CANDIDATE
  implementation, not a constitutional requirement.
- `MISSION.md` §"Post-v2 strategic moment" — v8.31 trigger
  framework; the analytical layer would open under "novel arc
  with documented external cause" once pre-conditions are met.
- `sanctum/2026-05-12-post-v2-steady-state-declaration.md` —
  the steady-state contract; this proposal explicitly does NOT
  break it.
- `sanctum/2026-05-13-arc-f-denarius-opening.md` — the
  Denarius arc; analytical-layer could feed real usage data
  into the reward function (track 4 / item 7 above).
- `sanctum/2026-05-13-civitas-100-year-post-v8-72-report.md` —
  the 100-year simulation methodology; could be re-applied to
  real Polaris token data at H2 time.
- `DEVNOTES/threat-model.md` — privacy-preserving analytics
  must respect the existing STRIDE-informed threat surface.
- `DEVNOTES/audit-of-record.md` — the FS-AoR + DB-AoR pattern
  extends to analytical findings naturally.
- `docs/reference/PRIVACY.md` — the existing privacy posture;
  C11 design must defer to or strengthen this baseline.

## VII. Maintainer note

This proposal is **PARKED**. It is not on the active ROADMAP.
It is on `docs/BACKLOG.md` (under "Mission-adjacent /
speculative") as a pointer to this document.

The proposal is structurally complete enough that, when
pre-conditions are met, a Sanctum could open Arc H with
this document as the architect's brief.

Re-evaluate when:
- Arc B opens
- Or VANTA names a different trigger
- Or six months pass without movement (then the Architect
  reflects on whether this proposal still represents the right
  next move)
