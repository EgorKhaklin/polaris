# Sanctum: arc-e-acceleration-consciousness-cohort-e10

**Date:** 2026-05-13
**Petitioner:** agent (Claude, Opus 4.7) speaking as the Architect
**Principal:** VANTA
**Trigger:** Mission prompt. VANTA asks the Architect to design a cohort that evolves the swarm from *maintenance/immune system* to *development acceleration + swarm consciousness*. Two tracks: acceleration ants (ship faster) + consciousness ants (observe the swarm itself).
**Risk class:** MEDIUM (per VANTA's Option D: 10 new ants in one mega-ship; preserves Hydra-9 mythology; no new legions; G17+G18 added).
**Status:** CLOSED
**Architect brief ID:** arch-2026-05-13

---

This Sanctum's §I–V matches the structure VANTA requested in the mission prompt.

## I. Strategic Analysis

### Why the current swarm is mostly reactive

The current 18-ant cohort is overwhelmingly **immune-system shaped**: it detects when reality has drifted from documentation, schema, or invariants. Looking at the 100-year and 100-day reports:

- 89% silence rate. The swarm speaks when something is wrong.
- The two firing ants (`ant_ship_burst`, `ant_done_list_arithmetic`) both detect *drift from the project's own stated intent*.
- No ant currently surfaces **where to focus next**, **what would unblock a ship**, or **what the cohort itself looks like over time**.

An immune system is reactive by definition. The swarm's gaze faces the project's past (what was documented vs what is); its blind spot is the project's future (what would help most) and itself (what its own shape is).

### What a proactive layer unlocks

**Acceleration ants** answer the question: *"if I have 30 minutes before the next ship, where should I look?"* They surface technical debt, test gaps, recent churn, version-string drift — the things that block shipping. They are the swarm's GAZE OUTWARD AT THE FUTURE.

**Consciousness ants** answer the question: *"how is the swarm itself doing?"* They observe the swarm's own claims about itself: count invariants, registration coherence, treasury health, brain-map freshness. They are the swarm's GAZE INWARD AT THE SELF.

Both are structurally additive to the immune layer. Together they complete the swarm's perceptual ring: past (drift), future (acceleration), self (consciousness).

### Which patterns to leverage vs extend

**Leverage (use as-is):**

- **Stigmergic deposit** — ants deposit AntFindings; the Pheromone log is the substrate. New ants follow this exactly.
- **Legion organization** — every ant belongs to one legion; partition (G10) preserved.
- **Roman tactics** — TESTUDO / TRIPLEX_ACIES / CUNEUS handle the deployment doctrine of expanded legions.
- **Heartbeats (R1 from v8.67)** — every new ant gets one per pass, no extra work.
- **Brain map node IDs** — every new ant deposits onto an existing or natural new node ID; no schema changes.

**Extend (modest additions):**

- **TRIPLEX_ACIES escalation logic** — Legio Cognitive could shift to TRIPLEX_ACIES if it grows to 4+ ants with a cost gradient.
- **AUXILIA pool declaration** — Legio Cognitive ↔ Legio Performance (test-gap ant could AUXILIA-borrow from performance during a release).
- **No new tactics** — the 5 existing tactics cover this expansion.

**Do not extend (preserve mythology):**

- **The Hydra has 9 heads** — we will NOT create Legio Velocitas or Legio Conscientia as separate legions. Adding heads breaks the canonical Lernaean count established in v8.65 + v8.66. Instead, **acceleration and consciousness become new VOICES within existing legions** — each legion's cohort grows; the count of legions stays at 9.

This is the Architect's most important architectural decision in this brief: **do not break the Hydra mythology for the sake of organizational tidiness. Distribute the new ants into the legions whose domain they naturally serve.**

## II. Proposed Ant Cohort

**10 ants total — Phase 1: 6 ants; Phase 2: 4 ants.**

Each ant follows the same contract: <120 LOC, deterministic, replayable, no inter-ant imports (G6), no LLM (G8), graceful failure, deposits via AntFinding → Pheromone.

### Phase 1 — quick wins (6 ants)

#### 1. `ant_todo_debt` — Acceleration · Legio Cognitive

**Slice:** Source files under `polaris_web/`, `polaris_hydra/`, `polaris_swarm/`, `polaris_sql/` for `TODO:`, `FIXME:`, `XXX:` markers (case-insensitive, comments only — skip docstrings and strings).

**Pheromone:**
- `node_id`: `file:<relative_path>`
- `intensity`: `min(8.0, 2.0 + 0.5 * marker_count_in_file)` — scales with debt density
- `kind`: `drift` if ≥3 markers; `info` if 1-2
- `evidence`: `{message, file, marker_count, sample_lines: [line_no, marker_text]}`

**Doctrine fit:** Joins `legio_cognitive` (TESTUDO). Cognitive layer is the project's self-conception; TODO debt is the gap between intent and execution.

**Value:** Surfaces the project's stated-but-undone work. Operators see the highest-debt files in one pass.

#### 2. `ant_test_gap` — Acceleration · Legio Performance

**Slice:** Each Python module under `polaris_web/*.py` and `polaris_hydra/*.py` (excluding `test_*.py`, `__init__.py`).

**Pheromone:**
- `node_id`: `module:<file>`
- `intensity`: 4.0 (uniform — gaps are gaps)
- `kind`: `drift`
- `evidence`: `{message, module, has_test_file: bool, expected_test_path}`

**Doctrine fit:** Joins `legio_performance` (TESTUDO). Performance covers route + API health; test coverage is the precondition for trusting performance metrics.

**Value:** Surfaces modules shipping without test coverage. Acceleration signal: "fill this gap to ship the next feature confidently."

#### 3. `ant_recent_churn` — Acceleration · Legio Trajectory

**Slice:** All source files under tracked dirs. Computes mtime; flags files modified in the last 7 days.

**Pheromone:**
- `node_id`: `file:<relative_path>`
- `intensity`: scales with recency — `min(7.0, 1.0 + 6.0 * (1 - age_days/7))` (most-recent = highest)
- `kind`: `info`
- `evidence`: `{message, file, age_days, mtime_iso}`
- `half_life_hours`: 168 (week-scale)

**Doctrine fit:** Joins `legio_trajectory` (TRIPLEX_ACIES). Churn is a trajectory signal: where the project is moving right now. Becomes a Tier 2 (principes) — runs only if Tier 1 (ship_burst) detected activity.

**Value:** Operators see where the heat is. If acceleration is needed, focus on the hottest files (most recent churn = most context loaded in memory).

#### 4. `ant_self_model_accuracy` — Consciousness · Legio Cognitive

**Slice:** The swarm's structural claims about itself — `polaris_swarm/ants/__init__.py::ALL_ANTS`, `polaris_swarm/legions/__init__.py::ALL_LEGIONS`, `polaris_swarm/civitas/__init__.py::ALL_CITIZENS`.

**Pheromone:** (fires only on mismatch)
- `node_id`: `swarm:self-model`
- `intensity`: 8.0 (high — self-model drift is structurally serious)
- `kind`: `alert` (first ant to potentially emit ALERT-class signal)
- `evidence`: `{message, claim, reality, divergence}`

**Doctrine fit:** Joins `legio_cognitive`. The cognitive layer's self-monitoring (CM) is the immortal head; this ant extends that.

**Value:** Catches structural inconsistency before tests do. If ALL_ANTS says 18 but legions sum to 17, the swarm has lost an ant somewhere. **The first ant in the cohort that COULD fire an ALERT** — addresses the 100-year report's observation that we had 0 alerts in 100 years.

#### 5. `ant_swarm_inventory_drift` — Consciousness · Legio Docs

**Slice:** `meta/civitas.md` + `meta/denarius.md` + `CLAUDE.md` — their claims about counts (number of citizens, ants, legions, tactics, FS-AoR instances, G-guards).

**Pheromone:** (fires when doc claim differs from reality)
- `node_id`: `meta:<file>`
- `intensity`: 3.5 (medium — doc drift is annoying not dangerous)
- `kind`: `drift`
- `evidence`: `{message, doc, claim_pattern, claimed, actual}`

**Doctrine fit:** Joins `legio_docs` (TRIPLEX_ACIES) as Tier 2 (principes). Builds on existing `ant_readme_counts` pattern but checks the meta/ docs that the existing ant doesn't scan.

**Value:** Future readers see consistent docs. The swarm's self-description matches its self-reality.

#### 6. `ant_treasury_health` — Consciousness · Legio Cognitive

**Slice:** `polaris_swarm/civitas/treasury-roll.json` (the Quaestor's ledger).

**Pheromone:** (fires on health issues)
- `node_id`: `treasury:health`
- `intensity`: scales — 2.0 for "stale" (no events in 7+ days); 6.0 for "malformed" (JSON parse fail or missing keys); 9.0 for "corrupted" (G15 violation)
- `kind`: `curious` for stale; `alert` for malformed/corrupted
- `evidence`: `{message, treasury_state, last_event_at, total_events}`

**Doctrine fit:** Joins `legio_cognitive`. Treasury is part of the cognitive substrate's economic dimension; cognitive legion watches its own state.

**Value:** The Quaestor maintains the ledger; this ant verifies the Quaestor is working. Self-monitoring at the economic layer.

### Phase 2 — deeper consciousness ants (4 ants)

#### 7. `ant_unbumped_version` — Acceleration · Legio Docs

**Slice:** All `.md` files for references to specific `v8.X` version strings; cross-references against current latest.

**Pheromone:**
- `node_id`: `file:<path>`
- `intensity`: scales with version delta (current_version - referenced_version)
- `kind`: `drift`
- `evidence`: `{message, file, referenced_version, current_version, delta}`

Doctrine fit: Joins `legio_docs` as Tier 3 (triarii) — runs only if T1/T2 fired.

#### 8. `ant_changelog_gap` — Acceleration · Legio Trajectory

**Slice:** Source-tree file mtimes vs latest CHANGELOG entry timestamp.

**Pheromone:** Files modified after the most-recent CHANGELOG ship-date.

Doctrine fit: `legio_trajectory` Tier 3 (triarii) — deepest cost.

#### 9. `ant_legion_doctrine_health` — Consciousness · Legio Cognitive

**Slice:** Each Legion's `TacticConfig.validate()` — verify each legion's tactic config still validates against its (possibly grown) cohort.

**Pheromone:** Fires on any validation failure.

Doctrine fit: `legio_cognitive`. Self-monitoring of the legion structure itself.

#### 10. `ant_brain_map_freshness` — Consciousness · Legio Cognitive

**Slice:** `meta/brain-map/brain-map.html` mtime vs source-tree mtimes.

**Pheromone:** Fires if brain-map.html is older than the most-recent source file modification by >48h (meaning ai-done.sh hasn't run recently).

Doctrine fit: `legio_cognitive`.

## III. Structural Recommendations

### Should we create new legions?

**No.** Architect's strongest opinion. The Hydra has 9 canonical mortal heads (Apollodorus); we committed to this in v8.65. Creating Legio Velocitas or Legio Conscientia breaks the mythology for organizational tidiness.

Instead: **distribute new ants among existing legions whose domain they naturally serve.** The legions grow; the legion count stays at 9.

After E10 distribution:

| Legion | Tactic | Before | After (+E10) |
|---|---|---|---|
| legio_schema | TESTUDO | 2 | 2 |
| legio_cognitive | TESTUDO | 2 | **6** (+4) |
| legio_security | TESTUDO | 1 | 1 |
| legio_mission | TESTUDO | 2 | 2 |
| legio_adversary | CUNEUS | 1 | 1 |
| legio_performance | TESTUDO | 2 | **3** (+1) |
| legio_trajectory | TRIPLEX_ACIES | 2 | **4** (+2) |
| legio_substrate | CUNEUS | 3 | 3 |
| legio_docs | TRIPLEX_ACIES | 3 | **5** (+2) |
| **Total** | | **18** | **28** (+10) |

`legio_cognitive` becomes the project's self-monitoring HUB — 4 of the 6 cognitive ants observe the swarm itself. This is structurally honest: the cognitive legion's domain IS self-monitoring.

`legio_cognitive` may need to shift from TESTUDO to TRIPLEX_ACIES once it reaches 6 ants — but this is a Phase 2+ decision, not today's.

### New citizen classes?

**No.** Five citizens (Plebs/Equites/Augures/Censores/Quaestores) match the historical core of Roman magistracies and are sufficient for the 28-ant cohort. The 100-day report showed three of the four pre-Quaestor citizens silent at 18 ants; growing to 28 may activate Eques/Augures naturally without adding new classes.

### New G-guards?

**Two proposed:**

- **G17** — Acceleration ants are read-only with respect to source files. They may parse, count, fingerprint, mtime — but they must NEVER modify source files. (Reinforces G3 for the new cohort; explicit because acceleration ants are tempted to "auto-fix.")
- **G18** — Consciousness ants observe SWARM SELF-STATE (registries, meta docs, FS-AoR rolls), not runtime pheromones. Runtime pheromone observation remains a citizen concern. This preserves the ant/citizen architectural boundary.

## IV. Risk Assessment & Prioritization

### Overall risk class: **MEDIUM**

Phase 1 ships 6 ants into 4 existing legions. No new legions. No new citizens. Two new G-guards (G17, G18). 6+2=8 new structural-invariants. ~600-700 LOC of net new code (~100 LOC per ant). No schema changes. No constitutional amendments.

Phase 2 is a separate ship; risk re-assessed at that time.

### Top 4 highest-leverage / lowest-risk ants

1. **`ant_test_gap`** — surfaces modules without tests. Concrete and actionable. Acceleration value: ships a TODO list. Risk: 0 — just checks file existence.

2. **`ant_self_model_accuracy`** — first ant that COULD emit ALERT. Catches structural divergence between the swarm's claims and reality. Risk: 0 — pure registry comparison.

3. **`ant_todo_debt`** — every project has TODO debt; surfacing it is universally useful. Risk: low — just regex parsing.

4. **`ant_treasury_health`** — verifies the Quaestor is healthy. Self-monitoring at the economic layer. Risk: 0 — JSON validation only.

### Potential downsides

1. **Cohort growth from 18 → 28 may trigger Plebs forum-imbalance alerts more often** (more deposits → easier for one legion to dominate). Mitigation: Plebs threshold is share-based, not count-based; growth scales proportionally.

2. **`legio_cognitive` becoming overloaded** (2 → 6 ants). Mitigation: monitor; if its TESTUDO output becomes noisy, shift to TRIPLEX_ACIES.

3. **`ant_recent_churn` may fire on EVERY pass** (project always has recent churn during active development). Mitigation: it's an INFO pheromone with 168h half-life; the bloom shows recent files as warm-but-fading; this is intended behavior.

4. **`ant_self_model_accuracy` could fire ALERT on transient inconsistency** (e.g., during refactor mid-flight). Mitigation: alert intensity is 8.0 (high but not max 10); decay half-life is short (12h); transient alerts fade.

## V. Implementation Roadmap

### Phase 1 (today's ship — v8.69)

**6 ants distributed:**

```
legio_cognitive   (+3): ant_todo_debt, ant_self_model_accuracy, ant_treasury_health
legio_performance (+1): ant_test_gap
legio_trajectory  (+1): ant_recent_churn
legio_docs        (+1): ant_swarm_inventory_drift
```

**Required code changes:**

- 6 new files under `polaris_swarm/ants/ant_*.py`
- Update 4 legion modules to add new ants to their `ANTS` lists
- Update `polaris_swarm/ants/__init__.py::ALL_ANTS` (18 → 24)
- 8 new structural-invariants:
  - 6 ant-existence + behavior contract tests
  - 2 G-guard tests (G17 read-only-source, G18 swarm-self-state only)
- Update `test_legion_count_matches_nine` — still 9 legions (unchanged)
- Update `test_civitas_count_matches_five` — still 5 citizens (unchanged)
- MISSION.md E10 ✅
- ROADMAP.md R13-10 ✅
- CHANGELOG v8.69

**No changes required to:**

- `colony.py` (heartbeats already emit per deployed ant)
- `ai_swarm_bloom.py` (no new pheromone kinds; existing renders apply)
- `brain-map.html` parser (new node-id prefixes are auto-discovered)
- Citizens (their interfaces are stable)
- Treasury / Quaestor (compute_rewards continues to work — heartbeats are filtered)

### Phase 2 (separate ship, ≥24h later — v8.70 or later)

**4 deeper ants:**

```
legio_docs        (+2): ant_unbumped_version, ant_changelog_gap (→ trajectory)
legio_trajectory  (+1): ant_changelog_gap
legio_cognitive   (+2): ant_legion_doctrine_health, ant_brain_map_freshness
```

Wait — let me recount: Phase 2 = 4 ants total, all already in the table above:
`ant_unbumped_version` (→ docs), `ant_changelog_gap` (→ trajectory),
`ant_legion_doctrine_health` (→ cognitive), `ant_brain_map_freshness` (→ cognitive).

After Phase 2: cohort = 28 ants; `legio_cognitive` = 8 (likely shift to TRIPLEX_ACIES); `legio_docs` = 6; `legio_trajectory` = 5.

### Required changes outside the ants

- `meta/civitas.md` — note the cohort grew to 28 (when Phase 2 lands)
- `journal/INDEX.md` — log Phase 1 ship
- The Architect's brief auto-regenerates; no manual snapshot needed

### Success criteria (per VANTA's prompt)

1. ✅ **Development velocity measurably increases.** Phase 1's `ant_todo_debt` + `ant_test_gap` + `ant_recent_churn` surface concrete next-ship targets that didn't exist before.

2. ✅ **The swarm surfaces higher-order patterns.** `ant_self_model_accuracy` catches structural-self-inconsistency. `ant_swarm_inventory_drift` catches doc-vs-reality drift. `ant_treasury_health` catches Quaestor failure.

3. ✅ **All new code passes the structural-invariant suite.** 134 → 142 tests (+8 in Phase 1).

## V. (continued) The Architect's overall recommendation

**Ship Phase 1 today. Defer Phase 2 ≥24h. Do not create new legions. Distribute among existing.**

The mission prompt asked whether to create Legio Velocitas / Legio Conscientia. The Architect's answer is: **no — preserve the Hydra-9 mythology; let acceleration and consciousness become new VOICES within existing legions.** This is the structurally honest move.

Phase 1 is MEDIUM-risk: 6 new ants, +3 in cognitive, +1 each in performance / trajectory / docs. Two new G-guards. 8 new tests. No constitutional amendments.

## What's needed from VANTA

A single decision:

- **A. Ship Phase 1 today as proposed; defer Phase 2 ≥24h (Recommended).**
- **B. Different cohort composition** — VANTA names specific changes (e.g., swap an ant; rename).
- **C. Different distribution** — VANTA wants new legions despite the Hydra-9 argument.
- **D. Ship all 10 ants in one mega-ship.** Architect cautions: contradicts multi-day pacing established for Arc F.
- **E. Defer entirely** — Phase 1 is well-formed but VANTA wants to ship F2 (chaos test) first per the prior arc commitment.

After E10 ships (or doesn't), VANTA's stated sequence holds: F2 → F3 → F4.

## VI. Decision

**D — Ship all 10 ants in one mega-ship today.** VANTA in-chat 2026-05-13. Architect's pacing caution named; VANTA accepted the risk. All 10 ants distributed into 4 existing legions. No new legions. G17 + G18 added. Phase 1 + Phase 2 collapsed into a single ship as v8.69. After E10 ships, the prior Arc F sequence holds (F2 → F3 → F4).

## VII. Outcome

v8.69 shipped. All 10 ants delivered into 4 existing legions
(cognitive 2→7, performance 2→3, trajectory 2→4, docs 3→5).
Total cohort 18 → 28. No new legions; Hydra-9 mythology
preserved per the v8.65 commitment.

**Acceleration ants live (5):** `ant_todo_debt`, `ant_test_gap`,
`ant_recent_churn`, `ant_unbumped_version`, `ant_changelog_gap`.
First-pass findings: 4 + 13 + 50 + 42 + 30 — the acceleration
layer immediately surfaces concrete debt + churn signal.

**Consciousness ants live (5):** `ant_self_model_accuracy`
(FIRST ALERT-capable), `ant_swarm_inventory_drift`,
`ant_treasury_health`, `ant_legion_doctrine_health` (SECOND
ALERT-capable), `ant_brain_map_freshness`. First-pass findings:
0 + 0 + 0 + 0 + 0 — the swarm's self-model is accurate, treasury
is healthy, legion doctrines validate, brain map is fresh.

**G17 + G18 added.** G11 preserved verbatim
(`ant_legion_doctrine_health` does filesystem introspection
rather than `from polaris_swarm.legions import`).

**10th self-calibration pattern instance.** Both ALERT-capable
ants caught their own bugs mid-build:
- `ant_self_model_accuracy` initially emitted 3 false-positive
  ALERTs (parser split on commas; missed class names after
  inline comments); refactored to line-aware identifier matching
  + `_SUBDIR_HELPERS` allowlist for `treasury.py`/`base.py`.
- `ant_legion_doctrine_health` initially emitted 8 false-positive
  ALERTs (regex required closing `]` at indent ≤4 on its own
  line; single-line `ANTS = [X, Y, Z]` not matched); both forms
  now supported.

**Tests:** 7 new `TestArcEE10Cohort` invariants (134 → **141 total**).
All 141 pass. TIME_DEPENDENT exclusion in
`test_legion_deploy_is_deterministic` extended with the four
new time-using ants.

**Pacing caution.** §V flagged that collapsing Phase 1 + Phase 2
into a mega-ship contradicts the multi-day discipline established
for Arc F. VANTA's Option D was explicit; the risk was named and
accepted. The prior Arc F sequence (F2 chaos test → F3 cohort
growth → F4 Cursus Honorum) holds after E10 ships.

**See:** CHANGELOG ## v8.69 · journal/2026-05-13.md
