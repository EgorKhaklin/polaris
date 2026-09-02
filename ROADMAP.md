# ROADMAP.md - from reference implementation to national deployment

This is the build plan. It is written to be executed: an agent (or a human) in a
fresh session reads [CLAUDE.md](CLAUDE.md), then this file, picks the first
unblocked item in the active phase, and ships it under the standing ship
discipline. Shipped history lives in [CHANGELOG.md](CHANGELOG.md), not here.

**Decision record.** MISSION.md's v9.32 freeze line limited work to hardening,
measurement, and thesis evidence, and required a named operator trigger to open
a new arc. That trigger occurred: on 2026-08-31 the project owner (VANTA)
directed a complete plan to real national deployment. This roadmap is that
recorded decision. The constitution (C1-C10 and the vocation) is not softened
by it; every phase below carries the constitution as a hard gate, and several
previously retired scope decisions are explicitly reopened here with reasons,
rather than silently.

**Status marks:** `[ ]` pending · `[>]` in progress · `[x]` done ·
`[EXT]` blocked on an external actor (funding, law, vendor, institution).
Update marks in place as part of each ship; never delete rows.

**Sizing:** S (under one session) · M (1-3 sessions) · L (an arc, 3-10) ·
XL (multi-arc). Risk is delivery risk, not security risk.

---

## Where we are (honest inventory, v9.157; items closed since are marked [x] in the phase tables below)

**Have, working, CI-proven:** a 29-table constraint-enforced schema with
append-only audit; 72-route application with WebAuthn operator MFA and the
Atlas; operator CLI; Plonky2 ZK Merkle-inclusion with an independent Python
second witness; real ML-DSA-65 signing two-witnessed (liboqs + OpenSSL);
five-service hardened production stack behind a post-quantum TLS edge
(X25519MLKEM768, proven in CI); pgBackRest backup/restore and streaming
replication, both CI-round-tripped; 77 invariant checks each with a detection
test; CVE gates on dependencies and images; operator tooling for backup,
restore, archive, purge (archive-bound), migrate, account recovery; twelve
operator runbooks; an honest gap ledger in
[docs/PRODUCTION-READINESS.md](docs/PRODUCTION-READINESS.md).

**Do not have:** hardware tokens (the physical artifact is modeled, not built);
holder-facing surfaces (everything today is operator-facing); identity-proofing
evidence flows mapped to NIST 800-63; scale beyond a single node (no
partitioning, no HA automation, no multi-region); a relying-party ecosystem
(no stable public API contract, no SDKs, no conformance suite); offline
verification; status/revocation distribution at scale; inter-authority
federation as deployed topology (the schema supports it; no protocol spec or
second instance exists); key custody beyond files (no HSM/KMS); certified
cryptography (liboqs is not FIPS-validated); artifact signing, SBOM, or build
provenance; accessibility conformance; any external audit, pen test, or pilot;
and every institutional prerequisite of a national system (statute, funding,
enrollment workforce, manufacturing, authorization to operate).

**Carrying debts (known, dated):** the Rust toolchain floats on an undated
nightly; `test_e2e_atlas.py` runs in no CI job; roughly twenty Dependabot PRs
sit unmerged; `polaris-rotate-secret.sh`, `polaris-chaos-test.sh`,
`polaris-load-test.sh`, and `polaris-ct-monitor.sh` have never been exercised
(the ops-sweep lesson: exercise them, do not read them); the ZK tree depth is
demo-scale by default ([DEVNOTES/zk-soundness.md](DEVNOTES/zk-soundness.md));
the internal TLS hops are classical pending OpenSSL 3.5 in those images.

---

## Phase map

| Phase | Objective | Scale target | Exit gate |
|---|---|---|---|
| P0 | Foundation closure | n/a | Every claim reproducible by command; supply chain signed; zero known debts |
| P1 | Single-authority production | 10k-100k persons, one org | A non-author operator runs it from docs alone; pen test closed; SLOs met |
| P2 | Scale architecture | 1-10M persons (state) | 10M load profile green on HA topology through a rolling deploy and a failover |
| P3 | Federation and relying parties | Many authorities, third-party verifiers | Two instances interoperate in CI; an external team integrates docs-only |
| P4 | Hardware token and enrollment | Field-ready issuance kit | Enroll, personalize, verify online+offline, revoke, recover: end to end on AoR |
| P5 | Pilots | Real, consenting users | Two completed pilots with public reports, zero constitutional violations |
| P6 | Certification and assurance | Authorization-ready | Validated crypto option, 800-63 mapping, audit and red team published |
| P7 | National rollout | 350M persons | First state live; a national program office assumes ownership |

P4 runs in parallel from P1 onward. P5-P7 are gated on external actors; the
buildable machinery for each is listed so no external gate is ever waiting on
us.

---

## P0 - Foundation closure

Objective: a stranger can clone the repo, verify every stated claim with a
command, and reproduce every artifact. Nothing on the known-debt list survives.

| ID | Item | Size | Risk | Blocked by | Definition of done |
|---|---|---|---|---|---|
| [x] P0.1 | Pin the Rust toolchain to a dated nightly (v9.160) | S | low | - | `rust-toolchain.toml` pins nightly-2026-05-10 (build + tests proven on it); CI derives the toolchain from the file; `check_rust_toolchain_pinned` enforces the dated form |
| [x] P0.2 | Wire `test_e2e_atlas.py` into CI (v9.160) | S | low | - | The suite was modernized first (it had rotted against the v9.146 MapLibre surface), proven to fail on a sabotaged page and pass on a healthy one, then wired into the docker-image job under POLARIS_E2E_REQUIRE=1 so skips cannot read as green; `check_ci_runs_atlas_e2e` pins the wiring |
| [x] P0.3 | Clear the Dependabot backlog and set policy (v9.161) | M | low | - | 15 safe bumps batch-applied and verified (cargo build+test, CLI suite, pip-audit clean, both images rebuilt); 4 foundation majors declined with recorded reasons and `ignore` rules (postgres 18, python 3.14, plonky2/plonky2_field 1.x); the merge policy is documented in dependabot.yml |
| [x] P0.4 | Exercise the un-swept operator tools: rotate-secret, chaos-test, load-test, ct-monitor (v9.166) | L | med | - | All four exercised end to end; four real defects found and fixed, each pinned: load-gen double-counted failures + exited green on 100% 5xx; the chaos zk_binary_absent scenario was VACUOUS (ran bare python3, mistook the import failure for a verifier refusal, missed a planted fail-open binary); ct-monitor was untestable offline + would parse a crt.sh error page as certs; rotate-secret regressed 0644 container-readable secrets to 0600 (the v9.140 crash-loop). Four detection-tested checks added |
| [x] P0.5 | SBOM per release (pip + all four images) (v9.167) | M | low | - | `.github/workflows/sbom.yml` fires on published release, generates SPDX-2.3 SBOMs for the Python surface + all four self-built images (via the same Trivy the CVE scanner pins), and attaches them; both surfaces exercised locally (20 + 60 packages); `check_sbom_workflow` and `check_sbom_trivy_matches_scan` pin the job and the version match |
| [x] P0.6 | Signed artifacts and provenance (v9.168) | M | med | P0.5 | Release SBOMs carry a keyless SLSA build-provenance attestation (Sigstore/Fulcio/Rekor via GitHub OIDC, `actions/attest-build-provenance@v4`); `gh attestation verify` documented in SECURITY.md. DoD amended: image signing at a registry digest is DEFERRED to P1.5 because the four images are not published to any registry, so there is no ref to sign today; `check_release_provenance` pins the attestation + permissions + verify doc |
| [x] P0.7 | ZK production profile + plonky2 major (v9.169 + v9.170) | M | med | - | Tree depth parameterized (v9.169): runtime `POLARIS_ZK_TREE_DEPTH`, default 14, prover + Python witness both read it (parity 31/31); prove/verify/size benchmarked across depths 10-24, zk-soundness ledger updated with measured numbers (verify + size constant, prove superlinear via full-tree reconstruction, sibling-path witness named as the next optimization). Plonky2 0.2->1.x taken (v9.170): roots bit-identical across the major, two-witness 31/31 + Rust 8/8 re-passing, seven new must-use-Result warnings handled with `?` (not silenced), Poseidon constants proven still-valid. `check_zk_tree_depth_synced` pins prover/witness depth agreement. A national-scale (depth 24+) anonymity set is verify/size-viable but gated on the sibling-path witness optimization, now a named follow-up |
| [x] P0.8 | Coverage measured and gated (v9.171) | M | low | - | `scripts/ai-coverage.sh` runs the Python suites under coverage.py (with subprocess coverage so the CLI's 664 lines are seen, not 0%), combines, and fails CI below a 72% floor (measured baseline 78%); CI gates the Rust library at `--fail-under-lines 85` (baseline ~92%); both numbers published to the CI step summary. `check_coverage_gated` pins both gates. Publishing per-release as an asset was scoped to the CI step summary since a coverage run needs the DB the release workflow lacks |
| [x] P0.9 | Offsite backup, one command (v9.173) | M | low | - | `POLARIS_PGBACKREST_S3_{BUCKET,ENDPOINT,REGION}` on the postgres service switch the pgBackRest repo to an S3-compatible offsite bucket: the image entrypoint renders `conf.d/repo.conf` at every start (pgBackRest refuses an option set in two files, which the drill found the first time it ran), the key pair is a mounted secret fragment, and the container refuses to start if it sees the pair in env. `scripts/polaris-offsite-drill.sh` backs up into a TLS MinIO bucket with verification on and restores a fresh postgres from the bucket alone; CI runs it on every push. `check_offsite_backup_env_driven` pins all of it |
| [x] P0.10 | Pager integration for alerts (v9.175) | S | low | - | `deploy/observability/alertmanager.yml` ships routing (PolarisDuressEvent: `group_wait: 0s`, re-page every 15m; other SEV-1 immediate; SEV-2/3 batched) and a `pager` webhook receiver whose URL is a mounted secret file (`url_file`; inline URLs/keys are refused by the check); `prometheus.yml` is wired to it. The duress>0 page path is proven in two halves: `test_duress_increments_prometheus_counter` (a duress-code match bumps the counter) and `scripts/polaris-page-drill.sh` (real Prometheus + Alertmanager on the shipped files, the counter flipped 0 to 1, the `PolarisDuressEvent` webhook asserted, none before). The drill also runs promtool/amtool, so "promtool-validated" is a CI fact now. RUNBOOKS.md gains the Paging section. `check_pager_integration` pins it |
| [ ] P0.11 | Internal-hop hybrid PQ KEX | M | ext | OpenSSL 3.5 in the pgbouncer/postgres images | Both internal hops negotiate hybrid KEX; the CI handshake proof extends to them; PQC-POSTURE updated |

Exit gate: every P0 row `[x]` (P0.11 may remain `[EXT]` if still
vendor-blocked); the known-debt paragraph above is rewritten empty.

---

## P1 - Single-authority production

Objective: one real issuing authority (a university, a county office) could run
Polaris for its population, on Linux, around the clock, without the author.

| ID | Item | Size | Risk | Blocked by | Definition of done |
|---|---|---|---|---|---|
| [x] P1.1 | First-class Linux server deployment (v9.176) | L | med | P0 | `deploy/linux/install.sh`: Docker from Docker's official apt/dnf repositories with the signing key fingerprint verified (never curl piped to sh), the repo at /opt/polaris, images, secrets, `/etc/polaris/polaris.env`, `polaris.service` plus daily backup and weekly verify timers, the stack started, migrations synced, `/api/health` asserted healthy through the TLS edge; idempotent. `docs/operator/LINUX-SERVER.md` (install, operate, upgrade, uninstall, caveats) and `HARDENING.md` (SSH, updates, firewall and Docker, time, daemon, permissions, sysctl, auditd, fail2ban, /metrics). CI: the packages stage executes for real in Debian 12 and Rocky 9 containers, and the full install runs under real systemd on the runner including a backup run and a restart. Stated limit: ACME is not exercised in CI (internal-CA edge). `check_linux_server_deployment` pins it |
| [x] P1.2 | Key custody abstraction (HSM/KMS) (v9.178) | L | high | - | `polaris_web/custody.py`: one interface (`public_key()`, `sign(digest)`, raw ML-DSA-65 bytes) with `file`, `pkcs11` (PKCS#11 v3.2 `CKM_ML_DSA`, key generated in-token and non-extractable) and `awskms` (KeySpec `ML_DSA_65`, RAW `ML_DSA_SHAKE_256`) drivers; `pqc_signing.sign()` routes through it and the two-witness verify is byte-for-byte unchanged and gates every driver's output. Secrets never from env (PIN file only; the app refuses a PIN in env). Rotation via `POLARIS_PQC_TRUST_ANCHORS_FILE`, tested end to end. Exercised: file for real; KMS through its real botocore wire path against a stand-in signing with OpenSSL's ML-DSA; PKCS#11 against a real token (Kryoptic) in CI job `custody-pkcs11`. `KEY-CEREMONY.md` (ceremony per driver, rotation, compromise). Scope note: epoch anchors are hash-chained, not signed, so the issuer key is the only key under custody; anything signed later goes through the same interface. Stated limit: no hardware HSM in CI. Cloud drivers: AWS shipped; GCP/Azure ML-DSA are preview-stage and follow the same ~150-line shape. `check_key_custody_abstraction` pins it |
| [x] P1.3 | Secrets lifecycle to KMS (v9.180) | M | med | P1.2 | `polaris_web/secretstore.py` + `scripts/polaris-secrets.sh`: a sealed store (`age` recipients, or AWS KMS envelope encryption with per-file `GenerateDataKey` + AES-256-GCM and `KeyId` pinned on `Decrypt`) is the source of truth; plaintext is unsealed into a root-only tmpfs (`POLARIS_SECRETS_DIR`) by `polaris-deploy.sh` and `polaris.service` before every start, and compose reads only that variable. `polaris-rotate-secret.sh` writes rotated secrets through to the store; `rotate-wrapping` re-seals under a new identity or key. Drilled in CI: prod-stack-boot seals, DELETES the plaintext directory, boots from the tmpfs, rotates the DB password and session key on the live stack, asserts health, verifies the store matches the tmpfs, and re-unseals the rotated value. `test_secretstore.py` covers both backends (age via the real CLI, KMS via the wire-faithful stand-in), wrapping rotation, tamper and drift detection, mode restoration. External stores (Vault, GSM, Azure KV) documented as the same unseal hook. `check_secrets_lifecycle_sealed` pins it |
| [x] P1.4 | Zero-downtime deploys (v9.183) | L | med | - | Expand-contract policy in `polaris_sql/migrations/README.md`, enforced by `check_migrations_expand_contract` (destructive DDL in an `.up.sql` must declare `-- phase: contract` and `-- expands: <earlier id>`; all 17 existing migrations comply without grandfathering). Blue-green profile `docker-compose.bluegreen.yml`: `app` + `app-green` behind Caddy with upstreams from `POLARIS_UPSTREAMS`, `lb_try_duration` retry onto the other colour, 2s `/api/health/live` polling, an app healthcheck and gunicorn drain. `polaris-deploy.sh` honours `POLARIS_COMPOSE_EXTRA`, brings infrastructure up, migrates first, then rolls green and blue with health waits and rolls both back on failure; `polaris-rotate-secret.sh` rolls the colours too. CI job `rolling-deploy` runs `scripts/polaris-rolling-drill.sh`: a full deploy under continuous edge traffic with zero non-200 and zero transport errors while both containers are replaced, plus a negative control (both colours stopped 20s) that must show drops. Stated limit: edge (Caddy) and database recreation are still window operations. `check_zero_downtime_deploy` pins it |
| [x] P1.5 | Kubernetes/Helm reference profile (v9.186) | L | med | P1.4 | `deploy/helm/polaris`: the production topology (caddy edge, 2 app replicas with `maxUnavailable: 0` and a PDB, pgbouncer, postgres StatefulSet as uid 70 with the self-contained image, redis) with every pod under the restricted Pod Security Standard and default-deny NetworkPolicies allowing only the topology's edges (DNS for all; ACME/S3 egress only when enabled). Secrets from the same generator as compose (`existingSecret`) or chart-generated. CI job `helm-kind` runs `scripts/polaris-helm-drill.sh`: kind with the default CNI disabled and Calico installed (kindnet does not enforce NetworkPolicy), the self-built images loaded with pull policy Never (redis pulled by its pinned digest), a privileged pod rejected by PSS, `helm install --wait`, `/api/health` healthy through the edge including custody, a probe pod denied on postgres/pgbouncer/app, and a rolling restart. `docs/operator/KUBERNETES.md`. Stated limits: one postgres replica (HA is P2), `tls: internal` in CI, no registry images published yet. `check_helm_reference_profile` pins it |
| [x] P1.6 | Distributed tracing and dashboards-as-code (v9.187) | M | low | - | Opt-in OTel tracing in `polaris_web/tracing.py`: POLARIS_OTEL-gated, announced in the log stream, a hand-rolled server span (route template as name, query-stripped `http.target`, the v9.122 correlation id as `polaris.request_id`, exception CLASS only) with psycopg2 client spans inside the same trace (statement templates, never values); inbound `traceparent` honoured only behind POLARIS_TRUST_PROXY. The correlation id joins logs to traces BOTH ways: structured_log lines carry trace_id/span_id while a span records. Dashboards as code: `deploy/observability/grafana/` provisions Prometheus+Tempo datasources and two committed dashboards (`polaris-overview` mirroring the alert thresholds incl. the duress panel, `polaris-traces` with TraceQL keyed on the request id); digest-pinned Tempo+Grafana in the `docker-compose.observability.yml` overlay. CI job `trace-drill` runs `scripts/polaris-trace-drill.sh`: dashboards validated, the overlay rendered, and the OTLP wire path proven — the exported span carries the caller's exact X-Request-ID and the query string is asserted absent from the payload bytes; the DB half is `DistributedTracingTests` in the product suite. `check_distributed_tracing` pins it |
| [x] P1.7 | Session and origin hardening pass (v9.189) | M | low | - | webauthn 3.0.0 taken with its own ceremony test pass (`WebAuthnCeremonyTests`: a synthetic ES256 and a synthetic ML-DSA-65 authenticator driven through the app's own register/assert routes, plus replayed-counter, wrong-origin, stale-challenge, and malformed-payload refusals); ML-DSA-65 offered first and verified, so the relying party is PQ-ready before the hardware. Attestation policy knobs `POLARIS_WEBAUTHN_ATTESTATION` / `_USER_VERIFICATION` (enforced on BOTH ceremonies) / `_REQUIRE_ATTESTATION` / `_ALLOWED_AAGUIDS`, validated at boot, refusals audited. Per-role network policy `POLARIS_NETWORK_POLICY_<ROLE>` enforced inside `authenticate()` (generic error, no counter bump, `NETWORK_POLICY_DENIED`) and on every live session, on the proxy-aware `client_ip()`. Server-side session registry `OperatorSession` (migration 2026-09-01-001): per-role concurrent caps with least-recently-seen eviction (exact under real threads, C9), idle timeouts, revocation on deactivation / logout / CLI password change, a cookie without a live row is anonymous; admin defaults 3 sessions / 30 min idle. Docs: HARDENING.md 13, WEBAUTHN-ROLLOUT.md Phase 6, DEPLOYMENT/SECRETS/SECURITY/DATA-MODEL/PQC-POSTURE. `check_session_origin_hardening` pins it |
| [x] P1.8 | Abuse controls (v9.190) | M | med | - | `AgencyQuota` (migration 2026-09-01-002): opt-in per-agency caps (issuances/day, revocations/day, verifications/hour), enforced by `enforce_agency_quota` BEFORE triggers on every write path (procedures, console, bulk loads) with no bypass GUC, a per-(kind, agency) advisory lock so the cap is exact under concurrent writers (C9, tested with real threads), a cheap exit for uncapped agencies, and the window indexes; the app answers 429 with the trigger's sentence and counts `polaris_quota_refusals_total`; `polaris quota-set` / `quota-show`. Velocity: `polaris_agency_events_total{kind,agency_id}` recorded on the issue, revoke, and verify routes (and `polaris_verifications_total` finally incremented); four alerts (`PolarisIssuanceVelocity` / `RevocationVelocity` / `VerificationVelocity` at an absolute floor AND 4x the agency's own trailing 7-day hourly mean, offset 1h; `PolarisQuotaRefusals` on any refusal), each with a runbook, unit-tested by `promtool test rules` (`polaris-alerts.test.yml`), two overview dashboard panels. Exercised: `scripts/polaris-abuse-drill.sh` in the CI test job logs in with the load generator (new `--login` / `--method POST` / `--form` / `--csrf-from` operator-flow mode) and POSTs 50 verifications at 10 rps against a cap of 25: exactly 25 recorded, the rest 429, database + `/metrics` + log agreeing, on the REDIS rate-limiter backend. redis-py 5.x to 8.1.0 taken with its own test pass: a Redis service in the CI test job so the Redis-backed limiter tests run instead of skipping, an explicit one-attempt fail-closed retry contract (8.x retries with backoff by default), the separate Dockerfile pin and the Dependabot ignore removed. `check_abuse_controls` pins it |
| [x] P1.9 | Performance baseline v1, published (v9.191) | M | low | P0.4 | `docs/reference/PERFORMANCE-BASELINE.md`: issuance/s, verification/s, and atlas p95 (zoomed warm and cold, whole-world warm) measured END TO END through gunicorn (4 sync workers) + PostgreSQL on stated hardware by `scripts/polaris-perf-baseline.sh`, which resets the sample data, starts the server, drives each stage with the load generator's new operator-flow mode (`{seq}` for unique serials and per-request bboxes, ML-DSA-65 signing when liboqs is present) for 60s, and rewrites the doc's measured block with a stamp (version, commit, date, CPU, cores, memory, OS, Postgres, Python, workers, signing, topology). SLO-boundary floors (issuance >= 2/s, verification >= 5/s at >= 95% success, atlas warm p95 <= 2s) gate the script; the CI test job re-runs it in `--smoke` mode on every push and uploads the JSON as an artifact (a shared runner is a procedure check, not a baseline). The F-03 per-IP limits gained env overrides for the benchmark's scratch server with the defaults pinned. `check_performance_baseline` pins it |
| [ ] P1.10 | DR to targets, on a schedule | M | low | P0.9 | RTO <= 4h and RPO <= 5min proven by an automated monthly drill with committed results |
| [ ] P1.11 | Retention and lifecycle engine | M | med | - | Per-table-class retention configuration with jurisdiction templates; the archive/purge chain drives it; the C1 carve-out rules unchanged |
| [ ] P1.12 | External penetration test | M | ext | P1.1-P1.8 | [EXT: funding, firm] The readiness pack is ours to build; findings triaged, fixed, and pinned; a summary published |

Exit gate: a non-author operator performs a witnessed clean install and a
simulated month of operations (issuance, revocation, recovery, backup, restore,
failover, rotation) using only the docs, and the
[SLOs](docs/operator/SLOS.md) hold on reference hardware.

---

## P2 - Scale architecture

Objective: a state-scale deployment (1-10M persons) with high availability,
horizontal read scaling, and operational headroom, proven by load.

Planning targets (to be validated by P2.9, not asserted): 10M persons;
sustained 1,000 verifications/s with 10x peak headroom; 50 issuances/s
sustained during enrollment surge; p95 online verification under 150ms
server-side; 99.95% availability.

| ID | Item | Size | Risk | Blocked by | Definition of done |
|---|---|---|---|---|---|
| [ ] P2.1 | Event-table partitioning | L | high | P1.4 | Time-range partitions on the event tables with lifecycle tooling; C1 append-only semantics preserved across attach and detach; the migration executes zero-downtime |
| [ ] P2.2 | Read-replica routing | M | med | P2.1 | Read-only surfaces (atlas, reports, exports) route to replicas under an explicit staleness contract; failback tested |
| [ ] P2.3 | Atlas v2 on PostGIS | L | med | P2.1 | Server-side clustering at scale replaces the bespoke binning; 10M-event map interaction inside p95 targets; the C8 caps retained |
| [ ] P2.4 | Bulk enrollment pipeline | L | med | P2.1 | COPY-based batch issuance for authority migrations, benchmarked; every imported row still passes the full constraint set |
| [ ] P2.5 | Epoch pipeline at scale | L | high | P0.7 | Incremental Merkle maintenance, parallel proving, witness parity at production depth; an epoch cadence spec published |
| [ ] P2.6 | Status distribution v1 | L | high | P2.5 | Signed, versioned, short-lived status artifacts (revocation and validity) distributable via CDN and verifiable offline; freshness rules specified; this is the backbone of P3.6 |
| [ ] P2.7 | HA automation | L | high | P1.10 | Supervisor-managed automated failover replaces the manual runbook; an induced-failure drill passes; the split-brain analysis is documented |
| [ ] P2.8 | Multi-region DR | L | med | P2.7 | An async standby region and a region-evacuation drill with measured RTO/RPO |
| [ ] P2.9 | 10M-profile load certification | L | med | P2.1-P2.7 | The published harness drives the planning targets above against the HA topology during a rolling deploy and one induced failover; the numbers are committed |
| [ ] P2.10 | Cost model | S | low | P2.9 | Infrastructure cost per 1M persons per year, derived from P2.9, committed |
| [ ] P2.11 | Standing chaos program | M | low | P0.4 | Scheduled chaos runs against the staging profile with paging verified; findings feed checks |
| [ ] P2.12 | Evaluate Plonky2 to Plonky3 migration | L | med | P2.5 | An EVALUATION SPIKE with a decision record, not a committed migration. Plonky3 is NOT a version bump: it ships as modular `p3-*` component crates (a STARK/AIR toolkit), not a drop-in for Plonky2's ready-made recursive-SNARK `CircuitBuilder`, so adopting it is a rewrite of `polaris_zk` (circuit as an AIR) plus a full two-witness re-anchor, not a `cargo` bump. As of 2026-09 Plonky3 is `0.7.0-rc.1` (a release candidate) while Plonky2 is stable at 1.1.0 but 16 months without a release. This row exists because that staleness-vs-momentum gap is a real long-term supply-chain question for a national system; it is timed to P2 because you do not rewrite a prover before (a) Plonky3 stabilizes past RC and (b) the scale requirements (P2.5 epoch pipeline) actually justify the cost. DoD: a written comparison (perf at production depth, proof size, audit status, maintenance trajectory, rewrite cost, two-witness feasibility) ending in a recorded keep-or-migrate decision. The nearer-term ZK step remains the sibling-path witness optimization named in P0.7 |

Exit gate: P2.9 green and published.

---

## P3 - Federation and the relying-party ecosystem

Objective: multiple independent issuing authorities interoperate, and third
parties verify against Polaris without talking to us.

| ID | Item | Size | Risk | Blocked by | Definition of done |
|---|---|---|---|---|---|
| [ ] P3.1 | Topology decision record | M | low | - | An ADR choosing federated per-authority instances (the schema's explicit-attestation model) over a central instance; the threat-model delta documented |
| [ ] P3.2 | Inter-authority protocol v1 | L | high | P3.1 | A versioned spec: attestation exchange, anchor cross-publication, epoch alignment, revocation propagation; conformance vectors included |
| [ ] P3.3 | Transparency service | L | med | P3.2 | A public append-only anchor log, mirrored; `ct-monitor` productized as an independent daemon anyone can run; a tampering drill proves detection |
| [ ] P3.4 | Relying-party API v1 | M | med | P2.6 | A stable versioned verification API; RP organizations authenticate via mTLS or OAuth2 client credentials. This is API access auth only: identity never becomes a login product, per the vocation. Deliberately reopens the retired "OIDC" scope in that narrow form |
| [ ] P3.5 | RP SDKs and conformance suite | L | med | P3.4 | Server-side verify SDKs (Python, TypeScript) with a public conformance suite; passing it is the integration contract |
| [ ] P3.6 | Offline verification protocol v1 | L | high | P2.6 | A short-lived signed presentation plus status bundle verifiable with no connectivity; replay and freshness bounds specified; a reference verifier CLI ships |
| [ ] P3.7 | mDL / ISO 18013-5 bridge | L | med | P3.4 | Read-only derived mdoc presentment from a Polaris token for mDL-reader interop; no new trust semantics |
| [ ] P3.8 | W3C VC issuance endpoint | M | low | P3.4 | An optional VC representation of a verification result; explicitly a format, not a trust model |
| [ ] P3.9 | Per-authority isolation review | L | med | P3.1 | Operator RBAC and data isolation reviewed for the federated topology; row-level security added where the review demands it |
| [ ] P3.10 | Federation proven in CI | M | med | P3.2 | A CI job boots two instances as two authorities and proves cross-verification, attestation revocation, and anchor cross-checks end to end |

Exit gate: P3.10 green, plus one external team completing an SDK integration
using only the public docs and the conformance suite.

---

## P4 - Hardware token and enrollment field kit

Objective: the physical layer. Runs in parallel from P1. The schema already
models the card (serials, biometric binding type, duress hash, succession);
this phase makes the card real.

An honest constraint, stated up front: ML-DSA on secure elements is
bleeding-edge silicon. The card profile therefore targets the schema's own
UC-6 dual-signature model: a classical signature on today's certified silicon
plus a post-quantum binding, migrating on-card as FIPS 204 hardware certifies.
That is exactly the migration the database was built to express.

| ID | Item | Size | Risk | Blocked by | Definition of done |
|---|---|---|---|---|---|
| [ ] P4.1 | Card profile spec v0 | L | high | - | The on-card data model, dual-signature layout, PIN and duress semantics, and succession handling, reviewed against the threat model |
| [ ] P4.2 | Software token emulator and vectors | L | med | P4.1 | An emulator implementing the profile plus published test vectors; everything downstream develops against it |
| [ ] P4.3 | Personalization service | L | high | P4.2, P1.2 | A secure key-injection flow bound to the audit-of-record; every personalization is an AoR event |
| [ ] P4.4 | Enrollment station reference | XL | high | P4.3 | A kiosk build: locked-down browser, vendor-neutral biometric capture abstraction, document authentication hooks, and the 800-63A evidence flow; produces a complete IAL-mapped enrollment record |
| [ ] P4.5 | Verifier device reference | L | med | P4.2, P3.6 | An NFC/QR read path with online and offline verification, running the P3.6 protocol |
| [ ] P4.6 | Silicon tracking and eval | M | ext | - | [EXT: vendor availability] A FIPS 140-3 SE vendor matrix, ML-DSA-on-SE status, and eval-kit results as they exist; refreshed quarterly |
| [ ] P4.7 | Duress-on-card interaction spec | M | med | P4.1 | The duress entry method specified with a safety review; indistinguishability preserved end to end at the physical layer |

Exit gate: enroll a person, personalize a token (emulator or eval silicon),
verify online and offline, revoke, and recover, with every step on the AoR and
every guarantee holding.

---

## P5 - Pilots [EXTERNAL GATES]

Objective: real, consenting users. Institutions decide; our job is to make
saying yes cheap and safe.

| ID | Item | Size | Risk | Blocked by | Definition of done |
|---|---|---|---|---|---|
| [ ] P5.1 | Pilot-in-a-box | L | med | P1, P4.2 | A one-command pilot deployment profile: ops pack, metrics and reporting bundle, DPIA template, consent flow, and a rollback-and-erasure plan |
| [ ] P5.2 | Campus pilot | M | ext | P5.1 | [EXT: university MOU, IRB] An opt-in campus credential shadow pilot; our part is support engineering and the public exit report |
| [ ] P5.3 | Agency pilot | L | ext | P5.2 | [EXT: county or agency MOU] Shadow verification alongside an existing credential at a real agency, to the same reporting bar |
| [ ] P5.4 | Post-pilot fix arcs | L | med | each pilot | Every pilot finding triaged, fixed, and pinned; the report published |

Exit gate: two completed pilots, public reports, zero constitutional
violations under real use, and erasure honored on request and proven.

---

## P6 - Certification and assurance [EXTERNAL-HEAVY]

Objective: the assurance envelope a government sponsor requires. External
certifications are theirs to grant; readiness is ours to build.

| ID | Item | Size | Risk | Blocked by | Definition of done |
|---|---|---|---|---|---|
| [ ] P6.1 | Validated-crypto option | M | ext | P1.2 | [EXT: module certification] The custody interface drives a FIPS 140-3 validated module; the two-witness discipline is retained; the toggle documented |
| [ ] P6.2 | NIST 800-63-4 mapping | L | med | P4.4 | An IAL/AAL/FAL mapping with evidence per control; gaps closed or explicitly waived with reasons |
| [ ] P6.3 | FedRAMP/StateRAMP-ready profile | L | ext | P1.5 | [EXT: authorization] A GovCloud IaC reference, a control-mapping SSP skeleton, inheritance documented |
| [ ] P6.4 | SOC 2 evidence automation | M | ext | P1 | [EXT: audit] Continuous evidence collection wired to the ops stack |
| [ ] P6.5 | Accessibility to WCAG 2.2 AA / Section 508 | L | med | - | Every surface audited and conformant; automated accessibility checks added to CI |
| [ ] P6.6 | Independent audit, public red team, bug bounty | M | ext | P1.12 | [EXT: funding] Scoped from [RED-TEAM-SCOPE](docs/RED-TEAM-SCOPE.md); results published unredacted where safe |
| [ ] P6.7 | Formal-methods expansion | L | med | P0.7 | Specs for C1, C2, and the epoch/status protocol; the purge coverage property proven; [meta/tla](meta/tla/README.md) graduates from demonstrator to maintained |

Exit gate: a sponsoring authority accepts the authorization package [EXT].

---

## P7 - National rollout [EXTERNAL-DOMINATED]

Objective: the machinery of scale-out. Statute, funding, and program authority
belong to government; every buildable artifact is ready before it is asked for.

Planning targets (to be validated, not asserted): 350M persons; 5,000
sustained and 50,000 peak verifications/s nationally across federated
instances; an enrollment surge of 200,000/day sustained during rollout years;
99.99% availability on the verification path.

| ID | Item | Size | Risk | Blocked by | Definition of done |
|---|---|---|---|---|---|
| [ ] P7.1 | Institutional prerequisites register | M | ext | - | [EXT: statute, SORN, funding] The complete list of legal instruments and decisions national operation requires, maintained as a living document |
| [ ] P7.2 | Authority onboarding factory | L | med | P3, P6.3 | Instance-per-authority provisioning automation plus an onboarding playbook; a new authority reaches interoperating-live in days |
| [ ] P7.3 | National capacity model | L | med | P2.9 | The targets above validated by extrapolation from measured P2 numbers plus staged federation load tests; published |
| [ ] P7.4 | 24/7 operations design | M | ext | P2.11 | [EXT: staffing] SOC integration, on-call structure, public status and incident communications, all specified and tool-ready |
| [ ] P7.5 | Coexistence and migration spec | M | med | P3.7 | Phased coexistence with Real ID and legacy credentials, cutover and sunset criteria, no flag-day |
| [ ] P7.6 | Quantum-event readiness | L | med | P2.5 | A mass UC-6 migration drill at scale: the measured time to re-sign a population when an algorithm falls; runbook committed |
| [ ] P7.7 | Public transparency program | M | low | P3.3 | Anchors, availability, audit results, and aggregate warrant-audit statistics published on a standing cadence |

Exit gate: the first state authority live at scale on its own instance; a
national program office assumes ownership; the project transitions to steward
of the reference implementation.

---

## Standing rules (every phase, every ship)

1. **The constitution gates everything.** No item ships if it erodes C1-C10 or
   the vocation. Anything touching them carries a constitutional note in its
   CHANGELOG entry.
2. **The ship discipline is unchanged** (see [CLAUDE.md](CLAUDE.md)): edit,
   test, check, bump, CHANGELOG, gate READY.
3. **Every new capability ships with its checks.** A capability without a
   detection-tested check is not done.
4. **Exercise, never just read.** Ten of ten defects found in the 2026-08-31
   sweeps were invisible to reading. Anything operational is run against a
   scratch stack before it is called done.
5. **Numbers carry stamps.** Any stated count or benchmark names the version
   it was measured at.
6. **External gates never wait on us.** For every [EXT] row, the buildable
   readiness artifact is listed and built before the external actor is
   engaged.
7. **Reopened decisions are recorded.** This file reopens Linux deployment
   (P1.1) and narrow RP API authentication (P3.4) against earlier
   retirements, with reasons inline. Banking and payments stay out
   permanently: C10 is not a phase.

## Permanent non-goals

No payment rails or monetary claims (C10). No central biometric database. No
population-scale attribute filtering or analytics. No social scoring. No
commercial or advertising use of verification data. No real personal data
before the P5 consent framework exists. These do not expire with any phase.

## Execution protocol for the next session

1. Read [CLAUDE.md](CLAUDE.md), then this file. The active phase is the lowest
   phase with pending rows.
2. Pick the first row whose Blocked-by column is satisfied; prefer S and M
   rows when resuming cold.
3. One row is one ship (S rows may batch). Mark `[>]` on start; mark `[x]`
   with a version stamp when the definition of done is verifiably true.
4. If a definition of done proves wrong or underspecified, amend the row in
   the same ship and say so in the CHANGELOG entry.
5. When a phase's exit gate is met, record it in the CHANGELOG and move to
   the next phase.
