# DEVNOTES: hydra-pheromone-integration

**Ship:** v9.04 / 2026-05-14.
**Sanctum:** [`2026-05-14-hydra-revamp-pheromone-integration.md`](../sanctum/2026-05-14-hydra-revamp-pheromone-integration.md).
**Pattern parallel:** v9.03 commander-vs-soldier vocabulary doc.

This is the watcher-vs-soldier intelligence-tier distinction, named
once so future ships have shared vocabulary.

---

## The two tiers

| Tier         | Implementation                  | Cadence       | Output       |
|--------------|---------------------------------|---------------|--------------|
| **Substrate**  | Mycelium swarm (commanders + soldiers) | High (~min)   | Pheromone deposits |
| **Lens**       | HYDRA's 9 watchers + CM         | Low (~run)    | WatcherReports |

Substrate = "what's happening right now, at high cadence, across
many nodes." Lens = "what's that mean for the system as a whole?"

Pre-v9.04 these layers existed but didn't talk:

- Watchers couldn't see swarm output (no Pheromone-reading code path)
- Swarm couldn't surface cross-watcher signal (no correlation)
- HYDRA couldn't reason across runs (no brief archive)
- HYDRA couldn't propose action (no ranking layer)

v9.04 closes all four gaps without breaking the 9-mortal mythology
(no new watchers; only infrastructure).

---

## The four new constructs

### 1. PheromoneReader (`polaris_hydra/pheromone_reader.py`)

The shared read-only window. Watchers + the Hydra host import this:

```python
from polaris_hydra.pheromone_reader import PheromoneReader
reader = PheromoneReader(window_hours=6.0)
snap = reader.snapshot()
snap.commander_count        # int
snap.soldier_count          # int
snap.per_soldier_class      # dict[str, SoldierClassReading]
snap.silent_soldier_classes # list[str] — classes silent >2h or never
snap.recent_alerts          # list[PheromoneRow] (kind='alert')

# Watcher-specific filter:
log_deposits = reader.deposits_by_class("soldier_log_tail",
                                         window_hours=1.0)
```

**Constitutional contract:**
- C1: `SELECT`-only against the Pheromone table; never `UPDATE`/`DELETE`
- C10: only metadata columns flow through (`deposited_by /
  deposited_at / kind / intensity / node_id / evidence /
  half_life_hours`); no holder PII path
- G1: deterministic (same query window → same result set, modulo new
  deposits arriving)
- G3: graceful — if psycopg2 missing OR DB unreachable, returns
  `PheromoneSnapshot(status='db_offline', ..., error='<reason>')`
  with all counts zero. Watchers that read pheromone-context surface
  no findings rather than crashing.

**Why a shared reader and not per-watcher SQL:** before v9.04 each
watcher would have had to write its own SQL. That meant N copies of
the connection-handling, the graceful-failure, the metadata-column
list. Pulling into one reader makes the constitutional posture
visible in one place + lets future watchers gain pheromone-context
in 3 lines instead of 30.

### 2. CorrelationEngine (`polaris_hydra/correlation.py`)

Runs after `Hydra.gather()`. Two strategies:

- **Strategy 1 (exact node_id match across distinct watchers):**
  strongest signal. If watcher A surfaces `route:/api/atlas` AND
  watcher B surfaces `route:/api/atlas`, that's a correlation. Full
  weight.
- **Strategy 2 (shared domain prefix across ≥3 distinct watchers):**
  weaker signal. If A/B/C all touch `route:*` (different routes,
  same domain), that's a correlation. 0.7× weight. Skipped if a
  Strategy-1 correlation already covers the same domain (avoid
  double-emit).

Output: ranked `CorrelatedFinding[]` by `(score, correlation_key)`
for determinism.

**Why both strategies:** node_id matches are the load-bearing case
(two watchers naming the same exact thing). Domain-prefix matches
catch the diffuse case where N watchers cluster on a domain without
any one node matching.

### 3. ActionQueue (`polaris_hydra/action_queue.py`)

Synthesizes findings + correlations into ranked `Action`s:

```
score = severity_score × confidence × (1 + 0.5 × constitutional_weight)
```

Where:
- `severity_score`: alert=7, drift=3, info=1
- `confidence`: 1 for singleton finding; ≥2 for correlations (the
  count of contributing watchers)
- `constitutional_weight`: count of `C[0-9]+` / `G[0-9]+` references
  extracted from finding text

Risk class ratchets to HIGH if the action touches C1 or C10
(constitutional load-bearing). HIGH-risk actions require a Sanctum;
ActionQueue proposes, VANTA disposes.

**Why singleton info findings are skipped:** they're housekeeping,
not action candidates. Including them would flood the queue with
"swarm is healthy" noise. The architect-recommended threshold
(Sanctum §IV.3) is severity ≥ drift OR confidence ≥ 2.

### 4. brief_archive (`polaris_hydra/brief_archive.py`)

`archive_brief()` writes Markdown to
`journal/hydra/<YYYY-MM-DD>-<HHMM>.md`. The format is human-readable
+ machine-greppable: section headers `## I.` … `## V.`, finding
titles preserved verbatim.

`compute_delta()` extracts finding-title sets and action-title sets
from current vs prior brief, returning `BriefDelta(new_findings,
closed_findings, new_actions, closed_actions, prior_path)`.

**Why filesystem and not DB:** HYDRA's brief is the audit-of-record
of the *system's own self-monitoring*. Filesystem matches the v8.20
filesystem-AoR principle (sanctum/, journal/, treasury-roll.json,
census-roll.json). Brief files accumulate; HYDRA never deletes
them. Operator may archive old ones manually if needed.

---

## The pheromone-context channels

Each of the 4 watchers (security/performance/schema/cognitive) gained
ONE new channel that reads the Pheromone substrate. The pattern is:

```python
def _check_pheromone_<class>(self) -> tuple[list[Finding], dict]:
    try:
        reader = PheromoneReader(window_hours=6.0)
        deposits = reader.deposits_by_class("soldier_<class>",
                                            window_hours=6.0)
    except Exception as exc:  # graceful
        return [], {"pheromone_<class>_status": f"reader_error:{type(exc).__name__}"}
    if not deposits:
        return [], {"pheromone_<class>_status": "no_deposits_in_window"}
    # Categorize by kind; surface alerts/drift as drift Finding
    # with `evidence={"pheromone_context": "soldier_<class>", ...}`
    ...
```

The `evidence["pheromone_context"]` key is the load-bearing handshake:
ActionQueue + CorrelationEngine can spot pheromone-sourced findings
to weight them differently if needed (currently treated equally; the
weighting hook exists for future tuning).

| Watcher       | Soldier read              | What it adds                |
|---------------|---------------------------|------------------------------|
| security      | `soldier_log_tail`        | runtime ERROR/WARNING entries the static CSP/CSRF check can't see |
| performance   | `soldier_route_pinger`    | continuous latency distribution (channel 1 takes one shot; this reads many) |
| schema        | `soldier_db_table_size`   | row-count growth (channel 1 confirms triggers present; this reads what's accumulating) |
| cognitive     | `soldier_sanctum_freshness` | stale OPEN sessions (channel 4 confirms index parity; this reads aging) |
| ant_colony    | (whole swarm)             | tier split + per-soldier-class freshness; load-bearing v9.04 add |

---

## Hybrid pipeline (`Hydra.speak_full`)

```
1. snapshot Pheromone substrate (once per pass)
2. gather watcher reports — each watcher reads the substrate via
   its v9.04 channel
3. synthesize voice (LLM via Claude Opus 4.7 with adaptive thinking;
   else deterministic fallback)
4. correlate cross-watcher findings
5. rank into ActionQueue (top-10 by default)
6. (optional) archive + compute delta vs prior brief
```

The pipeline is single-pass. No loops. Each stage takes the prior
stage's output. This preserves the Watcher-deterministic invariant:
swap any stage and the rest still composes (G1 + the v8.30
substitutability principle).

---

## node_id format convention (v9.06 / I1)

The CorrelationEngine splits on the first `:` to extract a
domain prefix. Watchers + ants depositing pheromones MUST follow
this format so correlation Strategy 2 (shared domain prefix)
works:

```
node_id ::= <domain>:<key>
```

Where `<domain>` is one of the 7 canonical domains and `<key>`
is the domain-specific identifier (URL path, table name, file
path, session id, etc.).

### Canonical domains (7)

| Domain        | Examples                                    | Used by |
|---------------|---------------------------------------------|---------|
| `route:`      | `route:/api/atlas`, `route:/login`          | security_watcher (channel 7), performance_watcher (channel 4), soldier_route_pinger |
| `schema:`     | `schema:tokenlifecycleevent`, `schema:identitytoken` | schema_watcher, soldier_db_table_size |
| `infra:`      | `infra:logs`, `infra:logs:tail`, `infra:db` | security_watcher (channel 7), soldier_log_tail, soldier_disk_usage |
| `cognitive:`  | `cognitive:sanctum`, `cognitive:hydra_brief` | cognitive_watcher (channels 4 + 6), soldier_sanctum_freshness |
| `swarm:`      | `swarm:cohort`, `swarm:soldier`, `swarm:commander`, `swarm:db` | ant_colony_watcher |
| `civitas:`    | `civitas:treasury`, `civitas:census`        | ant_colony_watcher (treasury channel), civitas_watcher |
| `mission:`    | `mission:section:Arc D`, `mission:c1`       | mission_watcher, ant_done_list_arithmetic |

Plus 1 reserved for build-system observability:

| Domain     | Examples                            | Used by |
|------------|-------------------------------------|---------|
| `build:`   | `build:pycache_orphan`, `build:zk`  | ant_build_freshness |

And 2 historical (kept for backwards-compat; new code SHOULD use
the canonical form above):

| Domain     | Status                                    |
|------------|-------------------------------------------|
| `file:`    | Used by some pre-v9.04 ants. New code: prefer `infra:` or `cognitive:` |
| `module:`  | Used by ant_test_gap. New code: prefer `infra:` |

### Why this matters

Without the colon convention:
- `_domain_prefix_of("naked_id")` returns `"naked_id"` (the whole
  string), so domain correlation never matches anything else;
  Strategy 2 silently degrades to no-op.
- ActionQueue's score formula treats all unrelated findings as
  uncorrelated; the action queue surface degrades.
- HYDRA brief readers have no shape contract on the node_id space.

### Lint structural invariant (v9.06 / I1)

`TestWave2V906.test_node_id_format_documented` verifies this section
exists. The existing watcher-evidence findings emit node_ids
matching the above convention — verified by inspection during the
v9.06 ship + by the 9 Hypothesis property tests in
`test_hydra_property.py` which use `node_id_strategy` (the same
canonical-domain set).

### Shared correlation surfaces (v9.10 / S1)

**Source:** `sanctum/2026-05-15-watcher-node-id-alignment.md`
Position B (DECIDED 2026-05-15).

Pre-v9.10, CorrelationEngine had fired 0 times across 6+ HYDRA
`--full` runs. Watchers stayed sovereign in their own domains
(per v9.04 §III.2); no two watchers ever observed the same node;
correlation by construction had no input.

v9.10 / S1 adds the **shared-surface convention**: a finding may
emit one domain-specific node_id (via the primary `node_id` key)
AND zero or more `runtime:*` shared-surface node_ids (via
`additional_node_ids: list[str]`) when the finding touches a
concern multiple watchers genuinely observe.

**Inclusion rule** (per Sanctum §IV.2): ≥2 watchers must already
emit findings about the concern before a shared surface is added.
Empirical inclusion, not speculative.

**Implementation:** the CorrelationEngine's new `_all_node_ids_of()`
helper returns ALL node_ids per finding; the correlate loop
indexes by EVERY node_id (one finding may appear under multiple
keys). Strategy 1 (exact node_id match across distinct watchers)
fires on the shared surface.

#### Canonical shared surfaces

| Surface | Watchers emitting | Concern | Status |
|---|---|---|---|
| `runtime:health` | security_watcher + performance_watcher | App reachability via `/api/health` (both watchers probe it) | ✅ wired (v9.10) |
| `runtime:swarm` | ant_colony_watcher + cognitive_watcher | Swarm tier alive / running (ant_colony sees soldier silence; cognitive sees HYDRA brief-archive stale; both indicate the cognitive substrate isn't running) | ✅ wired (v9.10) |
| `runtime:auth` | (security_watcher) + (mission_watcher) | Auth-flow + AppUser state (security has CSP/CSRF/role-gating; mission would have AppUser deltas) | ⏸ RESERVED — mission_watcher does not yet emit auth-related node_ids; will be wired when ≥2 watchers genuinely emit findings on this concern |

**Acceptance criterion** (per Sanctum §IV.3): ≥1 correlation
fires within 5 HYDRA `--full` runs after implementation.
**Verified live in v9.10 first run**: 1 correlation fired on
`runtime:health` (security + performance both observe app
offline).

#### Adding a new shared surface

1. Verify the inclusion rule: ≥2 watchers have been observed (in
   2+ HYDRA runs) emitting findings about the concern
2. Pick a `runtime:*` node_id name (consistent with the
   convention; lowercase + colon-separated)
3. In the relevant findings, set
   `evidence={"node_id": "<own-domain-key>",
              "additional_node_ids": ["runtime:<surface>"]}`
4. Update this table with the new surface
5. Add a structural invariant pinning the wiring
6. Run `bash scripts/ai-hydra.sh --full --save` to confirm
   correlation fires

---

## What this isn't

- **Not a 10th watcher.** The 9-mortal-head mythology is preserved
  (Sanctum §III.2). The 4 new constructs are infrastructure, not
  heads.
- **Not an LLM in the watchers.** Watchers stay deterministic;
  HYDRA is still the only LLM-bearing layer.
- **Not a write path.** Nothing in `polaris_hydra/` writes to the
  Pheromone table. The swarm is the only writer; HYDRA is reader.
- **Not Sanctum-bypassing.** ActionQueue may propose HIGH-risk
  actions, but it doesn't execute them. Sanctum protocol still
  gates constitutional changes (Pattern #20 Constitutional
  Discipline).

---

## Cross-references

- v8.62 commanders + v9.03 soldiers: the substrate this ship layers HYDRA over
- v8.65 + v8.72 Hydra-9 mythology: the mortality count this ship preserves
- BettaFish ForumEngine: the pattern this ship extends
- `meta/architect.md`: the synthesis voice (unchanged)
- `MISSION.md` C1, C10: constitutional preservation
- `polaris_swarm/soldiers/README.md`: per-soldier-class contracts
