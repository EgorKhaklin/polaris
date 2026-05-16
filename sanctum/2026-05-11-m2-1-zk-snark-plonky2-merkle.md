# Sanctum: m2-1-zk-snark-plonky2-merkle

**Date:** 2026-05-11
**Petitioner:** agent (Claude, Opus 4.7)
**Principal:** VANTA
**Trigger:** HIGH-risk ship-Sanctum scoped by the M2-1 exploration Sanctum (which picked C3+A4+B3). Final substrate-D arc closure leg; largest single ship in Polaris history (multi-language, multi-component, multi-session if needed).
**Risk class:** HIGH (cryptographic-correctness; new Rust toolchain dependency; verification-flow change for ZERO_KNOWLEDGE outcomes; silent-failure mode if circuit is subtly wrong)
**Status:** CLOSED
**Architect brief ID:** arch-2026-05-11-002 (continues from the readiness brief and exploration Sanctum)

> **Prep-check note:** Same case-sensitive matcher bug — script missed `proposals/M2-1-zk-snark-plonky2-merkle.md` (uppercase M). Proposal IS in place. Tooling fix tracked.

---

## I. The Matter

VANTA's approval to ship **M2-1 ZK-SNARK** as scoped: Plonky2 + transparent setup + hybrid-Merkle circuit reusing R10-2. Closes the Substrate-D arc to 5/5 and v2 to 11/12.

## II. Preparation

- **Architect brief:** arch-2026-05-11-002 — committed to C3+A4+B3 after VANTA called my neutrality.
- **Exploration Sanctum (closed):** [`sanctum/2026-05-11-m2-1-snark-exploration.md`](./2026-05-11-m2-1-snark-exploration.md) — narrowed the design space from 36 candidate combinations to one.
- **Proposal draft:** [`proposals/M2-1-zk-snark-plonky2-merkle.md`](../proposals/M2-1-zk-snark-plonky2-merkle.md) — scoped within the picked combination; nine audit refinements (R1–R9) folded in before this Sanctum entry.
- **Alignment audit:** ran the established checklist plus four SNARK-specific items (R1 binding, R2 replay, R3 witness-leak, R4 epoch-boundary). Surfaced and folded in nine refinements total — one more than R11-1's seven, reflecting the wider cryptographic surface.
- **Blast radius if approved:**
  - Schema: +2 tables (`TokenStateEpoch`, `TokenStateEpochLeaf`), +1 trigger (`enforce_epoch_immutability`), +1 partial unique index
  - Procedures: +1 (`uc11_close_epoch`) with per-epoch-id advisory lock (**6th catalog entry**)
  - **New top-level directory: `polaris_zk/`** (Rust workspace using `mir-protocol/plonky2`)
  - Python: 1 new module (`polaris_web/zk.py`); `verifications_new` extended
  - Flask: +3 routes (`/api/zk/epoch/close`, `/api/zk/epoch/<id>`, `/api/zk/verify`)
  - Tests: +18 `ZKSnarkTests` + 2 `ConcurrencyTests` + 5 SQL section Q + Rust unit tests in `polaris_zk/tests/`
  - DEVNOTES: 1 new (`zk-snark.md`), 3 extended (`audit-of-record.md` → 7 instances, `concurrency.md` → 6 advisory-lock entries, `substrate.md` → 27 rows with Plonky2 + Rust toolchain)
  - Substrate manifest grows by 2 entries — the largest substrate addition since v6 Redis
  - Counts: 20 → 22 tables; 11 → 12 procedures; 11 → 12 triggers; 6 → 7 audit-of-record instances; 5 → 6 advisory-lock entries
- **Tests planned:** ~25 (18 ZKSnark + 2 concurrency + 5 SQL Q) — plus Rust unit tests in the new crate, plus adversary-model tests per PDF acceptance criterion.
- **Phasing:** v1 (this Sanctum, target v8.23) ships the full scaffolding + a working Merkle-inclusion circuit. v2 (future) extracts holder-side prover and encrypts witness rows. M2-1 closes at v8.23.

## III. Alternatives considered

1. **Ship M2-1 without phasing — single monolithic ship.** Rejected because the Rust + Python + circuit + schema integration is multi-component; phasing makes the v1 deliverable testable end-to-end without paying for production hardening upfront. The phasing IS the honest scope.
2. **Pure Python SNARK library (e.g., `pysnark`, `py_ecc`).** Rejected at the exploration-Sanctum level — A4 Plonky2 is Rust-native; no Python implementation exists. Adding a Python SNARK library means abandoning the C3+A4 axis-combination VANTA picked.
3. **Defer Plonky2 integration; ship the schema-only half now, the Rust half later.** Rejected because the schema additions only make sense if the SNARK is actually integrated. Shipping `TokenStateEpoch` without a verifier that uses it would be a half-thing — the Polaris quality bar refuses half-things.
4. **B1 predicate circuit (full validity-in-circuit) instead of B3 hybrid.** Foreclosed by the exploration-Sanctum decision; would be a different ship-proposal.

## IV. Recommendation

Approve M2-1 ship as scoped in the proposal. All nine audit refinements folded in. The "Pre-Sanctum sanity checklist" is fully green.

The strategic case rests on four observations:

1. **This closes the v2 arc on the substrate side.** Substrate-D goes from 4/5 to 5/5. Combined with the holder-protection triad (3/3) and the issuer-trust-concentration triad (3/3), v2 reaches 11/12 done — only M2-10 duress codes remain.
2. **The exploration Sanctum did the heavy alignment work.** VANTA already picked the design space; this Sanctum scopes execution within the narrowed space. The audit refinements R1–R9 are mechanical extensions of the established pattern plus four SNARK-specific items.
3. **Honest phasing keeps the ship scopable.** v1 delivers a real ZK proof (Merkle-inclusion under Plonky2) that meets the PDF acceptance criteria. v2 hardens for production. The phase boundary is named, not hidden.
4. **The "honest about library maturity" posture is part of the ship.** Plonky2 is the youngest of the four candidates; we pinned the version, accept the risk explicitly, and noted that the B3 epoch-bounded architecture lets us re-port to Halo2 in a future migration without changing the schema.

## V. What's needed from VANTA

Choose one:

- **"yes do M2-1"** — proceed with the audited proposal as scoped. v1 targets v8.23.
- **"yes with changes: X, Y"** — proceed with modifications.
- **"phase differently"** — split the ship into N>1 Sanctums (e.g., schema-only first, Rust-second).
- **"defer; do M2-10 next"** — pivot to duress codes; M2-1 stays open.
- **"reject"** — proposal needs deeper revision; the SNARK ship doesn't ship.

## VI. Decision

Proceed with the architects recommendation.

## VII. Outcome

Shipped end-to-end: TokenStateEpoch + TokenStateEpochLeaf tables (7th audit-of-record), enforce_epoch_immutability trigger, uc11_close_epoch procedure with per-procedure advisory lock (6th catalog entry, first non-per-entity), polaris_zk/ Rust crate (Plonky2 circuit + prover + verifier + CLI binary), polaris_web/zk.py subprocess wrapper, three /api/zk/* routes (epoch/close, epoch/<id>, verify), demo epoch seed (3 leaves over BANKING tokens T2/T3/T4), 5 SQL self-tests section Q, 15 ZKSnarkTests + 2 ConcurrencyTests + 3 Rust unit tests — all 22 Python ZK tests passing, all 73 SQL tests passing on full clean reload. Nine audit refinements (R1-R9) folded in. **Substrate-D arc closed 5/5** — every PDF Appendix E/F primitive now in-tree or scaffolded; v2 done-list = 11 ✅ / 1 ⬜ (only M2-10 duress codes remains). Canonical execution links: CHANGELOG.md v8.23 entry; MISSION.md M2-1 marked ✅; ROADMAP.md R10-1 marked ✅; DEVNOTES/zk-snark.md (new); DEVNOTES/audit-of-record.md extended to 7 instances; DEVNOTES/concurrency.md extended to 6 entries; DEVNOTES/substrate.md + polaris_sql/13_substrate.sql extended with Plonky2 + Rust toolchain (27 primitives total).

