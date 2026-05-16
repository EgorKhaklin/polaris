# Sanctum: arc-e-civitas-civilian-classes

**Date:** 2026-05-13
**Petitioner:** agent (Claude, Opus 4.7) speaking as the Architect
**Principal:** VANTA
**Trigger:** Metaphor expansion. VANTA: *"we need probably peasant class / worker class / upper class ants… these aren't part of the legions… ants make more ants… use roman civilization as a metaphor."*
**Risk class:** HIGH (new parallel abstraction layer; colony refactor; proposal-driven autogenesis as a constitutional mechanism)
**Status:** DECIDED
**Architect brief ID:** arch-2026-05-13

---

## I. The Matter

Expand Mycelium beyond legions to a full **Civitas**. Four civilian classes (Plebs, Equites, Augures, Censores) mapped to four genuine coverage gaps. Add proposal-driven autogenesis. Defer Cursus Honorum reputation.

## II. Preparation

**Polaris-as-Civitas mapping (already structurally true; now named):**

| Roman | Polaris |
|---|---|
| Senatus | Sanctum protocol |
| Capitolium | MISSION.md |
| Forum Romanum | Pheromone log + ai-swarm-bloom |
| Pomerium (sacred boundary) | C10 (identity ≠ money) |
| Mos Maiorum | Audit-of-record discipline |
| Legiones | 9 mortal Legions |
| Pontifices | CM, the immortal head |
| Limes (frontier) | TrajectoryWatcher |
| Lares et Penates | Per-domain Legion identities |

**The four civilian classes:**

- **Plebs** — cross-legion readers. `PlebsForumWatcher` reads recent pheromones, surfaces volume imbalances.
- **Equites** — cross-legion couriers. `EquesCorrelator` deposits correlated-drift findings when two un-allied legions fire near-in-time.
- **Augures** — pattern interpreters. `AugurBloomReader` finds brain-map nodes with ≥5 distinct ants firing; deposits "convergent attention."
- **Censores** — keepers of the roll. `CensorRollKeeper` maintains `census-roll.json` (filesystem AoR) tracking ant lifecycle.

**Autogenesis (proposal-driven):**

Roman ratification pattern. Citizens or ants deposit `kind=info, evidence.type=proposal_new_ant` carrying a sketch. VANTA reviews; if ratified, the proposal manifests. No literal spawning.

**Architecture:**

```
polaris_swarm/civitas/
├── __init__.py        (ALL_CITIZENS = 4)
├── base.py            (Citizen + CitizenFinding)
├── plebs_forum_watcher.py
├── eques_correlator.py
├── augur_bloom_reader.py
├── censor_roll_keeper.py
└── census-roll.json   (filesystem AoR)
```

**Two-phase deployment:** legions → ants deposit → citizens read pheromones + corpus → citizens deposit civic findings.

**Constitutional preservation:** G6-G11 unchanged. New: **G12** (citizens don't subclass Ant), **G13** (no direct autogenesis), **G14** (census-roll.json is append-only filesystem AoR).

## III. Alternatives considered

1. All four + proposal + defer Cursus (CHOSEN).
2. Two only — VANTA preferred full civic structure.
3. Just Augures — too narrow.
4. Literal autogenesis — rejected (G6 violation).
5. Cursus Honorum now — rejected (no history yet).

## IV. Recommendation

**All four + proposal-driven + defer Cursus.** Each class fills a real coverage gap; civitas is the right abstraction (parallel to legions, not replacing them); proposal-driven autogenesis honors Roman ratification; Cursus deferred because reputation needs data we don't have.

## V. What's needed from VANTA

Approved in-chat 2026-05-13 via AskUserQuestion:
- Q1: All four civilian classes
- Q2: Proposal-driven autogenesis
- Q3: Defer Cursus Honorum

## VI. Decision

All four civilian classes + proposal-driven autogenesis + defer Cursus Honorum — Polaris becomes a full Roman Civitas with 9 Legions + 4 civilian orders (Plebs/Equites/Augures/Censores)

## VII. Outcome

v8.66 shipped. 4 citizens added (parallel to legions); proposal-driven autogenesis mechanism installed (G13); two-phase run_swarm(); G12-G14 architectural guards; 5 new TestMyceliumCivitas invariants (122→127); meta/civitas.md ships complete Polaris-as-Civitas mapping; first colony run demonstrated emergent layer (Plebs aggregated 4 burst pheromones into 1 forum-imbalance observation). Cursus Honorum deferred to E9. See CHANGELOG ## v8.66 and journal/2026-05-13.md.

