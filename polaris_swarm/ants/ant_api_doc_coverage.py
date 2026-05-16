"""ant_api_doc_coverage — pheromones for undocumented /api/* routes.

Slice: each `@app.route('/api/...')` decorator in
`polaris_web/app.py` paired with the corresponding `### ` heading in
`docs/reference/API.md`.

Local rule: if a route exists in app.py but no matching heading
exists in API.md, deposit an `alert` pheromone onto that route's
brain-map node.

This is the v8.61 Polish 1 finding (4 routes were missing from
API.md pre-v8.61). The ant exists so any new route added without a
corresponding doc surface gets immediate attention. The pheromone
will fade if the docs are added; it will persist (and accumulate
intensity across multiple deposits) if the gap remains.
"""

from __future__ import annotations

import re

from polaris_swarm.base import Ant, AntFinding, KIND_ALERT, KIND_INFO


_ROUTE_RE = re.compile(
    r"@app\.route\(['\"](/api/[^'\"]+)['\"](?:,\s*methods=\[([^\]]+)\])?",
    re.MULTILINE,
)
# Normalize Flask route patterns: /api/zk/epoch/<int:epoch_id> -> /api/zk/epoch/<int
# (the brain-map and the docs both elide the typed parameter suffix the same way)


def _normalize_route(route: str) -> str:
    """Strip Flask type converters: '/api/zk/epoch/<int:epoch_id>' -> '/api/zk/epoch/<int'."""
    return re.sub(r":(?:int|float|string|path|uuid)>", ">", route).split(">")[0].rstrip("<") + (
        ">" if "<" in route else ""
    )


class AntApiDocCoverage(Ant):
    NAME = "ant_api_doc_coverage"
    DESCRIPTION = "Pheromones routes that exist in app.py but lack API.md headings."

    def scan(self) -> list[AntFinding]:
        findings: list[AntFinding] = []
        app_text = self._read("polaris_web", "app.py")
        docs_text = self._read("docs", "reference", "API.md")
        if app_text is None or docs_text is None:
            return findings

        # Build set of documented routes.
        # API.md uses headings like:  ### `GET /api/atlas/timeline`
        doc_headings = re.findall(
            r"^### `(GET|POST) (/api/[^`]+)`", docs_text, re.MULTILINE
        )
        documented = {(method, path) for method, path in doc_headings}

        # Walk app.py routes.
        seen: set[tuple[str, str]] = set()
        for m in _ROUTE_RE.finditer(app_text):
            raw_path, methods_str = m.group(1), m.group(2)
            methods = ["GET"]
            if methods_str:
                methods = [
                    s.strip().strip("'\"").upper() for s in methods_str.split(",")
                ]
            for method in methods:
                # Match against documented set with type-converter normalization.
                # We strip both sides to a common form for comparison.
                norm_raw = re.sub(r"<[^>]+>", "<...>", raw_path)
                norm_doc_paths = {
                    (mm, re.sub(r"<[^>]+>", "<...>", pp))
                    for mm, pp in documented
                }
                if (method, norm_raw) in norm_doc_paths:
                    continue
                key = (method, raw_path)
                if key in seen:
                    continue
                seen.add(key)
                findings.append(AntFinding(
                    node_id=f"route:{raw_path}",
                    intensity=4.0,
                    kind=KIND_ALERT,
                    evidence={
                        "message": "route exists in app.py but missing from docs/reference/API.md",
                        "method": method,
                        "route": raw_path,
                        "fix_hint": f"add '### `{method} {raw_path}`' heading to docs/reference/API.md",
                    },
                ))
        return findings
