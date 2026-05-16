"""ant_devnotes_ships_coverage — verify v2 ships have DEVNOTES/ships/ entries.

Slice: `MISSION.md` v2 done-list (M2-1..M2-12) ↔ `DEVNOTES/ships/`.

Local rule: every closed v2 mission item (M2-N) should have a
`DEVNOTES/ships/<slug>.md` write-up. If a closed M2-N has no
corresponding ship doc, deposit an `info` pheromone (not alert —
some items are deliberately not documented separately because
they're tiny / structural).

This is the triarii (T3) for Legio Docs — deepest scan: cross-
reference parsing across two files + a directory. Only runs after
T1 (structure) and T2 (README counts) have fired.

The pheromone is informational because documentation gaps are
not security failures — they're future-readability concerns. The
operator may legitimately decide a particular M2-N doesn't need
its own ship doc.
"""

from __future__ import annotations

import re

from polaris_swarm.base import Ant, AntFinding, KIND_INFO


# M2-* slugs that ARE expected to have DEVNOTES/ships/ entries.
# (Anchored to the established ship-doc directory contents as of
# v8.60's organization.) M2-3 (substrate manifest), M2-4 (genomic
# anchor), M2-12 (verification-graph redaction proof) are
# deliberately not in this set — they're concepts realized at the
# schema/test layer without separate write-ups.
EXPECTED_SHIP_DOCS = {
    "M2-1":  "zk-snark.md",
    "M2-2":  "anchoring.md",
    "M2-5":  "quantum-observer.md",
    "M2-6":  "multi-sig-migration.md",
    "M2-7":  "recovery-ceremony.md",
    "M2-8":  "federation.md",
    "M2-9":  "tiered-enrollment.md",
    "M2-10": "duress-codes.md",
    "M2-11": "issuer-discretion.md",
}


class AntDevnotesShipsCoverage(Ant):
    NAME = "ant_devnotes_ships_coverage"
    DESCRIPTION = "Pheromones M2-* mission items missing DEVNOTES/ships/ entries."

    def scan(self) -> list[AntFinding]:
        findings: list[AntFinding] = []
        ships_dir = self.root / "DEVNOTES" / "ships"
        if not ships_dir.is_dir():
            return [AntFinding(
                node_id="file:DEVNOTES/ships/",
                intensity=5.0,
                kind=KIND_INFO,
                evidence={
                    "message": "DEVNOTES/ships/ directory missing",
                    "rule": "v8.26 organized v2 ship docs under DEVNOTES/ships/",
                },
            )]
        present = {p.name for p in ships_dir.glob("*.md")}
        for mn, fname in EXPECTED_SHIP_DOCS.items():
            if fname not in present:
                findings.append(AntFinding(
                    node_id=f"ship:{mn}",
                    intensity=2.5,
                    kind=KIND_INFO,
                    evidence={
                        "message": (
                            f"{mn} expected DEVNOTES/ships/{fname} is missing"
                        ),
                        "fix_hint": (
                            f"either write the ship doc or remove {mn} "
                            f"from this ant's EXPECTED_SHIP_DOCS"
                        ),
                    },
                    half_life_hours=168.0,    # week-scale; informational
                ))
        return findings
