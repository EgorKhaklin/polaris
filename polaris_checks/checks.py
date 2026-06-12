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
        # v9.125: the right-to-erasure log is append-only (the record that an
        # erasure happened must not be editable or removable).
        "individualerasureevent",
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
    # Issuance must route through the signing module — either the 2-tuple
    # signature_bytes_for_token or the 3-tuple signature_with_key_for_token
    # (v9.117, which also surfaces the public key to store with the signature).
    if not re.search(r"pqc_signing\.signature_(bytes_for_token|with_key_for_token)", app):
        return _fail("pqc_wired",
                     "app.py does not call pqc_signing.signature_bytes_for_token / "
                     "signature_with_key_for_token; the issuance signature would bypass the "
                     "signing module")
    # v9.119: uc6 algorithm-migration must also route through the signing module,
    # not write a hardcoded operator string.
    if "UC6_OPERATOR_MIGRATE" in app:
        return _fail("pqc_wired",
                     "uc6 still writes a hardcoded UC6_OPERATOR_MIGRATE signature; route the "
                     "migration signature through pqc_signing like issuance")
    return _ok("pqc_wired",
               "issuance + uc6 migration signatures route through the pqc_signing module")


# ---------------------------------------------------------------------------
# The production signing key MUST be generated as clean JSON. liboqs-python
# prints a banner to STDOUT at import; polaris-generate-secrets.sh mints the key
# by capturing a `python -c "...print(json.dumps(generate_keypair()))"` stdout,
# so a naive capture prepends the banner and produces a malformed key file the
# app refuses to load — real-PQC issuance broken at deploy (v9.139). Two
# defenses must be present: the generator swallows stdout during the import (so
# no banner can leak into the JSON), AND it validates the captured output parses
# as ML-DSA-65 key JSON before writing (fail loud, never write a malformed key).
# ---------------------------------------------------------------------------
def check_signing_key_generation(root: pathlib.Path) -> list[Finding]:
    sh = _read(root, "scripts/polaris-generate-secrets.sh")
    if not sh:
        return _fail("signing_key_gen", "scripts/polaris-generate-secrets.sh is missing")
    if "generate_keypair" not in sh:
        return _fail("signing_key_gen",
                     "polaris-generate-secrets.sh must mint the ML-DSA-65 signing key "
                     "(pqc_signing.generate_keypair)")
    # Defense 1: stdout swallowed during import so the liboqs banner cannot leak.
    if "io.StringIO()" not in sh or "sys.stdout" not in sh:
        return _fail("signing_key_gen",
                     "the signing-key generator must swallow stdout during the pqc import "
                     "(sys.stdout = io.StringIO()) so the liboqs banner cannot corrupt the key JSON")
    # Defense 2: validate the captured JSON before writing (fail loud).
    if not re.search(r"json\.load.*algorithm.*ML-DSA-65|ML-DSA-65.*secret_key_hex", sh, re.S):
        return _fail("signing_key_gen",
                     "the generator must VALIDATE the captured output is ML-DSA-65 key JSON "
                     "(algorithm + secret_key_hex + public_key_hex) before writing it")
    # The existence guards must be -s (non-empty), not -e, so an interrupted run's
    # 0-byte files are regenerated rather than silently shipped as empty secrets.
    if re.search(r"\[\[\s*-e\s+\"\$\{target\}\"\s*\]\]", sh):
        return _fail("signing_key_gen",
                     "secret existence guards must test -s (non-empty), not -e: a 0-byte file "
                     "from an interrupted run would silently block regeneration")
    return _ok("signing_key_gen",
               "the signing-key generator swallows the import banner, validates the key JSON "
               "before writing, and regenerates empty files (-s guard)")


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
# Verification must be ENFORCED, not just possible. A signing core where
# verify() is never called is theater. Two live obligations: (1) issuance
# self-verifies the signature it produces (signature_bytes_for_token calls
# verify) and refuses to persist one that does not check out; (2) a use-path
# primitive (verify_token_signature) checks a stored signature against the
# published trust anchor, exercised in the pqc-real CI job.
# ---------------------------------------------------------------------------
def check_verify_enforced(root: pathlib.Path) -> list[Finding]:
    p = _read(root, "polaris_web/pqc_signing.py")
    if not p:
        return _fail("verify_enforced", "polaris_web/pqc_signing.py is missing")
    if "def verify_token_signature" not in p or "def trust_anchor_public_key_hex" not in p:
        return _fail("verify_enforced",
                     "pqc_signing.py must expose verify_token_signature + "
                     "trust_anchor_public_key_hex (the use-path check + the published anchor)")
    # The self-verify lives in signature_with_key_for_token (v9.117); the older
    # signature_bytes_for_token is now a thin wrapper around it.
    m = re.search(r"def signature_with_key_for_token\(.*?\n(?=def [a-z])", p, re.S)
    body = m.group(0) if m else ""
    # The self-verify may be the lone verify() or, since v9.133, the two-witness
    # verify_both() (a strictly stronger self-check); either satisfies enforcement.
    if "verify(" not in body and "verify_both(" not in body:
        return _fail("verify_enforced",
                     "signature_bytes_for_token must self-verify the signature it produces (call "
                     "verify / verify_both) so an unverifiable signature is never persisted")
    ci = _read(root, ".github/workflows/ci.yml")
    if not ci or "verify_token_signature" not in ci:
        return _fail("verify_enforced",
                     "the pqc-real CI job must exercise verify_token_signature (verify-at-use)")
    return _ok("verify_enforced",
               "verification is enforced: issuance self-verifies, verify_token_signature checks "
               "stored signatures against the trust anchor, exercised in CI")


# ---------------------------------------------------------------------------
# The ML-DSA-65 verify path is TWO-WITNESSED (v9.133): every real verdict is
# cross-checked by two INDEPENDENT FIPS 204 implementations — liboqs (primary)
# and cryptography/OpenSSL (the second witness) — which must AGREE, or the
# signature is refused. A lone verifier would silently trust a signature a bug
# or compromise in its one library mis-accepts; the witness closes that, the
# same discipline polaris_zk/witness2 gives the ZK path. The contract: a
# verify_both that both signing AND use-path sites route through, a real second
# witness backed by cryptography's MLDSA65 (a different implementation, not a
# second oqs call), and CI that proves the two agree.
# ---------------------------------------------------------------------------
def check_pqc_second_witness(root: pathlib.Path) -> list[Finding]:
    p = _read(root, "polaris_web/pqc_signing.py")
    if not p:
        return _fail("pqc_second_witness", "polaris_web/pqc_signing.py is missing")
    if "def verify_both" not in p or "def _verify_second_witness" not in p:
        return _fail("pqc_second_witness",
                     "pqc_signing.py must expose verify_both + _verify_second_witness "
                     "(the two-witness ML-DSA-65 verify path)")
    # The witness must be a DIFFERENT implementation, not a second liboqs call.
    if "MLDSA65PublicKey" not in p or "mldsa" not in p:
        return _fail("pqc_second_witness",
                     "the second witness must be cryptography's MLDSA65 (an independent FIPS 204 "
                     "implementation), not a second liboqs verify")
    # A disagreement must be refused (fail closed), not silently averaged away.
    if "DISAGREEMENT" not in p:
        return _fail("pqc_second_witness",
                     "verify_both must refuse (and log) when the two witnesses disagree")
    # Every real verify site must route through verify_both, not the lone verify().
    # The three sites: issuance self-verify, verify_stored_signature, verify_token_signature.
    for fn in ("signature_with_key_for_token", "verify_stored_signature", "verify_token_signature"):
        # Match the function body up to the next top-level def OR end of file (so a
        # site that happens to be the last function is not wrongly read as empty).
        m = re.search(r"def %s\(.*?(?=\ndef [a-z]|\Z)" % re.escape(fn), p, re.S)
        body = m.group(0) if m else ""
        if "verify_both(" not in body:
            return _fail("pqc_second_witness",
                         "%s must route its real-PQC verify through verify_both (two witnesses), "
                         "not the lone verify()" % fn)
    ci = _read(root, ".github/workflows/ci.yml")
    if not ci or "SecondWitnessTests" not in ci:
        return _fail("pqc_second_witness",
                     "the pqc-real CI job must run the SecondWitnessTests (prove the two "
                     "independent implementations agree on a real ML-DSA-65 signature)")
    return _ok("pqc_second_witness",
               "ML-DSA-65 verify is two-witnessed: liboqs + cryptography/OpenSSL must agree "
               "(verify_both), a disagreement is refused, proven by the pqc-real CI job")


# ---------------------------------------------------------------------------
# The PQC posture audit must stay HONEST. Polaris's thesis is "post-quantum",
# but only its token core is; its transport (TLS key exchange) and operator auth
# (WebAuthn) are still classical. docs/reference/PQC-POSTURE.md states that split
# plainly. This check pins the honesty discipline: the doc must keep BOTH halves
# (what is post-quantum AND what is still classical), must name the classical
# surfaces by name (so the gap cannot be quietly deleted into an overclaim), must
# map to the NIST timeline, and must not assert production-readiness. It is the
# anti-larping guard for the headline claim, the same role check_thesis_* plays.
# ---------------------------------------------------------------------------
def check_pqc_posture(root: pathlib.Path) -> list[Finding]:
    doc = _read(root, "docs/reference/PQC-POSTURE.md")
    if not doc:
        return _fail("pqc_posture",
                     "docs/reference/PQC-POSTURE.md is missing (the honest post-quantum audit)")
    low = doc.lower()
    # Both halves of the honest split must be present.
    if "what is post-quantum today" not in low or "what is still classical" not in low:
        return _fail("pqc_posture",
                     "PQC-POSTURE.md must keep BOTH an honest 'what is post-quantum today' AND a "
                     "'what is still classical' section (the audit cannot become a one-sided claim)")
    # The PQ core must be named.
    if "ML-DSA-65" not in doc:
        return _fail("pqc_posture",
                     "PQC-POSTURE.md must name the post-quantum core (ML-DSA-65 token signature)")
    # The classical surfaces must be named AND called classical, so the gap is not
    # silently softened. TLS key exchange and WebAuthn are the load-bearing ones.
    classical_block = low.split("what is still classical", 1)[1]
    for surface in ("tls", "webauthn"):
        if surface not in classical_block:
            return _fail("pqc_posture",
                         "PQC-POSTURE.md must name %s among the still-classical surfaces "
                         "(honesty: the transport/auth gap stays stated)" % surface.upper())
    if "classical" not in classical_block:
        return _fail("pqc_posture",
                     "the still-classical section must actually call its surfaces 'classical' "
                     "(no euphemism for the quantum-vulnerable primitives)")
    # The NIST migration clock must be cited (the audit is timeline-relative).
    if "2030" not in doc or "2035" not in doc or "FIPS 204" not in doc:
        return _fail("pqc_posture",
                     "PQC-POSTURE.md must map to the NIST timeline (FIPS 204 + the 2030 deprecate / "
                     "2035 disallow clock from IR 8547)")
    # It must not overclaim production-readiness (the standing honesty line).
    if "production-readiness" not in low and "production readiness" not in low:
        return _fail("pqc_posture",
                     "PQC-POSTURE.md must disclaim production-readiness (link the gap ledger), not "
                     "imply the system is deployable")
    return _ok("pqc_posture",
               "PQC posture audit is honest: the PQ token core and the still-classical "
               "transport/WebAuthn are both stated, mapped to the NIST 2030/2035 clock")


# ---------------------------------------------------------------------------
# A post-quantum CLAIM must not drift ahead of its PROOF. The posture audit
# (v9.136) states the client-to-edge TLS hop negotiates the hybrid PQ group
# X25519MLKEM768. That positive security claim is only honest while CI actually
# reads it off a real handshake: this check fails if the doc names the hybrid
# group but the caddy-edge CI job does not prove the negotiation. (The empirical
# v9.136 review flagged exactly this drift risk: an unproven "proven in CI".)
# ---------------------------------------------------------------------------
def check_edge_pq_kex(root: pathlib.Path) -> list[Finding]:
    doc = _read(root, "docs/reference/PQC-POSTURE.md")
    if not doc:
        return _fail("edge_pq_kex", "docs/reference/PQC-POSTURE.md is missing")
    GROUP = "X25519MLKEM768"
    if GROUP not in doc:
        # The doc makes no edge-PQ-KEX claim; nothing to pin.
        return _ok("edge_pq_kex",
                   "the posture audit makes no edge hybrid-KEX claim; nothing to pin")
    ci = _read(root, ".github/workflows/ci.yml")
    if not ci or GROUP not in ci:
        return _fail("edge_pq_kex",
                     "PQC-POSTURE.md claims the edge negotiates %s, but CI does not prove it; "
                     "the caddy-edge job must read the negotiated group off a real handshake" % GROUP)
    # The CI must ASSERT the negotiation, not merely mention the group name. Require
    # both the negotiated-group read and a hard failure when it is absent.
    if "Negotiated TLS1.3 group" not in ci:
        return _fail("edge_pq_kex",
                     "the caddy-edge job must read 'Negotiated TLS1.3 group' off a real TLS 1.3 "
                     "handshake (not merely name the group) to prove the edge PQ-KEX claim")
    if not re.search(r"grep -q '%s'" % re.escape(GROUP), ci):
        return _fail("edge_pq_kex",
                     "the caddy-edge job must GATE on the negotiated group being %s "
                     "(a grep -q assertion), so the claim cannot pass without the proof" % GROUP)
    return _ok("edge_pq_kex",
               "the edge hybrid-KEX claim (%s) is backed by the caddy-edge CI job, which asserts "
               "the negotiated group off a real handshake" % GROUP)


# ---------------------------------------------------------------------------
# The issuer public key is stored WITH each signature (TokenSignature.
# signing_public_key_hex) so verification at use is self-contained — no live
# key-file lookup, and it survives key rotation. This pins the whole wiring:
# the column (schema), the stored-proc parameter, issuance threading the key,
# and the token-detail page verifying each stored signature.
# ---------------------------------------------------------------------------
def check_signature_self_contained_verify(root: pathlib.Path) -> list[Finding]:
    p = _read(root, "polaris_web/pqc_signing.py")
    if not p or "def verify_stored_signature" not in p or "def signature_with_key_for_token" not in p:
        return _fail("self_contained_verify",
                     "pqc_signing.py must expose signature_with_key_for_token + "
                     "verify_stored_signature (the self-contained store + verify path)")
    schema = _read(root, "polaris_sql/01_schema.sql")
    if "signing_public_key_hex" not in schema:
        return _fail("self_contained_verify",
                     "TokenSignature must have signing_public_key_hex in 01_schema.sql (the "
                     "stored issuer public key / DB trust anchor)")
    proc = _read(root, "polaris_sql/05_procedures.sql")
    if "p_signing_public_key_hex" not in proc:
        return _fail("self_contained_verify",
                     "uc1_issue_and_activate must accept p_signing_public_key_hex and store it")
    app = _read(root, "polaris_web/app.py")
    if "verify_stored_signature" not in app:
        return _fail("self_contained_verify",
                     "the token-detail route must verify each stored signature "
                     "(pqc_signing.verify_stored_signature) so verification is surfaced at use")
    return _ok("self_contained_verify",
               "the issuer public key is stored with each signature and verification is surfaced "
               "at use (token detail) — self-contained, survives key rotation")


# ---------------------------------------------------------------------------
# Real PQC must be the PRODUCTION DEFAULT, not merely testable. That needs three
# things together: liboqs in the prod image (so oqs imports at runtime), the
# flag on in the prod compose (POLARIS_USE_REAL_PQC=1), and the signing-key
# secret mounted (the stable trust anchor verify-at-use checks against). CI
# verifies real ML-DSA-65 actually works inside the prod image. The real key
# CUSTODY (HSM/KMS) stays operator-gated; the compose ships a generated key.
# ---------------------------------------------------------------------------
def check_prod_real_pqc(root: pathlib.Path) -> list[Finding]:
    df = _read(root, "polaris_web/Dockerfile.prod")
    compose = _read(root, "polaris_web/docker-compose.prod.yml")
    if not df or not compose:
        return _fail("prod_real_pqc", "Dockerfile.prod / docker-compose.prod.yml missing")
    if "liboqs-python" not in df:
        return _fail("prod_real_pqc",
                     "Dockerfile.prod must install liboqs-python so real ML-DSA-65 signing is "
                     "available in the prod image (not just testable in a CI job)")
    if not re.search(r"POLARIS_USE_REAL_PQC:\s*['\"]?1", compose):
        return _fail("prod_real_pqc",
                     "the prod compose must set POLARIS_USE_REAL_PQC=1 so issuance uses real PQC, "
                     "not the SHA3-256 placeholder")
    if "POLARIS_PQC_SIGNING_KEY_FILE" not in compose or "polaris_signing_key" not in compose:
        return _fail("prod_real_pqc",
                     "the prod compose must mount the signing keypair secret (polaris_signing_key) "
                     "and point POLARIS_PQC_SIGNING_KEY_FILE at it (the stable trust anchor)")
    ci = _read(root, ".github/workflows/ci.yml")
    if not ci or "real ML-DSA-65 signing inside the prod image" not in ci:
        return _fail("prod_real_pqc",
                     "CI must verify real ML-DSA-65 signing works INSIDE the built prod image "
                     "(a broken liboqs copy would otherwise only surface at deploy)")
    return _ok("prod_real_pqc",
               "real ML-DSA-65 is the production default: liboqs in the prod image, the flag on, "
               "the signing-key secret mounted as the trust anchor, verified in CI")


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
# Container IMAGE CVE scanning (v9.138). pip-audit covers Python deps; bandit
# covers our code; but the OS packages in the base images were unscanned and
# shipped real fixable CRITICALs. This pins the control: the self-built
# Dockerfiles must patch their bases (apt-get upgrade / apk upgrade), CI must run
# Trivy gating on fixable CRITICAL, and a documented .trivyignore carries the
# justified exceptions. Without all three, image CVEs ship silently.
# ---------------------------------------------------------------------------
def check_image_cve_scanning(root: pathlib.Path) -> list[Finding]:
    ci = _read(root, ".github/workflows/ci.yml")
    if not ci:
        return _fail("image_cve_scan", ".github/workflows/ci.yml is missing")
    if "trivy" not in ci.lower():
        return _fail("image_cve_scan",
                     "CI must scan the built container images for OS-package CVEs (Trivy); "
                     "pip-audit only covers Python dependencies")
    # The scan must GATE on fixable CRITICAL (an --exit-code 1 + --severity CRITICAL
    # run), not merely report. Require both tokens near the trivy usage.
    if "--severity CRITICAL" not in ci or "--exit-code 1" not in ci:
        return _fail("image_cve_scan",
                     "the Trivy image scan must GATE on fixable CRITICAL "
                     "(--severity CRITICAL --exit-code 1), not only report")
    if "--ignore-unfixed" not in ci:
        return _fail("image_cve_scan",
                     "the Trivy gate should use --ignore-unfixed so it fails only on ACTIONABLE "
                     "(fixable) CVEs, not on base-image CVEs with no upstream patch yet")
    # The fixable CVEs must be PATCHED in what ships, not just reported: the
    # self-built Dockerfiles upgrade their base packages.
    patched = {
        "polaris_web/Dockerfile.prod": "apt-get -y upgrade",
        "polaris_web/Dockerfile.caddy": "apk upgrade",
        "polaris_web/Dockerfile.pgbouncer": "apk upgrade",
        "polaris_web/Dockerfile.postgres": "apk upgrade",
    }
    for path, token in patched.items():
        df = _read(root, path)
        if not df or token not in df:
            return _fail("image_cve_scan",
                         "%s must `%s` so fixable base-image CVEs are patched in the shipped image, "
                         "not merely scanned" % (path, token))
    # Exceptions must be documented, not silently widened.
    if not (root / ".trivyignore").is_file():
        return _fail("image_cve_scan",
                     ".trivyignore is missing — Trivy exceptions must be documented + justified")
    return _ok("image_cve_scan",
               "CI builds + Trivy-scans every prod image gating on fixable CRITICAL; the "
               "Dockerfiles patch their bases; exceptions are documented in .trivyignore")


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
# A persistent-volume UPGRADE does NOT re-run docker-init.sh (postgres init
# scripts only fire on an empty data dir), so the deploy must itself apply
# pending migrations AND re-sync the idempotent DB objects (procedures, triggers,
# views, grants). Without this a changed procedure — e.g. v9.117's
# uc1_issue_and_activate signature — never reaches the upgraded DB and issuance
# breaks. polaris-migrate.sh provides --sync-objects; polaris-deploy.sh runs both
# against the running stack.
# ---------------------------------------------------------------------------
def check_deploy_syncs_db_objects(root: pathlib.Path) -> list[Finding]:
    mig = _read(root, "scripts/polaris-migrate.sh")
    dep = _read(root, "scripts/polaris-deploy.sh")
    if not mig or not dep:
        return _fail("deploy_db_sync", "scripts/polaris-migrate.sh or polaris-deploy.sh is missing")
    if "--sync-objects" not in mig or "sync-objects)" not in mig:
        return _fail("deploy_db_sync",
                     "polaris-migrate.sh must provide a --sync-objects mode that re-applies the "
                     "procedure/trigger/view/grant files (else a changed object never reaches an "
                     "upgraded DB)")
    if "--sync-objects" not in dep or "--up --target=docker-stack" not in dep:
        return _fail("deploy_db_sync",
                     "polaris-deploy.sh must apply migrations + --sync-objects against the running "
                     "stack on deploy — an upgrade does not re-run docker-init, so a changed "
                     "procedure would otherwise never reach the live DB")
    return _ok("deploy_db_sync",
               "the deploy applies migrations and re-syncs DB objects on upgrade (procedure / "
               "trigger / view / grant changes reach an upgraded DB, not just a fresh one)")


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
# Prometheus metrics must aggregate ACROSS gunicorn workers. With a per-worker
# registry a /metrics scrape reports only the worker that served it — a 4x
# undercount under 4 workers. Multiprocess mode (PROMETHEUS_MULTIPROC_DIR) file-
# backs each worker's samples and the scrape aggregates them via a
# MultiProcessCollector; gunicorn must reap a dead worker's files (child_exit +
# mark_process_dead) and the prod compose must set the dir.
# ---------------------------------------------------------------------------
def check_prometheus_multiprocess(root: pathlib.Path) -> list[Finding]:
    app = _read(root, "polaris_web/app.py")
    gconf = _read(root, "polaris_web/gunicorn.conf.py")
    compose = _read(root, "polaris_web/docker-compose.prod.yml")
    if not app or not gconf or not compose:
        return _fail("prom_multiproc",
                     "app.py / gunicorn.conf.py / docker-compose.prod.yml is missing")
    if "MultiProcessCollector" not in app or "PROMETHEUS_MULTIPROC_DIR" not in app:
        return _fail("prom_multiproc",
                     "app.py must aggregate /metrics via a MultiProcessCollector when "
                     "PROMETHEUS_MULTIPROC_DIR is set (else metrics undercount across workers)")
    if "mark_process_dead" not in gconf or "def child_exit" not in gconf:
        return _fail("prom_multiproc",
                     "gunicorn.conf.py must reap a dead worker's metric files (a child_exit hook "
                     "calling mark_process_dead)")
    if "PROMETHEUS_MULTIPROC_DIR" not in compose:
        return _fail("prom_multiproc",
                     "docker-compose.prod.yml must set PROMETHEUS_MULTIPROC_DIR so the multi-worker "
                     "app aggregates metrics")
    return _ok("prom_multiproc",
               "Prometheus /metrics aggregates across workers (multiprocess dir + "
               "MultiProcessCollector + child_exit reaping)")


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
# Container runtime hardening (v9.141, CIS Docker 5.x). Every prod-compose
# service must drop ALL Linux capabilities (adding back only the few its
# entrypoint genuinely needs) and forbid privilege escalation
# (no-new-privileges). The app + pgbouncer then run with ZERO capabilities; the
# public Caddy edge keeps only NET_BIND_SERVICE; postgres/redis keep only the
# caps their root-then-drop init needs. Proven to still boot + serve by the
# prod-stack-boot CI job (cap_drop ALL would otherwise silently break an
# entrypoint). A service that ships without these is the un-hardened default.
# ---------------------------------------------------------------------------
def check_container_hardening(root: pathlib.Path) -> list[Finding]:
    text = _read(root, "polaris_web/docker-compose.prod.yml")
    if not text:
        return _fail("container_hardening", "polaris_web/docker-compose.prod.yml is missing")
    services = len(re.findall(r"(?m)^\s+image:\s", text))
    if services == 0:
        return _fail("container_hardening", "could not find any services in the prod compose")
    nnp = len(re.findall(r"no-new-privileges:\s*true", text))
    cap_drop_all = len(re.findall(r"(?m)cap_drop:\s*\n\s+-\s*ALL\b", text))
    if nnp < services:
        return _fail("container_hardening",
                     f"only {nnp}/{services} prod-compose services set "
                     "security_opt no-new-privileges:true — a service can still escalate privileges")
    if cap_drop_all < services:
        return _fail("container_hardening",
                     f"only {cap_drop_all}/{services} prod-compose services cap_drop ALL — a "
                     "service runs with the full default Linux capability set")
    # The boot test must prove the hardened stack still serves (cap_drop can break
    # an entrypoint that needs a capability — e.g. gosu/setpriv's SETUID).
    ci = _read(root, ".github/workflows/ci.yml")
    if not ci or "prod-stack-boot" not in ci:
        return _fail("container_hardening",
                     "the prod-stack-boot CI job must boot the HARDENED stack so cap_drop cannot "
                     "silently break a service's entrypoint")
    return _ok("container_hardening",
               f"all {services} prod-compose services drop ALL caps (adding back only what their "
               "entrypoint needs) + forbid privilege escalation; proven to still serve by CI")


# ---------------------------------------------------------------------------
# Third-party images in the PROD compose must be pinned by digest (@sha256), not
# just a mutable tag. A tag can be repointed at different content upstream (or, as
# bitnami/pgbouncer showed, deleted); a digest is immutable, so the deploy runs
# exactly what was reviewed. Locally-built images (polaris-*) are exempt — they
# have no registry digest. Dependabot's docker ecosystem bumps the pins.
# ---------------------------------------------------------------------------
def check_prod_images_digest_pinned(root: pathlib.Path) -> list[Finding]:
    compose = _read(root, "polaris_web/docker-compose.prod.yml")
    if not compose:
        return _fail("image_digests", "polaris_web/docker-compose.prod.yml is missing")
    unpinned = []
    for m in re.finditer(r"(?m)^\s*image:\s*(\S+)", compose):
        img = m.group(1).strip().strip('"').strip("'")
        if img.startswith("polaris-"):
            continue  # built locally via `build:`, no registry digest to pin
        if "@sha256:" not in img:
            unpinned.append(img)
    if unpinned:
        return _fail("image_digests",
                     "prod-compose third-party image(s) are tag-pinned, not digest-pinned: "
                     + ", ".join(unpinned) + " — pin as name:tag@sha256:<digest> so a mutated or "
                     "deleted upstream tag cannot change what runs")
    dep = root / ".github" / "dependabot.yml"
    if not dep.is_file() or "docker" not in dep.read_text():
        return _fail("image_digests",
                     "add the docker ecosystem to .github/dependabot.yml so the pinned digests get "
                     "security bumps (a frozen digest never updates on its own)")
    return _ok("image_digests",
               "all third-party prod-compose images are digest-pinned (@sha256); Dependabot's "
               "docker ecosystem keeps the pins current")


# ---------------------------------------------------------------------------
# Alerting rules must be a real, shipped, validated artifact the operator can
# deploy — not a doc snippet. DR.md referenced "PolarisHigh5xx and related"
# rules that lived only as an OPERATIONS.md example. They now ship at
# deploy/observability/ (promtool-validated) with a scrape config; the alerting
# backend (Alertmanager + pager) remains operator-provided.
# ---------------------------------------------------------------------------
def check_alert_rules(root: pathlib.Path) -> list[Finding]:
    rules = _read(root, "deploy/observability/polaris-alerts.yml")
    cfg = _read(root, "deploy/observability/prometheus.yml")
    if not rules or not cfg:
        return _fail("alert_rules",
                     "deploy/observability/polaris-alerts.yml + prometheus.yml must ship (a real "
                     "rules artifact, not just a doc example)")
    if "groups:" not in rules:
        return _fail("alert_rules", "polaris-alerts.yml must be a Prometheus rule-group file (groups:)")
    for a in ("PolarisHigh5xx", "PolarisAppDown"):
        if f"alert: {a}" not in rules:
            return _fail("alert_rules", f"polaris-alerts.yml must define the {a} alert")
    if "polaris-alerts.yml" not in cfg or "job_name: polaris" not in cfg:
        return _fail("alert_rules",
                     "prometheus.yml must scrape the polaris job and load polaris-alerts.yml "
                     "(rule_files)")
    return _ok("alert_rules",
               "shipped Prometheus scrape config + promtool-validated alerting rules "
               "(deploy/observability/); the Alertmanager backend stays operator-provided")


# ---------------------------------------------------------------------------
# Every shipped alert must have a runbook, and every runbook must name a real
# alert. An alert that pages on-call with no documented Trigger/Diagnosis/
# Remediation is a 03:00 dead end; a runbook section for an alert that no longer
# exists is stale guidance. This parses the alert names out of polaris-alerts.yml
# and asserts a one-to-one mapping with the `## <AlertName>` headings in
# docs/operator/RUNBOOKS.md (no missing runbook, no orphan section).
# ---------------------------------------------------------------------------
def check_alert_runbooks(root: pathlib.Path) -> list[Finding]:
    rules = _read(root, "deploy/observability/polaris-alerts.yml")
    book = _read(root, "docs/operator/RUNBOOKS.md")
    if not rules:
        return _fail("alert_runbooks",
                     "deploy/observability/polaris-alerts.yml is missing — no alerts to document")
    if not book:
        return _fail("alert_runbooks",
                     "docs/operator/RUNBOOKS.md is missing — every shipped alert needs a runbook")
    alerts = re.findall(r"(?m)^\s*-\s*alert:\s*(\w+)\s*$", rules)
    if not alerts:
        return _fail("alert_runbooks", "could not parse any `- alert: <Name>` lines from polaris-alerts.yml")
    # Runbook sections are H2 headings naming exactly one alert.
    sections = re.findall(r"(?m)^##\s+(\w+)\s*$", book)
    documented = {s for s in sections if s.startswith("Polaris")}
    alert_set = set(alerts)
    missing = sorted(alert_set - documented)
    if missing:
        return _fail("alert_runbooks",
                     "alert(s) with no `## <name>` runbook section in docs/operator/RUNBOOKS.md: "
                     + ", ".join(missing) + " — an alert that pages with no runbook is a dead end")
    orphans = sorted(documented - alert_set)
    if orphans:
        return _fail("alert_runbooks",
                     "RUNBOOKS.md has runbook section(s) for alert(s) not in polaris-alerts.yml: "
                     + ", ".join(orphans) + " — stale guidance; remove or re-add the alert")
    return _ok("alert_runbooks",
               f"all {len(alert_set)} shipped alerts have exactly one runbook section in "
               "docs/operator/RUNBOOKS.md (no missing, no orphan)")


# ---------------------------------------------------------------------------
# The duress signal must be ALERTABLE (v9.128). observability.py calls duress
# "the headline metric": an unread duress event is the coercion-cover failure
# mode. The JSON /api/metrics snapshot is not scrapeable for alerting, so the
# count must be a Prometheus counter on /metrics, incremented where the
# DuressEvent is recorded, with an alert on it — otherwise the page never fires.
# ---------------------------------------------------------------------------
def check_duress_alertable(root: pathlib.Path) -> list[Finding]:
    app = _read(root, "polaris_web/app.py")
    alerts = _read(root, "deploy/observability/polaris-alerts.yml")
    if not (app and alerts):
        return _fail("duress_alert", "app.py or the alerts file is missing")
    if "polaris_duress_events_total" not in app:
        return _fail("duress_alert",
                     "app.py must expose polaris_duress_events_total on /metrics (the duress signal "
                     "must be alertable, not only in the JSON /api/metrics)")
    # It must be incremented where the DuressEvent is recorded, or the alert sits
    # on a counter that never moves.
    m = re.search(r"def _record_duress_async\b.*?(?=\n\ndef |\Z)", app, re.S)
    if not m or "_METRICS_DURESS" not in m.group(0):
        return _fail("duress_alert",
                     "the duress counter must be incremented in _record_duress_async (where the "
                     "DuressEvent is recorded) — an alert on a never-incremented counter never fires")
    if "PolarisDuressEvent" not in alerts or "polaris_duress_events_total" not in alerts:
        return _fail("duress_alert",
                     "polaris-alerts.yml must alert (PolarisDuressEvent) on polaris_duress_events_total")
    return _ok("duress_alert",
               "the duress signal is alertable: polaris_duress_events_total is on /metrics, incremented "
               "at the DuressEvent record site, and PolarisDuressEvent pages on it (runbook enforced by "
               "check_alert_runbooks)")


# ---------------------------------------------------------------------------
# Fail-closed on production misconfiguration (v9.129). The prod compose sets
# these correctly, but a hand-rolled deployment could miss them, so app.py
# refuses to start in production when:
#   - POLARIS_DB_SSLMODE permits a silent plaintext DB hop (prefer/allow/disable);
#   - POLARIS_DURESS_SYNC=1 reintroduces the duress timing side-channel.
# Mirrors the existing default-SECRET_KEY guard. This pins both guards so neither
# can be silently dropped (a removed fail-closed check reads as "still safe").
# ---------------------------------------------------------------------------
def check_prod_fail_closed(root: pathlib.Path) -> list[Finding]:
    app = _read(root, "polaris_web/app.py")
    if not app:
        return _fail("prod_fail_closed", "polaris_web/app.py is missing")
    if "_PRODUCTION" not in app:
        return _fail("prod_fail_closed", "app.py must compute a _PRODUCTION flag")
    # The DB-TLS guard: POLARIS_DB_SSLMODE tied to a sys.exit, rejecting the
    # plaintext-capable modes.
    if not re.search(r"POLARIS_DB_SSLMODE.{0,500}sys\.exit", app, re.S):
        return _fail("prod_fail_closed",
                     "app.py must refuse to start in production when POLARIS_DB_SSLMODE permits a "
                     "silent plaintext DB hop (a sys.exit guard on prefer/allow/disable)")
    if not re.search(r"prefer", app):
        return _fail("prod_fail_closed",
                     "the sslmode guard must reject the plaintext-capable modes (prefer/allow/disable)")
    # v9.132 — verify-ca/verify-full must require a pinned CA (sslrootcert) at
    # startup, or a hand-rolled deploy boots and fails confusingly at first
    # connect. The guard must tie POLARIS_DB_SSLROOTCERT to a sys.exit.
    if not re.search(r"POLARIS_DB_SSLROOTCERT.{0,500}sys\.exit", app, re.S):
        return _fail("prod_fail_closed",
                     "app.py must refuse to start in production when sslmode is verify-ca/verify-full "
                     "but POLARIS_DB_SSLROOTCERT is unset/missing (verify-* without a pinned CA cannot "
                     "verify the peer)")
    # The duress-sync guard: POLARIS_DURESS_SYNC tied to a sys.exit.
    if not re.search(r"POLARIS_DURESS_SYNC.{0,500}sys\.exit", app, re.S):
        return _fail("prod_fail_closed",
                     "app.py must refuse to start in production when POLARIS_DURESS_SYNC=1 (it "
                     "reintroduces the duress timing side-channel)")
    return _ok("prod_fail_closed",
               "app.py fails closed in production on a plaintext-capable POLARIS_DB_SSLMODE and on "
               "POLARIS_DURESS_SYNC=1 (the duress timing side-channel), alongside the default-SECRET_KEY "
               "guard")


# ---------------------------------------------------------------------------
# At-rest data-protection posture. Polaris does not encrypt the live database at
# the app layer (host volume encryption + key custody is operator-gated). The
# risk is not that gap (it is documented and deliberate) but that the POSTURE doc
# silently drifts from the schema reality, or quietly starts overclaiming. This
# pins both: the doc must name the actual sensitive surfaces the schema holds in
# plaintext (Individual.legal_name / date_of_birth, TokenStateEpochLeaf.proof_path
# — the schema's own "v1 stores proof_path in plaintext" note), must point at the
# host-level operator path, and must NOT claim the live DB is encrypted at rest.
# ---------------------------------------------------------------------------
def check_encryption_at_rest_posture(root: pathlib.Path) -> list[Finding]:
    doc = _read(root, "docs/operator/ENCRYPTION-AT-REST.md")
    schema = _read(root, "polaris_sql/01_schema.sql")
    if not doc:
        return _fail("at_rest_posture",
                     "docs/operator/ENCRYPTION-AT-REST.md is missing — the at-rest posture must be "
                     "documented, not implicit")
    # Normalize markdown emphasis out so a bolded "does **not** encrypt" still
    # matches the honesty substring below.
    low = doc.lower().replace("*", "")
    # The plaintext-sensitive surfaces the doc must enumerate, so it cannot drift
    # from the schema. proof_path is load-bearing: the schema itself flags it.
    for needed, why in (
        ("proof_path", "the plaintext ZK Merkle path the schema flags as v1-plaintext"),
        ("legal_name", "the direct PII column on Individual"),
        ("date_of_birth", "the direct PII column on Individual"),
    ):
        if needed not in doc:
            return _fail("at_rest_posture",
                         f"ENCRYPTION-AT-REST.md must name {needed} ({why}) — it is plaintext at rest")
    # Schema-drift guard: while the schema still stores proof_path in plaintext,
    # the doc must say so (not quietly claim it is encrypted).
    if "proof_path" in schema and re.search(r"plaintext", schema, re.I):
        if "plaintext" not in low:
            return _fail("at_rest_posture",
                         "the schema still stores proof_path in plaintext but ENCRYPTION-AT-REST.md "
                         "does not say 'plaintext' — the posture has drifted from the schema")
    # The operator path must be named (host volume encryption), not hand-waved.
    if not re.search(r"luks|dm-crypt|fscrypt", low):
        return _fail("at_rest_posture",
                     "ENCRYPTION-AT-REST.md must name the host-level encryption path (LUKS/dm-crypt/"
                     "fscrypt) — the operator-gated control that actually closes the gap")
    if "operator-gated" not in low:
        return _fail("at_rest_posture",
                     "ENCRYPTION-AT-REST.md must mark the live-DB at-rest control operator-gated")
    # Honesty guard: the doc must NOT claim the live database is encrypted at rest.
    # Any sentence asserting at-rest encryption of the live DB must be negated
    # ('does not', 'not') — we require the explicit honest disclaimer to be present.
    if not re.search(r"does not encrypt|not encrypt the live", low):
        return _fail("at_rest_posture",
                     "ENCRYPTION-AT-REST.md must state plainly that Polaris does NOT encrypt the live "
                     "database at rest (honesty discipline — no overclaiming)")
    return _ok("at_rest_posture",
               "the at-rest posture is documented and honest: names the plaintext-sensitive surfaces "
               "(legal_name/date_of_birth/proof_path), points at the operator-gated host volume "
               "encryption, and does not claim the live DB is encrypted at rest")


# ---------------------------------------------------------------------------
# Right-to-erasure mechanism (v9.125). Polaris cannot delete a holder (C1), so
# erasure = pseudonymize Individual.legal_name and record the act in the
# append-only IndividualErasureEvent. Two things must hold for this to respect
# the audit: (1) the procedure must NOT issue a DELETE (it must not become a
# covert deletion path around C1), and (2) the erasure log must be append-only
# (its REVOKE is checked by check_aor_privilege_boundary; here we assert the
# table + procedure + trigger exist and the PRIVACY doc points at the real
# mechanism rather than describing a capability that does not ship).
# ---------------------------------------------------------------------------
def check_erasure_procedure(root: pathlib.Path) -> list[Finding]:
    schema = _read(root, "polaris_sql/01_schema.sql")
    proc = _read(root, "polaris_sql/05_procedures.sql")
    triggers = _read(root, "polaris_sql/06_triggers.sql")
    privacy = _read(root, "docs/operator/PRIVACY.md")
    if not (schema and proc and triggers):
        return _fail("erasure", "a SQL file for the erasure mechanism is missing")
    if "IndividualErasureEvent" not in schema:
        return _fail("erasure",
                     "01_schema.sql must declare IndividualErasureEvent (the append-only erasure log)")
    m = re.search(r"CREATE\s+OR\s+REPLACE\s+PROCEDURE\s+uc_pseudonymize_individual\b.*?END\$\$;",
                  proc, re.I | re.S)
    if not m:
        return _fail("erasure", "05_procedures.sql must define uc_pseudonymize_individual")
    body = m.group(0)
    # The whole point: it pseudonymizes the NAME and must NOT delete anything.
    if not (re.search(r"UPDATE\s+Individual", body, re.I) and "legal_name" in body):
        return _fail("erasure",
                     "uc_pseudonymize_individual must UPDATE Individual.legal_name (pseudonymize)")
    if "INSERT INTO IndividualErasureEvent" not in body:
        return _fail("erasure",
                     "uc_pseudonymize_individual must record the act in IndividualErasureEvent")
    if re.search(r"\bDELETE\b", body, re.I):
        return _fail("erasure",
                     "uc_pseudonymize_individual must issue NO DELETE — it must not be a covert "
                     "deletion path around C1 (erasure pseudonymizes, it does not delete)")
    if "must be admin" not in body:
        return _fail("erasure", "uc_pseudonymize_individual must be admin-gated (actor role check)")
    if "trg_erasure_append_only" not in triggers:
        return _fail("erasure",
                     "06_triggers.sql must attach the append-only trigger to IndividualErasureEvent")
    # The PRIVACY doc must point at the real procedure, not just describe a policy.
    if "uc_pseudonymize_individual" not in privacy:
        return _fail("erasure",
                     "PRIVACY.md must reference uc_pseudonymize_individual (the doc must point at the "
                     "real mechanism, not describe a capability that does not ship)")
    return _ok("erasure",
               "right-to-erasure ships: uc_pseudonymize_individual pseudonymizes legal_name (admin-"
               "gated, no DELETE) and records it in the append-only IndividualErasureEvent; PRIVACY.md "
               "points at it")


# ---------------------------------------------------------------------------
# Streaming-replication readiness (v9.126). The HA gated item's scaffolding: the
# primary is made replication-ready (wal_level + a REPLICATION role + pg_hba),
# the bootstrap + promotion are documented, and a CI round-trip proves the config
# produces a working hot standby. Only the standby HOST is operator-gated. This
# pins the wiring so it cannot silently rot, and that the doc stays honest about
# what is operator-supplied (no overclaiming a running standby).
# ---------------------------------------------------------------------------
def check_replication_scaffolding(root: pathlib.Path) -> list[Finding]:
    init = _read(root, "polaris_web/docker-init.sh")
    compose = _read(root, "polaris_web/docker-compose.prod.yml")
    secrets = _read(root, "scripts/polaris-generate-secrets.sh")
    doc = _read(root, "docs/operator/FAILOVER.md")
    ci = _read(root, ".github/workflows/ci.yml")
    if not (init and compose and secrets and doc and ci):
        return _fail("replication", "a replication-scaffolding file is missing")
    # The primary must be made replication-ready at init.
    if not re.search(r"ALTER SYSTEM SET wal_level\s*=\s*replica", init):
        return _fail("replication",
                     "docker-init.sh must set wal_level=replica (ALTER SYSTEM) for replication readiness")
    if not re.search(r"CREATE ROLE polaris_replicator.*REPLICATION", init):
        return _fail("replication",
                     "docker-init.sh must create the least-privilege polaris_replicator REPLICATION role")
    if "host replication polaris_replicator" not in init:
        return _fail("replication",
                     "docker-init.sh must add a pg_hba entry for the replication role")
    # The secret is generated and mounted (file-mounted convention, G28).
    if "polaris_replicator_password" not in secrets:
        return _fail("replication",
                     "polaris-generate-secrets.sh must mint polaris_replicator_password")
    if "POLARIS_REPLICATOR_PASSWORD_FILE" not in compose or "polaris_replicator_password" not in compose:
        return _fail("replication",
                     "the prod compose must mount the polaris_replicator_password secret + "
                     "POLARIS_REPLICATOR_PASSWORD_FILE")
    # The runbook documents the bootstrap + promotion and stays honest.
    if "pg_basebackup" not in doc or "pg_promote" not in doc:
        return _fail("replication",
                     "FAILOVER.md must document the pg_basebackup standby bootstrap and pg_promote")
    if "operator-gated" not in doc.lower() or "operator-supplied" not in doc.lower():
        return _fail("replication",
                     "FAILOVER.md must state the standby host is operator-supplied (no overclaiming a "
                     "running standby)")
    # A CI round-trip proves the config produces a working hot standby.
    if "pg_basebackup" not in ci or "pg_stat_replication" not in ci:
        return _fail("replication",
                     "ci.yml must run a primary->standby replication round-trip (pg_basebackup + "
                     "pg_stat_replication assertion)")
    return _ok("replication",
               "replication readiness ships: primary is wal_level=replica with a least-privilege "
               "REPLICATION role + pg_hba; the bootstrap/promotion are documented (FAILOVER.md) and a "
               "CI round-trip proves a working hot standby; the standby host stays operator-supplied")


# ---------------------------------------------------------------------------
# Continuous WAL archiving (pgBackRest, v9.126+). DR.md's ≤1-min-RPO path. The
# scaffolding: a pgbackrest-enabled postgres image, a stanza config, the
# docker-init archive wiring (opt-in), the restore runbook, and a CI round-trip
# that archives + backs up + RESTORES with WAL replay. The offsite S3 repo is
# operator-supplied. This pins the wiring + that the config stays honest that the
# default filesystem repo is not offsite.
# ---------------------------------------------------------------------------
def check_pgbackrest_scaffolding(root: pathlib.Path) -> list[Finding]:
    dockerfile = _read(root, "polaris_web/Dockerfile.postgres")
    conf = _read(root, "polaris_web/pgbackrest.conf")
    compose = _read(root, "polaris_web/docker-compose.prod.yml")
    init = _read(root, "polaris_web/docker-init.sh")
    dr = _read(root, "docs/operator/DR.md")
    ci = _read(root, ".github/workflows/ci.yml")
    if not (dockerfile and conf and compose and init and dr and ci):
        return _fail("pgbackrest", "a pgBackRest-scaffolding file is missing")
    # pgbackrest must be IN the postgres image (archive_command runs there), and
    # the base must stay digest-pinned.
    if "pgbackrest" not in dockerfile:
        return _fail("pgbackrest",
                     "Dockerfile.postgres must install pgbackrest (archive_command runs in the DB image)")
    if "@sha256:" not in dockerfile:
        return _fail("pgbackrest",
                     "Dockerfile.postgres FROM must be digest-pinned (a mutated base must not change "
                     "what runs)")
    # The stanza config ships and stays honest about the local-vs-offsite repo.
    if "[polaris]" not in conf or "pg1-path" not in conf:
        return _fail("pgbackrest", "pgbackrest.conf must define the [polaris] stanza + pg1-path")
    if "s3" not in conf.lower():
        return _fail("pgbackrest",
                     "pgbackrest.conf must document the offsite S3 repo swap (the local repo is not "
                     "offsite) — no overclaiming durability")
    # The compose builds the image + mounts the conf + the opt-in flag.
    if "Dockerfile.postgres" not in compose or "pgbackrest.conf" not in compose:
        return _fail("pgbackrest",
                     "the prod compose must build Dockerfile.postgres and mount pgbackrest.conf")
    if "POLARIS_PGBACKREST_ENABLED" not in compose or "POLARIS_PGBACKREST_ENABLED" not in init:
        return _fail("pgbackrest",
                     "archiving must be opt-in via POLARIS_PGBACKREST_ENABLED (wired in compose + "
                     "docker-init) so a no-repo deployment does not accumulate WAL")
    if "archive_mode" not in init or "archive-push" not in init:
        return _fail("pgbackrest",
                     "docker-init.sh must set archive_mode + the pgbackrest archive_command when enabled")
    # The runbook documents stanza-create; the CI round-trip restores.
    if "stanza-create" not in dr:
        return _fail("pgbackrest", "DR.md must document `pgbackrest --stanza=polaris stanza-create`")
    if "pgbackrest" not in ci or "restore" not in ci:
        return _fail("pgbackrest",
                     "ci.yml must run a pgBackRest archive+backup+RESTORE round-trip")
    # v9.130 operational hardening: the deploy auto-bootstraps the stanza when
    # archiving is enabled (so an operator who enables it but forgets
    # stanza-create does not silently accumulate WAL until the disk fills).
    deploy = _read(root, "scripts/polaris-deploy.sh")
    if "stanza-create" not in deploy or "POLARIS_PGBACKREST_ENABLED" not in deploy:
        return _fail("pgbackrest",
                     "polaris-deploy.sh must run stanza-create when POLARIS_PGBACKREST_ENABLED=1 (so "
                     "archiving enabled-but-unbootstrapped does not fill the disk with WAL)")
    # docker-init warns loudly if archiving runs against a LOCAL (non-offsite) repo.
    if not re.search(r"repo1-type.{0,40}s3", init) or "WARNING" not in init:
        return _fail("pgbackrest",
                     "docker-init.sh must WARN when archiving is enabled with a local (non-s3) repo "
                     "(a local repo does not survive host loss)")
    # The S3 credentials must be guided to a file-mounted secret, NOT compose env.
    if "conf.d" not in conf and "conf.d" not in dr:
        return _fail("pgbackrest",
                     "the S3-credential guidance must use a file-mounted config (conf.d), not compose "
                     "env literals which leak via docker inspect")
    return _ok("pgbackrest",
               "continuous WAL archiving ships: pgbackrest in the DB image (digest-pinned base) + the "
               "[polaris] stanza, opt-in archive_mode/archive_command, a documented stanza-create + "
               "restore, a CI backup+restore round-trip, deploy auto-bootstrap, a local-repo warning, "
               "and file-mounted S3-credential guidance; the offsite S3 repo stays operator-supplied")


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
# The TLS edge must actually START. The prod Caddyfile uses the `rate_limit`
# directive from the third-party caddy-ratelimit plugin, which is NOT in the
# stock caddy image: pinning the stock image (v9.114) made the edge crash-loop
# on "unrecognized directive: rate_limit" and the whole front door never came up
# (v9.135, same class as the bitnami/pgbouncer breakage). The fix is a self-built
# Caddy (Dockerfile.caddy) with the plugin compiled in. This pins it: if the
# Caddyfile uses a third-party directive, the edge must be built (not a stock
# image), the plugin must be compiled in, and CI must validate the Caddyfile
# against the built image so an unbacked directive can never reach production.
# ---------------------------------------------------------------------------
def check_caddy_self_built(root: pathlib.Path) -> list[Finding]:
    caddyfile = _read(root, "polaris_web/Caddyfile")
    compose = _read(root, "polaris_web/docker-compose.prod.yml")
    if not caddyfile or not compose:
        return _fail("caddy_edge", "polaris_web/Caddyfile or docker-compose.prod.yml is missing")
    # The third-party directives the stock image does NOT ship. rate_limit is the
    # live one; extend this set if the Caddyfile adopts more plugin directives.
    THIRD_PARTY = {"rate_limit": "github.com/mholt/caddy-ratelimit"}
    used = {d: mod for d, mod in THIRD_PARTY.items()
            if re.search(r"(?m)^\s*%s\b" % re.escape(d), caddyfile)}
    if not used:
        # No plugin directives: the stock pinned image is fine, nothing to enforce.
        return _ok("caddy_edge",
                   "the Caddyfile uses no third-party directives; the stock edge image suffices")
    # The caddy service must BUILD from Dockerfile.caddy, not pull a stock image
    # that cannot load these directives.
    if not re.search(r"(?m)^\s*dockerfile:\s*Dockerfile\.caddy\b", compose):
        return _fail("caddy_edge",
                     "the Caddyfile uses %s (third-party plugin directives), so the caddy service "
                     "must build from Dockerfile.caddy with the plugins compiled in, not pull a "
                     "stock caddy image that crash-loops on the unrecognized directive"
                     % ", ".join(sorted(used)))
    df = _read(root, "polaris_web/Dockerfile.caddy")
    if not df:
        return _fail("caddy_edge", "polaris_web/Dockerfile.caddy is missing")
    for directive, module in sorted(used.items()):
        if module not in df:
            return _fail("caddy_edge",
                         "the Caddyfile uses `%s` but Dockerfile.caddy does not compile in its "
                         "plugin (%s) via xcaddy --with" % (directive, module))
    ci = _read(root, ".github/workflows/ci.yml")
    if not ci or "Dockerfile.caddy" not in ci or "caddy validate" not in ci:
        return _fail("caddy_edge",
                     "CI must build Dockerfile.caddy and `caddy validate` the real Caddyfile against "
                     "it (the regression guard for the v9.135 crash class)")
    return _ok("caddy_edge",
               "the TLS edge is self-built (Dockerfile.caddy) with every third-party directive (%s) "
               "compiled in, and CI validates the Caddyfile against it" % ", ".join(sorted(used)))


# ---------------------------------------------------------------------------
# The FULL production compose must boot and serve end to end, not just the dev
# compose + per-image tests. CI booting only the dev stack (db+app on :5000) let
# real prod-down bugs ship: a Caddyfile directive the stock image lacked (v9.135)
# and 09_grants.sql hardcoding the test DB name so prod init aborted before TLS
# (v9.140) — the prod stack had never come up. This pins the keystone test: a CI
# job generates secrets, builds the prod images, boots docker-compose.prod.yml +
# the citest override (Caddy internal CA instead of ACME), and asserts the stack
# serves /api/health through the TLS edge with the DB-backed components healthy.
# ---------------------------------------------------------------------------
def check_prod_stack_boot(root: pathlib.Path) -> list[Finding]:
    ci = _read(root, ".github/workflows/ci.yml")
    if not ci:
        return _fail("prod_stack_boot", ".github/workflows/ci.yml is missing")
    # The boot harness (override compose + Caddyfile) must exist.
    if not (root / "polaris_web" / "docker-compose.citest.yml").is_file():
        return _fail("prod_stack_boot",
                     "polaris_web/docker-compose.citest.yml is missing (the prod-stack boot "
                     "override that swaps Caddy's ACME edge for an internal CA in CI)")
    if not (root / "polaris_web" / "Caddyfile.citest").is_file():
        return _fail("prod_stack_boot",
                     "polaris_web/Caddyfile.citest is missing (the CI edge config)")
    # CI must actually boot the FULL prod compose with the override, not the dev one.
    if "docker-compose.prod.yml" not in ci or "docker-compose.citest.yml" not in ci:
        return _fail("prod_stack_boot",
                     "a CI job must boot the FULL prod compose end to end "
                     "(docker compose -f docker-compose.prod.yml -f docker-compose.citest.yml up)")
    # It must generate the secrets the prod stack needs (not run on dev defaults).
    if "polaris-generate-secrets.sh" not in ci:
        return _fail("prod_stack_boot",
                     "the prod-stack boot job must run polaris-generate-secrets.sh so the stack "
                     "boots on real generated secrets + certs, like a deploy")
    # It must assert the stack actually SERVES through the edge (a health probe).
    if "/api/health" not in ci:
        return _fail("prod_stack_boot",
                     "the prod-stack boot job must assert the stack serves /api/health through the "
                     "Caddy TLS edge (a 200 + DB-backed components healthy), not just that it starts")
    return _ok("prod_stack_boot",
               "CI boots the FULL prod compose (generated secrets, real images, TLS edge) and "
               "asserts it serves /api/health end to end")


# ---------------------------------------------------------------------------
# The app<->DB path must be TLS-encrypted, not silently plaintext. psycopg2's
# default sslmode is 'prefer' (encrypt if offered, else cleartext, no warning).
# The prod path encrypts BOTH hops: app -> pgbouncer (pgbouncer client_tls,
# self-signed cert) and pgbouncer -> postgres (server_tls), with postgres TLS
# enabled at init from a host-generated cert. sslmode stays configurable so
# dev/CI (no TLS) keep 'prefer'.
# ---------------------------------------------------------------------------
def check_app_db_tls(root: pathlib.Path) -> list[Finding]:
    app = _read(root, "polaris_web/app.py")
    compose = _read(root, "polaris_web/docker-compose.prod.yml")
    init = _read(root, "polaris_web/docker-init.sh")
    entry = _read(root, "polaris_web/pgbouncer-entrypoint.sh")
    if not (app and compose and init and entry):
        return _fail("app_db_tls", "an app<->DB TLS wiring file is missing")
    if "POLARIS_DB_SSLMODE" not in app or "sslmode" not in app:
        return _fail("app_db_tls",
                     "DB_CONFIG must set a configurable sslmode (POLARIS_DB_SSLMODE) — psycopg2's "
                     "'prefer' default silently falls back to plaintext")
    # v9.131 — the app must support pinning the pgbouncer cert (sslrootcert) so a
    # verify-ca/verify-full deployment can validate the peer, not just encrypt.
    if "sslrootcert" not in app or "POLARIS_DB_SSLROOTCERT" not in app:
        return _fail("app_db_tls",
                     "DB_CONFIG must support pinning the peer cert via POLARIS_DB_SSLROOTCERT "
                     "(sslrootcert) — verify-ca needs the CA/cert, not just encryption")
    # Both hops VERIFY the pinned self-signed certs (not merely encrypt): the app
    # pins pgbouncer (verify-ca + sslrootcert), pgbouncer pins postgres
    # (server_tls verify-ca + ca_file). 'require' (encrypt only) is the v9.121
    # floor; v9.131 raised the prod default to verify-ca.
    if not re.search(r"POLARIS_DB_SSLMODE:\s*verify-ca", compose):
        return _fail("app_db_tls",
                     "the prod compose must set POLARIS_DB_SSLMODE=verify-ca (pin pgbouncer's cert, "
                     "not just encrypt the app<->pgbouncer hop)")
    if "POLARIS_DB_SSLROOTCERT" not in compose:
        return _fail("app_db_tls",
                     "the prod compose must set POLARIS_DB_SSLROOTCERT to pgbouncer's pinned cert")
    if not re.search(r"PGBOUNCER_SERVER_TLS_SSLMODE:\s*verify-ca", compose):
        return _fail("app_db_tls",
                     "the prod compose must set PGBOUNCER_SERVER_TLS_SSLMODE=verify-ca (pin postgres's "
                     "cert on the pgbouncer<->postgres hop)")
    if "PGBOUNCER_SERVER_TLS_CA_FILE" not in compose or "PGBOUNCER_CLIENT_TLS_CERT_FILE" not in compose:
        return _fail("app_db_tls",
                     "the prod compose must wire the pinned CA (server_tls_ca_file) + a stable "
                     "client cert (client_tls_cert_file) for verify-ca")
    if "ALTER SYSTEM SET ssl" not in init:
        return _fail("app_db_tls",
                     "docker-init.sh must enable Postgres TLS (ALTER SYSTEM SET ssl = on) from the "
                     "mounted cert")
    if "server_tls_sslmode" not in entry or "client_tls_sslmode" not in entry:
        return _fail("app_db_tls",
                     "pgbouncer-entrypoint.sh must wire server_tls + client_tls")
    if "server_tls_ca_file" not in entry:
        return _fail("app_db_tls",
                     "pgbouncer-entrypoint.sh must wire server_tls_ca_file (the pinned postgres CA for "
                     "verify-ca on the backend hop)")
    # v9.132 — the entrypoint must ENFORCE the pairing: verify-* without a CA
    # cannot verify, so it must fail fast rather than start unverified.
    if not re.search(r"verify-ca\|verify-full", entry) or "requires PGBOUNCER_SERVER_TLS_CA_FILE" not in entry:
        return _fail("app_db_tls",
                     "pgbouncer-entrypoint.sh must REQUIRE the CA file when server_tls_sslmode is "
                     "verify-* (fail fast, not start with verification effectively off)")
    return _ok("app_db_tls",
               "the app<->DB path is TLS on both hops AND verifies the pinned self-signed certs "
               "(app verify-ca pins pgbouncer; pgbouncer server_tls verify-ca pins postgres) — a MITM "
               "with a different cert is rejected; verify-full + a real CA stays the operator's upgrade")


# ---------------------------------------------------------------------------
# Request-correlation id (v9.122). A per-request id stamped into the structured
# logs and echoed in X-Request-ID, so an operator can correlate a log line to a
# caller's request. The VOCATION constraint is the load-bearing part: the id
# must stay ephemeral and per-request and must NEVER be written to a DB row — in
# particular not the append-only audit-of-record, where the C1 trigger would
# turn it into a permanent, reconstructable cross-request linkage key (exactly
# the surveillance vector Polaris refuses). A static grep cannot PROVE
# non-persistence (the DB-backed test does that), but it can bite the realistic
# regressions: the id leaking into the DB-write module, the id-owning module
# gaining DB access, or the inbound-trust boundary being bypassed.
# ---------------------------------------------------------------------------
def check_correlation_id(root: pathlib.Path) -> list[Finding]:
    obs = _read(root, "polaris_web/observability.py")
    app = _read(root, "polaris_web/app.py")
    sec = _read(root, "polaris_web/security.py")
    if not (obs and app):
        return _fail("correlation_id", "observability.py or app.py is missing")

    # --- the id core lives in observability.py ---
    if "ContextVar(" not in obs:
        return _fail("correlation_id",
                     "observability.py must hold the request id in a contextvars.ContextVar "
                     "(per-request, not a global)")
    if "[A-Za-z0-9-]" not in obs or "{8,64}" not in obs:
        return _fail("correlation_id",
                     "the inbound id validator must bound BOTH charset ([A-Za-z0-9-]) and length "
                     "({8,64}) — an unbounded value is a log-injection + memory-abuse hole")
    if "uuid4(" not in obs:
        return _fail("correlation_id",
                     "observability.py must mint a fresh uuid4 id when none is supplied")
    # The id-owning module must never touch the DB: if it could INSERT, the
    # non-persistence property would no longer be auditable from app.py alone.
    if re.search(r"\b(execute|cursor|get_db)\s*\(", obs) or re.search(r"\bINSERT\b", obs):
        return _fail("correlation_id",
                     "observability.py must stay DB-free (no execute/cursor/get_db/INSERT) — the "
                     "request id must never reach a DB row from the module that owns it")

    # --- the lifecycle is wired in app.py ---
    if "set_request_id(" not in app:
        return _fail("correlation_id", "app.py must bind the id in a before_request (set_request_id)")
    if "X-Request-ID" not in app:
        return _fail("correlation_id", "app.py must echo the id in the X-Request-ID response header")
    if "teardown_request" not in app or "reset_request_id(" not in app:
        return _fail("correlation_id",
                     "app.py must clear the id in teardown_request (reset_request_id) so it does not "
                     "leak across requests on a reused worker")
    # set_request_id may ONLY be fed by validate_or_new_request_id — that is the
    # sole function allowed to trust inbound bytes. A raw header into the
    # contextvar would be a log-injection / response-splitting path.
    for m in re.finditer(r"(?<![A-Za-z_])set_request_id\(", app):
        window = app[m.end():m.end() + 90]
        if "validate_or_new_request_id" not in window:
            return _fail("correlation_id",
                         "set_request_id() must be called only with validate_or_new_request_id(...) "
                         "(never a raw inbound header)")

    # --- VOCATION: the id must not reach the DB-write / audit path ---
    # The DB-write + audit module must not even reference the id.
    if "get_request_id" in sec:
        return _fail("correlation_id",
                     "security.py (the DB-write/audit module) must not reference get_request_id — the "
                     "request id has no business in an audit row (vocation: no cross-request linkage)")
    # Backstop in app.py: the id must not co-occur with an audit/DB write call.
    for line in app.splitlines():
        if "get_request_id" not in line:
            continue
        if re.search(r"(_audit\(|cur\.execute\(|reason_code|requesting_purpose)", line):
            return _fail("correlation_id",
                         "the request id appears on a DB-write/audit line in app.py — it must never "
                         "be persisted (vocation)")
    # The id must not be derived from identity (that would make it a user key).
    for line in app.splitlines():
        if "set_request_id" not in line and "validate_or_new_request_id" not in line:
            continue
        if re.search(r"(session\.get\(|user_id|username)", line):
            return _fail("correlation_id",
                         "the request id must not be seeded from identity (session/user_id/username)")

    return _ok("correlation_id",
               "request id is per-request, validated+bounded ([A-Za-z0-9-]{8,64} or uuid4), echoed in "
               "X-Request-ID, cleared in teardown, and never written to the audit-of-record (vocation)")


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
    # because only the architecture doc was guarded. Guard both — and check
    # EVERY occurrence, not just the first: v9.141 shipped a README whose first
    # count was right while three later "26 tables" instances had drifted
    # (re.search only validated the first match).
    docs = [
        ("docs/ARCHITECTURE-OVERVIEW.md", r"(\d+)\s+(?:schema )?tables"),
        ("README.md", r"(\d+)\s+(?:schema )?tables"),
    ]
    for rel, pat in docs:
        stated_counts = [int(s) for s in re.findall(pat, _read(root, rel))]
        if not stated_counts:
            return _fail("table_count", f"{rel} states no schema-table count")
        wrong = sorted(set(s for s in stated_counts if s != n))
        if wrong:
            return _fail("table_count",
                         f"{rel} says {wrong} tables somewhere but the schema "
                         f"defines {n} (every stated count must match)")
    return _ok("table_count", f"doc table counts match the schema ({n}, all instances)")


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
# Code-object currency (v9.152) — the launcher preserves DATA across launches
# (it skips the schema reload when the core tables already exist), so a change
# to a function/trigger/view SIGNATURE in the repo does NOT reach an existing
# database through that path. Migrations cover schema/data deltas; CODE objects
# (procedures, triggers, atlas functions, ontology views) must be re-applied on
# every launch or a stale function 500s the app (the "ATLAS FEED INTERRUPTED"
# bug: v9.146 changed the atlas function signatures and old DBs kept the old
# ones). Pin that the launcher re-applies the atlas function file every launch.
# ---------------------------------------------------------------------------
def check_launcher_refreshes_code(root: pathlib.Path) -> list[Finding]:
    sh = _read(root, "polaris_mac_launch.sh")
    if not sh:
        return _fail("launcher_code", "polaris_mac_launch.sh is missing")
    # The atlas function file must be re-applied on every launch. It is the file
    # whose v9.146 signature change caused the drift bug; if the launcher
    # re-applies it, the whole code-object class is covered alongside it.
    if "11_atlas.sql" not in sh:
        return _fail("launcher_code",
                     "the launcher never re-applies 11_atlas.sql; a changed atlas function "
                     "signature would not reach an existing DB (the ATLAS-FEED-INTERRUPTED bug)")
    return _ok("launcher_code",
               "the launcher re-applies idempotent code objects (atlas functions etc.) on every launch")


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
    # v9.142: the /atlas HTML route no longer reads requestor_location at all
    # (its inline globe-node query was dead code, removed; the globe fetches
    # via /api/atlas/*, whose SQL functions exclude ZK rows entirely, asserted
    # above). The one remaining app.py HTML read path is /verifications.
    app = _read(root, "polaris_web/app.py")
    if app.count("THEN NULL ELSE ve.requestor_location") < 1:
        return _fail("c6_atlas_zk",
                     "app.py /verifications must redact requestor_location "
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


# ---------------------------------------------------------------------------
# Template/route integrity — every url_for('name') in a template must name a
# function that actually carries an @app.route in app.py. A renamed or deleted
# route otherwise becomes a BuildError 500 on whichever page links to it, and
# nothing static catches it until a user clicks. (v9.143; the same sweep found
# role-gated buttons rendered for roles that 403 on click, which the
# UiLinkIntegrityTests crawler in test_app.py now guards dynamically.)
# ---------------------------------------------------------------------------
def check_template_endpoints_resolve(root: pathlib.Path) -> list[Finding]:
    app_src = _read(root, "polaris_web/app.py")
    # Collect the function name following each @app.route decorator stack.
    endpoints: set[str] = set()
    pending_route = False
    for line in app_src.splitlines():
        if line.startswith("@app.route("):
            pending_route = True
        elif pending_route and line.startswith("def "):
            m = re.match(r"def ([A-Za-z_][A-Za-z_0-9]*)\(", line)
            if m:
                endpoints.add(m.group(1))
            pending_route = False
    endpoints.add("static")  # Flask built-in
    missing = []
    tpl_dir = root / "polaris_web" / "templates"
    if tpl_dir.is_dir():
        for tpl in sorted(tpl_dir.glob("*.html")):
            names = re.findall(r"url_for\(\s*'([A-Za-z_][A-Za-z_0-9]*)'",
                               tpl.read_text(encoding="utf-8"))
            for name in names:
                if name not in endpoints:
                    missing.append(f"{tpl.name} -> {name}")
    if missing:
        return _fail("template_endpoints",
                     "template url_for() names no @app.route function: "
                     + ", ".join(sorted(set(missing))))
    return _ok("template_endpoints",
               f"every template url_for() resolves to a real route ({len(endpoints) - 1} endpoints)")


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
    check_signing_key_generation,
    check_pqc_real_signing,
    check_verify_enforced,
    check_pqc_second_witness,
    check_pqc_posture,
    check_edge_pq_kex,
    check_signature_self_contained_verify,
    check_prod_real_pqc,
    check_sql_console_readonly,
    check_prod_image_no_test_deps,
    check_cve_scanning,
    check_image_cve_scanning,
    check_sast_scanning,
    check_migration_timeouts,
    check_deploy_syncs_db_objects,
    check_web_concurrency_honored,
    check_prometheus_multiprocess,
    check_health_liveness_readiness_split,
    check_compose_resource_limits,
    check_prod_images_digest_pinned,
    check_alert_rules,
    check_alert_runbooks,
    check_duress_alertable,
    check_prod_fail_closed,
    check_encryption_at_rest_posture,
    check_erasure_procedure,
    check_replication_scaffolding,
    check_pgbackrest_scaffolding,
    check_pgbouncer_self_built,
    check_caddy_self_built,
    check_prod_stack_boot,
    check_container_hardening,
    check_app_db_tls,
    check_correlation_id,
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
    check_launcher_refreshes_code,
    check_local_clock_convention,
    check_c6_atlas_redacts_zk_location,
    check_coercion_evidence_retained,
    check_zk_verify_anti_replay,
    check_no_migration_column_drift,
    check_operator_scripts_validate_argv,
    check_template_endpoints_resolve,
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
