# Retention

**Reader:** an engineer or an assessor. **Job:** How long the record is kept,
who decided that, and why the purge cannot be talked out of it.

## What was wrong

Polaris had an archive-then-purge chain from v8.87: `polaris-archive.sh` writes
a verified tarball, `polaris-purge.sh` checks its SHA-256 against a manifest,
and `uc_archive_purge` deletes the covered rows and appends a checkpoint. Every
part of that was audited except the number that matters. The cutoff was
whatever the operator typed. The database accepted a purge at "older than one
hour" as readily as one at five years, and nothing anywhere recorded who had
decided the retention window or on what grounds.

That is the shape of a coercion vector. An operator under pressure, or an
administration with a preference, could shorten the window to the point where
the record no longer exists, and the shortening would leave no trace beyond a
checkpoint row saying rows were purged. The vocation refuses unbounded
retention; it equally refuses retention short enough to erase the record.

## The mechanism

Three parts, all in the database.

**The decision is data.** `RetentionPolicy` holds one effective row per
(`table_class`, `jurisdiction`), with the number of days, a justification of at
least twenty characters, the operator who set it, and when it took effect. A
NULL jurisdiction is the deployment default. A partial unique index on
`(table_class, COALESCE(jurisdiction, ''))` where `superseded_at IS NULL` means
two effective policies can never disagree about one class.

**The floor is a constraint.** `CHECK (retention_days >= 365)`. No policy row
can express a retention shorter than a year, so no configuration path reaches
one. Lowering the floor means editing `01_schema.sql`, writing a migration, and
answering for it in review. `check_retention_engine` fails the build if the
floor is lowered or removed.

**The purge obeys it.** `uc_archive_purge` resolves the effective retention for
every class it would delete from and raises if the requested cutoff is inside
any of those windows. It refuses rather than narrowing: a purge that silently
deleted less than the operator asked for would be a worse failure than one that
stops and explains itself.

Resolution is `retention_days_for(class, jurisdiction)`: the jurisdiction-scoped
policy, then the deployment default, then 365. There is always an answer, and it
is never below the floor, so a deployment that has configured nothing is still
bounded.

## Why the decision is append-only

A retention decision is an audit of record in the sense
[audit-of-record.md](audit-of-record.md) describes: the row and its history are
the same object. `trg_retention_policy_immutable` refuses DELETE outright,
permits only `superseded_at` to change, and refuses to un-set it or move it
earlier. Changing a retention decision appends a new row and marks the old one
superseded, so the sequence of decisions, and their justifications, survives
the change. `polaris_app` holds SELECT and INSERT and is revoked UPDATE and
DELETE, the same privilege boundary the other append-only tables have.

The consequence worth stating: an operator can lengthen retention freely and can
shorten it only down to the floor, and either way the previous decision stays
readable. Shortening is not silent.

## Templates

`uc_apply_retention_template(template, jurisdiction, actor)` adopts one of two
profiles for a jurisdiction, superseding whatever was effective and appending
the replacement in one transaction. `STANDARD-5Y` is 1825 days for every class
and is what a fresh database ships with. `MINIMIZED` is 1825 days for the two
civic-record classes (token lifecycle, enrollment) and 730 for the two
operational ones (verification, auth audit), for a deployment that wants to hold
less operational history without touching the civic record.

Both are engineering defaults. Neither is a legal determination, and the
procedure is admin-gated: it raises `insufficient_privilege` for any actor whose
`AppUser.role` is not `admin`.

## What this does not do

It does not archive. The archive chain is unchanged: the operator still runs
`polaris-archive.sh` and `polaris-purge.sh`, and the purge still verifies the
manifest SHA-256 before deleting anything.

It does not enforce a jurisdiction's law. `jurisdiction` is an opaque
ten-character label the deployment chooses. Polaris holds the decision, its
justification and its author; whether the number satisfies a statute is a
question for the deployment's counsel.

It does not expire anything on its own. Nothing deletes on a timer. Retention
bounds what a purge is permitted to remove; running the purge stays a
deliberate operator action with an archive behind it.

## Where it is

| Part | Object |
|---|---|
| The table | `RetentionPolicy` (`polaris_sql/01_schema.sql`) |
| One effective row | `uq_effective_retention_policy` (`02_indexes.sql`) |
| Append-only | `trg_retention_policy_immutable` (`06_triggers.sql`) |
| Privilege boundary | `09_grants.sql` |
| Resolution | `retention_days_for`, `retention_cutoff` (`05_procedures.sql`) |
| Templates | `uc_apply_retention_template` (`05_procedures.sql`) |
| The guard | `uc_archive_purge` (`05_procedures.sql`) |
| Migration | `2026-09-05-001-retention-policy` |
| Tests | Section S of `08_tests.sql`; `TestRetentionEngine` in `polaris_web/test_check_constraints.py` |
| Invariant | `check_retention_engine` (`polaris_checks/checks.py`) |
