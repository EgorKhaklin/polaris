#!/bin/bash
# =============================================================================
# scripts/ai-lattice.sh
#
# Walks the C1-C10 constraint lattice from any node. Surfaces:
#
#   1. The chosen node — its position (APEX / EXPAND·N / CONTRACT·N /
#      BALANCE·N / MANIFEST) and what it enforces
#   2. Its NEIGHBORS — constraints at the same tier
#   3. Its COMPLEMENT — the inverse constraint across the polarity
#      (EXPAND ↔ CONTRACT at the same tier)
#   4. Its DEPENDENCY CASCADE — what breaks if this node is removed
#
# Use this when you're about to change a constraint and want to know
# what else in the system might need to move. The three-view return
# forces multi-angle thinking: "if I touch C5, what else needs to be
# considered?" Answer: its tier neighbors and its polarity complement.
#
# This is the operational counterpart to meta/constraint-lattice.md.
# The doc has the full structural argument; this script lets you
# query the lattice at the speed of bash.
#
# Usage:
#     ai-lattice.sh C5                 # show C5's position, neighbors, complement
#     ai-lattice.sh --diagram          # print the full topology
#     ai-lattice.sh --polarity         # show all EXPAND↔CONTRACT pairs
#     ai-lattice.sh --tier 2           # show all tier-2 constraints
# =============================================================================

set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"

if [ -t 1 ]; then
    BOLD="\033[1m"; G="\033[0;32m"; Y="\033[0;33m"; R="\033[0;31m"
    DIM="\033[2m"; CYAN="\033[0;36m"; BLUE="\033[38;5;75m"; NC="\033[0m"
else
    BOLD=""; G=""; Y=""; R=""; DIM=""; CYAN=""; BLUE=""; NC=""
fi

# -----------------------------------------------------------------------------
# The lattice data: constraint | position | tier | pillar | summary | complement
# -----------------------------------------------------------------------------
read -r -d '' LATTICE_DATA <<'EOF' || true
C10|APEX|0|center|identity ≠ money — no MonetaryClaim table|
C7|EXPAND·1|1|right|algorithm metadata via CryptographicAlgorithm table|C2
C2|CONTRACT·1|1|left|ZERO_KNOWLEDGE verifications have token_id IS NULL|C7
C5|EXPAND·2|2|right|CSP script-src 'self' — same-origin scripts permitted|C4
C4|CONTRACT·2|2|left|failed_login_count increments atomic (no TOCTOU)|C5
C3|BALANCE·2|2|center|one ACTIVE token per Individual (uq_one_active_per_person)|
C8|EXPAND·3|3|right|atlas API endpoints hard-capped (_ATLAS_MAX_*)|C6
C6|CONTRACT·3|3|left|disclosure level enforced server-side|C8
C1|BALANCE·3|3|center|TokenLifecycleEvent/VerificationEvent append-only|
C9|MANIFEST|4|center|concurrency tests use real threading (not mocks)|
CM|META|meta|meta|cognitive layer self-monitors via executable checks (ai-meta.sh)|
EOF

# -----------------------------------------------------------------------------
# Cascade data: what breaks when X is removed (semicolon-separated targets)
# -----------------------------------------------------------------------------
read -r -d '' CASCADE_DATA <<'EOF' || true
C10|system becomes financial surveillance; meaning of every other constraint changes
C7|can't migrate algorithms; signatures eventually become unverifiable; C1's audit becomes audit of unverifiable signatures
C2|ZK privacy collapses; verification graph reconstructable by anyone with read access; system's value proposition gone
C5|XSS leaks operator session; attacker exfiltrates tokens; C3's uniqueness no longer protects (attacker has a legitimate token)
C4|brute force succeeds; legitimate operators locked out; C5+C9 protections moot once attacker is in
C3|repudiation defense collapses for any individual whose token is duplicated
C8|atlas DoS takes down worker pool; C9 tests pass but production crashes
C6|client upgrades ZK to FULL; C2 broken at app layer (trigger still enforces, but app-side bypass exists)
C1|audit history mutable; non-repudiation collapses; every constraint's enforcement retroactively deniable
C9|concurrency arguments unverified; production failures reveal them, expensively
CM|cognitive layer drifts silently; doc claims diverge from code; ai-* scripts decay; pattern catalog dies; Sanctum lifecycle untracked; v8.20 self-monitoring discipline collapses
EOF

# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------
lookup() {
    local cid="$1"
    echo "$LATTICE_DATA" | awk -F '|' -v cid="$cid" '$1 == cid { print; exit }'
}

cascade_for() {
    local cid="$1"
    echo "$CASCADE_DATA" | awk -F '|' -v cid="$cid" '$1 == cid { print $2; exit }'
}

print_diagram() {
    printf "${BLUE}${BOLD}═══ Polaris constraint lattice ═══${NC}\n\n"
    printf "                       %s[C10] APEX%s\n" "$BOLD" "$NC"
    printf "                            │\n"
    printf "            %s[C7] EXPAND·1%s ─┼─ %s[C2] CONTRACT·1%s\n" "$G" "$NC" "$R" "$NC"
    printf "                            │\n"
    printf "            %s[C5] EXPAND·2%s ─┼─ %s[C4] CONTRACT·2%s\n" "$G" "$NC" "$R" "$NC"
    printf "                            │\n"
    printf "                       %s[C3] BALANCE·2%s\n" "$Y" "$NC"
    printf "                            │\n"
    printf "            %s[C8] EXPAND·3%s ─┼─ %s[C6] CONTRACT·3%s\n" "$G" "$NC" "$R" "$NC"
    printf "                            │\n"
    printf "                       %s[C1] BALANCE·3 (FOUNDATION)%s\n" "$Y" "$NC"
    printf "                            │\n"
    printf "                       %s[C9] MANIFEST%s\n\n" "$BOLD" "$NC"
    printf "${DIM}EXPAND constraints (right) say what the system PERMITS.${NC}\n"
    printf "${DIM}CONTRACT constraints (left) say what the system FORBIDS.${NC}\n"
    printf "${DIM}BALANCE constraints (center) reconcile expansion and contraction.${NC}\n"
    printf "${DIM}APEX is the architectural intent; MANIFEST is the empirical check.${NC}\n\n"
    printf "${DIM}Reserved meta-slot: the hidden 11th position; currently unfilled.${NC}\n"
}

print_polarity() {
    printf "${BLUE}${BOLD}═══ EXPAND ↔ CONTRACT polarity pairs ═══${NC}\n\n"
    printf "${DIM}Every EXPAND constraint at a tier needs its CONTRACT counterpart${NC}\n"
    printf "${DIM}at the same tier. Loosening one without strengthening the other${NC}\n"
    printf "${DIM}is the canonical way to break the system.${NC}\n\n"
    for tier in 1 2 3; do
        printf "${BOLD}── Tier %s ──${NC}\n" "$tier"
        while IFS='|' read -r cid pos t pillar summary comp; do
            [ -z "$cid" ] && continue
            [ "$t" != "$tier" ] && continue
            [ "$pillar" = "center" ] && continue
            local color="$G"
            [ "$pillar" = "left" ] && color="$R"
            printf "  ${color}%s${NC}  %-13s  %s\n" "$cid" "$pos" "$summary"
        done <<< "$LATTICE_DATA"
        echo
    done
}

print_tier() {
    local tier="$1"
    printf "${BLUE}${BOLD}═══ Tier %s constraints ═══${NC}\n\n" "$tier"
    while IFS='|' read -r cid pos t pillar summary comp; do
        [ -z "$cid" ] && continue
        [ "$t" != "$tier" ] && continue
        local color="$Y"
        case "$pillar" in
            right) color="$G" ;;
            left) color="$R" ;;
        esac
        printf "  ${color}%s${NC}  %-13s  %s\n" "$cid" "$pos" "$summary"
    done <<< "$LATTICE_DATA"
}

walk_node() {
    local cid="$1"
    local line
    line=$(lookup "$cid")
    if [ -z "$line" ]; then
        printf "${R}No such constraint: %s${NC}\n" "$cid"
        printf "Valid constraints: C1 through C10, plus CM (meta-constraint). Try ${BOLD}ai-lattice.sh --diagram${NC}.\n"
        exit 1
    fi
    IFS='|' read -r _ pos tier pillar summary comp <<< "$line"

    printf "${BLUE}${BOLD}═══ %s — %s (tier %s, %s pillar) ═══${NC}\n\n" "$cid" "$pos" "$tier" "$pillar"
    printf "${CYAN}${BOLD}This constraint:${NC} %s\n\n" "$summary"

    # Neighbors at the same tier
    printf "${BOLD}Same-tier neighbors:${NC}\n"
    local found_neighbors=0
    while IFS='|' read -r ncid npos nt npillar nsum ncomp; do
        [ -z "$ncid" ] && continue
        [ "$ncid" = "$cid" ] && continue
        if [ "$nt" = "$tier" ]; then
            local color="$Y"
            case "$npillar" in
                right) color="$G" ;;
                left) color="$R" ;;
            esac
            printf "  ${color}%s${NC}  %-13s  %s\n" "$ncid" "$npos" "$nsum"
            found_neighbors=1
        fi
    done <<< "$LATTICE_DATA"
    if [ "$found_neighbors" -eq 0 ]; then
        printf "  ${DIM}(none — this is the sole occupant of tier %s)${NC}\n" "$tier"
    fi
    echo

    # Complement across polarity
    if [ -n "$comp" ]; then
        local comp_line
        comp_line=$(lookup "$comp")
        if [ -n "$comp_line" ]; then
            IFS='|' read -r ccid cpos _ cpillar csum _ <<< "$comp_line"
            printf "${BOLD}Polarity complement (the inverse — what would change at the opposite pillar):${NC}\n"
            local color="$G"
            [ "$cpillar" = "left" ] && color="$R"
            printf "  ${color}%s${NC}  %-13s  %s\n\n" "$ccid" "$cpos" "$csum"
            printf "  ${DIM}If you loosen %s, check whether %s still holds — its job is to keep${NC}\n" "$cid" "$ccid"
            printf "  ${DIM}%s's relaxation safe.${NC}\n\n" "$cid"
        fi
    else
        printf "${BOLD}Polarity complement:${NC} ${DIM}(none — this is a BALANCE node or APEX/MANIFEST)${NC}\n\n"
    fi

    # Dependency cascade
    local cascade
    cascade=$(cascade_for "$cid")
    if [ -n "$cascade" ]; then
        printf "${BOLD}Dependency cascade (what breaks if %s is removed):${NC}\n" "$cid"
        printf "  ${R}%s${NC}\n\n" "$cascade"
    fi

    # Suggested next thinking moves
    printf "${DIM}── Use this lattice walk:${NC}\n"
    printf "  1. ${DIM}Before changing %s, re-read its complement and tier-neighbors.${NC}\n" "$cid"
    printf "  2. ${DIM}A change to %s usually requires a matching change at the complement${NC}\n" "$cid"
    printf "     ${DIM}or weakens the system's overall coherence.${NC}\n"
    printf "  3. ${DIM}The cascade describes the worst case; verify each link is still real.${NC}\n"
}

# -----------------------------------------------------------------------------
# Dispatch
# -----------------------------------------------------------------------------
if [ $# -eq 0 ]; then
    printf "${BOLD}Usage:${NC}\n"
    printf "  ai-lattice.sh <Cn>          # walk the lattice from constraint Cn\n"
    printf "  ai-lattice.sh --diagram     # print the full lattice topology\n"
    printf "  ai-lattice.sh --polarity    # show all EXPAND↔CONTRACT pairs\n"
    printf "  ai-lattice.sh --tier <N>    # show all constraints at tier N\n\n"
    printf "Examples:\n"
    printf "  ai-lattice.sh C5            # find C5's neighbors, complement, cascade\n"
    printf "  ai-lattice.sh --polarity    # see the three EXPAND/CONTRACT pairs\n"
    exit 0
fi

case "${1:-}" in
    --diagram|-d)
        print_diagram ;;
    --polarity|-p)
        print_polarity ;;
    --tier|-t)
        [ -z "${2:-}" ] && { printf "${R}--tier requires a number (0-4)${NC}\n"; exit 1; }
        print_tier "$2" ;;
    --help|-h)
        sed -n '2,30p' "$0" | sed 's/^# \?//' ;;
    C[0-9]|C[0-9][0-9]|CM)
        walk_node "$1" ;;
    *)
        printf "${R}Unknown argument: %s${NC}\n" "$1"
        printf "Try ${BOLD}ai-lattice.sh${NC} for usage.\n"
        exit 1 ;;
esac
