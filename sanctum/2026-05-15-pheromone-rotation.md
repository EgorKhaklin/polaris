# Sanctum: pheromone-rotation

**Date:** 2026-05-15
**Petitioner:** agent (Claude, Opus 4.7) speaking as the Architect
**Principal:** VANTA
**Trigger:** polaris-self-roadmap-2026-05-14.md item D5 — surfaced
when the v9.04 macro-to-micro scan observed Pheromone table growth
projection: 1002 rows in 30 minutes during the v9.04 drill, cron
soldiers + commanders projecting ~50K rows/day, ~1.5M/month, ~18M/year.
The table is C1 audit-of-record (append-only forever); no archive/purge
equivalent to `polaris-archive.sh` + `polaris-purge.sh` for AuditLog
exists. Authorized for Wave 2 by VANTA in-chat 2026-05-15: *"wave 2
proceed"*.
**Risk class:** HIGH (the IMPLEMENTATION is HIGH; this OPENING is
LOW because it only files positions. Implementation gates on this
Sanctum's decision and ships in Wave 3 as a separate v9.x ship.)
**Status:** DECIDED + CLOSED 2026-05-15 — Position A (mirror v8.84+v8.87
audit-log archive+purge framework) selected per heavy-production
posture (v8.31 §III.6); implementation deferred to Wave 3 separately.

---

## I. The Matter

The Pheromone table, introduced v8.62 as the Mycelium swarm's audit-of-
record substrate, is the load-bearing input to v9.04's PheromoneReader
+ CorrelationEngine + cognitive_watcher's pheromone-context channels.
Every commander run (~33 commanders × every 6h cron = ~132 deposits/day)
plus every soldier run (~8 soldiers × every 30min cron × 60s ≈ 19+
deposits per cron run × 48 runs/day = ~900 deposits/day from soldiers
alone) plus every `--hybrid` invocation seeds 1000+ deposits.

**Observed growth rate (during the v9.04 drill):**
- 1002 rows in 30 minutes (drill-rate)
- Cron-only projection: ~50K rows/day, ~1.5M/month, ~18M/year
- 5-year projection: ~90M rows, multi-GB table

**The constitutional question:** Pheromone is C1 (audit-of-record;
append-only; trigger enforces). Like AuditLog before it (which got
archive+purge framework via the v8.84 export-only pass + v8.87
constitutional carve-out + LifecycleArchiveCheckpoint), Pheromone
needs a parallel framework. The audit-log carve-out was opened as
Sanctum `2026-05-14-audit-log-deletion-from-hot.md` and closed with
Position B (archive-then-delete with carve-out). This Sanctum is the
parallel for Pheromone.

**Why Wave 2 surfaces it as an opening only (not implementation):**
Per the polaris-self-roadmap, item D5 was "Pheromone rotation Sanctum"
(Wave 2) and item Wave-3 #2 is "Pheromone rotation framework". The
opening surfaces the question; the framework ships separately. Same
two-step pattern as v8.84 → v8.87 (audit-log).

## II. The architect's positions

### Position A: Mirror v8.84+v8.87 framework — architect-recommended

**Implementation shape (deferred to Wave 3):**
1. **`scripts/polaris-pheromone-archive.sh`** (mirrors `polaris-archive.sh`)
   — exports Pheromone rows older than configurable cutoff to a
   manifest-hashed tarball; verifies SHA-256; default 30-day cutoff;
   `--verify-latest` re-hashes. Like v8.84, EXPORT-ONLY; never deletes.
2. **`LifecyclePheromoneCheckpoint` table** (mirrors `LifecycleArchiveCheckpoint`
   — v8.87 G30/G31) — records cutoff + archive_uri + archive_sha256 +
   actor_user_id + rows_purged. Strictly append-only; NO GUC carve-out
   at the checkpoint layer (G30 parallel).
3. **`uc_pheromone_archive_purge()` procedure** — validates
   cutoff-in-past + SHA-256 hex + actor-role; sets LOCAL GUC
   `polaris.pheromone_purge_in_progress='TRUE'`; DELETEs from Pheromone
   in same txn; INSERTs checkpoint. The single sanctioned DELETE path.
4. **`reject_pheromone_modification()` trigger** rewritten with
   GUC-keyed DELETE carve-out (`TG_OP='DELETE'` only — UPDATE still
   rejects).
5. **`scripts/polaris-pheromone-purge.sh`** operator wrapper —
   computes SHA-256, reads manifest cutoff, calls procedure.
6. **OPERATIONS.md §"Pheromone archive + purge"** with two-step
   workflow + non-repudiation chain.

**Scope:** ~600 lines (parallel to v8.87 audit-log carve-out which was
~700 lines). Quarterly archive cadence; yearly purge cadence
(architect-recommended).

**G-guards added:** G32 (Pheromone archive append-only), G33
(uc_pheromone_archive_purge is the only DELETE path).

**Strengths:**
- Reuses the v8.84+v8.87 pattern operators already understand
- Constitutional carve-out preserves C1 by making DELETE require a
  documented archive-with-checkpoint cycle
- Bounds Pheromone growth at 30-day rolling window (configurable)
- HYDRA's PheromoneReader 6h/24h windows untouched (live data stays hot)

**Weaknesses:**
- ~600 lines of new code/SQL; another ship surface
- Deletion-from-hot is constitutionally heavy (Pattern #20 8th
  instance; same shape as v8.87)

### Position B: Partition Pheromone by month + drop old partitions

PostgreSQL native partitioning. Each month becomes its own table;
when a month is N+12 months old, drop the partition.

**Strengths:** Postgres-native, less custom code, faster queries on
recent data (partition pruning).

**Weaknesses:** DROP TABLE bypasses the C1 audit-of-record discipline
entirely — there's no checkpoint, no operator-signed manifest, no SHA
chain. Constitutional regression vs Position A.

### Position C: TimescaleDB hypertable + retention policy

Drop in TimescaleDB extension, convert Pheromone to a hypertable, set
retention to 12 months.

**Strengths:** Industry-standard for time-series.

**Weaknesses:** Adds a runtime dependency (TimescaleDB extension);
operator burden; Polaris is a reference implementation that should
work on stock Postgres.

### Position D: Defer indefinitely

Argue 18M rows/year is fine; PostgreSQL handles it.

**Strengths:** Zero work.

**Weaknesses:** True at 1 year; questionable at 5 years; certain
problem at 10 years. The v9.04 macro-to-micro scan flagged the
projection specifically because deferring forever was the prior
posture (item D5 surfaced exactly this gap).

## III. Architect's recommendation

**Position A (mirror v8.84+v8.87 framework).** Rationale:

1. **Pattern parallel is exact.** AuditLog and Pheromone are both
   C1 audit-of-record append-only tables. v8.84 + v8.87 closed
   AuditLog's growth question with archive+purge. Pheromone gets the
   same shape. Operators already know the workflow; G-guards
   parallel; tooling parallel.

2. **Constitutional preservation is mechanical.** Position A
   preserves C1 via the same GUC-keyed DELETE carve-out that v8.87
   shipped for AuditLog. The carve-out is constitutional discipline
   in code, not narrative.

3. **Reference-implementation discipline.** Position B + C compromise
   on Polaris's "stock Postgres + hand-written SQL" reference posture
   (no extensions; no opaque framework dependencies).

4. **Position D ignores the macro-to-micro scan finding.** The whole
   point of producing the polaris-self-roadmap was to surface gaps
   the implicit deferrals had let accumulate.

The architect's caution: Wave 3 implementation is HIGH-risk because
it touches C1. The Sanctum itself opens + closes here (DECIDED-on-
arrival per heavy-production); the framework ship will need its own
verification surface (drill: archive 1000 rows → verify SHA → purge →
checkpoint → adversarial DELETE rejection → tamper-test). Same shape
as v8.87 drill.

## IV. Open questions for VANTA

(All resolved per architect-recommended defaults; no additional
operator decision required for the OPENING. Wave 3 implementation
ship may surface new questions.)

1. **Default cutoff?** Architect-recommended: 30 days. Live data
   for HYDRA's 6h/24h windows + a comfortable margin. Operator-
   tunable via `--cutoff` flag.

2. **Archive cadence?** Architect-recommended: quarterly archive
   (3 months); yearly purge. OPERATIONS.md cron rows added at Wave
   3 ship.

3. **Per-tier retention?** Architect-recommended: NO. Same cutoff
   applies to commander + soldier deposits. Soldier deposits are
   the bulk-volume tier; treating them differently would complicate
   the framework. The disposability invariant (v9.03 Sanctum) is
   for soldier *operation*, not soldier *audit-of-record*.

4. **Strict invariant for the Wave 3 ship?** Architect-recommended:
   archive-then-purge produces byte-identical output across two runs
   given same DB state + cutoff (the v8.87 acceptance criterion
   parallel).

## V. Decision

**Position A (mirror v8.84+v8.87 framework).** VANTA in-chat
2026-05-15: *"wave 2 proceed"* — authorizing the OPENING of this
Sanctum + the Wave 2 composite. DECIDED-on-arrival per heavy-
production posture (Pattern #20 ninth instance this cycle).

The four §IV resolutions all per architect-recommended defaults.
Wave 3 implementation ships separately when VANTA authorizes —
that ship carries the actual G32/G33 + tooling + drill.

## VI. Outcome

OPENED + DECIDED + CLOSED 2026-05-15 same surface as v9.06 Wave 2
composite. Implementation deferred to Wave 3 (separate ship surface;
HIGH-risk; requires drill verification).

**Records:**
- This file (sanctum/2026-05-15-pheromone-rotation.md)
- meta/sanctum-index.md entry (added with v9.06 ship)
- ROADMAP.md Wave 3 #2 row updated to "DECIDED 2026-05-15; awaiting
  implementation authorization"
- polaris-self-roadmap-2026-05-14.md item D5 marked decided
- v9.06 CHANGELOG entry references this Sanctum

**Pattern #20 Constitutional Discipline ninth instance** in the
v8.84/v8.87/v8.90/v8.91/v8.94/v8.95/v8.96/v8.97/v9.04/v9.06 series
of constitutional-question Sanctums under heavy-production. The
opening shape is identical to v8.84 (audit-log-deletion-from-hot)
opening; the closing shape will be identical to v8.87 (Position B
deletion-from-hot shipped as Wave 3 / Pheromone-rotation-framework).

## VII. Cross-references

- v8.84 sanctum — audit-log-deletion-from-hot (the parallel Sanctum)
- v8.87 implementation — uc_archive_purge + LifecycleArchiveCheckpoint
- v8.62 — Pheromone primitive opening
- v9.04 — PheromoneReader + cognitive_watcher pheromone-context
  channels (the read-side; this Sanctum addresses the rotation-side)
- meta/polaris-self-roadmap-2026-05-14.md — item D5 (the surfacing)
- DEVNOTES/audit-of-record.md — the principle this Sanctum is
  protecting
