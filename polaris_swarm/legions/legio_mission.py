"""Legio Mission — Legatus of the mission/done-list domain.

Commands the ants that read MISSION.md and the Sanctum corpus:
done-list arithmetic and Sanctum §VII cross-ref coverage. Doctrine:
TESTUDO — both ants scan independent slices and aggregate cleanly.
"""

from polaris_swarm.legions.base import Legion, Tactic, TacticConfig
from polaris_swarm.ants.ant_done_list_arithmetic import AntDoneListArithmetic
from polaris_swarm.ants.ant_sanctum_outcome import AntSanctumOutcome


class LegioMission(Legion):
    NAME    = "legio_mission"
    DOMAIN  = "mission"
    LEGATUS = "Legatus Mission"
    ANTS    = [AntDoneListArithmetic, AntSanctumOutcome]
    TACTIC  = TacticConfig(tactic=Tactic.TESTUDO)
