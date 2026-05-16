"""ant_recent_churn — surfaces source files modified in the last 7 days.

Acceleration ant. Slice: source files under `polaris_web/`,
`polaris_hydra/`, `polaris_swarm/`, `polaris_sql/`, `scripts/`.
Files modified within `RECENT_DAYS` deposit an `info` pheromone.

Local rule: most-recent = highest intensity. Operators see where
the heat is — if acceleration is needed, focus on the hottest files
(most recent churn = most context loaded in memory).

Determinism: takes optional `at` parameter (runner-supplied)
matching the `ant_journal_silence` / `ant_stale_script` pattern.
Same `at` + same mtimes = same findings.

Half-life: 168h (week-scale). The bloom shows recent files as
warm-but-fading; this is intended behavior.

Authorized by `sanctum/2026-05-13-arc-e-acceleration-consciousness-cohort-e10.md`.
"""

from __future__ import annotations

from datetime import datetime, timezone

from polaris_swarm.base import Ant, AntFinding, KIND_INFO


RECENT_DAYS = 7.0
SCAN_DIRS = (
    "polaris_web", "polaris_hydra", "polaris_swarm",
    "polaris_sql", "scripts",
)
SCAN_EXTS = {".py", ".sh", ".sql", ".md", ".js", ".css", ".html"}

# Cap how many files we deposit on per pass. The hottest 50 are
# more than enough — the bloom needs signal, not noise.
MAX_FINDINGS_PER_PASS = 50


class AntRecentChurn(Ant):
    NAME = "ant_recent_churn"
    DESCRIPTION = "Pheromones source files modified in the last 7 days."

    def __init__(self, root, seed=None, at: datetime | None = None):
        super().__init__(root, seed=seed)
        self.at = at if at is not None else datetime.now(timezone.utc)

    def scan(self) -> list[AntFinding]:
        from polaris_swarm.scan_filters import is_polaris_source
        candidates: list[tuple[float, str, datetime]] = []
        for sd in SCAN_DIRS:
            base = self.root / sd
            if not base.is_dir():
                continue
            for path in base.rglob("*"):
                if not path.is_file() or path.suffix not in SCAN_EXTS:
                    continue
                # v9.05 / B1: scan_filters rejects venv/, etc.
                if not is_polaris_source(path):
                    continue
                try:
                    mtime_ts = path.stat().st_mtime
                except OSError:
                    continue
                mtime = datetime.fromtimestamp(mtime_ts, tz=timezone.utc)
                age_days = (self.at - mtime).total_seconds() / 86400.0
                if age_days < 0 or age_days > RECENT_DAYS:
                    continue
                rel = path.relative_to(self.root)
                candidates.append((age_days, str(rel), mtime))
        # Sort by recency (smallest age = most recent first), cap.
        candidates.sort(key=lambda x: x[0])
        findings: list[AntFinding] = []
        for age_days, rel, mtime in candidates[:MAX_FINDINGS_PER_PASS]:
            # Intensity scales: 0d → ~7.0, 7d → ~1.0
            intensity = round(min(7.0, 1.0 + 6.0 * (1.0 - age_days / RECENT_DAYS)), 3)
            findings.append(AntFinding(
                node_id=f"file:{rel}",
                intensity=intensity,
                kind=KIND_INFO,
                evidence={
                    "message": (
                        f"{rel} modified {age_days:.1f} days ago"
                    ),
                    "file": rel,
                    "age_days": round(age_days, 3),
                    "mtime_iso": mtime.isoformat(),
                },
                half_life_hours=168.0,  # week-scale fade
            ))
        return findings
