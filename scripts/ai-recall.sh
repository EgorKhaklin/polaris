#!/bin/bash
# =============================================================================
# scripts/ai-recall.sh QUERY [QUERY ...]
#
# Search the project's AI-readable knowledge corpus and return the most
# relevant snippets. The corpus:
#
#     CLAUDE.md                  — agent runbook
#     DEVNOTES/*.md              — semantic memory (concurrency, gotchas, …)
#     patterns/*.md              — pattern library (chunked recipes)
#     journal/*.md               — episodic memory (past sessions)
#     docs/reference/SCALING.md  CHANGELOG.md   — architectural prose
#
# Results are ranked: exact match > word match > nearby line context.
# Each hit shows file:line + 2 lines of context.
#
# Brain analog: directed associative recall. "Have I dealt with this
# before?" answered by searching multiple memory stores in parallel.
#
# Usage:
#     ai-recall.sh "csp violation"
#     ai-recall.sh atlas slow scaling
#     ai-recall.sh "stat -f"      # multi-word phrase
# =============================================================================

set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"

if [ $# -eq 0 ]; then
    cat <<EOF
ai-recall.sh — search the project knowledge corpus

Usage:
    ai-recall.sh QUERY [QUERY ...]

Searches across CLAUDE.md, DEVNOTES/, patterns/, journal/, docs/reference/SCALING.md,
CHANGELOG.md. Results ranked by relevance. Each hit shows file:line
plus surrounding context.

Examples:
    ai-recall.sh csp violation
    ai-recall.sh "atlas slow"
    ai-recall.sh "stat -f"
EOF
    exit 0
fi

if [ -t 1 ]; then
    BOLD="\033[1m"; CYAN="\033[0;36m"; DIM="\033[2m"; NC="\033[0m"
else
    BOLD=""; CYAN=""; DIM=""; NC=""
fi

# Build the corpus list
CORPUS=()
[ -f "$ROOT/CLAUDE.md" ] && CORPUS+=("$ROOT/CLAUDE.md")
[ -f "$ROOT/docs/reference/SCALING.md" ] && CORPUS+=("$ROOT/docs/reference/SCALING.md")
[ -f "$ROOT/CHANGELOG.md" ] && CORPUS+=("$ROOT/CHANGELOG.md")
[ -f "$ROOT/docs/operator/INSTALL.md" ] && CORPUS+=("$ROOT/docs/operator/INSTALL.md")
for d in DEVNOTES patterns journal meta; do
    if [ -d "$ROOT/$d" ]; then
        while IFS= read -r f; do CORPUS+=("$f"); done < <(find "$ROOT/$d" -name '*.md' -type f 2>/dev/null)
    fi
done

if [ ${#CORPUS[@]} -eq 0 ]; then
    echo "No corpus files found. Is this the polaris root?" >&2
    exit 1
fi

# Combine query terms — multi-word query becomes both a literal phrase
# search and an AND-of-terms search.
QUERY_PHRASE="$*"
QUERY_TERMS=("$@")

printf "${BOLD}═══ Recall: '%s' ═══${NC}\n" "$QUERY_PHRASE"
printf "${DIM}Corpus: %d files across %s${NC}\n\n" \
    "${#CORPUS[@]}" \
    "$(echo "${CORPUS[@]}" | xargs -n1 dirname | sort -u | xargs -n1 basename | tr '\n' ',' | sed 's/,$//')"

# -----------------------------------------------------------------------------
# Tier 1: exact phrase match (case-insensitive)
# -----------------------------------------------------------------------------
PHRASE_HITS=$(grep -niH -F -- "$QUERY_PHRASE" "${CORPUS[@]}" 2>/dev/null || true)
if [ -n "$PHRASE_HITS" ]; then
    printf "${BOLD}EXACT PHRASE MATCH:${NC}\n"
    echo "$PHRASE_HITS" | while IFS=: read -r FILE LINE TEXT; do
        REL=$(realpath --relative-to="$ROOT" "$FILE" 2>/dev/null || basename "$FILE")
        printf "  ${CYAN}%s:%s${NC}  %s\n" "$REL" "$LINE" "$(echo "$TEXT" | head -c 120)"
        # Show one line of surrounding context
        START=$((LINE > 0 ? LINE - 1 : 1))
        sed -n "${START},$((LINE + 1))p" "$FILE" 2>/dev/null \
            | sed "s/^/    ${DIM}|${NC} /" | head -3
        echo
    done
    PHRASE_FOUND=1
else
    PHRASE_FOUND=0
fi

# -----------------------------------------------------------------------------
# Tier 2: AND-of-terms (only if multi-word query and no exact phrase hits)
# -----------------------------------------------------------------------------
if [ ${#QUERY_TERMS[@]} -gt 1 ] && [ "$PHRASE_FOUND" -eq 0 ]; then
    printf "${BOLD}ALL-TERMS MATCH (any order):${NC}\n"
    # Build a regex that requires all terms in any order on the same line
    # via lookbehind-free composition: grep each term, intersect results.
    TMPFILE=$(mktemp)
    grep -niH -- "${QUERY_TERMS[0]}" "${CORPUS[@]}" 2>/dev/null > "$TMPFILE" || true
    for term in "${QUERY_TERMS[@]:1}"; do
        grep -i -- "$term" "$TMPFILE" > "$TMPFILE.next" 2>/dev/null || true
        mv "$TMPFILE.next" "$TMPFILE"
    done
    if [ -s "$TMPFILE" ]; then
        head -10 "$TMPFILE" | while IFS=: read -r FILE LINE TEXT; do
            REL=$(realpath --relative-to="$ROOT" "$FILE" 2>/dev/null || basename "$FILE")
            printf "  ${CYAN}%s:%s${NC}  %s\n" "$REL" "$LINE" "$(echo "$TEXT" | head -c 120)"
        done
        echo
        TERM_FOUND=1
    else
        TERM_FOUND=0
    fi
    rm -f "$TMPFILE"
else
    TERM_FOUND=0
fi

# -----------------------------------------------------------------------------
# Tier 3: any-term match (fallback)
# -----------------------------------------------------------------------------
if [ "$PHRASE_FOUND" -eq 0 ] && [ "$TERM_FOUND" -eq 0 ]; then
    printf "${BOLD}ANY-TERM MATCH (each term, separately):${NC}\n"
    for term in "${QUERY_TERMS[@]}"; do
        printf "${DIM}  …matching '%s'${NC}\n" "$term"
        grep -niH -- "$term" "${CORPUS[@]}" 2>/dev/null | head -3 | while IFS=: read -r FILE LINE TEXT; do
            REL=$(realpath --relative-to="$ROOT" "$FILE" 2>/dev/null || basename "$FILE")
            printf "    ${CYAN}%s:%s${NC}  %s\n" "$REL" "$LINE" "$(echo "$TEXT" | head -c 110)"
        done
    done
    echo
fi

# -----------------------------------------------------------------------------
# Pattern hint — if the query matches a known pattern name, surface it
# -----------------------------------------------------------------------------
if [ -d "$ROOT/patterns" ]; then
    MATCHED_PATTERNS=$(find "$ROOT/patterns" -name '*.md' -type f 2>/dev/null | while read -r p; do
        BASE=$(basename "$p" .md)
        for term in "${QUERY_TERMS[@]}"; do
            if echo "$BASE" | grep -qi -- "$term"; then
                echo "$p"
                break
            fi
        done
    done | sort -u)
    if [ -n "$MATCHED_PATTERNS" ]; then
        printf "${BOLD}MATCHING PATTERN(S):${NC}\n"
        echo "$MATCHED_PATTERNS" | while read -r p; do
            REL=$(realpath --relative-to="$ROOT" "$p" 2>/dev/null || basename "$p")
            printf "  ${CYAN}%s${NC} — read this for the full recipe\n" "$REL"
        done
        echo
    fi
fi
