// polaris_zk/src/main.rs — CLI binary for the Plonky2 SNARK prover/verifier.
//
// Subcommands (read JSON on stdin, write JSON on stdout):
//   compute-root        Compute the Poseidon Merkle root over a leaf set
//                       Input:  {"leaves_hex": [hex, hex, ...]}
//                       Output: {"epoch_root_hex": hex}
//   compute-leaves      Compute Merkle inclusion paths for each leaf
//                       Input:  {"leaves_hex": [...]}
//                       Output: {"leaves": [{"index": i, "leaf_hash": hex, "proof_path": [...]}, ...]}
//                                "epoch_root_hex": hex}
//   prove               Generate a SNARK proof for a leaf in a tree
//                       Input:  WitnessInput + {"epoch_id": u64, "context_id": u64, "nonce": u64}
//                       Output: ProofBundle
//   verify              Verify a SNARK proof bundle
//                       Input:  ProofBundle
//                       Output: {"verified": bool}
//
// Polaris's polaris_web/zk.py invokes this binary with subprocess.run() and
// JSON pipes. The binary stays small; all proof state lives in stdin/stdout.

use anyhow::{anyhow, Result};
use polaris_zk::{
    build_merkle_tree, compute_epoch_root, prove, verify, ProofBundle, WitnessInput, F, TREE_DEPTH,
};
use plonky2::field::types::PrimeField64;
use serde::{Deserialize, Serialize};
use std::io::{self, Read, Write};

#[derive(Deserialize)]
struct ComputeRootInput {
    leaves_hex: Vec<String>,
}

#[derive(Serialize)]
struct ComputeRootOutput {
    epoch_root_hex: String,
}

#[derive(Deserialize)]
struct ProveInput {
    leaf_seed_hex: String,
    leaf_index: usize,
    all_leaves_hex: Vec<String>,
    epoch_id: u64,
    context_id: u64,
    nonce: u64,
}

#[derive(Serialize)]
struct VerifyOutput {
    verified: bool,
}

#[derive(Deserialize)]
struct ComputeLeavesInput {
    leaves_hex: Vec<String>,
}

#[derive(Serialize)]
struct ComputeLeavesLeafEntry {
    index: usize,
    leaf_hash: String,
    proof_path: Vec<String>,
}

#[derive(Serialize)]
struct ComputeLeavesOutput {
    epoch_root_hex: String,
    leaves: Vec<ComputeLeavesLeafEntry>,
}

fn hash_to_hex(h: &plonky2::hash::hash_types::HashOut<F>) -> String {
    let mut bytes = [0u8; 32];
    for i in 0..4 {
        bytes[i * 8..(i + 1) * 8].copy_from_slice(&h.elements[i].to_canonical_u64().to_le_bytes());
    }
    hex::encode(bytes)
}

fn cmd_compute_root(input: &str) -> Result<String> {
    let parsed: ComputeRootInput = serde_json::from_str(input)?;
    let root = compute_epoch_root(&parsed.leaves_hex)?;
    Ok(serde_json::to_string(&ComputeRootOutput {
        epoch_root_hex: root,
    })?)
}

fn cmd_compute_leaves(input: &str) -> Result<String> {
    let parsed: ComputeLeavesInput = serde_json::from_str(input)?;
    if parsed.leaves_hex.is_empty() {
        return Err(anyhow!("empty leaf set"));
    }
    if parsed.leaves_hex.len() > (1 << TREE_DEPTH) {
        return Err(anyhow!(
            "too many leaves ({}); circuit cap at 2^{} = {}",
            parsed.leaves_hex.len(),
            TREE_DEPTH,
            1 << TREE_DEPTH
        ));
    }
    // build_merkle_tree from the library handles the padding to 2^TREE_DEPTH.
    let tree = build_merkle_tree(&parsed.leaves_hex)?;
    let root_hex = hash_to_hex(&tree.cap.0[0]);

    // Generate one proof_path per *real* leaf (not the padded ones).
    let mut entries = Vec::with_capacity(parsed.leaves_hex.len());
    for (i, leaf_hash) in parsed.leaves_hex.iter().enumerate() {
        let proof = tree.prove(i);
        let proof_path: Vec<String> = proof.siblings.iter().map(hash_to_hex).collect();
        entries.push(ComputeLeavesLeafEntry {
            index: i,
            leaf_hash: leaf_hash.clone(),
            proof_path,
        });
    }

    Ok(serde_json::to_string(&ComputeLeavesOutput {
        epoch_root_hex: root_hex,
        leaves: entries,
    })?)
}

fn cmd_prove(input: &str) -> Result<String> {
    let parsed: ProveInput = serde_json::from_str(input)?;
    let witness = WitnessInput {
        leaf_seed_hex: parsed.leaf_seed_hex,
        leaf_index: parsed.leaf_index,
        all_leaves_hex: parsed.all_leaves_hex,
    };
    let bundle = prove(&witness, parsed.epoch_id, parsed.context_id, parsed.nonce)?;
    Ok(serde_json::to_string(&bundle)?)
}

fn cmd_verify(input: &str) -> Result<String> {
    let bundle: ProofBundle = serde_json::from_str(input)?;
    let ok = verify(&bundle)?;
    Ok(serde_json::to_string(&VerifyOutput { verified: ok })?)
}

fn main() -> Result<()> {
    let args: Vec<String> = std::env::args().collect();
    let subcommand = args.get(1).cloned().unwrap_or_else(|| {
        eprintln!("usage: polaris-zk <compute-root|compute-leaves|prove|verify>");
        std::process::exit(2);
    });

    let mut input = String::new();
    io::stdin().read_to_string(&mut input)?;

    let output = match subcommand.as_str() {
        "compute-root" => cmd_compute_root(&input)?,
        "compute-leaves" => cmd_compute_leaves(&input)?,
        "prove" => cmd_prove(&input)?,
        "verify" => cmd_verify(&input)?,
        other => {
            eprintln!("unknown subcommand: {}", other);
            std::process::exit(2);
        }
    };

    io::stdout().write_all(output.as_bytes())?;
    io::stdout().write_all(b"\n")?;
    Ok(())
}
