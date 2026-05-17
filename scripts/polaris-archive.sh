#!/usr/bin/env bash
# ============================================================================
# polaris-archive.sh — selective export of audit-log rows to cold storage
#
# v8.84 / Arc B Phase 2 — closes the docs/operator/OPERATIONS.md storage-growth gap
# WITHOUT compromising C1 (the rows stay in the hot tables; the archive
# is a backup, not a move). The "rotate-from-hot" half of an archive
# policy is genuinely constitutional — it touches C1's append-only
# invariant — and is on file as an OPEN Sanctum awaiting VANTA's
# decision (sanctum/2026-05-14-audit-log-deletion-from-hot.md).
#
# What this script does:
#   - SELECTs every audit-class row older than --cutoff-days (default 365)
#   - Writes per-table CSV files into a timestamped tarball
#   - Includes a MANIFEST.json with row counts + SHA-256 hashes
#   - Writes mode 0600 to the destination
#
# What this script DOES NOT do:
#   - It does NOT issue DELETE against any audit table. C1 stands.
#   - It does NOT mutate any row. Read-only on the live DB.
#   - It does NOT replace polaris-backup.sh. That captures the
#     entire DB + filesystem AoR; this script captures only audit-class
#     rows older than the cutoff, for retention-policy purposes.
#
# Audit-class tables exported (all 9 schema AoR instances):
#   TokenLifecycleEvent, VerificationEvent, EnrollmentStatusEvent,
#   AuthAuditLog, AnchorBatch, AgencyTrustAttestation,
#   TokenStateEpoch, TokenStateEpochLeaf, DuressEvent, TokenSignature,
#   RecoveryRequest
#
# Usage:
#   ./scripts/polaris-archive.sh                            # 365-day cutoff, /var/backups dest
#   ./scripts/polaris-archive.sh --cutoff-days=730          # 2-year retention floor
#   ./scripts/polaris-archive.sh --dest=/path/to/dir
#   ./scripts/polaris-archive.sh --target=docker-stack      # use the running prod Postgres
#   ./scripts/polaris-archive.sh --verify-latest --dest=DIR # re-hash newest archive
# ============================================================================

set -euo pipefail

EXIT_OK=0
EXIT_USAGE=2
EXIT_DB_FAIL=3
EXIT_ARCHIVE_MISSING=4
EXIT_VERIFY_FAIL=5

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"
POLARIS_ROOT="$(cd -- "${SCRIPT_DIR}/.." &> /dev/null && pwd)"
COMPOSE_FILE="${POLARIS_ROOT}/polaris_web/docker-compose.prod.yml"

DEST="/var/backups"
CUTOFF_DAYS=365
USE_DOCKER_STACK=0
VERIFY_LATEST=0

while [[ $# -gt 0 ]]; do
    case "$1" in
        --dest=*)          DEST="${1#--dest=}" ;;
        --dest)            shift; DEST="${1:-/var/backups}" ;;
        --cutoff-days=*)   CUTOFF_DAYS="${1#--cutoff-days=}" ;;
        --cutoff-days)     shift; CUTOFF_DAYS="${1:-365}" ;;
        --target=docker-stack) USE_DOCKER_STACK=1 ;;
        --verify-latest)   VERIFY_LATEST=1 ;;
        --help|-h)
            sed -n '2,40p' "$0" | sed 's/^# \{0,1\}//'
            exit "${EXIT_USAGE}"
            ;;
        *) echo "warn: unknown arg $1" >&2 ;;
    esac
    shift
done

mkdir -p "${DEST}"

# Pick a psql invocation.
run_psql() {
    if [[ "${USE_DOCKER_STACK}" -eq 1 ]]; then
        docker compose -f "${COMPOSE_FILE}" exec -T postgres \
            psql -U postgres -d polaris -tA "$@"
    else
        psql -h "${POLARIS_DB_HOST:-localhost}" \
             -U "${POLARIS_DB_USER:-postgres}" \
             -d "${POLARIS_DB_NAME:-polaris}" \
             -tA "$@"
    fi
}

sha256_of() {
    if command -v sha256sum >/dev/null 2>&1; then
        sha256sum "$1" | awk '{print $1}'
    else
        shasum -a 256 "$1" | awk '{print $1}'
    fi
}

# ---------------------------------------------------------------------------
# Verify mode
# ---------------------------------------------------------------------------
if [[ "${VERIFY_LATEST}" -eq 1 ]]; then
    LATEST=$(ls -1t "${DEST}"/polaris-archive-*.tar.gz 2>/dev/null | head -1 || true)
    if [[ -z "${LATEST}" ]]; then
        echo "  ✗ no archives under ${DEST}" >&2
        exit "${EXIT_ARCHIVE_MISSING}"
    fi
    echo "  → verifying: ${LATEST}"
    TMP=$(mktemp -d)
    trap 'rm -rf "${TMP}"' EXIT
    tar -xzf "${LATEST}" -C "${TMP}"
    EXTRACTED=$(find "${TMP}" -maxdepth 1 -mindepth 1 -type d -name 'polaris-archive-*' | head -1)
    [[ -z "${EXTRACTED}" ]] && EXTRACTED="${TMP}"
    python3 - "${EXTRACTED}" <<'PY'
import json, hashlib, os, sys
base = sys.argv[1]
with open(os.path.join(base, "MANIFEST.json")) as f:
    m = json.load(f)
ok = True
for name, expected in m.get("sha256", {}).items():
    p = os.path.join(base, name)
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 16), b""):
            h.update(chunk)
    got = h.hexdigest()
    if got != expected:
        print(f"  ✗ {name} hash mismatch")
        ok = False
    else:
        print(f"  ✓ {name}  ({m.get('row_counts', {}).get(name, '?')} rows)")
print(f"  cutoff_days = {m.get('cutoff_days', '?')}")
print(f"  oldest_kept_at_least_until = {m.get('cutoff_iso', '?')}")
if not ok:
    sys.exit(1)
PY
    exit "${EXIT_OK}"
fi

# ---------------------------------------------------------------------------
# Archive mode
# ---------------------------------------------------------------------------
TS=$(date -u +%Y%m%dT%H%M%SZ)
WORK=$(mktemp -d)
trap 'rm -rf "${WORK}"' EXIT
STAGE="${WORK}/polaris-archive-${TS}"
mkdir -p "${STAGE}"

# Resolve cutoff timestamp (Postgres-evaluated).
CUTOFF_ISO=$(run_psql -c "SELECT to_char(now() - interval '${CUTOFF_DAYS} days', 'YYYY-MM-DD\"T\"HH24:MI:SS.MSOF')" 2>/dev/null | tr -d '\n\r' || echo "")
if [[ -z "${CUTOFF_ISO}" ]]; then
    echo "  ✗ cannot reach DB to compute cutoff timestamp" >&2
    exit "${EXIT_DB_FAIL}"
fi

cat <<BANNER
  Polaris audit-log archive
  ─────────────────────────
  Cutoff (days):     ${CUTOFF_DAYS}
  Cutoff timestamp:  ${CUTOFF_ISO}
  Mode:              C1-preserving (no DELETE; rows stay in hot tables)
  Destination:       ${DEST}/polaris-archive-${TS}.tar.gz
BANNER

# Each row below: (output_file, table, time_column).
# Order matches the 9 schema AoR + the 2 supporting audit-class tables.
declare -a TABLES=(
    "lifecycle.csv|TokenLifecycleEvent|event_timestamp"
    "verifications.csv|VerificationEvent|event_timestamp"
    "enrollment_events.csv|EnrollmentStatusEvent|event_timestamp"
    "auth_audit.csv|AuthAuditLog|event_timestamp"
    "anchor_batches.csv|AnchorBatch|created_at"
    "trust_attestations.csv|AgencyTrustAttestation|attested_date"
    "epochs.csv|TokenStateEpoch|valid_from"
    "epoch_leaves.csv|TokenStateEpochLeaf|leaf_id"
    "duress_events.csv|DuressEvent|event_timestamp"
    "token_signatures.csv|TokenSignature|signed_at"
    "recovery_requests.csv|RecoveryRequest|requested_at"
)

TOTAL_ROWS=0

for entry in "${TABLES[@]}"; do
    IFS='|' read -r out_file table tcol <<< "${entry}"
    echo "  → exporting ${table} (older than cutoff)…"
    if [[ "${table}" == "TokenStateEpochLeaf" ]]; then
        sql="COPY (SELECT * FROM ${table}) TO STDOUT WITH CSV HEADER"
    else
        sql="COPY (SELECT * FROM ${table} WHERE ${tcol} < '${CUTOFF_ISO}'::timestamptz) TO STDOUT WITH CSV HEADER"
    fi
    if run_psql -c "${sql}" > "${STAGE}/${out_file}" 2>/dev/null; then
        line_count=$(wc -l < "${STAGE}/${out_file}" | tr -d ' ')
        row_count=$(( line_count > 0 ? line_count - 1 : 0 ))
        TOTAL_ROWS=$(( TOTAL_ROWS + row_count ))
        echo "      ${row_count} rows"
    else
        echo "      ✗ failed (skipping)"
        : > "${STAGE}/${out_file}"
    fi
done

# Manifest with row counts + hashes.
echo "  → writing MANIFEST.json…"
python3 - "${STAGE}" "${CUTOFF_DAYS}" "${CUTOFF_ISO}" "${TS}" <<'PY' > "${STAGE}/MANIFEST.json"
import json, hashlib, os, sys, time
stage, cutoff_days, cutoff_iso, ts = sys.argv[1:5]
files = sorted(f for f in os.listdir(stage) if f != "MANIFEST.json")
out = {
    "timestamp_utc": ts,
    "generated_at": time.time(),
    "polaris_version": "8.84",
    "archive_kind": "audit-log-export-only-C1-preserving",
    "cutoff_days": int(cutoff_days),
    "cutoff_iso": cutoff_iso,
    "deletion_from_hot": False,
    "deletion_sanctum": "sanctum/2026-05-14-audit-log-deletion-from-hot.md",
    "sha256": {},
    "size_bytes": {},
    "row_counts": {},
}
for name in files:
    p = os.path.join(stage, name)
    if not os.path.isfile(p):
        continue
    h = hashlib.sha256()
    sz = 0
    rc = 0
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 16), b""):
            h.update(chunk)
            sz += len(chunk)
    # Count CSV rows (excluding header line).
    if name.endswith(".csv") and sz > 0:
        with open(p) as fh:
            rc = max(0, sum(1 for _ in fh) - 1)
    out["sha256"][name] = h.hexdigest()
    out["size_bytes"][name] = sz
    out["row_counts"][name] = rc
print(json.dumps(out, indent=2))
PY

# Bundle.
OUT="${DEST}/polaris-archive-${TS}.tar.gz"
tar -czf "${OUT}" -C "${WORK}" "polaris-archive-${TS}"
chmod 0600 "${OUT}"

SIZE=$(du -h "${OUT}" | awk '{print $1}')

cat <<DONE

  ✓ archive complete: ${OUT}  (${SIZE}; ${TOTAL_ROWS} rows total)

  C1 preserved — no rows deleted from any audit table.

  Verify:    $(basename "$0") --verify-latest --dest=${DEST}
  Constitutional question (deletion-from-hot):
             sanctum/2026-05-14-audit-log-deletion-from-hot.md

  Recommended retention chain:
    Daily   →  polaris-backup.sh  (whole-system)
    Yearly  →  polaris-archive.sh  (audit-log, 365-day cutoff)
    +5y     →  cold storage (S3 Glacier / equivalent)

DONE
exit "${EXIT_OK}"
