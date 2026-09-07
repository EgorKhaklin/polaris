# Benchmark and load certification

This is the committed record of Polaris driven at scale by the national
simulation harness (`polaris_sim`, roadmap P2.14). The numbers were produced by
running the real system, not asserted. The harness builds a synthetic nation,
streams a day of national life-events through the real procedures and write
paths, then measures throughput, latency, the Atlas aggregates over the loaded
data, and whether the invariants still hold, including that mass-issued tokens
actually verify.

Reproduce it:

```bash
POLARIS_USE_REAL_PQC=1 POLARIS_CUSTODY_DRIVER=file POLARIS_PQC_SIGNING_KEY_FILE=<key.json> \
  python3 -m polaris_sim benchmark --scale 10000 --events 200000 --verify-samples 2000 --seed 42
```

`--scale` is a downscale divisor (synthetic people is about the US population
divided by it). Every run states its scale factor and host; a downscaled run
never implies full national scale.

## Three numbers that must not be conflated

A benchmark of an identity system has to separate what it is actually measuring,
because the honest numbers are an order of magnitude apart:

1. **Verification-EVENT ingestion** is how fast the system records verification
   audit rows. It is a database write. It does NOT verify a signature.
2. **Cryptographic signature verification** is how fast the system actually
   verifies a token's ML-DSA-65 signature against its stored public key. This is
   the real cryptographic throughput.
3. **Enrollment (issue + sign)** is how fast tokens are minted, and under real
   post-quantum signing it is signing-bound.

Earlier phrasing that called event ingestion "verifications/s" overstated the
cryptographic claim; these are now measured and reported as three distinct
numbers.

## Method

- **Enrollment** goes through the real bulk pipeline (`uc_bulk_issue`), and every
  token_value is SIGNED through the same `pqc_signing` path single issuance uses
  (real ML-DSA-65 under `POLARIS_USE_REAL_PQC=1`, a deterministic verifiable
  sha3-256 placeholder otherwise). Bulk issuance refuses an unsigned row, so a
  mass-issued token can never carry a placeholder literal.
- **Verification events** are written by the same direct `INSERT INTO
  VerificationEvent` the application's verification route uses (a zero-knowledge
  event carries no token and no location, C6). Recording a verification event is
  not a signature check, in the app or here.
- **Cryptographic verification** samples issued tokens and verifies each stored
  signature with `pqc_signing.verify_stored_signature` (two independent
  witnesses under real PQC), timing each and asserting they all verify.
- **The Atlas at scale** is each bounded aggregate executed fully over the events.
- **Invariants under load** are checked after the load: C3, C6, the C1
  append-only boundary, and that the mass-issued signatures verify.

## Certified run (real ML-DSA-65)

Scale 1:10000, 200,000 verification events, 2,000 signatures verified, seed 42,
`POLARIS_USE_REAL_PQC=1` with a file-custody ML-DSA-65 authority key, on a
development host (single node, notional data). Single-node numbers; a
measurement instrument, not a production SLO.

| Dimension | Result |
|---|---|
| Substrate | 33,117 people, 465 ID bureaus, 51 jurisdictions |
| Enrollment (issue + real ML-DSA-65 sign) | ~372 tokens/s (signing-bound) |
| Verification-EVENT ingestion (audit writes, NOT signature checks) | ~25,970 events/s |
| **Cryptographic signature verification (ML-DSA-65)** | **~743 verifications/s** (2,000/2,000 verified, p95 1.37 ms) |
| Single event write latency | p50 0.14 ms, p95 0.19 ms, p99 0.23 ms (n=500) |
| Event set measured | 200,010 verification events |

**Atlas aggregate query time over 200,010 events:**

| Aggregate | Time |
|---|---|
| `atlas_records` (keyset page) | 1.9 ms |
| `atlas_geo_jurisdictions` (Regions) | 71 ms |
| `atlas_breakdown` | 77 ms |
| `atlas_volume_series` | 142 ms |
| `atlas_hexbin` (Density) | 143 ms |
| `atlas_crosstab` | 163 ms |

**Invariants under load:** C3, C6, the C1 append-only boundary, and
`signatures_cryptographically_verify` (every sampled mass-issued token verified)
all held.

With the deterministic-placeholder signature (`POLARIS_USE_REAL_PQC` unset, the
dev/CI default) enrollment is far faster (thousands/s) because there is no real
signing; that mode measures the event machinery, not cryptography, and is
labeled as such.

## Findings (the hardening leads)

1. **Event ingestion is not cryptographic verification.** ~26,000 audit-row
   writes/s versus ~743 real ML-DSA-65 verifications/s is a ~35x gap. A claim
   about "verification throughput" has to say which one it means; national
   cryptographic verification at rate is a real-signing, likely multi-core or
   batched-verify problem, not a database-write problem.
2. **Real signing dominates enrollment.** At ~0.4 ms per ML-DSA-65 signature
   plus a two-witness self-check, mass enrollment is signing-bound (~372/s
   single-threaded here). Parallel signing across custody workers is the lever.
3. **The scan-based Atlas roll-ups remain the read-side scaling front** (they
   grow with the event count while the keyset `atlas_records` stays flat), the
   first candidate for a materialized rollup or covering index.

## Relation to P2.9

This is the single-node load certification the roadmap's P2.9 calls for: the
published harness drives the planning targets and commits the numbers, including
that mass-issued identities are cryptographically valid. The remaining P2.9
integration is to run the same harness against the HA topology during a rolling
deploy and one induced failover.
