"""
merkle.py - the Plonky2 Merkle-tree semantics Polaris's circuit proves, re-done
independently in Python.

What the Polaris circuit proves (polaris_zk/src/lib.rs):
  "I know a leaf L at index i, and a sibling path P, such that hashing L up the
   tree along P produces the public root R."

This module recomputes R two ways:
  - build_root(leaves)          - the full tree, matching `compute-root`
  - root_from_path(leaf, path)  - the inclusion check, matching the in-circuit
                                  verify_merkle_proof_to_cap gadget

Both must agree, bit-for-bit, with the Rust crate. The hashing primitive is the
independent Poseidon in poseidon.py. Encoding conventions are copied from the
Rust crate's hex_to_hash_elements / hash_elements_to_hex so the byte layout
lines up exactly (little-endian, 8 bytes per Goldilocks lane, 4 lanes = 32 bytes
= 64 hex chars).
"""

from __future__ import annotations

from .poseidon import HASH_OUT_ELEMENTS, hash_or_noop, two_to_one
from .poseidon_constants import P

# Must match polaris_zk/src/lib.rs TREE_DEPTH. Depth 14 supports 16,384
# leaves, covering the schema's 10,000-leaf epoch cap. The differential
# test fails loudly if the Rust crate's depth ever diverges.
TREE_DEPTH = 14
ZERO_LEAF_HEX = "0" * 64


def hex_to_elements(hex_str: str) -> list[int]:
    """Decode 64 hex chars (32 bytes) into 4 Goldilocks lanes.

    Matches lib.rs hex_to_hash_elements: little-endian u64 per 8 bytes, then
    reduced mod P (Rust uses from_noncanonical_u64, i.e. reduce, not panic)."""
    raw = bytes.fromhex(hex_str)
    if len(raw) != 32:
        raise ValueError(f"hash must be 32 bytes / 64 hex chars, got {len(raw)} bytes")
    return [
        int.from_bytes(raw[i * 8 : (i + 1) * 8], "little") % P
        for i in range(HASH_OUT_ELEMENTS)
    ]


def elements_to_hex(elements: list[int]) -> str:
    """Encode 4 Goldilocks lanes into 64 hex chars.

    Matches lib.rs hash_elements_to_hex: canonical u64 per lane, little-endian."""
    if len(elements) != HASH_OUT_ELEMENTS:
        raise ValueError("expected 4 elements")
    out = bytearray()
    for e in elements:
        out += (e % P).to_bytes(8, "little")
    return out.hex()


def _pad_leaves(leaves_hex: list[str]) -> list[str]:
    """Pad with the zero-leaf up to 2^TREE_DEPTH, matching pad_leaves_to_full_depth."""
    cap = 1 << TREE_DEPTH
    if not leaves_hex:
        raise ValueError("cannot build a Merkle tree from an empty leaf set")
    if len(leaves_hex) > cap:
        raise ValueError(f"too many leaves ({len(leaves_hex)}); depth {TREE_DEPTH} caps at {cap}")
    return list(leaves_hex) + [ZERO_LEAF_HEX] * (cap - len(leaves_hex))


def build_root(leaves_hex: list[str]) -> str:
    """Compute the epoch Merkle root over a leaf set. Mirrors compute_epoch_root.

    Leaf digest = hash_or_noop(leaf) (a no-op pad for 4-element leaves).
    Internal node = two_to_one(left, right). Pairs adjacent siblings
    (even index = left, odd index = right), bottom up, for cap_height = 0."""
    padded = _pad_leaves(leaves_hex)
    level = [hash_or_noop(hex_to_elements(h)) for h in padded]
    while len(level) > 1:
        level = [two_to_one(level[2 * j], level[2 * j + 1]) for j in range(len(level) // 2)]
    return elements_to_hex(level[0])


def root_from_path(leaf_hex: str, leaf_index: int, sibling_path_hex: list[str]) -> str:
    """Recompute the root from a single leaf and its inclusion path.

    Mirrors Plonky2's verify_merkle_proof_to_cap: walk the index bits least
    significant first; bit 0 means current is the left child, bit 1 the right."""
    if len(sibling_path_hex) != TREE_DEPTH:
        raise ValueError(f"inclusion path must have {TREE_DEPTH} siblings, got {len(sibling_path_hex)}")
    current = hash_or_noop(hex_to_elements(leaf_hex))
    for i in range(TREE_DEPTH):
        sibling = hex_to_elements(sibling_path_hex[i])
        bit = (leaf_index >> i) & 1
        if bit:
            current = two_to_one(sibling, current)
        else:
            current = two_to_one(current, sibling)
    return elements_to_hex(current)


def membership_holds(
    leaf_hex: str, leaf_index: int, sibling_path_hex: list[str], claimed_root_hex: str
) -> bool:
    """True iff the leaf hashes up its path to the claimed root."""
    return root_from_path(leaf_hex, leaf_index, sibling_path_hex) == claimed_root_hex.lower()
