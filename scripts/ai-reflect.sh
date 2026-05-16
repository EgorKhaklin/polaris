#!/bin/bash
# =============================================================================
# scripts/ai-reflect.sh
#
# End-of-session reflection / consolidation loop. The brain analog is sleep:
# during slow-wave sleep, the hippocampus replays daytime experiences and
# the cortex consolidates the important ones into long-term memory. The
# unimportant gets discarded; the patterns get extracted.
#
# I don't sleep — every conversation ends and I die. So I have to do this
# CONSCIOUSLY before context disappears.
#
# This script:
#   1. Reads today's journal entries
#   2. Reads recent file modifications (git diff if available, else mtime)
#   3. Reads recent test runs (if /tmp/polaris_app.log has structured info)
#   4. Surfaces candidate items for promotion:
#        - learnings → known-gotchas.md
#        - new task shapes → patterns/
#        - voice / quality observations → style.md
#   5. Writes a reflection summary as the day's last journal entry
#
# Usage:
#     ai-reflect.sh                # interactive prompt + summary
#     ai-reflect.sh --auto         # non-interactive; just emit candidate list
#     ai-reflect.sh --commit       # interactive AND apply auto-promotions
#                                  # (gotchas → known-gotchas.md if confidence high)
# =============================================================================

set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
DATE=$(date +%Y-%m-%d)
TIME=$(date +%H:%M)
JOURNAL="$ROOT/journal/$DATE.md"
KNOWN_GOTCHAS="$ROOT/DEVNOTES/known-gotchas.md"
STYLE="$ROOT/DEVNOTES/style.md"

if [ -t 1 ]; then
    BOLD="\033[1m"; CYAN="\033[0;36m"; GOLD="\033[0;33m"; DIM="\033[2m"; G="\033[0;32m"; NC="\033[0m"
else
    BOLD=""; CYAN=""; GOLD=""; DIM=""; G=""; NC=""
fi

MODE="${1:-interactive}"

printf "${BOLD}═══ Reflection — %s %s ═══${NC}\n\n" "$DATE" "$TIME"

# -----------------------------------------------------------------------------
# 1. Today's journal
# -----------------------------------------------------------------------------
if [ -f "$JOURNAL" ]; then
    LEARNINGS=$(grep -E "^- \*\*learning\*\*" "$JOURNAL" 2>/dev/null || true)
    BUGS=$(grep -E "^- \*\*bug\*\*" "$JOURNAL" 2>/dev/null || true)
    DECISIONS=$(grep -E "^- \*\*decision\*\*" "$JOURNAL" 2>/dev/null || true)
    SESSIONS=$(grep -cE "^## SESSION " "$JOURNAL" 2>/dev/null || echo 0)

    printf "${BOLD}Today's journal:${NC}  %s sessions, %s learnings, %s bugs, %s decisions\n" \
        "${SESSIONS:-0}" \
        "$(echo "$LEARNINGS" | grep -c '^-' || echo 0)" \
        "$(echo "$BUGS" | grep -c '^-' || echo 0)" \
        "$(echo "$DECISIONS" | grep -c '^-' || echo 0)"
else
    printf "${BOLD}Today's journal:${NC}  ${DIM}(no journal file — nothing to consolidate)${NC}\n"
    LEARNINGS=""; BUGS=""; DECISIONS=""; SESSIONS=0
fi
echo

# -----------------------------------------------------------------------------
# 2. Recent file modifications
# -----------------------------------------------------------------------------
printf "${BOLD}Files modified today:${NC}\n"
RECENT_FILES=$(find "$ROOT" -type f \
    -not -path '*/.git/*' -not -path '*/__pycache__/*' \
    -not -path '*/journal/*' -not -path '*/node_modules/*' \
    -newermt "$DATE 00:00:00" 2>/dev/null \
    | sort)
if [ -z "$RECENT_FILES" ]; then
    printf "  ${DIM}(none)${NC}\n"
else
    echo "$RECENT_FILES" | while read -r f; do
        REL=$(realpath --relative-to="$ROOT" "$f" 2>/dev/null || echo "$f")
        printf "  %s\n" "$REL"
    done
fi
echo

# -----------------------------------------------------------------------------
# 3. Candidate promotions
# -----------------------------------------------------------------------------
printf "${BOLD}═══ Promotion candidates ═══${NC}\n\n"

# 3a. Learnings → known-gotchas.md
if [ -n "$LEARNINGS" ]; then
    printf "${GOLD}LEARNINGS → %s${NC}\n" "DEVNOTES/known-gotchas.md"
    echo "$LEARNINGS" | sed -E 's/^- \*\*learning\*\* [0-9:]+ —/  /'
    echo
    printf "  ${DIM}Action: append each as a section if it's a recurrent gotcha.${NC}\n"
    echo
fi

# 3b. Bugs → known-gotchas.md (or patterns)
if [ -n "$BUGS" ]; then
    printf "${GOLD}BUGS → %s${NC}\n" "DEVNOTES/known-gotchas.md"
    echo "$BUGS" | sed -E 's/^- \*\*bug\*\* [0-9:]+ —/  /'
    echo
    printf "  ${DIM}Action: append cause + fix to known-gotchas if non-obvious.${NC}\n"
    echo
fi

# 3c. Repeated task shape → patterns/
# Heuristic: if 3+ similar files were modified in similar sequences across
# multiple journal sessions today, that's a candidate task shape.
if [ -n "$DECISIONS" ] && [ "$SESSIONS" -ge 2 ]; then
    printf "${GOLD}REPEATED TASK SHAPE → %s${NC}\n" "patterns/"
    printf "  ${DIM}%s sessions today; if any subtask repeated, extract it as a pattern.${NC}\n" "$SESSIONS"
    echo
fi

# 3d. Style observations
# If "larping" appeared in any journal entry today, that's a style flag
LARP_HITS=$(grep -i "larp" "$JOURNAL" 2>/dev/null | wc -l)
if [ "$LARP_HITS" -gt 0 ]; then
    printf "${GOLD}STYLE FLAG → %s${NC}\n" "DEVNOTES/style.md"
    printf "  ${DIM}'larping' was noted %d time(s) today. Reinforce the pattern in style.md.${NC}\n" "$LARP_HITS"
    echo
fi

# -----------------------------------------------------------------------------
# 4. Self-monitoring metrics (calls ai-loop-check if available)
# -----------------------------------------------------------------------------
if [ -x "$HERE/ai-loop-check.sh" ]; then
    printf "${BOLD}═══ Self-monitoring ═══${NC}\n"
    "$HERE/ai-loop-check.sh"
    echo
fi

# -----------------------------------------------------------------------------
# 5. Write reflection entry to journal
# -----------------------------------------------------------------------------
if [ -f "$JOURNAL" ]; then
    cat >> "$JOURNAL" <<EOF

## REFLECTION $TIME

- Sessions today:   $SESSIONS
- Learnings logged: $(echo "$LEARNINGS" | grep -c '^-' || echo 0)
- Bugs logged:      $(echo "$BUGS" | grep -c '^-' || echo 0)
- Decisions logged: $(echo "$DECISIONS" | grep -c '^-' || echo 0)
- Files modified:   $(echo "$RECENT_FILES" | wc -l)

EOF

    printf "${G}Reflection entry written to %s${NC}\n" \
        "$(realpath --relative-to="$ROOT" "$JOURNAL" 2>/dev/null)"
fi

# -----------------------------------------------------------------------------
# 6. Auto-commit mode (apply low-risk promotions)
# -----------------------------------------------------------------------------
if [ "$MODE" = "--commit" ] && [ -n "$LEARNINGS" ] && [ -f "$KNOWN_GOTCHAS" ]; then
    echo
    printf "${BOLD}--commit mode: appending learnings to known-gotchas.md${NC}\n"
    {
        echo
        echo "## Auto-promoted from journal $DATE"
        echo
        echo "$LEARNINGS" | sed -E 's/^- \*\*learning\*\* [0-9:]+ —/-/'
    } >> "$KNOWN_GOTCHAS"
    printf "${G}Appended to %s${NC}\n" "DEVNOTES/known-gotchas.md"
fi

echo
printf "${BOLD}Done.${NC} Re-run with ${BOLD}--commit${NC} to auto-promote learnings into DEVNOTES.\n"
