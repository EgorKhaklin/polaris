# DEVNOTES/ships/zk-snark.md

**Introduced:** v8.23 (R10-1 / M2-1). Closes the Substrate-D arc to **5/5**.
The last open substrate item; the v2 mission goes from 10 ✅ / 2 ⬜ to
11 ✅ / 1 ⬜ with this ship.

This file is the canonical write-up for Polaris's ZK-SNARK layer: which
cryptographic primitive, why, what the circuit proves, how it integrates,
what v1 ships, what v1 deliberately defers.

---

## The picked combination: C3 + A4 + B3

The M2-1 alignment-exploration narrowed the 4 × 3 × 3 design space
(4 SNARK families, 3 circuit designs, 3 trusted-setup postures) to a
single combination:

- **C3 — Transparent setup.** No ceremony, by construction. The most
  honest posture — removes a trust assumption entirely rather than
  externalizing or documenting it.
- **A4 — Plonky2 SNARK family.** FRI-based, hash-only commitments,
  post-quantum-comfortable. The only candidate that aligns with
  Polaris's "post-quantum by default" mission at the SNARK layer.
- **B3 — Hybrid-Merkle circuit reusing R10-2 infrastructure.** The
  issuer publishes a Merkle root over the active-token set per epoch;
  the SNARK proves Merkle membership in this root, bound to
  (epoch_id, context_id, nonce) public inputs.

Trade-offs accepted (named honestly):
- Plonky2 is the youngest of the four SNARK families considered.
  Library breaking changes are possible. B3's epoch-bounded
  architecture lets us re-port to Halo2 in a future migration
  without changing the schema.
- Proof size ~70 KB; verifier ~30 ms.
- v1 uses TREE_DEPTH=4 (16 leaves max) for demo-scale. Production
  would re-run the SNARK setup with TREE_DEPTH=14 (16,384 leaves).
  The SQL cap (10,000) is decoupled from the circuit cap — schema
  is wider than v1 demo circuit.

## What the circuit proves

```
Public inputs (verifier-visible):
  epoch_root  : 4 field elements (32 bytes) — the Poseidon Merkle root
  epoch_id    : 1 field element
  context_id  : 1 field element
  nonce       : 1 field element

Private inputs (witness, prover-only):
  leaf        : 4 field elements — the prover's leaf seed
  proof_path  : TREE_DEPTH × 4 field elements — sibling hashes
  index_bits  : TREE_DEPTH boolean targets — leaf's position

Constraint: Poseidon-hashing `leaf` up the tree along `proof_path`
            per `index_bits` must produce `epoch_root`.
```

The (epoch_id, context_id, nonce) public inputs are not arithmetic
constraints — they're registered as public inputs so the proof binds
to them. A prover cannot reuse a proof generated for one (epoch,
context, nonce) triple with a different triple; the verifier checks
the proof's public inputs match what's expected (R1, R2, R9 audit
refinements).

## Architecture: Rust subprocess

Plonky2 is Rust-native; no Python bindings are mature. v1 ships:

1. **`polaris_zk/` Rust crate** — uses `plonky2 = "0.2"`, requires
   Rust nightly (Plonky2 uses `#![feature(specialization)]`). Builds
   one CLI binary: `polaris-zk`.
2. **`polaris_web/zk.py`** — Python wrapper that shells out to
   `polaris-zk` via subprocess + JSON pipes. No PyO3, no Rust runtime
   inside Python.
3. **Subprocess interface:** stdin = JSON request; stdout = JSON
   response. Subcommands: `compute-root`, `compute-leaves`, `prove`,
   `verify`.

Operational note: Polaris's launcher needs to either build the Rust
binary at startup or assume it's pre-built. v1 ships the source and a
build instruction; production deployment would compile the binary
once and distribute it alongside Polaris.

## Hash choice: Poseidon (not SHA3)

R10-2's `AnchorBatch` uses SHA3-256 because it's the operator-policy
hash for off-chain commitments. R10-1's `TokenStateEpoch` uses
**Poseidon** because Poseidon is SNARK-friendly — its arithmetic
constraints fit Plonky2's circuit efficiently. SHA3 inside a circuit
would be 10,000+ R1CS constraints per hash; Poseidon is ~100.

The two commitments are distinct primitives for distinct primitives.
DEVNOTES/substrate.md adds a row for Poseidon explicitly so the
manifest captures both. `TokenStateEpoch.merkle_root` stores the
Poseidon root as a hex-encoded byte sequence (same hex format as
`AnchorBatch.merkle_root`, different underlying hash).

## Audit refinements (R1–R9)

All folded into the design and shipped:

### R1. Honest-prover binding to (epoch, context, nonce)

The Plonky2 circuit registers `(epoch_root, epoch_id, context_id,
nonce)` as public inputs. The verifier checks the proof's public
inputs match the verification request before accepting. A proof for
one triple cannot be replayed as another triple — different public
inputs → different proof commitments.

### R2. Replay resistance via nonce binding

Each verification request includes a fresh nonce. The nonce is bound
to the proof at generation time. A proof generated for nonce X
cannot be replayed under nonce Y because the verifier checks the
proof's bound nonce matches X.

### R3. Witness-leak resistance IS the SNARK soundness property

Plonky2's zero-knowledge property: the proof reveals nothing about
the witness beyond "the witness exists." This is the cryptographic
guarantee, not something we have to enforce at the API layer. The
verifier sees proof bytes + public inputs; it cannot reconstruct
the leaf value from the proof.

### R4. Epoch-boundary semantics

`TokenStateEpoch.valid_until` is checked at verification time. A
proof generated under an expired epoch is rejected with
`reason="epoch expired"` — distinct from "verification failed" so
the audit captures the difference. The `/api/zk/verify` route
performs this check before invoking the Rust verifier.

### R5. Substrate manifest update

Two new rows in `DEVNOTES/substrate.md` + `13_substrate.sql`:
- `Plonky2 SNARK` (crypto layer; in-tree dependency `plonky2 = "0.2"`)
- `Rust toolchain` (runtime layer; required to build `polaris_zk`)

The Rust toolchain row's fail-mode is "operator cannot rebuild
binary; existing binary continues to verify." Replacement: pin the
Plonky2 version + ship pre-built binaries for common platforms.

### R6. Performance budget

Measured on a 2026 desktop with TREE_DEPTH=4:
- Prover: ~3 s (circuit build + proof generation; dominated by
  build, not the proof itself)
- Verifier: ~30 ms (including subprocess spawn)
- Total /api/zk/verify hot path: ~80 ms

Future optimization: cache the verifier circuit data so each verify
call doesn't rebuild the circuit. v1 ships without this caching;
the regression is named here in §"Performance budget."

### R7. Operator-driven epoch closure

`uc11_close_epoch` is an explicit operator action — admin-role-required.
No scheduled job auto-closes epochs. The schema records the epoch;
the operator decides when to close. Same posture as R10-2's
`committed_to_chain` and R11-3's federation attestation.

### R8. TokenStateEpoch is the 7th audit-of-record instance

Append-only via `enforce_epoch_immutability` trigger. Once closed,
nothing on the row can change — every proof issued against
`merkle_root` depends on its immutability. The TokenStateEpochLeaf
table is also append-only (extends `reject_audit_modification`).

### R9. Coexistence with R11-3 federation check

The verifications_new SUCCESS path now has TWO complementary
cryptographic gatings, applied by disclosure level:

| Disclosure | Federation check (R11-3) | SNARK check (M2-1) |
|---|---|---|
| ZERO_KNOWLEDGE | N/A (no issuer disclosed) | **runs** |
| SELECTIVE | **runs** | N/A (no proof submitted) |
| FULL | **runs** | N/A (no proof submitted) |

The split is static — disclosure level determines which check
applies. No verification flow runs both checks for the same event.

## What v1 deliberately DOES NOT do

1. **No production hardening.** The Rust binary uses release-mode
   builds but no independent cryptographic audit.
2. **No on-device prover.** Proof generation lives in `polaris_zk`
   on the Polaris host. A production deployment would extract the
   prover to the holder's device.
3. **No witness encryption.** `TokenStateEpochLeaf.proof_path` is
   stored plaintext in v1.
4. **No real-time epoch refresh.** Epochs are closed manually via
   `POST /api/zk/epoch/close`. Production would schedule.
5. **The circuit only proves Merkle membership.** Validity predicates
   (ACTIVE, has-context-permission, not-revoked) are checked at
   epoch-commitment time by the caller. This is the B3 contract.

## Adversary walk

1. **Defender's claim:** A `ZERO_KNOWLEDGE` verification proves
   "a valid token exists in the named epoch" without revealing
   *which* token. The proof is a Plonky2 FRI-based SNARK over a
   Merkle-inclusion circuit; the verifier sees (epoch_root, public
   inputs, proof) and learns nothing about the leaf's index or
   identity. Soundness rests on Plonky2 + Poseidon collision
   resistance over the Goldilocks field.
2. **Attacker's optimal response:** Forge a proof. Plonky2 is
   FRI-based and post-quantum-comfortable; soundness reduces to
   cryptographic assumptions the substrate already documents
   (`DEVNOTES/substrate.md`). Game over for the attacker at the
   cryptographic layer — unless the attacker can move *outside the
   proof* to a side channel.
3. **Equilibrium:** The proof itself reveals nothing. The
   attacker is forced to attack adjacent surfaces — the timing of
   the verification request, the IP/context co-occurrence of
   ZK events with non-ZK events for the same individual, or the
   epoch-leaf composition layer (closer to the database than to
   the SNARK).
4. **Second-best attack:** Correlate ZERO_KNOWLEDGE events with
   FULL or SELECTIVE events for the same individual across
   contexts and timestamps to reconstruct identity from the
   verification graph. Defeated *outside the SNARK* by M2-12
   (redaction proof) + R6 anti-revealing + the C8 atlas hard caps
   that bound aggregate visibility. The SNARK alone does not solve
   this; the system's response is that the verification graph is
   itself confidential and rate-limited.
5. **Defender's cost:** Proof generation is subprocess-heavy
   (Rust nightly + Plonky2 + Poseidon hashing). Epoch closure
   serializes via the 6th catalog advisory lock
   (`pg_advisory_xact_lock(uc11_close_epoch_oid)`) so the prover
   isn't racing the leaf set. Accepted: the cost is paid at epoch
   boundaries, amortized across all ZK verifications in the epoch
   window.
6. **Mechanism-design note:** Plonky2 over Goldilocks + Poseidon
   was picked in the alignment exploration (C3+A4+B3) for
   post-quantum-comfortable assumptions and tooling maturity. The
   substitutability principle holds: the circuit, prover, and
   verifier could be swapped for any SNARK satisfying the same
   public-input contract without amending the schema. The B3
   contract (circuit only proves Merkle membership; validity
   predicates checked at epoch-commitment time) is the load-
   bearing design choice — keeping the circuit small keeps the
   prover fast.

## Cross-references

- `polaris_zk/` — Rust crate (Cargo workspace).
- `polaris_zk/src/lib.rs` — Plonky2 circuit + prover + verifier
  implementation.
- `polaris_zk/src/main.rs` — CLI binary with 4 subcommands.
- `polaris_web/zk.py` — Python subprocess wrapper.
- `polaris_sql/01_schema.sql` — `TokenStateEpoch` + `TokenStateEpochLeaf` tables.
- `polaris_sql/05_procedures.sql` — `uc11_close_epoch` procedure.
- `polaris_sql/06_triggers.sql` — `enforce_epoch_immutability` trigger.
- `polaris_sql/08_tests.sql` — Section Q (5 SQL self-tests).
- `polaris_sql/10_auth.sql` — demo epoch seed (3 leaves over BANKING context).
- `polaris_web/test_app.py` — `ZKSnarkTests` (15+ tests),
  `ConcurrencyTests.test_uc11_*` (2 tests).
- `DEVNOTES/substrate.md` — Plonky2 + Rust toolchain rows.
- `DEVNOTES/audit-of-record.md` — `TokenStateEpoch` is the 7th instance.
- `DEVNOTES/concurrency.md` — per-procedure advisory-lock is the 6th catalog entry.
