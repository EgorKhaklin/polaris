"""ant_proposal_stagnation — surfaces stagnant proposals/*.md files.

**This ant was materialized via the F3 proposal-driven autogenesis
loop (Arc F / F2-F4 / v8.70).** The Augur observed that
`proposals/` had files but zero ant coverage and emitted a
`proposal_new_ant` pheromone naming the gap. VANTA ratified by
authorizing the Architect to materialize this ant.

Acceleration ant. Slice: every `proposals/*.md` file. For each:

  - check mtime; if older than `STAGNATION_DAYS` (default 30d),
    deposit a `drift` pheromone.
  - check whether the proposal's R-id (matched from the filename
    pattern `R\\d+-\\d+-...`) appears anywhere in `ROADMAP.md`.
    If NOT promoted yet AND the file is stagnant, intensity is
    higher (the proposal has been forgotten).
  - check whether the proposal's R-id appears in `CHANGELOG.md`
    as a shipped item; if so, the proposal is likely outdated
    (already realized) and should be either marked done or
    archived — info-class pheromone.

Local rule:
  - shipped + stagnant: `info` at intensity 3.0 — "already done,
    can be archived"
  - not shipped + stagnant + not in ROADMAP: `drift` at intensity
    `min(7.0, 2.0 + age_days/30)` — "genuine stagnation; review
    or drop"
  - not shipped + stagnant + in ROADMAP: `info` at intensity 2.0
    — "on the active roadmap, just untouched"
  - not stagnant: silent

G17 (acceleration, read-only): only reads proposals/, ROADMAP.md,
CHANGELOG.md; never writes. Materializes the v8.66 G13
proposal-pheromone-to-ant loop end-to-end.

Determinism: optional `at` parameter for replay safety.

Authorized by `sanctum/2026-05-13-arc-f-accelerated-pacing-override.md`.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone

from polaris_swarm.base import Ant, AntFinding, KIND_DRIFT, KIND_INFO


STAGNATION_DAYS = 30.0

# Proposal filename → R-id extraction:
#   "R11-6-issuer-discretion.md" → "R11-6"
#   "R-something.md"             → None (skipped)
_R_ID_RE = re.compile(r"^(R\d+-\d+)\b")

# In ROADMAP.md, the headers are `### ✅ R13-7. ...` or `### ⬜ R14-2. ...`
_ROADMAP_RID_RE = re.compile(r"R\d+-\d+")

# In CHANGELOG.md, a shipped R-id often appears in entry titles or bodies.
_CHANGELOG_RID_RE = re.compile(r"R\d+-\d+")


class AntProposalStagnation(Ant):
    NAME = "ant_proposal_stagnation"
    DESCRIPTION = "Pheromones proposals/*.md files untouched ≥30d (stagnant vs already-shipped vs scheduled)."

    def __init__(self, root, seed=None, at: datetime | None = None):
        super().__init__(root, seed=seed)
        self.at = at if at is not None else datetime.now(timezone.utc)

    def scan(self) -> list[AntFinding]:
        findings: list[AntFinding] = []
        proposals_dir = self.root / "proposals"
        if not proposals_dir.is_dir():
            return findings
        roadmap = self._read("ROADMAP.md") or ""
        changelog = self._read("CHANGELOG.md") or ""
        # Cache: which R-ids appear where?
        roadmap_rids = set(_ROADMAP_RID_RE.findall(roadmap))
        changelog_rids = set(_CHANGELOG_RID_RE.findall(changelog))
        for path in sorted(proposals_dir.glob("*.md")):
            if path.name.startswith("README"):
                continue
            try:
                mtime = datetime.fromtimestamp(
                    path.stat().st_mtime, tz=timezone.utc,
                )
            except OSError:
                continue
            age_days = (self.at - mtime).total_seconds() / 86400.0
            if age_days < STAGNATION_DAYS:
                continue
            # Extract R-id from filename
            m = _R_ID_RE.match(path.name)
            r_id = m.group(1) if m else None
            rel = str(path.relative_to(self.root))
            in_roadmap = r_id in roadmap_rids if r_id else False
            in_changelog = r_id in changelog_rids if r_id else False
            if in_changelog and r_id:
                # Already shipped — proposal is historical
                findings.append(AntFinding(
                    node_id=f"file:{rel}",
                    intensity=3.0,
                    kind=KIND_INFO,
                    evidence={
                        "message": (
                            f"{rel} (R-id {r_id}) was shipped; "
                            f"proposal can be archived or marked done"
                        ),
                        "file": rel,
                        "r_id": r_id,
                        "state": "shipped_but_proposal_lingers",
                        "age_days": round(age_days, 2),
                        "fix_hint": (
                            "move to proposals/archive/ or annotate "
                            "with the shipped version"
                        ),
                    },
                    half_life_hours=168.0,
                ))
            elif in_roadmap and r_id:
                # Scheduled but not yet shipped — visible, low signal
                findings.append(AntFinding(
                    node_id=f"file:{rel}",
                    intensity=2.0,
                    kind=KIND_INFO,
                    evidence={
                        "message": (
                            f"{rel} (R-id {r_id}) is on ROADMAP "
                            f"but untouched for {age_days:.0f}d"
                        ),
                        "file": rel,
                        "r_id": r_id,
                        "state": "scheduled_on_roadmap",
                        "age_days": round(age_days, 2),
                    },
                    half_life_hours=168.0,
                ))
            else:
                # Genuine stagnation — not on roadmap, not shipped
                intensity = round(min(7.0, 2.0 + age_days / 30.0), 3)
                findings.append(AntFinding(
                    node_id=f"file:{rel}",
                    intensity=intensity,
                    kind=KIND_DRIFT,
                    evidence={
                        "message": (
                            f"{rel} (R-id {r_id or '?'}) is "
                            f"{age_days:.0f}d stagnant; not on "
                            f"ROADMAP; not shipped"
                        ),
                        "file": rel,
                        "r_id": r_id,
                        "state": "stagnant",
                        "age_days": round(age_days, 2),
                        "in_roadmap": False,
                        "in_changelog": False,
                        "fix_hint": (
                            "decide: promote to ROADMAP, drop, "
                            "or schedule for a future arc"
                        ),
                    },
                    half_life_hours=168.0,
                ))
        return findings
