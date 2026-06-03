# ZK soundness ledger — what Polaris's Merkle-inclusion proof actually guarantees

Polaris's `polaris_zk` crate uses the words *proof*, *zero-knowledge*, and
*post-quantum*. This is the honest ledger: which of those claims are rigorous,
which are demo-scale, and exactly where the edges are. It is modeled on Glass's
`docs/soundness.md` and was added in v9.44 as the documentation half of the
Glass bounded-integration decision
(`sanctum/2026-06-03-glass-bounded-integration.md`).

The short version, up front:

> **The ZK layer is an educational, demo-scale Merkle-inclusion SNARK built on the
> audited `plonky2` 0.2 crate. The membership statement and its verdict are now
> two-witnessed by an independent implementation. The circuit parameters
> (`TREE_DEPTH = 4`, single root) are demo-scale, the token-signing PQC path is a
> deterministic placeholder by default, and none of this has had an external
> cryptographic audit. Do not protect real identities with it as shipped.**

There are two different kinds of guarantee here. Conflating them is the main way
to be misled. Keep them separate.

---

## 1. The differential / consistency guarantee — strong and real

This is the guarantee Polaris now delivers rigorously, and it is not itself a
cryptographic claim. It is a correctness claim about the implementation.

The verdict of the Rust verifier (`polaris_zk::verify`) is **two-witnessed**: an
independent, from-scratch re-implementation of the same field, hash, and Merkle
semantics (`polaris_zk/witness2/`, pure Python, plain `int mod p` rather than the
Rust crate's limbs, sharing no code with the crate or with Glass) re-derives the
membership fact and the public-input binding and must agree ACCEPT / REJECT on
every honest and adversarial case.

What is checked, and how hard you can lean on it:

- **Root computation** is bit-for-bit identical between the Rust crate
  (`compute-root`) and the Python witness across every cohort size 1..16
  (`test_root_agreement_bit_identical`). A wrong Poseidon, MDS, encoding, or tree
  ordering could not survive this.
- **The Python Poseidon is anchored independently** of Polaris: it reproduces
  Plonky2's own published permutation test vectors (all-zeros, `0..11`, all `-1`)
  in `poseidon_constants.py::POSEIDON_TEST_VECTORS`, so the second witness has its
  own ground truth, not just "agrees with the Rust binary."
- **The verdict differential** (`polaris_web/test_zk_second_witness.py`) runs
  honest proofs and every public-input tamper (nonce, epoch, context, root, and a
  multi-field replay) through both verifiers; both ACCEPT the honest case and both
  REJECT every tamper.

This is the part you can lean on hardest. It says: the membership statement
Polaris's verifier accepts is the statement an independent implementation also
accepts, and the bindings it rejects are the bindings an independent
implementation also rejects.

---

## 2. The cryptographic guarantee — demo-scale, with specific caveats

The soundness of the *proof object itself* (the FRI / Plonky2 proof, that a
cheating prover cannot forge membership) rests entirely on the upstream
`plonky2` 0.2 crate. Polaris does not re-implement or audit that; it depends on
it. The honest caveats:

| Component | What is real | The honest caveat |
|---|---|---|
| **Proof system** | The audited, widely-used `plonky2` 0.2 crate (transparent setup, FRI-based, no trusted ceremony, no elliptic-curve assumption). | Polaris ships a thin circuit over it. The *crate* is mature; *Polaris's use of it* has had no external review. |
| **Statement** | "I know a leaf `L` and a path `P` such that `L` hashes up to the public root `R`, bound to `(epoch_id, context_id, nonce)`." Correct and now two-witnessed. | The binding fields are registered as public inputs but not otherwise constrained (see `lib.rs:231-238`); they defeat replay by commitment, not by an in-circuit predicate. |
| **Tree size** | `TREE_DEPTH = 4`, up to 16 leaves per epoch, padded with a zero-leaf. | **Demo-scale.** The schema cap is 10,000 leaves; production would need `TREE_DEPTH = 14` and a fresh setup. Until then the anonymity set is at most 16. |
| **Hash** | Poseidon over Goldilocks, Plonky2-native, vector-matched. | Standard primitive, but the in-circuit security margin is Plonky2's default config, not a parameter set audited for this deployment. |
| **FRI parameters** | `CircuitConfig::standard_recursion_config()` defaults. | The concrete bit-security of the shipped config is **not independently verified here**; treat any specific number (including the crate README's "256-bit") as aspirational until measured. |
| **Token-signing PQC** | Integration scaffold for real ML-DSA via liboqs (`pqc_signing.py`, `POLARIS_USE_REAL_PQC`). | **Off by default**: `token_value` is a deterministic placeholder so property tests stay reproducible. Activation is operator-side. This is a separate primitive from the Merkle SNARK above; do not conflate them. |

---

## What the second witness covers, and what it does not

The second witness is a **statement-level** check, by design. It re-establishes:

- **membership** — the leaf really hashes up its path to the committed root, and
- **binding** — the bundle's public inputs equal the ones the proof committed to.

It deliberately **ABSTAINS** on one axis: the integrity of the Plonky2 proof
*bytes*. It does not parse or re-run the FRI object, so it cannot detect a
corrupted proof blob; that axis is witnessed by the Rust decoder alone. The
differential records this explicitly
(`test_proof_byte_tamper_rust_rejects_witness_abstains`): on proof-byte
corruption the Rust side rejects and the witness, seeing an intact statement,
abstains rather than bluffs.

This is the same honest boundary Glass's Pentecost verifier names for itself: a
second witness catches implementation divergence on the statement, not a shared
misreading of the spec, and never substitutes for an external audit.

---

## Bottom line for an operator

- The **engine** invariants (C1-C10) are real and enforced in Postgres. This
  ledger is **only** about the optional ZK layer.
- The ZK layer is good **tooling and teaching**: a transparent-setup,
  post-quantum-comfortable membership proof whose verdict is now independently
  two-witnessed.
- It is **not** audited cryptography and is **demo-scale** (≤16-leaf anonymity
  set, placeholder PQC signing by default). The README's framing as a real
  identity system is, correctly, labeled notional.

| Question | Read |
|---|---|
| The independent witness | `polaris_zk/witness2/` (+ `test_witness2.py`) |
| The verdict differential | `polaris_web/test_zk_second_witness.py` |
| The two-witness principle | [`DEVNOTES/two-witness-principle.md`](two-witness-principle.md) |
| Why Plonky2 + FRI | `sanctum/2026-05-11-m2-1-snark-exploration.md` |
| The Glass bounded-integration decision | `sanctum/2026-06-03-glass-bounded-integration.md` |
| Per-ship ZK reference | [`DEVNOTES/ships/zk-snark.md`](ships/zk-snark.md) |
