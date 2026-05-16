# meta/denarius.md — the economic dimension of the Civitas

> *Money makes the world go round.* — VANTA, 2026-05-13, opening Arc F

Polaris's cognitive layer has had a Civitas since v8.66. v8.68
adds the economic substrate that makes the Civitas a system: the
**denarius**, swarm currency, accumulated by ants whose pheromones
lead to drift resolution.

This document is the **map** of the economic dimension. Read it
alongside `meta/civitas.md` (the civic structure) and
`MISSION.md` Arc F (the constitutional opening).

---

## The pomerium holds

Before anything else: the **denarius is swarm currency, not
Polaris currency.** Ants accumulate wealth; Individuals do not.
The boundary between cognitive-layer economics and identity-layer
is preserved verbatim. C10 (*identity ≠ money*) is the pomerium —
the sacred Roman boundary inside which the army cannot enter — and
it does not move.

The denarius is denominated in *units of swarm signal-value*,
not in any external currency. It is intentionally non-fungible
with anything outside the swarm.

---

## What rewards what (Phase F1)

The reward function is **drift-resolution rewards**, chosen by
VANTA in the Arc F opening Sanctum:

| Event | Detection | Effect |
|---|---|---|
| **Drift resolved** | A pheromone fingerprint `(deposited_by, node_id)` was present last pass and is absent this pass | **+10 denarii** to the ant |
| **Persistent silence** | A fingerprint has been present for ≥3 consecutive passes (nobody acted) | **−2 denarii** from the ant |
| **Volume** | Ant fired more pheromones | **0 denarii** (neutral — volume is not rewarded) |

The architecture rewards **signal**, not **volume**. An ant
firing 100 pheromones with 0 resolutions earns 0 denarii. An ant
firing 1 pheromone with 1 resolution earns +10. This is
**Goodhart's Law mitigation by design**: making volume a target
would dilute the bloom; the function refuses that incentive
structurally.

## The Quaestor (5th citizen, v8.68)

The Roman Quaestores were financial magistrates overseeing the
treasury — required service before any higher magistracy. In
Polaris:

- **NAME**: `quaestor_treasurer`
- **Class**: maintains the treasury (lifecycle-keeper sibling of
  the Censor; same filesystem-AoR discipline)
- **Slice**: `polaris_swarm/civitas/treasury-roll.json`
- **Cadence**: every colony pass; computes rewards/penalties
  comparing last pass's fingerprints to this pass's pheromones

The Quaestor emits three kinds of citizen findings:

- `denarii_awarded` — summary of rewards this pass
- `denarii_penalty` — summary of persistent-silence penalties
- `treasury_summary` — top-3 denarii holders (when any balances exist)

## The roll (filesystem-AoR, 3rd instance)

`polaris_swarm/civitas/treasury-roll.json` is the ledger. Per
**G15** (append-only-discipline filesystem-AoR):

```jsonc
{
  "_g_guards": "G15 (filesystem-AoR) + G16 (deterministic)",
  "events": [
    { "timestamp": "2026-05-14T...", "ant": "ant_csp_health",
      "amount": 10, "reason": "drift_resolution",
      "node_id": "module:security.py" },
    ...
  ],
  "last_pass_fingerprints": {
    "ant_ship_burst::file:CHANGELOG.md#2026-05-13": 1,
    ...
  },
  "last_pass_taken": "2026-05-14T..."
}
```

The `events` list is the audit trail; balances are **computed**
by summing matching `ant` entries, not stored as state.
`last_pass_fingerprints` carries the pheromone fingerprints from
the previous pass forward so the Quaestor can detect resolutions
on the next pass.

**Filesystem AoR instances (as of v8.68):**

1. `sanctum/` — the Sanctum corpus
2. `polaris_swarm/civitas/census-roll.json` — the census (Censor)
3. `polaris_swarm/civitas/treasury-roll.json` — the treasury (Quaestor)

## Property classes (informational in F1; **structural in F4 / v8.70**)

The Cursus Honorum maps denarii balance to civic property class
in the Roman style:

| Property class | Denarii balance | Multiplier | Roman analog |
|---|---|---|---|
| **Pleb** | 0 – 1,000 | 1.0× | Plebeian census |
| **Eques** | 1,001 – 10,000 | **1.5×** | Equestrian census (400,000 sesterces historically) |
| **Patrician** | 10,001+ | **2.0×** | Senatorial census (1,000,000 sesterces) |

**As of v8.70 (F4 shipped), these are structurally active.** The
bloom renderer (`scripts/ai_swarm_bloom.py`) consults the
treasury for each ant's current balance, classifies via
`property_class(balance)`, and applies the multiplier to
effective intensity before aggregating per node. Patrician-class
ants additionally gain Sanctum-chair eligibility via
`is_sanctum_chair_eligible(roll, ant)` — a predicate wired into
nothing today, but available for future consultation flows.

**Behaviorally inert today** — max positive ant balance is ~80
denarii at v8.70 ship time; every ant is pleb; every multiplier
is 1.0×; no ant qualifies for Sanctum-chair. As denarii
accumulate through real drift-resolution operation, the
multipliers and eligibility predicates engage automatically. No
further code ship is needed for F4 to "go live."

## The G-guard family extended

| Guard | Rule | Source |
|---|---|---|
| G1-G5 | HYDRA watcher contract | v8.44 |
| G6-G9 | Ant + Mycelium contract | v8.62-E2 |
| G10-G11 | Legion contract | v8.64 |
| G12-G14 | Civitas contract | v8.66 |
| **G15** | **`treasury-roll.json` is filesystem-AoR (append-only-discipline; events list is the truth; balances are computed)** | **v8.68 / Arc F / F1** |
| **G16** | **Reward function is deterministic; same input produces same denarii deltas; replay-safe** | **v8.68 / Arc F / F1** |
| G17-G18 | Acceleration read-only + Consciousness swarm-self-state | v8.69 / Arc E / E10 |
| **G19** | **Cursus Honorum multipliers are monotonic non-decreasing in balance (pleb ≤ eques ≤ patrician). Higher denarii NEVER reduces multiplier.** | **v8.70 / Arc F / F4** |
| **G20** | **Sanctum-chair eligibility derives ONLY from denarii balance. Never references Individual / token / holder / any identity-layer state. C10 (pomerium) preserved.** | **v8.70 / Arc F / F4** |
| G21-G25 | Praetorian-constitutional + Tribuni-usability + Via-Appia-property + new-legions-Sanctum + cohort-growth-50% | v8.71 / Arc G / G1 |
| **G26** | **Additions to `STEADY_STATE_ANTS` allowlist require Sanctum authorization. The in-code allowlist must match the F5 Sanctum's §III enumeration exactly.** | **v8.73 / Arc F / F5** |

## Phase plan — **CLOSED 2026-05-13**

Original commitment was multi-day pacing (F1 today, F2 ≥24h,
F3 ≥24h after F2, F4 ≥7 days after F3). VANTA collapsed F2/F3/F4
into a single ship on the same day as F1 via
`sanctum/2026-05-13-arc-f-accelerated-pacing-override.md`. The
Architect surfaced the technical state-dependencies (F4
behaviorally inert until denarii accumulate); VANTA's
Option B was explicit acceptance.

- **F1 (v8.68)** — Treasury foundation. **SHIPPED.**
- **F2 (v8.70)** — Chaos test for silent ants. **SHIPPED.**
- **F3 (v8.70)** — Cohort growth via proposal exercise.
  **SHIPPED** — first ratified proposal: `ant_proposal_stagnation`.
- **F4 (v8.70)** — Cursus Honorum activation (structural).
  **SHIPPED** — multipliers wired, behaviorally inert until
  denarii accumulate.
- **F5 (v8.73)** — Steady-state ants reward exemption.
  **SHIPPED** — empirical fix surfaced by the 100-year
  post-v8.72 simulation. The v8.68 reward function rewarded
  signal-RESOLUTION, but the v8.69+ acceleration cohort emits
  STEADY-STATE observations that never resolve. F5 adds a
  `STEADY_STATE_ANTS` frozenset (9 ants) that's exempted from
  both reward AND penalty in `compute_rewards`. Drift-class
  ants stay on the original reward function; the Cursus
  Honorum now has a chance to engage.

**Arc F reopened at v8.73 with F5 amendment.** Was closed at
4/4 on 2026-05-13; reopened the same day when the 100-year
simulation surfaced a structural flaw in the F1 reward
function. F5 is the empirically-informed correction. Future F#
items will earn their own Sanctums.

## Why "money makes the world go round" was the right move

The 100-year report identified the deepest blind spot in the
swarm: *we cannot tell which ants are valuable.* Heartbeats (R1)
told us which ants RAN. The denarius tells us which ants
MATTERED.

Without the denarius, the Cursus Honorum could only be
participation-trophy (every ant gets promoted by tenure) or
volume-trophy (loudest ants win). With the denarius, promotion
is *earned by resolution* — the architecturally cleanest
proxy for value Polaris has had.

The Roman civitas worked because the property qualification
made hierarchy meaningful. The Mycelium civitas now has the
same affordance.

## Cross-references

- `MISSION.md` Arc F section — done-list F1..F4
- `ROADMAP.md` v14 section — R14-1..R14-4
- Sanctums:
  - v8.66 / E8: `sanctum/2026-05-13-arc-e-civitas-civilian-classes.md` (Civitas opened)
  - 100-year report: `sanctum/2026-05-13-civitas-100-year-architect-report.md`
  - 100-day report: `sanctum/2026-05-13-civitas-100-day-second-architect-report.md`
  - v8.68 / F1: `sanctum/2026-05-13-arc-f-denarius-opening.md`
- `meta/civitas.md` — the civic structure (legions + citizens + the immortal head)
- `polaris_swarm/civitas/treasury.py` — the reward function (G16)
- `polaris_swarm/civitas/quaestor_treasurer.py` — the financial magistrate
- `polaris_swarm/civitas/treasury-roll.json` — the ledger (G15)
