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
    for p in sorted(sqldir.glob("*.sql")) if sqldir.is_dir() else []:
        text = re.sub(r"--[^\n]*", "", p.read_text(errors="replace"))  # strip line comments
        for m in re.finditer(r"ON\s+(DELETE|UPDATE)\s+CASCADE", text, re.I):
            offenders.append(f"{p.name}: ON {m.group(1).upper()} CASCADE")
    if offenders:
        return _fail("fk_cascade", "destructive FK cascade(s): " + "; ".join(offenders[:5]))
    return _ok("fk_cascade", "no ON DELETE/UPDATE CASCADE in schema")


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
# Doc/schema drift — the headline architecture doc must state the real number
# of tables. A reviewer reads this number; it must not contradict the schema.
# ---------------------------------------------------------------------------
def check_table_count_matches_doc(root: pathlib.Path) -> list[Finding]:
    schema = _read(root, "polaris_sql/01_schema.sql")
    n = len(re.findall(r"^CREATE TABLE ", schema, re.M))
    doc = _read(root, "docs/ARCHITECTURE-OVERVIEW.md")
    m = re.search(r"(\d+)\s+tables", doc)
    if not m:
        return _fail("table_count", "ARCHITECTURE-OVERVIEW.md states no table count")
    stated = int(m.group(1))
    if stated != n:
        return _fail("table_count",
                     f"ARCHITECTURE-OVERVIEW.md says {stated} tables but the schema defines {n}")
    return _ok("table_count", f"ARCHITECTURE-OVERVIEW.md table count matches the schema ({n})")


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
    check_crypto_algorithm_is_data,
    check_no_fk_cascade,
    check_version_is_canonical,
    check_changelog_matches_version,
    check_secrets_file_ignored,
    check_gitignore_no_trailing_comments,
    check_zk_two_witness_present,
    check_no_debug_artifacts,
    check_pqc_signing_wired,
    check_c2_zk_token_null,
    check_c4_atomic_failed_login,
    check_c8_atlas_caps,
    check_c9_concurrency_threading,
    check_c10_no_money_tables,
    check_open_redirect_guard,
    check_cookie_secure_in_production,
    check_table_count_matches_doc,
    check_local_clock_convention,
    check_c6_atlas_redacts_zk_location,
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
