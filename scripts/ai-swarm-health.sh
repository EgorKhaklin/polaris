#!/bin/bash
# =============================================================================
# scripts/ai-swarm-health.sh — Mycelium swarm health snapshot (v9.14)
#
# One-screen operator report of the swarm's current state. Distinct from
# ai-hydra.sh (HYDRA's lens view) and ai-dashboard.sh (whole-system).
# This is the SWARM's view of itself — what HYDRA's ant_colony_watcher
# would see, but rendered for direct operator consumption.
#
# Sections:
#   I.   Pheromone substrate freshness (deposits in last 6h)
#   II.  Per-legion deposit cadence (11 manifest + 1 reserved)
#   III. Per-soldier-class cadence (8 workers + 1 priest)
#   IV.  Citizen activity (6 citizens)
#   V.   Treasury balance + F5 flow summary
#   VI.  Shared correlation surfaces (v9.10): hit count per surface
#   VII. Anomalies (silent classes; outsized depositors)
#
# Requires DB connection (POLARIS_DB_* env vars). Gracefully degrades
# with a "DB unreachable" banner if no connection.
#
# Usage:
#     scripts/ai-swarm-health.sh           # full report
#     scripts/ai-swarm-health.sh --json    # JSON output (audit trail)
#     scripts/ai-swarm-health.sh --quick   # skip §V + §VI + §VII
# =============================================================================
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"

if [ -t 1 ]; then
    BOLD="\033[1m"; G="\033[0;32m"; Y="\033[0;33m"; R="\033[0;31m"
    DIM="\033[2m"; CYAN="\033[0;36m"; GOLD="\033[38;5;220m"
    PURPLE="\033[0;35m"; NC="\033[0m"
else
    BOLD=""; G=""; Y=""; R=""; DIM=""; CYAN=""; GOLD=""; PURPLE=""; NC=""
fi

MODE="full"
JSON=0
QUICK=0
for arg in "$@"; do
    case "$arg" in
        --json)   JSON=1 ;;
        --quick)  QUICK=1 ;;
        --help|-h)
            sed -n '2,25p' "$0" | sed 's/^# \?//'
            exit 0
            ;;
    esac
done

# DB query helper. Exits silently with no output on connection failure
# (caller decides how to render the absence).
PSQL_CMD="psql"
if ! command -v psql >/dev/null 2>&1; then
    # macOS Homebrew default
    for cand in /opt/homebrew/opt/postgresql@16/bin/psql \
                /usr/local/opt/postgresql@16/bin/psql; do
        if [ -x "$cand" ]; then
            PSQL_CMD="$cand"
            break
        fi
    done
fi

PGHOST="${POLARIS_DB_HOST:-localhost}"
PGDATABASE="${POLARIS_DB_NAME:-polaris_test}"
PGUSER="${POLARIS_DB_USER:-$(whoami)}"
export PGHOST PGDATABASE PGUSER
[ -n "${POLARIS_DB_PASSWORD:-}" ] && export PGPASSWORD="$POLARIS_DB_PASSWORD"

query() {
    "$PSQL_CMD" -At -c "$1" 2>/dev/null
}

check_db() {
    query "SELECT 1" >/dev/null 2>&1
}

if ! check_db; then
    printf "${R}DB unreachable${NC} (PGHOST=%s PGDATABASE=%s PGUSER=%s).\n" \
        "$PGHOST" "$PGDATABASE" "$PGUSER"
    printf "${DIM}This report requires a live DB connection. Start Postgres + load\n"
    printf "schema, then re-run. The swarm cannot report on itself without its\n"
    printf "substrate being readable.${NC}\n"
    exit 1
fi

# JSON path — short-circuits all the human-readable rendering
if [ "$JSON" = "1" ]; then
    # Emit a compact JSON snapshot suitable for audit + log archiving.
    # Built via a single multi-row CTE query to keep it atomic.
    "$PSQL_CMD" -At <<'SQL' 2>/dev/null
WITH
substrate AS (
  SELECT COUNT(*) AS deposits_6h,
         MAX(deposited_at)::TEXT AS last_deposit_at
    FROM Pheromone
   WHERE deposited_at >= NOW() - INTERVAL '6 hours'
),
per_class AS (
  SELECT deposited_by, COUNT(*) AS n
    FROM Pheromone
   WHERE deposited_at >= NOW() - INTERVAL '6 hours'
   GROUP BY deposited_by
),
surfaces AS (
  SELECT
    COALESCE((SELECT COUNT(*) FROM Pheromone
              WHERE node_id = 'runtime:health'
                AND deposited_at >= NOW() - INTERVAL '24 hours'), 0) AS runtime_health_24h,
    COALESCE((SELECT COUNT(*) FROM Pheromone
              WHERE node_id = 'runtime:swarm'
                AND deposited_at >= NOW() - INTERVAL '24 hours'), 0) AS runtime_swarm_24h,
    COALESCE((SELECT COUNT(*) FROM Pheromone
              WHERE node_id = 'runtime:auth'
                AND deposited_at >= NOW() - INTERVAL '24 hours'), 0) AS runtime_auth_24h
)
SELECT json_build_object(
  'substrate', (SELECT row_to_json(s) FROM substrate s),
  'per_depositor', (SELECT json_agg(row_to_json(pc)) FROM per_class pc),
  'shared_surfaces', (SELECT row_to_json(sf) FROM surfaces sf),
  'generated_at', NOW()::TEXT
);
SQL
    exit 0
fi

# ----- §I: Substrate freshness ----------------------------------
printf "${BOLD}${GOLD}═══ POLARIS SWARM HEALTH ═══${NC}\n"
printf "${DIM}%s${NC}\n\n" "$(date '+%Y-%m-%d %H:%M %Z') · DB: $PGDATABASE @ $PGHOST"

printf "${PURPLE}§I. Pheromone substrate (last 6h)${NC}\n"
TOTAL_6H=$(query "SELECT COUNT(*) FROM Pheromone WHERE deposited_at >= NOW() - INTERVAL '6 hours';" | tr -d ' ')
LAST_AT=$(query "SELECT TO_CHAR(MAX(deposited_at), 'YYYY-MM-DD HH24:MI:SS TZ') FROM Pheromone;" | tr -d ' ' | head -c 30)
LAST_AGO=$(query "SELECT EXTRACT(EPOCH FROM (NOW() - MAX(deposited_at)))::INTEGER FROM Pheromone;" | tr -d ' ')
printf "  Total deposits (6h):   ${BOLD}%s${NC}\n" "${TOTAL_6H:-0}"
if [ -n "${LAST_AT:-}" ] && [ "$LAST_AT" != "" ]; then
    printf "  Most recent deposit:   %s\n" "$LAST_AT"
    if [ -n "${LAST_AGO:-}" ] && [ "$LAST_AGO" != "" ]; then
        if [ "$LAST_AGO" -lt 600 ]; then
            printf "  Time since last:       ${G}%s seconds (fresh)${NC}\n" "$LAST_AGO"
        elif [ "$LAST_AGO" -lt 3600 ]; then
            printf "  Time since last:       ${Y}%s seconds (within hour)${NC}\n" "$LAST_AGO"
        else
            printf "  Time since last:       ${R}%s seconds (stale)${NC}\n" "$LAST_AGO"
        fi
    fi
else
    printf "  ${DIM}Substrate empty.${NC}\n"
fi
printf "\n"

# ----- §II: Per-legion cadence ----------------------------------
printf "${PURPLE}§II. Per-legion deposit cadence (last 6h)${NC}\n"
python3 - <<'PY' 2>/dev/null
import os, subprocess, sys
sys.path.insert(0, "/Users/vanta/Desktop/polaris")
try:
    from polaris_swarm.legions import REPUBLICAN_LEGIONS, IMPERIAL_LEGIONS, RESERVED_TWELFTH_LEGION_SLOT
except Exception:
    sys.exit(0)
psql_cmd = os.environ.get("PSQL_CMD") or "psql"
for cand in ["/opt/homebrew/opt/postgresql@16/bin/psql", "/usr/local/opt/postgresql@16/bin/psql"]:
    if os.path.isfile(cand) and os.access(cand, os.X_OK):
        psql_cmd = cand
        break

def deposit_count(ant_names):
    if not ant_names:
        return 0
    quoted = ",".join(f"'{n}'" for n in ant_names)
    sql = f"SELECT COUNT(*) FROM Pheromone WHERE deposited_by IN ({quoted}) AND deposited_at >= NOW() - INTERVAL '6 hours';"
    try:
        out = subprocess.run([psql_cmd, "-At", "-c", sql],
                              capture_output=True, text=True, timeout=10)
        return int(out.stdout.strip() or 0)
    except Exception:
        return -1

def render(tier_marker, color, legions):
    for cls in legions:
        ants = [a.NAME for a in getattr(cls, "ANTS", []) if hasattr(a, "NAME")]
        cnt = deposit_count(ants)
        bar = ""
        if cnt > 0:
            bar = "█" * min(cnt, 40)
        elif cnt == 0:
            bar = "·" * 3
        print(f"  {tier_marker} {cls.NAME:30s} ants={len(ants):2d}  deposits(6h)={cnt:4d}  {bar}")

print("  Republican legions (9):")
render("R", "", REPUBLICAN_LEGIONS)
print("  Imperial legions (2 manifest + 1 reserved):")
render("I", "", IMPERIAL_LEGIONS)
if not RESERVED_TWELFTH_LEGION_SLOT.get("manifested"):
    print(f"  I legion_reserved_twelfth        (RESERVED; manifest via Sanctum when justified)")
PY
echo

# ----- §III: Per-soldier-class cadence --------------------------
printf "${PURPLE}§III. Per-soldier-class cadence (8 workers + 1 priest, last 6h)${NC}\n"
# Avoid bash 4 associative arrays (macOS ships bash 3.2). Use temp file
# keyed by depositor name with the count as value.
SOLDIER_QUERY="SELECT deposited_by, COUNT(*) FROM Pheromone WHERE deposited_at >= NOW() - INTERVAL '6 hours' AND deposited_by LIKE 'soldier_%' GROUP BY deposited_by ORDER BY deposited_by;"
ALL_SOLDIERS="soldier_route_pinger soldier_file_mtime soldier_process_alive soldier_disk_usage soldier_log_tail soldier_db_table_size soldier_heartbeat_freshness soldier_sanctum_freshness soldier_swarm_witness"
SOLDIER_OBS=$(query "$SOLDIER_QUERY")
for s in $ALL_SOLDIERS; do
    cnt=$(echo "$SOLDIER_OBS" | awk -F'|' -v name="$s" '$1 == name {print $2}' | head -1)
    cnt=${cnt:-0}
    marker=" "
    if [ "$s" = "soldier_swarm_witness" ]; then
        marker="${GOLD}†${NC}"  # priest tier
    fi
    if [ "$cnt" = "0" ]; then
        printf "  ${R}✗${NC} %b %-35s ${DIM}silent${NC}\n" "$marker" "$s"
    else
        printf "  ${G}✓${NC} %b %-35s deposits=%s\n" "$marker" "$s" "$cnt"
    fi
done
printf "\n"

if [ "$QUICK" = "1" ]; then
    printf "${DIM}(skipped §IV-§VII under --quick)${NC}\n"
    exit 0
fi

# ----- §IV: Citizen activity ------------------------------------
printf "${PURPLE}§IV. Citizen activity (6 citizens, last 24h)${NC}\n"
# v9.37: was `AND tier = 'citizen'` but Pheromone has no `tier`
# column; the query silently errored to empty, printing "No citizen
# deposits" regardless of reality. Citizens deposit with their NAME
# as `deposited_by` and carry `civitas_class` in evidence JSONB (per
# `_deposit_citizen_results` docstring in polaris_swarm/colony.py).
# Use the JSONB ? operator to auto-discover any future citizens
# without hardcoding ALL_CITIZENS names here.
CITIZEN_QUERY="SELECT deposited_by, COUNT(*) FROM Pheromone WHERE deposited_at >= NOW() - INTERVAL '24 hours' AND evidence ? 'civitas_class' GROUP BY deposited_by ORDER BY deposited_by;"
CITIZEN_ROWS=$(query "$CITIZEN_QUERY")
if [ -z "$CITIZEN_ROWS" ]; then
    printf "  ${DIM}No citizen deposits in last 24h.${NC}\n"
else
    echo "$CITIZEN_ROWS" | while IFS='|' read -r name count; do
        printf "  ${CYAN}%-30s${NC} deposits=%s\n" "$name" "$count"
    done
fi
printf "\n"

# ----- §V: Treasury + F5 flow -----------------------------------
printf "${PURPLE}§V. Treasury (Denarius) balance${NC}\n"
TREASURY_TABLE_EXISTS=$(query "SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name = 'antbalance');")
if [ "$TREASURY_TABLE_EXISTS" = "t" ]; then
    NET_BALANCE=$(query "SELECT COALESCE(SUM(balance), 0) FROM AntBalance;" | tr -d ' ')
    MIN_BALANCE=$(query "SELECT MIN(balance) FROM AntBalance;" | tr -d ' ')
    MAX_BALANCE=$(query "SELECT MAX(balance) FROM AntBalance;" | tr -d ' ')
    NEGATIVE_COUNT=$(query "SELECT COUNT(*) FROM AntBalance WHERE balance < 0;" | tr -d ' ')
    printf "  Net balance:           %s denarii\n" "${NET_BALANCE:-?}"
    printf "  Min/max ant balance:   %s / %s\n" "${MIN_BALANCE:-?}" "${MAX_BALANCE:-?}"
    if [ -n "${NEGATIVE_COUNT:-}" ] && [ "$NEGATIVE_COUNT" -gt 0 ]; then
        printf "  Ants with negative balance: ${Y}%s${NC} (persistent-silence penalty signal)\n" "$NEGATIVE_COUNT"
    fi
else
    # Treasury lives in polaris_swarm/civitas/treasury-roll.json (Quaestor ledger),
    # not in a SQL table. Read from the JSON if present so the operator sees the
    # real balance picture rather than a missing-table message.
    TREASURY_JSON="$ROOT/polaris_swarm/civitas/treasury-roll.json"
    if [ -f "$TREASURY_JSON" ]; then
        python3 - "$TREASURY_JSON" <<'PY' || printf "  ${DIM}(treasury-roll.json present but unreadable)${NC}\n"
import json, sys
from collections import Counter
with open(sys.argv[1]) as f:
    roll = json.load(f)
events = roll.get("events", []) if isinstance(roll, dict) else []
balances = Counter()
for e in events:
    balances[e.get("ant", "?")] += e.get("amount", 0)
if not balances:
    print("  Treasury ledger empty.")
else:
    vals = list(balances.values())
    neg = sum(1 for v in vals if v < 0)
    print(f"  Source:                treasury-roll.json (Quaestor JSON ledger; no SQL table)")
    print(f"  Net balance:           {sum(vals)} denarii  across {len(vals)} ant(s) · {len(events)} events")
    print(f"  Min/max ant balance:   {min(vals)} / {max(vals)}")
    if neg:
        print(f"  Ants with negative balance: {neg} (persistent-silence penalty signal — F5)")
PY
    else
        printf "  ${DIM}AntBalance table not present, and no treasury-roll.json found.${NC}\n"
    fi
fi
printf "\n"

# ----- §VI: Shared correlation surfaces (v9.10) ------------------
printf "${PURPLE}§VI. Shared correlation surfaces (v9.10, last 24h)${NC}\n"
for surface in "runtime:health" "runtime:swarm" "runtime:auth"; do
    cnt=$(query "SELECT COUNT(*) FROM Pheromone WHERE node_id = '$surface' AND deposited_at >= NOW() - INTERVAL '24 hours';" | tr -d ' ')
    cnt=${cnt:-0}
    if [ "$surface" = "runtime:auth" ]; then
        # RESERVED until mission_watcher emits auth findings
        if [ "$cnt" = "0" ]; then
            printf "  ${DIM}runtime:auth   deposits=0   (RESERVED; awaiting mission_watcher activation)${NC}\n"
        else
            printf "  ${GOLD}runtime:auth   deposits=$cnt   (RESERVED but receiving — investigate)${NC}\n"
        fi
    else
        if [ "$cnt" = "0" ]; then
            printf "  ${Y}%-15s deposits=%s   (correlation cannot fire)${NC}\n" "$surface" "$cnt"
        else
            printf "  ${G}%-15s deposits=%s   (correlation candidates present)${NC}\n" "$surface" "$cnt"
        fi
    fi
done
printf "\n"

# ----- §VII: Anomalies -----------------------------------------
printf "${PURPLE}§VII. Anomalies${NC}\n"
SILENT_LEGIONS_COUNT=$(query "
WITH known_ants AS (
  SELECT unnest(ARRAY[
    'ant_aor_immutability','ant_adversary_walk_complete','ant_atlas_endpoint_health',
    'ant_brain_map_freshness','ant_build_freshness','ant_changelog_gap','ant_csp_health',
    'ant_dependency_in_use','ant_devnotes_ships_coverage','ant_docs_structure',
    'ant_done_list_arithmetic','ant_fk_cascade_guard','ant_journal_silence',
    'ant_legion_doctrine_health','ant_mission_drift','ant_pattern_warmth',
    'ant_principle_invariant','ant_api_doc_coverage'
  ]) AS name
)
SELECT COUNT(*) FROM known_ants k
WHERE NOT EXISTS (
  SELECT 1 FROM Pheromone p
  WHERE p.deposited_by = k.name
    AND p.deposited_at >= NOW() - INTERVAL '24 hours'
);" | tr -d ' ')
if [ -n "${SILENT_LEGIONS_COUNT:-}" ] && [ "$SILENT_LEGIONS_COUNT" -gt 0 ]; then
    printf "  ${Y}%s commander ants silent in last 24h${NC}\n" "$SILENT_LEGIONS_COUNT"
fi
# Single depositor outsized share
OUTSIZED=$(query "
WITH t AS (SELECT COUNT(*) AS total FROM Pheromone WHERE deposited_at >= NOW() - INTERVAL '6 hours')
SELECT deposited_by, COUNT(*), ROUND(100.0 * COUNT(*) / NULLIF((SELECT total FROM t), 0), 1)
  FROM Pheromone
 WHERE deposited_at >= NOW() - INTERVAL '6 hours'
 GROUP BY deposited_by
HAVING COUNT(*) > 0.5 * (SELECT total FROM t)
 ORDER BY COUNT(*) DESC;")
if [ -n "$OUTSIZED" ]; then
    echo "$OUTSIZED" | while IFS='|' read -r name count pct; do
        printf "  ${Y}%s holds %s%% of deposits (>50%% threshold)${NC}\n" "$name" "$pct"
    done
fi
if [ -z "${SILENT_LEGIONS_COUNT:-}" ] || [ "$SILENT_LEGIONS_COUNT" = "0" ] && [ -z "$OUTSIZED" ]; then
    printf "  ${G}No anomalies detected.${NC}\n"
fi
