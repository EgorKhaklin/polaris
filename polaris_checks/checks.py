"""
polaris_checks — a flat, legible invariant-check layer for Polaris.

This is the clean replacement for the legacy cognitive apparatus. A check is a
check: a plain function that takes the repo root and returns a list of Findings.
No organizational mythology, no simulated economy, no self-referential
governance — just checks.

Each check maps to something real Polaris must hold — most of them to the
C1-C10 constitution (see MISSION.md). They are file-based and deterministic:
no database, no network, no global state, so they run anywhere in well under a
second and gate CI directly.

    from polaris_checks.checks import run_all
    findings = run_all(repo_root)
    fails = [f for f in findings if f.level == "FAIL"]

Add a check by writing a `check_*` function and listing it in CHECKS.
"""

from __future__ import annotations

import pathlib
import re
from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class Finding:
    level: str   # "FAIL" | "WARN" | "OK"
    check: str   # the check's name
    message: str

    def __str__(self) -> str:
        glyph = {"FAIL": "✗", "WARN": "!", "OK": "✓"}.get(self.level, "?")
        return f"  {glyph} [{self.check}] {self.message}"


def _read(root: pathlib.Path, rel: str) -> str:
    p = root / rel
    return p.read_text(encoding="utf-8", errors="replace") if p.is_file() else ""


def _ok(name: str, msg: str) -> list[Finding]:
    return [Finding("OK", name, msg)]


def _fail(name: str, msg: str) -> list[Finding]:
    return [Finding("FAIL", name, msg)]


# ---------------------------------------------------------------------------
# C5 — Content-Security-Policy forbids inline scripts.
# ---------------------------------------------------------------------------
def check_csp_forbids_unsafe_inline(root: pathlib.Path) -> list[Finding]:
    src = _read(root, "polaris_web/security.py")
    if "script-src 'self'" not in src:
        return _fail("csp", "security.py CSP must pin script-src 'self'")
    # C5 is violated only if the script-src directive ITSELF enables
    # 'unsafe-inline'. style-src 'unsafe-inline' is acceptable, so check per
    # directive line, not across the whole file.
    for line in src.splitlines():
        if "script-src" in line and "'unsafe-inline'" in line:
            return _fail("csp", "script-src enables 'unsafe-inline' (C5 violation)")
    return _ok("csp", "CSP pins script-src 'self'; no unsafe-inline on scripts (C5)")


# ---------------------------------------------------------------------------
# C3 — one active identity per person, enforced by a partial unique index.
# ---------------------------------------------------------------------------
def check_one_active_token_index(root: pathlib.Path) -> list[Finding]:
    sql = _read(root, "polaris_sql/02_indexes.sql") + _read(root, "polaris_sql/01_schema.sql")
    if re.search(r"UNIQUE\s+INDEX[^;]*IdentityToken[^;]*WHERE\s+status\s*=\s*'ACTIVE'", sql, re.I | re.S):
        return _ok("c3_one_active", "partial unique index enforces one ACTIVE token per person (C3)")
    return _fail("c3_one_active", "missing partial-unique index for one-active-token (C3)")


# ---------------------------------------------------------------------------
# C1 — audit-of-record append-only triggers on the lifecycle event tables.
# ---------------------------------------------------------------------------
def check_aor_append_only_triggers(root: pathlib.Path) -> list[Finding]:
    triggers = _read(root, "polaris_sql/06_triggers.sql")
    if "insufficient_privilege" not in triggers:
        return _fail("c1_aor", "06_triggers.sql must raise insufficient_privilege on AoR UPDATE/DELETE (C1)")
    n = len(re.findall(r"BEFORE\s+UPDATE\s+OR\s+DELETE", triggers, re.I))
    if n < 1:
        return _fail("c1_aor", "no BEFORE UPDATE OR DELETE append-only triggers found (C1)")
    return _ok("c1_aor", f"{n} append-only audit-of-record trigger(s) present (C1)")


# ---------------------------------------------------------------------------
# C1 — append-only is a PRIVILEGE boundary, not only a trigger.
#
# reject_audit_modification() has a carve-out: it permits UPDATE/DELETE when
# the custom GUC polaris.purge_in_progress is 'TRUE'. Any role can SET a custom
# GUC, so the trigger alone did not stop the application role (polaris_app) from
# deleting an audit row — it could set the GUC and delete. The grant model must
# back the trigger: polaris_app keeps SELECT + INSERT (append-only IS insert-
# allowed) but loses UPDATE/DELETE on every append-only table, so the carve-out
# is unreachable from the app role. The one legitimate DELETE path,
# uc_archive_purge, must be SECURITY DEFINER so it runs the purge with the
# owner's rights inside its admin-gated, checkpoint-writing transaction.
# ---------------------------------------------------------------------------
def check_aor_privilege_boundary(root: pathlib.Path) -> list[Finding]:
    grants = _read(root, "polaris_sql/09_grants.sql")
    # The append-only tables whose trigger honors the purge_in_progress GUC.
    # auditaccesslog is created (and revoked) in its own migration.
    base_tables = [
        "tokenlifecycleevent", "verificationevent", "enrollmentstatusevent",
        "anchorbatch", "tokenstateepochleaf", "duressevent", "authauditlog",
    ]
    if not re.search(r"REVOKE\s+UPDATE\s*,\s*DELETE", grants, re.I):
        return _fail("c1_aor_priv",
                     "09_grants.sql must REVOKE UPDATE, DELETE on append-only tables from polaris_app (C1)")
    missing = [t for t in base_tables if t.lower() not in grants.lower()]
    if missing:
        return _fail("c1_aor_priv",
                     "append-only REVOKE omits table(s): " + ", ".join(missing) + " (C1)")
    # auditaccesslog REVOKE rides along with its migration.
    mig = _read(root, "polaris_sql/migrations/2026-05-15-003-audit-access-log.up.sql")
    if not re.search(r"REVOKE\s+UPDATE\s*,\s*DELETE\s+ON\s+AuditAccessLog", mig, re.I):
        return _fail("c1_aor_priv",
                     "the AuditAccessLog migration must REVOKE UPDATE, DELETE from polaris_app (C1)")
    # The sole legitimate DELETE path must run with the owner's rights.
    proc = _read(root, "polaris_sql/05_procedures.sql")
    m = re.search(r"CREATE\s+OR\s+REPLACE\s+PROCEDURE\s+uc_archive_purge\b.*?\bAS\s*\$\$",
                  proc, re.I | re.S)
    if not m:
        return _fail("c1_aor_priv", "uc_archive_purge procedure not found in 05_procedures.sql (C1)")
    if not re.search(r"SECURITY\s+DEFINER", m.group(0), re.I):
        return _fail("c1_aor_priv",
                     "uc_archive_purge must be SECURITY DEFINER so the purge runs with the "
                     "owner's rights after polaris_app loses direct DELETE (C1)")
    return _ok("c1_aor_priv",
               "append-only tables revoke UPDATE/DELETE from polaris_app; "
               "uc_archive_purge is SECURITY DEFINER (C1)")


# ---------------------------------------------------------------------------
# C7 — cryptographic algorithm is data, not hardcoded.
# ---------------------------------------------------------------------------
def check_crypto_algorithm_is_data(root: pathlib.Path) -> list[Finding]:
    schema = _read(root, "polaris_sql/01_schema.sql")
    if re.search(r"CREATE\s+TABLE\s+CryptographicAlgorithm", schema, re.I):
        return _ok("c7_crypto_data", "CryptographicAlgorithm table holds algorithm metadata (C7)")
    return _fail("c7_crypto_data", "no CryptographicAlgorithm table — algorithm must be data, not hardcoded (C7)")


# ---------------------------------------------------------------------------
# FK discipline — no destructive ON DELETE/UPDATE CASCADE.
# ---------------------------------------------------------------------------
def check_no_fk_cascade(root: pathlib.Path) -> list[Finding]:
    offenders = []
    sqldir = root / "polaris_sql"
    files = []
    if sqldir.is_dir():
        # Scan the base schema AND migrations — a cascade smuggled into a
        # migration is just as destructive as one in 01_schema.sql.
        files = sorted(sqldir.glob("*.sql")) + sorted((sqldir / "migrations").glob("*.sql"))
    for p in files:
        text = re.sub(r"--[^\n]*", "", p.read_text(errors="replace"))  # strip line comments
        for m in re.finditer(r"ON\s+(DELETE|UPDATE)\s+CASCADE", text, re.I):
            offenders.append(f"{p.name}: ON {m.group(1).upper()} CASCADE")
    if offenders:
        return _fail("fk_cascade", "destructive FK cascade(s): " + "; ".join(offenders[:5]))
    return _ok("fk_cascade", "no ON DELETE/UPDATE CASCADE in schema or migrations")


# ---------------------------------------------------------------------------
# Version is canonical — app.py imports __version__ rather than redefining it.
# ---------------------------------------------------------------------------
def check_version_is_canonical(root: pathlib.Path) -> list[Finding]:
    app = _read(root, "polaris_web/app.py")
    if re.search(r"from\s+__version__\s+import|import\s+__version__", app):
        return _ok("version_canonical", "app.py imports the canonical __version__")
    if re.search(r"POLARIS_VERSION\s*=\s*['\"]", app):
        return _fail("version_canonical", "app.py redefines POLARIS_VERSION instead of importing __version__")
    return _ok("version_canonical", "no redefined version literal in app.py")


# ---------------------------------------------------------------------------
# CHANGELOG's top entry matches the current version.
# ---------------------------------------------------------------------------
def check_changelog_matches_version(root: pathlib.Path) -> list[Finding]:
    ver = ""
    m = re.search(r'__version__[^"\'\n]*["\'](\d+\.\d+)["\']', _read(root, "polaris_web/__version__.py"))
    if m:
        ver = m.group(1)
    top = re.search(r"^##\s+v(\d+\.\d+)\b", _read(root, "CHANGELOG.md"), re.M)
    if not ver or not top:
        return _fail("changelog_version", "could not read __version__ or CHANGELOG top entry")
    if top.group(1) != ver:
        return _fail("changelog_version", f"CHANGELOG top is v{top.group(1)} but __version__ is v{ver}")
    return _ok("changelog_version", f"CHANGELOG top entry matches __version__ (v{ver})")


# ---------------------------------------------------------------------------
# Thesis honesty — past the v9.40 terminus, the strong claim must read as RETIRED.
#
# MISSION.md's abandonment clause is mechanical: "if no cold-read attempt occurs
# by v9.40 ... the thesis is documented as inconclusive and the strong claim is
# retired permanently." No external cold read occurred and the repo is past v9.40,
# so docs/THESIS.md must reflect that terminal state — not leave the thesis framed
# as an open, still-pending hypothesis. Leaving the softer wording past the
# deadline is itself the dishonesty the project's discipline forbids. This check
# enforces the constitution's own rule against drift back to the open framing.
# (It does NOT touch MISSION.md's freeze line, which is un-amendable here.)
# ---------------------------------------------------------------------------
def check_thesis_terminus_honest(root: pathlib.Path) -> list[Finding]:
    ver = _read(root, "polaris_web/__version__.py")
    m = re.search(r'__version__[^"\'\n]*["\'](\d+)\.(\d+)["\']', ver)
    if not m:
        return _fail("thesis_terminus", "could not read __version__ for the v9.40 terminus check")
    major, minor = int(m.group(1)), int(m.group(2))
    thesis = _read(root, "docs/THESIS.md")
    if not thesis:
        return _fail("thesis_terminus", "docs/THESIS.md is missing")
    if (major, minor) < (9, 40):
        return _ok("thesis_terminus",
                   f"v{major}.{minor} is before the v9.40 thesis terminus; THESIS.md may remain open")
    # Past v9.40: THESIS.md must state the terminus and the permanent retirement.
    low = thesis.lower()
    missing = [s for s in ("v9.40", "retired") if s.lower() not in low]
    if missing:
        return _fail("thesis_terminus",
                     "past the v9.40 terminus, THESIS.md must document the strong claim as retired "
                     f"(missing term(s): {', '.join(missing)}); the abandonment clause has fired")
    # The stale open-framing must be gone.
    if "until a real cold read happens" in thesis:
        return _fail("thesis_terminus",
                     "THESIS.md still holds the status open 'until a real cold read happens'; the v9.40 "
                     "terminus closed that window (retired by default, reopenable only by recorded decision)")
    if re.search(r"\*\*Status:\*\*\s*HYPOTHESIS-NOT-VERIFIED", thesis):
        return _fail("thesis_terminus",
                     "THESIS.md status is still the open 'HYPOTHESIS-NOT-VERIFIED'; past v9.40 it must "
                     "read as retired / inconclusive")
    return _ok("thesis_terminus",
               "past the v9.40 terminus, THESIS.md documents the strong claim as retired/inconclusive")


# ---------------------------------------------------------------------------
# Secrets hygiene — operator-secrets file is gitignored (no trailing-comment trap).
# ---------------------------------------------------------------------------
def check_secrets_file_ignored(root: pathlib.Path) -> list[Finding]:
    gi = _read(root, ".gitignore")
    # A bare `polaris.env` line (trailing inline comments silently disable the rule).
    if re.search(r"(?m)^\s*polaris\.env\s*$", gi):
        return _ok("secrets_ignored", "polaris.env is gitignored by a bare pattern")
    if "polaris.env" in gi:
        return _fail("secrets_ignored", "polaris.env pattern has a trailing comment — git ignores nothing")
    return _fail("secrets_ignored", "polaris.env (operator secrets) is not gitignored")


def check_gitignore_no_trailing_comments(root: pathlib.Path) -> list[Finding]:
    offenders = []
    for i, line in enumerate(_read(root, ".gitignore").splitlines(), 1):
        s = line.rstrip()
        if not s.strip() or s.lstrip().startswith("#"):
            continue
        if re.search(r"\S +#", s):
            offenders.append(str(i))
    if offenders:
        return _fail("gitignore_comments", f"trailing inline comments disable patterns at line(s) {','.join(offenders)}")
    return _ok("gitignore_comments", "no trailing inline comments in .gitignore")


# ---------------------------------------------------------------------------
# The ZK verdict is two-witnessed (the v9.44 independent verifier exists).
# ---------------------------------------------------------------------------
def check_zk_two_witness_present(root: pathlib.Path) -> list[Finding]:
    if (root / "polaris_zk" / "witness2" / "verifier.py").is_file():
        return _ok("zk_two_witness", "independent second witness present (polaris_zk/witness2)")
    return _fail("zk_two_witness", "the ZK two-witness verifier is missing (polaris_zk/witness2)")


# ---------------------------------------------------------------------------
# No debug artifacts left in source.
# ---------------------------------------------------------------------------
def check_no_debug_artifacts(root: pathlib.Path) -> list[Finding]:
    offenders = []
    for sub in ("polaris_web", "polaris_checks"):
        d = root / sub
        for p in sorted(d.rglob("*.py")) if d.is_dir() else []:
            if "venv" in p.parts or p.name.startswith("test_"):
                continue
            for i, line in enumerate(p.read_text(errors="replace").splitlines(), 1):
                if re.search(r"\b(pdb\.set_trace|breakpoint)\s*\(", line):
                    offenders.append(f"{p.relative_to(root)}:{i}")
    if offenders:
        return _fail("debug_artifacts", "debugger calls in source: " + "; ".join(offenders[:5]))
    return _ok("debug_artifacts", "no pdb/breakpoint debug artifacts in source")


# ---------------------------------------------------------------------------
# Post-quantum signing is wired into issuance, not an island (v9.58).
# The uc1_issue route must route the issuance signature through
# pqc_signing.signature_bytes_for_token(), and uc1_issue_and_activate must
# accept it (p_signature_bytes). Otherwise the headline post-quantum claim
# decays back into a hardcoded SQL string and the signing module is dead code.
# ---------------------------------------------------------------------------
def check_pqc_signing_wired(root: pathlib.Path) -> list[Finding]:
    proc = _read(root, "polaris_sql/05_procedures.sql")
    if "p_signature_bytes" not in proc:
        return _fail("pqc_wired",
                     "uc1_issue_and_activate must accept p_signature_bytes so the app "
                     "supplies the issuance signature (it is a hardcoded SQL string otherwise)")
    app = _read(root, "polaris_web/app.py")
    if "import pqc_signing" not in app:
        return _fail("pqc_wired", "app.py does not import pqc_signing")
    if "signature_bytes_for_token" not in app:
        return _fail("pqc_wired",
                     "app.py does not call pqc_signing.signature_bytes_for_token; the "
                     "issuance signature would bypass the signing module")
    return _ok("pqc_wired",
               "issuance signature routes through pqc_signing.signature_bytes_for_token")


# ---------------------------------------------------------------------------
# Real signing core (production-readiness Wave 2) — a signature that nobody can
# verify against a stable key is theater. pqc_signing must support a PERSISTENT
# signing key (POLARIS_PQC_SIGNING_KEY_FILE), expose generate_keypair + verify,
# and CI must actually exercise the real ML-DSA path (the pqc-real job installs
# liboqs and runs a persistent-key sign+verify). See docs/PRODUCTION-READINESS.md.
# ---------------------------------------------------------------------------
def check_pqc_real_signing(root: pathlib.Path) -> list[Finding]:
    p = _read(root, "polaris_web/pqc_signing.py")
    if not p:
        return _fail("pqc_real", "polaris_web/pqc_signing.py is missing")
    if "POLARIS_PQC_SIGNING_KEY_FILE" not in p:
        return _fail("pqc_real",
                     "pqc_signing.py must load a persistent signing key "
                     "(POLARIS_PQC_SIGNING_KEY_FILE), not generate an ephemeral key per call")
    if "def generate_keypair" not in p or "def verify" not in p:
        return _fail("pqc_real", "pqc_signing.py must expose generate_keypair + verify")
    ci = _read(root, ".github/workflows/ci.yml")
    if "pqc-real" not in ci or "liboqs" not in ci:
        return _fail("pqc_real",
                     "CI must install liboqs and test the real ML-DSA signing path (the pqc-real job)")
    return _ok("pqc_real",
               "real signing core: persistent key + verify, exercised by the CI pqc-real job")


# ---------------------------------------------------------------------------
# The /sql operator console must be read-only at the DATABASE level, not just
# by a first-keyword whitelist. The whitelist accepts WITH, and a data-modifying
# CTE (`WITH t AS (DELETE ... RETURNING *) SELECT * FROM t`) starts with WITH and
# writes. `set_session(readonly=True)` — issued before any statement opens a
# transaction — makes Postgres itself refuse every write on that connection,
# closing the bypass. (A mid-transaction `SET default_transaction_read_only`
# would NOT bind the query's already-started transaction; that subtlety is why
# this needs a DB-backed test, not just this static check.) The grant boundary
# already stops DDL; this stops DML smuggled through the console.
# ---------------------------------------------------------------------------
def check_sql_console_readonly(root: pathlib.Path) -> list[Finding]:
    app = _read(root, "polaris_web/app.py")
    if not app:
        return _fail("sql_console_ro", "polaris_web/app.py is missing")
    m = re.search(r"def sql_query\(.*?\n(?=@app\.route|def [a-z])", app, re.S)
    body = m.group(0) if m else ""
    if not body:
        return _fail("sql_console_ro", "could not locate the sql_query console handler")
    if not re.search(r"set_session\(\s*readonly\s*=\s*True", body):
        return _fail("sql_console_ro",
                     "the /sql console must call conn.set_session(readonly=True) before any "
                     "statement so the database refuses writes — the SELECT/WITH keyword "
                     "whitelist alone is bypassable by a data-modifying CTE")
    return _ok("sql_console_ro",
               "the /sql console sets the session READ ONLY at the DB level "
               "(CTE-smuggled writes are refused by Postgres, not just the keyword gate)")


# ---------------------------------------------------------------------------
# The production image must not carry test frameworks. v9.105 split the single
# requirements.txt into a runtime surface (what the Docker images install) and a
# requirements-dev.txt (pytest, hypothesis, playwright). Test tooling in prod is
# dead weight and extra CVE surface — a pytest CVE (CVE-2025-71176) was riding
# into the image via the shared file. This check keeps the two apart.
# ---------------------------------------------------------------------------
_TEST_ONLY_PKGS = ("pytest", "hypothesis", "playwright")


def check_prod_image_no_test_deps(root: pathlib.Path) -> list[Finding]:
    req = _read(root, "polaris_web/requirements.txt")
    dev = _read(root, "polaris_web/requirements-dev.txt")
    if not req:
        return _fail("prod_no_test_deps", "polaris_web/requirements.txt is missing")
    if not dev:
        return _fail("prod_no_test_deps",
                     "polaris_web/requirements-dev.txt is missing — test tooling must live in a "
                     "separate file so the production image does not install it")
    leaked = [pkg for pkg in _TEST_ONLY_PKGS
              if re.search(rf"(?im)^\s*{re.escape(pkg)}\s*(?:[<>=!~;\[]|$)", req)]
    if leaked:
        return _fail("prod_no_test_deps",
                     "polaris_web/requirements.txt (the prod image surface) lists test-only "
                     "package(s): " + ", ".join(leaked) + " — move them to requirements-dev.txt")
    if not re.search(r"(?m)^\s*-r\s+requirements\.txt", dev):
        return _fail("prod_no_test_deps",
                     "requirements-dev.txt must include the runtime surface via "
                     "`-r requirements.txt` so one install covers run + test")
    for rel in ("polaris_web/Dockerfile", "polaris_web/Dockerfile.prod"):
        df = _read(root, rel)
        if df and "requirements-dev.txt" in df:
            return _fail("prod_no_test_deps",
                         f"{rel} installs requirements-dev.txt — the image must install the "
                         "runtime requirements.txt only (no test frameworks in the image)")
    return _ok("prod_no_test_deps",
               "test tooling is isolated in requirements-dev.txt; the Docker images install the "
               "runtime requirements.txt only (pytest/hypothesis/playwright never ship to prod)")


# ---------------------------------------------------------------------------
# The dependency surface must be CVE-scanned, and the scan must GATE on the
# runtime surface (requirements.txt) — a known CVE in a package the production
# image installs has to fail the build, not ship silently. pip-audit on the dev
# tooling is informational (a test-tool CVE never reaches prod). Dependabot
# opens update PRs for new advisories.
# ---------------------------------------------------------------------------
def check_cve_scanning(root: pathlib.Path) -> list[Finding]:
    ci = _read(root, ".github/workflows/ci.yml")
    if not ci:
        return _fail("cve_scanning", ".github/workflows/ci.yml is missing")
    if "pip-audit" not in ci:
        return _fail("cve_scanning",
                     "CI must run pip-audit to scan dependencies for known CVEs")
    if not re.search(r"pip-audit\s+-r\s+\S*requirements\.txt[^\n]*--strict", ci):
        return _fail("cve_scanning",
                     "the pip-audit run on requirements.txt must be gating (--strict) so a known "
                     "CVE in the production dependency surface fails the build")
    if not (root / ".github" / "dependabot.yml").is_file():
        return _fail("cve_scanning",
                     ".github/dependabot.yml is missing — add Dependabot so new advisories open "
                     "update PRs automatically")
    return _ok("cve_scanning",
               "CI gates on pip-audit of the runtime surface (--strict); Dependabot tracks new "
               "advisories")


# ---------------------------------------------------------------------------
# Static application security testing (SAST). pip-audit covers dependency CVEs;
# bandit covers OUR source for security anti-patterns (hardcoded secrets, weak
# crypto, world-writable files, shell=True, etc.). CI must run it and GATE on
# high-severity findings so a real issue (e.g. the world-writable state dir
# bandit caught at v9.112) fails the build rather than shipping.
# ---------------------------------------------------------------------------
def check_sast_scanning(root: pathlib.Path) -> list[Finding]:
    ci = _read(root, ".github/workflows/ci.yml")
    if not ci:
        return _fail("sast", ".github/workflows/ci.yml is missing")
    if "bandit" not in ci:
        return _fail("sast", "CI must run bandit (SAST) over polaris_web + polaris_cli")
    if not re.search(r"bandit\b[^\n]*--severity-level\s+high", ci):
        return _fail("sast",
                     "the bandit run must GATE on high severity (--severity-level high), so a real "
                     "finding fails the build instead of shipping")
    return _ok("sast", "CI runs bandit SAST gating on high-severity findings")


# ---------------------------------------------------------------------------
# Schema migrations must bound their lock acquisition and statement time. An
# ALTER TABLE that needs an ACCESS EXCLUSIVE lock queues behind any open
# transaction and, once granted, blocks ALL traffic on that table — an
# unbounded wait turns one slow query into a site-wide stall. The migration
# runner must SET LOCAL lock_timeout (fail fast rather than queue) AND
# statement_timeout (cap a runaway migration) inside the apply transaction.
# ---------------------------------------------------------------------------
def check_migration_timeouts(root: pathlib.Path) -> list[Finding]:
    sh = _read(root, "scripts/polaris-migrate.sh")
    if not sh:
        return _fail("migration_timeouts", "scripts/polaris-migrate.sh is missing")
    missing = [name for name in ("lock_timeout", "statement_timeout")
               if not re.search(rf"SET\s+LOCAL\s+{name}\b", sh)]
    if missing:
        return _fail("migration_timeouts",
                     "the migration runner must SET LOCAL " + " and ".join(missing) +
                     " inside the apply transaction so a migration cannot queue on / hold a "
                     "table lock unboundedly and stall all traffic")
    return _ok("migration_timeouts",
               "migrations SET LOCAL lock_timeout + statement_timeout (a blocking ALTER fails "
               "fast instead of stalling the table)")


# ---------------------------------------------------------------------------
# The worker-count knob must actually work. Dockerfile.prod and the prod compose
# advertise WEB_CONCURRENCY (gunicorn's own convention), but gunicorn.conf.py
# read only POLARIS_WORKERS — so setting WEB_CONCURRENCY did nothing and an
# operator scaling the stack with it silently got the default 4 workers (and,
# with no Redis, a per-worker rate limiter at 4x the configured cap). The config
# must honor WEB_CONCURRENCY so the advertised knob is real.
# ---------------------------------------------------------------------------
def check_web_concurrency_honored(root: pathlib.Path) -> list[Finding]:
    conf = _read(root, "polaris_web/gunicorn.conf.py")
    if not conf:
        return _fail("web_concurrency", "polaris_web/gunicorn.conf.py is missing")
    if "WEB_CONCURRENCY" not in conf:
        return _fail("web_concurrency",
                     "gunicorn.conf.py must honor WEB_CONCURRENCY — the Dockerfile.prod and "
                     "docker-compose.prod.yml set it, but the config reads only POLARIS_WORKERS, "
                     "so the advertised scaling knob is inert")
    return _ok("web_concurrency",
               "gunicorn.conf.py honors WEB_CONCURRENCY (the knob the prod image + compose set), "
               "with POLARIS_WORKERS taking precedence")


# ---------------------------------------------------------------------------
# Liveness and readiness are distinct production probes and must not be
# conflated. Liveness ("is the process alive?") must be CHEAP and dependency-
# free: an orchestrator RESTARTS on liveness failure, so checking the DB there
# turns a transient outage into a restart storm. Readiness ("can I serve?") runs
# the dependency checks; its failure STOPS traffic without a restart. The app
# must expose both, the liveness handler must not run the dependency roll-up,
# and the container HEALTHCHECK must use liveness.
# ---------------------------------------------------------------------------
def check_health_liveness_readiness_split(root: pathlib.Path) -> list[Finding]:
    app = _read(root, "polaris_web/app.py")
    if not app:
        return _fail("health_probes", "polaris_web/app.py is missing")
    for route in ("/api/health/live", "/api/health/ready"):
        if route not in app:
            return _fail("health_probes",
                         f"app.py must expose {route} — liveness (cheap, no deps) and readiness "
                         "(dependency roll-up) are distinct production probes")
    m = re.search(r"def api_health_live\(.*?\n(?=@app\.route|def [a-z])", app, re.S)
    live_body = m.group(0) if m else ""
    if live_body and "_compute_readiness" in live_body:
        return _fail("health_probes",
                     "the liveness probe must not run the dependency checks (a DB blip would then "
                     "restart the container); keep /api/health/live cheap")
    df = _read(root, "polaris_web/Dockerfile.prod")
    if df and "/api/health/live" not in df:
        return _fail("health_probes",
                     "the prod HEALTHCHECK should use the liveness probe (/api/health/live), not "
                     "the dependency roll-up, so a transient outage does not restart the container")
    return _ok("health_probes",
               "liveness (/api/health/live, cheap) and readiness (/api/health/ready, deps) are "
               "split; the container HEALTHCHECK uses liveness")


# ---------------------------------------------------------------------------
# Every production-stack container must bound its blast radius: a memory/cpu
# limit (so one runaway container cannot OOM the host) and a rotating log driver
# (so logs cannot fill the disk). Both are per-service config in the prod
# compose. Checked by text (the check layer runs on system python with no
# PyYAML): every service has an image, and the count of deploy-limits + logging
# blocks must cover every service.
# ---------------------------------------------------------------------------
def check_compose_resource_limits(root: pathlib.Path) -> list[Finding]:
    text = _read(root, "polaris_web/docker-compose.prod.yml")
    if not text:
        return _fail("compose_limits", "polaris_web/docker-compose.prod.yml is missing")
    services = len(re.findall(r"(?m)^\s+image:\s", text))
    if services == 0:
        return _fail("compose_limits", "could not find any services in the prod compose")
    deploy_limits = len(re.findall(r"(?m)^\s+limits:\s*$", text))
    logging_blocks = len(re.findall(r"(?m)^\s+logging:\s*$", text))
    if deploy_limits < services:
        return _fail("compose_limits",
                     f"only {deploy_limits}/{services} prod-compose services set "
                     "deploy.resources.limits — one unbounded container can OOM the host")
    if logging_blocks < services:
        return _fail("compose_limits",
                     f"only {logging_blocks}/{services} prod-compose services configure log "
                     "rotation (logging: json-file max-size/max-file) — logs can fill the disk")
    if "max-size" not in text or "memory:" not in text:
        return _fail("compose_limits",
                     "resource limits need a memory bound and log rotation needs a max-size bound")
    return _ok("compose_limits",
               f"all {services} prod-compose services set memory/cpu limits + rotating json-file "
               "logging (no host OOM, no unbounded logs)")


# ---------------------------------------------------------------------------
# The connection pooler must not depend on a third-party image that can vanish.
# bitnami/pgbouncer:1.22 was removed from Docker Hub when Bitnami retired their
# free catalogue (Aug 2025), leaving the prod stack unable to pull its pooler.
# Polaris now builds pgbouncer itself (Dockerfile.pgbouncer, alpine + the distro
# package) and the entrypoint reads the DB password from the file-mounted secret
# (not an env literal). This check keeps the bitnami image from creeping back and
# keeps the secret off the environment.
# ---------------------------------------------------------------------------
def check_pgbouncer_self_built(root: pathlib.Path) -> list[Finding]:
    compose = _read(root, "polaris_web/docker-compose.prod.yml")
    if not compose:
        return _fail("pgbouncer_image", "polaris_web/docker-compose.prod.yml is missing")
    # Docker image refs are case-insensitive and may be quoted; match accordingly.
    if re.search(r"""image:\s*['"]?bitnami/pgbouncer""", compose, re.I):
        return _fail("pgbouncer_image",
                     "the prod compose references bitnami/pgbouncer — that image was removed from "
                     "Docker Hub (Bitnami catalogue retirement); the stack cannot pull it")
    df = _read(root, "polaris_web/Dockerfile.pgbouncer")
    entry = _read(root, "polaris_web/pgbouncer-entrypoint.sh")
    if not df or not entry:
        return _fail("pgbouncer_image",
                     "the self-built pooler needs polaris_web/Dockerfile.pgbouncer + "
                     "pgbouncer-entrypoint.sh")
    # Require an actual `dockerfile: Dockerfile.pgbouncer` build directive, not a
    # passing mention of the filename in a comment.
    if not re.search(r"(?m)^\s*dockerfile:\s*Dockerfile\.pgbouncer\b", compose):
        return _fail("pgbouncer_image",
                     "the pgbouncer service must build from Dockerfile.pgbouncer (a "
                     "`dockerfile:` directive), not pull a third-party image that can disappear")
    # Require the secret to be consumed in code — a `VAR=...POLARIS_DB_PASSWORD_FILE`
    # assignment — not merely named in a comment while the password comes from env.
    if not re.search(r"(?m)^\s*[A-Za-z_][A-Za-z0-9_]*=[^#\n]*POLARIS_DB_PASSWORD_FILE", entry):
        return _fail("pgbouncer_image",
                     "pgbouncer-entrypoint.sh must READ the DB password from the file-mounted "
                     "secret (POLARIS_DB_PASSWORD_FILE), not an environment variable")
    ci = _read(root, ".github/workflows/ci.yml")
    if not ci or "Dockerfile.pgbouncer" not in ci:
        return _fail("pgbouncer_image",
                     "CI must build + exercise the self-built pgbouncer image (Dockerfile.pgbouncer) "
                     "so a broken pooler image is caught in CI, not at deploy")
    return _ok("pgbouncer_image",
               "pgbouncer is self-built from Dockerfile.pgbouncer (no third-party catalog), reads "
               "the file-mounted DB secret (scram on both hops), and is round-tripped in CI")


# ---------------------------------------------------------------------------
# Docker image completeness — every LOCAL module app.py imports must be COPYd
# into both images, or the container ModuleNotFoundErrors at startup and crash-
# loops. This has bitten twice: observability.py (v9.40) and pqc_signing.py
# (v9.58, which crashed the dev + prod images until v9.94). The narrow
# "copies security.py" doctor check did not generalize; this does.
# ---------------------------------------------------------------------------
def check_dockerfile_copies_app_modules(root: pathlib.Path) -> list[Finding]:
    app = _read(root, "polaris_web/app.py")
    web = root / "polaris_web"
    if not app:
        return _fail("dockerfile_modules", "polaris_web/app.py is missing")
    # Local modules = `import X` / `from X import` where polaris_web/X.py exists.
    # Tolerate trailing comments on the import line (the v9.40 miss was a regex
    # that did not).
    imported = set(re.findall(r"^\s*(?:import|from)\s+([A-Za-z_]\w*)", app, re.M))
    local = sorted(m for m in imported if (web / f"{m}.py").is_file())
    if not local:
        return _fail("dockerfile_modules", "could not resolve app.py's local module imports")
    for rel in ("polaris_web/Dockerfile", "polaris_web/Dockerfile.prod"):
        df = _read(root, rel)
        if not df:
            continue
        copy_lines = " ".join(l for l in df.splitlines() if l.lstrip().upper().startswith("COPY"))
        copied = set(re.findall(r"\b([A-Za-z_]\w*)\.py\b", copy_lines))
        missing = [m for m in local if m not in copied]
        if missing:
            return _fail("dockerfile_modules",
                         f"{rel} does not COPY local module(s) app.py imports: "
                         + ", ".join(missing) + " — the container will ModuleNotFoundError at startup")
    return _ok("dockerfile_modules",
               f"both Dockerfiles COPY every local app module ({', '.join(local)})")


# ---------------------------------------------------------------------------
# C2 — ZERO_KNOWLEDGE verifications must not carry a token_id. Enforced by a
# CHECK constraint on VerificationEvent, not by application policy.
# ---------------------------------------------------------------------------
def check_c2_zk_token_null(root: pathlib.Path) -> list[Finding]:
    schema = _read(root, "polaris_sql/01_schema.sql")
    if ("chk_disclosure_token_consistency" in schema
            and re.search(r"ZERO_KNOWLEDGE'\s+AND\s+token_id\s+IS\s+NULL", schema, re.I)):
        return _ok("c2_zk_null", "ZERO_KNOWLEDGE verifications are forbidden from carrying token_id (C2)")
    return _fail("c2_zk_null", "no CHECK forces token_id NULL on ZERO_KNOWLEDGE verification events (C2)")


# ---------------------------------------------------------------------------
# C4 — the failed-login counter increments atomically (no TOCTOU race): a
# single UPDATE that references the column, not a read-then-write.
# ---------------------------------------------------------------------------
def check_c4_atomic_failed_login(root: pathlib.Path) -> list[Finding]:
    sec = _read(root, "polaris_web/security.py")
    if re.search(r"failed_login_count\s*=\s*failed_login_count\s*\+\s*1", sec):
        return _ok("c4_atomic_login", "failed-login counter increments atomically in one UPDATE (C4)")
    return _fail("c4_atomic_login", "no atomic 'failed_login_count = failed_login_count + 1' UPDATE in security.py (C4)")


# ---------------------------------------------------------------------------
# C8 — /api/atlas/* result sets are bounded by hard caps.
# ---------------------------------------------------------------------------
def check_c8_atlas_caps(root: pathlib.Path) -> list[Finding]:
    app = _read(root, "polaris_web/app.py")
    missing = [c for c in ("_ATLAS_MAX_CLUSTERS", "_ATLAS_MAX_POINTS", "_ATLAS_MAX_EVENTS") if c not in app]
    if missing:
        return _fail("c8_atlas_caps", "missing atlas hard-cap constant(s): " + ", ".join(missing) + " (C8)")
    return _ok("c8_atlas_caps", "/api/atlas/* endpoints have hard result-set caps (C8)")


# ---------------------------------------------------------------------------
# C9 — concurrency hazards are tested with real threading, not mocks.
# ---------------------------------------------------------------------------
def check_c9_concurrency_threading(root: pathlib.Path) -> list[Finding]:
    t = _read(root, "polaris_web/test_app.py")
    if "class ConcurrencyTests" in t and re.search(r"threading\.Thread", t):
        return _ok("c9_concurrency", "ConcurrencyTests exercises real threading (C9)")
    return _fail("c9_concurrency", "no ConcurrencyTests with threading.Thread in test_app.py (C9)")


# ---------------------------------------------------------------------------
# C10 — identity is not money: the schema carries no monetary primitives.
# ---------------------------------------------------------------------------
def check_c10_no_money_tables(root: pathlib.Path) -> list[Finding]:
    schema = _read(root, "polaris_sql/01_schema.sql")
    bad = re.findall(r"CREATE TABLE\s+(\w*(?:Monetary|Balance|Payment|Wallet|Merchant|Spending)\w*)", schema, re.I)
    if bad:
        return _fail("c10_no_money", "schema defines monetary table(s): " + ", ".join(bad[:5]) + " (C10)")
    return _ok("c10_no_money", "schema carries no monetary primitives; identity is not money (C10)")


# ---------------------------------------------------------------------------
# Open redirect (CWE-601) — every post-login ?next= redirect routes through
# one guard that rejects off-site targets, including the backslash trick that
# browsers normalize to '//host'. The naive '//'-only guard must not survive.
# ---------------------------------------------------------------------------
def check_open_redirect_guard(root: pathlib.Path) -> list[Finding]:
    sec = _read(root, "polaris_web/security.py")
    if "def is_safe_next_url" not in sec:
        return _fail("open_redirect", "security.py must define the is_safe_next_url guard (CWE-601)")
    app = _read(root, "polaris_web/app.py")
    if "startswith('//')" in app:
        return _fail("open_redirect",
                     "app.py still uses the naive startswith('//') next-url guard; "
                     "route ?next= through security.is_safe_next_url (CWE-601)")
    if "is_safe_next_url" not in app:
        return _fail("open_redirect", "app.py must route ?next= through security.is_safe_next_url (CWE-601)")
    return _ok("open_redirect",
               "post-login ?next= routed through is_safe_next_url; the naive '//'-only guard is gone (CWE-601)")


# ---------------------------------------------------------------------------
# Session cookie Secure flag (CWE-614) — mandatory in production, not opt-in.
# ---------------------------------------------------------------------------
def check_cookie_secure_in_production(root: pathlib.Path) -> list[Finding]:
    app = _read(root, "polaris_web/app.py")
    m = re.search(r"SESSION_COOKIE_SECURE'\]\s*=\s*(.+)", app)
    if not m:
        return _fail("cookie_secure", "app.py does not set SESSION_COOKIE_SECURE")
    if "_PRODUCTION" not in m.group(1):
        return _fail("cookie_secure",
                     "SESSION_COOKIE_SECURE is opt-in only; force it on in production via _PRODUCTION (CWE-614)")
    return _ok("cookie_secure", "SESSION_COOKIE_SECURE is forced on in production (CWE-614)")


# ---------------------------------------------------------------------------
# Prod deploy — the polaris_app role password must be synced to the generated
# secret, not left at the dev default from 09_grants.sql.
#
# The app and pgbouncer authenticate as polaris_app with the file-mounted
# secret /run/secrets/polaris_db_password. 09_grants.sql creates the role with
# 'polaris_dev_password'. If docker-init.sh never rotates the role to the
# secret, the role keeps the dev password while its clients present the
# generated one — prod auth breaks, or the dev password is what is live. The
# postgres service must therefore point POLARIS_APP_PASSWORD_FILE at the SAME
# secret the app reads, and docker-init.sh must read it and ALTER the role.
# ---------------------------------------------------------------------------
def check_prod_app_password_synced(root: pathlib.Path) -> list[Finding]:
    compose = _read(root, "polaris_web/docker-compose.prod.yml")
    init = _read(root, "polaris_web/docker-init.sh")
    if not compose or not init:
        return _fail("prod_pw_sync", "docker-compose.prod.yml or docker-init.sh missing")
    app_secret = re.search(r"POLARIS_DB_PASSWORD_FILE:\s*(\S+)", compose)
    role_secret = re.search(r"POLARIS_APP_PASSWORD_FILE:\s*(\S+)", compose)
    if app_secret is None:
        return _fail("prod_pw_sync", "compose does not set POLARIS_DB_PASSWORD_FILE for the app")
    if role_secret is None:
        return _fail("prod_pw_sync",
                     "compose never sets POLARIS_APP_PASSWORD_FILE — the polaris_app role keeps the "
                     "dev password while the app authenticates with the generated secret")
    if app_secret.group(1) != role_secret.group(1):
        return _fail("prod_pw_sync",
                     f"role password secret ({role_secret.group(1)}) differs from the app's "
                     f"({app_secret.group(1)}); they must be the same file")
    if "POLARIS_APP_PASSWORD_FILE" not in init:
        return _fail("prod_pw_sync", "docker-init.sh does not read POLARIS_APP_PASSWORD_FILE")
    if not re.search(r"ALTER\s+ROLE\s+polaris_app", init, re.I):
        return _fail("prod_pw_sync", "docker-init.sh does not ALTER ROLE polaris_app to the secret")
    return _ok("prod_pw_sync",
               f"prod syncs the polaris_app role password to the app's secret ({app_secret.group(1)})")


# ---------------------------------------------------------------------------
# Production hardening — two BLOCKER-class defaults must not survive into prod:
#   1. The SQL seed loads demo accounts with publicly-known passwords
#      (admin/Admin@123! ...) and a demo duress code. docker-init.sh must
#      neutralize them when POLARIS_ENV=production (disable + scramble).
#   2. The rate limiter silently falls back to per-worker in-memory unless
#      POLARIS_REDIS_URL is set; prod runs 4 workers, so per-IP limits would
#      fragment 4x. The prod compose must wire POLARIS_REDIS_URL.
# (Part of the v9.101+ production-readiness arc; see docs/PRODUCTION-READINESS.md.)
# ---------------------------------------------------------------------------
def check_prod_hardening(root: pathlib.Path) -> list[Finding]:
    init = _read(root, "polaris_web/docker-init.sh")
    compose = _read(root, "polaris_web/docker-compose.prod.yml")
    if not init:
        return _fail("prod_hardening", "polaris_web/docker-init.sh is missing")
    # 1. Demo accounts neutralized in production.
    prod_block = re.search(r'POLARIS_ENV.*?production.*?(?=\nfi\b|\Z)', init, re.S)
    if not (prod_block and "is_active" in prod_block.group(0)
            and re.search(r"'admin',\s*'operator',\s*'auditor'", prod_block.group(0))):
        return _fail("prod_hardening",
                     "docker-init.sh must disable the demo accounts (admin/operator/auditor) when "
                     "POLARIS_ENV=production — they ship with publicly-known passwords")
    # 2. Prod rate limiter uses Redis, not the per-worker in-memory fallback.
    if not re.search(r"POLARIS_REDIS_URL:\s*\S+", compose):
        return _fail("prod_hardening",
                     "docker-compose.prod.yml must set POLARIS_REDIS_URL so the rate limiter uses the "
                     "cross-worker Redis backend (else per-IP limits fragment across the 4 workers)")
    return _ok("prod_hardening",
               "prod neutralizes demo accounts and wires the Redis rate limiter")


# ---------------------------------------------------------------------------
# Backup at-rest encryption — DB backups are a full pg_dump of (would-be)
# national-identity data; they must not sit in plaintext. polaris-backup.sh must
# support encrypting to POLARIS_BACKUP_KEY_FILE and polaris-restore.sh must
# decrypt .enc backups (production-readiness Wave 3, v9.102).
# ---------------------------------------------------------------------------
def check_backup_encryption(root: pathlib.Path) -> list[Finding]:
    bk = _read(root, "scripts/polaris-backup.sh")
    rs = _read(root, "scripts/polaris-restore.sh")
    if not bk or not rs:
        return _fail("backup_encryption", "backup/restore scripts missing")
    if "POLARIS_BACKUP_KEY_FILE" not in bk or "openssl enc" not in bk:
        return _fail("backup_encryption",
                     "polaris-backup.sh must support at-rest encryption (POLARIS_BACKUP_KEY_FILE + openssl)")
    if "openssl enc -d" not in rs or ".enc" not in rs:
        return _fail("backup_encryption",
                     "polaris-restore.sh must decrypt encrypted (.enc) backups")
    return _ok("backup_encryption",
               "backups support at-rest encryption (POLARIS_BACKUP_KEY_FILE) and restore decrypts them")


# ---------------------------------------------------------------------------
# Doc/schema drift — the headline architecture doc must state the real number
# of tables. A reviewer reads this number; it must not contradict the schema.
# ---------------------------------------------------------------------------
def check_table_count_matches_doc(root: pathlib.Path) -> list[Finding]:
    schema = _read(root, "polaris_sql/01_schema.sql")
    n = len(re.findall(r"^CREATE TABLE ", schema, re.M))
    # Every doc that states a schema-table count must match the real schema. Both
    # ARCHITECTURE-OVERVIEW.md ("N tables") and README.md ("N schema tables")
    # carry one; the README's drifted to 26 while the schema reached 27 (v9.89)
    # because only the architecture doc was guarded. Guard both.
    docs = [
        ("docs/ARCHITECTURE-OVERVIEW.md", r"(\d+)\s+tables"),
        ("README.md", r"(\d+)\s+schema tables"),
    ]
    for rel, pat in docs:
        m = re.search(pat, _read(root, rel))
        if not m:
            return _fail("table_count", f"{rel} states no schema-table count")
        stated = int(m.group(1))
        if stated != n:
            return _fail("table_count",
                         f"{rel} says {stated} tables but the schema defines {n}")
    return _ok("table_count", f"doc table counts match the schema ({n})")


# ---------------------------------------------------------------------------
# Launcher currency — the macOS launcher (the SCS-230 deliverable surface) must
# track the real stack, not drift. Pin the three properties that went stale: it
# installs native deps from requirements.txt (not a hardcoded list that misses
# prometheus_client/redis/hypothesis/pytest), its `test` command runs the
# canonical suite (not just test_app), and it builds/points at the ZK binary so
# /api/zk/* is not silently dead on a native launch.
# ---------------------------------------------------------------------------
def check_launcher_current(root: pathlib.Path) -> list[Finding]:
    sh = _read(root, "polaris_mac_launch.sh")
    if not sh:
        return _fail("launcher_current", "polaris_mac_launch.sh is missing")
    # Installs via `pip install ... -r <…>` AND the file it points at is
    # requirements.txt (referenced directly or through a variable).
    if not (re.search(r"pip install[^\n]*\s-r\b", sh) and "requirements.txt" in sh):
        return _fail("launcher_current",
                     "the launcher must install native deps from requirements.txt, not a hardcoded list")
    if re.search(r"pip install[^\n]*\bflask\b[^\n]*\bpsycopg2-binary\b[^\n]*\bgunicorn\b", sh):
        return _fail("launcher_current",
                     "the launcher still pip-installs a hardcoded package list; use requirements.txt")
    missing = [s for s in ("polaris_checks", "test_check_constraints",
                           "test_invariants_property", "test_redaction_property")
               if s not in sh]
    if missing:
        return _fail("launcher_current",
                     "the launcher's test command omits canonical suite(s): " + ", ".join(missing))
    if "polaris-zk" not in sh and "POLARIS_ZK_BINARY" not in sh:
        return _fail("launcher_current",
                     "the launcher never builds or references the ZK binary; /api/zk/* would be dead natively")
    return _ok("launcher_current",
               "launcher installs from requirements.txt, runs the canonical suite, and builds the ZK binary")


# ---------------------------------------------------------------------------
# Local-wall-clock convention — the DB stores TIMESTAMP-without-zone and app+DB
# are co-located, so every Python boundary compares against datetime.now().
# A datetime.utcnow() would silently shift the boundary by the server's UTC
# offset (and is deprecated). One such bug shipped in the ZK epoch check.
# ---------------------------------------------------------------------------
def check_local_clock_convention(root: pathlib.Path) -> list[Finding]:
    app = _read(root, "polaris_web/app.py")
    if "utcnow" in app:
        return _fail("local_clock",
                     "app.py references utcnow; the DB stores local-wall-clock "
                     "TIMESTAMPs, so compare against datetime.now() (see the atlas TZ note)")
    return _ok("local_clock", "app.py uses local-wall-clock datetime.now() for boundaries, never utcnow()")


# ---------------------------------------------------------------------------
# C6 (server-side disclosure) — ZERO_KNOWLEDGE verification location must be
# redacted/excluded at EVERY read path, not just uc7_warrant_audit. The atlas
# spatial layers and the /verifications list would otherwise expose the precise
# location that de-anonymizes a ZK holder (spatial side-channel).
# ---------------------------------------------------------------------------
def check_c6_atlas_redacts_zk_location(root: pathlib.Path) -> list[Finding]:
    atlas = _read(root, "polaris_sql/11_atlas.sql")
    excludes = atlas.count("disclosure_level <> 'ZERO_KNOWLEDGE'")
    if excludes < 2:
        return _fail("c6_atlas_zk",
                     "atlas verification points + clusters must exclude ZERO_KNOWLEDGE "
                     f"(found {excludes} exclusion clause(s), need >=2) (C6)")
    if "THEN NULL ELSE tv.latitude" not in atlas:
        return _fail("c6_atlas_zk",
                     "atlas_recent_events must NULL lat/lon for ZERO_KNOWLEDGE rows (C6)")
    app = _read(root, "polaris_web/app.py")
    if app.count("THEN NULL ELSE ve.requestor_location") < 2:
        return _fail("c6_atlas_zk",
                     "app.py /verifications + /atlas must redact requestor_location "
                     "for ZERO_KNOWLEDGE (C6)")
    return _ok("c6_atlas_zk",
               "ZK verification location is excluded/redacted at the atlas + list read paths (C6)")


# ---------------------------------------------------------------------------
# Vocation (anti-coercion) — the coercion-evidence trail must NOT be redacted.
#
# VerificationEvent.requesting_purpose_text is operator-supplied free text: a
# coerced verification leaves the coercer's stated purpose on the permanent
# record (the evidentiary chain). It is deliberately RETAINED on every
# disclosure level, ZERO_KNOWLEDGE included — UNLIKE requestor_location, which
# IS ZK-redacted (C6, the check above). Pass-7 found a stale schema comment that
# falsely called it "redacted for ZERO_KNOWLEDGE rows at read"; a well-meaning
# engineer reading that could add a redaction CASE and silently destroy the
# anti-coercion feature. This guards against exactly that: the evidence trail
# must never be NULLed for ZK rows at a read path, and the canonical schema must
# not falsely claim it is.
# ---------------------------------------------------------------------------
def check_coercion_evidence_retained(root: pathlib.Path) -> list[Finding]:
    schema = _read(root, "polaris_sql/01_schema.sql")
    if "requesting_purpose_text" not in schema:
        return _fail("vocation_coercion_evidence",
                     "VerificationEvent.requesting_purpose_text (the coercion-evidence trail) is missing")
    # The canonical schema must not FALSELY claim the evidence trail is redacted
    # (the stale comment that invited the confusion). The same phrase legitimately
    # describes requestor_location elsewhere, so only flag it when it sits in the
    # comment block immediately preceding the requesting_purpose_text column.
    col_at = schema.find("requesting_purpose_text VARCHAR")
    false_claim = "is redacted for ZERO_KNOWLEDGE rows at read"
    claim_at = schema.rfind(false_claim, 0, col_at) if col_at != -1 else -1
    if claim_at != -1 and (col_at - claim_at) < 400:
        return _fail("vocation_coercion_evidence",
                     "01_schema.sql falsely documents requesting_purpose_text as ZK-redacted; it is "
                     "the deliberately-retained anti-coercion evidentiary trail (Vocation)")
    # No read path may redact the evidence trail to NULL for ZERO_KNOWLEDGE rows.
    reads = (_read(root, "polaris_web/app.py")
             + _read(root, "polaris_sql/11_atlas.sql")
             + _read(root, "polaris_sql/05_procedures.sql"))
    if re.search(r"THEN\s+NULL\s+ELSE[^;]*requesting_purpose_text", reads, re.I | re.S) or \
       re.search(r"requesting_purpose_text[^;]*ZERO_KNOWLEDGE[^;]*THEN\s+NULL", reads, re.I | re.S):
        return _fail("vocation_coercion_evidence",
                     "a read path redacts requesting_purpose_text for ZERO_KNOWLEDGE rows — that "
                     "destroys the anti-coercion evidentiary trail it exists to create (Vocation)")
    return _ok("vocation_coercion_evidence",
               "the coercion-evidence trail (requesting_purpose_text) is retained, not ZK-redacted (Vocation)")


# ---------------------------------------------------------------------------
# R2 anti-replay — /api/zk/verify must consume a single-use nonce.
#
# A proof bundle is bound to (epoch_id, context_id, nonce), which prevents proof
# SUBSTITUTION. It does NOT prevent REPLAY on its own: the identical bundle,
# captured off the wire, verifies again. The verify route must consume the nonce
# (insert into the single-use ZkVerificationNonce store) on a verified result and
# reject a second submission of the same tuple. Closes threat-model T-T2.
# ---------------------------------------------------------------------------
def check_zk_verify_anti_replay(root: pathlib.Path) -> list[Finding]:
    schema = _read(root, "polaris_sql/01_schema.sql")
    app = _read(root, "polaris_web/app.py")
    if "CREATE TABLE ZkVerificationNonce" not in schema:
        return _fail("zk_anti_replay",
                     "ZkVerificationNonce single-use nonce store is missing from the schema (R2/T-T2)")
    if "INSERT INTO ZkVerificationNonce" not in app:
        return _fail("zk_anti_replay",
                     "/api/zk/verify does not consume the nonce — a verified bundle replays (R2/T-T2)")
    if "replay" not in app.lower():
        return _fail("zk_anti_replay",
                     "/api/zk/verify consumes the nonce but never rejects the replay case (R2/T-T2)")
    return _ok("zk_anti_replay",
               "/api/zk/verify consumes a single-use nonce; replays are rejected (R2/T-T2)")


# ---------------------------------------------------------------------------
# Schema completeness — every column a migration ADDs to an existing table must
# also be declared in 01_schema.sql, so the canonical schema is complete on its
# own and a cold reader (or a fresh 01_schema build) never silently lacks a
# column the app writes. The migrations stay (idempotent) for deployed DBs.
# ---------------------------------------------------------------------------
def check_no_migration_column_drift(root: pathlib.Path) -> list[Finding]:
    schema = _read(root, "polaris_sql/01_schema.sql")
    mig_dir = root / "polaris_sql" / "migrations"
    missing = []
    if mig_dir.is_dir():
        for path in sorted(mig_dir.glob("*.up.sql")):
            text = path.read_text(encoding="utf-8")
            for m in re.finditer(r"ADD COLUMN(?:\s+IF NOT EXISTS)?\s+(\w+)", text, re.I):
                col = m.group(1)
                if not re.search(rf"\b{re.escape(col)}\b", schema):
                    missing.append(f"{path.name}:{col}")
    if missing:
        return _fail("migration_drift",
                     "migration-added column(s) missing from 01_schema.sql: "
                     + ", ".join(missing[:6]))
    return _ok("migration_drift",
               "every migration-added column is declared in 01_schema.sql (no schema drift)")


# ---------------------------------------------------------------------------
# Operator-script argument validation — the operator shell scripts interpolate
# argv into superuser `psql -c` statements, so every SQL-bound argument must be
# regex-validated (numeric / username format) before use or it is a SQL
# injection (multi-statement) as postgres.
# ---------------------------------------------------------------------------
def check_operator_scripts_validate_argv(root: pathlib.Path) -> list[Finding]:
    required = [
        # (script, marker that proves the SQL-bound arg is regex-validated)
        ("scripts/polaris-recover-admin.sh", r"TARGET.*=~|=~[^\n]*\[a-z0-9\._-\]\{3,50\}"),
        ("scripts/polaris-purge.sh",        r"ACTOR_USER_ID[^\n]*=~[^\n]*\^\[0-9\]\+\$"),
        ("scripts/polaris-migrate.sh",      r"ACTOR_USER_ID[^\n]*=~[^\n]*\^\[0-9\]\+\$"),
        ("scripts/polaris-archive.sh",      r"CUTOFF_DAYS[^\n]*=~[^\n]*\^\[0-9\]\+\$"),
    ]
    missing = []
    for rel, pat in required:
        if not re.search(pat, _read(root, rel)):
            missing.append(rel.split("/")[-1])
    if missing:
        return _fail("script_argv",
                     "operator script(s) missing SQL-arg validation (injection risk): "
                     + ", ".join(missing))
    return _ok("script_argv",
               "operator scripts regex-validate SQL-bound argv (recover/purge/migrate/archive)")


CHECKS: list[Callable[[pathlib.Path], list[Finding]]] = [
    check_csp_forbids_unsafe_inline,
    check_one_active_token_index,
    check_aor_append_only_triggers,
    check_aor_privilege_boundary,
    check_crypto_algorithm_is_data,
    check_no_fk_cascade,
    check_version_is_canonical,
    check_changelog_matches_version,
    check_thesis_terminus_honest,
    check_secrets_file_ignored,
    check_gitignore_no_trailing_comments,
    check_zk_two_witness_present,
    check_no_debug_artifacts,
    check_pqc_signing_wired,
    check_pqc_real_signing,
    check_sql_console_readonly,
    check_prod_image_no_test_deps,
    check_cve_scanning,
    check_sast_scanning,
    check_migration_timeouts,
    check_web_concurrency_honored,
    check_health_liveness_readiness_split,
    check_compose_resource_limits,
    check_pgbouncer_self_built,
    check_dockerfile_copies_app_modules,
    check_c2_zk_token_null,
    check_c4_atomic_failed_login,
    check_c8_atlas_caps,
    check_c9_concurrency_threading,
    check_c10_no_money_tables,
    check_open_redirect_guard,
    check_cookie_secure_in_production,
    check_prod_app_password_synced,
    check_prod_hardening,
    check_backup_encryption,
    check_table_count_matches_doc,
    check_launcher_current,
    check_local_clock_convention,
    check_c6_atlas_redacts_zk_location,
    check_coercion_evidence_retained,
    check_zk_verify_anti_replay,
    check_no_migration_column_drift,
    check_operator_scripts_validate_argv,
]


def run_all(repo_root: pathlib.Path) -> list[Finding]:
    """Run every check against repo_root. Deterministic; order-stable."""
    findings: list[Finding] = []
    for check in CHECKS:
        try:
            findings.extend(check(repo_root))
        except Exception as exc:  # a check must never crash the run
            findings.append(Finding("FAIL", check.__name__, f"check raised {type(exc).__name__}: {exc}"))
    return findings
