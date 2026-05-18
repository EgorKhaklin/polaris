# Changelog (last 10 ships)

This file is the **curated index** of Polaris's recent ships. The full
audit-of-record — every entry from v1.0 through v9.23 byte-identical
— lives at [`archive/CHANGELOG-FULL.md`](archive/CHANGELOG-FULL.md).
v9.24 (BIG MISSION Tier 4 #12) compressed this file from 17,946 lines
to a 10-ship summary; the Anti-Architect's joint resolution in
`sanctum/2026-05-16-cognitive-substrate-must-bite.md` preserved the
full record at the archive path so v8.20 audit-of-record discipline
holds (the file moved; no entry was edited or deleted).

For per-ship deep detail, read the archive. For the active-decision
record, read [`meta/sanctum-index.md`](meta/sanctum-index.md).

---

## v9.42 — 2026-05-18 (Post-freeze hardening · HYDRA watcher false-positive cleanup · two drift-in-the-watcher fixes)

scope: cognitive-layer · ship_marker: hydra-watcher-cleanup · vocation: anti-surveillance (watcher honesty) · pattern20_instance: drift→test promotion loop (arch-2026-05-18-003)

The 2026-05-17 HYDRA pass surfaced 4 drift signals. Two of them were
not drift in the system being observed; they were drift in the
watchers themselves. v9.42 closes both, both with behavioral tests
under the Architect's drift→test promotion principle.

**Finding 1 — `soldier_log_tail` phantom alerts after Docker switch.**
The soldier reads `/tmp/polaris_app.log` with no staleness check. Under
the Docker runtime that file is frozen at the moment the last native
gunicorn shutdown wrote to it (2026-05-15 04:54 in this case); the
soldier kept emitting 5 alert pheromones every 6h reading the same
frozen ERROR + 4 WARNING lines (all about the in-memory rate limiter,
which v9.39 actually fixed at the root). **Fix:** add
`STALE_THRESHOLD_SECONDS = 600`. If mtime > threshold, return one
KIND_INFO observation flagging the source as dormant. Phantom-signal
storm stops within one cycle.

**Finding 2 — `ant_colony` watcher graded F5 on the wrong window.**
The watcher's `_summarize_balances` reduced ALL events from
`treasury-roll.json` into per-ant balances and graded the
"Treasury skewed strongly negative" finding on the aggregate
min/max. The aggregate is forever-polluted by pre-v8.91 frozen -2
penalties (G15 keeps them in the ledger). `scripts/ai-treasury-report.sh`
already splits "post-rebalance (since v8.91, +10/-1 in operation)"
distinctly from aggregate; the report's verdict reads ✓ in-band, but
the HYDRA watcher read ✗ skewed. **Fix:** mirror the report's split.
The watcher now exposes `post_rebalance_min_negative` /
`post_rebalance_max_positive` (filtered to amounts in {+10, -1}, the
current policy) and grades the F5 drift finding on the post-rebalance
subset. The aggregate is still exposed in evidence_summary for
operator visibility, but no longer drives the finding.

**Tests** (TestWave42V942, 5 cases):
- `test_v942_log_tail_has_stale_guard` — source-level invariant
- `test_v942_log_tail_returns_info_on_stale_file` — behavioral; stale
  file with ERROR content emits KIND_INFO, not KIND_ALERT
- `test_v942_log_tail_still_alerts_on_fresh_errors` — negative test;
  guard is not over-broad
- `test_v942_ant_colony_uses_post_rebalance` — source-level invariant
- `test_v942_ant_colony_summarize_filters_pre_rebalance` — behavioral;
  fake roll with -2 (pre-rebalance) + -1 (post) + +10 confirms only
  {+10, -1} amounts enter the post-rebalance subset

**Personas weighed in.** Architect: invoked arch-2026-05-18-003
(drift→test promotion loop) — every drift catch should become an
executable test. Done. Anti-Architect: silent on the scope (no
structured proposal dissent); flagged v9.39 already closed a
soldier_log_tail finding at the **root cause** (Redis env wired),
but didn't close the **failure mode** (stale-file phantom signal) —
v9.42 closes the latter, mirroring the v8.12 drift→test pattern.

Risk class: LOW (drift maintenance under heavy-production steady-state;
both edits are watcher-bug fixes, no constitutional surface touched).

## v9.41 — 2026-05-17 (AoR reclassification · canonical set 12 → 10 · two derived caches dropped · v9.x release)

The published-release ship for v9.x. Closes the constitutional gap
opened by v9.40's `.gitignore` polish commit (e56b310): three files
were untracked as auto-gen state (`meta/brain-map/brain-map.html`,
`polaris_swarm/civitas/census-roll.json`,
`polaris_swarm/civitas/treasury-roll.json`), but the constitution still
claimed all three as filesystem audit-of-record instances #10/#11/#12.
CI caught the divergence: structural invariants expected those files
present on origin.

**Architect + Anti-Architect adjudication:** the v8.66 + v8.68 ships
that classified census-roll/treasury-roll as filesystem-AoR failed the
AoR criterion ("fully reconstructs operation history without joining
elsewhere"). Census-roll is a cached projection over the actual
presence of `polaris_swarm/ants/ant_*.py` modules + civitas modules.
Treasury-roll is a cached sum over Pheromone-table deposits (already
schema-AoR #2) plus the reward function. Both are derived; neither is
source-of-truth. **Reclassification:** 12 total → **10 total (9 schema
+ 1 filesystem)**. The brain-map.html was the third reclassified file
(generator-marker invariant survives at the generator level).

**Documents updated** (canonical-count cascade):
DEVNOTES/audit-of-record.md (header + table rows #11/#12 + new
"v9.41 reclassification" subsection); MISSION.md §Principle 2;
CLAUDE.md C1 invariant; README.md "Twelve instances" prose;
DEVNOTES/README.md; docs/README.md; meta/sanctum-protocol.md;
docs/ARCHITECTURE-OVERVIEW.md; docs/operator/DR-SINGLE-REGION.md;
docs/reference/GLOSSARY.md; polaris_swarm/__init__.py docstring.

**Tests:** 2 renamed (`test_sanctum_protocol_aor_count_is_ten`,
`test_glossary_acknowledges_aor_count_is_ten` — regex now matches
`r"10 instances\s*\(9 schema\s*\+\s*1 filesystem\)"` + asserts the two
reclassified files are named in the protocol doc); 6 retired with
`@unittest.skip` decorators naming the replacing invariant
(test_brain_map_html_present, test_census_roll_json_exists_with_append_only_marker,
test_treasury_roll_is_filesystem_aor, test_a1_treasury_roll_has_v905_audit_marker,
test_brain_map_output_grows_with_mycelium, test_brain_map_has_auto_generated_marker);
1 adapted (`test_denarii_never_reference_polaris_identity` — dataclass
shape check always runs; file-scan portion wrapped in
`if os.path.isfile(roll_path):`). The class-shape claims are preserved
at the generator level; only instance-level file-presence checks
retired.

**Followup commit:** repointed 2 broken markdown links to the
generator script (`README.md:126` and `docs/story/STORY.md:73`) that
ai-link-check caught after the c1f0ea6 push went green on tests but
red on link discipline. Historical narrative numbers (222 nodes / 248
edges in STORY.md May-13 snapshot) preserved.

Final live counts: 937 tests, OK (skipped=6); 633 link references
resolved; `/api/version` reports v9.41.

Per-ship archive-move: v9.30 byte-identical to "Post-v9.24" section
in archive. CHANGELOG = 10 stable (v9.40..v9.31) + v9.41 in-flight.

## v9.40 — 2026-05-17 (Post-freeze hardening · operational completeness · v9.31+v9.39 cascade)

Three coupled defects surfaced when the v9.39 container rebuild
exposed them:

1. **`observability.py` (v9.31) missing from both Dockerfiles.**
   Container failed to boot: `ModuleNotFoundError: No module named
   'observability'`. The v9.17 regression-guard test was supposed
   to catch exactly this (it caught v8.97 webauthn_auth.py
   omission). But its regex `^\\s*import\\s+(\\w+)\\s*$` required
   nothing after the module name; my v9.31 edit had
   `import observability  # v9.31 ...` — trailing comment invisible
   to the regex. **Both the Dockerfiles AND the regex fixed.**
2. **Regression-guard only scanned `app.py`**, not `security.py`.
   v9.31 added `import observability` to security.py too. The new
   regex pattern (with trailing-comment tolerance) now applies to
   both files.
3. **`redis` Python lib missing from `requirements.txt`** →
   v9.39's `POLARIS_REDIS_URL` env-pass-through silently degraded
   to in-memory backend even when the URL was correctly set
   (`security.py` auto-selector requires the lib to be importable).

Live verified post-rebuild: `/api/version` reports v9.40,
`/api/metrics` returns real counters (was 404 in v9.30 container),
observability.py imports cleanly.

Per-ship archive-move: v9.29 byte-identical to Post-v9.24 section
in archive. CHANGELOG = 10 stable (v9.39..v9.30) + v9.40 in-flight.

`TestWave40V940` × 4 invariants: observability in both Dockerfiles;
regex tolerates trailing comments; regression-guard scans
security.py; `redis>=` in requirements.txt. Plus the underlying
regression-guard now catches future occurrences of this class.

## v9.39 — 2026-05-17 (Post-freeze hardening · POLARIS_REDIS_URL wired into docker-compose · soldier-log-tail finding closed)

Closes shakedown finding C: `soldier_log_tail` correctly flagged the
runtime warning "POLARIS_WORKERS=4 with in-memory rate limiter —
actual per-IP limits will be ~4× configured because each worker
holds its own buckets." Real defect surface (multi-worker dev
convenience).

Fix: `polaris_web/docker-compose.yml` now declares
`POLARIS_REDIS_URL: ${POLARIS_REDIS_URL:-}` in the app service
environment. Empty default preserves backward compat (security.py
auto-selects in-memory if URL empty). Operator sets the env var in
shell to activate, e.g.:

    brew services start redis
    POLARIS_REDIS_URL=redis://host.docker.internal:6379/0 \
        ./polaris_mac_launch.sh rebuild

After rebuild, `/api/health` will report `redis.backend = "redis"`
instead of `"memory"`, and the soldier_log_tail signals about
multi-worker bucket fragmentation should clear.

Per-ship archive-move pattern (established v9.38): v9.28 entry moved
byte-identical from CHANGELOG.md → "Post-v9.24 ships" section in
archive/CHANGELOG-FULL.md. CHANGELOG holds 10 stable (v9.38..v9.29)
+ this v9.39 in-flight = 11.

`TestWave39V939` × 1 invariant pins the env-pass-through declaration
in docker-compose.yml with the empty-default backward-compat
pattern.

## v9.38 — 2026-05-17 (Post-freeze hardening · archive-extension Sanctum · CHANGELOG = last 10 honestly)

Decided in `sanctum/2026-05-17-changelog-archive-extension.md`
(HIGH — amends v9.24's "no entry was edited or deleted" archive
claim). Pre-authorized by VANTA: "have the changelog at 10 latest
ships, the other ones move to the archive changelog."

The v9.24 compression committed "last 10 ships" in CHANGELOG.md
with byte-frozen pre-v9.24 history in
`archive/CHANGELOG-FULL.md`. As v9.25+ accumulated, the convention
needed entries to age OUT of CHANGELOG.md, but the archive's
byte-frozen claim forbade growth. v9.34 + v9.36 deferred via cap
relaxation (12→14). v9.38 closes it properly.

- **Amendment:** archive grows APPENDS-only (no edits or deletions
  of existing rows). New section `## Post-v9.24 ships` marks the
  boundary. v9.24–v9.27 moved byte-identical from CHANGELOG.md →
  archive's new section.
- **CHANGELOG.md state:** 10 ships + this in-flight v9.38 entry = 11.
  Cap restored 14 → 11.
- **ROADMAP.md** entry transitioned "NOW RIPE" → "DONE in v9.38."

`TestWave38V938` × 5 invariants: archive has post-v9.24 section;
v9.24–v9.27 in archive; v9.24–v9.27 NOT in CHANGELOG.md; CHANGELOG
has exactly 11 ships; Sanctum closed + indexed.

## v9.37 — 2026-05-17 (Post-freeze hardening · deep-scan cascade · 2 swarm-script hidden failures)

Round-three of the discipline catching itself. The 2026-05-17 deep
swarm/hydra scan (after v9.35+v9.36 cleared obvious bugs) surfaced
two more silent-failure patterns:

- **`ai-swarm-health.sh §IV` citizen activity** queried
  `WHERE tier = 'citizen'` but `Pheromone` has no `tier` column;
  query silently errored to empty, printing "No citizen deposits"
  regardless of reality. Citizens DO deposit (verified live: 5/6
  visible after fix — `censor_roll_keeper` silent by design, only
  fires on new-ant events). Fix: filter by JSONB `evidence ?
  'civitas_class'` per `_deposit_citizen_results` docstring in
  `polaris_swarm/colony.py`. Auto-discovers any future citizens.
- **`ai-swarm-bloom.sh find_python`** had candidate order putting
  `/private/tmp/polaris-codex-venv312/bin/python3` before
  `polaris_web/venv/bin/python3`. Codex venv exists + meets the
  3.9+ version check, but has NO psycopg2 → bloom always reported
  "psycopg2 not installed; use --dry." Fix: invert order + verify
  psycopg2 importable (mirrors `ai-hydra.sh` correct pattern since
  v9.04 — same comment said "same discovery pattern" while doing
  the opposite).

Live verified: §IV shows 5 citizens with deposit counts; bloom
processes 486 deposits across 72h and renders the hottest
brain-map nodes.

`TestWave37V937` × 3 invariants: citizen query uses JSONB marker;
bloom candidates have polaris_web/venv first; psycopg2 import-verify
present.

## v9.36 — 2026-05-17 (Post-freeze hardening · cascade fix from v9.35 · false-positive ALERT cleared)

Real defect closed: `security_watcher.py` read
`health["checks"]["rate_limiter"]["ok"]` from /api/health, but the
endpoint emits the rate-limiter component under key `"redis"` with
field `"status"` carrying "healthy"/"degraded"/"unhealthy" (per
`_health_check_redis` in `polaris_web/app.py:1800` — legacy name from
when Redis was the only backend). The watcher's key+field lookup
returned `{}` → `None` → falsy → false-positive ALERT every time the
watcher could actually reach the live app.

**Cascade from v9.35:** the port fix in v9.35 let the watcher reach
the live app for the first time, which immediately fired the
false-positive ALERT, which exposed the parser bug. Drift→test
promotion working: catching one bug exposes the next.

Fix: read `"redis"` key + check `status == "healthy"`. Live verified:
`rate_limiter_status` flipped from `not_ok` to `ok` with backend
correctly identified as `memory`. ALERT cleared.

`TestWave36V936` × 3 invariants: watcher reads canonical `"redis"`
key; checks `status == "healthy"`; sanity-pin that `app.py`'s
`/api/health` still emits the `redis` key (if app.py renames, the
watcher's parser must follow).

## v9.35 — 2026-05-17 (Post-freeze hardening · HYDRA watcher port env-driven · shakedown finding closed)

Real defect closed: `polaris_hydra/watchers/security_watcher.py` and
`polaris_hydra/watchers/performance_watcher.py` hardcoded the live-
app health probe to `http://localhost:2223/api/health`, but the
launcher canonical is `POLARIS_PORT` defaulting to **2222**. Port
2223 has never been a Polaris listening port. The watchers'
live-probe was permanently INCONCLUSIVE since the watchers were
introduced — every HYDRA brief carried "app not reachable on port
2223" as decorative info, never a real reachability check.

Surfaced by the 2026-05-17 full-system shakedown (post-v9.34
sweep). Fix: read `POLARIS_PORT` env at module load — same pattern
`polaris_web/app.py:4358`, `polaris_mac_launch.sh:145`, and
`scripts/ai-bootstrap.sh:267` already use.

- `polaris_hydra/watchers/security_watcher.py` — `HEALTH_URL` derived
  from `_POLARIS_PORT = os.environ.get("POLARIS_PORT", "2222")`
- `polaris_hydra/watchers/performance_watcher.py` — `HEALTH_URL` +
  `BASE_URL` env-derived; the operator-facing "app not reachable"
  detail string now interpolates the actual port so the diagnostic
  is honest, not misleading

Verified live: after the fix, performance_watcher's HYDRA evidence
flipped from `app_reachable=False` to `app_reachable=True` +
`endpoints_timed=5, endpoints_healthy=5`. The watchers can now
actually reach the live app for the first time since they were
written.

`TestWave35V935` × 3 invariants: both watchers read POLARIS_PORT;
no hardcoded port literals in either watcher's URL constants or
operator-facing detail strings; no live code references port 2223
(historical comments documenting the bug are OK).

## v9.34 — 2026-05-17 (Post-freeze hardening · swarm cron cadence · 2 long-latent defects closed)

Real defect closed: `polaris-cron-install.sh` wired `ai-hydra` (read-
side audit) but NOT the deposit-side colony runners. HYDRA's
`ant_colony` "zero pheromones in window" ALERT had been firing as
baseline since v9.03 — exactly the failure mode the cron-schedule
docs already promised was solved. Two new cron entries (matching
`docs/operator/OPERATIONS.md` documented cadence): soldier-tier
wake every 30 min for 60s, commander deployment every 6h.

- **`scripts/polaris-mycelium-wake.sh`** — new wrapper. Cron calls
  it instead of inline python. Sources `${POLARIS_ROOT}/polaris.env`
  (gitignored, operator-managed) so credentials stay out of
  `crontab -l`. Dev defaults for POLARIS_DB_HOST/PORT/NAME/USER;
  PASSWORD intentionally never defaulted (must come from
  polaris.env, `.pgpass`, or peer auth).
- **`scripts/polaris-cron-install.sh`** — adds 2 entries between
  the existing markers, lists wrapper in `required_scripts` gate so
  install refuses if wrapper missing.
- **`.gitignore`** — `polaris.env` now ignored so operator following
  the documented env pattern can't accidentally commit credentials.

Also closes a latent crash in `polaris_swarm/soldiers/swarm_witness.py`
(introduced v9.11): naive-vs-aware datetime subtraction silently
crashed every soldier-tier wake under the colony's graceful-failure
swallower. The priest tier was decorative-by-accident for ~30 ships.
Fix: promote `last` to tz-aware before subtracting (`last.tzinfo is
None` guard so future psycopg2 upgrades don't double-localize).

AP3 caught in flight: first draft of cron entries hardcoded
`POLARIS_DB_PASSWORD=polaris_dev_password` inline in the operator's
crontab. The Anti-Architect catch on `--dry-run` output forced the
wrapper redesign — credentials never leak to `crontab -l`.

`TestWave34V934` × 9 invariants pin: wrapper exists + executable +
no hardcoded password + sources polaris.env; `.gitignore` covers
polaris.env; cron entries present with correct cadence + call the
wrapper + no inline DB_PASSWORD; wrapper in `required_scripts` gate;
swarm_witness datetime fix in place with naive-input guard.

Verified end-to-end this session: HYDRA `ant_colony` ALERT
("zero pheromones") → DRIFT ("ok") after 1 soldier wake + 1
commander wake. 135 deposits in last 6h (68 commander + 67 soldier).
Remaining HYDRA drifts (treasury skew, real ERROR log signals) are
the system working as designed — surfacing real signal, not
masking silence.

Activation: `./scripts/polaris-cron-install.sh` (operator action).

## v9.33 — 2026-05-17 (Post-freeze measurement · Playwright Atlas-globe E2E scaffold · gotcha #6 pinned)

First post-freeze measurement ship per MISSION.md §"From v9.32 forward,
(b) Measurement". Closes second follow-up from
`sanctum/2026-05-17-plugin-installation-tier2.md` (Option A).

- **`polaris_web/test_e2e_atlas.py`** — 3 smoke tests against `/atlas`
  via headless Chromium: globe-element-present; HUD-renders-4-figures;
  no-CSP-violations-on-console. Smoke, not exhaustive (measurement,
  not carpet-bomb).
- **Graceful skip** when Playwright/chromium missing OR app unreachable.
  Activation: `pip install playwright && playwright install chromium &&
  ./polaris_mac_launch.sh up --detach`. Suite stays green on machines
  without the 250MB browser dependency.
- **Gotcha #6 pinned** — `wait_until="domcontentloaded"` (NOT
  `"networkidle"`; the 10s heartbeat POST means networkidle never
  resolves). `TestWave33V933` invariant prevents rediscovery.
- **`playwright>=1.40,<2.0`** added to `polaris_web/requirements.txt`.

`TestWave33V933` × 7 invariants pin scaffold + gotcha-#6 + skip
discipline + activation documentation + version bump.

## v9.32 — 2026-05-17 (Post-freeze hardening · hookify · ship-gate enforced by harness not memory)

First post-freeze hardening ship per MISSION.md §"From v9.32 forward,
(a) Hardening". Closes follow-up commitment from
`sanctum/2026-05-17-plugin-installation-tier2.md` (Option A).

Before v9.32: CLAUDE.md step 12 ("`ai-done.sh` must report READY")
was memory-dependent. v9.32 makes it harness-enforced.

- **`scripts/polaris-ai-done-hook.sh`** — PreToolUse hook scoped to
  ship commits only: triggers iff bash matches `git commit` AND
  `polaris_web/__version__.py` is staged. Runs `ai-done.sh`; exit
  non-zero blocks. Hygiene commits / branch ops / non-commit bash pass
  through.
- **`.claude/settings.json`** — registers the hook with
  `$CLAUDE_PROJECT_DIR` for portability across operator checkouts.
- **Override:** `POLARIS_HOOK_BYPASS=1` skips the gate but emits an
  audit-trail line to stderr (visible in session log) — v9.26
  AppendOnlyBypass discipline applied to this hook.

Also v9.32 corrected an in-flight bug in the v9.31 freeze invariant
`test_freeze_polaris_version_is_9_31`: original assertion pinned
`== '9.31'` which would fail on every post-freeze ship.
Generalized to `≥ (9, 31)` tuple-compare so freezing ≠ stopping —
hardening is explicitly permitted by the same MISSION.md clause that
enforces the freeze.

`TestWave32V932` × 7 invariants pin: hook script exists + executable;
settings.json wires the hook; passes through non-ship bash; passes
through non-ship commits; bypass documented with audit-trail; version
bumped; CHANGELOG justifies as hardening.

---

## How to read the older entries

```bash
# Full per-ship history (v1.0 → v9.23):
less archive/CHANGELOG-FULL.md

# Find a specific ship:
grep -n '^## v8.97' archive/CHANGELOG-FULL.md

# Current active decisions (Sanctum index):
less meta/sanctum-index.md

# Today's session log:
ls journal/ | tail -1
```

The full record is preserved byte-identical at the archive path. No
entry was edited or deleted in the v9.24 compression — the
v8.20 audit-of-record discipline holds.

*Per BIG MISSION Sanctum 2026-05-16, Tier 4 #12. CHANGELOG.md compressed
17,946 → ~180 lines; full content at [archive/CHANGELOG-FULL.md](archive/CHANGELOG-FULL.md).*
