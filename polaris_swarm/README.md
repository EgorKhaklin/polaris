# polaris_swarm/ — Arc E · the Mycelium swarm

This directory is **Arc E** (Mycelium / genuine swarm intelligence),
opened 2026-05-13 by Sanctum
`sanctum/2026-05-13-arc-e-swarm-intelligence-opening.md`. Subsequent
arcs (F · the Denarius; G · Roman Empire) live partially under
`polaris_swarm/civitas/` and `polaris_swarm/legions/`.

Where `polaris_hydra/` (Arc D) is the **centralized synthesis** layer
(N watchers → 1 host → 1 voice for VANTA), Mycelium is the
**decentralized substrate**: tiny ants depositing pheromones onto
brain-map nodes via the append-only `Pheromone` table. Synthesis
emerges from pheromone density; no host calls; no LLM in the
substrate. Operators read the heatmap via
`scripts/ai-swarm-bloom.sh`.

For the strategic record (E1–E10 done-list narratives, legion +
Civitas + Cursus Honorum mechanics, the Architect's 100-year
simulation findings), see **`meta/arc-e-mycelium.md`**. For the
deeper Polaris-as-Civitas concept mapping, see `meta/civitas.md`.
For the Denarius economy (Arc F), see `meta/arc-f-denarius.md`
+ `meta/denarius.md`.

---

## Directory layout

```
polaris_swarm/
├── base.py                     # Pheromone, Ant, AntFinding base classes
├── colony.py                   # run_swarm(): Phase 1 legions → Phase 2 citizens
├── chaos.py                    # F2 chaos-test harness (deterministic failure injection)
├── ants/                       # 33 ants in 11 legions (post-v8.71)
│   ├── __init__.py             # ALL_ANTS registry
│   ├── ant_*.py                # one file per ant; each <120 LOC
│   └── ...
├── legions/                    # 11 legions (9 Republican + 2 Imperial)
│   ├── base.py                 # Legion + TacticConfig + 5 tactics
│   ├── legio_*.py              # one file per legion; declares ANTS + TACTIC
│   └── ...
└── civitas/                    # 6 citizens + Denarius treasury
    ├── base.py                 # Citizen + CitizenFinding + propose_new_ant
    ├── plebs_forum_watcher.py
    ├── eques_correlator.py
    ├── augur_bloom_reader.py
    ├── censor_roll_keeper.py
    ├── quaestor_treasurer.py   # 5th citizen (Arc F · F1)
    ├── tribuni_plebis_watcher.py  # 6th citizen (Arc G · G1)
    ├── treasury.py             # Denarius reward function (compute_rewards)
    ├── census-roll.json        # Filesystem-AoR (G14)
    └── treasury-roll.json      # Filesystem-AoR (G15)
```

---

## Three layers (read top-down)

### 1. Substrate — `Pheromone` table + `base.py`

The Pheromone table (in `polaris_sql/01_schema.sql`) is the 11th
audit-of-record instance. Append-only via
`trg_pheromone_append_only`. Every ant's deposit becomes one row;
the row carries `(deposited_by, node_id, intensity, kind,
half_life_hours, evidence)`. Decay is deterministic per `G7` (pure
function in `base.py::effective_intensity`).

Ants subclass `Ant`, return a list of `AntFinding` from `scan()`,
and never deposit directly — the colony runner serializes findings
to Pheromone rows.

### 2. Organization — `legions/`

Ants are organized into Legions for tactical dispatch. Each Legion
has:
- `NAME` — module name (e.g., `legio_cognitive`)
- `DOMAIN` — high-level area
- `LEGATUS` — display name
- `ANTS` — list of Ant subclasses
- `TACTIC` — `TacticConfig` declaring deployment doctrine

Five tactics (Roman military doctrine):
- **TESTUDO** — all ants scan; aggregate
- **TRIPLEX_ACIES** — tiered escalation (hastati → principes → triarii)
- **CUNEUS** — lead ant fires first; followers only if lead detects
- **VEXILLATIO** — operator-directed focused mission
- **AUXILIA** — borrow ants from allied legions

11 legions today: 9 **Republican** (the original Mycelium cohort —
schema, cognitive, security, mission, adversary, performance,
trajectory, substrate, docs) + 2 **Imperial** (added Arc G — Praetorian,
Engineer). The Hydra-9 mythology was relocated from Mycelium legions
to HYDRA watchers in v8.72 — see
`sanctum/2026-05-13-hydra-mythology-relocation-to-watchers.md`.

### 3. Civic layer — `civitas/`

Six citizen classes, parallel to legions:
- **Plebs** (Plebeians) — cross-legion forum readers
- **Equites** (Equestrians) — cross-legion correlators
- **Augures** (Augurs) — pattern interpreters
- **Censores** (Censors) — keepers of the census-roll (G14 FS-AoR)
- **Quaestores** (Quaestors) — financial magistrates; Denarius reward
  function via `treasury.py` (G15 FS-AoR + G16 determinism)
- **Tribuni Plebis** — usability advocates; observe Sanctum-protocol
  entropy (Arc G addition)

Citizens observe the swarm itself (cross-legion patterns + civic
state); they do NOT subclass Ant (G12); they cannot literally spawn
ants (G13 — proposal-driven autogenesis only).

---

## G-guards (the contract)

| Guard | Rule |
|---|---|
| G6 | No ant imports another ant (decentralization) |
| G7 | Pheromone decay is deterministic (replay) |
| G8 | No ant imports an LLM client (substrate determinism) |
| G9 | Pheromone table is append-only (AoR) |
| G10 | Every ant belongs to exactly one Legion (partition) |
| G11 | Ants don't import from `polaris_swarm.legions` (one-way knowledge) |
| G12 | Citizens don't subclass Ant (parallel hierarchy) |
| G13 | No literal autogenesis (proposal-pheromone-driven only) |
| G14 | `census-roll.json` is filesystem-AoR (append-only) |
| G15 | `treasury-roll.json` is filesystem-AoR (append-only) |
| G16 | Reward function is deterministic (replay-safe) |
| G17 | Acceleration ants are read-only with respect to source files |
| G18 | Consciousness ants observe SWARM SELF-STATE (registries, meta docs, FS-AoR rolls) |
| G19 | Cursus Honorum multipliers are monotonic non-decreasing in balance |
| G20 | Sanctum-chair eligibility derives ONLY from denarii balance (C10 pomerium) |
| G22 | Tribuni Plebis observes usability surface only (no identity-layer) |
| G23 | Via Appia is a property of AntFinding, not a parallel routing layer |
| G24 | New legions require Sanctum authorization |
| G25 | Cohort growth >50% per ship requires explicit Sanctum acknowledgment |
| G26 | Additions to `STEADY_STATE_ANTS` allowlist require Sanctum authorization |

(G21 belongs to `polaris_hydra/` — Praetorian observability constraint
on the Praetorian ants under `polaris_swarm/ants/`.)

---

## Running the swarm

```bash
# Single colony pass (--dry: no DB writes)
python3 -m polaris_swarm.colony --dry

# Full two-phase swarm (legions then citizens)
python3 -m polaris_swarm.colony --swarm --dry

# Read the bloom (operator-facing heatmap)
./scripts/ai-swarm-bloom.sh

# Run F2 chaos test
python3 -c "
from polaris_swarm.chaos import run_chaos_pass, FailureMode
from polaris_swarm.ants import AntTodoDebt
import pathlib
result = run_chaos_pass({AntTodoDebt: FailureMode.RAISE_EXCEPTION},
                        root=pathlib.Path('.').resolve())
print(result.detected_failures)
"
```

---

## Where to learn more

| Question | Read |
|---|---|
| Strategic record (E1-E10 narratives) | `meta/arc-e-mycelium.md` |
| Civitas concept (Senatus, Forum, Pomerium, Mos Maiorum) | `meta/civitas.md` |
| Denarius economy + Cursus Honorum | `meta/arc-f-denarius.md`, `meta/denarius.md` |
| Roman Empire expansion (Imperial legions, Tribuni Plebis) | `meta/arc-g-empire.md` |
| HYDRA's relationship to Mycelium | `polaris_hydra/README.md` |
| Pheromone schema | `polaris_sql/01_schema.sql` (search `Pheromone`) |
| Ant contract | `polaris_swarm/base.py::Ant` |
| Citizen contract | `polaris_swarm/civitas/base.py::Citizen` |
| Tactical doctrine details | `polaris_swarm/legions/base.py` |
| Authorizing Sanctums | `sanctum/2026-05-13-arc-e-*` + `arc-f-*` + `arc-g-*` |
