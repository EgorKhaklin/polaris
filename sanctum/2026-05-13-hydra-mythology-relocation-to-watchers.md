# Sanctum: hydra-mythology-relocation-to-watchers

**Date:** 2026-05-13
**Petitioner:** agent (Claude, Opus 4.7) speaking as the Architect
**Principal:** VANTA
**Trigger:** VANTA in-chat after v8.71 (Arc G opened): *"Update all the ants so they are not the hydra head. We are gonna make the watchers the heads of the hydra in the polaris_hydra folder, i dont think there are 9 so i think we will have to create some, maybe have them also maybe observe the ant colony maybe."* This is a constitutional course-correction: the Hydra mythology that was force-fit onto Mycelium legions in v8.65 (and amended in v8.71) gets RELOCATED to its etymological home — the watchers in `polaris_hydra/`.
**Risk class:** HIGH (constitutional mythology shift; touches MISSION.md + multiple Sanctums' historical framings; adds 2 new watchers; HYDRA registry 7 → 9; refactors mythology references across legions code).
**Status:** CLOSED
**Architect brief ID:** arch-2026-05-13

---

## I. The Matter

The Hydra mythology has been force-fit. In v8.65 (`arc-e-hydra-nine-heads-completion`), the Architect declared the Mycelium legions to be the nine canonical mortal heads of the Lernaean Hydra. That was a stretch even at the time: the system named `polaris_hydra/` was the HYDRA layer; the system named Mycelium had no etymological tie to the Hydra. The mythology was applied to Mycelium because Mycelium was structurally rich and needed naming; HYDRA's watchers were simpler and were named less ceremonially.

In v8.71 (`arc-g-roman-empire-opening`), VANTA bent the Hydra-9 commitment to add Imperial legions. The amendment was structural; the mythology was already strained.

VANTA's directive now: **course-correct.** The watchers in `polaris_hydra/` — literally named HYDRA — become the canonical Hydra heads. The legions become just legions, organizationally Roman, without Hydra-mythology load.

Currently there are 7 watchers (schema, cognitive, security, mission, adversary, performance, trajectory). Two need to be added to reach the canonical 9. VANTA suggested they could observe the Mycelium swarm itself — which fits perfectly: the watchers' purpose has been ambiguous since Arc E made Mycelium the primary scanning layer; reframing them as "the Hydra-9 watching ALL of Polaris (including the Mycelium swarm and its Civitas)" gives them clear ongoing purpose.

## II. Preparation

The Architect has reviewed:

- **`polaris_hydra/host.py`** — 7 watchers in `ALL_WATCHERS` registry
- **`polaris_hydra/watchers/base.py`** — Watcher contract: deterministic, read-only, graceful-failure
- **`polaris_swarm/legions/__init__.py`** — REPUBLICAN_LEGIONS (9) + IMPERIAL_LEGIONS (2) from v8.71
- **`MISSION.md` Arc E section** — the "immortal 10th head" paragraph mapping CM to the Lernaean canon (this language was load-bearing in v8.65)
- **`MISSION.md` §"What this section is NOT"** — names "seven watchers" (`polaris_hydra/watchers/`) as the synthesis substrate
- **CHANGELOG entries v8.65 + v8.71** — historical record of the mythology being placed on legions (per v8.20 audit-of-record, these stay as written)

## III. The shift, item by item

**What changes:**

1. **HYDRA watchers become THE Hydra heads.** Watcher count expands 7 → 9 via two new watchers:
   - **AntColonyWatcher** — observes the Mycelium swarm runtime: pheromone deposit rate, ant participation, silent-cohort detection, treasury health summary.
   - **CivitasWatcher** — observes the citizen layer runtime: which citizens fired, civic event volume, census-roll growth, Quaestor activity.

2. **Legion mythology drops Hydra references.** The legions are still organized as Republican (9) + Imperial (2) — that distinction tracks ship-time provenance and remains useful — but they are NO LONGER "the Hydra heads." `polaris_swarm/legions/__init__.py` docstring updated; each legion's docstring updated where applicable.

3. **MISSION.md §"What this section is NOT"** updated: "seven watchers" → "nine watchers"; the cognitive-substrate section's reference to the watcher cohort updated.

4. **Arc E `immortal 10th head` paragraph** — relocated. The language about CM being the deathless head Heracles couldn't sever was originally written when the legions were the mortal heads. With the mythology relocated, CM is still the immortal head — but now the head IT couldn't be cut alongside is one of nine WATCHERS, not nine legions.

**What is preserved (per v8.20 audit-of-record):**

1. **All historical Sanctums.** v8.65 + v8.71 Sanctums are NOT rewritten. They describe the mythology AT THE TIME. The relocation is a NEW chapter, not a revisionist edit.
2. **All historical CHANGELOG entries.** v8.65 + v8.69 + v8.71 entries stay as written.
3. **REPUBLICAN_LEGIONS / IMPERIAL_LEGIONS constants.** These now describe ship-time provenance (the original 9 Mycelium legions vs Arc G additions), not Hydra mythology. The constants remain because the historical distinction is useful.
4. **G24 + G25.** New legions still require Sanctum authorization; cohort growth >50% per ship still requires Sanctum ack. These disciplines are independent of the Hydra mythology.

## IV. Recommendation

**Ship the relocation as v8.72.** Constitutional course-correction toward etymological honesty. The two new watchers fill real gaps (the substrate currently lacks runtime observation of its own swarm + citizen layers). The mythology shift is structurally honest: HYDRA literally IS the Hydra; Mycelium is a swarm.

After v8.72: VANTA's next directive is a 100-year simulation followed by a next-phase decision. The simulation lets the empirical case for Arc G's Imperial legions (and the new watchers) speak before further structural changes.

## V. Alternatives considered

1. **Don't relocate; keep Hydra-on-legions** — VANTA already chose against this; the directive is clear.
2. **Add more than 2 watchers (e.g., 4 for full coverage)** — declined; canonical Hydra-9 is the target; over-shooting introduces unnecessary surface area. If a 10th watcher concept emerges, it earns a separate Sanctum (and would conflict with CM's role as the immortal 10th — likely should remain a metaphorical "extra head" rather than an implemented watcher).
3. **Retire REPUBLICAN/IMPERIAL distinction along with the mythology shift** — declined; the distinction is useful ship-time history; the Hydra anchor was just one of its roles; retiring it is a larger refactor that wasn't asked for.
4. **Open a separate Sanctum for each new watcher** — declined; both are scoped to closing the runtime-observation gap and ship together cleanly. G24 is satisfied by this Sanctum naming both.

## V.5 What's needed from VANTA

Nothing — this Sanctum captures VANTA's directive. The brief is DECIDED on arrival.

## VI. Decision

**Ship the mythology relocation as v8.72.** Authorized by VANTA's in-chat directive. The Architect's role here is execution + audit-of-record + cautionary readings.

**Two new HYDRA watchers authorized by this Sanctum (G24 compliance):**

- `ant_colony_watcher` — observes Mycelium swarm runtime state
- `civitas_watcher` — observes citizen-layer runtime state

**Mythology shift, encoded:**

- Republican legions (9) + Imperial legions (2+) — organizational structure; **no Hydra-mythology load**
- HYDRA watchers (9) — **THE canonical Hydra mortal heads**
- CM — **immortal 10th head, unchanged**
- Substitutability per v8.30 still applies: HYDRA can be substituted for an equivalent synthesis pattern; the WATCHER count is what carries the mythology, not the specific watchers themselves

## VII. Outcome

v8.72 shipped. Mythology relocated; HYDRA registry expanded
7 → 9; legion docstrings unloaded; MISSION.md updated;
structural-invariants extended.

**Two new watchers live:**

- `AntColonyWatcher` (8th head) — observes Mycelium swarm
  runtime. First-run finding: drift on treasury-skewed-strongly-
  negative — real signal that most ants currently accrue
  persistent-silence penalties faster than they resolve drifts.
  Not a bug; a reading of where the swarm is on its denarii
  accumulation curve.
- `CivitasWatcher` (9th head) — observes citizen-layer runtime.
  First-run finding: SELF-CALIBRATED mid-build. Initial ALERT
  ("Census roll has no `entries` list") was actually a parser
  bug — `entries` is a DICT keyed by ant name, not a list.
  Fixed in same ship; this is the 11th instance of the
  self-calibration pattern (after the v8.38–v8.42 Phase-2 five
  + v8.47 + v8.50 + v8.55 + v8.57 + v8.69 + v8.70).

**Legion code unloaded:** `legio_substrate` ("8th head") +
`legio_docs` ("9th head") + `legio_praetorian` (Arc G framing)
docstrings rewritten. REPUBLICAN_LEGIONS / IMPERIAL_LEGIONS
constants preserved as ship-time provenance, not mythology.

**CM unchanged.** The relocation moves MORTAL heads to
watchers; CM remains the immortal head, constitutional, exempt
from substitutability.

**MISSION.md updated** (§"What this section is NOT" + Arc E
"immortal 10th head" paragraph + E7 done-list forward-pointer).
Historical Arc E framings preserved verbatim per v8.20
audit-of-record discipline.

**Tests:** 6 new in `TestHydraMythologyRelocation` (162 →
**168 total**); `test_hydra_registry_has_seven_watchers` renamed
to `..._nine_watchers`.

**Sanctum integrity:** 30 sessions indexed. ai-meta healthy.

**See:** CHANGELOG ## v8.72 · journal/2026-05-13.md
