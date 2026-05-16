"""Legio Performance — Legatus of the runtime/route surface domain.

Commands the ants that verify routes exist, their docs match, and
the modules backing them have test coverage. Doctrine: TESTUDO —
all ants run independent slices and aggregate.

Cohort grew 2 → 3 in v8.69 (Phase E10): added `ant_test_gap`, the
acceleration ant that surfaces modules under `polaris_web/` /
`polaris_hydra/` without colocated `test_*.py` files. Test
coverage is the precondition for trusting performance metrics —
hence its natural home in this legion.

Authorized by `sanctum/2026-05-13-arc-e-acceleration-consciousness-cohort-e10.md`.
"""

from polaris_swarm.legions.base import Legion, Tactic, TacticConfig
from polaris_swarm.ants.ant_atlas_endpoint_health import AntAtlasEndpointHealth
from polaris_swarm.ants.ant_api_doc_coverage import AntApiDocCoverage
from polaris_swarm.ants.ant_test_gap import AntTestGap


class LegioPerformance(Legion):
    NAME    = "legio_performance"
    DOMAIN  = "performance"
    LEGATUS = "Legatus Performance"
    ANTS    = [AntAtlasEndpointHealth, AntApiDocCoverage, AntTestGap]
    TACTIC  = TacticConfig(tactic=Tactic.TESTUDO)
