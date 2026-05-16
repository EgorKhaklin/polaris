"""ActionQueue auto-promotion — closes the observe→correlate→act loop.

v9.11 / Chapter X (closing the loop).

ActionQueue (v9.04) ranks findings into prioritized Actions. Pre-v9.11
those Actions surfaced only in the brief output; the operator had to
manually triage them into ROADMAP.md candidates. The leak between
"observation surfaced" and "operator can act on it" was a constitutional
weakness — the cycle that should be self-amplifying had a gap.

This module promotes top-N Actions into ROADMAP.md as candidate items
under a dedicated §"Auto-promoted action candidates (v9.11+)" section.
Promotion is:

  - **Idempotent.** Each Action gets a stable ID derived from its title
    (sha256 prefix). If the ID is already present in ROADMAP.md, no
    duplicate is written. Re-running the promotion is safe.

  - **Conservative.** Only LOW and MEDIUM risk Actions are promoted
    autonomously. HIGH-risk requires a Sanctum (the existing protocol
    is unchanged). Correlations always promote (multi-watcher consensus
    is high-confidence signal). Singleton findings only promote if
    severity = "alert".

  - **Operator-triageable.** Promoted items are explicitly marked
    "candidate" — the operator promotes them to a real R-id during
    triage, or removes them. The §"Auto-promoted action candidates"
    section is operator-cleanable; nothing in the system depends on
    those items remaining.

  - **Vocation-aware (v9.11).** Each promoted item carries a
    vocation-alignment line referring to MISSION.md §"Vocation". The
    Anti-Architect's AP5 detection reads these lines.

Constitutional contract:
  - C1 / G1 / G3: read-only against findings; only writes to ROADMAP.md
    in the dedicated section
  - Sanctum protocol (Pattern #20): not bypassed; HIGH-risk actions
    are explicitly excluded from auto-promotion
  - Audit-of-record: ROADMAP.md edits are visible in CHANGELOG-adjacent
    diffs; nothing is silently mutated
"""

from __future__ import annotations

import dataclasses
import hashlib
import pathlib
import re
from datetime import datetime, timezone
from typing import Optional

from polaris_hydra.action_queue import Action

# Repo root inferred from this file's location: polaris_hydra/action_promotion.py
_REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent

# Section header that bounds the auto-promotion area in ROADMAP.md.
_SECTION_HEADER = "## Auto-promoted action candidates (v9.11+)"

# Header body inserted on first promotion if the section doesn't exist.
_SECTION_INTRO = """\
Per the v9.11 ship (Chapter X — closing the observe→correlate→act loop),
HYDRA's ActionQueue auto-promotes top-N actionable findings into this
section. Each item carries a stable ID derived from its title; re-runs
of the promotion are idempotent (no duplicates).

**Operator workflow:**
1. Triage these candidates during the next Architect brief review.
2. Promote a candidate to a real R-id (in the prioritized backlog
   below) when adopting it as work.
3. Remove a candidate when explicitly declining (write a one-line
   "declined: <reason>" comment so re-promotion of the same finding
   doesn't re-add it; see the "decline marker" convention below).

**Decline marker convention:** to permanently decline a candidate
without removing the entry, prefix its line with `- ~~AP-XXXXXXXX~~`
(strikethrough) plus a `<!-- declined: reason -->` comment. The
auto-promotion logic detects struck-through entries and does NOT
re-promote even if the underlying finding recurs.

**Promotion rules (conservative by design):**
- Only LOW + MEDIUM risk promote autonomously; HIGH still requires Sanctum
- Correlations (multi-watcher consensus) always promote
- Singleton findings only promote if severity = alert
- Idempotent: re-running adds nothing if the action ID is present
"""


@dataclasses.dataclass
class PromotionResult:
    """Outcome of a promotion pass."""
    candidates_considered: int
    promoted_new: int
    skipped_existing: int
    skipped_high_risk: int
    skipped_severity: int
    skipped_declined: int
    promoted_ids: list[str]

    def summary_line(self) -> str:
        return (
            f"promoted={self.promoted_new} new "
            f"(considered={self.candidates_considered}, "
            f"skipped_existing={self.skipped_existing}, "
            f"skipped_high_risk={self.skipped_high_risk}, "
            f"skipped_severity={self.skipped_severity}, "
            f"skipped_declined={self.skipped_declined})"
        )


def stable_action_id(action: Action) -> str:
    """Generate a stable 8-hex-char ID for an Action based on its title.

    Format: AP-XXXXXXXX. The "AP" prefix means "auto-promoted" — easy
    to grep, distinct from R-ids (real backlog items) and arch-ids
    (Architect brief suggestions).

    Stability: sha256 of the title alone (not score, not timestamp) so
    the same finding promoted today + tomorrow produces the same ID.
    """
    h = hashlib.sha256(action.title.encode("utf-8")).hexdigest()[:8].upper()
    return f"AP-{h}"


def _read_roadmap(roadmap_path: pathlib.Path) -> str:
    """Read ROADMAP.md, returning empty string if missing (caller may
    decide to create it; this module never creates ROADMAP.md from
    scratch — that's a constitutional file)."""
    if not roadmap_path.exists():
        return ""
    return roadmap_path.read_text(encoding="utf-8")


def _existing_action_ids(roadmap_text: str) -> set[str]:
    """Extract all AP-XXXXXXXX IDs already present in ROADMAP.md.

    Includes both active candidates AND struck-through (declined) ones —
    declines should not be re-promoted.
    """
    return set(re.findall(r"AP-[0-9A-F]{8}", roadmap_text))


def _section_exists(roadmap_text: str) -> bool:
    return _SECTION_HEADER in roadmap_text


def _insert_section(roadmap_text: str) -> str:
    """Insert the auto-promotion section just after the existing
    §"Layer-1 candidates" section (if present), else after the file's
    intro paragraph. Idempotent: never inserts if the section already
    exists.
    """
    if _section_exists(roadmap_text):
        return roadmap_text

    # Try to insert after the Layer-1 candidates section (v9.10)
    layer1_marker = "## Layer-1 candidates"
    if layer1_marker in roadmap_text:
        # Find the end of that section: next ## or ---
        idx = roadmap_text.index(layer1_marker)
        # Search for the next ## heading or --- after the marker
        rest = roadmap_text[idx + len(layer1_marker):]
        next_section = re.search(r"\n(## |---)", rest)
        if next_section:
            insertion_point = idx + len(layer1_marker) + next_section.start() + 1
        else:
            insertion_point = len(roadmap_text)
    else:
        # Insert after first --- separator (the file's intro divider)
        m = re.search(r"\n---\n", roadmap_text)
        if m:
            insertion_point = m.end()
        else:
            insertion_point = len(roadmap_text)

    insertion = f"\n{_SECTION_HEADER}\n\n{_SECTION_INTRO}\n"
    return roadmap_text[:insertion_point] + insertion + roadmap_text[insertion_point:]


def _vocation_alignment_line(action: Action) -> str:
    """Generate a one-line vocation-alignment hint for the Action.

    The vocation (MISSION.md §"Vocation"): anti-coercion identity
    substrate. We classify the Action against vocation-keywords; if no
    keyword matches, we mark it "alignment: unclear (operator triage)"
    so the Anti-Architect's AP5 detection has a target.
    """
    text = (action.title + " " + action.rationale).lower()
    if any(kw in text for kw in (
        "auth", "credential", "duress", "compulsion", "coerc",
        "token", "signature", "identity", "verify", "verification",
        "webauthn", "mfa", "redaction", "audit", "append-only",
        "trigger", "rotate", "rotation",
    )):
        return "vocation: anti-coercion (advances identity inviolability)"
    if any(kw in text for kw in (
        "performance", "scaling", "scale", "latency", "throughput",
        "index", "query plan",
    )):
        return "vocation: anti-coercion (operational reliability serves availability of identity)"
    if any(kw in text for kw in (
        "doc", "readme", "convention",
    )):
        return "vocation: support (operator clarity; not direct vocation advance)"
    return "vocation: unclear (operator triage; AP5 candidate)"


def _format_action_entry(action: Action, ap_id: str) -> str:
    """Render one Action as a markdown bullet for the ROADMAP."""
    title_clean = action.title.strip()
    # Truncate rationale to a single sentence-ish for ROADMAP brevity
    rationale_clean = re.sub(r"\s+", " ", action.rationale.strip())
    if len(rationale_clean) > 200:
        rationale_clean = rationale_clean[:197] + "..."
    sources = ", ".join(action.source_watchers) if action.source_watchers else "(unknown)"
    constraints = (", ".join(action.constitutional_constraints_touched)
                   if action.constitutional_constraints_touched else "(none cited)")
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    voc = _vocation_alignment_line(action)

    return (
        f"\n- **{ap_id}** ({action.risk_class}/{action.effort_estimate}, "
        f"score={action.score:.1f}, source={action.source_kind}: {sources}) "
        f"— {title_clean}\n"
        f"  - rationale: {rationale_clean}\n"
        f"  - constraints touched: {constraints}\n"
        f"  - {voc}\n"
        f"  - first promoted: {timestamp}\n"
    )


def promote_actions(
    actions: list[Action],
    roadmap_path: Optional[pathlib.Path] = None,
    top_n: int = 5,
) -> PromotionResult:
    """Promote top-N actions into ROADMAP.md auto-promotion section.

    Args:
        actions: list of Action objects from ActionQueue.rank().
                 Order matters: caller should pre-sort by score (which
                 ActionQueue.rank does).
        roadmap_path: path to ROADMAP.md. Defaults to repo's ROADMAP.md.
        top_n: maximum number of NEW actions to promote per call.
               Existing-not-yet-declined candidates are NOT re-counted
               against this budget; only newly-promoted ones are.

    Returns:
        PromotionResult with counts + the IDs of newly-promoted actions.

    Side effects:
        Modifies roadmap_path in place if any new actions are promoted.
        Idempotent: re-running with the same actions adds nothing.
    """
    if roadmap_path is None:
        roadmap_path = _REPO_ROOT / "ROADMAP.md"

    result = PromotionResult(
        candidates_considered=len(actions),
        promoted_new=0,
        skipped_existing=0,
        skipped_high_risk=0,
        skipped_severity=0,
        skipped_declined=0,
        promoted_ids=[],
    )

    if not actions:
        return result

    roadmap_text = _read_roadmap(roadmap_path)
    if not roadmap_text:
        # ROADMAP.md is constitutional; refuse to create it
        # (this signals a deeper problem the operator should investigate)
        return result

    existing_ids = _existing_action_ids(roadmap_text)

    # Filter actions through promotion rules
    to_promote: list[tuple[Action, str]] = []
    for action in actions:
        # Rule: HIGH-risk requires Sanctum, not auto-promotion
        if action.risk_class == "HIGH":
            result.skipped_high_risk += 1
            continue

        # Rule: singleton findings (source_kind="finding") only promote
        # if their score implies alert severity (score >= 7 from the
        # severity_score table; correlations bypass this)
        if action.source_kind == "finding" and action.score < 7:
            result.skipped_severity += 1
            continue

        ap_id = stable_action_id(action)

        # Rule: idempotency — skip if ID already exists in ROADMAP.md
        # (this catches both active and struck-through entries)
        if ap_id in existing_ids:
            # Check if it was specifically declined (struck-through)
            decline_pattern = re.compile(
                rf"~~{re.escape(ap_id)}~~", re.IGNORECASE
            )
            if decline_pattern.search(roadmap_text):
                result.skipped_declined += 1
            else:
                result.skipped_existing += 1
            continue

        to_promote.append((action, ap_id))

        if len(to_promote) >= top_n:
            break

    if not to_promote:
        return result

    # Ensure section exists
    roadmap_text = _insert_section(roadmap_text)

    # Find the section + append entries
    sec_idx = roadmap_text.index(_SECTION_HEADER)
    # Find next ## heading or end-of-file
    after_sec = roadmap_text[sec_idx + len(_SECTION_HEADER):]
    next_section = re.search(r"\n## ", after_sec)
    if next_section:
        insertion_point = sec_idx + len(_SECTION_HEADER) + next_section.start()
    else:
        insertion_point = len(roadmap_text)

    new_entries = "".join(_format_action_entry(a, ap_id) for a, ap_id in to_promote)
    roadmap_text = roadmap_text[:insertion_point] + new_entries + roadmap_text[insertion_point:]

    roadmap_path.write_text(roadmap_text, encoding="utf-8")

    result.promoted_new = len(to_promote)
    result.promoted_ids = [ap_id for _, ap_id in to_promote]
    return result
