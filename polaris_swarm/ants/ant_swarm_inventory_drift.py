"""ant_swarm_inventory_drift — surfaces drift between meta-doc claims and reality.

Consciousness ant. Slice: `meta/civitas.md`, `meta/denarius.md`,
and `CLAUDE.md`. Each carries numeric claims about the swarm
(citizens, ants, legions, tactics, FS-AoR instances, G-guards).
This ant cross-checks each claim against runtime reality.

Local rule: any documented-vs-reality count mismatch deposits a
`drift` pheromone at intensity 3.5 (medium — doc drift is annoying,
not dangerous; the swarm still works).

Sister to `ant_readme_counts` (which scans `README.md`); this ant
covers the meta-layer docs that `ant_readme_counts` doesn't reach.

G18 (consciousness): reads swarm self-state (registries +
documentation), not runtime pheromones.

Determinism: pure file-system scan; no time, no randomness.

Authorized by `sanctum/2026-05-13-arc-e-acceleration-consciousness-cohort-e10.md`.
"""

from __future__ import annotations

import re

from polaris_swarm.base import Ant, AntFinding, KIND_DRIFT


# Each claim entry: (label, doc, regex, reality_callable).
# The regex must capture a single integer group; reality_callable
# is invoked with `self` and returns the actual count. If the doc
# does not contain the regex, that claim is simply not checked
# (graceful — doc may have evolved away from the phrasing).
CLAIMS_SPEC = [
    # meta/civitas.md — citizen-class count claim
    {
        "doc": "meta/civitas.md",
        "label": "civitas-class-count",
        "regex": re.compile(
            r"(\d+)\s+citizen\s+class(?:es)?", re.IGNORECASE,
        ),
        "key":   "citizens",
    },
    # meta/denarius.md — FS-AoR-instance ordinal claim
    {
        "doc": "meta/denarius.md",
        "label": "denarius-fs-aor-instances",
        "regex": re.compile(
            r"(\d+)(?:rd|st|nd|th)?\s+FS-AoR\s+instance", re.IGNORECASE,
        ),
        "key":   "fs_aor",
    },
    # meta/civitas.md — explicit cohort total claim. The regex
    # deliberately matches only cohort-level phrasings ("cohort of N
    # ants", "N-ant cohort", "N ants total") — never per-legion line
    # items like "2 ants" in a table row.
    {
        "doc": "meta/civitas.md",
        "label": "civitas-ant-count",
        "regex": re.compile(
            r"(?:cohort of\s+|swarm of\s+)(\d+)\s+ants?\b"
            r"|(\d+)\s*-?\s*ant cohort\b"
            r"|(\d+)\s+ants?\s+total\b",
            re.IGNORECASE,
        ),
        "key":   "ants",
    },
]


def _count_ant_files(root) -> int:
    pkg = root / "polaris_swarm" / "ants"
    if not pkg.is_dir():
        return 0
    return sum(
        1 for p in pkg.glob("ant_*.py") if p.is_file()
    )


def _count_citizen_files(root) -> int:
    pkg = root / "polaris_swarm" / "civitas"
    if not pkg.is_dir():
        return 0
    # Citizens have varied filenames; count by reading __init__.
    init = pkg / "__init__.py"
    if not init.is_file():
        return 0
    text = init.read_text(errors="replace")
    # The civitas package classes are commonly suffixed with the
    # canonical class names; we count entries inside ALL_CITIZENS
    # by counting class names in the list.
    m = re.search(
        r"ALL_CITIZENS\s*=\s*\[(.*?)\]",
        text, re.DOTALL,
    )
    if not m:
        return 0
    body = m.group(1)
    return sum(
        1 for line in body.split(",")
        if line.split("#", 1)[0].strip()
    )


def _count_fs_aor(root) -> int:
    """Filesystem-AoR instances: count files matching the canonical
    triad — sanctum/ directory, census-roll.json, treasury-roll.json.
    """
    n = 0
    if (root / "sanctum").is_dir():
        n += 1
    if (root / "polaris_swarm" / "civitas" / "census-roll.json").is_file():
        n += 1
    if (root / "polaris_swarm" / "civitas" / "treasury-roll.json").is_file():
        n += 1
    return n


class AntSwarmInventoryDrift(Ant):
    NAME = "ant_swarm_inventory_drift"
    DESCRIPTION = "Pheromones meta-doc claims that disagree with swarm reality."

    def scan(self) -> list[AntFinding]:
        findings: list[AntFinding] = []
        # Build reality snapshot
        reality = {
            "citizens": _count_citizen_files(self.root),
            "ants":     _count_ant_files(self.root),
            "fs_aor":   _count_fs_aor(self.root),
        }
        for spec in CLAIMS_SPEC:
            doc_path = spec["doc"]
            text = self._read(*doc_path.split("/")) or ""
            if not text:
                continue
            m = spec["regex"].search(text)
            if not m:
                continue
            # Regex may have multiple alternation groups; the first
            # non-None group is the captured count.
            captured = next(
                (g for g in m.groups() if g is not None), None,
            )
            try:
                claimed = int(captured) if captured is not None else None
            except (TypeError, ValueError):
                continue
            if claimed is None:
                continue
            actual = reality.get(spec["key"], -1)
            if actual < 0:
                continue
            if claimed == actual:
                continue
            findings.append(AntFinding(
                node_id=f"meta:{doc_path}",
                intensity=3.5,
                kind=KIND_DRIFT,
                evidence={
                    "message": (
                        f"{doc_path}: claims {claimed} for "
                        f"{spec['label']}, actual is {actual}"
                    ),
                    "doc": doc_path,
                    "claim_label": spec["label"],
                    "claim_pattern": spec["regex"].pattern,
                    "claimed": claimed,
                    "actual": actual,
                    "fix_hint": (
                        f"update {doc_path} to reflect actual count "
                        f"({actual})"
                    ),
                },
                half_life_hours=168.0,    # week-scale
            ))
        return findings
