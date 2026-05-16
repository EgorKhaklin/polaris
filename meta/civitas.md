# meta/civitas.md — Polaris as a Roman civilization

Polaris's cognitive layer is structurally Rome. The metaphor was
implicit through v8.61; v8.64 named the legions; v8.65 closed the
Hydra mythology; v8.66 names the rest of the civitas.

This document is the **map** of what Roman concept means what in
Polaris. Future agents priming on the cognitive layer should read
this once.

---

## The civitas, in full

| Roman concept | Polaris artifact | Where to find it |
|---|---|---|
| **Senatus** (Senate) | The Sanctum protocol | `meta/sanctum-protocol.md`, `scripts/ai-sanctum.sh`, `sanctum/*.md` |
| **SPQR** (Senate + People) | Operator-agent dialogue | The chat thread + Sanctum §V/§VI |
| **Capitolium** (Capitol Hill) | The constitution | `MISSION.md` |
| **Forum Romanum** | Pheromone log + bloom | `Pheromone` table; `scripts/ai-swarm-bloom.sh` |
| **Pomerium** (sacred boundary) | C10 (identity ≠ money) | `MISSION.md` hard constraints table |
| **Mos Maiorum** (ancestral custom) | Audit-of-record discipline | `DEVNOTES/audit-of-record.md` |
| **Lares et Penates** (household spirits) | Per-domain Legion identities | `polaris_swarm/legions/legio_*.py` |
| **Pontifices** (custodians of sacred rite) | CM, the immortal head | `scripts/ai-meta.sh`; v8.9 + v8.65 framing |
| **Limes** (frontier wall) | TrajectoryWatcher | `polaris_hydra/watchers/trajectory_watcher.py` |
| **Cursus Honorum** (career path) | Deferred — future E9 | (not yet shipped) |
| **Auspicia** (interpretation of signs) | Augur civitas class | `polaris_swarm/civitas/augur_bloom_reader.py` |
| **Census** (the roll of citizens) | Censor class + census-roll.json | `polaris_swarm/civitas/censor_roll_keeper.py`, `census-roll.json` |

## The military: Legiones

The Mycelium swarm's military layer. Eleven legions, organized
Republican + Imperial. **Legions are NOT Hydra heads** (as of
v8.72) — that mythology was relocated to HYDRA watchers in
`polaris_hydra/`; the legions are organizationally Roman but
mythologically just legions. The five tactical doctrines
(TESTUDO, TRIPLEX_ACIES, CUNEUS, VEXILLATIO, AUXILIA) are
documented in `polaris_swarm/legions/base.py`. Recruitment is
autonomous within Arc E (each Legatus can add ants to their
cohort without a Sanctum, as long as G6-G11 still pass).

```
Republican legions (the v8.65 cohort — 9 legions):
  Legatus Schema          (testudo)        2 ants
  Legatus Cognitive       (testudo)        7 ants   ← self-monitoring HUB (v8.69)
  Legatus Security        (testudo)        1 ant
  Legatus Mission         (testudo)        2 ants
  Legatus Adversary       (cuneus)         1 ant
  Legatus Performance     (testudo)        3 ants
  Legatus Trajectory      (triplex_acies)  5 ants   ← all 3 tiers active (v8.69+F3)
  Legatus Dependentia     (cuneus)         3 ants
  Legatus Memoria         (triplex_acies)  5 ants   ← T2+T3 grew (v8.69)

Imperial legions (added v8.71 / Arc G):
  Legatus Custos          (testudo)        2 ants   ← Praetorian (constitutional)
  Legatus Aedile          (cuneus)         2 ants   ← Engineer (build/release)
                                          ────────
                                          33 legionnaires
```

**Cohort growth.** v8.62 (E1) shipped 3 starter ants; v8.63 (E2)
grew it to 12; v8.65 (E7) reached 18 across 9 legions (the
moment the Hydra-9 mythology was placed on legions); v8.69 (E10)
added **acceleration + consciousness** for a cohort of **28**;
v8.70 (F3) added the first proposal-driven ant
(`ant_proposal_stagnation`) for **29**; v8.71 (G1) opened Arc G
adding Legio Praetorian + Legio Engineer for a cohort of **33**;
**v8.72 relocated the Hydra mythology entirely to HYDRA watchers**,
leaving the legions organizationally Roman but mythologically
unloaded.

**Hydra mythology relocation (v8.72).** Originally (v8.65) the
nine Mycelium legions were the nine canonical mortal heads of
the Lernaean Hydra. The placement was a stretch even at the
time: `polaris_hydra/` is literally named HYDRA; Mycelium has
no etymological tie to the Hydra. v8.72 course-corrects per
VANTA's directive: the watchers in `polaris_hydra/` (expanded
7 → 9 with `ant_colony` + `civitas`) ARE the canonical Hydra-9
heads. The Mycelium legions are *legions* — organizational
units of the swarm, named in the Roman military tradition,
without Hydra-mythology load.

CM remains the immortal 10th head — constitutional bedrock,
outside both legions and watchers. See [`MISSION.md`](../MISSION.md)
"What this section is NOT" for the substitutability clause that
applies to every other element of the substrate (but not CM).
The relocation Sanctum:
`sanctum/2026-05-13-hydra-mythology-relocation-to-watchers.md`.

## The civilians: Civitas

Four civilian classes, **not in legions**, each filling a coverage
gap the legions don't see. Citizens observe the swarm itself
(the Forum, the census, cross-legion patterns) rather than the
project artifacts.

### Plebs (Plebeians)

The everyday citizens; the working class. In the swarm, they
read the Forum (pheromone log) and surface volume imbalances.
When one legion contributes >50% of recent deposits, that's
either a crisis or a burst of genuine work — either way, worth
visibility.

- Module: `polaris_swarm/civitas/plebs_forum_watcher.py`
- Civic class: `plebs`
- Deposits: `observation_type=forum_imbalance`

### Equites (Equestrians)

The merchant class; they moved between cities, between social
strata. In the swarm, they're cross-legion couriers — they
correlate findings across legions that have not declared formal
alliances (no `auxilia_pool`). Generic curiosity, not loyalty.

- Module: `polaris_swarm/civitas/eques_correlator.py`
- Civic class: `eques`
- Deposits: `observation_type=cross_legion_correlation`

### Augures (Augurs)

The priests who read auspices — flights of birds, entrails,
lightning. They interpreted; they did not decide. In the swarm,
the Augur reads the Forum's collective pattern and surfaces
emergent shapes (convergent attention on one brain-map node by
multiple ants).

- Module: `polaris_swarm/civitas/augur_bloom_reader.py`
- Civic class: `augur`
- Deposits: `observation_type=augur_convergent_attention`

The Augur never decides. The Senate (Sanctum) decides.

### Censores (Censors)

The magistrates who maintained the census — the official roll of
citizens, their property, their voting class. They updated the
roll on a fixed cadence; they were institutional memory.

In the swarm, the Censor maintains
`polaris_swarm/civitas/census-roll.json` — filesystem-AoR per
**G14** — tracking every ant's `first_seen`, `last_seen`,
`legion_at_birth`, and (when applicable) `retired_at`. Entries
are append-only-discipline: once an ant is in the roll, it stays
forever.

- Module: `polaris_swarm/civitas/censor_roll_keeper.py`
- Civic class: `censor`
- Deposits: `observation_type=census_birth | census_retirement`

## Recruitment: how the swarm grows

Two paths to new ants:

1. **Legatus authority** (v8.64): a Legatus can add an ant to
   its cohort without a Sanctum, as long as G6-G11 still pass.
   Recruitment is documented in
   `polaris_swarm/legions/legio_X.py::ANTS`.

2. **Proposal-driven autogenesis** (v8.66): a citizen (or
   future ant) can deposit `evidence.observation_type=proposal_new_ant`
   carrying a sketch. The proposal is **nominated** by the swarm;
   VANTA or a Censor **ratifies** by materializing the new ant
   file. This is the Roman ratification pattern — magistrates
   nominated by the people, ratified by the Senate.

**Literal autogenesis is forbidden** (G13). No citizen or ant
may directly spawn another at runtime. This preserves G6
(independence) and prevents unbounded growth.

## The architectural G-guards

The full family of architectural guards as of v8.66:

| Guard | Rule |
|---|---|
| **G1** | No `import random` / `numpy.random` under `polaris_hydra/` |
| **G2** | No `eval(` / `exec(` / `ast.literal_eval(` of model output |
| **G3** | Watchers are read-only (no fs mutation, no SQL mutation) |
| **G4** | Single shared `WatcherReport`/`Finding` schema |
| **G5** | No `.seek(` / `tail -f` subprocesses (watcher pushes; never tails) |
| **G6** | No ant ↔ ant imports (legion ants are siblings) |
| **G7** | Pheromone decay is deterministic (pure function) |
| **G8** | No LLM client imports in `polaris_swarm/` |
| **G9** | Pheromone table is append-only |
| **G10** | Every ant belongs to exactly one Legion |
| **G11** | Ants don't import from `polaris_swarm.legions` |
| **G12** | Citizens do NOT subclass `Ant` (parallel hierarchy) |
| **G13** | No literal autogenesis (proposal-pheromone-driven only) |
| **G14** | `census-roll.json` is filesystem-AoR (append-only-discipline) |

G1-G5 enforce the watcher contract (Arc D).
G6-G9 enforce the ant contract (Arc E E1-E2).
G10-G11 enforce the legion contract (Arc E E6).
G12-G14 enforce the civitas contract (Arc E E8).

## Two-phase deployment

`run_swarm()` (added v8.66) is the full two-phase deployment:

1. **Phase 1 — Legions deploy.** Each Legion deploys via its
   tactic; ants scan; findings collected; pheromones deposited.

2. **Phase 2 — Civitas observes.** Citizens read the recent
   pheromones (from DB, or in-memory from Phase 1's findings
   when `--dry`) plus the project corpus; civic findings deposited.

`run_colony()` (Phase 1 only) is preserved for backward
compatibility. CLI: `python -m polaris_swarm.colony --swarm`.

## Cross-references

- `MISSION.md` Arc E section — done-list E1..E8
- `ROADMAP.md` v13 section — R13-1..R13-8
- Sanctums opening / extending each phase:
  - v8.62 / E1: `sanctum/2026-05-13-arc-e-swarm-intelligence-opening.md`
  - v8.64 / E6: `sanctum/2026-05-13-arc-e-legion-structure-with-tactics.md`
  - v8.65 / E7: `sanctum/2026-05-13-arc-e-hydra-nine-heads-completion.md`
  - v8.66 / E8: `sanctum/2026-05-13-arc-e-civitas-civilian-classes.md`
- `DEVNOTES/audit-of-record.md` — the Mos Maiorum
- `meta/constraint-lattice.md` — the constitutional substrate
