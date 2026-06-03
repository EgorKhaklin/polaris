#!/usr/bin/env python3
"""ai-swarm-bloom — renders Mycelium's pheromone state as a heatmap.

This is the operator-facing surface of the swarm. It queries the
Pheromone table, computes effective intensity per node via the
deterministic decay function, and prints a sorted summary of the
brain-map nodes currently lit up by the swarm.

The bloom is the only synthesis surface. It does NOT call an LLM
in this Phase-1 implementation. The pheromone log itself is the
truth; the bloom is just a rendering.

Modes:
    --top N           print top N hottest brain-map nodes (default 20)
    --by-ant          group by depositing ant
    --by-kind         group by kind (drift/alert/info/curious)
    --since-hours N   only consider deposits within the last N hours
    --json            JSON output
    --dry             scan colony and print pheromones without DB

Substitutable per v8.30: future-agents may replace this renderer
with a different visualization (e.g., live brain-map overlay,
terminal TUI, web dashboard) without touching the constitution.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import pathlib
import sys
from collections import defaultdict
from datetime import datetime, timezone

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    _PSYCOPG2_AVAILABLE = True
except ImportError:
    psycopg2 = None
    RealDictCursor = None
    _PSYCOPG2_AVAILABLE = False


def _project_root() -> pathlib.Path:
    return pathlib.Path(__file__).resolve().parent.parent


def _connect_db():
    if not _PSYCOPG2_AVAILABLE:
        return None
    try:
        return psycopg2.connect(
            host=os.environ.get("POLARIS_DB_HOST", "localhost"),
            dbname=os.environ.get("POLARIS_DB_NAME", "polaris_test"),
            user=os.environ.get("POLARIS_DB_USER", "polaris_app"),
            password=os.environ.get("POLARIS_DB_PASSWORD", "polaris_dev_password"),
            cursor_factory=RealDictCursor,
        )
    except Exception:
        return None


def _effective(intensity: float, age_hours: float, half_life_hours: float) -> float:
    """Identical decay function to polaris_swarm/base.py::effective_intensity.

    Duplicated here intentionally so the bloom renderer has no Python
    dependency on the swarm package — anyone can run the bloom against
    the Pheromone table without having polaris_swarm/ installed.
    """
    if age_hours < 0:
        age_hours = 0.0
    if half_life_hours <= 0:
        return 0.0
    return intensity * math.exp(-math.log(2) * age_hours / half_life_hours)


def fetch_pheromones(since_hours: float) -> list[dict]:
    """Return raw Pheromone rows for the last `since_hours`. Decay
    NOT applied at this layer — the caller computes effective
    intensity at render time."""
    conn = _connect_db()
    if conn is None:
        return []
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT pheromone_id, deposited_at, deposited_by,
                           node_id, intensity::float, kind,
                           half_life_hours::float, evidence, seed
                      FROM Pheromone
                     WHERE deposited_at >= NOW() - (%s || ' hours')::INTERVAL
                     ORDER BY deposited_at DESC
                    """,
                    (since_hours,),
                )
                return list(cur.fetchall())
    finally:
        conn.close()


# Via Appia (Arc G / G1 / v8.71): mirror constant; we don't
# import from polaris_swarm.base here because the bloom script
# may run from sys.path positions where the package isn't
# importable. Default value if the base module IS importable
# wins via the try/except below.
VIA_APPIA_MULTIPLIER_DEFAULT = 1.5


def _load_via_appia_multiplier() -> float:
    try:
        from polaris_swarm.base import VIA_APPIA_MULTIPLIER
        return float(VIA_APPIA_MULTIPLIER)
    except ImportError:
        return VIA_APPIA_MULTIPLIER_DEFAULT


def render_top_nodes(
    rows: list[dict], n: int, now: datetime,
    root: pathlib.Path | None = None,
) -> list[tuple[str, float, int]]:
    """Aggregate effective intensity per node; return top N as
    (node_id, total_effective_intensity, deposit_count).

    Priority surfacing (Arc G / v8.71): pheromones marked
    `priority=True` get a `VIA_APPIA_MULTIPLIER` (1.5×). Priority is
    auto-set for ALERT-kind pheromones and intensities ≥7.0 (in
    `AntFinding.__post_init__`), so constitutional emergencies surface
    even when the depositing ant didn't explicitly opt in.

    (v9.50: the Cursus Honorum denarii-balance multiplier was removed —
    it was provably inert, every ant mapping to 1.0× because no balance
    ever approached the tier threshold. The `root` arg is retained for
    signature compatibility.)
    """
    via_appia_mult = _load_via_appia_multiplier()
    bucket: dict[str, list[float]] = defaultdict(list)
    for row in rows:
        # deposited_at may be naive; align to UTC
        ts = row["deposited_at"]
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        age_hours = max(0.0, (now - ts).total_seconds() / 3600.0)
        eff = _effective(
            float(row["intensity"]),
            age_hours,
            float(row["half_life_hours"]),
        )
        # G1 Via Appia multiplier — priority pheromones compound.
        # Priority may live in row directly (DB column) or in
        # evidence (when synthesized via --dry from in-memory
        # AntFinding objects).
        priority = bool(row.get("priority", False))
        if not priority:
            evidence = row.get("evidence") or {}
            priority = bool(evidence.get("priority", False))
        if priority:
            eff *= via_appia_mult
        bucket[row["node_id"]].append(eff)
    aggregated = [
        (node, sum(intensities), len(intensities))
        for node, intensities in bucket.items()
    ]
    aggregated.sort(key=lambda t: t[1], reverse=True)
    return aggregated[:n]


def main() -> int:
    p = argparse.ArgumentParser(prog="ai-swarm-bloom")
    p.add_argument("--top", type=int, default=20, help="top N hottest nodes")
    p.add_argument("--by-ant", action="store_true",
                   help="group by depositing ant")
    p.add_argument("--by-legio", action="store_true",
                   help="group by depositing legion (v8.64+)")
    p.add_argument("--by-kind", action="store_true",
                   help="group by kind")
    p.add_argument("--since-hours", type=float, default=72.0,
                   help="window in hours (default 72)")
    p.add_argument("--json", action="store_true",
                   help="JSON output instead of human-readable")
    p.add_argument("--dry", action="store_true",
                   help="scan colony in-memory; do not touch the DB")
    args = p.parse_args()

    now = datetime.now(timezone.utc)

    if args.dry:
        # Run the colony in --dry mode and render its in-memory findings
        # as if they were just deposited. Useful when there's no DB.
        try:
            from polaris_swarm.colony import run_colony
        except ImportError:
            sys.stderr.write("ai-swarm-bloom: polaris_swarm not importable\n")
            return 1
        results = run_colony(dry=True)
        # Synthesize pheromone-like rows from the findings. Post-v8.64
        # the colony returns per-legion (legion, ant_results) where
        # ant_results is list[(AntCls, list[AntFinding])]; flatten while
        # populating the legio field in evidence.
        rows = []
        for legion, ant_results in results:
            for AntCls, findings in ant_results:
                for f in findings:
                    evidence = dict(f.evidence)
                    evidence.setdefault("legio", legion.NAME)
                    # Via Appia: propagate priority into evidence
                    # so the bloom renderer sees it in --dry mode.
                    if getattr(f, "priority", False):
                        evidence["priority"] = True
                    rows.append({
                        "pheromone_id": 0,
                        "deposited_at": now,
                        "deposited_by": AntCls.NAME,
                        "node_id": f.node_id,
                        "intensity": f.intensity,
                        "kind": f.kind,
                        "half_life_hours": f.half_life_hours,
                        "evidence": evidence,
                        "priority": getattr(f, "priority", False),
                        "seed": 0,
                    })
    else:
        rows = fetch_pheromones(args.since_hours)
        if not _PSYCOPG2_AVAILABLE:
            sys.stderr.write(
                "ai-swarm-bloom: psycopg2 not installed; use --dry "
                "to render the colony's in-memory findings instead\n"
            )
            return 1

    if args.json:
        top = render_top_nodes(rows, args.top, now, root=_project_root())
        payload = {
            "now": now.isoformat(),
            "since_hours": args.since_hours,
            "deposits": len(rows),
            "top_nodes": [
                {"node_id": node, "effective_intensity": round(intensity, 3),
                 "deposit_count": count}
                for node, intensity, count in top
            ],
        }
        print(json.dumps(payload, indent=2))
        return 0

    # Human-readable header
    print(f"═══ Mycelium bloom — last {args.since_hours:.0f}h ═══")
    print(f"  Deposits considered: {len(rows)}")
    if not rows:
        print("  Swarm is silent. No pheromones in window.")
        return 0
    print()

    if args.by_kind:
        by_kind: dict[str, int] = defaultdict(int)
        for r in rows:
            by_kind[r["kind"]] += 1
        print("── By kind ──")
        for k in ("alert", "drift", "curious", "info"):
            cnt = by_kind.get(k, 0)
            if cnt:
                print(f"  {k:10s} {cnt:4d} deposits")
        print()

    if args.by_ant:
        by_ant: dict[str, int] = defaultdict(int)
        for r in rows:
            by_ant[r["deposited_by"]] += 1
        print("── By ant ──")
        for ant_name in sorted(by_ant, key=lambda k: -by_ant[k]):
            print(f"  {ant_name:30s} {by_ant[ant_name]:4d} deposits")
        print()

    if args.by_legio:
        # Legion identity lives in evidence JSONB per v8.64 colony refactor.
        by_legio: dict[str, int] = defaultdict(int)
        for r in rows:
            ev = r.get("evidence") or {}
            legio = ev.get("legio", "(unattributed)")
            by_legio[legio] += 1
        print("── By legio ──")
        for legio in sorted(by_legio, key=lambda k: -by_legio[k]):
            print(f"  {legio:25s} {by_legio[legio]:4d} deposits")
        print()

    top = render_top_nodes(rows, args.top, now, root=_project_root())
    print(f"── Top {len(top)} hottest brain-map nodes ──")
    for node, intensity, count in top:
        bar = "█" * min(40, int(intensity * 4))
        print(f"  {intensity:6.2f}  [{count:3d}]  {node}")
        if bar:
            print(f"          {bar}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
