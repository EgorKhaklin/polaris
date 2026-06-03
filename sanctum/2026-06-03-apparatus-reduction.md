# Sanctum: apparatus-reduction

**Date:** 2026-06-03
**Petitioner:** agent (Claude, Opus 4.8)
**Principal:** VANTA
**Trigger:** VANTA questioned whether the cognitive apparatus (ants, legions, soldiers, citizens/civitas, Denarius treasury, Roman/bio theming) is necessary. A function-vs-theme audit confirmed the project's own standing "cut-deeper" signal (`polaris-sanctum-status.sh` ratio 0.29, APPARATUS-DOMINANT). This is the apparatus-reduction Sanctum already named on the roadmap.
**Risk class:** HIGH-composite (touches ship gates, CI, ~130 themed source files, ~250k words of narrative). Executed under the 2026-06-03 heavy-production authorization.
**Status:** OPEN — phased execution.

---

## I. The authorization (verbatim)

VANTA, 2026-06-03, choosing scope: **"dead weight and full de-theme. + harden. Keep the hydra named hydra"**.

So: execute Phases 1+2+3 (cut dead weight, harden, full de-theme) — with one carve-out: **HYDRA keeps its name** (and its "watcher" vocabulary). The de-theme applies to the swarm layer (ants, legions, soldiers, citizens/civitas, Denarius, pheromones, blooms, mycelium), not to HYDRA.

## II. The finding (function-vs-theme audit, 2026-06-03)

A 4-investigator audit found the cognitive apparatus is ~50% real function / ~50% costume + self-narrating prose. The function (a ~18k-LOC invariant-monitor wired into two real ship gates) is worth keeping; the costume earns almost nothing and triples the apparent mass. Standout findings:

- **Denarius/treasury economy** is the clearest larping instance: a reward function, property tiers, Cursus-Honorum multipliers, chair-eligibility, and two "100-year simulations" producing a number that has never exceeded 50 against a 1001 threshold, feeding a multiplier permanently 1.0×, feeding a cosmetic display, feeding nothing. The project's own journal calls it "vestigial" / "empirically broken." `denarii_scheduler.py` (the one attempt to make it load-bearing) is dead AND broken (reads JSON keys that don't exist).
- **5 bit-rotted ants** hardcode `v8.` regex and now silently match nothing (we are on v9.x): ant_release_velocity, ant_ship_burst, ant_changelog_gap, ant_unbumped_version, ant_sanctum_outcome (partial).
- **`escape_rate_trailing_10ships`** is structurally pinned at 0.0 — a metric that cannot move.
- **Two real bugs:** the `ai-done.sh` HYDRA findings-gate reads an 18-day-stale brief with no freshness check (passes vacuously); watcher *detection correctness* is regression-tested nowhere.

The project itself convicts the apparatus: `polaris-sanctum-status.sh` prints "ratio 0.29 — APPARATUS-DOMINANT (cut deeper)"; three scorecards carry built-in cut-deeper triggers. The Anti-Architect persona named AP8 ("Larping") and AP1 ("loving the cognitive layer's growth more than the product's") as the exact failure modes — so removal is the loyal-opposition position, not a betrayal of the design.

## III. Constitutional clearance

- **C1–C10 + the Vocation never move.** They are schema-level triggers / partial-unique-indexes / CHECKs; the apparatus only OBSERVES them. `grep` confirms no core code (`polaris_web/app.py`, `security.py`, `polaris_sql/`) imports `polaris_hydra` / `polaris_swarm` / `polaris_foresight`. The implementation layer is explicitly substitutable per MISSION.md §375-377 (v8.30).
- **Audit-of-record preserved.** Deletions of code/economy are forward-only; shipped CHANGELOG/journal/sanctum history is untouched. The Pheromone table (the 11th AoR) stays.

## IV. Phased plan + load-bearing warnings

**Phase 1 — cut dead weight (near-zero risk, biggest mass reduction).** Delete: `denarii_scheduler.py`, the Denarius economy logic (reward fn, tiers, multipliers, chair-eligibility), the 5 bit-rotted ants, the `escape_rate` metric. Update/remove the tests that PIN economy constants. **WARNING:** keep the census/treasury roll *integrity probe* (HYDRA's ant_colony_watcher + civitas_watcher emit a ship-gate ALERT if a roll is missing/malformed) — shed the economy that writes one of them, not the liveness signal. Rewire/remove watcher inputs BEFORE deleting their data sources.

**Phase 2 — harden (improves the product).** Add the missing watcher detection-regression tests (inject broken CSP / trigger → assert ALERT, run in CI). Fix the vacuous step-14 findings-gate (regenerate a fresh brief before grepping, or drop step 14 and lean on the real CM gate, step 15).

**Phase 3 — full de-theme of the swarm layer (keep HYDRA named).** Rename ants→checks, legions→check-groups, soldiers→probes, pheromones→event-log, blooms→heatmap; drop citizens/civitas/mycelium/Denarius vocabulary; collapse the Roman organizational layer to a flat registry + the two real dispatch tactics. HYDRA and its "watchers" keep their names per VANTA. **WARNING:** the CM gate (`_cm_check.py`) is the one always-running hard gate — looks like "immortal 10th head" flavor but is real; decouple the gate from the myth, keep the gate. 157 CI test methods touch the swarm — preserve the G6/append-only/determinism tests for the substrate being kept.

**Guardrail:** after Phase 1, ratchet the `pre-commit-scope-check` baseline DOWN to lock in the narrative reduction (a large net delete should pass the ratio ceiling easily).

## V. Reviewer of record

Anti-Architect persona (`meta/architect.md`), which pre-named this failure mode. The dissent brief is the loyal-opposition case FOR the cut.

Each phase ships under the standard sequence (new TestWave class, version bump, CHANGELOG, journal, scorecard). Phases recorded here as they close.
