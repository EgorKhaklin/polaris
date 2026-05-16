#!/bin/bash
# =============================================================================
# scripts/ai-impact.sh — given a file, list everything that references it (v8.6)
#
# The mirror image of ai-link-check.sh. ai-link-check answers "are my
# outgoing references valid?" This script answers "if I rename or move
# THIS file, what else breaks?"
#
# Use cases:
#   - Before renaming a script: who calls it?
#   - Before moving a doc: where is it linked?
#   - Before changing a function: which other files import / reference it?
#   - Before deprecating a SQL function: where is it queried?
#
# Usage:
#     scripts/ai-impact.sh polaris_sql/01_schema.sql
#     scripts/ai-impact.sh CryptographicAlgorithm   # bare-name search
#     scripts/ai-impact.sh atlas_clusters_verifications
# =============================================================================

set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
cd "$ROOT"

if [ -t 1 ]; then
    BOLD="\033[1m"; G="\033[0;32m"; Y="\033[0;33m"; CYAN="\033[0;36m"
    DIM="\033[2m"; NC="\033[0m"
else
    BOLD=""; G=""; Y=""; CYAN=""; DIM=""; NC=""
fi

TARGET="${1:-}"
if [ -z "$TARGET" ]; then
    printf "Usage: ai-impact.sh <file-or-symbol>\n"
    printf "Examples:\n"
    printf "  ai-impact.sh polaris_sql/01_schema.sql\n"
    printf "  ai-impact.sh atlas_clusters_verifications\n"
    printf "  ai-impact.sh GenomicAnchor\n"
    exit 1
fi

# -----------------------------------------------------------------------------
# Resolve target into search terms.
#   - If it's an existing file path, search for the basename (best signal)
#     and the relative path (catches link-style references)
#   - If it's a symbol/function name, search for it as a whole word
# -----------------------------------------------------------------------------
TERMS=()
if [ -f "$TARGET" ]; then
    base=$(basename "$TARGET")
    rel=$(python3 -c "import os, sys; print(os.path.relpath(sys.argv[1], sys.argv[2]))" \
        "$TARGET" "$ROOT")
    TERMS+=("$base" "$rel")
    printf "${BOLD}Impact analysis: %s${NC}\n" "$rel"
else
    TERMS+=("$TARGET")
    printf "${BOLD}Impact analysis: %s${NC}\n" "$TARGET"
fi
printf "${DIM}(searching for references in code, docs, and tests)${NC}\n\n"

# -----------------------------------------------------------------------------
# Search each term across relevant file types, excluding noise.
# -----------------------------------------------------------------------------
EXCLUDE_DIRS=(
    --exclude-dir=.git
    --exclude-dir=node_modules
    --exclude-dir=__pycache__
    --exclude-dir=venv
    --exclude-dir=journal              # historical, not impact
)
INCLUDES=(
    --include='*.md'
    --include='*.py'
    --include='*.sh'
    --include='*.sql'
    --include='*.html'
    --include='*.js'
    --include='*.css'
    --include='*.json'
)

# Track unique referencing files
SEEN=$(mktemp)
trap 'rm -f "$SEEN"' EXIT

for term in "${TERMS[@]}"; do
    # Use grep -F (fixed-string) to be safe with regex-special chars
    while IFS=: read -r path lineno line; do
        # Don't include the target file itself
        if [ -f "$TARGET" ] && [ "$(realpath "$path" 2>/dev/null)" = "$(realpath "$TARGET" 2>/dev/null)" ]; then
            continue
        fi
        # Skip CHANGELOG.md (historical references) for cleaner output
        if [ "$(basename "$path")" = "CHANGELOG.md" ] && [ "$(dirname "$path")" = "." ]; then
            continue
        fi
        if ! grep -qFx "$path" "$SEEN" 2>/dev/null; then
            echo "$path" >> "$SEEN"
        fi
        # Print one line per hit, trimmed
        trimmed=$(echo "$line" | sed 's/^[[:space:]]*//' | head -c 90)
        printf "  ${CYAN}%s:%s${NC}  %s\n" "$path" "$lineno" "$trimmed"
    done < <(grep -rnF "${EXCLUDE_DIRS[@]}" "${INCLUDES[@]}" "$term" 2>/dev/null)
done

n_files=$(wc -l < "$SEEN" | tr -d ' ')
printf "\n${BOLD}Summary${NC}\n"
if [ "$n_files" -eq 0 ]; then
    printf "  ${G}No references${NC} — this file/symbol appears unused.\n"
    if [ -f "$TARGET" ]; then
        printf "  ${DIM}(safe to rename or delete with no cross-file impact)${NC}\n"
    fi
else
    printf "  ${Y}%s files reference this${NC}\n" "$n_files"
    if [ -f "$TARGET" ]; then
        printf "  ${DIM}(rename / move requires updating each)${NC}\n"
    fi
fi
