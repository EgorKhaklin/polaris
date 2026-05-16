"""polaris_swarm/fault_injection.py — realistic defects for the kill test.

v9.25 / BIG MISSION Tier 5 #2. Distinct from polaris_swarm/fixtures/
(v9.24) which holds *expected-firing matrices* for static analysis.
Fault-injection runs the defect against the live test substrate +
measures detection rate.

**Anti-Architect invariants enforced (Sanctum 2026-05-16 §II T5#2):**

1. Defects must be REALISTIC — not toy scenarios. Each defect mirrors
   a real production failure mode (CSRF dropped in deploy, CSP
   regressed by template edit, auth decorator missed, partial unique
   index dropped, append-only trigger weakened).

2. Defects must be detectable by EXISTING ants/tests, NOT by
   defect-specific new ants. If you have to write a new ant to catch
   the defect, the kill test is gaming itself.

3. Defects MUST be reversible. Each `apply()` returns a `revert_token`
   that the runner uses to restore state in a try/finally. The runner
   refuses to start a second defect until the previous is reverted.

**Five defects shipped in v9.25:**

Production-shape (3):
  - `DefectDropCsrf`            — remove CSRF check from /login POST
  - `DefectCspUnsafeInline`     — add 'unsafe-inline' to CSP script-src
  - `DefectRevokeAuthDecorator` — remove @login_required from /dashboard

Invariant-shape (2):
  - `DefectC3DropUniqueIndex`   — drop uq_one_active_token_per_individual
  - `DefectAppendOnlyBypass`    — alter trigger to silently allow DELETE

Each defect is detectable by at least one existing test in
test_structural_invariants.py + ai-done.sh check + Hypothesis property
test. The kill test in scripts/polaris-swarm-killtest.sh runs the swarm
against each defect, records which detection channels fire, and reports
per-defect detection time + overall pass-rate against the joint Sanctum's
bar (≥70% within 1 pass; ≥90% within 3 passes).
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

_REPO_ROOT = Path(__file__).resolve().parent.parent


@dataclass
class RevertToken:
    """Opaque handle the runner uses to revert a defect."""
    defect_name: str
    revert_fn: Callable[[], None]
    backup_data: dict = field(default_factory=dict)


@dataclass(frozen=True)
class Defect:
    """One injectable defect with its detection-channel expectation.

    `apply` mutates the live substrate and returns a RevertToken.
    `detection_channels` is the list of channels that SHOULD fire when
        this defect is present. The runner records which fired and
        which didn't.

    `shape` is one of:
        'production'  — defect mirrors a real deploy/operator failure
        'invariant'   — defect violates a structural invariant (C1-C10)
    """
    name: str
    description: str
    shape: str
    apply: Callable[[], RevertToken]
    detection_channels: tuple  # e.g. ("test_structural_invariants", "ai-done.sh")


# ---------- Helper: file backup + restore -----------------------------

def _backup_file(path: Path) -> bytes:
    return path.read_bytes()


def _restore_file(path: Path, original: bytes) -> None:
    path.write_bytes(original)


# ---------- Defect 1: drop CSRF check from /login --------------------

def _apply_drop_csrf() -> RevertToken:
    target = _REPO_ROOT / "polaris_web" / "app.py"
    original = _backup_file(target)
    txt = original.decode()
    # The login POST handler calls security.csrf_protect. Comment it out
    # IF present as a decorator. We do a single, minimal edit.
    # Look for either the decorator @security.csrf_protect on the login
    # POST route OR an inline csrf check call.
    patched = re.sub(
        r'(\n\s*)(@security\.csrf_protect)(\s*\n\s*def\s+(?:login|do_login))',
        r'\1# \2  # FAULT_INJECTION: DefectDropCsrf\3',
        txt,
        count=1,
    )
    if patched == txt:
        # Fall back: comment any csrf_protect decorator in the file's
        # first 1000 lines (will still be a real defect detectable by
        # the security test suite even if not specifically on login)
        patched = re.sub(
            r'(\n\s*)(@security\.csrf_protect)',
            r'\1# \2  # FAULT_INJECTION: DefectDropCsrf',
            txt,
            count=1,
        )
    target.write_bytes(patched.encode())

    def revert():
        _restore_file(target, original)
    return RevertToken(defect_name="DefectDropCsrf", revert_fn=revert)


# ---------- Defect 2: CSP allows unsafe-inline -----------------------

def _apply_csp_unsafe_inline() -> RevertToken:
    target = _REPO_ROOT / "polaris_web" / "security.py"
    original = _backup_file(target)
    txt = original.decode()
    # Mutate the CSP script-src to include 'unsafe-inline'.
    # Look for script-src 'self' and replace with script-src 'self' 'unsafe-inline'
    patched = re.sub(
        r"script-src 'self'(?! 'unsafe-inline')",
        "script-src 'self' 'unsafe-inline'  /* FAULT_INJECTION: DefectCspUnsafeInline */",
        txt,
        count=1,
    )
    target.write_bytes(patched.encode())

    def revert():
        _restore_file(target, original)
    return RevertToken(defect_name="DefectCspUnsafeInline", revert_fn=revert)


# ---------- Defect 3: remove @login_required from /dashboard --------

def _apply_revoke_auth_decorator() -> RevertToken:
    target = _REPO_ROOT / "polaris_web" / "app.py"
    original = _backup_file(target)
    txt = original.decode()
    # Find a @security.login_required decorator and comment it out.
    patched = re.sub(
        r'(\n\s*)(@security\.login_required)',
        r'\1# \2  # FAULT_INJECTION: DefectRevokeAuthDecorator',
        txt,
        count=1,
    )
    target.write_bytes(patched.encode())

    def revert():
        _restore_file(target, original)
    return RevertToken(defect_name="DefectRevokeAuthDecorator", revert_fn=revert)


# ---------- Defect 4: drop partial unique index (C3 violation) ------

def _apply_c3_drop_unique_index() -> RevertToken:
    """Schema-level defect. Note: this modifies the SCHEMA SOURCE FILE
    (01_schema.sql OR 02_indexes.sql) NOT the live DB (the kill test
    never touches a real DB; static analysis is the detection channel).

    The actual index name in the current schema is `uq_one_active_per_person`
    (some docs use `uq_one_active_token_per_individual` — the kill test
    accepts either)."""
    # Find the file containing the partial unique index on IdentityToken
    candidates = [
        _REPO_ROOT / "polaris_sql" / "02_indexes.sql",
        _REPO_ROOT / "polaris_sql" / "01_schema.sql",
    ]
    target = None
    original = None
    txt = None
    pattern = re.compile(
        r'(CREATE\s+UNIQUE\s+INDEX\s+\w+\s+ON\s+IdentityToken'
        r'[^;]*\bindividual_id[^;]*WHERE[^;]*ACTIVE[^;]*;)',
        re.IGNORECASE | re.DOTALL,
    )
    for c in candidates:
        if c.is_file():
            content = _backup_file(c).decode()
            if pattern.search(content):
                target = c
                original = content.encode()
                txt = content
                break

    if target is None:
        raise RuntimeError(
            "could not locate partial unique index on IdentityToken "
            "in schema files; kill test cannot inject DefectC3DropUniqueIndex"
        )

    patched = pattern.sub(
        r'-- FAULT_INJECTION: DefectC3DropUniqueIndex\n-- \1',
        txt,
        count=1,
    )
    target.write_bytes(patched.encode())

    def revert():
        _restore_file(target, original)
    return RevertToken(defect_name="DefectC3DropUniqueIndex", revert_fn=revert)


# ---------- Defect 5: append-only trigger weakened ------------------

def _apply_append_only_bypass() -> RevertToken:
    """Weaken the reject_audit_modification function by inserting an
    UNCONDITIONAL `RETURN OLD;` immediately before its terminal
    `RAISE EXCEPTION`. The RAISE EXCEPTION becomes unreachable; the
    trigger silently allows the modification. C1 violated silently.

    This is the real production failure shape: a developer adds
    "RETURN OLD;" to unblock a local test, intends to remove it,
    forgets. The audit-of-record breaks without any audit row.
    """
    target = _REPO_ROOT / "polaris_sql" / "06_triggers.sql"
    original = _backup_file(target)
    txt = original.decode()

    # Find the reject_audit_modification function body's terminal
    # `RAISE EXCEPTION` and insert `RETURN OLD;` immediately before it
    # (outside any IF/ELSIF/ELSE block; at top-level of the function body).
    # The terminal RAISE comes after the carve-out IF block closes
    # ("END IF;" + blank line + "RAISE EXCEPTION ...").
    patched = re.sub(
        r"(END IF;\s*\n\s*)(RAISE EXCEPTION)",
        r"\1-- FAULT_INJECTION: DefectAppendOnlyBypass\n    RETURN OLD;\n    \2",
        txt,
        count=1,
    )

    if patched == txt:
        # Fallback: just insert RETURN OLD; before the first RAISE
        # EXCEPTION in the function (less surgical but still a real
        # defect shape).
        patched = re.sub(
            r"(RAISE EXCEPTION\s+'%)",
            r"-- FAULT_INJECTION: DefectAppendOnlyBypass\n    RETURN OLD;\n    \1",
            txt,
            count=1,
        )

    target.write_bytes(patched.encode())

    def revert():
        _restore_file(target, original)
    return RevertToken(defect_name="DefectAppendOnlyBypass", revert_fn=revert)


# ---------- The defect catalog ---------------------------------------

ALL_DEFECTS = (
    Defect(
        name="DefectDropCsrf",
        description="@security.csrf_protect decorator removed from a "
                    "POST handler. Real production failure: developer "
                    "removes for a 'quick test' and forgets to restore.",
        shape="production",
        apply=_apply_drop_csrf,
        detection_channels=("test_structural_invariants",
                            "test_app",
                            "ai-done.sh"),
    ),
    Defect(
        name="DefectCspUnsafeInline",
        description="Content-Security-Policy script-src extended with "
                    "'unsafe-inline'. Real production failure: temporary "
                    "relaxation to debug an analytics snippet, never "
                    "rolled back.",
        shape="production",
        apply=_apply_csp_unsafe_inline,
        detection_channels=("test_structural_invariants",
                            "ant_csp_health",
                            "ai-coherence.sh"),
    ),
    Defect(
        name="DefectRevokeAuthDecorator",
        description="@security.login_required decorator removed from a "
                    "protected route. Real production failure: refactor "
                    "split a function and the decorator stayed on the "
                    "wrapper that no longer exists.",
        shape="production",
        apply=_apply_revoke_auth_decorator,
        detection_channels=("test_app",
                            "test_structural_invariants",
                            "ai-done.sh"),
    ),
    Defect(
        name="DefectC3DropUniqueIndex",
        description="Partial unique index uq_one_active_token_per_individual "
                    "removed from schema. C3 violation; two ACTIVE tokens "
                    "for the same individual would now be possible.",
        shape="invariant",
        apply=_apply_c3_drop_unique_index,
        detection_channels=("test_structural_invariants",
                            "test_invariants_property",
                            "ai-meta.sh"),
    ),
    Defect(
        name="DefectAppendOnlyBypass",
        description="reject_audit_modification trigger weakened to "
                    "RETURN OLD instead of RAISE EXCEPTION. C1 violation; "
                    "TokenLifecycleEvent rows could be deleted silently.",
        shape="invariant",
        apply=_apply_append_only_bypass,
        detection_channels=("test_structural_invariants",
                            "ai-meta.sh"),
    ),
)


def list_defects() -> list[dict]:
    """Operator-readable inventory."""
    return [
        {
            "name": d.name,
            "shape": d.shape,
            "description": d.description,
            "detection_channels": list(d.detection_channels),
        }
        for d in ALL_DEFECTS
    ]
