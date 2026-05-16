# DR.md — Polaris disaster recovery runbook (v9.01 / Phase 3 Wave 1)

This document is the operator's playbook when something goes wrong:
the database loses a tablespace, a host fails, an admin authenticator
is lost, ransomware encrypts the disk, an entire region goes dark,
or a more mundane operator-error wipes a critical row.

It is written for the **on-call engineer at 03:00 with an open
incident**, not for the architect at design time.

---

## Table of contents

1. [Targets — RPO and RTO](#1-targets-rpo-and-rto)
2. [Severity matrix](#2-severity-matrix)
3. [Decision tree — what failed](#3-decision-tree-what-failed)
4. [Procedures by failure class](#4-procedures-by-failure-class)
   - 4.1 [Application crash / container exit](#41-application-crash-container-exit)
   - 4.2 [Database corruption — single table](#42-database-corruption-single-table)
   - 4.3 [Database corruption — full-cluster](#43-database-corruption-full-cluster)
   - 4.4 [Disk full / volume exhaustion](#44-disk-full-volume-exhaustion)
   - 4.5 [TLS cert expired / chain broken](#45-tls-cert-expired-chain-broken)
   - 4.6 [Locked-out admin (no WebAuthn authenticator)](#46-locked-out-admin)
   - 4.7 [Ransomware / encrypted volume](#47-ransomware-encrypted-volume)
   - 4.8 [Region-wide outage](#48-region-wide-outage)
5. [Drill cadence](#5-drill-cadence)
6. [On-call playbook](#6-on-call-playbook)
7. [Communications templates](#7-communications-templates)
8. [Post-incident review](#8-post-incident-review)
9. [Cross-references](#9-cross-references)

---

## 1. Targets — RPO and RTO

| Target | Value | Source / Mechanism |
|---|---|---|
| **RPO** (Recovery Point Objective) | **≤ 1 minute** | pgbackrest WAL archiving (v8.93 OPERATIONS.md §"Point-in-time recovery"). Continuous WAL stream → S3 (or equivalent). Worst-case data loss = unflushed WAL between disk write and S3 upload. |
| **RTO** (Recovery Time Objective) | **≤ 30 minutes** | polaris-restore.sh (v8.81) drill measurement on a single-host stack with sample-size data. Larger volumes scale roughly linearly with database size; estimate: +5 min per 10 GB compressed pg_dump. |
| **MTTR** (Mean Time To Restore — incident detection → service restored) | **≤ 60 minutes** | RTO + 30 min for detection (alert → on-call → triage → decide-to-restore). Tighten by reducing detection latency (alert thresholds tuned per OPERATIONS.md). |

These are the **published** targets. Internal team SLOs may be
tighter; operator's compliance regime (SOC 2, FedRAMP, PCI) may
demand specific values — see [SOC2.md](SOC2.md) § Availability for
the auditor-facing version.

**RPO=1 min is achievable only if WAL archiving is healthy.**
Verify daily:
```bash
pgbackrest --stanza=polaris check
```
If this fails, the RPO regresses to the last successful base backup
(default: 24h). Treat as SEV-2 incident.

---

## 2. Severity matrix

| Severity | Definition | Response time | Escalation |
|---|---|---|---|
| **SEV-1** | Total service outage; users cannot log in or perform any operation | Immediate (page on-call within 5 min) | Page secondary on-call within 15 min if no acknowledgment |
| **SEV-2** | Major degradation; one core flow broken (e.g. token issuance failing) OR data-integrity risk (e.g. WAL archiving stopped) | Within 15 min | Secondary on-call within 30 min |
| **SEV-3** | Minor degradation; one non-critical surface broken (e.g. atlas tile cache cold) OR isolated user impact | Within 1 hour | Secondary on-call if unresolved at 4h |
| **SEV-4** | Cosmetic or single-user issue with workaround | Next business day | None |

The Polaris alert layer (v8.93 Prometheus `/metrics` endpoint) emits
metrics that map to severity: `polaris_app_info` absent → SEV-1;
`polaris_db_query_latency_seconds` p99 > 5s → SEV-2; etc.
PolarisHigh5xx and PolarisSwarmDormant Prometheus alerting rules
(OPERATIONS.md) classify automatically.

---

## 3. Decision tree — what failed

```
Is /api/health responding at all?
├── No  → § 4.1 Application crash
└── Yes → check the JSON body
    │
    ├── status: "unhealthy"
    │   └── which check?
    │       ├── database  → § 4.2 or § 4.3
    │       ├── redis     → restart redis container; if persistent, § 4.1 (cascade)
    │       ├── zk_binary → R10-1 epoch closes will fail; non-blocking for token issue/verify
    │       └── disk      → § 4.4
    │
    ├── status: "degraded"
    │   └── continue serving but investigate; usually disk usage > 80% or zk_binary missing
    │
    └── status: "healthy" but users report issues
        └── check Caddy logs (TLS handshake failures) → § 4.5
            check AuthAuditLog (login failures) → § 4.6
```

---

## 4. Procedures by failure class

### 4.1 Application crash / container exit

**Symptoms:** /api/health returns connection-refused or 502; gunicorn
PID gone; docker compose ps shows app restarting in a loop.

**Procedure:**

```bash
# 1. Check the immediate cause — usually visible in the last 200
#    log lines.
docker compose -f polaris_web/docker-compose.prod.yml logs --tail=200 app

# 2. Common causes + fixes:
#    - "Connection refused" to postgres → § 4.2/4.3
#    - "OperationalError" missing column → schema migration drift;
#      run polaris-migrate.sh --status; apply pending if safe (see SOC2.md)
#    - "ImportError: webauthn" → pip dependency missing in image;
#      rebuild via ./scripts/polaris-deploy.sh prod --rebuild
#    - "OOMKilled" → raise container memory limit in docker-compose.prod.yml

# 3. If cause is transient (single crash, restart loop now stable),
#    monitor /api/health for 15 min and resume. If unstable, escalate
#    to SEV-1 and proceed to § 4.7 (full restore from backup).
```

### 4.2 Database corruption — single table

**Symptoms:** /api/health database check OK, but specific queries
return "ERROR: invalid page in block" OR specific tables fail
SELECT but neighbors are fine.

**Procedure:**

```bash
# 1. Verify table-level corruption with pg's heap check
docker compose exec postgres psql -U postgres -d polaris -c "
    SELECT * FROM pg_stat_database_conflicts WHERE datname='polaris';
"

# 2. Restore the affected table from the most recent pg_dump
#    (NOT the full DB — cherry-pick the table only).
TARGET_TABLE=identitytoken
TIMESTAMP=$(date -u +%Y%m%dT%H%M%S)

#    a. Pull the latest backup tarball
ls -lt polaris-backups/ | head -3

#    b. Extract just the table's pg_dump section
pg_restore -t "$TARGET_TABLE" -f /tmp/restore-${TARGET_TABLE}.sql polaris-backups/polaris-LATEST.tarball

#    c. Drop + restore the affected table
#       (CASCADE if FKs depend on it; review carefully)
docker compose exec postgres psql -U postgres -d polaris -c "
    BEGIN;
    DROP TABLE ${TARGET_TABLE} CASCADE;
    \i /tmp/restore-${TARGET_TABLE}.sql
    COMMIT;
"

# 3. Re-run /api/health and the affected queries to verify.
```

**Audit-of-record concern:** restoring an audit-class table
(TokenLifecycleEvent, VerificationEvent, AuthAuditLog, etc.) from
a backup older than the corruption-detection time means **the
intervening events are lost** unless they're also captured in the
WAL archive. WAL replay (§ 4.3) preserves every event up to the
moment of corruption; per-table restore loses the window between
the last backup and the corruption. Prefer § 4.3 WAL replay for
audit-class tables.

### 4.3 Database corruption — full-cluster

**Symptoms:** /api/health database check fails entirely; postgres
container won't start; pg_ctl returns "cluster is not consistent".

**Procedure:**

```bash
# 1. Stop the app immediately to prevent additional state divergence
docker compose -f polaris_web/docker-compose.prod.yml stop app

# 2. Take a forensic snapshot of the broken volume BEFORE recovery
#    (auditors will want to see what was on disk at the moment of
#    failure; ransomware investigation needs this too).
docker run --rm -v polaris_postgres_data:/data -v $(pwd):/snap \
    busybox tar czf /snap/forensic-snapshot-$(date -u +%Y%m%dT%H%M%S).tgz /data

# 3. Restore from PITR via pgbackrest, targeting the last known-good
#    timestamp (just before the corruption window).
TARGET_TIME="2026-05-14 03:14:00 UTC"

#    a. Stop postgres + clear the volume
docker compose stop postgres
docker volume rm polaris_postgres_data
docker volume create polaris_postgres_data

#    b. pgbackrest --stanza=polaris --type=time --target="$TARGET_TIME" restore

#    c. Bring postgres back up + let it apply WAL until target
docker compose up -d postgres
docker compose logs --follow postgres | grep "consistent recovery state reached"

# 4. Verify integrity
docker compose exec postgres psql -U postgres -d polaris -c "
    SELECT count(*) FROM TokenLifecycleEvent;
    SELECT count(*) FROM VerificationEvent;
    SELECT max(occurred_at) FROM TokenLifecycleEvent;
"

# 5. Bring app back up + smoke-test
docker compose up -d app
curl -sf https://${POLARIS_DOMAIN}/api/health | jq .
```

**Audit-of-record continuity:** WAL replay preserves every event
up to the target timestamp. Events between target time and the
moment of corruption ARE lost; document this in the post-incident
review (§ 8) so the auditor can reconcile any holder-reported
verification events that don't appear in the restored database.

### 4.4 Disk full / volume exhaustion

**Symptoms:** /api/health disk check fails (used_pct > 90%); writes
fail with "no space left on device"; postgres may have stopped
accepting transactions (WAL writes blocked).

**Procedure:**

```bash
# 1. Identify what's filling the disk
df -h | head -5
du -sh /var/lib/docker/volumes/polaris_*/_data | sort -h | tail -5

# 2. Common culprits:
#    a. WAL archive backlog (pgbackrest archive_command failed silently)
#       Fix: pgbackrest --stanza=polaris check; resume archive_command
#    b. Audit-log accumulation (5y+ retention)
#       Fix: ./scripts/polaris-rotate-logs.sh (v8.93 archive→verify→purge)
#    c. Application logs (Caddy + gunicorn access logs)
#       Fix: /etc/logrotate.d/polaris (sample in OPERATIONS.md § "Log rotation")

# 3. Emergency space-recovery (LAST RESORT — destructive):
#    docker volume prune (drops orphaned volumes; safe if nothing else uses Docker)
#    docker system prune -a (drops orphaned images; rebuild from registry on next deploy)

# 4. Once disk has ≥20% free, restart any halted services
docker compose restart postgres app
```

### 4.5 TLS cert expired / chain broken

**Symptoms:** users see browser cert warnings; curl --insecure works
but normal curl fails; Caddy logs show TLS handshake errors.

**Procedure:**

```bash
# 1. Check current cert state
echo | openssl s_client -connect ${POLARIS_DOMAIN}:443 -servername ${POLARIS_DOMAIN} 2>/dev/null \
    | openssl x509 -noout -dates -issuer -subject

# 2. Force Caddy to re-acquire from Let's Encrypt
docker compose exec caddy caddy reload --config /etc/caddy/Caddyfile
docker compose logs --tail=50 caddy | grep -i "obtaining\|certificate\|tls"

# 3. If LE is rate-limiting (50 certs/week per registered domain), wait
#    for the window to reset OR temporarily switch to staging:
#    edit Caddyfile to add `acme_ca https://acme-staging-v02.api.letsencrypt.org/directory`
#    THEN reload, THEN switch back to prod ACME and reload again.

# 4. Verify CT monitoring caught any anomalous issuance
./scripts/polaris-ct-monitor.sh --check ${POLARIS_DOMAIN}
```

### 4.6 Locked-out admin (no WebAuthn authenticator)

**Symptoms:** admin reports they cannot log in; their authenticator
device is lost / broken / forgotten somewhere; their `webauthn_required_after`
deadline has passed.

**Procedure:**

```bash
# Path A — second-admin pairing (preferred when ≥2 admins exist)
./scripts/polaris-recover-admin.sh \
    --target locked-out-admin-username \
    --authorizing-user-id <your-admin-user-id> \
    --window-minutes 15

# The locked-out admin has 15 minutes to log in with password only
# AND enroll a fresh authenticator at /settings/webauthn before the
# window closes. EMERGENCY_PASSWORD_LOGIN_AUTHORIZED audit row is
# written.

# Path B — printed mnemonic (solo-admin deployment)
# The admin pulls their printed recovery code from the safe and
# uses it. (The in-app verification flow is deferred per Sanctum
# 2026-05-14-webauthn-operator-auth.md § V; for v9.01, the manual
# path is: SSH to host, run polaris-recover-admin.sh as the same
# user, supplying the printed code as authorization evidence.
# Operationally this is a self-pair using the printed code as
# the second factor.)
```

See [SECRETS.md](SECRETS.md) § 7 for the full enrollment + recovery
runbook.

### 4.7 Ransomware / encrypted volume

**Symptoms:** files have unfamiliar extensions; postgres won't start
because data files are unreadable; ransom note in the deploy
directory.

**Procedure:**

```bash
# CRITICAL: do NOT pay the ransom. Do NOT restart anything until
# step 1 completes.

# 1. Disconnect the host from the network IMMEDIATELY (prevents
#    lateral movement to backups + buys time for forensics)
sudo ifconfig eth0 down  # or unplug the cable

# 2. Take a forensic disk image BEFORE any recovery action
sudo dd if=/dev/sda of=/external-drive/forensic-image.img bs=4M status=progress

# 3. Verify backups are NOT also encrypted
#    a. pgbackrest backups in S3 (bucket should be in a separate AWS
#       account with versioning + MFA-delete; ransomware can't reach
#       across the trust boundary)
aws s3 ls s3://${POLARIS_BACKUP_BUCKET}/ --recursive | tail -10

#    b. Filesystem AoR backups (sanctum/, journal/, treasury-roll.json)
#       — these should be in the same offsite bucket with the same MFA-delete

# 4. Provision a fresh host (different region, different credentials,
#    different SSH keys); install Polaris from clean source; restore
#    from offsite backup.

# 5. Forensic analysis (parallel to recovery):
#    - Identify entry vector (SSH brute-force? compromised SSH key? supply-chain?)
#    - Identify lateral movement (did attacker reach the database?
#      check pgbackrest restore for ransomware signatures in the
#      restored data — if ANY base backup is encrypted, the attacker
#      was inside before the cut, restore from BEFORE the suspect
#      backup window)
#    - Notify legal + compliance (GDPR breach notification = 72h
#      from discovery if PII potentially exposed)

# 6. Post-recovery: rotate EVERY secret. The attacker may have
#    exfiltrated POLARIS_SECRET_KEY, database password, AppUser
#    password hashes, WebAuthn credential public keys (low-impact
#    since private keys never leave authenticators), AppUser session
#    tokens. Treat every secret as compromised.
./scripts/polaris-generate-secrets.sh --force-rotate-all
./scripts/polaris-deploy.sh prod --restart-secrets
```

### 4.8 Region-wide outage

**Symptoms:** entire AWS region down; cloud provider dashboard shows
incident; multiple services in the region unreachable.

**Procedure (current state — single-region deployment):**

Polaris's v9.01 deployment is single-region. Region-wide outage =
Polaris unavailable until the region recovers OR multi-region is
shipped (Phase 3 deferred item; gated on production-deployment-pressure
trigger).

In the interim:
1. **Communicate transparently** (see § 7 Communications templates →
   "regional outage" template). Don't promise a recovery time you
   can't meet; quote the cloud provider's status page directly.
2. **Verify backups are in a different region** (S3 cross-region
   replication should be configured; if not, that's a SEV-2 finding
   to file post-incident).
3. **Do NOT attempt a manual cross-region failover** unless the
   multi-region runbook (Phase 3 deferred) has been written +
   drilled. An untested failover during an incident creates a
   secondary incident.

Multi-region is on the deployability checklist as ⬜ Phase 3
deferred per architect's note: blocks on production-deployment-pressure
trigger; will get its own Sanctum when an operator names a real
data-locality constraint.

---

## 5. Drill cadence

Disasters that are never drilled don't get recovered from. The
on-call team must rehearse each procedure on a cadence:

| Drill | Frequency | Procedure | Pass criteria |
|---|---|---|---|
| **Backup verify** | Monthly | `./scripts/polaris-backup.sh --verify-latest` | All 6 components ✓ MANIFEST verified |
| **Restore-only drill** | Quarterly | Restore latest backup into a fresh `polaris_drill` DB; compare row counts | ±1% of production counts; admin can log in |
| **PITR drill** | Quarterly | Restore to a point-in-time 1h before now via pgbackrest | Recovered DB is consistent at target time |
| **Full-stack failover** | Half-yearly | Spin up a new host from clean source; restore from offsite backup; verify TLS issuance + admin login + token issue | < 60 min total; matches RTO target |
| **Locked-out admin recovery** | Half-yearly | Admin removes their own credential, simulates lost device, runs polaris-recover-admin.sh from a peer | < 15 min total; EMERGENCY audit row visible |
| **Ransomware tabletop** | Annual | Walk § 4.7 procedure on paper; verify each step's tool/credential is reachable from the on-call's emergency runbook | Every step has a named owner + access path |

The drills themselves produce audit-of-record evidence. Log each
drill outcome in `journal/<date>-dr-drill-<class>.md` per OPERATIONS.md
journal protocol.

---

## 6. On-call playbook

When you're paged at 03:00:

```
Step 1.  Acknowledge the page within 5 min (SEV-1) / 15 min (SEV-2).
         Stop the rotation timer.

Step 2.  Read the incident summary in the alert body. Don't open
         dashboards yet — read the alert first.

Step 3.  Open three tabs:
         (a) https://${POLARIS_DOMAIN}/api/health
         (b) Grafana / Prometheus dashboard
         (c) docker compose logs --tail=200 (via SSH)

Step 4.  Walk § 3 decision tree. Identify failure class.

Step 5.  Open the matching § 4 procedure. Follow step-by-step.
         DO NOT IMPROVISE — if a step doesn't apply, document
         in the incident channel why; don't skip silently.

Step 6.  At every state transition (started restore, restore
         complete, app reachable, smoke test passed) update the
         incident channel. Operators upstream watch this.

Step 7.  Once /api/health returns "healthy" + smoke tests pass,
         declare the incident resolved + start the post-mortem
         clock (24h to write up; 7d to internal review).

Step 8.  Close the incident in the tracking system. Note the
         actual MTTR + RPO loss (if any) in the closing comment.
```

---

## 7. Communications templates

### 7.1 Status page snippet — service degraded

```
[INVESTIGATING] We are currently investigating reports of
slowness in <component>. Some users may experience <symptom>.
Updates every 30 minutes until resolved.

— Polaris on-call
```

### 7.2 Status page snippet — service down

```
[CRITICAL] Polaris is currently unavailable. Cause is being
investigated. Estimated time to resolution: <X> minutes per our
RTO target. We will update every 15 minutes until service is
restored.

— Polaris on-call
```

### 7.3 Customer-facing — incident resolved

```
Subject: Polaris service restored — incident <ID>

Polaris was unavailable from <start UTC> to <end UTC> due to
<one-sentence cause>. Service has been restored. Total downtime:
<X> minutes.

Data impact: <none / specify>. We do not believe holder data was
exposed.

A full post-mortem will be published at <link> within 7 business
days.

— Polaris team
```

### 7.4 Internal post-incident summary template

```
INCIDENT <ID>  /  <date>  /  <severity>

TIMELINE
  HH:MM UTC  Alert fired (<which alert>)
  HH:MM UTC  On-call acknowledged
  HH:MM UTC  Root cause identified (<one sentence>)
  HH:MM UTC  Mitigation started
  HH:MM UTC  Service restored
  HH:MM UTC  Incident closed

IMPACT
  - Duration: <X> minutes
  - Users affected: <count or %>
  - Data loss: <none / X minutes of WAL>
  - SLA breach: <yes/no, by how much>

ROOT CAUSE
  <2-3 paragraphs>

MITIGATIONS APPLIED
  <bulleted list of immediate actions taken>

PREVENTIVE ACTIONS (with owners + dates)
  - [ ] <action 1>  /  owner: <name>  /  by: <date>
  - [ ] <action 2>  /  owner: <name>  /  by: <date>

LESSONS
  <2-3 sentences capturing what we learned and what we'd do
  differently next time>
```

---

## 8. Post-incident review

Every SEV-1 and SEV-2 incident gets a **blameless post-mortem**
within 7 business days. The post-mortem is filed in
`journal/<date>-incident-<ID>.md` (Polaris's filesystem AoR)
and produces preventive-action tickets in the operator's tracking
system.

**Blameless** means the post-mortem focuses on **systems and
processes**, not individuals. Even when an operator made a
mistake, the question is: what process let that mistake reach
production? Adversarial framing here trains people to hide
mistakes; blameless framing trains them to surface mistakes
before they cause incidents.

The §7.4 template above is the canonical structure. Reviewers
look for:
- Was the root cause correctly identified?
- Are the preventive actions specific + actionable + assigned?
- Are the lessons captured at the right level of generality?
- Is there an audit trail (commits, AuthAuditLog rows, deploy
  logs, etc.) backing each timeline entry?

---

## 9. Cross-references

- [OPERATIONS.md](OPERATIONS.md) — day-to-day operations runbook
  (this DR doc is the **incident** runbook)
- [SOC2.md](SOC2.md) — SOC 2 readiness checklist (Availability TSC
  cites this DR doc + the drill cadence as evidence)
- [SECRETS.md](SECRETS.md) § 7 — operator authentication +
  WebAuthn recovery
- [SECRETS.md](SECRETS.md) § 8 — HSM/KMS integration (relevant for
  § 4.7 ransomware recovery — cloud-KMS-backed secrets cannot be
  exfiltrated by attackers without compromising the cloud account)
- [PENTEST.md](PENTEST.md) — penetration test schedule (ransomware
  is a common pen-test scenario; see § 4.7)
- `scripts/polaris-restore.sh` (v8.81) — full-DB restore
- `scripts/polaris-backup.sh` (v8.77) — backup creation
- `scripts/polaris-archive.sh` (v8.84) + `scripts/polaris-purge.sh` (v8.87)
  — audit-log archive + purge
- `scripts/polaris-recover-admin.sh` (v8.97) — locked-out admin
  recovery
- `scripts/polaris-ct-monitor.sh` (v9.01) — TLS cert anomaly
  monitoring (early detection of cert-misissuance attacks)
- `polaris_web/docker-compose.prod.yml` — production stack composition
- `DEVNOTES/threat-model.md` — STRIDE threat-model that this DR
  runbook responds to

---

**Maintenance:** when a new failure class is encountered in
production OR an existing procedure is found inadequate during
a drill, update this document AND link the change to a
post-mortem entry in the journal. Never let a real-incident
finding stay only in slack — it has to land here.
