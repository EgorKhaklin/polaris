#!/bin/bash
# =============================================================================
# scripts/ai-bootstrap.sh
#
# Single-command sanity check for an AI agent (or human) starting a fresh
# session on Polaris. Verifies Postgres is up, schema is loaded, sample data
# is present, and prints the env block to copy-paste for running tests or
# the Flask app.
#
# Outputs colored, line-by-line status. Anything red or yellow has a
# specific recovery command on the next line. Designed to be readable
# under token-pressure.
#
# Usage:
#     ./scripts/ai-bootstrap.sh           # check + report
#     ./scripts/ai-bootstrap.sh --fix     # also auto-repair (start pg,
#                                         # reload schema, regenerate stress
#                                         # data) when reasonable
#     ./scripts/ai-bootstrap.sh --stress  # additionally regenerate the 2M
#                                         # synthetic stress data
# =============================================================================

set -uo pipefail

# Resolve paths relative to this script regardless of CWD.
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
SQL_DIR="$ROOT/polaris_sql"
WEB_DIR="$ROOT/polaris_web"

# ANSI colors (no-op when stdout isn't a tty)
if [ -t 1 ]; then
    R="\033[0;31m"; G="\033[0;32m"; Y="\033[0;33m"; B="\033[0;34m"
    BOLD="\033[1m"; NC="\033[0m"
else
    R=""; G=""; Y=""; B=""; BOLD=""; NC=""
fi

ok()   { printf "  ${G}OK  ${NC} %s\n" "$1"; }
warn() { printf "  ${Y}WARN${NC} %s\n" "$1"; [ $# -gt 1 ] && printf "       fix: %s\n" "$2"; }
fail() { printf "  ${R}FAIL${NC} %s\n" "$1"; [ $# -gt 1 ] && printf "       fix: %s\n" "$2"; FAIL_COUNT=$((FAIL_COUNT+1)); }

FIX_MODE=0
STRESS_MODE=0
for arg in "$@"; do
    case "$arg" in
        --fix)    FIX_MODE=1 ;;
        --stress) STRESS_MODE=1; FIX_MODE=1 ;;
        --help|-h)
            sed -n '2,30p' "$0" | sed 's/^# \?//'
            exit 0 ;;
    esac
done
FAIL_COUNT=0

printf "\n${BOLD}═══ Polaris AI Bootstrap ═══${NC}\n\n"
printf "  Root:    %s\n" "$ROOT"
printf "  Mode:    %s\n" "$([ $FIX_MODE -eq 1 ] && echo "fix" || echo "report-only")"
printf "  Date:    %s\n\n" "$(date '+%Y-%m-%d %H:%M:%S %Z')"

# -----------------------------------------------------------------------------
# 1. Project layout
# -----------------------------------------------------------------------------
printf "${BOLD}[1/6] Project layout${NC}\n"
for d in "$SQL_DIR" "$WEB_DIR" "$ROOT/scripts" "$ROOT/DEVNOTES"; do
    if [ -d "$d" ]; then ok "$(basename "$d")/"
    else fail "$(basename "$d")/" "this is not the Polaris root — cd to the right folder"
    fi
done
echo

# -----------------------------------------------------------------------------
# 2. Critical files exist
# -----------------------------------------------------------------------------
printf "${BOLD}[2/6] Critical files${NC}\n"
for f in \
    "$SQL_DIR/00_load_all.sql" \
    "$SQL_DIR/11_atlas.sql" \
    "$WEB_DIR/app.py" \
    "$WEB_DIR/security.py" \
    "$WEB_DIR/test_app.py" \
    "$WEB_DIR/static/atlas-globe.js" \
    "$ROOT/CLAUDE.md" \
    "$ROOT/docs/reference/SCALING.md" \
    ; do
    if [ -f "$f" ]; then ok "$(realpath --relative-to="$ROOT" "$f" 2>/dev/null || echo "$f")"
    else fail "missing: $f"
    fi
done
echo

# -----------------------------------------------------------------------------
# 3. PostgreSQL
# -----------------------------------------------------------------------------
printf "${BOLD}[3/6] PostgreSQL${NC}\n"
if command -v pg_ctlcluster >/dev/null 2>&1; then
    ok "pg_ctlcluster available"
elif command -v pg_ctl >/dev/null 2>&1; then
    ok "pg_ctl available"
else
    fail "Neither pg_ctlcluster nor pg_ctl found" \
         "install PostgreSQL 16+: apt install postgresql-16  (or use Docker via Polaris.command)"
fi

if [ -S /var/run/postgresql/.s.PGSQL.5432 ]; then
    ok "Postgres socket present at :5432"
else
    warn "Postgres socket not found"
    if [ $FIX_MODE -eq 1 ] && command -v pg_ctlcluster >/dev/null 2>&1; then
        printf "       starting cluster...\n"
        timeout 10 pg_ctlcluster 16 main start 2>&1 | tail -1 | sed 's/^/       /'
        sleep 3
        # Wait for recovery
        for i in $(seq 1 30); do
            if timeout 2 su postgres -c "psql -c 'SELECT 1'" >/dev/null 2>&1; then
                ok "Postgres now accepting connections (after ${i}s)"
                break
            fi
            sleep 1
        done
    else
        warn "  rerun with --fix or: pg_ctlcluster 16 main start"
    fi
fi
echo

# -----------------------------------------------------------------------------
# 4. Database state
# -----------------------------------------------------------------------------
printf "${BOLD}[4/6] Database state${NC}\n"
DB="${POLARIS_DB_NAME:-polaris_test}"
printf "  Target DB: %s (override via POLARIS_DB_NAME)\n" "$DB"

if timeout 3 su postgres -c "psql -lqt" 2>/dev/null | cut -d'|' -f1 | grep -qw "$DB"; then
    ok "Database '$DB' exists"
else
    fail "Database '$DB' missing" \
         "createdb $DB && psql -d $DB -f $SQL_DIR/00_load_all.sql"
    if [ $FIX_MODE -eq 1 ]; then
        printf "       creating + loading schema...\n"
        timeout 10 su postgres -c "createdb $DB" 2>&1 | sed 's/^/       /'
        timeout 30 su postgres -c "psql -d $DB -v ON_ERROR_STOP=1 -f $SQL_DIR/00_load_all.sql" \
            2>&1 | tail -3 | sed 's/^/       /'
    fi
fi

# Schema sanity — count tables + the 6 atlas functions
TABLE_COUNT=$(timeout 3 su postgres -c "psql -d $DB -tAc \"SELECT count(*) FROM pg_tables WHERE schemaname='public'\"" 2>/dev/null | tr -d '[:space:]')
if [ "${TABLE_COUNT:-0}" -ge 12 ]; then
    ok "Schema loaded: $TABLE_COUNT tables"
else
    fail "Schema incomplete (expected 12+ tables, got ${TABLE_COUNT:-0})" \
         "psql -d $DB -f $SQL_DIR/00_load_all.sql"
fi

ATLAS_FUNCS=$(timeout 3 su postgres -c "psql -d $DB -tAc \"SELECT count(*) FROM pg_proc WHERE proname LIKE 'atlas\\\\_%'\"" 2>/dev/null | tr -d '[:space:]')
if [ "${ATLAS_FUNCS:-0}" -ge 6 ]; then
    ok "Atlas v6 SQL functions: $ATLAS_FUNCS"
else
    fail "Atlas functions missing (expected 6, got ${ATLAS_FUNCS:-0})" \
         "psql -d $DB -f $SQL_DIR/11_atlas.sql"
fi

# Row counts
INDIVIDUAL_N=$(timeout 3 su postgres -c "psql -d $DB -tAc 'SELECT count(*) FROM Individual'" 2>/dev/null | tr -d '[:space:]')
TOKEN_N=$(timeout 3 su postgres -c "psql -d $DB -tAc 'SELECT count(*) FROM IdentityToken'" 2>/dev/null | tr -d '[:space:]')
VERIF_N=$(timeout 3 su postgres -c "psql -d $DB -tAc 'SELECT count(*) FROM VerificationEvent'" 2>/dev/null | tr -d '[:space:]')
LIFECYCLE_N=$(timeout 3 su postgres -c "psql -d $DB -tAc 'SELECT count(*) FROM TokenLifecycleEvent'" 2>/dev/null | tr -d '[:space:]')

printf "  Individuals:           %s\n" "${INDIVIDUAL_N:-?}"
printf "  IdentityTokens:        %s\n" "${TOKEN_N:-?}"
printf "  VerificationEvents:    %s\n" "${VERIF_N:-?}"
printf "  TokenLifecycleEvents:  %s\n" "${LIFECYCLE_N:-?}"

# Lockout check on the seeded admin
LOCKED=$(timeout 3 su postgres -c "psql -d $DB -tAc \"SELECT locked_until IS NOT NULL FROM AppUser WHERE username='admin'\"" 2>/dev/null | tr -d '[:space:]')
if [ "$LOCKED" = "t" ]; then
    warn "admin account is LOCKED (likely from prior auth tests)" \
         "psql -d $DB -c \"UPDATE AppUser SET locked_until=NULL, failed_login_count=0\""
    if [ $FIX_MODE -eq 1 ]; then
        timeout 3 su postgres -c "psql -d $DB -c \"UPDATE AppUser SET locked_until=NULL, failed_login_count=0\"" >/dev/null 2>&1 \
            && ok "admin unlocked"
    fi
else
    ok "admin account not locked"
fi
echo

# -----------------------------------------------------------------------------
# 5. Stress data (optional)
# -----------------------------------------------------------------------------
printf "${BOLD}[5/6] Stress test data (optional)${NC}\n"
if [ "${VERIF_N:-0}" -ge 1000000 ]; then
    ok "VerificationEvent has ${VERIF_N} rows — stress data present"
elif [ "${VERIF_N:-0}" -ge 8 ]; then
    warn "Only sample-size data (${VERIF_N} verifications)" \
         "rerun with --stress to generate 2M synthetic events for benchmarking"
    if [ $STRESS_MODE -eq 1 ]; then
        printf "       generating 2M synthetic events (~90s)...\n"
        timeout 200 su postgres -c "psql -d $DB -v ON_ERROR_STOP=1 -f $SQL_DIR/_stress_seed.sql" \
            2>&1 | tail -3 | sed 's/^/       /'
    fi
else
    fail "VerificationEvent count = ${VERIF_N:-?} — sample data missing" \
         "psql -d $DB -f $SQL_DIR/04_data.sql"
fi
echo

# -----------------------------------------------------------------------------
# 6. Test runner readiness
# -----------------------------------------------------------------------------
printf "${BOLD}[6/6] Test runner readiness${NC}\n"
if command -v python3 >/dev/null 2>&1; then
    PYV=$(python3 --version 2>&1 | awk '{print $2}')
    ok "python3 $PYV"
else
    fail "python3 not in PATH" "apt install python3"
fi

for mod in flask psycopg2 gunicorn werkzeug webauthn; do
    if python3 -c "import $mod" 2>/dev/null; then
        ok "python: $mod importable"
    else
        warn "python: $mod NOT importable" \
             "pip3 install --break-system-packages $mod"
    fi
done
echo

# v8.99: Verify v8.95+v8.97 schema migrations have been applied. The
# schema_version registry lands via 00_load_all.sql, but the migrations
# themselves require an explicit polaris-migrate.sh --up.
SCHEMA_VERSION_TABLE=$(timeout 3 su postgres -c "psql -d $DB -tAc \"SELECT 1 FROM information_schema.tables WHERE table_name='schema_version'\"" 2>/dev/null | tr -d '[:space:]')
if [ "$SCHEMA_VERSION_TABLE" = "1" ]; then
    APPLIED_COUNT=$(timeout 3 su postgres -c "psql -d $DB -tAc \"SELECT count(*) FROM (SELECT name FROM schema_version sv1 WHERE event_type='applied' AND NOT EXISTS (SELECT 1 FROM schema_version sv2 WHERE sv2.name=sv1.name AND sv2.event_type='reverted' AND sv2.occurred_at>sv1.occurred_at)) t\"" 2>/dev/null | tr -d '[:space:]')
    ON_DISK_COUNT=$(ls "$ROOT/polaris_sql/migrations/"*.up.sql 2>/dev/null | wc -l | tr -d '[:space:]')
    if [ "${APPLIED_COUNT:-0}" -ge "${ON_DISK_COUNT:-0}" ]; then
        ok "schema migrations: $APPLIED_COUNT applied (matches ${ON_DISK_COUNT} on disk)"
    else
        warn "schema migrations: $APPLIED_COUNT applied / $ON_DISK_COUNT on disk — pending" \
             "POLARIS_DB_NAME=$DB POLARIS_DB_USER=postgres $ROOT/scripts/polaris-migrate.sh --up"
        if [ $FIX_MODE -eq 1 ]; then
            POLARIS_DB_NAME=$DB POLARIS_DB_USER=postgres POLARIS_DB_HOST=localhost \
                "$ROOT/scripts/polaris-migrate.sh" --up >/dev/null 2>&1 \
                && ok "migrations applied"
        fi
    fi
else
    warn "schema_version registry missing — re-run 00_load_all.sql" \
         "su postgres -c 'psql -d $DB -f $SQL_DIR/00_load_all.sql'"
fi
echo

# -----------------------------------------------------------------------------
# Summary + env block
# -----------------------------------------------------------------------------
if [ $FAIL_COUNT -eq 0 ]; then
    printf "${BOLD}${G}═══ READY ═══${NC}\n\n"
    printf "Copy-paste this env block before running tests or the app:\n\n"
    printf "${B}"
    cat <<EOF
unset PGPORT
export POLARIS_DB_HOST=localhost
export POLARIS_DB_NAME=$DB
export POLARIS_DB_USER=polaris_app
export POLARIS_DB_PASSWORD=polaris_dev_password
export POLARIS_PORT=2222
export POLARIS_SECRET_KEY=test-secret
export POLARIS_STATE_DIR=/tmp/polaris-state
# v8.99: required on macOS — hashlib.scrypt forks into objc-loaded
# parent and crashes mid-login without this. Harmless on Linux.
export OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES
mkdir -p \$POLARIS_STATE_DIR
EOF
    printf "${NC}\n"
    printf "Then:\n"
    printf "  ${BOLD}cd $WEB_DIR${NC}\n"
    printf "  ${BOLD}python3 test_app.py${NC}                  # run all 118 tests\n"
    printf "  ${BOLD}gunicorn --config gunicorn.conf.py app:app${NC}     # start the app\n"
    printf "\n"
    exit 0
else
    printf "${BOLD}${R}═══ ${FAIL_COUNT} FAILURE(S) ═══${NC}\n\n"
    printf "Each failure printed its specific fix command. Address them in\n"
    printf "order, then re-run this script. Or run with ${BOLD}--fix${NC} to attempt\n"
    printf "automatic repairs.\n\n"
    exit 1
fi
