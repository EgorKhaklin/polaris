"""QuaestorTreasurer — the financial magistrate of the Civitas.

The Quaestores were Roman magistrates responsible for the
treasury — overseeing public funds, managing payments, and
maintaining records of state finance. The cursus honorum required
serving as Quaestor before any higher magistracy: financial
competence preceded all other public service.

In the swarm, the Quaestor maintains
`polaris_swarm/civitas/treasury-roll.json` — the ledger of denarii
rewarded to ants for drift-resolution. Each pass:

  1. Read last pass's pheromone fingerprints from the roll
  2. Compare to this pass's pheromones (heartbeats + civitas
     observations filtered out)
  3. Compute rewards: fingerprints present-then-absent = drift
     resolved = +10 denarii to the responsible ant
  4. Compute penalties: fingerprints persistent for ≥3 passes =
     -2 denarii (persistent silence)
  5. Append events to the ledger; update last_pass_fingerprints
  6. Emit citizen findings summarizing the treasury activity

The Quaestor's pheromones are summaries — they don't influence
the reward function (which is deterministic per G16). They tell
the operator what the treasury did this pass.

Authorized by `sanctum/2026-05-13-arc-f-denarius-opening.md`.
"""

from __future__ import annotations

from polaris_swarm.civitas.base import (
    Citizen, CitizenFinding, CIVITAS_CENSORES,  # Quaestor maps closest to Censor class
)
from polaris_swarm.civitas.treasury import (
    DENARII_PER_RESOLUTION, DENARII_PENALTY_PERSISTENT,
    PERSISTENT_THRESHOLD_PASSES,
    compute_rewards, load_roll, save_roll, all_balances, property_class,
)
from datetime import datetime, timezone


# The Quaestor is its own civic class. Adding to civitas/base.py
# would expand VALID_CIVITAS_CLASSES; here we use a unique
# observation_type and treat the Quaestor's class as 'quaestor'
# via the evidence JSONB.
QUAESTOR_CLASS = "quaestor"


class QuaestorTreasurer(Citizen):
    NAME          = "quaestor_treasurer"
    # Use the existing CIVITAS_CENSORES class as the registry slot
    # (the Quaestor IS a roll-keeper too, like the Censor — they
    # share filesystem-AoR semantics). The unique observation_type
    # distinguishes Quaestor activity from Censor activity.
    CIVITAS_CLASS = CIVITAS_CENSORES
    DESCRIPTION   = "Quaestor — financial magistrate; maintains the treasury of denarii."

    def observe(self, recent_pheromones: list[dict]) -> list[CitizenFinding]:
        findings: list[CitizenFinding] = []

        # Load the treasury roll (filesystem-AoR)
        roll = load_roll(self.root)
        last_fingerprints = roll.get("last_pass_fingerprints", {})

        # Compute rewards/penalties for this pass
        events, new_fingerprints = compute_rewards(
            last_fingerprints, recent_pheromones,
        )

        # Append events to the ledger (G15: append-only)
        for ev in events:
            roll["events"].append(ev.to_dict())

        # Update last_pass_fingerprints for next pass
        roll["last_pass_fingerprints"] = new_fingerprints
        roll["last_pass_taken"] = datetime.now(timezone.utc).isoformat()

        # Persist (filesystem-AoR per G15)
        try:
            save_roll(self.root, roll)
        except OSError:
            pass  # graceful — read-only filesystem, dry-run, etc.

        # Emit citizen findings summarizing the treasury activity
        rewards = [e for e in events if e.amount > 0]
        penalties = [e for e in events if e.amount < 0]

        if rewards:
            total_awarded = sum(e.amount for e in rewards)
            findings.append(CitizenFinding(
                node_id="treasury:rewards",
                intensity=min(8.0, 2.0 + len(rewards) * 0.5),
                kind="info",
                observation_type="denarii_awarded",
                evidence={
                    "message": (
                        f"Quaestor observation: awarded {total_awarded} denarii "
                        f"to {len(rewards)} ant(s) for drift resolution this pass"
                    ),
                    "civitas_class": QUAESTOR_CLASS,
                    "rewards_count": len(rewards),
                    "total_awarded": total_awarded,
                    "denarii_per_resolution": DENARII_PER_RESOLUTION,
                },
                half_life_hours=72.0,
            ))

        if penalties:
            total_penalty = sum(-e.amount for e in penalties)
            findings.append(CitizenFinding(
                node_id="treasury:penalties",
                intensity=min(6.0, 2.0 + len(penalties) * 0.4),
                kind="curious",
                observation_type="denarii_penalty",
                evidence={
                    "message": (
                        f"Quaestor observation: deducted {total_penalty} denarii "
                        f"from {len(penalties)} ant(s) for persistent silence "
                        f"(≥{PERSISTENT_THRESHOLD_PASSES} passes without resolution)"
                    ),
                    "civitas_class": QUAESTOR_CLASS,
                    "penalty_count": len(penalties),
                    "total_deducted": total_penalty,
                    "threshold_passes": PERSISTENT_THRESHOLD_PASSES,
                },
                half_life_hours=168.0,    # week-scale — penalties deserve longer attention
            ))

        # Optionally: emit a treasury census summary (top-3 balances)
        # but only when we have meaningful balances (avoid noise in early days).
        balances = all_balances(roll)
        if balances and max(balances.values(), default=0) > 0:
            top = sorted(
                balances.items(), key=lambda kv: -kv[1]
            )[:3]
            findings.append(CitizenFinding(
                node_id="treasury:summary",
                intensity=1.5,
                kind="info",
                observation_type="treasury_summary",
                evidence={
                    "message": (
                        f"Quaestor observation: top denarii holders — "
                        + ", ".join(
                            f"{ant} ({bal} denarii, {property_class(bal)})"
                            for ant, bal in top
                        )
                    ),
                    "civitas_class": QUAESTOR_CLASS,
                    "top_balances": [
                        {"ant": ant, "denarii": bal,
                         "property_class": property_class(bal)}
                        for ant, bal in top
                    ],
                },
                half_life_hours=168.0,
            ))

        return findings
