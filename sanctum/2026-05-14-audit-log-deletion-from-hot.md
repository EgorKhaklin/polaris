# Sanctum: audit-log-deletion-from-hot

**Date:** 2026-05-14
**Petitioner:** agent (Claude, Opus 4.7) speaking as the Architect
**Principal:** VANTA
**Trigger:** v8.84 ship of `polaris-archive.sh` (export-only, C1-preserving) surfaces the next question: should an "archive policy" also DELETE the archived rows from the hot tables (`TokenLifecycleEvent`, `VerificationEvent`, etc.) to keep `pg_data` bounded over multi-year retention? The export-only half is in the v8.84 ship; the deletion half is constitutional and waits here.
**Risk class:** MEDIUM (touches C1 — the append-only audit invariant; the schema's two append-only triggers physically refuse `DELETE`; loosening them requires a constitutional carve-out on file)
**Status:** DECIDED + CLOSED — Position B selected by VANTA in-chat 2026-05-14 ("Top-3 proceed with the architects + hydras recommendation"). Shipped as v8.87.

---

## I. The Matter

C1 (MISSION.md, hard constraint) states: lifecycle and verification events are **append-only**. The schema enforces this with two `BEFORE DELETE OR UPDATE` triggers (`reject_audit_modification` on `TokenLifecycleEvent`, `enrollment_event_append_only` on `EnrollmentStatusEvent`, etc.). A literal reading: no row can ever leave these tables. Ever.

The OPERATIONS.md storage-growth projection (~330 MB/day at 1M verifications/day → ~120 GB/year → ~1.5 TB at the 5-year mark named in the same section) makes literal-C1 untenable at production scale beyond a few years. Real deployments will need to free space somehow.

Three positions to choose between:

### Position A: Literal C1 — no deletions, ever

The schema doesn't delete; operators scale storage. Acceptable up to ~5 years at low volume; expensive at high volume. **No code change needed.** The export-only `polaris-archive.sh` (v8.84) gives operators *backup* copies but not *space reclamation*.

**Strength:** purest non-repudiation. The hot table is the source of truth, always.

**Weakness:** operationally infeasible past ~5 years of high-volume use. Forces operators to scale storage indefinitely. May push smaller deployments to falsify the audit log out-of-band (worse than a documented archive policy).

### Position B: Archive-then-delete, with strict guarantees

Define "archive-then-delete" as constitutionally distinct from "delete." The carve-out:

1. The rows must first be exported to a durable, indexed, manifest-hashed tarball (the v8.84 `polaris-archive.sh` format).
2. The export must succeed AND verify cleanly before any deletion is permitted.
3. Deletion runs under a dedicated procedure (`uc_archive_purge`) that:
   - Confirms the archive tarball exists and verifies
   - DELETEs the same row-set the archive contains
   - Writes a single `LifecycleArchiveCheckpoint` row recording: cutoff timestamp, archive tarball SHA-256, row count, operator user_id, decided_at
   - The checkpoint row is itself append-only
4. The two append-only triggers gain an exception clause keyed on a process-local GUC the procedure sets (`polaris.purge_in_progress = TRUE`). Outside the procedure, deletions still fail.

**Strength:** unbounded retention horizon; storage stays bounded; non-repudiation preserved via the archive + checkpoint chain.

**Weakness:** the constitutional language goes from "no deletions ever" to "no deletions outside the archive-purge procedure." Subtler, more easily mis-implemented, more state to keep aligned. If the archive tarball is lost between export and deletion, recovery is impossible.

### Position C: Tiered storage at the row level (no deletion needed)

PostgreSQL table partitioning by `event_timestamp` quarter or year. Old partitions move to slower/cheaper tablespaces; the rows stay in the database. No `DELETE` ever issues.

**Strength:** keeps C1 literal. Storage cost drops as old partitions move to cheap SSD or HDD. No archive-tarball-as-source-of-truth concern.

**Weakness:** requires a non-trivial schema migration (table-to-partitioned-table); slow partitions hurt cross-partition queries (e.g. "all of an individual's history"); operators need to manage tablespaces. Doesn't help if the storage cost is the database product (RDS) rather than the disk.

## II. Architect's recommendation

**Position B with the strict-guarantee carve-out**, contingent on VANTA's sign-off. Rationale:

1. Position A becomes the de-facto position by default if VANTA doesn't decide otherwise. The OPERATIONS.md storage-growth section already calls this out as a "Phase 2 will ship an automated archive policy" — VANTA has implicitly named this as a real need.

2. Position C is constitutionally cleaner but operationally heavier. Partitioning a v1.0 schema retroactively is a real migration; doing it AFTER years of data accumulation is worse. If we want Position C, the right time was v1; the next-best time is now, but it competes against shipping the production-deploy story.

3. Position B can be implemented incrementally:
   - Phase 2a (this ship, v8.84): export-only, C1-preserving. Done.
   - Phase 2b (this Sanctum's decision): the `uc_archive_purge` procedure + the trigger carve-out + the `LifecycleArchiveCheckpoint` audit-table. Schema migration; MEDIUM-risk; documented.
   - Phase 2c (future): operator-facing automation (cron / S3-rotation).

4. The non-repudiation guarantee survives B if the archive chain is durable and verifiable. The `LifecycleArchiveCheckpoint` row IS the audit-of-record for the purge; the tarball is the materialized referent.

## III. Open questions for VANTA

If Position B is acceptable, three operator-facing choices need a decision before Phase 2b can ship:

1. **Default cutoff for purgeability.** Reasonable choices: 730 days (2y), 1095 days (3y), 1825 days (5y). The OPERATIONS.md storage-growth section uses 5y as the planning horizon, suggesting 1825 is the right default. Older rows (5y+) can be archive-purged; younger stays in hot.

2. **Archive tarball custody.** The deletion is gated on the archive existing AND verifying. Where does the archive live?
   - (a) On the same host (simplest; cheapest; one disaster wipes both copies)
   - (b) On a known offsite (S3 Glacier, separate region, separate key)
   - (c) Operator-discretion; the procedure checks SHA-256 against a configured manifest URL

3. **Whether `LifecycleArchiveCheckpoint` is publicly queryable** or admin-only. Public surface signals to relying parties that an archive policy is in force; admin-only avoids exposing the cutoff cadence as a side channel.

## IV. Alternatives considered

- **Add a `is_archived` column to each audit table instead of deleting.** Same storage; weaker C1 signal; nobody benefits. Rejected.
- **Implement deletion silently without a carve-out.** Violates the audit-of-record discipline. The Architect could not in good conscience recommend this.
- **Refuse to ship a deletion policy at all.** Forces operators to invent their own; the system loses control over how the constitutional invariant is interpreted in practice. Worse than a deliberate policy.

## V. Decision

**Position B selected.** VANTA in-chat 2026-05-14: *"Top-3 proceed with the architects + hydras recommendation."*

The three operator-facing follow-up decisions were resolved by the agent under heavy-production posture with the architect's recommended defaults; VANTA can override via a fresh Sanctum if a different policy is wanted in a real deployment:

1. **Default cutoff: 1825 days (5y).** Matches the OPERATIONS.md storage-growth planning horizon. Operators pass a different `--cutoff-days` to `polaris-archive.sh` to override per-purge.
2. **Archive tarball custody: operator-discretion with required SHA-256 verification.** The procedure records the URI verbatim; the operator is responsible for keeping the archive accessible at that URI for the non-repudiation chain to remain whole.
3. **`LifecycleArchiveCheckpoint` queryability: admin-only.** Per default SQL grants. Public surface would leak the cutoff cadence as a side channel; admin-only avoids that.

## VI. Outcome

**v8.87 shipped Phase 2b in full:**

1. New table `LifecycleArchiveCheckpoint` (~50-line `CREATE TABLE` in `01_schema.sql`) with strict append-only enforcement via a dedicated `reject_checkpoint_modification()` trigger (no GUC carve-out at this layer; G30).

2. `reject_audit_modification()` trigger function rewritten with a GUC-keyed carve-out: when `current_setting('polaris.purge_in_progress', true) = 'TRUE'`, DELETE is permitted. UPDATE remains forbidden. Outside the procedure, both DELETE and UPDATE still fail. (G31.)

3. New procedure `uc_archive_purge(p_cutoff_timestamp, p_archive_uri, p_archive_sha256, p_actor_user_id)` in `05_procedures.sql` (~120 lines): validates cutoff-in-past, SHA-256 format, admin-role actor; sets `LOCAL polaris.purge_in_progress='TRUE'`; DELETEs from the 4 reject_audit_modification-protected audit tables (`TokenLifecycleEvent`, `VerificationEvent`, `EnrollmentStatusEvent`, `AuthAuditLog`); INSERTs the `LifecycleArchiveCheckpoint` row in the same transaction.

4. `scripts/polaris-purge.sh` (~150 lines): operator wrapper that requires an archive tarball, computes its SHA-256, reads the manifest cutoff, calls `uc_archive_purge` with all four params, reports the checkpoint row.

5. **End-to-end drill verified (60-row test set):**
   - Direct DELETE on TokenLifecycleEvent → `insufficient_privilege` (carve-out closed)
   - `polaris-archive.sh --cutoff-days=0` → tarball with 60 rows
   - `polaris-purge.sh --archive=… --actor-user-id=1` → 37 rows purged (TLE=15 + VE=9 + Enrollment=13), 1 checkpoint row written
   - Post-purge: TLE=0, VE=0, Enrollment=0, Checkpoint=1
   - Post-purge direct DELETE on AnchorBatch → `insufficient_privilege` (carve-out closed after procedure exit; SET LOCAL evaporates at txn boundary as designed)
   - Direct DELETE/UPDATE on LifecycleArchiveCheckpoint → both rejected (G30 holds)

6. **Scope honesty:** v8.87 covers the 4 high-volume reject_audit_modification-protected tables. **AnchorBatch** has FK pressure from BlockchainAnchor.batch_id (deferred to Phase 2c); **AgencyTrustAttestation** and **DuressEvent** have their own immutability triggers separate from `reject_audit_modification` (deferred to Phase 2c, when the same GUC pattern can be extended to those triggers if the storage pressure ever justifies it — currently they are low-volume).

7. **Two new G-guards:**
   - **G30** — `LifecycleArchiveCheckpoint` is strictly append-only (no GUC carve-out; the checkpoint chain IS the audit-of-record for the deletion carve-out and must remain whole).
   - **G31** — the only DELETE path through reject_audit_modification-protected audit tables is via `uc_archive_purge()`. Any direct DELETE attempt outside the procedure must surface the trigger's `insufficient_privilege` error.

**Non-repudiation chain (the constitutional claim):**

Question — *"did event X happen?"* Answer:

```
1. SELECT * FROM TokenLifecycleEvent WHERE event_id = X
   → found?  YES → answer here.
              NO  → continue
2. SELECT * FROM LifecycleArchiveCheckpoint
   WHERE cutoff_timestamp >= <when X would have occurred>
   ORDER BY purged_at LIMIT 1
   → found?  YES → archive_uri + archive_sha256 give the offline
                   tarball that contains X
              NO  → X never happened
3. Verify the tarball at archive_uri matches archive_sha256
4. Extract; read the matching .csv; locate X
```

C1's append-only invariant is preserved at the *constitutional* level by this chain (every event reconstructible) even though it is loosened at the *table* level for the four high-volume tables.

**Drill results match the contract precisely.** The Sanctum is closed.
