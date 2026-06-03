"""ant_changelog_gap — surfaces files modified after the latest CHANGELOG entry.

Acceleration ant. Slice: source files under tracked dirs vs the
mtime of the most-recent file listed under the top CHANGELOG entry.

Local rule: compare each tracked source file's mtime against the
CHANGELOG's latest version-header date (`## v8.X — YYYY-MM-DD`).
Files modified AFTER that date but not yet captured in any
subsequent CHANGELOG entry = `drift` pheromone. This is the gap
between "code changed" and "ship doc updated."

The opposite of `ant_recent_churn` (which surfaces hot files
regardless of their CHANGELOG status). This ant cares specifically
about the documentation gap — what's in the tree but not yet
narrated.

G17 (acceleration, read-only): only checks mtimes; never modifies
files.

Determinism: optional `at` parameter for replay safety. Output
depends only on file mtimes and CHANGELOG.md contents, not on
wall-clock time.

Authorized by `sanctum/2026-05-13-arc-e-acceleration-consciousness-cohort-e10.md`.
"""

from __future__ import annotations

import re
from datetime import datetime, time, timezone

from polaris_swarm.base import Ant, AntFinding, KIND_DRIFT


SCAN_DIRS = (
    "polaris_web", "polaris_hydra", "polaris_swarm",
    "polaris_sql", "scripts",
)
SCAN_EXTS = {".py", ".sh", ".sql", ".js", ".css", ".html"}

# CHANGELOG top header: `## vMAJOR.MINOR — YYYY-MM-DD ...`
# v9.51: was `v8\.` (bit-rotted — matched nothing once CHANGELOG went all-v9.x);
# now version-agnostic so the gap detector tracks the current scheme.
HEADER_RE = re.compile(
    r"^## v\d+\.(\d+)\s+—\s+(\d{4})-(\d{2})-(\d{2})\b",
    re.MULTILINE,
)

# Maximum findings per pass (most-recent first).
MAX_FINDINGS_PER_PASS = 30


def _latest_changelog_date(text: str) -> datetime | None:
    """Return the top (newest) version-header date as a UTC datetime
    at end-of-day (23:59:59), so files modified anywhere on the same
    day don't false-positive. Returns None if no header parseable."""
    if not text:
        return None
    m = HEADER_RE.search(text)
    if not m:
        return None
    try:
        y, mo, d = int(m.group(2)), int(m.group(3)), int(m.group(4))
        return datetime.combine(
            datetime(y, mo, d).date(),
            time(23, 59, 59),
            tzinfo=timezone.utc,
        )
    except (TypeError, ValueError):
        return None


class AntChangelogGap(Ant):
    NAME = "ant_changelog_gap"
    DESCRIPTION = "Pheromones source files modified after the latest CHANGELOG entry."

    def __init__(self, root, seed=None, at: datetime | None = None):
        super().__init__(root, seed=seed)
        self.at = at if at is not None else datetime.now(timezone.utc)

    def scan(self) -> list[AntFinding]:
        text = self._read("CHANGELOG.md") or ""
        threshold = _latest_changelog_date(text)
        if threshold is None:
            return []
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
                if mtime <= threshold:
                    continue
                age_hours = (self.at - mtime).total_seconds() / 3600.0
                rel = str(path.relative_to(self.root))
                candidates.append((age_hours, rel, mtime))
        # Sort newest-first
        candidates.sort(key=lambda x: x[0])
        findings: list[AntFinding] = []
        for age_hours, rel, mtime in candidates[:MAX_FINDINGS_PER_PASS]:
            # Intensity: newer than threshold = warmer; cap at 6.0.
            hours_past = max(
                0.0,
                (mtime - threshold).total_seconds() / 3600.0,
            )
            intensity = round(min(6.0, 2.0 + 0.05 * hours_past), 3)
            findings.append(AntFinding(
                node_id=f"file:{rel}",
                intensity=intensity,
                kind=KIND_DRIFT,
                evidence={
                    "message": (
                        f"{rel} modified after CHANGELOG threshold "
                        f"({threshold.date().isoformat()})"
                    ),
                    "file": rel,
                    "mtime_iso": mtime.isoformat(),
                    "changelog_threshold_iso": threshold.isoformat(),
                    "hours_past_threshold": round(hours_past, 3),
                    "fix_hint": (
                        "if this file changed materially, add a "
                        "CHANGELOG entry; otherwise touch the file's "
                        "mtime to suppress signal"
                    ),
                },
                half_life_hours=72.0,
            ))
        return findings
