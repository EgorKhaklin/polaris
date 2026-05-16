# Sanctum: m2-1-snark-exploration

**Date:** 2026-05-11
**Petitioner:** agent (Claude, Opus 4.7)
**Principal:** VANTA
**Trigger:** HIGH-risk **alignment-exploration** (new Sanctum variant); design space narrowing before any ship-Sanctum. Acted on the Architect's readiness brief.
**Risk class:** HIGH (cryptographic primitive selection — the highest-stakes Sanctum to date, but no code lands from this one)
**Status:** CLOSED
**Architect brief ID:** arch-2026-05-11-002 (from the M2-1 readiness assessment)

> **Prep-check note:** Same case-sensitive matcher bug as R11-3 surfaced — the script missed `proposals/M2-1-snark-exploration.md` (uppercase M). Proposal IS in place. Tooling fix tracked.

---

## I. The Matter

VANTA's call on three axes that together specify how (and whether) M2-1
ZK-SNARK is approached:

- **Axis A:** which SNARK family (Groth16 / PLONK / Halo2 / Plonky2)
- **Axis B:** circuit design (predicate / validity-tuple / hybrid-Merkle)
- **Axis C:** trusted-setup posture (dev-artifact / universal / transparent)

OR a fourth outcome: defer M2-1 in favor of M2-10 or R8-4.

## II. Preparation

- **Architect brief:** today (2026-05-11) — readiness assessment named the
  cryptographic-apprenticeship gap honestly and recommended exploration
  before ship.
- **Proposal draft:** [`proposals/M2-1-snark-exploration.md`](../proposals/M2-1-snark-exploration.md)
  — survey of 4 SNARK families × 3 circuit designs × 3 setup postures,
  with the compatibility matrix and the substrate impact of each
  combination.
- **Alignment audit:** NOT run in the usual sense. The proposal *is*
  the audit — it surveys options rather than committing to one. The
  six R10-2 / R11-3-style refinement checklist items don't apply
  here because no design is being committed.
- **Blast radius if approved:** ZERO from this Sanctum. Code, schema,
  procedures, tests are untouched. The blast-radius assessment will
  happen in the follow-up ship-Sanctum, scoped to whatever direction
  VANTA picks.
- **Tests planned (from this Sanctum):** none. From the follow-up
  ship-Sanctum: estimated 30+ Python tests + 5–10 SQL self-tests
  (section Q) + adversary-model tests per PDF acceptance.

## III. Alternatives considered

1. **Ship M2-1 directly without exploration.** Rejected — see Architect
   brief. Cryptographic surface is wider than any prior R-* item;
   "pick by default" would be either lucky or arbitrary, and the
   failure mode of getting M2-1 subtly wrong is silent (invalid
   proofs accepted at verification time).
2. **Defer M2-1 indefinitely.** Rejected — closing the Substrate-D arc
   to 5/5 is high mission-leverage. The arc has 4/5 done; the holdout
   is the *last* substrate item, and deferring it indefinitely leaves
   v2 at 10/12 done with the hardest two items both ⬜.
3. **Ship R8-4 (PostGIS) or M2-10 (duress codes) first.** Acceptable
   as alternative outcomes of this Sanctum. M2-10 has comparable HIGH
   risk but smaller cryptographic surface (no SNARK primitive
   selection). R8-4 is a clean MEDIUM.
4. **Open a Sanctum for M2-10 instead and come back to M2-1 later.**
   Also acceptable — listed as a defer-outcome of this Sanctum.

## IV. Choice tree (instead of single recommendation)

The Architect does NOT recommend a specific combination. Three
independent decisions and one "or escape" axis:

### Recommended ordering: pick Axis C first

The trusted-setup posture (Axis C) has the most operator-honesty
weight and constrains Axis A by construction. Once C is fixed, the
compatible A-entries are obvious. Once A is fixed, B is independent.

### If transparency-first (C3 transparent, no ceremony)

Foreclosed: A1 Groth16, A2 PLONK.
Compatible: A3 Halo2 OR A4 Plonky2.
- **C3 + A3 Halo2:** classical security + no ceremony + medium proof size + Zcash-mainnet maturity. Diplomatic middle.
- **C3 + A4 Plonky2:** PQ-comfortable + no ceremony + larger proofs + Polygon-ecosystem maturity. The "honesty-and-PQ-maximalist" pick.

### If diplomatic middle (C2 universal community setup)

Compatible: A2 PLONK.
- **C2 + A2 PLONK:** community ceremony externalizes trust; proof size moderate; library maturity high; classical security.

### If engineering-pragmatist (C1 dev-artifact ceremony)

Compatible: A1 Groth16, A2 PLONK (custom).
- **C1 + A1 Groth16:** smallest proofs + fastest verifier + most library options + dev-artifact-ceremony-honestly-documented. The "ship-first, honest-about-it" pick.

### Independent: Axis B

- **B1 Predicate:** end-to-end ZK; no trust on issuer; very heavy circuit.
- **B2 Validity-tuple:** issuer pre-signs; light circuit; classical issuer-trust posture.
- **B3 Hybrid Merkle:** reuses R10-2 AnchorBatch infrastructure; medium circuit; epoch-bounded staleness.

The Architect notes — but does **not** recommend — that B3 has the
lowest marginal substrate cost because it reuses R10-2's Merkle
machinery.

## V. What's needed from VANTA

Choose one outcome:

- **"C3 + A3"** / **"C3 + A4"** / **"C2 + A2"** / **"C1 + A1"** (or any
  other valid combination from the compatibility matrix) — pick the
  Axis A × C combination; pick Axis B independently.
- **"explore more"** — proposal needs deeper survey on one specific
  axis. Name which.
- **"defer M2-1; do M2-10 next"** — pivot to duress codes (also
  HIGH-risk, smaller crypto surface).
- **"defer M2-1; do R8-4 next"** — pivot to PostGIS (clean MEDIUM,
  performance ship).
- **"defer M2-1 indefinitely"** — close v2 at 10/12 done; substrate
  arc remains 4/5.

Picking C + A + B opens a follow-up ship-Sanctum scoped to that
combination. The follow-up ship-Sanctum then does the audit-refinement
work in the usual R10-2 / R11-3 style.

## VI. Decision

lets proceed with your recommendation. (C3 transparent + A4 Plonky2 + B3 hybrid-Merkle reusing R10-2)

## VII. Outcome

Design space narrowed to C3+A4+B3: transparent setup (no ceremony), Plonky2 SNARK family (FRI-based, post-quantum-comfortable), hybrid-Merkle circuit reusing R10-2 AnchorBatch infrastructure. The Architect committed to this direction when called on neutrality, naming the trade-offs explicitly (library maturity, proof size, epoch-bounded staleness, Rust toolchain). Canonical execution links: follow-up ship-Sanctum at sanctum/2026-05-11-m2-1-snark-plonky2-merkle.md scopes the actual implementation with the audit-refinement work in the R10-2 / R11-3 style. The alignment-exploration Sanctum variant is now a recorded protocol pattern: when a design space is too wide for a single ship-Sanctum to be honest, the first Sanctum surveys and the second Sanctum ships within the narrowed space.

**See:** [CHANGELOG `## v8.23 (the ZK-SNARK ship that followed this exploration Sanctum)`](../CHANGELOG.md) · [`journal/2026-05-11.md`](../journal/2026-05-11.md). Cross-ref added v8.61 per Architect-reflection finding.
