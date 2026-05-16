"""Mycelium Civitas — citizens of the swarm.

Parallel to `polaris_swarm/legions/` and `polaris_swarm/ants/`.
Where legions command ants (military), citizens are civilians
who observe the swarm itself (the Forum, the census, cross-legion
patterns).

The four civic classes:

  - **Plebs** (Plebeians)     — cross-legion forum readers
  - **Equites** (Equestrians) — cross-legion correlators
  - **Augures** (Augurs)      — pattern interpreters (read auspices)
  - **Censores** (Censors)    — keepers of the census roll

Citizens deposit to the same Pheromone table as ants. AoR is
preserved via `deposited_by = citizen.NAME`. Citizen class is in
`evidence.civitas_class`; observation type is in
`evidence.observation_type`.

Authorized by `sanctum/2026-05-13-arc-e-civitas-civilian-classes.md`.
"""

from polaris_swarm.civitas.base import (
    Citizen, CitizenFinding,
    CIVITAS_PLEBS, CIVITAS_EQUITES, CIVITAS_AUGURES, CIVITAS_CENSORES,
    CIVITAS_QUAESTORES, CIVITAS_TRIBUNI_PLEBIS,
    VALID_CIVITAS_CLASSES,
    propose_new_ant,
)
from polaris_swarm.civitas.plebs_forum_watcher import PlebsForumWatcher
from polaris_swarm.civitas.eques_correlator import EquesCorrelator
from polaris_swarm.civitas.augur_bloom_reader import AugurBloomReader
from polaris_swarm.civitas.censor_roll_keeper import CensorRollKeeper
from polaris_swarm.civitas.quaestor_treasurer import QuaestorTreasurer
from polaris_swarm.civitas.tribuni_plebis_watcher import TribuniPlebisWatcher


ALL_CITIZENS = [
    PlebsForumWatcher,        # Plebeians
    EquesCorrelator,          # Equestrians
    AugurBloomReader,         # Augurs
    CensorRollKeeper,         # Censors
    QuaestorTreasurer,        # Quaestores — financial magistrates (Arc F / F1 / v8.68)
    TribuniPlebisWatcher,     # Tribuni Plebis — usability advocates (Arc G / G1 / v8.71)
]


__all__ = [
    "Citizen", "CitizenFinding",
    "CIVITAS_PLEBS", "CIVITAS_EQUITES", "CIVITAS_AUGURES", "CIVITAS_CENSORES",
    "CIVITAS_QUAESTORES", "CIVITAS_TRIBUNI_PLEBIS",
    "VALID_CIVITAS_CLASSES",
    "propose_new_ant",
    "PlebsForumWatcher", "EquesCorrelator", "AugurBloomReader",
    "CensorRollKeeper", "QuaestorTreasurer", "TribuniPlebisWatcher",
    "ALL_CITIZENS",
]
