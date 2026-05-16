"""FS-XXXXXXXX auto-promotion — parallel of v9.11 action_promotion.

Foresight candidates from `Brief` §V are promoted to ROADMAP.md as
FS-XXXXXXXX items. Mirrors the v9.11 AP-XXXXXXXX shape:
  - 8-hex-char stable IDs from sha256 of the title
  - Idempotent (re-runs add nothing)
  - Decline-marker convention (~~FS-XXXXXXXX~~ prevents re-promotion)
  - Conservative: defaults to LOW + MEDIUM only

Differences from action_promotion (intentional):
  - Different prefix (FS- vs AP-) so operator can grep separately
  - Different ROADMAP section: §"Foresight candidates (v9.12+)"
  - Empirical-graduation tracking: every promotion writes to
    `_acceptance_log.json` so the sunset clause has data to evaluate
  - Vocation-alignment hint is REQUIRED (not advisory) per Anti-
    Architect modification §IV.2; promotion fails if a candidate
    has no vocation hint
"""

from __future__ import annotations

import dataclasses
import datetime
import hashlib
import json
import pathlib
import re
from typing import Optional

_REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent

_SECTION_HEADER = "## Foresight candidates (v9.12+)"
_SECTION_INTRO = """\
Per the v9.12 ship (Position B foresight surface),
`bash scripts/ai-foresight.sh --promote` writes top-N foresight
candidates from monthly briefs into this section. Each item carries a
stable ID derived from its title; re-runs are idempotent.

**Operator workflow:**
1. Read the brief at `journal/foresight/YYYY-MM-DD.md` first.
2. Triage candidates here: promote to a real R-id when adopting; mark
   with strikethrough + `<!-- declined: reason -->` when declining.
3. The empirical-graduation rule (50% acceptance over 6 monthly briefs)
   gates whether the foresight surface earns the right to expand into a
   subsystem. Below threshold + 6 briefs in: sunset warning fires.

**Decline marker convention** (same shape as AP-XXXXXXXX):
prefix the line with `- ~~FS-XXXXXXXX~~ <!-- declined: reason -->` to
prevent re-promotion of the same finding even if it surfaces again.

**Promotion rules:**
- LOW + MEDIUM only auto-promote; HIGH still requires Sanctum
- Vocation-alignment hint is REQUIRED (not advisory)
- Idempotent: re-running adds nothing if the FS-ID is present
"""


@dataclasses.dataclass
class PromotionResult:
    """Outcome of a foresight promotion pass."""
    candidates_considered: int
    promoted_new: int
    skipped_existing: int
    skipped_high_risk: int
    skipped_no_vocation: int
    skipped_declined: int
    promoted_ids: list[str]

    def summary_line(self) -> str:
        return (
            f"foresight promoted={self.promoted_new} new "
            f"(considered={self.candidates_considered}, "
            f"existing={self.skipped_existing}, "
            f"high_risk={self.skipped_high_risk}, "
            f"no_vocation={self.skipped_no_vocation}, "
            f"declined={self.skipped_declined})"
        )


def stable_foresight_id(title: str) -> str:
    """Generate a stable 8-hex-char FS-ID from a candidate title."""
    h = hashlib.sha256(title.encode("utf-8")).hexdigest()[:8].upper()
    return f"FS-{h}"


@dataclasses.dataclass
class ForesightCandidate:
    """One §V candidate for promotion."""
    title: str
    rationale: str
    risk_class: str           # LOW | MEDIUM | HIGH
    effort_estimate: str      # one-shot | one-day | multi-ship
    vocation_alignment: str   # REQUIRED non-empty per Anti-Architect mod
    source_section: str       # which brief section it came from


def _read_roadmap(roadmap_path: pathlib.Path) -> str:
    if not roadmap_path.exists():
        return ""
    return roadmap_path.read_text(encoding="utf-8")


def _existing_fs_ids(roadmap_text: str) -> set[str]:
    return set(re.findall(r"FS-[0-9A-F]{8}", roadmap_text))


def _section_exists(roadmap_text: str) -> bool:
    return _SECTION_HEADER in roadmap_text


def _insert_section(roadmap_text: str) -> str:
    """Insert §"Foresight candidates" after §"Auto-promoted action
    candidates" if present, else after §"Layer-1 candidates", else after
    file's intro divider."""
    if _section_exists(roadmap_text):
        return roadmap_text

    # Try to insert after auto-promoted-action section (v9.11)
    for anchor in (
        "## Auto-promoted action candidates (v9.11+)",
        "## Layer-1 candidates",
    ):
        if anchor in roadmap_text:
            idx = roadmap_text.index(anchor)
            rest = roadmap_text[idx + len(anchor):]
            next_section = re.search(r"\n(## |---)", rest)
            if next_section:
                insertion_point = idx + len(anchor) + next_section.start() + 1
            else:
                insertion_point = len(roadmap_text)
            insertion = f"\n{_SECTION_HEADER}\n\n{_SECTION_INTRO}\n"
            return roadmap_text[:insertion_point] + insertion + roadmap_text[insertion_point:]

    # Fallback: after first ---
    m = re.search(r"\n---\n", roadmap_text)
    if m:
        insertion_point = m.end()
    else:
        insertion_point = len(roadmap_text)
    insertion = f"\n{_SECTION_HEADER}\n\n{_SECTION_INTRO}\n"
    return roadmap_text[:insertion_point] + insertion + roadmap_text[insertion_point:]


def _format_candidate_entry(c: ForesightCandidate, fs_id: str) -> str:
    timestamp = datetime.date.today().isoformat()
    return (
        f"\n- **{fs_id}** ({c.risk_class}/{c.effort_estimate}, source=foresight: §{c.source_section}) "
        f"— {c.title}\n"
        f"  - rationale: {c.rationale}\n"
        f"  - vocation: {c.vocation_alignment}\n"
        f"  - first promoted: {timestamp}\n"
    )


def _update_acceptance_log(
    promoted_ids: list[str],
    candidates: list[ForesightCandidate],
    log_path: pathlib.Path,
) -> None:
    """Mark each newly-promoted FS-ID as 'open' in the acceptance log."""
    if log_path.exists():
        try:
            log = json.loads(log_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            log = {"briefs": [], "candidates": {}}
    else:
        log = {"briefs": [], "candidates": {}}

    log.setdefault("candidates", {})
    today = datetime.date.today().isoformat()
    id_to_candidate = dict(zip(promoted_ids, candidates))
    for fs_id in promoted_ids:
        c = id_to_candidate.get(fs_id)
        log["candidates"][fs_id] = {
            "title": c.title if c else "",
            "promoted_at": today,
            "status": "open",
            "vocation_alignment": c.vocation_alignment if c else "",
        }
    log_path.write_text(json.dumps(log, indent=2, sort_keys=True), encoding="utf-8")


def promote_foresight_candidates(
    candidates: list[ForesightCandidate],
    roadmap_path: Optional[pathlib.Path] = None,
    top_n: int = 3,
) -> PromotionResult:
    """Promote top-N foresight candidates into ROADMAP.md."""
    if roadmap_path is None:
        roadmap_path = _REPO_ROOT / "ROADMAP.md"

    result = PromotionResult(
        candidates_considered=len(candidates),
        promoted_new=0,
        skipped_existing=0,
        skipped_high_risk=0,
        skipped_no_vocation=0,
        skipped_declined=0,
        promoted_ids=[],
    )

    if not candidates:
        return result

    roadmap_text = _read_roadmap(roadmap_path)
    if not roadmap_text:
        # ROADMAP.md is constitutional; refuse to create it
        return result

    existing_ids = _existing_fs_ids(roadmap_text)

    to_promote: list[tuple[ForesightCandidate, str]] = []
    for c in candidates:
        # Vocation-alignment is REQUIRED (Anti-Architect mod, structural)
        if not c.vocation_alignment.strip():
            result.skipped_no_vocation += 1
            continue
        # Risk gate
        if c.risk_class == "HIGH":
            result.skipped_high_risk += 1
            continue

        fs_id = stable_foresight_id(c.title)

        # Idempotency: skip if ID exists (active or struck-through)
        if fs_id in existing_ids:
            decline_pattern = re.compile(
                rf"~~{re.escape(fs_id)}~~", re.IGNORECASE
            )
            if decline_pattern.search(roadmap_text):
                result.skipped_declined += 1
            else:
                result.skipped_existing += 1
            continue

        to_promote.append((c, fs_id))

        if len(to_promote) >= top_n:
            break

    if not to_promote:
        return result

    roadmap_text = _insert_section(roadmap_text)

    # Find section + append entries
    sec_idx = roadmap_text.index(_SECTION_HEADER)
    after_sec = roadmap_text[sec_idx + len(_SECTION_HEADER):]
    next_section = re.search(r"\n## ", after_sec)
    if next_section:
        insertion_point = sec_idx + len(_SECTION_HEADER) + next_section.start()
    else:
        insertion_point = len(roadmap_text)

    new_entries = "".join(_format_candidate_entry(c, fs_id) for c, fs_id in to_promote)
    roadmap_text = roadmap_text[:insertion_point] + new_entries + roadmap_text[insertion_point:]

    roadmap_path.write_text(roadmap_text, encoding="utf-8")

    result.promoted_new = len(to_promote)
    result.promoted_ids = [fs_id for _, fs_id in to_promote]

    # Update acceptance log
    log_path = _REPO_ROOT / "polaris_foresight" / "_acceptance_log.json"
    _update_acceptance_log(
        result.promoted_ids,
        [c for c, _ in to_promote],
        log_path,
    )

    return result


def parse_brief_for_candidates(brief_text: str) -> list[ForesightCandidate]:
    """Parse a rendered Brief markdown back into ForesightCandidate
    objects suitable for promotion.

    Looks at §V section; pulls out FS-CANDIDATE-N items + their
    risk/effort/vocation annotations.

    Implementation: split into bullet lines first (treats one
    candidate per `- **FS-CANDIDATE-N**` bullet, single-line or
    multi-line); then parse each bullet's text for the
    `_risk: ... · effort: ... · vocation: ..._` annotation block.
    """
    candidates: list[ForesightCandidate] = []
    # Find §V section
    m = re.search(
        r"## §V — Three foresight candidates(.*?)(?=^---|\Z)",
        brief_text,
        re.MULTILINE | re.DOTALL,
    )
    if not m:
        return candidates
    sec_v = m.group(1)

    # Split sec_v into one bullet per FS-CANDIDATE-N. Each bullet's
    # body runs from "- **FS-CANDIDATE-N**" to the next bullet OR
    # end-of-section.
    bullets = re.split(r"^-\s+(?=\*\*FS-CANDIDATE-)", sec_v, flags=re.MULTILINE)
    for bullet in bullets:
        bullet = bullet.strip()
        if not bullet.startswith("**FS-CANDIDATE-"):
            continue

        # Title + rationale: everything before the underscore-italics annotation
        # If no annotation present, the whole bullet is the title.
        annot_re = re.compile(
            r"_risk:\s*([^·]+?)\s*·\s*effort:\s*([^·]+?)\s*·\s*vocation:\s*(.+?)_",
            re.DOTALL,
        )
        annot_match = annot_re.search(bullet)

        if annot_match:
            risk = annot_match.group(1).strip().upper()
            effort = annot_match.group(2).strip()
            vocation = annot_match.group(3).strip()
            title_section = bullet[:annot_match.start()].strip()
        else:
            risk = "LOW"
            effort = "one-shot"
            vocation = ""
            title_section = bullet

        if risk not in ("LOW", "MEDIUM", "HIGH"):
            risk = "LOW"

        # Strip the **FS-CANDIDATE-N**: prefix from title_section
        title_clean = re.sub(
            r"^\*\*FS-CANDIDATE-\d+\*\*:?\s*", "", title_section
        ).strip()

        # Title is the first sentence (up to first period followed by space/end)
        title_match = re.match(r"^(.+?\.)(?:\s|$)", title_clean, re.DOTALL)
        if title_match:
            title = title_match.group(1)[:140]
        else:
            title = title_clean[:140]

        candidates.append(ForesightCandidate(
            title=title,
            rationale=title_clean[:300],
            risk_class=risk,
            effort_estimate=effort,
            vocation_alignment=vocation,
            source_section="V",
        ))
    return candidates
