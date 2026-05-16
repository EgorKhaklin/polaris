#!/bin/bash
# =============================================================================
# scripts/ai-hydra.sh — HYDRA swarm-synthesis wrapper (Arc D / v8.37+).
# v9.04 hybrid intelligence: --full / --actions / --save / --diff modes.
#
# Invokes polaris_hydra.host with the same Python venv discovery the
# rest of the cognitive layer uses. HYDRA gathers reports from every
# enabled watcher, optionally synthesizes via Claude Opus 4.7 with
# adaptive thinking, and (in --full mode) augments with cross-watcher
# correlations + a ranked action queue + the swarm Pheromone snapshot.
#
# Usage:
#   ai-hydra.sh                                 # all watchers, text synthesis
#   ai-hydra.sh --watcher schema                # one watcher
#   ai-hydra.sh --json                          # JSON output (full audit trail)
#   ai-hydra.sh --query "…"                     # focused synthesis question
#
# v9.04 modes:
#   ai-hydra.sh --full                          # gather + correlate + actions
#                                               #   + Pheromone snapshot
#   ai-hydra.sh --actions                       # just the ranked action queue
#   ai-hydra.sh --full --save                   # archive to journal/hydra/
#                                               #   + delta vs prior brief
#   ai-hydra.sh --full --diff <prior_brief.md>  # explicit delta target
#   ai-hydra.sh --pheromone-window-hours 12     # override 6h substrate default
#   ai-hydra.sh --deterministic                 # force deterministic synthesis
#                                               #   even with ANTHROPIC_API_KEY (v9.05)
#   ai-hydra.sh --gc                            # rotate journal/hydra/ — list
#                                               #   briefs older than --gc-keep
#                                               #   (default 30); requires --gc-yes
#                                               #   to actually delete (v9.09)
#   ai-hydra.sh --gc --gc-keep 20 --gc-yes      # cron-mode purge
#   ai-hydra.sh --help                          # this help
#
# Environment:
#   ANTHROPIC_API_KEY     if set, HYDRA calls Claude Opus 4.7
#   POLARIS_DB_HOST       database host         (default: localhost)
#   POLARIS_DB_NAME       database name         (default: polaris_test)
#   POLARIS_DB_USER       database user         (default: polaris_app)
#   POLARIS_DB_PASSWORD   database password     (default: polaris_dev_password)
#   POLARIS_HYDRA_PYTHON  override venv python  (otherwise auto-discovers)
#
# See polaris_hydra/README.md for the swarm architecture +
# DEVNOTES/hydra-pheromone-integration.md for the v9.04 hybrid model.
# =============================================================================

set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"

# -----------------------------------------------------------------------------
# Find a Python venv with psycopg2 (same discovery as ai-test.sh).
# Order: env override → repo-local venv → codex venv → user venv → system.
# -----------------------------------------------------------------------------
PYVENV="${POLARIS_HYDRA_PYTHON:-${POLARIS_TEST_PYTHON:-}}"
if [ -z "$PYVENV" ]; then
    for cand in \
        "$ROOT/polaris_web/venv/bin/python" \
        "/private/tmp/polaris-codex-venv312/bin/python" \
        "/Users/$(whoami)/venv/bin/python" \
        "$(command -v python3 2>/dev/null)" \
    ; do
        if [ -x "$cand" ] && "$cand" -c "import psycopg2" 2>/dev/null; then
            PYVENV="$cand"
            break
        fi
    done
fi

if [ -z "$PYVENV" ]; then
    echo "ai-hydra: cannot find a Python venv with psycopg2." >&2
    echo "  Set POLARIS_HYDRA_PYTHON=/path/to/venv/bin/python or" >&2
    echo "  install psycopg2 in one of the candidate venvs." >&2
    echo "  HYDRA will still run but the Pheromone substrate will" >&2
    echo "  report status='db_offline' and watchers reading the DB" >&2
    echo "  will alert. Falling back to a system python3." >&2
    PYVENV="$(command -v python3 2>/dev/null)"
    if [ -z "$PYVENV" ]; then
        echo "  No python3 found. Aborting." >&2
        exit 1
    fi
fi

# -----------------------------------------------------------------------------
# Defaults for DB env vars so HYDRA can talk to Polaris out of the box.
# Inherits if already set; otherwise uses the same defaults as the test DB.
# -----------------------------------------------------------------------------
export POLARIS_DB_HOST="${POLARIS_DB_HOST:-localhost}"
export POLARIS_DB_NAME="${POLARIS_DB_NAME:-polaris_test}"
export POLARIS_DB_USER="${POLARIS_DB_USER:-polaris_app}"
export POLARIS_DB_PASSWORD="${POLARIS_DB_PASSWORD:-polaris_dev_password}"

# -----------------------------------------------------------------------------
# Hand off to the host module. PYTHONPATH lets us run polaris_hydra as a
# package from the repo root without installing it.
# -----------------------------------------------------------------------------
cd "$ROOT"
PYTHONPATH="$ROOT" "$PYVENV" -m polaris_hydra.host "$@"
