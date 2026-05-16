"""AdversaryWatcher — H6 of Arc D.

Runs the game-theoretic adversary walk for each of C1–C10 via
`scripts/ai-adversary.sh` and surfaces:

  - The defender's claim (what the constraint asserts)
  - The attacker's optimal response (the primary threat)
  - The second-best attack (the threat to plan against AFTER the
    primary defense holds — the load-bearing prediction)

Alerts if any walk fails to produce the expected six-section
structure. The watcher is the recurring sentry for game-theoretic
equilibrium weakening: if a constraint's "second-best attack" shifts,
something material changed about Polaris's threat model.

Like the other watchers, this is read-only: it invokes ai-adversary.sh
as a subprocess and parses stdout. The ai-adversary.sh script itself
does not modify state.
"""

from __future__ import annotations

import pathlib
import re
import subprocess
from typing import Any

from .base import Finding, Watcher, WatcherReport


# All ten hard constraints. Pinned because adding C11+ requires a
# Sanctum-class amendment to the constraint-lattice (per MISSION
# §"Constraint lattice"), and the watcher should fail loudly if the
# lattice is amended without this constant catching up.
EXPECTED_CONSTRAINTS = [f"C{i}" for i in range(1, 11)]

# The six sections ai-adversary.sh emits per walk. The watcher only
# extracts the highest-signal three (Defender's claim, attacker's
# response, second-best attack) but verifies all six headers are
# present as a "did the walk complete" check.
EXPECTED_WALK_SECTIONS = (
    "Defender's claim",
    "Attacker's optimal response",
    "Equilibrium the defender is reaching for",
    "Second-best attack",
    "Defender's cost",
    "Mechanism-design note",
)

# Per-walk timeout. 10 × 5s = ~50s worst case if every walk timed
# out; in practice each walk is <100ms because ai-adversary.sh just
# emits canned text.
WALK_TIMEOUT_SECS = 5


class AdversaryWatcher(Watcher):
    name = "adversary"
    domain = "game-theoretic equilibrium walks across C1–C10"

    def _observe(self) -> WatcherReport:
        repo_root = self._repo_root()
        findings: list[Finding] = []
        evidence: dict[str, Any] = {
            "constraints_checked": 0,
            "constraints_clean": 0,
            "constraints_broken": [],
            "second_best_attacks": {},
        }

        script = repo_root / "scripts" / "ai-adversary.sh"
        if not script.is_file():
            findings.append(Finding(
                severity="alert",
                title="scripts/ai-adversary.sh missing",
                detail=("The adversary-walk script is not present. The "
                        "game-theoretic threat model cannot be surfaced "
                        "automatically. Inspect scripts/."),
                evidence={"path": str(script)},
            ))
            return WatcherReport(
                watcher_name=self.name, domain=self.domain,
                status="alert", findings=findings,
                evidence_summary=evidence,
            )

        broken: list[dict[str, Any]] = []
        per_constraint: dict[str, dict[str, str]] = {}

        for c in EXPECTED_CONSTRAINTS:
            evidence["constraints_checked"] += 1
            walk = self._run_walk(script, repo_root, c)
            if walk is None:
                broken.append({"constraint": c, "reason": "walk did not run"})
                continue
            sections = self._parse_walk(walk)
            # Section header matching is substring-based: ai-adversary's
            # actual headers sometimes have parenthetical qualifiers
            # (e.g. "Second-best attack (if equilibrium holds)"). The
            # watcher matches the canonical prefix.
            missing = [
                expected for expected in EXPECTED_WALK_SECTIONS
                if not any(expected in actual for actual in sections.keys())
            ]
            if missing:
                broken.append({
                    "constraint": c,
                    "reason": "missing walk sections",
                    "missing": missing,
                })
                continue
            per_constraint[c] = sections
            evidence["constraints_clean"] += 1
            # Pull the second-best attack text (substring-keyed).
            second_best = next(
                (v for k, v in sections.items()
                 if "Second-best attack" in k),
                "",
            )
            evidence["second_best_attacks"][c] = second_best[:200]

        evidence["constraints_broken"] = broken

        if broken:
            findings.append(Finding(
                severity="alert",
                title=f"{len(broken)} adversary walk(s) malformed",
                detail=("One or more game-theoretic walks did not produce "
                        "the expected six-section structure. The "
                        "ai-adversary.sh output format may have drifted "
                        "or a constraint's case branch is missing. "
                        "Inspect scripts/ai-adversary.sh."),
                evidence={"broken": broken[:5]},
            ))

        # Beyond completeness, surface one synthesis finding per
        # constraint family. We don't emit 10 separate Findings — that
        # would clutter HYDRA's brief — but we do put the per-constraint
        # second-best attacks in evidence_summary so HYDRA can cite them.
        # The headline-level Finding here is "the equilibria are
        # documented + readable."
        if evidence["constraints_clean"] == len(EXPECTED_CONSTRAINTS):
            findings.append(Finding(
                severity="info",
                title=f"all {len(EXPECTED_CONSTRAINTS)} adversary walks complete",
                detail=("Each of C1–C10 produces a six-section walk: "
                        "Defender's claim → Attacker's optimal response "
                        "→ Equilibrium → Second-best attack → Defender's "
                        "cost → Mechanism-design note. The threat model "
                        "is surveyable from the cognitive layer."),
                evidence={"second_best_summary": evidence["second_best_attacks"]},
            ))

        # Status aggregate. Because walks are mostly deterministic text
        # emission, anything other than 10/10 clean is alert-worthy.
        if any(f.severity == "alert" for f in findings):
            status = "alert"
        else:
            status = "healthy"

        return WatcherReport(
            watcher_name=self.name, domain=self.domain,
            status=status, findings=findings,
            evidence_summary=evidence,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _repo_root(self) -> pathlib.Path:
        here = pathlib.Path(__file__).resolve()
        return here.parent.parent.parent

    def _run_walk(
        self,
        script: pathlib.Path,
        repo_root: pathlib.Path,
        constraint: str,
    ) -> str | None:
        """Invoke ai-adversary.sh for one constraint; return raw text
        or None on failure."""
        try:
            proc = subprocess.run(
                ["bash", str(script), constraint],
                cwd=str(repo_root),
                capture_output=True,
                text=True,
                timeout=WALK_TIMEOUT_SECS,
            )
        except subprocess.TimeoutExpired:
            return None
        except Exception:  # noqa: BLE001
            return None
        if proc.returncode != 0:
            return None
        # Strip ANSI color codes for stable text matching.
        return re.sub(r"\x1b\[[0-9;]*m", "", proc.stdout)

    def _parse_walk(self, text: str) -> dict[str, str]:
        """Extract the six sections from an adversary walk.

        ai-adversary.sh emits numbered sections like:
            1. Defender's claim
               <indented text>
            2. Attacker's optimal response
               <indented text>
            ...

        Section headers are on lines starting with `N. <Title>` and
        bodies follow on indented lines until the next numbered
        header (or the trailing "How to use this walk:" block).
        """
        sections: dict[str, str] = {}
        current_title: str | None = None
        current_body_lines: list[str] = []

        # Lines we consider end-of-section markers.
        END_MARKERS = ("How to use this walk", "── How to use")

        for raw in text.splitlines():
            line = raw.rstrip()
            # Numbered section header?
            m = re.match(r"^\s*\d+\.\s+(.+?)\s*$", line)
            if m:
                # Flush previous section.
                if current_title is not None:
                    sections[current_title] = "\n".join(
                        current_body_lines
                    ).strip()
                current_title = m.group(1).strip()
                current_body_lines = []
                continue
            # End-of-walk marker?
            if any(marker in line for marker in END_MARKERS):
                if current_title is not None:
                    sections[current_title] = "\n".join(
                        current_body_lines
                    ).strip()
                    current_title = None
                break
            # Body line (only collect non-empty ones).
            if current_title is not None and line.strip():
                current_body_lines.append(line.strip())

        # Flush trailing section if no end marker was hit.
        if current_title is not None:
            sections[current_title] = "\n".join(current_body_lines).strip()

        return sections
