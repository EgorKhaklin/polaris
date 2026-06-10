# ROADMAP.md — where Polaris is going

The forward backlog. Shipped history lives in [`CHANGELOG.md`](CHANGELOG.md), not
here. Tagging: `effort(XS/S/M/L) · value · risk · category`. The live invariant
layer is [`polaris_checks/`](polaris_checks/), which gates CI via
`python3 -m polaris_checks.run`.

**Production-readiness:** the path from reference implementation to a system that
can run real identity data is tracked honestly in
[`docs/PRODUCTION-READINESS.md`](docs/PRODUCTION-READINESS.md) — what is already
production-grade, the engineering waves, and the operator/legal decisions that are
not an agent's to make. Wave 1 shipped in v9.101.

---

## Flagged for the maintainer (decision required)

- _(resolved v9.91)_ **THESIS v9.40 terminus.** Move (a) was taken: it is the
  constitution's own mechanical outcome (past v9.40, no external cold read →
  retired permanently), not a discretionary choice, so it needed no new maintainer
  authority to action. `docs/THESIS.md` now reads INCONCLUSIVE with the strong
  claim retired, the v9.40 terminus stated, and `check_thesis_terminus_honest`
  pinning it against drift. Move (b) — amending the deadline through a recorded
  decision to reopen — remains genuinely VANTA's, if you ever want it: that one
  does require maintainer authority, and the docs now say so.

---

## Next ships

(Backlog is operator-gated from here. The next agent-buildable ship is a new
feature or a maintainer-green-lit gated item; see the migration roadmap in
[`docs/reference/PQC-POSTURE.md`](docs/reference/PQC-POSTURE.md) for the
third-party-gated PQC items. The client-to-edge hybrid TLS KEX shipped in
v9.136; the still-open gated items are the internal-hop hybrid KEX (app to
pgbouncer, pgbouncer to postgres), gated on OpenSSL 3.5 reaching those
images.)

---

## Deferred — production-scale, gated

These open at real production scale and are premature before then.

- **Multi-instance scaling** — read-replica routing via Caddy/HAProxy, Redis Sentinel
  or Cluster topology, and the PostGIS Phase-2 atlas rewrite (`atlas_clusters_*` /
  `atlas_points_*` gain a `CASE` branch on `pg_extension` presence; ≥3× benchmark at
  10M+ events). `L · medium · MEDIUM · scaling`
- **Multi-region deployment** — read-replicas across regions, failover orchestration,
  per-jurisdiction data locality. Gated on an operator naming a real data-locality
  constraint. `L · medium · HIGH · scaling`
- **Distributed tracing** — OpenTelemetry across services. Gated on multi-instance:
  there is no second hop to trace until the distributed stack exists. `M · low · LOW · ops`

---

## Out of scope

Explicitly passed and not on the backlog (retired in `MISSION.md`'s v1 done-list,
items 13-15):

- **External IdP / OIDC integration** — out of the reference-implementation scope.
- **Banking-on-Polaris reference architecture** — the correct shape is a separate
  repo that consumes Polaris over HTTP, not a feature merged in (C10 keeps identity
  and money in different databases).
- **Linux / Windows launcher variants** — the macOS launcher is the deliverable
  surface; cross-platform packaging is an operational concern, not a mission item.

---

## How this file works

This is the forward roadmap, not a ship log. When work ships, it moves to the
`CHANGELOG.md` and out of here. Add new ideas under **Next ships** as they arise;
promote a flagged item once the maintainer decides.
