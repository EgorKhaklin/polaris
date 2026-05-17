#!/bin/bash
# =============================================================================
# scripts/ai-watcher-coverage.sh — HYDRA watcher coverage report (v9.14)
#
# For each of HYDRA's 9 mortal watchers, reports WHAT it actually reads.
# Surfaces blind spots: files/tables/routes that no watcher monitors.
#
# Each watcher's actual reads are detected by static analysis of its
# Python source: imports, SQL query strings, file path references,
# subprocess calls to other ai-* scripts, Pheromone node_id reads.
#
# Output sections:
#   I.   Per-watcher: files read, SQL touched, scripts invoked,
#        Pheromone surfaces consumed
#   II.  Coverage by Layer: which Layer-1 files have ≥1 watcher reading?
#   III. Blind spots: surfaces NO watcher reads
#   IV.  Overlap: surfaces read by ≥2 watchers (potential for
#        correlation; runtime:health + runtime:swarm already shared)
#
# Pure local-file analysis; no DB required.
#
# Usage:
#     scripts/ai-watcher-coverage.sh           # full report
#     scripts/ai-watcher-coverage.sh --watcher security_watcher
#                                              # focus on one watcher
#     scripts/ai-watcher-coverage.sh --json    # JSON output
# =============================================================================
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"

if [ -t 1 ]; then
    BOLD="\033[1m"; G="\033[0;32m"; Y="\033[0;33m"; R="\033[0;31m"
    DIM="\033[2m"; CYAN="\033[0;36m"; GOLD="\033[38;5;220m"
    PURPLE="\033[0;35m"; NC="\033[0m"
else
    BOLD=""; G=""; Y=""; R=""; DIM=""; CYAN=""; GOLD=""; PURPLE=""; NC=""
fi

PY=""
for cand in \
    "$ROOT/polaris_web/venv/bin/python" \
    "$(command -v python3)"; do
    if [ -n "$cand" ] && [ -x "$cand" ]; then
        PY="$cand"
        break
    fi
done
[ -z "$PY" ] && { echo "ai-watcher-coverage: no python3" >&2; exit 1; }

WATCHER_FILTER=""
JSON=0
for arg in "$@"; do
    case "$arg" in
        --watcher)
            shift
            WATCHER_FILTER="$1"
            shift
            ;;
        --json) JSON=1 ;;
        --help|-h)
            sed -n '2,25p' "$0" | sed 's/^# \?//'
            exit 0
            ;;
    esac
done

# Delegate the heavy lifting to a Python helper that does the static
# analysis (regex over source files; clean separation from the bash
# rendering layer).
WATCHER_FILTER="$WATCHER_FILTER" JSON_OUT="$JSON" \
    BOLD="$BOLD" G="$G" Y="$Y" R="$R" DIM="$DIM" \
    CYAN="$CYAN" GOLD="$GOLD" PURPLE="$PURPLE" NC="$NC" \
    "$PY" - <<'PYEOF'
import json
import os
import pathlib
import re
import sys

ROOT = pathlib.Path("/Users/vanta/Desktop/polaris")
WATCHER_DIR = ROOT / "polaris_hydra" / "watchers"
ONE_FILTER = os.environ.get("WATCHER_FILTER", "").strip()
JSON_OUT = os.environ.get("JSON_OUT") == "1"

BOLD = os.environ.get("BOLD", "")
G = os.environ.get("G", "")
Y = os.environ.get("Y", "")
R = os.environ.get("R", "")
DIM = os.environ.get("DIM", "")
CYAN = os.environ.get("CYAN", "")
GOLD = os.environ.get("GOLD", "")
PURPLE = os.environ.get("PURPLE", "")
NC = os.environ.get("NC", "")


def analyze_watcher(path: pathlib.Path) -> dict:
    """Return a coverage profile for a single watcher source file."""
    src = path.read_text(errors="replace")
    name = path.stem  # e.g. "security_watcher"

    # SQL table references: look for table names from polaris_sql schema
    # in any string literal (heuristic; catches FROM/JOIN/UPDATE clauses)
    sql_tables = set()
    for m in re.finditer(
        r'(?:FROM|JOIN|UPDATE|INTO)\s+(\w+)',
        src, re.IGNORECASE,
    ):
        sql_tables.add(m.group(1).lower())

    # File/path references (e.g., reads polaris_web/app.py)
    file_refs = set()
    for m in re.finditer(
        r'["\']((?:polaris_[a-z]+|scripts|meta|sanctum|journal|DEVNOTES|docs)/[^"\']+)["\']',
        src,
    ):
        file_refs.add(m.group(1))

    # Pheromone node_id reads (e.g., looks for "runtime:health", "swarm:cohort")
    node_ids = set()
    for m in re.finditer(
        r'["\']([a-z_]+:[a-z_:][a-z_:0-9]*)["\']',
        src,
    ):
        nid = m.group(1)
        # Exclude obvious false positives (file extensions, version refs)
        if ":" in nid and len(nid) < 80 and not nid.startswith(("http", "https")):
            node_ids.add(nid)

    # Subprocess invocations of ai-* scripts
    invoked = set()
    for m in re.finditer(r'["\']?(ai-[\w-]+\.sh)["\']?', src):
        invoked.add(m.group(1))

    # Imports
    imports = set()
    for m in re.finditer(r'^(?:from|import)\s+(\S+)', src, re.MULTILINE):
        imports.add(m.group(1))

    return {
        "name": name,
        "path": str(path.relative_to(ROOT)),
        "lines": len(src.splitlines()),
        "sql_tables": sorted(sql_tables),
        "file_refs": sorted(file_refs),
        "node_ids": sorted(node_ids),
        "scripts_invoked": sorted(invoked),
        "imports": sorted(imports),
    }


def main() -> int:
    watcher_files = sorted(WATCHER_DIR.glob("*_watcher.py"))
    if not watcher_files:
        print(f"{R}No watcher files found at {WATCHER_DIR}{NC}", file=sys.stderr)
        return 1

    profiles = []
    for f in watcher_files:
        if f.stem == "base":
            continue
        if ONE_FILTER and ONE_FILTER not in f.stem:
            continue
        profiles.append(analyze_watcher(f))

    if JSON_OUT:
        print(json.dumps({"watchers": profiles}, indent=2))
        return 0

    print(f"{BOLD}{GOLD}═══ HYDRA WATCHER COVERAGE REPORT ═══{NC}")
    print(f"{DIM}9 mortal watchers; coverage = files + SQL + node_ids they read{NC}")
    print()

    # §I: Per-watcher
    print(f"{PURPLE}§I. Per-watcher coverage{NC}")
    for p in profiles:
        print(f"  {BOLD}{p['name']}{NC} {DIM}({p['lines']} lines){NC}")
        if p["sql_tables"]:
            print(f"    SQL tables ({len(p['sql_tables'])}): "
                  f"{CYAN}{', '.join(p['sql_tables'][:8])}{NC}"
                  f"{' ...' if len(p['sql_tables']) > 8 else ''}")
        if p["file_refs"]:
            print(f"    File refs ({len(p['file_refs'])}): "
                  f"{CYAN}{', '.join(p['file_refs'][:6])}{NC}"
                  f"{' ...' if len(p['file_refs']) > 6 else ''}")
        if p["node_ids"]:
            print(f"    Node IDs ({len(p['node_ids'])}): "
                  f"{CYAN}{', '.join(p['node_ids'][:8])}{NC}"
                  f"{' ...' if len(p['node_ids']) > 8 else ''}")
        if p["scripts_invoked"]:
            print(f"    Scripts invoked: {CYAN}{', '.join(p['scripts_invoked'])}{NC}")
        print()

    # §II: Layer-1 coverage
    print(f"{PURPLE}§II. Layer-1 file coverage{NC}")
    # Aggregate which polaris_web/sql/zk/cli files have watcher coverage
    all_refs = set()
    for p in profiles:
        all_refs.update(p["file_refs"])
    l1_covered = sorted(
        f for f in all_refs
        if f.startswith(("polaris_web/", "polaris_sql/",
                          "polaris_zk/", "polaris_cli/"))
    )
    if l1_covered:
        for f in l1_covered[:20]:
            print(f"  {G}✓{NC} {f}")
        if len(l1_covered) > 20:
            print(f"  {DIM}... and {len(l1_covered) - 20} more{NC}")
    else:
        print(f"  {Y}No Layer-1 files explicitly referenced by any watcher.{NC}")
        print(f"  {DIM}(Watchers may still observe Layer-1 indirectly via SQL or API.)"
              f"{NC}")
    print()

    # §III: Blind spots
    # v9.25 (sanctum/2026-05-17-watcher-coverage-completion.md Position
    # C+B-trigger): tables without a direct watcher are not all "blind
    # spots." A table may carry a coverage-exempt marker recorded as a
    # structured SQL comment immediately above its CREATE TABLE line.
    # The marker form is:
    #     -- coverage:exempt — <rationale text>
    # Parsed-non-empty rationales are reported as POSITIVE coverage
    # ("exempt with rationale"). Tables without watcher AND without
    # marker are the true blind spots.
    print(f"{PURPLE}§III. Coverage blind spots{NC}")
    all_sql = set()
    for p in profiles:
        all_sql.update(p["sql_tables"])
    schema_src = (ROOT / "polaris_sql" / "01_schema.sql").read_text(errors="replace")
    # Strip SQL line-comments before extracting CREATE TABLE — a comment
    # containing "CREATE TABLE so that" otherwise yields a spurious "so".
    stripped_lines = []
    for line in schema_src.splitlines():
        idx = line.find("--")
        if idx >= 0:
            stripped_lines.append(line[:idx])
        else:
            stripped_lines.append(line)
    stripped = "\n".join(stripped_lines)
    known_tables = set()
    for m in re.finditer(
        r"CREATE TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(\w+)",
        stripped, re.IGNORECASE,
    ):
        name = m.group(1).lower()
        if name not in ("if",):  # defensive: skip IF (shouldn't reach here)
            known_tables.add(name)

    # Parse coverage-exempt markers (Position C from the 2026-05-17 Sanctum)
    exempt_rationales: dict[str, str] = {}
    raw_lines = schema_src.splitlines()
    for i, line in enumerate(raw_lines):
        # Look for CREATE TABLE statements in raw text
        m = re.match(
            r"\s*CREATE TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(\w+)",
            line, re.IGNORECASE,
        )
        if not m:
            continue
        tname = m.group(1).lower()
        # Walk back through any number of consecutive comment lines for
        # the marker. Allow whitespace and additional comment lines
        # between the marker and the CREATE TABLE.
        for j in range(i - 1, max(-1, i - 10), -1):
            prev = raw_lines[j].strip()
            if not prev:
                continue
            if not prev.startswith("--"):
                break
            mm = re.search(
                r"coverage:exempt\s*[—\-]+\s*(.+)$", prev,
            )
            if mm:
                rationale = mm.group(1).strip()
                # Reject obvious placeholders to keep the marker honest.
                if rationale and rationale.lower() not in (
                    "todo", "tbd", "fill in", "fixme", "...",
                ):
                    exempt_rationales[tname] = rationale
                    break

    unwatched = known_tables - all_sql
    exempt = sorted(t for t in unwatched if t in exempt_rationales)
    blind = sorted(t for t in unwatched if t not in exempt_rationales)

    if blind:
        print(f"  {Y}Tables no watcher reads AND no exempt marker:{NC} {len(blind)}")
        for t in blind[:15]:
            print(f"    · {t}")
        if len(blind) > 15:
            print(f"    {DIM}... and {len(blind) - 15} more{NC}")
    else:
        print(f"  {G}Every schema table is either watched or exempt with rationale.{NC}")
    if exempt:
        print(f"  {G}Tables exempt-with-rationale (Position C, 2026-05-17):{NC} {len(exempt)}")
        for t in exempt[:5]:
            r = exempt_rationales[t]
            r_short = r[:80] + ("…" if len(r) > 80 else "")
            print(f"    {DIM}·{NC} {t}: {DIM}{r_short}{NC}")
        if len(exempt) > 5:
            print(f"    {DIM}... and {len(exempt) - 5} more exempt tables{NC}")
    print()

    # §IV: Overlap (correlation potential)
    print(f"{PURPLE}§IV. Cross-watcher overlap (correlation potential){NC}")
    # node_id → list of watchers that mention it
    node_to_watchers: dict[str, list[str]] = {}
    for p in profiles:
        for nid in p["node_ids"]:
            node_to_watchers.setdefault(nid, []).append(p["name"])
    shared = sorted(
        ((nid, ws) for nid, ws in node_to_watchers.items() if len(ws) >= 2),
        key=lambda x: -len(x[1]),
    )
    if shared:
        for nid, ws in shared[:15]:
            tag = ""
            if nid in ("runtime:health", "runtime:swarm", "runtime:auth"):
                tag = f" {GOLD}[v9.10 shared surface]{NC}"
            print(f"  {G}{nid}{NC} ← {', '.join(ws)}{tag}")
    else:
        print(f"  {Y}No node IDs shared across watchers. CorrelationEngine will fire 0 times.{NC}")
        print(f"  {DIM}(Pre-v9.10 baseline; v9.10 added runtime:health + runtime:swarm.){NC}")
    print()

    return 0


sys.exit(main())
PYEOF
