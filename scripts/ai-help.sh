#!/bin/bash
# =============================================================================
# scripts/ai-help.sh — index of every ai-* script with one-line purpose
# (v8.6; v8.37 ai-hydra; v8.52 ai-brain-map; v8.62 ai-swarm-bloom — current count: 30 scripts)
#
# Discoverability tool. The cognitive layer accumulated 29 scripts; without
# this, the agent has to grep or open each to figure out which one does
# what. This script reads the doc-comment block at the top of each ai-*.sh
# (or test_implants.sh) and emits a sorted single-screen index.
#
# Usage:
#     scripts/ai-help.sh           # full table
#     scripts/ai-help.sh prime     # show full doc for one script
# =============================================================================

set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ -t 1 ]; then
    BOLD="\033[1m"; G="\033[0;32m"; CYAN="\033[0;36m"; DIM="\033[2m"; NC="\033[0m"
else
    BOLD=""; G=""; CYAN=""; DIM=""; NC=""
fi

QUERY="${1:-}"

# -----------------------------------------------------------------------------
# Resolve the one-liner for a script: first non-shebang non-blank doc line.
# -----------------------------------------------------------------------------
oneline() {
    local f="$1"
    awk '
        NR == 1 && /^#!/  { next }      # skip shebang
        /^# ===/          { next }      # skip rule lines
        /^#$/             { next }      # skip blank doc lines
        /^# *scripts\/ai-/{
            sub(/^# */, "")
            sub(/ —.*/, "")             # cut at em-dash separator
            sub(/ - .*/, "")
            next                         # this is the path; skip and read next
        }
        /^# / {
            sub(/^# */, "")
            print
            exit
        }
    ' "$f"
}

# -----------------------------------------------------------------------------
# v9.05 / Wave 1 / C4: Extract user-facing flags from a script's doc-comment.
# Looks for lines containing `--<word>` patterns inside the first comment
# block, deduplicates, joins with spaces. Returns empty string if none.
# -----------------------------------------------------------------------------
flags_for() {
    local f="$1"
    awk '
        BEGIN { in_doc = 1 }
        /^[^#]/ && !/^$/ { in_doc = 0; exit }
        in_doc {
            while (match($0, /--[a-zA-Z][a-zA-Z0-9-]+/)) {
                flag = substr($0, RSTART, RLENGTH)
                if (!(flag in seen)) {
                    seen[flag] = 1
                    flags[++n] = flag
                }
                $0 = substr($0, RSTART + RLENGTH)
            }
        }
        END {
            out = ""
            for (i = 1; i <= n && i <= 6; i++) {
                out = out (i > 1 ? " " : "") flags[i]
            }
            print out
        }
    ' "$f"
}

# -----------------------------------------------------------------------------
# Single-script mode — print the doc-comment block.
# -----------------------------------------------------------------------------
if [ -n "$QUERY" ]; then
    # v8.28 — prefer EXACT match (`ai-<query>.sh` or `<query>.sh`) over
    # substring. Before this, `ai-help test` returned `ai-test-counts.sh`
    # because alphabetical order placed it first in the substring scan.
    target=""
    for f in "$HERE"/ai-*.sh "$HERE"/test_implants.sh; do
        base="$(basename "$f")"
        case "$base" in
            "ai-$QUERY.sh"|"$QUERY.sh") target="$f"; break ;;
        esac
    done
    # Fallback: substring match (preserves prior behavior for partial queries).
    if [ -z "$target" ]; then
        for f in "$HERE"/ai-*.sh "$HERE"/test_implants.sh; do
            base="$(basename "$f")"
            case "$base" in
                *"$QUERY"*) target="$f"; break ;;
            esac
        done
    fi
    if [ -z "$target" ]; then
        printf "No script matches: %s\n" "$QUERY"
        exit 1
    fi
    printf "${BOLD}%s${NC}\n" "$(basename "$target")"
    sed -n '/^#!/d; /^# ===/d; /^#/p; /^[^#]/q' "$target" \
        | sed 's/^# \?//' \
        | head -40
    exit 0
fi

# -----------------------------------------------------------------------------
# Index mode — table of every script with its one-liner.
# -----------------------------------------------------------------------------
printf "${BOLD}═══ Polaris cognitive-layer scripts ═══${NC}\n\n"

# Groups (v8.10 — reorganized after 11-script Memory & introspection became unwieldy):
#   prime / mission / status / propose / bootstrap         → onboarding + planning
#   test / done / link-check / cache-bust / impact         → working + shipping
#   where / recall / journal / reflect                     → memory + journaling
#   pattern / lattice / adversary                          → cognitive lenses
#   loop-check / coherence / coverage / test-counts / meta → diagnostics
#   snapshot / context-digest / help / test_implants       → snapshots + meta

print_group() {
    local name="$1"; shift
    printf "${CYAN}── %s ──${NC}\n" "$name"
    for s in "$@"; do
        f="$HERE/$s"
        if [ ! -x "$f" ]; then
            continue
        fi
        line=$(oneline "$f" || echo "(no description)")
        printf "  ${BOLD}%-22s${NC} %s\n" "$s" "$line"
        # v9.05 / Wave 1 / C4: surface key flags inline so an agent
        # skimming the index sees them without `ai-help <script>`.
        local script_flags
        script_flags=$(flags_for "$f")
        if [ -n "$script_flags" ]; then
            printf "  ${DIM}%-22s%s${NC}\n" "" "flags: $script_flags"
        fi
    done
    printf "\n"
}

print_group "Onboarding & planning" \
    ai-prime.sh ai-mission.sh ai-status.sh ai-propose.sh ai-bootstrap.sh

print_group "Working & shipping" \
    ai-test.sh ai-done.sh ai-cache-bust.sh ai-link-check.sh ai-impact.sh

print_group "Memory & journaling" \
    ai-where.sh ai-recall.sh ai-journal.sh ai-reflect.sh

print_group "Cognitive lenses" \
    ai-pattern.sh ai-lattice.sh ai-adversary.sh

print_group "Diagnostics" \
    ai-loop-check.sh ai-coherence.sh ai-coverage.sh ai-test-counts.sh ai-meta.sh

print_group "Synthesis & reporting" \
    ai-architect.sh ai-sanctum.sh ai-hydra.sh ai-swarm-bloom.sh

print_group "Snapshots & meta" \
    ai-snapshot.sh ai-context-digest.sh ai-help.sh test_implants.sh

printf "${DIM}Run \`ai-help.sh <name>\` (e.g. \`ai-help.sh prime\`) for a single script's full doc.${NC}\n"
