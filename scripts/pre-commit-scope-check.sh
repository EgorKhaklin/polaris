#!/usr/bin/env bash
# ============================================================================
# pre-commit-scope-check.sh — mechanical scope rule
#
# v9.24 / BIG MISSION Tier 4 #13. Pre-commit hook that fails if either:
#
#   (a) narrative-mass word count exceeds core word count by more than
#       NARRATIVE_RATIO (default = current ratio + 0.1; pinned in
#       meta/scope-rule-baseline.json). Anti-Architect's "do not rely
#       on feeling the moment you cross the line" — feeling is replaced
#       by ratio.
#
#   (b) any commit touching polaris_swarm/ lacks a corresponding edit
#       to meta/ant-predicates.md. Predicate-or-no-commit rule.
#
# Narrative mass = total word count under:
#     meta/ + DEVNOTES/ + journal/ + sanctum/ + proposals/
# Core mass = total word count under:
#     polaris_sql/ + polaris_web/ + polaris_hydra/ + polaris_swarm/
#     + polaris_foresight/ + polaris_cli/ + polaris_zk/ + scripts/
#
# Refusing to ship is the only meaningful enforcement; warnings would
# decay into background noise.
#
# Usage (manual):
#     ./scripts/pre-commit-scope-check.sh
#     ./scripts/pre-commit-scope-check.sh --check-staged   (git only)
#     ./scripts/pre-commit-scope-check.sh --rebase-baseline (after intentional shift)
#
# Hooked from .pre-commit-config.yaml as a `local` repo entry.
#
# Override (LAST RESORT — leaves an audit-trail line):
#     POLARIS_ALLOW_SCOPE_OVERRUN=1 git commit ...
# ============================================================================

set -uo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"
POLARIS_ROOT="$(cd -- "${SCRIPT_DIR}/.." &> /dev/null && pwd)"
BASELINE_FILE="${POLARIS_ROOT}/meta/scope-rule-baseline.json"

NARRATIVE_DIRS=(meta DEVNOTES journal sanctum proposals)
CORE_DIRS=(polaris_sql polaris_web polaris_hydra polaris_swarm
           polaris_foresight polaris_cli polaris_zk scripts)

# Count words in a directory tree (text files only)
count_words() {
    local dir="$1"
    if [[ ! -d "${POLARIS_ROOT}/${dir}" ]]; then
        echo 0
        return
    fi
    find "${POLARIS_ROOT}/${dir}" -type f \
        \( -name '*.md' -o -name '*.py' -o -name '*.sh' -o -name '*.sql' \
           -o -name '*.html' -o -name '*.txt' -o -name '*.toml' \
           -o -name '*.rs' -o -name '*.js' -o -name '*.css' \
           -o -name '*.json' -o -name '*.yml' -o -name '*.yaml' \) \
        -not -path '*/__pycache__/*' \
        -not -path '*/.hypothesis/*' \
        -not -path '*/node_modules/*' \
        -not -path '*/target/*' \
        -not -path '*/.git/*' \
        -not -path '*/venv*' \
        -exec wc -w {} \; 2>/dev/null \
    | awk '{sum += $1} END {print sum+0}'
}

sum_dirs() {
    local total=0
    for d in "$@"; do
        local n
        n=$(count_words "${d}")
        total=$((total + n))
    done
    echo "${total}"
}

REBASE=0
CHECK_STAGED=0
for arg in "$@"; do
    case "${arg}" in
        --rebase-baseline) REBASE=1 ;;
        --check-staged)    CHECK_STAGED=1 ;;
        --help|-h)
            sed -n '2,32p' "$0" | sed 's/^# \{0,1\}//'
            exit 0
            ;;
    esac
done

NARRATIVE_WORDS=$(sum_dirs "${NARRATIVE_DIRS[@]}")
CORE_WORDS=$(sum_dirs "${CORE_DIRS[@]}")

if [[ "${CORE_WORDS}" -eq 0 ]]; then
    echo "✗ core word count is zero — refusing to compute ratio" >&2
    exit 2
fi

# Use awk for floating-point ratio
RATIO=$(awk -v n="${NARRATIVE_WORDS}" -v c="${CORE_WORDS}" 'BEGIN {printf "%.3f", n/c}')

# Rebase baseline mode: write current ratio + 0.10 headroom
if [[ "${REBASE}" -eq 1 ]]; then
    HEADROOM=$(awk -v r="${RATIO}" 'BEGIN {printf "%.3f", r + 0.10}')
    mkdir -p "$(dirname "${BASELINE_FILE}")"
    cat > "${BASELINE_FILE}" <<EOF
{
  "_doc": "Scope-rule baseline pinned by scripts/pre-commit-scope-check.sh --rebase-baseline. The ratio_ceiling is current narrative/core word ratio + 0.10 headroom. Future commits must keep narrative/core <= ratio_ceiling. Edit only via --rebase-baseline.",
  "rebased_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "current_ratio": ${RATIO},
  "ratio_ceiling": ${HEADROOM},
  "narrative_words": ${NARRATIVE_WORDS},
  "core_words": ${CORE_WORDS},
  "narrative_dirs": ["${NARRATIVE_DIRS[*]}"],
  "core_dirs": ["${CORE_DIRS[*]}"]
}
EOF
    echo "✓ baseline rebased: ratio=${RATIO}, ceiling=${HEADROOM}"
    echo "  wrote ${BASELINE_FILE}"
    exit 0
fi

# Read baseline ceiling
if [[ ! -f "${BASELINE_FILE}" ]]; then
    echo "✗ no baseline at ${BASELINE_FILE}" >&2
    echo "  run: $(basename "$0") --rebase-baseline" >&2
    exit 3
fi

CEILING=$(grep '"ratio_ceiling"' "${BASELINE_FILE}" \
    | awk -F: '{print $2}' | tr -d ' ,')

# Compare (awk because bash lacks float comparison)
OVERRUN=$(awk -v r="${RATIO}" -v c="${CEILING}" 'BEGIN {print (r > c) ? 1 : 0}')

# Print state
echo "pre-commit-scope-check:"
echo "  narrative words: ${NARRATIVE_WORDS}"
echo "  core words:      ${CORE_WORDS}"
echo "  current ratio:   ${RATIO}"
echo "  ceiling ratio:   ${CEILING}"

if [[ "${OVERRUN}" -eq 1 ]]; then
    if [[ "${POLARIS_ALLOW_SCOPE_OVERRUN:-0}" = "1" ]]; then
        echo "  ! ratio ${RATIO} > ceiling ${CEILING}"
        echo "    OVERRIDDEN via POLARIS_ALLOW_SCOPE_OVERRUN=1"
        echo "    (audit-trail: narrative mass exceeds core by margin set in"
        echo "    ${BASELINE_FILE} — next commit must rebase baseline OR"
        echo "    trim narrative)"
        exit 0
    else
        echo "  ✗ ratio ${RATIO} > ceiling ${CEILING}"
        echo "    narrative mass has grown faster than core mass."
        echo "    Either:"
        echo "      (a) trim narrative (CHANGELOG/CLAUDE.md/etc.) before commit"
        echo "      (b) add core mass (real code) before commit"
        echo "      (c) rebase baseline: $(basename "$0") --rebase-baseline"
        echo "          (use ONLY when the narrative growth is intentional"
        echo "          and approved per Sanctum)"
        echo "      (d) one-shot override: POLARIS_ALLOW_SCOPE_OVERRUN=1"
        exit 1
    fi
fi

# Predicate-or-no-commit rule: if --check-staged and swarm files staged,
# require meta/ant-predicates.md is also staged
if [[ "${CHECK_STAGED}" -eq 1 ]]; then
    if command -v git >/dev/null 2>&1 && [[ -d "${POLARIS_ROOT}/.git" ]]; then
        SWARM_STAGED=$(git -C "${POLARIS_ROOT}" diff --cached --name-only \
            | grep -E '^polaris_swarm/' | wc -l | tr -d ' ')
        if [[ "${SWARM_STAGED}" -gt 0 ]]; then
            PREDICATES_STAGED=$(git -C "${POLARIS_ROOT}" diff --cached --name-only \
                | grep -c 'meta/ant-predicates.md' || true)
            if [[ "${PREDICATES_STAGED}" -eq 0 ]]; then
                echo "  ✗ ${SWARM_STAGED} polaris_swarm/ file(s) staged but meta/ant-predicates.md not staged"
                echo "    Predicate-or-no-commit rule (BIG MISSION Sanctum 2026-05-16 T1#2):"
                echo "    any change to swarm code must include a corresponding"
                echo "    predicate update OR be a documented exception in the commit message."
                exit 1
            fi
        fi
    fi
fi

echo "  ✓ scope rule satisfied"
exit 0
