"""ant_release_velocity — Engineer-class observation of release cadence.

Arc G / G1 — Legio Engineer (CUNEUS follower). Where
`ant_build_freshness` (lead) surfaces what's blocking the next
ship, this ant surfaces the *rhythm* of ships: bursts,
stagnation, version-bump cadence.

Slice: `CHANGELOG.md` headers grouped by date + by week. The
Engineer cares about:

  - **Stagnation** — no ship in ≥14 days = `drift` (project is
    slowing down).
  - **Sustained burst** — ≥3 consecutive days with ships = `info`
    (high-velocity period; the Engineer notes it but doesn't
    alarm).
  - **Version-bump cadence** — average days between v8.X bumps
    over the last 30 days; if median <1 day, that's mission-creep
    territory (`drift`); if median >7 days, that's slowdown
    (`info`).

Differs from `ant_ship_burst` (TrajectoryWatcher's tier-1 in
legio_trajectory): ship_burst counts single-date ships; this ant
characterizes the LONGER-TERM cadence. The two ants are
complementary; both can fire on the same data without
duplication.

CUNEUS doctrine: deploys only if the lead ant
(`ant_build_freshness`) fired, indicating something about the
build state is worth understanding alongside the cadence.

G17 (acceleration ant, read-only).

Determinism: optional `at` parameter for replay safety.

Authorized by `sanctum/2026-05-13-arc-g-roman-empire-opening.md`.
"""

from __future__ import annotations

import re
import statistics
from collections import defaultdict
from datetime import datetime, timezone

from polaris_swarm.base import Ant, AntFinding, KIND_DRIFT, KIND_INFO


# Parse `## v8.X — YYYY-MM-DD (subtitle)` headers
HEADER_RE = re.compile(
    r"^## v8\.(\d+)\s+—\s+(\d{4})-(\d{2})-(\d{2})\b",
    re.MULTILINE,
)

STAGNATION_DAYS = 14.0
RECENT_WINDOW_DAYS = 30.0


class AntReleaseVelocity(Ant):
    NAME = "ant_release_velocity"
    DESCRIPTION = "Engineer (follower): characterizes long-term release cadence (stagnation / sustained burst / version-bump rhythm)."

    def __init__(self, root, seed=None, at: datetime | None = None):
        super().__init__(root, seed=seed)
        self.at = at if at is not None else datetime.now(timezone.utc)

    def scan(self) -> list[AntFinding]:
        findings: list[AntFinding] = []
        changelog = self._read("CHANGELOG.md") or ""
        if not changelog:
            return findings
        # Parse all v8.X ships with dates
        ships: list[tuple[int, datetime]] = []
        for m in HEADER_RE.finditer(changelog):
            try:
                v = int(m.group(1))
                y, mo, d = int(m.group(2)), int(m.group(3)), int(m.group(4))
                ts = datetime(y, mo, d, tzinfo=timezone.utc)
                ships.append((v, ts))
            except (TypeError, ValueError):
                continue
        if not ships:
            return findings
        # Latest ship + stagnation check
        ships.sort(key=lambda x: x[1])
        latest = ships[-1][1]
        days_since_latest = (self.at - latest).total_seconds() / 86400.0
        if days_since_latest > STAGNATION_DAYS:
            findings.append(AntFinding(
                node_id="release:stagnation",
                intensity=round(min(6.0, 2.0 + days_since_latest / 14.0), 3),
                kind=KIND_DRIFT,
                evidence={
                    "message": (
                        f"latest ship was {days_since_latest:.1f}d ago; "
                        f"project may be stagnating"
                    ),
                    "days_since_latest_ship": round(days_since_latest, 3),
                    "latest_version": f"v8.{ships[-1][0]}",
                    "latest_date": latest.date().isoformat(),
                    "fix_hint": (
                        "if work is happening, document via "
                        "CHANGELOG; if not, consider what's blocking"
                    ),
                },
                half_life_hours=168.0,
            ))
        # Version-bump cadence over recent window
        recent = [
            (v, ts) for v, ts in ships
            if (self.at - ts).total_seconds() / 86400.0 <= RECENT_WINDOW_DAYS
        ]
        if len(recent) >= 3:
            # Sort by ts ascending; compute deltas between consecutive
            recent.sort(key=lambda x: x[1])
            gaps = []
            for i in range(1, len(recent)):
                gap_days = (recent[i][1] - recent[i-1][1]).total_seconds() / 86400.0
                gaps.append(gap_days)
            if gaps:
                median_gap = statistics.median(gaps)
                if median_gap < 1.0:
                    findings.append(AntFinding(
                        node_id="release:cadence_fast",
                        intensity=round(min(6.5, 3.0 + (1.0 - median_gap) * 3.0), 3),
                        kind=KIND_DRIFT,
                        evidence={
                            "message": (
                                f"median inter-ship gap is "
                                f"{median_gap:.2f}d over last "
                                f"{RECENT_WINDOW_DAYS:.0f}d; "
                                f"sustained mission-creep territory"
                            ),
                            "median_gap_days": round(median_gap, 3),
                            "ships_in_window": len(recent),
                            "interpretation": (
                                "if each ship was Sanctum-authorized "
                                "and in-scope, the cadence is healthy; "
                                "otherwise consider why the pace is "
                                "this fast"
                            ),
                        },
                        half_life_hours=168.0,
                    ))
                elif median_gap > 7.0:
                    findings.append(AntFinding(
                        node_id="release:cadence_slow",
                        intensity=2.5,
                        kind=KIND_INFO,
                        evidence={
                            "message": (
                                f"median inter-ship gap is "
                                f"{median_gap:.1f}d over last "
                                f"{RECENT_WINDOW_DAYS:.0f}d; "
                                f"deliberate slow cadence"
                            ),
                            "median_gap_days": round(median_gap, 3),
                            "ships_in_window": len(recent),
                        },
                        half_life_hours=168.0,
                    ))
        # Sustained-burst characterization: count consecutive days
        # with ships in the recent window
        by_date: dict[str, int] = defaultdict(int)
        for v, ts in recent:
            by_date[ts.date().isoformat()] += 1
        sorted_dates = sorted(by_date.keys())
        max_streak = 0
        cur_streak = 0
        prev: datetime | None = None
        for ds in sorted_dates:
            cur = datetime.strptime(ds, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            if prev is None or (cur - prev).days == 1:
                cur_streak += 1
            else:
                cur_streak = 1
            max_streak = max(max_streak, cur_streak)
            prev = cur
        if max_streak >= 3:
            findings.append(AntFinding(
                node_id="release:sustained_burst",
                intensity=round(min(5.0, 2.5 + max_streak * 0.5), 3),
                kind=KIND_INFO,
                evidence={
                    "message": (
                        f"sustained burst: {max_streak} consecutive "
                        f"days with ships in last {RECENT_WINDOW_DAYS:.0f}d"
                    ),
                    "consecutive_days": max_streak,
                    "ships_in_window": len(recent),
                },
                half_life_hours=72.0,
            ))
        return findings
