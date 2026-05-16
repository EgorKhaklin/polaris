-- ============================================================================
-- POLARIS — IDENTITY TOKEN SYSTEM
-- 00_load_all.sql : Master loader
--
-- Loads all files in the correct order, producing a fully populated
-- and validated database in one command:
--
--   psql -d polaris_test -f 00_load_all.sql
--
-- Each file is idempotent (DROP IF EXISTS before CREATE), so this script
-- can be re-run any number of times against an existing database.
--
-- IMPORTANT — RUN AS A SUPERUSER (v8.32 maintenance note):
-- This file sources 12_v7_constraints.sql which creates triggers, indexes,
-- and a view in the public schema. The polaris_app role (created by
-- 09_grants.sql earlier in this file) has NO DDL privileges by design
-- (defense-in-depth: see 09_grants.sql comment block). If 00_load_all.sql
-- is run as polaris_app, the v7 hardening DDL fails SILENTLY and the
-- database appears loaded but is actually missing C-NEW-1..C-NEW-4
-- (cross-individual-succession trigger, revocation-status trigger,
-- composite index, TokensWithLifecycleSummary view). The v8.32
-- maintenance pass surfaced this gap on the live test DB.
--
-- Always load as the macOS default superuser (`vanta` on dev) or the
-- Postgres superuser (`postgres` on Linux/Docker):
--
--   psql -d polaris_test -f 00_load_all.sql       # inherits OS user
--   su postgres -c "psql -d polaris_test -f ..."  # Linux/Docker pattern
--
-- DO NOT load as polaris_app (e.g., via PGUSER=polaris_app). The
-- application role connects to the loaded database; it does not load it.
--
-- Output: a fully working schema with 73 sample rows, plus 36 test results
-- printed at the end. A clean run shows "Total: 36 tests, 36 passed, 0 failed".
-- ============================================================================

\timing on
\set ECHO queries

\echo Loading 00_migrations_table.sql (v8.95 migration registry; 13th AoR)...
\i 00_migrations_table.sql

\echo Loading 01_schema.sql...
\i 01_schema.sql

\echo Loading 02_indexes.sql...
\i 02_indexes.sql

\echo Loading 03_view.sql...
\i 03_view.sql

\echo Loading 04_data.sql...
\i 04_data.sql

\echo Loading 05_procedures.sql...
\i 05_procedures.sql

\echo Loading 06_triggers.sql...
\i 06_triggers.sql

\echo Loading 11_atlas.sql (spatial aggregation functions)...
\i 11_atlas.sql

\echo Loading 09_grants.sql...
\i 09_grants.sql

\echo Loading 10_auth.sql...
\i 10_auth.sql

\echo Re-applying grants (covers the new auth tables)...
\i 09_grants.sql

\echo Running 07_queries.sql (output displayed below)...
\i 07_queries.sql

\echo Running 08_tests.sql...
\i 08_tests.sql

\echo
\echo ============================================================================
\echo ALL FILES LOADED. See test summary above for pass/fail counts.
\echo ============================================================================
\i 12_v7_constraints.sql

\echo Loading 13_substrate.sql (M2-3 substrate-dependency manifest)...
\i 13_substrate.sql

\echo Loading 13_postgis.sql (R8-4 optional PostGIS migration; no-op without postgis)...
\i 13_postgis.sql

\echo Loading 14_foresight_helpers.sql (v9.12 Position B Layer-1 bundle: 3 SQL functions)...
\i 14_foresight_helpers.sql

\echo Loading 15_ontology.sql (v9.19 ontology layer: 6 semantic views over the schema)...
\i 15_ontology.sql
