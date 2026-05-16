"""brief_archive — persist HYDRA briefs + compute deltas across runs.

v9.04 / Sanctum 2026-05-14-hydra-revamp-pheromone-integration.md.

Each `--save`'d brief lands as a Markdown file under
`journal/hydra/<YYYY-MM-DD>-<HHMM>.md`. The format is human-
readable + machine-greppable (sections demarcated by `## `; finding
titles preserved verbatim). The file is the audit trail of HYDRA's
own state-of-the-system claims over time.

`compute_delta()` compares the current brief against the most-recent
prior brief in the directory. The delta surfaces:

  - new_findings: titles in current but not prior
  - closed_findings: titles in prior but not current
  - new_actions: top-3 action titles in current but not prior
  - closed_actions: top-3 action titles in prior but not current

This is the load-bearing piece of the architect persona's
"Self-monitoring" section — gives HYDRA real cross-run memory.

Constitutional contract:
  - C1: brief files are filesystem audit-of-record (per v8.20
    principle); they accumulate; never deleted by HYDRA itself.
    Operator may archive old ones manually if needed.
  - G1 (deterministic): same input synthesis → same Markdown bytes
"""

from __future__ import annotations

import dataclasses
import datetime
import os
import pathlib
import re
from typing import Any, Optional


@dataclasses.dataclass
class BriefDelta:
    """The result of comparing two briefs.

    v9.09 / B — adds `persistent_findings` + `persistent_actions`
    (intersection of prior and current). The missing symmetry: a
    finding/action that's neither new nor closed is *stuck*.
    Operator never acted, OR the finding is unactionable, OR it's
    a permanent state. Different signal worth surfacing.
    """
    prior_path: Optional[str]
    new_findings: list[str]      # titles
    closed_findings: list[str]
    new_actions: list[str]
    closed_actions: list[str]
    # v9.09 additions
    persistent_findings: list[str] = dataclasses.field(default_factory=list)
    persistent_actions: list[str] = dataclasses.field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)

    def is_empty(self) -> bool:
        return not (self.new_findings or self.closed_findings
                    or self.new_actions or self.closed_actions
                    or self.persistent_findings or self.persistent_actions)


def _archive_dir(repo_root: pathlib.Path) -> pathlib.Path:
    """journal/hydra/ — auto-created if missing."""
    d = repo_root / "journal" / "hydra"
    d.mkdir(parents=True, exist_ok=True)
    return d


def archive_brief(
    repo_root: pathlib.Path,
    voice: str,
    reports: list[Any],          # list[WatcherReport]
    correlations: list[Any] = None,    # list[CorrelatedFinding]
    actions: list[Any] = None,         # list[Action]
    pheromone_snapshot: Any = None,   # PheromoneSnapshot
) -> pathlib.Path:
    """Write a Markdown archive of the current brief. Returns the path.

    v9.05 / Wave 1 / D1 — collision detection: filename has minute
    resolution (`%Y-%m-%d-%H%M.md`). Two `--save` invocations within
    the same minute used to silently overwrite the first. Now appends
    `-N` (1, 2, 3, …) until a free path is found. Sorted-by-filename
    ordering preserved (the suffix is lexicographically after no-suffix
    and the next minute's filename starts with new digits, so prior
    briefs sort earlier). C1 preserved: never overwrites.
    """
    correlations = correlations or []
    actions = actions or []
    now = datetime.datetime.now()
    base_stem = now.strftime("%Y-%m-%d-%H%M")
    archive_dir = _archive_dir(repo_root)
    path = archive_dir / (base_stem + ".md")
    # Collision: same-minute --save. Append -1, -2, … until free.
    if path.exists():
        for n in range(1, 1000):
            candidate = archive_dir / f"{base_stem}-{n}.md"
            if not candidate.exists():
                path = candidate
                break
        else:
            # Defensive: 1000 saves in one minute is pathological; raise.
            raise RuntimeError(
                f"brief_archive: > 1000 collisions for {base_stem!r}. "
                f"Refusing to silently overwrite."
            )

    lines: list[str] = []
    lines.append(f"# HYDRA brief — {now.strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")
    lines.append("v9.04 hybrid intelligence brief (HYDRA + swarm).")
    lines.append("")
    lines.append("Auto-archived by `polaris_hydra/brief_archive.py`. ")
    lines.append("Sanctum [`2026-05-14-hydra-revamp-pheromone-integration.md`](../../sanctum/2026-05-14-hydra-revamp-pheromone-integration.md).")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## I. Voice (Architect synthesis)")
    lines.append("")
    lines.append("```")
    lines.append(voice)
    lines.append("```")
    lines.append("")

    # Pheromone snapshot summary
    if pheromone_snapshot is not None:
        lines.append("## II. Swarm substrate (Pheromone snapshot)")
        lines.append("")
        if hasattr(pheromone_snapshot, "to_dict"):
            d = pheromone_snapshot.to_dict()
            lines.append(f"- status: {d.get('status')}")
            lines.append(f"- window_hours: {d.get('window_hours')}")
            lines.append(f"- commander_count: {d.get('commander_count')}")
            lines.append(f"- soldier_count: {d.get('soldier_count')}")
            silent = [n for n, r in d.get("per_soldier_class", {}).items()
                      if r.get("is_silent")]
            if silent:
                lines.append(f"- silent_soldier_classes: {silent}")
            else:
                lines.append("- silent_soldier_classes: (none)")
            recent_alerts = d.get("recent_alerts", [])
            if recent_alerts:
                lines.append(f"- recent_alerts: {len(recent_alerts)} (showing first 5)")
                for r in recent_alerts[:5]:
                    lines.append(f"  - `{r['deposited_by']}` "
                                 f"node=`{r['node_id']}` "
                                 f"intensity={r['intensity']:.2f}")
        lines.append("")

    # Watcher reports
    lines.append("## III. Watcher reports")
    lines.append("")
    for report in reports:
        lines.append(f"### {report.watcher_name} — {report.status}")
        lines.append("")
        lines.append(f"_{report.domain}_")
        lines.append("")
        if not report.findings:
            lines.append("(no findings)")
            lines.append("")
            continue
        for finding in report.findings:
            lines.append(f"- **[{finding.severity}]** {finding.title}")
            lines.append(f"  - {finding.detail}")
        lines.append("")

    # Correlations
    lines.append("## IV. Cross-watcher correlations")
    lines.append("")
    if not correlations:
        lines.append("(none)")
    else:
        for c in correlations:
            lines.append(f"- **[{c.severity}]** {c.title}")
            lines.append(f"  - {c.detail}")
            lines.append(f"  - score: {c.score:.1f}; watchers: "
                         f"{', '.join(c.contributing_watchers)}")
    lines.append("")

    # Actions
    lines.append("## V. Ranked action queue")
    lines.append("")
    if not actions:
        lines.append("(no actions proposed)")
    else:
        for i, a in enumerate(actions, 1):
            lines.append(f"{i}. **{a.title}** "
                         f"(risk={a.risk_class}, effort={a.effort_estimate}, "
                         f"score={a.score:.1f})")
            lines.append(f"   - {a.rationale}")
            if a.constitutional_constraints_touched:
                lines.append(f"   - touches: "
                             f"{', '.join(a.constitutional_constraints_touched)}")
    lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def list_prior_briefs(repo_root: pathlib.Path) -> list[pathlib.Path]:
    """Return all archived briefs sorted oldest → newest."""
    d = _archive_dir(repo_root)
    out = sorted(d.glob("*.md"))
    return out


_FINDING_LINE = re.compile(r"^- \*\*\[(info|drift|alert)\]\*\* (.+)$")
_ACTION_LINE = re.compile(r"^\d+\. \*\*(.+?)\*\*")


def _extract_titles(brief_path: pathlib.Path) -> tuple[list[str], list[str]]:
    """Pull (finding_titles, action_titles) from a saved brief."""
    if not brief_path.is_file():
        return [], []
    text = brief_path.read_text(encoding="utf-8", errors="replace")
    findings: list[str] = []
    actions: list[str] = []
    in_actions = False
    for line in text.splitlines():
        if line.strip().startswith("## V."):
            in_actions = True
            continue
        if line.strip().startswith("## "):
            in_actions = False
        if in_actions:
            m = _ACTION_LINE.match(line)
            if m:
                actions.append(m.group(1).strip())
        else:
            m = _FINDING_LINE.match(line)
            if m:
                findings.append(m.group(2).strip())
    return findings, actions


def compute_delta(
    repo_root: pathlib.Path,
    current_brief_path: pathlib.Path,
    prior_brief_path: Optional[pathlib.Path] = None,
) -> BriefDelta:
    """Compute delta of current brief vs prior. If prior_brief_path
    is None, find the most-recent OTHER brief in journal/hydra/."""
    if prior_brief_path is None:
        all_briefs = list_prior_briefs(repo_root)
        # Pick the most-recent that isn't the current one
        priors = [p for p in all_briefs if p != current_brief_path]
        prior_brief_path = priors[-1] if priors else None

    if prior_brief_path is None:
        # First brief — no delta possible
        return BriefDelta(
            prior_path=None,
            new_findings=[],
            closed_findings=[],
            new_actions=[],
            closed_actions=[],
        )

    cur_findings, cur_actions = _extract_titles(current_brief_path)
    prev_findings, prev_actions = _extract_titles(prior_brief_path)

    cur_findings_set = set(cur_findings)
    prev_findings_set = set(prev_findings)
    cur_actions_set = set(cur_actions[:10])
    prev_actions_set = set(prev_actions[:10])

    return BriefDelta(
        prior_path=_relpath_or_abs(prior_brief_path, repo_root),
        new_findings=sorted(cur_findings_set - prev_findings_set),
        closed_findings=sorted(prev_findings_set - cur_findings_set),
        new_actions=sorted(cur_actions_set - prev_actions_set),
        closed_actions=sorted(prev_actions_set - cur_actions_set),
        # v9.09 / B — persistent = present in both prior and current
        persistent_findings=sorted(cur_findings_set & prev_findings_set),
        persistent_actions=sorted(cur_actions_set & prev_actions_set),
    )


def _relpath_or_abs(path: pathlib.Path, repo_root: pathlib.Path) -> str:
    """relative_to() raises if path isn't under repo_root. v9.05 / D4
    fallback: return absolute path string when the prior brief lives
    outside the repo (e.g., explicit --diff <abs-path>)."""
    try:
        return str(path.relative_to(repo_root))
    except ValueError:
        return str(path)


def compute_delta_in_memory(
    repo_root: pathlib.Path,
    reports: list[Any],
    actions: list[Any],
    prior_brief_path: pathlib.Path,
) -> BriefDelta:
    """v9.05 / Wave 1 / D4 — Compute delta WITHOUT writing a temp file.

    Pre-v9.05, `Hydra.speak_full(diff_against=p, save=False)` wrote a
    temp brief to disk, computed delta against `p`, then conditionally
    cleaned up. The on-disk roundtrip was fragile (cleanup decision
    depended on prior-count) and unnecessary — the finding/action
    titles are already in memory.

    This function extracts titles from the in-memory `reports + actions`
    using the same parsing rules as `_extract_titles()`, then performs
    the same set-difference compute_delta does, against the prior brief
    parsed off disk. No temp file written. C1 preserved.

    Args:
        repo_root: project root (for `prior_path` relativization)
        reports:   list[WatcherReport] from Hydra.gather()
        actions:   list[Action] from ActionQueue.rank()
        prior_brief_path: the brief to diff against

    Returns:
        BriefDelta as compute_delta() would return.
    """
    if not prior_brief_path.is_file():
        # Caller passed an explicit --diff target that doesn't exist.
        # Treat as no-prior — same shape as compute_delta's first-brief path.
        return BriefDelta(
            prior_path=None,
            new_findings=[],
            closed_findings=[],
            new_actions=[],
            closed_actions=[],
        )

    # Extract current finding-titles from in-memory reports.
    # Uses the same shape archive_brief writes (`- **[severity]** title`),
    # then _extract_titles parses out the title group. Equivalent to
    # walking each report's findings.
    cur_finding_titles: list[str] = []
    for report in reports:
        for finding in getattr(report, "findings", []):
            cur_finding_titles.append(finding.title.strip())

    cur_action_titles: list[str] = [
        getattr(a, "title", "").strip() for a in actions
    ]

    prev_findings, prev_actions = _extract_titles(prior_brief_path)

    cur_findings_set = set(cur_finding_titles)
    prev_findings_set = set(prev_findings)
    cur_actions_set = set(cur_action_titles[:10])
    prev_actions_set = set(prev_actions[:10])

    return BriefDelta(
        prior_path=_relpath_or_abs(prior_brief_path, repo_root),
        new_findings=sorted(cur_findings_set - prev_findings_set),
        closed_findings=sorted(prev_findings_set - cur_findings_set),
        new_actions=sorted(cur_actions_set - prev_actions_set),
        closed_actions=sorted(prev_actions_set - cur_actions_set),
        persistent_findings=sorted(cur_findings_set & prev_findings_set),
        persistent_actions=sorted(cur_actions_set & prev_actions_set),
    )


# ============================================================================
# v9.28 / Hydra #3 — cross-run delta of CORRELATED findings as primary output
# ============================================================================
#
# Per v9.28 Sanctum: "Make the cross-run delta the primary output. Most of
# the brief's value is what changed since last run, not the full picture.
# First step: persist last run's correlated findings, emit only new,
# resolved, or escalated, archive the full restatement out of the default
# view."
#
# Distinct from compute_delta() above which works against per-date brief
# files (the audit-of-record archive). The functions below work against
# a SINGLE persisted file that's overwritten each run — purpose-built for
# delta-as-default-view.
# ============================================================================

import json as _json

_LAST_CORRELATED_FILENAME = "_last_correlated.json"


def _last_correlated_path(repo_root: pathlib.Path) -> pathlib.Path:
    return repo_root / "journal" / "hydra" / _LAST_CORRELATED_FILENAME


def persist_correlated(repo_root: pathlib.Path,
                        triage_result: dict) -> pathlib.Path:
    """Persist the latest triage() output for delta computation next run.

    Single file, overwritten each run. The per-date brief archive still
    keeps the full audit-of-record; this is purpose-built for fast delta.
    """
    path = _last_correlated_path(repo_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": "v9.28",
        "ts": _iso_utc_now(),
        "escalations": triage_result.get("escalations", []),
        "lone_alerts": triage_result.get("lone_alerts", []),
        "suppressed_count": (
            triage_result.get("suppressed_below_threshold", {}).get("count", 0)
        ),
    }
    # Use pathlib.write_text for the same v8.37 / G3 "no open(...,'w')"
    # discipline as archive_brief() above.
    path.write_text(_json.dumps(payload, indent=2), encoding="utf-8")
    return path


def delta_correlated(repo_root: pathlib.Path,
                      current_triage: dict) -> dict:
    """Compute the cross-run delta of correlated findings.

    Returns:
      {
        "new":        list of escalations present now, absent before
        "resolved":   list of escalations present before, absent now
        "escalated":  list of correlations whose severity rose
        "unchanged":  count only (suppressed from default view per Hydra #3)
        "first_run":  True if no prior persisted snapshot exists
      }

    Key for matching: (correlation_kind, correlation_key). Per the v9.28
    Sanctum design: delta IS the primary output; the full restatement is
    available behind --full.
    """
    path = _last_correlated_path(repo_root)
    if not path.is_file():
        # First run — every escalation is "new"; no resolveds; no escalations.
        return {
            "first_run": True,
            "new": current_triage.get("escalations", []),
            "resolved": [],
            "escalated": [],
            "unchanged": 0,
        }

    with open(path) as f:
        prior = _json.load(f)

    def key(c: dict) -> tuple:
        return (c.get("correlation_kind"), c.get("correlation_key"))

    cur_list = current_triage.get("escalations", [])
    cur_by_key = {key(c): c for c in cur_list}
    prior_list = prior.get("escalations", [])
    prior_by_key = {key(c): c for c in prior_list}

    new = [c for k, c in cur_by_key.items() if k not in prior_by_key]
    resolved = [c for k, c in prior_by_key.items() if k not in cur_by_key]
    escalated = []
    unchanged = 0

    sev_score = {"info": 1, "drift": 3, "alert": 7}
    for k, c in cur_by_key.items():
        prior_c = prior_by_key.get(k)
        if prior_c is None:
            continue
        prior_sev = sev_score.get(prior_c.get("severity"), 1)
        cur_sev = sev_score.get(c.get("severity"), 1)
        if cur_sev > prior_sev:
            escalated.append({
                **c,
                "prior_severity": prior_c.get("severity"),
            })
        else:
            unchanged += 1

    return {
        "first_run": False,
        "new": new,
        "resolved": resolved,
        "escalated": escalated,
        "unchanged": unchanged,
    }


def _iso_utc_now() -> str:
    import datetime as _dt
    return _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds") + "Z"
