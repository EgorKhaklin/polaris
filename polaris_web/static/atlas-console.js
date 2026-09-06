/* ===========================================================================
 * atlas-console.js  —  the Atlas analytical console shell + Overview view.
 * Roadmap P2.3 (v9.248, the analytical-console rebuild).
 *
 * Owns:
 *   1. the view tabs (Overview / Map), booting the MapLibre map LAZILY the
 *      first time the Map tab is shown (a hidden container cannot size a GL
 *      canvas, and an always-live map is wasted work on a page that opens on
 *      the Overview);
 *   2. the Overview view: a bounded, NON-geographic analytics surface built
 *      from /api/atlas/series (volume time-series) + /api/atlas/breakdown
 *      (top-K roll-ups) + the server-rendered point-in-time figures.
 *
 * Every chart is hand-rolled inline SVG or CSS bars, built programmatically
 * (createElement / createElementNS / textContent) — never innerHTML with
 * markup — so `script-src 'self'` (C5) stays strict and no charting CDN is
 * needed. Zero-knowledge events are counted in every figure but never located
 * (C6): the server aggregates enforce that; the console only ever shows counts.
 * ======================================================================== */
(function () {
  'use strict';

  var shell = document.querySelector('.atlas-shell');
  if (!shell) return;

  // ---- tiny helpers --------------------------------------------------------
  function $(sel, root) { return (root || document).querySelector(sel); }
  function $$(sel, root) { return Array.prototype.slice.call((root || document).querySelectorAll(sel)); }
  var SVGNS = 'http://www.w3.org/2000/svg';

  function el(tag, attrs, children) {
    var n = document.createElement(tag);
    if (attrs) for (var k in attrs) {
      if (k === 'class') n.className = attrs[k];
      else if (k === 'text') n.textContent = attrs[k];
      else n.setAttribute(k, attrs[k]);
    }
    if (children) children.forEach(function (c) { if (c) n.appendChild(c); });
    return n;
  }
  function svg(tag, attrs) {
    var n = document.createElementNS(SVGNS, tag);
    if (attrs) for (var k in attrs) n.setAttribute(k, attrs[k]);
    return n;
  }
  function fmtInt(n) {
    n = Number(n) || 0;
    if (n >= 1e9) return (n / 1e9).toFixed(1).replace(/\.0$/, '') + 'B';
    if (n >= 1e6) return (n / 1e6).toFixed(1).replace(/\.0$/, '') + 'M';
    if (n >= 1e3) return (n / 1e3).toFixed(1).replace(/\.0$/, '') + 'k';
    return String(n);
  }
  function fmtPct(x) { return (Math.round(x * 10) / 10) + '%'; }

  function apiCall(url) {
    return fetch(url, { credentials: 'same-origin', headers: { 'Accept': 'application/json' } })
      .then(function (r) {
        if (!r.ok) throw new Error('HTTP ' + r.status);
        return r.json();
      });
  }

  // =========================================================================
  // View tabs (Overview / Map) + lazy map boot
  // =========================================================================
  var mapBooted = false;
  function showView(name) {
    $$('[data-atlas-view-tab]').forEach(function (t) {
      var on = t.getAttribute('data-atlas-view-tab') === name;
      t.classList.toggle('atlas-tab-active', on);
      t.setAttribute('aria-selected', on ? 'true' : 'false');
    });
    $$('[data-atlas-view-panel]').forEach(function (p) {
      p.hidden = p.getAttribute('data-atlas-view-panel') !== name;
    });
    if (name === 'map') {
      // Boot the map on first reveal, then keep it resized on every return.
      // rAF so the panel is laid out (measurable) before MapLibre boots/measures.
      requestAnimationFrame(function () {
        window.dispatchEvent(new CustomEvent('polaris:atlas-map-show'));
        if (window.atlasMap && window.atlasMap.resize) window.atlasMap.resize();
      });
      mapBooted = true;
    }
    if (name === 'breakdown') loadBreakdown();
    try { history.replaceState(null, '', '#' + name); } catch (e) { /* ignore */ }
  }
  $$('[data-atlas-view-tab]').forEach(function (t) {
    t.addEventListener('click', function () { showView(t.getAttribute('data-atlas-view-tab')); });
  });
  // Deep-link support: #map opens the map tab directly.
  if ((location.hash || '').replace('#', '') === 'map') showView('map');

  // =========================================================================
  // Overview state + controls
  // =========================================================================
  var overview = $('[data-atlas-view-panel="overview"]');
  if (!overview) return;

  var state = { stream: 'verification', window: 'all' };
  var TONE = { total: '#38bdf8', fail: '#f87171', zk: '#a78bfa' };

  // The breakdown panels each view shows, per stream. A panel names its mount
  // (data-ov-breakdown), its title, and the SQL dimension to request.
  var PANELS = {
    verification: [
      { key: 'context',    title: 'By context',   dim: 'context' },
      { key: 'agency',     title: 'Top agencies', dim: 'agency' },
      { key: 'disclosure', title: 'Disclosure mix', dim: 'disclosure', mix: true },
      { key: 'outcome',    title: 'Outcome mix',  dim: 'outcome' }
    ],
    lifecycle: [
      { key: 'context',    title: 'By event type', dim: 'event_type' },
      { key: 'agency',     title: 'By actor agency', dim: 'agency' }
    ]
  };

  function setChipGroup(attr, value) {
    $$('[' + attr + ']', overview).forEach(function (c) {
      var on = c.getAttribute(attr) === value;
      c.classList.toggle('toolbar-chip-active', on);
      c.setAttribute('aria-checked', on ? 'true' : 'false');
    });
  }
  $$('[data-ov-stream]', overview).forEach(function (c) {
    c.addEventListener('click', function () {
      state.stream = c.getAttribute('data-ov-stream');
      setChipGroup('data-ov-stream', state.stream);
      loadOverview();
    });
  });
  $$('[data-ov-window]', overview).forEach(function (c) {
    c.addEventListener('click', function () {
      state.window = c.getAttribute('data-ov-window');
      setChipGroup('data-ov-window', state.window);
      loadOverview();
    });
  });
  var retry = $('[data-ov-retry]', overview);
  if (retry) retry.addEventListener('click', loadOverview);

  // =========================================================================
  // Chart primitives (all CSP-clean: programmatic SVG / DOM)
  // =========================================================================

  // A filled area for the primary series with a stroked overlay for failures.
  function renderHero(mount, points) {
    mount.textContent = '';
    if (!points || !points.length) {
      mount.appendChild(el('div', { class: 'ov-empty', text: 'No events in this window.' }));
      return;
    }
    var W = 820, H = 220, padL = 8, padR = 8, padT = 12, padB = 22;
    var iW = W - padL - padR, iH = H - padT - padB;
    var maxV = 1;
    points.forEach(function (p) { if (p.n_total > maxV) maxV = p.n_total; });
    var n = points.length;
    function X(i) { return padL + (n === 1 ? iW / 2 : (i / (n - 1)) * iW); }
    function Y(v) { return padT + iH - (v / maxV) * iH; }

    var s = svg('svg', { viewBox: '0 0 ' + W + ' ' + H, class: 'ov-hero-svg',
      preserveAspectRatio: 'none', role: 'img' });

    // horizontal gridlines at 0/50/100% of max
    [0, 0.5, 1].forEach(function (f) {
      var y = padT + iH - f * iH;
      s.appendChild(svg('line', { x1: padL, y1: y, x2: W - padR, y2: y, class: 'ov-gridline' }));
      s.appendChild(svg('text', { x: padL + 2, y: y - 3, class: 'ov-axis' })).textContent =
        f === 0 ? '' : fmtInt(Math.round(maxV * f));
    });

    // area path for n_total
    var d = 'M ' + X(0) + ' ' + Y(points[0].n_total);
    for (var i = 1; i < n; i++) d += ' L ' + X(i) + ' ' + Y(points[i].n_total);
    var area = d + ' L ' + X(n - 1) + ' ' + (padT + iH) + ' L ' + X(0) + ' ' + (padT + iH) + ' Z';
    s.appendChild(svg('path', { d: area, class: 'ov-area' }));
    s.appendChild(svg('path', { d: d, class: 'ov-line' }));

    // failure overlay (only if any)
    var anyFail = points.some(function (p) { return p.n_failure > 0; });
    if (anyFail) {
      var fd = 'M ' + X(0) + ' ' + Y(points[0].n_failure);
      for (var j = 1; j < n; j++) fd += ' L ' + X(j) + ' ' + Y(points[j].n_failure);
      s.appendChild(svg('path', { d: fd, class: 'ov-line-fail' }));
    }
    mount.appendChild(s);

    // date range under the chart
    var range = el('div', { class: 'ov-hero-range' });
    range.appendChild(el('span', { text: shortTs(points[0].ts) }));
    range.appendChild(el('span', { text: shortTs(points[n - 1].ts) }));
    mount.appendChild(range);
  }

  function shortTs(ts) {
    if (!ts) return '';
    // ts is 'YYYY-MM-DDTHH:MM:SS'; show date, plus time only for sub-day ranges.
    return ts.slice(0, 10);
  }

  function renderSparkline(mount, values, tone) {
    mount.textContent = '';
    if (!values || !values.length) return;
    var W = 100, H = 26, max = 1;
    values.forEach(function (v) { if (v > max) max = v; });
    var n = values.length;
    var s = svg('svg', { viewBox: '0 0 ' + W + ' ' + H, class: 'ov-spark-svg', preserveAspectRatio: 'none' });
    function X(i) { return n === 1 ? W / 2 : (i / (n - 1)) * W; }
    function Y(v) { return H - 2 - (v / max) * (H - 4); }
    var d = 'M ' + X(0) + ' ' + Y(values[0]);
    for (var i = 1; i < n; i++) d += ' L ' + X(i) + ' ' + Y(values[i]);
    var p = svg('path', { d: d, fill: 'none', stroke: tone || TONE.total, 'stroke-width': '1.5' });
    s.appendChild(p);
    mount.appendChild(s);
  }

  // Horizontal bars: fill width is n_total / max, split into success + failure.
  function renderBars(mount, cats) {
    mount.textContent = '';
    if (!cats || !cats.length) {
      mount.appendChild(el('div', { class: 'ov-empty', text: 'No data in this window.' }));
      return;
    }
    var max = 1;
    cats.forEach(function (c) { if (c.n_total > max) max = c.n_total; });
    cats.forEach(function (c) {
      var row = el('div', { class: 'ov-bar-row' });
      row.appendChild(el('span', { class: 'ov-bar-label', title: c.label, text: c.label }));
      var track = el('span', { class: 'ov-bar-track' });
      var okN = Math.max(0, c.n_total - c.n_failure);
      var ok = el('span', { class: 'ov-bar-fill' });
      ok.style.width = (100 * okN / max) + '%';
      track.appendChild(ok);
      if (c.n_failure > 0) {
        var bad = el('span', { class: 'ov-bar-fill ov-bar-fill-fail',
          title: c.n_failure + ' non-success' });
        bad.style.width = (100 * c.n_failure / max) + '%';
        track.appendChild(bad);
      }
      row.appendChild(track);
      row.appendChild(el('span', { class: 'ov-bar-val', text: fmtInt(c.n_total) }));
      mount.appendChild(row);
    });
  }

  // A single stacked bar of category shares (for the disclosure mix).
  function renderMix(mount, cats) {
    mount.textContent = '';
    if (!cats || !cats.length) return;
    var total = 0;
    cats.forEach(function (c) { total += c.n_total; });
    if (!total) return;
    var mixTone = { ZERO_KNOWLEDGE: TONE.zk, SELECTIVE: '#38bdf8', FULL: '#fbbf24' };
    var bar = el('div', { class: 'ov-mix-bar' });
    var legend = el('div', { class: 'ov-mix-legend' });
    cats.forEach(function (c) {
      var pct = 100 * c.n_total / total;
      var seg = el('span', { class: 'ov-mix-seg', title: c.label + ' ' + fmtPct(pct) });
      seg.style.width = pct + '%';
      seg.style.background = mixTone[c.label] || '#64748b';
      bar.appendChild(seg);
      var li = el('span', { class: 'ov-mix-li' });
      var dot = el('i', { class: 'ov-mix-dot' }); dot.style.background = mixTone[c.label] || '#64748b';
      li.appendChild(dot);
      li.appendChild(el('span', { text: prettyLabel(c.label) + ' ' + fmtPct(pct) }));
      legend.appendChild(li);
    });
    mount.appendChild(bar);
    mount.appendChild(legend);
  }

  function prettyLabel(s) {
    return String(s).replace(/_/g, ' ').toLowerCase().replace(/^./, function (m) { return m.toUpperCase(); });
  }

  // =========================================================================
  // Overview data load
  // =========================================================================
  function setKpi(key, text) {
    var n = $('[data-ov-kpi="' + key + '"]', overview);
    if (n) n.textContent = text;
  }
  function setSub(key, text) {
    var n = $('[data-ov-kpi-sub="' + key + '"]', overview);
    if (n) n.textContent = text;
  }
  function showError(msg) {
    var box = $('[data-ov-error]', overview);
    if (!box) return;
    box.hidden = false;
    var d = $('[data-ov-error-detail]', overview);
    if (d) d.textContent = msg || 'Could not load analytics.';
  }
  function hideError() {
    var box = $('[data-ov-error]', overview);
    if (box) box.hidden = true;
  }

  var loadSeq = 0;
  function loadOverview() {
    var seq = ++loadSeq;
    hideError();
    configurePanels();
    var q = 'window=' + encodeURIComponent(state.window) + '&kind=' + encodeURIComponent(state.stream);

    // 1) the volume series drives the hero + the volume/failure/zk KPIs.
    apiCall('/api/atlas/series?' + q + '&buckets=48').then(function (data) {
      if (seq !== loadSeq) return;
      var pts = data.points || [];
      renderHero($('[data-ov-hero]', overview), pts);
      var vol = 0, fail = 0, zk = 0;
      pts.forEach(function (p) { vol += p.n_total; fail += p.n_failure; zk += p.n_zk; });
      setKpi('volume', fmtInt(vol));
      setSub('volume', windowLabel(data));
      setKpi('failure-rate', vol ? fmtPct(100 * fail / vol) : '0%');
      setSub('failure-rate', fmtInt(fail) + ' non-success');
      if (state.stream === 'verification') setKpi('zk', vol ? fmtPct(100 * zk / vol) : '0%');
      renderSparkline($('[data-ov-spark="volume"]', overview), pts.map(function (p) { return p.n_total; }), TONE.total);
      renderSparkline($('[data-ov-spark="failure"]', overview), pts.map(function (p) { return p.n_failure; }), TONE.fail);
      if (state.stream === 'verification')
        renderSparkline($('[data-ov-spark="zk"]', overview), pts.map(function (p) { return p.n_zk; }), TONE.zk);
      var scope = $('[data-ov-scope]', overview);
      if (scope) scope.textContent = pts.length ? (shortTs(pts[0].ts) + ' → ' + shortTs(pts[pts.length - 1].ts)) : '';
    }).catch(function (e) { if (seq === loadSeq) showError('Volume series failed: ' + e.message); });

    // 2) the breakdown panels.
    PANELS[state.stream].forEach(function (panel) {
      var mount = $('[data-ov-breakdown="' + panel.key + '"]', overview);
      if (!mount) return;
      apiCall('/api/atlas/breakdown?' + q + '&dimension=' + panel.dim + '&limit=12').then(function (data) {
        if (seq !== loadSeq) return;
        var cats = data.categories || [];
        renderBars(mount, cats);
        if (panel.mix) {
          var mixMount = $('[data-ov-mix="disclosure"]', overview);
          if (mixMount) renderMix(mixMount, cats);
        }
      }).catch(function (e) { if (seq === loadSeq) showError('Breakdown failed: ' + e.message); });
    });
  }

  function windowLabel(data) {
    if (state.window === 'all') return 'all recorded';
    return 'last ' + state.window;
  }

  // Show only the panels this stream has data for; retitle the shared mounts.
  function configurePanels() {
    var active = PANELS[state.stream];
    var byKey = {};
    active.forEach(function (p) { byKey[p.key] = p; });
    $$('[data-ov-panel]', overview).forEach(function (card) {
      var key = card.getAttribute('data-ov-panel');
      var p = byKey[key];
      card.hidden = !p;
      if (p) {
        var title = $('.ov-card-title', card);
        if (title) title.textContent = p.title;
        var mixMount = $('[data-ov-mix]', card);
        if (mixMount) mixMount.hidden = !p.mix;
      }
    });
    // the hero title + zk KPI visibility follow the stream
    var ht = $('[data-ov-hero-title]', overview);
    if (ht) ht.textContent = state.stream === 'verification' ? 'Verification volume' : 'Lifecycle volume';
    var zkCard = $('[data-ov-kpi="zk"]', overview);
    if (zkCard) {
      var card = zkCard.closest('.ov-kpi');
      if (card) card.hidden = state.stream !== 'verification';
    }
  }

  // =========================================================================
  // Breakdown view (v9.249): slice one dimension, then cross-tab it against
  // outcome and disclosure so an anomalous profile stands out.
  // =========================================================================
  var bd = $('[data-atlas-view-panel="breakdown"]');
  var bdState = { stream: 'verification', window: 'all', dim: 'agency', metric: 'volume', search: '' };
  var BD_DIMS = {
    verification: [
      { key: 'agency', label: 'Agency' }, { key: 'context', label: 'Context' },
      { key: 'jurisdiction', label: 'Jurisdiction' }, { key: 'algorithm', label: 'Algorithm' }
    ],
    lifecycle: [{ key: 'agency', label: 'Agency' }]
  };
  var BD_XTABS = {
    verification: [
      { col: 'outcome', title: 'Profile by outcome' },
      { col: 'disclosure', title: 'Profile by disclosure' }
    ],
    lifecycle: [{ col: 'event_type', title: 'Profile by event type' }]
  };
  var COL_TONE = {
    SUCCESS: '#5fd9a2', FAILURE: '#f87171', EXPIRED: '#fbbf24', UNAUTHORIZED: '#f87171',
    ZERO_KNOWLEDGE: '#a78bfa', SELECTIVE: '#38bdf8', FULL: '#fbbf24'
  };
  function hexA(hex, a) {
    var n = parseInt(hex.slice(1), 16);
    return 'rgba(' + ((n >> 16) & 255) + ',' + ((n >> 8) & 255) + ',' + (n & 255) + ',' + a.toFixed(3) + ')';
  }

  function bdSetChips(attr, value, root) {
    $$('[' + attr + ']', root || bd).forEach(function (c) {
      var on = c.getAttribute(attr) === value;
      c.classList.toggle('toolbar-chip-active', on);
      c.setAttribute('aria-checked', on ? 'true' : 'false');
    });
  }
  function bdBuildDimPicker() {
    var group = $('[data-bd-dim-group]', bd);
    if (!group) return;
    group.textContent = '';
    BD_DIMS[bdState.stream].forEach(function (d) {
      var b = el('button', { class: 'toolbar-chip', type: 'button', role: 'radio',
        'data-bd-dim': d.key, 'aria-checked': 'false', text: d.label });
      b.addEventListener('click', function () {
        bdState.dim = d.key; bdSetChips('data-bd-dim', d.key); bdClearSearch(); loadBreakdown();
      });
      group.appendChild(b);
    });
    // keep a valid selection when switching streams
    if (!BD_DIMS[bdState.stream].some(function (d) { return d.key === bdState.dim; }))
      bdState.dim = BD_DIMS[bdState.stream][0].key;
    bdSetChips('data-bd-dim', bdState.dim);
  }
  if (bd) {
    $$('[data-bd-stream]', bd).forEach(function (c) {
      c.addEventListener('click', function () {
        bdState.stream = c.getAttribute('data-bd-stream');
        bdSetChips('data-bd-stream', bdState.stream); bdClearSearch(); bdBuildDimPicker(); loadBreakdown();
      });
    });
    $$('[data-bd-window]', bd).forEach(function (c) {
      c.addEventListener('click', function () {
        bdState.window = c.getAttribute('data-bd-window');
        bdSetChips('data-bd-window', bdState.window); loadBreakdown();
      });
    });
    $$('[data-bd-metric]', bd).forEach(function (c) {
      c.addEventListener('click', function () {
        bdState.metric = c.getAttribute('data-bd-metric');
        bdSetChips('data-bd-metric', bdState.metric);
        if (bdLastCats) renderRankedTable($('[data-bd-ranked]', bd), bdLastCats, bdState.metric);
      });
    });
    var bdRetry = $('[data-bd-retry]', bd);
    if (bdRetry) bdRetry.addEventListener('click', loadBreakdown);
    var bdSearchEl = $('[data-bd-search]', bd);
    if (bdSearchEl) {
      var bdSearchTimer = null;
      bdSearchEl.addEventListener('input', function () {
        clearTimeout(bdSearchTimer);
        bdSearchTimer = setTimeout(function () {
          bdState.search = bdSearchEl.value.trim();
          loadRanked();   // only the list re-fetches; the cross-tabs are unaffected by a label filter
        }, 220);
      });
    }
    bdBuildDimPicker();
  }

  function bdClearSearch() {
    bdState.search = '';
    var elx = $('[data-bd-search]', bd);
    if (elx) elx.value = '';
  }

  function renderRankedTable(mount, cats, metric) {
    if (!mount) return;
    mount.textContent = '';
    if (!cats || !cats.length) { mount.appendChild(el('div', { class: 'ov-empty', text: 'No data in this window.' })); return; }
    var total = cats.reduce(function (a, c) { return a + c.n_total; }, 0) || 1;
    var maxV = Math.max.apply(null, cats.map(function (c) { return c.n_total; })) || 1;
    var sorted = cats.slice().sort(function (a, b) {
      if (metric === 'failure') {
        var ra = a.n_total ? a.n_failure / a.n_total : 0, rb = b.n_total ? b.n_failure / b.n_total : 0;
        return (rb - ra) || (b.n_total - a.n_total);
      }
      return b.n_total - a.n_total;
    });
    var head = el('div', { class: 'bd-row bd-row-head' });
    head.appendChild(el('span', { class: 'bd-row-label', text: 'Category' }));
    head.appendChild(el('span', { class: 'bd-row-barhead', text: 'Volume' }));
    head.appendChild(el('span', { class: 'bd-row-vol', text: '#' }));
    head.appendChild(el('span', { class: 'bd-row-rate', text: 'Fail %' }));
    head.appendChild(el('span', { class: 'bd-row-share', text: 'Share' }));
    mount.appendChild(head);
    sorted.forEach(function (c) {
      var rate = c.n_total ? c.n_failure / c.n_total : 0;
      var row = el('div', { class: 'bd-row' });
      row.appendChild(el('span', { class: 'bd-row-label', title: c.label, text: c.label }));
      var track = el('span', { class: 'ov-bar-track' });
      var ok = el('span', { class: 'ov-bar-fill' }); ok.style.width = (100 * (c.n_total - c.n_failure) / maxV) + '%'; track.appendChild(ok);
      if (c.n_failure > 0) { var bad = el('span', { class: 'ov-bar-fill ov-bar-fill-fail' }); bad.style.width = (100 * c.n_failure / maxV) + '%'; track.appendChild(bad); }
      row.appendChild(track);
      row.appendChild(el('span', { class: 'bd-row-vol', text: fmtInt(c.n_total) }));
      row.appendChild(el('span', { class: 'bd-row-rate' + (rate >= 0.15 ? ' bd-rate-high' : ''), text: fmtPct(100 * rate) }));
      row.appendChild(el('span', { class: 'bd-row-share', text: fmtPct(100 * c.n_total / total) }));
      mount.appendChild(row);
    });
  }

  function renderMatrix(mount, data) {
    if (!mount) return;
    mount.textContent = '';
    if (!data || !data.rows.length || !data.cols.length) {
      mount.appendChild(el('div', { class: 'ov-empty', text: 'No data in this window.' })); return;
    }
    var lut = {};
    data.cells.forEach(function (c) { lut[c.row + ' ' + c.col] = c.n; });
    var grid = el('div', { class: 'bd-matrix-grid' });
    grid.style.gridTemplateColumns = 'minmax(84px,1.3fr) repeat(' + data.cols.length + ', 1fr) auto';
    grid.appendChild(el('span', { class: 'bd-mx-corner' }));
    data.cols.forEach(function (col) { grid.appendChild(el('span', { class: 'bd-mx-colhead', title: col, text: prettyLabel(col) })); });
    grid.appendChild(el('span', { class: 'bd-mx-colhead bd-mx-total', text: 'Total' }));
    data.rows.forEach(function (r) {
      grid.appendChild(el('span', { class: 'bd-mx-rowhead', title: r.label, text: r.label }));
      data.cols.forEach(function (col) {
        var n = lut[r.label + ' ' + col] || 0;
        var share = r.total ? n / r.total : 0;
        var cell = el('span', { class: 'bd-mx-cell', text: n ? fmtInt(n) : '·',
          title: r.label + ' · ' + prettyLabel(col) + ': ' + fmtInt(n) + ' (' + fmtPct(100 * share) + ' of row)' });
        cell.style.background = n ? hexA(COL_TONE[col] || '#8da6c4', 0.10 + 0.60 * share) : 'transparent';
        if (share >= 0.5 && n) cell.classList.add('bd-mx-strong');
        grid.appendChild(cell);
      });
      grid.appendChild(el('span', { class: 'bd-mx-cell bd-mx-total', text: fmtInt(r.total) }));
    });
    mount.appendChild(grid);
  }

  function bdShowError(msg) {
    var box = $('[data-bd-error]', bd); if (!box) return;
    box.hidden = false; var d = $('[data-bd-error-detail]', bd); if (d) d.textContent = msg;
  }

  var bdRankedSeq = 0, bdXtabSeq = 0, bdLastCats = null;

  // The ranked dimension list. Re-fetched on its own for search (a label filter
  // narrows the list without touching the cross-tabs), so thousands of agencies
  // stay findable and the list scrolls inside its own card.
  function loadRanked() {
    if (!bd) return;
    var seq = ++bdRankedSeq;
    var box = $('[data-bd-error]', bd); if (box) box.hidden = true;
    var dim = bdState.dim;
    var title = $('[data-bd-ranked-title]', bd);
    if (title) title.textContent = 'By ' + dim;
    var q = 'window=' + encodeURIComponent(bdState.window) + '&kind=' + encodeURIComponent(bdState.stream)
          + '&dimension=' + dim + '&limit=40'
          + (bdState.search ? '&search=' + encodeURIComponent(bdState.search) : '');
    apiCall('/api/atlas/breakdown?' + q).then(function (data) {
      if (seq !== bdRankedSeq) return;
      bdLastCats = data.categories || [];
      renderRankedTable($('[data-bd-ranked]', bd), bdLastCats, bdState.metric);
      var foot = $('[data-bd-count]', bd);
      if (foot) {
        var n = bdLastCats.length, s = bdState.search;
        var plural = n === 1 ? dim : dim.replace(/y$/, 'ie') + 's';
        if (n === 0) foot.textContent = s ? 'No ' + dim + ' matches "' + s + '".' : 'No data in this window.';
        else if (data.truncated) foot.textContent = 'Top ' + n + ' by volume' + (s ? ' matching "' + s + '"' : '') + ' — refine the filter to narrow';
        else foot.textContent = n + ' ' + plural + (s ? ' matching "' + s + '"' : '');
      }
    }).catch(function (e) { if (seq === bdRankedSeq) bdShowError('Breakdown failed: ' + e.message); });
  }

  function loadBreakdown() {
    if (!bd) return;
    loadRanked();
    var seq = ++bdXtabSeq;
    var dim = bdState.dim;
    var q = 'window=' + encodeURIComponent(bdState.window) + '&kind=' + encodeURIComponent(bdState.stream);
    var xtabs = BD_XTABS[bdState.stream];
    ['outcome', 'disclosure'].forEach(function (colKey) {
      var card = $('[data-bd-xtab-card="' + colKey + '"]', bd);
      var conf = xtabs.filter(function (x) { return x.col === colKey; })[0];
      // for lifecycle, reuse the 'outcome' card slot to show the event_type matrix
      if (!conf && colKey === 'outcome' && bdState.stream === 'lifecycle') conf = xtabs[0];
      if (card) card.hidden = !conf;
      if (!conf) return;
      var mount = $('[data-bd-crosstab="' + colKey + '"]', bd);
      var tEl = $('[data-bd-xtab-title="' + colKey + '"]', bd);
      if (tEl) tEl.textContent = conf.title;
      apiCall('/api/atlas/crosstab?' + q + '&row=' + dim + '&col=' + conf.col + '&limit=20').then(function (data) {
        if (seq !== bdXtabSeq) return;
        renderMatrix(mount, data);
      }).catch(function (e) { if (seq === bdXtabSeq) bdShowError('Cross-tab failed: ' + e.message); });
    });
  }

  // initial paint
  loadOverview();

  // LIVE refresh (shared cadence with the map). Skip when the tab is hidden.
  setInterval(function () {
    if (document.hidden) return;
    if (!overview.hidden) loadOverview();
    else if (bd && !bd.hidden) loadBreakdown();
  }, 60000);
})();
