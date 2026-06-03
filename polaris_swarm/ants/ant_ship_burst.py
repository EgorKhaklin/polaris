"""ant_ship_burst — pheromone ship-rate bursts in the CHANGELOG.

Slice: `CHANGELOG.md`'s top-of-file v8.x entries.

Local rule: parse the `## v8.X — YYYY-MM-DD (...)` headers. Group
by date. If any single date carries ≥ `BURST_THRESHOLD` ships,
deposit a `drift` pheromone on that day's node. Mission-creep
signal per the TrajectoryWatcher heuristic; pheromone form lands
the signal in the swarm even when no LLM call happens.

Determinism: scan output depends only on CHANGELOG.md contents,
not on wall-clock time.
"""

from __future__ import annotations

import re
from collections import defaultdict

from polaris_swarm.base import Ant, AntFinding, KIND_DRIFT


BURST_THRESHOLD = 6
# v9.51: was `v8\.` (bit-rotted — matched nothing once CHANGELOG went all-v9.x);
# now version-agnostic so burst days are counted under the current scheme.
HEADER_RE = re.compile(
    r"^## v\d+\.\d+ — (\d{4}-\d{2}-\d{2})\b",
    re.MULTILINE,
)


class AntShipBurst(Ant):
    NAME = "ant_ship_burst"
    DESCRIPTION = "Pheromones CHANGELOG dates with ≥6 ships (mission-creep)."

    def scan(self) -> list[AntFinding]:
        findings: list[AntFinding] = []
        changelog = self._read("CHANGELOG.md")
        if changelog is None:
            return findings
        counts: dict[str, int] = defaultdict(int)
        for m in HEADER_RE.finditer(changelog):
            counts[m.group(1)] += 1
        for date, n in sorted(counts.items()):
            if n < BURST_THRESHOLD:
                continue
            # Intensity scales with size of burst above threshold.
            intensity = round(min(8.5, 2.0 + (n - BURST_THRESHOLD) * 0.5), 3)
            findings.append(AntFinding(
                node_id=f"file:CHANGELOG.md#{date}",
                intensity=intensity,
                kind=KIND_DRIFT,
                evidence={
                    "message": (
                        f"{n} ships landed on {date} (threshold = "
                        f"{BURST_THRESHOLD}); mission-creep signal"
                    ),
                    "date": date,
                    "ship_count": n,
                    "threshold": BURST_THRESHOLD,
                    "interpretation": (
                        "If each ship was authorized + in-scope, this "
                        "is the watcher doing its job, not a problem. "
                        "If the burst was unstructured, slow down."
                    ),
                },
                half_life_hours=72.0,  # 3-day fade for trajectory signals
            ))
        return findings
