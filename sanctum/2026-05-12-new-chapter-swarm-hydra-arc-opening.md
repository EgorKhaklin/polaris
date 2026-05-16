# Sanctum: new-chapter-swarm-hydra-arc-opening

**Date:** 2026-05-12
**Petitioner:** agent (Claude, Opus 4.7)
**Principal:** VANTA
**Trigger:** **Novel arc** — VANTA's explicit "new chapter" announcement
naming an external research direction (swarm intelligence) backed by
two reference codebases (`MiroFish-main.zip` + `BettaFish-main.zip`).
This is the third Arc-trigger condition named by Sanctum
`2026-05-12-post-v2-steady-state-declaration` §IV: *"Novel arc —
opens when an external cause is documented (a regulatory change, a
credible new threat class, an academic finding that invalidates an
existing assumption)."* The external cause here is **VANTA's research
direction + the BettaFish/MiroFish prior-art exemplars**, both
documented in this turn.
**Risk class:** MEDIUM
**Status:** CLOSED
**Architect brief ID:** arch-2026-05-12-007 (swarm-integration brief,
in-chat 2026-05-12)

---

## I. The Matter

Whether to formally open **Arc D — Swarm / HYDRA**, evolving Polaris's
single-Architect cognitive synthesis into a multi-agent swarm with a
unified HYDRA (Jarvis-equivalent) host speaking to VANTA, modeled on
the BettaFish ForumEngine + N-specialist-agents pattern.

## II. Preparation

### v8.36 closed cleanly

Polaris is publish-ready and final-gate approved. v8.36 was the
terminal pre-publication state. VANTA confirmed v8.36 is backed up;
this Sanctum opens a new arc atop a known-good baseline.

### Discovery (this turn)

Both zip files extracted to `/tmp/polaris-new-chapter/study/`:

**MiroFish** (`/tmp/polaris-new-chapter/study/MiroFish-main/`, 7 MB
zip → frontend + Python `backend/app/`):

- Self-described: *"A Simple and Universal Swarm Intelligence Engine,
  Predicting Anything"*
- Architecture: seed-material input → parallel digital-world
  construction → thousands of agent-personalities interact + evolve
  → prediction output as report + interactive simulation
- Use case: rehearse policy / public-opinion outcomes in a sandbox
  before committing in reality

**BettaFish** (`/tmp/polaris-new-chapter/study/BettaFish-main/`,
134 MB zip → 5 specialist engines + 1 coordinator engine):

| Engine | Role |
|---|---|
| `MediaEngine/` | Multimodal content analysis (video, image, structured cards) |
| `MindSpider/` | Distributed crawler cluster (the data-gathering swarm) |
| `QueryEngine/` | Internet search agent (deep-search nodes pattern) |
| `InsightEngine/` | Private-database mining agent |
| `ReportEngine/` | Multi-round report generation (Flask interface) |
| **`ForumEngine/`** | **The coordinator: `llm_host.py` runs a "ForumHost" (Qwen3-235B for BettaFish; Claude Opus 4.7 for Polaris) that ingests N agent speeches per round, parses them, and emits a unified synthesis. Tracks `previous_summaries` across rounds → has memory. This is the HYDRA-equivalent.** |

Each engine extends a `DeepSearchAgent` base class with its own LLM
client + tool set. Agents post into a shared forum; the host
moderates + synthesizes.

### Mapping to Polaris

The existing Polaris cognitive layer is a **single-Architect
monolith**: `ai-architect.sh` reads from N internal scripts and emits
one brief. That worked for v1+v2 because the synthesis surface was
narrow. The swarm pattern extends it without violating it:

| Polaris today | Polaris-with-HYDRA |
|---|---|
| 27 `ai-*` scripts (point tools) | Still there. Become the swarm's *senses*. |
| `ai-meta.sh` (single aggregator) | Becomes one of the watcher inputs HYDRA reads. |
| `ai-architect.sh` (single voice, six-section brief) | Becomes the **HYDRA synthesis voice** — one head of the new beast. |
| Sanctum protocol | Unchanged. Still gates MEDIUM/HIGH-risk. |
| Audit-of-record | Unchanged. HYDRA's briefs + swarm-agent transcripts join the eight existing instances as new entries. |
| Risk classes | Unchanged. Swarm operates under the same LOW/MEDIUM/HIGH gating. |
| CM | Unchanged. HYDRA itself comes under CM monitoring. |

**Constitutional alignment:** the v8.30 cognitive-substrate section
explicitly named the Architect persona, constraint lattice, 22-pattern
catalog, and constraint-lattice as **substitutable implementation,
not constitutional**. The four principles (Sanctum / audit-of-record /
risk classes / CM) are preserved. This is the kind of evolution v8.30
was written to enable.

### Proposed initial swarm composition (Phase 1)

Six specialist watchers, each a small Python file calling Claude
Opus 4.7 with a focused system prompt + a narrow tool surface:

| Watcher | Domain | Reads | Detects |
|---|---|---|---|
| **SchemaWatcher** | Audit-of-record + schema invariants | `information_schema.triggers`, `pg_indexes`, audit-of-record tables | New audit-of-record candidates; missing triggers; index drift |
| **CognitiveWatcher** | CM + pattern catalog warmth | `ai-meta.sh`, `ai-pattern.sh`, journal entries | Pattern hot/cold rotation; script decay; CM violations |
| **SecurityWatcher** | CSP/CSRF/rate-limiter/role-gating | `security.py`, `/api/health`, CSRF coverage | Policy weakening; missing role gates; rate-limit anomalies |
| **MissionWatcher** | Done-list rollup + steady-state | `MISSION.md`, `ROADMAP.md`, `ai-status.sh` | Done-list drift; steady-state-boundary crossings |
| **AdversaryWatcher** | Game-theoretic walks per C-constraint | `ai-adversary.sh` per constraint | Equilibrium weakening; second-best attacks materializing |
| **PerformanceWatcher** | Atlas latency + query plans | `/api/atlas/*` timings, `EXPLAIN ANALYZE` | Latency regressions; index-miss patterns |

Plus **HYDRA** itself (`scripts/hydra.sh` or `polaris_web/hydra/`):
the ForumHost-equivalent that aggregates the six watchers and speaks
to VANTA in a single Architect-grade voice.

### Naming

VANTA proposed *"Jarvis or maybe HYDRA"*. The Architect recommends
**HYDRA**:
- Mythological multi-headed creature = the swarm pattern itself
  (the Architect's voice + N watcher heads, sharing one body)
- "Jarvis" connotes a butler model (one assistant serving one master);
  HYDRA connotes distributed cognition that resolves to a single
  output, which is what we're actually building
- HYDRA is also legible as an acronym: **H**igh-fidelity **Y**ielding
  **D**istributed **R**eflection **A**gent (or VANTA can name it
  otherwise; this is a brand choice)

### Reference-codebase posture (important)

MiroFish and BettaFish are **prior art for the architecture, not
dependencies for the code**. We study their:
- Engine-as-agent pattern (BettaFish)
- ForumHost-as-aggregator pattern (BettaFish `ForumEngine/llm_host.py`)
- Multi-agent simulation pattern (MiroFish — for if we later want
  to *simulate* adversarial scenarios before they hit production)

We do not vendor them in. Polaris-HYDRA is original code written
against Polaris's existing architecture, informed by the patterns.
Both BettaFish and MiroFish carry their own LICENSEs which would
have to be reconciled if vendored; better to learn-then-write.

### Blast radius if approved

If §VI is "open Arc D":

- **New top-level directory:** `polaris_hydra/` containing watcher
  agents + the HYDRA host
- **Existing cognitive layer:** untouched in Phase 1; HYDRA reads
  from `scripts/ai-*` outputs, doesn't replace them
- **MISSION.md:** new "Arc D — Swarm / HYDRA" section. New done-list
  H1..HN. v2 stays closed; Arc D is the v3 we deliberately left open
- **ROADMAP.md:** new R12-* prefix for HYDRA roadmap items
- **CHANGELOG.md:** v8.37 entry opening the arc; new ship cadence
  follows
- **No constitutional changes.** C1–C10 + CM unchanged. The four
  principles unchanged. Only the *implementation* of synthesis
  evolves
- **Sanctum protocol unchanged.** New ships still follow §I–VII
- **Steady-state declaration of v8.31:** explicitly *honored*. The
  novel-arc trigger condition fired (VANTA + zips); the contract is
  operator-revocable, and VANTA revoked it for this new arc

### Tests planned (Phase 1 acceptance)

- One structural-invariant test asserting MISSION.md gained an
  "Arc D" section
- One test asserting `polaris_hydra/` directory exists with at least
  one watcher + HYDRA host
- One smoke test that HYDRA can be invoked and emits a brief
- The existing 56-test structural suite remains green
- All Polaris functionality (live app, schema, tests) untouched

## III. Alternatives considered

### A. Vendor MiroFish + BettaFish wholesale

Copy the codebases into Polaris, adapt prompts.

- **For:** Fastest to "working." Skip the design phase.
- **Against:** License reconciliation, dependency bloat (Chinese
  social-media APIs Polaris doesn't need, sentence-transformers
  download, full Anspire/Aihubmix integration). Worst: blurs
  ownership boundary — Polaris becomes "BettaFish + Polaris"
  not "Polaris with HYDRA". Violates the v8.30 substitutability
  principle's spirit (the cognitive layer should be ours).

### B. Build HYDRA monolith (no swarm)

Just rewrite `ai-architect.sh` to call Claude with more context.

- **For:** Less new infrastructure.
- **Against:** This is what we have today. VANTA explicitly asked for
  *swarm intelligence*. The whole point is parallel specialized
  monitors feeding a single voice. A monolith Architect is not the
  ask.

### C. Build Polaris-native HYDRA + 6 watcher agents *(recommended)*

Phase 1 builds the skeleton (HYDRA host + at least 2 watchers
working end-to-end), Phase 2 fills out the remaining 4 watchers,
Phase 3 hardens + tests.

- **For:** Honors the request. Preserves Polaris's existing
  constitution. Re-uses the existing `ai-*` scripts as the swarm's
  senses (they're already battle-tested point tools). Studyable from
  BettaFish without vendoring. Reversible: if HYDRA proves
  unnecessary, the old `ai-architect.sh` is still there.
- **Against:** Real implementation work. Cost: probably the same
  order of magnitude as a single v8.x ship per Phase. Risk: the
  swarm could grow beyond useful (Pattern #15 Workaround applied to
  watcher proliferation). Mitigation: hard limit at 6–8 watchers
  by Sanctum decree.

### D. Hold the arc

Defer until Polaris's first publish has been observed in public for
N weeks; let post-publication signals shape Arc D's scope.

- **For:** Empirical Arc D content rather than speculative.
- **Against:** VANTA explicitly opened the chapter *now*, citing the
  zip files as the external trigger. Deferring would be the agent
  second-guessing VANTA's directive.

## IV. Recommendation

**Option C — open Arc D as a Polaris-native HYDRA build.**

Concrete first-ship plan (v8.37, this turn or next, after §VI):

1. **MISSION.md** gains an "Arc D — Swarm / HYDRA" section under
   "What 'done' looks like for Polaris", with done-list H1..H6
   (one per watcher) + H7 (HYDRA host) + H8 (HYDRA constitutional
   integration into the cognitive-substrate section).
2. **ROADMAP.md** gains R12-* entries for each H-item.
3. **`polaris_hydra/`** directory created with:
   - `README.md` (Arc D overview + watcher contract)
   - `host.py` (HYDRA aggregator — Claude Opus 4.7, mirrors BettaFish
     `ForumHost` pattern but Polaris-native)
   - `watchers/schema_watcher.py` (first watcher — proves the
     end-to-end loop)
4. **`scripts/ai-hydra.sh`** wrapper that invokes HYDRA with a query
   and prints the synthesis.
5. **Test** asserting MISSION.md has Arc D section + `polaris_hydra/`
   exists.
6. **CHANGELOG** v8.37 records the arc opening + Phase 1 deliverable.

Subsequent ships (v8.38+) add watchers one at a time, each their
own LOW-risk autonomous ship under Arc D, until all 6 watchers
exist. Then HYDRA gets a Phase 3 hardening Sanctum.

This is structurally identical to how v2 unfolded (M2-1..M2-12, each
shipped individually under the Arc-A+D framing). Different content,
same cadence.

## V. What's needed from VANTA

One of:

1. **"yes proceed"** / **"yes C"** / **"open Arc D"** — approve the
   arc opening; ship v8.37 with the MISSION.md + ROADMAP.md additions
   + the Phase 1 skeleton (HYDRA host + first watcher).
2. **"yes C with edits"** — approve with specific changes:
   - Name (HYDRA / Jarvis / other)
   - Initial watcher composition (different than the 6 proposed)
   - Phase 1 scope (fewer or more deliverables)
3. **"slow down — design first"** — open a *design-only* Sanctum
   like the M2-1 ZK-SNARK exploration, where the agent surveys
   alternatives without shipping until VANTA picks one.
4. **"vendor BettaFish/MiroFish"** — Option A. Agent will note the
   license + dependency implications but execute.
5. **"hold"** — defer.

### Open design questions (if Option C)

- **Q1.** Naming: **HYDRA** (recommended) / Jarvis / your choice?
- **Q2.** Initial watcher set: the proposed 6, or a subset for
  Phase 1?
- **Q3.** Should HYDRA's voice be a *new persona* or evolve the
  existing Architect persona (`meta/architect.md`)? Recommended:
  HYDRA *consumes* the Architect persona as its synthesis voice —
  the Architect doesn't go away, it becomes HYDRA's head-of-state.
- **Q4.** Should this Sanctum's name change to reflect the chosen
  brand? (Current filename: `new-chapter-swarm-hydra-arc-opening`.)

## VI. Decision

Proceed with recommendation

## VII. Outcome

Shipped v8.37 — Arc D Phase 1. Added: MISSION.md 'Arc D — Swarm / HYDRA' section with done-list H1..H8; ROADMAP.md R12-1..R12-8 entries; polaris_hydra/ directory with __init__.py, README.md, host.py (HYDRA aggregator), watchers/__init__.py, watchers/base.py (Watcher base + WatcherReport + Finding dataclasses), watchers/schema_watcher.py (H2 — first watcher; 11/11 AoR tables, 12/12 triggers, 2/2 indexes verified); scripts/ai-hydra.sh wrapper; 8 new TestArcDSwarmHydra structural-invariant tests. End-to-end smoke clean: HYDRA reports 'swarm is healthy. steady-state holds.' Constitutional principles (Sanctum/audit-of-record/risk-classes/CM) all unchanged. Architect persona unchanged — HYDRA consumes it as synthesis voice. Phase 2 (R12-3..R12-7) ships one watcher at a time. Phase 3 (R12-8) extends MISSION cognitive-substrate section with HYDRA-as-current-implementation clause. Sanctum integrity: 15 sessions, no drift.

**See:** [CHANGELOG `## v8.37 (Arc D opening)`](../CHANGELOG.md) · [`journal/2026-05-12.md`](../journal/2026-05-12.md). Cross-ref added v8.61 per Architect-reflection finding.
