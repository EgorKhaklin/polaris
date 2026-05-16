#!/usr/bin/env bash
# =============================================================================
# scripts/polaris-doctor.sh — read-only diagnostic wrapper
#
# Forwards to `polaris_mac_launch.sh doctor` for the actual diagnostic logic.
# Exists so that operator runbooks (DR-SINGLE-REGION.md, polaris-oracle-runner.sh)
# can invoke `polaris-doctor.sh` as a standalone command without coupling to
# the launcher path.
#
# The launcher's doctor() function is the canonical implementation. This
# wrapper is the operator-facing entry point.
# =============================================================================

set -uo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"
POLARIS_ROOT="$(cd -- "${SCRIPT_DIR}/.." &> /dev/null && pwd)"
LAUNCHER="${POLARIS_ROOT}/polaris_mac_launch.sh"

if [[ ! -x "${LAUNCHER}" ]]; then
    echo "polaris-doctor: ${LAUNCHER} not executable — install or chmod +x it" >&2
    exit 2
fi

exec "${LAUNCHER}" doctor "$@"
