"""AugurBloomReader — interpreter of signs + proposal-emitter (F3).

The Augures (Augurs) were Roman priests who read auspices — the
flight of birds, the entrails of sacrifices, the patterns of
lightning. They didn't make decisions; they INTERPRETED what the
gods were saying, and the Senate decided what to do about it.

In the swarm, the Augur reads the Forum's collective pheromone
pattern. Where individual ants see their own slice, the Augur
sees the WHOLE — and surfaces emergent shapes that no single
ant or legion could.

The canonical signal: **convergent attention.** When ≥ N distinct
ants (across legions) all fire on the same brain-map node within
the same window, that node has the swarm's attention. The Augur
deposits an "augur_convergent_attention" finding so the operator
can ratchet up scrutiny on that node.

**F3 extension (v8.70).** The Augur is also the swarm's
**proposal-emitter**. When the Augur observes a project-state
category for which ZERO ants are reading (the
node-id-namespace is uncovered), it emits a
`proposal_new_ant` pheromone naming the gap. Operators
ratify by materializing the proposal as a real ant file
(G13 proposal-driven autogenesis).

This is the *non-larping* form of F3: the proposal is real
(a genuine coverage gap), not synthetic. The first ratified
proposal (`ant_proposal_stagnation`) lands in legio_trajectory
in v8.70.

The Augur never decides. The Augur only reads and reports. The
Senate (Sanctum) decides; the operator acts.
"""

from __future__ import annotations

from collections import defaultdict

from polaris_swarm.civitas.base import (
    Citizen, CitizenFinding, CIVITAS_AUGURES, propose_new_ant,
)


# Minimum distinct ants firing on one node to constitute convergence.
# v8.67 (R2 from the 100-year-architect Sanctum): lowered 3 → 2.
# At current cohort size (18 ants), threshold=3 is structurally
# unreachable — the 100-year simulation showed maximum active ants
# per node = 1-2. Lowered to 2 so convergence becomes detectable
# at the actual swarm scale. The Architect's reasoning preserved
# in `sanctum/2026-05-13-civitas-100-year-architect-report.md`.
CONVERGENCE_THRESHOLD = 2


# Project-state namespaces the Augur watches for ant coverage.
# Each entry: (directory_relative_to_root, node_id_prefix_expected).
# If the directory contains ≥ MIN_FILES_FOR_PROPOSAL files AND no
# ant has ever deposited on a node carrying the expected prefix,
# the Augur emits a proposal_new_ant pheromone.
WATCHED_NAMESPACES = (
    # (dir,         expected_node_prefix,  proposed_legion,    sketch)
    ("proposals",   "file:proposals/",     "legio_trajectory",
     "ant_proposal_stagnation: surface proposals/*.md files "
     "untouched ≥30d and not referenced in ROADMAP.md"),
)
MIN_FILES_FOR_PROPOSAL = 3


class AugurBloomReader(Citizen):
    NAME          = "augur_bloom_reader"
    CIVITAS_CLASS = CIVITAS_AUGURES
    DESCRIPTION   = "Augur reading the auspices: surfaces convergent attention + emits proposal_new_ant for uncovered namespaces."

    def observe(self, recent_pheromones: list[dict]) -> list[CitizenFinding]:
        findings: list[CitizenFinding] = []
        if recent_pheromones:
            findings.extend(self._observe_convergent_attention(recent_pheromones))
        # Proposal-emission runs even when the forum is silent —
        # uncovered namespaces are visible from the filesystem.
        findings.extend(self._observe_uncovered_namespaces(recent_pheromones))
        return findings

    def _observe_convergent_attention(
        self, recent_pheromones: list[dict],
    ) -> list[CitizenFinding]:
        findings: list[CitizenFinding] = []
        # Group: for each brain-map node, which distinct ants fired?
        node_to_ants: dict[str, set[str]] = defaultdict(set)
        node_to_intensity: dict[str, float] = defaultdict(float)
        for ph in recent_pheromones:
            node = ph.get("node_id", "")
            ant = ph.get("deposited_by", "")
            if not node or not ant:
                continue
            # Skip civitas-class deposits — Augur reads the underlying
            # legion signal, not other citizens' interpretations.
            ev = ph.get("evidence") or {}
            if ev.get("civitas_class"):
                continue
            node_to_ants[node].add(ant)
            try:
                node_to_intensity[node] += float(ph.get("intensity", 0))
            except (TypeError, ValueError):
                continue

        # Find nodes with ≥ CONVERGENCE_THRESHOLD distinct ants
        for node, ant_set in node_to_ants.items():
            if len(ant_set) < CONVERGENCE_THRESHOLD:
                continue
            findings.append(CitizenFinding(
                node_id=node,
                intensity=min(8.0, 3.0 + len(ant_set) * 0.8),
                kind="info",
                observation_type="augur_convergent_attention",
                evidence={
                    "message": (
                        f"Augur observation: {len(ant_set)} distinct ants "
                        f"firing on {node} — convergent attention; the "
                        f"swarm wants something looked at here"
                    ),
                    "distinct_ants": sorted(ant_set),
                    "ant_count": len(ant_set),
                    "summed_raw_intensity": round(node_to_intensity[node], 2),
                },
                half_life_hours=48.0,    # 2-day fade — augur reads persist
            ))
        return findings

    def _observe_uncovered_namespaces(
        self, recent_pheromones: list[dict],
    ) -> list[CitizenFinding]:
        """F3 — emit proposal_new_ant for namespaces with no ant coverage.

        For each WATCHED_NAMESPACES entry: count files in the dir;
        check whether ANY pheromone in `recent_pheromones` carries
        a node_id starting with the expected prefix; if none, emit
        a proposal.

        This is conservative — it only fires when (a) the directory
        has ≥ MIN_FILES_FOR_PROPOSAL files (so it's worth observing)
        AND (b) zero coverage exists. Both conditions must hold; the
        proposal is real, not theatrical.

        G13: emits via `propose_new_ant()` helper; never spawns an
        ant directly.
        """
        findings: list[CitizenFinding] = []
        # Build the set of currently-covered prefixes
        covered_prefixes: set[str] = set()
        for ph in recent_pheromones:
            node = ph.get("node_id", "")
            if not node:
                continue
            covered_prefixes.add(node)

        for dir_name, prefix, legion, sketch in WATCHED_NAMESPACES:
            base = self.root / dir_name
            if not base.is_dir():
                continue
            # Count substantive files (.md only)
            files = [p for p in base.glob("*.md") if p.is_file()]
            if len(files) < MIN_FILES_FOR_PROPOSAL:
                continue
            # Already covered?
            is_covered = any(n.startswith(prefix) for n in covered_prefixes)
            if is_covered:
                continue
            # Uncovered + substantive — emit proposal
            findings.append(propose_new_ant(
                sketch=sketch,
                proposed_legion=legion,
                triggering_observation=(
                    f"{dir_name}/ has {len(files)} files but zero "
                    f"ant coverage; node-id prefix {prefix!r} unobserved"
                ),
                intensity=4.0,
            ))
        return findings
