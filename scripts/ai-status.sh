#!/bin/bash
# =============================================================================
# scripts/ai-status.sh
#
# Where is Polaris vs MISSION.md, right now?
#
# Reports:
#   - Hard constraints C1-C10: which are still in force, which look at risk
#   - Done-list (1-15): what's complete, what's in progress, what's pending
#   - Roadmap: what's active in v7, v8, v9
#   - Recent activity: changelog entries, journal entries, last reflection
#   - Drift signals: dangling threads, file-mtime hotspots, scope-creep flags
#
# Brain analog: introspection. "Where am I in the plan? What's the current
# state of the world relative to what I'm trying to achieve?" The prefrontal
# cortex's continuous self-assessment.
#
# Usage:
#     ai-status.sh                     # full report
#     ai-status.sh constraints         # just C1-C10 check
#     ai-status.sh done-list           # just done-list progress
#     ai-status.sh roadmap             # just roadmap state
# =============================================================================

set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"

if [ -t 1 ]; then
    BOLD="\033[1m"; G="\033[0;32m"; Y="\033[0;33m"; R="\033[0;31m"
    CYAN="\033[0;36m"; DIM="\033[2m"; NC="\033[0m"
else
    BOLD=""; G=""; Y=""; R=""; CYAN=""; DIM=""; NC=""
fi

ok()      { printf "  ${G}✓${NC} %s\n" "$1"; }
warn()    { printf "  ${Y}!${NC} %s\n" "$1"; STATUS_DEGRADED=1; }
broken()  { printf "  ${R}✗${NC} %s\n" "$1"; STATUS_DEGRADED=2; }
section() { printf "\n${BOLD}── %s ──${NC}\n" "$1"; }

STATUS_DEGRADED=0
SECTION="${1:-all}"

# Sanity check: we need MISSION.md
if [ ! -f "$ROOT/MISSION.md" ]; then
    printf "${R}MISSION.md not found at %s${NC}\n" "$ROOT/MISSION.md"
    printf "Cannot evaluate status without a mission.\n"
    exit 2
fi

# -----------------------------------------------------------------------------
# Header
# -----------------------------------------------------------------------------
printf "${BOLD}═══ Polaris status ═══${NC}\n"
printf "${DIM}  Date:  %s${NC}\n" "$(date '+%Y-%m-%d %H:%M:%S')"
printf "${DIM}  Root:  %s${NC}\n" "$ROOT"

# -----------------------------------------------------------------------------
# Constraints check (C1-C10)
# -----------------------------------------------------------------------------
check_constraints() {
section "Hard constraints (MISSION.md C1–C10)"

# C1: append-only triggers exist
if [ -f "$ROOT/polaris_sql/06_triggers.sql" ] && \
   grep -q -E "REJECT.*UPDATE.*DELETE|reject_update_delete|append.only" \
       "$ROOT/polaris_sql/06_triggers.sql" 2>/dev/null; then
    ok "C1  append-only triggers present (06_triggers.sql)"
else
    broken "C1  append-only triggers missing or weakened"
fi

# C2: ZK token_id NULL enforcement
# Enforced by the disclosure_consistency CHECK constraint in 01_schema.sql
# (CHECK ((disclosure_level = 'ZERO_KNOWLEDGE' AND token_id IS NULL) OR …)).
# Either the CHECK or a trigger is acceptable — grep both shapes.
if grep -q -i "disclosure_consistency\|disclosure_level *= *'ZERO_KNOWLEDGE' *AND *token_id *IS *NULL\|enforce.*zk\|zk.*null" \
       "$ROOT/polaris_sql/01_schema.sql" "$ROOT/polaris_sql/06_triggers.sql" 2>/dev/null; then
    ok "C2  ZK→token_id NULL enforcement present"
else
    warn "C2  ZK enforcement not found by grep — verify manually"
fi

# C3: partial unique index for one-active-per-person
if grep -r -q "uq_one_active_per_person\|UNIQUE.*INDEX.*WHERE.*status.*=.*'ACTIVE'" \
       "$ROOT/polaris_sql/" 2>/dev/null; then
    ok "C3  uq_one_active_per_person partial unique index present"
else
    broken "C3  one-active-per-person guarantee missing"
fi

# C4: atomic increment in security.py
if grep -q "failed_login_count = failed_login_count + 1\|RETURNING failed_login_count" \
       "$ROOT/polaris_web/security.py" 2>/dev/null; then
    ok "C4  atomic failed_login_count increment present"
else
    broken "C4  TOCTOU regression — failed_login_count not atomic"
fi

# C5: CSP not weakened
if grep -q "script-src 'self'" "$ROOT/polaris_web/security.py" 2>/dev/null; then
    ok "C5  CSP script-src 'self' in force"
elif grep -q "unsafe-inline\|unsafe-eval" "$ROOT/polaris_web/security.py" 2>/dev/null; then
    broken "C5  CSP weakened (unsafe-inline or unsafe-eval present)"
else
    warn "C5  CSP rule not found by grep — verify manually"
fi

# C6: server-side disclosure enforcement
if grep -q "disclosure_level\|enforce_zk\|ZERO_KNOWLEDGE" \
       "$ROOT/polaris_web/app.py" 2>/dev/null; then
    ok "C6  disclosure level enforced server-side"
else
    warn "C6  disclosure enforcement not found by grep"
fi

# C7: CryptographicAlgorithm table
if grep -q "CryptographicAlgorithm" \
       "$ROOT/polaris_sql/01_schema.sql" 2>/dev/null; then
    ok "C7  CryptographicAlgorithm table present"
else
    broken "C7  algorithm metadata missing or hardcoded"
fi

# C8: hard caps on atlas endpoints
if grep -q "_ATLAS_MAX_CLUSTERS\|_ATLAS_MAX_POINTS\|_ATLAS_MAX_EVENTS" \
       "$ROOT/polaris_web/app.py" 2>/dev/null; then
    ok "C8  hard caps present on /api/atlas/* endpoints"
else
    broken "C8  unbounded atlas API responses"
fi

# C9: ConcurrencyTests with real threading
if grep -q -E "(threading|ThreadPoolExecutor)" \
       "$ROOT/polaris_web/test_app.py" 2>/dev/null && \
   grep -q "class ConcurrencyTests" "$ROOT/polaris_web/test_app.py" 2>/dev/null; then
    ok "C9  ConcurrencyTests use real threading"
else
    broken "C9  concurrency tests missing or use mocks"
fi

# C10: no MonetaryClaim table (identity != money)
if grep -r -q "CREATE TABLE.*MonetaryClaim\|MonetaryClaim" \
       "$ROOT/polaris_sql/" 2>/dev/null; then
    broken "C10 MonetaryClaim table found — IDENTITY ≠ MONEY violated"
else
    ok "C10 identity layer is identity-only (no MonetaryClaim table)"
fi
}

# -----------------------------------------------------------------------------
# Done-list progress
# -----------------------------------------------------------------------------
check_done_list() {
section "Mission done-list"

local mission="$ROOT/MISSION.md"

# v1 done-list: numbered "1." through "15." with status emoji.
# Use head -1 around grep -c to defeat the multi-line bug where some
# greps emit "0\n0" on no-match.
local v1_complete v1_pending v1_progress v1_retired
v1_complete=$(grep -cE "^[0-9]+\. ✅"  "$mission" 2>/dev/null | head -1)
v1_progress=$(grep -cE "^[0-9]+\. 🟡"  "$mission" 2>/dev/null | head -1)
v1_pending=$(grep -cE  "^[0-9]+\. ⬜"  "$mission" 2>/dev/null | head -1)
# Retired = out-of-scope items kept on the list for audit-of-record (v8.26).
# Count both ✗ RETIRED (post-v8.26) and ⏸ DEFERRED (pre-v8.26) for back-compat.
v1_retired=$(grep -cE "^[0-9]+\. (✗|⏸)"  "$mission" 2>/dev/null | head -1)

# v2 done-list: numbered "M2-N." with status emoji.
local v2_complete v2_pending v2_progress
v2_complete=$(grep -cE "^M2-[0-9]+\. ✅"  "$mission" 2>/dev/null | head -1)
v2_progress=$(grep -cE "^M2-[0-9]+\. 🟡"  "$mission" 2>/dev/null | head -1)
v2_pending=$(grep -cE  "^M2-[0-9]+\. ⬜"  "$mission" 2>/dev/null | head -1)

printf "  ${BOLD}v1${NC} (closed): ${G}%s ✅${NC} · ${Y}%s 🟡${NC} · ${DIM}%s ⬜${NC} · ✗ %s retired\n" \
    "${v1_complete:-0}" "${v1_progress:-0}" "${v1_pending:-0}" "${v1_retired:-0}"
# v8.28 — v2 label flips from "(active)" to "(closed)" once all M2-* items
# show ✅. Until v3 is opened, the post-v2 strategic moment is documented in
# MISSION.md's "Post-v2 strategic moment" section.
if [ "${v2_pending:-0}" -eq 0 ] && [ "${v2_progress:-0}" -eq 0 ] && [ "${v2_complete:-0}" -gt 0 ]; then
    v2_state="closed"
else
    v2_state="active"
fi
printf "  ${BOLD}v2${NC} (%s): ${G}%s ✅${NC} · ${Y}%s 🟡${NC} · ${DIM}%s ⬜${NC}\n" \
    "$v2_state" "${v2_complete:-0}" "${v2_progress:-0}" "${v2_pending:-0}"
echo

echo "  v2 done-list (D + A — substrate + open problems):"
grep -E "^M2-[0-9]+\. [✅🟡⬜]" "$mission" 2>/dev/null \
    | sed -E 's/(\*\*[^*]*\*\*).*/\1/' \
    | sed 's/^/    /' \
    | head -20
}

# -----------------------------------------------------------------------------
# Roadmap state
# -----------------------------------------------------------------------------
check_roadmap() {
section "Active roadmap (ROADMAP.md)"

if [ ! -f "$ROOT/ROADMAP.md" ]; then
    warn "ROADMAP.md not found — run ai-propose.sh to bootstrap"
    return
fi

local r7 r7d r8 r8d r9 r10 r10d r11 r11d
# head -1 trick to defeat the multi-line bug some greps emit on no match
r7=$(grep -cE  "^### R7-"  "$ROOT/ROADMAP.md" 2>/dev/null | head -1)
r7d=$(grep -cE "^### ✅ R7-" "$ROOT/ROADMAP.md" 2>/dev/null | head -1)
r8=$(grep -cE  "^### R8-"  "$ROOT/ROADMAP.md" 2>/dev/null | head -1)
r8d=$(grep -cE "^### ✅ R8-" "$ROOT/ROADMAP.md" 2>/dev/null | head -1)
r9=$(grep -cE  "^### R9-"  "$ROOT/ROADMAP.md" 2>/dev/null | head -1)
r10=$(grep -cE "^### R10-" "$ROOT/ROADMAP.md" 2>/dev/null | head -1)
r10d=$(grep -cE "^### ✅ R10-" "$ROOT/ROADMAP.md" 2>/dev/null | head -1)
r11=$(grep -cE "^### R11-" "$ROOT/ROADMAP.md" 2>/dev/null | head -1)
r11d=$(grep -cE "^### ✅ R11-" "$ROOT/ROADMAP.md" 2>/dev/null | head -1)

# v8.28 — labels are roadmap-arc groupings (R10-* / R11-* prefixes), not
# version numbers. Earlier display said "v10/v11" which read as "version 10/11"
# (we're at v8.28). Renamed to "R10-* arc" / "R11-* arc" for clarity. R9 items
# are RETIRED post-v8.27, not deferred — label updated accordingly.
printf "  ${BOLD}v7 (closed):${NC}        %s items (%s ✅)\n" "${r7:-0}" "${r7d:-0}"
printf "  ${BOLD}v8 (closed):${NC}        %s items (%s ✅)\n" "${r8:-0}" "${r8d:-0}"
printf "  ${BOLD}v9 (retired):${NC}       %s items\n" "${r9:-0}"
printf "  ${BOLD}R10-* arc (closed):${NC} %s items (%s ✅)  ${DIM}— substrate D${NC}\n" "${r10:-0}" "${r10d:-0}"
printf "  ${BOLD}R11-* arc (closed):${NC} %s items (%s ✅)  ${DIM}— open-problems A${NC}\n" "${r11:-0}" "${r11d:-0}"
# Only print the open-arc detail blocks if there are open items. After v2
# closure (12/12 ✅) these blocks are empty noise.
r10_open=$(( ${r10:-0} - ${r10d:-0} ))
r11_open=$(( ${r11:-0} - ${r11d:-0} ))
if [ "$r10_open" -gt 0 ] || [ "$r11_open" -gt 0 ]; then
    echo
    if [ "$r10_open" -gt 0 ]; then
        echo "  R10-* substrate-arc open items (D):"
        grep "^### R10-" "$ROOT/ROADMAP.md" 2>/dev/null | grep -v "✅" | sed 's/^### /    /' | head -10
    fi
    if [ "$r11_open" -gt 0 ]; then
        echo "  R11-* open-problems items (A):"
        grep "^### R11-" "$ROOT/ROADMAP.md" 2>/dev/null | grep -v "✅" | sed 's/^### /    /' | head -10
    fi
fi
}

# -----------------------------------------------------------------------------
# Recent activity
# -----------------------------------------------------------------------------
check_activity() {
section "Recent activity"

# CHANGELOG: lines under most recent version
local version_line
version_line=$(grep -n "^## v[0-9]" "$ROOT/CHANGELOG.md" 2>/dev/null | head -1 | cut -d: -f1)
if [ -n "$version_line" ]; then
    local current_version
    current_version=$(sed -n "${version_line}p" "$ROOT/CHANGELOG.md" | sed 's/^## //')
    printf "  Most recent CHANGELOG section: ${BOLD}%s${NC}\n" "$current_version"
fi

# Journal entries
if [ -d "$ROOT/journal" ]; then
    local journal_count latest_journal
    journal_count=$(find "$ROOT/journal" -name '*.md' -type f ! -name 'README.md' 2>/dev/null | wc -l)
    latest_journal=$(find "$ROOT/journal" -name '20*.md' -type f 2>/dev/null | sort | tail -1)
    printf "  Journal entries: %s\n" "$journal_count"
    if [ -n "$latest_journal" ]; then
        printf "    Latest: %s\n" "$(realpath --relative-to="$ROOT" "$latest_journal" 2>/dev/null)"
    fi
fi

# Last reflection
if [ -f "$ROOT/meta/last-reflection.md" ]; then
    local refl_when
    refl_when=$(grep "^Date:" "$ROOT/meta/last-reflection.md" 2>/dev/null | head -1)
    printf "  Last reflection: %s\n" "${refl_when:-unknown}"
fi

# Recently modified source files
section "Recently modified source files (last 5)"
find "$ROOT" -type f \( -name '*.py' -o -name '*.sql' -o -name '*.js' -o -name '*.html' \) \
    -not -path '*/__pycache__/*' -not -path '*/vendor/*' \
    -printf '%T@ %p\n' 2>/dev/null | sort -rn | head -5 | while read -r ts path; do
    printf "  ${DIM}%s${NC}  %s\n" \
        "$(date -d @"${ts%.*}" '+%Y-%m-%d %H:%M' 2>/dev/null || echo '         ')" \
        "$(realpath --relative-to="$ROOT" "$path" 2>/dev/null)"
done
}

# -----------------------------------------------------------------------------
# Drift signals
# -----------------------------------------------------------------------------
check_drift() {
section "Drift signals"

# Dangling threads in journal
local dangling=0
if [ -d "$ROOT/journal" ]; then
    dangling=$(grep -hi -E "^- \*\*(bug|note)\*\*.*(TODO|FIXME|left for|tabled|come back to|incomplete)" \
        "$ROOT/journal/"*.md 2>/dev/null | wc -l)
fi
if [ "$dangling" -gt 0 ]; then
    warn "$dangling dangling thread mentions in journal"
else
    ok "no dangling-thread mentions in journal"
fi

# Roadmap items older than 30 days untouched
if [ -f "$ROOT/ROADMAP.md" ]; then
    local roadmap_age
    roadmap_age=$(stat -c %Y "$ROOT/ROADMAP.md" 2>/dev/null || stat -f %m "$ROOT/ROADMAP.md" 2>/dev/null || echo 0)
    local now=$(date +%s)
    local days_since=$(( (now - roadmap_age) / 86400 ))
    if [ "$days_since" -gt 30 ]; then
        warn "ROADMAP.md unchanged for $days_since days — possible stagnation"
    else
        ok "ROADMAP.md updated within last $days_since days"
    fi
fi

# Tests in test_app.py vs production routes
if [ -f "$ROOT/polaris_web/test_app.py" ] && [ -f "$ROOT/polaris_web/app.py" ]; then
    local routes tests
    routes=$(grep -c "^@app.route" "$ROOT/polaris_web/app.py" 2>/dev/null || echo 0)
    tests=$(grep -cE "^    def test_" "$ROOT/polaris_web/test_app.py" 2>/dev/null || echo 0)
    if [ "$tests" -lt "$routes" ]; then
        warn "tests ($tests) < routes ($routes) — coverage may be lagging"
    else
        ok "test count ($tests) ≥ route count ($routes)"
    fi
fi
}

# -----------------------------------------------------------------------------
# Summary
# -----------------------------------------------------------------------------
print_summary() {
section "Summary"

case "$STATUS_DEGRADED" in
    0) printf "  ${G}${BOLD}MISSION ALIGNED.${NC} All hard constraints in force; "
       printf "no drift signals.\n" ;;
    1) printf "  ${Y}${BOLD}DEGRADED — soft signals.${NC} Investigate warnings; "
       printf "no broken constraints.\n" ;;
    2) printf "  ${R}${BOLD}MISSION VIOLATION.${NC} A hard constraint failed. "
       printf "Address before proceeding.\n" ;;
esac

printf "\n${DIM}Next: ai-propose.sh to identify the highest-value next move.${NC}\n"
}

# -----------------------------------------------------------------------------
# Dispatch
# -----------------------------------------------------------------------------
case "$SECTION" in
    constraints) check_constraints ;;
    done-list)   check_done_list ;;
    roadmap)     check_roadmap ;;
    activity)    check_activity ;;
    drift)       check_drift ;;
    all|"")
        check_constraints
        check_done_list
        check_roadmap
        check_activity
        check_drift
        print_summary
        ;;
    *) echo "Unknown section: $SECTION"; exit 1 ;;
esac

exit 0
