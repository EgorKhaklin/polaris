"""CivitasWatcher — HYDRA's 9th head (v8.72 / mythology relocation).

The canonical Hydra has nine mortal heads (Apollodorus). With
v8.72 relocating the mythology from Mycelium legions to HYDRA
watchers, this watcher completes the canonical count: it
observes the **citizen layer runtime**.

While AntColonyWatcher (the 8th head) watches the swarm's deposit
behavior, CivitasWatcher watches the **civilian** classes — Plebs,
Equites, Augures, Censores, Quaestores, Tribuni Plebis. Citizens
read the swarm; this watcher reads the citizens.

Four channels:

  1. **Citizen participation.** Which citizens fired in the last
     pass (via `run_swarm(dry=True)` synthesis when DB unreachable,
     or DB query when available). Flags a citizen that hasn't
     fired in N passes as `info` (silent-because-healthy is OK
     for most civic classes, but the operator should know).

  2. **Civic event mix.** Distribution of `observation_type`
     across recent citizen findings: `forum_imbalance`,
     `cross_legion_correlation`, `convergent_attention`,
     `census_event`, `proposal_new_ant`, `tribunician_friction`.
     A pass with ZERO civic events when ants are firing means
     the citizens aren't doing their job.

  3. **Census-roll integrity.** Reads `census-roll.json`; checks
     it exists, parses, has expected schema (`entries`,
     `_g_guard`). G14 (append-only-discipline) verified.

  4. **Quaestor liveness.** Reads `treasury-roll.json`; checks
     `last_pass_taken` is recent (≤7d). Flags `info` if stale,
     `drift` if absent.

Per the watcher contract: read-only, deterministic given fixed
inputs, graceful failure on missing artifacts. Per v8.45's
self-calibration pattern, this watcher's first run may surface
its own design bugs; expect mid-build refinement.

Per the v8.72 Sanctum: this is the 9th head of the Hydra. The
canonical Lernaean count (9 mortal heads) is now matched by
HYDRA's watcher registry. CM remains the immortal 10th head —
constitutional, narrative; the watcher registry does not include
it.

Authorized by `sanctum/2026-05-13-hydra-mythology-relocation-to-watchers.md`.
"""

from __future__ import annotations

import json
import os
import pathlib
from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Any

from .base import Finding, Watcher, WatcherReport


# Tunables
QUAESTOR_STALE_DAYS = 7.0
EXPECTED_CITIZENS = (
    "plebs_forum_watcher",
    "eques_correlator",
    "augur_bloom_reader",
    "censor_roll_keeper",
    "quaestor_treasurer",
    "tribuni_plebis_watcher",
)
EXPECTED_OBSERVATION_TYPES = (
    "forum_imbalance",
    "cross_legion_correlation",
    "augur_convergent_attention",
    "census_event",
    "proposal_new_ant",
    "tribunician_friction",
    "treasury_summary",
)

_HERE = pathlib.Path(__file__).resolve().parent
_PROJECT_ROOT = _HERE.parent.parent


def _load_roll(filename: str) -> dict | None:
    """Read a citizen FS-AoR roll; None if absent or malformed."""
    path = _PROJECT_ROOT / "polaris_swarm" / "civitas" / filename
    if not path.is_file():
        return None
    try:
        roll = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(roll, dict):
        return None
    return roll


def _try_observe_via_dry_swarm_pass() -> list[dict] | None:
    """Run a --dry colony+citizen pass; return the citizen findings
    as list-of-dicts. None on import failure."""
    try:
        from polaris_swarm.colony import run_swarm
        import pathlib as _pl
        _, civitas_results = run_swarm(
            root=_pl.Path(_PROJECT_ROOT), dry=True,
        )
        flat: list[dict] = []
        for citizen, findings in civitas_results:
            for f in findings:
                flat.append({
                    "citizen": citizen.NAME,
                    "civitas_class": (
                        f.evidence.get("civitas_class")
                        if isinstance(f.evidence, dict)
                        else None
                    ),
                    "observation_type": f.observation_type,
                    "node_id": f.node_id,
                    "kind": f.kind,
                    "intensity": f.intensity,
                })
        return flat
    except Exception:
        return None


def _parse_iso(ts: str | None):
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts)
    except (TypeError, ValueError):
        return None


class CivitasWatcher(Watcher):
    """HYDRA's 9th head — observes the citizen layer runtime."""

    name = "civitas"
    domain = "Citizen-layer runtime (six civic classes + their AoR rolls)"

    def _observe(self) -> WatcherReport:
        findings: list[Finding] = []
        summary: dict[str, Any] = {}

        # Channel 1 + 2: citizen participation + event mix
        events = _try_observe_via_dry_swarm_pass()
        if events is None:
            findings.append(Finding(
                severity="alert",
                title="Cannot observe citizen layer",
                detail=(
                    "polaris_swarm.colony.run_swarm() failed; the "
                    "citizen runtime is not observable from this "
                    "watcher's vantage."
                ),
                evidence={},
            ))
            summary["events"] = None
        else:
            firing_citizens = {e["citizen"] for e in events}
            silent = [c for c in EXPECTED_CITIZENS
                      if c not in firing_citizens]
            summary["firing_citizens"] = sorted(firing_citizens)
            summary["silent_citizens"] = silent
            summary["total_civic_events"] = len(events)

            type_counts = Counter(e["observation_type"] for e in events)
            summary["event_mix"] = dict(type_counts)

            if len(events) == 0:
                findings.append(Finding(
                    severity="drift",
                    title="Citizens are silent",
                    detail=(
                        "Zero civic events from this colony pass. "
                        "Either ants are silent (no signal to "
                        "interpret) or citizens are not firing."
                    ),
                    evidence={"firing_citizens": [],
                              "silent_citizens": list(EXPECTED_CITIZENS)},
                ))
            if len(silent) == len(EXPECTED_CITIZENS):
                # All silent — bigger signal
                pass  # already covered by zero-events finding
            elif silent:
                findings.append(Finding(
                    severity="info",
                    title=f"{len(silent)} citizen(s) silent this pass",
                    detail=(
                        f"Silent: {', '.join(silent)}. "
                        "Most citizen classes are designed for "
                        "intermittent firing; investigate only if "
                        "the silence persists across multiple passes."
                    ),
                    evidence={"silent": silent,
                              "firing": sorted(firing_citizens)},
                ))

        # Channel 3: census-roll integrity (G14)
        census = _load_roll("census-roll.json")
        if census is None:
            findings.append(Finding(
                severity="alert",
                title="Census roll missing or malformed",
                detail=(
                    "polaris_swarm/civitas/census-roll.json could "
                    "not be read; G14 (filesystem-AoR) at risk."
                ),
                evidence={},
            ))
            summary["census"] = None
        else:
            entries = census.get("entries")
            # Census-roll `entries` is keyed-by-ant-name (a dict); G14
            # append-only-discipline applies to the keys (once added,
            # never removed). Earlier the watcher mistakenly checked
            # for a list — self-calibration fix on first run.
            if not isinstance(entries, (dict, list)):
                findings.append(Finding(
                    severity="alert",
                    title="Census roll has no `entries` container",
                    detail=(
                        "Census schema is malformed; G14 invariant "
                        "(append-only entries) does not hold — "
                        "`entries` is neither dict nor list."
                    ),
                    evidence={"keys": list(census.keys()),
                              "entries_type": type(entries).__name__},
                ))
                summary["census"] = {"status": "schema_violation"}
            else:
                gguard = census.get("_g_guard", "")
                summary["census"] = {
                    "entry_count": len(entries),
                    "entries_shape": type(entries).__name__,
                    "g_guard_marker": gguard,
                }
                if "G14" not in gguard:
                    findings.append(Finding(
                        severity="drift",
                        title="Census roll missing G14 metadata",
                        detail=(
                            "_g_guard field present but doesn't "
                            "reference G14; documentation drift."
                        ),
                        evidence={"_g_guard": gguard},
                    ))

        # Channel 4: Quaestor liveness via treasury-roll.json
        treasury = _load_roll("treasury-roll.json")
        if treasury is None:
            findings.append(Finding(
                severity="drift",
                title="Treasury roll missing or malformed",
                detail=(
                    "polaris_swarm/civitas/treasury-roll.json could "
                    "not be read; Quaestor liveness unknown."
                ),
                evidence={},
            ))
            summary["quaestor"] = {"status": "missing"}
        else:
            last_pass = _parse_iso(treasury.get("last_pass_taken"))
            if last_pass is None:
                summary["quaestor"] = {
                    "status": "never_run",
                    "last_pass_taken": None,
                }
                findings.append(Finding(
                    severity="info",
                    title="Quaestor has never run",
                    detail=(
                        "treasury-roll.json exists but last_pass_taken "
                        "is null. The Quaestor will populate it on the "
                        "next colony pass."
                    ),
                    evidence={},
                ))
            else:
                age = datetime.now(timezone.utc) - last_pass
                age_days = age.total_seconds() / 86400.0
                summary["quaestor"] = {
                    "last_pass_taken": treasury.get("last_pass_taken"),
                    "age_days": round(age_days, 3),
                    "event_count": len(treasury.get("events", [])),
                }
                if age_days > QUAESTOR_STALE_DAYS:
                    findings.append(Finding(
                        severity="info",
                        title=f"Quaestor stale ({age_days:.1f}d)",
                        detail=(
                            f"Treasury last_pass_taken is "
                            f"{age_days:.1f}d ago (threshold "
                            f"{QUAESTOR_STALE_DAYS}d). If this is "
                            f"intentional (paused swarm), OK; "
                            f"otherwise wire the Quaestor back into "
                            f"colony passes."
                        ),
                        evidence={"age_days": age_days,
                                  "threshold_days": QUAESTOR_STALE_DAYS},
                    ))

        # Aggregate status
        status = "healthy"
        if any(f.severity == "alert" for f in findings):
            status = "alert"
        elif sum(1 for f in findings if f.severity == "drift") >= 2:
            status = "drift"
        elif any(f.severity == "drift" for f in findings):
            status = "drift"

        return WatcherReport(
            watcher_name=self.name,
            domain=self.domain,
            status=status,
            findings=findings,
            evidence_summary=summary,
        )
