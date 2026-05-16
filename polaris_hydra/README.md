# polaris_hydra/ — Arc D · the Swarm + HYDRA

This directory is **Arc D**, opened 2026-05-12 by Sanctum
[`sanctum/2026-05-12-new-chapter-swarm-hydra-arc-opening.md`](../sanctum/2026-05-12-new-chapter-swarm-hydra-arc-opening.md).
**v9.04 (2026-05-14): hybrid-intelligence revamp** —
[`sanctum/2026-05-14-hydra-revamp-pheromone-integration.md`](../sanctum/2026-05-14-hydra-revamp-pheromone-integration.md).
HYDRA + the Mycelium swarm became co-intelligent: the centralized
intelligence (HYDRA's 9 watchers) now reads the decentralized
intelligence's substrate (Pheromone deposits from 33 commanders +
9 soldier classes — 8 workers + 1 priest `soldier_swarm_witness`
added v9.11), correlates findings across watchers, ranks
next-moves into a queue, and archives briefs with cross-run delta
detection. v9.11 adds [`action_promotion.py`](action_promotion.py)
which auto-promotes top-N actions to ROADMAP candidate items
(AP-XXXXXXXX). v9.12 adds [`polaris_foresight/`](../polaris_foresight/)
as a parallel surface with FS-XXXXXXXX candidates. See
"v9.04 hybrid intelligence model" below.

Polaris's cognitive layer pre-Arc-D was a **single-Architect monolith**:
[`scripts/ai-architect.sh`](../scripts/ai-architect.sh) read from N point
tools (`ai-status`, `ai-meta`, `ai-coherence`, `ai-propose`, `ai-adversary`,
…) and emitted one six-section brief. Arc D evolves this into a **swarm**:
N specialist *watchers*, each with its own domain + tool surface, feeding
findings into a unified **HYDRA host** that speaks back to VANTA in a
single Architect-grade voice.

The design is informed by BettaFish's `ForumEngine/llm_host.py` pattern
(N specialist agents → ForumHost moderator → unified synthesis), and by
MiroFish's swarm-simulation pattern (held in reserve for adversarial
rehearsal scenarios in future phases). Neither is vendored.

---

## Architecture

```
                ┌─────────────────────────────────────────┐
                │              VANTA                      │
                │      (the human observer)               │
                └──────────────────▲──────────────────────┘
                                   │
                              one voice
                                   │
                ┌──────────────────┴──────────────────────┐
                │            HYDRA host                   │
                │   polaris_hydra/host.py                 │
                │   (Claude Opus 4.7 synthesis, adaptive  │
                │    thinking; deterministic-fallback if  │
                │    ANTHROPIC_API_KEY unset)             │
                └──┬─────┬─────┬─────┬─────┬─────┬────────┘
                   ▲     ▲     ▲     ▲     ▲     ▲
                   │     │     │     │     │     │
   ┌───────────────┴┐ ┌──┴──┐ ┌┴───┐ ┌┴────┐ ┌─┴───┐ ┌┴──────────┐
   │  Schema       │ │Cog. │ │Sec.│ │Miss.│ │Adv. │ │Perf.      │
   │  Watcher      │ │Watch│ │Watc│ │Watch│ │Watch│ │Watcher    │
   │  H2 (Phase 1) │ │ H3  │ │ H4 │ │ H5  │ │ H6  │ │ H7        │
   └────────┬──────┘ └──┬──┘ └─┬──┘ └──┬──┘ └──┬──┘ └────┬──────┘
            │           │      │       │       │         │
            ▼           ▼      ▼       ▼       ▼         ▼
        Postgres   ai-meta  security  MISSION  ai-     /api/atlas
        triggers   ai-      .py       .md      adversary  /api/health
        + indexes  pattern  /api/     ai-      .sh       EXPLAIN
        + AoR      journal  health    status   per-C     ANALYZE
        tables                       .sh
```

Each watcher is a small Python module with:
- A class extending `Watcher` (`watchers/base.py`)
- A focused domain (the columns of the table above)
- A `report() -> WatcherReport` method returning structured findings
- No LLM calls of its own (watchers are deterministic; HYDRA is the
  LLM layer)

HYDRA's job is to:
1. Invoke each enabled watcher → collect a list of `WatcherReport`
2. Optionally call Claude Opus 4.7 with the reports + a query → emit
   a synthesis
3. If `ANTHROPIC_API_KEY` is unset, emit a deterministic structured
   summary instead (so the swarm works offline + under CI)

---

## Why this structure

**Watcher determinism.** Watchers do not call LLMs. They read disk,
the database, the live app — concrete observable state. Their reports
are reproducible. Tests can pin them. This matches the
audit-of-record discipline at the cognitive layer: the *findings* are
the audit; the *synthesis* is the editorial.

**HYDRA centralization.** Only HYDRA touches the LLM. This keeps the
"intelligence" in one well-tested place, keeps the watchers cheap, and
lets the LLM call be optional (deterministic fallback for offline
work).

**Constitutional fit (v8.30).** The four cognitive-substrate
principles are unchanged. The Architect persona (`meta/architect.md`)
is unchanged; HYDRA's synthesis voice IS the Architect, just informed
by N parallel watchers instead of one synthesis pass. The 27 existing
`ai-*` scripts are unchanged; some of them are read by watchers as
data sources.

**Boundary.** Nothing in `polaris_hydra/` touches `polaris_web/`,
`polaris_sql/`, `polaris_zk/`, or `polaris_cli/`. The Polaris system
itself is what HYDRA *watches*, not what it *is*.

---

## Phase 1 (this ship, v8.37)

- ✅ `polaris_hydra/README.md` — this file
- ✅ `polaris_hydra/__init__.py` — package init
- ✅ `polaris_hydra/watchers/__init__.py` — sub-package init
- ✅ `polaris_hydra/watchers/base.py` — `Watcher` base class +
  `WatcherReport` + `Finding` dataclasses
- ✅ `polaris_hydra/watchers/schema_watcher.py` — first watcher (H2)
- ✅ `polaris_hydra/host.py` — HYDRA aggregator (H1)
- ✅ `scripts/ai-hydra.sh` — invocation wrapper

After Phase 1, an end-to-end smoke works:

```bash
./scripts/ai-hydra.sh                  # runs all enabled watchers,
                                        # emits a synthesis
./scripts/ai-hydra.sh --watcher schema # one watcher only
```

## Phase 2 (v8.38+)

Add watchers one ship at a time:
- H3 CognitiveWatcher (wraps `ai-meta` + `ai-pattern`)
- H4 SecurityWatcher (CSP/CSRF/rate-limiter/role-gates)
- H5 MissionWatcher (done-list + steady-state)
- H6 AdversaryWatcher (10 × `ai-adversary.sh`)
- H7 PerformanceWatcher (atlas + health latencies)

## Phase 3 (one ship after all 6 watchers exist)

H8 — HYDRA constitutional integration. Extend MISSION.md's
cognitive-substrate section to name HYDRA as the operative synthesis
implementation (still substitutable per the v8.30 principle, but
documented as what's actually running).

---

## Invariants (Phase 1)

- **No watcher calls an LLM.** Watchers are deterministic.
- **HYDRA's LLM call is optional.** Offline + CI must work via the
  deterministic fallback.
- **No watcher modifies state.** Watchers only read. The cognitive
  layer's read-only invariant carries through.
- **Watchers fail gracefully.** A failing watcher reports an `alert`
  Finding and lets HYDRA proceed with partial information; it does
  not propagate exceptions up to HYDRA.
- **Reports are JSON-serializable.** This is the data contract
  between watchers and HYDRA. No object soup; no closures.

---

## Naming

**HYDRA** chosen over Jarvis per the Sanctum §IV recommendation:
- Mythological multi-headed creature = the swarm pattern itself
- One body, multiple heads, single voice — the synthesis is *the
  Hydra speaking*, not the heads speaking
- Legible-as-acronym: **H**igh-fidelity **Y**ielding **D**istributed
  **R**eflection **A**gent
- Jarvis connotes butler-servant (one master, one assistant); HYDRA
  connotes distributed cognition resolving to a single output, which
  is what we're actually building

---

## Cross-references

- Sanctum: [`sanctum/2026-05-12-new-chapter-swarm-hydra-arc-opening.md`](../sanctum/2026-05-12-new-chapter-swarm-hydra-arc-opening.md)
- Arc D done-list: [`MISSION.md`](../MISSION.md) §"Arc D — Swarm / HYDRA"
- Roadmap items: [`ROADMAP.md`](../ROADMAP.md) under R12-* prefix
- Prior art (studied, not vendored): BettaFish-main, MiroFish-main
- Architect persona (HYDRA's voice register): [`meta/architect.md`](../meta/architect.md)
- Cognitive substrate principles: [`MISSION.md`](../MISSION.md)
  §"The cognitive substrate (the agent contract)"

---

## v9.04 hybrid intelligence model

VANTA's framing: *"the Hydra is the centralized intelligence with
multiple heads and the swarm is the decentralized intelligence,
together combined and working together they are power."* v9.04
ships the connective tissue.

### The two tiers, named

- **Substrate (decentralized intelligence)** — the Mycelium swarm:
  33 commanders across 11 legions + 6 citizens + 8 v9.03 soldier
  classes. Continuous, high-cadence, empirical observation.
  Deposits Pheromones at ~1000+ per `--hybrid` cycle. Each
  pheromone is `(deposited_by, kind, intensity, node_id, evidence)`.
- **Lens (centralized intelligence)** — HYDRA's 9 mortal watchers
  (schema, cognitive, security, mission, adversary, performance,
  trajectory, ant_colony, civitas) + CM as immortal 10th. Low-cadence,
  structural synthesis. Each watcher is a deterministic monitor of
  one Polaris dimension; HYDRA composes their reports into one
  Architect-voice brief.

### What v9.04 added

Four new constructs (no new heads — the 9-mortal mythology stays):

1. **`pheromone_reader.py`** — shared, read-only window over recent
   Pheromone deposits. Watchers + the Hydra host import this; the
   reader groups deposits by tier (commander vs soldier) and per-class
   freshness. Graceful-fails to `status='db_offline'` if Postgres is
   unreachable; never raises. (C1: SELECT-only; G1: deterministic;
   G3: graceful.)
2. **`correlation.py`** — `CorrelationEngine` runs after
   `Hydra.gather()`. Finds findings across DIFFERENT watchers that
   touch the same `node_id` (strong signal, full weight) or share a
   colon-prefix domain (weaker signal, 0.7× weight, requires ≥3
   distinct watchers). Emits `CorrelatedFinding` ranked by score.
3. **`action_queue.py`** — `ActionQueue` synthesizes watcher findings
   + correlations into a ranked list of `Action`s with imperative
   title, rationale, risk class (LOW autonomous-eligible / MEDIUM
   propose-and-wait / HIGH Sanctum-required), effort estimate
   (one-shot / one-day / multi-ship), and the constitutional
   constraints touched. Score formula:
   `severity × confidence × (1 + 0.5 × constitutional_weight)`.
4. **`brief_archive.py`** — `archive_brief()` writes each `--save`'d
   brief as a Markdown file under
   `journal/hydra/<YYYY-MM-DD>-<HHMM>.md`. `compute_delta()` diffs
   the current brief against the most-recent prior, surfacing new
   findings + closed findings + new actions + closed actions.

PLUS the existing 9 watchers refreshed:

- **`ant_colony_watcher`** — splits report into commander vs soldier
  tiers; per-soldier-class freshness check (drift if any v9.03 soldier
  class silent for >2h); surfaces recent alert pheromones as info.
- **`security_watcher`** — adds channel 7: pheromone-context for
  `soldier_log_tail` (surfaces ERROR-level entries the static
  CSP/CSRF surface can't see).
- **`performance_watcher`** — adds channel 4: pheromone-context for
  `soldier_route_pinger` (continuous latency distribution; channel
  1 takes one-shot timings).
- **`schema_watcher`** — adds channel 6: pheromone-context for
  `soldier_db_table_size` (row-count growth vs static table+trigger
  presence).
- **`cognitive_watcher`** — adds channel 5: pheromone-context for
  `soldier_sanctum_freshness` (stale OPEN sessions vs static index
  parity).

PLUS `Hydra.speak_full()` runs the new pipeline:

```
1. snapshot Pheromone substrate (PheromoneReader)
2. gather watcher reports (each watcher uses PheromoneReader via
   its v9.04 channel)
3. synthesize voice (LLM if key set; else deterministic)
4. correlate cross-watcher findings (CorrelationEngine)
5. rank into ActionQueue
6. (optional) archive to journal/hydra/ + compute delta
```

Returns `HybridIntelligenceBrief` composing `synthesis +
pheromone_snapshot + correlations + actions + archive_path + delta`.

### CLI usage

```bash
ai-hydra.sh --full              # full hybrid: gather+correlate+actions
ai-hydra.sh --actions           # just the ranked action queue
ai-hydra.sh --full --save       # archive + delta vs prior brief
ai-hydra.sh --full --diff <p>   # explicit diff target
ai-hydra.sh --pheromone-window-hours 12  # widen substrate window
```

### Constitutional preservation

- **C1 (audit append-only):** PheromoneReader is `SELECT`-only;
  brief-archive writes new files but never deletes prior ones.
  HYDRA never modifies state.
- **C10 (value-pure):** only system-state metrics flow through HYDRA;
  no holder PII path. The reader projects only metadata columns
  (`deposited_by / deposited_at / kind / intensity / node_id /
  evidence`).
- **G1 (deterministic):** same Pheromone snapshot + same watcher
  reports → same correlations → same action queue → byte-identical
  archive (modulo the timestamp header).
- **G3 (graceful failure):** every channel fails to "no signal"
  rather than raising. PheromoneReader returns
  `status='db_offline'` when DB unreachable. Watchers running
  without psycopg2 still produce reports.
- **G6 (no inter-tier imports):** PheromoneReader reads the
  Pheromone TABLE directly via SQL; it does not import any
  `polaris_swarm.soldiers.*` module. The cross-tier surface stays
  the table itself, not Python imports.
- **F5 (Cursus Honorum):** ActionQueue may PROPOSE F5 changes
  ("Treasury still skewed; consider B+D rebalance") but never
  executes them; Sanctum protocol still gates constitutional
  changes.

### Pattern named

The swarm is the **substrate** (high-cadence empirical observation).
HYDRA is the **lens** (low-cadence structural synthesis). Together:
substrate → lens → unified brief. This extends the BettaFish
ForumEngine pattern (specialized agents → moderator) — in v9.04 the
agents themselves are also reading shared substrate (Pheromone),
producing a richer synthesis than either tier alone could.
