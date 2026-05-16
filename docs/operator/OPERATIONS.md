# OPERATIONS.md — Polaris production runbook (Arc B)

This is the runbook for operating Polaris in production.

For development setup: `README.md`. For threat model and security
posture: `SECURITY.md` and `DEVNOTES/threat-model.md`. For secrets:
`docs/operator/SECRETS.md`. For installation: `docs/operator/INSTALL.md`.

This document was rewritten under Arc B (production-deployment arc)
opened by `sanctum/2026-05-14-arc-b-production-deployment-opening.md`.
The pre-v8.77 version is preserved verbatim in git history.

---

## Table of contents

1. [Quick start (5 min)](#quick-start-5-min)
2. [System requirements](#system-requirements)
3. [Pre-deploy checklist](#pre-deploy-checklist)
4. [Deploy](#deploy)
5. [Verify](#verify)
6. [Day-2 operations](#day-2-operations)
7. [Backup & restore](#backup--restore)
8. [Scaling](#scaling)
9. [Monitoring & alerting](#monitoring--alerting)
10. [Incident response](#incident-response)
11. [Common errors](#common-errors)
12. [Upgrades](#upgrades)
13. [Decommissioning](#decommissioning)
14. [What this document does NOT cover](#what-this-document-does-not-cover)

---

## Quick start (5 min)

Production-ready Polaris on a single Linux host, behind TLS, with
backups, on commodity hardware:

```bash
# 1. Clone + enter
git clone https://github.com/<your-fork>/polaris.git
cd polaris

# 2. Generate all secrets (see docs/operator/SECRETS.md for what is generated)
./scripts/polaris-generate-secrets.sh

# 3. Set the public domain (must resolve to this host's public IP)
export POLARIS_DOMAIN=polaris.example.com

# 4. Deploy
./scripts/polaris-deploy.sh prod

# 5. Verify
curl -fsS https://${POLARIS_DOMAIN}/api/health | jq .
```

Within ~90 seconds Caddy will provision a Let's Encrypt certificate
and `/api/health` returns structured JSON with overall status
`healthy` and per-component checks (db / redis / zk-binary / disk).

If anything failed, jump to [Common errors](#common-errors). For the
expected health-check shape, see `docs/operator/SECRETS.md` →
"Health-check contract".

---

## System requirements

### Hardware (minimum)

- 2 vCPU
- 4 GB RAM
- 40 GB SSD (database growth budget: ~120 GB/year at 1M
  verifications/day; see [Storage growth](#storage-growth))
- 1 Gbps NIC

### Software

- Linux x86_64 (Debian 12+ / Ubuntu 22.04+ / RHEL 9+ tested)
- Docker Engine 24+ with Compose v2
- A public DNS A record pointing at this host (for TLS)
- TCP/443 reachable from the internet (for Let's Encrypt challenge
  and operator traffic)
- TCP/80 reachable from the internet (for the HTTP-01 challenge;
  Caddy redirects 80 → 443 in steady state)

### Network

The production stack listens on TCP/443 (Caddy) and exposes nothing
else externally. Internal services (app:8000, postgres:5432,
redis:6379) are reachable only inside the Compose network.

Out-bound: the host must reach Let's Encrypt
(`acme-v02.api.letsencrypt.org`) for certificate issuance.

---

## Pre-deploy checklist

- [ ] DNS A record for `${POLARIS_DOMAIN}` resolves to this host
- [ ] TCP/80 + TCP/443 reachable from the public internet
- [ ] All secrets generated via `scripts/polaris-generate-secrets.sh`
      and `ls -la secrets/` shows mode `0600`
- [ ] `secrets/` is in `.gitignore` (verify: `git check-ignore -v
      secrets/polaris_secret_key`)
- [ ] Backup destination configured (S3 bucket, local volume, or
      remote tarball drop)
- [ ] Monitoring endpoint configured (a place to receive alerts —
      PagerDuty / OpsGenie / a simple cron-curl)
- [ ] Admin operator email known (for the initial seeded account)
- [ ] G27 (TLS), G28 (no secrets in env), G29 (structured /api/health)
      verified by `pytest polaris_web/test_structural_invariants.py
      -k "Arc_B"`
- [ ] Read `SECURITY.md` once

---

## Deploy

### Standard path (Docker Compose, single host)

```bash
./scripts/polaris-deploy.sh prod
```

This script is idempotent. It performs:

1. `git pull` (skipped if `--no-pull`)
2. `docker compose -f polaris_web/docker-compose.prod.yml pull` to
   refresh upstream images (postgres, redis, caddy)
3. `docker compose build app` (multi-stage Dockerfile.prod)
4. Schema migration via the same load path as dev
   (`polaris_sql/00_load_all.sql`) — only applies fresh on an empty
   database; subsequent runs no-op
5. Smoke test: HTTP GET `/api/health` from inside the network must
   return overall `status: healthy`
6. Blue-green swap (when re-deploying over a running stack):
   `docker compose up -d --no-deps --force-recreate app` recreates
   the app container only; DB + Redis volumes are preserved
7. Rollback on failure: if the smoke test fails post-swap, the
   script restarts the previous image tag and exits non-zero

Three modes:

```bash
./scripts/polaris-deploy.sh dev       # local dev stack (delegates to polaris_mac_launch.sh)
./scripts/polaris-deploy.sh staging   # prod stack but on staging.${POLARIS_DOMAIN}
./scripts/polaris-deploy.sh prod      # production
```

### Manual path (advanced)

```bash
cd polaris_web

# Build the app image
docker compose -f docker-compose.prod.yml build app

# Bring up the stack
docker compose -f docker-compose.prod.yml up -d

# Tail logs until you see "Listening at: http://0.0.0.0:8000"
docker compose -f docker-compose.prod.yml logs -f app

# Smoke test from inside the network
docker compose -f docker-compose.prod.yml exec app curl -fsS http://localhost:8000/api/health
```

### Production stack components

| Service | Image | Role | Port (internal) |
|---|---|---|---|
| `caddy` | `caddy:2-alpine` | TLS termination, security headers, rate limit | 80 + 443 (host) |
| `app` | `polaris-app:prod` (built locally) | Flask + gunicorn (4 workers) | 8000 |
| `postgres` | `postgres:16-alpine` | Database | 5432 |
| `redis` | `redis:7-alpine` | Rate limiter backend + atlas cache | 6379 |

Volumes:
- `pg_data` (named) — Postgres data
- `redis_data` (named) — Redis AOF/RDB
- `caddy_data` (named) — Caddy's Let's Encrypt certs + state
- `caddy_config` (named) — Caddy's config-time state
- `./secrets/` (bind mount, read-only) — file-mounted secrets
- `./logs/` (bind mount) — gunicorn access + error logs
- `../sanctum/` (bind mount, read-only) — Sanctum audit-of-record
- `../journal/` (bind mount, read-only) — daily journal

---

## Verify

After deploy, run through this checklist:

```bash
# 1. Stack is up
docker compose -f polaris_web/docker-compose.prod.yml ps
# Every service should show "running" or "running (healthy)"

# 2. Public TLS endpoint
curl -fsS https://${POLARIS_DOMAIN}/api/health | jq .
# Should return: {"status": "healthy", "version": "8.77", ...}

# 3. Per-component health
curl -fsS https://${POLARIS_DOMAIN}/api/health | jq '.checks'
# Each of db / redis / zk_binary / disk should report "healthy"

# 4. TLS certificate chain
openssl s_client -connect ${POLARIS_DOMAIN}:443 -servername ${POLARIS_DOMAIN} </dev/null 2>/dev/null | openssl x509 -noout -issuer -subject -dates
# Issuer should be Let's Encrypt; notAfter should be ~90 days out

# 5. Security headers
curl -fsSI https://${POLARIS_DOMAIN}/ | grep -iE "strict-transport-security|x-frame-options|x-content-type-options|content-security-policy"
# All four headers should be present

# 6. HTTP → HTTPS redirect
curl -fsSI http://${POLARIS_DOMAIN}/ | head -1
# Should be: HTTP/1.1 308 Permanent Redirect (or 301)

# 7. Rate limiter is alive
for i in $(seq 1 5); do
  curl -fsS https://${POLARIS_DOMAIN}/api/health -o /dev/null -w "%{http_code}\n"
done
# All should return 200; the limiter only kicks in at 200 req/min/IP
```

### Initial admin login

The first operator account is seeded by `10_auth.sql`:

```
username: admin
password: (printed once during ./scripts/polaris-deploy.sh prod)
```

**Rotate immediately:**

1. Browse to `https://${POLARIS_DOMAIN}/`
2. Sign in
3. `/admin/users` → edit `admin` → set a new password (argon2id-hashed
   server-side)
4. Sign out + sign back in to confirm

---

## Day-2 operations

### Routine maintenance

| Task | Frequency | Command |
|---|---|---|
| Backup | Daily (automated) | `./scripts/polaris-backup.sh` (cron) |
| Verify backup integrity | Weekly | `./scripts/polaris-backup.sh --verify-latest` |
| Restore drill | Quarterly | `./scripts/polaris-restore.sh <latest> --target=polaris_drill` |
| Restore dry-run | Monthly | `./scripts/polaris-restore.sh <latest> --dry-run` (manifest-verify only) |
| Audit-log archive | Yearly | `./scripts/polaris-archive.sh --cutoff-days=1825` (C1-preserving export at the 5y retention floor) |
| Verify archive integrity | Quarterly | `./scripts/polaris-archive.sh --verify-latest --dest=DIR` |
| Audit-log purge (Phase 2b) | Operator-driven, after archive verify | `./scripts/polaris-purge.sh --archive=TARBALL --actor-user-id=N` |
| **Pheromone archive** (v9.07) | **Quarterly** | `./scripts/polaris-pheromone-archive.sh --cutoff='30 days ago'` — C1-preserving export of Pheromone rows older than cutoff; 30-day default per Sanctum §IV.1 |
| **Verify Pheromone archive** (v9.07) | **Quarterly** | `./scripts/polaris-pheromone-archive.sh --verify-latest` |
| **Pheromone purge** (v9.07 / D5-impl) | **Yearly**, after archive verify | `./scripts/polaris-pheromone-purge.sh --archive=TARBALL --cutoff=ISO --actor-user-id=N` — calls uc_pheromone_archive_purge() inside a transaction; G33 protected |
| Run Mycelium **commanders** | **Every 6h (cron)** | `python3 -m polaris_swarm.colony --swarm` — deposits high-intensity pheromones (33 commanders); HYDRA ant_colony watcher ALERTs when 72h silent. v9.01 cadence change; v9.02 correction (was misnamed); v9.03 split into commander + soldier rows. |
| Run Mycelium **soldiers** | **Every 30 min for 60s (cron)** | `python3 -m polaris_swarm.colony --soldiers --duration 60` — v9.03 hybrid-swarm soldier tier (8 lightweight classes); aggregated deposits (~10-20 per cycle batch); short half-life (1h). Sanctum 2026-05-14-hybrid-swarm-mirai-pattern. |
| Read the bloom heatmap | Daily | `./scripts/ai-swarm-bloom.sh` — operator-facing drift surface (read-only) |
| **Certificate transparency check** | **Daily (cron)** | `./scripts/polaris-ct-monitor.sh` — alerts on unexpected cert issuance for ${POLARIS_DOMAIN}; see [Certificate transparency monitoring](#certificate-transparency-monitoring-v901) below |
| Audit-log rotation | Yearly (cron) | `./scripts/polaris-rotate-logs.sh --actor-user-id=N` — wraps archive + verify + purge in one cron-ready pipeline |
| Operator onboarding | As needed | `./scripts/polaris-create-operator.sh --username NAME --role admin\|operator\|auditor --password-file PATH` — argon2id-hashed AppUser + AuthAuditLog entry |
| Treasury health check | Weekly | `./scripts/ai-treasury-report.sh` — penalty:reward ratio + class distribution |
| Scrape `/metrics` | Continuous (Prometheus) | `curl https://${POLARIS_DOMAIN}/metrics` — Prometheus text-format exposition |
| Rotate `POLARIS_SECRET_KEY` | 180 days | `./scripts/polaris-rotate-secret.sh polaris_secret_key` |
| Rotate DB password | 180 days | `./scripts/polaris-rotate-secret.sh polaris_db_password` |
| OS security updates | Monthly | distro-specific (`apt upgrade` / `dnf update`) |
| Docker image refresh | Monthly | `./scripts/polaris-deploy.sh prod` |
| Review AuthAuditLog for anomalies | Weekly | see [Audit review](#audit-review) |
| Review TrajectoryWatcher signals | Weekly | `./scripts/ai-hydra.sh` |

### Audit review

Polaris's audit-of-record discipline (v8.20) records every
state-changing event in 9 schema tables + 3 filesystem rolls. Review
cadence:

```bash
# Weekly: failed-login surface
docker compose -f polaris_web/docker-compose.prod.yml exec postgres \
  psql -U polaris_app -d polaris -c "
    SELECT username, count(*) AS attempts,
           min(occurred_at) AS first, max(occurred_at) AS last
    FROM AuthAuditLog
    WHERE outcome = 'FAILURE' AND occurred_at > now() - interval '7 days'
    GROUP BY username
    ORDER BY attempts DESC LIMIT 20;"

# Weekly: token lifecycle anomalies
docker compose -f polaris_web/docker-compose.prod.yml exec postgres \
  psql -U polaris_app -d polaris -c "
    SELECT new_state, count(*) FROM TokenLifecycleEvent
    WHERE event_at > now() - interval '7 days'
    GROUP BY new_state ORDER BY count(*) DESC;"

# Weekly: revocation velocity (R11-6)
docker compose -f polaris_web/docker-compose.prod.yml exec postgres \
  psql -U polaris_app -d polaris -c "
    SELECT issuing_agency_id, count(*) AS revocations_7d
    FROM TokenLifecycleEvent
    WHERE new_state = 'REVOKED' AND event_at > now() - interval '7 days'
    GROUP BY issuing_agency_id ORDER BY revocations_7d DESC LIMIT 5;"
```

### Reading container logs

```bash
# Live tail of the app
docker compose -f polaris_web/docker-compose.prod.yml logs -f --tail=100 app

# Last 24h of access log
docker compose -f polaris_web/docker-compose.prod.yml logs --since=24h app | grep -E "GET|POST"

# Caddy (TLS + reverse proxy)
docker compose -f polaris_web/docker-compose.prod.yml logs --tail=100 caddy

# Postgres
docker compose -f polaris_web/docker-compose.prod.yml logs --tail=100 postgres
```

Persistent log files are written to `./logs/` (mounted into the app
container as `/var/log/polaris/`).

### Operator authentication (WebAuthn-MFA, v8.97)

Operator login for admin accounts is two-factor: password + WebAuthn
assertion (Position B of `sanctum/2026-05-14-webauthn-operator-auth.md`).

**Enrollment cadence:**
- New admin accounts via `polaris-create-operator.sh --role admin` get
  `webauthn_required_after = now() + 30 days`
- During grace period: password-only login completes; user sees a
  warning banner with day count
- After deadline + no credential: login REFUSED with operator guidance
- After deadline + credential enrolled: password + WebAuthn assertion required

**Enroll a credential:**
1. Log in via `/login`
2. Navigate to `/settings/webauthn`
3. Press *Enroll WebAuthn credential* and follow the browser prompt
4. Optionally enroll a second credential as backup

See `docs/operator/SECRETS.md` § 7 for the full enrollment + recovery
runbook.

**Operator emergency recovery (locked-out admin):**

If an admin loses their authenticator AND the deadline has passed,
a second admin runs:

```bash
./scripts/polaris-recover-admin.sh \
    --target <username-of-locked-out-admin> \
    --authorizing-user-id <your-admin-user-id> \
    --window-minutes 15
```

The grant is audited as `EMERGENCY_PASSWORD_LOGIN_AUTHORIZED`. The
target must enroll a new credential at `/settings/webauthn` before
the window closes, otherwise the refusal returns.

For solo-admin deployments (no second admin available), generate a
printed mnemonic at enrollment time via
`./scripts/polaris-generate-recovery-code.sh` and store it offline.

**Audit the WebAuthn surface:**

```sql
-- Last 20 WebAuthn-class events
SELECT event_timestamp, event_type, username, detail
  FROM AuthAuditLog
 WHERE event_type LIKE 'WEBAUTHN_%'
    OR event_type = 'EMERGENCY_PASSWORD_LOGIN_AUTHORIZED'
 ORDER BY event_timestamp DESC LIMIT 20;

-- Enrolled credentials per admin
SELECT u.username, count(c.credential_id) AS credentials
  FROM AppUser u
  LEFT JOIN OperatorWebauthnCredential c ON c.user_id = u.user_id
 WHERE u.role = 'admin' AND u.is_active = TRUE
 GROUP BY u.username
 ORDER BY u.username;

-- Admins approaching their enrollment deadline (next 7 days)
SELECT username, webauthn_required_after
  FROM AppUser
 WHERE role = 'admin'
   AND webauthn_required_after IS NOT NULL
   AND webauthn_required_after > now()
   AND webauthn_required_after < now() + interval '7 days'
 ORDER BY webauthn_required_after;
```

### Rotate cryptographic algorithm

Marking an algorithm as `is_active = FALSE` prevents new tokens
under that algorithm without affecting existing tokens:

```sql
UPDATE CryptographicAlgorithm
SET is_active = FALSE
WHERE name = 'ECDSA-P256';
```

To migrate a holder to a new algorithm: issue a successor token
(`uc7_succeed_token`) referencing the new `algorithm_id`. UC-1
also supports specifying the multi-sig migration mode (R11-1 /
v8.18).

### Schema migrations (v8.95)

Polaris ships a custom polaris-native migration framework
(Position C of `sanctum/2026-05-14-schema-migration-framework.md`,
DECIDED 2026-05-14). State lives in the `schema_version` table
(13th audit-of-record instance) and migration files are
hand-written SQL pairs under `polaris_sql/migrations/`.

**What it is:**

- Each schema change is two files:
  `<YYYY-MM-DD>-<NNN>-<slug>.up.sql` and `.down.sql`
- Files apply in lexicographic order via `scripts/polaris-migrate.sh`
- SHA-256 of every applied file is recorded for tamper detection
- The `schema_version` registry is append-only (UPDATE/DELETE forbidden);
  reverts append a new `event_type='reverted'` row rather than mutating

**Authoring a new migration** (development workflow lives in
`polaris_sql/migrations/README.md`; the file pair is committed
together).

**Inspect state on the production stack:**

```bash
# What's on disk and what's currently applied
./scripts/polaris-migrate.sh --target=docker-stack --status
```

Sample output:

```
  Polaris schema migration status
  ────────────────────────────────

  Migrations on disk:
    ✓ 2026-05-14-001-idx-checkpoint-recent  (applied)

  schema_version events (lifetime, append-only):  3
  Currently applied (last event = applied):       1
```

**Apply pending migrations:**

```bash
# Apply ALL pending, recording your operator user_id in the registry
./scripts/polaris-migrate.sh --target=docker-stack \
    --actor-user-id <your-user-id> --up

# Apply only the next N pending
./scripts/polaris-migrate.sh --target=docker-stack \
    --actor-user-id <your-user-id> --up 1

# Preview what would be applied without writing
./scripts/polaris-migrate.sh --target=docker-stack --dry-run --up
```

The `--actor-user-id` flag records WHO authorized the change. Use
your own `AppUser.user_id`; do not share accounts. Find your id
with:

```bash
docker compose -f polaris_web/docker-compose.prod.yml exec postgres \
    psql -U postgres -d polaris -c \
    "SELECT user_id, username FROM AppUser WHERE role='admin'"
```

**Revert the most recent applied migration:**

```bash
./scripts/polaris-migrate.sh --target=docker-stack \
    --actor-user-id <your-user-id> --down 1
```

The runner refuses to revert if the `.up.sql` file has been edited
since the recorded SHA-256 was taken (exit code 6 — tamper
detection). If you legitimately need to change an already-applied
migration, write a new one that fixes the problem; do not edit
history.

**Exit codes** (greppable for incident response and CI):

| Code | Meaning |
|------|---------|
| 0    | success (or `--status` / `--dry-run` finished) |
| 2    | usage error |
| 3    | migrations directory missing/empty (only an issue for `--up`/`--down`) |
| 4    | filename validation error (must match `YYYY-MM-DD-NNN-slug`) |
| 5    | database call failed (migration content or psql error) |
| 6    | SHA-256 mismatch on revert — file edited post-apply, refusing |
| 7    | invalid argument (e.g., `--down 0`) |

**Backups + migrations.** Take a backup BEFORE applying a
migration on production. Polaris does not pause writes during
the migration's transaction; PostgreSQL transactional DDL handles
isolation correctly, but if anything goes wrong at the
applicaton-state level (a constraint that fails halfway through
a batched UPDATE, e.g.), restoring from the most recent
pre-migration backup is the recovery path. See § Backup &
restore below.

**The registry itself is the audit-of-record.** Querying it shows
exactly which migrations have run, when, by whom, and against
which file content (the recorded SHA-256). It is append-only at
the database level, so even a compromised admin role cannot
silently rewrite migration history without leaving evidence in
the audit trail of WHO tried to DELETE/UPDATE (the trigger logs
the rejection).

### Certificate transparency monitoring (v9.01)

Polaris's TLS certs are issued by Let's Encrypt via Caddy's
ACME client. Any cert for `${POLARIS_DOMAIN}` issued by a
DIFFERENT issuer is a sign of:

- A misconfigured Caddy that re-issued instead of renewed
- Compromised DNS allowing rogue ACME validation by a third party
- A CA mis-issuance attack (rare but real; documented in
  [PENTEST.md](PENTEST.md) § 6.12)

The CT monitor polls the public crt.sh log, compares against an
operator-maintained allowlist (`$STATE_DIR/ct-monitor/known.txt`),
and alerts on anything unexpected.

**Initial setup:**

```bash
# 1. Capture the current legitimate cert's SHA-256 fingerprint
echo | openssl s_client -connect ${POLARIS_DOMAIN}:443 \
                        -servername ${POLARIS_DOMAIN} 2>/dev/null \
    | openssl x509 -noout -fingerprint -sha256 \
    | awk -F= '{print $2}' | tr -d ': ' | tr '[:upper:]' '[:lower:]'

# 2. Add to allowlist
./scripts/polaris-ct-monitor.sh --add-known <fingerprint>

# 3. Verify
./scripts/polaris-ct-monitor.sh --list-known
```

**Daily cron** (recommended):

```cron
# /etc/cron.d/polaris-ct-monitor
# Run at 06:00 UTC daily; CT logs have ~2h propagation latency,
# so once a day catches every unexpected issuance within ≤24h.
0 6 * * * polaris cd /opt/polaris && ./scripts/polaris-ct-monitor.sh \
              --window-days 1 \
              --check ${POLARIS_DOMAIN} \
              >> /var/log/polaris/ct-monitor.log 2>&1
```

**On alert** (exit code 5):

The script logs anomalies to `$STATE_DIR/ct-monitor/anomalies.log`.
Investigate via [DR.md](DR.md) § 4.5 procedure. If the new cert is
a legitimate renewal (Caddy auto-renews ~30 days before expiry,
which produces a fresh fingerprint), add it to the allowlist:

```bash
./scripts/polaris-ct-monitor.sh --add-known <new-fingerprint>
```

If unfamiliar, treat as a SEV-2 incident; the cert may have been
issued to an attacker who controls a different CA path or the
operator's DNS.

**Exit codes:**

| Code | Meaning |
|------|---------|
| 0    | No anomalies (all certs in window are in the allowlist OR no certs in window) |
| 2    | Usage error |
| 3    | `POLARIS_DOMAIN` not set + no `--check` argument |
| 4    | Network error (crt.sh unreachable; treat as inconclusive — retry next cycle) |
| 5    | **Anomaly** — UNKNOWN cert detected; investigate immediately |
| 6    | Malformed allowlist file |

### Mycelium swarm cron schedule (v9.01)

The Mycelium swarm deposits pheromones (drift findings) into the
`Pheromone` table. The HYDRA `ant_colony_watcher` ALERTs when no
pheromones land in a 72-hour window — operationally that means
"the swarm isn't running."

Pre-v9.01 the swarm was operator-driven (manual `ai-swarm-bloom.sh`
runs). v9.01 adds a cron schedule so the 72h ALERT never trips
under normal operation:

```cron
# /etc/cron.d/polaris-swarm
# v9.03 hybrid swarm cadence:
#
# Commanders (heavyweight, identity-bearing): every 6h.
# ~30-90s per run; deposits 100-200 high-intensity pheromones.
0 */6 * * * polaris cd /opt/polaris && \
    POLARIS_DB_HOST=localhost POLARIS_DB_NAME=polaris POLARIS_DB_USER=polaris_app \
    polaris_web/venv/bin/python3 -m polaris_swarm.colony --swarm \
    >> /var/log/polaris/swarm.log 2>&1

# Soldiers (lightweight, disposable, aggregated): every 30 min for 60s.
# Closes the gap between commander runs; ensures HYDRA ant_colony
# ALERT never trips. ~10-20 aggregated deposits per cycle batch
# (low-intensity, short half-life). v9.03 / Sanctum 2026-05-14-hybrid-
# swarm-mirai-pattern.
*/30 * * * * polaris cd /opt/polaris && \
    POLARIS_DB_HOST=localhost POLARIS_DB_NAME=polaris POLARIS_DB_USER=polaris_app \
    polaris_web/venv/bin/python3 -m polaris_swarm.colony --soldiers --duration 60 \
    >> /var/log/polaris/soldier-swarm.log 2>&1
```

**Operational notes:**

- The cron user (`polaris` above) needs read access to the Polaris
  source tree + write access to the database (the swarm INSERTs
  into `Pheromone`)
- 4 runs/day × ~150 pheromones/run = ~600 pheromones/day; the
  table grows ~220K rows/year
- Use `./scripts/polaris-rotate-logs.sh` to archive + purge old
  pheromones quarterly (or extend the cutoff to keep more
  history if the operator wants longitudinal swarm-behavior
  analysis)
- The swarm is NOT in the production hot path — it can fail
  silently without affecting user-facing /api/* requests; the
  HYDRA ALERT is the safety net that surfaces persistent failures

**Verify the cron is healthy:**

```bash
# Should show pheromones deposited within the last 6 hours
psql -d polaris -c "
    SELECT
        date_trunc('hour', deposited_at) AS hour,
        count(*) AS pheromones
    FROM Pheromone
    WHERE deposited_at > now() - interval '24 hours'
    GROUP BY 1
    ORDER BY 1 DESC LIMIT 12;
"

# HYDRA should report 0 ALERT for ant_colony
./scripts/ai-hydra.sh | grep -A1 ant_colony
```

---

## Backup & restore

### Backup

`scripts/polaris-backup.sh` produces a single timestamped tarball
containing every durable component:

- `pg_dump` of the Polaris database (custom format, gzipped)
- `treasury-roll.json` (denarii ledger, Arc F)
- `census-roll.json` (citizen census, Arc E)
- `sanctum/` directory (full; filesystem audit-of-record)
- `journal/` directory (full; episodic memory)
- `meta/sanctum-index.md` (current computed index)
- `MANIFEST.json` with timestamps + SHA-256 hashes of each component

```bash
./scripts/polaris-backup.sh                    # writes /var/backups/polaris-YYYYMMDD-HHMMSS.tar.gz
./scripts/polaris-backup.sh --dest s3://...    # uploads to S3 (requires awscli)
./scripts/polaris-backup.sh --verify-latest    # extracts + verifies most recent backup
```

### Backup schedule

```bash
# /etc/cron.d/polaris-backup
0 3 * * * polaris /opt/polaris/scripts/polaris-backup.sh --dest /var/backups/polaris
0 4 * * 0 polaris /opt/polaris/scripts/polaris-backup.sh --verify-latest
```

Retention policy:

| Layer | Window | Where |
|---|---|---|
| Daily | 30 days | Local + offsite |
| Weekly | 12 weeks | Offsite (S3 / Glacier) |
| Monthly | 12 months | Cold storage |
| Yearly | Indefinite | Cold storage |

### Restore

`scripts/polaris-restore.sh` (v8.81) is the scripted counterpart to
`polaris-backup.sh`. It verifies every component's SHA-256 hash
against the in-band `MANIFEST.json`, then restores PostgreSQL +
filesystem audit-of-record (sanctum/, journal/, treasury-roll,
census-roll). It refuses to clobber a non-empty target database
without `--force`.

```bash
# Standard path — restore into a fresh database
createdb polaris_restored
./scripts/polaris-restore.sh \
    /var/backups/polaris-20260514T030000Z.tar.gz \
    --target=polaris_restored

# Verify-only mode (manifest check, then list what would be restored)
./scripts/polaris-restore.sh \
    /var/backups/polaris-20260514T030000Z.tar.gz \
    --dry-run

# Restore into the running production stack
./scripts/polaris-restore.sh \
    /var/backups/polaris-20260514T030000Z.tar.gz \
    --target=docker-stack

# DB-only restore (skip filesystem AoR)
./scripts/polaris-restore.sh <backup> --skip-fs

# Filesystem-AoR-only restore (skip DB)
./scripts/polaris-restore.sh <backup> --skip-db
```

The script preserves the existing `sanctum/` and `journal/`
directories under timestamped names
(`sanctum.pre-restore.<utc-timestamp>` /
`journal.pre-restore.<utc-timestamp>`) before overwriting — restore
is non-destructive at the filesystem layer; the operator can
investigate the prior state if a restore proves wrong.

Exit codes (greppable for incident response):

| Code | Meaning |
|---|---|
| 0 | Restore succeeded |
| 2 | Usage error |
| 3 | Backup file not found |
| 4 | MANIFEST.json missing inside archive |
| 5 | Manifest hash verification failed |
| 6 | Target DB not empty; `--force` required |
| 7 | `pg_restore` failed (state may be partial) |
| 8 | Filesystem AoR restore failed |
| 9 | `docker` not available (when `--target=docker-stack`) |

After restore:

```bash
# Run integrity checks
psql -d polaris_restored -c "SELECT count(*) FROM IdentityToken;"
psql -d polaris_restored -f polaris_sql/08_tests.sql        # 170 SQL self-tests; expect 0 failures
psql -d polaris_restored -f polaris_sql/12_v7_constraints.sql
```

If this was a real recovery (not a drill), **rotate every secret
next** — assume the prior secrets are also compromised:

```bash
./scripts/polaris-rotate-secret.sh polaris_secret_key
./scripts/polaris-rotate-secret.sh polaris_db_password
./scripts/polaris-rotate-secret.sh polaris_db_root_password
```

Recovery point objective (RPO): up to 24 hours with daily backups.
Recovery time objective (RTO): ~15 minutes for a clean restore on
matched hardware (drill-verified against a 256KB backup of the
seed database).

For tighter RPO, configure WAL archiving (PostgreSQL streaming
replication or `pgbackrest`) — Arc B Phase 2 will ship a paved-path
recipe.

### What NOT to back up

- The codebase itself — that's in git
- `./logs/` — captured by your log aggregator
- Docker images — rebuilt from the Dockerfile
- `secrets/` — sealed outside the backup tarball; generate fresh
  via `scripts/polaris-generate-secrets.sh` and use the same DB
  password as the restore source, OR rotate everything after
  restore (preferred)

### Audit-log archive + purge (Phase 2b / v8.87)

**Constitutional carve-out** — `sanctum/2026-05-14-audit-log-deletion-from-hot.md`
selected Position B: archive-then-delete via a dedicated
procedure. C1's append-only invariant is preserved at the
*constitutional* level by the archive + checkpoint chain; the
table-level invariant is loosened for four high-volume audit
tables (`TokenLifecycleEvent`, `VerificationEvent`,
`EnrollmentStatusEvent`, `AuthAuditLog`) when and only when
`uc_archive_purge()` is running.

**Two-step retention workflow:**

```bash
# Step 1: produce a manifest-hashed archive of rows older than the
#         retention floor (default 1825 days / 5y).
./scripts/polaris-archive.sh --cutoff-days=1825 --dest=/var/backups

# Step 2: verify the archive (re-hashes every component against MANIFEST.json).
./scripts/polaris-archive.sh --verify-latest --dest=/var/backups

# Step 3: actually purge the matching rows from hot tables. This is
#         the deletion step; it requires --actor-user-id (must be admin).
./scripts/polaris-purge.sh \
    --archive=/var/backups/polaris-archive-<TIMESTAMP>.tar.gz \
    --actor-user-id=<admin user_id>

# Step 4: smoke. The hot tables now exclude the purged rows; the
#         LifecycleArchiveCheckpoint table has one new row recording
#         the SHA-256 + cutoff + per-table row counts.
psql -d polaris -c "
    SELECT checkpoint_id, purged_at, cutoff_timestamp,
           rows_purged_total, archive_uri
    FROM LifecycleArchiveCheckpoint
    ORDER BY purged_at DESC LIMIT 5"
```

**Non-repudiation chain** — operators who need to answer "did
event X happen?":

1. Query the hot tables. If found, done.
2. If not, query `LifecycleArchiveCheckpoint` for cutoffs that
   would have covered when X was expected.
3. Retrieve the archive tarball at `archive_uri`; verify its
   SHA-256 matches `archive_sha256` in the checkpoint.
4. Extract; read the matching CSV file in the tarball; locate X.

**Archive custody is operator-discretion.** The procedure stores
the URI verbatim in `archive_uri`; the operator is responsible
for keeping the archive accessible at that URI for the chain
to remain whole. If the archive moves, append a new checkpoint
row recording the move (the table is append-only — the move
itself is audit-of-record).

**What the GUC carve-out does and does not allow:**

| Action | Outside `uc_archive_purge` | Inside `uc_archive_purge` |
|---|---|---|
| DELETE on protected audit tables | rejected (insufficient_privilege) | permitted |
| UPDATE on protected audit tables | rejected | rejected |
| DELETE on LifecycleArchiveCheckpoint | rejected (G30) | rejected (G30 — no carve-out at this layer) |
| UPDATE on LifecycleArchiveCheckpoint | rejected (G30) | rejected (G30) |

`SET LOCAL polaris.purge_in_progress` is transaction-scoped; if
the procedure rolls back, the deletes and the checkpoint roll
back together, atomically.

**Phase 2b coverage** — the four reject_audit_modification-protected
tables: `TokenLifecycleEvent`, `VerificationEvent`,
`EnrollmentStatusEvent`, `AuthAuditLog`. **Not covered** in
v8.87 (deferred to Phase 2c if storage pressure justifies):
`AnchorBatch` (FK from BlockchainAnchor); `AgencyTrustAttestation`
+ `DuressEvent` (separate immutability triggers; pattern can be
extended to those when needed).

---

### Pheromone archive + purge (v9.07 / D5-impl)

**Source:** Sanctum
[`sanctum/2026-05-15-pheromone-rotation.md`](../../sanctum/2026-05-15-pheromone-rotation.md)
Position A — mirror v8.84+v8.87 framework for the Pheromone table
(the v8.62 Mycelium swarm substrate; append-only AoR with operator-
controlled archive+purge, outside the canonical-12 constitutional
set). Polaris-self-roadmap-2026-05-14 item D5 surfaced the
~50K rows/day growth projection.

**Why a separate carve-out from audit-log:** Pheromone uses its
**own GUC** (`polaris.pheromone_purge_in_progress`), distinct from
the audit-log GUC (`polaris.purge_in_progress`). This prevents
cross-contamination — opening the audit-log carve-out cannot
accidentally allow Pheromone DELETEs.

**G-guards:**
- **G32** (parallel to G30) — `LifecyclePheromoneCheckpoint` is
  strictly append-only. NO GUC carve-out at the checkpoint layer.
- **G33** (parallel to G31) — `uc_pheromone_archive_purge()` is the
  ONLY sanctioned DELETE path on Pheromone.

**Operator workflow (two-step):**

```bash
# Step 1: archive — exports rows older than cutoff to a manifest-hashed
#                   tarball. C1-preserving (SELECT only; never DELETE).
./scripts/polaris-pheromone-archive.sh \
    --cutoff='30 days ago' \
    --out-dir=./archives/pheromone

# (Optional) verify the latest archive's SHA-256
./scripts/polaris-pheromone-archive.sh --verify-latest

# Step 2: purge — calls uc_pheromone_archive_purge() inside a tx;
#                  validates SHA-256 against manifest before issuing
#                  DELETE; writes LifecyclePheromoneCheckpoint row;
#                  carve-out GUC evaporates at COMMIT.
./scripts/polaris-pheromone-purge.sh \
    --archive=./archives/pheromone/polaris-pheromone-archive-<TS>-<N>rows.tar.gz \
    --cutoff='2026-04-15 00:00:00+00' \
    --actor-user-id=1
```

**Adversarial guarantees** (verified by D5-impl drill 2026-05-15):
- Direct `DELETE FROM Pheromone` (raw, outside procedure) → REJECTED
  with `insufficient_privilege`
- Direct `UPDATE Pheromone` → REJECTED (no carve-out for UPDATE)
- Direct `DELETE FROM LifecyclePheromoneCheckpoint` → REJECTED (G32:
  no carve-out at checkpoint layer)
- After `COMMIT` of a successful purge, raw `DELETE` immediately
  rejected again — the GUC is `SET LOCAL`, evaporates at txn boundary
- `uc_pheromone_archive_purge()` rejects: cutoff in future,
  malformed SHA-256, non-existent actor, non-admin actor

**Recommended cadence:** quarterly archive (3 months); yearly purge
(operator-driven after archive verify). Default cutoff 30 days
preserves live data for HYDRA's 6h/24h pheromone-context windows
+ comfortable margin.

**Non-repudiation chain:** the `LifecyclePheromoneCheckpoint` row +
the offline archive tarball together reconstitute every purged row.
If the operator loses the tarball, the checkpoint row still proves
the purge happened + the SHA-256 of what should be in the tarball.

---

## Scaling

### When to scale

Single-host Polaris (4 vCPU / 8 GB / SSD) handles:

- ~200 verifications/sec sustained
- ~5M `VerificationEvent` rows in the active dataset (with the v6
  spatial index)
- ~50 concurrent operators
- ~10 anchor-batch closes / hour
- ~5 ZK-epoch closes / hour (the Plonky2 prover is single-threaded;
  see `polaris_zk/`)

Past those numbers, the architecture supports the following
horizontal-scaling moves. Each subsection below names the
inflection point at which it pays off and the concrete recipe to
apply.

### Connection pooling (pgbouncer) — DEFAULT in v8.83+

**Inflection:** ~30-50 concurrent operators / ~100 concurrent
sessions / sustained 100+ verifications/sec. Without pgbouncer,
Polaris's per-request connection pattern saturates Postgres's
`max_connections` ceiling (default 100). With pgbouncer in
transaction-pooling mode, thousands of short-lived app
connections multiplex onto a small handful of long-lived backend
connections.

**Already shipped:** the production stack
(`docker-compose.prod.yml`) places **pgbouncer between the app
and Postgres** by default since v8.83. The app reads
`POLARIS_DB_HOST=pgbouncer` and `POLARIS_DB_PORT=6432`; pgbouncer
forwards to `postgres:5432`. No operator action needed for
standard deployments.

**Tuning knobs** (defaults in `docker-compose.prod.yml`):

| Setting | Default | Raise when |
|---|---|---|
| `PGBOUNCER_DEFAULT_POOL_SIZE` | 20 | App workers × 1.5 above this (so 30+ for 20 gunicorn workers) |
| `PGBOUNCER_MIN_POOL_SIZE`     | 5  | Cold-start latency matters; pre-warming pool reduces first-request P99 |
| `PGBOUNCER_RESERVE_POOL_SIZE` | 5  | Bursty traffic; reserve absorbs spikes |
| `PGBOUNCER_MAX_CLIENT_CONN`   | 500 | If you see "no more connections allowed" from clients |
| `PGBOUNCER_MAX_DB_CONNECTIONS` | 50 | Must be ≤ Postgres `max_connections` minus admin headroom (~10) |

**Operator commands:**

```bash
# Connection-pool live view (admin pseudo-db)
docker compose -f polaris_web/docker-compose.prod.yml exec pgbouncer \
    psql -h 127.0.0.1 -p 6432 -U polaris_app pgbouncer -c "SHOW POOLS;"

# All active client connections
docker compose -f polaris_web/docker-compose.prod.yml exec pgbouncer \
    psql -h 127.0.0.1 -p 6432 -U polaris_app pgbouncer -c "SHOW CLIENTS;"

# Stats summary (queries/sec, avg wait, etc.)
docker compose -f polaris_web/docker-compose.prod.yml exec pgbouncer \
    psql -h 127.0.0.1 -p 6432 -U polaris_app pgbouncer -c "SHOW STATS;"
```

**When pgbouncer transaction-pooling is wrong:**

- If you start using prepared statements cached client-side
  (Polaris doesn't), you'll need session-pooling or to disable
  cached prepared statements.
- If you start using `LISTEN`/`NOTIFY` (Polaris doesn't),
  transaction-pooling discards the listening session at txn end.
- `SET SESSION` calls (Polaris uses only short-lived
  `polaris.actor_username` GUCs inside the transaction) are
  fine.

### gunicorn worker tuning — `WEB_CONCURRENCY`

**Inflection:** sustained CPU utilization above ~70% on the app
container, OR p95 latency creeping above the request budget.

**Recipe:**

```bash
# In your shell or systemd unit file:
export WEB_CONCURRENCY=8

# Then deploy as usual:
./scripts/polaris-deploy.sh prod
```

Rule of thumb: `WEB_CONCURRENCY = (2 × vCPU) + 1` for the
gunicorn default sync worker class. The default is 4 (suitable
for 2-vCPU hosts). On an 8-vCPU host raise to 17. Above 16
workers, also raise `PGBOUNCER_DEFAULT_POOL_SIZE` proportionally.

### Read replica — for atlas-dominated read load

**Inflection:** atlas API (`/api/atlas/*`) dominates request
volume AND p99 latency above 200ms.

**Recipe (deferred to Phase 2.5):** add a PostgreSQL streaming
replica; Caddy or HAProxy routes `/api/atlas/*` to the replica
endpoint. The app's read paths are read-only by construction
(SELECT-only); the routing layer is upstream of any auth.

Until shipped, the workaround is to scale Postgres vertically
(more vCPU + SSD IO).

### Redis cluster — for high-QPS rate limiting + atlas cache

**Inflection:** sustained 500+ req/min/IP across distinct
clients, OR rate-limiter Redis latency p95 > 5ms.

**Recipe (deferred to Phase 2.5):** Redis Sentinel or Redis
Cluster (operator's choice) replaces the single Redis instance.
The app's `security.py` rate-limiter selection logic
auto-discovers Redis via `POLARIS_REDIS_URL`; point it at the
cluster's read-write endpoint.

Until shipped: a single Redis instance with `maxmemory 256mb`
and `allkeys-lru` (the current default) handles ~50k ops/sec
which is well above Polaris's expected QPS.

### PostGIS — for atlas spatial queries at very high cardinality (R8-4 Phase 1 ✅ v8.88)

**Inflection:** atlas API p95 > 500ms at 5M+ events with the
default B-tree spatial indexes; B-tree breaks down past ~10M
events because it doesn't model 2D proximity natively.

**Recipe (v8.88+):** the `polaris_sql/13_postgis.sql` script is
optional-by-design — schema works with and without the extension.

```bash
# 1. As a Postgres superuser, install the extension once:
docker compose -f polaris_web/docker-compose.prod.yml exec postgres \
    psql -U postgres -d polaris -c "CREATE EXTENSION postgis;"

# 2. Re-run the load script so 13_postgis.sql picks up the change:
docker compose -f polaris_web/docker-compose.prod.yml exec postgres \
    psql -U postgres -d polaris -f /docker-entrypoint-initdb.d/sql/13_postgis.sql

# 3. Confirm:
docker compose -f polaris_web/docker-compose.prod.yml exec postgres \
    psql -U postgres -d polaris -c "
        SELECT EXISTS (SELECT 1 FROM pg_extension WHERE extname='postgis') AS postgis_loaded,
               EXISTS (SELECT 1 FROM information_schema.columns
                       WHERE table_name='verificationevent' AND column_name='geo')
                       AS geo_column_present"
```

After step 3 both should return `t`. The schema gains:
- `VerificationEvent.geo` (generated, stored) + `gix_verification_geo` (GiST)
- `TokenLifecycleEvent.geo` (generated, stored) + `gix_lifecycle_geo` (GiST)

The application-layer atlas functions still use the B-tree path
in v8.88 — the function rewrite (Phase 2 of R8-4) is gated on a
PostGIS-enabled benchmark environment where the ≥3× acceptance
criterion can be measured. Until Phase 2 ships, operators with
PostGIS active can run hand-queries against the GiST index
directly (see `DEVNOTES/atlas-scaling.md` § "PostGIS-optional
scaling path" for a sample `ST_DWithin` query).

**When NOT to enable PostGIS:** managed Postgres tiers that gate
it behind paid plans (RDS free tier, some Aiven plans). The
B-tree fallback is operationally complete below ~5M events.

### Vertical alternative

For most deployments the cheaper move is **vertical scaling
first, horizontal second**:

- 2 vCPU → 4 vCPU: doubles app throughput, gunicorn worker bump
- 4 GB → 16 GB: enables larger `shared_buffers` for Postgres
- SSD → NVMe: cuts atlas p99 by ~3x at large cardinality

These changes are operator-driven and don't require app code
changes.

### Storage growth

`VerificationEvent` grows fastest. Sizing rule:

- ~300 bytes per VerificationEvent row (including indexes)
- 1M verifications/day → ~330 MB/day → ~120 GB/year

Plan 5-year retention; archive older to cold storage if needed.
Phase 2 ships an automated archive policy (audit-log-archive: S3
+ Glacier rotation).

---

## Monitoring & alerting

### Health check

`GET /api/health` (no auth) returns structured JSON:

```json
{
  "status": "healthy",
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

Overall status:
- `healthy` — every check is healthy; HTTP 200
- `degraded` — some non-fatal check is degraded (e.g., redis
  slow); HTTP 200
- `unhealthy` — at least one critical check is unhealthy (db
  unreachable, disk full); HTTP 503

This contract is structurally enforced by G29 in
`test_structural_invariants.py`.

### Recommended alerts

| Condition | Severity | Action |
|---|---|---|
| `/api/health` returns 503 sustained >2 min | Page | Investigate immediately |
| `/api/health` returns degraded sustained >10 min | Notify | Investigate within business hours |
| `disk.free_gb` < 5 | Page | Free space or expand volume |
| `disk.used_pct` > 85 | Notify | Plan capacity expansion |
| `database.latency_ms` > 500 sustained | Notify | Investigate slow queries |
| Failed logins >50/min sustained | Page | Suspected brute-force |
| 5xx rate > 0.1% sustained | Notify | Bug or capacity issue |
| Caddy ACME failure | Page | TLS will expire in <90 days |

### Metrics worth watching

| Metric | Source | Threshold |
|---|---|---|
| `/api/health` overall status | endpoint | 503 = page |
| DB latency | `/api/health` `checks.database.latency_ms` | >500ms = degraded |
| 4xx rate | gunicorn log | >5% sustained = investigate |
| 5xx rate | gunicorn log | >0.1% sustained = investigate |
| `failed_login_count` delta | `AuthAuditLog` | spike = brute force |
| `pg_stat_activity` rows | DB | >100 connections = leak |
| Anchor-batch close latency | `AnchorBatch.closed_at - opened_at` | >1h = backed up |
| ZK epoch close latency | `TokenStateEpoch` | >1h = prover overload |

### Prometheus metrics (`/metrics` — v8.93)

A Prometheus-compatible `/metrics` endpoint exposes time-series
data complementing `/api/health`'s point-in-time view. No
authentication; consumed by a scraper in the cluster network or
behind operator-internal ACL.

**Scrape config example** (Prometheus `prometheus.yml`):

```yaml
scrape_configs:
  - job_name: polaris
    metrics_path: /metrics
    scheme: https
    scrape_interval: 30s
    static_configs:
      - targets: ['polaris.example.com:443']
```

**Exposed metrics:**

| Metric | Type | Labels | Meaning |
|---|---|---|---|
| `polaris_requests_total` | counter | route, method, status | HTTP requests served |
| `polaris_request_latency_seconds` | histogram | route | Per-route request latency |
| `polaris_verifications_total` | counter | disclosure_level | VerificationEvent rows (incremented at insert time — Phase 2.5 wiring) |
| `polaris_db_query_latency_seconds` | histogram | — | DB round-trip (sampled on `/api/health` probes) |
| `polaris_pheromones_recent` | gauge | — | Pheromone deposits in last 72h (Mycelium liveness — pairs with HYDRA ant_colony watcher) |
| `polaris_app_info` | gauge | version | App metadata; value always 1; the label carries the data |

**Alert example** (Prometheus alerting rule):

```yaml
groups:
  - name: polaris
    rules:
      - alert: PolarisSwarmDormant
        expr: polaris_pheromones_recent == 0
        for: 72h
        annotations:
          summary: "Mycelium swarm has not deposited in 72h"
          runbook: "Check scripts/ai-swarm-bloom.sh cron + HYDRA ant_colony watcher"
      - alert: PolarisHigh5xx
        expr: |
          sum(rate(polaris_requests_total{status=~"5.."}[5m]))
            / sum(rate(polaris_requests_total[5m]))
            > 0.001
        for: 10m
        annotations:
          summary: "5xx rate > 0.1% sustained"
```

**Graceful fallback:** if `prometheus_client` is not installed
(ad-hoc dev environment without the prod image), `/metrics`
returns HTTP 503 with a plain-text message rather than crashing.

---

## Encryption at rest (v8.93)

The production stack's `pg_data` volume is **not** encrypted by
default. PostgreSQL's data files sit on the host filesystem in
plaintext. For deployments handling holder PII this is a real
gap — the schema enforces application-layer privacy (C2 / C9 /
audit-log discipline) but a host-filesystem read bypasses that.

**Recommended recipes** (operator picks one based on deployment):

### Option A — LUKS on the host (bare-metal / VM)

```bash
# One-time setup on a fresh host BEFORE running polaris-deploy.sh prod
sudo cryptsetup luksFormat /dev/sdb
sudo cryptsetup open /dev/sdb polaris_pg_crypt
sudo mkfs.ext4 /dev/mapper/polaris_pg_crypt
sudo mkdir -p /opt/polaris/pg_data
sudo mount /dev/mapper/polaris_pg_crypt /opt/polaris/pg_data

# Add to /etc/crypttab + /etc/fstab for boot-time mount with key file
echo "polaris_pg_crypt UUID=$(sudo blkid -s UUID -o value /dev/sdb) /etc/polaris/luks.key luks" | sudo tee -a /etc/crypttab
echo "/dev/mapper/polaris_pg_crypt /opt/polaris/pg_data ext4 defaults 0 2" | sudo tee -a /etc/fstab

# Then override the pg_data volume mount in docker-compose.prod.yml:
#   - /opt/polaris/pg_data:/var/lib/postgresql/data
```

The LUKS key file (`/etc/polaris/luks.key`) is mode 0400, owned
by root, and **never enters a backup tarball**. If the host
disk is removed, ransacked, or imaged, the data is inert.

### Option B — Managed Postgres with TDE

AWS RDS, Google Cloud SQL, Azure Postgres Flexible Server all
support transparent disk encryption (TDE) at the storage layer.
Enable it at provisioning time; rotate the KMS key per the
provider's recommendation; verify via the provider's console
that the database instance reports `storage_encrypted: true`.

The Polaris stack doesn't change; only the Postgres backend
moves from the docker compose service to the managed instance.

### Option C — Filesystem-level encryption (eCryptfs, fscrypt)

Per-directory encryption for the `pg_data` mount only.
Lighter-weight than full-disk; same key-management
considerations.

**Verification step** (operator should run after any of the
above):

```bash
# Sanity: is the pg_data mount on an encrypted device?
docker compose -f polaris_web/docker-compose.prod.yml exec postgres \
  df -T /var/lib/postgresql/data | tail -1
# LUKS shows "crypt" in the filesystem-type column
# Managed TDE shows ext4/xfs but the storage-layer attestation is in the cloud console
```

Cross-reference: `docs/operator/PRIVACY.md` § Append-only audit
documents the application-layer privacy posture; encryption at
rest closes the host-filesystem-read attack vector below it.

---

## Point-in-time recovery (PITR) with WAL archiving (v8.93)

The default backup cadence (daily `polaris-backup.sh`) gives an
RPO of 24 hours — anything between backups is lost on a hard
crash. **For deployments that need minute-grade RPO**, configure
WAL archiving via `pgbackrest`.

### Why pgbackrest

- Multi-repository support (local + S3 + Azure + GCS)
- Differential + incremental backups against full-PITR base
- Cryptographic checksums on every WAL segment
- Parallel restore (multiple workers)
- Compatible with the existing `polaris-backup.sh` schedule

### Setup recipe

```bash
# 1. Install pgbackrest on the host (or in a sidecar container)
sudo apt-get install -y pgbackrest

# 2. Configure /etc/pgbackrest/pgbackrest.conf
sudo tee /etc/pgbackrest/pgbackrest.conf <<EOF
[global]
repo1-path=/var/lib/pgbackrest
repo1-retention-full=2
repo1-retention-archive=14    # 14-day WAL retention
process-max=2
log-level-console=info
log-level-file=detail

[polaris]
pg1-path=/var/lib/postgresql/data
pg1-port=5432
pg1-user=postgres
pg1-host=postgres
EOF

# 3. Stanza-create (one-time)
sudo -u postgres pgbackrest --stanza=polaris stanza-create

# 4. Postgres-side configuration (adds to docker-compose.prod.yml
#    postgres environment):
#      POSTGRES_INITDB_ARGS: "--auth-host=scram-sha-256 --wal-level=replica"
#    AND in the postgres command:
#      archive_mode = on
#      archive_command = 'pgbackrest --stanza=polaris archive-push %p'
#      max_wal_senders = 3

# 5. Cron schedule
cat | sudo tee /etc/cron.d/pgbackrest-polaris <<EOF
# Full backup weekly, differential daily, archive-check hourly
0 2 * * 0 postgres pgbackrest --stanza=polaris --type=full backup
0 3 * * 1-6 postgres pgbackrest --stanza=polaris --type=diff backup
30 * * * * postgres pgbackrest --stanza=polaris check
EOF
```

### Point-in-time restore

```bash
# Restore to a specific timestamp
sudo systemctl stop polaris-app
sudo -u postgres pgbackrest --stanza=polaris \
    --type=time \
    --target="2026-05-14 14:30:00 UTC" \
    --target-action=promote \
    restore

sudo systemctl start polaris-app
```

**RPO with WAL archiving:** ~1 minute (last `archive_command`).
**RTO:** ~15-30 minutes (restore from base + WAL replay).

### When NOT to bother

- Below ~5M events at low operator volume, the daily
  `polaris-backup.sh` cadence is sufficient and pgbackrest
  adds operational complexity that doesn't pay off.
- Managed Postgres (RDS / Cloud SQL) already does WAL
  archiving at the storage layer; pgbackrest would duplicate.

---

## Incident response

### Database unreachable

`/api/health` returns 503; Caddy returns 502 to clients.

1. `docker compose -f polaris_web/docker-compose.prod.yml ps`
   — is the postgres container up?
2. `docker compose -f polaris_web/docker-compose.prod.yml logs
   postgres | tail -50`
3. Check disk space: `df -h` (most common cause)
4. Check `pg_stat_activity` for stuck queries:
   `docker compose ... exec postgres psql -U polaris_app -c "SELECT
   pid, state, query_start, query FROM pg_stat_activity WHERE state
   != 'idle';"`
5. If recoverable, `docker compose ... restart postgres`. If not,
   restore from the latest backup.

### Suspected operator-credential compromise

1. **Immediate:** lock the affected operator account:

   ```sql
   UPDATE AppUser SET locked_until = now() + interval '30 days'
   WHERE username = '<compromised>';
   ```

2. **Audit:** review `AuthAuditLog` for the suspected window:

   ```sql
   SELECT * FROM AuthAuditLog
   WHERE username = '<x>'
     AND occurred_at > now() - interval '7 days'
   ORDER BY occurred_at DESC;
   ```

   Look for unusual IPs, unusual times.

3. **Review token actions:**

   ```sql
   SELECT * FROM TokenLifecycleEvent
   WHERE actor_agency_id = (SELECT agency_id FROM AppUser
                            WHERE username = '<x>')
     AND event_at > '<compromise window start>'
   ORDER BY event_at DESC;
   ```

   Any tokens issued / revoked / lost during the window need
   re-validation by an uncompromised operator.

4. **Rotate:** new password (via UI), new session secret if
   widespread compromise (`./scripts/polaris-rotate-secret.sh
   polaris_secret_key` — this invalidates ALL sessions).

5. **Document:** post-mortem in `journal/<date>.md`. If a new
   attack class was used, also update `DEVNOTES/known-gotchas.md`.

### Suspected schema tampering (DBA-level compromise)

1. **Stop writes:** `docker compose -f
   polaris_web/docker-compose.prod.yml stop app`.

2. **Verify constraints intact:**

   ```bash
   docker compose -f polaris_web/docker-compose.prod.yml run --rm \
     app pytest test_structural_invariants.py -k "TestHardConstraints"
   ```

   Each C1-C10 invariant should pass. Any failure ⇒ schema has
   been modified.

3. **Check append-only triggers:**

   ```sql
   SELECT trigger_name, event_object_table, action_statement
   FROM information_schema.triggers
   WHERE trigger_name LIKE '%append_only%'
   ORDER BY trigger_name;
   ```

   Expected: 4 append-only triggers (lifecycle, verification,
   enrollment-event, anchor-batch). All should match the committed
   `06_triggers.sql`.

4. **Check audit-table row counts:**

   ```sql
   SELECT 'lifecycle' AS table, count(*) FROM TokenLifecycleEvent
   UNION ALL SELECT 'verification', count(*) FROM VerificationEvent
   UNION ALL SELECT 'enrollment', count(*) FROM EnrollmentStatusEvent
   UNION ALL SELECT 'anchor-batch', count(*) FROM AnchorBatch
   UNION ALL SELECT 'attestation', count(*) FROM AgencyTrustAttestation
   UNION ALL SELECT 'duress', count(*) FROM DuressEvent;
   ```

   Compare against the latest backup. Any unexplained decrement
   indicates tampering.

5. **If tampering confirmed:** restore from backup. The audit log
   is the source of truth; if it has been tampered with, the
   system has lost its non-repudiation guarantee and a public
   disclosure may be required.

### Unbounded resource consumption

Symptom: gunicorn workers hung; CPU 100%; atlas API slow.

1. **Check the cache:** `GET /api/atlas/cache-stats` — high miss
   rate suggests a query pattern not benefiting from the cache.
2. **Check for an attacker:** `docker compose logs caddy | grep
   429` — Caddy rate-limiter rejections indicate brute-force.
3. **Check connection count:** `SELECT count(*) FROM
   pg_stat_activity WHERE usename = 'polaris_app';` If >100, a
   connection leak; restart gunicorn:
   `docker compose ... restart app`.
4. **Check the ZK queue:** Plonky2 prover is single-threaded; a
   backed-up epoch close queue can starve other requests. Defer
   non-urgent epoch closes.

---

## Common errors

### "Caddy could not get certificate"

Cause: Let's Encrypt HTTP-01 challenge failed. Most often DNS
hasn't propagated, or TCP/80 is firewalled.

```bash
# Verify DNS
dig +short ${POLARIS_DOMAIN}
# Should match this host's public IP

# Verify port 80 is open from outside
curl -fsS http://${POLARIS_DOMAIN}/
# From a different host; should return 308 redirect to https

# Tail Caddy logs
docker compose -f polaris_web/docker-compose.prod.yml logs caddy | tail -50
```

### "/api/health returns unhealthy: zk_binary not found"

Cause: the production image was built without Rust toolchain, or
the prover binary wasn't bundled.

```bash
# Verify binary exists in the running container
docker compose -f polaris_web/docker-compose.prod.yml exec app \
  ls -la /opt/polaris/zk

# If missing, force rebuild
docker compose -f polaris_web/docker-compose.prod.yml build --no-cache app
docker compose -f polaris_web/docker-compose.prod.yml up -d --force-recreate app
```

The Dockerfile.prod has a `--build-arg POLARIS_ZK_BUILD=1` (default
on) that includes a `cargo +nightly build --release` of the Plonky2
prover in the builder stage. Set `--build-arg POLARIS_ZK_BUILD=0`
to skip if you don't need ZK epochs (e.g., for a development
restore).

### "Postgres docker volume drift"

Cause: the password in `secrets/polaris_db_password` doesn't match
what the `pg_data` volume was initialized with. Common after
restore-from-backup if backups were taken under different secrets.

```bash
# OPTION A: rotate the secret to match the volume's expected password
echo "<the original password>" > secrets/polaris_db_password
chmod 0600 secrets/polaris_db_password
docker compose -f polaris_web/docker-compose.prod.yml up -d --force-recreate

# OPTION B: nuke the volume and re-initialize (destroys all data!)
docker compose -f polaris_web/docker-compose.prod.yml down -v
./scripts/polaris-deploy.sh prod
```

### "Login redirects to /login again"

Cause: `POLARIS_SECRET_KEY` was rotated. All session cookies
signed under the old key now fail validation. Expected behavior;
operators must sign in again.

### "Localhost refused to connect" (dev launcher only)

Two root causes (resolved across v8.51 + v8.55):
1. Browser-background-throttling > stale-heartbeat threshold
2. Page-hide / before-unload firing the quit beacon on navigation

Both fixed. Affects only the dev launcher
(`polaris_mac_launch.sh`), not the production stack. See
`CLAUDE.md` gotcha #11.

### "ZK prove takes >30 seconds"

The Plonky2 prover is single-threaded and CPU-bound. On a 2 vCPU
host, expect ~10-15s per epoch close at 100 leaves. To improve:

1. Pin more CPUs to the app container (Compose `cpus: 4`)
2. Reduce leaves per epoch (close more often)
3. Phase 2 will introduce a dedicated prover sidecar

---

## Upgrades

### Polaris version upgrade

```bash
# Standard path
./scripts/polaris-deploy.sh prod
```

This pulls the latest commit, rebuilds the app image, runs schema
migrations idempotently, and recreates the app container with the
new code. The DB volume is preserved; downtime is ~30 seconds.

Always read `CHANGELOG.md` for the version you're upgrading to —
any v8.X with "breaking change" in the notes requires extra steps.

### Postgres version upgrade

Postgres major-version upgrades (e.g., 16 → 17) require an explicit
`pg_upgrade` step. Backup first, then:

```bash
# 1. Backup
./scripts/polaris-backup.sh

# 2. Stop the stack
docker compose -f polaris_web/docker-compose.prod.yml down

# 3. Edit docker-compose.prod.yml: change postgres image tag

# 4. Migrate the volume
docker run --rm -v polaris_pg_data:/var/lib/postgresql/data \
  -v polaris_pg_data_new:/var/lib/postgresql/data_new \
  postgres:17-alpine pg_upgrade --old-datadir=/var/lib/postgresql/data \
                                --new-datadir=/var/lib/postgresql/data_new

# 5. Swap volumes + bring stack back up
./scripts/polaris-deploy.sh prod
```

### TLS certificate renewal

Caddy auto-renews ~30 days before expiry. No manual action needed.
Confirm:

```bash
docker compose -f polaris_web/docker-compose.prod.yml exec caddy \
  caddy list-certs
```

If you ever need to force renewal:

```bash
docker compose -f polaris_web/docker-compose.prod.yml exec caddy \
  caddy reload --config /etc/caddy/Caddyfile
```

---

## Decommissioning

If you ever need to retire a Polaris instance:

1. **Final backup**

   ```bash
   ./scripts/polaris-backup.sh --dest s3://archive-bucket
   ```

2. **Notify dependent verifiers** — anyone consuming
   `/api/federation/*` or `/api/zk/*` needs the migration window.

3. **Set all operators to read-only**

   ```sql
   UPDATE AppUser SET role = 'auditor' WHERE role != 'auditor';
   ```

4. **Stop accepting new tokens** by deactivating issuer agencies:

   ```sql
   UPDATE Agency SET is_active = FALSE;
   ```

5. **Cool-down window** (recommended 30 days) — verifications
   continue working; no new issuance.

6. **Final audit export**

   ```bash
   pg_dump -Fc polaris -t TokenLifecycleEvent -t VerificationEvent \
     -t AuthAuditLog -t DuressEvent -t AnchorBatch \
     -t AgencyTrustAttestation -f final-audit-$(date +%Y%m%d).dump
   ```

7. **Tear down**

   ```bash
   docker compose -f polaris_web/docker-compose.prod.yml down -v
   ```

8. **Preserve audit volumes** — `pg_data` should be archived per
   your retention policy. The audit-of-record discipline (v8.20)
   requires that these never be destroyed without a documented
   sunset decision.

---

## Pre-commit hooks (v9.06)

**Source:** v9.06 / Wave 2 / G1 ships `.pre-commit-config.yaml` at
the repo root.

The polaris-self-roadmap-2026-05-14 macro-to-micro scan caught
multiple drift classes that would have been prevented by pre-commit
hooks: venv-pollution in ant walkers, stale POLARIS_VERSION, the
F5-soldier-exemption violation. v9.06 closes that gap with a
local-hooks pre-commit configuration that runs before every push.

### Install (one-time per clone)

```bash
# Install pre-commit in the dev venv
pip install pre-commit

# Wire the hooks into .git/hooks/pre-commit
pre-commit install
```

### What runs on every commit

| Hook | Speed | What it catches |
|------|-------|-----------------|
| ai-link-check | ~2s | Broken Markdown / cross-ref links |
| ai-meta | ~3s | Cognitive-layer self-monitoring drift (CM constraint) |
| ai-coherence | ~5s | Structural ↔ codebase coherence (larping detector) |
| structural-invariants | ~25s | Full TestStructural… suite (only on .py/.sh/.sql/.md/.yml/.yaml changes) |
| g28-no-sensitive-env-in-prod-compose | <1s | POLARIS_SECRET_KEY: literal in production compose |
| em-dash-warn | <1s | Em-dash in own-prose docs (informational) |

### Manual run

```bash
pre-commit run --all-files
```

### CI is the safety net

Pre-commit hooks are the operator's local safety net. CI
(`.github/workflows/ci.yml`) runs the FULL suite on every push +
PR; pre-commit hooks are a fast subset that catches the highest-
impact drifts before code leaves the local clone.

### Why local-hooks (not third-party repos)

Polaris is currently in a "git-or-no-git" Sanctum-class decision
(roadmap C2 / Wave 3). Local hooks work whether or not the repo is
git-initialized. Once C2 is decided, this configuration may add
upstream `repos:` entries (ruff, black, etc. — at operator discretion).

---

## What this document does NOT cover

- Application code internals — `CLAUDE.md`, `DEVNOTES/`
- Cryptographic algorithm choice — `docs/operator/SECURITY.md`
- Schema design — `docs/reference/DATA-MODEL.md`
- Threat model — `DEVNOTES/threat-model.md`
- API reference — `docs/reference/API.md`
- Privacy posture — `docs/operator/PRIVACY.md`
- Multi-region deployment — Arc B Phase 3 (deferred)
- Disaster recovery RPO/RTO targets — Arc B Phase 3 (deferred)
- SOC 2 readiness checklist — Arc B Phase 3 (deferred)
- WebAuthn + hardware-token operator auth — Arc B Phase 2 (deferred)

---

*Last updated under v8.77 / Arc B Phase 1.*
