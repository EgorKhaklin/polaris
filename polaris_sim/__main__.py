"""`python3 -m polaris_sim` - build a synthetic nation and (later ships) run its
life through the real Polaris system.

    python3 -m polaris_sim build --scale 100000 --seed 42

Reads the standard POLARIS_DB_* environment (host / name / user / password),
exactly like the operator CLI, so it points at whatever database is configured.
This is a benchmark and test harness: point it at an expendable database.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

from . import nation, reference


def _db_config() -> dict:
    return {
        "host": os.environ.get("POLARIS_DB_HOST", "localhost"),
        "dbname": os.environ.get("POLARIS_DB_NAME", "polaris_test"),
        "user": os.environ.get("POLARIS_DB_USER", "polaris_app"),
        "password": os.environ.get("POLARIS_DB_PASSWORD", "polaris_dev_password"),
    }


def _connect():
    import psycopg2
    from psycopg2.extras import RealDictCursor
    cfg = _db_config()
    try:
        return psycopg2.connect(cursor_factory=RealDictCursor, **cfg)
    except psycopg2.OperationalError as e:
        sys.stderr.write(f"cannot connect to database {cfg['dbname']} at {cfg['host']}: {e}\n")
        raise SystemExit(2)


def cmd_build(args: argparse.Namespace) -> int:
    plan = nation.plan_nation(scale_divisor=args.scale, seed=args.seed)
    if not args.json:
        print(f"Synthetic United States (scale 1:{args.scale}, seed {args.seed})")
        print(f"  jurisdictions : {plan.jurisdictions}")
        print(f"  ID bureaus    : {plan.total_bureaus}")
        print(f"  people        : {plan.total_people:,}")
        print(f"  (full-scale reference population: {reference.US_TOTAL_POPULATION:,})")
    if args.plan_only:
        if args.json:
            print(json.dumps({"scale_divisor": args.scale, "seed": args.seed,
                              "jurisdictions": plan.jurisdictions,
                              "bureaus": plan.total_bureaus, "people": plan.total_people}))
        return 0

    from . import load
    conn = _connect()
    try:
        last = [0]

        def progress(juris: str, done: int, total: int) -> None:
            pct = int(100 * done / total) if total else 100
            if pct >= last[0] + 10:
                last[0] = pct
                if not args.json:
                    sys.stderr.write(f"  ... {pct:3d}%  ({done:,}/{total:,})\n")

        stats = load.build_nation(conn, plan, batch_size=args.batch_size, progress=progress)
    finally:
        conn.close()

    summary = {
        "scale_divisor": stats.scale_divisor, "seed": stats.seed,
        "agencies": stats.agencies, "people": stats.people,
        "tokens_issued": stats.tokens_issued,
        "seconds": round(stats.seconds, 3), "rows_per_sec": round(stats.rows_per_sec, 1),
    }
    if args.json:
        print(json.dumps(summary))
    else:
        print(f"\nLoaded through the real bulk-enrollment pipeline:")
        print(f"  agencies      : {stats.agencies:,}")
        print(f"  tokens issued : {stats.tokens_issued:,}")
        print(f"  wall time     : {stats.seconds:.2f}s")
        print(f"  throughput    : {stats.rows_per_sec:,.0f} enrollments/s")
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    from . import events
    conn = _connect()
    try:
        stats = events.run_stream(
            conn, verifications=args.events, lifecycle=args.lifecycle,
            window_hours=args.window, seed=args.seed, batch_size=args.batch_size)
    except RuntimeError as e:
        sys.stderr.write(f"{e}\n")
        return 1
    finally:
        conn.close()

    summary = {
        "verifications": stats.verifications, "revocations": stats.revocations,
        "window_hours": args.window, "seed": args.seed,
        "seconds": round(stats.seconds, 3), "rows_per_sec": round(stats.rows_per_sec, 1),
        "by_disclosure": stats.by_disclosure,
    }
    if args.json:
        print(json.dumps(summary))
    else:
        print(f"Life-event stream over the last {args.window:g}h (seed {args.seed}):")
        print(f"  verifications : {stats.verifications:,}")
        for level in ("ZERO_KNOWLEDGE", "SELECTIVE", "FULL"):
            print(f"      {level:<15}: {stats.by_disclosure.get(level, 0):,}")
        print(f"  revocations   : {stats.revocations:,} (through uc8_revoke_token)")
        print(f"  wall time     : {stats.seconds:.2f}s")
        print(f"  throughput    : {stats.rows_per_sec:,.0f} verifications/s")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="polaris_sim",
                                description="Polaris national simulation and benchmark harness.")
    sub = p.add_subparsers(dest="command", metavar="COMMAND")
    b = sub.add_parser("build", help="generate a synthetic nation and enroll it")
    b.add_argument("--scale", type=int, default=100000,
                   help="downscale divisor: synthetic people ~= US population / scale (default 100000)")
    b.add_argument("--seed", type=int, default=42, help="deterministic seed (default 42)")
    b.add_argument("--batch-size", type=int, default=5000,
                   help="rows per uc_bulk_issue batch (default 5000)")
    b.add_argument("--plan-only", action="store_true",
                   help="print the plan without touching the database")
    b.add_argument("--json", action="store_true", help="emit a JSON summary")

    r = sub.add_parser("run", help="drive a life-event stream through the enrolled nation")
    r.add_argument("--events", type=int, default=100000,
                   help="verifications to generate (default 100000)")
    r.add_argument("--lifecycle", type=int, default=0,
                   help="token revocations through uc8_revoke_token (default 0)")
    r.add_argument("--window", type=float, default=24.0,
                   help="spread events over the last N hours (default 24)")
    r.add_argument("--seed", type=int, default=42, help="deterministic seed (default 42)")
    r.add_argument("--batch-size", type=int, default=10000,
                   help="rows per COPY batch (default 10000)")
    r.add_argument("--json", action="store_true", help="emit a JSON summary")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "build":
        return cmd_build(args)
    if args.command == "run":
        return cmd_run(args)
    build_parser().print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
