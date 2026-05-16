#!/bin/bash
# =============================================================================
# scripts/ai-where.sh FILE [FILE ...]
#
# Triggered associative recall. When you're about to edit a file, this script
# surfaces the relevant DEVNOTES, patterns, and recent journal entries.
#
# Brain analog: priming. Seeing one cue activates related memories. When a
# musician sees sheet music in B-flat, the related fingerings are already
# loaded before they consciously think about them. Same idea here — when I
# open atlas-globe.js, I want docs/reference/SCALING.md and visual-feature-on-atlas.md
# already pre-loaded into context, not waiting for me to remember they exist.
#
# Usage:
#     ai-where.sh polaris_web/app.py
#     ai-where.sh polaris_sql/11_atlas.sql polaris_web/static/atlas-globe.js
#     ai-where.sh -                              # read paths from stdin
# =============================================================================

set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"

if [ -t 1 ]; then
    BOLD="\033[1m"; CYAN="\033[0;36m"; GOLD="\033[0;33m"; DIM="\033[2m"; NC="\033[0m"
else
    BOLD=""; CYAN=""; GOLD=""; DIM=""; NC=""
fi

# -----------------------------------------------------------------------------
# Mapping table: file pattern → relevant DEVNOTES + patterns + queries
#
# Format per row (separator: |):
#   FILE_REGEX | TITLE | RECOMMEND_LIST
#
# RECOMMEND_LIST is space-separated; each item is "TYPE:PATH" where TYPE
# is read|pattern|query|skim.
#   read    — open this file in full
#   skim    — scan headings only
#   pattern — apply this canonical recipe
#   query   — also run ai-recall.sh with this query string
# -----------------------------------------------------------------------------

# We use the file basename + path-prefix matching for reasonable coverage.
emit_for_file() {
    local f="$1"
    local rel
    rel=$(realpath --relative-to="$ROOT" "$f" 2>/dev/null || echo "$f")

    printf "${BOLD}── %s ──${NC}\n" "$rel"

    # Match by basename or path
    local base
    base=$(basename "$f")

    # Always include CLAUDE.md as the "you should already know this" baseline
    printf "  ${DIM}global:${NC} %sCLAUDE.md%s — agent runbook, file map, gotchas\n" "$GOLD" "$NC"

    case "$rel" in
        polaris_sql/05_procedures.sql|polaris_sql/06_triggers.sql)
            printf "  ${BOLD}read:${NC}    DEVNOTES/concurrency.md\n"
            printf "  ${BOLD}pattern:${NC} patterns/concurrency-fix.md\n"
            printf "  ${BOLD}pattern:${NC} patterns/new-uc-procedure.md ${DIM}(if adding a new use case)${NC}\n"
            printf "  ${BOLD}note:${NC}    Reload after edit: psql -d \$DB -f %s\n" "$rel"
            printf "  ${BOLD}note:${NC}    The audit trigger reads polaris.actor_agency_id, polaris.reason_code, polaris.event_lat, polaris.event_lon GUCs.\n"
            ;;

        polaris_sql/01_schema.sql)
            printf "  ${BOLD}read:${NC}    DEVNOTES/concurrency.md (partial unique index section)\n"
            printf "  ${BOLD}note:${NC}    DROP TABLE CASCADE means all data is wiped on reload\n"
            printf "  ${BOLD}note:${NC}    14 tables (12 domain + 2 auth: AppUser, AuthAuditLog)\n"
            printf "  ${BOLD}note:${NC}    After any edit, also rerun: 02_indexes.sql, 09_grants.sql\n"
            ;;

        polaris_sql/11_atlas.sql)
            printf "  ${BOLD}read:${NC}    docs/reference/SCALING.md\n"
            printf "  ${BOLD}read:${NC}    DEVNOTES/atlas-scaling.md\n"
            printf "  ${BOLD}pattern:${NC} patterns/scaling-investigation.md\n"
            printf "  ${BOLD}pattern:${NC} patterns/visual-feature-on-atlas.md\n"
            printf "  ${BOLD}note:${NC}    Functions are STABLE — no side effects. Don't add INSERT/UPDATE.\n"
            printf "  ${BOLD}note:${NC}    All endpoints have hard caps. Don't unbound a query.\n"
            printf "  ${BOLD}check:${NC}   After edit, EXPLAIN ANALYZE the changed function at 2M scale\n"
            ;;

        polaris_sql/02_indexes.sql)
            printf "  ${BOLD}read:${NC}    DEVNOTES/atlas-scaling.md (Index reference table)\n"
            printf "  ${BOLD}note:${NC}    Partial indexes (WHERE …) save space — use them when 50%%+ rows are NULL\n"
            ;;

        polaris_sql/04_data.sql|polaris_sql/_stress_seed.sql)
            printf "  ${BOLD}note:${NC}    04_data.sql TRUNCATEs everything — full reset\n"
            printf "  ${BOLD}note:${NC}    _stress_seed.sql adds 2M synthetic events; takes ~90s\n"
            printf "  ${BOLD}note:${NC}    Test runs trample data — keep stress data in a separate DB if needed\n"
            ;;

        polaris_sql/08_tests.sql)
            printf "  ${BOLD}note:${NC}    36 SQL self-tests run automatically via 00_load_all.sql\n"
            printf "  ${BOLD}note:${NC}    UC-1, UC-4, UC-5, UC-7 procedure tests live here\n"
            ;;

        polaris_web/app.py)
            printf "  ${BOLD}read:${NC}    DEVNOTES/known-gotchas.md (CSP, Jinja comment escape)\n"
            printf "  ${BOLD}pattern:${NC} patterns/add-flask-route.md\n"
            printf "  ${BOLD}pattern:${NC} patterns/add-list-page-pagination.md ${DIM}(if list returns >100 rows)${NC}\n"
            printf "  ${BOLD}note:${NC}    Routes grouped by entity (search '# ====.*=====')\n"
            printf "  ${BOLD}note:${NC}    Authenticated routes: @security.login_required\n"
            printf "  ${BOLD}note:${NC}    State-changing: + @security.require_role + @security.csrf_protect\n"
            ;;

        polaris_web/security.py)
            printf "  ${BOLD}read:${NC}    DEVNOTES/concurrency.md (atomic increment section)\n"
            printf "  ${BOLD}read:${NC}    docs/operator/SECURITY.md (full threat model)\n"
            printf "  ${BOLD}note:${NC}    CSP is 'self' — never weaken it without naming the threat\n"
            printf "  ${BOLD}note:${NC}    rate limiter is in-memory, single-process. Multi-worker = redis.\n"
            printf "  ${BOLD}note:${NC}    Tests can lock admin — run UPDATE AppUser SET locked_until=NULL after\n"
            ;;

        polaris_web/static/atlas-globe.js)
            printf "  ${BOLD}read:${NC}    docs/reference/SCALING.md\n"
            printf "  ${BOLD}read:${NC}    DEVNOTES/atlas-scaling.md\n"
            printf "  ${BOLD}pattern:${NC} patterns/visual-feature-on-atlas.md\n"
            printf "  ${BOLD}note:${NC}    renderNodes() is the d3 enter/update/exit binding\n"
            printf "  ${BOLD}note:${NC}    isVisibleByFilter() — clusters bypass; points sub-filter\n"
            printf "  ${BOLD}note:${NC}    fetchData() debounced 220ms; AbortController cancels in-flight\n"
            printf "  ${BOLD}note:${NC}    chooseGrid(zoom) maps zoom to grid degrees — DON'T tighten without testing\n"
            ;;

        polaris_web/templates/atlas.html|polaris_web/templates/dashboard.html)
            printf "  ${BOLD}read:${NC}    DEVNOTES/known-gotchas.md (Jinja {{}} in HTML comments)\n"
            printf "  ${BOLD}pattern:${NC} patterns/visual-feature-on-atlas.md\n"
            printf "  ${BOLD}note:${NC}    HUD signals use data-atlas-* attributes; JS auto-populates\n"
            printf "  ${BOLD}note:${NC}    Inline <script>...</script> is blocked by CSP. Use external .js\n"
            ;;

        polaris_web/templates/_pager.html|*tokens_list.html|*verifications_list.html)
            printf "  ${BOLD}pattern:${NC} patterns/add-list-page-pagination.md\n"
            printf "  ${BOLD}note:${NC}    {%% from \"_pager.html\" import render_pager %%} at top of template\n"
            ;;

        polaris_web/test_app.py)
            printf "  ${BOLD}read:${NC}    DEVNOTES/known-gotchas.md (admin lockout in tests)\n"
            printf "  ${BOLD}note:${NC}    setUp() calls reload_sample_data() which honors POLARIS_DB_NAME\n"
            printf "  ${BOLD}note:${NC}    ConcurrencyTests use threading; each thread needs own conn\n"
            printf "  ${BOLD}note:${NC}    For new tests, follow class-per-concern; don't dump in misc\n"
            ;;

        polaris_mac_launch.sh|Polaris.command)
            printf "  ${BOLD}read:${NC}    docs/operator/INSTALL.md\n"
            printf "  ${BOLD}note:${NC}    file_mtime() is OS-aware (BSD vs GNU stat) — don't 'simplify'\n"
            printf "  ${BOLD}note:${NC}    docker_compose_up_with_heal() auto-wipes on stale-volume\n"
            printf "  ${BOLD}note:${NC}    'doctor' subcommand = read-only; 'nuke' = full wipe\n"
            ;;

        scripts/ai-bootstrap.sh|scripts/ai-context-digest.sh|scripts/ai-*.sh)
            printf "  ${BOLD}read:${NC}    meta/cognitive-loop.md\n"
            printf "  ${BOLD}note:${NC}    These ARE the AI implants. Self-recursive: editing them needs to update meta/cognitive-loop.md\n"
            ;;

        DEVNOTES/*.md|patterns/*.md|meta/*.md|journal/*.md)
            printf "  ${BOLD}note:${NC}    This is part of the AI metacognition layer. After editing, run:\n"
            printf "  ${BOLD}check:${NC}   ai-recall.sh QUERY for some likely queries to make sure findability still works\n"
            ;;

        *)
            printf "  ${DIM}(no specific guidance for this file path)${NC}\n"
            printf "  ${BOLD}suggest:${NC} ai-recall.sh '%s' to find related notes\n" "$base"
            ;;
    esac

    # Recent journal touches mentioning this file
    if [ -d "$ROOT/journal" ]; then
        local recent
        recent=$(grep -l -F -- "$base" "$ROOT/journal"/*.md 2>/dev/null | tail -3)
        if [ -n "$recent" ]; then
            printf "  ${BOLD}journal:${NC} recent entries mention this file:\n"
            echo "$recent" | while read -r jf; do
                printf "    - %s\n" "$(realpath --relative-to="$ROOT" "$jf" 2>/dev/null)"
            done
        fi
    fi

    echo
}

# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------
if [ $# -eq 0 ]; then
    cat <<EOF
ai-where.sh — triggered context for a file you're about to edit

Usage:
    ai-where.sh polaris_web/app.py
    ai-where.sh polaris_sql/05_procedures.sql polaris_web/security.py

Outputs the relevant DEVNOTES, patterns, and journal entries for each
file. Use this BEFORE you start editing — it's cheaper to load the
context now than to rediscover it via bug.

Brain analog: priming. Walking into the kitchen reminds you you wanted
a glass of water. Opening app.py should remind you about CSP, the
route grouping convention, and the auth decorator stack.
EOF
    exit 0
fi

if [ "$1" = "-" ]; then
    while IFS= read -r f; do emit_for_file "$f"; done
else
    for f in "$@"; do emit_for_file "$f"; done
fi
