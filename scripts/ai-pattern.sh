#!/bin/bash
# =============================================================================
# scripts/ai-pattern.sh
#
# Given a problem statement, surface the matching software-work pattern
# from the 22-element pattern catalog. For each match, print three things:
#
#   1. The PATTERN     — which shape this is
#   2. The SHADOW      — the predicted failure mode for this shape
#   3. The COMPLEMENT  — the inverse pattern that surfaces by re-framing
#
# The three-view return forces non-linear reasoning. A linear match
# ("you're in collapse mode") is useful but flat. Adding the shadow
# primes failure-mode hunting; adding the complement primes "what would
# this look like if I were on the other side of it" — the cheapest way
# to surface non-obvious failure modes.
#
# The pattern catalog is a closed set of 22 software-work shapes. See
# meta/structural-constants.json::PATTERN_CATALOG_SIZE for why 22 and
# meta/lineage.md for the etymology if curious.
#
# Usage:
#     ai-pattern.sh "<problem>"            # best match + shadow + complement
#     ai-pattern.sh --compose "<problem>"  # top-3 matches (multi-pattern compose)
#     ai-pattern.sh --list                 # show all 22 with brief shape
#     ai-pattern.sh --random               # pull a random pattern for ideation
#     ai-pattern.sh "<problem>" --shadow   # detail the failure mode only
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
# The 22-element pattern catalog
# Format: number|name|shape|shadow|complement-number|keywords
# Complement = the inverse pattern (re-frame from the other side)
# -----------------------------------------------------------------------------
read -r -d '' PATTERNS <<'EOF' || true
0|Greenfield|Beginning a new project / fresh session / unknown territory|Naive optimism: under-scoping risk; missing prior art; ignoring written warnings|21|new,start,beginning,fresh,scratch,greenfield,init,bootstrap
1|Composition|Creating something new from existing components / wiring up an integration|Tool-fixation: making the tool the goal, not the result; over-engineering the framework|13|create,build,wire,integrate,implement,construct,assemble
2|HiddenState|Hidden knowledge surfacing / debugging a non-obvious bug / race condition|Unspoken assumptions: the bug is in what you didn't think to check; gut says wrong but you proceed anyway|19|race,toctou,intermittent,flaky,heisenbug,hidden,obscure,nondeterministic
3|Foundation|Foundational creation / schema design / defining the data model|Premature commitment: the schema feels right but locks in decisions you haven't fully thought through|20|schema,model,foundation,table,structure,data
4|Authority|Authority and order / security control / access enforcement|Brittle authority: the rule is right but enforcement is at the wrong layer; bypassable|15|security,auth,role,permission,enforce,access,control,authorize
5|Convention|Tradition and convention / following the established pattern / using a known recipe|Cargo-culting: applying the recipe where it doesn't fit; treating convention as law|12|pattern,convention,standard,recipe,established,tradition,follow
6|Branchpoint|Choice between two paths / proposal vs alternative / fork in the road|False symmetry: presenting two options as equal when one is clearly better; analysis paralysis|14|choice,fork,decide,propose,alternative,either,or,decision
7|ShipPressure|Drive and momentum / shipping under deadline / pushing through obstacles|Forced victory: shipping unfinished work because you committed to the date; technical debt accrues invisibly|8|deadline,ship,deploy,push,momentum,drive,launch,release
8|Endurance|Quiet endurance / refactoring patiently / handling concurrency without panic|Brute force: solving with effort what should be solved with insight; missing the elegant decomposition|7|refactor,endure,concurrency,patient,sustain,iterate
9|Investigation|Solo investigation / reading code alone / deep focus on one problem|Bus factor: the knowledge stays in your head; nobody else can pick this up; bus-factor=1|10|investigate,debug,explore,solo,read,trace,analyze,research
10|Recurrence|Cyclical patterns / recurring incidents / what comes around|Same bug, third time: pattern wasn't documented after the first or second occurrence; doomed to repeat|9|recurring,cycle,pattern,recurring,again,repeat,incident
11|Audit|Audit and accountability / consequences for actions / things being weighed|Selective audit: enforcing on small actors, lenient on big ones; audit log is incomplete|18|audit,fair,balance,consequence,accountability,judge,review
12|Inversion|Inversion of perspective / suspending judgment / seeing it from the other side|Stuck inversion: contemplation becomes paralysis; the inversion never lands; never deciding|5|invert,suspend,contemplate,perspective,reframe,paused,delayed
13|Removal|Ending what no longer serves / removing dead code / deprecating an API|Sentimental keep: refusing to delete because you might need it; dead code accumulates and obscures live code|1|remove,delete,deprecate,end,kill,remove,sunset
14|Migration|Balance and integration / mixing old and new / migration|Forever-migration: dual-write that never completes; both systems running in parallel indefinitely|6|balance,integrate,migrate,mix,transition,blend,gradual
15|Workaround|Unhealthy attachment / shortcut that bites / addictive bad pattern|Sweet poison: the workaround works AND it's wrong; quick fix becomes permanent debt|4|workaround,hack,shortcut,quick,fix,kludge,bandaid,sticky
16|Collapse|Sudden collapse / production incident / catastrophic failure|Predictable surprise: the warning signs were there for weeks; the post-mortem will be embarrassing|17|incident,outage,collapse,crash,break,failure,emergency,prod
17|Recovery|Hope after collapse / after a major bug / clean slate post-incident|Premature optimism: declaring victory before the root cause is understood; same bug returns|16|recover,recovery,hope,after,postmortem,fresh
18|Phantom|Illusion and uncertainty / flaky tests / can't reproduce|False reading: chasing a phantom; the bug isn't where you think; the test is testing the wrong thing|11|flaky,illusion,uncertain,reproduce,phantom,intermittent,glitch
19|Clarity|Clarity and success / feature working as intended / clean ship|Too-bright glare: declaring done too soon; happy-path tested, edges not|2|feature,working,success,clear,visible,done,green
20|Reckoning|Reckoning with past decisions / refactoring legacy / paying tech debt|Total rewrite trap: scrapping rather than refactoring; throwing out working code with the ugly|3|legacy,refactor,debt,rewrite,reckoning,review,older
21|Closure|Completion / closing a chapter / ending a release|Premature closure: declaring complete when there are still 🟡 items; not opening the next loop|0|complete,done,closure,finish,end,wrap,release,ship,final
EOF

# -----------------------------------------------------------------------------
# Game-theoretic type annotation per pattern (v8.10)
# Surfaces the game-theoretic structure each shape encodes — knowing the
# game-type predicts which failure mode applies. Read alongside the shadow.
# -----------------------------------------------------------------------------
read -r -d '' GAME_TYPES <<'EOF' || true
0|Single-player exploration under uncertainty
1|Coordination game (components must agree)
2|Imperfect-information / Bayesian game
3|Commitment device (irreversible choice)
4|Principal-agent (delegation may defect)
5|Coordination equilibrium (Schelling-point following)
6|Decision under uncertainty (expected-value calculation)
7|Time-discounted preference (hyperbolic-discounting trap)
8|Repeated cooperative game (refactoring rounds)
9|Single-player search (information gathering)
10|Iterated game without memory (same mistake replayed)
11|Principal-agent monitoring (costly observation)
12|Adversarial role-switch (model from other side)
13|Commitment unwind (reversing a commitment device)
14|Two-system bridging (heterogeneous-state coordination)
15|Defection equilibrium (shortcut becomes the norm)
16|Tail-risk realization (low-prob high-impact event)
17|Repeated-game restart (rebuild reputation)
18|Information asymmetry (signal vs noise)
19|Common knowledge (all parties see the same thing)
20|Accumulated-debt unwind (deferred-commitment payoff)
21|Terminal state (game ends; new game begins)
EOF

lookup_game_type() {
    local n="$1"
    echo "$GAME_TYPES" | awk -F '|' -v n="$n" '$1 == n { print $2; exit }'
}

# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------
lookup_by_number() {
    local n="$1"
    echo "$PATTERNS" | awk -F '|' -v n="$n" '$1 == n { print; exit }'
}

list_all() {
    printf "${BLUE}${BOLD}═══ The 22-pattern catalog — Polaris software-work shapes ═══${NC}\n\n"
    printf "${DIM}Each pattern maps a recurring shape of software work to its${NC}\n"
    printf "${DIM}characteristic failure mode (the 'shadow') and its inverse pattern${NC}\n"
    printf "${DIM}(the 'complement'). Use ai-pattern to surface predicted failure${NC}\n"
    printf "${DIM}and re-framing before the work goes sideways.${NC}\n\n"
    while IFS='|' read -r num name shape shadow comp keywords; do
        [ -z "$num" ] && continue
        printf "${BOLD}%2d. %s${NC}\n" "$num" "$name"
        printf "    ${CYAN}shape:${NC}      %s\n" "$shape"
        printf "    ${BLUE}game-type:${NC}  %s\n" "$(lookup_game_type "$num")"
        printf "    ${PURPLE}shadow:${NC}     %s\n" "$shadow"
        comp_line=$(lookup_by_number "$comp")
        if [ -n "$comp_line" ]; then
            comp_name=$(echo "$comp_line" | awk -F '|' '{print $2}')
            printf "    ${G}complement:${NC} %s. %s\n\n" "$comp" "$comp_name"
        else
            printf "\n"
        fi
    done <<< "$PATTERNS"
}

random_pattern() {
    local n=$((RANDOM % 22))
    local line
    line=$(lookup_by_number "$n")
    [ -z "$line" ] && line=$(echo "$PATTERNS" | head -1)
    IFS='|' read -r num name shape shadow comp keywords <<< "$line"
    printf "${BLUE}${BOLD}═══ Random pattern: %s. %s ═══${NC}\n\n" "$num" "$name"
    printf "${CYAN}Shape:${NC}      %s\n" "$shape"
    printf "${PURPLE}Shadow:${NC}     %s\n" "$shadow"
    comp_line=$(lookup_by_number "$comp")
    if [ -n "$comp_line" ]; then
        comp_name=$(echo "$comp_line" | awk -F '|' '{print $2}')
        comp_shape=$(echo "$comp_line" | awk -F '|' '{print $3}')
        printf "${G}Complement:${NC} %s. %s — %s\n\n" "$comp" "$comp_name" "$comp_shape"
    fi
    printf "${DIM}Apply this pattern to your current work as a thought experiment:${NC}\n"
    printf "${DIM}what would the shadow predict goes wrong? Then re-frame as the complement.${NC}\n"
}

score_patterns() {
    # Emit scored list: "<score>|<num>|<name>|<shape>|<shadow>|<comp>|<keywords>"
    # for every pattern with score > 0. Used by both match_problem (top-1)
    # and compose_problem (top-K).
    local lower="$1"
    while IFS='|' read -r num name shape shadow comp keywords; do
        [ -z "$num" ] && continue
        local score=0
        for kw in $(echo "$keywords" | tr ',' ' '); do
            if echo "$lower" | grep -qw "$kw"; then
                score=$((score + 1))
            fi
            if echo "$lower" | grep -q "$kw"; then
                score=$((score + 1))
            fi
        done
        if [ "$score" -gt 0 ]; then
            echo "$score|$num|$name|$shape|$shadow|$comp|$keywords"
        fi
    done <<< "$PATTERNS" | sort -t '|' -k1 -rn
}

match_problem() {
    local problem="$1"
    local lower
    lower=$(echo "$problem" | tr '[:upper:]' '[:lower:]')

    local best_line
    best_line=$(score_patterns "$lower" | head -1)
    local best_score
    best_score=$(echo "$best_line" | cut -d'|' -f1)
    [ -z "$best_score" ] && best_score=0

    if [ "$best_score" -eq 0 ]; then
        printf "${Y}No clear pattern match for: \"%s\"${NC}\n\n" "$problem"
        printf "Possible reasons:\n"
        printf "  - The problem statement is too vague — try with more keywords\n"
        printf "  - The shape is novel and doesn't fit one of the 22 patterns\n"
        printf "  - The keywords don't match. Try ${BOLD}ai-pattern.sh --list${NC}.\n"
        printf "\nAs a fallback, here's a random pattern to consider:\n\n"
        random_pattern
        return
    fi

    IFS='|' read -r _ num name shape shadow comp keywords <<< "$best_line"
    printf "${BLUE}${BOLD}═══ Pattern match: %s. %s ═══${NC}\n" "$num" "$name"
    printf "${DIM}(match score: %s; keywords: %s)${NC}\n\n" "$best_score" "$keywords"
    printf "${CYAN}${BOLD}Problem:${NC} %s\n\n" "$problem"
    printf "${CYAN}${BOLD}Shape (what this looks like):${NC}\n  %s\n\n" "$shape"
    printf "${BLUE}${BOLD}Game-type:${NC} %s\n\n" "$(lookup_game_type "$num")"
    printf "${PURPLE}${BOLD}Shadow (predicted failure mode):${NC}\n"
    printf "  ${PURPLE}%s${NC}\n\n" "$shadow"

    # Surface the complement
    comp_line=$(lookup_by_number "$comp")
    if [ -n "$comp_line" ]; then
        comp_name=$(echo "$comp_line" | awk -F '|' '{print $2}')
        comp_shape=$(echo "$comp_line" | awk -F '|' '{print $3}')
        comp_shadow=$(echo "$comp_line" | awk -F '|' '{print $4}')
        printf "${G}${BOLD}Complement (inverse re-frame): %s. %s${NC}\n" "$comp" "$comp_name"
        printf "  ${G}shape:${NC}  %s\n" "$comp_shape"
        printf "  ${G}shadow:${NC} %s\n\n" "$comp_shadow"
    fi

    printf "${DIM}── Use this three-view return:${NC}\n"
    printf "  1. The ${CYAN}shape${NC} confirms what you're doing now.\n"
    printf "  2. The ${PURPLE}shadow${NC} predicts the failure — build the detection FIRST.\n"
    printf "  3. The ${G}complement${NC} asks: what if I were on the other side of this?\n"
    printf "     Sometimes the complement reveals the move you actually need.\n"
}

compose_problem() {
    local problem="$1"
    local lower
    lower=$(echo "$problem" | tr '[:upper:]' '[:lower:]')

    local scored
    scored=$(score_patterns "$lower")

    if [ -z "$scored" ]; then
        printf "${Y}No pattern matches for: \"%s\"${NC}\n\n" "$problem"
        random_pattern
        return
    fi

    printf "${BLUE}${BOLD}═══ Multi-pattern compose — \"%s\" ═══${NC}\n\n" "$problem"
    printf "${DIM}Real situations often hit several patterns at once. Top matches:${NC}\n\n"

    local i=0
    while IFS='|' read -r score num name shape shadow comp keywords; do
        [ -z "$score" ] && continue
        i=$((i + 1))
        if [ "$i" -gt 3 ]; then break; fi
        printf "${BOLD}%d. %s. %s${NC} ${DIM}(score %s)${NC}\n" "$i" "$num" "$name" "$score"
        printf "   ${CYAN}shape:${NC}     %s\n" "$shape"
        printf "   ${BLUE}game-type:${NC} %s\n" "$(lookup_game_type "$num")"
        printf "   ${PURPLE}shadow:${NC}    %s\n" "$shadow"
        comp_line=$(lookup_by_number "$comp")
        if [ -n "$comp_line" ]; then
            comp_name=$(echo "$comp_line" | awk -F '|' '{print $2}')
            printf "   ${G}complement:${NC} %s. %s\n" "$comp" "$comp_name"
        fi
        echo
    done <<< "$scored"

    printf "${DIM}── Use the composite read:${NC}\n"
    printf "  - If the top two scores are within 1 point, the situation is genuinely\n"
    printf "    multi-pattern — both shadows apply, and the BOTH-fail mode is\n"
    printf "    sneakier than either alone (e.g. ShipPressure + Reckoning →\n"
    printf "    rushing a refactor that loses elegant decomposition AND ships debt).\n"
    printf "  - If the gap is large, the top match is dominant; the others are\n"
    printf "    background concerns to file for later.\n"
}

# -----------------------------------------------------------------------------
# Dispatch
# -----------------------------------------------------------------------------
if [ $# -eq 0 ]; then
    printf "${BOLD}Usage:${NC}\n"
    printf "  ai-pattern.sh \"<problem statement>\"\n"
    printf "  ai-pattern.sh --list      (show all 22 patterns)\n"
    printf "  ai-pattern.sh --random    (pull a random one for ideation)\n\n"
    printf "Example:\n"
    printf "  ai-pattern.sh \"intermittent test failure on CI but passes locally\"\n"
    exit 0
fi

case "${1:-}" in
    --list|-l)    list_all ;;
    --random|-r)  random_pattern ;;
    --compose|-c) shift; compose_problem "$*" ;;
    --help|-h)    sed -n '2,18p' "$0" | sed 's/^# \?//' ;;
    *)            match_problem "$*" ;;
esac
