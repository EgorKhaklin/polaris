#!/usr/bin/env python3
"""Polaris Brain Map Generator — v8.52 / v8.53 parser-v2 / v8.54 trigger fix.

Parses Polaris's structural artifacts (schema, procedures, routes,
watchers, ai-* scripts, Sanctums, ships, principles, DEVNOTES) and
emits an interactive D3 force-directed graph at
`meta/brain-map/brain-map.html`.

Audience: future agents priming themselves + VANTA visualizing the
hive mind of the system.

Authorized by: VANTA's "ship now" on the Architect's Shape-A
proposal (Shape A = generator script + standalone HTML artifact,
not in the web UI). No Sanctum required — this is a pure-additive
documentation artifact, not a constitutional change.

Read-only. Deterministic. Graceful-failure: missing source files
produce a smaller graph rather than a crash. Honors the v8.44 G1-G5
watcher contract by analogy even though this isn't a watcher.

Edge extractors (13 total as of v8.54):
  - parse_schema_fks            (fk)
  - parse_schema_indexes        (indexes)
  - parse_triggers              (fires_on; v8.54 regex fix for UPDATE OF col)
  - parse_route_calls           (calls — narrow, route-body uc_proc())
  - parse_route_calls_broad     (calls — broader uc\\w+ mention scan)
  - parse_watcher_reports       (reports_to)
  - parse_sanctum_authorized    (authorized — frontmatter)
  - parse_sanctum_outcome_ships (authorized — §VII outcome parsing)
  - parse_sanctum_realizes      (realizes)
  - parse_constraint_constrains (constrains)
  - parse_constraint_enforcement (enforced_by)
  - parse_procedure_locks       (uses)
  - parse_script_calls          (invokes — script→script)
  - parse_markdown_cross_refs   (links_to — backtick-quoted paths)
  - parse_watcher_constraints   (monitors — watcher→C-constraint)

Companion: `ai_brain_map_analyze.py` consumes the generated graph
and surfaces topology/hubs/orphans/missing-edge suggestions.

Usage:
    python3 scripts/ai_brain_map.py      # writes meta/brain-map/brain-map.html
    bash scripts/ai-brain-map.sh         # convenience wrapper
"""

from __future__ import annotations

import json
import pathlib
import re
import sys
from datetime import datetime, timezone

# ---------------------------------------------------------------------
# Node-group categories drive node coloring + the legend.
# ---------------------------------------------------------------------
G_SCHEMA       = "schema"        # tables, indexes, triggers
G_BEHAVIOR     = "behavior"      # routes + procedures (system behavior)
G_COGNITIVE    = "cognitive"     # ai-* scripts (the executable cognitive layer)
G_DECISION     = "decision"      # sanctums + ships (strategic decisions)
G_CONSTITUTION = "constitution"  # C1-C10, CM, 4 principles
G_OBSERVATION  = "observation"   # HYDRA host + 7 watchers
G_KNOWLEDGE    = "knowledge"     # DEVNOTES (durable memory)


class GraphBuilder:
    """Build a {nodes, links} graph from Polaris's artifacts."""

    def __init__(self, root: pathlib.Path):
        self.root = root
        self.nodes: dict[str, dict] = {}
        self.links: list[dict] = []
        self._table_names: set[str] = set()
        self._proc_names: set[str] = set()
        self._sanctum_slugs: set[str] = set()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def add_node(self, node_id: str, label: str, type_: str,
                 group: str, **meta) -> None:
        if node_id in self.nodes:
            self.nodes[node_id].update(meta)
            return
        self.nodes[node_id] = {
            "id": node_id, "label": label, "type": type_,
            "group": group, **meta,
        }

    def add_link(self, source: str, target: str, type_: str,
                 value: int = 1) -> None:
        if source not in self.nodes or target not in self.nodes:
            return
        self.links.append({
            "source": source, "target": target,
            "type": type_, "value": value,
        })

    def _read(self, *parts: str) -> str | None:
        path = self.root.joinpath(*parts)
        if not path.is_file():
            return None
        try:
            return path.read_text(errors="replace")
        except OSError:
            return None

    # ------------------------------------------------------------------
    # Parsers — one per artifact class
    # ------------------------------------------------------------------

    def parse_schema_tables(self) -> None:
        body = self._read("polaris_sql", "01_schema.sql")
        if body is None:
            return
        # Match CREATE TABLE Name ( ... );  (greedy across newlines until `);`)
        for m in re.finditer(
            r"CREATE\s+TABLE\s+(\w+)\s*\((.*?)^\);",
            body, re.DOTALL | re.MULTILINE | re.IGNORECASE,
        ):
            table = m.group(1)
            block = m.group(2)
            self._table_names.add(table.lower())
            self.add_node(
                f"table:{table.lower()}", table,
                "schema_table", G_SCHEMA,
            )
            # FK edges: REFERENCES TableName ...
            for ref in re.finditer(
                r"REFERENCES\s+(\w+)", block, re.IGNORECASE
            ):
                target = ref.group(1)
                if target.lower() == table.lower():
                    continue
                # Add the target table node (may be defined later in file)
                self.add_node(
                    f"table:{target.lower()}", target,
                    "schema_table", G_SCHEMA,
                )
                self.add_link(
                    f"table:{table.lower()}",
                    f"table:{target.lower()}", "fk",
                )

    def parse_indexes(self) -> None:
        for fname in ("02_indexes.sql", "12_v7_constraints.sql"):
            body = self._read("polaris_sql", fname)
            if body is None:
                continue
            for m in re.finditer(
                r"CREATE\s+(?:UNIQUE\s+)?INDEX\s+(?:IF\s+NOT\s+EXISTS\s+)?"
                r"(\w+)\s+ON\s+(\w+)",
                body, re.IGNORECASE,
            ):
                idx = m.group(1)
                table = m.group(2)
                self.add_node(
                    f"index:{idx}", idx, "index", G_SCHEMA,
                )
                self.add_node(
                    f"table:{table.lower()}", table,
                    "schema_table", G_SCHEMA,
                )
                self.add_link(
                    f"index:{idx}",
                    f"table:{table.lower()}", "indexes",
                )

    def parse_triggers(self) -> None:
        body = self._read("polaris_sql", "06_triggers.sql")
        if body is None:
            return
        # v8.54: extended event-spec pattern to allow `UPDATE OF col`
        # (column-list trigger form). v8.52 regex required plain
        # `UPDATE` or `UPDATE OR DELETE` etc., missing the 3 triggers
        # in 06_triggers.sql that use `BEFORE UPDATE OF status` /
        # `AFTER UPDATE OF status`. Each event token is now
        # optionally followed by `OF column`.
        event_token = r"\w+(?:\s+OF\s+\w+)?"
        events = rf"{event_token}(?:\s+OR\s+{event_token})*"
        for m in re.finditer(
            rf"CREATE\s+TRIGGER\s+(\w+)\s+"
            rf"(?:BEFORE|AFTER|INSTEAD\s+OF)\s+"
            rf"{events}\s+ON\s+(\w+)",
            body, re.IGNORECASE,
        ):
            trig = m.group(1)
            table = m.group(2)
            self.add_node(
                f"trigger:{trig}", trig, "trigger", G_SCHEMA,
            )
            self.add_node(
                f"table:{table.lower()}", table,
                "schema_table", G_SCHEMA,
            )
            self.add_link(
                f"trigger:{trig}",
                f"table:{table.lower()}", "fires_on",
            )

    def parse_procedures(self) -> None:
        body = self._read("polaris_sql", "05_procedures.sql")
        if body is None:
            return
        for m in re.finditer(
            r"CREATE\s+OR\s+REPLACE\s+(PROCEDURE|FUNCTION)\s+(\w+)",
            body, re.IGNORECASE,
        ):
            kind = m.group(1).upper()
            proc = m.group(2)
            self._proc_names.add(proc.lower())
            self.add_node(
                f"proc:{proc.lower()}", proc,
                kind.lower(), G_BEHAVIOR, kind=kind,
            )

    def parse_routes(self) -> None:
        body = self._read("polaris_web", "app.py")
        if body is None:
            return
        # @app.route('/path', methods=...)  optionally followed by
        # decorators, then def func_name(
        # Capture procedure CALLs inside route handlers in a second pass.
        route_pattern = re.compile(
            r"@app\.route\(\s*['\"]([^'\"]+)['\"][^)]*\)"
            # Decorator stack: allow `@module.func(...)` style with
            # dotted attribute access (e.g. `@security.login_required`,
            # `@security.require_role('admin')`).
            r"((?:\s*@[\w.]+(?:\([^)]*\))?)*)"
            r"\s*def\s+(\w+)",
            re.MULTILINE,
        )
        for m in route_pattern.finditer(body):
            route = m.group(1)
            decorators = m.group(2) or ""
            func = m.group(3)
            # Find the route handler body (from def to next top-level
            # def/@ at column 0). Used for procedure-call detection.
            start = m.end()
            tail = body[start:start + 20000]  # bounded slice
            end_m = re.search(r"^(@app\.route|def\s)", tail, re.MULTILINE)
            handler_body = tail[: end_m.start()] if end_m else tail[:5000]

            requires_role = bool(re.search(r"@\w*require_role", decorators))
            login_required = bool(re.search(r"@\w*login_required", decorators))

            self.add_node(
                f"route:{route}", route, "route", G_BEHAVIOR,
                handler=func,
                requires_role=requires_role,
                login_required=login_required,
            )

            # Procedure-call edges: heuristic scan for CALL uc\w+(
            for call in re.finditer(
                r"\bCALL\s+(uc\w+)\s*\(",
                handler_body, re.IGNORECASE,
            ):
                proc = call.group(1)
                self.add_node(
                    f"proc:{proc.lower()}", proc,
                    "procedure", G_BEHAVIOR,
                )
                self.add_link(
                    f"route:{route}", f"proc:{proc.lower()}",
                    "calls",
                )
            # Function-call edges: SELECT uc_func(...) FROM ...
            for fcall in re.finditer(
                r"SELECT\s+\*?\s*FROM\s+(uc\w+)\s*\(",
                handler_body, re.IGNORECASE,
            ):
                func_name = fcall.group(1)
                self.add_node(
                    f"proc:{func_name.lower()}", func_name,
                    "function", G_BEHAVIOR,
                )
                self.add_link(
                    f"route:{route}", f"proc:{func_name.lower()}",
                    "calls",
                )

    def parse_watchers(self) -> None:
        self.add_node(
            "hydra:host", "HYDRA host", "hydra_host", G_OBSERVATION,
        )
        watchers_dir = self.root / "polaris_hydra" / "watchers"
        if not watchers_dir.is_dir():
            return
        for f in sorted(watchers_dir.glob("*_watcher.py")):
            name = f.stem.replace("_watcher", "")
            label = name[:1].upper() + name[1:] + "Watcher"
            self.add_node(
                f"watcher:{name}", label, "watcher", G_OBSERVATION,
            )
            self.add_link(
                f"watcher:{name}", "hydra:host", "reports_to",
            )

    def parse_ai_scripts(self) -> None:
        scripts_dir = self.root / "scripts"
        if not scripts_dir.is_dir():
            return
        for f in sorted(scripts_dir.glob("ai-*.sh")):
            slug = f.stem  # e.g., "ai-meta"
            self.add_node(
                f"script:{slug}", slug, "ai_script", G_COGNITIVE,
            )

    def parse_foresight_package(self) -> None:
        """v9.12 / v9.14 — surface the polaris_foresight package as a
        cluster in the brain-map. Mirrors the parse_watchers pattern.
        Includes the ForesightAgent, Brief, promotion, and external
        categories file. The Layer-1 SQL helpers from
        polaris_sql/14_foresight_helpers.sql are picked up by
        parse_procedures (which already scans 05_procedures.sql and
        we now extend to 14_foresight_helpers.sql below in
        parse_foresight_sql_helpers).
        """
        fdir = self.root / "polaris_foresight"
        if not fdir.is_dir():
            return
        # Host node
        self.add_node(
            "foresight:host", "polaris_foresight",
            "foresight_host", G_OBSERVATION,
        )
        # Per-module nodes
        for fname, label in (
            ("foresight_agent.py", "ForesightAgent"),
            ("brief.py", "Brief"),
            ("promotion.py", "FS-XXXXXXXX promotion"),
            ("external_categories.txt", "external categories"),
            ("_acceptance_log.json", "acceptance log"),
            ("README.md", "foresight README"),
        ):
            if (fdir / fname).is_file():
                node_id = f"foresight:{fname}"
                self.add_node(node_id, label, "foresight_module", G_OBSERVATION)
                self.add_link(node_id, "foresight:host", "reports_to")

    def parse_foresight_sql_helpers(self) -> None:
        """v9.12 / v9.14 — surface foresight_token_age_distribution,
        foresight_verification_dormancy, foresight_audit_volume_trend
        from polaris_sql/14_foresight_helpers.sql."""
        body = self._read("polaris_sql", "14_foresight_helpers.sql")
        if not body:
            return
        for m in re.finditer(
            r"CREATE OR REPLACE FUNCTION\s+(foresight_\w+)",
            body, re.IGNORECASE,
        ):
            fn = m.group(1)
            self.add_node(
                f"proc:{fn.lower()}", fn, "function", G_BEHAVIOR,
                kind="FUNCTION",
            )

    def parse_action_promotion(self) -> None:
        """v9.11 — surface polaris_hydra/action_promotion.py + the
        AP-XXXXXXXX/FS-XXXXXXXX auto-promotion linkage to ROADMAP."""
        ap = self.root / "polaris_hydra" / "action_promotion.py"
        if ap.is_file():
            self.add_node(
                "module:action_promotion", "ActionQueue auto-promotion",
                "module", G_OBSERVATION,
            )
            # Link to HYDRA host (lives inside polaris_hydra/)
            self.add_link(
                "module:action_promotion", "hydra:host", "reports_to",
            )

    def parse_anti_architect(self) -> None:
        """v9.11 — surface the Anti-Architect persona as a cognitive-
        layer construct + its persona spec."""
        # The script (already picked up by parse_ai_scripts as
        # script:ai-anti-architect); persona spec is a meta/ artifact.
        spec = self.root / "meta" / "anti-architect.md"
        if spec.is_file():
            self.add_node(
                "meta:anti-architect", "Anti-Architect persona",
                "persona_spec", G_COGNITIVE,
            )
            # Linked to the architect persona spec (loyal opposition)
            arch_spec = self.root / "meta" / "architect.md"
            if arch_spec.is_file():
                self.add_node(
                    "meta:architect", "Architect persona",
                    "persona_spec", G_COGNITIVE,
                )
                self.add_link(
                    "meta:anti-architect", "meta:architect",
                    "loyal_opposition",
                )

    def parse_priest_soldier(self) -> None:
        """v9.11 — surface soldier_swarm_witness explicitly as the
        priest tier (distinct from the 8 workers)."""
        f = self.root / "polaris_swarm" / "soldiers" / "swarm_witness.py"
        if f.is_file():
            self.add_node(
                "soldier:swarm_witness", "soldier_swarm_witness (priest)",
                "priest_soldier", G_OBSERVATION,
            )

    def parse_legions(self) -> None:
        """v9.15 — surface all 11 manifest legions (9 Republican + 2
        Imperial). Each legion has its commander ants attached via
        parse_commander_ants below."""
        sys.path.insert(0, str(self.root))
        try:
            from polaris_swarm.legions import (  # type: ignore
                REPUBLICAN_LEGIONS, IMPERIAL_LEGIONS,
            )
        except Exception:  # noqa: BLE001
            return
        for cls in REPUBLICAN_LEGIONS:
            name = getattr(cls, "NAME", cls.__name__).lower()
            self.add_node(
                f"legion:{name}",
                cls.__name__,
                "republican_legion", G_OBSERVATION,
                domain=getattr(cls, "DOMAIN", ""),
            )
        for cls in IMPERIAL_LEGIONS:
            name = getattr(cls, "NAME", cls.__name__).lower()
            self.add_node(
                f"legion:{name}",
                cls.__name__,
                "imperial_legion", G_OBSERVATION,
                domain=getattr(cls, "DOMAIN", ""),
            )

    def parse_commander_ants(self) -> None:
        """v9.15 — surface every commander ant under its legion. The
        legion's ANTS attribute is ground truth for the ant→legion
        mapping."""
        sys.path.insert(0, str(self.root))
        try:
            from polaris_swarm.legions import (  # type: ignore
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
                ant_id = f"ant:{ant_name}"
                self.add_node(
                    ant_id, ant_name, "commander_ant", G_OBSERVATION,
                    description=getattr(ant_cls, "DESCRIPTION", ""),
                )
                self.add_link(ant_id, legion_id, "serves_in")

    def parse_worker_soldiers(self) -> None:
        """v9.15 — surface the eight v9.03 worker soldier classes.
        The ninth (priest) is added by parse_priest_soldier; this
        parser covers the workers only."""
        sdir = self.root / "polaris_swarm" / "soldiers"
        if not sdir.is_dir():
            return
        for f in sorted(sdir.glob("*.py")):
            if f.stem in ("base", "__init__", "swarm_witness"):
                continue
            try:
                src = f.read_text(errors="replace")
            except OSError:
                continue
            m = re.search(r'NAME\s*=\s*"(soldier_\w+)"', src)
            if not m:
                continue
            name = m.group(1)
            desc_m = re.search(r'DESCRIPTION\s*=\s*"([^"]+)"', src)
            desc = desc_m.group(1) if desc_m else ""
            self.add_node(
                f"soldier:{name}", name, "worker_soldier", G_OBSERVATION,
                description=desc,
            )

    def parse_citizens(self) -> None:
        """v9.15 — surface the six citizen classes (Plebs, Equites,
        Augures, Censores, Quaestores, Tribuni Plebis)."""
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
            name_m = re.search(r'NAME\s*=\s*"([^"]+)"', src)
            display = name_m.group(1) if name_m else cls_name
            desc_m = re.search(r'DESCRIPTION\s*=\s*"([^"]+)"', src)
            desc = desc_m.group(1) if desc_m else ""
            self.add_node(
                f"citizen:{display}", display, "citizen", G_OBSERVATION,
                description=desc,
            )

    def parse_treasury(self) -> None:
        """v9.15 — surface the Civitas Treasury (Denarius) as a single
        anchor node. The Quaestor citizen tends it."""
        ttable = self.root / "polaris_swarm" / "civitas" / "treasury.py"
        if not ttable.is_file():
            return
        self.add_node(
            "treasury:civitas", "Treasury (Denarius)",
            "treasury", G_OBSERVATION,
            description="F5 reward function. Drift-resolution rewards "
                        "+ persistent-silence penalties.",
        )
        if "citizen:quaestor_treasurer" in self.nodes:
            self.add_link(
                "citizen:quaestor_treasurer", "treasury:civitas",
                "tends",
            )

    def parse_twelfth_legion_reserve(self) -> None:
        """v9.11 — surface the reserved twelfth legion slot as an
        explicit "held silence" node (rather than absence). The node
        is marked as reserved so the visualization can render it
        differently (ghosted, dashed, etc.)."""
        f = self.root / "meta" / "twelfth-legion.md"
        if f.is_file():
            self.add_node(
                "legion:reserved_twelfth",
                "twelfth legion (RESERVED)",
                "reserved_slot", G_CONSTITUTION,
                manifested=False,
                reserved_at="v9.11",
            )

    def parse_vocation(self) -> None:
        """v9.11 — surface the named vocation (anti-coercion) as a
        constitutional construct above C1-C10."""
        mission = self._read("MISSION.md")
        if not mission:
            return
        if "## Vocation" in mission:
            self.add_node(
                "principle:vocation",
                "Vocation: anti-coercion",
                "principle", G_CONSTITUTION,
                description=(
                    "No person shall be compellable into renouncing, "
                    "transferring, or surrendering their identity "
                    "against their will. Above C1-C10."
                ),
            )

    def parse_cadences(self) -> None:
        """v9.11 — surface the seven planetary cadences from
        meta/cadences.md."""
        f = self.root / "meta" / "cadences.md"
        if not f.is_file():
            return
        self.add_node(
            "meta:cadences", "Cron cadence vocabulary",
            "cadences_doc", G_COGNITIVE,
        )
        # Seven planetary cadences
        for name in ("Saturn-pass", "Jupiter-pass", "Mars-cycle",
                     "Sun-pass", "Venus-cycle", "Mercury-cycle",
                     "Moon-cycle"):
            slug = name.lower().replace("-", "_")
            self.add_node(
                f"cadence:{slug}", name,
                "cadence", G_COGNITIVE,
            )
            self.add_link(f"cadence:{slug}", "meta:cadences", "defined_in")

    def parse_sanctums(self) -> None:
        sanctum_dir = self.root / "sanctum"
        if not sanctum_dir.is_dir():
            return
        for f in sorted(sanctum_dir.glob("*.md")):
            if f.name == "README.md":
                continue
            slug = f.stem
            self._sanctum_slugs.add(slug)
            try:
                text = f.read_text(errors="replace")
            except OSError:
                text = ""
            # Title from first H1
            m = re.search(r"^#\s+(.+?)$", text, re.MULTILINE)
            title = m.group(1).strip() if m else slug
            # Status from Status: field
            status_m = re.search(
                r"\*\*Status:\*\*\s*(\w+)", text, re.IGNORECASE,
            )
            status = status_m.group(1).upper() if status_m else "UNKNOWN"
            # Risk class
            risk_m = re.search(
                r"\*\*Risk class:\*\*\s*(\w+)", text, re.IGNORECASE,
            )
            risk = risk_m.group(1).upper() if risk_m else "UNKNOWN"
            self.add_node(
                f"sanctum:{slug}", title.replace("Sanctum: ", ""),
                "sanctum", G_DECISION,
                slug=slug, status=status, risk=risk,
            )

    def parse_ships(self) -> None:
        ships_dir = self.root / "DEVNOTES" / "ships"
        if not ships_dir.is_dir():
            return
        for f in sorted(ships_dir.glob("*.md")):
            slug = f.stem
            try:
                text = f.read_text(errors="replace")
            except OSError:
                text = ""
            m = re.search(r"^#\s+(.+?)$", text, re.MULTILINE)
            title = m.group(1).strip() if m else slug
            has_walk = "## Adversary walk" in text
            self.add_node(
                f"ship:{slug}", slug, "ship", G_KNOWLEDGE,
                title=title, has_adversary_walk=has_walk,
            )
            # Heuristic: if a sanctum's slug contains the ship slug or
            # references this ship doc, link sanctum→ship.
            for sslug in self._sanctum_slugs:
                if slug.replace("-", "") in sslug.replace("-", ""):
                    self.add_link(
                        f"sanctum:{sslug}", f"ship:{slug}",
                        "authorized",
                    )

    def parse_constraints(self) -> None:
        body = self._read("MISSION.md")
        if body is None:
            return
        # The C1-C10 table has format:
        # | C1 | description | where enforced |
        for m in re.finditer(
            r"^\|\s*(C\d{1,2})\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|$",
            body, re.MULTILINE,
        ):
            cid = m.group(1)
            desc = m.group(2).strip()
            enforced = m.group(3).strip()
            self.add_node(
                f"constraint:{cid}", cid,
                "constraint", G_CONSTITUTION,
                description=desc[:200],
                enforced=enforced[:200],
            )
            # Try to link to tables referenced in `enforced` column.
            for table_match in re.finditer(
                r"`?(\w+)\.sql|polaris_sql/(\w+)", enforced,
            ):
                pass  # too noisy in v1; leave for v2
            # Better signal: scan the description + enforced for
            # known table names (case-insensitive).
            for tname in list(self._table_names):
                if tname in (desc + " " + enforced).lower():
                    self.add_link(
                        f"constraint:{cid}", f"table:{tname}",
                        "constrains",
                    )

        # CM at the meta-constraint level.
        self.add_node(
            "constraint:CM", "CM",
            "constraint", G_CONSTITUTION,
            description="The cognitive layer self-monitors via "
                        "executable checks.",
        )

        # Four constitutional principles (v8.30 elevation).
        for pname, pid in (
            ("Sanctum protocol",     "principle:Sanctum"),
            ("Audit-of-record",      "principle:AoR"),
            ("Risk classes",         "principle:RiskClasses"),
            ("CM (meta-constraint)", "principle:CM"),
        ):
            self.add_node(
                pid, pname, "principle", G_CONSTITUTION,
            )
        # CM principle ↔ CM constraint
        self.add_link(
            "principle:CM", "constraint:CM", "is_constraint",
        )
        # Sanctum principle realized by every Sanctum file.
        for sslug in self._sanctum_slugs:
            self.add_link(
                f"sanctum:{sslug}", "principle:Sanctum",
                "realizes",
            )

    def parse_devnotes(self) -> None:
        devnotes_dir = self.root / "DEVNOTES"
        if not devnotes_dir.is_dir():
            return
        for f in sorted(devnotes_dir.glob("*.md")):
            if f.stem == "README":
                continue
            slug = f.stem
            self.add_node(
                f"devnote:{slug}", slug, "devnote", G_KNOWLEDGE,
            )

    # ------------------------------------------------------------------
    # v8.53 parser v2 extractors — close the connectivity gaps the
    # v8.52 brain-map analysis surfaced. Each method extracts one
    # missing edge type identified in the analysis.
    # ------------------------------------------------------------------

    def parse_script_calls(self) -> None:
        """script → script edges. ai-* scripts invoke each other
        constantly (ai-done calls ai-architect + ai-brain-map +
        ai-status + ai-meta + ai-link-check etc.). v8.52 saw none of
        this. Pattern: search each script's body for references to
        sibling ai-* scripts via `$HERE/ai-X`, `./scripts/ai-X`,
        `scripts/ai-X`, or bare `ai-X.sh`."""
        scripts_dir = self.root / "scripts"
        if not scripts_dir.is_dir():
            return
        # Collect all known script slugs first
        known_slugs = {
            f.stem for f in scripts_dir.glob("ai-*.sh")
        }
        # Pattern matches: ai-NAME or ai-NAME.sh in plausible contexts
        # (after /, "$HERE/", or word boundary). The captured group is
        # the slug (without the .sh suffix).
        ref_pattern = re.compile(
            r"(?:[\"'/\s])(ai-[a-zA-Z0-9_-]+)(?:\.sh)?\b"
        )
        seen_edges: set[tuple[str, str]] = set()
        for f in sorted(scripts_dir.glob("ai-*.sh")):
            caller_slug = f.stem  # e.g. "ai-done"
            try:
                body = f.read_text(errors="replace")
            except OSError:
                continue
            for m in ref_pattern.finditer(body):
                callee_slug = m.group(1)
                if callee_slug == caller_slug:
                    continue  # self-reference; skip
                if callee_slug not in known_slugs:
                    continue  # referenced script doesn't exist
                key = (caller_slug, callee_slug)
                if key in seen_edges:
                    continue
                seen_edges.add(key)
                self.add_link(
                    f"script:{caller_slug}",
                    f"script:{callee_slug}",
                    "invokes",
                )

    def parse_markdown_cross_refs(self) -> None:
        """devnote ↔ devnote, ship ↔ devnote, ship ↔ ship cross-refs.
        Polaris uses TWO link conventions:
          1. Standard Markdown: `[text](path)`
          2. Backtick-quoted paths: `` `DEVNOTES/foo.md` ``  ← dominant
        The first pass catches both. v8.52 only checked (1) and saw
        all 9 DEVNOTES as orphans because Polaris's convention is (2).
        """
        sources: list[tuple[pathlib.Path, str]] = []

        devnotes_dir = self.root / "DEVNOTES"
        if devnotes_dir.is_dir():
            for f in devnotes_dir.glob("*.md"):
                if f.stem == "README":
                    continue
                sources.append((f, f"devnote:{f.stem}"))
        ships_dir = devnotes_dir / "ships"
        if ships_dir.is_dir():
            for f in ships_dir.glob("*.md"):
                sources.append((f, f"ship:{f.stem}"))
        sanctum_dir = self.root / "sanctum"
        if sanctum_dir.is_dir():
            for f in sanctum_dir.glob("*.md"):
                if f.name == "README.md":
                    continue
                sources.append((f, f"sanctum:{f.stem}"))

        # Pattern 1: `[text](path)` — standard Markdown link.
        md_link = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
        # Pattern 2: backtick-quoted path. Only count things that
        # look like in-repo paths (DEVNOTES/, sanctum/, polaris_*,
        # meta/, scripts/, journal/, proposals/) ending in a known
        # extension OR a directory marker. Excludes prose backticks
        # and code snippets.
        backtick_path = re.compile(
            r"`(DEVNOTES/[\w/.-]+\.md|"
            r"sanctum/[\w./-]+\.md|"
            r"meta/[\w./-]+\.(?:md|json)|"
            r"scripts/[\w./-]+\.(?:sh|py)|"
            r"polaris_sql/[\w./-]+\.sql|"
            r"polaris_web/[\w./-]+\.(?:py|html|js|css)|"
            r"polaris_hydra/[\w./-]+\.py|"
            r"MISSION\.md|ROADMAP\.md|CHANGELOG\.md|CLAUDE\.md|"
            r"README\.md|SEED_DATA\.md|BACKLOG\.md)`"
        )

        for fpath, src_id in sources:
            if src_id not in self.nodes:
                continue
            try:
                body = fpath.read_text(errors="replace")
            except OSError:
                continue
            seen: set[str] = set()

            # Markdown-link path
            for m in md_link.finditer(body):
                target = m.group(1).split("#")[0].strip()
                if not target or target.startswith(("http://", "https://")):
                    continue
                tgt_id = self._resolve_md_link(fpath, target)
                if tgt_id is None or tgt_id == src_id or tgt_id in seen:
                    continue
                seen.add(tgt_id)
                self.add_link(src_id, tgt_id, "links_to")

            # Backtick-quoted path. Resolve as repo-root-relative.
            for m in backtick_path.finditer(body):
                target = m.group(1).split("#")[0].strip()
                tgt_id = self._resolve_backtick_path(target)
                if tgt_id is None or tgt_id == src_id or tgt_id in seen:
                    continue
                seen.add(tgt_id)
                self.add_link(src_id, tgt_id, "links_to")

    def _resolve_backtick_path(self, rel_str: str) -> str | None:
        """Map a backtick-quoted repo-relative path to a node id."""
        rel_str = rel_str.rstrip("/")
        if rel_str.startswith("DEVNOTES/ships/") and rel_str.endswith(".md"):
            slug = pathlib.Path(rel_str).stem
            nid = f"ship:{slug}"
            return nid if nid in self.nodes else None
        if rel_str.startswith("DEVNOTES/") and rel_str.endswith(".md"):
            slug = pathlib.Path(rel_str).stem
            if slug == "README":
                return None
            nid = f"devnote:{slug}"
            return nid if nid in self.nodes else None
        if rel_str.startswith("sanctum/") and rel_str.endswith(".md"):
            slug = pathlib.Path(rel_str).stem
            if slug == "README":
                return None
            nid = f"sanctum:{slug}"
            return nid if nid in self.nodes else None
        if rel_str.startswith("scripts/") and rel_str.startswith("scripts/ai-"):
            slug = pathlib.Path(rel_str).stem
            nid = f"script:{slug}"
            return nid if nid in self.nodes else None
        # MISSION.md, CHANGELOG.md, ROADMAP.md, CLAUDE.md, README.md
        # → no node today; could add later. Skip.
        return None

    def _resolve_md_link(self, source_file: pathlib.Path,
                         target: str) -> str | None:
        """Map a Markdown link target (relative path) to a node id.
        Returns None if the target doesn't correspond to a known
        knowledge/decision-layer node."""
        # Strip off URL fragments + query strings already done in caller
        target = target.strip().rstrip("/")
        # Resolve relative to the source file's directory.
        try:
            resolved = (source_file.parent / target).resolve()
        except (OSError, ValueError):
            return None
        # Make path relative to repo root for matching.
        try:
            rel = resolved.relative_to(self.root)
        except ValueError:
            return None
        rel_str = str(rel)
        # Match patterns we care about.
        if rel_str.startswith("DEVNOTES/ships/") and rel_str.endswith(".md"):
            slug = pathlib.Path(rel_str).stem
            nid = f"ship:{slug}"
            return nid if nid in self.nodes else None
        if rel_str.startswith("DEVNOTES/") and rel_str.endswith(".md"):
            slug = pathlib.Path(rel_str).stem
            if slug == "README":
                return None
            nid = f"devnote:{slug}"
            return nid if nid in self.nodes else None
        if rel_str.startswith("sanctum/") and rel_str.endswith(".md"):
            slug = pathlib.Path(rel_str).stem
            if slug == "README":
                return None
            nid = f"sanctum:{slug}"
            return nid if nid in self.nodes else None
        # Could also map polaris_sql/*.sql → table cluster, but skip
        # for v2; v8.52 already captures schema connectivity.
        return None

    def parse_sanctum_outcome_ships(self) -> None:
        """sanctum → ship via §VII Outcome body. v8.52 used a slug-
        substring heuristic that matched 6 of 9 ships. Parse each
        Sanctum's §VII Outcome for explicit ship references like
        `DEVNOTES/ships/X.md` or `ships/X` or even just `vX.Y` ship
        version mentions cross-referenced to the ship-doc set."""
        sanctum_dir = self.root / "sanctum"
        if not sanctum_dir.is_dir():
            return
        # Build {ship_slug → ship_id} for lookup
        ship_ids = {
            nd["id"].split(":", 1)[1]: nd["id"]
            for nd in self.nodes.values()
            if nd["type"] == "ship"
        }
        # Also: many sanctums authorize the multi-sig migration
        # without the slug match — look for explicit ship-slug
        # mentions anywhere in the file body, not just §VII.
        ship_mention_pattern = re.compile(
            r"\bships/([\w-]+)(?:\.md)?\b"
        )
        for f in sorted(sanctum_dir.glob("*.md")):
            if f.name == "README.md":
                continue
            slug = f.stem
            try:
                body = f.read_text(errors="replace")
            except OSError:
                continue
            seen: set[str] = set()
            for m in ship_mention_pattern.finditer(body):
                ship_slug = m.group(1)
                if ship_slug in ship_ids and ship_slug not in seen:
                    seen.add(ship_slug)
                    self.add_link(
                        f"sanctum:{slug}", ship_ids[ship_slug],
                        "authorized",
                    )

    def parse_route_calls_broad(self) -> None:
        """Broaden route → procedure detection. v8.52 caught CALL +
        SELECT * FROM uc_xxx(. Real app.py uses more patterns:
        cur.execute("SELECT uc_xxx(...)"), cur.execute(\"\"\"
        SELECT uc_xxx ... \"\"\"), or even just calling uc_xxx via
        a helper. Generic pattern: any uc\\w+ mention inside a
        route handler body."""
        body = self._read("polaris_web", "app.py")
        if body is None:
            return
        # Find each @app.route → def boundary
        route_pattern = re.compile(
            r"@app\.route\(\s*['\"]([^'\"]+)['\"][^)]*\)"
            r"((?:\s*@[\w.]+(?:\([^)]*\))?)*)"
            r"\s*def\s+(\w+)",
            re.MULTILINE,
        )
        matches = list(route_pattern.finditer(body))
        for i, m in enumerate(matches):
            route = m.group(1)
            start = m.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(body)
            handler_body = body[start:end]
            # Any uc\w+ identifier in the handler body that matches
            # an existing procedure.
            seen: set[str] = set()
            for proc_match in re.finditer(
                r"\b(uc\d+\w*)\b", handler_body, re.IGNORECASE
            ):
                proc = proc_match.group(1).lower()
                if proc in self._proc_names and proc not in seen:
                    seen.add(proc)
                    self.add_link(
                        f"route:{route}", f"proc:{proc}", "calls",
                    )

    def parse_constraint_enforcement(self) -> None:
        """C-constraint → enforcement target. The MISSION.md C1-C10
        table's "Where enforced" column references specific files
        (06_triggers.sql, security.py, app.py) and symbols
        (`reject_update_delete()`, `authenticate()`). Parse those
        and emit edges to the corresponding nodes when we have them.
        v8.52 only matched 3 of 11 constraints to tables."""
        body = self._read("MISSION.md")
        if body is None:
            return
        # The C1-C10 table. Each row's third column is "Where enforced".
        for m in re.finditer(
            r"^\|\s*(C\d{1,2}|CM)\s*\|\s*[^|]+?\s*\|\s*([^|]+?)\s*\|$",
            body, re.MULTILINE,
        ):
            cid = m.group(1)
            enforced = m.group(2)
            cnode = f"constraint:{cid}"
            if cnode not in self.nodes:
                continue
            # 1. Reference to a specific trigger symbol:
            #    e.g., `06_triggers.sql::reject_update_delete()`
            for tm in re.finditer(
                r"::(\w+)\(\)", enforced
            ):
                trig_name = tm.group(1)
                tnode = f"trigger:{trig_name}"
                if tnode in self.nodes:
                    self.add_link(cnode, tnode, "enforced_by")
            # 2. Reference to a schema element symbol:
            #    e.g., `01_schema.sql::uq_one_active_per_person`,
            #    `01_schema.sql::CryptographicAlgorithm`,
            #    `01_schema.sql::disclosure_consistency`
            for sm in re.finditer(
                r"01_schema\.sql::(\w+)", enforced
            ):
                sym = sm.group(1)
                # Try matching the symbol as a table, then an index.
                if f"table:{sym.lower()}" in self.nodes:
                    self.add_link(
                        cnode, f"table:{sym.lower()}",
                        "enforced_by",
                    )
                elif f"index:{sym}" in self.nodes:
                    self.add_link(
                        cnode, f"index:{sym}", "enforced_by",
                    )
            # 3. Reference to specific module files. Create an
            #    enforcement_module synthetic node per file mentioned.
            for fm in re.finditer(
                r"`?(security\.py|app\.py|test_app\.py)`?",
                enforced
            ):
                mod = fm.group(1)
                mod_id = f"module:{mod}"
                self.add_node(
                    mod_id, mod, "module", G_BEHAVIOR,
                )
                self.add_link(cnode, mod_id, "enforced_by")

    def parse_watcher_constraints(self) -> None:
        """watcher → C-constraint. Each watcher's domain ties to
        specific C-constraints (SchemaWatcher to C1, SecurityWatcher
        to C5/C6, AdversaryWatcher walks all of C1-C10, etc.).
        Signal: scan each watcher's source file for `Cn` and `CM`
        token mentions (in comments + docstrings) and emit edges to
        the corresponding constraint nodes."""
        watchers_dir = self.root / "polaris_hydra" / "watchers"
        if not watchers_dir.is_dir():
            return
        # Match Cn (n=1..10) and CM as word-boundary tokens, BUT only
        # those that appear in comment / docstring contexts. Easiest
        # heuristic: only match when preceded by `# `, `## `, `"""`,
        # or `(` (typical commentary contexts) — avoid matching code
        # like `C2_PATTERN` accidentally. We'll use word-boundary
        # match and trust the source to be largely commented prose.
        constraint_pattern = re.compile(
            r"\b(C\d{1,2}|CM)\b"
        )
        for f in sorted(watchers_dir.glob("*_watcher.py")):
            wname = f.stem.replace("_watcher", "")
            wid = f"watcher:{wname}"
            if wid not in self.nodes:
                continue
            try:
                body = f.read_text(errors="replace")
            except OSError:
                continue
            seen: set[str] = set()
            for m in constraint_pattern.finditer(body):
                cid = m.group(1)
                # Validate: C-constraints are 1..10 and CM.
                if cid == "CM":
                    pass
                else:
                    n = int(cid[1:])
                    if n < 1 or n > 10:
                        continue
                if cid in seen:
                    continue
                seen.add(cid)
                target = f"constraint:{cid}"
                if target in self.nodes:
                    self.add_link(wid, target, "monitors")

    def parse_advisory_locks(self) -> None:
        """The 6-entry advisory-lock catalog (per DEVNOTES/concurrency.md).
        Procedures using pg_advisory_xact_lock get an edge to a
        synthetic 'locking' node."""
        body = self._read("polaris_sql", "05_procedures.sql")
        if body is None:
            return
        self.add_node(
            "concept:advisory_lock", "advisory-lock catalog",
            "concept", G_BEHAVIOR,
        )
        # Find procedure name → contains pg_advisory_xact_lock
        for pm in re.finditer(
            r"CREATE\s+OR\s+REPLACE\s+(?:PROCEDURE|FUNCTION)\s+(\w+)\s*\("
            r"(.*?)\$\$",
            body, re.DOTALL | re.IGNORECASE,
        ):
            proc = pm.group(1)
            block = pm.group(2)
            # Look ahead in the body for the locking call
            start = pm.end()
            # bounded slice for the function body
            end_m = re.search(
                r"\$\$\s*LANGUAGE", body[start:], re.IGNORECASE,
            )
            if end_m:
                fbody = body[start: start + end_m.start()]
                if re.search(
                    r"pg_advisory_xact_lock", fbody, re.IGNORECASE,
                ):
                    self.add_link(
                        f"proc:{proc.lower()}",
                        "concept:advisory_lock", "uses",
                    )

    # ------------------------------------------------------------------
    # Build
    # ------------------------------------------------------------------

    def build(self) -> dict:
        # Phase 1: node discovery + intra-domain edges (v8.52).
        self.parse_schema_tables()
        self.parse_indexes()
        self.parse_triggers()
        self.parse_procedures()
        self.parse_routes()
        self.parse_watchers()
        self.parse_ai_scripts()
        self.parse_sanctums()
        self.parse_ships()
        self.parse_constraints()
        # Phase 1.5 (v9.14 catch-up): v9.11-v9.13 entities the v8.52
        # collectors didn't know about.
        self.parse_foresight_package()      # v9.12
        self.parse_foresight_sql_helpers()  # v9.12
        self.parse_action_promotion()       # v9.11
        self.parse_anti_architect()         # v9.11
        self.parse_priest_soldier()         # v9.11
        self.parse_twelfth_legion_reserve() # v9.11
        self.parse_vocation()               # v9.11
        self.parse_cadences()               # v9.11
        # v9.15 — full Mycelium surface in brain-map (legions + ants +
        # workers + citizens + treasury). Previously these lived only
        # in swarm-map; v9.15 makes the brain-map the unified view.
        self.parse_legions()                # v9.15
        self.parse_commander_ants()         # v9.15
        self.parse_worker_soldiers()        # v9.15
        self.parse_citizens()               # v9.15
        self.parse_treasury()               # v9.15
        # Phase 2: parser v2 cross-domain edges (v8.53). Must run
        # after node discovery so the resolve helpers find targets.
        self.parse_script_calls()
        self.parse_markdown_cross_refs()
        self.parse_sanctum_outcome_ships()
        self.parse_route_calls_broad()
        self.parse_constraint_enforcement()
        self.parse_watcher_constraints()
        self.parse_devnotes()
        self.parse_advisory_locks()
        return {
            "nodes": list(self.nodes.values()),
            "links": self.links,
            "generated_at": datetime.now(timezone.utc)
                .isoformat(timespec="seconds"),
            "polaris_version": self._read_polaris_version(),
            "node_count": len(self.nodes),
            "link_count": len(self.links),
        }

    def _read_polaris_version(self) -> str:
        body = self._read("CHANGELOG.md")
        if body is None:
            return "unknown"
        m = re.search(r"^##\s+(v[\d\.]+)", body, re.MULTILINE)
        return m.group(1) if m else "unknown"


HTML_TEMPLATE = r"""<!DOCTYPE html>
<!-- AUTO-GENERATED by scripts/ai_brain_map.py — DO NOT HAND-EDIT.
     Per v9.30 item 11: brain-map is generated from actual repo state,
     not hand-maintained (a hand-maintained 222-node map is a lie within
     a month). Regenerate with: python3 scripts/ai_brain_map.py -->
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Polaris Brain Map — __VERSION__</title>
<style>
  html, body { margin: 0; padding: 0; height: 100%; overflow: hidden;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI',
    Roboto, sans-serif; background: #0a0e14; color: #e1e6ec; }
  #title { position: absolute; top: 12px; left: 16px; z-index: 10;
    font-size: 14px; }
  #title strong { color: #f4d35e; }
  #stats { position: absolute; top: 12px; right: 16px; z-index: 10;
    font-size: 12px; color: #8892a6; text-align: right; }
  #legend { position: absolute; bottom: 12px; left: 16px; z-index: 10;
    background: rgba(15, 20, 30, 0.85); padding: 10px 14px;
    border-radius: 6px; font-size: 12px; max-width: 220px; }
  #legend h3 { margin: 0 0 8px; font-size: 12px;
    text-transform: uppercase; letter-spacing: 0.1em;
    color: #8892a6; font-weight: 500; }
  #legend .row { display: flex; align-items: center;
    margin: 4px 0; }
  #legend .swatch { width: 12px; height: 12px; border-radius: 50%;
    margin-right: 8px; flex-shrink: 0; }
  #tooltip { position: absolute; padding: 8px 12px;
    background: rgba(15, 20, 30, 0.95); border: 1px solid #2a3548;
    border-radius: 4px; font-size: 12px; pointer-events: none;
    opacity: 0; transition: opacity 0.12s; max-width: 320px;
    z-index: 20; }
  #tooltip .t-label { font-weight: 600; color: #f4d35e; }
  #tooltip .t-type  { color: #8892a6; font-size: 11px;
    text-transform: uppercase; letter-spacing: 0.05em; }
  #tooltip .t-meta  { margin-top: 6px; color: #c0c8d4;
    line-height: 1.45; }
  #search { position: absolute; top: 12px; left: 50%;
    transform: translateX(-50%); z-index: 10; }
  #search input { background: rgba(15, 20, 30, 0.85);
    border: 1px solid #2a3548; color: #e1e6ec;
    padding: 6px 10px; border-radius: 4px; font-size: 12px;
    width: 240px; outline: none; }
  #search input:focus { border-color: #f4d35e; }
  .node { stroke: #1a1e26; stroke-width: 1.5; cursor: pointer; }
  .node.dim { opacity: 0.15; }
  .node.hl  { stroke: #f4d35e; stroke-width: 3; }
  .link { stroke: #2a3548; stroke-opacity: 0.4; }
  .link.dim { stroke-opacity: 0.05; }
  .link.hl  { stroke: #f4d35e; stroke-opacity: 0.7; }
  .label { font-size: 9px; fill: #8892a6;
    pointer-events: none; user-select: none; }
  .label.hl { fill: #f4d35e; font-size: 11px; font-weight: 600; }
</style>
</head>
<body>
<div id="title">
  <strong>POLARIS</strong> · brain map · <span id="ver">__VERSION__</span>
</div>
<div id="stats">
  <span id="node-count">__NODE_COUNT__</span> nodes ·
  <span id="link-count">__LINK_COUNT__</span> edges<br>
  <span id="gen-time">generated __GENERATED_AT__</span>
</div>
<div id="search"><input type="text" id="q"
  placeholder="search · click to focus · esc to clear"></div>
<div id="legend">
  <h3>Layers</h3>
  <div class="row"><span class="swatch" style="background:#4a90e2"></span>
    schema (tables, indexes, triggers)</div>
  <div class="row"><span class="swatch" style="background:#5cb85c"></span>
    behavior (routes, procedures)</div>
  <div class="row"><span class="swatch" style="background:#f4d35e"></span>
    cognitive (ai-* scripts)</div>
  <div class="row"><span class="swatch" style="background:#d9534f"></span>
    decisions (sanctums, ships)</div>
  <div class="row"><span class="swatch" style="background:#e6e6e6"></span>
    constitution (C1-C10, CM, principles)</div>
  <div class="row"><span class="swatch" style="background:#b67aeb"></span>
    observation (HYDRA, watchers)</div>
  <div class="row"><span class="swatch" style="background:#f0ad4e"></span>
    knowledge (DEVNOTES, ships)</div>
</div>
<div id="tooltip"></div>
<svg id="graph"></svg>
<script src="assets/d3.v7.min.js"></script>
<script id="graph-data" type="application/json">__GRAPH_JSON__</script>
<script>
(function () {
  var DATA = JSON.parse(document.getElementById('graph-data').textContent);
  var COLOR = {
    schema:       '#4a90e2',
    behavior:     '#5cb85c',
    cognitive:    '#f4d35e',
    decision:     '#d9534f',
    constitution: '#e6e6e6',
    observation:  '#b67aeb',
    knowledge:    '#f0ad4e'
  };
  var SIZE = {
    hydra_host: 14, principle: 12, constraint: 11,
    schema_table: 9, watcher: 9, procedure: 8, function: 8,
    sanctum: 8, ship: 7, route: 6, ai_script: 6,
    index: 4, trigger: 5, devnote: 6, concept: 11
  };

  var svg = d3.select('#graph');
  var W = window.innerWidth, H = window.innerHeight;
  svg.attr('width', W).attr('height', H)
     .attr('viewBox', [-W/2, -H/2, W, H]);
  var g = svg.append('g');

  svg.call(d3.zoom()
    .scaleExtent([0.1, 8])
    .on('zoom', function (event) { g.attr('transform', event.transform); })
  );

  var sim = d3.forceSimulation(DATA.nodes)
    .force('link', d3.forceLink(DATA.links).id(function (d) { return d.id; })
                     .distance(function (l) {
                       // Group-internal links are tighter than cross-group
                       var s = DATA.nodes.find(function (n) { return n.id === l.source.id || n.id === l.source; });
                       var t = DATA.nodes.find(function (n) { return n.id === l.target.id || n.id === l.target; });
                       if (s && t && s.group === t.group) return 35;
                       return 70;
                     }).strength(0.4))
    .force('charge', d3.forceManyBody().strength(-90))
    .force('collide', d3.forceCollide().radius(function (d) {
       return (SIZE[d.type] || 6) + 4;
    }))
    .force('center', d3.forceCenter(0, 0))
    .force('x', d3.forceX(0).strength(0.03))
    .force('y', d3.forceY(0).strength(0.03));

  var link = g.append('g').attr('class', 'links')
    .selectAll('line').data(DATA.links).join('line')
    .attr('class', 'link')
    .attr('stroke-width', function (d) { return Math.sqrt(d.value || 1); });

  var node = g.append('g').attr('class', 'nodes')
    .selectAll('circle').data(DATA.nodes).join('circle')
    .attr('class', 'node')
    .attr('r', function (d) { return SIZE[d.type] || 6; })
    .attr('fill', function (d) { return COLOR[d.group] || '#888'; })
    .call(d3.drag()
      .on('start', function (event, d) {
        if (!event.active) sim.alphaTarget(0.25).restart();
        d.fx = d.x; d.fy = d.y;
      })
      .on('drag', function (event, d) { d.fx = event.x; d.fy = event.y; })
      .on('end', function (event, d) {
        if (!event.active) sim.alphaTarget(0);
        d.fx = null; d.fy = null;
      }));

  var label = g.append('g').attr('class', 'labels')
    .selectAll('text').data(DATA.nodes).join('text')
    .attr('class', 'label')
    .attr('dx', function (d) { return (SIZE[d.type] || 6) + 3; })
    .attr('dy', 3)
    .text(function (d) { return d.label; });

  sim.on('tick', function () {
    link
      .attr('x1', function (d) { return d.source.x; })
      .attr('y1', function (d) { return d.source.y; })
      .attr('x2', function (d) { return d.target.x; })
      .attr('y2', function (d) { return d.target.y; });
    node
      .attr('cx', function (d) { return d.x; })
      .attr('cy', function (d) { return d.y; });
    label
      .attr('x', function (d) { return d.x; })
      .attr('y', function (d) { return d.y; });
  });

  // ---- Interaction: hover + click highlight ----
  var tooltip = d3.select('#tooltip');
  var adjacency = {};
  DATA.links.forEach(function (l) {
    var s = (l.source.id || l.source);
    var t = (l.target.id || l.target);
    (adjacency[s] = adjacency[s] || new Set()).add(t);
    (adjacency[t] = adjacency[t] || new Set()).add(s);
  });

  function showTooltip(event, d) {
    var meta = '';
    if (d.type) meta += '<div class="t-type">' + d.type.replace(/_/g, ' ') + '</div>';
    var lines = [];
    if (d.description)     lines.push(d.description);
    if (d.enforced)        lines.push('Enforced: ' + d.enforced);
    if (d.handler)         lines.push('Handler: ' + d.handler);
    if (d.requires_role)   lines.push('Role-gated');
    if (d.status)          lines.push('Sanctum status: ' + d.status);
    if (d.risk)            lines.push('Risk: ' + d.risk);
    if (d.has_adversary_walk) lines.push('Has adversary walk');
    if (d.kind)            lines.push('Kind: ' + d.kind);
    tooltip.html(
      '<div class="t-label">' + d.label + '</div>' + meta +
      (lines.length ? '<div class="t-meta">' + lines.join('<br>') + '</div>' : '')
    );
    tooltip.style('opacity', 1)
           .style('left', (event.pageX + 14) + 'px')
           .style('top',  (event.pageY + 14) + 'px');
  }
  function hideTooltip() { tooltip.style('opacity', 0); }

  function highlight(nodeId) {
    var neighbors = adjacency[nodeId] || new Set();
    neighbors.add(nodeId);
    node.classed('hl',  function (d) { return d.id === nodeId; });
    node.classed('dim', function (d) { return !neighbors.has(d.id); });
    label.classed('hl', function (d) { return d.id === nodeId; });
    link.classed('hl',  function (l) {
      var s = (l.source.id || l.source);
      var t = (l.target.id || l.target);
      return s === nodeId || t === nodeId;
    });
    link.classed('dim', function (l) {
      var s = (l.source.id || l.source);
      var t = (l.target.id || l.target);
      return s !== nodeId && t !== nodeId;
    });
  }
  function clearHighlight() {
    node.classed('hl', false).classed('dim', false);
    label.classed('hl', false);
    link.classed('hl', false).classed('dim', false);
  }

  node.on('mouseover', showTooltip)
      .on('mouseout', hideTooltip)
      .on('click', function (event, d) {
        event.stopPropagation();
        highlight(d.id);
      });
  svg.on('click', clearHighlight);
  d3.select(document).on('keydown', function (event) {
    if (event.key === 'Escape') {
      clearHighlight();
      document.getElementById('q').value = '';
    }
  });

  // Search
  d3.select('#q').on('input', function () {
    var q = this.value.toLowerCase().trim();
    if (!q) { clearHighlight(); return; }
    var matches = DATA.nodes.filter(function (n) {
      return n.label.toLowerCase().indexOf(q) >= 0 ||
             (n.id || '').toLowerCase().indexOf(q) >= 0;
    });
    var matchIds = new Set(matches.map(function (n) { return n.id; }));
    node.classed('dim', function (d) { return !matchIds.has(d.id); });
    node.classed('hl',  function (d) { return matchIds.has(d.id); });
    label.classed('hl', function (d) { return matchIds.has(d.id); });
    link.classed('dim', function (l) {
      var s = (l.source.id || l.source);
      var t = (l.target.id || l.target);
      return !matchIds.has(s) && !matchIds.has(t);
    });
  });

  // Resize
  window.addEventListener('resize', function () {
    var w = window.innerWidth, h = window.innerHeight;
    svg.attr('width', w).attr('height', h)
       .attr('viewBox', [-w/2, -h/2, w, h]);
  });
})();
</script>
</body>
</html>
"""


def render_html(graph: dict) -> str:
    html = HTML_TEMPLATE
    html = html.replace("__VERSION__", graph["polaris_version"])
    html = html.replace("__NODE_COUNT__", str(graph["node_count"]))
    html = html.replace("__LINK_COUNT__", str(graph["link_count"]))
    html = html.replace("__GENERATED_AT__", graph["generated_at"])
    # Embed the graph JSON inline. The script tag has
    # type="application/json" so it is non-executable per CSP-style
    # data-island rules (the same pattern atlas-globe.js uses).
    payload = {
        "nodes": graph["nodes"],
        "links": graph["links"],
    }
    blob = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    # Defend against `</script>` smuggling in any node label or
    # description (would prematurely terminate the data-island).
    blob = blob.replace("</", "<\\/")
    html = html.replace("__GRAPH_JSON__", blob)
    return html


def main(argv: list[str]) -> int:
    repo_root = pathlib.Path(__file__).resolve().parent.parent
    out_path = repo_root / "meta" / "brain-map" / "brain-map.html"

    builder = GraphBuilder(repo_root)
    graph = builder.build()

    html = render_html(graph)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding="utf-8")

    print(f"polaris brain-map written: {out_path}", file=sys.stderr)
    print(f"  {graph['node_count']} nodes · "
          f"{graph['link_count']} links · "
          f"version {graph['polaris_version']}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
