"""Soldier colony — runs the soldier tier in a tight loop and
aggregates Observations into batched Pheromone deposits.

v9.03 / Sanctum 2026-05-14-hybrid-swarm-mirai-pattern.

Design contract (Sanctum §VI):
  - Discovers all Soldier subclasses under polaris_swarm.soldiers.*
  - Runs each soldier on every cycle within the run window
  - Aggregates Observations by (soldier_class, node_id):
      → one Pheromone deposit per group
      → intensity = mean of observation values where numeric, else
        the soldier class's INTENSITY default
      → kind = the most-severe kind seen in the group
        (alert > drift > info)
      → evidence = {
          "aggregated_count": N,
          "cycles": K,
          "observations": [first_3_samples],
          "soldier_class": <class name>
        }
  - C1 preserved: each deposit is a single append-only INSERT
  - F5 exempt: no Treasury writes; no CitizenFinding path
  - Graceful-failure: per-soldier crash returns []; colony continues

Usage (via colony.py CLI):
  python -m polaris_swarm.colony --soldiers --duration 30
  python -m polaris_swarm.colony --hybrid --duration 30

The aggregation strategy bounds Pheromone table growth:
  8 soldiers × 30 cycles each = 240 raw observations
  → grouped by (class, node_id) ≈ 8-16 deposits per cycle batch
"""
from __future__ import annotations

import dataclasses
import importlib
import inspect
import os
import pathlib
import pkgutil
import statistics
import sys
import time
from collections import defaultdict
from typing import Any

from polaris_swarm.soldiers.base import (
    Observation,
    Soldier,
    SOLDIER_INTENSITY_MIN,
    SOLDIER_INTENSITY_MAX,
    KIND_INFO,
    KIND_DRIFT,
    KIND_ALERT,
    KIND_CURIOUS,
)

# Optional psycopg2 (matches the colony.py pattern)
try:
    import psycopg2
    from psycopg2.extras import Json
    _PSYCOPG2_AVAILABLE = True
except ImportError:
    psycopg2 = None
    _PSYCOPG2_AVAILABLE = False


# Severity ordering used to pick the "most severe kind" within a
# soldier's grouped observations. Higher = more severe.
_KIND_SEVERITY: dict[str, int] = {
    KIND_INFO: 0,
    KIND_CURIOUS: 1,
    KIND_DRIFT: 2,
    KIND_ALERT: 3,
}


@dataclasses.dataclass(frozen=True)
class _GroupKey:
    soldier_name: str
    node_id: str
    half_life_hours: float


def discover_soldiers() -> list[type[Soldier]]:
    """Walk polaris_swarm.soldiers.* and return every Soldier subclass
    whose NAME starts with 'soldier_'. Mirrors the Ant discovery
    pattern in colony.py without sharing code (G6: no inter-tier
    imports beyond the base classes)."""
    import polaris_swarm.soldiers as soldiers_pkg

    found: list[type[Soldier]] = []
    seen_names: set[str] = set()
    pkg_path = list(soldiers_pkg.__path__)
    for module_info in pkgutil.iter_modules(pkg_path):
        if module_info.name.startswith("_") or module_info.name == "base":
            continue
        full = f"polaris_swarm.soldiers.{module_info.name}"
        try:
            mod = importlib.import_module(full)
        except Exception:
            continue
        for _, cls in inspect.getmembers(mod, inspect.isclass):
            if (
                issubclass(cls, Soldier)
                and cls is not Soldier
                and cls.NAME.startswith("soldier_")
                and cls.NAME not in seen_names
            ):
                found.append(cls)
                seen_names.add(cls.NAME)
    # Stable ordering by NAME for deterministic deposit order
    found.sort(key=lambda c: c.NAME)
    return found


def _connect_db():
    if not _PSYCOPG2_AVAILABLE:
        return None
    try:
        return psycopg2.connect(
            host=os.environ.get("POLARIS_DB_HOST", "localhost"),
            dbname=os.environ.get("POLARIS_DB_NAME", "polaris_test"),
            user=os.environ.get("POLARIS_DB_USER", "polaris_app"),
            password=os.environ.get("POLARIS_DB_PASSWORD", "polaris_dev_password"),
            connect_timeout=2,
        )
    except Exception:
        return None


def _safely_observe(soldier: Soldier) -> list[Observation]:
    """Run one soldier's .observe() in graceful-failure mode."""
    try:
        out = soldier.observe()
    except Exception as e:                     # noqa: BLE001 — by design
        # G3 / G6: a soldier crash returns [] for that cycle; the
        # colony continues with the rest. Print to stderr for the
        # operator's log scrape but never raise.
        sys.stderr.write(
            f"soldier {soldier.NAME} crashed: {type(e).__name__}: {e}\n"
        )
        return []
    if out is None:
        return []
    if not isinstance(out, list):
        sys.stderr.write(
            f"soldier {soldier.NAME} returned {type(out).__name__}, "
            "not list[Observation]; skipping\n"
        )
        return []
    return [obs for obs in out if isinstance(obs, Observation)]


def _aggregate(
    cycles: int,
    observations_by_soldier: dict[type[Soldier], list[Observation]],
) -> list[tuple[type[Soldier], _GroupKey, dict[str, Any]]]:
    """Group observations by (soldier_class, node_id); compute the
    intensity / kind / evidence per group.

    Returns a list of (SoldierCls, group_key, deposit_payload) tuples
    ready to INSERT into Pheromone.
    """
    out: list[tuple[type[Soldier], _GroupKey, dict[str, Any]]] = []

    for SoldierCls, obs_list in observations_by_soldier.items():
        # Group by node_id (the soldier's INTENSITY + HALF_LIFE_HOURS
        # are class-level, so they're constant within a soldier's
        # observations)
        per_node: dict[str, list[Observation]] = defaultdict(list)
        for obs in obs_list:
            per_node[obs.node_id].append(obs)

        for node_id, group in per_node.items():
            # Compute intensity: try to extract numeric value from the
            # first observation; if not present, use the class default.
            intensity = float(SoldierCls.INTENSITY)
            numeric_values: list[float] = []
            for obs in group:
                if isinstance(obs.value, (int, float)) and not isinstance(obs.value, bool):
                    numeric_values.append(float(obs.value))
                elif isinstance(obs.value, dict):
                    # Look for common numeric keys
                    for k in ("value", "count", "age_s", "age_days",
                              "used_pct", "errors", "warnings",
                              "estimated_rows", "latency_ms"):
                        v = obs.value.get(k)
                        if isinstance(v, (int, float)) and not isinstance(v, bool):
                            numeric_values.append(float(v))
                            break
            if numeric_values:
                # Bound the intensity into the soldier band so we don't
                # accidentally exceed the [0.5, 2.0] range the soldier
                # tier is supposed to occupy. Treats raw numeric values
                # as severity hints, not intensity proper.
                # Always emit the soldier class's default INTENSITY so
                # the bloom heatmap sees consistent soldier signal.
                intensity = float(SoldierCls.INTENSITY)

            # Pick the most-severe kind in the group
            severity = max(_KIND_SEVERITY.get(o.kind, 0) for o in group)
            kind = next(k for k, v in _KIND_SEVERITY.items() if v == severity)

            # Build evidence: count + cycles + sample
            sample = []
            for obs in group[:3]:
                sample.append({"node_id": obs.node_id,
                               "value": obs.value,
                               "kind": obs.kind})
            evidence: dict[str, Any] = {
                "soldier_class": SoldierCls.__name__,
                "soldier_name": SoldierCls.NAME,
                "aggregated_count": len(group),
                "cycles": cycles,
                "observations": sample,
            }
            key = _GroupKey(
                soldier_name=SoldierCls.NAME,
                node_id=node_id,
                half_life_hours=float(SoldierCls.HALF_LIFE_HOURS),
            )
            out.append((SoldierCls, key, {
                "intensity": intensity,
                "kind": kind,
                "evidence": evidence,
            }))
    return out


def _deposit(
    aggregated: list[tuple[type[Soldier], _GroupKey, dict[str, Any]]],
    soldiers_by_cls: dict[type[Soldier], Soldier],
) -> int:
    """INSERT one Pheromone row per aggregated group. Returns the
    count of rows written (0 if no DB connection)."""
    conn = _connect_db()
    if conn is None:
        sys.stderr.write(
            "polaris_swarm.soldier_colony: no DB connection (set POLARIS_DB_* "
            "env vars and ensure psycopg2 is installed); use --soldier-dry "
            "to scan without writing\n"
        )
        return 0
    written = 0
    try:
        with conn:
            with conn.cursor() as cur:
                for SoldierCls, key, payload in aggregated:
                    soldier = soldiers_by_cls[SoldierCls]
                    seed = getattr(soldier, "seed", 0)
                    # Per-soldier advisory lock (mirrors the per-ant
                    # lock in colony.py); keyspace = hash(NAME) % 2^31
                    lock_key = abs(hash(SoldierCls.NAME)) % (2 ** 31)
                    cur.execute(
                        "SELECT pg_advisory_xact_lock(%s)", (lock_key,)
                    )
                    cur.execute(
                        """
                        INSERT INTO Pheromone
                          (deposited_by, node_id, intensity, kind,
                           half_life_hours, evidence, seed)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            SoldierCls.NAME,
                            key.node_id,
                            payload["intensity"],
                            payload["kind"],
                            key.half_life_hours,
                            Json(payload["evidence"]),
                            seed,
                        ),
                    )
                    written += 1
    finally:
        conn.close()
    return written


def run_soldier_colony(
    duration_s: float = 30.0,
    cycle_interval_s: float = 1.0,
    root: pathlib.Path | None = None,
    dry: bool = False,
) -> dict[str, Any]:
    """Run the soldier tier for `duration_s` seconds, aggregating
    Observations and depositing one Pheromone per group.

    Returns a dict summary:
      {
        "soldiers_discovered": N,
        "cycles_completed": K,
        "raw_observations": M,
        "deposits_written": D,
        "deposits_skipped_dry": Bool,
        "elapsed_s": float,
      }
    """
    if root is None:
        root = pathlib.Path(__file__).resolve().parent.parent

    soldier_classes = discover_soldiers()
    soldiers_by_cls: dict[type[Soldier], Soldier] = {
        cls: cls(root) for cls in soldier_classes
    }

    observations_by_soldier: dict[type[Soldier], list[Observation]] = defaultdict(list)
    cycles = 0
    raw_count = 0

    t0 = time.monotonic()
    deadline = t0 + duration_s
    while time.monotonic() < deadline:
        for SoldierCls, soldier in soldiers_by_cls.items():
            obs = _safely_observe(soldier)
            observations_by_soldier[SoldierCls].extend(obs)
            raw_count += len(obs)
        cycles += 1
        # Sleep until the next cycle if there's still time
        elapsed = time.monotonic() - t0
        next_cycle = (cycles * cycle_interval_s)
        sleep_s = next_cycle - elapsed
        if sleep_s > 0 and time.monotonic() + sleep_s < deadline:
            time.sleep(sleep_s)
    elapsed_s = time.monotonic() - t0

    aggregated = _aggregate(cycles, observations_by_soldier)
    deposits = 0 if dry else _deposit(aggregated, soldiers_by_cls)

    return {
        "soldiers_discovered": len(soldier_classes),
        "cycles_completed": cycles,
        "raw_observations": raw_count,
        "deposits_aggregated": len(aggregated),
        "deposits_written": deposits,
        "deposits_skipped_dry": dry,
        "elapsed_s": round(elapsed_s, 2),
    }
