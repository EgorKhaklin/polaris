#!/bin/bash
# =============================================================================
# scripts/ai-meta.sh — meta-cognitive audit (v8.9)
#
# The cognitive layer's self-monitor. Fills the previously-reserved
# meta-slot in the constraint lattice (the position formerly known as
# "the hidden 11th, currently unfilled"). The constraint it enforces:
#
#   CM: The cognitive layer self-monitors via executable checks.
#
# What this means concretely: the layer's tools, patterns, constraints,
# and structural claims must be auditable from inside the layer. If a
# pattern is in the catalog but never matches anything; if a constraint
# is in MISSION.md but never touched in code; if a script is in
# CLAUDE.md but doesn't exist on disk — those are drifts the layer
# should catch itself.
#
# Distinct from ai-coherence.sh: that script checks STRUCTURAL invariants
# (lattice intact, constants honored, layers consistent). This script
# checks COGNITIVE-LAYER USAGE invariants (which tools are warm, which
# patterns are cold, which constraints are live, which scripts have
# drifted from their docs).
#
# Sections:
#   tools       — every ai-*.sh referenced in CLAUDE.md exists and runs
#   patterns    — usage analysis of the 22-pattern catalog
#   constraints — which of C1-C10 + CM are live (touched recently)
#   scripts     — script-vs-doc drift (existence + executability)
#   meta-slot   — is the meta-slot filled or explicitly unfilled
#
# Usage:
#     ai-meta.sh             # full report
#     ai-meta.sh --strict    # exit 1 on any drift
#     ai-meta.sh tools       # only the tools check
#     ai-meta.sh patterns    # only the pattern-usage analysis
#     ai-meta.sh constraints # only the constraint-pressure heatmap
# =============================================================================

set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"

if [ -t 1 ]; then
    BOLD="\033[1m"; G="\033[0;32m"; Y="\033[0;33m"; R="\033[0;31m"
    DIM="\033[2m"; CYAN="\033[0;36m"; BLUE="\033[38;5;75m"; NC="\033[0m"
else
    BOLD=""; G=""; Y=""; R=""; DIM=""; CYAN=""; BLUE=""; NC=""
fi

DRIFT=0
STRICT=0
SECTION="all"

for arg in "$@"; do
    case "$arg" in
        --strict) STRICT=1 ;;
        tools|patterns|constraints|scripts|meta-slot) SECTION="$arg" ;;
        --help|-h) sed -n '2,30p' "$0" | sed 's/^# \?//'; exit 0 ;;
    esac
done

ok()      { printf "  ${G}✓${NC} %s\n" "$1"; }
warn()    { printf "  ${Y}!${NC} %s\n" "$1"; DRIFT=$((DRIFT+1)); }
broken()  { printf "  ${R}✗${NC} %s\n" "$1"; DRIFT=$((DRIFT+2)); }
note()    { printf "  ${DIM}-${NC} %s\n" "$1"; }
section() { printf "\n${BOLD}── %s ──${NC}\n" "$1"; }

printf "${BLUE}${BOLD}═══ Polaris — meta-cognitive audit (CM) ═══${NC}\n"
printf "${DIM}  Date:  %s${NC}\n" "$(date '+%Y-%m-%d %H:%M:%S')"
printf "${DIM}  CM constraint: the cognitive layer self-monitors via executable checks${NC}\n"

# -----------------------------------------------------------------------------
# Tools — every ai-*.sh exists, is executable, has a doc comment
# -----------------------------------------------------------------------------
check_tools() {
section "Tools: every ai-* script is real, executable, documented"

local scripts
scripts=$(ls "$HERE"/ai-*.sh 2>/dev/null)
local count=0 ok_count=0
for f in $scripts; do
    count=$((count + 1))
    local base
    base=$(basename "$f")
    if [ ! -x "$f" ]; then
        broken "$base not executable"
        continue
    fi
    # Verify there's a doc-comment block (lines 2-N starting with #)
    local doclines
    doclines=$(sed -n '2,30p' "$f" | grep -c '^#')
    if [ "$doclines" -lt 5 ]; then
        warn "$base has thin doc-comment ($doclines lines; want ≥5)"
        continue
    fi
    ok_count=$((ok_count + 1))
done
ok "$ok_count/$count ai-* scripts: executable, documented"

# Cross-reference CLAUDE.md script list vs disk
local doc_scripts=()
while IFS= read -r line; do
    doc_scripts+=("$line")
done < <(grep -oE 'ai-[a-z-]+\.sh' "$ROOT/CLAUDE.md" 2>/dev/null | sort -u)

local missing=0
for s in "${doc_scripts[@]}"; do
    if [ ! -f "$HERE/$s" ]; then
        broken "CLAUDE.md references $s but it doesn't exist on disk"
        missing=$((missing + 1))
    fi
done
if [ "$missing" -eq 0 ]; then
    ok "every ai-* script in CLAUDE.md exists on disk (${#doc_scripts[@]} cross-references)"
fi

# Reverse: scripts on disk not mentioned in CLAUDE.md
local orphans=0
for f in $scripts; do
    local base
    base=$(basename "$f")
    if ! grep -q "$base" "$ROOT/CLAUDE.md" 2>/dev/null; then
        warn "$base exists but isn't mentioned in CLAUDE.md (orphan or doc drift)"
        orphans=$((orphans + 1))
    fi
done
if [ "$orphans" -eq 0 ]; then
    ok "every disk-resident ai-* script is mentioned in CLAUDE.md"
fi
}

# -----------------------------------------------------------------------------
# Patterns — usage analysis of the 22-pattern catalog
# -----------------------------------------------------------------------------
check_patterns() {
section "Pattern catalog: which patterns are warm, which are cold"

# Pull every pattern name from ai-pattern.sh
local names
names=$(grep -E '^[0-9]+\|[A-Z][A-Za-z]+\|' "$HERE/ai-pattern.sh" 2>/dev/null \
        | cut -d'|' -f2)

if [ -z "$names" ]; then
    broken "couldn't extract pattern names from ai-pattern.sh"
    return
fi

# Count journal mentions for each pattern across all journals
local cold=()
local warm=0 total=0
while read -r name; do
    [ -z "$name" ] && continue
    total=$((total + 1))
    local mentions
    mentions=$(grep -rl "$name" "$ROOT/journal" 2>/dev/null | wc -l | tr -d ' ')
    if [ "$mentions" -eq 0 ]; then
        cold+=("$name")
    else
        warm=$((warm + 1))
    fi
done <<< "$names"

ok "pattern catalog: $warm/$total warm (have journal mentions)"
if [ "${#cold[@]}" -gt 0 ] && [ "${#cold[@]}" -lt "$total" ]; then
    note "cold patterns (never invoked in any journal): ${cold[*]}"
    note "cold patterns are not necessarily wrong; they're shapes we haven't hit yet"
fi

# If ALL patterns are cold, the catalog isn't being used at all
if [ "$warm" -eq 0 ] && [ "$total" -gt 0 ]; then
    warn "0/$total patterns ever invoked — ai-pattern.sh may not be in active use"
fi
}

# -----------------------------------------------------------------------------
# Constraints — which of C1-C10 + CM are touched recently
# -----------------------------------------------------------------------------
check_constraints() {
section "Constraint pressure: which constraints are live"

# For each C1-C10, count mentions in files modified in the last 30 days
local cutoff_days=30
local pressure=()
for n in 1 2 3 4 5 6 7 8 9 10; do
    local mentions
    mentions=$(find "$ROOT" -type f \
        \( -name '*.py' -o -name '*.sql' -o -name '*.sh' -o -name '*.md' \) \
        -not -path '*/.git/*' -not -path '*/__pycache__/*' \
        -mtime -"$cutoff_days" 2>/dev/null \
        | xargs grep -l "C$n " 2>/dev/null \
        | wc -l | tr -d ' ')
    pressure+=("C$n:$mentions")
done

# Sort by pressure descending
printf "  ${DIM}30-day file-touch counts (which constraints are being worked on):${NC}\n"
for entry in "${pressure[@]}"; do
    local cid="${entry%%:*}"
    local count="${entry##*:}"
    if [ "$count" -ge 5 ]; then
        printf "    ${G}%s${NC}: %s files (active)\n" "$cid" "$count"
    elif [ "$count" -ge 1 ]; then
        printf "    ${Y}%s${NC}: %s files (light)\n" "$cid" "$count"
    else
        printf "    ${DIM}%s: 0 files (cold)${NC}\n" "$cid"
    fi
done

# CM check
local cm_mentions
cm_mentions=$(grep -rl "CM\b" "$ROOT" \
    --include='*.md' --include='*.sh' --include='*.py' \
    --exclude-dir='__pycache__' --exclude-dir='.hypothesis' 2>/dev/null \
    | wc -l | tr -d ' ')
if [ "$cm_mentions" -ge 3 ]; then
    ok "CM (meta-constraint) referenced in $cm_mentions files — meta-slot is filled"
elif [ "$cm_mentions" -ge 1 ]; then
    warn "CM referenced in only $cm_mentions file(s) — may not be load-bearing yet"
else
    broken "CM not referenced anywhere — meta-slot is unfilled"
fi
}

# -----------------------------------------------------------------------------
# Scripts — drift between ai-help.sh, CLAUDE.md, and actual disk state
# -----------------------------------------------------------------------------
check_scripts() {
section "Script-vs-doc drift"

# Verify ai-help.sh print_group calls reference real scripts
local help_refs
help_refs=$(grep -oE 'ai-[a-z-]+\.sh' "$HERE/ai-help.sh" 2>/dev/null | sort -u)
local help_missing=0
for s in $help_refs; do
    if [ ! -f "$HERE/$s" ]; then
        broken "ai-help.sh references $s but it doesn't exist"
        help_missing=$((help_missing + 1))
    fi
done
[ "$help_missing" -eq 0 ] && ok "ai-help.sh references match disk"

# Verify ai-done.sh doesn't reference missing scripts
local done_refs
done_refs=$(grep -oE 'ai-[a-z-]+\.sh' "$HERE/ai-done.sh" 2>/dev/null | sort -u)
local done_missing=0
for s in $done_refs; do
    if [ "$s" = "ai-done.sh" ]; then continue; fi
    if [ ! -f "$HERE/$s" ]; then
        broken "ai-done.sh references $s but it doesn't exist"
        done_missing=$((done_missing + 1))
    fi
done
[ "$done_missing" -eq 0 ] && ok "ai-done.sh references match disk"
}

# -----------------------------------------------------------------------------
# Meta-slot — the reserved 11th position
# -----------------------------------------------------------------------------
check_meta_slot() {
section "Meta-slot status (the previously-reserved 11th position)"

local lattice="$ROOT/meta/constraint-lattice.md"
local mission="$ROOT/MISSION.md"

if [ ! -f "$lattice" ]; then
    broken "constraint-lattice.md missing"
    return
fi

# The meta-slot is either:
#   (a) filled with CM constraint
#   (b) explicitly acknowledged as still-unfilled with documented reason
local cm_in_lattice
cm_in_lattice=$(grep -c "CM\b\|cognitive layer self-monitors" "$lattice" 2>/dev/null)
local cm_in_mission
cm_in_mission=$(grep -c "CM\b\|cognitive layer self-monitors" "$mission" 2>/dev/null)

if [ "$cm_in_lattice" -gt 0 ] && [ "$cm_in_mission" -gt 0 ]; then
    ok "meta-slot is FILLED with CM in both constraint-lattice.md and MISSION.md"

    # Verify CM has an enforcement
    if [ -x "$HERE/ai-meta.sh" ]; then
        ok "CM enforced by ai-meta.sh (this script)"
    else
        warn "CM claimed but no executable enforcement found"
    fi
elif [ "$cm_in_lattice" -gt 0 ] || [ "$cm_in_mission" -gt 0 ]; then
    warn "CM half-declared — present in one doc but not the other (drift)"
else
    warn "meta-slot still unfilled — neither lattice nor MISSION names CM"
fi

# Acknowledgement of the reserved position itself
if grep -qi "meta-slot\|reserved\|hidden 11th" "$lattice"; then
    ok "reserved-position acknowledgement present in constraint-lattice.md"
else
    broken "reserved meta-position not acknowledged in constraint-lattice.md"
fi
}

# -----------------------------------------------------------------------------
# check_sanctum — CM check #6, added v8.20 / R-sanctum-self-monitor
#
# The Sanctum is a cognitive-layer audit-of-record (see
# DEVNOTES/audit-of-record.md). CM enforcement extends to it: stale-OPEN
# sessions, lifecycle violations, and index drift between sanctum/ and
# meta/sanctum-index.md all constitute meta-drift.
# -----------------------------------------------------------------------------
check_sanctum() {
section "Sanctum integrity (v8.20 — CM #6)"

local sanctum_dir="$ROOT/sanctum"
local index_file="$ROOT/meta/sanctum-index.md"

if [ ! -d "$sanctum_dir" ]; then
    warn "sanctum/ directory missing — Sanctum protocol not yet bootstrapped"
    return
fi

if [ ! -f "$index_file" ]; then
    broken "meta/sanctum-index.md missing — index drift"
    return
fi

local now_epoch
now_epoch=$(date +%s)
local stale_threshold=$((7 * 86400))  # 7 days

local stale_open=0
local lifecycle_violations=0
local index_misses=0

for f in "$sanctum_dir"/*.md; do
    [ -f "$f" ] || continue
    [ "$(basename "$f")" = "README.md" ] && continue

    local status
    status=$(grep -E '^\*\*Status:\*\*' "$f" | head -1 | sed 's/^\*\*Status:\*\* *//' | tr -d ' ')

    case "$status" in
        OPEN)
            # Stale-OPEN check: file mtime older than 7 days.
            local file_mtime
            file_mtime=$(stat -f %m "$f" 2>/dev/null || stat -c %Y "$f" 2>/dev/null)
            if [ -n "$file_mtime" ] && [ $((now_epoch - file_mtime)) -gt $stale_threshold ]; then
                warn "stale OPEN session (>7 days): $(basename "$f")"
                stale_open=$((stale_open + 1))
            fi
            ;;
        CLOSED)
            # Lifecycle: CLOSED but §VII Outcome empty/placeholder.
            if grep -A 2 '^## VII\. Outcome' "$f" | tail -1 | grep -qE '^\(Filled in|^$'; then
                broken "lifecycle violation: CLOSED but §VII Outcome empty: $(basename "$f")"
                lifecycle_violations=$((lifecycle_violations + 1))
            fi
            ;;
        REJECTED)
            # Lifecycle: REJECTED but §VI Decision empty/placeholder.
            if grep -A 2 '^## VI\. Decision' "$f" | tail -1 | grep -qE '^\(Filled in|^$'; then
                broken "lifecycle violation: REJECTED but §VI Decision empty: $(basename "$f")"
                lifecycle_violations=$((lifecycle_violations + 1))
            fi
            ;;
        "")
            broken "session has no Status field: $(basename "$f")"
            lifecycle_violations=$((lifecycle_violations + 1))
            ;;
    esac

    # Index drift: closed/rejected sessions must appear in the index.
    if [ "$status" = "CLOSED" ] || [ "$status" = "REJECTED" ]; then
        if ! grep -q "$(basename "$f")" "$index_file"; then
            broken "index drift: $(basename "$f") not listed in meta/sanctum-index.md"
            index_misses=$((index_misses + 1))
        fi
    fi
done

# Reverse drift: index lists sessions that don't exist on disk.
while IFS= read -r referenced; do
    [ -z "$referenced" ] && continue
    if [ ! -f "$sanctum_dir/$referenced" ]; then
        broken "index drift: meta/sanctum-index.md references missing $referenced"
        index_misses=$((index_misses + 1))
    fi
done < <(grep -oE 'sanctum/[0-9]{4}-[0-9]{2}-[0-9]{2}-[a-z0-9-]+\.md' "$index_file" | sed 's|sanctum/||' | sort -u)

if [ $stale_open -eq 0 ] && [ $lifecycle_violations -eq 0 ] && [ $index_misses -eq 0 ]; then
    local total
    total=$(find "$sanctum_dir" -maxdepth 1 -name '*.md' ! -name 'README.md' 2>/dev/null | wc -l | tr -d ' ')
    ok "Sanctum integrity: $total session(s), no stale-OPEN, no lifecycle violations, no index drift"
fi
}

# -----------------------------------------------------------------------------
# Dispatch
# -----------------------------------------------------------------------------
case "$SECTION" in
    tools) check_tools ;;
    patterns) check_patterns ;;
    constraints) check_constraints ;;
    scripts) check_scripts ;;
    meta-slot) check_meta_slot ;;
    sanctum) check_sanctum ;;
    all|"")
        check_tools
        check_patterns
        check_constraints
        check_scripts
        check_meta_slot
        check_sanctum
        ;;
esac

# -----------------------------------------------------------------------------
# Summary
# -----------------------------------------------------------------------------
section "Meta-audit summary"
case "$DRIFT" in
    0)  printf "  ${G}${BOLD}LAYER SELF-MONITORING IS HEALTHY.${NC} CM constraint satisfied.\n" ;;
    [1-3]) printf "  ${Y}${BOLD}MINOR META-DRIFT.${NC} %s soft signal(s); investigate.\n" "$DRIFT" ;;
    *)  printf "  ${R}${BOLD}META-DRIFT.${NC} %s point(s) — the cognitive layer has drifted from its own claims.\n" "$DRIFT" ;;
esac

if [ "$STRICT" -eq 1 ] && [ "$DRIFT" -gt 0 ]; then
    exit 1
fi
exit 0
