# Sanctum: arc-e-hydra-nine-heads-completion

**Date:** 2026-05-13
**Petitioner:** agent (Claude, Opus 4.7) speaking as the Architect
**Principal:** VANTA
**Trigger:** Mythological correction. VANTA observed: *"the hydra has 9 heads not 7 ,, we need 2 more"*. The canonical Lernaean Hydra (Apollodorus) has nine heads; one is immortal.
**Risk class:** MEDIUM (constitutional count change 7→9; new ants + legions; preserves all four constitutional principles + G6-G11)
**Status:** DECIDED
**Architect brief ID:** arch-2026-05-13

---

## I. The Matter

Promote Mycelium from 7 to 9 Legions to match the canonical Lernaean Hydra. Add **Legio Substrate** (dependency contract) and **Legio Docs** (explain-itself surface). Recognize CM as the **immortal 10th head** — narrative only.

## II. Preparation

Apollodorus's Heracles labor names the Hydra with 9 heads, one immortal. CM maps cleanly onto the immortal head: every other constraint is verified through CM, so removing CM means losing the verification itself. Substitutability applies to every cognitive-layer element except CM.

Coverage gap survey identified two genuine domains the current 7 legions don't see:

- **Substrate** — no ant scans `DEVNOTES/substrate.md`, `Cargo.toml`, or `rust-toolchain.toml` vs reality
- **Docs** — partial only (ant_api_doc_coverage); no holistic scan of `docs/{story,reference,operator}/`, README counts, paper presence, DEVNOTES/ships/ coverage

Both gaps were surfaced by the v8.61 multi-agent audit and the v8.62 Sanctum's "surfaced but parked" list.

**Legio Substrate (Legatus Dependentia) — CUNEUS doctrine:**

| Ant | Role | Slice |
|---|---|---|
| `ant_substrate_catalog` | LEAD (wedge) | `DEVNOTES/substrate.md` |
| `ant_dependency_in_use` | follower | `polaris_web/*.py` imports |
| `ant_rust_toolchain` | follower | `polaris_zk/rust-toolchain.toml` |

**Legio Docs (Legatus Memoria) — TRIPLEX_ACIES doctrine:**

| Ant | Tier | Slice |
|---|---|---|
| `ant_docs_structure` | hastati (T1) | `docs/` filesystem |
| `ant_readme_counts` | principes (T2) | `README.md` claims vs reality |
| `ant_devnotes_ships_coverage` | triarii (T3) | `DEVNOTES/ships/` coverage |

**CM as the immortal 10th head — pure narrative.** One paragraph in MISSION.md's Arc E section maps the mythological structure to the architectural truth v8.9 already established.

## III. Alternatives considered

1. **Substrate + Docs (CHOSEN).** VANTA's pick.
2. Substrate + Health — rejected (runtime-dependent).
3. Docs + Brainmap — rejected (brainmap regenerates automatically).
4. Four new legions (11 total) — rejected (breaks Hydra mythology).
5. Reject — keep 7 — rejected (the mythological alignment is genuinely better than incremental count).

## IV. Recommendation

**Option A — Substrate + Docs + CM-as-immortal-head.** See §II for the design. After this ship, FOUR of nine legions use non-trivial tactics (Adversary CUNEUS, Trajectory TRIPLEX_ACIES, Substrate CUNEUS, Docs TRIPLEX_ACIES). All five tactic dispatchers genuinely exercised on default deployment.

## V. What's needed from VANTA

Approved in-chat 2026-05-13 via AskUserQuestion:
- **Q1:** Substrate + Docs
- **Q2:** Yes — CM the immortal 10th head (narrative only)

## VI. Decision

Substrate + Docs + CM-as-immortal-head — Promote Mycelium 7→9 mortal Legions matching canonical Lernaean Hydra; recognize CM as immortal 10th head (narrative only)

## VII. Outcome

v8.65 shipped. 6 new ants (12→18 total); 2 new legions (Substrate-CUNEUS + Docs-TRIPLEX_ACIES); ALL_LEGIONS=9; count test renamed 7→9; MISSION Arc E E7 ✅ + immortal-head paragraph added. First colony run surfaced 5 drift findings including 2 real ≥1-month drifts (substrate.md missing D3 + anthropic); fixed mid-ship. 122/122 tests; ai-meta healthy; Sanctum integrity 22/22. See CHANGELOG ## v8.65 and journal/2026-05-13.md.

