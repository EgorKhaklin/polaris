# Sanctum: arc-f-f5-steady-state-ants-reward-exemption

**Date:** 2026-05-13
**Petitioner:** agent (Claude, Opus 4.7) speaking as the Architect
**Principal:** VANTA
**Trigger:** Empirical finding from
`sanctum/2026-05-13-civitas-100-year-post-v8-72-report.md` §V — the
v8.68 reward function was designed for ants that flag transient
drift, but the v8.69+ acceleration cohort emits **steady-state
observations** that never "resolve." 100 simulated years show NO
ant reaches Eques; the v8.70 F4 Cursus Honorum multipliers are
structurally inert at current design. VANTA's directive: *"proceed
with the architects recommendation."* — i.e., R1: revise the
reward function to exempt steady-state-observer ants.
**Risk class:** MEDIUM (amends the Arc F · F1 reward function;
touches treasury.py; G16 determinism preserved; G15 AoR preserved;
existing treasury history NOT rewritten — only future passes
behave differently).
**Status:** CLOSED
**Architect brief ID:** arch-2026-05-13

---

## I. The Matter

The v8.68 reward function (`compute_rewards` in
`polaris_swarm/civitas/treasury.py`) implements Goodhart's-Law
mitigation by rewarding signal-resolution rather than
signal-volume:

- **+10 denarii** when a pheromone fingerprint that was present
  last pass is absent this pass (drift resolved).
- **−2 denarii** when a fingerprint has been present for ≥3
  consecutive passes (persistent silence).

The 100-year simulation revealed that this design assumes
**every ant emits transient drift signals.** It does not. The
v8.69+ acceleration ants surface STEADY-STATE observations:

| Ant | What it fires on | Does the finding resolve? |
|---|---|---|
| `ant_recent_churn` | files modified in last 7d | No — files always change in active development |
| `ant_changelog_gap` | files newer than latest CHANGELOG header | No — files always newer until next ship |
| `ant_ship_burst` | historical date with ≥6 ships | No — historical bursts are permanent in CHANGELOG |
| `ant_release_velocity` | cadence summary | No — cadence is always *something* |
| `ant_test_gap` | modules without test files | Rarely — most modules legitimately stay untested |
| `ant_todo_debt` | TODO/FIXME markers in source | Rarely — TODOs are work-in-progress markers |
| `ant_unbumped_version` | markdown refs to old v8.X | No — audit-of-record docs are correct as written |
| `ant_pattern_warmth` | catalog patterns with cold journal mentions | No — cold patterns stay cold |
| `ant_stale_script` | ai-*.sh scripts older than 60d | No — stable scripts stay stable |

These ants accumulate **persistent-silence penalties forever**
(linear in pass count) while **drift-resolution rewards never
fire** for them. After 1200 simulated passes:

- `ant_recent_churn`: −122,404 denarii (max negative across the cohort)
- `ant_changelog_gap`: −85,840 denarii
- `ant_test_gap`: −42,920 denarii
- Median balance across all firing ants: −7,334 denarii

**No ant ever reaches Eques.** The Cursus Honorum infrastructure
shipped in v8.70 / F4 is behaviorally unreachable.

This is not a bug in the simulation; it's a structural property
of the current reward function applied to the current cohort
composition.

## II. Preparation

The Architect has reviewed:

- **`polaris_swarm/civitas/treasury.py`** — current
  `compute_rewards` implementation (drift_resolution +10 /
  persistent_silence −2 / threshold 3 passes)
- **`sanctum/2026-05-13-arc-f-denarius-opening.md`** — the F1
  Sanctum that established the reward function; Goodhart's
  Law mitigation as primary design goal
- **`sanctum/2026-05-13-civitas-100-year-post-v8-72-report.md`** —
  the empirical case for revision
- **G15 + G16** — filesystem-AoR + reward-determinism guards;
  any revision must preserve both
- **The 33-ant cohort** — categorized below into drift-class and
  steady-state-observer-class

## III. Item-by-item: which ants are steady-state-observers?

Of the 33 ants in the v8.72 cohort, the Architect identifies
**9 as steady-state-observers**:

```
STEADY_STATE_ANTS = {
    "ant_recent_churn",       # legio_trajectory
    "ant_changelog_gap",      # legio_trajectory
    "ant_ship_burst",         # legio_trajectory
    "ant_release_velocity",   # legio_engineer
    "ant_test_gap",           # legio_performance
    "ant_todo_debt",          # legio_cognitive
    "ant_unbumped_version",   # legio_docs
    "ant_pattern_warmth",     # legio_cognitive
    "ant_stale_script",       # legio_cognitive
}
```

The criterion: **does the ant's typical finding persist
indefinitely on the same node_id under steady-state
development?** If yes, the ant is steady-state-observer; the
reward function as currently designed denies it value.

The remaining 24 ants emit transient-drift signals that legitimately
resolve when an operator acts. Example resolution events:

| Ant | Example transient drift | Resolution path |
|---|---|---|
| `ant_sanctum_outcome` | CLOSED Sanctum lacks §VII cross-ref | operator adds the line |
| `ant_api_doc_coverage` | new route undocumented | operator updates API.md |
| `ant_aor_immutability` | append-only trigger missing | schema fix |
| `ant_csp_health` | CSP violation | template fix |
| `ant_done_list_arithmetic` | mission rollup wrong | MISSION update |
| `ant_mission_drift` | MISSION.md anchor missing | restore the anchor |
| `ant_principle_invariant` | principle implementation missing | restore implementation |
| `ant_self_model_accuracy` | registry vs reality mismatch | sync the registry |
| `ant_legion_doctrine_health` | TacticConfig invalid | fix tiers/lead |
| `ant_brain_map_freshness` | brain-map stale | regenerate |
| ... (14 more) | ... | ... |

These 24 ants stay on the standard reward function. The
Cursus Honorum mechanism rewards drift-resolution; the 24
drift-class ants are the legitimate participants in that race.

## IV. Recommendation

**Ship as v8.73 (Arc F · F5 — Steady-State Ants Reward Exemption).**

### Design

In `polaris_swarm/civitas/treasury.py`:

1. Add `STEADY_STATE_ANTS = frozenset({…9 names…})` module constant.
2. Modify `compute_rewards(last_fingerprints, current_pheromones)`
   to **skip both reward AND penalty** when the depositing ant is
   in `STEADY_STATE_ANTS`. The function signature is unchanged;
   the change is purely internal logic.
3. Allowlisted ants become **denarii-neutral**: they never
   accumulate denarii (positive or negative) from this pass
   forward. Their existing balances (per the historical reward
   function design) remain as recorded — per G15 AoR, the
   ledger is the history. No retroactive correction.
4. Document the change at the function docstring + add a
   `_revision` marker in the next treasury-roll.json save so the
   audit trail is legible: "ledger semantics changed at v8.73."

### G-guards preserved

- **G15** (FS-AoR) — preserved. Existing events stay; no entries
  rewritten. Only the formula for future entries changes.
- **G16** (determinism) — preserved. The new `compute_rewards`
  remains a pure function: same fingerprints + same pheromones
  + same allowlist = same events. Replay-safe.

### What CHANGES (and what doesn't)

| Property | Before F5 | After F5 |
|---|---|---|
| `STEADY_STATE_ANTS` constant | Doesn't exist | 9 ants |
| Allowlisted-ant rewards | Counted | Skipped |
| Allowlisted-ant penalties | Counted | Skipped |
| Drift-class ant behavior | Unchanged | Unchanged |
| Cursus Honorum multipliers | Inert (no Eques exists) | Reachable by drift-class ants |
| Historical balances | As recorded | As recorded (G15 holds) |
| Function signature | (last_fp, current_ph) → (events, new_fp) | Same |
| Determinism (G16) | Pure function | Pure function |
| Treasury append-only (G15) | Yes | Yes |

### Verification approach

**Two-pass replay test:** synthesize a controlled fingerprint +
pheromone scenario; run `compute_rewards` twice — once with the
steady-state ant included as a depositor, once with a drift-class
ant. Assert: drift-class produces +10/−2 events; steady-state
ant produces 0 events. This is the structural-invariant for F5.

## V. Alternatives considered

1. **Reset balances for allowlisted ants to 0.** Rejected: G15
   forbids destructive edits to the events list. Audit-of-record
   discipline.

2. **Issue compensating credit events to allowlisted ants** to
   zero out their historical penalties. Rejected: doesn't honor
   the historical design's intent (the ants WERE losing under
   the old rules; rewriting history elides that signal).

3. **Drop the persistent-silence penalty entirely.** Rejected:
   the penalty IS load-bearing for drift-class ants — it forces
   real signal-resolution rather than persistent flagging
   without operator action. Removing it for everyone breaks
   Goodhart-mitigation for the 24 drift-class ants.

4. **Different reward function entirely** (e.g., +1 per priority
   promotion). Rejected for this Sanctum's scope — a larger
   redesign deserves its own deliberation. The allowlist
   approach is the surgical minimum fix that addresses the
   empirical finding without re-opening Arc F design.

5. **Allowlist is too permissive — should require explicit
   Sanctum per ant.** Considered. Rejected: the criterion
   (steady-state observer) is structural and defensible per ant
   in §III; bundling all 9 into one Sanctum is more legible than
   9 separate ratifications. Future additions to the allowlist
   should require Sanctum authorization (new structural guard:
   G26 — allowlist additions require Sanctum).

## VI. Decision

**Ship as v8.73 — Arc F · F5 — Steady-State Ants Reward Exemption.**

VANTA in-chat 2026-05-13 directive: *"proceed with the architects
recommendation."* Authorized.

### What ships

- `polaris_swarm/civitas/treasury.py` — `STEADY_STATE_ANTS`
  constant + `compute_rewards()` revision + `_revision_marker`
  metadata in saved roll.
- **G26** — additions to `STEADY_STATE_ANTS` require Sanctum
  authorization; codified structurally via a test that compares
  the in-code allowlist against this Sanctum's enumerated list.
- 4 new structural-invariants in `TestArcFF5SteadyStateExemption`.
- MISSION.md Arc F: F5 ✅ added.
- ROADMAP.md v14: R14-5 ✅ added.
- meta/denarius.md updated.
- CHANGELOG v8.73 entry.
- CLAUDE.md state-map.
- journal.

### What does NOT ship

- **No retroactive balance correction.** Historical events stay.
  Allowlisted ants keep their accrued (negative) balances; they
  simply stop accumulating more from F5 onward.
- **No legion split** (R2 from the report) — deferred until R1's
  effects observable.
- **No Arc G Phase 2** — deferred per R3.

## VII. Outcome

v8.73 shipped. `STEADY_STATE_ANTS` frozenset added with 9 ants;
`compute_rewards()` revised to skip both reward and penalty for
allowlisted ants. G15 + G16 preserved verbatim. G26 added
(allowlist additions require Sanctum).

**Five-scenario replay verification confirmed the design:**

1. Drift-class `ant_sanctum_outcome` → resolution gives +10 ✓
2. Steady-state `ant_recent_churn` → resolution gives 0 events ✓
3. Drift-class `ant_legion_doctrine_health` at pass 3 → −2 penalty ✓
4. Steady-state `ant_changelog_gap` at pass 3 → 0 events;
   fingerprint count still incremented to 3 (replay traceability
   preserved) ✓
5. Determinism — two consecutive `compute_rewards()` calls with
   identical input produce identical events and identical
   fingerprint output ✓

**6 new structural-invariants in `TestArcFF5SteadyStateExemption`**
(168 → 174 total):
- F5.1 allowlist constant exists with canonical 9 ants
- F5.2 reward skipped for allowlisted ants
- F5.3 penalty skipped for allowlisted ants (fingerprint still tracked)
- F5.4 drift-class regression guard (24 other ants unaffected)
- F5.5 G16 determinism preserved post-F5
- G26 allowlist-matches-Sanctum-enumeration

**Audit-of-record discipline:** allowlisted ants keep their
historical (negative) balances. F5 is forward-looking only. They
will remain pleb-class indefinitely — that's intentional; they're
not in the Cursus Honorum race. The race continues among the 24
drift-class ants whose signals genuinely resolve.

**Arc F reopened.** Was closed 4/4 ✅ at v8.70; F5 amendment
reopens the arc. The 100-year simulation surfaced the gap that
shipping at scale would not have caught for years.

**The simulation-to-fix cycle:** v8.72 ship → 100-year simulation
→ Architect surfaces R1 → VANTA authorizes → v8.73 ship. This is
the cleanest empirical iteration realized today. Pattern #21
Closure 12th instance.

**See:** CHANGELOG ## v8.73 · journal/2026-05-13.md
