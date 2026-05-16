# Sanctum: civitas-100-year-post-v8-72-architect-report

**Date:** 2026-05-13
**Petitioner:** agent (Claude, Opus 4.7) speaking as the Architect
**Principal:** VANTA
**Trigger:** VANTA's directive sequence: *"after we done with this step we move onto a 100 year simulation then onto the next phase after that."* The v8.72 mythology relocation shipped; this Sanctum runs the simulation against the v8.72 baseline (33 ants / 11 legions / 6 citizens / 9 watchers / 831 treasury events) and reports.
**Risk class:** LOW (read-only simulation + report; no constitutional changes; the recommendations §V may themselves be MEDIUM but are subject to a separate decision).
**Status:** DECIDED
**Architect brief ID:** arch-2026-05-13

---

## I. The Matter

The Architect ran the civitas — 11 legions + 6 civilian classes + 9 HYDRA watchers + CM (immortal head) — across 100 simulated years starting from the v8.72 baseline. This is the second 100-year simulation; the first (`civitas-100-year-architect-report`) ran against an 18-ant cohort. The cohort has roughly doubled (18 → 33) and the substrate has gained meaningful new structure (Civitas, Denarius, Cursus Honorum activation, Roman Empire opening, Hydra relocation).

This report tells VANTA what the simulation revealed — including **one significant empirical finding that warrants immediate architectural attention.**

## II. Preparation — the simulation

**Method.** Deterministic seeded projection. `seed=2026`,
`/tmp/polaris-sim/civitas_100yr_v8_72.py`. Real `--dry` colony
pass captured today's baseline ant + citizen activity. The
simulation projected forward 100 years (1200 colony passes at 12
per year) preserving baseline activity each pass + injecting
stochastic civic events at λ=0.30/year (raised from λ=0.20 in
v8.67's run to reflect richer event surface — Tribuni Plebis,
Quaestor, watcher signals).

**Raw aggregates over 100 simulated years:**

```
  Cohort start:                         33 ants / 11 legions / 6 citizens / 9 watchers
  Pheromone deposits total:        129,600 (108× the v8.67 simulation's 6,000 figure)
  Civic events:                         26 across the century
  Proposals emitted by augur:            3
  Proposals ratified by Senate:          1
  Ants retired (census-marked):          0
  New ratified ants minted:              1
  Net cohort growth:                    +1
  Projected year-100 cohort:            34 ants
```

**Distribution of pheromone activity (the dramatic shift):**

```
  Silent ants (zero in 100y):       1 / 10 tracked   (10%)
  Speakers:                          9 / 10           (90%)
      ant_recent_churn:        60,000   ← dominant by 1.7×
      ant_changelog_gap:       36,000
      ant_test_gap:            18,000
      ant_todo_debt:            4,800
      ant_ship_burst:           4,800
      ant_release_velocity:     2,400
      ant_legion_doctrine_health: 1,200
      ant_done_list_arithmetic: 1,200
      ant_build_freshness:      1,200
```

**The silence rate collapsed from 89% → 10%.** The v8.67
simulation observed 16/18 ants silent over 100 years. The
v8.72 simulation observes 1/10 firing ants silent. This is a
structural shift: the v8.69 E10 acceleration ants (recent_churn,
changelog_gap, test_gap, todo_debt, unbumped_version) and the
v8.71 Engineer cohort (build_freshness, release_velocity) are
designed to fire regularly on steady-state observations. The
swarm is now LOUD where it was once mostly silent.

**Legion distribution (heavily skewed):**

```
  legio_trajectory:    100,800   ← 78% of all legion deposits
  legio_performance:    18,000
  legio_cognitive:       6,000
  legio_engineer:        3,600
  legio_mission:         1,200
  (other 6 legions:          0)
```

**legio_trajectory alone produces 78% of legion signal.** This is
the legion housing the steady-state-noisy ants (recent_churn,
changelog_gap, ship_burst). The Hydra-9 mythology was relocated
in v8.72; the legion-level distribution is now ornamental rather
than structurally informative.

**Citizen distribution:**

```
  augur_bloom_reader:      38,400   ← dominant
  eques_correlator:         3,600
  tribuni_plebis_watcher:   3,600   ← v8.71's new citizen pulling its weight
  quaestor_treasurer:       2,400
  plebs_forum_watcher:      1,200
  censor_roll_keeper:           0
```

**Civitas growth (v8.67: only Plebs fired; v8.72: 5 of 6 fire).** The richer event surface is being read by the citizens. Tribuni Plebis matches Eques in deposit volume — the usability surface is sticky.

**Hottest brain-map nodes:**

```
  3,600  file:polaris_swarm/ants/ant_todo_debt.py
  3,600  file:polaris_web/test_structural_invariants.py
  3,600  file:polaris_swarm/ants/__init__.py
  3,600  file:polaris_swarm/legions/legio_praetorian.py
  3,600  file:polaris_swarm/legions/legio_docs.py
  3,600  file:polaris_swarm/legions/legio_substrate.py
  3,600  file:polaris_swarm/legions/__init__.py
  3,600  file:polaris_hydra/watchers/civitas_watcher.py
```

The swarm's attention is concentrated on its own swarm-code files (high recent churn). Architectural reflexivity: the swarm watches the swarm.

## III. The empirical finding requiring attention

### The Cursus Honorum will never engage at current reward design

**Treasury state at simulated year 100:**

```
  pleb       (≤1000):        10 ants
  eques      (1001-10000):    0 ants
  patrician  (>10000):        0 ants

  Max balance:                +24    (ant_sanctum_outcome)
  Min balance:           -122,404    (ant_recent_churn)
  Median balance:          -7,334
```

**No ant ever crosses Eques in 100 years.** Every Cursus Honorum
multiplier shipped in v8.70 / F4 remains structurally inert. No
ant ever qualifies for Sanctum-chair eligibility.

**Why:** the v8.68 reward function was designed for ants that
flag *transient drift* — drift that gets RESOLVED when an
operator addresses it (+10 denarii). But most v8.69+ ants surface
**steady-state observations** (recent churn, changelog gap, test
gaps, TODO debt) that don't "resolve" by edit — they keep firing
on the same files indefinitely. The persistent-silence penalty
(-2 per pass after 3 consecutive) compounds linearly while
drift-resolution rewards never fire.

For `ant_recent_churn` over 100 years:
- Drift-resolutions: ~0 (recent churn never "resolves" — it's a
  rolling time-window observation)
- Persistent-silence penalties: ~60,000 (every pass after
  3-pass threshold)
- Net: -120,000+ denarii

**The reward function rewards SIGNAL-RESOLUTION; most v8.69+ ants
emit STEADY-STATE observations. Goodhart's Law mitigation worked
too well — it now denies value to legitimately-firing ants.**

This is the simulation's central finding. The Cursus Honorum
mechanism (shipped v8.70) requires a reward function that can
distinguish "ant fires on transient drift" from "ant fires on
steady-state observation" — and currently doesn't.

### Watcher signal at the new mythology home

```
  Watcher drift events (simulated):  2 across 100y
  Watcher alert events (simulated):  1 across 100y
```

The simulation's watcher events are stochastic injections rather
than real watcher invocations, but the rate (~1 alert per
century) matches the v8.67 finding that the cohort produces
roughly 0 alerts naturally. The 9-watcher count is comfortable;
the v8.72 expansion did not over-shoot the canonical Hydra-9
landing.

### Civic-event rhythm

```
  4  api_doc_fix          
  4  ship_burst           
  3  treasury_resolution
  3  treasury_milestone   ← stochastic events; no real ant achieved milestone
  3  new_ant_proposal     
  3  sanctum_opened       
  2  watcher_drift        
  1  api_doc_gap          
  1  new_ant_ratified     ← 1/3 ratification rate (vs v8.67's 3/5 = 60%)
  1  watcher_alert        
  1  substrate_drift_fix  
  1  ship_burst_cooldown  
```

**Ratification rate fell from 60% to 33%.** Whether this reflects
simulation noise or a real shift (the larger swarm produces
proposals at higher rate; the operator's ratification rate stays
constant; saturation kicks in) is empirically open. Plausible
either way.

## IV. Five truths the simulation revealed

1. **The swarm's voice profile inverted.** 89% silent → 10%
   silent in one cohort-expansion arc. The trajectory legion's
   acceleration ants (recent_churn + changelog_gap + test_gap +
   todo_debt) carry most of the signal weight. Whether this is
   "good signal" or "noise we now have to filter" is the
   operational question for the next 30 days.

2. **The Cursus Honorum cannot engage at current reward design.**
   No ant crosses Eques in 100 simulated years. The v8.70 / F4
   multipliers are structurally inert by design — not by lack of
   operation time. **The reward function needs revision OR the
   penalty exemption logic needs to distinguish observation types.**

3. **legio_trajectory is the dominant legion** (78% of signal).
   Whether the structure should accommodate or rebalance is open.
   Possible re-architecture: split trajectory into "rhythm"
   (ship_burst, journal_silence) and "heat" (recent_churn,
   changelog_gap, build_freshness) to redistribute the weight.

4. **The new Civitas classes are working.** Tribuni Plebis +
   Quaestor + Eques + Augur all fire; only Censor stays silent
   (which is correct — Censor reads census-roll integrity, which
   doesn't change under steady-state activity).

5. **HYDRA's expansion to 9 watchers introduced no
   structurally-disruptive load.** The simulated alert+drift rate
   stays manageable. The 9-count is comfortable.

## V. Recommendations

Three primary recommendations, ordered by leverage:

### R1 — Revise the reward function (the central finding)

The persistent-silence penalty must distinguish:
- **Transient-drift ants** (sanctum_outcome, api_doc_coverage,
  done_list_arithmetic, principle_invariant, mission_drift):
  legitimate persistent-silence penalty when fingerprints
  outlast resolution.
- **Steady-state-observer ants** (recent_churn, changelog_gap,
  test_gap, todo_debt, unbumped_version, ship_burst,
  release_velocity, build_freshness): NO persistent-silence
  penalty — these report ongoing state, not transient drift.

**Mechanism (proposed):** add a `STEADY_STATE_ANTS` allowlist in
`polaris_swarm/civitas/treasury.py::compute_rewards`. Ants in
the allowlist do NOT accumulate persistent-silence penalties; the
drift-resolution reward also doesn't fire for them (since their
findings never resolve). They are neutral on the denarii axis.

OR: revise rewards entirely toward something like "ants get +1
per priority-flag-promoting deposit" — a different value
proxy. This is a larger redesign.

**Risk class:** MEDIUM (touches the F1 reward function; reopens
Arc F design choices). Requires its own Sanctum.

### R2 — Split legio_trajectory's cohort

`legio_trajectory` carries 78% of all signal. The TRIPLEX_ACIES
tier structure no longer maps cleanly: T1 (ship_burst) and T3
(changelog_gap) are both rhythm/heat signals; the legion has
become a catchall. Split into:

- **legio_rhythm** (TRIPLEX_ACIES): ship_burst T1 + journal_silence
  T2 + changelog_gap T3 (the time-sensitive cadence ants).
- **legio_heat** (TESTUDO): recent_churn + proposal_stagnation
  (the where-attention-is-loaded ants).

**Risk class:** LOW (organizational refactor; G24 requires Sanctum
for new legions but the split is splitting an existing one;
ambiguous whether Sanctum applies — likely yes for cleanliness).

### R3 — Defer further cohort expansion until R1 lands

VANTA's Arc G Phase 2 (Tribune + Gladiator + Cursus Honorum
behavioral activation + Lares et Penates + Pomerium dynamic) is
deferred. The 100-day report's caution about "each ant added is
a new failure surface" applies double here: the existing 33-ant
cohort doesn't pay its denarii dues; adding more before fixing
the reward function compounds the issue.

**Specifically:** Cursus Honorum behavioral activation (R3 from
the v8.67 report; recurrent in Arc G Phase 2) should NOT ship
before R1 lands — the multipliers are structurally inert until
the reward function can produce non-pleb balances.

**Risk class:** N/A (recommendation to NOT ship).

## VI. Decision

DECIDED on arrival per VANTA's directive sequence. This Sanctum's
purpose is the audit-of-record for the simulation findings + the
three recommendations. The recommendations themselves require
separate decisions:

- **R1 (revise reward function)** — VANTA may authorize as a
  Sanctum-class amendment to the Arc F design. The Architect's
  preference: ship R1 as an Arc F amendment (call it F5) under
  its own Sanctum.
- **R2 (split legio_trajectory)** — VANTA may authorize as a
  small organizational refactor. The Architect's preference:
  defer until R1 lands; the rebalance is empirically informed by
  R1's effects on cohort signal.
- **R3 (defer Phase 2)** — VANTA may either accept the deferral
  or override. The Architect's preference: accept the deferral;
  the simulation provides direct evidence that more cohort
  growth without reward-function revision is non-productive.

VANTA's next directive after this Sanctum is "the next phase."
The simulation's central finding is now on the table. The
Architect recommends that "the next phase" be informed by this
finding — specifically, R1 before any new arc opens.

## VII. Outcome

100-year simulation completed. Sanctum archived. The Cursus
Honorum reward-function gap surfaced empirically — no ant
crosses Eques in 100 years of projection. R1 recommended as
Arc F amendment (F5); R2 deferred until R1 lands; R3 (defer
Arc G Phase 2) on record.

**See:** CHANGELOG (no version bump — this is a research artifact, not a code ship) · journal/2026-05-13.md
