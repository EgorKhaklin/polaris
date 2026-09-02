# Polaris — Deployment Guide

**One page. Three deployment paths. Security defaults documented.**

---

## Path 1: Docker Compose (fastest)

```bash
cd polaris_web
docker compose up
```

Postgres 16 + schema + sample data + Flask app on port 5000 in ~30 seconds.
Reset with `docker compose down -v`. CLI via `docker compose exec app python3 ../polaris_cli/polaris.py health`. Default seed accounts: `admin / Admin@123!`, `operator / Operator@123!`, `auditor / Auditor@123!` (rotate immediately).

> **For development on macOS, prefer the launcher:** the bundled
> `polaris_mac_launch.sh` (or double-clickable `Polaris.command`)
> wraps `docker compose` with self-healing for stale-volume drift,
> auto-start of Docker Desktop, port preflight, watch mode that tears
> the stack down on browser close, a `doctor` diagnostic, and a `nuke`
> reset. Default port is `2222` (avoiding macOS AirPlay Receiver on 5000).
> Run `./polaris_mac_launch.sh --help` for the full subcommand list.

## Path 2: Local Python (development)

```bash
sudo apt install postgresql-16
sudo -u postgres createdb polaris_test
cd polaris_sql && psql -d polaris_test -f 00_load_all.sql      # loads schema + auth
cd ../polaris_web && bash setup.sh                              # creates polaris_app
pip3 install --break-system-packages flask psycopg2-binary gunicorn
python3 app.py                                                  # http://localhost:5000
```

## Path 3: Production (a Linux server under systemd)

The production path is the compose stack behind the Caddy TLS edge, owned by
systemd, installed by one script on a fresh Debian, Ubuntu, or RHEL-family host:

```bash
git clone https://github.com/EgorKhaklin/polaris-id.git /opt/polaris
sudo POLARIS_DOMAIN=polaris.example.org /opt/polaris/deploy/linux/install.sh
```

Everything about it, including what is installed, day-2 commands, upgrades, and
uninstall, is in [`LINUX-SERVER.md`](LINUX-SERVER.md); the operating system
around it is [`HARDENING.md`](HARDENING.md). The earlier native path on this page
(a host Postgres, gunicorn under systemd, nginx with certbot) was retired in
v9.176: it bypassed the container hardening, the pgbouncer and postgres TLS
hops, pgBackRest, and the secrets layout that the rest of these docs assume.
The seeded accounts still apply and must be rotated on first login (below).

---

## Security Environment Variables

| Variable                       | Purpose                                                                                                          | Default      |
|--------------------------------|------------------------------------------------------------------------------------------------------------------|--------------|
| `POLARIS_ENV`                  | When `production`, refuses to start with default secret key                                                      | unset        |
| `POLARIS_SECRET_KEY`           | Session signing key (32-byte hex). MUST be rotated before prod                                                   | dev fallback |
| `POLARIS_COOKIE_SECURE`        | When `1`, session cookie sent only over HTTPS                                                                    | unset        |
| `POLARIS_HSTS`                 | When `1`, sends Strict-Transport-Security header                                                                 | unset        |
| `POLARIS_TRUST_PROXY`          | When `1`, honors X-Forwarded-For for client IP                                                                   | unset        |
| `POLARIS_DB_PASSWORD`          | polaris_app role password — rotate from dev default                                                              | dev fallback |
| `POLARIS_APP_PASSWORD`         | (Docker init only) New polaris_app password — must be ≥16 chars w/ digit+letter+symbol                           | unset        |
| `POLARIS_RATE_LIMIT_BACKEND`   | `auto` / `memory` / `redis`. `auto` picks Redis when `POLARIS_REDIS_URL` is set, otherwise in-memory             | `auto`       |
| `POLARIS_REDIS_URL`            | Redis URL (e.g. `redis://127.0.0.1:6379/0`). REQUIRED for accurate per-IP rate limiting when `POLARIS_WORKERS>1` | unset        |
| `POLARIS_WORKERS`              | Gunicorn worker count. `gunicorn.conf.py` re-exports the resolved value so security.py sees it                   | 4 (gunicorn) |
| `POLARIS_NETWORK_POLICY_<ROLE>` | v9.189. Comma-separated CIDRs/addresses the role (ADMIN/OPERATOR/AUDITOR) may log in from and keep a session on; evaluated on the proxy-aware client address. A malformed value refuses the boot | unset (any) |
| `POLARIS_SESSION_MAX_<ROLE>`   | v9.189. Concurrent live sessions per account; 0 = unlimited. The least-recently-seen seat is evicted (audited `SESSION_EVICTED`) | ADMIN 3, others 0 |
| `POLARIS_SESSION_IDLE_MINUTES_<ROLE>` | v9.189. Idle timeout for the role's sessions; 0 = none. The 8h absolute lifetime always applies | ADMIN 30, others 0 |
| `POLARIS_RATE_LIMIT_WRITE_MAX` / `POLARIS_RATE_LIMIT_WRITE_WINDOW` / `POLARIS_RATE_LIMIT_LOGIN_MAX` | v9.191. Override the F-03 per-IP limits (60 writes per 60 s; 10 logins per 60 s). Exists for the performance baseline's scratch server; raising them in production lowers brute-force and flood resistance and should be justified in `polaris.env` | 60 / 60 / 10 |
| `POLARIS_WEBAUTHN_ATTESTATION` | v9.189. Attestation conveyance asked of the browser at enrollment: `none` / `indirect` / `direct` / `enterprise` | `none` |
| `POLARIS_WEBAUTHN_USER_VERIFICATION` | v9.189. `preferred` / `required` / `discouraged`; `required` demands PIN or biometric on enrollment AND every assertion | `preferred` |
| `POLARIS_WEBAUTHN_REQUIRE_ATTESTATION` | v9.189. When `1`, an enrollment whose attestation format is `none` is refused (audited `WEBAUTHN_REGISTRATION_REFUSED`) | unset |
| `POLARIS_WEBAUTHN_ALLOWED_AAGUIDS` | v9.189. Comma-separated authenticator model AAGUIDs; any other model is refused at enrollment (meaningful with `direct` attestation) | unset (any) |

### Rate-limiter backend (R8-2 / v7.5)

The login + write rate limiter (CWE-307 / CWE-770 mitigation) has two backends:

- **`memory`** — per-process sliding window. Correct for single-worker
  deployments (`POLARIS_WORKERS=1`, `flask run`, dev). With multiple gunicorn
  workers each holds its own bucket, so the *effective* per-IP cap becomes
  `workers × configured`. The app logs a startup warning to stderr when this
  configuration is detected.

- **`redis`** — atomic sliding window backed by a Redis sorted set and a
  Lua script. All workers share the same per-key counter. `RedisRateLimiter`
  fails closed (denies on Redis error) per OWASP "fail securely" — so a
  Redis hiccup will return 429s rather than silently bypass the limiter.
  Operators must monitor `/api/health` (the `rate_limiter` block) and treat
  sustained `ok: false` as a paging condition.

**Production checklist:**

1. Set `POLARIS_REDIS_URL` to your Redis endpoint.
2. Verify backend selection: `curl -s http://localhost:5000/api/health | jq .checks.rate_limiter` should show `{"backend": "redis", "ok": true}`.
3. If Redis becomes unreachable mid-flight, `/api/health` returns `degraded`. Page on `degraded` for over 60 s.
4. For development without Redis, leave `POLARIS_REDIS_URL` unset and run a single worker (`POLARIS_WORKERS=1` or `python3 app.py`); the in-memory backend is correct.

## Default Application Accounts (DEV ONLY — ROTATE IN PROD)

| Username   | Password         | Role     | Capability                                         |
|------------|------------------|----------|----------------------------------------------------|
| `admin`    | `Admin@123!`     | admin    | Full CRUD, all use cases, SQL console, transitions |
| `operator` | `Operator@123!`  | operator | Issue/activate/bind tokens, record verifications   |
| `auditor`  | `Auditor@123!`   | auditor  | Read-only + UC-7 warrant audits + SQL console      |

After successful rotation, log in once with each new password to confirm; the `LOGIN_SUCCESS` events will appear in `AuthAuditLog`.

---

## Verification

```bash
curl -fsS https://polaris.example.gov/login | grep -q POLARIS && echo OK   # Web reachable
curl -fsS https://polaris.example.gov/                                    # → 302 /login (auth gate)
sudo -u postgres psql -d polaris_test -f polaris_sql/08_tests.sql          # SQL: 36/36
cd polaris_web && python3 test_app.py                                      # Web: 101/101
cd polaris_cli && python3 test_cli.py                                      # CLI: 28/28
sudo -u polaris polaris health                                             # CLI smoke
```

## Operational

| Concern              | Action                                                              |
|----------------------|---------------------------------------------------------------------|
| Logs                 | `journalctl -u polaris.service -f`                                   |
| Health monitoring    | HTTP 302 on `/` (redirect to /login) means app is up; HTTP 200 on `/login` confirms |
| Database backups     | `pg_dump polaris_test | gzip > polaris_$(date +%F).sql.gz` nightly  |
| Secret rotation      | Update `POLARIS_SECRET_KEY` and restart; sessions invalidate cleanly |
| Auth audit review    | `SELECT event_type, COUNT(*) FROM AuthAuditLog WHERE event_timestamp > NOW() - INTERVAL '24 hours' GROUP BY 1` |
| Suspicious login activity | `SELECT username, ip_address, COUNT(*) FROM AuthAuditLog WHERE event_type='LOGIN_FAILED' AND event_timestamp > NOW() - INTERVAL '1 hour' GROUP BY 1, 2 HAVING COUNT(*) > 3` |

## Troubleshooting

- **`permission denied for table ...`** → polaris_app role missing grants. Run `09_grants.sql`.
- **Login always fails with correct password** → Account may be locked; check `SELECT failed_login_count, locked_until FROM AppUser WHERE username = ?`.
- **CSRF rejections in audit log** → Either a real CSRF attack, OR a session that expired between form render and submit (8-hour lifetime).
- **`Too many requests`** → Rate limiter triggered; default 60 writes/min/IP. Adjust in `security.py` or wait 60s. With multiple workers, confirm via `/api/health` that you are running the Redis backend; the in-memory backend silently multiplies the cap by worker count.
- **Sustained `degraded` from /api/health (rate_limiter)** → Redis unreachable. The limiter is failing closed (every login/write returns 429). Restore Redis or set `POLARIS_RATE_LIMIT_BACKEND=memory` as an emergency stopgap; remember the cap multiplication when you do.
- **Atlas page slow** → Run `ANALYZE` or check that the indexes from `02_indexes.sql` were created.
- **SQL console "timed out"** → 5s `statement_timeout` fired. Add `LIMIT`, narrow the WHERE clause.

---

*Polaris Identity Token System · Schema v1.0 · Fixus inter mutabilia*
