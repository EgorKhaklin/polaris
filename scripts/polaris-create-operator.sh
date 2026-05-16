#!/usr/bin/env bash
# ============================================================================
# polaris-create-operator.sh — onboard a new operator account
#
# v8.93 / Phase 2 closing-list item. Closes the gap surfaced by the
# v8.92 deployability checklist: creating an AppUser was previously
# manual SQL (fragile + error-prone + bypassed the audit log).
#
# What it does:
#   1. Validates the requested username + role
#   2. Refuses to overwrite an existing account (idempotency)
#   3. Reads the password from stdin or --password-file (never argv)
#   4. Computes the werkzeug scrypt hash (matches security.py:hash_password)
#   5. INSERTs into AppUser with the hash + role + is_active=TRUE
#   6. Writes an ACCOUNT_CREATED entry to AuthAuditLog
#
# Usage:
#   ./scripts/polaris-create-operator.sh --username NAME --role ROLE [options]
#
#   --username NAME            lowercase, 3-50 chars, [a-z0-9._-]
#   --role admin|operator|auditor
#   --password-file PATH       read password from file (preferred)
#   --target=docker-stack      use the running docker compose Postgres
#   --dry-run                  validate + report; no INSERT issued
#
# If --password-file is omitted, the script prompts on stdin (no echo).
#
# Exit codes:
#   0  account created
#   2  usage error
#   3  validation error (username format / role enum)
#   4  account already exists (refuse to clobber)
#   5  database call failed
# ============================================================================

set -euo pipefail

EXIT_OK=0
EXIT_USAGE=2
EXIT_VALIDATION=3
EXIT_EXISTS=4
EXIT_DB=5

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"
POLARIS_ROOT="$(cd -- "${SCRIPT_DIR}/.." &> /dev/null && pwd)"
COMPOSE_FILE="${POLARIS_ROOT}/polaris_web/docker-compose.prod.yml"

USERNAME=""
ROLE=""
PASSWORD_FILE=""
USE_DOCKER_STACK=0
DRY_RUN=0

while [[ $# -gt 0 ]]; do
    case "$1" in
        --username=*)       USERNAME="${1#--username=}" ;;
        --username)         shift; USERNAME="${1:-}" ;;
        --role=*)           ROLE="${1#--role=}" ;;
        --role)             shift; ROLE="${1:-}" ;;
        --password-file=*)  PASSWORD_FILE="${1#--password-file=}" ;;
        --password-file)    shift; PASSWORD_FILE="${1:-}" ;;
        --target=docker-stack) USE_DOCKER_STACK=1 ;;
        --dry-run)          DRY_RUN=1 ;;
        --help|-h)
            sed -n '2,30p' "$0" | sed 's/^# \{0,1\}//'
            exit "${EXIT_USAGE}"
            ;;
        *) echo "warn: unknown arg $1" >&2 ;;
    esac
    shift
done

# Validate username + role per the schema constraints
# (chk_appuser_username_format: ^[a-z0-9._-]{3,50}$; chk_appuser_role).
if [[ -z "${USERNAME}" || -z "${ROLE}" ]]; then
    echo "error: --username and --role are required" >&2
    exit "${EXIT_USAGE}"
fi
if ! [[ "${USERNAME}" =~ ^[a-z0-9._-]{3,50}$ ]]; then
    echo "error: username must match ^[a-z0-9._-]{3,50}$ (lowercase, alphanumeric + . _ -)" >&2
    exit "${EXIT_VALIDATION}"
fi
case "${ROLE}" in
    admin|operator|auditor) ;;
    *)
        echo "error: --role must be one of: admin, operator, auditor" >&2
        exit "${EXIT_VALIDATION}"
        ;;
esac

# Read password
if [[ -n "${PASSWORD_FILE}" ]]; then
    if [[ ! -f "${PASSWORD_FILE}" ]]; then
        echo "error: password-file not found: ${PASSWORD_FILE}" >&2
        exit "${EXIT_USAGE}"
    fi
    PASSWORD="$(cat "${PASSWORD_FILE}" | tr -d '\n\r')"
elif [[ -t 0 ]]; then
    # Interactive terminal — prompt with no echo.
    printf "Password for %s: " "${USERNAME}" >&2
    stty -echo
    IFS= read -r PASSWORD
    stty echo
    printf "\n" >&2
    printf "Confirm: " >&2
    stty -echo
    IFS= read -r PASSWORD_CONFIRM
    stty echo
    printf "\n" >&2
    if [[ "${PASSWORD}" != "${PASSWORD_CONFIRM}" ]]; then
        echo "error: passwords do not match" >&2
        exit "${EXIT_VALIDATION}"
    fi
else
    # Non-interactive (CI / cron) — require --password-file
    echo "error: stdin is not a tty; pass --password-file PATH" >&2
    exit "${EXIT_USAGE}"
fi

if [[ ${#PASSWORD} -lt 8 ]]; then
    echo "error: password must be ≥ 8 characters" >&2
    exit "${EXIT_VALIDATION}"
fi

# psql wrapper
run_psql() {
    if [[ "${USE_DOCKER_STACK}" -eq 1 ]]; then
        docker compose -f "${COMPOSE_FILE}" exec -T postgres \
            psql -U postgres -d polaris -tA "$@"
    else
        psql -h "${POLARIS_DB_HOST:-localhost}" \
             -U "${POLARIS_DB_USER:-postgres}" \
             -d "${POLARIS_DB_NAME:-polaris}" \
             -tA "$@"
    fi
}

# Idempotency check
EXISTS=$(run_psql -c "SELECT 1 FROM AppUser WHERE username='${USERNAME}'" 2>/dev/null | tr -d '[:space:]')
if [[ "${EXISTS}" == "1" ]]; then
    echo "error: username '${USERNAME}' already exists. Use the web UI or a SQL ALTER to update an existing account; this script refuses to clobber." >&2
    exit "${EXIT_EXISTS}"
fi

cat <<BANNER

  Polaris — create operator account
  ─────────────────────────────────
  Username:     ${USERNAME}
  Role:         ${ROLE}
  Mode:         $([[ "${USE_DOCKER_STACK}" -eq 1 ]] && echo 'docker-stack' || echo 'local-psql')
  Dry-run:      $([[ "${DRY_RUN}" -eq 1 ]] && echo yes || echo no)

BANNER

if [[ "${DRY_RUN}" -eq 1 ]]; then
    echo "  [dry-run] validation passed; account would be created."
    echo "  [dry-run] AppUser INSERT + AuthAuditLog ACCOUNT_CREATED would issue."
    exit "${EXIT_OK}"
fi

# Compute werkzeug scrypt hash (matches security.py:hash_password).
# We shell out to python3 to use the same werkzeug version the app uses.
HASH=$(POLARIS_PASSWORD="${PASSWORD}" python3 -c "
import os, sys
try:
    from werkzeug.security import generate_password_hash
except ImportError:
    sys.stderr.write('error: werkzeug not on PYTHONPATH; install it or run via the prod docker image\n')
    sys.exit(1)
print(generate_password_hash(os.environ['POLARIS_PASSWORD'], method='scrypt'))
")
if [[ -z "${HASH}" ]]; then
    echo "error: hash computation failed" >&2
    exit "${EXIT_DB}"
fi
unset PASSWORD PASSWORD_CONFIRM POLARIS_PASSWORD

# INSERT into AppUser + AuthAuditLog in one transaction.
# Use a temp file to avoid shell-escaping the hash (it contains $).
SQL_TMP=$(mktemp)
trap 'rm -f "${SQL_TMP}"' EXIT
# v8.97 / Position B: new admin accounts get a 30-day WebAuthn
# enrollment deadline (architect's §IV.4 recommendation). Operator and
# auditor roles get NULL (per §IV.1: operator optional, auditor exempt).
# A deployment that wants to enforce MFA on operators too can flip this
# below to apply to the operator role as well, or set
# webauthn_required_after manually post-create.
if [[ "${ROLE}" == "admin" ]]; then
    WEBAUTHN_DEADLINE_SQL="now() + interval '30 days'"
else
    WEBAUTHN_DEADLINE_SQL="NULL"
fi

cat > "${SQL_TMP}" <<SQL
BEGIN;
INSERT INTO AppUser (username, password_hash, role, is_active, webauthn_required_after)
VALUES ('${USERNAME}', \$polaris\$${HASH}\$polaris\$, '${ROLE}', TRUE, ${WEBAUTHN_DEADLINE_SQL});
INSERT INTO AuthAuditLog (event_type, username, detail)
VALUES (
    'ACCOUNT_CREATED',
    '${USERNAME}',
    'role=${ROLE} created_by=polaris-create-operator.sh webauthn_deadline=${WEBAUTHN_DEADLINE_SQL}'
);
COMMIT;
SQL

if ! run_psql -f "${SQL_TMP}" 2>&1 | grep -qE 'INSERT|COMMIT'; then
    # Capture full error
    OUT=$(run_psql -f "${SQL_TMP}" 2>&1 || true)
    echo "error: database insert failed:" >&2
    echo "${OUT}" >&2
    exit "${EXIT_DB}"
fi

echo "  ✓ account '${USERNAME}' created with role '${ROLE}'."
echo "  ✓ AuthAuditLog ACCOUNT_CREATED entry written."
echo
echo "  Next: operator should log in via /login and change the password"
echo "        via /admin/users/<id>/edit on first session."
if [[ "${ROLE}" == "admin" ]]; then
    echo
    echo "  v8.97 / WebAuthn-MFA: admin accounts have a 30-day WebAuthn"
    echo "  enrollment deadline. After deadline + no enrolled credential,"
    echo "  login is refused. Enroll a credential at /settings/webauthn"
    echo "  promptly."
fi

exit "${EXIT_OK}"
