# patterns/scaling-investigation.md

## Trigger

- "X is slow", "p95 latency too high"
- "EXPLAIN", "query plan"
- "OOM", "browser hangs"
- "1M rows", "2M users", "doesn't scale"
- A new table is approaching 100K+ rows

## Recipe

### 1. Establish the baseline

Don't optimize blind. Get a number first.

```bash
# For a SQL function or query:
psql -d $DB -c '\timing on' -c 'SELECT * FROM thing(args)'

# For an HTTP endpoint:
START=$(date +%s%N); curl -s -b "$JAR" "http://localhost:2222/api/X"; \
  END=$(date +%s%N); echo "$(( (END-START)/1000000 ))ms"
```

Record the number. **Run it 3 times** — first run is cold cache,
subsequent are warm. The number that matters is warm.

### 2. EXPLAIN ANALYZE — find where time goes

```sql
EXPLAIN (ANALYZE, BUFFERS) SELECT … FROM thing WHERE …;
```

Read the output bottom-up. Look for:

- **Seq Scan on big_table** with high actual time → missing index
- **Hash Join** with large right side → join is materializing too much
- **Sort … rows=2000000** before LIMIT → sort happens before slice;
  rewrite as top-N + late join
- **CTE Scan … (× N times)** → CTE re-scanned; switch to single-pass
  aggregate or materialize explicitly
- **JIT … Total: NN ms** → JIT itself is taking time; use SET
  jit=off if the query is fast enough without it

### 3. Pick the architectural fix

Common shapes:

| Symptom | Fix |
|---|---|
| Seq scan on bbox query | Composite index on (col1, col2), partial on `WHERE col1 IS NOT NULL` |
| Top-N over 2M rows | Two-stage: index-driven top-N from each source, JOIN metadata only for the result rows |
| Aggregating 8 things from same table | Single pass with FILTER aggregates: `count(*) FILTER (WHERE cond)` |
| HTML table with 2M rows | Pagination at the route. Hard cap page_size. |
| JSON payload >MB | Server-side aggregation (cluster summaries instead of individual rows) |
| Repeated identical queries | API-layer cache keyed by query parameters |

### 4. Verify the improvement

Run the same baseline command 3 times again. The improvement should be
**at least 3×** to justify shipping. Sub-3× wins are usually the
optimizer's work, not yours.

### 5. Document the rewrite

- Add benchmark numbers (before / after) to `docs/reference/SCALING.md`
- Add a comment IN THE FUNCTION explaining what the previous
  implementation did and why it was slow. Future me will edit this and
  needs to know why it's structured this way.

### 6. Add the regression check

- A test in `ClusterCorrectnessTests` (or appropriate class) that
  asserts the function still returns correct results after the rewrite
- A note in `DEVNOTES/atlas-scaling.md` "What NOT to change without
  measuring first"

## Pre-known gotchas

- **`ANALYZE` is not free at scale** but you must run it after bulk
  inserts. Without fresh stats, the planner picks bad plans.
  `ANALYZE table_name;` on the affected table is enough; full
  `VACUUM ANALYZE` is overkill.

- **PostgreSQL chooses Parallel Seq Scan over Index Scan** when the
  bbox is wide enough that "scan everything" is cheaper than "skip
  rows via index." This is correct behavior — don't fight it. The
  index exists for tight bboxes, not wide ones.

- **CTEs aren't always materialization fences** in pg14+. Postgres
  inlines simple CTEs unless they're referenced multiple times. If you
  rely on CTE materialization, force it: `WITH x AS MATERIALIZED (…)`.

- **Hard caps protect the wire AND the renderer.** Even if the SQL is
  fast, a 100MB JSON response will OOM the browser and saturate the
  connection. Cap server-side at the API layer.

- **Deep OFFSET is O(offset).** `OFFSET 1000000` scans past 1M rows.
  Page 1 might be 10ms; page 10000 might be 13s. Use cursor pagination
  (WHERE col < last_seen_value) for deep pagination.

- **Don't optimize the first thing you find.** Run EXPLAIN ANALYZE,
  list the top 3 cost centers, and fix them in cost order. The cheapest
  optimization isn't always the one with the highest absolute cost.

## Completion check

- [ ] Before/after numbers measured (not estimated)
- [ ] At least 3× improvement
- [ ] EXPLAIN ANALYZE plan no longer shows the original bottleneck
- [ ] Correctness test added/passes
- [ ] `docs/reference/SCALING.md` updated with the new numbers
- [ ] Comment in the rewritten function explains the previous
      implementation and why it was slow
