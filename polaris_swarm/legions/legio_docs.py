"""Legio Docs — Legatus Memoria.

Republican legion #9 (added v8.65). Guards the explain-itself
surface — how Polaris tells future readers what it is. The
documentation layer is the project's memory; drift here is
invisible at runtime but corrodes future-reader comprehension.

Originally established as the "9th head of the Hydra" in v8.65;
the Hydra mythology was relocated to HYDRA watchers in v8.72.

Cohort grew 3 → 5 in v8.69 (Phase E10): added
`ant_swarm_inventory_drift` (T2 principes — checks meta/ docs
that ant_readme_counts doesn't reach) and `ant_unbumped_version`
(T3 triarii — surfaces stale version-string references).

Doctrine: **TRIPLEX ACIES** (three-line battle order).

The full Roman doctrine, mapped to real cost gradient, post-E10:

  - **Hastati (Tier 1)**: `ant_docs_structure`
      Fastest: just `path.exists()` checks across the post-v8.60
      subdivision. Front line; cheap; runs first. If silent, no
      escalation needed.

  - **Principes (Tier 2)**: `ant_readme_counts`,
    `ant_swarm_inventory_drift`
      Medium: grep README + count schema/route/script reality,
      and cross-check meta-docs (`meta/civitas.md`,
      `meta/denarius.md`, `CLAUDE.md`) against actual counts.
      Runs only if Tier 1 fired — if structure is broken, counts
      are unreliable; fix structure first.

  - **Triarii (Tier 3)**: `ant_devnotes_ships_coverage`,
    `ant_unbumped_version`
      Deepest: cross-reference v2 done-list against
      DEVNOTES/ships/, and surface markdown files with stale
      v8.X version references. Runs only if Tier 2 also fired.
      Reserved for crisis — documentation has drifted in count
      AND in coverage AND in landmark accuracy.

The escalation order is meaningful: each tier presupposes the
prior tier is in order. Documentation correctness is layered.

Authorized by `sanctum/2026-05-13-arc-e-hydra-nine-heads-completion.md`
and extended in `sanctum/2026-05-13-arc-e-acceleration-consciousness-cohort-e10.md`.
"""

from polaris_swarm.legions.base import Legion, Tactic, TacticConfig
from polaris_swarm.ants.ant_docs_structure import AntDocsStructure
from polaris_swarm.ants.ant_readme_counts import AntReadmeCounts
from polaris_swarm.ants.ant_devnotes_ships_coverage import AntDevnotesShipsCoverage
from polaris_swarm.ants.ant_swarm_inventory_drift import AntSwarmInventoryDrift
from polaris_swarm.ants.ant_unbumped_version import AntUnbumpedVersion


class LegioDocs(Legion):
    NAME    = "legio_docs"
    DOMAIN  = "docs"
    LEGATUS = "Legatus Memoria"
    ANTS    = [
        AntDocsStructure,
        AntReadmeCounts,
        AntDevnotesShipsCoverage,
        AntSwarmInventoryDrift,
        AntUnbumpedVersion,
    ]
    TACTIC  = TacticConfig(
        tactic=Tactic.TRIPLEX_ACIES,
        tiers=[
            [AntDocsStructure],                           # hastati (T1)
            [AntReadmeCounts, AntSwarmInventoryDrift],    # principes (T2)
            [AntDevnotesShipsCoverage, AntUnbumpedVersion],  # triarii (T3)
        ],
    )
