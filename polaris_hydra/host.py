"""HYDRA host — Arc D · H1; v9.04 hybrid-intelligence revamp.

HYDRA is Polaris's swarm-synthesis layer. It:

  1. Invokes each enabled watcher to collect a list of WatcherReport.
  2. Optionally calls Claude Opus 4.7 with adaptive thinking to
     synthesize the reports into a single brief in the Architect
     voice (`meta/architect.md`).
  3. If `ANTHROPIC_API_KEY` is unset, emits a deterministic structured
     summary instead. The swarm works offline + under CI.

**v9.04 hybrid intelligence (Sanctum 2026-05-14-hydra-revamp-pheromone-
integration.md).** `speak_full()` extends `speak()` with three new
post-gather stages: CorrelationEngine (cross-watcher correlations),
ActionQueue (ranked next-moves), and (optional) brief-archive +
delta-detection (`journal/hydra/<YYYY-MM-DD>-<HHMM>.md`). The
output is a `HybridIntelligenceBrief` extending HydraSynthesis with
4 new fields (correlations, actions, archive_path, delta).

Modeled on BettaFish's `ForumEngine/llm_host.py` pattern (N
specialist agents → host moderator → unified synthesis). Not vendored;
Polaris-native code informed by the pattern. v9.04 extends the
pattern: the agents themselves now read shared substrate
(Pheromone), producing a richer synthesis than either tier alone
could.

The Architect persona is unchanged. HYDRA *consumes* that persona as
its synthesis voice — invoking the Architect's six-section brief
structure (I State, II Outlook, III Drift, IV Threats, V Suggestions,
VI Self-monitoring), but informed by N parallel watcher findings
instead of one synthesis pass.
"""

from __future__ import annotations

import dataclasses
import datetime
import json
import os
import sys
from typing import Iterable, Optional

import pathlib

from polaris_hydra.watchers import (
    AdversaryWatcher,
    AntColonyWatcher,
    CivitasWatcher,
    CognitiveWatcher,
    Finding,
    MissionWatcher,
    PerformanceWatcher,
    SchemaWatcher,
    SecurityWatcher,
    TrajectoryWatcher,
    Watcher,
    WatcherReport,
)
from polaris_hydra.action_queue import Action, ActionQueue
from polaris_hydra.oracles import OracleSnapshot, read_oracles, reconcile
from polaris_hydra.brief_archive import (
    BriefDelta,
    archive_brief,
    compute_delta,
    compute_delta_in_memory,
)
from polaris_hydra.correlation import CorrelatedFinding, CorrelationEngine
from polaris_hydra.pheromone_reader import PheromoneReader, PheromoneSnapshot


# Repo root inferred once for archive + diff paths.
_HERE = pathlib.Path(__file__).resolve().parent
_REPO_ROOT = _HERE.parent


# Registry of all watchers — **the nine canonical Hydra heads** (v8.72+).
#
# The Lernaean Hydra had nine mortal heads (Apollodorus). Prior to
# v8.72 the Hydra-9 mythology was anchored on Mycelium legions
# (v8.65 / arc-e-hydra-nine-heads-completion). VANTA's v8.72
# directive relocated the mythology to its etymological home: the
# watchers in `polaris_hydra/`. The watcher count now carries the
# mythology; the specific watcher identities are substitutable per
# v8.30.
#
# CM is the immortal 10th head — narrative only, constitutional;
# it does NOT appear in this registry.
#
# Phase 1 (v8.37):    SchemaWatcher.
# Phase 2 (v8.38–v8.42): full swarm — one watcher per ship.
# Phase 3 (v8.43):    HYDRA constitutional integration (no new watcher).
# Post-Arc-D (v8.49): TrajectoryWatcher — observes shipping trajectory.
# v8.72 mythology relocation: AntColonyWatcher + CivitasWatcher
#   added — the 8th and 9th heads — closing the runtime-observation
#   gap (the swarm + the citizen layer became primary in Arcs E+F+G
#   but had no dedicated watchers). Authorized by
#   `sanctum/2026-05-13-hydra-mythology-relocation-to-watchers.md`.
ALL_WATCHERS: dict[str, type[Watcher]] = {
    "schema":      SchemaWatcher,
    "cognitive":   CognitiveWatcher,     # v8.38
    "security":    SecurityWatcher,      # v8.39
    "mission":     MissionWatcher,       # v8.40
    "adversary":   AdversaryWatcher,     # v8.41
    "performance": PerformanceWatcher,   # v8.42 — closes Phase 2
    "trajectory":  TrajectoryWatcher,    # v8.49 — post-Arc-D extension
    "ant_colony":  AntColonyWatcher,     # v8.72 — 8th head
    "civitas":     CivitasWatcher,       # v8.72 — 9th head
}


@dataclasses.dataclass
class HydraSynthesis:
    """The final output VANTA sees.

    `voice` is the synthesis text (in the Architect's register).
    `reports` is the underlying watcher data (the audit trail).
    `mode` says whether the LLM was used or the deterministic
    fallback. `mode_reason` (v8.45) distinguishes WHY deterministic
    was chosen, since pre-v8.45 a consumer reading `mode` alone could
    not tell `no_key` from `llm_error`. `generated_at` pins the moment.
    """

    voice: str
    reports: list[WatcherReport]
    mode: str  # "llm" | "deterministic"
    mode_reason: str = "ok"
    # mode_reason values:
    #   "ok"                — mode=llm succeeded, or mode=deterministic
    #                          with no LLM attempted (steady-state default)
    #   "no_anthropic_key"  — mode=deterministic because ANTHROPIC_API_KEY unset
    #   "llm_error:<type>"  — mode=deterministic because LLM attempt raised
    generated_at: datetime.datetime = dataclasses.field(
        default_factory=datetime.datetime.now
    )

    def to_dict(self) -> dict:
        return {
            "voice": self.voice,
            "reports": [r.to_dict() for r in self.reports],
            "mode": self.mode,
            "mode_reason": self.mode_reason,
            "generated_at": self.generated_at.isoformat(timespec="seconds"),
        }


@dataclasses.dataclass
class HybridIntelligenceBrief:
    """v9.04: extends HydraSynthesis with cross-watcher correlations,
    a ranked action queue, optional brief-archive, and (when an
    archive lands AND a prior archive exists) a delta vs the prior
    brief. v9.24 (BIG MISSION T1#6) adds the external-oracles
    reconciliation block — the brief must now explicitly agree or
    diverge against ground-truth signals HYDRA does not control.

    This is the output of `Hydra.speak_full()` — the load-bearing v9.04
    addition. It composes:

      - synthesis: the existing watcher voice + reports (HydraSynthesis)
      - pheromone_snapshot: the swarm substrate read at gather time
      - correlations: cross-watcher findings (CorrelatedFinding[])
      - actions: ranked next-moves (Action[])
      - archive_path: path of the saved brief (if --save), else None
      - delta: BriefDelta vs prior brief (if computable), else None
      - oracles: OracleSnapshot read from meta/oracle-state.json (v9.24)
      - oracle_reconciliation: list of AGREE/DIVERGE/NOTE strings (v9.24)
    """
    synthesis: HydraSynthesis
    pheromone_snapshot: PheromoneSnapshot
    correlations: list[CorrelatedFinding]
    actions: list[Action]
    archive_path: pathlib.Path | None = None
    delta: BriefDelta | None = None
    oracles: "OracleSnapshot | None" = None
    oracle_reconciliation: list = dataclasses.field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "synthesis": self.synthesis.to_dict(),
            "pheromone_snapshot": self.pheromone_snapshot.to_dict(),
            "correlations": [c.to_dict() for c in self.correlations],
            "actions": [a.to_dict() for a in self.actions],
            "archive_path": (
                str(self.archive_path) if self.archive_path else None
            ),
            "delta": self.delta.to_dict() if self.delta else None,
            "oracles": (
                {
                    "status": self.oracles.status,
                    "last_run_utc": self.oracles.last_run_utc,
                    "age_days": self.oracles.age_days,
                }
                if self.oracles is not None
                else None
            ),
            "oracle_reconciliation": list(self.oracle_reconciliation),
        }


class Hydra:
    """The aggregator-with-voice. Invoke watchers, synthesize, report.

    Usage:

        hydra = Hydra()                       # all enabled watchers
        hydra = Hydra(watchers=["schema"])    # subset
        synthesis = hydra.speak()             # full pass: gather + synthesize
        synthesis = hydra.speak(query="…")    # focused synthesis on a query

    The output is a HydraSynthesis with both the synthesized voice
    (for VANTA) and the underlying watcher reports (the audit trail).
    """

    def __init__(self, watchers: Optional[Iterable[str]] = None):
        if watchers is None:
            self._watcher_names = list(ALL_WATCHERS.keys())
        else:
            unknown = [w for w in watchers if w not in ALL_WATCHERS]
            if unknown:
                known = ", ".join(sorted(ALL_WATCHERS.keys()))
                raise ValueError(
                    f"Unknown watcher(s): {unknown!r}. Known: {known}"
                )
            self._watcher_names = list(watchers)

    def gather(self) -> list[WatcherReport]:
        """Invoke each enabled watcher in sequence. Returns the
        reports. Watchers are deterministic + already graceful, so
        this never raises."""
        reports: list[WatcherReport] = []
        for name in self._watcher_names:
            watcher_cls = ALL_WATCHERS[name]
            reports.append(watcher_cls().report())
        return reports

    def speak(
        self,
        query: Optional[str] = None,
        force_deterministic: bool = False,
    ) -> HydraSynthesis:
        """Full pass: gather watcher reports, synthesize a voice.

        If `ANTHROPIC_API_KEY` is set, calls Claude Opus 4.7 with
        adaptive thinking to compose the voice in the Architect's
        register. Otherwise emits a deterministic structured summary
        sufficient for CI + offline use.

        v9.05 / Wave 1 / I2 — `force_deterministic=True` ignores the
        env var and always uses the deterministic path. Useful for:
          - testing that the deterministic surface still works without
            having to unset ANTHROPIC_API_KEY in the shell
          - CI determinism guarantees
          - cost control during heavy iteration

        `query` (optional) focuses the synthesis. Examples:
            "what is the current state of the audit-of-record discipline?"
            "is there anything VANTA should know before shipping v8.38?"

        With no query, HYDRA produces a general state-of-the-swarm
        synthesis.
        """
        reports = self.gather()
        if not force_deterministic and os.environ.get("ANTHROPIC_API_KEY"):
            try:
                voice = self._llm_synthesize(reports, query)
                return HydraSynthesis(
                    voice=voice, reports=reports,
                    mode="llm", mode_reason="ok",
                )
            except Exception as exc:  # noqa: BLE001 — graceful fallback
                voice = self._deterministic_synthesize(
                    reports, query,
                    fallback_note=(f"LLM synthesis failed: "
                                   f"{type(exc).__name__}: {exc}. "
                                   f"Falling back to deterministic output."),
                )
                return HydraSynthesis(
                    voice=voice, reports=reports,
                    mode="deterministic",
                    mode_reason=f"llm_error:{type(exc).__name__}",
                )

        voice = self._deterministic_synthesize(reports, query)
        # v9.05 / I2: differentiate forced-deterministic from no-key case.
        mode_reason = (
            "forced_deterministic" if force_deterministic
            else "no_anthropic_key"
        )
        return HydraSynthesis(
            voice=voice, reports=reports,
            mode="deterministic", mode_reason=mode_reason,
        )

    # ----------------------------------------------------------------
    # v9.04: hybrid intelligence — speak_full
    # ----------------------------------------------------------------

    def speak_full(
        self,
        query: Optional[str] = None,
        save: bool = False,
        diff_against: Optional[pathlib.Path] = None,
        pheromone_window_hours: float = 6.0,
        force_deterministic: bool = False,
    ) -> HybridIntelligenceBrief:
        """Full hybrid-intelligence pass.

        Stages:
          1. Snapshot Pheromone substrate (PheromoneReader)
          2. Gather watcher reports (existing speak() pipeline; the
             watchers themselves use PheromoneReader via the v9.04
             pheromone-context channels)
          3. Synthesize voice (LLM if key set; else deterministic)
          4. Correlate cross-watcher findings (CorrelationEngine)
          5. Rank into ActionQueue
          6. (optional) Archive brief to journal/hydra/ + compute
             delta vs prior brief

        Returns HybridIntelligenceBrief composing all five outputs.

        Constitutional contract:
          - C1: archive is filesystem audit-of-record (append-only;
            never overwrites; HYDRA never deletes prior briefs)
          - C10: pheromone_snapshot is metadata-only (deposited_by /
            kind / node_id / etc.); no holder PII path
          - G1: deterministic given (snapshot, reports) — same input
            produces same correlations + same action queue
          - G3: graceful — if LLM fails, falls back to deterministic;
            if Pheromone DB offline, snapshot.status=='db_offline'
            and the rest of the pipeline still runs
        """
        # Stage 1: snapshot the substrate
        reader = PheromoneReader(window_hours=pheromone_window_hours)
        snapshot = reader.snapshot()

        # Stage 2+3: gather + synthesize (existing pipeline)
        synthesis = self.speak(
            query=query, force_deterministic=force_deterministic
        )

        # Stage 4: correlate
        correlations = CorrelationEngine(synthesis.reports).correlate()

        # Stage 5: rank into actions (top 10 to keep brief readable)
        actions = ActionQueue(synthesis.reports, correlations).rank(top_n=10)

        # Stage 5.5 (v9.24 / T1#6): read external oracles + reconcile.
        # The reader never runs the underlying probes itself (G1 + speed);
        # operator runs scripts/polaris-oracle-runner.sh to refresh state.
        oracles = read_oracles()
        all_findings = []
        for rep in synthesis.reports:
            all_findings.extend(getattr(rep, "findings", []) or [])
        oracle_reconciliation = reconcile(oracles, all_findings)

        # Stage 6 (optional): archive + delta
        archive_path: pathlib.Path | None = None
        delta: BriefDelta | None = None
        if save:
            archive_path = archive_brief(
                repo_root=_REPO_ROOT,
                voice=synthesis.voice,
                reports=synthesis.reports,
                correlations=correlations,
                actions=actions,
                pheromone_snapshot=snapshot,
            )
            # Delta against prior (most-recent OTHER brief, by default)
            delta = compute_delta(
                repo_root=_REPO_ROOT,
                current_brief_path=archive_path,
                prior_brief_path=diff_against,
            )
        elif diff_against is not None:
            # v9.05 / Wave 1 / D4 — pure in-memory delta. No temp file.
            # Pre-v9.05 this branch wrote a temp brief, computed delta,
            # then conditionally cleaned up — fragile and unnecessary
            # since the title-sets are already in memory. The new
            # `compute_delta_in_memory()` extracts directly from
            # `synthesis.reports + actions` without disk roundtrip.
            delta = compute_delta_in_memory(
                repo_root=_REPO_ROOT,
                reports=synthesis.reports,
                actions=actions,
                prior_brief_path=diff_against,
            )

        return HybridIntelligenceBrief(
            synthesis=synthesis,
            pheromone_snapshot=snapshot,
            correlations=correlations,
            actions=actions,
            archive_path=archive_path,
            delta=delta,
            oracles=oracles,
            oracle_reconciliation=oracle_reconciliation,
        )

    # ----------------------------------------------------------------
    # Synthesis strategies
    # ----------------------------------------------------------------

    def _llm_synthesize(
        self,
        reports: list[WatcherReport],
        query: Optional[str],
    ) -> str:
        """Call Claude Opus 4.7 with adaptive thinking.

        Lazy-imports the anthropic SDK so the package loads even when
        the SDK is not installed. If the import fails, the caller
        catches and falls back.
        """
        from anthropic import Anthropic  # lazy: optional dependency

        client = Anthropic()
        system = self._system_prompt()
        user = self._user_prompt(reports, query)

        # Per the Anthropic skill: default to claude-opus-4-7 with
        # adaptive thinking. Stream-collected via .get_final_message().
        with client.messages.stream(
            model="claude-opus-4-7",
            max_tokens=4096,
            thinking={"type": "adaptive"},
            system=system,
            messages=[{"role": "user", "content": user}],
        ) as stream:
            final = stream.get_final_message()

        # Concatenate all text blocks from the response.
        text_parts: list[str] = []
        for block in final.content:
            if getattr(block, "type", None) == "text":
                text_parts.append(block.text)
        return "".join(text_parts).strip()

    def _deterministic_synthesize(
        self,
        reports: list[WatcherReport],
        query: Optional[str],
        fallback_note: Optional[str] = None,
    ) -> str:
        """Structured-output synthesis used when no LLM is available.

        The voice is plain, declarative, and stays close to the data.
        Useful for CI, tests, and quick local checks. The schema
        matches the Architect brief's six sections but is dense
        rather than narrative.
        """
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        lines: list[str] = [
            "═══ HYDRA — DETERMINISTIC SYNTHESIS ═══",
            f"  Generated: {now}",
            f"  Mode: deterministic (no ANTHROPIC_API_KEY, or LLM fallback)",
        ]
        if fallback_note:
            lines.append(f"  Note: {fallback_note}")
        if query:
            lines.append(f"  Query: {query}")
        lines.append("")

        # I. State of the swarm
        lines.append("─── I. State of the swarm ───")
        status_counts = {"healthy": 0, "drift": 0, "alert": 0}
        for r in reports:
            status_counts[r.status] = status_counts.get(r.status, 0) + 1
        lines.append(
            f"  Watchers reporting: {len(reports)} "
            f"({status_counts['healthy']} healthy, "
            f"{status_counts['drift']} drift, "
            f"{status_counts['alert']} alert)"
        )
        for r in reports:
            lines.append(f"  - {r.watcher_name:12s} {r.status:8s} "
                         f"({len(r.findings)} finding(s))")
        lines.append("")

        # II. Findings (the watcher details)
        lines.append("─── II. Findings ───")
        any_finding = False
        for r in reports:
            for f in r.findings:
                if f.severity == "info" and len(r.findings) == 1:
                    # info-only no-issue findings: don't clutter the brief
                    continue
                any_finding = True
                lines.append(f"  [{f.severity.upper():5s}] "
                             f"{r.watcher_name}: {f.title}")
                lines.append(f"          {f.detail}")
        if not any_finding:
            lines.append("  (No drift or alert findings. The swarm is quiet.)")
        lines.append("")

        # III. Recommendation (deterministic)
        lines.append("─── III. Recommendation ───")
        if status_counts["alert"] > 0:
            lines.append("  ALERT findings present. Investigate before any "
                         "MEDIUM/HIGH-risk ship.")
        elif status_counts["drift"] > 0:
            lines.append("  Drift signals present but no alerts. Schedule "
                         "maintenance under the steady-state contract.")
        else:
            lines.append("  The swarm is healthy. Steady-state holds.")
        lines.append("")

        # IV. Evidence summary (one line per watcher)
        lines.append("─── IV. Evidence ───")
        for r in reports:
            keys = list(r.evidence_summary.keys())[:6]
            summary = ", ".join(
                f"{k}={r.evidence_summary[k]}"
                for k in keys
                if not isinstance(r.evidence_summary[k], (list, dict))
            )
            if summary:
                lines.append(f"  {r.watcher_name}: {summary}")
        lines.append("")

        lines.append("── HYDRA (deterministic mode; "
                     "for LLM synthesis set ANTHROPIC_API_KEY)")
        return "\n".join(lines)

    def _system_prompt(self) -> str:
        """The Architect register, applied to swarm synthesis."""
        return (
            "You are HYDRA, the synthesis voice of Polaris's cognitive "
            "swarm. You inherit the Architect persona defined in "
            "`meta/architect.md`: declarative, no em-dashes, "
            "intelligence-report aesthetic, game-theoretic framing where "
            "it predicts behavior, names patterns when they appear, "
            "no larping.\n\n"
            "Your input is a JSON list of WatcherReports from "
            "specialist swarm agents. Each report has a watcher_name, "
            "domain, status, findings (severity + title + detail + "
            "evidence), and evidence_summary.\n\n"
            "Your output is a unified brief to VANTA. Structure:\n"
            "  I. State of the swarm (1-2 sentence headline + per-watcher "
            "status table)\n"
            "  II. Drift + alerts (compact list of the actionable findings, "
            "highest severity first; ignore info-only findings unless they "
            "are themselves the story)\n"
            "  III. Recommendation (one sentence: what should VANTA do)\n"
            "  IV. Self-monitoring (anything HYDRA itself noticed about "
            "its own reading — uncertainty, missing watchers, etc.)\n\n"
            "Keep the brief tight. Do not paste the raw evidence; the "
            "evidence is in the JSON, available to VANTA on demand. Your "
            "job is synthesis."
        )

    def _user_prompt(
        self,
        reports: list[WatcherReport],
        query: Optional[str],
    ) -> str:
        reports_json = json.dumps(
            [r.to_dict() for r in reports], indent=2, sort_keys=False
        )
        query_clause = (
            f"VANTA's query: {query}\n\n"
            if query else
            "VANTA did not specify a query; produce a general "
            "state-of-the-swarm brief.\n\n"
        )
        return (
            f"{query_clause}"
            f"Watcher reports:\n```json\n{reports_json}\n```\n\n"
            f"Synthesize per the system instructions."
        )


# ----------------------------------------------------------------------
# CLI entry point — invoked by scripts/ai-hydra.sh
# ----------------------------------------------------------------------

def _cli(argv: list[str]) -> int:
    """v9.04 CLI (+ v9.05 --deterministic + v9.09 --gc):
       python -m polaris_hydra.host [--watcher NAME] [--json]
                                    [--query "..."]
                                    [--full | --actions | --gc]
                                    [--save] [--diff <prior_brief.md>]
                                    [--pheromone-window-hours N]
                                    [--deterministic]
                                    [--gc-keep N] [--gc-yes]

    Modes:
      (default)        watcher synthesis (existing v8.37 behavior)
      --full           hybrid intelligence: gather + correlate + actions +
                       pheromone snapshot
      --actions        just the ranked action queue
      --save           archive the brief to journal/hydra/ + compute delta
      --diff <p>       compute delta against the given prior brief
      --pheromone-window-hours N  override the default 6h substrate window
      --deterministic  force deterministic synthesis even when
                       ANTHROPIC_API_KEY is set (v9.05 / I2)
      --gc             rotate journal/hydra/ — list briefs older than
                       GC_KEEP_MOST_RECENT (default 30) + ask operator to
                       confirm purge; preserves C1 audit-of-record by
                       requiring explicit operator confirmation (v9.09 / H)
      --gc-keep N      override default keep-count (default 30)
      --gc-yes         skip confirmation prompt (for cron use; still
                       prints what's purged)

    Returns POSIX exit code: 0 if any synthesis was produced (even
    with alerts), 1 if HYDRA itself failed.
    """
    selected: Optional[list[str]] = None
    emit_json = False
    query: Optional[str] = None
    mode_full = False
    mode_actions = False
    mode_gc = False
    save = False
    diff_path: Optional[pathlib.Path] = None
    pheromone_window_hours = 6.0
    force_deterministic = False
    gc_keep = 30
    gc_yes = False
    promote_actions = False     # v9.11 / Chapter X: auto-promote top-N actions to ROADMAP
    promote_top_n = 5

    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg == "--watcher" and i + 1 < len(argv):
            selected = (selected or []) + [argv[i + 1]]
            i += 2
        elif arg == "--json":
            emit_json = True
            i += 1
        elif arg == "--query" and i + 1 < len(argv):
            query = argv[i + 1]
            i += 2
        elif arg == "--full":
            mode_full = True
            i += 1
        elif arg == "--actions":
            mode_actions = True
            i += 1
        elif arg == "--save":
            save = True
            i += 1
        elif arg == "--diff" and i + 1 < len(argv):
            diff_path = pathlib.Path(argv[i + 1])
            if not diff_path.is_absolute():
                diff_path = (_REPO_ROOT / diff_path).resolve()
            i += 2
        elif arg == "--pheromone-window-hours" and i + 1 < len(argv):
            try:
                pheromone_window_hours = float(argv[i + 1])
            except ValueError:
                print(f"Invalid --pheromone-window-hours: {argv[i + 1]!r}",
                      file=sys.stderr)
                return 1
            i += 2
        elif arg == "--deterministic":
            # v9.05 / I2: bypass LLM even if ANTHROPIC_API_KEY is set.
            force_deterministic = True
            i += 1
        elif arg == "--gc":
            # v9.09 / H: rotate journal/hydra/
            mode_gc = True
            i += 1
        elif arg == "--gc-keep" and i + 1 < len(argv):
            try:
                gc_keep = int(argv[i + 1])
            except ValueError:
                print(f"Invalid --gc-keep: {argv[i + 1]!r}", file=sys.stderr)
                return 1
            i += 2
        elif arg == "--gc-yes":
            gc_yes = True
            i += 1
        elif arg == "--promote-actions":
            # v9.11 / Chapter X: write top-N actions to ROADMAP.md
            # auto-promotion section. Idempotent. LOW + MEDIUM only.
            promote_actions = True
            i += 1
        elif arg == "--promote-top-n" and i + 1 < len(argv):
            try:
                promote_top_n = int(argv[i + 1])
            except ValueError:
                print(f"Invalid --promote-top-n: {argv[i + 1]!r}", file=sys.stderr)
                return 1
            if promote_top_n < 1 or promote_top_n > 20:
                print(f"--promote-top-n must be 1..20 (got {promote_top_n})",
                      file=sys.stderr)
                return 1
            i += 2
        elif arg in ("-h", "--help"):
            print(__doc__)
            print()
            print("Usage (v9.04):")
            print("  python -m polaris_hydra.host                       "
                  "# all watchers, text output")
            print("  python -m polaris_hydra.host --watcher schema       "
                  "# one watcher")
            print("  python -m polaris_hydra.host --json                 "
                  "# JSON output (audit trail)")
            print("  python -m polaris_hydra.host --query \"…\"            "
                  "# focused synthesis")
            print("  python -m polaris_hydra.host --full                 "
                  "# hybrid: gather+correlate+actions+pheromone")
            print("  python -m polaris_hydra.host --actions              "
                  "# just the ranked action queue")
            print("  python -m polaris_hydra.host --full --save          "
                  "# archive to journal/hydra/ + compute delta")
            print("  python -m polaris_hydra.host --full --diff <path>   "
                  "# delta vs explicit prior brief")
            print("  python -m polaris_hydra.host --pheromone-window-hours 12 "
                  "# override 6h default")
            print("  python -m polaris_hydra.host --deterministic         "
                  "# force deterministic (ignore ANTHROPIC_API_KEY) — v9.05")
            print("  python -m polaris_hydra.host --full --promote-actions "
                  "# auto-promote top-N actions to ROADMAP.md (v9.11)")
            print("  python -m polaris_hydra.host --full --promote-actions --promote-top-n 3 "
                  "# limit to top 3")
            return 0
        else:
            print(f"Unknown argument: {arg}", file=sys.stderr)
            return 1

    # v9.09 / H — --gc mode is independent of Hydra invocation.
    if mode_gc:
        return _cli_gc(gc_keep, gc_yes)

    try:
        hydra = Hydra(watchers=selected)
    except Exception as exc:  # noqa: BLE001
        print(f"HYDRA failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1

    # v9.04 modes (+ v9.05 force_deterministic)
    if mode_full or mode_actions or save or diff_path is not None:
        try:
            brief = hydra.speak_full(
                query=query,
                save=save,
                diff_against=diff_path,
                pheromone_window_hours=pheromone_window_hours,
                force_deterministic=force_deterministic,
            )
        except Exception as exc:  # noqa: BLE001
            print(f"HYDRA --full failed: {type(exc).__name__}: {exc}",
                  file=sys.stderr)
            return 1
        if emit_json:
            print(json.dumps(brief.to_dict(), indent=2, sort_keys=False))
        elif mode_actions:
            _print_actions(brief)
        else:
            _print_full(brief)

        # v9.11 / Chapter X — auto-promote top-N actions to ROADMAP.md
        # if --promote-actions was passed. Idempotent; LOW + MEDIUM only.
        if promote_actions:
            from polaris_hydra.action_promotion import promote_actions as _promote
            try:
                result = _promote(brief.actions, top_n=promote_top_n)
                print()
                print(f"AUTO-PROMOTION: {result.summary_line()}")
                if result.promoted_ids:
                    print(f"  Promoted IDs: {', '.join(result.promoted_ids)}")
                    print(f"  See: ROADMAP.md §\"Auto-promoted action candidates\"")
            except Exception as exc:  # noqa: BLE001
                print(f"AUTO-PROMOTION failed: {type(exc).__name__}: {exc}",
                      file=sys.stderr)
                # Don't fail the whole run; promotion is supplementary

        return 0

    # Default mode (existing v8.37 path)
    try:
        synthesis = hydra.speak(
            query=query, force_deterministic=force_deterministic
        )
    except Exception as exc:  # noqa: BLE001
        print(f"HYDRA failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1

    if emit_json:
        print(json.dumps(synthesis.to_dict(), indent=2, sort_keys=False))
    else:
        print(synthesis.voice)
    return 0


def _cli_gc(keep: int, yes: bool) -> int:
    """v9.09 / H — journal/hydra/ rotation.

    Lists briefs older than the most-recent `keep` count + asks operator
    to confirm purge. C1 preserved: brief-archive is filesystem AoR per
    v8.20; no auto-purge without explicit confirmation. With `--gc-yes`
    the operator pre-authorizes (e.g., for cron use); the script still
    prints exactly what it purged.
    """
    from polaris_hydra.brief_archive import list_prior_briefs
    briefs = list_prior_briefs(_REPO_ROOT)
    n = len(briefs)
    print(f"═══ HYDRA brief-archive GC ═══")
    print(f"  Total briefs: {n}")
    print(f"  Keep most-recent: {keep}")
    if n <= keep:
        print(f"  → nothing to purge ({n} ≤ {keep})")
        return 0
    # Briefs are sorted oldest → newest by list_prior_briefs.
    to_purge = briefs[: n - keep]
    print(f"  → {len(to_purge)} brief(s) eligible for purge:")
    for p in to_purge[:10]:
        print(f"    - {p.name}")
    if len(to_purge) > 10:
        print(f"    … and {len(to_purge) - 10} more")
    if not yes:
        print()
        print("  Pass --gc-yes to confirm purge. C1 preserved by")
        print("  this confirmation gate (filesystem AoR per v8.20).")
        return 0
    # Operator-confirmed: purge
    purged = 0
    for p in to_purge:
        try:
            p.unlink()
            purged += 1
        except OSError as exc:
            print(f"    ! could not purge {p.name}: {exc}", file=sys.stderr)
    print(f"  ✓ purged {purged} brief(s); kept {n - purged} most-recent.")
    return 0


def _print_full(brief: HybridIntelligenceBrief) -> None:
    """Render the hybrid-intelligence brief as text."""
    print(brief.synthesis.voice)
    print()
    print("═══ V. SWARM SUBSTRATE (Pheromone snapshot) ═══")
    snap = brief.pheromone_snapshot
    print(f"  status: {snap.status}; window: {snap.window_hours}h")
    print(f"  commanders: {snap.commander_count}; "
          f"soldiers: {snap.soldier_count}")
    silent = snap.silent_soldier_classes
    if silent:
        print(f"  silent_soldier_classes: {silent}")
    if snap.recent_alerts:
        print(f"  recent_alerts: {len(snap.recent_alerts)} "
              f"(showing first 3)")
        for r in snap.recent_alerts[:3]:
            print(f"    - `{r.deposited_by}` node=`{r.node_id}` "
                  f"intensity={r.intensity:.2f}")
    print()
    print("═══ VI. CROSS-WATCHER CORRELATIONS ═══")
    if not brief.correlations:
        # v9.09 / C — silence instrumentation.
        # 0 correlations is ambiguous: is the engine broken, or the
        # substrate just clean? Show WHY by counting node_ids per
        # watcher and surfacing the disjoint-set status.
        from collections import defaultdict
        watchers_with_node_ids: dict = defaultdict(set)
        for report in brief.synthesis.reports:
            for finding in report.findings:
                ev = finding.evidence or {}
                node_id = ev.get("node_id") or ev.get("node") or ev.get("route") or ev.get("endpoint")
                if isinstance(node_id, str) and node_id:
                    watchers_with_node_ids[report.watcher_name].add(node_id)
        print("  (no correlations)")
        if watchers_with_node_ids:
            n_watchers = len(watchers_with_node_ids)
            total_unique_nodes = len({n for s in watchers_with_node_ids.values() for n in s})
            from collections import Counter
            node_freq = Counter(n for s in watchers_with_node_ids.values() for n in s)
            shared = [n for n, count in node_freq.items() if count >= 2]
            print(f"  Strategy 1 (node_id match): 0 correlations across "
                  f"{n_watchers} watcher(s) emitting node_ids "
                  f"({total_unique_nodes} unique node(s); "
                  f"{len(shared)} shared by ≥2 watchers)")
            # Strategy 2 (domain): count unique colon-prefixes
            domain_freq = Counter(
                n.split(':', 1)[0] for s in watchers_with_node_ids.values()
                for n in s if ':' in n
            )
            shared_domains = [d for d, c in domain_freq.items() if c >= 3]
            print(f"  Strategy 2 (domain match):  0 correlations across "
                  f"{len(domain_freq)} domain(s); "
                  f"{len(shared_domains)} shared by ≥3 watchers")
            print(f"  → all watchers reported on disjoint node_ids; "
                  f"correlation requires overlap. (Sanctum-class question: "
                  f"sanctum/2026-05-15-watcher-node-id-alignment.md if open)")
        else:
            print("  → no watcher emitted any node_id this pass; "
                  "correlation engine had no input")
    else:
        for c in brief.correlations[:5]:
            print(f"  [{c.severity.upper():5s}] {c.title}")
            print(f"          watchers: {', '.join(c.contributing_watchers)}; "
                  f"score: {c.score:.1f}")
    print()
    print("═══ VII. RANKED ACTIONS (top 10) ═══")
    if not brief.actions:
        print("  (no actions proposed)")
    else:
        for i, a in enumerate(brief.actions[:10], 1):
            print(f"  {i:2d}. [{a.risk_class}/{a.effort_estimate}] "
                  f"{a.title}  (score={a.score:.1f})")
            print(f"      {a.rationale[:200]}"
                  f"{'…' if len(a.rationale) > 200 else ''}")
    print()
    if brief.archive_path:
        print(f"═══ VIII. ARCHIVED ═══")
        print(f"  → {brief.archive_path}")
    if brief.delta:
        print()
        print("═══ IX. DELTA vs PRIOR BRIEF ═══")
        d = brief.delta
        if d.is_empty():
            print(f"  (no delta vs {d.prior_path})")
        else:
            print(f"  prior: {d.prior_path}")
            if d.new_findings:
                print(f"  + {len(d.new_findings)} new finding(s):")
                for t in d.new_findings[:5]:
                    print(f"    + {t}")
            if d.closed_findings:
                print(f"  - {len(d.closed_findings)} closed finding(s):")
                for t in d.closed_findings[:5]:
                    print(f"    - {t}")
            if d.new_actions:
                print(f"  + {len(d.new_actions)} new action(s):")
                for t in d.new_actions[:5]:
                    print(f"    + {t}")
            if d.closed_actions:
                print(f"  - {len(d.closed_actions)} closed action(s):")
                for t in d.closed_actions[:5]:
                    print(f"    - {t}")
        # v9.09 / B — Section X: persistent findings + actions.
        # The missing symmetry: items present in BOTH prior and current
        # are *stuck*. Operator never acted, OR unactionable, OR
        # permanent state. Different signal than new/closed.
        if d.persistent_findings or d.persistent_actions:
            print()
            print("═══ X. PERSISTENT (across last 2 briefs) ═══")
            if d.persistent_findings:
                print(f"  ◇ {len(d.persistent_findings)} persistent finding(s):")
                for t in d.persistent_findings[:5]:
                    print(f"    ◇ {t}")
            if d.persistent_actions:
                print(f"  ◇ {len(d.persistent_actions)} persistent action(s) "
                      f"(stuck in queue; consider: act, defer formally, "
                      f"or accept):")
                for t in d.persistent_actions[:5]:
                    print(f"    ◇ {t}")


def _print_actions(brief: HybridIntelligenceBrief) -> None:
    """Render JUST the ranked action queue, for --actions mode."""
    print("═══ HYDRA ranked action queue (v9.04) ═══")
    print(f"  Generated: "
          f"{brief.synthesis.generated_at.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Source: "
          f"{len(brief.synthesis.reports)} watcher report(s) + "
          f"{len(brief.correlations)} correlation(s)")
    print()
    if not brief.actions:
        print("  (no actions proposed; the swarm is quiet)")
        return
    for i, a in enumerate(brief.actions, 1):
        print(f"  {i:2d}. [{a.risk_class}/{a.effort_estimate}] {a.title}")
        print(f"      score: {a.score:.1f}  "
              f"source: {a.source_kind} via "
              f"{', '.join(a.source_watchers)}")
        if a.constitutional_constraints_touched:
            print(f"      touches: "
                  f"{', '.join(a.constitutional_constraints_touched)}")
        print(f"      rationale: {a.rationale}")
        print()


if __name__ == "__main__":
    sys.exit(_cli(sys.argv[1:]))
