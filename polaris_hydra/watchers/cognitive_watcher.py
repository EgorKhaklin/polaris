"""CognitiveWatcher — H3 of Arc D.

Monitors the cognitive layer itself: the swarm watching the
infrastructure that watches Polaris. Specifically:

  - CM (meta-constraint) health: invokes `scripts/ai-meta.sh` and
    captures the overall status line. Drift surfaces here first.
  - Pattern catalog warmth: counts how many of the 22 named patterns
    have journal mentions. The catalog being half-cold is itself a
    signal (v8.27 surfaced this and the recap entry warmed it).
  - Script staleness: any ai-*.sh that hasn't been touched in
    > 60 days while other layers move is decay candidate.
  - Sanctum count parity: sanctum/ file count vs index entry count.
    Disagreement = audit-of-record discipline broken.
  - **(v9.04)** Pheromone-context: recent soldier_sanctum_freshness
    deposits surface stale Sanctum sessions (open >7d without close).
    The static parity check above proves the index is in sync; this
    additional channel proves the SESSIONS themselves aren't aging.
  - **(v9.06 / Wave 2 / H1)** HYDRA brief-archive freshness — the
    LENS WATCHING ITSELF. v9.04 wired HYDRA to read the swarm
    substrate; v9.04's brief-archive (`journal/hydra/<date>-<HHMM>.md`)
    is HYDRA's own AoR output. If it stops accumulating, no other
    watcher would notice — until v9.06. This channel reads the
    directory mtime + count + shape, surfaces drift if briefs go
    stale (>14d), info if archive empty (HYDRA never run with
    `--save`), healthy when active.

The watcher does NOT re-implement ai-meta's checks. It defers to
ai-meta as the canonical source and surfaces ai-meta's verdict
plus a small set of independent direct signals (file mtimes, journal
text scans). This honors the v8.30 substitutability principle: the
existing scripts remain the source of truth; the watcher reads
their outputs.
"""

from __future__ import annotations

import datetime
import os
import pathlib
import re
import subprocess
from typing import Any

from polaris_hydra.pheromone_reader import PheromoneReader, WINDOW_SLOW

from .base import Finding, Watcher, WatcherReport


# How old an ai-*.sh script can be (mtime) before "stale" fires.
# This is calibrated against the post-v2 steady-state cadence: most
# scripts settle in and rarely get touched, but a script untouched for
# > 60 days with the layer otherwise moving is a candidacy signal.
STALE_DAYS_THRESHOLD = 60

# v9.06 / H1 — HYDRA brief-archive freshness thresholds.
#
# A brief is the audit-of-record output of `Hydra.speak_full(--save)`.
# The cognitive layer should produce briefs regularly; if archive goes
# silent, either nobody is running --save (operator hygiene drift) OR
# the cognitive layer itself stopped working (constitutional drift).
HYDRA_BRIEF_STALE_DAYS = 14.0          # drift threshold
HYDRA_BRIEF_DEAD_DAYS  = 30.0          # alert threshold (cold-storage)

# The constraint-lattice / structural-architecture closure: 22 patterns.
# The watcher does NOT hard-code the names — those are the canonical
# catalog's responsibility (ai-pattern.sh). The watcher checks that
# the catalog has the right *count*, then measures warm/cold on
# whatever names are actually in it. This honors the v8.30
# substitutability principle: the canonical source stays canonical.
EXPECTED_PATTERN_COUNT = 22

# CM check labels we care about from `ai-meta.sh` output. We only need
# the overall verdict, but recording sub-check anchors here lets the
# watcher correlate future format changes.
CM_HEALTHY_MARKERS = (
    "LAYER SELF-MONITORING IS HEALTHY",
    "CM constraint satisfied",
)


class CognitiveWatcher(Watcher):
    name = "cognitive"
    domain = "CM + pattern catalog + script staleness + Sanctum integrity"

    def _observe(self) -> WatcherReport:
        repo_root = self._repo_root()
        findings: list[Finding] = []
        evidence: dict[str, Any] = {}

        # ---- 1. CM via ai-meta.sh ----------------------------------------
        meta_status, meta_output = self._invoke_ai_meta(repo_root)
        evidence["ai_meta_status"] = meta_status
        if meta_status == "healthy":
            pass  # no finding emitted; the info case at the bottom catches it
        elif meta_status == "drift":
            findings.append(Finding(
                severity="drift",
                title="ai-meta reports drift",
                detail=("ai-meta.sh's overall verdict was not the healthy "
                        "marker line. The cognitive layer claims something "
                        "is inconsistent with its own self-monitoring "
                        "checks. Run `bash scripts/ai-meta.sh` for the "
                        "specific failing check."),
                evidence={"last_lines": meta_output[-300:]
                          if meta_output else ""},
            ))
        else:  # broken
            findings.append(Finding(
                severity="alert",
                title="ai-meta.sh did not produce a verdict",
                detail=("CognitiveWatcher could not parse a CM verdict from "
                        "ai-meta.sh output. The script may have crashed or "
                        "its output format changed. The cognitive layer "
                        "cannot self-monitor right now."),
                evidence={"output_tail": meta_output[-300:]
                          if meta_output else ""},
            ))

        # ---- 2. Pattern catalog warmth -----------------------------------
        catalog_size, warm, cold = self._pattern_warmth(repo_root)
        evidence["patterns_defined"] = catalog_size
        evidence["patterns_warm"] = warm
        evidence["patterns_cold"] = cold
        evidence["patterns_expected"] = EXPECTED_PATTERN_COUNT
        if catalog_size != EXPECTED_PATTERN_COUNT and catalog_size > 0:
            findings.append(Finding(
                severity="alert",
                title=f"pattern catalog size is {catalog_size}, expected {EXPECTED_PATTERN_COUNT}",
                detail=("The constraint-lattice closure is 22 patterns "
                        "(see meta/structural-constants.json + "
                        "meta/structural-architecture.md). A different "
                        "size means either the structural invariant was "
                        "amended without updating the catalog, or vice "
                        "versa. Reconcile."),
                evidence={"catalog_size": catalog_size,
                          "expected": EXPECTED_PATTERN_COUNT},
            ))
        if catalog_size > 0 and cold > warm:
            findings.append(Finding(
                severity="drift",
                title="majority of patterns cold",
                detail=(f"Only {warm}/{catalog_size} patterns "
                        f"have journal mentions; {cold} are cold. The "
                        f"catalog tracks the shapes of work that have "
                        f"actually occurred. Predominantly cold = either "
                        f"the catalog is too broad for Polaris's domain, "
                        f"or journaling discipline is slipping."),
                evidence={"warm": warm, "cold": cold},
            ))

        # ---- 3. Script staleness -----------------------------------------
        stale_scripts = self._stale_ai_scripts(repo_root)
        evidence["stale_scripts"] = len(stale_scripts)
        evidence["stale_threshold_days"] = STALE_DAYS_THRESHOLD
        if stale_scripts:
            # Stale scripts are not necessarily a problem (some scripts
            # are one-shot installers or were correctly built once and
            # never need to change). But they're worth surfacing.
            findings.append(Finding(
                severity="info" if len(stale_scripts) <= 5 else "drift",
                title=f"{len(stale_scripts)} ai-* script(s) unchanged > {STALE_DAYS_THRESHOLD}d",
                detail=("These scripts have not been touched in the staleness "
                        "window. In post-v2 steady-state this is expected "
                        "for most scripts, but worth a glance to confirm "
                        "they still run cleanly."),
                evidence={"scripts": stale_scripts[:10]},
            ))

        # ---- 4. Sanctum count parity -------------------------------------
        sanctum_count, index_count, drift_note = self._sanctum_parity(repo_root)
        evidence["sanctum_sessions"] = sanctum_count
        evidence["sanctum_index_entries"] = index_count
        if drift_note:
            findings.append(Finding(
                severity="alert",
                title="Sanctum index drift",
                detail=drift_note,
                evidence={"sanctum_files": sanctum_count,
                          "index_entries": index_count,
                          "node_id": "cognitive:sanctum"},
            ))

        # ---- 5. Pheromone-context: soldier_sanctum_freshness (v9.04) -----
        ph_findings, ph_evidence = self._check_pheromone_sanctum_freshness()
        findings.extend(ph_findings)
        evidence.update(ph_evidence)

        # ---- 6. HYDRA brief-archive freshness (v9.06 / H1) --------------
        # The lens watching itself — see channel doc.
        hbf_findings, hbf_evidence = self._check_hydra_brief_freshness(
            repo_root
        )
        findings.extend(hbf_findings)
        evidence.update(hbf_evidence)

        # ---- Status aggregate ---------------------------------------------
        if any(f.severity == "alert" for f in findings):
            status = "alert"
        elif sum(1 for f in findings if f.severity == "drift") >= 2:
            status = "drift"
        elif any(f.severity == "drift" for f in findings):
            status = "drift"
        else:
            status = "healthy"

        if not findings:
            findings.append(Finding(
                severity="info",
                title="cognitive layer healthy",
                detail=(f"CM healthy. Pattern catalog {warm}/{catalog_size} "
                        f"warm. Sanctum index in sync ({sanctum_count} sessions). "
                        f"No stale scripts beyond threshold."),
                evidence={
                    "patterns_warm": warm,
                    "sanctum_sessions": sanctum_count,
                    "ai_meta_status": meta_status,
                },
            ))

        return WatcherReport(
            watcher_name=self.name,
            domain=self.domain,
            status=status,
            findings=findings,
            evidence_summary=evidence,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _repo_root(self) -> pathlib.Path:
        """Locate the Polaris repo root by walking up from this file."""
        # polaris_hydra/watchers/cognitive_watcher.py → polaris_hydra/watchers/
        #   → polaris_hydra/ → repo root
        here = pathlib.Path(__file__).resolve()
        return here.parent.parent.parent

    def _invoke_ai_meta(self, repo_root: pathlib.Path) -> tuple[str, str]:
        """Run ai-meta.sh and classify the verdict.

        Returns ("healthy" | "drift" | "broken", raw_output).
        """
        script = repo_root / "scripts" / "ai-meta.sh"
        if not script.is_file():
            return "broken", "scripts/ai-meta.sh not present"
        try:
            proc = subprocess.run(
                ["bash", str(script)],
                cwd=str(repo_root),
                capture_output=True,
                text=True,
                timeout=30,
            )
        except subprocess.TimeoutExpired:
            return "broken", "ai-meta.sh timed out (> 30s)"
        except Exception as exc:  # noqa: BLE001
            return "broken", f"ai-meta.sh invocation failed: {exc}"

        # Combine stdout + stderr — ai-meta writes mostly to stdout.
        output = (proc.stdout or "") + (proc.stderr or "")
        # Strip ANSI color codes that the script emits in interactive
        # mode (subprocess capture preserves them when run from a TTY-
        # detecting environment); strip defensively.
        output = re.sub(r"\x1b\[[0-9;]*m", "", output)

        if any(marker in output for marker in CM_HEALTHY_MARKERS):
            return "healthy", output
        if "META-DRIFT" in output or "drift" in output.lower():
            return "drift", output
        return "broken", output

    def _pattern_warmth(
        self, repo_root: pathlib.Path
    ) -> tuple[int, int, int]:
        """Read the pattern catalog dynamically + measure warmth.

        Returns (catalog_size, warm_count, cold_count). The catalog is
        whatever ai-pattern.sh defines; the watcher does not enforce
        specific names, only the count + the warm/cold ratio.
        """
        pattern_script = repo_root / "scripts" / "ai-pattern.sh"
        if not pattern_script.is_file():
            return 0, 0, 0

        text = pattern_script.read_text(errors="replace")
        defined_patterns: list[str] = []
        for m in re.finditer(r"^\s*\d+\s*\|\s*([A-Z][A-Za-z]+)\s*\|",
                             text, flags=re.MULTILINE):
            defined_patterns.append(m.group(1))
        catalog_size = len(defined_patterns)

        if catalog_size == 0:
            return 0, 0, 0

        # Count journal mentions per pattern.
        journal_dir = repo_root / "journal"
        if not journal_dir.is_dir():
            return catalog_size, 0, catalog_size

        # Read all journal entries once (~30-50 files, modest cost).
        journal_text = ""
        for entry in journal_dir.glob("*.md"):
            try:
                journal_text += entry.read_text(errors="replace")
            except OSError:
                pass

        warm = sum(1 for p in defined_patterns if p in journal_text)
        cold = catalog_size - warm
        return catalog_size, warm, cold

    def _stale_ai_scripts(
        self, repo_root: pathlib.Path
    ) -> list[dict[str, Any]]:
        """Find ai-*.sh scripts unchanged for > STALE_DAYS_THRESHOLD."""
        scripts_dir = repo_root / "scripts"
        if not scripts_dir.is_dir():
            return []
        now = datetime.datetime.now().timestamp()
        threshold_secs = STALE_DAYS_THRESHOLD * 86400
        stale: list[dict[str, Any]] = []
        for script in scripts_dir.glob("ai-*.sh"):
            try:
                mtime = script.stat().st_mtime
            except OSError:
                continue
            age_days = (now - mtime) / 86400
            if (now - mtime) > threshold_secs:
                stale.append({
                    "script": script.name,
                    "age_days": round(age_days, 1),
                })
        stale.sort(key=lambda d: -d["age_days"])
        return stale

    def _sanctum_parity(
        self, repo_root: pathlib.Path
    ) -> tuple[int, int, str]:
        """Compare sanctum/ session count with meta/sanctum-index.md entries.

        Returns (session_file_count, index_entry_count, drift_note).
        Empty drift_note means in sync.
        """
        sanctum_dir = repo_root / "sanctum"
        index_file = repo_root / "meta" / "sanctum-index.md"

        if not sanctum_dir.is_dir():
            return 0, 0, "sanctum/ directory missing"

        # Session files: YYYY-MM-DD-*.md, excluding README.md.
        sessions = [p for p in sanctum_dir.glob("2026-*.md")]
        session_count = len(sessions)

        index_count = 0
        if index_file.is_file():
            text = index_file.read_text(errors="replace")
            index_count = len(
                re.findall(r"^- \*\*2026-", text, flags=re.MULTILINE)
            )

        if session_count != index_count:
            return session_count, index_count, (
                f"sanctum/ has {session_count} session file(s) but "
                f"meta/sanctum-index.md has {index_count} entry/entries. "
                f"Run `ai-sanctum.sh close` to re-index, or inspect "
                f"manually."
            )
        return session_count, index_count, ""

    # ------------------------------------------------------------------
    # Channel 5 (v9.04): pheromone-context — soldier_sanctum_freshness
    # ------------------------------------------------------------------

    def _check_pheromone_sanctum_freshness(
        self,
    ) -> tuple[list[Finding], dict[str, Any]]:
        """Read recent soldier_sanctum_freshness deposits + surface stale.

        soldier_sanctum_freshness inspects sanctum/ and deposits:
          - kind='alert' for sessions OPEN > N days (the soldier
            decides N; the watcher reads the verdict)
          - kind='drift' for sessions trending toward stale
          - kind='info' for healthy sessions

        Where channel 4 (sanctum parity) checks structural integrity
        (file count == index count), this channel checks whether the
        sessions THEMSELVES are aging out unnoticed. Both are
        necessary; neither subsumes the other.

        Graceful: missing reader / no deposits → no findings.
        """
        findings: list[Finding] = []
        evidence: dict[str, Any] = {
            "pheromone_sanctum_freshness_status": "unknown",
        }

        try:
            reader = PheromoneReader(window_hours=WINDOW_SLOW)
            deposits = reader.deposits_by_class("soldier_sanctum_freshness",
                                                window_hours=WINDOW_SLOW)
        except Exception as exc:  # noqa: BLE001 — graceful
            evidence["pheromone_sanctum_freshness_status"] = (
                f"reader_error:{type(exc).__name__}"
            )
            return findings, evidence

        if not deposits:
            evidence["pheromone_sanctum_freshness_status"] = (
                "no_deposits_in_window"
            )
            return findings, evidence

        evidence["pheromone_sanctum_freshness_status"] = "ok"
        evidence["pheromone_sanctum_freshness_count"] = len(deposits)

        alert_count = sum(1 for d in deposits if d.kind == "alert")
        drift_count = sum(1 for d in deposits if d.kind == "drift")
        evidence["pheromone_sanctum_freshness_alert"] = alert_count
        evidence["pheromone_sanctum_freshness_drift"] = drift_count

        if alert_count > 0 or drift_count > 0:
            stale_sessions = sorted({
                d.node_id for d in deposits
                if d.kind in ("alert", "drift")
            })[:5]
            findings.append(Finding(
                severity="drift",
                title=(f"soldier_sanctum_freshness flagged "
                       f"{alert_count + drift_count} session(s)"),
                detail=(
                    f"In the last {WINDOW_SLOW:.0f}h "
                    f"soldier_sanctum_freshness deposited "
                    f"{alert_count} alert + {drift_count} "
                    f"drift pheromone(s). The Sanctum index parity "
                    f"check above is fine, but at least one session "
                    f"has been OPEN long enough that the soldier "
                    f"flagged it. Sample: {stale_sessions}"
                ),
                evidence={
                    "alert_count": alert_count,
                    "drift_count": drift_count,
                    "stale_sessions": stale_sessions,
                    "node_id": ("cognitive:sanctum" if not stale_sessions
                                else stale_sessions[0]),
                    "pheromone_context": "soldier_sanctum_freshness",
                },
            ))

        return findings, evidence

    # ------------------------------------------------------------------
    # Channel 6 (v9.06 / H1): HYDRA brief-archive freshness — the lens
    # watching itself
    # ------------------------------------------------------------------

    def _check_hydra_brief_freshness(
        self, repo_root: pathlib.Path
    ) -> tuple[list[Finding], dict[str, Any]]:
        """Read journal/hydra/ and surface freshness signals.

        States:
          - empty   → info: HYDRA never run with --save (operator hygiene)
          - fresh   → no finding (brief within HYDRA_BRIEF_STALE_DAYS)
          - stale   → drift: most-recent brief between STALE and DEAD days
          - dead    → alert: most-recent brief older than DEAD days
                      (the cognitive layer probably stopped working)

        The check is filesystem-only — no DB, no LLM — so it works
        even when DB is offline. Constitutional preservation: read-only.
        """
        findings: list[Finding] = []
        evidence: dict[str, Any] = {
            "hydra_brief_archive_status": "unknown",
        }

        archive_dir = repo_root / "journal" / "hydra"
        if not archive_dir.is_dir():
            evidence["hydra_brief_archive_status"] = "no_directory"
            findings.append(Finding(
                severity="info",
                title="journal/hydra/ directory absent",
                detail=(
                    "HYDRA's brief-archive directory does not exist. "
                    "Run `bash scripts/ai-hydra.sh --full --save` to "
                    "produce the first brief. (v9.04 hybrid intelligence "
                    "feature.)"
                ),
                evidence={"path": str(archive_dir),
                          "node_id": "cognitive:hydra_brief"},
            ))
            return findings, evidence

        briefs = sorted(archive_dir.glob("*.md"))
        evidence["hydra_brief_count"] = len(briefs)

        if not briefs:
            evidence["hydra_brief_archive_status"] = "empty"
            findings.append(Finding(
                severity="info",
                title="HYDRA brief-archive is empty",
                detail=(
                    "journal/hydra/ exists but contains no briefs. "
                    "Run `bash scripts/ai-hydra.sh --full --save` to "
                    "produce one. The brief-archive feeds the v9.04 "
                    "delta-detection + v9.06 lens-watching-itself loop."
                ),
                evidence={"path": str(archive_dir),
                          "node_id": "cognitive:hydra_brief"},
            ))
            return findings, evidence

        # Use mtime of newest brief as the freshness marker.
        latest = max(briefs, key=lambda p: p.stat().st_mtime)
        latest_mtime = datetime.datetime.fromtimestamp(latest.stat().st_mtime)
        age_days = (datetime.datetime.now() - latest_mtime).total_seconds() \
                   / 86400.0
        evidence["hydra_brief_latest"] = latest.name
        evidence["hydra_brief_age_days"] = round(age_days, 2)
        evidence["hydra_brief_stale_threshold_days"] = HYDRA_BRIEF_STALE_DAYS
        evidence["hydra_brief_dead_threshold_days"] = HYDRA_BRIEF_DEAD_DAYS

        if age_days >= HYDRA_BRIEF_DEAD_DAYS:
            evidence["hydra_brief_archive_status"] = "dead"
            findings.append(Finding(
                severity="alert",
                title=(f"HYDRA brief-archive dead "
                       f"({age_days:.0f}d since last save)"),
                detail=(
                    f"The most-recent brief at {latest.name} is "
                    f"{age_days:.1f} days old (> {HYDRA_BRIEF_DEAD_DAYS:.0f}d "
                    f"dead threshold). The cognitive layer's lens has "
                    f"stopped emitting OR no operator has run "
                    f"`ai-hydra.sh --full --save` in over a month. "
                    f"Either is worth investigating — the lens is "
                    f"how HYDRA tracks its own state across runs."
                ),
                # v9.10 / S1: shared-surface `runtime:swarm` (DEAD)
                evidence={"latest_brief": latest.name,
                          "age_days": round(age_days, 2),
                          "node_id": "cognitive:hydra_brief",
                          "additional_node_ids": ["runtime:swarm"]},
            ))
        elif age_days >= HYDRA_BRIEF_STALE_DAYS:
            evidence["hydra_brief_archive_status"] = "stale"
            findings.append(Finding(
                severity="drift",
                title=(f"HYDRA brief-archive stale "
                       f"({age_days:.1f}d since last save)"),
                detail=(
                    f"The most-recent brief at {latest.name} is "
                    f"{age_days:.1f} days old (> {HYDRA_BRIEF_STALE_DAYS:.0f}d "
                    f"stale threshold). Run `bash scripts/ai-hydra.sh "
                    f"--full --save` to refresh. The lens-watching-"
                    f"itself loop (v9.06 / H1) needs regular brief "
                    f"deposits to detect cross-run drift."
                ),
                # v9.10 / S1: shared-surface `runtime:swarm` —
                # ant_colony_watcher emits the same when soldiers are
                # silent. HYDRA-brief-stale means HYDRA isn't running
                # often, which usually means the swarm isn't either.
                evidence={"latest_brief": latest.name,
                          "age_days": round(age_days, 2),
                          "node_id": "cognitive:hydra_brief",
                          "additional_node_ids": ["runtime:swarm"]},
            ))
        else:
            evidence["hydra_brief_archive_status"] = "fresh"
            # Healthy — no finding emitted; the no-finding info case
            # at the bottom of _observe() catches this.

        return findings, evidence
