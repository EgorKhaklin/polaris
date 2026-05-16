# proposals/M2-1-snark-exploration.md

**Risk class:** HIGH (cryptographic primitive selection; trusted-setup posture; ZK-SNARK substrate addition)
**Mission link:** v2 M2-1 (Substrate-D arc closure leg — the last ⬜)
**Status:** PROPOSED — **alignment-exploration**, NOT ship-recommendation
**Effort:** N/A (this proposal narrows the design space; ship effort scoped after VANTA picks a direction)
**Architect ID:** arch-2026-05-11-002 (from the M2-1 readiness brief)

---

## Why this proposal does not recommend

The Architect's readiness brief (arch-2026-05-11-002) named the gap honestly:
M2-1 has a **graduate-level cryptographic surface** and **no in-tree
precedent** to lean on. The four candidate SNARK families differ in
proof size, prover/verifier time, trusted-setup requirement, and
library maturity. The three circuit-design options differ in what gets
proven and how heavy the circuit becomes. The trusted-setup posture
options differ in operator-honesty implications.

Picking one without surveying the others would either be lucky or
arbitrary. The audit-then-Sanctum pattern as established (R10-2, R11-3)
assumes the design space is *bounded by Polaris's own conventions* —
audit-of-record, advisory-lock catalog, anti-auto-derivation. M2-1's
design space is *bounded by the cryptographic literature*. The honest
move is to narrow it first, in dialogue with VANTA, and ship within the
narrowed space later.

This proposal therefore surveys. The exit condition is VANTA picking a
direction across three independent axes. A subsequent ship-Sanctum
will execute within the narrowed direction.

---

## Axis A — SNARK family

Four candidate families that meet the M2-1 acceptance criterion ("real
ZK-SNARK for ZERO_KNOWLEDGE verifications"). Each entry names what it
trades for what.

### A1. Groth16

- **Proof size:** 192–256 bytes (smallest of the four)
- **Verifier time:** ~5 ms (constant; 3 pairings)
- **Prover time:** linear in circuit size; typically 100 ms – 10 s
  depending on circuit depth
- **Trusted setup:** REQUIRED, per-circuit. If the circuit changes,
  the ceremony must be re-run.
- **Library maturity:** highest. `arkworks` (Rust), `gnark` (Go),
  `libsnark` (C++), `snarkjs` (Node), `circom` (JS circuit compiler)
  are all production-grade. Zcash, Tornado Cash, Filecoin ship on
  Groth16.
- **Post-quantum posture:** classical (elliptic-curve pairings). Not
  PQ-safe. Aligns with the PDF's "post-quantum by default" only at
  the schema layer, not the SNARK layer.
- **What Polaris would import:** typically `arkworks` via Rust →
  Python (subprocess or PyO3 bindings) OR `circom` + `snarkjs` shelling
  out from Python.

### A2. PLONK

- **Proof size:** 400–600 bytes
- **Verifier time:** ~5–10 ms
- **Prover time:** comparable to Groth16; sometimes slower
- **Trusted setup:** REQUIRED but **universal** — one ceremony serves
  every circuit up to a given size. The Perpetual Powers of Tau
  community ceremony is publicly verifiable and reusable.
- **Library maturity:** high. `halo2`, `arkworks-plonk`,
  `plonky-plonk`, `gnark`, several Rust implementations.
- **Post-quantum posture:** same as Groth16 (elliptic-curve based;
  classical security).
- **What Polaris would import:** typically `arkworks` or
  `halo2-proofs` (the latter is misleadingly named — it implements
  both PLONK and Halo2 schemes).

### A3. Halo2

- **Proof size:** 1.5–2 KB (3–10× Groth16)
- **Verifier time:** ~30–100 ms (slower; recursion overhead)
- **Prover time:** comparable to Groth16 / PLONK
- **Trusted setup:** **NONE**. Halo2 is transparent — no ceremony.
- **Library maturity:** high. The reference implementation is
  `zcash/halo2` (Rust). Zcash's mainnet runs on Halo2 as of 2022.
- **Post-quantum posture:** classical (elliptic curves under the hood).
  Halo2 is no more PQ-safe than Groth16 in the cryptographic sense,
  but its NO-trusted-setup property *honestly removes one class of
  failure mode* (compromised ceremony) that PQ analysis cannot fix.
- **What Polaris would import:** `halo2` (Rust) via subprocess or
  PyO3 bindings. No Python-native implementation.

### A4. Plonky2

- **Proof size:** 4–10 KB (largest of the four)
- **Verifier time:** ~50–200 ms
- **Prover time:** **very fast** — sub-second for medium circuits
  (the Plonky2 selling point)
- **Trusted setup:** **NONE**. FRI-based (hash-only commitments).
- **Library maturity:** medium. `mir-protocol/plonky2` (Rust) is the
  reference; no production deployments outside the Polygon ecosystem
  at scale.
- **Post-quantum posture:** **best of the four**. FRI is hash-based;
  hashes (SHA-256, Poseidon) are PQ-comfortable. This is the only
  candidate that *aligns* with Polaris's PQ posture at the SNARK layer.
- **What Polaris would import:** `plonky2` (Rust) via subprocess. No
  Python-native implementation; bindings are immature.

### Comparison

| Axis A entry | Proof size | Verifier | Trusted setup | PQ posture | Library maturity |
|---|---|---|---|---|---|
| A1 Groth16 | 192 B | ~5 ms | per-circuit | classical | highest |
| A2 PLONK | 500 B | ~10 ms | universal | classical | high |
| A3 Halo2 | 1.5 KB | ~50 ms | none | classical | high |
| A4 Plonky2 | 5 KB | ~100 ms | none | post-quantum | medium |

The Architect notes — but does **not** recommend — that A3 and A4
align best with Polaris's "honesty-first, PQ-by-default" posture. A1
is the easiest engineering shipment. A2 is the diplomatic middle
ground (universal setup is reusable; the community ceremony
externalizes the trust assumption). **VANTA picks.**

---

## Axis B — Circuit design

Three options for what the SNARK actually proves. Each interacts
with Axis A differently and has different schema implications.

### B1. Predicate-by-predicate (encode the full check in the circuit)

The circuit takes as private inputs `(token_value, signature, individual_id, …)`
and proves *inside the circuit*:

1. Signature verifies under the issuer's public key
2. Token status = ACTIVE
3. Token has permission for the requested context
4. Token is not in the RevocationList

This requires the circuit to encode:
- Signature verification (elliptic-curve operations or hash-based
  signature checks)
- Merkle-tree membership over a snapshotted token table
- Merkle-tree non-membership over a snapshotted revocation table

**Pros:** End-to-end ZK with no out-of-band trust on issuer cooperation.
**Cons:** Heavy. 100K+ R1CS constraints. Prover time 5–30 s for a
typical desktop. Requires snapshot infrastructure (Merkle commitments
of the token table at known epochs).
**Schema impact:** Adds `TokenStateMerkleSnapshot` table (per-epoch
Merkle root over active tokens) + `RevocationMerkleSnapshot` table.
**Substrate impact:** Heavy circuit library + circuit compiler.

### B2. Validity-tuple commitment (issuer pre-signs)

The issuer pre-signs a tuple `(token_id_hash, valid_until,
allowed_contexts)` per token; the SNARK proves "I hold a tuple
signed by the issuer for `context=C`." The circuit only verifies
the signature.

**Pros:** Small circuit (just signature verification). Fast prover.
**Cons:** Requires issuer to pre-compute and store these tuples;
they're a parallel state alongside `IdentityToken`. The revocation
path requires invalidating the tuple, which is a new mechanism.
**Schema impact:** Adds `TokenValidityTuple` table + a procedure to
generate tuples at issuance/revocation time.
**Substrate impact:** Lighter circuit library.

### B3. Hybrid: Merkle-state commitment + R10-2 reuse

The issuer publishes a Merkle root over the active token set per
epoch (reusing R10-2 `AnchorBatch` infrastructure). The SNARK proves
"my token is committed in this Merkle root, and the commitment encodes
context-permission and validity."

**Pros:** Reuses R10-2 infrastructure — minimal new substrate. The
schema already has `AnchorBatch` and a Merkle helper.
**Cons:** Per-epoch refresh required (when tokens are added, revoked,
or context permissions change, the epoch's Merkle root is stale).
The SNARK proves *historical* validity at the epoch boundary, not
*current* validity. Verifiers must accept some staleness.
**Schema impact:** `AnchorBatch` extended (or new `TokenStateBatch`
table that mirrors `AnchorBatch`'s structure).
**Substrate impact:** Lightest — reuses Merkle infrastructure.

### Comparison

| Axis B entry | Circuit complexity | Trust on issuer | Schema impact | Reuses R10-2 |
|---|---|---|---|---|
| B1 Predicate | very high | none | new Merkle tables | partially |
| B2 Validity-tuple | low | pre-signed tuples | new tuple table | no |
| B3 Hybrid | medium | epoch-bounded staleness | extend AnchorBatch | **yes** |

The Architect notes — but does **not** recommend — that B3 has the
lowest marginal substrate cost because it reuses R10-2. B2 is the
classical "trusted issuer" posture and may be the right pragmatic
choice. B1 is the gold standard but is genuinely heavy. **VANTA picks.**

---

## Axis C — Trusted-setup posture

Three honesty-postures the operator can adopt. This axis interacts
with Axis A but is conceptually separate (the SNARK choice may foreclose
some options; e.g., A3 Halo2 / A4 Plonky2 are NO-trusted-setup by
construction, foreclosing C1).

### C1. Dev-artifact ceremony (single-party, honestly named)

For A1 Groth16 or A2 PLONK with a custom setup. We run the ceremony
on a single development machine, document the process, and **name it
explicitly as a dev artifact** in `DEVNOTES/snark-ceremony.md`. Any
production deployment must redo the ceremony with proper participant
diversity (multi-party computation with public verification).

**Pros:** Allowed by PDF acceptance ("documented even if performed
only as a dev artifact"). Lowest operational complexity for v8.
**Cons:** A future production deployment requires its own ceremony.
The dev artifact's toxic waste (the trapdoor values that must be
deleted after the ceremony) is single-party — if the dev machine
ever leaks the values, every proof generated under this setup is
forgeable. We accept this risk explicitly.

### C2. Universal/community setup (Powers of Tau)

For A2 PLONK. We use the public Perpetual Powers of Tau ceremony
output, which is community-verified and reusable. Polaris does not
run its own ceremony; we just bind to a published one.

**Pros:** Externalizes trust to the community ceremony (which is
publicly verifiable). No single-party trapdoor concern.
**Cons:** Brings an external dependency: the Powers of Tau output
file (≥30 GB for high-capacity setups). Trusts that the community
ceremony was honest (at least one participant deleted their share).
**Substrate impact:** Adds an external dependency to the substrate
manifest.

### C3. Transparent (no setup)

For A3 Halo2 or A4 Plonky2. By construction, no ceremony exists.

**Pros:** Most honest — no trust assumption beyond the cryptographic
primitive itself. Aligns with the audit-of-record principle's spirit
("the artifact is the audit; no parallel ceremony needed").
**Cons:** Larger proofs and slower verifiers (Axis A trade-off).
**Substrate impact:** Lowest — no ceremony artifact to manage.

### Comparison

| Axis C entry | Trust model | Operational complexity | Honesty grade |
|---|---|---|---|
| C1 Dev-artifact ceremony | single-party (dev) | low | acceptable only if documented |
| C2 Universal community setup | community-verified | medium | strong |
| C3 Transparent (no setup) | none | none | strongest |

The Architect notes — but does **not** recommend — that C3 is the
most honest posture but requires accepting Axis A's A3 or A4
trade-offs. C1 is acceptable for a reference impl IF the dev-artifact
status is named explicitly. C2 is the diplomatic middle. **VANTA picks.**

---

## Compatibility matrix (Axis A × Axis C)

Some combinations are foreclosed by construction. Some are
diplomatic. None is unambiguously dominant.

| A × C | C1 dev-artifact | C2 universal | C3 transparent |
|---|---|---|---|
| A1 Groth16 | ✓ (default) | × | × |
| A2 PLONK | ✓ (custom) | ✓ (preferred) | × |
| A3 Halo2 | × | × | ✓ (default) |
| A4 Plonky2 | × | × | ✓ (default) |

Conclusion: VANTA's pick on Axis C heavily constrains Axis A (or vice
versa). The Architect recommends VANTA pick **Axis C first**, then
choose the Axis A entry compatible with it.

---

## Axis B is independent

Circuit design (B1 / B2 / B3) is largely orthogonal to A and C — any
SNARK family supports any circuit shape, though the circuit's R1CS
constraint count interacts with prover time. VANTA can pick B
independently.

---

## What changes in Polaris if M2-1 ships

Regardless of which combination is picked, the following are common:

1. **VerificationEvent.proof_commitment becomes load-bearing.** Today
   it's an optional string hash; after M2-1 it's a real ZK proof
   blob. Schema migration: column type change to BYTEA, length grows
   from 64 chars to 200B–10KB depending on Axis A pick.

2. **A new verification path in `verifications_new` Flask route.**
   Today the disclosure-consistency CHECK gates ZK events. After
   M2-1, a SUCCESS outcome on a ZERO_KNOWLEDGE event must invoke a
   verifier — call out to the SNARK library, get verify=true|false,
   reject SUCCESS if false.

3. **New DEVNOTES file:** `DEVNOTES/snark.md` covering circuit design,
   library choice, ceremony posture, performance budget. Companion to
   `DEVNOTES/anchoring.md` and `DEVNOTES/federation.md`.

4. **Substrate manifest update:** `SystemDependency` view gains 1–3
   new rows (SNARK library; ceremony artifact if C1/C2; circuit
   compiler if applicable).

5. **MISSION M2-1 ✅; Substrate-D arc closed 5/5; ROADMAP R10-1 ✅;
   CHANGELOG v8.23 entry.**

The acceptance criterion the PDF names (honest prover passes; malicious
prover fails; replay attempts fail; circuit-witness-leak attempts fail)
becomes the test plan. Substantially more cryptographic adversary
testing than any prior R-* item.

---

## Open questions for VANTA

These do not all need answers — picking a direction on each axis is
sufficient. Listed for thoroughness.

1. **Axis A choice?** Or rank-order if you're flexible.
2. **Axis B choice?** Predicate / validity-tuple / hybrid.
3. **Axis C choice?** Dev-artifact / universal / transparent.
4. **Performance budget:** is a 100ms verifier acceptable for the
   verifications_new Flask route? If not, A1 (Groth16) becomes mandatory.
5. **Production-deployment intention:** is Polaris envisioned as ever
   running in production, or is it permanently a reference impl? This
   affects whether C1 dev-artifact is acceptable.
6. **PQ alignment priority:** is post-quantum SNARK alignment (A4
   Plonky2) a hard requirement, a strong preference, or "would be
   nice"?
7. **Substrate-weight tolerance:** how much new dependency are we
   willing to add to `DEVNOTES/substrate.md`? A heavy Rust toolchain
   pull-in is the largest substrate addition since v6.

---

## What this Sanctum does NOT do

- Does not write code. No schema changes, no procedures, no Flask
  routes are touched in this round.
- Does not pick a SNARK. The proposal surveys; VANTA picks.
- Does not commit to a ship timeline. M2-1 effort is scoped after the
  design is narrowed.
- Does not foreclose alternatives. If VANTA wants to defer M2-1
  entirely in favor of M2-10 duress codes or R8-4 PostGIS, that's
  also a valid outcome of this Sanctum.

---

## What this Sanctum DOES do

- Narrows the M2-1 design space from "12+ orthogonal candidate
  combinations" to "one combination VANTA picked from the
  compatibility matrix."
- Establishes the audit-then-Sanctum pattern's *exploration variant*:
  when a design space is too wide for a single ship-Sanctum to be
  honest, the first Sanctum surveys and the second Sanctum ships.
- Names the dev-artifact-vs-production-ceremony honesty axis
  explicitly, so the operator's posture is recorded, not implied.

---

## Cross-references

- `MISSION.md` M2-1 — the open item this proposal scopes.
- `ROADMAP.md` R10-1 — the corresponding R-id.
- `meta/architect.md` — the Architect persona that recommends
  alignment-exploration as the right next move.
- `sanctum/2026-05-11-r10-2-functional-did-anchoring.md` — Substrate-D
  arc leg 4, ✅ v8.21. Possible reuse target for Axis B3.
- `DEVNOTES/anchoring.md` — Merkle infrastructure that B3 would reuse.
- `DEVNOTES/substrate.md` — substrate manifest; M2-1 will add 1–3 rows.
