"""PheromoneReader — HYDRA's window into the swarm substrate.

v9.04 / Sanctum 2026-05-14-hydra-revamp-pheromone-integration.md.

Watchers + the Hydra host import this module to read recent
Pheromone deposits without each writing its own SQL. The reader
groups deposits by tier (commander vs soldier) and per-class
freshness, returning structured `PheromoneSnapshot` objects.

Constitutional contract:
  - C1 (audit-of-record append-only): SELECT-only; never
    UPDATE/DELETE; the trigger holds independently
  - C10 (system identity is value-pure): only reads metadata
    columns (deposited_by / deposited_at / kind / intensity /
    node_id / evidence); never returns holder PII
  - G1 (deterministic): same query window → same result set
  - G3 (graceful failure): if DB is offline, returns an empty
    snapshot (status="db_offline"); never raises

Usage:

    reader = PheromoneReader(window_hours=6.0)
    snap = reader.snapshot()
    snap.commander_count    # int
    snap.soldier_count      # int
    snap.per_soldier_class  # dict[str, SoldierClassReading]
    snap.recent_alerts      # list[PheromoneRow]  (kind='alert')

    # Watcher-specific filters
    soldier_logs = reader.deposits_by_class("soldier_log_tail",
                                             window_hours=1.0)

The reader is INSTANCE-stateless — it can be re-snapshot'd safely
without coordinating with prior reads. DB connection opened +
closed per snapshot (small enough; bounded by the 6h window).
"""

from __future__ import annotations

import dataclasses
import datetime
import os
from typing import Any, Optional

# Optional psycopg2 import — graceful fallback to db_offline status
try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    _PSYCOPG2_AVAILABLE = True
except ImportError:
    psycopg2 = None
    _PSYCOPG2_AVAILABLE = False


# Soldier classes ship in v9.03; this reader pre-knows the canonical
# 8 names for per-class freshness checks. New soldier classes added
# later will appear in `per_soldier_class` automatically (the reader
# discovers from observed deposits, not from a registry).
KNOWN_SOLDIER_CLASSES_V9_03: tuple[str, ...] = (
    "soldier_route_pinger",
    "soldier_file_mtime",
    "soldier_process_alive",
    "soldier_disk_usage",
    "soldier_log_tail",
    "soldier_db_table_size",
    "soldier_heartbeat_freshness",
    "soldier_sanctum_freshness",
)


# v9.11 — the priest tier (a single new soldier class added to the
# v9.03 set). The witness is structurally distinct: it observes the
# OTHER eight soldiers' Pheromone deposits and emits a meta-finding
# (verdict + per-worker cadence). This gives the substrate internal
# self-knowledge alongside HYDRA's external observation.
#
# KNOWN_SOLDIER_CLASSES_V9_11 is a SUPERSET of the v9.03 set. The
# v9.03 constant is preserved for historical accuracy + backward
# compatibility (consumers wanting the original baseline still have
# it; consumers wanting the live operational set use v9.11).
PRIEST_SOLDIER_CLASS_V9_11: str = "soldier_swarm_witness"

KNOWN_SOLDIER_CLASSES_V9_11: tuple[str, ...] = (
    KNOWN_SOLDIER_CLASSES_V9_03 + (PRIEST_SOLDIER_CLASS_V9_11,)
)


# v9.05 / Wave 1 / D2 — Centralized window defaults.
#
# Pre-v9.05 each watcher passed `window_hours=N` literally; the
# values drifted (ant_colony 6h, security 6h, performance 6h, schema
# 24h, cognitive 24h). No central policy meant a refactor of "what's
# the right window for soldier_X?" required touching N watchers.
#
# v9.05 names two policies:
#   WINDOW_FAST  — high-cadence soldiers + watchers that take fresh-
#                  state snapshots (soldier_log_tail, route_pinger,
#                  ant_colony tier-split).
#   WINDOW_SLOW  — slow-cadence soldiers + watchers reading
#                  accumulated state (soldier_db_table_size growth,
#                  soldier_sanctum_freshness aging).
#
# Watchers import the right symbol; the v9.04 PheromoneReader
# constructor still accepts `window_hours=N` for ad-hoc overrides
# (e.g. the --pheromone-window-hours CLI flag).
WINDOW_FAST: float = 6.0     # commander cron cadence; same-pass freshness
WINDOW_SLOW: float = 24.0    # day-scale accumulated-state observations


@dataclasses.dataclass
class PheromoneRow:
    """One Pheromone row, narrowed to HYDRA-relevant columns."""
    deposited_by: str
    deposited_at: datetime.datetime
    intensity: float
    kind: str
    node_id: str
    evidence: dict[str, Any]
    half_life_hours: float

    @property
    def tier(self) -> str:
        """'soldier' if deposited_by starts with 'soldier_', else 'commander'."""
        return "soldier" if self.deposited_by.startswith("soldier_") else "commander"

    def to_dict(self) -> dict[str, Any]:
        return {
            "deposited_by": self.deposited_by,
            "deposited_at": self.deposited_at.isoformat(timespec="seconds"),
            "intensity": float(self.intensity),
            "kind": self.kind,
            "node_id": self.node_id,
            "evidence": self.evidence,
            "half_life_hours": float(self.half_life_hours),
            "tier": self.tier,
        }


@dataclasses.dataclass
class SoldierClassReading:
    """Per-soldier-class summary within the window."""
    soldier_name: str
    deposits_in_window: int
    most_recent_deposit_at: Optional[datetime.datetime]
    most_recent_kind: Optional[str]
    age_minutes: Optional[float]   # minutes since most_recent_deposit_at

    @property
    def is_silent(self) -> bool:
        """True if the soldier hasn't deposited in >2h or never."""
        return self.age_minutes is None or self.age_minutes > 120.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "soldier_name": self.soldier_name,
            "deposits_in_window": self.deposits_in_window,
            "most_recent_deposit_at": (
                self.most_recent_deposit_at.isoformat(timespec="seconds")
                if self.most_recent_deposit_at else None
            ),
            "most_recent_kind": self.most_recent_kind,
            "age_minutes": (
                round(self.age_minutes, 1) if self.age_minutes is not None else None
            ),
            "is_silent": self.is_silent,
        }


@dataclasses.dataclass
class PheromoneSnapshot:
    """A point-in-time read of recent Pheromone activity.

    `status` is "ok" when the snapshot completed cleanly, or
    "db_offline" when psycopg2/DB couldn't be reached (in which case
    all counts are 0 and per_soldier_class is empty)."""
    status: str  # "ok" | "db_offline"
    window_hours: float
    snapshot_at: datetime.datetime
    commander_count: int
    soldier_count: int
    per_soldier_class: dict[str, SoldierClassReading]
    recent_alerts: list[PheromoneRow]
    recent_drift: list[PheromoneRow]
    error: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "window_hours": self.window_hours,
            "snapshot_at": self.snapshot_at.isoformat(timespec="seconds"),
            "commander_count": self.commander_count,
            "soldier_count": self.soldier_count,
            "per_soldier_class": {
                k: v.to_dict() for k, v in self.per_soldier_class.items()
            },
            "recent_alerts": [r.to_dict() for r in self.recent_alerts],
            "recent_drift": [r.to_dict() for r in self.recent_drift],
            "error": self.error,
        }

    @property
    def silent_soldier_classes(self) -> list[str]:
        """Soldier classes that haven't deposited in >2h."""
        return sorted(
            name for name, reading in self.per_soldier_class.items()
            if reading.is_silent
        )


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


class PheromoneReader:
    """Read-only Pheromone window for HYDRA + watchers."""

    def __init__(self, window_hours: float = 6.0):
        self.window_hours = float(window_hours)

    def snapshot(self) -> PheromoneSnapshot:
        """Take a point-in-time snapshot of recent Pheromone activity.
        Graceful-fails to db_offline status if psycopg2 / DB is unavailable."""
        now = datetime.datetime.now()
        empty = PheromoneSnapshot(
            status="db_offline",
            window_hours=self.window_hours,
            snapshot_at=now,
            commander_count=0,
            soldier_count=0,
            per_soldier_class={},
            recent_alerts=[],
            recent_drift=[],
        )

        conn = _connect_db()
        if conn is None:
            empty.error = "no DB connection (psycopg2 missing or DB unreachable)"
            return empty

        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT deposited_by, deposited_at, intensity, kind,
                           node_id, evidence, half_life_hours
                      FROM Pheromone
                     WHERE deposited_at >= now() - (%s || ' hours')::interval
                     ORDER BY deposited_at DESC
                     LIMIT 5000
                    """,
                    (self.window_hours,),
                )
                rows = [PheromoneRow(
                    deposited_by=r["deposited_by"],
                    deposited_at=r["deposited_at"],
                    intensity=float(r["intensity"]),
                    kind=r["kind"],
                    node_id=r["node_id"],
                    evidence=r["evidence"] or {},
                    half_life_hours=float(r["half_life_hours"]),
                ) for r in cur.fetchall()]
        except Exception as exc:                # noqa: BLE001 — graceful
            empty.error = f"{type(exc).__name__}: {exc}"
            return empty
        finally:
            conn.close()

        commander_count = sum(1 for r in rows if r.tier == "commander")
        soldier_count = sum(1 for r in rows if r.tier == "soldier")
        recent_alerts = [r for r in rows if r.kind == "alert"][:50]
        recent_drift = [r for r in rows if r.kind == "drift"][:50]

        # Per-soldier-class freshness
        per_soldier_class: dict[str, SoldierClassReading] = {}
        # Seed all known classes (so silent classes appear)
        # v9.11: use the v9.11 superset (8 workers + 1 priest = 9)
        for name in KNOWN_SOLDIER_CLASSES_V9_11:
            per_soldier_class[name] = SoldierClassReading(
                soldier_name=name,
                deposits_in_window=0,
                most_recent_deposit_at=None,
                most_recent_kind=None,
                age_minutes=None,
            )
        # Then update from observed deposits (also discovers new
        # soldier classes added after v9.03)
        for row in rows:
            if not row.deposited_by.startswith("soldier_"):
                continue
            name = row.deposited_by
            existing = per_soldier_class.get(name)
            if existing is None:
                existing = SoldierClassReading(
                    soldier_name=name,
                    deposits_in_window=0,
                    most_recent_deposit_at=None,
                    most_recent_kind=None,
                    age_minutes=None,
                )
            existing.deposits_in_window += 1
            if (existing.most_recent_deposit_at is None
                    or row.deposited_at > existing.most_recent_deposit_at):
                existing.most_recent_deposit_at = row.deposited_at
                existing.most_recent_kind = row.kind
                # age_minutes computed at snapshot time (pure function of
                # deposited_at + now)
                age_s = (now - row.deposited_at.replace(tzinfo=None)).total_seconds() \
                    if row.deposited_at.tzinfo is None else \
                    (datetime.datetime.now(row.deposited_at.tzinfo)
                     - row.deposited_at).total_seconds()
                existing.age_minutes = max(0.0, age_s / 60.0)
            per_soldier_class[name] = existing

        return PheromoneSnapshot(
            status="ok",
            window_hours=self.window_hours,
            snapshot_at=now,
            commander_count=commander_count,
            soldier_count=soldier_count,
            per_soldier_class=per_soldier_class,
            recent_alerts=recent_alerts,
            recent_drift=recent_drift,
        )

    def deposits_by_class(
        self,
        soldier_name: str,
        window_hours: Optional[float] = None,
    ) -> list[PheromoneRow]:
        """Watcher-specific filter: just the deposits from one soldier
        class within an optional override window. Empty list if DB
        offline."""
        wh = window_hours if window_hours is not None else self.window_hours
        conn = _connect_db()
        if conn is None:
            return []
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT deposited_by, deposited_at, intensity, kind,
                           node_id, evidence, half_life_hours
                      FROM Pheromone
                     WHERE deposited_by = %s
                       AND deposited_at >= now() - (%s || ' hours')::interval
                     ORDER BY deposited_at DESC
                     LIMIT 1000
                    """,
                    (soldier_name, wh),
                )
                return [PheromoneRow(
                    deposited_by=r["deposited_by"],
                    deposited_at=r["deposited_at"],
                    intensity=float(r["intensity"]),
                    kind=r["kind"],
                    node_id=r["node_id"],
                    evidence=r["evidence"] or {},
                    half_life_hours=float(r["half_life_hours"]),
                ) for r in cur.fetchall()]
        except Exception:
            return []
        finally:
            conn.close()
