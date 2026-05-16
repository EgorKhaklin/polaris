# patterns/add-sql-aggregation.md

## Trigger

- "summary count", "aggregate", "cluster", "rollup"
- "histogram", "distribution", "by category"
- "top N", "leaderboard"
- A new metric that needs to scan a large table for the right answer

## Recipe

### 1. Decide where the aggregation lives

| Location | When |
|---|---|
| **SQL function** in `11_atlas.sql` (or new `12_*.sql`) | Used by multiple endpoints, or the planner needs STABLE for plan caching |
| **Inline `query()` in `app.py`** | Used by exactly one endpoint, simple enough to read |
| **Materialized view** | The result is reused many times per second AND the underlying data is slowly-changing |
| **Triggers updating a counter table** | Hot-read, hot-write — when even a single SELECT count(*) is too expensive |

For Polaris: anything that aggregates across the 2M `VerificationEvent` table goes into a STABLE function so the planner caches the plan and the GROUP BY happens in the database, not the network.

### 2. Pick the aggregation technique

| Pattern | When |
|---|---|
| `count(*) FILTER (WHERE …)` | Multiple counts over the same scan — single-pass |
| `count(DISTINCT col)` | Unique cardinality (slower than `count(*)`) |
| `array_agg(…)` / `string_agg(…)` | Pivot rows into a single output |
| `GROUP BY floor(x/grid)` | Spatial / temporal binning |
| `WITH cte AS (… top N …) SELECT FROM cte JOIN big USING(id)` | Two-stage top-N with late metadata join |

The single-pass FILTER pattern is the v6 win for `atlas_stats` (1428ms→511ms). Use it whenever you have multiple counts over the same predicate base.

### 3. Skeleton

```sql
-- Single-pass aggregation over a bounded subset
CREATE OR REPLACE FUNCTION atlas_my_aggregation(
    p_min_lat DOUBLE PRECISION, p_min_lon DOUBLE PRECISION,
    p_max_lat DOUBLE PRECISION, p_max_lon DOUBLE PRECISION
) RETURNS TABLE (
    n_total      BIGINT,
    n_failure    BIGINT,
    n_pq         BIGINT,
    pct_failure  NUMERIC
) LANGUAGE sql STABLE AS $$
    SELECT
        count(*)                                             AS n_total,
        count(*) FILTER (WHERE outcome = 'FAILURE')          AS n_failure,
        count(*) FILTER (WHERE qr_token)                     AS n_pq,
        ROUND(100.0 * count(*) FILTER (WHERE outcome='FAILURE')
                    / NULLIF(count(*), 0), 1)                AS pct_failure
    FROM (
        SELECT ve.outcome,
               COALESCE(ca.quantum_resistant, FALSE) AS qr_token
        FROM   VerificationEvent ve
        LEFT JOIN IdentityToken t  ON ve.token_id = t.token_id
        LEFT JOIN CryptographicAlgorithm ca ON t.algorithm_id = ca.algorithm_id
        WHERE  ve.latitude  IS NOT NULL
          AND  ve.longitude IS NOT NULL
          AND  ve.latitude  BETWEEN p_min_lat AND p_max_lat
          AND  ve.longitude BETWEEN p_min_lon AND p_max_lon
    ) src;
$$;
```

Note the inner SELECT pulls the join data ONCE, then the outer FILTERs read from that single materialized scan. Without this, multiple `count(*) FILTER` clauses can confuse the planner into multi-pass.

### 4. Two-stage top-N (when the table has 1M+ rows)

```sql
CREATE OR REPLACE FUNCTION atlas_recent_my_thing(p_limit INT)
RETURNS TABLE (id INT, ts TIMESTAMPTZ, label TEXT)
LANGUAGE sql STABLE AS $$
    -- Stage 1: index-driven top-N (cheap)
    WITH top_ids AS (
        SELECT id, ts FROM BigTable
        ORDER BY ts DESC, id DESC
        LIMIT p_limit
    )
    -- Stage 2: late metadata join (only over the result rows)
    SELECT t.id, t.ts, m.label
    FROM   top_ids t
    JOIN   MetadataTable m ON m.id = t.id
    ORDER  BY t.ts DESC, t.id DESC;
$$;
```

The trick: the JOIN happens AFTER the LIMIT, not before. Putting the JOIN before the LIMIT forces the planner to materialize all matched rows then sort, which kills perf at 2M scale. This was the v6 `atlas_recent_events` rewrite — 5919ms→2ms.

### 5. EXPLAIN ANALYZE before shipping

Always run against representative data — not against the 17-row sample.

```bash
psql -d polaris_test -c "EXPLAIN (ANALYZE, BUFFERS) SELECT * FROM atlas_my_aggregation(20, -130, 50, -65);"
```

Look for:
- `Seq Scan` on the big table when `Index Scan` was expected → check WHERE clauses match an existing index
- `Sort` rows = millions before LIMIT → you have a join-before-sort that needs the two-stage rewrite
- `Buffers: shared hit=N read=M` — read=M means cold cache, run twice; the second number matters
- `Planning Time` > `Execution Time` — your function is too cheap to be in SQL; inline it in the app

### 6. Test it

In `test_app.py`, add a `ClusterCorrectnessTests`-style test that compares the aggregate to a hand-rolled count:

```python
def test_my_aggregation_total_matches_raw(self):
    with self._connect() as conn, conn.cursor() as cur:
        cur.execute("SELECT n_total FROM atlas_my_aggregation(20, -130, 50, -65)")
        agg_total = cur.fetchone()['n_total']
        cur.execute("""SELECT count(*) AS s FROM VerificationEvent
                       WHERE latitude BETWEEN 20 AND 50
                         AND longitude BETWEEN -130 AND -65""")
        raw_total = cur.fetchone()['s']
        self.assertEqual(agg_total, raw_total)
```

This catches off-by-one in the binning, predicate drift, and JOIN explosion.

### 7. Document

- Append a row to the table in `DEVNOTES/atlas-scaling.md` under "What's in 11_atlas.sql"
- Add measured latency to `docs/reference/SCALING.md` under "Performance at 2M scale"
- CHANGELOG one-liner under current version

## Pre-known gotchas

- **STABLE means deterministic given inputs and data state.** No `CURRENT_TIMESTAMP` (use a parameter), no `random()`, no setvars. STABLE allows the planner to inline + cache; VOLATILE prevents it.

- **`NULLIF(count(*), 0)`** prevents division-by-zero when the bbox is empty. Without it, your function returns NULL for an empty bbox; the API layer must handle that.

- **Don't aggregate over JOIN before the JOIN is filtered.** A LEFT JOIN to a large table inside an aggregate is cheap (good); a CROSS JOIN you forgot is catastrophic at 2M.

- **`count(*) FILTER (WHERE x)` and `sum(CASE WHEN x THEN 1 ELSE 0 END)` are equivalent but FILTER is clearer.** Both produce the same plan in pg14+.

- **The result of `floor(x / grid) * grid`** is the bin's lower bound, not the bin label. Use it for grouping, not for display. For display, use `avg(x)` (centroid) or `floor(x/g)*g + g/2` (bin center).

- **`ANALYZE` after bulk inserts.** Without fresh stats, the planner picks bad plans. After `_stress_seed.sql` finishes, you must `ANALYZE VerificationEvent` (the seed script does this; remember if you generate data manually).

## Completion check

- [ ] Function is STABLE (no side effects, no time-dependent fns)
- [ ] Single-pass FILTER pattern used if multiple counts over same scan
- [ ] Two-stage top-N if pulling top results from 1M+ table
- [ ] EXPLAIN ANALYZE inspected; no obvious cost drivers
- [ ] Correctness test (compares to raw count) added
- [ ] Latency added to `docs/reference/SCALING.md`
- [ ] DEVNOTES/atlas-scaling.md table updated
- [ ] CHANGELOG entry
