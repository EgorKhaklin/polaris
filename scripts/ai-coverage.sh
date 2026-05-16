#!/usr/bin/env bash
# =============================================================================
# scripts/ai-coverage.sh
#
# For each MISSION.md hard constraint (C1-C10), report which tests exercise
# that constraint. A constraint without an exercising test is a coverage gap
# that should be addressed before the next release.
#
# This is not test-line coverage; it's CONSTRAINT coverage. A line of code
# can be 100% covered without any test verifying that it actually enforces
# the constraint it's supposed to enforce.
#
# Usage:
#     ai-coverage.sh                  # full report
#     ai-coverage.sh --gaps           # only show constraints with NO test
#     ai-coverage.sh C1               # detail for one constraint
#
# Portability note (v8.28): rewritten away from `declare -A` (bash 4+) to
# `case`-based dispatch so this works on macOS's default bash 3.2.57.
# =============================================================================

set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"

if [ -t 1 ]; then
    BOLD="\033[1m"; G="\033[0;32m"; Y="\033[0;33m"; R="\033[0;31m"
    DIM="\033[2m"; CYAN="\033[0;36m"; NC="\033[0m"
else
    BOLD=""; G=""; Y=""; R=""; DIM=""; CYAN=""; NC=""
fi

GAPS_ONLY=0
SPECIFIC=""
for arg in "$@"; do
    case "$arg" in
        --gaps) GAPS_ONLY=1 ;;
        C*) SPECIFIC="$arg" ;;
        --help|-h) sed -n '2,20p' "$0" | sed 's/^# \?//'; exit 0 ;;
    esac
done

# -----------------------------------------------------------------------------
# Constraint→search-pattern map. Each constraint is associated with one or
# more grep patterns we expect to find in the test files. If none of the
# patterns matches in any test file, the constraint has zero coverage.
#
# Patterns are case-insensitive and match against:
#   polaris_web/test_app.py
#   polaris_web/test_invariants_property.py
#   polaris_sql/08_tests.sql
#   polaris_sql/12_v7_constraints.sql (v7)
# -----------------------------------------------------------------------------
c_desc() {
    case "$1" in
        C1)  echo "Append-only audit (TokenLifecycleEvent, VerificationEvent UPDATE/DELETE rejected)" ;;
        C2)  echo "ZK→token_id NULL (chk_disclosure_token_consistency)" ;;
        C3)  echo "One ACTIVE token per individual (uq_one_active_per_person)" ;;
        C4)  echo "Atomic failed_login_count increment (no TOCTOU)" ;;
        C5)  echo "CSP script-src 'self' (no unsafe-inline)" ;;
        C6)  echo "Server-side disclosure level enforcement" ;;
        C7)  echo "CryptographicAlgorithm metadata flow" ;;
        C8)  echo "Atlas hard caps (_ATLAS_MAX_*)" ;;
        C9)  echo "ConcurrencyTests use real threading (not mocks)" ;;
        C10) echo "Identity ≠ money (no MonetaryClaim table)" ;;
    esac
}

c_pattern() {
    case "$1" in
        C1)  echo "C1_AppendOnlyProperties|append.only|reject_audit_modification|append_only|trg_lifecycle_append|trg_verification_append" ;;
        C2)  echo "C2_DisclosureTypingProperties|chk_disclosure_token|ZERO_KNOWLEDGE.*token_id|test_zero_knowledge|test_zk_with" ;;
        C3)  echo "C3_OneActivePerIndividualProperties|uq_one_active_per_person|one.active.per|test_second_active|partial.unique" ;;
        C4)  echo "ConcurrencyTests|failed_login_count|test_failed_login_count_is_atomic|atomic.increment" ;;
        C5)  echo "CSP|secure_headers|script-src|test_csp|content.security.policy" ;;
        C6)  echo "disclosure_level|test_zero_knowledge|test_full_without_token|test_disclosure" ;;
        C7)  echo "CryptographicAlgorithm|algorithm_id" ;;
        C8)  echo "_ATLAS_MAX|test_points_endpoint_caps|test_clusters_endpoint_caps|hard.cap|atlas.*max" ;;
        C9)  echo "ConcurrencyTests|threading|ThreadPoolExecutor" ;;
        C10) echo "MonetaryClaim" ;;
    esac
}

# -----------------------------------------------------------------------------
# Test corpus
# -----------------------------------------------------------------------------
TEST_FILES="$ROOT/polaris_web/test_app.py $ROOT/polaris_web/test_invariants_property.py $ROOT/polaris_sql/08_tests.sql $ROOT/polaris_sql/12_v7_constraints.sql"
EXISTING_TEST_FILES=""
for f in $TEST_FILES; do
    [ -f "$f" ] && EXISTING_TEST_FILES="$EXISTING_TEST_FILES $f"
done

# -----------------------------------------------------------------------------
# Header
# -----------------------------------------------------------------------------
printf "${BOLD}═══ ai-coverage: constraint → test mapping ═══${NC}\n\n"
printf "${DIM}Test corpus: %s${NC}\n\n" "$(echo $EXISTING_TEST_FILES | sed 's|/tmp/polaris_final/polaris/||g')"

# -----------------------------------------------------------------------------
# Walk constraints
# -----------------------------------------------------------------------------
TOTAL=0
COVERED=0
GAPS=0

for c in C1 C2 C3 C4 C5 C6 C7 C8 C9 C10; do
    [ -n "$SPECIFIC" ] && [ "$SPECIFIC" != "$c" ] && continue
    desc=$(c_desc "$c")
    pat=$(c_pattern "$c")
    TOTAL=$((TOTAL + 1))

    # C10 inverts: a MATCH is a VIOLATION (someone added MonetaryClaim).
    if [ "$c" = "C10" ]; then
        if grep -r -q -E "$pat" "$ROOT/polaris_sql/" 2>/dev/null; then
            printf "${R}✗${NC} ${BOLD}%s${NC}  %s\n" "$c" "$desc"
            printf "    ${R}VIOLATION:${NC} MonetaryClaim found in schema — C10 broken\n"
            grep -rn "MonetaryClaim" "$ROOT/polaris_sql/" 2>/dev/null | sed 's/^/    /' | head -3
            GAPS=$((GAPS + 1))
        else
            COVERED=$((COVERED + 1))
            [ "$GAPS_ONLY" -eq 0 ] && \
                printf "${G}✓${NC} ${BOLD}%s${NC}  %s\n    ${DIM}architectural — no MonetaryClaim table in schema${NC}\n" "$c" "$desc"
        fi
        continue
    fi

    # Other constraints: count tests that match the pattern
    matches=$(grep -l -E -i "$pat" $EXISTING_TEST_FILES 2>/dev/null)
    n_matches=0
    if [ -n "$matches" ]; then
        n_matches=$(echo "$matches" | wc -l)
    fi

    if [ "$n_matches" -gt 0 ]; then
        COVERED=$((COVERED + 1))
        [ "$GAPS_ONLY" -eq 1 ] && continue
        printf "${G}✓${NC} ${BOLD}%s${NC}  %s\n" "$c" "$desc"
        for f in $matches; do
            # BSD realpath (macOS) doesn't have --relative-to; use param expansion.
            rel="${f#$ROOT/}"
            count=$(grep -c -E -i "$pat" "$f")
            printf "    ${DIM}%-50s${NC} %s ref(s)\n" "$rel" "$count"
        done
        # If specific constraint requested, dump the matching test names
        if [ -n "$SPECIFIC" ]; then
            echo
            printf "    ${BOLD}Matching test names:${NC}\n"
            grep -E -i "def test_.*($pat)|class.*($pat)|TEST.*$c" $EXISTING_TEST_FILES 2>/dev/null | \
                sed 's|/tmp/polaris_final/polaris/||' | head -10 | sed 's/^/      /'
        fi
    else
        GAPS=$((GAPS + 1))
        printf "${R}✗${NC} ${BOLD}%s${NC}  %s\n" "$c" "$desc"
        printf "    ${R}GAP:${NC} no test exercises this constraint\n"
        printf "    ${DIM}search pattern: %s${NC}\n" "$pat"
    fi
done

# -----------------------------------------------------------------------------
# Summary
# -----------------------------------------------------------------------------
echo
printf "${BOLD}── Summary ──${NC}\n"
printf "  %s/%s constraints have at least one test reference.\n" "$COVERED" "$TOTAL"
if [ "$GAPS" -eq 0 ]; then
    printf "  ${G}${BOLD}No coverage gaps.${NC}\n"
else
    printf "  ${Y}${BOLD}%s gap(s)${NC} — see ${R}✗${NC} entries above.\n" "$GAPS"
    printf "  ${DIM}A gap means no test name or comment matches the constraint's pattern; it does NOT\n"
    printf "  necessarily mean the constraint is unenforced. But every gap is worth investigating.${NC}\n"
fi

# Exit code reflects coverage: 0 = clean, 1 = gaps
[ "$GAPS" -eq 0 ] && exit 0 || exit 1
