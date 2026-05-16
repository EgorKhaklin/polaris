# polaris_swarm/legions/ — domain groupings of commander ants

11 legions group the 33 commander ants by domain. Each legion is a
Python module that declares its `ALL_ANTS` list and registers any
legion-level discipline.

For the individual ants see [`../ants/`](../ants/).

---

## What's here

13 files: `__init__.py` + `base.py` + 11 legion modules.

### Republican legions (9)

| Legion | Domain | Ant count |
|---|---|---|
| [`legio_schema.py`](legio_schema.py) | Schema invariants | 2 |
| [`legio_cognitive.py`](legio_cognitive.py) | Cognitive layer hygiene | 3 |
| [`legio_security.py`](legio_security.py) | Security surface | 1 |
| [`legio_mission.py`](legio_mission.py) | MISSION discipline | 2 |
| [`legio_adversary.py`](legio_adversary.py) | Adversary walks | 1 |
| [`legio_performance.py`](legio_performance.py) | Atlas + scaling | 2 |
| [`legio_trajectory.py`](legio_trajectory.py) | Shipping cadence | 3 |
| [`legio_substrate.py`](legio_substrate.py) | Primitive dependencies | 4 |
| [`legio_docs.py`](legio_docs.py) | Documentation discipline | 6 |

### Imperial legions (2 — added v8.71)

| Legion | Domain | Ant count |
|---|---|---|
| [`legio_praetorian.py`](legio_praetorian.py) | Palace guard observability | 3 |
| [`legio_engineer.py`](legio_engineer.py) | Process hygiene | 5 |

**Total: 33 commander ants in 11 legions.**

---

## What a legion is

A legion is **a domain plus the ants that observe it**. Each legion
module exports:

- `LEGION_NAME` — short identifier (e.g., `"legio_schema"`)
- `LEGION_DESCRIPTION` — one-line purpose
- `ALL_ANTS` — the list of Ant subclasses this legion contains
- `LEGION_DOCTRINE` — optional `LegionDoctrine` dataclass naming
  the tactic + tier structure (added v8.69)

The legion is the discovery unit: [`../colony.py`](../colony.py)
walks legions to find ants, not the ants directory directly.

---

## What a legion is NOT

- Not a Hydra head (that mythology was relocated to HYDRA watchers
  in v8.72; legions are now purely organizational)
- Not constitutional (legions can be added/removed; the swarm
  invariants are at C/G level)
- Not citizen-aware (citizens live in [`../civitas/`](../civitas/);
  legions are commander-only)

`polaris_swarm/legions/` is **how 33 ants are organized into 11
coherent domains** — the equivalent of "teams" in a software org,
sized so each team has 1-6 specialists.

---

## Constitutional contract

- **G6 (no inter-tier imports)**: legions do not import from
  HYDRA or polaris_web; they're pure swarm.
- **G16 (deterministic)**: legion `ALL_ANTS` lists are static;
  the swarm composition is reproducible across runs.
- Adding/removing a legion requires updating the relevant ant
  inventory + structural-invariants count tests.

---

## Adding a new legion

1. Create `legio_<name>.py` matching the existing template
2. Define `LEGION_NAME`, `LEGION_DESCRIPTION`, `ALL_ANTS`,
   optionally `LEGION_DOCTRINE`
3. Add legion module to `__init__.py`'s `ALL_LEGIONS`
4. Update CLAUDE.md state-map's swarm topology line
5. Run structural invariants — counts will need updating
6. Sanctum if the legion crosses an arc boundary
   (e.g., the v8.71 Imperial-legions ship had a Sanctum)
