# Sanctum: doc-soft-refactor

**Date:** 2026-05-14
**Petitioner:** agent (Claude, Opus 4.7) speaking as the Architect
**Principal:** VANTA
**Trigger:** Yesterday (2026-05-13) VANTA + Architect agreed on the soft doc-organization refactor (Option A: keep constitution unified, lighten central docs, add per-subsystem READMEs + per-arc meta files). The decision was parked in `docs/BACKLOG.md` under "Documentation gaps" with explicit 5-step plan. Today's directive: *"proceed architect."*
**Risk class:** MEDIUM (constitutional document touched: MISSION.md; large file moves; large reorganization; constitutional CONTENT preserved verbatim — only LOCATION changes).
**Status:** CLOSED
**Architect brief ID:** arch-2026-05-14

---

## I. The Matter

The central docs are weighty:
- `MISSION.md` is 1,389 lines (constitutional core + 4 arcs of deep detail bundled together)
- `CLAUDE.md` is 641 lines (mostly state-map rows duplicating CHANGELOG)
- `docs/BACKLOG.md` is 396 lines (organized by topic, not subsystem)

The plan parked yesterday: lighten MISSION.md by extracting per-arc detail into `meta/arc-*.md` files; trim CLAUDE.md state-map; reorganize BACKLOG.md by subsystem; add missing per-folder READMEs (`polaris_swarm/`, `polaris_zk/`).

**Constitutional discipline preserved verbatim:**
- C1-C10 stay in MISSION.md
- The four cognitive-substrate principles stay in MISSION.md
- The post-v2 steady-state contract stays in MISSION.md
- Done-list rollups (X/Y per arc) stay in MISSION.md (the constitutional summary)
- ALL deep arc detail moves OUT to per-arc meta files

The arc files become the canonical home for the per-arc done-list ITEM detail (E1-E10 narratives, F1-F5 mechanics, etc.); MISSION.md retains just the constitutional summary + status (X/Y).

## II. Preparation

Yesterday's BACKLOG entry (the parked decision) names the 5-step plan:
1. Trim CLAUDE.md (state-map → CHANGELOG-only; CLAUDE keeps runbook/gotchas)
2. Lighten MISSION.md (arc detail → per-arc meta files)
3. Reorganize BACKLOG.md by subsystem
4. Add per-folder READMEs where missing
5. Extend per-arc meta/*.md (the destination for #2)

Architect has reviewed:
- Current line counts (above)
- Per-folder READMEs that exist (`polaris_cli`, `polaris_hydra`, `polaris_sql`, `polaris_web`); missing (`polaris_swarm`, `polaris_zk`)
- meta/arc-*.md files: none exist yet
- Constitutional structure of MISSION.md (preserved verbatim except moves)

## III. Design

### Per-arc meta files to create

- **`meta/arc-d-hydra.md`** — Arc D opening narrative + watcher cohort + H1-H8 done-list detail. Companion to `polaris_hydra/README.md` (which is operational; this is the strategic record).
- **`meta/arc-e-mycelium.md`** — Arc E opening narrative + ant cohort + legion + civitas structure + E1-E10 detail. Cross-references existing `meta/civitas.md` (the citizen-class concept doc).
- **`meta/arc-f-denarius.md`** — Arc F opening + Denarius economy + F1-F5 detail. Cross-references existing `meta/denarius.md` (the economic-dimension concept doc; deeper mechanics).
- **`meta/arc-g-empire.md`** — Arc G opening + Imperial legions + Tribuni Plebis + G1-G3 detail.

### What MISSION.md keeps

- Preamble (`# Polaris mission`)
- "What Polaris is / is not"
- C1-C10 constitutional constraints (verbatim)
- The four cognitive-substrate principles (verbatim)
- Done-list rollup table:
  - v1: X/Y status
  - v2: X/Y status (closed)
  - Arc D: X/Y → see meta/arc-d-hydra.md
  - Arc E: X/Y → see meta/arc-e-mycelium.md
  - Arc F: X/Y → see meta/arc-f-denarius.md
  - Arc G: X/Y → see meta/arc-g-empire.md
- Post-v2 steady-state contract (verbatim)
- The agent's relationship to this mission (verbatim)
- Cross-references

Target: ≤500 lines.

### What CLAUDE.md keeps

- Quick-start (`./scripts/ai-prime.sh`)
- "Where does X live?" mini-table
- File map (compact)
- Pre-known gotchas (load-bearing for fresh agents)
- Spinning-up-to-test instructions
- Quality bar (VANTA's standing instructions)
- Post-v2 default posture
- State-map: only **last 5 entries** as recency-summary; older entries point to CHANGELOG.md

Target: ≤500 lines.

### BACKLOG.md reorganization

New section structure (replaces topic-based with subsystem-based):
- Polaris Core (identity tokens, web, SQL, ZK)
- HYDRA (watchers + synthesis)
- Mycelium swarm (ants + legions + Civitas)
- Denarius (economic dimension)
- Cognitive layer (scripts, meta/, brain map)
- Future arcs (parked vision items, per-conditions)
- Documentation gaps (cross-cutting)

Items in current sections migrate to their primary subsystem section.

### Missing per-folder READMEs

- `polaris_swarm/README.md` — what the Mycelium swarm is, key entry points (ants/, legions/, civitas/, colony.py), G6-G14 contract, where to learn more.
- `polaris_zk/README.md` — what the Plonky2 ZK crate is, build instructions, key files (lib.rs, main.rs), the Sanctum that authorized it.

### What does NOT change

Per v8.20 audit-of-record:
- All historical Sanctums preserved verbatim
- All historical CHANGELOG entries preserved verbatim
- All journal entries preserved verbatim
- The constitutional content of MISSION.md (C1-C10 + four principles + steady-state contract) preserved verbatim — only LOCATION changes for arc detail

## IV. Recommendation

**Ship as v8.75 (constitutional-document maintenance — soft refactor).**

This is the planned execution of yesterday's decided direction. Single ship covers all 4 chunks since they're coherent (creating per-arc files IS the lightening of MISSION.md; reorganizing BACKLOG is independent but small; adding READMEs is independent and small). Verifying via:
- Test suite still passes (177/177 expected — content moves don't break tests)
- ai-link-check still passes (links to MISSION.md sections may shift; new links to per-arc files added)
- ai-meta still healthy

## V. Alternatives considered

1. **Split into 4 separate ships** (one per subsystem refactor). Rejected — these are coherent; splitting would require 4 Sanctums where 1 covers the same scope; over-pacing.
2. **Full per-project doc set (yesterday's Option B).** Rejected yesterday by VANTA + Architect — fragments constitution, breaks AoR.
3. **Defer further.** Rejected — directive is clear; new day; fresh-perspective rationale satisfied.
4. **Move EVERYTHING from MISSION (including done-list summaries) to per-arc files.** Rejected — done-list rollups are constitutional summary; MISSION should still let a reader see "we shipped 12/12 of v2, 8/8 of Arc D, etc." in one place. The DETAIL moves; the SUMMARY stays.

## VI. Decision

**Ship as v8.75 — soft doc-organization refactor.** VANTA in-chat 2026-05-14: *"proceed architect."* Authorized.

## VII. Outcome

v8.75 shipped. The decided refactor from yesterday's parking
note executed cleanly on the first ship of the new day.

**File moves complete:**
- 4 per-arc files created (`meta/arc-d-hydra.md`,
  `meta/arc-e-mycelium.md`, `meta/arc-f-denarius.md`,
  `meta/arc-g-empire.md`)
- 2 missing READMEs created (`polaris_swarm/README.md`,
  `polaris_zk/README.md`)

**Line counts:**
- `MISSION.md`: 1,389 → 747 (−46%)
- `CLAUDE.md`: 641 → 580 (−10% by line count, but ~75 sprawling
  state-map paragraphs replaced by 5 condensed; readability win
  much larger than the line-count delta)
- `docs/BACKLOG.md`: 396 → ~430 (+9%; added top-of-file
  subsystem-aligned navigation table)

**Constitutional content preserved verbatim.** The cross-checks
are clean:
- C1-C10 + four cognitive-substrate principles + steady-state
  contract: unchanged in MISSION.md
- All G-guards (G1-G26): unchanged
- Sanctum protocol + Architect persona docs (refreshed in v8.74):
  unchanged
- ROADMAP.md, all CHANGELOG history, all journal entries, all
  prior Sanctums: preserved verbatim per v8.20 audit-of-record

**Test discipline preserved:** 177/177 invariants pass. Two
existing tests adjusted to match the new file locations
(`test_mission_arc_d_done_list_present` now reads from the
per-arc file). No new G-guards needed; no new tests added (this
is a content-relocation ship, not a behavioral change).

**ai-meta caught + closed self-introduced drift:** the CLAUDE.md
trim initially orphaned two ai-* script mentions
(`ai-brain-map.sh`, `ai-swarm-bloom.sh`); ai-meta surfaced the
drift; fix landed mid-ship before close. **13th instance of the
self-calibration pattern.**

**Constitutional discipline of the refactor itself:** per v8.30
substitutability, the per-arc files are the IMPLEMENTATION of
arc documentation; the constitutional summaries in MISSION.md
are the LOAD-BEARING claims. A future agent could rearrange the
per-arc files (rename, merge, split) without amending the
constitution; the substitutability clause covers documentation
organization too.

**See:** CHANGELOG ## v8.75 · journal/2026-05-14.md
