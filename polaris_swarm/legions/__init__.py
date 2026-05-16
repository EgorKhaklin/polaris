"""Mycelium legions — Republican + Imperial cohorts commanding the swarm.

**Legions are NOT Hydra heads** (as of v8.72). They are
organizational units of the Mycelium swarm, named in the Roman
military tradition. The Hydra-9 mythology was relocated from
legions to HYDRA watchers in v8.72 — see
`sanctum/2026-05-13-hydra-mythology-relocation-to-watchers.md`.

**Republican legions (9):** the original Mycelium legions
established during Arc E (v8.62–v8.65): schema, cognitive,
security, mission, adversary, performance, trajectory, substrate,
docs. The count of 9 was historically anchored to the Hydra-9
mythology but is now retained as ship-time provenance — the v8.65
cohort that emerged from the Hydra-nine-heads-completion ship.

**Imperial legions (added v8.71+):** legions created after Arc G
via `sanctum/2026-05-13-arc-g-roman-empire-opening.md`. Phase 1
adds two:

  - **Legio Praetorian** (constitutional guard, TESTUDO)
  - **Legio Engineer** (development acceleration, CUNEUS)

Future legions can only be added via a Sanctum that explicitly
authorizes them (G24).

The Pheromone log records `deposited_by = ant.NAME` for
audit-of-record preservation; the legion identity travels in the
evidence JSONB (`evidence["legio"]`).

**On CM and the immortal head.** CM remains constitutional. Prior
to v8.72 it was framed as "the immortal 10th head" of the
Hydra-on-legions mythology. With the mythology relocated to
watchers, CM is now the immortal head of the Hydra-on-watchers
mythology — the watcher that cannot be cut without losing the
substrate's ability to verify its own claims. CM lives in
`MISSION.md`'s cognitive-substrate section; it does not appear
as a watcher in `polaris_hydra/`. Substitutability per v8.30
applies to every other element of the substrate but not to CM.

Authorized by:
  - v8.62: `sanctum/2026-05-13-arc-e-swarm-intelligence-opening.md`
  - v8.64: `sanctum/2026-05-13-arc-e-legion-structure-with-tactics.md`
  - v8.65: `sanctum/2026-05-13-arc-e-hydra-nine-heads-completion.md`
    (the legion-Hydra mythology that was later relocated)
  - v8.71: `sanctum/2026-05-13-arc-g-roman-empire-opening.md` (Hydra-9 amended)
  - v8.72: `sanctum/2026-05-13-hydra-mythology-relocation-to-watchers.md`
    (mythology moved off legions onto HYDRA watchers; legions are
    organizationally Roman but mythologically just legions)
"""

from polaris_swarm.legions.base import Legion, Tactic, TacticConfig
# Republican legions (Arc E / v8.62-v8.65)
from polaris_swarm.legions.legio_schema import LegioSchema
from polaris_swarm.legions.legio_cognitive import LegioCognitive
from polaris_swarm.legions.legio_security import LegioSecurity
from polaris_swarm.legions.legio_mission import LegioMission
from polaris_swarm.legions.legio_adversary import LegioAdversary
from polaris_swarm.legions.legio_performance import LegioPerformance
from polaris_swarm.legions.legio_trajectory import LegioTrajectory
from polaris_swarm.legions.legio_substrate import LegioSubstrate
from polaris_swarm.legions.legio_docs import LegioDocs
# Imperial legions (Arc G / v8.71+)
from polaris_swarm.legions.legio_praetorian import LegioPraetorian
from polaris_swarm.legions.legio_engineer import LegioEngineer


# Republican legions (Hydra's nine mortal heads, per v8.65 commitment)
REPUBLICAN_LEGIONS = [
    LegioSchema,         # head 1
    LegioCognitive,      # head 2
    LegioSecurity,       # head 3
    LegioMission,        # head 4
    LegioAdversary,      # head 5
    LegioPerformance,    # head 6
    LegioTrajectory,     # head 7
    LegioSubstrate,      # head 8  (v8.65)
    LegioDocs,           # head 9  (v8.65)
]

# Imperial legions (added after Arc G amended Hydra-9 via v8.71 Sanctum)
IMPERIAL_LEGIONS = [
    LegioPraetorian,     # v8.71 — constitutional guard
    LegioEngineer,       # v8.71 — development acceleration
]

# Full registry — Republican first (mythologically primary),
# Imperial after. CM is the immortal 10th head; lives in
# MISSION.md as a principle, not in this registry.
ALL_LEGIONS = REPUBLICAN_LEGIONS + IMPERIAL_LEGIONS


# v9.11 — the twelfth legion, held in reserve.
#
# The current legion count is 11 (9 Republican + 2 Imperial). Eleven
# is structurally unstable in tiling-geometry (cannot be evenly divided;
# Republican-Imperial split 9+2 is asymmetric). Twelve is the natural
# completion (matches astrological houses, dodecagon, the Twelve
# Tables of Roman law).
#
# Rather than create a twelfth legion preemptively (which would be
# a solution looking for a problem), v9.11 documents the twelfth
# slot as DELIBERATELY RESERVED. When a future operational need
# surfaces that genuinely demands a new legion, this slot exists to
# receive it. Until then, the gap is a feature: the system holds
# space for what it does not yet know it needs.
#
# Naming convention: when manifested, the twelfth legion takes its
# name from the operational need that justifies it (e.g., LegioFiscalia
# for treasury-specific governance, LegioPraetoriaSecunda for a
# second constitutional guard, etc.). The name is NOT pre-assigned;
# pre-naming would constrain the manifestation.
#
# Structural invariant (TestWave11V911) pins:
#   - len(ALL_LEGIONS) == 11 (current; the eleventh + twelfth-reserved)
#   - RESERVED_TWELFTH_LEGION_SLOT is named (this constant)
#   - meta/twelfth-legion.md exists and documents the reserve
RESERVED_TWELFTH_LEGION_SLOT: dict = {
    "manifested": False,
    "reserved_at": "v9.11",
    "rationale": (
        "Twelve is the natural completion of the legion count "
        "(matches dodecagon, twelve houses, twelve tables). The "
        "twelfth slot is held in deliberate reserve until an "
        "operational need surfaces that justifies a new legion. "
        "Pre-naming would constrain the manifestation; the slot "
        "exists as a held silence."
    ),
    "manifestation_protocol": (
        "When the twelfth legion's need surfaces (operator-identified "
        "or surfaced by HYDRA), open a Sanctum proposing it. The "
        "Sanctum's §I documents the operational need; §II proposes the "
        "legion's name + scope; §V (decision) authorizes addition to "
        "ALL_LEGIONS. RESERVED_TWELFTH_LEGION_SLOT[\"manifested\"] flips "
        "to True; the structural invariant updates."
    ),
}


__all__ = [
    "Legion", "Tactic", "TacticConfig",
    # Republican
    "LegioSchema", "LegioCognitive", "LegioSecurity", "LegioMission",
    "LegioAdversary", "LegioPerformance", "LegioTrajectory",
    "LegioSubstrate", "LegioDocs",
    # Imperial
    "LegioPraetorian", "LegioEngineer",
    # Groupings
    "REPUBLICAN_LEGIONS", "IMPERIAL_LEGIONS", "ALL_LEGIONS",
    # v9.11 — held silence
    "RESERVED_TWELFTH_LEGION_SLOT",
]
