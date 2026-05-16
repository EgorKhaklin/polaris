"""Mycelium base — Pheromone dataclass + Ant base class.

Every ant subclasses `Ant` and implements `scan() -> list[AntFinding]`.
The colony runner serializes findings to `Pheromone` rows. Ants do
NOT write to the database directly — they return structured findings
which the runner deposits, so the substrate boundary is enforced.

Reads use the same `Pheromone` table via `recent_pheromones()` which
returns rows decayed by `effective_intensity(intensity, age_hours,
half_life_hours)`.

Determinism contract:
  - Every Ant has a `seed` (defaulting to a hash of its module name +
    today's date). The seed is what's written into Pheromone.seed.
  - For replay: running the same ant twice with the same seed against
    the same source files MUST produce identical AntFinding outputs.
  - This means: no `time.time()` inside ant logic, no `random` without
    seeded `random.Random(seed)`, no environment-dependent reads
    beyond the project's own files.
"""

from __future__ import annotations

import dataclasses
import hashlib
import math
import pathlib
from datetime import date
from typing import Any, ClassVar


# Default decay half-life in hours. After this many hours, a pheromone's
# effective intensity halves. Ants can override per-deposit.
DECAY_HALF_LIFE_HOURS_DEFAULT: float = 24.0

# Pheromone kinds — closed enum matching the SQL CHECK constraint.
KIND_DRIFT = "drift"        # something has shifted away from documented state
KIND_ALERT = "alert"        # active issue requiring attention
KIND_INFO = "info"          # baseline observation, not concerning
KIND_CURIOUS = "curious"    # interesting pattern, not classified

VALID_KINDS = (KIND_DRIFT, KIND_ALERT, KIND_INFO, KIND_CURIOUS)


# Via Appia (Arc G / G1 / v8.71): the priority property.
# Pheromones marked priority=True are on the "via appia" — the
# Roman state highway. They get a 1.5× visibility multiplier in
# the bloom renderer, compounding with Cursus Honorum multipliers.
#
# G23 invariant: priority is a PROPERTY of pheromones, not a
# separate routing layer. There is no "Via Appia legion" or
# parallel pheromone table. Every pheromone has priority; most
# have it set to False. Ants opt IN by passing priority=True.
#
# Auto-priority rules (applied at __post_init__ time):
#   - kind == "alert" → priority True automatically
#   - intensity >= AUTO_PRIORITY_INTENSITY → priority True
# These rules ensure that constitutional emergencies (ALERTs) and
# high-signal observations always reach the operator's attention
# without requiring each ant to remember to set the flag.
AUTO_PRIORITY_INTENSITY = 7.0
VIA_APPIA_MULTIPLIER = 1.5


@dataclasses.dataclass(frozen=True)
class AntFinding:
    """One pheromone deposit candidate returned by an ant's scan.

    The colony runner serializes this into a Pheromone row. Frozen so
    ants cannot accidentally mutate findings before deposit.

    Via Appia (v8.71): `priority` flag marks high-importance
    findings for visibility boost in the bloom renderer.
    Defaults to False; auto-promoted to True for ALERT kinds
    and intensities ≥ AUTO_PRIORITY_INTENSITY.
    """
    node_id: str                # brain-map node id (e.g., 'route:/api/zk/verify')
    intensity: float            # 0 < intensity <= 10
    kind: str                   # one of VALID_KINDS
    evidence: dict[str, Any]    # structured payload
    half_life_hours: float = DECAY_HALF_LIFE_HOURS_DEFAULT
    priority: bool = False      # Via Appia (Arc G): high-importance routing

    def __post_init__(self) -> None:
        if not (0.0 < self.intensity <= 10.0):
            raise ValueError(f"intensity must be in (0, 10]; got {self.intensity}")
        if self.kind not in VALID_KINDS:
            raise ValueError(f"kind must be one of {VALID_KINDS}; got {self.kind!r}")
        if not (0.0 < self.half_life_hours <= 720.0):
            raise ValueError(
                f"half_life_hours must be in (0, 720]; got {self.half_life_hours}"
            )
        if not self.node_id:
            raise ValueError("node_id must be non-empty")
        # Via Appia auto-priority: ALERTs and high-intensity findings
        # land on the highway by default. The flag is frozen-dataclass-
        # safe via object.__setattr__.
        if not self.priority and (
            self.kind == KIND_ALERT
            or self.intensity >= AUTO_PRIORITY_INTENSITY
        ):
            object.__setattr__(self, "priority", True)


@dataclasses.dataclass
class Pheromone:
    """A deposited pheromone as returned by a database read.

    Distinct from AntFinding: this carries `deposited_at` and
    `deposited_by` populated from the database row.
    """
    pheromone_id: int
    deposited_at: Any           # datetime; typed as Any to avoid stdlib coupling
    deposited_by: str
    node_id: str
    intensity: float
    kind: str
    half_life_hours: float
    evidence: dict[str, Any]
    seed: int


class Ant:
    """Base class for all ants under polaris_swarm/ants/.

    Subclasses MUST:
      - Set class attribute `NAME` (used as Pheromone.deposited_by)
      - Implement `scan(self) -> list[AntFinding]`

    Subclasses MUST NOT:
      - Import any other ant module
      - Call any LLM API
      - Use unseeded randomness
      - Read external network resources
      - Write to the database (use the runner)
    """

    NAME: ClassVar[str] = "ant_base"
    DESCRIPTION: ClassVar[str] = "(base class; subclass me)"

    def __init__(self, root: pathlib.Path, seed: int | None = None):
        self.root = root
        # Default seed = deterministic hash of (ant name, today's date).
        # Each ant gets a stable per-day seed without using time-of-day.
        #
        # v8.89 fix: mask to 63 bits.
        # `int.from_bytes(...8 bytes..., 'big')` returns UNSIGNED 64-bit
        # (range [0, 2^64-1] ≈ 1.8e19), but PostgreSQL bigint is SIGNED
        # (range [-2^63, 2^63-1] ≈ ±9.2e18). About half of SHA-256 prefixes
        # exceed bigint's positive range and the INSERT into Pheromone.seed
        # raises NumericValueOutOfRange. Masking to 63 bits keeps the seed
        # always-positive AND always-in-range without losing
        # determinism — same input → same seed, both pre- and post-mask.
        # Surfaced by the v8.89 Architect+HYDRA macro scan when the
        # swarm-run produced 0 pheromones after the schema reload.
        if seed is None:
            blob = f"{self.NAME}:{date.today().isoformat()}".encode("utf-8")
            seed = int.from_bytes(hashlib.sha256(blob).digest()[:8], "big")
            seed &= (1 << 63) - 1
        self.seed = seed

    def scan(self) -> list[AntFinding]:
        """Return the findings this ant observed in its slice.

        Subclasses MUST implement. The runner will deposit each
        finding as one Pheromone row, with this ant's NAME and seed.
        """
        raise NotImplementedError

    # ------------------------------------------------------------------
    # Helpers — small read-only utilities ants can share without
    # importing each other. These belong to the base class deliberately
    # (per Arc E G6: no ant ↔ ant imports).
    # ------------------------------------------------------------------

    def _read(self, *parts: str) -> str | None:
        """Read a project file relative to repo root; None if missing."""
        path = self.root.joinpath(*parts)
        if not path.is_file():
            return None
        try:
            return path.read_text(errors="replace")
        except OSError:
            return None


def effective_intensity(
    raw_intensity: float, age_hours: float, half_life_hours: float
) -> float:
    """Deterministic exponential decay applied at read time.

    Returns the pheromone's current effective intensity given its
    raw deposit intensity and age. This is a pure function with no
    state; identical inputs ALWAYS produce identical outputs.
    """
    if age_hours < 0:
        age_hours = 0.0
    if half_life_hours <= 0:
        return 0.0
    return raw_intensity * math.exp(-math.log(2) * age_hours / half_life_hours)
