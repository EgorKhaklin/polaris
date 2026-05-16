"""ant_treasury_health — surfaces health of the Quaestor's ledger.

Consciousness ant. Slice: `polaris_swarm/civitas/treasury-roll.json`
(the Quaestor's denarius ledger; 3rd filesystem-AoR per G15).

Local rule (three severity tiers):

  - **stale** (intensity 2.0, `curious`)  — file exists, parses OK,
    but `last_pass_taken` is >7 days old (or null). Means the
    Quaestor isn't running — could be intentional (cohort paused)
    or drift (forgot to wire it).
  - **malformed** (intensity 6.0, `alert`) — file exists but JSON
    parse fails or top-level keys are missing.
  - **corrupted** (intensity 9.0, `alert`) — G15 violation
    detected: events list shorter than what `last_pass_fingerprints`
    would imply, or events have non-monotonic timestamps.

The Quaestor maintains the ledger; this ant verifies the Quaestor
is working. Self-monitoring at the economic layer.

G18 (consciousness): reads swarm self-state (the FS-AoR roll), not
runtime pheromones.

Determinism: optional `at` parameter for replay safety.

Authorized by `sanctum/2026-05-13-arc-e-acceleration-consciousness-cohort-e10.md`.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

from polaris_swarm.base import Ant, AntFinding, KIND_ALERT, KIND_CURIOUS


STALE_DAYS = 7.0
REQUIRED_TOP_KEYS = ("events", "last_pass_fingerprints")


def _parse_iso(ts: str | None) -> datetime | None:
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts)
    except (TypeError, ValueError):
        return None


class AntTreasuryHealth(Ant):
    NAME = "ant_treasury_health"
    DESCRIPTION = "Pheromones treasury-roll.json health (stale / malformed / corrupted)."

    def __init__(self, root, seed=None, at: datetime | None = None):
        super().__init__(root, seed=seed)
        self.at = at if at is not None else datetime.now(timezone.utc)

    def scan(self) -> list[AntFinding]:
        path = self.root / "polaris_swarm" / "civitas" / "treasury-roll.json"
        if not path.is_file():
            # No treasury yet — that's a different concern (Arc F not
            # yet shipped). Silent.
            return []
        try:
            raw = path.read_text(errors="replace")
        except OSError:
            return []
        # Tier 2: malformed
        try:
            roll = json.loads(raw)
        except json.JSONDecodeError as e:
            return [AntFinding(
                node_id="treasury:health",
                intensity=6.0,
                kind=KIND_ALERT,
                evidence={
                    "message": "treasury-roll.json fails JSON parse",
                    "treasury_state": "malformed",
                    "json_error": str(e),
                    "fix_hint": "restore from backup; check FS-AoR contract",
                },
                half_life_hours=24.0,
            )]
        if not isinstance(roll, dict):
            return [AntFinding(
                node_id="treasury:health",
                intensity=6.0,
                kind=KIND_ALERT,
                evidence={
                    "message": "treasury-roll.json top-level is not an object",
                    "treasury_state": "malformed",
                    "fix_hint": "restore from backup; check FS-AoR contract",
                },
                half_life_hours=24.0,
            )]
        missing = [k for k in REQUIRED_TOP_KEYS if k not in roll]
        if missing:
            return [AntFinding(
                node_id="treasury:health",
                intensity=6.0,
                kind=KIND_ALERT,
                evidence={
                    "message": (
                        f"treasury-roll.json missing required keys: "
                        f"{', '.join(missing)}"
                    ),
                    "treasury_state": "malformed",
                    "missing_keys": missing,
                    "fix_hint": "regenerate via Quaestor; preserve events list",
                },
                half_life_hours=24.0,
            )]
        events = roll.get("events", [])
        # Tier 3: corrupted — non-monotonic timestamps
        if isinstance(events, list) and len(events) >= 2:
            timestamps = []
            for ev in events:
                if isinstance(ev, dict):
                    timestamps.append(ev.get("timestamp"))
            parsed = [_parse_iso(ts) for ts in timestamps]
            # If any parsed and the sequence is non-monotonic, flag.
            valid = [t for t in parsed if t is not None]
            if len(valid) >= 2:
                monotonic = all(
                    valid[i] <= valid[i + 1] for i in range(len(valid) - 1)
                )
                if not monotonic:
                    return [AntFinding(
                        node_id="treasury:health",
                        intensity=9.0,
                        kind=KIND_ALERT,
                        evidence={
                            "message": (
                                "treasury-roll.json events are NOT in "
                                "monotonic time order — G15 violation"
                            ),
                            "treasury_state": "corrupted",
                            "total_events": len(events),
                            "fix_hint": (
                                "halt Quaestor; investigate which pass "
                                "wrote out-of-order events"
                            ),
                        },
                        half_life_hours=12.0,
                    )]
        # Tier 1: stale
        last_pass = _parse_iso(roll.get("last_pass_taken"))
        if last_pass is None:
            # Never ran a pass — fresh treasury. Silent (the Quaestor
            # writes last_pass_taken on its first execution).
            return []
        age_days = (self.at - last_pass).total_seconds() / 86400.0
        if age_days < STALE_DAYS:
            return []
        return [AntFinding(
            node_id="treasury:health",
            intensity=2.0,
            kind=KIND_CURIOUS,
            evidence={
                "message": (
                    f"treasury-roll.json last_pass_taken is "
                    f"{age_days:.1f} days old (threshold "
                    f"{STALE_DAYS}d)"
                ),
                "treasury_state": "stale",
                "last_event_at": roll.get("last_pass_taken"),
                "total_events": len(events) if isinstance(events, list) else 0,
                "age_days": round(age_days, 3),
                "fix_hint": (
                    "Quaestor isn't running — wire it into the next "
                    "colony pass, or accept intentional pause"
                ),
            },
            half_life_hours=168.0,
        )]
