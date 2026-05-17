#!/usr/bin/env python3
"""Polaris brain-map analyzer — v8.54.

Companion to `ai_brain_map.py`. Loads the generated brain map JSON
and emits a structured findings report covering:

  - Topology summary (nodes, edges, components, density)
  - Layer distribution (mean degree per layer)
  - Top-10 hubs
  - Orphans by layer (degree 0 + degree 1)
  - Cross-layer edges (which layers actually talk)
  - Missing-edge suggestions (heuristic — `X looks like it should
    connect to Y but doesn't`). Surfaces parser gaps without
    inventing speculative structure.

Authorized by: VANTA's "proceed with your recommendation" on the
v8.54 Shape-A analyzer proposal. Replaces the prior `neuro surgeon
agent` framing with a non-agentic, deterministic gap-surfacer that
proposes edges *for human review*, not auto-applied.

Read-only. Deterministic. Graceful-failure.

Usage:
    bash scripts/ai-brain-map.sh --analyze
    python3 scripts/ai_brain_map_analyze.py            # stdout report
    python3 scripts/ai_brain_map_analyze.py --write    # also write
                                                       # meta/brain-map/brain-map-analysis.md
"""

from __future__ import annotations

import json
import pathlib
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone


def load_graph(repo_root: pathlib.Path) -> dict:
    """Extract the embedded JSON from meta/brain-map/brain-map.html, plus
    the version string from the HTML title bar."""
    html_path = repo_root / "meta" / "brain-map" / "brain-map.html"
    if not html_path.is_file():
        raise FileNotFoundError(
            f"{html_path} not found. Run scripts/ai-brain-map.sh first."
        )
    html = html_path.read_text(errors="replace")
    m = re.search(
        r'id="graph-data"[^>]*>(.*?)</script>',
        html, re.DOTALL,
    )
    if not m:
        raise ValueError("graph-data script tag not found in brain-map.html")
    graph = json.loads(m.group(1).replace("<\\/", "</"))
    # Pull version + generation timestamp from the HTML body so the
    # report header isn't "unknown".
    ver_m = re.search(r'<span id="ver">(v[\d\.]+)</span>', html)
    if ver_m:
        graph["polaris_version"] = ver_m.group(1)
    gen_m = re.search(
        r'<span id="gen-time">generated ([^<]+)</span>', html
    )
    if gen_m:
        graph["map_generated_at"] = gen_m.group(1)
    return graph


def analyze(graph: dict, repo_root: pathlib.Path) -> str:
    """Run the full analysis. Returns a markdown report string."""
    nodes = graph["nodes"]
    links = graph["links"]
    N = {n["id"]: n for n in nodes}
    n_count = len(nodes)

    # Adjacency + degree
    adj: dict[str, set[str]] = defaultdict(set)
    for l in links:
        s = l["source"] if isinstance(l["source"], str) else l["source"]["id"]
        t = l["target"] if isinstance(l["target"], str) else l["target"]["id"]
        adj[s].add(t)
        adj[t].add(s)
    deg = {nid: len(adj[nid]) for nid in N}

    # Connected components (BFS)
    seen: set[str] = set()
    components: list[set[str]] = []
    for nid in N:
        if nid in seen:
            continue
        comp: set[str] = set()
        stack = [nid]
        while stack:
            x = stack.pop()
            if x in comp:
                continue
            comp.add(x)
            for y in adj[x]:
                if y not in comp:
                    stack.append(y)
        seen.update(comp)
        components.append(comp)
    components.sort(key=len, reverse=True)
    n_singletons = sum(1 for c in components if len(c) == 1)

    # Density
    max_edges = n_count * (n_count - 1) // 2 if n_count else 0
    density = len(links) / max_edges if max_edges else 0
    mean_degree = sum(deg.values()) / n_count if n_count else 0
    median_degree = sorted(deg.values())[n_count // 2] if n_count else 0
    max_degree = max(deg.values()) if deg else 0

    # Layer distribution
    group_counts = Counter(n["group"] for n in nodes)
    group_degree: dict[str, list[int]] = defaultdict(list)
    for nid, nd in N.items():
        group_degree[nd["group"]].append(deg[nid])
    group_mean_deg = {
        g: sum(d) / len(d) if d else 0
        for g, d in group_degree.items()
    }

    # Hubs
    hubs = sorted(N.values(), key=lambda nd: -deg[nd["id"]])[:10]

    # Orphans by layer
    orphans_by_group: dict[str, dict[str, list[dict]]] = defaultdict(
        lambda: {"d0": [], "d1": []}
    )
    for nid, nd in N.items():
        if deg[nid] == 0:
            orphans_by_group[nd["group"]]["d0"].append(nd)
        elif deg[nid] == 1:
            orphans_by_group[nd["group"]]["d1"].append(nd)

    # Cross-layer edges
    cross_counts: Counter[tuple[str, str, str]] = Counter()
    for l in links:
        s = l["source"] if isinstance(l["source"], str) else l["source"]["id"]
        t = l["target"] if isinstance(l["target"], str) else l["target"]["id"]
        gs = N[s]["group"]
        gt = N[t]["group"]
        if gs == gt:
            cross_counts[(gs, gs, "intra")] += 1
        else:
            a, b = sorted([gs, gt])
            cross_counts[(a, b, "inter")] += 1

    # Edge-type distribution
    ltype_counts = Counter(l["type"] for l in links)

    # ------------------------------------------------------------------
    # Missing-edge suggestions (the "more connections" goal)
    # ------------------------------------------------------------------
    suggestions = _find_missing_edges(N, links, repo_root)

    # ------------------------------------------------------------------
    # Render markdown
    # ------------------------------------------------------------------
    out: list[str] = []
    out.append(f"# Polaris brain-map analysis — "
               f"{graph.get('polaris_version', 'unknown')}")
    out.append("")
    out.append(f"Generated: {datetime.now(timezone.utc).isoformat(timespec='seconds')}")
    out.append(f"Map: `meta/brain-map/brain-map.html`")
    out.append("")

    out.append("## I. Topology")
    out.append("")
    out.append(f"| Metric | Value |")
    out.append(f"|---|---|")
    out.append(f"| Nodes | {n_count} |")
    out.append(f"| Edges | {len(links)} |")
    out.append(f"| Connected components | {len(components)} |")
    out.append(f"| Largest component | {len(components[0])} "
               f"({100*len(components[0])/n_count:.1f}%) |")
    out.append(f"| Isolated singletons | {n_singletons} |")
    out.append(f"| Graph density | {density:.4f} |")
    out.append(f"| Mean degree | {mean_degree:.2f} |")
    out.append(f"| Median degree | {median_degree} |")
    out.append(f"| Max degree | {max_degree} |")
    out.append("")

    out.append("## II. Layer distribution")
    out.append("")
    out.append("| Layer | Nodes | Mean degree |")
    out.append("|---|---|---|")
    for g in sorted(group_counts.keys(),
                    key=lambda k: -group_counts[k]):
        out.append(f"| {g} | {group_counts[g]} "
                   f"| {group_mean_deg[g]:.2f} |")
    out.append("")

    out.append("## III. Top-10 hubs")
    out.append("")
    out.append("| Degree | Group | Type | Label |")
    out.append("|---|---|---|---|")
    for nd in hubs:
        out.append(f"| {deg[nd['id']]} | {nd['group']} "
                   f"| {nd['type']} | `{nd['label']}` |")
    out.append("")

    out.append("## IV. Orphans by layer")
    out.append("")
    out.append("Nodes with degree 0 (no connections) or degree 1 "
               "(single connection). High d0 counts in a layer "
               "indicate parser miss OR genuinely isolated nodes "
               "(e.g., the schema's `AuthAuditLog` admin-log).")
    out.append("")
    for g in sorted(orphans_by_group.keys()):
        d0 = orphans_by_group[g]["d0"]
        d1 = orphans_by_group[g]["d1"]
        if not (d0 or d1):
            continue
        out.append(f"### {g}  (d0={len(d0)}, d1={len(d1)})")
        out.append("")
        for nd in d0[:6]:
            out.append(f"- d0: ({nd['type']}) `{nd['label']}`")
        if len(d0) > 6:
            out.append(f"- d0: ... +{len(d0)-6} more")
        for nd in d1[:6]:
            n_id = nd["id"]
            if adj[n_id]:
                neigh = next(iter(adj[n_id]))
                neigh_nd = N.get(neigh)
                if neigh_nd:
                    out.append(f"- d1: ({nd['type']}) `{nd['label']}` "
                               f"→ ({neigh_nd['type']}) `{neigh_nd['label']}`")
        if len(d1) > 6:
            out.append(f"- d1: ... +{len(d1)-6} more")
        out.append("")

    out.append("## V. Cross-layer edges")
    out.append("")
    intra = sorted([(k, v) for k, v in cross_counts.items()
                    if k[2] == "intra"],
                   key=lambda x: -x[1])
    inter = sorted([(k, v) for k, v in cross_counts.items()
                    if k[2] == "inter"],
                   key=lambda x: -x[1])
    out.append("### Intra-layer (edges within a single layer)")
    out.append("")
    for (a, _, _), c in intra:
        out.append(f"- `{a}`: {c}")
    out.append("")
    out.append("### Inter-layer (top 10 cross-layer edges)")
    out.append("")
    for (a, b, _), c in inter[:10]:
        out.append(f"- `{a}` ↔ `{b}`: {c}")
    out.append("")

    out.append("## VI. Edge-type distribution")
    out.append("")
    out.append("| Type | Count |")
    out.append("|---|---|")
    for t, c in sorted(ltype_counts.items(), key=lambda kv: -kv[1]):
        out.append(f"| `{t}` | {c} |")
    out.append("")

    out.append("## VII. Missing-edge suggestions")
    out.append("")
    out.append(f"**{sum(len(v) for v in suggestions.values())} potential "
               f"edges surfaced by heuristic.** Each is a *suggestion for "
               f"human review*, not a recommendation to auto-add. The "
               f"system grows by VANTA's deliberate decisions, not by "
               f"agent inference. Review and either:")
    out.append("")
    out.append("- (a) accept the suggestion → extend the parser to "
               "extract this edge class deterministically next time;")
    out.append("- (b) reject as not-a-real-connection → no action;")
    out.append("- (c) add explicit `# brain-map:` annotation in the "
               "source file to make the relationship machine-readable.")
    out.append("")
    for category, items in suggestions.items():
        if not items:
            continue
        out.append(f"### {category}  ({len(items)})")
        out.append("")
        for item in items[:20]:
            out.append(f"- {item}")
        if len(items) > 20:
            out.append(f"- ... +{len(items)-20} more")
        out.append("")

    out.append("## VIII. Architect's read")
    out.append("")
    largest_pct = 100 * len(components[0]) / n_count
    if largest_pct >= 80:
        verdict = ("Graph is highly connected — one large component "
                   "captures most of the system. Parser is doing its "
                   "job.")
    elif largest_pct >= 50:
        verdict = ("Graph is moderately connected — the schema + "
                   "cognitive layers form the spine. Other layers are "
                   "less linked. Review §VII suggestions to close "
                   "specific gaps.")
    else:
        verdict = ("Graph is sparse — many singletons and small "
                   "components. Either the parser is missing edge "
                   "classes, the system is genuinely fragmented, or "
                   "(most likely) some node types are reference "
                   "material that doesn't naturally cite outward.")
    out.append(verdict)
    out.append("")
    out.append(f"**Connectivity progress over time:**")
    out.append(f"- v8.52: 216 nodes / 126 links / 113 components")
    out.append(f"- v8.53: 219 nodes / 243 links / 72 components")
    out.append(f"- v8.54: {n_count} nodes / {len(links)} links / "
               f"{len(components)} components "
               f"(largest = {len(components[0])} = {largest_pct:.1f}%)")
    out.append("")

    return "\n".join(out)


def _find_missing_edges(
    N: dict, links: list, repo_root: pathlib.Path
) -> dict[str, list[str]]:
    """Heuristics for `this looks like it should be connected but
    isn't`. Each finding is a string description for human review.

    Categories:
      - sanctum_mentions_ship: sanctum body mentions a ship slug
        not currently linked via `authorized`
      - watcher_mentions_constraint_not_linked: watcher source
        mentions Cn not yet captured by `monitors`
      - ship_mentions_sanctum: ship doc references a Sanctum slug
        not currently linked
      - devnote_referenced_but_floating: devnote is heavily cited
        but cites nothing outward (parser limit OR reference-only)
      - script_named_but_not_invoked: ai-* script exists but no
        other script calls it (orphan in cognitive layer)
    """
    out: dict[str, list[str]] = defaultdict(list)

    # Build lookups for existing edges
    existing_edges: set[tuple[str, str, str]] = set()
    inbound: dict[str, set[str]] = defaultdict(set)
    outbound: dict[str, set[str]] = defaultdict(set)
    for l in links:
        s = l["source"] if isinstance(l["source"], str) else l["source"]["id"]
        t = l["target"] if isinstance(l["target"], str) else l["target"]["id"]
        existing_edges.add((s, t, l["type"]))
        outbound[s].add(t)
        inbound[t].add(s)

    # Ship slug → ship node id
    ship_ids = {
        nd["id"].split(":", 1)[1]: nd["id"]
        for nd in N.values() if nd["type"] == "ship"
    }
    sanctum_ids = {
        nd["id"].split(":", 1)[1]: nd["id"]
        for nd in N.values() if nd["type"] == "sanctum"
    }

    # --- Sanctum body mentions ship slug not yet linked -----------------
    sanctum_dir = repo_root / "sanctum"
    if sanctum_dir.is_dir():
        for f in sorted(sanctum_dir.glob("*.md")):
            if f.name == "README.md":
                continue
            s_id = f"sanctum:{f.stem}"
            if s_id not in N:
                continue
            try:
                body = f.read_text(errors="replace").lower()
            except OSError:
                continue
            for slug, ship_id in ship_ids.items():
                # Only count substantive mentions: slug as whole word
                # in body. Skip if already linked.
                if (s_id, ship_id, "authorized") in existing_edges:
                    continue
                # word-boundary search to avoid 'token' matching
                # 'authtoken' etc.
                if re.search(rf"\b{re.escape(slug)}\b", body):
                    out["sanctum→ship mentions not yet linked"].append(
                        f"`sanctum/{f.stem}` mentions ship `{slug}` but "
                        f"no `authorized` edge"
                    )

    # --- Watcher source mentions Cn / CM not yet captured ---------------
    watchers_dir = repo_root / "polaris_hydra" / "watchers"
    if watchers_dir.is_dir():
        for f in sorted(watchers_dir.glob("*_watcher.py")):
            wname = f.stem.replace("_watcher", "")
            wid = f"watcher:{wname}"
            if wid not in N:
                continue
            try:
                body = f.read_text(errors="replace")
            except OSError:
                continue
            mentioned = set(re.findall(r"\b(C\d{1,2}|CM)\b", body))
            for cid in mentioned:
                if cid == "CM" or 1 <= int(cid[1:]) <= 10:
                    cnode = f"constraint:{cid}"
                    if cnode in N and (wid, cnode, "monitors") not in existing_edges:
                        out["watcher→C-constraint mentions not yet linked"].append(
                            f"`{wname}_watcher.py` mentions `{cid}` but "
                            f"no `monitors` edge"
                        )

    # --- Ship doc references a Sanctum slug not linked ------------------
    ships_dir = repo_root / "DEVNOTES" / "ships"
    if ships_dir.is_dir():
        for f in sorted(ships_dir.glob("*.md")):
            ship_id = f"ship:{f.stem}"
            if ship_id not in N:
                continue
            try:
                body = f.read_text(errors="replace")
            except OSError:
                continue
            for sslug, s_id in sanctum_ids.items():
                if (s_id, ship_id, "authorized") in existing_edges:
                    continue
                # Look for explicit Sanctum filename in body
                if sslug in body:
                    out["ship→sanctum references not yet linked"].append(
                        f"`ships/{f.stem}.md` references "
                        f"`sanctum/{sslug}` but no `authorized` edge"
                    )

    # --- DEVNOTES heavily-cited but degree-1 ----------------------------
    devnote_ids = [
        nid for nid, nd in N.items() if nd["type"] == "devnote"
    ]
    for d_id in devnote_ids:
        in_deg = len(inbound[d_id])
        out_deg = len(outbound[d_id])
        total_deg = len(inbound[d_id] | outbound[d_id])
        # Note: inbound + outbound may include same edges going both
        # ways in undirected reading. Approximate.
        if in_deg >= 2 and out_deg == 0:
            label = N[d_id]["label"]
            out["devnote: heavily cited inbound, cites nothing out"].append(
                f"`DEVNOTES/{label}.md` cited by {in_deg} other "
                f"node(s) but cites no other DEVNOTES/ships/sanctums"
            )

    # --- ai-* script named but not invoked ------------------------------
    for nid, nd in N.items():
        if nd["type"] != "ai_script":
            continue
        n_inbound = len([l for l in links
                         if (l["target"] if isinstance(l["target"], str)
                             else l["target"]["id"]) == nid
                         and l["type"] == "invokes"])
        if n_inbound == 0:
            out["ai-script: no inbound `invokes` edge (orphan callee)"].append(
                f"`{nd['label']}` exists but no other script invokes it"
            )

    return out


def main(argv: list[str]) -> int:
    repo_root = pathlib.Path(__file__).resolve().parent.parent
    try:
        graph = load_graph(repo_root)
    except (FileNotFoundError, ValueError) as e:
        print(f"ai-brain-map --analyze: {e}", file=sys.stderr)
        return 1

    report = analyze(graph, repo_root)

    # Always print to stdout
    print(report)

    # If --write flag, also persist to meta/brain-map/brain-map-analysis.md
    if "--write" in argv:
        out_path = repo_root / "meta" / "brain-map-analysis.md"
        out_path.write_text(report, encoding="utf-8")
        print(f"\n[written to {out_path}]", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
