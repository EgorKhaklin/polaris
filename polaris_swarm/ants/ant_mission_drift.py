"""ant_mission_drift — Praetorian-class observation of MISSION.md drift.

Arc G / G1 — Legio Praetorian. The Praetorian Guard's original
Roman function was to guard the emperor's person. In the
cognitive substrate, MISSION.md is the constitution; this ant
guards its surface against silent drift.

Slice: `MISSION.md` content snapshot vs the structural-constants
declared in `meta/structural-constants.json`. Specifically:

  - The cognitive-substrate section must name the four
    principles by their canonical labels: "Sanctum",
    "Audit-of-record", "Risk classes", "CM".
  - The C1-C10 constraints must each appear in MISSION.md
    (textual presence; the static suite enforces semantic
    correctness).
  - The "What this section is NOT" block must be present —
    this is the substitutability clause from v8.30.

Local rule: any missing canonical element = `alert` pheromone
at intensity 8.0. The Praetorian's job is to fire LOUDLY when
the constitution is touched; this ant is a tripwire, not a
nuance.

G21 (Praetorian observability): observes constitutional
artifacts only. Never observes runtime behavior; never deposits
on user-facing nodes. The Praetorian's gaze is inward at the
constitution.

Determinism: pure text scan; no time, no randomness.

Authorized by `sanctum/2026-05-13-arc-g-roman-empire-opening.md`.
"""

from __future__ import annotations

import re

from polaris_swarm.base import Ant, AntFinding, KIND_ALERT


# Canonical constitutional surface — anchor strings the Praetorian
# expects in MISSION.md. Each is REQUIRED. If any disappears,
# the Praetorian fires.
REQUIRED_ANCHORS = (
    # Four principles
    "Sanctum",
    "Audit-of-record",
    "Risk classes",
    # CM (canonical capitalization)
    "CM",
    # Substitutability clause
    "What this section is NOT",
    # The constitutional preamble idea
    "cognitive substrate",
)

# C1..C10 must each appear at least once
C_CONSTRAINTS = tuple(f"C{i}" for i in range(1, 11))


class AntMissionDrift(Ant):
    NAME = "ant_mission_drift"
    DESCRIPTION = "Praetorian: ALERT if MISSION.md's constitutional surface is missing canonical anchors."

    def scan(self) -> list[AntFinding]:
        findings: list[AntFinding] = []
        mission = self._read("MISSION.md") or ""
        if not mission:
            return [AntFinding(
                node_id="constitution:MISSION.md",
                intensity=10.0,
                kind=KIND_ALERT,
                evidence={
                    "message": "MISSION.md is missing or unreadable",
                    "fix_hint": "MISSION.md is the constitution; restore from git",
                },
                half_life_hours=12.0,
            )]
        # Check required anchors
        missing_anchors = [a for a in REQUIRED_ANCHORS if a not in mission]
        if missing_anchors:
            findings.append(AntFinding(
                node_id="constitution:MISSION.md#anchors",
                intensity=8.0,
                kind=KIND_ALERT,
                evidence={
                    "message": (
                        f"MISSION.md missing canonical anchor(s): "
                        f"{', '.join(missing_anchors)}"
                    ),
                    "missing_anchors": missing_anchors,
                    "fix_hint": (
                        "restore canonical anchor; if removal was "
                        "intentional, open a Sanctum to amend the "
                        "constitution explicitly"
                    ),
                },
                half_life_hours=12.0,
            ))
        # Check C-constraints presence
        # Use word-boundary so 'C10' doesn't match 'C1' twice.
        present: list[str] = []
        absent: list[str] = []
        for c in C_CONSTRAINTS:
            if re.search(rf"\b{c}\b", mission):
                present.append(c)
            else:
                absent.append(c)
        if absent:
            findings.append(AntFinding(
                node_id="constitution:MISSION.md#c-constraints",
                intensity=8.0,
                kind=KIND_ALERT,
                evidence={
                    "message": (
                        f"MISSION.md missing C-constraint mention(s): "
                        f"{', '.join(absent)}"
                    ),
                    "present": present,
                    "absent": absent,
                    "fix_hint": (
                        "every C1-C10 must be textually present in "
                        "MISSION.md; if a constraint was retired, "
                        "Sanctum-amend the constitution and update "
                        "the structural test"
                    ),
                },
                half_life_hours=12.0,
            ))
        return findings
