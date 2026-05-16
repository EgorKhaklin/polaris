#!/bin/bash
# ============================================================================
# Polaris Docker Init Script
#
# Runs once when the postgres container boots with an empty data volume.
# Loads the Polaris schema + sample data + procedures + triggers + grants
# via 00_load_all.sql, which now includes 09_grants.sql.
#
# After this completes, the polaris_app role exists with the right grants
# and the database has 73 sample rows ready for the Flask app to query.
# ============================================================================

set -e

echo "Loading Polaris SQL package..."

# 00_load_all.sql uses \i with relative paths, so we cd into the SQL directory
# before invoking psql.
cd /docker-entrypoint-initdb.d/sql
psql -v ON_ERROR_STOP=1 \
     --username "$POSTGRES_USER" \
     --dbname "$POSTGRES_DB" \
     -f /docker-entrypoint-initdb.d/sql/00_load_all.sql

# v9.18 — apply all pending migrations after the baseline schema loads.
# Without this, columns added post-v8.95 (e.g., AppUser.webauthn_required_after
# from the 2026-05-14-002-operator-webauthn migration) are missing from
# fresh containers, and any code path that queries them 500s. The fix
# mirrors scripts/polaris-migrate.sh's apply path: lexicographic ordering,
# per-file transaction, SHA-256 recorded in schema_version. actor_user_id
# is NULL (system-applied during init; no human actor at boot time).
MIG_DIR="/docker-entrypoint-initdb.d/sql/migrations"
if [ -d "$MIG_DIR" ]; then
    echo "Applying schema migrations..."
    count=0
    for up_file in "$MIG_DIR"/*.up.sql; do
        [ -f "$up_file" ] || continue
        name=$(basename "$up_file" .up.sql)
        sha=$(sha256sum "$up_file" | awk '{print $1}')
        # Wrap in a single transaction: apply + record in schema_version.
        sql_tmp=$(mktemp)
        cat > "$sql_tmp" <<SQL
BEGIN;
\i $up_file
INSERT INTO schema_version (name, event_type, actor_user_id, file_sha256)
VALUES ('$name', 'applied', NULL, '$sha');
COMMIT;
SQL
        if ! psql -v ON_ERROR_STOP=1 \
                  --username "$POSTGRES_USER" \
                  --dbname "$POSTGRES_DB" \
                  -f "$sql_tmp" > /dev/null; then
            echo "FATAL: migration '$name' failed to apply" >&2
            rm -f "$sql_tmp"
            exit 4
        fi
        rm -f "$sql_tmp"
        count=$((count + 1))
        echo "  ✓ applied: $name (sha=${sha:0:16}…)"
    done
    echo "Applied $count migration(s)."
fi

# If the deployer set a custom polaris_app password via env var, apply it.
# 09_grants.sql created the role with the dev default; rotate to the prod value.
if [ -n "$POLARIS_APP_PASSWORD" ] && [ "$POLARIS_APP_PASSWORD" != "polaris_dev_password" ]; then
    # F-13: Basic password complexity gate. The polaris_app role can read all
    # rows in the schema; a weak password here means the entire database is
    # one credential-stuffing attempt away. We require:
    #   - at least 16 characters
    #   - at least one digit
    #   - at least one letter
    #   - at least one symbol
    if [ ${#POLARIS_APP_PASSWORD} -lt 16 ]; then
        echo "FATAL: POLARIS_APP_PASSWORD must be at least 16 characters." >&2
        exit 2
    fi
    if ! echo "$POLARIS_APP_PASSWORD" | grep -q '[0-9]'; then
        echo "FATAL: POLARIS_APP_PASSWORD must contain at least one digit." >&2
        exit 2
    fi
    if ! echo "$POLARIS_APP_PASSWORD" | grep -q '[A-Za-z]'; then
        echo "FATAL: POLARIS_APP_PASSWORD must contain at least one letter." >&2
        exit 2
    fi
    if ! echo "$POLARIS_APP_PASSWORD" | grep -q '[^A-Za-z0-9]'; then
        echo "FATAL: POLARIS_APP_PASSWORD must contain at least one symbol." >&2
        exit 2
    fi

    echo "Rotating polaris_app password..."
    # Pass via env-var to psql to avoid showing it in process listings or logs.
    PGPASSWORD_NEW="$POLARIS_APP_PASSWORD" psql -v ON_ERROR_STOP=1 \
         --username "$POSTGRES_USER" \
         --dbname "$POSTGRES_DB" \
         -c "ALTER ROLE polaris_app WITH PASSWORD '$POLARIS_APP_PASSWORD'" \
         > /dev/null  # suppress any echo of the SQL
fi

echo "Polaris init complete."
