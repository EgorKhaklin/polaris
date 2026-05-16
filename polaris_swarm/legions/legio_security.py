"""Legio Security — Legatus of the security domain.

Commands the C5-CSP guardian. Doctrine: TESTUDO (single ant; the
tactic is trivial but uniform with the other legions). Schema-
level invariants like C5 are the highest-confidence signals in
the system; CSP-drift would be a constitutional emergency, so
the legion always scans on every colony pass.

This is the legion most likely to grow next — additional ants for
CSRF dual-transport, rate-limiter health, role-gating, R6 anti-
revealing are all candidates for Legatus Security's recruitment
authority.
"""

from polaris_swarm.legions.base import Legion, Tactic, TacticConfig
from polaris_swarm.ants.ant_csp_health import AntCspHealth


class LegioSecurity(Legion):
    NAME    = "legio_security"
    DOMAIN  = "security"
    LEGATUS = "Legatus Security"
    ANTS    = [AntCspHealth]
    TACTIC  = TacticConfig(tactic=Tactic.TESTUDO)
