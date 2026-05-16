"""Soldier base — the lightweight, disposable second tier of the
Mycelium swarm (v9.03, Sanctum 2026-05-14-hybrid-swarm-mirai-pattern).

Where commanders (`polaris_swarm/base.py:Ant`) are sophisticated,
identity-bearing, individually-traceable agents that emit
multi-attribute Findings, soldiers are the opposite:

  - Lightweight: one Soldier subclass = one fact-checking primitive
  - Disposable: a soldier crash returns no Observations; the colony
    continues with the rest. There is no "this soldier is critical."
  - Stateless: each .observe() run is fresh; no carry-over between
    runs. Replay-safe via the same seed protocol as commanders.
  - F5-EXEMPT: soldiers do NOT accrue Denarii (see Arc F / F5 +
    Sanctum 2026-05-14-treasury-rebalance.md). The reward function
    is for identity-bearing commanders who carry insight; soldiers
    are disposable and replaceable. Treasury, Cursus Honorum,
    STEADY_STATE_ANTS — none apply to soldiers.

Constitutional preservation (Sanctum §II Position A):

  - C1 (audit-of-record append-only): preserved — soldier
    Observations get aggregated into single Pheromone INSERTs by
    the SoldierColony; Pheromone trigger still rejects UPDATE/DELETE
  - C10 (system identity is value-pure): preserved — soldiers
    observe only system-state metrics; no holder PII path
  - G1 (deterministic): preserved — each .observe() is a pure
    function of observable state + the soldier's seed
  - G3 (read-only / graceful-failure): preserved — soldiers never
    write to anything except Pheromone (via colony) and graceful-
    failure on individual crash
  - G6 (no inter-ant imports): preserved — soldiers don't import
    each other or commanders

External-source synthesis:

  - Mirai (jgamblin/mirai-source-code): tier-separation by
    responsibility; per-bot < 100KB footprint; bot disposability
    via auto-replacement on next scan cycle.
  - MiroFish (666ghj/MiroFish): specialized agents producing
    independent observations; the synthesizer (here: SoldierColony
    aggregator + commanders + HYDRA + CM) ties everything together.
  - BettaFish (666ghj/BettaFish): capability-based distribution +
    aggregation layer for synthesis; resilience through redundancy.

============================================================================
"""

from __future__ import annotations

import dataclasses
import hashlib
import pathlib
from datetime import date
from typing import Any, ClassVar

from polaris_swarm.base import (
    KIND_INFO,
    KIND_DRIFT,
    KIND_ALERT,
    KIND_CURIOUS,
    VALID_KINDS,
)


# Soldiers use a much lower intensity range than commanders (3.0-7.0).
# Background noise vs commander peaks: the bloom heatmap stays legible.
SOLDIER_INTENSITY_MIN: float = 0.5
SOLDIER_INTENSITY_MAX: float = 2.0

# Short half-life — soldiers report frequently; their pheromones decay
# fast so the bloom heatmap reflects RECENT state. Commanders default
# to 24h; soldiers default to 1h.
SOLDIER_HALF_LIFE_HOURS_DEFAULT: float = 1.0


@dataclasses.dataclass(frozen=True)
class Observation:
    """One single-fact reading from a soldier.

    An Observation is to a Soldier what an AntFinding is to an Ant —
    but Observations are intentionally simpler:

      - One node_id, one value, one kind
      - No `evidence` dict; just `value` (which may be a number, str,
        dict, or None)
      - No `priority` flag; soldier deposits never go on the Via Appia
        (priority routing is a commander-tier signal)
      - No `half_life_hours` override; the soldier class sets it
      - No multi-step composition; one observation per fact

    The SoldierColony aggregates Observations across cycles and across
    soldiers-of-the-same-class into a single Pheromone deposit per
    (soldier_class, node_id) pair, with the raw observations preserved
    in `evidence.observations[]`.

    Frozen so soldiers cannot accidentally mutate observations
    after returning them.
    """
    node_id: str
    value: Any                  # number | str | dict | None
    kind: str = KIND_INFO

    def __post_init__(self) -> None:
        if not self.node_id:
            raise ValueError("Observation.node_id must be non-empty")
        if self.kind not in VALID_KINDS:
            raise ValueError(
                f"Observation.kind must be in {VALID_KINDS}; got {self.kind!r}"
            )


class Soldier:
    """Base class for lightweight soldier ants under polaris_swarm/soldiers/.

    Subclasses MUST:
      - Set class attribute `NAME` (used as Pheromone.deposited_by;
        canonical prefix: "soldier_<purpose>")
      - Set class attribute `DESCRIPTION` (one-line operator-readable)
      - Set class attribute `INTENSITY` in [0.5, 2.0]
      - Set class attribute `NODE_PREFIX` (e.g., "infra:routes")
      - Implement `observe(self) -> list[Observation]`

    Subclasses MUST NOT:
      - Import any other soldier or commander module (G6)
      - Call any LLM API
      - Use unseeded randomness (replay-safety)
      - Read external network resources EXCEPT for explicitly-named
        local same-host endpoints (e.g., http://localhost:$POLARIS_PORT)
      - Write to the database (the SoldierColony aggregator handles
        deposits)
      - Carry holder PII or token data (C10)
      - Persist state between .observe() calls (statelessness invariant)
      - Inherit from polaris_swarm.base.Ant (the two tiers are
        deliberately separate; no diamond inheritance, no
        accidental commander-vs-soldier conflation)

    Subclass discovery: SoldierColony's auto-loader iterates
    polaris_swarm/soldiers/*.py and instantiates every subclass of
    Soldier whose NAME matches "soldier_*".
    """

    NAME: ClassVar[str] = "soldier_base"
    DESCRIPTION: ClassVar[str] = "(base class; subclass me)"
    INTENSITY: ClassVar[float] = 1.0
    NODE_PREFIX: ClassVar[str] = "infra:base"
    HALF_LIFE_HOURS: ClassVar[float] = SOLDIER_HALF_LIFE_HOURS_DEFAULT

    def __init_subclass__(cls, **kwargs: Any) -> None:
        """Validate class-level attributes at subclass-definition time
        so misconfigured soldiers fail loud at import, not at runtime."""
        super().__init_subclass__(**kwargs)
        # Allow abstract intermediate subclasses by skipping validation
        # when the subclass kept the base NAME.
        if cls.NAME == "soldier_base":
            return
        if not cls.NAME.startswith("soldier_"):
            raise TypeError(
                f"{cls.__name__}.NAME must start with 'soldier_'; "
                f"got {cls.NAME!r}"
            )
        if not (SOLDIER_INTENSITY_MIN <= cls.INTENSITY <= SOLDIER_INTENSITY_MAX):
            raise TypeError(
                f"{cls.__name__}.INTENSITY must be in "
                f"[{SOLDIER_INTENSITY_MIN}, {SOLDIER_INTENSITY_MAX}]; "
                f"got {cls.INTENSITY}. Soldiers use the low band; "
                f"commanders use the [3.0, 7.0] band."
            )
        if not cls.NODE_PREFIX or ":" not in cls.NODE_PREFIX:
            raise TypeError(
                f"{cls.__name__}.NODE_PREFIX must be a non-empty "
                f"colon-namespaced string (e.g., 'infra:routes'); "
                f"got {cls.NODE_PREFIX!r}"
            )

    def __init__(
        self,
        root: pathlib.Path,
        seed: int | None = None,
    ) -> None:
        self.root = root
        if seed is None:
            blob = f"{self.NAME}:{date.today().isoformat()}".encode("utf-8")
            seed = int.from_bytes(hashlib.sha256(blob).digest()[:8], "big")
            seed &= (1 << 63) - 1   # match v8.89 commander bigint-safety fix
        self.seed = seed

    def observe(self) -> list[Observation]:
        """Return zero or more single-fact Observations.

        MUST be a pure function of observable state + self.seed.
        MUST graceful-fail (catch exceptions; return [] on error).
        SoldierColony invokes this on every cycle within the run window.

        Subclasses MUST implement.
        """
        raise NotImplementedError

    # Helpers — same shape as Ant._read for consistency.
    def _read(self, *parts: str) -> str | None:
        """Read a project file relative to repo root; None if missing."""
        path = self.root.joinpath(*parts)
        if not path.is_file():
            return None
        try:
            return path.read_text(errors="replace")
        except OSError:
            return None


# Re-export the kind constants for convenience — soldiers usually
# emit KIND_INFO; some emit KIND_DRIFT (e.g., stale-mtime); rare
# KIND_ALERT (e.g., process gone). Soldiers should NOT emit
# KIND_CURIOUS — that's a commander-tier classification reserved
# for findings that need human judgment.
__all__ = [
    "Soldier",
    "Observation",
    "SOLDIER_INTENSITY_MIN",
    "SOLDIER_INTENSITY_MAX",
    "SOLDIER_HALF_LIFE_HOURS_DEFAULT",
    "KIND_INFO",
    "KIND_DRIFT",
    "KIND_ALERT",
]
