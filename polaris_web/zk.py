"""
zk.py — Python wrapper around the polaris_zk Rust binary (R10-1 / M2-1 / v8.23).

The Rust binary lives at `polaris_zk/target/release/polaris-zk` (configurable
via the POLARIS_ZK_BINARY env var). We talk to it via subprocess + JSON over
stdin/stdout. The binary is small; all proof state stays in the pipe.

This is the C3+A4+B3 ship picked in the M2-1 alignment-exploration Sanctum:
  C3 — transparent setup (no ceremony; Plonky2 is FRI-based)
  A4 — Plonky2 SNARK family
  B3 — hybrid-Merkle circuit reusing R10-2 AnchorBatch infrastructure

The schema-level commitment (`TokenStateEpoch.merkle_root`) is the Poseidon
root produced by Plonky2 over the per-token leaf hashes. This is different
from R10-2's SHA3-256 anchoring — two distinct cryptographic commitments
for two distinct primitives. See docs/design/zk-snark.md.
"""

from __future__ import annotations

import hashlib
import json
import os
import pathlib
import subprocess


def _binary_path() -> str:
    """Locate the polaris-zk Rust binary. POLARIS_ZK_BINARY env var wins;
    otherwise default to ../polaris_zk/target/release/polaris-zk."""
    explicit = os.environ.get("POLARIS_ZK_BINARY")
    if explicit:
        return explicit
    here = pathlib.Path(__file__).resolve().parent
    return str(here.parent / "polaris_zk" / "target" / "release" / "polaris-zk")


def _run_subcommand(subcommand: str, payload: dict) -> dict:
    """Invoke the Rust binary's <subcommand> with <payload> on stdin.
    Returns parsed JSON output. Raises RuntimeError with stderr context on
    non-zero exit."""
    binary = _binary_path()
    if not os.path.isfile(binary):
        raise RuntimeError(
            f"polaris-zk binary not found at {binary}. "
            f"Build with `cargo build --release` in polaris_zk/. "
            f"Or override via POLARIS_ZK_BINARY env var."
        )
    proc = subprocess.run(
        [binary, subcommand],
        input=json.dumps(payload).encode("utf-8"),
        capture_output=True,
        timeout=60,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"polaris-zk {subcommand} failed (exit={proc.returncode}): "
            f"stderr={proc.stderr.decode('utf-8', errors='replace')[:500]}"
        )
    return json.loads(proc.stdout.decode("utf-8"))


# ---------------------------------------------------------------------------
# Leaf-seed derivation. The schema layer hands us a (token_id,
# token_value, status, context_set) tuple; we deterministically derive
# the 32-byte leaf-seed that goes into the Merkle tree.
#
# v1 derivation: leaf_seed = SHA3-256(token_id || token_value || context_id).
# A future v2 would extend this to encode the validity timestamp and the
# revocation-list hash for in-circuit predicate enforcement (B1 instead of
# B3). v1 is pure B3 — predicates are filtered at epoch-commitment time;
# the circuit only proves Merkle membership.
# ---------------------------------------------------------------------------

def derive_leaf_seed(token_id: int, token_value: str, context_id: int) -> str:
    """Deterministically derive the 32-byte leaf seed for an epoch leaf.
    Returns hex (64 chars). Used by uc11_close_epoch sample-data path and
    by tests."""
    h = hashlib.sha3_256()
    h.update(f"{token_id}|{token_value}|{context_id}".encode("utf-8"))
    return h.hexdigest()


# ---------------------------------------------------------------------------
# Public API. Polaris callers (Flask routes, sample data, tests) use these.
# ---------------------------------------------------------------------------

def compute_epoch_root(leaves_hex: list[str]) -> str:
    """Compute the Poseidon Merkle root for a set of leaf hashes.
    Each leaf must be 64 hex chars (32 bytes). Returns root as hex."""
    result = _run_subcommand("compute-root", {"leaves_hex": leaves_hex})
    return result["epoch_root_hex"]


def compute_epoch_leaves(leaves_hex: list[str]) -> tuple[str, list[dict]]:
    """Compute root + per-leaf inclusion proofs.
    Returns (root_hex, [{index, leaf_hash, proof_path}...]).
    Used by uc11_close_epoch path to populate TokenStateEpochLeaf rows."""
    result = _run_subcommand("compute-leaves", {"leaves_hex": leaves_hex})
    return result["epoch_root_hex"], result["leaves"]


def generate_proof(
    leaf_seed_hex: str,
    leaf_index: int,
    all_leaves_hex: list[str],
    epoch_id: int,
    context_id: int,
    nonce: int,
) -> dict:
    """Generate a ZK-SNARK proof that the prover knows the witness for
    leaves[leaf_index] in a tree whose root is computed over all_leaves_hex.
    The proof is bound to (epoch_id, context_id, nonce) — see R1, R2, R9
    audit refinements.

    Returns the ProofBundle: {"proof_hex": ..., "public_inputs": {...}}.
    """
    return _run_subcommand(
        "prove",
        {
            "leaf_seed_hex": leaf_seed_hex,
            "leaf_index": leaf_index,
            "all_leaves_hex": all_leaves_hex,
            "epoch_id": epoch_id,
            "context_id": context_id,
            "nonce": nonce,
        },
    )


def verify_proof(proof_bundle: dict) -> bool:
    """Verify a ProofBundle. Returns True if cryptographically valid AND
    the public inputs match the proof's commitment to them."""
    result = _run_subcommand("verify", proof_bundle)
    return bool(result["verified"])


def verify_proof_against_epoch(
    proof_bundle: dict,
    expected_root_hex: str,
    expected_epoch_id: int,
    expected_context_id: int,
    expected_nonce: int,
) -> bool:
    """Verify a proof AND check that the proof's public inputs match the
    epoch we expect. This is the verifier-side entry point for the Flask
    route — it cross-checks the proof's bound (epoch, context, nonce)
    against what the verifier expects, then runs the SNARK verification.

    Returns True only if BOTH the proof verifies AND its public inputs
    match. This is where R1/R2/R9 binding takes effect at the API layer.
    """
    pi = proof_bundle.get("public_inputs", {})
    if pi.get("epoch_root_hex") != expected_root_hex:
        return False
    if int(pi.get("epoch_id", -1)) != int(expected_epoch_id):
        return False
    if int(pi.get("context_id", -1)) != int(expected_context_id):
        return False
    if int(pi.get("nonce", -1)) != int(expected_nonce):
        return False
    return verify_proof(proof_bundle)
