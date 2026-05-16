"""ant_journal_silence — pheromone if today's journal is untouched.

Slice: `journal/YYYY-MM-DD.md` for the current date.

Local rule: if today's journal exists but hasn't been touched in
≥ N hours (default 6), deposit a `curious` pheromone. The intensity
scales with hours-of-silence.

This is a TIME-OF-SCAN-dependent ant. To preserve determinism, the
"current time" used by the ant is supplied by the runner (not pulled
from the OS clock inside the scan method). This means: replay with
the same `at` parameter produces identical findings.

Rationale: long journal silences during a working day can indicate
scope-creep, stuck-loop, or the agent forgot to write decisions.
This is a CURIOUS pheromone (not an alert) because silence is
sometimes appropriate (e.g. weekend, holiday, finished session).
The pheromone gives the operator a signal to investigate, not a
command.
"""

from __future__ import annotations

from datetime import datetime, timezone

from polaris_swarm.base import Ant, AntFinding, KIND_CURIOUS


SILENCE_THRESHOLD_HOURS = 6.0


class AntJournalSilence(Ant):
    NAME = "ant_journal_silence"
    DESCRIPTION = "Pheromones today's journal if untouched for hours."

    def __init__(self, root, seed=None, at: datetime | None = None):
        super().__init__(root, seed=seed)
        # `at` is the runner-supplied current time. Default uses UTC now()
        # ONLY when not in a replay. Tests supply `at` explicitly.
        self.at = at if at is not None else datetime.now(timezone.utc)

    def scan(self) -> list[AntFinding]:
        findings: list[AntFinding] = []
        today = self.at.strftime("%Y-%m-%d")
        path = self.root / "journal" / f"{today}.md"
        if not path.is_file():
            # No journal for today yet — silence is implicit, but the
            # ant doesn't fire on "doesn't exist" (that's a different ant).
            return findings
        try:
            mtime_ts = path.stat().st_mtime
        except OSError:
            return findings
        mtime = datetime.fromtimestamp(mtime_ts, tz=timezone.utc)
        age_hours = (self.at - mtime).total_seconds() / 3600.0
        if age_hours < SILENCE_THRESHOLD_HOURS:
            return findings
        # Intensity scales: 6h -> 1.0, 12h -> 2.0, 24h -> 4.0, 48h -> 8.0,
        # cap at 9.0 (just under the schema check of <=10).
        intensity = min(9.0, age_hours / 6.0)
        findings.append(AntFinding(
            node_id=f"file:journal/{today}.md",
            intensity=round(intensity, 3),
            kind=KIND_CURIOUS,
            evidence={
                "message": f"today's journal untouched for {age_hours:.1f} hours",
                "file": f"journal/{today}.md",
                "threshold_hours": SILENCE_THRESHOLD_HOURS,
                "fix_hint": "if work is happening, run `scripts/ai-journal.sh decision \"...\"` to log it",
            },
            half_life_hours=6.0,  # short half-life: silence fades fast once broken
        ))
        return findings
