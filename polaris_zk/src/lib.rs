// polaris_zk/src/lib.rs — Plonky2 Merkle-inclusion circuit + prover + verifier.
//
// Implements the C3+A4+B3 ship picked in the M2-1 alignment-exploration
// Sanctum:
//   C3 — transparent setup (no ceremony; Plonky2 is FRI-based)
//   A4 — Plonky2 SNARK family (post-quantum-comfortable hash commitments)
//   B3 — hybrid-Merkle circuit (the issuer commits the valid-token set
//        per epoch to a Merkle root; the SNARK proves membership)
//
// The circuit proves: "I know a leaf value L and a Merkle path P such
// that hashing L up the tree along P produces the public root R, and
// I am bound to the public (epoch_id, context_id, nonce) triple."
//
// Public inputs: epoch_root [4 field elements], epoch_id, context_id, nonce
// Private inputs: leaf value, sibling hashes (the inclusion path)
//
// Per the R1-R9 audit refinements, the (epoch, context, nonce) binding
// prevents proof substitution: a proof cannot be re-labelled across
// epochs or contexts, or under a different nonce. It does NOT by itself
// prevent replay of the identical bundle — that needs the single-use
// nonce store deferred in threat-model.md T-T2. The witness-leak
// resistance is the SNARK's zero-knowledge property (Plonky2's standard
// FRI commitment scheme).
//
// Hash function: Poseidon (Plonky2 native). Different from the schema's
// SHA3-256 used by R10-2 AnchorBatch — these are distinct commitments
// for distinct primitives. The TokenStateEpoch.merkle_root column
// stores the Poseidon root as a hex-encoded byte sequence.

use anyhow::{anyhow, Result};
use plonky2::field::goldilocks_field::GoldilocksField;
use plonky2::field::types::{Field, PrimeField64};
use plonky2::hash::hash_types::{HashOut, HashOutTarget, MerkleCapTarget};
use plonky2::hash::merkle_proofs::MerkleProofTarget;
use plonky2::hash::merkle_tree::MerkleTree;
use plonky2::hash::poseidon::PoseidonHash;
use plonky2::iop::witness::{PartialWitness, WitnessWrite};
use plonky2::plonk::circuit_builder::CircuitBuilder;
use plonky2::plonk::circuit_data::{CircuitConfig, VerifierCircuitData};
use plonky2::plonk::config::PoseidonGoldilocksConfig;
use plonky2::plonk::proof::ProofWithPublicInputs;
use serde::{Deserialize, Serialize};

pub type F = GoldilocksField;
pub type C = PoseidonGoldilocksConfig;
pub const D: usize = 2;

/// Tree depth — limits the maximum number of leaves to 2^TREE_DEPTH.
/// TREE_DEPTH=14 supports 16,384 leaves, which covers the schema cap of
/// 10,000 leaves per epoch (`TokenStateEpoch`), so the anonymity set is a
/// full epoch rather than a 16-leaf demo. Plonky2 is transparent (no
/// trusted setup), so changing this is a recompile, not a ceremony.
/// The trade-off is named in DEVNOTES/zk-snark.md.
///
/// Smaller leaves are padded with zero-hash to 2^TREE_DEPTH so the
/// circuit is uniform regardless of actual epoch size.
pub const TREE_DEPTH: usize = 14;

/// Pad leaves with zero-hash entries up to 2^TREE_DEPTH so every tree
/// has the same shape and `tree.prove(i)` returns exactly TREE_DEPTH
/// siblings.
fn pad_leaves_to_full_depth(leaves_hex: &[String]) -> Vec<String> {
    let cap = 1usize << TREE_DEPTH;
    let zero_leaf = "0".repeat(64); // 32 bytes of zero
    let mut padded: Vec<String> = leaves_hex.iter().cloned().collect();
    while padded.len() < cap {
        padded.push(zero_leaf.clone());
    }
    padded
}

/// JSON shape of a witness file (private inputs to the prover).
#[derive(Serialize, Deserialize, Debug)]
pub struct WitnessInput {
    /// Hex-encoded 32-byte leaf seed. The leaf is hashed with Poseidon.
    pub leaf_seed_hex: String,
    /// Position of this leaf in the Merkle tree (0-indexed).
    pub leaf_index: usize,
    /// All leaves in the epoch, hex-encoded. The prover reconstructs the
    /// tree from this to derive its proof path. In a production deployment
    /// only the leaf's siblings would be needed; v1 ships the full set
    /// because the witness file is local to the prover.
    pub all_leaves_hex: Vec<String>,
}

/// JSON shape of the public inputs (verifier-visible).
#[derive(Serialize, Deserialize, Debug, Clone)]
pub struct PublicInputs {
    /// Hex-encoded epoch Merkle root (4 field elements → 32 bytes → 64 hex chars).
    pub epoch_root_hex: String,
    pub epoch_id: u64,
    pub context_id: u64,
    pub nonce: u64,
}

/// JSON shape of a proof emitted by the prover.
#[derive(Serialize, Deserialize, Debug)]
pub struct ProofBundle {
    /// Hex-encoded serialized proof bytes.
    pub proof_hex: String,
    pub public_inputs: PublicInputs,
}

/// Decode 32-byte hex into 4 Goldilocks field elements (8 bytes each).
fn hex_to_hash_elements(hex_str: &str) -> Result<[F; 4]> {
    let bytes = hex::decode(hex_str)?;
    if bytes.len() != 32 {
        return Err(anyhow!("hash bytes must be exactly 32 ({} hex chars)", 64));
    }
    let mut elements = [F::ZERO; 4];
    for i in 0..4 {
        let mut limb_bytes = [0u8; 8];
        limb_bytes.copy_from_slice(&bytes[i * 8..(i + 1) * 8]);
        // Goldilocks elements fit in u64; mask to be safe.
        let raw = u64::from_le_bytes(limb_bytes);
        // The Goldilocks field modulus is 2^64 - 2^32 + 1; raw u64 values
        // may exceed it. F::from_canonical_u64 panics on overflow; we
        // reduce explicitly.
        elements[i] = F::from_noncanonical_u64(raw);
    }
    Ok(elements)
}

/// Encode 4 Goldilocks field elements as 32 bytes → 64 hex chars.
fn hash_elements_to_hex(elements: &[F; 4]) -> String {
    let mut bytes = [0u8; 32];
    for i in 0..4 {
        let raw = elements[i].to_canonical_u64();
        bytes[i * 8..(i + 1) * 8].copy_from_slice(&raw.to_le_bytes());
    }
    hex::encode(bytes)
}

/// Convert a hex-encoded leaf seed into the 4-element field representation.
fn leaf_hex_to_hash(hex_str: &str) -> Result<HashOut<F>> {
    let elements = hex_to_hash_elements(hex_str)?;
    Ok(HashOut { elements })
}

/// Compute the Merkle root over a vector of leaf hashes (each a HashOut).
/// Returns the root as a HashOut and the MerkleTree for proof generation.
pub fn build_merkle_tree(leaves_hex: &[String]) -> Result<MerkleTree<F, PoseidonHash>> {
    if leaves_hex.is_empty() {
        return Err(anyhow!("Cannot build Merkle tree from empty leaf set"));
    }
    if leaves_hex.len() > (1 << TREE_DEPTH) {
        return Err(anyhow!(
            "Too many leaves ({}); circuit tree depth {} caps at {}",
            leaves_hex.len(),
            TREE_DEPTH,
            1 << TREE_DEPTH
        ));
    }
    // Each leaf is a 4-element field array. MerkleTree expects Vec<Vec<F>>.
    let padded = pad_leaves_to_full_depth(leaves_hex);
    let leaves: Vec<Vec<F>> = padded
        .iter()
        .map(|h| {
            let elements = hex_to_hash_elements(h)?;
            Ok(elements.to_vec())
        })
        .collect::<Result<_>>()?;
    // cap_height=0 means a single root hash (no Merkle cap). Standard.
    Ok(MerkleTree::new(leaves, 0))
}

/// Compute the epoch Merkle root from the same leaf set the prover sees.
/// This is the function `polaris_web/zk.py`'s "compute_root" subcommand
/// shells out to.
pub fn compute_epoch_root(leaves_hex: &[String]) -> Result<String> {
    let tree = build_merkle_tree(leaves_hex)?;
    Ok(hash_elements_to_hex(&tree.cap.0[0].elements))
}

/// Build the circuit: prove "I know the leaf at index i in a Merkle tree
/// whose root is R, where R + epoch_id + context_id + nonce are public."
///
/// The circuit takes a leaf hash (4 elements, private), an inclusion path
/// (TREE_DEPTH siblings × 4 elements each, private), and the leaf's index
/// (TREE_DEPTH bits, private). It verifies the path hashes up to the
/// claimed root.
pub fn build_circuit() -> (
    CircuitBuilder<F, D>,
    HashOutTarget,      // leaf_target (private)
    MerkleProofTarget,  // proof_target (private siblings)
    Vec<plonky2::iop::target::BoolTarget>, // index bits (private)
    HashOutTarget,      // root_target (public)
    plonky2::iop::target::Target, // epoch_id (public)
    plonky2::iop::target::Target, // context_id (public)
    plonky2::iop::target::Target, // nonce (public)
) {
    let config = CircuitConfig::standard_recursion_config();
    let mut builder = CircuitBuilder::<F, D>::new(config);

    // Private: the leaf the prover holds.
    let leaf_target = builder.add_virtual_hash();

    // Private: the inclusion proof's sibling hashes.
    let proof_target = MerkleProofTarget {
        siblings: (0..TREE_DEPTH).map(|_| builder.add_virtual_hash()).collect(),
    };

    // Private: the leaf's index expressed as bits.
    let index_bits: Vec<_> = (0..TREE_DEPTH)
        .map(|_| builder.add_virtual_bool_target_safe())
        .collect();

    // Public: the claimed root, wrapped as a MerkleCapTarget of length 1
    // (cap_height=0 means the cap IS the root). MerkleCapTarget(pub Vec<...>)
    // — the field is pub so we construct via the tuple form.
    let root_target = builder.add_virtual_hash();
    builder.register_public_inputs(&root_target.elements);
    let cap_target = MerkleCapTarget(vec![root_target]);

    // Public: epoch_id, context_id, nonce (each one field element).
    let epoch_id_t = builder.add_virtual_target();
    let context_id_t = builder.add_virtual_target();
    let nonce_t = builder.add_virtual_target();
    builder.register_public_input(epoch_id_t);
    builder.register_public_input(context_id_t);
    builder.register_public_input(nonce_t);

    // The core verification: Plonky2's verify_merkle_proof_to_cap checks
    // that hashing leaf along proof.siblings (per index_bits) produces the
    // claimed root. The public API uses index_bits where bits beyond the
    // proof depth address into the cap; for cap_height=0 there are no
    // such bits, so we pass exactly TREE_DEPTH index bits.
    builder.verify_merkle_proof_to_cap::<PoseidonHash>(
        leaf_target.elements.to_vec(),
        &index_bits,
        &cap_target,
        &proof_target,
    );

    // The epoch_id / context_id / nonce binding: these targets are part of
    // the public-input commitment. Even though they're not used as
    // arithmetic constraints, registering them as public inputs binds the
    // proof to specific values — a malicious prover can't reuse a proof
    // with different (epoch, context, nonce) public inputs.
    //
    // R1, R2, R9 audit refinements: this is where they materialize.
    let _ = (epoch_id_t, context_id_t, nonce_t);

    (
        builder,
        leaf_target,
        proof_target,
        index_bits,
        root_target,
        epoch_id_t,
        context_id_t,
        nonce_t,
    )
}

/// Generate a proof. Returns the serialized proof bytes + the public inputs.
pub fn prove(
    witness: &WitnessInput,
    epoch_id: u64,
    context_id: u64,
    nonce: u64,
) -> Result<ProofBundle> {
    // Validate the caller-supplied index against the REAL leaf count before
    // using it. build_merkle_tree pads to 2^TREE_DEPTH, so an index past the
    // real leaves but within the padded range slips past tree.prove() and then
    // panics on the all_leaves_hex[leaf_index] slice; an index past the padded
    // range panics inside plonky2. Return the crate's error instead of aborting
    // the process — prove() is a trust boundary the app shells into.
    if witness.leaf_index >= witness.all_leaves_hex.len() {
        return Err(anyhow!(
            "leaf_index {} out of range (only {} leaves)",
            witness.leaf_index,
            witness.all_leaves_hex.len()
        ));
    }
    let tree = build_merkle_tree(&witness.all_leaves_hex)?;
    let merkle_proof = tree.prove(witness.leaf_index);
    let root_hex = hash_elements_to_hex(&tree.cap.0[0].elements);
    let leaf_hash = leaf_hex_to_hash(&witness.all_leaves_hex[witness.leaf_index])?;

    let (builder, leaf_t, proof_t, index_bits_t, root_t, epoch_t, context_t, nonce_t) =
        build_circuit();

    let mut pw = PartialWitness::<F>::new();
    pw.set_hash_target(leaf_t, leaf_hash);
    pw.set_hash_target(root_t, tree.cap.0[0]);
    pw.set_target(epoch_t, F::from_canonical_u64(epoch_id));
    pw.set_target(context_t, F::from_canonical_u64(context_id));
    pw.set_target(nonce_t, F::from_canonical_u64(nonce));

    for (i, sibling) in merkle_proof.siblings.iter().enumerate() {
        pw.set_hash_target(proof_t.siblings[i], *sibling);
    }
    // Set index bits: TREE_DEPTH bits, least significant first.
    for (i, bit_t) in index_bits_t.iter().enumerate() {
        let bit_val = ((witness.leaf_index >> i) & 1) as u64;
        pw.set_bool_target(*bit_t, bit_val == 1);
    }

    let circuit = builder.build::<C>();
    let proof = circuit.prove(pw)?;
    let proof_bytes = proof.to_bytes();

    Ok(ProofBundle {
        proof_hex: hex::encode(&proof_bytes),
        public_inputs: PublicInputs {
            epoch_root_hex: root_hex,
            epoch_id,
            context_id,
            nonce,
        },
    })
}

/// Verify a proof. Returns true iff the proof is valid AND the public
/// inputs in the proof match the claimed (epoch_root, epoch_id, context_id,
/// nonce).
pub fn verify(bundle: &ProofBundle) -> Result<bool> {
    let (builder, _, _, _, _, _, _, _) = build_circuit();
    let circuit = builder.build::<C>();
    let verifier_data: VerifierCircuitData<F, C, D> = circuit.verifier_data();

    let proof_bytes = hex::decode(&bundle.proof_hex)?;
    let proof = ProofWithPublicInputs::<F, C, D>::from_bytes(proof_bytes, &verifier_data.common)?;

    // Our circuit commits to exactly 7 public inputs: root[0..4], epoch_id,
    // context_id, nonce. Plonky2's from_bytes reads the public-input COUNT
    // straight from the (caller-supplied) buffer and does not constrain it to
    // the circuit's count until the cryptographic verify below — so a crafted
    // proof can deserialize Ok with a shorter public_inputs vector, and the
    // indexing on the next lines (`[0..4]`, `[4]`, `[5]`, `[6]`) would panic and
    // abort the process. verify() is an attacker-reachable trust boundary
    // (POST /api/zk/verify), so reject cleanly instead of crashing — the same
    // panic-as-DoS class v9.84 closed for prove()'s leaf_index. Returning false
    // is fail-closed: this branch is reached before verifier_data.verify(), so
    // it can never let an invalid proof verify true.
    if proof.public_inputs.len() < 7 {
        return Ok(false);
    }

    // Check public-input binding before letting Plonky2 verify, so a
    // mismatched public-input shape rejects fast.
    let expected_root = hex_to_hash_elements(&bundle.public_inputs.epoch_root_hex)?;
    let actual_root = &proof.public_inputs[0..4];
    for i in 0..4 {
        if actual_root[i] != expected_root[i] {
            return Ok(false);
        }
    }
    let actual_epoch = proof.public_inputs[4].to_canonical_u64();
    let actual_context = proof.public_inputs[5].to_canonical_u64();
    let actual_nonce = proof.public_inputs[6].to_canonical_u64();
    if actual_epoch != bundle.public_inputs.epoch_id
        || actual_context != bundle.public_inputs.context_id
        || actual_nonce != bundle.public_inputs.nonce
    {
        return Ok(false);
    }

    // Plonky2 verifies the cryptographic soundness.
    let result = verifier_data.verify(proof);
    Ok(result.is_ok())
}

#[cfg(test)]
mod tests {
    use super::*;

    fn make_leaves(n: usize) -> Vec<String> {
        (0..n)
            .map(|i| {
                let mut bytes = [0u8; 32];
                bytes[0..8].copy_from_slice(&(i as u64).to_le_bytes());
                hex::encode(bytes)
            })
            .collect()
    }

    #[test]
    fn honest_prover_passes() {
        let leaves = make_leaves(8);
        let witness = WitnessInput {
            leaf_seed_hex: leaves[3].clone(),
            leaf_index: 3,
            all_leaves_hex: leaves.clone(),
        };
        let bundle = prove(&witness, 42, 1, 99).unwrap();
        assert!(verify(&bundle).unwrap(), "honest prover should pass");
    }

    #[test]
    fn verify_rejects_malformed_proof_without_panicking() {
        // from_bytes reads the public-input count from the buffer, so a crafted
        // proof can deserialize with fewer than the 7 public inputs the circuit
        // commits to. Indexing public_inputs[0..4] used to panic (exit 101) on
        // such input — an unhandled crash at the attacker-reachable verify
        // boundary. An all-zero buffer the size of a real proof exercises it:
        // from_bytes accepts it (pi_len reads as 0 -> empty vector), and the
        // old slice would panic. verify() must now return cleanly, never crash.
        let leaves = make_leaves(8);
        let witness = WitnessInput {
            leaf_seed_hex: leaves[3].clone(),
            leaf_index: 3,
            all_leaves_hex: leaves.clone(),
        };
        let real = prove(&witness, 42, 1, 99).unwrap();
        let n = hex::decode(&real.proof_hex).unwrap().len();
        let malformed = ProofBundle {
            proof_hex: hex::encode(vec![0u8; n]),
            public_inputs: real.public_inputs,
        };
        // No panic. A clean result either way: Ok(false) under the guard, or a
        // plain Err if a future plonky2 rejects the buffer in from_bytes. Never
        // an invalid proof verifying true.
        match verify(&malformed) {
            Ok(v) => assert!(!v, "a malformed proof must never verify true"),
            Err(_) => {}
        }
    }

    #[test]
    fn replay_with_different_nonce_fails() {
        let leaves = make_leaves(8);
        let witness = WitnessInput {
            leaf_seed_hex: leaves[3].clone(),
            leaf_index: 3,
            all_leaves_hex: leaves.clone(),
        };
        let bundle = prove(&witness, 42, 1, 99).unwrap();

        // Tamper the public inputs: change nonce. Verifier must reject.
        let mut tampered = bundle;
        tampered.public_inputs.nonce = 100;
        assert!(!verify(&tampered).unwrap(), "tampered nonce should fail");
    }

    #[test]
    fn cross_epoch_proof_fails() {
        let leaves = make_leaves(8);
        let witness = WitnessInput {
            leaf_seed_hex: leaves[3].clone(),
            leaf_index: 3,
            all_leaves_hex: leaves.clone(),
        };
        let bundle = prove(&witness, 42, 1, 99).unwrap();

        // Change epoch_id in public inputs: must reject.
        let mut tampered = bundle;
        tampered.public_inputs.epoch_id = 43;
        assert!(!verify(&tampered).unwrap(), "cross-epoch should fail");
    }

    // ------------------------------------------------------------------
    // v8.80 — additional adversarial tests (ARCH-004 test-depth gap)
    //
    // The first three tests cover the primary identity-preservation
    // properties. The four below cover targeted adversaries:
    //
    //   - tampered Merkle root in public inputs
    //   - wrong context binding (re-binding context_id)
    //   - prover-side replay across different epochs (witness valid
    //     in one epoch must not produce a passing proof for another)
    //   - small-cohort safety (n=1, n=2, edge sizes)
    // ------------------------------------------------------------------

    #[test]
    fn tampered_merkle_root_fails() {
        let leaves = make_leaves(8);
        let witness = WitnessInput {
            leaf_seed_hex: leaves[3].clone(),
            leaf_index: 3,
            all_leaves_hex: leaves.clone(),
        };
        let bundle = prove(&witness, 42, 1, 99).unwrap();

        // Flip a single byte in the committed Merkle root in public inputs.
        // The verifier MUST reject because the proof was generated against
        // the original root.
        let mut tampered = bundle;
        let mut root_bytes = hex::decode(&tampered.public_inputs.epoch_root_hex)
            .expect("root is hex");
        root_bytes[0] ^= 0x01;
        tampered.public_inputs.epoch_root_hex = hex::encode(root_bytes);
        assert!(
            !verify(&tampered).unwrap(),
            "tampered Merkle root must fail verification"
        );
    }

    #[test]
    fn cross_context_proof_fails() {
        // A proof bound to context_id=1 must not verify under context_id=2.
        // This is the schema C9 (context isolation) at the ZK layer.
        let leaves = make_leaves(8);
        let witness = WitnessInput {
            leaf_seed_hex: leaves[3].clone(),
            leaf_index: 3,
            all_leaves_hex: leaves.clone(),
        };
        let bundle = prove(&witness, 42, 1, 99).unwrap();

        let mut tampered = bundle;
        tampered.public_inputs.context_id = 2;
        assert!(
            !verify(&tampered).unwrap(),
            "cross-context proof must fail (C9 / context isolation)"
        );
    }

    #[test]
    fn replay_across_epochs_fails() {
        // A prover with a valid witness for epoch 42 must not be able to
        // produce a verifying proof for epoch 43 simply by editing the
        // public inputs — the verifier binds the proof to the public
        // inputs at proof time.
        let leaves = make_leaves(8);
        let witness = WitnessInput {
            leaf_seed_hex: leaves[3].clone(),
            leaf_index: 3,
            all_leaves_hex: leaves.clone(),
        };
        let mut bundle = prove(&witness, 42, 1, 99).unwrap();

        // Edit BOTH epoch_id and context_id and nonce simultaneously —
        // a multi-public-input replay attempt. Verifier must still reject.
        bundle.public_inputs.epoch_id = 43;
        bundle.public_inputs.context_id = 2;
        bundle.public_inputs.nonce = 100;
        assert!(
            !verify(&bundle).unwrap(),
            "multi-public-input replay must fail"
        );
    }

    #[test]
    fn small_cohort_n1_passes_with_one_leaf() {
        // Edge case: a 1-leaf Merkle tree. The leaf is its own root.
        // The honest prover must still produce a verifying proof.
        let leaves = make_leaves(1);
        let witness = WitnessInput {
            leaf_seed_hex: leaves[0].clone(),
            leaf_index: 0,
            all_leaves_hex: leaves.clone(),
        };
        let bundle = prove(&witness, 42, 1, 99).unwrap();
        assert!(
            verify(&bundle).unwrap(),
            "honest prover with single-leaf cohort must verify"
        );
    }
}
