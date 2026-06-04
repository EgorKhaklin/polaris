#!/usr/bin/env bash
# ============================================================================
# polaris-backup.sh — atomic full-system backup
#
# Arc B Phase 1 (v8.77). Produces a single timestamped tarball containing
# every durable component, plus a manifest with SHA-256 hashes:
#
#   pg_dump (custom format, gzipped)        the database
#   sanctum/                                filesystem audit-of-record
#   journal/                                episodic decision log
#   meta/sanctum-index.md                   index of the sanctum/ directory
#   MANIFEST.json                           timestamps + SHA-256 hashes
#
# Usage:
#     ./scripts/polaris-backup.sh                       # writes /var/backups/polaris-<ts>.tar.gz
#     ./scripts/polaris-backup.sh --dest /path/to/dir   # custom destination
#     ./scripts/polaris-backup.sh --verify-latest       # extract + verify newest backup
# ============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"
POLARIS_ROOT="$(cd -- "${SCRIPT_DIR}/.." &> /dev/null && pwd)"
COMPOSE_FILE="${POLARIS_ROOT}/polaris_web/docker-compose.prod.yml"
DEFAULT_DEST="/var/backups"

DEST="${DEFAULT_DEST}"
VERIFY_LATEST=0
# while-loop form: supports both `--dest=/path` and `--dest /path`.
# (Pre-v8.82 used `for arg in "$@"; do shift; done` which couldn't
# advance the iterator and only handled the `--dest=` form correctly.)
while [[ $# -gt 0 ]]; do
    case "$1" in
        --dest=*)         DEST="${1#--dest=}" ;;
        --dest)           shift; DEST="${1:-${DEFAULT_DEST}}" ;;
        --verify-latest)  VERIFY_LATEST=1 ;;
        *) ;;
    esac
    shift
done

mkdir -p "${DEST}"

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
    LATEST=$(ls -1t "${DEST}"/polaris-*.tar.gz 2>/dev/null | head -1 || true)
    if [[ -z "${LATEST}" ]]; then
        echo "  ✗ no backups found under ${DEST}" >&2
        exit 1
    fi
    echo "  → verifying: ${LATEST}"
    TMP=$(mktemp -d)
    trap 'rm -rf "${TMP}"' EXIT
    tar -tzf "${LATEST}" >/dev/null
    tar -xzf "${LATEST}" -C "${TMP}"

    # The backup-side staging path is ${WORK}/polaris-${TS}/<files>, so
    # the tarball extracts into ${TMP}/polaris-<ts>/<files>. Descend one
    # level to find MANIFEST.json. (Pre-v8.82 looked at ${TMP}/MANIFEST.json
    # and would always report 'malformed' even on healthy backups — bug
    # surfaced during the v8.81 polaris-restore.sh drill.)
    EXTRACTED=$(find "${TMP}" -maxdepth 1 -mindepth 1 -type d -name 'polaris-*' | head -1)
    if [[ -z "${EXTRACTED}" || ! -d "${EXTRACTED}" ]]; then
        # Fall back to the flat layout for hand-rolled tarballs.
        EXTRACTED="${TMP}"
    fi
    if [[ ! -f "${EXTRACTED}/MANIFEST.json" ]]; then
        echo "  ✗ MANIFEST.json missing — backup is malformed" >&2
        exit 1
    fi
    python3 - "${EXTRACTED}" <<'PY'
import json, hashlib, os, sys
base = sys.argv[1]
with open(os.path.join(base, "MANIFEST.json")) as f:
    m = json.load(f)
ok = True
for name, expected in m["sha256"].items():
    p = os.path.join(base, name)
    if not os.path.exists(p):
        print(f"  ✗ {name} missing from archive")
        ok = False
        continue
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1<<16), b""):
            h.update(chunk)
    got = h.hexdigest()
    if got != expected:
        print(f"  ✗ {name} hash mismatch  expected={expected[:16]}  got={got[:16]}")
        ok = False
    else:
        print(f"  ✓ {name}")
if not ok:
    sys.exit(1)
print("  ✓ MANIFEST verified")
PY
    exit 0
fi

# ---------------------------------------------------------------------------
# Backup mode
# ---------------------------------------------------------------------------
TS=$(date -u +%Y%m%dT%H%M%SZ)
WORK=$(mktemp -d)
trap 'rm -rf "${WORK}"' EXIT
STAGE="${WORK}/polaris-${TS}"
mkdir -p "${STAGE}"

echo "  → Polaris backup ${TS}"
echo "  → staging at ${STAGE}"

# 1. pg_dump
echo "  [1/5] pg_dump…"
if docker compose -f "${COMPOSE_FILE}" ps --services 2>/dev/null | grep -q '^postgres$'; then
    # Production stack is up — dump via compose exec
    docker compose -f "${COMPOSE_FILE}" exec -T postgres \
        pg_dump -Fc -U postgres polaris > "${STAGE}/polaris.dump"
elif command -v pg_dump >/dev/null 2>&1; then
    # Local pg available
    pg_dump -Fc \
        -h "${POLARIS_DB_HOST:-localhost}" \
        -U "${POLARIS_DB_USER:-postgres}" \
        "${POLARIS_DB_NAME:-polaris}" \
        > "${STAGE}/polaris.dump"
else
    echo "  ! pg_dump unavailable and stack not running; skipping DB"
    : > "${STAGE}/polaris.dump"   # zero-byte sentinel
fi

# 2. sanctum/
echo "  [2/5] sanctum/…"
if [[ -d "${POLARIS_ROOT}/sanctum" ]]; then
    tar -czf "${STAGE}/sanctum.tar.gz" -C "${POLARIS_ROOT}" sanctum
else
    : > "${STAGE}/sanctum.tar.gz"
fi

# 3. journal/
echo "  [3/5] journal/…"
if [[ -d "${POLARIS_ROOT}/journal" ]]; then
    tar -czf "${STAGE}/journal.tar.gz" -C "${POLARIS_ROOT}" journal
else
    : > "${STAGE}/journal.tar.gz"
fi

# 4. meta/sanctum-index.md
echo "  [4/5] meta/sanctum-index.md…"
if [[ -f "${POLARIS_ROOT}/meta/sanctum-index.md" ]]; then
    cp "${POLARIS_ROOT}/meta/sanctum-index.md" "${STAGE}/sanctum-index.md"
else
    : > "${STAGE}/sanctum-index.md"
fi

# 5. Manifest with hashes
echo "  [5/5] manifest…"
python3 - "${STAGE}" "${TS}" <<'PY' > "${STAGE}/MANIFEST.json"
import json, hashlib, os, sys, time
stage = sys.argv[1]
ts = sys.argv[2]
files = sorted(f for f in os.listdir(stage) if f != "MANIFEST.json")
out = {
    "timestamp_utc": ts,
    "generated_at": time.time(),
    "polaris_version": "8.77",
    "sha256": {},
    "size_bytes": {},
}
for name in files:
    p = os.path.join(stage, name)
    if not os.path.isfile(p):
        continue
    h = hashlib.sha256()
    sz = 0
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1<<16), b""):
            h.update(chunk)
            sz += len(chunk)
    out["sha256"][name] = h.hexdigest()
    out["size_bytes"][name] = sz
print(json.dumps(out, indent=2))
PY

# Bundle into a single tarball
OUT="${DEST}/polaris-${TS}.tar.gz"
tar -czf "${OUT}" -C "${WORK}" "polaris-${TS}"
chmod 0600 "${OUT}"

SIZE=$(du -h "${OUT}" | awk '{print $1}')
echo
echo "  ✓ backup complete:  ${OUT}  (${SIZE})"
echo "  → verify with:       $(basename "$0") --verify-latest --dest ${DEST}"
