# Prior-art analysis: BettaFish + MiroFish

<!-- coherence:taxonomy-allowed — six analysis lenses + decisions + conclusion + cross-refs; structure is content-determined, not over-decomposed -->

**Authored:** 2026-05-12 (post-v8.43, immediately after Arc D close)
**Method:** Swarm-as-lens. The HYDRA six-watcher domain set
(schema, cognitive, security, mission, adversary, performance) was
applied as an analytical framework to two prior-art codebases
named in the v8.37 Sanctum: **BettaFish** (5 specialist engines +
1 coordinator; the immediate ancestor of HYDRA's host pattern) and
**MiroFish** (parallel-world LLM-driven social-media simulation).
**Both studied, never vendored** — per the v8.37 Sanctum §VI.

This document is the formal record of the study, surfacing what
patterns Polaris should **adopt**, what to **reject**, and what to
**invert.** Each pattern carries a citation to the prior-art source
and a Polaris-flavored shape if the verdict is adopt.

---

## Codebase footprints

| | BettaFish | MiroFish |
|---|---|---|
| Source LoC | 37,313 Python | 21,016 Python + 20,917 Vue/JS |
| Entry point | `MindSpider/main.py` + `ReportEngine/flask_interface.py` Blueprint (no app.py at root) | `backend/run.py` (Flask `0.0.0.0:5001`) + `backend/scripts/run_parallel_simulation.py` (subprocess) |
| Engines | 6 (`ForumEngine`, `InsightEngine`, `MediaEngine`, `MindSpider`, `QueryEngine`, `ReportEngine`) | 1 (wraps CAMEL-AI's OASIS social-simulation library) |
| Persistence | Filesystem JSONL + logs + 4-table MySQL crawler scratch DB | Filesystem JSON + 2 OASIS-owned SQLite DBs + Zep Cloud KG (SaaS) |
| LLM providers | 7 separate API keys (one per engine + host + keyword optimizer + crawler) | 2 keys (primary + optional "boost" for dual-provider concurrency) |
| License | Unstated in README; LICENSE 33 KB | AGPL-3.0 |
| Mission framing | "Multi-agent public-opinion analysis... 24/7 AI crawler clusters" | "Next-generation AI prediction engine... rehearse the future in a digital sandbox" |

**Important framing:** both codebases are **engineering-sophisticated
demos** wrapped in production-launch packaging. Neither is
production in the senses Polaris's threat model requires (no auth,
no append-only audit, no role-split, no CSP, no rate limiting,
`DEBUG=True` defaults). The interesting material is **patterns**,
not posture.

---

## Lens 1 — Schema

### BettaFish

- **No agent-state schema.** All inter-engine state lives on the
  filesystem as `.log` files and JSON dumps
  (`InsightEngine/state/state.py:142-258` — dataclass + `to_json()`).
- **`MindSpider/schema/mindspider_tables.sql`** (201 LOC, MySQL,
  `utf8mb4`) is **crawler scratch only** — 4 tables (`daily_news`,
  `daily_topics`, `topic_news_relation`, `crawling_tasks`), all
  `DROP TABLE IF EXISTS` at every reload (lines 11, 41, 65, 88),
  `task_status` mutated in place. No triggers, no event log.
- **`ForumEngine/monitor.py:78-91`** — `clear_forum_log()` calls
  `self.forum_log_file.unlink()` at the start of every new session.
  **The "audit" is mutable and overwriteable.**
- **Zero advisory locks. Zero append-only invariants.**

### MiroFish

- **No relational DB. No ORM.** State is files-on-disk +
  in-process memory + a remote SaaS (Zep Cloud).
- **`backend/uploads/projects/<project_id>/project.json`** is the
  project metadata blob. `shutil.rmtree(project_dir)` deletes
  projects on request (`backend/app/models/project.py:237`) —
  one-click destruction, no soft-delete, no audit.
- **`actions.jsonl`** files (`backend/scripts/action_logger.py`)
  are append-only by convention — single `'a'` open per entry —
  but there is **no immutability invariant, no hash chain, no
  signature**. A developer with shell access trivially rewrites them.
- **`TaskManager`** is an in-memory singleton guarded by
  `threading.Lock` (`backend/app/models/task.py:62-186`). Tasks
  are lost on restart; `cleanup_old_tasks` exists but is never
  wired into a scheduler.

### Polaris contrast

Polaris has **9 schema audit-of-record instances + 1 filesystem
instance + 6 advisory-lock granularities** (canonicalized in
`DEVNOTES/audit-of-record.md`). Every state-changing event writes a
trigger-enforced append-only row. Neither prior-art codebase has
anything in this neighborhood. The closest analog — MiroFish's
`actions.jsonl` — is journaling, not audit-of-record.

---

## Lens 2 — Cognitive (the highest-yield lens)

### BettaFish — the ancestor of HYDRA

The v8.37 Sanctum cited `ForumEngine/llm_host.py` as the coordinator
pattern that informed HYDRA host. The deep read reveals **exactly
where HYDRA self-consciously diverged.**

- **Communication is out-of-band file-tailing, not message-passing.**
  `ForumEngine/monitor.py:584-700` polls `insight.log`, `media.log`,
  `query.log` every 1 second via `file.seek(last_position)` byte-
  position tracking. Specialist engines never call the coordinator;
  the coordinator scrapes the disk.
- The monitor parses output by **looking for hardcoded class names**
  in log lines (`monitor.py:58-67`, e.g. `'FirstSummaryNode'`,
  `'ReflectionSummaryNode'`). It runs a hand-rolled JSON repair
  function (`fix_json_string`, 758-837) that walks characters
  tracking `in_string` and `escape_next` flags — because the
  loguru/JSON contract between writer and reader has no schema.
- **Host synthesis is a single Qwen prompt** bookended by **two
  identical "research-purpose, ethics-approved" disclaimers**
  (`llm_host.py:135, 163, 176, 206`) — content-policy bypass
  theater aimed outward at the model provider's filters.
- **No deterministic fallback.** If `FORUM_HOST_API_KEY` is unset,
  `ForumHost.__init__` raises `ValueError` (lines 43-44). If Qwen
  is unreachable, `generate_host_speech` returns `None` and the
  session continues with no synthesis.
- **Five-speech batching is a magic number** (`monitor.py:51`).

### MiroFish — parallel-world simulation

- **Subprocess-isolated simulation loop.**
  `SimulationRunner.start_simulation()` (`backend/app/services/simulation_runner.py:312-479`)
  spawns `python run_parallel_simulation.py --config <path>` with
  `start_new_session=True` and a daemon thread tails `actions.jsonl`.
- **Three agent layers:** OASIS social agents (LLM-driven personas);
  `ReportAgent` (ReAct loop with 5 tools, min-3/max-5 calls per
  section, hard conflict-handling for `<tool_call>` + `Final Answer:`
  emitted in same response — `report_agent.py:1330-1361`); and
  `OntologyGenerator` (one-shot LLM, mandates exactly 10 entity types
  with 2 fallback types).
- **Circadian time-step propagation.** `run_parallel_simulation.py:1228-1280`
  is the actual sim loop: per-round active-agent sampling weighted by
  `activity_level`, with peak/off-peak multipliers aligned to
  Chinese work/sleep hours. State propagates because OASIS persists
  every action to its SQLite DB; the next round sees the updated
  graph.
- **Intentionally non-deterministic.** `random.sample()` over
  weighted candidates (line 1074), seeds never set,
  `temperature=0.7` (`llm_client.py:38`). Two runs over the same
  config produce different worlds — by design.
- **Filesystem IPC for live interrogation.** After the round loop
  completes, OASIS envs are kept alive
  (`run_parallel_simulation.py:1281`, comment: "保留给Interview使用").
  Flask drops `ipc_commands/<uuid>.json`; the running sim polls,
  executes `env.step({agent: ManualAction(ActionType.INTERVIEW, ...)})`,
  writes `ipc_responses/<uuid>.json`. **You can ask "what does
  Agent #17 think about X?" after the simulation has ended,
  against the still-alive state.** This is the strongest cognitive
  idea in either codebase.
- **Dual-LLM-provider concurrency split**
  (`run_parallel_simulation.py:984-1037`): Twitter agents on the
  primary, Reddit agents on the boost — multiplies effective
  throughput by using two providers.

### Polaris contrast

HYDRA (v8.37–v8.43) made the **right inversion** of BettaFish:
watchers push `WatcherReport`s directly to the host, no log-tailing,
no JSON repair, no inode-swap races. HYDRA also kept the
**LLM-optional-with-deterministic-fallback** contract that BettaFish
never had — `host.py` synthesizes via Opus 4.7 when `ANTHROPIC_API_KEY`
is set, and produces structured deterministic output otherwise.

The strongest *adoptable* cognitive pattern is MiroFish's
**filesystem IPC for live interrogation of a still-running agent**
(see Lens 6 + adopt list).

---

## Lens 3 — Security

### Shared findings (both codebases)

- **No authentication. No CSRF. No rate limiting.**
  BettaFish: 14 routes in `flask_interface.py`, zero `@login_required`.
  MiroFish: 59 routes across three blueprints, `CORS(... origins='*')`
  (`backend/app/__init__.py:43`), `SECRET_KEY = "mirofish-secret-key"`
  default (`config.py:24`).
- **No CSP, no security headers.** Both render LLM-generated content
  into HTML. BettaFish uses `ast.literal_eval` on model output
  (`html_renderer.py:874, 3083`) — DoS surface and parser-quirk
  risk. MiroFish hasn't been audited for `v-html` in
  `Step4Report.vue` (5,162 lines, unaudited).
- **`DEBUG=True` defaults** (MiroFish `config.py:25`) — Werkzeug
  debugger + traceback in HTTP responses
  (`graph.py:251-255` and ~23 other callsites return
  `traceback.format_exc()` in the JSON 500 body).
- **API keys in plaintext .env.** BettaFish: 7 distinct provider
  keys. MiroFish: 5 keys (LLM, LLM-boost, Zep).
- **Disclaimer-in-prompt as security.** BettaFish `llm_host.py`
  brackets every host call with `"已通过伦理性合规审查"` (lines
  135, 163, 176, 206) — a request to the provider, not a defense.

### Polaris contrast

Polaris's `SecurityWatcher` (v8.39) enforces CSP `script-src 'self'`,
CSRF dual-transport (form + `X-CSRFToken` header per v8.22), Redis
rate limiter, role-gating at 47 `@security.login_required` + 25
`@security.require_role` decorators. R6 anti-revealing scan ensures
operator templates never disclose duress codes. Both prior-art
codebases would **fail every channel** of SecurityWatcher.

Polaris is exactly the kind of system whose threat model these
codebases ignore. **Adopting their security posture would regress
v4 + v8.22 + v8.39 work.**

---

## Lens 4 — Mission

### BettaFish

- **Claims** (`README-EN.md:34-67`): "comprehensive crawling, composite
  analysis beyond LLM, multimodal, Agent Forum collaboration,
  public+private data fusion, lightweight extensible framework."
  "30+ social platforms and millions of public comments." "AI crawler
  clusters operate 24/7 non-stop."
- **Actual code**: a 5-engine chain that scrapes Chinese platforms via
  a Playwright-driven submodule, runs three independent
  `FirstSearchNode → ReflectionNode → SummaryNode` pipelines, and
  tails their logs to synthesize a Qwen "host speech" every 5
  speeches. "Agent Forum collaboration" is described as bidirectional
  chain-of-thought debate; the code is **one-directional, out-of-band
  log-scraping with synthesis bolted on every 5 entries.** No
  message bus, no schema, no debate loop.
- The "Composite Analysis Engine Beyond LLM" claim reduces to one
  sentence-transformer doing KMeans clustering
  (`InsightEngine/agent.py:99`) and one multilingual sentiment model.
- **Drift assessment:** substantial, but not dishonest — the engineering
  is real, the marketing exceeds the architecture.

### MiroFish

- **Claims** (`README.md:27-42`): "next-generation AI prediction engine
  powered by multi-agent technology... extracting seed information
  from the real world... automatically constructs a high-fidelity
  parallel digital world... rehearse the future in a digital sandbox,
  and win decisions after countless simulations."
- **Actual code**: a thin orchestration shell that asks an LLM to (1)
  invent a Zep ontology from uploaded text, (2) ingest text into Zep,
  (3) invent OASIS agent profiles from the graph, (4) invent a sim
  config, (5) run OASIS for 72 simulated hours, (6) ask an LLM to
  write a 2–5 section report describing what the LLM made up as
  "a prediction of the future."
- **Drift assessment:** the "future" is whatever the LLM made up this
  time. There is no calibration loop, no ensemble averaging across
  runs, no statistical reporting, no comparison to ground truth.
  The CAMEL-AI OASIS library does the hard work; MiroFish is the
  orchestration shell.

### Polaris contrast

`MissionWatcher` (v8.40) enforces done-list rollup arithmetic, the
steady-state marker, section anchors, and stale-⬜ detection across
v1 + v2 + Arc D. Polaris's mission framing (every claim is
auditable, every primitive has an invariant, every adversary walk
has a defender response) is structurally allergic to both codebases'
"the LLM said it, ship it" disposition.

---

## Lens 5 — Adversary

### BettaFish — five concrete attack walks (from the deep read)

1. **LLM-provider compromise of the forum host.** `FORUM_HOST_API_KEY`
   is a single shared secret. Compromise the upstream → silently
   rewrite the synthesis output. No signature, no second-source check,
   no consistency invariant. **Polaris analog:** every claim in a
   Polaris ZK epoch is cryptographically committed; the equivalent
   attack would require breaking Plonky2.
2. **Forum-log poisoning** (insider or filesystem-write). Append a
   line matching `monitor.py:111`'s `\[(\w+)\]` regex to
   `logs/insight.log` → the host receives the forged speech
   indistinguishably from real engine output. No HMAC, no per-engine
   signing key. **Polaris analog:** the C1 append-only trigger
   physically rejects UPDATE/DELETE on `TokenLifecycleEvent` and
   `VerificationEvent`.
3. **Crawler subprocess argv injection.** `MindSpider/main.py:152-355`
   spawns crawlers with `platform` derived from `daily_topics.keywords`
   (LLM-extracted from news). User-controlled JSON
   (`mindspider_tables.sql:88`) reaches Playwright's URL construction.
4. **ReportEngine eval on model output.** `html_renderer.py:874, 3083`
   call `ast.literal_eval(candidate)` on text the model produced.
   Recursive-explosion DoS + downstream eval pivot.
5. **TOCTOU on file-tailing.** Between size-read (`monitor.py:397`)
   and seek (`:409`), the file can be truncated, replaced, or
   rotated. The code partially handles `current_size < last_position`
   but **does not detect inode change.** A logrotate that swaps the
   inode mid-read produces silently-dropped content.

### MiroFish — three concrete attack walks

1. **Compromised LLM provider / MITM on `LLM_BASE_URL`.** The LLM
   dictates the ontology (what agents *exist*), the personas (what
   they *think*), the config (when they *act*), and the final report
   (the user's *takeaway*). An attacker controlling the upstream can
   silently steer outputs toward a desired conclusion; exfiltrate seed
   material by encoding it into prompt traffic; or inject `<tool_call>`
   blocks that the ReAct parser will execute
   (`report_agent.py:1078-1098`). No mitigation exists.
2. **Hostile seed upload.** PDF/MD/TXT up to 50 MB is fed to PyMuPDF
   in-process, then to the LLM as system context. Prompt-injection
   in seed text propagates through ontology, persona, and report
   stages. PyMuPDF CVE pivot is real (parser runs in-process, no
   sandbox). Storage-DoS via no per-IP throttling.
3. **Deployment compromise.** `SECRET_KEY = "mirofish-secret-key"`
   default + no auth + traceback in 500 responses + `.env` reads on
   any file-read primitive. Any attacker with code-execution reads
   the live LLM and Zep keys, modifies `actions.jsonl` without
   detection (no hash chain), or injects a malicious
   `simulation_config.json` that gets exec'd next run (no signature
   on the spawn; `simulation_runner.py:419` reads `--config` from
   disk without integrity check).

### Polaris contrast

`AdversaryWatcher` (v8.41) runs `ai-adversary.sh` per C1–C10 and
parses the canonical six-section equilibrium structure (claim →
attacker response → equilibrium → second-best attack → defender's
cost → mechanism-design note). Every Polaris constraint has a
documented adversarial walk **with a second-best attack named**.
Neither prior-art codebase has anything comparable — they have
threat-model-by-omission.

---

## Lens 6 — Performance

### BettaFish

- **One daemon thread for the monitor + one per Flask report task.**
  No asyncio in the agent path. `task_lock = threading.Lock()`
  (`flask_interface.py:32`) serializes report-generation; one task
  at a time.
- **Hot path: 1-Hz file-tail loop.** Each tick stats 3 files and
  line-counts them via `sum(1 for _ in f)` (`monitor.py:385`) — full
  read on every file every second.
- **No caching.** Every `LLMClient.invoke` is a fresh HTTP call.
- **SSE event-stream with `Last-Event-ID` replay**
  (`flask_interface.py:215-230, 369-404, 1071+`). Each event has a
  monotonic `id`, a `type`, a JSON payload; subscribers can
  disconnect and resume via `history_since`. A loguru sink
  (`_stream_log_to_task`, 74-122) forwards every log line above
  DEBUG into the task's event stream. **This is the strongest
  pattern in either codebase.**

### MiroFish

- **Hybrid concurrency.** Flask `threaded=True`; simulation in a
  subprocess running its own asyncio loop; filesystem IPC at
  500 ms polling (`simulation_ipc.py:176`).
- **The simulation is the hot path by orders of magnitude.** Each
  round dispatches an `LLMAction` per active agent — typically
  5–20 agents × ~144 rounds = 720–2,880 LLM calls per platform
  per run, doubled for parallel. The OASIS-layer `semaphore=30`
  is the only concurrency throttle.
- **Dual-LLM-provider split** is real perf engineering: Twitter
  agents and Reddit agents hit different rate-limit pools.
- **JSONL append-only trace** (`agent_log.jsonl`) with timestamp +
  `elapsed_seconds` + step type (`report_agent.py:67-98`) — good
  replay-debugging substrate.

### Polaris contrast

`PerformanceWatcher` (v8.42) times the 3 atlas endpoints with a
3s budget (200 ms drift / 1 s alert), GETs `/api/health`, and runs
`EXPLAIN ANALYZE` with `SEQ_SCAN_REGRESSION_ROW_THRESHOLD = 1000`.
HYDRA itself currently has no observability stream — it produces
one synthesis per run. **BettaFish's SSE + Last-Event-ID replay
is the single highest-yield adoptable pattern.**

---

## Decisions — adopt / reject / invert

Each pattern below carries a verdict, a citation, and a
Polaris-flavored shape. Adoptable items become **maintenance
candidates** under the v8.31 steady-state contract — none open
new mission scope autonomously; VANTA names triggers as needed.

### ADOPT

| # | Pattern | Source | Polaris-flavored shape |
|---|---|---|---|
| A1 | **SSE event stream with `Last-Event-ID` replay** | BettaFish `ReportEngine/flask_interface.py:215-230, 369-404` | Add `/api/hydra/stream` SSE endpoint for live swarm observability. Events carry `watcher_name` + `severity` (info/drift/alert); `@security.require_role('admin','operator','auditor')`-gated; deque sized per-run, not message-count |
| A2 | **loguru-sink-as-broadcaster** (reuse the existing logger as event source; don't invent a parallel log path) | BettaFish `flask_interface.py:74-122` | Filter by `watcher_name` structured field, not by file-path keyword. Existing `ai-*` scripts and watchers already log structured — sink them into the SSE endpoint above |
| A3 | **JSONL append-only trace with `elapsed_seconds`** | MiroFish `ReportAgent` log (`report_agent.py:67-98`) | Parallel `journal/YYYY-MM-DD.jsonl` alongside the markdown journal — lets CognitiveWatcher and future ReflectionWatcher do statistical analysis ("decisions per session", "ramp shape per arc") without parsing markdown |
| A4 | **Filesystem IPC: command/response directories** for asking a running agent a question mid-run | MiroFish `simulation_ipc.py:117-187` + `ParallelIPCHandler:217-543` | A future Sanctum-style "ask the live watcher" mechanism: drop a query in `polaris_hydra/ipc/queries/<uuid>.json`, get a response in `polaris_hydra/ipc/responses/<uuid>.json`. Audit-of-record-friendly by construction (every interaction leaves a file) |
| A5 | **ReAct conflict-handling 3-strike protocol** for LLM emitting both `<tool_call>` and `Final Answer:` in the same response | MiroFish `report_agent.py:1330-1361` | If HYDRA host ever uses tool-calling in adaptive-thinking mode, copy this verbatim. Empirical wisdom worth not re-deriving |
| A6 | **Min-N-tool-calls-before-Final-Answer floor** as a "show your work" proxy | MiroFish `report_agent.py:1376-1389` | If AdversaryWatcher ever gates an alert behind LLM-driven analysis, require evidence from ≥2 channels before flagging. Raises cry-wolf bar without complexity |
| A7 | **Per-specialist LLM-provider abstraction** with separate keys + base URLs + model names | BettaFish `.env.example:23-62` + `InsightEngine/llms/base.py:30-55` | If HYDRA host grows beyond Opus 4.7 (e.g., wants Sonnet for cheap drill-downs), one shared client with per-watcher overrides via env. **Reject** BettaFish's verbatim copy-paste; Polaris keeps one shared client |
| A8 | **Two-tier temperature discipline** (`T=0.3` for JSON/factual, `T=0.5–0.7` for narrative) | MiroFish `llm_client.py:74` + `report_agent.py:1307` | If/when HYDRA host produces structured findings vs narrative synthesis, lower-T for the structured path. Free quality improvement |
| A9 | **Dual-LLM-provider concurrency split** | MiroFish `run_parallel_simulation.py:984-1037` | Bookmarked. Not relevant until HYDRA has >1 LLM-driven watcher AND rate-limiting becomes a real constraint |

### REJECT

| # | Pattern | Source | Why rejecting is correct for Polaris |
|---|---|---|---|
| R1 | **File-tailing as inter-agent communication** | BettaFish `LogMonitor.read_new_lines` + byte-position state machine (`monitor.py:389-423`) | TOCTOU on inode swap, O(n)/s line-counting, no schema, no append-only guarantee. HYDRA's direct-method-call `WatcherReport` flow already does this correctly; never regress |
| R2 | **Mutable filesystem state as audit trail** | BettaFish `clear_forum_log()` deletes log per session (`monitor.py:78-91`); MiroFish `shutil.rmtree(project_dir)` on user request (`project.py:237`) | Constitutional violation. Audit-of-record principle (9 schema + 1 filesystem instances) is non-negotiable |
| R3 | **Disclaimer-in-prompt as security** | BettaFish `llm_host.py:135, 163, 176, 206` | Prompt-bracketing is not a defense; it's a request to the provider with no enforceability. Polaris's defense is CSP + CSRF + role-gating + advisory locks |
| R4 | **Eval on model output** | BettaFish `html_renderer.py:874, 3083` (`ast.literal_eval` on LLM payloads) | Threat model assumes every model output is adversarial. Never eval. Parse with strict schema or reject |
| R5 | **No-op retry-decorator fallback** | BettaFish every `llms/base.py:19-27` catches `ImportError` and silently degrades retry to pass-through | Silent degradation of a reliability primitive is worse than noisy failure. If retry helpers are missing, fail loudly at import |
| R6 | **No auth + CORS `*` + default secret key + `DEBUG=True`** | MiroFish `__init__.py:43`, `config.py:24-25` | Polaris is the system whose threat model these defaults ignore. Adoption would regress v4/v8.22/v8.39 work |
| R7 | **Per-route blanket `try/except Exception: return 500 + traceback.format_exc()`** | MiroFish every route in `graph.py`, `simulation.py`, `report.py` | Polaris uses typed errors and never returns internal stack traces to a 4xx/5xx body |
| R8 | **In-memory `TaskManager` singleton as state-of-record** | MiroFish `task.py:62-186` | Lost on restart. Polaris job state with operational meaning lives in Postgres. Singleton-with-lock is OK for HYDRA's in-process *registry* but not for jobs that need to survive crashes |
| R9 | **Twin sites of truth for output directories** (hardcoded in multiple files) | BettaFish `flask_interface.py:415-417` ↔ `agent.py:325-327` | v8.30 substitutability principle requires single-source-of-truth constants |

### INVERT

| # | Their pattern | Polaris's inversion | Why |
|---|---|---|---|
| I1 | **Coordinator pulls from log** | **Watcher pushes to coordinator** (HYDRA's current shape) | Eliminates file-tail race + JSON-repair bandage + polling cost + inode-swap blind spot in one stroke |
| I2 | **LLM-mandatory** (BettaFish raises ValueError without API key; MiroFish breaks) | **LLM-optional-with-deterministic-fallback** (HYDRA `host.py`: Opus 4.7 when key is set, deterministic structured output otherwise) | Polaris's steady-state mandates auditable, deterministic core behavior; LLM synthesis is *commentary*, not truth |
| I3 | **Intentionally non-deterministic** (MiroFish `temperature=0.7`, no seeds, `random.sample()` for active agents) | **Seeded and replayable** for any constraint-attack simulation | The C1–C10 adversary walks must produce the same output every time. If HYDRA ever does Monte-Carlo over attacker strategies, record the seed in an AoR table |
| I4 | **Single-trusted-user assumption** (both codebases) | **Operator + auditor + admin + holder role-split** (v2 codified) | Even Sanctum-protocol (one principal + one agent) is structured around the four-instance AoR principle precisely because the role-split is constitutional |
| I5 | **Free-form user-input drops into prompts** (MiroFish `simulation_requirement` flows verbatim into ontology generator) | **Typed dataclass with length caps + allowlist** for any operator-input that drives structurally significant action | Polaris's UC procedures use parameterized SQL only; the same discipline applies to LLM prompts |
| I6 | **Mission framing claims LLM output as "predictions of the future"** (MiroFish `report_agent.py:552-557`) | **Synthesis voice frames outputs as hypotheses or current-state diagnostics**, never predictions | v8.31 decline-and-surface posture already enforces this culturally; the inverse rule for any future synthesis layer is "claim no more than evidence supports, tag every claim with its evidence path" |
| I7 | **Sync polling IPC at 500 ms** (MiroFish) | **Event-driven where possible** (advisory locks, Postgres LISTEN/NOTIFY) | Polaris already has the 6-entry advisory-lock catalog; polling is reserved for places Postgres LISTEN doesn't reach (filesystem watchers, external endpoints — PerformanceWatcher's atlas-latency channel, e.g.) |
| I8 | **One LLM client per engine, verbatim copy-paste** (BettaFish 4 near-identical `llms/base.py` files) | **One shared `WatcherReport` / `Finding` schema** in `polaris_hydra/watchers/base.py`; never let watchers diverge | BettaFish has 4 near-identical `State` dataclasses across engines; HYDRA has one base. Resist specialization |

---

## Strategic conclusion

**BettaFish is the immediate ancestor of HYDRA's host pattern.** The
v8.37 Sanctum cited `ForumEngine/llm_host.py` and the
specialist-engines-around-a-coordinator shape. The deep read confirms
that **HYDRA's design choices (push-not-pull, LLM-optional, sync
in-process, structured `WatcherReport` dataclass, audit-of-record
discipline) are the correct inversions** of BettaFish's architectural
debts (log-tail-as-channel, LLM-mandatory, daemon-thread polling,
ad-hoc JSON, mutable filesystem audit).

**MiroFish offers the cognitive substrate idea that HYDRA does not
yet have: filesystem-IPC live interrogation of a running agent.**
The pattern (`backend/app/services/simulation_ipc.py` + the
running-process polling loop in `run_parallel_simulation.py:217-543`)
is the closest thing to a "Sanctum mid-run" mechanism in either
codebase. If Polaris ever wants to ask a still-running HYDRA sweep
"what's your current finding for watcher X" without re-running it,
this is the right shape — audit-of-record-friendly by construction,
since every interaction leaves a file behind.

**The single highest-yield adoptable pattern is the SSE event-stream
with `Last-Event-ID` replay** (BettaFish `ReportEngine`). It would
give HYDRA an operator-facing live dashboard channel that survives
laptop sleep, while costing very little — the watchers already
return structured `WatcherReport`s; the new endpoint just publishes
them as SSE frames with monotonic ids.

**The single highest-yield rejection is treating LLM output as
trusted.** Both codebases do this — BettaFish via `ast.literal_eval`
on model payloads, MiroFish via framing LLM-fabricated simulation
output as "predictions of the future." Polaris's threat model treats
every LLM output as adversarial; HYDRA's deterministic-fallback
contract codifies this. Any future maintenance ship that introduces
LLM-driven decision logic must preserve the contract.

**Steady-state posture:** none of the adopt-list items above are
authorized to ship autonomously. They are surfaced here as
**maintenance candidates** under the v8.31 contract. The strongest
candidate (SSE event stream, A1+A2) would be LOW-risk
(non-constitutional, additive code, no schema change) but its
implementation requires VANTA's say-so per the standing post-v2
decline-and-surface posture.

**No external trigger fires from this analysis.** The next
mission-scope expansion still requires VANTA to name one.

---

## Cross-references

- v8.37 Sanctum: `sanctum/2026-05-12-new-chapter-swarm-hydra-arc-opening.md` — original "studied, not vendored" framing
- v8.43 Sanctum: `sanctum/2026-05-12-hydra-constitutional-integration.md` — Arc D close
- Constitutional layer: `MISSION.md` §"The cognitive substrate" — names HYDRA + watchers as the operative synthesis implementation
- HYDRA implementation: `polaris_hydra/host.py` + `polaris_hydra/watchers/*.py`
- Audit-of-record principle: `DEVNOTES/audit-of-record.md`
- Substitutability principle: `MISSION.md` §"What this section is NOT"
- Steady-state contract: `MISSION.md` §"Post-v2 strategic moment"
- Prior-art extracted at: `/tmp/polaris-prior-art/{BettaFish-main,MiroFish-main}/` (transient working copy; zips remain at `~/Downloads/`)
