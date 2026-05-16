#!/bin/bash
# =============================================================================
# scripts/ai-mission.sh — print MISSION.md back at the agent (v8.6)
#
# MISSION.md says: "ai-mission.sh prints it back so the agent re-grounds at
# the start of every session." Pre-v8.6 the script didn't exist and the
# claim was a lie. v8.6 builds it.
#
# Three modes:
#   ai-mission.sh             # full mission with section headers
#   ai-mission.sh constraints # just the hard constraints C1-C10
#   ai-mission.sh done        # just the done-list (v1 + v2)
#   ai-mission.sh isnot       # just the "What Polaris IS NOT" section
#                              (the most-forgotten part — re-read this when
#                              tempted to add money/authority/surveillance)
# =============================================================================

set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
MISSION="$ROOT/MISSION.md"

if [ ! -f "$MISSION" ]; then
    printf "MISSION.md not found at %s\n" "$MISSION"
    exit 1
fi

if [ -t 1 ]; then
    BOLD="\033[1m"; DIM="\033[2m"; NC="\033[0m"
else
    BOLD=""; DIM=""; NC=""
fi

case "${1:-}" in
    constraints|c)
        # Pull C1-C10 table + the brief WHY-each section that follows
        sed -n '/^## The hard constraints/,/^## What "done" looks like/p' "$MISSION" \
            | sed '$d'      # drop the trailing section header
        ;;
    done|d)
        sed -n '/^## What "done" looks like/,/^## The agent.s relationship/p' "$MISSION" \
            | sed '$d'
        ;;
    isnot|n)
        sed -n '/^## What Polaris IS NOT/,/^## The hard constraints/p' "$MISSION" \
            | sed '$d'
        ;;
    is)
        sed -n '/^## What Polaris IS$/,/^## What Polaris IS NOT/p' "$MISSION" \
            | sed '$d'
        ;;
    why)
        sed -n '/^## Why Polaris exists/,/^## What Polaris IS$/p' "$MISSION" \
            | sed '$d'
        ;;
    --help|-h)
        sed -n '2,16p' "$0" | sed 's/^# \?//'
        ;;
    "")
        printf "${BOLD}═══ MISSION.md ═══${NC}\n"
        printf "${DIM}(Polaris constitution. Read this when tempted to drift toward identity ↔ money,\n"
        printf "or any of the other 'IS NOT' lines. Pass a section name to scope: constraints, done, isnot, is, why)${NC}\n\n"
        cat "$MISSION"
        ;;
    *)
        printf "Unknown section: %s\n" "$1"
        printf "Try: constraints, done, isnot, is, why, or no argument for full text.\n"
        exit 2
        ;;
esac
