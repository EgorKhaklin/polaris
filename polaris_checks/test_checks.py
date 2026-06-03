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


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
