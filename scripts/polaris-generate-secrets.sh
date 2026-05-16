#!/usr/bin/env bash
# ============================================================================
# polaris-generate-secrets.sh — one-time secret material generation
#
# Arc B Phase 1 (v8.77). Generates the file-mounted secrets the production
# docker-compose stack expects under polaris_web/secrets/. Refuses to
# overwrite existing files (rotation lives in polaris-rotate-secret.sh).
#
# Files generated (all mode 0600):
#   secrets/polaris_secret_key          — Flask session signing key (64 hex)
#   secrets/polaris_db_password         — Postgres polaris_app password (32+ chars)
#   secrets/polaris_db_root_password    — Postgres superuser password (32+ chars)
#
# G28 enforced: nothing here echoes secrets to stdout. The file mode is
# verified after write.
# ============================================================================

set -euo pipefail

# Resolve the polaris root from this script's location.
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"
POLARIS_ROOT="$(cd -- "${SCRIPT_DIR}/.." &> /dev/null && pwd)"
SECRETS_DIR="${POLARIS_ROOT}/polaris_web/secrets"

mkdir -p "${SECRETS_DIR}"
chmod 0700 "${SECRETS_DIR}"

# Pick a random-source command in order of preference.
gen_hex() {
    local nbytes="$1"
    if command -v openssl >/dev/null 2>&1; then
        openssl rand -hex "${nbytes}"
    elif command -v python3 >/dev/null 2>&1; then
        python3 -c "import secrets; print(secrets.token_hex(${nbytes}))"
    else
        # Fall back to /dev/urandom + hex via xxd or od.
        if command -v xxd >/dev/null 2>&1; then
            head -c "${nbytes}" /dev/urandom | xxd -p -c 1024
        else
            head -c "${nbytes}" /dev/urandom | od -An -tx1 | tr -d ' \n'
        fi
    fi
}

write_secret_if_missing() {
    local name="$1"
    local hex_bytes="$2"
    local target="${SECRETS_DIR}/${name}"

    if [[ -e "${target}" ]]; then
        echo "  ✓ ${name}  (exists; not overwriting — use polaris-rotate-secret.sh to rotate)"
        return 0
    fi

    # Use umask so the file is born 0600 even before chmod.
    ( umask 0177 && gen_hex "${hex_bytes}" > "${target}" )
    chmod 0600 "${target}"

    # Verify mode actually took.
    local mode
    if mode=$(stat -f '%Lp' "${target}" 2>/dev/null); then :;
    else mode=$(stat -c '%a' "${target}" 2>/dev/null || echo "?"); fi
    if [[ "${mode}" != "600" ]]; then
        echo "  ✗ ${name}  (mode is ${mode}, expected 600 — fix manually)" >&2
        return 1
    fi
    echo "  ✓ ${name}  (generated; mode 0600)"
}

cat <<'BANNER'

  Polaris — secret material generator
  ───────────────────────────────────
  Generating file-mounted secrets under polaris_web/secrets/.
  This script will NOT overwrite existing secrets.

BANNER

write_secret_if_missing polaris_secret_key       32
write_secret_if_missing polaris_db_password      24
write_secret_if_missing polaris_db_root_password 24

cat <<BANNER

  Done.

  Next steps:
    1. export POLARIS_DOMAIN=<your domain>
    2. ./scripts/polaris-deploy.sh prod
    3. curl -fsS https://\${POLARIS_DOMAIN}/api/health | jq .

  Rotation:    ./scripts/polaris-rotate-secret.sh <name>
  Threat model & rotation cadence:  docs/operator/SECRETS.md

BANNER
