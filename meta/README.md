# meta/ — the cognitive layer's architecture

This directory holds the documents that govern how the AI agent
(Claude) thinks about Polaris. It's the constitutional infrastructure
beneath `MISSION.md` / `ROADMAP.md` / `CLAUDE.md` at the repo root.

If `MISSION.md` says **what** Polaris is, `meta/` says **how the
agent reasons about it.**

---

## What's here

### Constitutional architecture

| File | Purpose |
|---|---|
| [`cognitive-loop.md`](cognitive-loop.md) | The session-loop architecture: prime → status → propose → ship → reflect |
| [`cognitive-architecture-v3.md`](cognitive-architecture-v3.md) | The current shape of the cognitive layer (v3; v8.6+) |
| [`autonomy-architecture.md`](autonomy-architecture.md) | LOW / MEDIUM / HIGH risk classes; what the agent can do autonomously |
| [`structural-architecture.md`](structural-architecture.md) | The Removable Test + structural-invariants discipline (v8.8+) |
| [`structural-constants.json`](structural-constants.json) | Canonical structural numbers (constraint counts, pattern counts, etc.) |
| [`constraint-lattice.md`](constraint-lattice.md) | C1-C10 ↔ 10-node lattice mapping |

### Personas + protocols

| File | Purpose |
|---|---|
| [`architect.md`](architect.md) | The Polaris Architect persona spec (HYDRA's synthesis voice) |
| [`sanctum-protocol.md`](sanctum-protocol.md) | Strategic-consultation protocol (the Sanctum) |
| [`sanctum-index.md`](sanctum-index.md) | Chronological index of all 59 Sanctum sessions |
| [`claude-90s.md`](claude-90s.md) | 90-second onboarding primer (v9.06 / J3 — read this first in a new session) |

### Per-arc strategic records

| File | Arc |
|---|---|
| [`arc-b-production.md`](arc-b-production.md) | Arc B: production deployment (Phase 1 ✅; Phase 2/3 ongoing) |
| [`arc-d-hydra.md`](arc-d-hydra.md) | Arc D: HYDRA swarm (closed v8.43; refreshed v9.04 hybrid) |
| [`arc-e-mycelium.md`](arc-e-mycelium.md) | Arc E: Mycelium swarm (substrate; v8.62+) |
| [`arc-f-denarius.md`](arc-f-denarius.md) | Arc F: Denarius (Treasury + Cursus Honorum; F1-F5) |
| [`arc-g-empire.md`](arc-g-empire.md) | Arc G: Empire-pattern expansion |

### Domain models

| File | Purpose |
|---|---|
| [`civitas.md`](civitas.md) | The Civitas (citizen layer) design |
| [`denarius.md`](denarius.md) | The Denarius (Treasury) economic model |
| [`redaction-proof.md`](redaction-proof.md) | M2-12 verification-graph redaction proof + adversary model |
| [`missions-considered.md`](missions-considered.md) | v2 strategic-arc analysis (A/B/C/D considered; D+A chosen) |
| [`lineage.md`](lineage.md) | Etymology of structural insights |

### Brain map (rendered)

| Path | Purpose |
|---|---|
| [`brain-map/`](brain-map/) | Generated visualization of the project's cognitive structure |

### Roadmaps + reviews

| File | When |
|---|---|
| [`polaris-self-roadmap-2026-05-14.md`](polaris-self-roadmap-2026-05-14.md) | The 30-item macro-to-micro scan roadmap (Wave 1 → v9.05; Wave 2 → v9.06; Wave 3 → v9.07; Wave 4 → v9.08) |
| [`treasury-60d-sim-review-2026-05-15.md`](treasury-60d-sim-review-2026-05-15.md) | v9.07 / J4 — review of v8.91 60-day commitment in light of v9.05 cohort shift |

---

## How to navigate

**Fresh agent session?** Start with [`claude-90s.md`](claude-90s.md)
(~30-line operative primer), then [`cognitive-loop.md`](cognitive-loop.md).

**Need to make a strategic decision?** Read
[`sanctum-protocol.md`](sanctum-protocol.md), then `bash
scripts/ai-sanctum.sh open <topic>`.

**Want to see what was decided when?** [`sanctum-index.md`](sanctum-index.md)
chronological + sanctum/ for full session bodies.

**Speak in the Architect's voice?** `bash scripts/ai-architect.sh
--voice` prints [`architect.md`](architect.md).

---

## What this directory is NOT

- Not source code (that's in `polaris_*/`)
- Not operator documentation (that's in `docs/operator/`)
- Not informal developer notes (that's in `DEVNOTES/`)
- Not session logs (that's in `journal/`)

`meta/` is **how the agent thinks**, named explicitly so the
thinking can be audited, version-controlled, and updated when the
constitutional landscape shifts.
