#!/usr/bin/env bash
# ============================================================================
# polaris-sanctum-status.sh — classify + tag Sanctum files (S1+S2+S3)
#
# v9.29 / BIG MISSION Sanctum items S1+S2+S3. Combined script because the
# three operations share one walk over the sanctum/ directory.
#
# S1 — Status-tag every Sanctum (ACTIVE / SUPERSEDED / DEAD).
# S2 — Core vs apparatus scope tag + ratio.
# S3 — Unreferenced = inert (archive).
#
# Classification logic:
#
#   ACTIVE      = referenced by ≥1 file in polaris_*/, scripts/, docs/,
#                 DEVNOTES/, or another currently-ACTIVE Sanctum AND
#                 not flagged SUPERSEDED.
#   SUPERSEDED  = explicitly walked back / superseded by a later Sanctum
#                 OR mentions "superseded" / "walked back" in its body.
#   DEAD        = unreferenced AND its subject (watcher / arc / feature)
#                 no longer exists in the source tree.
#
# Scope tag (for ACTIVE only):
#   core      = touches polaris_sql / polaris_web / polaris_zk
#   apparatus = touches polaris_hydra / polaris_swarm / polaris_foresight /
#               scripts/ai-* / meta/ / sanctum/
#
# Usage:
#   ./scripts/polaris-sanctum-status.sh             # classify + report
#   ./scripts/polaris-sanctum-status.sh --json
#   ./scripts/polaris-sanctum-status.sh --archive   # MOVE non-ACTIVE to archive/sanctum/
#   ./scripts/polaris-sanctum-status.sh --archive --dry-run
# ============================================================================

set -uo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"
POLARIS_ROOT="$(cd -- "${SCRIPT_DIR}/.." &> /dev/null && pwd)"

JSON=0
ARCHIVE=0
DRY_RUN=0
for arg in "$@"; do
    case "${arg}" in
        --json)       JSON=1 ;;
        --archive)    ARCHIVE=1 ;;
        --dry-run)    DRY_RUN=1 ;;
        --help|-h)
            sed -n '2,30p' "$0" | sed 's/^# \{0,1\}//'
            exit 0
            ;;
    esac
done

cd "${POLARIS_ROOT}"

python3 - "${JSON}" "${ARCHIVE}" "${DRY_RUN}" <<'PY'
import json
import os
import re
import shutil
import sys
import subprocess
from pathlib import Path

json_mode, archive_mode, dry_run = sys.argv[1:4]
json_mode = json_mode == "1"
archive_mode = archive_mode == "1"
dry_run = dry_run == "1"

ROOT = Path(os.getcwd())
SANCTUM_DIR = ROOT / "sanctum"
ARCHIVE_DIR = ROOT / "archive" / "sanctum"

# Scope discriminators
CORE_GLOBS = (
    "polaris_sql/", "polaris_web/", "polaris_zk/",
)
APPARATUS_GLOBS = (
    "polaris_hydra/", "polaris_swarm/", "polaris_foresight/",
    "scripts/ai-", "meta/", "sanctum/",
)


def list_sanctums():
    return sorted(SANCTUM_DIR.glob("*.md"))


def is_referenced(sanctum_path: Path) -> tuple[bool, list[str]]:
    """Returns (is_referenced, list_of_referencers).
    A Sanctum is referenced if any file outside sanctum/ or
    archive/ mentions its basename."""
    name = sanctum_path.name
    stem = sanctum_path.stem
    try:
        proc = subprocess.run(
            ["grep", "-rl", "--include=*.py",
             "--include=*.md", "--include=*.sh",
             "--include=*.sql", "--include=*.json",
             "--exclude-dir=archive",
             "--exclude-dir=sanctum",
             "--exclude-dir=.git",
             "--exclude-dir=__pycache__",
             stem, str(ROOT)],
            capture_output=True, timeout=30,
        )
        refs = [l for l in proc.stdout.decode().strip().split("\n") if l]
        return (len(refs) > 0, refs)
    except Exception:
        return (False, [])


def detect_superseded(sanctum_path: Path, all_sanctums: list[Path]) -> bool:
    """Detect ONLY explicit-status markers; never substring-match
    keyword in body (which would sweep meta-Sanctums about supersession)."""
    body = sanctum_path.read_text()
    # Explicit status line declaring this Sanctum superseded
    explicit_markers = (
        "**Status:** SUPERSEDED",
        "**STATUS:** SUPERSEDED",
        "Status: SUPERSEDED",
        "REVOKED + SHIPPED",  # the v8.74 revocation pattern
        "**Status:** REVOKED",
        "Status: REVOKED",
    )
    for marker in explicit_markers:
        if marker in body:
            return True
    # Later Sanctum explicitly says "supersedes <this-stem>"
    stem = sanctum_path.stem
    sorted_paths = sorted(all_sanctums, key=lambda p: p.name)
    try:
        idx = sorted_paths.index(sanctum_path)
    except ValueError:
        return False
    for later in sorted_paths[idx + 1:]:
        later_body = later.read_text()
        # Only catch explicit "supersedes <stem>" / "supersedes the <stem>"
        # patterns; not generic supersede mentions
        for pat in (f"supersedes {stem}", f"supersedes the {stem}",
                    f"revokes {stem}", f"walks back {stem}"):
            if pat in later_body:
                return True
    return False


def classify_scope(sanctum_path: Path) -> str:
    """core or apparatus based on path mentions in the Sanctum body."""
    body = sanctum_path.read_text()
    core_hits = sum(1 for g in CORE_GLOBS if g in body)
    apparatus_hits = sum(1 for g in APPARATUS_GLOBS if g in body)
    if core_hits > apparatus_hits:
        return "core"
    if apparatus_hits > 0:
        return "apparatus"
    return "core"  # default for ambiguous


def classify_status(sanctum_path: Path, all_sanctums: list[Path]) -> dict:
    is_ref, refs = is_referenced(sanctum_path)
    is_super = detect_superseded(sanctum_path, all_sanctums)
    if is_super:
        status = "SUPERSEDED"
    elif is_ref:
        status = "ACTIVE"
    else:
        status = "DEAD"
    return {
        "status": status,
        "scope": classify_scope(sanctum_path),
        "referenced": is_ref,
        "n_referencers": len(refs),
    }


sanctums = list_sanctums()
classified = {}
for s in sanctums:
    classified[s.name] = classify_status(s, sanctums)

# Counts
counts = {"ACTIVE": 0, "SUPERSEDED": 0, "DEAD": 0}
scope_counts = {"core": 0, "apparatus": 0}
for name, info in classified.items():
    counts[info["status"]] += 1
    if info["status"] == "ACTIVE":
        scope_counts[info["scope"]] += 1

if json_mode:
    print(json.dumps({
        "total_sanctums": len(sanctums),
        "counts": counts,
        "active_scope_counts": scope_counts,
        "core_to_apparatus_ratio": (
            scope_counts["core"] / scope_counts["apparatus"]
            if scope_counts["apparatus"] > 0 else None
        ),
        "by_sanctum": classified,
    }, indent=2))
    sys.exit(0)

print(f"polaris-sanctum-status ({len(sanctums)} total):")
print(f"  ACTIVE:     {counts['ACTIVE']}")
print(f"  SUPERSEDED: {counts['SUPERSEDED']}")
print(f"  DEAD:       {counts['DEAD']}")
print()
print(f"  ACTIVE scope split:")
print(f"    core:      {scope_counts['core']}")
print(f"    apparatus: {scope_counts['apparatus']}")
if scope_counts["apparatus"] > 0:
    ratio = scope_counts["core"] / scope_counts["apparatus"]
    verdict = (
        "CORE-DOMINANT (Sanctums govern Polaris)" if ratio > 1.0
        else "BALANCED" if ratio > 0.5
        else "APPARATUS-DOMINANT (Sanctum governs itself — cut deeper)"
    )
    print(f"    ratio:     {ratio:.2f} — {verdict}")

# Archive moves
if archive_mode:
    print()
    to_move = [n for n, info in classified.items()
               if info["status"] != "ACTIVE"]
    print(f"  → would move {len(to_move)} non-ACTIVE Sanctums to archive/sanctum/")
    if not dry_run and to_move:
        ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
        for name in to_move:
            src = SANCTUM_DIR / name
            dst = ARCHIVE_DIR / name
            if dst.exists():
                print(f"    ⚠ skip {name} (already in archive)")
                continue
            shutil.move(str(src), str(dst))
            print(f"    ✓ moved {name} → archive/sanctum/")
    elif dry_run:
        for name in to_move[:5]:
            print(f"    [dry-run] {name} ({classified[name]['status']})")
        if len(to_move) > 5:
            print(f"    [dry-run] ... and {len(to_move) - 5} more")
PY
