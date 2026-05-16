"""soldier_sanctum_freshness — sanctum/ directory file count + mtime.

Tracks the cadence of constitutional decisions. INFO-level (not
alerting); the operator wants to SEE Sanctum activity, not be paged on it.
"""
from __future__ import annotations

import time

from polaris_swarm.soldiers.base import (
    Observation,
    Soldier,
    KIND_INFO,
)


class SanctumFreshnessSoldier(Soldier):
    NAME = "soldier_sanctum_freshness"
    DESCRIPTION = "sanctum/ file count + most-recent mtime; tracks decision cadence"
    INTENSITY = 0.75
    NODE_PREFIX = "constitution:sanctum"

    def observe(self) -> list[Observation]:
        sdir = self.root / "sanctum"
        if not sdir.is_dir():
            return []
        files = [f for f in sdir.iterdir() if f.is_file() and f.suffix == ".md"]
        if not files:
            return [Observation(
                node_id=f"{self.NODE_PREFIX}:files",
                value={"count": 0},
                kind=KIND_INFO,
            )]
        try:
            most_recent = max(f.stat().st_mtime for f in files)
        except OSError:
            return []
        age_days = (time.time() - most_recent) / 86400.0
        return [Observation(
            node_id=f"{self.NODE_PREFIX}:files",
            value={
                "count": len(files),
                "most_recent_age_days": round(age_days, 2),
            },
            kind=KIND_INFO,
        )]
