# DEVNOTES/concurrency.md

<!-- coherence:taxonomy-allowed — hazard inventory + 7 lock-pattern sections (UC-8, UC-9, etc. per use-case) + catalog summary; each pattern is a distinct concurrency hazard with its own lock, test, and rationale -->

What concurrency hazards exist, what protects against each, and what the
test for each protection is. Read before changing anything in
`05_procedures.sql`, `security.py::authenticate`, or any path that
touches `IdentityToken.status`.

---

## Hazard inventory

| # | Scenario | Pre-v6 outcome | Protection | Test |
|---|----------|----------------|------------|------|
| 1 | Two parallel UC-1s for the same individual | Both create new Individual rows + tokens. Not really a race; data quality issue. | None needed — UC-1 always creates a fresh Individual | n/a |
| 2 | Two parallel UC-1s for DIFFERENT individuals | Independent rows, no conflict | None needed | n/a |
| 3 | Two parallel UC-4s on the same `(lost_token, reserve_token)` pair | Idempotent — both T1 and T2 transition lost→LOST, both UPDATE reserve→ACTIVE. Final state correct; double `RevocationList` entry possible. | `SELECT FOR UPDATE Individual` serializes UC-4 per holder; second observer sees post-T1 state | `ConcurrencyTests.test_partial_unique_index_blocks_double_active` (related) |
| 4 | Two parallel UC-4s activating DIFFERENT reserves of same holder | Pre-v6: both could win because `activation_sequence=2` was hardcoded. Could leave holder with two ACTIVE tokens *briefly* — partial unique index fired only when both tried final UPDATE. | Same `FOR UPDATE` lock + partial unique index `uq_one_active_per_person` | `test_partial_unique_index_blocks_double_active` |
| 5 | Manual UPDATE of `IdentityToken.status='ACTIVE'` for a holder who already has one | Allowed → "two active tokens" violation | Partial unique index `uq_one_active_per_person` (DB-level) | `test_partial_unique_index_blocks_double_active` |
| 6 | Concurrent failed logins for same user | Pre-v6: TOCTOU lost increments; lockout bypassable. | Atomic `UPDATE … SET col = col + 1 RETURNING` | `test_failed_login_count_is_atomic_under_concurrent_load` |
| 7 | Threshold-crossing concurrent failed logins both apply lockout | Pre-v6: each could write `locked_until = now + lock_min`, doubling the lockout interval | `WHERE locked_until IS NULL` predicate on the lockout UPDATE | covered by atomic-increment test |
| 8 | Concurrent INSERTs into `TokenLifecycleEvent` | None — append-only by design, no conflicts | DB-level append-only (no shared row state) | n/a |
| 9 | Verification event arrives during a token revocation | The verification reads pre-revocation state and succeeds | Acceptable by design — verifications are point-in-time. Token state at verification was valid. | n/a |

---

## What the partial unique index actually protects

```sql
CREATE UNIQUE INDEX uq_one_active_per_person
    ON IdentityToken (individual_id)
    WHERE status = 'ACTIVE';
```

This is a **partial** unique index — it only enforces uniqueness on
rows where `status = 'ACTIVE'`. So a holder can have:

- 1 ACTIVE
- N RESERVE  (any number, no constraint)
- N DORMANT
- N REVOKED, LOST, EXPIRED  (terminal states, all permitted)

The moment two transactions both try to set `status='ACTIVE'` for the
same `individual_id`, exactly one succeeds. The other gets:

```
ERROR: duplicate key value violates unique constraint "uq_one_active_per_person"
DETAIL: Key (individual_id)=(N) already exists.
```

In the application, this surfaces as `psycopg2.errors.UniqueViolation`
which `db_error_to_message()` translates to a user-friendly message.

---

## Why `SELECT FOR UPDATE` instead of `SERIALIZABLE`

Three options were considered:

1. **Optimistic** — let the partial unique index reject conflicts;
   handle `UniqueViolation` in the app. Pro: no lock contention.
   Con: error surface complicated by the activation_sequence race
   (which the unique index doesn't catch, because seq is just a number,
   not constrained).

2. **`SERIALIZABLE` isolation** — let Postgres detect serialization
   anomalies and retry. Pro: clean. Con: requires retry logic in every
   caller; `psycopg2` doesn't auto-retry; and the failure mode is a
   late `SerializationFailure` exception which is harder to map to a
   domain error than a clean `UniqueViolation`.

3. **`SELECT FOR UPDATE` row lock** (chosen) — explicitly serialize on
   the holder row at the start of the procedure. Pro: deterministic;
   second writer observes post-T1 state and re-validates; no retry
   needed. Con: lock contention if many UC-4s for same holder fire
   simultaneously, but in practice UC-4 is rare (a holder reports a
   lost token once a year at most).

Option 3 also makes the `activation_sequence` race trivial to fix —
compute MAX inside the locked region.

---

## Why the auth atomic increment matters

The pre-v6 pattern was a textbook TOCTOU:

```python
new_count = user['failed_login_count'] + 1     # T  read N
# ... time passes, OTHER transaction reads N too ...
cur.execute("UPDATE … SET failed_login_count=%s …", (new_count,))   # write N+1
```

Two simultaneous failed logins both read `N`, both wrote `N+1`. Lost
increment. Concrete consequence: an attacker spammed parallel failed
logins; the counter never crossed the lockout threshold; brute force
was unrate-limited above the configured threshold.

The fix is the standard atomic-counter pattern:

```python
cur.execute(
    "UPDATE AppUser SET failed_login_count = failed_login_count + 1 "
    "WHERE user_id = %s RETURNING failed_login_count", (uid,))
new_count = cur.fetchone()['failed_login_count']
```

`UPDATE … SET col = col + 1` resolves under row-level lock in
PostgreSQL; both transactions queue at the lock; both see the correct
post-increment value via `RETURNING`.

---

## What's NOT protected (and why that's OK)

- **Verification event ordering** doesn't matter. Two parallel
  verifications can interleave freely; each is an independent
  append-only fact about a point in time.

- **Lifecycle event ordering** is preserved by the audit trigger
  (`audit_token_state_change`) which fires AFTER UPDATE on
  `IdentityToken`. Postgres serializes UPDATEs on the same row, so the
  trigger executions are serialized too. The lifecycle audit order
  reflects the actual UPDATE order.

- **Login successes** don't need atomicity beyond what the session
  cookie already provides. No counter, no lockout state to corrupt.

- **CSRF token generation** uses `secrets.token_urlsafe(32)` which is
  cryptographically random; collision probability is ignorable.

- **Rate limiter state** is in-memory, single-process. Multi-worker
  gunicorn deployments would each have independent counters; that's a
  known limitation documented in `security.py`. For multi-process,
  swap the in-memory dict for Redis.

---

## What to do if you find ANOTHER race

1. Add the scenario row to the table at the top of this file.
2. Decide: optimistic, FOR UPDATE, or SERIALIZABLE.
3. If FOR UPDATE: lock the SMALLEST row that contains the contested
   state. (For UC-1/UC-4: the Individual row, not the IdentityToken
   table.)
4. Add a test in `ConcurrencyTests` that uses `threading +
   ThreadPoolExecutor` to actually trigger the race. Don't mock it.
5. Document the race + fix here AND in the procedure comment.

Concurrency bugs that aren't in the test suite WILL come back.

---

## Advisory-lock pattern — UC-8 / R11-6 (added v8.15)

The bounded-revocation procedure (`uc8_revoke_token`) has a different
shape of race than the row-level ones above. The rate-limit check
reads `count(*)` across many `TokenLifecycleEvent` rows joined to
`IdentityToken` — there is no single row to `FOR UPDATE`. Two threads
both at the boundary could each read "you're at N revocations, one
more makes (N+1)" and both write, putting the system at N+2.

The fix is a **PostgreSQL transaction-scoped advisory lock** keyed on
the issuing agency id:

```sql
PERFORM pg_advisory_xact_lock(
    hashtext('polaris.revoke.' ||
        (SELECT issuing_agency_id::TEXT FROM IdentityToken WHERE token_id = p_token_id)));
```

Why this granularity:

- **Per-agency lock, not global.** Cross-agency revocations don't
  conflict — each agency has its own bound and its own counter.
  Locking globally would block legitimate parallel work needlessly.
  `ConcurrencyTests.test_uc8_cross_agency_revocations_do_not_block`
  asserts the parallelism behavior.
- **`hashtext` reduces the string key to the `bigint` that
  `pg_advisory_xact_lock` accepts.** Collision probability is
  ignorable at the cardinality of agency_ids.
- **`_xact_` flavor releases at COMMIT/ROLLBACK.** No application-side
  unlock; no leaked locks when a transaction errors out mid-way.

When to reach for this pattern:

- The contested state is a *derived* count (rate, sum, percentile),
  not a single row.
- You can map the contention to a natural key (an entity id) that's
  available at the start of the transaction.
- You want READ COMMITTED elsewhere in the schema (this is the case
  in Polaris) but need SERIALIZABLE-like guarantees on a specific
  procedure.

Anti-pattern: do not advisory-lock on a hash of the *token id* in
this case. The bound applies to the *issuing agency*. Two threads
revoking *different tokens issued by the same agency* must serialize;
locking on token_id would let them both pass.

---

## Per-individual advisory-lock — UC-9 / R11-2 (added v8.17)

Same pattern as UC-8, applied to a different shape of contention.
`uc9_complete_recovery` faces this race: two threads (or two
admins, one per browser tab) calling
`uc9_complete_recovery(recovery_id=X)` on the same PENDING request
would each pass the cool-down + three-channel CHECKs before either
UPDATE landed. Without serialization, both would issue new ACTIVE
tokens for the same individual — violating C3 (one ACTIVE per
individual) and producing two RevocationList entries for each lost
token.

```sql
PERFORM pg_advisory_xact_lock(
    hashtext('polaris.recovery.' ||
        (SELECT claimed_individual_id::TEXT
         FROM RecoveryRequest WHERE recovery_id = p_recovery_id)));
```

Lock key per claimed-individual (not per recovery_id, because two
different recovery_ids for the same individual would also conflict —
though the partial unique index `uq_one_pending_recovery_per_individual`
makes that case impossible). Cross-individual recoveries don't
conflict. Transaction-scoped.

Test: `ConcurrencyTests.test_uc9_advisory_lock_serializes_concurrent_completes`
fires T=4 threads at the same PENDING and asserts exactly one
succeeds, T-1 fail with "not PENDING".

---

## Per-token advisory-lock — UC-6 / R11-1 (added v8.18)

Third entry in the catalog. Same advisory-lock mechanism as UC-8 and
UC-9, but the contention is per-token: `uc6_migrate_algorithm` races
on the same token would both try to insert new TokenSignature rows
and the trigger checks could interleave dangerously.

```sql
PERFORM pg_advisory_xact_lock(
    hashtext('polaris.migrate.' || p_token_id::TEXT));
```

Why per-token:

- The contested state is the **active-signature set per token**.
- Two threads migrating *different tokens* don't conflict — each
  token has its own row in IdentityToken and its own set of
  TokenSignature rows.
- Two threads migrating the *same token* must serialize so the
  invariant trigger (`enforce_token_has_active_signature`) sees a
  consistent count.

Test: `ConcurrencyTests.test_uc6_per_token_lock_serializes_concurrent_migrations`
fires 3 threads each migrating the same token to 3 distinct
algorithms; all succeed, final state has 4 active signatures
(1 seed + 3 migrations). Plus
`test_uc6_cross_token_migrations_run_in_parallel` confirms the
wall-clock parallelism for different tokens.

### Verification-snapshot consistency model

Distinct from the lock: when verification reads
`TokenSignature WHERE deprecation_date IS NULL` and a migrator
concurrently sets `deprecation_date` on a row, what does the verifier
see?

The verifier sees its pre-migration snapshot under PostgreSQL's
default READ COMMITTED (each statement sees committed state at
statement start) or REPEATABLE READ (whole transaction sees txn-start
snapshot). New migrations are visible to *subsequent* transactions.
Test `test_uc6_verification_snapshot_consistent_with_migration`
asserts this contract explicitly so the verification path can rely
on it.

## Per-algorithm advisory-lock — R10-2 / M2-2 (added v8.21)

Fourth entry in the catalog. `close_anchor_batch(algorithm_id, root,
proofs)` groups pending `BlockchainAnchor` rows by their underlying
token's signature algorithm and inserts a single `AnchorBatch` row
plus per-leaf merkle proofs. Without a lock, two parallel calls for
the same algorithm could each see the full pending leaf set and
produce two batches — either with identical roots (a wasted batch)
or with the leaves silently split across two batches (breaks the
audit-of-record's "one batch per leaf" invariant).

The lock key is `hashtext('polaris.anchor.close-batch.' ||
algorithm_id::TEXT)`. Same-algorithm closes serialize; cross-algorithm
closes parallelize. Per-algorithm scope is natural: different
algorithms have *disjoint* pending leaf sets, so cross-algorithm
contention is impossible by construction.

Test: `ConcurrencyTests.test_close_anchor_batch_same_algorithm_serializes`
asserts that two parallel close calls for algorithm 2 produce a
single batch of size 2 (one thread wins the lock, the other finds no
pending leaves and gets `no_data_found`).
Test: `ConcurrencyTests.test_close_anchor_batch_cross_algorithm_parallel`
asserts that closes for algorithms 2 and 3 complete in ~0.3s (the
held lock duration), not ~0.6s (serialized).

See `DEVNOTES/ships/anchoring.md` for the broader R10-2 / M2-2 write-up.

## Per-attesting-agency advisory-lock — R11-3 / M2-8 (added v8.22)

Fifth entry in the catalog. `uc10_attest_trust` and
`uc10_revoke_attestation` both hold
`pg_advisory_xact_lock(hashtext('polaris.federation.attest.' ||
attesting_agency_id::TEXT))` for the transaction. Without the lock,
same-agency concurrent attest+revoke could interleave such that the
final state is ambiguous (did the revoke see the attestation that's
about to commit?).

Per-attesting-agency scope is the natural unit: a single agency's
federation decisions are coordinated by that agency's operators;
parallel decisions by *different* agencies have no overlapping state
and can run concurrently.

Test: `ConcurrencyTests.test_uc10_same_attesting_agency_serializes`
asserts that two parallel attests on the same attesting_agency_id
take ~0.6s (one sleeps 0.3s holding the lock; the other waits then
sleeps 0.3s). The test manually holds the lock to make the
serialization timing observable; the procedure's lock acquisition
inside is a no-op reacquire on the same transaction.
Test: `ConcurrencyTests.test_uc10_cross_attesting_agency_parallelizes`
asserts cross-agency parallelism completes in ~0.3s.

See `DEVNOTES/ships/federation.md` for the broader R11-3 / M2-8 write-up.

## Per-procedure advisory-lock — R10-1 / M2-1 (added v8.23)

Sixth entry in the catalog. `uc11_close_epoch` holds
`pg_advisory_xact_lock(hashtext('polaris.zk.close-epoch'))` — a
**single global key** rather than a per-entity key. The reason: epoch
closures are inherently global (`epoch_id` is a SERIAL), and
serializing them avoids race conditions on SERIAL assignment and on
the per-procedure Merkle-commitment workflow.

Distinct from the prior five entries, which are per-entity (per-agency,
per-individual, per-token, per-algorithm, per-attesting-agency). The
per-procedure scope here is the natural unit: the procedure is the
"entity" being serialized.

Test: `ConcurrencyTests.test_uc11_close_epoch_serializes_under_lock`
asserts that two parallel calls take ~0.6s (the manually-held lock
forces serialization).
Test: `ConcurrencyTests.test_uc11_close_epoch_both_rows_committed`
asserts that both serialized closures commit (lock = ordering, not
loss-of-write).

See `DEVNOTES/ships/zk-snark.md` for the broader R10-1 / M2-1 write-up.

## Catalog summary

| Procedure | Lock granularity | Cross-key parallelism |
|---|---|---|
| `uc8_revoke_token` | per-agency | cross-agency parallel |
| `uc9_complete_recovery` | per-individual | cross-individual parallel |
| `uc6_migrate_algorithm` | per-token | cross-token parallel |
| `close_anchor_batch` | per-algorithm | cross-algorithm parallel |
| `uc10_attest_trust` / `uc10_revoke_attestation` | per-attesting-agency | cross-attesting-agency parallel |
| `uc11_close_epoch` | per-procedure (global) | N/A — all closures serialize |

The same mechanism applied at six different granularities, each
chosen to match the *natural scope of contention* for that procedure.
The sixth entry breaks the per-entity pattern explicitly: ZK epoch
closures are inherently global because the merkle_root commitment
shape doesn't admit cross-key parallelism.
