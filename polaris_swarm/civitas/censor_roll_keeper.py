"""CensorRollKeeper — keeper of the roll.

The Censores were Roman magistrates who maintained the **census**:
the official roll of all Roman citizens, their property, their
voting class. They updated the roll on a fixed cadence. They were
the institutional memory of who was in the city.

In the swarm, the Censor maintains `census-roll.json` — a
filesystem-AoR file recording every ant's:

  - `first_seen`: ISO timestamp of first census observation
  - `last_seen`: ISO timestamp of most recent census observation
  - `legion_at_birth`: which legion claimed this ant first
  - `class`: 'ant' (vs future 'citizen' entries)

The Censor compares ALL_ANTS on each pass against the existing
roll:

  - **New ants** (in ALL_ANTS but not in roll) get added to the
    roll AND a "census_birth" finding is deposited.
  - **Returning ants** (in both) get their `last_seen` updated;
    no finding (silent presence is normal).
  - **Missing ants** (in roll but not in ALL_ANTS) get marked
    `retired_at`; **the entry STAYS in the roll** (G14 — census
    is append-only-discipline filesystem AoR; never deleted).

The census-roll.json file is filesystem-AoR per G14. No entry is
ever deleted; entries can only acquire fields. This is the same
discipline as schema-AoR (UPDATE/DELETE rejected by trigger).
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

from polaris_swarm.civitas.base import (
    Citizen, CitizenFinding, CIVITAS_CENSORES,
)


CENSUS_ROLL_PATH = ("polaris_swarm", "civitas", "census-roll.json")


class CensorRollKeeper(Citizen):
    NAME          = "censor_roll_keeper"
    CIVITAS_CLASS = CIVITAS_CENSORES
    DESCRIPTION   = "Censor maintaining the census roll of all ants in the swarm."

    def observe(self, recent_pheromones: list[dict]) -> list[CitizenFinding]:
        findings: list[CitizenFinding] = []

        # Load the current ALL_ANTS roster + legion membership.
        # Note: the Censor IMPORTS the ants registry only as a
        # source of truth for membership. This is allowed —
        # the Censor is a citizen, not an ant; G6 + G11 apply
        # only to ant ↔ ant and ant ↔ legion.
        try:
            from polaris_swarm.ants import ALL_ANTS
            from polaris_swarm.legions import ALL_LEGIONS
        except ImportError:
            return findings
        current: dict[str, str] = {}    # ant.NAME → legion.NAME
        for LegionCls in ALL_LEGIONS:
            for AntCls in LegionCls.ANTS:
                current[AntCls.NAME] = LegionCls.NAME

        # Load existing roll (filesystem AoR).
        roll_path = self.root.joinpath(*CENSUS_ROLL_PATH)
        try:
            existing = json.loads(roll_path.read_text())
            if not isinstance(existing, dict) or "entries" not in existing:
                existing = {"entries": {}}
        except (OSError, json.JSONDecodeError):
            existing = {"entries": {}}

        now_iso = datetime.now(timezone.utc).isoformat()
        entries: dict[str, dict] = existing.get("entries", {})

        # Discover new ants — those in current but not in roll
        new_ants: list[str] = []
        for ant_name, legio_name in current.items():
            if ant_name not in entries:
                entries[ant_name] = {
                    "first_seen": now_iso,
                    "last_seen": now_iso,
                    "legion_at_birth": legio_name,
                    "class": "ant",
                }
                new_ants.append(ant_name)
            else:
                # Returning ant — update last_seen only (additive)
                entries[ant_name]["last_seen"] = now_iso

        # Discover retired ants — in roll, not in current
        retired_this_pass: list[str] = []
        for ant_name in entries:
            if ant_name not in current and "retired_at" not in entries[ant_name]:
                # Only mark retired_at the FIRST time we observe absence.
                # G14: census entries are append-only; once retired_at
                # is set, it stays set.
                entries[ant_name]["retired_at"] = now_iso
                retired_this_pass.append(ant_name)

        # Write the roll back (filesystem AoR — append-only-discipline)
        existing["entries"] = entries
        existing["last_census_taken"] = now_iso
        try:
            roll_path.parent.mkdir(parents=True, exist_ok=True)
            roll_path.write_text(json.dumps(existing, indent=2, sort_keys=True))
        except OSError:
            pass    # graceful — read-only filesystem, dry-run, etc.

        # Deposit findings for new ants observed this pass
        for ant_name in new_ants:
            findings.append(CitizenFinding(
                node_id=f"ant:{ant_name}",
                intensity=2.0,
                kind="info",
                observation_type="census_birth",
                evidence={
                    "message": (
                        f"Censor observation: new ant {ant_name} entered "
                        f"the census (legion: {entries[ant_name]['legion_at_birth']})"
                    ),
                    "ant_name": ant_name,
                    "legion_at_birth": entries[ant_name]["legion_at_birth"],
                    "first_seen": entries[ant_name]["first_seen"],
                },
                half_life_hours=72.0,
            ))
        for ant_name in retired_this_pass:
            findings.append(CitizenFinding(
                node_id=f"ant:{ant_name}",
                intensity=3.5,
                kind="curious",
                observation_type="census_retirement",
                evidence={
                    "message": (
                        f"Censor observation: ant {ant_name} no longer "
                        f"in ALL_ANTS; marking retired_at in the roll"
                    ),
                    "ant_name": ant_name,
                    "retired_at": entries[ant_name]["retired_at"],
                },
                half_life_hours=168.0,    # week-scale — retirements deserve attention
            ))
        return findings
