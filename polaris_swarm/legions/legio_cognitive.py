"""Legio Cognitive — Legatus of the cognitive-layer domain.

The project's self-monitoring HUB. Commands the ants that scan
the cognitive substrate's own state: script staleness, pattern
warmth, TODO debt, registry-vs-reality, treasury health, legion
doctrine, brain-map freshness.

Cohort grew 2 → 7 in v8.69 (Phase E10 acceleration + consciousness
expansion). Doctrine remains TESTUDO for now — all 7 ants scan
every pass. Per the Sanctum, the shift to TRIPLEX_ACIES is a
deliberate Phase-2+ decision; TESTUDO at 7 ants is operationally
fine (each ant is cheap; the swarm pays a few seconds for
maximum coverage).

Two of the seven (`ant_self_model_accuracy`,
`ant_legion_doctrine_health`) are the first ALERT-capable ants
in the cohort. They surface structural divergence between the
swarm's CLAIMS about itself and its actual state — the consciousness
layer of the swarm.

Authorized by `sanctum/2026-05-13-arc-e-acceleration-consciousness-cohort-e10.md`.
"""

from polaris_swarm.legions.base import Legion, Tactic, TacticConfig
from polaris_swarm.ants.ant_stale_script import AntStaleScript
from polaris_swarm.ants.ant_pattern_warmth import AntPatternWarmth
from polaris_swarm.ants.ant_todo_debt import AntTodoDebt
from polaris_swarm.ants.ant_self_model_accuracy import AntSelfModelAccuracy
from polaris_swarm.ants.ant_treasury_health import AntTreasuryHealth
from polaris_swarm.ants.ant_legion_doctrine_health import AntLegionDoctrineHealth
from polaris_swarm.ants.ant_brain_map_freshness import AntBrainMapFreshness


class LegioCognitive(Legion):
    NAME    = "legio_cognitive"
    DOMAIN  = "cognitive"
    LEGATUS = "Legatus Cognitive"
    ANTS    = [
        # Original (E2)
        AntStaleScript,
        AntPatternWarmth,
        # E10 acceleration (1)
        AntTodoDebt,
        # E10 consciousness (4)
        AntSelfModelAccuracy,
        AntTreasuryHealth,
        AntLegionDoctrineHealth,
        AntBrainMapFreshness,
    ]
    TACTIC  = TacticConfig(tactic=Tactic.TESTUDO)
