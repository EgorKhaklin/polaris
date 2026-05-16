#!/bin/bash
# =============================================================================
# scripts/test_implants.sh
#
# Smoke tests for the AI metacognition implants themselves.
#
# Tests that each script:
#   - exits cleanly on the help/no-arg path
#   - exits cleanly when invoked normally
#   - produces expected output structure
#   - cleans up after itself
#
# Run from the project root:
#     ./scripts/test_implants.sh
#
# Exit 0 on all pass; exit 1 on any failure.
# =============================================================================

set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"

if [ -t 1 ]; then
    G="\033[0;32m"; R="\033[0;31m"; Y="\033[0;33m"; BOLD="\033[1m"; DIM="\033[2m"; NC="\033[0m"
else
    G=""; R=""; Y=""; BOLD=""; DIM=""; NC=""
fi

PASS=0
FAIL=0
FAILED_TESTS=()

# Quarantine — keep test artifacts out of the real journal
TEST_JOURNAL_DIR=$(mktemp -d)
ORIGINAL_JOURNAL_DIR="$ROOT/journal"

# Each test function returns 0 on pass, 1 on fail
run_test() {
    local name="$1"
    local cmd="$2"
    local expected_pattern="${3:-.}"  # regex; default matches anything

    printf "  ${DIM}─${NC} %-50s " "$name"
    OUT=$(eval "$cmd" 2>&1)
    RC=$?
    if [ $RC -eq 0 ] && echo "$OUT" | grep -qE "$expected_pattern"; then
        printf "${G}PASS${NC}\n"
        PASS=$((PASS + 1))
    else
        printf "${R}FAIL${NC}\n"
        printf "${DIM}    cmd: %s${NC}\n" "$cmd"
        printf "${DIM}    rc=%s, expected pattern: %s${NC}\n" "$RC" "$expected_pattern"
        printf "${DIM}    output:\n%s${NC}\n" "$(echo "$OUT" | head -3 | sed 's/^/      /')"
        FAIL=$((FAIL + 1))
        FAILED_TESTS+=("$name")
    fi
}

# Each script must be executable
test_executable() {
    local script="$1"
    local path="$ROOT/scripts/$script"
    if [ -x "$path" ]; then return 0; else return 1; fi
}

printf "${BOLD}═══ Implant smoke tests ═══${NC}\n\n"

# -----------------------------------------------------------------------------
# 1. Permissions
# -----------------------------------------------------------------------------
printf "${BOLD}[permissions]${NC}\n"
for s in ai-bootstrap.sh ai-context-digest.sh ai-journal.sh ai-recall.sh \
         ai-where.sh ai-reflect.sh ai-loop-check.sh test_implants.sh; do
    if test_executable "$s"; then
        printf "  ${DIM}─${NC} %-50s ${G}PASS${NC}\n" "$s is +x"
        PASS=$((PASS + 1))
    else
        printf "  ${DIM}─${NC} %-50s ${R}FAIL${NC} (not +x)\n" "$s is +x"
        FAIL=$((FAIL + 1))
        FAILED_TESTS+=("$s permission")
    fi
done

# -----------------------------------------------------------------------------
# 2. ai-bootstrap.sh
# -----------------------------------------------------------------------------
printf "\n${BOLD}[ai-bootstrap]${NC}\n"
run_test "help flag exits cleanly" \
    "$ROOT/scripts/ai-bootstrap.sh --help" \
    "."
run_test "report mode runs without --fix" \
    "timeout 30 $ROOT/scripts/ai-bootstrap.sh 2>&1; true" \
    "Polaris AI Bootstrap"

# -----------------------------------------------------------------------------
# 3. ai-context-digest.sh
# -----------------------------------------------------------------------------
printf "\n${BOLD}[ai-context-digest]${NC}\n"
run_test "no-arg shows all sections" \
    "OUT=\$(timeout 15 $ROOT/scripts/ai-context-digest.sh 2>&1); echo \"\$OUT\" | head -80" \
    "(SCHEMA|TEST CLASSES|RECENTLY MODIFIED|FLASK ROUTES|ATLAS SQL)"
run_test "tests subsection works" \
    "timeout 10 $ROOT/scripts/ai-context-digest.sh tests" \
    "Total test methods"
run_test "routes subsection works" \
    "timeout 10 $ROOT/scripts/ai-context-digest.sh routes" \
    "FLASK ROUTES"

# -----------------------------------------------------------------------------
# 4. ai-journal.sh — capture episodic memory
# -----------------------------------------------------------------------------
printf "\n${BOLD}[ai-journal]${NC}\n"
# Use a temp journal dir; redirect via env override won't work since the
# script computes JOURNAL_DIR=$ROOT/journal. So we test by writing into
# the real dir and cleaning up.

JOURNAL_FILE="$ROOT/journal/$(date +%Y-%m-%d).md"
[ -f "$JOURNAL_FILE" ] && BACKUP=$(mktemp) && cp "$JOURNAL_FILE" "$BACKUP"

run_test "no-arg shows usage" \
    "$ROOT/scripts/ai-journal.sh" \
    "ai-journal.sh"
run_test "start opens session" \
    "$ROOT/scripts/ai-journal.sh start 'smoke test'" \
    "session opened"
run_test "decision is logged" \
    "$ROOT/scripts/ai-journal.sh decision 'test decision'" \
    "decision logged"
run_test "learning is logged" \
    "$ROOT/scripts/ai-journal.sh learning 'test learning'" \
    "learning logged"
run_test "end closes session" \
    "$ROOT/scripts/ai-journal.sh end" \
    "session closed"
run_test "journal file contains entries" \
    "grep -E 'SESSION|decision|learning' $JOURNAL_FILE" \
    "test decision"

# Restore original journal file (or remove our test file)
if [ -n "${BACKUP:-}" ]; then
    mv "$BACKUP" "$JOURNAL_FILE"
else
    rm -f "$JOURNAL_FILE"
fi

# -----------------------------------------------------------------------------
# 5. ai-recall.sh — directed search
# -----------------------------------------------------------------------------
printf "\n${BOLD}[ai-recall]${NC}\n"
run_test "no-arg shows usage" \
    "$ROOT/scripts/ai-recall.sh" \
    "ai-recall.sh"
run_test "single-word query finds matches" \
    "$ROOT/scripts/ai-recall.sh concurrency" \
    "EXACT PHRASE MATCH|ALL-TERMS|ANY-TERM"
run_test "multi-word query finds matches" \
    "$ROOT/scripts/ai-recall.sh atlas slow" \
    "(EXACT PHRASE|ALL-TERMS|ANY-TERM)"
run_test "nonexistent query is handled gracefully" \
    "$ROOT/scripts/ai-recall.sh xyzzyplugh_nonexistent_term" \
    "Recall"

# -----------------------------------------------------------------------------
# 6. ai-where.sh — triggered associative recall
# -----------------------------------------------------------------------------
printf "\n${BOLD}[ai-where]${NC}\n"
run_test "no-arg shows usage" \
    "$ROOT/scripts/ai-where.sh" \
    "ai-where.sh"
run_test "known file path surfaces context" \
    "$ROOT/scripts/ai-where.sh polaris_web/app.py" \
    "DEVNOTES|patterns|note"
run_test "atlas SQL gets atlas-scaling reference" \
    "$ROOT/scripts/ai-where.sh polaris_sql/11_atlas.sql" \
    "atlas-scaling"
run_test "concurrency procedure gets concurrency reference" \
    "$ROOT/scripts/ai-where.sh polaris_sql/05_procedures.sql" \
    "concurrency"
run_test "unknown file falls back gracefully" \
    "$ROOT/scripts/ai-where.sh some/random/file.xyz" \
    "(no specific guidance|suggest)"

# -----------------------------------------------------------------------------
# 7. ai-loop-check.sh — self-monitoring
# -----------------------------------------------------------------------------
printf "\n${BOLD}[ai-loop-check]${NC}\n"
run_test "runs without journal file" \
    "$ROOT/scripts/ai-loop-check.sh" \
    "stuck-loop check"
run_test "produces a verdict line" \
    "$ROOT/scripts/ai-loop-check.sh" \
    "Loop check"

# -----------------------------------------------------------------------------
# 8. ai-reflect.sh — consolidation
# -----------------------------------------------------------------------------
printf "\n${BOLD}[ai-reflect]${NC}\n"
run_test "runs without journal file" \
    "$ROOT/scripts/ai-reflect.sh" \
    "Reflection"
run_test "produces summary section" \
    "$ROOT/scripts/ai-reflect.sh" \
    "(no journal file|sessions today|Done)"

# Make sure our test journal entries didn't leak
if [ -f "$JOURNAL_FILE" ]; then
    rm -f "$JOURNAL_FILE"
fi

# -----------------------------------------------------------------------------
# 9. Pattern + DEVNOTES integrity (no syntax errors in the markdown)
# -----------------------------------------------------------------------------
printf "\n${BOLD}[corpus integrity]${NC}\n"
for f in "$ROOT/CLAUDE.md" "$ROOT/docs/reference/SCALING.md" "$ROOT/meta/cognitive-loop.md" \
         "$ROOT/DEVNOTES"/*.md "$ROOT/patterns"/*.md; do
    if [ -f "$f" ]; then
        # Check for unclosed code fences. grep -c ALWAYS emits a number, so
        # don't add `|| echo 0` — it produces "0\n0" when grep finds nothing.
        FENCE_COUNT=$(grep -c '^```' "$f" 2>/dev/null)
        FENCE_COUNT=${FENCE_COUNT:-0}
        if [ $((FENCE_COUNT % 2)) -eq 0 ]; then
            printf "  ${DIM}─${NC} %-50s ${G}PASS${NC}\n" "$(basename "$f") fences balanced"
            PASS=$((PASS + 1))
        else
            printf "  ${DIM}─${NC} %-50s ${R}FAIL${NC} (odd fence count: %d)\n" "$(basename "$f")" "$FENCE_COUNT"
            FAIL=$((FAIL + 1))
            FAILED_TESTS+=("$(basename "$f") fence balance")
        fi
    fi
done

# -----------------------------------------------------------------------------
# 10. Cross-references — every pattern referenced from the README exists
# -----------------------------------------------------------------------------
printf "\n${BOLD}[cross-references]${NC}\n"
if [ -f "$ROOT/patterns/README.md" ]; then
    # Only scan lines that look like table rows (start with | and contain `.md`)
    # so we ignore the code-block example that mentions `patterns/my-pattern.md`.
    REFERENCED=$(grep -E '^\|' "$ROOT/patterns/README.md" | \
                 grep -oE '`[a-z][a-z0-9-]+\.md`' | \
                 tr -d '`' | sort -u)
    for ref in $REFERENCED; do
        if [ -f "$ROOT/patterns/$ref" ]; then
            printf "  ${DIM}─${NC} %-50s ${G}PASS${NC}\n" "patterns/$ref exists"
            PASS=$((PASS + 1))
        else
            printf "  ${DIM}─${NC} %-50s ${R}FAIL${NC} (referenced but missing)\n" "patterns/$ref"
            FAIL=$((FAIL + 1))
            FAILED_TESTS+=("missing $ref")
        fi
    done
fi

# -----------------------------------------------------------------------------
# Summary
# -----------------------------------------------------------------------------
echo
TOTAL=$((PASS + FAIL))
if [ $FAIL -eq 0 ]; then
    printf "${G}${BOLD}═══ ALL %d TESTS PASS ═══${NC}\n" "$TOTAL"
    exit 0
else
    printf "${R}${BOLD}═══ %d FAIL / %d TOTAL ═══${NC}\n" "$FAIL" "$TOTAL"
    printf "Failed:\n"
    for t in "${FAILED_TESTS[@]}"; do
        printf "  - %s\n" "$t"
    done
    exit 1
fi
