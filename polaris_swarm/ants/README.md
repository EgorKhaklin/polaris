# polaris_swarm/ants/ — the Mycelium swarm's commander tier

33 commander ants (33 modules; 1 base file + `__init__.py`). Each ant
is an autonomous worker that scans one slice of Polaris's state and
deposits Pheromones into the substrate. Ants are the load-bearing
empirical observation layer; HYDRA reads what ants see.

For the soldier tier (8 lightweight disposable classes, v9.03+) see
[`../soldiers/`](../soldiers/).

For the citizen layer (Plebs, Equites, Augures, Censores, Quaestores,
Tribuni Plebis) see [`../civitas/`](../civitas/).

For the legion structure (commanders grouped by domain) see
[`../legions/`](../legions/).

---

## What's here

33 ants across 11 legions. Each `ant_<name>.py` is one module;
each module exports one Ant subclass. Discovered automatically by
[`../colony.py`](../colony.py) — no central registry to maintain.

### Republican legions (9 — pre-Imperial)

- **legio_schema** — schema invariants
  - `ant_aor_immutability` — audit-of-record append-only checks
  - `ant_fk_cascade_guard` — FK CASCADE policy enforcement
- **legio_cognitive** — cognitive layer hygiene
  - `ant_pattern_warmth` — pattern catalog journal mentions
  - `ant_todo_debt` — TODO/FIXME marker count
  - `ant_stale_script` — ai-*.sh scripts >60d unchanged
- **legio_security** — security surface
  - `ant_csp_health` — CSP literal in security.py
- **legio_mission** — MISSION discipline
  - `ant_mission_drift` — claims drift between MISSION + reality
  - `ant_done_list_arithmetic` — done-list count drift
- **legio_adversary** — adversary walks
  - `ant_adversary_walk_complete` — coverage of C1-C10
- **legio_performance** — atlas + scaling
  - `ant_atlas_endpoint_health` — /api/atlas/* responsiveness
  - `ant_test_gap` — modules without colocated test files
- **legio_trajectory** — shipping trajectory
  - `ant_recent_churn` — files modified in last 7d
  - `ant_changelog_gap` — files newer than latest CHANGELOG header
  - `ant_ship_burst` — historical date with ≥6 ships
- **legio_substrate** — primitive dependencies
  - `ant_substrate_catalog` — `DEVNOTES/substrate.md` ↔ reality
  - `ant_dependency_in_use` — packages used vs declared
  - `ant_build_freshness` — Rust + Python build artifact age
  - `ant_rust_toolchain` — `rust-toolchain.toml` pin currency
- **legio_docs** — documentation discipline
  - `ant_api_doc_coverage` — routes vs docs/reference/API.md entries
  - `ant_readme_counts` — every directory has a README
  - `ant_devnotes_ships_coverage` — major ships have DEVNOTES/ships entries
  - `ant_docs_structure` — docs/ subdirectory layout integrity
  - `ant_unbumped_version` — md docs referencing stale v8.X
  - `ant_release_velocity` — long-term cadence summary

### Imperial legions (2 — added v8.71)

- **legio_praetorian** — palace guard observability
  - `ant_principle_invariant` — PRINCIPLES.md ↔ structural-invariants
  - `ant_self_model_accuracy` — agent's claims about Polaris ↔ reality
  - `ant_legion_doctrine_health` — legion-doctrine modules well-formed
- **legio_engineer** — process hygiene
  - `ant_swarm_inventory_drift` — declared swarm inventory ↔ files
  - `ant_journal_silence` — gaps in journal cadence
  - `ant_proposal_stagnation` — proposals/ left dangling
  - `ant_brain_map_freshness` — brain-map.html ↔ source mtime
  - `ant_sanctum_outcome` — Sanctum sessions without §VII Outcome links

---

## Constitutional contract

- **C1 (audit append-only)**: every ant's `.scan()` produces
  Pheromone deposits via `Pheromone INSERT`; never UPDATE/DELETE.
  The `reject_pheromone_modification` trigger (v9.07) enforces.
- **C10 (value-pure)**: ants observe system-state metrics only;
  never holder PII; never identity-token contents.
- **G1 (deterministic)**: same input state → same Pheromone deposits.
  Verified by replay testing.
- **G3 (graceful)**: ant `.scan()` failures are caught by
  `_safely_observe()` in [`../colony.py`](../colony.py) — one ant
  crash never breaks the swarm pass.
- **G6 (no inter-tier imports)**: ants do not import from
  `polaris_hydra/` or `polaris_web/`. They observe via filesystem
  + DB SELECT only.
- **F4 (Cursus Honorum)**: ants accumulate denarii based on
  drift-resolution (rewards) and persistent-silence (penalties);
  see [`../civitas/treasury.py`](../civitas/treasury.py).
- **F5 (steady-state exemption)**: 9 ants in `STEADY_STATE_ANTS`
  are reward-and-penalty-neutral (their findings never "resolve").

---

## Adding a new ant

1. Pick a legion (or open a new one in [`../legions/`](../legions/))
2. Create `ant_<your_name>.py`:
   ```python
   from polaris_swarm.base import Ant, AntFinding, KIND_DRIFT
   from polaris_swarm.scan_filters import is_polaris_source  # v9.05+

   class AntYourName(Ant):
       NAME = "ant_your_name"
       DESCRIPTION = "<one-line purpose>"

       def scan(self) -> list[AntFinding]:
           findings: list[AntFinding] = []
           # Read state; don't modify.
           # Use scan_filters.is_polaris_source() for any rglob/walk.
           # Return findings with node_id = "<domain>:<key>"
           #   (see DEVNOTES/hydra-pheromone-integration.md for canonical domains)
           return findings
   ```
3. Add to the legion's `ALL_ANTS` list
4. Run `python3 -m polaris_swarm.colony --dry --ant ant_your_name`
   to smoke-test
5. Run `bash scripts/ai-test.sh` to confirm no structural-invariant
   regressions
6. CHANGELOG entry + journal entry per project convention

---

## What this directory is NOT

- Not the soldier tier (that's in [`../soldiers/`](../soldiers/);
  v9.03+; lightweight + disposable + F5-exempt)
- Not the citizen layer (that's in [`../civitas/`](../civitas/);
  Plebs/Equites/Augures/Censores/Quaestores/Tribuni Plebis)
- Not the legion structure (that's in [`../legions/`](../legions/);
  groups ants by domain)
- Not HYDRA watchers (those live in [`../../polaris_hydra/watchers/`](../../polaris_hydra/watchers/);
  HYDRA is the centralized lens; ants are the decentralized substrate)

`polaris_swarm/ants/` is **the empirical observation layer** —
where 33 deterministic workers continuously read Polaris's state
and emit findings into the substrate that HYDRA later synthesizes.
