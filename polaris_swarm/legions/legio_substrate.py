"""Legio Substrate — Legatus Dependentia.

Republican legion #8 (added v8.65). Guards Polaris's contract
with the external world: what it depends on, what versions, where
the Rust toolchain lives. Without substrate scrutiny, dependency
drift accumulates silently until a fresh checkout fails.

Doctrine: **CUNEUS** (wedge formation).

The wedge-lead is `ant_substrate_catalog`. If the catalog itself
(`DEVNOTES/substrate.md`) is missing primitives, the rest of the
swarm's substrate signals are unmoored. Only when the lead is
silent do the follower ants (in-use Python imports + Rust
toolchain) deploy. Trigger-driven cascade: if substrate.md is
broken, fix substrate.md first; then re-scan downstream.

Originally established as a "Hydra head" in
`sanctum/2026-05-13-arc-e-hydra-nine-heads-completion.md`. In
v8.72 the Hydra mythology was relocated to HYDRA watchers
(`sanctum/2026-05-13-hydra-mythology-relocation-to-watchers.md`);
this legion is now organizationally Republican rather than
mythologically a Hydra head.
"""

from polaris_swarm.legions.base import Legion, Tactic, TacticConfig
from polaris_swarm.ants.ant_substrate_catalog import AntSubstrateCatalog
from polaris_swarm.ants.ant_dependency_in_use import AntDependencyInUse
from polaris_swarm.ants.ant_rust_toolchain import AntRustToolchain


class LegioSubstrate(Legion):
    NAME    = "legio_substrate"
    DOMAIN  = "substrate"
    LEGATUS = "Legatus Dependentia"
    ANTS    = [AntSubstrateCatalog, AntDependencyInUse, AntRustToolchain]
    TACTIC  = TacticConfig(
        tactic=Tactic.CUNEUS,
        lead=AntSubstrateCatalog,
    )
