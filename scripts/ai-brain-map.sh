#!/bin/bash
# =============================================================================
# scripts/ai-brain-map.sh — Polaris hive-mind visualizer (v8.52)
#
# Parses Polaris's structural artifacts (schema, procedures, routes, watchers,
# ai-* scripts, Sanctums, ships, principles, constraints, DEVNOTES) and
# generates an interactive D3 force-directed graph at meta/brain-map/brain-map.html.
#
# Open the output in any browser — no server needed, no network calls
# (d3 is vendored at meta/brain-map/assets/d3.v7.min.js).
#
# Usage:
#     scripts/ai-brain-map.sh         # generate + report
#     scripts/ai-brain-map.sh --open  # generate + open in default browser
#
# Audience: future agents priming themselves + VANTA visualizing the
# hive mind. The output stays in sync with the system because ai-done.sh
# runs this script as part of its pre-ship gate (v8.52 wiring).
#
# Authorization: VANTA's "ship now" on the Architect's Shape-A proposal.
# No Sanctum required — pure additive documentation artifact.
# =============================================================================
set -eu

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"

# Find a working Python 3. Try the candidate venvs first (matches the
# pattern in ai-test.sh), then system python3.
PY=""
for cand in \
    "$ROOT/polaris_web/venv/bin/python" \
    "/private/tmp/polaris-codex-venv312/bin/python" \
    "/Users/$(whoami)/venv/bin/python" \
    "$(command -v python3.12)" \
    "$(command -v python3)" ; do
    if [ -n "$cand" ] && [ -x "$cand" ]; then
        # Only stdlib needed; any Python 3 works.
        if "$cand" -c "import json, pathlib, re" >/dev/null 2>&1; then
            PY="$cand"
            break
        fi
    fi
done

if [ -z "$PY" ]; then
    echo "ai-brain-map: cannot find a Python 3 with stdlib" >&2
    exit 1
fi

cd "$ROOT"

# Dispatch on flag
case "${1:-}" in
    --analyze|-a)
        # v8.54: structured findings report — orphans, hubs, cross-
        # layer edges, missing-edge suggestions. Output to stdout
        # (and optionally to meta/brain-map/brain-map-analysis.md via --write).
        # Requires meta/brain-map/brain-map.html to already exist; regenerate
        # it first if needed.
        if [ ! -f "$ROOT/meta/brain-map/brain-map.html" ]; then
            "$PY" "$HERE/ai_brain_map.py"
        fi
        "$PY" "$HERE/ai_brain_map_analyze.py" "${@:2}"
        ;;
    --open|-o)
        "$PY" "$HERE/ai_brain_map.py"
        if command -v open >/dev/null 2>&1; then
            open "$ROOT/meta/brain-map/brain-map.html"
        else
            echo "ai-brain-map: \`open\` not available; open the file yourself:" >&2
            echo "  $ROOT/meta/brain-map/brain-map.html" >&2
        fi
        ;;
    --auto)
        # v9.09 / E — cron-safe regen.
        # Only regenerates if brain-map.html is older than the most-
        # recent source mtime (matches ant_brain_map_freshness's
        # detection logic). Silent if nothing to do; exits 0.
        # Suitable for `ai-brain-map.sh --auto` in cron + pre-commit.
        if [ ! -f "$ROOT/meta/brain-map/brain-map.html" ]; then
            "$PY" "$HERE/ai_brain_map.py" >/dev/null 2>&1 || exit 1
            echo "ai-brain-map --auto: brain-map.html created"
            exit 0
        fi
        # Find newest source mtime under polaris_*/ + scripts/ + meta/
        # (matches the ant; excludes venv + caches + brain-map itself)
        BRAIN_MAP_MTIME=$(stat -f%m "$ROOT/meta/brain-map/brain-map.html" 2>/dev/null \
                          || stat -c%Y "$ROOT/meta/brain-map/brain-map.html" 2>/dev/null)
        # Cross-platform stat: macOS -f%m vs Linux -c%Y
        NEWEST_SRC=$(find "$ROOT/polaris_web" "$ROOT/polaris_hydra" \
                          "$ROOT/polaris_swarm" "$ROOT/polaris_sql" \
                          "$ROOT/scripts" "$ROOT/meta" \
                     -type f \
                     \( -name "*.py" -o -name "*.sh" -o -name "*.sql" \
                        -o -name "*.md" -o -name "*.json" \) \
                     -not -path "*/venv/*" -not -path "*/__pycache__/*" \
                     -not -path "*/brain-map/*" 2>/dev/null \
                     | xargs -I{} sh -c 'stat -f%m "{}" 2>/dev/null || stat -c%Y "{}" 2>/dev/null' \
                     | sort -rn | head -1)
        if [ -z "$NEWEST_SRC" ] || [ -z "$BRAIN_MAP_MTIME" ]; then
            echo "ai-brain-map --auto: could not compute mtimes" >&2
            exit 1
        fi
        if [ "$NEWEST_SRC" -gt "$BRAIN_MAP_MTIME" ]; then
            "$PY" "$HERE/ai_brain_map.py" >/dev/null 2>&1
            echo "ai-brain-map --auto: regenerated (source newer than map)"
        fi
        # Silent on no-op (cron-friendly)
        ;;
    *)
        "$PY" "$HERE/ai_brain_map.py"
        ;;
esac
