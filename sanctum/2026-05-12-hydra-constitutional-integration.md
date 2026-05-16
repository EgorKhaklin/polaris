# Sanctum: hydra-constitutional-integration

**Date:** 2026-05-12
**Petitioner:** agent (Claude, Opus 4.7)
**Principal:** VANTA
**Trigger:** structural change to the cognitive layer (amendment to MISSION.md's "The cognitive substrate" section). MEDIUM-risk per `meta/autonomy-architecture.md`. Companion piece to the v8.37 arc-opening Sanctum.
**Risk class:** MEDIUM
**Status:** CLOSED
**Architect brief ID:** n/a — structural

---

## I. The Matter

Phase 2 of Arc D closed in v8.42 with all six watchers shipped and the
HYDRA swarm healthy. Phase 3 / H8 / R12-8 is the constitutional
amendment that elevates HYDRA from "running implementation" to
"named operative implementation" in MISSION.md's cognitive-substrate
section — while preserving the v8.30 substitutability principle.

VANTA must decide **whether to name HYDRA in the constitution at all,
and if so, in which shape** (full elevation, narrow naming, or
non-naming).

## II. Preparation

- **Architect brief:** today's snapshot at `journal/2026-05-12-architect.md`
- **Proposal draft:** none required (structural change, scope is
  one section in MISSION.md + one structural-invariant test)
- **Alignment audit:**
  - **v8.30 (cognitive-layer constitutional elevation):** established
    the precedent that the cognitive substrate is named in MISSION.md
    as *principles*, not implementations. The 27 ai-* scripts /
    22-pattern catalog / Architect persona / constraint lattice are
    explicitly marked **substitutable**. This Sanctum must honor that
    precedent — HYDRA cannot be named as constitutional, only as
    *currently operative*.
  - **v8.31 (post-v2 steady-state):** the agent's default posture is
    decline-and-surface. Arc D fires the third external-trigger
    clause (novel arc with documented external cause). Constitutional
    integration is the natural close-out of that arc, not scope
    creep.
  - **v8.37 (arc-opening Sanctum):** §IV closed with VANTA's
    "Proceed with recommendation" and committed Phase 3 to a
    separate Sanctum. **This document is that follow-on.**
  - **Phase 2 evidence:** 6/6 watchers shipped (v8.37, v8.38, v8.39,
    v8.40, v8.41, v8.42); five consecutive self-calibration loops;
    HYDRA smoke `6 (6 healthy, 0 drift, 0 alert) · swarm is healthy.
    steady-state holds.` The implementation has earned the right to
    be cited.
- **Blast radius (if approved as recommended):**
  - `MISSION.md` — cognitive-substrate section amended with one new
    clause naming HYDRA + one cross-reference to `polaris_hydra/`
  - `polaris_web/test_structural_invariants.py` — one new soft-check
    test (or class) asserting the HYDRA naming + substitutability
    qualifier are both present
  - `CHANGELOG.md` — v8.43 entry
  - `CLAUDE.md` — state-map row + script-count update (none expected)
  - `ROADMAP.md` — R12-8 ✅
  - `journal/2026-05-12.md` — decision + outcome
  - **No** changes to `polaris_hydra/`, `scripts/`, `polaris_web/app.py`,
    or any SQL/schema/procedure. This is a documentation amendment with
    a structural-test guard.
- **Tests planned:** +2 structural-invariant tests (target 82/82).
  Names: `test_hydra_is_named_in_cognitive_substrate`,
  `test_hydra_naming_is_marked_substitutable`. Both soft-checks (do
  not pin specific prose; pin the property).

## III. Alternatives considered

### A. Do not name HYDRA in MISSION.md (status quo)

**Move:** leave MISSION.md's cognitive-substrate section unchanged.
Document HYDRA in `DEVNOTES/` and `polaris_hydra/README.md` only.
Close R12-8 by marking it ✗ RETIRED with rationale.

**Pro:** maximally faithful to the v8.30 principle (constitution
names principles, not implementations). Zero risk of the
constitutional layer ossifying around a specific implementation.

**Con:** the cognitive-substrate section already enumerates *all
other* operative implementations as substitutable (27 ai-* scripts,
22-pattern catalog, Architect persona, constraint lattice). HYDRA is
the **same kind of thing** as those — a currently-running
implementation of a principle that could in theory be replaced.
Listing the others but omitting HYDRA is asymmetric and would
slowly become wrong as readers wonder why HYDRA is invisible. The
v8.30 amendment named the *category* (Sanctum protocol,
audit-of-record, risk classes, CM); this would name the
implementation list — both moves are consistent with the principle.

**Verdict:** rejected. Asymmetry against the v8.30 pattern is a
worse outcome than naming HYDRA with the substitutability qualifier.

### B. Name HYDRA fully — elevate "swarm synthesis" as a fifth principle

**Move:** amend the cognitive-substrate section to add a fifth
*principle*: "swarm synthesis" alongside Sanctum protocol,
audit-of-record, risk classes, CM. HYDRA becomes the canonical
implementation; the principle itself is constitutional.

**Pro:** strongest commitment to Arc D's strategic thesis.
Maximally legible to future readers.

**Con:** **violates the v8.30 substitutability precedent in spirit.**
The four named principles (Sanctum, AoR, risk classes, CM) are
*orthogonal* to any specific implementation — they survive script
rewrites, agent swaps, even language migrations. "Swarm synthesis"
is not yet that abstract; it is a specific operating pattern of a
specific multi-agent setup. Elevating it to principle now would
pre-commit the constitution to multi-watcher architecture in a way
that would be costly to roll back if a different synthesis pattern
proved better.

**Verdict:** rejected. Premature elevation. Earn this position over
multiple arcs, not in a single phase.

### C. Narrow naming — extend the substitutability-implementation list (recommended)

**Move:** amend MISSION.md's cognitive-substrate section by adding
HYDRA + watchers to the existing enumeration of *substitutable
implementation* alongside the 27 ai-* scripts, 22-pattern catalog,
Architect persona, and constraint lattice. Do not add a new
principle. Do not elevate "swarm synthesis" to constitutional
status. Add one cross-reference clause that names `polaris_hydra/`
as the directory containing the current implementation. Add a soft
test that pins the naming and the substitutability qualifier.

**Pro:**
- Symmetric with v8.30 — same naming pattern as the existing
  enumeration.
- Honors the substitutability principle verbatim.
- Acknowledges Arc D's delivery (6/6 watchers, all healthy) without
  ossifying any implementation choice.
- Reversibility is trivial: if HYDRA is ever replaced, the clause
  swaps its name for the successor's. No principle migration.
- Closes R12-8 with the minimum constitutional surface area
  consistent with VANTA's "holy shit, that's done" bar.

**Con:** smallest possible change. A reader looking for "where
does HYDRA fit in the constitution" gets a one-line answer rather
than a full architectural argument. Acceptable: that's what
`DEVNOTES/ships/` and `polaris_hydra/README.md` are for.

**Verdict:** recommended.

## IV. Recommendation

**Option C.** Narrow naming — extend the existing
substitutability-implementation enumeration in MISSION.md's
cognitive-substrate section to include HYDRA + watchers, with the
substitutability qualifier preserved. One new structural test
class (2 soft-check tests, 80 → 82 total) pins the naming and
the qualifier. No new principle. No new constraints. No changes to
schema, procedure, or any non-documentation code.

### Specific amendment text (preview)

The cognitive-substrate section currently reads (in summary):

> The cognitive substrate is named here as four principles —
> Sanctum protocol, audit-of-record, risk classes, CM. The current
> implementations of these principles — 27 ai-* scripts, the
> 22-pattern catalog, the Architect persona, the constraint lattice
> — are substitutable. Future agents may replace any of them
> without amending the constitution, provided the principles still
> hold.

The proposed amendment adds one sentence:

> The HYDRA swarm (`polaris_hydra/`) and its six watchers
> (schema, cognitive, security, mission, adversary, performance)
> are the operative synthesis implementation, also substitutable
> under the same principle: a future agent may replace the swarm
> with a different synthesis pattern without amending the
> constitution, provided the four principles still hold.

The new soft-check tests assert (a) the string "HYDRA" appears in
the cognitive-substrate section, and (b) the substitutability
qualifier ("substitutable" or equivalent) is present in the same
section after the HYDRA mention. Both tests pin the property, not
the prose.

### Why this is the right move now

- Phase 2 delivered. 6/6 watchers shipped, all healthy, swarm
  smoke green. The implementation has been load-tested by five
  consecutive self-calibration loops.
- Without this amendment, the v8.30 enumeration is asymmetric:
  it names every other operative implementation of cognitive-layer
  principles but omits the one that just shipped. That asymmetry
  is a constitutional drift signal of its own.
- The smallest possible amendment closes the gap. Larger
  amendments (Option B) overcommit; smaller amendments (Option A)
  leave the asymmetry.
- Reversibility holds: substitutability is preserved verbatim.
  HYDRA is named only as the *current* implementation, not as the
  canonical one. The constitution does not pin a specific
  multi-agent shape.

### Risks and mitigations

| Risk | Likelihood | Mitigation |
|---|---|---|
| Future readers read the HYDRA mention as constitutional and resist replacing it | Low | Substitutability clause is in the same sentence. The pattern matches v8.30 — readers already know how to parse it. |
| The structural test pins prose too tightly and breaks on a future rewrite | Low | Tests are soft-checks on property (string presence + qualifier presence), not exact prose match. |
| Naming HYDRA in MISSION.md leaks into other layers (schema, etc.) | None | The amendment touches only the cognitive-substrate section. No code or schema references MISSION.md content directly. |
| Steady-state default posture is undermined by an apparent expansion | Low | This Sanctum closes Arc D, which was opened under the third external-trigger clause of the v8.31 steady-state declaration. R12-8 is the documented final item of that arc, not a new arc. |

## V. What's needed from VANTA

**One decision:**

- **Option A** — do not name HYDRA in MISSION.md; mark R12-8 ✗ RETIRED
- **Option B** — name HYDRA AND elevate "swarm synthesis" as a fifth principle
- **Option C (recommended)** — narrow naming, extend the
  substitutability-implementation enumeration with HYDRA + watchers,
  preserve substitutability, add a 2-test soft-check guard
- **Other** — name a different shape

Once decided, the agent will execute LOW-risk-style (MEDIUM-risk
work is authorized once the Sanctum closes):

1. Amend MISSION.md cognitive-substrate section per the chosen
   option's text
2. Add `TestHydraConstitutionalIntegration` (or equivalent) class
   to `polaris_web/test_structural_invariants.py`
3. Mark R12-8 ✅ in ROADMAP.md
4. Mark H8 ✅ in MISSION.md Arc D done-list
5. Write v8.43 CHANGELOG entry
6. Update CLAUDE.md state map
7. Journal decision + outcome
8. Run ai-link-check + ai-meta + ai-done
9. Close this Sanctum (transition to CLOSED with §VII outcome)

## VI. Decision

Proceed with recommendation (Option C — narrow naming).

## VII. Outcome

MISSION.md cognitive-substrate section amended (one new bullet + one substitutability clause); TestHydraConstitutionalIntegration class added (2 soft-check tests; 82/82 total); H8 ✅, R12-8 ✅, Arc D closed (H1..H8 + R12-1..R12-8 all ✅). Shipped as v8.43. Constitutional principles unchanged (four principles preserved verbatim). Steady-state default posture restored.

**See:** [CHANGELOG `## v8.43 (Arc D CLOSED 8/8)`](../CHANGELOG.md) · [`journal/2026-05-12.md`](../journal/2026-05-12.md). Cross-ref added v8.61 per Architect-reflection finding.
