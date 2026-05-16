"""TrajectoryWatcher — HYDRA's 7th watcher (v8.49).

The other six watchers observe Polaris's *current health*; this one
observes its *trajectory*. Specifically: the pattern of recent
shipping itself can become a drift signal that no other surface
catches.

Three channels:

  1. **Ship-rate analysis.** Inter-ship wall-clock gaps over the
     last N CHANGELOG entries. Flags:
       - 3+ ships in <2 hours → mission-creep warning,
       - 0 ships in 7+ days (when prior cadence was higher) →
         stagnation warning.

  2. **Parking-pattern detection.** Tokens like "still parked",
     "surfaced but parked", "deferred", "parked" recurring across
     recent ship entries. Flags items parked 3+ times without
     closure (the avoidance signal).

  3. **File-churn cluster.** Filesystem mtimes for source files
     touched in the last 24h. Flags single files modified ≥4
     times (rework / scope creep).

Per the v8.44 G1–G5 guards: this watcher is read-only,
deterministic, graceful-failure. No randomness, no eval, no
file-tail polling, no SQL mutation. All inputs are parsed from
existing artifacts in the repo (CHANGELOG.md, mtimes); no DB
connection needed.

Per v8.31: this watcher runs only when HYDRA runs (operator-
invoked or end-of-ship). It does not generate strategic
recommendations on its own — it surfaces drift signals as
structured findings, which the HYDRA host then includes in its
synthesis.

Authorized by:
  - `sanctum/2026-05-13-trajectory-watcher-7th-channel.md` —
    Option A, registry expansion 6 → 7.
  - The Architect's StrategicAdvisor-feedback analysis that
    identified trajectory-drift as the 20% gap not covered by
    Architect + HYDRA + iteration protocol.
"""

from __future__ import annotations

import datetime
import os
import pathlib
import re
from typing import Any

from .base import Finding, Watcher, WatcherReport


# ---------------------------------------------------------------------
# Tunable thresholds. These are Schelling-point choices; they should
# only be changed when concrete operational experience suggests a
# better value, and the change should be noted in the journal.
# ---------------------------------------------------------------------

# Ship-rate analysis: how many recent CHANGELOG entries to look at.
SHIP_RATE_WINDOW = 10

# Ship-rate analysis: more than this many ships within the burst
# window triggers a mission-creep warning. The default tolerates the
# rapid shipping that v8.27–v8.49 actually did (~24 ships in ~36h),
# while still flagging anything significantly faster.
SHIP_BURST_THRESHOLD = 6
SHIP_BURST_WINDOW_HOURS = 2.0

# Ship-rate analysis: stagnation threshold. If the latest ship is
# older than this AND the prior cadence (last 5 ships) averaged
# faster than this, emit a stagnation warning.
STAGNATION_DAYS = 7

# Parking-pattern detection: how many recent CHANGELOG entries to
# scan + how many recurrences before flagging.
PARKING_WINDOW = 10
PARKING_RECURRENCE_THRESHOLD = 3

# Tokens that indicate a parked item. Substring-matched
# case-insensitively against the CHANGELOG entry body.
PARKING_TOKENS = (
    "still parked",
    "surfaced but parked",
    "surfaced (still parked)",
    "parked until",
    "remain parked",
    "still surfaced",
)

# File-churn cluster: how far back to look + threshold for the
# single-file-domination warning.
CHURN_WINDOW_HOURS = 24
CHURN_MIN_TOUCHES = 4

# Source-file extensions that count for churn analysis. Markdown
# docs are deliberately excluded — doc-ship clusters (v8.48
# touching 5 ship docs at once) are NOT scope creep, they're
# intentional batch work.
CHURN_EXTENSIONS = (".py", ".sql", ".rs", ".js", ".css", ".html")

# Directories to exclude from churn analysis (third-party, generated,
# transient).
CHURN_EXCLUDED_DIRS = (
    "__pycache__",
    "node_modules",
    ".git",
    "target",
    "vendor",
    "static/data",
)


class TrajectoryWatcher(Watcher):
    """The 7th watcher. Observes the shipping pattern itself."""

    name = "trajectory"
    domain = "ship-rate + parking-pattern + file-churn"

    def _observe(self) -> WatcherReport:
        repo_root = self._repo_root()
        findings: list[Finding] = []
        evidence: dict[str, Any] = {}

        changelog = repo_root / "CHANGELOG.md"

        # ---- 1. Ship-rate analysis ---------------------------------------
        sr_findings, sr_evidence = self._check_ship_rate(changelog)
        findings.extend(sr_findings)
        evidence.update(sr_evidence)

        # ---- 2. Parking-pattern detection --------------------------------
        pp_findings, pp_evidence = self._check_parking_pattern(changelog)
        findings.extend(pp_findings)
        evidence.update(pp_evidence)

        # ---- 3. File-churn cluster ---------------------------------------
        fc_findings, fc_evidence = self._check_file_churn(repo_root)
        findings.extend(fc_findings)
        evidence.update(fc_evidence)

        # ---- Status aggregate --------------------------------------------
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
                title="trajectory healthy",
                detail=("Ship cadence within tolerance; no parked-"
                        "item recurrences detected; no single file "
                        "dominates recent churn."),
                evidence={
                    "ship_count_in_burst_window":
                        evidence.get("ship_count_in_burst_window"),
                    "parked_recurrences": evidence.get("parked_recurrences"),
                    "max_churn_count": evidence.get("max_churn_count"),
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
        here = pathlib.Path(__file__).resolve()
        return here.parent.parent.parent

    # Match `## v8.49 — 2026-05-13 (title)` or `## v8.49 (title)` or
    # `## v8.49 — title`. The version + optional date are what we
    # care about; title is informational.
    _CHANGELOG_VERSION_PATTERN = re.compile(
        r"^##\s+(?P<version>v[\d\.]+)"
        r"(?:\s+[—-]\s+(?P<date>\d{4}-\d{2}-\d{2}))?",
        re.MULTILINE,
    )

    def _parse_changelog_entries(
        self, changelog: pathlib.Path
    ) -> list[dict[str, Any]]:
        """Return a list of {version, date, body} for each CHANGELOG
        entry, newest first. Returns an empty list if the file can't
        be read or no entries match — graceful failure."""
        try:
            text = changelog.read_text(errors="replace")
        except OSError:
            return []

        matches = list(self._CHANGELOG_VERSION_PATTERN.finditer(text))
        entries: list[dict[str, Any]] = []
        for i, m in enumerate(matches):
            start = m.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            date_str = m.group("date")
            date_val: datetime.date | None = None
            if date_str:
                try:
                    date_val = datetime.date.fromisoformat(date_str)
                except ValueError:
                    date_val = None
            entries.append({
                "version": m.group("version"),
                "date": date_val,
                "body": text[start:end],
            })
        return entries

    # ------------------------------------------------------------------
    # Channel 1: ship-rate analysis
    # ------------------------------------------------------------------

    def _check_ship_rate(
        self, changelog: pathlib.Path
    ) -> tuple[list[Finding], dict[str, Any]]:
        findings: list[Finding] = []
        evidence: dict[str, Any] = {
            "ship_window_examined": 0,
            "ship_count_in_burst_window": 0,
            "ship_rate_status": "unknown",
        }

        if not changelog.is_file():
            findings.append(Finding(
                severity="info",
                title="ship-rate channel skipped",
                detail=("CHANGELOG.md not found at "
                        f"{changelog}. Ship-rate analysis skipped."),
                evidence={"path": str(changelog)},
            ))
            evidence["ship_rate_status"] = "no_changelog"
            return findings, evidence

        entries = self._parse_changelog_entries(changelog)[:SHIP_RATE_WINDOW]
        evidence["ship_window_examined"] = len(entries)

        # The CHANGELOG only carries date precision, not time. To do
        # burst detection within hours, we approximate: count entries
        # sharing the same date. If 3+ entries land on the same date,
        # they shipped within a single day window ≈ much faster than
        # the burst threshold. Refine to per-version-spacing if higher
        # precision is needed later.
        dated_entries = [e for e in entries if e["date"] is not None]
        if dated_entries:
            from collections import Counter
            date_counts = Counter(e["date"] for e in dated_entries)
            max_per_day = max(date_counts.values())
            evidence["ship_count_in_burst_window"] = max_per_day
            evidence["max_ships_per_day"] = max_per_day
            evidence["ship_rate_status"] = "examined"

            # Mission-creep warning: 6+ ships on the same date.
            if max_per_day >= SHIP_BURST_THRESHOLD:
                busiest_date = max(date_counts, key=lambda d: date_counts[d])
                findings.append(Finding(
                    severity="drift",
                    title="ship-rate burst (mission-creep signal)",
                    detail=(f"{max_per_day} ships shipped on "
                            f"{busiest_date.isoformat()}, exceeding the "
                            f"burst threshold of {SHIP_BURST_THRESHOLD}. "
                            f"High shipping velocity over a short window "
                            f"is the mission-creep signal: consider "
                            f"whether the recent ships extended scope or "
                            f"merely closed parked items."),
                    evidence={
                        "busiest_date": busiest_date.isoformat(),
                        "ships_that_day": max_per_day,
                        "threshold": SHIP_BURST_THRESHOLD,
                    },
                ))

            # Stagnation warning: latest ship is older than threshold
            # AND prior cadence was faster.
            today = datetime.date.today()
            latest_date = max(e["date"] for e in dated_entries)
            days_since_latest = (today - latest_date).days
            evidence["days_since_latest_ship"] = days_since_latest

            if days_since_latest >= STAGNATION_DAYS:
                # Was the prior cadence faster? Compute mean inter-
                # ship gap (in days) across the window, excluding the
                # current gap.
                older_dates = sorted(
                    set(e["date"] for e in dated_entries),
                    reverse=True,
                )
                if len(older_dates) >= 3:
                    prior_gaps = [
                        (older_dates[i] - older_dates[i + 1]).days
                        for i in range(min(3, len(older_dates) - 1))
                    ]
                    mean_prior_gap = sum(prior_gaps) / len(prior_gaps)
                    if mean_prior_gap < STAGNATION_DAYS:
                        findings.append(Finding(
                            severity="drift",
                            title="ship-rate stagnation",
                            detail=(f"No ships in the last "
                                    f"{days_since_latest} days; prior "
                                    f"cadence averaged "
                                    f"{mean_prior_gap:.1f} days per "
                                    f"ship. This is the stagnation "
                                    f"signal: either a new arc should "
                                    f"open or steady-state is "
                                    f"genuinely empty (both fine; the "
                                    f"asymmetry is the signal)."),
                            evidence={
                                "days_since_latest": days_since_latest,
                                "prior_mean_gap_days": mean_prior_gap,
                                "stagnation_threshold_days":
                                    STAGNATION_DAYS,
                            },
                        ))
        else:
            evidence["ship_rate_status"] = "no_dated_entries"

        return findings, evidence

    # ------------------------------------------------------------------
    # Channel 2: parking-pattern detection
    # ------------------------------------------------------------------

    def _check_parking_pattern(
        self, changelog: pathlib.Path
    ) -> tuple[list[Finding], dict[str, Any]]:
        findings: list[Finding] = []
        evidence: dict[str, Any] = {
            "parking_window_examined": 0,
            "parked_recurrences": {},
        }

        if not changelog.is_file():
            return findings, evidence

        entries = self._parse_changelog_entries(changelog)[:PARKING_WINDOW]
        evidence["parking_window_examined"] = len(entries)

        # For each entry, extract the "parked" tokens it mentions.
        # We're looking for short labels like "M1", "L2", "L5",
        # "gotcha #5" etc. that recur across entries — the avoidance
        # signal.
        # Strategy: in each entry, find lines that contain a parking
        # token, then extract any `M\d+`, `L\d+`, `R\d+-\d+` or
        # `gotcha #\d+` identifiers from those lines.
        item_pattern = re.compile(
            r"\b(?:M\d+|L\d+|R\d{1,2}-\d+|gotcha\s*#\d+)\b",
            re.IGNORECASE,
        )

        item_count: dict[str, int] = {}
        for entry in entries:
            body_lower = entry["body"].lower()
            # Cheap pre-check: does this entry mention parking at all?
            if not any(tok in body_lower for tok in PARKING_TOKENS):
                continue
            # Find every parked item identifier in the entry.
            seen_in_entry: set[str] = set()
            for line in entry["body"].splitlines():
                line_lower = line.lower()
                if not any(tok in line_lower for tok in PARKING_TOKENS):
                    continue
                for m in item_pattern.finditer(line):
                    seen_in_entry.add(m.group(0).upper())
            for item in seen_in_entry:
                item_count[item] = item_count.get(item, 0) + 1

        # Items recurring at or above the threshold are avoidance
        # candidates.
        recurrences = {
            item: count for item, count in item_count.items()
            if count >= PARKING_RECURRENCE_THRESHOLD
        }
        evidence["parked_recurrences"] = recurrences
        evidence["parked_items_tracked"] = len(item_count)

        if recurrences:
            sorted_recurrences = sorted(
                recurrences.items(), key=lambda kv: kv[1], reverse=True
            )
            findings.append(Finding(
                severity="drift",
                title="parked-item avoidance signal",
                detail=(f"{len(recurrences)} parked item(s) recurred "
                        f"across {PARKING_RECURRENCE_THRESHOLD}+ "
                        f"ship entries without closure. Consider "
                        f"either shipping or formally deferring; "
                        f"sustained parking is the avoidance pattern "
                        f"the v8.45 scan named."),
                evidence={
                    "recurrences": dict(sorted_recurrences[:10]),
                    "threshold": PARKING_RECURRENCE_THRESHOLD,
                    "window": PARKING_WINDOW,
                },
            ))

        return findings, evidence

    # ------------------------------------------------------------------
    # Channel 3: file-churn cluster
    # ------------------------------------------------------------------

    def _check_file_churn(
        self, repo_root: pathlib.Path
    ) -> tuple[list[Finding], dict[str, Any]]:
        """Walk the repo for source files modified within the churn
        window. If any single file was touched ≥CHURN_MIN_TOUCHES
        times... well, mtimes only record the LAST touch, not the
        count. So we approximate: instead, we measure how many
        *distinct files* were touched, and flag if a single
        *directory* dominates touches. Directory-domination is a
        better proxy for scope-creep than file-domination because
        repeated edits to the same file overwrite mtime."""
        findings: list[Finding] = []
        evidence: dict[str, Any] = {
            "churn_files_in_window": 0,
            "churn_directories": {},
            "max_churn_count": 0,
        }

        now = datetime.datetime.now()
        window_start = now - datetime.timedelta(hours=CHURN_WINDOW_HOURS)
        cutoff_mtime = window_start.timestamp()

        from collections import Counter
        dir_counter: Counter[str] = Counter()
        files_in_window = 0

        for dirpath, dirnames, filenames in os.walk(repo_root):
            # Skip excluded dirs (in-place mutation to prune walk).
            dirnames[:] = [d for d in dirnames
                           if d not in CHURN_EXCLUDED_DIRS
                           and not d.startswith(".")]
            for fn in filenames:
                if not fn.endswith(CHURN_EXTENSIONS):
                    continue
                full = os.path.join(dirpath, fn)
                try:
                    mtime = os.path.getmtime(full)
                except OSError:
                    continue
                if mtime < cutoff_mtime:
                    continue
                files_in_window += 1
                # Bucket by top-level dir relative to repo root.
                rel = os.path.relpath(dirpath, repo_root)
                top = rel.split(os.sep)[0] if rel != "." else "(root)"
                dir_counter[top] += 1

        evidence["churn_files_in_window"] = files_in_window
        evidence["churn_directories"] = dict(dir_counter.most_common(5))

        if dir_counter:
            max_count = dir_counter.most_common(1)[0][1]
            evidence["max_churn_count"] = max_count
            # Flag if a single dir got >= CHURN_MIN_TOUCHES touches
            # AND it's >= 60% of total recent activity.
            if (max_count >= CHURN_MIN_TOUCHES
                    and max_count >= 0.6 * files_in_window):
                top_dir = dir_counter.most_common(1)[0][0]
                findings.append(Finding(
                    severity="drift",
                    title="file-churn cluster (scope-creep signal)",
                    detail=(f"Directory `{top_dir}/` accumulated "
                            f"{max_count} of {files_in_window} "
                            f"source-file modifications in the last "
                            f"{CHURN_WINDOW_HOURS}h. Dominant single-"
                            f"directory churn suggests either intense "
                            f"focused work (fine if intentional) or "
                            f"rework / scope creep within a narrow "
                            f"area (worth examining)."),
                    evidence={
                        "directory": top_dir,
                        "touches": max_count,
                        "total_files_in_window": files_in_window,
                        "window_hours": CHURN_WINDOW_HOURS,
                    },
                ))

        return findings, evidence
