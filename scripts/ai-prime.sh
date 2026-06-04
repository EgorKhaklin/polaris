#!/bin/bash
# =============================================================================
# scripts/ai-prime.sh — single-command session primer (v8.5)
#
# A fresh agent session needs to know:
#   1. What is Polaris (mission)? — already in MISSION.md
#   2. What's the current state (constraints, done-list)? — ai-status.sh
#   3. What should I do next? — ai-propose.sh
#   4. What did the previous session do / decide? — tail of journal
#   5. What's been touched recently in the source? — git status surrogate
#
# Pre-v8.5, all of the above required running 4-5 commands in order. This
# script runs them as one, emits ≤80 lines of cohesive output, and points
# at the next move. Designed so a fresh CLAUDE.md reader can get up to
# speed in ~30 seconds: read CLAUDE.md, run ai-prime.sh, ready.
#
# Usage:
#     scripts/ai-prime.sh             # full primer
#     scripts/ai-prime.sh --quick     # skip the constraint checks
#     scripts/ai-prime.sh --strict    # only emit if everything green
# =============================================================================

set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
cd "$ROOT"

if [ -t 1 ]; then
    BOLD="\033[1m"; G="\033[0;32m"; Y="\033[0;33m"; R="\033[0;31m"
    CYAN="\033[0;36m"; DIM="\033[2m"; NC="\033[0m"
else
    BOLD=""; G=""; Y=""; R=""; CYAN=""; DIM=""; NC=""
fi

QUICK=0
STRICT=0
for arg in "$@"; do
    case "$arg" in
        --quick)  QUICK=1 ;;
        --strict) STRICT=1 ;;
        --help|-h)
            sed -n '2,20p' "$0" | sed 's/^# \?//'
            exit 0 ;;
    esac
done

# -----------------------------------------------------------------------------
# 1) Header — name + date + git-style state
# -----------------------------------------------------------------------------
printf "${BOLD}═══ POLARIS — session primer ═══${NC}\n"
printf "  ${DIM}%s · %s${NC}\n" "$(date '+%Y-%m-%d %H:%M')" "$(uname -s)"
printf "\n"

# -----------------------------------------------------------------------------
# 2) Mission state — concise version of ai-status.sh
# -----------------------------------------------------------------------------
if [ "$QUICK" -ne 1 ]; then
    printf "${BOLD}── Mission state ──${NC}\n"

    # Hard constraints — count green/yellow/red without rendering each line
    constraint_output=$("$HERE/ai-status.sh" 2>/dev/null \
        | sed -n '/Hard constraints/,/Mission done-list/p' \
        | grep -E '^\s+[✓!⬜]' )
    n_ok=$(printf '%s\n' "$constraint_output" | grep -c '✓' || true)
    n_warn=$(printf '%s\n' "$constraint_output" | grep -cE '!|⬜' || true)
    n_warn=${n_warn:-0}
    if [ "$n_ok" -eq 10 ] && [ "$n_warn" -eq 0 ]; then
        printf "  C1-C10:   ${G}all 10 green${NC}\n"
    else
        printf "  C1-C10:   ${G}%s green${NC} · ${Y}%s warn${NC}\n" \
            "$n_ok" "$n_warn"
    fi

    # Done-list rollup
    v1_done=$(grep -cE '^[0-9]+\. ✅' "$ROOT/MISSION.md" 2>/dev/null | head -1)
    v1_def=$(grep -cE  '^[0-9]+\. ⏸'  "$ROOT/MISSION.md" 2>/dev/null | head -1)
    v2_done=$(grep -cE 'M2-[0-9]+\. ✅' "$ROOT/MISSION.md" 2>/dev/null | head -1)
    v2_open=$(grep -cE 'M2-[0-9]+\. ⬜' "$ROOT/MISSION.md" 2>/dev/null | head -1)
    printf "  v1:       ${G}%s ✅${NC} · ⏸ %s deferred\n" "${v1_done:-0}" "${v1_def:-0}"
    printf "  v2:       ${G}%s ✅${NC} · ${DIM}%s ⬜${NC}\n" "${v2_done:-0}" "${v2_open:-0}"
    printf "\n"

    if [ "$STRICT" -eq 1 ] && { [ "$n_ok" -lt 10 ] || [ "$n_warn" -gt 0 ]; }; then
        printf "${R}--strict: constraint check is not all-green. Bail.${NC}\n"
        exit 1
    fi
fi

# -----------------------------------------------------------------------------
# 3) Top proposed moves — top 3 from ai-propose.sh, condensed
# -----------------------------------------------------------------------------
printf "${BOLD}── Top moves ──${NC}\n"
"$HERE/ai-propose.sh" 3 2>/dev/null \
    | sed -n '/Top.*proposed moves/,/Next steps/p' \
    | grep -E '^[0-9]+\. R[0-9]+-|^   risk:' \
    | head -12 \
    | sed 's/^/  /'
printf "\n"

# -----------------------------------------------------------------------------
# 4) Recent journal — last 5 entries, decisions and learnings only
# -----------------------------------------------------------------------------
printf "${BOLD}── Recent journal ──${NC}\n"
latest_journal=$(ls -1t "$ROOT/journal/"*.md 2>/dev/null | head -1)
if [ -n "$latest_journal" ]; then
    printf "  ${DIM}%s${NC}\n" "$(basename "$latest_journal")"
    grep -E '^- \*\*(decision|learning)\*\*' "$latest_journal" 2>/dev/null \
        | tail -5 \
        | sed 's/^/  /' \
        | head -10
else
    printf "  ${DIM}(no journal entries — call scripts/ai-journal.sh start to open one)${NC}\n"
fi
printf "\n"

# -----------------------------------------------------------------------------
# 5) Recently modified source files — heuristic for "what's in flight"
# -----------------------------------------------------------------------------
printf "${BOLD}── Recently modified (last 24h) ──${NC}\n"
recent_files=$(find "$ROOT" -type f \
    \( -name '*.py' -o -name '*.sql' -o -name '*.html' -o -name '*.js' \
       -o -name '*.css' -o -name '*.md' -o -name '*.sh' \) \
    -not -path '*/node_modules/*' \
    -not -path '*/__pycache__/*' \
    -not -path '*/.git/*' \
    -mtime -1 2>/dev/null \
    | grep -v '/journal/' \
    | sed "s|$ROOT/||" \
    | head -8)
if [ -n "$recent_files" ]; then
    printf '%s\n' "$recent_files" | sed 's/^/  /'
else
    printf "  ${DIM}(nothing in the last 24h — fresh slate)${NC}\n"
fi
printf "\n"

# -----------------------------------------------------------------------------
# 6) Suggested next move — one line
# -----------------------------------------------------------------------------
top_move=$("$HERE/ai-propose.sh" 1 2>/dev/null \
    | grep -E '^1\. R[0-9]+-' \
    | head -1 \
    | sed 's/^1\. /  /')
if [ -n "$top_move" ]; then
    printf "${BOLD}── Suggested next ──${NC}\n"
    printf "%s\n" "$top_move"
    printf "  ${DIM}(scripts/ai-propose.sh 5 for more, --strict for LOW-risk only)${NC}\n"
fi

# -----------------------------------------------------------------------------
# 7) Onboarding pointers.
# -----------------------------------------------------------------------------
printf "\n${BOLD}── Onboarding ──${NC}\n"
printf "  ${DIM}New session? Read \`CLAUDE.md\` (the agent runbook), then \`MISSION.md\`.${NC}\n"
printf "  ${DIM}Invariants: C1-C10 in MISSION.md, checked by \`python3 -m polaris_checks.run\`.${NC}\n"

# -----------------------------------------------------------------------------
# 8) Since-last-session delta.
# Surfaces what changed since the most-recent prior ai-prime.sh
# invocation: ships landed, sanctums opened/closed, journal decisions.
# Reads timestamp from /tmp/polaris-ai-prime.last; writes a new one
# at exit. First-run prints a friendly initialization message.
# -----------------------------------------------------------------------------
printf "\n${BOLD}── Since last session ──${NC}\n"
LAST_RUN_FILE="/tmp/polaris-ai-prime.last"
if [ -f "$LAST_RUN_FILE" ] && [ -s "$LAST_RUN_FILE" ]; then
    last_iso=$(cat "$LAST_RUN_FILE" 2>/dev/null | head -1)
    if [ -n "$last_iso" ]; then
        # Compute delta in days for the human-readable summary
        if command -v python3 >/dev/null 2>&1; then
            delta_summary=$(python3 - "$last_iso" "$ROOT" 2>/dev/null <<'PY'
import sys, os, datetime, pathlib, re
last_iso = sys.argv[1]
root = pathlib.Path(sys.argv[2])
try:
    last = datetime.datetime.fromisoformat(last_iso)
except ValueError:
    sys.exit(0)
now = datetime.datetime.now(last.tzinfo) if last.tzinfo else datetime.datetime.now()
delta = now - last
hours = delta.total_seconds() / 3600
if hours < 0.1:
    print(f"  Last session: just now ({delta.total_seconds():.0f}s ago)")
elif hours < 1:
    print(f"  Last session: {hours*60:.0f}min ago")
elif hours < 48:
    print(f"  Last session: {hours:.1f}h ago")
else:
    print(f"  Last session: {hours/24:.1f}d ago")

# Ships since last (CHANGELOG entries with dates after last_iso)
changelog = root / "CHANGELOG.md"
if changelog.is_file():
    text = changelog.read_text(errors="replace")
    headers = re.findall(r'^## (v[0-9.]+) — (\d{4}-\d{2}-\d{2})', text, re.MULTILINE)
    last_date = last.date()
    new_ships = [v for v, d in headers
                 if datetime.date.fromisoformat(d) >= last_date]
    if new_ships:
        print(f"  Ships since: {', '.join(new_ships[:5])}")

# Sanctums opened OR modified since last
sanctum_dir = root / "sanctum"
if sanctum_dir.is_dir():
    new_sanctums = [p for p in sanctum_dir.glob("2026-*.md")
                    if datetime.datetime.fromtimestamp(p.stat().st_mtime).timestamp()
                    > last.timestamp()]
    if new_sanctums:
        names = [p.stem for p in sorted(new_sanctums, key=lambda p: p.stat().st_mtime, reverse=True)[:3]]
        print(f"  Sanctums touched: {', '.join(names)}")

# Journal entries since
today = datetime.date.today().isoformat()
journal_today = root / "journal" / f"{today}.md"
if journal_today.is_file():
    mtime_ts = journal_today.stat().st_mtime
    if mtime_ts > last.timestamp():
        # Count "**decision**" lines added since last
        text = journal_today.read_text(errors="replace")
        decisions = text.count("**decision**")
        print(f"  Today's journal: {decisions} decision(s) recorded")
PY
)
            if [ -n "$delta_summary" ]; then
                printf "%s\n" "$delta_summary"
            else
                printf "  ${DIM}(could not compute delta)${NC}\n"
            fi
        else
            printf "  ${DIM}(python3 not found; install for delta surface)${NC}\n"
        fi
    fi
else
    printf "  ${DIM}First run, no prior session recorded.${NC}\n"
    printf "  ${DIM}Future runs will surface ships + sanctums + journal decisions since last.${NC}\n"
fi

# Update the timestamp for next-run.
date -u +"%Y-%m-%dT%H:%M:%S+00:00" > "$LAST_RUN_FILE" 2>/dev/null || true

exit 0
