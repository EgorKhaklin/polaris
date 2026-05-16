# SYSTEM-MAP — the architectural centerpiece

**Polaris's complete structure, named.** Every directory's role, every
package's purpose, every cross-reference made explicit. This is the
single best entry point for understanding the project's shape.

For naming + structural conventions see [`../CONVENTIONS.md`](../CONVENTIONS.md).
For the philosophical principles beneath the structure, see
[`../story/PRINCIPLES.md`](../story/PRINCIPLES.md).

---

## At a glance

```
polaris/                          ← repo root
│
├── README.md                     ← portfolio front-page
├── MISSION.md                    ← constitution (C1-C10 + cognitive substrate)
├── ROADMAP.md                    ← prioritized backlog (R-* items)
├── CHANGELOG.md                  ← audit-of-record (v8.20; ~32 ships)
├── CLAUDE.md                     ← agent runbook
├── LICENSE / NOTICE              ← legal
│
├── Polaris.command               ← double-click launcher (macOS)
├── polaris_mac_launch.sh         ← launcher logic
│
├── polaris_web/        ← Flask app (4K-line app.py + WebAuthn + ZK wrapper)
├── polaris_sql/        ← schema, procedures, triggers, atlas, migrations
├── polaris_hydra/      ← HYDRA centralized intelligence (v9.04 hybrid)
├── polaris_swarm/      ← Mycelium decentralized intelligence
├── polaris_zk/         ← Plonky2 ZK-SNARK Rust crate
├── polaris_cli/        ← CLI utilities
│
├── docs/               ← all documentation (operator + reference + story + paper)
├── meta/               ← cognitive-layer architecture
├── DEVNOTES/           ← informal developer notes
├── patterns/           ← 22-pattern catalog
├── proposals/          ← long-form proposal drafts
├── sanctum/            ← strategic-consultation records (v8.20 AoR)
├── journal/            ← per-day session logs (v8.20 AoR)
├── scripts/            ← cognitive (ai-*) + operator (polaris-*) scripts
├── archives/           ← v9.07 Pheromone archives
├── assets/             ← branding (logo)
│
├── .git/               ← v9.07 (genesis 2026-05-15; first commit deferred to operator)
├── .github/workflows/  ← CI (Postgres-16 service container; full suite)
├── .gitignore          ← venv, caches, secrets, .DS_Store, .hypothesis
└── .pre-commit-config.yaml  ← v9.06 — local hooks (link-check, meta, coherence, invariants)
```

**32 directories** (excl. caches/venv/.git). **Every directory has a
README** as of v9.08.

---

## The four layers

Polaris is built in **four concentric layers**, each with a distinct
role. Understanding the layer-of-the-thing tells you 90% of what you
need.

### Layer 1: Polaris itself (the identity-token system)

The actual product — the thing being built.

| Layer-1 dir | What |
|---|---|
| [`polaris_web/`](../../polaris_web/) | Flask web app — 60+ routes; 33 schema tables; ZK wrapper; WebAuthn |
| [`polaris_sql/`](../../polaris_sql/) | DDL + procedures + triggers + atlas functions + migrations |
| [`polaris_zk/`](../../polaris_zk/) | Rust crate — Plonky2 ZK-SNARK prover/verifier |
| [`polaris_cli/`](../../polaris_cli/) | CLI utilities |

### Layer 2: Cognitive substrate (HYDRA + Mycelium)

The AI agent's working environment. Layer 2 *observes* Layer 1
without modifying it.

| Layer-2 dir | What |
|---|---|
| [`polaris_hydra/`](../../polaris_hydra/) | HYDRA — 9 mortal watchers + CM immortal; v9.04 hybrid intelligence (PheromoneReader + CorrelationEngine + ActionQueue + brief-archive); v9.11 adds action_promotion (FS- via [`polaris_foresight/`](../../polaris_foresight/)) |
| [`polaris_swarm/`](../../polaris_swarm/) | Mycelium — 33 commander ants + 9 soldier classes (8 workers + 1 priest `soldier_swarm_witness` added v9.11) + 6 citizen classes |
| [`polaris_foresight/`](../../polaris_foresight/) | Foresight surface (v9.12; minimum-viable per [`sanctum/2026-05-15-polaris-odyssey-debate.md`](../../sanctum/2026-05-15-polaris-odyssey-debate.md) Position B). Single `ForesightAgent` + 5-section `Brief` + FS-XXXXXXXX promotion. Empirical-graduation rule: 50% acceptance over 6 distinct-month briefs or sunset clause fires. |

### Layer 3: Cognitive layer (the agent's tools)

How the agent thinks: scripts, meta-architecture, audit-of-record.

| Layer-3 dir | What |
|---|---|
| [`scripts/`](../../scripts/) | 32 ai-* (cognitive) + 16 polaris-* (operator) scripts |
| [`meta/`](../../meta/) | Cognitive architecture (cognitive-loop, autonomy, structural, sanctum-protocol, architect persona, per-arc records) |
| [`sanctum/`](../../sanctum/) | 47+ strategic-consultation sessions (v8.20 AoR) |
| [`journal/`](../../journal/) | Per-day session logs + Architect briefs + HYDRA briefs (v8.20 AoR) |
| [`patterns/`](../../patterns/) | 22-pattern software-work catalog |
| [`proposals/`](../../proposals/) | Long-form proposal drafts |

### Layer 4: Documentation (for humans)

What the operator + developer + auditor needs to read.

| Layer-4 dir | What |
|---|---|
| [`docs/operator/`](../operator/) | Runbooks (INSTALL, DEPLOYMENT, OPERATIONS, DR, SOC2, PENTEST, SECRETS, SECURITY, PRIVACY) |
| [`docs/reference/`](../reference/) | Technical reference (API, DATA-MODEL, GLOSSARY, SCALING, **this SYSTEM-MAP**) |
| [`docs/story/`](../story/) | Narrative + principles (STORY, PRINCIPLES) |
| [`docs/paper/`](../paper/) | Academic write-up |
| [`DEVNOTES/`](../../DEVNOTES/) | Informal developer notes (cross-cutting + per-ship in `ships/`) |

---

## The hybrid intelligence pipeline (v9.04+)

The substrate-vs-lens architecture that makes Polaris's cognitive
layer distinct:

```
       SUBSTRATE                              LENS
       (decentralized; v8.62+)                (centralized; v8.37+)

       polaris_swarm/                         polaris_hydra/
       │                                      │
       ├── ants/         (33 commanders)      ├── watchers/   (9 mortal heads)
       ├── soldiers/     (8 classes)          │   ├── schema_watcher
       ├── civitas/      (6 citizens)         │   ├── cognitive_watcher
       ├── legions/      (11 groupings)       │   ├── security_watcher
       └── colony.py     (orchestrator)       │   ├── mission_watcher
            │                                 │   ├── adversary_watcher
            │ deposits                        │   ├── performance_watcher
            ▼                                 │   ├── trajectory_watcher
       Pheromone table  ◄───── reads ──────── │   ├── ant_colony_watcher
       (PostgreSQL; C1 append-only)           │   └── civitas_watcher
       (~50K rows/day; v9.07 archive+purge)   │
                                              ├── pheromone_reader.py  (v9.04 — reads substrate)
                                              ├── correlation.py        (v9.04 — cross-watcher)
                                              ├── action_queue.py       (v9.04 — ranked moves)
                                              ├── brief_archive.py      (v9.04 — journal/hydra/)
                                              └── host.py               (Hydra.speak_full)
                                                  │
                                                  │ writes
                                                  ▼
                                              journal/hydra/<date>-<HHMM>.md
                                              (v8.20 filesystem AoR)
                                                  │
                                                  ▼
                                              cognitive_watcher channel 6
                                              (v9.06 — the lens watching itself)
```

**The flow:** ants + soldiers deposit Pheromones → HYDRA watchers
read both Pheromones AND static state → CorrelationEngine finds
cross-watcher signal → ActionQueue ranks → brief-archive saves →
cognitive_watcher (v9.06) observes the brief-archive's freshness.
The lens watching itself.

---

## The constitutional spine

These documents are the load-bearing constitutional surfaces.
Touching them requires Sanctum protocol (Pattern #20).

```
MISSION.md (constitution)
    ├── C1-C10 hard constraints
    ├── Four cognitive-substrate principles
    ├── G1-G33 G-guards (G27-G29 from v8.77; G30/G31 from v8.87; G32/G33 from v9.07)
    └── Mission v1 + v2 done-lists

meta/architect.md (the agent's voice persona)
meta/sanctum-protocol.md (strategic-consultation protocol)
meta/cognitive-loop.md (session-loop architecture)
meta/autonomy-architecture.md (LOW/MEDIUM/HIGH risk classes)

sanctum/<date>-<topic>.md (47+ DECIDED sessions; v8.20 AoR)
meta/sanctum-index.md (chronological index)

CHANGELOG.md (every ship; v8.20 AoR; ~737 KB; never edited
              retroactively)
journal/<date>.md (per-day narrative; v8.20 AoR)
journal/hydra/<date>-<HHMM>.md (HYDRA briefs; v9.04+)

polaris_swarm/civitas/treasury-roll.json (Denarius ledger; G15)
polaris_swarm/civitas/census-roll.json (Census Roll; G15)
```

---

## Cross-reference quick map

**"Where do I look for X?"** (matches CLAUDE.md's table; replicated
here for self-contained navigation):

| Question | Look here |
|---|---|
| What is Polaris? What is it NOT? | [`MISSION.md`](../../MISSION.md) |
| What's next? Backlog by risk class? | [`ROADMAP.md`](../../ROADMAP.md) / [`docs/BACKLOG.md`](../BACKLOG.md) |
| What just shipped? | [`CHANGELOG.md`](../../CHANGELOG.md) (top entry = latest) |
| 90-second onboarding | [`meta/claude-90s.md`](../../meta/claude-90s.md) |
| Why was a Decision made? | [`sanctum/<date>-<topic>.md`](../../sanctum/) — indexed at [`meta/sanctum-index.md`](../../meta/sanctum-index.md) |
| Cross-cutting principle (AoR, concurrency, substrate, threat-model, style) | [`DEVNOTES/<name>.md`](../../DEVNOTES/) |
| How does ship X work? | [`DEVNOTES/ships/<short-name>.md`](../../DEVNOTES/ships/) |
| Naming + structural conventions | [`docs/CONVENTIONS.md`](../CONVENTIONS.md) |
| Architectural map (this doc) | [`docs/reference/SYSTEM-MAP.md`](SYSTEM-MAP.md) |
| HYDRA brief output (v9.04+) | [`journal/hydra/<date>-<HHMM>.md`](../../journal/hydra/) |
| Day-by-day narrative | [`journal/<date>.md`](../../journal/) (indexed at [`journal/INDEX.md`](../../journal/INDEX.md)) |

---

## Who reads what

| Audience | Primary reading order |
|---|---|
| **Agent (Claude) starting a fresh session** | [`meta/claude-90s.md`](../../meta/claude-90s.md) → `bash scripts/ai-prime.sh` → `bash scripts/ai-status.sh` |
| **Operator deploying Polaris** | [`docs/operator/INSTALL.md`](../operator/INSTALL.md) → [`docs/operator/DEPLOYMENT.md`](../operator/DEPLOYMENT.md) → [`docs/operator/OPERATIONS.md`](../operator/OPERATIONS.md) |
| **Developer contributing** | [`README.md`](../../README.md) → [`docs/CONVENTIONS.md`](../CONVENTIONS.md) → [`DEVNOTES/style.md`](../../DEVNOTES/style.md) → relevant `polaris_*/README.md` |
| **Compliance auditor** | [`docs/operator/SOC2.md`](../operator/SOC2.md) → [`docs/operator/SECURITY.md`](../operator/SECURITY.md) → [`docs/operator/PENTEST.md`](../operator/PENTEST.md) → [`docs/operator/DR.md`](../operator/DR.md) |
| **Academic reviewer** | `docs/paper/polaris_project_report.pdf` → [`docs/story/STORY.md`](../story/STORY.md) → [`docs/story/PRINCIPLES.md`](../story/PRINCIPLES.md) |
| **Future-VANTA orienting after time away** | [`docs/story/STORY.md`](../story/STORY.md) → [`meta/polaris-self-roadmap-2026-05-14.md`](../../meta/polaris-self-roadmap-2026-05-14.md) → `bash scripts/ai-dashboard.sh` |

---

## What this document is NOT

- Not source code (that's in `polaris_*/`)
- Not the constitution (that's `MISSION.md`)
- Not informal notes (those are `DEVNOTES/`)
- Not strategic decisions (those are `sanctum/`)

`SYSTEM-MAP.md` is **the architectural centerpiece** — the single
document that, if read in full, gives a complete sense of how
Polaris's many parts fit together.

Last refreshed: 2026-05-15 (v9.08 — showroom polish).
