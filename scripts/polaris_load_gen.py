#!/usr/bin/env python3
"""
polaris_load_gen.py
============================================================================

Async load generator for Polaris endpoints. Pure stdlib — no external
deps. Targets a single URL at a configurable RPS for a fixed duration;
reports throughput, latency percentiles, status-code histogram.

Used by `scripts/polaris-load-test.sh`.

Design:
- ``asyncio`` event loop + ``urllib.request`` in a thread pool
  (urllib is stdlib; httpx would be lighter but adds a dependency)
- Token-bucket pacing: emit ``rps`` requests/second uniformly
- 10-second progress lines + final summary

Run:
    python3 polaris_load_gen.py --target http://localhost:5000/api/health \\
                                --rps 50 --duration 30
"""

import argparse
import asyncio
import json
import statistics
import sys
import time
import urllib.error
import urllib.request
from collections import Counter


def _do_request(target, timeout=10.0):
    """Issue one HTTP GET; return (status_code, latency_ms, error)."""
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(target, timeout=timeout) as resp:
            # Drain the body to be fair to the server
            resp.read(64 * 1024)
            latency_ms = (time.perf_counter() - t0) * 1000.0
            return resp.status, latency_ms, None
    except urllib.error.HTTPError as e:
        latency_ms = (time.perf_counter() - t0) * 1000.0
        return e.code, latency_ms, f"HTTPError: {e.reason}"
    except (urllib.error.URLError, ConnectionError, TimeoutError) as e:
        latency_ms = (time.perf_counter() - t0) * 1000.0
        return None, latency_ms, f"NetworkError: {e}"


async def _bounded_request(sem, loop, target):
    async with sem:
        return await loop.run_in_executor(None, _do_request, target)


async def run_load(target, rps, duration, max_concurrency=200):
    """Main load loop. Returns (latencies_ms, status_counter, error_count)."""
    interval = 1.0 / rps
    end_at = time.perf_counter() + duration
    sem = asyncio.Semaphore(max_concurrency)
    loop = asyncio.get_event_loop()

    latencies = []
    statuses = Counter()
    errors = 0

    tasks = []
    next_emit = time.perf_counter()
    last_report_at = next_emit
    last_report_count = 0
    progress_interval = 10.0   # seconds between progress lines

    while time.perf_counter() < end_at:
        now = time.perf_counter()
        if now >= next_emit:
            tasks.append(asyncio.create_task(
                _bounded_request(sem, loop, target)
            ))
            next_emit += interval
        else:
            # Yield briefly so other tasks can run
            await asyncio.sleep(0.001)

        # Progress line every progress_interval
        if now - last_report_at >= progress_interval:
            done = sum(1 for t in tasks if t.done())
            collected_latencies = []
            for t in tasks:
                if t.done() and t.exception() is None:
                    status, lat, err = t.result()
                    if not err and status is not None:
                        collected_latencies.append(lat)
            if collected_latencies:
                p50 = statistics.median(collected_latencies)
                # quantile-style; statistics.quantiles needs n>=2
                p95 = (
                    statistics.quantiles(collected_latencies, n=20)[18]
                    if len(collected_latencies) >= 20 else max(collected_latencies)
                )
                p99 = (
                    statistics.quantiles(collected_latencies, n=100)[98]
                    if len(collected_latencies) >= 100 else max(collected_latencies)
                )
                elapsed = int(now - (next_emit - duration * interval))
                print(
                    f"  [{int(now - end_at + duration):2d}s]  "
                    f"hit {done}/{len(tasks)}   "
                    f"p50={p50:.1f}ms p95={p95:.1f}ms p99={p99:.1f}ms",
                    flush=True,
                )
            last_report_at = now
            last_report_count = done

    # Drain remaining tasks
    if tasks:
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for res in results:
            if isinstance(res, Exception):
                errors += 1
                continue
            status, lat, err = res
            if err:
                errors += 1
                statuses[f'err:{err.split(":")[0]}'] += 1
            else:
                statuses[status] += 1
                latencies.append(lat)

    return latencies, statuses, errors


def summarize(latencies, statuses, errors, target, rps, duration, wall):
    total = sum(statuses.values()) + errors
    print()
    print("  " + "─" * 60)
    print(f"  total requests:   {total}")
    success_pct = (
        100.0 * sum(c for s, c in statuses.items() if isinstance(s, int) and 200 <= s < 400) / total
        if total else 0.0
    )
    successes = sum(c for s, c in statuses.items() if isinstance(s, int) and 200 <= s < 400)
    print(f"  successes:        {successes}  ({success_pct:.2f}%)")
    print(f"  errors:           {errors}")
    rate_limited = statuses.get(429, 0)
    print(f"  rate-limited:     {rate_limited}")
    if statuses:
        breakdown = ", ".join(
            f"{k}={v}" for k, v in sorted(statuses.items(), key=lambda kv: -kv[1])
        )
        print(f"  status counts:    {breakdown}")
    if latencies:
        p50 = statistics.median(latencies)
        p95 = (
            statistics.quantiles(latencies, n=20)[18]
            if len(latencies) >= 20 else max(latencies)
        )
        p99 = (
            statistics.quantiles(latencies, n=100)[98]
            if len(latencies) >= 100 else max(latencies)
        )
        print(f"  p50 / p95 / p99:  {p50:.1f}ms / {p95:.1f}ms / {p99:.1f}ms")
    actual_rps = total / wall if wall else 0
    print(f"  wall-clock:       {wall:.2f}s   ({actual_rps:.2f} req/s)")


def main():
    ap = argparse.ArgumentParser(
        description="Polaris stdlib-only load generator"
    )
    ap.add_argument('--target', required=True,
                    help="Target URL (e.g. http://localhost:5000/api/health)")
    ap.add_argument('--rps', type=float, default=50.0,
                    help="Target requests per second")
    ap.add_argument('--duration', type=float, default=30.0,
                    help="Duration in seconds")
    args = ap.parse_args()

    print(f"polaris-load-test: {args.target} @ {args.rps:g} rps for {args.duration:g}s")
    t0 = time.perf_counter()
    try:
        latencies, statuses, errors = asyncio.run(
            run_load(args.target, args.rps, args.duration)
        )
    except KeyboardInterrupt:
        print("\n  interrupted; partial results follow:", file=sys.stderr)
        latencies, statuses, errors = [], Counter(), 0
    wall = time.perf_counter() - t0
    summarize(latencies, statuses, errors, args.target, args.rps, args.duration, wall)

    # Exit non-zero if more than 1% errored — useful for CI.
    total = sum(statuses.values()) + errors
    if total > 0 and errors / total > 0.01:
        sys.exit(1)


if __name__ == '__main__':
    main()
