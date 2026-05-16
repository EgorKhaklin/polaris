"""ant_readme_counts — verify README.md count claims match reality.

Slice: `README.md` "Polaris in numbers" block.

Local rule: the README's headline counts (tables, procedures,
routes, ai-* scripts, structural invariants) must be within a
small tolerance of reality. If any are off by more than the
tolerance, deposit a `drift` pheromone.

This is the principes (T2) for Legio Docs — medium effort: grep
counts from disk, compare to README claims, surface the deltas.
Slower than Tier 1 (structure check) but cheaper than Tier 3
(cross-reference scan).
"""

from __future__ import annotations

import re

from polaris_swarm.base import Ant, AntFinding, KIND_DRIFT


def _count(text: str, pattern: str) -> int:
    return len(re.findall(pattern, text, re.MULTILINE))


class AntReadmeCounts(Ant):
    NAME = "ant_readme_counts"
    DESCRIPTION = "Pheromones README.md count claims drifting from reality."

    def scan(self) -> list[AntFinding]:
        findings: list[AntFinding] = []
        readme = self._read("README.md")
        if readme is None:
            return findings

        # Reality probes — each one a different file/grep.
        # Tables: count CREATE TABLE in schema
        schema = self._read("polaris_sql", "01_schema.sql") or ""
        actual_tables = _count(schema, r"^CREATE TABLE \w+")
        # Routes: count @app.route in app.py
        app_py = self._read("polaris_web", "app.py") or ""
        actual_routes = _count(app_py, r"^@app\.route\(")
        # ai-* scripts
        scripts_dir = self.root / "scripts"
        actual_scripts = (
            len(list(scripts_dir.glob("ai-*.sh"))) if scripts_dir.is_dir() else 0
        )

        # Each tuple: (label, regex extracting claimed count from README,
        # actual_value, tolerance)
        checks = [
            ("tables",     r"\b(\d+) tables\b",            actual_tables,  1),
            ("routes",     r"\b(\d+) HTTP routes\b",       actual_routes,  1),
            ("ai-scripts", r"\b(\d+) ai-\* scripts\b",     actual_scripts, 1),
        ]
        for label, pat, actual, tol in checks:
            m = re.search(pat, readme)
            if not m:
                # Claim not present in README; ant doesn't fire — that's
                # a Docs-coverage concern handled by ant_docs_structure
                continue
            claimed = int(m.group(1))
            if abs(claimed - actual) > tol:
                findings.append(AntFinding(
                    node_id="file:README.md",
                    intensity=3.5,
                    kind=KIND_DRIFT,
                    evidence={
                        "message": (
                            f"README {label} count drift: claims "
                            f"{claimed}, reality {actual} (tolerance ±{tol})"
                        ),
                        "fix_hint": f"update README's '{label}' count",
                    },
                    half_life_hours=72.0,
                ))
        return findings
