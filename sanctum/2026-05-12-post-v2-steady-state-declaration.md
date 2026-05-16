# Sanctum: post-v2-steady-state-declaration

**Date:** 2026-05-12
**Petitioner:** agent (Claude, Opus 4.7)
**Principal:** VANTA
**Trigger:** Structural change to MISSION.md (constitutional amendment
to the "Post-v2 strategic moment" section authorized in v8.29). Also:
cross-arc / mission-level decision per `meta/sanctum-protocol.md` §49.
**Risk class:** MEDIUM
**Status:** CLOSED
**Architect brief ID:** arch-2026-05-12-001 (in-chat brief, 2026-05-12)

---

## I. The Matter

Resolve the v3-vs-steady-state binding question that v8.29 documented
as deliberately unresolved. Architect recommended steady-state; VANTA
approved.

## II. Preparation

- **Architect brief:** in-chat Architect brief 2026-05-12, structured
  as a six-section strategic survey with §V containing three
  numbered suggestions (arch-2026-05-12-001 through -003). The brief
  is not journaled to disk (chat-only) but its substance is preserved
  in this Sanctum's §III–IV.
- **Prior surfacing:** the Architect raised this question in every
  brief since v8.20 (8+ occurrences). MISSION.md's "Post-v2 strategic
  moment" section (added v8.29) documents the moment formally. The
  recurrence count itself is evidence the question needs resolution.
- **Alignment audit:** ran v8.29 audit pass (8 lenses against
  MISSION); the audit confirmed v2 is closed 12/12, both done-lists
  archived, cognitive layer constitutionalized at the principles
  level (v8.30). No mission-shaped work remains.
- **Trigger conditions:** Arc B (adversarial hardening) gated on
  prod-deploy — not fired. Arc C (Polaris-as-platform) gated on a
  partner consumer — not fired. Novel arc — requires a documented
  external cause; none observed.
- **Blast radius if approved:**
  - `MISSION.md` — amend the "Post-v2 strategic moment" section
    from "deliberately unresolved" to "Resolved 2026-05-12:
    steady-state" with operating clauses (~15 lines net change).
  - `scripts/ai-architect.sh` — stop emitting the v3-vs-steady-state
    suggestion once resolved.
  - `scripts/ai-propose.sh` — already correctly weights mission
    items above maintenance; document that maintenance is the
    reward function in the post-v2 era.
  - `CLAUDE.md` — note the default agent posture for ambiguous
    requests (decline-and-surface, not propose-new-mission).
  - Tests — add a sibling class `TestPostV2Resolution` to assert
    the "Resolved" language appears in MISSION.md and cites this
    Sanctum.

## III. Alternatives considered

### A. Open v3 (autonomous-invented arc)

The agent invents an arc not currently triggered. Candidates surfaced
in prior conversations: AI-generated synthetic-identity attacks,
post-quantum hardening beyond what ML-DSA already gives, formal
verification of selected procedures.

- **For:** Forward motion. Intellectually compelling. Each candidate
  is rationally defensible in isolation.
- **Against:** No external trigger fired. This is the canonical
  Workaround pattern (#15): inventing internal triggers to sustain
  motion when external pressure is zero. Violates MISSION's "no
  workaround" principle (IS NOT §6). Locks the agent into ongoing
  mission work that has no calibrated reward signal.

### B. Continued graduation (Option 3 again)

Keep shipping small bounded close-out items without formally declaring
steady-state. v8.28 was the canonical graduation phase; it correctly
closed v2's UI dimension.

- **For:** Mild forward motion without committing to a new arc.
- **Against:** v2's UI dimension is closed. Further "graduation"
  would be invented, same failure mode as A. Less honest than
  steady-state. Pattern: steady-state in denial.

### C. Formalize steady-state *(recommended)*

Resolve MISSION's "Post-v2 strategic moment" to steady-state.
External triggers (Arc B prod-deploy, Arc C partner consumer, novel
arc with documented external cause) open new arcs by name. Until
then, the agent ships LOW-risk maintenance only; the cognitive layer
self-monitors; the Architect stops surfacing the question.

- **For:**
  - Honest: matches the calibrated post-v2 state.
  - Reversible: Arc B/C/novel can open later if triggers fire.
  - Limits agent self-imposed scope creep (the v8.30 elevation
    explicitly forbade scope creep into agent-infra; this extends
    the discipline to mission scope).
  - Stops the Architect-recurrence pattern (which is itself a drift
    signal the v8.20 self-monitoring should care about).
  - Matches pattern #21 Closure: greenfield's complement.
- **Against:**
  - Less interesting work for the agent.
  - Some scripts may decay if unexercised (mitigated: ai-meta
    catches this; ai-done check #12 keeps brief journaling alive).
  - VANTA may itch to add features and bypass the contract
    (acceptable: the contract is operator-revocable).

## IV. Recommendation

**Option C — formalize steady-state.**

Concrete execution if §VI approves:

1. Amend `MISSION.md` §"Post-v2 strategic moment" — replace the
   "deliberately unresolved" framing with:

   > **Resolved 2026-05-12: steady-state** (Sanctum
   > `2026-05-12-post-v2-steady-state-declaration`).
   >
   > The agent operates in maintenance mode. External triggers open
   > new mission arcs by name: Arc B (prod-deploy), Arc C (partner
   > consumer), or a novel arc with a documented external cause.
   > Until a trigger fires, the agent ships LOW-risk maintenance
   > only; the cognitive layer self-monitors via CM; the Architect
   > surfaces drift, not opportunities for new scope.
   >
   > The default posture for ambiguous requests is *decline and
   > surface*: explain why the request looks like new mission
   > scope, name the trigger that would be needed, and let VANTA
   > authorize before any execution.

2. `scripts/ai-architect.sh` — remove the v3-vs-steady-state
   suggestion from §V Suggestions (resolved suggestions are not
   re-surfaced; this is `arch-2026-05-12-001 RESOLVED`).

3. `scripts/ai-propose.sh` — confirm housekeeping items remain
   propose-eligible at their existing weight; document the post-v2
   reward function with a comment block.

4. `CLAUDE.md` — add a one-line note that the post-v2 default
   posture is decline-and-surface, referencing this Sanctum.

5. Add two soft-check tests to `polaris_web/test_structural_invariants.py`
   (sibling class `TestPostV2Resolution`):
   - The "Resolved" or "steady-state" keyword appears in MISSION.md.
   - The Sanctum filename is referenced from MISSION.md (the
     audit-of-record principle: the constitution cites the audit
     trail that authorized the resolution).

## V. What's needed from VANTA

One of:

1. **"yes C"** / **"proceed with recommendation"** — approve
   steady-state declaration; ship as v8.31.
2. **"yes C with edits"** — approve with specific changes to
   operating clauses or test posture.
3. **"yes A, trigger is X"** — open a v3 arc, naming the external
   trigger that justifies it.
4. **"yes B"** — continued graduation only.
5. **"hold"** — defer.

## VI. Decision

Proceed with recommendation.

## VII. Outcome

Shipped v8.31. MISSION.md 'Post-v2 strategic moment' rewritten from 'deliberately unresolved' to 'Resolved 2026-05-12: steady-state' with operating clauses (external triggers Arc B/C/novel, decline-and-surface default posture). ai-architect.sh gained is_steady_state() detector; emit_outlook + emit_suggestions reframe propose-output as housekeeping under steady-state. ai-propose.sh comment block documents post-v2 reward function. CLAUDE.md gained 'Post-v2 default posture' section. New TestPostV2Resolution class (3 soft-check tests; 56/56 structural total). Sanctum integrity: 12 sessions, no drift.

**See:** [CHANGELOG `## v8.31`](../CHANGELOG.md) · [`journal/2026-05-12.md`](../journal/2026-05-12.md). Cross-ref added v8.61 per Architect-reflection finding.
