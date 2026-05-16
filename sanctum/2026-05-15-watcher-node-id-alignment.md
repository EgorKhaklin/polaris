# Sanctum: watcher-node-id-alignment

**Date:** 2026-05-15
**Petitioner:** agent (Claude, Opus 4.7) speaking as the Architect
**Principal:** VANTA
**Trigger:** v9.09 multi-agent scan; surfaced as item S1 in
[`meta/polaris-self-roadmap-3-2026-05-15.md`](../meta/polaris-self-roadmap-3-2026-05-15.md).
HYDRA's `--full` has fired CorrelationEngine 6+ times across v9.04
→ v9.08; cross-watcher correlations: 0 every time. The
instrumentation added in v9.09 / C now shows why: watchers emit
disjoint node_ids. The constitutional question is whether to
preserve that disjointness or design shared-node-id surfaces.
**Risk class:** MEDIUM (touches v9.04 design intent for
CorrelationEngine semantics).
**Status:** DECIDED + CLOSED 2026-05-15 — Position B (designed
shared-surface node_ids ADDITIVE) selected per heavy-production
posture (v8.31 §III.6) following VANTA's *"proceed with the
architects recommendation"*. Implemented + drilled live in v9.10.

---

## I. The Matter

v9.04's hybrid intelligence pipeline includes CorrelationEngine: a
post-`Hydra.gather()` pass that finds findings across DIFFERENT
watchers touching the same `node_id` (Strategy 1) or sharing a
colon-prefix domain (Strategy 2). The promise: when 2+ watchers
independently observe the same surface, that's a higher-confidence
signal than either alone.

**The reality:** CorrelationEngine has fired 0 times in 6+ runs.
The v9.09 / C instrumentation makes the cause visible:
- Each watcher's findings emit node_ids in their own naming
  pattern (security uses `infra:logs:tail`, ant_colony uses
  `swarm:cohort` / `swarm:soldier` / `civitas:treasury`,
  cognitive uses `cognitive:sanctum` / `cognitive:hydra_brief`,
  trajectory uses no node_ids today)
- No two watchers ever observe the same node
- Correlation by construction has no input

This is a **design feature**: each watcher is sovereign over its
domain (the v9.04 Sanctum §III.2 was explicit). A watcher claiming
node_ids in another watcher's domain would invade sovereignty.

But the v9.04 Sanctum ALSO promised correlation as the load-bearing
benefit. If correlation never fires, the v9.04 ship has half a
working feature.

**Three possible reconciliations:**

1. **Accept the disjointness as correct.** Document that "0
   correlations" is the steady-state condition; surface it via the
   v9.09 / C instrumentation; declare the CorrelationEngine
   dormant-until-genuinely-overlapping-substrate.

2. **Design shared-node-id surfaces deliberately.** Identify
   2-3 surfaces where multiple watchers genuinely share an
   observable concern (e.g., security AND ant_colony both have
   opinions about swarm health; performance AND ant_colony both
   touch the swarm's cron behavior). Watchers emit BOTH their
   own-domain node_id AND a shared-surface node_id. Strategy 1
   would then fire on the shared surface.

3. **Add a soldier that emits cross-watcher correlation
   directly.** Skip the watcher emission requirement; have a
   dedicated `soldier_cross_watcher_correlator` that watches all
   watchers and synthesizes its own correlations. This makes
   the lens (HYDRA) meta-observe its own watchers via the
   substrate.

## II. The architect's positions

### Position A: Accept disjointness — architect-default

Document "0 correlations" as the expected steady-state when
watchers stay in their lanes. The v9.09 / C instrumentation
already surfaces the cause. CorrelationEngine remains operational
for the rare case where genuine overlap exists (e.g., a single
node_id that genuinely belongs to multiple domains).

**Strengths:**
- Preserves watcher sovereignty (v9.04 §III.2)
- Zero new code; documentation-only
- Honest: "0 correlations" stops being silent ambiguity, becomes
  an explicit "no overlap" signal via instrumentation
- Aligns with v8.20 audit-of-record: each watcher's findings are
  its own; correlation is opportunistic

**Weaknesses:**
- v9.04 ship's correlation feature stays dormant
- Rejects the lens-watching-substrate-cross-cutting promise

### Position B: Designed shared-surfaces — architect-recommended

Identify 2-3 cross-watcher concerns; watchers emit both own-domain
node_ids AND a shared-surface node_id when their finding touches
the shared concern.

**Concrete shared surfaces (proposed):**
- `runtime:swarm` — emitted by ant_colony when commenting on swarm
  health, AND by performance_watcher when noting cron behavior
- `runtime:auth` — emitted by security when noting auth-flow
  behavior, AND by mission when noting AppUser changes
- `runtime:health` — emitted by performance + security when
  noting /api/health surface

The shared-surface node_ids are ADDITIVE; original domain-specific
node_ids stay. CorrelationEngine fires on the shared surfaces.

**Strengths:**
- Activates the v9.04 CorrelationEngine for real
- Watcher sovereignty preserved (each watcher continues emitting
  its own domain node_ids)
- Shared surfaces are explicit + documented (DEVNOTES/hydra-
  pheromone-integration.md gets a new "Shared correlation
  surfaces" section)

**Weaknesses:**
- Touches every shared-concern watcher (~3-5 modules)
- Risks scope-creep: every "interesting" cross-watcher pair
  might attract a shared surface; need a clear inclusion rule

### Position C: Cross-watcher correlator soldier

Add `soldier_cross_watcher_correlator` to the v9.03 soldier tier.
The soldier reads all 9 watchers' recent findings + emits
correlation pheromones directly. The lens meta-observing itself
through the substrate.

**Strengths:**
- Doesn't touch any watcher
- Substrate-driven: emerges from the same Pheromone substrate the
  v9.04 architecture already uses

**Weaknesses:**
- Adds a 9th soldier class (was 8); changes v9.03 cohort count
- The correlator IS the CorrelationEngine, just relocated; risks
  duplication
- Soldier tier is meant to be high-cadence, low-state; correlator
  is low-cadence, high-state — wrong tier

## III. Architect's recommendation

**Position B (designed shared surfaces).** Rationale:

1. **CorrelationEngine is load-bearing v9.04 work.** Position A
   accepts dormancy; that's a regression from v9.04 ship intent.

2. **Watcher sovereignty + shared surfaces are compatible.** The
   shared-surface node_ids are ADDITIVE to existing domain-
   specific node_ids. Watchers don't lose sovereignty; they gain
   a second axis on which their findings can correlate.

3. **The inclusion rule is small.** A shared surface is justified
   only when ≥2 watchers have ALREADY been observed (in 2+ HYDRA
   runs) emitting findings about the same observable concern.
   Empirical inclusion, not speculative.

4. **Position C duplicates the engine.** A soldier-correlator
   replaces the lens-correlator with substrate-correlator; same
   logic, wrong tier.

The architect's caution: this ship is MEDIUM not LOW because it
changes correlation semantics. Today "0 correlations" means "no
overlap"; under Position B "0 correlations" means "no agreement
on shared surfaces". Different signal — operator needs to know.

## IV. Open questions for VANTA

1. **Approve Position B's shared-surface set?** Architect
   proposes: `runtime:swarm`, `runtime:auth`, `runtime:health`.
   Operator may add or veto specific surfaces.

2. **Inclusion rule strictness?** Architect-recommended: ≥2
   watchers must have been observed (in 2+ HYDRA runs) emitting
   findings about a concern before the shared surface is added.
   Operator may loosen or tighten.

3. **Acceptance criterion?** Architect-recommended: at least 1
   correlation fires within 5 HYDRA `--full` runs after
   implementation; instrumentation shows non-zero overlap.

## V. Decision

**Position B (designed shared-surface node_ids ADDITIVE).** VANTA
in-chat 2026-05-15: *"proceed with the architects recommendation"*
— authorizing Position B for both this Sanctum and the v9.09 S2
Sanctum (cognitive-layer-ratio Position C).

Three §IV resolutions per architect-recommended defaults:
- §IV.1 — shared-surface set: `runtime:health` + `runtime:swarm`
  shipped; `runtime:auth` reserved (mission_watcher does not yet
  emit auth-related node_ids; deferred until empirically warranted)
- §IV.2 — inclusion rule: ≥2 watchers must already emit findings
  about the concern before shared surface added (verbatim per
  architect recommendation)
- §IV.3 — acceptance criterion: ≥1 correlation fires within 5
  HYDRA `--full` runs after impl. **Verified live in v9.10
  first run: 1 correlation fired on runtime:health
  (security + performance both observe app-offline)**.

## VI. Outcome

Shipped as v9.10 same surface as decision.

**Records:**
- This file (sanctum/2026-05-15-watcher-node-id-alignment.md;
  Status updated to DECIDED + CLOSED)
- meta/sanctum-index.md entry refreshed
- DEVNOTES/hydra-pheromone-integration.md gains "Shared
  correlation surfaces" section documenting `runtime:health`,
  `runtime:swarm`, `runtime:auth` (RESERVED)
- v9.10 CHANGELOG entry references this Sanctum
- Structural invariants in TestWave10V910 pin the implementation

**Implementation:**
1. `polaris_hydra/correlation.py` — new helper `_all_node_ids_of()`
   returns ALL node_ids per finding (primary + `additional_node_ids`
   list); CorrelationEngine indexes by every node_id
2. `polaris_hydra/watchers/security_watcher.py` — "app not reachable"
   finding gains `additional_node_ids: ["runtime:health"]`
3. `polaris_hydra/watchers/performance_watcher.py` — "app not reachable"
   finding gains `additional_node_ids: ["runtime:health"]`
4. `polaris_hydra/watchers/ant_colony_watcher.py` — "soldier classes
   silent" finding gains `additional_node_ids: ["runtime:swarm"]`
5. `polaris_hydra/watchers/cognitive_watcher.py` — "HYDRA brief-archive
   stale/dead" findings gain `additional_node_ids: ["runtime:swarm"]`

**Live drill verified**: `bash scripts/ai-hydra.sh --full --save`
produces "VI. CROSS-WATCHER CORRELATIONS: [INFO] 2 watchers correlate
on node runtime:health; watchers: performance, security; score: 2.0"
on the very first run.

**Pattern #20 Constitutional Discipline 12th instance** in the
v8.84/v8.87/v8.90/v8.91/v8.94/v8.95/v8.96/v8.97/v9.04/v9.06/v9.07/
v9.08/**v9.10** series.

## VII. Cross-references

- v9.04 sanctum: hydra-revamp-pheromone-integration (the source
  of CorrelationEngine + the §III.2 sovereignty principle)
- v9.06 sanctum: I1 / docs/CONVENTIONS.md (node_id format
  convention)
- v9.09 / C: CorrelationEngine instrumentation (the surfacing)
- meta/polaris-self-roadmap-3-2026-05-15.md item S1 (the deliverable)
