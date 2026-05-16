"""ant_unbumped_version — surfaces stale v8.X version references in docs.

Acceleration ant. Slice: every `.md` file under the repo root,
`docs/`, `DEVNOTES/`, `meta/`. Excludes `CHANGELOG.md` (historical
record — version references are correct as written), `sanctum/`,
`journal/`, and `proposals/` (all audit-of-record).

Local rule: for each `v8.X` reference outside the historical
record, compare X against the current latest version (parsed from
CHANGELOG's top entry). If a doc references an old version with
delta >= `STALE_DELTA`, deposit a `drift` pheromone with intensity
scaling on the delta.

The point isn't to ban version references in docs — sometimes
"as of v8.42" is exactly right. It's to surface where the version
landmark has drifted far enough that the surrounding prose is
likely also stale.

G17 (acceleration, read-only): only reads docs; never rewrites them.

Determinism: pure file-system scan; no time.

Authorized by `sanctum/2026-05-13-arc-e-acceleration-consciousness-cohort-e10.md`.
"""

from __future__ import annotations

import re

from polaris_swarm.base import Ant, AntFinding, KIND_DRIFT


# Minimum delta from current version before the reference is "stale enough."
# Below this, "as of v8.X" is plausibly intentional history pinning.
STALE_DELTA = 10

# Doc roots scanned (relative to repo root). Files MUST end in .md.
SCAN_DIRS = ("", "docs", "DEVNOTES", "meta")

# Audit-of-record directories — version references are correct as written.
EXCLUDE_PARTS = {"sanctum", "journal", "proposals"}
EXCLUDE_FILES = {"CHANGELOG.md"}

VERSION_RE = re.compile(r"\bv8\.(\d+)\b")
# CHANGELOG header: `## v8.X — YYYY-MM-DD`
LATEST_RE = re.compile(r"^## v8\.(\d+)\s+—", re.MULTILINE)


def _latest_version(text: str) -> int | None:
    """Return the highest v8.X seen in the CHANGELOG's headers, or
    None if no headers can be parsed."""
    if not text:
        return None
    nums = [int(m.group(1)) for m in LATEST_RE.finditer(text)]
    return max(nums) if nums else None


class AntUnbumpedVersion(Ant):
    NAME = "ant_unbumped_version"
    DESCRIPTION = "Pheromones markdown files referencing stale v8.X versions."

    def scan(self) -> list[AntFinding]:
        findings: list[AntFinding] = []
        changelog = self._read("CHANGELOG.md") or ""
        current = _latest_version(changelog)
        if current is None:
            return findings
        seen: set[str] = set()  # Don't double-report the same file
        for sd in SCAN_DIRS:
            base = self.root if sd == "" else self.root / sd
            if not base.is_dir():
                continue
            for path in base.rglob("*.md"):
                # v9.05 / B1: skip venv/ + site-packages/ + caches.
                from polaris_swarm.scan_filters import is_polaris_source
                if not is_polaris_source(path):
                    continue
                if path.name in EXCLUDE_FILES:
                    continue
                if any(part in EXCLUDE_PARTS for part in path.parts):
                    continue
                rel = str(path.relative_to(self.root))
                if rel in seen:
                    continue
                seen.add(rel)
                try:
                    text = path.read_text(errors="replace")
                except OSError:
                    continue
                versions = {int(m.group(1)) for m in VERSION_RE.finditer(text)}
                if not versions:
                    continue
                oldest = min(versions)
                delta = current - oldest
                if delta < STALE_DELTA:
                    continue
                intensity = round(min(7.0, 1.0 + 0.3 * delta), 3)
                findings.append(AntFinding(
                    node_id=f"file:{rel}",
                    intensity=intensity,
                    kind=KIND_DRIFT,
                    evidence={
                        "message": (
                            f"{rel} references v8.{oldest}; current "
                            f"is v8.{current} (delta {delta})"
                        ),
                        "file": rel,
                        "referenced_version": f"v8.{oldest}",
                        "current_version": f"v8.{current}",
                        "delta": delta,
                        "all_referenced": sorted(
                            f"v8.{v}" for v in versions
                        ),
                        "fix_hint": (
                            "review surrounding prose for staleness; "
                            "refresh to current version OR pin "
                            "explicitly to historical context"
                        ),
                    },
                    half_life_hours=168.0,
                ))
        return findings
