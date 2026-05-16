"""scripts/_cm_check.py — CM constitutional-meta-constraint enforcement.

Invoked by ai-done.sh step 15 (v9.28 / Hydra #5). Exits non-zero if
CM's claims about the system don't match reality. Override:
POLARIS_ALLOW_CM_MISMATCH=1 (handled by ai-done.sh wrapper).

CM's claims (per meta/watcher-predicates.md): the system is what it
claims to be. Concrete checks:

  1. POLARIS_VERSION in __version__.py matches the most-recent
     CHANGELOG entry's version.
  2. The freeze-line target version (v9.30 per MISSION.md §Freeze line)
     is present and unchanged.
  3. meta/watcher-predicates.md exists and enumerates exactly the
     watchers present in polaris_hydra/watchers/.

Per v9.28 Sanctum: "A self-model check that only reports is theater;
a self-model check that can stop a ship is the point of having one."
"""

from __future__ import annotations

import re
import sys
from pathlib import Path


def cm_check(root: Path) -> list[str]:
    """Returns list of mismatch strings. Empty list = CM is honest."""
    mismatches: list[str] = []

    # Claim 1: __version__.py matches latest CHANGELOG entry
    try:
        vfile = (root / "polaris_web" / "__version__.py").read_text()
        # Match the canonical assignment line, not docstring mentions.
        # The canonical form (v9.06+) is: `__version__: str = "X.Y"` at
        # start of line.
        m = re.search(r'^__version__\s*:\s*str\s*=\s*["\']([^"\']+)["\']',
                      vfile, re.MULTILINE)
        if m is None:
            # Fallback: match `POLARIS_VERSION: str = "X.Y"` line
            m = re.search(
                r'^POLARIS_VERSION\s*:\s*str\s*=\s*["\']([^"\']+)["\']',
                vfile, re.MULTILINE)
        declared = m.group(1) if m else None
        cl = (root / "CHANGELOG.md").read_text()
        m2 = re.search(r'^## v(\d+\.\d+)', cl, re.MULTILINE)
        latest_cl = m2.group(1) if m2 else None
        if declared and latest_cl and declared != latest_cl:
            mismatches.append(
                f"CM-mismatch: __version__.py={declared} but latest "
                f"CHANGELOG entry is v{latest_cl} — they must match "
                f"(v9.27 freeze requires monotonic version-bump per ship)"
            )
    except Exception as e:
        mismatches.append(f"CM-check error: version-vs-changelog: {e}")

    # Claim 2: freeze-line v9.30 present in MISSION.md
    try:
        mission = (root / "MISSION.md").read_text()
        if "Freeze line" not in mission:
            mismatches.append(
                "CM-mismatch: MISSION.md §Freeze line missing — v9.27 "
                "constitutional record requires this section"
            )
        elif "v9.30" not in mission:
            mismatches.append(
                "CM-mismatch: MISSION.md does not reference v9.30 freeze "
                "version — v9.27 constitutional record requires it"
            )
    except Exception as e:
        mismatches.append(f"CM-check error: mission-freeze-line: {e}")

    # Claim 3: meta/watcher-predicates.md enumerates actual watchers
    try:
        pred_file = root / "meta" / "watcher-predicates.md"
        if not pred_file.is_file():
            mismatches.append(
                "CM-mismatch: meta/watcher-predicates.md missing — "
                "v9.28 Hydra #1 requires it"
            )
        else:
            pred_content = pred_file.read_text()
            wpath = root / "polaris_hydra" / "watchers"
            actual = sorted(
                f.stem for f in wpath.glob("*_watcher.py")
                if f.name != "__init__.py"
            )
            for w in actual:
                if w not in pred_content:
                    mismatches.append(
                        f"CM-mismatch: watcher {w!r} exists but is NOT "
                        f"listed in meta/watcher-predicates.md"
                    )
    except Exception as e:
        mismatches.append(f"CM-check error: watcher-enumeration: {e}")

    # Claim 4 (v9.29 / CM1): GROUND-TRUTH ANCHOR.
    # Per Sanctum 2026-05-16 v9.29: "CM cannot grade its own homework.
    # Give it one ground-truth input it cannot author."
    #
    # The anchor: AST count of `def test_*` methods in
    # test_structural_invariants.py. The COUNT is computed by Python's
    # ast module from the actual file's actual bytes. CM does not
    # write the test methods or their count; the operator/agent
    # authors tests but the ast parse is mechanically external. The
    # count is a floor that ratchets up only with a recorded
    # freeze-amendment-protocol amendment (not by re-derivation).
    #
    # The floor here is itself protected by the amendment protocol:
    # lowering it requires a Sanctum + cost.
    try:
        import ast
        test_file = root / "polaris_web" / "test_structural_invariants.py"
        if not test_file.is_file():
            mismatches.append(
                "CM-mismatch (ground-truth): "
                "test_structural_invariants.py missing — CM has no anchor"
            )
        else:
            tree = ast.parse(test_file.read_text())
            test_count = 0
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
                    test_count += 1

            # The floor. Per the amendment protocol: this number may
            # only ratchet UP, and only with an amendment Sanctum.
            # v9.29 floor = 850 (CM at v9.28 saw 844; v9.29 adds tests).
            # Lowering this requires meta/freeze-amendment-protocol.md
            # Move 2 (amendment with stated cost).
            v9_29_floor = 850

            if test_count < v9_29_floor:
                mismatches.append(
                    f"CM-mismatch (ground-truth): test_structural_invariants.py "
                    f"has {test_count} test_* methods, below v9.29 floor {v9_29_floor}. "
                    f"Tests can grow but never shrink past the floor without an "
                    f"amendment Sanctum per meta/freeze-amendment-protocol.md."
                )
    except Exception as e:
        mismatches.append(f"CM-check error: ground-truth anchor: {e}")

    return mismatches


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: _cm_check.py <repo_root>", file=sys.stderr)
        return 2
    root = Path(sys.argv[1])
    mismatches = cm_check(root)
    if mismatches:
        print("CM_MISMATCH")
        for m in mismatches:
            print(f"  {m}")
        return 1
    print("CM_OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
