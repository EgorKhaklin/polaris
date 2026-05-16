"""CorrelationEngine — find cross-watcher findings on the same domain.

v9.04 / Sanctum 2026-05-14-hydra-revamp-pheromone-integration.md.

After Hydra.gather() collects 9 WatcherReports, this engine looks
for findings across DIFFERENT watchers that touch the same node_id
or related domain. Two security_watcher findings about CSP are
internal to one watcher; a security_watcher CSP finding + a
performance_watcher slow-/api/atlas finding both touching node
"route:/api/atlas" is a CORRELATION worth surfacing.

Correlation discovery rules:

  1. **Exact node_id match across watchers** — strongest signal.
     If watcher A's finding has evidence.node_id="route:/login"
     and watcher B's finding has the same node_id, they correlate.

  2. **Shared domain prefix** — weaker signal. Findings whose
     evidence.node_id share a colon-prefix (e.g., "route:" or
     "schema:" or "infra:routes") cluster.

  3. **Severity multiplier** — alerts correlate higher than drifts
     correlate higher than infos. Severity-product picks the
     correlation's overall severity.

The output `CorrelatedFinding`s feed into ActionQueue ranking:
correlations score higher than singleton findings because they're
multi-watcher consensus.

Constitutional contract:
  - C1 / C10 / G1 / G3: pure read-side; never writes; deterministic
    given the same input WatcherReports
  - F5: never proposes Treasury changes; that's ActionQueue's domain
"""

from __future__ import annotations

import dataclasses
from collections import defaultdict
from typing import Any

from polaris_hydra.watchers.base import Finding, WatcherReport, Severity


# Severity score for ranking (matches the soldier_colony pattern)
_SEVERITY_SCORE = {"info": 1, "drift": 3, "alert": 7}


@dataclasses.dataclass
class CorrelatedFinding:
    """A finding that two or more watchers independently surfaced
    against the same node_id or domain.

    `severity` is the max of the contributing findings' severities.
    `confidence` is the count of contributing watchers (≥ 2).
    `score` is severity_max × confidence — used by ActionQueue.
    """
    title: str
    detail: str
    severity: Severity
    confidence: int                   # number of contributing watchers
    score: float
    contributing_watchers: list[str]
    contributing_findings: list[dict[str, Any]]   # to_dict() form
    correlation_kind: str             # "node_id" | "domain"
    correlation_key: str              # the shared node_id or domain prefix

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


def _node_id_of(finding: Finding) -> str | None:
    """Best-effort extract the PRIMARY node_id from a finding's evidence
    dict. Watchers vary in their evidence shape: some put node_id at the
    top level, some inside a nested 'node' or similar.

    For the FULL set of node_ids (including v9.10 / S1 shared-surface
    additional_node_ids), use `_all_node_ids_of()`.
    """
    ev = finding.evidence or {}
    for key in ("node_id", "node", "route", "endpoint"):
        v = ev.get(key)
        if isinstance(v, str) and v:
            return v
    return None


def _all_node_ids_of(finding: Finding) -> list[str]:
    """v9.10 / S1 (Position B): return ALL node_ids a finding is keyed
    on, including any shared-surface node_ids in
    `evidence.additional_node_ids`.

    The shared-surface convention (DEVNOTES/hydra-pheromone-integration.md
    section "Shared correlation surfaces"): a finding may emit one
    domain-specific node_id (via the primary `node_id` key) AND zero or
    more `runtime:*` shared-surface node_ids (via `additional_node_ids`)
    when the finding touches a concern multiple watchers genuinely
    observe.

    The CorrelationEngine indexes by ALL of them; correlation fires
    when ≥2 distinct watchers emit ANY common node_id.
    """
    out: list[str] = []
    primary = _node_id_of(finding)
    if primary:
        out.append(primary)
    ev = finding.evidence or {}
    additional = ev.get("additional_node_ids")
    if isinstance(additional, list):
        for n in additional:
            if isinstance(n, str) and n and n not in out:
                out.append(n)
    return out


def _domain_prefix_of(node_id: str) -> str:
    """Colon-prefix as the shared-domain key (e.g., 'route:/api/x' → 'route')."""
    if ":" in node_id:
        return node_id.split(":", 1)[0]
    return node_id


class CorrelationEngine:
    """Run after Hydra.gather() to find cross-watcher correlations."""

    def __init__(self, reports: list[WatcherReport]):
        self.reports = reports

    def correlate(self) -> list[CorrelatedFinding]:
        """Find correlations across watchers. Returns ranked by score
        (highest first).

        v9.10 / S1 (Position B): indexes findings by ALL node_ids
        (primary + additional_node_ids) so shared-surface node_ids
        like `runtime:swarm` / `runtime:auth` / `runtime:health`
        — emitted by ≥2 watchers when both observe a shared concern
        — produce correlations.
        """
        out: list[CorrelatedFinding] = []

        # Index findings by (watcher, finding) pairs plus EVERY
        # node_id the finding emits (primary + additional). Same
        # finding may appear under multiple node_ids (one per surface).
        all_pairs: list[tuple[str, Finding, str | None]] = []
        for report in self.reports:
            for finding in report.findings:
                node_ids = _all_node_ids_of(finding)
                if not node_ids:
                    all_pairs.append((report.watcher_name, finding, None))
                else:
                    for nid in node_ids:
                        all_pairs.append((report.watcher_name, finding, nid))

        # Strategy 1: exact node_id match across DIFFERENT watchers
        by_node: dict[str, list[tuple[str, Finding]]] = defaultdict(list)
        for watcher, finding, node_id in all_pairs:
            if node_id is None:
                continue
            by_node[node_id].append((watcher, finding))

        for node_id, contributors in by_node.items():
            distinct_watchers = sorted({w for w, _ in contributors})
            if len(distinct_watchers) < 2:
                continue
            findings = [f for _, f in contributors]
            sev_max = max(
                _SEVERITY_SCORE.get(f.severity, 1) for f in findings
            )
            severity_label: Severity = "alert" if sev_max == 7 else (
                "drift" if sev_max == 3 else "info"
            )
            confidence = len(distinct_watchers)
            score = sev_max * confidence
            out.append(CorrelatedFinding(
                title=f"{len(distinct_watchers)} watchers correlate on node {node_id}",
                detail=(f"Watchers {distinct_watchers} all surfaced findings "
                        f"touching node_id={node_id!r}. Combined severity {severity_label}; "
                        f"confidence {confidence}."),
                severity=severity_label,
                confidence=confidence,
                score=float(score),
                contributing_watchers=distinct_watchers,
                contributing_findings=[f.to_dict() for f in findings],
                correlation_kind="node_id",
                correlation_key=node_id,
            ))

        # Strategy 2: shared domain prefix across DIFFERENT watchers
        # (when no exact node_id match — weaker; only emitted when
        # ≥ 3 watchers share a domain to keep noise down)
        by_domain: dict[str, list[tuple[str, Finding]]] = defaultdict(list)
        for watcher, finding, node_id in all_pairs:
            if node_id is None:
                continue
            domain = _domain_prefix_of(node_id)
            by_domain[domain].append((watcher, finding))
        for domain, contributors in by_domain.items():
            distinct_watchers = sorted({w for w, _ in contributors})
            if len(distinct_watchers) < 3:
                continue
            # Skip if already covered by an exact-node correlation
            # in the same domain (avoid double-emit)
            already = any(c.correlation_kind == "node_id"
                          and _domain_prefix_of(c.correlation_key) == domain
                          for c in out)
            if already:
                continue
            findings = [f for _, f in contributors]
            sev_max = max(
                _SEVERITY_SCORE.get(f.severity, 1) for f in findings
            )
            severity_label = "alert" if sev_max == 7 else (
                "drift" if sev_max == 3 else "info"
            )
            confidence = len(distinct_watchers)
            # Domain correlations get a 0.7× weight (weaker than node_id)
            score = sev_max * confidence * 0.7
            out.append(CorrelatedFinding(
                title=f"{len(distinct_watchers)} watchers cluster in domain {domain}",
                detail=(f"Watchers {distinct_watchers} all surfaced findings "
                        f"in the {domain!r} domain. Weaker signal than exact node "
                        f"match; confidence {confidence}."),
                severity=severity_label,
                confidence=confidence,
                score=float(score),
                contributing_watchers=distinct_watchers,
                contributing_findings=[f.to_dict() for f in findings],
                correlation_kind="domain",
                correlation_key=domain,
            ))

        # Sort by score (highest first); ties broken by alphabetical
        # correlation_key for determinism
        out.sort(key=lambda c: (-c.score, c.correlation_key))
        return out

    # v9.28 / Hydra #2 — escalation + lone-watcher suppression
    # Per Sanctum 2026-05-16 v9.28: "a finding confirmed by two or
    # more independent watchers escalates; a lone-watcher finding is
    # low-confidence by default and suppressed below a threshold."
    def triage(
        self,
        correlated: list[CorrelatedFinding] | None = None,
    ) -> dict[str, Any]:
        """Categorize findings into three buckets:

        - escalations:        ≥2-watcher correlations. The ranked
                              corroboration list. The brief's headline.
        - lone_alerts:        single-watcher findings with severity=alert.
                              Still emitted (alert is non-suppressible)
                              but flagged "uncorroborated" so the
                              operator knows the confidence is lower.
        - suppressed_below:   single-watcher findings with severity
                              below alert. Count emitted; details
                              suppressed from default brief (operator
                              can opt in to see them).

        This is the brief's ranked-corroboration-list shape per Hydra #2.
        """
        if correlated is None:
            correlated = self.correlate()

        # Build a set of (watcher, node_id) pairs that ARE corroborated
        # (i.e., appear in some correlation). Lone findings are those
        # not in this set.
        corroborated_keys: set[tuple[str, str]] = set()
        for c in correlated:
            if c.correlation_kind != "node_id":
                continue
            for w in c.contributing_watchers:
                corroborated_keys.add((w, c.correlation_key))

        lone_alerts: list[dict[str, Any]] = []
        suppressed_below_count = 0
        suppressed_examples: list[str] = []   # first 3 only, for context

        for report in self.reports:
            for finding in report.findings:
                node_ids = _all_node_ids_of(finding)
                # Lone if NO node_id of this finding is in corroborated_keys
                # for this watcher
                is_lone = not any(
                    (report.watcher_name, nid) in corroborated_keys
                    for nid in node_ids
                )
                if not is_lone:
                    continue
                if finding.severity == "alert":
                    lone_alerts.append({
                        "watcher": report.watcher_name,
                        "title": finding.title,
                        "node_ids": node_ids,
                        "confidence": "low (single-watcher; uncorroborated)",
                    })
                else:
                    suppressed_below_count += 1
                    if len(suppressed_examples) < 3:
                        suppressed_examples.append(
                            f"[{finding.severity}] {report.watcher_name}: "
                            f"{finding.title[:60]}"
                        )

        return {
            "escalations": [c.to_dict() for c in correlated],
            "lone_alerts": lone_alerts,
            "suppressed_below_threshold": {
                "count": suppressed_below_count,
                "examples": suppressed_examples,
                "note": "single-watcher findings below alert; opt-in to view",
            },
            "summary": {
                "escalations_count": len(correlated),
                "lone_alerts_count": len(lone_alerts),
                "suppressed_count": suppressed_below_count,
                "load_bearing_metric": (
                    "escalations_count" if len(correlated) > 0
                    else "lone_alerts_count" if len(lone_alerts) > 0
                    else "(quiet)"
                ),
            },
        }
