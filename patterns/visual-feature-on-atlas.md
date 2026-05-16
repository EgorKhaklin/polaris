# patterns/visual-feature-on-atlas.md

## Trigger

- "add a filter chip", "new HUD signal", "different reticle for X"
- "atlas should show Y"
- file change touches `atlas-globe.js`, `atlas.html`, or any
  `atlas_*` SQL function

## Recipe

The Atlas v6 architecture is layered. Touch only the layers your
feature requires. The dependencies flow:

```
SQL function       11_atlas.sql
   ↓ called by
API endpoint       app.py /api/atlas/*
   ↓ consumed by
Frontend layer     atlas-globe.js (data wiring)
   ↓ rendered with
Visual treatment   polaris.css (.d3-globe-node tones, reticle ornaments)
   ↓ exposed in
Template DOM       atlas.html (HUD slots, filter chips, feed rail)
```

### 1. Decide which layer(s) the feature touches

| Feature | SQL | API | JS | CSS | HTML |
|---|---|---|---|---|---|
| New HUD signal (computed bbox-scoped) | yes | yes (extend stats) | yes | maybe | yes (slot) |
| New filter chip (server-side filtered) | yes (kind param) | yes | yes (kindForFilter) | maybe | yes (chip) |
| New reticle tone (alert variant) | no | maybe | yes (toneClass) | yes | no |
| New cluster-level diagnostic count | yes | yes | yes | maybe | no |
| Frontend-only refinement (animation) | no | no | yes | maybe | no |

### 2. SQL layer (if touching)

In `polaris_sql/11_atlas.sql`. The pattern for new aggregation:

```sql
CREATE OR REPLACE FUNCTION atlas_clusters_verifications(
    p_min_lat DOUBLE PRECISION, …, p_grid DOUBLE PRECISION
) RETURNS TABLE (
    lat DOUBLE PRECISION, lon DOUBLE PRECISION,
    n_total BIGINT,
    -- ADD HERE:
    n_my_thing BIGINT
) LANGUAGE sql STABLE AS $$
    SELECT avg(latitude), avg(longitude), count(*),
           count(*) FILTER (WHERE my_predicate) AS n_my_thing
    FROM …
$$;
```

Reload: `psql -d $DB -f polaris_sql/11_atlas.sql`. Then EXPLAIN ANALYZE
the function call against the 2M synthetic data — see
`patterns/scaling-investigation.md`.

### 3. API layer (if touching)

In `polaris_web/app.py`, `/api/atlas/*` endpoints. Extend the JSON
shape:

```python
return jsonify(
    …,
    clusters=[dict(r) for r in rows],   # the new column flows through
)
```

Test with curl. Add a row to the contract tests in
`AtlasAPITests.test_clusters_endpoint_returns_aggregated_bins` asserting
the new field is in each cluster.

### 4. Frontend (atlas-globe.js)

The data flows through `clusterToNode()` and `pointToNode()` (around
line 750+ in atlas-globe.js). Extend these to copy the new fields:

```javascript
function clusterToNode(c, kind) {
    return {
        // … existing …
        n_my_thing: c.n_my_thing || 0,
    };
}
```

If the feature involves a new tone, extend `isVisibleByFilter()`:

```javascript
if (activeFilter === 'my-filter') return d.n_my_thing > 0;
```

If it's a sub-filter chip applied client-side over server-fetched
data, the kind parameter stays the same. If it requires different
server-side filtering, add a new `kind` to `atlas_clusters_*`.

### 5. CSS (polaris.css)

If you're adding a tone, follow the existing pattern:

```css
.d3-globe-node.node-my-tone .reticle-ring { stroke: #my-color; }
.atlas-feed-row.tone-my-tone { border-left-color: #my-color; }
```

Tones currently available: `alert` (red), `full` (amber), `zk`
(cyan), `selective` (gray). Don't add a 5th tone unless the
operational distinction is real.

### 6. Template (atlas.html)

For HUD slots: add a `<span data-atlas-my-signal>` and the JS will
auto-populate it from the API response (extend `updateAtlasStats()`).

For filter chips: add a button with `data-atlas-filter="my-filter"`
in the toolbar. The existing listener wires it to `setFilter()`.

### 7. Test it visually

- Restart gunicorn, log in
- Snap a Playwright screenshot:
  ```python
  await page.goto("http://localhost:2222/atlas")
  await page.wait_for_timeout(5000)  # let the cluster fetch land
  await page.screenshot(path="/tmp/atlas_check.png")
  ```
- Eyeball the result. Layout collisions, color contrast, label overlap.

### 8. Test programmatically

- AtlasAPITests for the API contract change
- ClusterCorrectnessTests if you added an aggregate count (it must
  match raw SQL)

## Pre-known gotchas

- **`isVisibleByFilter` was the bug that hid clusters in v6.** Server-side
  filtering happens via the `kind` API parameter; client-side filter
  chips refine, they don't replace. For cluster nodes, default to
  `return true` and only filter on diagnostic counts (n_failure>0,
  n_pq>0).

- **The d3 enter/update/exit pattern is in `renderNodes()`.** New
  visual elements per node go inside the `enter.each(function(d) {…})`
  block. Existing nodes get re-positioned via `nodeSelection.each` in
  `redraw()`.

- **CSS for `.reticle-cluster-count`** uses fill, not color, because
  it's an SVG `<text>` element. Same for stroke vs border on
  `.reticle-ring`.

- **The HUD updates on every API fetch via `updateAtlasStats()`.**
  Server-rendered initial values get overwritten as soon as the first
  fetch lands. Don't rely on the Jinja template values for accuracy.

- **The event feed has infinite scroll** — adding entries means
  hooking into the cursor pagination, not just appending to the rail.

## Completion check

- [ ] All touched layers have corresponding test coverage
- [ ] EXPLAIN ANALYZE confirms no new perf cliff at 2M scale
- [ ] Screenshot taken and eyeballed for collision/contrast
- [ ] No CSP violations in the browser console
- [ ] Changelog entry under current version
