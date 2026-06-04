"""
test_checks.py — tests for the flat check layer.

Two things matter: (1) every check runs against the real repo without crashing
and returns Findings; (2) each check actually discriminates — it FAILs on a
broken fixture and passes (OK) on the real tree. The discrimination tests are
what make these checks trustworthy (detection correctness, tested — the gap the
old apparatus never closed).

Run: python3 -m pytest polaris_checks/test_checks.py
"""

from __future__ import annotations

import pathlib

import pytest

from polaris_checks import checks
from polaris_checks.checks import Finding, run_all

REPO = pathlib.Path(__file__).resolve().parent.parent


def test_run_all_clean_on_real_repo():
    findings = run_all(REPO)
    assert findings, "run_all must produce findings"
    assert all(isinstance(f, Finding) for f in findings)
    fails = [f for f in findings if f.level == "FAIL"]
    assert fails == [], f"the real repo must pass every check; failures: {[str(f) for f in fails]}"


def test_every_check_returns_findings_and_does_not_crash():
    for check in checks.CHECKS:
        out = check(REPO)
        assert isinstance(out, list) and out, f"{check.__name__} returned no findings"
        assert all(isinstance(f, Finding) for f in out)


def test_csp_check_fails_on_unsafe_inline(tmp_path):
    (tmp_path / "polaris_web").mkdir()
    (tmp_path / "polaris_web" / "security.py").write_text(
        "CSP = \"script-src 'self' 'unsafe-inline'\"\n")
    out = checks.check_csp_forbids_unsafe_inline(tmp_path)
    assert out[0].level == "FAIL", "must FAIL when CSP enables 'unsafe-inline' for scripts"


def test_fk_cascade_check_scans_migrations(tmp_path):
    # A cascade smuggled into a migration (not just 01_schema.sql) must be caught.
    (tmp_path / "polaris_sql").mkdir()
    (tmp_path / "polaris_sql" / "migrations").mkdir()
    (tmp_path / "polaris_sql" / "01_schema.sql").write_text("CREATE TABLE A (id SERIAL);\n")
    (tmp_path / "polaris_sql" / "migrations" / "y.up.sql").write_text(
        "ALTER TABLE B ADD CONSTRAINT fk FOREIGN KEY (a) REFERENCES A(id) ON DELETE CASCADE;\n")
    out = checks.check_no_fk_cascade(tmp_path)
    assert out[0].level == "FAIL", "must FAIL on a cascade in a migration, not only 01_schema.sql"


def test_fk_cascade_check_fails_on_cascade(tmp_path):
    (tmp_path / "polaris_sql").mkdir()
    (tmp_path / "polaris_sql" / "x.sql").write_text(
        "ALTER TABLE T ADD FOREIGN KEY (a) REFERENCES U(id) ON DELETE CASCADE;\n")
    out = checks.check_no_fk_cascade(tmp_path)
    assert out[0].level == "FAIL", "must FAIL on a destructive ON DELETE CASCADE"


def test_gitignore_trailing_comment_check_fails(tmp_path):
    (tmp_path / ".gitignore").write_text("polaris.env   # operator secrets\n")
    out = checks.check_gitignore_no_trailing_comments(tmp_path)
    assert out[0].level == "FAIL", "must FAIL on a trailing inline comment"
    # and the secrets check must catch the now-disabled pattern
    out2 = checks.check_secrets_file_ignored(tmp_path)
    assert out2[0].level == "FAIL", "trailing comment leaves polaris.env un-ignored"


def test_changelog_version_mismatch_fails(tmp_path):
    (tmp_path / "polaris_web").mkdir()
    (tmp_path / "polaris_web" / "__version__.py").write_text('__version__ = "9.99"\n')
    (tmp_path / "CHANGELOG.md").write_text("## v1.00 — old\n")
    out = checks.check_changelog_matches_version(tmp_path)
    assert out[0].level == "FAIL", "must FAIL when CHANGELOG top != __version__"


def test_debug_artifact_check_fails(tmp_path):
    (tmp_path / "polaris_web").mkdir()
    (tmp_path / "polaris_web" / "x.py").write_text("def f():\n    breakpoint()\n")
    out = checks.check_no_debug_artifacts(tmp_path)
    assert out[0].level == "FAIL", "must FAIL on a breakpoint() in source"


def test_pqc_wired_check_fails_when_issuance_bypasses_signing_module(tmp_path):
    (tmp_path / "polaris_sql").mkdir()
    (tmp_path / "polaris_web").mkdir()
    # Procedure accepts the param, but the app never routes through the module.
    (tmp_path / "polaris_sql" / "05_procedures.sql").write_text(
        "CREATE FUNCTION uc1_issue_and_activate(p_signature_bytes BYTEA) ...\n")
    (tmp_path / "polaris_web" / "app.py").write_text(
        "import pqc_signing  # imported but never used for issuance\n")
    out = checks.check_pqc_signing_wired(tmp_path)
    assert out[0].level == "FAIL", "must FAIL when the app never calls signature_bytes_for_token"

    # And it must FAIL when the procedure hardcodes the signature (no param).
    (tmp_path / "polaris_sql" / "05_procedures.sql").write_text(
        "CREATE FUNCTION uc1_issue_and_activate(p_token_value VARCHAR) ...\n")
    out2 = checks.check_pqc_signing_wired(tmp_path)
    assert out2[0].level == "FAIL", "must FAIL when the procedure does not accept p_signature_bytes"


def test_c2_zk_null_check_fails_without_constraint(tmp_path):
    (tmp_path / "polaris_sql").mkdir()
    (tmp_path / "polaris_sql" / "01_schema.sql").write_text(
        "CREATE TABLE VerificationEvent (token_id INTEGER, disclosure_level VARCHAR);\n")
    out = checks.check_c2_zk_token_null(tmp_path)
    assert out[0].level == "FAIL", "must FAIL when the ZK->token_id NULL CHECK is absent"


def test_c4_atomic_login_check_fails_on_read_then_write(tmp_path):
    (tmp_path / "polaris_web").mkdir()
    (tmp_path / "polaris_web" / "security.py").write_text(
        "n = read_count()\nexecute('UPDATE AppUser SET failed_login_count = %s', n + 1)\n")
    out = checks.check_c4_atomic_failed_login(tmp_path)
    assert out[0].level == "FAIL", "must FAIL when the increment is not a single atomic UPDATE"


def test_c8_atlas_caps_check_fails_without_constants(tmp_path):
    (tmp_path / "polaris_web").mkdir()
    (tmp_path / "polaris_web" / "app.py").write_text("# no atlas caps here\n")
    out = checks.check_c8_atlas_caps(tmp_path)
    assert out[0].level == "FAIL", "must FAIL when atlas hard-cap constants are missing"


def test_c9_concurrency_check_fails_without_threading_tests(tmp_path):
    (tmp_path / "polaris_web").mkdir()
    (tmp_path / "polaris_web" / "test_app.py").write_text("class FooTests:\n    pass\n")
    out = checks.check_c9_concurrency_threading(tmp_path)
    assert out[0].level == "FAIL", "must FAIL without a ConcurrencyTests class using threading"


def test_c10_no_money_check_fails_on_money_table(tmp_path):
    (tmp_path / "polaris_sql").mkdir()
    (tmp_path / "polaris_sql" / "01_schema.sql").write_text(
        "CREATE TABLE MonetaryClaim (id SERIAL, balance NUMERIC);\n")
    out = checks.check_c10_no_money_tables(tmp_path)
    assert out[0].level == "FAIL", "must FAIL when the schema defines a monetary table"


def test_open_redirect_guard_fails_on_naive_guard(tmp_path):
    (tmp_path / "polaris_web").mkdir()
    # The helper exists, but app.py still uses the naive '//'-only guard it was
    # meant to replace — the one the backslash trick (/\\host) slips past.
    (tmp_path / "polaris_web" / "security.py").write_text(
        "def is_safe_next_url(u):\n    return bool(u)\n")
    (tmp_path / "polaris_web" / "app.py").write_text(
        "next_url = request.args.get('next', '')\n"
        "if next_url.startswith('/') and not next_url.startswith('//'):\n"
        "    return redirect(next_url)\n")
    out = checks.check_open_redirect_guard(tmp_path)
    assert out[0].level == "FAIL", "must FAIL while the naive startswith('//') guard survives"


def test_cookie_secure_check_fails_when_opt_in_only(tmp_path):
    (tmp_path / "polaris_web").mkdir()
    (tmp_path / "polaris_web" / "app.py").write_text(
        "app.config['SESSION_COOKIE_SECURE'] = "
        "os.environ.get('POLARIS_COOKIE_SECURE', '').lower() in ('1', 'true')\n")
    out = checks.check_cookie_secure_in_production(tmp_path)
    assert out[0].level == "FAIL", "must FAIL when SESSION_COOKIE_SECURE is opt-in only"


def test_table_count_check_fails_on_doc_drift(tmp_path):
    (tmp_path / "polaris_sql").mkdir()
    (tmp_path / "docs").mkdir()
    # Schema with 2 tables; doc claims 27 -> drift -> FAIL.
    (tmp_path / "polaris_sql" / "01_schema.sql").write_text(
        "CREATE TABLE A (id SERIAL);\nCREATE TABLE B (id SERIAL);\n")
    (tmp_path / "docs" / "ARCHITECTURE-OVERVIEW.md").write_text(
        "PostgreSQL 16. 27 tables, stored procedures.\n")
    out = checks.check_table_count_matches_doc(tmp_path)
    assert out[0].level == "FAIL", "must FAIL when the doc table count contradicts the schema"


def test_local_clock_check_fails_on_utcnow(tmp_path):
    (tmp_path / "polaris_web").mkdir()
    (tmp_path / "polaris_web" / "app.py").write_text(
        "if epoch['valid_until'] < datetime.utcnow():\n    pass\n")
    out = checks.check_local_clock_convention(tmp_path)
    assert out[0].level == "FAIL", "must FAIL when app.py compares boundaries against utcnow()"


def test_operator_script_argv_check_fails_without_validation(tmp_path):
    (tmp_path / "scripts").mkdir()
    # A purge script that interpolates --actor-user-id with no numeric guard.
    (tmp_path / "scripts" / "polaris-purge.sh").write_text(
        '#!/usr/bin/env bash\nACTOR_USER_ID="$2"\n'
        'psql -c "CALL uc_archive_purge(p_actor_user_id := ${ACTOR_USER_ID})"\n')
    for name in ("polaris-recover-admin.sh", "polaris-migrate.sh", "polaris-archive.sh"):
        (tmp_path / "scripts" / name).write_text("#!/usr/bin/env bash\n# no validation\n")
    out = checks.check_operator_scripts_validate_argv(tmp_path)
    assert out[0].level == "FAIL", "must FAIL when an operator script interpolates argv without regex validation"


def test_migration_drift_check_fails_on_column_missing_from_schema(tmp_path):
    (tmp_path / "polaris_sql").mkdir()
    (tmp_path / "polaris_sql" / "migrations").mkdir()
    (tmp_path / "polaris_sql" / "01_schema.sql").write_text(
        "CREATE TABLE AppUser (user_id SERIAL PRIMARY KEY);\n")
    (tmp_path / "polaris_sql" / "migrations" / "x.up.sql").write_text(
        "ALTER TABLE AppUser ADD COLUMN secret_drift_col TEXT;\n")
    out = checks.check_no_migration_column_drift(tmp_path)
    assert out[0].level == "FAIL", "must FAIL when a migration adds a column missing from 01_schema.sql"


def test_c6_atlas_zk_check_fails_when_zk_location_not_redacted(tmp_path):
    (tmp_path / "polaris_sql").mkdir()
    (tmp_path / "polaris_web").mkdir()
    # Atlas function that plots ZK location with no exclusion/redaction.
    (tmp_path / "polaris_sql" / "11_atlas.sql").write_text(
        "SELECT ve.latitude, ve.longitude, ve.requestor_location "
        "FROM VerificationEvent ve WHERE ve.latitude IS NOT NULL;\n")
    (tmp_path / "polaris_web" / "app.py").write_text(
        "SELECT ve.*, ve.requestor_location FROM VerificationEvent ve;\n")
    out = checks.check_c6_atlas_redacts_zk_location(tmp_path)
    assert out[0].level == "FAIL", "must FAIL when ZK location is not excluded/redacted at the atlas read paths"


def test_aor_privilege_boundary_check_discriminates(tmp_path):
    sql = tmp_path / "polaris_sql"
    mig = sql / "migrations"
    mig.mkdir(parents=True)
    base_tables = ("tokenlifecycleevent verificationevent enrollmentstatusevent "
                   "anchorbatch tokenstateepochleaf duressevent authauditlog")

    def write(grants, mig_revoke, proc_definer):
        (sql / "09_grants.sql").write_text(grants)
        (mig / "2026-05-15-003-audit-access-log.up.sql").write_text(
            "REVOKE UPDATE, DELETE ON AuditAccessLog FROM polaris_app;\n"
            if mig_revoke else "CREATE TABLE AuditAccessLog (id BIGSERIAL);\n")
        (sql / "05_procedures.sql").write_text(
            "CREATE OR REPLACE PROCEDURE uc_archive_purge(p_actor INTEGER)\n"
            "LANGUAGE plpgsql\n"
            + ("SECURITY DEFINER\n" if proc_definer else "")
            + "AS $$ BEGIN NULL; END; $$;\n")

    good_grants = (f"REVOKE UPDATE, DELETE ON ... -- tables: {base_tables}\n")

    # 1. No REVOKE at all -> FAIL.
    write("GRANT SELECT ON ALL TABLES TO polaris_app;\n", True, True)
    assert checks.check_aor_privilege_boundary(tmp_path)[0].level == "FAIL", \
        "must FAIL when 09_grants.sql never revokes UPDATE/DELETE"

    # 2. REVOKE present but omits a table -> FAIL.
    write("REVOKE UPDATE, DELETE ON tokenlifecycleevent FROM polaris_app;\n", True, True)
    assert checks.check_aor_privilege_boundary(tmp_path)[0].level == "FAIL", \
        "must FAIL when the REVOKE omits an append-only table"

    # 3. Grants/migration fine, but uc_archive_purge is not SECURITY DEFINER -> FAIL.
    write(good_grants, True, False)
    assert checks.check_aor_privilege_boundary(tmp_path)[0].level == "FAIL", \
        "must FAIL when the sole DELETE path is not SECURITY DEFINER"

    # 4. Migration forgets its own REVOKE for AuditAccessLog -> FAIL.
    write(good_grants, False, True)
    assert checks.check_aor_privilege_boundary(tmp_path)[0].level == "FAIL", \
        "must FAIL when the AuditAccessLog migration does not revoke UPDATE/DELETE"

    # 5. All three present -> OK.
    write(good_grants, True, True)
    assert checks.check_aor_privilege_boundary(tmp_path)[0].level == "OK", \
        "must PASS when revoke + migration revoke + SECURITY DEFINER are all present"


def test_prod_app_password_synced_check_discriminates(tmp_path):
    web = tmp_path / "polaris_web"
    web.mkdir()

    GOOD_INIT = (
        'if [ -n "$POLARIS_APP_PASSWORD_FILE" ]; then\n'
        '  POLARIS_APP_PASSWORD="$(cat "$POLARIS_APP_PASSWORD_FILE")"\n'
        'fi\n'
        'psql -c "ALTER ROLE polaris_app WITH PASSWORD \'$POLARIS_APP_PASSWORD\'"\n')

    def write(compose, init=GOOD_INIT):
        (web / "docker-compose.prod.yml").write_text(compose)
        (web / "docker-init.sh").write_text(init)

    app_line = "      POLARIS_DB_PASSWORD_FILE: /run/secrets/polaris_db_password\n"
    role_line = "      POLARIS_APP_PASSWORD_FILE: /run/secrets/polaris_db_password\n"

    # 1. compose never wires the role password file -> FAIL.
    write(app_line)
    assert checks.check_prod_app_password_synced(tmp_path)[0].level == "FAIL", \
        "must FAIL when POLARIS_APP_PASSWORD_FILE is absent"

    # 2. role secret differs from the app's secret -> FAIL.
    write(app_line + "      POLARIS_APP_PASSWORD_FILE: /run/secrets/something_else\n")
    assert checks.check_prod_app_password_synced(tmp_path)[0].level == "FAIL", \
        "must FAIL when the role password secret differs from the app's"

    # 3. compose fine, but docker-init.sh never reads the file -> FAIL.
    write(app_line + role_line, init='echo "no rotation here"\n')
    assert checks.check_prod_app_password_synced(tmp_path)[0].level == "FAIL", \
        "must FAIL when docker-init.sh does not read POLARIS_APP_PASSWORD_FILE"

    # 4. compose fine, init reads the file but never ALTERs the role -> FAIL.
    write(app_line + role_line,
          init='POLARIS_APP_PASSWORD="$(cat "$POLARIS_APP_PASSWORD_FILE")"\n')
    assert checks.check_prod_app_password_synced(tmp_path)[0].level == "FAIL", \
        "must FAIL when docker-init.sh does not ALTER ROLE polaris_app"

    # 5. all wired and matching -> OK.
    write(app_line + role_line)
    assert checks.check_prod_app_password_synced(tmp_path)[0].level == "OK", \
        "must PASS when the role password is synced to the app's secret and rotated at init"


def test_coercion_evidence_retained_check_discriminates(tmp_path):
    sql = tmp_path / "polaris_sql"
    web = tmp_path / "polaris_web"
    sql.mkdir(); web.mkdir()

    GOOD_SCHEMA = (
        "-- requesting_purpose_text is the anti-coercion evidentiary trail,\n"
        "-- RETAINED on every disclosure level (unlike requestor_location).\n"
        "    requesting_purpose_text VARCHAR(280),\n")

    def write(schema, app="SELECT requesting_purpose_text FROM VerificationEvent;\n"):
        (sql / "01_schema.sql").write_text(schema)
        (sql / "11_atlas.sql").write_text("-- atlas\n")
        (sql / "05_procedures.sql").write_text("-- procs\n")
        (web / "app.py").write_text(app)

    # 1. Column missing entirely -> FAIL.
    write("CREATE TABLE VerificationEvent (id SERIAL);\n")
    assert checks.check_coercion_evidence_retained(tmp_path)[0].level == "FAIL", \
        "must FAIL when the coercion-evidence column is missing"

    # 2. Stale FALSE comment claiming ZK redaction, right before the column -> FAIL.
    write("-- Like requestor_location, it is redacted for ZERO_KNOWLEDGE rows at read.\n"
          "    requesting_purpose_text VARCHAR(280),\n")
    assert checks.check_coercion_evidence_retained(tmp_path)[0].level == "FAIL", \
        "must FAIL when the schema falsely documents the trail as ZK-redacted"

    # 3. A read path that NULLs the trail for ZK rows -> FAIL (destroys the feature).
    write(GOOD_SCHEMA,
          app=("SELECT CASE WHEN disclosure_level = 'ZERO_KNOWLEDGE' "
               "THEN NULL ELSE requesting_purpose_text END FROM VerificationEvent;\n"))
    assert checks.check_coercion_evidence_retained(tmp_path)[0].level == "FAIL", \
        "must FAIL when a read path redacts the evidence trail for ZERO_KNOWLEDGE"

    # 4. Retained + accurate comment -> OK.
    write(GOOD_SCHEMA)
    assert checks.check_coercion_evidence_retained(tmp_path)[0].level == "OK", \
        "must PASS when the evidence trail is retained and not falsely documented"


def test_zk_anti_replay_check_discriminates(tmp_path):
    sql = tmp_path / "polaris_sql"
    web = tmp_path / "polaris_web"
    sql.mkdir(); web.mkdir()

    TABLE = "CREATE TABLE ZkVerificationNonce (epoch_id INTEGER, nonce BIGINT);\n"
    CONSUME = ("INSERT INTO ZkVerificationNonce (epoch_id, context_id, nonce) "
               "VALUES (%s,%s,%s) ON CONFLICT DO NOTHING RETURNING consumed_at\n"
               "return jsonify(verified=False, reason='nonce already consumed (replay)')\n")

    def write(schema, app):
        (sql / "01_schema.sql").write_text(schema)
        (web / "app.py").write_text(app)

    # 1. No nonce store table -> FAIL.
    write("CREATE TABLE TokenStateEpoch (epoch_id SERIAL);\n", CONSUME)
    assert checks.check_zk_verify_anti_replay(tmp_path)[0].level == "FAIL", \
        "must FAIL when the single-use nonce store is missing"

    # 2. Table exists but the route never consumes the nonce -> FAIL (replay open).
    write(TABLE, "def api_zk_verify(): return jsonify(verified=True)\n")
    assert checks.check_zk_verify_anti_replay(tmp_path)[0].level == "FAIL", \
        "must FAIL when the verify route does not consume the nonce"

    # 3. Consumes but never rejects the replay case -> FAIL.
    write(TABLE, "INSERT INTO ZkVerificationNonce (epoch_id, context_id, nonce) VALUES (1,1,1)\n")
    assert checks.check_zk_verify_anti_replay(tmp_path)[0].level == "FAIL", \
        "must FAIL when the route consumes but does not reject replays"

    # 4. Table + consume + replay rejection -> OK.
    write(TABLE, CONSUME)
    assert checks.check_zk_verify_anti_replay(tmp_path)[0].level == "OK", \
        "must PASS when the nonce is consumed and replays are rejected"


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
