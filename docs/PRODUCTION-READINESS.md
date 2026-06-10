# PRODUCTION-READINESS.md — the honest path from reference to production

**Status: NOT production-ready.** Polaris is a strong reference implementation
with a genuinely production-grade core, but it is not yet a system you can run
with real national-identity data. This document is the honest gap ledger between
here and there. It exists so the claim "production-ready" is only ever made when
it is true, primitive by primitive. (See [`THESIS.md`](THESIS.md) for why this
project refuses to overclaim, and [`MISSION.md`](../MISSION.md) for the
constitution that still governs every change.)

A six-dimension production-readiness assessment (v9.101) found **49 properties
already production-grade**, **45 engineering gaps an agent can close**, and **10
gaps that require operator/legal/organizational decisions**. The engineering work
proceeds in waves; the operator decisions are yours.

---

## What is already production-grade

The seven adversarial review passes (v9.64-v9.88) and the C1-C10 DB enforcement
left a real foundation. Genuinely sound today:

- **The ZK stack is real**, not a mock: a Plonky2 (transparent-setup,
  post-quantum-comfortable) Merkle-inclusion circuit, verified at use on
  `/api/zk/verify` with single-use nonce anti-replay, plus an **independent
  second-witness** Poseidon/Merkle verifier in Python.
- **Auth + access control**: scrypt password hashing, atomic failed-login
  counting (no lockout-bypass TOCTOU), username-enumeration resistance (uniform
  scrypt work + lockout revealed only post-auth), per-session CSRF with
  constant-time compare, session-fixation regeneration, role-based authz with
  403 + audit, and a CSP with no `unsafe-inline` for scripts.
- **The C1-C10 invariants are enforced at the database**, not in policy: the
  v9.85 grant boundary revokes UPDATE/DELETE on append-only audit tables from
  `polaris_app`, the only DELETE path is SECURITY DEFINER, and `polaris_app` has
  no DDL.
- **Secrets for the deployment** are file-mounted (`/run/secrets/*`), the app
  refuses to boot in production on the default `SECRET_KEY`, and docker-init
  rotates the `polaris_app` role password off its dev default.
- **C7 algorithm-as-data**, TokenSignature immutability, and the duress/Vocation
  machinery are real and DB-enforced.

---

## Engineering gaps (agent-buildable) — the waves

### Wave 1 — shipped (v9.101)
- [x] **Demo accounts no longer ship to production.** The SQL seed loads
  `admin/Admin@123!`, `operator/Operator@123!`, `auditor/Auditor@123!` and a demo
  duress code. In `POLARIS_ENV=production`, docker-init now disables them
  (is_active=FALSE), scrambles their passwords, locks them, and clears the demo
  duress enrollment. No default credentials reach a production DB; the operator
  bootstraps the first admin with `scripts/polaris-create-operator.sh`. Pinned by
  `check_prod_hardening`.
- [x] **The rate limiter actually uses Redis in production.** The prod compose
  ran Redis but never set `POLARIS_REDIS_URL`, so per-IP limits fragmented across
  the 4 gunicorn workers. Now wired. Pinned by `check_prod_hardening`.

### Wave 2 — cryptographic core (the heart; BLOCKER)
- [x] **Real ML-DSA-65 is now testable + tested (v9.103).** liboqs-python builds
  and runs; a dedicated CI job (`pqc-real`) installs it and proves real signing
  end to end. Real signatures are 3309 bytes, public keys 1952 bytes (FIPS 204),
  verify True, forgeries False.
- [x] **Persistent signing key (v9.103).** `sign()` now loads a long-lived
  keypair from `POLARIS_PQC_SIGNING_KEY_FILE` when set, so the public key is a
  stable, publishable trust anchor (the ephemeral per-call fallback remains only
  for dev). `generate_keypair()` mints one; a malformed key file fails loud.
  Pinned by `check_pqc_real_signing`; unit-tested in `PersistentKeyTests`.
- [x] **Verification is enforced (v9.113).** `verify()` is now live on a real
  path: `signature_bytes_for_token()` self-verifies the signature it produces and
  refuses (`SigningError`) to persist an unverifiable one, and
  `verify_token_signature()` checks a stored signature against the published trust
  anchor (`trust_anchor_public_key_hex()`). Exercised in the `pqc-real` CI job;
  pinned by `check_verify_enforced`.
- [x] **Signing-key generation produces a loadable key (v9.139).** Found by
  exercising the prod-stack bring-up: `polaris-generate-secrets.sh` captured a
  python one-liner's stdout to mint the ML-DSA-65 key, but liboqs prints a banner
  to stdout at import, corrupting the JSON so the app refused to load it (real-PQC
  issuance broken at deploy under the `POLARIS_USE_REAL_PQC=1` default). Fixed: the
  generator swallows stdout during import, validates the JSON before writing, and
  uses `-s` (non-empty) existence guards. Pinned by `check_signing_key_generation`
  + a `pqc-real` CI assertion.
- [x] **Real PQC is the production default (v9.116).** liboqs ships in the prod
  image (built in the Python builder, copied to the runtime), the prod compose
  sets `POLARIS_USE_REAL_PQC=1` and mounts the `polaris_signing_key` secret (the
  trust anchor), and `polaris-generate-secrets.sh` mints the keypair. CI verifies
  real ML-DSA-65 sign + verify-at-use inside the built image. Pinned by
  `check_prod_real_pqc`. *(HSM/KMS key custody remains operator-gated.)*
- [x] **DB trust anchor + verification surfaced at use (v9.117).**
  `TokenSignature.signing_public_key_hex` stores the issuer public key with each
  signature (NULL = placeholder), so verification is self-contained and survives
  key rotation; the token-detail page verifies each signature and renders the
  result. Pinned by `check_signature_self_contained_verify`.
- [x] **uc6 through the signing module (v9.119).** The `/uc6/migrate` route signs
  the token value via `pqc_signing.signature_with_key_for_token()` and stores the
  issuer key, exactly like issuance — no more hardcoded `UC6_OPERATOR_MIGRATE`
  string. Pinned by `check_pqc_wired` + `test_uc6_route_signature_routes_through_signing_module`.

- [x] **Two-witness ML-DSA-65 verification (v9.133).** Every real signature
  verdict is cross-checked by two independent FIPS 204 implementations (liboqs +
  cryptography/OpenSSL) that must agree, or the signature is refused. Pinned by
  `check_pqc_second_witness`.
- [x] **Honest PQC posture audit (v9.134).** The full crypto surface is audited
  against the NIST FIPS 203/204/205 + IR 8547 (2030/2035) timeline in
  [reference/PQC-POSTURE.md](reference/PQC-POSTURE.md): the token signature,
  hashing, and ZK proof are post-quantum; TLS key exchange, the cert signatures,
  and WebAuthn operator MFA are still classical, with the realistic exposure of
  each stated plainly. Pinned by `check_pqc_posture`.
- [x] **Post-quantum edge key exchange, proven (v9.136).** The audit's
  highest-priority transport gap (P1) is closed: the self-built Caddy edge
  negotiates the hybrid PQ group X25519MLKEM768 with modern clients, proven off a
  real TLS 1.3 handshake (forced + default) and asserted by the `caddy-edge` CI
  job. Opportunistic (classical fallback for old clients), adversarially reviewed
  for overclaim. The two internal hops stay classical, gated on OpenSSL below 3.5
  at both ends (measured v9.137: app libpq 3.0.20 on Bookworm, pgbouncer 3.3.7;
  postgres is already 3.5.6). Pinned by `check_edge_pq_kex`.

**Wave 2 (cryptographic core) is complete.** The remaining PQC items (hybrid TLS
KEX, PQC certs, PQC WebAuthn) are operator-gated or third-party-gated; see the
posture audit's migration roadmap.

### Wave 3 — data protection + DR (BLOCKER/HIGH)
- [x] **Encrypt backups at rest (v9.102).** `polaris-backup.sh` encrypts the
  tarball with AES-256-CBC/PBKDF2 when `POLARIS_BACKUP_KEY_FILE` is set (and warns
  loudly when it is not); `polaris-restore.sh` decrypts `.enc` backups and fails
  closed without the key. CI now runs the encrypted round-trip + a no-key
  negative check. Pinned by `check_backup_encryption`.
- [x] **Reconciled `DR.md` (v9.102):** it no longer claims a wired ≤1-min RPO;
  the real RPO is the encrypted-`pg_dump` interval (~24h), and pgbackrest/WAL/S3
  is documented as the not-yet-configured target.
- [x] **App<->DB TLS, both hops, with cert pinning (v9.121 + v9.131).** Both
  prod hops are TLS (`ALTER SYSTEM SET ssl=on` on Postgres; `client_tls` +
  `server_tls` on the pooler) AND, as of v9.131, VERIFY the pinned self-signed
  certs rather than merely encrypting: the app pins pgbouncer
  (`POLARIS_DB_SSLMODE=verify-ca` + `POLARIS_DB_SSLROOTCERT`) and pgbouncer pins
  postgres (`server_tls` verify-ca + `server_tls_ca_file`), so a MITM presenting
  a different cert on either hop is rejected — without needing a real CA.
  `verify-full` + hostname against a real CA stays the operator's upgrade. CI
  runs a verify-ca pinning round-trip (correct pin connects, wrong pin rejected,
  backend SSL confirmed); pinned by `check_app_db_tls`.
- [x] **At-rest encryption posture (v9.124).** `docs/operator/ENCRYPTION-AT-REST.md`
  enumerates the plaintext-sensitive surfaces (`Individual.legal_name` /
  `date_of_birth`, `TokenStateEpochLeaf.proof_path` — the one the schema itself
  flags as v1-plaintext), records that backups (v9.102) and transit (v9.121) are
  encrypted while the live DB is not, and explains why host volume encryption is
  the right control over field-level (which would break C3's unique index and the
  ZK second witness). Pinned by `check_encryption_at_rest_posture`. The host
  encryption layer + key custodian remain operator-gated.
- [x] **Continuous WAL archiving config (v9.127).** pgBackRest ships in the
  postgres image (`Dockerfile.postgres`, digest-pinned base), `pgbackrest.conf`
  defines the `polaris` stanza, and `docker-init.sh` enables `archive_mode` + the
  `archive_command` when `POLARIS_PGBACKREST_ENABLED=1` (opt-in, so no-repo
  deployments do not pile up WAL). A CI round-trip archives → backs up → RESTORES
  with WAL replay. Pinned by `check_pgbackrest_scaffolding`. The **offsite repo**
  (S3 bucket + credentials) and the backup schedule remain operator-supplied.

### Wave 4 — deploy/ops/reliability/observability (HIGH/MEDIUM)
- [x] **Container runtime hardening (v9.141).** Every prod-compose service drops
  ALL Linux capabilities + forbids privilege escalation (`no-new-privileges`),
  adding back only what each entrypoint needs: the app + pgbouncer run with ZERO
  caps (verified `CapEff: 0`), Caddy keeps only `NET_BIND_SERVICE`, postgres/redis
  keep only the five their root-then-drop init needs. Proven to still serve by the
  `prod-stack-boot` job (an early `cap_drop: ALL`-with-no-add draft crashed redis,
  caught by the boot test). Pinned by `check_container_hardening`. Full non-root
  `USER` for the Caddy edge is a noted follow-up.
- [x] **Full prod compose boots + serves end to end (v9.140).** CI booted only the
  dev compose; booting the real prod stack for the first time found it had never
  come up: `09_grants.sql` hardcoded the test DB name `polaris_test`, so prod init
  (DB `polaris`) aborted before enabling TLS, postgres ran `ssl=off`, pgbouncer's
  verify-ca backend was refused, and the app crash-looped. Fixed (dynamic
  `current_database()` grant). A new `prod-stack-boot` CI job generates real
  secrets, builds the prod images, boots `docker-compose.prod.yml` + the citest
  override, and asserts `/api/health` serves through the TLS edge with the
  DB-backed components healthy + postgres `ssl=on`. Pinned by `check_prod_stack_boot`.
- [x] **Migration `lock_timeout`/`statement_timeout` (v9.106).**
  `polaris-migrate.sh` SET LOCALs both inside the apply/revert transaction
  (defaults `3s`/`60s`, overridable), so a blocking `ALTER` fails fast instead
  of stalling all traffic on the table. Pinned by `check_migration_timeouts`.
  (Zero-downtime/rolling deploy still open.)
- [x] **`WEB_CONCURRENCY` is now honored (v9.107).** `gunicorn.conf.py` resolves
  `POLARIS_WORKERS` > `WEB_CONCURRENCY` > 4 (the deploy surface advertised
  `WEB_CONCURRENCY` but the config ignored it). Pinned by
  `check_web_concurrency_honored` + `GunicornConfigTests`.
- [x] **Liveness vs readiness split (v9.108).** `/api/health/live` (cheap, no
  deps — failure should restart) and `/api/health/ready` (dependency roll-up —
  failure should stop routing) are distinct; the container HEALTHCHECK uses
  liveness so a transient outage does not restart the container. Pinned by
  `check_health_liveness_readiness_split` + `HealthEndpointTests`.
- [x] **Container resource limits + log rotation (v9.109).** All five
  prod-compose services (caddy, app, pgbouncer, postgres, redis) set
  `deploy.resources.limits` (memory + cpu, sized to role) and a `json-file`
  log driver capped at `10m` x `5`, so one container cannot OOM the host and
  logs cannot fill the disk. Pinned by `check_compose_resource_limits`.
- [x] **Self-built pgbouncer (v9.110).** The pooler pinned `bitnami/pgbouncer:1.22`,
  which Bitnami removed from Docker Hub (free-catalogue retirement) — the stack
  could not pull it and was unstartable. Now built from `alpine` + the distro
  package (`Dockerfile.pgbouncer`), reading the DB password from the file-mounted
  secret with SCRAM on both hops. Pinned by `check_pgbouncer_self_built`.
- [x] **Self-built Caddy edge (v9.135).** The prod Caddyfile uses the `rate_limit`
  directive (third-party caddy-ratelimit plugin), which the stock `caddy:2-alpine`
  image does not ship, so the pinned edge crash-looped on startup
  (`unrecognized directive: rate_limit`) and the whole TLS front door never came
  up — the same prod-down class as the pgbouncer breakage, missed because CI's
  docker boot job runs the DEV compose (no Caddy). Now built from
  `Dockerfile.caddy` with the plugin compiled in (`xcaddy`, FROM stages
  digest-pinned, in-build plugin guard); a new `caddy-edge` CI job validates the
  real Caddyfile against the built image. Pinned by `check_caddy_self_built`.
- [x] **Pinned image digests (v9.114).** The prod compose's third-party images
  (caddy, postgres, redis) are pinned `tag@sha256:<digest>` so a mutated or
  deleted upstream tag cannot change what runs; the `docker` Dependabot
  ecosystem keeps the pins current. Pinned by `check_prod_images_digest_pinned`.
- [x] **Shipped alert rules (v9.115).** `deploy/observability/` ships a
  promtool-validated `polaris-alerts.yml` (6 rules) + `prometheus.yml` scrape
  config + README; ratios/quantiles stay valid per worker. Pinned by
  `check_alert_rules`. (Alertmanager backend operator-gated.)
- [x] **Prometheus multiprocess metrics (v9.120).** `/metrics` aggregates across
  all gunicorn workers (`PROMETHEUS_MULTIPROC_DIR` + a `MultiProcessCollector`;
  gunicorn `child_exit` reaps dead workers) — no more 4x undercount. Pinned by
  `check_prometheus_multiprocess`; proven across real processes in
  `MetricsMultiprocessTests`.
- [x] **Request-correlation IDs (v9.122).** Per-request `X-Request-ID`:
  generated when absent, validated to `[A-Za-z0-9-]{8,64}` when inbound (honoured
  only behind `POLARIS_TRUST_PROXY`, else minted), stamped into every
  `structured_log` line, echoed on the response, cleared in teardown. Vocation:
  never derived from identity, never written to the audit-of-record — pinned by
  `check_correlation_id` and a DB-backed non-persistence test.
- [x] **SLOs + alert runbooks (v9.123).** `docs/operator/SLOS.md` states the
  reference SLO targets (≥ 99.9% non-5xx availability, request p99 < 2s, DB
  round-trip p99 < 5s) grounded only in exposed metrics, with the error budget
  and the up-front honesty that these are reference targets for a notional
  deployment, not a measured guarantee (Prometheus/Alertmanager operator-gated).
  `docs/operator/RUNBOOKS.md` ships one Trigger/Diagnosis/Remediation section
  per shipped alert. Pinned by `check_alert_runbooks` (one-to-one alert↔runbook
  mapping). Shipped alert rules (done, v9.115); log rotation (done, v9.109).
- [x] **Duress signal is alertable (v9.128).** Duress was "the headline metric"
  but lived only in the JSON `/api/metrics` (not scrapeable), so it could not
  page. Now `polaris_duress_events_total` is a Prometheus counter on `/metrics`
  (incremented where the silent `DuressEvent` is recorded), the SEV-1
  `PolarisDuressEvent` alert fires immediately on any new event, and a
  coercion-response runbook ships. The pager backend stays operator-gated. Pinned
  by `check_duress_alertable` + a DB-backed counter-increment test.
- [x] **Dependency CVE scanning gates the build (v9.105).** A `cve-scan` CI job
  runs `pip-audit --strict` on the runtime `requirements.txt`, so a known CVE in
  a package the production image installs fails the build. v9.105 split test
  tooling (pytest/hypothesis/playwright) into `requirements-dev.txt` so the prod
  image no longer ships a test framework (or its CVEs); the dev surface is
  audited informationally. Dependabot opens weekly update PRs. Pinned by
  `check_prod_image_no_test_deps` + `check_cve_scanning`.
- [x] **Container image CVE scanning + base patching (v9.138).** pip-audit covered
  Python deps and bandit our code, but the OS packages in the base images were
  unscanned and shipped real fixable CRITICALs (2 in the app's Bookworm base, 1 in
  postgres). The four self-built Dockerfiles now `apt-get/apk upgrade` their bases
  (app image drops to 0 fixable CRITICAL/HIGH), and a new `image-cve-scan` CI job
  Trivy-scans every prod image gating on fixable CRITICAL (HIGH reported). One
  documented `.trivyignore` exception (an unreachable Go crypto/tls CVE in the
  postgres base's gosu binary). Pinned by `check_image_cve_scanning`.
- [x] **SAST in CI (v9.112).** `bandit` scans `polaris_web` + `polaris_cli`,
  gating on HIGH severity — it immediately caught a world-writable
  (`chmod 0o777`) state dir, now `0o700` in production. Pinned by
  `check_sast_scanning` + `StateDirPermsTests`.
- [x] **SQL console is READ ONLY at the engine (v9.104).** `sql_query` calls
  `conn.set_session(readonly=True)` before any statement, so a data-modifying
  CTE that slips past the `SELECT`/`WITH` keyword whitelist is refused by
  Postgres itself. Pinned by `check_sql_console_readonly`; the DB-backed
  `test_data_modifying_cte_refused_by_db_readonly` proves the engine refuses the
  write (it caught a mid-transaction `SET` non-fix first).

The full enumerated gap list with file pointers lives in the v9.101 assessment;
each wave lands as its own CI-green ship and ticks its boxes here.

---

## Operator / legal / organizational decisions (NOT agent-buildable)

These are yours. Production with real identity data cannot proceed without them:

| Decision | Why it can't be an engineering task |
|---|---|
| **Legal basis + DPIA + regulator approval** | Holding national-identity PII needs a named controller, jurisdiction, counsel-drafted DPIA, and regulatory sign-off. |
| **Signing-key custody (HSM/KMS)** | The real private key material and its custody/rotation authority are operator-held; the agent can only build the loading + rotation mechanism. |
| **Postgres HA topology** | The replication READINESS ships (v9.126): the primary is `wal_level=replica` with a least-privilege `polaris_replicator` role, [`docs/operator/FAILOVER.md`](operator/FAILOVER.md) documents the `pg_basebackup` standby bootstrap + `pg_promote` failover, and CI proves a working hot standby. The standby HOST (a second machine/AZ), the failover decision, and any managed-tier choice remain operator infrastructure decisions; until a standby is stood up the single node is still a SPOF. |
| **Encryption-at-rest host + key** | LUKS/TDE/fscrypt needs a provisioned host and a key custodian. |
| **Offsite backup target + RPO** | The S3/offsite bucket, retention, and the real RPO/RTO targets. |
| **Alerting backend + on-call** | The pager/notification backend and the named on-call rotation — including who receives the duress page — are organizational. |
| **Right-to-erasure policy** | The pseudonymize MECHANISM ships (v9.125: `uc_pseudonymize_individual` + the append-only `IndividualErasureEvent`). WHICH erasures to honor, the retention floor, and crypto-shred-vs-pseudonymize against the append-only non-repudiation audit remain a legal/policy call. |
| **Independent pen-test + threat-model sign-off** | Requires a qualified external assessor and an accountable human signature. |

---

## The rule

No wave flips this file's top line to "production-ready," and no doc claims a
protection the code does not implement. "Production-ready" becomes true when the
boxes above are checked and the operator decisions are made — not by assertion.
