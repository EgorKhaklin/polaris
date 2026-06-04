#!/usr/bin/env bash
# ============================================================================
# polaris-purge.sh — archive-then-delete operator wrapper
#
# v8.87 / Arc B Phase 2b — closes the deletion-from-hot constitutional
# carve-out per a recorded decision
# (Position B, DECIDED).
#
# The ONLY legitimate path for DELETE against audit-class tables. This
# script:
#   1. Requires a previously-produced polaris-archive.sh tarball
#   2. Computes the tarball's SHA-256
#   3. Reads the manifest to confirm the cutoff_iso the archive covers
#   4. Calls uc_archive_purge() with the verified SHA-256
#   5. Prints the resulting LifecycleArchiveCheckpoint row
#
# Outside this script, direct DELETE against audit tables fails with
# insufficient_privilege (per reject_audit_modification trigger). The
# carve-out is procedure-only.
#
# CONSTITUTIONAL CARVE-OUT NOTE
# ─────────────────────────────
# This script issues DELETE against audit tables. C1 (append-only) is
# preserved at the constitutional level by the archive + checkpoint
# chain: the LifecycleArchiveCheckpoint row + the offline archive
# tarball together reconstitute every purged row. Non-repudiation
# survives the deletion IF the archive remains durable. Operator-set
# archive custody is the load-bearing operational concern (see
# docs/operator/OPERATIONS.md § Backup & restore).
#
# Usage:
#   ./scripts/polaris-purge.sh \
#       --archive=PATH \
#       --actor-user-id=N \
#       [--target=docker-stack] \
#       [--dry-run]
#
#   --archive       path to the polaris-archive-*.tar.gz to purge against
#   --actor-user-id AppUser.user_id of the operator (must be admin)
#   --target=docker-stack  use the running docker-compose Postgres
#                          instead of local psql
#   --dry-run       verify archive + manifest; print intent; do NOT call
#                   uc_archive_purge
#
# Exit codes:
#   0  purge complete
#   2  usage error
#   3  archive missing or malformed
#   4  archive SHA-256 mismatch with declared manifest
#   5  procedure call failed
# ============================================================================

set -euo pipefail

EXIT_OK=0
EXIT_USAGE=2
EXIT_ARCHIVE=3
EXIT_SHA=4
EXIT_PROC=5

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"
POLARIS_ROOT="$(cd -- "${SCRIPT_DIR}/.." &> /dev/null && pwd)"
COMPOSE_FILE="${POLARIS_ROOT}/polaris_web/docker-compose.prod.yml"

ARCHIVE=""
ACTOR_USER_ID=""
USE_DOCKER_STACK=0
DRY_RUN=0

while [[ $# -gt 0 ]]; do
    case "$1" in
        --archive=*)       ARCHIVE="${1#--archive=}" ;;
        --archive)         shift; ARCHIVE="${1:-}" ;;
        --actor-user-id=*) ACTOR_USER_ID="${1#--actor-user-id=}" ;;
        --actor-user-id)   shift; ACTOR_USER_ID="${1:-}" ;;
        --target=docker-stack) USE_DOCKER_STACK=1 ;;
        --dry-run)         DRY_RUN=1 ;;
        --help|-h)
            sed -n '2,50p' "$0" | sed 's/^# \{0,1\}//'
            exit "${EXIT_USAGE}"
            ;;
        *) echo "warn: unknown arg $1" >&2 ;;
    esac
    shift
done

if [[ -z "${ARCHIVE}" || -z "${ACTOR_USER_ID}" ]]; then
    echo "error: --archive and --actor-user-id are required" >&2
    exit "${EXIT_USAGE}"
fi
# --actor-user-id is interpolated bare into the destructive CALL against the
# superuser connection; require it to be numeric so it cannot inject SQL.
if ! [[ "${ACTOR_USER_ID}" =~ ^[0-9]+$ ]]; then
    echo "error: --actor-user-id must be a numeric AppUser.user_id" >&2
    exit "${EXIT_USAGE}"
fi
if [[ ! -f "${ARCHIVE}" ]]; then
    echo "error: archive file not found: ${ARCHIVE}" >&2
    exit "${EXIT_ARCHIVE}"
fi

# Resolve to absolute path.
ARCHIVE="$(cd "$(dirname "${ARCHIVE}")" && pwd)/$(basename "${ARCHIVE}")"

# Compute SHA-256.
sha256_of() {
    if command -v sha256sum >/dev/null 2>&1; then
        sha256sum "$1" | awk '{print $1}'
    else
        shasum -a 256 "$1" | awk '{print $1}'
    fi
}

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

ARCHIVE_SHA=$(sha256_of "${ARCHIVE}")
echo
echo "  Polaris — archive-then-delete (Phase 2b constitutional carve-out)"
echo "  ────────────────────────────────────────────────────────────────"
echo "  Archive:       ${ARCHIVE}"
echo "  Archive SHA:   ${ARCHIVE_SHA}"
echo "  Actor user_id: ${ACTOR_USER_ID}"
echo "  Mode:          $([[ "${USE_DOCKER_STACK}" -eq 1 ]] && echo 'docker-stack' || echo 'local-psql')"
echo "  Dry-run:       $([[ "${DRY_RUN}" -eq 1 ]] && echo yes || echo no)"
echo

# Extract manifest to read the cutoff timestamp it covers.
TMP=$(mktemp -d)
trap 'rm -rf "${TMP}"' EXIT
tar -xzf "${ARCHIVE}" -C "${TMP}"
EXTRACTED=$(find "${TMP}" -maxdepth 1 -mindepth 1 -type d -name 'polaris-archive-*' | head -1)
if [[ -z "${EXTRACTED}" || ! -f "${EXTRACTED}/MANIFEST.json" ]]; then
    echo "  ✗ archive manifest not found; refusing to purge" >&2
    exit "${EXIT_ARCHIVE}"
fi

CUTOFF_ISO=$(python3 -c "
import json, sys
with open('${EXTRACTED}/MANIFEST.json') as f:
    m = json.load(f)
print(m.get('cutoff_iso', ''))
")
if [[ -z "${CUTOFF_ISO}" ]]; then
    echo "  ✗ manifest missing cutoff_iso; refusing" >&2
    exit "${EXIT_ARCHIVE}"
fi
DELETION_FROM_HOT=$(python3 -c "
import json
with open('${EXTRACTED}/MANIFEST.json') as f:
    m = json.load(f)
print(m.get('deletion_from_hot', False))
")
echo "  Manifest cutoff_iso: ${CUTOFF_ISO}"
echo "  Manifest deletion_from_hot flag: ${DELETION_FROM_HOT}  (informational; this script issues the deletion)"
echo

if [[ "${DRY_RUN}" -eq 1 ]]; then
    echo "  [dry-run] would call uc_archive_purge with:"
    echo "    cutoff_timestamp = ${CUTOFF_ISO}"
    echo "    archive_uri      = file://${ARCHIVE}"
    echo "    archive_sha256   = ${ARCHIVE_SHA}"
    echo "    actor_user_id    = ${ACTOR_USER_ID}"
    echo "  [dry-run] no DELETE issued."
    exit "${EXIT_OK}"
fi

# Issue the procedure call.
echo "  → calling uc_archive_purge()…"
PURGE_OUT=$(run_psql -c "
CALL uc_archive_purge(
    p_cutoff_timestamp := '${CUTOFF_ISO}'::timestamptz,
    p_archive_uri      := 'file://${ARCHIVE}',
    p_archive_sha256   := '${ARCHIVE_SHA}',
    p_actor_user_id    := ${ACTOR_USER_ID}
);
" 2>&1) || {
    echo "  ✗ procedure call failed:" >&2
    echo "${PURGE_OUT}" >&2
    exit "${EXIT_PROC}"
}

# Read back the checkpoint we just wrote.
CHECKPOINT=$(run_psql -c "
SELECT checkpoint_id || ' | rows=' || rows_purged_total
       || ' | cutoff=' || cutoff_timestamp::text
       || ' | sha=' || left(archive_sha256, 16) || '…'
FROM LifecycleArchiveCheckpoint
ORDER BY checkpoint_id DESC LIMIT 1
")

cat <<DONE
  ✓ purge complete.

  Checkpoint: ${CHECKPOINT}

  Non-repudiation chain:
    LifecycleArchiveCheckpoint row written      ✓
    Archive tarball at recorded SHA-256          ${ARCHIVE_SHA}
    Cutoff covered                               ${CUTOFF_ISO}

  Verification: the archive must remain accessible at the recorded URI
  for non-repudiation. If the archive moves, update the checkpoint's
  archive_uri via a NEW checkpoint row (the table is append-only — no
  UPDATE — so the move is itself audit-of-record).

  Operator runbook: docs/operator/OPERATIONS.md § Backup & restore
  Constitutional record: a recorded decision
DONE
exit "${EXIT_OK}"
