#!/usr/bin/env python3
"""ai_swarm_map.py — Mycelium swarm visualizer (v9.14).

Generates an interactive D3 force-directed graph dedicated to the
Mycelium swarm — distinct from `ai_brain_map.py` which visualizes the
whole system. The swarm map's job is to show:

  - 11 manifested legions (9 Republican + 2 Imperial) + 1 reserved slot
  - All commander ants (~33) clustered under their legion
  - All soldier classes (8 workers + 1 priest swarm_witness)
  - All citizens (6: Plebs, Equites, Augures, Censores, Quaestores,
    Tribuni Plebis)
  - The Pheromone substrate as the underlying field that every
    deposit flows into
  - HYDRA watchers as the outer observation ring (the lens that reads
    the swarm)
  - Optionally: live deposit-count edges per ant/soldier (when a DB
    connection is available)

The visualization complements the brain-map by giving operators a
swarm-native view. The brain-map answers "how is everything wired?";
the swarm map answers "who is alive, what are they doing, how do they
relate?"

Output: `meta/swarm-map/swarm-map.html` (self-contained; uses the same
vendored d3.v7.min.js as the brain-map).

CLI:
    python3 scripts/ai_swarm_map.py              # generate
    python3 scripts/ai_swarm_map.py --live       # also query DB for
                                                 # per-ant deposit cadence
"""

from __future__ import annotations

import datetime
import json
import os
import pathlib
import re
import sys
from typing import Any

_REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
_OUT_PATH = _REPO_ROOT / "meta" / "swarm-map" / "swarm-map.html"
_ASSETS_DIR = _REPO_ROOT / "meta" / "swarm-map" / "assets"

# Cluster groups (used by D3 force layout for color + spatial layout)
G_REPUBLICAN = "republican"   # 9 Republican legions
G_IMPERIAL   = "imperial"     # 2 Imperial legions (+ 1 reserved)
G_ANT        = "ant"          # commander ants
G_SOLDIER    = "soldier"      # soldier worker classes
G_PRIEST     = "priest"       # the priest tier (soldier_swarm_witness)
G_CITIZEN    = "citizen"      # citizen classes
G_SUBSTRATE  = "substrate"    # Pheromone substrate
G_LENS       = "lens"         # HYDRA watchers (outer ring)
G_TREASURY   = "treasury"     # Civitas treasury (Denarius)


class SwarmGraphBuilder:
    """Walks the polaris_swarm/ tree + reads pheromone_reader to
    enumerate every tier in the swarm. Pure local-file analysis;
    optional DB query for live deposit cadence."""

    def __init__(self, root: pathlib.Path, live: bool = False):
        self.root = root
        self.live = live
        self.nodes: dict[str, dict[str, Any]] = {}
        self.links: list[dict[str, Any]] = []

    def add_node(self, node_id: str, label: str, ntype: str, group: str,
                 **attrs: Any) -> None:
        if node_id in self.nodes:
            return
        self.nodes[node_id] = {
            "id": node_id,
            "label": label,
            "type": ntype,
            "group": group,
            **attrs,
        }

    def add_link(self, src: str, dst: str, ltype: str = "relates",
                 **attrs: Any) -> None:
        # Defer source/target validation; D3 tolerates missing nodes
        # by creating them implicitly but we prefer not to.
        if src not in self.nodes or dst not in self.nodes:
            return
        self.links.append({
            "source": src,
            "target": dst,
            "type": ltype,
            **attrs,
        })

    # ------- Parsers ------------------------------------------------

    def parse_pheromone_substrate(self) -> None:
        """The substrate is the field every deposit flows into. Render
        as a single anchor node + a halo of "shared correlation surfaces"
        from v9.10."""
        self.add_node(
            "substrate:pheromone",
            "Pheromone substrate",
            "substrate", G_SUBSTRATE,
            description="The stigmergic field; every ant + soldier + "
                        "citizen + priest deposits here. Append-only.",
        )
        # v9.10 shared correlation surfaces (runtime:health + runtime:swarm,
        # with runtime:auth held reserved)
        for surface in ("runtime:health", "runtime:swarm", "runtime:auth"):
            reserved = (surface == "runtime:auth")
            self.add_node(
                f"surface:{surface}",
                surface + (" (RESERVED)" if reserved else ""),
                "correlation_surface", G_SUBSTRATE,
                reserved=reserved,
            )
            self.add_link(f"surface:{surface}", "substrate:pheromone",
                          "shared_surface_in")

    def parse_legions(self) -> None:
        """Walk polaris_swarm/legions/__init__.py for REPUBLICAN/IMPERIAL
        registries + the reserved twelfth slot."""
        sys.path.insert(0, str(self.root))
        try:
            from polaris_swarm.legions import (
                REPUBLICAN_LEGIONS, IMPERIAL_LEGIONS,
                RESERVED_TWELFTH_LEGION_SLOT,
            )
        except Exception as exc:  # noqa: BLE001
            print(f"swarm-map: legion import failed: {exc}", file=sys.stderr)
            return
        for cls in REPUBLICAN_LEGIONS:
            name = getattr(cls, "NAME", cls.__name__).lower()
            domain = getattr(cls, "DOMAIN", "")
            self.add_node(
                f"legion:{name}",
                cls.__name__,
                "republican_legion", G_REPUBLICAN,
                domain=domain,
                ants=[a.NAME for a in getattr(cls, "ANTS", [])
                      if hasattr(a, "NAME")],
            )
        for cls in IMPERIAL_LEGIONS:
            name = getattr(cls, "NAME", cls.__name__).lower()
            domain = getattr(cls, "DOMAIN", "")
            self.add_node(
                f"legion:{name}",
                cls.__name__,
                "imperial_legion", G_IMPERIAL,
                domain=domain,
                ants=[a.NAME for a in getattr(cls, "ANTS", [])
                      if hasattr(a, "NAME")],
            )
        if RESERVED_TWELFTH_LEGION_SLOT.get("manifested") is False:
            self.add_node(
                "legion:reserved_twelfth",
                "(twelfth — RESERVED)",
                "reserved_legion", G_IMPERIAL,
                manifested=False,
                reserved_at=RESERVED_TWELFTH_LEGION_SLOT.get(
                    "reserved_at", "v9.11"),
                rationale=RESERVED_TWELFTH_LEGION_SLOT.get("rationale", ""),
            )

    def parse_ants(self) -> None:
        """Each commander ant is a child of a legion. Use the legion's
        ANTS attribute as ground truth (walking the legions resolves
        the ant→legion mapping deterministically)."""
        try:
            from polaris_swarm.legions import (
                REPUBLICAN_LEGIONS, IMPERIAL_LEGIONS,
            )
        except Exception:  # noqa: BLE001
            return
        for cls in REPUBLICAN_LEGIONS + IMPERIAL_LEGIONS:
            legion_id = f"legion:{getattr(cls, 'NAME', '').lower()}"
            for ant_cls in getattr(cls, "ANTS", []):
                ant_name = getattr(ant_cls, "NAME", "")
                if not ant_name:
                    continue
                desc = getattr(ant_cls, "DESCRIPTION", "")
                ant_id = f"ant:{ant_name}"
                self.add_node(ant_id, ant_name, "commander_ant", G_ANT,
                              description=desc)
                self.add_link(ant_id, legion_id, "serves_in")
                self.add_link(ant_id, "substrate:pheromone", "deposits_to")

    def parse_soldiers(self) -> None:
        """Each soldier class is in polaris_swarm/soldiers/<class>.py.
        soldier_swarm_witness is the priest tier (added v9.11)."""
        sdir = self.root / "polaris_swarm" / "soldiers"
        if not sdir.is_dir():
            return
        for f in sorted(sdir.glob("*.py")):
            if f.stem in ("base", "__init__"):
                continue
            try:
                src = f.read_text(errors="replace")
            except OSError:
                continue
            m = re.search(r'NAME\s*=\s*"(soldier_\w+)"', src)
            if not m:
                continue
            name = m.group(1)
            desc_m = re.search(
                r'DESCRIPTION\s*=\s*"([^"]+)"', src,
            )
            desc = desc_m.group(1) if desc_m else ""
            is_priest = (name == "soldier_swarm_witness")
            self.add_node(
                f"soldier:{name}", name,
                "priest_soldier" if is_priest else "worker_soldier",
                G_PRIEST if is_priest else G_SOLDIER,
                description=desc,
                tier="priest" if is_priest else "worker",
            )
            self.add_link(f"soldier:{name}", "substrate:pheromone",
                          "deposits_to")
            # The priest watches the workers (v9.11 design intent)
            if is_priest:
                # Witness reads other soldiers; add observation edges
                # for each worker class enumerated in OBSERVED_WORKERS
                worker_match = re.search(
                    r"OBSERVED_WORKERS[^=]*=\s*\(([^)]+)\)",
                    src, re.DOTALL,
                )
                if worker_match:
                    for wm in re.finditer(
                        r'"(soldier_\w+)"', worker_match.group(1)
                    ):
                        worker = wm.group(1)
                        if worker != name:
                            self.add_link(
                                f"soldier:{name}",
                                f"soldier:{worker}",
                                "witnesses",
                            )

    def parse_citizens(self) -> None:
        """Citizens live in polaris_swarm/civitas/. Six classes:
        Plebs, Equites, Augures, Censores, Quaestores, Tribuni Plebis."""
        cdir = self.root / "polaris_swarm" / "civitas"
        if not cdir.is_dir():
            return
        for f in sorted(cdir.glob("*.py")):
            if f.stem in ("base", "__init__", "treasury"):
                continue
            try:
                src = f.read_text(errors="replace")
            except OSError:
                continue
            cls_m = re.search(r"^class\s+(\w+)\(Citizen\):", src, re.MULTILINE)
            if not cls_m:
                continue
            cls_name = cls_m.group(1)
            # Citizen NAME attr
            name_m = re.search(r'NAME\s*=\s*"([^"]+)"', src)
            display = name_m.group(1) if name_m else cls_name
            desc_m = re.search(r'DESCRIPTION\s*=\s*"([^"]+)"', src)
            desc = desc_m.group(1) if desc_m else ""
            self.add_node(
                f"citizen:{display}", display, "citizen", G_CITIZEN,
                description=desc,
            )
            self.add_link(f"citizen:{display}", "substrate:pheromone",
                          "observes")

    def parse_treasury(self) -> None:
        """The Civitas treasury (Denarius). Single anchor node; receives
        F5 reward flows from drift-resolution; pays penalty flows on
        persistent silence."""
        ttable = self.root / "polaris_swarm" / "civitas" / "treasury.py"
        if not ttable.is_file():
            return
        self.add_node(
            "treasury:civitas", "Treasury (Denarius)",
            "treasury", G_TREASURY,
            description="F5 reward function in operation. Rewards "
                        "drift-resolution; penalties on persistent silence.",
        )
        # The Quaestor citizen tends the Treasury
        if "citizen:quaestor_treasurer" in self.nodes:
            self.add_link(
                "citizen:quaestor_treasurer", "treasury:civitas",
                "tends",
            )

    def parse_hydra_watchers(self) -> None:
        """HYDRA watchers are the OUTER RING — the lens that observes
        the substrate. Render them outside the swarm body. Distinct
        from the commander tier; observer not participant."""
        self.add_node(
            "hydra:host", "HYDRA host (lens)",
            "hydra_host", G_LENS,
        )
        wdir = self.root / "polaris_hydra" / "watchers"
        if not wdir.is_dir():
            return
        for f in sorted(wdir.glob("*_watcher.py")):
            name = f.stem.replace("_watcher", "")
            label = name.capitalize() + "Watcher"
            self.add_node(f"watcher:{name}", label, "watcher", G_LENS)
            self.add_link(f"watcher:{name}", "hydra:host", "reports_to")
            self.add_link(f"watcher:{name}", "substrate:pheromone",
                          "reads")

    def parse_live_cadence(self) -> None:
        """Optional --live: query Pheromone table for per-depositor
        deposit counts in last hour. Annotates ant/soldier/citizen
        nodes with a `recent_deposits` attribute; D3 layer can render
        edge weight or node radius from this."""
        if not self.live:
            return
        try:
            import psycopg2  # type: ignore
        except ImportError:
            return
        try:
            conn = psycopg2.connect(
                host=os.environ.get("POLARIS_DB_HOST", "localhost"),
                dbname=os.environ.get("POLARIS_DB_NAME", "polaris_test"),
                user=os.environ.get("POLARIS_DB_USER",
                                    os.environ.get("USER", "polaris_app")),
                password=os.environ.get("POLARIS_DB_PASSWORD", ""),
                connect_timeout=2,
            )
        except Exception:  # noqa: BLE001
            return
        try:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT deposited_by, COUNT(*)
                  FROM Pheromone
                 WHERE deposited_at >= NOW() - INTERVAL '1 hour'
                 GROUP BY deposited_by
                """
            )
            for depositor, cnt in cur.fetchall():
                # Match ant_*, soldier_*, citizen_* prefix → node key
                for prefix, group_key in (
                    ("ant_",     "ant:"),
                    ("soldier_", "soldier:"),
                ):
                    if depositor.startswith(prefix):
                        node_id = group_key + depositor
                        if node_id in self.nodes:
                            self.nodes[node_id]["recent_deposits"] = int(cnt)
                        break
                else:
                    # Citizens may deposit under their NAME (often a
                    # role name, not prefixed)
                    cn_id = f"citizen:{depositor}"
                    if cn_id in self.nodes:
                        self.nodes[cn_id]["recent_deposits"] = int(cnt)
            cur.close()
        except Exception:  # noqa: BLE001
            pass
        finally:
            try:
                conn.close()
            except Exception:  # noqa: BLE001
                pass

    def build(self) -> dict[str, Any]:
        self.parse_pheromone_substrate()
        self.parse_legions()
        self.parse_ants()
        self.parse_soldiers()
        self.parse_citizens()
        self.parse_treasury()
        self.parse_hydra_watchers()
        self.parse_live_cadence()
        return {
            "nodes": list(self.nodes.values()),
            "links": self.links,
            "generated_at": datetime.datetime.now(
                datetime.timezone.utc
            ).isoformat(timespec="seconds"),
            "polaris_version": self._read_version(),
            "node_count": len(self.nodes),
            "link_count": len(self.links),
            "live_data_enabled": self.live,
        }

    def _read_version(self) -> str:
        try:
            sys.path.insert(0, str(self.root))
            from polaris_web.__version__ import POLARIS_VERSION  # type: ignore
            return f"v{POLARIS_VERSION}"
        except Exception:  # noqa: BLE001
            return "v?"


_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Polaris Swarm Map · v__VERSION__</title>
<script src="assets/d3.v7.min.js"></script>
<style>
  body { margin: 0; background: #0a0e1a; color: #d8d8c4;
         font-family: -apple-system, BlinkMacSystemFont, "Segoe UI",
         "Helvetica Neue", sans-serif; overflow: hidden; }
  #header { position: fixed; top: 0; left: 0; right: 0; padding: 12px 16px;
            background: linear-gradient(180deg, rgba(10,14,26,0.95), rgba(10,14,26,0.6));
            z-index: 10; border-bottom: 1px solid #2a3550; }
  #header h1 { margin: 0 0 4px 0; font-size: 15px; letter-spacing: 1px;
               color: #f2c14e; font-weight: 600; }
  #header .meta { font-size: 11px; color: #889; }
  #legend { position: fixed; bottom: 16px; left: 16px;
            background: rgba(10,14,26,0.85); border: 1px solid #2a3550;
            border-radius: 4px; padding: 10px 14px; font-size: 11px;
            z-index: 10; }
  #legend .swatch { display: inline-block; width: 10px; height: 10px;
                    border-radius: 50%; vertical-align: middle;
                    margin-right: 6px; }
  #legend div { margin: 3px 0; }
  #tooltip { position: fixed; padding: 8px 12px;
             background: rgba(10,14,26,0.95); border: 1px solid #2a3550;
             border-radius: 4px; font-size: 12px; pointer-events: none;
             opacity: 0; transition: opacity 0.1s; z-index: 20;
             max-width: 320px; line-height: 1.4; }
  svg { width: 100vw; height: 100vh; display: block; }
  .node circle { stroke: #0a0e1a; stroke-width: 1.5px; cursor: pointer; }
  .node text { font-size: 10px; fill: #aab; pointer-events: none;
               text-shadow: 0 0 3px #0a0e1a; }
  .link { stroke-opacity: 0.4; }
  .link.witnesses { stroke-dasharray: 3 3; stroke-opacity: 0.6; }
  .link.shared_surface_in { stroke: #f2c14e; stroke-opacity: 0.5; }
  .reserved { stroke-dasharray: 4 4; opacity: 0.5; }
</style>
</head>
<body>
<div id="header">
  <h1>Polaris Swarm Map · __VERSION__</h1>
  <div class="meta">
    <span id="counts">…</span> · generated __GENERATED__
    · <a href="brain-map.html" style="color:#7ab">brain-map</a>
  </div>
</div>
<div id="legend">
  <div><strong>Tiers</strong></div>
  <div><span class="swatch" style="background:#7ab"></span>Republican legion (9)</div>
  <div><span class="swatch" style="background:#c47"></span>Imperial legion (2 + 1 reserved)</div>
  <div><span class="swatch" style="background:#5b8"></span>Commander ant</div>
  <div><span class="swatch" style="background:#fd6"></span>Soldier worker (8)</div>
  <div><span class="swatch" style="background:#f2c14e"></span>Priest (soldier_swarm_witness)</div>
  <div><span class="swatch" style="background:#a8a"></span>Citizen (6)</div>
  <div><span class="swatch" style="background:#444"></span>Pheromone substrate</div>
  <div><span class="swatch" style="background:#258"></span>HYDRA watcher (lens)</div>
  <div><span class="swatch" style="background:#a72"></span>Treasury (Denarius)</div>
</div>
<div id="tooltip"></div>
<svg></svg>
<script id="graph-data" type="application/json">__GRAPH_JSON__</script>
<script>
const GROUP_COLOR = {
  "republican": "#7ab",
  "imperial":   "#c47",
  "ant":        "#5b8",
  "soldier":    "#fd6",
  "priest":     "#f2c14e",
  "citizen":    "#a8a",
  "substrate":  "#444",
  "lens":       "#258",
  "treasury":   "#a72",
};
const GROUP_RADIUS = {
  "republican": 14,
  "imperial":   14,
  "ant":        7,
  "soldier":    10,
  "priest":     12,
  "citizen":    11,
  "substrate":  20,
  "lens":       12,
  "treasury":   16,
};

const raw = JSON.parse(document.getElementById("graph-data").textContent);
const nodes = raw.nodes;
const links = raw.links;
document.getElementById("counts").textContent =
  raw.node_count + " nodes · " + raw.link_count + " links"
  + (raw.live_data_enabled ? " · live data" : "");

const svg = d3.select("svg");
const W = window.innerWidth, H = window.innerHeight;

// Force layout: substrate at center; lens (HYDRA) outer ring; legions
// around center; ants/soldiers/citizens cluster near their parents.
const simulation = d3.forceSimulation(nodes)
  .force("link", d3.forceLink(links).id(d => d.id).distance(d => {
    if (d.type === "serves_in" || d.type === "reads") return 60;
    if (d.type === "deposits_to" || d.type === "observes") return 80;
    if (d.type === "witnesses") return 100;
    return 70;
  }).strength(0.5))
  .force("charge", d3.forceManyBody().strength(d => {
    if (d.group === "substrate") return -1500;
    if (d.group === "lens")      return -400;
    return -200;
  }))
  .force("center", d3.forceCenter(W / 2, H / 2))
  .force("collide", d3.forceCollide().radius(d => (GROUP_RADIUS[d.group] || 8) + 3));

// Radial pin for substrate at center; lens nodes on outer ring;
// Republican/Imperial on inner ring.
simulation.force("radial", d3.forceRadial(d => {
  if (d.group === "substrate") return 0;
  if (d.group === "lens")      return Math.min(W, H) * 0.42;
  if (d.group === "republican" || d.group === "imperial") return Math.min(W, H) * 0.27;
  if (d.group === "treasury")  return Math.min(W, H) * 0.22;
  return 0;
}, W / 2, H / 2).strength(d => {
  if (d.group === "substrate" || d.group === "lens" ||
      d.group === "republican" || d.group === "imperial" ||
      d.group === "treasury") return 0.5;
  return 0;
}));

const link = svg.append("g").selectAll("line")
  .data(links).enter().append("line")
  .attr("class", d => "link " + d.type)
  .attr("stroke", d => d.type === "shared_surface_in" ? "#f2c14e" : "#445");

const node = svg.append("g").selectAll("g")
  .data(nodes).enter().append("g")
  .attr("class", d => "node" + (d.manifested === false || d.reserved ? " reserved" : ""))
  .call(d3.drag()
    .on("start", (e, d) => { if (!e.active) simulation.alphaTarget(0.3).restart(); d.fx = d.x; d.fy = d.y; })
    .on("drag",  (e, d) => { d.fx = e.x; d.fy = e.y; })
    .on("end",   (e, d) => { if (!e.active) simulation.alphaTarget(0);   d.fx = null; d.fy = null; })
  );

node.append("circle")
  .attr("r", d => {
    // Live data: scale radius by recent_deposits (sqrt for area-proportional)
    const base = GROUP_RADIUS[d.group] || 8;
    if (raw.live_data_enabled && d.recent_deposits) {
      return base + Math.min(8, Math.sqrt(d.recent_deposits));
    }
    return base;
  })
  .attr("fill", d => GROUP_COLOR[d.group] || "#888")
  .attr("stroke-dasharray", d => d.manifested === false || d.reserved ? "4 4" : "")
  .attr("opacity", d => d.manifested === false || d.reserved ? 0.5 : 1.0);

node.append("text")
  .attr("dy", d => (GROUP_RADIUS[d.group] || 8) + 12)
  .attr("text-anchor", "middle")
  .text(d => {
    // Show full labels for top tier; abbreviated for ants
    if (d.group === "ant") return d.label.replace(/^ant_/, "");
    if (d.group === "soldier" || d.group === "priest") return d.label.replace(/^soldier_/, "");
    return d.label;
  });

// Tooltip
const tooltip = d3.select("#tooltip");
node.on("mouseover", (e, d) => {
  let html = `<strong>${d.label}</strong><br><span style="color:#889">${d.type}</span>`;
  if (d.description) html += `<br><br>${d.description}`;
  if (d.domain)      html += `<br><br>domain: ${d.domain}`;
  if (d.ants && d.ants.length) html += `<br><br>ants (${d.ants.length}): ${d.ants.join(", ")}`;
  if (d.recent_deposits !== undefined)
    html += `<br><br><strong style="color:#f2c14e">recent (1h): ${d.recent_deposits} deposits</strong>`;
  if (d.tier === "priest")
    html += `<br><br><em>The priest tier (v9.11). Witnesses the other soldiers + emits witness:swarm:* meta-pheromone.</em>`;
  if (d.manifested === false)
    html += `<br><br><em>Held in deliberate reserve. Manifest via Sanctum when operational need surfaces.</em>`;
  tooltip.html(html).style("opacity", 0.95);
}).on("mousemove", (e) => {
  tooltip.style("left", (e.pageX + 14) + "px")
         .style("top",  (e.pageY + 14) + "px");
}).on("mouseout", () => tooltip.style("opacity", 0));

simulation.on("tick", () => {
  link
    .attr("x1", d => d.source.x)
    .attr("y1", d => d.source.y)
    .attr("x2", d => d.target.x)
    .attr("y2", d => d.target.y);
  node.attr("transform", d => `translate(${d.x},${d.y})`);
});

// Zoom + pan
svg.call(d3.zoom().scaleExtent([0.3, 4]).on("zoom", (e) => {
  svg.select("g").attr("transform", e.transform);
  svg.selectAll("g.node").attr("transform", d => `translate(${e.transform.applyX(d.x)},${e.transform.applyY(d.y)})`);
}));
</script>
</body>
</html>
"""


def render_html(graph: dict[str, Any]) -> str:
    blob = json.dumps(graph, separators=(",", ":"))
    blob = blob.replace("</", "<\\/")
    html = _HTML_TEMPLATE
    html = html.replace("__VERSION__", graph["polaris_version"])
    html = html.replace("__GENERATED__", graph["generated_at"])
    html = html.replace("__GRAPH_JSON__", blob)
    return html


def _ensure_d3_vendored() -> None:
    """Reuse the brain-map's vendored d3 instead of re-downloading."""
    target = _ASSETS_DIR / "d3.v7.min.js"
    if target.exists():
        return
    _ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    src = _REPO_ROOT / "meta" / "brain-map" / "assets" / "d3.v7.min.js"
    if src.exists():
        target.write_bytes(src.read_bytes())


def main(argv: list[str]) -> int:
    live = "--live" in argv
    _ensure_d3_vendored()
    builder = SwarmGraphBuilder(_REPO_ROOT, live=live)
    graph = builder.build()
    html = render_html(graph)
    _OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    _OUT_PATH.write_text(html, encoding="utf-8")
    print(f"polaris swarm-map written: {_OUT_PATH}", file=sys.stderr)
    print(f"  {graph['node_count']} nodes · "
          f"{graph['link_count']} links · "
          f"version {graph['polaris_version']}"
          f"{' · live data' if graph['live_data_enabled'] else ''}",
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
