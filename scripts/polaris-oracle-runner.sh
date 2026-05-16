#!/usr/bin/env bash
# ============================================================================
# polaris-oracle-runner.sh — refresh meta/oracle-state.json
#
# v9.24 / BIG MISSION Tier 1 #6. Runs the two external oracles HYDRA
# reconciles against and writes the result to meta/oracle-state.json.
# HYDRA's polaris_hydra/oracles.py reads this file (does not run the
# probes itself, keeping brief-emit latency deterministic + G1
# preserved).
#
# Cadence:
#     ./scripts/polaris-oracle-runner.sh              # full refresh
#     ./scripts/polaris-oracle-runner.sh --launcher-only
#     ./scripts/polaris-oracle-runner.sh --adversary-only
#
# Cron-recommended: every Saturn-pass (24h). polaris-cron-install.sh
# wires this at 05:30 UTC (after the daily cog-self-audit at 05:00).
#
# The two oracles:
#
#     launcher  — polaris_mac_launch.sh status (or polaris-doctor.sh
#                 as fallback if launcher not present)
#                 exit code 0 = healthy
#
#     adversary — ai-adversary.sh per constraint
#                 exit code 0 = no new violation
# ============================================================================

set -uo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"
POLARIS_ROOT="$(cd -- "${SCRIPT_DIR}/.." &> /dev/null && pwd)"
OUT_FILE="${POLARIS_ROOT}/meta/oracle-state.json"

RUN_LAUNCHER=1
RUN_ADVERSARY=1

for arg in "$@"; do
    case "${arg}" in
        --launcher-only) RUN_ADVERSARY=0 ;;
        --adversary-only) RUN_LAUNCHER=0 ;;
        --help|-h)
            sed -n '2,28p' "$0" | sed 's/^# \{0,1\}//'
            exit 0
            ;;
    esac
done

NOW_UTC=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

# Launcher probe
LAUNCHER_EXIT="-1"
LAUNCHER_TAIL=""
if [[ "${RUN_LAUNCHER}" -eq 1 ]]; then
    if [[ -x "${POLARIS_ROOT}/polaris_mac_launch.sh" ]]; then
        LAUNCHER_OUT=$("${POLARIS_ROOT}/polaris_mac_launch.sh" status 2>&1 || true)
        LAUNCHER_EXIT=$?
        LAUNCHER_TAIL=$(echo "${LAUNCHER_OUT}" | tail -3 | tr '\n' ' ' | sed 's/"/\\"/g')
    elif [[ -x "${POLARIS_ROOT}/scripts/polaris-doctor.sh" ]]; then
        LAUNCHER_OUT=$("${POLARIS_ROOT}/scripts/polaris-doctor.sh" 2>&1 || true)
        LAUNCHER_EXIT=$?
        LAUNCHER_TAIL="(doctor.sh fallback) "$(echo "${LAUNCHER_OUT}" | tail -3 | tr '\n' ' ' | sed 's/"/\\"/g')
    else
        LAUNCHER_TAIL="(no launcher or doctor present)"
    fi
fi

# Adversary probe — per constraint
ADV_RESULTS=""
ADV_ANY_NONZERO="false"
if [[ "${RUN_ADVERSARY}" -eq 1 ]]; then
    if [[ -x "${POLARIS_ROOT}/scripts/ai-adversary.sh" ]]; then
        first=1
        for c in C1 C2 C3 C4 C5 C6 C7 C8 C9 C10; do
            "${POLARIS_ROOT}/scripts/ai-adversary.sh" "${c}" >/dev/null 2>&1
            rc=$?
            if [[ "${rc}" -ne 0 ]]; then
                ADV_ANY_NONZERO="true"
            fi
            sep=$([[ "${first}" -eq 1 ]] && echo "" || echo ",")
            ADV_RESULTS="${ADV_RESULTS}${sep}\"${c}\":${rc}"
            first=0
        done
    fi
fi

mkdir -p "$(dirname "${OUT_FILE}")"

cat > "${OUT_FILE}" <<EOF
{
  "_doc": "Polaris external-oracles state. Refreshed by scripts/polaris-oracle-runner.sh; read by polaris_hydra/oracles.py during brief synthesis. Stale (>7d) entries surface as NOTE oracle:stale in the brief.",
  "last_run_utc": "${NOW_UTC}",
  "oracles": {
    "launcher": {
      "status_exit_code": ${LAUNCHER_EXIT},
      "checked_at_utc": "${NOW_UTC}",
      "raw_stdout_tail": "${LAUNCHER_TAIL}"
    },
    "adversary": {
      "per_constraint_exit": { ${ADV_RESULTS} },
      "checked_at_utc": "${NOW_UTC}",
      "any_nonzero": ${ADV_ANY_NONZERO}
    }
  }
}
EOF

echo "polaris-oracle-runner: wrote ${OUT_FILE}"
echo "  launcher exit: ${LAUNCHER_EXIT}"
echo "  adversary any_nonzero: ${ADV_ANY_NONZERO}"
