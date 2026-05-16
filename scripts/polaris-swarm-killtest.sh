#!/usr/bin/env bash
# ============================================================================
# polaris-swarm-killtest.sh — run kill test against fault-injected defects
#
# v9.25 / BIG MISSION Tier 5 #2. The swarm's regression test against
# realistic defects. Each defect in polaris_swarm/fault_injection.py is
# applied to the live source tree, the detection channels are run, and
# the runner records:
#
#   - did the defect get caught (yes/no)
#   - which channel caught it first
#   - wall-time to first detection (proxy for "time to detect")
#
# Pass bar (per Sanctum 2026-05-16 Tier 5 §II joint resolution):
#
#   ≥70% defects caught within 1 pass (4/5)
#   ≥90% defects caught within 3 passes (5/5 typically)
#
# Anti-Architect invariants:
#
#   - Defects are reversible (apply returns revert_token; try/finally)
#   - Runner refuses to start a second defect until previous reverted
#   - Wall budget: total run ≤5 min (CI-runnable)
#   - Runs git-clean check first; refuses to start if uncommitted changes
#
# Usage:
#   ./scripts/polaris-swarm-killtest.sh              # full kill test
#   ./scripts/polaris-swarm-killtest.sh --defect NAME   # one defect only
#   ./scripts/polaris-swarm-killtest.sh --list           # list available
#   ./scripts/polaris-swarm-killtest.sh --json           # machine-readable
#   ./scripts/polaris-swarm-killtest.sh --dry-run        # show plan, no edits
#
# Exit codes:
#   0  pass bar met (≥70% in 1 pass)
#   1  pass bar not met
#   2  refused (dirty git tree or argument error)
#   3  defect failed to revert (red flag — abort + alert)
# ============================================================================

set -uo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"
POLARIS_ROOT="$(cd -- "${SCRIPT_DIR}/.." &> /dev/null && pwd)"

LIST=0
JSON=0
DRY_RUN=0
TARGET_DEFECT=""

for arg in "$@"; do
    case "${arg}" in
        --list)    LIST=1 ;;
        --json)    JSON=1 ;;
        --dry-run) DRY_RUN=1 ;;
        --defect)  shift; TARGET_DEFECT="${1:-}" ;;
        --defect=*) TARGET_DEFECT="${arg#*=}" ;;
        --help|-h)
            sed -n '2,38p' "$0" | sed 's/^# \{0,1\}//'
            exit 0
            ;;
    esac
    shift 2>/dev/null || true
done

cd "${POLARIS_ROOT}"

# Refuse to start if git tree is dirty (would conflate operator
# changes with defect injections + risk losing operator work on revert).
# Skipped for --list, --dry-run, --help, and when POLARIS_KILLTEST_ALLOW_DIRTY=1
# (the operator may opt in if they understand the revert is file-content
# based and will restore the original bytes regardless of git state).
SKIP_DIRTY_CHECK=0
[[ "${LIST}" -eq 1 ]] && SKIP_DIRTY_CHECK=1
[[ "${DRY_RUN}" -eq 1 ]] && SKIP_DIRTY_CHECK=1
[[ "${POLARIS_KILLTEST_ALLOW_DIRTY:-0}" = "1" ]] && SKIP_DIRTY_CHECK=1

if [[ "${SKIP_DIRTY_CHECK}" -eq 0 ]]; then
    if command -v git >/dev/null 2>&1 && [[ -d .git ]]; then
        DIRTY=$(git status --porcelain 2>/dev/null | grep -v '^??' | head -5)
        if [[ -n "${DIRTY}" ]]; then
            echo "✗ refusing — git tree has uncommitted CHANGES (not untracked):" >&2
            echo "${DIRTY}" | sed 's/^/    /' >&2
            echo "    commit or stash before running the kill test" >&2
            echo "    (defects mutate source files; dirty tree would lose work on revert)" >&2
            echo "    override: POLARIS_KILLTEST_ALLOW_DIRTY=1" >&2
            exit 2
        fi
    fi
fi

python3 - "${LIST}" "${JSON}" "${DRY_RUN}" "${TARGET_DEFECT}" <<'PY'
import json
import os
import sys
import time
import subprocess
import traceback
from pathlib import Path

list_mode, json_mode, dry_run, target_defect = sys.argv[1:5]
list_mode = list_mode == "1"
json_mode = json_mode == "1"
dry_run = dry_run == "1"

from polaris_swarm.fault_injection import ALL_DEFECTS, list_defects

# --list mode
if list_mode:
    if json_mode:
        print(json.dumps(list_defects(), indent=2))
    else:
        print("polaris-swarm-killtest: available defects:")
        for d in list_defects():
            print(f"  - {d['name']} ({d['shape']}): {d['description'][:60]}...")
    sys.exit(0)

# Filter to target defect if specified
defects = ALL_DEFECTS
if target_defect:
    defects = tuple(d for d in defects if d.name == target_defect)
    if not defects:
        print(f"✗ no defect named '{target_defect}'", file=sys.stderr)
        sys.exit(2)

# Detection-channel runners. Each takes no args and returns
# (caught: bool, channel_name: str, elapsed_ms: float, detail: str).
# Order matters: cheap-fast first; slow-thorough last.

def run_structural_invariants():
    t0 = time.perf_counter()
    proc = subprocess.run(
        ["python3", "-m", "unittest", "polaris_web.test_structural_invariants",
         "-v", "-f"],  # -f = fail-fast
        capture_output=True, timeout=120,
    )
    elapsed_ms = (time.perf_counter() - t0) * 1000
    caught = proc.returncode != 0
    # Extract first failure line
    detail = ""
    if caught:
        for line in proc.stderr.decode().split("\n"):
            if "FAIL:" in line or "ERROR:" in line:
                detail = line.strip()[:120]
                break
    return (caught, "test_structural_invariants", elapsed_ms, detail)


def run_ai_meta():
    t0 = time.perf_counter()
    proc = subprocess.run(
        ["bash", "scripts/ai-meta.sh"],
        capture_output=True, timeout=60,
    )
    elapsed_ms = (time.perf_counter() - t0) * 1000
    # ai-meta.sh reports "LAYER SELF-MONITORING IS HEALTHY" or "META-DRIFT"
    out = proc.stdout.decode()
    caught = "META-DRIFT" in out or proc.returncode != 0
    detail = ""
    if caught:
        for line in out.split("\n"):
            if "drift" in line.lower() or "✗" in line:
                detail = line.strip()[:120]
                break
    return (caught, "ai-meta.sh", elapsed_ms, detail)


def run_ai_coherence():
    t0 = time.perf_counter()
    proc = subprocess.run(
        ["bash", "scripts/ai-coherence.sh"],
        capture_output=True, timeout=60,
    )
    elapsed_ms = (time.perf_counter() - t0) * 1000
    out = proc.stdout.decode()
    # ai-coherence emits "STRUCTURE INTACT" or drift warnings (✗)
    caught = "STRUCTURE INTACT" not in out or proc.returncode != 0
    detail = ""
    if caught:
        for line in out.split("\n"):
            if "✗" in line:
                detail = line.strip()[:120]
                break
    return (caught, "ai-coherence.sh", elapsed_ms, detail)


CHANNELS = (run_structural_invariants, run_ai_meta, run_ai_coherence)


def run_defect(defect, pass_n):
    """Apply defect; run detection channels in order; record first
    catch; revert. Returns dict with results."""
    result = {
        "defect": defect.name,
        "shape": defect.shape,
        "pass_n": pass_n,
        "caught": False,
        "caught_by": None,
        "first_detection_ms": None,
        "channel_runs": [],
        "revert_ok": False,
        "error": None,
    }

    if dry_run:
        result["error"] = "dry-run; not applied"
        result["revert_ok"] = True
        return result

    revert_token = None
    try:
        revert_token = defect.apply()
        for ch_fn in CHANNELS:
            caught, name, elapsed_ms, detail = ch_fn()
            result["channel_runs"].append({
                "channel": name,
                "caught": caught,
                "elapsed_ms": round(elapsed_ms, 1),
                "detail": detail,
            })
            if caught and not result["caught"]:
                result["caught"] = True
                result["caught_by"] = name
                result["first_detection_ms"] = round(elapsed_ms, 1)
                # Don't break: still run remaining channels for full data
    except Exception as e:
        result["error"] = f"defect application/run failed: {e}\n{traceback.format_exc()}"
    finally:
        if revert_token is not None:
            try:
                revert_token.revert_fn()
                result["revert_ok"] = True
            except Exception as e:
                result["revert_ok"] = False
                result["error"] = (result.get("error") or "") + f"\nrevert failed: {e}"
                # CRITICAL: must alert; corrupt state
    return result


# Run the full pass (1 pass = apply each defect once + measure)
print(f"polaris-swarm-killtest: {len(defects)} defect(s); dry_run={dry_run}")
print()

total_start = time.perf_counter()
all_results = []
revert_failures = []

for defect in defects:
    print(f"  → {defect.name} ({defect.shape}): {defect.description[:60]}...")
    r = run_defect(defect, pass_n=1)
    all_results.append(r)
    if not r["revert_ok"] and not dry_run:
        revert_failures.append(r["defect"])
        # ABORT — corrupt state
        print(f"    ✗ REVERT FAILED for {r['defect']}; aborting kill test")
        break
    caught_marker = "✓" if r["caught"] else "✗"
    detection = (f"caught by {r['caught_by']} in {r['first_detection_ms']:.0f}ms"
                 if r["caught"] else "ESCAPED")
    print(f"    {caught_marker} {detection}")
    if r["error"]:
        print(f"      error: {r['error'][:200]}")

total_elapsed_s = time.perf_counter() - total_start

# Pass-bar evaluation
n_total = len(all_results)
n_caught = sum(1 for r in all_results if r["caught"])
catch_rate = n_caught / n_total if n_total > 0 else 0.0

print()
print(f"===== summary =====")
print(f"  defects tested:  {n_total}")
print(f"  caught (pass 1): {n_caught}")
print(f"  catch rate:      {catch_rate * 100:.0f}%")
print(f"  wall time:       {total_elapsed_s:.1f}s")
print(f"  revert failures: {len(revert_failures)}")

# Pass bar from Sanctum
pass_bar_1 = 0.70  # ≥70% within 1 pass
pass_bar_3 = 0.90  # ≥90% within 3 passes (3-pass not implemented v9.25)

if revert_failures:
    print(f"  ✗ REVERT FAILED for: {revert_failures}")
    print(f"    git status to inspect; revert manually before proceeding")
    sys.exit(3)

if catch_rate >= pass_bar_1:
    print(f"  ✓ PASS BAR MET ({catch_rate * 100:.0f}% ≥ {pass_bar_1 * 100:.0f}% in 1 pass)")
    if json_mode:
        print(json.dumps({"summary": {"catch_rate": catch_rate,
                                       "pass_bar_met": True,
                                       "wall_time_s": total_elapsed_s,
                                       "revert_failures": revert_failures},
                          "results": all_results}, indent=2))
    sys.exit(0)
else:
    print(f"  ✗ PASS BAR MISSED ({catch_rate * 100:.0f}% < {pass_bar_1 * 100:.0f}%)")
    print(f"    escaped defects:")
    for r in all_results:
        if not r["caught"]:
            print(f"      - {r['defect']}: no channel caught this defect")
    if json_mode:
        print(json.dumps({"summary": {"catch_rate": catch_rate,
                                       "pass_bar_met": False,
                                       "wall_time_s": total_elapsed_s,
                                       "revert_failures": revert_failures},
                          "results": all_results}, indent=2))
    sys.exit(1)
PY
