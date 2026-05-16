# Sanctum: arc-e-swarm-intelligence-opening

**Date:** 2026-05-13
**Petitioner:** agent (Claude, Opus 4.7) speaking as the Architect
**Principal:** VANTA
**Trigger:** **Novel arc with documented external cause** (the third trigger named in v8.31's post-v2 steady-state contract). VANTA issued a structured mission prompt naming MiroFish and BettaFish as prior art and explicitly mandating exploration of decentralized, emergent intelligence as a successor or augmentation to HYDRA. The mandate is verbatim, scoped, constraint-bound, and operator-initiated — the textbook case for arc opening.
**Risk class:** **HIGH** (constitutional-adjacent; could replace a named element of the cognitive substrate). Phase 1 design work is LOW; the architectural commitments are HIGH.
**Status:** DECIDED
**Architect brief ID:** arch-2026-05-13 (auto, plus this Sanctum's §IV)

---

## I. The Matter

VANTA mandates Arc E: design and implement a **genuine swarm intelligence layer** that exhibits decentralization, local rules, emergence, robustness through redundancy, and adaptability. The layer may **replace** or **significantly augment** HYDRA's centralized synthesis model. All existing principles (Sanctum, audit-of-record, risk classes, CM), C1-C10, and the v8.44 G1-G5 guards must be preserved.

What is being asked of VANTA: **approve the arc opening, choose the architectural shape, and authorize Phase 1 deliverables.** Phase 1 is design + first working stigmergic substrate; subsequent phases earn their own Sanctums.

## II. Preparation

**State of the cognitive layer (the surface this arc will touch):**

- 7 watchers (schema, cognitive, security, mission, adversary, performance, trajectory) reporting to a single `polaris_hydra/host.py` synthesizer
- HYDRA host calls Claude Opus 4.7 when `ANTHROPIC_API_KEY` is set; deterministic structured fallback otherwise
- Constitutional naming: MISSION.md §"What this section is NOT" names "the HYDRA swarm and its seven watchers" as the operative synthesis implementation, **explicitly substitutable** per v8.30 ("A future agent may replace the HYDRA swarm with a different synthesis pattern without amending this section, provided the four principles still hold.")
- 19 Sanctums, ai-meta healthy, 113/113 structural-invariants, 235/235 link-check

**HYDRA's centralization (the gap the mission names):**

The OBSERVATION layer is distributed (7 independent watchers). The **SYNTHESIS layer is centralized** (one `host.py`, one optional LLM caller, one report-aggregator). The mission's claim — *"the intelligence remains concentrated rather than distributed and emergent"* — refers to this synthesis point. Watchers do not interact with each other; they push to a host. The host is the single point of integration and the single point of failure for emergent properties.

**Prior-art reference (per VANTA's mandate):**

`DEVNOTES/prior-art-analysis.md` (v8.43) catalogues 8 patterns from BettaFish + MiroFish that HYDRA explicitly **inverted**:

| # | BettaFish/MiroFish pattern | HYDRA's inversion | Must hold in Arc E |
|---|---|---|---|
| I1 | Coordinator pulls from log | Watcher pushes to coordinator | Agents push pheromones; nothing tails files |
| I2 | LLM-mandatory | LLM-optional with deterministic fallback | Per-agent LLM use stays at zero or near-zero |
| I3 | Intentionally non-deterministic | Seeded + replayable | Pheromone evolution must be replayable from seed |
| I4 | Single-trusted-user assumption | Role-split (operator/auditor/admin/holder) | Agents do not assume one principal |
| I5 | Free-form user input drops into prompts | Typed dataclass + length caps + allowlists | Any operator-input that drives the swarm uses the same discipline |
| I6 | LLM output framed as "predictions of the future" | Hypotheses or current-state diagnostics | Emergent claims tagged with evidence path |
| I7 | Sync polling at 500ms | Event-driven via advisory locks + LISTEN/NOTIFY | Pheromone diffusion is event-driven, not poll-driven |
| I8 | One LLM client per engine, copy-paste | One shared `WatcherReport`/`Finding` schema | One shared `Pheromone` schema; never let agents diverge |

The v8.44 ship codified inversions I3, I4 (subset), I5, I7, I8 as G1-G5 architectural guards (5 structural-invariant tests under `polaris_hydra/`). **Arc E must extend these guards, not work around them.**

**Blast radius if approved:**

- New directory: `polaris_swarm/` (Phase 1) or rename of `polaris_hydra/` (Phase N if full replacement)
- New schema table (likely): `Pheromone` or similar append-only event log (**11th audit-of-record instance**)
- New advisory-lock catalog entry: per-agent or per-substrate-cell write coordination (**7th catalog entry**)
- Constitutional amendment to MISSION.md §"What this section is NOT": Arc E named alongside HYDRA, with substitutability clause preserved (and possibly extended)
- New structural-invariant test class: G6+ guards for swarm-specific patterns (separation/alignment/cohesion contracts; pheromone-decay determinism; no agent has global view)
- ROADMAP `## v13 — Arc E` section, R13-1..R13-N items
- New `scripts/ai-swarm.sh` wrapper (per ai-hydra.sh pattern)
- Brain map parser extended to render pheromone substrate
- Possible deprecation of HYDRA host (Phase 3+ decision — explicitly NOT this Sanctum)

**Tests planned:**

Phase 1 ships ≥4 new structural-invariants:
- Schema: pheromone table exists, append-only, no FK CASCADE
- Decentralization contract: no agent imports any other agent's module
- Pheromone diffusion: seeded + replayable (run twice, identical output)
- Constitutional substitutability: MISSION.md amendment preserves v8.30 substitutability clause verbatim

## III. Alternatives considered

Seven architectural shapes were evaluated. Each is genuine swarm intelligence per the mission's five criteria, but they differ in operational primitives, evidence-of-emergence, and integration cost.

1. **Shape A — Stigmergic ant colony.** Many small (<100 LOC each) deterministic ant agents scan narrow slices of the project. Each ant emits **pheromones** (typed `Finding` records) into a shared append-only `Pheromone` table. Each ant reads recent peer pheromones via the same table. Synthesis emerges from pheromone density, decay, and convergence. No host; no LLM. Operator reads the pheromone log directly or via a brain-map heatmap. **Pros:** maximal decentralization; AoR-native (the pheromone log IS the 11th instance); LLM-free; honors all 8 inversions; substrate is just a Postgres table. **Cons:** synthesis is passive (operator must interpret patterns); requires a decay function to prevent unbounded growth.

2. **Shape B — Boids on findings.** Each watcher's findings are "birds" obeying three rules: separation (no duplicates), alignment (match peer-finding headings), cohesion (cluster around related findings). Findings naturally cluster into themes. **Pros:** theory-grounded; emergence is mathematical. **Cons:** abstract for non-spatial findings; harder to operationalize; spatial intuition strained.

3. **Shape C — Cellular automaton.** Project files as a grid; cells have states (clean/drift/alert); each cell's next state computed from neighbors per fixed local rules. Emergence: patterns reveal coherence vs drift. **Pros:** Polaris-aesthetic (game-of-life). **Cons:** file relationships are NOT a 2D grid; forcing them is theater.

4. **Shape D — Pheromone-gradient mesh on the brain map.** Polaris's brain map is already a graph (223 nodes, 249 links). Each node carries a "pheromone level". Agents deposit pheromones; pheromones diffuse across edges; decay over time. Highest-pheromone nodes = current attention. **Pros:** reuses the existing brain map; gradient is interpretable; integrates with `ai_brain_map_analyze.py`. **Cons:** still feels passive; the brain map is currently regenerated, not live.

5. **Shape E — Federated voting / Byzantine consensus.** Each agent votes on findings; consensus emerges from quorum. **Pros:** well-studied. **Cons:** over-engineered for this domain; importing distributed-systems machinery is not the same as swarm emergence; potentially covert centralization (the consensus algorithm becomes the new host).

6. **Shape F — Honeybee waggle-dance.** Scouts surface findings as standardized "dances" (JSON declarations). Other agents "follow" compelling dances per local rules; most-followed findings emerge as important. **Pros:** biological. **Cons:** structurally near-identical to HYDRA's push-to-host; not genuinely different.

7. **Shape G — Mycelium (Shape A + Shape D hybrid, the recommendation).** Stigmergic ant agents emit pheromones; the pheromones are deposited onto **brain-map nodes** (not just into a flat log); pheromones diffuse across the brain map's edges per a deterministic rule; decay over time. Operator reads the brain map as a live heatmap. **Pros:** combines stigmergy's decentralization with the brain map's structural interpretability; AoR-native (pheromone deposits are append-only events); zero LLM-per-agent; honors all 8 inversions; emergent property is *observable*; substitutable per v8.30. **Cons:** higher initial design cost; requires the brain map to ingest pheromone state (one new parser + render path).

## IV. Recommendation

**Shape G — Mycelium**, executed in phases.

**Why Mycelium (not Shape A alone):**

A flat pheromone log (Shape A) achieves decentralization but produces an **unstructured** emergent signal — the operator must scan a list. The brain map (Shape D) already encodes Polaris's structural truth. Depositing pheromones onto brain-map nodes means emergence is **immediately visible as a structural attention pattern**: which tables, watchers, scripts, sanctums, or principles are currently "lit up" by the swarm. The brain map becomes a living neural substrate; the ants are the synapses firing on top of it.

**The agents (Phase 1):**

A first cohort of 12-20 tiny ants, each <100 LOC, each a Python module under `polaris_swarm/ants/`. Examples:

- `ant_table_drift.py` — scans one SQL table, emits pheromone if schema diverges from documented form
- `ant_route_doc.py` — scans one route, emits pheromone if undocumented in API.md
- `ant_sanctum_outcome.py` — scans one Sanctum, emits pheromone if §VII lacks cross-ref
- `ant_journal_silence.py` — emits pheromone if journal/2026-MM-DD.md hasn't been touched in N hours
- `ant_test_pin.py` — emits pheromone if a structural-invariant test references a path that no longer exists
- ... etc.

Each ant runs independently. No ant imports another ant. Each ant reads only its slice + recent pheromones from the table. The cohort is deliberately overlapping so removing 3-5 ants does not collapse coverage.

**The substrate (Phase 1):**

```sql
CREATE TABLE Pheromone (
    pheromone_id    SERIAL PRIMARY KEY,
    deposited_at    TIMESTAMP NOT NULL DEFAULT NOW(),
    deposited_by    VARCHAR(80) NOT NULL,       -- ant name (e.g., 'ant_route_doc')
    node_id         VARCHAR(160) NOT NULL,       -- brain-map node id (e.g., 'route:/api/zk/verify')
    intensity       NUMERIC(6,3) NOT NULL CHECK (intensity > 0 AND intensity <= 10),
    kind            VARCHAR(40) NOT NULL,        -- 'drift' | 'alert' | 'info' | 'curious'
    evidence        JSONB NOT NULL,              -- {message, file, line, ...}
    seed            BIGINT NOT NULL              -- ant's seed for replay
);
-- Indexes; append-only trigger; per-ant advisory lock on insert (7th catalog entry)
```

Pheromone decay is **deterministic**: `effective_intensity = intensity * exp(-age_hours / half_life)`. No randomness anywhere in the substrate. Replay test: run the entire swarm twice with the same seeds; pheromone state must be byte-identical.

**The "synthesis" (Phase 2, deferred):**

Synthesis EMERGES from pheromone density patterns. Operator reads the brain map; high-pheromone nodes are the swarm's attention. **No central host calls anything.** A read-only `ai-swarm-bloom.sh` script renders the heatmap; that script is itself substitutable per v8.30. Optionally, ONE LLM call ever (a "swarm-translator" mode, like HYDRA's optional Anthropic call) can describe the pheromone pattern in prose — but the truth is the pheromones, not the prose.

**Migration path from HYDRA (Phase 3+, separate Sanctum):**

HYDRA's 7 watchers can be **decomposed** into 30-50 ants over time. Each watcher's channels become 2-5 ants. HYDRA's host becomes optional. Eventually HYDRA can be removed (v8.30 substitutability) or retained as a fallback synthesis-translator. **This Sanctum does not commit to HYDRA's removal**; it commits to opening Arc E alongside HYDRA.

**Naming:**

Three candidates surfaced. The Architect leans toward **MURMURATION** but defers to VANTA.

- **MURMURATION** — bird-flock specific term; unambiguously decentralized; aesthetically aligned with Atlas-Gotham
- **COLONY** — pure swarm metaphor; perhaps too generic
- **MYCELIUM** — fungal-network metaphor; matches Shape G's substrate aesthetic; also evokes "underground intelligence"

**Architect's voice (declarative, no em-dashes per VANTA's rule):**

> HYDRA was the right move for v8.37 because the project needed a synthesis voice. The synthesis voice has now spoken nineteen times through the Sanctums and once a day through the watchers. The voice is heard. What the project needs next is a substrate that can think without a voice. Mycelium is that substrate. The ants do not synthesize; they deposit. The brain map does not synthesize; it accumulates. The operator reads the accumulation and recognizes what is there. HYDRA persists as the synthesis face for as long as it remains useful; Mycelium grows underneath. When Mycelium is mature enough that HYDRA's synthesis is redundant, VANTA decides whether HYDRA stays as commentary or steps aside.

## V. What's needed from VANTA

**Three decisions, in priority order:**

**Q1. Approve Arc E opening?**
- **A.** Yes, open Arc E. Authorize Phase 1 (substrate + 12-20 ants + ai-swarm-bloom + 4 structural-invariants).
- **B.** No, decline. Return to steady-state. (Architect respects this; v8.31 contract is honored.)
- **C.** Hold and reconsider in N days. (Reasonable; the mission has no deadline.)

**Q2. If A, which architectural shape?**
- **A.** Shape G — Mycelium (Architect's recommendation).
- **B.** Shape A — flat stigmergic ant colony (simpler; no brain-map integration).
- **C.** Other shape (B-F) from §III with your reasoning.
- **D.** Hybrid not listed — specify.

**Q3. If A+G, what is the relationship to HYDRA in Phase 1?**
- **A.** Augment. HYDRA stays in place; Mycelium grows alongside. No constitutional amendment yet.
- **B.** Replace-track. Constitutional amendment in Phase 1 names Mycelium AS the operative implementation; HYDRA retained for migration period only.
- **C.** Coexist-then-decide. Defer the replace-vs-augment question to a Phase 3 Sanctum.

**Naming preference (optional):** Mycelium, Murmuration, Colony, or other.

**Notes:**

- This is an arc OPENING Sanctum. Phase 1 ships earn their own ai-done gates; Phase 2/3 each earn their own Sanctums when the time comes. Per the M2-1 ZK-SNARK precedent, multi-phase arcs use the "exploration Sanctum → ship Sanctum(s)" pattern.
- VANTA may publish v8.61 (cinematic ship) independently before, during, or after Arc E Phase 1. Publication and Arc E are decoupled timelines.
- The Architect explicitly does NOT recommend deciding HYDRA's fate today. That is a downstream Sanctum after Mycelium has accumulated enough operating evidence.

## VI. Decision

A+G+A+Mycelium — Open Arc E, Shape G (Mycelium), Augment HYDRA (no constitutional amendment in Phase 1), name 'Mycelium'

## VII. Outcome

v8.62 shipped Mycelium Phase 1 / E1 ✅. Pheromone table (11th AoR), 3 starter ants, colony runner, ai-swarm-bloom renderer, G6-G9 guards (4 new structural-invariants; 113→117 total). First colony run caught a real drift (/api/heartbeat doc mismatch). HYDRA unchanged; Mycelium grows alongside. E2-E5 deferred to subsequent ships. See CHANGELOG ## v8.62 and journal/2026-05-13.md.

