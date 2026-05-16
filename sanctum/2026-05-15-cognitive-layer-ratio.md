# Sanctum: cognitive-layer-ratio

**Date:** 2026-05-15
**Petitioner:** agent (Claude, Opus 4.7) speaking as the Architect
**Principal:** VANTA
**Trigger:** v9.09 multi-agent scan; surfaced as item S2 in
[`meta/polaris-self-roadmap-3-2026-05-15.md`](../meta/polaris-self-roadmap-3-2026-05-15.md).
A deeper-pattern observation: across v9.04 → v9.08, ~80% of changes
touched the cognitive-layer scaffolding (HYDRA + Mycelium + scripts/
+ meta/ + docs/) and ~20% touched the actual identity-token product
(polaris_web/sql/zk/cli). The cognitive layer has been growing; the
identity-token system has been static. The constitutional question is
whether there is a healthy ratio.
**Risk class:** HIGH (touches the cognitive-substrate principles
+ the architectural-soul of the project; could reframe what
Polaris is becoming).
**Status:** DECIDED + CLOSED 2026-05-15 — Position C (defer; current
ratio is correct for current phase) selected per heavy-production
posture (v8.31 §III.6) following VANTA's *"proceed with the architects
recommendation"*. Adopted in v9.10 alongside S1 (watcher-node-id-
alignment Position B). Layer-1 substantive work bundled into v9.10:
Pheromone rotation framework gains 10 SQL self-tests in
`polaris_sql/08_tests.sql` section S — first Layer-1 ship since v8.97.

---

## I. The Matter

Polaris is, per [`MISSION.md`](../MISSION.md), a **national identity
token reference implementation**. The cognitive layer (HYDRA +
Mycelium swarm + the ai-* scripts + the meta/ architecture +
sanctum/ + journal/) was built to **observe and improve the
identity-token system**. The cognitive layer is meant to be in
service of the identity-token system, not the reverse.

**The empirical observation across v9.04 → v9.08 (~30 hours, 38
items shipped):**

| Layer | What changed | Approx % of effort |
|---|---|---|
| Layer 1 (polaris_web/sql/zk/cli) | __version__.py + requirements.txt + 5 new test files | ~15% |
| Layer 2 (cognitive substrate: polaris_hydra/swarm) | 4 new modules + ant refactors + watcher channels + Pheromone framework | ~30% |
| Layer 3 (cognitive layer tools: scripts/ + meta/) | scan_filters + Sanctums + claude-90s + dashboard + sanctum-search + roadmap docs | ~35% |
| Layer 4 (documentation) | 10 new READMEs + CONVENTIONS + SYSTEM-MAP + per-folder docs | ~20% |

**Layers 2 + 3 + 4 = ~85% of v9.04 → v9.08 effort.**

The identity-token system itself — the actual product Polaris is
a reference implementation of — gained 0 schema tables, 0 new use
cases, 0 new SQL procedures, 0 new ZK circuits since v8.97
(WebAuthn-MFA). Five days, eight ships, no Layer-1 advances.

**This is not necessarily wrong.** Phases of cognitive-layer
investment are legitimate when:
- The cognitive layer is the project's distinguishing research
  contribution (arguable: the v9.04 hybrid intelligence model IS a
  real architectural innovation)
- Layer 1 is in a deliberate pause (Arc B Phase 2 is partially
  deferred per VANTA's prior posture)
- The cognitive layer was genuinely unfinished and v9.04+ closed
  the gap (true: v9.04 hybrid intelligence + v9.05 substrate
  hygiene + v9.06 lens-watching-itself + v9.08 showroom)

**But it is worth naming explicitly because:**
- The cognitive layer's growth has its own gravity. Each
  shipping cycle that observes itself produces signals worth
  observing again. The lens consuming the substrate it serves.
- A reference implementation that lives mostly in its
  meta-layer rather than its product layer is a different kind
  of artifact than what MISSION.md names.
- The next 30 hours could continue Layer-2/3 polish ad infinitum.

The hermetic principle: as above, so below. If the cognitive
layer at the top is healthy and the product layer at the
bottom is static, the symmetry is broken. The two should
move together.

## II. The architect's positions

### Position A: Declare the cognitive layer COMPLETE; freeze it

For v9.10 → v10.0, no Layer-2/3 changes unless they unblock a
Layer-1 advance. The cognitive layer is shipped; the product
needs work.

**Concrete shape:**
- Open a moratorium Sanctum: no Layer-2/3 changes accept under
  bug-fix carve-out (v8.31 §III.6) or under explicit operator
  authorization
- ROADMAP.md gets a new top-of-file Layer-1 priority list
- Architect briefs surface Layer-1 ideas; Layer-2/3 ideas
  filed in BACKLOG without ship priority

**Strengths:**
- Hard reset to product focus
- Forces Layer-1 advances
- The cognitive layer is genuinely impressive at v9.08; freezing
  it preserves what works

**Weaknesses:**
- Brittle if a real Layer-2/3 bug surfaces (bug-fix carve-out
  handles this but adds friction)
- Ignores that the cognitive layer is itself a real research
  contribution

### Position B: Explicit per-ship Layer-1-minimum budget

Each ship must touch ≥1 Layer-1 file (polaris_web/sql/zk/cli)
substantively (not just test_*.py + __version__.py). If no
Layer-1 work fits, the ship doesn't go.

**Strengths:**
- Forces Layer-1 advances per-ship without freezing the cognitive
  layer
- Maintains the wave-by-wave composite-ship pattern
- Operator-tunable: budget can be raised or lowered as project
  evolves

**Weaknesses:**
- Inflexible for ships that are genuinely Layer-2/3 closing-passes
  (e.g., a focused HYDRA refactor)
- "Touches Layer 1" is a vague metric; needs operational
  definition

### Position C: Defer; current ratio is correct for current phase — architect-recommended

Argue that v9.04 → v9.08 was the right phase: the cognitive layer
needed catch-up after v8.x focused on Layer 1 (Arc B production
deployment + v8.95 schema migration framework + v8.97 WebAuthn).
The v9.x catch-up is now done; v9.10+ naturally returns to
Layer-1 focus.

**Concrete shape:**
- No moratorium, no per-ship budget
- ROADMAP.md gets a "Layer-1 candidates" section (proposals: new
  use cases, schema migrations, ZK circuit improvements)
- Architect briefs lead with Layer-1 candidates from BACKLOG
- v9.10+ ships are scored partly on Layer-1 surface area

**Strengths:**
- Honors that v9.x was a deliberate cognitive-layer ship phase
- No new constraints on the agent
- Trusts emergent rebalancing

**Weaknesses:**
- Could just continue the imbalance if not actively monitored
- "Trust emergent rebalancing" is what got us here

## III. Architect's recommendation

**Position C (defer; current ratio is correct for current phase).**
Rationale:

1. **The v9.04 → v9.08 phase was substantively complete.**
   Hybrid intelligence (v9.04) + substrate hygiene (v9.05) +
   lens-watching-itself (v9.06) + Pheromone rotation (v9.07) +
   showroom polish (v9.08) form a coherent cognitive-layer
   completion arc. Stopping mid-arc would have been worse than
   shipping it through. The ratio is high because the work was
   bundled.

2. **Layer-1 work is not blocked, just unprioritized.** The
   v8.97 WebAuthn ship landed real Layer-1 work. v9.x had no
   pending Layer-1 Sanctum-class items in the queue. Layer-1
   advances need a TRIGGER (new external need, security gap,
   feature request); the cognitive layer was triggered by the
   2026-05-14 macro scan.

3. **Position A's moratorium would be brittle.** The cognitive
   layer surfaces real bugs (v9.05 / A1 — F5 soldier-exemption
   constitutional violation) that need shipping. A moratorium
   would force every fix through Sanctum, slowing the Pattern
   #20 cycle.

4. **Position B's per-ship budget over-constrains.** Some ships
   are genuinely focused (the v9.07 Pheromone rotation
   implementation was Layer-2/3 only and that was correct). A
   blanket "every ship touches Layer 1" rule would have prevented
   that ship.

The architect's caution on C: it requires the operator to
**actively look for Layer-1 advances**. Without that vigilance,
the ratio could continue to drift. v9.10's first ship should
deliberately include a Layer-1 candidate (e.g., a new use case,
or address Arc B Phase 2.5 deferred items, or open the multi-
region Sanctum).

## IV. Open questions for VANTA

1. **Position?** A, B, or C.

2. **If C: what's the next Layer-1 candidate?** Architect-suggested:
   - Arc B Phase 2.5 multi-instance scaling (gated on production-
     scale data; could be opened defensively now)
   - Arc B Phase 3 multi-region (operator-driven trigger)
   - A new use case (UC-13?) addressing a real-world identity gap
     that v8.97 WebAuthn didn't cover

3. **Tracking?** Architect-suggested: ai-architect's brief gains a
   "Layer ratio (last 5 ships)" line so operator can spot drift.

## V. Decision

**Position C (defer; current ratio is correct for current phase).**
VANTA in-chat 2026-05-15: *"proceed with the architects recommendation"*
— authorizing Position C for this Sanctum and Position B for the
v9.09 S1 Sanctum (watcher-node-id-alignment) in the same letter.

Three §IV resolutions per architect-recommended defaults:
- §IV.1 — Position: C (defer; trust emergent rebalancing with
  vigilance per architect's caution)
- §IV.2 — next Layer-1 candidate: Pheromone rotation framework SQL
  self-tests (the v9.07 framework shipped with end-to-end drill but
  no SQL-level structural enforcement; section S in 08_tests.sql
  closes that gap and is naturally Layer-1 because it touches
  `polaris_sql/`). Architect-suggested Arc B Phase 2.5 multi-instance
  scaling and UC-13 deferred to a future ship under explicit operator
  trigger.
- §IV.3 — tracking: `scripts/ai-architect.sh` gains a "Layer ratio
  (last 5 ships)" line in its brief so operator can spot drift.

## VI. Outcome

Shipped as v9.10 same surface as decision.

**Records:**
- This file (sanctum/2026-05-15-cognitive-layer-ratio.md;
  Status updated to DECIDED + CLOSED)
- meta/sanctum-index.md entry refreshed
- ROADMAP.md gains "Layer-1 candidates" section at top documenting
  next deliberate Layer-1 advances
- scripts/ai-architect.sh gains "Layer ratio (last 5 ships)" line
  in `emit_outlook` (computes from CHANGELOG-listed ship layers)
- v9.10 CHANGELOG entry references this Sanctum
- Structural invariants in TestWave10V910 pin the implementation

**Implementation:**
1. `ROADMAP.md` — new top-of-file §"Layer-1 candidates (per S2
   Position C)" section with 3 enumerated candidates + cadence rule
2. `scripts/ai-architect.sh` — `emit_outlook()` gains Layer-ratio
   compute (parses CHANGELOG.md last 5 entries; tags Layer 1/2/3/4
   from file paths; emits one-line ratio so drift is grep-visible)
3. `polaris_sql/08_tests.sql` — new section S with 10 SQL self-tests
   for v9.07 Pheromone rotation framework (S.1-S.10). **This is
   v9.10's deliberate Layer-1 ship per S2 §III architect requirement.**

**Live drill verified**: ai-architect.sh emits "Layer ratio (last 5
ships): L1×1 L2×3 L3×4 L4×2" line; section S 10 SQL self-tests pass
during `00_load_all.sql` smoke load.

**Pattern #20 Constitutional Discipline 13th instance** in the
v8.84/v8.87/v8.90/v8.91/v8.94/v8.95/v8.96/v8.97/v9.04/v9.06/v9.07/
v9.08/v9.10/**v9.10** series (S2 closes alongside S1 in the same ship).

## VII. Cross-references

- meta/polaris-self-roadmap-3-2026-05-15.md item S2 (the
  surfacing)
- meta/architect.md (the persona that should track this)
- v8.97 WebAuthn (last substantive Layer-1 ship)
- v9.04 → v9.08 CHANGELOG entries (the ships under review)
- MISSION.md (the constitution naming Polaris as
  identity-token-system)
