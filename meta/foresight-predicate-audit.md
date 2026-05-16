# meta/foresight-predicate-audit.md — does foresight predict something checkable?

**Origin:** v9.30 Sanctum item 8 — "Apply the predicate test to
foresight. If it predicts something checkable, score it; if it only
narrates, fold or cut."

---

## Foresight's existing predicate

Per v9.12 Sanctum (`sanctum/2026-05-15-polaris-odyssey-debate.md`),
the foresight surface has ONE falsifiable predicate, baked in
structurally as the SUNSET clause:

> If at 6 distinct calendar months of operation, fewer than 50% of
> promoted FS-XXXXXXXX candidates have been accepted, the foresight
> surface fails the empirical-graduation rule and the sunset clause
> fires.

This is checkable. The acceptance state is tracked in
`polaris_foresight/_acceptance_log.json` (per the v9.12 Anti-Architect
modification). The 6-month threshold + the 50% rate are both observable
external facts.

**Predicate exists. ✓** (per item 8 test: "Write down the one
falsifiable prediction it makes.")

---

## Scoring against history

Reading `_acceptance_log.json` as of v9.30:

```
{
  "briefs":     10 entries (per-brief timestamps)
  "candidates": 2 entries (FS-5B5F30C9 + FS-FBAEC2B8)
  "accepted":   0 of 2
  "open":       2 of 2
  "declined":   0 of 2
}
```

**Distinct calendar months in `briefs`:** 1 (all briefs dated
2026-05-15 — the v9.12 ship + immediate testing window).

**Months elapsed since v9.12 ship:** ~1 day. The 6-distinct-month
threshold is months away.

**Current acceptance rate:** 0/2 = 0%. **Far below the 50%
threshold.** If the surface had been running for 6 distinct months
with this acceptance rate, the SUNSET would fire today.

---

## Per item 8: is foresight worth keeping?

The user's framing: "If the prediction can be wrong and is sometimes
right, add a scoring loop. If it only narrates, fold it into Hydra
or cut it."

**Honest answer at v9.30:** the prediction CAN be wrong (acceptance
< 50%) and we currently have no acceptances. The prediction is
firing toward SUNSET. The mechanism is working — the v9.12 Anti-
Architect's empirical-graduation rule IS doing its job. But the
acceptance count is so small (n=2) that scoring is statistically
meaningless; we need the 6-month window to elapse to have
meaningful data.

**The scoring loop already exists.** It's the empirical-graduation
clause. Running `bash scripts/ai-foresight.sh` emits the brief +
appends to `_acceptance_log.json`. The 6-month / 50% check is the
score. No new scoring infrastructure needed.

**Decision:** KEEP foresight through the empirical-graduation window
(per the v9.12 commit). At ~6 months post-v9.12 (~2026-11-15), the
acceptance rate gets re-scored. If still <50%, the SUNSET fires +
foresight is folded into HYDRA or cut at that point. If ≥50%,
foresight has earned its place.

**This audit + the existing structural mechanism = item 8 satisfied.**
No new code. No new scoring loop. The pre-existing v9.12 design
already passes the predicate test the user is requiring.

---

## Structural invariant pinning this

`test_foresight_has_falsifiable_predicate` (TestWave30V930):
- `polaris_foresight/_acceptance_log.json` exists
- It records `briefs` + `candidates` + per-candidate `status`
- The empirical-graduation predicate (50%-over-6-distinct-months) is
  referenced in `polaris_foresight/promotion.py` or
  `polaris_foresight/foresight_agent.py`

If the predicate ever gets removed, this invariant fires + the
SUNSET-clause's mechanical existence is restored.

---

## What v9.30 ships for item 8

This document. The audit. The honest "wait for the empirical-
graduation window to fire." No new infrastructure.

If at the 6-month window the SUNSET fires, that's a separate
operator-authorized decision: cut foresight, or extend the window
with a recorded amendment per the freeze-amendment-protocol.

---

*Per v9.30 Sanctum item 8, 2026-05-16. Predicate audit complete;
existing v9.12 empirical-graduation mechanism satisfies item 8 by
construction.*
