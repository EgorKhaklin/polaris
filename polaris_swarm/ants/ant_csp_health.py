"""ant_csp_health — verify CSP literal still names script-src 'self'.

Slice: `polaris_web/security.py`.

Local rule: scan for the `Content-Security-Policy` literal. If
`script-src 'self'` is missing OR `'unsafe-inline'` appears in
the script-src clause, deposit an `alert` pheromone. This is the
strongest security signal in the cognitive layer (C5).

Pairs with the SecurityWatcher's channel-1 CSP check during
HYDRA passes; pheromone form makes the check emergent on every
colony pass.
"""

from __future__ import annotations

import re

from polaris_swarm.base import Ant, AntFinding, KIND_ALERT


class AntCspHealth(Ant):
    NAME = "ant_csp_health"
    DESCRIPTION = "Pheromones any drift in security.py's CSP literal."

    def scan(self) -> list[AntFinding]:
        findings: list[AntFinding] = []
        security_py = self._read("polaris_web", "security.py")
        if security_py is None:
            return findings

        # We want the literal to contain "script-src 'self'" and NOT
        # have "'unsafe-inline'" inside any script-src clause.
        if "script-src 'self'" not in security_py:
            findings.append(AntFinding(
                node_id="module:security.py",
                intensity=10.0,                 # max; C5 violation
                kind=KIND_ALERT,
                evidence={
                    "message": "security.py missing `script-src 'self'` literal",
                    "rule": "C5 — CSP is script-src 'self'",
                },
            ))
            return findings

        # Check for 'unsafe-inline' anywhere near a script-src clause.
        # Be conservative: if 'unsafe-inline' appears at ALL in the
        # CSP block, flag it.
        # Approximate the CSP block as the literal `Content-Security-Policy`
        # value the headers helper sets.
        m = re.search(
            r"Content-Security-Policy['\"]?\s*[:=]\s*['\"]([^'\"]+)['\"]",
            security_py,
        )
        if m:
            csp_value = m.group(1)
            if "'unsafe-inline'" in csp_value and "script-src" in csp_value:
                # Locate which clause 'unsafe-inline' is in
                for clause in csp_value.split(";"):
                    clause = clause.strip()
                    if clause.startswith("script-src") and "'unsafe-inline'" in clause:
                        findings.append(AntFinding(
                            node_id="module:security.py",
                            intensity=10.0,
                            kind=KIND_ALERT,
                            evidence={
                                "message": "CSP script-src contains 'unsafe-inline'",
                                "clause": clause,
                                "rule": "C5 — must remain script-src 'self'",
                            },
                        ))
                        break
        return findings
