#!/bin/bash
# =============================================================================
# scripts/ai-adversary.sh — game-theoretic adversary lens (v8.10)
#
# Every defense is a game against an attacker. If you don't model the
# attacker, the defense is theater. This script surfaces the explicit
# game-theoretic structure of each C1-C10 constraint (and CM):
#
#   1. DEFENDER's claim — what this constraint commits to
#   2. ATTACKER's optimal response — the best move against the defense
#   3. EQUILIBRIUM the defender is reaching for — the desired stable state
#   4. SECOND-BEST attack — if the equilibrium holds, what's next?
#   5. DEFENDER's cost — what the defense costs in cycles/latency/complexity
#   6. MECHANISM design note — what incentives this creates
#
# Companion to ai-lattice.sh. Where ai-lattice walks the structural
# topology (neighbors / complement / cascade), ai-adversary walks the
# game-theoretic topology (attacker / equilibrium / fallback attack).
#
# Game-theoretic types (Stackelberg, principal-agent, defection
# equilibrium, etc.) are surfaced explicitly. Not as decoration — each
# named type predicts a different failure mode for the defense, and the
# script tells you which.
#
# Usage:
#     ai-adversary.sh C5             # game-theoretic walk of CSP 'self'
#     ai-adversary.sh CM             # adversary model for the meta-constraint
#     ai-adversary.sh --list         # all constraints with their game-types
#     ai-adversary.sh --equilibria   # all equilibrium goals at a glance
#     ai-adversary.sh --topic "rate limiting"   # free-text → matched constraint
# =============================================================================

set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"

if [ -t 1 ]; then
    BOLD="\033[1m"; G="\033[0;32m"; Y="\033[0;33m"; R="\033[0;31m"
    DIM="\033[2m"; CYAN="\033[0;36m"; BLUE="\033[38;5;75m"
    PURPLE="\033[0;35m"; NC="\033[0m"
else
    BOLD=""; G=""; Y=""; R=""; DIM=""; CYAN=""; BLUE=""; PURPLE=""; NC=""
fi

# -----------------------------------------------------------------------------
# Adversary data table — for each constraint, the game-theoretic structure
# Format: id|game_type|defender_claim|attacker_play|equilibrium|second_best|cost|mechanism_note
# -----------------------------------------------------------------------------
read -r -d '' ADVERSARIES <<'EOF' || true
C1|Commitment device|TokenLifecycleEvent/VerificationEvent cannot be UPDATEd or DELETEd|tamper with audit history retroactively to hide an action|Tamper-evident history; any retroactive change is impossible at the trigger layer|insert false-but-plausible events; reorder via timestamp manipulation in a layer above|trigger overhead per write (~µs); storage grows monotonically|The issuer commits to a history that cannot be unwritten. Reputational/legal cost of fabricated history shifts to insertion-side, where it's auditable.
C2|Privacy by structure (vs by promise)|ZERO_KNOWLEDGE verifications cannot record a token_id|reconstruct verification graph from token_id leakage on ZK events|Privacy is uncircumventable at the trusted layer; ZK is zero-knowledge at storage|side-channel correlation via timestamp/IP/context co-occurrence — vectors NOT in token_id|CHECK constraint overhead per row (negligible); developer cognitive load|Privacy guarantee is enforced by the database, not asked of the developer. Attack surface shifts to side-channels (which property tests in redaction-proof.md cover).
C3|Stackelberg defense (defender moves first)|partial unique index uq_one_active_per_person|create two parallel identities and operate them concurrently|Uniqueness of identity at any point in time|attack via succession-collision; rapid revoke-then-issue cycles to confuse the unique window|partial-index maintenance cost; some constraint-error UX cost|Defender closes the multiplexing equilibrium before attacker can establish it. Attacker forced to single-thread their attack.
C4|TOCTOU defeat (race elimination)|UPDATE … SET failed_login_count = failed_login_count + 1 RETURNING …|brute-force concurrently to win TOCTOU race; flood N parallel attempts hoping count check trails the lockout|No race window between check and increment; the count is the lock|distributed brute force; credential stuffing across IPs|UPDATE-with-RETURNING per failed attempt (~1ms extra)|Shifts attacker from cheap parallelism to expensive serial. Lockout window becomes a real cost.
C5|Trust-boundary closure|no third-party scripts can execute; only same-origin content|XSS via a same-origin sink (operator-uploaded content reflected unescaped)|Same-origin trust boundary; trusted code only|attack the heartbeat or atlas-globe.js supply chain; compromise a static asset before it ships|some operator friction (no CDN'd scripts); occasional CSP-violation noise|Makes attacker pay the cost of finding a same-origin sink. Closes the cheap third-party-XSS path.
C6|Server-as-arbiter (untrusted client)|client cannot upgrade ZERO_KNOWLEDGE to FULL by modifying the request|client modifies disclosure header / form field before submission|Server is the source of truth for disclosure semantics|attack via context manipulation; trick the server into thinking a different context applies|server-side validation per disclosure call|Removes the "I asked nicely" attack. Server treats client input as untrusted.
C7|Governance-not-code (algorithm-as-data)|CryptographicAlgorithm table; no hardcoded algorithm choice in app code|exploit algorithm-name string handling; substitute an algorithm via a lookup attack|Algorithm choice is auditable + revocable at the data layer|attack via newly-added algorithm row before security review catches it|join overhead on every algorithm reference (negligible with index)|Algorithm choice becomes a governance decision, not a code commit. Makes algorithm migration tractable; concentrates trust in the algorithm-table-change process.
C8|Bounded-loss defense|_ATLAS_MAX_* constants bound result-set size on every /api/atlas/*|DoS via unbounded query: 6.5M cluster, deep recursion, etc.|Worker survives any single request; latency bounded|distributed-request DoS where each individual request is below the cap|max(LIMIT) overhead per query; some user friction at the cap|Shifts attacker from cheap-single-shot DoS to expensive-coordinated DoS. Plus rate limiter (R8-2) caps the latter.
C9|Empirical-over-theoretical (real-world arbitration)|ConcurrencyTests use threading.Thread, not mocks|exploit a concurrency hazard that mocks would have hidden|Production concurrency claims are empirically verified|exploit a hazard the test doesn't model (new code paths added since)|test runtime increased by ~10s for thread setup|Forces empirical truth-telling. Mock-based tests live in theory; real-thread tests live in the world.
C10|Perverse-equilibrium prevention (mechanism-design)|no MonetaryClaim table; no spending-authority field on tokens|repurpose identity tokens as a value-transfer instrument via off-system protocol|Identity layer is value-pure; programmable-money pressure cannot accrete here|build a separate value-layer ON TOP that uses Polaris verification proofs (this is the *correct* response — the boundary is load-bearing)|architectural cost: cannot serve as one-stop-shop for identity-AND-money|The hardest case in the whole system. Prevents the equilibrium where the identity layer carries monetary payoffs (inheriting all CBDC failure modes). The boundary itself is the constraint.
CM|Self-monitoring loop (canary-in-the-mine)|ai-meta.sh + test_structural_invariants.py catch drift in the cognitive layer|let the cognitive layer drift silently; refer to scripts that don't exist; claim patterns that aren't invoked|Cognitive layer's claims are auditable; no museum of past architecture|skip running ai-meta.sh; develop a habit of trusting CLAUDE.md without verification|ai-meta.sh runtime (~1s); maintenance cost of keeping the audit checks fresh|Makes cognitive-layer drift observable. The script is the canary; ignoring its output is the real attack.
EOF

# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------
lookup_adversary() {
    local cid="$1"
    echo "$ADVERSARIES" | awk -F '|' -v cid="$cid" '$1 == cid { print; exit }'
}

print_list() {
    printf "${BLUE}${BOLD}═══ Polaris adversary catalog — game-theoretic structure of each constraint ═══${NC}\n\n"
    printf "${DIM}Each constraint encodes a game. The game-type predicts which failure${NC}\n"
    printf "${DIM}mode applies if the defender's commitment isn't credible.${NC}\n\n"
    while IFS='|' read -r id game_type claim play eq second cost mech; do
        [ -z "$id" ] && continue
        printf "${BOLD}%-4s${NC} ${CYAN}%s${NC}\n" "$id" "$game_type"
        printf "      defender: %s\n" "$claim"
        printf "      attacker: %s\n\n" "$play"
    done <<< "$ADVERSARIES"
}

print_equilibria() {
    printf "${BLUE}${BOLD}═══ Equilibrium map — what each constraint is reaching for ═══${NC}\n\n"
    while IFS='|' read -r id game_type claim play eq second cost mech; do
        [ -z "$id" ] && continue
        printf "${BOLD}%-4s${NC} ${G}equilibrium:${NC} %s\n" "$id" "$eq"
    done <<< "$ADVERSARIES"
    echo
    printf "${DIM}Reading: if you change a constraint, ask whether the named equilibrium${NC}\n"
    printf "${DIM}still holds. If not, the change has cascaded into a different game.${NC}\n"
}

walk_constraint() {
    local cid="$1"
    local line
    line=$(lookup_adversary "$cid")
    if [ -z "$line" ]; then
        printf "${R}No adversary model for: %s${NC}\n" "$cid"
        printf "Valid: C1 through C10, CM. Try ${BOLD}ai-adversary.sh --list${NC}.\n"
        exit 1
    fi
    IFS='|' read -r id game_type claim play eq second cost mech <<< "$line"

    printf "${BLUE}${BOLD}═══ %s — game-theoretic walk ═══${NC}\n\n" "$id"
    printf "${CYAN}${BOLD}Game type:${NC} %s\n\n" "$game_type"

    printf "${BOLD}1. Defender's claim${NC}\n"
    printf "   %s\n\n" "$claim"

    printf "${BOLD}2. Attacker's optimal response${NC}\n"
    printf "   ${R}%s${NC}\n\n" "$play"

    printf "${BOLD}3. Equilibrium the defender is reaching for${NC}\n"
    printf "   ${G}%s${NC}\n\n" "$eq"

    printf "${BOLD}4. Second-best attack (if equilibrium holds)${NC}\n"
    printf "   ${PURPLE}%s${NC}\n\n" "$second"

    printf "${BOLD}5. Defender's cost${NC}\n"
    printf "   %s\n\n" "$cost"

    printf "${BOLD}6. Mechanism-design note${NC}\n"
    printf "   ${DIM}%s${NC}\n\n" "$mech"

    printf "${DIM}── How to use this walk:${NC}\n"
    printf "  1. ${DIM}Before changing %s, verify the game-type hasn't shifted.${NC}\n" "$id"
    printf "  2. ${DIM}The second-best attack is the threat to plan against AFTER the change.${NC}\n"
    printf "  3. ${DIM}If the equilibrium changes, the mechanism-design note may be wrong.${NC}\n"
    printf "  4. ${DIM}Pair with ${BOLD}ai-lattice.sh %s${NC} ${DIM}for the structural complement.${NC}\n" "$id"
}

match_topic() {
    local topic="$1"
    local lower
    lower=$(echo "$topic" | tr '[:upper:]' '[:lower:]')

    # Simple keyword match against the adversary text
    local best_id="" best_score=0
    while IFS='|' read -r id game_type claim play eq second cost mech; do
        [ -z "$id" ] && continue
        local combined
        combined=$(echo "$game_type $claim $play $eq $mech" | tr '[:upper:]' '[:lower:]')
        local score=0
        for kw in $lower; do
            if echo "$combined" | grep -q "$kw"; then
                score=$((score + 1))
            fi
        done
        if [ "$score" -gt "$best_score" ]; then
            best_score=$score
            best_id="$id"
        fi
    done <<< "$ADVERSARIES"

    if [ -z "$best_id" ] || [ "$best_score" -eq 0 ]; then
        printf "${Y}No constraint matches topic: \"%s\"${NC}\n" "$topic"
        printf "Try ${BOLD}ai-adversary.sh --list${NC} or pick a specific Cn.\n"
        exit 1
    fi
    printf "${DIM}Topic \"%s\" → best match: %s (score %s)${NC}\n\n" "$topic" "$best_id" "$best_score"
    walk_constraint "$best_id"
}

# -----------------------------------------------------------------------------
# Dispatch
# -----------------------------------------------------------------------------
if [ $# -eq 0 ]; then
    printf "${BOLD}Usage:${NC}\n"
    printf "  ai-adversary.sh <Cn>          # game-theoretic walk of constraint Cn (or CM)\n"
    printf "  ai-adversary.sh --list        # all constraints with their game-types\n"
    printf "  ai-adversary.sh --equilibria  # all equilibrium goals at a glance\n"
    printf "  ai-adversary.sh --topic \"…\"   # free-text → matched constraint\n\n"
    printf "Examples:\n"
    printf "  ai-adversary.sh C5            # what attacker plays against CSP 'self'?\n"
    printf "  ai-adversary.sh --equilibria  # see all 11 equilibrium goals in one view\n"
    exit 0
fi

case "${1:-}" in
    --list|-l)        print_list ;;
    --equilibria|-e)  print_equilibria ;;
    --topic|-t)       shift; match_topic "$*" ;;
    --help|-h)        sed -n '2,30p' "$0" | sed 's/^# \?//' ;;
    C[0-9]|C[0-9][0-9]|CM)  walk_constraint "$1" ;;
    *)
        printf "${R}Unknown argument: %s${NC}\n" "$1"
        printf "Try ${BOLD}ai-adversary.sh${NC} for usage.\n"
        exit 1 ;;
esac
