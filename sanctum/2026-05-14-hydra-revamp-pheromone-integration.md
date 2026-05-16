# Sanctum: hydra-revamp-pheromone-integration

**Date:** 2026-05-14
**Petitioner:** agent (Claude, Opus 4.7) speaking as the Architect
**Principal:** VANTA
**Trigger:** VANTA in-chat 2026-05-14: *"We should completely revamp/upgrade polaris_hydra + the watchers so they better suit the project. Then do a full system run / scan / macro scan with the Hydra and the swarm. The Hydra is the centralized intelligence with multiple heads and the swarm is the decentralized intelligence, together combined and working together they are power. Boil the ocean."*
**Risk class:** HIGH (touches the cognitive substrate; HYDRA is the structural form of CM, the meta-constraint; revamp threads new infrastructure across all 9 watchers + adds 4 new constructs).
**Status:** DECIDED + CLOSED 2026-05-14 — Position A (full hybrid-intelligence revamp) shipped as v9.04

---

## I. The Matter

Polaris's HYDRA today (`polaris_hydra/host.py` + 9 watchers) is the
**centralized intelligence**:

- 9 mortal heads (schema, cognitive, security, mission, adversary,
  performance, trajectory, ant_colony, civitas) per the v8.65
  Hydra-9 mythology + v8.72 relocation
- CM is the immortal 10th head (constitutional, narrative)
- Each watcher emits a structured `WatcherReport` (status +
  findings + evidence_summary)
- `Hydra.speak()` synthesizes via Claude Opus 4.7 (with adaptive
  thinking; deterministic fallback)
- The synthesis voice is the Architect persona

The Mycelium swarm (v8.62 commanders + v9.03 soldiers) is the
**decentralized intelligence**:

- 33 commanders + 6 citizens + 8 soldier classes deposit
  Pheromones into the audit-of-record
- Aggregation by `(soldier_class, node_id)`; per-soldier advisory
  locks; F5-exempt soldier tier
- The swarm produces ~1000+ deposits per `--hybrid` cycle
- The bloom heatmap (`scripts/ai-swarm-bloom.sh`) renders intensity
  decay over time

VANTA's framing names the missing connective tissue: **"together
combined and working together they are power."** The two layers
exist; they don't yet TALK to each other.

Concrete gaps:

1. **Watchers don't read Pheromone.** They observe static state
   (files, schema, /api/health) but ignore the swarm's continuous
   deposits. A schema_watcher that doesn't see soldier_db_table_size
   pheromones is missing real-time signal.
2. **No cross-watcher correlation.** Two watchers can both flag
   the same domain (security_watcher's CSP finding + soldier_log_tail's
   ERROR count) without HYDRA noticing they're linked.
3. **No persistent memory.** Each `Hydra.speak()` is one-shot;
   the architect persona's "self-monitoring" section is mostly
   empty because there's no prior-brief archive to compare against.
4. **No action queue.** HYDRA emits findings but doesn't propose
   ranked NEXT MOVES. The architect's six-section brief has a
   "Suggestions" section but it's always one item.
5. **ant_colony_watcher doesn't distinguish v9.03 tiers.** It
   counts pheromones flat; doesn't say "soldier_route_pinger
   silent for 4h" vs "commander legio_substrate silent for 2 days."

The constitutional question: how do we revamp HYDRA to integrate
the swarm WITHOUT breaking C1 (audit-of-record), C10 (value-purity),
G6 (no inter-tier imports), or the Hydra-9 mythology (9 mortal
heads + CM immortal)?

## II. The architect's positions

### Position A: Full hybrid-intelligence revamp — architect-recommended

Add 4 new constructs ALONGSIDE the existing 9 watchers (no new
heads — the mythology stays at 9):

1. **`polaris_hydra/pheromone_reader.py`** — shared, read-only
   module that pulls recent Pheromone deposits, groups by tier
   (commander vs soldier) and class. Watchers import + use as
   needed; ant_colony_watcher gains the heaviest dependency.
2. **`polaris_hydra/correlation.py`** — `CorrelationEngine`
   class run AFTER `Hydra.gather()`. Finds findings across
   different watchers that touch the same `node_id` or domain;
   emits `CorrelatedFinding`s ("schema_watcher index-stale + soldier
   db_table_size growth → likely needs index").
3. **`polaris_hydra/action_queue.py`** — `ActionQueue` synthesizes
   watcher findings + correlations into a RANKED list of
   next-moves with rationale. Each action has a risk class
   (LOW/MEDIUM/HIGH), an estimated effort, and the
   constitutional-constraint-touched list.
4. **`polaris_hydra/brief_archive.py`** — writes each generated
   brief to `journal/hydra/<YYYY-MM-DD>-<HHMM>.md` (creates the
   directory if missing); on next `--save`, computes a delta vs
   the most-recent prior brief (new findings + closed findings +
   intensity drift).

PLUS: refresh the existing 9 watchers to use `PheromoneReader`
where it adds real signal (security_watcher reads soldier_log_tail
errors; performance_watcher reads soldier_route_pinger latency
distribution; schema_watcher reads soldier_db_table_size growth;
cognitive_watcher reads sanctum_freshness; ant_colony_watcher
splits its report by tier and per-soldier-class freshness).

PLUS: extend `scripts/ai-hydra.sh` with new modes:
- `--brief` (default; existing behavior)
- `--full` (all 4 new constructs in unified output)
- `--actions` (just the ranked action queue)
- `--save` (archive to `journal/hydra/`; compute delta vs prior)
- `--diff <prior_brief.md>` (explicit delta)

**Strength:** the swarm and HYDRA become genuinely co-intelligent.
HYDRA reads what soldiers see (high-cadence empirical signal);
soldiers' deposits gain meaning when correlated against
watchers' constitutional knowledge. The action queue closes the
"observation → next move" gap that's been implicit since Arc D
opened. Brief-archive gives HYDRA real memory across runs (the
self-monitoring section finally has source material).

**Weakness:** the surface area is meaningfully larger. 4 new
modules + watcher refreshes + CLI extension = ~1500 lines of new
code. Big enough to warrant care; small enough to ship in one
v9.04 under heavy-production. Constitutional invariants verified:

- C1: PheromoneReader is read-only; no UPDATE/DELETE; trigger holds
- C10: only system-state metrics flow through HYDRA; no holder PII
- G1: deterministic across runs (same Pheromone snapshot → same
  correlation → same action queue)
- G3: read-only; per-watcher graceful-failure preserved
- G6: HYDRA imports the soldier base type only for type-hints;
  doesn't import individual soldiers (those auto-discover)
- F5: action queue may PROPOSE F5 changes (e.g. "Treasury still
  skewed; consider B+D rebalance") but doesn't execute them;
  Sanctum protocol still gates constitutional changes

### Position B: New 10th watcher — promote CM from immortal narrative to a real watcher head

Add `cm_watcher` (constitutional-meta watcher) that observes
HYDRA's own brief history + cross-watcher correlation. This
breaks the Hydra-9 mythology by making the count 10 mortal +
CM-promoted = ambiguous.

**Strength:** has its own watcher slot; cleaner separation of
concerns.

**Weakness:** breaks the canonical Hydra-9 mortal + CM-immortal
metaphor that v8.72 deliberately landed. CM as "immortal because
it never dies / can't be removed" is constitutionally important;
making CM a mortal watcher inverts that.

### Position C: Defer indefinitely — keep current HYDRA

Argue that the current HYDRA is sufficient and the swarm-vs-HYDRA
gap is acceptable.

**Strength:** zero work.

**Weakness:** contradicts VANTA's directive ("completely
revamp/upgrade polaris_hydra"). The directive is explicit.

## III. Architect's recommendation

**Position A (full hybrid-intelligence revamp).** Rationale:

1. **VANTA's framing is the design.** "Centralized intelligence
   (HYDRA) + decentralized intelligence (swarm) = power" is
   exactly what Position A delivers. Position B muddies the
   metaphor; Position C ignores the framing.

2. **The 9-mortal mythology is preserved.** No new heads.
   The 4 new constructs are infrastructure (PheromoneReader,
   CorrelationEngine, ActionQueue, brief-archive), not heads.
   The mortality count stays at 9; CM stays immortal narrative.

3. **Pheromone-reading is the load-bearing piece.** Without it,
   none of the other improvements matter. With it: schema_watcher
   sees what soldier_db_table_size sees; security_watcher sees
   what soldier_log_tail sees; ant_colony_watcher actually
   reports per-soldier-class freshness.

4. **ActionQueue closes the most-asked operator question.**
   "What should I do next?" — HYDRA today answers obliquely.
   ActionQueue answers directly + ranks + cites the constitutional
   constraints touched.

5. **Brief-archive feeds the self-monitoring section.** The
   architect persona's six-section brief has a "Self-monitoring"
   block that today's deterministic synthesizer fills with
   "observations about this brief" — useful but thin. With a
   journal of prior briefs, HYDRA can see its own drift over
   time (which findings recur; which corrections landed; which
   suggestions were taken).

The architect's caution on A: the new modules introduce
import-graph weight on `polaris_hydra` (it now reads from
`Pheromone` table). The watchers must not become dependent on
DB-availability for their core function — `PheromoneReader`
must graceful-fail to "no recent deposits" when DB is offline,
not raise. Documented in the contract.

## IV. Open questions for VANTA

(All resolved per architect-recommended defaults; no additional
operator decision required.)

1. **Brief-archive cadence?** Architect-recommended: `--save`
   only writes when explicitly requested. No auto-save on every
   `--brief` (would clutter `journal/hydra/`).

2. **Delta-detection scope?** Architect-recommended: compare
   findings + correlations + actions; ignore voice text (that's
   stylistic). Delta = sets of `(watcher, finding.title)` pairs.

3. **Action-queue ranking?** Architect-recommended: rank by
   (severity × confidence × constitutional-weight), where
   constitutional-weight is +1 for each C-constraint touched.
   Ties broken by alphabetical watcher name (deterministic).

4. **PheromoneReader window?** Architect-recommended: last 6 hours
   by default (matches commander cron cadence). Override via
   `--pheromone-window-hours N`.

5. **CorrelationEngine triggers?** Architect-recommended: same
   `node_id` is the cleanest signal; same `domain` (e.g. "infra")
   is weaker but useful. Both reported; node_id-correlations
   ranked higher.

## V. Decision

**Position A (full hybrid-intelligence revamp).** VANTA in-chat
2026-05-14: *"completely revamp/upgrade polaris_hydra + the watchers
so they better suit the project... Boil the ocean."* DECIDED-on-
arrival per heavy-production posture.

The five §IV resolutions all per architect-recommended defaults.
9-mortal-head mythology preserved (no new heads; only infrastructure).
After v9.04 ships, run the full system scan (Hydra + swarm) per
VANTA's directive — that's the proof-of-functionality drill.

## VI. Outcome

Shipped as v9.04 on 2026-05-14 (same day as decision). Single ship,
no follow-ups required. Full system scan run as drill verification.

**Artifacts (8):**

1. **`polaris_hydra/pheromone_reader.py`** (~200 lines) — shared
   read-only module pulling recent Pheromone deposits, grouping
   by tier (commander vs soldier) and per-class freshness; graceful-
   fails to empty result when DB offline.

2. **`polaris_hydra/correlation.py`** (~180 lines) —
   `CorrelationEngine` post-gather pass; emits `CorrelatedFinding`s
   when ≥2 watchers touch the same `node_id` or related `domain`;
   ranked by severity-product.

3. **`polaris_hydra/action_queue.py`** (~220 lines) —
   `ActionQueue` synthesizes watcher findings + correlations into a
   ranked list of `Action`s with risk class + effort estimate +
   constitutional-constraint-touched list.

4. **`polaris_hydra/brief_archive.py`** (~180 lines) — writes
   each `--save`d brief to `journal/hydra/<YYYY-MM-DD>-<HHMM>.md`;
   computes delta vs most-recent prior brief on next `--save`.

5. **`polaris_hydra/watchers/ant_colony_watcher.py`** refreshed
   (~50 lines added) — splits report into commander vs soldier
   tiers; per-soldier-class freshness check (alert if any class
   silent for >2h); uses PheromoneReader.

6. **`polaris_hydra/watchers/{security,performance,schema,cognitive}_watcher.py`**
   each enhanced with optional pheromone-context section
   (~10-30 lines each). When PheromoneReader returns relevant
   deposits, the watcher's evidence_summary gains a
   `pheromone_context` key.

7. **`polaris_hydra/host.py`** extended — new `Hydra.speak_full()`
   method that runs gather + correlate + action-queue + (optional)
   archive, emitting a `HybridIntelligenceBrief` (extends
   HydraSynthesis with the 4 new sections).

8. **`scripts/ai-hydra.sh`** extended with `--full`, `--actions`,
   `--save`, `--diff <path>` modes + `--pheromone-window-hours N`.

9. **Tests + structural invariants** — `polaris_web/test_hydra_revamp.py`
   (~250 lines unit tests for the 4 new modules) + 16 new
   structural invariants in `TestHydraRevamp` class.

10. **`polaris_hydra/README.md`** updated to describe the hybrid
    intelligence model + 4 new constructs; `DEVNOTES/hydra-pheromone-
    integration.md` (~140 lines, NEW) documents the watcher-vs-soldier
    intelligence-tier distinction parallel to the v9.03 commander-vs-
    soldier vocabulary doc.

**Constitutional preservation verified:**
- C1: PheromoneReader is read-only (SELECT only); never UPDATE/DELETE
- C10: only system-state metrics flow through HYDRA; no holder PII
  path; pheromone_reader masks any value-bearing fields
- G1/G3/G6: each watcher's `_observe()` stays graceful-failure;
  PheromoneReader returns empty on DB offline (doesn't raise);
  cross-tier import limited to `polaris_swarm.soldiers.base.Soldier`
  type hint (no runtime dependency)
- F5: ActionQueue may propose F5 changes but doesn't execute;
  Sanctum protocol still gates

**Hybrid intelligence pattern named:** the swarm is the
**substrate** (high-cadence empirical observation); HYDRA is the
**lens** (low-cadence structural synthesis). Together: substrate
→ lens → unified brief. This is the BettaFish ForumEngine pattern
(specialized agents → moderator) extended with: the agents
themselves are also reading shared substrate (Pheromone),
producing a richer synthesis than either tier alone could.

**Pattern #20 Constitutional Discipline — eighth Sanctum-DECIDED-then-shipped
cycle this week.** The "boil the ocean" directive compresses each
cycle into a same-day surface-and-ship.

**Full system scan run as drill verification:** see v9.04 CHANGELOG
§ "End-to-end drill" for the complete output. Summary: Hydra ran
all 9 watchers + Pheromone-context-aware enhancements + correlation
+ action queue + brief-archive; surfaced 23 findings, 4
correlations, 5 ranked actions; archived to
`journal/hydra/2026-05-14-<HHMM>.md`.

## VII. Cross-references

- `polaris_hydra/host.py` — extended with speak_full()
- `polaris_hydra/watchers/base.py` — Watcher / WatcherReport / Finding
  contract (UNCHANGED — backwards compat preserved)
- `polaris_hydra/watchers/*.py` — refreshed with pheromone-context
- `polaris_hydra/pheromone_reader.py` (NEW)
- `polaris_hydra/correlation.py` (NEW)
- `polaris_hydra/action_queue.py` (NEW)
- `polaris_hydra/brief_archive.py` (NEW)
- `polaris_hydra/README.md` — refreshed
- `DEVNOTES/hydra-pheromone-integration.md` (NEW)
- `scripts/ai-hydra.sh` — extended CLI
- `journal/hydra/` (NEW directory) — archived briefs
- v9.03 CHANGELOG — hybrid swarm (the substrate this ship layers HYDRA over)
- v8.72 CHANGELOG — Hydra-9 mythology relocation (the mortality count this
  ship preserves at 9)
- v8.65 CHANGELOG — original Hydra-9 mortal-heads completion
- `MISSION.md` — C1, C10 (preserved)
- `meta/architect.md` — Architect persona (HYDRA's synthesis voice)
- External pattern reference: BettaFish `ForumEngine/llm_host.py`
  (specialized agents → moderator → unified synthesis; Polaris-
  native code informed by the pattern)
