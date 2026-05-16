"""soldier_db_table_size — single COUNT(*) for top tables.

Cheap O(estimated-rows) query via pg_class.reltuples (planner stats);
doesn't actually count. Reports estimated row counts for the
high-volume audit-class tables. INFO-level.

Note: pg_class.reltuples is updated by VACUUM/ANALYZE; on a fresh DB
the value may be -1 ("unknown"). The soldier reports unknown as
value=null (not an alert).
"""
from __future__ import annotations

import os
from typing import Any

from polaris_swarm.soldiers.base import (
    Observation,
    Soldier,
    KIND_INFO,
)

# Tables whose growth is operationally interesting
WATCHED_TABLES: tuple[str, ...] = (
    "tokenlifecycleevent",
    "verificationevent",
    "authauditlog",
    "pheromone",
    "schema_version",
)


class DbTableSizeSoldier(Soldier):
    NAME = "soldier_db_table_size"
    DESCRIPTION = "Estimated row counts for high-volume audit-class tables"
    INTENSITY = 1.0
    NODE_PREFIX = "infra:db_tables"

    def observe(self) -> list[Observation]:
        try:
            import psycopg2
        except ImportError:
            # Without psycopg2 the soldier is a no-op (graceful-fail)
            return []

        host = os.environ.get("POLARIS_DB_HOST", "localhost")
        name = os.environ.get("POLARIS_DB_NAME", "polaris_test")
        user = os.environ.get("POLARIS_DB_USER", "vanta")
        password = os.environ.get("POLARIS_DB_PASSWORD", "")

        try:
            conn = psycopg2.connect(
                host=host, dbname=name, user=user,
                password=password, connect_timeout=2,
            )
        except Exception:
            return []

        out: list[Observation] = []
        try:
            with conn.cursor() as cur:
                for table in WATCHED_TABLES:
                    try:
                        cur.execute(
                            "SELECT reltuples::bigint FROM pg_class "
                            "WHERE relname = %s AND relkind = 'r'",
                            (table,)
                        )
                        row = cur.fetchone()
                    except Exception:
                        continue
                    estimated: Any = None
                    if row is not None and row[0] is not None and row[0] >= 0:
                        estimated = int(row[0])
                    out.append(Observation(
                        node_id=f"{self.NODE_PREFIX}:{table}",
                        value={"estimated_rows": estimated},
                        kind=KIND_INFO,
                    ))
        finally:
            conn.close()
        return out
