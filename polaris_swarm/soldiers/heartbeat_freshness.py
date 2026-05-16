"""soldier_heartbeat_freshness — age of $STATE_DIR/heartbeat.

DRIFT if > 30s; ALERT if > 180s (matches the launcher's
v8.51 stale-heartbeat threshold). The launcher's watch loop
uses 180s to decide a tab is closed; soldier uses the same
boundary for consistency.
"""
from __future__ import annotations

import os
import pathlib
import time

from polaris_swarm.soldiers.base import (
    Observation,
    Soldier,
    KIND_INFO,
    KIND_DRIFT,
    KIND_ALERT,
)


class HeartbeatFreshnessSoldier(Soldier):
    NAME = "soldier_heartbeat_freshness"
    DESCRIPTION = "Reports age of $STATE_DIR/heartbeat (matches launcher's stale threshold)"
    INTENSITY = 1.0
    NODE_PREFIX = "infra:heartbeat"

    def observe(self) -> list[Observation]:
        state_dir = os.environ.get("POLARIS_STATE_DIR", "/tmp/polaris-state")
        hb = pathlib.Path(state_dir) / "heartbeat"
        if not hb.is_file():
            return [Observation(
                node_id=f"{self.NODE_PREFIX}:state",
                value={"present": False},
                kind=KIND_INFO,
            )]
        try:
            age_s = time.time() - hb.stat().st_mtime
        except OSError:
            return []
        if age_s > 180.0:
            kind = KIND_ALERT
        elif age_s > 30.0:
            kind = KIND_DRIFT
        else:
            kind = KIND_INFO
        return [Observation(
            node_id=f"{self.NODE_PREFIX}:state",
            value={"present": True, "age_s": round(age_s, 1)},
            kind=kind,
        )]
