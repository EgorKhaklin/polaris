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

## v9.31 — 2026-05-17 (Mechanical freeze-line verification · 7 freeze conditions encoded as invariants · the terminus)

Per MISSION.md §"Freeze line — definition of done (v9.27, amended once
v9.29)", the core is **done at v9.31** when ALL seven conditions are
mechanically verifiable from outside the cognitive layer. v9.31 makes
each condition a Python test in `TestWave31V931` — if every test
passes, the freeze is satisfied.

Surfaced by Option A sequencing the user approved after the petitioner
discovered v9.31 was NOT a 5-minute mechanical bump as initially
represented — 5 of 7 conditions were failing. Sanctum
`sanctum/2026-05-17-v9-31-prep.md` scoped the 5 gaps; VANTA approved
"Full prep"; gaps closed in dependency order before the version literal
moved.

- **Gap 1 (commit hygiene)** — 44 files / 3973 insertions committed in
  prior commit `2b60179` ("hygiene: commit accumulated 2026-05-16/17
  session work"). Kill test no longer refuses on dirty tree.
- **Gap 2 (observability, cond 6)** — `/api/metrics` route + counter
  call sites in `_metrics_after_request` (request+5xx), `security.py`
  (auth-failure password), `webauthn_assert_finish` (auth-failure
  webauthn ×2), `_check_and_record_duress` (the anti-coercion alarm
  per T8#11). 4 headline counters now actually fire.
- **Gap 3 (MTTR back-fill + parser fix, cond 4)** — 3 honest
  resolutions with provenance (treasury 04:09, Mycelium 03:31, CSP
  regex 03:24). `_parse_iso` helper handles 12-day silent +00:00Z
  double-suffix bug rejecting every early-ledger entry. Trend slope
  **-1.72h/ship (loop earning)**. v9.30 binding clause passes.
- **Gap 4 (mttr.sh regex)** — Anchored `^__version__` to skip a
  docstring example.
- **Gap 5a/5b (chaos test, cond 3)** — `brew link --force libpq`
  exposed hidden fail-open in `polaris-recover-admin.sh`: `run_psql`
  swallowed errors via `2>/dev/null` + `set -e` exited silently before
  any refusal reached operator. Wrapped to emit loud `EXIT_DB`
  refusal. **Real security defect caught by chaos test the moment
  psql became available.** 3/3 fail-safe.
- **Cond 1, 5, 7** — ai-coherence STRUCTURE INTACT; v9.30 binding
  passes; `__version__` 9.30 → 9.31.

**This is the freeze.** Post-v9.31 work is bounded to (a) hardening,
(b) measurement, (c) thesis cold-read evidence per MISSION.md §"From
v9.32 forward". Integration ships (v9.32 hookify, v9.33 playwright)
are post-freeze hardening — separate ships, separate version bumps.

## v9.30 — 2026-05-16 (Original 13-item arc completes · 7 items + 174M deleted · no item #14 · Pattern #20 24th instance)

VANTA: "proceed lets do it." 7 remaining items shipped under the
subtraction-or-enforcement rule. **Ceiling held at 13. No item #14
added.** Freeze line unchanged (v9.31 per v9.29 amendment).

- **#7** — `polaris_zk/target/` deleted (174M → 64K). `.gitignore`
  already excluded it. *Cheapest real win.*
- **#12** — [`scripts/polaris-idempotency-test.sh`](scripts/polaris-idempotency-test.sh)
  + CI step. Loads `00_load_all.sql` twice, asserts identical state.
  Retires the saga of reload-safety comments.
- **#6** — ZK CI prove-verify already in v9.24 (ci.yml line 149).
  v9.30 pins via invariant.
- **#11** — Brain-map AUTO-GENERATED marker added to
  `ai_brain_map.py` HTML template + `brain-map.html`. Regen is the
  only update path.
- **#10** — Atlas HUD invariant `test_atlas_stats_endpoint_reads_from_db_function_only`
  pins that all HUD fields come from `row['...']` cast — no Python-
  side aggregation. HUD cannot lie by construction.
- **#8** — [`meta/foresight-predicate-audit.md`](meta/foresight-predicate-audit.md):
  foresight ALREADY has the v9.12 empirical-graduation predicate
  (50% acceptance over 6 distinct months or SUNSET). KEEP through
  ~Nov for the window to fire.
- **#13** — [`meta/observer-map.md`](meta/observer-map.md): same 4
  watchers v9.28 flagged DEPRECATION_CANDIDATE are independently
  re-confirmed by observer-to-artifact mapping. **Physical cuts
  deferred** to operator-routed amendment per [`meta/freeze-amendment-protocol.md`](meta/freeze-amendment-protocol.md) — the
  9-mortal-heads pin from v9.04 §III.2 needs its own amendment.

**13-item arc tally:** 1-5 (v9.28), 9 deleted on merits (v9.29),
6+7+8+10+11+12+13 (v9.30). 12 shipped + 1 deleted. AP3+AP7+AP8
surfaced. TestWave30V930. `POLARIS_VERSION` 9.29 → 9.30.
**v9.31 = mechanical freeze-line verification only. One ship to the freeze.**

## v9.29 — 2026-05-16 (Constitution + Sanctum + CM hardening · ONE freeze amendment v9.30 → v9.31 logged with cost · external referent caught locally-valid-globally-a-ratchet · Pattern #20 23rd instance)

External referent (routed by operator) caught the agent proposing a
"rebased ceiling" of 19 from the v9.28-committed 13 under the banner
of "honest accounting" — locally-valid steps, globally a ratchet.
Verdict: ship 7 as v9.29; cut item 9 (CLI canonical) on its merits
as elaboration, not counterweight; amend freeze v9.30 → v9.31 ONCE
with cost. Ledger does NOT balance to 19; the slip IS the cost.

**Amendment log entry (per [`meta/freeze-amendment-protocol.md`](meta/freeze-amendment-protocol.md)):**

| Date | Ceiling | Old → New | Cost |
|------|---------|-----------|------|
| 2026-05-16 | freeze-line version | v9.30 → v9.31 | one ship slip |

**7 items shipped (subtraction-or-enforcement):**
- **C1:** every C-number must have ≥1 invariant in test_structural_invariants.py
- **C2:** hard cap = exactly 10 C-numbers in MISSION.md table
- **C3:** substitutability proven via AST — no C-invariant imports polaris_hydra
- **S1+S2+S3:** [`scripts/polaris-sanctum-status.sh`](scripts/polaris-sanctum-status.sh) classifies 59 Sanctums ACTIVE/SUPERSEDED/DEAD + core/apparatus + reference-check. **First-run data: 54 ACTIVE / 5 SUPERSEDED / 0 DEAD. ACTIVE scope = 13 core / 41 apparatus = ratio 0.32 = APPARATUS-DOMINANT.** Operator data for post-freeze cuts.
- **CM1:** [`scripts/_cm_check.py`](scripts/_cm_check.py) gains AST-count anchor (test count from python's ast module; CM does not author it; floor 850 ratchets up only by amendment).

**Deletion:** item 9 (CLI as canonical) from v9.28's 13-item arc, on its merits (adds interface surface; fails subtraction-or-enforcement). NOT used as ceiling counterweight.

**Structural primitive:** [`meta/freeze-amendment-protocol.md`](meta/freeze-amendment-protocol.md). Rule: ceilings move only by recorded amendment with stated cost, never by re-derivation. Two honest moves only — displace inside, or amend once. Append-only amendment log; v9.29 is first row.

**The deeper lesson, recorded so it inherits:** the agent reasoned correctly at every local step; the aggregate was the freeze expanding 46% under the banner of discipline. The gap between locally-valid and globally-correct is the structural reason the amendment power over the agent's own ceiling lives outside the agent's write access — and the reason the operator's reflex to route through an outside check is the only thing that catches it. Recorded verbatim in `meta/freeze-amendment-protocol.md` §"The deeper lesson."

**4 of 8 anti-patterns surfaced** (AP1, AP3, AP5, AP8) on the agent's own reasoning about its own ceiling. TestWave29V929 (19 invariants; this CHANGELOG entry pinned by `test_changelog_has_v9_29_entry`). `POLARIS_VERSION` 9.28 → 9.29. **v9.31 is the new freeze. The slip is the cost.**

## v9.28 — 2026-05-16 (HYDRA revamp · Tier 1 of v9.28/v9.29/v9.30 freeze-completion arc · Pattern #20 22nd instance · structural move one layer up)

VANTA: *"the Hydra should be improved, and the improvement is the same
structural move applied one layer up."* First of three ships in the
v9.28-v9.30 freeze-completion arc. 5 Hydra items + Sanctum scorecard
addition + scope-rebase pre-allocation.

**Hydra #1 — predicate-or-delete for watchers** (mirrors v9.24 T1#2
ant-predicate pattern one layer up). [`meta/watcher-predicates.md`](meta/watcher-predicates.md)
enumerates each of 9 watchers + CM with single falsifiable claim AND
VANTA's external-record refinement (the outside-the-cognitive-layer
artifact that confirms the predicate). **5 KEEP** (schema, security,
performance, adversary, ant_colony, CM) — all grounded in DB rows or
HTTP responses. **4 DEPRECATION_CANDIDATE** (cognitive, mission,
trajectory, civitas) — only claims are about narrative or internal
HYDRA state (AP1 by construction). v9.30 grace cycle: ground the
predicate against external record OR cut.

**Hydra #2 — correlator triage.** [`polaris_hydra/correlation.py`](polaris_hydra/correlation.py)
gains `CorrelationEngine.triage()` that splits findings into
`escalations` (≥2-watcher correlations; the brief's headline),
`lone_alerts` (single-watcher alerts; uncorroborated; still emitted
because alert is non-suppressible), and `suppressed_below_threshold`
(single-watcher findings below alert; count only; default-suppressed
per Hydra #2's "lone-watcher finding is low-confidence by default
and suppressed below a threshold"). Brief becomes a ranked
corroboration list.

**Hydra #3 — cross-run delta as primary output.** [`polaris_hydra/brief_archive.py`](polaris_hydra/brief_archive.py)
gains `persist_correlated()` + `delta_correlated()` that maintain
`journal/hydra/_last_correlated.json` (single file; overwritten each
run; separate from the date-stamped audit-of-record briefs). Delta
returns `new` / `resolved` / `escalated` / `unchanged_count` —
matches the "emit only new, resolved, or escalated" Hydra #3 spec.

**Hydra #4 — runtime-grounding for schema + security.** [`schema_watcher.py`](polaris_hydra/watchers/schema_watcher.py)
gains `query_live_schema()` (psycopg2 diff vs declared schema; falls
back to INCONCLUSIVE on connection failure per chaos-test pattern).
[`security_watcher.py`](polaris_hydra/watchers/security_watcher.py)
gains `probe_running_app()` (urllib HTTP probe at `/dashboard`;
asserts 200-anonymous = alert; 302/401/403 = held; unreachable =
INCONCLUSIVE).

**Hydra #5 — CM enforces, not observes.** [`scripts/_cm_check.py`](scripts/_cm_check.py)
implements the constitutional-meta-constraint check: __version__.py
matches latest CHANGELOG entry; MISSION.md §Freeze line + v9.30
present; watcher-predicates.md enumerates exactly the watchers in
the source tree. Wired into [`scripts/ai-done.sh`](scripts/ai-done.sh)
as step 15: CM-mismatch → non-zero exit. Override
`POLARIS_ALLOW_CM_MISMATCH=1` with audit-trail line (mirrors
POLARIS_ALLOW_ALERT_SHIPS from v9.24). **CM caught two real defects
on first run** (stale version regex + missing ant_colony_watcher in
predicates doc) — proving the gate bites.

**Addition A — Sanctum scorecard** (VANTA's structural move applied
to the Sanctum protocol itself). [`meta/sanctum-scorecard.json`](meta/sanctum-scorecard.json)
+ [`scripts/polaris-sanctum-scorecard.sh`](scripts/polaris-sanctum-scorecard.sh).
Load-bearing metric: `joint_resolution_survival_rate_trailing_10sanctums`.
Auto-classified retroactively at next-3-ships boundary; refuses
manual classification per AP3; matches v9.25 swarm-scorecard
discipline one layer up. **The same predicate test the Sanctum
applied to watchers is now applied to the Sanctum itself.**

**Addition B — scope-rebase pre-allocation.** The 3-ship arc (v9.28
+ v9.29 + v9.30) will add narrative. Pre-allocated rebase budget
documented in v9.28 Sanctum §II.B. Anti-architect-locked: "v9.28-
v9.30 freeze-completion allocation; not extensible past v9.30."

**Anti-architect anti-pattern hits — 4 of 8** (AP1, AP3, AP7, AP8).
The predicate-or-delete pattern fires the same anti-pattern axes one
layer up. 5 of 9 watchers KEEP; 4 DEPRECATION_CANDIDATE. The
external-record refinement on Hydra #1 is the operator-grounding
that distinguishes class-shaped from instance-shaped rules.

**The 13-item ceiling.** v9.27 committed v9.30 as the freeze. The
13 items VANTA cataloged for v9.28-v9.30 ARE the def-of-done content.
Per the v9.28 Sanctum §IV: no item #14 may be added without VANTA
explicitly authorizing scope re-opening.

7 new artifacts (sanctum + watcher-predicates + sanctum-scorecard
JSON + sanctum-scorecard script + CM-check Python + edits to
correlation.py, brief_archive.py, schema_watcher.py, security_watcher.py,
ai-done.sh). TestWave28V928 (~15 invariants). `POLARIS_VERSION`
9.27 → 9.28. **Two ships left until the freeze.**

## v9.27 — 2026-05-16 (Tier 7+8 · thesis HYPOTHESIS-NOT-VERIFIED · freeze line at v9.30 · the terminus · Pattern #20 21st instance)

VANTA: *"Item 12 is the real terminus. Everything in both lists is in
service of being able to write it and mean it."* 6-item composite
across Tier 7 (test the thesis for real) and Tier 8 (operational
maturity); Pattern #20 21st instance — the final BIG MISSION ship.

**Tier 7 — the thesis test.** **T7#7:** chose a contained feature
(structural-invariant addition for `meta/swarm-mttr.json` schema_version)
and walked through what a fresh agent reading ONLY CLAUDE.md would do
(`meta/cold-read-walkthrough-v9.27.md`). **10 intervention points
logged** — places where session-context filled gaps CLAUDE.md did not
(TestWave naming convention, version-bump trigger, CHANGELOG entry
shape, scorecard append, MTTR raise/resolve, etc.). **Acknowledged
limitation:** self-evaluation by the agent that built the system is
AP1-compromised; the real cold-read remains the unconducted test.
**T7#8:** added a **14-step ship sequence** to CLAUDE.md ("Ship
sequence (v9.27 cold-read closure — T7#8)") that captures the 10
interventions as class-shaped rules (not instance-shaped per
Anti-Architect AP3 refusal). Two interventions honestly named as
"accept it never will" (the actual cold-read by external party; spec-
completeness on every contained feature). **T7#9 — the load-bearing
decision:** `docs/THESIS.md` REFRAMED to **HYPOTHESIS-NOT-VERIFIED**.
The strong claim ("agent-maintainable architecture pattern is novel
and works") is RETIRED. The page now states the hypothesis + the
falsification test + the invitation to replicate. **The Anti-Architect's
contest produced this:** publishing requires evidence; self-evaluation
is not evidence; the experiment is preserved as good tooling.

**Tier 8 — operational maturity.** **T8#10:** `scripts/polaris-chaos-test.sh`
injects 3 realistic failure modes (db_unreachable_mid_recovery,
zk_binary_absent, epoch_close_interrupted) and asserts FAIL-SAFE
NEVER OPEN. Each scenario deterministic, CI-runnable, ≤5min wall.
**T8#11:** `polaris_web/observability.py` + `DEVNOTES/observability.md`
ship 4 operator-readable metrics (request_rate, error_rate,
auth_failures, **duress_events as headline** per anti-coercion
vocation). No metrics backend — structured logs to stdout + JSON
`/api/metrics` endpoint per Anti-Architect "no Prometheus exporter
without an operator who runs it" refusal.

**T8#12 — THE TERMINUS.** `MISSION.md` gains §"Freeze line — definition
of done (v9.27)". **The core is done at v9.30** when 7 mechanical
conditions hold (all 10 hard constraints schema-enforced; kill test
5/5; chaos test 3/3; ≥3 MTTR resolved findings; v9.30 binding-clause
fired; observability wired into app+security; POLARIS_VERSION=9.30).
**From v9.31 forward all work is (a) hardening, (b) measurement, OR
(c) thesis cold-read evidence.** New arcs require Sanctum + named
external trigger (NOT pre-catalogued). **Abandonment clause:** if no
cold-read attempt by v9.40, the thesis is documented inconclusive
and the strong claim retired permanently. **The freeze line is
mechanical, externally verifiable, includes the abandonment
condition.** This is the operational answer to "this stops being
infinite."

**Anti-Architect anti-pattern hits — 5 of 8 fire substantively**
(AP1, AP3, AP5, AP7, AP8) — the most across any Tier ship. Maximum
self-deception risk on a ship that assesses the protocol itself →
maximum counterweight required. The Anti-Architect's contest of T7#9
produced the most important result of the entire BIG MISSION arc:
the strong claim is killed on insufficient evidence; the experiment
is preserved; future external replication is the only way to revive
the claim. **This is the protocol working at its hardest: refusing
to publish something the agent wants to publish, because the evidence
isn't there.**

6 new artifacts (sanctum + cold-read walkthrough + CLAUDE.md 14-step
sequence + chaos script + observability module + observability
DEVNOTES + MISSION.md freeze line + THESIS.md reframe). TestWave27V927
pins each artifact. `POLARIS_VERSION` 9.26 → 9.27. **v9.30 is the
freeze. v9.40 is the abandonment threshold. The terminus is committed.**

## v9.26 — 2026-05-16 (Kill test 80% → 100% · close the AppendOnlyBypass coverage gap surfaced by v9.25)

LOW-risk fix-from-v9.25. The v9.25 kill test shipped at 80% pass rate
with `DefectAppendOnlyBypass` escaping; v9.25's CHANGELOG recorded it as
a known coverage gap. v9.26 closes it.

**Two real bugs, both surfaced by the kill test working correctly:**

1. **Defect regex was a no-op.** `polaris_swarm/fault_injection.py`'s
   `_apply_append_only_bypass` looked for `RAISE EXCEPTION 'TokenLifecycleEvent[^']*'`
   — a pattern that NEVER appeared in `polaris_sql/06_triggers.sql`. The
   actual RAISE EXCEPTION uses `TG_TABLE_NAME` parameterization, not a
   literal table name. The "defect" never modified the file; v9.25's
   "escape" was therefore vacuous — there was no defect to detect. Fix:
   regex now targets the structural pattern (`END IF;` + blank line +
   `RAISE EXCEPTION`) which IS present, and inserts an unconditional
   `RETURN OLD;` immediately before the terminal RAISE — the real
   production-shape defect (developer adds RETURN OLD to unblock a
   local test, forgets to remove).

2. **`test_audit_trigger_rejects_modifications` was insufficient.**
   Strengthened to detect any unconditional RETURN OLD that appears
   BEFORE the function's terminal RAISE EXCEPTION (excluding RETURN OLD
   inside legitimate IF/ELSIF/ELSE carve-outs like the v8.87 GUC path).

**Kill test result: 5/5 caught in 1 pass (100%).** All five defect
classes — DropCsrf, CspUnsafeInline, RevokeAuthDecorator,
C3DropUniqueIndex, AppendOnlyBypass — now detect within ~25 seconds
each via the structural-invariant channel.

**Honest accounting per Anti-Architect:** the v9.25 ship's 80% was
honest at the time (a real "we don't know what to detect" gap). This
v9.26 ship is the kill test doing its job — surfacing a gap that
closes within one cycle. The v9.30 binding clause didn't need to fire;
the operator-agent loop closed naturally.

`POLARIS_VERSION` 9.25 → 9.26. Scorecard appended.

---

## v9.25 — 2026-05-16 (BIG MISSION Tier 5 · swarm must earn its weight, with numbers · Pattern #20 20th instance · v9.30 binding clause)

VANTA: *"After Tier 4 the system functions and is disciplined. This
phase proves it works instead of asserting it..."* 3-item measurement
ship; the v9.24 mechanism now has scoring. **T5#1 swarm scorecard:**
[`meta/swarm-scorecard.json`](meta/swarm-scorecard.json) + [`scripts/polaris-swarm-scorecard.sh`](scripts/polaris-swarm-scorecard.sh)
append per-ship findings_raised / TP / FP / escaped_defects. Auto-
classified from CHANGELOG fix-list (Anti-Architect refused manual
classification per AP3). Escapes back-fill retroactively when later
ships reference "fix from v9.X" (refused self-reported escapes per AP8).
Load-bearing metric: `escape_rate_trailing_10ships`. **T5#2 kill test:**
[`polaris_swarm/fault_injection.py`](polaris_swarm/fault_injection.py)
ships 5 realistic defects (3 production-shape: DropCsrf, CspUnsafeInline,
RevokeAuthDecorator; 2 invariant-shape: C3DropUniqueIndex, AppendOnlyBypass).
[`scripts/polaris-swarm-killtest.sh`](scripts/polaris-swarm-killtest.sh)
runs each defect through 3 detection channels, measures catch-rate +
time-to-detect. Pass bar ≥70% in 1 pass / ≥90% in 3 passes. Refuses
dirty git tree by default (override `POLARIS_KILLTEST_ALLOW_DIRTY=1`).
**First kill-test run showed coverage gap;** v9.25 also adds 5 new
structural invariants (CSP unsafe-inline, @login_required on protected
routes, audit trigger RAISE EXCEPTION, C3 partial unique index, CSRF
on POST handlers) — production-shape checks, not defect-specific
cheats. **T5#3 MTTR trend:** [`meta/swarm-mttr.json`](meta/swarm-mttr.json)
+ [`scripts/polaris-swarm-mttr.sh`](scripts/polaris-swarm-mttr.sh)
record raise/resolve timestamps from v9.25 forward (Anti-Architect
refused fabricated pre-v9.24 baseline per AP1+AP8 — measurement starts
at v9.25; meaningful trend emerges at v9.30). 36 existing briefs
imported as historical raise-events. **v9.30 binding clause** recorded
in constitutional record: *if mttr_trend_slope is not negative at
v9.30, the agent is bound to open a cognitive-layer-deletion Sanctum*
— making "cut deeper if not earning" structural, not aspirational.
**6 new artifacts** + 5 coverage-closure invariants. **Anti-Architect's
dissent materially shaped 3 of 3 items.** Pattern #20 Constitutional
Discipline 20th instance. `POLARIS_VERSION` 9.24 → 9.25.

## v9.24 — 2026-05-16 (BIG MISSION composite II · cognitive substrate must bite · Pattern #20 19th instance)

VANTA's framing: *"the swarm is dead weight, the headline crypto is a
stub, and the narrative mass is regulating nothing."* 14 items across 4
tiers debated by the Architect + Anti-Architect (Pattern #20 19th
instance). **Tier 1** wires the observability apparatus to consequence:
the ai-done.sh pre-ship script now gates on HYDRA ALERT findings
(override = `POLARIS_ALLOW_ALERT_SHIPS=1`); every commander ant gets a
falsifiable predicate in [`meta/ant-predicates.md`](meta/ant-predicates.md) (5
flagged DEPRECATION_CANDIDATE for v9.25 grace cycle); the Treasury
becomes a real selection oracle via [`scripts/polaris-ant-ranking.sh`](scripts/polaris-ant-ranking.sh);
the stigmergic loop is closed in [`polaris_swarm/stigmergy.py`](polaris_swarm/stigmergy.py)
(recurrence-weighted scan ordering — Anti-Architect banned "emergent"
vocabulary); denarii now purchase scan attention via
[`polaris_swarm/denarii_scheduler.py`](polaris_swarm/denarii_scheduler.py) (quartile-based with 24h
floor); external oracles ([`polaris_hydra/oracles.py`](polaris_hydra/oracles.py) +
[`scripts/polaris-oracle-runner.sh`](scripts/polaris-oracle-runner.sh)) pipe launcher status +
ai-adversary exit codes into the brief with AGREE/DIVERGE/NOTE
reconciliation. **Tier 2** hardens the core: real ML-DSA-65 signing path
shipped behind `POLARIS_USE_REAL_PQC=1` flag in
[`polaris_web/pqc_signing.py`](polaris_web/pqc_signing.py) (honest accounting: oqs
not installed by default; flag-off means current `token_value` is a
deterministic string, NOT post-quantum signed — operator activation
documented in module header); [`scripts/polaris-concurrency-harness.sh`](scripts/polaris-concurrency-harness.sh)
measures C3 behavior under N concurrent issuers; CI gains an explicit
ZK prove-verify roundtrip (not just `cargo test`); ground-truth
validation framework ships in [`polaris_swarm/fixtures/`](polaris_swarm/fixtures/) + 3
fixtures + [`scripts/ai-swarm-validate.sh`](scripts/ai-swarm-validate.sh)
(precision/recall integration scoped to v9.25). **Tier 3** ships
[`docs/THESIS.md`](docs/THESIS.md) — one-page argument that Polaris's contribution
is the agent-maintainable architecture pattern (5 composed primitives:
constitution + risk classes + structured second-opinion + consultation
protocol + CI as binding-consequence-layer); Anti-Architect refused
mythology vocabulary, page reads flat. **Tier 4** installs mechanical
hygiene: [`scripts/pre-commit-scope-check.sh`](scripts/pre-commit-scope-check.sh)
+ [`meta/scope-rule-baseline.json`](meta/scope-rule-baseline.json) (narrative/core
word-count ratio with 0.10 headroom; refuses commits exceeding ceiling;
override = `POLARIS_ALLOW_SCOPE_OVERRUN=1`); CHANGELOG.md compressed
from 17,946 lines to ~150 (full text preserved in archive); CLAUDE.md
trimmed to invariants + predicates + loop wiring. **Anti-Architect's
dissent materially shaped 5 of 14 items:** refused immediate deletion
of un-predicated ants (operator grace cycle); refused half-implemented
PQC ship (forced honest accounting if liboqs missing); refused mythology
vocabulary in thesis + stigmergy; refused archival of journal/sanctum
(only CHANGELOG compressed; the constitutional record stays at original
paths); refused new CLAUDE-NARRATIVE.md file (net delete, not net
move). 6 of 8 anti-patterns surfaced (AP1, AP3, AP4, AP6, AP7, AP8). 16
new artifacts. TestWave24V924 invariants pin every ship. `POLARIS_VERSION`
9.23 → 9.24.

_Per CHANGELOG.md convention (last 10 ships only): v9.23 → v9.15 trimmed
2026-05-17 with v9.31 + v9.32 ships. v9.24+ entries stay in CHANGELOG.md
until an explicit archive-extension Sanctum (not yet opened). Pre-v9.24
history at [archive/CHANGELOG-FULL.md](archive/CHANGELOG-FULL.md)._

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
