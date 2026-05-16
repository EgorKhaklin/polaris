#!/usr/bin/env bash
# ============================================================================
# ai-swarm-validate.sh — validate swarm against ground-truth fixtures
#
# v9.24 / BIG MISSION Tier 2 #10. Runs the swarm against each fixture
# in polaris_swarm/fixtures/, compares fired ants vs expected, reports
# precision + recall per ant.
#
# Sub-threshold ants (precision < 0.5 OR recall < 0.5) get auto-flagged
# for PREDICATE_PENDING in meta/ant-predicates.md (operator review).
#
# Usage:
#     ./scripts/ai-swarm-validate.sh                # full validation pass
#     ./scripts/ai-swarm-validate.sh --fixture NAME # one fixture only
#     ./scripts/ai-swarm-validate.sh --json         # machine-readable
#
# WARNING: fixtures with `setup` SQL modify the database. Run against
# polaris_test (NOT polaris). The script refuses to run if the target
# DB name contains 'prod'.
# ============================================================================

set -uo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"
POLARIS_ROOT="$(cd -- "${SCRIPT_DIR}/.." &> /dev/null && pwd)"

DB_NAME="${POLARIS_DB_NAME:-polaris_test}"
if [[ "${DB_NAME}" =~ prod ]]; then
    echo "✗ refusing — POLARIS_DB_NAME='${DB_NAME}' contains 'prod'" >&2
    exit 2
fi

FIXTURE_FILTER=""
JSON=0
for arg in "$@"; do
    case "${arg}" in
        --fixture) shift; FIXTURE_FILTER="${1:-}" ;;
        --fixture=*) FIXTURE_FILTER="${arg#*=}" ;;
        --json) JSON=1 ;;
        --help|-h)
            sed -n '2,20p' "$0" | sed 's/^# \{0,1\}//'
            exit 0
            ;;
    esac
    shift 2>/dev/null || true
done

cd "${POLARIS_ROOT}"

python3 - "${FIXTURE_FILTER}" "${JSON}" "${DB_NAME}" <<'PY'
import json
import os
import sys
import subprocess
from collections import defaultdict
from pathlib import Path

fixture_filter, json_mode, db_name = sys.argv[1:4]
json_mode = json_mode == "1"

from polaris_swarm.fixtures import ALL_FIXTURES

# Filter
fixtures = ALL_FIXTURES
if fixture_filter:
    fixtures = [f for f in fixtures if f["name"] == fixture_filter]
if not fixtures:
    print(f"✗ no fixture matches '{fixture_filter}'", file=sys.stderr)
    sys.exit(3)

# For each fixture: collect expected firing + silent ants
all_expected_firing = set()
all_expected_silent = set()
for f in fixtures:
    all_expected_firing.update(f.get("expected_firing_ants", []))
    all_expected_silent.update(f.get("expected_silent_ants", []))

# Per-ant per-fixture: True if expected to fire, False otherwise
# Then we observe (by reading recent Pheromone deposits or by stub)
# For v9.24 first ship: STUB the validation — emit the matrix shape +
# placeholder precision/recall. Real validation requires running the
# swarm + reading deposits, which is a heavy + DB-dependent operation
# and warrants its own iteration.
#
# Honest accounting: this script v9.24 ships the FRAMEWORK + fixture
# inventory + matrix-emission. Per-ant observed-firing comes in v9.25
# when the validator integrates with run_colony() + Pheromone reads.

per_ant_stats = defaultdict(lambda: {"expected_fire": 0, "expected_silent": 0,
                                      "observed_fire": 0, "observed_silent": 0})
for f in fixtures:
    for ant in f.get("expected_firing_ants", []):
        per_ant_stats[ant]["expected_fire"] += 1
    for ant in f.get("expected_silent_ants", []):
        per_ant_stats[ant]["expected_silent"] += 1

if json_mode:
    out = {
        "fixtures_count": len(fixtures),
        "fixtures": [{"name": f["name"], "type": f["test_type"]} for f in fixtures],
        "per_ant_expected": {a: s for a, s in per_ant_stats.items()},
        "note": "v9.24 ships framework + fixture inventory. Observed-firing comes in v9.25.",
    }
    print(json.dumps(out, indent=2))
    sys.exit(0)

print(f"ai-swarm-validate: {len(fixtures)} fixture(s)")
for f in fixtures:
    print(f"  - {f['name']} ({f['test_type']}): {f['description'][:60]}...")
print()
print(f"  Expected-firing matrix (per-ant counts across fixtures):")
print(f"  {'ant':<35} fire  silent")
print(f"  {'-'*35} ----  ------")
for ant in sorted(per_ant_stats):
    s = per_ant_stats[ant]
    print(f"  {ant:<35} {s['expected_fire']:>4}  {s['expected_silent']:>6}")
print()
print("  Status: v9.24 ships framework + 3 fixtures + matrix emission.")
print("  Observed-firing comparison + precision/recall computation lands")
print("  in v9.25 when validator runs run_colony() against each fixture")
print("  and reads Pheromone deposits. The fixture catalog is the")
print("  load-bearing contribution of v9.24 T2#10.")
print()
print("  To add fixtures: drop a new file in polaris_swarm/fixtures/")
print("  matching the FIXTURE schema (see polaris_swarm/fixtures/__init__.py).")
PY
