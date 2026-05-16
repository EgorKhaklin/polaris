"""ant_dependency_in_use — verify Python top-level imports are in substrate.

Slice: top-level `import` and `from X import` statements in
`polaris_web/*.py` and `polaris_hydra/*.py` and `polaris_swarm/*.py`.

Local rule: every third-party module Polaris imports MUST be
mentioned in `DEVNOTES/substrate.md`. Stdlib + first-party
(polaris_*) imports are allowed unconditionally. If a third-party
import is missing from the catalog, deposit a `drift` pheromone.

This catches the silent introduction of new dependencies — a major
class of supply-chain drift. The catalog is the contract; this
ant enforces it.
"""

from __future__ import annotations

import re
import sys

from polaris_swarm.base import Ant, AntFinding, KIND_DRIFT


# Stdlib modules are extracted at runtime so the ant adapts to the
# Python version it runs under. First-party packages are listed
# explicitly.
FIRST_PARTY_PREFIXES = (
    "polaris_", "ai_brain_map",  # internal modules
    "test_",                      # in-repo test modules (test_app, test_invariants_property, etc.)
    "anchoring", "zk",            # polaris_web first-party helpers
    "security", "app",            # polaris_web's app + security modules
)

# Known stdlib top-level modules (Python 3.10+). Conservative
# allowlist — sys.stdlib_module_names is the source of truth at
# runtime; this fallback is for offline / partial-stdlib environments.
_STDLIB_FALLBACK = frozenset({
    "abc", "argparse", "array", "ast", "asyncio", "base64", "bisect",
    "builtins", "calendar", "collections", "concurrent", "contextlib",
    "contextvars", "copy", "csv", "ctypes", "dataclasses", "datetime",
    "decimal", "difflib", "dis", "email", "enum", "errno", "fcntl",
    "fnmatch", "functools", "gc", "getpass", "glob", "grp", "gzip",
    "hashlib", "heapq", "hmac", "html", "http", "importlib", "inspect",
    "io", "ipaddress", "itertools", "json", "logging", "math", "mimetypes",
    "multiprocessing", "operator", "os", "pathlib", "pickle", "platform",
    "plistlib", "posixpath", "pprint", "queue", "random", "re", "secrets",
    "select", "shlex", "shutil", "signal", "smtplib", "socket", "sqlite3",
    "ssl", "stat", "string", "struct", "subprocess", "sys", "tempfile",
    "textwrap", "threading", "time", "timeit", "token", "tokenize",
    "traceback", "types", "typing", "unicodedata", "unittest", "urllib",
    "uuid", "warnings", "weakref", "xml", "zipfile", "zlib",
})


# Match top-level `import X` and `from X import Y`.
_IMPORT_RE = re.compile(
    r"^\s*(?:from\s+([\w.]+)\s+import|import\s+([\w.]+))",
    re.MULTILINE,
)


def _stdlib_set() -> frozenset[str]:
    """Use sys.stdlib_module_names (3.10+) if available, else fallback."""
    names = getattr(sys, "stdlib_module_names", None)
    if names:
        return frozenset(names)
    return _STDLIB_FALLBACK


class AntDependencyInUse(Ant):
    NAME = "ant_dependency_in_use"
    DESCRIPTION = "Pheromones third-party imports missing from substrate.md."

    def scan(self) -> list[AntFinding]:
        findings: list[AntFinding] = []
        substrate = self._read("DEVNOTES", "substrate.md") or ""
        substrate_lower = substrate.lower()
        stdlib = _stdlib_set()

        from polaris_swarm.scan_filters import is_polaris_source
        seen: set[str] = set()
        for src_dir in ("polaris_web", "polaris_hydra", "polaris_swarm"):
            src_path = self.root / src_dir
            if not src_path.is_dir():
                continue
            for py in src_path.rglob("*.py"):
                # v9.05 / B1: skip venv-vendored deps' import lines —
                # they reflect their dependencies, not Polaris's.
                if not is_polaris_source(py):
                    continue
                try:
                    body = py.read_text(errors="replace")
                except OSError:
                    continue
                for m in _IMPORT_RE.finditer(body):
                    name = m.group(1) or m.group(2)
                    if not name:
                        continue
                    top = name.split(".", 1)[0]
                    if top in stdlib:
                        continue
                    if any(top.startswith(p) for p in FIRST_PARTY_PREFIXES):
                        continue
                    if top in seen:
                        continue
                    seen.add(top)
                    # Allow common test-only deps (hypothesis, pytest)
                    # which are dev tools, not runtime dependencies.
                    if top in {"hypothesis", "pytest"}:
                        continue
                    # Check substrate.md (case-insensitive substring)
                    if top.lower() not in substrate_lower:
                        findings.append(AntFinding(
                            node_id=f"dependency:{top}",
                            intensity=4.0,
                            kind=KIND_DRIFT,
                            evidence={
                                "message": (
                                    f"third-party import {top!r} missing "
                                    f"from substrate.md"
                                ),
                                "fix_hint": (
                                    f"add {top} to DEVNOTES/substrate.md "
                                    f"with version + purpose"
                                ),
                            },
                            half_life_hours=168.0,  # week-scale
                        ))
        return findings
