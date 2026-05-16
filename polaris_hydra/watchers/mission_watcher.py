"""MissionWatcher — H5 of Arc D.

Monitors Polaris's mission state from the cognitive layer:

  1. Done-list rollup — parses MISSION.md and counts ✅ / ⬜ / ✗
     across v1 (items 1–15), v2 (M2-1..M2-12), and Arc D (H1..H8).
     Reports concrete numbers and flags arithmetic that doesn't add
     up (e.g., v1 ✅ + ⬜ + ✗ ≠ 15).
  2. Steady-state declaration — verifies the v8.31 marker
     "Resolved 2026-05-12: steady-state" is still in MISSION.md.
     Removal of that marker = boundary crossing of constitutional
     significance.
  3. Stale ⬜ detection — any pending mission item that's been
     visible for > 7 days without a journal mention is a candidacy
     signal (either ship it or retire it).
  4. Arc consistency — checks that the open arc (Arc D) has at
     least one ⬜ item OR all items are ✅ (no contradictory state
     like "arc is active but everything is done — needs explicit
     closure ship").

Read-only. Parses MISSION.md + journal/*.md text. No DB, no LLM.
"""

from __future__ import annotations

import datetime
import pathlib
import re
from typing import Any

from .base import Finding, Watcher, WatcherReport


# Threshold: how long a ⬜ item can sit visible before it becomes a
# drift signal. 7 days matches the post-v2 cadence — most ships land
# within a session-or-two, so a week-old ⬜ is worth surfacing.
STALE_PENDING_DAYS = 7

# The post-v2 steady-state marker. Removal = constitutional drift.
STEADY_STATE_MARKER = "Resolved 2026-05-12: steady-state"

# Expected done-list anchor strings. Watcher confirms each section's
# header exists; missing = MISSION drift.
EXPECTED_SECTIONS = {
    "v1": "v1 done-list",
    "v2": "v2 done-list",
    "ArcD": "Arc D",
}


class MissionWatcher(Watcher):
    name = "mission"
    domain = "MISSION done-list rollup + steady-state boundary + stale items"

    def _observe(self) -> WatcherReport:
        repo_root = self._repo_root()
        findings: list[Finding] = []
        evidence: dict[str, Any] = {}

        mission_path = repo_root / "MISSION.md"
        if not mission_path.is_file():
            findings.append(Finding(
                severity="alert",
                title="MISSION.md missing",
                detail=("MISSION.md is not present. The constitution is "
                        "load-bearing for the entire cognitive layer; "
                        "without it, no mission state can be verified."),
                evidence={"path": str(mission_path)},
            ))
            return WatcherReport(
                watcher_name=self.name, domain=self.domain,
                status="alert", findings=findings,
                evidence_summary={"mission_md_present": False},
            )

        mission_text = mission_path.read_text(errors="replace")
        evidence["mission_md_present"] = True

        # ---- 1. Done-list rollup -----------------------------------------
        v1_done, v1_pending, v1_retired = self._count_v1(mission_text)
        v2_done, v2_pending = self._count_v2(mission_text)
        arc_d_done, arc_d_pending = self._count_arc_d(mission_text)
        evidence["v1_done"] = v1_done
        evidence["v1_pending"] = v1_pending
        evidence["v1_retired"] = v1_retired
        evidence["v1_total"] = v1_done + v1_pending + v1_retired
        evidence["v2_done"] = v2_done
        evidence["v2_pending"] = v2_pending
        evidence["v2_total"] = v2_done + v2_pending
        evidence["arc_d_done"] = arc_d_done
        evidence["arc_d_pending"] = arc_d_pending
        evidence["arc_d_total"] = arc_d_done + arc_d_pending

        # v1 should sum to 15 items (the historical SCS-230 done-list).
        if evidence["v1_total"] != 15 and evidence["v1_total"] > 0:
            findings.append(Finding(
                severity="alert",
                title=f"v1 done-list arithmetic broken: {evidence['v1_total']} items, expected 15",
                detail=("v1 was historically 15 items (12 ✅ + 3 ✗ retired). "
                        "A different total means the list was edited "
                        "without audit-of-record discipline. Inspect "
                        "MISSION.md §'v1 done-list'."),
                evidence={"counted": evidence["v1_total"],
                          "expected": 15,
                          "done": v1_done, "pending": v1_pending,
                          "retired": v1_retired},
            ))

        # v2 should sum to 12 (M2-1..M2-12).
        if evidence["v2_total"] != 12 and evidence["v2_total"] > 0:
            findings.append(Finding(
                severity="alert",
                title=f"v2 done-list arithmetic broken: {evidence['v2_total']} items, expected 12",
                detail=("v2 mission has 12 items (M2-1..M2-12). A different "
                        "total means the list was edited; inspect "
                        "MISSION.md §'v2 done-list'."),
                evidence={"counted": evidence["v2_total"],
                          "expected": 12,
                          "done": v2_done, "pending": v2_pending},
            ))

        # ---- 2. Steady-state declaration ---------------------------------
        steady_state_in_force = STEADY_STATE_MARKER in mission_text
        evidence["steady_state_in_force"] = steady_state_in_force
        if not steady_state_in_force:
            findings.append(Finding(
                severity="alert",
                title="steady-state marker removed from MISSION",
                detail=(f"The v8.31 marker '{STEADY_STATE_MARKER}' is "
                        f"missing from MISSION.md. The post-v2 contract "
                        f"that gates new mission scope is no longer "
                        f"recorded as in force. Either re-add it or open "
                        f"a Sanctum to formally revoke."),
                evidence={"marker": STEADY_STATE_MARKER},
            ))

        # ---- 3. Expected section anchors ---------------------------------
        missing_sections = [
            label for label, anchor in EXPECTED_SECTIONS.items()
            if anchor not in mission_text
        ]
        evidence["mission_sections_missing"] = missing_sections
        if missing_sections:
            findings.append(Finding(
                severity="alert",
                title="MISSION.md section anchor missing",
                detail=("One or more expected MISSION.md done-list section "
                        "anchors are absent. The done-list rollup may be "
                        "undercounting because the watcher couldn't find "
                        "the section."),
                evidence={"missing_anchors": missing_sections},
            ))

        # ---- 4. Stale ⬜ items --------------------------------------------
        stale_items = self._stale_pending_items(
            repo_root, mission_text, v1_pending, v2_pending, arc_d_pending,
        )
        evidence["stale_pending_count"] = len(stale_items)
        evidence["stale_pending_threshold_days"] = STALE_PENDING_DAYS
        if stale_items:
            findings.append(Finding(
                severity="drift",
                title=f"{len(stale_items)} pending item(s) without recent journal mention",
                detail=(f"Mission items with ⬜ status that have no "
                        f"reference in any journal entry from the last "
                        f"{STALE_PENDING_DAYS} days. Either pick one up "
                        f"or surface why it's frozen. Under the v8.31 "
                        f"steady-state contract, leaving ⬜ items "
                        f"unmentioned is the slippage pattern."),
                evidence={"items": stale_items[:10]},
            ))

        # ---- 5. Arc-D consistency ----------------------------------------
        # Arc D opened + closed 2026-05-12 with H1..H8 all ✅.
        # Pre-v8.45 this finding emitted a "ship H8 now" prompt whenever
        # arc_d_pending == 0; that was correct between v8.42 (H7 done,
        # H8 still ⬜) and v8.43 (H8 ✅). After v8.43 the prompt became
        # permanently stale. v8.45 fix: the finding is now an Arc-state
        # info-only emit that distinguishes "ready to close" from
        # "closed", using the constitutional-integration Sanctum's
        # presence as the closure marker.
        if evidence["arc_d_total"] > 0 and arc_d_pending == 0:
            sanctum_dir = self._repo_root() / "sanctum"
            h8_closer = sanctum_dir / (
                "2026-05-12-hydra-constitutional-integration.md")
            arc_closed = h8_closer.exists()
            if arc_closed:
                findings.append(Finding(
                    severity="info",
                    title="Arc D done-list fully ✅ — arc closed",
                    detail=(f"All {evidence['arc_d_total']} Arc D items "
                            f"are complete and the constitutional-"
                            f"integration Sanctum is in the index. "
                            f"No action needed; steady-state holds."),
                    evidence={"arc_d_done": arc_d_done,
                              "arc_closed": True},
                ))
            else:
                findings.append(Finding(
                    severity="info",
                    title="Arc D done-list fully ✅ — closer pending",
                    detail=("All Arc D items are complete on disk but "
                            "the constitutional-integration Sanctum "
                            "is not yet in the index. This is the "
                            "moment for the H8 closing ship (Phase 3)."),
                    evidence={"arc_d_done": arc_d_done,
                              "arc_closed": False},
                ))

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
                title="mission state healthy",
                detail=(f"v1: {v1_done} ✅ + {v1_retired} ✗ retired + "
                        f"{v1_pending} ⬜ = 15 total. "
                        f"v2: {v2_done} ✅ + {v2_pending} ⬜ = 12 total. "
                        f"Arc D: {arc_d_done} ✅ + {arc_d_pending} ⬜ = "
                        f"{evidence['arc_d_total']} total. Steady-state "
                        f"declaration in force. No stale ⬜ items."),
                evidence={
                    "v1_done": v1_done, "v2_done": v2_done,
                    "arc_d_done": arc_d_done,
                    "steady_state": steady_state_in_force,
                },
            ))

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

    def _count_v1(self, text: str) -> tuple[int, int, int]:
        """Count v1 done-list items.

        v1 items use plain numeric prefixes (1., 2., …, 15.). The
        status emoji follows the number. We split the file into
        sections and only count within the v1 section.

        Returns (done, pending, retired).
        """
        # Carve out v1 section: from "v1 done-list" header to next "##".
        m = re.search(
            r"### v1 done-list.*?(?=\n###|\n## |\Z)",
            text, flags=re.DOTALL,
        )
        if not m:
            return 0, 0, 0
        section = m.group(0)
        done = len(re.findall(r"^\s*\d+\.\s*✅", section, flags=re.MULTILINE))
        pending = len(re.findall(r"^\s*\d+\.\s*⬜", section, flags=re.MULTILINE))
        retired = len(re.findall(r"^\s*\d+\.\s*(?:✗|⏸)", section,
                                 flags=re.MULTILINE))
        return done, pending, retired

    def _count_v2(self, text: str) -> tuple[int, int]:
        """Count v2 done-list items.

        v2 items use the M2-N prefix. Status emoji follows.

        Returns (done, pending).
        """
        m = re.search(
            r"### v2 done-list.*?(?=\n###|\n## |\Z)",
            text, flags=re.DOTALL,
        )
        if not m:
            return 0, 0
        section = m.group(0)
        done = len(re.findall(r"^\s*M2-\d+\.\s*✅", section,
                              flags=re.MULTILINE))
        pending = len(re.findall(r"^\s*M2-\d+\.\s*⬜", section,
                                 flags=re.MULTILINE))
        return done, pending

    def _count_arc_d(self, text: str) -> tuple[int, int]:
        """Count Arc D done-list items.

        Arc D items use the H<N>. prefix (H1., H2., …, H8.).

        Returns (done, pending).
        """
        m = re.search(
            r"### Arc D.*?(?=\n###|\n## |\Z)",
            text, flags=re.DOTALL,
        )
        if not m:
            return 0, 0
        section = m.group(0)
        done = len(re.findall(r"^H\d+\.\s*✅", section, flags=re.MULTILINE))
        pending = len(re.findall(r"^H\d+\.\s*⬜", section,
                                 flags=re.MULTILINE))
        return done, pending

    def _stale_pending_items(
        self,
        repo_root: pathlib.Path,
        mission_text: str,
        v1_pending: int,
        v2_pending: int,
        arc_d_pending: int,
    ) -> list[dict[str, Any]]:
        """Find ⬜ items absent from recent journal entries.

        A ⬜ item's identifier (e.g. "M2-7", "H4") is the key. If the
        identifier doesn't appear in any journal entry from the last
        STALE_PENDING_DAYS, the item is stale.
        """
        if v1_pending + v2_pending + arc_d_pending == 0:
            return []  # nothing pending; nothing can be stale

        # Extract pending-item identifiers from MISSION.md.
        pending_ids: list[str] = []
        # v1: line starts with a number then ⬜
        for m in re.finditer(
            r"^(\d+)\.\s*⬜\s+(.+?)$", mission_text, flags=re.MULTILINE
        ):
            pending_ids.append(f"v1-item-{m.group(1)}")
        for m in re.finditer(
            r"^(M2-\d+)\.\s*⬜", mission_text, flags=re.MULTILINE
        ):
            pending_ids.append(m.group(1))
        for m in re.finditer(
            r"^(H\d+)\.\s*⬜", mission_text, flags=re.MULTILINE
        ):
            pending_ids.append(m.group(1))

        if not pending_ids:
            return []

        # Load recent journal entries + ROADMAP (last STALE_PENDING_DAYS).
        # ROADMAP counts as a "recent mention" source because items
        # described there with acceptance criteria are *scheduled*, not
        # *forgotten*. The stale check is meant to catch ⬜ items that
        # have fallen off the radar entirely, not items in active
        # planning.
        cutoff = (datetime.datetime.now()
                  - datetime.timedelta(days=STALE_PENDING_DAYS)).timestamp()
        recent_text = ""

        journal_dir = repo_root / "journal"
        if journal_dir.is_dir():
            for entry in journal_dir.glob("*.md"):
                try:
                    if entry.stat().st_mtime >= cutoff:
                        recent_text += entry.read_text(errors="replace")
                except OSError:
                    pass

        roadmap_path = repo_root / "ROADMAP.md"
        if roadmap_path.is_file():
            try:
                if roadmap_path.stat().st_mtime >= cutoff:
                    recent_text += roadmap_path.read_text(errors="replace")
            except OSError:
                pass

        stale: list[dict[str, Any]] = []
        for ident in pending_ids:
            # v1-item-N is a synthesized key; check the readable form too.
            search_key = ident.replace("v1-item-", "v1 item ")
            if search_key not in recent_text and ident not in recent_text:
                stale.append({"id": ident})
        return stale
