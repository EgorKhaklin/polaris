#!/usr/bin/env bash
# ============================================================================
# polaris-mycelium-wake.sh — wrapper for Mycelium swarm wake invocations
#                            (v9.34 / swarm-cron-cadence ship)
#
# Purpose: keep cron entries credential-free + env-portable. Cron
# scheduled via polaris-cron-install.sh calls this wrapper at the
# documented cadences (every 30m soldiers, every 6h commanders per
# docs/operator/OPERATIONS.md §"Mycelium swarm cron schedule").
#
# Env handling (in priority order):
#   1. Operator's current shell env (cron inherits little; rarely set)
#   2. ${POLARIS_ROOT}/polaris.env — operator-managed, gitignored,
#      sourced if present. Recommended pattern: file owned by the
#      cron user, mode 0600, contains POLARIS_DB_PASSWORD + any
#      non-default values for POLARIS_DB_HOST/PORT/NAME/USER.
#   3. Sensible dev defaults below for POLARIS_DB_* (NOT password)
#
# POLARIS_DB_PASSWORD is INTENTIONALLY NOT defaulted. If it isn't
# set by step 1 or step 2, the wrapper relies on PostgreSQL peer
# auth or .pgpass — never a hardcoded literal. (Pre-v9.34 a draft
# of the cron-install entries hardcoded the dev password inline in
# the operator's crontab, which would leak via `crontab -l`. The
# Anti-Architect catch on dry-run forced this wrapper redesign.)
#
# Usage:
#   ./scripts/polaris-mycelium-wake.sh --soldiers
#   ./scripts/polaris-mycelium-wake.sh --commander
#   ./scripts/polaris-mycelium-wake.sh --hybrid          # both, sequential
#   ./scripts/polaris-mycelium-wake.sh --help
#
# Exit codes:
#   0  wake completed
#   2  usage error
#   3  python venv not found
#   any non-zero from python -m polaris_swarm.colony propagates
# ============================================================================

set -uo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"
POLARIS_ROOT="$(cd -- "${SCRIPT_DIR}/.." &> /dev/null && pwd)"

# Step 2: source polaris.env if present (operator-managed, gitignored)
if [[ -f "${POLARIS_ROOT}/polaris.env" ]]; then
    # shellcheck source=/dev/null
    set -a
    . "${POLARIS_ROOT}/polaris.env"
    set +a
fi

# Step 3: dev defaults (NOT password)
export POLARIS_DB_HOST="${POLARIS_DB_HOST:-localhost}"
export POLARIS_DB_PORT="${POLARIS_DB_PORT:-5432}"
export POLARIS_DB_NAME="${POLARIS_DB_NAME:-polaris_test}"
export POLARIS_DB_USER="${POLARIS_DB_USER:-polaris_app}"

# Venv must exist (cron has minimal PATH; explicit path required)
PYBIN="${POLARIS_ROOT}/polaris_web/venv/bin/python3"
if [[ ! -x "${PYBIN}" ]]; then
    echo "polaris-mycelium-wake: venv python not found at ${PYBIN}" >&2
    echo "  create with: python3 -m venv ${POLARIS_ROOT}/polaris_web/venv && \\" >&2
    echo "    ${POLARIS_ROOT}/polaris_web/venv/bin/pip install -r ${POLARIS_ROOT}/polaris_web/requirements.txt" >&2
    exit 3
fi

cd "${POLARIS_ROOT}"

case "${1:-}" in
    --soldiers)
        exec "${PYBIN}" -m polaris_swarm.colony --soldiers --duration 60
        ;;
    --commander|--commanders|--swarm)
        exec "${PYBIN}" -m polaris_swarm.colony --swarm
        ;;
    --hybrid)
        "${PYBIN}" -m polaris_swarm.colony --swarm || exit $?
        exec "${PYBIN}" -m polaris_swarm.colony --soldiers --duration 60
        ;;
    --help|-h|"")
        sed -n '2,32p' "$0" | sed 's/^# \{0,1\}//'
        exit 0
        ;;
    *)
        echo "polaris-mycelium-wake: unknown arg: ${1}" >&2
        echo "usage: $0 --soldiers | --commander | --hybrid" >&2
        exit 2
        ;;
esac
