"""ant_substrate_catalog — verify substrate.md mentions key primitives.

Slice: `DEVNOTES/substrate.md`.

Local rule: the substrate document is Polaris's contract with the
external world (M2-3). It must mention each of the key primitives
Polaris depends on. If any are missing, deposit an `alert`
pheromone on the substrate node. The CUNEUS-lead in Legio
Substrate: when substrate.md itself is broken, downstream
dependency checks become meaningless.
"""

from __future__ import annotations

from polaris_swarm.base import Ant, AntFinding, KIND_ALERT


# Canonical primitives Polaris depends on as of v8.65. New entries
# get added when a new dependency is taken; removed when one is
# retired (Sanctum-class decision).
REQUIRED_PRIMITIVES = (
    "PostgreSQL",       # primary store
    "Plonky2",          # ZK-SNARK prover (R10-1)
    "Flask",            # web framework
    "gunicorn",         # WSGI server
    "psycopg2",         # PG client
    "Werkzeug",         # auth + utilities
    "D3",               # atlas visualization
)


class AntSubstrateCatalog(Ant):
    NAME = "ant_substrate_catalog"
    DESCRIPTION = "Pheromones primitives missing from DEVNOTES/substrate.md."

    def scan(self) -> list[AntFinding]:
        findings: list[AntFinding] = []
        substrate = self._read("DEVNOTES", "substrate.md")
        if substrate is None:
            return [AntFinding(
                node_id="file:DEVNOTES/substrate.md",
                intensity=9.0,
                kind=KIND_ALERT,
                evidence={
                    "message": "DEVNOTES/substrate.md is missing",
                    "rule": "M2-3 — substrate catalog must exist",
                },
            )]
        for primitive in REQUIRED_PRIMITIVES:
            # Case-insensitive substring check — substrate.md uses
            # various forms (PostgreSQL / Postgres / postgres). The
            # canonical name above is the form we verify against;
            # the substring search is forgiving on case.
            if primitive.lower() not in substrate.lower():
                findings.append(AntFinding(
                    node_id="file:DEVNOTES/substrate.md",
                    intensity=6.5,
                    kind=KIND_ALERT,
                    evidence={
                        "message": (
                            f"substrate.md missing required primitive: "
                            f"{primitive}"
                        ),
                        "fix_hint": (
                            f"add a row for {primitive} in the M2-3 "
                            f"substrate catalog"
                        ),
                    },
                ))
        return findings
