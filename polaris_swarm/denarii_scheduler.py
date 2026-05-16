"""polaris_swarm/denarii_scheduler.py — currency-weighted scan frequency.

v9.24 / BIG MISSION Tier 1 #5. Builds on Tier 1 #3 (Treasury-as-oracle
ranking) and Tier 1 #4 (stigmergic loop closure).

Pre-v9.24, the Treasury was a scoreboard: rewards and penalties
accumulated, but no scheduling decision consulted balances. The
currency consumed nothing.

This module decides, given a colony cycle, which legions get deployed
*this* cycle based on their aggregate ant balance. The mapping:

    Top quartile (Q1)    — always deploy (every cycle)
    Second quartile (Q2) — deploy every cycle
    Third quartile (Q3)  — deploy every other cycle (50%)
    Bottom quartile (Q4) — deploy every fourth cycle (25%)

**Floor (Anti-Architect's requirement in v9.24 Sanctum):** NO legion
gets sampled less than once per 24h. Bottom-quartile ants don't
disappear — they just get less often. Deletion-by-proxy is not
permitted; only the v9.25 Sanctum can authorize deletion.

**Determinism (G1):** given the same cycle index + same Treasury
balances + same last-deploy timestamps, the output is identical.

**Graceful (G3):** if treasury-roll.json is missing or malformed,
falls back to "deploy all legions every cycle" (the pre-v9.24
behavior). The scheduler never blocks a legion from running due to
its own malfunction.
"""

from __future__ import annotations

import json
import pathlib
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional


_DEFAULT_TREASURY = pathlib.Path(__file__).resolve().parent / "civitas" / "treasury-roll.json"
_FLOOR_HOURS = 24.0


@dataclass(frozen=True)
class DeployDecision:
    """One legion's deploy/skip decision for the current cycle.

    `deploy` is True if this legion should run this cycle.
    `quartile` is 1..4 (1 = highest balance, 4 = lowest).
    `reason` is a one-line explanation.
    """
    legion_name: str
    deploy: bool
    quartile: int
    reason: str


def schedule_legions(
    legion_names: list[str],
    legion_to_ants: dict[str, list[str]],
    cycle_index: int,
    treasury_path: pathlib.Path = _DEFAULT_TREASURY,
    last_deploy_utc: Optional[dict[str, str]] = None,
) -> list[DeployDecision]:
    """Decide which legions to deploy this cycle.

    Args:
        legion_names: ordered list of all legion names
        legion_to_ants: map legion_name → list of commander ant names
        cycle_index: current cycle number (used for modular scheduling)
        treasury_path: where to read balances from
        last_deploy_utc: optional map legion_name → ISO timestamp of
                         last deploy (used to enforce the 24h floor)

    Returns one DeployDecision per legion in `legion_names`.
    Order is preserved.
    """
    if last_deploy_utc is None:
        last_deploy_utc = {}

    balances = _read_legion_balances(legion_to_ants, treasury_path)

    # If we couldn't read any balances, deploy all (graceful)
    if not any(balances.values()) and not any(v == 0 for v in balances.values()):
        return [
            DeployDecision(
                legion_name=n, deploy=True, quartile=0,
                reason="treasury unreadable; falling back to deploy-all",
            )
            for n in legion_names
        ]

    # Quartile-classify
    sorted_balances = sorted(balances.values(), reverse=True)
    n = len(sorted_balances)
    if n == 0:
        return []

    q1_threshold = sorted_balances[max(0, n // 4 - 1)] if n >= 4 else sorted_balances[0]
    q2_threshold = sorted_balances[max(0, n // 2 - 1)] if n >= 2 else sorted_balances[0]
    q3_threshold = sorted_balances[max(0, 3 * n // 4 - 1)] if n >= 4 else sorted_balances[-1]

    decisions: list[DeployDecision] = []
    now = datetime.now(timezone.utc)

    for name in legion_names:
        bal = balances.get(name, 0)
        if bal >= q1_threshold:
            quartile = 1
        elif bal >= q2_threshold:
            quartile = 2
        elif bal >= q3_threshold:
            quartile = 3
        else:
            quartile = 4

        # Floor check: if last deploy >24h ago, force deploy
        last_iso = last_deploy_utc.get(name)
        floor_forced = False
        if last_iso:
            try:
                last_dt = datetime.fromisoformat(last_iso.replace("Z", "+00:00"))
                if not last_dt.tzinfo:
                    last_dt = last_dt.replace(tzinfo=timezone.utc)
                if (now - last_dt) > timedelta(hours=_FLOOR_HOURS):
                    floor_forced = True
            except ValueError:
                floor_forced = True
        else:
            # No record of ever deploying → floor-force
            floor_forced = True

        if floor_forced:
            decisions.append(DeployDecision(
                legion_name=name, deploy=True, quartile=quartile,
                reason=f"24h floor forces deploy (Q{quartile}, balance={bal})",
            ))
            continue

        # Quartile-based decision
        if quartile <= 2:
            deploy = True
            reason = f"Q{quartile} balance={bal} — deploy every cycle"
        elif quartile == 3:
            deploy = (cycle_index % 2 == 0)
            reason = f"Q3 balance={bal} — deploy every 2nd cycle (cycle {cycle_index})"
        else:
            deploy = (cycle_index % 4 == 0)
            reason = f"Q4 balance={bal} — deploy every 4th cycle (cycle {cycle_index})"

        decisions.append(DeployDecision(
            legion_name=name, deploy=deploy, quartile=quartile, reason=reason,
        ))

    return decisions


def _read_legion_balances(
    legion_to_ants: dict[str, list[str]],
    treasury_path: pathlib.Path,
) -> dict[str, int]:
    """Sum per-ant balances per legion. Missing treasury → all zeros."""
    if not treasury_path.is_file():
        return {name: 0 for name in legion_to_ants}

    try:
        raw = json.loads(treasury_path.read_text())
    except (json.JSONDecodeError, OSError):
        return {name: 0 for name in legion_to_ants}

    accounts = raw.get("accounts") or raw.get("ants") or {}
    if not accounts and "ledger" in raw:
        # Reconstruct
        accounts = {}
        for e in raw.get("ledger", []):
            n = e.get("ant") or e.get("ant_name")
            if not n:
                continue
            amt = e.get("amount", 0)
            accounts.setdefault(n, {"balance": 0})
            accounts[n]["balance"] = accounts[n].get("balance", 0) + amt

    out: dict[str, int] = {}
    for legion_name, ants in legion_to_ants.items():
        out[legion_name] = sum(
            accounts.get(a, {}).get("balance", 0) for a in ants
        )
    return out
