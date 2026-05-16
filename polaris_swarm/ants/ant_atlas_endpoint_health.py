"""ant_atlas_endpoint_health — verify the 5 atlas endpoints exist.

Slice: `polaris_web/app.py`.

Local rule: each of the 5 atlas API routes (stats, clusters, points,
events, timeline) must have an `@app.route('/api/atlas/X')`
declaration. If any are missing, deposit an `alert` pheromone.

The PerformanceWatcher times these endpoints during HYDRA passes;
the ant verifies their structural presence on every colony pass.
This is the existence check; PerformanceWatcher does the latency
check. Different layers of the same correctness claim.
"""

from __future__ import annotations

import re

from polaris_swarm.base import Ant, AntFinding, KIND_ALERT


ATLAS_ENDPOINTS = ("stats", "clusters", "points", "events", "timeline")


class AntAtlasEndpointHealth(Ant):
    NAME = "ant_atlas_endpoint_health"
    DESCRIPTION = "Pheromones any missing /api/atlas/* route declarations."

    def scan(self) -> list[AntFinding]:
        findings: list[AntFinding] = []
        app_py = self._read("polaris_web", "app.py")
        if app_py is None:
            return findings
        for name in ATLAS_ENDPOINTS:
            route_re = (
                rf"@app\.route\(['\"]/api/atlas/{name}['\"]"
            )
            if not re.search(route_re, app_py):
                findings.append(AntFinding(
                    node_id=f"route:/api/atlas/{name}",
                    intensity=7.5,
                    kind=KIND_ALERT,
                    evidence={
                        "message": (
                            f"atlas endpoint /api/atlas/{name} not declared "
                            f"in app.py"
                        ),
                    },
                ))
        return findings
