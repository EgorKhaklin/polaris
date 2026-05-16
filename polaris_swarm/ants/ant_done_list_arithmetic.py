"""ant_done_list_arithmetic — verify mission done-list counts add up.

Slice: `MISSION.md` done-list sections for v1, v2, Arc D, Arc E.

Local rule: count ✅ / ⬜ / ✗ markers at the START of done-list item
lines in each named section. Counts are compared against the
section's header — closed sections like `(closed 2026-05-12 at
8/8 ✅)` declare their expected done/total inline; active sections
without an explicit count are only checked for total stability.

This is the v8.63 refactor (E2 ship) — Arc E moved from
E1✅ to E1+E2✅, exposing that hardcoded expected counts go stale
the moment a ship lands. The header-driven design adapts
automatically: when Arc E eventually closes with `at 5/5 ✅`,
the ant uses that as ground truth without code changes.

Drift in any of these counts = a real done-list arithmetic
mismatch. Symmetric to MissionWatcher's first channel; pheromone
form makes the check emergent on every colony pass.
"""

from __future__ import annotations

import re

from polaris_swarm.base import Ant, AntFinding, KIND_DRIFT


# (display_name, header_regex, item_prefix_regex, fallback_total)
# fallback_total is the expected total when the header does not
# encode `at N/M ✅`. None means "do not enforce total either."
SECTIONS = (
    ("v1 done-list",        r"^### v1 done-list",
     r"^\d+\. (✅|⬜|✗)",       15),
    ("v2 done-list",        r"^### v2 done-list",
     r"^M2-\d+\. (✅|⬜|✗)",    12),
    ("Arc D (Swarm/HYDRA)", r"^### Arc D — Swarm / HYDRA",
     r"^H\d+\. (✅|⬜|✗)",       8),
    ("Arc E (Mycelium)",    r"^### Arc E — Mycelium",
     r"^E\d+\. (✅|⬜|✗)",       9),    # E1..E9 as of v8.67
)


# Parse `at N/M ✅` from a section header line. Returns (done, total)
# or None if the header doesn't carry a count.
_HEADER_COUNT_RE = re.compile(r"at (\d+)/(\d+) ✅")


class AntDoneListArithmetic(Ant):
    NAME = "ant_done_list_arithmetic"
    DESCRIPTION = "Pheromones MISSION.md done-list arithmetic mismatches."

    def scan(self) -> list[AntFinding]:
        findings: list[AntFinding] = []
        mission = self._read("MISSION.md")
        if mission is None:
            return findings

        for name, header_re, item_re, fallback_total in SECTIONS:
            m = re.search(header_re, mission, re.MULTILINE)
            if not m:
                findings.append(AntFinding(
                    node_id=f"mission:section:{name}",
                    intensity=4.0,
                    kind=KIND_DRIFT,
                    evidence={
                        "message": f"MISSION.md missing section: {name}",
                    },
                ))
                continue

            # Extract the full header line for count parsing.
            line_end = mission.find("\n", m.end())
            header_line = mission[m.start():line_end if line_end > 0 else len(mission)]
            header_count = _HEADER_COUNT_RE.search(header_line)
            if header_count:
                expected_done = int(header_count.group(1))
                expected_total = int(header_count.group(2))
                source = "header"
            else:
                expected_done = None     # active section; done may drift
                expected_total = fallback_total
                source = "fallback"

            # Body extends to the next ## or ### header.
            body_start = m.end()
            next_h = re.search(
                r"^(?:##|###) ", mission[body_start:], re.MULTILINE,
            )
            body_end = body_start + next_h.start() if next_h else len(mission)
            body = mission[body_start:body_end]

            # Count ONLY item-prefix-start markers.
            done_count = 0
            todo_count = 0
            retired_count = 0
            for line_match in re.finditer(item_re, body, re.MULTILINE):
                mark = line_match.group(1)
                if mark == "✅":
                    done_count += 1
                elif mark == "⬜":
                    todo_count += 1
                elif mark == "✗":
                    retired_count += 1
            total = done_count + todo_count + retired_count

            # Total must always match expected_total. Done count is
            # only enforced for sections whose header pins it.
            total_drift = total != expected_total
            done_drift = (
                expected_done is not None and done_count != expected_done
            )
            if total_drift or done_drift:
                findings.append(AntFinding(
                    node_id=f"mission:section:{name}",
                    intensity=5.5,
                    kind=KIND_DRIFT,
                    evidence={
                        "message": (
                            f"{name} done-list arithmetic drift "
                            f"(source={source}): "
                            f"found ✅={done_count} ⬜={todo_count} "
                            f"✗={retired_count} (total={total}); "
                            f"expected ✅={expected_done} total={expected_total}"
                        ),
                    },
                ))
        return findings
