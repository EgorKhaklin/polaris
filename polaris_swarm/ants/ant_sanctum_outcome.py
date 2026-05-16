"""ant_sanctum_outcome — pheromones for Sanctums lacking §VII cross-refs.

Slice: each Sanctum file under `sanctum/2026-*.md`.

Local rule: if a Sanctum is CLOSED but its §VII Outcome does not name a
CHANGELOG version or link a journal file, deposit a `drift` pheromone
onto the brain-map node for that Sanctum.

This is the Architect-reflection finding that v8.61 closed manually.
The ant exists so any future regression is surfaced automatically: as
soon as a Sanctum is created, the ant will track it; as soon as it
gets a §VII cross-ref, the ant stops complaining (no pheromone next
pass).

Decentralization note: this ant does NOT decide what to do about the
finding. It just deposits the observation. Other ants (or human
operators reading the bloom) interpret the pattern.
"""

from __future__ import annotations

import re

from polaris_swarm.base import (
    Ant, AntFinding, KIND_DRIFT, KIND_INFO, DECAY_HALF_LIFE_HOURS_DEFAULT,
)


# Pattern for "§VII Outcome that names a v8.X version OR links a journal/ path"
_VII_SECTION_RE = re.compile(r"^## VII\. Outcome\b", re.MULTILINE)
_HAS_LINK_RE = re.compile(r"(CHANGELOG|## v8\.|journal/)")


class AntSanctumOutcome(Ant):
    NAME = "ant_sanctum_outcome"
    DESCRIPTION = "Pheromones Sanctums whose §VII lacks CHANGELOG/journal links."

    def scan(self) -> list[AntFinding]:
        findings: list[AntFinding] = []
        sanctum_dir = self.root / "sanctum"
        if not sanctum_dir.is_dir():
            return findings
        for path in sorted(sanctum_dir.glob("2026-*.md")):
            text = self._read("sanctum", path.name) or ""
            # Find §VII section
            m = _VII_SECTION_RE.search(text)
            if not m:
                # No §VII at all — not closed yet, skip
                continue
            vii_body = text[m.end():]
            # Skip if Sanctum is still OPEN (no decision yet)
            if "DECIDED" not in text and "Status:** CLOSED" not in text:
                continue
            if _HAS_LINK_RE.search(vii_body):
                # Has a cross-ref; quiet
                continue
            # Drift: closed Sanctum lacks §VII cross-ref
            slug = path.stem  # "2026-05-13-arc-e-..."
            findings.append(AntFinding(
                node_id=f"sanctum:{slug}",
                intensity=2.5,
                kind=KIND_DRIFT,
                evidence={
                    "message": "§VII Outcome lacks CHANGELOG/journal cross-ref",
                    "file": f"sanctum/{path.name}",
                    "fix_hint": "append '**See:** CHANGELOG ## vX.Y · journal/YYYY-MM-DD.md'",
                },
                half_life_hours=DECAY_HALF_LIFE_HOURS_DEFAULT,
            ))
        return findings
