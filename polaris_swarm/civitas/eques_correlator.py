"""EquesCorrelator — cross-legion courier.

The Equites (Equestrians) were Rome's merchant class — they moved
between cities, between provinces, between social strata. In the
swarm, they move INFORMATION between legions that have not
declared formal alliances (auxilia_pool).

The Eques observes when two un-allied legions fire within a short
window on related signals. The classic example: Legio Schema
flags drift AND Legio Substrate flags drift within 6 hours. This
could be a real **dependency-driven schema regression** that
neither legion alone would surface.

The Eques deposits a "cross_legion_correlation" finding which
Augures (interpreters) can read on the next pass. Information
moves between legions via the Forum, not via direct messages —
this preserves G6 (legions don't talk to each other directly).
"""

from __future__ import annotations

from datetime import datetime, timezone, timedelta

from polaris_swarm.civitas.base import (
    Citizen, CitizenFinding, CIVITAS_EQUITES,
)


# Correlation window: deposits from different legions within this
# many hours are candidates for cross-legion correlation.
CORRELATION_WINDOW_HOURS = 6.0

# Pairs of legions whose co-firing is structurally interesting.
# These are NOT pre-declared alliances (that's AUXILIA); these are
# generic curiosity correlations the Equites watch for.
INTERESTING_PAIRS = [
    ("legio_schema",     "legio_substrate"),    # dependency-driven schema drift
    ("legio_schema",     "legio_security"),     # schema change + security regression
    ("legio_cognitive",  "legio_mission"),      # cognitive drift + mission drift
    ("legio_performance","legio_substrate"),    # perf regression + dependency
    ("legio_docs",       "legio_mission"),      # doc drift + mission drift
    # v8.67 (R bundle from the 100-year-architect Sanctum): added the
    # dominant-signal pairs the simulation revealed. Trajectory is
    # the limes; ship-burst alone or done-list alone is signal, but
    # together (or co-occurring with cognitive drift) they may
    # indicate scope-creep under pressure.
    ("legio_mission",    "legio_trajectory"),   # done-list + ship-burst (the heartbeat of the project)
    ("legio_cognitive",  "legio_trajectory"),   # cognitive drift + scope-creep
]


class EquesCorrelator(Citizen):
    NAME          = "eques_correlator"
    CIVITAS_CLASS = CIVITAS_EQUITES
    DESCRIPTION   = "Eques on horseback: correlates findings across un-allied legions."

    def observe(self, recent_pheromones: list[dict]) -> list[CitizenFinding]:
        findings: list[CitizenFinding] = []
        if not recent_pheromones:
            return findings

        # Group deposits by legion + timestamp.
        per_legio: dict[str, list[datetime]] = {}
        for ph in recent_pheromones:
            ev = ph.get("evidence") or {}
            legio = ev.get("legio", "")
            if not legio:
                continue
            ts = ph.get("deposited_at")
            if ts is None:
                continue
            if isinstance(ts, datetime) and ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            per_legio.setdefault(legio, []).append(ts)

        window = timedelta(hours=CORRELATION_WINDOW_HOURS)
        for legio_a, legio_b in INTERESTING_PAIRS:
            times_a = per_legio.get(legio_a, [])
            times_b = per_legio.get(legio_b, [])
            if not times_a or not times_b:
                continue
            # Find any cross-pair within the window.
            correlated = False
            for ta in times_a:
                for tb in times_b:
                    if abs((ta - tb).total_seconds()) <= window.total_seconds():
                        correlated = True
                        break
                if correlated:
                    break
            if correlated:
                findings.append(CitizenFinding(
                    node_id=f"correlation:{legio_a}+{legio_b}",
                    intensity=4.5,
                    kind="drift",
                    observation_type="cross_legion_correlation",
                    evidence={
                        "message": (
                            f"Eques observation: {legio_a} and {legio_b} "
                            f"both fired within {CORRELATION_WINDOW_HOURS}h — "
                            f"may indicate a cross-domain issue neither "
                            f"legion alone would surface"
                        ),
                        "legio_a": legio_a,
                        "legio_b": legio_b,
                        "deposits_a": len(times_a),
                        "deposits_b": len(times_b),
                        "window_hours": CORRELATION_WINDOW_HOURS,
                    },
                    half_life_hours=24.0,
                ))
        return findings
