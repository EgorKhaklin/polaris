# Sanctum: schema-migration-framework

**Date:** 2026-05-14
**Petitioner:** agent (Claude, Opus 4.7) speaking as the Architect
**Principal:** VANTA
**Trigger:** Architect+HYDRA brief (v8.93) named schema migration framework as one of the three remaining Phase 2 Sanctum-class items from the deployability checklist. VANTA: *"okay lets proceed."* Heavy-production posture in force; Pattern #20 Constitutional Discipline says architectural choices with long-term consequences get a Sanctum even when they're not strictly C1-C10.
**Risk class:** MEDIUM (touches the bootstrap path of every future schema change — Polaris currently uses destructive `DROP TABLE … CASCADE` reload; whatever ships here is the path-of-least-resistance for the next ten years of schema evolution).
**Status:** DECIDED + CLOSED 2026-05-14 — Position C shipped as v8.95

---

## I. The Matter

Polaris's current schema-bootstrap path is `polaris_sql/00_load_all.sql`:

```sql
DROP TABLE IF EXISTS … CASCADE;
\i 01_schema.sql
\i 02_indexes.sql
…
\i 13_postgis.sql
```

This is **destructive** by design — every reload starts from a clean slate. It worked perfectly for v1 through v8.x because:

1. The dev database (`polaris_test`) is recreated freely
2. Sample data + seed accounts are loaded fresh each time
3. The schema evolves via edits to `01_schema.sql` directly (additive in practice, but the bootstrap path doesn't know that)

**It will not work for v1.0 production cutover.** Real deployments accumulate:
- 5+ years of `TokenLifecycleEvent` history (archived under Phase 2a, but archive ≠ migration)
- Operator accounts with rotated credentials
- Production-specific configuration (anchor batches, federation attestations, ZK epochs)
- The `LifecycleArchiveCheckpoint` chain (v8.87 constitutional carve-out — DELETING these chains breaks the non-repudiation guarantee)

Any v1.0+ production deployment that wants to ingest the next schema change needs a **forward-only migration** with rollback support, not a `DROP CASCADE`. The architect's brief named four positions; this Sanctum carries them.

## II. The architect's positions

### Position A: Alembic (SQLAlchemy ecosystem)

The Python-ecosystem standard. SQLAlchemy-aware, autogenerate-from-model, ORM-friendly. Used by Flask-SQLAlchemy + Django + many production Python applications.

**Strength:** widely-known; documented exhaustively; many operators have prior experience; integrates with the Python testing story Polaris already uses.

**Weakness:** **Polaris is not a SQLAlchemy project.** The schema is hand-written SQL across 13 numbered files; the app uses psycopg2 + raw SQL strings; there's no ORM model layer. Alembic's autogenerate-from-model feature is the part that makes it loved; without it Alembic becomes "Python files that wrap SQL execution" which is more overhead than value. Forces operators to learn an Alembic DSL on top of the SQL they already maintain.

### Position B: sqitch (pure SQL, dialect-agnostic)

The "deploy / verify / revert" Perl tool that tracks migrations as plain SQL files. Each change has three files: `deploy/<name>.sql` (forward), `verify/<name>.sql` (idempotency check), `revert/<name>.sql` (rollback). Tracks state in a registry schema.

**Strength:** **plain SQL throughout** — fits Polaris's hand-written-SQL ethos exactly. Dialect-agnostic; same machinery works on Postgres + MySQL + SQLite. Verify scripts are a built-in correctness layer (run after every deploy to confirm the change took).

**Weakness:** introduces a Perl runtime dependency (homebrew + apt have packages, but not all managed-Postgres providers offer it pre-installed; some operators will have to install it themselves). The three-file-per-change discipline is heavy for small changes (an `ALTER TABLE ADD COLUMN` becomes three files).

### Position C: Custom polaris-native (architect-recommended)

Match the existing project ethos: hand-written SQL, no new runtime deps, audit-of-record discipline.

**Specification:**

- New `polaris_sql/migrations/` directory; each migration is two files:
  - `YYYY-MM-DD-NNN-slug.up.sql` — forward (REQUIRED)
  - `YYYY-MM-DD-NNN-slug.down.sql` — rollback (REQUIRED; may be a no-op for irreversible changes, but the file must exist as audit-of-record)
- New `polaris_sql/00_migrations_table.sql` creates `schema_version` (append-only via trigger): `migration_id`, `applied_at`, `actor_user_id`, `up_sha256`, `down_sha256`
- New `scripts/polaris-migrate.sh` operator script:
  - `--status` — shows current state (applied migrations + pending count)
  - `--up` (default) — applies pending migrations in lexicographic order in a single transaction; computes SHA-256 of each `*.up.sql` and records it
  - `--down N` — reverts the most recent N migrations using the corresponding `*.down.sql`; refuses to revert if SHA-256 doesn't match the recorded value (catches operator-edited migration files post-deploy)
  - `--dry-run` — lists pending migrations + the SQL they would execute
  - `--target=docker-stack` for the running stack
- `00_load_all.sql` continues to work for fresh installs; on existing databases, `polaris-migrate.sh --up` is the only legitimate path
- `OPERATIONS.md` gains §"Schema migrations" with the workflow

**Strength:** zero new runtime deps (POSIX shell + psql + python3 for SHA-256). Audit-of-record at every migration via `schema_version` row + SHA-256-of-file (so the operator can prove which exact bytes ran). Forward-only by default (reverts require explicit `--down N`). Matches Polaris's existing operator-script style (`polaris-backup.sh`, `polaris-restore.sh`, `polaris-archive.sh`, `polaris-purge.sh`, `polaris-deploy.sh`, `polaris-rotate-logs.sh`, `polaris-create-operator.sh`). Each migration is plain reviewable SQL.

**Weakness:** Polaris-specific (operators with prior Alembic/sqitch experience need to learn this one). No autogenerate; the operator writes the up/down SQL by hand for every change. (Defensible: Polaris's schema changes are infrequent and significant; hand-writing the SQL is the right level of friction. Goodhart's-Law-style mitigation against migration sprawl.)

**Migration scope at v1.0:** the migrations directory starts empty. The existing `01_schema.sql` + `02_indexes.sql` + … + `13_postgis.sql` are the "v0 baseline." Future schema changes (e.g., adding the `LifecycleArchiveCheckpoint` table that v8.87 introduced — currently inlined into `01_schema.sql` — could be backfilled as `2026-05-14-001-lifecycle-archive-checkpoint.up.sql` representing what would have happened if the migration framework had existed). The architect's recommendation: don't backfill historical changes. Start fresh at v1.0.

### Position D: defer indefinitely (status quo)

Accept that schema changes require destructive reload + manual data migration. Don't ship a migration framework.

**Strength:** zero work right now; preserves current behavior.

**Weakness:** **blocks v1.0 production cutover.** Any operator running a real Polaris instance who wants to ingest the next schema change will have to: (1) `polaris-backup.sh`, (2) `dropdb && createdb`, (3) `00_load_all.sql`, (4) `pg_restore` the data. That's a destructive + lossy + non-atomic operation on a production database. **Not acceptable for v1.0.**

## III. Architect's recommendation

**Position C (custom polaris-native).** Rationale:

1. Polaris's hand-written-SQL discipline is load-bearing. Position A (Alembic) replaces hand-written SQL with Python files that wrap SQL; Position B (sqitch) keeps SQL but adds Perl + a three-file-per-change discipline. Position C preserves the hand-written-SQL discipline AND adds the minimum tooling for forward-only migrations with rollback.

2. The operator-script style is already canonical: `polaris-backup.sh` + `polaris-restore.sh` + `polaris-archive.sh` + `polaris-purge.sh` + `polaris-deploy.sh` + `polaris-rotate-logs.sh` + `polaris-create-operator.sh` form a coherent operator surface. `polaris-migrate.sh` fits cleanly. Position A or B introduces a non-`polaris-*.sh` interface that operators have to learn separately.

3. **SHA-256-of-file recording in `schema_version`** is the audit-of-record discipline (v8.20) applied to migrations. Operator-edited-post-deploy migration files are caught at revert time. Position A records migration name only; Position B records via the registry schema; Position C records via the same hash-chain pattern already used for backup manifests + archive verification.

4. Polaris's schema changes are infrequent and significant. The lack of autogenerate (Position A's main feature) is not a real loss — every Polaris schema change to date has been a deliberate architectural decision worth manual SQL.

## IV. Open questions for VANTA

1. **Backfill the existing schema as v0 baseline migrations?** Architect-recommended: NO. Start fresh at v1.0; `00_load_all.sql` is the canonical baseline for fresh installs; `polaris-migrate.sh` only manages changes from that baseline forward.

2. **Forward-only or bidirectional?** Architect-recommended: BIDIRECTIONAL (`*.up.sql` + `*.down.sql` both required). Down-migrations may be no-ops for irreversible changes (e.g., `DROP COLUMN` with data; the down file documents that the column data is gone forever and stays as audit-of-record).

3. **Schema-version table append-only?** Architect-recommended: YES. Same discipline as the other 12 audit-of-record instances. Adding a `reverted_at` column for revert tracking; never DELETE from `schema_version`. (Revert appends a new row with the inverse migration; the original applied-row stays.)

4. **Migration acceptance criterion?** Architect-recommended: every migration applied to a clean `00_load_all.sql` baseline produces a schema state byte-identical to what `00_load_all.sql` alone would produce if updated to include the migration's effects. (Catches migrations that drift from the canonical schema definition.)

## V. Decision

**Position C (custom polaris-native).** VANTA in-chat 2026-05-14: `"C"`.

Position C aligns with Polaris's hand-written-SQL ethos, adds zero
runtime dependencies, and applies the audit-of-record discipline
(v8.20) at the migration layer via SHA-256-of-file recording in
`schema_version`. Estimate was "one ship"; outcome confirms it
(see §VI).

The four §IV open questions resolved per architect recommendation:
NO backfill, YES bidirectional, YES append-only, YES byte-identical
acceptance criterion.

## VI. Outcome

Shipped as v8.95 on 2026-05-14 (same day as decision). Single ship,
no follow-ups required.

**Artifacts:**

- `polaris_sql/00_migrations_table.sql` — creates the `schema_version`
  table (the 13th audit-of-record instance). BIGSERIAL PK,
  `event_type IN ('applied', 'reverted')`, append-only via
  `reject_schema_version_modification()` trigger (no GUC carve-out;
  the migration audit trail must be complete). Loaded FIRST in
  `00_load_all.sql` (before `01_schema.sql`).
- `scripts/polaris-migrate.sh` — operator runner (~340 lines bash).
  Modes: `--status` (default) / `--up [N]` / `--down N` / `--dry-run`.
  Targets: local dev + `--target=docker-stack` for the running stack.
  SHA-256 tamper-detection on revert (exit 6). `--actor-user-id N`
  records the operator in the audit row.
- `polaris_sql/migrations/` — directory + README documenting authoring
  workflow, naming convention, single-transaction discipline, and
  the bidirectional/append-only invariants from this Sanctum.
- `polaris_sql/migrations/2026-05-14-001-idx-checkpoint-recent.{up,down}.sql`
  — first example migration. Adds an index on
  `LifecycleArchiveCheckpoint.purged_at DESC` (small, real, additive,
  demonstrably reversible). End-to-end drill (status → up → status →
  down → status → tamper-test → re-apply) ran clean against the dev
  DB during ship verification.
- `docs/operator/OPERATIONS.md` § "Schema migrations (v8.95)" —
  production operator workflow with all four modes, exit-code table,
  and backup-before-migration guidance.
- Structural invariants — `TestSchemaMigrationFrameworkShipped` class
  in `polaris_web/test_structural_invariants.py` pins:
    1. `00_migrations_table.sql` exists
    2. `00_load_all.sql` loads it BEFORE `01_schema.sql`
    3. `scripts/polaris-migrate.sh` exists + executable + has all four
       modes
    4. SHA-256 tamper-detection exit code 6 path is present in the
       runner
    5. `polaris_sql/migrations/README.md` exists and names the four
       Sanctum §IV resolutions
    6. The first example migration ships paired (.up + .down) and
       matches the naming pattern
    7. This Sanctum file is DECIDED + CLOSED (Status line)

**The four §IV open questions, finalized:**

1. NO backfill — `00_load_all.sql` is the canonical baseline for
   fresh installs. The migrations directory starts with one example
   (the index above), not a backfill of v8.87's `LifecycleArchiveCheckpoint`.
2. YES bidirectional — every migration ships with `.up.sql` AND
   `.down.sql`. The runner refuses to load an `.up.sql` without a
   matching `.down.sql` (exit code 4).
3. YES append-only — `schema_version` rejects UPDATE and DELETE
   via trigger. Reverts append a new `event_type='reverted'` row;
   the original `applied` row stays untouched.
4. YES byte-identical acceptance — documented in OPERATIONS.md and
   in `polaris_sql/migrations/README.md` as the standard for any
   future migration.

**Pattern #20 Constitutional Discipline — fourth Sanctum-DECIDED-ship
cycle this week:**
- v8.84 audit-log-deletion-from-hot → v8.87 LifecycleArchiveCheckpoint
- v8.90 treasury-rebalance → v8.91 Position B shipped
- v8.94 schema-migration-framework → **v8.95 Position C shipped**
The cycle (Architect surfaces → Sanctum opens → VANTA decides →
agent ships the complete thing, with tests + docs + invariants) is
the dominant macro-pattern of the deployability program. The
v8.95 ship completes the framework that makes future schema changes
themselves auditable — every subsequent change to the schema is now
itself an audit-of-record entry in `schema_version`.

**Deployability checklist impact:** removes the "Phase 2 ⬜ Schema
migration framework" item; remaining Phase 2 deferred items are
now the two non-deployability-blocking Sanctum-class items
identified in the v8.93 macro scan.

## VII. Cross-references

- `polaris_sql/00_load_all.sql` — the current destructive bootstrap path
- `polaris_sql/01_schema.sql` — the hand-written schema (1189 lines)
- `polaris_sql/06_triggers.sql` — append-only triggers + the v8.87 constitutional carve-out
- `scripts/polaris-backup.sh` / `polaris-restore.sh` / `polaris-archive.sh` / `polaris-purge.sh` — existing operator-script style this ship would extend
- `meta/arc-b-production.md` — Arc B strategic record naming "Phase 2 schema migration framework" as deferred
- `ROADMAP.md` § "What needs done before it can become a deployable system" — Phase 2 ⬜ item
- v8.93 CHANGELOG — naming this as one of the three remaining Sanctum-class items
- v8.87 CHANGELOG — `LifecycleArchiveCheckpoint` (which would become migration `2026-05-14-001` IF backfill is selected)
