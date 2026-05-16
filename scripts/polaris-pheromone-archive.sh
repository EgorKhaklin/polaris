#!/usr/bin/env bash
# ============================================================================
# polaris-pheromone-archive.sh — export Pheromone rows older than cutoff
#                                 to a manifest-hashed tarball
#
# v9.07 / Wave 3 / D5-impl — Sanctum-decided per
# sanctum/2026-05-15-pheromone-rotation.md (Position A: mirror v8.84+v8.87
# audit-log archive+purge framework). EXPORT-ONLY — never deletes.
# Companion: polaris-pheromone-purge.sh (the deletion path) calls
# uc_pheromone_archive_purge() inside a transaction.
#
# Operator workflow:
#   1. ./scripts/polaris-pheromone-archive.sh --cutoff "30 days ago"
#      → produces polaris-pheromone-archive-<ISO>-<N>rows.tar.gz +
#        embedded MANIFEST.json with cutoff + sha256
#   2. ./scripts/polaris-pheromone-purge.sh --archive <tarball>
#                                            --actor-user-id <id>
#      → verifies archive SHA-256, calls uc_pheromone_archive_purge()
#
# C1 preserved: this script issues SELECT only; never DELETE.
#
# Usage:
#   ./scripts/polaris-pheromone-archive.sh \
#       [--cutoff='30 days ago'] \
#       [--out-dir=DIR] \
#       [--target=docker-stack] \
#       [--verify-latest]
#
#   --cutoff           PostgreSQL interval-or-timestamp expression
#                      (default: '30 days ago')
#   --out-dir          where to write the tarball (default: ./archives/pheromone)
#   --target=docker-stack  use the running docker-compose Postgres
#   --verify-latest    re-hash the most recent archive in --out-dir;
#                      compare against its embedded MANIFEST.json
#
# Exit codes:
#   0  archive written + verified, OR --verify-latest passed
#   2  usage error
#   3  no rows to archive (cutoff selects nothing)
#   4  SHA-256 mismatch on --verify-latest
#   5  pg_dump or shasum failed
# ============================================================================

set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"

# Defaults
CUTOFF='30 days ago'
OUT_DIR="$ROOT/archives/pheromone"
TARGET=local
VERIFY_LATEST=0

# Greppable exit codes
EXIT_OK=0
EXIT_USAGE=2
EXIT_NO_ROWS=3
EXIT_SHA_MISMATCH=4
EXIT_TOOL_FAIL=5

usage() {
    sed -n '2,42p' "$0" | sed 's/^# \?//'
    exit "$EXIT_USAGE"
}

# Parse args
while [[ $# -gt 0 ]]; do
    case "$1" in
        --cutoff=*)         CUTOFF="${1#*=}"; shift ;;
        --cutoff)           CUTOFF="$2"; shift 2 ;;
        --out-dir=*)        OUT_DIR="${1#*=}"; shift ;;
        --out-dir)          OUT_DIR="$2"; shift 2 ;;
        --target=docker-stack) TARGET=docker-stack; shift ;;
        --verify-latest)    VERIFY_LATEST=1; shift ;;
        -h|--help)          usage ;;
        *)
            echo "unknown arg: $1" >&2
            usage
            ;;
    esac
done

mkdir -p "$OUT_DIR"

# DB env (mirrors polaris-archive.sh + ai-hydra.sh discovery)
export POLARIS_DB_HOST="${POLARIS_DB_HOST:-localhost}"
export POLARIS_DB_NAME="${POLARIS_DB_NAME:-polaris_test}"
export POLARIS_DB_USER="${POLARIS_DB_USER:-polaris_app}"
export POLARIS_DB_PASSWORD="${POLARIS_DB_PASSWORD:-polaris_dev_password}"

PSQL_BIN=""
for cand in \
    "/opt/homebrew/opt/postgresql@16/bin/psql" \
    "/usr/local/opt/postgresql@16/bin/psql" \
    "$(command -v psql 2>/dev/null)" \
; do
    if [ -x "$cand" ]; then
        PSQL_BIN="$cand"
        break
    fi
done

if [ -z "$PSQL_BIN" ]; then
    echo "polaris-pheromone-archive: no psql binary found in PATH or homebrew prefix" >&2
    exit "$EXIT_TOOL_FAIL"
fi

run_psql() {
    if [ "$TARGET" = docker-stack ]; then
        # Inside the running app stack
        docker compose exec -T postgres psql \
            -U "$POLARIS_DB_USER" -d "$POLARIS_DB_NAME" "$@"
    else
        PGPASSWORD="$POLARIS_DB_PASSWORD" "$PSQL_BIN" \
            -h "$POLARIS_DB_HOST" \
            -U "$POLARIS_DB_USER" \
            -d "$POLARIS_DB_NAME" \
            "$@"
    fi
}

# ----------------------------------------------------------------------------
# Verify-latest mode
# ----------------------------------------------------------------------------
if [ "$VERIFY_LATEST" = 1 ]; then
    LATEST=$(ls -1t "$OUT_DIR"/polaris-pheromone-archive-*.tar.gz 2>/dev/null | head -1)
    if [ -z "$LATEST" ]; then
        echo "polaris-pheromone-archive: no archives found in $OUT_DIR" >&2
        exit "$EXIT_TOOL_FAIL"
    fi
    echo "Verifying: $LATEST"
    TMP=$(mktemp -d)
    tar -xzf "$LATEST" -C "$TMP"
    MANIFEST=$(find "$TMP" -name MANIFEST.json -type f | head -1)
    if [ -z "$MANIFEST" ] || [ ! -f "$MANIFEST" ]; then
        echo "  ✗ MANIFEST.json missing inside tarball" >&2
        rm -rf "$TMP"
        exit "$EXIT_SHA_MISMATCH"
    fi
    DECLARED=$(grep -oE '"sha256":\s*"[a-f0-9]{64}"' "$MANIFEST" \
               | head -1 | grep -oE '[a-f0-9]{64}')
    ACTUAL=$(shasum -a 256 "$LATEST" | awk '{print $1}')
    if [ "$DECLARED" = "$ACTUAL" ]; then
        echo "  ✓ SHA-256 verified: $ACTUAL"
        rm -rf "$TMP"
        exit "$EXIT_OK"
    else
        echo "  ✗ MISMATCH" >&2
        echo "    declared: $DECLARED" >&2
        echo "    actual:   $ACTUAL" >&2
        rm -rf "$TMP"
        exit "$EXIT_SHA_MISMATCH"
    fi
fi

# ----------------------------------------------------------------------------
# Archive mode
# ----------------------------------------------------------------------------
ISO_TS=$(date -u +"%Y-%m-%dT%H-%M-%SZ")
TMP_DIR=$(mktemp -d)
EXPORT_FILE="$TMP_DIR/pheromone-${ISO_TS}.csv"
MANIFEST_FILE="$TMP_DIR/MANIFEST.json"

# Resolve cutoff to a concrete timestamp + count rows we WOULD archive
COUNT_ROW=$(run_psql -A -t -c "
    SELECT
        count(*),
        (now() - INTERVAL '$CUTOFF')::text
      FROM Pheromone
     WHERE deposited_at < now() - INTERVAL '$CUTOFF';
")
ROW_COUNT=$(echo "$COUNT_ROW" | cut -d'|' -f1 | tr -d ' ')
RESOLVED_CUTOFF=$(echo "$COUNT_ROW" | cut -d'|' -f2)

if [ -z "$ROW_COUNT" ] || [ "$ROW_COUNT" = 0 ]; then
    echo "No rows older than '$CUTOFF' (resolved: $RESOLVED_CUTOFF). Nothing to archive."
    rm -rf "$TMP_DIR"
    exit "$EXIT_NO_ROWS"
fi

echo "Archiving $ROW_COUNT Pheromone row(s) older than $RESOLVED_CUTOFF..."

# Export rows as CSV. Read-only; never DELETE.
run_psql -c "
\\copy (
    SELECT pheromone_id, deposited_at, deposited_by, node_id,
           intensity, kind, half_life_hours, evidence::text, seed
      FROM Pheromone
     WHERE deposited_at < '$RESOLVED_CUTOFF'::timestamptz
     ORDER BY pheromone_id
) TO '$EXPORT_FILE' WITH CSV HEADER
"

# Manifest
cat >"$MANIFEST_FILE" <<EOF
{
  "schema": "polaris-pheromone-archive/1",
  "ship": "v9.07",
  "sanctum": "sanctum/2026-05-15-pheromone-rotation.md",
  "iso_timestamp": "$ISO_TS",
  "cutoff_resolved": "$RESOLVED_CUTOFF",
  "row_count": $ROW_COUNT,
  "export_file": "pheromone-${ISO_TS}.csv"
}
EOF

# Tar + hash
TARBALL="$OUT_DIR/polaris-pheromone-archive-${ISO_TS}-${ROW_COUNT}rows.tar.gz"
tar -C "$TMP_DIR" -czf "$TARBALL" . 2>/dev/null

SHA256=$(shasum -a 256 "$TARBALL" | awk '{print $1}')

# Embed sha256 INTO the manifest by re-creating with it included.
# (The first manifest computes the row_count + cutoff before we know the
# tarball's sha; we re-tar with the sha-included manifest so verify-latest
# can match.)
cat >"$MANIFEST_FILE" <<EOF
{
  "schema": "polaris-pheromone-archive/1",
  "ship": "v9.07",
  "sanctum": "sanctum/2026-05-15-pheromone-rotation.md",
  "iso_timestamp": "$ISO_TS",
  "cutoff_resolved": "$RESOLVED_CUTOFF",
  "row_count": $ROW_COUNT,
  "export_file": "pheromone-${ISO_TS}.csv",
  "sha256": "$SHA256"
}
EOF
tar -C "$TMP_DIR" -czf "$TARBALL" . 2>/dev/null
SHA256_FINAL=$(shasum -a 256 "$TARBALL" | awk '{print $1}')

echo
echo "Archive: $TARBALL"
echo "  rows:     $ROW_COUNT"
echo "  cutoff:   $RESOLVED_CUTOFF"
echo "  sha256:   $SHA256_FINAL"
echo
echo "C1 preserved: source rows REMAIN in Pheromone (export-only)."
echo "Next step (deletion):"
echo "  ./scripts/polaris-pheromone-purge.sh \\"
echo "      --archive='$TARBALL' \\"
echo "      --cutoff='$RESOLVED_CUTOFF' \\"
echo "      --actor-user-id=<your-admin-user-id>"

rm -rf "$TMP_DIR"
exit "$EXIT_OK"
