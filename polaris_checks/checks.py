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
