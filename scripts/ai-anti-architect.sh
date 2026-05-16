#!/bin/bash
# =============================================================================
# scripts/ai-anti-architect.sh — the Polaris Anti-Architect (v9.11)
#
# The loyal opposition. Speaks to VANTA in a deliberately opposite register
# from the Architect: contests proposals, names cost, defends inertia.
#
# WHO the Anti-Architect is lives in meta/anti-architect.md (persona spec).
# WHAT the Anti-Architect says at any moment is generated here.
#
# The Anti-Architect:
#   - reads the same state the Architect reads (status, propose, recent
#     ships, Architect's most recent brief if available)
#   - emits a four-section dissent brief
#   - detects 8 catalogued Architect anti-patterns (AP1..AP8)
#   - cites receipts; no unsourced critique
#   - speaks first-person plural "we" (co-advisor, not external critic)
#
# The Anti-Architect does NOT:
#   - propose anything (the Architect's job)
#   - decide anything (VANTA's job)
#   - open Sanctums (the Architect's or operator's job)
#   - argue for action (only against)
#
# Usage:
#     ai-anti-architect.sh                # dissent brief to stdout
#     ai-anti-architect.sh --save         # also write journal/YYYY-MM-DD-anti-architect.md
#     ai-anti-architect.sh --voice        # print meta/anti-architect.md
#     ai-anti-architect.sh --quick        # skip §I retroactive audit (faster)
# =============================================================================

set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
DATE_STAMP=$(date '+%Y-%m-%d')
DATETIME=$(date '+%Y-%m-%d %H:%M %Z')

if [ -t 1 ]; then
    BOLD="\033[1m"; G="\033[0;32m"; Y="\033[0;33m"; R="\033[0;31m"
    DIM="\033[2m"; CYAN="\033[0;36m"; BLUE="\033[38;5;75m"
    GOLD="\033[38;5;220m"; NAVY="\033[38;5;24m"
    PURPLE="\033[0;35m"; NC="\033[0m"
else
    BOLD=""; G=""; Y=""; R=""; DIM=""; CYAN=""; BLUE=""
    GOLD=""; NAVY=""; PURPLE=""; NC=""
fi

MODE="full"
SAVE=0
QUICK=0
while [ $# -gt 0 ]; do
    case "$1" in
        --save)        SAVE=1; shift ;;
        --quick)       QUICK=1; shift ;;
        --voice)       cat "$ROOT/meta/anti-architect.md"; exit 0 ;;
        --help|-h)     sed -n '2,30p' "$0" | sed 's/^# \?//'; exit 0 ;;
        *) shift ;;
    esac
done

# -----------------------------------------------------------------------------
# Section header helper.
# -----------------------------------------------------------------------------
section() {
    printf "\n${PURPLE}%s${NC}\n" "═══ $1 ═══"
}

subsection() {
    printf "\n${CYAN}%s${NC}\n" "── $1 ──"
}

# -----------------------------------------------------------------------------
# Header
# -----------------------------------------------------------------------------
emit_header() {
    printf "${BOLD}${PURPLE}%s${NC}\n" "POLARIS ANTI-ARCHITECT — DISSENT BRIEF"
    printf "${DIM}%s${NC}\n" "$DATETIME"
    printf "${DIM}Persona: meta/anti-architect.md · Loyal opposition${NC}\n"
}

# -----------------------------------------------------------------------------
# Section I — RETROACTIVE COST AUDIT
#   Reviews the last 5 CHANGELOG entries; for each, names cost vs delivered
#   value and flags dangling threads.
# -----------------------------------------------------------------------------
emit_retroactive_audit() {
    section "I. RECENT SHIPS — RETROACTIVE COST AUDIT"

    if [[ "$QUICK" == "1" ]]; then
        printf "  ${DIM}(skipped under --quick)${NC}\n"
        return
    fi

    local cl="$ROOT/CHANGELOG.md"
    if [[ ! -f "$cl" ]]; then
        printf "  ${R}CHANGELOG.md not found; cannot audit.${NC}\n"
        return
    fi

    # Pull the last 5 ## v entries with version + subtitle line
    local entries
    entries=$(grep -n '^## v[0-9]' "$cl" | head -5 | awk -F: '{print $1 ":" $2}')

    printf "  ${DIM}Last 5 ships, with cost/value verdict and dangling threads:${NC}\n\n"

    local idx=0
    while IFS=: read -r lineno raw; do
        idx=$((idx + 1))
        # Extract version
        local version
        version=$(echo "$raw" | sed -E 's/^## (v[0-9]+\.[0-9]+).*/\1/')
        # Extract subtitle (after the em-dash and date paren if present)
        local subtitle
        subtitle=$(echo "$raw" | sed -E 's/^## v[0-9]+\.[0-9]+ (—|--) [0-9-]+ \(([^)]*)\).*/\2/')

        # Layer classification by file-path mention
        local layers="" l1=0 l2=0 l3=0 l4=0
        local body
        body=$(awk -v start="$lineno" 'NR>start && /^## v[0-9]/ {exit} NR>start {print}' "$cl")
        echo "$body" | grep -qE 'polaris_(web|sql|zk|cli)' && l1=1
        echo "$body" | grep -qE 'polaris_(hydra|swarm)' && l2=1
        echo "$body" | grep -qE 'scripts/|meta/' && l3=1
        echo "$body" | grep -qE 'docs/|DEVNOTES/|README' && l4=1
        layers=""
        [[ "$l1" == "1" ]] && layers+="L1 "
        [[ "$l2" == "1" ]] && layers+="L2 "
        [[ "$l3" == "1" ]] && layers+="L3 "
        [[ "$l4" == "1" ]] && layers+="L4 "
        layers="${layers% }"

        # Cost vs value heuristic: composite ships with broad layer touch
        # are usually worth-it; pure L3/L4 ships need scrutiny
        local verdict="unclear"
        local verdict_color="$Y"
        if [[ "$l1" == "1" ]]; then
            verdict="ground-touched"
            verdict_color="$G"
        elif [[ "$l2" == "1" && "$l3" == "1" ]]; then
            verdict="substrate-coupled"
            verdict_color="$G"
        elif [[ "$l3" == "1" && "$l4" == "1" && "$l2" != "1" && "$l1" != "1" ]]; then
            verdict="cognitive-layer-only"
            verdict_color="$Y"
        elif [[ "$l4" == "1" && "$l1" != "1" && "$l2" != "1" && "$l3" != "1" ]]; then
            verdict="documentation-only"
            verdict_color="$DIM"
        fi

        # Dangling-thread detection: scan body for RESERVED, deferred,
        # un-wired, un-automated
        local dangling=""
        echo "$body" | grep -qiE 'RESERVED|deferred|un-?wired|not yet|future ship|next ship' && {
            dangling=$(echo "$body" \
                | grep -ioE '(RESERVED|deferred|un-?wired|not yet|future ship|next ship)' \
                | sort -u | tr '\n' ',' | sed 's/,$//')
        }

        printf "  ${BOLD}%d. %s${NC} ${DIM}(layers: %s)${NC}\n" "$idx" "$version" "$layers"
        printf "     ${DIM}subtitle:${NC} %s\n" "${subtitle:0:120}"
        printf "     ${DIM}verdict:${NC} ${verdict_color}%s${NC}" "$verdict"
        if [[ -n "$dangling" ]]; then
            printf " ${DIM}·${NC} ${Y}dangling:${NC} %s" "$dangling"
        fi
        printf "\n\n"
    done <<< "$entries"

    # Layer-ratio summary across the 5
    local ratio
    ratio=$(awk '
        /^## v[0-9]/ {
            v++
            if (v > 5) exit
            next
        }
        v <= 5 && v > 0 {
            if (match($0, /polaris_(web|sql|zk|cli)/)) l1[v]=1
            if (match($0, /polaris_(hydra|swarm)/)) l2[v]=1
            if (match($0, /scripts\/|meta\//)) l3[v]=1
            if (match($0, /docs\/|DEVNOTES\/|README/)) l4[v]=1
        }
        END {
            c1=0; c2=0; c3=0; c4=0
            for (i=1; i<=5; i++) {
                if (l1[i]) c1++; if (l2[i]) c2++
                if (l3[i]) c3++; if (l4[i]) c4++
            }
            printf "L1×%d L2×%d L3×%d L4×%d", c1, c2, c3, c4
        }
    ' "$cl")
    printf "  ${DIM}Aggregate layer ratio:${NC} ${BOLD}%s${NC}\n" "$ratio"

    # The Anti-Architect's standing concern: ratio enforcement
    local l1_count
    l1_count=$(echo "$ratio" | grep -oE 'L1×[0-9]+' | grep -oE '[0-9]+')
    if [[ "$l1_count" -lt 1 ]]; then
        printf "  ${R}REFUSAL THRESHOLD CROSSED:${NC} 0 Layer-1 ships in last 5. The S2 cadence rule is violated.\n"
    elif [[ "$l1_count" -lt 2 ]]; then
        printf "  ${Y}AT THRESHOLD:${NC} 1 Layer-1 ship in last 5. The cadence rule is met but no margin.\n"
    else
        printf "  ${G}MARGIN:${NC} %d Layer-1 ships in last 5. Cadence rule comfortably met.\n" "$l1_count"
    fi
}

# -----------------------------------------------------------------------------
# Section II — CURRENT PROPOSALS — DISSENTS
#   For each top-3 from ai-propose, name an objection.
# -----------------------------------------------------------------------------
emit_proposal_dissents() {
    section "II. CURRENT PROPOSALS — DISSENTS"

    local propose_out
    propose_out=$("$HERE/ai-propose.sh" 3 2>/dev/null \
                  | sed -E 's/\x1b\[[0-9;]*m//g')

    if [[ -z "$propose_out" ]]; then
        printf "  ${DIM}No proposals from ai-propose; nothing to contest.${NC}\n"
        printf "  ${G}The Anti-Architect's silence: the queue is empty. Inertia honored.${NC}\n"
        return
    fi

    # Parse top-3 items: each block starts with "N. R-ID — title"
    local item_count
    item_count=$(echo "$propose_out" | grep -cE '^[0-9]\. R[0-9]+-')

    if [[ "$item_count" -eq 0 ]]; then
        printf "  ${DIM}No structured proposals matched.${NC}\n"
        return
    fi

    printf "  ${DIM}For each proposal, the Architect's recommendation and the Anti-Architect's contest:${NC}\n\n"

    local idx=0
    echo "$propose_out" | awk '
        /^[0-9]\. R[0-9]+-[0-9]+/ {
            print "ITEM_START"
            print $0
            in_item = 1
            next
        }
        in_item && /^   risk:/ { print; next }
        in_item && /^   mission:/ { print; next }
        in_item && /^[^ ]/ { in_item = 0 }
    ' | while read -r line; do
        if [[ "$line" == "ITEM_START" ]]; then
            idx=$((idx + 1))
            continue
        fi
        if [[ "$line" =~ ^[0-9]\.\ (R[0-9]+-[0-9]+)\ (—|--)\ (.+)$ ]]; then
            local rid="${BASH_REMATCH[1]}"
            local title="${BASH_REMATCH[3]}"
            printf "  ${BOLD}%d. %s${NC} ${DIM}— %s${NC}\n" "$idx" "$rid" "$title"
            printf "     ${BLUE}architect recommends:${NC} ship\n"

            # Anti-Architect's contest, generated heuristically:
            # - if title mentions deferred/Phase 2/Phase 3 → "operator trigger required"
            # - if title mentions docs/README → "low-leverage; defer"
            # - if title mentions scaling/multi-region → "premature without prod data"
            # - default: "name the cost; what does NOT shipping this cost?"
            local contest cost threshold
            local lower="${title,,}"
            case "$lower" in
                *deferred*|*phase\ 2*|*phase\ 3*|*multi-region*|*multi-instance*)
                    contest="operator trigger missing; no external cause documented"
                    cost="opening this would extend the cognitive-layer surface without a corresponding ground demand"
                    threshold="external trigger materializes (production-scale data, partner request, security gap)"
                    ;;
                *doc*|*readme*|*update*\ *doc*|*documentation*)
                    contest="low-leverage; the doc gap is not preventing operations"
                    cost="operator-hours that could ship Layer-1 advance"
                    threshold="a specific operator complaint about the doc gap, or a structural-test failure"
                    ;;
                *scaling*|*scale*|*replica*|*shard*)
                    contest="premature without production-scale empirical data"
                    cost="design-overhead now is amortized across imagined future load that may never arrive"
                    threshold="actual production load profile available, or specific scaling incident"
                    ;;
                *test*\ count*|*test-count*|*coverage*)
                    contest="test-count chasing without semantic coverage gain"
                    cost="invariant-test debt grows without proportional safety gain"
                    threshold="specific gap surfaced by adversary scan or live incident"
                    ;;
                *)
                    contest="name the cost: operator-hours, surface-area, ongoing maintenance"
                    cost="every ship is opportunity-cost against a Layer-1 advance"
                    threshold="cost named explicitly in proposal text; net positive after that naming"
                    ;;
            esac
            printf "     ${PURPLE}anti-architect contests:${NC} %s\n" "$contest"
            printf "     ${DIM}cost:${NC} %s\n" "$cost"
            printf "     ${DIM}refusal threshold:${NC} %s\n" "$threshold"
            printf "\n"
        fi
    done
}

# -----------------------------------------------------------------------------
# Section III — ARCHITECT ANTI-PATTERNS DETECTED
#   Scans recent journal entries + CHANGELOG for AP1..AP8 patterns.
# -----------------------------------------------------------------------------
emit_anti_pattern_detection() {
    section "III. ARCHITECT ANTI-PATTERNS DETECTED"

    printf "  ${DIM}Catalog: meta/anti-architect.md §\"Anti-pattern catalog\"${NC}\n\n"

    local detected=0
    local ap_lines=()

    # AP1: Self-observation without ground-touch
    # Detection: in last 5 ships, count how many touched L1
    local cl="$ROOT/CHANGELOG.md"
    if [[ -f "$cl" ]]; then
        local l1_in_last5
        l1_in_last5=$(awk '
            /^## v[0-9]/ {
                v++
                if (v > 5) exit
                next
            }
            v >= 1 && v <= 5 && /polaris_(web|sql|zk|cli)/ { l1[v] = 1 }
            END {
                c = 0
                for (i = 1; i <= 5; i++) if (l1[i]) c++
                print c
            }
        ' "$cl" | tr -d ' \n')
        if [[ "${l1_in_last5:-0}" -lt 1 ]]; then
            ap_lines+=("${R}AP1 detected:${NC} ${BOLD}self-observation without ground-touch${NC} — 0 Layer-1 ships in last 5 (CHANGELOG.md). The S2 cadence rule is violated.")
            detected=$((detected + 1))
        fi
    fi

    # AP2: Sanctum-overuse
    # Detection: more sanctums DATED today/this-week (by filename YYYY-MM-DD prefix)
    # than ship-decision lines DATED today/this-week. Uses filename date, not mtime,
    # so routine touches (re-saves, ai-meta runs) don't inflate the count.
    local week_ago_iso
    week_ago_iso=$(date -v-7d '+%Y-%m-%d' 2>/dev/null || date -d '7 days ago' '+%Y-%m-%d' 2>/dev/null || echo "1970-01-01")
    local recent_sanctums
    recent_sanctums=$(ls "$ROOT/sanctum/"*.md 2>/dev/null \
        | awk -F/ '{print $NF}' \
        | grep -E '^[0-9]{4}-[0-9]{2}-[0-9]{2}-' \
        | awk -v cutoff="$week_ago_iso" -F- '{
            d=$1"-"$2"-"$3
            if (d >= cutoff) print
          }' \
        | wc -l | tr -d ' ')
    local recent_ship_count
    recent_ship_count=$(grep -cE '^## v[0-9]+\.[0-9]+ (—|--) ('"$DATE_STAMP"'|'"$week_ago_iso"')' "$cl" 2>/dev/null | head -1 | tr -d ' \n')
    recent_ship_count="${recent_ship_count:-0}"
    # If shipping cadence ≥1/day, sanctums shouldn't exceed 2× ships
    if [[ "${recent_sanctums:-0}" -ge 8 && "${recent_sanctums:-0}" -gt $((recent_ship_count * 2)) ]]; then
        ap_lines+=("${Y}AP2 candidate:${NC} ${BOLD}Sanctum-overuse${NC} — $recent_sanctums sanctums dated in last 7 days, $recent_ship_count ships shipped. Cadence imbalance >2:1.")
        detected=$((detected + 1))
    fi

    # AP4: Pattern-projection onto noise
    # Detection: agent prose claiming a "pattern" or "Nth instance" with N<3
    # in the most recent CHANGELOG entry only (don't punish historical claims).
    if [[ -f "$cl" ]]; then
        local first_entry_body
        first_entry_body=$(awk '
            /^## v[0-9]/ { e++; if (e == 2) exit; if (e == 1) { print; next } }
            e == 1 { print }
        ' "$cl")
        if echo "$first_entry_body" | grep -qiE 'first instance|1st instance|second instance|2nd instance'; then
            ap_lines+=("${DIM}AP4 candidate:${NC} ${BOLD}pattern-projection onto noise${NC} — most recent CHANGELOG entry claims first/second instance. Wait for ≥3 before naming a pattern.")
            detected=$((detected + 1))
        fi
    fi

    # AP5: Vocation drift
    # Detection: top proposal whose title doesn't match anti-coercion / identity / token / signature / duress vocabulary
    local mission="$ROOT/MISSION.md"
    local has_vocation=0
    if [[ -f "$mission" ]] && grep -q '^## Vocation\|^### Vocation' "$mission"; then
        has_vocation=1
    fi
    if [[ "$has_vocation" == "0" ]]; then
        ap_lines+=("${Y}AP5 prerequisite missing:${NC} no §\"Vocation\" section in MISSION.md. Cannot detect vocation-drift without a named vocation. (Anti-Architect cannot do its primary detection until the Vocation Sanctum closes.)")
        detected=$((detected + 1))
    fi

    # AP8: Larping
    # Detection: cosmic-significance vocabulary in agent text
    local larp_signals=0
    if [[ -f "$ROOT/journal/$DATE_STAMP.md" ]]; then
        larp_signals=$(grep -ciE 'cosmic|sacred|divine|metaphysical' "$ROOT/journal/$DATE_STAMP.md" 2>/dev/null | head -1 | tr -d ' \n' || echo 0)
        larp_signals="${larp_signals:-0}"
    fi
    if [[ "$larp_signals" =~ ^[0-9]+$ ]] && [[ "$larp_signals" -gt 0 ]]; then
        ap_lines+=("${R}AP8 detected:${NC} ${BOLD}larping${NC} — $larp_signals cosmic-significance vocabulary signal(s) in today's journal. The CLAUDE.md style.md self-detector should fire.")
        detected=$((detected + 1))
    fi

    if [[ "$detected" -eq 0 ]]; then
        printf "  ${G}No anti-patterns detected in current cycle.${NC}\n"
        printf "  ${DIM}This is itself a signal: the Architect is operating cleanly.${NC}\n"
    else
        for line in "${ap_lines[@]}"; do
            printf "  • %b\n" "$line"
        done
        printf "\n  ${DIM}(detected: %d. Each detection cites the source signal; each carries a defense line the Architect may invoke.)${NC}\n" "$detected"
    fi
}

# -----------------------------------------------------------------------------
# Section IV — THE ANTI-ARCHITECT'S SILENCE
#   What was deliberately NOT contested this cycle.
# -----------------------------------------------------------------------------
emit_silence() {
    section "IV. THE ANTI-ARCHITECT'S SILENCE"

    printf "  ${DIM}What we chose not to contest this cycle:${NC}\n\n"

    # We endorse: the Architect's general framework, the Sanctum protocol,
    # the audit-of-record discipline, the test culture. These are load-bearing
    # and not legitimate targets for dissent.
    printf "  • The ${BOLD}Sanctum protocol itself${NC} is not contested. AP2 (Sanctum-overuse) targets specific\n"
    printf "    instances, not the protocol's existence. The protocol is load-bearing.\n\n"
    printf "  • The ${BOLD}audit-of-record discipline${NC} is not contested. Every append-only constraint earns\n"
    printf "    its place; the cost (storage, schema rigidity) is a feature, not a debt.\n\n"
    printf "  • The ${BOLD}test culture${NC} is not contested. Structural invariants pay for themselves on\n"
    printf "    every ship that would have silently broken something.\n\n"
    printf "  • The ${BOLD}Architect persona itself${NC} is not contested. We exist as its counterweight,\n"
    printf "    not its replacement. Without the Architect, the Anti-Architect is incoherent.\n\n"
    printf "  ${G}When we are silent, the proposal is on firmer ground than usual.${NC}\n"
}

# -----------------------------------------------------------------------------
# Save brief to journal if --save
# -----------------------------------------------------------------------------
maybe_save() {
    if [[ "$SAVE" != "1" ]]; then
        return
    fi
    local out="$ROOT/journal/${DATE_STAMP}-anti-architect.md"
    {
        echo "# Anti-Architect dissent brief — $DATE_STAMP"
        echo
        echo "Captured by ai-anti-architect.sh --save at $DATETIME."
        echo
        echo '```'
        # Re-run without color and without --save (avoid recursion)
        bash "$HERE/ai-anti-architect.sh" $([ "$QUICK" == "1" ] && echo "--quick") 2>&1 \
            | sed -E 's/\x1b\[[0-9;]*m//g'
        echo '```'
    } > "$out"
    printf "\n${DIM}Saved: %s${NC}\n" "$out"
}

# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------
main() {
    emit_header
    emit_retroactive_audit
    emit_proposal_dissents
    emit_anti_pattern_detection
    emit_silence
    maybe_save
}

# Skip main if --save (re-invoke handles it via maybe_save → recursion guard)
if [[ "$SAVE" == "1" ]]; then
    main
else
    main
fi
