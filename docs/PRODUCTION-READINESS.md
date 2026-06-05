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
- [ ] **Real PQC is the production default, not the SHA3 placeholder.** Today the
  shipped default signs tokens with a deterministic `sha3_256(token_value)` that
  authenticates nothing. Make real ML-DSA-65 (liboqs) the production path.
- [ ] **Signing-key custody.** `sign()` generates a fresh ephemeral keypair per
  call and discards the private key. Load a persistent per-agency signing key
  from a secret/KMS instead. (The real key *material* and HSM/KMS are
  operator-gated; the loading mechanism is buildable.)
- [ ] **Verify signatures at use.** `pqc_signing.verify()` is called nowhere in
  the product — TokenSignature is write-only. Enforce verification on the paths
  that consume a token's authenticity.
- [ ] uc6 algorithm-migration writes a hardcoded non-signature; route it through
  the signing module.

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
- [ ] Migration `lock_timeout`/`statement_timeout`; zero-downtime/rolling deploy.
- [ ] `WEB_CONCURRENCY` is inert (workers hardcoded); container resource limits;
  pinned image digests; split liveness vs readiness in `/api/health`.
- [ ] Prometheus multiprocess mode (metrics undercount across 4 workers);
  shipped alert rules; log rotation; request-correlation IDs; SLOs; runbooks.
- [ ] CVE scanning (pip-audit/Dependabot) + SAST in CI.
- [ ] SQL console: make the connection READ ONLY (the keyword whitelist is
  CTE-bypassable).

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
