# polaris_zk/ — R10-1 / M2-1 · Plonky2 ZK-SNARK prover

This Rust crate is the post-quantum-comfortable ZK-SNARK
implementation for Polaris's `ZERO_KNOWLEDGE` verification
disclosure level. Built v8.23 (2026-05-11): Plonky2, chosen for
post-quantum sovereignty + FRI-based proof system + no trusted
setup.

It is the **5th and final** primitive in the Substrate-D arc
(M2-1; the other four are M2-2 anchoring, M2-3 substrate catalog,
M2-8 federation, M2-12 redaction proof). Closes the v2 substrate
arc 5/5.

---

## What it does

Given a Merkle tree of token state-epoch leaves, the prover
generates a SNARK proving "leaf X is in tree T at root R" without
revealing X. The verifier checks the proof against R alone.

This is what makes Polaris's `ZERO_KNOWLEDGE` disclosure level
real: the verifier learns "a valid token exists in this epoch"
without learning *which* token. C2 (`token_id IS NULL` on ZK
events) is structurally enforced; this crate provides the
cryptographic backing.

---

## Directory layout

```
polaris_zk/
├── Cargo.toml              # plonky2 = "0.2", serde, hex, anyhow
├── rust-toolchain.toml     # pins nightly (Plonky2 uses feature(specialization))
└── src/
    ├── lib.rs              # Merkle-inclusion circuit + prover + verifier
    └── main.rs             # CLI binary `polaris-zk` with subcommands
```

CLI subcommands (`polaris-zk`):
- `compute-root --leaves <file>` — Merkle root over leaves
- `compute-leaves --epoch <id>` — extract canonical leaves for an epoch
- `prove --leaves <file> --leaf-idx <n>` — generate SNARK
- `verify --proof <file> --root <hex>` — verify SNARK against root

The Flask app calls this binary as a subprocess via
`polaris_web/zk.py` (avoids embedding Rust into the Python web
process; preserves the 5+ year old web-app's stable surface).

---

## Building

The build is **optional** (Polaris core works without ZK proofs;
only the `ZERO_KNOWLEDGE` disclosure path needs the binary). To
build:

```bash
# 1. Install rustup (one-time)
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh

# 2. Build the crate
cd polaris_zk
cargo +nightly build --release

# 3. Point the Flask app at the binary (optional; defaults to
#    polaris_zk/target/release/polaris-zk)
export POLARIS_ZK_BINARY=/path/to/polaris-zk
```

If the binary is missing at runtime, the Flask app raises a
clear error on `/api/zk/*` routes naming this README and the
build steps above. Other disclosure levels (`SELECTIVE`, `FULL`)
work without it.

---

## Schema integration

Polaris's `TokenStateEpoch` table (the **7th audit-of-record
instance**) holds epoch metadata; `TokenStateEpochLeaf` holds the
leaves. The `uc11_close_epoch` procedure (the **6th catalog entry**
in the per-procedure advisory-lock catalog; first non-per-entity
one) atomically closes an epoch and computes its Merkle root.

Three `/api/zk/*` routes:
- `POST /api/zk/epoch/<id>/close` — close current epoch (admin-only)
- `GET /api/zk/epoch/<id>/proof?leaf=<n>` — generate ZK proof for a leaf
- `POST /api/zk/verify` — verify a proof against an epoch root

---

## G-guards / constitutional discipline

This crate is on the cryptographic substrate side; the relevant
constraints:

- **C2** — `ZERO_KNOWLEDGE` events have `token_id IS NULL`
  (CHECK constraint + form-layer coercion). The ZK proof is
  what makes this honest: the verifier can confirm validity
  without ever seeing `token_id`.
- **C7** — Cryptographic algorithm metadata flows through
  `CryptographicAlgorithm` table. Plonky2 + Poseidon hash
  registered there; never hardcoded in app code.
- **PQ-comfortable** — Plonky2 is FRI-based (hash-function
  security only); no elliptic-curve assumption. Survives
  Shor's algorithm if Poseidon survives Grover (which it does
  with the 256-bit security level used here).

Any monitoring of ZK proof generation latency should subprocess
this binary and time it; never embed prover state into Python
(would break the substrate-isolation discipline).

---

## Where to learn more

| Question | Read |
|---|---|
| Why Plonky2 + FRI vs Groth16 + ECDSA? | `DEVNOTES/threat-model.md` (PQ section) |
| Ship CHANGELOG entry | search `CHANGELOG.md` for `v8.23` |
| Per-ship reference doc | `DEVNOTES/ships/zk-snark.md` |
| Adversary walk + threat model | `DEVNOTES/threat-model.md` (PQ section) |
| Schema integration | `polaris_sql/01_schema.sql` (search `TokenStateEpoch`) |
| Flask wrapper | `polaris_web/zk.py` |
| v2 mission link | M2-1 (Substrate-D arc; 5/5 closed) |
