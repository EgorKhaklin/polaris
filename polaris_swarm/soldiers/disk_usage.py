"""soldier_disk_usage — single du sample of POLARIS_STATE_DIR + /tmp/.

DRIFT if > 70% used; ALERT if > 85% used.
"""
from __future__ import annotations

import os
import pathlib
import shutil

from polaris_swarm.soldiers.base import (
    Observation,
    Soldier,
    KIND_INFO,
    KIND_DRIFT,
    KIND_ALERT,
)


# (mount-probe-path, label)
PROBED_MOUNTS: tuple[tuple[str, str], ...] = (
    (os.environ.get("POLARIS_STATE_DIR", "/tmp/polaris-state"), "state_dir"),
    ("/tmp", "tmp"),
)


class DiskUsageSoldier(Soldier):
    NAME = "soldier_disk_usage"
    DESCRIPTION = "Single du sample of state-dir + /tmp; alerts at 70%/85%"
    INTENSITY = 1.5
    NODE_PREFIX = "infra:disk"

    def observe(self) -> list[Observation]:
        out: list[Observation] = []
        for path_str, label in PROBED_MOUNTS:
            path = pathlib.Path(path_str)
            if not path.exists():
                continue
            try:
                usage = shutil.disk_usage(path)
            except OSError:
                continue
            used_pct = (usage.used / usage.total) * 100.0 if usage.total else 0.0
            if used_pct >= 85.0:
                kind = KIND_ALERT
            elif used_pct >= 70.0:
                kind = KIND_DRIFT
            else:
                kind = KIND_INFO
            out.append(Observation(
                node_id=f"{self.NODE_PREFIX}:{label}",
                value={
                    "used_pct": round(used_pct, 1),
                    "free_gb": round(usage.free / (1024**3), 2),
                },
                kind=kind,
            ))
        return out
