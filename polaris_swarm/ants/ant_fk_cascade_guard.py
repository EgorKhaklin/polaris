"""ant_fk_cascade_guard — enforce v8.50's no-FK-CASCADE rule.

Slice: every SQL file under `polaris_sql/`.

Local rule: if any SQL file contains `ON DELETE CASCADE` or
`ON UPDATE CASCADE` (case-insensitive, word-boundary, comments
stripped), deposit an `alert` pheromone. CASCADE would silently
destroy audit-of-record evidence on parent-row deletion; v8.50
codified this as a hard project rule recorded in
`DEVNOTES/audit-of-record.md` and the
`test_no_fk_cascade_in_polaris_sql` structural invariant.

This ant exists so a violation surfaces in the bloom before
someone tries to ship it. Operationally redundant with the
existing test, but the test fires at CI time; the ant fires
on every colony pass and lands in the operator-readable
heatmap.
"""

from __future__ import annotations

import os
import re

from polaris_swarm.base import Ant, AntFinding, KIND_ALERT


_CASCADE_RE = re.compile(
    r"\bON\s+(DELETE|UPDATE)\s+CASCADE\b",
    re.IGNORECASE,
)
_LINE_COMMENT = re.compile(r"--.*$", re.MULTILINE)
_BLOCK_COMMENT = re.compile(r"/\*.*?\*/", re.DOTALL)


def _strip_sql_comments(text: str) -> str:
    text = _BLOCK_COMMENT.sub("", text)
    text = _LINE_COMMENT.sub("", text)
    return text


class AntFkCascadeGuard(Ant):
    NAME = "ant_fk_cascade_guard"
    DESCRIPTION = "Pheromones any ON DELETE/UPDATE CASCADE in polaris_sql/."

    def scan(self) -> list[AntFinding]:
        findings: list[AntFinding] = []
        sql_dir = self.root / "polaris_sql"
        if not sql_dir.is_dir():
            return findings
        for path in sorted(sql_dir.glob("*.sql")):
            text = self._read("polaris_sql", path.name)
            if text is None:
                continue
            stripped = _strip_sql_comments(text)
            for m in _CASCADE_RE.finditer(stripped):
                clause = m.group(0).upper()
                # Find the approximate line number in the original
                line_no = text[:text.upper().find(clause)].count("\n") + 1
                findings.append(AntFinding(
                    node_id=f"file:polaris_sql/{path.name}",
                    intensity=9.0,                  # near-max; this is a hard rule
                    kind=KIND_ALERT,
                    evidence={
                        "message": f"forbidden {clause} clause in {path.name}",
                        "file": f"polaris_sql/{path.name}",
                        "approx_line": line_no,
                        "rule": "v8.50 — no CASCADE on FK relationships",
                        "rationale": "DEVNOTES/audit-of-record.md §No FK CASCADE",
                    },
                ))
        return findings
