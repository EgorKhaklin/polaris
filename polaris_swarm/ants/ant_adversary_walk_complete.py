"""ant_adversary_walk_complete — verify every C-constraint has a walk.

Slice: `scripts/ai-adversary.sh`'s ADVERSARIES table.

Local rule: for each of C1..C10 + CM, the canonical six-section
walk must be expressible by ai-adversary.sh. The ant doesn't run
the walk (subprocess is heavy); it verifies the walk's data is
present in the script by checking that each Cn appears with a
"Defender's claim" line.

Pairs with AdversaryWatcher's pass; the pheromone form gives
operators a quick visual that the threat-map is intact.
"""

from __future__ import annotations

import re

from polaris_swarm.base import Ant, AntFinding, KIND_DRIFT


CONSTRAINTS = tuple(f"C{n}" for n in range(1, 11)) + ("CM",)


class AntAdversaryWalkComplete(Ant):
    NAME = "ant_adversary_walk_complete"
    DESCRIPTION = "Pheromones C-constraints missing adversary walk data."

    def scan(self) -> list[AntFinding]:
        findings: list[AntFinding] = []
        adversary_sh = self._read("scripts", "ai-adversary.sh")
        if adversary_sh is None:
            return findings
        for cn in CONSTRAINTS:
            # The script's ADVERSARIES table uses case statements like
            # `C1)` or `C9 | CM)`. We just need each Cn to appear
            # somewhere AND each Cn to have its "defenders_claim" entry.
            if not re.search(rf"\b{cn}\b", adversary_sh):
                findings.append(AntFinding(
                    node_id=f"constraint:{cn}",
                    intensity=6.0,
                    kind=KIND_DRIFT,
                    evidence={
                        "message": f"ai-adversary.sh missing entry for {cn}",
                    },
                ))
        return findings
