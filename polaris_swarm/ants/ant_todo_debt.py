"""ant_todo_debt — surfaces TODO/FIXME/XXX markers in source.

Acceleration ant. Slice: every `.py`, `.sh`, `.sql`, `.md` file
under `polaris_web/`, `polaris_hydra/`, `polaris_swarm/`,
`polaris_sql/`, `scripts/`. Counts case-insensitive markers in
COMMENTS (not strings, not docstrings — we strip those before
the scan).

Local rule: ≥3 markers in a file = drift; 1-2 = info. Intensity
scales with marker count. Surfaces the highest-debt files so
the next ship can target them.

Authorized by `sanctum/2026-05-13-arc-e-acceleration-consciousness-cohort-e10.md`.
"""

from __future__ import annotations

import re

from polaris_swarm.base import Ant, AntFinding, KIND_DRIFT, KIND_INFO


# Match a comment-leading TODO/FIXME/XXX. We tolerate ANY of
# Python (#), shell (#), SQL (--), Markdown (HTML comment).
_MARKER_RE = re.compile(
    r"(?im)(?:^|[#-/\s])\s*(?:#|--|//)?\s*(TODO|FIXME|XXX|HACK)\b"
)

SCAN_DIRS = (
    "polaris_web", "polaris_hydra", "polaris_swarm",
    "polaris_sql", "scripts",
)
SCAN_EXTS = {".py", ".sh", ".sql", ".md"}


def _strip_docstrings(body: str) -> str:
    """Coarse: remove triple-quoted string blocks. Good enough
    for the scan; perfect parsing would require AST."""
    body = re.sub(r'"""[\s\S]*?"""', "", body)
    body = re.sub(r"'''[\s\S]*?'''", "", body)
    return body


class AntTodoDebt(Ant):
    NAME = "ant_todo_debt"
    DESCRIPTION = "Pheromones source files with TODO/FIXME/XXX/HACK markers."

    def scan(self) -> list[AntFinding]:
        from polaris_swarm.scan_filters import is_polaris_source
        findings: list[AntFinding] = []
        for sd in SCAN_DIRS:
            base = self.root / sd
            if not base.is_dir():
                continue
            for path in base.rglob("*"):
                if not path.is_file() or path.suffix not in SCAN_EXTS:
                    continue
                # v9.05 / B1: scan_filters rejects venv/, site-packages/,
                # __pycache__/, etc.
                if not is_polaris_source(path):
                    continue
                try:
                    body = path.read_text(errors="replace")
                except OSError:
                    continue
                body = _strip_docstrings(body)
                matches = _MARKER_RE.findall(body)
                if not matches:
                    continue
                count = len(matches)
                kinds_found = sorted(set(m.upper() for m in matches))
                rel = path.relative_to(self.root)
                intensity = min(8.0, 2.0 + 0.5 * count)
                kind = KIND_DRIFT if count >= 3 else KIND_INFO
                findings.append(AntFinding(
                    node_id=f"file:{rel}",
                    intensity=round(intensity, 3),
                    kind=kind,
                    evidence={
                        "message": (
                            f"{count} TODO-class marker(s) in "
                            f"{rel} ({', '.join(kinds_found)})"
                        ),
                        "file": str(rel),
                        "marker_count": count,
                        "marker_kinds": kinds_found,
                    },
                    half_life_hours=168.0,    # week-scale
                ))
        return findings
