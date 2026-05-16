"""Legio Engineer — Legatus Aedile.

The second **Imperial legion** added after Arc G. Roman
context: the *aediles* were the magistrates responsible for
public works — roads, aqueducts, granaries, public games. The
Engineer's domain in the cognitive substrate is the *public
works of the codebase*: build artifacts, release cadence,
shipping velocity.

This legion is deliberately CUNEUS doctrine — the lead ant
(`ant_build_freshness`) pierces first: if build state looks
healthy, no further investigation is needed. If the lead fires,
the follower (`ant_release_velocity`) deploys to characterize
the cadence implications.

The Engineer **does not duplicate** the v8.69 / E10 acceleration
ants under `legio_cognitive` / `legio_performance` /
`legio_trajectory`. Those ants surface source-level debt (TODOs,
test gaps, recent churn, version refs, CHANGELOG gaps); the
Engineer covers the layer ABOVE the source: build artifacts,
vendored assets, release rhythm. The Sanctum §III analysis
called out the duplication risk explicitly; the Engineer's
cohort was scoped to address it.

The cohort:
  - `ant_build_freshness` (LEAD / CUNEUS point) — Docker
    artifacts, `__pycache__` orphans, Rust target staleness,
    vendored-asset version drift.
  - `ant_release_velocity` (follower) — long-term cadence:
    stagnation (≥14d no ship); sustained burst (≥3 consecutive
    days with ships); median version-bump gap.

Authorized by `sanctum/2026-05-13-arc-g-roman-empire-opening.md`.
"""

from polaris_swarm.legions.base import Legion, Tactic, TacticConfig
from polaris_swarm.ants.ant_build_freshness import AntBuildFreshness
from polaris_swarm.ants.ant_release_velocity import AntReleaseVelocity


class LegioEngineer(Legion):
    NAME    = "legio_engineer"
    DOMAIN  = "engineering"
    LEGATUS = "Legatus Aedile"
    ANTS    = [AntBuildFreshness, AntReleaseVelocity]
    TACTIC  = TacticConfig(
        tactic=Tactic.CUNEUS,
        lead=AntBuildFreshness,
    )
