# meta/observer-map.md — every observer mapped to the artifact it watches

**Origin:** v9.30 Sanctum (`sanctum/2026-05-16-v9-30-seven-remaining-items.md`),
item 13. Mirrors `meta/watcher-predicates.md` and `meta/ant-predicates.md`
one layer up: instead of "what does this observer claim?", asks "what
does this observer watch, and is anything else watching the same
thing?"

**Status:** Analysis complete. Physical cuts of redundant observers are
deferred to a separate operator-routed amendment per
`meta/freeze-amendment-protocol.md` (the "9 mortal heads" pin from
v9.04 §III.2 is a constitutional ceiling that moves only by amendment
with stated cost, not by being bundled into a composite ship).

---

## Rule (item 13)

> Deduplicate the four parallel observation systems. Swarm, Hydra,
> civitas, foresight overlap. Treasury is watched by an ant, a civitas
> class, and a Hydra watcher. MISSION.md is watched by mission_watcher
> and ant_mission_drift. First step: map every observer to the artifact
> it watches, and where two or more watch the same artifact, keep one.

---

## The four observation systems

1. **Mycelium swarm** — 33 commander ants in `polaris_swarm/ants/`,
   each with a falsifiable predicate (per v9.24 T1#2). Continuous
   per-ant observation; writes to `Pheromone` table.
2. **HYDRA** — 9 watchers in `polaris_hydra/watchers/` + CM (the
   immortal 10th head). Per-session brief; reads pheromone + filesystem
   + DB; emits findings.
3. **Civitas** — 6 citizens in `polaris_swarm/civitas/`. Each citizen
   class observes one swarm-governance axis (Treasury, census, Cursus
   Honorum, etc.).
4. **Foresight** — single ForesightAgent in `polaris_foresight/`.
   Reads external_categories.txt + journal; emits Brief.

These four are NOT siblings. Mycelium is high-cadence empirical;
HYDRA is mid-cadence structural; Civitas is per-swarm-governance;
Foresight is forward-looking research. The dedup question: where do
two of them observe the SAME artifact?

---

## Observer-to-artifact map

| Artifact | Observers (multiple = overlap) | Canonical | Redundant |
|---|---|---|---|
| **Treasury balance / denarii ledger** | `ant_treasury_health` + `civitas_watcher` (HYDRA) + `Quaestor` (citizen) | ant + Quaestor (different cadences serve different purposes) | civitas_watcher (HYDRA layer just re-reads what Quaestor + ant already see) |
| **MISSION.md drift** | `ant_mission_drift` (swarm) + `mission_watcher` (HYDRA) | ant (continuous; catches per-edit drift) | mission_watcher (per-session; same predicate; AP1-self-observation) |
| **Cognitive layer health** | `cognitive_watcher` (HYDRA) | NONE — this watcher has no operator-load-bearing predicate per v9.28 watcher-predicates.md | cognitive_watcher (full cut candidate) |
| **Ship rate / file churn** | `trajectory_watcher` (HYDRA) | `pre-commit-scope-check.sh` (v9.24) | trajectory_watcher (same signal; pre-commit is the enforcement layer; trajectory is observation theater) |
| **Schema integrity** | `ant_aor_immutability` (swarm) + `schema_watcher` (HYDRA) + `polaris_sql/08_tests.sql` | schema_watcher (only one with live DB diff per v9.28 #4) | none — three layers observe different shapes of schema integrity |
| **Security posture** | `security_watcher` (HYDRA) + `ant_csp_health` (swarm) + structural-invariant tests | security_watcher (only one with runtime probe per v9.28 #4) | none — three layers observe different security shapes |
| **Performance** | `performance_watcher` (HYDRA) + `test_app.py::TestPerformanceBudget` | both — different shapes (continuous vs CI) | none |
| **Adversary signals** | `adversary_watcher` (HYDRA) | only observer | none |
| **Ant colony health** | `ant_colony_watcher` (HYDRA) | only observer | none — this watcher watches the swarm itself, no redundancy |
| **Foresight predictions** | `polaris_foresight/foresight_agent.py` | only observer | none |

---

## Findings

**4 confirmed redundant observers (HYDRA watchers):**

1. `civitas_watcher` — redundant with `ant_treasury_health` + Quaestor
2. `mission_watcher` — redundant with `ant_mission_drift`; predicate is
   AP1 (self-observation)
3. `cognitive_watcher` — no external-record predicate per v9.28
4. `trajectory_watcher` — same signal as `pre-commit-scope-check.sh`;
   observation without enforcement

**These are the same 4 watchers flagged DEPRECATION_CANDIDATE in
`meta/watcher-predicates.md` at v9.28.** This dedup audit independently
confirms the v9.28 classification using a different methodology
(observer-to-artifact mapping vs predicate-or-delete). Two independent
audits agreeing on the same 4 candidates IS the corroboration
escalation pattern from Hydra #2 working at the meta level.

---

## What v9.30 ships

This document. The audit. The map.

**What v9.30 does NOT ship:** the physical cuts of the 4 watchers.

**Why:** "9 mortal heads" is a constitutional pin from v9.04 Sanctum
§III.2 — pinned by `test_watcher_count_unchanged_at_nine` in
test_structural_invariants.py at line 8959. Per the v9.29
freeze-amendment-protocol, moving this ceiling from 9 → 5 requires
its OWN amendment with stated cost, routed through the external
referent. Bundling the cut into a composite v9.30 ship would launder
the constitutional amendment — the exact pattern the v9.29 Sanctum
caught.

The honest path: the v9.30 ship lands the AUDIT (this document) and
the predicate-or-delete + observer-dedup mechanism (v9.28's watcher-
predicates.md + this map). The operator routes a separate amendment
proposal through the external referent if/when ready to cut.

---

## Recommended amendment shape (for the operator's future routing)

When/if the operator routes the watcher-count amendment:

- **Ceiling:** HYDRA watcher count, pinned at 9 by v9.04 Sanctum
- **Old → New:** 9 → 5 (KEEP: schema, security, performance, adversary,
  ant_colony) OR 9 → 6 if cognitive_watcher gets a new external-record
  predicate
- **Cost:** the 4 cut watcher files + their TestClasses + ai-architect/
  ai-swarm-health references must be removed in the same amendment
  Sanctum (single recorded decision)
- **Counterweight from C2:** the v9.04 "9 mortal heads" line in
  MISSION.md or the relevant Sanctum gets updated to reflect the new
  count + the v9.30 amendment-trail line

This is recorded here so the future routing has a starting position
from this analysis — not a pre-authorized cut.

---

*Per v9.30 Sanctum item 13, 2026-05-16. Audit complete; physical
cuts deferred to operator-routed amendment per the v9.29 freeze-
amendment-protocol.*
