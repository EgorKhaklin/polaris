# National Simulation and Benchmark (the living-nation test harness)

The sub-roadmap for a full national-scale simulation of Polaris: a synthetic
United States, ID bureaus in every state, and life events streaming through the
**real** system in (optionally real) time, so the system can be exercised,
benchmarked, and hardened at a scale no unit test reaches. Direction from VANTA
(2026-09-06): "simulate the life of all of the USA ... ID bureaus in all states
... things happening everywhere on a USA scale ... in real time ... fully
simulated to test the system. Use these tests to gather information to harden
the system even further, like a benchmark." One ship per version, tracked here.

## What it is

A seeded, deterministic generator of a synthetic nation and its daily life,
driven through the **actual** Polaris procedures, constraints, zero-knowledge
path, and Atlas aggregates. Not mocks. If the simulation issues a token, it goes
through `uc1_issue` and the full constraint set; if it records a verification,
the row is written and the Atlas counts it exactly as a real one. The point is
to learn where the real system bends and to harden it there.

## Principles (the bar)

- **Deterministic and seeded.** A seed fixes the nation and the event stream, so
  a run is reproducible and two runs are comparable. Required for a benchmark.
- **Scaled by a factor, honest about it.** The USA is ~335M people; a laptop
  holds a downscale. A `scale` factor (e.g. 1:100000 for dev, up toward 1:1 for
  a benchmark host) sets the size, and every report states the factor and the
  hardware. Never imply full scale from a downscaled run.
- **Realistic distributions.** Population by state (real Census figures), ID
  bureaus per state scaled by population, event mix by context (banking,
  travel, healthcare, ...), temporal rhythm (business hours, weekly cycle),
  and lifecycle rates (issuance, renewal, revocation, loss, death and erasure).
- **Through the real system.** The substrate loads via the bulk-enrollment
  pipeline (P2.4: COPY + `uc_bulk_issue`); the live stream drives the
  single-event procedures. No table is written behind the procedures' backs.
- **Measured, then hardened.** Every run captures throughput, latency
  percentiles, contention, index effectiveness, Atlas query time at scale, and
  whether C1-C10 hold under load. Findings become targeted hardening ships,
  each re-benchmarked to prove the gain.
- **Notional and isolated.** Notional data only, like all of Polaris. The
  simulation runs against a dedicated/expendable database and is gated so it can
  never be pointed at anything real. C10 (identity is not money) and the rest
  hold under simulation exactly as always.

## The arc

| Ship | Scope | Status |
|---|---|---|
| S1 | **The synthetic nation (substrate).** A `polaris_sim` package + reference data (all 50 states + DC + territories with real populations), a deterministic generator of jurisdictions / ID bureaus (agencies, count per state scaled by population) / individuals at a `scale` factor, loaded through the bulk pipeline. A `polaris-sim build` entry point. First benchmark point: substrate generate + load throughput. | done |
| S2 | **The life-event stream.** `polaris_sim/events.py`: a generator of realistic verification (through the app's real `INSERT INTO VerificationEvent` path, C6-correct so a zero-knowledge event carries no token or location, disclosing events placed near their holder's state) and token-lifecycle streams (revocations through the real `uc8_revoke_token`, which enforces its rate bound, co-signer, and algorithm authorization). `python3 -m polaris_sim run --events N --lifecycle K --window H`. Sustained ~20k verification EVENTS/s ingested (audit writes, not signature checks; distinguished from cryptographic verification in v9.257); the events light up the existing Atlas. | done |
| S3 | **The benchmark harness + report.** `polaris_sim/benchmark.py` runs the build + stream as timed phases and measures single-write latency percentiles, each bounded Atlas aggregate's time over the loaded set, and whether C3/C6/C1 hold under load (it exits non-zero if any broke). `python3 -m polaris_sim benchmark`. The committed report is [docs/reference/BENCHMARK.md](../docs/reference/BENCHMARK.md); the certified run distinguishes enrollment, verification-EVENT ingestion (~20-26k/s), and real cryptographic ML-DSA-65 verification (~743/s), with invariants holding (see v9.257). It found the scan-based Atlas roll-ups (0.4-1.1s at 1M) as the first hardening lead. Realizes the single-node half of the roadmap's P2.9; the HA-topology-under-load + failover run remains. | done |
| S4 | **Atlas simulation mode (v9.261).** A live control in the Atlas: an operator clicks *Simulate* and watches notional national activity stream in — the volume series climbing, the breakdown shifting, the map lighting up. **Client-driven** (each tick POSTs a bounded batch to `/api/sim/tick`, which writes through the same `polaris_sim` path the benchmark uses, then the console refreshes), so it needs no server-side background thread — correct for the multi-worker gunicorn model. **Triple-gated** out of production: `SIM_MODE` is force-off under `POLARIS_ENV=production`, the route 404s when off, and `polaris_sim.assert_expendable()` refuses production on the writer (the hard isolation gate the harness was missing). Append-only (C1): sim events cannot be deleted, so it runs on an expendable database. | done |
| S5+ | **The hardening loop.** Each benchmark finding (a slow query, a hot lock, a missing index, a cap set too low, a contention point) becomes a focused hardening ship, re-benchmarked to prove the improvement. Open-ended: the simulation is a permanent instrument, not a one-off. **#1 (v9.260): Atlas roll-ups prune the partitioned event table.** The benchmark's first lead was the scan-based roll-ups; the deeper cause was that `p_since IS NULL OR event_timestamp >= p_since` (and a params-CTE indirection) defeated partition pruning under the generic plan the app runs, so a windowed query scanned every month of history. Fixed to `event_timestamp >= COALESCE(p_since, '-infinity')`; the benchmark now measures partitions-scanned (recent window vs all-time) and fails if pruning regresses, `check_atlas_rollups_prune` forbids the bad shapes, and `AtlasPartitionPruningTests` proves it under a forced generic plan. | in progress |

The order after S1 is adjustable. Every ship holds the bar above; none fabricates
numbers, hides a scale factor, or writes around the real procedures.
