#!/usr/bin/env bash
# ============================================================================
# polaris-swarm-scorecard.sh — record + report swarm performance per ship
#
# v9.25 / BIG MISSION Tier 5 #1. Appends a per-ship scorecard entry to
# meta/swarm-scorecard.json. Each entry captures:
#
#   - findings_raised   — count of distinct (ant, node_id) emissions
#                         during the ship cycle (from journal/hydra/)
#   - true_positives    — findings that map to a CHANGELOG fix in the
#                         same or subsequent ship (auto-derived)
#   - false_positives   — findings not mapped to any fix (auto-derived)
#   - escaped_defects   — defects mentioned in CHANGELOG as "fix from
#                         vY.X" that no ant raised in vY.X's cycle
#                         (retroactive; back-fills vY.X's entry)
#
# Load-bearing metric (per Sanctum 2026-05-16 Tier 5):
#   escape_rate_trailing_10ships — escaped_defects / total_defects across
#   the last 10 ship entries. Single number that says whether the swarm
#   is worth maintaining.
#
# Usage:
#   ./scripts/polaris-swarm-scorecard.sh append <version> [shipped_at_utc]
#   ./scripts/polaris-swarm-scorecard.sh report             # human-readable
#   ./scripts/polaris-swarm-scorecard.sh report --json
#   ./scripts/polaris-swarm-scorecard.sh backfill-escape <vY.X>
#       Back-fills vY.X's escape count from later CHANGELOG entries
#       that say "fix from vY.X" or similar.
#
# Anti-Architect constraints (Sanctum 2026-05-16 §II T5#1):
#   - NO manual classification (auto-derive from CHANGELOG)
#   - NO self-reported escapes (back-fill from later ships)
#   - Trend over absolute counts (10-ship rolling window)
# ============================================================================

set -uo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"
POLARIS_ROOT="$(cd -- "${SCRIPT_DIR}/.." &> /dev/null && pwd)"
SCORECARD="${POLARIS_ROOT}/meta/swarm-scorecard.json"
CHANGELOG="${POLARIS_ROOT}/CHANGELOG.md"
ARCHIVE="${POLARIS_ROOT}/archive/CHANGELOG-FULL.md"
JOURNAL_HYDRA="${POLARIS_ROOT}/journal/hydra"

ACTION="${1:-report}"
shift 2>/dev/null || true

if [[ ! -f "${SCORECARD}" ]]; then
    echo "✗ scorecard not found at ${SCORECARD}" >&2
    echo "  (it should ship with v9.25; recreate with /tmp template)" >&2
    exit 2
fi

case "${ACTION}" in
    append)
        VERSION="${1:-}"
        SHIPPED_AT="${2:-$(date -u +%Y-%m-%dT%H:%M:%SZ)}"
        if [[ -z "${VERSION}" ]]; then
            echo "usage: $(basename "$0") append <version> [shipped_at_utc]" >&2
            exit 2
        fi
        ;;
    report|backfill-escape|--help|-h)
        ;;
    *)
        echo "unknown action: ${ACTION}" >&2
        sed -n '2,32p' "$0" | sed 's/^# \{0,1\}//'
        exit 2
        ;;
esac

if [[ "${ACTION}" = "--help" || "${ACTION}" = "-h" ]]; then
    sed -n '2,32p' "$0" | sed 's/^# \{0,1\}//'
    exit 0
fi

python3 - "${ACTION}" "${SCORECARD}" "${CHANGELOG}" "${ARCHIVE}" \
         "${JOURNAL_HYDRA}" "${1:-}" "${2:-}" <<'PY'
import json
import sys
import re
import os
from pathlib import Path
from datetime import datetime, timezone

action, scorecard_path, changelog_path, archive_path, journal_hydra, arg1, arg2 = sys.argv[1:8]
scorecard_path = Path(scorecard_path)

with open(scorecard_path) as f:
    sc = json.load(f)


def count_findings_in_briefs(since_iso=None):
    """Count distinct (ant, node_id) emissions across journal/hydra/ briefs
    since `since_iso`. Returns int."""
    jhdir = Path(journal_hydra)
    if not jhdir.is_dir():
        return 0
    findings = set()
    for brief in sorted(jhdir.glob("*.md")):
        # Extract ant + node_id from finding lines like
        # "  [ALERT] cognitive: Sanctum index drift" or similar
        with open(brief) as f:
            txt = f.read()
        # Crude pattern: [LEVEL] ant_or_legion: title
        for m in re.finditer(r'\[(ALERT|DRIFT|INFO)\]\s+(\S+):\s+(.+)', txt):
            findings.add((m.group(2), m.group(3)[:60]))
    return len(findings)


def find_back_references_in_changelog(version):
    """Search CHANGELOG + archive for entries that say
    'fix from v9.X' or 'introduced in v9.X' or similar — these are
    escaped defects from vX. Returns count.
    """
    count = 0
    sources = []
    for p in (changelog_path, archive_path):
        if os.path.isfile(p):
            with open(p) as f:
                sources.append(f.read())
    haystack = "\n".join(sources)
    # Patterns indicating a back-reference fix
    patterns = [
        rf'fix.*from\s+v{re.escape(version)}\b',
        rf'introduced.*in\s+v{re.escape(version)}\b',
        rf'regression.*from\s+v{re.escape(version)}\b',
        rf'bug.*latent.*since\s+v{re.escape(version)}\b',
    ]
    for pat in patterns:
        count += len(re.findall(pat, haystack, re.IGNORECASE))
    return count


def compute_escape_rate(entries, window=10):
    """Trailing-window escape rate. Skips entries with null counts."""
    valid = [
        e for e in entries
        if e.get("escaped_defects") is not None
        and e.get("true_positives") is not None
    ]
    window_entries = valid[-window:]
    total_escaped = sum(e["escaped_defects"] for e in window_entries)
    total_caught = sum(e["true_positives"] for e in window_entries)
    total_defects = total_escaped + total_caught
    if total_defects == 0:
        return None
    return round(total_escaped / total_defects, 3)


if action == "append":
    version = arg1
    shipped_at = arg2 or datetime.now(timezone.utc).isoformat(timespec="seconds") + "Z"

    # Auto-derive findings_raised from current journal/hydra/ briefs
    findings_raised = count_findings_in_briefs()

    # Auto-classify: TP if any finding maps to a CHANGELOG line in this
    # ship's entry. Heuristic: count distinct keywords from CHANGELOG
    # ship section that overlap with finding titles.
    # First-pass simple: TP = min(findings_raised, fixes_in_changelog)
    # FP = findings_raised - TP
    fixes_in_ship = 0
    if os.path.isfile(changelog_path):
        with open(changelog_path) as f:
            cl = f.read()
        if f"## v{version}" in cl:
            section = cl[cl.index(f"## v{version}"):]
            next_ver_idx = section.find("\n## v", 1)
            if next_ver_idx > 0:
                section = section[:next_ver_idx]
            # Count "fix" / "fixed" / "resolves" mentions
            fixes_in_ship = (
                len(re.findall(r'\bfix(?:ed|es)?\b', section, re.IGNORECASE))
                + len(re.findall(r'\bresolv(?:ed|es)\b', section, re.IGNORECASE))
            )

    true_positives = min(findings_raised, fixes_in_ship)
    false_positives = max(0, findings_raised - true_positives)
    escaped_defects = 0  # filled in retroactively when v9.X+N ships back-ref

    entries = sc.setdefault("entries", [])

    # Drop any pre-existing entry for this version (re-append idempotent)
    entries = [e for e in entries if e.get("version") != version]

    new_entry = {
        "version": version,
        "shipped_at_utc": shipped_at,
        "findings_raised": findings_raised,
        "true_positives": true_positives,
        "false_positives": false_positives,
        "escaped_defects": escaped_defects,
        "escape_rate_trailing_10ships": None,
        "note": "auto-classified from CHANGELOG + journal/hydra/",
    }
    entries.append(new_entry)
    entries.sort(key=lambda e: e.get("version", ""))

    # Compute escape rate for the latest window
    new_entry["escape_rate_trailing_10ships"] = compute_escape_rate(entries)

    sc["entries"] = entries

    with open(scorecard_path, "w") as f:
        json.dump(sc, f, indent=2)

    print(f"polaris-swarm-scorecard: appended v{version}")
    print(f"  findings_raised: {findings_raised}")
    print(f"  true_positives:  {true_positives}")
    print(f"  false_positives: {false_positives}")
    print(f"  escape_rate_trailing_10ships: "
          f"{new_entry['escape_rate_trailing_10ships']}")

elif action == "backfill-escape":
    target_version = arg1
    if not target_version:
        print("usage: backfill-escape <vY.X>", file=sys.stderr)
        sys.exit(2)
    back_refs = find_back_references_in_changelog(target_version)
    entries = sc.get("entries", [])
    target = next((e for e in entries if e.get("version") == target_version), None)
    if target is None:
        print(f"✗ no entry for v{target_version}", file=sys.stderr)
        sys.exit(3)
    target["escaped_defects"] = back_refs
    # Recompute escape rate for ALL entries (rolling)
    for i, e in enumerate(entries):
        window_entries = entries[:i + 1]
        e["escape_rate_trailing_10ships"] = compute_escape_rate(window_entries)
    sc["entries"] = entries
    with open(scorecard_path, "w") as f:
        json.dump(sc, f, indent=2)
    print(f"polaris-swarm-scorecard: back-filled v{target_version}")
    print(f"  escaped_defects: {back_refs}")
    print(f"  escape_rate_trailing_10ships: {target['escape_rate_trailing_10ships']}")

elif action == "report":
    json_mode = arg1 == "--json"
    entries = sc.get("entries", [])
    if json_mode:
        print(json.dumps(sc, indent=2))
        sys.exit(0)

    print(f"polaris-swarm-scorecard ({len(entries)} entries):")
    print(f"  {'version':<10} {'raised':>6} {'TP':>4} {'FP':>4} {'esc':>4} {'esc_rate':>8}")
    print(f"  {'-'*10:<10} {'-'*6:>6} {'-'*4:>4} {'-'*4:>4} {'-'*4:>4} {'-'*8:>8}")
    for e in entries:
        v = e.get("version", "?")
        r = e.get("findings_raised")
        tp = e.get("true_positives")
        fp = e.get("false_positives")
        esc = e.get("escaped_defects")
        rate = e.get("escape_rate_trailing_10ships")
        r_s = str(r) if r is not None else "-"
        tp_s = str(tp) if tp is not None else "-"
        fp_s = str(fp) if fp is not None else "-"
        esc_s = str(esc) if esc is not None else "-"
        rate_s = f"{rate:.3f}" if rate is not None else "-"
        print(f"  {v:<10} {r_s:>6} {tp_s:>4} {fp_s:>4} {esc_s:>4} {rate_s:>8}")

    # Load-bearing summary
    print()
    latest = entries[-1] if entries else None
    if latest and latest.get("escape_rate_trailing_10ships") is not None:
        r = latest["escape_rate_trailing_10ships"]
        if r < 0.05:
            verdict = "EARNING (escape_rate < 5%)"
        elif r < 0.15:
            verdict = "EARNING (escape_rate < 15%)"
        elif r < 0.30:
            verdict = "MARGINAL (escape_rate < 30%; trend matters)"
        else:
            verdict = "NOT EARNING (escape_rate ≥ 30%; cut-deeper triggered)"
        print(f"  load-bearing: escape_rate_trailing_10ships = {r:.3f} — {verdict}")
    else:
        print(f"  load-bearing: escape_rate not yet computable "
              f"(needs ≥1 entry with real TP/escape counts; v9.25 is baseline)")

PY
