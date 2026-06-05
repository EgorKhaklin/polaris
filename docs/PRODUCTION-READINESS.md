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
- [ ] **Wire it the rest of the way (Wave 2 cont.).** Store the issuer public key
  as a DB trust anchor (a `SigningKey`/Agency key) and surface verification at a
  use point (token detail / a verify endpoint); make real PQC the production
  default (`POLARIS_USE_REAL_PQC=1` in prod, with liboqs in the prod image); route
  uc6 migration through the signing module (it writes a hardcoded non-signature).
  *(Real key material / HSM custody remains operator-gated.)*

### Wave 3 — data protection + DR (BLOCKER/HIGH)
- [x] **Encrypt backups at rest (v9.102).** `polaris-backup.sh` encrypts the
  tarball with AES-256-CBC/PBKDF2 when `POLARIS_BACKUP_KEY_FILE` is set (and warns
  loudly when it is not); `polaris-restore.sh` decrypts `.enc` backups and fails
  closed without the key. CI now runs the encrypted round-trip + a no-key
  negative check. Pinned by `check_backup_encryption`.
- [x] **Reconciled `DR.md` (v9.102):** it no longer claims a wired ≤1-min RPO;
  the real RPO is the encrypted-`pg_dump` interval (~24h), and pgbackrest/WAL/S3
  is documented as the not-yet-configured target.
- [ ] **App<->DB TLS** (`sslmode`), and field-level / at-rest encryption posture
  for PII and the plaintext ZK `proof_path`.
- [ ] Offsite backup target + WAL archiving for the ≤1-min RPO (operator-gated:
  the S3/offsite store).

### Wave 4 — deploy/ops/reliability/observability (HIGH/MEDIUM)
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
- [ ] Pinned image digests.
- [ ] Prometheus multiprocess mode (metrics undercount across 4 workers);
  shipped alert rules; log rotation; request-correlation IDs; SLOs; runbooks.
- [x] **Dependency CVE scanning gates the build (v9.105).** A `cve-scan` CI job
  runs `pip-audit --strict` on the runtime `requirements.txt`, so a known CVE in
  a package the production image installs fails the build. v9.105 split test
  tooling (pytest/hypothesis/playwright) into `requirements-dev.txt` so the prod
  image no longer ships a test framework (or its CVEs); the dev surface is
  audited informationally. Dependabot opens weekly update PRs. Pinned by
  `check_prod_image_no_test_deps` + `check_cve_scanning`.
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
| **Postgres HA topology** | Replica/standby/failover choice and the host/AZ/managed-tier are infrastructure decisions; today the single node is an unmitigated SPOF. |
| **Encryption-at-rest host + key** | LUKS/TDE/fscrypt needs a provisioned host and a key custodian. |
| **Offsite backup target + RPO** | The S3/offsite bucket, retention, and the real RPO/RTO targets. |
| **Alerting backend + on-call** | The pager/notification backend and the named on-call rotation — including who receives the duress page — are organizational. |
| **Right-to-erasure policy** | How erasure is honored against the append-only non-repudiation audit (crypto-shred vs pseudonymize, retention floor) is a legal/policy call. |
| **Independent pen-test + threat-model sign-off** | Requires a qualified external assessor and an accountable human signature. |

---

## The rule

No wave flips this file's top line to "production-ready," and no doc claims a
protection the code does not implement. "Production-ready" becomes true when the
boxes above are checked and the operator decisions are made — not by assertion.
