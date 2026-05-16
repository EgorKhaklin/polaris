"""soldier_file_mtime — last-modified time of high-signal files.

Observes the age (in days) of CHANGELOG.md, MISSION.md, ROADMAP.md.
DRIFT if older than the per-file threshold (signals doc-staleness).
"""
from __future__ import annotations

import os
import time
from typing import ClassVar

from polaris_swarm.soldiers.base import (
    Observation,
    Soldier,
    KIND_INFO,
    KIND_DRIFT,
)


# (relative_path, drift_threshold_days)
WATCHED_FILES: tuple[tuple[str, float], ...] = (
    ("CHANGELOG.md", 7.0),
    ("MISSION.md", 30.0),
    ("ROADMAP.md", 14.0),
    ("CLAUDE.md", 14.0),
)


class FileMtimeSoldier(Soldier):
    NAME = "soldier_file_mtime"
    DESCRIPTION = "Tracks staleness of CHANGELOG / MISSION / ROADMAP / CLAUDE.md"
    INTENSITY = 1.0
    NODE_PREFIX = "infra:doc_mtime"

    def observe(self) -> list[Observation]:
        out: list[Observation] = []
        now = time.time()
        for relpath, threshold_days in WATCHED_FILES:
            path = self.root.joinpath(relpath)
            if not path.is_file():
                continue
            try:
                mtime = path.stat().st_mtime
            except OSError:
                continue
            age_days = (now - mtime) / 86400.0
            kind = KIND_DRIFT if age_days > threshold_days else KIND_INFO
            out.append(Observation(
                node_id=f"{self.NODE_PREFIX}:{relpath}",
                value={
                    "age_days": round(age_days, 2),
                    "threshold_days": threshold_days,
                },
                kind=kind,
            ))
        return out
