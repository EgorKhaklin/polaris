# Sanctum — Tier 5: swarm must earn its weight (numbers, not assertions)

**Status:** DECIDED + SHIPPED 2026-05-16 — Position JOINT-MODIFIED (ship all 3 items with Anti-Architect-imposed honest-baseline constraint on T5#3). Authorized by VANTA in-chat 2026-05-16. Shipped as v9.25.

**Date opened:** 2026-05-16
**Date decided:** 2026-05-16
**Date shipped:** 2026-05-16 (v9.25)
**Lifecycle:** OPEN → DECIDING → DECIDED → SHIPPED
**Risk class:** HIGH (composite — touches measurement, fault-injection, MTTR-tracking; all three are the substrate the v9.24 ship now needs to *prove* works)
**Pattern #20 Constitutional Discipline:** 20th instance
**Authorization:** "After Tier 4 the system functions and is disciplined. This phase proves it works instead of asserting it..." — VANTA, in-chat 2026-05-16

---

## §I. The Critique (VANTA's framing, verbatim)

> Tier 5 — prove the swarm earns its weight, with numbers.
>
> 1. Stand up a swarm scorecard. Every ship logs findings raised,
>    true positives, false positives, and escaped defects (a defect
>    that shipped that no ant caught). First step: swarm-scorecard.json,
>    appended each ship. This single number is the only thing that
>    tells you the swarm is worth maintaining.
> 2. Run a kill test. Inject realistic defects into a branch, drop
>    an auth gate, break an invariant, regress CSP, and measure
>    detection rate and time-to-detect. First step: a fault-injection
>    script with a pass bar, must catch most within one pass. This
>    becomes the swarm's own regression test, run every release.
> 3. Make the closed loop show a measurable delta. Track mean time
>    from defect introduced to defect resolved, before versus after
>    the loop. First step: timestamp finding-raised and finding-resolved
>    in the ledger and chart the trend. If it does not fall, the loop
>    is decorative and you cut deeper.

The unifying claim across all three items: **the swarm's worth is no
longer assertable; only measurable.** The v9.24 ship (cognitive
substrate must bite) gave the swarm consequence. This ship gives the
swarm scoring. If the scoring shows the swarm is not earning, the
v9.25 → v9.26 work is to delete what doesn't earn.

---

## §II. Debate (Architect ↔ Anti-Architect, per item)

### T5#1 — Swarm scorecard

**Architect:** New `meta/swarm-scorecard.json` (append-only). Each
ship invokes `scripts/polaris-swarm-scorecard.sh append` after merging
the v9.X CHANGELOG entry, capturing:
- `findings_raised`: count of distinct (ant, node_id) emissions during
  the ship cycle
- `true_positives`: findings the operator validated against a real defect
- `false_positives`: findings the operator marked as noise
- `escaped_defects`: defects that shipped that no ant caught (the most
  important number)
- `precision` + `recall` derived

**Anti-Architect:** Three contests:

1. **AP3 if `true_positives` / `false_positives` need manual
   classification per ship.** Manual classification dies in 3 ships;
   then the numbers degrade into noise. The honest version: auto-label
   findings as TP if they appear in the same ship's CHANGELOG-fix
   list, FP if not. The operator can override with a single edit, but
   the default is auto-derived.

2. **AP8 if "escaped defects" is self-reported.** The operator
   marking a defect as "escaped" is the operator grading their own
   exam. The honest source: a defect that surfaces in v9.X+1 ship
   notes ("fix bug introduced v9.X") gets retroactively logged as
   escaped from v9.X.

3. **The single number that matters:** not `findings_raised`
   (productivity) but `escaped_defects / total_defects_shipped`
   (negation rate). Zero is impossible; the trend matters. Plot it
   across the last 10 ships, not absolute counts.

**Joint:** Ship `meta/swarm-scorecard.json` + `polaris-swarm-scorecard.sh
append|backfill|report`. Auto-classify TP/FP from CHANGELOG fix-list +
ai-done.sh ALERT findings; operator can override. Escaped-defect
detection is retroactive: when a v9.X+N ship records "fix from v9.X,"
the script back-fills the v9.X escape. Single load-bearing metric:
`escape_rate_trailing_10ships`.

### T5#2 — Kill test (fault injection)

**Architect:** New `polaris_swarm/fault_injection.py` + a set of
realistic defects (drop auth gate, break invariant, regress CSP,
introduce SQL injection, weaken rate limiter). Each defect has a
`setup` + `teardown` + `expected_firing_ants` mirror of the v9.24
fixtures. New `scripts/polaris-swarm-killtest.sh` runs the swarm
against each injected defect, measures detection rate + time-to-detect
(in colony cycles), and reports per-defect status.

**Pass bar:** swarm catches **≥70% within 1 colony pass**, **≥90%
within 3 passes**.

**Anti-Architect:** Concur on shape. Three additional invariants:

1. **AP6 (proceed-without-reading):** the kill test must verify
   defects are *realistic* — not toy scenarios that any grep would
   catch. The defect set must include at least one defect that requires
   cross-table inference (e.g., "auth gate removed but token still
   issued in a specific code path"). Toy defects → toy pass rate →
   meaningless number.

2. **AP8 (larping):** if a defect requires a defect-specific ant
   to be added, the kill test is gaming itself. The defects must be
   detectable by ants that exist *now*, not ants we'd build.

3. **The kill test must be runnable in CI** (≤5 minutes wall time);
   otherwise it becomes the swarm's quarterly test and silently rots.

**Joint:** Ship the kill test with 5 realistic defects (3 production-
shape: auth gate removal, CSP regression, SQL injection in a
parameter; 2 invariant-shape: C3 violation, append-only trigger
bypass). Pass bar 70%/1-pass, 90%/3-passes. Add to CI as a
non-blocking-yet step (will become blocking in v9.26 if pass rate
holds). 5-minute wall budget enforced.

### T5#3 — MTTR trend (the loop's measurable delta)

**Architect:** Timestamp every finding as raised + resolved in
`meta/swarm-mttr.json`. `polaris-swarm-mttr.sh chart` plots the
trend. Pre-v9.24 ("before the loop") MTTR vs post-v9.24 ("after the
loop") should show a downward slope.

**Anti-Architect (sharp):** AP1 (self-observation without ground-touch)
and AP8 (larping) fire hard:

1. **The "before" baseline DOES NOT EXIST.** Pre-v9.24 there was no
   finding-raised timestamp because findings were advisory. We cannot
   compute pre-v9.24 MTTR from any extant data without fabricating it.
   Fabricating it is AP8.

2. **The honest framing:** start measuring from v9.25 forward. The
   "before/after" comparison becomes meaningful at v9.30 (5 ships
   from now), not today. Today's ship records the *start* of
   measurement; the trend emerges over time.

3. **The cut-deeper clause:** if at v9.30, MTTR has NOT fallen, the
   loop IS decorative — and v9.31 deletes the parts of the cognitive
   layer that aren't earning. This needs to be in the constitutional
   record NOW so future-VANTA + future-agent are bound to the rule.

**Joint:** Ship `meta/swarm-mttr.json` + `polaris-swarm-mttr.sh`
recording raised/resolved timestamps from v9.25 forward. NO fabricated
baseline. Add a structural invariant + Sanctum entry binding v9.30:
"if `mttr_trend_slope` is not negative across v9.25..v9.30, open a
deletion Sanctum on the cognitive layer." This is the cut-deeper
clause as a binding contract on future ships.

---

## §III. Position selected — JOINT-MODIFIED

### Items shipped per Architect proposal:

- T5#1 (with Anti-Architect auto-classification + escape-rate metric)
- T5#2 (with Anti-Architect realistic-defects + CI-runnable + no-self-gaming
  invariants)
- T5#3 (with Anti-Architect honest-baseline framing — no fabrication; v9.30
  cut-deeper clause as binding contract)

### Items added by agent: 0
### Items removed: 0

---

## §IV. Anti-Architect anti-pattern hits surfaced

- **AP1** (self-observation without ground-touch) — caught on T5#3's
  fabricated-baseline reflex; structurally refused
- **AP3** (proposal-as-self-elaboration) — caught on T5#1's
  manual-classification path; replaced with auto-derive
- **AP6** (proceed-without-reading) — caught on T5#2's toy-defect risk
- **AP8** (larping) — caught on T5#1's self-reported escapes + T5#2's
  defect-specific-ant risk + T5#3's fake-baseline risk

Four of eight catalogued anti-patterns fire substantively — the same
four that fired in the v9.24 ship. The pattern: measurement-of-self
work attracts the same self-deception failure modes that observation-
of-self does. The Anti-Architect's catalog applies equally to "do we
observe correctly" and "do we score the observation correctly."

---

## §V. Vocation alignment

- T5#1: ANTI-COERCION-INFRASTRUCTURE (a scorecard exposes whether the
  swarm is detecting coercion-shaped patterns; if escape_rate is high
  on coercion-class defects, the coercion-defense vocation isn't
  served by the current swarm composition)
- T5#2: ANTI-COERCION-INFRASTRUCTURE (kill test includes auth-gate-
  removal — directly a coercion vector; if swarm misses it,
  anti-coercion vocation is at risk)
- T5#3: ANTI-COERCION-NEUTRAL — MTTR is operational, not
  vocation-direct. But the v9.30 cut-deeper clause is anti-coercion-
  *structural*: it binds future agent + operator to delete decorative
  primitives, preventing the cognitive layer from becoming a
  coercion-cover (an inert system that LOOKS like it's monitoring but
  is actually just adding ceremony).

3/3 vocation-positive or vocation-structural. 0 negative.

---

## §VI. The v9.30 binding clause

**Recorded here as constitutional record for future ships:**

> If `polaris-swarm-mttr.sh chart` at v9.30 (5 ships from v9.25) does
> not show a negative `mttr_trend_slope`, the agent is bound by
> Sanctum decision to open `sanctum/2026-XX-XX-cognitive-layer-deletion.md`
> proposing deletion of any cognitive-layer primitive whose
> contribution to MTTR-reduction cannot be demonstrated. The cut is
> not optional. The decision-now is that an unmeasurable loop must not
> persist; the cut is the operator's prerogative on *what* to delete;
> the trigger is the slope.

This is the operational version of VANTA's "If it does not fall, the
loop is decorative and you cut deeper."

---

## §VII. Outcome

Ship as v9.25. 3 items. The cognitive substrate now has scoring +
fault-injection + MTTR-tracking. The v9.30 binding clause makes the
"cut if not earning" promise structural, not aspirational.

**The Anti-Architect's role in this ship was sharper than in v9.24:**
caught a fabricated-baseline reflex (T5#3), a self-reported-escapes
reflex (T5#1), and a self-gaming-defects reflex (T5#2). All three
were the Architect's default path; all three got structural refusal.

Authorization: VANTA, in-chat 2026-05-16: "After Tier 4 the system
functions and is disciplined. This phase proves it works instead of
asserting it..."

**SHIPPED 2026-05-16 as v9.25.** 6 new artifacts + TestWave25V925 +
state-map + sanctum-index + journal.
