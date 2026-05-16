#!/bin/bash
# =============================================================================
# scripts/ai-test-counts.sh — auto-count tests + flag stale doc claims (v8.6)
#
# MISSION.md done-list item 7 makes a claim about test count. Pre-v8.5 the
# claim said "134 Python (incl. 10 Hypothesis) + 39 SQL" while reality
# was 196 Python — the number drifted across two releases without anyone
# updating the doc. This script:
#
#   1. Counts test methods across the Python suite (test_*.py files)
#   2. Counts SQL self-tests (DO blocks with PERFORM _record(...))
#   3. Compares against the claim in MISSION.md
#   4. Flags drift; --update writes the fresh number back
#
# Usage:
#     scripts/ai-test-counts.sh          # report only
#     scripts/ai-test-counts.sh --update # rewrite MISSION.md item 7
# =============================================================================

set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"

if [ -t 1 ]; then
    BOLD="\033[1m"; G="\033[0;32m"; Y="\033[0;33m"; R="\033[0;31m"
    DIM="\033[2m"; NC="\033[0m"
else
    BOLD=""; G=""; Y=""; R=""; DIM=""; NC=""
fi

UPDATE=0
[ "${1:-}" = "--update" ] && UPDATE=1

# -----------------------------------------------------------------------------
# Count Python test methods. Pattern: lines starting with `    def test_`
# inside test_*.py files. Class bodies use 4-space indent; the def goes
# inside a TestCase. Hypothesis-decorated methods are still `def test_...`
# so they're caught.
# -----------------------------------------------------------------------------
py_total=$(grep -rE '^\s{4}def test_[A-Za-z_]+\(' \
    "$ROOT/polaris_web"/test_*.py 2>/dev/null | wc -l | tr -d ' ')
py_classes=$(grep -rcE '^class [A-Z].*\b(unittest\.TestCase|TestCase|PolarisTestCase|UnauthenticatedTestCase)' \
    "$ROOT/polaris_web"/test_*.py 2>/dev/null | awk -F: '{s+=$2} END {print s}')
py_hypothesis=$(grep -rE '^\s+@given\(' \
    "$ROOT/polaris_web"/test_*.py 2>/dev/null | wc -l | tr -d ' ')

# -----------------------------------------------------------------------------
# Count SQL self-tests. Pattern: PERFORM _record(...) inside DO blocks in
# polaris_sql/08_tests.sql + polaris_sql/12_v7_constraints.sql + 13_substrate.
# -----------------------------------------------------------------------------
sql_total=$(grep -rE 'PERFORM\s+_record\s*\(' "$ROOT/polaris_sql/" 2>/dev/null | wc -l | tr -d ' ')

printf "${BOLD}Polaris test counts${NC}\n"
printf "  Python tests:  ${G}%s${NC} across ${G}%s${NC} TestCase classes\n" \
    "$py_total" "$py_classes"
printf "  Hypothesis property tests:  ${G}%s${NC}\n" "$py_hypothesis"
printf "  SQL self-tests:  ${G}%s${NC}\n" "$sql_total"
printf "\n"

# -----------------------------------------------------------------------------
# Compare against MISSION.md done-list item 7. The claim line is
#   "7. ✅ Test coverage: <N> Python ... + <M> SQL self-tests ..."
# We pull N and M with regex.
# -----------------------------------------------------------------------------
mission_line=$(grep -E '^7\. ✅ Test coverage:' "$ROOT/MISSION.md" | head -1)
if [ -z "$mission_line" ]; then
    printf "${Y}Could not find item 7 in MISSION.md done-list${NC}\n"
    exit 0
fi

claim_py=$(echo "$mission_line" | grep -oE '[0-9]+ Python' | head -1 | grep -oE '[0-9]+')
claim_sql=$(echo "$mission_line" | grep -oE '[0-9]+ SQL' | head -1 | grep -oE '[0-9]+')

drift=0
if [ -n "$claim_py" ] && [ "$claim_py" -ne "$py_total" ]; then
    printf "${Y}Drift:${NC} MISSION.md says ${R}%s${NC} Python; reality is ${G}%s${NC}\n" \
        "$claim_py" "$py_total"
    drift=1
fi
if [ -n "$claim_sql" ] && [ "$claim_sql" -ne "$sql_total" ]; then
    printf "${Y}Drift:${NC} MISSION.md says ${R}%s${NC} SQL self-tests; reality is ${G}%s${NC}\n" \
        "$claim_sql" "$sql_total"
    drift=1
fi
if [ "$drift" -eq 0 ]; then
    printf "${G}OK${NC}  MISSION.md test counts match reality\n"
    exit 0
fi

if [ "$UPDATE" -ne 1 ]; then
    printf "\n${DIM}Pass --update to rewrite MISSION.md item 7 with fresh numbers.${NC}\n"
    exit 0
fi

# -----------------------------------------------------------------------------
# --update mode — replace just the numbers, preserve the rest of the line.
# -----------------------------------------------------------------------------
new_line=$(printf "7. ✅ Test coverage: %s Python (12 test classes incl. property + redaction-property) + %s SQL self-tests (achieved v6/v7; growing each release — last counted via ai-test-counts.sh)" \
    "$py_total" "$sql_total")

# Macos `sed -i` differs from GNU; use a Python one-liner for portability
python3 - "$ROOT/MISSION.md" "$new_line" <<'PY'
import re, sys
path, new_line = sys.argv[1], sys.argv[2]
with open(path, encoding='utf-8') as f:
    src = f.read()
# Replace the entire line starting with "7. ✅ Test coverage:"
new = re.sub(r'^7\. ✅ Test coverage:.*$', new_line, src, count=1, flags=re.MULTILINE)
if new == src:
    sys.exit("No change made — pattern not found")
with open(path, 'w', encoding='utf-8') as f:
    f.write(new)
print("MISSION.md item 7 updated.")
PY
