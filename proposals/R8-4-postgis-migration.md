# proposals/R8-4-postgis-migration.md

**Risk class:** MEDIUM (propose-and-wait)
**Mission link:** Performance headroom; not on done-list
**Status:** PROPOSED — awaiting user approval

## Problem

At 100M+ events, the composite B-tree index on `(latitude, longitude)`
becomes the bottleneck for atlas queries. PostGIS provides a GiST
index over a `geography(Point)` column that materially outperforms
B-tree for spatial range queries at this scale.

## Why MEDIUM

PostGIS is a ~50MB extension that may not be available in every
deployment target (some managed Postgres providers gate it behind
paid tiers). Making it a hard dependency excludes those deployments.

## Recommended approach

**Optional dependency.** Schema works with or without PostGIS:

- If `CREATE EXTENSION IF NOT EXISTS postgis` succeeds, the schema
  adds a `geography(Point)` column and uses GiST.
- If not available, schema falls back to the current
  `(latitude, longitude)` B-tree.
- Atlas SQL functions check for the column at function-creation time
  and emit either the PostGIS-aware or the B-tree-aware variant.

Alternative: hard requirement on PostGIS. Rejected: excludes managed
DB tiers that VANTA may want to deploy on.

## Implementation sketch

1. New `polaris_sql/13_postgis.sql` (idempotent — runs both fresh
   install and migrations):
   - `CREATE EXTENSION IF NOT EXISTS postgis`
   - If extension created: `ALTER TABLE VerificationEvent ADD COLUMN
     geo geography(Point, 4326) GENERATED ALWAYS AS
     (ST_MakePoint(longitude, latitude)::geography) STORED`
   - `CREATE INDEX gix_verification_geo ON VerificationEvent USING
     GIST (geo) WHERE latitude IS NOT NULL`
2. Atlas SQL functions get a CASE branch on
   `EXISTS(SELECT 1 FROM pg_extension WHERE extname='postgis')`.
3. Performance benchmark:
   - 10M-row stress data
   - Cluster query at zoom-out (full world bbox, grid=10): record
     latency before/after.
   - Acceptance: ≥3× improvement at 10M+ events.

## Predicted blast radius

- New SQL file: `polaris_sql/13_postgis.sql` (~80 lines)
- Atlas functions: ~5 ALTER FUNCTION calls
- `00_load_all.sql`: + `\i 13_postgis.sql`
- `docs/DEPLOYMENT.md`: + PostGIS section
- No app code change (functions remain same signature).

## Acceptance criteria

- ✅ Schema loads cleanly with AND without PostGIS available
- ✅ With PostGIS: atlas at 10M+ events is ≥3× faster than B-tree
- ✅ Without PostGIS: behavior identical to current
- ✅ DEVNOTES/atlas-scaling.md updated
- ✅ Existing tests pass in both modes

## What this needs from you

"Yes do R8-4" plus a note on whether the test suite should run
PostGIS-mode by default or only on explicit opt-in. Recommendation:
opt-in (most contributors won't have PostGIS).
