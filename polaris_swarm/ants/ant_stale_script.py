"""ant_stale_script — pheromone scripts unmodified for 60+ days.

Slice: every `scripts/ai-*.sh` script.

Local rule: if a script's mtime is older than `STALE_THRESHOLD_DAYS`,
deposit a `curious` pheromone. Intensity scales with months of
silence. Older scripts may be:
  - perfectly stable (intended)
  - quietly orphaned (drift)
  - waiting to be retired (decision needed)

The pheromone surfaces the question; it does not answer it.
Symmetric to the CognitiveWatcher channel that does the same scan
during HYDRA passes.

Determinism: takes optional `at` parameter (runner-supplied)
matching the ant_journal_silence pattern.
"""

from __future__ import annotations

from datetime import datetime, timezone

from polaris_swarm.base import Ant, AntFinding, KIND_CURIOUS


STALE_THRESHOLD_DAYS = 60.0


class AntStaleScript(Ant):
    NAME = "ant_stale_script"
    DESCRIPTION = "Pheromones ai-*.sh scripts older than 60 days."

    def __init__(self, root, seed=None, at: datetime | None = None):
        super().__init__(root, seed=seed)
        self.at = at if at is not None else datetime.now(timezone.utc)

    def scan(self) -> list[AntFinding]:
        findings: list[AntFinding] = []
        scripts_dir = self.root / "scripts"
        if not scripts_dir.is_dir():
            return findings
        for path in sorted(scripts_dir.glob("ai-*.sh")):
            try:
                mtime = datetime.fromtimestamp(
                    path.stat().st_mtime, tz=timezone.utc,
                )
            except OSError:
                continue
            age_days = (self.at - mtime).total_seconds() / 86400.0
            if age_days < STALE_THRESHOLD_DAYS:
                continue
            # Intensity: 60d → 1.0, 120d → 2.0, capped at 8.0 (240d+)
            intensity = round(min(8.0, age_days / 60.0), 3)
            findings.append(AntFinding(
                node_id=f"ai_script:{path.stem}",
                intensity=intensity,
                kind=KIND_CURIOUS,
                evidence={
                    "message": (
                        f"{path.name} hasn't been touched in "
                        f"{age_days:.0f} days"
                    ),
                    "file": f"scripts/{path.name}",
                    "fix_hint": "review for relevance; mark retired or refresh",
                },
                half_life_hours=168.0,  # week-scale fade
            ))
        return findings
