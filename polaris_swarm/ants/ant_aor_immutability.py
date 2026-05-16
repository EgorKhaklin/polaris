"""ant_aor_immutability — verify every AoR table has its trigger.

Slice: every CREATE TABLE in `polaris_sql/01_schema.sql` that is
documented as an audit-of-record instance, paired with the matching
trigger in `polaris_sql/06_triggers.sql`.

Local rule: if an AoR table exists but its append-only trigger
does not, deposit an `alert` pheromone onto that table's brain-map
node. AoR without immutability is the most dangerous schema-layer
drift Polaris can produce.

This ant is structural-domain coverage. Pairs with ant_fk_cascade_guard
(forbidden CASCADE clauses) and the SchemaWatcher.
"""

from __future__ import annotations

import re

from polaris_swarm.base import Ant, AntFinding, KIND_ALERT


# The 10 schema-AoR tables canonical as of v8.62. Filesystem-AoR
# (sanctum/, proposals/, etc.) is out of scope for this ant.
AOR_TABLES = (
    "TokenLifecycleEvent", "VerificationEvent", "AuthAuditLog",
    "EnrollmentStatusEvent", "AnchorBatch", "AgencyTrustAttestation",
    "TokenStateEpoch", "TokenStateEpochLeaf", "DuressEvent", "Pheromone",
)


class AntAorImmutability(Ant):
    NAME = "ant_aor_immutability"
    DESCRIPTION = "Pheromones AoR tables missing append-only triggers."

    def scan(self) -> list[AntFinding]:
        findings: list[AntFinding] = []
        schema = self._read("polaris_sql", "01_schema.sql") or ""
        triggers = self._read("polaris_sql", "06_triggers.sql") or ""
        if not schema or not triggers:
            return findings
        for table in AOR_TABLES:
            # Must have CREATE TABLE
            if not re.search(rf"CREATE TABLE {table}\b", schema):
                findings.append(AntFinding(
                    node_id=f"table:{table.lower()}",
                    intensity=7.0,
                    kind=KIND_ALERT,
                    evidence={
                        "message": f"AoR table {table} declared but CREATE TABLE missing",
                    },
                ))
                continue
            # Must have BEFORE UPDATE OR DELETE trigger on this table
            trig_re = (
                rf"BEFORE\s+UPDATE\s+OR\s+DELETE\s+ON\s+{table}\b"
                r"|BEFORE\s+(?:UPDATE|DELETE)\s+ON\s+" + table + r"\b"
            )
            if not re.search(trig_re, triggers, re.IGNORECASE):
                findings.append(AntFinding(
                    node_id=f"table:{table.lower()}",
                    intensity=6.0,
                    kind=KIND_ALERT,
                    evidence={
                        "message": f"AoR table {table} lacks append-only trigger",
                        "fix_hint": (
                            f"add trg_{table.lower()}_append_only in "
                            f"06_triggers.sql BEFORE UPDATE OR DELETE"
                        ),
                    },
                ))
        return findings
