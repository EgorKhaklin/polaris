# ROADMAP.md — where Polaris is going

<!-- ============================================================ -->
<!-- LIVING BACKLOG. Newest priorities first. Continuously updated -->
<!-- each session (per the 2026-06-03 heavy-production directive:  -->
<!-- "create a future roadmap ... constantly updated with ideas"). -->
<!-- Add new ideas here as they arise; move to the prioritized     -->
<!-- backlog below when adopted as an R-id; never delete shipped   -->
<!-- history (audit-of-record).                                    -->
<!-- ============================================================ -->

## 🔭 OPEN NOW — living backlog (updated 2026-06-03, v9.55)

Tagging: `effort(XS/S/M/L) · value · risk · category`. As of v9.55 the
cognitive apparatus was removed; the live invariant layer is
[`polaris_checks/`](polaris_checks/), gating CI via
`python3 -m polaris_checks.run`. Add new ideas here as they arise; move
to the prioritized backlog below when adopted as an R-id.

**Flagged for VANTA (decision required):**

- **[VANTA] THESIS v9.40 terminus has passed unactioned.** MISSION.md
  says the strong "agent-maintainable production identity system" claim
  *retires permanently* if no external cold-read occurs by v9.40. We are
  past v9.40 with only the system's own walkthrough, never an external one,
  yet `docs/THESIS.md` still uses the softer conditional "RETIRED *until*
  evidence supports it." Leaving the softer wording past the deadline is
  itself the dishonesty the project's discipline forbids. Two honest moves,
  both VANTA's call: (a) reflect the permanent terminus ("has not been
  independently validated") and pin it with a check, or (b) amend the
  deadline via Sanctum plus freeze-amendment-protocol. `S · high · MEDIUM · cold-read-evidence`

**Next ships:**

1. **[PARTIAL] Wire suites into CI.** Done: the ZK two-witness
   differential plus `witness2/` self-tests plus `polaris_checks` now gate
   CI, and `pytest` is in `requirements.txt`. **Still open:** wire
   `test_app.py` plus `test_cli.py` (DB-backed) once confirmed green against
   the CI sample DB, deferred because they are not verifiable from the local
   env (no psycopg2). `S · high · LOW · measurement`
2. **[PARTIAL] PQC lone verifier** — `pqc_signing.py` is an integration
   island: `app.py` never imports it, `uc1_issue` never calls `sign()`.
   **Still open (deferred):** a full independent ML-DSA-65 second witness,
   premature while the path is OFF by default and unwired; revisit when it
   goes live. `L · medium · MEDIUM · hardening`
3. **ZK anonymity set is demo-scale (`TREE_DEPTH=4`, ≤16 leaves).** Re-run
   the circuit setup at `TREE_DEPTH=14` (16,384 leaves) for a realistic set;
   the second witness already generalizes. `L · medium · MEDIUM · hardening`
4. **PQC-posture audit** — audit Polaris against NIST PQC
   migration timelines; surface gaps. `S · low · LOW · cold-read-evidence`
5. **CI: bump deprecated GitHub Actions before the deadline.** Live CI annotation:
   `actions/checkout@v4` plus `actions/setup-python@v5` run on Node.js 20,
   which GitHub force-migrates to Node 24 on **2026-06-16** and removes on
   **2026-09-16**. Bump to current major versions before then.
   `XS · low · LOW · hardening`

---

This file is the prioritized backlog. Each item has:

- **Mission link** — which item in `MISSION.md`'s done-list this
  advances (or which constraint it strengthens)
- **Risk class** — `LOW` (autonomous-eligible), `MEDIUM` (propose-and-
  wait), `HIGH` (explicit human approval required)
- **Effort estimate** — rough magnitude
- **Acceptance criteria** — how we know it's done

---

## What needs done before it can become a deployable system

VANTA's deployability checklist (2026-05-14). The base three lines are the
operator-facing summary; the indented items name the concrete
deferred work each phase carries. Add to this section when a
genuinely new gap is surfaced; never silently delete (the
checklist is itself audit-of-record).

### ✅ Phase 1 — production deployment shipped

Shipped across v8.77 (Arc B Phase 1) → v8.81 (Phase 1.5) →
v8.83/v8.84/v8.87/v8.88 (Phase 2 foundations). The system can be
deployed to a single Linux host behind TLS, with secrets handled
correctly, structured monitoring, manifest-verified backup/restore,
and audit-log archive+purge.

- **TLS** via Caddy + Let's Encrypt auto-issuance
- **File-mounted secrets** via Docker secrets + `*_FILE` env vars
- **Structured `/api/health`** with per-component checks
- **Backup** with manifest-hashed tarball (`polaris-backup.sh`, v8.77)
- **Restore** with verify mode + force-required guard (`polaris-restore.sh`, v8.81)
- **Audit-log archive** export-only, C1-preserving (`polaris-archive.sh`, v8.84)
- **Audit-log purge** under constitutional carve-out + `LifecycleArchiveCheckpoint` (`polaris-purge.sh`, v8.87)
- **pgbouncer** connection pooling foundation (v8.83)
- **PostGIS** schema foundation, optional-dependency (v8.88)
- **Operator runbook** `docs/operator/OPERATIONS.md` (~1000+ lines)
- **Secrets primer** `docs/operator/SECRETS.md`
- **Public landing + demo** at `/` and `/demo` (v8.79)
- **Quick start**: `./scripts/polaris-generate-secrets.sh && export POLARIS_DOMAIN=… && ./scripts/polaris-deploy.sh prod`

### ⬜ Phase 2 — still deferred

VANTA-named:

- ✅ **WebAuthn operator auth** *(shipped v8.97)* — Position B (WebAuthn-MFA) from [sanctum/2026-05-14-webauthn-operator-auth.md](sanctum/2026-05-14-webauthn-operator-auth.md). Migration `2026-05-14-002-operator-webauthn` (first non-example migration; validates the v8.95 framework on a real schema change) adds `OperatorWebauthnCredential` + `AppUser.webauthn_required_after` + 5 new AuthAuditLog event types. `polaris_web/webauthn_auth.py` + 7 new routes in `app.py` handle registration + assertion ceremonies via the Duo Labs `webauthn` package. Login flow modified for grace_period / mfa_required / mfa_overdue states. `scripts/polaris-recover-admin.sh` (second-admin pairing) + `scripts/polaris-generate-recovery-code.sh` (printed mnemonic) handle recovery. `polaris-create-operator.sh` sets 30-day deadline for new admin accounts. threat-model § T-S4 + SECRETS.md § 7 + OPERATIONS.md §Operator authentication document the operator runbook. 10-step end-to-end drill + round-trip enrollment drill green.
- ✅ **Audit log rotation** *(shipped v8.93)* — `scripts/polaris-rotate-logs.sh` wraps `polaris-archive.sh` + verify + `polaris-purge.sh` in one cron-ready pipeline. 5-year default cutoff per Sanctum §V. Cron recipe in OPERATIONS.md. Greppable exit codes for incident response.
- **Multi-instance scaling completion** — Phase 2.5 work: read replica routing via Caddy/HAProxy; Redis Sentinel or Cluster topology; PostGIS Phase 2 atlas function rewrite (`atlas_clusters_*` / `atlas_points_*` gain a `CASE` branch on `pg_extension` presence; ≥3× benchmark at 10M+ events).

Scan additions (2026-05-14):

- ✅ **WAL archiving / point-in-time recovery** *(shipped v8.93)* — pgbackrest paved-path recipe in OPERATIONS.md § "Point-in-time recovery". Full + differential schedule, archive-check cron, restore-to-time procedure. RPO drops from 24h to ~1 minute.
- ✅ **Schema migration framework** *(shipped v8.95)* — Position C (custom polaris-native) from [sanctum/2026-05-14-schema-migration-framework.md](sanctum/2026-05-14-schema-migration-framework.md). `polaris_sql/00_migrations_table.sql` creates the `schema_version` registry (13th audit-of-record); `scripts/polaris-migrate.sh` runs status/up/down/dry-run with SHA-256 tamper detection (exit 6); `polaris_sql/migrations/` holds the hand-written .up + .down SQL pairs; first example migration ships (`2026-05-14-001-idx-checkpoint-recent`). End-to-end drill clean. `docs/operator/OPERATIONS.md` § "Schema migrations (v8.95)" documents the operator workflow. v1.0 production cutover path unblocked.
- ✅ **Prometheus-compatible `/metrics` endpoint** *(shipped v8.93)* — `/metrics` route in app.py via `prometheus_client`. Counters (`polaris_requests_total` by route/method/status; `polaris_verifications_total` by disclosure_level), histograms (`polaris_request_latency_seconds`, `polaris_db_query_latency_seconds`), gauge (`polaris_app_info` version label). Graceful fallback if `prometheus_client` is unavailable. OPERATIONS.md gains scrape-config + alerting-rule examples.
- ✅ **CI/CD pipeline configuration** *(shipped v8.93)* — `.github/workflows/ci.yml` runs the test suite on every push: the `polaris_checks` invariant layer, CHECK regression tests, Hypothesis property tests, ZK crate `cargo test`, bash syntax check, and `ai-link-check --ci`. PostgreSQL 16 service container with the polaris schema loaded.
- ✅ **Encryption-at-rest recipe** *(shipped v8.93)* — OPERATIONS.md § "Encryption at rest" with three operator-pick options (LUKS on bare-metal, TDE on managed Postgres, fscrypt/eCryptfs for per-directory). Verification step. PRIVACY.md cross-references.
- ✅ **Operator onboarding script** *(shipped v8.93)* — `scripts/polaris-create-operator.sh` with werkzeug scrypt password hash (matching `security.py:hash_password`), AppUser format validation (chk_appuser_username_format + chk_appuser_role), AuthAuditLog ACCOUNT_CREATED entry in the same transaction, idempotency guard against duplicate usernames, `--dry-run` mode, `--password-file` for non-interactive use, interactive stty -echo prompt for tty use.

### ⚠️ Phase 3 — Wave 1 shipped v9.01; multi-region + distributed tracing remain deferred

Phase 3 opened 2026-05-14 per [sanctum/2026-05-14-phase-3-opening.md](sanctum/2026-05-14-phase-3-opening.md) (DECIDED + CLOSED, Position A: Wave-1 autonomous-eligible 5 items in one ship). Wave 1 shipped as v9.01 same day.

VANTA-named:

- **Multi-region deployment** ⬜ — read-replicas across regions; failover orchestration; data-locality requirements per jurisdiction. Gating condition: production-deployment-pressure trigger (operator names a real data-locality constraint). Will get its own Sanctum.
- ✅ **Disaster recovery runbook** *(shipped v9.01)* — [`docs/operator/DR.md`](docs/operator/DR.md) (~450 lines): RPO ≤ 1min / RTO ≤ 30min targets named (per Sanctum §IV.1); 8 failure-class procedures; severity matrix (SEV-1/2/3/4); decision tree; on-call playbook; communications templates (status-page snippets + post-mortem template); drill cadence (monthly verify, quarterly restore, half-yearly failover, annual ransomware tabletop).
- ✅ **SOC 2 readiness checklist** *(shipped v9.01)* — [`docs/operator/SOC2.md`](docs/operator/SOC2.md) (~520 lines): TSCs in-scope per Sanctum §IV.2 (Security mandatory + Availability + Confidentiality; Processing Integrity + Privacy out-of-scope as operator-layer); CC1-CC9 mapping table — every common-criteria control mapped to existing C-constraints / scripts that satisfy it; 7 evidence-collection SQL recipes (admin authentications by quarter, schema changes in audit period, token revocations, emergency-password-login authorizations, audit-log purges, append-only enforcement check, WebAuthn-MFA enforcement check); known-limitations section for audit transparency.

Scan additions (2026-05-14):

- **Distributed tracing** ⬜ — OpenTelemetry integration for cross-service request flows. **Gated on Phase 2.5 multi-instance** (deferral note: tracing-without-a-distributed-stack is overhead without payoff; reopens automatically when the second hop exists to trace through).
- ✅ **HSM / KMS integration for secret material** *(shipped v9.01)* — [`docs/operator/SECRETS.md`](docs/operator/SECRETS.md) § 8 (~280 lines added): three operator-pick paved paths per Sanctum §IV.3 (HashiCorp Vault Transit Engine, AWS KMS envelope encryption, GCP Secret Manager); each with install + Polaris integration shape + IAM policy + key-rotation automation + cost notes; comparison matrix; migration recipe from v8.77 file-mounted to KMS-backed (preserves user sessions across the cut).
- ✅ **Penetration test schedule + reporting cadence** *(shipped v9.01)* — [`docs/operator/PENTEST.md`](docs/operator/PENTEST.md) (~280 lines): annual cycle (internal Q1 + external Q3) per Sanctum §IV.4; scope matrix (every STRIDE entry mapped to in/out-of-scope + test approach); remediation SLA (HIGH 30d / MEDIUM 90d / LOW next-cycle); report-archive policy (filesystem AoR + SHA-256 manifest, 7-year retention); vendor evaluation checklist; 12-scenario minimum-tests-per-cycle list; follow-up testing protocol.
- ✅ **Certificate transparency monitoring** *(shipped v9.01)* — [`scripts/polaris-ct-monitor.sh`](scripts/polaris-ct-monitor.sh) (~220 lines): polls crt.sh API for cert-issuance events on ${POLARIS_DOMAIN}; SHA-256 fingerprint allowlist in `$STATE_DIR/ct-monitor/known.txt`; daily 06:00 UTC cron per Sanctum §IV.5; greppable exit codes (0 ok / 4 inconclusive / 5 anomaly); alert sink = file + stderr per Sanctum §IV.5 (operator integrates with their alerting stack); OPERATIONS.md § "Certificate transparency monitoring (v9.01)" documents setup + on-alert procedure.

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
- **Risk class:** LOW (additive docs; no code path change)
- **Effort:** ~1-2 sessions
- **Acceptance:**
  - `MISSION.md`, `ROADMAP.md`, `docs/BACKLOG.md` exist
  - The LOW/MEDIUM/HIGH risk classes are documented
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
  - Tests enforce the optional-dependency guard, idempotency, and
    the GENERATED-ALWAYS-AS-STORED pattern.
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

- **Check added:** Production requires TLS. Enforced by a test.
- **Mission link:** Arc B done-list (Phase 1)
- **Risk class:** MEDIUM

### ✅ R16-4. Structured `/api/health` (`v8.77`)

**Shipped:** Rewrote `/api/health` from the v7.5 prototype to the
structured contract — `{status, version, uptime_seconds, checks:
{database, redis, zk_binary, disk}, timestamp}`. Each component
carries its own status; overall = worst per-component status. HTTP
503 on `unhealthy`, 200 otherwise.

- **Check added:** Structured-JSON contract enforced by a test.
- **Mission link:** Arc B done-list (Phase 1)
- **Risk class:** LOW

### ✅ R16-5. File-mounted secrets (`v8.77`)

**Shipped:** `_read_secret_file()` helper in `app.py` reads
`POLARIS_*_FILE` env vars (preferred) before falling back to direct
env vars. Production compose mounts `./secrets/*` at
`/run/secrets/` (mode 0600) and sets `POLARIS_SECRET_KEY_FILE` +
`POLARIS_DB_PASSWORD_FILE`. `polaris-generate-secrets.sh` +
`polaris-rotate-secret.sh` complete the lifecycle.

- **Check added:** No sensitive env-var literals in production
  compose. Enforced by a test.
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
`meta/sanctum-index.md`, and a `MANIFEST.json` with SHA-256 hashes.
`--verify-latest` mode re-hashes the newest backup to detect bit-rot.

- **Mission link:** Arc B done-list (Phase 1)
- **Risk class:** LOW

### ✅ R16-8. Tests for the deploy stack (`v8.77`)

**Shipped:** `TestArcBProductionDeploymentStack` (8 tests):
deploy-stack-files-exist, TLS-required, no-env-secrets, health
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
a gap surfaced after Phase 1 soak):

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

### ✅ Apparatus reduction — **DONE in v9.55**

Shipped 2026-06-03. The cognitive apparatus (the swarm, the HYDRA
host, the legions, the civitas/Denarius economy, foresight, and the
~50 `ai-*`/`polaris-*` cognitive scripts) was cut wholesale (~52k
lines) and replaced by the flat invariant layer
[`polaris_checks/`](polaris_checks/), one `check_*(repo_root)` per
constraint, gating CI via `python3 -m polaris_checks.run`. The
product (`polaris_sql/`, `polaris_web/`, `polaris_cli/`,
`polaris_zk/`) and the C1-C10 constraints plus the Vocation are
unchanged. The development record (CHANGELOG, journal, sanctum,
archive) is kept as history.

---

## Process notes

- Items move from `docs/BACKLOG.md` → ROADMAP.md when they have mission
  alignment + risk class + effort estimate + acceptance criteria.
- Items leave the roadmap by being done (move to CHANGELOG) or by
  being formally rejected (move to `meta/rejected.md` with rationale).
- The roadmap is read first each session, alongside `MISSION.md`. If it
  is older than 30 days without movement, that's a flag.
