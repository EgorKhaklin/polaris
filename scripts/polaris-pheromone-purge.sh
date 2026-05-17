#!/usr/bin/env bash
# ============================================================================
# polaris-pheromone-purge.sh — archive-then-delete operator wrapper for
#                              the Pheromone table
#
# v9.07 / Wave 3 / D5-impl — closes the deletion-from-hot constitutional
# carve-out for Pheromone per
# sanctum/2026-05-15-pheromone-rotation.md (Position A).
#
# The ONLY legitimate path for DELETE against the Pheromone table. This
# script:
#   1. Requires a previously-produced polaris-pheromone-archive.sh tarball
#   2. Computes the tarball's SHA-256
#   3. Reads the manifest to confirm the cutoff_resolved the archive
#      covers
#   4. Calls uc_pheromone_archive_purge() with the verified SHA-256 +
#      operator's user_id
#   5. Prints the resulting LifecyclePheromoneCheckpoint row
#
# Outside this script, direct DELETE against Pheromone fails with
# insufficient_privilege (per reject_pheromone_modification trigger,
# v9.07 / D5-impl). The carve-out is procedure-only.
#
# CONSTITUTIONAL CARVE-OUT NOTE
# ─────────────────────────────
# This script issues DELETE against an audit-class table. C1 (append-
# only) is preserved at the constitutional level by the archive +
# checkpoint chain: the LifecyclePheromoneCheckpoint row + the offline
# archive tarball together reconstitute every purged row. Non-
# repudiation survives the deletion IF the archive remains durable.
# Operator-set archive custody is the load-bearing operational concern
# (see docs/operator/OPERATIONS.md § Pheromone archive + purge).
#
# Usage:
#   ./scripts/polaris-pheromone-purge.sh \
#       --archive=PATH \
#       --cutoff=ISO_TIMESTAMP \
#       --actor-user-id=N \
#       [--target=docker-stack] \
#       [--dry-run]
#
#   --archive          path to polaris-pheromone-archive-*.tar.gz
#   --cutoff           timestamp the archive covers (matches manifest)
#   --actor-user-id    AppUser.user_id (must be admin)
#   --target=docker-stack  use the running docker-compose Postgres
#   --dry-run          verify archive + manifest; print intent; do NOT
#                      call uc_pheromone_archive_purge
#
# Exit codes:
#   0  purge complete
#   2  usage error
#   3  archive missing or malformed
#   4  archive SHA-256 mismatch with declared manifest
#   5  procedure call failed (DB error)
#   6  cutoff arg mismatches manifest
# ============================================================================

set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"

ARCHIVE=""
CUTOFF=""
ACTOR_USER_ID=""
TARGET=local
DRY_RUN=0

EXIT_OK=0
EXIT_USAGE=2
EXIT_ARCHIVE_BAD=3
EXIT_SHA_MISMATCH=4
EXIT_PROC_FAIL=5
EXIT_CUTOFF_MISMATCH=6

usage() {
    sed -n '2,52p' "$0" | sed 's/^# \?//'
    exit "$EXIT_USAGE"
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --archive=*)         ARCHIVE="${1#*=}"; shift ;;
        --archive)           ARCHIVE="$2"; shift 2 ;;
        --cutoff=*)          CUTOFF="${1#*=}"; shift ;;
        --cutoff)            CUTOFF="$2"; shift 2 ;;
        --actor-user-id=*)   ACTOR_USER_ID="${1#*=}"; shift ;;
        --actor-user-id)     ACTOR_USER_ID="$2"; shift 2 ;;
        --target=docker-stack) TARGET=docker-stack; shift ;;
        --dry-run)           DRY_RUN=1; shift ;;
        -h|--help)           usage ;;
        *)
            echo "unknown arg: $1" >&2
            usage
            ;;
    esac
done

if [ -z "$ARCHIVE" ] || [ -z "$CUTOFF" ] || [ -z "$ACTOR_USER_ID" ]; then
    echo "missing required arg" >&2
    usage
fi

if [ ! -f "$ARCHIVE" ]; then
    echo "archive not found: $ARCHIVE" >&2
    exit "$EXIT_ARCHIVE_BAD"
fi

# Verify the SHA-256 against the manifest BEFORE issuing DELETE
TMP=$(mktemp -d)
tar -xzf "$ARCHIVE" -C "$TMP"
MANIFEST=$(find "$TMP" -name MANIFEST.json -type f | head -1)
if [ -z "$MANIFEST" ] || [ ! -f "$MANIFEST" ]; then
    echo "MANIFEST.json not found inside $ARCHIVE" >&2
    rm -rf "$TMP"
    exit "$EXIT_ARCHIVE_BAD"
fi

DECLARED_SHA=$(grep -oE '"sha256":\s*"[a-f0-9]{64}"' "$MANIFEST" \
               | head -1 | grep -oE '[a-f0-9]{64}')
DECLARED_CUTOFF=$(grep -oE '"cutoff_resolved":\s*"[^"]+"' "$MANIFEST" \
                 | head -1 | sed -E 's/.*:\s*"([^"]+)".*/\1/')
ROW_COUNT=$(grep -oE '"row_count":\s*[0-9]+' "$MANIFEST" \
            | head -1 | grep -oE '[0-9]+')

if [ -z "$DECLARED_SHA" ] || [ -z "$DECLARED_CUTOFF" ]; then
    echo "MANIFEST.json malformed (missing sha256 or cutoff_resolved)" >&2
    rm -rf "$TMP"
    exit "$EXIT_ARCHIVE_BAD"
fi

ACTUAL_SHA=$(shasum -a 256 "$ARCHIVE" | awk '{print $1}')
if [ "$DECLARED_SHA" != "$ACTUAL_SHA" ]; then
    echo "✗ SHA-256 MISMATCH (refusing to purge)" >&2
    echo "  declared: $DECLARED_SHA" >&2
    echo "  actual:   $ACTUAL_SHA" >&2
    rm -rf "$TMP"
    exit "$EXIT_SHA_MISMATCH"
fi

# Cutoff arg must match manifest (operator-supplied vs archive-declared)
if [ "$CUTOFF" != "$DECLARED_CUTOFF" ]; then
    echo "✗ cutoff arg ($CUTOFF) mismatches manifest cutoff ($DECLARED_CUTOFF)" >&2
    rm -rf "$TMP"
    exit "$EXIT_CUTOFF_MISMATCH"
fi
rm -rf "$TMP"

echo "Archive verified:"
echo "  $ARCHIVE"
echo "  sha256: $ACTUAL_SHA"
echo "  cutoff: $CUTOFF"
echo "  rows in archive: $ROW_COUNT"
echo "  actor user_id:   $ACTOR_USER_ID"
echo

if [ "$DRY_RUN" = 1 ]; then
    echo "DRY RUN — uc_pheromone_archive_purge() NOT called."
    echo "Re-run without --dry-run to execute the purge."
    exit "$EXIT_OK"
fi

# Resolve the archive_uri to its absolute path for non-repudiation
ARCHIVE_URI="file://$(cd "$(dirname "$ARCHIVE")" && pwd)/$(basename "$ARCHIVE")"

# Locate psql
PSQL_BIN=""
for cand in \
    "/opt/homebrew/opt/postgresql@16/bin/psql" \
    "/usr/local/opt/postgresql@16/bin/psql" \
    "$(command -v psql 2>/dev/null)" \
; do
    if [ -x "$cand" ]; then PSQL_BIN="$cand"; break; fi
done

if [ -z "$PSQL_BIN" ]; then
    echo "polaris-pheromone-purge: no psql binary found" >&2
    exit "$EXIT_PROC_FAIL"
fi

export POLARIS_DB_HOST="${POLARIS_DB_HOST:-localhost}"
export POLARIS_DB_NAME="${POLARIS_DB_NAME:-polaris_test}"
export POLARIS_DB_USER="${POLARIS_DB_USER:-polaris_app}"
export POLARIS_DB_PASSWORD="${POLARIS_DB_PASSWORD:-polaris_dev_password}"

# Call the procedure inside one txn (BEGIN..COMMIT is implicit per
# psql's CALL). The procedure internally SET LOCALs the carve-out GUC.
echo "Calling uc_pheromone_archive_purge()..."
PGPASSWORD="$POLARIS_DB_PASSWORD" "$PSQL_BIN" \
    -h "$POLARIS_DB_HOST" \
    -U "$POLARIS_DB_USER" \
    -d "$POLARIS_DB_NAME" \
    -v ON_ERROR_STOP=1 \
    -c "CALL uc_pheromone_archive_purge(
            '${CUTOFF}'::timestamptz,
            '${ARCHIVE_URI}',
            '${ACTUAL_SHA}',
            ${ACTOR_USER_ID}
        );" \
    -c "SELECT * FROM LifecyclePheromoneCheckpoint
         ORDER BY checkpoint_id DESC LIMIT 1;" \
    || { echo "uc_pheromone_archive_purge failed" >&2; exit "$EXIT_PROC_FAIL"; }

echo
echo "✓ Purge complete. Pheromone rows < $CUTOFF deleted; "\
"checkpoint row written; carve-out GUC closed at COMMIT."
exit "$EXIT_OK"
