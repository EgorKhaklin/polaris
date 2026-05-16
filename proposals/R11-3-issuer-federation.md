# proposals/R11-3-issuer-federation.md

**Risk class:** HIGH (explicit-approval-required; verification-flow change + cross-jurisdiction surface)
**Mission link:** v2 M2-8 (open problems — issuer trust concentration / federation)
**Status:** PROPOSED, awaiting VANTA approval
**Effort:** ~3 sessions
**Architect ID:** arch-2026-05-11-001 (from the brief opening this round)

## Problem (PDF §9.2)

Today, every `IdentityToken` carries an `issuing_agency_id`. Verification
implicitly trusts whatever agency issued the token — there is no
mechanism for one agency to declare which other agencies' tokens it
accepts. Three consequences follow:

1. **Issuer trust concentration.** A nation-scale system that runs on a
   single trusted issuer is a single point of failure (political,
   technical, and adversarial). The PDF names this as the open problem
   the schema does not yet model.
2. **Brittle multi-jurisdiction operation.** A token issued by
   California's DMV (Agency 3) operating at a federal TSA checkpoint
   (Agency 4) currently works only because the seed data hard-codes the
   trust. There is no schema-level expression of "Agency 4 accepts
   Agency 3's TRAVEL tokens." If a third agency comes online tomorrow,
   nothing in the schema captures whether existing verifiers should
   accept its tokens.
3. **No revocation pathway for trust itself.** If Agency 3's signing
   keys were compromised, today the only response is `RevocationList`
   per-token. There is no mechanism for verifying agencies to
   collectively say "stop trusting Agency 3 in TRAVEL contexts" without
   touching every token Agency 3 ever issued.

## Triad closure

The issuer-trust-concentration triad spans three independent
mitigations:

| Leg | Item | Status |
|---|---|---|
| Cryptographic diversity (multi-signature transitional state) | M2-6 / R11-1 | ✅ v8.18 |
| Constitutional limits (issuer-discretion bounds) | M2-11 / R11-6 | ✅ v8.15 |
| **Federation (trust attestation graph)** | **M2-8 / R11-3** | ⬜ this proposal |

R11-3 closes the triad to 3/3. After this ships, every leg of the
"no single trusted issuer" claim is structurally grounded.

## Why HIGH

The verification flow is the hottest path in Polaris — touched by every
UC, every atlas event, every external verifier. R11-3 changes the
"who do we trust" decision-procedure in that path. Bugs here are
high-blast-radius:

- A false-positive (accepting a token whose issuer is not trusted) is a
  spoofing vulnerability.
- A false-negative (rejecting a token whose issuer IS trusted) breaks
  every cross-jurisdiction verification — a denial-of-service against
  legitimate holders.
- The schema introduces a graph (the trust-attestation relation), and
  graph reasoning has non-obvious correctness bugs (cycles, transitive
  trust, revocation propagation).
- Cross-jurisdiction trust is a sociopolitical surface. A poorly-named
  field or a too-permissive default could embed an opinion about
  sovereignty.

LOW or MEDIUM would be wrong because the verification flow change is
load-bearing for C1 (audit), C2 (ZK disclosure), and C6 (server-side
disclosure enforcement).

## Schema

```sql
CREATE TABLE AgencyTrustAttestation (
    attestation_id        SERIAL       PRIMARY KEY,
    attesting_agency_id   INTEGER      NOT NULL
                          REFERENCES Agency(agency_id),
    attested_agency_id    INTEGER      NOT NULL
                          REFERENCES Agency(agency_id),
    context_id            INTEGER      NOT NULL
                          REFERENCES VerificationContext(context_id),
    attested_date         TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    valid_until           DATE         NOT NULL,
    signed_by             INTEGER      NOT NULL
                          REFERENCES AppUser(user_id),
    revocation_date       TIMESTAMP,
    revocation_reason     VARCHAR(80),

    CONSTRAINT attestation_no_self_attestation CHECK (
        attesting_agency_id <> attested_agency_id
    ),

    CONSTRAINT attestation_validity_floor CHECK (
        valid_until > attested_date::DATE
    ),

    CONSTRAINT attestation_revocation_consistency CHECK (
        (revocation_date IS NULL  AND revocation_reason IS NULL) OR
        (revocation_date IS NOT NULL AND revocation_reason IS NOT NULL
         AND char_length(revocation_reason) >= 8)
    )
);

-- Per-direction unique within active window (attestation_id is the
-- audit handle; this prevents duplicate concurrent attestations for
-- the same (attesting, attested, context) triple).
CREATE UNIQUE INDEX uq_active_attestation
    ON AgencyTrustAttestation (attesting_agency_id, attested_agency_id, context_id)
    WHERE revocation_date IS NULL;
```

Three CHECK constraints worth highlighting:

1. **No self-attestation.** An agency trivially trusts its own tokens
   (the same-agency verification path). The schema rejects rows where
   `attesting_agency_id = attested_agency_id` because they would be
   noise — they neither enable nor restrict anything.
2. **Validity floor.** `valid_until` must be strictly after
   `attested_date`. A zero-or-negative-duration attestation has no
   effect and is operator error.
3. **Revocation consistency.** Mirrors the audit-of-record bounded-
   mutation pattern from `TokenSignature.deprecation_date` — once
   `revocation_date` is set, both fields must move together, and the
   reason must be ≥ 8 chars (forces operators to write *why*, not
   just *that*).

## Procedures

### `uc10_attest_trust(attesting_id, attested_id, context_id, valid_until, signed_by)`

Creates a new attestation under a per-attesting-agency advisory lock
(the 5th catalog entry):

```sql
PERFORM pg_advisory_xact_lock(
    hashtext('polaris.federation.attest.' || p_attesting_id::TEXT));
```

Validates:
- Both agencies exist
- Context exists
- No active attestation already exists for this (attesting, attested,
  context) triple (the partial unique index enforces this; the
  procedure surfaces a readable error)
- `signed_by` is an admin (operator role isn't sufficient for trust
  decisions)

### `uc10_revoke_attestation(attestation_id, revocation_reason, signed_by)`

Sets `revocation_date` and `revocation_reason` under the same per-
attesting-agency advisory lock. The one-way mutation is enforced by a
trigger (next section).

## Triggers

### `enforce_attestation_immutability`

Mirrors `enforce_token_signature_immutability`. Rejects any UPDATE
that touches a column other than `(revocation_date, revocation_reason)`
on `AgencyTrustAttestation`. Rejects any UPDATE where
`revocation_date` is transitioning from non-NULL to NULL (one-way).
DELETE is always rejected.

This makes `AgencyTrustAttestation` the **6th audit-of-record
instance** in Polaris.

## Verification flow change

The verification path's trust check today:

```python
# Today (simplified)
def is_token_valid_for_verification(token, verifier_agency):
    return token.status == 'ACTIVE' and \
           token.signature_verifies() and \
           verifier_agency.has_permission(token.context)
```

After R11-3:

```python
# After
def is_token_valid_for_verification(token, verifier_agency, context):
    if token.status != 'ACTIVE': return False
    if not token.signature_verifies(): return False
    if not verifier_agency.has_permission(context): return False

    # Federation check
    if token.issuing_agency_id == verifier_agency.agency_id:
        return True  # same-agency trust is implicit
    return _has_active_attestation(
        attesting=verifier_agency.agency_id,
        attested=token.issuing_agency_id,
        context=context,
    )
```

`_has_active_attestation` consults `AgencyTrustAttestation` for an
unrevoked, unexpired row. A SQL function or a join in the existing
verification view (TBD by alignment audit).

## Acceptance

1. Schema: `AgencyTrustAttestation` + partial unique index + 3 CHECK
   constraints + 1 trigger
2. Procedures: `uc10_attest_trust`, `uc10_revoke_attestation` (per-
   attesting-agency advisory lock; admin-role-required)
3. Verification flow change in `verifications_new` route and
   `verify_token()` helper
4. Sample data: 3 attestations seeding the existing agency graph
5. SQL self-tests section P (≥4 tests)
6. Python tests: `IssuerFederationTests` (≥15 tests):
   - same-agency trust passes without attestation
   - cross-agency trust requires attestation
   - revoked attestation breaks verification (forward-looking only)
   - past `VerificationEvent` rows survive revocation (audit
     integrity)
   - expired attestation breaks verification
   - cross-context (A→B for TRAVEL does not authorize BANKING)
   - mutual recognition (A↔B as two separate rows) works
   - **transitive trust rejected** (A→B + B→C does NOT grant A→C —
     R1 audit refinement)
   - self-attestation rejected at schema layer (R5 audit refinement)
   - non-admin attestation attempt rejected
   - zero-duration attestation rejected at schema layer
   - revocation reason floor (< 8 chars) rejected at schema layer
   - one-way revocation: cannot UN-revoke (NULL ← timestamp blocked)
   - 2 ConcurrencyTests: same-attesting-agency parallel attests
     serialize; cross-attesting-agency parallel attests parallelize
     (the 5th advisory-lock pair)
7. DEVNOTES/federation.md (new) — the canonical write-up
8. DEVNOTES/audit-of-record.md extended to 6 instances
9. DEVNOTES/concurrency.md extended to 5 advisory-lock entries
10. MISSION M2-8 ✅; ROADMAP R11-3 ✅; CHANGELOG v8.22 entry
11. Counts sweep

## Audit refinements (folded in, 2026-05-11)

Following the audit-then-Sanctum pattern from R11-6 / R11-1 / R10-2,
six substantive refinements were surfaced and folded in before
Sanctum entry:

### R1. NO transitive trust at the schema level

If A→B and B→C exist, A does NOT implicitly trust C. The verification
check looks for *exactly one* row in `AgencyTrustAttestation` matching
`(attesting=verifier, attested=issuer, context)`; it does NOT recurse
or compute transitive closure. This is the anti-auto-derivation
principle applied to trust:

- Transitive trust would be silent magic — adding A→B could silently
  grant trust paths the operator didn't intend.
- Cycle detection becomes trivial (no recursion = no cycles to
  detect at verification time).
- Operators who *want* multi-hop trust must declare it explicitly
  with separate rows.

The PDF §9.2 anti-pattern this defeats: "the federation collapses
into the most-permissive agency's trust set." With explicit-only
federation, every trust edge is operator-attested.

### R2. "Schema records, agencies decide" framing for revocation

When attestation A→B is revoked:
- The revocation is recorded in `AgencyTrustAttestation`
  (`revocation_date` + `revocation_reason` set).
- **No retroactive invalidation** of past `VerificationEvent` rows.
  Those events happened; they remain in the append-only audit log.
- New verifications after revocation see the revoked state via the
  partial unique index `WHERE revocation_date IS NULL`.
- In-flight verifications use READ COMMITTED snapshots: a transaction
  that started before the revocation commit sees the pre-revocation
  state; a transaction starting after sees the post-revocation state.

This matches the established Polaris posture: the schema does not
re-write history. Revocation is a forward-looking decision recorded
in the audit, not a backwards rewrite.

### R3. Attestations as candidate AnchorBatch leaves (future-field)

Just as R10-2 added `committed_to_chain` as an operator-set
future-field on `AnchorBatch`, R11-3 leaves a future-field path for
anchoring attestations themselves:

- Today: `AgencyTrustAttestation` is the relational audit-of-record
  for federation decisions.
- Future: a separate batch table (`AttestationBatch`) or an extension
  to `AnchorBatch` could commit attestation hashes to the Merkle log.
- v1 does NOT ship this; the column-level scaffold is left out
  entirely (no `batch_id` field). A future increment can add it
  cleanly because the schema's append-only invariant means existing
  rows are stable.

Recorded in `DEVNOTES/federation.md`'s "Future extensions" section
so the upgrade path is visible.

### R4. v1 federation is operator-logged, not agency-signed

The `signed_by AppUser` field records which operator created the
attestation. It does NOT carry a cryptographic signature from the
attesting agency's signing key. This is honest, not aspirational:

- AppUser doesn't link to Agency today; operators are Polaris
  operators, not jurisdiction operators.
- A v2 federation extension would add `attestation_signature BYTEA`
  + an FK to `CryptographicAlgorithm`, allowing the attesting agency
  to sign the (attesting, attested, context, valid_until) tuple with
  its own key. The verifier could then check the signature against
  the agency's published public key.
- v1 ships without this and names the limitation. The substitution
  is local — adding the column doesn't break existing rows because
  the column would be NULLable until a future migration window.

The DEVNOTES/federation.md write-up calls this out as the canonical
v1/v2 split.

### R5. Self-attestation rejected at schema layer (not no-op)

The CHECK constraint `attestation_no_self_attestation` rejects rows
where `attesting_agency_id = attested_agency_id`. Alternative
considered: allow them and treat them as no-ops at the verification
layer. Rejected because:

- Noise hides signal. A trust graph populated with self-attestation
  rows obscures the cross-agency edges that actually matter.
- Same-agency verification is already implicit in the verification
  flow (the `token.issuing_agency_id == verifier_agency.agency_id`
  short-circuit). A self-attestation row would be either redundant
  (same outcome as the short-circuit) or *misleading* (suggesting
  that absence of a self-attestation row breaks same-agency
  verification — it doesn't).
- Operator error surfaces immediately at INSERT time, not
  silently-ignored at verification time.

### R6. Concrete seed attestation graph

Six seed attestations matching the existing demo scenarios:

| # | Attesting | Attested | Context | Why |
|---|---|---|---|---|
| 1 | Agency 4 (TSA federal) | Agency 1 (federal NY issuer) | TRAVEL | James's T3 already verifies at TSA |
| 2 | Agency 4 (TSA federal) | Agency 3 (CA issuer) | TRAVEL | Maria's T2 (CA-issued) operating in federal context |
| 3 | Agency 4 (TSA federal) | Agency 2 (PA issuer) | TRAVEL | Cross-state TRAVEL: PA-issued at TSA |
| 4 | Agency 5 (bank) | Agency 1 (federal NY issuer) | BANKING | T3 banking verifications |
| 5 | Agency 5 (bank) | Agency 3 (CA issuer) | BANKING | T2 banking verifications |
| 6 | Agency 5 (bank) | Agency 2 (PA issuer) | BANKING | Cross-state BANKING |

No HEALTHCARE attestations seeded — Maria's T2 is the only token
with HEALTHCARE permissions, and her issuing agency is also her
verifying agency for that context (so same-agency implicit trust
applies).

This seed makes the existing 8 verification events in sample data
*explicable through the federation graph* rather than implicit
hard-coded trust.

## Audit-of-record + advisory-lock catalog growth

After R11-3 ships:
- **6 audit-of-record instances** (TokenLifecycleEvent,
  RecoveryRequest, TokenSignature, AnchorBatch, Sanctum sessions,
  **+AgencyTrustAttestation**)
- **5 per-entity advisory-lock granularities** (per-agency for
  revocation, per-individual for recovery, per-token for migration,
  per-algorithm for anchor-batch close, **+per-attesting-agency for
  federation**)

## Blast radius

- Schema: +1 table, +1 partial unique index, +3 CHECK constraints, +1 trigger
- Procedures: +2 (uc10_attest_trust, uc10_revoke_attestation)
- Verification path: 1 helper function added; existing
  `verifications_new` extended
- New routes: optionally `/api/federation/attest` (admin) +
  `/api/federation/revoke` (admin); v1 ships routes for parity with
  R10-2's `/api/anchor/*` endpoints
- Tests: +15 Python tests, +2 concurrency tests, +5 SQL self-tests
  (section P)
- DEVNOTES: 1 new file (`federation.md`), 2 extended
  (`audit-of-record.md`, `concurrency.md`)
- Counts: +1 table (19 → 20); +2 procedures (9 → 11); +1 trigger;
  +1 audit-of-record instance (5 → 6); +1 advisory-lock entry (4 → 5)

## Pre-Sanctum sanity checklist

| Check | Status |
|---|---|
| C9 advisory-lock named (per-attesting-agency) | ✅ |
| "Schema records, agencies decide" framing | ✅ R2 |
| Append-only / audit-of-record applied | ✅ 6th instance |
| Anti-auto-derivation explicit (no transitive trust) | ✅ R1 |
| Future-fields path noted, not wired (operator-signed, anchored) | ✅ R3, R4 |
| Concurrency contract (5th lock pair) tested | ✅ |
| Seed data populates the new graph | ✅ R6 |
| HIGH-risk: triad-closing leg explicit | ✅ |
| Documentation: DEVNOTES + audit-of-record + concurrency updates planned | ✅ |
