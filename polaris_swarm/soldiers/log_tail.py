"""soldier_log_tail — counts ERROR/WARNING in the tail of polaris_app.log.

DRIFT if any WARNING; ALERT if any ERROR. Reports the count + sample
of the most-recent matching line.
"""
from __future__ import annotations

import pathlib
import re

from polaris_swarm.soldiers.base import (
    Observation,
    Soldier,
    KIND_INFO,
    KIND_DRIFT,
    KIND_ALERT,
)


LOG_FILE = pathlib.Path("/tmp/polaris_app.log")
TAIL_LINES = 200
ERROR_RE = re.compile(r"\bERROR\b", re.IGNORECASE)
WARNING_RE = re.compile(r"\bWARNING\b", re.IGNORECASE)


class LogTailSoldier(Soldier):
    NAME = "soldier_log_tail"
    DESCRIPTION = "Counts ERROR/WARNING in the tail of /tmp/polaris_app.log"
    INTENSITY = 1.5
    NODE_PREFIX = "infra:logs"

    def observe(self) -> list[Observation]:
        if not LOG_FILE.is_file():
            return []
        try:
            # Read only the tail to keep this cheap (logs grow fast)
            with LOG_FILE.open("rb") as f:
                f.seek(0, 2)   # end
                size = f.tell()
                # Read approximately TAIL_LINES * 200 bytes from the end
                read_n = min(size, TAIL_LINES * 200)
                f.seek(max(0, size - read_n))
                blob = f.read().decode("utf-8", errors="replace")
        except OSError:
            return []
        lines = blob.splitlines()[-TAIL_LINES:]

        error_count = 0
        warning_count = 0
        last_error = None
        last_warning = None
        for line in lines:
            if ERROR_RE.search(line):
                error_count += 1
                last_error = line[:200]
            elif WARNING_RE.search(line):
                warning_count += 1
                last_warning = line[:200]

        if error_count:
            kind = KIND_ALERT
        elif warning_count:
            kind = KIND_DRIFT
        else:
            kind = KIND_INFO

        return [Observation(
            node_id=f"{self.NODE_PREFIX}:tail",
            value={
                "errors": error_count,
                "warnings": warning_count,
                "tail_lines": len(lines),
                "last_error": last_error,
                "last_warning": last_warning,
            },
            kind=kind,
        )]
