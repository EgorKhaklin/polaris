"""soldier_process_alive — checks /tmp/polaris_app.pid against ps.

ALERT if pid file present but the process is gone (zombie pid file
suggests the launcher's stale-pid cleanup didn't run; operator should
investigate).
"""
from __future__ import annotations

import os
import pathlib

from polaris_swarm.soldiers.base import (
    Observation,
    Soldier,
    KIND_INFO,
    KIND_ALERT,
)


PID_FILE = pathlib.Path("/tmp/polaris_app.pid")


class ProcessAliveSoldier(Soldier):
    NAME = "soldier_process_alive"
    DESCRIPTION = "Checks PID file vs actual process; alerts on stale PID"
    INTENSITY = 1.5
    NODE_PREFIX = "infra:process"

    def observe(self) -> list[Observation]:
        out: list[Observation] = []
        if not PID_FILE.is_file():
            # No PID file = no native launcher running. That's
            # benign (operator may be using docker stack instead).
            out.append(Observation(
                node_id=f"{self.NODE_PREFIX}:pid_file",
                value={"present": False},
                kind=KIND_INFO,
            ))
            return out
        try:
            pid = int(PID_FILE.read_text().strip())
        except (OSError, ValueError):
            out.append(Observation(
                node_id=f"{self.NODE_PREFIX}:pid_file",
                value={"present": True, "readable": False},
                kind=KIND_ALERT,
            ))
            return out
        # Signal 0 = "is this PID alive?" without actually signaling
        try:
            os.kill(pid, 0)
            alive = True
        except ProcessLookupError:
            alive = False
        except PermissionError:
            # Process exists but owned by another user. Treat as alive.
            alive = True
        out.append(Observation(
            node_id=f"{self.NODE_PREFIX}:pid_file",
            value={"present": True, "pid": pid, "alive": alive},
            kind=KIND_INFO if alive else KIND_ALERT,
        ))
        return out
