# SOC2.md — Polaris SOC 2 readiness checklist (v9.01 / Phase 3 Wave 1)

This document is the **auditor-facing operator handbook**. It maps
every applicable Trust Service Criterion (TSC) to the Polaris
controls that satisfy it, names the evidence the auditor will ask
for, and tells the operator how to produce that evidence.

Polaris is a **reference-implementation**, not a SaaS. Operators
deploying Polaris into a SOC-2-attested environment use this
document as the starting point; the operator's full SOC-2 report
will combine these controls with the operator's own organizational
controls (HR onboarding, vendor management, business continuity
planning, etc.).

---

## Table of contents

1. [Trust Service Criteria scope](#1-trust-service-criteria-scope)
2. [Common Criteria — CC1: Control environment](#2-cc1-control-environment)
3. [Common Criteria — CC2: Communication and information](#3-cc2-communication-and-information)
4. [Common Criteria — CC3: Risk assessment](#4-cc3-risk-assessment)
5. [Common Criteria — CC4: Monitoring activities](#5-cc4-monitoring-activities)
6. [Common Criteria — CC5: Control activities](#6-cc5-control-activities)
7. [Common Criteria — CC6: Logical and physical access](#7-cc6-logical-and-physical-access)
8. [Common Criteria — CC7: System operations](#8-cc7-system-operations)
9. [Common Criteria — CC8: Change management](#9-cc8-change-management)
10. [Common Criteria — CC9: Risk mitigation](#10-cc9-risk-mitigation)
11. [Availability — A1](#11-availability-a1)
12. [Confidentiality — C1](#12-confidentiality-c1)
13. [Evidence-collection recipes](#13-evidence-collection-recipes)
14. [Known limitations](#14-known-limitations)
15. [Cross-references](#15-cross-references)

---

## 1. Trust Service Criteria scope

| TSC | In Polaris's scope | Justification |
|---|---|---|
| **Security (Common Criteria)** | ✅ Mandatory | Required for any SOC 2 attestation. Polaris's C1-C10 + G1-G31 + audit-of-record discipline directly satisfies most CC controls. |
| **Availability (A1)** | ✅ In-scope | Polaris is a service infrastructure component; downtime affects holders' ability to verify identity. DR runbook + drill cadence + RPO/RTO targets satisfy. |
| **Confidentiality (C1)** | ✅ In-scope | Holder PII + biometric templates + token-bind data require confidentiality. C2 (privacy-preserving disclosure) + ZK-NULL + scrypt password hashing + KMS-backed secrets satisfy. |
| **Processing Integrity (PI1)** | ⬜ Out-of-scope | Polaris's processing integrity (UC-1 through UC-12 stored procedures, append-only audit, SERIALIZABLE concurrency) is internally enforced; Processing Integrity TSC is about "data processed completely, accurately, timely, and authorized" which maps to operator-level workflows that wrap Polaris (claim-handling pipelines, agency-onboarding flows). The operator scopes PI separately. |
| **Privacy (P1)** | ⬜ Out-of-scope | GDPR/CCPA/HIPAA compliance is operator-layer responsibility. Polaris provides primitives (right-to-be-forgotten via uc8_revoke_token + uc_archive_purge; data-minimization via C2; consent-bound disclosure via TokenSignature) but doesn't ship a complete Privacy program. The operator scopes Privacy on top of Polaris primitives. |

**The scope above is the architect's recommended default.** Operators
with stricter compliance requirements (e.g. HIPAA-Privacy, FedRAMP-PI)
extend the scope by adding their organizational controls; this
document covers the Polaris contribution.

---

## 2. CC1 — Control environment

CC1 is about the operator's organizational tone-at-the-top, governance,
ethics. Polaris contributes infrastructure primitives that REFLECT
the operator's governance, but the governance itself is operator-side.

| Control | Polaris contribution | Evidence query |
|---|---|---|
| CC1.1 — Integrity and ethical values | n/a (operator) | — |
| CC1.2 — Board oversight | n/a (operator) | — |
| CC1.3 — Authority and responsibility | Role-based access (admin/operator/auditor) per `polaris_sql/01_schema.sql:AppUser`; documented in `docs/operator/SECRETS.md` § 7 | `SELECT username, role, is_active FROM AppUser` |
| CC1.4 — Competence | n/a (operator) | — |
| CC1.5 — Accountability | AuthAuditLog records every authenticated action with `user_id` + `event_timestamp`; combined with role enum produces the accountability chain | `SELECT u.username, u.role, l.event_timestamp, l.event_type FROM AuthAuditLog l JOIN AppUser u ON u.user_id = l.user_id ORDER BY l.event_timestamp DESC LIMIT 100` |

---

## 3. CC2 — Communication and information

| Control | Polaris contribution | Evidence query |
|---|---|---|
| CC2.1 — Information quality | Schema CHECK constraints (~41 in 01_schema.sql) + structural-invariant test suite (349 tests) + ai-coherence cross-layer correspondence checks | `python3 -m unittest polaris_web.test_structural_invariants` (must report 349/349 OK); `./scripts/ai-coherence.sh` (must report STRUCTURE INTACT) |
| CC2.2 — Internal communication of objectives + responsibilities | MISSION.md (C1-C10 + G1-G31); ROADMAP.md deployability checklist; meta/architect.md persona spec | `cat MISSION.md ROADMAP.md` (the two are public-readable; auditor inspects directly) |
| CC2.3 — External communication (customers, regulators) | docs/STORY.md (project narrative); docs/reference/API.md (HTTP API surface); docs/operator/* (operator runbooks) | `ls docs/` (auditor inspects directly) |

---

## 4. CC3 — Risk assessment

| Control | Polaris contribution | Evidence query |
|---|---|---|
| CC3.1 — Specifies suitable objectives | MISSION.md C1-C10 (the 10 hard constraints); each constraint has documented threat model | `cat MISSION.md DEVNOTES/threat-model.md` |
| CC3.2 — Identifies + analyzes risk | DEVNOTES/threat-model.md (STRIDE-categorized); v8.97 added § T-S4 (stolen admin password); architect adversary walks via `./scripts/ai-adversary.sh` | `./scripts/ai-adversary.sh` (machine-readable) + `cat DEVNOTES/threat-model.md` |
| CC3.3 — Considers fraud potential | Civitas + Mycelium swarm watch for behavioral anomalies; AnchorBatch + Merkle-tree provides tamper-evidence | `SELECT count(*) FROM AuthAuditLog WHERE event_type='WEBAUTHN_ASSERTION_FAILED' AND event_timestamp > now() - interval '30 days'` |
| CC3.4 — Identifies + assesses change | Schema migration framework (v8.95) provides per-change SHA-256 + actor-user-id + reversibility evidence | `SELECT name, event_type, occurred_at, actor_user_id, file_sha256 FROM schema_version ORDER BY occurred_at DESC LIMIT 50` |

---

## 5. CC4 — Monitoring activities

| Control | Polaris contribution | Evidence query |
|---|---|---|
| CC4.1 — Selects, develops, performs evaluations | HYDRA watcher synthesis (`./scripts/ai-hydra.sh`); Mycelium swarm bloom (`./scripts/ai-swarm-bloom.sh`); ai-coherence; ai-meta. Quarterly drill cadence (DR.md § 5). | `./scripts/ai-hydra.sh > evidence/hydra-Q$(date +%q)-$(date +%Y).log` |
| CC4.2 — Communicates evaluation results | journal/<date>.md daily session log; meta/sanctum-index.md strategic decisions; CHANGELOG.md release log | `ls journal/ \| tail -30` (auditor samples 30 days of operator activity) |

---

## 6. CC5 — Control activities

| Control | Polaris contribution | Evidence query |
|---|---|---|
| CC5.1 — Selects + develops control activities | C1-C10 are the load-bearing controls; each has structural-invariant test coverage (62 schema-CHECK tests + 349 structural tests + Hypothesis property tests) | `cat MISSION.md \| grep -E "^### C[0-9]"` |
| CC5.2 — Selects + develops controls over technology | docker-compose.prod.yml + Caddyfile (TLS via Let's Encrypt, HSTS, security headers per G27); WebAuthn-MFA (v8.97); rate limiter (R8-2) | `docker compose -f polaris_web/docker-compose.prod.yml config` |
| CC5.3 — Deploys via policies + procedures | scripts/polaris-deploy.sh (idempotent); scripts/polaris-migrate.sh (audited schema changes); scripts/polaris-create-operator.sh (audited account creation) | `ls scripts/polaris-*.sh \| wc -l` |

---

## 7. CC6 — Logical and physical access

CC6 is the largest CC group and where most of Polaris's controls
land. **The auditor will spend most of their time here.**

| Control | Polaris contribution | Evidence query |
|---|---|---|
| CC6.1 — Logical access security software, infrastructure, architectures | Caddy TLS edge (G27) + Docker network isolation + polaris_app DB role with limited grants (09_grants.sql) + WebAuthn-MFA for admin (v8.97) | `docker compose -f polaris_web/docker-compose.prod.yml config \| grep -A2 networks` + `SELECT rolname, rolsuper, rolcreatedb FROM pg_roles WHERE rolname LIKE 'polaris%'` |
| CC6.2 — Logical access — authorization, registration | scripts/polaris-create-operator.sh + AuthAuditLog ACCOUNT_CREATED entry in same txn | `SELECT event_timestamp, username, detail FROM AuthAuditLog WHERE event_type='ACCOUNT_CREATED' ORDER BY event_timestamp` |
| CC6.3 — Logical access — modification + removal | UPDATE AppUser SET is_active=FALSE (deactivation; preserves audit trail vs DELETE); WebAuthn credential deregister via `/auth/webauthn/credentials/<id>/delete` | `SELECT username, is_active FROM AppUser` + `SELECT event_timestamp, username, detail FROM AuthAuditLog WHERE event_type='WEBAUTHN_DEREGISTERED'` |
| CC6.4 — Physical access controls | n/a Polaris (physical security is operator-side; cloud provider's data center handles for cloud deployments) | (operator provides) |
| CC6.5 — Logical and physical protections — disposal | uc_archive_purge() with LifecycleArchiveCheckpoint (v8.87 carve-out) for audit-class data; pgbackrest backup retention policies for operational data | `SELECT * FROM LifecycleArchiveCheckpoint ORDER BY purged_at DESC LIMIT 10` |
| CC6.6 — Logical access — boundary protections | Caddyfile rate limit (200 req/min/IP, G27) + per-IP token bucket (R8-2) + CSP `script-src 'self'` (C5) + CSRF (form + X-CSRFToken header) | `curl -sI https://${POLARIS_DOMAIN} \| grep -E "Strict-Transport-Security\|Content-Security-Policy\|X-Frame-Options"` |
| CC6.7 — Restricted to authorized users | @login_required + @require_role decorators (51 + 25 occurrences in app.py); structural invariants enforce coverage | `grep -c "@login_required\|@require_role" polaris_web/app.py` |
| CC6.8 — Information sensitivity classification | C2 (privacy-preserving disclosure: ZK-NULL / partial / full); chk_disclosure_token_consistency CHECK constraint enforces | `SELECT count(*), disclosure_level FROM VerificationEvent GROUP BY disclosure_level` |

---

## 8. CC7 — System operations

| Control | Polaris contribution | Evidence query |
|---|---|---|
| CC7.1 — Detection of vulnerabilities | Annual pen-test cycle (PENTEST.md); structural-invariant test suite catches drift; CT monitoring (v9.01 polaris-ct-monitor.sh) | `cat docs/operator/PENTEST.md` + `./scripts/polaris-ct-monitor.sh --check ${POLARIS_DOMAIN}` |
| CC7.2 — Monitoring of system components | /api/health (G29 structured) + Prometheus /metrics (v8.93) + HYDRA watchers + Mycelium swarm | `curl -sf https://${POLARIS_DOMAIN}/api/health \| jq .checks` + `curl -sf https://${POLARIS_DOMAIN}/metrics \| head -20` |
| CC7.3 — Detected anomalies are evaluated | HYDRA findings written to journal; SEV-1/SEV-2 trigger DR.md § 6 on-call playbook | `ls journal/ \| grep -i incident \| head -10` |
| CC7.4 — Incident response procedures | DR.md § 4 (procedures by failure class); § 6 on-call playbook; § 8 post-incident review template | `cat docs/operator/DR.md` (auditor inspects) |
| CC7.5 — Recovery from incidents | DR.md § 4 procedures; quarterly drill cadence (§ 5); preventive-actions tracking (§ 7.4 template) | `ls journal/ \| grep dr-drill \| tail -8` (last 2 years of quarterly drills) |

---

## 9. CC8 — Change management

| Control | Polaris contribution | Evidence query |
|---|---|---|
| CC8.1 — Authorizes + designs + tests + approves changes | Schema migration framework (v8.95) requires actor_user_id + SHA-256 file hash + .up.sql AND .down.sql pair; CI/CD pipeline (v8.93 .github/workflows/ci.yml) blocks merges with failing tests; Sanctum protocol for HIGH-risk decisions | `SELECT name, event_type, occurred_at, actor_user_id, file_sha256 FROM schema_version ORDER BY occurred_at DESC LIMIT 50` + `cat .github/workflows/ci.yml` |

---

## 10. CC9 — Risk mitigation

| Control | Polaris contribution | Evidence query |
|---|---|---|
| CC9.1 — Mitigation of business disruptions | DR runbook + RPO/RTO targets + drill cadence (DR.md) | `cat docs/operator/DR.md` § 1 (auditor confirms targets are documented + drilled) |
| CC9.2 — Vendor + business partner risk | Polaris dependencies are minimal (psycopg2 + flask + werkzeug + webauthn + cryptography + Plonky2/Rust crate); each is a well-known library; vendor-risk assessments are operator-side | `pip3 freeze \| grep -E "^(psycopg2\|flask\|werkzeug\|webauthn\|cryptography)"` |

---

## 11. Availability — A1

| Control | Polaris contribution | Evidence query |
|---|---|---|
| A1.1 — System availability monitored | /api/health + Prometheus /metrics + alerting rules (PolarisHigh5xx, PolarisSwarmDormant) | `curl -sf https://${POLARIS_DOMAIN}/metrics \| grep polaris_app_info` |
| A1.2 — Backup + recovery procedures | DR.md § 4 (procedures); polaris-backup.sh + polaris-restore.sh; pgbackrest WAL archive | (see CC7 evidence + drill journal entries) |
| A1.3 — Recovery testing | DR.md § 5 quarterly drill cadence; logged in `journal/<date>-dr-drill-<class>.md` | `ls journal/ \| grep dr-drill` |

---

## 12. Confidentiality — C1

(Note: this "C1" is the SOC2 Confidentiality TSC, not Polaris's
constitutional constraint C1. Disambiguation: when a control's
evidence references "C1", the context disambiguates — SOC 2 C1
appears in audit-facing tables; Polaris C1 appears in MISSION.md +
threat-model.md.)

| Control | Polaris contribution | Evidence query |
|---|---|---|
| C1.1 — Confidential information identified + protected | C2 (privacy-preserving disclosure); ZK-NULL verification (R10-1 / M2-1); biometric template column-level encryption (consideration); KMS-backed secrets (SECRETS.md § 8) | `cat DEVNOTES/threat-model.md \| grep -A2 "I-I"` |
| C1.2 — Disposal of confidential information | uc_archive_purge() with LifecycleArchiveCheckpoint (v8.87); pg_dump/pgbackrest retention policies | `SELECT * FROM LifecycleArchiveCheckpoint` |

---

## 13. Evidence-collection recipes

The most-asked-for auditor questions, pre-built as SQL recipes:

### 13.1 "Show me all admin authentications in Q3"

```sql
SELECT
    u.username,
    l.event_timestamp,
    l.event_type,
    l.ip_address,
    l.user_agent
FROM AuthAuditLog l
LEFT JOIN AppUser u ON u.user_id = l.user_id
WHERE u.role = 'admin'
  AND l.event_type IN ('LOGIN_SUCCESS', 'LOGIN_FAILED', 'LOGIN_LOCKED',
                       'WEBAUTHN_ASSERTED', 'WEBAUTHN_ASSERTION_FAILED',
                       'EMERGENCY_PASSWORD_LOGIN_AUTHORIZED')
  AND l.event_timestamp >= '2026-07-01' AND l.event_timestamp < '2026-10-01'
ORDER BY l.event_timestamp;
```

### 13.2 "Show me every schema change in the audit period"

```sql
SELECT
    name,
    event_type,
    occurred_at,
    actor_user_id,
    file_sha256
FROM schema_version
WHERE occurred_at >= '<period start>' AND occurred_at < '<period end>'
ORDER BY occurred_at;
```

### 13.3 "Show me all token revocations + their reasons"

```sql
SELECT
    t.token_id,
    t.revoked_at,
    r.reason_code,
    r.detail,
    u.username AS revoked_by
FROM IdentityToken t
JOIN RevocationList r ON r.token_id = t.token_id
LEFT JOIN AppUser u ON u.user_id = r.actor_user_id
WHERE t.revoked_at IS NOT NULL
ORDER BY t.revoked_at DESC;
```

### 13.4 "Show me every emergency-password-login authorization"

```sql
SELECT
    event_timestamp,
    username,
    detail
FROM AuthAuditLog
WHERE event_type = 'EMERGENCY_PASSWORD_LOGIN_AUTHORIZED'
ORDER BY event_timestamp DESC;
```

### 13.5 "Show me every audit-log purge that occurred"

```sql
SELECT
    purged_at,
    cutoff_timestamp,
    archive_uri,
    archive_sha256,
    actor_user_id,
    rows_purged_total
FROM LifecycleArchiveCheckpoint
ORDER BY purged_at DESC;
```

### 13.6 "Confirm append-only enforcement is active"

```sql
-- Should show triggers on TokenLifecycleEvent, VerificationEvent,
-- EnrollmentStatusEvent, AnchorBatch, RecoveryRequest, TokenSignature,
-- AgencyTrustAttestation, TokenStateEpoch, DuressEvent,
-- LifecycleArchiveCheckpoint, schema_version
SELECT
    n.nspname AS schema,
    c.relname AS table_name,
    t.tgname AS trigger_name,
    pg_get_triggerdef(t.oid) AS definition
FROM pg_trigger t
JOIN pg_class c ON c.oid = t.tgrelid
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE t.tgname LIKE '%append_only%' OR t.tgname LIKE '%audit_modification%'
ORDER BY c.relname;
```

### 13.7 "Confirm WebAuthn-MFA is enforced for admin"

```sql
-- Each admin should have either:
--   - webauthn_required_after IN THE PAST  (MFA enforced)
--   - at least one OperatorWebauthnCredential row
-- Or be a legacy account explicitly exempted.
SELECT
    u.username,
    u.role,
    u.webauthn_required_after,
    count(c.credential_id) AS enrolled_credentials
FROM AppUser u
LEFT JOIN OperatorWebauthnCredential c ON c.user_id = u.user_id
WHERE u.role = 'admin' AND u.is_active = TRUE
GROUP BY u.username, u.role, u.webauthn_required_after
ORDER BY u.username;
```

---

## 14. Known limitations

For audit transparency, here are the Polaris design decisions that
**limit** the scope of certain SOC 2 controls:

1. **Polaris is reference-implementation, not production SaaS.**
   Operators deploying Polaris into a SOC-2-attested environment
   carry the operator-layer controls (vendor management, employee
   onboarding, business continuity) on their own; this document
   covers only Polaris's contribution.

2. **Multi-region deployment is Phase 3 deferred** (per
   `sanctum/2026-05-14-phase-3-opening.md` § II Position B
   weakness). Operators with cross-region availability requirements
   should track the multi-region work as a known-not-yet-shipped
   item; alternative: deploy Polaris in their preferred single
   region with explicit RPO/RTO communicated to customers.

3. **Distributed tracing is Phase 3 deferred** (gated on Phase 2.5
   multi-instance). For single-instance deployments, the
   /api/health structured JSON + Prometheus /metrics + AuthAuditLog
   provide sufficient observability for SOC 2 CC4 + CC7 controls.

4. **Privacy TSC is operator-side.** Polaris provides primitives
   (right-to-be-forgotten via uc8_revoke_token + uc_archive_purge;
   data-minimization via C2; consent-bound disclosure via
   TokenSignature) but doesn't ship a complete Privacy program.
   GDPR/CCPA/HIPAA mappings to Polaris primitives are documented
   in `docs/operator/PRIVACY.md` (operator's Privacy program builds
   on those).

5. **Processing Integrity TSC is operator-side.** Polaris's
   internal processing integrity (UC stored procedures + SERIALIZABLE
   + append-only audit) is enforced; PI TSC scope concerns
   end-to-end workflows wrapping Polaris (claim-handling pipelines,
   agency onboarding, etc.) which are operator-side.

---

## 15. Cross-references

- [DR.md](DR.md) — disaster recovery runbook (cited for CC7 + A1)
- [SECRETS.md](SECRETS.md) § 7 — operator authentication +
  WebAuthn (cited for CC6.2/3/7)
- [SECRETS.md](SECRETS.md) § 8 — KMS integration (cited for CC6.1
  + C1.1)
- [PENTEST.md](PENTEST.md) — pen-test schedule (cited for CC7.1)
- [OPERATIONS.md](OPERATIONS.md) — daily operations (cited for
  CC4 + CC7.2 + CC8)
- [PRIVACY.md](PRIVACY.md) — data minimization posture
  (operator's Privacy program builds on this)
- [SECURITY.md](SECURITY.md) — cybersecurity audit + controls
- `MISSION.md` — C1-C10 constitutional constraints
- `DEVNOTES/threat-model.md` — STRIDE threat model (cited for CC3.2)
- `polaris_sql/01_schema.sql` — schema CHECK constraints (cited
  for CC2.1)
- `scripts/polaris-*.sh` — operator scripts (cited throughout)
- `sanctum/` — strategic-decision audit-of-record (cited for CC3.4)
- `journal/` — episodic-memory audit-of-record (cited for CC4.2)

---

**Maintenance:** when a new SOC 2 audit cycle begins, update
each "Evidence query" block with the audit period dates, run
each query, archive the output to `evidence/SOC2-Q<N>-<YYYY>/`,
and SHA-256-manifest the archive. The auditor receives this
package as the answer to "show me your evidence for control X."
The package is itself audit-of-record (filesystem AoR per v8.20).
