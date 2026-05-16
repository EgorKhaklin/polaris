"""Mycelium Treasury — the denarius ledger (Arc F / F1 / v8.68).

The economic dimension of the Civitas. Each ant accumulates
**denarii** based on whether its pheromones lead to drift
resolution. The ledger is filesystem-AoR per G15: entries are
append-only; balances are COMPUTED by summing, not stored.

Reward function (drift-resolution rewards):

  +10 denarii  — a pheromone fingerprint (deposited_by, node_id)
                 that was present last pass and is absent this
                 pass = the drift the ant flagged got resolved.
  -1  denarii  — a fingerprint that has been present for ≥3
                 consecutive passes = persistent silence;
                 nobody acted; the ant kept flagging the same
                 thing. (Was -2 pre-v8.91; halved per
                 sanctum/2026-05-14-treasury-rebalance.md
                 Position B to admit upward Cursus Honorum
                 mobility from below.)

Volume is neutral. An ant firing 100 pheromones with 0
resolutions earns 0 denarii. An ant firing 1 pheromone with 1
resolution earns +10. **The architecture rewards signal, not
volume** — Goodhart's Law mitigation by design.

The Quaestor (`quaestor_treasurer.py`) is the citizen class that
maintains this ledger. G16: same input (recent + last
fingerprints) produces same denarii deltas; replay-safe.

Authorized by `sanctum/2026-05-13-arc-f-denarius-opening.md`.
"""

from __future__ import annotations

import json
import pathlib
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any


# Reward function constants. Tunable in F4 (Cursus Honorum).
#
# v8.91 rebalance — `DENARII_PENALTY_PERSISTENT` was 2 (Position B from
# sanctum/2026-05-14-treasury-rebalance.md, selected by VANTA in-chat
# 2026-05-14 = "B"). The v8.90 macro-scan diagnostic showed a 14:1
# penalty:reward ratio after the swarm started depositing cleanly
# (the v8.89 bigint-overflow fix); under that ratio, Cursus Honorum
# tier-mobility was unreachable from below. The +10/−1 rebalance
# preserves Goodhart's Law mitigation (signal still earns 10× volume)
# while admitting real upward mobility. 100-day-sim projection: 2/10
# drift-class ants reach Eques within 60 days under the new parameters
# (vs 1/10 under the +10/−2 baseline). Acceptance criterion satisfied.
DENARII_PER_RESOLUTION = 10
DENARII_PENALTY_PERSISTENT = 1
PERSISTENT_THRESHOLD_PASSES = 3

# Property-class thresholds. Informational in F1; structurally
# activated in F4.
DENARII_PLEB_MAX      = 1_000
DENARII_EQUES_MAX     = 10_000
# 10_001+ = patrician


# F4 (v8.70) — Cursus Honorum activation. Multipliers applied to
# pheromone intensity when reading the swarm via the bloom renderer.
# Eques pheromones become 1.5× as visible; patrician pheromones
# become 2× as visible AND gain Sanctum-chair eligibility.
#
# G19 invariant: multipliers are monotonic non-decreasing in
# property class (pleb ≤ eques ≤ patrician). More denarii never
# REDUCES effective intensity.
#
# G20 invariant: Sanctum-chair eligibility is strictly inside the
# Civitas. It derives from the SWARM-CURRENCY balance only; never
# from any Polaris identity-layer attribute. C10 (pomerium)
# preserved.
#
# Behavior today (v8.70): treasury is empty; every ant balance is 0;
# every ant is pleb; every multiplier is 1.0×; no ant is
# Sanctum-chair eligible. As denarii accumulate over the coming
# days, the multipliers and eligibility predicates engage
# automatically. No further code ship is needed for F4 to "go
# live"; operation time is the only remaining variable.
CURSUS_MULTIPLIER = {
    "pleb":      1.0,
    "eques":     1.5,
    "patrician": 2.0,
}

# Sanctum-chair eligibility threshold: must be patrician (10k+).
SANCTUM_CHAIR_MIN_DENARII = DENARII_EQUES_MAX + 1  # = 10_001


# F5 (v8.73) — Steady-State Ants Reward Exemption.
#
# The 100-year simulation
# (`sanctum/2026-05-13-civitas-100-year-post-v8-72-report.md`)
# revealed that the v8.68 reward function rewards
# signal-RESOLUTION, but the v8.69+ acceleration cohort emits
# STEADY-STATE observations that never resolve. The persistent-
# silence penalty compounds linearly; no ant reaches Eques in 100
# simulated years; the F4 Cursus Honorum multipliers are
# behaviorally unreachable.
#
# F5 fixes this surgically: ants in `STEADY_STATE_ANTS` are
# DENARII-NEUTRAL — they accumulate neither rewards nor penalties.
# Drift-class ants (the other 24 in the v8.72 cohort) stay on the
# original reward function and remain eligible for Cursus Honorum.
#
# G15 preserved: existing events stay; only future passes behave
# differently. Allowlisted ants keep their historical (negative)
# balances per audit-of-record.
#
# G16 preserved: `compute_rewards` remains a pure function given
# this allowlist + the input fingerprints/pheromones.
#
# G26 (new): additions to STEADY_STATE_ANTS require a Sanctum
# authorizing each new entry. Enforced by structural-invariant
# `test_f5_allowlist_membership_matches_sanctum`.
#
# Authorized by:
#   sanctum/2026-05-13-arc-f-f5-steady-state-ants-reward-exemption.md
STEADY_STATE_ANTS: frozenset[str] = frozenset({
    # legio_trajectory (3): churn + cadence + historical bursts
    "ant_recent_churn",        # files modified <7d (always something)
    "ant_changelog_gap",       # files newer than latest CHANGELOG header
    "ant_ship_burst",          # historical date with ≥6 ships (permanent)
    # legio_engineer (1): cadence rhythm
    "ant_release_velocity",    # long-term cadence summary
    # legio_performance (1): test coverage
    "ant_test_gap",            # modules without colocated test files
    # legio_cognitive (3): debt + cold patterns + stable scripts
    "ant_todo_debt",           # TODO/FIXME markers in source
    "ant_pattern_warmth",      # catalog patterns with cold journal mentions
    "ant_stale_script",        # ai-*.sh scripts older than 60d
    # legio_docs (1): version-string drift in audit-of-record docs
    "ant_unbumped_version",    # md docs referencing stale v8.X
})


# v9.05 / Wave 1 / A1 — Soldier tier (v9.03) is structurally F5-exempt.
#
# v9.03 Sanctum (`sanctum/2026-05-14-hybrid-swarm-mirai-pattern.md` §VI)
# explicitly claims:
#     "F5 (soldiers explicitly EXEMPT — no Treasury accrual;
#      disposable invariant)"
# but `compute_rewards()` only checked the STEADY_STATE_ANTS allowlist;
# soldier_* deposits accrued rewards/penalties anyway. The
# polaris-self-roadmap-2026-05-14.md macro-to-micro scan caught 21
# soldier_* entries in treasury-roll.json by direct read, contradicting
# the Sanctum claim.
#
# This predicate restores the constitutional invariant: anything whose
# `deposited_by` starts with `soldier_` is structurally exempt, no
# matter how many soldier classes ship in the future. The exemption is
# enforced in `compute_rewards()` alongside the STEADY_STATE_ANTS
# allowlist check.
#
# G16 still preserved: predicate is pure on the ant name string.
# G26 still preserved: STEADY_STATE_ANTS additions still need a Sanctum;
# soldier_* exemption derives from the v9.03 Sanctum already in force.
SOLDIER_NAME_PREFIX = "soldier_"


def is_treasury_exempt(ant_name: str) -> bool:
    """True iff this ant accrues neither rewards nor penalties.

    Two exemption paths:
      1. STEADY_STATE_ANTS allowlist (F5; v8.73)
      2. soldier_* prefix (v9.03 disposability invariant; v9.05 enforcement)
    """
    if ant_name in STEADY_STATE_ANTS:
        return True
    if ant_name.startswith(SOLDIER_NAME_PREFIX):
        return True
    return False


TREASURY_ROLL_PARTS = ("polaris_swarm", "civitas", "treasury-roll.json")


@dataclass
class DenariusEvent:
    """One ledger entry — a reward or penalty."""
    timestamp: str           # ISO 8601 UTC
    ant: str                 # which ant earned/lost
    amount: int              # +10 reward; -1 penalty (v8.91 rebalance; was -2)
    reason: str              # 'drift_resolution' | 'persistent_silence'
    node_id: str             # the brain-map node concerned

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "ant": self.ant,
            "amount": self.amount,
            "reason": self.reason,
            "node_id": self.node_id,
        }


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _empty_roll() -> dict:
    return {
        "_doc": (
            "Mycelium Treasury Roll (Arc F / F1 / v8.68). The Quaestores "
            "maintain this file as filesystem-AoR per G15: entries are "
            "append-only-discipline. Balances are computed by summing "
            "the events list, never stored. Last-pass fingerprints are "
            "tracked for next-pass drift-resolution detection."
        ),
        "_authority": "sanctum/2026-05-13-arc-f-denarius-opening.md",
        "_g_guards": "G15 (filesystem-AoR) + G16 (deterministic)",
        "last_pass_taken": None,
        "last_pass_fingerprints": {},   # {fingerprint: pass_count}
        "events": [],
    }


def load_roll(root: pathlib.Path) -> dict:
    """Read the treasury roll. Returns an empty roll if file
    missing or malformed (graceful failure per the read-only
    contract). G15: this function never deletes or modifies
    existing events."""
    path = root.joinpath(*TREASURY_ROLL_PARTS)
    if not path.is_file():
        return _empty_roll()
    try:
        roll = json.loads(path.read_text())
        if not isinstance(roll, dict):
            return _empty_roll()
        roll.setdefault("last_pass_fingerprints", {})
        roll.setdefault("events", [])
        return roll
    except (OSError, json.JSONDecodeError):
        return _empty_roll()


def save_roll(root: pathlib.Path, roll: dict) -> None:
    """Write the treasury roll. G15: append-only-discipline —
    callers may add events and update last_pass_fingerprints
    but must never remove events."""
    path = root.joinpath(*TREASURY_ROLL_PARTS)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(roll, indent=2, sort_keys=True))


def fingerprint(deposited_by: str, node_id: str) -> str:
    """Stable identifier for a pheromone position in the swarm."""
    return f"{deposited_by}::{node_id}"


def compute_balance(roll: dict, ant_name: str) -> int:
    """Sum all events for an ant. Deterministic per G16."""
    total = 0
    for ev in roll.get("events", []):
        if ev.get("ant") == ant_name:
            total += int(ev.get("amount", 0))
    return total


def all_balances(roll: dict) -> dict[str, int]:
    """All ants' current balances. Deterministic per G16."""
    totals: dict[str, int] = defaultdict(int)
    for ev in roll.get("events", []):
        totals[ev.get("ant", "(unknown)")] += int(ev.get("amount", 0))
    return dict(totals)


def property_class(balance: int) -> str:
    """Cursus Honorum tier based on denarii balance.
    Informational in F1 (v8.68); structurally activated in F4 (v8.70).
    """
    if balance <= DENARII_PLEB_MAX:
        return "pleb"
    if balance <= DENARII_EQUES_MAX:
        return "eques"
    return "patrician"


def multiplier_for(balance: int) -> float:
    """F4 — return the Cursus Honorum intensity multiplier for an
    ant's current denarii balance.

    G19 holds: monotonic non-decreasing in balance. Pleb=1.0 ≤
    Eques=1.5 ≤ Patrician=2.0. Higher denarii NEVER reduces
    multiplier below pleb.

    Today (v8.70 ship-day): treasury is empty; every ant is at
    balance=0; every ant returns 1.0. As denarii accumulate over
    days of operation, multipliers organically engage.
    """
    cls = property_class(balance)
    return CURSUS_MULTIPLIER.get(cls, 1.0)


def multiplier_for_ant(roll: dict, ant_name: str) -> float:
    """Convenience: compute balance, then multiplier. The bloom
    renderer's per-ant lookup path."""
    return multiplier_for(compute_balance(roll, ant_name))


def is_sanctum_chair_eligible(roll: dict, ant_name: str) -> bool:
    """F4 — return True iff the ant has earned patrician-class
    denarii history.

    G20 holds: eligibility derives ONLY from SWARM-CURRENCY
    balance. Never references Individual, token, or any
    identity-layer attribute. The pomerium (C10) does not move.

    Today (v8.70): all balances are 0; no ant qualifies. As real
    denarii accumulate (≥7 days of distinct treasury operation
    per the Arc F Sanctum), patrician-class ants emerge
    automatically and become available for future Sanctum-chair
    consultation flows. The eligibility predicate is wired into
    NOTHING in v8.70 — it is structural readiness, not behavior
    change. Future ships may consult patrician ants on Sanctum
    decisions; the predicate is ready when that consultation
    flow is designed.
    """
    return compute_balance(roll, ant_name) >= SANCTUM_CHAIR_MIN_DENARII


def patrician_ants(roll: dict) -> list[str]:
    """F4 — return the list of currently-patrician-class ant names.

    For ratification flows / Sanctum-chair eligibility queries.
    Sorted alphabetically for stable output (deterministic per
    G16)."""
    return sorted(
        ant for ant, bal in all_balances(roll).items()
        if bal >= SANCTUM_CHAIR_MIN_DENARII
    )


def compute_rewards(
    last_fingerprints: dict[str, int],
    current_pheromones: list[dict],
) -> tuple[list[DenariusEvent], dict[str, int]]:
    """Compute denarii deltas comparing last pass's fingerprints
    against the current pass's pheromones.

    Returns:
        events: list of DenariusEvent rewards/penalties this pass
        new_fingerprints: updated {fingerprint: pass_count}
                          to write back to the roll

    Drift-resolution: present last → absent this = reward.
    Persistent silence: fingerprint count >= threshold = penalty.

    Filters at pheromone-collection time:
      - heartbeats are NOT eligible for rewards (proof-of-life,
        not signal).
      - Civic findings are excluded (meta-observations).

    F5 (v8.73 / Arc F): ants in `STEADY_STATE_ANTS` are
    DENARII-NEUTRAL — their fingerprints are still tracked
    (so the system knows what the swarm currently sees), but
    they accumulate NEITHER drift-resolution rewards NOR
    persistent-silence penalties. Steady-state observers
    (recent_churn, changelog_gap, todo_debt, etc.) emit findings
    that never "resolve" by edit; the original reward function
    denied them legitimate value. Authorized by
    `sanctum/2026-05-13-arc-f-f5-steady-state-ants-reward-exemption.md`.

    G16 preserved: this remains a pure function.
        same(last_fingerprints, current_pheromones, STEADY_STATE_ANTS)
        always yields same (events, new_fingerprints).
    """
    now = _now_iso()
    events: list[DenariusEvent] = []
    new_fingerprints: dict[str, int] = {}

    # Build current fingerprint set, excluding heartbeats + civitas
    current_fingerprints: set[str] = set()
    for ph in current_pheromones:
        ev = ph.get("evidence") or {}
        obs_type = ev.get("observation_type", "")
        if obs_type == "heartbeat":
            continue
        if ev.get("civitas_class"):
            continue
        deposited_by = ph.get("deposited_by", "")
        node_id = ph.get("node_id", "")
        if not deposited_by or not node_id:
            continue
        current_fingerprints.add(fingerprint(deposited_by, node_id))

    # Drift resolution: was present last pass, absent this pass.
    # F5: skip both reward AND penalty for steady-state-observer ants.
    # v9.05 / A1: skip for the soldier_* tier per the v9.03 Sanctum.
    for fp, count in last_fingerprints.items():
        ant, _, node = fp.partition("::")
        is_steady_state = is_treasury_exempt(ant)

        if fp not in current_fingerprints:
            # Drift resolved
            if is_steady_state:
                # F5: no reward — but also don't carry the fingerprint
                # forward (it's gone from current; the fingerprint set
                # ends here for this trace, same as drift-class).
                continue
            events.append(DenariusEvent(
                timestamp=now,
                ant=ant,
                amount=DENARII_PER_RESOLUTION,
                reason="drift_resolution",
                node_id=node,
            ))
        else:
            # Still present; increment pass count
            new_fingerprints[fp] = count + 1
            if is_steady_state:
                # F5: no penalty — but still track the pass count so
                # the fingerprint history is auditable. The count
                # accumulates harmlessly.
                continue
            if count + 1 >= PERSISTENT_THRESHOLD_PASSES:
                events.append(DenariusEvent(
                    timestamp=now,
                    ant=ant,
                    amount=-DENARII_PENALTY_PERSISTENT,
                    reason="persistent_silence",
                    node_id=node,
                ))

    # New fingerprints this pass: present this, absent last.
    # Tracked for ALL ants (so resolution can be detected next pass);
    # F5 exemption only affects events, not fingerprint tracking.
    for fp in current_fingerprints:
        if fp not in last_fingerprints:
            new_fingerprints[fp] = 1

    return events, new_fingerprints
