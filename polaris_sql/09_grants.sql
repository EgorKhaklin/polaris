-- ============================================================================
-- POLARIS — IDENTITY TOKEN SYSTEM
-- 09_grants.sql : Application-role privileges
--
-- Creates the polaris_app database role used by the Flask web app and the
-- polaris-cli tool, with the minimum privilege set needed:
--   - CONNECT on the database
--   - USAGE on the public schema
--   - SELECT, INSERT, UPDATE, DELETE on tables
--   - USAGE, SELECT on sequences (for SERIAL/IDENTITY columns)
--   - EXECUTE on functions (for the UC stored procedures)
--
-- Notably absent: any DDL privileges (CREATE/DROP/ALTER). This is intentional
-- defense-in-depth for the SQL console: even if the application-layer
-- whitelist were bypassed, DROP TABLE would still be rejected by Postgres.
--
-- Default privileges are also configured so future objects added to the public
-- schema (e.g. by future migrations) inherit the same grant pattern.
-- ============================================================================

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'polaris_app') THEN
        CREATE ROLE polaris_app WITH LOGIN PASSWORD 'polaris_dev_password';
    END IF;
END$$;

GRANT CONNECT ON DATABASE polaris_test TO polaris_app;
GRANT USAGE ON SCHEMA public TO polaris_app;

GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO polaris_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO polaris_app;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO polaris_app;

-- Default privileges for any future objects in the public schema.
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO polaris_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT USAGE, SELECT ON SEQUENCES TO polaris_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT EXECUTE ON FUNCTIONS TO polaris_app;

-- ----------------------------------------------------------------------------
-- v8.15 / R11-6 / M2-11 — System-default GUCs for the issuer-discretion
-- bound enforced by uc8_revoke_token.
--
-- polaris.default_max_revoke_percent — N (percent of agency's outstanding
--                                       tokens) above which a co-signer is
--                                       required.
-- polaris.default_window_days         — W (rolling window) over which
--                                       revocations are counted.
--
-- Per-agency overrides live in IssuerDiscretionPolicy; absence of a row
-- there inherits these defaults. The procedure reads them via
-- current_setting('polaris.default_*', true) and COALESCEs against a
-- hardcoded numeric fallback so a missing GUC degrades to defaults rather
-- than erroring.
--
-- ALTER DATABASE binds the setting to whichever database this file loads
-- into. format(%I) is the safe-identifier path; current_database() picks
-- the live DB name so this works for polaris, polaris_test, or any other
-- deployment target.
-- ----------------------------------------------------------------------------
DO $$
BEGIN
    EXECUTE format(
        'ALTER DATABASE %I SET polaris.default_max_revoke_percent = 5.00',
        current_database());
    EXECUTE format(
        'ALTER DATABASE %I SET polaris.default_window_days = 30',
        current_database());
END$$;

-- ============================================================================
-- END OF 09_grants.sql
-- ============================================================================
