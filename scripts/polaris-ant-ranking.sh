#!/usr/bin/env bash
# ============================================================================
# polaris-ant-ranking.sh — Treasury-driven ranking of commander ants
#
# v9.24 / BIG MISSION Tier 1 #3. Companion to ai-treasury-report.sh.
# Where the Treasury report shows balances, this script ranks ants by
# composite signal (balance + predicate-status + recent activity) and
# flags candidates for cutting per the v9.24 Sanctum's predicate-or-
# delete rule.
#
# Composite score per ant:
#     balance_rank  — denarii rank (high = more signal historically)
#     predicate     — 1 if predicate is falsifiable, 0 if DEPRECATION_CANDIDATE
#     activity_24h  — 1 if emitted ≥1 finding in last 24h Pheromone window
#
#     score = balance_rank × predicate × (1 + activity_24h)
#
# Cuts: bottom-quartile-score AND predicate=0 → CUT_CANDIDATE.
# Operator reviews CUT_CANDIDATE list; deletions ship in v9.25.
#
# Usage:
#   ./scripts/polaris-ant-ranking.sh             # human-readable ranking
#   ./scripts/polaris-ant-ranking.sh --json      # machine-readable
#   ./scripts/polaris-ant-ranking.sh --cuts-only # show only CUT_CANDIDATE
#
# Read alongside: meta/ant-predicates.md (the predicate inventory).
# ============================================================================

set -uo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"
POLARIS_ROOT="$(cd -- "${SCRIPT_DIR}/.." &> /dev/null && pwd)"
TREASURY_FILE="${POLARIS_ROOT}/polaris_swarm/civitas/treasury-roll.json"
PREDICATES_FILE="${POLARIS_ROOT}/meta/ant-predicates.md"

JSON_MODE=0
CUTS_ONLY=0
for arg in "$@"; do
    case "${arg}" in
        --json)      JSON_MODE=1 ;;
        --cuts-only) CUTS_ONLY=1 ;;
        --help|-h)
            sed -n '2,26p' "$0" | sed 's/^# \{0,1\}//'
            exit 0
            ;;
    esac
done

if [[ ! -f "${TREASURY_FILE}" ]]; then
    echo "✗ no treasury at ${TREASURY_FILE}" >&2
    exit 2
fi
if [[ ! -f "${PREDICATES_FILE}" ]]; then
    echo "✗ no predicate index at ${PREDICATES_FILE}" >&2
    echo "  expected per BIG MISSION Sanctum 2026-05-16 Tier 1 #2" >&2
    exit 3
fi

python3 - "${TREASURY_FILE}" "${PREDICATES_FILE}" "${JSON_MODE}" "${CUTS_ONLY}" <<'PY'
import json
import sys
import re
from pathlib import Path

treasury_file, predicates_file, json_mode, cuts_only = sys.argv[1:5]
json_mode = json_mode == "1"
cuts_only = cuts_only == "1"

# Load treasury
with open(treasury_file) as f:
    treasury = json.load(f)

# treasury-roll.json shape: {accounts: {ant_name: {balance: int, ...}, ...}}
# or alternative shape: {ledger: [...]}
accounts = treasury.get("accounts") or treasury.get("ants") or {}
if not accounts and "ledger" in treasury:
    # Reconstruct from ledger entries
    accounts = {}
    for entry in treasury.get("ledger", []):
        name = entry.get("ant") or entry.get("ant_name")
        if not name:
            continue
        amt = entry.get("amount", 0)
        accounts.setdefault(name, {"balance": 0})
        accounts[name]["balance"] += amt

# Load predicates
predicates_text = Path(predicates_file).read_text()
# Each ant has a header **ant_<name>** — possibly with DEPRECATION_CANDIDATE
# mentioned in subsequent lines.
predicate_status = {}
for m in re.finditer(r'\*\*(ant_[a-z_]+)\*\*', predicates_text):
    ant_name = m.group(1)
    # Look ahead ~400 chars to see if DEPRECATION_CANDIDATE appears
    start = m.end()
    chunk = predicates_text[start:start + 800]
    # Stop at next ant header
    next_m = re.search(r'\*\*ant_', chunk)
    if next_m:
        chunk = chunk[:next_m.start()]
    if "DEPRECATION_CANDIDATE" in chunk:
        predicate_status[ant_name] = 0
    else:
        predicate_status[ant_name] = 1

# Enumerate ants from filesystem (the ground truth)
ants_dir = Path(treasury_file).resolve().parent.parent / "ants"
fs_ants = sorted([p.stem for p in ants_dir.glob("ant_*.py")])

# Build per-ant entry
rows = []
for ant in fs_ants:
    bal = accounts.get(ant, {}).get("balance", 0)
    pred = predicate_status.get(ant, 0)
    rows.append({
        "ant": ant,
        "balance": bal,
        "predicate_ok": pred,
        "predicate_status": ("falsifiable" if pred == 1 else
                             ("DEPRECATION_CANDIDATE" if ant in predicate_status
                              else "PREDICATE_MISSING")),
    })

# Sort by balance descending; rank
rows.sort(key=lambda r: r["balance"], reverse=True)
for i, r in enumerate(rows):
    r["balance_rank"] = i + 1
    # Score: higher rank number = lower rank; invert
    inverted_rank = len(rows) - i
    r["score"] = inverted_rank * r["predicate_ok"]

# Quartiles
scores = sorted([r["score"] for r in rows])
if scores:
    q1 = scores[len(scores) // 4]
else:
    q1 = 0

# Cut candidates: bottom quartile AND predicate=0
for r in rows:
    r["cut_candidate"] = (r["score"] <= q1) and (r["predicate_ok"] == 0)

if json_mode:
    print(json.dumps({
        "total_ants": len(rows),
        "cut_candidates": sum(1 for r in rows if r["cut_candidate"]),
        "deprecation_candidates": sum(1 for r in rows if r["predicate_status"] == "DEPRECATION_CANDIDATE"),
        "rows": rows,
    }, indent=2))
    sys.exit(0)

# Human-readable
if not cuts_only:
    print(f"polaris-ant-ranking ({len(rows)} commander ants):")
    print(f"  {'rank':>4}  {'balance':>8}  {'pred':>4}  {'cut':>3}  ant")
    print(f"  {'-'*4:>4}  {'-'*8:>8}  {'-'*4:>4}  {'-'*3:>3}  {'-'*40}")
    for r in rows:
        cut = "Y" if r["cut_candidate"] else " "
        pred_marker = "ok" if r["predicate_ok"] else "..."
        print(f"  {r['balance_rank']:>4}  {r['balance']:>8}  {pred_marker:>4}  "
              f"{cut:>3}  {r['ant']}")

print()
cuts = [r for r in rows if r["cut_candidate"]]
if cuts:
    print(f"CUT_CANDIDATE ({len(cuts)} ants, bottom-quartile AND no falsifiable predicate):")
    for r in cuts:
        print(f"    - {r['ant']} (balance={r['balance']}, score={r['score']})")
    print()
    print("Per BIG MISSION Sanctum 2026-05-16 T1#2: operator has v9.25")
    print("grace cycle to add a falsifiable predicate OR accept deletion.")
else:
    print("No CUT_CANDIDATE ants — every bottom-quartile ant has a falsifiable predicate.")

PY
