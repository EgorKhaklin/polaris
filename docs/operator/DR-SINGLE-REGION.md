# Disaster recovery — single-region runbook

**Origin:** BIG MISSION Sanctum (`sanctum/2026-05-15-big-mission.md`),
item High #2 (refused as multi-region; shipped as single-region per
v9.16 RESERVED-NOT-PLANNED constraint)
**Status:** Active runbook for the current single-region deployment
**Last reviewed:** 2026-05-15 (v9.23)
**Companion:** `docs/operator/DR.md` (v9.01 backup philosophy);
this document scopes RPO/RTO + procedures explicitly to single-region

---

## Why this is single-region

The BIG MISSION asked for multi-region DR. It was refused on the
grounds that v9.16 resolved multi-region as RESERVED-NOT-PLANNED. The
resolution: ship single-region DR with documented RPO/RTO targets;
multi-region remains held in reserve until external triggers fire
(at least 10x verification volume, a partner deployment, or a
federation requirement).

This document is the single-region DR runbook. The multi-region
equivalent will be a future Sanctum when triggers fire.

---

## Recovery objectives

### RPO (Recovery Point Objective): 24 hours

The maximum acceptable data loss in a disaster scenario. This number
is set by the backup cadence: daily backup at 03:00 UTC via
`scripts/polaris-backup.sh`. A disaster at 02:59 UTC could lose up to
24 hours of identity events.

**Improving RPO:** the cadence can be tightened to hourly (RPO = 1
hour) by adjusting the crontab entry. The cost is backup storage
volume (24× more backup tarballs) and pg_dump load on the running
database. For a reference implementation, 24 hours is appropriate.
For a production deployment, the operator should evaluate the
business cost of 24-hour data loss vs. backup-volume cost.

### RTO (Recovery Time Objective): 1 hour

The maximum acceptable downtime from disaster onset to restored
service. This is achievable for single-region single-host failures
via the documented restore procedure (Phase 3 below). For host-
total-loss (the hardware itself is gone), RTO depends on host-
provision time + restore-tarball-fetch-from-cold-storage time, which
is environment-specific.

**Documented breakdown:**

- Detect failure: 0–5 min (operator paging / `/api/health` failure)
- Provision replacement (if needed): 5–30 min (cloud) / hours (on-prem)
- Fetch latest backup tarball: 1–5 min (warm S3 / equivalent)
- Verify backup integrity: 1–2 min
  (`polaris-backup.sh --verify-latest`)
- Restore database: 5–15 min (depends on row volume)
- Restore filesystem AoR: 1–2 min
- Restart stack: 1–2 min
- Smoke-test `/api/health`: 1 min
- **Total:** 15–60 min, hitting the 1-hour target

---

## What is in scope for "disaster"

In-scope disaster scenarios:

- **Hardware failure** (disk dies, host kernel-panics, network card
  fails): restore from latest backup; service resumes
- **Data corruption** (DB integrity check fails; tampering detected):
  restore from latest known-good backup; investigate root cause
- **Software bug** (a migration corrupted data; an undocumented code
  path wiped a table): restore from latest backup; revert the bug
- **Operator error** (someone DROP TABLEd a critical table; rm -rf'd
  the wrong directory): restore from latest backup
- **Ransomware** (an attacker encrypts the DB; the backup tarballs
  are NOT on the affected host): restore from cold-storage backup;
  run security incident response

Out-of-scope scenarios (multi-region territory):

- **Regional outage** (entire AWS region fails; entire DC loses
  power): the single-region deployment is down until the region
  recovers. Multi-region would fail over; this deployment does not.
- **Targeted nation-state attack on the host itself** (physical
  destruction of the on-prem rack with all backup tapes co-located):
  geographically-distributed backup storage (the v9.01 DR.md model)
  is the partial mitigation; full mitigation requires multi-region
  (deferred per v9.16).

---

## Phase 1: pre-disaster preparation

```bash
# Daily backup (crontab, installed by polaris-cron-install.sh in v9.23)
03 00 * * * /opt/polaris/scripts/polaris-backup.sh --dest /var/backups \
            2>&1 | logger -t polaris-backup

# Off-host replication (operator-side; environment-specific)
# Example: rsync to S3 / Azure Blob / NAS / equivalent
05 00 * * * rsync -a /var/backups/polaris-*.tar.gz \
            backup-store:/polaris/$(hostname)/

# Weekly verify-latest (Sunday 04:00 UTC)
00 04 * * 0 /opt/polaris/scripts/polaris-backup.sh --verify-latest \
            2>&1 | logger -t polaris-backup-verify
```

Verify these run by checking `/var/log/syslog | grep polaris-backup`
weekly. Use the verify-latest cron output to confirm SHA-256 manifest
checks pass.

---

## Phase 2: disaster detection

The standard signals:

- **`/api/health` returns non-200** for >5 minutes
- **No `LIFECYCLE_EVENT` rows inserted** for >10 minutes during
  business hours (anomalous quiet)
- **Manual operator report** (someone notices the system is down)

Response: page the operator; open `polaris-doctor.sh` for diagnosis;
escalate to restore if root cause is corruption or data loss.

---

## Phase 3: restore procedure

```bash
# 1. Fetch the latest backup
ls -t /var/backups/polaris-*.tar.gz | head -1
# If not present locally, fetch from off-host:
#   rsync backup-store:/polaris/<host>/polaris-{latest}.tar.gz /var/backups/

# 2. Verify manifest
./scripts/polaris-backup.sh --verify-latest

# 3. If verify passes, restore (DRY-RUN first if unsure)
./scripts/polaris-restore.sh /var/backups/polaris-{ts}.tar.gz --dry-run

# 4. Real restore — to docker-stack target
./scripts/polaris-restore.sh /var/backups/polaris-{ts}.tar.gz \
    --target=docker-stack

# 5. Smoke-test
curl -fsS https://${POLARIS_DOMAIN}/api/health | jq .
psql -d polaris -c "SELECT count(*) FROM IdentityToken"
psql -d polaris -c "SELECT max(created_at) FROM TokenLifecycleEvent"

# 6. Verify schema version post-restore
psql -d polaris -c "SELECT version, applied_at FROM schema_version
                    ORDER BY applied_at DESC LIMIT 5"

# 7. Open a Sanctum for the recovery incident
./scripts/ai-sanctum.sh open dr-restore-$(date +%Y%m%d)
# Record: trigger, RPO realized, RTO realized, root cause, follow-up
```

The v9.23 hardening adds `--verify-schema-version` to
`polaris-restore.sh`: after restoring, the script cross-checks that
the `schema_version` table is consistent with the migration tree on
disk. If they diverge, the script EXITS non-zero with `EXIT_SCHEMA_MISMATCH`
and refuses to start the stack — preventing a half-restored DB from
serving traffic.

---

## Phase 4: post-recovery audit

After every recovery, the operator runs:

```bash
# Invariant integrity (C1-C10), including audit-of-record append-only triggers
python3 -m polaris_checks.run

# Audit-of-record chain intact on the restored DB
psql -d polaris -c "SELECT count(*) FROM TokenLifecycleEvent"

# Open Sanctum recording the recovery (decision record)
./scripts/ai-sanctum.sh close dr-restore-... \
    --position recovered \
    --decision "restored from $(date -u -d '24 hours ago' +%Y%m%d) backup; \
                RPO realized: N hours; RTO realized: M minutes; \
                root cause: ..."
```

The Sanctum is a filesystem decision record. Every recovery adds an
entry to the record.

---

## Drill cadence

A DR drill should be run quarterly:

```bash
# Restore the latest backup to a separate database (not the live one)
./scripts/polaris-restore.sh /var/backups/polaris-{latest}.tar.gz \
    --target=polaris_dr_drill

# Smoke-test the drill DB
psql -d polaris_dr_drill -c "SELECT count(*) FROM IdentityToken"

# Drop the drill DB after verification
dropdb polaris_dr_drill
```

The drill itself is added to the crontab by
`polaris-cron-install.sh` (v9.23). The drill output is logged; failures
emit an alert.

---

## Constraints honored

- **C1 audit-of-record:** every restore writes a Sanctum file; every
  Sanctum is in git; the chain is preserved.
- **v9.16 RESERVED-NOT-PLANNED:** this document EXPLICITLY does not
  ship multi-region. Multi-region requires a new Sanctum + named
  triggers per v9.16.
- **C3 one-identity-per-person:** a restore from a backup that
  predates a fork (an individual gained then lost a token) restores
  to the pre-fork state. The partial unique index re-establishes
  on the restored data. No fork-state can survive a restore.

---

## Vocation alignment

ANTI-COERCION-INDIRECT. Availability under attack is itself
anti-coercion: a coerced operator cannot be told "the system is down,
do it manually outside the audit trail" when the system is restorable
within an hour. The documented RTO is itself a coercion-defense
primitive.

The drill cadence (quarterly) is anti-coercion-structural: a coerced
operator could fail to run drills, letting the recovery capacity
silently atrophy. The cron-installed drill catches this; the alert
on drill failure means a silently-missed drill is detected.

---

## Multi-region (deferred)

When external triggers fire (per v9.16):

1. Open a Sanctum: `sanctum/YYYY-MM-DD-multi-region-opening.md`
2. Record the specific scope and the dissent against it
3. Operator decides
4. Multi-region implementation flows from there

This document does not pre-commit any multi-region design. The v9.16
RESERVED-NOT-PLANNED clause is binding until the Sanctum opens.

---

*Per BIG MISSION Sanctum, 2026-05-15. Single-region scope by design;
multi-region held in reserve per v9.16.*
