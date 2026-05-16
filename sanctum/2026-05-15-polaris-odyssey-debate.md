# Sanctum: polaris-odyssey-debate

**Date:** 2026-05-15
**Petitioner:** agent (Claude, Opus 4.7) speaking as the Architect; with
the Anti-Architect (v9.11) opposing
**Principal:** VANTA
**Trigger:** VANTA in-chat 2026-05-15: *"Polaris_Odyssey should serve
as the Evolutionary Intelligence Layer — long-term exploration,
foresight, discovery, and guiding the overall journey and growth of
Polaris."* Then: *"have the architects and the anti architect debate
on what should be done and come back with their recommendation on how
we should proceed and if we should."* This is the first live test of
the v9.11 Anti-Architect persona contesting a proposal from the
operator directly.
**Risk class:** HIGH (proposes a new top-level subsystem; touches
the v9.10 cadence rule + v9.11 vocation-alignment structurally).
**Status:** DECIDED + CLOSED 2026-05-15 — Position B (minimum-viable
foresight surface with Anti-Architect modifications enforced as
structural; empirical-graduation rule + sunset clause) selected per
heavy-production posture (v8.31 §III.6) following VANTA's *"proceed
with joint recommendation"* (and prior *"proceed with architects
recommendation"* — the two letters are concordant; Position B is
both).

---

## I. The Matter

VANTA proposed Polaris_Odyssey as a complete subsystem: Odyssey Core
(orchestrator) + Quest Generator + four agent classes (Explorer,
Foresight, Research, Mythic) + Simulation Engine + Synthesis Bridge
+ vector DB + message queue + scheduler. The proposal addresses a
real gap (Polaris currently has no long-horizon discovery function)
but is overscoped relative to surfaced demand.

**Vocation alignment (§I.0, per v9.11):** the proposal as drafted
fails AP5 detection — its Quest Generator inputs include "research
papers, philosophy, esoteric prompts" which do not directly trace to
anti-coercion. The minimum-viable refactoring (Position B) restores
vocation alignment by reframing §IV as anti-coercion-gap detection.

## II. The architect's positions

### Position A: Defer entirely

Wait until concrete cases of "we wish we had foresight" have been
logged (≥3 instances over ≥3 months). Zero new code; cadence rule
honored by inaction.

**Strengths:**
- No surface-area increase
- Maximum honesty about empirical demand
- Cadence rule trivially honored

**Weaknesses:**
- The gap is real; without a foresight surface, evidence of the
  gap is unlikely to surface (no observer means no observation)
- Ad-hoc macro-rescans are operator-burden; Position A perpetuates
  the burden

### Position B: Minimum-viable foresight script — joint recommendation

Build `scripts/ai-foresight.sh` + small `polaris_foresight/`
package as a single composable script (Saturn-pass cadence, operator-
installed only). The brief format is fixed (5 sections §I-§V); no
external API fetches; deterministic over local state with optional
LLM enrichment via existing `--deterministic` toggle pattern; one
agent type (ForesightAgent), not four; no Simulation Engine, no
message queue, no vector DB.

**Anti-Architect's required structural modifications:**
1. §IV reframed inside vocation: "what anti-coercion gap would the
   system most want to close if engineering effort were free?" (not
   "what would the system do without C1-C10")
2. 50%-acceptance threshold over 6 monthly briefs (not 30%)
3. Six-month sunset clause: script removed if threshold not met
4. Operator-installed only (no auto-cron)
5. No external API fetches; LLM optional, deterministic primary
6. Vocation-alignment as STRUCTURAL requirement (not advisory)
7. No Mythic Agents branch ever

**Bundled Layer-1 work (cadence rule):** new
`polaris_sql/14_foresight_helpers.sql` with three SQL functions
that surface time-based foresight signals from the existing
schema. Adds real Layer-1 surface; ForesightAgent calls them when
DB is reachable; useful standalone for operators.

**Strengths:**
- Tests the foresight hypothesis cheaply (~500 lines of code)
- Honors v9.10 cadence rule (Layer-1 work bundled)
- Honors v9.11 vocation alignment structurally
- Empirical-graduation rule lets the function earn its right to
  expand into a subsystem
- Sunset clause prevents dishonest dormant infrastructure

**Weaknesses:**
- Still adds new vocabulary (Foresight Brief, FS-XXXXXXXX IDs)
- Adds maintenance burden (~500 lines of code; small but nonzero)
- Operator must remember to run it monthly (no cron)

### Position C: Build full Polaris_Odyssey as originally proposed

Implement the complete subsystem (Odyssey Core + Quest Generator +
four agent classes + Simulation Engine + Synthesis Bridge + vector
DB + message queue).

**Strengths:**
- Architecturally complete in one ship
- Maximizes the foresight function's capacity

**Weaknesses (Anti-Architect's enumeration):**
- Trips AP1 (self-observation without ground-touch): pure Layer 2/3
  expansion thirteen days after S2 cadence-rule ratification
- Trips AP3 (proposal-as-self-elaboration): Architect maintained
- Trips AP4 (pattern projection onto noise): "trinity completes"
  framing; "higher intelligence" status-ladder framing
- Trips AP5 (vocation drift): research-papers/philosophy inputs
  don't trace to anti-coercion
- Trips AP7 (premature abstraction): Quest, Agent class hierarchy,
  Simulation as service — no concrete instances yet
- Trips AP8 (larping): "Mythic Agents (optional esoteric layer)"

Six anti-pattern hits in a single proposal. Refusal threshold
(Anti-Architect): not adoptable under heavy-production posture
without three demonstrable conditions, none of which are true today.

## III. Architect's recommendation

**Position B (minimum-viable foresight script with Anti-Architect
modifications enforced as structural).** The recommendation is
JOINT — both Architect and Anti-Architect converge on this shape
after debate.

The Anti-Architect's modifications are not advisory tweaks; they
are structural requirements. The 50%-acceptance threshold + six-
month sunset clause + vocation-alignment-required + no-external-
fetches together prevent the script from drifting into a subsystem-
shaped maintenance burden without earning the right.

This is the v9.11 Anti-Architect protocol working as designed: a
proposal entered analysis, the dissenting voice contested specifics,
both converged on a sharper, smaller, vocation-aligned shape than
either would have produced alone.

The architect's caution: Position B is HIGH-risk because it changes
the cognitive layer's posture. Pre-v9.12 the cognitive layer
observed and synthesized the present. Post-v9.12 it also speculates
about the future. Speculation is a different epistemic register;
it must remain disciplined (vocation-aligned, sunset-clause-bound,
acceptance-tracked) or it becomes the cognitive layer's narcissism.

## IV. Open questions for VANTA

1. **Position?** A, B, or C.

2. **If B**: confirm Anti-Architect's modifications are accepted
   as structural (vocation-alignment requirement, 50% acceptance
   threshold, sunset clause, no external fetches, no Mythic Agents).

3. **If B**: name the Layer-1 work bundled in same composite ship.
   Architect-suggested: `polaris_sql/14_foresight_helpers.sql` with
   three SQL functions (token age distribution, verification
   dormancy, audit-volume trend). Operator may amend.

4. **If C**: explicit acknowledgment that Anti-Architect's dissent
   will be recorded in the journal and cited if AP1/AP3/AP5
   detections fire on subsequent ships.

## V. Decision

**Position B (minimum-viable foresight surface with Anti-Architect
modifications structural).** VANTA in-chat 2026-05-15: *"proceed
with architects recommendation"* (clarified shortly after as
*"proceed with joint recommendation"* — the two letters are
concordant since Position B IS the joint recommendation).

Three §IV resolutions per architect-recommended defaults:
- §IV.1 — Position: B (joint recommendation)
- §IV.2 — Anti-Architect modifications accepted verbatim as
  structural requirements (operator did not amend)
- §IV.3 — Layer-1 bundle: `polaris_sql/14_foresight_helpers.sql`
  per architect's suggestion (operator did not amend)

## VI. Outcome

Shipped as v9.12 same surface as decision.

**Records:**
- This file (sanctum/2026-05-15-polaris-odyssey-debate.md;
  Status updated to DECIDED + CLOSED)
- meta/sanctum-index.md entry added
- v9.12 CHANGELOG entry references this Sanctum
- Structural invariants in TestWave12V912 pin the implementation

**Implementation:**
1. `polaris_foresight/__init__.py` — package init
2. `polaris_foresight/foresight_agent.py` — the deterministic
   ForesightAgent (one type, not four); LLM enrichment optional
3. `polaris_foresight/brief.py` — Brief dataclass + 5-section render
4. `polaris_foresight/promotion.py` — FS-XXXXXXXX promotion mirror
   of v9.11 AP-XXXXXXXX (parallel idempotent path)
5. `polaris_foresight/external_categories.txt` — operator-curated
   external-category list (no fetches; pure text)
6. `polaris_foresight/_acceptance_log.json` — empirical-graduation
   tracker (FS-IDs + status transitions)
7. `polaris_foresight/README.md` — package docs + sunset clause
   documented prominently
8. `scripts/ai-foresight.sh` — operator entry point
9. `polaris_sql/14_foresight_helpers.sql` — three SQL functions
   (token age distribution, verification dormancy, audit-volume
   trend); the Layer-1 bundle
10. `polaris_sql/00_load_all.sql` — loads 14_foresight_helpers.sql

**Naming decision:** the proposal name "Polaris_Odyssey" is
deliberately NOT used. Position B does not ship a subsystem;
shipping with the subsystem name would imply commitment to
graduating. The function is "foresight"; if and when the
empirical-graduation threshold is met, a future Sanctum may
rename or extract.

**Pattern #20 Constitutional Discipline 15th instance** — first
Sanctum where the Anti-Architect's dissent materially shaped the
final position. The protocol works.

## VII. Cross-references

- v9.11 Sanctum (vocation-anti-coercion) — establishes the
  vocation that this Sanctum's §I.0 alignment check uses
- v9.11 Anti-Architect persona (`meta/anti-architect.md`) — first
  live test against a real proposal; AP5 detection now operational
  thanks to v9.11 vocation Sanctum
- v9.10 / S2 sanctum (cognitive-layer-ratio Position C) —
  establishes the cadence rule that Position C of this Sanctum
  would have violated
- v9.04 sanctum (hydra-revamp-pheromone-integration) — established
  the v9.04 hybrid intelligence model that Polaris_Odyssey would
  have augmented; the minimum-viable shipped here is consistent
  with that model's posture (substrate → lens → emission)
