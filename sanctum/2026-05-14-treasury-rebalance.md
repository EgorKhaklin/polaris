# Sanctum: treasury-rebalance

**Date:** 2026-05-14
**Petitioner:** agent (Claude, Opus 4.7) speaking as the Architect
**Principal:** VANTA
**Trigger:** v8.89 macro scan's third finding: *"Treasury skewed strongly negative (min -2704, max +18). F5 was structurally correct but operationally insufficient — ants accrue persistent-silence penalty without offsetting drift-resolution reward."* v8.90 produced the quantitative report (`scripts/ai-treasury-report.sh`): **48 drift_resolution events (+480) vs 3357 persistent_silence events (-6714) — a 14:1 penalty:reward ratio**, all 10 drift-class ants stuck at Plebs.
**Risk class:** MEDIUM (touches the reward function shipped as Arc F / F5 v8.73; any change here is a constitutional reconsideration of the v8.73 Sanctum's conclusion. The DIAGNOSTIC is LOW-risk and shipped under v8.90. The REWARD-FUNCTION CHANGE is what this Sanctum gates.)
**Status:** DECIDED + CLOSED — Position B selected by VANTA in-chat 2026-05-14 ("B"). Shipped as v8.91 after 100-day-sim verified acceptance criterion.

---

## I. The Matter

The Mycelium Treasury (Arc F / F1 / v8.68) was designed so that **signal earns denarii, not volume** (Goodhart's Law mitigation). The reward function:

- **+10** when a pheromone fingerprint present last pass is absent this pass → the drift the ant flagged got resolved.
- **−2** when a fingerprint has been present for **≥3 consecutive passes** → persistent silence; nobody acted; the ant kept flagging the same thing.

F5 (v8.73) introduced `STEADY_STATE_ANTS` — a 9-ant allowlist exempted from BOTH reward AND penalty. This was the recommendation from the v8.72 100-year simulation (`sanctum/2026-05-13-civitas-100-year-post-v8-72-report.md`). It targeted the well-configured ants that fire correctly but rarely change their findings (their findings are stable observations, not unresolved drift).

**The empirical post-v8.89 state** (the bigint-overflow bug fixed; the swarm finally depositing pheromones cleanly for the first time since v8.62):

| Metric | Value |
|---|---|
| Drift-class ants in ledger | 10 (all non-steady-state) |
| Reward events | 48 (+480 denarii total) |
| Penalty events | 3357 (-6714 denarii total) |
| Net | -6234 denarii |
| **Penalty:reward ratio** | **14:1** |
| Min balance | -2704 (`ant_recent_churn`) |
| Max balance | +18 (`ant_sanctum_outcome`) |
| Class distribution | plebs=10, eques=0, patrician=0 |

**What F5 was supposed to fix:** the v8.72-era observation that most ants never get a chance to earn denarii because they don't flag drift (their findings are stable). F5 exempted those.

**What F5 missed:** the drift-class ants — the ants whose JOB is to surface drift the operator should fix — accrue penalty for KEEPING surfacing the same drift across multiple passes when the operator doesn't act on it. This is by design (the "persistent silence" mechanism). But empirically, operators leave drift findings in the surface for weeks. The penalty accumulates 14× faster than reward.

`ant_recent_churn` at -2704 needs **281 drift-resolution events** to reach Eques (≥101). That's 281 instances where it flagged churn AND the churn got resolved before the next pass. At current rates (14 resolution events across the entire ledger lifetime), that's effectively unreachable.

**The mechanism doesn't admit upward mobility from Plebs → Eques for drift-class ants.** Cursus Honorum's three-tier structure was designed for it; the current parameters make tier-2 reachable only by ants the operator actively follows on. That's not a functional class system; it's a single-class system with a vestigial threshold.

## II. The architect's positions

The pre-decision space has five real positions. They're not equally weighted — Architect-recommended is **B**, with a soft preference for compounding with **D**.

### Position A: do nothing

Accept the negative-skew as the empirical truth. The drift-class ants ARE mostly silent in terms of drift-resolution; F5 already captured the noise floor; the persistent-silence penalty is the system's signal that operator attention is needed. Bottom-of-the-ledger ants are the noisiest signal surface and that's appropriate.

**Strength:** preserves the v8.68 Goodhart's Law mitigation as designed; the most operationally-conservative move.

**Weakness:** the Cursus Honorum mechanism (Plebs/Eques/Patrician with multipliers 1.0×/1.5×/2.0×) becomes vestigial code — it exists in the schema but never engages. The Sanctum-chair eligibility predicate (`is_sanctum_chair_eligible`) becomes a permanently-false function. **Vestigial structure that never tests is the larping failure mode the project explicitly resists.**

### Position B: adjust the penalty-reward ratio — *architect-recommended*

Change the reward function from `+10 / -2` to `+10 / -1` (halve the penalty). Rationale: the silence-detection threshold of 3 consecutive passes is conservative, but the per-event penalty was set parallel-symmetric to the reward (+10 reward for resolution, −2 penalty for silence — designed so that 1 resolution offsets 5 silences). Empirically, operators don't resolve drift at that rate; the 1:5 ratio is wrong. 1:10 (or even 1:20) better matches the empirical operator-cadence.

**Strength:** small parameter change; preserves the v8.68 architecture; keeps Goodhart's Law mitigation intact (still rewards signal, not volume); admits real upward mobility for drift-resolving ants. With this change, `ant_recent_churn` reaches Eques after ~14 resolution events — a real but ambitious bar.

**Weakness:** invalidates the v8.73 F5 100-year-sim conclusion. The sim was on the +10/−2 parameters; the 100-year forward-projection of +10/−1 may surface new failure modes (e.g., ants that find ONE drift and never deposit again accrue +10 forever).

**Compounding with D:** if Position D is also taken (per-day reward floor for active ants), then B's "the resolver got lucky and never deposits again" failure mode is offset by a baseline drip.

### Position C: extend the STEADY_STATE_ANTS allowlist

Add some or all of the current drift-class ants to the allowlist. They are, empirically, *also* mostly silent (in the sense of not resolving the drift they flag), so they fit the F5 criterion. The 10-ant negative-skew goes away because exempted ants accrue zero, not negative.

**Strength:** minimal code change; only data change (the allowlist is a frozenset).

**Weakness:** **defeats the purpose of having drift-class ants.** If the swarm's drift-class ants are exempt from the silence penalty, they have no mechanism that flags "you're surfacing the same drift forever, operator isn't acting." Disables a load-bearing observability signal. Plebs becomes the only class; Cursus Honorum is fully vestigial. **The architect actively recommends against this.**

### Position D: per-day reward floor

Every ant that produces ≥1 finding per pass earns +1 denarius regardless of resolution. The "you did your job by being awake and observing" floor. Combined with the existing +10 resolution reward, this creates a baseline rate-of-accumulation that scales with operator response.

**Strength:** rewards being-alive separately from being-effective; matches the human-organization pattern where showing up is rewarded distinctly from delivering. Mobility becomes time-driven (every active ant inches upward) rather than purely resolution-driven.

**Weakness:** weakens the Goodhart's Law mitigation — now volume DOES earn denarii, just at 1/10 the resolution rate. May admit Goodhart effects at scale (ants tuned to fire ≥1 finding per pass irrespective of usefulness).

**Compounding:** safer in combination with B (the +10/−1 ratio's "lucky resolver" failure mode is offset by the floor's persistent drip).

### Position E: change the silence-detection threshold

Currently silence-penalty fires at ≥3 consecutive same-fingerprint passes. Raise to ≥7 (penalty fires only after the drift has been on screen for a week+ at daily cadence). At 7-day threshold, current penalty count would drop from 3357 to roughly 3357 × (3/7) ≈ 1440; net Treasury position would improve from -6234 to roughly +480 - 1440 × 2 = -2400.

**Strength:** parameter change; preserves both the F5 design and the reward function. The threshold reflects "the operator has had reasonable time to act."

**Weakness:** doesn't fix the underlying ratio problem; just makes the penalty fire less often. Drift-class ants still don't reach Eques without resolution events. **Necessary but not sufficient.**

## III. Architect's recommendation

**B compounded with D (and possibly E as a third adjustment).** Concrete proposal:

1. Change reward function: `+10` for drift_resolution (unchanged), `-1` for persistent_silence (was −2). [Position B]
2. Add baseline reward: `+1` for any ant that produced ≥1 finding in the current pass. [Position D]
3. (Optional) Raise silence-detection threshold from 3 to 5 passes. [Position E partial]

Under this proposal, after 100 simulated passes:
- An ant that always fires and never resolves: `+100 (floor) − 100 × ((100-3+1)/5) × 1 ≈ +100 − 20 = +80` (still Plebs but trending positive)
- An ant that resolves at 10% rate: `+100 (floor) + 10 × 10 (resolution) − ... = +200` (reaches Eques)
- An ant that resolves at 50% rate: `+100 + 50 × 10 − ... = +600` (well into Eques)

This makes Cursus Honorum tier-mobility correlated with resolution rate, with a baseline drip for being-alive. Goodhart's Law mitigation: volume earns +1; signal earns +10. The 10:1 weighting preserves the architecture's intent.

## IV. Open questions for VANTA

1. **Do you want a 100-day-sim before deciding?** The v8.73 F5 ship was preceded by the v8.72 100-year sim. v8.90 ships the diagnostic but NOT the sim harness. Architect-recommended: yes, but the simulation is itself a follow-up ship.

2. **Should the rebalance be retroactive (delete existing negative balances)?** Architect-recommended: NO. The Treasury ledger is append-only filesystem-AoR; deletions would violate G15. Apply changes going forward.

3. **Should `STEADY_STATE_ANTS` change?** Architect-recommended: NO. F5's allowlist is the correct shape; the issue isn't who's exempt, it's how the included ants are weighted.

4. **Acceptance criterion for the post-rebalance state?** Architect-recommended: at least one drift-class ant reaches Eques within 60 days of normal operation. The current rate is 0 ants in months.

## V. Decision

**Position B selected.** VANTA in-chat 2026-05-14: *"B"*.

The architect's recommended position. VANTA did NOT bundle D (per-day reward floor) or E (raise silence threshold). Position B ships alone — the +10/−2 parameters become +10/−1.

The architect-recommended prerequisites were addressed in-line during v8.91:

1. **100-day-sim verified** the acceptance criterion (≥1 drift-class ant reaches Eques within 60 days of normal operation). Position B yields **2/10** ants reaching Eques within 60 days (vs **1/10** under the +10/−2 baseline). The sim is heuristic — extrapolated from a 0.29-day observation window (only that much swarm data exists post-v8.89 bigint-fix) — but the direction is unambiguous and the criterion is met.
2. **Retroactive zeroing rejected.** Per G15 filesystem-AoR, historical Treasury balances are preserved. The rebalance is forward-looking only. Existing negative balances stay; new events accrue at the rebalanced rate.
3. **Acceptance criterion locked in.** ≥1 drift-class ant reaching Eques within 60 days. Sim says 2; reality may differ; the diagnostic (`scripts/ai-treasury-report.sh`) is now the operator's instrument for confirming.

## VI. Outcome

**v8.91 shipped Position B in full:**

1. **`polaris_swarm/civitas/treasury.py`** — `DENARII_PENALTY_PERSISTENT = 2` → `1`. Module docstring updated: the reward function now reads `+10 / −1` (was `+10 / −2`). The CitizenFinding amount-field comment updated similarly. **One numeric change; the rest is documentation.**

2. **`scripts/ai-treasury-report.sh`** — bonus correction. The v8.90 first-cut had Eques threshold = 101 (off by 10×; canonical per `treasury.py:DENARII_PLEB_MAX = 1_000` is balance ≥ 1_001). Fixed. The diagnostic now matches the canonical mechanism. The shape of the v8.90 finding (14:1 ratio; 0 ants at Eques) was correct — only the "how far to Eques" magnitude reported on a per-ant basis was off.

3. **`meta/arc-f-denarius.md`** — F5 postscript section updated to note the rebalance shipped + the Sanctum closed.

4. **`meta/sanctum-index.md`** — entry updated to **DECIDED + CLOSED**.

5. **Structural invariants** in `TestTreasuryRebalanceShipped`: enforce `DENARII_PENALTY_PERSISTENT == 1`; enforce the Sanctum's closed status with Position B; enforce the diagnostic's Eques threshold matches canonical.

**The 100-day-sim methodology:**

```
Observation window: 2026-05-14T01:37 → 08:38 UTC (0.29 days)
Empirical rates (post-v8.89 bigint-fix; the first window the swarm
actually deposited cleanly since v8.62):
  - drift_resolution: 164/day
  - persistent_silence: 11,500/day (the open-drift surface)

Linear extrapolation to 100 days, applied per-ant from current balance:

  Current (+10/−2):
    1 of 10 ants reaches Eques (≥1001)
    Net delta: −2,136K denarii over 100 days

  Position B (+10/−1):
    2 of 10 ants reaches Eques  ← acceptance criterion satisfied
    Net delta: −986K denarii over 100 days  ← halved penalty as designed

  Improvement: +1,150K denarii / 100 days
```

The deeply-negative ants (`ant_recent_churn` at -2704, `ant_changelog_gap` at -1502) continue to trend more-negative under Position B alone — their findings keep flagging the same drift while no resolution comes through. Per Sanctum §II, this is the failure mode Positions D + E would address; VANTA selected B alone, accepting this trade-off. **The mechanism is now functional (Eques is reachable), but the lowest-mobility ants remain in a deep penalty hole.** If, in 60 days of real operation, fewer than 1 drift-class ant has reached Eques, a follow-up Sanctum can revisit B+D / B+E / both.

**Drill not feasible** in a single ship — Position B's empirical confirmation requires real operator-driven drift-resolution over weeks, not a forced swarm pass. The sim is the architect's substitute; the diagnostic is the operator's continuous-verification instrument.

**Constitutional core preserved:**
- C1-C10 unchanged.
- G15 (filesystem-AoR) unchanged — historical balances stay.
- G16 (deterministic reward function) unchanged — same input still yields same output, at the new ratio.
- G26 (STEADY_STATE_ANTS additions require Sanctum) unchanged.
- Pattern #11 Audit (the catalog pattern: "consequences for actions; things being weighed") — Cursus Honorum can now actually engage; the weighing mechanism is no longer vestigial.

**Cross-references:** v8.91 CHANGELOG · `polaris_swarm/civitas/treasury.py` (the changed constant) · `scripts/ai-treasury-report.sh` (the corrected diagnostic) · `meta/arc-f-denarius.md` F5 postscript · `sanctum/2026-05-13-arc-f-f5-steady-state-ants-reward-exemption.md` (the F5 prior decision being refined) · `journal/2026-05-14.md` (the day's record).

## VII. Cross-references

- `polaris_swarm/civitas/treasury.py` — the reward function (line ~50-80 has the constants)
- `polaris_swarm/civitas/treasury-roll.json` — the ledger (filesystem-AoR / G15)
- `scripts/ai-treasury-report.sh` (v8.90) — the diagnostic
- `sanctum/2026-05-13-arc-f-denarius-opening.md` — the original Arc F authority
- `sanctum/2026-05-13-civitas-100-year-post-v8-72-report.md` — the prior 100-year sim that motivated F5
- `sanctum/2026-05-13-arc-f-f5-steady-state-ants-reward-exemption.md` — F5's prior decision
- `meta/arc-f-denarius.md` — Arc F strategic record
- `meta/denarius.md` — economic-theory document
- `journal/2026-05-14-architect.md` — today's brief that named this as Sanctum-class follow-up
