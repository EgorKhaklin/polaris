# FAILOVER.md: streaming replication, hot standby, and failover

This is the runbook for running a Postgres hot standby and promoting it when the
primary fails. It is the high-availability counterpart to [`DR.md`](DR.md)
(which restores from a backup); replication keeps a second copy continuously
current so a primary loss costs seconds, not the backup interval.

> **Honest status (v9.126).** Polaris ships replication **readiness**, not a
> running standby. The primary is made replication-ready at init
> (`wal_level=replica`, a least-privilege `polaris_replicator` role, the `pg_hba`
> entry) when the operator provides the `polaris_replicator_password` secret, and
> the bootstrap below is proven in CI (a write on the primary appears on a
> `pg_basebackup`-cloned standby). What is **operator-gated**: the **standby
> host** (a second machine; co-locating a standby on the primary's host gives no
> availability benefit) and the **failover decision** (promotion is a documented
> manual procedure, not an automated controller like Patroni or repmgr, which
> stay operator choices). No data is replicated until the operator stands up a
> standby on their own second host.

---

## Table of contents

1. [What ships vs. what the operator supplies](#1-what-ships-vs-what-the-operator-supplies)
2. [Bring up a standby](#2-bring-up-a-standby)
3. [Failover: promote the standby](#3-failover-promote-the-standby)
4. [After failover: re-establish redundancy](#4-after-failover-re-establish-redundancy)
5. [RPO/RTO with streaming replication](#5-rporto-with-streaming-replication)
6. [Cross-references](#6-cross-references)

---

## 1. What ships vs. what the operator supplies

**Ships (made ready by `docker-init.sh` when `polaris_replicator_password` is
mounted):**

- `wal_level=replica`, `max_wal_senders`, `max_replication_slots`,
  `hot_standby=on`, `wal_log_hints=on`, persisted via `ALTER SYSTEM`.
- A `polaris_replicator` role with `LOGIN REPLICATION` and nothing else (it
  cannot read application data; it can only stream WAL).
- A `pg_hba.conf` line allowing the replication role from
  `POLARIS_REPLICATION_CIDR` (default `samenet`; set the real CIDR for a remote
  standby).
- `scripts/polaris-generate-secrets.sh` mints the replication password.

**Operator-supplied:**

- The **standby host** (a separate machine or VM; for real HA it must not share
  the primary's failure domain).
- The **failover decision** and, if wanted, an automated promotion controller.
- For zero data loss, a choice to run **synchronous** replication (see §5).

---

## 2. Bring up a standby

On the operator's second host, with network reach to the primary's Postgres
port and the `polaris_replicator` password to hand, clone the primary into the
standby's data directory. `pg_basebackup -R` writes both `standby.signal` and
`primary_conninfo`, so the cloned directory starts as a streaming standby with
no further edits.

```bash
# As the postgres user, with an EMPTY target data dir ($PGDATA):
PGPASSWORD='<polaris_replicator_password>' \
  pg_basebackup \
    --host=<primary-host> --port=5432 \
    --username=polaris_replicator \
    --pgdata="$PGDATA" \
    --wal-method=stream \
    --write-recovery-conf          # -R: writes standby.signal + primary_conninfo

chmod 0700 "$PGDATA"               # postgres refuses a looser data dir
pg_ctl -D "$PGDATA" start
```

Verify the standby is streaming:

```bash
# On the standby — must report 't' (it is in recovery, read-only):
psql -tAc 'SELECT pg_is_in_recovery();'

# On the primary — must list the standby's connection:
psql -tAc "SELECT application_name, state, sync_state FROM pg_stat_replication;"
```

A row written on the primary should now appear on the standby within a second.
This is exactly the round-trip the CI `Streaming-replication primary -> standby`
job asserts on every build.

---

## 3. Failover: promote the standby

**Trigger.** The primary is unreachable: `PolarisAppDown` /
`PolarisHighDBLatency` firing, the primary host or its Postgres is down, and the
outage is not a transient blip. Failover is a deliberate decision (promoting
while the old primary is merely partitioned risks split-brain).

**Diagnosis.**
1. Confirm the primary is genuinely gone, not partitioned from you but alive to
   clients. If there is any chance it is still serving writes, **do not promote**
   (two primaries accepting writes is split-brain; the divergent histories
   cannot be cleanly merged afterward).
2. Confirm the standby is current: on the standby,
   `SELECT pg_last_wal_replay_lsn();` and compare to the last known primary LSN
   if reachable. A standby far behind means accepting more data loss.

**Remediation.**
1. **Fence the old primary** so it cannot accept writes (stop its container /
   host, or block its client port). This is the split-brain guard.
2. **Promote the standby** to a read-write primary:
   ```bash
   psql -tAc 'SELECT pg_promote();'     # or: pg_ctl -D "$PGDATA" promote
   # pg_is_in_recovery() now returns 'f'.
   ```
3. **Repoint the application at the new primary.** Update
   `POLARIS_DB_HOST` (and the pgbouncer `POLARIS_DB_HOST`) to the promoted host
   and restart the app + pgbouncer so the pool reconnects. The app and pooler
   are stateless; only the DB endpoint changes.
4. **Confirm recovery.** `/api/health/ready` returns 200; a write succeeds; the
   `PolarisAppDown` / DB-latency alerts clear.

---

## 4. After failover: re-establish redundancy

A promoted standby is a single point of failure until a new standby backs it up.

1. Treat the old primary as **destroyed** (do not bring it back as a primary —
   it may have diverged). When convenient, rebuild it as a fresh standby of the
   new primary using §2 (`pg_basebackup -R` from the new primary).
2. Re-run a backup (`scripts/polaris-backup.sh`) against the new primary so the
   [`DR.md`](DR.md) restore path is current for the new topology.
3. Update whatever records the primary endpoint (DNS, the compose
   `POLARIS_DB_HOST`, your runbook) so the next operator inherits the truth.

---

## 5. RPO/RTO with streaming replication

- **Asynchronous streaming (the default here)** keeps the standby within
  seconds of the primary, so an unplanned failover loses at most the last
  in-flight transactions, not the [`DR.md`](DR.md) backup interval. The headline
  ≤1-minute RPO target in `DR.md` is met by replication far more tightly than by
  the periodic `pg_dump`, for the failure class where the standby survives.
- **Synchronous replication** (`synchronous_standby_names`, an operator choice)
  makes RPO zero for committed transactions, at the cost of commit latency and a
  liveness coupling (a commit waits for the standby). Polaris does not enable it
  by default because it trades availability for durability in a way only the
  operator can weigh; the knob is theirs.
- Replication does **not** replace backups. It does not protect against a logical
  error replicated to the standby (a bad migration, an erroneous bulk update);
  for that, the point-in-time / `pg_dump` path in `DR.md` is the recovery, and
  the append-only audit-of-record (C1) is the integrity anchor.

---

## 6. Cross-references

- [`DR.md`](DR.md): backup/restore recovery and the SEV ladder; failover is the
  HA complement (seconds of loss vs. the backup interval).
- [`OPERATIONS.md`](OPERATIONS.md): day-2 operations, monitoring, the metrics the
  failover triggers come from.
- [`SECRETS.md`](SECRETS.md): the `polaris_replicator_password` secret and the
  file-mounted secret convention.
- [`RUNBOOKS.md`](RUNBOOKS.md): the per-alert response runbooks
  (`PolarisAppDown` / `PolarisHighDBLatency` are the failover triggers).
- `.github/workflows/ci.yml`: the `Streaming-replication primary -> standby`
  round-trip that proves the shipped config produces a working hot standby.
