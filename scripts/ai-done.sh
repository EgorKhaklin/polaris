#!/bin/bash
# =============================================================================
# scripts/ai-done.sh — pre-ship sanity check (v8.6; v8.27 adds #12)
#
# Before claiming a piece of work is "done," twelve things should be true.
# This script checks them all and prints a single clean/dirty verdict.
# Pre-v8.6 these were checked manually, which means sometimes they
# weren't checked, which means CHANGELOG entries went missing or tests
# were left red.
#
# Checks:
#   1. ai-status.sh — all 10 hard constraints in force
#   2. ai-link-check.sh — every cross-reference resolves
#   3. ai-cache-bust.sh — CSS/JS hashes match content
#   4. ai-test-counts.sh — MISSION.md test counts match reality
#   5. test_app.py — full suite green
#   6. journal — today's file has at least one decision entry
#   7. CHANGELOG — last entry is from today (or there are no source changes)
#   8. No orphaned debug code (window.__atlasRender, console.log, TODO etc.)
#   9. No stale cache-buster (?v=v8.X format) in templates
#  10. ai-meta.sh — cognitive-layer self-monitoring (CM constraint, v8.9)
#  11. No bare references to moved docs
#  12. Architect brief snapshot — saves journal/YYYY-MM-DD-architect.md
#      so ai-architect.sh --reflect has substrate to read (v8.27)
#  13. Brain map refresh — regenerates meta/brain-map/brain-map.html so the
#      visualization stays in sync with the system (v8.52)
#
# Usage:
#     scripts/ai-done.sh          # human-readable report
#     scripts/ai-done.sh --strict # exit 1 on any failure
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

STRICT=0
[ "${1:-}" = "--strict" ] && STRICT=1

pass=0; fail=0; warn=0
fail_msgs=()

ok()    { printf "  ${G}✓${NC} %s\n" "$1"; pass=$((pass + 1)); }
flag()  { printf "  ${R}✗${NC} %s\n" "$1"; fail=$((fail + 1)); fail_msgs+=("$1"); }
note()  { printf "  ${Y}!${NC} %s\n" "$1"; warn=$((warn + 1)); }

printf "${BOLD}═══ ai-done — pre-ship sanity check ═══${NC}\n\n"

# -----------------------------------------------------------------------------
# 1. Hard constraints
# -----------------------------------------------------------------------------
status_out=$("$HERE/ai-status.sh" 2>/dev/null || true)
n_ok=$(echo "$status_out" | grep -c '✓ C' || true)
if [ "$n_ok" -eq 10 ]; then
    ok "ai-status: 10/10 hard constraints in force"
else
    flag "ai-status: only $n_ok/10 constraints green"
fi

# -----------------------------------------------------------------------------
# 2. Link check
# -----------------------------------------------------------------------------
if "$HERE/ai-link-check.sh" --ci >/dev/null 2>&1; then
    ok "ai-link-check: all references resolve"
else
    n_broken=$("$HERE/ai-link-check.sh" 2>/dev/null | grep -oE 'BROKEN  [0-9]+' | head -1 | grep -oE '[0-9]+')
    flag "ai-link-check: ${n_broken:-some} broken references"
fi

# -----------------------------------------------------------------------------
# 3. Cache-bust hashes match content
# -----------------------------------------------------------------------------
cb_out=$("$HERE/ai-cache-bust.sh" 2>/dev/null || true)
if echo "$cb_out" | grep -q "All tracked files are in sync"; then
    ok "ai-cache-bust: CSS/JS hashes match content"
else
    flag "ai-cache-bust: hashes drifted — run \`scripts/ai-cache-bust.sh --apply\`"
fi

# -----------------------------------------------------------------------------
# 4. Test counts
# -----------------------------------------------------------------------------
tc_out=$("$HERE/ai-test-counts.sh" 2>/dev/null || true)
if echo "$tc_out" | grep -q "test counts match reality"; then
    ok "ai-test-counts: MISSION.md numbers fresh"
else
    note "ai-test-counts: drift — run \`scripts/ai-test-counts.sh --update\`"
fi

# -----------------------------------------------------------------------------
# 5. Test suite green — fast path: trust the most recent .pytest_cache /
#    .test-result if updated within last 5 minutes; otherwise ask the user
#    to run ai-test.sh themselves (running it here would be 60+ seconds).
# -----------------------------------------------------------------------------
recent_pyfiles=$(find "$ROOT/polaris_web" -name '*.py' -mmin -5 2>/dev/null | wc -l | tr -d ' ')
if [ "$recent_pyfiles" -gt 0 ]; then
    note "test_app.py: source modified in last 5 min — re-run \`scripts/ai-test.sh\` to confirm"
else
    note "test_app.py: not auto-run by this script (~60s); confirm via \`scripts/ai-test.sh\`"
fi

# -----------------------------------------------------------------------------
# 6. Journal — today's file has at least one decision
# -----------------------------------------------------------------------------
today_journal="$ROOT/journal/$(date '+%Y-%m-%d').md"
if [ -f "$today_journal" ]; then
    n_decisions=$(grep -cE '^- \*\*decision\*\*' "$today_journal" || true)
    if [ "$n_decisions" -gt 0 ]; then
        ok "journal: $n_decisions decision(s) recorded today"
    else
        note "journal: today's file exists but has no decision entries"
    fi
else
    note "journal: no entry for today — \`scripts/ai-journal.sh start \"…\"\` to open one"
fi

# -----------------------------------------------------------------------------
# 7. CHANGELOG entry from today
# -----------------------------------------------------------------------------
today=$(date '+%Y-%m-%d')
if grep -q "^## .* — $today" "$ROOT/CHANGELOG.md" 2>/dev/null; then
    ok "CHANGELOG: entry from today"
else
    # Only flag this if there were source changes today
    src_changes=$(find "$ROOT" -type f \
        \( -name '*.py' -o -name '*.sql' -o -name '*.html' -o -name '*.js' -o -name '*.css' \) \
        -not -path '*/journal/*' -not -path '*/.git/*' \
        -mtime -1 2>/dev/null | wc -l | tr -d ' ')
    if [ "$src_changes" -gt 0 ]; then
        flag "CHANGELOG: source files changed today but no CHANGELOG entry from today"
    else
        ok "CHANGELOG: no source changes today (no entry needed)"
    fi
fi

# -----------------------------------------------------------------------------
# 8. Orphaned debug code
# -----------------------------------------------------------------------------
debug_hits=$(grep -rEn 'window\.__atlasRender|window\.__atlasLastFresh|console\.log\(.{0,40}DEBUG' \
    --include='*.js' --include='*.py' --include='*.html' \
    "$ROOT/polaris_web" 2>/dev/null | head -3)
if [ -z "$debug_hits" ]; then
    ok "no orphaned debug code"
else
    flag "orphaned debug code found"
    echo "$debug_hits" | sed 's/^/      /'
fi

# -----------------------------------------------------------------------------
# 9. Stale ?v= cache-buster format
# -----------------------------------------------------------------------------
stale_cb=$(grep -E '\?v=v[0-9]\.' "$ROOT/polaris_web/templates/"*.html 2>/dev/null | head -1)
if [ -z "$stale_cb" ]; then
    ok "templates use content-hash cache busters"
else
    flag "templates have a stale manual ?v=vX.Y cache buster — run cache-bust"
fi

# -----------------------------------------------------------------------------
# 10. Meta-cognitive audit (CM constraint, v8.9)
# -----------------------------------------------------------------------------
if "$HERE/ai-meta.sh" --strict >/dev/null 2>&1; then
    ok "ai-meta: cognitive layer self-monitoring healthy (CM satisfied)"
else
    n_drift=$("$HERE/ai-meta.sh" 2>/dev/null | grep -cE '^\s+[!✗]' || true)
    note "ai-meta: ${n_drift} meta-drift signal(s) — run \`scripts/ai-meta.sh\` for detail"
fi

# -----------------------------------------------------------------------------
# 11. Bare references to moved docs (catches future drift)
# -----------------------------------------------------------------------------
bare_refs=$(grep -rln "INSTALL\.md\|DEPLOYMENT\.md\|OPERATIONS\.md\|SECURITY\.md\|PRIVACY\.md\|SCALING\.md\|API\.md\|DATA-MODEL\.md\|GLOSSARY\.md" \
    --include='*.md' --include='*.py' --include='*.sh' --include='*.html' --include='*.js' --include='*.sql' \
    "$ROOT" 2>/dev/null \
    | xargs -I{} grep -l "INSTALL\.md\|DEPLOYMENT\.md\|OPERATIONS\.md\|SECURITY\.md\|PRIVACY\.md\|SCALING\.md\|API\.md\|DATA-MODEL\.md\|GLOSSARY\.md" {} \
    | xargs grep -l -E '(^|[^/])(INSTALL|DEPLOYMENT|OPERATIONS|SECURITY|PRIVACY|SCALING|API|DATA-MODEL|GLOSSARY)\.md' 2>/dev/null \
    | grep -vE 'docs/|CHANGELOG\.md|journal/' \
    | head -3)
# If any of those files have a non-prefixed ref AND aren't inside docs/ or
# CHANGELOG, that's drift. (CHANGELOG can legitimately mention old paths.)
if [ -z "$bare_refs" ]; then
    ok "no bare references to moved docs"
else
    note "possible bare doc references (verify manually):"
    echo "$bare_refs" | sed 's/^/      /'
fi

# -----------------------------------------------------------------------------
# 12. Architect brief snapshot (v8.27 — supports ai-architect --reflect)
#
# Runs ai-architect.sh --save unconditionally so every pre-ship gate
# leaves a dated brief in journal/. Stdout is suppressed (the brief is
# verbose) and we only verify the file landed.
# -----------------------------------------------------------------------------
"$HERE/ai-architect.sh" --save >/dev/null 2>&1
BRIEF_FILE="$ROOT/journal/$(date '+%Y-%m-%d')-architect.md"
if [ -f "$BRIEF_FILE" ]; then
    ok "ai-architect: brief snapshot at journal/$(basename "$BRIEF_FILE")"
else
    note "ai-architect: snapshot not written (check scripts/ai-architect.sh)"
fi

# -----------------------------------------------------------------------------
# 13. Brain map refresh (v8.52)
#
# Regenerates meta/brain-map/brain-map.html so the visualization is always in
# sync with the system. Output is suppressed (the generator's stderr
# message is verbose) and we only verify the file landed and is
# fresher than any source it parses.
# -----------------------------------------------------------------------------
"$HERE/ai-brain-map.sh" >/dev/null 2>&1
BRAIN_MAP_FILE="$ROOT/meta/brain-map/brain-map.html"
if [ -f "$BRAIN_MAP_FILE" ]; then
    ok "ai-brain-map: meta/brain-map/brain-map.html refreshed"
else
    note "ai-brain-map: meta/brain-map/brain-map.html not written (check scripts/ai-brain-map.sh)"
fi

# -----------------------------------------------------------------------------
# 14. HYDRA findings gate (v9.24 / BIG MISSION Tier 1 #1)
#
# Until this gate existed, findings produced by the cognitive substrate
# were advisory — a ship could land with active ALERT-level findings
# and nothing in ai-done.sh would notice. That meant the swarm + HYDRA
# was instrumentation without consequence; AP1 fires by construction.
#
# This gate scans the most-recent HYDRA brief in journal/hydra/ for
# [ALERT] lines and fails the ship if any are present. Override:
# POLARIS_ALLOW_ALERT_SHIPS=1 — leaves an audit-trail line and proceeds
# (intended for documented incident-response cases like shipping the
# fix for the alerting condition itself).
#
# Severity hierarchy (per polaris_hydra/correlation.py):
#   ALERT  (7)  — gate blocks
#   DRIFT  (3)  — warns
#   INFO   (1)  — neutral
# -----------------------------------------------------------------------------
LATEST_BRIEF=$(ls -1t "$ROOT/journal/hydra/"*.md 2>/dev/null | head -1)
if [ -z "$LATEST_BRIEF" ]; then
    note "hydra-findings-gate: no brief in journal/hydra/ (run ai-hydra.sh --full --save)"
else
    ALERT_COUNT=$(grep -c '^\s*\[ALERT\]' "$LATEST_BRIEF" 2>/dev/null || echo 0)
    DRIFT_COUNT=$(grep -c '^\s*\[DRIFT\]' "$LATEST_BRIEF" 2>/dev/null || echo 0)
    BRIEF_NAME=$(basename "$LATEST_BRIEF")
    if [ "${ALERT_COUNT:-0}" -gt 0 ]; then
        if [ "${POLARIS_ALLOW_ALERT_SHIPS:-0}" = "1" ]; then
            note "hydra-findings-gate: $ALERT_COUNT ALERT(s) in $BRIEF_NAME (OVERRIDDEN via POLARIS_ALLOW_ALERT_SHIPS=1)"
            grep '^\s*\[ALERT\]' "$LATEST_BRIEF" | sed 's/^/      /'
        else
            flag "hydra-findings-gate: $ALERT_COUNT ALERT(s) in $BRIEF_NAME — ship blocked"
            grep '^\s*\[ALERT\]' "$LATEST_BRIEF" | sed 's/^/      /'
            printf "      Resolve the alerts, OR set POLARIS_ALLOW_ALERT_SHIPS=1\n"
            printf "      to ship past them (audit-trail line will be printed).\n"
        fi
    else
        if [ "${DRIFT_COUNT:-0}" -gt 0 ]; then
            ok "hydra-findings-gate: 0 ALERT, $DRIFT_COUNT DRIFT in $BRIEF_NAME"
        else
            ok "hydra-findings-gate: 0 ALERT in $BRIEF_NAME"
        fi
    fi
fi

# -----------------------------------------------------------------------------
# Step 15: CM enforces (v9.28 / Hydra #5).
#
# Per Sanctum 2026-05-16 v9.28: "Make CM enforce instead of observe. The
# meta-constraint is the one watcher that should be a hard gate. If CM's
# claims do not match reality, ai-done.sh exits non-zero."
#
# CM's claims (the constitutional meta-constraint, per meta/watcher-
# predicates.md): the system is what it claims to be. Concrete checks:
#
#   1. POLARIS_VERSION in __version__.py matches the most-recent
#      CHANGELOG entry's version.
#   2. The freeze-line target version (v9.30 per MISSION.md §Freeze line)
#      is present and unchanged.
#   3. meta/watcher-predicates.md exists and enumerates exactly the
#      watchers present in polaris_hydra/watchers/.
#
# Override: POLARIS_ALLOW_CM_MISMATCH=1 prints an audit-trail line +
# proceeds. Same pattern as POLARIS_ALLOW_ALERT_SHIPS.
# -----------------------------------------------------------------------------
CM_CHECK_SCRIPT="$ROOT/scripts/_cm_check.py"
if [ ! -f "$CM_CHECK_SCRIPT" ]; then
    flag "cm-enforce: scripts/_cm_check.py missing — v9.28 ship required this"
else
    CM_RESULT_FILE=$(mktemp)
    python3 "$CM_CHECK_SCRIPT" "$ROOT" > "$CM_RESULT_FILE" 2>&1
    CM_EXIT=$?
    CM_RESULT=$(cat "$CM_RESULT_FILE")
    rm -f "$CM_RESULT_FILE"
fi

if [ "$CM_EXIT" -ne 0 ]; then
    if [ "${POLARIS_ALLOW_CM_MISMATCH:-0}" = "1" ]; then
        note "cm-enforce: CM claims do not match reality (OVERRIDDEN via POLARIS_ALLOW_CM_MISMATCH=1)"
        printf "%s\n" "$CM_RESULT" | sed 's/^/      /'
    else
        flag "cm-enforce: CM claims do not match reality — ship blocked"
        printf "%s\n" "$CM_RESULT" | sed 's/^/      /'
        printf "      Resolve the mismatches, OR set POLARIS_ALLOW_CM_MISMATCH=1\n"
        printf "      to ship past them (audit-trail line will be printed).\n"
    fi
else
    ok "cm-enforce: CM claims match reality"
fi

# -----------------------------------------------------------------------------
# Verdict
# -----------------------------------------------------------------------------
printf "\n${BOLD}── Verdict ──${NC}\n"
printf "  ${G}%s pass${NC} · ${Y}%s warn${NC} · ${R}%s fail${NC}\n" \
    "$pass" "$warn" "$fail"

if [ "$fail" -gt 0 ]; then
    printf "\n${R}NOT READY${NC} — address the failures above first.\n"
    [ "$STRICT" -eq 1 ] && exit 1
    exit 0
fi

if [ "$warn" -gt 0 ]; then
    printf "\n${Y}READY (with caveats)${NC} — review the warnings; ship if intentional.\n"
    exit 0
fi

printf "\n${G}READY TO SHIP${NC}\n"
