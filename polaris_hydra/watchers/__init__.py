"""polaris_hydra.watchers — the Hydra's nine canonical heads (v8.72+).

Each watcher monitors one Polaris dimension. Watchers do not call
LLMs; they are deterministic. The HYDRA host (`polaris_hydra.host`)
aggregates watcher reports and is the only LLM caller.

**The Hydra-9 mythology lives here** (since v8.72). The Lernaean
Hydra had nine mortal heads (Apollodorus). HYDRA's nine watchers
match the canonical count. CM is the immortal 10th head —
narrative only, lives in `MISSION.md` as a constitutional
principle, not in this registry.

Phase 1 (v8.37): SchemaWatcher.
Phase 2 (v8.38–v8.42): CognitiveWatcher (v8.38), SecurityWatcher
(v8.39), MissionWatcher, AdversaryWatcher, PerformanceWatcher — one
per ship.
Post-Arc-D (v8.49): TrajectoryWatcher — observes shipping
trajectory rather than current health. Authorized by
`sanctum/2026-05-13-trajectory-watcher-7th-channel.md`.

**Mythology relocation (v8.72):** AntColonyWatcher + CivitasWatcher
— close the runtime-observation gap (the swarm and the citizen
layer became primary in Arc E+F+G but had no dedicated watchers).
Adding them brings HYDRA to nine, completing the canonical Hydra-9
count for the first time at its etymological home. Authorized by
`sanctum/2026-05-13-hydra-mythology-relocation-to-watchers.md`.

Prior to v8.72, the Hydra-9 anchor was on Mycelium legions
(v8.65) — see that ship's Sanctum and CHANGELOG for the
historical reading. v8.72 relocates the mythology to where
its etymology already pointed.
"""

from .adversary_watcher import AdversaryWatcher
from .ant_colony_watcher import AntColonyWatcher
from .base import Finding, Watcher, WatcherReport
from .civitas_watcher import CivitasWatcher
from .cognitive_watcher import CognitiveWatcher
from .mission_watcher import MissionWatcher
from .performance_watcher import PerformanceWatcher
from .schema_watcher import SchemaWatcher
from .security_watcher import SecurityWatcher
from .trajectory_watcher import TrajectoryWatcher

__all__ = [
    "Finding",
    "Watcher",
    "WatcherReport",
    # The nine Hydra heads (v8.72+):
    "SchemaWatcher",
    "CognitiveWatcher",
    "SecurityWatcher",
    "MissionWatcher",
    "AdversaryWatcher",
    "PerformanceWatcher",
    "TrajectoryWatcher",
    "AntColonyWatcher",   # 8th head (v8.72)
    "CivitasWatcher",     # 9th head (v8.72)
]
