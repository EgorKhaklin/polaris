# FAILOVER.md: the HA profile, automated failover, and the split-brain analysis

**Reader:** the operator who runs Polaris with a database that must survive
the loss of its host, or who is deciding whether to. **Job:** what the HA
profile does on its own, what it measured doing it, what it asks of you, and
why a partitioned primary cannot keep accepting writes. This is the
high-availability counterpart to [`DR.md`](DR.md), which restores from a
backup; the HA profile keeps a second copy current and moves the primary
role to it by itself, so a lost host costs the lease, not the backup
interval.

Until v9.243 this page was a manual runbook: the primary was made
replication-ready, the standby and the promotion were the operator's, and
"Patroni or repmgr stay operator choices". Since v9.243 the choice is made
and shipped as [`polaris_web/docker-compose.ha.yml`](../../polaris_web/docker-compose.ha.yml),
and the runbook's promotion steps are what the supervisor does. What stays
yours is placement: the hosts.

---

## Table of contents

1. [What ships vs. what the operator supplies](#1-what-ships-vs-what-the-operator-supplies)
2. [The topology](#2-the-topology)
3. [What it measured](#3-what-it-measured)
4. [The split-brain analysis](#4-the-split-brain-analysis)
5. [Operating it](#5-operating-it)
6. [RPO and RTO](#6-rpo-and-rto)
7. [Cross-references](#7-cross-references)

---

## 1. What ships vs. what the operator supplies

**Ships (the HA profile, `-f docker-compose.ha.yml` on top of the production
stack):**

- Two database members, `postgres` and `postgres2`, running the same
  database image under Patroni (`patroni-entrypoint.sh` renders Patroni's
  configuration from the compose environment and the file-mounted secrets).
  Patroni runs `initdb` on the first member, loads the schema through the
  same `docker-init.sh` the single-node stack runs, clones the second member
  with `pg_basebackup`, and keeps the replica streaming with a replication
  slot.
- A three-member etcd (`etcd1`, `etcd2`, `etcd3`, self-built from Alpine's
  package, non-root) on an internal network only the database members join.
  It holds the leader lease: `ttl` 20 s, renewed every `loop_wait` 5 s, with
  `retry_timeout` 5 s.
- HAProxy (`pg-router`) forwarding 5432 to whichever member answers
  Patroni's `/primary` and 5433 to a member answering `/replica`, checking
  every half second, cutting sessions to a member the moment it is marked
  down. pgbouncer dials `pg-router`; the application is unchanged.
- The failover drill, [`scripts/polaris-failover-drill.sh`](../../scripts/polaris-failover-drill.sh),
  run on every push (the `ha-failover` CI job) against the ceilings in §3,
  asserting after every scenario that each insert acknowledged since the
  drill began is present on the leader: no acknowledged write is lost.
- `check_ha_automation`, which fails the build if the lease semantics, the
  routing, the drill or this analysis change out from under each other.

**Operator-supplied:**

- **Placement.** On one host the profile proves the mechanism and survives a
  process, a container or a lease loss; it does not survive the host. The
  two members belong on two hosts and the three etcd members on three (two
  of them can share the database hosts). The compose file is the same;
  `POLARIS_PATRONI_HOST` names each member's reachable address and
  `POLARIS_PATRONI_ETCD_HOSTS` the lease store's.
- **Transport security between hosts.** On the single-host profile etcd
  speaks plain HTTP on an internal bridge and Patroni's REST API is plain
  HTTP on the stack network. Across hosts both need TLS (Patroni's `etcd3`
  and `restapi` sections take certificates; the entrypoint's rendering is
  the place to add them) or a private network you trust as much as the
  bridge.
- **Durability versus availability.** Replication is asynchronous:
  a failover can lose the transactions the replica had not received.
  `synchronous_mode` (`patronictl edit-config`) makes a commit wait for the
  replica; the trade is commit latency and a liveness coupling. Polaris does
  not choose for you.

---

## 2. The topology

```
        app / app-green ──► pgbouncer ──► pg-router (HAProxy)
                                             │  /primary → 5432     /replica → 5433
                                   ┌─────────┴─────────┐
                              postgres              postgres2          (Patroni members)
                                   └────── lease ──────┘
                                   etcd1  etcd2  etcd3                 (internal network)
```

Patroni's contract, which everything above relies on:

- **The lease is the primary role.** A member is primary only while it
  holds the leader key in etcd, which expires after `ttl` seconds unless the
  holder renews it. A member that cannot renew (it cannot reach a quorum of
  etcd within `retry_timeout`) demotes itself: it restarts Postgres in
  recovery and stops answering `/primary`. `failsafe_mode` is off (it would
  let a leader keep the role while the lease store is unreachable if it can
  still see the other members; it trades the guarantee below for
  availability, and the analysis in §4 depends on not having it).
- **Promotion is the lease changing hands.** When the key expires the
  streaming replica acquires it and promotes. Nothing else promotes: no
  operator step, no timer on the replica, no vote among the members.
- **A returning member follows.** A former leader that starts again finds
  the lease held elsewhere, rewinds its data directory to the new timeline
  (`pg_rewind`, enabled by `wal_log_hints`) and streams. If rewind cannot
  apply it is re-cloned.
- **Routing follows the lease, not the address.** HAProxy asks each member
  whether it holds the role; the member's own answer, not a cached
  address, decides where the next connection goes.

---

## 3. What it measured

The drill runs a writer through the real client path (pgbouncer, HAProxy,
the leader) four times a second and logs every insert, so a scenario's
write outage is what an application would have seen: a failed insert, or an
insert that stalled in the pooler's queue. Reads run against the edge as in
the other drills. Local reference run at v9.243, the ceilings the drill
asserts on the right:

| Induced failure | What the supervisor did | Write outage | Rejoin | Ceiling |
|---|---|---|---|---|
| The leader node is lost (killed, kept down) | the replica acquired the lease and promoted 19 s later | 20.0 s, no insert failed: the pooler queued them | the old node was streaming again 4 s after it was started | 60 s |
| The leader is cut off from the lease store; its clients and the other member can still reach it | it demoted itself after 9 s; the other member, current, took the lease after 10 s | 12.3 s, no insert failed | streaming as soon as it reconnected | 45 s to demote, 60 s |
| A planned switchover (`patronictl switchover`) | the candidate was leader within a second | 3.4 s, no insert failed | the old leader followed after 2 s | 30 s |
| One etcd member crashes | nothing: the leader kept the lease on the remaining quorum | 0.3 s longest stall, no insert failed | the member restarted on its own | 5 s, no failure |

Two things the numbers say. The write outage of a lost leader is the lease:
about `ttl` plus one `loop_wait` before the replica can take the key. A
shorter lease shortens it, and makes a slow lease store more likely to cost
a demotion; 20 s is the shipped balance and `POLARIS_PATRONI_TTL` is the
knob. And a Postgres process that crashes on the leader and restarts within
its lease is not a failover: Patroni restarts it in place and keeps the
lease, which is what a supervisor should do; the chaos drill measures that
case on the single-node stack.

The drill starts a scenario only when the replica is streaming with zero
lag, because the partition scenario has a second outcome (§4) when it is not.
The first runs of the drill found three things the numbers now include. A
pooler connect that started in the two seconds before HAProxy marked the
old leader down hung for PgBouncer's default 15 s `server_connect_timeout`
with every client queued behind it; the pooler now abandons a connect after
3 s (`PGBOUNCER_SERVER_CONNECT_TIMEOUT`) and HAProxy redispatches a failed
backend connect to another member. And the write stream stalls rather than
fails while the pooler queues, so the drill reports the longest stall as
well as the failed inserts, and asserts on the larger of the two; and it
stamps each insert with its completion time, since an insert that waited
twenty seconds in the queue is a twenty-second stall, not a fast one.

---

## 4. The split-brain analysis

Split-brain is two members accepting writes at once: two histories that
cannot be merged afterwards, in a system whose audit of record is
append-only (C1). The question is whether any sequence of failures lets it
happen here.

**The invariant.** Writes reach a member only through `pg-router`, which
forwards to a member answering `/primary`, which answers 200 only while the
member holds the lease. So a write can land on a member only while that
member holds a lease that has not expired, and etcd grants one holder at a
time.

**The partitions, one by one.**

- *The leader loses etcd but not its clients.* It cannot renew; within
  `retry_timeout` it demotes (§3 measured 6 s) and `/primary` turns 503, so
  HAProxy stops sending it connections and cuts the open ones. Meanwhile the
  key cannot expire earlier than `ttl` after its last renewal, so the
  replica cannot acquire it before the old leader has already had its
  `retry_timeout` to stand down. The windows are ordered by construction
  (`ttl` > `loop_wait` + 2 × `retry_timeout`; the entrypoint refuses a
  configuration that breaks the ordering). This is the case the drill
  exercises: the cut-off member demoted 9 s in, the lease moved at 10 s, and
  the cut-off member never took a write after its demotion.
- *The same partition, with the other member a few records behind.* The
  first CI run found this outcome. A fast shutdown writes a final WAL record
  or two, and if the replica's walreceiver was not attached at that instant
  it never gets them. Patroni will not promote a member while a reachable
  member reports a position ahead of it, and the member that is ahead cannot
  take the lease without the store, so nobody holds it: the cluster is
  read-only everywhere until the partition heals, after which the member
  that is ahead takes the lease back (its lease and registration have
  expired, it is still ahead, and it can now reach the store). Integrity is
  kept at the price of availability, and the drill accepts this outcome,
  asserting that no insert was acknowledged while nobody held the lease.
  The operator's override, if the partition will not heal, is
  `patronictl failover --candidate <survivor>`, which promotes the member
  that is behind and gives up the records it never received.
- *The leader loses its clients but not etcd.* It keeps the lease and the
  role; no write reaches any member (HAProxy sees one primary, unreachable)
  until the partition heals or you intervene with a switchover. This is an
  outage, not a split-brain: availability is lost, integrity is not.
- *The two members lose each other but both see etcd.* Replication breaks;
  the leader keeps the lease; the replica cannot acquire a held key. One
  primary. The replica falls behind and `maximum_lag_on_failover` (1 MiB)
  keeps a badly lagging replica from being promoted later without the
  operator's say.
- *etcd loses quorum.* No key can be renewed or acquired. The leader demotes
  when it cannot renew; nobody can promote. The database becomes read-only
  everywhere until quorum returns: again an outage, not a split-brain. This
  is why there are three etcd members and why they belong on three hosts.
- *A former leader comes back with a divergent history.* It finds the lease
  held, rewinds to the holder's timeline, and streams. Its unreplicated
  transactions are gone (the durability choice in §1); they are not merged
  and they do not resurface.
- *HAProxy itself.* It holds no state that can be wrong for longer than one
  check interval: a stale "up" costs at most `inter` × `fall` (one second)
  of connections to a member that has just demoted, and those connections
  fail on the member (it is in recovery) rather than write.

**What would break it.** Turning `failsafe_mode` on (a leader may keep the
role without the lease); pointing pgbouncer at a member by name instead of
at `pg-router` (a failover would move nothing); a lease shorter than the
retry window; running a single etcd member across hosts (no quorum to lose,
so no protection when it is gone). `check_ha_automation` pins the first two
and the entrypoint the third; the fourth is placement, which is yours.

**What the analysis does not cover.** The single-host profile shares the
host: a host failure takes both members and all three etcd members, and the
answer to that is [`DR.md`](DR.md). Clock skew between hosts is bounded by
etcd's lease implementation (leases are server-side), not by the members'
clocks. And the application's own idempotency under a retried write is a
property of the application, not of the topology; Polaris's per-request
transactions and append-only tables make a retry visible rather than
silent.

---

## 5. Operating it

```bash
P="docker compose -f polaris_web/docker-compose.prod.yml -f polaris_web/docker-compose.ha.yml exec postgres patronictl -c /var/lib/postgresql/patroni.yml"
$P list                                                  # roles, timeline, lag
$P switchover --primary postgres --candidate postgres2   # planned; a few seconds of write outage (§3)
$P history                                               # every timeline change and its cause
$P show-config                                           # ttl, loop_wait, retry_timeout, postgresql parameters
$P reinit postgres2                                      # force a fresh clone of a member
```

- **Host maintenance:** switch the lease away, work on the idle member,
  switch back. A member you stop stays a member; when it starts it rejoins.
- **After an unplanned failover:** nothing to do for the topology; the
  returning member rejoins by itself. Take a backup against the new leader
  so the [`DR.md`](DR.md) path is current for the new timeline; the WAL
  archive follows the leader (only the leader archives).
- **Alerts:** `PolarisAppDown` and `PolarisHighDBLatency` still fire for what
  clients see. Patroni's REST API also serves `/metrics` on each member;
  scraping it is the next step in [`OPERATIONS.md`](OPERATIONS.md)'s
  observability section, not yet wired.
- **Never edit `postgresql.conf` on a member.** Patroni owns it; use
  `edit-config`.

---

## 6. RPO and RTO

- **RTO** for a lost host is the lease plus routing: 20 s measured (§3), against [`DR.md`](DR.md)'s 4 h target for the case where no replica
  survives.
- **RPO** is whatever the replica had not received: usually milliseconds on
  a healthy link, zero with `synchronous_mode` at the cost above. The 300 s
  target in `DR.md` is met by streaming more tightly than by the 60 s WAL
  archive interval, for the failure class where the replica survives.
- Replication does **not** replace backups. A logical error (a bad
  migration, an erroneous bulk update) replicates to the replica within
  milliseconds; the point-in-time restore in `DR.md` is the recovery for
  that, and the append-only audit of record is the integrity anchor.

---

## 7. Cross-references

- [`DEPLOYMENT.md`](DEPLOYMENT.md#automated-database-failover-ha-profile):
  enabling the profile.
- [`OPERATIONS.md`](OPERATIONS.md#the-ha-profile-living-with-patroni):
  day-2 with `patronictl`.
- [`DR.md`](DR.md): backup and restore, the SEV ladder, the case the HA
  profile does not cover.
- [`SECRETS.md`](SECRETS.md): `polaris_replicator_password` and the
  file-mounted secret convention Patroni's rendering reads.
- [`RUNBOOKS.md`](RUNBOOKS.md): the per-alert responses.
- `.github/workflows/ci.yml`, job `ha-failover`: the drill on every push.
