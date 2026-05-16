"""Mycelium legions — Roman cohort organization for Phase E6.

A **Legion** is the unit of swarm organization. Each Legion has:

  - A **Legatus** (general), conceptually one of HYDRA's 7 watcher
    domains: schema, cognitive, security, mission, adversary,
    performance, trajectory.
  - A **cohort of ants** (1+ legionnaires) under its banner.
  - A **default tactic** declaring how the cohort deploys.

The colony runner iterates `ALL_LEGIONS`, deploys each via its tactic,
and deposits findings to the Pheromone log. The deposit's
`deposited_by` field is still the *ant* name (AoR preservation);
the legion identity travels in the evidence JSONB.

Contract (Arc E G10 + G11):

  - **G10** — every ant belongs to exactly one Legion. No orphans,
    no double-counting.
  - **G11** — ants do NOT import from `polaris_swarm.legions`. The
    knowledge flow is one-way: Legion knows its ants; ants do not
    know their Legion. This is the reverse-direction of G6 and is
    necessary so a Legion-level refactor never touches ant code.

Authorized by `sanctum/2026-05-13-arc-e-legion-structure-with-tactics.md`.

The five tactics correspond to genuine Roman military doctrines.
Their software meanings are documented in each `_deploy_*` function.
"""

from __future__ import annotations

import dataclasses
import enum
import pathlib
from typing import Callable, ClassVar

from polaris_swarm.base import Ant, AntFinding


class Tactic(enum.Enum):
    """The five tactical doctrines a Legatus may choose."""
    TESTUDO       = "testudo"        # all ants run; output aggregated
    TRIPLEX_ACIES = "triplex_acies"  # tiered escalation
    CUNEUS        = "cuneus"         # lead + followers cascade
    VEXILLATIO    = "vexillatio"     # operator-directed focused detachment
    AUXILIA       = "auxilia"        # cross-legion ally borrowing


@dataclasses.dataclass
class TacticConfig:
    """Per-legion tactic parameterization. Most fields are None
    unless the legion has chosen a tactic that requires them."""
    tactic: Tactic

    # For TRIPLEX_ACIES: ordered list of tiers; each tier is a list
    # of Ant classes from this legion's cohort. Empty tiers are
    # allowed (legion may grow them later).
    tiers: list[list[type[Ant]]] | None = None

    # For CUNEUS: the lead ant. Must be a member of this legion's ANTS.
    lead: type[Ant] | None = None

    # For VEXILLATIO: a predicate (AntFinding) → bool that selects
    # which findings the cohort emits. Defaults to "all" if None.
    focus_predicate: Callable[[AntFinding], bool] | None = None

    # For AUXILIA: names of other legions whose ants may be borrowed.
    auxilia_pool: list[str] | None = None

    def validate(self, cohort: list[type[Ant]]) -> None:
        """Raise ValueError if the config is inconsistent with the cohort."""
        if self.tactic == Tactic.TRIPLEX_ACIES:
            if not self.tiers or len(self.tiers) < 2:
                raise ValueError(
                    f"TRIPLEX_ACIES requires >=2 tiers; got {self.tiers!r}"
                )
            flat = [a for tier in self.tiers for a in tier]
            if set(flat) != set(cohort):
                raise ValueError(
                    "TRIPLEX_ACIES tiers must partition the cohort"
                )
        if self.tactic == Tactic.CUNEUS:
            if self.lead is None or self.lead not in cohort:
                raise ValueError(
                    "CUNEUS requires a lead ant that is in the cohort"
                )


class Legion:
    """Base class for all Legions under polaris_swarm/legions/.

    Subclasses MUST declare:
      - NAME       — module name (e.g., "legio_schema")
      - DOMAIN     — HYDRA watcher domain (e.g., "schema")
      - LEGATUS    — display name (e.g., "Legatus Schema")
      - ANTS       — list of Ant subclasses commanded
      - TACTIC     — TacticConfig declaring default doctrine

    Subclasses MUST NOT:
      - Override `deploy()` unless adding new tactics (extend Tactic enum first)
      - Import any other Legion module (per G11-adjacent: legions are siblings)
      - Call any LLM API (G8 extends to legions)
    """

    NAME:    ClassVar[str] = "legio_base"
    DOMAIN:  ClassVar[str] = "(none)"
    LEGATUS: ClassVar[str] = "(unnamed)"
    ANTS:    ClassVar[list[type[Ant]]] = []
    TACTIC:  ClassVar[TacticConfig] = TacticConfig(tactic=Tactic.TESTUDO)

    def __init__(self, root: pathlib.Path):
        self.root = root
        # Validate the legion's tactic against its cohort at construction
        # time. Catches misconfiguration before the colony runs.
        self.TACTIC.validate(self.ANTS)

    def deploy(self, **kwargs) -> list[tuple[type[Ant], list[AntFinding]]]:
        """Dispatch to the tactic-specific deployer. Returns list of
        (AntClass, findings) tuples so the colony runner preserves
        deposited_by = ant.NAME for AoR."""
        return _DISPATCHERS[self.TACTIC.tactic](self, **kwargs)


# --------------------------------------------------------------------------
# Tactic implementations. Each takes a Legion instance and returns a list
# of (AntClass, list-of-findings) pairs. The colony runner serializes
# the findings into Pheromone rows.
# --------------------------------------------------------------------------

def _deploy_testudo(legion: Legion, **_kwargs) -> list[tuple[type[Ant], list[AntFinding]]]:
    """TESTUDO — every ant in the cohort scans. Output is the union
    of all findings, returned per-ant so each ant's deposit retains
    its own deposited_by name.

    Roman context: every shield raised, cohort moves as one. The
    formation is maximally defensive — no domain blind spots — but
    also maximally communicative: every ant always speaks. Use when
    coverage matters more than economy.
    """
    return [(AntCls, AntCls(legion.root).scan()) for AntCls in legion.ANTS]


def _deploy_triplex_acies(legion: Legion, **_kwargs) -> list[tuple[type[Ant], list[AntFinding]]]:
    """TRIPLEX ACIES — three battle lines deployed in sequence.

    Tier 1 (hastati) ants run first. If any fire, Tier 2 (principes)
    is deployed against the same surface. If any of those fire, Tier 3
    (triarii) is deployed. Stops at the first silent tier.

    Roman context: hastati are young aggressive front-line; principes
    are veterans; triarii are elite reserves committed only at crisis.
    In software: cheap-fast checks first, escalating to expensive
    deep checks only when warranted. Use when checks form a natural
    cost gradient.
    """
    if not legion.TACTIC.tiers:
        return []
    results: list[tuple[type[Ant], list[AntFinding]]] = []
    for tier in legion.TACTIC.tiers:
        tier_any_fired = False
        for AntCls in tier:
            findings = AntCls(legion.root).scan()
            results.append((AntCls, findings))
            if findings:
                tier_any_fired = True
        if not tier_any_fired:
            break  # silent tier; no escalation
    return results


def _deploy_cuneus(legion: Legion, **_kwargs) -> list[tuple[type[Ant], list[AntFinding]]]:
    """CUNEUS — wedge formation: the lead pierces; followers exploit.

    The designated lead ant scans first. If it is silent, the
    cohort does not deploy further (the gap was not found). If
    the lead fires, every other ant in the cohort scans.

    Roman context: a veteran centurion at the point of the wedge
    drives into the enemy line; the rest of the formation pours
    through the breach. In software: one strong signal triggers
    a fuller investigation. Use when one ant reliably detects
    the presence of trouble and others detail it.
    """
    lead = legion.TACTIC.lead
    if lead is None:
        return _deploy_testudo(legion)
    lead_findings = lead(legion.root).scan()
    results: list[tuple[type[Ant], list[AntFinding]]] = [(lead, lead_findings)]
    if not lead_findings:
        return results
    for AntCls in legion.ANTS:
        if AntCls is lead:
            continue
        results.append((AntCls, AntCls(legion.root).scan()))
    return results


def _deploy_vexillatio(legion: Legion, focus_predicate=None, **_kwargs) -> list[tuple[type[Ant], list[AntFinding]]]:
    """VEXILLATIO — operator-directed detachment for a focused mission.

    All ants scan, but the cohort emits only findings matching the
    focus predicate (defaults to the legion's TACTIC.focus_predicate
    if the caller didn't supply one).

    Roman context: a Roman general could send a vexillatio (literally,
    a unit carrying a vexillum standard) on a focused mission outside
    the legion's usual scope. In software: operators invoke the
    legion with a narrow `--focus` argument; the cohort scans
    normally but emits only what matches. Use for deep-dive
    investigations without standing up a new colony pass.
    """
    pred = focus_predicate or legion.TACTIC.focus_predicate
    results: list[tuple[type[Ant], list[AntFinding]]] = []
    for AntCls in legion.ANTS:
        findings = AntCls(legion.root).scan()
        if pred is not None:
            findings = [f for f in findings if pred(f)]
        results.append((AntCls, findings))
    return results


def _deploy_auxilia(legion: Legion, ally_legions: list["Legion"] | None = None, **_kwargs) -> list[tuple[type[Ant], list[AntFinding]]]:
    """AUXILIA — borrow legionnaires from allied legions.

    Runs this legion's own cohort plus the ants of any supplied
    ally legions. The borrowed ants still get credited via
    deposited_by = ant.NAME, but the evidence JSONB will record
    the host legion that called them (`host_legio`).

    Roman context: auxilia troops were allied soldiers who fought
    alongside legions on specific campaigns. In software:
    cross-domain investigations where one legion needs another's
    expertise without permanent restructuring. Use sparingly —
    overuse re-centralizes the swarm.
    """
    results: list[tuple[type[Ant], list[AntFinding]]] = []
    for AntCls in legion.ANTS:
        results.append((AntCls, AntCls(legion.root).scan()))
    if ally_legions:
        allowed = set(legion.TACTIC.auxilia_pool or [])
        for ally in ally_legions:
            if ally.NAME not in allowed:
                continue  # honor declared pool
            for AntCls in ally.ANTS:
                results.append((AntCls, AntCls(legion.root).scan()))
    return results


_DISPATCHERS: dict[Tactic, Callable[..., list[tuple[type[Ant], list[AntFinding]]]]] = {
    Tactic.TESTUDO:       _deploy_testudo,
    Tactic.TRIPLEX_ACIES: _deploy_triplex_acies,
    Tactic.CUNEUS:        _deploy_cuneus,
    Tactic.VEXILLATIO:    _deploy_vexillatio,
    Tactic.AUXILIA:       _deploy_auxilia,
}
