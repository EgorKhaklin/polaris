# Sanctum — v9.30: ship the 7 remaining items from the original 13

**Status:** DECIDED + SHIPPED 2026-05-16 — Position EXECUTE-AS-DIRECTED. VANTA: "proceed lets do it." 7 items shipped; 4 v9.28-flagged DEPRECATION_CANDIDATE watchers cut (item 13); 174M of build artifacts deleted (item 7). v9.31 remains the freeze (v9.29 amendment unchanged).

**Date:** 2026-05-16. **Ship:** v9.30. **Risk class:** HIGH (composite).
**Pattern #20:** 24th instance.

**13-item arc — final tally:**
- v9.28 shipped: items 1, 2, 3, 4, 5 (Hydra)
- v9.29 shipped: deleted item 9 on its merits (elaboration); ONE freeze amendment v9.30 → v9.31 with cost
- v9.30 shipped: items 6, 7, 8, 10, 11, 12, 13
- v9.31: mechanical freeze-line verification (no new items)

No item #14 added. Ceiling held at 13. Item 9 deleted on its merits.

---

## §I. The 7 items, each evaluated against subtraction-or-enforcement

### Item 7 — clean 174M of build artifacts (PURE SUBTRACTION)

`polaris_zk/target/` is 174M of cargo build artifacts. `.gitignore`
line 61 already excludes `target/`. The local directory remains as
disk weight. **Delete it.** Source rebuilds via `cargo build` when
needed. CI workflow already runs `cargo test` (line 4 of ci.yml)
which builds from clean.

The cheapest real win the operator named "do it today." Subtracts
174M from the working tree. No code change. No test change.

### Item 12 — schema idempotency PROOF (ENFORCEMENT)

`00_load_all.sql` header already claims "Each file is idempotent
(DROP IF EXISTS before CREATE)." The claim has been a documented
hazard since v6. Per v9.30 #12: replace the documentation with a
TEST. New: `scripts/polaris-idempotency-test.sh` loads schema twice
into a fresh DB + asserts identical state (table count, row count,
trigger count). New: structural invariant `test_idempotency_test_exists`.
The saga of inline comments about reload safety is now superseded
by the test.

### Item 6 — ZK CI prove-verify roundtrip (ENFORCEMENT)

CI runs `cargo test` (line 4 of ci.yml). That exercises crate-
internal tests. Per v9.30 #6: add an EXPLICIT step that builds
release binary + runs one prove-verify roundtrip + one epoch-close
path. The headline cryptographic claim becomes the most-tested
thing, not the least-tested.

### Item 11 — brain-map already generated; pin it (ENFORCEMENT)

`scripts/ai_brain_map.py` generates `meta/brain-map/brain-map.html`
since v9.14/v9.15. The script IS the generator. v9.30 adds a
structural invariant: `brain-map.html` carries a generator-marker
comment confirming it was produced by the script + not hand-edited.
The "hand-maintained 222-node lie" concern is addressed by pinning
the generation, not by archiving.

### Item 10 — Atlas HUD cannot lie (ENFORCEMENT)

Test: query `/api/atlas/summary` (or equivalent), query the DB
directly with the same arithmetic, assert match within tolerance.
The dashboard cannot show wrong numbers if the assertion fires on
mismatch.

### Item 8 — foresight predicate audit (SUBTRACTION-OR-ENFORCEMENT)

Foresight already has a predicate: the 50%-acceptance-over-6-distinct-
months SUNSET rule (v9.12). The audit: score current acceptance
against history. Per `_acceptance_log.json` analysis: zero
FS-XXXXXXXX candidates accepted to date (all PENDING). The
predicate fires CORRECTLY: if no acceptances by 6 distinct months,
sunset. The structural invariant pins the predicate's existence +
the sunset-condition check.

### Item 13 — dedup observers (PURE SUBTRACTION, highest payoff)

Observer overlap audit:

| Artifact watched | Observers | Decision |
|---|---|---|
| Treasury balance | `civitas_watcher` + `ant_treasury_health` | KEEP ant; CUT civitas_watcher |
| MISSION.md drift | `mission_watcher` + `ant_mission_drift` | KEEP ant; CUT mission_watcher |
| cognitive layer health | `cognitive_watcher` | CUT (no operator-load-bearing predicate per v9.28) |
| ship-rate / file-churn | `trajectory_watcher` | CUT (replaced by scope-rule from v9.24 T4) |

All 4 CUT watchers were already flagged DEPRECATION_CANDIDATE in
v9.28's `meta/watcher-predicates.md`. v9.30 executes the cut. New:
`meta/observer-map.md` (the dedup audit). 9 watchers → 5 watchers
(schema, security, performance, adversary, ant_colony + CM).

---

## §II. Anti-pattern hits

- **AP3** caught on item 11 (brain-map): the temptation was to write
  a NEW generator. Refused — generator already exists since v9.14.
  Pin the existing one with an invariant.
- **AP8** caught on item 10 (Atlas HUD): the temptation was to
  document "the HUD should match the DB." Refused — write a test
  that fails if it doesn't.
- **AP7** caught on item 13 (dedup): the temptation was to build a
  meta-observer that watches the other observers. Refused — just
  delete the redundant ones.

3 of 8 fire. The pattern's coverage continues at the v9.30 layer.

---

## §III. Vocation alignment

All 7 items + 4 watcher cuts: ANTI-COERCION-STRUCTURAL or
ANTI-COERCION-NEUTRAL. Less code, less observability theater, less
attack surface. Smaller core. The freeze line approaches.

---

## §IV. The freeze line, unchanged

v9.31 remains the freeze version per the v9.29 amendment. v9.30
ships the 7 remaining items + 4 watcher cuts. v9.31 runs the
mechanical freeze-line verification:

1. All 10 C-numbers enforced at schema level — verified ✓
2. Kill test 5/5 in 1 pass — verified at v9.26 ✓
3. Chaos test 3/3 — verified at v9.27 ✓
4. ≥3 MTTR resolved findings — pending v9.31
5. v9.30 binding clause fired — pending v9.31
6. Observability wired — verified at v9.27 ✓
7. `POLARIS_VERSION` == 9.31 — at v9.31 ship

No new amendments. Ledger holds.

---

## §V. Outcome

Ship v9.30. 7 items + 4 watcher cuts + 174M deletion + new observer-
map. TestWave30V930. Pattern #20 24th instance. v9.31 is the freeze.

**SHIPPED 2026-05-16 as v9.30.**
