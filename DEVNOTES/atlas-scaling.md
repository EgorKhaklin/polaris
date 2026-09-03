# DEVNOTES/atlas-scaling.md

The scaling story in 60 lines. Full treatment in `docs/reference/SCALING.md`.

---

## Why the architecture is what it is

Atlas at 1M+ events cannot send the data to the browser: payload is
gigabytes. The fix is server-side spatial aggregation: the browser
sends the visible bounding box, the server returns at most a few
hundred cluster summaries (centroid + counts), the browser renders
those instead of individual events. When the user zooms close enough
that the cluster count drops to a renderable handful (≤ 30), the
client switches to fetching individual points.

## Data path

```
viewport rotation/zoom changes in browser
  → atlas-globe.js scheduleFetch() (debounced 220ms)
    → currentBbox() derives [min_lat, min_lon, max_lat, max_lon]
    → chooseGrid(zoom) maps zoom level to grid cell size in degrees
    → GET /api/atlas/clusters?bbox=…&grid=…&kind=…
      → Flask app.py validates + caps
        → SQL atlas_clusters_verifications(...)
          → uses idx_verificationevent_geo for bbox filter
          → GROUP BY floor(lat/grid), floor(lon/grid)
          → returns ≤ 5000 rows
      → JSON response
    → renderNodes() updates d3 selection (enter/update/exit)
    → if count ≤ 30 and zoom ≥ 2:
        → second fetch: GET /api/atlas/points
        → renderNodes() with individual reticle ornaments
  → HUD signals updated from /api/atlas/stats (parallel fetch)
```

## What's in 11_atlas.sql

Six STABLE functions. STABLE = same input + same data → same output, no
side effects. PostgreSQL caches plans for STABLE functions.

| Function | Purpose | Worst-case at 2M |
|---|---|---|
| `atlas_clusters_verifications(bbox, grid)` | Aggregated bins, verification kind | 1.2 s whole world |
| `atlas_clusters_lifecycles(bbox, grid)` | Aggregated bins, lifecycle kind | <100 ms (small table) |
| `atlas_points_verifications(bbox, limit)` | Individual events, top-N by recency | 35 ms metro bbox |
| `atlas_points_lifecycles(bbox, limit)` | Individual lifecycle, top-N | <50 ms |
| `atlas_stats(bbox)` | HUD signals, single-pass aggregation | 511 ms |
| `atlas_recent_events(cursor_ts, cursor_id, limit)` | Paginated unified feed | 2 ms (top-N + late join) |

## API contract

All four `/api/atlas/*` endpoints:
- Require `@security.login_required`
- Accept `bbox=min_lat,min_lon,max_lat,max_lon` decimal degrees
- Validate via `_parse_bbox()` (see app.py)
- Return JSON: `{ kind, bbox, count, [clusters|points|events] }`
- Hard-capped: clusters ≤ 5000, points ≤ 2000, events ≤ 500

## Antimeridian (supported as of v7)

`_parse_bbox()` accepts bboxes where `min_lon > max_lon`. Atlas SQL
functions use a wrap-aware predicate of the form:

```sql
(p_min_lon <= p_max_lon AND longitude BETWEEN p_min_lon AND p_max_lon)
OR (p_min_lon  > p_max_lon AND (longitude >= p_min_lon OR longitude <= p_max_lon))
```

PostgreSQL's planner uses bitmap OR over the partial geo indexes, so
performance is comparable to non-wrapping bboxes.


## What NOT to change without measuring first

1. **The grid sliding scale in `chooseGrid(zoom)`.** It was tuned by
   eyeball against real distributions; smaller grids = more clusters =
   more rendering work. Don't make it finer without checking pan/zoom
   responsiveness.

2. **The cluster→point switchover thresholds (count ≤ 30 AND zoom ≥ 2).**
   Switching too early shows hundreds of point reticles which is
   slower than clusters.

3. **The 220ms debounce.** Below 150ms the API gets hammered during a
   smooth pan. Above 400ms feels laggy.

4. **The hard caps (5000 / 2000 / 500).** They're not arbitrary:
   above these, JSON serialization and DOM updates begin to dominate
   render time.

## Performance regression checks

Run these and compare to the table in docs/reference/SCALING.md:

```bash
# After loading stress data:
psql -d polaris_test <<'SQL'
\timing on
SELECT count(*) FROM atlas_clusters_verifications(-90,-180,90,180,10);
SELECT count(*) FROM atlas_clusters_verifications(20,-130,50,-65,5);
SELECT * FROM atlas_stats(20,-130,50,-65);
SELECT count(*) FROM atlas_recent_events(NULL,NULL,50);
SQL
```

Target latencies (warm cache, 2M events):
- clusters whole-world: <1500 ms
- clusters continent: <800 ms
- stats: <600 ms
- recent_events: <10 ms

If any are 2× off, run `EXPLAIN ANALYZE` and check whether an index
got dropped or whether the planner picked a seq scan when an index
scan was expected.

## PostGIS-optional scaling path (v8.88 / R8-4)

The default schema uses composite B-tree indexes on
`(latitude, longitude)` for atlas spatial queries. B-tree starts to
break down past ~10M events because the index doesn't model
2-dimensional proximity natively: a bbox query degrades toward a
range scan over one dimension.

**v8.88 ships an optional PostGIS migration** (`polaris_sql/13_postgis.sql`)
that, when the `postgis` extension is available, adds a generated
`geography(Point, 4326)` column to `VerificationEvent` and
`TokenLifecycleEvent` plus a GiST index on each. GiST models 2D
proximity correctly; bbox + radius queries return a logarithmic
fraction of the index instead of a linear scan.

### When the PostGIS path is active

```sql
-- Detect mode
SELECT EXISTS (SELECT 1 FROM pg_extension WHERE extname='postgis') AS postgis_loaded;
```

When `postgis_loaded` is `t`, two new columns + indexes exist:

| Table | Column | Index | Type |
|---|---|---|---|
| `VerificationEvent` | `geo geography(Point, 4326)` (generated, stored) | `gix_verification_geo` | GiST |
| `TokenLifecycleEvent` | `geo geography(Point, 4326)` (generated, stored) | `gix_lifecycle_geo` | GiST |

The columns are `GENERATED ALWAYS AS (... STORED)` from
`(latitude, longitude)` so they stay in sync without app-code
changes.

### Sample GiST-aware query (operator-side)

The application-layer atlas functions (`atlas_clusters_*`,
`atlas_points_*`, etc.) still use the B-tree path until a v8.x
follow-up ship rewrites them: that rewrite is gated on a
PostGIS-enabled environment plus a 10M-event benchmark dataset
where the ≥3× R8-4 acceptance criterion can be measured. Until
then, operators can hand-query the GiST index:

```sql
-- All verifications within 50km of Pittsburgh
SELECT event_id, event_timestamp, latitude, longitude
FROM VerificationEvent
WHERE geo IS NOT NULL
  AND ST_DWithin(
          geo,
          ST_SetSRID(ST_MakePoint(-79.9959, 40.4406), 4326)::geography,
          50000   -- meters
      );
```

### When NOT to enable PostGIS

- The extension is ~50MB and gated behind paid tiers on some
  managed Postgres providers (RDS Free Tier, some Aiven plans,
  etc.). The B-tree fallback is operationally complete for
  deployments below ~5M events.
- If the operator has a non-superuser deployment role and no path
  to run `CREATE EXTENSION postgis` once, the v8.88 script emits a
  NOTICE and falls back to B-tree gracefully.

### Phase 2 (deferred, v8.x)

The atlas SQL functions will gain a CASE branch on
`EXISTS(SELECT 1 FROM pg_extension WHERE extname='postgis')` and
emit either the GiST or B-tree path at function-call time. The
acceptance criterion (≥3× improvement at 10M+ events) is verified
by running `scripts/polaris-load-test.sh` against the rewritten
functions in both modes. R8-4 Phase 2.
