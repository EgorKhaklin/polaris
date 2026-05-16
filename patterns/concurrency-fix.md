# patterns/concurrency-fix.md

## Trigger

User says any of:
- "race condition", "TOCTOU"
- "concurrent", "parallel"
- "atomic", "locked"
- "two users at the same time"
- "lockout bypassable", "increment lost"

Or you find a SELECT-then-UPDATE pattern that depends on the
intermediate value.

## Recipe

### 1. Classify the hazard

Read `DEVNOTES/concurrency.md`. Add a row to its table at the top with
the new scenario before doing anything else. If you can't characterize
the race in one sentence, you don't understand it well enough to fix.

### 2. Pick the protection

In order of preference:

| Mechanism | When to use |
|---|---|
| **Atomic SQL** (`UPDATE … SET col = col + 1 RETURNING …`) | Any counter / accumulator |
| **Partial unique index** (`CREATE UNIQUE INDEX … WHERE …`) | Invariants like "at most one X per Y in state Z" |
| **`SELECT FOR UPDATE`** | Multi-statement procedures where the holding transaction needs to read-modify-write across rows |
| **`SERIALIZABLE` isolation** | Last resort. Requires retry logic in every caller; psycopg2 doesn't auto-retry. |

### 3. Implement

- For SQL procedures: `polaris_sql/05_procedures.sql`
- For app-level (auth, request handlers): `polaris_web/security.py` or `polaris_web/app.py`
- After editing 05_procedures.sql, you must reload it:
  `psql -d $DB -f polaris_sql/05_procedures.sql`
  (or run the full loader)

### 4. Test with REAL threading

- Add the test to `class ConcurrencyTests(PolarisTestCase)` in `test_app.py`
- Use `concurrent.futures.ThreadPoolExecutor` or `threading.Thread`
- **Each thread needs its own connection** — psycopg2 connections are
  not thread-safe
- Don't mock the race; trigger it. If the test passes serially but you
  haven't actually exercised concurrency, you've tested the wrong thing.

### 5. Update docs

- Add the protection to the table in `DEVNOTES/concurrency.md`
- Add a one-line entry in `CHANGELOG.md` under the current version
- If the pattern was non-obvious, append to `DEVNOTES/known-gotchas.md`

## Pre-known gotchas

- **TOCTOU pattern in Python**: `new = row['x'] + 1; UPDATE SET x=%s` is
  always wrong if x is shared. Use `UPDATE SET x = x + 1 RETURNING x`.

- **Lockout double-apply**: when several concurrent failures both cross
  the threshold, each will write `locked_until = now + interval`,
  doubling the lockout. Add `WHERE locked_until IS NULL` to the
  conditional UPDATE.

- **The partial unique index is your safety net but not your strategy.**
  It will catch double-active-token, but the user-facing error is a
  generic UniqueViolation. Add `FOR UPDATE` upstream so the second
  caller observes post-first-caller state and gets a clean domain
  error.

- **`activation_sequence` was hardcoded to 2** pre-v6 — both wrong past
  the second active token AND a TOCTOU. The MAX(seq)+1 computation must
  happen INSIDE the locked region or the race comes back.

- **Tests that auth-fail several times will lock the admin account.**
  Either reset the admin row at test setup, or use a fresh test user
  for the auth-failure scenario (the v6 tests do the latter).

## Completion check

- [ ] Race documented in `DEVNOTES/concurrency.md` table
- [ ] Protection chosen with a sentence-long justification
- [ ] Test in `ConcurrencyTests` actually triggers the race via threads
- [ ] Test PASSES (and would have FAILED on the pre-fix code)
- [ ] CHANGELOG updated
- [ ] If new pattern: appended to known-gotchas.md
