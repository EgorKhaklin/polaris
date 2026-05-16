"""Legio Adversary — Legatus of the C-constraint threat-map domain.

Commands the adversary-walk completeness ant. Doctrine: CUNEUS —
the walk-completeness ant is the wedge-lead; if it fires (a
C-constraint is missing its walk), follower ants would cascade
to investigate.

For now there is only the lead ant. The CUNEUS tactic still
applies — it degrades gracefully to "run the lead only" when no
followers exist yet. As the cohort grows (e.g., adding an ant
that verifies each walk's six canonical sections are present),
the cascade behavior activates automatically.

This is the canonical example of *tactic richness scaling with
cohort growth*: choose the right doctrine today and the structure
already accommodates tomorrow's recruits.
"""

from polaris_swarm.legions.base import Legion, Tactic, TacticConfig
from polaris_swarm.ants.ant_adversary_walk_complete import AntAdversaryWalkComplete


class LegioAdversary(Legion):
    NAME    = "legio_adversary"
    DOMAIN  = "adversary"
    LEGATUS = "Legatus Adversary"
    ANTS    = [AntAdversaryWalkComplete]
    TACTIC  = TacticConfig(
        tactic=Tactic.CUNEUS,
        lead=AntAdversaryWalkComplete,
    )
