"""Legio Praetorian — Legatus Custos Constitutionis.

The first **Imperial legion** (added v8.71 / Arc G). Where the
nine Republican legions cover project surface area (schema,
cognitive, security, mission, adversary, performance, trajectory,
substrate, docs), the Praetorian guards the **constitution
itself**: MISSION.md, the four cognitive-substrate principles,
the C1-C10 lattice.

Note: v8.71 framed this addition as bending the "v8.65 Hydra-9
commitment." In v8.72 the Hydra mythology was relocated from
legions to HYDRA watchers, retroactively unloading that
framing — adding an Imperial legion no longer breaks any Hydra
count, only the historical Republican vs Imperial provenance
distinction.

The Roman Praetorian Guard's history was mixed (the Architect
recorded this in §IV of the Arc G Sanctum). In the cognitive
substrate, this risk is structurally mitigated by G24: new
legions require a Sanctum, and the Sanctum that creates a legion
specifies its tactic. The Praetorian here observes; it does
not adjudicate or auction the constitution to the highest bidder.

Doctrine: **TESTUDO** — both ants always scan; constitutional
drift is the kind of thing that wants maximum-defense coverage,
not escalation tiers. If MISSION.md changes silently, BOTH ants
should fire on the next pass.

The cohort:
  - `ant_mission_drift` — anchor presence in MISSION.md (the
    document)
  - `ant_principle_invariant` — implementation presence of the
    four principles (the lived structure)

Both ants are ALERT-capable. The Praetorian's gaze produces
the project's third and fourth ALERT-capable ants (after
`ant_self_model_accuracy` and `ant_legion_doctrine_health` from
v8.69).

Authorized by `sanctum/2026-05-13-arc-g-roman-empire-opening.md`.
"""

from polaris_swarm.legions.base import Legion, Tactic, TacticConfig
from polaris_swarm.ants.ant_mission_drift import AntMissionDrift
from polaris_swarm.ants.ant_principle_invariant import AntPrincipleInvariant


class LegioPraetorian(Legion):
    NAME    = "legio_praetorian"
    DOMAIN  = "constitutional"
    LEGATUS = "Legatus Custos Constitutionis"
    ANTS    = [AntMissionDrift, AntPrincipleInvariant]
    TACTIC  = TacticConfig(tactic=Tactic.TESTUDO)
