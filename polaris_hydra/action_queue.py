"""ActionQueue — synthesizes findings into a ranked list of next-moves.

v9.04 / Sanctum 2026-05-14-hydra-revamp-pheromone-integration.md.

HYDRA today emits findings. ActionQueue closes the gap from
"observation" to "next move" by ranking the surfaced findings +
correlations into actionable proposals with:

  - title: imperative-form short ("Investigate <thing>")
  - rationale: 1-3 sentence explanation citing the finding sources
  - risk_class: LOW (autonomous-eligible) | MEDIUM (propose-and-wait) |
    HIGH (Sanctum-required)
  - effort_estimate: rough magnitude (one-shot / one-day / multi-ship)
  - constitutional_constraints_touched: list of C-constraints / G-guards
    the action would touch
  - score: ranking value used to order the queue

Ranking formula:
    score = severity_score × confidence × (1 + 0.5 × constitutional_weight)

Where:
  - severity_score: alert=7, drift=3, info=1 (matches CorrelationEngine)
  - confidence: 1 for singleton finding, ≥2 for correlations
  - constitutional_weight: count of C-constraints + G-guards the action
    touches (more important constraints → higher rank)

The queue is intentionally CONSERVATIVE about HIGH-risk actions —
they require a Sanctum, not autonomous execution. ActionQueue
proposes; VANTA disposes.

Constitutional contract:
  - C1 / G1 / G3: read-only against findings; never executes anything
  - F5: may PROPOSE Treasury rebalances but doesn't execute them;
    Sanctum protocol still gates constitutional changes
"""

from __future__ import annotations

import dataclasses
import re
from typing import Any, Optional

from polaris_hydra.watchers.base import Finding, WatcherReport, Severity
from polaris_hydra.correlation import CorrelatedFinding


_SEVERITY_SCORE = {"info": 1, "drift": 3, "alert": 7}

# Risk class for an action based on the source finding's severity +
# the constraints it touches. Ratchet up to HIGH if the finding
# touches C1 or C10 (constitutional load-bearing).
_HIGH_RISK_CONSTRAINTS = {"C1", "C10"}


@dataclasses.dataclass
class Action:
    """One ranked next-move proposal."""
    title: str
    rationale: str
    risk_class: str           # LOW | MEDIUM | HIGH
    effort_estimate: str      # one-shot | one-day | multi-ship
    constitutional_constraints_touched: list[str]
    score: float
    source_kind: str          # "finding" | "correlation"
    source_watchers: list[str]

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


# Heuristic constraint extraction from finding text. The watchers
# don't yet annotate findings with explicit C/G refs (would be a
# nice future addition); this regex pulls them from the title +
# detail when present.
_CONSTRAINT_RE = re.compile(r"\b(C[0-9]+|G[0-9]+)\b")


def _constraints_from_text(*texts: str) -> list[str]:
    """Extract C-constraint / G-guard references from finding text.
    De-duplicated, sorted alphabetically (deterministic)."""
    out: set[str] = set()
    for t in texts:
        if not t:
            continue
        for m in _CONSTRAINT_RE.finditer(t):
            out.add(m.group(1))
    return sorted(out)


def _risk_class_for(severity: Severity, constraints: list[str]) -> str:
    """Ratchet risk class up if constitutional load-bearing constraints
    are touched."""
    if any(c in _HIGH_RISK_CONSTRAINTS for c in constraints):
        return "HIGH"
    if severity == "alert":
        return "MEDIUM"
    if severity == "drift":
        return "LOW"
    return "LOW"


def _effort_estimate_for(severity: Severity, constraints: list[str]) -> str:
    """Rough effort estimate."""
    if any(c in _HIGH_RISK_CONSTRAINTS for c in constraints):
        return "multi-ship"
    if severity == "alert":
        return "one-day"
    return "one-shot"


def _imperative_title(finding_title: str) -> str:
    """Reshape a finding title (often noun-form) into an imperative
    action title. Conservative — keeps the original if it already
    starts with an imperative verb."""
    finding_title = finding_title.strip()
    if not finding_title:
        return "Investigate finding"
    # Already imperative-like?
    first_word = finding_title.split()[0].lower()
    imperative_starters = {
        "fix", "investigate", "review", "address", "close", "ship",
        "open", "verify", "audit", "remove", "rotate", "update",
        "regenerate", "patch", "purge", "archive", "monitor",
        "deploy", "test", "drill", "rerun", "rebuild", "restore",
    }
    if first_word in imperative_starters:
        return finding_title
    # Default: prepend "Investigate"
    return f"Investigate: {finding_title}"


class ActionQueue:
    """Ranks findings + correlations into ordered Actions."""

    def __init__(
        self,
        reports: list[WatcherReport],
        correlations: Optional[list[CorrelatedFinding]] = None,
    ):
        self.reports = reports
        self.correlations = correlations or []

    def rank(self, top_n: Optional[int] = None) -> list[Action]:
        """Produce a ranked list of Actions. If `top_n` is provided,
        truncate to the top N."""
        actions: list[Action] = []

        # Correlations rank highest because confidence ≥ 2 by definition
        for c in self.correlations:
            constraints = _constraints_from_text(c.title, c.detail)
            risk = _risk_class_for(c.severity, constraints)
            effort = _effort_estimate_for(c.severity, constraints)
            score = (
                _SEVERITY_SCORE.get(c.severity, 1)
                * c.confidence
                * (1.0 + 0.5 * len(constraints))
            )
            actions.append(Action(
                title=f"Investigate cross-watcher correlation: {c.correlation_key}",
                rationale=(f"{c.confidence} watcher(s) ({', '.join(c.contributing_watchers)}) "
                           f"independently surfaced findings on {c.correlation_kind}="
                           f"{c.correlation_key!r} with combined severity {c.severity}. "
                           f"Multi-watcher consensus is high-confidence signal."),
                risk_class=risk,
                effort_estimate=effort,
                constitutional_constraints_touched=constraints,
                score=float(score),
                source_kind="correlation",
                source_watchers=c.contributing_watchers,
            ))

        # Singleton findings (one watcher, one observation)
        for report in self.reports:
            for finding in report.findings:
                # Skip info-level singletons — those are housekeeping,
                # not action candidates
                if finding.severity == "info":
                    continue
                constraints = _constraints_from_text(finding.title, finding.detail)
                risk = _risk_class_for(finding.severity, constraints)
                effort = _effort_estimate_for(finding.severity, constraints)
                score = (
                    _SEVERITY_SCORE.get(finding.severity, 1)
                    * 1   # singleton confidence
                    * (1.0 + 0.5 * len(constraints))
                )
                actions.append(Action(
                    title=_imperative_title(finding.title),
                    rationale=(f"{report.watcher_name}_watcher: {finding.detail}"),
                    risk_class=risk,
                    effort_estimate=effort,
                    constitutional_constraints_touched=constraints,
                    score=float(score),
                    source_kind="finding",
                    source_watchers=[report.watcher_name],
                ))

        # Rank by score (highest first); ties broken by:
        # (a) HIGH > MEDIUM > LOW risk
        # (b) alphabetical title
        risk_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
        actions.sort(key=lambda a: (
            -a.score,
            risk_order.get(a.risk_class, 3),
            a.title,
        ))

        if top_n is not None and top_n > 0:
            actions = actions[:top_n]
        return actions
