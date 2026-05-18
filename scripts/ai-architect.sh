#!/bin/bash
# =============================================================================
# scripts/ai-architect.sh — the Polaris Architect (v8.13)
#
# The chief-of-staff persona for Polaris. Speaks to VANTA in a consistent
# register, synthesizes across the cognitive layer, produces structured
# intelligence briefs. This is the HEAD (synthesis) and EYE (monitoring)
# of Polaris, reporting up to its principal.
#
# WHO the Architect is lives in meta/architect.md (persona spec).
# WHAT the Architect says at any moment is generated here.
#
# The Architect:
#   - reads state from ai-status, ai-meta, ai-coherence, ai-propose, ai-adversary
#   - synthesizes through a six-section brief structure
#   - tracks suggestions across briefs (arch-YYYY-MM-DD-NNN IDs)
#   - self-monitors (notes its own blind spots in section VI)
#   - cites evidence with file paths or tool names (no unsourced claims)
#
# The Architect does NOT:
#   - act (recommends only; VANTA executes or authorizes LOW-risk loop)
#   - chat (produces structured briefs, not conversational text)
#   - hedge (declares uncertainty explicitly; no filler hedges)
#   - larp (game-theoretic framing only where it predicts behavior)
#
# Usage:
#     ai-architect.sh                 # full brief to stdout
#     ai-architect.sh --save          # also write to journal/YYYY-MM-DD-architect.md
#     ai-architect.sh --cron          # terser brief (for scheduled runs)
#     ai-architect.sh --reflect       # analyze prior briefs + last 10 closed/rejected Sanctums
#     ai-architect.sh --reflect-n N   # same, but read last N Sanctums (default 10)
#     ai-architect.sh --voice         # print meta/architect.md (the persona spec)
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
REFLECT_N=10
while [ $# -gt 0 ]; do
    case "$1" in
        --save)        SAVE=1; shift ;;
        --cron)        MODE="cron"; shift ;;
        --reflect)     MODE="reflect"; shift ;;
        --reflect-n)   REFLECT_N="$2"; MODE="reflect"; shift 2 ;;
        --voice)       cat "$ROOT/meta/architect.md"; exit 0 ;;
        --help|-h)     sed -n '2,30p' "$0" | sed 's/^# \?//'; exit 0 ;;
        *) shift ;;
    esac
done
export REFLECT_N

# -----------------------------------------------------------------------------
# Game-type lookup for ROADMAP items (Architect annotates recommendations
# with their game-theoretic structure — see meta/structural-architecture.md
# framework #6 and scripts/ai-adversary.sh for the model).
# -----------------------------------------------------------------------------
game_type_for() {
    case "$1" in
        # v1 closure arc (R7-*) — pure-coordination shapes
        R7-1)  echo "Mechanism design (STRIDE-to-control mapping)" ;;
        R7-2)  echo "Coordination game (geometric edge case as convention)" ;;
        R7-3)  echo "Bandwidth allocation (keyset cursor vs offset)" ;;
        R7-4)  echo "Schelling-point alignment (test-counts as truth)" ;;
        # v1 hardening arc (R8-*) — defender-improvement shapes
        R8-1)  echo "Defense-in-depth (constraint hardening at schema layer)" ;;
        R8-2)  echo "Coordination under failure (multi-process rate-limit consistency)" ;;
        R8-3)  echo "Trust delegation (out-of-scope — retired)" ;;
        R8-4)  echo "Scaling under load (B-tree vs GiST equilibrium)" ;;
        R8-5)  echo "Caching as commitment (TTL trades freshness for throughput)" ;;
        # v1 speculative arc (R9-*) — out-of-scope shapes
        R9-1)  echo "Architectural boundary (value-pure identity layer — retired)" ;;
        R9-2)  echo "Platform fan-out (out-of-scope — retired)" ;;
        R9-3)  echo "Operational expansion (deferred speculative)" ;;
        # v2 substrate arc (R10-*) — cryptographic-commitment shapes
        R10-1) echo "Bayesian game (ZK soundness under adversarial inputs)" ;;
        R10-2) echo "Commitment device (Merkle anchor as irreversible commit)" ;;
        R10-3) echo "Substrate enumeration (known-knowns vs known-unknowns)" ;;
        R10-4) echo "Privacy by structure (hash-only commitment)" ;;
        R10-5) echo "Commitment device (scaffold reserving future namespace)" ;;
        # v2 open-problems arc (R11-*) — game-theoretic open problems
        R11-1) echo "Repeated cooperative game (cryptographic-era transitions)" ;;
        R11-2) echo "Principal-agent (recovery requester may be adversarial)" ;;
        R11-3) echo "Trust federation (cross-jurisdiction coordination)" ;;
        R11-4) echo "Population coordination (Schelling-point enrollment)" ;;
        R11-5) echo "Information asymmetry (duress code as signaling)" ;;
        R11-6) echo "Principal-agent monitoring (issuer-discretion bounds)" ;;
        R11-7) echo "Adversary modeling (formal redaction proof)" ;;
        *)     echo "(unknown game type — annotate in scripts/ai-architect.sh game_type_for)" ;;
    esac
}

# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------
section() { printf "\n${BOLD}${NAVY}─── %s ───${NC}\n\n" "$1"; }
hdr()     { printf "${BOLD}${GOLD}═══ %s ═══${NC}\n" "$1"; }

# Find the previous Architect brief (for Section VI self-monitoring).
prev_brief() {
    ls -1t "$ROOT/journal/"*-architect.md 2>/dev/null | head -1
}

# Generate next sequential suggestion ID for today's brief.
next_arch_id() {
    local n=$1
    printf "arch-%s-%03d" "$DATE_STAMP" "$n"
}

# Check whether a recommendation ID has been acted on (referenced in any
# journal entry or CHANGELOG line since it was made).
rec_status() {
    local id="$1"
    local hits
    hits=$(grep -rl "$id" "$ROOT/journal" "$ROOT/CHANGELOG.md" 2>/dev/null \
           | grep -v "$DATE_STAMP-architect" \
           | wc -l | tr -d ' ')
    if [ "$hits" -ge 1 ]; then
        echo "acted"
    else
        echo "pending"
    fi
}

# -----------------------------------------------------------------------------
# Section I: State of the realm
# -----------------------------------------------------------------------------
emit_state() {
    section "I. STATE OF THE REALM"

    local c_count
    c_count=$("$HERE/ai-status.sh" 2>/dev/null | grep -c '✓ C' || true)

    local v1_done v1_ret v2_done v2_open
    v1_done=$(grep -cE '^[0-9]+\. ✅' "$ROOT/MISSION.md")
    # v8.27 — count both ✗ RETIRED (post-v8.27) and ⏸ DEFERRED (pre-v8.27)
    # for back-compat. Display uses the post-v8.27 symbol.
    v1_ret=$(grep -cE  '^[0-9]+\. (✗|⏸)'  "$ROOT/MISSION.md")
    v2_done=$(grep -cE 'M2-[0-9]+\. ✅' "$ROOT/MISSION.md")
    v2_open=$(grep -cE 'M2-[0-9]+\. ⬜' "$ROOT/MISSION.md")

    printf "  Constraints in force: ${G}%s/10${NC} hard + CM. " "$c_count"
    if [ "$c_count" -eq 10 ]; then
        printf "${G}All green.${NC}\n"
    else
        printf "${R}One or more red.${NC}\n"
    fi
    printf "  Mission v1: ${G}%s ✅${NC} closed / ${DIM}✗ %s retired${NC}\n" "$v1_done" "$v1_ret"
    printf "  Mission v2: ${G}%s ✅${NC} done / ${Y}⬜ %s open${NC}\n" "$v2_done" "$v2_open"

    # Pressure top-3 from ai-meta
    printf "\n  ${DIM}30-day constraint-touch pressure (top 3):${NC}\n"
    "$HERE/ai-meta.sh" constraints 2>&1 \
        | grep -E '^\s+\x1b\[0;3[12]m|^\s+C[0-9]' \
        | sed -E 's/\x1b\[[0-9;]*m//g' \
        | sort -t':' -k2 -rn \
        | head -3 \
        | awk -F: '{ gsub(/^ +/,"",$0); printf "    %s\n", $0 }' \
        || printf "    ${DIM}(pressure data unavailable)${NC}\n"

    # Last journal activity
    local last_journal
    last_journal=$(ls -1t "$ROOT/journal/"[0-9]*-[0-9]*.md 2>/dev/null | head -1)
    if [ -n "$last_journal" ]; then
        local decisions
        decisions=$(grep -cE '^- \*\*decision\*\*' "$last_journal" 2>/dev/null || true)
        printf "\n  Last journal: ${DIM}%s${NC} (%s decision(s))\n" "$(basename "$last_journal" .md)" "$decisions"
    fi
}

# -----------------------------------------------------------------------------
# Section II: Strategic outlook
# -----------------------------------------------------------------------------
emit_outlook() {
    section "II. STRATEGIC OUTLOOK"

    local propose_out
    propose_out=$("$HERE/ai-propose.sh" 3 2>/dev/null \
                  | sed -E 's/\x1b\[[0-9;]*m//g')

    # Posture-aware framing. Heavy-production takes precedence over
    # steady-state (the most recent revocation wins).
    if is_heavy_production; then
        printf "  ${DIM}Mission state: ${BOLD}heavy-production${NC}${DIM} (active since 2026-05-14).\n"
        printf "  Steady-state revoked by Sanctum 2026-05-14-steady-state-revocation-heavy-production.md.\n"
        printf "  Default response shape: ${BOLD}ship the complete thing${NC}${DIM}.\n"
        printf "  Constitutional questions still gated through Sanctum (Pattern #20).${NC}\n\n"
    elif is_steady_state; then
        printf "  ${DIM}Mission state: ${BOLD}steady-state${NC}${DIM} (resolved 2026-05-12).\n"
        printf "  No open mission items. The list below is housekeeping; the Architect\n"
        printf "  surfaces it for visibility, not as a recommendation to ship.${NC}\n\n"
    fi

    # Layer-ratio line per S2 Sanctum Position C (v9.10), refined v9.11:
    # surface cognitive-vs-product split across the last 5 ships. Pre-v9.11
    # the heuristic counted ANY mention of a layer's path in the entry
    # body (narrative inflated L1). v9.11 counts only BACKTICKED file paths
    # (the artifacts-list discipline established by v8.20+) — these are
    # the actual modified files, not prose mentions.
    local cl="$ROOT/CHANGELOG.md"
    if [[ -f "$cl" ]]; then
        local ratio
        ratio=$(awk '
            BEGIN { v = 0 }
            /^## v[0-9]/ {
                v++
                if (v > 5) exit
                next
            }
            v >= 1 && v <= 5 {
                # Find all backticked tokens on this line; for each,
                # classify if it looks like a file path (contains "/")
                # AND matches a known top-level directory.
                line = $0
                while (match(line, /`[^`]+`/) > 0) {
                    tok = substr(line, RSTART + 1, RLENGTH - 2)
                    line = substr(line, RSTART + RLENGTH)
                    # Only consider tokens that look like file paths
                    if (index(tok, "/") == 0) continue
                    # L1: polaris_web/, polaris_sql/, polaris_zk/, polaris_cli/.
                    # Exclude __version__.py because every ship bumps it,
                    # so counting it would inflate L1 to always-true and
                    # destroy the signal value of the metric.
                    if (tok ~ /^polaris_(web|sql|zk|cli)\// && tok !~ /__version__\.py/) l1[v] = 1
                    # L2: polaris_hydra/, polaris_swarm/ (excluding civitas which is L1-adjacent identity surface)
                    else if (tok ~ /^polaris_(hydra|swarm)\//) l2[v] = 1
                    # L3: scripts/, meta/, sanctum/
                    else if (tok ~ /^(scripts|meta|sanctum)\//) l3[v] = 1
                    # L4: docs/, DEVNOTES/, README, CHANGELOG, ROADMAP, journal/
                    else if (tok ~ /^(docs|DEVNOTES|journal)\// || tok ~ /(README|CHANGELOG|ROADMAP|MISSION|CLAUDE)\.md$/) l4[v] = 1
                }
            }
            END {
                c1=0; c2=0; c3=0; c4=0
                for (i = 1; i <= 5; i++) {
                    if (l1[i]) c1++
                    if (l2[i]) c2++
                    if (l3[i]) c3++
                    if (l4[i]) c4++
                }
                printf "L1×%d L2×%d L3×%d L4×%d", c1, c2, c3, c4
            }
        ' "$cl")
        printf "  ${DIM}Layer ratio (last 5 ships): ${BOLD}%s${NC}${DIM}. Per S2 Sanctum (cognitive-layer-ratio); cadence rule: at least 1 Layer-1 per 5 ships. (v9.11: counts backticked file paths only; narrative mentions excluded.)${NC}\n\n" "$ratio"
    fi

    printf "  ${DIM}Top-3 moves from ai-propose, annotated with game-type:${NC}\n\n"

    # Parse the propose output. Each item is a block starting with N. R-ID — title
    echo "$propose_out" \
        | awk '/^[0-9]\. R[0-9]+-[0-9]+/{
            print "MARK"; print
            next
          }
          /^   risk:/  { print }
          /^   mission:/ { print }' \
        | awk -v R="$R" -v G="$G" -v Y="$Y" -v BOLD="$BOLD" -v DIM="$DIM" -v NC="$NC" '
          BEGIN { idx=0 }
          /^MARK$/ { idx++; next }
          /^[0-9]\. R/ {
              # Line is like "1. R11-6 — Issuer-discretion bounds"
              line = $0
              sub(/^[0-9]\. /, "", line)
              # Extract R-id
              rid = line
              sub(/ .*/, "", rid)
              titles[idx] = line
              rids[idx] = rid
              next
          }
          /risk:/ {
              gsub(/^   risk: */, "")
              risks[idx] = $0
              next
          }
          /mission:/ {
              gsub(/^   mission: */, "")
              missions[idx] = $0
              next
          }
          END {
              for (i = 1; i <= idx; i++) {
                  printf "  %s%d.%s %s\n", BOLD, i, NC, titles[i]
                  printf "     risk:      %s\n", risks[i]
                  printf "     mission:   %s\n", missions[i]
                  # game-type is filled in below via shell
                  printf "     game-type: __GAMETYPE__%s__\n", rids[i]
                  printf "\n"
              }
          }' | while IFS= read -r line; do
              # Substitute the game-type placeholder
              if echo "$line" | grep -q '__GAMETYPE__'; then
                  rid=$(echo "$line" | sed -E 's/.*__GAMETYPE__([^_]+)__.*/\1/')
                  gt=$(game_type_for "$rid")
                  echo "$line" | sed "s|__GAMETYPE__${rid}__|${gt}|"
              else
                  echo "$line"
              fi
          done

    printf "  ${DIM}Recommendations cite their R-id; full bodies in ROADMAP.md.${NC}\n"
}

# -----------------------------------------------------------------------------
# Section III: Drift detection
# -----------------------------------------------------------------------------
emit_drift() {
    section "III. DRIFT DETECTION"

    local coh_summary
    coh_summary=$("$HERE/ai-coherence.sh" 2>&1 \
                  | sed -E 's/\x1b\[[0-9;]*m//g' \
                  | grep -E 'STRUCTURE INTACT|MINOR DRIFT|STRUCTURAL DRIFT' \
                  | head -1)

    local meta_summary
    meta_summary=$("$HERE/ai-meta.sh" 2>&1 \
                   | sed -E 's/\x1b\[[0-9;]*m//g' \
                   | grep -E 'LAYER SELF-MONITORING|MINOR META-DRIFT|META-DRIFT' \
                   | head -1)

    local link_summary
    link_summary=$("$HERE/ai-link-check.sh" 2>&1 | tail -1 \
                   | sed -E 's/\x1b\[[0-9;]*m//g')

    # Pattern catalog warmth
    local warm
    warm=$("$HERE/ai-meta.sh" patterns 2>&1 \
           | grep -oE '[0-9]+/[0-9]+ warm' | head -1)

    printf "  ${BOLD}ai-coherence:${NC}     %s\n" "$(echo "$coh_summary" | sed 's/^ *//')"
    printf "  ${BOLD}ai-meta:${NC}          %s\n" "$(echo "$meta_summary" | sed 's/^ *//')"
    printf "  ${BOLD}ai-link-check:${NC}    %s\n" "$(echo "$link_summary" | sed 's/^ *//')"
    printf "  ${BOLD}Pattern catalog:${NC}  %s (cold patterns = shapes not yet hit, not necessarily wrong)\n" "$warm"

    # Doc-schema correspondence — pull from the test
    local docs_test_pass
    if python3 -c "
import sys, os, re
ROOT='$ROOT'
schema = set()
for f in ['polaris_sql/01_schema.sql', 'polaris_sql/10_auth.sql']:
    for line in open(os.path.join(ROOT, f)):
        m = re.match(r'^CREATE TABLE\s+([A-Z]\w+)\s*\(', line)
        if m: schema.add(m.group(1))
doc = set()
for line in open(os.path.join(ROOT, 'docs/reference/DATA-MODEL.md')):
    m = re.match(r'^###\s+\`([A-Z]\w+)\`', line)
    if m: doc.add(m.group(1))
sys.exit(0 if schema == doc else 1)
" 2>/dev/null; then
        printf "  ${BOLD}Doc↔schema:${NC}       ${G}aligned${NC} (every schema table documented; no phantoms)\n"
    else
        printf "  ${BOLD}Doc↔schema:${NC}       ${R}DRIFT${NC} (run test_structural_invariants.py::TestDocSchemaCorrespondence)\n"
    fi
}

# -----------------------------------------------------------------------------
# Section IV: Threats and adversaries
# -----------------------------------------------------------------------------
emit_threats() {
    section "IV. THREATS AND ADVERSARIES"

    # Identify the top-pressure constraint
    local top_pressure
    top_pressure=$("$HERE/ai-meta.sh" constraints 2>&1 \
        | sed -E 's/\x1b\[[0-9;]*m//g' \
        | grep -E '^\s+C[0-9]+:' \
        | sort -t':' -k2 -rn \
        | head -1 \
        | grep -oE 'C[0-9]+' \
        | head -1)

    [ -z "$top_pressure" ] && top_pressure="C10"

    printf "  Top-pressure constraint: ${BOLD}%s${NC} (most-touched in 30 days)\n" "$top_pressure"
    printf "\n  ${DIM}Adversary walk:${NC}\n"

    "$HERE/ai-adversary.sh" "$top_pressure" 2>&1 \
        | sed -E 's/\x1b\[[0-9;]*m//g' \
        | grep -A 1 -E '^[0-9]\.' \
        | grep -v '^--$' \
        | awk 'NR<=20{print "    "$0}'

    printf "\n  ${DIM}The Architect watches the second-best attack. That is the next${NC}\n"
    printf "  ${DIM}move an adversary makes after the primary defense holds.${NC}\n"
}

# -----------------------------------------------------------------------------
# Section V: Suggestions
# -----------------------------------------------------------------------------
# Posture detectors.
#
# Polaris has two named post-v2 postures, declared and revoked via
# Sanctum:
#   - steady-state (v8.31, 2026-05-12) — decline-and-surface
#   - heavy-production (v8.31-revocation, 2026-05-14) — active-production
#
# Heavy-production REPLACES steady-state when both markers are present
# (the revocation Sanctum's existence is the determinant). Detection
# follows that precedence: is_heavy_production() returns true iff the
# revocation Sanctum file exists; is_steady_state() returns true iff
# the steady-state marker is in MISSION.md AND heavy-production is
# NOT active.
#
# Both contracts are operator-revocable. If a future Sanctum revokes
# heavy-production, this detector layer should grow another tier.
is_heavy_production() {
    [ -f "$ROOT/sanctum/2026-05-14-steady-state-revocation-heavy-production.md" ] 2>/dev/null
}

is_steady_state() {
    if is_heavy_production; then
        return 1
    fi
    grep -q "Resolved 2026-05-12: steady-state" "$ROOT/MISSION.md" 2>/dev/null
}

emit_suggestions() {
    section "V. SUGGESTIONS"

    printf "  ${DIM}Concrete next moves, each with an ID for tracking across briefs.${NC}\n\n"

    # Suggestion 1: top propose item — framing depends on mission state
    local id1 top_id top_title top_risk top_mission
    id1=$(next_arch_id 1)
    top_id=$("$HERE/ai-propose.sh" 1 2>/dev/null \
             | sed -E 's/\x1b\[[0-9;]*m//g' \
             | grep -oE 'R[0-9]+-[0-9]+' | head -1)
    if [ -n "$top_id" ]; then
        top_title=$("$HERE/ai-propose.sh" 1 2>/dev/null \
                    | sed -E 's/\x1b\[[0-9;]*m//g' \
                    | grep -E "$top_id " | head -1 | sed -E 's/^[0-9]+\. //')
        if is_heavy_production; then
            # Heavy-production: ship the complete thing. Top-propose
            # item is a candidate to ship under the active-production
            # default. MEDIUM-risk still goes through proposal +
            # Sanctum-DECIDED-on-arrival; HIGH-risk still opens a fresh
            # Sanctum; constitutional questions still go to VANTA.
            printf "  ${BOLD}%s${NC}: Ship-candidate ${BOLD}%s${NC}\n" "$id1" "$top_id"
            printf "    %s\n" "$top_title"
            printf "    ${DIM}Evidence:${NC} ai-propose.sh top-ranked; ROADMAP.md\n"
            printf "    ${DIM}Action:${NC}   ${BOLD}ship the complete thing${NC} under heavy-production posture.\n"
            printf "             MEDIUM/HIGH-risk still gates through Sanctum (DECIDED-on-arrival\n"
            printf "             when directive is unambiguous; protocol is faster, not skipped).\n\n"
        elif is_steady_state; then
            # Post-v2 steady-state: top propose item is a maintenance
            # candidate, not a mission-promotion candidate. Architect
            # surfaces it without recommending it; VANTA decides whether
            # to schedule housekeeping.
            printf "  ${BOLD}%s${NC}: Maintenance candidate ${BOLD}%s${NC}\n" "$id1" "$top_id"
            printf "    %s\n" "$top_title"
            printf "    ${DIM}Evidence:${NC} ai-propose.sh top-ranked; ROADMAP.md\n"
            printf "    ${DIM}Action:${NC}   ${BOLD}housekeeping${NC} (steady-state). Schedule when VANTA wants maintenance done.\n"
            printf "    ${DIM}Note:${NC}     this is NOT a v3 opening. v3 opens only when an external trigger fires\n"
            printf "             (Arc B prod-deploy / Arc C partner / novel arc with documented cause).\n\n"
        else
            printf "  ${BOLD}%s${NC}: Promote ${BOLD}%s${NC}\n" "$id1" "$top_id"
            printf "    %s\n" "$top_title"
            printf "    ${DIM}Evidence:${NC} ai-propose.sh top-ranked; ROADMAP.md\n"
            printf "    ${DIM}Action:${NC}   if MEDIUM, write proposals/${top_id}-*.md and wait for VANTA approval\n\n"
        fi
    fi

    # Suggestion 2: a cognitive-layer improvement drawn from ai-meta findings
    local id2
    id2=$(next_arch_id 2)
    local cold_count
    cold_count=$("$HERE/ai-meta.sh" patterns 2>&1 \
                 | grep -oE '[0-9]+/22 warm' \
                 | head -1 \
                 | grep -oE '^[0-9]+')
    if [ -n "$cold_count" ] && [ "$cold_count" -lt 12 ]; then
        printf "  ${BOLD}%s${NC}: Investigate cold-pattern signal\n" "$id2"
        printf "    Pattern catalog is %s/22 warm. Either we journal pattern-matches\n" "$cold_count"
        printf "    too rarely, or the 22-shape closure is too broad for Polaris's domain.\n"
        printf "    ${DIM}Evidence:${NC} ai-meta.sh patterns\n"
        printf "    ${DIM}Action:${NC}   when next ai-pattern.sh matches a cold pattern, log it explicitly\n\n"
    fi

    # Suggestion 3: schema/doc/test correspondence check
    local id3
    id3=$(next_arch_id 3)
    printf "  ${BOLD}%s${NC}: Continue the drift→test promotion loop\n" "$id3"
    printf "    v8.12 made doc↔schema executable. Apply the same pattern wherever\n"
    printf "    ai-meta or ai-coherence surfaces a new drift class.\n"
    printf "    ${DIM}Evidence:${NC} v8.12 CHANGELOG; the BiometricEnrollment phantom case\n"
    printf "    ${DIM}Action:${NC}   on every drift catch, ask whether the catch is testable\n"
}

# -----------------------------------------------------------------------------
# Section VI: Self-monitoring
# -----------------------------------------------------------------------------
emit_self_monitor() {
    section "VI. SELF-MONITORING"

    local prev
    prev=$(prev_brief)

    if [ -n "$prev" ] && [ "$(basename "$prev" .md)" != "$DATE_STAMP-architect" ]; then
        local prev_name
        prev_name=$(basename "$prev" .md)
        printf "  ${DIM}Previous brief: %s${NC}\n\n" "$prev_name"
        printf "  Tracking prior recommendations:\n"
        # Extract arch-IDs from prior brief and check status
        local found_any=0
        while IFS= read -r prev_id; do
            [ -z "$prev_id" ] && continue
            local status
            status=$(rec_status "$prev_id")
            case "$status" in
                acted)   printf "    ${G}✓${NC} %s : referenced in journal/CHANGELOG since brief\n" "$prev_id" ;;
                pending) printf "    ${Y}⏸${NC} %s : pending; no action recorded\n" "$prev_id" ;;
            esac
            found_any=1
        done < <(grep -oE 'arch-[0-9]{4}-[0-9]{2}-[0-9]{2}-[0-9]{3}' "$prev" | sort -u)
        if [ "$found_any" -eq 0 ]; then
            printf "    ${DIM}(prior brief had no tracked IDs)${NC}\n"
        fi
    else
        printf "  ${DIM}No prior brief found. This is the first.${NC}\n"
    fi

    printf "\n  ${BOLD}Observations about this brief:${NC}\n"
    printf "    - Suggestions span MEDIUM (mission item) and LOW (cognitive-layer).\n"
    printf "    - Adversary walk used %s as proxy for system-wide threat surface.\n" "${top_pressure:-C10}"
    printf "    - Drift detection used 4 input tools; if a 5th catch class is needed\n"
    printf "      (e.g. test-coverage drift), add it via TestCrossLayerPrinciples.\n"
    printf "    - ${DIM}Uncertain about:${NC} whether the cold-pattern count is a real signal\n"
    printf "      or a journaling-style artifact. The next brief will track this.\n"
}

# -----------------------------------------------------------------------------
# Closing
# -----------------------------------------------------------------------------
emit_closing() {
    section "CLOSING"

    printf "  Reporting up. Recommend reviewing suggestions, then either approving\n"
    printf "  the MEDIUM-risk ${BOLD}arch-%s-001${NC} or selecting a different top move\n" "$DATE_STAMP"
    printf "  via ${BOLD}ai-propose.sh 5${NC}.\n\n"
    printf "  ${DIM}── Polaris Architect (generated by scripts/ai-architect.sh on %s)${NC}\n" "$DATETIME"
    printf "  ${DIM}── Persona spec in meta/architect.md. Run with --voice to read it.${NC}\n"
}

# -----------------------------------------------------------------------------
# Reflect mode — analyze prior briefs for drift in the Architect's voice
# -----------------------------------------------------------------------------
do_reflect() {
    hdr "POLARIS ARCHITECT — REFLECTION"
    printf "  ${DIM}%s${NC}\n\n" "$DATETIME"

    local n_briefs
    n_briefs=$(ls -1 "$ROOT/journal/"*-architect.md 2>/dev/null | wc -l | tr -d ' ')

    printf "  Briefs on file: %s\n\n" "$n_briefs"

    if [ "$n_briefs" -lt 2 ]; then
        printf "  ${Y}Brief-history reflection needs ≥ 2 briefs; skipping that section.${NC}\n"
        do_reflect_sanctum
        return
    fi

    # Common voice-drift signals
    printf "  ${BOLD}Voice drift scan:${NC}\n"
    local em_dash_count
    em_dash_count=$(grep -c '—' "$ROOT/journal/"*-architect.md 2>/dev/null | awk -F: '{s+=$2}END{print s}')
    if [ "${em_dash_count:-0}" -gt 0 ]; then
        printf "    ${Y}!${NC} %s em-dash(es) found across briefs (VANTA rule: none in own prose)\n" "$em_dash_count"
    else
        printf "    ${G}✓${NC} No em-dashes in Architect prose\n"
    fi

    # Suggestion-acted-on rate
    local total_recs acted_recs
    total_recs=$(grep -hoE 'arch-[0-9]{4}-[0-9]{2}-[0-9]{2}-[0-9]{3}' "$ROOT/journal/"*-architect.md 2>/dev/null | sort -u | wc -l | tr -d ' ')
    acted_recs=0
    for id in $(grep -hoE 'arch-[0-9]{4}-[0-9]{2}-[0-9]{2}-[0-9]{3}' "$ROOT/journal/"*-architect.md 2>/dev/null | sort -u); do
        if [ "$(rec_status "$id")" = "acted" ]; then
            acted_recs=$((acted_recs + 1))
        fi
    done
    printf "    Recommendations: ${G}%s acted${NC} / %s total\n" "$acted_recs" "$total_recs"

    do_reflect_sanctum
    do_reflect_hydra_briefs
}

# ─────────────────────────────────────────────────────────────────────
# v9.06 / Wave 2 / C1 — HYDRA brief-archive reflection.
#
# Pre-v9.06 the Architect's --reflect read journal/*-architect.md only.
# v9.04 introduced HYDRA's hybrid intelligence brief-archive at
# journal/hydra/<YYYY-MM-DD>-<HHMM>.md. The two reflection paths were
# unaware of each other. Cross-pollination per the polaris-self-roadmap
# C1 item: surface HYDRA brief activity inline so the Architect's
# reflection sees the lens's own state-of-system trace.
# ─────────────────────────────────────────────────────────────────────
do_reflect_hydra_briefs() {
    local hydra_dir="$ROOT/journal/hydra"
    if [ ! -d "$hydra_dir" ]; then
        return
    fi

    local n_briefs
    n_briefs=$(ls -1 "$hydra_dir"/*.md 2>/dev/null | wc -l | tr -d ' ')

    printf "\n  ${BOLD}HYDRA brief-archive (v9.04 lens-output, C1 cross-ref):${NC}\n"
    printf "    HYDRA briefs on file: %s\n" "$n_briefs"

    if [ "$n_briefs" -eq 0 ]; then
        printf "    ${DIM}(empty: run 'ai-hydra.sh --full --save' to start the archive)${NC}\n"
        return
    fi

    local latest latest_basename age_days
    latest=$(ls -1t "$hydra_dir"/*.md 2>/dev/null | head -1)
    latest_basename=$(basename "$latest")

    # macOS-compatible age computation: stat -f%m latest mtime in epoch seconds
    if command -v stat >/dev/null 2>&1; then
        local now_ts latest_ts
        now_ts=$(date +%s)
        # macOS stat -f vs Linux stat -c
        if stat -f%m "$latest" >/dev/null 2>&1; then
            latest_ts=$(stat -f%m "$latest")
        else
            latest_ts=$(stat -c%Y "$latest")
        fi
        age_days=$(awk -v n="$now_ts" -v l="$latest_ts" 'BEGIN{printf "%.1f", (n-l)/86400}')
        printf "    Latest: %s (%sd old)\n" "$latest_basename" "$age_days"
    else
        printf "    Latest: %s\n" "$latest_basename"
    fi

    # Freshness signal — matches cognitive_watcher's H1 channel thresholds
    if [ "${age_days:-0}" != "0" ]; then
        local stale_check
        stale_check=$(awk -v a="$age_days" 'BEGIN{print (a >= 30 ? "DEAD" : (a >= 14 ? "STALE" : "FRESH"))}')
        case "$stale_check" in
            DEAD)
                printf "    ${R}!${NC} brief-archive DEAD (>30d): cognitive_watcher H1 will alert\n" ;;
            STALE)
                printf "    ${Y}!${NC} brief-archive STALE (>14d): refresh via 'ai-hydra.sh --full --save'\n" ;;
            FRESH)
                printf "    ${G}✓${NC} brief-archive fresh\n" ;;
        esac
    fi

    if [ "$n_briefs" -ge 2 ]; then
        printf "    ${DIM}HYDRA's compute_delta reads cross-run; briefs are mutually comparable.${NC}\n"
    fi
}

# ─────────────────────────────────────────────────────────────────────
# Sanctum prediction-vs-reality (v8.20)
# ─────────────────────────────────────────────────────────────────────
do_reflect_sanctum() {
    local reflect_n="${REFLECT_N:-10}"
    local sanctum_dir="$ROOT/sanctum"

    if [ ! -d "$sanctum_dir" ]; then
        return
    fi

    printf "\n  ${BOLD}Sanctum prediction-vs-reality (last %s closed-or-rejected):${NC}\n" "$reflect_n"

    local sanctum_count=0
    local closed_count=0
    local rejected_count=0
    local backfilled_count=0
    local with_outcome_link=0

    # Walk recent sessions (most recent first by filename, which is date-prefixed)
    while IFS= read -r f; do
        [ -z "$f" ] && continue
        [ "$(basename "$f")" = "README.md" ] && continue
        sanctum_count=$((sanctum_count + 1))

        local status
        status=$(grep -E '^\*\*Status:\*\*' "$f" | head -1 | sed 's/^\*\*Status:\*\* *//' | tr -d ' ')

        case "$status" in
            CLOSED)   closed_count=$((closed_count + 1)) ;;
            REJECTED) rejected_count=$((rejected_count + 1)) ;;
        esac

        # Reconstruction note?
        if grep -q "Backfilled retroactively" "$f" 2>/dev/null; then
            backfilled_count=$((backfilled_count + 1))
        fi

        # Outcome links to journal/CHANGELOG?
        if grep -A 20 '^## VII\. Outcome' "$f" 2>/dev/null | grep -qE 'CHANGELOG|journal'; then
            with_outcome_link=$((with_outcome_link + 1))
        fi
    done < <(ls -1 "$sanctum_dir"/*.md 2>/dev/null | grep -v README | sort -r | head -"$reflect_n")

    printf "    Sessions reviewed:         %s\n" "$sanctum_count"
    printf "    Closed (executed):         ${G}%s${NC}\n" "$closed_count"
    printf "    Rejected (declined):       ${Y}%s${NC}\n" "$rejected_count"
    printf "    Backfilled (reconstructed): ${DIM}%s${NC}\n" "$backfilled_count"
    printf "    With CHANGELOG/journal links in §VII: %s/%s\n" "$with_outcome_link" "$closed_count"

    # Quality signals.
    if [ "$closed_count" -gt 0 ] && [ "$with_outcome_link" -lt "$closed_count" ]; then
        local missing=$((closed_count - with_outcome_link))
        printf "    ${Y}!${NC} %s closed session(s) lack CHANGELOG/journal links in §VII Outcome\n" "$missing"
    fi
    if [ "$rejected_count" -gt 0 ]; then
        printf "    ${DIM}Rejected sessions are valuable artifacts: they document what was considered and not done.${NC}\n"
    fi
    if [ "$sanctum_count" -lt 5 ]; then
        printf "    ${DIM}Sample size N=%s is small; pattern claims should be tentative.${NC}\n" "$sanctum_count"
    fi
}

# -----------------------------------------------------------------------------
# Cron mode — terser brief for scheduled invocations
# -----------------------------------------------------------------------------
do_cron() {
    hdr "POLARIS ARCHITECT, TERSE BRIEF"
    printf "  ${DIM}%s${NC}\n" "$DATETIME"
    local c_count meta_ok coh_ok
    c_count=$("$HERE/ai-status.sh" 2>/dev/null | grep -c '✓ C' || true)
    if "$HERE/ai-meta.sh" 2>&1 | sed -E 's/\x1b\[[0-9;]*m//g' | grep -q 'LAYER SELF-MONITORING IS HEALTHY'; then
        meta_ok=OK
    else
        meta_ok=DRIFT
    fi
    local coh_line
    coh_line=$("$HERE/ai-coherence.sh" 2>&1 | sed -E 's/\x1b\[[0-9;]*m//g' \
               | grep -E 'STRUCTURE INTACT|MINOR DRIFT|STRUCTURAL DRIFT' | head -1)
    case "$coh_line" in
        *"STRUCTURE INTACT"*)   coh_ok=OK ;;
        *"MINOR DRIFT"*)        coh_ok=minor ;;
        *"STRUCTURAL DRIFT"*)   coh_ok=DRIFT ;;
        *)                      coh_ok="?" ;;
    esac
    printf "  C%s/10  meta=%s  coherence=%s\n" "$c_count" "$meta_ok" "$coh_ok"
    local top
    top=$("$HERE/ai-propose.sh" --strict 1 2>/dev/null | grep -oE 'R[0-9]+-[0-9]+' | head -1)
    [ -n "$top" ] && printf "  Top move: %s\n" "$top"
}

# -----------------------------------------------------------------------------
# Full brief
# -----------------------------------------------------------------------------
do_full() {
    {
        hdr "POLARIS ARCHITECT'S BRIEF"
        printf "  Generated: ${DIM}%s${NC}\n" "$DATETIME"
        printf "  Reporting to: ${GOLD}VANTA${NC}\n"
        printf "  Persona: ${DIM}meta/architect.md${NC} (run --voice for full spec)\n"

        emit_state
        emit_outlook
        emit_drift
        emit_threats
        emit_suggestions
        emit_self_monitor
        emit_closing
    }
}

# -----------------------------------------------------------------------------
# Dispatch
# -----------------------------------------------------------------------------
trap 'exit 0' EXIT  # ai-* sub-script greps may return 1 on empty match; that's fine
case "$MODE" in
    reflect)  do_reflect ;;
    cron)     do_cron ;;
    full)
        if [ "$SAVE" -eq 1 ]; then
            BRIEF_FILE="$ROOT/journal/$DATE_STAMP-architect.md"
            TMP_CAPTURE=$(mktemp)
            do_full > "$TMP_CAPTURE" 2>&1
            cat "$TMP_CAPTURE"
            {
                printf "# Polaris Architect's Brief, %s\n\n" "$DATE_STAMP"
                printf "Generated: %s\n" "$DATETIME"
                printf "Persona: meta/architect.md\n\n"
                printf '```\n'
                sed -E 's/\x1b\[[0-9;]*m//g' "$TMP_CAPTURE"
                printf '```\n'
            } > "$BRIEF_FILE"
            rm -f "$TMP_CAPTURE"
            printf "\n${DIM}Saved to %s${NC}\n" "${BRIEF_FILE#$ROOT/}"
        else
            do_full
        fi
        ;;
esac
