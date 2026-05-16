"""soldier_route_pinger — HEAD requests against public Polaris routes.

Observes status code + latency for /, /login, /demo, /api/health.
Each route produces one Observation; aggregator groups by node_id.

Constitutional notes:
  - C10: probes ONLY same-host endpoints; no off-host network reads
  - G3: HEAD requests (read-only); never POSTs
  - Graceful-failure: any urllib error returns [] for that route
"""
from __future__ import annotations

import os
import time
import urllib.error
import urllib.request

from polaris_swarm.soldiers.base import (
    Observation,
    Soldier,
    KIND_INFO,
    KIND_DRIFT,
    KIND_ALERT,
)


PROBED_ROUTES: tuple[str, ...] = ("/", "/login", "/demo", "/api/health")


class RoutePingerSoldier(Soldier):
    NAME = "soldier_route_pinger"
    DESCRIPTION = "HEAD probes against public Polaris routes; reports status + latency"
    INTENSITY = 1.0
    NODE_PREFIX = "infra:routes"

    def observe(self) -> list[Observation]:
        port = os.environ.get("POLARIS_PORT", "2222")
        base = f"http://localhost:{port}"
        out: list[Observation] = []
        for route in PROBED_ROUTES:
            url = base + route
            t0 = time.monotonic()
            try:
                req = urllib.request.Request(url, method="HEAD")
                with urllib.request.urlopen(req, timeout=2.0) as resp:
                    status = resp.status
                latency_ms = (time.monotonic() - t0) * 1000.0
                kind = KIND_INFO if 200 <= status < 400 else KIND_DRIFT
                out.append(Observation(
                    node_id=f"{self.NODE_PREFIX}:{route}",
                    value={"status": status, "latency_ms": round(latency_ms, 2)},
                    kind=kind,
                ))
            except (urllib.error.URLError, ConnectionError, OSError, TimeoutError):
                # App down — alert; latency irrelevant.
                out.append(Observation(
                    node_id=f"{self.NODE_PREFIX}:{route}",
                    value={"status": "unreachable"},
                    kind=KIND_ALERT,
                ))
        return out
