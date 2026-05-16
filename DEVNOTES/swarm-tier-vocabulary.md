# DEVNOTES: swarm-tier-vocabulary

v9.03 / Sanctum [`2026-05-14-hybrid-swarm-mirai-pattern.md`](../sanctum/2026-05-14-hybrid-swarm-mirai-pattern.md).

The Mycelium swarm has TWO tiers. They share infrastructure
(`Pheromone` table, deposit protocol, advisory locks) but have
distinct vocabularies, intensities, lifecycles, and constitutional
relationships. This file is the canonical reference for which tier
a given concept belongs to.

---

## Quick reference

| Concept | Commander tier | Soldier tier |
|---|---|---|
| **Base class** | `polaris_swarm/base.py:Ant` | `polaris_swarm/soldiers/base.py:Soldier` |
| **Output unit** | `AntFinding` | `Observation` |
| **Output method** | `def scan(self) -> list[AntFinding]` | `def observe(self) -> list[Observation]` |
| **Intensity range** | `[3.0, 7.0]` | `[0.5, 2.0]` |
| **Default half-life** | 24h | 1h |
| **NAME prefix** | `ant_` (e.g. `ant_changelog_gap`) | `soldier_` (e.g. `soldier_route_pinger`) |
| **Cadence** | Every 6h (cron) | Every 30 min for 60s (cron) |
| **Per-cycle deposits** | 100-200 | 10-20 (aggregated) |
| **Aggregation** | Each finding → its own Pheromone INSERT | Per `(soldier_class, node_id)` group → one INSERT |
| **Composition** | Organized into 11 Legions + 6 Citizens | Flat namespace; auto-discovered |
| **Identity-bearing** | Yes (each ant has documented purpose) | No (disposable; replaceable) |
| **F5 (Cursus Honorum)** | Active (drift-resolution rewards / persistent-silence penalties) | **Exempt** (no Denarii accrual) |
| **Treasury participation** | Via Citizen.findings → CitizenFinding | None |
| **Inter-tier imports allowed?** | No (G6) | No (G6) — soldiers can't import commanders or each other |
| **Crash semantics** | Logged + flagged by ant_colony watcher | Returns []; colony continues |
| **Replay** | `seed = hash(NAME, today)` | Same seed protocol |
| **Source of design** | Polaris-native (Arc D / E) | Mirai + MiroFish + BettaFish synthesis (v9.03) |

---

## Why both tiers, not just one bigger commander tier?

Per VANTA's directive (Sanctum §I):

1. **Resilience** — losing 4-5 commanders today degrades performance
   noticeably; soldiers can be lost in droves
2. **Scale** — soldiers can grow to hundreds without exploding
   complexity (commanders top out at ~50 before the colony run
   gets unwieldy)
3. **Speed** — soldiers parallelize cheap checks across tight loops;
   commanders do heavy work less frequently
4. **Resource efficiency** — not every check needs consciousness-level
   reasoning; PID-file-vs-ps is one syscall
5. **Strategic flexibility** — two cadences, two intensity bands; the
   bloom heatmap stays legible (commanders peak; soldiers murmur)

External-source synthesis (the three repos VANTA pointed at):
- **Mirai**: scanner/loader/CnC tier separation + per-bot < 100KB
  footprint + disposability
- **MiroFish**: specialized agents with independent behavioral logic
  + ReportAgent synthesis
- **BettaFish**: capability-based distribution + aggregation layer
  + resilience through redundancy

---

## What goes where

### Use a Commander when:
- The check requires multi-attribute reasoning (cross-file diff,
  Sanctum-state synthesis, cognitive-layer health)
- The finding carries operator-actionable insight that warrants
  attention beyond "noted"
- The agent benefits from F5 reward/penalty (it's identity-bearing
  and we want the Cursus Honorum to engage)
- The finding belongs to a Legion (e.g., `ant_legion_doctrine_health`
  is a member of `LegioCognitiva`)
- The agent needs Citizen-class behavior (claim filing, civic
  participation)

### Use a Soldier when:
- The check is single-fact and stateless (PID alive? log line count?)
- The check is cheap enough to run every second
- Aggregating N observations into one deposit is fine (operator only
  needs to see "soldier saw X N times in the last cycle batch")
- The check is **disposable** — losing this soldier in a crash is
  acceptable; the next cycle's soldier is identical
- The check observes infrastructure state, not constitutional state

If a check could fit either bucket, the architect-recommended
default is **soldier** — the soldier protocol is more constrained
and that constraint forces honesty about whether the check really
needs commander-tier sophistication.

---

## Vocabulary collision avoidance

The terms "ant", "swarm", and "colony" pre-date the tier split.
Disambiguation rules:

- **"ant"** — by itself, ambiguous. In CHANGELOG / docs, prefer
  **"commander"** when the v9.03 distinction matters; **"agent"**
  when speaking about the abstract tier-agnostic concept.
- **"swarm"** — refers to BOTH tiers collectively. The Mycelium
  swarm = commanders + soldiers + citizens.
- **"colony"** — `polaris_swarm/colony.py` is the COMMANDER runner.
  `polaris_swarm/soldier_colony.py` is the SOLDIER runner.
  Confusingly, `colony.py:main()` dispatches to BOTH (via
  `--soldiers` and `--hybrid`). Future docs should refer to
  "commander colony" vs "soldier colony" when precision matters.
- **"deposit"** — a Pheromone INSERT. Both tiers deposit. Tier
  visible via `Pheromone.deposited_by` prefix (`ant_*` vs `soldier_*`).
- **"finding"** vs **"observation"** — strict tier-distinct.
  Commanders return `AntFinding`s (multi-attribute, individually
  inserted). Soldiers return `Observation`s (single-fact, batched
  before insertion).

---

## Inheritance prohibition

`Soldier` is **NOT** a subclass of `Ant`. They share NO base class.

Reason: a diamond-inherit hierarchy would let an agent accidentally
inherit commander-tier semantics (F5 participation, Legion
membership) into the soldier tier, breaking the disposability
invariant. The two base classes are deliberately disjoint; inter-
tier code reuse goes through plain functions in
`polaris_swarm/utils.py` (none currently shared).

The structural invariant `test_soldier_not_subclass_of_ant`
enforces this at test time.

---

## Cross-references

- [`polaris_swarm/base.py`](../polaris_swarm/base.py) — Ant base + AntFinding
- [`polaris_swarm/soldiers/base.py`](../polaris_swarm/soldiers/base.py) — Soldier base + Observation
- [`polaris_swarm/colony.py`](../polaris_swarm/colony.py) — commander runner + CLI dispatch
- [`polaris_swarm/soldier_colony.py`](../polaris_swarm/soldier_colony.py) — soldier aggregator
- [`polaris_swarm/soldiers/README.md`](../polaris_swarm/soldiers/README.md) — soldier protocol + 8-soldier list
- [`sanctum/2026-05-14-hybrid-swarm-mirai-pattern.md`](../sanctum/2026-05-14-hybrid-swarm-mirai-pattern.md)
- [`MISSION.md`](../MISSION.md) — C1, C10, G1, G3, G6 (preserved)
- [`meta/arc-f-denarius.md`](../meta/arc-f-denarius.md) — F5 (soldiers exempt)
