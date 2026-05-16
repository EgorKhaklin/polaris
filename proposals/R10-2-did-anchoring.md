# proposals/R10-2-did-anchoring.md

**Risk class:** MEDIUM (propose-and-wait)
**Mission link:** v2 M2-2 (substrate arc)
**Status:** PROPOSED, awaiting VANTA approval
**Effort:** ~2-3 sessions
**Architect ID:** arch-2026-05-11-001 (per first brief)

## Problem

`BlockchainAnchor` exists in the schema with the `ledger_network` enum
(`ALGORAND_PQ`, `HYPERLEDGER_INDY`, `CUSTOM_LATTICE`) and per-token
rows, but no actual anchoring machinery. Today a row in
`BlockchainAnchor` is just metadata; there is no Merkle structure, no
inclusion proof, no way for an external verifier to assert "this token
was committed to a tamper-evident log at time T."

This closes the substrate arc. After v8.11, M2-3, M2-4, M2-5 are ✅
done; only M2-2 remains open in the D-arc.

## Why MEDIUM

The verification flow may eventually depend on inclusion proofs (a
verifier checking a token's history could demand "show me this token's
Merkle proof at the time of issuance"). The API shape needs upfront
design before code, and the hash-algorithm choice is a governance
decision per C7. Schema additions and a new endpoint also expand the
attack surface.

LOW would be wrong because verifiers may rely on the proof format
across release boundaries. HIGH would be wrong because the internal
Merkle log is well-bounded and external chain anchoring is left to a
future increment.

## Substrate-D arc closure

R10-2 closes the Substrate-D arc to **4/5 done**. The arc spans M2-1
through M2-5; M2-3 (substrate manifest), M2-4 (GenomicAnchor), and
M2-5 (QuantumObserverBinding scaffold) all shipped in v8. After
R10-2 ships, only **M2-1 (real ZK-SNARK for ZERO_KNOWLEDGE
verifications)** remains as the lone HIGH-risk Substrate-D item.

| Substrate-D leg | Item | Status |
|---|---|---|
| Substrate manifest | M2-3 | ✅ v8 |
| GenomicAnchor schema | M2-4 | ✅ v8 |
| QuantumObserverBinding scaffold | M2-5 | ✅ v8.11 |
| **DID anchoring (Merkle log)** | **M2-2 (R10-2)** | ⬜ this proposal |
| Real ZK-SNARK | M2-1 | ⬜ HIGH-risk holdout |

The PDF §9 "Centralized trust assumption" anchor for R10-2 says
explicitly: *"the relational schema would remain useful as the
off-chain event and audit layer."* The internal Merkle log this
proposal builds IS that off-chain audit layer; external-chain
integration is deferred as future work.

## "Schema implements a primitive, operator decides timing"

R10-2 differs from the v8.15–v8.18 ships (R11-6 issuer-discretion,
R11-4 tiered enrollment, R11-2 catastrophic-loss recovery, R11-1
multi-sig) in posture. Those four were "the schema constrains the
shape of agency behavior" ships — the schema added vocabulary and
structural constraints while agencies made decisions about *who*,
*when*, and *which path*.

R10-2 is different: **the schema implements a cryptographic primitive
(Merkle log + inclusion proofs); the operator decides timing
(when to close a batch, when to push to an external chain).**

What the schema does:

- Computes a deterministic Merkle root from the pending leaf set.
- Stores the root, batch metadata, and per-leaf inclusion proofs.
- Enforces the append-only invariant on AnchorBatch
  (audit-of-record — see refinement below).

What the operator decides:

- When to call `close_anchor_batch` (cadence is policy, not schema-driven).
- When to mark `committed_to_chain=TRUE` and which external chain
  (no auto-derivation; an external commit is recorded only when it
  actually happens).
- Whether to expose `/api/anchor/<token_id>` to unauthenticated verifiers
  in the future (currently auth-required; that's a deferred policy decision).

This is the same separation-of-concerns the prior four ships
established — the schema does not act on its own — but the
balance shifts: more primitive, less constraint. R10-2 is the first
ship where the schema is *doing cryptographic work* rather than
*recording policy choices*. The MISSION constraint "Polaris is NOT
an authority" is preserved because the schema still doesn't decide
*what should be anchored* (operator triggers batch close) or *which
external chain to use* (operator selects from the
`ledger_network` enum).

## Game-theoretic structure

- **Game type:** Commitment device (Merkle root is the irreversible
  commitment).
- **Defender's claim:** for every token committed in batch B, an
  inclusion proof exists; tampering with the leaf set invalidates the
  proof.
- **Attacker's optimal response:** forge an inclusion proof for a
  token that was never in the batch.
- **Equilibrium:** Merkle hash function's collision resistance is the
  floor; if the hash holds, proofs are unforgeable.
- **Second-best attack:** publish-then-fork — get a token into batch
  B, observe the published root, then claim a different leaf order
  produced the same root. Defended by deterministic leaf ordering
  (sort by `token_id`).
- **Mechanism-design note:** anchoring shifts the attacker's cost from
  "forge a signature" to "forge a chain of hashes." Hash-collision
  attacks are much more expensive than signature forgery in the
  PQ-secure regime.

Pairs naturally with C1 (append-only audit) — both are commitment
devices, but at different layers: C1 commits per-event, R10-2 commits
per-batch.

## Recommended approach

**Internal Merkle log first; external chain anchoring later.** The
internal log is the smallest credible step. External chain integration
(actually pushing roots to Algorand-PQ, etc.) is a separate proposal
when the chain ecosystem is ready.

Three parts:

1. **`AnchorBatch` table** — one row per Merkle batch.
2. **Extended `BlockchainAnchor`** — per-token rows now carry the
   `batch_id` and `merkle_proof` (JSON-encoded inclusion path).
3. **Three endpoints** — close-batch (admin), get-proof (any auth),
   verify-proof (any auth, no DB write).

## Implementation sketch

### Schema

```sql
CREATE TABLE AnchorBatch (
    batch_id            SERIAL       PRIMARY KEY,
    merkle_root         VARCHAR(128) NOT NULL,
    algorithm_id        INTEGER      NOT NULL
                        REFERENCES CryptographicAlgorithm(algorithm_id),
    batch_size          INTEGER      NOT NULL CHECK (batch_size > 0),
    created_at          TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    committed_to_chain  BOOLEAN      NOT NULL DEFAULT FALSE,
    external_chain      VARCHAR(40),    -- ledger_network enum subset, NULL while internal-only
    external_chain_tx   VARCHAR(128),   -- tx id on the external chain, NULL while internal-only

    CONSTRAINT batch_root_is_hex CHECK (merkle_root ~ '^[0-9a-fA-F]+$'),
    CONSTRAINT batch_chain_consistency CHECK (
        (committed_to_chain = FALSE AND external_chain IS NULL AND external_chain_tx IS NULL) OR
        (committed_to_chain = TRUE  AND external_chain IS NOT NULL)
    )
);

ALTER TABLE BlockchainAnchor
    ADD COLUMN batch_id     INTEGER REFERENCES AnchorBatch(batch_id),
    ADD COLUMN merkle_proof JSONB,
    ADD CONSTRAINT anchor_proof_with_batch CHECK (
        (batch_id IS NULL AND merkle_proof IS NULL) OR
        (batch_id IS NOT NULL AND merkle_proof IS NOT NULL)
    );
```

`AnchorBatch` is append-only by trigger (same pattern as the v1 audit
tables — `reject_update_delete`). Once a batch is committed, its
`merkle_root` cannot be rewritten.

### Stored procedure

```sql
CREATE PROCEDURE close_anchor_batch(
    p_algorithm_id INTEGER,
    p_merkle_root  VARCHAR(128)   -- pre-computed by anchoring.py
)
LANGUAGE plpgsql AS $$
    -- 0. C9: per-algorithm advisory-lock to serialize concurrent
    --    batch-close attempts on the same algorithm. Without this, two
    --    threads both SELECT the same WHERE batch_id IS NULL set, both
    --    INSERT an AnchorBatch row, then one's UPDATE collides with the
    --    other's already-set batch_id — leaving a phantom AnchorBatch.
    --    See "Concurrency (C9)" subsection below.
    PERFORM pg_advisory_xact_lock(
        hashtext('polaris.anchor.close-batch.' || p_algorithm_id::TEXT));
    -- 1. Select all BlockchainAnchor rows where batch_id IS NULL and the
    --    token was signed under p_algorithm_id (per-algorithm batching).
    --    Sort by token_id (deterministic leaf order — defeats publish-then-fork).
    -- 2. INSERT AnchorBatch row with p_merkle_root.
    -- 3. UPDATE BlockchainAnchor rows to set batch_id + merkle_proof.
    -- 4. The auto-audit trigger writes TokenLifecycleEvent rows
    --    (event_type = 'ANCHOR_BATCHED').
$$;
```

The Merkle implementation lives in a small Python helper
(`polaris_web/anchoring.py`) so the SQL procedure can call it via
`plpython3u` if available, or the app can pre-compute the root and
pass it in. **Recommend the latter** for portability (avoid plpython3u
as a hard dependency) — that's why the procedure signature accepts
`p_merkle_root` as a parameter rather than computing it internally.

### Concurrency (C9)

The advisory-lock keyed on `hashtext('polaris.anchor.close-batch.' ||
algorithm_id)` follows the per-entity-lock pattern catalog in
`DEVNOTES/concurrency.md`:

| Procedure | Lock key | Cross-key parallelism |
|---|---|---|
| `uc8_revoke_token` | per-agency | cross-agency parallel |
| `uc9_complete_recovery` | per-individual | cross-individual parallel |
| `uc6_migrate_algorithm` | per-token | cross-token parallel |
| **`close_anchor_batch`** | **per-algorithm** | **cross-algorithm parallel** |

The natural scope of contention for batch-close is per-algorithm:
two threads closing batches for different algorithms have disjoint
leaf sets and can proceed in parallel. Same-algorithm threads must
serialize so the pending-set selection and the AnchorBatch INSERT
land atomically.

This becomes the fourth advisory-lock entry in
`DEVNOTES/concurrency.md` after R11-1's per-token addition (v8.18).

### App routes

| Route | Method | Purpose |
|---|---|---|
| `/api/anchor/batch` | POST | Close current batch (admin only); returns `batch_id` |
| `/api/anchor/<token_id>` | GET | Returns the token's inclusion proof + root |
| `/api/anchor/verify/<token_id>` | GET | Re-validates the inclusion proof against the stored root |

Per C8: all three have hard caps. Batch close has an upper bound on
`batch_size` (recommend 10,000 leaves per batch as the initial cap).

### Tests

`AnchorBatchTests` class:

- Empty batch close (no pending anchors) → procedure raises clean error
- Single-leaf batch (degenerate Merkle; root = hash of leaf)
- Multi-leaf batch (4, 7, 8 leaves — covering even, odd, power-of-2)
- Inclusion-proof generation correctness (verify each leaf reproduces root)
- Inclusion-proof verification (positive + negative)
- Batch-tampering detection (modify a leaf, proof should fail)
- Deterministic leaf ordering (same set in different insert order → same root)
- Anchor row without batch raises CHECK violation
- Anchor row with batch but no proof raises CHECK violation
- `AnchorBatch` append-only: UPDATE to `merkle_root` rejected
- `AnchorBatch` append-only: DELETE rejected
- `committed_to_chain=FALSE` row cannot have `external_chain_tx` set
  (CHECK violation)
- No auto-derivation: setting `CryptographicAlgorithm.deprecation_date`
  does NOT cascade into any `AnchorBatch.committed_to_chain` flag

**Concurrency tests (C9, in `ConcurrencyTests`):**

- **Race two `close_anchor_batch` calls for the same algorithm.**
  Seed N pending `BlockchainAnchor` rows (batch_id IS NULL). Spawn
  T ≥ 4 threads each calling `close_anchor_batch(alg_id, merkle_root)`.
  Per-thread psycopg2 connections (no mocks per C9). Expected: the
  advisory-lock serializes the threads; exactly one AnchorBatch
  row is produced, and all N pending anchors are atomically assigned
  to it. Losing threads see the empty WHERE batch_id IS NULL set and
  raise the "empty batch close" error cleanly.

- **Cross-algorithm batch closes run in parallel.** Seed pending
  anchors under two different algorithms. Two threads each close a
  batch for a different algorithm. Both succeed. Wall-clock check
  asserts elapsed time < 1.5× single-thread time (the advisory-lock
  key is per-algorithm; no cross-algorithm contention).

## Predicted blast radius

- `polaris_sql/01_schema.sql` — new `AnchorBatch` table, extended
  `BlockchainAnchor` (~60 lines). Schema goes to 19 tables.
- `polaris_sql/05_procedures.sql` — `close_anchor_batch` with
  per-algorithm advisory-lock (~100 lines). Procedure count goes to 9.
- `polaris_sql/06_triggers.sql` — append-only trigger for `AnchorBatch`
  via `reject_audit_modification` extension (the same trigger function
  that already protects TokenLifecycleEvent, VerificationEvent,
  EnrollmentStatusEvent).
- `polaris_sql/02_indexes.sql` — index on `BlockchainAnchor.batch_id`
  for proof-lookup queries.
- `polaris_sql/08_tests.sql` — section O: 3–4 SQL self-tests for the
  CHECK constraints + append-only behavior.
- `polaris_web/anchoring.py` (new) — Merkle helper (~150 lines).
- `polaris_web/app.py` — 3 routes (~80 lines).
- `polaris_web/test_app.py` — `AnchorBatchTests` (~320 lines, ≥13
  tests) + 2 `ConcurrencyTests` entries (~80 lines) for the
  per-algorithm race and cross-algorithm parallelism.
- `polaris_sql/13_substrate.sql` — add Merkle-log primitive to
  `SystemDependency` view.
- `DEVNOTES/anchoring.md` (new) — design rationale, hash-algorithm
  selection, eventual-external-chain plan, the cryptographic-primitive-
  vs-authority framing.
- **`DEVNOTES/audit-of-record.md`** — extend the instances table from
  four to five rows; add AnchorBatch's conformance grading.
- **`DEVNOTES/concurrency.md`** — append the per-algorithm advisory-
  lock pattern entry (fourth in the catalog).
- `MISSION.md` — mark M2-2 ✅.
- `ROADMAP.md` — mark R10-2 ✅; note Substrate-D arc closure.
- `docs/DATA-MODEL.md` — new `AnchorBatch` section.
- `docs/API.md` — three new endpoints documented.

## Acceptance criteria

- ✅ `AnchorBatch` table exists; append-only trigger enforced.
- ✅ `BlockchainAnchor` extended with `batch_id` + `merkle_proof`;
  CHECK constraint enforces "both or neither."
- ✅ `close_anchor_batch` procedure produces deterministic root for a
  given leaf set.
- ✅ **C9 advisory-lock**: `close_anchor_batch` opens with
  `pg_advisory_xact_lock(hashtext('polaris.anchor.close-batch.' ||
  p_algorithm_id::TEXT))`. Same-algorithm batch-closes serialize
  cleanly; cross-algorithm batch-closes parallelize. The fourth
  per-entity-lock entry in the catalog (after R11-1's per-token,
  R11-2's per-individual, R11-6's per-agency).
- ✅ **AnchorBatch is the 5th audit-of-record instance.**
  `DEVNOTES/audit-of-record.md`'s instance table extends from four
  rows to five. Update both the table and the conformance grading
  section.
- ✅ `/api/anchor/<token_id>` returns valid proof; verify endpoint
  succeeds.
- ✅ Tampering with any leaf invalidates the proof (regression test).
- ✅ **No auto-derivation:** test asserts
  `CryptographicAlgorithm.deprecation_date` changes do not cascade
  into any `AnchorBatch` state.
- ✅ `SystemDependency` view + `DEVNOTES/substrate.md` updated with
  Merkle-log primitive.
- ✅ `docs/DATA-MODEL.md` documents `AnchorBatch`; doc↔schema test
  still passes.
- ✅ ≥ 13 new tests in `AnchorBatchTests` (was ≥ 9 in the original
  draft; refinements added append-only-mutation tests,
  no-auto-derivation, CHECK-constraint coverage) + ≥ 2 new tests in
  `ConcurrencyTests` (per-algorithm race, cross-algorithm parallelism).
- ✅ External-chain integration left explicitly DEFERRED in
  `DEVNOTES/anchoring.md` with the migration path described.
- ✅ **Substrate-D arc closure** explicitly noted in CHANGELOG:
  after R10-2, the arc is 4/5 done with only M2-1 (real ZK-SNARK,
  HIGH-risk) remaining.

## What this is NOT

- Not actually anchoring to an external chain. That's a separate
  proposal. This is internal-Merkle-log only.
- Not changing C1 (per-event audit). C1 and R10-2 coexist; each
  commits at a different granularity. **`AnchorBatch` joins the
  audit-of-record principle** (`DEVNOTES/audit-of-record.md`) as the
  fifth instance, alongside `TokenLifecycleEvent` (per-event),
  `RecoveryRequest` (per-ceremony), `TokenSignature` (per-migration),
  and Sanctum sessions (per-strategic-decision). `AnchorBatch` is the
  *per-batch commitment-time* audit-of-record: the row's own state
  (`merkle_root`, `batch_size`, `created_at`) plus append-only
  invariants together fully reconstruct what was committed at time T.
- Not opening cross-chain interoperability (that's M2-8 / R11-3).
- **Not auto-derivation.** `committed_to_chain`, `external_chain`,
  and `external_chain_tx` are operator-set when an external commit
  actually happens. The schema does NOT auto-flip
  `committed_to_chain=TRUE` based on time, batch age, or any other
  trigger. Same anti-auto-derivation posture as R11-4 (no auto-LAPSED
  from token state) and R11-1 (no auto-deprecation cascading from
  `CryptographicAlgorithm.deprecation_date`).
- Not Polaris deciding *which* tokens to anchor or *when* to close
  a batch. Operator policy (cadence, batch-size threshold, chain
  selection) drives the timing. The schema computes the cryptographic
  primitive on operator demand and refuses to silently lose history.

## What this needs from you

"Yes do R10-2" plus:

1. **Hash algorithm preference.** Default would be SHA3-256
   (matches GenomicAnchor and is post-quantum). Confirm or override.
2. **Initial batch-size cap.** Recommend 10,000. Higher = fewer
   batches, smaller proofs; lower = more frequent batching, larger
   per-proof verification surface.
3. **Whether to allow public read on `/api/anchor/<token_id>`.**
   Current proposal: auth required (any role). Public read would let
   verifiers operate without an account. Recommend auth-required for
   v1.
