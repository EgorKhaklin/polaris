# `polaris_swarm/soldiers/` — the lightweight tier of the Mycelium swarm

v9.03 / Sanctum [`2026-05-14-hybrid-swarm-mirai-pattern.md`](../../sanctum/2026-05-14-hybrid-swarm-mirai-pattern.md).

This package holds the **soldier tier** — lightweight, disposable
agents that emit single-fact `Observation`s and are aggregated by
`polaris_swarm/soldier_colony.py` into batched Pheromone deposits.

For the heavyweight tier (sophisticated commanders that emit
multi-attribute `AntFinding`s), see [`polaris_swarm/`](../README.md)
and [`polaris_swarm/civitas/`](../civitas/).

---

## Why two tiers exist

VANTA's directive (verbatim):

> Adding a Mirai-inspired hybrid layer (high-intelligence
> "commander" ants + large numbers of simple, disposable "soldier"
> ants) would meaningfully improve Polaris in several important
> ways: dramatically increases resilience, enables real scale,
> improves speed and responsiveness, better resource efficiency,
> strengthens long-term self-improvement, makes the cognitive
> substrate more production-ready, creates strategic flexibility.

External-source synthesis: Mirai (tier-separation by responsibility +
disposability), MiroFish (specialized agents with independent
behavioral logic + ReportAgent synthesis), BettaFish (capability-based
distribution + aggregation layer + resilience through redundancy).

---

## The 8 shipped soldiers (Wave-1)

Each soldier is one fact-checking primitive. The list is bounded
intentionally; more can be added over time without changing the
protocol.

| Soldier | Probes | Kind |
|---|---|---|
| `soldier_route_pinger` | HEAD requests against `/`, `/login`, `/demo`, `/api/health` (status + latency) | info / drift / alert (unreachable) |
| `soldier_file_mtime` | last-modified time of CHANGELOG.md, MISSION.md, ROADMAP.md, CLAUDE.md | info / drift (stale) |
| `soldier_process_alive` | `/tmp/polaris_app.pid` vs `kill -0 <pid>` | info / alert (zombie pid file) |
| `soldier_disk_usage` | `du` sample of `$STATE_DIR` + `/tmp` | info / drift (>70%) / alert (>85%) |
| `soldier_log_tail` | greps last 200 lines of `/tmp/polaris_app.log` for ERROR / WARNING | info / drift (warning) / alert (error) |
| `soldier_db_table_size` | `pg_class.reltuples` for the 5 highest-volume tables | info |
| `soldier_heartbeat_freshness` | age of `$STATE_DIR/heartbeat` (matches launcher's 180s threshold) | info / drift (>30s) / alert (>180s) |
| `soldier_sanctum_freshness` | `sanctum/` file count + most-recent mtime | info |

---

## Protocol

A soldier is a subclass of `polaris_swarm.soldiers.base.Soldier`. The
contract is small (deliberately):

```python
from polaris_swarm.soldiers.base import Soldier, Observation, KIND_INFO

class MySoldier(Soldier):
    NAME = "soldier_my_thing"          # MUST start with 'soldier_'
    DESCRIPTION = "one-line operator-readable purpose"
    INTENSITY = 1.0                    # MUST be in [0.5, 2.0]
    NODE_PREFIX = "infra:my_thing"     # MUST be colon-namespaced
    HALF_LIFE_HOURS = 1.0              # default; override per class

    def observe(self) -> list[Observation]:
        # MUST be a pure function of observable state + self.seed
        # MUST graceful-fail: catch exceptions; return [] on error
        # MUST NOT import other soldiers/commanders (G6)
        # MUST NOT carry holder PII (C10)
        # MUST NOT call LLMs / write to DB / persist state
        return [Observation(
            node_id=f"{self.NODE_PREFIX}:something",
            value={"foo": 42},
            kind=KIND_INFO,
        )]
```

The `Soldier.__init_subclass__` validator runs at import time:
- `NAME` must start with `"soldier_"`
- `INTENSITY` must be in `[0.5, 2.0]` (the soldier band; commanders
  use `[3.0, 7.0]`)
- `NODE_PREFIX` must be a non-empty colon-namespaced string

A misconfigured soldier fails LOUD at import, not at runtime.

---

## Aggregation

`polaris_swarm/soldier_colony.py:run_soldier_colony()`:

1. Discovers all `Soldier` subclasses under `polaris_swarm.soldiers.*`
2. Runs each `.observe()` on every cycle within the run window
3. Groups Observations by `(soldier_class, node_id)`
4. Produces ONE Pheromone deposit per group with:
   - `intensity = SoldierCls.INTENSITY` (constant; in the soldier band)
   - `kind = max(severity in group)` — alert > drift > info
   - `evidence = {soldier_class, soldier_name, aggregated_count, cycles, observations: [first_3_samples]}`
5. C1 preserved: each deposit is one append-only INSERT
6. F5 exempt: no Treasury writes, no CitizenFinding path

Bounds Pheromone table growth:
- 9 soldiers × 30 cycles × ~3 observations each = ~810 raw observations
  (v9.11 added the priest tier `soldier_swarm_witness` to the v9.03 baseline of 8 workers)
- → grouped to ~10-20 deposits per cycle batch

---

## CLI

```bash
# Soldier-tier only, default 30s
python -m polaris_swarm.colony --soldiers

# Soldier-tier only, custom duration + cycle interval
python -m polaris_swarm.colony --soldiers --duration 60 --cycle-interval 0.5

# Both tiers: commanders ONCE + soldiers for the duration
python -m polaris_swarm.colony --hybrid --duration 30

# Dry run (no DB writes)
python -m polaris_swarm.colony --soldiers --dry
```

Production cron recipe lives in
[`docs/operator/OPERATIONS.md`](../../docs/operator/OPERATIONS.md)
§ Mycelium swarm cron schedule.

The dev launcher (`polaris_mac_launch.sh`) kicks off
`--hybrid --duration 30` automatically as a one-shot after gunicorn
becomes ready, so a fresh dev double-click seeds the swarm with both
tiers within ~60 seconds.

---

## Constitutional preservation

| Constraint | Preservation |
|---|---|
| C1 (audit-of-record append-only) | Each aggregated group → ONE Pheromone INSERT; trigger still rejects UPDATE/DELETE |
| C10 (system identity is value-pure) | Soldiers observe ONLY system-state metrics; no holder PII path |
| G1 (deterministic) | Each `.observe()` is a pure function of observable state + seed |
| G3 (read-only / graceful-failure) | Soldiers never write to anything except Pheromone (via colony); per-soldier crash returns [] |
| G6 (no inter-ant imports) | Soldiers don't import commanders or each other |
| F5 (Cursus Honorum) | **Soldiers exempt** — no Denarii accrual; disposable invariant |

See [`DEVNOTES/swarm-tier-vocabulary.md`](../../DEVNOTES/swarm-tier-vocabulary.md)
for the canonical commander-vs-soldier vocabulary distinction
(Finding vs Observation, etc).

---

## Adding a new soldier

1. Create `polaris_swarm/soldiers/<purpose>.py`
2. Subclass `Soldier`; set `NAME` / `DESCRIPTION` / `INTENSITY` /
   `NODE_PREFIX`; implement `.observe()`
3. The discovery walker auto-finds it on next import — no
   registry-file edit needed
4. Add a structural-invariant test in `test_structural_invariants.py`
   `TestHybridSwarmArchitecture` if the soldier carries new
   constitutional weight (most don't; they're disposable)
5. CHANGELOG entry under the next ship's "soldiers added" line

---

## Cross-references

- [`polaris_swarm/soldiers/base.py`](base.py) — `Soldier` base + `Observation` dataclass
- [`polaris_swarm/soldier_colony.py`](../soldier_colony.py) — discovery + aggregation + deposit
- [`polaris_swarm/colony.py`](../colony.py) — CLI entry-point with `--soldiers` / `--hybrid`
- [`polaris_swarm/README.md`](../README.md) — overall swarm overview
- [`DEVNOTES/swarm-tier-vocabulary.md`](../../DEVNOTES/swarm-tier-vocabulary.md) — commander vs soldier
- [`sanctum/2026-05-14-hybrid-swarm-mirai-pattern.md`](../../sanctum/2026-05-14-hybrid-swarm-mirai-pattern.md) — constitutional record
