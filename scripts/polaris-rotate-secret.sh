#!/usr/bin/env bash
# ============================================================================
# polaris-rotate-secret.sh — rotate a single secret in place
#
# Arc B Phase 1 (v8.77). Replaces a secret file under polaris_web/secrets/,
# archives the previous version under polaris_web/secrets/.archive/ (mode
# 0600 so an operator can investigate if a rotation breaks production), and
# bumps the affected component(s).
#
# Usage:
#     ./scripts/polaris-rotate-secret.sh polaris_secret_key
#     ./scripts/polaris-rotate-secret.sh polaris_db_password
#     ./scripts/polaris-rotate-secret.sh polaris_db_root_password
#
# Effects per secret:
#   polaris_secret_key           — recreates app container (sessions invalidated)
#   polaris_db_password          — rotates polaris_app password in DB, recreates app
#   polaris_db_root_password     — rotates postgres superuser password, recreates postgres
#
# Cadence + threat model: docs/operator/SECRETS.md
# ============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"
POLARIS_ROOT="$(cd -- "${SCRIPT_DIR}/.." &> /dev/null && pwd)"
SECRETS_DIR="${POLARIS_ROOT}/polaris_web/secrets"
ARCHIVE_DIR="${SECRETS_DIR}/.archive"
COMPOSE_FILE="${POLARIS_ROOT}/polaris_web/docker-compose.prod.yml"

if [[ $# -ne 1 ]]; then
    echo "usage: $(basename "$0") <secret-name>" >&2
    echo "       valid names: polaris_secret_key | polaris_db_password | polaris_db_root_password" >&2
    exit 2
fi
SECRET="$1"

case "${SECRET}" in
    polaris_secret_key|polaris_db_password|polaris_db_root_password) ;;
    *)
        echo "error: unknown secret '${SECRET}'" >&2
        exit 2
        ;;
esac

TARGET="${SECRETS_DIR}/${SECRET}"
if [[ ! -f "${TARGET}" ]]; then
    echo "error: ${TARGET} does not exist; run polaris-generate-secrets.sh first" >&2
    exit 1
fi

mkdir -p "${ARCHIVE_DIR}"
chmod 0700 "${ARCHIVE_DIR}"

TS=$(date -u +%Y%m%dT%H%M%SZ)
ARCHIVE_PATH="${ARCHIVE_DIR}/${SECRET}.${TS}"

# Archive the prior secret (mode 0600).
cp "${TARGET}" "${ARCHIVE_PATH}"
chmod 0600 "${ARCHIVE_PATH}"

# Generate replacement (32 random bytes -> 64 hex chars).
gen_hex() {
    if command -v openssl >/dev/null 2>&1; then
        openssl rand -hex 32
    else
        python3 -c "import secrets; print(secrets.token_hex(32))"
    fi
}
NEW_VALUE=$(gen_hex)

# Write replacement atomically (mv preserves the file as 0600).
( umask 0177 && printf '%s\n' "${NEW_VALUE}" > "${TARGET}.new" )
chmod 0600 "${TARGET}.new"
mv "${TARGET}.new" "${TARGET}"

echo "  ✓ rotated ${SECRET} (previous archived at ${ARCHIVE_PATH})"

# Apply the rotation to the running stack.
if ! command -v docker >/dev/null 2>&1; then
    echo "  ! docker not on PATH — secret file rotated but stack not reloaded" >&2
    exit 0
fi

if ! docker compose -f "${COMPOSE_FILE}" ps --status running --quiet 2>/dev/null | grep -q .; then
    echo "  • stack not running; secret will take effect on next 'polaris-deploy.sh prod'"
    exit 0
fi

case "${SECRET}" in
    polaris_secret_key)
        echo "  → recreating app container (all sessions invalidated)…"
        docker compose -f "${COMPOSE_FILE}" up -d --no-deps --force-recreate app
        ;;

    polaris_db_password)
        echo "  → updating polaris_app password in DB…"
        docker compose -f "${COMPOSE_FILE}" exec -T postgres psql -U postgres -d polaris \
            -c "ALTER USER polaris_app WITH PASSWORD '${NEW_VALUE}';"
        echo "  → recreating app container…"
        docker compose -f "${COMPOSE_FILE}" up -d --no-deps --force-recreate app
        ;;

    polaris_db_root_password)
        echo "  → updating postgres superuser password…"
        docker compose -f "${COMPOSE_FILE}" exec -T postgres psql -U postgres -d polaris \
            -c "ALTER USER postgres WITH PASSWORD '${NEW_VALUE}';"
        echo "  → recreating postgres container…"
        docker compose -f "${COMPOSE_FILE}" up -d --no-deps --force-recreate postgres
        ;;
esac

cat <<EOF

  Rotation complete.

  Verify:
    curl -fsS https://\${POLARIS_DOMAIN}/api/health | jq .checks

  If the stack misbehaves, the prior secret is at:
    ${ARCHIVE_PATH}

  Threat model + cadence:  docs/operator/SECRETS.md
EOF
