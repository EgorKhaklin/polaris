# Sanctum: arc-e-legion-structure-with-tactics

**Date:** 2026-05-13
**Petitioner:** agent (Claude, Opus 4.7) speaking as the Architect
**Principal:** VANTA
**Trigger:** Mid-arc structural refinement. VANTA observed in chat: *"so basically each hydra watcher is like a roman general who has their own legion og cohort ants? if os maybe we should allow each watcher to recruit more cohorts /// have their own tactices... lets give them roman tactics"*. The metaphor maps elegantly to the existing 7-watcher + 12-ant cohort topology and resolves a real organizational gap (the Phase 2 ants currently have no formal home).
**Risk class:** MEDIUM (structural reorganization of Mycelium under Arc E; preserves all four constitutional principles and G6-G9 architectural guards; additive on top of Phase 2)
**Status:** DECIDED
**Architect brief ID:** arch-2026-05-13 (auto, plus this Sanctum's §IV)

---

## I. The Matter

Reorganize the 12 Mycelium ants into 7 **Legions**, each commanded by a **Legatus** (one per HYDRA watcher domain), each operating under one of five **Roman tactics**. Grant each Legatus autonomous recruitment authority within Arc E.

## II. Preparation

**The metaphor.** Each HYDRA watcher is a domain expert without a cohort to command. The 9 Phase-2 ants (v8.63) are domain-themed but organizationally homeless. Roman legion structure resolves the gap: a Legatus (general) commands legionnaires (ants); the Legatus chooses tactics; the legion is the unit of organization. The metaphor maps so cleanly that it is almost forced.

**Current state (post-v8.63):**

- 12 ants, flat list in `polaris_swarm/ants/__init__.py::ALL_ANTS`
- Colony runner deploys all ants identically; no organizational structure
- Each ant happens to scan a HYDRA-watcher-themed slice but doesn't belong to anyone
- HYDRA's 7 watchers are runtime-active but have no swarm-side counterpart

**The proposed structure:**

```
polaris_swarm/
├── base.py                  (Ant, Pheromone, decay — unchanged)
├── colony.py                (top-level runner — deploys legions, not ants)
├── legions/                 NEW
│   ├── __init__.py          (ALL_LEGIONS — 7 Legatus modules)
│   ├── base.py              (Legion base + 5 tactic dispatchers)
│   ├── legio_schema.py
│   ├── legio_cognitive.py
│   ├── legio_security.py
│   ├── legio_mission.py
│   ├── legio_adversary.py
│   ├── legio_performance.py
│   └── legio_trajectory.py
└── ants/                    (12 legionnaires, unchanged code)
```

**The five tactics.** Each Legatus chooses one default tactic; operators can override per-run.

| Tactic | Doctrine | Software behavior |
|---|---|---|
| **TESTUDO** | All shields raised; cohort moves as one mass | Every ant scans; outputs are aggregated. High-confidence single signal. |
| **TRIPLEX ACIES** | Hastati first; principes if pressed; triarii at crisis | Tier 1 (fast/cheap) ants run; if any fire, Tier 2 (medium) runs; if any fire, Tier 3 (expensive) runs. Stops at first silent tier. |
| **CUNEUS** | Veteran lead pierces; rest follow through the gap | One designated lead ant fires; the rest scan only if the lead found something. Trigger-driven cascade. |
| **VEXILLATIO** | General sends focused detachment on a specific mission | Operator-driven scope: `--legio security --focus "route:/api/zk/*"`. Cohort scans only matching nodes. |
| **AUXILIA** | Borrow allied troops from another legion for cross-domain work | A legion temporarily activates ants from another legion when evidence requires (security calling api-doc-coverage during a CSP investigation). |

**Per-legion default tactic (initial assignments):**

| Legion | Ants | Default tactic | Rationale |
|---|---|---|---|
| Schema | ant_aor_immutability, ant_fk_cascade_guard | TESTUDO | No false positives on AoR invariants |
| Cognitive | ant_stale_script, ant_pattern_warmth | TESTUDO | Both cheap; aggregate is fine |
| Security | ant_csp_health | TESTUDO | Single ant; tactic is trivial but uniform |
| Mission | ant_done_list_arithmetic, ant_sanctum_outcome | TESTUDO | Independent slices; aggregate |
| Adversary | ant_adversary_walk_complete | CUNEUS | Single-ant lead; structurally meant to escalate |
| Performance | ant_atlas_endpoint_health, ant_api_doc_coverage | TESTUDO | Both fast |
| Trajectory | ant_ship_burst, ant_journal_silence | TRIPLEX_ACIES | ship_burst (hastati) → journal_silence (principes) when burst already firing |

Tactic richness grows as cohorts grow. Today most legions use TESTUDO; that's expected at 12-ant scale. The structure is what's being installed today.

**Recruitment authority.** VANTA approved autonomous recruitment within Arc E: a Legatus can add a new ant to its cohort without requiring a separate Sanctum, as long as G6-G9 still pass. Recruitment is documented in `polaris_swarm/legions/legio_X.py::ANTS` list; the structural-invariant `test_every_ant_belongs_to_exactly_one_legion` enforces the partition.

**Preservation of guards:**

- **G6** (no ant ↔ ant imports) — preserved. Legions import ants; ants do NOT import legions. One-way knowledge.
- **G7** (decay deterministic) — unchanged. Decay function untouched.
- **G8** (no LLM in `polaris_swarm/`) — preserved. Legions are pure dispatch logic.
- **G9** (Pheromone append-only) — unchanged. Same table, same trigger.

**New G-guards proposed (G10-G11):**

- **G10**: every ant belongs to exactly one Legion. Partition contract.
- **G11**: ants do NOT import from `polaris_swarm.legions`. Reverse-direction G6.

**Blast radius:**

- 1 new directory: `polaris_swarm/legions/`
- 1 new base module + 5 tactic dispatchers
- 7 new legio_*.py modules (10-30 LOC each)
- Refactor `colony.py` to be legion-aware (preserve `deposited_by=ant.NAME` for AoR; add `legio` field to evidence JSONB)
- Extend `scripts/ai_swarm_bloom.py` with `--by-legio` mode
- 5 new structural-invariants under `TestMyceliumLegions`
- MISSION.md: Arc E gets E6 ✅
- ROADMAP.md: v13 gets R13-6 ✅
- ~80-100 LOC of new structural code; 0 LOC of new ant code

**Audit-of-record continuity.** The Pheromone schema is unchanged; `deposited_by` still records the ant name, never the legion name. This preserves the principle that the actual scanner is what gets recorded. The legion membership lives in evidence JSONB and in the legion module's source, both of which are git-tracked.

## III. Alternatives considered

1. **Option A — Full legions + 5 tactics + Sanctum (CHOSEN).** Architect's recommendation. See §IV.

2. **Option B — Minimal legions, defer tactics.** Just the organizational structure (7 legio modules each owning ants), with only TESTUDO. LOW-risk under existing Arc E authority. Rejected because tactics ARE the doctrine; without them this is just renamed lists.

3. **Option C — Defer entirely.** Open a design-only Sanctum, ship later. Rejected because VANTA chose A in chat; the design is fresh; the burst-pressure cost is the same whether we ship today or tomorrow.

4. **Option D — Reject the framing.** Keep ants flat; add a `LEGIO` metadata field on each ant for filtering only. Rejected because the structural insight (Legatus has tactics) is real; collapsing to metadata loses the doctrine.

## IV. Recommendation

**Option A — Full legions + 5 tactics + autonomous recruitment within Arc E.**

Reasoning:

1. **The metaphor maps without strain.** Each HYDRA watcher is a Legatus; each ant is a legionnaire. The mapping is not forced; the structural correspondence is already there.

2. **It resolves a real gap.** v8.63's ants are domain-themed but organizationally homeless. The legion structure makes them belong.

3. **It does NOT re-centralize.** Watchers were never the synthesis problem; host.py was. Watchers are domain experts with read-only scans. Elevating them to Legatus status is recognizing what they already are.

4. **Tactics are genuinely pluggable.** Five tactics implement five distinct deployment patterns. Each Legatus picks one as default; operators can override. The colony runner does not interpret tactics; it dispatches.

5. **G6-G9 all hold; G10-G11 extend the family.** The architectural guards scale to the new structure without compromise.

6. **Audit-of-record is preserved.** The Pheromone table is unchanged. Legion membership lives in evidence + source code, both git-tracked.

7. **Recruitment is rate-limited by structure, not bureaucracy.** A new ant is one file under `ants/` plus one line in a `legio_X.py::ANTS` list. G6 + G10 enforce partition correctness automatically. No new Sanctum per ant.

**The shape the Architect will build:**

- Phase E6.1: `legions/base.py` with Legion ABC + TacticConfig + 5 tactic dispatchers (TESTUDO, TRIPLEX_ACIES, CUNEUS, VEXILLATIO, AUXILIA).
- Phase E6.2: 7 `legio_*.py` modules, each with its `ANTS`, `TACTIC`, `LEGATUS` declaration.
- Phase E6.3: Refactor `colony.py::run_colony` to iterate `ALL_LEGIONS`, deploy each via its tactic, deposit findings with `evidence['legio']` populated.
- Phase E6.4: Extend `ai_swarm_bloom.py` with `--by-legio` group-by mode.
- Phase E6.5: 5 new tests (`TestMyceliumLegions`): legion count == 7; ant partition correctness; tactic-config validity; ant-doesn't-import-legion (G11); tactic-dispatch determinism.
- Phase E6.6: MISSION + ROADMAP + CHANGELOG + journal + close Sanctum.

**Cost of opening this arc now.** TrajectoryWatcher already flags 2026-05-13 at 15 ships. Shipping this makes it 16. The Architect named this in chat; VANTA chose to proceed. Pattern realized: VANTA shipping under burst is operator-revocable; the agent surfaces and defers.

## V. What's needed from VANTA

Approved in-chat 2026-05-13 via AskUserQuestion:
- **Scope:** Option A — Full legions + 5 tactics (Sanctum)
- **Recruitment:** Yes — autonomous within Arc E

## VI. Decision

A + autonomous recruitment — Full legions with 5 Roman tactics, autonomous Legatus recruitment within Arc E

## VII. Outcome

v8.64 shipped. 12 ants reorganized into 7 Legions; 5 tactical dispatchers (TESTUDO/TRIPLEX_ACIES/CUNEUS/VEXILLATIO/AUXILIA); G10 + G11 added; 5 new TestMyceliumLegions tests (117→122). TRIPLEX_ACIES demonstrated live: Legio Trajectory escalated from ship_burst (Tier 1, 4 findings) to journal_silence (Tier 2, silent). AoR preserved. Recruitment is autonomous within Arc E. See CHANGELOG ## v8.64 and journal/2026-05-13.md.

