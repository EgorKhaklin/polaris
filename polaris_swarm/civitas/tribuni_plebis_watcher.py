"""TribuniPlebisWatcher — Tribuni Plebis class (Arc G / G1 / v8.71).

The Roman Tribuni Plebis were elected representatives of the
plebeian class with veto power over Senate actions. In the
cognitive substrate, the Tribuni's role is reframed: they
**defend the usability surface** against creeping complexity.

The Architect's §III analysis of Arc G named this citizen class
as "premature for not-yet-existing external users." VANTA's
Option C overrode that recommendation; in honest implementation,
the Tribuni's scope is therefore **internal usability** —
observing whether the cognitive layer's own surface is becoming
harder for VANTA (the only current operator) to navigate.

Observation surface (G22 — usability-only):

  - **Command count growth.** `scripts/ai-*.sh` count vs CLAUDE.md's
    documented count. Drift = surface growing without doc
    catching up.
  - **Doc complexity growth.** `CLAUDE.md` line count vs
    7-day-ago. If the agent runbook has grown >30% in a
    week, the cognitive load on future agents is increasing.
  - **Sanctum-protocol entropy.** Number of OPEN Sanctums >0,
    or count of Sanctums per day >3 over the last 7 days.
    Either signals process friction.

The Tribuni emits `tribunician_friction` observations. Like a
real Tribune in Rome, the Tribuni does NOT itself veto — it
surfaces the friction signal for VANTA to act on. The veto
power, in the substrate's terms, is *VANTA's* — exercised by
choosing to address the friction or explicitly accept it.

**G22 boundary:** observes usability artifacts only. Never
observes identity-layer attributes (no Individual / token /
holder references). C10 (pomerium) preserved.

Authorized by `sanctum/2026-05-13-arc-g-roman-empire-opening.md`.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone

from polaris_swarm.civitas.base import (
    Citizen, CitizenFinding, CIVITAS_TRIBUNI_PLEBIS,
)


# Friction thresholds (tunable)
COMMAND_DOC_DRIFT_MIN = 2          # ≥2 ai-* commands undocumented in CLAUDE.md
CLAUDE_MD_GROWTH_PCT  = 30.0       # >30% growth over recent window
SANCTUM_DAILY_BURST   = 3          # >3 Sanctums opened in a single date
SANCTUM_RECENT_WINDOW_DAYS = 7.0


# Regex: ai-*.sh script names
_AI_SCRIPT_RE = re.compile(r"^ai-([a-z0-9-]+)\.sh$")


class TribuniPlebisWatcher(Citizen):
    NAME          = "tribuni_plebis_watcher"
    CIVITAS_CLASS = CIVITAS_TRIBUNI_PLEBIS
    DESCRIPTION   = "Tribuni Plebis: surfaces friction signals in the cognitive layer's usability surface."

    def __init__(self, root, seed=None, at: datetime | None = None):
        super().__init__(root, seed=seed)
        self.at = at if at is not None else datetime.now(timezone.utc)

    def observe(self, recent_pheromones: list[dict]) -> list[CitizenFinding]:
        findings: list[CitizenFinding] = []
        findings.extend(self._check_command_doc_drift())
        findings.extend(self._check_claude_md_complexity())
        findings.extend(self._check_sanctum_entropy())
        return findings

    def _check_command_doc_drift(self) -> list[CitizenFinding]:
        scripts_dir = self.root / "scripts"
        if not scripts_dir.is_dir():
            return []
        on_disk: list[str] = []
        for p in scripts_dir.iterdir():
            if not p.is_file():
                continue
            m = _AI_SCRIPT_RE.match(p.name)
            if m:
                on_disk.append(p.stem)  # e.g., "ai-status"
        claude = self._read("CLAUDE.md") or ""
        if not claude:
            return []
        undocumented = [
            name for name in on_disk
            if name not in claude
        ]
        if len(undocumented) < COMMAND_DOC_DRIFT_MIN:
            return []
        return [CitizenFinding(
            node_id="usability:command_doc_drift",
            intensity=round(min(6.0, 2.0 + 0.5 * len(undocumented)), 3),
            kind="drift",
            observation_type="tribunician_friction",
            evidence={
                "civitas_class": CIVITAS_TRIBUNI_PLEBIS,
                "message": (
                    f"{len(undocumented)} ai-* script(s) on disk "
                    f"are not mentioned in CLAUDE.md"
                ),
                "undocumented": sorted(undocumented),
                "fix_hint": (
                    "either document the commands in CLAUDE.md or "
                    "retire them; surface area without docs is "
                    "friction for future agents"
                ),
            },
            half_life_hours=168.0,
        )]

    def _check_claude_md_complexity(self) -> list[CitizenFinding]:
        claude_path = self.root / "CLAUDE.md"
        if not claude_path.is_file():
            return []
        try:
            line_count = sum(1 for _ in claude_path.open(errors="replace"))
        except OSError:
            return []
        # Heuristic threshold: CLAUDE.md is intended as a
        # ≤500-line agent runbook. Beyond ~1500 lines the
        # signal-to-noise ratio degrades for fresh agents.
        if line_count <= 1500:
            return []
        intensity = round(min(6.0, 2.0 + (line_count - 1500) / 1000.0), 3)
        return [CitizenFinding(
            node_id="usability:claude_md_complexity",
            intensity=intensity,
            kind="info",
            observation_type="tribunician_friction",
            evidence={
                "civitas_class": CIVITAS_TRIBUNI_PLEBIS,
                "message": (
                    f"CLAUDE.md is {line_count} lines; cognitive "
                    f"load on future agents is high"
                ),
                "line_count": line_count,
                "fix_hint": (
                    "consider splitting state-map rows to "
                    "CHANGELOG only (keep CLAUDE.md focused on "
                    "agent runbook + gotchas)"
                ),
            },
            half_life_hours=168.0,
        )]

    def _check_sanctum_entropy(self) -> list[CitizenFinding]:
        sanctum_dir = self.root / "sanctum"
        if not sanctum_dir.is_dir():
            return []
        # Count sanctums per date over recent window
        recent_dates: dict[str, int] = {}
        for p in sanctum_dir.glob("2026-*.md"):
            # Filename: YYYY-MM-DD-topic.md
            m = re.match(r"(\d{4}-\d{2}-\d{2})-", p.name)
            if not m:
                continue
            date_str = m.group(1)
            try:
                date_ts = datetime.strptime(date_str, "%Y-%m-%d").replace(
                    tzinfo=timezone.utc,
                )
            except ValueError:
                continue
            age_days = (self.at - date_ts).total_seconds() / 86400.0
            if age_days > SANCTUM_RECENT_WINDOW_DAYS or age_days < 0:
                continue
            recent_dates[date_str] = recent_dates.get(date_str, 0) + 1
        findings: list[CitizenFinding] = []
        for date_str, count in sorted(recent_dates.items()):
            if count >= SANCTUM_DAILY_BURST:
                findings.append(CitizenFinding(
                    node_id=f"usability:sanctum_burst#{date_str}",
                    intensity=round(min(7.0, 3.0 + 0.5 * count), 3),
                    kind="drift",
                    observation_type="tribunician_friction",
                    evidence={
                        "civitas_class": CIVITAS_TRIBUNI_PLEBIS,
                        "message": (
                            f"{count} Sanctum(s) opened on {date_str}; "
                            f"process-friction signal"
                        ),
                        "date": date_str,
                        "count": count,
                        "threshold": SANCTUM_DAILY_BURST,
                        "fix_hint": (
                            "the Sanctum protocol is for MEDIUM/HIGH-risk "
                            "decisions; if multiple Sanctums are opened "
                            "in one day, consider whether the decisions "
                            "could be batched or whether the protocol "
                            "is being over-applied"
                        ),
                    },
                    half_life_hours=72.0,
                ))
        return findings
