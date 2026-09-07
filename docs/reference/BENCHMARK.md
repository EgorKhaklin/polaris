# Benchmark and load certification

This is the committed record of Polaris driven at scale by the national
simulation harness (`polaris_sim`, roadmap P2.14). The numbers below were
produced by running the real system, not asserted. The harness builds a
synthetic nation, streams a day of national life-events through the real
procedures and write paths, then measures throughput, single-write latency, the
Atlas aggregates over the loaded data, and whether the invariants still hold.

Reproduce it:

```bash
python3 -m polaris_sim benchmark --scale 1000 --events 1000000 --lifecycle 300 --seed 42
```

`--scale` is a downscale divisor (synthetic people is about the US population
divided by it). Every run states its scale factor and host; a downscaled run
never implies full national scale.

## Method

- **Enrollment** goes through the real bulk pipeline (`uc_bulk_issue`): every
  synthetic person passes the full constraint set a real enrollee does.
- **Verifications** are written by the same direct `INSERT INTO
  VerificationEvent` the application's verification route uses, via `COPY`; a
  zero-knowledge event carries no token and no location (C6).
- **Latency** is the wall time of a single verification write (`INSERT`),
  sampled and rolled back, so it does not skew the throughput counts. This is
  the database write, a lower bound on the full server-side path (which also
  runs auth, disclosure enforcement, and the duress check); the full HTTP
  round-trip is measured separately by `scripts/polaris_load_gen.py`.
- **The Atlas at scale** is each bounded aggregate executed fully over the
  loaded event set.
- **Invariants under load** are checked after the load: C3 (one active token per
  person), C6 (no zero-knowledge verification is located), and the C1
  append-only boundary (an `UPDATE` on the verification audit table is refused).

## Certified run

Scale 1:1000 (a state-sized slice of the nation), 1,000,000 verifications over a
24-hour window, seed 42, on a development host (macOS, single node, notional
data). Single-node numbers; they are a measurement instrument, not a production
SLO.

| Dimension | Result |
|---|---|
| Substrate | 331,423 people, 465 ID bureaus, 51 jurisdictions |
| Enrollment throughput | ~2,640 enrollments/s (bulk pipeline) |
| Verification throughput | ~19,800 verifications/s (COPY) |
| Verification write latency | p50 0.18 ms, p95 0.22 ms, p99 0.35 ms (n=500) |
| Event set measured | 1,000,010 verification events |
| Disclosure mix | 55% zero-knowledge, 35% selective, 10% full |

**Atlas aggregate query time over 1,000,010 events:**

| Aggregate | Time |
|---|---|
| `atlas_records` (keyset page) | 2.8 ms |
| `atlas_geo_jurisdictions` (Regions) | 408 ms |
| `atlas_breakdown` | 496 ms |
| `atlas_volume_series` | 692 ms |
| `atlas_crosstab` | 860 ms |
| `atlas_hexbin` (Density) | 1,071 ms |

**Invariants under load:** C3, C6, and the C1 append-only boundary all held.

## Findings (the hardening leads)

The point of a benchmark is what it tells you to fix next.

1. **The scan-based Atlas aggregates are the scaling front.** At a million
   events the roll-ups run 0.4 to 1.1 seconds because each scans the full event
   set. That is fine for a million and too slow for ten. The keyset-paginated
   `atlas_records` stays at 2.8 ms at the same scale, which is the proof that
   the keyset design is right and the roll-ups are the thing to harden next (a
   materialized rollup refreshed on a cadence, or a covering index per
   dimension). This is the first candidate for an S5 hardening ship.
2. **Enrollment throughput is bounded by per-bureau batching.** The substrate
   commits per bureau across 459 bureaus, so a large batch amortizes better than
   many small ones; grouping bureaus per commit is a cheap win.
3. **Writes are not the bottleneck.** A single verification write is well under
   a millisecond even at a million rows, so the append path has ample headroom;
   the read/aggregate path is where scale work belongs.

## Relation to P2.9

This is the single-node load certification the roadmap's P2.9 calls for: the
published harness drives the planning targets and commits the numbers. The
remaining P2.9 integration is to run the same harness against the HA topology
during a rolling deploy and one induced failover, which composes this harness
with the existing failover and chaos drills.
