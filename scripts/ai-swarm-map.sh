#!/bin/bash
# =============================================================================
# scripts/ai-swarm-map.sh — Mycelium swarm visualizer (v9.14)
#
# Generates an interactive D3 force-directed graph dedicated to the
# Mycelium swarm. Distinct from ai-brain-map.sh which visualizes the
# whole system. The swarm map answers "who is alive, what are they
# doing, how do they relate?" at the swarm tier.
#
# Output: meta/swarm-map/swarm-map.html (open in any browser; no server
# needed; d3 is vendored).
#
# Usage:
#     scripts/ai-swarm-map.sh           # generate
#     scripts/ai-swarm-map.sh --open    # generate + open in browser
#     scripts/ai-swarm-map.sh --live    # also query DB for per-ant
#                                       # deposit cadence in last hour
#     scripts/ai-swarm-map.sh --auto    # cron-safe regen (only if stale)
# =============================================================================
set -eu

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"

# Find a working Python 3 (matches ai-brain-map.sh discovery order)
PY=""
for cand in \
    "$ROOT/polaris_web/venv/bin/python" \
    "/private/tmp/polaris-codex-venv312/bin/python" \
    "/Users/$(whoami)/venv/bin/python" \
    "$(command -v python3.12)" \
    "$(command -v python3)" ; do
    if [ -n "$cand" ] && [ -x "$cand" ]; then
        if "$cand" -c "import json, pathlib, re" >/dev/null 2>&1; then
            PY="$cand"
            break
        fi
    fi
done

if [ -z "$PY" ]; then
    echo "ai-swarm-map: cannot find a Python 3 with stdlib" >&2
    exit 1
fi

cd "$ROOT"

OPEN=0
LIVE=0
AUTO=0
for arg in "$@"; do
    case "$arg" in
        --open|-o)  OPEN=1 ;;
        --live|-l)  LIVE=1 ;;
        --auto)     AUTO=1 ;;
        --help|-h)
            sed -n '2,20p' "$0" | sed 's/^# \?//'
            exit 0
            ;;
    esac
done

OUT="$ROOT/meta/swarm-map/swarm-map.html"

if [ "$AUTO" = "1" ]; then
    # Only regen if missing or older than swarm sources
    if [ ! -f "$OUT" ]; then
        regen=1
    else
        BM_MTIME=$(stat -f%m "$OUT" 2>/dev/null || stat -c%Y "$OUT" 2>/dev/null)
        NEWEST=$(find "$ROOT/polaris_swarm" "$ROOT/polaris_hydra/watchers" \
                 -type f -name "*.py" \
                 -not -path "*/__pycache__/*" 2>/dev/null \
                 | xargs -I{} sh -c 'stat -f%m "{}" 2>/dev/null || stat -c%Y "{}" 2>/dev/null' \
                 | sort -rn | head -1)
        if [ -n "$NEWEST" ] && [ "$NEWEST" -gt "$BM_MTIME" ]; then
            regen=1
        else
            regen=0
        fi
    fi
    if [ "$regen" = "0" ]; then
        exit 0
    fi
fi

if [ "$LIVE" = "1" ]; then
    "$PY" "$HERE/ai_swarm_map.py" --live
else
    "$PY" "$HERE/ai_swarm_map.py"
fi

if [ "$OPEN" = "1" ]; then
    if command -v open >/dev/null 2>&1; then
        open "$OUT"
    elif command -v xdg-open >/dev/null 2>&1; then
        xdg-open "$OUT"
    else
        echo "ai-swarm-map: open the file yourself:" >&2
        echo "  $OUT" >&2
    fi
fi
