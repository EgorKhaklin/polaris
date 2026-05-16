"""ForesightAgent — deterministic generator of the 5-section brief.

Single agent type per Position B. Reads:
  - CHANGELOG.md (last 30 ## v entries)
  - ROADMAP.md (current state + auto-promotion section)
  - meta/sanctum-index.md (last 30)
  - journal/ (last 30 days, decisions only)
  - meta/polaris-self-roadmap-*.md (macro re-scans, all)
  - external_categories.txt (operator-curated; no fetches)
  - MISSION.md §"Vocation" (the seven anti-coercion primitives)
  - Optional: SQL helpers from polaris_sql/14_foresight_helpers.sql
    (called when a DB connection is available; gracefully no-ops
    otherwise)

The agent is deterministic over local state. It does NOT fetch external
URLs. It does NOT call LLMs. (LLM enrichment is intentionally NOT
included in v9.12 to keep the surface minimum-viable; future Sanctum
may add it if the empirical-graduation threshold is met.)

Constitutional contract:
  - C1 / G1: read-only against all inputs
  - Sanctum protocol: Position B prevents bypassing into a subsystem
  - Vocation alignment: §IV enforcement is structural via Brief class
  - Sunset clause: agent reads acceptance log + emits warning when
    threshold breach detected
"""

from __future__ import annotations

import datetime
import json
import os
import pathlib
import re
from typing import Any, Optional

from polaris_foresight.brief import Brief, BriefSection


_REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent

# Anti-coercion primitives named in MISSION.md §"Vocation". The
# ForesightAgent flags these as Layer-1 surfaces whose absence-from-
# recent-CHANGELOG-mentions constitutes a vocation gap.
ANTI_COERCION_PRIMITIVES: tuple[str, ...] = (
    "TokenSignature",
    "multi-signature migration",
    "WebAuthn-MFA",
    "federation trust graph",
    "redaction-proof",
    "audit-of-record",
    "duress-code",
)

# Sunset clause threshold (per Anti-Architect modification §IV.2).
SUNSET_BRIEFS_REQUIRED = 6
SUNSET_ACCEPTANCE_THRESHOLD = 0.50  # 50%

# Patterns to detect "surprise" in CHANGELOG body (§I)
SURPRISE_MARKERS = (
    "didn't expect", "did not expect", "unexpectedly", "surprising",
    "surprisingly", "to our surprise", "outcome diverged", "what we found",
    "turned out", "actually was", "ended up being", "the truth was",
)


class ForesightAgent:
    """Deterministic generator of the foresight Brief."""

    def __init__(
        self,
        repo_root: Optional[pathlib.Path] = None,
        today: Optional[datetime.date] = None,
    ):
        self.repo_root = repo_root or _REPO_ROOT
        self.today = today or datetime.date.today()
        self._cache: dict[str, Any] = {}

    # ----- Inputs ---------------------------------------------------

    def _read(self, rel: str) -> str:
        path = self.repo_root / rel
        if not path.exists():
            return ""
        return path.read_text(encoding="utf-8", errors="replace")

    def _changelog(self) -> str:
        return self._read("CHANGELOG.md")

    def _roadmap(self) -> str:
        return self._read("ROADMAP.md")

    def _sanctum_index(self) -> str:
        return self._read("meta/sanctum-index.md")

    def _macro_rescans(self) -> list[tuple[str, str]]:
        """Return list of (filename, body) for all polaris-self-roadmap-* docs."""
        meta = self.repo_root / "meta"
        if not meta.is_dir():
            return []
        out = []
        for path in sorted(meta.glob("polaris-self-roadmap*.md")):
            out.append((path.name, path.read_text(encoding="utf-8", errors="replace")))
        return out

    def _external_categories(self) -> list[str]:
        """Read operator-curated external-category list. Lines starting
        with `#` are comments. Empty lines skipped."""
        text = self._read("polaris_foresight/external_categories.txt")
        return [
            line.strip() for line in text.splitlines()
            if line.strip() and not line.strip().startswith("#")
        ]

    def _journal_recent_decisions(self, days: int = 30) -> list[str]:
        """Return recent journal decision lines."""
        jdir = self.repo_root / "journal"
        if not jdir.is_dir():
            return []
        cutoff = self.today - datetime.timedelta(days=days)
        out = []
        for path in sorted(jdir.glob("*.md")):
            stem = path.stem
            try:
                d = datetime.date.fromisoformat(stem)
            except ValueError:
                continue
            if d < cutoff:
                continue
            for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
                if line.startswith("- **decision**"):
                    out.append(line)
        return out

    def _acceptance_log(self) -> dict[str, Any]:
        """Read the empirical-graduation tracker."""
        path = self.repo_root / "polaris_foresight" / "_acceptance_log.json"
        if not path.exists():
            return {"briefs": [], "candidates": {}}
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {"briefs": [], "candidates": {}}

    # ----- Section generators ---------------------------------------

    def _section_i_surprises(self) -> BriefSection:
        """§I — What we shipped that surprised us.

        Two signals:
        1. CHANGELOG entries containing surprise markers in body
        2. Sanctum §VI Outcomes that diverge from §V Decisions
           (heuristic: §VI mentions "did not", "however", "instead")
        """
        body = []
        citations = []
        cl = self._changelog()
        # Slice last 30 entries
        entries = re.split(r"^## v[0-9]+\.[0-9]+", cl, flags=re.MULTILINE)[:31]
        for i, entry in enumerate(entries[:10]):  # only last 10 to bound work
            if not entry.strip():
                continue
            lower = entry.lower()
            for marker in SURPRISE_MARKERS:
                if marker in lower:
                    # Extract version from entry header (preceding line)
                    # by finding nearest preceding "## v" in original
                    # text — for simplicity, just note "recent CHANGELOG"
                    excerpt = entry[lower.index(marker):lower.index(marker) + 200]
                    body.append(f"- CHANGELOG surprise marker (`{marker}`): {excerpt[:120]}...")
                    citations.append(f"CHANGELOG.md (entry #{i+1})")
                    break
        # Sanctum divergence: scan recent sanctums for §VI containing
        # "however" or "actually" — divergence from §V intent
        sanctum_dir = self.repo_root / "sanctum"
        if sanctum_dir.is_dir():
            recent_sanctums = sorted(
                sanctum_dir.glob("*.md"),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )[:10]
            for s in recent_sanctums:
                content = s.read_text(encoding="utf-8", errors="replace")
                # Find §VI section
                m = re.search(r"## VI\..*?(?=^## VII\.|\Z)", content, re.MULTILINE | re.DOTALL)
                if not m:
                    continue
                section_text = m.group(0)
                if any(kw in section_text.lower() for kw in
                       ("however", "actually", "diverged", "ended up")):
                    body.append(f"- Sanctum outcome divergence: `{s.name}`")
                    citations.append(f"sanctum/{s.name}")
        if not body:
            body.append("- No surprise signals in current cycle (CHANGELOG + Sanctum §VI).")
        return BriefSection(
            heading="I — What we shipped that surprised us",
            body_lines=body[:10],
            citations=list(dict.fromkeys(citations))[:10],
        )

    def _section_ii_perpetual_deferrals(self) -> BriefSection:
        """§II — What we keep almost-shipping but never quite do.

        Find items mentioned in 3+ macro-rescans that remain deferred.
        Heuristic: words like "deferred", "RESERVED", "Phase 2", "Phase 3",
        "future ship", appearing across multiple macro-rescan docs.
        """
        body = []
        citations = []
        rescans = self._macro_rescans()
        if len(rescans) < 2:
            body.append(
                f"- Insufficient macro-rescans for perpetual-deferral detection "
                f"(found {len(rescans)}, need ≥2). Run macro re-scan more often "
                f"to enable §II signal."
            )
            return BriefSection(
                heading="II — What we keep almost-shipping but never quite do",
                body_lines=body,
                citations=[fname for fname, _ in rescans],
            )

        # Extract deferred-item phrases from each rescan
        deferred_per_scan: list[set[str]] = []
        for fname, body_text in rescans:
            seen: set[str] = set()
            for m in re.finditer(
                r"([A-Z][^.]{20,100}?(?:deferred|RESERVED|Phase [23]|future ship|next ship))",
                body_text,
            ):
                phrase = m.group(1).strip()
                # Normalize whitespace
                phrase = re.sub(r"\s+", " ", phrase)
                seen.add(phrase[:80])  # truncate
            deferred_per_scan.append(seen)

        # Find phrases appearing in ≥ ceil(N/2) scans (where N = total rescans)
        threshold = max(2, (len(rescans) + 1) // 2)
        all_phrases: dict[str, int] = {}
        for s in deferred_per_scan:
            for p in s:
                all_phrases[p] = all_phrases.get(p, 0) + 1
        perpetual = [
            (p, n) for p, n in all_phrases.items() if n >= threshold
        ]
        perpetual.sort(key=lambda x: -x[1])
        for phrase, count in perpetual[:8]:
            body.append(f"- ({count}x) `{phrase[:80]}...`")
        if not body:
            body.append(
                "- No perpetual-deferral patterns detected (no item appears in "
                f"≥{threshold} of {len(rescans)} macro-rescans)."
            )
        return BriefSection(
            heading="II — What we keep almost-shipping but never quite do",
            body_lines=body,
            citations=[fname for fname, _ in rescans],
        )

    def _section_iii_external_signals(self) -> BriefSection:
        """§III — External signals to watch.

        Reads the operator-curated external_categories.txt. Agent does
        NOT fetch external state.
        """
        body = []
        cats = self._external_categories()
        if not cats:
            body.append(
                "- External categories file is empty. Operator should populate "
                "`polaris_foresight/external_categories.txt` with anti-coercion-"
                "relevant signal categories to track."
            )
        else:
            for cat in cats[:10]:
                body.append(f"- {cat}")
        return BriefSection(
            heading="III — External signals to watch",
            body_lines=body,
            citations=["polaris_foresight/external_categories.txt"],
        )

    def _section_iv_vocation_gaps(self) -> BriefSection:
        """§IV — Vocation-aligned gaps. STRUCTURALLY REQUIRED non-empty
        per Anti-Architect modification.

        For each of the seven anti-coercion primitives, scan the last
        N=30 ships in CHANGELOG. If a primitive hasn't been touched
        (no mention in any of the 30), surface as a vocation gap.
        """
        body = []
        citations = ["MISSION.md §Vocation", "CHANGELOG.md (last 30 ships)"]
        cl = self._changelog()
        # Take first ~30 entries (newest)
        entries = re.split(r"^## v[0-9]+\.[0-9]+", cl, flags=re.MULTILINE)[:31]
        scope = "\n".join(entries)
        scope_lower = scope.lower()
        for primitive in ANTI_COERCION_PRIMITIVES:
            if primitive.lower() not in scope_lower:
                body.append(
                    f"- **{primitive}** has no mention in last 30 CHANGELOG entries. "
                    f"This is a vocation gap; consider whether the primitive needs "
                    f"a maintenance pass, hardening, or test coverage refresh."
                )
        # Also check the "candidate" surface from polaris_sql for
        # foresight signals (when DB-helpers exist)
        if (self.repo_root / "polaris_sql" / "14_foresight_helpers.sql").exists():
            citations.append("polaris_sql/14_foresight_helpers.sql")
            body.append(
                "- Foresight SQL helpers available "
                "(`foresight_token_age_distribution`, "
                "`foresight_verification_dormancy`, "
                "`foresight_audit_volume_trend`). "
                "Operator may run them via psql to surface schema-level "
                "anti-coercion signals (e.g., dormant tokens, unverified-too-long)."
            )
        if not body:
            body.append(
                "- All seven anti-coercion primitives mentioned in recent ships. "
                "(May indicate the agent's heuristic is too lenient; consider "
                "tightening to specific test/file modifications.)"
            )
        return BriefSection(
            heading="IV — Vocation-aligned gaps (anti-coercion)",
            body_lines=body,
            citations=citations,
        )

    def _section_v_candidates(
        self,
        sec_i: BriefSection,
        sec_ii: BriefSection,
        sec_iii: BriefSection,
        sec_iv: BriefSection,
    ) -> BriefSection:
        """§V — Three foresight candidates derived from §I-§IV."""
        candidates: list[str] = []

        # Candidate from §IV: most-mentioned vocation gap
        if not sec_iv.is_empty():
            for line in sec_iv.body_lines[:1]:
                if line.startswith("- **"):
                    primitive = line.split("**")[1] if "**" in line else "vocation gap"
                    candidates.append(
                        f"- **FS-CANDIDATE-1**: Vocation maintenance pass on "
                        f"`{primitive}` (no recent mention in CHANGELOG; "
                        f"consider hardening, test refresh, or doc update). "
                        f"_risk: LOW · effort: one-shot · vocation: anti-coercion (direct)_"
                    )

        # Candidate from §II: longest-perpetual-deferral
        if not sec_ii.is_empty():
            for line in sec_ii.body_lines[:1]:
                if line.startswith("- ("):
                    candidates.append(
                        f"- **FS-CANDIDATE-2**: Address perpetual deferral surfaced by "
                        f"§II. {line[2:120]}... _risk: MEDIUM · effort: one-day · "
                        f"vocation: depends on item; operator triages_"
                    )

        # Candidate from §III: top external category
        if not sec_iii.is_empty():
            external = self._external_categories()
            if external:
                candidates.append(
                    f"- **FS-CANDIDATE-3**: Audit Polaris's posture against "
                    f"external category: \"{external[0]}\". Surface gaps via "
                    f"adversary_watcher pass. _risk: LOW · effort: one-shot · "
                    f"vocation: anti-coercion (defensive scan)_"
                )

        if not candidates:
            candidates.append(
                "- No candidates surfaced this cycle. Either the system is in "
                "steady-state (good) or the agent is mistuned (consider operator "
                "review of brief)."
            )

        return BriefSection(
            heading="V — Three foresight candidates",
            body_lines=candidates[:3],
            citations=[],
        )

    # ----- Sunset detection -----------------------------------------

    def _distinct_months_in_briefs(self, briefs: list[dict[str, Any]]) -> int:
        """Count DISTINCT calendar months represented in the briefs log.

        The sunset clause counts "6 monthly briefs" as 6 distinct months,
        NOT 6 emissions. Same-month emissions (e.g., operator re-runs the
        script multiple times in one Saturn-pass) count as one. This makes
        the sunset clause honest in the presence of repeated invocations.
        """
        months: set[str] = set()
        for b in briefs:
            d = b.get("date")
            if not d:
                continue
            # YYYY-MM prefix
            if len(d) >= 7:
                months.add(d[:7])
        return len(months)

    def _check_sunset(self, log: dict[str, Any]) -> Optional[str]:
        """Return a sunset warning string if the empirical-graduation
        threshold is not met, else None.

        Threshold: ≥50% of FS-XXXXXXXX candidates promoted to ROADMAP
        must be ACCEPTED (graduated to a real R-id) over 6 DISTINCT-MONTH
        briefs. Multiple emissions in the same month count as one (per
        v9.13 fix; pre-v9.13 raw count caused same-day test invocations
        to false-trigger the sunset).
        """
        briefs = log.get("briefs", [])
        months_observed = self._distinct_months_in_briefs(briefs)
        if months_observed < SUNSET_BRIEFS_REQUIRED:
            return None  # not enough distinct-month data yet
        candidates = log.get("candidates", {})
        if not candidates:
            return (
                f"After {months_observed} distinct-month briefs, zero candidates "
                f"have been tracked. The acceptance log is empty; either no "
                f"candidates were ever promoted, or the log is corrupted."
            )
        accepted = sum(1 for c in candidates.values() if c.get("status") == "accepted")
        total = len(candidates)
        rate = accepted / total if total > 0 else 0.0
        if rate < SUNSET_ACCEPTANCE_THRESHOLD:
            return (
                f"After {months_observed} distinct-month briefs and {total} "
                f"candidates, acceptance rate is {rate:.0%} (threshold: "
                f"{SUNSET_ACCEPTANCE_THRESHOLD:.0%}). The foresight surface has "
                f"not earned its right to expand and may not be earning its "
                f"right to exist. Operator should consider a removal Sanctum or "
                f"a corrective tuning Sanctum."
            )
        return None

    def _acceptance_summary(self, log: dict[str, Any]) -> str:
        briefs = log.get("briefs", [])
        months_observed = self._distinct_months_in_briefs(briefs)
        candidates = log.get("candidates", {})
        if not candidates:
            return (
                f"Empirical-graduation tracker: {len(briefs)} brief emission(s) "
                f"across {months_observed} distinct month(s); 0 candidates tracked."
            )
        accepted = sum(1 for c in candidates.values() if c.get("status") == "accepted")
        declined = sum(1 for c in candidates.values() if c.get("status") == "declined")
        open_ = sum(1 for c in candidates.values() if c.get("status") == "open")
        total = len(candidates)
        rate = (accepted / total) if total > 0 else 0.0
        return (
            f"Empirical-graduation tracker: {len(briefs)} brief emission(s) "
            f"across {months_observed} distinct month(s); "
            f"{total} candidate(s) tracked "
            f"(accepted={accepted}, declined={declined}, open={open_}). "
            f"Acceptance rate {rate:.0%}; threshold {SUNSET_ACCEPTANCE_THRESHOLD:.0%} "
            f"after {SUNSET_BRIEFS_REQUIRED} distinct-month briefs."
        )

    # ----- Main entry ----------------------------------------------

    def generate(self) -> Brief:
        """Generate the complete foresight Brief."""
        sec_i = self._section_i_surprises()
        sec_ii = self._section_ii_perpetual_deferrals()
        sec_iii = self._section_iii_external_signals()
        sec_iv = self._section_iv_vocation_gaps()
        sec_v = self._section_v_candidates(sec_i, sec_ii, sec_iii, sec_iv)

        log = self._acceptance_log()
        sunset = self._check_sunset(log)
        accept_summary = self._acceptance_summary(log)

        return Brief(
            date=self.today,
            sections={
                "I": sec_i,
                "II": sec_ii,
                "III": sec_iii,
                "IV": sec_iv,
                "V": sec_v,
            },
            sunset_warning=sunset,
            acceptance_summary=accept_summary,
        )

    def update_acceptance_log_after_brief(self) -> None:
        """Append a brief-emission marker to the acceptance log.

        Called after every brief generation (whether saved or not).
        """
        path = self.repo_root / "polaris_foresight" / "_acceptance_log.json"
        log = self._acceptance_log()
        log.setdefault("briefs", []).append({
            "date": self.today.isoformat(),
            "timestamp_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        })
        path.write_text(json.dumps(log, indent=2, sort_keys=True), encoding="utf-8")
