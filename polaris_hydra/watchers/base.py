"""Base contract for HYDRA swarm watchers.

A watcher is a deterministic monitor of one Polaris dimension. It
reads observable state (database, files, the live app, the cognitive
layer's outputs) and emits a structured WatcherReport that HYDRA
consumes.

The data contract between watcher and HYDRA is intentionally narrow:

    WatcherReport
      ├── watcher_name: str           # e.g. "schema"
      ├── domain: str                 # one-line description
      ├── status: "healthy" | "drift" | "alert"
      ├── findings: list[Finding]     # specific observations
      ├── evidence_summary: dict      # high-level metrics, JSON-safe
      └── timestamp: datetime

    Finding
      ├── severity: "info" | "drift" | "alert"
      ├── title: str                  # short headline
      ├── detail: str                 # 1-3 sentence explanation
      └── evidence: dict              # raw data the finding points at

Invariants (enforced by convention, not by code):

1. Watchers do NOT call LLMs. Watchers are reproducible from inputs.
2. Watchers do NOT modify state. Read-only against Polaris.
3. Watchers fail gracefully. If something blows up, emit an `alert`
   finding with the exception in `evidence` and return a report
   with status="alert"; do not raise to HYDRA.
4. Reports are JSON-serializable. Use dataclasses + primitives.
"""

from __future__ import annotations

import dataclasses
import datetime
import json
from typing import Any, Literal


Severity = Literal["info", "drift", "alert"]
Status = Literal["healthy", "drift", "alert"]


@dataclasses.dataclass
class Finding:
    """One observation from a watcher.

    `severity` is the watcher's claim about how much VANTA should
    care. `info` is housekeeping; `drift` is a real signal worth
    addressing eventually; `alert` is something that should block a
    ship or trigger an investigation.
    """

    severity: Severity
    title: str
    detail: str
    evidence: dict[str, Any] = dataclasses.field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


@dataclasses.dataclass
class WatcherReport:
    """One watcher's pass over its domain.

    `status` is the aggregate health flag. The convention is:
        - healthy: 0 alert findings, ≤ 1 drift finding
        - drift:   0 alert findings, ≥ 2 drift findings
        - alert:   ≥ 1 alert finding
    But each watcher may compute its own status. HYDRA reads status
    as a hint, not as gospel.
    """

    watcher_name: str
    domain: str
    status: Status
    findings: list[Finding]
    evidence_summary: dict[str, Any]
    timestamp: datetime.datetime = dataclasses.field(
        default_factory=datetime.datetime.now
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "watcher_name": self.watcher_name,
            "domain": self.domain,
            "status": self.status,
            "findings": [f.to_dict() for f in self.findings],
            "evidence_summary": self.evidence_summary,
            "timestamp": self.timestamp.isoformat(timespec="seconds"),
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, sort_keys=False)


class Watcher:
    """Base class. Subclasses override `name`, `domain`, and
    `_observe()`.

    `report()` is the public API HYDRA calls. It wraps `_observe()`
    in graceful-failure: a watcher that crashes returns a one-alert
    report rather than propagating.
    """

    name: str = "unnamed"
    domain: str = "unspecified"

    def report(self) -> WatcherReport:
        try:
            return self._observe()
        except Exception as exc:  # noqa: BLE001 — graceful by design
            return WatcherReport(
                watcher_name=self.name,
                domain=self.domain,
                status="alert",
                findings=[
                    Finding(
                        severity="alert",
                        title=f"{self.name} watcher crashed",
                        detail=f"_observe() raised: {type(exc).__name__}: {exc}",
                        evidence={"exception_type": type(exc).__name__,
                                  "exception_message": str(exc)},
                    )
                ],
                evidence_summary={"crashed": True},
            )

    def _observe(self) -> WatcherReport:
        """Subclasses override. Must return a WatcherReport.

        Implementations should keep their domain narrow + their
        evidence concrete + their findings actionable. A watcher that
        emits 30 findings is doing too much; split it.
        """
        raise NotImplementedError(
            "Subclass must implement _observe()"
        )
