#!/bin/bash
# =============================================================================
# scripts/ai-sanctum.sh — the Polaris Sanctum (v8.19)
#
# The protocol for agent-operator strategic consultation. When the Architect
# identifies a move that crosses a defined weight threshold (risk class,
# scope, structural impact), the agent does not casually present it in chat.
# The agent enters the Sanctum: writes a structured document, presents it
# under a defined form, records VANTA's response persistently, and only
# then executes.
#
# WHAT the Sanctum is lives in meta/sanctum-protocol.md (full spec + triggers
# + anti-patterns + lineage).
#
# HOW to use the Sanctum: this script.
#
# Usage:
#     ai-sanctum.sh open <topic>                        # start a new session
#     ai-sanctum.sh close <topic> --decision "..." --outcome "..."
#     ai-sanctum.sh list                                # all sessions
#     ai-sanctum.sh search <query>                      # find decisions by topic (v9.09)
#     ai-sanctum.sh open --strict                       # refuse if prep is missing
#     ai-sanctum.sh --voice                             # print the protocol spec
#     ai-sanctum.sh --help                              # short help
#
# Entry triggers (see meta/sanctum-protocol.md §"When to enter"):
#     - MEDIUM- or HIGH-risk propose-and-wait
#     - cross-arc decisions
#     - structural changes to the cognitive layer
#     - architectural-soul reframes
#     - pre-implementation alignment audits
#     - substrate-layer additions
#
# Routine LOW-risk work does NOT trigger the Sanctum.
# =============================================================================

set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
DATE_STAMP=$(date '+%Y-%m-%d')

if [ -t 1 ]; then
    BOLD="\033[1m"; G="\033[0;32m"; Y="\033[0;33m"; R="\033[0;31m"; CYAN="\033[0;36m"
    DIM="\033[2m"; NC="\033[0m"
else
    BOLD=""; G=""; Y=""; R=""; DIM=""; NC=""; CYAN=""
fi

SANCTUM_DIR="$ROOT/sanctum"
INDEX_FILE="$ROOT/meta/sanctum-index.md"

# -----------------------------------------------------------------------------
# Help / voice
# -----------------------------------------------------------------------------

print_help() {
    cat <<'EOF'
ai-sanctum.sh — the Polaris Sanctum (strategic-consultation protocol)

  open <topic> [--strict]
      Start a new Sanctum session. Creates sanctum/YYYY-MM-DD-<topic>.md
      from the template. With --strict, refuses to open if no matching
      proposal exists in proposals/ AND no recent Architect brief.

  close <topic> --decision "..." --outcome "..."
      Record VANTA's decision and the post-execution outcome. Updates
      meta/sanctum-index.md.

  list
      Show open sessions (no §VI Decision) and recent closed sessions.

  --voice
      Print meta/sanctum-protocol.md (the full protocol spec).

The Sanctum is reserved for MEDIUM/HIGH-risk strategic moments. Routine
LOW-risk work proceeds without a Sanctum. See triggers in
meta/sanctum-protocol.md.
EOF
}

print_voice() {
    if [ -f "$ROOT/meta/sanctum-protocol.md" ]; then
        cat "$ROOT/meta/sanctum-protocol.md"
    else
        printf "${R}meta/sanctum-protocol.md not found${NC}\n" >&2
        exit 1
    fi
}

# -----------------------------------------------------------------------------
# Slug helper
# -----------------------------------------------------------------------------

slugify() {
    echo "$1" | tr '[:upper:]' '[:lower:]' | sed -E 's/[^a-z0-9-]+/-/g; s/^-+//; s/-+$//'
}

# -----------------------------------------------------------------------------
# open
# -----------------------------------------------------------------------------

cmd_open() {
    local topic="$1"
    local strict="${2:-}"
    local structural="${3:-}"

    if [ -z "$topic" ]; then
        printf "${R}usage:${NC} ai-sanctum.sh open <topic> [--strict] [--structural]\n" >&2
        exit 2
    fi

    mkdir -p "$SANCTUM_DIR"
    local slug
    slug=$(slugify "$topic")
    local target="$SANCTUM_DIR/${DATE_STAMP}-${slug}.md"

    if [ -f "$target" ]; then
        printf "${Y}Sanctum session already exists:${NC} %s\n" "$target" >&2
        printf "${DIM}If you meant to reopen, edit the file. If a new session, change the topic.${NC}\n" >&2
        exit 3
    fi

    # Preparation check. Two paths are accepted:
    #   (a) standard:    proposals/<slug>*.md exists AND a today-dated
    #                    journal entry mentions "architect" (the brief
    #                    that surfaced this move).
    #   (b) structural:  caller passes --structural to declare "this is
    #                    a cognitive-layer change with no proposal; the
    #                    audit is in chat / in the protocol spec itself."
    #                    Skips the proposal check but still wants a
    #                    today-dated journal trace.
    local prep_warnings=""
    local proposal_match=""
    if [ "$structural" != "--structural" ]; then
        proposal_match=$(find "$ROOT/proposals" -maxdepth 1 -name "*${slug}*.md" 2>/dev/null | head -1)
        if [ -z "$proposal_match" ]; then
            prep_warnings="${prep_warnings}- No proposal at proposals/*${slug}*.md (use --structural for cognitive-layer changes)\n"
        fi
    fi

    # Brief-recency check uses journal content, not file mtime — mtime is
    # fragile across clock skew and system sleep. A today-dated journal
    # file containing "architect" is the signal we want.
    local recent_brief=""
    local today_journal="$ROOT/journal/${DATE_STAMP}.md"
    if [ -f "$today_journal" ] && grep -qiE 'architect|arch-[0-9]{4}' "$today_journal"; then
        recent_brief="$today_journal"
    fi
    if [ -z "$recent_brief" ]; then
        prep_warnings="${prep_warnings}- Today's journal (${DATE_STAMP}.md) has no architect reference\n"
    fi

    if [ -n "$prep_warnings" ]; then
        printf "${Y}Sanctum preparation incomplete:${NC}\n"
        printf "%b" "$prep_warnings"
        if [ "$strict" = "--strict" ]; then
            printf "${R}--strict mode: refusing to open without preparation${NC}\n" >&2
            exit 4
        else
            printf "${DIM}Proceeding anyway. The session document will note the gap.${NC}\n"
        fi
    fi

    cat > "$target" <<EOF
# Sanctum: ${topic}

**Date:** ${DATE_STAMP}
**Petitioner:** agent (Claude, Opus 4.7)
**Principal:** VANTA
**Trigger:** (fill in: MEDIUM-risk propose-and-wait / cross-arc / structural / etc.)
**Risk class:** (LOW / MEDIUM / HIGH)
**Status:** OPEN
**Architect brief ID:** (fill in the arch-YYYY-MM-DD-NNN suggestion ID that surfaced this move, or "n/a — structural" for cognitive-layer changes)

---

## I. The Matter

(One sentence. What is being asked of VANTA.)

## II. Preparation

- Architect brief: $( [ -n "$recent_brief" ] && echo "$(basename "$recent_brief")" || echo "(none recent)" )
- Proposal draft: $( [ -n "$proposal_match" ] && echo "$(basename "$proposal_match")" || echo "(none — structural change, see §II body)" )
- Alignment audit: (link or describe; for structural changes, summarize the prior alignment work inline)
- Blast radius (files touched if approved): (list)
- Tests planned: (count + classes)

## III. Alternatives considered

1. (Alternative A — what it would do, why rejected)
2. (Alternative B — what it would do, why rejected)
3. (etc.)

## IV. Recommendation

(The agent's proposed move, declarative, cites the audit and the alignment with MISSION.)

## V. What's needed from VANTA

(Explicit ask. Usually "yes do <item>", "choose between A and B", or "approve N open questions" with the questions listed.)

## VI. Decision

(Filled in by VANTA. Verbatim when short. The presence of content in this section transitions the Sanctum from OPEN to DECIDED.)

## VII. Outcome

(Filled in by agent after execution. Link to journal entry, CHANGELOG version, mission marks. The presence of content here transitions the Sanctum from DECIDED to CLOSED.)
EOF

    printf "${G}Opened:${NC} %s\n" "$target"
    printf "${DIM}Edit the file to fill in §I–V, present the digest in chat, then run:${NC}\n"
    printf "${DIM}  ai-sanctum.sh close %s --decision \"...\" --outcome \"...\"${NC}\n" "$slug"
}

# -----------------------------------------------------------------------------
# close
# -----------------------------------------------------------------------------

cmd_close() {
    local topic="$1"; shift
    local decision=""
    local outcome=""
    local reject="false"

    while [ $# -gt 0 ]; do
        case "$1" in
            --decision) decision="$2"; shift 2 ;;
            --outcome)  outcome="$2";  shift 2 ;;
            --reject)   reject="true";  shift ;;
            *) printf "${R}unknown flag:${NC} %s\n" "$1" >&2; exit 2 ;;
        esac
    done

    # Two valid forms:
    #   close <topic> --decision "..." --outcome "..."           (CLOSED)
    #   close <topic> --decision "..." --reject                  (REJECTED)
    if [ -z "$decision" ]; then
        printf "${R}usage:${NC} ai-sanctum.sh close <topic> --decision \"...\" --outcome \"...\"\n" >&2
        printf "${DIM}                  or: ... --decision \"...\" --reject  (for REJECTED sessions)${NC}\n" >&2
        exit 2
    fi
    if [ "$reject" = "true" ]; then
        outcome="(none — see §VI; VANTA declined)"
    elif [ -z "$outcome" ]; then
        printf "${R}usage:${NC} pass either --outcome \"...\" or --reject\n" >&2
        exit 2
    fi
    local target_status="CLOSED"
    [ "$reject" = "true" ] && target_status="REJECTED"

    local slug
    slug=$(slugify "$topic")
    local target
    target=$(find "$SANCTUM_DIR" -maxdepth 1 -name "*${slug}*.md" 2>/dev/null | sort | tail -1)
    if [ -z "$target" ] || [ ! -f "$target" ]; then
        printf "${R}No Sanctum session matching${NC} '%s'\n" "$slug" >&2
        exit 3
    fi

    # Replace §VI and §VII placeholders.
    local tmp="${target}.tmp"
    python3 - "$target" "$tmp" "$decision" "$outcome" <<'PY'
import sys
src, dst, decision, outcome = sys.argv[1:]
with open(src) as f:
    content = f.read()
import re
content = re.sub(
    r"(## VI\. Decision\n\n).*?(\n\n## VII\. Outcome\n\n).*?$",
    lambda m: f"{m.group(1)}{decision.strip()}{m.group(2)}{outcome.strip()}\n",
    content, flags=re.DOTALL)
content = content.replace("**Status:** OPEN", "**Status:** CLOSED")
with open(dst, 'w') as f:
    f.write(content)
PY
    mv "$tmp" "$target"

    # Update the Status: line to the target terminal state (CLOSED or REJECTED).
    # The python substitution above already set CLOSED; if the target is
    # REJECTED, fix it.
    if [ "$target_status" = "REJECTED" ]; then
        sed -i.bak 's/^\*\*Status:\*\* CLOSED$/**Status:** REJECTED/' "$target" && rm -f "${target}.bak"
    fi

    # Append to index.
    mkdir -p "$(dirname "$INDEX_FILE")"
    if [ ! -f "$INDEX_FILE" ]; then
        cat > "$INDEX_FILE" <<'EOF'
# meta/sanctum-index.md — chronological index of Sanctum sessions

Maintained by `scripts/ai-sanctum.sh close`. Newest first.

EOF
    fi
    # Insert the new entry after the heading + intro (top of list).
    local one_liner_decision
    one_liner_decision=$(echo "$decision" | head -1 | cut -c1-80)
    python3 - "$INDEX_FILE" "$DATE_STAMP" "$(basename "$target")" "$topic" "$one_liner_decision" <<'PY'
import sys
path, date, fname, topic, decision = sys.argv[1:]
with open(path) as f:
    lines = f.readlines()
# Insert immediately after the first --- separator (which closes the intro
# block in the index template). Falls back to appending if no --- exists.
new_entry = f"- **{date}** — [{topic}](../sanctum/{fname}) — {decision}\n"
out, inserted = [], False
for i, ln in enumerate(lines):
    out.append(ln)
    if not inserted and ln.strip() == "---":
        # Skip the blank line after --- and then insert.
        if i + 1 < len(lines) and lines[i + 1].strip() == "":
            out.append(lines[i + 1])
            # Skip ahead past the blank we just appended.
            lines[i + 1] = "__SKIP__"
        out.append(new_entry)
        inserted = True
out = [ln for ln in out if ln != "__SKIP__"]
if not inserted:
    out.append(new_entry)
with open(path, 'w') as f:
    f.writelines(out)
PY

    printf "${G}%s:${NC} %s\n" "$target_status" "$target"
    printf "${G}Indexed:${NC} %s\n" "$INDEX_FILE"
}

# -----------------------------------------------------------------------------
# list
# -----------------------------------------------------------------------------

cmd_list() {
    if [ ! -d "$SANCTUM_DIR" ] || [ -z "$(ls -A "$SANCTUM_DIR" 2>/dev/null)" ]; then
        printf "${DIM}No Sanctum sessions yet.${NC}\n"
        return 0
    fi

    printf "${BOLD}Open sessions (no §VI Decision):${NC}\n"
    local found_open=0
    for f in "$SANCTUM_DIR"/*.md; do
        [ -f "$f" ] || continue
        if grep -q '^\*\*Status:\*\* OPEN' "$f"; then
            printf "  %s\n" "$(basename "$f")"
            found_open=1
        fi
    done
    [ "$found_open" = "0" ] && printf "  ${DIM}(none)${NC}\n"

    printf "\n${BOLD}Recent closed sessions:${NC}\n"
    for f in $(ls -t "$SANCTUM_DIR"/*.md 2>/dev/null | head -10); do
        if grep -q '^\*\*Status:\*\* CLOSED' "$f"; then
            local matter
            matter=$(grep -A 2 "^## I\. The Matter" "$f" | tail -1 | sed 's/^[ \t]*//' | head -c 80)
            printf "  ${G}%s${NC} — %s\n" "$(basename "$f")" "$matter"
        fi
    done

    printf "\n${BOLD}Recent rejected sessions:${NC}\n"
    local found_rejected=0
    for f in $(ls -t "$SANCTUM_DIR"/*.md 2>/dev/null | head -10); do
        if grep -q '^\*\*Status:\*\* REJECTED' "$f"; then
            local matter
            matter=$(grep -A 2 "^## I\. The Matter" "$f" | tail -1 | sed 's/^[ \t]*//' | head -c 80)
            printf "  ${Y}%s${NC} — %s\n" "$(basename "$f")" "$matter"
            found_rejected=1
        fi
    done
    [ "$found_rejected" = "0" ] && printf "  ${DIM}(none)${NC}\n"
}

# -----------------------------------------------------------------------------
# Dispatch
# -----------------------------------------------------------------------------

case "${1:-}" in
    open)
        shift
        # Collect topic + optional flags in any order
        topic=""
        strict_flag=""
        structural_flag=""
        while [ $# -gt 0 ]; do
            case "$1" in
                --strict)     strict_flag="--strict";     shift ;;
                --structural) structural_flag="--structural"; shift ;;
                *) if [ -z "$topic" ]; then topic="$1"; else
                       printf "${R}unknown arg:${NC} %s\n" "$1" >&2; exit 2
                   fi; shift ;;
            esac
        done
        if [ -z "$topic" ]; then
            printf "${R}usage:${NC} ai-sanctum.sh open <topic> [--strict] [--structural]\n" >&2
            exit 2
        fi
        cmd_open "$topic" "$strict_flag" "$structural_flag"
        ;;
    close)
        shift
        cmd_close "$@"
        ;;
    list)
        cmd_list
        ;;
    search)
        # v9.09 / F — find decisions by topic.
        # Searches: filename slug, §I (the matter), §V (decision).
        # Output ordered by relevance: slug-match > matter > decision.
        shift
        if [ $# -eq 0 ]; then
            printf "${R}usage:${NC} ai-sanctum.sh search <query>\n" >&2
            exit 2
        fi
        QUERY="$*"
        printf "${BOLD}═══ Sanctum search:${NC} %s\n\n" "$QUERY"
        # Tier 1: slug match (filename contains query)
        printf "${CYAN}── Tier 1: filename slug match ──${NC}\n"
        slug_hits=$(ls "$ROOT/sanctum"/2026-*.md 2>/dev/null \
                    | grep -i "$QUERY" || true)
        if [ -n "$slug_hits" ]; then
            echo "$slug_hits" | while read -r f; do
                base=$(basename "$f" .md)
                # Extract status
                status=$(grep -E '^\*\*Status:' "$f" | head -1 \
                         | sed 's/\*\*Status:\*\*//' | tr -d ' ' \
                         | cut -c1-30)
                printf "  %s [%s]\n" "$base" "${status:-OPEN}"
            done
        else
            printf "  ${DIM}(no slug matches)${NC}\n"
        fi
        printf "\n"
        # Tier 2: §I (the matter) match
        printf "${CYAN}── Tier 2: §I 'The Matter' body match ──${NC}\n"
        matter_hits_count=0
        for f in "$ROOT/sanctum"/2026-*.md; do
            [ ! -f "$f" ] && continue
            # Extract the §I body (between '## I.' and '## II.')
            matter=$(awk '/^## I\./{flag=1; next} /^## II\./{flag=0} flag' "$f" \
                     | grep -i "$QUERY" || true)
            if [ -n "$matter" ]; then
                # Skip if already in slug-hits
                if ! echo "$slug_hits" | grep -q "$f"; then
                    base=$(basename "$f" .md)
                    snippet=$(echo "$matter" | head -1 | cut -c1-100)
                    printf "  %s\n" "$base"
                    printf "    ${DIM}…%s…${NC}\n" "$snippet"
                    matter_hits_count=$((matter_hits_count + 1))
                fi
            fi
        done
        if [ "$matter_hits_count" -eq 0 ]; then
            printf "  ${DIM}(no matter matches)${NC}\n"
        fi
        printf "\n"
        # Tier 3: §V (decision) match
        printf "${CYAN}── Tier 3: §V 'Decision' body match ──${NC}\n"
        decision_hits_count=0
        for f in "$ROOT/sanctum"/2026-*.md; do
            [ ! -f "$f" ] && continue
            decision=$(awk '/^## V\./{flag=1; next} /^## VI\./{flag=0} flag' "$f" \
                       | grep -i "$QUERY" || true)
            if [ -n "$decision" ]; then
                if ! echo "$slug_hits" | grep -q "$f"; then
                    base=$(basename "$f" .md)
                    snippet=$(echo "$decision" | head -1 | cut -c1-100)
                    printf "  %s\n" "$base"
                    printf "    ${DIM}…%s…${NC}\n" "$snippet"
                    decision_hits_count=$((decision_hits_count + 1))
                fi
            fi
        done
        if [ "$decision_hits_count" -eq 0 ]; then
            printf "  ${DIM}(no decision matches)${NC}\n"
        fi
        printf "\n${DIM}── %s sessions searched ──${NC}\n" \
            "$(ls "$ROOT/sanctum"/2026-*.md 2>/dev/null | wc -l | tr -d ' ')"
        ;;
    --voice)
        print_voice
        ;;
    --help|-h|"")
        print_help
        ;;
    *)
        printf "${R}unknown command:${NC} %s\n" "$1" >&2
        print_help
        exit 2
        ;;
esac
