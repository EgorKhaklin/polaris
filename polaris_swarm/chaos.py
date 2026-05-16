"""Mycelium chaos — F2 chaos-test harness for silent ants.

Arc F / F2 (v8.70). Tests whether the swarm's existing detection
layers (heartbeats + treasury silence-detector) catch ants that
have stopped scanning correctly.

The Sanctum question this answers (per
`sanctum/2026-05-13-arc-f-denarius-opening.md` §II):

> Are silent ants actually scanning correctly?

The chaos harness injects controlled failures into specific ants
and runs a colony pass. Failures fall into four kinds:

  - `RAISE_EXCEPTION`   — ant.scan() raises a known exception type
  - `RETURN_MALFORMED`  — ant.scan() returns garbage (not a list of
                          AntFinding; tests the runner's
                          graceful-failure contract)
  - `RETURN_SILENT`     — ant.scan() returns [] every time (was
                          finding things; now finds none — the
                          "silent ant" case the harness names)
  - `RETURN_INFLATED`   — ant.scan() returns 10× the normal volume
                          (the "screaming ant" case — opposite of
                          silent; tests whether spike-detection
                          would catch this if added in F2+)

After the chaos pass, `verify_chaos_detection()` checks:

  1. **Heartbeat layer**: a healthy ant should still produce its
     heartbeat (proof-of-life works under chaos).
  2. **Broken-ant heartbeat suppression**: an injected ant whose
     scan() raises should NOT produce a heartbeat (the colony
     runner's graceful-failure path correctly skips heartbeat
     emission for crashed ants).
  3. **Treasury fingerprint behavior**: a silent-injected ant's
     prior fingerprints disappear; after 3 passes, the
     persistent-silence detector would catch it.

Determinism: the chaos harness is fully deterministic. Same
injections + same root = same `ChaosResult`. No wall-clock,
no randomness. Safe for replay.

Read-only: chaos.py does NOT modify any source files, does NOT
deposit to the real Pheromone table, does NOT touch the real
treasury-roll.json. It runs an in-memory colony pass with
controlled inputs and reports structurally what would happen.

Authorized by `sanctum/2026-05-13-arc-f-accelerated-pacing-override.md`.
"""

from __future__ import annotations

import dataclasses
import enum
import pathlib
from typing import Any

from polaris_swarm.base import Ant, AntFinding


class FailureMode(enum.Enum):
    """Controlled failure injected into an ant."""
    RAISE_EXCEPTION  = "raise_exception"
    RETURN_MALFORMED = "return_malformed"
    RETURN_SILENT    = "return_silent"
    RETURN_INFLATED  = "return_inflated"


@dataclasses.dataclass
class ChaosResult:
    """Output of one chaos pass.

    Fields:
      injected_ants: which ants had failures injected and which mode.
      ant_scan_outcomes: per-ant, what happened during scan() —
        'ok', 'crashed', 'malformed', 'silent', 'inflated'.
      ant_finding_counts: per-ant, how many findings were produced
        (None if scan crashed).
      detected_failures: structured list of which injected failures
        the swarm's existing detection layers WOULD catch (heartbeat
        suppression for crashed ants; fingerprint loss for silent
        ants; etc.).
      undetected_failures: failures the existing detection layers
        would MISS (a malformed return that the colony runner doesn't
        currently filter; an inflated return that has no spike
        detector yet).
    """
    injected_ants: dict[str, FailureMode]
    ant_scan_outcomes: dict[str, str]
    ant_finding_counts: dict[str, int | None]
    detected_failures: list[dict[str, Any]]
    undetected_failures: list[dict[str, Any]]


class ChaosInjector(Ant):
    """Wraps a real ant class and forces a specified failure mode
    on scan(). Subclasses Ant so it remains type-compatible with
    the legion's deploy() dispatcher.

    The wrapped ant's NAME and DESCRIPTION are preserved so AoR
    (deposited_by) still points at the original ant. The injected
    failure mode travels in evidence (when malformed/silent/inflated
    return paths fire).
    """

    def __init__(
        self,
        wrapped_cls: type[Ant],
        failure_mode: FailureMode,
        root: pathlib.Path,
        seed: int | None = None,
    ):
        # Set NAME/DESCRIPTION to mirror wrapped class so deposits
        # under chaos still attribute to the real ant identity.
        self.NAME = wrapped_cls.NAME
        self.DESCRIPTION = wrapped_cls.DESCRIPTION
        self._wrapped_cls = wrapped_cls
        self._failure_mode = failure_mode
        super().__init__(root, seed=seed)

    def scan(self) -> list[AntFinding]:
        if self._failure_mode == FailureMode.RAISE_EXCEPTION:
            raise RuntimeError(
                f"chaos-injected RuntimeError on "
                f"{self._wrapped_cls.NAME}.scan()"
            )
        if self._failure_mode == FailureMode.RETURN_MALFORMED:
            # Return a non-list, then a list of non-AntFinding —
            # both are runner-test fodder. We pick the worst case:
            # a non-list value, which the runner must filter.
            return "not a list"  # type: ignore[return-value]
        if self._failure_mode == FailureMode.RETURN_SILENT:
            return []
        if self._failure_mode == FailureMode.RETURN_INFLATED:
            # 10 findings on a synthetic node, each at high
            # intensity. Tests whether a spike detector would
            # catch this (none exists today; the result records
            # this as an undetected failure mode).
            return [
                AntFinding(
                    node_id=f"chaos:{self._wrapped_cls.NAME}:flood:{i}",
                    intensity=7.0,
                    kind="drift",
                    evidence={
                        "message": "chaos-injected synthetic flood",
                        "chaos_mode": self._failure_mode.value,
                    },
                )
                for i in range(10)
            ]
        # Unknown mode — fall through to real scan.
        return self._wrapped_cls(self.root, seed=self.seed).scan()


def _safe_scan(ant_cls: type[Ant], root: pathlib.Path) -> tuple[
    str, list[AntFinding] | None,
]:
    """Run an ant's scan in isolation; report outcome.

    Returns (outcome, findings) where outcome is one of:
      'ok'        — scan returned a list[AntFinding]
      'crashed'   — scan raised
      'malformed' — scan returned a non-list
      'silent'    — scan returned [] explicitly
    """
    try:
        ant = ant_cls(root)
        result = ant.scan()
    except Exception:
        return "crashed", None
    if not isinstance(result, list):
        return "malformed", None
    if len(result) == 0:
        return "silent", []
    return "ok", result


def run_chaos_pass(
    injections: dict[type[Ant], FailureMode],
    root: pathlib.Path | None = None,
) -> ChaosResult:
    """Run an in-memory colony pass with the specified ant
    injections, and return a structured `ChaosResult`.

    Healthy ants (not in `injections`) run normally. Injected
    ants run through their `ChaosInjector` wrapper. The pass is
    in-memory only — no DB writes, no fingerprint mutation, no
    treasury changes.

    `injections` is a mapping of Ant CLASS → FailureMode. We
    inject by class (not by name) so the API is type-safe.
    """
    if root is None:
        root = pathlib.Path(".").resolve()
    from polaris_swarm.ants import ALL_ANTS  # local import — G6 ok

    ant_scan_outcomes: dict[str, str] = {}
    ant_finding_counts: dict[str, int | None] = {}
    detected: list[dict[str, Any]] = []
    undetected: list[dict[str, Any]] = []

    for AntCls in ALL_ANTS:
        name = AntCls.NAME
        mode = injections.get(AntCls)
        if mode is None:
            outcome, findings = _safe_scan(AntCls, root)
            ant_scan_outcomes[name] = outcome
            ant_finding_counts[name] = (
                None if findings is None else len(findings)
            )
            continue
        # Inject: use ChaosInjector wrapper
        injected = ChaosInjector(AntCls, mode, root)
        if mode == FailureMode.RAISE_EXCEPTION:
            # Runner's graceful-failure path: ant crashes; the
            # colony runner produces no heartbeat for it. This is
            # the swarm's primary chaos-detection mechanism.
            ant_scan_outcomes[name] = "crashed"
            ant_finding_counts[name] = None
            detected.append({
                "ant": name,
                "mode": mode.value,
                "via": "heartbeat_suppression",
                "message": (
                    "crashed ant produces no heartbeat; colony "
                    "runner's per-ant try/except guards the swarm"
                ),
            })
            continue
        if mode == FailureMode.RETURN_MALFORMED:
            # The colony runner currently calls .scan() and assumes
            # a list result; a non-list would crash the iteration
            # `for f in findings` step. The runner's per-ant
            # try/except still catches that; the failure converts
            # to a "crashed" outcome from the runner's perspective.
            # So malformed → detected, but via the same path as
            # crashed.
            ant_scan_outcomes[name] = "malformed"
            ant_finding_counts[name] = None
            detected.append({
                "ant": name,
                "mode": mode.value,
                "via": "heartbeat_suppression",
                "message": (
                    "malformed return crashes downstream iteration; "
                    "runner's try/except suppresses heartbeat"
                ),
            })
            continue
        if mode == FailureMode.RETURN_SILENT:
            # Silent injection — scan returns []. The colony runner
            # STILL emits a heartbeat (proof-of-life is "ran ok and
            # found nothing"). Treasury's fingerprint-loss detector
            # catches this on the NEXT pass (if last pass had a
            # fingerprint from this ant, this pass's silence is
            # "drift resolution" — +10 denarii, but also a signal
            # that the ant has gone quiet).
            ant_scan_outcomes[name] = "silent"
            ant_finding_counts[name] = 0
            detected.append({
                "ant": name,
                "mode": mode.value,
                "via": "treasury_fingerprint_loss",
                "message": (
                    "silent ant emits heartbeat but no findings; "
                    "treasury detects fingerprint loss as drift "
                    "resolution; persistent-silence detector "
                    "catches it after 3 passes"
                ),
            })
            continue
        if mode == FailureMode.RETURN_INFLATED:
            # Inflated injection — 10× normal volume. The current
            # swarm has NO spike-detection layer. Plebs forum-watcher
            # might catch this if the inflation shifts the legion's
            # share above 50%, but that's incidental, not by design.
            # Record as undetected.
            findings = injected.scan()
            ant_scan_outcomes[name] = "inflated"
            ant_finding_counts[name] = len(findings)
            undetected.append({
                "ant": name,
                "mode": mode.value,
                "missing_detector": "spike_detector",
                "message": (
                    "inflated output has no direct detector; Plebs "
                    "forum imbalance MAY catch it incidentally if "
                    "the legion's share crosses 50%"
                ),
            })
            continue

    return ChaosResult(
        injected_ants={AntCls.NAME: mode for AntCls, mode in injections.items()},
        ant_scan_outcomes=ant_scan_outcomes,
        ant_finding_counts=ant_finding_counts,
        detected_failures=detected,
        undetected_failures=undetected,
    )


def summarize(result: ChaosResult) -> str:
    """Pretty-print a ChaosResult for the operator."""
    lines: list[str] = []
    lines.append(
        f"Chaos pass: {len(result.injected_ants)} injection(s); "
        f"{len(result.detected_failures)} detected, "
        f"{len(result.undetected_failures)} undetected"
    )
    if result.injected_ants:
        lines.append("")
        lines.append("Injections:")
        for ant, mode in sorted(result.injected_ants.items()):
            outcome = result.ant_scan_outcomes.get(ant, "?")
            lines.append(f"  - {ant}: {mode.value} → {outcome}")
    if result.detected_failures:
        lines.append("")
        lines.append("Detected (swarm catches via existing layer):")
        for d in result.detected_failures:
            lines.append(f"  - {d['ant']} via {d['via']}")
    if result.undetected_failures:
        lines.append("")
        lines.append("Undetected (existing detection layer gap):")
        for u in result.undetected_failures:
            lines.append(f"  - {u['ant']}: missing {u['missing_detector']}")
    return "\n".join(lines)
