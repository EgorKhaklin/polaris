#!/usr/bin/env bash
# ============================================================================
# ai-swarm-validate.sh — validate swarm against ground-truth fixtures
#
# v9.24 / BIG MISSION Tier 2 #10. Inventories the ground-truth fixtures
# in polaris_swarm/fixtures/ and emits the EXPECTED-firing matrix
# (per-ant expected fire/silent counts across fixtures).
#
# HONEST SCOPE (v9.47 accounting fix): this script does NOT yet run the
# swarm or compute observed precision/recall. The OBSERVED-firing pass
# (run_colony() against each fixture + Pheromone reads -> precision/recall
# -> auto-flag sub-threshold ants for PREDICATE_PENDING) was deferred at
# v9.24 and has not shipped. `observed_*` counts are 0 by construction.
# Treat the output as a fixture catalog + expected-firing matrix, not a
# validation verdict. (Closing this is a ROADMAP candidate; until then the
# header does not claim a computation the body does not perform.)
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

# Per-ant per-fixture: count how many fixtures EXPECT each ant to fire
# vs stay silent. This is the expected-firing matrix only.
#
# Honest accounting (v9.47): observed-firing is NOT computed. The
# observed pass (run_colony() against each fixture + Pheromone reads ->
# precision/recall -> auto-flag) is a heavy, DB-dependent operation that
# was deferred at v9.24 and has not shipped. The `observed_*` fields stay
# 0 by construction; no precision/recall is produced.

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
        "note": "Expected-firing matrix only. Observed-firing / precision-recall is NOT computed (deferred at v9.24, unshipped).",
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
print("  Status: fixture inventory + expected-firing matrix only.")
print("  Observed-firing comparison + precision/recall is NOT computed")
print("  (deferred at v9.24; the run_colony()+Pheromone-read pass has not")
print("  shipped). The fixture catalog is the load-bearing contribution.")
print()
print("  To add fixtures: drop a new file in polaris_swarm/fixtures/")
print("  matching the FIXTURE schema (see polaris_swarm/fixtures/__init__.py).")
PY
