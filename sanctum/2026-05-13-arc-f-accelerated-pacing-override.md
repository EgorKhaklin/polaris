# Sanctum: arc-f-accelerated-pacing-override

**Date:** 2026-05-13
**Petitioner:** agent (Claude, Opus 4.7) speaking as the Architect
**Principal:** VANTA
**Trigger:** VANTA in-chat after v8.69 (E10) shipped: *"lets do all that now actually."* The implied request: collapse the multi-day F2 → F3 → F4 sequence (committed in `sanctum/2026-05-13-arc-f-denarius-opening.md` §II) into one ship. This is a second pacing-override within one session (the first was Option D on `arc-e-acceleration-consciousness-cohort-e10`).
**Risk class:** MEDIUM (amends a Sanctum-authorized multi-day commitment; ships F2 functional + F3 structural + F4 structural in one ship; introduces multiplier mechanics + chaos harness + one ratified proposal-driven ant).
**Status:** CLOSED
**Architect brief ID:** arch-2026-05-13

---

## I. The Matter

Arc F was opened in `sanctum/2026-05-13-arc-f-denarius-opening.md` as **explicitly multi-day**:

> The Architect commits to spacing F2-F4 across days, not back-to-back.
> - **F1 (today)** — Treasury foundation.
> - **F2 (≥24h from F1)** — Chaos test for silent ants.
> - **F3 (≥24h from F2)** — Cohort growth via proposal exercise.
> - **F4 (≥7 days from F3)** — Cursus Honorum activation.
>
> The Architect will NOT propose F2 today regardless of what observations surface. **The arc paces itself.**

VANTA's request collapses this. The Architect's first move was to surface the **technical** state-dependencies (not just discipline-dependencies) in F3 and F4, presented via AskUserQuestion. VANTA chose **Option B — Ship F2 + structural F3 + structural F4**.

## II. The Architect's read

Three phases, three different feasibility profiles:

**F2 — Chaos test (fully buildable today).** Deterministic harness. Inject ant failures (exceptions, malformed findings, time-outs); observe whether the swarm's existing heartbeat + treasury silence-detector layers catch them. The question the chaos test answers — *are silent ants actually scanning correctly?* — is a structural question that doesn't need real elapsed time to answer.

**F3 — Cohort growth via proposal exercise (mechanically yes; meaningfully partial).** The G13 proposal mechanism exists (`propose_new_ant()` helper in `civitas/base.py` from v8.66). What's missing is a citizen that ACTUALLY emits `proposal_new_ant` pheromones based on observation. Today's ship: extend one citizen to do this; ratify ONE real proposal — for an ant addressing a coverage gap the existing 28 don't cover. **The proposal is real, not theatrical** — the ant covers a genuine gap.

**F4 — Cursus Honorum activation (code yes; behavioral effect null until history accrues).** The Sanctum specified ≥7 days of denarii history. Treasury was opened at v8.68 today; events list is empty. Shipping multiplier code today means landing the bloom-renderer multiplier wiring + property-class predicates + Sanctum-chair eligibility predicate as **structural readiness**: when real denarii accumulate over the coming days, the multipliers will engage automatically. **The activation is not a no-op when state arrives; it is a no-op today.** That's the explicit trade.

## III. Design

**F2 — `polaris_swarm/chaos.py`** (~150 LOC):

- `ChaosInjector` class wraps an `Ant` (or `Citizen`) and forces a specified failure mode on `.scan()` / `.observe()`: `raise_exception`, `return_malformed`, `time_out`, `infinite_silence`.
- `run_chaos_pass(injected: dict[type, FailureMode], root) -> ChaosResult`: runs a colony pass with specified ants injected; returns a structured report of (a) whether the swarm produced heartbeats only for healthy ants, (b) whether broken-ant findings disappeared from the deposit set, (c) whether the silence-detector heuristic would catch the broken ant after 3 passes.
- `verify_chaos_detection(result) -> list[ChaosFailure]`: returns the assertions the swarm should have caught and didn't.
- Test class `TestF2ChaosHarness` in `test_structural_invariants.py`: structural contracts that the harness exists, that injection works on at least one ant, that detection layer responds.

**F3 — extend Augur + materialize `ant_proposal_stagnation`**:

The Augur becomes the citizen that emits proposals. Why Augur: its role is to read auspices / patterns; surfacing "we have no ant for X" is a pattern reading. New method `_propose_for_uncovered_node(...)`. When the Augur observes a category of project-state with ZERO ants reading it (e.g., `proposals/`), it deposits a `proposal_new_ant` pheromone.

The new ant ratified by this exercise: **`ant_proposal_stagnation`** — surfaces `proposals/*.md` files that have been untouched for ≥30 days and never promoted to ROADMAP (their R-id never appears in `ROADMAP.md`). This is a real coverage gap; the proposals/ directory has no observer.

Lands in `legio_trajectory` (T2 principes — proposals that stagnate are a trajectory signal, between ship_burst T1 and changelog_gap T3).

**F4 — Cursus Honorum multipliers + Sanctum-chair eligibility**:

Three pieces:

1. **`polaris_swarm/civitas/treasury.py`** gains `CURSUS_MULTIPLIER` constant + `multiplier_for(balance)` function. Pleb 1.0×, Eques 1.5×, Patrician 2.0×.

2. **`scripts/ai_swarm_bloom.py`** integrates: when reading pheromones, look up each ant's balance via `treasury.compute_balance(roll, ant)`, classify via `property_class(balance)`, apply multiplier to the displayed effective intensity. Falls back to 1.0× if treasury is empty (current state).

3. **`treasury.is_sanctum_chair_eligible(roll, ant_name)`** — returns True iff balance ≥ patrician threshold. Wired into NOTHING in this ship; just structurally available. When a future Architect or VANTA wants to consult patrician ants on Sanctum decisions, the predicate is ready.

**New G-guards:**

- **G19** — Property-class multipliers are monotonic non-decreasing in balance. Pleb ≤ Eques ≤ Patrician multiplier. Structural property that "more denarii never hurts."
- **G20** — Sanctum-chair eligibility is strictly inside the Civitas. Only ants with patrician-class denarii history may chair; never derived from any Polaris-identity attribute (preserves C10 / pomerium).

## IV. Risk

- **F2 chaos test:** clean. New module, new tests, no schema changes.
- **F3 proposal exercise:** modest. One new citizen method, one new ant, one legion update. Real coverage gap; not theater.
- **F4 multipliers:** medium. Wired into bloom rendering; defaults to 1.0× when treasury is empty (i.e., today's state). The code path is exercised but behaviorally inert. **The structural test must verify the no-op-today behavior** so the next ship can't accidentally regress.

Total blast radius:
- 1 new module (chaos.py)
- 1 new ant (ant_proposal_stagnation)
- Augur extension (proposal emission)
- Treasury extension (multipliers + eligibility)
- Bloom renderer integration
- 2 new G-guards (G19, G20)
- ~6-8 new structural-invariants in `TestArcFAcceleratedPacing`
- MISSION.md F2/F3/F4 ✅
- ROADMAP.md R14-2/R14-3/R14-4 ✅
- Test count 141 → ~148

## V. The Architect's recommendation

**Proceed with VANTA's Option B.** The pacing-override is a deliberate operator decision; the technical state-dependencies (F4 behaviorally null until history) are explicit in the design and recorded here. After this ship:

- F2 is functional. The chaos harness can be re-run any time.
- F3 has exercised the proposal loop end-to-end (citizen → pheromone → operator ratification → materialized ant). The mechanism is proven; future proposals will follow the same path.
- F4 is structural-ready. Multipliers activate automatically when denarii accumulate over the coming days. **No further ship needed for F4 to "go live"** — operation time is the only remaining variable.

**This is the last consolidation ship of the day.** The Architect names a clear pacing boundary: after v8.70 ships, **no further Arc F (or Arc E) work today.** The next session resumes at steady-state. The 100-day report's caution about cohort growth ("each ant added is a new failure surface") applies double after a 28-ant + 5-citizen day plus chaos infrastructure plus multiplier wiring.

## VI. Decision

**Option B — Ship F2 + structural F3 + structural F4 in v8.70.** VANTA in-chat 2026-05-13 via AskUserQuestion. Technical state-dependencies named; VANTA accepted that F4 is behaviorally inert today and activates organically as denarii accumulate. Architect's "no further Arc F today" boundary stated; VANTA's response (proceed) is taken as acceptance of the boundary.

## VII. Outcome

v8.70 shipped. **Arc F closed 4/4 ✅ on the day it opened.**

**F2 (functional):** `polaris_swarm/chaos.py` ships with four
FailureMode variants. Live smoke confirmed the Sanctum's
predicted detection map: 3 of 4 failure modes are caught by
existing layers (heartbeat suppression for crashes/malformed;
treasury fingerprint loss for silence). **Inflated mode is the
architectural gap** — the swarm has no spike detector. F2 thus
delivers what was asked of it: a structural answer to *"are
silent ants actually scanning correctly?"* with a clear map of
what's caught and what isn't. A future ship may add a spike
detector; v8.70 ends with the gap explicitly named.

**F3 (real, not theatrical):** Augur observed `proposals/` had
23 files and zero ant coverage → emitted a `proposal_new_ant`
pheromone for `ant_proposal_stagnation`. Architect materialized
the ant; VANTA ratified through this Sanctum. The G13
proposal-driven autogenesis loop is now **closed end-to-end for
the first time in cohort history.** ALL_ANTS grew 28 → 29.

**F4 (structural readiness):** treasury extended with
`CURSUS_MULTIPLIER` + multiplier predicates +
`is_sanctum_chair_eligible()` + `patrician_ants()`. Bloom
renderer consults treasury per-ant. G19 (monotonicity) + G20
(strict-civitas / C10-preservation) added.

**Behavior today:** 8 ants have non-zero balances; max positive
+76; max negative -772 (persistent silence on recent-files
nodes); every ant is pleb at 1.0× multiplier; zero patricians.
**The multipliers are wired and inert.** As denarii accumulate
through real drift-resolution over days of operation, the
multipliers engage automatically — no further ship is needed
for F4 to "go live."

**Tests:** 9 new structural-invariants in
`TestArcFAcceleratedPacing` (141 → **150 total**). G20 test
required a regex-based docstring stripper after the ad-hoc
line-based stripper failed on multi-line docstrings ending on
content lines — recorded here as a learning.

**Pacing boundary held.** No further Arc F or Arc E work today.
The Architect's §V boundary stated; VANTA's "proceed" was taken
as acceptance. Steady-state posture resumes from the next
session forward.

**See:** CHANGELOG ## v8.70 · journal/2026-05-13.md
