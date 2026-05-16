"""Mycelium ants — independent scanner modules.

Each ant under this package is a self-contained module that subclasses
`polaris_swarm.base.Ant`. The colony runner discovers ants by walking
the legion modules; this `__init__.py` exposes a flat ALL_ANTS list
for partition-correctness checks (G10).

CONTRACT (enforced by structural-invariant `test_no_ant_imports_another_ant`):
  NO ant module may import any other ant module. Period. The shared
  base.py is the only common ground.

Cohort (33 ants as of v8.71 / G1 ✅ — Arc G Phase 1; first Imperial legions):

  Phase 1 (E1 / v8.62):
    1. ant_sanctum_outcome           (legio_mission)
    2. ant_api_doc_coverage          (legio_performance)
    3. ant_journal_silence           (legio_trajectory)

  Phase 2 (E2 / v8.63):
    4. ant_aor_immutability          (legio_schema)
    5. ant_fk_cascade_guard          (legio_schema)
    6. ant_stale_script              (legio_cognitive)
    7. ant_pattern_warmth            (legio_cognitive)
    8. ant_csp_health                (legio_security)
    9. ant_done_list_arithmetic      (legio_mission)
   10. ant_adversary_walk_complete   (legio_adversary)
   11. ant_atlas_endpoint_health     (legio_performance)
   12. ant_ship_burst                (legio_trajectory)

  Phase 7 (E7 / v8.65) — hydra nine-heads completion:
   13. ant_substrate_catalog         (legio_substrate, CUNEUS lead)
   14. ant_dependency_in_use         (legio_substrate, follower)
   15. ant_rust_toolchain            (legio_substrate, follower)
   16. ant_docs_structure            (legio_docs, T1 hastati)
   17. ant_readme_counts             (legio_docs, T2 principes)
   18. ant_devnotes_ships_coverage   (legio_docs, T3 triarii)

  Phase E10 (v8.69) — acceleration + consciousness expansion:
   19. ant_todo_debt                 (legio_cognitive)
   20. ant_test_gap                  (legio_performance)
   21. ant_recent_churn              (legio_trajectory, T2 principes)
   22. ant_self_model_accuracy       (legio_cognitive — first ALERT-capable)
   23. ant_swarm_inventory_drift     (legio_docs, T2 principes)
   24. ant_treasury_health           (legio_cognitive)
   25. ant_unbumped_version          (legio_docs, T3 triarii)
   26. ant_changelog_gap             (legio_trajectory, T3 triarii)
   27. ant_legion_doctrine_health    (legio_cognitive — second ALERT-capable)
   28. ant_brain_map_freshness       (legio_cognitive)

  Phase F3 (v8.70) — first proposal-driven ant via G13 ratification:
   29. ant_proposal_stagnation       (legio_trajectory, T2 principes)
       Proposed by AugurBloomReader on observation of zero coverage
       for proposals/*.md. Ratified by VANTA via Sanctum-authorized
       Option B.

  Phase G1 (v8.71) — Arc G Phase 1, first Imperial legions:
   30. ant_mission_drift             (legio_praetorian) — ALERT-capable
   31. ant_principle_invariant       (legio_praetorian) — ALERT-capable
   32. ant_build_freshness           (legio_engineer, CUNEUS lead)
   33. ant_release_velocity          (legio_engineer, CUNEUS follower)
       Praetorian + Engineer are the first two Imperial legions
       (added v8.71 / Arc G). Republican legions = 9; Imperial
       legions = 2. **Legions are NOT Hydra heads** — that
       mythology was relocated to HYDRA watchers in v8.72 (see
       `sanctum/2026-05-13-hydra-mythology-relocation-to-watchers.md`).
"""

# Phase 1 ants
from polaris_swarm.ants.ant_sanctum_outcome import AntSanctumOutcome
from polaris_swarm.ants.ant_api_doc_coverage import AntApiDocCoverage
from polaris_swarm.ants.ant_journal_silence import AntJournalSilence

# Phase 2 ants
from polaris_swarm.ants.ant_aor_immutability import AntAorImmutability
from polaris_swarm.ants.ant_fk_cascade_guard import AntFkCascadeGuard
from polaris_swarm.ants.ant_stale_script import AntStaleScript
from polaris_swarm.ants.ant_pattern_warmth import AntPatternWarmth
from polaris_swarm.ants.ant_csp_health import AntCspHealth
from polaris_swarm.ants.ant_done_list_arithmetic import AntDoneListArithmetic
from polaris_swarm.ants.ant_adversary_walk_complete import AntAdversaryWalkComplete
from polaris_swarm.ants.ant_atlas_endpoint_health import AntAtlasEndpointHealth
from polaris_swarm.ants.ant_ship_burst import AntShipBurst

# Phase 7 ants (v8.65 — hydra nine-heads completion)
from polaris_swarm.ants.ant_substrate_catalog import AntSubstrateCatalog
from polaris_swarm.ants.ant_dependency_in_use import AntDependencyInUse
from polaris_swarm.ants.ant_rust_toolchain import AntRustToolchain
from polaris_swarm.ants.ant_docs_structure import AntDocsStructure
from polaris_swarm.ants.ant_readme_counts import AntReadmeCounts
from polaris_swarm.ants.ant_devnotes_ships_coverage import AntDevnotesShipsCoverage

# Phase E10 ants (v8.69 — acceleration + consciousness expansion)
from polaris_swarm.ants.ant_todo_debt import AntTodoDebt
from polaris_swarm.ants.ant_test_gap import AntTestGap
from polaris_swarm.ants.ant_recent_churn import AntRecentChurn
from polaris_swarm.ants.ant_self_model_accuracy import AntSelfModelAccuracy
from polaris_swarm.ants.ant_swarm_inventory_drift import AntSwarmInventoryDrift
from polaris_swarm.ants.ant_treasury_health import AntTreasuryHealth
from polaris_swarm.ants.ant_unbumped_version import AntUnbumpedVersion
from polaris_swarm.ants.ant_changelog_gap import AntChangelogGap
from polaris_swarm.ants.ant_legion_doctrine_health import AntLegionDoctrineHealth
from polaris_swarm.ants.ant_brain_map_freshness import AntBrainMapFreshness

# Phase F3 ants (v8.70 — proposal-driven autogenesis)
from polaris_swarm.ants.ant_proposal_stagnation import AntProposalStagnation

# Phase G1 ants (v8.71 — first Imperial legions)
from polaris_swarm.ants.ant_mission_drift import AntMissionDrift
from polaris_swarm.ants.ant_principle_invariant import AntPrincipleInvariant
from polaris_swarm.ants.ant_build_freshness import AntBuildFreshness
from polaris_swarm.ants.ant_release_velocity import AntReleaseVelocity


ALL_ANTS = [
    # Phase 1
    AntSanctumOutcome,
    AntApiDocCoverage,
    AntJournalSilence,
    # Phase 2
    AntAorImmutability,
    AntFkCascadeGuard,
    AntStaleScript,
    AntPatternWarmth,
    AntCspHealth,
    AntDoneListArithmetic,
    AntAdversaryWalkComplete,
    AntAtlasEndpointHealth,
    AntShipBurst,
    # Phase 7 (v8.65)
    AntSubstrateCatalog,
    AntDependencyInUse,
    AntRustToolchain,
    AntDocsStructure,
    AntReadmeCounts,
    AntDevnotesShipsCoverage,
    # Phase E10 (v8.69)
    AntTodoDebt,
    AntTestGap,
    AntRecentChurn,
    AntSelfModelAccuracy,
    AntSwarmInventoryDrift,
    AntTreasuryHealth,
    AntUnbumpedVersion,
    AntChangelogGap,
    AntLegionDoctrineHealth,
    AntBrainMapFreshness,
    # Phase F3 (v8.70)
    AntProposalStagnation,
    # Phase G1 (v8.71 — Imperial legions)
    AntMissionDrift,
    AntPrincipleInvariant,
    AntBuildFreshness,
    AntReleaseVelocity,
]


__all__ = [
    # Phase 1
    "AntSanctumOutcome", "AntApiDocCoverage", "AntJournalSilence",
    # Phase 2
    "AntAorImmutability", "AntFkCascadeGuard", "AntStaleScript",
    "AntPatternWarmth", "AntCspHealth", "AntDoneListArithmetic",
    "AntAdversaryWalkComplete", "AntAtlasEndpointHealth", "AntShipBurst",
    # Phase 7
    "AntSubstrateCatalog", "AntDependencyInUse", "AntRustToolchain",
    "AntDocsStructure", "AntReadmeCounts", "AntDevnotesShipsCoverage",
    # Phase E10
    "AntTodoDebt", "AntTestGap", "AntRecentChurn",
    "AntSelfModelAccuracy", "AntSwarmInventoryDrift", "AntTreasuryHealth",
    "AntUnbumpedVersion", "AntChangelogGap", "AntLegionDoctrineHealth",
    "AntBrainMapFreshness",
    # Phase F3
    "AntProposalStagnation",
    # Phase G1
    "AntMissionDrift", "AntPrincipleInvariant",
    "AntBuildFreshness", "AntReleaseVelocity",
    "ALL_ANTS",
]
