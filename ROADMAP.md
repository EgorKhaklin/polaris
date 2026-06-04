# ROADMAP.md — where Polaris is going

The forward backlog. Shipped history lives in [`CHANGELOG.md`](CHANGELOG.md), not
here. Tagging: `effort(XS/S/M/L) · value · risk · category`. The live invariant
layer is [`polaris_checks/`](polaris_checks/), which gates CI via
`python3 -m polaris_checks.run`.

---

## Flagged for the maintainer (decision required)

- **[VANTA] THESIS v9.40 terminus has passed unactioned.** `MISSION.md` says the
  strong "agent-maintainable production identity system" claim *retires permanently*
  if no external cold-read occurs by v9.40. We are past v9.40 with only the system's
  own walkthrough, never an external one, yet `docs/THESIS.md` still uses the softer
  conditional "RETIRED *until* evidence supports it." Leaving the softer wording past
  the deadline is itself the dishonesty the project's discipline forbids. Two honest
  moves, both VANTA's call: (a) reflect the permanent terminus ("has not been
  independently validated") and pin it with a check, or (b) amend the deadline through
  an explicit, recorded decision. `S · high · MEDIUM · cold-read-evidence`

---

## Next ships

1. **PQC second witness.** Issuance is wired through
   `pqc_signing.signature_bytes_for_token` (v9.58) and the real ML-DSA-65 path is one
   flag away (`POLARIS_USE_REAL_PQC=1`). Still open: a full independent ML-DSA-65
   second witness for the verify path, premature while real PQC is OFF by default;
   revisit when it goes live. `L · medium · MEDIUM · hardening`
2. **PQC-posture audit** — audit Polaris against NIST PQC migration timelines;
   surface gaps. `S · low · LOW · cold-read-evidence`

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
