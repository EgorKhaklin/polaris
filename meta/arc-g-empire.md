# Arc G — Roman Empire opening

**Status:** **Phase 1 SHIPPED 2026-05-13 (v8.71); Phase 2 + Phase 3
RESERVED-NOT-PLANNED** (per Sanctum
[`sanctum/2026-05-15-open-arcs-debate.md`](../sanctum/2026-05-15-open-arcs-debate.md)
Position C′; truth-update v9.16).

**RESERVED-NOT-PLANNED** is a deliberate v9.16 framing (the
Anti-Architect's contribution to Position C′). It is honest about
the actual state:

- Phase 1 (Imperial legions Praetorian + Engineer) shipped v8.71.
- Phase 2 (Legio Tribune + projection legions) and Phase 3 (Senate
  voting mechanics) were originally framed as "deferred" — but
  "deferred" implies *planned but not yet*. The honest read after
  two days without surfaced need is that they are *reserved-not-planned*:
  the structural slot is available if a future operational need
  manifests it, but Polaris is not actively planning toward it.

**Manifestation protocol** (mirrors the v9.11 twelfth-legion pattern):
operator opens a Sanctum proposing Phase 2 or Phase 3 implementation
when a real operational event makes it necessary. The Sanctum's §I
documents the surfaced need; §II proposes the concrete shape; §V
authorizes; the implementation follows.

Opened 2026-05-13.
**Roadmap prefix:** R15-*
**Authorizing Sanctum:** `sanctum/2026-05-13-arc-g-roman-empire-opening.md`
**Truth-update Sanctum:** [`sanctum/2026-05-15-open-arcs-debate.md`](../sanctum/2026-05-15-open-arcs-debate.md)

This file extracts Arc G's per-item detail from `MISSION.md`. The
extraction is editorial (per `sanctum/2026-05-14-doc-soft-refactor.md`);
no constitutional content is amended. `MISSION.md` retains the
constitutional summary + done-list rollup; this file holds the
historical narrative of how each G-item shipped.

---

## Arc opening

Authorized by
`sanctum/2026-05-13-arc-g-roman-empire-opening.md`. VANTA's
proposal (Empire-pattern expansion: new military legions + civic
deepening + infrastructure layers) was presented in Sanctum-brief
language; the Architect's brief surfaced concerns in §III–§V
(item-by-item analysis; the Empire narrative as cautionary tale;
the pacing reality check). VANTA chose **Option C** — ship Phase 1
in full despite the Architect's recommendation of Option A
(decline today; revisit with operational data).

**The Hydra-9 mythology was amended.** v8.65 affirmed nine
mortal legions; v8.71's Phase 1 adds Legio Praetorian + Legio
Engineer as the first two Imperial legions. The new mythology
distinguishes:

- **Republican legions (9)** — the original Hydra-9: schema,
  cognitive, security, mission, adversary, performance,
  trajectory, substrate, docs.
- **Imperial legions (2+)** — added v8.71+ via Sanctum
  authorization (G24): praetorian, engineer.
- **CM remains the immortal 10th head** — constitutional, not
  implementational; the Hydra-9 bending does not change CM's
  status.

**v8.72 follow-on:** the Hydra-9 mortal-head mythology was then
relocated entirely from Mycelium legions to HYDRA watchers via
`sanctum/2026-05-13-hydra-mythology-relocation-to-watchers.md`.
After v8.72: REPUBLICAN_LEGIONS / IMPERIAL_LEGIONS distinction
remains as ship-time provenance, but the mortal-head mythology
no longer attaches to legions; it attaches to the 9 watchers.

---

## Done-list

G1. ✅ **Phase 1 foundations** *(delivered v8.71)*. Two Imperial
    legions, one new citizen class, Via Appia priority property,
    five new G-guards.

    **Legio Praetorian** (TESTUDO, constitutional guard):
    - `ant_mission_drift` (ALERT-capable) — guards MISSION.md
      anchors + C1-C10 textual presence
    - `ant_principle_invariant` (ALERT-capable) — guards
      implementation of the four cognitive-substrate principles
      (Sanctum, AoR, Risk Classes, CM)

    **Legio Engineer** (CUNEUS, development acceleration above
    the source layer):
    - `ant_build_freshness` (lead) — Docker artifacts, Rust
      target staleness, vendored-asset drift, `__pycache__`
      orphans
    - `ant_release_velocity` (follower) — long-term cadence:
      stagnation (≥14d), sustained burst, median version-bump gap

    **Tribuni Plebis** (new 6th citizen class, usability advocate):
    - `tribuni_plebis_watcher` — command/doc drift, CLAUDE.md
      complexity, Sanctum-protocol entropy. Surfaces friction
      signals for VANTA to act on; never decides itself.

    **Via Appia** (priority property of AntFinding):
    - `AntFinding.priority: bool` field; auto-promoted for
      ALERT-kind or intensity ≥7.0
    - Bloom renderer applies a 1.5× multiplier on priority
      pheromones, compounding with Cursus Honorum multipliers

    **G-guards G21–G25:**
    - G21: Praetorian observes constitutional artifacts only
    - G22: Tribuni Plebis observes usability surface only
      (no identity-layer references; C10 preserved)
    - G23: Via Appia is a PROPERTY of AntFinding, not a parallel
      routing layer
    - G24: New legions require Sanctum authorization
      (every Imperial legion name must appear in a sanctum file)
    - G25: Cohort growth >50% per ship requires explicit Sanctum
      acknowledgment (codifies the 2026-05-13 E10 override pattern)

    Cohort: 29 → **33 ants** (+4); 9 → **11 legions** (+2);
    5 → **6 citizens** (+1). G-guards: G1-G18 + G19-G20 (F4) +
    G21-G25 (G1) = G1-G25.

G2. ⬜ **Phase 2 projection** (deferred). Legio Tribune + Legio
    Gladiator + Cursus Honorum behavioral activation + Lares
    et Penates module guardians + Pomerium dynamic enforcement.
    The Architect explicitly recommended against most of this
    in the §III analysis; if shipped, each item earns its own
    Sanctum.

G3. ⬜ **Phase 3 empire** (deferred). Senate voting mechanics,
    provincial governor pattern, Mos Maiorum v2, Vestal Virgins,
    Decline & Fall graceful degradation protocol.

---

## The Architect's Empire-metaphor caution

**The Architect's Empire-metaphor caution** (§IV of the
opening Sanctum) stands as the prediction-vs-reality reference:
Rome's Empire was cautionary, not aspirational. The Praetorian
Guard's track record was the worst of any Roman institution
(193 CE: auctioned the throne). VANTA's choice to ship Phase 1
is on record; future `ai-architect.sh --reflect` runs will
score this against subsequent events.
