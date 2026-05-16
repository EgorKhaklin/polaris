# proposals/M2-1-zk-snark-plonky2-merkle.md

**Risk class:** HIGH (cryptographic-correctness; new Rust toolchain dependency; verification-flow change for ZERO_KNOWLEDGE outcomes)
**Mission link:** v2 M2-1 (Substrate-D arc closure — the last ⬜)
**Status:** PROPOSED, awaiting VANTA ship approval
**Effort:** ~3 sessions (highest of any single ship; multi-language)
**Architect ID:** arch-2026-05-11-002 (continues from the readiness brief and the M2-1 exploration Sanctum)

---

## Scope — fixed by the exploration Sanctum

VANTA picked **C3 + A4 + B3** in the M2-1 exploration Sanctum
(`sanctum/2026-05-11-m2-1-snark-exploration.md`):

- **C3 — Transparent trusted-setup posture.** No ceremony, by construction.
- **A4 — Plonky2 SNARK family.** FRI-based, hash-only commitments,
  post-quantum-comfortable, Rust reference implementation.
- **B3 — Hybrid-Merkle circuit reusing R10-2 AnchorBatch infrastructure.**
  Issuer publishes a Merkle root over the active token set per epoch;
  SNARK proves "I hold a token committed in this Merkle root."

This proposal scopes the actual ship within this combination.

## Problem

PDF §9 closure for the Substrate-D arc requires a real
zero-knowledge proof in the verification path. Today,
`VerificationEvent.proof_commitment` is an opaque string-hash field
treated as audit metadata — the schema does not verify anything
cryptographic about it. The disclosure-consistency CHECK enforces
the *typing* invariant (`ZERO_KNOWLEDGE` → `token_id IS NULL`) but
not the *soundness* invariant ("the prover actually holds a valid
token").

A real ZK-SNARK would change the verification flow such that:

1. The prover (holder's device, conceptually) generates a proof from
   their token's witness against an issuer-published Merkle root.
2. The verifier (Polaris route) accepts the proof, the proof's
   binding fields (epoch, context), and verifies cryptographically
   that the prover possesses a witness for the committed Merkle root
   at that epoch, in that context.
3. SUCCESS outcomes on `ZERO_KNOWLEDGE` events are gated by this
   verification. Without a valid proof, the recorded outcome cannot
   be SUCCESS.

## What v1 ships

Honest scope:

### Schema layer (Polaris-side)

1. **`TokenStateEpoch` table** — per-epoch Merkle commitment over the
   set of (active, in-context) tokens at a snapshot in time. Append-
   only (7th audit-of-record instance). Fields:
   - `epoch_id SERIAL PK`
   - `merkle_root VARCHAR(128)` — SHA3-256 hex (B3 reuses R10-2's
     hash function for consistency; Plonky2 internally uses Poseidon
     but our schema-level commitment uses SHA3-256 as the operator-
     policy hash)
   - `valid_from TIMESTAMP`
   - `valid_until TIMESTAMP` — explicit expiry forces re-anchoring
   - `closed_at TIMESTAMP`, `closed_by_user_id` — admin-only closure
   - `committed_count INTEGER` — number of tokens in the commitment
2. **`TokenStateEpochLeaf` table** — per-token witness within an
   epoch. Each row is (epoch_id, token_id, leaf_hash, proof_path) —
   the holder's "witness" for proving membership. Append-only.
3. **`uc11_close_epoch` procedure** — admin-only, per-epoch-id
   advisory-lock (6th catalog entry), computes Merkle commitment over
   currently-valid tokens, inserts `TokenStateEpoch` row, fills
   `TokenStateEpochLeaf` per token. Hard cap: 10,000 leaves per
   epoch (mirrors `close_anchor_batch`).
4. **`uc11_record_zk_verification` procedure** — receives a
   verification request with proof bytes, calls the verifier helper
   (Python → Rust subprocess), records outcome.

### Crypto layer (Rust crate)

5. **`polaris_zk/` directory** (new) — a Rust workspace containing:
   - `polaris_zk/Cargo.toml` — Plonky2 dependency
   - `polaris_zk/src/circuit.rs` — the Merkle inclusion circuit
   - `polaris_zk/src/prover.rs` — `prove(witness, epoch_root) → proof_bytes`
   - `polaris_zk/src/verifier.rs` — `verify(proof_bytes, epoch_root, context_id) → bool`
   - `polaris_zk/src/main.rs` — CLI binary: `polaris-zk prove <witness>` / `polaris-zk verify <proof>`
   - The binary reads inputs as JSON on stdin, writes results as JSON on stdout. Subprocess interface, not bindings (to avoid linking Rust runtime into Python).

### Python integration (Polaris-side)

6. **`polaris_web/zk.py`** (new) — thin wrapper around the Rust
   binary:
   - `generate_proof(witness, epoch_root) -> bytes`
   - `verify_proof(proof_bytes, epoch_root, context_id) -> bool`
   - Both shell out to `polaris-zk` binary. Cached binary path via env
     var; falls back to `cargo run --release` for dev.
7. **`verifications_new` extension** — SUCCESS-on-ZK-event path calls
   `zk.verify_proof()` before INSERT. If verification fails, the
   route either records `outcome=UNAUTHORIZED` or rejects with a
   flash, mirroring the federation-check flow.

### Flask routes

8. **`POST /api/zk/epoch/close`** (admin) — wraps `uc11_close_epoch`.
9. **`GET /api/zk/epoch/<int:epoch_id>`** — returns the epoch row
   plus the count of committed tokens.
10. **`POST /api/zk/verify`** — endpoint that accepts a proof +
    epoch_id + context_id and returns `{verified: bool}`. Used by
    external verifiers (the prover holds the witness off-system).

### Tests

11. **`ZKSnarkTests` (Python, ≥18 tests)**:
    - Schema invariants (TokenStateEpoch append-only, leaf row
      uniqueness per (epoch, token))
    - Procedure semantics (close_epoch produces consistent root)
    - **Honest prover passes** (the witness for a committed token
      generates a proof that verifies)
    - **Malicious prover fails** (a prover without the witness
      cannot construct a verifying proof)
    - **Wrong-token prover fails** (a prover with witness for token
      A cannot produce a proof for token B's commitment)
    - **Replay attempt fails** (a proof from epoch N does not verify
      against epoch N+1's root)
    - **Epoch-boundary semantics** (proofs valid only while the
      epoch is current; post-valid_until proofs rejected)
    - **Witness-leak resistance** (verification accepts the proof
      without exposing the witness to the verifier)
    - **Per-epoch advisory-lock contract** (same-epoch parallel close
      attempts serialize)
12. **`ConcurrencyTests` +2**:
    - `test_uc11_close_epoch_same_epoch_serializes`
    - `test_uc11_close_epoch_cross_epoch_parallelizes`
13. **SQL self-tests section Q** (≥5 tests):
    - Seed produced 1 TokenStateEpoch row (the demo epoch)
    - TokenStateEpoch UPDATE rejected (append-only)
    - TokenStateEpochLeaf DELETE rejected
    - uc11_close_epoch rejects zero-valid-tokens
    - uc11_close_epoch rejects exceeding 10,000-leaf cap
14. **Rust unit tests** in `polaris_zk/tests/` — Plonky2 circuit
    soundness tests: malicious witness construction; cross-epoch
    binding; Merkle-path manipulation.

### Documentation

15. **`DEVNOTES/zk-snark.md`** (new) — canonical write-up: circuit
    design, Plonky2 choice, epoch semantics, witness construction,
    operator-side prover invocation, performance budget.
16. **`DEVNOTES/audit-of-record.md`** — extended to 7 instances.
17. **`DEVNOTES/concurrency.md`** — extended to 6 advisory-lock
    entries.
18. **`DEVNOTES/substrate.md`** + `polaris_sql/13_substrate.sql` —
    add `Plonky2 SNARK` + `Rust toolchain` rows. Substrate manifest
    grows from 25 to 27 rows.
19. **`docs/API.md`** — add the 3 new `/api/zk/*` routes.
20. **`docs/DATA-MODEL.md`** — `TokenStateEpoch` section.
21. **`MISSION.md` M2-1 ✅** + **ROADMAP R10-1 ✅** + **CHANGELOG v8.23 entry**.

## What v1 deliberately does NOT do

Honestly named:

1. **No production hardening.** The Rust binary is built in
   `release` mode but no formal verification of the circuit. Real
   production use requires independent cryptographic audit.
2. **No on-device prover.** The proof generation lives in the
   `polaris_zk` binary on the Polaris host. A real holder would
   prove on their own device with their own witness. v1 keeps the
   proving in-tree for testability; v2 would extract a holder-side
   prover.
3. **No witness encryption.** The `TokenStateEpochLeaf.proof_path`
   is stored in plaintext in v1, treated as audit metadata. A real
   deployment would encrypt witness rows under the holder's key.
   v1 is a reference impl; this trade-off is named.
4. **No real-time epoch refresh.** Epochs are closed manually via
   `POST /api/zk/epoch/close`. A production deployment would run an
   epoch closer on a scheduler. v1 leaves scheduling to the operator.
5. **The circuit only proves Merkle membership.** The validity
   predicates (active status, has-context-permission, not-revoked)
   are checked *outside* the SNARK at epoch-commitment time. This is
   the B3 contract — `uc11_close_epoch` filters tokens by validity
   before committing the Merkle root. The SNARK proves the prover
   knows a witness for *something the issuer committed* — and the
   issuer only commits valid tokens.

This is honest B3. Not B1 predicate-in-circuit. The validity
predicates live in SQL; the cryptographic binding lives in the
Plonky2 circuit. Each layer does the right thing.

## Why HIGH-risk

Beyond the obvious (new cryptographic primitive, new toolchain,
new schema) — three specific concerns:

1. **Soundness failure is silent.** A bug in the circuit that
   accepts invalid witnesses is undetectable from outside —
   verifications pass that shouldn't. R10-2 anchoring had public
   detection (verify endpoint catches root mismatch); Plonky2
   circuit bugs don't.
2. **Rust toolchain weight.** Largest substrate addition since
   v6 Redis. The Polaris launcher needs `cargo` available; CI
   needs Rust installed. Operational complexity grows.
3. **Library maturity.** Plonky2 is the youngest of the four SNARK
   families surveyed. Breaking changes possible. v1 pins a specific
   version; future upgrades require re-running the circuit
   correctness suite.

## Audit refinements (folded in below)

Following the audit-then-Sanctum pattern, eight refinements
specific to this ship (the prior pattern had ~6; the SNARK ship
needs more because the cryptographic surface is wider):

### R1. Honest-prover binding to specific (epoch, context, token)

The Plonky2 circuit must bind the proof to a specific
`(epoch_id, context_id, token_commitment)` triple. Without this
binding, a proof valid for `(epoch_N, BANKING, token_5)` could be
replayed as `(epoch_N, TRAVEL, token_5)`. The verifier must check
the proof's public inputs match the verification request.

**Implementation:** the circuit takes `(epoch_root, context_id,
nonce)` as public inputs and the witness as a private input. The
`verify` function checks the verifier-supplied public inputs match
the proof's commitment to them.

### R2. Replay resistance via nonce binding

Each verification request includes a fresh nonce. The nonce is
bound to the proof at generation time and re-supplied to the
verifier. A proof generated for nonce X cannot be replayed under
nonce Y.

**Implementation:** `nonce` is a public input of the circuit. The
prover includes it; the verifier checks the proof commits to the
nonce it expects. The `VerificationEvent.proof_commitment` field
stores `hash(nonce || epoch_id || context_id || proof_bytes)` for
audit-side replay detection.

### R3. Witness-leak resistance is the SNARK soundness property

By Plonky2's zero-knowledge property, the proof reveals nothing
about the witness beyond "the witness exists." This is the
cryptographic guarantee. Tests verify this empirically: prover
generates proof with witness W; verifier accepts proof without
seeing W; verifier cannot reconstruct W from proof bytes.

### R4. Epoch-boundary semantics named explicitly

Proofs are valid *only while the epoch's `valid_until` has not
passed*. The verifier checks `valid_until >= CURRENT_TIMESTAMP`
before accepting a proof. A proof generated yesterday under
yesterday's epoch is valid today only if today's `valid_until` has
not passed.

**Implementation:** verifier reads `TokenStateEpoch.valid_until`
and rejects proofs whose epoch is past-valid. The reason for
rejection is recorded with `outcome=EXPIRED` rather than
`UNAUTHORIZED` so the audit captures the difference.

### R5. Substrate manifest update + Rust toolchain

Two new rows in `DEVNOTES/substrate.md` + `13_substrate.sql`:
- `Plonky2 SNARK` (crypto layer; reference impl is `mir-protocol/plonky2`)
- `Rust toolchain` (runtime layer; required to build `polaris_zk`)

The `Rust toolchain` row's fail-mode is "operator cannot rebuild
binary; existing binary continues to verify." Replacement: pin to
a specific Plonky2 version + ship pre-built binary for common
platforms (macOS arm64, Linux x86_64).

### R6. Performance budget acknowledged

Per-verification cost (the hot path):
- Verifier: ~100 ms (Plonky2 verifier overhead on the Polaris host)
- Subprocess invocation: ~30 ms (process spawn + JSON pipe)
- Total: ~130 ms per ZK verification request

Per-epoch cost (cold path):
- Prover: depends on epoch size; ~1 s for 1K leaves on a desktop
- Merkle commitment: ~10 ms for 10K leaves (R10-2 reuse)

The Flask hot-path budget had been ~10 ms. ZK adds 13x. We accept
this for the v1 ship because the alternative (no ZK guarantee) is
worse. We name the regression explicitly. Future optimization:
proof caching by `(epoch_id, context_id, nonce)` triple, or
in-process Rust bindings via PyO3.

### R7. Operator-driven epoch closure (anti-auto-derivation)

Following the established Polaris pattern: epochs do NOT
auto-close. An operator (or a future scheduled job) calls
`uc11_close_epoch` explicitly. The schema records the epoch; the
operator decides when to close. Same posture as R10-2's
`committed_to_chain` and R11-3's federation attestation.

### R8. TokenStateEpoch is the 7th audit-of-record instance

Append-only via `enforce_epoch_immutability` trigger (mirrors
`enforce_attestation_immutability`). Once an epoch is closed, its
merkle_root cannot change — every proof issued against it depends
on its immutability. Bounded mutation: none (epochs are fully
append-only after closure; `valid_until` is set at closure and
cannot be moved).

### R9. Coexistence with R11-3 federation check

The verifications_new SUCCESS path now has TWO cryptographic
gatings, applied by disclosure level. They are *complementary*, not
redundant:

| Disclosure | token_id | Federation check (R11-3) | SNARK check (M2-1) |
|---|---|---|---|
| `ZERO_KNOWLEDGE` | NULL | N/A — no issuer to check | **runs** — proof gates SUCCESS |
| `SELECTIVE` | NOT NULL | **runs** — attestation gates SUCCESS | N/A — no proof submitted |
| `FULL` | NOT NULL | **runs** — attestation gates SUCCESS | N/A — no proof submitted |

This is the natural split: federation answers "do we trust who
issued this token?", SNARK answers "does the holder actually have
the token?". For ZK events the issuer-question is moot (no
disclosed token); for SELECTIVE/FULL the holder-question is moot
(holder is explicitly named). No verification flow runs both
checks for the same event; the disclosure level statically
determines which.

This is recorded so future maintainers know the two checks were
designed as complementary gates, not as competing alternatives.

## Audit checklist

| Check | Status |
|---|---|
| C9 advisory-lock named (per-epoch-id) | ✅ 6th catalog entry |
| "Schema records, agencies decide" framing | ✅ R7 |
| Append-only / audit-of-record applied | ✅ 7th instance |
| Anti-auto-derivation explicit (no auto-close) | ✅ R7 |
| Honest-prover binding (epoch + context + nonce) | ✅ R1 |
| Replay resistance (nonce binding) | ✅ R2 |
| Witness-leak resistance | ✅ R3 (SNARK soundness) |
| Epoch-boundary semantics explicit | ✅ R4 |
| Substrate manifest update planned | ✅ R5 (Plonky2 + Rust) |
| Performance budget acknowledged | ✅ R6 (~130 ms / verification) |
| Coexistence with R11-3 federation check | ✅ R9 |
| Library-maturity risk named | ✅ "What v1 deliberately does NOT do" |

## Phasing

This is a multi-session ship. Suggested phasing:

**Phase 1 (this Sanctum, target v8.23):**
- Schema additions (TokenStateEpoch + leaf)
- SQL procedures (uc11_close_epoch)
- Triggers (enforce_epoch_immutability)
- Rust crate scaffold (polaris_zk/) — circuit + prover + verifier + CLI
- Python wrapper (polaris_web/zk.py)
- Flask routes (3 endpoints)
- Tests (Python + Rust + SQL)
- Documentation
- M2-1 marked ✅

**Phase 2 (future, not in this Sanctum):**
- Holder-side prover extraction (witness stays on device)
- Witness-row encryption
- Scheduled epoch refresh
- Performance optimization (PyO3 bindings, proof caching)

Phase 1 alone is the largest single ship in Polaris history. Honestly
named.

## Blast radius

- Schema: +2 tables (`TokenStateEpoch`, `TokenStateEpochLeaf`), +1 partial unique index, +1 trigger
- Procedures: +1 (`uc11_close_epoch`); per-epoch-id advisory lock (6th catalog entry)
- New top-level directory: `polaris_zk/` (Rust workspace)
- Python: 1 new module (`zk.py`), `verifications_new` extension
- Flask: +3 routes
- Tests: +18 `ZKSnarkTests` + 2 concurrency + 5 SQL section Q + Rust unit tests
- DEVNOTES: 1 new (`zk-snark.md`), 3 extended (audit-of-record → 7; concurrency → 6; substrate → 27 rows)
- Counts: 20 → 22 tables; 11 → 12 procedures; 11 → 12 triggers; 6 → 7 audit-of-record instances; 5 → 6 advisory-lock entries

## Pre-Sanctum sanity checklist

| Check | Status |
|---|---|
| C9 advisory-lock named (per-epoch-id) | ✅ |
| Append-only / audit-of-record (7th instance) | ✅ |
| Anti-auto-derivation explicit | ✅ |
| Replay resistance designed in | ✅ |
| Witness-leak resistance is the SNARK property | ✅ |
| Performance budget named (~130 ms / verification) | ✅ |
| Library-maturity risk acknowledged | ✅ |
| Multi-session phasing named | ✅ |
| Documentation: DEVNOTES + 3 extended docs planned | ✅ |
| Substrate manifest growth named (+2 rows) | ✅ |

## Cross-references

- **Exploration Sanctum:** `sanctum/2026-05-11-m2-1-snark-exploration.md` (closed; VANTA picked C3+A4+B3)
- **MISSION:** M2-1 in the v2 done-list — last ⬜ in the Substrate-D arc
- **R10-2 reuse:** `polaris_sql/01_schema.sql` AnchorBatch table; `polaris_web/anchoring.py` Merkle helper. The B3 circuit reads commitments from `TokenStateEpoch`, which mirrors AnchorBatch's structure.
- **Substrate manifest:** `DEVNOTES/substrate.md` + `polaris_sql/13_substrate.sql` — to be extended with Plonky2 + Rust toolchain rows
- **Audit-of-record:** `DEVNOTES/audit-of-record.md` — to be extended to 7 instances
- **Concurrency catalog:** `DEVNOTES/concurrency.md` — to be extended to 6 advisory-lock entries
