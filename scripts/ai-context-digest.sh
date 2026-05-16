#!/bin/bash
# =============================================================================
# scripts/ai-context-digest.sh
#
# Dumps a compact, scannable digest of the project's current state to stdout.
# Designed for an AI agent to read when bootstrapping a fresh session — gives
# the high-signal pieces in <200 lines so token budget stays useful for
# actual work.
#
# Sections, in order:
#   - Schema digest (table list with row counts and key columns)
#   - Stored procedures (signatures only)
#   - Atlas SQL functions (signatures only)
#   - Flask routes (path + method + auth requirement)
#   - Recent app log errors (last 20 traceback heads)
#   - Test classes + count (no per-test detail)
#   - Recently-modified files (last 10 by mtime)
#
# Usage:
#     ./scripts/ai-context-digest.sh           # everything
#     ./scripts/ai-context-digest.sh routes    # just the route table
#     ./scripts/ai-context-digest.sh schema    # just the schema digest
# =============================================================================

set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
SQL_DIR="$ROOT/polaris_sql"
WEB_DIR="$ROOT/polaris_web"
DB="${POLARIS_DB_NAME:-polaris_test}"

SECTION="${1:-all}"

if [ -t 1 ]; then
    BOLD="\033[1m"; DIM="\033[2m"; NC="\033[0m"
else
    BOLD=""; DIM=""; NC=""
fi

print_section() {
    printf "\n${BOLD}═══ %s ═══${NC}\n" "$1"
}

# -----------------------------------------------------------------------------
section_schema() {
    print_section "SCHEMA"
    if ! timeout 3 su postgres -c "psql -d $DB -c 'SELECT 1'" >/dev/null 2>&1; then
        echo "  (database '$DB' unreachable — run scripts/ai-bootstrap.sh first)"
        return
    fi
    timeout 5 su postgres -c "psql -d $DB -P pager=off" <<SQL 2>/dev/null
\pset border 1
SELECT
    c.relname AS table,
    pg_size_pretty(pg_total_relation_size(c.oid)) AS size,
    (SELECT count(*) FROM pg_attribute a WHERE a.attrelid = c.oid AND a.attnum > 0 AND NOT a.attisdropped) AS cols,
    (SELECT reltuples::bigint FROM pg_class WHERE oid = c.oid) AS est_rows
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = 'public' AND c.relkind = 'r'
ORDER BY pg_total_relation_size(c.oid) DESC;
SQL
}

# -----------------------------------------------------------------------------
section_procedures() {
    print_section "STORED PROCEDURES (UC-1 .. UC-7)"
    if ! timeout 3 su postgres -c "psql -d $DB -c 'SELECT 1'" >/dev/null 2>&1; then
        echo "  (database unreachable)"
        return
    fi
    timeout 5 su postgres -c "psql -d $DB -P pager=off" <<SQL 2>/dev/null | grep -E "^uc[0-9]" | sort
\pset format unaligned
\pset tuples_only on
SELECT proname || '(' ||
       pg_get_function_arguments(p.oid) ||
       ') -> ' || pg_get_function_result(p.oid)
FROM pg_proc p
JOIN pg_namespace n ON p.pronamespace = n.oid
WHERE n.nspname = 'public' AND proname LIKE 'uc%';
SQL
}

# -----------------------------------------------------------------------------
section_atlas() {
    print_section "ATLAS SQL FUNCTIONS (v6)"
    if ! timeout 3 su postgres -c "psql -d $DB -c 'SELECT 1'" >/dev/null 2>&1; then
        echo "  (database unreachable)"
        return
    fi
    timeout 5 su postgres -c "psql -d $DB -P pager=off" <<SQL 2>/dev/null | grep -E "^atlas_" | sort
\pset format unaligned
\pset tuples_only on
SELECT proname
FROM pg_proc p
JOIN pg_namespace n ON p.pronamespace = n.oid
WHERE n.nspname = 'public' AND proname LIKE 'atlas\_%';
SQL
}

# -----------------------------------------------------------------------------
section_routes() {
    print_section "FLASK ROUTES"
    # Portable approach: read the file in Python (which IS available)
    # rather than fight awk's match() variants across platforms.
    python3 - "$WEB_DIR/app.py" <<'PY'
import re, sys
src = open(sys.argv[1]).read()
# Each block:
#   @app.route('PATH', methods=[...])
#   @security.something
#   def NAME(args):
#
# Walk lines, accumulate decorators, emit when we hit `def `.
route = None
methods = "GET"
auth = []
for line in src.splitlines():
    stripped = line.strip()
    m = re.match(r"@app\.route\(\s*['\"]([^'\"]+)['\"](?:.*?methods\s*=\s*\[([^\]]+)\])?", stripped)
    if m:
        route = m.group(1)
        methods = (m.group(2) or "'GET'").replace("'", "").replace('"', '').replace(" ", "")
        auth = []
        continue
    m = re.match(r"@security\.(\w+)", stripped)
    if m and route:
        auth.append(m.group(1))
        continue
    m = re.match(r"def ([a-zA-Z_]\w*)\s*\(", stripped)
    if m and route:
        auth_str = ",".join(auth) if auth else "anon"
        print(f"  {route:<42} {methods:<14} {auth_str:<24} {m.group(1)}")
        route = None
        auth = []
PY
}

# -----------------------------------------------------------------------------
section_log_errors() {
    print_section "RECENT APP LOG ERRORS (last 20)"
    if [ -f /tmp/polaris_app.log ]; then
        grep -E "Traceback|Error|FAIL|^\[.*ERROR" /tmp/polaris_app.log 2>/dev/null \
            | tail -20 | sed 's/^/  /'
        if ! grep -q -E "Traceback|Error" /tmp/polaris_app.log 2>/dev/null; then
            echo "  (no errors in /tmp/polaris_app.log)"
        fi
    else
        echo "  (no app log yet)"
    fi
}

# -----------------------------------------------------------------------------
section_tests() {
    print_section "TEST CLASSES"
    grep -E "^class [A-Z][A-Za-z0-9_]+(Test|Tests)" "$WEB_DIR/test_app.py" \
        | sed -E 's/^class ([^:(]+)\(.*$/  \1/' \
        | sort
    TEST_COUNT=$(grep -cE "    def test_" "$WEB_DIR/test_app.py" 2>/dev/null || echo 0)
    echo
    echo "  Total test methods: $TEST_COUNT"
}

# -----------------------------------------------------------------------------
section_recent() {
    print_section "RECENTLY MODIFIED FILES (last 10)"
    # v8.28 — `find -printf '%T@'` is GNU-only; macOS BSD find has no -printf,
    # and BSD awk has no strftime. Probe for GNU support, fall back to BSD
    # `stat -f` + `date -r` formatting. The `head -10` upstream triggers
    # SIGPIPE on find which `pipefail` would propagate as exit 141, so the
    # whole section is wrapped in `|| true` — the truncation is the design.
    if find /dev/null -maxdepth 0 -printf '' >/dev/null 2>&1; then
        find "$ROOT" -type f \
            -not -path '*/\.*' \
            -not -path '*/__pycache__/*' \
            -not -path '*/node_modules/*' \
            -not -path '*/vendor/*' \
            -printf '%T@ %p\n' 2>/dev/null \
            | sort -rn | head -10 | awk '{
                ts = strftime("%Y-%m-%d %H:%M", $1);
                sub(/^[^ ]+ /, "");
                printf "  %s  %s\n", ts, $0;
            }' || true
    else
        find "$ROOT" -type f \
            -not -path '*/\.*' \
            -not -path '*/__pycache__/*' \
            -not -path '*/node_modules/*' \
            -not -path '*/vendor/*' \
            -exec stat -f '%m|%N' {} \; 2>/dev/null \
            | sort -rn | head -10 | while IFS='|' read -r ts path; do
                printf "  %s  %s\n" \
                    "$(date -r "$ts" '+%Y-%m-%d %H:%M' 2>/dev/null)" \
                    "$path"
            done || true
    fi
}

# -----------------------------------------------------------------------------
case "$SECTION" in
    schema)     section_schema ;;
    proc*)      section_procedures ;;
    atlas)      section_atlas ;;
    routes)     section_routes ;;
    log|errors) section_log_errors ;;
    test*)      section_tests ;;
    recent)     section_recent ;;
    all|"")
        section_schema
        section_procedures
        section_atlas
        section_routes
        section_log_errors
        section_tests
        section_recent
        ;;
    *)
        echo "Unknown section: $SECTION"
        echo "Try: schema | procedures | atlas | routes | log | tests | recent | all"
        exit 1
        ;;
esac
