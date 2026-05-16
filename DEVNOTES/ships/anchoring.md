# DEVNOTES/ships/anchoring.md

**Introduced:** v8.21 (R10-2 / M2-2). Closes the Substrate-D arc to
4/5 done (M2-1 ZK-SNARK remains).

This file is the canonical write-up for Polaris's DID anchoring layer:
how Merkle batches are computed, where the substrate enforcement lives,
and what the schema does versus what the operator decides.

---

## What R10-2 implements

PDF §9 "Centralized trust assumption" names DID anchoring as the
substrate alternative to the relational schema as a sole trust root.
Polaris's posture: the schema remains the *primary* audit-of-record,
and the anchoring layer is a periodic, signed off-chain commitment
that lets external verifiers reconstruct the same audit without
trusting the Polaris operator.

Concretely:

1. Each `BlockchainAnchor` row carries a per-token DID + commitment
   hash (added in v1).
2. A `close_anchor_batch(algorithm_id, root, proofs)` procedure groups
   pending `BlockchainAnchor` rows by signature algorithm, computes a
   Merkle root over them, and records a new `AnchorBatch` row.
3. The Merkle root + per-leaf inclusion proof is what gets committed
   to an external PQ-capable ledger (operator-discretion when, and
   which ledger).

The Polaris schema is the audit-of-record. The external ledger is the
trust-anchor — every batch the operator pushes there is a public
commitment that the schema's history at that point cannot be
silently revised.

## Architecture choice: Python helper, not plpython3u

The Merkle math runs in Python (`polaris_web/anchoring.py`). The SQL
procedure consumes pre-computed root + proofs as parameters. This
keeps the substrate portable — no `plpython3u` dependency, which would
otherwise lock Polaris to a Postgres build with the trusted-language
extension installed.

The cost: a determined attacker who controls the Python helper could
hand the procedure inconsistent (root, proofs) data. Defense: every
*verifier* (the Flask route, external auditor scripts) recomputes the
Merkle root from `BlockchainAnchor.commitment_hash` and compares. If
the helper lied to the procedure at batch-close, the lie is
detectable on the very next verification call.

## Leaf ordering: sort by anchor_id ascending

The Python helper sorts `(anchor_id, commitment_hash)` tuples by
`anchor_id` ascending before computing leaves. This defeats the
"publish-then-fork" attack:

> If an attacker can re-order leaves arbitrarily, they can produce
> two different Merkle roots from the same leaf set — one to show
> auditor A, one to show auditor B — and claim each is the canonical
> batch.

Deterministic ordering forces a single root per leaf set. The same
ordering is implicit in the SQL procedure (the `ORDER BY a.anchor_id`
on the SELECT inside `close_anchor_batch` is the schema-side mirror).

## Hash algorithm: SHA3-256 default, operator-policy

`SUPPORTED_HASHES` in `anchoring.py`:

- `SHA3-256` — default, FIPS 202, post-quantum-comfortable
- `SHA3-512` — for batches with higher security-level targets
- `BLAKE3-256` — falls back to SHA3-256 if blake3 not installed

The algorithm choice is operator policy. The `CryptographicAlgorithm`
table records *signature* algorithms (ML-DSA, SLH-DSA, etc.), not
hash functions; the hash function is implicit in the helper at batch
time and recorded only in this file. If the hash needs to change in
the future, that's a new entry in `SUPPORTED_HASHES` plus an
operator-policy update — not a schema migration.

## Per-algorithm advisory-lock (C9)

`close_anchor_batch` holds `pg_advisory_xact_lock(hashtext(
'polaris.anchor.close-batch.' || algorithm_id::TEXT))`. Two parallel
calls for the same algorithm serialize; two parallel calls for
different algorithms run in parallel. This is the same shape as the
per-agency lock (UC-8), per-individual lock (UC-9), and per-token
lock (UC-6) — the fourth entry in Polaris's per-entity advisory-lock
catalog. See `DEVNOTES/concurrency.md`.

The lock protects against the phantom-batch race: without it, two
threads could each see the same pending leaf set, both INSERT an
`AnchorBatch` row, and split or duplicate the leaves between the two
batches — either way breaking the audit-of-record's
"one-batch-per-leaf" property.

## Schema decisions and what they're NOT

Three deliberate non-choices, each named here to keep the operator
discretion visible:

1. **`committed_to_chain` is not auto-derived.** The column exists,
   but no trigger flips it to TRUE just because an `AnchorBatch` row
   was created. Pushing the batch to an external ledger is an
   operator action; the schema records the fact of the push but does
   not perform the push.

2. **No `close_anchor_batch_chain` procedure.** A future tooling
   layer might add a procedure that takes (batch_id, external_chain,
   external_chain_tx) and flips `committed_to_chain = TRUE`. R10-2
   deliberately ships without it — see the v8.21 Sanctum decision
   §VI.

3. **Hash algorithm is not in the schema.** As above, it's an
   operator-policy choice recorded in this DEVNOTES file. If you want
   to query "which hash function was used for batch N", you read the
   relevant Sanctum / journal entry or this file. The Merkle proof
   format itself encodes the hash function implicitly via the proof
   geometry.

## 10,000 leaf hard cap

`close_anchor_batch` rejects batches larger than 10,000 leaves with a
clear message. Rationale:

- A SHA3-256 Merkle tree of 10k leaves is ~14 levels deep; proofs are
  14 sibling-hashes (~448 bytes). Acceptable inclusion-proof size.
- 10k anchors per batch at one batch/hour is 240k anchors/day —
  enough for a population-scale issuer.
- Larger batches would push proof size into the kilobyte range,
  which is a UX problem for verifier clients.

The cap is a soft engineering bound, not a security bound. Bumping it
to 100k is fine if the use case warrants; the proof-size growth is
logarithmic.

## The `committed_to_chain` future-fields

`AnchorBatch` ships with `committed_to_chain`, `external_chain`,
`external_chain_tx` columns that are *operator-set future-fields*.
The `batch_chain_consistency` CHECK constraint enforces that they
move together (you can't have `external_chain_tx` filled while
`committed_to_chain = FALSE`), but no code-path in v8.21 writes to
them. They're a placeholder for the eventual external-ledger
integration.

This is intentional: the schema documents the relationship between
the off-chain batch and the on-chain commitment *before* the on-chain
side is wired. When that integration ships, the schema doesn't need
to change.

## Adversary walk

1. **Defender's claim:** Every closed `AnchorBatch` produces an
   immutable Merkle root; the inclusion proof for any leaf
   (`token_id`, `commitment_hash`) is forge-proof under SHA3-256
   collision resistance. A verifier given (root, leaf, proof) can
   independently confirm the leaf was in the batch at close time.
2. **Attacker's optimal response:** Pre-image search on SHA3-256 to
   forge a leaf that hashes into an existing root. SHA3-256 has
   256-bit pre-image resistance; the attacker reduces to brute
   force against a hash family selected post-quantum-comfortable.
   Game over for the attacker at the cryptographic layer.
3. **Equilibrium:** The Merkle layer is computationally infeasible
   to forge; the attacker must move *up the stack* to attack
   (a) the batch-construction procedure (`close_anchor_batch`),
   (b) the per-algorithm advisory lock that scopes which leaves
   are eligible for a batch, or (c) the post-close immutability
   trigger (`trg_anchor_batch_append_only`).
4. **Second-best attack:** Race two concurrent batch-close calls
   against the same algorithm to compose a malicious leaf set
   before the lock acquires. Defeated by the per-algorithm
   `pg_advisory_xact_lock(algorithm_id)` (4th catalog entry in
   `DEVNOTES/concurrency.md`): the second caller waits, then sees
   the first caller's `batch_id IS NOT NULL` rows and finds no
   eligible leaves. Tested by
   `ConcurrencyTests.test_close_anchor_batch_concurrent`.
5. **Defender's cost:** Per-algorithm scoping means batches with
   mixed algorithms can't co-exist in one Merkle tree. A future
   "global anchor" would require a separate procedure with a
   weaker (or differently-scoped) lock. Accepted: the algorithm-
   scope is a feature, not a bug — it preserves cryptographic
   substitutability per the v8.30 principle.
6. **Mechanism-design note:** The 10,000-leaf hard cap is a
   Schelling-point choice balancing proof-size (logarithmic in
   batch size) against operator-pace (one batch = one ledger
   transaction = one operator approval). Lowering the cap
   tightens batch latency; raising it amortizes more leaves per
   ledger tx. The choice is operator-policy, not constitutional.

## Cross-references

- `polaris_web/anchoring.py` — the Merkle helper (compute_batch,
  leaf_hash, merkle_root, inclusion_proof, verify_proof).
- `polaris_sql/01_schema.sql` — `AnchorBatch` table, extended
  `BlockchainAnchor` with `batch_id` + `merkle_proof`.
- `polaris_sql/05_procedures.sql` — `close_anchor_batch` procedure.
- `polaris_sql/06_triggers.sql` — `trg_anchor_batch_append_only`.
- `polaris_sql/08_tests.sql` — Section O (5 self-tests).
- `polaris_web/test_app.py` — `AnchorBatchTests` (15 tests),
  `ConcurrencyTests.test_close_anchor_batch_*` (2 tests).
- `DEVNOTES/audit-of-record.md` — `AnchorBatch` is the 5th instance
  of the principle.
- `DEVNOTES/concurrency.md` — per-algorithm advisory-lock is the
  4th entry in the catalog.
- `MISSION.md` — M2-2 marked ✅ in the v2 done-list.
- `sanctum/2026-05-11-r10-2-functional-did-anchoring.md` — the
  consultation that authorized this work.
