#!/usr/bin/env bash
# ============================================================================
# polaris-swarm-mttr.sh — MTTR ledger + trend
#
# v9.25 / BIG MISSION Tier 5 #3. Records timestamps for each finding as
# it's raised (by HYDRA or kill test) and as it's resolved (by a fix
# shipped to the same ant's node_id). The trend chart shows whether
# the closed loop is reducing time-to-resolve.
#
# **Honest baseline (Anti-Architect joint resolution Sanctum 2026-05-16
# §II T5#3):** there is NO pre-v9.24 baseline. Findings were advisory
# pre-v9.24; no timestamps exist. Measurement starts at v9.25.
# Meaningful trend emerges at v9.30 (5 ships from v9.25). At v9.30,
# the v9.30 binding clause fires: if mttr_trend_slope is not negative,
# the agent opens a cognitive-layer-deletion Sanctum.
#
# Usage:
#   ./scripts/polaris-swarm-mttr.sh raise <finding_id> <ant> <node_id>
#   ./scripts/polaris-swarm-mttr.sh resolve <finding_id> [<commit_sha>]
#   ./scripts/polaris-swarm-mttr.sh import-from-briefs
#       Scans journal/hydra/ and ingests findings emitted there.
#   ./scripts/polaris-swarm-mttr.sh trend           # human-readable
#   ./scripts/polaris-swarm-mttr.sh trend --json    # machine-readable
#   ./scripts/polaris-swarm-mttr.sh check-v9-30      # v9.30 binding clause check
# ============================================================================

set -uo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"
POLARIS_ROOT="$(cd -- "${SCRIPT_DIR}/.." &> /dev/null && pwd)"
LEDGER="${POLARIS_ROOT}/meta/swarm-mttr.json"
JOURNAL_HYDRA="${POLARIS_ROOT}/journal/hydra"
VERSION_FILE="${POLARIS_ROOT}/polaris_web/__version__.py"

if [[ ! -f "${LEDGER}" ]]; then
    echo "✗ ledger not found at ${LEDGER}" >&2; exit 2
fi

ACTION="${1:-trend}"
shift 2>/dev/null || true

case "${ACTION}" in
    --help|-h)
        sed -n '2,28p' "$0" | sed 's/^# \{0,1\}//'
        exit 0
        ;;
esac

python3 - "${ACTION}" "${LEDGER}" "${JOURNAL_HYDRA}" "${VERSION_FILE}" \
         "${1:-}" "${2:-}" "${3:-}" "${4:-}" <<'PY'
import json
import re
import sys
import hashlib
from pathlib import Path
from datetime import datetime, timezone

action, ledger_path, journal_hydra, version_file, arg1, arg2, arg3, arg4 = sys.argv[1:9]
ledger_path = Path(ledger_path)

with open(ledger_path) as f:
    ledger = json.load(f)

findings = ledger.setdefault("findings", [])

# Current version
current_version = "unknown"
try:
    vf = Path(version_file).read_text()
    m = re.search(r'POLARIS_VERSION[:\s=]+["\']([^"\']+)["\']', vf)
    if m:
        current_version = m.group(1)
except Exception:
    pass


def now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds") + "Z"


def find_by_id(fid):
    for f in findings:
        if f.get("finding_id") == fid:
            return f
    return None


def stable_finding_id(ant, node_id, raised_version):
    h = hashlib.sha256(f"{ant}|{node_id}|{raised_version}".encode()).hexdigest()
    return f"FND-{h[:10].upper()}"


def compute_per_version_mttr():
    """Returns dict: version -> {n_resolved, mean_hours, median_hours}."""
    from statistics import median
    out = {}
    for f in findings:
        if not f.get("resolved_at_utc"):
            continue
        try:
            raised = datetime.fromisoformat(f["raised_at_utc"].replace("Z", "+00:00"))
            resolved = datetime.fromisoformat(f["resolved_at_utc"].replace("Z", "+00:00"))
        except (KeyError, ValueError):
            continue
        hours = (resolved - raised).total_seconds() / 3600.0
        v = f.get("raised_at_version", "unknown")
        out.setdefault(v, []).append(hours)
    summary = {}
    for v, hrs in out.items():
        summary[v] = {
            "n_resolved": len(hrs),
            "mean_hours": round(sum(hrs) / len(hrs), 2),
            "median_hours": round(median(hrs), 2),
        }
    return summary


def trend_slope(per_version):
    """Naive slope: (mean_at_latest - mean_at_first) / (n_versions).
    Negative = MTTR decreasing (the loop is earning).
    Positive = MTTR increasing (loop is decorative; v9.30 cut-deeper).
    """
    versions = sorted(per_version.keys())
    if len(versions) < 2:
        return None
    means = [per_version[v]["mean_hours"] for v in versions]
    return round((means[-1] - means[0]) / (len(versions) - 1), 3)


if action == "raise":
    ant, node_id = arg1, arg2
    raised_version = arg3 or current_version
    if not ant or not node_id:
        print("usage: raise <ant> <node_id> [raised_version]", file=sys.stderr)
        sys.exit(2)
    fid = stable_finding_id(ant, node_id, raised_version)
    existing = find_by_id(fid)
    if existing:
        print(f"polaris-swarm-mttr: already raised {fid} "
              f"at {existing.get('raised_at_utc')}")
        sys.exit(0)
    new_finding = {
        "finding_id": fid,
        "ant": ant,
        "node_id": node_id,
        "raised_at_utc": now_iso(),
        "raised_at_version": raised_version,
        "resolved_at_utc": None,
        "resolved_at_version": None,
        "resolved_commit_sha": None,
    }
    findings.append(new_finding)
    with open(ledger_path, "w") as f:
        json.dump(ledger, f, indent=2)
    print(f"polaris-swarm-mttr: raised {fid} ({ant} on {node_id})")

elif action == "resolve":
    fid = arg1
    commit_sha = arg2 or ""
    if not fid:
        print("usage: resolve <finding_id> [commit_sha]", file=sys.stderr)
        sys.exit(2)
    f_obj = find_by_id(fid)
    if not f_obj:
        print(f"✗ no finding {fid}", file=sys.stderr); sys.exit(3)
    if f_obj.get("resolved_at_utc"):
        print(f"polaris-swarm-mttr: {fid} already resolved at "
              f"{f_obj['resolved_at_utc']}")
        sys.exit(0)
    f_obj["resolved_at_utc"] = now_iso()
    f_obj["resolved_at_version"] = current_version
    f_obj["resolved_commit_sha"] = commit_sha
    with open(ledger_path, "w") as f:
        json.dump(ledger, f, indent=2)
    raised = datetime.fromisoformat(f_obj["raised_at_utc"].replace("Z", "+00:00"))
    hours = (datetime.now(timezone.utc) - raised).total_seconds() / 3600.0
    print(f"polaris-swarm-mttr: resolved {fid} ({f_obj['ant']} on "
          f"{f_obj['node_id']}); MTTR = {hours:.1f}h")

elif action == "import-from-briefs":
    """Scan journal/hydra/ for [ALERT] / [DRIFT] findings + raise any
    not already in the ledger. Each entry tagged with the brief filename
    as raised_at_version (mtime fallback)."""
    jhdir = Path(journal_hydra)
    if not jhdir.is_dir():
        print(f"no briefs at {jhdir}", file=sys.stderr)
        sys.exit(0)
    new_count = 0
    for brief in sorted(jhdir.glob("*.md")):
        txt = brief.read_text()
        for m in re.finditer(r'\[(?:ALERT|DRIFT)\]\s+(\S+):\s+(.+)', txt):
            ant = m.group(1)
            node_id = m.group(2)[:60]
            # raised version = brief filename date (proxy for "what
            # version was current when emitted")
            raised_version = brief.stem  # e.g. "2026-05-15-0137"
            fid = stable_finding_id(ant, node_id, raised_version)
            if find_by_id(fid):
                continue
            # Use brief's mtime as raised_at (better than now())
            mtime_iso = datetime.fromtimestamp(
                brief.stat().st_mtime, tz=timezone.utc
            ).isoformat(timespec="seconds") + "Z"
            findings.append({
                "finding_id": fid,
                "ant": ant,
                "node_id": node_id,
                "raised_at_utc": mtime_iso,
                "raised_at_version": raised_version,
                "resolved_at_utc": None,
                "resolved_at_version": None,
                "resolved_commit_sha": None,
                "imported_from": str(brief.relative_to(jhdir.parent.parent)),
            })
            new_count += 1
    with open(ledger_path, "w") as f:
        json.dump(ledger, f, indent=2)
    print(f"polaris-swarm-mttr: imported {new_count} new findings from briefs")

elif action == "trend":
    json_mode = arg1 == "--json"
    n_total = len(findings)
    n_resolved = sum(1 for f in findings if f.get("resolved_at_utc"))
    n_open = n_total - n_resolved
    per_version = compute_per_version_mttr()
    slope = trend_slope(per_version)

    if json_mode:
        print(json.dumps({
            "total_findings": n_total,
            "resolved": n_resolved,
            "open": n_open,
            "per_version_mttr": per_version,
            "trend_slope_hours_per_version": slope,
            "current_version": current_version,
            "measurement_start": ledger.get("measurement_start"),
            "v9_30_binding_clause": ledger.get("v9_30_binding_clause"),
        }, indent=2))
        sys.exit(0)

    print(f"polaris-swarm-mttr trend ({n_total} findings; {n_resolved} resolved, {n_open} open):")
    print()
    if not per_version:
        print(f"  no resolved findings yet — measurement starts at v9.25.")
        print(f"  meaningful trend emerges at v9.30 (per Sanctum 2026-05-16 §VI).")
        sys.exit(0)
    print(f"  {'version':<12} {'n_resolved':>11} {'mean_h':>8} {'median_h':>10}")
    print(f"  {'-'*12:<12} {'-'*11:>11} {'-'*8:>8} {'-'*10:>10}")
    for v in sorted(per_version):
        s = per_version[v]
        print(f"  {v:<12} {s['n_resolved']:>11} {s['mean_hours']:>8.2f} {s['median_hours']:>10.2f}")
    print()
    if slope is not None:
        if slope < 0:
            verdict = f"EARNING (slope {slope}h/ship; MTTR decreasing)"
        elif slope == 0:
            verdict = f"FLAT (slope 0; loop neither earning nor decaying)"
        else:
            verdict = (f"NOT EARNING (slope +{slope}h/ship; loop is "
                       f"decorative; v9.30 cut-deeper triggered if held)")
        print(f"  trend slope: {verdict}")
    else:
        print(f"  trend slope: not computable (need ≥2 versions with resolved findings)")

elif action == "check-v9-30":
    """v9.30 binding clause check. If we're at v9.30 (or later) AND
    the trend slope is not negative, emit the cut-deeper trigger."""
    cur_major, cur_minor = (int(x) for x in current_version.split("."))
    if (cur_major, cur_minor) < (9, 30):
        print(f"polaris-swarm-mttr: v9.30 check not yet due (current v{current_version})")
        sys.exit(0)
    per_version = compute_per_version_mttr()
    slope = trend_slope(per_version)
    if slope is None:
        print(f"✗ v9.30 due but slope not computable; check ledger")
        sys.exit(1)
    if slope < 0:
        print(f"✓ v9.30 binding clause: slope {slope}h/ship is negative; loop earning")
        sys.exit(0)
    print(f"✗ v9.30 binding clause TRIGGERED: slope {slope}h/ship is not negative")
    print(f"  Per Sanctum 2026-05-16 §VI, the agent is bound to open")
    print(f"  sanctum/<date>-cognitive-layer-deletion.md proposing deletion of")
    print(f"  cognitive-layer primitives that aren't contributing to MTTR reduction.")
    sys.exit(2)

else:
    print(f"unknown action: {action}", file=sys.stderr)
    sys.exit(2)
PY
