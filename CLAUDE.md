# CLAUDE.md — agent runbook for Polaris

This file is the **load-bearing runbook** for an agent (Claude) working
on Polaris in a fresh session. Per BIG MISSION Sanctum 2026-05-16
Tier 4 #14, this file was trimmed from 672 lines to a compact set of
invariants, predicates, and loop wiring. Narrative state-map detail
moved to its existing homes (see pointers below); nothing was created
that didn't already exist.

If you are not Claude, this is still a developer onboarding doc — it
just talks to itself.

---

## Invariants (C1–C10)

The constitution lives in [`MISSION.md`](MISSION.md). Read it once at
session start. Ten hard constraints, all enforced at the database
level (trigger / partial unique index / CHECK constraint), not at the
policy level:

- **C1** audit-of-record (9 schema instances + 3 filesystem instances; 12 total)
- **C2** zero-knowledge (verification graph not reconstructable)
- **C3** one identity per person (partial unique index)
- **C4** atomic failed-login counter (no TOCTOU)
- **C5** CSP forbids inline scripts (no `unsafe-inline`)
- **C6** server-side disclosure enforcement
- **C7** no hardcoded cryptography (algorithm in `CryptographicAlgorithm` table)
- **C8** bounded result sets on `/api/atlas/*`
- **C9** concurrency hazards tested with real threading
- **C10** identity is not money

**Vocation** ([`MISSION.md` §Vocation](MISSION.md#vocation)) sits above
C1–C10: anti-coercion. Changes that strengthen anti-coercion are
welcomed; changes toward surveillance / centralized aggregation /
unbounded retention are refused on sight.

---

## Predicates (load-bearing falsifiable claims)

The 33 commander ants' predicates are enumerated at
[`meta/ant-predicates.md`](meta/ant-predicates.md) (v9.24 BIG MISSION T1#2).
5 are flagged DEPRECATION_CANDIDATE; v9.25 either rewrites them as
falsifiable or deletes the ant.

The 5 cognitive-layer threats are at
[`DEVNOTES/threat-model-cognitive.md`](DEVNOTES/threat-model-cognitive.md)
(v9.23 BIG MISSION Critical #2): T-CL-1..T-CL-5 covering pheromone
poisoning, watcher compromise, Sanctum prompt injection, foresight
weaponization, persona spoofing.

The C3 demonstrator TLA+ spec is at
[`meta/tla/c3-one-active-token.tla`](meta/tla/c3-one-active-token.tla)
(v9.23 BIG MISSION High #1; demonstrator only, not maintained
verification infrastructure).

---

## Loop wiring (how an agent session works)

```bash
# Single-command session prime — replaces the four-step ceremony
./scripts/ai-prime.sh
```

Returns an ≤80-line primer: mission state, top moves, recent journal,
recently modified files, suggested next.

**Read first:**
- [`MISSION.md`](MISSION.md) — the constitution + v2 done-list
- [`ROADMAP.md`](ROADMAP.md) — prioritized backlog
- [`meta/sanctum-index.md`](meta/sanctum-index.md) — recent strategic decisions

**Per-task scripts:**

```bash
./scripts/ai-test.sh                       # full Python suite (wraps env+redis)
./scripts/ai-test.sh quick                 # skip slow concurrency/property tests
./scripts/ai-link-check.sh --ci            # cross-ref resolution
./scripts/ai-meta.sh                       # cognitive-layer self-audit
./scripts/ai-coherence.sh                  # cross-layer consistency
./scripts/ai-done.sh                       # pre-ship 15-check gate (v9.24 adds findings-gate; v9.28 adds CM-enforce)
```

**Capture decisions during the session:**

```bash
./scripts/ai-journal.sh start "what I'm trying to do"
./scripts/ai-journal.sh decision "kept FOR UPDATE; SERIALIZABLE needs retry logic"
./scripts/ai-journal.sh learning "ca.algorithm_name doesn't exist; column is ca.name"
```

**For MEDIUM/HIGH-risk strategic decisions — DO NOT present ad-hoc in chat.
Enter the Sanctum:**

```bash
./scripts/ai-sanctum.sh open <topic>
./scripts/ai-sanctum.sh close <topic> --position A --decision ...
./scripts/ai-sanctum.sh --voice               # full protocol spec
```

Risk classes in [`meta/autonomy-architecture.md`](meta/autonomy-architecture.md).
Architect/Anti-Architect 8-pattern catalog in [`meta/architect.md`](meta/architect.md).

**Ship sequence (v9.27 cold-read closure — T7#8).** Every ship — LOW
or otherwise — runs these in order. Missing a step is a known drift
class the cold-read walkthrough surfaced. Class-shaped, not instance:

1. **Pick risk class** (LOW autonomous / MEDIUM proposal / HIGH Sanctum).
   See `meta/autonomy-architecture.md`.
2. **For HIGH:** open Sanctum first (`scripts/ai-sanctum.sh open <topic>`).
3. **Code change:** edit `polaris_*` source / scripts / docs.
4. **Tests:** add to `polaris_web/test_structural_invariants.py` under a
   NEW class named `TestWaveNN_VNNN` (one class per ship version; never
   add to a prior ship's class — the v8.20 AoR discipline applies).
5. **File reads in tests:** always use `self._read('relative/path')` +
   `self.ROOT` join (the existing helper convention). Never absolute paths.
6. **Bump version:** edit `polaris_web/__version__.py` to `X.Y` matching
   the ship's intended version. Every ship gets its own version; no
   "skipping" or "batching" multiple changes into one version.
7. **CHANGELOG entry:** prepend a `## vX.Y — DATE (subtitle)` block at
   the top of `CHANGELOG.md`. Last 10 ships only stay in `CHANGELOG.md`;
   older entries already in `archive/CHANGELOG-FULL.md` are byte-frozen
   (v8.20 AoR). Markers per shipping convention (`scope`, `ship_marker`,
   `vocation`, `pattern20_instance`) read by tests.
8. **Journal entry:** append `- **decision** HH:MM — vX.Y SHIPPED — ...`
   to `journal/YYYY-MM-DD.md`. Every ship leaves a journal trace.
9. **Scorecard:** `bash scripts/polaris-swarm-scorecard.sh append X.Y`.
   Auto-classifies TP/FP. Skipping breaks the load-bearing
   `escape_rate_trailing_10ships` metric (v9.25).
10. **MTTR (if findings raised/resolved):** `polaris-swarm-mttr.sh raise`
    when a finding fires; `polaris-swarm-mttr.sh resolve <fid>` when a fix
    ships. v9.30 binding clause depends on this; silently skipping makes
    the cut-deeper clause fire on missing data.
11. **Sanctum index** (if Sanctum opened): add a `- **YYYY-MM-DD** — [topic]
    — **DECIDED + SHIPPED** ...` entry at the top of `meta/sanctum-index.md`.
12. **Pre-ship gate:** `bash scripts/ai-done.sh`. Must report READY.
    If `--strict` is on, exits non-zero on any fail. Step 14 blocks on
    HYDRA ALERT findings.
13. **Scope-check:** the pre-commit hook checks narrative/core ratio.
    If it fails, EITHER trim narrative OR commit the rebase via
    `--rebase-baseline` AFTER a Sanctum decision documents the intentional
    growth. Never silent-rebase.
14. **Definition of shipped:** every test added in step 4 passes; every
    pre-ship gate in step 12 passes; the work-item closes against its
    stated spec. If any of these is false, the ship is not shipped.

**The 10 cold-read interventions are now captured as steps 4-14 above.
Two remaining honestly-named "accept it never will" items:**

- The actual cold-read by an external party (only an operator can
  commission this — see T7#9 decision).
- Spec-completeness on every contained feature: a fresh agent might
  still over- or under-interpret the spec; no runbook rule eliminates
  this without becoming AP3 (instance-level rule for every possible
  spec ambiguity).

**Pre-ship gates that enforce, not suggest:**

- `scripts/ai-done.sh` — 15 checks; step 14 (v9.24) blocks ship on HYDRA
  ALERT-level finding. Override = `POLARIS_ALLOW_ALERT_SHIPS=1`
  (audit-trail line printed).
- `scripts/pre-commit-scope-check.sh` (v9.24) — refuses commits where
  narrative-mass-to-core ratio exceeds baseline ceiling. Override =
  `POLARIS_ALLOW_SCOPE_OVERRUN=1`.

**Full ai-* + polaris-* script index** (canonical list via
`./scripts/ai-help.sh`; one-line shorthand below for the META-check):

- `ai-adversary.sh ai-anti-architect.sh ai-architect.sh ai-authz-audit.sh ai-bootstrap.sh ai-brain-map.sh ai-cache-bust.sh ai-coherence.sh ai-context-digest.sh ai-coverage.sh ai-dashboard.sh ai-done.sh ai-foresight.sh ai-help.sh ai-hydra.sh ai-impact.sh ai-journal.sh ai-lattice.sh ai-link-check.sh ai-loop-check.sh ai-meta.sh ai-mission.sh ai-pattern.sh ai-prime.sh ai-propose.sh ai-recall.sh ai-reflect.sh ai-sanctum.sh ai-snapshot.sh ai-status.sh ai-swarm-bloom.sh ai-swarm-health.sh ai-swarm-map.sh ai-swarm-validate.sh ai-test-counts.sh ai-test.sh ai-treasury-report.sh ai-watcher-coverage.sh ai-where.sh`
- `polaris-ant-ranking.sh polaris-archive.sh polaris-backup.sh polaris-chaos-test.sh polaris-concurrency-harness.sh polaris-create-operator.sh polaris-cron-install.sh polaris-ct-monitor.sh polaris-deploy.sh polaris-doctor.sh polaris-generate-recovery-code.sh polaris-generate-secrets.sh polaris-idempotency-test.sh polaris-load-test.sh polaris-loadtest-tokens.sh polaris-migrate.sh polaris-oracle-runner.sh polaris-pheromone-archive.sh polaris-pheromone-purge.sh polaris-pqc-status.sh polaris-purge.sh polaris-recover-admin.sh polaris-restore.sh polaris-rotate-logs.sh polaris-rotate-secret.sh polaris-sanctum-scorecard.sh polaris-sanctum-status.sh polaris-set-webauthn-deadline.sh polaris-swarm-killtest.sh polaris-swarm-mttr.sh polaris-swarm-scorecard.sh pre-commit-scope-check.sh`

---

## Where does X live? (quick-ref)

| Question | File |
|---|---|
| What is Polaris? What is it NOT? | [`MISSION.md`](MISSION.md) |
| What's next? Backlog by risk class? | [`ROADMAP.md`](ROADMAP.md) (active) / [`docs/BACKLOG.md`](docs/BACKLOG.md) (unsorted) |
| What just shipped? Last 10 ships? | [`CHANGELOG.md`](CHANGELOG.md) |
| Full per-ship history (v1.0 → present) | [`archive/CHANGELOG-FULL.md`](archive/CHANGELOG-FULL.md) |
| What did we decide on day Y? | [`journal/<date>.md`](journal/) (index at `journal/INDEX.md`) |
| Why was a strategic Decision made? | [`sanctum/<date>-<topic>.md`](sanctum/) (index at `meta/sanctum-index.md`) |
| Why this proposal exists? | [`proposals/<R-id>-<topic>.md`](proposals/) |
| Cross-cutting principle | [`DEVNOTES/<name>.md`](DEVNOTES/) |
| How does ship X work? | [`DEVNOTES/ships/<short-name>.md`](DEVNOTES/ships/) |
| How do I do X (add Flask route, fix race, etc.)? | [`patterns/<task>.md`](patterns/) |
| Where everything lives, system-wide | [`docs/reference/SYSTEM-MAP.md`](docs/reference/SYSTEM-MAP.md) |
| Conventions (naming, structure) | [`docs/CONVENTIONS.md`](docs/CONVENTIONS.md) |
| Architectural principles | [`docs/story/PRINCIPLES.md`](docs/story/PRINCIPLES.md) |
| The thesis (one-page external pitch) | [`docs/THESIS.md`](docs/THESIS.md) (v9.24) |
| Onboarding for a new operator | [`docs/QUICKSTART.md`](docs/QUICKSTART.md) (v9.23) |
| Architecture brief for an engineer | [`docs/ARCHITECTURE-OVERVIEW.md`](docs/ARCHITECTURE-OVERVIEW.md) (v9.23) |
| Schema / procedures / triggers | [`polaris_sql/01_schema.sql`](polaris_sql/01_schema.sql) / `05_procedures.sql` / `06_triggers.sql` |
| Flask app / templates / CSS | [`polaris_web/app.py`](polaris_web/app.py) / `templates/` / `static/` |
| Rust ZK crate | [`polaris_zk/src/lib.rs`](polaris_zk/src/lib.rs) + `polaris_zk/src/main.rs` |
| What scripts can I run? | `./scripts/ai-help.sh` or `ls scripts/` |
| Operator/architect reference docs | [`docs/README.md`](docs/README.md) (indexed) |

**Routing the user's request:**

| User mentions | Read first | Edit |
|---|---|---|
| "concurrency" | [`DEVNOTES/concurrency.md`](DEVNOTES/concurrency.md) | `05_procedures.sql`, `security.py` |
| "atlas slow / 2M / scale" | [`docs/reference/SCALING.md`](docs/reference/SCALING.md), [`DEVNOTES/atlas-scaling.md`](DEVNOTES/atlas-scaling.md) | `11_atlas.sql`, `app.py /api/atlas/*` |
| "globe / map / reticle" | `atlas-globe.js` | `atlas-globe.js`, `atlas.html`, `polaris.css` |
| "schema / table / column" | `01_schema.sql` | `01_schema.sql` + `04_data.sql` |
| "test / regression" | `test_app.py` top | `test_app.py` |
| "launcher / stop won't work" | `polaris_mac_launch.sh` top comment | `polaris_mac_launch.sh` |
| "login broken / locked" | `security.py::authenticate()` | `UPDATE AppUser SET locked_until=NULL, failed_login_count=0` |
| "CSP error / inline script" | `security.py::secure_headers()` | `security.py` — don't weaken CSP; externalize to `static/*.js` |
| "page is slow" | `app.py` route + `EXPLAIN ANALYZE` | typically add LIMIT, index, refactor |
| "post-quantum signing not working" | [`polaris_web/pqc_signing.py`](polaris_web/pqc_signing.py) (v9.24) | check `POLARIS_USE_REAL_PQC` flag + liboqs install |

---

## Current version

**v9.35** (2026-05-17). 45 ships in v9.x. 33 commander ants. 9 HYDRA
watchers + CM. 11 manifest legions + 1 reserved. 9 soldier classes (8
workers + 1 priest). 6 citizens. Treasury (Denarius) ledger.

**Freeze line at v9.31** (the terminus). Post-v9.31 work is bounded to
(a) hardening, (b) measurement, (c) thesis cold-read evidence per
MISSION.md §"From v9.32 forward". v9.32 wired hookify; v9.33 added
Playwright E2E scaffold; v9.34 closed swarm cron-cadence + priest-tier
datetime crash; v9.35 fixed HYDRA watchers' hardcoded-port-2223 bug
that had made live-app probes permanently inconclusive.

For the per-ship history of v9.x: see [`CHANGELOG.md`](CHANGELOG.md)
(curated last 10) or [`archive/CHANGELOG-FULL.md`](archive/CHANGELOG-FULL.md)
(full).

---

## Pre-known gotchas

These have bitten me. Skip the rediscovery cost.

1. **`reload_sample_data()` operates on whatever DB `POLARIS_DB_NAME`
   says.** Pre-v6 it was hardcoded to `polaris_test`, which silently
   wiped the wrong database. Confirm before tests.

2. **Postgres restart between bash turns:** `pg_ctlcluster 16 main start`.
   Wait ~5s before reconnecting.

3. **Test admin locks itself out** after auth tests. Unlock:
   `UPDATE AppUser SET locked_until=NULL, failed_login_count=0`.

4. **`stat -f`** means filesystem stats on Linux but BSD format string on
   macOS. Fixed in v5.

5. **`script-src 'self'`** blocks inline `<script>` and inline
   event-handlers. The only legitimate inline `<script>` is the
   `application/json` data-island at `atlas.html:157`. Add new JS as
   external `static/*.js` loaded with `defer`. Never add `'unsafe-inline'`.

6. **Playwright `wait_for_load_state("networkidle")`** hangs because
   heartbeat runs every 10s. Use `wait_until="domcontentloaded"` +
   explicit `wait_for_timeout`.

7. **Postgres docker volume drift:** password mismatch → all auth fails.
   Launcher's `docker_compose_up_with_heal` auto-detects + wipes volume.
   Outside launcher: `docker compose down -v && docker compose up`.

8. **`ca.algorithm_name` doesn't exist.** Column is `ca.name`.

9. **`{{ ... }}` in HTML comments breaks Jinja.** Use `{# … #}`.

10. **Two unique-pattern conventions exist** (`uq_*` and `idx_*`). Match
    the surrounding convention; don't add a third.

11. **"Localhost refused to connect" after navigation** had two roots
    fixed across v8.51 + v8.55: launcher stale-heartbeat threshold +
    `pagehide`/`beforeunload` listeners. See pre-v9.24 detail at
    `archive/CHANGELOG-FULL.md` if needed.

12. **`webauthn_required_after` migration must apply at docker init.**
    v9.18 fixed `docker-init.sh` to loop through migrations/*.up.sql
    after schema load. v9.17 fixed Dockerfile to COPY
    `webauthn_auth.py` + `__version__.py`. If login returns 500 with
    "column does not exist", the migration didn't run.

13. **Demo template hallucinated `uc1_issue_token`** + `uc2_verify_token`
    pre-v9.21 — these procedures have never existed. Real ones:
    `uc1_issue_and_activate`, `uc4_activate_reserve`, `uc8_revoke_token`.
    Verification flow is a direct INSERT into `VerificationEvent`.

14. **Post-quantum signing (`POLARIS_USE_REAL_PQC=1`) requires liboqs**
    native library + `pip install oqs`. Flag-off default means
    `token_value` is a deterministic string. v9.24 ships the integration
    scaffold; activation is operator-side. Check
    `scripts/polaris-pqc-status.sh`.

---

## Spinning up to test

```bash
# 1. pg up
pg_ctlcluster 16 main start 2>&1 | tail -2

# 2. Test DB exists?
su postgres -c "psql -d polaris_test -c '\df atlas_*'" | head

# 3. Reload schema if stale
cd polaris_sql
su postgres -c "dropdb --if-exists polaris_test && createdb polaris_test"
su postgres -c "psql -d polaris_test -v ON_ERROR_STOP=1 -f $PWD/00_load_all.sql"

# 4. Env
unset PGPORT
export POLARIS_DB_HOST=localhost POLARIS_DB_NAME=polaris_test \
    POLARIS_DB_USER=polaris_app POLARIS_DB_PASSWORD=polaris_dev_password \
    POLARIS_PORT=2222 POLARIS_SECRET_KEY=test-secret \
    POLARIS_STATE_DIR=/tmp/polaris-state
mkdir -p /tmp/polaris-state

# 5. Start
cd polaris_web
setsid nohup gunicorn --config gunicorn.conf.py app:app > /tmp/polaris_app.log 2>&1 < /dev/null &

# 6. Wait
for i in $(seq 1 15); do
  curl -fsS -m 1 http://localhost:2222/login >/dev/null 2>&1 && break
  sleep 0.5
done
```

Or just `./scripts/ai-bootstrap.sh`.

---

## Quality bar (VANTA's standing instructions)

Read [`DEVNOTES/style.md`](DEVNOTES/style.md). Summary:

- No em-dashes in human-readable prose.
- Declarative style, no filler.
- Game-theory framing where appropriate.
- Intelligence-report aesthetic in visuals (navy/gold).
- "Holy shit, that's done" — no workarounds, no tabling.
- When drifting toward cosmic-significance framing ("larping"), name
  the pattern and back off. The Anti-Architect persona
  ([`meta/architect.md`](meta/architect.md) §"The Architect's shadow"
  + 8-pattern catalog) is the formal version of this discipline.
- Banking / payments tied to the identity token: see Architecture #2
  in the prior thread; default answer is build it as a separate repo
  consuming Polaris over HTTP.

---

## Post-v2 default posture (v8.31 + revoked v8.74 → reaffirmed v9.16)

Polaris reached steady-state 2026-05-12 (Sanctum
[`sanctum/2026-05-12-post-v2-steady-state-declaration.md`](sanctum/2026-05-12-post-v2-steady-state-declaration.md)).
The agent's default posture for ambiguous requests is
**decline-and-surface**:

- New mission scope → DO NOT silently expand. Explain why it crosses
  steady-state. Name the trigger needed. Wait for VANTA.
- LOW-risk maintenance (drift, doc gaps, soft signals) → ship under
  standard autonomous rules.
- The Architect surfaces drift, not opportunities.
- The contract is operator-revocable: VANTA may name a trigger or
  open a new arc at any time. The constraint is on the agent.

See [`MISSION.md` §"Post-v2 strategic moment"](MISSION.md) for the
constitutional clause.

**v8.74 / "boil the ocean" heavy-production override:** when VANTA
explicitly invokes "boil the ocean" or "Vanta Sanctum authorized" or
similar heavy-production directive, the steady-state contract is
overridden for that session. Ships during such directives are HIGH-
composite and must record the authorization quote in the Sanctum file.

---

*Per BIG MISSION Sanctum 2026-05-16, Tier 4 #14. CLAUDE.md trimmed
from 672 lines to ≤250. Detail moved (not copied) to the existing
homes shown in the Where-does-X-live table above. Per Anti-Architect
joint resolution: net delete, no new narrative file created.*
