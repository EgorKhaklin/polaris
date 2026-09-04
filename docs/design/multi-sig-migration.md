# Algorithm migration

**Reader:** an engineer or an assessor. **Job:** How a token moves to a new signature algorithm without a gap in coverage.

---

## What this is

The M:N resolution of `IdentityToken → signature`. A token can carry
signatures from multiple cryptographic algorithms during a migration
window — the case the PDF §9.4 phrase names:

> *"how tokens transition between post-quantum primitives when one of
> them itself is later weakened or superseded: the second-generation
> migration problem, when ML-DSA or SLH-DSA is replaced by a successor
> algorithm. A production system would require either simultaneous
> mass reissuance, or a multi-signature scheme where tokens can accept
> signatures from multiple algorithms during transition periods."* implements the multi-signature scheme. Simultaneous mass
reissuance was the other option in the PDF; it's not viable at
population scale.

## The issuer-trust-concentration triad closes one leg of the **issuer-trust-concentration triad**
named in PDF §9:

| Leg | PDF §9 requirement | Item | Status |
|---|---|---|---|
| **Cryptographic diversity** | "cryptographic diversity across issuers" | **** | ✅ v8.18 |
| Federation | "a federation model with mutual recognition between independent authorities" | | ⬜ |
| Constitutional limits | "constitutional limits on issuer discretion" | | ✅ v8.15 | sits at the intersection of both triads — exit leg of the
holder-protection triad AND third leg of the issuer-trust triad.
Shipping closes leg 1 of issuer-trust. ** is now the only
unshipped leg across both triads.**

## What this is NOT

- **Not Polaris deciding which algorithm to use.** The schema records
  the algorithm a signature was generated under; agencies and the
  jurisdiction's cryptographic authority decide which algorithms are
  credible. Same posture as / C7.
- **Not auto-derivation of `TokenSignature.deprecation_date` from
  `CryptographicAlgorithm.deprecation_date`.** The two columns serve
  different purposes:
  - `CryptographicAlgorithm.deprecation_date` says "this algorithm is
    end-of-life globally."
  - `TokenSignature.deprecation_date` says "this specific signature
    is no longer accepted."
  Operator policy (UC-6) drives both, separately. Setting the
  algorithm-wide date does NOT cascade into any TokenSignature row.
- **Not a real cryptographic signing operation.** The reference
  implementation inserts placeholder bytes (e.g., `UC1_ISSUE_PLACEHOLDER_<token>`,
  `BACKFILL_PLACEHOLDER_<token>`, `UC9_RECOVERY_PLACEHOLDER_<recovery>_TOKEN_<token>`).
  Production would derive `signature_bytes` from a hardware-attested
  signing ceremony external to the database.
- **Not key escrow.** Private signing keys remain not held by the
  issuer post-issuance, per MISSION.md architectural-soul section 5.
- **Not multi-party signing.** That would be threshold signatures —
  a different problem.
- **Not a separate `TokenMigrationEvent` audit table.** The
  TokenSignature row itself IS the audit-of-record. The
  append-only invariants (DELETE forbidden, UPDATE confined to
  one-way `deprecation_date`) preserve the migration trail in the
  row's own state.

## The two invariants

**Invariant 1:** Every IdentityToken has at least one non-deprecated
TokenSignature row.

Enforced by `enforce_token_has_active_signature` (AFTER INSERT/UPDATE/DELETE
on TokenSignature). The trigger counts active signatures for the
affected token; if zero, RAISE. The check fires AFTER the operation,
so the committed-state row count is what's checked.

**Invariant 2:** TokenSignature is write-once, with one-way
`deprecation_date`.

Enforced by `enforce_token_signature_immutability` (BEFORE UPDATE/DELETE):

- DELETE forbidden outright (would erase the migration record).
- UPDATE to `signature_id` / `token_id` / `algorithm_id` /
  `signature_bytes` / `signed_at` → forbidden.
- UPDATE to `deprecation_date`:
  - NULL → timestamp: **allowed once**.
  - timestamp → NULL: **forbidden** (cannot un-deprecate).
  - timestamp → earlier timestamp: **forbidden** (cannot backdate).
  - timestamp → later timestamp: allowed (extending the migration
    window is legitimate).

Together these enforce: signatures are immutable except for the
deprecation marker, and tokens never end up signature-less.

## The migration ceremony

UC-6 (`uc6_migrate_algorithm`) is the single sanctioned path:

```sql
CALL uc6_migrate_algorithm(
    p_token_id        => 42,
    p_new_algorithm   => 2,       -- ML-DSA-87
    p_new_signature   => <bytes>, -- hardware-attested in production
    p_deprecate_old   => FALSE    -- two sigs coexist (migration window)
                                  -- OR TRUE to deprecate old now
);
```

Steps:

1. `pg_advisory_xact_lock(hashtext('polaris.migrate.' || token_id))`
   — C9 correctness; per-token serialization. Cross-token migrations
   remain parallel.
2. Validate token exists.
3. Validate new algorithm exists and is not itself deprecated.
4. INSERT new TokenSignature row (UNIQUE constraint blocks
   duplicate-algorithm migrations).
5. Optionally UPDATE other active signatures' deprecation_date.
   The constraint `deprecation_after_signed` requires
   `deprecation_date > signed_at`, so the UPDATE uses `NOW() +
   INTERVAL '1 second'` to satisfy the CHECK on
   millisecond-old rows.
6. The two triggers fire automatically:
   - `enforce_token_has_active_signature` re-checks the count.
   - `enforce_token_signature_immutability` allows the deprecation_date
     UPDATE but rejects any other mutation.

## The verification consistency model

Verification reads from `TokenSignature WHERE deprecation_date IS
NULL`. Two threads — verifier A and migrator B — racing on the same
token: what does A see?

**Answer: A sees its pre-migration snapshot.** Under PostgreSQL's
default READ COMMITTED isolation, each statement sees rows committed
before the statement started. Under REPEATABLE READ (used in some
verification paths for stronger guarantees), the entire transaction
sees the snapshot at txn start.

The test `ConcurrencyTests.test_uc6_verification_snapshot_consistent_with_migration`
documents this contract: a verifier transaction reading the active
signature set, then doing other work, then re-reading — sees the
same set both times even though a migrator committed in between.
New migrations are visible only to *subsequent* transactions.

This is the correct semantic. A verifier that started its work
under the pre-migration crypto regime should complete under that
regime; the migration takes effect for the next request.

## Why the partial index

`idx_token_signature_active ON TokenSignature(token_id) WHERE
deprecation_date IS NULL` shrinks the index to just the active set.
Typically 1–2 rows per token (one signature normally; two during a
brief migration window). The historical-deprecated rows accumulate
indefinitely (append-only) but stay out of the partial index. The
verification query is therefore O(1) effectively, not O(history).

## Backfill

Every existing IdentityToken row (from v1 sample data) needs a
TokenSignature backfill. Done in `04_data.sql`:

```sql
INSERT INTO TokenSignature (token_id, algorithm_id, signature_bytes, signed_at)
SELECT t.token_id, t.algorithm_id,
       ('BACKFILL_PLACEHOLDER_' || t.token_id::TEXT)::BYTEA,
       t.issued_date
FROM IdentityToken t
ORDER BY t.token_id;
```

For new tokens issued via UC-1 or UC-9 (recovery), the procedure
itself inserts a placeholder TokenSignature row alongside the
IdentityToken. The placeholder tag distinguishes reference-
implementation signatures from real production ones.

## Adversary walk

1. **Defender's claim:** Every token has ≥ 1 active signature under
   a non-deprecated algorithm at all times.
2. **Attacker's optimal response:** During the migration window,
   target the weakest currently-active algorithm. If old + new are
   both active and old is cryptanalyzed, forge under old.
3. **Equilibrium:** The "active set" of algorithms at any moment is
   those still cryptographically credible. As soon as an algorithm
   is deprecated, its signatures no longer verify (regardless of how
   many tokens have rows under it). The migration window is operator-
   controlled but bounded.
4. **Second-best attack:** Race condition during deprecation cutover
   — algorithm flagged deprecated, but a verification in flight
   already read the old algorithm row. Defended by the verification
   consistency model above: a verifier's transaction sees its
   pre-deprecation snapshot, which is the correct (read-stable)
   behavior; new requests after the cutover read the post-deprecation
   state.
5. **Defender's cost:** During a migration window, every verification
   does N reads instead of 1 (N = number of active signatures per
   token). The partial index keeps this O(1) in practice. The
   operator's cost is procedural: every token must be UC-6-migrated
   individually (or in bulk via a script invoking UC-6).
6. **Mechanism-design note:** Multi-signature shifts the algorithm-
   migration problem from "everything fails at once when an algorithm
   breaks" to "the operator orchestrates an orderly transition window."
   The schema enables the orderly version; the operator drives it.

## Per-token advisory lock — concurrency model

Pattern catalog (see `docs/design/concurrency.md`):

| Use case | Lock key | Granularity |
|---|---|---|
| UC-8 revocation | per-agency | Cross-agency parallel |
| UC-9 recovery | per-individual | Cross-individual parallel |
| **UC-6 migration** | **per-token** | **Cross-token parallel** |

Three patterns, three granularities, same mechanism. The catalog
entry in `docs/design/concurrency.md` documents the pattern.

## Cross-references

- PDF §9.4 "Cryptographic migration during transitions" — original
  problem statement.
- `proposals/-multisig-transitional.md` — the post-audit
  proposal with the seven refinements folded in.
- `MISSION.md` *Polaris is NOT an authority* + C7 — the constraints calibrates against and strengthens.
- `docs/design/issuer-discretion.md` —, the constitutional-limits
  leg of the issuer-trust triad.
- `docs/design/concurrency.md` — the advisory-lock pattern catalog.
- `docs/operator/SECURITY.md` — cryptographic-migration subsection.
