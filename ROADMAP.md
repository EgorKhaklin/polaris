# ROADMAP.md — where Polaris is going

<!-- ============================================================ -->
<!-- LIVING BACKLOG. Newest priorities first. Continuously updated -->
<!-- each session (per the 2026-06-03 heavy-production directive:  -->
<!-- "create a future roadmap ... constantly updated with ideas"). -->
<!-- Add new ideas here as they arise; move to the prioritized     -->
<!-- backlog below when adopted as an R-id; never delete shipped   -->
<!-- history (audit-of-record).                                    -->
<!-- ============================================================ -->

## 🔭 OPEN NOW — living backlog (updated 2026-06-03, v9.48)

Tagging: `effort(XS/S/M/L) · value · risk · freeze-category`. The
v9.31 freeze permits hardening / measurement / cold-read-evidence;
a new-arc item needs a Sanctum naming an external trigger.

**Flagged for VANTA (decision required):**

- **[VANTA] THESIS v9.40 terminus has passed unactioned.** MISSION.md:70
  says the strong "agent-maintainable production identity system" claim
  *retires permanently* if no external cold-read occurs by v9.40. We are
  at v9.45 with only the system's own walkthrough, never an external one,
  yet `docs/THESIS.md` still uses the softer conditional "RETIRED *until*
  evidence supports it." Leaving the softer wording past the deadline is
  itself the dishonesty the project's discipline forbids. Two honest moves,
  both VANTA's call: (a) reflect the permanent terminus ("has not been
  independently validated") + pin it with an invariant, or (b) amend the
  deadline via Sanctum + freeze-amendment-protocol. `S · high · MEDIUM · cold-read-evidence`

**Next ships (agent-actionable under heavy-production authorization):**

1. **[PARTIAL ✅ v9.46] Wire suites into CI.** Done: the v9.44 ZK two-witness
   differential + witness2 self-tests + pure HYDRA suites now gate CI, and
   `pytest` is in `requirements.txt`. **Still open:** wire `test_app.py` +
   `test_cli.py` (DB-backed) once confirmed green against the CI sample DB —
   deferred because they are not verifiable from the local env (no psycopg2).
   `S · high · LOW · measurement`
2. **[PARTIAL ✅ v9.47] PQC lone verifier** — recorded as an explicit two-witness
   ABSTAIN; the docstring overclaim (flag-on enables real-signature issuance)
   was corrected (it is an integration island: `app.py` never imports it,
   `uc1_issue` never calls `sign()`). **Still open (deferred):** a full
   independent ML-DSA-65 second witness — premature while the verdict is OFF by
   default and unwired; revisit when the path goes live. `L · medium · MEDIUM · hardening`
3. **Foresight experiment is in limbo — cut the knot.** The v9.12 deal
   (≥50% candidate acceptance over 6 monthly briefs, else sunset) can neither
   graduate nor sunset: 20 briefs but all in one month, cadence stalled.
   Either wire `ai-foresight.sh` into a real monthly cron, or open the removal
   Sanctum and retire the surface. `M · medium · MEDIUM · measurement`
4. **ZK anonymity set is demo-scale (`TREE_DEPTH=4`, ≤16 leaves).** Re-run
   the circuit setup at `TREE_DEPTH=14` (16,384 leaves) for a realistic set;
   the second witness already generalizes. `L · medium · MEDIUM · hardening`
5. **Apparatus-reduction Sanctum** — cut-deeper signal firing since v9.29
   (core/apparatus ratio 0.29). Walk ACTIVE sanctums, transition those now
   embodied as structural invariants to SUPERSEDED (files stay; only
   classification changes). Own Sanctum, execution-intent present. `M · medium · HIGH · measurement`
6. **PQC-posture audit** (FS-5B5F30C9) — audit Polaris against NIST PQC
   migration timelines; surface gaps. `S · low · LOW · cold-read-evidence`
7. **R13-3 / R13-4 Mycelium bloom + deliberation** (only if Arc E is still
   open) — additive brain-map bloom overlay + deliberation threshold; unblocks
   the R13-5 HYDRA-vs-Mycelium decision. `M · medium · LOW · new-arc`

**Recently shipped (this session, 2026-06-03):** v9.44 ZK two-witness (Glass
bounded-integration); v9.45 secret-leak gitignore fix + foresight integrity;
v9.46 CI wiring (ZK two-witness + HYDRA suites gate CI); v9.47 PQC two-witness
ABSTAIN + docstring honesty; v9.48 ai-swarm-validate honest header. Six commits;
gate READY throughout. **Next tier needs VANTA's call** — see the "Flagged for
VANTA" item above (THESIS terminus) plus the foresight keep/kill (#3) and
apparatus-reduction (#5) decisions.

---

## Layer-1 candidates (per S2 Position C, 2026-05-15)

The v9.04 → v9.08 phase invested heavily in Layer-2/3 (cognitive
substrate + tools). Per the [cognitive-layer-ratio Sanctum](sanctum/2026-05-15-cognitive-layer-ratio.md)
Position C, v9.10+ deliberately surfaces Layer-1 advances. This
section is the operator-facing list of next Layer-1 candidates;
the Architect's brief reads from it when scoring next moves.

**Cadence rule**: at least 1 Layer-1 candidate must ship per 5
composite ships, OR an explicit Sanctum must record why the cycle
remained Layer-2/3-focused. Tracked via the
`scripts/ai-architect.sh` "Layer ratio (last 5 ships)" line in
`emit_outlook` (added v9.10 alongside this section).

**Current candidates (operator-tunable):**

1. **L1-1 — Pheromone rotation SQL self-tests** (✅ shipped v9.10)
   The v9.07 Pheromone rotation framework has end-to-end drill but
   no SQL-level structural enforcement. Section S in
   `polaris_sql/08_tests.sql` adds 10 DO-block invariants
   (trigger-rejection paths + GUC carve-out + checkpoint
   append-only + CHECK constraints + admin-role validation).

2. **L1-2 — Arc B Phase 2.5 multi-instance scaling completion**
   (gated on production-scale data; could be opened defensively).
   Foundations shipped v8.83 (pgbouncer + scaling recipes); the
   read-replica + Redis-cluster + PostGIS Phase 2 work is deferred
   per OPERATIONS.md "Scaling" section. Could be opened defensively
   under a Sanctum to surface the trade-offs.

3. **L1-3 — UC-13 (TBD)** — a new use case addressing a real-world
   identity-token gap that v8.97 WebAuthn didn't cover. Explicit
   operator trigger required (no autonomous arc-opening).
   Architect-suggested neighborhood: cross-jurisdictional trust
   federation enrollment, attestation-chain visualization for
   Census.


## Auto-promoted action candidates (v9.11+)

Per the v9.11 ship (Chapter X — closing the observe→correlate→act loop),
HYDRA's ActionQueue auto-promotes top-N actionable findings into this
section. Each item carries a stable ID derived from its title; re-runs
of the promotion are idempotent (no duplicates).

**Operator workflow:**
1. Triage these candidates during the next Architect brief review.
2. Promote a candidate to a real R-id (in the prioritized backlog
   below) when adopting it as work.
3. Remove a candidate when explicitly declining (write a one-line
   "declined: <reason>" comment so re-promotion of the same finding
   doesn't re-add it; see the "decline marker" convention below).

**Decline marker convention:** to permanently decline a candidate
without removing the entry, prefix its line with `- ~~AP-XXXXXXXX~~`
(strikethrough) plus a `<!-- declined: reason -->` comment. The
auto-promotion logic detects struck-through entries and does NOT
re-promote even if the underlying finding recurs.

**Promotion rules (conservative by design):**
- Only LOW + MEDIUM risk promote autonomously; HIGH still requires Sanctum
- Correlations (multi-watcher consensus) always promote
- Singleton findings only promote if severity = alert
- Idempotent: re-running adds nothing if the action ID is present


## Foresight candidates (v9.12+)

Per the v9.12 ship (Position B foresight surface),
`bash scripts/ai-foresight.sh --promote` writes top-N foresight
candidates from monthly briefs into this section. Each item carries a
stable ID derived from its title; re-runs are idempotent.

**Operator workflow:**
1. Read the brief at `journal/foresight/YYYY-MM-DD.md` first.
2. Triage candidates here: promote to a real R-id when adopting; mark
   with strikethrough + `<!-- declined: reason -->` when declining.
3. The empirical-graduation rule (50% acceptance over 6 monthly briefs)
   gates whether the foresight surface earns the right to expand into a
   subsystem. Below threshold + 6 briefs in: sunset warning fires.

**Decline marker convention** (same shape as AP-XXXXXXXX):
prefix the line with `- ~~FS-XXXXXXXX~~ <!-- declined: reason -->` to
prevent re-promotion of the same finding even if it surfaces again.

**Promotion rules:**
- LOW + MEDIUM only auto-promote; HIGH still requires Sanctum
- Vocation-alignment hint is REQUIRED (not advisory)
- Idempotent: re-running adds nothing if the FS-ID is present

---

This file is the prioritized backlog. Each item has:

- **Mission link** — which item in `MISSION.md`'s done-list this
  advances (or which constraint it strengthens)
- **Risk class** — `LOW` (autonomous-eligible), `MEDIUM` (propose-and-
  wait), `HIGH` (explicit human approval required)
- **Effort estimate** — rough magnitude
- **Acceptance criteria** — how we know it's done

`scripts/ai-propose.sh` reads this file. `scripts/ai-status.sh` checks
which items have advanced.

---

- ~~**AP-E8FCC9A5**~~ (MEDIUM/one-day, score=7.0, source=finding: ant_colony) — Investigate: Cannot reach Mycelium swarm (DB offline) <!-- declined: dev-environment artifact (local DB offline / psycopg2 not in venv per the session-start gotcha), not durable mission work. Triaged v9.46. -->
  - rationale: ant_colony_watcher: PheromoneReader returned db_offline status: no DB connection (psycopg2 missing or DB unreachable). The swarm runtime is not observable from this watcher's vantage. Verify Postgr...
  - constraints touched: (none cited)
  - vocation: anti-coercion (advances identity inviolability)
  - first promoted: 2026-05-15

- ~~**AP-4866529A**~~ (MEDIUM/one-day, score=7.0, source=finding: cognitive) — Investigate: Sanctum index drift <!-- declined: expected gap, not a defect. 67 sanctum files / 65 index entries (v9.46): non-strategic Sanctum files are intentionally not indexed; the index is maintained per the ship runbook. -->
  - rationale: cognitive_watcher: sanctum/ has 49 session file(s) but meta/sanctum-index.md has 48 entry/entries. Run `ai-sanctum.sh close` to re-index, or inspect manually.
  - constraints touched: (none cited)
  - vocation: anti-coercion (operational reliability serves availability of identity)
  - first promoted: 2026-05-15

- ~~**AP-BB688443**~~ (MEDIUM/one-day, score=7.0, source=finding: schema) — Investigate: psycopg2 not importable <!-- declined: dev-environment artifact (psycopg2 not in the watcher's venv); an install step, not mission work. Triaged v9.46. -->
  - rationale: schema_watcher: SchemaWatcher requires psycopg2. Install it in the same venv the Flask app uses.
  - constraints touched: (none cited)
  - vocation: unclear (operator triage; AP5 candidate)
  - first promoted: 2026-05-15

- ~~**AP-3ACE3236**~~ (LOW/one-shot, score=2.0, source=correlation: performance, security) — Investigate cross-watcher correlation: runtime:health <!-- declined: low-severity (info) dev-runtime correlation, same DB-offline root as the trio above. Triaged v9.46. -->
  - rationale: 2 watcher(s) (performance, security) independently surfaced findings on node_id='runtime:health' with combined severity info. Multi-watcher consensus is high-confidence signal.
  - constraints touched: (none cited)
  - vocation: anti-coercion (operational reliability serves availability of identity)
  - first promoted: 2026-05-15

- **FS-5B5F30C9** (LOW/one-shot, source=foresight: §V) — Audit Polaris's posture against external category: "Post-quantum cryptography migration timelines (NIST PQC finalists; deployment milestones
  - rationale: Audit Polaris's posture against external category: "Post-quantum cryptography migration timelines (NIST PQC finalists; deployment milestones)". Surface gaps via adversary_watcher pass.
  - vocation: anti-coercion (defensive scan)
  - first promoted: 2026-05-15

## Polaris-self roadmap (2026-05-14, post-v9.04)

VANTA asked Polaris to scan itself macro-to-micro and produce a gap
roadmap "as if you are Polaris itself". That document is
[`meta/polaris-self-roadmap-2026-05-14.md`](meta/polaris-self-roadmap-2026-05-14.md).

It contains 30 items in 4 waves:

- **Wave 1 (14 items, autonomous-eligible bug-fix carve-out):**
  F5 soldier-exemption violation [A1, HIGH-priority constitutional
  bug surfaced by the scan], MISSION test-count drift [A2], systemic
  ant venv-pollution refactor [B1+B2], requirements.txt creation [C3],
  ai-help inline flags [C4], brief-archive collision detection [D1],
  central PheromoneReader window defaults [D2], in-memory `--diff`
  cleanup [D4], full --save→--diff integration test [E1], CLAUDE.md
  intro/Where-X-lives updates [F1+F3+F4], README v9.04 paragraph
  [F2], HYDRA `--deterministic` flag [I2]. Composite ship as v9.05
  recommended.
- **Wave 2 (8 items, MEDIUM):** brief-archive unification
  Architect↔HYDRA [C1], canonical POLARIS_VERSION source [C5],
  Pheromone rotation Sanctum [D5 — opens a Sanctum], Hypothesis
  tests for v9.04 modules [E2], pre-commit hooks [G1],
  cognitive_watcher channel for journal/hydra/ freshness [H1 — the
  lens watching itself], node_id format documentation + lint [I1],
  90-second Claude onboarding doc [J3].
- **Wave 3 (4 items, Sanctum-class HIGH):** git-or-no-git decision
  [C2], Pheromone rotation framework [D5 implementation], unified
  cognitive-layer dashboard [J1], Treasury 60-day sim review [J4].
- **Wave 4 (ongoing):** since-last-session diff at session start
  [J2], monthly macro-to-micro re-scan.

Wave 1 is autonomous-eligible under standing rules; awaiting
VANTA confirmation to ship as v9.05.

---

## What needs done before it can become a deployable system

VANTA's deployability checklist (2026-05-14) plus
Architect+HYDRA scan additions. The base three lines are the
operator-facing summary; the indented items name the concrete
deferred work each phase carries. Add to this section when a
genuinely new gap is surfaced; never silently delete (the
checklist is itself audit-of-record).

### ✅ Phase 1 — production deployment shipped

Shipped across v8.77 (Arc B Phase 1) → v8.81 (Phase 1.5) →
v8.83/v8.84/v8.87/v8.88 (Phase 2 foundations) → v8.91 (Treasury
rebalance). The system can be deployed to a single Linux host
behind TLS, with secrets handled correctly, structured
monitoring, manifest-verified backup/restore, audit-log
archive+purge, and operator-readable Treasury diagnostics.

- **TLS** via Caddy + Let's Encrypt auto-issuance (G27)
- **File-mounted secrets** via Docker secrets + `*_FILE` env vars (G28)
- **Structured `/api/health`** with per-component checks (G29)
- **Backup** with manifest-hashed tarball (`polaris-backup.sh`, v8.77)
- **Restore** with verify mode + force-required guard (`polaris-restore.sh`, v8.81)
- **Audit-log archive** export-only, C1-preserving (`polaris-archive.sh`, v8.84)
- **Audit-log purge** under constitutional carve-out + `LifecycleArchiveCheckpoint` (`polaris-purge.sh` + G30/G31, v8.87)
- **pgbouncer** connection pooling foundation (v8.83)
- **PostGIS** schema foundation, optional-dependency (v8.88)
- **Treasury rebalance** under Sanctum-decided Position B (v8.91)
- **Operator runbook** `docs/operator/OPERATIONS.md` (~1000+ lines)
- **Secrets primer** `docs/operator/SECRETS.md`
- **Public landing + demo** at `/` and `/demo` (v8.79)
- **Quick start**: `./scripts/polaris-generate-secrets.sh && export POLARIS_DOMAIN=… && ./scripts/polaris-deploy.sh prod`

### ⬜ Phase 2 — still deferred

VANTA-named:

- ✅ **WebAuthn operator auth** *(shipped v8.97)* — Position B (WebAuthn-MFA) from [sanctum/2026-05-14-webauthn-operator-auth.md](sanctum/2026-05-14-webauthn-operator-auth.md). Migration `2026-05-14-002-operator-webauthn` (first non-example migration; validates the v8.95 framework on a real schema change) adds `OperatorWebauthnCredential` + `AppUser.webauthn_required_after` + 5 new AuthAuditLog event types. `polaris_web/webauthn_auth.py` + 7 new routes in `app.py` handle registration + assertion ceremonies via the Duo Labs `webauthn` package. Login flow modified for grace_period / mfa_required / mfa_overdue states. `scripts/polaris-recover-admin.sh` (second-admin pairing) + `scripts/polaris-generate-recovery-code.sh` (printed mnemonic) handle recovery. `polaris-create-operator.sh` sets 30-day deadline for new admin accounts. threat-model § T-S4 + SECRETS.md § 7 + OPERATIONS.md §Operator authentication document the operator runbook. 10-step end-to-end drill + round-trip enrollment drill green. **Shipped same-day as the v8.96 Sanctum opening; architect's two-ship estimate compressed to one under heavy-production.**
- ✅ **Audit log rotation** *(shipped v8.93)* — `scripts/polaris-rotate-logs.sh` wraps `polaris-archive.sh` + verify + `polaris-purge.sh` in one cron-ready pipeline. 5-year default cutoff per Sanctum §V. Cron recipe in OPERATIONS.md. Greppable exit codes for incident response.
- **Multi-instance scaling completion** — Phase 2.5 work: read replica routing via Caddy/HAProxy; Redis Sentinel or Cluster topology; PostGIS Phase 2 atlas function rewrite (`atlas_clusters_*` / `atlas_points_*` gain a `CASE` branch on `pg_extension` presence; ≥3× benchmark at 10M+ events).

Architect+HYDRA scan additions (2026-05-14):

- ✅ **WAL archiving / point-in-time recovery** *(shipped v8.93)* — pgbackrest paved-path recipe in OPERATIONS.md § "Point-in-time recovery". Full + differential schedule, archive-check cron, restore-to-time procedure. RPO drops from 24h to ~1 minute.
- ✅ **Schema migration framework** *(shipped v8.95)* — Position C (custom polaris-native) from [sanctum/2026-05-14-schema-migration-framework.md](sanctum/2026-05-14-schema-migration-framework.md). `polaris_sql/00_migrations_table.sql` creates the `schema_version` registry (13th audit-of-record); `scripts/polaris-migrate.sh` runs status/up/down/dry-run with SHA-256 tamper detection (exit 6); `polaris_sql/migrations/` holds the hand-written .up + .down SQL pairs; first example migration ships (`2026-05-14-001-idx-checkpoint-recent`). End-to-end drill clean. `docs/operator/OPERATIONS.md` § "Schema migrations (v8.95)" documents the operator workflow. v1.0 production cutover path unblocked.
- ✅ **Prometheus-compatible `/metrics` endpoint** *(shipped v8.93)* — `/metrics` route in app.py via `prometheus_client`. Counters (`polaris_requests_total` by route/method/status; `polaris_verifications_total` by disclosure_level), histograms (`polaris_request_latency_seconds`, `polaris_db_query_latency_seconds`), gauges (`polaris_pheromones_recent` — Mycelium liveness; `polaris_app_info` version label). Graceful fallback if `prometheus_client` is unavailable. OPERATIONS.md gains scrape-config + alerting-rule examples.
- ✅ **CI/CD pipeline configuration** *(shipped v8.93)* — `.github/workflows/ci.yml` runs the full test suite on every push: 278 structural invariants, 62 CHECK regression tests, Hypothesis property tests, ZK crate `cargo test`, bash syntax check, `ai-link-check --ci`, `ai-meta`, `ai-coherence`. PostgreSQL 16 service container with the polaris schema loaded.
- ✅ **Encryption-at-rest recipe** *(shipped v8.93)* — OPERATIONS.md § "Encryption at rest" with three operator-pick options (LUKS on bare-metal, TDE on managed Postgres, fscrypt/eCryptfs for per-directory). Verification step. PRIVACY.md cross-references.
- ✅ **Operator onboarding script** *(shipped v8.93)* — `scripts/polaris-create-operator.sh` with werkzeug scrypt password hash (matching `security.py:hash_password`), AppUser format validation (chk_appuser_username_format + chk_appuser_role), AuthAuditLog ACCOUNT_CREATED entry in the same transaction, idempotency guard against duplicate usernames, `--dry-run` mode, `--password-file` for non-interactive use, interactive stty -echo prompt for tty use.

### ⚠️ Phase 3 — Wave 1 shipped v9.01; multi-region + distributed tracing remain deferred

Phase 3 opened 2026-05-14 per [sanctum/2026-05-14-phase-3-opening.md](sanctum/2026-05-14-phase-3-opening.md) (DECIDED + CLOSED, Position A: Wave-1 autonomous-eligible 5 items in one ship). Wave 1 shipped as v9.01 same day.

VANTA-named:

- **Multi-region deployment** ⬜ — read-replicas across regions; failover orchestration; data-locality requirements per jurisdiction. Gating condition: production-deployment-pressure trigger (operator names a real data-locality constraint). Will get its own Sanctum.
- ✅ **Disaster recovery runbook** *(shipped v9.01)* — [`docs/operator/DR.md`](docs/operator/DR.md) (~450 lines): RPO ≤ 1min / RTO ≤ 30min targets named (per Sanctum §IV.1); 8 failure-class procedures; severity matrix (SEV-1/2/3/4); decision tree; on-call playbook; communications templates (status-page snippets + post-mortem template); drill cadence (monthly verify, quarterly restore, half-yearly failover, annual ransomware tabletop).
- ✅ **SOC 2 readiness checklist** *(shipped v9.01)* — [`docs/operator/SOC2.md`](docs/operator/SOC2.md) (~520 lines): TSCs in-scope per Sanctum §IV.2 (Security mandatory + Availability + Confidentiality; Processing Integrity + Privacy out-of-scope as operator-layer); CC1-CC9 mapping table — every common-criteria control mapped to existing C-constraints / G-guards / scripts that satisfy it; 7 evidence-collection SQL recipes (admin authentications by quarter, schema changes in audit period, token revocations, emergency-password-login authorizations, audit-log purges, append-only enforcement check, WebAuthn-MFA enforcement check); known-limitations section for audit transparency.

Architect+HYDRA scan additions (2026-05-14):

- **Distributed tracing** ⬜ — OpenTelemetry integration for cross-service request flows. **Gated on Phase 2.5 multi-instance** (architect's own deferral note: tracing-without-a-distributed-stack is overhead without payoff; reopens automatically when the second hop exists to trace through).
- ✅ **HSM / KMS integration for secret material** *(shipped v9.01)* — [`docs/operator/SECRETS.md`](docs/operator/SECRETS.md) § 8 (~280 lines added): three operator-pick paved paths per Sanctum §IV.3 (HashiCorp Vault Transit Engine, AWS KMS envelope encryption, GCP Secret Manager); each with install + Polaris integration shape + IAM policy + key-rotation automation + cost notes; comparison matrix; migration recipe from v8.77 file-mounted to KMS-backed (preserves user sessions across the cut).
- ✅ **Penetration test schedule + reporting cadence** *(shipped v9.01)* — [`docs/operator/PENTEST.md`](docs/operator/PENTEST.md) (~280 lines): annual cycle (internal Q1 + external Q3) per Sanctum §IV.4; scope matrix (every STRIDE entry mapped to in/out-of-scope + test approach); remediation SLA (HIGH 30d / MEDIUM 90d / LOW next-cycle); report-archive policy (filesystem AoR + SHA-256 manifest, 7-year retention); vendor evaluation checklist; 12-scenario minimum-tests-per-cycle list; follow-up testing protocol.
- ✅ **Certificate transparency monitoring** *(shipped v9.01)* — [`scripts/polaris-ct-monitor.sh`](scripts/polaris-ct-monitor.sh) (~220 lines): polls crt.sh API for cert-issuance events on ${POLARIS_DOMAIN}; SHA-256 fingerprint allowlist in `$STATE_DIR/ct-monitor/known.txt`; daily 06:00 UTC cron per Sanctum §IV.5; greppable exit codes (0 ok / 4 inconclusive / 5 anomaly); alert sink = file + stderr per Sanctum §IV.5 (operator integrates with their alerting stack); OPERATIONS.md § "Certificate transparency monitoring (v9.01)" documents setup + on-alert procedure.

Plus operator hygiene fold-in:

- ✅ **Mycelium swarm cron schedule** *(shipped v9.01)* — closes the v8.85-era HYDRA ant_colony "zero pheromones in 72h" ALERT surfaced by today's macro scan; OPERATIONS.md § "Mycelium swarm cron schedule (v9.01)" documents the every-6h cron recipe; `Pheromone` table grows ~220K rows/year at this cadence; `polaris-rotate-logs.sh` handles quarterly archive+purge.

### Maintenance rule

Add to this section when:
- A genuinely new gap is surfaced by a macro scan, an incident, or operator feedback
- A scoped move shifts phase (e.g., a Phase 3 item gets pulled into Phase 2 by operator pressure)

Never silently delete. The checklist is itself audit-of-record;
items move via strikethrough + reference to the ship that
closed them, not by removal.

---

## v7 — the plausible next release (active roadmap)

Items prefixed with ✅ are completed and recorded in CHANGELOG.md.
Items without the prefix are still active.

### ✅ R7-1. STRIDE threat model document

- **Mission link:** Done-list item 8 (Threat model: STRIDE-categorized)
- **Risk class:** LOW (pure documentation, no code change)
- **Effort:** ~1 session
- **Acceptance:**
  - `DEVNOTES/threat-model.md` exists
  - Every STRIDE category (Spoofing, Tampering, Repudiation,
    Information disclosure, Denial of service, Elevation of privilege)
    has at least 2 enumerated threats
  - Every threat is mapped to one or more existing controls (constraint
    C1-C10 from MISSION.md or another concrete defense)
  - Threats without a current control are explicitly listed as
    "ACCEPTED" or "DEFERRED" with rationale

### ✅ R7-2. Antimeridian-spanning bbox support

- **Mission link:** Done-list item 9 (eliminates the limitation)
- **Risk class:** LOW (additive — existing rejection becomes split-and-union)
- **Effort:** ~1-2 hours; bounded scope
- **Acceptance:**
  - `_parse_bbox()` accepts bboxes where `min_lon > max_lon`
  - SQL atlas functions handle the split (UNION ALL of two ranges)
  - New tests in `AtlasAPITests` for date-line-spanning queries
  - Existing 118 tests still pass
  - docs/reference/SCALING.md updated; "Antimeridian limitation" section removed

### ✅ R7-3. Cursor pagination for list pages

- **Mission link:** Done-list item 10 (eliminates the limitation)
- **Risk class:** MEDIUM (changes existing route semantics; UI flow change)
- **Effort:** ~1 session — delivered in v7.4 (2026-05-09)
- **Acceptance:**
  - ✅ `/tokens` and `/verifications` accept either `?page=N` (legacy) or
    `?cursor=X` (new); cursor takes precedence
  - ✅ Pager macro renders cursor links when on cursor mode
  - ✅ Page-deep walks ride the index (`idx_verificationevent_time_id` for
    verifications, primary key for tokens); the per-page cost is
    O(log n + page_size), not O(offset)
  - ✅ Tests for both modes; cursor pagination tested for boundary
    duplicates / skips (`CursorPaginationTokensTests`,
    `CursorPaginationVerificationsTests` — 11 tests, all green)

### ✅ R7-4. Self-improving loop (this work)

- **Mission link:** Across-cutting; advances how the agent itself
  works on Polaris
- **Risk class:** LOW (additive scripts + docs; no code path change)
- **Effort:** ~1-2 sessions
- **Acceptance:**
  - `MISSION.md`, `ROADMAP.md`, `docs/BACKLOG.md` exist
  - `scripts/ai-status.sh`, `scripts/ai-propose.sh` work end-to-end
  - `meta/autonomy-architecture.md` documents the risk classes
  - Demonstrated by completing at least one R7-* item in the same
    session that the planning layer was built

---

## v8 — plausible but not committed

### ✅ R8-1. Property-based tests for invariants

- **Mission link:** Done-list item 11
- **Risk class:** LOW (test-only)
- **Effort:** ~1-2 sessions
- **Acceptance:**
  - Hypothesis-style strategies for `IdentityToken`, `Individual`,
    `VerificationEvent` generation
  - Properties tested:
    - C2 (ZK→token_id NULL) holds for all generated valid sequences
    - C3 (one active per individual) holds across random UC-1/UC-4
      interleavings
    - C1 (append-only) holds — every UPDATE/DELETE attempt fails
  - Adds ≥10 property tests; existing tests unchanged

### ✅ R8-2. Multi-process rate limiter (Redis-backed)

- **Mission link:** Done-list item 12
- **Risk class:** MEDIUM (touches security.py rate limiter)
- **Effort:** ~1 session — delivered in v7.5 (2026-05-09)
- **Acceptance:**
  - ✅ `security.py` rate limiter has two backends (`InMemoryRateLimiter`,
    `RedisRateLimiter`) selected by `POLARIS_RATE_LIMIT_BACKEND` /
    `POLARIS_REDIS_URL`. Startup warning fires when in-memory is
    selected with `POLARIS_WORKERS > 1`.
  - ✅ Contract test suite (`_RateLimiterContractMixin`) runs identical
    assertions against both backends — concurrency, sliding-window,
    per-key independence, reset semantics. Plus
    `MultiProcessRateLimiterTests` proving the bug exists in-memory and
    Redis fixes it.
  - ✅ docs/operator/DEPLOYMENT.md gained a Rate-limiter backend section with the
    production checklist; `/api/health` reports backend + ok status.

### R8-3. External IdP (OIDC) integration

- **Status:** ✗ RETIRED 2026-05-09 (re-classified v8.26 from `⏸ DEFERRED`).
  Out-of-scope, not paused. Kept on the roadmap for audit-of-record;
  not a propose-eligible candidate until the user explicitly resurrects it.
- **Mission link:** Done-list item 13
- **Risk class:** HIGH (changes auth model; requires deployment-target
  decisions)
- **Effort:** ~1-2 sessions
- **Acceptance:**
  - OIDC flow as opt-in via env var; password auth remains default
  - At least one IdP tested (GitHub OAuth or Keycloak)
  - docs/operator/SECURITY.md updated; new threat model entries

### ✅ R8-4. PostGIS migration for spatial queries — Phase 1 foundation (v8.88)

- **Mission link:** Performance / scale headroom; not on done-list
  but clean path to 100M+ events
- **Risk class:** MEDIUM (schema change; index swap; optional
  dependency mitigates blast radius)
- **Effort:** ~1 session (Phase 1 foundation)
- **Phase 1 shipped (v8.88):**
  - `polaris_sql/13_postgis.sql` (~160 lines): optional-dependency
    DO-block that checks `pg_available_extensions` before
    `CREATE EXTENSION`. Adds generated
    `geography(Point, 4326)` columns to `VerificationEvent`
    and `TokenLifecycleEvent` + GiST indexes (`gix_verification_geo`,
    `gix_lifecycle_geo`) when PostGIS is installed.
  - `00_load_all.sql` wires `\i 13_postgis.sql` at the tail.
  - DEVNOTES/atlas-scaling.md § "PostGIS-optional scaling path"
    documents the design trade-off + sample ST_DWithin query.
  - OPERATIONS.md § "PostGIS" recipe for operator enablement.
  - 7 new structural invariants in
    `TestArchHydraTop4PostGISFoundation` enforce optional-
    dependency, idempotency, GENERATED-ALWAYS-AS-STORED pattern.
  - **Without-PostGIS path verified** live (the default for the
    dev environment): schema loads cleanly, atlas functions
    continue to work via B-tree.
- **Phase 2 deferred (gated on PostGIS-enabled environment +
  10M-event benchmark dataset):**
  - Atlas SQL function rewrite to detect PostGIS at function-call
    time and emit GiST or B-tree path conditionally.
  - Acceptance criterion: ≥3× improvement at 10M+ events,
    measured via `scripts/polaris-load-test.sh`.

### ✅ R8-5. API-layer caching for hot atlas queries

- **Mission link:** Performance; supports done-list item 6 at higher scale
- **Risk class:** LOW (additive)
- **Effort:** ~½ session
- **Acceptance:**
  - Redis-backed cache with 30s TTL on `(bbox, grid, kind)` keys
  - Cache hit / miss metrics exposed
  - Tests for: cache miss path, cache hit path, expiration, key
    collision handling

---

## v9 — speculative

### R9-1. Banking-on-Polaris reference architecture (separate repo)

- **Status:** ✗ RETIRED 2026-05-09 (re-classified v8.26 from `⏸ DEFERRED`).
  Out-of-scope, not paused. Kept on the roadmap for audit-of-record;
  not a propose-eligible candidate until the user explicitly resurrects it.
- **Mission link:** Done-list item 14; demonstrates C10 in practice
- **Risk class:** HIGH (architectural decision with sovereignty implications)
- **Effort:** ~5+ sessions; separate repository
- **Acceptance:**
  - New repo `polaris-ledger`
  - Consumes Polaris verification proofs over HTTP
  - FK-enforced separation: `MonetaryClaim` cannot reference
    `IdentityToken` directly; must reference a verification proof URI
  - Architecture document explains why architecture #2 was chosen over
    architectures #1 and #3

### R9-2. Linux + Windows launcher variants

- **Status:** ✗ RETIRED 2026-05-09 (re-classified v8.26 from `⏸ DEFERRED`).
  Out-of-scope, not paused. Kept on the roadmap for audit-of-record;
  not a propose-eligible candidate until the user explicitly resurrects it.
- **Mission link:** Done-list item 15
- **Risk class:** LOW (no security implications)
- **Effort:** ~1-2 sessions per platform
- **Acceptance:**
  - `polaris_linux_launch.sh` works on Ubuntu 22.04 + Fedora
  - `polaris_windows_launch.ps1` works on Windows 10/11 with WSL
  - Same self-heal / doctor / nuke / watch contract as macOS launcher

### ✅ R9-3. Federation across jurisdictions

- **Status:** Superseded and delivered — v2 mission item M2-8 / R11-3
  shipped 2026-05-12 in v8.22 with `AgencyTrustAttestation` table,
  `uc10_attest_trust` + `uc10_revoke_attestation` procedures, the
  per-attesting-agency advisory lock (5th catalog entry), and the
  `_federation_trust_holds` verification flow gate. See
  `DEVNOTES/ships/federation.md`.
- **Mission link:** v2 done-list item M2-8 ✅
- **Risk class:** was HIGH; delivered as MEDIUM-risk per Sanctum
- **Effort:** delivered

---

## v10 — v2 mission, substrate arc (D)

These items make Appendices E and F of the project report concrete.
See `MISSION.md` v2 done-list M2-1..M2-5 and `meta/missions-considered.md`.
Numbered R10-* (substrate) to leave room for further v8/v9 items above.

### ✅ R10-1. Real ZK-SNARK for ZERO_KNOWLEDGE verifications

- **Mission link:** v2 M2-1 (substrate) — delivered in v8.23 (2026-05-11)
- **Risk class:** HIGH (cryptographic rabbit hole; circuit design)
- **Effort:** ~3-5 sessions estimated — shipped in one
- **Acceptance:**
  - ✅ Plonky2 circuit (FRI-based, post-quantum-comfortable) proves
    Merkle inclusion in `TokenStateEpoch.merkle_root` bound to
    `(epoch_id, context_id, nonce)` public inputs. C3+A4+B3 picked
    at the M2-1 alignment-exploration Sanctum.
  - ✅ Server-side verifier (`polaris_web/zk.py` → `polaris_zk/`
    subprocess) accepts valid proofs and rejects tampered ones
  - ✅ `TokenStateEpoch` + `TokenStateEpochLeaf` tables — the
    cryptographic commitment is the schema-level audit-of-record (7th
    instance)
  - ✅ Tests: honest prover succeeds; replay-with-wrong-nonce fails;
    cross-epoch fails; cross-context fails; wrong-root fails;
    witness-leak resistance is the SNARK soundness property
  - ✅ **Transparent setup** (C3) — Plonky2 is FRI-based and requires
    no trusted-setup ceremony, replacing the PDF's "documented as dev
    artifact" requirement with an honesty-first posture
  - ✅ **Substrate-D arc closed 5/5** (M2-1 + M2-2 + M2-3 + M2-4 + M2-5)

### ✅ R10-2. Functional DID anchoring

- **Mission link:** v2 M2-2 (substrate) — delivered in v8.21 (2026-05-11)
- **Risk class:** MEDIUM (new endpoint; new state surface)
- **Effort:** ~3 sessions — shipped in one
- **Acceptance:**
  - ✅ Append-only Merkle log (no external blockchain dependency;
    `AnchorBatch` is the off-chain audit-of-record; `committed_to_chain`
    + `external_chain` are operator-set future-fields ready when an
    external PQ-capable ledger integration ships)
  - ✅ `close_anchor_batch(algorithm_id, root, proofs)` procedure
    groups pending `BlockchainAnchor` rows by underlying signature
    algorithm; per-algorithm advisory-lock (4th entry in the catalog);
    extends `BlockchainAnchor` with `batch_id` + `merkle_proof` (co-NULL
    invariant via CHECK constraint)
  - ✅ `polaris_web/anchoring.py` — Merkle helper (compute_batch,
    leaf_hash, merkle_root, inclusion_proof, verify_proof); SHA3-256
    default; sort by anchor_id for publish-then-fork resistance
  - ✅ `/api/anchor/batch` (POST, admin) closes a batch
  - ✅ `/api/anchor/<token_id>` (GET) returns anchor + batch + proof
  - ✅ `/api/anchor/verify/<token_id>` (GET) server-side reconstructs
    the Merkle root from leaf + proof and rejects tampered logs
  - ✅ 5 SQL self-tests in `08_tests.sql` section O
  - ✅ 15 Python tests in `AnchorBatchTests` + 2 concurrency tests
    (`test_close_anchor_batch_same_algorithm_serializes`,
    `test_close_anchor_batch_cross_algorithm_parallel`)
  - ✅ `DEVNOTES/ships/anchoring.md` written; `audit-of-record.md` extended
    to 5 instances; `concurrency.md` extended to 4 advisory-lock
    entries

### ✅ R10-3. Substrate-dependency manifest

- **Mission link:** v2 M2-3 (substrate)
- **Risk class:** LOW (documentation + queryable view)
- **Effort:** ~1 session — delivered in v8 (2026-05-09)
- **Acceptance:**
  - ✅ `DEVNOTES/substrate.md` — 27 named primitives across 7 layers
    (crypto, network, storage, runtime, standards, hardware, human),
    each with fail-mode / replacement / detection. Re-evaluation
    triggers documented.
  - ✅ Cross-references to Appendix E (substrate-layer argument),
    MISSION C7, DEVNOTES/threat-model.md, DEVNOTES/rate-limiter.md, and
    meta/redaction-proof.md.
  - ✅ `polaris_sql/13_substrate.sql` defines the read-only
    `SystemDependency` view as the queryable mirror; INSERT into the
    view is rejected (test enforces).
  - ✅ `SubstrateManifestTests` verifies row count, all 7 layers
    present, every row has complete metadata, well-known load-bearing
    primitives appear by name, and the prose form mentions every SQL
    primitive (drift detection).

### ✅ R10-4. GenomicAnchor schema (Appendix F.1)

- **Mission link:** v2 M2-4 (substrate)
- **Risk class:** LOW (additive schema)
- **Effort:** ~1 session — delivered in v8 (2026-05-09)
- **Acceptance:**
  - ✅ New table `GenomicAnchor` (anchor_id, token_id, hash_algorithm,
    anchor_hash, enrollment_date, witness_agency_id, enrolled_at)
  - ✅ Three CHECK constraints layered:
    `genomic_hash_is_hex` (hex format) +
    `genomic_hash_length_matches_algorithm` (length per algorithm) +
    `genomic_anchor_refuses_plaintext` (must contain at least one
    char outside the genomic alphabet {A,C,G,T,U,N})
  - ✅ Sample data: 3 rows (one per ACTIVE token T2/T3/T4)
  - ✅ Tests: 11 in `GenomicAnchorTests` covering each constraint's
    failure mode + FK validation + happy paths

### ✅ R10-5. QuantumObserverBinding scaffold (Appendix F.2)

- **Mission link:** v2 M2-5 (substrate)
- **Risk class:** LOW (scaffold only; functional fields explicitly DEFERRED)
- **Effort:** ~½ session
- **Acceptance:**
  - ✅ Table exists with two CHECK constraints enforcing the
    SCAFFOLD/OPERATIONAL state transition; column comments explain
    each deferred field
  - ✅ `DEVNOTES/ships/quantum-observer.md` explains the architectural
    rationale, expected `observer_protocol` values from Appendix F.2,
    and the state-transition diagram
  - ✅ Schema does not block functional state — the test
    `test_operational_state_with_full_functional_fields_succeeds`
    proves forward compatibility
  - ✅ `SystemDependency` view + `DEVNOTES/substrate.md` updated to
    catalog the reserved primitive; `test_prose_and_sql_forms_agree`
    enforces the two stay in sync
  - ✅ Tests: 9 in `QuantumObserverBindingTests` (table exists,
    SCAFFOLD default, three CHECK-fires on premature population,
    OPERATIONAL-requires-fields CHECK, OPERATIONAL with full fields
    succeeds, enum CHECK, substrate-manifest cross-reference)

---

## v11 — v2 mission, open-problems arc (A)

These items close the gaps the project report itself names in §9.
See `MISSION.md` v2 done-list M2-6..M2-12.

### ✅ R11-1. Multi-signature transitional state (§9.4)

**Delivered v8.18** (2026-05-11). Closes M2-6 and the cryptographic-
diversity leg of the issuer-trust-concentration triad alongside
R11-6 ✅. M2-8 federation is now the only unbuilt leg across both
PDF §9 triads.

**Shipped:**

- `TokenSignature` table (M:N) with UNIQUE composite key and
  `deprecation_after_signed` CHECK. Schema at 18 tables after this
  ship (later extended to 19 by R10-2 / M2-2 / v8.21).
- Partial index `idx_token_signature_active` for O(1) verification.
- Two triggers: `enforce_token_has_active_signature` (≥ 1 active
  signature per token) + `enforce_token_signature_immutability`
  (write-once with one-way `deprecation_date`).
- Procedure `uc6_migrate_algorithm` with
  `pg_advisory_xact_lock(hashtext('polaris.migrate.' || token_id))`
  for C9 correctness; per-token serialization, cross-token parallel.
- UC-1 (`uc1_issue_and_activate`) and UC-9
  (`uc9_complete_recovery` APPROVED branch) extended to INSERT a
  TokenSignature row alongside the new IdentityToken.
- Backfill block in `04_data.sql` covering all v1 sample tokens
  with `BACKFILL_PLACEHOLDER` tags.
- Flask `/uc6/migrate` route + template; nav entry. Dashboard's
  Post-Quantum panel re-queries against the M:N relation.
- 16 tests in `MultiSignatureTests` (including the no-auto-derivation
  assertion mirroring R11-4) + 3 tests in `ConcurrencyTests`
  (per-token race, verify+migrate snapshot consistency, cross-token
  parallelism). 5 SQL self-tests in section N.
- `DEVNOTES/ships/multi-sig-migration.md` documents the adversary walk,
  consistency model, and the issuer-trust-triad positioning;
  `DEVNOTES/concurrency.md` gains the per-token-lock catalog entry.
- `docs/reference/DATA-MODEL.md`, `docs/reference/API.md` (`POST /uc6/migrate`),
  `docs/operator/SECURITY.md` (Cryptographic Migration subsection).

---

### (historical R11-1 spec, before delivery)

- **Mission link:** v2 M2-6 (open problems)
- **Risk class:** MEDIUM (changes core token verification flow)
- **Effort:** ~2 sessions
- **Acceptance:**
  - New `TokenSignature` table (token_id, algorithm_id, signature_bytes,
    issued_date, deprecation_date)
  - Verification accepts ANY valid signature in the active set; the
    "active set" is determined by deprecation_date being NULL or future
  - UC-6 (algorithm migration) updated to ADD signatures rather than
    swap; tests for the migration window where both old and new
    signatures are valid
  - Trigger ensures every IdentityToken has ≥1 non-deprecated signature
    (would otherwise be unverifiable)

### ✅ R11-2. Catastrophic-loss recovery — UC-9 (§9.1)

- **Mission link:** v2 M2-7 (open problems)
- **Risk class:** MEDIUM (propose-and-wait; new lifecycle pathway)
- **Effort:** ~2 sessions — delivered in v8.17 (2026-05-11)
- **Achieved:**
  - `RecoveryRequest` table with four load-bearing CHECK constraints
    (cool-down ≥ 48h, three OOB channels required for APPROVED,
    decided_at after cool-down, approver ≠ requester)
  - Partial unique index `uq_one_pending_recovery_per_individual`
    ensures at most one PENDING per individual at a time
  - Two-phase procedures: `uc9_initiate_recovery` (operator+admin
    can initiate) and `uc9_complete_recovery` (admin only;
    RAISE EXCEPTION enforced inside the procedure as belt-and-
    suspenders to the Flask `@require_role('admin')`)
  - `pg_advisory_xact_lock` on claimed_individual_id for C9
    concurrency correctness; cross-individual recoveries remain
    parallel
  - APPROVED branch: transition non-terminal tokens to LOST,
    publish each to RevocationList (UC-4 pattern), issue new
    ACTIVE token with `predecessor_token_id=NULL`, tag all
    lifecycle rows with `[RECOVERY:<recovery_id>]`
  - Three Flask routes: `/uc9/initiate-recovery`, `/uc9/queue`,
    `/uc9/decide/<id>`; three templates + nav entry
  - 15 tests in `CatastrophicLossRecoveryTests`, 2 in
    `ConcurrencyTests`, 5 SQL self-tests in section M
  - `DEVNOTES/ships/recovery-ceremony.md` documents the adversary walk,
    the four-CHECK mechanism, the administrative-vs-operational
    grace-period framing, and PDF §9.1 anchoring;
    `DEVNOTES/concurrency.md` gains the per-individual
    advisory-lock pattern; `docs/operator/SECURITY.md` recovery threat-model
    subsection; `docs/reference/API.md` UC-9 endpoint reference; `docs/DATA-
    MODEL.md` `RecoveryRequest` section.
  - **The third leg of the "schema doesn't weaponize itself against
    the holder" triad (entry R11-4, exit R11-6, recovery this) —
    now structurally complete.**
- **Note:** Originally drafted as UC-8 in `proposals/R11-2-…`; UC-8
  was claimed by R11-6 (Bounded Revocation) in v8.15, so this work
  shipped as UC-9. The proposal text was renamed accordingly.
  - UI flow on /tokens for recovery initiation
  - Trigger enforces grace-period max (e.g., 30 days)
  - Tests: happy path; grace-period expiry; unauthorized recovery
    attempt rejected; audit trail entries written

### ✅ R11-3. Issuer federation model (§9.2)

- **Mission link:** v2 M2-8 (open problems) — delivered in v8.22 (2026-05-11)
- **Risk class:** HIGH (cross-jurisdiction trust; sovereignty implications)
- **Effort:** ~3 sessions — shipped in one
- **Acceptance:**
  - ✅ New `AgencyTrustAttestation` table (attesting_agency_id,
    attested_agency_id, context_id, attested_date, valid_until,
    signed_by, revocation_date, revocation_reason) with 3 CHECK
    constraints (no-self-attestation, validity-floor, revocation-
    consistency) and partial unique index on the active triple
  - ✅ Verification flow gates SUCCESS outcomes via the new
    `_federation_trust_holds()` helper in `app.py`
  - ✅ Cross-jurisdiction TSA scenario: TSA (Agency 4) verifies CA-
    issued (Agency 3) tokens for TRAVEL iff seed attestation
    4→3 for TRAVEL exists
  - ✅ Attestation revocation tested (`uc10_revoke_attestation`);
    revocation is forward-looking (past `VerificationEvent` rows
    survive)
  - ✅ Explicit-only federation: NO transitive trust (R1 audit
    refinement) — test verifies that A→B + B→C does NOT imply A→C
  - ✅ Per-attesting-agency advisory lock (5th catalog entry); both
    same-attesting-agency serialization and cross-attesting-agency
    parallelism tested
  - ✅ `enforce_attestation_immutability` trigger enforces append-
    only with one-way revocation; 6th audit-of-record instance
  - ✅ Two Flask routes: `POST /api/federation/attest` and
    `POST /api/federation/revoke` (admin-only); CSRF via
    `X-CSRFToken` header (v8.22 added header support to
    `validate_csrf`)
  - ✅ 6-row seed graph in `10_auth.sql` matching existing demo
    verifications
  - ✅ 15 `IssuerFederationTests` + 2 `ConcurrencyTests` + 5 SQL
    self-tests in section P
  - ✅ `DEVNOTES/ships/federation.md` written; `audit-of-record.md` extended
    to 6 instances; `concurrency.md` extended to 5 advisory-lock
    entries
  - ✅ **Issuer-trust-concentration triad closed 3/3** (cryptographic
    diversity R11-1 + constitutional limits R11-6 + federation R11-3)

### ✅ R11-4. Tiered enrollment / population coverage (§9.3)

- **Mission link:** v2 M2-9 (open problems)
- **Risk class:** MEDIUM (propose-and-wait; sociotechnical surface)
- **Effort:** ~1-2 sessions — delivered in v8.16 (2026-05-11)
- **Achieved:**
  - `EnrollmentStatusEvent` append-only table with 5-status CHECK
    enum (`NOT_ENROLLED`, `PENDING_ENROLLMENT`, `ENROLLED`, `EXEMPT`,
    `LAPSED`)
  - `IndividualCurrentEnrollment` view returns latest event per
    individual, COALESCEs to `NOT_ENROLLED` when no events exist
  - `seed_default_enrollment_status` trigger emits a `NOT_ENROLLED`
    event on every new `Individual` so the absence is materialized
  - Append-only invariant extended via the existing
    `reject_audit_modification` trigger
  - `civic_enrollment_summary(jurisdiction)` function returns
    per-jurisdiction × status counts — **counts only**, per-individual
    enumeration deliberately not first-class (asymmetric design
    against the NOT_ENROLLED-as-surveillance-marker attack)
  - `/individuals/enrollment` Flask route + pivot table template
  - 10 tests in `TieredEnrollmentTests`, 5 SQL self-tests in
    section L
  - `DEVNOTES/ships/tiered-enrollment.md` documents the asymmetric design,
    adversary walk, no-auto-derivation rationale, and PDF §9
    anchoring; `docs/reference/DATA-MODEL.md` `EnrollmentStatusEvent` section;
    `docs/reference/API.md` `/individuals/enrollment` reference;
    `docs/operator/PRIVACY.md` Population coverage subsection

### ✅ R11-5. Compulsion resistance — duress codes (§9.5)

- **Mission link:** v2 M2-10 (open problems) — delivered in v8.24 (2026-05-11)
- **Risk class:** HIGH (privacy-critical; timing-attack surface)
- **Effort:** ~2 sessions estimated — shipped in one
- **Acceptance:**
  - ✅ `IdentityToken.duress_code_hash` (Werkzeug scrypt, hash-only)
  - ✅ Verification flow accepts an optional `duress_code` field;
    constant-time hash comparison via
    `werkzeug.security.check_password_hash` (same primitive as
    AppUser auth)
  - ✅ DuressEvent table is the 8th audit-of-record; append-only via
    `reject_audit_modification` trigger
  - ✅ R6 anti-revealing posture: `/verifications` operator list does
    NOT join to DuressEvent; admin/auditor-only `/api/duress/events`
    dashboard
  - ✅ Identical observable behavior across all four branches
    (R2 audit refinement)
  - ✅ Duress secret never appears in plaintext — only the scrypt
    hash is stored (the plaintext '911911' demo code is documented in
    the seed file for teaching purposes only)
  - ✅ **v2 mission-closer — v2 done-list = 12/12 ✅**

### ✅ R11-6. Issuer-discretion bounds

- **Mission link:** v2 M2-11 (open problems; defends UC-1 failure-mode
  concern about denaturalization-style mass revocation)
- **Risk class:** MEDIUM (propose-and-wait; constrains operational
  behavior, needed carefully-chosen bound)
- **Effort:** ~1 session — delivered in v8.15 (2026-05-11)
- **Achieved:**
  - `IssuerDiscretionPolicy` table for per-agency policy overrides
    with justification length floor; sample data ships two overrides
    (agency 1 loosened, agency 6 tightened) demonstrating both
    directions
  - `uc8_revoke_token` stored procedure: rolling N%/W-day cap,
    optional co-signer who must hold `BOTH` on the algorithm and
    differ from actor, RevocationList publish in same transaction
    (UC-4 pattern), `[COSIGN:<id>]` tag in audit reason_code while
    CRL stays in canonical reason vocabulary
  - System defaults via `ALTER DATABASE` GUCs (N=5%, W=30d) with
    procedure-level fallback for missing GUCs
  - `enforce_revocation_velocity_bound` BEFORE-UPDATE trigger as
    belt-and-suspenders against raw UPDATEs
  - `pg_advisory_xact_lock` per agency_id for C9 concurrency
    correctness; cross-agency revocations remain parallel
  - 11 tests in `IssuerDiscretionBoundsTests`, 2 in `ConcurrencyTests`,
    7 SQL self-tests in section K
  - `DEVNOTES/ships/issuer-discretion.md` documents the N=5% / W=30d
    Schelling-point choices, adversary walk, advisory-lock
    rationale, and PDF §9 *"constitutional limits on issuer
    discretion"* anchoring; `docs/operator/SECURITY.md` denaturalization-
    resistance subsection; `docs/reference/API.md` `/uc8/revoke` reference;
    `docs/reference/DATA-MODEL.md` IssuerDiscretionPolicy section

### ✅ R11-7. Verification-graph redaction proof

- **Mission link:** v2 M2-12 (open problems; strengthens C2 from
  syntactic NULL to semantic privacy claim)
- **Risk class:** LOW (proof + tests; no schema or runtime change)
- **Effort:** ~1-2 sessions — delivered in v8 (2026-05-09)
- **Acceptance:**
  - ✅ `meta/redaction-proof.md` with formal adversary model (passive
    read-only attacker; full SELECT privilege), privacy claim, five
    enumerated side-channels (S1 temporal, S2 spatial, S3 sequential,
    S4 commitment determinism, S5 agency-context bias), and explicit
    re-evaluation triggers
  - ✅ `test_redaction_property.py` with three adversary classes
    (`UniformGuessAdversary`, `TemporalCorrelationAdversary`,
    `SpatialUniquenessAdversary`) and 6 tests demonstrating both that
    isolated ZK sequences resist reconstruction (success rate bounded
    by 1/N + slack) AND that the two named counterexamples succeed —
    documented operational limits, not disguised weaknesses
  - ✅ Wired into the main suite via `test_app.py` import block

---

## v12 — Arc D, Swarm / HYDRA (closed 2026-05-12 at 8/8 ✅, opened 2026-05-12)

Authorized by Sanctum
`sanctum/2026-05-12-new-chapter-swarm-hydra-arc-opening.md`. Evolves
Polaris's single-Architect cognitive synthesis into a multi-agent
swarm + unified HYDRA host. Modeled on BettaFish's ForumEngine pattern
(prior art, not vendored).

See `MISSION.md` §"Arc D — Swarm / HYDRA" for the done-list (H1..H8).

### ✅ R12-1. HYDRA host (`polaris_hydra/host.py`)

**Delivered v8.37** (2026-05-12). Phase 1 of Arc D.

**Shipped:**
- `polaris_hydra/host.py` — aggregator that gathers `WatcherReport`s
  and emits a `HydraSynthesis` via either Claude Opus 4.7 (with
  adaptive thinking, when `ANTHROPIC_API_KEY` is set) or a
  deterministic structured fallback (CI + offline mode).
- LLM-call path uses streaming (`messages.stream`) +
  `get_final_message()` per the Anthropic skill defaults.
- CLI entry point (`python -m polaris_hydra.host`) supports
  `--watcher NAME`, `--query "…"`, `--json`, `--help`.

- **Mission link:** Arc D done-list item H1
- **Risk class:** MEDIUM (architectural edge)

### ✅ R12-2. SchemaWatcher (`polaris_hydra/watchers/schema_watcher.py`)

**Delivered v8.37** (2026-05-12). First watcher; proves the swarm
contract end-to-end.

**Shipped:**
- Reads `information_schema.triggers`, `pg_indexes`, `pg_views`, and
  audit-of-record table row counts.
- Detects the v8.32 silent-failure mode (12_v7_constraints.sql DDL
  not applied as superuser) explicitly: separate `alert` finding
  category for v7-hardening misses.
- Graceful fallback when psycopg2 absent or DB unreachable: emits
  an `alert` finding rather than crashing HYDRA.

- **Mission link:** Arc D done-list item H2
- **Risk class:** LOW (additive, read-only)

### ✅ R12-3. CognitiveWatcher

**Delivered v8.38** (2026-05-12). Second watcher; closes the
Phase-2-first-watcher slot. Closes MISSION done-list item H3.

**Shipped:**
- `polaris_hydra/watchers/cognitive_watcher.py` — invokes
  `scripts/ai-meta.sh` as a subprocess and classifies the verdict
  (`healthy` / `drift` / `broken`); reads the pattern catalog
  dynamically from `scripts/ai-pattern.sh` and measures warmth
  against `journal/*.md` mentions; checks `ai-*.sh` script mtimes
  for `> 60d` staleness; verifies `sanctum/` count parity with
  `meta/sanctum-index.md` entries.
- Honors the v8.30 substitutability principle: the watcher reads
  from canonical sources, does not duplicate their logic.
- Caught its own design bug at first smoke: my initial hardcoded
  `EXPECTED_PATTERNS` list disagreed with the actual catalog
  (Investigation/Audit/Recovery in catalog; not in my list).
  Refactored to derive from the catalog dynamically; the watcher
  now flags catalog-size drift instead of name drift.
- 3 new structural tests (67/67 total).

- **Mission link:** Arc D done-list item H3
- **Risk class:** LOW (additive, read-only)

### ✅ R12-4. SecurityWatcher

**Delivered v8.39** (2026-05-12). Third watcher; closes MISSION
done-list item H4.

**Shipped:**
- `polaris_hydra/watchers/security_watcher.py` — five-channel
  watcher: CSP literal scan + no-unsafe-inline check; CSRF
  validate_csrf + dual-transport (form + X-CSRFToken) check;
  `/api/health` rate-limiter probe (1.5s timeout; offline = info
  not alert); role-gating decorator counts (47 login_required + 25
  require_role baseline observed at v8.39, flag-on-drop);
  R6 anti-revealing scan across 9 operator-visible templates +
  rendered-text scan of verifications_form.html (Jinja comments
  + HTML attributes stripped before keyword check).
- **Self-calibrated mid-ship.** First version had a guessed
  baseline (50/10) and over-strict R6 scan; watcher reported
  drift + alert that were both false positives. Refactored:
  baselines observed empirically (47/25); R6 scan strips Jinja
  `{# … #}` comments + `="..."` attributes before keyword check
  (so `verifications_form.html`'s legitimate `name="duress_code"`
  doesn't false-positive).
- 4 new structural tests including a Jinja-stripping unit test
  (71/71 total).

- **Mission link:** Arc D done-list item H4
- **Risk class:** LOW (additive, read-only, graceful on offline app)

### ✅ R12-5. MissionWatcher

**Delivered v8.40** (2026-05-12). Fourth watcher; closes MISSION
done-list item H5.

**Shipped:**
- `polaris_hydra/watchers/mission_watcher.py` — four channels:
  done-list rollup (parses ✅ / ⬜ / ✗ across v1 [15 items],
  v2 [M2-1..M2-12], Arc D [H1..H8]; flags arithmetic mismatches as
  alerts); steady-state marker verification (the v8.31 phrase
  `Resolved 2026-05-12: steady-state` must still be present);
  section anchor presence (v1/v2/Arc-D headers); stale-⬜ detection
  (> 7 days without journal OR ROADMAP mention).
- **Self-calibrated mid-ship.** First smoke reported 6 stale ⬜
  items; investigation showed H1 + H2 had been delivered in v8.37
  but never marked ✅ in MISSION.md (real audit-of-record arrearage).
  Backfilled H1/H2 ✅ + H5 ✅ in the same ship. Watcher then
  reported 3 remaining stale (H6/H7/H8) — also a false-positive,
  since those items are scheduled in ROADMAP with acceptance
  criteria. Refined the watcher: pending items mentioned in a
  recently-touched ROADMAP count as "scheduled, not forgotten."
- 3 new structural tests including done-list-arithmetic invariants
  (74/74 total).

- **Mission link:** Arc D done-list item H5
- **Risk class:** LOW (additive, read-only, file parsing only)

### ✅ R12-6. AdversaryWatcher

**Delivered v8.41** (2026-05-12). Fifth watcher; closes MISSION
done-list item H6.

**Shipped:**
- `polaris_hydra/watchers/adversary_watcher.py` — invokes
  `scripts/ai-adversary.sh` once per C-constraint (10 subprocess
  calls, 5s per-walk timeout). Parses the six-section equilibrium
  structure with substring-matched headers (so e.g.
  `Second-best attack (if equilibrium holds)` matches the canonical
  `Second-best attack` prefix). Surfaces each constraint's
  second-best attack in `evidence_summary` so HYDRA can cite the
  full game-theoretic threat map.
- **Self-calibrated mid-ship.** First smoke reported 10/10 walks
  malformed because my exact-match parser missed the parenthetical
  in the actual section header. Refined to substring matching;
  now 10/10 clean.
- 3 new structural tests including a contract test that asserts
  all 10 walks complete + each has a non-empty second-best attack
  (77/77 total).

- **Mission link:** Arc D done-list item H6
- **Risk class:** LOW (10 read-only subprocess calls, 5s per-walk
  timeout, no state modification)

### ✅ R12-7. PerformanceWatcher

**Delivered v8.42** (2026-05-12). Sixth watcher; **closes Phase 2 of
Arc D — 6/6 watchers live.** Closes MISSION done-list item H7.

**Shipped:**
- `polaris_hydra/watchers/performance_watcher.py` — three channels:
  - **Atlas latency** times `/api/atlas/stats`, `/clusters`, `/points`
    with a 3 s budget; drift at > 200 ms, alert at > 1 s. App
    offline reports `info` (not alert) so the watcher doesn't
    cry-wolf on a stopped instance.
  - **App-self-report** GETs `/api/health` (if reachable) and
    surfaces the JSON-reported overall status.
  - **Query-plan spot-check** runs `EXPLAIN (ANALYZE, BUFFERS,
    FORMAT JSON)` on the canonical bbox query against
    `VerificationEvent`. **Row-threshold-gated:** below 1000 rows
    the optimizer's choice to Seq Scan is the correct plan and is
    not flagged. Above the threshold, Seq Scan triggers a
    regression alert.
- **Self-calibrated mid-ship.** First smoke flagged the seed-DB
  Seq Scan (9 rows) as `alert: SEQ_SCAN_REGRESSION`. Added
  `SEQ_SCAN_REGRESSION_ROW_THRESHOLD = 1000` so the watcher
  respects optimizer reality. **This was the fifth consecutive
  Phase-2 ship where the watcher caught its own calibration bug
  mid-build** — a pattern worth naming. The swarm grows up by
  catching itself.
- 3 new structural tests (80/80 total — Phase 2 close-out).

- **Mission link:** Arc D done-list item H7
- **Risk class:** LOW (read-only timing + one offline EXPLAIN
  ANALYZE; query-plan check is gated on app availability)

### ✅ R12-8. HYDRA constitutional integration

**Delivered v8.43** (2026-05-12). **Closes Phase 3 of Arc D and Arc D
itself.** Sanctum-authorized
(`sanctum/2026-05-12-hydra-constitutional-integration.md`, Option C —
narrow naming). Closes MISSION done-list item H8.

**Shipped:**
- **MISSION.md §"What this section is NOT"** extended with one new
  bullet naming the HYDRA swarm (`polaris_hydra/`) and its six
  watchers (schema, cognitive, security, mission, adversary,
  performance) as the operative synthesis implementation as of
  v8.43, cross-referenced to both the arc-opening Sanctum
  (v8.37) and the constitutional-integration Sanctum (v8.43).
  The closing paragraph extended with an explicit substitutability
  clause: *"A future agent may replace the HYDRA swarm with a
  different synthesis pattern without amending this section,
  provided the four principles still hold."* The v8.30
  substitutability principle is preserved verbatim.
- Arc D header in MISSION.md transitions
  `(active, opened 2026-05-12)` → `(closed 2026-05-12, opened 2026-05-12)`.
- **`TestHydraConstitutionalIntegration` class** in
  `polaris_web/test_structural_invariants.py` — 2 soft-check tests:
  one asserts the HYDRA naming + directory cross-reference are
  present in the cognitive-substrate section; one asserts the
  substitutability qualifier follows the HYDRA mention. Both pin
  the *property*, not the prose. **82/82 structural tests pass.**
- The `## The cognitive substrate` section's substitutable-
  implementation enumeration also gains a script-count update
  (27 → 28 ai-* scripts, reflecting ai-hydra.sh added v8.37).

**Constitutional principles unchanged.** The four principles
(Sanctum, AoR, risk classes, CM) are untouched. HYDRA is named as
*operative implementation*, not as a new principle.

- **Mission link:** Arc D done-list item H8
- **Risk class:** MEDIUM (Sanctum-authorized; constitutional
  documentation amendment)

---

## v13 — Arc E, Mycelium / genuine swarm intelligence (active, opened 2026-05-13)

Authorized by `sanctum/2026-05-13-arc-e-swarm-intelligence-opening.md`.
v8.31 trigger 3 fired again on VANTA's "Mission Prompt: Genuine
Swarm Intelligence Layer." Arc E replaces HYDRA's centralized
synthesis with a stigmergic ant-colony pattern depositing pheromones
onto brain-map nodes. Phase 1 (E1) shipped v8.62; subsequent
phases earn their own ai-done gates.

### ✅ R13-1. Mycelium Phase 1 — pheromone substrate (`v8.62`)

The 11th audit-of-record instance plus the swarm scaffold.

**Shipped:**

- `Pheromone` table + `trg_pheromone_append_only` trigger +
  3 indexes (`polaris_sql/01_schema.sql` + `06_triggers.sql`).
- `polaris_swarm/` module: `base.py` (Pheromone dataclass + Ant
  base + `effective_intensity()` decay), `ants/` (3 starter ants),
  `colony.py` (deposit runner with per-ant advisory locks —
  the 7th catalog entry).
- `scripts/ai-swarm-bloom.{sh,py}` — operator-facing renderer.
- `TestMyceliumPhaseOne` (4 tests; G6-G9 contract guards).

**Pattern realized:** v8.42 self-calibration realized once more
(the colony's first run surfaced a real drift the v8.61
ai-coherence check had missed — `/api/heartbeat` documented as
GET when actually POST). Fixed in the same ship.

- **Mission link:** Arc E done-list item E1
- **Risk class:** MEDIUM (Sanctum-authorized; new schema +
  cognitive-layer scaffold)

### ✅ R13-2. Expand the cohort to 12 ants (`v8.63`)

Added 9 ants to reach 12 total covering all 7 HYDRA watcher
domains. Each <100 LOC. Each independent (G6). Each LLM-free (G8).
Cohort is deliberately overlapping so removing 3-5 ants degrades
coverage gracefully.

**Shipped:** ant_aor_immutability + ant_fk_cascade_guard (schema),
ant_stale_script + ant_pattern_warmth (cognitive), ant_csp_health
(security), ant_done_list_arithmetic (mission),
ant_adversary_walk_complete (adversary),
ant_atlas_endpoint_health (performance), ant_ship_burst
(trajectory). Two ants self-calibrated mid-ship — the 7th
instance of the self-calibration pattern.

- **Mission link:** Arc E done-list item E2
- **Risk class:** LOW (additive, deterministic, no schema changes)

### ⬜ R13-3. Brain-map bloom integration

Render pheromone intensity directly on `meta/brain-map/brain-map.html`
as a color overlay (heatmap on graph nodes). Operator sees structural
attention in situ rather than via a separate sorted list.

- **Acceptance:** brain-map HTML accepts an optional embedded
  `pheromone` blob and colors nodes by effective intensity at
  render time; `ai-brain-map.sh --with-bloom` flag wires it up.
- **Mission link:** Arc E done-list item E3
- **Risk class:** LOW (additive rendering, no schema/security
  changes)

### ⬜ R13-4. Deliberation threshold + optional LLM translation

When N pheromones accumulate on one node within T minutes,
optionally invoke ONE LLM call (in the Architect voice) to
translate the pattern into prose. The pheromone log remains the
truth; the prose is commentary. Threshold is configurable; LLM
absence falls back to deterministic structured output.

- **Acceptance:** `ai-swarm-bloom --deliberate` mode that checks
  the threshold and either calls Claude Opus 4.7 OR emits a
  deterministic summary; threshold and budget are env-var
  configurable.
- **Mission link:** Arc E done-list item E4
- **Risk class:** LOW (additive optional surface)

### ⬜ R13-5. HYDRA-vs-Mycelium decision Sanctum

After R13-2..R13-4 are in operation for enough time to evaluate,
a Phase 3+ Sanctum decides whether HYDRA stays (as a synthesis
commentator) or steps aside in favor of Mycelium alone.
v8.30 substitutability authorizes either outcome.

- **Acceptance:** Sanctum opened; Architect's brief includes a
  prediction-vs-reality scan over E1-E4 evidence; VANTA decides.
- **Mission link:** Arc E done-list item E5
- **Risk class:** MEDIUM (constitutional question; touches the
  HYDRA naming in MISSION.md §"What this section is NOT")

### ✅ R13-10. Acceleration + consciousness cohort expansion (`v8.69`)

**Sanctum-authorized:**
`sanctum/2026-05-13-arc-e-acceleration-consciousness-cohort-e10.md`.
VANTA: *"design a cohort that evolves the swarm from
maintenance/immune system to development acceleration + swarm
consciousness."* The 100-day report identified the cohort as
overwhelmingly immune-system-shaped (detecting drift from
documented state). E10 adds two new perceptual modes.

**Shipped:**

- **5 acceleration ants** (gaze outward at the future):
  `ant_todo_debt`, `ant_test_gap`, `ant_recent_churn`,
  `ant_unbumped_version`, `ant_changelog_gap`.
- **5 consciousness ants** (gaze inward at the self):
  `ant_self_model_accuracy` (FIRST ALERT-capable),
  `ant_swarm_inventory_drift`, `ant_treasury_health`,
  `ant_legion_doctrine_health` (SECOND ALERT-capable),
  `ant_brain_map_freshness`.
- 4 legion modules extended (cognitive 2→7, performance 2→3,
  trajectory 2→4, docs 3→5); **no new legions** (Hydra-9
  preserved). Total cohort **18 → 28**.
- legio_trajectory now uses all three TRIPLEX_ACIES tiers:
  T1 ship_burst → T2 journal_silence + recent_churn → T3
  changelog_gap.
- legio_docs T2 gains swarm_inventory_drift; T3 gains
  unbumped_version.
- 2 new G-guards:
  - **G17** — acceleration ants are read-only with respect to
    source files (no write opens, no `Path.write_*`, no
    `os.replace`/`os.rename`/`shutil` mutation).
  - **G18** — consciousness ants observe swarm self-state
    (registries, meta docs, FS-AoR rolls), never runtime
    pheromones. Preserves the ant/citizen architectural
    boundary.
- `ALL_ANTS` grew 18 → 28; `__all__` and ALL_ANTS list updated.
- 7 new structural-invariants in `TestArcEE10Cohort` (134 → **141**).
- TIME_DEPENDENT exclusion set in `test_legion_deploy_is_deterministic`
  extended with the four new time-using ants.

**Architectural decision:** the Sanctum explicitly REJECTED
creating new legions (Legio Velocitas / Legio Conscientia) on
the grounds that Hydra-9 mythology must be preserved per the
v8.65 commitment. The 10 ants distribute into existing legions
whose domain they naturally serve. `legio_cognitive` becomes
the project's self-monitoring HUB (7 ants, 5 of which observe
the swarm itself).

**First ALERT-capable ants.** The 100-year report observed 0
ALERTs in 100 years; both E10 consciousness ants are designed
to fire ALERT when the swarm's self-CLAIMS diverge from its
self-REALITY. `ant_legion_doctrine_health` deliberately uses
filesystem introspection (not `from polaris_swarm.legions
import`) to preserve G11 verbatim.

**Pacing decision:** the Architect cautioned that collapsing
Phase 1 (6 ants) + Phase 2 (4 ants) into a single mega-ship
contradicts the multi-day pacing established for Arc F. VANTA
chose Option D ("Ship all 10 ants in one mega-ship today")
explicitly, accepting the risk. After E10 ships, the prior
Arc F sequence holds (F2 → F3 → F4).

- **Mission link:** Arc E done-list item E10
- **Risk class:** MEDIUM (10 new ants in one ship; 2 new
  G-guards; structural-invariant expansion; doctrine extension
  in 4 legions)

### ✅ R13-9. Post-100-year-architect refinements (`v8.67`)

**Sanctum-authorized:**
`sanctum/2026-05-13-civitas-100-year-architect-report.md`.
VANTA asked the Architect to run the civitas across 100 simulated
years and report with recommendations. Three primary
recommendations surfaced; VANTA ratified R1 + R2 + one minor
refinement.

**Shipped:**

- **R1: Heartbeat pheromones** — proof-of-deployment layer in
  `colony.py`. One heartbeat per actually-deployed ant per pass
  (intensity=0.5, half-life=24h, observation_type=heartbeat).
  Citizens filter via `_is_heartbeat()`. The bloom now
  distinguishes silent-and-deployed from silent-and-not-deployed.
- **R2: Augur threshold lowered 3 → 2** in
  `civitas/augur_bloom_reader.py`. Convergence detection now
  reachable at the actual swarm scale.
- **Eques INTERESTING_PAIRS expansion** in
  `civitas/eques_correlator.py`: added Mission+Trajectory and
  Cognitive+Trajectory.
- 3 new structural-invariants in `TestHeartbeatPheromones`
  (127 → 130 total).
- **R3 (Cursus Honorum / reputation) deferred** per Architect's
  recommendation; needs ≥30 days of heartbeat-distinguished
  operation before promotion-on-signal-volume becomes safe.

**First post-ship run produced exactly the predicted Eques
correlation:** `legio_mission and legio_trajectory both fired
within 6h` — the dominant-signal correlation pair the 100-year
simulation predicted.

- **Mission link:** Arc E done-list item E9
- **Risk class:** LOW (additive heartbeat + threshold tuning;
  preserves all G1-G14 guards)

### ✅ R13-8. Civitas — civilian classes (`v8.66`)

**Sanctum-authorized:**
`sanctum/2026-05-13-arc-e-civitas-civilian-classes.md`.
VANTA: *"we need probably peasant class / worker class / upper
class ants… use roman civilization as a metaphor."* The Roman
metaphor expands beyond legions; Polaris becomes a full Civitas.

**Shipped:**

- `polaris_swarm/civitas/` — new parallel hierarchy to legions
- 4 citizen modules: PlebsForumWatcher, EquesCorrelator,
  AugurBloomReader, CensorRollKeeper
- `polaris_swarm/civitas/census-roll.json` — filesystem-AoR
  (2nd filesystem-AoR instance after `sanctum/`)
- `colony.py` refactored: `run_swarm()` two-phase deployment;
  `run_colony()` preserved for Phase 1 only
- `meta/civitas.md` — complete Polaris-as-Civitas mapping
- G12-G14 architectural guards
- 5 new structural-invariants (`TestMyceliumCivitas`; 122→127)

**Proposal-driven autogenesis:** the Roman ratification pattern.
Citizens deposit `proposal_new_ant` pheromones; operators ratify
by materializing real ant files. Literal autogenesis is
forbidden (G13).

- **Mission link:** Arc E done-list item E8
- **Risk class:** HIGH (new parallel abstraction; constitutional
  G12-G14; refactored colony runner; preserves all four
  principles and G6-G11)

### ✅ R13-7. Hydra nine-heads completion (`v8.65`)

**Sanctum-authorized:**
`sanctum/2026-05-13-arc-e-hydra-nine-heads-completion.md`.
VANTA: *"the hydra has 9 heads not 7 ,, we need 2 more."*
The canonical Lernaean Hydra (Apollodorus) has nine heads, one
immortal. v8.65 promotes Mycelium to nine Legions and recognizes
CM as the immortal 10th head (narrative only).

**Shipped:**

- Two new legions:
  - `legio_substrate` (Legatus Dependentia) — CUNEUS doctrine
  - `legio_docs` (Legatus Memoria) — TRIPLEX_ACIES doctrine
- Six new ants (12 → 18 total):
  - **Substrate cohort**: ant_substrate_catalog (LEAD),
    ant_dependency_in_use, ant_rust_toolchain
  - **Docs cohort**: ant_docs_structure (T1), ant_readme_counts
    (T2), ant_devnotes_ships_coverage (T3)
- `ALL_LEGIONS` extended 7 → 9
- `test_legion_count_matches_seven` renamed →
  `test_legion_count_matches_nine`
- MISSION.md Arc E gains E7 ✅ + the **immortal 10th head**
  paragraph mapping CM to the deathless head of the myth
- substrate.md gained D3 + anthropic entries (real drift the
  new ants surfaced on first scan)

**Self-calibration:** the 8th instance of the pattern. First
post-ship colony run produced 5 genuine drift findings; mid-ship
fixes folded in (substrate.md updated, ant_dependency_in_use
first-party allowlist extended, ant_done_list_arithmetic Arc E
fallback updated).

- **Mission link:** Arc E done-list item E7
- **Risk class:** MEDIUM (constitutional count change 7→9;
  preserves all four principles + G6-G11)

### ✅ R13-6. Legion structure with Roman tactics (`v8.64`)

**Sanctum-authorized:**
`sanctum/2026-05-13-arc-e-legion-structure-with-tactics.md`.
VANTA observed in chat that each HYDRA watcher is structurally a
Roman general; the 12 Phase-2 ants were domain-themed but
organizationally homeless. R13-6 introduces the **Legion**
construct — 7 Legions (one per HYDRA watcher domain) each
commanded by a Legatus, each operating under one of 5 Roman
tactical doctrines.

**Shipped:**

- `polaris_swarm/legions/base.py` — `Legion` ABC + `Tactic` enum
  + `TacticConfig` dataclass + 5 dispatcher functions
  (`_deploy_testudo`, `_deploy_triplex_acies`, `_deploy_cuneus`,
  `_deploy_vexillatio`, `_deploy_auxilia`).
- 7 legio modules: legio_schema, legio_cognitive, legio_security,
  legio_mission, legio_adversary, legio_performance,
  legio_trajectory. Each declares its NAME / DOMAIN / LEGATUS /
  ANTS / TACTIC.
- `polaris_swarm/colony.py` refactored to iterate `ALL_LEGIONS`;
  AoR preserved (`deposited_by` = ant.NAME; legion in evidence
  JSONB).
- `scripts/ai_swarm_bloom.py` gained `--by-legio` grouping mode.
- `TestMyceliumLegions` (5 tests; 117 → **122 total**): G10
  partition contract, G11 reverse-knowledge contract, count == 7,
  TacticConfig validation, dispatch determinism.

**Recruitment authority:** within Arc E, a Legatus can add ants
to its cohort without requiring a separate Sanctum, as long as
G6-G11 still pass. The partition contract enforces correctness
automatically.

**Default tactic per legion:**

| Legion | Tactic |
|---|---|
| Legio Schema | TESTUDO |
| Legio Cognitive | TESTUDO |
| Legio Security | TESTUDO |
| Legio Mission | TESTUDO |
| Legio Adversary | CUNEUS (lead = walk-completeness ant) |
| Legio Performance | TESTUDO |
| Legio Trajectory | **TRIPLEX_ACIES** (hastati=ship_burst, principes=journal_silence) |

- **Mission link:** Arc E done-list item E6
- **Risk class:** MEDIUM (structural reorg under Arc E; preserves
  all four principles, G6-G9 unchanged, adds G10-G11)

---

## v15 — Arc G, Roman Empire opening (active multi-day, opened 2026-05-13)

Authorized by
`sanctum/2026-05-13-arc-g-roman-empire-opening.md`. VANTA's
Option C choice overrode the Architect's recommendation; the
brief's §III–§V cautionary readings remain on record. Phase 1
ships today; Phases 2 and 3 deferred to future Sanctums per VANTA's
own phasing in the original proposal.

### ✅ R15-1. Phase 1 foundations (`v8.71`)

**Sanctum-authorized:** override-style — the Architect
recommended Option A (decline today; revisit with operational
data); VANTA chose Option C (ship Phase 1 in full). The
Hydra-9 mythology is amended: 9 Republican legions + N Imperial
legions, CM still the immortal 10th head.

**Shipped:**

- **Legio Praetorian (TESTUDO)** — constitutional guard:
  - `ant_mission_drift` (ALERT-capable) — MISSION.md anchor +
    C1-C10 presence
  - `ant_principle_invariant` (ALERT-capable) — implementation
    presence of the four principles
- **Legio Engineer (CUNEUS)** — development acceleration above
  source layer (deliberately scoped to NOT duplicate v8.69 / E10):
  - `ant_build_freshness` (lead) — build artifacts, Rust target,
    vendored-asset drift, `__pycache__` orphans
  - `ant_release_velocity` (follower) — long-term cadence
    characterization (stagnation / burst / median gap)
- **TribuniPlebisWatcher** (new 6th citizen class) — usability
  advocate, observing command/doc drift, CLAUDE.md complexity,
  and Sanctum-protocol entropy.
- **Via Appia** — `priority: bool` field on AntFinding +
  bloom-renderer 1.5× multiplier. Auto-promotes for ALERT-kind
  and intensity ≥7.0.
- **G-guards G21–G25** — Praetorian-observes-constitutional;
  Tribuni-observes-usability; Via-Appia-is-property;
  new-legions-require-Sanctum; cohort-growth-50%-requires-Sanctum.
- 12 new structural-invariants in `TestArcGRomanEmpire`
  (150 → **162 total**).

**The Hydra-9 amendment:** `polaris_swarm.legions` now exposes
`REPUBLICAN_LEGIONS` (the 9 mortal Hydra heads, fixed at 9) and
`IMPERIAL_LEGIONS` (Arc G+ additions, grows by Sanctum). `ALL_LEGIONS`
is the union. The v8.65 mythological commitment is preserved as
the Republican-legion floor; the Empire metaphor is honored via
the parallel registry.

**Tribuni Plebis fires immediately on its first run:** detects
**13 Sanctums opened on 2026-05-13** (today), flagging it as the
highest-friction day in project history. The very ship that
authorized the Tribuni surfaces this signal. The signal is real;
the Architect's pacing-caution from the override Sanctum §V is
empirically corroborated by the new citizen class.

- **Mission link:** Arc G done-list item G1
- **Risk class:** HIGH (Hydra-9 amendment; 5 new G-guards;
  Empire-pattern infrastructure shipped against Architect's
  Option A recommendation)

### ⬜ R15-2. Phase 2 projection (deferred)

Legio Tribune (external stakeholder advocacy), Legio Gladiator
(permanent adversarial arena / spike detector), Cursus Honorum
behavioral activation (R3 from 100-year report — needs 30 days
of operation), Lares et Penates (module-level guardians; the
100-year-report antipattern named by the Architect), Pomerium
dynamic enforcement.

- **Architect's recommendation:** Phase 2 items require
  empirical justification ≥40% firing rate (VANTA's own metric)
  on Phase 1 units before earning a ship. The Architect's §III
  brief named most of Phase 2 as either premature or
  micro-redundant; if shipped, each item earns its own Sanctum.
- **Mission link:** Arc G done-list item G2
- **Risk class:** MEDIUM-to-HIGH (per item)
- **Earliest ship:** TBD — gated on operational data

### ⬜ R15-3. Phase 3 empire (deferred indefinitely)

Senate voting mechanics, provincial governor pattern, Mos
Maiorum v2, Vestal Virgins, Decline & Fall graceful degradation
protocol.

- **Architect's strong opinion:** these items require Polaris
  to have grown materially in scale (multiple operators,
  external partners via Arc B/C, persistent legions with
  competing interests). Today none of those conditions exist.
- **Mission link:** Arc G done-list item G3
- **Risk class:** HIGH (introduces governance, complexity,
  potential constitutional drift)
- **Earliest ship:** indefinite; revisit at Arc B/C openings

---

## v14 — Arc F, the Denarius / economic dimension (active, opened 2026-05-13; reopened with F5 amendment)

Authorized by `sanctum/2026-05-13-arc-f-denarius-opening.md`.
After the 100-year + 100-day Architect reports, VANTA opened the
economic dimension. *Money makes the world go round* — and in
Polaris terms, the denarius is the substrate that lets us
distinguish ants whose pheromones lead to drift resolution
from ants whose pheromones decay unread.

The arc is **explicitly multi-day**. Phases F2-F4 each earn
their own Sanctum and ship no sooner than the previous phase
plus an explicit cooldown.

### ✅ R14-5. Steady-state ants reward exemption (`v8.73`)

**Sanctum-authorized:**
`sanctum/2026-05-13-arc-f-f5-steady-state-ants-reward-exemption.md`.
The empirical case from the 100-year post-v8.72 simulation
(`sanctum/2026-05-13-civitas-100-year-post-v8-72-report.md` §V/R1):
no ant reached Eques in 100 simulated years; the F4 Cursus
Honorum multipliers were behaviorally unreachable because most
v8.69+ ants emit steady-state observations that never "resolve."

**Shipped:**

- `polaris_swarm/civitas/treasury.py`: `STEADY_STATE_ANTS`
  frozenset (9 ants) + revised `compute_rewards()` that skips
  both reward AND penalty events for allowlisted ants.
- Allowlist contents: `ant_recent_churn`, `ant_changelog_gap`,
  `ant_ship_burst`, `ant_release_velocity`, `ant_test_gap`,
  `ant_todo_debt`, `ant_pattern_warmth`, `ant_stale_script`,
  `ant_unbumped_version`.
- **G26** (new) — additions to `STEADY_STATE_ANTS` require
  Sanctum authorization. Enforced structurally:
  `test_g26_allowlist_matches_sanctum_enumeration` cross-checks
  the in-code allowlist against the F5 Sanctum's enumeration.
- 6 new structural-invariants in `TestArcFF5SteadyStateExemption`
  (168 → 174 total).

**G15 + G16 preserved.** Existing treasury events stay as
recorded; only future computations exempt the allowlist.
`compute_rewards` remains a pure function — same input still
yields same output. Allowlisted ants' historical (negative)
balances stay where they are per audit-of-record discipline.

**Verification:** five-scenario replay confirms the design —
drift-class ants still receive +10/−2 events; steady-state ants
receive zero; determinism holds.

- **Mission link:** Arc F done-list item F5
- **Risk class:** MEDIUM (amends the F1 reward function; touches
  the core compute_rewards path; preserves G15 + G16)

### ✅ R14-1. Treasury + Quaestor + drift-resolution rewards (`v8.68`)

**Sanctum-authorized:**
`sanctum/2026-05-13-arc-f-denarius-opening.md`.
Phase F1 of Arc F. The economic substrate for the Civitas.

**Shipped:**

- `polaris_swarm/civitas/treasury.py` — denarii ledger helpers,
  reward function (`compute_rewards`), property-class
  classifier
- `polaris_swarm/civitas/quaestor_treasurer.py` — the 5th
  citizen, financial magistrate
- `polaris_swarm/civitas/treasury-roll.json` — filesystem-AoR
  ledger (3rd FS-AoR instance after sanctum/ + census-roll.json)
- `ALL_CITIZENS` extended 4 → 5; `test_civitas_count_matches_four`
  renamed `..._matches_five`
- 4 new structural-invariants in `TestArcFDenarius` (130 → 134)
- New G-guards: **G15** (treasury filesystem-AoR), **G16** (reward
  function deterministic)
- `meta/denarius.md` — complete economic-dimension doc

**Reward function:** drift-resolution rewards.

| Event | Effect |
|---|---|
| Drift resolved (fingerprint present-then-absent) | +10 denarii |
| Persistent silence (fingerprint ≥3 passes) | −2 denarii |
| Volume (more pheromones) | 0 denarii (neutral) |

**Goodhart's Law mitigation by design:** the function rewards
signal, not volume.

**First-pass behavior demonstrated:** Quaestor silent on first
pass (no last_pass_fingerprints to compare); treasury-roll.json
populated with this pass's 5 fingerprints; future passes will
detect resolutions (when project state changes) or persistent
silences (after 3 unchanged passes).

- **Mission link:** Arc F done-list item F1
- **Risk class:** MEDIUM (new citizen + new FS-AoR; preserves
  C10 — denarii are swarm currency, not identity currency)

### ✅ R14-2. Chaos test for silent ants (`v8.70`)

**Sanctum-authorized:**
`sanctum/2026-05-13-arc-f-accelerated-pacing-override.md`.
VANTA collapsed multi-day F2/F3/F4 pacing into one ship via
Option B; the Architect cautioned about state-dependencies and
VANTA accepted.

**Shipped:**

- `polaris_swarm/chaos.py` — deterministic harness with four
  FailureMode variants (RAISE_EXCEPTION, RETURN_MALFORMED,
  RETURN_SILENT, RETURN_INFLATED), `ChaosInjector` wrapper,
  `run_chaos_pass()` runner, `ChaosResult` dataclass.
- 3 new structural-invariants in `TestArcFAcceleratedPacing`
  verify harness existence + heartbeat-suppression detection +
  spike-detector-gap surfacing.

**Architectural finding:** 3 of 4 failure modes are caught by
existing detection layers (heartbeat suppression for
crashes/malformed; treasury fingerprint loss for silence).
**Spike detection is the architectural gap** — there is no
detector for an over-producing ant. F2 surfaces this gap
structurally; a future ship may add a spike detector.

- **Mission link:** Arc F done-list item F2
- **Risk class:** LOW (test infrastructure; no constitutional
  changes)

### ✅ R14-3. Cohort growth via proposal exercise (`v8.70`)

**Sanctum-authorized:** same Sanctum as R14-2.

**Shipped:**

- `AugurBloomReader` extended with `_observe_uncovered_namespaces()`
  — scans WATCHED_NAMESPACES (today: `proposals/`); when a
  namespace has ≥3 files and zero ant coverage, emits
  `proposal_new_ant` via the v8.66 G13 helper.
- `ant_proposal_stagnation` materialized — the first ant
  ratified through the proposal-driven autogenesis loop.
  Surfaces proposals/*.md files ≥30 days stagnant; three
  severity tiers (shipped-but-lingers, scheduled-but-untouched,
  genuinely-stagnant). Lands in legio_trajectory T2 (proposal
  stagnation is a pacing signal, sibling to journal_silence
  and recent_churn).
- ALL_ANTS: 28 → 29.
- 3 new structural-invariants verify registry placement +
  Augur proposal emission + loop closure once coverage exists.

**The G13 proposal-driven autogenesis loop is now closed
end-to-end for the first time in cohort history.** Future
proposals will follow the same path: Augur observes uncovered
namespace → emits proposal_new_ant → operator ratifies →
Architect materializes → ant joins legion → Augur stops
proposing for that namespace.

- **Mission link:** Arc F done-list item F3
- **Risk class:** MEDIUM (exercises G13 mechanism for the first
  time; ratification recorded in the override Sanctum)

### ✅ R14-4. Cursus Honorum activation (structural) (`v8.70`)

**Sanctum-authorized:** same Sanctum as R14-2.

**Shipped:**

- `treasury.CURSUS_MULTIPLIER = {pleb: 1.0, eques: 1.5, patrician: 2.0}`.
- `multiplier_for(balance)` + `multiplier_for_ant(roll, name)`
  + `is_sanctum_chair_eligible(roll, name)` +
  `patrician_ants(roll)` — the F4 public surface.
- `SANCTUM_CHAIR_MIN_DENARII = 10_001` (patrician threshold).
- `scripts/ai_swarm_bloom.py::render_top_nodes()` consults the
  treasury per-ant; applies multipliers to effective intensity
  before aggregation. Backward-compatible: omit `root` → 1.0×
  multipliers everywhere (pre-F4 behavior).
- **G19** — multipliers are monotonic non-decreasing in
  balance (pleb ≤ eques ≤ patrician). Enforced structurally.
- **G20** — Sanctum-chair eligibility derives ONLY from denarii
  balance; never from Polaris identity-layer attributes. C10
  (pomerium) preserved. Enforced by a source-scan test
  forbidding identity-symbol references in treasury.py code.
- 3 new structural-invariants verify G19 monotonicity + G20
  strict-civitas + the 29-ant count from F3.

**Behaviorally inert today** — max positive ant balance is 76
denarii; every ant is pleb; every multiplier is 1.0×; no ant is
Sanctum-chair eligible. **As denarii accumulate through real
drift-resolution operation, the multipliers engage
automatically; no further code ship is needed for F4 to "go
live."** Operation time is the only remaining variable.

- **Mission link:** Arc F done-list item F4
- **Risk class:** MEDIUM (introduces intensity weighting + new
  eligibility predicate; structural readiness, not behavior
  change in v8.70)

---

## v16 — Arc B, Production deployment (active multi-phase, opened 2026-05-14)

Production-readiness arc. Opened by VANTA's heavy-production
directive on 2026-05-14, authorized via
`sanctum/2026-05-14-steady-state-revocation-heavy-production.md`
and `sanctum/2026-05-14-arc-b-production-deployment-opening.md`.

Phase 1 closes the gap between Polaris's architectural sophistication
and its production-deployability. The full strategic record lives in
`meta/arc-b-production.md`.

### ✅ R16-1. Operator runbook + secrets primer (`v8.77`)

**Shipped:** `docs/operator/OPERATIONS.md` (~700 lines: quick start,
pre-deploy checklist, deploy, verify, day-2 ops, backup, scaling,
monitoring, incident response, upgrades, decommissioning) +
`docs/operator/SECRETS.md` (~400 lines: 7-secret matrix, generation
recipes, rotation cadence, leak prevention, threat-model summary).

- **Mission link:** Arc B done-list (Phase 1)
- **Risk class:** LOW

### ✅ R16-2. Production Docker stack (`v8.77`)

**Shipped:** `Dockerfile.prod` (multi-stage: Rust ZK builder + Python
deps builder + Debian-slim runtime, non-root, tini entrypoint,
structured healthcheck) + `docker-compose.prod.yml` (Caddy + app +
Postgres 16 + Redis 7; file-mounted secrets; internal network with
only Caddy exposing ports).

- **Mission link:** Arc B done-list (Phase 1)
- **Risk class:** MEDIUM

### ✅ R16-3. TLS + security headers (Caddyfile) (`v8.77`)

**Shipped:** Caddyfile declaring `{$POLARIS_DOMAIN}` site block
(triggers Let's Encrypt auto-issuance) + HSTS / X-Frame /
X-Content-Type / Referrer-Policy / Permissions-Policy headers +
edge rate-limit + HTTP→HTTPS redirect + h1/h2/h3.

- **G27 added:** Production requires TLS. Enforced structurally.
- **Mission link:** Arc B done-list (Phase 1)
- **Risk class:** MEDIUM

### ✅ R16-4. Structured `/api/health` (`v8.77`)

**Shipped:** Rewrote `/api/health` from the v7.5 prototype to the
G29 contract — `{status, version, uptime_seconds, checks: {database,
redis, zk_binary, disk}, timestamp}`. Each component carries its own
status; overall = worst per-component status. HTTP 503 on
`unhealthy`, 200 otherwise.

- **G29 added:** Structured-JSON contract enforced structurally.
- **Mission link:** Arc B done-list (Phase 1)
- **Risk class:** LOW

### ✅ R16-5. File-mounted secrets (`v8.77`)

**Shipped:** `_read_secret_file()` helper in `app.py` reads
`POLARIS_*_FILE` env vars (preferred) before falling back to direct
env vars. Production compose mounts `./secrets/*` at
`/run/secrets/` (mode 0600) and sets `POLARIS_SECRET_KEY_FILE` +
`POLARIS_DB_PASSWORD_FILE`. `polaris-generate-secrets.sh` +
`polaris-rotate-secret.sh` complete the lifecycle.

- **G28 added:** No sensitive env-var literals in production
  compose. Enforced structurally.
- **Mission link:** Arc B done-list (Phase 1)
- **Risk class:** MEDIUM

### ✅ R16-6. Idempotent deploy script (`v8.77`)

**Shipped:** `scripts/polaris-deploy.sh {dev|staging|prod}` with
pre-flight checks, git pull, image refresh, build, stack up,
30-attempt smoke against `/api/health`, and rollback-to-prior-image
on failure.

- **Mission link:** Arc B done-list (Phase 1)
- **Risk class:** LOW

### ✅ R16-7. Atomic backup script (`v8.77`)

**Shipped:** `scripts/polaris-backup.sh` produces a single
timestamped tarball with `pg_dump` (custom), `sanctum/`, `journal/`,
`treasury-roll.json`, `census-roll.json`, `meta/sanctum-index.md`,
and a `MANIFEST.json` with SHA-256 hashes. `--verify-latest` mode
re-hashes the newest backup to detect bit-rot.

- **Mission link:** Arc B done-list (Phase 1)
- **Risk class:** LOW

### ✅ R16-8. Structural invariants for the deploy stack (`v8.77`)

**Shipped:** `TestArcBProductionDeploymentStack` (8 tests):
deploy-stack-files-exist, G27 TLS, G28 no-env-secrets, G29 health
contract, Dockerfile-prod non-root, Caddyfile security headers,
deploy-scripts executable, secrets-dir gitignored.

- **Mission link:** Arc B done-list (Phase 1)
- **Risk class:** LOW

### ✅ R16-9. Strategic record + cross-references (`v8.77`)

**Shipped:** `meta/arc-b-production.md` (strategic record), MISSION.md
Arc B section, this v16 ROADMAP section, CLAUDE.md state-map row,
sanctum-index entry, journal entry for 2026-05-14.

- **Mission link:** Arc B done-list (Phase 1) + audit-of-record (v8.20)
- **Risk class:** LOW

### ⬜ R16-10. Phase 2 / Phase 3 deferred items

Scoped to Phase 2 (open via fresh VANTA directive or
Architect-surfaced gap after Phase 1 soak):

- WebAuthn + hardware-token operator auth
- Audit-log archive policy (S3 / Glacier rotation)
- Multi-instance scaling (pgbouncer + gunicorn tuning + Redis cluster)
- `polaris-restore.sh` recovery-from-backup with validation

Scoped to Phase 3:

- Multi-region deployment patterns
- Disaster-recovery runbook with RPO/RTO targets
- SOC 2 readiness checklist

---

## Post-freeze candidates (surfaced 2026-05-17 polish pass)

### ✅ Archive-extension Sanctum (CHANGELOG aging-out mechanism) — **DONE in v9.38**

Shipped 2026-05-17 in v9.38 via
`sanctum/2026-05-17-changelog-archive-extension.md`. Amendment:
archive grows APPENDS-only (no edits/deletions of existing rows).
v9.24–v9.27 moved byte-identical from CHANGELOG.md to a new
"Post-v9.24 ships" section in archive/CHANGELOG-FULL.md.
test_changelog_compressed cap restored from 14 → 11. Future
agings-out follow the same pattern.

### ⬜ Apparatus-reduction Sanctum (sanctum-scope cut-deeper signal)

`polaris-sanctum-status` reports ratio 0.29 (14 core / 48 apparatus
ACTIVE) — APPARATUS-DOMINANT, "cut deeper" trigger fired since v9.29.
This is its own HIGH-risk Sanctum: identify SUPERSEDED-but-not-marked
sanctums and apparatus sanctums whose decisions have been embodied as
invariants, transition them to SUPERSEDED, observe whether ratio
improves.

- **Justification under freeze:** (b) Measurement — the sanctum-status
  scorecard is part of the cognitive-loop earning measurement; reducing
  apparatus weight without losing audit-of-record is a measurement
  refinement, not new scope.
- **Risk:** HIGH (touches every Sanctum file's classification + the
  ratio definition itself).
- **Cost:** requires careful walk-through of all ACTIVE sanctums; AP2
  would fire if opened without execution intent. Defer until a
  dedicated session.
- **Surfaced by:** 2026-05-17 polish pass joint Architect ↔ Anti-
  Architect review (Class C item).

---

## Process notes

- Items move from `docs/BACKLOG.md` → ROADMAP.md when they have mission
  alignment + risk class + effort estimate + acceptance criteria.
- Items leave the roadmap by being done (move to CHANGELOG) or by
  being formally rejected (move to `meta/rejected.md` with rationale).
- The roadmap is checked at the start of every agent session via
  `scripts/ai-status.sh`. If the roadmap is older than 30 days
  without movement, that's a flag.
