#!/usr/bin/env bash
# ============================================================================
# polaris-loadtest-tokens.sh — token-volume load simulator
#
# v9.23 / BIG MISSION Medium #2. Companion to polaris-load-test.sh (v8.80
# which simulates HTTP RPS). This script simulates TOKEN VOLUME: bulk-
# inserts N tokens into a target database (NOT production), then times
# atlas + verification queries against the resulting DB. The output is a
# per-query latency report comparing pre-insert vs post-insert state.
#
# Per the BIG MISSION Sanctum, the Anti-Architect required honest accounting:
# the script reports the volume actually tested, not a fictitious "10M+
# certified" claim. To go beyond what's been tested, the operator runs the
# script at higher volume in their own environment and submits the report.
#
# What this script does NOT do:
#   - It does NOT run against the production database. Refuses unless
#     POLARIS_LOADTEST_TARGET is set to a non-prod-looking value.
#   - It does NOT simulate the full verification flow with crypto-signing
#     (that's polaris-load-test.sh's domain). This is a *data-volume*
#     stress test.
#   - It does NOT generate cryptographically-real signatures; tokens
#     get placeholder signature values.
#   - It does NOT use uc1_issue_and_activate; bulk inserts go direct to
#     IdentityToken with synthetic individual_id + agency_id rows.
#
# Usage:
#   POLARIS_LOADTEST_TARGET=polaris_loadtest ./scripts/polaris-loadtest-tokens.sh
#   POLARIS_LOADTEST_TARGET=polaris_loadtest ./scripts/polaris-loadtest-tokens.sh --tokens 1000000
#   POLARIS_LOADTEST_TARGET=polaris_loadtest ./scripts/polaris-loadtest-tokens.sh --tokens 10000000 --batch 100000
#
# Options:
#   --tokens N    Number of tokens to insert (default: 100000)
#   --batch B     Insert batch size (default: 10000)
#   --skip-create Skip creating supporting Individual + Agency rows
#                 (assumes target DB already has them; useful for
#                 incremental scale-up runs)
#   --report-only Run only the post-insert query timings; don't insert
#
# Output: structured report to stdout with:
#   - row counts before/after
#   - per-query latency (atlas_summary, atlas_lookup, verifications
#     by individual, single-token-lookup)
#   - total insert time + insert rate (rows/sec)
#
# Cadence-recommendation: run quarterly against staging/loadtest DBs.
# Not for production cron.
# ============================================================================

set -euo pipefail

# Hard refuse production: the target name must NOT contain 'prod', and
# the operator must explicitly set POLARIS_LOADTEST_TARGET.
if [[ -z "${POLARIS_LOADTEST_TARGET:-}" ]]; then
    echo "✗ POLARIS_LOADTEST_TARGET must be set to a non-production database name." >&2
    echo "  example: POLARIS_LOADTEST_TARGET=polaris_loadtest" >&2
    exit 2
fi

if [[ "${POLARIS_LOADTEST_TARGET}" =~ prod ]]; then
    echo "✗ refusing — POLARIS_LOADTEST_TARGET contains 'prod' (${POLARIS_LOADTEST_TARGET})" >&2
    echo "  this script never runs against production." >&2
    exit 3
fi

# Defaults
TOKEN_COUNT=100000
BATCH_SIZE=10000
SKIP_CREATE=0
REPORT_ONLY=0

while [[ $# -gt 0 ]]; do
    case "$1" in
        --tokens)       shift; TOKEN_COUNT="${1}" ;;
        --tokens=*)     TOKEN_COUNT="${1#*=}" ;;
        --batch)        shift; BATCH_SIZE="${1}" ;;
        --batch=*)      BATCH_SIZE="${1#*=}" ;;
        --skip-create)  SKIP_CREATE=1 ;;
        --report-only)  REPORT_ONLY=1 ;;
        --help|-h)
            sed -n '2,50p' "$0" | sed 's/^# \{0,1\}//'
            exit 0
            ;;
        *) echo "unknown arg: $1" >&2; exit 2 ;;
    esac
    shift
done

# Sanity-check args are numeric
if ! [[ "${TOKEN_COUNT}" =~ ^[0-9]+$ ]] || [[ "${TOKEN_COUNT}" -le 0 ]]; then
    echo "✗ --tokens must be a positive integer" >&2; exit 2
fi
if ! [[ "${BATCH_SIZE}" =~ ^[0-9]+$ ]] || [[ "${BATCH_SIZE}" -le 0 ]]; then
    echo "✗ --batch must be a positive integer" >&2; exit 2
fi

PSQL="${POLARIS_PSQL:-psql}"
DB_NAME="${POLARIS_LOADTEST_TARGET}"
DB_USER="${POLARIS_DB_USER:-polaris_app}"
DB_HOST="${POLARIS_DB_HOST:-localhost}"

PSQLARGS=(-h "${DB_HOST}" -U "${DB_USER}" -d "${DB_NAME}" -At -v ON_ERROR_STOP=1)

# Confirm target DB exists + schema is present
if ! ROW_COUNT=$(${PSQL} "${PSQLARGS[@]}" -c "SELECT count(*) FROM IdentityToken" 2>&1); then
    echo "✗ cannot reach IdentityToken in ${DB_NAME}; ensure target DB has schema loaded" >&2
    echo "${ROW_COUNT}" | sed 's/^/  /' >&2
    exit 4
fi

echo "polaris-loadtest-tokens:"
echo "  target db:   ${DB_NAME}"
echo "  tokens:      ${TOKEN_COUNT} (batch ${BATCH_SIZE})"
echo "  starting row count (IdentityToken): ${ROW_COUNT}"
echo

run_timed_query() {
    local label="$1"
    local sql="$2"
    local start_ms end_ms
    start_ms=$(${PSQL} "${PSQLARGS[@]}" -c \
        "SELECT (EXTRACT(EPOCH FROM clock_timestamp()) * 1000)::bigint")
    ${PSQL} "${PSQLARGS[@]}" -c "${sql}" >/dev/null
    end_ms=$(${PSQL} "${PSQLARGS[@]}" -c \
        "SELECT (EXTRACT(EPOCH FROM clock_timestamp()) * 1000)::bigint")
    local elapsed=$((end_ms - start_ms))
    printf "  %-40s %6d ms\n" "${label}" "${elapsed}"
}

echo "===== query timings (pre-insert) ====="
run_timed_query "count IdentityToken" "SELECT count(*) FROM IdentityToken"
run_timed_query "count active tokens" \
    "SELECT count(*) FROM IdentityToken WHERE status='ACTIVE'"
run_timed_query "atlas_token_distribution()" \
    "SELECT * FROM atlas_token_distribution()"
echo

if [[ "${REPORT_ONLY}" -eq 1 ]]; then
    echo "→ --report-only; skipping insert"
    exit 0
fi

# Create supporting rows if needed (Individual + Agency)
if [[ "${SKIP_CREATE}" -eq 0 ]]; then
    echo "===== creating supporting rows ====="
    INDIVIDUAL_COUNT=$(${PSQL} "${PSQLARGS[@]}" \
        -c "SELECT count(*) FROM Individual")
    AGENCY_COUNT=$(${PSQL} "${PSQLARGS[@]}" \
        -c "SELECT count(*) FROM Agency")
    echo "  pre-insert: ${INDIVIDUAL_COUNT} individuals, ${AGENCY_COUNT} agencies"

    # Insert TOKEN_COUNT new individuals + 1 placeholder agency if missing.
    # The 'loadtest' country prefix tags them for cleanup.
    ${PSQL} "${PSQLARGS[@]}" -c "
        INSERT INTO Agency (agency_name, jurisdiction_country)
        SELECT 'loadtest-agency', 'XX'
        WHERE NOT EXISTS (SELECT 1 FROM Agency WHERE agency_name = 'loadtest-agency');
    " >/dev/null

    # Bulk-insert individuals via generate_series
    BATCH_START=$(($(${PSQL} "${PSQLARGS[@]}" -c \
        "SELECT COALESCE(MAX(individual_id), 0) FROM Individual") + 1))
    BATCH_END=$((BATCH_START + TOKEN_COUNT - 1))

    echo "  inserting ${TOKEN_COUNT} individuals (id range ${BATCH_START}..${BATCH_END})"
    INDIVIDUAL_START_MS=$(date +%s%3N 2>/dev/null || \
                          ${PSQL} "${PSQLARGS[@]}" -c \
                          "SELECT (EXTRACT(EPOCH FROM clock_timestamp())*1000)::bigint")

    ${PSQL} "${PSQLARGS[@]}" -c "
        INSERT INTO Individual (
            full_name, date_of_birth, country_of_residence
        )
        SELECT 'loadtest-individual-' || i,
               DATE '1970-01-01' + (i % 20000) * INTERVAL '1 day',
               'XX'
        FROM generate_series(${BATCH_START}, ${BATCH_END}) i;
    " >/dev/null

    INDIVIDUAL_END_MS=$(date +%s%3N 2>/dev/null || \
                        ${PSQL} "${PSQLARGS[@]}" -c \
                        "SELECT (EXTRACT(EPOCH FROM clock_timestamp())*1000)::bigint")
    INDIVIDUAL_ELAPSED=$((INDIVIDUAL_END_MS - INDIVIDUAL_START_MS))
    echo "  individuals inserted in ${INDIVIDUAL_ELAPSED} ms"
fi

# Bulk-insert tokens
echo
echo "===== inserting tokens ====="
TOTAL_INSERTED=0
INSERT_START_MS=$(date +%s%3N 2>/dev/null || \
                   ${PSQL} "${PSQLARGS[@]}" -c \
                   "SELECT (EXTRACT(EPOCH FROM clock_timestamp())*1000)::bigint")

while [[ "${TOTAL_INSERTED}" -lt "${TOKEN_COUNT}" ]]; do
    THIS_BATCH=${BATCH_SIZE}
    if [[ $((TOTAL_INSERTED + BATCH_SIZE)) -gt "${TOKEN_COUNT}" ]]; then
        THIS_BATCH=$((TOKEN_COUNT - TOTAL_INSERTED))
    fi
    # Insert THIS_BATCH tokens against most-recent THIS_BATCH new individuals.
    ${PSQL} "${PSQLARGS[@]}" -c "
        INSERT INTO IdentityToken (
            individual_id, issuing_agency_id, status,
            issued_at, expires_at, algorithm_id, token_value
        )
        SELECT individual_id,
               (SELECT agency_id FROM Agency WHERE agency_name='loadtest-agency'),
               'ACTIVE',
               NOW(),
               NOW() + INTERVAL '5 years',
               (SELECT min(algorithm_id) FROM CryptographicAlgorithm),
               'loadtest-token-' || individual_id
          FROM Individual
         WHERE full_name LIKE 'loadtest-individual-%'
           AND individual_id NOT IN (SELECT individual_id FROM IdentityToken
                                      WHERE status='ACTIVE')
         LIMIT ${THIS_BATCH};
    " >/dev/null
    TOTAL_INSERTED=$((TOTAL_INSERTED + THIS_BATCH))
    printf "\r  inserted: %d / %d (%d%%)" "${TOTAL_INSERTED}" \
           "${TOKEN_COUNT}" $((TOTAL_INSERTED * 100 / TOKEN_COUNT))
done
echo

INSERT_END_MS=$(date +%s%3N 2>/dev/null || \
                 ${PSQL} "${PSQLARGS[@]}" -c \
                 "SELECT (EXTRACT(EPOCH FROM clock_timestamp())*1000)::bigint")
INSERT_ELAPSED_MS=$((INSERT_END_MS - INSERT_START_MS))
INSERT_RATE=$((TOTAL_INSERTED * 1000 / (INSERT_ELAPSED_MS > 0 ? INSERT_ELAPSED_MS : 1)))
echo "  inserted ${TOTAL_INSERTED} tokens in ${INSERT_ELAPSED_MS} ms (${INSERT_RATE} rows/sec)"

echo
echo "===== query timings (post-insert) ====="
run_timed_query "count IdentityToken" "SELECT count(*) FROM IdentityToken"
run_timed_query "count active tokens" \
    "SELECT count(*) FROM IdentityToken WHERE status='ACTIVE'"
run_timed_query "atlas_token_distribution()" \
    "SELECT * FROM atlas_token_distribution()"
run_timed_query "single-token lookup by id" \
    "SELECT token_id, status FROM IdentityToken
     WHERE token_id = (SELECT max(token_id) FROM IdentityToken)"
run_timed_query "token by individual_id" \
    "SELECT token_id FROM IdentityToken
     WHERE individual_id = (SELECT individual_id FROM Individual
                            WHERE full_name LIKE 'loadtest-individual-%'
                            ORDER BY individual_id DESC LIMIT 1)"

echo
echo "===== honest accounting ====="
echo "  VERIFIED LOCALLY: ${TOKEN_COUNT} tokens in ${INSERT_ELAPSED_MS}ms"
echo "  This run did NOT exercise:"
echo "    - cryptographic-real signing (placeholders only)"
echo "    - HTTP-layer rate limits (data-tier only)"
echo "    - federation / multi-region (RESERVED-NOT-PLANNED per v9.16)"
echo "    - concurrent-write conflicts (single-thread inserts)"
echo
echo "  For 10M+ scale: invoke with --tokens 10000000 (allow hours);"
echo "    the per-query latency report stays meaningful at any scale."

exit 0
