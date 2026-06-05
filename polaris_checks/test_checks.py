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
    # Schema with 2 tables.
    (tmp_path / "polaris_sql" / "01_schema.sql").write_text(
        "CREATE TABLE A (id SERIAL);\nCREATE TABLE B (id SERIAL);\n")
    arch = tmp_path / "docs" / "ARCHITECTURE-OVERVIEW.md"
    readme = tmp_path / "README.md"

    # 1. ARCHITECTURE-OVERVIEW drift -> FAIL.
    arch.write_text("PostgreSQL 16. 27 tables, stored procedures.\n")
    readme.write_text("a working reference implementation: 2 schema tables.\n")
    assert checks.check_table_count_matches_doc(tmp_path)[0].level == "FAIL", \
        "must FAIL when the architecture-doc table count contradicts the schema"

    # 2. Architecture doc correct, but the README count drifts -> FAIL (now guarded).
    arch.write_text("PostgreSQL 16. 2 tables, stored procedures.\n")
    readme.write_text("a working reference implementation: 26 schema tables.\n")
    assert checks.check_table_count_matches_doc(tmp_path)[0].level == "FAIL", \
        "must FAIL when the README schema-table count drifts from the schema"

    # 3. Both match the schema -> OK.
    readme.write_text("a working reference implementation: 2 schema tables.\n")
    assert checks.check_table_count_matches_doc(tmp_path)[0].level == "OK", \
        "must PASS when both docs match the schema"


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


def test_thesis_terminus_check_discriminates(tmp_path):
    web = tmp_path / "polaris_web"
    docs = tmp_path / "docs"
    web.mkdir(); docs.mkdir()

    RETIRED = ("**Status:** INCONCLUSIVE — retired.\nThe v9.40 terminus passed; "
               "the strong claim is retired permanently.\n")
    OPEN = "**Status:** HYPOTHESIS-NOT-VERIFIED.\nawaiting a cold read.\n"

    def write(version, thesis):
        (web / "__version__.py").write_text(f'__version__: str = "{version}"\n')
        (docs / "THESIS.md").write_text(thesis)

    # 1. Before the v9.40 terminus: an open THESIS is fine -> OK.
    write("9.39", OPEN)
    assert checks.check_thesis_terminus_honest(tmp_path)[0].level == "OK", \
        "before v9.40 the thesis may remain open"

    # 2. Past v9.40 but status still the open 'HYPOTHESIS-NOT-VERIFIED' -> FAIL.
    write("9.90", OPEN)
    assert checks.check_thesis_terminus_honest(tmp_path)[0].level == "FAIL", \
        "past v9.40 the open status must fail"

    # 3. Past v9.40, retired language but the 'until a real cold read happens' softener remains -> FAIL.
    write("9.90", RETIRED + "we keep the status honest until a real cold read happens.\n")
    assert checks.check_thesis_terminus_honest(tmp_path)[0].level == "FAIL", \
        "the open 'until a real cold read happens' softener must fail past v9.40"

    # 4. Past v9.40 but no terminus / retirement language at all -> FAIL.
    write("9.90", "**Status:** an experiment.\nstill thinking about it.\n")
    assert checks.check_thesis_terminus_honest(tmp_path)[0].level == "FAIL", \
        "past v9.40, missing the terminus + retirement language must fail"

    # 5. Past v9.40 with proper retired/inconclusive framing -> OK.
    write("9.90", RETIRED)
    assert checks.check_thesis_terminus_honest(tmp_path)[0].level == "OK", \
        "past v9.40 the retired/inconclusive framing must pass"


def test_launcher_current_check_discriminates(tmp_path):
    GOOD = (
        'req="$WEB_DIR/requirements.txt"\n'
        'pip install --quiet -r "$req"\n'
        'build_zk_binary() { cargo build --release --bin polaris-zk; export POLARIS_ZK_BINARY; }\n'
        'run_tests() { python -m polaris_checks.run; python -m unittest '
        'test_check_constraints test_invariants_property test_redaction_property test_app; }\n')

    def write(sh):
        (tmp_path / "polaris_mac_launch.sh").write_text(sh)

    # 1. Hardcoded pip list, no requirements.txt -> FAIL.
    write("pip install flask psycopg2-binary gunicorn werkzeug webauthn\n"
          "polaris_checks test_check_constraints test_invariants_property test_redaction_property polaris-zk\n")
    assert checks.check_launcher_current(tmp_path)[0].level == "FAIL", \
        "must FAIL on a hardcoded pip list"

    # 2. Installs from requirements.txt but the test command omits canonical suites -> FAIL.
    write('pip install -r requirements.txt\nrun_tests() { python test_app.py; }\npolaris-zk\n')
    assert checks.check_launcher_current(tmp_path)[0].level == "FAIL", \
        "must FAIL when the test command omits the canonical suites"

    # 3. Deps + suites fine but no ZK binary reference -> FAIL.
    write('pip install -r requirements.txt\n'
          'run_tests(){ polaris_checks.run test_check_constraints test_invariants_property test_redaction_property; }\n')
    assert checks.check_launcher_current(tmp_path)[0].level == "FAIL", \
        "must FAIL when the launcher never builds/references the ZK binary"

    # 4. All three present -> OK.
    write(GOOD)
    assert checks.check_launcher_current(tmp_path)[0].level == "OK", \
        "must PASS when deps come from requirements.txt, the suite is canonical, and ZK is built"


def test_dockerfile_copies_app_modules_check_discriminates(tmp_path):
    web = tmp_path / "polaris_web"
    web.mkdir()
    # app.py imports two local modules; both exist as files.
    (web / "app.py").write_text(
        "import os\nimport security\nimport pqc_signing  # v9.58 trailing comment\n")
    (web / "security.py").write_text("# local\n")
    (web / "pqc_signing.py").write_text("# local\n")

    def write_dockerfiles(dev_copy, prod_copy):
        (web / "Dockerfile").write_text(f"FROM python\n{dev_copy}\n")
        (web / "Dockerfile.prod").write_text(f"FROM python\n{prod_copy}\n")

    # 1. Dev Dockerfile omits pqc_signing.py (the real v9.58 bug) -> FAIL.
    write_dockerfiles("COPY app.py security.py ./",
                      "COPY app.py security.py pqc_signing.py ./")
    out = checks.check_dockerfile_copies_app_modules(tmp_path)
    assert out[0].level == "FAIL" and "pqc_signing" in out[0].message, \
        "must FAIL when a Dockerfile omits a local module app.py imports"

    # 2. Prod Dockerfile omits it -> FAIL (both images are checked).
    write_dockerfiles("COPY app.py security.py pqc_signing.py ./",
                      "COPY app.py security.py ./")
    assert checks.check_dockerfile_copies_app_modules(tmp_path)[0].level == "FAIL", \
        "must FAIL when the prod Dockerfile omits a local module"

    # 3. Both COPY every local module -> OK.
    write_dockerfiles("COPY app.py security.py pqc_signing.py ./",
                      "COPY --chown=x:y app.py security.py pqc_signing.py ./")
    assert checks.check_dockerfile_copies_app_modules(tmp_path)[0].level == "OK", \
        "must PASS when both Dockerfiles COPY every local app module"


def test_prod_hardening_check_discriminates(tmp_path):
    web = tmp_path / "polaris_web"
    web.mkdir()
    GOOD_INIT = (
        'if [ "${POLARIS_ENV:-}" = "production" ]; then\n'
        "  psql <<'SQL'\n"
        "  UPDATE AppUser SET is_active = FALSE WHERE username IN ('admin', 'operator', 'auditor');\n"
        "SQL\n"
        "fi\n")
    GOOD_COMPOSE = "services:\n  app:\n    environment:\n      POLARIS_REDIS_URL: redis://redis:6379/0\n"

    def write(init, compose):
        (web / "docker-init.sh").write_text(init)
        (web / "docker-compose.prod.yml").write_text(compose)

    # 1. docker-init does not neutralize demo accounts in prod -> FAIL.
    write('echo "no prod hardening"\n', GOOD_COMPOSE)
    assert checks.check_prod_hardening(tmp_path)[0].level == "FAIL", \
        "must FAIL when demo accounts are not disabled in production"

    # 2. Demo accounts handled, but no Redis URL in prod compose -> FAIL.
    write(GOOD_INIT, "services:\n  app:\n    environment:\n      POLARIS_PORT: '8000'\n")
    assert checks.check_prod_hardening(tmp_path)[0].level == "FAIL", \
        "must FAIL when the prod rate limiter is not wired to Redis"

    # 3. Both present -> OK.
    write(GOOD_INIT, GOOD_COMPOSE)
    assert checks.check_prod_hardening(tmp_path)[0].level == "OK", \
        "must PASS when demo accounts are neutralized and Redis is wired"


def test_backup_encryption_check_discriminates(tmp_path):
    sc = tmp_path / "scripts"
    sc.mkdir()
    bk = sc / "polaris-backup.sh"
    rs = sc / "polaris-restore.sh"

    # 1. Backup script has no encryption support -> FAIL.
    bk.write_text("tar -czf backup.tar.gz .\n")
    rs.write_text("tar -xzf backup.tar.gz\n")
    assert checks.check_backup_encryption(tmp_path)[0].level == "FAIL", \
        "must FAIL when backups are not encryptable"

    # 2. Backup encrypts but restore cannot decrypt -> FAIL.
    bk.write_text('KEY="$POLARIS_BACKUP_KEY_FILE"\nopenssl enc -aes-256-cbc -in t -out t.enc\n')
    rs.write_text("tar -xzf backup.tar.gz\n")
    assert checks.check_backup_encryption(tmp_path)[0].level == "FAIL", \
        "must FAIL when restore cannot decrypt .enc backups"

    # 3. Both present -> OK.
    bk.write_text('KEY="$POLARIS_BACKUP_KEY_FILE"\nopenssl enc -aes-256-cbc -in t -out t.enc\n')
    rs.write_text('if [[ "$f" == *.enc ]]; then openssl enc -d -aes-256-cbc -in "$f"; fi\n')
    assert checks.check_backup_encryption(tmp_path)[0].level == "OK", \
        "must PASS when backup encrypts and restore decrypts"


def test_pqc_real_signing_check_discriminates(tmp_path):
    web = tmp_path / "polaris_web"
    gh = tmp_path / ".github" / "workflows"
    web.mkdir(); gh.mkdir(parents=True)
    GOOD_PQC = ("POLARIS_PQC_SIGNING_KEY_FILE\ndef generate_keypair(): ...\ndef verify(): ...\n")
    GOOD_CI = "jobs:\n  pqc-real:\n    steps: [pip install liboqs-python]\n"

    def write(pqc, ci):
        (web / "pqc_signing.py").write_text(pqc)
        (gh / "ci.yml").write_text(ci)

    # 1. Ephemeral-only (no persistent key file) -> FAIL.
    write("def generate_keypair(): ...\ndef verify(): ...\n", GOOD_CI)
    assert checks.check_pqc_real_signing(tmp_path)[0].level == "FAIL", \
        "must FAIL when there is no persistent signing key"

    # 2. Persistent key but CI never tests real PQC -> FAIL.
    write(GOOD_PQC, "jobs:\n  test:\n    steps: []\n")
    assert checks.check_pqc_real_signing(tmp_path)[0].level == "FAIL", \
        "must FAIL when CI does not exercise the real ML-DSA path"

    # 3. Persistent key + verify + CI pqc-real job with liboqs -> OK.
    write(GOOD_PQC, GOOD_CI)
    assert checks.check_pqc_real_signing(tmp_path)[0].level == "OK", \
        "must PASS with a persistent key, verify, and a real-PQC CI job"


def test_sql_console_readonly_check_discriminates(tmp_path):
    web = tmp_path / "polaris_web"
    web.mkdir()

    def write(body):
        (web / "app.py").write_text(
            "def sql_query():\n" + body + "\n\ndef next_route():\n    pass\n"
        )

    # 1. Keyword whitelist only, no DB-level read-only -> FAIL (CTE-bypassable).
    write("    cur.execute('SET statement_timeout = 5000')\n    cur.execute(sql)")
    assert checks.check_sql_console_readonly(tmp_path)[0].level == "FAIL", \
        "must FAIL when the console relies only on the SELECT/WITH keyword gate"

    # 2. A mid-transaction SET default_transaction_read_only does NOT bind the
    #    query's own already-started transaction -> still FAIL (the real bug the
    #    DB-backed test caught; the check must not accept this non-fix).
    write("    cur.execute('SET statement_timeout = 5000')\n"
          "    cur.execute('SET default_transaction_read_only = on')\n"
          "    cur.execute(sql)")
    assert checks.check_sql_console_readonly(tmp_path)[0].level == "FAIL", \
        "must FAIL on the non-functional mid-transaction SET (it does not bind the query)"

    # 3. Session set read-only before any statement -> OK.
    write("    conn.set_session(readonly=True)\n"
          "    cur.execute('SET statement_timeout = 5000')\n"
          "    cur.execute(sql)")
    assert checks.check_sql_console_readonly(tmp_path)[0].level == "OK", \
        "must PASS once the session is set read-only before any statement"

    # 4. read-only set in some OTHER function, not sql_query -> FAIL (scoped to the handler).
    (web / "app.py").write_text(
        "def sql_query():\n    cur.execute(sql)\n\n"
        "def elsewhere():\n    conn.set_session(readonly=True)\n"
    )
    assert checks.check_sql_console_readonly(tmp_path)[0].level == "FAIL", \
        "must FAIL when read-only is set outside the sql_query handler"

    # 5. Missing app.py -> FAIL.
    (web / "app.py").unlink()
    assert checks.check_sql_console_readonly(tmp_path)[0].level == "FAIL", \
        "must FAIL when app.py is absent"


def test_prod_image_no_test_deps_check_discriminates(tmp_path):
    web = tmp_path / "polaris_web"
    web.mkdir()
    RUNTIME = "Flask==3.1.3\npsycopg2-binary==2.9.12\nredis>=5.0,<6.0\n"
    DEV = "-r requirements.txt\nhypothesis>=6.0,<7.0\npytest>=7.0,<9.0\nplaywright>=1.40,<2.0\n"
    DF = "FROM python:3.12-slim\nCOPY requirements.txt /tmp/\nRUN pip install -r /tmp/requirements.txt\n"

    def write(runtime, dev=DEV, df=DF, dfp=DF):
        (web / "requirements.txt").write_text(runtime)
        if dev is not None:
            (web / "requirements-dev.txt").write_text(dev)
        elif (web / "requirements-dev.txt").exists():
            (web / "requirements-dev.txt").unlink()
        (web / "Dockerfile").write_text(df)
        (web / "Dockerfile.prod").write_text(dfp)

    # 1. A test framework in the runtime surface -> FAIL.
    write(RUNTIME + "pytest>=7.0,<9.0\n")
    assert checks.check_prod_image_no_test_deps(tmp_path)[0].level == "FAIL", \
        "must FAIL when requirements.txt lists a test-only package"

    # 2. Clean runtime but no requirements-dev.txt -> FAIL.
    write(RUNTIME, dev=None)
    assert checks.check_prod_image_no_test_deps(tmp_path)[0].level == "FAIL", \
        "must FAIL when the dev requirements file is absent"

    # 3. Dev file does not pull in the runtime surface -> FAIL.
    write(RUNTIME, dev="pytest>=7.0,<9.0\n")
    assert checks.check_prod_image_no_test_deps(tmp_path)[0].level == "FAIL", \
        "must FAIL when requirements-dev.txt omits `-r requirements.txt`"

    # 4. A Dockerfile installs the dev file -> FAIL.
    write(RUNTIME, dfp="FROM x\nCOPY requirements-dev.txt /tmp/\nRUN pip install -r /tmp/requirements-dev.txt\n")
    assert checks.check_prod_image_no_test_deps(tmp_path)[0].level == "FAIL", \
        "must FAIL when an image installs the dev requirements"

    # 5. Clean runtime, dev file with -r, images install runtime only -> OK.
    write(RUNTIME)
    assert checks.check_prod_image_no_test_deps(tmp_path)[0].level == "OK", \
        "must PASS when test tooling is isolated and the images install runtime only"


def test_cve_scanning_check_discriminates(tmp_path):
    gh = tmp_path / ".github" / "workflows"
    gh.mkdir(parents=True)
    GATING = "      run: pip-audit -r polaris_web/requirements.txt --progress-spinner off --strict\n"

    def write_ci(text):
        (gh / "ci.yml").write_text(text)

    def write_dependabot():
        (tmp_path / ".github" / "dependabot.yml").write_text("version: 2\nupdates: []\n")

    # 1. No pip-audit in CI -> FAIL.
    write_ci("jobs:\n  test:\n    steps: []\n")
    write_dependabot()
    assert checks.check_cve_scanning(tmp_path)[0].level == "FAIL", \
        "must FAIL when CI does not run pip-audit"

    # 2. pip-audit present but not gating (--strict) on requirements.txt -> FAIL.
    write_ci("jobs:\n  scan:\n    steps:\n      run: pip-audit -r polaris_web/requirements.txt\n")
    assert checks.check_cve_scanning(tmp_path)[0].level == "FAIL", \
        "must FAIL when the runtime audit is not --strict (non-gating)"

    # 3. Gating audit but no dependabot.yml -> FAIL.
    write_ci("jobs:\n  scan:\n    steps:\n" + GATING)
    (tmp_path / ".github" / "dependabot.yml").unlink()
    assert checks.check_cve_scanning(tmp_path)[0].level == "FAIL", \
        "must FAIL when Dependabot is not configured"

    # 4. Gating audit + dependabot -> OK.
    write_ci("jobs:\n  scan:\n    steps:\n" + GATING)
    write_dependabot()
    assert checks.check_cve_scanning(tmp_path)[0].level == "OK", \
        "must PASS with a gating runtime audit and Dependabot configured"


def test_migration_timeouts_check_discriminates(tmp_path):
    scripts = tmp_path / "scripts"
    scripts.mkdir()

    def write(sh):
        (scripts / "polaris-migrate.sh").write_text(sh)

    # 1. No timeouts at all -> FAIL.
    write("BEGIN;\n\\i up.sql\nCOMMIT;\n")
    assert checks.check_migration_timeouts(tmp_path)[0].level == "FAIL", \
        "must FAIL when the runner sets no migration timeouts"

    # 2. lock_timeout only (statement_timeout missing) -> FAIL.
    write("BEGIN;\nSET LOCAL lock_timeout = '3s';\n\\i up.sql\nCOMMIT;\n")
    assert checks.check_migration_timeouts(tmp_path)[0].level == "FAIL", \
        "must FAIL when statement_timeout is not also bounded"

    # 3. Both SET LOCAL timeouts -> OK.
    write("BEGIN;\nSET LOCAL lock_timeout = '3s';\n"
          "SET LOCAL statement_timeout = '60s';\n\\i up.sql\nCOMMIT;\n")
    assert checks.check_migration_timeouts(tmp_path)[0].level == "OK", \
        "must PASS when both lock_timeout and statement_timeout are SET LOCAL"

    # 4. Missing script -> FAIL.
    (scripts / "polaris-migrate.sh").unlink()
    assert checks.check_migration_timeouts(tmp_path)[0].level == "FAIL", \
        "must FAIL when the migrate script is absent"


def test_web_concurrency_honored_check_discriminates(tmp_path):
    web = tmp_path / "polaris_web"
    web.mkdir()

    def write(conf):
        (web / "gunicorn.conf.py").write_text(conf)

    # 1. Reads only POLARIS_WORKERS -> FAIL (WEB_CONCURRENCY inert).
    write("workers = int(os.environ.get('POLARIS_WORKERS', '4'))\n")
    assert checks.check_web_concurrency_honored(tmp_path)[0].level == "FAIL", \
        "must FAIL when the config ignores WEB_CONCURRENCY"

    # 2. Honors WEB_CONCURRENCY -> OK.
    write("workers = int(os.environ.get('POLARIS_WORKERS') "
          "or os.environ.get('WEB_CONCURRENCY') or 4)\n")
    assert checks.check_web_concurrency_honored(tmp_path)[0].level == "OK", \
        "must PASS when WEB_CONCURRENCY is honored"

    # 3. Missing config -> FAIL.
    (web / "gunicorn.conf.py").unlink()
    assert checks.check_web_concurrency_honored(tmp_path)[0].level == "FAIL", \
        "must FAIL when gunicorn.conf.py is absent"


def test_health_liveness_readiness_split_check_discriminates(tmp_path):
    web = tmp_path / "polaris_web"
    web.mkdir()
    GOOD_LIVE = (
        "@app.route('/api/health/ready')\n"
        "def api_health_ready():\n    body, code = _compute_readiness()\n    return body, code\n\n"
        "@app.route('/api/health/live')\n"
        "def api_health_live():\n    return {'status': 'alive'}, 200\n\n"
        "def next_route():\n    pass\n"
    )
    GOOD_DF = "HEALTHCHECK CMD curl http://localhost:8000/api/health/live | grep alive\n"

    def write(app_py, df=GOOD_DF):
        (web / "app.py").write_text(app_py)
        (web / "Dockerfile.prod").write_text(df)

    # 1. Only the old /api/health (no split) -> FAIL.
    write("@app.route('/api/health')\ndef api_health():\n    return {}, 200\n")
    assert checks.check_health_liveness_readiness_split(tmp_path)[0].level == "FAIL", \
        "must FAIL when liveness/readiness are not split"

    # 2. Both routes, liveness cheap, HEALTHCHECK uses liveness -> OK.
    write(GOOD_LIVE)
    assert checks.check_health_liveness_readiness_split(tmp_path)[0].level == "OK", \
        "must PASS with both probes split and a cheap liveness handler"

    # 3. Liveness handler runs the dependency roll-up -> FAIL (not cheap).
    write(
        "@app.route('/api/health/ready')\ndef api_health_ready():\n    return _compute_readiness()\n\n"
        "@app.route('/api/health/live')\n"
        "def api_health_live():\n    body, code = _compute_readiness()\n    return body, code\n\n"
        "def next_route():\n    pass\n"
    )
    assert checks.check_health_liveness_readiness_split(tmp_path)[0].level == "FAIL", \
        "must FAIL when the liveness probe runs the dependency checks"

    # 4. Both routes but the prod HEALTHCHECK still uses the dependency roll-up -> FAIL.
    write(GOOD_LIVE, df="HEALTHCHECK CMD curl http://localhost:8000/api/health | grep healthy\n")
    assert checks.check_health_liveness_readiness_split(tmp_path)[0].level == "FAIL", \
        "must FAIL when the container HEALTHCHECK does not use the liveness probe"


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
