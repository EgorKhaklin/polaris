"""AntColonyWatcher — HYDRA's 8th head (v8.72 / mythology relocation).

v9.04 refresh: now uses `polaris_hydra.pheromone_reader.PheromoneReader`
to split the swarm report by tier (commander vs soldier) + add
per-soldier-class freshness checks (alert if any v9.03 soldier class
silent for >2h). Sanctum: 2026-05-14-hydra-revamp-pheromone-integration.

Where the original 7 watchers observe Polaris's *project state*
(schema, cognitive layer, security, mission, adversary models,
performance, trajectory), this watcher observes the **Mycelium
swarm's runtime state**.

The Mycelium swarm became the primary scanning layer in Arc E
(v8.62+), then split into commander + soldier tiers in v9.03. Prior
to v9.04 this watcher counted pheromones flat ("33 in window") with
no commander-vs-soldier distinction; v9.04 fixes that gap so HYDRA
can see *which tier* is silent.

Five channels:

  1. **Pheromone volume + tier split.** Counts deposits over the last
     6h (PheromoneReader default), split into commander_count vs
     soldier_count.
       - 0 deposits total → `alert` (swarm not running OR not connected)
       - <10 deposits over 6h → `drift` (swarm under-firing)
       - commander_count == 0 but soldier_count > 0 → `drift`
         (commander tier silent; rare since soldiers usually fire
         alongside commanders, but the asymmetry is itself a signal)

  2. **Per-soldier-class freshness (v9.04).** Reads
     `PheromoneSnapshot.per_soldier_class`. For each of the 9 known
     soldier classes (8 v9.03 workers: route_pinger, file_mtime,
     process_alive, disk_usage, log_tail, db_table_size,
     heartbeat_freshness, sanctum_freshness; plus 1 v9.11 priest:
     soldier_swarm_witness), checks `is_silent` (no deposit in >2h
     or ever). Emits one drift finding listing all silent classes.
     This is the load-bearing v9.04 add: a missing soldier class
     used to silently disappear from observability; now it surfaces
     within 2h.

  3. **Treasury activity.** Reads `treasury-roll.json` as a swarm
     activity/liveness signal (v9.53: the inert pleb/eques/patrician
     tier classification was removed with the Cursus Honorum economy).
     Flags:
       - Balances skewed strongly negative post-rebalance → `drift`
       - Treasury malformed or missing → `alert` (integrity probe)

  4. **Recent alerts surface.** If the snapshot includes any
     pheromones with kind='alert' in the window, surface their count
     + the deposited_by names as info (the ant_colony watcher does
     not re-grade them — that's the deposit's own claim — but it
     names them so they reach the synthesis brief).

  5. **Cohort sanity.** Counts of ALL_ANTS / ALL_LEGIONS /
     ALL_CITIZENS via import. If imports fail, alert.

Per the v8.44 G1-G5 guards: read-only; deterministic given a
fixed input; graceful failure on missing DB / file. Per
v8.62 G6-G9: this watcher does NOT deposit pheromones (only
ants do); it reads them.

Per the v8.72 Sanctum: this is the 8th head of the Hydra. The
mythology was relocated from Mycelium legions to HYDRA watchers;
the watcher count is the load-bearing element, not the specific
identity of any one watcher.

Authorized by `sanctum/2026-05-13-hydra-mythology-relocation-to-watchers.md`
+ `sanctum/2026-05-14-hydra-revamp-pheromone-integration.md` (v9.04).
"""

from __future__ import annotations

import json
import pathlib
import statistics
from typing import Any

from polaris_hydra.pheromone_reader import (
    PheromoneReader,
    PheromoneSnapshot,
    WINDOW_FAST,
)

from .base import Finding, Watcher, WatcherReport


# Tunables (Schelling-point choices; change with operational evidence).
# v9.05 / D2: aliased to centralized WINDOW_FAST for consistency across
# all pheromone-context channels (security/performance use the same).
PHEROMONE_WINDOW_HOURS = WINDOW_FAST   # v9.04: aligned to commander cron cadence
PHEROMONE_MIN_DEPOSITS_HEALTHY = 10
PHEROMONE_MIN_DEPOSITS_DRIFT_THRESHOLD = 0  # 0 = alert; >0 = drift

# Project root inference
_HERE = pathlib.Path(__file__).resolve().parent
_PROJECT_ROOT = _HERE.parent.parent


def _load_treasury_roll() -> dict | None:
    """Read treasury-roll.json; None if absent or malformed."""
    path = _PROJECT_ROOT / "polaris_swarm" / "civitas" / "treasury-roll.json"
    if not path.is_file():
        return None
    try:
        roll = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(roll, dict):
        return None
    return roll


def _summarize_balances(roll: dict) -> dict[str, Any]:
    """Group balances by property class + extract summary metrics.

    v9.42: dual summary. The aggregate-since-inception min/max is
    forever-polluted by pre-v8.91 frozen -2 penalties (G15 keeps them
    in the ledger). The post-rebalance subset (events matching the
    current policy in operation: +10 reward / -1 penalty) is the
    honest signal for whether the F5 reward function is engaging.
    Mirrors `scripts/ai-treasury-report.sh` which split the same way.
    """
    balances: dict[str, int] = {}
    post_balances: dict[str, int] = {}    # v9.42: post-rebalance subset
    for ev in roll.get("events", []):
        if not isinstance(ev, dict):
            continue
        ant = ev.get("ant", "(unknown)")
        amount = int(ev.get("amount", 0))
        balances[ant] = balances.get(ant, 0) + amount
        if amount in (10, -1):
            post_balances[ant] = post_balances.get(ant, 0) + amount
    # v9.53: the pleb/eques/patrician tier classification was removed with the
    # rest of the inert Cursus Honorum economy (v9.50). The roll is kept as a
    # liveness/activity signal; the never-engaged tiers are not.
    values = list(balances.values())
    median_b = statistics.median(values) if values else 0
    post_values = list(post_balances.values())
    return {
        "ants_with_balance": len(balances),
        "median_balance": median_b,
        "max_positive": max(values) if values else 0,
        "min_negative": min(values) if values else 0,
        # v9.42: post-rebalance (current policy) subset — what the F5
        # finding should actually grade on.
        "post_rebalance_max_positive": max(post_values) if post_values else 0,
        "post_rebalance_min_negative": min(post_values) if post_values else 0,
        "post_rebalance_ants_with_balance": len(post_balances),
    }


class AntColonyWatcher(Watcher):
    """HYDRA's 8th head — observes the Mycelium swarm runtime.

    v9.04: tier-split + per-soldier-class freshness via PheromoneReader.
    """

    name = "ant_colony"
    domain = ("Mycelium swarm runtime "
              "(commander/soldier tiers + per-class freshness + treasury)")

    def _observe(self) -> WatcherReport:
        findings: list[Finding] = []
        summary: dict[str, Any] = {}

        # ---- Channel 1+2+4: Pheromone via reader (tier split + freshness) ----
        reader = PheromoneReader(window_hours=PHEROMONE_WINDOW_HOURS)
        snap: PheromoneSnapshot = reader.snapshot()
        summary["pheromone_window_hours"] = PHEROMONE_WINDOW_HOURS
        summary["pheromone_status"] = snap.status
        summary["commander_count"] = snap.commander_count
        summary["soldier_count"] = snap.soldier_count
        summary["total_count"] = snap.commander_count + snap.soldier_count
        summary["recent_alerts_count"] = len(snap.recent_alerts)
        summary["recent_drift_count"] = len(snap.recent_drift)
        summary["per_soldier_class"] = {
            k: v.to_dict() for k, v in snap.per_soldier_class.items()
        }

        if snap.status == "db_offline":
            findings.append(Finding(
                severity="alert",
                title="Cannot reach Mycelium swarm (DB offline)",
                detail=(
                    f"PheromoneReader returned db_offline status: "
                    f"{snap.error or '(no error detail)'}. The swarm "
                    f"runtime is not observable from this watcher's "
                    f"vantage. Verify Postgres reachability "
                    f"(POLARIS_DB_HOST, POLARIS_DB_NAME) + that "
                    f"psycopg2 is installed in the HYDRA venv."
                ),
                evidence={"window_hours": PHEROMONE_WINDOW_HOURS,
                          "error": snap.error,
                          "node_id": "swarm:db"},
            ))
        else:
            total = snap.commander_count + snap.soldier_count
            if total == 0:
                findings.append(Finding(
                    severity="alert",
                    title="Zero pheromones in window",
                    detail=(
                        f"No pheromone deposits over the last "
                        f"{PHEROMONE_WINDOW_HOURS:.0f}h. The swarm is "
                        f"either not running or not reaching its "
                        f"deposit path."
                    ),
                    evidence={"window_hours": PHEROMONE_WINDOW_HOURS,
                              "node_id": "swarm:cohort"},
                ))
            elif total < PHEROMONE_MIN_DEPOSITS_HEALTHY:
                findings.append(Finding(
                    severity="drift",
                    title=f"Swarm under-firing ({total} deposits)",
                    detail=(
                        f"Only {total} pheromone deposit(s) over "
                        f"{PHEROMONE_WINDOW_HOURS:.0f}h "
                        f"(commanders={snap.commander_count}, "
                        f"soldiers={snap.soldier_count}). "
                        f"Healthy baseline is "
                        f"≥{PHEROMONE_MIN_DEPOSITS_HEALTHY}."
                    ),
                    evidence={"deposits": total,
                              "commander_count": snap.commander_count,
                              "soldier_count": snap.soldier_count,
                              "threshold": PHEROMONE_MIN_DEPOSITS_HEALTHY,
                              "node_id": "swarm:cohort"},
                ))
            else:
                # Tier-asymmetry signal: commanders silent while soldiers fire.
                # Less common than the reverse (soldiers are higher cadence)
                # but real: commanders cron every ~1h, so 0 commanders over
                # 6h is suspicious.
                if snap.commander_count == 0 and snap.soldier_count > 0:
                    findings.append(Finding(
                        severity="drift",
                        title="Commander tier silent (soldiers firing alone)",
                        detail=(
                            f"{snap.soldier_count} soldier deposit(s) "
                            f"in the {PHEROMONE_WINDOW_HOURS:.0f}h "
                            f"window but ZERO commander deposits. "
                            f"Commanders cron every ~1h; six hours of "
                            f"silence suggests the commander legions "
                            f"are not running. Check "
                            f"`scripts/ai-swarm.sh` cron + the "
                            f"polaris_swarm/colony.py entry point."
                        ),
                        evidence={"commander_count": 0,
                                  "soldier_count": snap.soldier_count,
                                  "node_id": "swarm:commander"},
                    ))

            # Channel 2 (the load-bearing v9.04 add):
            # per-soldier-class freshness.
            silent_classes = snap.silent_soldier_classes
            summary["silent_soldier_classes"] = silent_classes
            if silent_classes:
                # Build per-class age-table for the finding detail.
                detail_lines = []
                for name in silent_classes:
                    reading = snap.per_soldier_class.get(name)
                    if reading and reading.age_minutes is not None:
                        detail_lines.append(
                            f"{name} ({reading.age_minutes:.0f}min)"
                        )
                    else:
                        detail_lines.append(f"{name} (never)")
                findings.append(Finding(
                    severity="drift",
                    title=(f"{len(silent_classes)}/{len(snap.per_soldier_class)} "
                           f"soldier class(es) silent >2h"),
                    detail=(
                        f"soldier class(es) silent for >2h "
                        f"(or never seen): "
                        f"{', '.join(detail_lines)}. Either the "
                        f"soldier ant cron stopped, or the class "
                        f"legitimately has nothing to deposit (in "
                        f"which case the threshold can be widened "
                        f"per-class). Check "
                        f"`polaris_swarm/soldiers/<name>.py` + the "
                        f"swarm entry point."
                    ),
                    # v9.10 / S1: shared-surface node_id `runtime:swarm`.
                # cognitive_watcher emits the same when its hydra-brief
                # freshness channel sees a stale brief (HYDRA not running
                # often means swarm not running). Correlation fires when
                # both watchers observe the swarm tier silent.
                    evidence={"silent_classes": silent_classes,
                              "node_id": "swarm:soldier",
                              "additional_node_ids": ["runtime:swarm"]},
                ))

            # Channel 4: surface recent alerts as INFO (not re-grading;
            # just naming so they reach synthesis).
            if snap.recent_alerts:
                top_alerters = sorted({
                    r.deposited_by for r in snap.recent_alerts[:10]
                })
                findings.append(Finding(
                    severity="info",
                    title=(f"{len(snap.recent_alerts)} recent alert "
                           f"pheromone(s) in window"),
                    detail=(
                        f"Pheromones with kind='alert' deposited in "
                        f"the last {PHEROMONE_WINDOW_HOURS:.0f}h by: "
                        f"{', '.join(top_alerters[:5])}"
                        f"{' …' if len(top_alerters) > 5 else ''}. "
                        f"The ant_colony watcher does not re-grade "
                        f"these — each ant's `kind` is its own claim "
                        f"— but they reach this brief."
                    ),
                    evidence={
                        "alert_count": len(snap.recent_alerts),
                        "deposited_by_unique": top_alerters,
                        "node_id": "swarm:cohort",
                    },
                ))

        # ---- Channel 3: treasury distribution (unchanged from v8.85) ----
        roll = _load_treasury_roll()
        if roll is None:
            findings.append(Finding(
                severity="alert",
                title="Treasury roll missing or malformed",
                detail=(
                    "polaris_swarm/civitas/treasury-roll.json could "
                    "not be read; G15 (filesystem-AoR) at risk."
                ),
                evidence={"node_id": "civitas:treasury"},
            ))
            summary["treasury"] = {"status": "missing"}
        else:
            bal_summary = _summarize_balances(roll)
            summary["treasury"] = bal_summary
            # Drift signals on extreme distribution.
            # v8.91 corrected the persistent-silence penalty
            # (DENARII_PENALTY_PERSISTENT 2→1). v9.42: grade on the
            # post-rebalance subset (current policy +10/-1), not the
            # aggregate. The aggregate is forever-skewed by pre-v8.91
            # frozen -2 events (G15); reading it for an F5 signal
            # produces a false-positive drift finding indefinitely.
            post_min = bal_summary["post_rebalance_min_negative"]
            post_max = bal_summary["post_rebalance_max_positive"]
            if post_min < -500 and post_max < 100:
                findings.append(Finding(
                    severity="drift",
                    title="Treasury skewed strongly negative (post-rebalance)",
                    detail=(
                        f"post-rebalance min balance {post_min}; "
                        f"post-rebalance max positive only {post_max}. "
                        f"Under the current +10/-1 policy ants are "
                        f"accruing persistent-silence penalties "
                        f"without offsetting drift-resolution rewards. "
                        f"F5 reward-function signal. (Aggregate "
                        f"min/max ignored per v9.42 — pre-v8.91 "
                        f"events are frozen per G15 and pollute the "
                        f"aggregate forever.)"
                    ),
                    evidence={**bal_summary,
                              "node_id": "civitas:treasury"},
                ))
            # (v9.53: the dead "patrician-class ant(s)" finding was removed —
            # it referenced the F4 Cursus Honorum multiplier retired in v9.50
            # and never fired anyway, since no ant ever approached the tier
            # threshold. The treasury roll is kept as a liveness/activity
            # signal; the inert tier classification is not.)

        # ---- Channel 5: cohort size + legion count sanity ----
        try:
            from polaris_swarm.ants import ALL_ANTS
            from polaris_swarm.legions import ALL_LEGIONS
            from polaris_swarm.civitas import ALL_CITIZENS
            cohort_summary = {
                "ants": len(ALL_ANTS),
                "legions": len(ALL_LEGIONS),
                "citizens": len(ALL_CITIZENS),
            }
            # Try to also count soldier classes (v9.03; optional import)
            try:
                from polaris_swarm.soldiers import ALL_SOLDIERS  # type: ignore
                cohort_summary["soldier_classes"] = len(ALL_SOLDIERS)
            except ImportError:
                cohort_summary["soldier_classes"] = "(not registered)"
            summary["cohort"] = cohort_summary
        except ImportError as e:
            findings.append(Finding(
                severity="alert",
                title="Cannot import polaris_swarm",
                detail=f"Import error: {e}",
                evidence={"exception_type": type(e).__name__,
                          "node_id": "swarm:cohort"},
            ))

        # ---- Aggregate status ----
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
