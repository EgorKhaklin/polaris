// =============================================================================
// AI-context: viewport-aware globe driving the /atlas page. v6 architecture.
// Read before editing:
//     ../../docs/reference/SCALING.md                       (architectural treatment)
//     ../../DEVNOTES/atlas-scaling.md        (what NOT to change without measuring)
// Key entry points:
//     renderNodes()       — d3 enter/update/exit binding
//     isVisibleByFilter() — clusters bypass; points sub-filter
//     fetchData()         — debounced 220ms; AbortController cancels in-flight
//     chooseGrid(zoom)    — DON'T tighten without testing pan/zoom feel
// =============================================================================

/* Polaris Atlas Globe / Gotham profile
 *
 * Solid-shaded orthographic projection with rim halation, country labels,
 * crosshair reticle nodes, bracket framing on selection, drag inertia,
 * wheel zoom, and a HUD (heading / pitch / Z-time).
 *
 * Externals: window.d3, window.topojson.
 */
(function () {
    'use strict';

    var svgEl = document.getElementById('atlas-globe-svg');
    var dataEl = document.getElementById('atlas-globe-data');
    if (!svgEl || !dataEl || !window.d3 || !window.topojson) return;

    var container = svgEl.closest('.atlas-globe');
    var detail = document.getElementById('atlas-globe-detail');
    var headingEl = document.getElementById('atlas-hud-heading');
    var pitchEl = document.getElementById('atlas-hud-pitch');
    var timeEl = document.getElementById('atlas-hud-time');
    var zoomEl = document.getElementById('atlas-hud-zoom');

    // Atlas v6: data is fetched from /api/atlas/* on viewport changes.
    // The template no longer inlines all events (would be 300+ MB at 1M
    // verifications). The JS computes the visible bbox from the projection
    // rotation, picks a grid resolution proportional to zoom, and fetches
    // from /api/atlas/clusters or /api/atlas/points depending on density.
    var nodes = [];
    var renderMode = 'cluster';        // 'cluster' or 'point'
    var lastFetchKey = null;           // dedupe identical fetches
    var inflightFetch = null;          // current AbortController
    var fetchScheduled = null;         // setTimeout handle for debounce

    var svg = d3.select(svgEl);

    // ============================================================
    // SVG defs — rim halation filter, vignette gradient, land shade
    // ============================================================
    var defs = svg.append('defs');

    var rimFilter = defs.append('filter')
        .attr('id', 'atlas-rim-glow')
        .attr('x', '-40%').attr('y', '-40%')
        .attr('width', '180%').attr('height', '180%');
    rimFilter.append('feGaussianBlur')
        .attr('in', 'SourceGraphic').attr('stdDeviation', 4).attr('result', 'b1');
    rimFilter.append('feGaussianBlur')
        .attr('in', 'SourceGraphic').attr('stdDeviation', 12).attr('result', 'b2');
    rimFilter.append('feGaussianBlur')
        .attr('in', 'SourceGraphic').attr('stdDeviation', 24).attr('result', 'b3');
    var merge = rimFilter.append('feMerge');
    merge.append('feMergeNode').attr('in', 'b3');
    merge.append('feMergeNode').attr('in', 'b2');
    merge.append('feMergeNode').attr('in', 'b1');
    merge.append('feMergeNode').attr('in', 'SourceGraphic');

    var vignette = defs.append('radialGradient').attr('id', 'atlas-sphere-vignette')
        .attr('cx', '50%').attr('cy', '50%').attr('r', '50%');
    vignette.append('stop').attr('offset', '0%').attr('stop-color', '#0d141c');
    vignette.append('stop').attr('offset', '60%').attr('stop-color', '#070b12');
    vignette.append('stop').attr('offset', '100%').attr('stop-color', '#02050a');

    var landGrad = defs.append('radialGradient').attr('id', 'atlas-land-shade')
        .attr('cx', '50%').attr('cy', '42%').attr('r', '58%');
    landGrad.append('stop').attr('offset', '0%').attr('stop-color', '#2a3038');
    landGrad.append('stop').attr('offset', '70%').attr('stop-color', '#1c2129');
    landGrad.append('stop').attr('offset', '100%').attr('stop-color', '#0e1218');

    // Clip path so labels only render inside the disc
    defs.append('clipPath').attr('id', 'atlas-disc-clip')
        .append('circle').attr('class', 'atlas-disc-clip-circle');

    // ============================================================
    // Projection + state
    // ============================================================
    var projection = d3.geoOrthographic().clipAngle(90).precision(0.4);
    var path = d3.geoPath(projection);
    var graticule = d3.geoGraticule10();
    var landFeature = null;
    var countryFeatures = [];
    var width = 0, height = 0, baseRadius = 0, zoom = 1;

    // v8.3 (A+C): unified filter state. The toolbar UI elements drive this
    // object directly; serializeFilters() turns it into a query string for
    // the /api/atlas/* endpoints. Two coupled axes the user controls:
    //   view     — what the dots ARE (verification | lifecycle).
    //              "tokens" was historically a synonym for verification;
    //              we keep the label in the UI but treat both the same.
    //   window   — temporal lens; one of 1h | 24h | 7d | 30d | all.
    //   modifiers— boolean toggles applied on top of view+window. They
    //              translate to specific server params.
    //   contexts — multi-select VerificationContext values. Empty = all.
    var filterState = {
        view:      'verification',
        // 'all' by default: the seed data's events are historical, so the
        // narrow windows render an empty globe on first load (v9.143).
        window:    'all',
        modifiers: { pq: false, anomalies: false, full: false },
        contexts:  []
    };

    // Backwards-compat: a few other functions still reference the old name.
    // Kept as a derived value so a future cleanup can drop it in one place.
    function activeFilterName() {
        if (filterState.modifiers.pq)        return 'pq';
        if (filterState.modifiers.anomalies) return 'failures';   // legacy alias
        if (filterState.view === 'lifecycle') return 'lifecycle';
        return 'tokens';
    }
    var activeFilter = 'tokens';   // kept in sync via setView/setModifier

    function serializeFilters() {
        var parts = ['window=' + encodeURIComponent(filterState.window)];
        var outs = [];
        if (filterState.modifiers.anomalies) outs.push('anomalies');
        if (outs.length) parts.push('outcomes=' + outs.join(','));
        if (filterState.modifiers.full) parts.push('disclosure=FULL');
        if (filterState.contexts.length) {
            parts.push('contexts=' + filterState.contexts.map(encodeURIComponent).join(','));
        }
        return parts.join('&');
    }

    var selectedId = nodes.length ? nodes[0].id : null;
    var spinning = true;
    var dragging = false;
    var velocity = [0, 0]; // dλ, dφ per frame
    var lastDragDelta = [0, 0];
    var reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (reducedMotion) spinning = false;

    var toneClass = {
        zk: 'node-zk',
        selective: 'node-selective',
        full: 'node-full',
        alert: 'node-alert'
    };

    // ============================================================
    // Layer stack — ordering matters for compositing
    // ============================================================
    var root = svg.append('g').attr('class', 'd3-globe-root');

    // Glow halo: rendered behind the sphere so it bleeds outward
    var rimHaloLayer = root.append('g').attr('class', 'd3-globe-rim-layer')
        .attr('filter', 'url(#atlas-rim-glow)');
    var rimHaloOuter = rimHaloLayer.append('circle').attr('class', 'd3-globe-rim-outer');
    var rimHaloInner = rimHaloLayer.append('circle').attr('class', 'd3-globe-rim-inner');

    // Sphere fill
    var sphere = root.append('path').attr('class', 'd3-globe-sphere');
    // Faint graticule
    var grid = root.append('path').attr('class', 'd3-globe-grid');
    // Land
    var land = root.append('path').attr('class', 'd3-globe-land');
    // Land borders (drawn on top)
    var landBorders = root.append('path').attr('class', 'd3-globe-borders');
    // Country labels (clipped to disc)
    var labelLayer = root.append('g').attr('class', 'd3-globe-labels')
        .attr('clip-path', 'url(#atlas-disc-clip)');
    // Sharp limb line
    var limbLine = root.append('circle').attr('class', 'd3-globe-limb');
    // Reticle nodes
    var nodeLayer = root.append('g').attr('class', 'd3-globe-nodes');
    // Bracket UI for selected node
    var bracketLayer = root.append('g').attr('class', 'd3-globe-brackets');

    // ============================================================
    // Node reticles
    // ============================================================
    function shortCode(d) {
        var prefix = d.kind === 'lifecycle' ? 'PLR'
                   : d.kind === 'verification' ? 'VRF'
                   : 'NDE';
        var num = d.tokenId
                 || (d.id || '').replace(/[^0-9]/g, '').slice(-4)
                 || '0000';
        return prefix + '-' + num;
    }

    // Re-renderable node binding. Called whenever new data arrives from the
    // API. Uses the standard d3 enter/update/exit pattern so old reticles
    // are removed cleanly and new ones get the full reticle ornament.
    var nodeSelection = null;

    // v8.2 / V2: track ids ever seen this session so we can light up only
    // the nodes that genuinely just arrived. Pan/zoom-driven re-renders
    // will revisit ids already in the set; those don't pulse.
    var seenNodeIds = Object.create(null);
    var FRESH_DURATION_MS = 2800;

    function renderNodes(newNodes) {
        nodes = newNodes || [];
        // If the previously selected id is no longer in the dataset, drop it.
        if (selectedId && !nodes.find(function (n) { return n.id === selectedId; })) {
            selectedId = nodes.length ? nodes[0].id : null;
        }

        // Identify nodes that are first-time arrivals across the whole
        // session. Returned as a plain object (id → true) so the lookup
        // below is O(1) and the closure stays small.
        var freshThisFrame = Object.create(null);
        nodes.forEach(function (n) {
            if (!seenNodeIds[n.id]) {
                freshThisFrame[n.id] = true;
                seenNodeIds[n.id] = true;
            }
        });

        var sel = nodeLayer.selectAll('g.d3-globe-node')
            .data(nodes, function (d) { return d.id; });

        // Exit
        sel.exit().remove();

        // Enter — build the reticle ornament for new data points
        var enter = sel.enter()
            .append('g')
            .attr('class', function (d) {
                return 'd3-globe-node ' + (toneClass[d.tone] || 'node-selective');
            })
            .attr('role', 'button')
            .attr('tabindex', '0')
            .attr('aria-label', function (d) { return (d.title || d.id) + ' / ' + (d.subtitle || ''); });

        enter.each(function (d) {
            var g = d3.select(this);
            // Hit target — invisible large circle so the reticle is easy to click
            g.append('circle').attr('class', 'reticle-hit').attr('r', 16);
            // Pulse ring — sits BEHIND the static ring; only animates when
            // the node carries .node-fresh. The base radius matches the
            // static ring; CSS scales it. v8.2 / V2.
            var ringR = d.isCluster ? clusterRadius(d.count) : 10;
            g.append('circle').attr('class', 'reticle-pulse').attr('r', ringR);
            // Outer ring; for cluster nodes we scale the ring proportional
            // to sqrt(count) so large clusters visually dominate small ones
            // without dwarfing the globe at 100k events. The base radius
            // for solo nodes was bumped from 8 → 10 in v8.2 / V2 so a
            // single point is unmistakable on the globe.
            g.append('circle').attr('class', 'reticle-ring').attr('r', ringR);
            // Tick marks
            g.append('line').attr('class', 'reticle-tick').attr('x1', 0).attr('y1', -12).attr('x2', 0).attr('y2', -6);
            g.append('line').attr('class', 'reticle-tick').attr('x1', 0).attr('y1', 6).attr('x2', 0).attr('y2', 12);
            g.append('line').attr('class', 'reticle-tick').attr('x1', -12).attr('y1', 0).attr('x2', -6).attr('y2', 0);
            g.append('line').attr('class', 'reticle-tick').attr('x1', 6).attr('y1', 0).attr('x2', 12).attr('y2', 0);
            // Center dot — radius now driven by CSS (.reticle-core { r }) so
            // a future visual pass can scale all centers in one place.
            g.append('circle').attr('class', 'reticle-core');
            // Label group — hidden for clusters at low zoom
            if (!d.isCluster) {
                var lg = g.append('g').attr('class', 'reticle-label-group');
                lg.append('line').attr('class', 'reticle-leader')
                    .attr('x1', 12).attr('y1', 0).attr('x2', 34).attr('y2', -10);
                lg.append('rect').attr('class', 'reticle-label-bg')
                    .attr('x', 34).attr('y', -23).attr('width', 102).attr('height', 26);
                lg.append('text').attr('class', 'reticle-label-title')
                    .attr('x', 40).attr('y', -10)
                    .text(shortCode(d));
                lg.append('text').attr('class', 'reticle-label-sub')
                    .attr('x', 40).attr('y', 1)
                    .text((d.context || '').toUpperCase());
            } else {
                // Cluster count label sits inside the ring
                g.append('text').attr('class', 'reticle-cluster-count')
                    .attr('text-anchor', 'middle')
                    .attr('dominant-baseline', 'central')
                    .text(formatClusterCount(d.count));
            }
        });

        enter.append('title').text(function (d) {
            return (d.title || d.id) + ' / ' + (d.subtitle || '') + ' / ' + (d.meta || '');
        });

        enter.merge(sel)
            .on('mouseenter', function () { d3.select(this).classed('node-hover', true); })
            .on('mouseleave', function () { d3.select(this).classed('node-hover', false); })
            .on('click', function (event, d) { event.preventDefault(); focusNode(d.id, true); })
            .on('keydown', function (event, d) {
                if (event.key === 'Enter' || event.key === ' ') {
                    event.preventDefault();
                    focusNode(d.id, true);
                }
            });

        nodeSelection = nodeLayer.selectAll('g.d3-globe-node');

        // v8.2 / V2: mark first-time-seen nodes with .node-fresh so the
        // CSS pulse animation runs. We do this on the full post-render
        // selection (not on enter alone) so the class lands on the
        // already-mounted DOM elements; an earlier attempt against the
        // enter+merge selection failed silently because the merged
        // selection's data binding hadn't settled before .classed() ran.
        // The eval check during preview verification confirmed this
        // approach attaches the class correctly.
        var freshIdList = Object.keys(freshThisFrame);
        if (freshIdList.length) {
            nodeSelection.each(function (d) {
                if (freshThisFrame[d.id]) {
                    this.classList.add('node-fresh');
                }
            });
            setTimeout(function () {
                // Look up by id again — the DOM may have re-rendered in
                // the interim. Only clear nodes whose id was in THIS
                // frame's fresh set; later frames may have marked others.
                nodeLayer.selectAll('g.d3-globe-node').each(function (d) {
                    if (freshThisFrame[d.id]) {
                        this.classList.remove('node-fresh');
                    }
                });
            }, FRESH_DURATION_MS);
        }

        redraw();
    }

    // Cluster radius — sqrt-scaled so an order-of-magnitude jump in count
    // produces a 3.16x visual jump, not a 10x one. Capped at 28px so dense
    // clusters don't blow out the screen.
    function clusterRadius(count) {
        var r = 6 + Math.sqrt(count || 1) * 0.8;
        return Math.min(28, r);
    }

    // Format counts for the cluster label: 1.2k, 850, 14M, etc.
    function formatClusterCount(n) {
        n = +n || 0;
        if (n >= 1e6) return (n / 1e6).toFixed(1).replace(/\.0$/, '') + 'M';
        if (n >= 1e3) return (n / 1e3).toFixed(1).replace(/\.0$/, '') + 'k';
        return String(n);
    }

    // ============================================================
    // Drag with inertia
    // ============================================================
    svg.call(d3.drag()
        .on('start', function () {
            dragging = true;
            spinning = false;
            velocity = [0, 0];
            updateSpinButton();
        })
        .on('drag', function (event) {
            var rotate = projection.rotate();
            var dx = event.dx * 0.22 / Math.max(0.6, zoom);
            var dy = event.dy * 0.22 / Math.max(0.6, zoom);
            rotate[0] += dx;
            rotate[1] -= dy;
            rotate[1] = Math.max(-72, Math.min(72, rotate[1]));
            projection.rotate(rotate);
            lastDragDelta = [dx, -dy];
            redraw();
        })
        .on('end', function () {
            dragging = false;
            // Hand off momentum (capped)
            var vx = lastDragDelta[0];
            var vy = lastDragDelta[1];
            var mag = Math.sqrt(vx * vx + vy * vy);
            var cap = 4;
            if (mag > cap) { vx = vx * cap / mag; vy = vy * cap / mag; }
            velocity = [vx, vy];
            // User finished panning the globe — refetch for the new bbox
            scheduleFetch();
        })
    );

    // ============================================================
    // Zoom — v9.144b ultra-zoom with frame easing.
    //
    // setZoom() sets a TARGET; the animate loop eases the actual zoom
    // toward it each frame (exponential approach), so wheel, chips,
    // keyboard, and cluster drill-down all feel fluid instead of
    // stepping. The ceiling is 40x: deep enough that the cluster
    // pipeline hands over to exact-position point reticles and the
    // operator can read pinpoint event locations. The fetch fires once
    // when the zoom settles, not on every animation frame.
    // ============================================================
    var ZOOM_MIN = 0.7, ZOOM_MAX = 40;
    var targetZoom = zoom;
    var zoomSettled = true;

    function applyZoom(z) {
        zoom = z;
        projection.scale(baseRadius * zoom);
        if (zoomEl) {
            zoomEl.textContent = (zoom >= 10 ? zoom.toFixed(1) : zoom.toFixed(2)) + 'x';
        }
        redraw();
    }

    function setZoom(z) {
        targetZoom = Math.max(ZOOM_MIN, Math.min(ZOOM_MAX, z));
        if (reducedMotion) {
            applyZoom(targetZoom);
            scheduleFetch();
            return;
        }
        zoomSettled = false;   // the animate loop takes it from here
    }

    svg.on('wheel', function (event) {
        event.preventDefault();
        // Multiplicative steps feel uniform across the whole 0.7x-40x range.
        setZoom(targetZoom * (event.deltaY > 0 ? 1 / 1.16 : 1.16));
    }, { passive: false });

    // ============================================================
    // Resize
    // ============================================================
    function resize() {
        var box = container.getBoundingClientRect();
        width = Math.max(280, box.width);
        height = Math.max(280, box.height);
        baseRadius = Math.min(width, height) / 2 - 24;

        svg.attr('viewBox', '0 0 ' + width + ' ' + height);
        projection.translate([width / 2, height / 2]).scale(baseRadius * zoom);
        // Viewport clipping: at ultra zoom the projected world is hundreds of
        // thousands of pixels across; without a clip extent d3 paths every
        // offscreen arc. With it, deep zoom stays cheap.
        projection.clipExtent([[0, 0], [width, height]]);

        // Position rim halos and limb at globe center
        rimHaloOuter.attr('cx', width / 2).attr('cy', height / 2);
        rimHaloInner.attr('cx', width / 2).attr('cy', height / 2);
        limbLine.attr('cx', width / 2).attr('cy', height / 2);

        // Sync the disc clip
        d3.select('.atlas-disc-clip-circle')
            .attr('cx', width / 2).attr('cy', height / 2);

        redraw();
    }

    // ============================================================
    // Geometry helpers
    // ============================================================
    function center() { return projection.invert([width / 2, height / 2]); }
    function onFront(coord) { return d3.geoDistance(coord, center()) < Math.PI / 2; }
    function distFromCenter(coord) { return d3.geoDistance(coord, center()); }

    function isVisibleByFilter(d) {
        // Cluster nodes have already been filtered server-side by the `kind`
        // parameter on the API call. The 'pq' and 'failures' chips are the
        // only sub-filters the client applies on top of the fetched data.
        if (d.isCluster) {
            if (activeFilter === 'pq')       return (d.n_pq      || 0) > 0;
            if (activeFilter === 'failures') return (d.n_failure || 0) > 0;
            return true;
        }
        // Point nodes — server already filtered by kind. Sub-chip refinement:
        if (activeFilter === 'pq')       return Boolean(d.pq);
        if (activeFilter === 'failures') return d.outcome === 'FAILURE';
        // Default ('tokens', 'verifications', 'lifecycle'): show everything
        // the server returned.
        return true;
    }

    // ============================================================
    // Render
    // ============================================================
    function redraw() {
        var r = projection.scale();

        sphere.datum({ type: 'Sphere' }).attr('d', path);

        rimHaloOuter.attr('r', r + 2);
        rimHaloInner.attr('r', r + 1);
        limbLine.attr('r', r + 0.5);

        // Sync clip to current radius
        d3.select('.atlas-disc-clip-circle').attr('r', r - 1);

        grid.datum(graticule).attr('d', path);

        if (landFeature) {
            land.datum(landFeature).attr('d', path);
            landBorders.datum(landFeature).attr('d', path);
        }

        // Country labels — two-pass: project + score, then suppress collisions, then render
        if (countryFeatures.length) {
            // Pass 1: build candidate list, area-weighted
            var cands = [];
            for (var i = 0; i < countryFeatures.length; i++) {
                var f = countryFeatures[i];
                var pt = projection(f.centroid);
                if (!pt) continue;
                var dist = distFromCenter(f.centroid);
                if (dist > Math.PI / 2.35) continue;
                var fadeStart = Math.PI / 3.0;
                var fadeEnd = Math.PI / 2.35;
                var op = dist < fadeStart
                    ? 1
                    : Math.max(0, (fadeEnd - dist) / (fadeEnd - fadeStart));
                op *= Math.min(1, f.area * 22) * 0.55;
                if (op < 0.04) continue;
                // Approx bbox in screen space: ~5.4px per char wide, 9px tall
                var w = f.label.length * 5.4;
                var h = 9;
                cands.push({
                    f: f, pt: pt, op: op, area: f.area,
                    bbox: { x0: pt[0] - w / 2, x1: pt[0] + w / 2, y0: pt[1] - h / 2, y1: pt[1] + h / 2 }
                });
            }
            // Pass 2: greedy collision suppression — sort by area desc, drop overlappers
            cands.sort(function (a, b) { return b.area - a.area; });
            var kept = [];
            for (var j = 0; j < cands.length; j++) {
                var c = cands[j];
                var clash = false;
                for (var k = 0; k < kept.length; k++) {
                    var b = kept[k].bbox;
                    if (!(c.bbox.x1 < b.x0 - 4 || c.bbox.x0 > b.x1 + 4 ||
                          c.bbox.y1 < b.y0 - 2 || c.bbox.y0 > b.y1 + 2)) {
                        clash = true;
                        break;
                    }
                }
                if (!clash) kept.push(c);
            }
            // Render
            var keepIds = {};
            kept.forEach(function (c) { keepIds[c.f.id] = c; });
            var labels = labelLayer.selectAll('text.country-label').data(countryFeatures, function (f) { return f.id; });
            labels.enter().append('text')
                .attr('class', 'country-label')
                .attr('text-anchor', 'middle')
                .merge(labels)
                .each(function (f) {
                    var t = d3.select(this);
                    var c = keepIds[f.id];
                    if (!c) { t.attr('display', 'none'); return; }
                    t.attr('display', null)
                     .attr('opacity', c.op)
                     .attr('x', c.pt[0])
                     .attr('y', c.pt[1])
                     .text(f.label);
                });
        }

        // Reticle nodes — null-guarded because renderNodes() may not have
        // been called yet (initial render before the first API fetch).
        if (nodeSelection) {
            nodeSelection.each(function (d) {
                var node = d3.select(this);
                var pt = projection([d.lon, d.lat]);
                var visible = pt && onFront([d.lon, d.lat]) && isVisibleByFilter(d);

                node.classed('node-hidden', !visible)
                    .classed('node-selected', d.id === selectedId)
                    .attr('aria-hidden', visible ? 'false' : 'true')
                    .attr('tabindex', visible ? '0' : '-1')
                    .style('display', visible ? null : 'none');
                if (visible) {
                    node.attr('transform', 'translate(' + pt[0] + ',' + pt[1] + ')');
                }
            });
        }

        // Bracket frame on selected node
        bracketLayer.selectAll('*').remove();
        var sel = nodes.find(function (n) { return n.id === selectedId; });
        if (sel) {
            var spt = projection([sel.lon, sel.lat]);
            if (spt && onFront([sel.lon, sel.lat]) && isVisibleByFilter(sel)) {
                drawBrackets(spt[0], spt[1]);
            }
        }

        updateHud();
    }

    function drawBrackets(cx, cy) {
        var d = 22;
        var len = 7;
        var corners = [
            [-d, -d, len, 0,   0, len],
            [ d, -d, -len, 0,  0, len],
            [-d,  d, len, 0,   0, -len],
            [ d,  d, -len, 0,  0, -len]
        ];
        corners.forEach(function (c) {
            var x = cx + c[0], y = cy + c[1];
            bracketLayer.append('path')
                .attr('class', 'bracket-arm')
                .attr('d', 'M' + x + ',' + y + ' l' + c[2] + ',' + c[3] +
                          ' M' + x + ',' + y + ' l' + c[4] + ',' + c[5]);
        });
    }

    function updateHud() {
        var rot = projection.rotate();
        var heading = ((-rot[0] % 360) + 360) % 360;
        var pitch = -rot[1];
        if (headingEl) headingEl.textContent = (Math.round(heading) + '').padStart(3, '0') + '°';
        if (pitchEl) pitchEl.textContent = (pitch >= 0 ? '+' : '') + Math.round(pitch) + '°';
    }

    // ============================================================
    // Detail panel (v9.144: lives in the dock; selecting a node
    // switches the dock to the Node Console tab so the inspection
    // never covers the globe)
    // ============================================================
    function activateDockTab(name) {
        document.querySelectorAll('[data-dock-tab]').forEach(function (b) {
            b.classList.toggle('dock-tab-active', b.dataset.dockTab === name);
        });
        document.querySelectorAll('[data-dock-panel]').forEach(function (p) {
            p.classList.toggle('dock-panel-active', p.dataset.dockPanel === name);
        });
    }
    document.querySelectorAll('[data-dock-tab]').forEach(function (b) {
        b.addEventListener('click', function () { activateDockTab(b.dataset.dockTab); });
    });

    function setDetail(d) {
        if (!detail) return;
        activateDockTab('console');
        detail.replaceChildren();

        var kicker = document.createElement('span');
        kicker.className = 'detail-kicker';
        kicker.textContent =
            (d.kind === 'verification' ? 'VERIFICATION NODE' : 'LIFECYCLE NODE') +
            ' / ' + shortCode(d);
        detail.appendChild(kicker);

        var title = document.createElement('strong');
        title.textContent = d.title;
        detail.appendChild(title);

        var subtitle = document.createElement('span');
        subtitle.textContent = d.subtitle || '';
        detail.appendChild(subtitle);

        // Holder + agency line
        var partyBits = [];
        if (d.holder) partyBits.push(d.holder);
        if (d.agency) partyBits.push(d.agency);
        if (partyBits.length) {
            var party = document.createElement('span');
            party.className = 'detail-party';
            party.textContent = partyBits.join(' · ');
            detail.appendChild(party);
        }

        // Algorithm pill row (PQ vs CLASSICAL is the operational concern)
        if (d.algorithm) {
            var algo = document.createElement('span');
            algo.className = 'detail-algo';
            var algName = document.createElement('span');
            algName.className = 'detail-algo-name';
            algName.textContent = d.algorithm;
            algo.appendChild(algName);
            var pq = document.createElement('span');
            pq.className = 'detail-pill ' + (d.algorithmPq ? 'detail-pill-pq' : 'detail-pill-classical');
            pq.textContent = d.algorithmPq ? 'PQ' : 'CLASSICAL';
            algo.appendChild(pq);
            detail.appendChild(algo);
        }

        // Outcome + disclosure stamp
        var stampBits = [];
        if (d.outcome) stampBits.push(d.outcome);
        if (d.disclosure) stampBits.push(d.disclosure);
        if (d.eventType) stampBits.push(d.eventType);
        if (d.reason) stampBits.push(d.reason);
        stampBits.push(d.timestamp);
        var meta = document.createElement('span');
        meta.className = 'detail-meta';
        meta.textContent = stampBits.join(' / ');
        detail.appendChild(meta);

        // Predecessor lineage chain — collapsed inline render
        if (d.lineage && d.lineage.predecessorId) {
            var line = document.createElement('span');
            line.className = 'detail-lineage';
            line.innerHTML = 'lineage: #' + d.lineage.predecessorId +
                             ' <span class="detail-lineage-status">' + d.lineage.predecessorStatus + '</span>' +
                             ' → #' + (d.tokenId || '?') +
                             ' <span class="detail-lineage-seq">seq ' + (d.lineage.sequence || '—') + '</span>';
            detail.appendChild(line);
        }

        if (d.href) {
            var link = document.createElement('a');
            link.href = d.href;
            link.textContent = 'Open token detail →';
            detail.appendChild(link);
        }
    }

    function focusNode(id, stopSpin) {
        var d = nodes.find(function (node) { return node.id === id; });
        if (!d) return;
        selectedId = d.id;
        if (stopSpin) {
            spinning = false;
            velocity = [0, 0];
        }
        updateSpinButton();
        setDetail(d);
        var target = [-d.lon, -d.lat, 0];
        d3.transition()
            .duration(reducedMotion ? 0 : 820)
            .ease(d3.easeCubicInOut)
            .tween('rotate-globe', function () {
                var interpolator = d3.interpolate(projection.rotate(), target);
                return function (t) {
                    projection.rotate(interpolator(t));
                    redraw();
                };
            })
            .on('end', function () {
                // Clusters promise "click to zoom in" in their subtitle —
                // honor it: double the zoom centered on the cluster, which
                // refetches and resolves it into points or finer clusters.
                if (d.isCluster) setZoom(targetZoom * 2);
            });
    }

    // v8.3 (A+C): three setters drive filterState. Each invalidates the
    // fetch cache and re-renders the chip group it owns; a single
    // refreshFilterUI() at the end syncs every chip-bearing element so
    // chip state and filterState never drift.
    function setView(view) {
        if (view !== 'verification' && view !== 'lifecycle') return;
        filterState.view = view;
        activeFilter = (view === 'lifecycle') ? 'lifecycle' : 'tokens';
        lastFetchKey = null;
        refreshFilterUI();
        scheduleFetch();
    }
    function setWindow(win) {
        if (!Object.prototype.hasOwnProperty.call({'1h':1,'24h':1,'7d':1,'30d':1,'all':1}, win)) return;
        filterState.window = win;
        lastFetchKey = null;
        refreshFilterUI();
        scheduleFetch();
        loadTimeline();   // histogram strip lives on its own fetch
    }
    function toggleModifier(name) {
        if (!Object.prototype.hasOwnProperty.call(filterState.modifiers, name)) return;
        filterState.modifiers[name] = !filterState.modifiers[name];
        // Anomalies and PQ are mutually contradictory in spirit (anomalies
        // surfaces failures, PQ surfaces successful PQ-signed events).
        // We allow both in case someone wants the intersection — the
        // server returns the AND of all filters, which is fine.
        // Update legacy activeFilter so isVisibleByFilter still works.
        if (filterState.modifiers.pq) activeFilter = 'pq';
        else if (filterState.modifiers.anomalies) activeFilter = 'failures';
        else activeFilter = (filterState.view === 'lifecycle') ? 'lifecycle' : 'tokens';
        lastFetchKey = null;
        refreshFilterUI();
        scheduleFetch();
        loadTimeline();
    }
    function toggleContext(ctx) {
        var idx = filterState.contexts.indexOf(ctx);
        if (idx >= 0) filterState.contexts.splice(idx, 1);
        else filterState.contexts.push(ctx);
        lastFetchKey = null;
        refreshFilterUI();
        scheduleFetch();
        loadTimeline();
    }
    function refreshFilterUI() {
        // View chips (role=radio: keep aria-checked in sync for AT users)
        document.querySelectorAll('[data-atlas-view]').forEach(function (b) {
            var on = b.dataset.atlasView === filterState.view;
            b.classList.toggle('toolbar-chip-active', on);
            b.setAttribute('aria-checked', on ? 'true' : 'false');
        });
        // Window chips (role=radio)
        document.querySelectorAll('[data-atlas-window]').forEach(function (b) {
            var on = b.dataset.atlasWindow === filterState.window;
            b.classList.toggle('toolbar-chip-active', on);
            b.setAttribute('aria-checked', on ? 'true' : 'false');
        });
        // Modifier chips (independent toggles: aria-pressed)
        document.querySelectorAll('[data-atlas-modifier]').forEach(function (b) {
            var on = Boolean(filterState.modifiers[b.dataset.atlasModifier]);
            b.classList.toggle('toolbar-chip-active', on);
            b.setAttribute('aria-pressed', on ? 'true' : 'false');
        });
        // Context multi-select pills (independent toggles: aria-pressed)
        document.querySelectorAll('[data-atlas-context]').forEach(function (b) {
            var on = filterState.contexts.indexOf(b.dataset.atlasContext) >= 0;
            b.classList.toggle('toolbar-chip-active', on);
            b.setAttribute('aria-pressed', on ? 'true' : 'false');
        });
    }

    function updateSpinButton() {
        var button = document.querySelector('[data-atlas-spin]');
        if (!button) return;
        button.classList.toggle('toolbar-chip-active', spinning);
        button.textContent = spinning ? 'Pause' : 'Spin';
    }

    // ============================================================
    // API client / viewport-aware fetch coordinator
    // ============================================================

    // The visible "bbox" on an orthographic globe is the hemisphere centered
    // on the rotation focus — there isn't a clean lat/lon rectangle for it.
    // For the API we use a generous bounding rectangle that contains the
    // visible hemisphere, which gives us all the data we could see plus a
    // little margin on the back side. The aggregator on the server filters
    // tightly anyway.
    function currentBbox() {
        // At low zoom (≤ 1.3) we fetch the whole world. The cluster query
        // returns at most ~30 reticles for whole-world at 10° grid, so it's
        // both cheap and gives the spinning globe a continuous result set
        // regardless of rotation. Above 1.3 we tighten to the visible
        // hemisphere so the cluster density adapts to the zoom level.
        if (zoom <= 1.3) {
            return [-89.9, -179.9, 89.9, 179.9];
        }
        var rot = projection.rotate();      // [lambda, phi, gamma]
        var centerLon = -rot[0];
        var centerLat = -rot[1];
        var span = 90 / Math.max(1, zoom * 0.7);
        var minLat = Math.max(-90,  centerLat - span);
        var maxLat = Math.min( 90,  centerLat + span);
        // Clamp at the antimeridian instead of bailing to a whole-world
        // fetch: at ultra zoom a world fetch at a 0.01-degree grid would
        // be needlessly heavy. (A box straddling the seam loses the far
        // sliver; the demo data is nowhere near the dateline.)
        var minLon = Math.max(-180, centerLon - span);
        var maxLon = Math.min( 180, centerLon + span);
        if (minLon >= maxLon) {
            return [-89.9, -179.9, 89.9, 179.9];
        }
        return [minLat, minLon, maxLat, maxLon];
    }

    // Map zoom level to grid cell size (in decimal degrees). Higher zoom
    // means tighter grid means more clusters. The cluster→point switchover
    // happens when n_clusters ≤ 30 (visually clean to draw individuals).
    function chooseGrid(z) {
        if (z >= 20) return 0.01;   /* ~1 km cells: street-level pinpointing */
        if (z >= 10) return 0.02;
        if (z >= 6) return 0.05;
        if (z >= 4) return 0.2;
        if (z >= 3) return 0.5;
        if (z >= 2) return 1;
        if (z >= 1.5) return 2;
        if (z >= 1.0) return 5;
        return 10;
    }

    // Map filter chip to API kind parameter.
    function kindForFilter(f) {
        if (f === 'lifecycle') return 'lifecycle';
        return 'verification';
    }

    // Convert a cluster row into a node renderable by renderNodes()
    function clusterToNode(c, kind) {
        var alert = (c.n_failure || 0) + (c.n_revoked || 0) + (c.n_lost || 0);
        var tone = alert > 0 ? 'alert' : (kind === 'lifecycle' ? 'full' : 'zk');
        return {
            id: 'CLU-' + kind + '-' + c.lat.toFixed(3) + '_' + c.lon.toFixed(3),
            isCluster: true,
            kind: kind,
            tone: tone,
            lat: c.lat,
            lon: c.lon,
            count: c.n_total,
            title: formatClusterCount(c.n_total) + ' ' + kind + ' events',
            subtitle: 'cluster · click to zoom in',
            meta: kind === 'verification'
                ? (c.n_failure + ' failures · ' + c.n_zk + ' ZK · ' + c.n_full + ' FULL')
                : (c.n_revoked + ' revoked · ' + c.n_lost + ' lost'),
            n_failure: c.n_failure || 0,
            n_pq: c.n_pq || 0,
            n_zk: c.n_zk || 0,
            n_full: c.n_full || 0,
            n_revoked: c.n_revoked || 0,
            n_lost: c.n_lost || 0
        };
    }

    // Convert a point row into a renderable node
    function pointToNode(p, kind) {
        if (kind === 'verification') {
            var ptone = p.outcome === 'FAILURE' ? 'alert'
                      : p.disclosure_level === 'FULL' ? 'full'
                      : p.disclosure_level === 'ZERO_KNOWLEDGE' ? 'zk'
                      : 'selective';
            return {
                id: 'VRF-' + p.event_id,
                kind: 'verification',
                tone: ptone,
                lat: p.lat,
                lon: p.lon,
                tokenId: p.token_id,
                title: p.context_type + ' verification',
                subtitle: p.requestor_location || (p.lat.toFixed(2) + ', ' + p.lon.toFixed(2)),
                holder: p.holder_name,
                agency: p.agency_name,
                algorithm: p.algorithm_name,
                pq: p.pq,
                outcome: p.outcome,
                disclosure: p.disclosure_level,
                context: p.context_type,
                timestamp: p.event_timestamp,
                href: p.token_id ? ('/tokens/' + p.token_id) : null,
                meta: p.outcome + ' / ' + p.disclosure_level + ' / ' + p.event_timestamp
            };
        } else {
            var ltone = (p.event_type === 'REVOKED' || p.event_type === 'LOST') ? 'alert'
                      : p.event_type === 'ACTIVATED' ? 'zk' : 'full';
            return {
                id: 'PLR-' + p.event_id,
                kind: 'lifecycle',
                tone: ltone,
                lat: p.lat,
                lon: p.lon,
                tokenId: p.token_id,
                title: p.event_type,
                subtitle: p.holder_name,
                holder: p.holder_name,
                agency: p.agency_name,
                algorithm: p.algorithm_name,
                pq: p.pq,
                eventType: p.event_type,
                reason: p.reason_code,
                timestamp: p.event_timestamp,
                href: p.token_id ? ('/tokens/' + p.token_id) : null,
                meta: p.event_type + ' / ' + (p.reason_code || '') + ' / ' + p.event_timestamp
            };
        }
    }

    // Update the HUD readouts from /api/atlas/stats. Called on every fetch
    // so the operational ratios always reflect the current viewport.
    function updateAtlasStats(stats) {
        if (!stats) return;
        var setText = function (sel, val) {
            var el = document.querySelector(sel);
            if (el) el.textContent = String(val);
        };
        setText('[data-atlas-active-tokens]', stats.n_active_tokens);
        setText('[data-atlas-pq-pct]', stats.pq_pct + '%');
        setText('[data-atlas-zk-pct]', stats.zk_pct + '%');
        setText('[data-atlas-failures]', stats.n_failures);
        setText('[data-atlas-full-disclosures]', stats.n_full);
    }

    // Tiny fetch helper with abort + JSON.
    function apiCall(url, signal) {
        return fetch(url, { signal: signal, credentials: 'same-origin' })
            .then(function (r) {
                if (!r.ok) throw new Error('HTTP ' + r.status);
                return r.json();
            });
    }

    // Coordinator. Picks endpoint by viewport, fetches in parallel, dedupes
    // identical requests, and aborts in-flight requests on viewport change.
    function fetchData() {
        var bbox = currentBbox();
        var grid = chooseGrid(zoom);
        var kind = kindForFilter(activeFilter);
        var filterQS = serializeFilters();
        // Cache key includes filter state — pre-v8.3 it didn't, so toggling
        // a chip while the same bbox/zoom was active produced a stale cache hit.
        var key = kind + '|' + bbox.join(',') + '|' + grid + '|' + renderMode + '|' + filterQS;
        if (key === lastFetchKey) return;
        lastFetchKey = key;

        if (inflightFetch) inflightFetch.abort();
        inflightFetch = (typeof AbortController !== 'undefined') ? new AbortController() : null;
        var signal = inflightFetch ? inflightFetch.signal : undefined;

        var bboxParam = bbox.join(',');

        // First try clusters. If the cluster count drops below the cluster→
        // point threshold, switch to points on the SAME viewport for the
        // labelled-reticle render. This is one extra HTTP round trip but only
        // when the user has zoomed deep, which is rare and has small payload.
        apiCall('/api/atlas/clusters?bbox=' + encodeURIComponent(bboxParam) +
                '&grid=' + grid + '&kind=' + kind + '&' + filterQS, signal)
            .then(function (data) {
                if (data.count <= 30 && zoom >= 2) {
                    // Few enough events that we can show individual reticles
                    return apiCall('/api/atlas/points?bbox=' + encodeURIComponent(bboxParam) +
                                   '&kind=' + kind + '&limit=500&' + filterQS, signal)
                        .then(function (pts) {
                            renderMode = 'point';
                            var pNodes = (pts.points || []).map(function (p) { return pointToNode(p, kind); });
                            renderNodes(pNodes);
                            toggleEmptyHint(pNodes.length === 0);
                            hideAtlasError();
                        });
                } else {
                    renderMode = 'cluster';
                    var cNodes = (data.clusters || []).map(function (c) { return clusterToNode(c, kind); });
                    renderNodes(cNodes);
                    toggleEmptyHint(cNodes.length === 0);
                }
                hideAtlasError();
            })
            .catch(function (err) {
                if (err.name !== 'AbortError') {
                    console.warn('Atlas fetch failed:', err);
                    // Drop the dedupe key so the next scheduleFetch for this
                    // viewport retries instead of short-circuiting forever.
                    lastFetchKey = null;
                    showAtlasError();
                }
            });

        // HUD signals — independent fetch, doesn't block reticles
        apiCall('/api/atlas/stats?bbox=' + encodeURIComponent(bboxParam) +
                '&' + filterQS, signal)
            .then(updateAtlasStats)
            .catch(function (err) {
                if (err.name !== 'AbortError') console.warn('Atlas stats fetch failed:', err);
            });
    }

    // ============================================================
    // Fetch-failure surfacing — a console.warn is invisible to an
    // operator. A non-abort failure raises a small chip over the
    // stage with a Retry control; any subsequent success clears it.
    // ============================================================
    var errorChip = document.querySelector('[data-atlas-error]');
    var emptyChip = document.querySelector('[data-atlas-empty]');

    function showAtlasError() { if (errorChip) errorChip.hidden = false; }
    function hideAtlasError() { if (errorChip) errorChip.hidden = true; }

    // A blank globe must explain itself: surfaced when a successful fetch
    // legitimately returns zero nodes for the current viewport + filters.
    function toggleEmptyHint(isEmpty) {
        if (emptyChip) emptyChip.hidden = !isEmpty;
    }

    var retryBtn = document.querySelector('[data-atlas-retry]');
    if (retryBtn) {
        retryBtn.addEventListener('click', function () {
            hideAtlasError();
            lastFetchKey = null;
            scheduleFetch();
            loadTimeline();
        });
    }

    // ============================================================
    // LIVE refresh — the LIVE chip used to be decorative; data only
    // refetched on viewport/filter changes. Refresh the reticles,
    // HUD stats, and histogram every 60s while the tab is visible,
    // and immediately when the operator returns to the tab.
    // ============================================================
    var LIVE_REFRESH_MS = 60000;

    function liveRefresh() {
        if (document.hidden) return;
        lastFetchKey = null;
        scheduleFetch();
        loadTimeline();
    }
    setInterval(liveRefresh, LIVE_REFRESH_MS);
    document.addEventListener('visibilitychange', function () {
        if (!document.hidden) liveRefresh();
    });

    // ============================================================
    // v8.3 / A — histogram strip below the toolbar
    //
    // Pulls bucket counts from /api/atlas/timeline and renders a small
    // SVG with one bar per bucket. The bar is split by anomaly portion
    // (red below) vs non-anomaly (steel above) so the operator can see
    // at a glance whether the activity in the selected window was
    // routine or interesting. Refetched on every filter or window
    // change. Hovering a bar surfaces the bucket timestamp.
    // ============================================================
    var timelineEl = null;
    var TIMELINE_BUCKETS = 60;

    function loadTimeline() {
        if (!timelineEl) {
            timelineEl = document.querySelector('[data-atlas-timeline]');
            if (!timelineEl) return;
        }
        var bbox = currentBbox();
        var kind = kindForFilter(activeFilter);
        var url = '/api/atlas/timeline?bbox=' + encodeURIComponent(bbox.join(','))
                + '&buckets=' + TIMELINE_BUCKETS + '&kind=' + kind
                + '&' + serializeFilters();
        apiCall(url)
            .then(renderTimeline)
            .catch(function (err) {
                if (err.name !== 'AbortError') console.warn('Atlas timeline fetch failed:', err);
            });
    }

    function renderTimeline(data) {
        if (!timelineEl) return;
        var pts = (data && data.points) || [];
        // Build a sparse-to-dense map: pts can have fewer rows than
        // TIMELINE_BUCKETS (server returns only non-empty buckets).
        // We fill the timeline with zeroes between since/until.
        var sinceMs = data.since ? new Date(data.since).getTime() : null;
        var untilMs = data.until ? new Date(data.until).getTime() : null;
        if (sinceMs === null || untilMs === null || untilMs <= sinceMs) {
            timelineEl.innerHTML = '';
            return;
        }
        var bucketSpan = (untilMs - sinceMs) / TIMELINE_BUCKETS;
        var dense = new Array(TIMELINE_BUCKETS);
        for (var i = 0; i < TIMELINE_BUCKETS; i++) {
            dense[i] = { ts: sinceMs + i * bucketSpan, n_total: 0, n_anomaly: 0 };
        }
        pts.forEach(function (p) {
            var t = new Date(p.ts).getTime();
            var idx = Math.max(0, Math.min(TIMELINE_BUCKETS - 1,
                Math.floor((t - sinceMs) / bucketSpan)));
            dense[idx].n_total += p.n_total;
            dense[idx].n_anomaly += p.n_anomaly;
        });
        var maxN = dense.reduce(function (m, b) { return b.n_total > m ? b.n_total : m; }, 0);
        // Log-scale so a 1000-event spike doesn't squash a 10-event bar
        // into invisibility. Empty buckets render as a hairline so the
        // strip's footprint matches the window even when nothing happened.
        function barHeight(n) {
            if (!n) return 1;
            if (!maxN) return 1;
            return Math.max(2, Math.round(36 * Math.log(1 + n) / Math.log(1 + maxN)));
        }

        var svgNS = 'http://www.w3.org/2000/svg';
        timelineEl.innerHTML = '';
        var svg = document.createElementNS(svgNS, 'svg');
        svg.setAttribute('class', 'atlas-timeline-svg');
        svg.setAttribute('viewBox', '0 0 ' + (TIMELINE_BUCKETS * 4) + ' 40');
        svg.setAttribute('preserveAspectRatio', 'none');
        svg.setAttribute('aria-label', 'Activity timeline for selected window');

        for (var j = 0; j < dense.length; j++) {
            var b = dense[j];
            var h = barHeight(b.n_total);
            var anomalyH = b.n_total ? Math.round(h * b.n_anomaly / b.n_total) : 0;
            var routineH = h - anomalyH;
            // Routine portion (top, steel)
            if (routineH > 0) {
                var rectR = document.createElementNS(svgNS, 'rect');
                rectR.setAttribute('class', 'atlas-timeline-bar-routine');
                rectR.setAttribute('x', j * 4);
                rectR.setAttribute('y', 40 - h);
                rectR.setAttribute('width', 3);
                rectR.setAttribute('height', routineH);
                svg.appendChild(rectR);
            }
            // Anomaly portion (bottom, red)
            if (anomalyH > 0) {
                var rectA = document.createElementNS(svgNS, 'rect');
                rectA.setAttribute('class', 'atlas-timeline-bar-anomaly');
                rectA.setAttribute('x', j * 4);
                rectA.setAttribute('y', 40 - anomalyH);
                rectA.setAttribute('width', 3);
                rectA.setAttribute('height', anomalyH);
                svg.appendChild(rectA);
            }
            // Hidden hit area + tooltip
            var hit = document.createElementNS(svgNS, 'rect');
            hit.setAttribute('x', j * 4);
            hit.setAttribute('y', 0);
            hit.setAttribute('width', 4);
            hit.setAttribute('height', 40);
            hit.setAttribute('fill', 'transparent');
            var title = document.createElementNS(svgNS, 'title');
            title.textContent = new Date(b.ts).toISOString().replace('T', ' ').slice(0, 16)
                + '  ·  ' + b.n_total + ' total'
                + (b.n_anomaly ? '  ·  ' + b.n_anomaly + ' anomaly' : '');
            hit.appendChild(title);
            svg.appendChild(hit);
        }
        timelineEl.appendChild(svg);
    }

    // Debounced wrapper so pan/zoom events don't issue a request per frame.
    function scheduleFetch() {
        if (fetchScheduled) clearTimeout(fetchScheduled);
        fetchScheduled = setTimeout(function () {
            fetchScheduled = null;
            fetchData();
        }, 220);
    }

    // Note: we do NOT wrap `redraw` to fire scheduleFetch on every animation
    // frame. The auto-spin would cause continuous bbox shifts, the 220ms
    // debounce would constantly reset, and inflight aborts would prevent
    // any cluster fetch from ever completing. Instead we hook scheduleFetch
    // to user-initiated viewport changes (drag end, wheel zoom, filter
    // chips) and call it once after the world topology resolves.

    // ============================================================
    // Event Feed (right rail) — paginated /api/atlas/events
    // ============================================================
    var eventFeedEl = document.querySelector('[data-atlas-event-feed]');
    var eventFeedCursor = null;
    var eventFeedLoading = false;

    function renderEventFeedRow(ev) {
        var li = document.createElement('li');
        li.className = 'atlas-feed-row tone-' + (ev.tone || 'selective');
        li.dataset.eventKind = ev.kind;
        li.dataset.eventId = ev.event_id;

        var badge = document.createElement('span');
        badge.className = 'atlas-feed-badge';
        badge.textContent = ev.label;
        li.appendChild(badge);

        var body = document.createElement('div');
        body.className = 'atlas-feed-body';
        var title = document.createElement('strong');
        title.textContent = ev.holder_name || '—';
        body.appendChild(title);
        var sub = document.createElement('span');
        sub.textContent = ev.agency_name + ' · ' + (ev.detail || '');
        body.appendChild(sub);
        li.appendChild(body);

        var stamp = document.createElement('time');
        stamp.className = 'atlas-feed-stamp';
        stamp.textContent = ev.event_timestamp;
        li.appendChild(stamp);

        if (ev.token_id) {
            li.style.cursor = 'pointer';
            li.addEventListener('click', function () {
                window.location.href = '/tokens/' + ev.token_id;
            });
        }

        return li;
    }

    function loadMoreEvents() {
        if (eventFeedLoading || !eventFeedEl) return;
        eventFeedLoading = true;
        var url = '/api/atlas/events?limit=50';
        if (eventFeedCursor) url += '&cursor=' + encodeURIComponent(eventFeedCursor);
        apiCall(url)
            .then(function (data) {
                (data.events || []).forEach(function (ev) {
                    eventFeedEl.appendChild(renderEventFeedRow(ev));
                });
                eventFeedCursor = data.next_cursor;
                eventFeedLoading = false;
                // Keep the rail-heading counter honest: rows loaded so far.
                var countEl = document.querySelector('[data-atlas-feed-count]');
                if (countEl) countEl.textContent = String(eventFeedEl.children.length);
            })
            .catch(function (err) {
                eventFeedLoading = false;
                console.warn('Event feed fetch failed:', err);
            });
    }

    if (eventFeedEl) {
        // Wipe any server-rendered placeholder content before fetching
        eventFeedEl.innerHTML = '';
        loadMoreEvents();

        // Infinite scroll: when the feed reaches its bottom and we have a
        // cursor, fetch the next page.
        var feedRail = eventFeedEl.closest('[data-atlas-event-feed-scroll]') || eventFeedEl;
        feedRail.addEventListener('scroll', function () {
            if (feedRail.scrollTop + feedRail.clientHeight >= feedRail.scrollHeight - 80) {
                if (eventFeedCursor) loadMoreEvents();
            }
        });
    }

    // Kick off the first fetch — happens after the world topology resolves
    // (see the d3.json block below). The world data is needed for the
    // reticles to project correctly.

    // v8.3 (A+C) chip handlers — view, window, modifier, context.
    document.querySelectorAll('[data-atlas-view]').forEach(function (b) {
        b.addEventListener('click', function () { setView(b.dataset.atlasView); });
    });
    document.querySelectorAll('[data-atlas-window]').forEach(function (b) {
        b.addEventListener('click', function () { setWindow(b.dataset.atlasWindow); });
    });
    document.querySelectorAll('[data-atlas-modifier]').forEach(function (b) {
        b.addEventListener('click', function () { toggleModifier(b.dataset.atlasModifier); });
    });
    document.querySelectorAll('[data-atlas-context]').forEach(function (b) {
        b.addEventListener('click', function () { toggleContext(b.dataset.atlasContext); });
    });
    var spinButton = document.querySelector('[data-atlas-spin]');
    if (spinButton) {
        spinButton.addEventListener('click', function () {
            spinning = !spinning;
            if (spinning) velocity = [0, 0];
            updateSpinButton();
        });
    }

    var resetZoomBtn = document.querySelector('[data-atlas-reset]');
    if (resetZoomBtn) {
        resetZoomBtn.addEventListener('click', function () {
            setZoom(1);
        });
    }

    var zoomInBtn = document.querySelector('[data-atlas-zoom-in]');
    var zoomOutBtn = document.querySelector('[data-atlas-zoom-out]');
    if (zoomInBtn)  zoomInBtn.addEventListener('click', function () { setZoom(targetZoom * 1.6); });
    if (zoomOutBtn) zoomOutBtn.addEventListener('click', function () { setZoom(targetZoom / 1.6); });

    // ============================================================
    // Fullscreen — the console takes the whole display ('f' or the
    // command-bar chip). The ResizeObserver re-measures the globe
    // when the stage box jumps.
    // ============================================================
    var shellEl = document.querySelector('.atlas-shell');
    var fsBtn = document.querySelector('[data-atlas-fullscreen]');

    function toggleFullscreen() {
        if (!shellEl) return;
        if (document.fullscreenElement || document.webkitFullscreenElement) {
            (document.exitFullscreen || document.webkitExitFullscreen).call(document);
        } else {
            (shellEl.requestFullscreen || shellEl.webkitRequestFullscreen).call(shellEl);
        }
    }

    function syncFullscreenChip() {
        if (!fsBtn) return;
        var on = Boolean(document.fullscreenElement || document.webkitFullscreenElement);
        fsBtn.classList.toggle('toolbar-chip-active', on);
        fsBtn.setAttribute('aria-pressed', on ? 'true' : 'false');
        fsBtn.textContent = on ? '✕ Exit' : '⛶ Full';
    }

    if (fsBtn) fsBtn.addEventListener('click', toggleFullscreen);
    document.addEventListener('fullscreenchange', syncFullscreenChip);
    document.addEventListener('webkitfullscreenchange', syncFullscreenChip);

    // ============================================================
    // Cursor coordinates — invert the projection under the pointer
    // and stream LAT/LON to the status bar. This is the pinpoint
    // readout: at ultra zoom the operator reads the exact position
    // of an event off the cursor.
    // ============================================================
    var cursorEl = document.getElementById('atlas-hud-cursor');

    function fmtCoord(v, posChar, negChar) {
        var hemi = v >= 0 ? posChar : negChar;
        return Math.abs(v).toFixed(zoom >= 8 ? 4 : 2) + '°' + hemi;
    }

    if (cursorEl) {
        svgEl.addEventListener('mousemove', function (event) {
            var pt = d3.pointer(event, svgEl);
            // Only meaningful inside the projected disc.
            var dx = pt[0] - width / 2, dy = pt[1] - height / 2;
            if (Math.sqrt(dx * dx + dy * dy) > baseRadius * zoom) {
                cursorEl.textContent = '— —';
                return;
            }
            var geo = projection.invert(pt);
            if (!geo || isNaN(geo[0]) || isNaN(geo[1])) {
                cursorEl.textContent = '— —';
                return;
            }
            cursorEl.textContent =
                fmtCoord(geo[1], 'N', 'S') + ' ' + fmtCoord(geo[0], 'E', 'W');
        });
        svgEl.addEventListener('mouseleave', function () {
            cursorEl.textContent = '— —';
        });
    }

    // ============================================================
    // Keyboard operation — the globe is focusable (tabindex=0):
    // arrows rotate, +/- zoom, space toggles spin.
    // ============================================================
    svgEl.addEventListener('keydown', function (event) {
        var step = event.shiftKey ? 18 : 6;
        var r = projection.rotate();
        switch (event.key) {
            case 'ArrowLeft':  r[0] -= step; break;
            case 'ArrowRight': r[0] += step; break;
            case 'ArrowUp':    r[1] += step; break;
            case 'ArrowDown':  r[1] -= step; break;
            case '+': case '=': setZoom(targetZoom * 1.6); event.preventDefault(); return;
            case '-': case '_': setZoom(targetZoom / 1.6); event.preventDefault(); return;
            case 'f': case 'F': toggleFullscreen(); event.preventDefault(); return;
            case ' ':
                spinning = !spinning;
                if (spinning) velocity = [0, 0];
                updateSpinButton();
                event.preventDefault();
                return;
            default: return;
        }
        event.preventDefault();
        spinning = false;
        updateSpinButton();
        r[1] = Math.max(-80, Math.min(80, r[1]));
        projection.rotate(r);
        redraw();
        scheduleFetch();
    });

    // ============================================================
    // Z-time ticker
    // ============================================================
    function tickTime() {
        if (!timeEl) return;
        var d = new Date();
        var pad = function (n) { return n < 10 ? '0' + n : '' + n; };
        var months = ['JAN','FEB','MAR','APR','MAY','JUN','JUL','AUG','SEP','OCT','NOV','DEC'];
        timeEl.textContent =
            months[d.getUTCMonth()] + ' ' + pad(d.getUTCDate()) + ' ' + d.getUTCFullYear() +
            ' / ' +
            pad(d.getUTCHours()) + ':' + pad(d.getUTCMinutes()) + ':' + pad(d.getUTCSeconds()) + 'Z';
    }
    tickTime();
    setInterval(tickTime, 1000);

    // ============================================================
    // Animate loop
    // ============================================================
    function animate() {
        // Frame-eased zoom: approach the target exponentially; snap and
        // fetch once within a quarter-percent of it.
        if (!zoomSettled) {
            var diff = targetZoom - zoom;
            if (Math.abs(diff) > Math.max(0.002, targetZoom * 0.0025)) {
                applyZoom(zoom + diff * 0.16);
            } else {
                applyZoom(targetZoom);
                zoomSettled = true;
                scheduleFetch();
            }
        }
        var r = projection.rotate();
        if (spinning && !dragging) {
            r[0] += 0.045;
            projection.rotate(r);
            redraw();
        } else if (!dragging && (Math.abs(velocity[0]) > 0.003 || Math.abs(velocity[1]) > 0.003)) {
            r[0] += velocity[0];
            r[1] += velocity[1];
            r[1] = Math.max(-72, Math.min(72, r[1]));
            projection.rotate(r);
            velocity[0] *= 0.93;
            velocity[1] *= 0.93;
            redraw();
        }
        window.requestAnimationFrame(animate);
    }

    // ============================================================
    // Load topojson
    // ============================================================
    d3.json(container.dataset.worldUrl)
        .then(function (world) {
            landFeature = topojson.feature(world, world.objects.countries);
            var feats = landFeature.features || [];
            var rawFeats = feats.map(function (f) {
                return {
                    id: f.id || (f.properties && f.properties.name) || Math.random().toString(36).slice(2),
                    centroid: d3.geoCentroid(f),
                    area: d3.geoArea(f),
                    label: ((f.properties && f.properties.name) || '').toUpperCase()
                };
            }).filter(function (f) {
                return f.label && f.area > 0.012;
            });
            // Dedupe by label, keep largest-area instance
            var byLabel = {};
            rawFeats.forEach(function (f) {
                if (!byLabel[f.label] || byLabel[f.label].area < f.area) {
                    byLabel[f.label] = f;
                }
            });
            countryFeatures = Object.keys(byLabel).map(function (k) { return byLabel[k]; });

            resize();
            // Fire the first API call now that the world topology is loaded
            // and renderNodes() can project the resulting reticles.
            scheduleFetch();
            updateSpinButton();
            refreshFilterUI();   // sync chip group with default filterState
            loadTimeline();      // initial histogram strip render
            window.requestAnimationFrame(animate);
        })
        .catch(function () {
            if (detail) {
                detail.replaceChildren();
                var error = document.createElement('strong');
                error.textContent = 'Globe data unavailable';
                detail.appendChild(error);
            }
        });

    window.addEventListener('resize', resize);
    // v9.144 console shell: the stage box also changes without a window
    // resize (dock stacking at breakpoints, flash messages above the bar).
    // Re-measure whenever the container box itself changes.
    if (typeof ResizeObserver !== 'undefined') {
        var lastBox = null;
        new ResizeObserver(function (entries) {
            var b = entries[0].contentRect;
            if (lastBox && Math.abs(b.width - lastBox.width) < 2 &&
                Math.abs(b.height - lastBox.height) < 2) return;
            lastBox = b;
            resize();
            scheduleFetch();
        }).observe(container);
    }
})();
