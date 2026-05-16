# proposals/R11-1-multisig-transitional.md

**Risk class:** MEDIUM (propose-and-wait)
**Mission link:** v2 M2-6 (open problems, PDF §9.4)
**Status:** PROPOSED, awaiting VANTA approval
**Effort:** ~2 sessions

## Problem

`IdentityToken` currently carries a single `algorithm_id`. When NIST
publishes the ML-DSA successor (or, less optimistically, when ML-DSA
gets cryptanalyzed), every active token needs a fresh signature under
the new algorithm. Under the current schema, this requires reissuing
every active token, which:

- Loses the predecessor lineage continuity for the migration window
- Is operationally infeasible at population scale (millions of
  reissuance ceremonies in a short window)
- Violates "post-quantum by default" in spirit: the system claims
  PQ-ready but has no PQ-migration path encoded in the schema

PDF §9.4 names this as an open problem. Polaris's most prominent claim
(post-quantum by default) is partially aspirational until M2-6 lands.

## Why MEDIUM

The change touches core verification flow (every verification reads a
signature). The migration of existing rows requires care to not break
the v1 sample data or in-flight tokens. New invariants are introduced.

LOW would be wrong — the verification flow change has fan-out into
UC-6 (algorithm migration), the dashboard's Post-Quantum panel, and
the cluster aggregation in 11_atlas.sql.

HIGH would be over-cautious — the change is well-bounded (one new
table, one column nullable/deprecated, no app-layer changes beyond
the verification read).

## The issuer-trust-concentration triad

R11-1 closes the **cryptographic-diversity** leg of the PDF §9
"Issuer trust concentration" triad. Read in parallel to the
holder-protection triad (R11-4 entry + R11-6 exit + R11-2 recovery,
all shipped), the issuer-trust triad has three legs:

| PDF §9 requirement | Item | Status |
|---|---|---|
| **Cryptographic diversity** across issuers | **R11-1 (this proposal)** | ⬜ |
| Federation model with mutual recognition between independent authorities | M2-8 | ⬜ |
| Constitutional limits on issuer discretion | R11-6 | ✅ v8.15 |

R11-6 sits at the **intersection** of both triads — it is the
"exit" leg of holder-protection AND the third leg of issuer-trust.
Shipping R11-1 closes leg 1 of issuer-trust. M2-8 then remains as
the unbuilt third leg.

The strategic shape: when both triads' "cryptographic" and
"federation" legs are built, every named PDF §9 production-system
requirement has a structural defense in the schema.

## "Schema records, agencies decide"

This is R11-1's expression of the architectural posture established
by R11-6, R11-4, and R11-2: the schema adds vocabulary and
structural constraints; the agencies make the actual decision.

In R11-1 specifically:

- The **decision** about *when* to migrate (which token to which
  algorithm) belongs to the issuing agency (or to operator policy
  reacting to a cryptanalysis announcement). The schema does not
  schedule migrations.
- The **decision** about *what algorithms are credible* belongs to
  NIST or the deploying jurisdiction's cryptographic authority. The
  schema does not pick algorithms.
- The **decision** about *when to deprecate* a specific token's
  signature belongs to operator policy. The schema records the
  `deprecation_date` as a policy event; it does not auto-compute it.

What the schema enforces:

- A token cannot end up with zero active signatures (trigger
  `enforce_token_has_active_signature`).
- A token cannot have two signatures under the same algorithm
  (UNIQUE constraint).
- A signature cannot be backdated or have its bytes mutated
  (append-only invariant — see refinement #2 below).
- Per-token migrations serialize cleanly under concurrent calls
  (advisory-lock — see refinement #1 below).

This puts R11-1 in the same category as **C3** (one ACTIVE per
individual: constraint on issuance behavior, not a holder verdict),
**C7** (algorithm metadata via table: constraint on what an agency
may sign with), and the three holder-protection legs already
shipped. The MISSION constraint *"Polaris is NOT an authority"* is
preserved because Polaris remains a recording and
constraint-enforcement surface, not a deciding one.

## Game-theoretic structure

- **Game type:** Repeated cooperative game across cryptographic eras.
  Each algorithm has a deprecation horizon; the system must remain
  verifiable across the transition without a verification gap.
- **Defender's claim:** Every token has ≥ 1 active signature under
  a non-deprecated algorithm at all times.
- **Attacker's optimal response:** During the migration window, target
  the weakest currently-active algorithm. If old + new are both
  active and old is cryptanalyzed, forge under old.
- **Equilibrium:** "Active set" of algorithms is always those still
  cryptographically credible. As soon as an algorithm is deprecated,
  its signatures no longer verify (regardless of how many tokens
  have rows under it).
- **Second-best attack:** Race condition during deprecation cutover —
  algorithm flagged deprecated, but a verification in flight already
  read the old algorithm row. Defended by `deprecation_date` being a
  hard CHECK at verification time, not a fast-changing flag.
- **Mechanism-design note:** the migration window is the dangerous
  period. Length is operator-controlled but the schema enforces that
  during the window, BOTH signatures must be valid; once new is
  deployed broadly enough, old's `deprecation_date` is set and only
  new verifies thereafter.

Directly extends **C7** (algorithm metadata via table) — adds a
many-to-many relation between tokens and algorithms instead of a
one-to-one.

## Recommended approach

Decouple signature from token. The new `TokenSignature` table is the
M:N resolution. `IdentityToken.algorithm_id` is kept as the "primary
algorithm" for backward compatibility but verification reads from
`TokenSignature`.

Three steps:

1. Add `TokenSignature` table with composite invariants.
2. Backfill: for every existing `IdentityToken`, create one
   `TokenSignature` row using the token's current
   `algorithm_id` and a `signature_bytes` value generated at backfill
   time.
3. Refactor verification to read the active signature set.

`IdentityToken.algorithm_id` is NOT removed; it serves as the
"originally issued under" field for audit purposes. New invariant:
every token has ≥ 1 row in `TokenSignature` with
`deprecation_date IS NULL`.

## Implementation sketch

### Schema

```sql
CREATE TABLE TokenSignature (
    signature_id       SERIAL       PRIMARY KEY,
    token_id           INTEGER      NOT NULL
                       REFERENCES IdentityToken(token_id),
    algorithm_id       INTEGER      NOT NULL
                       REFERENCES CryptographicAlgorithm(algorithm_id),
    signature_bytes    BYTEA        NOT NULL,
    signed_at          TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deprecation_date   TIMESTAMP,
        -- NULL = currently active; non-NULL = no longer accepted
        -- after this timestamp

    CONSTRAINT one_signature_per_algorithm_per_token
        UNIQUE (token_id, algorithm_id),

    CONSTRAINT deprecation_after_signed CHECK (
        deprecation_date IS NULL OR deprecation_date > signed_at
    )
);

-- Every token must have at least one ACTIVE signature.
-- Enforced via trigger because partial-unique-index can't express
-- "row count > 0" — we use an AFTER trigger that re-checks the
-- invariant on token state-change and on TokenSignature delete.
CREATE OR REPLACE FUNCTION enforce_token_has_active_signature()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
DECLARE
    n_active INTEGER;
BEGIN
    SELECT count(*) INTO n_active
    FROM TokenSignature
    WHERE token_id = COALESCE(NEW.token_id, OLD.token_id)
      AND deprecation_date IS NULL;
    IF n_active = 0 THEN
        RAISE EXCEPTION 'Token % has zero active signatures',
            COALESCE(NEW.token_id, OLD.token_id);
    END IF;
    RETURN NEW;
END$$;

CREATE TRIGGER trg_token_must_have_active_signature
    AFTER INSERT OR UPDATE OR DELETE ON TokenSignature
    FOR EACH ROW EXECUTE FUNCTION enforce_token_has_active_signature();

-- TokenSignature is the audit-of-record for migrations: a UC-6 call
-- produces a new row, and the procedure may also UPDATE an existing
-- row to set deprecation_date. This means UPDATEs are NOT entirely
-- forbidden — but they must be confined to setting deprecation_date,
-- and signature_bytes / signed_at / token_id / algorithm_id must be
-- immutable once written. A targeted append-only trigger enforces this:
CREATE OR REPLACE FUNCTION enforce_token_signature_immutability()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    -- DELETE is forbidden outright (would erase the migration record).
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'DELETE on TokenSignature is forbidden (audit-of-record for migrations)'
            USING ERRCODE = 'insufficient_privilege';
    END IF;
    -- UPDATE: only deprecation_date may change; everything else is frozen.
    IF NEW.signature_id   <> OLD.signature_id
       OR NEW.token_id    <> OLD.token_id
       OR NEW.algorithm_id <> OLD.algorithm_id
       OR NEW.signature_bytes <> OLD.signature_bytes
       OR NEW.signed_at   <> OLD.signed_at THEN
        RAISE EXCEPTION
            'TokenSignature is append-only except for deprecation_date'
            USING ERRCODE = 'insufficient_privilege';
    END IF;
    -- deprecation_date is one-way: NULL → timestamp is allowed; un-setting
    -- it (timestamp → NULL) or moving it earlier are forbidden.
    IF OLD.deprecation_date IS NOT NULL THEN
        IF NEW.deprecation_date IS NULL THEN
            RAISE EXCEPTION
                'deprecation_date cannot be un-set once recorded'
                USING ERRCODE = 'insufficient_privilege';
        END IF;
        IF NEW.deprecation_date < OLD.deprecation_date THEN
            RAISE EXCEPTION
                'deprecation_date cannot be moved earlier once recorded'
                USING ERRCODE = 'insufficient_privilege';
        END IF;
    END IF;
    RETURN NEW;
END$$;

CREATE TRIGGER trg_token_signature_immutable
    BEFORE UPDATE OR DELETE ON TokenSignature
    FOR EACH ROW EXECUTE FUNCTION enforce_token_signature_immutability();
```

The append-only trigger does NOT use the shared
`reject_audit_modification` function (which forbids ALL UPDATE/DELETE)
because TokenSignature's deprecation_date is mutable-once. The
narrower trigger enforces the precise invariant: signatures are
written-once, deprecation_date is set-once.

### UC-6 stored procedure update

```sql
CREATE OR REPLACE PROCEDURE uc6_migrate_algorithm(
    p_token_id        INTEGER,
    p_new_algorithm   INTEGER,
    p_new_signature   BYTEA,
    p_deprecate_old   BOOLEAN DEFAULT FALSE
);
```

Behavior: INSERT a new TokenSignature row under the new algorithm.
Optionally set the deprecation_date on the old signature. The old
signature continues to verify until its deprecation_date passes —
this is the migration window.

**Concurrency (C9):** opens with
`pg_advisory_xact_lock(hashtext('polaris.migrate.' || p_token_id))`
so two threads racing the migration of the same token serialize
cleanly. Without this, both threads could pass the
`enforce_token_has_active_signature` AFTER-trigger checks, and a
poorly-ordered deprecation could briefly leave the token with zero
active signatures. The lock is per-token; cross-token migrations
remain parallel. Mirrors the pattern used by `uc8_revoke_token`
(per-agency lock) and `uc9_complete_recovery` (per-individual lock).

The procedure also sets `polaris.actor_agency_id` and
`polaris.reason_code` GUCs. While `uc6_migrate_algorithm` does not
itself change `IdentityToken.status` (so the auto-audit trigger does
not fire), the TokenSignature row's `signed_at` and the append-only
invariant on it together constitute the audit-of-record for the
migration.

### Verification flow change

`app.py` token verification reads:

```sql
SELECT signature_bytes, algorithm_id
FROM TokenSignature
WHERE token_id = %s
  AND (deprecation_date IS NULL OR deprecation_date > CURRENT_TIMESTAMP)
```

Then iterates: try each active signature against the verifier's
expected algorithm; first valid match returns SUCCESS.

### Tests

`MultiSignatureTests` class:

- Token with one signature (legacy case, pre-migration).
- Token with two signatures (during migration window).
- Token with one active + one deprecated (post-migration).
- Token with zero active signatures → triggers the floor exception.
- UC-6 migration: INSERT adds without breaking old.
- UC-6 migration: optional deprecation of old.
- UC-6 migration leaves a TokenSignature row whose `signed_at` and
  immutable `signature_bytes` together are the migration audit.
- Verifying with deprecated algorithm → rejected.
- Verifying with non-deprecated algorithm → accepted.
- All existing v1 tokens have TokenSignature rows after backfill
  (with `BACKFILL_PLACEHOLDER` tag in signature_bytes for test data).
- DELETE on TokenSignature → rejected by the append-only trigger.
- UPDATE to `signature_bytes` / `signed_at` / `token_id` /
  `algorithm_id` → rejected by the append-only trigger.
- UPDATE to set `deprecation_date` (NULL → timestamp) → allowed.
- UPDATE to un-set `deprecation_date` (timestamp → NULL) → rejected.
- UPDATE to move `deprecation_date` earlier → rejected.
- UNIQUE constraint: cannot insert two signatures for same
  (token_id, algorithm_id).
- TokenSignature.deprecation_date is **not** auto-derived from
  CryptographicAlgorithm.deprecation_date. Setting
  CryptographicAlgorithm.deprecation_date does NOT auto-deprecate
  any TokenSignature row; operator policy via UC-6 is the only path.

**Concurrency tests (C9, in `ConcurrencyTests`):**

- **Race two migrations on the same token.** Set up a token with one
  active signature. Spawn `T` threads (T ≥ 4), each calling
  `uc6_migrate_algorithm(token_id, new_algorithm=<distinct per
  thread>, ...)`. Use `concurrent.futures.ThreadPoolExecutor` with
  per-thread psycopg2 connections (no mocks per C9). Expected: the
  advisory lock serializes the calls; final state has the original
  signature plus one new one per thread (T+1 active signatures);
  the `one_signature_per_algorithm_per_token` UNIQUE constraint
  prevents duplicate-algorithm inserts; if any thread tries to
  deprecate the same old sig as another, the later attempt sees the
  already-set `deprecation_date` and the append-only trigger rejects
  the redundant write.

- **Race verification + migration on the same token.** Thread A
  begins a verification (SELECT from TokenSignature with snapshot
  isolation). Thread B simultaneously calls uc6_migrate_algorithm
  setting `deprecation_date` on the old signature. Expected: thread
  A's verification reads its transaction snapshot — the old signature
  appears active *within thread A's read snapshot* even after thread
  B commits the deprecation. This is the documented consistency
  model: a verification transaction is consistent against the
  pre-verification state; migrations that land mid-verification are
  visible only to subsequent transactions. The test asserts this
  semantic explicitly so the behavior is contractually established
  for the verification path.

- **Cross-token migrations run in parallel.** Two threads, two
  different tokens, both calling `uc6_migrate_algorithm`. Both
  succeed in parallel (advisory-lock key is per-token). Assert
  wall-clock time < (single-thread time × 1.5).

## Predicted blast radius

- `polaris_sql/01_schema.sql` — `TokenSignature` table with UNIQUE
  composite key + deprecation_after_signed CHECK (~40 lines).
  Schema goes to 18 tables.
- `polaris_sql/02_indexes.sql` — partial index on `TokenSignature
  (token_id) WHERE deprecation_date IS NULL` for fast active-signature
  lookup during verification (~10 lines).
- `polaris_sql/05_procedures.sql` — `uc6_migrate_algorithm` with
  advisory-lock + audit-GUC setup (~80 lines). Procedure count
  goes to 8.
- `polaris_sql/06_triggers.sql` — `enforce_token_has_active_signature`
  AFTER trigger (~30 lines) + `enforce_token_signature_immutability`
  BEFORE trigger for append-only-ish behavior with one-way
  deprecation_date (~40 lines). Trigger count goes to 9.
- `polaris_sql/04_data.sql` — backfill block: for each existing
  IdentityToken row, INSERT one TokenSignature row with placeholder
  bytes tagged `BACKFILL_PLACEHOLDER` (~40 lines, runs once at load).
- `polaris_sql/08_tests.sql` — section N: 4–5 SQL self-tests for
  the immutability trigger and the UNIQUE composite key (~90 lines).
- `polaris_web/app.py` — verification path reads from TokenSignature
  (~70 lines changed). Dashboard's Post-Quantum panel re-queries
  against the M:N relation (~20 lines).
- `polaris_web/test_app.py` — `MultiSignatureTests` class (~320
  lines, ≥16 tests) + 3 new ConcurrencyTests entries for per-token
  migration race, verify+migrate consistency model, and cross-token
  parallelism (~130 lines).
- `polaris_sql/13_substrate.sql` — extend `SystemDependency` to add
  "multi-signature M:N capability" as a primitive of the
  cryptographic-substrate layer.
- `DEVNOTES/multi-sig-migration.md` (new) — design rationale,
  migration-window semantics, advisory-lock rationale,
  verify+migrate consistency model, no-auto-derivation argument,
  adversary walk, and the issuer-trust-concentration triad
  positioning.
- `DEVNOTES/concurrency.md` — append a "Per-token advisory lock —
  UC-6 / R11-1" section (third entry in the catalog after the
  per-agency UC-8 and per-individual UC-9 patterns).
- `MISSION.md` — mark M2-6 ✅.
- `ROADMAP.md` — mark R11-1 ✅.
- `docs/DATA-MODEL.md` — new `TokenSignature` section + view of
  active-signatures-per-token.
- `docs/API.md` — verification endpoint behavior change (returns
  `algorithm_id` of the signature used).
- `docs/SECURITY.md` — new "Cryptographic Migration (R11-1 / M2-6)"
  section mapping to PDF §9.4 and documenting the
  issuer-trust-concentration triad position.

## Acceptance criteria

- ✅ `TokenSignature` table with UNIQUE composite key + the
  deprecation-after-signed CHECK.
- ✅ `enforce_token_has_active_signature` trigger fires when a
  token would be left with zero active signatures.
- ✅ **`enforce_token_signature_immutability` trigger** rejects
  DELETE outright, rejects UPDATEs to any column other than
  `deprecation_date`, and rejects deprecation_date that's un-set
  (timestamp → NULL) or moved earlier.
- ✅ **`uc6_migrate_algorithm` opens with
  `pg_advisory_xact_lock(hashtext('polaris.migrate.' || p_token_id))`**
  for C9 concurrency correctness. Per-token serialization;
  cross-token migrations run in parallel.
- ✅ **TokenSignature is the audit-of-record for migrations.** Every
  migration event is auditable as a TokenSignature INSERT (and
  optionally an UPDATE setting `deprecation_date` on a prior row),
  retrievable via `SELECT * FROM TokenSignature WHERE token_id=X
  ORDER BY signed_at`. No separate `TokenMigrationEvent` table is
  needed.
- ✅ Backfill: every existing IdentityToken has ≥ 1 TokenSignature
  row with placeholder bytes tagged `BACKFILL_PLACEHOLDER`.
- ✅ UC-6 produces a new signature without deleting the old; the
  migration window is observable as two rows coexisting.
- ✅ Verification accepts ANY non-deprecated signature.
- ✅ Deprecated signatures rejected at verification time.
- ✅ **C7 (algorithm metadata via table) preserved AND strengthened**
  — M:N (TokenSignature) instead of 1:1 (IdentityToken.algorithm_id).
- ✅ **C9 (real-threading concurrency tests) honored** —
  per-token-migration race + verification + migration race tested
  with `threading.Thread` and per-thread psycopg2 connections;
  cross-token parallelism asserted via wall-clock check.
- ✅ C2 (ZK invariant) unaffected; signature is on the token, not on
  the verification event.
- ✅ C10 (identity ≠ money) untouched.
- ✅ ≥ 16 new tests in `MultiSignatureTests` (was ≥11 in the original
  draft; refinements added immutability tests, no-auto-derivation
  test, and audit-via-TokenSignature test) + ≥ 3 new tests in
  `ConcurrencyTests`.
- ✅ `DEVNOTES/multi-sig-migration.md` documents the migration-window
  semantics, the adversary walk, the verify+migrate consistency
  model, the advisory-lock rationale, and the issuer-trust triad
  framing.
- ✅ Dashboard's Post-Quantum panel updated: now shows "tokens with
  ≥ 1 active PQ signature" rather than "tokens with PQ algorithm_id".

## What this is NOT

- **Not Polaris deciding which algorithm to use.** The schema records
  the algorithm a signature was generated under; agencies and the
  jurisdiction's cryptographic authority decide which algorithms are
  credible. Same posture as R11-4 (tiered enrollment vocabulary),
  R11-6 (constitutional limits on issuer discretion), R11-2
  (catastrophic-loss recovery), and the existing C7 constraint.
- **Not auto-derivation of `TokenSignature.deprecation_date` from
  `CryptographicAlgorithm.deprecation_date`.** The two columns serve
  different purposes: `CryptographicAlgorithm.deprecation_date` says
  "this algorithm is end-of-life globally"; `TokenSignature
  .deprecation_date` says "this specific signature is no longer
  accepted." Operator policy (UC-6) drives both, separately.
  Setting `CryptographicAlgorithm.deprecation_date` does not
  cascade into any TokenSignature row. Same anti-auto-derivation
  posture as R11-4 (no auto-derivation of enrollment from token
  state).
- Not actually performing a real cryptanalysis or migration. This
  is the schema and procedure work that makes a future real
  migration tractable.
- Not removing `IdentityToken.algorithm_id`. The column stays as
  "originally issued under" metadata for audit.
- Not multi-party signing (that would be threshold signatures, a
  different problem).
- Not key rotation per se — the keys remain held by the issuer's
  process; only the algorithm choice migrates.
- **Not a `TokenMigrationEvent` audit table.** The TokenSignature
  row itself (with its append-only invariant on
  `signature_bytes`/`signed_at`/etc. and one-way `deprecation_date`)
  IS the migration audit. Adding a parallel event table would
  duplicate state.

## What this needs from you

"Yes do R11-1" plus:

1. **Default algorithm priority order** for verification. When a
   token has two active signatures (ML-DSA-65 and ML-DSA-87), which
   does the verifier prefer? Recommend: highest `algorithm_id` first
   (newer rows are stronger by convention), then `signed_at` desc.
2. **Whether to expose the algorithm-priority to the verifier.**
   Current proposal: verifier specifies expected algorithm OR
   accepts any active. Recommend the latter for v1 (broad
   compatibility).
3. **Backfill strategy for existing sample data.** Recommend
   generating placeholder signatures with a tag like
   `BACKFILL_PLACEHOLDER` so test data is clearly synthetic. Real
   deployment would use actual issuer-signing keys.
