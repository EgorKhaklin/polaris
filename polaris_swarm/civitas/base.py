"""Mycelium Civitas — citizens of the swarm, parallel to legions.

A **Citizen** is a non-legionnaire member of the swarm. Citizens
do NOT belong to legions and are NOT instances of Ant. They live
in a parallel class hierarchy.

Where ants scan project artifacts (schema, code, docs) and deposit
findings about the project, **citizens observe the swarm itself**:
they read recent pheromones, they correlate across legions, they
interpret patterns, and they keep the roll of who's in the swarm.

The four civic classes (per Polaris-as-Civitas, v8.66):

  - **Plebs** (Plebeians)     — cross-legion readers
  - **Equites** (Equestrians) — cross-legion couriers
  - **Augures** (Augurs)      — pattern interpreters
  - **Censores** (Censors)    — keepers of the roll

Citizens deposit to the same Pheromone table as ants. AoR is
preserved: `deposited_by` is the citizen's NAME. Citizen class
travels in evidence JSONB as `civitas_class` and the type of
observation as `observation_type`.

CONTRACT (Arc E G12-G14):

  - **G12** — citizens do NOT subclass Ant. Different abstraction
    layer; different observation pattern (citizens take recent
    pheromones as input; ants take no input).
  - **G13** — citizens cannot directly spawn ants. Autogenesis is
    proposal-pheromone-driven only: citizens deposit
    `evidence.type=proposal_new_ant`; operators ratify by
    materializing the proposal as a real ant file. (Roman
    ratification pattern.)
  - **G14** — `census-roll.json` is filesystem-AoR (append-only
    discipline; no destructive edits). Modifications add entries;
    never remove them.

Authorized by `sanctum/2026-05-13-arc-e-civitas-civilian-classes.md`.
"""

from __future__ import annotations

import dataclasses
import hashlib
import pathlib
from datetime import date
from typing import Any, ClassVar


# Civic class enum — the orders of Polaris-as-Civitas.
CIVITAS_PLEBS         = "plebs"     # Plebeians — cross-legion readers
CIVITAS_EQUITES       = "eques"     # Equestrians — cross-legion couriers
CIVITAS_AUGURES       = "augur"     # Augurs — pattern interpreters
CIVITAS_CENSORES      = "censor"    # Censors — keepers of the roll
CIVITAS_QUAESTORES    = "quaestor"  # Quaestores — financial magistrates (Arc F / F1 / v8.68)
CIVITAS_TRIBUNI_PLEBIS = "tribuni_plebis"  # Tribuni Plebis — usability advocates (Arc G / G1 / v8.71)

VALID_CIVITAS_CLASSES = (
    CIVITAS_PLEBS, CIVITAS_EQUITES, CIVITAS_AUGURES, CIVITAS_CENSORES,
    CIVITAS_QUAESTORES, CIVITAS_TRIBUNI_PLEBIS,
)


@dataclasses.dataclass(frozen=True)
class CitizenFinding:
    """One deposit candidate returned by a citizen's observe().

    Structurally parallel to AntFinding but semantically different:
    a CitizenFinding is an observation ABOUT the swarm, not about
    a project artifact. The colony runner serializes both finding
    types to the same Pheromone table.
    """
    node_id: str
    intensity: float
    kind: str                       # one of 'drift','alert','info','curious'
    observation_type: str           # 'forum_imbalance', 'cross_legion_correlation',
                                    # 'convergent_attention', 'census_event',
                                    # 'proposal_new_ant', etc.
    evidence: dict[str, Any]
    half_life_hours: float = 24.0

    def __post_init__(self) -> None:
        if not (0.0 < self.intensity <= 10.0):
            raise ValueError(f"intensity must be in (0, 10]; got {self.intensity}")
        if self.kind not in ("drift", "alert", "info", "curious"):
            raise ValueError(f"invalid kind {self.kind!r}")
        if not self.observation_type:
            raise ValueError("observation_type must be non-empty")
        if not self.node_id:
            raise ValueError("node_id must be non-empty")


class Citizen:
    """Base class for all citizens under polaris_swarm/civitas/.

    Subclasses MUST declare:
      - NAME           — module name (e.g., 'plebs_forum_watcher')
      - CIVITAS_CLASS  — one of VALID_CIVITAS_CLASSES
      - DESCRIPTION    — one-line summary

    Subclasses MUST implement:
      - `observe(recent_pheromones)` — return list[CitizenFinding]

    Subclasses MUST NOT:
      - Subclass Ant (G12)
      - Directly create new Ant or Citizen instances at runtime (G13)
      - Call any LLM API (G8 extended to civitas)
      - Use unseeded randomness

    `recent_pheromones` is a list of dicts with the same shape as
    `polaris_swarm/base.Pheromone`. In `--dry` mode, the colony
    runner synthesizes this from the legion deployment's
    in-memory findings.
    """

    NAME:          ClassVar[str] = "citizen_base"
    CIVITAS_CLASS: ClassVar[str] = CIVITAS_PLEBS
    DESCRIPTION:   ClassVar[str] = "(base class; subclass me)"

    def __init__(self, root: pathlib.Path, seed: int | None = None):
        self.root = root
        if seed is None:
            blob = f"{self.NAME}:{date.today().isoformat()}".encode("utf-8")
            seed = int.from_bytes(hashlib.sha256(blob).digest()[:8], "big")
            # v8.89 fix: mask to 63 bits to stay within signed bigint range
            # (Pheromone.seed). See polaris_swarm/base.py for the rationale.
            seed &= (1 << 63) - 1
        self.seed = seed

    def observe(
        self, recent_pheromones: list[dict],
    ) -> list[CitizenFinding]:
        """Return civic findings derived from recent pheromones
        + project corpus. Subclasses MUST implement."""
        raise NotImplementedError

    # ------------------------------------------------------------------
    # Shared helpers (belong on the base per G6-adjacent — citizens
    # do not import each other).
    # ------------------------------------------------------------------

    def _read(self, *parts: str) -> str | None:
        path = self.root.joinpath(*parts)
        if not path.is_file():
            return None
        try:
            return path.read_text(errors="replace")
        except OSError:
            return None


def propose_new_ant(
    sketch: str,
    proposed_legion: str,
    triggering_observation: str,
    intensity: float = 3.0,
) -> CitizenFinding:
    """Helper for citizens that want to propose new ants.

    Returns a CitizenFinding with observation_type=proposal_new_ant
    that operators can later ratify by materializing as a real ant
    file. This is the Roman ratification pattern: nomination by
    the people, ratification by the Senate.

    G13: citizens MUST use this helper rather than spawning ants
    directly. The proposal pheromone is the autogenesis primitive.
    """
    return CitizenFinding(
        node_id=f"proposal:{proposed_legion}/{sketch[:40]}",
        intensity=intensity,
        kind="info",
        observation_type="proposal_new_ant",
        evidence={
            "sketch": sketch,
            "proposed_legion": proposed_legion,
            "triggering_observation": triggering_observation,
            "ratification_required": True,
            "ratification_by": "operator-or-censor",
        },
        half_life_hours=168.0,    # week-scale; proposals deserve time to review
    )
