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
- **Gap 2 (observability wiring, condition 6)** — `polaris_web/observability.py`
  (v9.27 / Tier 8 #11) is now actually wired: `/api/metrics` route added
  next to `/api/health`; `_metrics_after_request` calls `record_request()`
  + `record_error()` on 5xx; `security.py:authenticate` calls
  `record_auth_failure(kind='password')` on bad-credentials path;
  `webauthn_assert_finish` calls `record_auth_failure(kind='webauthn')`
  on both invalid-credential and invalid-assertion branches;
  `_check_and_record_duress` calls `record_duress_event()` after the
  silent DB record. **The duress counter being non-zero IS THE
  ANTI-COERCION ALARM.** Per T8#11: an unobservable duress signal is
  the coercion-cover failure mode (R11-5 becomes decorative).
- **Gap 3 (MTTR back-fill + parser fix, condition 4)** — Three honest
  resolutions back-filled with provenance (treasury rebalance 04:09,
  Mycelium swarm wake 03:31, security_watcher CSP regex fix 03:24, all
  per `journal/2026-05-17.md`). `_parse_iso` helper added to
  `polaris-swarm-mttr.sh` to handle the historical "+00:00Z" double-
  suffix format that was silently rejecting every early-ledger entry —
  the slope computation was inoperative for 12 days. Trend slope now
  computes: **-1.72h/ship (negative = MTTR decreasing = loop earning)**.
  v9.30 binding clause passes.
- **Gap 4 (mttr.sh version regex, prep)** — Regex anchored to
  `^__version__` start-of-line to skip the docstring example
  `POLARIS_VERSION = '9.05'` literal in `__version__.py:9-10`. Script
  now correctly reports current version.
- **Gap 5a/5b (chaos test, condition 3)** — `libpq` linked (`brew link
  --force libpq`) so `psql` is on PATH. This exposed a hidden fail-open
  in `polaris-recover-admin.sh`: `run_psql` used `2>/dev/null` at three
  call sites, so `set -e` silently exited on DB-unreachable BEFORE any
  refusal message was emitted to the operator — fail-open-in-disguise
  (script crash treated by caller as "no result, retry" rather than
  "REFUSE"). Fixed: `run_psql` wrapped to capture psql exit code,
  emit loud operator-readable refusal, then exit `EXIT_DB`. **Real
  security defect caught by the chaos test the moment psql became
  available** — exactly the posture the v9.27 Anti-Architect
  constraint targeted. Chaos test now 3/3 fail-safe.
- **Conditions 1, 5, 7** — C1–C10 coherence reported by ai-coherence
  (rollup of 100+ structural invariants); v9.30 binding clause passing
  per Gap 3 work; `__version__` literal bumped 9.30 → 9.31.

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

## v9.23 — 2026-05-15 (BIG MISSION composite I · 12-item Architect + Anti-Architect debate · Pattern #20 18th instance)

VANTA: *"BIG MISSION. (Architect + Antiarchitect Agents discusses each one
... Vanta Sanctum authorized."* First BIG MISSION ship; 12 items across
Critical/High/Medium tiers. **Critical:** WebAuthn rollout helper +
operator runbook (`scripts/polaris-set-webauthn-deadline.sh` +
`docs/operator/WEBAUTHN-ROLLOUT.md`; audit confirmed v8.97 infrastructure
100% complete — no rebuild); cognitive-layer threat model
(`DEVNOTES/threat-model-cognitive.md` covers 5 threat classes T-CL-1..T-CL-5);
polaris-restore.sh hardened with `--verify-schema-version` flag +
`EXIT_SCHEMA_MISMATCH=10`. **High:** ONE TLA+ demonstrator for C3 (Anti-
Architect refused broad scope per AP7); single-region DR runbook (Anti-
Architect refused multi-region per v9.16 RESERVED-NOT-PLANNED clause);
RASP rule catalog (12 rules; IMPLEMENTED vs GAP labels); RED-TEAM-SCOPE.md
(agent ships spec; operator commissions exercise per AP8 refusal of
red-team simulation). **Medium:** QuantumObserverBinding deferral-rationale
doc; token-volume loadtest script with honest accounting; QUICKSTART.md +
ARCHITECTURE-OVERVIEW.md onboarding docs; polaris-cron-install.sh wiring
existing v8.84/v8.87/v9.07 scripts (not new archival framework);
top-level CONTRIBUTING.md + SECURITY.md. 13 new artifacts. TestWave23V923
(32 invariants). Pattern #20 Constitutional Discipline 18th instance.

## v9.22 — 2026-05-15 (Landing-page repair · C4-C9 honest accounting · 8 broken /docs/*.md links → GitHub URLs)

VANTA caught two real bugs on the public landing page. Architect's
instinct: add C4-C9 as more claim cards. Anti-Architect refused
(AP3: would convert 4-card highlight into 10-card feature list).
Joint: keep 4 cards + add one paragraph naming C4-C9 + link to
MISSION.md. 8 broken `/docs/*.md` links rewritten to GitHub URLs (same
pattern as v9.21 demo fix; all 8 target files verified present).
Landing page now tells the truth.

_Per CHANGELOG.md convention (last 10 ships only): v9.21 → v9.15 trimmed
2026-05-17 with the v9.31 ship. Full byte-identical history at
[archive/CHANGELOG-FULL.md](archive/CHANGELOG-FULL.md)._

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
