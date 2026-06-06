#!/usr/bin/env bash
# ============================================================================
# polaris-generate-secrets.sh — one-time secret material generation
#
# Arc B Phase 1 (v8.77). Generates the file-mounted secrets the production
# docker-compose stack expects under polaris_web/secrets/. Refuses to
# overwrite existing files (rotation lives in polaris-rotate-secret.sh).
#
# Files generated (all mode 0600):
#   secrets/polaris_secret_key          — Flask session signing key (64 hex)
#   secrets/polaris_db_password         — Postgres polaris_app password (32+ chars)
#   secrets/polaris_db_root_password    — Postgres superuser password (32+ chars)
#
# G28 enforced: nothing here echoes secrets to stdout. The file mode is
# verified after write.
# ============================================================================

set -euo pipefail

# Resolve the polaris root from this script's location.
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"
POLARIS_ROOT="$(cd -- "${SCRIPT_DIR}/.." &> /dev/null && pwd)"
SECRETS_DIR="${POLARIS_ROOT}/polaris_web/secrets"

mkdir -p "${SECRETS_DIR}"
chmod 0700 "${SECRETS_DIR}"

# Pick a random-source command in order of preference.
gen_hex() {
    local nbytes="$1"
    if command -v openssl >/dev/null 2>&1; then
        openssl rand -hex "${nbytes}"
    elif command -v python3 >/dev/null 2>&1; then
        python3 -c "import secrets; print(secrets.token_hex(${nbytes}))"
    else
        # Fall back to /dev/urandom + hex via xxd or od.
        if command -v xxd >/dev/null 2>&1; then
            head -c "${nbytes}" /dev/urandom | xxd -p -c 1024
        else
            head -c "${nbytes}" /dev/urandom | od -An -tx1 | tr -d ' \n'
        fi
    fi
}

write_secret_if_missing() {
    local name="$1"
    local hex_bytes="$2"
    local target="${SECRETS_DIR}/${name}"

    if [[ -e "${target}" ]]; then
        echo "  ✓ ${name}  (exists; not overwriting — use polaris-rotate-secret.sh to rotate)"
        return 0
    fi

    # Use umask so the file is born 0600 even before chmod.
    ( umask 0177 && gen_hex "${hex_bytes}" > "${target}" )
    chmod 0600 "${target}"

    # Verify mode actually took.
    local mode
    if mode=$(stat -f '%Lp' "${target}" 2>/dev/null); then :;
    else mode=$(stat -c '%a' "${target}" 2>/dev/null || echo "?"); fi
    if [[ "${mode}" != "600" ]]; then
        echo "  ✗ ${name}  (mode is ${mode}, expected 600 — fix manually)" >&2
        return 1
    fi
    echo "  ✓ ${name}  (generated; mode 0600)"
}

# v9.116 — the ML-DSA-65 signing keypair. Unlike the hex secrets, this needs
# liboqs (oqs) to mint. Prefer a local oqs; otherwise mint inside the built
# polaris-app:prod image (which ships liboqs). If neither is available, skip with
# a clear message — operators custodying key material in an HSM/KMS supply their
# own loader instead (that custody is operator-gated).
write_signing_key_if_missing() {
    local name="polaris_signing_key"
    local target="${SECRETS_DIR}/${name}"
    if [[ -e "${target}" ]]; then
        echo "  ✓ ${name}  (exists; not overwriting — use polaris-rotate-secret.sh to rotate)"
        return 0
    fi
    local json=""
    if python3 -c "import oqs" >/dev/null 2>&1; then
        json=$(python3 -c "import sys; sys.path.insert(0, '${POLARIS_ROOT}/polaris_web'); import pqc_signing, json; print(json.dumps(pqc_signing.generate_keypair()))" 2>/dev/null || true)
    elif command -v docker >/dev/null 2>&1 && docker image inspect polaris-app:prod >/dev/null 2>&1; then
        json=$(docker run --rm polaris-app:prod python -c "import pqc_signing, json; print(json.dumps(pqc_signing.generate_keypair()))" 2>/dev/null || true)
    fi
    if [[ -z "${json}" ]]; then
        echo "  ! ${name}  (NOT generated — needs liboqs locally OR the built polaris-app:prod image)"
        echo "      Build the prod image first, or 'pip install liboqs-python', then re-run." >&2
        echo "      (HSM/KMS custody: supply your own ML-DSA-65 key loader instead.)" >&2
        return 0
    fi
    ( umask 0177 && printf '%s\n' "${json}" > "${target}" )
    chmod 0600 "${target}"
    echo "  ✓ ${name}  (ML-DSA-65 keypair generated; mode 0600)"
}

# v9.121 — a self-signed TLS server cert for Postgres, so the app<->DB hop is
# encrypted (sslmode=require). The cert is mounted into the postgres container,
# which copies it into its data dir and enables ssl at init (docker-init.sh).
# CN=postgres (the in-network service name) so it is verify-full-ready if the
# operator later supplies a real CA; until then 'require' encrypts without cert
# verification. Operators with a managed-Postgres CA replace this cert.
write_postgres_cert_if_missing() {
    local crt="${SECRETS_DIR}/postgres_server.crt"
    local key="${SECRETS_DIR}/postgres_server.key"
    if [[ -f "${crt}" && -f "${key}" ]]; then
        echo "  ✓ postgres_server.crt/.key  (exist; not overwriting)"
        return 0
    fi
    if ! command -v openssl >/dev/null 2>&1; then
        echo "  ! postgres_server.{crt,key}  (NOT generated — needs openssl; set" >&2
        echo "      POLARIS_DB_SSLMODE=prefer to run without TLS, or supply your own cert)" >&2
        return 0
    fi
    ( umask 0077 && openssl req -new -x509 -days 825 -nodes \
        -subj "/CN=postgres" -out "${crt}" -keyout "${key}" >/dev/null 2>&1 )
    chmod 0644 "${crt}"
    chmod 0600 "${key}"
    echo "  ✓ postgres_server.crt/.key  (self-signed TLS cert generated; key 0600)"
}

# v9.131 — a STABLE self-signed cert pgbouncer presents to the app, so the app
# can PIN it (sslmode=verify-ca, sslrootcert=this cert) and reject a MITM that
# presents a different cert on the app<->pgbouncer hop. Stable (not regenerated
# per pgbouncer start) precisely so it is pinnable. BOTH files are 0644: the
# non-root pgbouncer container user must read the KEY across a plain Linux bind
# mount (where perms are not uid-mapped), and the cert is public. The host-side
# protection is the 0700 SECRETS_DIR above — a 0644 file inside an owner-only
# directory is still reachable only by the owner; the dir, not the file mode, is
# the boundary (the postgres key is 0600 only because root copies+chowns it into
# the container, a path pgbouncer does not have).
write_pgbouncer_cert_if_missing() {
    local crt="${SECRETS_DIR}/pgbouncer_server.crt"
    local key="${SECRETS_DIR}/pgbouncer_server.key"
    if [[ -f "${crt}" && -f "${key}" ]]; then
        echo "  ✓ pgbouncer_server.crt/.key  (exist; not overwriting)"
        return 0
    fi
    if ! command -v openssl >/dev/null 2>&1; then
        echo "  ! pgbouncer_server.{crt,key}  (NOT generated — needs openssl; the app<->pgbouncer" >&2
        echo "      hop falls back to 'require' without a pinnable cert)" >&2
        return 0
    fi
    ( umask 0077 && openssl req -new -x509 -days 825 -nodes \
        -subj "/CN=pgbouncer" -out "${crt}" -keyout "${key}" >/dev/null 2>&1 )
    chmod 0644 "${crt}"
    chmod 0644 "${key}"   # readable by the non-root pgbouncer user; 0700 dir gates host access
    echo "  ✓ pgbouncer_server.crt/.key  (self-signed TLS cert generated; in the 0700 secrets dir)"
}

cat <<'BANNER'

  Polaris — secret material generator
  ───────────────────────────────────
  Generating file-mounted secrets under polaris_web/secrets/.
  This script will NOT overwrite existing secrets.

BANNER

write_secret_if_missing polaris_secret_key       32
write_secret_if_missing polaris_db_password      24
write_secret_if_missing polaris_db_root_password 24
# v9.126 — the streaming-replication role password. Mounted at the postgres
# container so docker-init.sh creates the polaris_replicator role and a standby
# can clone with `pg_basebackup` (see docs/operator/FAILOVER.md). The standby
# host itself is operator-supplied.
write_secret_if_missing polaris_replicator_password 24
write_signing_key_if_missing
write_postgres_cert_if_missing
write_pgbouncer_cert_if_missing

cat <<BANNER

  Done.

  Next steps:
    1. export POLARIS_DOMAIN=<your domain>
    2. ./scripts/polaris-deploy.sh prod
    3. curl -fsS https://\${POLARIS_DOMAIN}/api/health | jq .

  Rotation:    ./scripts/polaris-rotate-secret.sh <name>
  Threat model & rotation cadence:  docs/operator/SECRETS.md

BANNER
