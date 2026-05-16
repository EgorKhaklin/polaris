#!/usr/bin/env bash
# ai-swarm-bloom — render Mycelium's pheromone heatmap (Arc E / E1 / v8.62).
#
# Mycelium is Polaris's swarm intelligence substrate. Tiny ants deposit
# pheromones onto brain-map nodes (the Pheromone table). This script
# queries those pheromones, applies the deterministic decay function,
# and renders the brain-map nodes currently lit up by the swarm.
#
# The bloom is the operator-facing surface. The pheromone log itself
# is the truth; this is just a rendering. No LLM is called in Phase 1.
#
# Substitutable per v8.30: a future agent may replace this renderer
# without violating any constitutional principle.
#
# Usage:
#     ai-swarm-bloom.sh                # top 20 hottest nodes, last 72h
#     ai-swarm-bloom.sh --top 5        # top 5
#     ai-swarm-bloom.sh --by-ant       # group by depositing ant
#     ai-swarm-bloom.sh --by-kind      # group by alert/drift/info/curious
#     ai-swarm-bloom.sh --dry          # scan colony in-memory, no DB
#     ai-swarm-bloom.sh --json         # JSON output for tooling

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Find a working Python venv. Same discovery pattern as ai-hydra.sh.
find_python() {
    if [[ -n "${POLARIS_SWARM_PYTHON:-}" ]]; then
        echo "$POLARIS_SWARM_PYTHON"
        return 0
    fi
    local candidates=(
        "/private/tmp/polaris-codex-venv312/bin/python3"
        "$ROOT/polaris_web/venv/bin/python3"
        "/opt/homebrew/bin/python3"
        "python3"
    )
    for py in "${candidates[@]}"; do
        if command -v "$py" >/dev/null 2>&1; then
            # Verify Python is recent enough.
            if "$py" -c "import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)" 2>/dev/null; then
                echo "$py"
                return 0
            fi
        fi
    done
    return 1
}

PY="$(find_python)" || {
    echo "ai-swarm-bloom: no suitable Python 3.9+ found" >&2
    echo "  Set POLARIS_SWARM_PYTHON=/path/to/python3 or install Python 3.9+." >&2
    exit 1
}

cd "$ROOT"
export PYTHONPATH="${PYTHONPATH:+$PYTHONPATH:}$ROOT"
exec "$PY" "$ROOT/scripts/ai_swarm_bloom.py" "$@"
