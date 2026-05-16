# polaris_swarm/civitas/ — the citizen layer

The Mycelium swarm has **three tiers**: commander ants
([`../ants/`](../ants/)) + soldier ants ([`../soldiers/`](../soldiers/))
+ **citizens** (this directory). Citizens are higher-order observers
that read the substrate the lower tiers create — they observe
the observers.

Six citizen classes ship in v9.x; their cohort doctrine is the
**Civitas** (Latin for citizenry; the political unit of Rome).
Constitutional source: [`../../meta/civitas.md`](../../meta/civitas.md).

---

## What's here

13 files: 6 citizen modules + 1 base + 1 init + 4 ledger/policy
files + 1 treasury implementation.

### Citizen classes (6)

| Citizen | Role | Notes |
|---|---|---|
| [`plebs_forum_watcher.py`](plebs_forum_watcher.py) | Plebs — the broad citizen body | Observes proposals/ + journal/ for civic activity |
| [`eques_correlator.py`](eques_correlator.py) | Equites — knights / cross-correlator | Reads multiple ant streams + correlates |
| [`augur_bloom_reader.py`](augur_bloom_reader.py) | Augures — soothsayers | Reads the bloom heatmap; emits prognostic signals |
| [`censor_roll_keeper.py`](censor_roll_keeper.py) | Censores — keepers of the roll | Maintains `census-roll.json` |
| [`quaestor_treasurer.py`](quaestor_treasurer.py) | Quaestores — treasurers | Maintains `treasury-roll.json` per F1 |
| [`tribuni_plebis_watcher.py`](tribuni_plebis_watcher.py) | Tribuni Plebis — guardians of the people | Watches CLAUDE.md complexity; alerts on cognitive overload |

### Treasury implementation

| File | Purpose |
|---|---|
| [`base.py`](base.py) | `Citizen` base class + `CitizenFinding` dataclass |
| [`treasury.py`](treasury.py) | F1 / Denarius reward function; `is_treasury_exempt()` predicate (v9.05+); STEADY_STATE_ANTS allowlist; F4 Cursus Honorum multipliers |

### Filesystem audit-of-record (v8.20 / G15)

| File | What |
|---|---|
| `treasury-roll.json` | Append-only-discipline ledger of denarii events |
| `census-roll.json` | Census Roll — citizen-class membership over time |

These two JSON files are **G15-protected**: existing entries stay;
balances are computed by summing, never stored. Per-ant exemption
logic in `treasury.py:is_treasury_exempt()` (v9.05+: extends F5
allowlist to soldier_* prefix per v9.03 Sanctum).

---

## What a citizen is

A citizen is **higher-order observer** — it reads the substrate
ants create and emits findings on top. Where an ant says
"X is happening", a citizen says "the pattern across X, Y, Z is..."
or "the swarm itself is in state W."

**Example:** `eques_correlator` reads ant findings across
multiple ants (similar to HYDRA's CorrelationEngine but emitting
into the same Pheromone substrate, vs HYDRA's lens-side synthesis).

---

## Constitutional contract

- **C1 / G15 (filesystem-AoR)**: `treasury-roll.json` and
  `census-roll.json` are append-only-discipline. Entries
  accumulate; balances are computed.
- **F1-F5 (Denarius / Cursus Honorum)**: the economic + tier-
  mobility model. F5 (v8.73) exempts `STEADY_STATE_ANTS`. v9.05
  / A1 extended the predicate to soldier_* prefix per the v9.03
  Sanctum's F5-soldier-exempt claim.
- **C10 (value-pure)**: citizens observe system-state metrics
  only; never holder PII.
- **G16 (deterministic)**: citizen scans are pure functions of
  the observed substrate.

---

## Adding a new citizen class

1. Define a citizen class extending `Citizen` in a new
   `<name>_<role>.py` module
2. Implement `.scan()` returning `list[CitizenFinding]`
3. Add to `__init__.py`'s `ALL_CITIZENS`
4. Open a Sanctum if the new class extends Civitas semantics
   (e.g., the v8.69 ship that introduced civilian classes had a
   Sanctum)
5. Update `meta/civitas.md` to document the new class's role

---

## What this directory is NOT

- Not commander ants (those are in [`../ants/`](../ants/);
  observe Polaris state directly)
- Not soldier ants (those are in [`../soldiers/`](../soldiers/);
  v9.03+; F5-exempt; lightweight)
- Not HYDRA watchers (those live in
  [`../../polaris_hydra/watchers/`](../../polaris_hydra/watchers/);
  HYDRA is the lens; citizens are the higher-order substrate observer)

`polaris_swarm/civitas/` is **the political dimension of the
swarm** — where higher-order observation, treasury, and tier-
mobility logic live.
