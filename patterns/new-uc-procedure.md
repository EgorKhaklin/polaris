# patterns/new-uc-procedure.md

## Trigger

- "add UC-N", "new use case"
- "stored procedure for X workflow"
- A multi-step business operation that reads + writes multiple tables atomically
- The user is mapping a real-world process (issue, transition, revoke) to code

## Recipe

### 1. Decide: stored procedure vs. application code

| Use a stored procedure when… | Use application code when… |
|---|---|
| The operation touches 3+ tables atomically | The operation is a single INSERT/UPDATE |
| Domain invariants must hold even if app is buggy | Logic is presentation-layer only |
| Concurrency requires holding row locks | No shared mutable state |
| The operation is a documented SCS-230 use case | One-off helper |

UC-1 (Issue), UC-4 (Activate Reserve), UC-5 (Bind Device), UC-7 (Audit Warrant) are stored procedures because they cross multiple tables AND are SCS-230-graded business operations. Internal helpers like "compute holder display name" stay in app code.

### 2. Define the contract first

In a comment block at the top of the procedure body:

```sql
-- ============================================================================
-- UC-N: HUMAN-READABLE NAME
--
-- Purpose:    one sentence
-- Inputs:     parameter list with type + meaning
-- Outputs:    return value + meaning
-- Side effects:
--   - INSERT into TableA (specific rows)
--   - UPDATE TableB (which rows, which columns)
--   - emits TokenLifecycleEvent of kind X (via trigger)
-- Concurrency:
--   - takes Individual row lock for input.individual_id
--   - safe to call concurrently for different individuals
--   - serialized for the same individual via FOR UPDATE
-- Domain errors raised:
--   - 'TOKEN_NOT_FOUND'        if input doesn't reference a real token
--   - 'INVALID_STATE_TRANSITION' if business rules forbid the move
--   - 'CONCURRENT_OPERATION'    if FOR UPDATE timeout
-- ============================================================================
```

This is load-bearing documentation. Future me reads it before changing the body.

### 3. Lock ordering

Always lock in a consistent order to prevent deadlocks. The convention in Polaris:

1. `Individual` row first (the holder)
2. `IdentityToken` rows (oldest → newest token_id)
3. `Agency` row last (rarely contested)

If your procedure needs to lock multiple individuals, lock in `individual_id` order ascending.

### 4. Skeleton

```sql
CREATE OR REPLACE PROCEDURE ucN_do_thing(
    p_input_a    INTEGER,
    p_input_b    TEXT,
    p_actor_id   INTEGER,
    OUT p_result_token_id INTEGER
) LANGUAGE plpgsql AS $$
DECLARE
    v_individual_id INTEGER;
    v_some_state    TEXT;
BEGIN
    -- 1. VALIDATE inputs (cheap checks before locking)
    IF p_input_a IS NULL THEN
        RAISE EXCEPTION 'INPUT_A_REQUIRED';
    END IF;

    -- 2. LOCK the holder
    SELECT individual_id INTO v_individual_id
    FROM   IdentityToken
    WHERE  token_id = p_input_a;
    IF v_individual_id IS NULL THEN
        RAISE EXCEPTION 'TOKEN_NOT_FOUND';
    END IF;
    PERFORM 1 FROM Individual WHERE individual_id = v_individual_id FOR UPDATE;

    -- 3. RE-READ contested state (post-lock)
    SELECT status INTO v_some_state
    FROM   IdentityToken WHERE token_id = p_input_a;

    -- 4. CHECK invariants under lock
    IF v_some_state != 'EXPECTED_STATE' THEN
        RAISE EXCEPTION 'INVALID_STATE_TRANSITION'
            USING DETAIL = format('expected EXPECTED_STATE, got %s', v_some_state);
    END IF;

    -- 5. EXECUTE state changes
    -- Set GUCs the audit trigger reads
    PERFORM set_config('polaris.actor_agency_id', p_actor_id::text, TRUE);
    PERFORM set_config('polaris.reason_code', 'UC_N_DOES_THING', TRUE);

    UPDATE IdentityToken SET status = 'NEW_STATE'
    WHERE  token_id = p_input_a
    RETURNING token_id INTO p_result_token_id;

    -- 6. EXPLICIT lifecycle event (if not auto-emitted by trigger)
    -- The audit_token_state_change trigger covers UPDATEs to IdentityToken,
    -- so don't double-insert here unless your event isn't a state change.
END;
$$;
```

### 5. Test (08_tests.sql)

Add a test in `polaris_sql/08_tests.sql`:

```sql
-- Test UC-N: happy path
DO $$
DECLARE
    v_result INTEGER;
BEGIN
    CALL ucN_do_thing(1, 'something', 1, v_result);
    IF v_result IS NULL THEN
        RAISE EXCEPTION 'UC-N failed: no token returned';
    END IF;
    RAISE NOTICE 'UC-N happy path: PASS';
EXCEPTION WHEN OTHERS THEN
    RAISE NOTICE 'UC-N happy path: FAIL — %', SQLERRM;
END;
$$;

-- Test UC-N: rejects bad input
DO $$
BEGIN
    BEGIN
        CALL ucN_do_thing(NULL, 'something', 1, NULL);
        RAISE NOTICE 'UC-N null input: FAIL — should have raised';
    EXCEPTION WHEN raise_exception THEN
        IF SQLERRM LIKE '%INPUT_A_REQUIRED%' THEN
            RAISE NOTICE 'UC-N null input: PASS';
        ELSE
            RAISE NOTICE 'UC-N null input: FAIL — wrong error: %', SQLERRM;
        END IF;
    END;
END;
$$;
```

### 6. Test (test_app.py)

If the procedure is exposed via a route, add a test class:

```python
class UCNTests(PolarisTestCase):
    def test_happy_path(self): ...
    def test_rejects_invalid_state(self): ...
    def test_emits_lifecycle_event(self): ...
    def test_respects_role_based_access(self): ...
```

### 7. Concurrency test (if shared state)

Add a row to `DEVNOTES/concurrency.md` table. If the procedure touches shared rows, add a `ConcurrencyTests` test that fires it from multiple threads.

## Pre-known gotchas

- **`SELECT 1 FROM X FOR UPDATE` without storing the result will work** because PERFORM doesn't return — but it ALSO won't error if the row doesn't exist. Always pre-validate with a SELECT INTO.

- **The audit trigger reads GUCs** (`polaris.actor_agency_id`, `polaris.reason_code`, `polaris.event_lat`, `polaris.event_lon`). Set them via `set_config(name, value, TRUE)` where the `TRUE` makes it transaction-local.

- **`RAISE EXCEPTION 'CODE'`** uses the code as the error message. Surfaces as `psycopg2.errors.RaiseException` in app code with `e.diag.message_primary == 'CODE'`. Match the existing string codes for `db_error_to_message()` to translate cleanly.

- **`CALL` vs `SELECT` matters.** Procedures use CALL; functions use SELECT. App code must use the right one or psycopg2 returns 0 rows silently.

- **OUT parameters vs RETURNS TABLE.** OUT params are simpler for single-row results. RETURNS TABLE for multi-row.

- **Don't INSERT into TokenLifecycleEvent directly when the trigger covers it.** Double-emission corrupts the audit trail.

## Completion check

- [ ] Contract documented at top of procedure
- [ ] Lock order matches the convention (Individual → Token → Agency)
- [ ] Pre-validation before locks
- [ ] Re-read contested state after lock
- [ ] Audit GUCs set if relevant
- [ ] SQL self-test in `08_tests.sql` for happy path + rejection cases
- [ ] App-level test class if exposed via route
- [ ] Concurrency test added if shared state is touched
- [ ] CHANGELOG entry under current version
