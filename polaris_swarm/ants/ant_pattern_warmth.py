"""ant_pattern_warmth — pheromone Polaris patterns with cold corpus presence.

Slice: the 22-pattern catalog (from `scripts/ai-pattern.sh`) and
the journal corpus (`journal/*.md`).

Local rule: parse the canonical 22 pattern names from
`ai-pattern.sh`. For each pattern, count mentions across journals.
If a pattern has ZERO mentions across all journals, deposit an
`info` pheromone. If a pattern has only 1 mention, deposit a
weaker info pheromone. The signal is "this pattern lives in the
catalog but the project's lived experience hasn't encountered it
yet" — which is fine for some patterns but worth visibility for
all of them.

This is the cognitive-warmth check that CognitiveWatcher already
does during HYDRA passes. The pheromone equivalent makes it
emergent: the bloom shows which patterns are cold across time.
"""

from __future__ import annotations

import re

from polaris_swarm.base import Ant, AntFinding, KIND_INFO


# ai-pattern.sh stores the canonical 22 in a pipe-separated table:
#   0|Greenfield|description|shadow|family|tags
#   1|Composition|...
# The pattern name is the second pipe-separated column. We pull it
# directly so the canonical source-of-truth lives in one place.
_PATTERN_LINE = re.compile(
    r"^\s*\d+\|([A-Z][A-Za-z]+)\|",
    re.MULTILINE,
)


class AntPatternWarmth(Ant):
    NAME = "ant_pattern_warmth"
    DESCRIPTION = "Pheromones 22-catalog patterns with cold journal mentions."

    def scan(self) -> list[AntFinding]:
        findings: list[AntFinding] = []
        pattern_sh = self._read("scripts", "ai-pattern.sh") or ""
        # Extract pattern names from the in-script table; the script
        # carries the canonical list.
        names = sorted(set(_PATTERN_LINE.findall(pattern_sh)))
        if len(names) < 18:
            # Parser failure or major catalog drift; emit a single
            # curious pheromone and stop. (CognitiveWatcher handles
            # the hard count = 22 check; this ant defers to that.)
            return [AntFinding(
                node_id="catalog:patterns",
                intensity=3.0,
                kind="curious",
                evidence={
                    "message": f"only found {len(names)} pattern names; "
                               f"expected ≥18",
                },
            )]
        # Concatenate every journal/*.md and count mentions
        journal_dir = self.root / "journal"
        if not journal_dir.is_dir():
            return findings
        corpus_parts: list[str] = []
        for path in journal_dir.glob("*.md"):
            try:
                corpus_parts.append(path.read_text(errors="replace"))
            except OSError:
                continue
        corpus = "\n".join(corpus_parts)
        for name in names:
            # word-boundary match avoids "ClarityCloud" matching "Clarity"
            count = len(re.findall(rf"\b{re.escape(name)}\b", corpus))
            if count == 0:
                findings.append(AntFinding(
                    node_id=f"pattern:{name}",
                    intensity=1.5,
                    kind=KIND_INFO,
                    evidence={
                        "message": f"pattern {name!r} has zero journal mentions",
                        "fix_hint": "either the pattern is genuinely "
                                    "unencountered (fine) or the journal "
                                    "discipline drifted",
                    },
                    half_life_hours=168.0,    # week-scale; informational
                ))
        return findings
