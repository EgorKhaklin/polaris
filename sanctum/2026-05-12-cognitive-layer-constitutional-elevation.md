# Sanctum: cognitive-layer-constitutional-elevation

**Date:** 2026-05-12
**Petitioner:** agent (Claude, Opus 4.7)
**Principal:** VANTA
**Trigger:** Structural change to the cognitive layer (explicit Sanctum
trigger per `meta/sanctum-protocol.md` §49)
**Risk class:** MEDIUM
**Status:** CLOSED
**Architect brief ID:** n/a — structural; surfaced in v8.29 audit pass

---

## I. The Matter

Whether to elevate the cognitive layer — currently scattered across
`CLAUDE.md`, `scripts/`, `meta/`, `DEVNOTES/` — into `MISSION.md` as
constitutional language, given it is now load-bearing infrastructure
for post-v2 custodianship.

## II. Preparation

- **Architect brief:** `journal/2026-05-12-architect.md` (current). The
  Architect has surfaced this in every brief since v8.20. v8.29 audit
  pass made the gap explicit.
- **Alignment audit:** v8.29 ran 8 lenses against MISSION; the
  cognitive layer's CM is named but the broader infrastructure
  (Sanctum protocol, Architect persona, audit-of-record principle,
  risk classes, 27 ai-* scripts, 22-pattern catalog, constraint
  lattice) is not. ai-coherence is GREEN because CM exists; ai-meta
  is GREEN because it self-monitors. Neither catches the unnamed
  dependency.
- **Proposal draft:** none — structural change; the audit surfaces are
  the preparation.
- **Blast radius if approved:**
  - `MISSION.md` — add ~30–50 lines (Option C) or ~250–300 lines
    (Option B); zero lines (Option A); ~15 lines (Option D)
  - No schema changes
  - No procedure changes
  - No script changes (the scripts already exist; this Sanctum decides
    whether MISSION acknowledges them)
  - No constraint changes (C1–C10 untouched in every option)
  - No test changes
- **Tests planned:** if approved, +1 structural-invariant test to
  `test_structural_invariants.py` asserting the new section's
  principle names appear in MISSION.md. The test enforces the
  doc-vs-claim contract the same way ai-coherence enforces the
  C1–C10 lattice claim.

## III. Alternatives considered

### A. Status quo

Keep the cognitive layer documented in `CLAUDE.md` / `meta/` /
`scripts/` only. `MISSION.md` continues to mention only the CM
meta-constraint with no broader naming.

- **For:** MISSION stays focused on Polaris-the-product properties.
  Avoids the category error of mixing product semantics with agent
  ergonomics. The cognitive layer is replaceable; pinning it to the
  constitution is anti-replaceable.
- **Against:** The Architect surfaces this gap in every brief because
  it is real. An unnamed structural dependency is invisible to the
  Removable Test (`meta/structural-architecture.md`). Future agents
  read MISSION and miss the load-bearing infrastructure.

### B. Full elevation

Add a top-level MISSION section naming all 27 scripts, the Sanctum
protocol, the Architect persona, the audit-of-record principle, the
risk classes, the 22-pattern catalog, and the constraint lattice.

- **For:** Maximum constitutional protection; everything load-bearing
  is explicitly named.
- **Against:** Locks in a specific implementation. MISSION grows
  ~50%. Category error: MISSION is about Polaris properties, not
  agent properties. If a script changes, the constitution changes —
  protocol overhead is wrong.

### C. Principles-only elevation *(recommended)*

Add one new top-level section — **"The cognitive substrate"** — that
names the *principles* the layer implements (Sanctum for MEDIUM/HIGH
decisions, audit-of-record for state changes, risk classes gating
autonomy, the CM meta-constraint) and explicitly notes the current
implementation is substitutable. The CM section gains a single pointer
to the new section as its enforcement substrate.

- **For:**
  - Separates durable contract (principles) from substitutable
    implementation (specific scripts). This matches how C1–C10 already
    work: they name properties, not procedures.
  - Right size — ~30–50 MISSION lines, not 300.
  - Honors the Removable Test: the principles cannot be removed
    without cascade; the specific scripts can be swapped.
  - Enables the v3-vs-steady-state decision by making the agent
    contract dimension explicit; both worlds need the principles,
    either can use different scripts.
  - Constitutional protection without lock-in.
- **Against:**
  - Adds complexity to the constitution.
  - Future agents might bypass principles by claiming a "different
    implementation that preserves them" (mitigation: the new section
    names testable criteria for each principle).

### D. CM expansion

Keep MISSION mostly as-is but expand the existing CM section from
~25 lines to ~60, folding in Sanctum / audit-of-record / risk
classes as CM's enforcement substrate.

- **For:** Minimum structural change. Stays inside the existing
  meta-constraint framing.
- **Against:** CM is about self-monitoring. Forcing it to also carry
  Sanctum/audit-of-record/risk-classes bends the constraint. CM
  becomes a kitchen-sink constraint, weakening the discipline of
  one-claim-per-constraint that C1–C10 model.

## IV. Recommendation

**Option C — principles-only elevation.**

Concretely: add a section after "The architectural soul (the 'why'
beneath the 'what')" titled **"The cognitive substrate (the agent
contract)"**. The section names four principles:

1. **The Sanctum protocol** — MEDIUM/HIGH-risk decisions are recorded
   as audit-of-record sessions in `sanctum/`. Routine LOW-risk work
   does not produce a Sanctum. Specified in `meta/sanctum-protocol.md`.
2. **Audit-of-record** — every primitive that changes state has a
   schema element + invariants that fully reconstruct operation
   history without a separate event-log table. Eight current
   instances; canonicalized in `DEVNOTES/audit-of-record.md`.
3. **Risk classes** — LOW (autonomous-eligible), MEDIUM (propose-and-
   wait), HIGH (explicit human approval). Defined in
   `meta/autonomy-architecture.md`.
4. **CM (meta-constraint)** — the cognitive layer self-monitors via
   executable checks. Enforced by `scripts/ai-meta.sh` (6 checks).
   This is the existing CM, now positioned as one of four principles
   rather than a single isolated constraint.

The section closes with an explicit note: *"This document names
principles, not implementations. The 27 ai-* scripts, the
22-pattern catalog, the Architect persona, and the constraint
lattice are the current implementation; they are substitutable. The
principles are not. A future agent may use a different cognitive
substrate so long as it preserves Sanctum discipline, audit-of-record,
risk-class gating, and CM self-monitoring."*

Cross-references in the new section point at the existing
`meta/sanctum-protocol.md`, `DEVNOTES/audit-of-record.md`,
`meta/autonomy-architecture.md`, and `scripts/ai-meta.sh`.

This is structurally analogous to how C10 ("identity ≠ money") names
the property without naming the *mechanism* of separation (no
MonetaryClaim table — that's the *current* mechanism, but a different
mechanism that preserved the property would still satisfy C10).

## V. What's needed from VANTA

One of the following:

1. **"yes C"** — approve principles-only elevation. The agent
   executes the section addition, adds the structural-invariant test,
   ships as v8.30.
2. **"yes C with edits"** — approve C but specify which principles
   make the cut, the section title, or the cross-references.
3. **"yes A"** — reject elevation; preserve status quo. The agent
   stops surfacing this in Architect briefs. (Architect protocol
   note: a REJECT here means "you may not raise this again until
   the strategic situation changes substantially.")
4. **"yes B"** — full elevation. The agent drafts the larger section.
5. **"yes D"** — CM expansion only. The agent expands the existing
   CM block instead of adding a new section.
6. **"hold"** — defer until after the v3-vs-steady-state decision.

Open questions if Option C is chosen:

- **Q1.** Section title: "The cognitive substrate" / "The agent
  contract" / "The operating discipline" / something else?
- **Q2.** Should the principles list include items beyond the four
  above (e.g., the constraint lattice itself, the 22-pattern catalog,
  the Architect persona)?
- **Q3.** Should the structural-invariant test treat the principle
  names as required keywords in MISSION.md (hard check) or only as
  expected appearances (soft check)?

## VI. Decision

**"Proceed with recommendation."** — VANTA, 2026-05-12

Option C approved verbatim. Open questions resolved by default (the
values named in §IV / §V, since VANTA did not specify edits):

- **Q1 (section title):** "The cognitive substrate (the agent contract)"
- **Q2 (principles list):** the four named in §IV — Sanctum protocol,
  audit-of-record, risk classes, CM. The constraint lattice, 22-pattern
  catalog, and Architect persona stay as implementation details
  cross-referenced from the new section, not promoted to principles.
- **Q3 (test posture):** soft check — the structural-invariant test
  asserts each principle's *name* appears in MISSION.md and links to
  its enforcement substrate; it does NOT pin the exact wording of the
  section.

## VII. Outcome

Shipped v8.30. Added 'The cognitive substrate (the agent contract)' section to MISSION.md naming four principles (Sanctum protocol, audit-of-record, risk classes, CM). CM block cross-linked to new section. New TestCognitiveSubstrateSection class in test_structural_invariants.py (6 tests, all pass; 53/53 structural total). ai-link-check 58/58 clean; ai-meta healthy; ai-coherence MINOR DRIFT unchanged (pre-existing soft signals only). Open questions Q1-Q3 resolved by defaults from §IV/V.

**See:** [CHANGELOG `## v8.30`](../CHANGELOG.md) · [`journal/2026-05-12.md`](../journal/2026-05-12.md). Cross-ref added v8.61 per Architect-reflection finding.
