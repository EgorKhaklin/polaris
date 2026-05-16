# Arc F — the Denarius

**Status:** **CLOSED 2026-05-15** (per Sanctum
[`sanctum/2026-05-15-open-arcs-debate.md`](../sanctum/2026-05-15-open-arcs-debate.md)
Position C′; F1-F5 all shipped). Opened 2026-05-13; F1-F4 closed
2026-05-13; reopened with F5 amendment 2026-05-13; F5 shipped v8.73.
**Roadmap prefix:** R14-*
**Authorizing Sanctum:** `sanctum/2026-05-13-arc-f-denarius-opening.md`
**Closing Sanctum:** [`sanctum/2026-05-15-open-arcs-debate.md`](../sanctum/2026-05-15-open-arcs-debate.md)
(joint Architect + Anti-Architect recommendation; closing-by-doc-edit
to honor the Anti-Architect's AP2 cost-naming on Sanctum-overuse)

## Closing summary (added v9.16)

All five F-items shipped:
- F1 ✅ Treasury + Quaestor + drift-resolution reward function (v8.69)
- F2 ✅ Chaos test for silent ants (v8.70)
- F3 ✅ Cohort growth via proposal exercise (v8.70)
- F4 ✅ Cursus Honorum activation, structural readiness (v8.71)
- F5 ✅ Steady-state ants reward exemption (v8.73; Goodhart's Law mitigation)

The Denarius economy is operational. Treasury ledger maintained by
`polaris_swarm/civitas/treasury.py`; reward + penalty flows wired via
the F5 exemption logic. The deeper economic-dimension theory lives
in [`meta/denarius.md`](denarius.md) (concept doc; remains active
reference material). No further F-phases pending.

This file extracts Arc F's per-item detail from `MISSION.md`. The
extraction is editorial (per `sanctum/2026-05-14-doc-soft-refactor.md`);
no constitutional content is amended. `MISSION.md` retains the
constitutional summary + done-list rollup; this file holds the
historical narrative of how each F-item shipped.

The deeper economic-dimension mechanics (denarius theory, property
classes, Cursus Honorum) live in `meta/denarius.md`. This file is
the per-arc done-list narrative; `meta/denarius.md` is the concept
doc.

---

## Arc opening

Authorized by Sanctum
`sanctum/2026-05-13-arc-f-denarius-opening.md`. After two
Architect-led reports (100-year + 100-day), VANTA opened the
**economic dimension** of the Civitas. The connective tissue
of *chaos test + cohort growth + reward function* is **money**,
and money is what makes the world go round.

In Roman terms: the **denarius** and the property qualification
distinguished pleb from eques from patrician. In Polaris terms:
the denarius distinguishes ants whose pheromones lead to drift
resolution from ants whose pheromones decay unread.

**The pomerium holds:** the denarius is SWARM currency, not
Polaris currency. Ants accumulate wealth; Individuals do not.
C10 (*identity ≠ money*) is preserved verbatim.

The arc was originally explicitly **multi-day** (F2 ≥24h after F1;
F3 ≥24h after F2; F4 ≥7 days after F3). VANTA collapsed this
pacing on 2026-05-13 via the
`arc-f-accelerated-pacing-override.md` Sanctum (Option B);
F2/F3/F4 all shipped same-day. F5 amendment landed 2026-05-13 from
the post-v8.72 100-year simulation finding.

---

## Done-list

F1. ✅ **Treasury + Quaestor + drift-resolution reward function**
    *(delivered v8.68)*. New 5th citizen class:
    `quaestor_treasurer` — financial magistrate. New
    filesystem-AoR instance: `treasury-roll.json` (3rd after
    `sanctum/` + `census-roll.json`). New reward function
    (drift-resolution rewards): +10 denarii when a pheromone
    fingerprint resolves; −2 denarii for persistent silence
    (≥3 passes); volume is neutral. New G-guards: **G15**
    (treasury filesystem-AoR), **G16** (reward function
    deterministic). 4 new structural-invariants in
    `TestArcFDenarius`. `meta/denarius.md` ships as the complete
    economic-dimension doc.

F2. ✅ **Chaos test for silent ants** *(delivered v8.70,
    Sanctum-authorized
    `sanctum/2026-05-13-arc-f-accelerated-pacing-override.md`)*.
    `polaris_swarm/chaos.py` ships a deterministic harness with
    four FailureMode injections (RAISE_EXCEPTION,
    RETURN_MALFORMED, RETURN_SILENT, RETURN_INFLATED).
    Verification: the swarm's existing detection layers catch
    crashes/malformed via heartbeat suppression, silence via
    treasury fingerprint loss; **inflation is the unguarded
    failure mode** (no spike detector exists). F2 thus answers
    *are silent ants actually scanning correctly?* with a
    structural map of what's caught and what isn't.

F3. ✅ **Cohort growth via proposal exercise** *(delivered v8.70,
    same Sanctum)*. The Augur was extended to scan for
    project-state namespaces with zero ant coverage; on the
    first run it emitted `proposal_new_ant` for `proposals/`.
    The Architect materialized `ant_proposal_stagnation`
    (surfaces proposals/*.md files ≥30d stagnant and not
    promoted to ROADMAP); VANTA ratified via the same Sanctum.
    Ant joins legio_trajectory T2. **The G13 proposal-driven
    autogenesis loop is now closed end-to-end** for the first
    time in cohort history. ALL_ANTS: 28 → 29.

F4. ✅ **Cursus Honorum activation (structural readiness)**
    *(delivered v8.70, same Sanctum)*. Treasury gains
    `CURSUS_MULTIPLIER` constant + `multiplier_for(balance)` +
    `is_sanctum_chair_eligible(roll, ant)` +
    `patrician_ants(roll)`. Bloom renderer
    (`scripts/ai_swarm_bloom.py`) consults the treasury per-ant
    and applies multipliers: eques 1.5×, patrician 2.0×.
    **Behaviorally inert today** — max positive balance is 76;
    every ant is pleb; every multiplier is 1.0×. **As denarii
    accumulate through real operation, the multipliers engage
    automatically; no further ship is needed.** Two new G-guards:
    **G19** (multipliers monotonic non-decreasing in balance) and
    **G20** (Sanctum-chair eligibility derives ONLY from denarii;
    never from identity-layer state — C10 pomerium preserved).

F5. ✅ **Steady-state ants reward exemption** *(delivered v8.73,
    Sanctum-authorized
    `sanctum/2026-05-13-arc-f-f5-steady-state-ants-reward-exemption.md`)*.
    The 100-year post-v8.72 simulation surfaced an empirical
    finding: the v8.68 reward function rewards
    signal-RESOLUTION, but the v8.69+ acceleration cohort emits
    STEADY-STATE observations (recent_churn, changelog_gap,
    todo_debt, etc.) that never "resolve." Persistent-silence
    penalties compound linearly; no ant reached Eques in 100
    simulated years; the F4 Cursus Honorum multipliers were
    behaviorally unreachable.

    **F5 surgically fixes this:** adds `STEADY_STATE_ANTS`
    frozenset (9 ants: recent_churn, changelog_gap, ship_burst,
    release_velocity, test_gap, todo_debt, pattern_warmth,
    stale_script, unbumped_version) to `treasury.py`. Ants in
    this allowlist are DENARII-NEUTRAL — `compute_rewards`
    skips both reward AND penalty for them. Drift-class ants
    (the other 24 in the cohort) stay on the original reward
    function and remain the legitimate Cursus Honorum
    participants.

    **G15** (FS-AoR) preserved — historical events stay; only
    future passes behave differently. **G16** (determinism)
    preserved — same input still yields same output. **G26**
    (new) — additions to `STEADY_STATE_ANTS` require Sanctum
    authorization; enforced structurally by
    `test_g26_allowlist_matches_sanctum_enumeration`.

    Allowlisted ants keep their historical (negative) balances
    per audit-of-record — F5 is forward-looking only. They
    will never reach Eques; that's intentional, they're not in
    the race. The Cursus Honorum mechanism now has a chance
    to engage for drift-class ants whose signals genuinely
    resolve.

### F5 postscript (v8.90 architect scan finding)

The v8.89 macro scan + v8.90 diagnostic surfaced that F5 was
**structurally correct but operationally insufficient.** Real
post-v8.89 Treasury state (after the v8.89 bigint-overflow fix
let pheromones deposit cleanly for the first time since v8.62):

| Metric | Value |
|---|---|
| Drift-class ants in ledger | 10 (all non-steady-state) |
| Reward events | 48 (+480 denarii) |
| Penalty events | 3357 (-6714 denarii) |
| **Penalty:reward** | **14:1** |
| Min balance | -2704 (`ant_recent_churn`) |
| Class distribution | plebs=10, eques=0, patrician=0 |

**Cursus Honorum tier-mobility is unreachable from below at
current parameters.** The architecture's three-tier structure
exists in code but never engages.

**Sanctum-class follow-up on file:**
`sanctum/2026-05-14-treasury-rebalance.md` (**DECIDED + CLOSED**)
enumerated five positions: A (do nothing), **B (architect-
recommended: +10/−1 ratio)** — *selected*, C (extend allowlist —
explicitly not recommended), D (per-day reward floor), E (raise
threshold). **Position B shipped as v8.91** after 100-day-sim
verified the acceptance criterion (2/10 drift-class ants reach
Eques within 60 days under +10/−1, vs 1/10 under +10/−2).
`DENARII_PENALTY_PERSISTENT = 2 → 1`. The Cursus Honorum
mechanism is now functional (Eques is reachable). VANTA did
NOT bundle D or E; if, in 60 days of real operation, fewer than
1 drift-class ant has reached Eques, a follow-up Sanctum can
revisit. The diagnostic (`scripts/ai-treasury-report.sh`) is
the operator's continuous-verification instrument.

---

## Goodhart's Law mitigation + constitutional discipline

**Goodhart's Law mitigation.** The reward function rewards
*signal* (drift resolution), not *volume* (pheromone count).
An ant firing 100 pheromones with 0 resolutions earns 0
denarii. The architecture refuses the obvious gaming pattern
structurally.

**Constitutional principles unchanged.** C1-C10 preserved.
G1-G14 preserved; G15-G16 added F1; G19-G20 added F4; G26 added
F5. The four cognitive-substrate principles (Sanctum, AoR, risk
classes, CM) untouched. The v8.30 substitutability clause extends
to the economic dimension — a future agent may substitute the
reward function or the treasury mechanism without amending the
constitution, provided the guards still hold.

**Reference posture.** The denarius is informed by Roman
political economy + ant colony optimization's reward-laying
literature. The reward function is original to Polaris.

See also: `meta/denarius.md` (the economic-dimension concept doc;
property classes; Cursus Honorum theory).
