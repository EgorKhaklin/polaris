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
| S1 | **The synthetic nation (substrate).** A `polaris_sim` package + reference data (all 50 states + DC + territories with real populations), a deterministic generator of jurisdictions / ID bureaus (agencies, count per state scaled by population) / individuals at a `scale` factor, loaded through the bulk pipeline. A `polaris-sim build` entry point. First benchmark point: substrate generate + load throughput. | next |
| S2 | **The life-event stream.** A generator of realistic verification and token-lifecycle event streams over a simulated clock (accelerated or real-time), fed through the real single-event procedures. Contextual + temporal realism (business hours, context mix, lifecycle rates). `polaris-sim run --duration --rate`. | planned |
| S3 | **The benchmark harness + report.** Orchestrate a run at a target scale/rate; capture throughput, latency percentiles per operation, DB contention + index stats, Atlas aggregate query times at scale, and C1-C10 behavior under load; emit a reproducible benchmark report artifact (the "gather information to harden" deliverable). Realizes and supersedes the roadmap's P2.9 load-cert. | planned |
| S4 | **Atlas simulation mode.** A live view in the Atlas that shows the simulation as it happens: the Regions/Density map lighting up across states, the volume series climbing, the breakdown shifting in real time. Connects the simulator to the operator surface VANTA asked for ("a test simulation mode for atlas and polaris"). | planned |
| S5+ | **The hardening loop.** Each benchmark finding (a slow query, a hot lock, a missing index, a cap set too low, a contention point) becomes a focused hardening ship, re-benchmarked to prove the improvement. Open-ended: the simulation is a permanent instrument, not a one-off. | planned |

The order after S1 is adjustable. Every ship holds the bar above; none fabricates
numbers, hides a scale factor, or writes around the real procedures.
