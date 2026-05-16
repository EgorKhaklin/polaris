"""polaris_hydra/oracles.py — external oracles HYDRA must reconcile against.

v9.24 / BIG MISSION Tier 1 #6. The cognitive substrate, prior to this
module, was internally self-consistent: HYDRA reads the Pheromone
substrate that HYDRA-aware watchers write. The Anti-Architect's AP1
(self-observation without ground-touch) is the failure mode this module
exists to break.

An **Oracle** is an external truth-witness that HYDRA does not control.
The brief synthesis must explicitly reconcile against oracle output — if
internal HYDRA findings disagree with the oracle, the brief calls out
the divergence, not the agreement.

Two oracles ship in v9.24:

    Oracle.LAUNCHER — polaris_mac_launch.sh status exit code
                      (the operator's running stack is up / not up)

    Oracle.ADVERSARY — ai-adversary.sh exit code per constraint
                       (the game-theoretic walks did not surface
                       new violations)

The runner writes `meta/oracle-state.json` so the live probes don't run
in the brief's hot path. Re-run cadence: every Saturn-pass (24h) via
cron OR before any --full brief that ships.

Schema of `meta/oracle-state.json`:
    {
        "_doc": "...",
        "last_run_utc": "2026-05-16T...",
        "oracles": {
            "launcher": {
                "status_exit_code": 0,         # 0 = healthy
                "checked_at_utc": "...",
                "raw_stdout_tail": "..."
            },
            "adversary": {
                "per_constraint_exit": {
                    "C1": 0, "C2": 0, ..., "C10": 0
                },
                "checked_at_utc": "...",
                "any_nonzero": false
            }
        }
    }

When `meta/oracle-state.json` is absent or older than 7 days, the
brief's reconciliation block flags `oracle:stale`. Stale oracles are
themselves a kind of finding — the operator should refresh.
"""

from __future__ import annotations

import json
import pathlib
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Optional


_REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
_ORACLE_STATE_PATH = _REPO_ROOT / "meta" / "oracle-state.json"
_STALE_AFTER_DAYS = 7


@dataclass(frozen=True)
class LauncherOracle:
    """Latest known result of `polaris_mac_launch.sh status`.

    `status_exit_code == 0` means the operator's last status-check
    reported the stack up. Any non-zero is a divergence the brief
    must call out.
    """
    status_exit_code: int
    checked_at_utc: str
    raw_stdout_tail: str = ""


@dataclass(frozen=True)
class AdversaryOracle:
    """Latest known per-constraint adversary-walk exit codes.

    `per_constraint_exit` maps constraint label (C1..C10) to exit code.
    `any_nonzero` is True if any constraint walked surfaced a new
    violation since the prior run.
    """
    per_constraint_exit: dict
    checked_at_utc: str
    any_nonzero: bool = False


@dataclass(frozen=True)
class OracleSnapshot:
    """The bundle of oracles read at brief-emit time.

    `status` is one of:
        'present' — both oracles present + non-stale
        'stale'   — at least one oracle present but older than
                    _STALE_AFTER_DAYS
        'absent'  — oracle-state.json missing or unreadable
    """
    status: str
    launcher: Optional[LauncherOracle] = None
    adversary: Optional[AdversaryOracle] = None
    last_run_utc: Optional[str] = None
    age_days: Optional[float] = None


def read_oracles(path: pathlib.Path = _ORACLE_STATE_PATH) -> OracleSnapshot:
    """Read the oracle state from disk.

    If the file is absent, returns OracleSnapshot(status='absent').
    If the file is older than _STALE_AFTER_DAYS, marks it 'stale'.
    Otherwise 'present'.

    The reader NEVER runs the underlying probes itself. That's the
    runner's job (scripts/polaris-oracle-runner.sh). Keeping reader
    deterministic + fast preserves brief-emit latency + G1.
    """
    if not path.is_file():
        return OracleSnapshot(status="absent")

    try:
        raw = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return OracleSnapshot(status="absent")

    last_run_str = raw.get("last_run_utc")
    age_days: Optional[float] = None
    is_stale = False
    if last_run_str:
        try:
            last_run = datetime.fromisoformat(last_run_str.replace("Z", "+00:00"))
            now = datetime.now(timezone.utc)
            age = now - last_run
            age_days = age.total_seconds() / 86400.0
            is_stale = age > timedelta(days=_STALE_AFTER_DAYS)
        except ValueError:
            pass

    oracles_raw = raw.get("oracles", {}) or {}

    launcher_raw = oracles_raw.get("launcher") or {}
    launcher = None
    if launcher_raw:
        launcher = LauncherOracle(
            status_exit_code=int(launcher_raw.get("status_exit_code", -1)),
            checked_at_utc=str(launcher_raw.get("checked_at_utc", "")),
            raw_stdout_tail=str(launcher_raw.get("raw_stdout_tail", "")),
        )

    adversary_raw = oracles_raw.get("adversary") or {}
    adversary = None
    if adversary_raw:
        per_constraint = adversary_raw.get("per_constraint_exit", {}) or {}
        adversary = AdversaryOracle(
            per_constraint_exit={
                str(k): int(v) for k, v in per_constraint.items()
            },
            checked_at_utc=str(adversary_raw.get("checked_at_utc", "")),
            any_nonzero=bool(adversary_raw.get("any_nonzero", False)),
        )

    return OracleSnapshot(
        status="stale" if is_stale else "present",
        launcher=launcher,
        adversary=adversary,
        last_run_utc=last_run_str,
        age_days=age_days,
    )


def reconcile(
    snapshot: OracleSnapshot, internal_findings: list
) -> list[str]:
    """Compare oracle output to internal HYDRA findings.

    Returns a list of one-line reconciliation strings to print in the
    brief. Each string starts with 'AGREE', 'DIVERGE', or 'NOTE' so
    the brief reader can grep for divergences.

    The reconciliation rules (load-bearing for the brief's claim to
    be ground-touching):

      DIVERGE if oracle.launcher.status_exit_code != 0 and zero
        internal findings touch node_id 'runtime:health' or
        'runtime:auth' — the stack is down but HYDRA didn't notice.

      DIVERGE if oracle.adversary.any_nonzero == True and zero
        internal findings touch the same constraint(s) — adversary
        walk found a violation HYDRA missed.

      AGREE if oracle says healthy AND zero ALERT internal findings.

      AGREE if oracle says broken AND ≥1 ALERT internal finding
        touching the same surface.

      NOTE if snapshot.status == 'stale' or 'absent' — operator must
        refresh.
    """
    out: list[str] = []

    if snapshot.status == "absent":
        out.append(
            "NOTE oracle:state-absent — meta/oracle-state.json missing; "
            "run scripts/polaris-oracle-runner.sh to refresh."
        )
        return out

    if snapshot.status == "stale":
        age_str = (
            f"{snapshot.age_days:.1f}d" if snapshot.age_days is not None else "?"
        )
        out.append(
            f"NOTE oracle:stale ({age_str}) — re-run "
            f"scripts/polaris-oracle-runner.sh before shipping."
        )

    if snapshot.launcher is not None:
        launcher_healthy = snapshot.launcher.status_exit_code == 0
        internal_health_alert = _has_alert_touching(
            internal_findings, {"runtime:health", "runtime:auth"}
        )
        if launcher_healthy and not internal_health_alert:
            out.append("AGREE oracle:launcher — stack up, HYDRA no ALERT")
        elif not launcher_healthy and internal_health_alert:
            out.append(
                f"AGREE oracle:launcher (exit={snapshot.launcher.status_exit_code}) "
                f"— HYDRA also flagged ALERT on runtime:health/auth"
            )
        elif not launcher_healthy and not internal_health_alert:
            out.append(
                f"DIVERGE oracle:launcher (exit={snapshot.launcher.status_exit_code}) "
                f"— stack reports unhealthy but HYDRA emitted no ALERT on "
                f"runtime:health/auth. Investigate watcher coverage."
            )
        else:
            out.append(
                "DIVERGE oracle:launcher — HYDRA ALERT on runtime:health/auth "
                "but launcher reports stack up. Either watcher false-positive "
                "or launcher false-negative."
            )

    if snapshot.adversary is not None:
        if not snapshot.adversary.any_nonzero:
            out.append(
                "AGREE oracle:adversary — all C1..C10 walks clean"
            )
        else:
            broken_constraints = [
                c for c, e in snapshot.adversary.per_constraint_exit.items()
                if e != 0
            ]
            internal_touched = _has_alert_touching(
                internal_findings,
                {f"constraint:{c.lower()}" for c in broken_constraints}
                | set(broken_constraints),
            )
            if internal_touched:
                out.append(
                    f"AGREE oracle:adversary — broken: {broken_constraints}, "
                    f"HYDRA also ALERTing on these"
                )
            else:
                out.append(
                    f"DIVERGE oracle:adversary — broken: {broken_constraints}, "
                    f"HYDRA emitted no ALERT on these constraints. "
                    f"Watcher gap or adversary false-positive."
                )

    return out


def _has_alert_touching(findings: list, target_node_ids: set) -> bool:
    """True if any finding has level/severity ALERT AND a node_id in target_node_ids.

    Tolerates both `level` and `severity` field names (legacy + current
    watcher output shapes). Tolerates both string and enum representations.
    """
    if not findings:
        return False

    for f in findings:
        # Try multiple shapes (dict, dataclass, namespace)
        level = _attr(f, "level") or _attr(f, "severity") or ""
        level_str = str(level).upper()
        if "ALERT" not in level_str and "alert" not in str(level):
            continue
        node_id = _attr(f, "node_id") or ""
        if node_id in target_node_ids:
            return True
        # Also check additional_node_ids (v9.10 shared surfaces)
        additional = _attr(f, "additional_node_ids") or []
        if isinstance(additional, list):
            for n in additional:
                if n in target_node_ids:
                    return True
    return False


def _attr(obj, name):
    """Get attribute from object (dataclass / namedtuple) or key from dict.

    Returns None on miss. Tolerates nested .evidence dict for findings
    that wrap node_id inside evidence.
    """
    if obj is None:
        return None
    if isinstance(obj, dict):
        if name in obj:
            return obj[name]
        # Look in evidence sub-dict
        evidence = obj.get("evidence", {}) or {}
        if isinstance(evidence, dict) and name in evidence:
            return evidence[name]
        return None
    v = getattr(obj, name, None)
    if v is not None:
        return v
    # Look in .evidence
    evidence = getattr(obj, "evidence", None)
    if isinstance(evidence, dict):
        return evidence.get(name)
    return None
