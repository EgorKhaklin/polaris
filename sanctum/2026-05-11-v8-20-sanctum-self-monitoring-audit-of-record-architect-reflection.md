# Sanctum: v8.20 — Sanctum self-monitoring + audit-of-record principle + Architect reflection

**Date:** 2026-05-11
**Petitioner:** agent (Claude, Opus 4.7)
**Principal:** VANTA
**Trigger:** structural change to the cognitive layer (bundle of three follow-up items from the v8.19 self-audit)
**Risk class:** MEDIUM
**Status:** CLOSED
**Architect brief ID:** n/a — structural (post-v8.19 self-audit, not architect-surfaced)

---

## I. The Matter

Bundle three structural follow-ups identified in the v8.19 cognitive-layer self-audit
into a single coordinated ship: CM extends to cover the Sanctum, the "audit-of-record"
principle gets a canonical definition, and the Architect gains a reflection mode that
ingests closed Sanctums to assess prediction-vs-reality.

## II. Preparation

- Architect brief: n/a — this Sanctum is a follow-up to the v8.19 self-audit that surfaced 11 findings (5 critical, 3 cognitive gaps, 3 anti-patterns). The audit itself is the preparation.
- Proposal draft: none — this is a structural cognitive-layer change.
- Alignment audit: the v8.19 self-audit is the audit. Seven LOW-risk fixes already shipped autonomously in Phase A. The four STRUCTURAL items remained; three are bundled into v8.20; the fourth (derived pattern observations) is deferred — see §III.
- Blast radius (files touched if approved):
  - `scripts/ai-meta.sh` — add CM check #6 (Sanctum integrity)
  - `DEVNOTES/audit-of-record.md` (new) — define the principle and list its four instances
  - `scripts/ai-architect.sh` — extend `--reflect` mode to ingest closed Sanctums
  - `meta/sanctum-protocol.md` — cross-reference the new principle file
  - `polaris_web/test_structural_invariants.py` — extension covering the new CM check (~3 tests)

## III. Alternatives considered

1. **Ship all four structural items in v8.20** (including derived-pattern-observation analysis on the Sanctum index). Rejected because (a) the pattern-observation analysis needs more sessions to be meaningful — N=4 is too small to derive stable patterns — and (b) the analysis tool can be its own ai-* script later. Deferring is honest; bundling now would be premature.
2. **Ship only the CM extension** (single item, smaller blast radius). Rejected because the three items have a natural coherence: CM check needs the audit-of-record principle to know what to check for, and Architect reflection needs both. Splitting them adds three Sanctums where one suffices.
3. **Skip the audit-of-record principle, leave the phrase as locally-used.** Rejected because the v8.19 audit specifically named this as cognitive-layer drift in progress — vocabulary used four times without canonical definition. Skipping continues the drift.
4. **Ship now without the Architect-reflection piece, defer that as well.** Rejected because Architect reflection is what closes the *learning loop* for the Sanctum. Without it, the protocol risks becoming ceremony — which was the deepest failure mode the v8.19 audit identified.

## IV. Recommendation

Ship v8.20 with three coordinated changes:

1. **`DEVNOTES/audit-of-record.md` (new).** Defines the principle: "an audit-of-record is a schema element whose own state, combined with its append-only invariants, fully reconstructs the history of the operation it records, without requiring a separate event-log table." Lists the four current instances (TokenLifecycleEvent, RecoveryRequest, TokenSignature, Sanctum sessions) and the structural shape each shares.

2. **`scripts/ai-meta.sh` CM check #6.** Scan `sanctum/` for:
   - Sessions with `Status: OPEN` that are >7 days old → flag as stale
   - Sessions where `Status: CLOSED` but §VII Outcome is empty → lifecycle violation
   - Sessions where `Status: REJECTED` but §VI Decision is empty → lifecycle violation
   - Sessions present in `sanctum/` but missing from `meta/sanctum-index.md`, or vice versa → index drift

3. **`scripts/ai-architect.sh --reflect`.** Extend to read recently-closed-and-rejected Sanctums and produce a "Sanctum prediction-vs-reality" subsection in the brief:
   - Did the recommendation in §IV match the actual outcome in §VII?
   - Did the refinements identified in the alignment audit catch real issues, or were they procedural?
   - Are there patterns across closed Sanctums the architect should weight in future briefs?

The derived-pattern-observation analysis is **explicitly deferred** to v8.21+. The current hand-curated section in `meta/sanctum-index.md` remains; below ~8 more Sanctums, automated analysis is noise.

## V. What's needed from VANTA

"Yes do v8.20" — single approval for the bundled three-item ship. Plus four decisions:

1. **CM extension scope.** Recommend the four checks in §IV item 2. Approve, or add/remove specific checks.
2. **Audit-of-record location.** Recommend `DEVNOTES/audit-of-record.md`. Alternative: `meta/audit-of-record.md` (closer to other architectural-concept files). I lean DEVNOTES because the principle is *implementation guidance* more than *architecture-of-the-architecture*.
3. **Architect reflection trigger.** Recommend `ai-architect.sh --reflect` reads the last 10 closed-or-rejected Sanctums by default, configurable via `--reflect-n N`. Approve, or specify a different default.
4. **Deferral acceptance.** The derived-pattern-observations item is deferred to v8.21+; the hand-curated pattern section in the index remains for now. Acknowledge that you're OK with this not landing in v8.20.

## VI. Decision

proceed with the recommendation — yes do v8.20 with all four recommended defaults: CM extension scope (four checks), audit-of-record location DEVNOTES/audit-of-record.md, Architect reflection default last-10 with --reflect-n flag, deferral of derived pattern analysis accepted

## VII. Outcome

Shipped v8.20 (2026-05-11). DEVNOTES/audit-of-record.md defines the principle with four current instances (TokenLifecycleEvent, RecoveryRequest, TokenSignature, Sanctum sessions). ai-meta.sh gains check_sanctum (CM #6) covering stale-OPEN, lifecycle violations, and index drift. ai-architect.sh --reflect extended to ingest closed/rejected Sanctums with prediction-vs-reality analysis; --reflect-n N for configurable depth. TestSanctumIntegrity adds 4 tests to test_structural_invariants.py; all pass. ai-meta verifies clean (LAYER SELF-MONITORING IS HEALTHY). The learning loop for the Sanctum is now closed; the protocol will not drift into ceremony.

**Canonical execution links:**

- CHANGELOG: [v8.20 entry](../CHANGELOG.md) (top of file, dated 2026-05-11)
- Journal: today's journal entry covering Phase A (7 fixes) and Phase B (this Sanctum)
- Mission marks: no v2 done-list items moved; cognitive-layer-only ship
- Meta: ai-meta.sh now runs six CM checks (was five since v8.9; check_sanctum is the first extension)
- Tests: 4 new TestSanctumIntegrity entries in `polaris_web/test_structural_invariants.py` (structural-invariant suite grew 18 → 22)

**Self-test the reflection mechanism caught its own missing link:**
On first close, §VII did not contain "CHANGELOG" or "journal" — the new
`ai-architect.sh --reflect` flagged it ("1 closed session(s) lack
CHANGELOG/journal links in §VII Outcome"). The link block above was
added in response. This is the learning loop functioning correctly
on its very first cycle.

