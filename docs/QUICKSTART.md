# Polaris quickstart — clone to running stack in 90 seconds

**Audience:** an operator who has never deployed Polaris before.
**Goal:** get the stack running locally; verify the audit-of-record
substrate; understand what's running.
**Total time:** 90 seconds for the happy path; +5 minutes for the
verification walkthrough.

Polaris is a national identity token system reference implementation.
It is built to demonstrate that the ten hard constraints (C1–C10)
are not policies — they are enforced at the database level via
triggers, CHECK constraints, partial unique indexes, and append-only
audit trails. The first thing you should see after a clean deploy is
the system refusing to violate its own constraints.

---

## Prerequisites

- macOS or Linux host
- Docker + Docker Compose
- 4 GB free RAM
- 5 GB free disk

For development against the codebase (running the test suite, editing
the SQL schema), additionally:

- Python 3.10+ with `psycopg2` and `pytest`
- Postgres 16 client tools
- Rust toolchain (only for the ZK-SNARK prover crate;
  optional)

---

## The 90-second path

```bash
git clone <polaris repo url> && cd polaris
./scripts/polaris-generate-secrets.sh        # writes .env
export POLARIS_DOMAIN=localhost              # for local-only; production uses your real domain
./scripts/polaris-deploy.sh prod             # brings up Caddy + Postgres + Redis + gunicorn
curl -fsS http://localhost/api/health | jq .
```

Within ~90 seconds, `/api/health` should return structured per-
component status. If it doesn't, read the next section.

### What `polaris-deploy.sh prod` does

- Builds the Docker image from `Dockerfile.prod`
- Brings up `docker-compose.prod.yml` which orchestrates:
  - Caddy (TLS terminator + reverse proxy)
  - Postgres 16 (the durable state)
  - Redis (rate-limiter backend + session cache)
  - gunicorn × N workers serving `polaris_web/app.py`
- Runs `docker-init.sh` which:
  - Loads the schema from `polaris_sql/00_load_all.sql`
  - Applies every migration in `polaris_sql/migrations/*.up.sql`
    (since v9.18 fix)
  - Seeds demo data (`polaris_sql/04_data.sql`)
- Waits for `/api/health` to return 200

---

## First-time login

Once the stack is up:

1. Open `http://localhost/` (or your `POLARIS_DOMAIN`)
2. Click "Sign in" or visit `/login`
3. Credentials: `admin` / `Admin@123!` (demo seed; CHANGE THIS in
   production)
4. Land on `/dashboard`

Demo accounts (seeded in `04_data.sql`):
- `admin` / `Admin@123!` — admin role
- `operator` / `Operator@123!` — operator role
- `auditor` / `Auditor@123!` — auditor role (read-only)

**Production checklist before exposing to the internet:**
- [ ] Change all three demo passwords (`UPDATE AppUser SET ...`)
- [ ] Set `webauthn_required_after` for admin/operator accounts via
      `scripts/polaris-set-webauthn-deadline.sh` (per
      `docs/operator/WEBAUTHN-ROLLOUT.md`)
- [ ] Set `POLARIS_DOMAIN` to your real domain
- [ ] Confirm Caddy provisions Let's Encrypt TLS
- [ ] Configure backup destination + cron via
      `scripts/polaris-cron-install.sh` (v9.23)
- [ ] Review `SECURITY.md` for vulnerability disclosure setup

---

## Verify the audit-of-record substrate

The thing that makes Polaris different is that the audit trail is
enforced, not requested. Verify this:

```bash
# Connect to the running database
docker compose -f polaris_web/docker-compose.prod.yml exec postgres \
    psql -U polaris -d polaris

# Attempt to UPDATE an audit row (should be refused by trigger)
UPDATE TokenLifecycleEvent SET created_at = NOW()
WHERE event_id = (SELECT min(event_id) FROM TokenLifecycleEvent);
-- ERROR: TokenLifecycleEvent is append-only (trigger trg_tle_no_update)

# Attempt to DELETE an audit row (should be refused by trigger)
DELETE FROM TokenLifecycleEvent
WHERE event_id = (SELECT min(event_id) FROM TokenLifecycleEvent);
-- ERROR: TokenLifecycleEvent is append-only (trigger trg_tle_no_delete)

# Attempt a second ACTIVE token for the same individual (should be refused)
INSERT INTO IdentityToken (individual_id, status, ...)
SELECT individual_id, 'ACTIVE', ...
FROM IdentityToken WHERE status='ACTIVE' LIMIT 1;
-- ERROR: duplicate key value violates unique constraint
--        "uq_one_active_token_per_individual" (the partial unique index)
```

Each of these refusals is C1 (audit-of-record) and C3 (one-identity-
per-person) enforced at the database level. The application code
*cannot* bypass these constraints without DDL.

---

## Explore the interface

| URL                          | What you see |
|------------------------------|--------------|
| `/`                          | Landing page (public) |
| `/demo`                      | Live walk-through of issue → verify → revoke |
| `/atlas`                     | World-map view of token distribution |
| `/individuals`               | List of individuals (logged-in only) |
| `/tokens`                    | List of tokens with state filters |
| `/verifications`             | List + form for recording verifications |
| `/investigate/token/<id>`    | Object Card for a single token (v9.19) |
| `/investigate/individual/<id>` | Object Card for a single individual (v9.19) |
| `/sql`                       | Authenticated SQL console (admin only) |
| `/dashboard`                 | Per-user dashboard |
| `/api/health`                | Structured health JSON |

For first-time exploration: walk the `/demo` route, then click through
the dashboard and atlas. The investigative routes (v9.19) are the
single-entity-focused inspection UX; they were built specifically to
NOT support cross-individual link analysis (that pattern would be a
surveillance primitive and is structurally refused).

---

## Understand what's running

The Polaris codebase has three concentric layers:

1. **Cognitive layer** (root + `scripts/` + `meta/` + `journal/`):
   the system's reward function (`MISSION.md`), the active backlog
   (`ROADMAP.md`), the agent runbook (`CLAUDE.md`), and the scripts
   that orchestrate sessions. If you're going to operate Polaris,
   read `CLAUDE.md` first — it's the agent runbook, but doubles as a
   developer onboarding doc.
2. **Knowledge layer** (`DEVNOTES/`, `patterns/`, `meta/`): durable
   memory — what races exist, what bit the developer last quarter,
   the canonical recipe for a new Flask route.
3. **Reference + source layer** (`docs/`, `polaris_sql/`,
   `polaris_web/`, `polaris_cli/`): operator/architect docs and the
   actual source tree.

Run `bash scripts/ai-prime.sh` to get an ≤80-line primer on current
state. It tells you what just shipped, what's in the active backlog,
what's recently modified.

---

## Operate it

| Need                                        | Run                                          |
|---------------------------------------------|----------------------------------------------|
| Daily backup                                | `polaris-backup.sh` (or cron — see polaris-cron-install.sh) |
| Restore from backup                         | `polaris-restore.sh` (see DR-SINGLE-REGION.md) |
| Unlock a locked-out admin                   | `polaris-recover-admin.sh` (see WEBAUTHN-ROLLOUT.md) |
| Set WebAuthn enforcement deadline           | `polaris-set-webauthn-deadline.sh` (v9.23)  |
| Rotate secrets                              | `polaris-rotate-secret.sh`                  |
| Archive audit-log rows to cold storage      | `polaris-archive.sh` (export-only; C1 preserved) |
| Generate emergency recovery code            | `polaris-generate-recovery-code.sh`         |
| Install full backup + archive crontab       | `polaris-cron-install.sh` (v9.23)           |
| Run health check                            | `curl http://localhost/api/health \| jq .`  |
| Deploy to production                        | `polaris-deploy.sh prod`                    |
| Tear down stack                             | `docker compose -f polaris_web/docker-compose.prod.yml down` |

For each of these, the script's `--help` flag explains the available
flags + when to use them. There is no flag that requires reading the
source code first; the scripts are self-explanatory.

---

## When things break

```bash
# First: check /api/health for structured per-component status
curl -fsS http://localhost/api/health | jq .

# Logs (production stack)
docker compose -f polaris_web/docker-compose.prod.yml logs --tail=200 gunicorn
docker compose -f polaris_web/docker-compose.prod.yml logs --tail=200 postgres

# If WebAuthn is locking you out — see WEBAUTHN-ROLLOUT.md recovery
./scripts/polaris-recover-admin.sh --target $LOCKED_USERNAME

# If the entire stack is unhealthy — restart
./scripts/polaris-deploy.sh prod --force-recreate

# If data integrity is in doubt — restore from backup
./scripts/polaris-restore.sh /var/backups/polaris-{latest}.tar.gz \
    --target=docker-stack
```

`DEVNOTES/known-gotchas.md` catalogs every weirdness the developer
has hit; check there before assuming a new bug.

---

## Where to go next

- **Architect's view of the system:** `docs/ARCHITECTURE-OVERVIEW.md`
  (v9.23 companion to this document)
- **Constitutional design:** `MISSION.md`
- **Operator runbook in depth:** `docs/operator/OPERATIONS.md`
- **Backup/restore:** `docs/operator/DR-SINGLE-REGION.md`
- **WebAuthn rollout:** `docs/operator/WEBAUTHN-ROLLOUT.md`
- **Security disclosure:** `SECURITY.md`
- **Contributing:** `CONTRIBUTING.md`
- **Cognitive layer architecture:** `meta/cognitive-loop.md`

---

*Per BIG MISSION Sanctum, 2026-05-15. v9.23.*
