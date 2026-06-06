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
                   "anchorbatch tokenstateepochleaf duressevent authauditlog "
                   "individualerasureevent")

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


def test_compose_resource_limits_check_discriminates(tmp_path):
    web = tmp_path / "polaris_web"
    web.mkdir()

    def service(name, with_limits, with_logging):
        s = f"  {name}:\n    image: {name}:latest\n"
        if with_limits:
            s += ("    deploy:\n      resources:\n        limits:\n"
                  "          cpus: '0.5'\n          memory: 128M\n")
        if with_logging:
            s += ("    logging:\n      driver: json-file\n"
                  "      options:\n        max-size: 10m\n        max-file: '5'\n")
        return s

    def write(*svcs):
        (web / "docker-compose.prod.yml").write_text("services:\n" + "".join(svcs))

    # 1. Two services, neither limited or rotated -> FAIL.
    write(service("a", False, False), service("b", False, False))
    assert checks.check_compose_resource_limits(tmp_path)[0].level == "FAIL", \
        "must FAIL when services have no resource limits"

    # 2. Limits on all, logging on only one -> FAIL (rotation not universal).
    write(service("a", True, True), service("b", True, False))
    assert checks.check_compose_resource_limits(tmp_path)[0].level == "FAIL", \
        "must FAIL when not every service configures log rotation"

    # 3. Logging on all, limits on only one -> FAIL.
    write(service("a", True, True), service("b", False, True))
    assert checks.check_compose_resource_limits(tmp_path)[0].level == "FAIL", \
        "must FAIL when not every service sets resource limits"

    # 4. Both on every service -> OK.
    write(service("a", True, True), service("b", True, True))
    assert checks.check_compose_resource_limits(tmp_path)[0].level == "OK", \
        "must PASS when every service has limits + rotating logging"

    # 5. Missing compose -> FAIL.
    (web / "docker-compose.prod.yml").unlink()
    assert checks.check_compose_resource_limits(tmp_path)[0].level == "FAIL", \
        "must FAIL when the prod compose is absent"


def test_pgbouncer_self_built_check_discriminates(tmp_path):
    web = tmp_path / "polaris_web"
    web.mkdir()
    GOOD_COMPOSE = ("services:\n  pgbouncer:\n    build:\n      context: .\n"
                    "      dockerfile: Dockerfile.pgbouncer\n    image: polaris-pgbouncer:prod\n")
    GOOD_ENTRY = "#!/bin/sh\nPWFILE=\"${POLARIS_DB_PASSWORD_FILE:-/run/secrets/x}\"\n"
    gh = tmp_path / ".github" / "workflows"
    gh.mkdir(parents=True)
    (gh / "ci.yml").write_text("jobs:\n  d:\n    steps:\n      run: docker build -f polaris_web/Dockerfile.pgbouncer .\n")

    def write(compose=GOOD_COMPOSE, df="FROM alpine\n", entry=GOOD_ENTRY):
        (web / "docker-compose.prod.yml").write_text(compose)
        if df is not None:
            (web / "Dockerfile.pgbouncer").write_text(df)
        elif (web / "Dockerfile.pgbouncer").exists():
            (web / "Dockerfile.pgbouncer").unlink()
        (web / "pgbouncer-entrypoint.sh").write_text(entry)

    # 1. Still references the removed bitnami image -> FAIL.
    write(compose="services:\n  pgbouncer:\n    image: bitnami/pgbouncer:1.22\n")
    assert checks.check_pgbouncer_self_built(tmp_path)[0].level == "FAIL", \
        "must FAIL when the compose still pulls bitnami/pgbouncer"

    # 2. No Dockerfile.pgbouncer present -> FAIL.
    write(df=None)
    assert checks.check_pgbouncer_self_built(tmp_path)[0].level == "FAIL", \
        "must FAIL when the self-built Dockerfile is absent"

    # 3. Entrypoint reads the password from env, not the file secret -> FAIL.
    write(entry="#!/bin/sh\nPASSWORD=\"$PGBOUNCER_PASSWORD\"\n")
    assert checks.check_pgbouncer_self_built(tmp_path)[0].level == "FAIL", \
        "must FAIL when the entrypoint does not use the file-mounted secret"

    # 4. Self-built, builds Dockerfile.pgbouncer, reads the file secret -> OK.
    write()
    assert checks.check_pgbouncer_self_built(tmp_path)[0].level == "OK", \
        "must PASS for a self-built pooler reading the file-mounted secret"

    # 5. Dockerfile.pgbouncer named only in a COMMENT while a third-party image
    #    is actually pulled -> FAIL (substring match would false-pass here).
    write(compose="# we use Dockerfile.pgbouncer now\nservices:\n  pgbouncer:\n"
                  "    image: third-party/pgbouncer:2.0\n")
    assert checks.check_pgbouncer_self_built(tmp_path)[0].level == "FAIL", \
        "must FAIL when Dockerfile.pgbouncer is only mentioned in a comment"

    # 6. POLARIS_DB_PASSWORD_FILE named only in a COMMENT while the password is
    #    actually read from the environment -> FAIL.
    write(entry="#!/bin/sh\n# TODO: switch to POLARIS_DB_PASSWORD_FILE\n"
                "PASSWORD=\"$PGBOUNCER_PASSWORD\"\n")
    assert checks.check_pgbouncer_self_built(tmp_path)[0].level == "FAIL", \
        "must FAIL when the secret is only named in a comment, not read in code"

    # 7. Upper/mixed-case BITNAMI reference (Docker refs are case-insensitive) -> FAIL.
    write(compose="services:\n  pgbouncer:\n    image: BITNAMI/PgBouncer:1.22\n")
    assert checks.check_pgbouncer_self_built(tmp_path)[0].level == "FAIL", \
        "must FAIL on a case-variant bitnami/pgbouncer reference"


def test_caddy_self_built_check_discriminates(tmp_path):
    web = tmp_path / "polaris_web"
    web.mkdir()
    gh = tmp_path / ".github" / "workflows"
    gh.mkdir(parents=True)

    RL_CADDYFILE = "site {\n    rate_limit {\n        zone z { events 200 }\n    }\n}\n"
    BUILD_COMPOSE = ("services:\n  caddy:\n    build:\n      context: .\n"
                     "      dockerfile: Dockerfile.caddy\n    image: polaris-caddy:prod\n")
    GOOD_DF = ("FROM caddy:2.11.4-builder-alpine AS builder\n"
               "RUN xcaddy build --with github.com/mholt/caddy-ratelimit\n"
               "FROM caddy:2.11.4-alpine\nCOPY --from=builder /usr/bin/caddy /usr/bin/caddy\n")
    GOOD_CI = "jobs:\n  e:\n    steps:\n      run: docker build -f polaris_web/Dockerfile.caddy . && caddy validate\n"

    def write(caddyfile=RL_CADDYFILE, compose=BUILD_COMPOSE, df=GOOD_DF, ci=GOOD_CI):
        (web / "Caddyfile").write_text(caddyfile)
        (web / "docker-compose.prod.yml").write_text(compose)
        if df is not None:
            (web / "Dockerfile.caddy").write_text(df)
        elif (web / "Dockerfile.caddy").exists():
            (web / "Dockerfile.caddy").unlink()
        (gh / "ci.yml").write_text(ci)

    # 1. Caddyfile uses rate_limit but the compose pulls the STOCK image -> FAIL.
    write(compose="services:\n  caddy:\n    image: caddy:2-alpine@sha256:abc\n")
    assert checks.check_caddy_self_built(tmp_path)[0].level == "FAIL", \
        "must FAIL when a plugin directive is used but the edge is the stock image"

    # 2. Builds Dockerfile.caddy but the plugin is not compiled in -> FAIL.
    write(df="FROM caddy:2.11.4-alpine\n")
    assert checks.check_caddy_self_built(tmp_path)[0].level == "FAIL", \
        "must FAIL when Dockerfile.caddy does not compile in the caddy-ratelimit plugin"

    # 3. Self-built + plugin compiled in, but CI does not validate the Caddyfile -> FAIL.
    write(ci="jobs:\n  e:\n    steps:\n      run: echo nothing\n")
    assert checks.check_caddy_self_built(tmp_path)[0].level == "FAIL", \
        "must FAIL when CI does not build + validate the Caddyfile against the edge image"

    # 4. Dockerfile.caddy named only in a COMMENT while the stock image is pulled -> FAIL.
    write(compose="# build: Dockerfile.caddy\nservices:\n  caddy:\n    image: caddy:2-alpine\n")
    assert checks.check_caddy_self_built(tmp_path)[0].level == "FAIL", \
        "must FAIL when Dockerfile.caddy is only mentioned in a comment"

    # 5. No third-party directive in the Caddyfile -> the stock image is fine -> OK.
    write(caddyfile="site {\n    reverse_proxy app:8000\n}\n",
          compose="services:\n  caddy:\n    image: caddy:2-alpine@sha256:abc\n")
    assert checks.check_caddy_self_built(tmp_path)[0].level == "OK", \
        "must PASS (nothing to enforce) when the Caddyfile uses no plugin directives"

    # 6. rate_limit used, self-built, plugin compiled in, CI validates -> OK.
    write()
    assert checks.check_caddy_self_built(tmp_path)[0].level == "OK", \
        "must PASS for a self-built edge with the plugin compiled in and CI validation"


def test_sast_scanning_check_discriminates(tmp_path):
    gh = tmp_path / ".github" / "workflows"
    gh.mkdir(parents=True)

    def write_ci(text):
        (gh / "ci.yml").write_text(text)

    # 1. No bandit in CI -> FAIL.
    write_ci("jobs:\n  test:\n    steps: []\n")
    assert checks.check_sast_scanning(tmp_path)[0].level == "FAIL", \
        "must FAIL when CI does not run bandit"

    # 2. bandit present but not gating on high severity -> FAIL.
    write_ci("jobs:\n  s:\n    steps:\n      run: bandit -r polaris_web\n")
    assert checks.check_sast_scanning(tmp_path)[0].level == "FAIL", \
        "must FAIL when bandit does not gate on high severity"

    # 3. bandit gating on high severity -> OK.
    write_ci("jobs:\n  s:\n    steps:\n      run: bandit -r polaris_web polaris_cli --severity-level high -q\n")
    assert checks.check_sast_scanning(tmp_path)[0].level == "OK", \
        "must PASS when bandit gates on high severity"


def test_verify_enforced_check_discriminates(tmp_path):
    web = tmp_path / "polaris_web"
    gh = tmp_path / ".github" / "workflows"
    web.mkdir(); gh.mkdir(parents=True)
    GOOD_PQC = (
        "def signature_with_key_for_token(t):\n"
        "    if flag:\n"
        "        r = sign(t)\n"
        "        if not verify(t, r.signature_hex, r.public_key_hex):\n"
        "            raise SigningError('nope')\n"
        "        return r\n"
        "    return digest, LABEL, None\n\n"
        "def verify(m, s, k):\n    return True\n"
        "def trust_anchor_public_key_hex():\n    return None\n"
        "def verify_token_signature(t, s, a):\n    return True\n"
    )
    GOOD_CI = "jobs:\n  pqc-real:\n    steps:\n      run: assert verify_token_signature(x)\n"

    def write(pqc, ci=GOOD_CI):
        (web / "pqc_signing.py").write_text(pqc)
        (gh / "ci.yml").write_text(ci)

    # 1. Missing verify_token_signature / trust anchor -> FAIL.
    write("def signature_bytes_for_token(t):\n    return digest\n\ndef verify(m,s,k):\n    return True\n")
    assert checks.check_verify_enforced(tmp_path)[0].level == "FAIL", \
        "must FAIL without the use-path verification primitive + trust anchor"

    # 2. Has the functions, but issuance does not self-verify -> FAIL.
    write("def signature_with_key_for_token(t):\n    return sign(t).sig, lbl, pk\n\n"
          "def verify(m,s,k):\n    return True\n"
          "def trust_anchor_public_key_hex():\n    return None\n"
          "def verify_token_signature(t,s,a):\n    return True\n")
    assert checks.check_verify_enforced(tmp_path)[0].level == "FAIL", \
        "must FAIL when signature_with_key_for_token does not self-verify"

    # 3. Self-verifies + functions present + CI exercises it -> OK.
    write(GOOD_PQC)
    assert checks.check_verify_enforced(tmp_path)[0].level == "OK", \
        "must PASS when issuance self-verifies and CI exercises verify_token_signature"

    # 4. CI does not exercise verify_token_signature -> FAIL.
    write(GOOD_PQC, ci="jobs:\n  pqc-real:\n    steps:\n      run: echo nothing\n")
    assert checks.check_verify_enforced(tmp_path)[0].level == "FAIL", \
        "must FAIL when CI does not exercise verify-at-use"


def test_pqc_second_witness_check_discriminates(tmp_path):
    web = tmp_path / "polaris_web"
    gh = tmp_path / ".github" / "workflows"
    web.mkdir(); gh.mkdir(parents=True)

    # A passing module: verify_both + an independent (cryptography MLDSA65) witness,
    # a refused disagreement, and all three real-verify sites routed through it.
    GOOD_PQC = (
        "from cryptography.hazmat.primitives.asymmetric import mldsa\n"
        "def _verify_second_witness(m, s, k):\n"
        "    return mldsa.MLDSA65PublicKey.from_public_bytes(b'').verify(s, m)\n"
        "def verify_both(m, s, k):\n"
        "    if primary != witness:\n"
        "        log('DISAGREEMENT')\n"
        "        return False\n"
        "    return primary\n"
        "def signature_with_key_for_token(t):\n"
        "    if not verify_both(t, r.signature_hex, r.public_key_hex):\n"
        "        raise SigningError('nope')\n"
        "    return r\n"
        "def verify_stored_signature(t, s, k):\n    return verify_both(t, s, k)\n"
        "def verify_token_signature(t, s, a):\n    return verify_both(t, s, anchor)\n"
    )
    GOOD_CI = "jobs:\n  pqc-real:\n    steps:\n      run: python -m unittest SecondWitnessTests\n"

    def write(pqc, ci=GOOD_CI):
        (web / "pqc_signing.py").write_text(pqc)
        (gh / "ci.yml").write_text(ci)

    # 1. No verify_both / second witness -> FAIL.
    write("def verify(m, s, k):\n    return True\n")
    assert checks.check_pqc_second_witness(tmp_path)[0].level == "FAIL", \
        "must FAIL without verify_both + _verify_second_witness"

    # 2. A second witness that is just another liboqs call (no independent impl) -> FAIL.
    write(GOOD_PQC.replace("from cryptography.hazmat.primitives.asymmetric import mldsa\n", "")
                  .replace("mldsa.MLDSA65PublicKey.from_public_bytes(b'').verify(s, m)", "oqs.verify(s, m)"))
    assert checks.check_pqc_second_witness(tmp_path)[0].level == "FAIL", \
        "must FAIL when the witness is not an independent implementation (cryptography MLDSA65)"

    # 3. Disagreement not refused -> FAIL.
    write(GOOD_PQC.replace("log('DISAGREEMENT')\n        ", ""))
    assert checks.check_pqc_second_witness(tmp_path)[0].level == "FAIL", \
        "must FAIL when a witness disagreement is not refused/logged"

    # 4. A real-verify site bypasses verify_both -> FAIL.
    write(GOOD_PQC.replace(
        "def verify_token_signature(t, s, a):\n    return verify_both(t, s, anchor)\n",
        "def verify_token_signature(t, s, a):\n    return verify(t, s, anchor)\n"))
    assert checks.check_pqc_second_witness(tmp_path)[0].level == "FAIL", \
        "must FAIL when a verify site routes around verify_both (lone verifier)"

    # 5. CI does not run the two-witness agreement test -> FAIL.
    write(GOOD_PQC, ci="jobs:\n  pqc-real:\n    steps:\n      run: echo nothing\n")
    assert checks.check_pqc_second_witness(tmp_path)[0].level == "FAIL", \
        "must FAIL when CI does not prove the two witnesses agree"

    # 6. All present -> OK.
    write(GOOD_PQC)
    assert checks.check_pqc_second_witness(tmp_path)[0].level == "OK", (
        "must PASS with verify_both, an independent witness, a refused disagreement, "
        "all sites routed through it, and CI proving agreement")


def test_pqc_posture_check_discriminates(tmp_path):
    ref = tmp_path / "docs" / "reference"
    ref.mkdir(parents=True)
    doc = ref / "PQC-POSTURE.md"

    GOOD = (
        "# PQC Posture\n"
        "Audited against NIST FIPS 204 and IR 8547 (deprecate 2030, disallow 2035).\n"
        "See the production-readiness ledger; nothing here claims deployability.\n"
        "## What is post-quantum today\n"
        "The token signature is ML-DSA-65 (FIPS 204), the ZK proof is FRI-based.\n"
        "## What is still classical\n"
        "TLS key exchange is classical ECDHE (harvest-now). WebAuthn operator MFA "
        "uses classical ECDSA/EdDSA/RSA.\n"
    )

    # 1. Missing doc -> FAIL.
    assert checks.check_pqc_posture(tmp_path)[0].level == "FAIL", "must FAIL with no posture doc"

    # 2. Only the rosy half (no 'what is still classical') -> FAIL.
    doc.write_text(GOOD.split("## What is still classical")[0])
    assert checks.check_pqc_posture(tmp_path)[0].level == "FAIL", \
        "must FAIL when the still-classical half is absent (one-sided claim)"

    # 3. Has both sections but omits a classical surface (no WebAuthn) -> FAIL.
    doc.write_text(GOOD.replace("WebAuthn operator MFA uses classical ECDSA/EdDSA/RSA.", "Nothing else."))
    assert checks.check_pqc_posture(tmp_path)[0].level == "FAIL", \
        "must FAIL when a classical surface (WebAuthn) is not named"

    # 4. Drops the NIST timeline mapping -> FAIL.
    doc.write_text(GOOD.replace("deprecate 2030, disallow 2035", "someday"))
    assert checks.check_pqc_posture(tmp_path)[0].level == "FAIL", \
        "must FAIL without the NIST 2030/2035 timeline"

    # 5. Overclaims by dropping the production-readiness disclaimer -> FAIL.
    doc.write_text(GOOD.replace(
        "See the production-readiness ledger; nothing here claims deployability.\n", ""))
    assert checks.check_pqc_posture(tmp_path)[0].level == "FAIL", \
        "must FAIL when the production-readiness disclaimer is gone"

    # 6. Honest, two-sided, timeline-mapped, disclaimed -> OK.
    doc.write_text(GOOD)
    assert checks.check_pqc_posture(tmp_path)[0].level == "OK", \
        "must PASS an honest, two-sided, NIST-mapped, non-overclaiming audit"


def test_prod_images_digest_pinned_check_discriminates(tmp_path):
    web = tmp_path / "polaris_web"
    gh = tmp_path / ".github"
    web.mkdir(); gh.mkdir()
    (gh / "dependabot.yml").write_text("version: 2\nupdates:\n  - package-ecosystem: docker\n")

    def write(compose):
        (web / "docker-compose.prod.yml").write_text(compose)

    PINNED = ("services:\n"
              "  caddy:\n    image: caddy:2-alpine@sha256:" + "a" * 64 + "\n"
              "  app:\n    build: .\n    image: polaris-app:prod\n"
              "  redis:\n    image: redis:7-alpine@sha256:" + "b" * 64 + "\n")

    # 1. A third-party image pinned only by tag -> FAIL.
    write("services:\n  caddy:\n    image: caddy:2-alpine\n"
          "  app:\n    image: polaris-app:prod\n")
    assert checks.check_prod_images_digest_pinned(tmp_path)[0].level == "FAIL", \
        "must FAIL when a third-party image is tag-pinned only"

    # 2. All third-party images digest-pinned, locally-built exempt -> OK.
    write(PINNED)
    assert checks.check_prod_images_digest_pinned(tmp_path)[0].level == "OK", \
        "must PASS when every third-party image is @sha256-pinned (polaris-* exempt)"

    # 3. Digest-pinned but Dependabot lacks the docker ecosystem -> FAIL.
    (gh / "dependabot.yml").write_text("version: 2\nupdates:\n  - package-ecosystem: pip\n")
    write(PINNED)
    assert checks.check_prod_images_digest_pinned(tmp_path)[0].level == "FAIL", \
        "must FAIL when Dependabot does not track docker (pins would never update)"


def test_alert_rules_check_discriminates(tmp_path):
    obs = tmp_path / "deploy" / "observability"
    obs.mkdir(parents=True)
    GOOD_RULES = ("groups:\n  - name: polaris\n    rules:\n"
                  "      - alert: PolarisAppDown\n        expr: up == 0\n"
                  "      - alert: PolarisHigh5xx\n        expr: ratio > 0.01\n")
    GOOD_CFG = ("scrape_configs:\n  - job_name: polaris\n    metrics_path: /metrics\n"
                "rule_files:\n  - polaris-alerts.yml\n")

    def write(rules=GOOD_RULES, cfg=GOOD_CFG):
        (obs / "polaris-alerts.yml").write_text(rules)
        (obs / "prometheus.yml").write_text(cfg)

    # 1. Rules file missing a key alert -> FAIL.
    write(rules="groups:\n  - name: polaris\n    rules:\n      - alert: SomethingElse\n        expr: x\n")
    assert checks.check_alert_rules(tmp_path)[0].level == "FAIL", \
        "must FAIL when PolarisHigh5xx/PolarisAppDown are absent"

    # 2. Scrape config does not load the rules -> FAIL.
    write(cfg="scrape_configs:\n  - job_name: polaris\n    metrics_path: /metrics\n")
    assert checks.check_alert_rules(tmp_path)[0].level == "FAIL", \
        "must FAIL when prometheus.yml does not load the rule file"

    # 3. Both present + wired -> OK.
    write()
    assert checks.check_alert_rules(tmp_path)[0].level == "OK", \
        "must PASS with shipped rules + a scrape config that loads them"

    # 4. Missing files -> FAIL.
    (obs / "polaris-alerts.yml").unlink()
    assert checks.check_alert_rules(tmp_path)[0].level == "FAIL", \
        "must FAIL when the artifact does not ship"


def test_alert_runbooks_check_discriminates(tmp_path):
    obs = tmp_path / "deploy" / "observability"
    ref = tmp_path / "docs" / "operator"
    obs.mkdir(parents=True)
    ref.mkdir(parents=True)
    RULES = ("groups:\n  - name: polaris\n    rules:\n"
             "      - alert: PolarisAppDown\n        expr: up == 0\n"
             "      - alert: PolarisHigh5xx\n        expr: ratio > 0.01\n")

    def write_rules(text=RULES):
        (obs / "polaris-alerts.yml").write_text(text)

    def write_book(text):
        (ref / "RUNBOOKS.md").write_text(text)

    # 1. An alert with no runbook section -> FAIL.
    write_rules()
    write_book("# RUNBOOKS\n\n## PolarisAppDown\n\nbody\n")
    out = checks.check_alert_runbooks(tmp_path)
    assert out[0].level == "FAIL", "must FAIL when an alert lacks a runbook section"
    assert "PolarisHigh5xx" in out[0].message

    # 2. Every alert documented, one-to-one -> OK.
    write_book("# RUNBOOKS\n\n## PolarisAppDown\n\nbody\n\n## PolarisHigh5xx\n\nbody\n")
    assert checks.check_alert_runbooks(tmp_path)[0].level == "OK", \
        "must PASS when every alert has exactly one runbook section"

    # 3. An orphan runbook for an alert that no longer exists -> FAIL.
    write_book("# RUNBOOKS\n\n## PolarisAppDown\n\nbody\n\n## PolarisHigh5xx\n\nbody\n"
               "\n## PolarisGhostAlert\n\nbody\n")
    out = checks.check_alert_runbooks(tmp_path)
    assert out[0].level == "FAIL", "must FAIL on an orphan runbook section"
    assert "PolarisGhostAlert" in out[0].message

    # 4. Missing RUNBOOKS.md entirely -> FAIL.
    (ref / "RUNBOOKS.md").unlink()
    assert checks.check_alert_runbooks(tmp_path)[0].level == "FAIL", \
        "must FAIL when RUNBOOKS.md does not exist"


def test_encryption_at_rest_posture_check_discriminates(tmp_path):
    op = tmp_path / "docs" / "operator"
    sql = tmp_path / "polaris_sql"
    op.mkdir(parents=True)
    sql.mkdir(parents=True)
    GOOD_SCHEMA = "proof_path JSONB NOT NULL,\n-- v1 stores proof_path in plaintext\n"
    GOOD_DOC = (
        "# at-rest posture\n"
        "Polaris does **not** encrypt the live database at rest.\n"
        "Sensitive at rest: Individual.legal_name, Individual.date_of_birth, and\n"
        "TokenStateEpochLeaf.proof_path (stored in plaintext, schema-acknowledged).\n"
        "The operator-gated control is host volume encryption (LUKS / fscrypt).\n"
    )

    def write(doc=GOOD_DOC, schema=GOOD_SCHEMA):
        (op / "ENCRYPTION-AT-REST.md").write_text(doc)
        (sql / "01_schema.sql").write_text(schema)

    # 1. all present and honest -> OK.
    write()
    assert checks.check_encryption_at_rest_posture(tmp_path)[0].level == "OK", \
        "must PASS an honest, schema-grounded posture doc"

    # 2. doc does not name proof_path -> FAIL.
    write(doc=GOOD_DOC.replace("proof_path", "the merkle leaves"))
    assert checks.check_encryption_at_rest_posture(tmp_path)[0].level == "FAIL", \
        "must FAIL when the plaintext proof_path surface is not named"

    # 3. doc does not name the PII columns -> FAIL.
    write(doc=GOOD_DOC.replace("legal_name", "the name"))
    assert checks.check_encryption_at_rest_posture(tmp_path)[0].level == "FAIL", \
        "must FAIL when the PII columns are not named"

    # 4. schema still plaintext but doc never says 'plaintext' -> FAIL (drift).
    write(doc=GOOD_DOC.replace("plaintext", "stored"))
    assert checks.check_encryption_at_rest_posture(tmp_path)[0].level == "FAIL", \
        "must FAIL when the doc drifts from the schema's plaintext reality"

    # 5. no host-level encryption path named -> FAIL.
    write(doc=GOOD_DOC.replace("(LUKS / fscrypt)", "(somehow)"))
    assert checks.check_encryption_at_rest_posture(tmp_path)[0].level == "FAIL", \
        "must FAIL without the host-level LUKS/fscrypt path"

    # 6. overclaiming: drops the honest 'does not encrypt' disclaimer -> FAIL.
    write(doc=GOOD_DOC.replace("does **not** encrypt the live database at rest",
                               "encrypts the live database at rest"))
    assert checks.check_encryption_at_rest_posture(tmp_path)[0].level == "FAIL", \
        "must FAIL when the doc overclaims that the live DB is encrypted"

    # 7. doc missing entirely -> FAIL.
    (op / "ENCRYPTION-AT-REST.md").unlink()
    assert checks.check_encryption_at_rest_posture(tmp_path)[0].level == "FAIL", \
        "must FAIL when the posture doc is absent"


def test_erasure_procedure_check_discriminates(tmp_path):
    sql = tmp_path / "polaris_sql"
    op = tmp_path / "docs" / "operator"
    sql.mkdir(parents=True)
    op.mkdir(parents=True)
    GOOD_SCHEMA = "CREATE TABLE IndividualErasureEvent (erasure_id SERIAL);\n"
    GOOD_TRIG = "CREATE TRIGGER trg_erasure_append_only BEFORE UPDATE OR DELETE ON IndividualErasureEvent\n"
    GOOD_PRIVACY = "Erasure is real: uc_pseudonymize_individual pseudonymizes legal_name.\n"
    GOOD_PROC = (
        "CREATE OR REPLACE PROCEDURE uc_pseudonymize_individual(p_id INTEGER, p_actor INTEGER, p_reason VARCHAR)\n"
        "LANGUAGE plpgsql AS $$\n"
        "BEGIN\n"
        "    IF v_role <> 'admin' THEN RAISE EXCEPTION 'must be admin'; END IF;\n"
        "    UPDATE Individual SET legal_name = 'PSEUDONYMIZED' WHERE individual_id = p_id;\n"
        "    INSERT INTO IndividualErasureEvent (individual_id) VALUES (p_id);\n"
        "END$$;\n"
    )

    def write(schema=GOOD_SCHEMA, proc=GOOD_PROC, trig=GOOD_TRIG, privacy=GOOD_PRIVACY):
        (sql / "01_schema.sql").write_text(schema)
        (sql / "05_procedures.sql").write_text(proc)
        (sql / "06_triggers.sql").write_text(trig)
        (op / "PRIVACY.md").write_text(privacy)

    # 1. fully wired -> OK.
    write()
    assert checks.check_erasure_procedure(tmp_path)[0].level == "OK", \
        "must PASS the complete erasure wiring"

    # 2. no erasure-log table -> FAIL.
    write(schema="-- no table here\n")
    assert checks.check_erasure_procedure(tmp_path)[0].level == "FAIL", \
        "must FAIL without the IndividualErasureEvent table"

    # 3. procedure issues a DELETE (covert deletion path around C1) -> FAIL.
    write(proc=GOOD_PROC.replace(
        "INSERT INTO IndividualErasureEvent (individual_id) VALUES (p_id);",
        "DELETE FROM Individual WHERE individual_id = p_id;\n"
        "    INSERT INTO IndividualErasureEvent (individual_id) VALUES (p_id);"))
    assert checks.check_erasure_procedure(tmp_path)[0].level == "FAIL", \
        "must FAIL when the procedure can DELETE (it must only pseudonymize)"

    # 4. procedure is not admin-gated -> FAIL.
    write(proc=GOOD_PROC.replace("must be admin", "anyone may"))
    assert checks.check_erasure_procedure(tmp_path)[0].level == "FAIL", \
        "must FAIL when the procedure is not admin-gated"

    # 5. the erasure log is not append-only (no trigger) -> FAIL.
    write(trig="-- no erasure trigger\n")
    assert checks.check_erasure_procedure(tmp_path)[0].level == "FAIL", \
        "must FAIL when IndividualErasureEvent has no append-only trigger"

    # 6. PRIVACY.md does not point at the real mechanism -> FAIL.
    write(privacy="Erasure is theoretically possible.\n")
    assert checks.check_erasure_procedure(tmp_path)[0].level == "FAIL", \
        "must FAIL when PRIVACY.md does not reference uc_pseudonymize_individual"


def test_replication_scaffolding_check_discriminates(tmp_path):
    web = tmp_path / "polaris_web"
    scripts = tmp_path / "scripts"
    op = tmp_path / "docs" / "operator"
    gh = tmp_path / ".github" / "workflows"
    for d in (web, scripts, op, gh):
        d.mkdir(parents=True)
    GOOD_INIT = (
        "psql -c \"ALTER SYSTEM SET wal_level = replica;\"\n"
        "psql -c \"CREATE ROLE polaris_replicator WITH LOGIN REPLICATION PASSWORD 'x'\"\n"
        "echo 'host replication polaris_replicator samenet scram-sha-256' >> pg_hba.conf\n"
    )
    GOOD_COMPOSE = ("services:\n  postgres:\n    environment:\n"
                    "      POLARIS_REPLICATOR_PASSWORD_FILE: /run/secrets/polaris_replicator_password\n"
                    "    secrets:\n      - polaris_replicator_password\n")
    GOOD_SECRETS = "write_secret_if_missing polaris_replicator_password 24\n"
    GOOD_DOC = ("# failover\nStandby is operator-supplied and operator-gated.\n"
                "Bootstrap with pg_basebackup -R; promote with pg_promote().\n")
    GOOD_CI = "docker run pg_basebackup ...\npsql -c 'SELECT * FROM pg_stat_replication'\n"

    def write(init=GOOD_INIT, compose=GOOD_COMPOSE, secrets=GOOD_SECRETS, doc=GOOD_DOC, ci=GOOD_CI):
        (web / "docker-init.sh").write_text(init)
        (web / "docker-compose.prod.yml").write_text(compose)
        (scripts / "polaris-generate-secrets.sh").write_text(secrets)
        (op / "FAILOVER.md").write_text(doc)
        (gh / "ci.yml").write_text(ci)

    # 1. fully wired -> OK.
    write()
    assert checks.check_replication_scaffolding(tmp_path)[0].level == "OK", \
        "must PASS the complete replication scaffolding"

    # 2. primary not made replication-ready (no wal_level) -> FAIL.
    write(init=GOOD_INIT.replace("ALTER SYSTEM SET wal_level = replica", "echo nope"))
    assert checks.check_replication_scaffolding(tmp_path)[0].level == "FAIL", \
        "must FAIL without wal_level=replica in docker-init"

    # 3. no replication role -> FAIL.
    write(init=GOOD_INIT.replace("REPLICATION", "NOREPL"))
    assert checks.check_replication_scaffolding(tmp_path)[0].level == "FAIL", \
        "must FAIL without the polaris_replicator REPLICATION role"

    # 4. secret not minted -> FAIL.
    write(secrets="write_secret_if_missing polaris_db_password 24\n")
    assert checks.check_replication_scaffolding(tmp_path)[0].level == "FAIL", \
        "must FAIL when the replicator password is not generated"

    # 5. compose does not mount the secret -> FAIL.
    write(compose="services:\n  postgres:\n    environment:\n      POLARIS_ENV: production\n")
    assert checks.check_replication_scaffolding(tmp_path)[0].level == "FAIL", \
        "must FAIL when the prod compose does not mount the replicator secret"

    # 6. doc does not document the bootstrap/promotion -> FAIL.
    write(doc="# failover\nStandby is operator-supplied and operator-gated.\nSomehow promote it.\n")
    assert checks.check_replication_scaffolding(tmp_path)[0].level == "FAIL", \
        "must FAIL when FAILOVER.md omits pg_basebackup/pg_promote"

    # 7. doc overclaims (not honest about operator-supplied standby) -> FAIL.
    write(doc="# failover\nA running standby ships out of the box.\n"
              "Bootstrap with pg_basebackup -R; promote with pg_promote().\n")
    assert checks.check_replication_scaffolding(tmp_path)[0].level == "FAIL", \
        "must FAIL when FAILOVER.md does not say the standby host is operator-supplied"

    # 8. no CI round-trip -> FAIL.
    write(ci="echo no replication test here\n")
    assert checks.check_replication_scaffolding(tmp_path)[0].level == "FAIL", \
        "must FAIL when ci.yml has no replication round-trip"


def test_pgbackrest_scaffolding_check_discriminates(tmp_path):
    web = tmp_path / "polaris_web"
    op = tmp_path / "docs" / "operator"
    gh = tmp_path / ".github" / "workflows"
    scripts = tmp_path / "scripts"
    for d in (web, op, gh, scripts):
        d.mkdir(parents=True)
    GOOD_DF = "FROM postgres:16-alpine@sha256:abc\nRUN apk add --no-cache pgbackrest\n"
    GOOD_CONF = ("[global]\nrepo1-path=/var/lib/pgbackrest\n# swap repo1 for s3 for offsite;\n"
                 "# S3 keys via a 0600 file mounted at /etc/pgbackrest/conf.d/, not env\n"
                 "[polaris]\npg1-path=/var/lib/postgresql/data\n")
    GOOD_COMPOSE = ("services:\n  postgres:\n    build:\n      dockerfile: Dockerfile.postgres\n"
                    "    environment:\n      POLARIS_PGBACKREST_ENABLED: \"0\"\n"
                    "    volumes:\n      - ./pgbackrest.conf:/etc/pgbackrest/pgbackrest.conf:ro\n")
    GOOD_INIT = ("if [ \"$POLARIS_PGBACKREST_ENABLED\" = \"1\" ]; then\n"
                 "  psql -c \"ALTER SYSTEM SET archive_mode = on;\"\n"
                 "  psql -c \"ALTER SYSTEM SET archive_command = 'pgbackrest --stanza=polaris archive-push %p';\"\n"
                 "  if ! grep -qE 'repo1-type[[:space:]]*=[[:space:]]*s3' /etc/pgbackrest/pgbackrest.conf; then\n"
                 "    echo 'WARNING: archiving to a LOCAL repo (no repo1-type=s3)' >&2\n  fi\nfi\n")
    GOOD_DR = "Bootstrap: pgbackrest --stanza=polaris stanza-create\n"
    GOOD_CI = "docker build Dockerfile.postgres\npgbackrest --stanza=polaris restore\n"
    GOOD_DEPLOY = ("if [ \"$POLARIS_PGBACKREST_ENABLED\" = \"1\" ]; then\n"
                   "  docker compose exec postgres pgbackrest --stanza=polaris stanza-create\nfi\n")

    def write(df=GOOD_DF, conf=GOOD_CONF, compose=GOOD_COMPOSE, init=GOOD_INIT, dr=GOOD_DR,
              ci=GOOD_CI, deploy=GOOD_DEPLOY):
        (web / "Dockerfile.postgres").write_text(df)
        (web / "pgbackrest.conf").write_text(conf)
        (web / "docker-compose.prod.yml").write_text(compose)
        (web / "docker-init.sh").write_text(init)
        (op / "DR.md").write_text(dr)
        (gh / "ci.yml").write_text(ci)
        (scripts / "polaris-deploy.sh").write_text(deploy)

    # 1. fully wired -> OK.
    write()
    assert checks.check_pgbackrest_scaffolding(tmp_path)[0].level == "OK", \
        "must PASS the complete pgBackRest scaffolding"

    # 2. image does not install pgbackrest -> FAIL.
    write(df="FROM postgres:16-alpine@sha256:abc\nRUN echo hi\n")
    assert checks.check_pgbackrest_scaffolding(tmp_path)[0].level == "FAIL", \
        "must FAIL when the postgres image lacks pgbackrest"

    # 3. base not digest-pinned -> FAIL.
    write(df="FROM postgres:16-alpine\nRUN apk add --no-cache pgbackrest\n")
    assert checks.check_pgbackrest_scaffolding(tmp_path)[0].level == "FAIL", \
        "must FAIL when the image base is not digest-pinned"

    # 4. config does not document the offsite S3 swap -> FAIL (overclaiming).
    write(conf="[global]\nrepo1-path=/var/lib/pgbackrest\n[polaris]\npg1-path=/var/lib/postgresql/data\n")
    assert checks.check_pgbackrest_scaffolding(tmp_path)[0].level == "FAIL", \
        "must FAIL when pgbackrest.conf does not document the offsite repo"

    # 5. archiving is not opt-in (no POLARIS_PGBACKREST_ENABLED gate) -> FAIL.
    write(init="psql -c \"ALTER SYSTEM SET archive_mode = on; archive-push\"\n")
    assert checks.check_pgbackrest_scaffolding(tmp_path)[0].level == "FAIL", \
        "must FAIL when archiving is not gated behind POLARIS_PGBACKREST_ENABLED"

    # 6. DR.md does not document stanza-create -> FAIL.
    write(dr="just restore somehow\n")
    assert checks.check_pgbackrest_scaffolding(tmp_path)[0].level == "FAIL", \
        "must FAIL when DR.md omits stanza-create"

    # 7. no CI restore round-trip -> FAIL.
    write(ci="echo no backup test\n")
    assert checks.check_pgbackrest_scaffolding(tmp_path)[0].level == "FAIL", \
        "must FAIL when ci.yml has no pgBackRest restore round-trip"

    # 8. the deploy does not auto-bootstrap the stanza -> FAIL (v9.130).
    write(deploy="echo deploy without pgbackrest\n")
    assert checks.check_pgbackrest_scaffolding(tmp_path)[0].level == "FAIL", \
        "must FAIL when polaris-deploy.sh does not stanza-create when archiving is enabled"

    # 9. docker-init does not warn about a local repo -> FAIL (v9.130).
    write(init=GOOD_INIT.replace("WARNING: archiving to a LOCAL repo (no repo1-type=s3)", "ok"))
    assert checks.check_pgbackrest_scaffolding(tmp_path)[0].level == "FAIL", \
        "must FAIL when docker-init does not warn on a local (non-s3) repo"

    # 10. the S3-cred guidance does not use a file-mounted config (conf.d) -> FAIL (v9.130).
    write(conf="[global]\nrepo1-path=/var/lib/pgbackrest\n# s3 swap\n[polaris]\npg1-path=/data\n",
          dr="Bootstrap: pgbackrest --stanza=polaris stanza-create\n")
    assert checks.check_pgbackrest_scaffolding(tmp_path)[0].level == "FAIL", \
        "must FAIL when S3-credential guidance does not use a mounted conf.d (env literals leak)"


def test_duress_alertable_check_discriminates(tmp_path):
    web = tmp_path / "polaris_web"
    obs = tmp_path / "deploy" / "observability"
    web.mkdir(parents=True)
    obs.mkdir(parents=True)
    GOOD_APP = (
        "_METRICS_DURESS = _PromCounter('polaris_duress_events_total', 'x')\n"
        "def _record_duress_async(token_id, context_id, requesting_agency_id):\n"
        "    observability.record_duress_event(individual_id=token_id)\n"
        "    _METRICS_DURESS.inc()\n"
        "\n\n"
        "def other():\n    pass\n"
    )
    GOOD_ALERTS = ("- alert: PolarisDuressEvent\n"
                   "  expr: increase(polaris_duress_events_total[5m]) > 0\n")

    def write(app=GOOD_APP, alerts=GOOD_ALERTS):
        (web / "app.py").write_text(app)
        (obs / "polaris-alerts.yml").write_text(alerts)

    # 1. fully wired -> OK.
    write()
    assert checks.check_duress_alertable(tmp_path)[0].level == "OK", \
        "must PASS when the duress counter is exposed, incremented, and alerted"

    # 2. duress is only in the JSON metrics, not a Prometheus counter -> FAIL.
    write(app="def _record_duress_async(t, c, a):\n    observability.record_duress_event(individual_id=t)\n\n\ndef o():\n    pass\n")
    assert checks.check_duress_alertable(tmp_path)[0].level == "FAIL", \
        "must FAIL when polaris_duress_events_total is not exposed on /metrics"

    # 3. counter exists but is NOT incremented at the record site -> FAIL.
    write(app=GOOD_APP.replace("    _METRICS_DURESS.inc()\n", ""))
    assert checks.check_duress_alertable(tmp_path)[0].level == "FAIL", \
        "must FAIL when the counter is never incremented (the alert would never fire)"

    # 4. no alert on the counter -> FAIL.
    write(alerts="- alert: PolarisAppDown\n  expr: up == 0\n")
    assert checks.check_duress_alertable(tmp_path)[0].level == "FAIL", \
        "must FAIL when no PolarisDuressEvent alert references the counter"


def test_prod_fail_closed_check_discriminates(tmp_path):
    web = tmp_path / "polaris_web"
    web.mkdir()
    GOOD = (
        "_PRODUCTION = os.environ.get('POLARIS_ENV') == 'production'\n"
        "if _PRODUCTION:\n"
        "    m = os.environ.get('POLARIS_DB_SSLMODE', 'prefer')\n"
        "    if m not in ('require', 'verify-ca', 'verify-full'):\n"
        "        sys.exit(2)\n"
        "    if m in ('verify-ca', 'verify-full') and not os.environ.get('POLARIS_DB_SSLROOTCERT'):\n"
        "        sys.exit(2)\n"
        "    if os.environ.get('POLARIS_DURESS_SYNC') == '1':\n"
        "        sys.exit(2)\n"
    )
    # The 'prefer' token must appear (the message names the plaintext-capable modes).
    GOOD = GOOD + "# rejects prefer/allow/disable\n"

    def write(app=GOOD):
        (web / "app.py").write_text(app)

    # 1. all guards present -> OK.
    write()
    assert checks.check_prod_fail_closed(tmp_path)[0].level == "OK", \
        "must PASS when the production fail-closed guards are present"

    # 2. no _PRODUCTION flag -> FAIL.
    write(app=GOOD.replace("_PRODUCTION", "_prod_flag"))
    assert checks.check_prod_fail_closed(tmp_path)[0].level == "FAIL", \
        "must FAIL without a _PRODUCTION flag"

    # 3. the sslmode guard is gone -> FAIL.
    write(app="_PRODUCTION = True\nif _PRODUCTION:\n    if os.environ.get('POLARIS_DURESS_SYNC') == '1':\n        sys.exit(2)\n")
    assert checks.check_prod_fail_closed(tmp_path)[0].level == "FAIL", \
        "must FAIL when the POLARIS_DB_SSLMODE guard is missing"

    # 4. verify-* does not require POLARIS_DB_SSLROOTCERT -> FAIL (v9.132).
    write(app="_PRODUCTION = True\nif _PRODUCTION:\n    m = os.environ.get('POLARIS_DB_SSLMODE', 'prefer')\n"
              "    if m not in ('require','verify-ca','verify-full'):\n        sys.exit(2)\n    # rejects prefer\n"
              "    if os.environ.get('POLARIS_DURESS_SYNC') == '1':\n        sys.exit(2)\n")
    assert checks.check_prod_fail_closed(tmp_path)[0].level == "FAIL", \
        "must FAIL when verify-* does not require POLARIS_DB_SSLROOTCERT"

    # 5. the duress-sync guard is gone -> FAIL.
    write(app="_PRODUCTION = True\nif _PRODUCTION:\n    m = os.environ.get('POLARIS_DB_SSLMODE', 'prefer')\n"
              "    if m not in ('require','verify-ca','verify-full'):\n        sys.exit(2)\n    # rejects prefer\n"
              "    if not os.environ.get('POLARIS_DB_SSLROOTCERT'):\n        sys.exit(2)\n")
    assert checks.check_prod_fail_closed(tmp_path)[0].level == "FAIL", \
        "must FAIL when the POLARIS_DURESS_SYNC guard is missing"


def test_prod_real_pqc_check_discriminates(tmp_path):
    web = tmp_path / "polaris_web"
    gh = tmp_path / ".github" / "workflows"
    web.mkdir(); gh.mkdir(parents=True)
    GOOD_DF = "FROM x\nRUN pip install liboqs-python\n"
    GOOD_COMPOSE = ("services:\n  app:\n    environment:\n"
                    "      POLARIS_USE_REAL_PQC: '1'\n"
                    "      POLARIS_PQC_SIGNING_KEY_FILE: /run/secrets/polaris_signing_key\n"
                    "    secrets:\n      - polaris_signing_key\n")
    GOOD_CI = "jobs:\n  d:\n    steps:\n      - name: Verify real ML-DSA-65 signing inside the prod image\n"

    def write(df=GOOD_DF, compose=GOOD_COMPOSE, ci=GOOD_CI):
        (web / "Dockerfile.prod").write_text(df)
        (web / "docker-compose.prod.yml").write_text(compose)
        (gh / "ci.yml").write_text(ci)

    # 1. liboqs not installed in the prod image -> FAIL.
    write(df="FROM x\nRUN pip install flask\n")
    assert checks.check_prod_real_pqc(tmp_path)[0].level == "FAIL", \
        "must FAIL when Dockerfile.prod does not install liboqs"

    # 2. liboqs present but the flag is off -> FAIL.
    write(compose="services:\n  app:\n    environment:\n      POLARIS_ENV: production\n")
    assert checks.check_prod_real_pqc(tmp_path)[0].level == "FAIL", \
        "must FAIL when POLARIS_USE_REAL_PQC is not set in prod"

    # 3. Flag on but no signing-key secret -> FAIL.
    write(compose="services:\n  app:\n    environment:\n      POLARIS_USE_REAL_PQC: '1'\n")
    assert checks.check_prod_real_pqc(tmp_path)[0].level == "FAIL", \
        "must FAIL when the signing-key secret is not mounted (no trust anchor)"

    # 4. CI does not verify real PQC in the prod image -> FAIL.
    write(ci="jobs:\n  d:\n    steps:\n      - name: build\n")
    assert checks.check_prod_real_pqc(tmp_path)[0].level == "FAIL", \
        "must FAIL when CI does not verify real PQC inside the prod image"

    # 5. All three + CI verification -> OK.
    write()
    assert checks.check_prod_real_pqc(tmp_path)[0].level == "OK", \
        "must PASS with liboqs in the image, the flag on, the key secret, and CI verification"


def test_signature_self_contained_verify_check_discriminates(tmp_path):
    web = tmp_path / "polaris_web"; sql = tmp_path / "polaris_sql"
    web.mkdir(); sql.mkdir()

    def write(pqc, schema, proc, app):
        (web / "pqc_signing.py").write_text(pqc)
        (sql / "01_schema.sql").write_text(schema)
        (sql / "05_procedures.sql").write_text(proc)
        (web / "app.py").write_text(app)

    GOOD_PQC = "def signature_with_key_for_token(): ...\ndef verify_stored_signature(): ...\n"
    GOOD_SCHEMA = "CREATE TABLE TokenSignature (signing_public_key_hex TEXT);\n"
    GOOD_PROC = "FUNCTION uc1_issue_and_activate(p_signing_public_key_hex TEXT) ...\n"
    GOOD_APP = "x = pqc_signing.verify_stored_signature(a, b, c)\n"

    # 1. pqc_signing missing the functions -> FAIL.
    write("def sign(): ...\n", GOOD_SCHEMA, GOOD_PROC, GOOD_APP)
    assert checks.check_signature_self_contained_verify(tmp_path)[0].level == "FAIL"

    # 2. schema missing the column -> FAIL.
    write(GOOD_PQC, "CREATE TABLE TokenSignature (signature_bytes BYTEA);\n", GOOD_PROC, GOOD_APP)
    assert checks.check_signature_self_contained_verify(tmp_path)[0].level == "FAIL"

    # 3. procedure missing the param -> FAIL.
    write(GOOD_PQC, GOOD_SCHEMA, "FUNCTION uc1_issue_and_activate(p_signature_bytes BYTEA) ...\n", GOOD_APP)
    assert checks.check_signature_self_contained_verify(tmp_path)[0].level == "FAIL"

    # 4. token-detail does not verify -> FAIL.
    write(GOOD_PQC, GOOD_SCHEMA, GOOD_PROC, "render_template('tokens_detail.html')\n")
    assert checks.check_signature_self_contained_verify(tmp_path)[0].level == "FAIL"

    # 5. all wired -> OK.
    write(GOOD_PQC, GOOD_SCHEMA, GOOD_PROC, GOOD_APP)
    assert checks.check_signature_self_contained_verify(tmp_path)[0].level == "OK"


def test_deploy_syncs_db_objects_check_discriminates(tmp_path):
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    GOOD_MIG = "case x in\n  --sync-objects) MODE=sync ;;\nesac\nsync-objects) do_sync_objects ;;\n"
    GOOD_DEP = ('polaris-migrate.sh --up --target=docker-stack\n'
                'polaris-migrate.sh --sync-objects --target=docker-stack\n')

    def write(mig=GOOD_MIG, dep=GOOD_DEP):
        (scripts / "polaris-migrate.sh").write_text(mig)
        (scripts / "polaris-deploy.sh").write_text(dep)

    # 1. migrate script lacks --sync-objects -> FAIL.
    write(mig="case x in\n  --up) MODE=up ;;\nesac\n")
    assert checks.check_deploy_syncs_db_objects(tmp_path)[0].level == "FAIL", \
        "must FAIL when polaris-migrate.sh has no --sync-objects mode"

    # 2. deploy does not run sync-objects/migrate against the stack -> FAIL.
    write(dep="docker compose up -d\n")
    assert checks.check_deploy_syncs_db_objects(tmp_path)[0].level == "FAIL", \
        "must FAIL when the deploy does not apply migrations + sync objects"

    # 3. both present -> OK.
    write()
    assert checks.check_deploy_syncs_db_objects(tmp_path)[0].level == "OK", \
        "must PASS when migrate has --sync-objects and the deploy runs migrate + sync on the stack"


def test_prometheus_multiprocess_check_discriminates(tmp_path):
    web = tmp_path / "polaris_web"
    web.mkdir()
    GOOD_APP = "PROMETHEUS_MULTIPROC_DIR\nMultiProcessCollector(reg)\n"
    GOOD_GCONF = "def child_exit(server, worker):\n    multiprocess.mark_process_dead(worker.pid)\n"
    GOOD_COMPOSE = "services:\n  app:\n    environment:\n      PROMETHEUS_MULTIPROC_DIR: /tmp/x\n"

    def write(app=GOOD_APP, gconf=GOOD_GCONF, compose=GOOD_COMPOSE):
        (web / "app.py").write_text(app)
        (web / "gunicorn.conf.py").write_text(gconf)
        (web / "docker-compose.prod.yml").write_text(compose)

    # 1. app.py does not aggregate via MultiProcessCollector -> FAIL.
    write(app="generate_latest(_METRICS_REGISTRY)\n")
    assert checks.check_prometheus_multiprocess(tmp_path)[0].level == "FAIL", \
        "must FAIL when /metrics does not aggregate across workers"

    # 2. gunicorn does not reap dead workers -> FAIL.
    write(gconf="def on_starting(s):\n    pass\n")
    assert checks.check_prometheus_multiprocess(tmp_path)[0].level == "FAIL", \
        "must FAIL without child_exit + mark_process_dead"

    # 3. prod compose does not set the dir -> FAIL.
    write(compose="services:\n  app:\n    environment:\n      POLARIS_ENV: production\n")
    assert checks.check_prometheus_multiprocess(tmp_path)[0].level == "FAIL", \
        "must FAIL when the prod compose does not set PROMETHEUS_MULTIPROC_DIR"

    # 4. all wired -> OK.
    write()
    assert checks.check_prometheus_multiprocess(tmp_path)[0].level == "OK", \
        "must PASS with multiprocess collector + child_exit reaping + the dir set"


def test_app_db_tls_check_discriminates(tmp_path):
    web = tmp_path / "polaris_web"
    web.mkdir()
    GOOD_APP = ("DB_CONFIG = {'sslmode': os.environ.get('POLARIS_DB_SSLMODE', 'prefer')}\n"
                "if os.environ.get('POLARIS_DB_SSLROOTCERT'):\n"
                "    DB_CONFIG['sslrootcert'] = os.environ['POLARIS_DB_SSLROOTCERT']\n")
    GOOD_COMPOSE = ("services:\n  app:\n    environment:\n"
                    "      POLARIS_DB_SSLMODE: verify-ca\n"
                    "      POLARIS_DB_SSLROOTCERT: /etc/polaris-pgb-certs/pgbouncer.crt\n"
                    "  pgbouncer:\n    environment:\n"
                    "      PGBOUNCER_SERVER_TLS_SSLMODE: verify-ca\n"
                    "      PGBOUNCER_SERVER_TLS_CA_FILE: /etc/polaris-pg-certs/postgres.crt\n"
                    "      PGBOUNCER_CLIENT_TLS_SSLMODE: require\n"
                    "      PGBOUNCER_CLIENT_TLS_CERT_FILE: /etc/polaris-pgb-certs/pgbouncer.crt\n")
    GOOD_INIT = "psql -c \"ALTER SYSTEM SET ssl = on;\"\n"
    GOOD_ENTRY = ("server_tls_sslmode = $X\nserver_tls_ca_file = $C\nclient_tls_sslmode = $Y\n"
                  "case $S in verify-ca|verify-full) "
                  "echo 'requires PGBOUNCER_SERVER_TLS_CA_FILE' >&2; exit 1;; esac\n")

    def write(app=GOOD_APP, compose=GOOD_COMPOSE, init=GOOD_INIT, entry=GOOD_ENTRY):
        (web / "app.py").write_text(app)
        (web / "docker-compose.prod.yml").write_text(compose)
        (web / "docker-init.sh").write_text(init)
        (web / "pgbouncer-entrypoint.sh").write_text(entry)

    # 1. app does not set a configurable sslmode -> FAIL.
    write(app="DB_CONFIG = {'host': 'x'}\n")
    assert checks.check_app_db_tls(tmp_path)[0].level == "FAIL", \
        "must FAIL when DB_CONFIG has no configurable sslmode"

    # 2. app cannot pin the peer cert (no sslrootcert) -> FAIL.
    write(app="DB_CONFIG = {'sslmode': os.environ.get('POLARIS_DB_SSLMODE', 'prefer')}\n")
    assert checks.check_app_db_tls(tmp_path)[0].level == "FAIL", \
        "must FAIL when DB_CONFIG cannot pin the peer cert (no POLARIS_DB_SSLROOTCERT/sslrootcert)"

    # 3. compose only encrypts (require), does not verify-ca pin -> FAIL.
    write(compose=GOOD_COMPOSE.replace("POLARIS_DB_SSLMODE: verify-ca", "POLARIS_DB_SSLMODE: require"))
    assert checks.check_app_db_tls(tmp_path)[0].level == "FAIL", \
        "must FAIL when the app hop is only 'require' (encrypt), not verify-ca"

    # 4. pgbouncer backend hop not verify-ca / no CA file -> FAIL.
    write(compose=GOOD_COMPOSE.replace("PGBOUNCER_SERVER_TLS_SSLMODE: verify-ca", "PGBOUNCER_SERVER_TLS_SSLMODE: require"))
    assert checks.check_app_db_tls(tmp_path)[0].level == "FAIL", \
        "must FAIL when the pgbouncer<->postgres hop does not verify-ca pin"

    # 5. entrypoint does not wire the server CA file -> FAIL.
    write(entry="server_tls_sslmode = $X\nclient_tls_sslmode = $Y\n")
    assert checks.check_app_db_tls(tmp_path)[0].level == "FAIL", \
        "must FAIL when the entrypoint does not wire server_tls_ca_file"

    # 6. docker-init does not enable Postgres TLS -> FAIL.
    write(init="echo no tls\n")
    assert checks.check_app_db_tls(tmp_path)[0].level == "FAIL", \
        "must FAIL when docker-init does not enable Postgres ssl"

    # 7. all wired -> OK.
    write()
    assert checks.check_app_db_tls(tmp_path)[0].level == "OK", \
        "must PASS with verify-ca pinning on both hops + sslrootcert + CA file"


def test_correlation_id_check_discriminates(tmp_path):
    web = tmp_path / "polaris_web"
    web.mkdir()
    GOOD_OBS = (
        "import contextvars, re, uuid\n"
        "_RE = re.compile(r'\\A[A-Za-z0-9-]{8,64}\\Z')\n"
        "_v = contextvars.ContextVar('rid', default='-')\n"
        "def validate_or_new_request_id(raw):\n"
        "    if isinstance(raw, str) and _RE.fullmatch(raw):\n"
        "        return raw\n"
        "    return uuid.uuid4().hex\n"
    )
    GOOD_APP = (
        "@app.before_request\n"
        "def _corr():\n"
        "    g._t = observability.set_request_id("
        "observability.validate_or_new_request_id(request.headers.get('X-Request-ID')))\n"
        "@app.teardown_request\n"
        "def _td(e):\n"
        "    reset_request_id(g._t)\n"
        "@app.after_request\n"
        "def _echo(r):\n"
        "    r.headers['X-Request-ID'] = observability.get_request_id()\n"
        "    return r\n"
    )
    GOOD_SEC = "def client_ip():\n    return request.remote_addr\n"

    def write(obs=GOOD_OBS, app=GOOD_APP, sec=GOOD_SEC):
        (web / "observability.py").write_text(obs)
        (web / "app.py").write_text(app)
        (web / "security.py").write_text(sec)

    # 1. all wired correctly -> OK.
    write()
    assert checks.check_correlation_id(tmp_path)[0].level == "OK", \
        "must PASS the correct wiring"

    # 2. unbounded validator (drop the {8,64} length bound) -> FAIL.
    write(obs=GOOD_OBS.replace("{8,64}", "+"))
    assert checks.check_correlation_id(tmp_path)[0].level == "FAIL", \
        "must FAIL when the id length is unbounded (log-injection / memory hole)"

    # 3. no uuid4 generation fallback -> FAIL.
    write(obs=GOOD_OBS.replace("uuid.uuid4().hex", "raw"))
    assert checks.check_correlation_id(tmp_path)[0].level == "FAIL", \
        "must FAIL without a generated id when none is supplied"

    # 4. the id-owning module gains DB access -> FAIL.
    write(obs=GOOD_OBS + "def leak(c):\n    c.execute('INSERT INTO audit VALUES (1)')\n")
    assert checks.check_correlation_id(tmp_path)[0].level == "FAIL", \
        "must FAIL when observability.py can touch the DB"

    # 5. no teardown reset -> FAIL (id leaks across requests).
    write(app=GOOD_APP.replace("reset_request_id(g._t)", "pass"))
    assert checks.check_correlation_id(tmp_path)[0].level == "FAIL", \
        "must FAIL without a teardown reset"

    # 6. set_request_id fed a raw header instead of the validator -> FAIL.
    bad = GOOD_APP.replace(
        "observability.set_request_id(observability.validate_or_new_request_id("
        "request.headers.get('X-Request-ID')))",
        "observability.set_request_id(request.headers.get('X-Request-ID'))")
    write(app=bad)
    assert checks.check_correlation_id(tmp_path)[0].level == "FAIL", \
        "must FAIL when a raw inbound header is bound without validation"

    # 7. VOCATION: the DB-write/audit module references the id -> FAIL.
    write(sec=GOOD_SEC + "def audit():\n    log(get_request_id())\n")
    assert checks.check_correlation_id(tmp_path)[0].level == "FAIL", \
        "must FAIL when security.py references the request id (surveillance vector)"

    # 8. VOCATION: the id co-occurs with an audit call in app.py -> FAIL.
    write(app=GOOD_APP + "    security._audit(get_db, 'X', detail=observability.get_request_id())\n")
    assert checks.check_correlation_id(tmp_path)[0].level == "FAIL", \
        "must FAIL when the id is threaded into an _audit() call"

    # 9. missing files -> FAIL.
    (web / "observability.py").unlink()
    assert checks.check_correlation_id(tmp_path)[0].level == "FAIL", \
        "must FAIL when a wiring file is absent"


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
