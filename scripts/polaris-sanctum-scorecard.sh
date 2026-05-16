#!/usr/bin/env bash
# ============================================================================
# polaris-sanctum-scorecard.sh — record + report Sanctum-protocol survival
#
# v9.28 / VANTA's addition to the v9.28 mission. Mirrors v9.25's
# swarm-scorecard one layer up: instead of measuring whether the swarm
# catches defects, this measures whether the Sanctum protocol's joint
# resolutions actually load-bear over subsequent ships.
#
# Load-bearing metric (per v9.28 Sanctum §II addition):
#   joint_resolution_survival_rate_trailing_10sanctums —
#   of the last 10 Sanctums, fraction whose joint resolution survived
#   contact with the next 3 ships unmodified (not walked back, not
#   quietly forgotten).
#
# If this rate is low (< 0.5), the Sanctum protocol is decorative —
# same shape the predicate test is auditing watchers for at v9.30.
#
# Anti-Architect constraints (Sanctum 2026-05-16 v9.28):
#   - NO manual classification (auto-derive from CHANGELOG + git mtimes)
#   - retroactive: classify Sanctum vX at vX+3 ship boundary
#   - trend over absolute (10-Sanctum window)
#
# Usage:
#   ./scripts/polaris-sanctum-scorecard.sh append <sanctum-path> <shipped-version>
#   ./scripts/polaris-sanctum-scorecard.sh classify <sanctum-path>
#       Auto-classify SURVIVED / WALKED_BACK / DECORATIVE based on
#       next-3-ships evidence.
#   ./scripts/polaris-sanctum-scorecard.sh report
#   ./scripts/polaris-sanctum-scorecard.sh report --json
# ============================================================================

set -uo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"
POLARIS_ROOT="$(cd -- "${SCRIPT_DIR}/.." &> /dev/null && pwd)"
SCORECARD="${POLARIS_ROOT}/meta/sanctum-scorecard.json"
CHANGELOG="${POLARIS_ROOT}/CHANGELOG.md"
ARCHIVE="${POLARIS_ROOT}/archive/CHANGELOG-FULL.md"

if [[ ! -f "${SCORECARD}" ]]; then
    echo "✗ scorecard not found at ${SCORECARD}" >&2; exit 2
fi

ACTION="${1:-report}"
shift 2>/dev/null || true

case "${ACTION}" in
    --help|-h)
        sed -n '2,32p' "$0" | sed 's/^# \{0,1\}//'
        exit 0
        ;;
esac

python3 - "${ACTION}" "${SCORECARD}" "${CHANGELOG}" "${ARCHIVE}" \
         "${POLARIS_ROOT}" "${1:-}" "${2:-}" <<'PY'
import json
import os
import re
import sys
from pathlib import Path

action, scorecard_path, changelog_path, archive_path, root, arg1, arg2 = sys.argv[1:8]
scorecard_path = Path(scorecard_path)
root = Path(root)

with open(scorecard_path) as f:
    sc = json.load(f)

sanctums = sc.setdefault("sanctums", [])


def find_entry(path: str):
    return next((s for s in sanctums if s.get("sanctum") == path), None)


def auto_classify(sanctum_path: str) -> dict:
    """Auto-classify a Sanctum's survival based on:
    - Was its joint resolution mentioned in any of the next 3 ships'
      CHANGELOG entries? (load_bore)
    - Was any of its commitments walked back (mentioned as 'reverted',
      'walked back', 'superseded') in later CHANGELOG entries?
    - If neither — DECORATIVE (the Sanctum had no observable effect
      on subsequent ships).
    """
    entry = find_entry(sanctum_path)
    if not entry:
        return {"error": f"no entry for {sanctum_path}"}
    shipped_at = entry.get("shipped_at_version")
    if not shipped_at:
        return {"error": "no shipped_at_version recorded"}

    # Read CHANGELOG + archive
    full_changelog = ""
    for p in (changelog_path, archive_path):
        if os.path.isfile(p):
            full_changelog += "\n" + open(p).read()

    # Find next 3 ship versions
    ship_pattern = re.compile(r'^## v(\d+\.\d+)', re.MULTILINE)
    all_versions = sorted(
        set(m.group(1) for m in ship_pattern.finditer(full_changelog)),
        key=lambda v: tuple(int(x) for x in v.split("."))
    )
    try:
        idx = all_versions.index(shipped_at)
    except ValueError:
        return {"status": "PENDING", "note": f"shipped_at v{shipped_at} not yet in CHANGELOG"}
    next_3 = all_versions[idx + 1: idx + 4]
    if len(next_3) < 3:
        return {"status": "PENDING",
                "note": f"only {len(next_3)} ships after v{shipped_at}; need 3 for classification"}

    # Extract sanctum's slug for grep
    sanctum_slug = os.path.basename(sanctum_path).replace(".md", "")

    # Look for references in next 3 ships' CHANGELOG entries
    load_bore_hits = 0
    walked_back_hits = 0
    for v in next_3:
        # Extract this version's CHANGELOG section
        m = re.search(rf'^## v{re.escape(v)}.*?(?=^## v|\Z)',
                      full_changelog, re.MULTILINE | re.DOTALL)
        if not m:
            continue
        section = m.group(0).lower()
        if sanctum_slug.lower() in section:
            load_bore_hits += 1
        if "walked back" in section or "reverted" in section or "superseded" in section:
            # Coarse: any later ship using these words COULD indicate
            # this sanctum was walked back. Operator can override.
            walked_back_hits += 1

    if walked_back_hits > 0:
        status = "WALKED_BACK"
    elif load_bore_hits > 0:
        status = "SURVIVED"
    else:
        status = "DECORATIVE"

    return {
        "status": status,
        "load_bore_hits": load_bore_hits,
        "walked_back_hits": walked_back_hits,
        "classified_against_versions": next_3,
    }


def trailing_survival_rate(window: int = 10):
    classified = [s for s in sanctums if s.get("survival_status") in
                  ("SURVIVED", "WALKED_BACK", "DECORATIVE")]
    window_set = classified[-window:]
    if not window_set:
        return None
    surviving = sum(1 for s in window_set if s["survival_status"] == "SURVIVED")
    return round(surviving / len(window_set), 3)


if action == "append":
    sanctum_path, version = arg1, arg2
    if not sanctum_path or not version:
        print("usage: append <sanctum-path> <version>", file=sys.stderr)
        sys.exit(2)
    if find_entry(sanctum_path):
        print(f"polaris-sanctum-scorecard: already tracked: {sanctum_path}")
        sys.exit(0)
    sanctums.append({
        "sanctum": sanctum_path,
        "shipped_at_version": version,
        "joint_resolution_summary": "(auto-classify at v" + str(version) + "+3)",
        "survival_status": "PENDING",
        "next_3_ships": [],
        "walked_back_evidence": None,
        "load_bore_evidence": None,
        "classified_at_version": None,
        "note": f"auto-appended; classify at next-3-ships boundary",
    })
    with open(scorecard_path, "w") as f:
        json.dump(sc, f, indent=2)
    print(f"polaris-sanctum-scorecard: appended {sanctum_path}")

elif action == "classify":
    sanctum_path = arg1
    if not sanctum_path:
        print("usage: classify <sanctum-path>", file=sys.stderr)
        sys.exit(2)
    result = auto_classify(sanctum_path)
    print(json.dumps(result, indent=2))
    if "status" in result and result["status"] != "PENDING":
        entry = find_entry(sanctum_path)
        if entry:
            entry["survival_status"] = result["status"]
            entry["next_3_ships"] = result.get("classified_against_versions", [])
            entry["load_bore_evidence"] = (
                f"{result.get('load_bore_hits', 0)} later ships reference this sanctum"
            )
            entry["walked_back_evidence"] = (
                f"{result.get('walked_back_hits', 0)} later ships use 'walked back / reverted / superseded'"
                if result.get("walked_back_hits", 0) > 0 else None
            )
            with open(scorecard_path, "w") as f:
                json.dump(sc, f, indent=2)
            print(f"\nupdated {sanctum_path} → {result['status']}")

elif action == "report":
    json_mode = arg1 == "--json"
    if json_mode:
        print(json.dumps(sc, indent=2))
        sys.exit(0)
    print(f"polaris-sanctum-scorecard ({len(sanctums)} tracked):")
    print(f"  {'sanctum':<50} {'shipped':>8} {'status':>14}")
    print(f"  {'-'*50:<50} {'-'*8:>8} {'-'*14:>14}")
    for s in sanctums:
        name = os.path.basename(s.get("sanctum", "?")).replace(".md", "")[:48]
        v = s.get("shipped_at_version", "?")
        status = s.get("survival_status", "?")
        print(f"  {name:<50} v{v:>7} {status:>14}")
    print()
    rate = trailing_survival_rate()
    if rate is None:
        print(f"  load-bearing metric: survival_rate not yet computable "
              f"(need ≥1 classified entry; v9.28 baseline)")
    else:
        verdict = (
            "PROTOCOL EARNING (≥80% survival)" if rate >= 0.8
            else "PROTOCOL MARGINAL (50%-80%)" if rate >= 0.5
            else "PROTOCOL DECORATIVE (<50%) — cut deeper"
        )
        print(f"  load-bearing: survival_rate_trailing_10sanctums = "
              f"{rate:.3f} — {verdict}")

else:
    print(f"unknown action: {action}", file=sys.stderr); sys.exit(2)
PY
