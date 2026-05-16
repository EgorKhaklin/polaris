"""ant_rust_toolchain — verify polaris_zk pins the right Rust toolchain.

Slice: `polaris_zk/rust-toolchain.toml`.

Local rule: Plonky2 requires `feature(specialization)` which is
nightly-only. If the toolchain file is missing OR doesn't pin
nightly, the ZK build silently breaks. Deposit an `alert`
pheromone on the polaris_zk node.

This is a quiet form of supply-chain drift: a contributor could
"upgrade" the toolchain to stable and nothing else in the system
would catch it until someone tried to build polaris_zk.
"""

from __future__ import annotations

from polaris_swarm.base import Ant, AntFinding, KIND_ALERT


class AntRustToolchain(Ant):
    NAME = "ant_rust_toolchain"
    DESCRIPTION = "Pheromones polaris_zk rust-toolchain drift from nightly."

    def scan(self) -> list[AntFinding]:
        findings: list[AntFinding] = []
        toolchain_path = self.root / "polaris_zk" / "rust-toolchain.toml"
        if not toolchain_path.is_file():
            return [AntFinding(
                node_id="file:polaris_zk/rust-toolchain.toml",
                intensity=8.0,
                kind=KIND_ALERT,
                evidence={
                    "message": "polaris_zk/rust-toolchain.toml is missing",
                    "rule": "Plonky2 requires nightly via rust-toolchain.toml",
                },
            )]
        try:
            body = toolchain_path.read_text(errors="replace")
        except OSError as e:
            return [AntFinding(
                node_id="file:polaris_zk/rust-toolchain.toml",
                intensity=5.0,
                kind=KIND_ALERT,
                evidence={
                    "message": f"could not read rust-toolchain.toml: {e}",
                },
            )]
        if "nightly" not in body.lower():
            findings.append(AntFinding(
                node_id="file:polaris_zk/rust-toolchain.toml",
                intensity=9.0,
                kind=KIND_ALERT,
                evidence={
                    "message": (
                        "rust-toolchain.toml does not pin nightly; "
                        "Plonky2 build will fail (needs feature(specialization))"
                    ),
                    "fix_hint": (
                        "ensure the file contains `channel = \"nightly\"`"
                    ),
                },
            ))
        return findings
