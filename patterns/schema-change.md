# patterns/schema-change.md

## Trigger

- A new column or table is needed
- An existing constraint needs tightening
- An index needs adding / removing
- A migration is required (production already has data)

## Recipe

### 1. Decide: in-place vs versioned migration

Polaris currently uses `00_load_all.sql` which DROPs and recreates
everything from scratch. This is fine for development and tests but
DESTRUCTIVE in production.

**Development / tests:** Add the change to the appropriate file in
`polaris_sql/` (typically `01_schema.sql` for tables, `02_indexes.sql`
for indexes, or a new `12_v7_constraints.sql` if it's a coherent
batch).

**Production:** A real migration tool is on the BACKLOG. Until then:
write a separate `migrate_vN_to_vN+1.sql` script that uses `ALTER
TABLE` and is idempotent (`IF NOT EXISTS` everywhere).

### 2. Classify the change against MISSION.md

- Adding a new column to an audit table → audit invariant (C1) check:
  the column should not enable bypassing the append-only constraint
- New CHECK constraint → strengthens an existing constraint (good)
- DROP CHECK constraint → weakens (HIGH risk; needs proposal)
- Index addition → performance only (LOW risk)
- DROP INDEX → check what queries depend on it
- New trigger → audit the trigger interaction with existing triggers
  (order matters; PostgreSQL fires them alphabetically by name)

### 3. Write the change idempotently

```sql
-- For tables / columns:
ALTER TABLE Foo ADD COLUMN IF NOT EXISTS bar INTEGER;

-- For indexes:
CREATE INDEX IF NOT EXISTS idx_foo_bar ON Foo(bar);

-- For triggers:
DROP TRIGGER IF EXISTS trg_foo ON Foo;
CREATE TRIGGER trg_foo BEFORE UPDATE ON Foo ...;

-- For constraints:
DO $$ BEGIN
    ALTER TABLE Foo ADD CONSTRAINT chk_foo CHECK (...);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
```

Idempotency lets the file be re-run on a database that may or may
not already have the change.

### 4. Backfill existing data if necessary

If the new column has a NOT NULL constraint, existing rows need a
default value. Two approaches:

```sql
-- Approach A: ADD COLUMN with DEFAULT, then DROP DEFAULT
ALTER TABLE Foo ADD COLUMN bar INTEGER NOT NULL DEFAULT 0;
ALTER TABLE Foo ALTER COLUMN bar DROP DEFAULT;

-- Approach B: ADD COLUMN nullable, backfill, then NOT NULL
ALTER TABLE Foo ADD COLUMN bar INTEGER;
UPDATE Foo SET bar = compute_bar(...) WHERE bar IS NULL;
ALTER TABLE Foo ALTER COLUMN bar SET NOT NULL;
```

Approach B is needed if `bar` requires a computed value, not a
constant default.

### 5. Add SQL self-tests in 08_tests.sql or the new file

For new constraints:

```sql
DO $$
DECLARE v_caught BOOLEAN := FALSE;
BEGIN
    BEGIN
        -- attempt the disallowed thing
        INSERT INTO Foo (bar) VALUES (-1);
    EXCEPTION WHEN check_violation THEN
        v_caught := TRUE;
        RAISE NOTICE 'TEST X-N PASS: <description>';
    END;
END $$;
```

For new indexes, add an EXPLAIN ANALYZE check that the planner uses
the new index for the expected query.

### 6. Add Python tests if the change affects the application layer

If the change is purely SQL (e.g., new index for performance), no
Python test is needed. If the change adds a new field that the app
should read or set, add tests.

For property-style invariant checks, add to
`test_invariants_property.py`.

### 7. Reload + verify

```bash
# Test reload (destructive; OK in dev)
cd polaris_sql && su postgres -c "psql -d polaris_test -f 00_load_all.sql"

# Verify Python tests still pass
cd ../polaris_web && python3 test_app.py
```

### 8. Documentation

- `docs/reference/DATA-MODEL.md` — update the affected table's column list and any
  noted indexes/triggers
- `CHANGELOG.md` — entry with the schema change
- `DEVNOTES/known-gotchas.md` — if the change introduces a non-
  obvious behavior, note it

### 9. Mission constraint check

- Did this change weaken any C1-C10 constraint? If yes, this is HIGH
  risk; needs a proposal (see `meta/autonomy-architecture.md`).
- Did this change strengthen one? Good — note it in CHANGELOG.

## Pre-known gotchas

- **DROP TABLE CASCADE in 00_load_all.sql kills data.** Never run it
  against production. Production migrations use ALTER TABLE.

- **Trigger order matters.** PostgreSQL fires triggers alphabetically
  by name. If you have `trg_audit` and `trg_validate`, audit fires
  before validate, which may not be what you want. Use names like
  `trg_a_validate`, `trg_b_audit` to control order.

- **`CREATE OR REPLACE FUNCTION` requires identical signatures.** If
  you change the parameter list of a function used by triggers, you
  must DROP the trigger first, replace the function, then re-CREATE
  the trigger.

- **Adding a partial unique index can fail at creation if existing
  data already violates.** Verify with a SELECT first:

  ```sql
  SELECT individual_id, count(*) FROM IdentityToken
  WHERE status = 'ACTIVE'
  GROUP BY individual_id HAVING count(*) > 1;
  ```

- **GRANT statements run from 09_grants.sql which loads BEFORE later
  files.** A view or function created in `12_*.sql` cannot be
  GRANTed in `09_grants.sql` — put the GRANT in `12_*.sql` itself,
  after the CREATE.

- **Materialized views are NOT auto-refreshed.** If you create one,
  document the refresh strategy (cron, app-triggered, or REFRESH
  CONCURRENTLY).

## Completion check

- [ ] Change is idempotent (`IF NOT EXISTS` / EXCEPTION-handled)
- [ ] Existing data backfilled if needed
- [ ] SQL self-test added for new constraints
- [ ] Python test added if the app layer is affected
- [ ] Full test suite passes
- [ ] docs/reference/DATA-MODEL.md updated
- [ ] CHANGELOG.md entry
- [ ] No C1-C10 constraint weakened (or if it was, HIGH-risk
      proposal written first)
- [ ] GRANTs in the right file (same file as the new object, not
      09_grants.sql, if it loads later)
