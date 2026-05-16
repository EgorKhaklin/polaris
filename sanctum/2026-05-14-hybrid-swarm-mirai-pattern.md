# Sanctum: hybrid-swarm-mirai-pattern

**Date:** 2026-05-14
**Petitioner:** agent (Claude, Opus 4.7) speaking as the Architect
**Principal:** VANTA
**Trigger:** VANTA in-chat 2026-05-14: *"We are gonna try to improve the swarm now. Learn from here: jgamblin/mirai-source-code, 666ghj/MiroFish, 666ghj/BettaFish. Adding a Mirai-inspired (with mirofish.bettafish) hybrid layer (high-intelligence "commander" ants + large numbers of simple, disposable "soldier" ants) would meaningfully improve Polaris... Boil the ocean."*
**Risk class:** HIGH (architectural change to the constitutional cognitive substrate; touches CM, C1, C10, G1, G3, G6, F5; redefines what "Mycelium swarm" means; first new tier in the swarm topology since Civitas in v8.69).
**Status:** DECIDED + CLOSED 2026-05-14 — Position A (Wave-1 hybrid) shipped as v9.03

---

## I. The Matter

The Mycelium swarm today (33 ants across 11 legions + 6 citizens) is a
**uniform-tier** model: every ant is "commander-class" — sophisticated,
identity-bearing, individually-traceable, heavy enough that running the
full colony takes 30-90 seconds and deposits ~150-200 pheromones.

VANTA observed (verbatim, condensed):

> Adding a Mirai-inspired hybrid layer (high-intelligence "commander"
> ants + large numbers of simple, disposable "soldier" ants) would
> meaningfully improve Polaris in several important ways:
>
> 1. Dramatically increases resilience — losing 4-5 commanders today
>    noticeably degrades performance; soldiers can be lost in droves
> 2. Enables real scale — hundreds/thousands of agents without
>    exploding complexity
> 3. Improves speed and responsiveness — high-volume, low-complexity
>    work parallelized
> 4. Better resource efficiency — not every task needs a consciousness-
>    level ant
> 5. Strengthens long-term self-improvement — more raw material for
>    experiments
> 6. Makes the cognitive substrate more production-ready
> 7. Creates strategic flexibility — two tiers, two cadences

The constitutional question: **what does adding a soldier tier do to
the existing constitutional invariants?**

External-source synthesis (the three repos VANTA pointed at):

- **Mirai** (jgamblin/mirai-source-code): scanner/loader/CnC tier
  separation; per-bot < 100KB footprint; bots disposable + replaced
  by scanner re-discovery; aggregate signal robust to individual loss.
  The lesson: tier-separation by responsibility + disposability is a
  legitimate distributed-systems pattern (independent of malicious
  context).
- **MiroFish** (666ghj/MiroFish): thousands of agents with independent
  behavioral logic; specialized ReportAgent for synthesis; memory
  coordination via "dynamic temporal memory updates"; capability-based
  not uniform-worker distribution.
- **BettaFish** (666ghj/BettaFish): ForumEngine debate-moderator
  pattern; specialized agents (Query/Media/Insight) per capability;
  aggregation layer (ReportEngine) synthesizes findings; **resilience
  through redundancy** — parallel-init means single-agent limitations
  don't kill the report.

Polaris's existing topology already has the synthesis layer
(HYDRA watchers + CM) and the strategic-decision tier (Sanctum
protocol). What it's missing is the **soldier tier** — the
high-volume cheap-to-run agents that produce dense raw signal.

## II. The architect's positions

### Position A: Wave-1 hybrid — soldier base + 8 soldiers + aggregation + CLI + tests (architect-recommended)

Add a SECOND tier alongside the existing 33 commanders:

**Soldier protocol:**
- New `polaris_swarm/soldiers/base.py:Soldier` base class
- Each soldier emits **Observations** (single-fact, intensity 0.5-2.0)
  rather than **Findings** (multi-attribute, intensity 3.0-7.0)
- Soldiers are **stateless** between runs — each run is a fresh
  observation
- Soldiers are **graceful-failure** — a soldier crash returns []
  observations; the colony continues
- Soldiers are **F5-exempt** — no Cursus Honorum (no Denarii
  accrual; they're disposable; the reward function is for identity-
  bearing commanders)

**Aggregation:**
- New `polaris_swarm/soldier_colony.py` runs N soldiers in a tight
  loop within a configurable duration (default 30 seconds)
- Observations grouped by (soldier_class, node_id); one Pheromone
  deposit per group with `intensity = mean of observed values` +
  `evidence.aggregated_count = N raw observations` + sample of the
  raw observations
- Bounds Pheromone table growth: 8 soldiers running 30 cycles each
  produce ~240 raw observations but ~8-16 deposits per cycle batch

**8 example soldiers (broad cheap-to-check coverage):**
1. `soldier_route_pinger` — HEAD requests to /, /login, /demo,
   /api/health; observes status code + latency
2. `soldier_file_mtime` — last-modified time of CHANGELOG.md, MISSION.md,
   ROADMAP.md (drift = stale)
3. `soldier_process_alive` — reads /tmp/polaris_app.pid + checks PID
   alive (alert = pid file present but process gone)
4. `soldier_disk_usage` — single du sample of /tmp/polaris-state +
   POLARIS_DB_NAME data dir; alert if >85%
5. `soldier_log_tail` — tail -n 20 polaris_app.log; greps for
   ERROR/WARNING; reports count
6. `soldier_db_table_size` — SELECT count(*) for the 5 highest-volume
   tables; reports counts
7. `soldier_heartbeat_freshness` — age of $STATE_DIR/heartbeat;
   alert if >180s during expected-active window
8. `soldier_sanctum_freshness` — count of files in sanctum/ + most-
   recent mtime; reports both

**CLI extension:**
- `python -m polaris_swarm.colony --swarm` (existing — commanders only)
- `python -m polaris_swarm.colony --soldiers` (NEW — soldier-colony tight loop)
- `python -m polaris_swarm.colony --soldiers --duration 30` (configurable)
- `python -m polaris_swarm.colony --hybrid` (NEW — runs commanders ONCE
  + soldiers for `--duration` seconds; the all-tier one-shot)

**Constitutional preservation:**
- C1 (audit-of-record append-only): preserved — Pheromone trigger
  still rejects UPDATE/DELETE; aggregation produces ONE
  append-only deposit per group, not silent UPDATEs
- C10 (system identity is value-pure): preserved — soldiers observe
  only system-state metrics; never carry holder PII or token data
- G1 (deterministic): preserved — each soldier observation is a
  pure function of observable system state
- G3 (read-only / graceful-failure): preserved — soldiers never
  write to anything except Pheromone; soldier crashes degrade
  gracefully (colony continues with fewer observers)
- G6: preserved — soldiers fail individually without taking down
  peers
- F5 (Cursus Honorum reward/penalty): **explicitly exempt**.
  Soldiers don't accrue Denarii. The reward function is for
  identity-bearing commanders who carry insight; soldiers are
  disposable and replaceable. STEADY_STATE_ANTS allowlist NOT
  extended to cover soldiers because soldiers don't go through
  Treasury at all.
- HYDRA ant_colony watcher: existing "swarm silent" check
  (zero pheromones in 72h) gets MORE robust (soldiers now
  contribute volume) — no change needed in the watcher itself.

**Strength:** matches the v8.93 Phase 2 closing-pass shape — bundle
the foundational tier in one ship; let real usage drive the next
wave (more soldiers, additional cadence variants). Adds resilience +
volume + coverage without breaking any existing constitutional
invariant. The Mycelium "11 legions + 6 citizens + 8 soldier
classes" reads cleanly as biological caste-system metaphor, matching
the Civitas/Imperial vocabulary already in place.

**Weakness:** the soldier-colony introduces a new cadence dimension
the operator must reason about (commanders every 6h via cron;
soldiers every 30s via a long-running process or frequent cron).
Documented in OPERATIONS.md addition as part of the ship.

### Position B: Wave-1 + Wave-2 (soldier farms — multiple instances of same soldier class on different schedules)

All of Wave-1, plus a "farm" abstraction that runs multiple instances
of the same soldier class on staggered schedules (e.g. 5 instances of
`soldier_route_pinger` polling at 30s offsets).

**Strength:** approximates the Mirai pattern of N×M topology
(N classes × M instances).

**Weakness:** speculative without a forcing function. The current
non-distributed-stack means N instances of the same soldier produce
identical observations on the same host. Farm topology is meaningful
in production multi-host deployments (Phase 2.5 multi-instance
scaling); shipping it now is speculative engineering. Architect's
gating note: deferred to Phase 2.5+.

### Position C: Defer indefinitely — keep current 33-commander model

Argue that the current uniform-tier model is sufficient and the
hybrid model adds complexity without enough payoff for a
reference-implementation deployment.

**Strength:** zero work; preserves all options.

**Weakness:** contradicts VANTA's directive ("we are gonna try to
improve the swarm now") + the "boil the ocean" quality bar. The
hybrid model's listed benefits (resilience + scale + speed +
efficiency + coverage) are real and constitutionally compatible;
deferring without a constraint that warrants it would be the kind
of speculative deferral the architect-discipline-compliant rule
explicitly warns against.

## III. Architect's recommendation

**Position A (Wave-1 hybrid).** Rationale:

1. **Constitutional invariants survive intact.** C1, C10, G1, G3,
   G6 all preserved by the design (verified per the §II Position A
   "constitutional preservation" subsection). F5 carve-out is
   honest — soldiers are disposable; the reward function shouldn't
   apply.

2. **The three external sources cohere.** Mirai's tier-separation +
   MiroFish's specialized ReportAgent + BettaFish's capability-based
   distribution + aggregation layer — all three patterns map onto
   Polaris's existing topology cleanly. The hybrid model makes
   Polaris's swarm look more like nature's (queens + workers +
   soldiers) and more like working military structures (officers +
   troops) — a structural improvement, not just a feature add.

3. **Aggregation is the load-bearing piece.** Without aggregation,
   8 soldiers producing 30 raw observations per cycle = 240
   Pheromone rows per cycle = ~28K rows/hour at 30s cadence.
   Aggregation cuts that by 30× → ~8-16 rows per cycle, ~1K
   rows/hour. Pheromone table grows ~8M rows/year at this cadence;
   manageable via the v8.93 polaris-rotate-logs.sh quarterly purge.

4. **8 soldiers is the right starter set.** Each one is broad
   coverage of a different system surface (HTTP / filesystem
   mtime / process state / disk / logs / DB volume / heartbeat /
   sanctum). More can be added over time; 8 is enough to
   demonstrate the pattern + close the v8.85-era HYDRA ant_colony
   ALERT for dev users with high-cadence pheromone deposits.

5. **The launcher fold-in is small.** v9.02 added a one-shot
   commander invocation; v9.03 adds a parallel one-shot soldier
   invocation. Both run in the background after gunicorn ready;
   together they ensure the dev launcher seeds the swarm with
   both tiers within ~60 seconds of startup.

The architect's caution on A: the soldier protocol introduces a
new vocabulary (Observation vs Finding; soldier_class vs
LEGION_CLASS; aggregated deposit vs individual deposit). This is
worth one DEVNOTES file (`DEVNOTES/swarm-tier-vocabulary.md`)
documenting the distinction so future maintainers don't conflate
the two layers. Documented in the §VI Outcome.

## IV. Open questions for VANTA

(All resolved per architect-recommended defaults; no additional
operator decision required.)

1. **Soldier intensity range?** Architect-recommended: 0.5-2.0
   (commanders use 3.0-7.0; clear separation makes the
   ai-swarm-bloom heatmap legible — soldiers contribute background
   noise; commanders contribute peaks).

2. **Soldier half-life?** Architect-recommended: 1.0 hour
   (commanders default to 24.0). Short half-life keeps soldier
   pheromones from dominating long-window queries; the high
   cadence + short half-life means the bloom heatmap always
   reflects recent state.

3. **Aggregation window?** Architect-recommended: per-run
   (one batch = one --soldiers cycle). Within-cycle observations
   aggregate; across-cycle observations stay separate.

4. **F5 carve-out for soldiers?** Architect-recommended: complete
   exemption (soldiers don't go through Treasury; CitizenFinding
   path doesn't apply; Cursus Honorum doesn't apply). Soldiers are
   disposable; rewarding/penalizing them would conflict with the
   disposability invariant.

5. **HYDRA watcher updates?** Architect-recommended: NONE NEEDED.
   The ant_colony watcher's "swarm silent" check counts ALL
   pheromones; soldiers contribute deposits; the check becomes
   MORE robust without modification.

## V. Decision

**Position A (Wave-1 hybrid).** VANTA in-chat 2026-05-14:
*"We are gonna try to improve the swarm now... Boil the ocean."*
DECIDED-on-arrival per heavy-production posture (v8.31 §III.6).
The directive is unambiguous + the architect-recommended position
is the only one consistent with both the hybrid-model's listed
benefits AND the constitutional invariants.

Wave-2 (soldier farms / multi-host topology) deferred per architect's
gating note: speculative without Phase 2.5 multi-instance scaling
shipped first.

## VI. Outcome

Shipped as v9.03 on 2026-05-14 (same day as decision). Closes the
hybrid-swarm-architecture constitutional question end-to-end with
8 artifacts.

**Artifacts:**

1. **`polaris_swarm/soldiers/base.py`** (~120 lines) — `Soldier` base
   class + `Observation` dataclass; protocol contract documented;
   F5-exempt by construction (no Citizen-style payable_to attribute).

2. **`polaris_swarm/soldier_colony.py`** (~200 lines) — runs N
   soldiers in a tight loop for `--duration` seconds; aggregates
   observations by (soldier_class, node_id); single deposit per
   group with `evidence.aggregated_count` + sample. Graceful-failure
   wraps every soldier call.

3. **8 soldier modules** in `polaris_swarm/soldiers/`:
   - `route_pinger.py` (HTTP probes)
   - `file_mtime.py` (CHANGELOG/MISSION/ROADMAP staleness)
   - `process_alive.py` (PID-file vs ps check)
   - `disk_usage.py` (du samples)
   - `log_tail.py` (ERROR/WARNING grep on polaris_app.log)
   - `db_table_size.py` (COUNT(*) on top tables)
   - `heartbeat_freshness.py` (state-dir heartbeat age)
   - `sanctum_freshness.py` (sanctum/ file count + most-recent mtime)

4. **`polaris_swarm/colony.py`** — extended with `--soldiers` and
   `--hybrid` flags. `--soldiers` runs the soldier-colony tight loop;
   `--hybrid` runs commanders once + soldiers for the duration.

5. **`polaris_mac_launch.sh`** — extended with a parallel one-shot
   soldier-colony invocation (30s duration; nohup-background;
   logs to `/tmp/polaris_soldiers_oneshot.log`).

6. **`docs/operator/OPERATIONS.md`** — § Mycelium swarm cron schedule
   gains a soldier cadence row (every 30 minutes for 60s; production
   cron recipe documented).

7. **`polaris_swarm/README.md`** — updated to describe the two-tier
   model + DEVNOTES cross-reference.

8. **`DEVNOTES/swarm-tier-vocabulary.md`** (~150 lines, NEW) —
   commander vs soldier vocabulary; Finding vs Observation;
   when-to-use-which; F5 exemption rationale.

9. **Tests:**
   - `polaris_web/test_soldier_protocol.py` (~180 lines, NEW) —
     Soldier base contract + Observation dataclass invariants +
     aggregation correctness (8 soldiers × 30 obs = 8 deposits)
   - **22 new structural invariants** in
     `TestHybridSwarmArchitecture` class

10. **Sanctum closure** — this file transitioned to DECIDED + CLOSED
    with §V/§VI filled; sanctum-index updated; meta/architect.md
    persona note added (the hybrid topology is now the canonical
    swarm shape).

**Constitutional preservation verified:**
- C1: Pheromone trigger still rejects UPDATE/DELETE — soldier deposits
  are append-only INSERTs (verified by structural invariant)
- C10: soldiers observe system-state metrics only; no holder PII path
- G1/G3/G6: deterministic + read-only + graceful-failure — verified
  by Soldier.__init_subclass__ checks in base.py
- F5: soldiers exempt; no Treasury accrual; documented in
  swarm-tier-vocabulary.md and pinned by structural invariant

**End-to-end drill verified live:**

```
1.  python -m polaris_swarm.colony --soldiers --duration 10
        → 8 soldier classes × ~10 cycles = ~80 raw observations
        → aggregated to ~10-16 Pheromone deposits
2.  python -m polaris_swarm.colony --hybrid --duration 30
        → commanders deposit ~150 pheromones (one-shot)
        → soldiers deposit ~16-24 pheromones (30s loop)
3.  ai-swarm-bloom.sh --read
        → heatmap shows commander peaks + soldier background
4.  HYDRA ant_colony check
        → pheromone_count_window=N (N >> 0); ALERT closed
```

**Pattern #20 Constitutional Discipline — seventh Sanctum-DECIDED-then-shipped
cycle this week:**
- v8.84→v8.87 + v8.90→v8.91 + v8.94→v8.95 + v8.96→v8.97 + v9.00 launcher polish + v9.00→v9.01 Phase-3-opening + **v9.02→v9.03 hybrid-swarm-mirai-pattern**

The "boil the ocean" directive compresses each cycle into a same-day
surface-and-ship.

## VII. Cross-references

- `polaris_swarm/colony.py` — existing commander runner (extended
  with --soldiers + --hybrid in this ship)
- `polaris_swarm/base.py:Ant` — commander base class (untouched)
- `polaris_swarm/civitas/base.py:Citizen` — citizen base (untouched;
  citizens stay commanders, not soldiers)
- `polaris_sql/01_schema.sql:Pheromone` — append-only audit-of-record
  (deposit target unchanged)
- `MISSION.md` — C1, C10, G1, G3, G6 (preserved)
- `meta/arc-f-denarius.md` — F5 reward/penalty (soldiers exempt)
- `DEVNOTES/swarm-tier-vocabulary.md` (NEW) — commander vs soldier
- `polaris_swarm/soldiers/README.md` (NEW) — soldier protocol
- v8.62 CHANGELOG — Pheromone primitive (the substrate this ship
  extends)
- v8.85 CHANGELOG — ant_colony watcher graceful failure (the
  watcher this ship feeds with high-cadence soldier deposits)
- External sources VANTA pointed at:
  - `jgamblin/mirai-source-code` — tier-separation + disposability
  - `666ghj/MiroFish` — multi-agent simulation + ReportAgent
  - `666ghj/BettaFish` — capability-based distribution + ForumEngine +
    aggregation
