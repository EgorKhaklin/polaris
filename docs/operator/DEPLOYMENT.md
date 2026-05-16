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

## Path 3: Production (systemd + nginx + TLS + auth)

**1. Provision Postgres** on a hardened host. Restrict `pg_hba.conf` to localhost or VPN. Run `polaris_sql/00_load_all.sql` once (loads schema, sample data, triggers, grants, AppUser/AuthAuditLog).

**2. Rotate the polaris_app role password.** The default `polaris_dev_password` is for development only:
```sql
ALTER ROLE polaris_app WITH PASSWORD '<min-16-chars-letters-digits-symbols>';
```

**3. Rotate the application user passwords.** Generate a real scrypt hash and update the seed accounts:
```python
python3 -c "from werkzeug.security import generate_password_hash; print(generate_password_hash('YourProdPassword!', method='scrypt'))"
```
```sql
UPDATE AppUser SET password_hash = '<the-hash>', failed_login_count=0, locked_until=NULL
 WHERE username IN ('admin', 'operator', 'auditor');
```
Or remove the seeds entirely and create your own via SQL.

**4. Generate a real session secret**:
```bash
python3 -c 'import secrets; print(secrets.token_hex(32))' > /etc/polaris/secret_key
chmod 600 /etc/polaris/secret_key
```

**5. systemd unit** at `/etc/systemd/system/polaris.service`:
```ini
[Unit]
Description=Polaris Identity Token System
After=network.target postgresql.service
Requires=postgresql.service

[Service]
Type=simple
User=polaris
WorkingDirectory=/opt/polaris/web
EnvironmentFile=/etc/polaris/env
ExecStart=/opt/polaris/venv/bin/gunicorn --config gunicorn.conf.py app:app
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

`/etc/polaris/env` (chmod 600, owned by polaris):
```
POLARIS_ENV=production              # refuses to start with default secret_key
POLARIS_DB_HOST=127.0.0.1
POLARIS_DB_NAME=polaris_test
POLARIS_DB_USER=polaris_app
POLARIS_DB_PASSWORD=<strong-password>
POLARIS_SECRET_KEY=<contents of /etc/polaris/secret_key>
POLARIS_COOKIE_SECURE=1             # require HTTPS for session cookie
POLARIS_HSTS=1                      # HSTS header (only after committed to HTTPS-only)
POLARIS_TRUST_PROXY=1               # honor X-Forwarded-For from nginx
POLARIS_WORKERS=4
POLARIS_REDIS_URL=redis://127.0.0.1:6379/0   # required when POLARIS_WORKERS > 1; see Rate Limiter section
```

**6. nginx with TLS** (see `polaris_web/nginx.conf.example`). Get a cert with `certbot --nginx -d polaris.example.gov`.

**7. Start**:
```bash
sudo systemctl daemon-reload
sudo systemctl enable --now polaris.service
sudo systemctl reload nginx
```

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
