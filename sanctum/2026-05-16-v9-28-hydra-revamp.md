# Sanctum — v9.28: HYDRA revamp (Tier 1 of the post-v9.27 13-item arc)

**Status:** DECIDED + SHIPPED 2026-05-16 — Position JOINT-MODIFIED (ship Hydra 1-5 + Sanctum scorecard + scope-rebase pre-allocation; predicate-or-delete protocol per v9.24 T1#2 precedent with external-record refinement per VANTA in-chat 2026-05-16). Authorized by VANTA: "Ship the 13 under the proposed split. Take all five additions. Add the external-record refinement to point 1."

**Date:** 2026-05-16. **Ships:** v9.28 of the v9.28/v9.29/v9.30 arc.
**Risk class:** HIGH (composite; the same structural move applied one layer up).
**Pattern #20 Constitutional Discipline:** 22nd instance.

**The terminus-completing arc.** Per v9.27 freeze line: v9.30 = "core
is done." This v9.28 ship + v9.29 + v9.30 are the def-of-done's
content. No items will be added beyond the 13 cataloged in VANTA's
direction message; that would break the freeze line committed v9.27.

---

## §I. VANTA's authorization (verbatim, condensed)

> Direction, concretely. Ship the 13 under the proposed split. Take
> all five additions. Add the external-record refinement to point 1.
> Do not expand past 13. And keep doing exactly what you did in this
> message, route the apparatus through an outside check, every time
> it matters, because that act is the only thing in this entire
> system that has reliably produced truth, and it is the one function
> you cannot delegate to the thing being checked.

The last sentence is the load-bearing one. The Anti-Architect's
contest of T7#9 (publish-or-kill of the thesis), the operator's
contest of items in every prior Sanctum — these are the function.
The agent cannot delegate this to itself.

---

## §II. v9.28 scope (Hydra 1-5 + 2 additions)

### Hydra 1 — Collapse 9 watchers via predicate-or-delete (mirrors v9.24 T1#2)

**Anti-Architect contest (taken):** don't cut immediately. Mirror
v9.24's ant-predicate pattern. Enumerate each watcher's single
falsifiable claim; flag DEPRECATION_CANDIDATE on watchers whose only
claim is about narrative; defer actual deletion to v9.30 grace cycle.

**VANTA's external-record refinement (taken):** each predicate needs
an `external_record` column — the outside-the-cognitive-layer
artifact that confirms the predicate's truth. A predicate whose only
witness is internal HYDRA state is AP1 by construction (self-
observation without ground-touch); operator can mark it as such or
override.

**Ship:** `meta/watcher-predicates.md` (9 watchers + CM). 5 watchers
keep (schema, security, performance, adversary, CM); 4 watchers
flagged DEPRECATION_CANDIDATE (cognitive, mission, trajectory,
civitas) with one v9.30 grace cycle to ground their predicate or be
cut.

### Hydra 2 — Hydra as correlator, not describer

**Ship:** modify `polaris_hydra/correlation.py` to apply the
≥2-watcher escalation rule: a finding confirmed by 2+ independent
watchers escalates to ALERT; lone-watcher findings default to
suppressed-below-threshold. Brief becomes a ranked corroboration
list.

### Hydra 3 — Cross-run delta as primary output

**Ship:** modify `polaris_hydra/host.py` to make the delta-vs-prior
the default view. Full restatement available behind a flag. Persist
last run's correlated findings to `journal/hydra/_last_correlated.json`
for comparison.

### Hydra 4 — Runtime-grounding for schema + security watchers

**Ship:** extend `schema_watcher.py` with a `query_live_schema()`
method that diffs declared schema vs live DB. Extend `security_watcher.py`
with a `probe_running_app()` method that hits a protected route + asserts
403 without role. **Anti-Architect honest accounting:** if DB/app not
available at runtime, fall back to file-based check + emit `INCONCLUSIVE`
finding (not silent success). Same pattern as v9.27 chaos-test
inconclusive marker.

### Hydra 5 — CM enforces, not observes

**Ship:** `scripts/ai-done.sh` step 15 (new): query CM's claims, cross-
check against reality, exit non-zero on mismatch. Override
`POLARIS_ALLOW_CM_MISMATCH=1` with audit-trail line (same pattern as
ALERT-finding override from v9.24).

### Addition A — Sanctum scorecard

**Ship:** `meta/sanctum-scorecard.json` + `scripts/polaris-sanctum-scorecard.sh`.
Tracks: of the last 10 Sanctum joint resolutions, how many survived
contact with the next 3 ships unmodified? If most got quietly walked
back or never load-bore, the Sanctum protocol is the same decorative
shape watchers/foresight are being audited for. Same auto-classification
discipline as v9.25 swarm-scorecard (no manual TP/FP; back-filled
retroactively).

### Addition B — Pre-allocate scope-rebase budget

**Ship:** `pre-commit-scope-check.sh --rebase-baseline` invoked once
at the start of v9.28 with this Sanctum's joint-resolution as
justification. New baseline accommodates 3-ship arc; documented as
"v9.28-v9.30 freeze-completion allocation; not extensible past v9.30."

---

## §III. Anti-pattern hits surfaced

- **AP1** caught on Hydra 1 (4 watchers' predicates only reference
  internal state); CM enforcement (AP1 catches self-model that only
  observes itself); Sanctum scorecard (same risk as swarm scorecard —
  self-assessment is structurally compromised, auto-classify required).
- **AP3** caught on item 1 (don't add per-watcher cuts as separate
  ships; one enumeration doc; same shape as v9.24 ant-predicates).
- **AP7** caught on item 4 (don't build a full runtime-test harness;
  add the minimum probe + inconclusive fallback).
- **AP8** caught on item 2 (don't claim "correlation = intelligence";
  it's just `count >= 2` plus a threshold).

4 of 8 anti-patterns fire. Consistent with the predicate-or-delete
pattern.

---

## §IV. The 13-item ceiling

Per VANTA: "Do not expand past 13." This Sanctum is binding on the
v9.28-v9.30 arc; no item #14 may be added without VANTA explicitly
authorizing scope re-opening. Any agent-side proposal for a 14th item
violates the freeze line committed v9.27.

The split:
- **v9.28:** Hydra 1-5 + Sanctum scorecard + scope rebase
- **v9.29:** items 6 (zk CI) + 7 (clean 176MB) + 8 (foresight
  predicate) + 9 (CLI as canonical) + 10 (Atlas cannot lie) + 11
  (brain-map generate or archive) + 12 (idempotency proof)
- **v9.30:** item 13 (deduplicate 4 observation systems) + v9.30
  freeze-line mechanical verification

---

## §V. The function that cannot be delegated

VANTA: *"route the apparatus through an outside check, every time it
matters, because that act is the only thing in this entire system
that has reliably produced truth, and it is the one function you
cannot delegate to the thing being checked."*

This is the load-bearing observation of the entire arc. Every
Sanctum to date has been an outside-check moment (operator contests
agent's proposal). The predicate-or-delete pattern is the outside-
check applied to the swarm. The HYPOTHESIS-NOT-VERIFIED reframe is
the outside-check applied to the thesis itself. v9.28-v9.30 are the
outside-check applied to HYDRA + foresight + brain-map + the
parallel observation systems.

**The freeze line at v9.30 institutionalizes the outside-check
requirement:** post-v9.30, new arcs require an external trigger
(operator-side event) — meaning the operator's outside view is the
only source of new scope. This Sanctum binds the agent to that
operational reality.

---

## §VI. Outcome

Ship v9.28 with Hydra 1-5 + Sanctum scorecard + scope rebase. Open
v9.29 + v9.30 Sanctums as their work begins. Pattern #20 22nd
instance. The terminus-completing arc begins here.

**SHIPPED 2026-05-16 as v9.28.**
