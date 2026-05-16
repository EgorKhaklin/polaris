#!/bin/bash
# =============================================================================
# scripts/ai-propose.sh
#
# Given the current state of Polaris, propose the top N most valuable next
# moves. Each proposal includes:
#   - mission alignment (which done-list item this advances)
#   - risk class (LOW / MEDIUM / HIGH)
#   - rough effort estimate
#   - what to do first
#
# This script does NOT execute. Execution is decided by:
#   - LOW    → agent may execute autonomously
#   - MEDIUM → agent writes proposal, waits for user approval, then executes
#   - HIGH   → agent writes proposal with constraint analysis, waits for
#              explicit approval
#
# Post-v2 reward function (v8.31, resolved by Sanctum
# `sanctum/2026-05-12-post-v2-steady-state-declaration.md`):
#   Polaris is in steady-state. v2 closed 12/12. There are no open
#   mission items. The list this script returns is therefore HOUSEKEEPING
#   candidates (R8-4 PostGIS perf, drift-resolution items, doc gaps),
#   not mission promotions. The agent does NOT propose new mission scope
#   autonomously; v3 opens only when an external trigger fires
#   (Arc B prod-deploy / Arc C partner consumer / novel arc with cause).
#
#   The scoring weights are unchanged from v8.7; they correctly rank
#   maintenance items below mission items. With no mission items open,
#   the top of the list IS the housekeeping queue.
#
# Brain analog: prefrontal cortex priority selection. Given many possible
# actions and a goal, which one moves toward the goal furthest per unit of
# effort and risk?
#
# Usage:
#     ai-propose.sh           # top 3 from active roadmap
#     ai-propose.sh 5         # top 5
#     ai-propose.sh --backlog # also scan backlog (for promotion candidates)
#     ai-propose.sh --strict  # only return LOW-risk items (for unattended runs)
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

TOP_N=3
INCLUDE_BACKLOG=0
STRICT_MODE=0

for arg in "$@"; do
    case "$arg" in
        --backlog) INCLUDE_BACKLOG=1 ;;
        --strict)  STRICT_MODE=1 ;;
        --help|-h)
            sed -n '2,30p' "$0" | sed 's/^# \?//'
            exit 0 ;;
        [0-9]*) TOP_N="$arg" ;;
    esac
done

if [ ! -f "$ROOT/ROADMAP.md" ] || [ ! -f "$ROOT/MISSION.md" ]; then
    printf "${R}MISSION.md or ROADMAP.md missing.${NC}\n"
    printf "Run from project root, or initialize the planning layer first.\n"
    exit 1
fi

printf "${BOLD}═══ Polaris — proposing next moves ═══${NC}\n\n"
printf "${DIM}Reading: MISSION.md, ROADMAP.md"
[ "$INCLUDE_BACKLOG" -eq 1 ] && printf ", BACKLOG.md"
[ "$STRICT_MODE" -eq 1 ] && printf " (strict: LOW-risk only)"
printf "${NC}\n\n"

# -----------------------------------------------------------------------------
# Parse ROADMAP.md to extract candidate items
# -----------------------------------------------------------------------------
# We look for blocks like:
#   ### Rx-N. Title
#   - **Mission link:** ...
#   - **Risk class:** LOW
#   - **Effort:** ...
#   - **Acceptance:**
#     - ...
#
# Output one parsed entry per candidate.

parse_roadmap() {
    python3 - "$ROOT/ROADMAP.md" <<'PY'
import re, sys

with open(sys.argv[1], encoding='utf-8') as f:
    src = f.read()

# Split on top-level (## ) sections — anchored to newline so ### doesn't match.
sections = re.split(r'\n## (?=\S)', '\n' + src)
items = []
for sec in sections:
    head = sec.split('\n', 1)[0].strip()
    if not head.startswith('v') or head.startswith('Process'):
        continue
    if head.startswith('v9'):
        continue   # speculative; don't propose
    # Match R7..R11. Two-digit ids (R10-, R11-) need explicit alternation.
    blocks = re.split(r'\n### (?:✅ )?(R(?:7|8|9|10|11)-\d+)\.\s*', sec)
    for i in range(1, len(blocks) - 1, 2):
        item_id = blocks[i]
        body = blocks[i + 1]
        # Skip items already marked done in ROADMAP (### ✅ R7-1.)
        if re.search(rf'^### ✅ {re.escape(item_id)}\.', sec, re.MULTILINE):
            continue
        # Skip out-of-scope items: ✗ RETIRED (post-v8.26) or ⏸ DEFERRED (pre-v8.26)
        if re.search(r'\*\*Status:\*\*\s*(✗ RETIRED|⏸ DEFERRED)', body):
            continue
        # Skip items superseded by a v2 item
        if re.search(r'\*\*Status:\*\*\s*Superseded by', body):
            continue
        # Title is the first line; rest is metadata
        title_line = body.split('\n')[0].strip()
        # Extract metadata fields
        def extract(label):
            m = re.search(rf'\*\*{re.escape(label)}:\*\*\s*([^\n]+)', body)
            return m.group(1).strip() if m else 'unknown'
        mission = extract('Mission link')
        risk    = extract('Risk class').split()[0] if extract('Risk class') != 'unknown' else 'UNKNOWN'
        effort  = extract('Effort')
        items.append({
            'id': item_id,
            'title': title_line,
            'mission': mission,
            'risk': risk,
            'effort': effort,
        })
print('---ITEMS---')
for it in items:
    print(f"{it['id']}|{it['risk']}|{it['title']}|{it['mission']}|{it['effort']}")
PY
}

ROADMAP_ITEMS=$(parse_roadmap | grep -A 1000 -- '---ITEMS---' | tail -n +2)

if [ -z "$ROADMAP_ITEMS" ]; then
    if [ "$INCLUDE_BACKLOG" -eq 0 ]; then
        printf "${Y}Roadmap empty. Run with --backlog to scan docs/BACKLOG.md "
        printf "for promotion candidates.${NC}\n"
        exit 0
    fi
fi

# -----------------------------------------------------------------------------
# Score and rank items
# -----------------------------------------------------------------------------
# Scoring heuristic:
#   risk=LOW    → +3 (autonomous-eligible)
#   risk=MEDIUM → +1
#   risk=HIGH   → -2 (penalize; humans should drive these)
#   v7 prefix   → +2 (active version)
#   v8 prefix   → +1
#   v9 prefix   → 0  (already filtered out)
#
# Items with a 🟡 (in-progress) mission link rank above ⬜ pending.

score_item() {
    local id="$1" risk="$2" mission="$3"
    local score=0

    # Risk weight — Fibonacci sequence (1, 2, 3, 5, 8, 13). The Fibonacci
    # progression encodes that work scales combinatorially with size, not
    # linearly: a HIGH-risk item isn't ~2× a LOW-risk item, it's ~5×. The
    # ratio approaches the golden ratio φ ≈ 1.618. Linear weighting
    # systematically under-penalizes large items. See
    # meta/structural-constants.json::FIBONACCI_PRIORITY_WEIGHTS.
    case "$risk" in
        LOW)    score=$((score + 8)) ;;     # autonomous-eligible — high payoff per unit risk
        MEDIUM) score=$((score + 3)) ;;     # propose-and-wait
        HIGH)   score=$((score - 5)) ;;     # explicit approval (negative — humans drive)
    esac

    # Strict mode skips non-LOW
    if [ "$STRICT_MODE" -eq 1 ] && [ "$risk" != "LOW" ]; then
        echo "-99 $id"
        return
    fi

    # Version weight — also Fibonacci, capturing that the active v2 mission
    # arc (v10/v11) deserves ~φ× the priority of completed-or-planned items.
    case "$id" in
        R10-*) score=$((score + 5)) ;;      # v2 substrate arc — active
        R11-*) score=$((score + 5)) ;;      # v2 open-problems arc — active
        R7-*)  score=$((score + 2)) ;;      # v1 trailing items
        R8-*)  score=$((score + 2)) ;;      # v1 trailing items
        R9-*)  score=$((score + 1)) ;;      # speculative
    esac

    # In-progress bonus (🟡 in mission link) — small but tipping
    if echo "$mission" | grep -q "🟡\|in progress"; then
        score=$((score + 2))
    fi

    echo "$score $id"
}

# Build scored list
SCORED=$(echo "$ROADMAP_ITEMS" | while IFS='|' read -r id risk title mission effort; do
    [ -z "$id" ] && continue
    sc=$(score_item "$id" "$risk" "$mission")
    [ "${sc%% *}" = "-99" ] && continue
    echo "$sc"
done | sort -rn -k1)

if [ -z "$SCORED" ]; then
    printf "${Y}No candidates after scoring "
    [ "$STRICT_MODE" -eq 1 ] && printf "(strict mode filtered all non-LOW items)"
    printf "${NC}\n"
    exit 0
fi

# -----------------------------------------------------------------------------
# Print top-N proposals
# -----------------------------------------------------------------------------
printf "${BOLD}── Top %s proposed moves ──${NC}\n\n" "$TOP_N"

i=0
echo "$SCORED" | head -"$TOP_N" | while read -r line; do
    i=$((i + 1))
    score="${line%% *}"
    id="${line##* }"
    # Find the item's full record
    record=$(echo "$ROADMAP_ITEMS" | grep "^$id|" | head -1)
    [ -z "$record" ] && continue
    IFS='|' read -r _ risk title mission effort <<< "$record"

    case "$risk" in
        LOW)    risk_color="${G}LOW${NC}    autonomous-eligible" ;;
        MEDIUM) risk_color="${Y}MEDIUM${NC} propose-and-wait" ;;
        HIGH)   risk_color="${R}HIGH${NC}   explicit approval required" ;;
        *)      risk_color="${DIM}$risk${NC}" ;;
    esac

    printf "${BOLD}%s. %s — %s${NC}\n" "$i" "$id" "$title"
    printf "   risk:    %b  (score=%s)\n" "$risk_color" "$score"
    printf "   mission: %s\n" "$mission"
    printf "   effort:  %s\n" "$effort"
    printf "\n"

    # For each item, suggest concrete first action
    case "$id" in
        R10-1)
            printf "   ${DIM}first action:${NC} stand up Groth16 toolchain (py_ecc or arkworks-py); choose circuit DSL\n"
            printf "   ${DIM}files touched:${NC} polaris_web/zk/, app.py (UC-2), test_app.py, DEVNOTES/zk-circuit.md\n" ;;
        R10-2)
            printf "   ${DIM}first action:${NC} design append-only Merkle log schema; expose /api/anchor/<id>\n"
            printf "   ${DIM}files touched:${NC} 01_schema.sql (BlockchainAnchor revision), app.py, test_app.py\n" ;;
        R10-3)
            printf "   ${DIM}first action:${NC} enumerate cryptographic and storage primitives; per-primitive fail-mode\n"
            printf "   ${DIM}files touched:${NC} DEVNOTES/substrate.md (new)\n" ;;
        R10-4)
            printf "   ${DIM}first action:${NC} draft GenomicAnchor table with hash-only constraint\n"
            printf "   ${DIM}files touched:${NC} 01_schema.sql, 04_data.sql, test_app.py\n" ;;
        R10-5)
            printf "   ${DIM}first action:${NC} write QuantumObserverBinding scaffold; mark fields DEFERRED\n"
            printf "   ${DIM}files touched:${NC} 01_schema.sql, DEVNOTES/quantum-observer.md (new)\n" ;;
        R11-1)
            printf "   ${DIM}first action:${NC} TokenSignature table; refactor verification to accept any active sig\n"
            printf "   ${DIM}files touched:${NC} 01_schema.sql, 05_procedures.sql (UC-6), app.py, test_app.py\n" ;;
        R11-2)
            printf "   ${DIM}first action:${NC} RecoveryRequest schema + UC-8 stored procedure\n"
            printf "   ${DIM}files touched:${NC} 01_schema.sql, 05_procedures.sql, app.py, test_app.py\n" ;;
        R11-3)
            printf "   ${DIM}first action:${NC} AgencyTrustAttestation schema + verification-flow consultation\n"
            printf "   ${DIM}files touched:${NC} 01_schema.sql, app.py, test_app.py, DEVNOTES/federation.md (new)\n" ;;
        R11-4)
            printf "   ${DIM}first action:${NC} EnrollmentStatus model + civic 'is-known' query path\n"
            printf "   ${DIM}files touched:${NC} 01_schema.sql, app.py, test_app.py, DEVNOTES/coverage.md (new)\n" ;;
        R11-5)
            printf "   ${DIM}first action:${NC} duress-code commitment column; verify-with-duress code path\n"
            printf "   ${DIM}files touched:${NC} 01_schema.sql, app.py, test_app.py, docs/operator/SECURITY.md\n" ;;
        R11-6)
            printf "   ${DIM}first action:${NC} mass-revocation rate-limit trigger; choose N%% / window-W defaults\n"
            printf "   ${DIM}files touched:${NC} 06_triggers.sql, test_app.py, meta/issuer-discretion.md (new)\n" ;;
        R11-7)
            printf "   ${DIM}first action:${NC} write adversary model; instantiate it in property tests\n"
            printf "   ${DIM}files touched:${NC} meta/redaction-proof.md (new), test_invariants_property.py\n" ;;
        R7-*|R8-*|R9-*)
            printf "   ${DIM}note:${NC} v7/v8/v9 trailing — v2 mission items (R10-*/R11-*) take precedence\n" ;;
    esac

    # Lattice-aware: if the title/mission mentions C1-C10, surface the
    # polarity complement so the proposer doesn't loosen one constraint
    # without considering the other side of the dialectic.
    constraints_mentioned=$(echo "$title $mission" | grep -oE '\bC[0-9]+\b' | sort -u)
    if [ -n "$constraints_mentioned" ]; then
        for cid in $constraints_mentioned; do
            complement=""
            case "$cid" in
                C7) complement="C2" ;;
                C2) complement="C7" ;;
                C5) complement="C4" ;;
                C4) complement="C5" ;;
                C8) complement="C6" ;;
                C6) complement="C8" ;;
            esac
            if [ -n "$complement" ]; then
                printf "   ${DIM}lattice:${NC}   touches %s — its polarity complement is %s; verify %s still holds after the change\n" "$cid" "$complement" "$complement"
            fi
        done
    fi
    echo
done

# -----------------------------------------------------------------------------
# Backlog promotion candidates (optional)
# -----------------------------------------------------------------------------
if [ "$INCLUDE_BACKLOG" -eq 1 ] && [ -f "$ROOT/docs/BACKLOG.md" ]; then
    printf "${BOLD}── Backlog scan (promotion candidates) ──${NC}\n\n"
    printf "${DIM}These are unsorted. Promotion to ROADMAP requires: mission link, "
    printf "risk class, effort, acceptance criteria.${NC}\n\n"

    # Surface 5 random backlog items as potential promotions
    grep -E "^- \*\*[A-Z]" "$ROOT/docs/BACKLOG.md" 2>/dev/null | head -8 | sed 's/^/  /'
    echo
fi

# -----------------------------------------------------------------------------
# Footer
# -----------------------------------------------------------------------------
printf "${BOLD}── Next steps ──${NC}\n"
printf "  1. Pick one of the proposals above\n"
printf "  2. If LOW-risk: implement → test → ai-journal.sh learning → ai-reflect.sh\n"
printf "  3. If MEDIUM/HIGH: write proposal explicitly → wait for user approval → execute\n"
printf "  4. After execution: update CHANGELOG.md and tick MISSION.md done-list\n"
printf "\n"
printf "${DIM}For automated unattended execution of LOW-risk items, consider:\n"
printf "    ai-propose.sh --strict 1   # only safe items, top one\n"
printf "    ai-propose.sh 5            # broader picture${NC}\n"

exit 0
