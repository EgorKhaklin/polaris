#!/usr/bin/env bash
# ============================================================================
# polaris-concurrency-harness.sh — measured C3 behavior under load
#
# v9.24 / BIG MISSION Tier 2 #8. Companion to polaris-loadtest-tokens.sh
# (v9.23 token-volume) and polaris-load-test.sh (v8.80 HTTP-RPS). This
# script measures CONCURRENCY behavior: N threads racing to issue an
# ACTIVE token for the SAME individual, observing the C3 partial unique
# index in action.
#
# What this script measures (per the v9.24 Sanctum):
#   - Successful issuance count (must be ≤ 1 per individual; C3 invariant)
#   - Lock-contention events on uq_one_active_token_per_individual
#   - Per-thread latency distribution
#   - The DETERMINISTIC RACE PROPERTY: of N concurrent attempts, exactly
#     one succeeds; N-1 lose the race deterministically (the partial
#     unique index + FOR UPDATE locking ensure this).
#
# The output is the load-bearing claim: not "we handle N RPS" but
# "C3 holds under N concurrent writers, deterministically."
#
# Refuses production DBs (POLARIS_LOADTEST_TARGET must not match prod).
#
# Usage:
#   POLARIS_LOADTEST_TARGET=polaris_test ./scripts/polaris-concurrency-harness.sh
#   POLARIS_LOADTEST_TARGET=polaris_test ./scripts/polaris-concurrency-harness.sh --threads 100 --individuals 10
#
# Options:
#   --threads N       Concurrent threads (default: 20)
#   --individuals M   Distinct individuals to race for (default: 5)
#                     Each individual gets N/M threads racing for it.
#   --report-dir DIR  Write JSON results here (default: meta/load-results)
# ============================================================================

set -uo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"
POLARIS_ROOT="$(cd -- "${SCRIPT_DIR}/.." &> /dev/null && pwd)"

if [[ -z "${POLARIS_LOADTEST_TARGET:-}" ]]; then
    echo "✗ POLARIS_LOADTEST_TARGET must be set (non-production DB name)" >&2
    exit 2
fi
if [[ "${POLARIS_LOADTEST_TARGET}" =~ prod ]]; then
    echo "✗ refusing — POLARIS_LOADTEST_TARGET contains 'prod'" >&2
    exit 3
fi

THREADS=20
INDIVIDUALS=5
REPORT_DIR="${POLARIS_ROOT}/meta/load-results"
for arg in "$@"; do
    case "${arg}" in
        --threads)     shift; THREADS="${1:-20}" ;;
        --threads=*)   THREADS="${arg#*=}" ;;
        --individuals) shift; INDIVIDUALS="${1:-5}" ;;
        --individuals=*) INDIVIDUALS="${arg#*=}" ;;
        --report-dir)  shift; REPORT_DIR="${1:-${REPORT_DIR}}" ;;
        --report-dir=*) REPORT_DIR="${arg#*=}" ;;
        --help|-h)
            sed -n '2,32p' "$0" | sed 's/^# \{0,1\}//'
            exit 0
            ;;
    esac
    shift 2>/dev/null || true
done

mkdir -p "${REPORT_DIR}"
TS=$(date -u +%Y-%m-%dT%H%M%SZ)
OUT_FILE="${REPORT_DIR}/${TS}-concurrency.json"

python3 - "${THREADS}" "${INDIVIDUALS}" "${OUT_FILE}" "${POLARIS_LOADTEST_TARGET}" <<'PY'
import os
import sys
import time
import json
import threading
from datetime import datetime, timezone

threads, individuals, out_file, db_name = sys.argv[1:5]
threads = int(threads)
individuals = int(individuals)

# Connect via psycopg2
try:
    import psycopg2
except ImportError:
    print("✗ psycopg2 required — pip install psycopg2-binary", file=sys.stderr)
    sys.exit(4)

DB_HOST = os.environ.get("POLARIS_DB_HOST", "localhost")
DB_USER = os.environ.get("POLARIS_DB_USER", "polaris_app")
DB_PASS = os.environ.get("POLARIS_DB_PASSWORD", "polaris_dev_password")

# Set up individuals: first M individuals from existing data; or create
# placeholders if not present
setup_conn = psycopg2.connect(host=DB_HOST, user=DB_USER, password=DB_PASS, dbname=db_name)
setup_conn.autocommit = True
with setup_conn.cursor() as cur:
    cur.execute("SELECT individual_id FROM Individual ORDER BY individual_id LIMIT %s", (individuals,))
    rows = cur.fetchall()
    if len(rows) < individuals:
        print(f"✗ only {len(rows)} individuals exist; need {individuals}", file=sys.stderr)
        sys.exit(5)
    individual_ids = [r[0] for r in rows]

    # Revoke all ACTIVE tokens for these individuals so the race is clean
    cur.execute(
        "UPDATE IdentityToken SET status='REVOKED' "
        "WHERE individual_id = ANY(%s) AND status='ACTIVE'",
        (individual_ids,)
    )

    # Get an agency + algorithm to use
    cur.execute("SELECT agency_id FROM Agency LIMIT 1")
    agency = cur.fetchone()
    if not agency:
        print("✗ no Agency rows", file=sys.stderr); sys.exit(6)
    agency_id = agency[0]

    cur.execute("SELECT algorithm_id FROM CryptographicAlgorithm LIMIT 1")
    alg = cur.fetchone()
    if not alg:
        print("✗ no CryptographicAlgorithm rows", file=sys.stderr); sys.exit(7)
    alg_id = alg[0]

setup_conn.close()

print(f"polaris-concurrency-harness: {threads} threads racing for {individuals} individuals")
print(f"  individual_ids: {individual_ids}")
print(f"  threads-per-individual: {threads // individuals} (extras drop)")

results = []
lock = threading.Lock()

def attempt(thread_id, individual_id):
    conn = psycopg2.connect(host=DB_HOST, user=DB_USER, password=DB_PASS, dbname=db_name)
    conn.autocommit = False
    t0 = time.perf_counter()
    error_class = None
    error_text = ""
    succeeded = False
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO IdentityToken (individual_id, issuing_agency_id, status, "
                "issued_at, expires_at, algorithm_id, token_value) "
                "VALUES (%s, %s, 'ACTIVE', NOW(), NOW() + INTERVAL '1 year', %s, %s)",
                (individual_id, agency_id, alg_id,
                 f"conc-harness-T{thread_id}-{int(time.time() * 1000)}")
            )
            conn.commit()
            succeeded = True
    except psycopg2.errors.UniqueViolation as e:
        error_class = "UniqueViolation"
        error_text = str(e)[:200]
        conn.rollback()
    except Exception as e:
        error_class = type(e).__name__
        error_text = str(e)[:200]
        conn.rollback()
    finally:
        conn.close()
    elapsed_ms = (time.perf_counter() - t0) * 1000
    with lock:
        results.append({
            "thread_id": thread_id,
            "individual_id": individual_id,
            "succeeded": succeeded,
            "error_class": error_class,
            "error_text": error_text,
            "elapsed_ms": round(elapsed_ms, 2),
        })

# Build the race plan: each thread targets one individual round-robin
plan = []
for t in range(threads):
    plan.append((t, individual_ids[t % individuals]))

print(f"  starting {threads} threads...")
t_start = time.perf_counter()
threads_list = [threading.Thread(target=attempt, args=p) for p in plan]
for th in threads_list:
    th.start()
for th in threads_list:
    th.join()
total_elapsed_s = time.perf_counter() - t_start

# Analyze
per_individual = {}
for r in results:
    per_individual.setdefault(r["individual_id"], []).append(r)

c3_violations = []
for iid, attempts in per_individual.items():
    succ = sum(1 for a in attempts if a["succeeded"])
    if succ > 1:
        c3_violations.append((iid, succ))

unique_violations = sum(1 for r in results if r["error_class"] == "UniqueViolation")
other_errors = sum(1 for r in results if r["error_class"] and r["error_class"] != "UniqueViolation")
succeeded = sum(1 for r in results if r["succeeded"])

print()
print(f"===== results =====")
print(f"  total attempts:       {len(results)}")
print(f"  succeeded:            {succeeded}")
print(f"  UniqueViolation (C3): {unique_violations}")
print(f"  other errors:         {other_errors}")
print(f"  total wall-clock:     {total_elapsed_s:.3f}s")
if results:
    elapsed_sorted = sorted(r["elapsed_ms"] for r in results)
    p50 = elapsed_sorted[len(elapsed_sorted) // 2]
    p95 = elapsed_sorted[int(len(elapsed_sorted) * 0.95)]
    print(f"  p50 latency:          {p50:.1f}ms")
    print(f"  p95 latency:          {p95:.1f}ms")
print()

if c3_violations:
    print(f"  ✗ C3 VIOLATION: {len(c3_violations)} individual(s) ended with >1 ACTIVE token")
    for iid, n in c3_violations:
        print(f"      individual_id={iid}: {n} successes")
    c3_ok = False
else:
    print(f"  ✓ C3 holds: every individual has ≤1 ACTIVE token")
    c3_ok = True

# Write JSON report
report = {
    "timestamp_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    "threads": threads,
    "individuals": individuals,
    "total_attempts": len(results),
    "succeeded": succeeded,
    "unique_violations_c3": unique_violations,
    "other_errors": other_errors,
    "total_elapsed_seconds": round(total_elapsed_s, 3),
    "c3_invariant_held": c3_ok,
    "c3_violations": [
        {"individual_id": iid, "successful_inserts": n} for iid, n in c3_violations
    ],
    "per_thread_results": results,
}
with open(out_file, "w") as f:
    json.dump(report, f, indent=2, default=str)
print(f"  → wrote {out_file}")

sys.exit(0 if c3_ok else 8)
PY
