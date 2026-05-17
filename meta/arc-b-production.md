# Arc B — Production deployment

**Status:** **Phase 1 SHIPPED 2026-05-14 (v8.77); Phase 3 Wave 1
SHIPPED 2026-05-14 (v9.01); Phase 2 + remaining Phase 3 GATED on
production-scale triggers** (per Sanctum
[`sanctum/2026-05-15-open-arcs-debate.md`](../sanctum/2026-05-15-open-arcs-debate.md)
Position C′; truth-update v9.16). The arc is *not closed* because
Phase 2 + remaining Phase 3 represent real deferred work; it is
*honest* because the deferred work is named with explicit triggers.

**Real-world triggers that would manifest the deferred phases:**
- **Phase 2** (read-replica + PostGIS scaling + Redis-cluster): production-scale data emerges (≥10× current verification volume) OR a specific scaling incident OR operator-prioritized capacity planning.
- **Phase 3** multi-region + distributed tracing: partner deployment spans ≥2 jurisdictions OR an explicit federation requirement from a real attesting agency.

**Opened by:** `sanctum/2026-05-14-arc-b-production-deployment-opening.md`
**Authorized by:** VANTA heavy-production directive recorded in
`sanctum/2026-05-14-steady-state-revocation-heavy-production.md`
**Truth-update Sanctum:** [`sanctum/2026-05-15-open-arcs-debate.md`](../sanctum/2026-05-15-open-arcs-debate.md)

## Why Arc B exists

Polaris was, before v8.77, **architecturally rich, productionally
thin**: cryptography, schema, audit-of-record, and the cognitive
substrate were all production-grade, but the *deployment story* was
the dev launcher (`polaris_mac_launch.sh`). A reference implementation
that no real operator can deploy is not actually a reference.

Arc B closes that gap. The deployment story IS the project's
reference-implementation claim; everything Arc B ships has to be
usable by someone who downloaded the repo this morning and wants
TLS, secrets management, structured monitoring, backups, and an
idempotent deploy command — without rolling their own.

## Done-list

| Phase | Deliverable | Status | Ship |
|---|---|---|---|
| 1 | `docs/operator/OPERATIONS.md` — full operator runbook | ✅ | v8.77 |
| 1 | `docs/operator/SECRETS.md` — env-var matrix + rotation cadence | ✅ | v8.77 |
| 1 | `polaris_web/docker-compose.prod.yml` — Caddy + app + Postgres + Redis | ✅ | v8.77 |
| 1 | `polaris_web/Dockerfile.prod` — multi-stage, non-root, ZK-built | ✅ | v8.77 |
| 1 | `polaris_web/Caddyfile` — TLS, security headers, rate-limit | ✅ | v8.77 |
| 1 | `/api/health` — structured JSON, per-component checks (G29) | ✅ | v8.77 |
| 1 | `scripts/polaris-deploy.sh` — idempotent deploy with rollback | ✅ | v8.77 |
| 1 | `scripts/polaris-backup.sh` — atomic backup with hash manifest | ✅ | v8.77 |
| 1 | `scripts/polaris-generate-secrets.sh` + `polaris-rotate-secret.sh` | ✅ | v8.77 |
| 1 | Structural invariants (G27 TLS, G28 no-env-secrets, G29 health) | ✅ | v8.77 |
| 1.5 | `scripts/polaris-restore.sh` — recovery-from-backup with manifest verification | ✅ | v8.81 |
| 2 | WebAuthn + hardware-token operator auth | ⬜ | (deferred) |
| 2a | `scripts/polaris-archive.sh` — audit-log export (C1-preserving) | ✅ | v8.84 |
| 2b | Audit-log deletion-from-hot (constitutional carve-out, Position B) | ✅ | v8.87 |
| 2 | Multi-instance scaling foundations (pgbouncer + WEB_CONCURRENCY + scaling recipes) | ✅ | v8.83 |
| 2.5 | Multi-instance scaling completion (read replica + Redis cluster + PostGIS) | ⬜ | (deferred) |
| 3 | Multi-region deployment patterns | ⬜ | (deferred) |
| 3 | Disaster-recovery runbook (RPO/RTO targets) | ⬜ | (deferred) |
| 3 | SOC 2 readiness checklist | ⬜ | (deferred) |

## G-guards introduced

- **G27** — Production deployment requires TLS. Caddyfile or
  equivalent reverse-proxy with TLS must be present in any
  production-targeted deploy. No HTTP-only production. Enforced
  by `test_g27_caddyfile_declares_tls`.

- **G28** — Sensitive secrets do not appear as environment-variable
  literals in production. The `docker-compose.prod.yml` references
  file-mounted secrets via `*_FILE` env vars; the app reads them
  through `_read_secret_file()` in `app.py`. Enforced by
  `test_g28_no_sensitive_env_in_prod_compose`.

- **G29** — `/api/health` returns structured JSON with overall
  status and per-component checks (database / redis / zk_binary /
  disk). Status field uses canonical values `healthy` / `degraded` /
  `unhealthy`. HTTP code follows the overall status (200 healthy or
  degraded, 503 unhealthy). Enforced by
  `test_g29_health_endpoint_contract`.

## Deploy topology (Phase 1)

```
                ┌───────────────────┐
                │  Caddy (host)     │  TLS termination
                │  :443 + auto-cert │  HSTS, security headers, rate-limit
                └────────┬──────────┘
                         │ http://app:8000
                ┌────────▼──────────┐
                │  Polaris app      │  multi-stage Dockerfile.prod
                │  gunicorn         │  non-root, minimal surface
                └────────┬──────────┘
                         │
              ┌──────────┼──────────┐
              │          │          │
        ┌─────▼────┐ ┌──▼──────┐ ┌─▼──────────┐
        │ postgres │ │ redis   │ │ zk-binary  │
        │ :5432    │ │ :6379   │ │ subprocess │
        └──────────┘ └─────────┘ └────────────┘
```

## Quality bar

VANTA's standing directive: *"the marginal cost of completeness is
near zero with AI. Do the whole thing. Do it right. Do it with
tests. Do it with documentation."* Phase 1 ships:

- **Complete:** every piece needed to bring up TLS-terminated,
  secret-isolated, monitored, backed-up production from a fresh
  host
- **Right:** non-root containers, file-mounted secrets, structured
  health, idempotent deploy, manifest-verified backups
- **With tests:** 8 new structural invariants (G27 TLS, G28
  no-env-secrets, G29 health contract, non-root, security headers,
  scripts-executable, secrets-gitignored, stack-files-present)
- **With documentation:** [`docs/operator/OPERATIONS.md`](../docs/operator/OPERATIONS.md)
  (~700 lines) + [`docs/operator/SECRETS.md`](../docs/operator/SECRETS.md)
  (~400 lines), in addition to this strategic record

## What Phase 1 does NOT do

- Run the production deploy. The agent's job ends at "complete and
  shippable"; the actual `./scripts/polaris-deploy.sh prod` is
  VANTA's operator-driven step, on VANTA's terms.
- Bundle hardware-token integration. WebAuthn + YubiKey is Phase 2
  scope.
- Provide multi-region or DR runbooks. Those are Phase 3.

## How Phase 2 opens

Phase 2 requires either:
1. VANTA directive after Phase 1 has soaked in real operation, OR
2. Architect-surfaced gap from running Phase 1 production for some
   time (e.g., audit-log volume forces archive policy)

Either case opens with a fresh Sanctum that references this file
as the prior commitment. Per the v8.30 substitutability principle,
nothing in Phase 1 is constitutionally locked — the entire stack
is implementation; the principle "Polaris is deployable in
production" is what stands.

## Cross-references

- Opening Sanctum: `sanctum/2026-05-14-arc-b-production-deployment-opening.md`
- Posture-shift Sanctum: `sanctum/2026-05-14-steady-state-revocation-heavy-production.md`
- Operator runbook: `docs/operator/OPERATIONS.md`
- Secrets primer: `docs/operator/SECRETS.md`
- Authorizing principle: MISSION.md §"The cognitive substrate (the agent contract)"
  (Sanctum + AoR + risk classes + CM) — substitutability preserved
