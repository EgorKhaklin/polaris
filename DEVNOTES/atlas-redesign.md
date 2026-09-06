# Atlas redesign (roadmap P2.3)

The sub-roadmap for rebuilding the Atlas as an analytical console. One ship per
version, tracked here. Written 2026-09-06 (at v9.247).

## The thesis

Today the Atlas is a globe you look at: an always-on MapLibre canvas of
server-clustered event bubbles. At national scale the bubbles read as
overlapping "40k" circles that convey little, the individual-point view plots
notional coordinates, and the geographic surface dominates a page whose real
job is operational insight.

The Atlas should be an analytical console you ask questions of. The geographic
map is one tool inside it, kept where it genuinely earns its place: a scalable
"where" view by jurisdiction, a drill into a single region, and above all the
per-subject investigation map (a handful of interpretable points, which is what
a map is actually good at). The globe stops being the front door.

## The production-readiness spine

One rule makes it scale: every default view is a bounded, server-side
aggregate. Time buckets, category counts, region counts, top-K. The browser
never receives more than a few hundred rows regardless of ledger size. This
extends the existing C8 caps rather than fighting them, and it is why the views
survive the 2M-row stress set (30 global clusters, 90 days, ~40% zero-knowledge
and unmappable) and 10M beyond it.

Invariants held throughout:
- **C8** (bounded results): every aggregate is capped; the cap constants are
  named in `app.py` and pinned by `check_c8_atlas_caps`.
- **C6** (zero-knowledge is counted, never located): ZK verifications
  contribute to volume and disclosure-mix figures but are never plotted or
  attributed to a subject. This is a feature, not a limitation: "40% of
  activity is zero-knowledge and unmappable" is the privacy posture on display.
- **C5** (no inline scripts): charts are hand-rolled inline SVG and CSS bars
  (the pattern already in the repo), self-hosted. No CDN, no new dependency, no
  weakening of `script-src 'self'`.

## Decisions (locked 2026-09-06)

- **Default view: Overview** (analytical at-a-glance). The globe is demoted to a
  tab.
- **Geography: region choropleth + drill.** The scalable "where" is
  jurisdictional distribution (which states and agencies carry elevated
  activity or failure), O(regions). Click a region to drill into the MapLibre
  point map; the globe stays for per-subject journeys and as a toggle.
- **Aesthetic: aligned with the v9.238 operations dashboard.** One clean
  operator design language across both surfaces; reuse its KPI-tile and CSS-bar
  primitives. Drop the cockpit theatrics (fake HDG/PIT/ZM readouts, the
  waveform, SPIN). Keep the operational density the Atlas needs.

## The console (view modes)

| View | Answers | Scale |
|---|---|---|
| **Overview** (default) | How is it doing right now? | Hero volume time-series (success vs failure) + KPI cards with sparklines + top agencies / contexts / disclosure mix | ≤240 buckets, top-K |
| **Trends** | What are the patterns over time? | Stack-by-dimension series + an hour-by-weekday activity heatmap | ≤168 cells |
| **Breakdown** | Which slice is anomalous? | Categorical bars + cross-tabs (failure rate by agency, disclosure by context) | top-K per dimension |
| **Map** | Where is activity / failure? | Region choropleth by jurisdiction; drill to MapLibre points; globe a toggle | O(regions) |
| **Feed** | What is happening live? | The existing event stream + detail panel | keyset, ≤500 |
| **Subject** (contextual) | What has this person done? | The per-subject journey map + timeline + summary; opened from search or a token page | one subject |

Shared: a slim toolbar (stream, window, filters) reusing the existing filter
state machine.

## What already exists (reuse)

- Bounded time-series (`atlas_timeline`, ≤240 buckets) and its endpoint.
- Single-pass stats (`atlas_stats`: active tokens, anomalies, failures, full,
  pq_pct, zk_pct, verifs, lifecycles).
- The subject-investigation API (`atlas_subjects/search`, `atlas_subject`) and
  the journey renderer in `atlas-map.js`.
- The fetch/debounce/filter state machine, the event feed + detail panel, the
  inline-SVG histogram primitive, MapLibre (self-hosted).

## What is new (small, bounded)

- SQL aggregates in `11_atlas.sql` (reach upgraded DBs via `--sync-objects`, no
  migration): `atlas_breakdown` (top-K by dimension), a stacked-timeseries
  variant, an hour-by-weekday heatmap, a by-jurisdiction aggregate.
- Their capped `/api/atlas/*` endpoints, new cap constants, and C8-check
  coverage.
- A compact SVG chart module (`atlas-charts.js`): sparkline, area/line series,
  bars, stacked bar, heatmap grid, choropleth.

## Ships

| Ship | Version | Scope | Status |
|---|---|---|---|
| 1 | v9.248 | Console shell + Overview view (default); globe and feed become tabs; `atlas_breakdown` aggregate; SVG chart module; aesthetic cleanup | in progress |
| 2 | v9.249 | Breakdown view (categorical composition + cross-tabs) | planned |
| 3 | v9.250 | Map redesign (region choropleth default + region drill + globe toggle) | planned |
| 4 | v9.251 | Trends view (stack-by-dimension series + hour-by-weekday heatmap) | planned |
| 5 | v9.252 | Subject investigation promoted (timeline + summary, "open in Atlas" from token pages) + docs rewrite (`atlas-scaling.md` into a full `atlas.md`) + e2e/benchmark updates | planned |

The order after ship 1 is adjustable. PostGIS at 10M (the original P2.3 scope)
remains a sub-item, gated on a PostGIS environment and a 10M dataset to measure
the threefold win; it is orthogonal to this UX rebuild.
