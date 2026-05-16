# Sanctum: v8-60-deep-reorganization

**Date:** 2026-05-13
**Petitioner:** agent (Claude, Opus 4.7)
**Principal:** VANTA
**Trigger:** MEDIUM-risk structural — file moves across multiple cognitive-layer and reference surfaces; first post-publication reorganization since the project began.
**Risk class:** MEDIUM
**Status:** DECIDED
**Architect brief ID:** n/a — structural (continuation of v8.59 publication-cleanup arc)

---

## I. The Matter

VANTA: *"do a deep professional reorganization of all the files"* (after v8.59's clutter sweep). Authorized scope via in-chat AskUserQuestion: **Aggressive** (logo + paper + brain-map grouping + SEED_DATA + BACKLOG + docs/ subdivision into story/reference/operator), **Keep current names**.

## II. Preparation

- Architect brief: n/a (continuation of v8.59 cleanup arc; no separate architect snapshot needed)
- Proposal draft: (none — surfaced + decided in-chat per iteration protocol)
- Alignment audit: 4 inputs surveyed before the move plan:
  - Root file inventory (15 files; 5 candidates for relocation)
  - docs/ cross-reference count (12 docs; 100+ inbound references across the codebase)
  - BACKLOG.md reference scan (15 references; ~10 active, ~5 audit-of-record)
  - meta/brain-map artifact scan (4 items currently flat in meta/, candidates for grouping)
- Blast radius (files touched if approved):
  - **Moves:** 1 logo + 2 paper + 4 brain-map artifacts + SEED_DATA.md + BACKLOG.md + 10 docs subdivided = ~20 file moves
  - **Active reference updates:** ~80-100 sites across README/CLAUDE/MISSION/ROADMAP/docs/DEVNOTES/patterns/meta(non-historical)/scripts
  - **Audit-of-record refs (PRESERVED per v8.20):** all sanctum/, proposals/, journal/*.md (except INDEX), prior CHANGELOG entries, meta/cognitive-architecture-v2.md
  - **Generated artifacts:** brain-map.html (regen-able), brain-map-analysis.md (regen-able)
- Tests planned: extend existing structural-invariants to verify new layout; ai-link-check must report 216/216 still resolving after the dust settles.

## III. Alternatives considered

1. **Surgical (rejected)** — only move the logo + the paper + group brain-map. Cleaner aesthetically but misses the bigger story-reference-operator distinction in docs/. VANTA explicitly chose Aggressive.
2. **Moderate (rejected)** — add SEED_DATA.md move but skip BACKLOG.md and docs/ subdivision. Same reason: VANTA wanted the full pass.
3. **Aggressive (CHOSEN)** — full reorg as outlined above.
4. **Defer to a later session (rejected)** — the publication arc is open *now* (v8.35 ship, v8.36 final-gate approval, v8.59 cleanup); a half-organized publication-ready repo is a worse outcome than completing the reorg in this session.

## IV. Recommendation

**Execute Aggressive scope in phases**, with verification after each phase, audit-of-record discipline preserved (no rewrite of historical refs):

- **Phase 1:** group `meta/brain-map.html` + `meta/brain-map-analysis.md` + `meta/brain-map-assets/` → `meta/brain-map/`. Update generator + analyzer + ai-brain-map.sh + 1 structural test that pins the path.
- **Phase 2:** move `polaris_logo_clean.png` → `assets/polaris_logo_clean.png`; move `polaris_project_report.{tex,pdf}` → `docs/paper/polaris_project_report.{tex,pdf}`. Update README + the 5 doc references.
- **Phase 3:** move `SEED_DATA.md` → `docs/SEED_DATA.md`; move `BACKLOG.md` → `docs/BACKLOG.md`. Update CLAUDE.md + MISSION.md + ROADMAP.md + ai-propose.sh + active docs.
- **Phase 4:** subdivide `docs/` into `docs/story/`, `docs/reference/`, `docs/operator/`. Top-level `docs/` keeps README + paper/ + SEED_DATA.md + BACKLOG.md (operator-facing tables). Update inbound refs.
- **Phase 5:** sweep ai-link-check, structural-invariants, HYDRA, ai-meta, ai-done.

**Audit-of-record discipline:** under v8.20, historical refs to old paths are intentionally preserved — they reflect "the path at the time of the entry." This means: do NOT rewrite sanctum/, proposals/, journal/*.md (except INDEX.md which is current/active), prior CHANGELOG entries, or meta/cognitive-architecture-v2.md. ONLY rewrite active-reference files.

## V. What's needed from VANTA

Approved in-chat 2026-05-13 via AskUserQuestion:
- "Aggressive" scope selected
- "Keep current names" — no rename pass, only relocation
- Implicit auth: continue under v8.59 publication-readiness arc

## VI. Decision

Proceed with Aggressive scope — keep current names

## VII. Outcome

v8.60 shipped — 20 file moves + 116 relative-path fixes + 117 cross-ref rewrites; 113/113 tests; 216/216 link-check; 7.4 MB tree.

**See:** [CHANGELOG `## v8.60`](../CHANGELOG.md) · [`journal/2026-05-13.md`](../journal/2026-05-13.md). Cross-ref added v8.61 per Architect-reflection finding.

