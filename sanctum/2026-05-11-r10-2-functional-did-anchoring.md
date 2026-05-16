# Sanctum: R10-2 functional DID anchoring

**Date:** 2026-05-11
**Petitioner:** agent (Claude, Opus 4.7)
**Principal:** VANTA
**Trigger:** MEDIUM-risk propose-and-wait + Substrate-D arc closure
**Risk class:** MEDIUM
**Status:** CLOSED
**Architect brief ID:** arch-2026-05-11-001 (per 2026-05-11 18:24 EDT brief, the post-v8.20 brief)

---

## I. The Matter

Implement the internal Merkle log + inclusion-proof machinery that
makes `BlockchainAnchor` functional (PDF §9 "Centralized trust
assumption" leg) — the cryptographic-commitment leg of the
Substrate-D arc.

## II. Preparation

- Architect brief: 2026-05-11 18:24 EDT brief, R10-2 ranked #1 with
  score 8 (MEDIUM propose-and-wait); top move after v8.20 ship.
- Proposal draft: [proposals/R10-2-did-anchoring.md](../proposals/R10-2-did-anchoring.md)
  (382 lines after audit; originally 213 — six refinements folded
  in)
- Alignment audit: six refinements identified and folded in:
  1. C9 advisory-lock on `close_anchor_batch` (per-algorithm)
  2. Two `ConcurrencyTests` entries (race + cross-algorithm parallel)
  3. `AnchorBatch` as 5th audit-of-record instance (extends
     `DEVNOTES/audit-of-record.md` from 4 to 5 instances)
  4. Substrate-D arc closure framing (4/5 done after this ship)
  5. Anti-auto-derivation note (`committed_to_chain` is operator-set)
  6. "Schema implements a primitive, operator decides timing"
     framing — first ship where the posture is primitive-work rather
     than agency-behavior-constraint
- Blast radius (~14 files): schema, indexes, procedure, trigger
  extension, sample data, SQL tests, anchoring.py (new Merkle
  helper), Flask routes, Python tests, DEVNOTES (anchoring.md new +
  audit-of-record.md extension + concurrency.md catalog entry),
  MISSION/ROADMAP/CHANGELOG marks, docs/DATA-MODEL + docs/API
- Tests planned: ≥13 `AnchorBatchTests` + 2 `ConcurrencyTests` +
  3–4 SQL self-tests in section O

## III. Alternatives considered

1. **Push to external chain directly in v1** (no internal Merkle log
   first). Rejected: requires committing to a specific PQ-capable
   distributed ledger before that ecosystem is mature (the proposal's
   `ledger_network` enum names ALGORAND_PQ / HYPERLEDGER_INDY /
   CUSTOM_LATTICE, none of which have fully mature PQ deployments
   yet). Internal-log-first matches the PDF anchor: *"the relational
   schema would remain useful as the off-chain event and audit
   layer."*
2. **Per-event anchoring instead of per-batch.** Rejected: would
   require Merkle proofs for every TokenLifecycleEvent (high write
   amplification, large proof sizes). Per-batch matches the natural
   commitment cadence; operators decide batch frequency.
3. **Use C1 (`TokenLifecycleEvent`) as the audit-of-record and skip
   `AnchorBatch` entirely.** Rejected: C1 records per-event state,
   not per-batch cryptographic commitments. They commit at different
   granularities and serve different purposes; the proposal makes
   this explicit in "What this is NOT."
4. **Compute Merkle root inside the PostgreSQL procedure via
   `plpython3u`.** Rejected: makes `plpython3u` a hard dependency.
   Pre-computing the root in `polaris_web/anchoring.py` and passing
   it as a procedure parameter is portable.
5. **Global advisory-lock instead of per-algorithm.** Rejected:
   different-algorithm batches have disjoint leaf sets; serializing
   them across algorithms is needless contention. Per-algorithm
   matches the natural scope.

## IV. Recommendation

Implement R10-2 with all six refinements folded in. The proposal at
[proposals/R10-2-did-anchoring.md](../proposals/R10-2-did-anchoring.md)
is the implementation target.

R10-2 closes the Substrate-D arc to **4/5 done.** After this ship,
only M2-1 (real ZK-SNARK, HIGH-risk) remains in the Substrate-D arc;
the v2 done-list moves to **9/12.**

The cryptographic-commitment leg of Polaris's "post-quantum by
default" claim becomes structurally complete with this ship: ML-DSA
signatures (R11-1 multi-sig M:N), QuantumObserverBinding scaffold
(M2-5), GenomicAnchor (M2-4), and now Merkle-log commitment (R10-2).
The substrate-layer argument from PDF Appendix E is fully realized
at the schema level.

## V. What's needed from VANTA

"Yes do R10-2" plus three remaining decisions (unchanged from the
proposal's original three open questions):

1. **Hash algorithm preference.** Recommend **SHA3-256** (matches
   GenomicAnchor, is post-quantum). Confirm or override.
2. **Initial batch-size cap.** Recommend **10,000 leaves per batch**.
   Higher = fewer batches, smaller proofs per leaf; lower = more
   frequent batching, larger per-proof verification surface.
3. **Auth on `/api/anchor/<token_id>`.** Recommend **auth-required
   (any role)** for v1. Public read would let external verifiers
   operate without an account; that's a deferred v2+ policy question.

## VI. Decision

yes do R10-2

## VII. Outcome

Shipped end-to-end: AnchorBatch table (5th audit-of-record), close_anchor_batch procedure with per-algorithm advisory lock (4th in catalog), anchoring.py Merkle helper, 3 Flask routes, 5 SQL self-tests (section O), 15 AnchorBatchTests + 2 ConcurrencyTests — all passing. M2-2 ✅; Substrate-D arc now 4/5 done. Six refinements from the audit folded in. Canonical execution links: see CHANGELOG.md v8.21 entry; ROADMAP.md R10-2 marked ✅; MISSION.md M2-2 marked ✅; DEVNOTES/anchoring.md (new); DEVNOTES/audit-of-record.md (extended to 5 instances); DEVNOTES/concurrency.md (extended to 4 advisory-lock entries).

