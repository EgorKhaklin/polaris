"""PlebsForumWatcher — cross-legion volume reader.

The Plebs (Plebeians) class watches the **Forum** — the pheromone
log — for cross-legion volume imbalances. If a single legion
contributes more than `DOMINANT_THRESHOLD` of recent pheromones,
that legion's domain is in crisis (or experiencing a real burst
of activity that warrants visibility).

This is the cross-legion read the bloom does at READ time; the
Plebs do it at SCAN time so the imbalance becomes a pheromone
itself, visible to other citizens (especially Augures).

The Forum is the public space where everything meets. The Plebs
walk it daily.
"""

from __future__ import annotations

from collections import Counter

from polaris_swarm.civitas.base import (
    Citizen, CitizenFinding, CIVITAS_PLEBS,
)


DOMINANT_THRESHOLD = 0.50    # one legion ≥ 50% of recent deposits = imbalance


class PlebsForumWatcher(Citizen):
    NAME          = "plebs_forum_watcher"
    CIVITAS_CLASS = CIVITAS_PLEBS
    DESCRIPTION   = "Plebs in the Forum: watches for cross-legion volume imbalance."

    def observe(self, recent_pheromones: list[dict]) -> list[CitizenFinding]:
        findings: list[CitizenFinding] = []
        if not recent_pheromones:
            return findings

        # Count deposits per legion (from evidence.legio).
        legio_counts: Counter[str] = Counter()
        for ph in recent_pheromones:
            ev = ph.get("evidence") or {}
            legio = ev.get("legio", "(unattributed)")
            legio_counts[legio] += 1

        total = sum(legio_counts.values())
        if total < 4:
            # Too few deposits to draw conclusions
            return findings

        for legio, count in legio_counts.most_common():
            share = count / total
            if share >= DOMINANT_THRESHOLD:
                findings.append(CitizenFinding(
                    node_id=f"forum:{legio}",
                    intensity=round(min(7.0, 3.0 + share * 5.0), 3),
                    kind="info",
                    observation_type="forum_imbalance",
                    evidence={
                        "message": (
                            f"Plebs observation: {legio} contributes "
                            f"{count}/{total} ({share:.0%}) of recent "
                            f"forum deposits — domain may be in crisis "
                            f"or experiencing a genuine activity burst"
                        ),
                        "dominant_legion": legio,
                        "share": round(share, 3),
                        "total_deposits": total,
                    },
                    half_life_hours=12.0,    # half-day; fades fast
                ))
                # Only flag the most dominant legion; one imbalance
                # finding per pass is enough signal.
                break
        return findings
