#!/usr/bin/env bash
# ============================================================================
# polaris-idempotency-test.sh — prove 00_load_all.sql is idempotent
#
# v9.30 / item 12. The schema header has claimed "Each file is idempotent
# (DROP IF EXISTS before CREATE)" since v6. v9.30 replaces the claim
# with a test: load the schema TWICE into a fresh DB, assert identical
# state (table count, trigger count, row count for seed data). The
# saga of inline comments about reload safety is retired by the test.
#
# Requires: psql + a postgres user that can CREATE/DROP DATABASE.
# Default DB name: polaris_idempotency_test (NEVER touches polaris or
# polaris_test).
#
# Exit codes:
#   0  idempotent (state after 2 loads == state after 1 load)
#   1  NOT idempotent — state differs between runs
#   2  precondition missing (psql / postgres unavailable)
# ============================================================================

set -uo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"
POLARIS_ROOT="$(cd -- "${SCRIPT_DIR}/.." &> /dev/null && pwd)"

DB_NAME="${POLARIS_IDEMPOTENCY_DB:-polaris_idempotency_test}"
PSQL_USER="${POLARIS_DB_USER:-postgres}"

if ! command -v psql >/dev/null 2>&1; then
    echo "INCONCLUSIVE: psql not on PATH (CI / dev box should install it)" >&2
    exit 2
fi
if ! command -v dropdb >/dev/null 2>&1 || ! command -v createdb >/dev/null 2>&1; then
    echo "INCONCLUSIVE: createdb/dropdb not on PATH" >&2
    exit 2
fi

cd "${POLARIS_ROOT}/polaris_sql"

run_load() {
    psql -U "${PSQL_USER}" -d "${DB_NAME}" \
         -v ON_ERROR_STOP=1 \
         -f 00_load_all.sql > /dev/null 2>&1
}

snapshot_state() {
    # Capture: table count + trigger count + per-table row counts of
    # seed-data tables. Output is sorted text — diff-friendly.
    psql -U "${PSQL_USER}" -d "${DB_NAME}" -At -F'|' <<'SQL'
SELECT 'table_count', count(*)::text
  FROM information_schema.tables
 WHERE table_schema = 'public';
SELECT 'trigger_count', count(*)::text
  FROM information_schema.triggers
 WHERE trigger_schema = 'public';
SELECT 'rows:' || table_name, count_estimate.cnt::text
  FROM information_schema.tables t,
       LATERAL (SELECT (xpath('/row/c/text()',
                              query_to_xml(format('SELECT count(*) AS c FROM %I',
                                                  t.table_name),
                                            true, true, '')))[1]::text::bigint AS cnt
               ) count_estimate
 WHERE t.table_schema = 'public'
 ORDER BY 1;
SQL
}

# Build fresh DB, load once, snapshot
dropdb -U "${PSQL_USER}" --if-exists "${DB_NAME}" 2>/dev/null
if ! createdb -U "${PSQL_USER}" "${DB_NAME}" 2>/dev/null; then
    echo "INCONCLUSIVE: cannot create ${DB_NAME} (need CREATEDB privilege)" >&2
    exit 2
fi

trap 'dropdb -U "${PSQL_USER}" --if-exists "${DB_NAME}" 2>/dev/null' EXIT

echo "polaris-idempotency-test: load #1 into ${DB_NAME}..."
if ! run_load; then
    echo "✗ first load failed" >&2
    exit 1
fi
SNAP1=$(snapshot_state)

echo "polaris-idempotency-test: load #2 (idempotency check)..."
if ! run_load; then
    echo "✗ second load failed — schema is NOT idempotent (re-load errors)" >&2
    exit 1
fi
SNAP2=$(snapshot_state)

if [[ "${SNAP1}" == "${SNAP2}" ]]; then
    echo "✓ schema is idempotent — state after 2 loads matches 1 load"
    echo "  table_count:    $(echo "${SNAP1}" | grep '^table_count' | cut -d'|' -f2)"
    echo "  trigger_count:  $(echo "${SNAP1}" | grep '^trigger_count' | cut -d'|' -f2)"
    exit 0
fi

echo "✗ schema is NOT idempotent — state DIFFERS between load #1 and load #2"
echo "diff:" >&2
diff <(echo "${SNAP1}") <(echo "${SNAP2}") | sed 's/^/  /' >&2
exit 1
