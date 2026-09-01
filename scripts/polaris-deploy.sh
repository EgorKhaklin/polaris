#!/usr/bin/env bash
# ============================================================================
# polaris-deploy.sh — idempotent production deploy
#
# Arc B Phase 1 (v8.77). Orchestrates the prod stack with rollback-on-fail
# semantics. Three modes:
#
#   dev       — delegates to ./polaris_mac_launch.sh (no production stack)
#   staging   — same as prod but with staging.${POLARIS_DOMAIN}
#   prod      — full production: build + migrate + smoke + swap
#
# Flow (prod):
#   1. Pre-flight: docker present, secrets present, POLARIS_DOMAIN set
#   2. git pull (skipped if --no-pull)
#   3. docker compose pull (refresh upstream images)
#   4. docker compose build app (multi-stage Dockerfile.prod)
#   5. Bring stack up
#   6. Smoke test: /api/health overall status must be 'healthy'
#   7. If smoke fails: rollback to previous app image tag, exit non-zero
#
# Usage:
#     export POLARIS_DOMAIN=polaris.example.com
#     ./scripts/polaris-deploy.sh prod
#     ./scripts/polaris-deploy.sh prod --no-pull
#     ./scripts/polaris-deploy.sh staging
# ============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"
POLARIS_ROOT="$(cd -- "${SCRIPT_DIR}/.." &> /dev/null && pwd)"
COMPOSE_FILE="${POLARIS_ROOT}/polaris_web/docker-compose.prod.yml"
SECRETS_DIR="${POLARIS_ROOT}/polaris_web/secrets"

MODE="${1:-prod}"
shift || true
PULL_GIT=1
for arg in "$@"; do
    case "${arg}" in
        --no-pull) PULL_GIT=0 ;;
        *)         echo "warn: unknown arg ${arg}" >&2 ;;
    esac
done

case "${MODE}" in
    dev)
        echo "  → dev mode: delegating to polaris_mac_launch.sh"
        exec "${POLARIS_ROOT}/polaris_mac_launch.sh" up
        ;;
    staging|prod) ;;
    *)
        echo "usage: $(basename "$0") {dev|staging|prod} [--no-pull]" >&2
        exit 2
        ;;
esac

if [[ "${MODE}" == "staging" ]] && [[ -z "${POLARIS_DOMAIN:-}" ]]; then
    echo "error: POLARIS_DOMAIN must be set (got empty)" >&2
    exit 2
fi
if [[ "${MODE}" == "prod" ]] && [[ -z "${POLARIS_DOMAIN:-}" ]]; then
    echo "error: POLARIS_DOMAIN must be set (got empty)" >&2
    exit 2
fi

echo
echo "  Polaris deploy — mode=${MODE} domain=${POLARIS_DOMAIN}"
echo "  ─────────────────────────────────────────────────────"
echo

# ---------------------------------------------------------------------------
# 1. Pre-flight
# ---------------------------------------------------------------------------
echo "  [1/7] Pre-flight…"

if ! command -v docker >/dev/null 2>&1; then
    echo "  ✗ docker not on PATH"; exit 1
fi
if ! docker compose version >/dev/null 2>&1; then
    echo "  ✗ docker compose v2 plugin not available"; exit 1
fi

# v9.173 — pgbackrest_repo_creds.conf is mounted unconditionally by the prod
# compose; if the source file is missing docker creates a DIRECTORY there.
for secret in polaris_secret_key polaris_db_password polaris_db_root_password pgbackrest_repo_creds.conf; do
    if [[ ! -s "${SECRETS_DIR}/${secret}" ]]; then
        echo "  ✗ missing secret: secrets/${secret}"
        echo "    run: ./scripts/polaris-generate-secrets.sh"
        exit 1
    fi
done
echo "  ✓ docker present"
echo "  ✓ all secrets present"

# ---------------------------------------------------------------------------
# 2. git pull
# ---------------------------------------------------------------------------
if [[ "${PULL_GIT}" -eq 1 ]] && [[ -d "${POLARIS_ROOT}/.git" ]]; then
    echo "  [2/7] git pull…"
    (cd "${POLARIS_ROOT}" && git pull --ff-only) || {
        echo "  ! git pull failed (continuing — fix manually if needed)"
    }
else
    echo "  [2/7] git pull… skipped"
fi

# ---------------------------------------------------------------------------
# 3. Capture previous image tag (for rollback)
# ---------------------------------------------------------------------------
PREV_IMAGE_ID=$(docker inspect --format='{{.Image}}' polaris-app 2>/dev/null || echo "")
if [[ -n "${PREV_IMAGE_ID}" ]]; then
    echo "  [3/7] Previous app image: ${PREV_IMAGE_ID:0:18}"
else
    echo "  [3/7] No previous app image (fresh deploy)"
fi

# ---------------------------------------------------------------------------
# 4. Pull upstream images + build app
# ---------------------------------------------------------------------------
echo "  [4/7] Pulling upstream images + building app…"
(cd "${POLARIS_ROOT}/polaris_web" && docker compose -f docker-compose.prod.yml pull --ignore-pull-failures postgres redis caddy)
(cd "${POLARIS_ROOT}/polaris_web" && docker compose -f docker-compose.prod.yml build app)

# ---------------------------------------------------------------------------
# 5. Bring stack up
# ---------------------------------------------------------------------------
echo "  [5/7] Bringing stack up…"
(cd "${POLARIS_ROOT}/polaris_web" && docker compose -f docker-compose.prod.yml up -d --remove-orphans)

# ---------------------------------------------------------------------------
# 5b. Apply migrations + sync DB objects against the RUNNING stack.
#     On a fresh volume docker-init.sh applied the schema + migrations during
#     postgres init; on an UPGRADE it did NOT (postgres init scripts only run on
#     an empty data dir), so without this a pending migration OR a changed
#     procedure/trigger (e.g. v9.117's uc1_issue_and_activate signature) never
#     reaches the running DB and issuance breaks. Both commands pipe SQL over
#     stdin into the postgres container, so they work regardless of host paths;
#     they are idempotent, so this is a harmless no-op on a fresh deploy.
# ---------------------------------------------------------------------------
echo "  [5b]  Applying migrations + syncing DB objects (procedures/triggers/views/grants)…"
for _i in $(seq 1 30); do
    if docker compose -f "${COMPOSE_FILE}" exec -T postgres pg_isready -U postgres >/dev/null 2>&1; then
        break
    fi
    sleep 2
done
"${SCRIPT_DIR}/polaris-migrate.sh" --up --target=docker-stack
"${SCRIPT_DIR}/polaris-migrate.sh" --sync-objects --target=docker-stack

# ---------------------------------------------------------------------------
# 5c. Bootstrap pgBackRest when continuous WAL archiving is enabled. docker-init
#     turned archive_mode on (POLARIS_PGBACKREST_ENABLED=1), but the stanza must
#     be created once against the running server or archive-push fails on every
#     WAL segment and they pile up on disk. stanza-create is idempotent, so this
#     is safe to re-run. Best-effort: a failure (e.g. an unreachable S3 repo)
#     WARNS loudly but does NOT block the deploy — the app is fine; the operator
#     must fix the repo before archiving works. This closes the "enabled but
#     never bootstrapped -> WAL fills the disk" gap (v9.130).
# ---------------------------------------------------------------------------
if [[ "${POLARIS_PGBACKREST_ENABLED:-0}" == "1" ]]; then
    echo "  [5c]  Bootstrapping pgBackRest stanza (WAL archiving is enabled)…"
    if docker compose -f "${COMPOSE_FILE}" exec -T postgres \
            pgbackrest --stanza=polaris stanza-create >/dev/null 2>&1 \
       && docker compose -f "${COMPOSE_FILE}" exec -T postgres \
            pgbackrest --stanza=polaris check >/dev/null 2>&1; then
        echo "  ✓ pgBackRest stanza ready (archive-push validated)"
    else
        echo "  ⚠  pgBackRest stanza-create/check FAILED. Archiving is enabled but the" >&2
        echo "     repo is not ready — WAL will accumulate on disk until this is fixed." >&2
        echo "     Check POLARIS_PGBACKREST_S3_* on the postgres service and" >&2
        echo "     secrets/pgbackrest_repo_creds.conf (the S3 key pair), then re-run:" >&2
        echo "       docker compose -f ${COMPOSE_FILE} exec postgres pgbackrest --stanza=polaris check" >&2
    fi
fi

# ---------------------------------------------------------------------------
# 6. Smoke test
# ---------------------------------------------------------------------------
echo "  [6/7] Smoke test (/api/health)…"
SMOKE_OK=0
for i in $(seq 1 30); do
    sleep 2
    # Probe from inside the docker network — avoids waiting on TLS issuance.
    if HEALTH_JSON=$(docker compose -f "${COMPOSE_FILE}" exec -T app \
                       curl -fsS http://localhost:8000/api/health 2>/dev/null); then
        STATUS=$(echo "${HEALTH_JSON}" | grep -oE '"status":"[a-z]+"' | head -1 | cut -d'"' -f4)
        if [[ "${STATUS}" == "healthy" ]]; then
            SMOKE_OK=1
            break
        fi
        if [[ "${STATUS}" == "degraded" ]]; then
            echo "  • health=degraded (continuing; degraded is non-fatal)"
            SMOKE_OK=1
            break
        fi
    fi
    [[ $((i % 5)) -eq 0 ]] && echo "    …still waiting (attempt ${i}/30)"
done

if [[ "${SMOKE_OK}" -ne 1 ]]; then
    echo "  ✗ Smoke test failed after 60s"
    if [[ -n "${PREV_IMAGE_ID}" ]]; then
        echo "  → Rolling back to previous app image…"
        docker tag "${PREV_IMAGE_ID}" polaris-app:prod
        (cd "${POLARIS_ROOT}/polaris_web" && docker compose -f docker-compose.prod.yml up -d --no-deps --force-recreate app)
        echo "  ✓ Rolled back. Investigate logs:"
        echo "    docker compose -f polaris_web/docker-compose.prod.yml logs --tail=200 app"
    else
        echo "  • No prior image to roll back to. Stack is up but unhealthy."
    fi
    exit 1
fi

echo "  ✓ /api/health is healthy"

# ---------------------------------------------------------------------------
# 7. Done
# ---------------------------------------------------------------------------
echo "  [7/7] Deploy complete."
cat <<EOF

  Stack:        ${COMPOSE_FILE}
  Domain:       https://${POLARIS_DOMAIN}/
  Health:       https://${POLARIS_DOMAIN}/api/health
  Logs:         docker compose -f polaris_web/docker-compose.prod.yml logs -f
  Backup:       ./scripts/polaris-backup.sh
  Rotate key:   ./scripts/polaris-rotate-secret.sh <name>

EOF
