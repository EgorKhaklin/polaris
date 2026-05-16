"""ant_docs_structure — verify docs/ post-v8.60 subdivision intact.

Slice: filesystem under `docs/`.

Local rule: after v8.60's deep reorganization, docs/ must contain
the three subdivision directories (story / reference / operator),
the paper directory, the index README, and the two operator-
facing tables (SEED_DATA, BACKLOG). If any are missing, deposit
an `alert` pheromone on the docs node.

This is the hastati (T1) for Legio Docs — cheap, fast, just
checks filesystem existence. If this ant fires, principes and
triarii escalate to look at content drift.
"""

from __future__ import annotations

from polaris_swarm.base import Ant, AntFinding, KIND_ALERT


# Required entries under docs/ post-v8.60.
REQUIRED_PATHS = (
    ("docs", "README.md"),
    ("docs", "SEED_DATA.md"),
    ("docs", "BACKLOG.md"),
    ("docs", "story"),                          # dir
    ("docs", "story", "STORY.md"),
    ("docs", "story", "PRINCIPLES.md"),
    ("docs", "reference"),                      # dir
    ("docs", "reference", "API.md"),
    ("docs", "reference", "DATA-MODEL.md"),
    ("docs", "reference", "GLOSSARY.md"),
    ("docs", "reference", "SCALING.md"),
    ("docs", "reference", "SYSTEM-MAP.md"),
    ("docs", "operator"),                       # dir
    ("docs", "operator", "INSTALL.md"),
    ("docs", "operator", "DEPLOYMENT.md"),
    ("docs", "operator", "OPERATIONS.md"),
    ("docs", "operator", "SECURITY.md"),
    ("docs", "operator", "PRIVACY.md"),
    ("docs", "paper"),                          # dir
    ("docs", "paper", "polaris_project_report.pdf"),
    ("docs", "paper", "polaris_project_report.tex"),
)


class AntDocsStructure(Ant):
    NAME = "ant_docs_structure"
    DESCRIPTION = "Pheromones docs/ structure missing post-v8.60 paths."

    def scan(self) -> list[AntFinding]:
        findings: list[AntFinding] = []
        for parts in REQUIRED_PATHS:
            path = self.root.joinpath(*parts)
            if not path.exists():
                findings.append(AntFinding(
                    node_id="file:docs/",
                    intensity=7.0,
                    kind=KIND_ALERT,
                    evidence={
                        "message": (
                            f"docs/ structure broken: {'/'.join(parts)} "
                            f"is missing"
                        ),
                        "rule": "v8.60 docs subdivision (story/reference/operator/paper)",
                    },
                ))
        return findings
