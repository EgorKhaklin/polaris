# Treasury 60-day sim review — 2026-05-15 (v9.07)

**Source:** polaris-self-roadmap-2026-05-14.md item J4, Wave 3.
**Sanctum referenced:** `sanctum/2026-05-14-treasury-rebalance.md`
(Position B / +10/-1 ratio shipped as v8.91).
**Petitioner:** agent (Claude, Opus 4.7) speaking as the Architect.

---

## The contract

v8.91 shipped Position B (`DENARII_PENALTY_PERSISTENT: 2 → 1`). The
Sanctum's §V acceptance criterion was a 100-day simulation
projection: **2/10 drift-class ants reach Eques (≥1001 denarii)
within 60 days under the +10/-1 ratio**, vs 1/10 under the prior
+10/-2.

The Sanctum committed to a 60-day operational evaluation window
ending **2026-07-13** (60 days from the v8.91 ship date 2026-05-14).

J4 surfaces the question: with v9.05's A1 (F5 soldier-exemption
restored) and B1+B2 (ant venv-blindness fixed), the underlying
counts changed materially. Should the 60-day window be reset, or
extended, or absorbed into a longer evaluation?

## Current state (snapshot 2026-05-15 ~05:00 UTC)

```
Total events:        3726
Distinct ants:       19
Class distribution:  plebs=19  eques=0  patrician=0
Reward total:        +680  (68 drift_resolution events)
Penalty total:       -7316  (3658 persistent_silence events)
Net:                 -6636
Penalty:reward:      10.76:1
```

Per-ant standings (positive ≠ Eques; Eques requires ≥1001):

| Ant | Balance | Δ from v8.91 baseline | Notes |
|---|---|---|---|
| ant_recent_churn | -2704 | unchanged | STEADY_STATE_ANTS; no new accruals |
| ant_changelog_gap | -1502 | unchanged | STEADY_STATE_ANTS; no new accruals |
| ant_test_gap | -802 | unchanged | STEADY_STATE_ANTS; v9.05/B1 reduced future penalty load by 97.7% |
| ant_done_list_arithmetic | -738 | -32 (worse) | drift-class; still accruing |
| ant_ship_burst | -248 | unchanged | STEADY_STATE_ANTS |
| ant_todo_debt | -232 | unchanged | STEADY_STATE_ANTS; v9.05/B1 reduced load 94% |
| ant_build_freshness | -228 | -16 (worse) | drift-class (note: not in STEADY_STATE) |
| ant_release_velocity | -72 | unchanged | STEADY_STATE_ANTS |
| ant_legion_doctrine_health | -32 | unchanged | drift-class |
| ant_journal_silence | +9 | unchanged | drift-class; tiny |
| 8× soldier_* | +10 to +50 | frozen v9.05 | F5-exempt as of v9.05; 19 historical events stay per G15 |
| ant_sanctum_outcome | +18 | unchanged | drift-class |

## What changed vs v8.91 baseline

**v9.05 Wave 1 affected the Treasury in three ways:**

1. **A1 — soldiers F5-exempt.** Before v9.05, soldiers accrued
   rewards/penalties in violation of the v9.03 Sanctum §VI claim.
   v9.05 restored the invariant via `is_treasury_exempt()`. The
   19 historical soldier events stay (G15); no new soldier
   accruals possible. **Impact: removes 8 ants from the reward
   pool.** This is a CORRECTION, not a regression.

2. **B1+B2 — ants stop scanning venv.** Before v9.05, ant_test_gap
   deposited 708 venv-noise pheromones/day, ant_todo_debt 96/day.
   Most never "resolved" (venv files don't change), so they
   accreted as persistent-silence penalties. **Impact: removes
   ~800 daily penalty-fingerprints from STEADY_STATE_ANTS.** This
   STRENGTHENS the v8.73 F5 exemption's intent (those ants were
   penalty-immune anyway, but now they're cleaner).

3. **F5 STEADY_STATE_ANTS** (unchanged from v8.73): the 9
   allowlisted ants are reward-and-penalty-neutral. Their
   historical balances stay (G15) but never change going forward.

## Implications for the 60-day window

The v8.91 100-day-sim projection assumed:
- Pre-v9.05 swarm cohort (no soldier exemption)
- Pre-v9.05 venv-noise (massive persistent-silence load)
- The ants that COULD reach Eques were the drift-class
  non-STEADY_STATE ants (12 of them in the v9.03 cohort)

The post-v9.05 reality:
- 19 ants in the ledger (8 are now-frozen soldiers)
- Of the 11 non-soldier ants, 9 are in STEADY_STATE_ANTS (no
  accrual)
- **Only 2 ants are eligible to reach Eques organically**:
  - `ant_done_list_arithmetic` (currently -738; needs +1739 to
    reach Eques)
  - `ant_legion_doctrine_health` (-32; needs +1033)
  - (`ant_journal_silence` and `ant_sanctum_outcome` are positive
    but barely; both classifiable as drift-class observers; either
    could move toward Eques)

## Architect's assessment

**The 60-day window is intact but the constituency changed.** The
v8.91 acceptance criterion (2/10 reach Eques in 60d) was framed
when the swarm had 10 drift-class ants. Post-v9.05 the
denominator is effectively 4 (the non-STEADY_STATE non-soldier
non-civitas ants). 2/10 → 2/4 is no longer a clean
apples-to-apples comparison.

**Two paths:**

### Path A — keep the original 2026-07-13 window, re-baseline metric

Continue the v8.91 60-day clock. At 2026-07-13, evaluate against
a re-baselined metric:
- Original criterion: 2/10 drift-class ants at Eques
- Re-baselined criterion: ANY drift-class ant at Eques OR
  meaningful upward trajectory (e.g., positive balance growth
  >+100/30d)

If neither is met, opens a follow-up Sanctum to either further
loosen the penalty (Position D from v8.90: per-day reward floor)
or accept that Cursus Honorum reaches Eques only on multi-quarter
timescales.

### Path B — reset to 2026-07-14 + 60d (= 2026-09-12)

Treat v9.05 as a new baseline. Run the 100-day sim projection
fresh with the post-v9.05 cohort. Wait the full 60d from v9.05.

**Architect's recommendation:** **Path A.** Two reasons:

1. **The v8.91 Sanctum's projection assumed +10/-1.** That
   ratio is unchanged in v9.05. The mechanism is the same; only
   the population shifted. Resetting the window punishes the
   v8.91 decision for being right (Position B was correct; the
   swarm population happened to evolve under it).

2. **Re-baselining the metric is cheaper than re-baselining the
   window.** A Wave 4 / Treasury-Rebalance-II Sanctum can adjust
   the criterion if the v9.05-cohort math demands it. That ship
   shouldn't be pre-empted by resetting the clock.

## Recommended actions

| Action | When | Trigger |
|---|---|---|
| Re-run treasury sim with v9.05 cohort | 2026-05-22 (1 week post v9.05) | Wave 4 candidate |
| Re-run macro-to-micro scan | 2026-06-15 (~30d post v9.04 scan) | Wave 4 candidate |
| Formal v8.91 60-day evaluation | 2026-07-13 | Calendar trigger |
| Wave 4 / Treasury-Rebalance-II Sanctum | 2026-07-13 IF criterion not met | Conditional |

## Acceptance criterion for J4 closure

J4 closes with this document filed under meta/. The substantive
60-day evaluation remains scheduled for 2026-07-13 per the v8.91
Sanctum's original commitment. No re-decisioning required today.

## Cross-references

- `sanctum/2026-05-14-treasury-rebalance.md` — the v8.91 source
- `meta/polaris-self-roadmap-2026-05-14.md` — item J4 (the surfacing)
- `meta/arc-f-denarius.md` — the F-arc strategic record
- `polaris_swarm/civitas/treasury.py` — the implementation
  (DENARII_PENALTY_PERSISTENT = 1; v9.05 added is_treasury_exempt)
- `scripts/ai-treasury-report.sh` — the standing diagnostic
