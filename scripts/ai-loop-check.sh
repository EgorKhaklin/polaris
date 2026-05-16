#!/bin/bash
# =============================================================================
# scripts/ai-loop-check.sh
#
# Stuck-loop detector. The brain analog is the anterior cingulate cortex —
# fires when behavior isn't producing expected outcomes. The conscious
# correlate is "wait, I've been hitting my head against this for an hour."
#
# In sessions, the failure mode is:
#   - editing the same file 5+ times because each edit reveals a new bug
#   - re-running the same test 5+ times waiting for it to pass
#   - logging the same "decision" 3+ times in different framings
#
# Each is a signal to STOP, name what's happening, and either:
#   - escalate (different approach)
#   - back out (the change was wrong)
#   - ask the user (we're missing context)
#
# This script reads today's journal + recent file mtimes and flags anything
# above threshold. Exit 0 if clean, exit 1 if any flag fires (so it can be
# wired into ai-bootstrap or ai-reflect as a guard).
#
# Usage:
#     ai-loop-check.sh                # warn-only
#     ai-loop-check.sh --strict       # exit 1 on any flag
#     ai-loop-check.sh --thresh-edit 8 --thresh-fail 5
# =============================================================================

set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
DATE=$(date +%Y-%m-%d)
JOURNAL="$ROOT/journal/$DATE.md"

if [ -t 1 ]; then
    BOLD="\033[1m"; R="\033[0;31m"; Y="\033[0;33m"; G="\033[0;32m"; DIM="\033[2m"; NC="\033[0m"
else
    BOLD=""; R=""; Y=""; G=""; DIM=""; NC=""
fi

# Defaults — tuneable
THRESH_EDIT_PER_FILE=5    # >N edits to same file in a day = suspicious
THRESH_RECENT_MIN=120     # files modified in last N min count as "current focus"
THRESH_REPEATED_DECISIONS=3  # same word stem in 3+ decisions = circling
STRICT=0

while [ $# -gt 0 ]; do
    case "$1" in
        --strict) STRICT=1; shift ;;
        --thresh-edit) THRESH_EDIT_PER_FILE="$2"; shift 2 ;;
        --thresh-min)  THRESH_RECENT_MIN="$2"; shift 2 ;;
        --help|-h)
            sed -n '2,30p' "$0" | sed 's/^# \?//'
            exit 0 ;;
        *) shift ;;
    esac
done

FLAGS=0

printf "${BOLD}── stuck-loop check ──${NC}\n"

# -----------------------------------------------------------------------------
# Flag 1: a single file edited many times in the recent window
# Heuristic: count number of distinct mtimes. If a file shows up modified
# more than THRESH_EDIT_PER_FILE times across journal "decision" entries
# referencing it, that's churn.
# -----------------------------------------------------------------------------
if [ -f "$JOURNAL" ]; then
    # Pull file paths mentioned in decisions, count occurrences
    HOTLINE=$(grep -oE '[a-zA-Z_./-]+\.(py|sql|js|html|css|md|sh)' "$JOURNAL" 2>/dev/null | sort | uniq -c | sort -rn | head -3)
    if [ -n "$HOTLINE" ]; then
        TOPCOUNT=$(echo "$HOTLINE" | head -1 | awk '{print $1}')
        TOPFILE=$(echo "$HOTLINE" | head -1 | awk '{print $2}')
        if [ "${TOPCOUNT:-0}" -gt "$THRESH_EDIT_PER_FILE" ]; then
            printf "  ${R}FLAG${NC}  %s mentioned in %d journal entries today\n" "$TOPFILE" "$TOPCOUNT"
            printf "        ${DIM}repeated edits suggest the underlying problem isn't where you think.${NC}\n"
            printf "        ${DIM}consider: back out, re-read DEVNOTES, or ask the user.${NC}\n"
            FLAGS=$((FLAGS+1))
        else
            printf "  ${G}OK  ${NC}  edit hotspot: %s (%d mentions, threshold=%d)\n" "$TOPFILE" "${TOPCOUNT:-0}" "$THRESH_EDIT_PER_FILE"
        fi
    else
        printf "  ${G}OK  ${NC}  no journal-tracked file edits today\n"
    fi
else
    printf "  ${DIM}skip${NC}  no journal file for today\n"
fi

# -----------------------------------------------------------------------------
# Flag 2: same word stem appears in many decision entries
# Words like "fix", "race", "concurrency", "atlas" recurring 3+ times across
# decision entries can mean circling on the same problem with different framings.
# -----------------------------------------------------------------------------
if [ -f "$JOURNAL" ]; then
    REPEATED=$(grep -E "^- \*\*decision\*\*" "$JOURNAL" 2>/dev/null | \
        grep -oE '\b[a-zA-Z_]{4,}\b' | \
        tr '[:upper:]' '[:lower:]' | \
        grep -vE '^(decision|the|that|this|with|from|when|then|must|need|will|have|should|while|there|because|after|before|could|would)$' | \
        sort | uniq -c | sort -rn | head -1)
    if [ -n "$REPEATED" ]; then
        REPCOUNT=$(echo "$REPEATED" | awk '{print $1}')
        REPWORD=$(echo "$REPEATED" | awk '{print $2}')
        if [ "${REPCOUNT:-0}" -ge "$THRESH_REPEATED_DECISIONS" ]; then
            printf "  ${Y}WARN${NC}  '%s' appears in %d decisions today\n" "$REPWORD" "$REPCOUNT"
            printf "        ${DIM}circling? if 3+ decisions touch the same concept, your model may be incomplete.${NC}\n"
            FLAGS=$((FLAGS+1))
        else
            printf "  ${G}OK  ${NC}  decision diversity: top word '%s' x%d (threshold=%d)\n" "${REPWORD:-N/A}" "${REPCOUNT:-0}" "$THRESH_REPEATED_DECISIONS"
        fi
    fi
fi

# -----------------------------------------------------------------------------
# Flag 3: bug entries without a follow-up decision
# A bug logged without a subsequent "decision" entry suggests the bug was
# noted but not actually closed.
# -----------------------------------------------------------------------------
if [ -f "$JOURNAL" ]; then
    BUGS=$(grep -cE "^- \*\*bug\*\*" "$JOURNAL" 2>/dev/null | head -1)
    DECISIONS=$(grep -cE "^- \*\*decision\*\*" "$JOURNAL" 2>/dev/null | head -1)
    : "${BUGS:=0}"
    : "${DECISIONS:=0}"
    if [ "$BUGS" -gt 0 ] && [ "$DECISIONS" -lt "$BUGS" ]; then
        printf "  ${Y}WARN${NC}  %d bugs logged but only %d decisions — open loops?\n" "$BUGS" "$DECISIONS"
        FLAGS=$((FLAGS+1))
    fi
fi

# -----------------------------------------------------------------------------
# Flag 4: recent-edit churn within a short window
# Files modified MORE THAN ONCE in the last N minutes = active churn.
# -----------------------------------------------------------------------------
RECENT_CHURN=$(find "$ROOT" -type f \
    -not -path '*/.git/*' -not -path '*/__pycache__/*' -not -path '*/journal/*' \
    -mmin -"$THRESH_RECENT_MIN" 2>/dev/null \
    | wc -l)

if [ "${RECENT_CHURN:-0}" -gt 20 ]; then
    printf "  ${Y}WARN${NC}  %d files touched in last %d min — broad scope, possible scope creep\n" \
        "$RECENT_CHURN" "$THRESH_RECENT_MIN"
    FLAGS=$((FLAGS+1))
else
    printf "  ${G}OK  ${NC}  recent churn: %d files in last %d min\n" "${RECENT_CHURN:-0}" "$THRESH_RECENT_MIN"
fi

# -----------------------------------------------------------------------------
# Flag 5: LARPING DETECTOR — structural vocabulary without structural backing
#
# Rule (from meta/structural-architecture.md): every structural element must
# impose a removable constraint. If structural vocabulary appears in the
# journal or session work WITHOUT a corresponding structural change, that's
# larping — the failure mode VANTA explicitly asked to be flagged.
#
# This check looks at TODAY's journal for structural vocabulary, then verifies
# the same session committed structural changes (file modifications or new
# files) consistent with the vocabulary used.
# -----------------------------------------------------------------------------
TODAY_JOURNAL="$ROOT/journal/$(date +%Y-%m-%d).md"
LARP_VOCAB="constraint lattice|lattice walk|pattern catalog|polarity complement|cross-layer principle|fibonacci|golden ratio|structural invariant"

if [ -f "$TODAY_JOURNAL" ]; then
    LARP_USES=$(grep -ciE "$LARP_VOCAB" "$TODAY_JOURNAL" 2>/dev/null | head -1)
    : "${LARP_USES:=0}"
    # Count structural changes in today's session — files modified in last 4h
    # within meta/, scripts/, patterns/, or DEVNOTES/
    STRUCTURAL_CHANGES=$(find "$ROOT/meta" "$ROOT/scripts" "$ROOT/patterns" "$ROOT/DEVNOTES" \
        -type f -mmin -240 2>/dev/null | wc -l)
    : "${STRUCTURAL_CHANGES:=0}"

    if [ "$LARP_USES" -gt 0 ] && [ "$STRUCTURAL_CHANGES" -eq 0 ]; then
        printf "  ${R}LARP${NC}  structural vocabulary used (%d times) without any structural change in last 4h\n" "$LARP_USES"
        printf "        ${DIM}Rule: every structural element must impose a removable constraint.${NC}\n"
        printf "        ${DIM}If you removed the structural references, would anything break?${NC}\n"
        FLAGS=$((FLAGS+2))
    elif [ "$LARP_USES" -gt 0 ]; then
        printf "  ${G}OK  ${NC}  structural vocabulary used (%d times) with %d structural changes (not larping)\n" \
            "$LARP_USES" "$STRUCTURAL_CHANGES"
    else
        printf "  ${G}OK  ${NC}  no structural vocabulary in today's journal (no larping risk)\n"
    fi
else
    printf "  ${DIM}--- ${NC}  no journal today — larp check skipped\n"
fi

# -----------------------------------------------------------------------------
# Summary
# -----------------------------------------------------------------------------
echo
if [ "$FLAGS" -eq 0 ]; then
    printf "${G}${BOLD}Loop check: clean${NC} (no signals of stuck-loop or churn)\n"
    exit 0
elif [ "$FLAGS" -le 1 ]; then
    printf "${Y}${BOLD}Loop check: %d soft signal${NC}\n" "$FLAGS"
    [ "$STRICT" -eq 1 ] && exit 1 || exit 0
else
    printf "${R}${BOLD}Loop check: %d signals${NC} — pause and reassess before continuing\n" "$FLAGS"
    [ "$STRICT" -eq 1 ] && exit 1 || exit 0
fi
