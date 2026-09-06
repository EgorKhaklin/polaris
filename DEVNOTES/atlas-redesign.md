# Atlas redesign (roadmap P2.3): the operational intelligence workspace

The sub-roadmap for rebuilding the Atlas into a professional, scale-ready
analytical console. Rewritten 2026-09-06 (at v9.249) after direction to raise
the bar to Palantir / TradingView grade. One ship per version, tracked here.

## The bar (VANTA's standing directive, 2026-09-06)

The whole thing must feel **professional, real, and production-ready**: software
a national authority actually operates, not a demo or a game HUD. See the
`ui-quality-bar` memory. Concretely:

- **Palantir-grade investigation, TradingView-grade analytics.** Real tools,
  options, configurability; coordinated, cross-filtered panels; saved state;
  entity-centric drill-down.
- **Scale-first.** Designed for millions of tokens and thousands-plus of
  agencies. Never a flat dump or a single giant table (a clutter nightmare).
  Every view is a bounded server aggregate; every list is searchable and
  server-paginated/virtualized; every entity filter is a typeahead.
- **Professional aesthetic.** A real design system (type scale, spacing grid,
  muted operational palette, principled data-viz color scales). Drop the
  game-y styling (neon glows, reticles, waveform/cockpit theatrics).
- **Well organized, nothing cut off.** Clear IA, progressive disclosure, clean
  overflow/scroll. Dense but legible.
- **No corners cut.** Use current tools and techniques. This takes many ships
  to complete correctly; quality over speed.

## What v9.249 exposed (why the bar had to rise)

At 54 agencies the console already broke down: the Breakdown became a flat 30+
row list that pushed the cross-tabs off-screen; the agency filter was an endless
chip flyout running past the viewport and occluding the feed; the map returned
to overlapping count bubbles. None of it survives thousands of agencies. The
Overview and Breakdown are sound *ideas* built on a foundation that is neither
scale-ready nor professional. This arc fixes the foundation, then builds the
advanced surfaces on it.

## The vision

The Atlas is Polaris's **operational intelligence workspace**: monitor and
investigate identity activity across the whole system. Principles:

1. **One query state, many coordinated views.** A global faceted filter/query
   (time range, stream, and facets: agency, context, outcome, disclosure,
   jurisdiction, algorithm) drives every view. Selecting in one view filters
   all (linked, cross-filtered).
2. **Server-side everything, bounded.** Aggregates for summaries; cursor
   pagination + virtualization for detail; typeahead for entity pickers.
3. **Progressive disclosure.** Summary → breakdown → entity investigation.
4. **Configurable.** Saved filters/views; per-view options.

## Constitutional invariants (unchanged, held every ship)

C8 (bounded results: caps on every aggregate; pagination caps on every grid),
C6 (zero-knowledge counted but never located or attributed), C5 (no inline
scripts; charts and grids hand-built or self-hosted, CSP-clean).

## Ships

Done, on the old foundation (kept, then refit): Overview (v9.248),
Breakdown + cross-tabs (v9.249).

| Ship | Version | Scope | Status |
|---|---|---|---|
| 1 | v9.248 | Console shell + analytical Overview (default); globe→tab; `atlas_volume_series`/`atlas_breakdown`; SVG charts | done |
| 2 | v9.249 | Breakdown view: slice + cross-tabs shaded by row share; `atlas_crosstab` | done |
| 3 | v9.250 | **Breakdown scale-hardening.** The sliced-dimension list became a searchable, internally-scrolling explorer (server-side `p_search`, honest truncation footer) with the cross-tabs beside it, so it survives thousands of categories instead of a flat dump. (The wider professional design-system pass and the agency typeahead moved into ships 4-6, where the global filter and map are rebuilt anyway.) | done |
| 4 | v9.251 | **Global faceted filter foundation.** One persistent query state (stream / window / facets: context, outcome, disclosure, agency) drives the Overview + Breakdown; facet dropdowns with live counts (standard faceting); agency typeahead (`atlas_agency_facet`); removable filter chips + Clear all; per-view stream/window controls removed. (Click-any-category cross-filtering and the deeper design-system/de-game-ify pass carry into ships 5-6 with the data grid and map.) | done |
| 5 | v9.252 | **Scale data grid + entity omni-search + cross-filtering + design-system pass.** A reusable server-paginated, sortable, virtualized table (agencies / tokens / events) with typeahead; click-a-category-to-filter from any chart; the muted operational palette / type-space tokens / de-game-ify | next |
| 6 | v9.253 | **Map v2.** Region choropleth by jurisdiction (default) + hexbin density + drill to points; globe an option, not the default | planned |
| 7 | v9.254 | **Trends.** Multi-series time analysis (brush/zoom, crosshair, compare-to-previous), hour×weekday heatmap, stack-by-dimension | planned |
| 8 | v9.255 | **Investigate (entity workspace).** Search any entity (subject / agency / token) → linked timeline + geography + relations + activity; warrant- and agency-audit as a real entity view | planned |
| 9 | v9.256 | **Alerts + saved views + final production pass.** Surfaced needs-attention queries; saveable filter/view state; accessibility, responsive and 2M+ performance pass | planned |

Order after ship 3 is adjustable. The PostGIS-at-10M backend (original P2.3
scope) folds into ship 6. Every ship holds the bar above; none ships a flat
table, an unpaginated list, or a decorative flourish.

## Server aggregates so far (all bounded, non-geographic unless noted)

`atlas_volume_series`, `atlas_breakdown`, `atlas_crosstab` (see
[docs/design/atlas-scaling.md](../docs/design/atlas-scaling.md)). New ships add:
faceted-count endpoints, entity search + paginated grids, choropleth/hexbin,
multi-series time, entity-timeline, each capped and C6/C8-clean.
