"""soldier_swarm_witness — the priest tier; the substrate's internal observer.

v9.11 / Architect's vision Chapter "Reserves honored". Pre-v9.11 the
Mycelium swarm had eight soldier classes, each performing its own
domain-scoped operational check. The substrate observed itself only
indirectly via HYDRA (the external lens layer).

This soldier is structurally distinct from the other eight:

  - The other eight are WORKERS — each watches a specific operational
    surface (routes, file mtimes, processes, disk, log tails, table
    sizes, heartbeat, sanctum filesystem).

  - This ninth is the WITNESS — it watches the SWARM ITSELF. It reads
    recent Pheromone deposits to assess whether the swarm is operating
    healthily (depositors per class within window, intensity-distribution
    skew, last-deposit-age per class). It deposits a meta-pheromone
    summarizing what it observes.

The witness gives the substrate *internal* self-knowledge. HYDRA's
ant_colony_watcher (external lens) still observes; the witness is
distinct because it deposits its observation INTO the substrate, where
correlations, decay, and the existing read-pipeline can pick it up.

This soldier is INFO-level by design. It does not page; it
contextualizes. The operator sees swarm-self-knowledge in the brief
without the witness ever raising an alarm. Alarms remain the domain
of HYDRA watchers and other soldiers.

Constitutional contract:
  - C1 / G1: read-only against Pheromone (does not write findings,
    only deposits its own meta-observation pheromone)
  - G6: does not import other soldier or commander modules; queries
    Pheromone via the connection layer like any soldier
  - Statelessness: each .observe() call is fresh; no cached state
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Any

from polaris_swarm.soldiers.base import (
    Observation,
    Soldier,
    KIND_INFO,
)


class SwarmWitnessSoldier(Soldier):
    NAME = "soldier_swarm_witness"
    DESCRIPTION = "the priest tier — observes swarm-internal health by reading recent Pheromone deposits"
    INTENSITY = 0.6
    NODE_PREFIX = "witness:swarm"

    # Window for "recent" deposits used in the witness summary.
    WINDOW_HOURS = 1.0

    # The eight workers under observation. The witness itself is NOT
    # in this list (a witness watching itself would be recursion, not
    # observation). When new worker soldiers are added, this list grows.
    OBSERVED_WORKERS: tuple[str, ...] = (
        "soldier_route_pinger",
        "soldier_file_mtime",
        "soldier_process_alive",
        "soldier_disk_usage",
        "soldier_log_tail",
        "soldier_db_table_size",
        "soldier_heartbeat_freshness",
        "soldier_sanctum_freshness",
    )

    def observe(self) -> list[Observation]:
        # Connect via the same env vars the colony uses (graceful no-op
        # if DB unavailable — the witness should not block on infra).
        try:
            import psycopg2  # type: ignore
        except ImportError:
            return [Observation(
                node_id=f"{self.NODE_PREFIX}:db_offline",
                value={"reason": "psycopg2_missing", "observed_workers": 0},
                kind=KIND_INFO,
            )]

        try:
            conn = psycopg2.connect(
                host=os.environ.get("POLARIS_DB_HOST", "localhost"),
                dbname=os.environ.get("POLARIS_DB_NAME", "polaris_test"),
                user=os.environ.get("POLARIS_DB_USER", os.environ.get("USER", "polaris_app")),
                password=os.environ.get("POLARIS_DB_PASSWORD", ""),
                connect_timeout=2,
            )
        except Exception:  # noqa: BLE001
            return [Observation(
                node_id=f"{self.NODE_PREFIX}:db_offline",
                value={"reason": "connect_failed", "observed_workers": 0},
                kind=KIND_INFO,
            )]

        try:
            cur = conn.cursor()
            cutoff = datetime.now(timezone.utc) - timedelta(hours=self.WINDOW_HOURS)
            cur.execute(
                """
                SELECT deposited_by, COUNT(*), MAX(deposited_at), AVG(intensity)
                  FROM Pheromone
                 WHERE deposited_at >= %s
                   AND deposited_by IN %s
                 GROUP BY deposited_by
                """,
                (cutoff, self.OBSERVED_WORKERS),
            )
            rows = cur.fetchall()
            cur.close()
        except Exception:  # noqa: BLE001
            try:
                conn.close()
            except Exception:  # noqa: BLE001
                pass
            return [Observation(
                node_id=f"{self.NODE_PREFIX}:query_error",
                value={"reason": "pheromone_query_failed"},
                kind=KIND_INFO,
            )]
        finally:
            try:
                conn.close()
            except Exception:  # noqa: BLE001
                pass

        # Build per-worker map; absent workers are silent in the window.
        seen: dict[str, dict[str, Any]] = {}
        for depositor, count, last, avg_int in rows:
            seen[depositor] = {
                "deposits": int(count),
                "last_age_minutes": round(
                    (datetime.now(timezone.utc) - last).total_seconds() / 60.0, 2
                ),
                "avg_intensity": round(float(avg_int), 3),
            }

        silent = [w for w in self.OBSERVED_WORKERS if w not in seen]
        active_count = len(seen)
        silent_count = len(silent)

        # Aggregate health verdict (INFO regardless; witness does not page)
        if silent_count == 0:
            verdict = "all-active"
        elif silent_count <= 2:
            verdict = "minor-silence"
        elif silent_count <= 5:
            verdict = "majority-silence"
        else:
            verdict = "swarm-quiet"

        observations = [Observation(
            node_id=f"{self.NODE_PREFIX}:health",
            value={
                "verdict": verdict,
                "active_workers": active_count,
                "silent_workers": silent_count,
                "window_hours": self.WINDOW_HOURS,
                "silent_classes": silent,
            },
            kind=KIND_INFO,
        )]

        # Per-worker observation under a sub-prefix; gives operators
        # a queryable surface for any specific worker's recent deposit
        # cadence.
        for worker_name, info in seen.items():
            observations.append(Observation(
                node_id=f"{self.NODE_PREFIX}:worker:{worker_name}",
                value=info,
                kind=KIND_INFO,
            ))

        return observations
