# Sanctum: arc-b-production-deployment-opening

**Date:** 2026-05-14
**Petitioner:** agent (Claude, Opus 4.7) speaking as the Architect
**Principal:** VANTA
**Trigger:** Architect's macro scan (2026-05-14, post-v8.76) identified production-deployment as the highest-leverage gap. The first v8.31 trigger condition (*Arc B prod-deploy*) fires explicitly here. Authorized by VANTA's heavy-production directive recorded in `sanctum/2026-05-14-steady-state-revocation-heavy-production.md`.
**Risk class:** HIGH (opens new arc; introduces production-deployment surface; multi-day scope; touches Docker + secrets + TLS + monitoring; the deployment story IS the project's reference-implementation claim)
**Status:** DECIDED
**Architect brief ID:** arch-2026-05-14-arch-001

---

## I. The Matter

Polaris is **architecturally rich, productionally thin**. The macro scan found:

- Cryptography: production-grade (ML-DSA, ZK-SNARK, multi-sig migration)
- Schema: production-grade (25 tables, 13 procedures, 41 CHECK constraints, 11 audit-of-record instances)
- Cognitive layer: more developed than the identity system it watches (33 ants, 9 watchers, 6 citizens)
- **Deployment story: dev launcher only** (`polaris_mac_launch.sh` for local Docker)

A reference implementation that no real user can deploy is not actually a reference. Arc B closes this gap.

## II. Phase 1 scope (this ship — v8.77)

10 deliverables, all complete-and-shippable in one ship per the standing instructions ("Do the whole thing. Do it right. Do it with tests. Do it with documentation"):

1. **`docs/operator/OPERATIONS.md`** — full operator runbook: install, configure, deploy, backup, restore, rotate secrets, scale, incident response, common errors. Target: production-deployable from this doc alone.
2. **`docs/operator/SECRETS.md`** — env-var matrix; secret rotation cadence; leak prevention; generation recipes for `POLARIS_SECRET_KEY`, `POLARIS_DB_PASSWORD`, etc.
3. **`polaris_web/docker-compose.prod.yml`** — production stack: Polaris app + Postgres + Redis + Caddy reverse proxy (TLS) + log volumes + healthchecks + restart policies + secrets via files
4. **`polaris_web/Dockerfile.prod`** — multi-stage build: builder + runtime; non-root user; minimal Alpine/Debian-slim base; no dev tools
5. **`polaris_web/Caddyfile`** — TLS automation (Let's Encrypt) + security headers + rate-limiting + reverse-proxy to gunicorn
6. **`/api/health` enhancement** — currently exists at `polaris_web/app.py`; expand to structured JSON with per-component status (db / redis / zk-binary / disk space / app version + uptime). Replace minimal "ok" string with actionable status.
7. **`scripts/polaris-deploy.sh`** — idempotent deploy: pull → build → migrate → smoke-test → swap → rollback-on-fail. Three modes: `dev`, `staging`, `prod`.
8. **`scripts/polaris-backup.sh`** — pg_dump + treasury-roll.json + census-roll.json + sanctum/ + journal/ tar with timestamp; verifies extraction
9. **`meta/arc-b-production.md`** — strategic record of Arc B (opening, phases, done-list)
10. **Structural-invariants** — verify the deploy stack files exist; verify Dockerfile.prod uses non-root; verify Caddyfile declares TLS; verify health endpoint returns structured JSON

## III. Design

### Deploy topology

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
              │          │
        ┌─────▼──────────▼─────┐
        │  Volumes (host)      │
        │  - pg_data           │
        │  - redis_data        │
        │  - logs              │
        │  - secrets/          │
        │  - sanctum/ + journal/  (mounted from host audit-of-record)
        └──────────────────────┘
```

### Secrets handling

Three tiers:

1. **Build-time:** none (Dockerfile.prod has no secrets baked)
2. **Runtime:** Docker secrets (file-mounted at `/run/secrets/`) for sensitive keys; env-vars for non-sensitive config
3. **Operator:** `secrets/` directory on host, gitignored, file-permissioned 0600

Files:
- `secrets/polaris_secret_key` — Flask session key
- `secrets/polaris_db_password` — Postgres app-user password
- `secrets/polaris_db_root_password` — Postgres superuser password (only for migrations)
- `secrets/redis_password` — Redis AUTH (currently unused; optional)

The launcher's existing rotation logic (v8.56 / v8.58) is reused for secret regeneration.

### Health endpoint contract

`GET /api/health` returns:

```json
{
  "status": "healthy" | "degraded" | "unhealthy",
  "version": "8.77",
  "uptime_seconds": 3600,
  "checks": {
    "database": {"status": "healthy", "latency_ms": 4, "table_count": 25},
    "redis":    {"status": "healthy", "latency_ms": 1},
    "zk_binary": {"status": "healthy", "path": "/opt/polaris/zk", "version": "0.2.0"},
    "disk":     {"status": "healthy", "free_gb": 42.7, "used_pct": 23.1}
  },
  "timestamp": "2026-05-14T12:34:56.789Z"
}
```

HTTP status code follows the overall status (200 healthy, 200 degraded, 503 unhealthy).

### TLS + Caddy

Caddyfile uses Caddy's automatic Let's Encrypt:

```caddy
{$POLARIS_DOMAIN} {
    reverse_proxy app:8000
    encode gzip zstd
    header {
        Strict-Transport-Security "max-age=63072000; includeSubDomains; preload"
        X-Content-Type-Options "nosniff"
        X-Frame-Options "DENY"
        Referrer-Policy "strict-origin-when-cross-origin"
        Permissions-Policy "geolocation=(), microphone=(), camera=()"
    }
    rate_limit {
        zone polaris_global {
            key {client.ip}
            events 200
            window 1m
        }
    }
}
```

Operator sets `POLARIS_DOMAIN=polaris.example.com` and Caddy auto-provisions TLS.

### Backup/restore semantics

`polaris-backup.sh` produces a single tar.gz containing:
- `pg_dump` of the database (custom format, gzipped)
- `treasury-roll.json` snapshot
- `census-roll.json` snapshot
- `sanctum/` directory (full)
- `journal/` directory (full)
- `meta/sanctum-index.md` (computed)
- Manifest with timestamps + hashes

`polaris-restore.sh` (Phase 1.5; deferred): extracts + validates + restores.

### G-guards added

- **G27** — Production deployment requires TLS. Caddyfile or equivalent reverse-proxy with TLS must be present in any production-targeted deploy. No HTTP-only production. Enforced structurally by `test_caddyfile_tls_declared`.
- **G28** — Secrets do not appear in environment variables for production. The Dockerfile.prod + docker-compose.prod.yml use Docker secrets (file-mounted) for sensitive values. Enforced by source-scan test that production compose file does not have `POLARIS_SECRET_KEY:` env-var literal.
- **G29** — `/api/health` returns structured JSON with `status` field in {`healthy`, `degraded`, `unhealthy`}. Enforced by app-layer test.

## IV. Recommendation

**Ship Phase 1 today as v8.77.** All 10 deliverables in one ship; complete; tested; documented. Per VANTA's standing instructions, "the answer is the finished product, not a plan to build it."

Phase 2 (deferred to a separate Sanctum, future-day):
- Hardware-token integration (WebAuthn + YubiKey ML-DSA)
- Audit-log archive policy (S3 / cold storage rotation)
- Multi-instance scaling (gunicorn worker tuning + Postgres connection pool)
- `polaris-restore.sh` (recovery-from-backup with validation)

Phase 3 (deferred):
- Multi-region deployment patterns
- Disaster recovery runbook (RPO/RTO targets)
- Compliance posture (SOC 2 readiness checklist)

## V. Alternatives considered

1. **Ship just OPERATIONS.md today; defer the rest** — rejected per standing instructions ("never offer to table this for later when the permanent solution is within reach"). The Docker prod stack + deploy script + healthcheck + backup script ARE the permanent solution; documentation alone is not.
2. **Wait for VANTA to specify which deliverable first** — rejected per "the answer is the finished product." VANTA already specified the directive (heavy production); the Architect's job is to identify the highest-leverage Phase 1 scope and execute.
3. **Open Arc B as multi-day from the start (one deliverable per day)** — rejected per "boil the ocean." The 10 Phase 1 deliverables are coherent; splitting them creates artificial seams. Phase 2/3 ARE multi-day; Phase 1 ships complete.
4. **Wait for ARCH-002 (docs) and ARCH-003 (UX) to ship first** — rejected. Operations runbook + deploy stack must precede UX polish (you don't polish a demo for a system nobody can deploy).

## VI. Decision

**Ship Arc B Phase 1 as v8.77.** Authorized by VANTA's heavy-production directive (`sanctum/2026-05-14-steady-state-revocation-heavy-production.md`) + the Architect's macro brief. Phase 1 = 10 deliverables = production-deployment foundations. Phase 2 + Phase 3 deferred to future Sanctums per multi-arc discipline.

The first v8.31 trigger condition (Arc B prod-deploy) is now formally fired and shipped. After v8.77, Arc B is open and active; ARCH-002 (docs) and ARCH-003 (UX) ship in subsequent days.

## VII. Outcome

**Ship: v8.77 closed Arc B Phase 1 with 10/10 ✅ on 2026-05-14.**

**Delivered:**

1. `docs/operator/OPERATIONS.md` — ~700-line production runbook
   (rewrite of v8.4 stub).
2. `docs/operator/SECRETS.md` — ~400-line secrets primer (new).
3. `polaris_web/docker-compose.prod.yml` — Caddy + app + Postgres
   + Redis stack with file-mounted secrets via `secrets:` block.
4. `polaris_web/Dockerfile.prod` — multi-stage (zk-builder +
   py-builder + slim runtime; non-root `polaris` user; tini
   entrypoint; bundles `/opt/polaris/zk`).
5. `polaris_web/Caddyfile` — Let's Encrypt auto-TLS,
   security-header set, edge rate-limit, HTTP→HTTPS redirect,
   h1/h2/h3.
6. `/api/health` rewritten — structured JSON with per-component
   status (database / redis / zk_binary / disk); HTTP 503 on
   unhealthy.
7. `scripts/polaris-deploy.sh` — idempotent {dev|staging|prod}
   with smoke test + rollback-to-prior-image on failure.
8. `scripts/polaris-backup.sh` — manifest-hashed tarball with
   `pg_dump` + sanctum/ + journal/ + treasury-roll +
   census-roll + sanctum-index; `--verify-latest` mode.
9. `scripts/polaris-generate-secrets.sh` +
   `scripts/polaris-rotate-secret.sh` — operator-facing secret
   lifecycle (umask-0177, mode-0600, archive-prior-on-rotate).
10. `meta/arc-b-production.md` — strategic record;
    MISSION.md gained `### Arc B` section; ROADMAP.md gained
    `## v16` with R16-1..R16-10.

**G-guards added (3):** G27 TLS-required, G28
no-sensitive-env-in-prod-compose, G29 structured-health-JSON.

**Structural invariants added (8):** in
`TestArcBProductionDeploymentStack` — deploy-stack-files-exist,
G27, G28, G29, Dockerfile-prod-non-root, Caddyfile-security-headers,
deploy-scripts-executable, secrets-dir-gitignored. 180 → 188
total.

**Source changes beyond docs/scripts/tests:** `polaris_web/app.py`
gained `_read_secret_file()` helper for `*_FILE` env vars (G28),
`POLARIS_VERSION='8.77'` constant, `_APP_STARTED_AT` epoch, four
per-component health-check helpers, rewritten `api_health()`
endpoint. `app.secret_key` and `DB_CONFIG['password']` read from
`*_FILE` env-vars with graceful direct-env-var fallback.

**Per §IV: the agent did NOT initiate the actual production deploy.**
That step remains VANTA's, on VANTA's terms.

**See:** `CHANGELOG.md` v8.77 entry · `journal/2026-05-14.md`
04:55 decision · `meta/arc-b-production.md` · `ROADMAP.md` v16
section.
