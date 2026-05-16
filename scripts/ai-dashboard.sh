#!/bin/bash
# =============================================================================
# scripts/ai-dashboard.sh — single-screen Polaris dashboard
#
# v9.07 / Wave 3 / J1 — surfaced by polaris-self-roadmap-2026-05-14
# item J1. Pre-v9.07 an operator opening a session toggled between
# ai-status / ai-propose / ai-architect / ai-hydra / ai-treasury-report /
# tail journal — 6+ separate invocations. v9.07 composes them into one
# screen.
#
# Usage:
#     ai-dashboard.sh                  # full dashboard, one render
#     ai-dashboard.sh --quick          # skip the slow checks (no DB)
#     ai-dashboard.sh --json           # machine-readable composite
#     ai-dashboard.sh --watch [N]      # re-render every N seconds (default 30)
#
# Sections (top to bottom):
#   1. Mission state — C1-C10 + version + done-list rollup
#   2. Top moves — top-3 from ai-propose
#   3. Latest brief delta — newest journal/hydra/ + age + status
#   4. Treasury health — quick read of the v9.05-fixed treasury state
#   5. Open Sanctums — any with Status: OPEN
#   6. Recent ships — last 3 from CHANGELOG
#   7. Substrate health — pheromone count last 6h + soldier freshness
#
# Each section is a compact 4-8 line block. Total fits one terminal
# screen at 80x40. Scrolls if smaller.
# =============================================================================

set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"

QUICK=0
EMIT_JSON=0
WATCH_MODE=0
WATCH_SECS=30

while [[ $# -gt 0 ]]; do
    case "$1" in
        --quick)  QUICK=1; shift ;;
        --json)   EMIT_JSON=1; shift ;;
        --watch)
            WATCH_MODE=1
            shift
            if [[ $# -gt 0 ]] && [[ "$1" =~ ^[0-9]+$ ]]; then
                WATCH_SECS="$1"
                shift
            fi
            ;;
        --help|-h)
            sed -n '2,28p' "$0" | sed 's/^# \?//'
            exit 0
            ;;
        *)
            echo "unknown arg: $1" >&2
            exit 2
            ;;
    esac
done

if [ -t 1 ]; then
    BOLD="\033[1m"; G="\033[0;32m"; Y="\033[0;33m"; R="\033[0;31m"
    CYAN="\033[0;36m"; DIM="\033[2m"; NC="\033[0m"
else
    BOLD=""; G=""; Y=""; R=""; CYAN=""; DIM=""; NC=""
fi

# ----------------------------------------------------------------------------
# Section helpers
# ----------------------------------------------------------------------------

render_header() {
    local now version
    now=$(date "+%Y-%m-%d %H:%M:%S")
    if [ -f "$ROOT/polaris_web/__version__.py" ]; then
        version=$(grep -oE '__version__\s*[:=].*"[^"]+"' \
                  "$ROOT/polaris_web/__version__.py" \
                  | head -1 | grep -oE '"[^"]+"' | tr -d '"')
    else
        version="?"
    fi
    printf "${BOLD}═══ POLARIS DASHBOARD — v%s — %s ═══${NC}\n\n" \
        "$version" "$now"
}

render_mission_state() {
    printf "${CYAN}── 1. Mission state${NC}\n"
    if [ -x "$HERE/ai-status.sh" ]; then
        local statout
        statout=$("$HERE/ai-status.sh" 2>&1 \
                  | sed -E 's/\x1b\[[0-9;]*m//g' || true)
        # Constraints + done-list rollups (compact)
        local c_ok
        c_ok=$(echo "$statout" | grep -c '^  ✓ C')
        local v1_summary v2_summary
        v1_summary=$(echo "$statout" | grep "v1 (closed)" | head -1)
        v2_summary=$(echo "$statout" | grep "v2 (closed)" | head -1)
        printf "  Constraints: ${G}%s/10${NC} in force\n" "$c_ok"
        [ -n "$v1_summary" ] && printf "  %s\n" "$(echo "$v1_summary" | sed 's/^  //')"
        [ -n "$v2_summary" ] && printf "  %s\n" "$(echo "$v2_summary" | sed 's/^  //')"
        local mission_state
        mission_state=$(echo "$statout" | grep "MISSION ALIGNED" | head -1)
        if [ -n "$mission_state" ]; then
            printf "  ${G}%s${NC}\n" "$(echo "$mission_state" | sed 's/^  //')"
        fi
    else
        printf "  ${Y}(ai-status.sh not found)${NC}\n"
    fi
    printf "\n"
}

render_top_moves() {
    printf "${CYAN}── 2. Top moves${NC}\n"
    if [ -x "$HERE/ai-propose.sh" ]; then
        local moves
        moves=$("$HERE/ai-propose.sh" 3 2>&1 \
                | sed -E 's/\x1b\[[0-9;]*m//g' \
                | grep -E '^[0-9]+\. ' \
                | head -3)
        if [ -n "$moves" ]; then
            printf "%s\n" "$moves" | sed 's/^/  /'
        else
            printf "  ${DIM}(roadmap empty; ai-propose --backlog for candidates)${NC}\n"
        fi
    fi
    printf "\n"
}

render_brief_delta() {
    printf "${CYAN}── 3. Latest HYDRA brief${NC}\n"
    local hydra_dir="$ROOT/journal/hydra"
    if [ ! -d "$hydra_dir" ]; then
        printf "  ${DIM}(no journal/hydra/ yet; run 'ai-hydra.sh --full --save')${NC}\n\n"
        return
    fi
    local latest n_briefs
    n_briefs=$(ls -1 "$hydra_dir"/*.md 2>/dev/null | wc -l | tr -d ' ')
    if [ "$n_briefs" -eq 0 ]; then
        printf "  ${DIM}(no briefs; run 'ai-hydra.sh --full --save')${NC}\n\n"
        return
    fi
    latest=$(ls -1t "$hydra_dir"/*.md 2>/dev/null | head -1)

    # Age in days (matches H1 thresholds)
    local now_ts latest_ts age_days status_color status_label
    now_ts=$(date +%s)
    if stat -f%m "$latest" >/dev/null 2>&1; then
        latest_ts=$(stat -f%m "$latest")
    else
        latest_ts=$(stat -c%Y "$latest")
    fi
    age_days=$(awk -v n="$now_ts" -v l="$latest_ts" 'BEGIN{printf "%.1f", (n-l)/86400}')
    if awk -v a="$age_days" 'BEGIN{exit !(a >= 30)}'; then
        status_color="$R"; status_label="DEAD"
    elif awk -v a="$age_days" 'BEGIN{exit !(a >= 14)}'; then
        status_color="$Y"; status_label="STALE"
    else
        status_color="$G"; status_label="FRESH"
    fi
    printf "  Latest: %s\n" "$(basename "$latest")"
    printf "  Age: %sd  Status: ${status_color}%s${NC}  Total briefs: %s\n" \
        "$age_days" "$status_label" "$n_briefs"
    printf "\n"
}

render_treasury() {
    printf "${CYAN}── 4. Treasury health${NC}\n"
    local roll="$ROOT/polaris_swarm/civitas/treasury-roll.json"
    if [ ! -f "$roll" ]; then
        printf "  ${DIM}(no treasury-roll.json; v9.05 / A1 may need re-run)${NC}\n\n"
        return
    fi
    if command -v python3 >/dev/null 2>&1; then
        python3 - "$roll" <<'PY'
import json, sys, datetime
roll = json.loads(open(sys.argv[1]).read())
events = roll.get("events", [])

# Separate balances + check soldier accruals against v9.05 cutover.
balances = {}
soldier_events_pre_v905 = 0
soldier_events_post_v905 = 0
# v9.05 fix shipped 2026-05-15 ~00:30 UTC.
V905_CUTOVER = datetime.datetime.fromisoformat("2026-05-15T04:00:00+00:00")
for ev in events:
    if not isinstance(ev, dict): continue
    a = ev.get("ant", "?")
    balances[a] = balances.get(a, 0) + int(ev.get("amount", 0))
    if a.startswith("soldier_"):
        ts_raw = ev.get("timestamp", "")
        try:
            ts = datetime.datetime.fromisoformat(ts_raw.replace("Z", "+00:00"))
            if ts < V905_CUTOVER:
                soldier_events_pre_v905 += 1
            else:
                soldier_events_post_v905 += 1
        except Exception:
            soldier_events_pre_v905 += 1
total = sum(balances.values())
n = len(balances)
mn = min(balances.values()) if balances else 0
mx = max(balances.values()) if balances else 0
audit_v9_05 = roll.get("_audit", [])
v905_present = any(isinstance(e, dict) and e.get("ship") == "v9.05" for e in audit_v9_05)
print(f"  Ants with balance: {n}; total: {total} denarii")
print(f"  Range: {mn} … {mx}")
# Pre-v9.05 soldier events are historical (G15 preserves them); only
# post-v9.05 events would indicate A1 violation.
if soldier_events_post_v905 == 0:
    if soldier_events_pre_v905 > 0:
        print(f"  ✓ F5 soldier-exemption holds: {soldier_events_pre_v905} historical (pre-v9.05) entries; 0 new since fix (G15 preserves history)")
    else:
        print(f"  ✓ F5 soldier-exemption holds: 0 soldier entries ever")
else:
    print(f"  ! {soldier_events_post_v905} POST-v9.05 soldier entries (A1 violation?)")
if v905_present:
    print(f"  ✓ v9.05 _audit marker present")
PY
    fi
    printf "\n"
}

render_open_sanctums() {
    printf "${CYAN}── 5. Open Sanctums${NC}\n"
    local sanctum_dir="$ROOT/sanctum"
    if [ ! -d "$sanctum_dir" ]; then
        printf "  ${DIM}(no sanctum/ directory)${NC}\n\n"
        return
    fi
    local open_files n_open=0
    for f in "$sanctum_dir"/2026-*.md; do
        [ ! -f "$f" ] && continue
        local status
        status=$(grep -E '^\*\*Status:' "$f" | head -1)
        if echo "$status" | grep -qE 'OPEN' && ! echo "$status" | grep -qE 'CLOSED|DECIDED'; then
            local base age_days f_ts
            base=$(basename "$f" .md)
            if stat -f%m "$f" >/dev/null 2>&1; then
                f_ts=$(stat -f%m "$f")
            else
                f_ts=$(stat -c%Y "$f")
            fi
            age_days=$(awk -v n="$(date +%s)" -v l="$f_ts" \
                       'BEGIN{printf "%.0f", (n-l)/86400}')
            printf "  ${Y}!${NC} %s (open %sd)\n" "$base" "$age_days"
            n_open=$((n_open+1))
        fi
    done
    if [ "$n_open" -eq 0 ]; then
        printf "  ${G}✓${NC} no open Sanctums\n"
    fi
    printf "\n"
}

render_recent_ships() {
    printf "${CYAN}── 6. Recent ships${NC}\n"
    if [ -f "$ROOT/CHANGELOG.md" ]; then
        grep -E "^## v[0-9]" "$ROOT/CHANGELOG.md" \
            | head -3 \
            | sed 's/^## /  /' \
            | sed 's/(\(.*\))/(\1)/' \
            | head -3
    fi
    printf "\n"
}

render_self_monitoring() {
    # v9.09 / D — surface ai-meta + ai-coherence + ai-link-check
    # status inline. These are the load-bearing self-monitoring
    # checks; pre-v9.09 the dashboard had no signal on them.
    if [ "$QUICK" = 1 ]; then
        return
    fi
    printf "${CYAN}── 8. Self-monitoring (cognitive layer health)${NC}\n"

    # ai-meta one-line status
    local meta_status
    meta_status=$("$HERE/ai-meta.sh" 2>&1 \
                  | sed -E 's/\x1b\[[0-9;]*m//g' \
                  | grep -E 'LAYER SELF-MONITORING IS HEALTHY|MINOR META-DRIFT|META-DRIFT' \
                  | head -1)
    if echo "$meta_status" | grep -q "HEALTHY"; then
        printf "  ${G}✓${NC} ai-meta: HEALTHY\n"
    elif echo "$meta_status" | grep -q "MINOR META-DRIFT"; then
        printf "  ${Y}!${NC} ai-meta: MINOR DRIFT (run \`bash scripts/ai-meta.sh\` for detail)\n"
    else
        printf "  ${R}✗${NC} ai-meta: %s\n" "${meta_status:-unknown}"
    fi

    # ai-coherence one-line
    local coh_status
    coh_status=$("$HERE/ai-coherence.sh" 2>&1 \
                 | sed -E 's/\x1b\[[0-9;]*m//g' \
                 | grep -E 'STRUCTURE INTACT|MINOR DRIFT|STRUCTURAL DRIFT' \
                 | head -1)
    if echo "$coh_status" | grep -q "STRUCTURE INTACT"; then
        printf "  ${G}✓${NC} ai-coherence: STRUCTURE INTACT\n"
    elif echo "$coh_status" | grep -q "MINOR DRIFT"; then
        printf "  ${Y}!${NC} ai-coherence: MINOR DRIFT\n"
    else
        printf "  ${R}✗${NC} ai-coherence: %s\n" "${coh_status:-unknown}"
    fi

    # ai-link-check one-line
    local link_status
    link_status=$("$HERE/ai-link-check.sh" 2>&1 \
                  | sed -E 's/\x1b\[[0-9;]*m//g' \
                  | tail -1)
    if echo "$link_status" | grep -qE '^OK\s'; then
        local link_count
        link_count=$(echo "$link_status" | grep -oE '[0-9]+ references' | head -1)
        printf "  ${G}✓${NC} ai-link-check: %s\n" "${link_count:-OK}"
    else
        printf "  ${R}✗${NC} ai-link-check: %s\n" "$link_status"
    fi

    printf "\n"
}

render_substrate() {
    if [ "$QUICK" = 1 ]; then
        return
    fi
    printf "${CYAN}── 7. Swarm substrate (last 6h)${NC}\n"
    local psql_bin=""
    for cand in \
        "/opt/homebrew/opt/postgresql@16/bin/psql" \
        "/usr/local/opt/postgresql@16/bin/psql" \
        "$(command -v psql 2>/dev/null)" \
    ; do
        if [ -x "$cand" ]; then psql_bin="$cand"; break; fi
    done
    if [ -z "$psql_bin" ]; then
        printf "  ${DIM}(no psql binary; substrate read skipped)${NC}\n\n"
        return
    fi
    local db="${POLARIS_DB_NAME:-polaris_test}"
    local user="${POLARIS_DB_USER:-polaris_app}"
    local pw="${POLARIS_DB_PASSWORD:-polaris_dev_password}"
    local host="${POLARIS_DB_HOST:-localhost}"
    local q="
        SELECT
          (SELECT count(*) FROM Pheromone WHERE deposited_at > now() - INTERVAL '6 hours' AND deposited_by NOT LIKE 'soldier_%') AS commanders,
          (SELECT count(*) FROM Pheromone WHERE deposited_at > now() - INTERVAL '6 hours' AND deposited_by LIKE 'soldier_%') AS soldiers,
          (SELECT count(DISTINCT deposited_by) FROM Pheromone WHERE deposited_at > now() - INTERVAL '24 hours' AND deposited_by LIKE 'soldier_%') AS soldier_classes_active_24h
    "
    local out
    out=$(PGPASSWORD="$pw" "$psql_bin" -h "$host" -U "$user" -d "$db" -tA -F'|' -c "$q" 2>&1)
    if echo "$out" | grep -q "ERROR\|FATAL"; then
        printf "  ${DIM}(DB unreachable; %s)${NC}\n\n" \
            "$(echo "$out" | head -1 | sed 's/^.*ERROR://')"
        return
    fi
    local commanders soldiers soldier_classes
    commanders=$(echo "$out" | head -1 | cut -d'|' -f1)
    soldiers=$(echo "$out" | head -1 | cut -d'|' -f2)
    soldier_classes=$(echo "$out" | head -1 | cut -d'|' -f3)
    printf "  Commanders: ${BOLD}%s${NC}  Soldiers: ${BOLD}%s${NC}  Soldier classes active (24h): ${BOLD}%s/8${NC}\n" \
        "$commanders" "$soldiers" "$soldier_classes"
    printf "\n"
}

# ----------------------------------------------------------------------------
# JSON mode
# ----------------------------------------------------------------------------

emit_json() {
    if ! command -v python3 >/dev/null 2>&1; then
        echo '{"error": "no python3"}'
        return
    fi
    python3 - <<PY
import json, os, subprocess
data = {
    "schema": "polaris-dashboard/1",
    "version": "$( [ -f "$ROOT/polaris_web/__version__.py" ] && grep -oE '__version__\s*[:=].*"[^"]+"' "$ROOT/polaris_web/__version__.py" | head -1 | grep -oE '"[^"]+"' | tr -d '"' )",
}
print(json.dumps(data, indent=2))
PY
}

# ----------------------------------------------------------------------------
# Main render
# ----------------------------------------------------------------------------

render_all() {
    if [ "$EMIT_JSON" = 1 ]; then
        emit_json
        return
    fi
    render_header
    render_mission_state
    render_top_moves
    render_brief_delta
    render_treasury
    render_open_sanctums
    render_recent_ships
    render_substrate
    render_self_monitoring   # v9.09 / D
}

if [ "$WATCH_MODE" = 1 ]; then
    while true; do
        clear
        render_all
        printf "${DIM}── refreshing every %ds (Ctrl-C to exit) ──${NC}\n" \
            "$WATCH_SECS"
        sleep "$WATCH_SECS"
    done
else
    render_all
fi
