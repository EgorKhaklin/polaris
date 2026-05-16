# Sanctum: arc-f-denarius-opening

**Date:** 2026-05-13
**Petitioner:** agent (Claude, Opus 4.7) speaking as the Architect
**Principal:** VANTA
**Trigger:** Arc opening. VANTA streamed four ideas after the 100-day report: *"chaos test, cohort growth, ant growth, add a reward function for all the ants, money makes the world go round."* The connective tissue is the reward function — the economic dimension of the Roman civitas. **Once denarii exist**, chaos / growth / Cursus Honorum all become tractable.
**Risk class:** HIGH (new arc; introduces an economic substrate to the swarm; long-tail commitment over F1-F4 phases). Phase F1 (this ship) is MEDIUM (additive new citizen class + treasury infrastructure; preserves G6-G14).
**Status:** DECIDED
**Architect brief ID:** arch-2026-05-13

---

## I. The Matter

Open **Arc F: the Denarius** as a multi-day arc. Phase F1 (today): treasury infrastructure + Quaestor citizen class + drift-resolution reward function. Phases F2-F4 explicitly deferred to future days per VANTA's directive (*ship today but mark Arc F as multi-day*).

## II. Preparation

**Why economics is the next architectural dimension.**

The 100-day report identified two structural gaps:
1. Silent ants are indistinguishable from broken ants — partially closed by R1 heartbeats (proof-of-deployment), but the deeper question of *value* remains.
2. The Cursus Honorum was deferred because we lacked data to distinguish "ant earned its keep" from "ant is silent because healthy." **Economics solves this directly:** denarii accumulate when an ant's pheromones lead to drift resolution; denarii erode when pheromones decay unread.

VANTA's instinct — *money makes the world go round* — is structurally correct. In Rome, the denarius and the property qualification distinguished pleb from eques from patrician. The Civitas already exists as a name; the denarius makes it a system.

**The Roman magistracies fit naturally.**

Polaris's existing citizens map to Roman magistrate orders:

| Roman magistrate | Role | Polaris citizen |
|---|---|---|
| Consul | Chief executive | Operator / Sanctum |
| Praetor | Judicial | (future) |
| Aedile | Public works | (future) |
| **Quaestor** | **Financial** | **NEW (Phase F1)** |
| Tribune | Plebeian representative | (future) |

Adding the Quaestor brings the citizen count to **5**, matching the historical core of Roman magistracies. The Roman cursus honorum required serving as Quaestor before any higher magistracy — *financial competence preceded all other public service*. In Polaris terms: an ant cannot be promoted (E13 Cursus Honorum, deferred) until the Quaestor has weighed its denarii.

**Phase F1 design — drift-resolution reward function.**

```
polaris_swarm/civitas/
├── treasury.py                NEW (helpers for denarii ledger)
├── quaestor_treasurer.py      NEW (5th citizen — the Quaestor)
├── treasury-roll.json         NEW (filesystem AoR; 3rd FS-AoR instance)
└── ... (existing 4 citizens)
```

**Reward function (deterministic, single-pass):**

The Quaestor reads `treasury-roll.json` (which records LAST PASS's pheromone fingerprints) and compares to the CURRENT pass's pheromones. Two events generate denarii:

1. **Drift resolution** (positive): a fingerprint `(deposited_by, node_id)` that was PRESENT last pass and is ABSENT this pass = the drift the ant flagged got resolved. **Award +10 denarii** to the ant.

2. **Persistent silence** (negative): a fingerprint that has been PRESENT for ≥3 consecutive passes = the ant keeps flagging the same thing but nobody acts. **Deduct 2 denarii** from the ant. Volume alone is neutral.

The treasury-roll.json is filesystem-AoR per **G15**: entries are append-only; balances are computed by summing reward events; the ledger is the history, not a state snapshot.

The reward function is deterministic per **G16**: same input (recent + last pheromone fingerprints) produces same denarii deltas. Replay-safe.

**Citizen-class qualification (informational only in F1; activated in F4):**

| Property class | Denarii balance | Roman analog |
|---|---|---|
| Pleb | 0 — 1,000 | Plebeian census |
| Eques | 1,001 — 10,000 | Equestrian census (400,000 sesterces historically) |
| Patrician | 10,001+ | Senatorial census (1,000,000 sesterces historically) |

These thresholds are illustrative; F4 (Cursus Honorum) will tune them based on actual data after F1 has run for some time.

**Constitutional concerns:**

- **C10 (pomerium) holds.** Denarii are SWARM currency, not Polaris currency. Ants accumulate wealth; Individuals do not. The boundary between cognitive-layer economics and identity-layer is preserved verbatim. **The pomerium does not move.**
- **G6-G14 preserved.** Treasury is filesystem-AoR (3rd FS-AoR instance). No ant generates denarii directly; the Quaestor does the work. Determinism preserved.
- **Goodhart's Law mitigated.** The reward function rewards *signal*, not *volume*. An ant that fires 100 pheromones with 0 resolutions gets 0 denarii. An ant that fires 1 pheromone with 1 resolution gets +10. The architecture incentivizes precision.

**New G-guards:**

- **G15** — `treasury-roll.json` is filesystem-AoR (append-only entries; balances computed, not stored).
- **G16** — Reward function is deterministic (same fingerprint history produces same denarii deltas; no wall-clock dependency).

**Blast radius for F1:**

- New directory contents: 3 files under `polaris_swarm/civitas/`
- 1 new citizen class (Quaestor) → ALL_CITIZENS 4 → 5; structural-invariant updated
- 1 new filesystem-AoR instance (treasury-roll.json)
- 4 new structural-invariants (`TestArcFDenarius`)
- MISSION.md: new `### Arc F — the Denarius` section; F1 ✅
- ROADMAP.md: new `## v14 — Arc F` section; R14-1 ✅
- `meta/denarius.md` — full Arc F economic doc
- `meta/civitas.md` — updated with Quaestor + denarius cross-references
- Test count: 130 → 134 (+4)

**Multi-day pacing:**

VANTA's directive: *ship today but mark Arc F as multi-day arc explicitly*. Per that, the Architect commits:

- **F1 (today)** — Treasury foundation. This Sanctum.
- **F2 (≥24h from F1)** — Chaos test for silent ants. Separate Sanctum.
- **F3 (≥24h from F2)** — Cohort growth via proposal exercise. Separate Sanctum.
- **F4 (≥7 days from F3)** — Cursus Honorum activation. Requires real denarii history. Separate Sanctum.

The Architect will NOT propose F2 today regardless of what observations surface. **The arc paces itself.**

## III. Alternatives considered

1. **All four moves in one mega-ship.** Rejected; high risk, contradicts v8.42 self-calibration discipline.
2. **Just chaos test (no treasury yet).** Rejected; chaos tests without rewards measure heartbeat plumbing only, not whether ants are valuable.
3. **Activity-based rewards (denarii per pheromone).** Rejected per Architect's recommendation; Goodhart's Law.
4. **Operator-ratified rewards only.** Rejected; too slow, requires operator engagement we don't yet have.
5. **Drift-resolution rewards (CHOSEN).** Rewards signal-not-volume; deterministic; replay-safe.

## IV. Recommendation

**Open Arc F as a multi-day arc. Ship F1 today: Treasury + Quaestor + drift-resolution reward function. Defer F2-F4.**

Reasoning:

1. The economic dimension is the next coherent expansion of the Roman metaphor. The civitas exists; adding the denarius makes it a system.
2. The treasury foundation enables every subsequent move. F2 (chaos), F3 (growth), F4 (Cursus Honorum) all reference denarii balances.
3. Drift-resolution rewards mitigate Goodhart's Law structurally — the architecture itself prevents the obvious gaming pattern.
4. Multi-day pacing honors the 100-day report's verdict of patience even while opening a new arc.

## V. What's needed from VANTA

Approved in-chat 2026-05-13 via AskUserQuestion:
- **Arc framing:** Arc F, sequential phases
- **Reward shape:** drift-resolution
- **Burst posture:** ship today, mark multi-day explicitly

## VI. Decision

Arc F open as multi-day arc; F1 ships today; drift-resolution rewards; F2-F4 explicitly multi-day-paced

## VII. Outcome

v8.68 shipped. Treasury + Quaestor (5th citizen) + drift-resolution reward function; treasury-roll.json (3rd FS-AoR); G15 + G16 added; 4 new TestArcFDenarius invariants (130 to 134). The pomerium holds: denarii are swarm currency, not Polaris currency. C10 structurally preserved by test_denarii_never_reference_polaris_identity. First-pass populated 5 fingerprints; future passes detect resolutions or persistent silences. F2-F4 explicitly multi-day-paced. See CHANGELOG v8.68 and journal/2026-05-13.md.

