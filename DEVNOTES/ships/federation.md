# DEVNOTES/ships/federation.md

**Introduced:** v8.22 (R11-3 / M2-8). Closes the issuer-trust-concentration
triad to 3/3 (after R11-1 cryptographic diversity ✅ and R11-6 constitutional
limits ✅).

This file is the canonical write-up for Polaris's federation layer: how
cross-agency trust is recorded, how the verification flow consults it, and
what the schema does versus what the operator decides.

---

## What R11-3 implements

PDF §9.2 names "issuer trust concentration" as an open problem the schema
does not yet model. Today, every `IdentityToken` carries an
`issuing_agency_id`, and verification implicitly trusts whichever agency
issued the token. R11-3 replaces "implicit trust" with an explicit,
declarative trust graph:

1. **`AgencyTrustAttestation` table** — directional edges in the
   federation trust graph. Each row says "agency V (attesting) accepts
   agency I (attested) for context C."
2. **`uc10_attest_trust` / `uc10_revoke_attestation`** — admin-only
   procedures under a per-attesting-agency advisory lock (the 5th
   catalog entry).
3. **Verification flow extension** — when a token is presented at a
   verifier, the federation check fires before recording SUCCESS:
   same-agency? implicit trust. Cross-agency? require an active row in
   the trust graph.

## NO transitive trust (R1 audit refinement)

A→B + B→C does NOT imply A→C. The verification check looks for *exactly
one* row in `AgencyTrustAttestation` matching `(attesting=verifier,
attested=issuer, context)`. It never recurses or computes transitive
closure.

This is the anti-auto-derivation principle applied to the trust graph:

- Transitive trust would be silent magic. Adding A→B could grant trust
  paths the operator never intended.
- Cycle handling becomes trivial: no recursion → no cycles to detect at
  verification time.
- Operators who *want* multi-hop trust must declare every edge
  explicitly. The audit trail captures every decision; nothing is
  inferred.

The PDF §9.2 attack this defeats: "the federation collapses into the
most-permissive agency's trust set." With explicit-only federation,
every trust edge is operator-attested, and the graph cannot grow
without explicit action.

## "Schema records, agencies decide" (R2 audit refinement)

When an attestation is revoked, the revocation is recorded in
`AgencyTrustAttestation` (`revocation_date` + `revocation_reason` set
together, both immutable thereafter). The verification path consults
the live state.

The revocation is **forward-looking only**:

- Past `VerificationEvent` rows that occurred while the attestation was
  active are NOT retroactively invalidated. Those events happened; they
  remain in the append-only audit log. C1 (append-only) takes
  precedence — the schema does not rewrite history.
- New verifications after revocation see the revoked state and fail
  the federation check.
- In-flight verifications use READ COMMITTED snapshots: a transaction
  that started before the revocation commit sees the pre-revocation
  state; a transaction starting after sees the post-revocation state.

This matches Polaris's broader posture: revocation is a forward-looking
decision recorded in the audit, not a backwards rewrite.

## Per-attesting-agency advisory-lock (C9, 5th catalog entry)

Both `uc10_attest_trust` and `uc10_revoke_attestation` hold
`pg_advisory_xact_lock(hashtext('polaris.federation.attest.' ||
attesting_agency_id::TEXT))` for the duration of the transaction.

| Procedure | Lock granularity | Cross-key parallelism |
|---|---|---|
| `uc8_revoke_token` | per-agency | cross-agency parallel |
| `uc9_complete_recovery` | per-individual | cross-individual parallel |
| `uc6_migrate_algorithm` | per-token | cross-token parallel |
| `close_anchor_batch` | per-algorithm | cross-algorithm parallel |
| `uc10_attest_trust` / `uc10_revoke_attestation` | per-attesting-agency | cross-attesting-agency parallel |

The lock protects against the attest-revoke race: without it, two
threads on the same agency could attest+revoke in interleaving order
such that the final state is ambiguous. With it, same-agency operations
serialize; cross-agency operations parallelize.

See `DEVNOTES/concurrency.md` "Per-attesting-agency advisory-lock" for
the full discussion.

## v1 = operator-logged; v2 path = agency-signed (R4 audit refinement)

The `signed_by AppUser` field records *which Polaris operator* created
the attestation. It does NOT carry a cryptographic signature from the
attesting agency's signing key.

This is honest, not aspirational:

- `AppUser` doesn't link to `Agency` today. Polaris operators are
  Polaris-operator-role users; they are not jurisdiction operators
  with cryptographic standing.
- The federation model in v1 assumes Polaris is operated by *some*
  authority that has the standing to record attestations on behalf of
  agencies. This is true for a reference implementation; a production
  deployment would need a richer model.

The path to v2 is clean:

```sql
ALTER TABLE AgencyTrustAttestation
    ADD COLUMN attestation_signature BYTEA,
    ADD COLUMN attestation_algorithm_id INTEGER
        REFERENCES CryptographicAlgorithm(algorithm_id);
```

A future migration would add these columns NULLable (existing rows
remain valid). New code paths would require the signature for fresh
attestations; old rows remain queryable in their v1 form. The verifier
would check the signature against the attesting agency's published
public key.

v1 ships without these because the cryptographic surface is the
bottleneck — adding it requires Agency-level signing key management,
which is its own design problem.

## Self-attestation rejected at schema layer (R5 audit refinement)

The CHECK constraint `attestation_no_self_attestation` rejects rows
where `attesting_agency_id = attested_agency_id`.

Alternative considered: allow them and treat them as no-ops at the
verification layer. Rejected because:

- **Noise hides signal.** A trust graph populated with self-attestation
  rows obscures the cross-agency edges that actually matter.
- **Same-agency verification is already implicit.** The verification
  flow's same-agency short-circuit (`token.issuing_agency_id ==
  verifier_agency.agency_id`) handles this without any row. A
  self-attestation row would be either redundant or misleading.
- **Operator error surfaces at INSERT time**, not silently-ignored at
  verification time.

## Seed graph (R6 audit refinement)

Six seed attestations matching the existing demo scenarios:

| # | Attesting | Attested | Context | Why |
|---|---|---|---|---|
| 1 | Agency 4 (TSA federal) | Agency 1 (federal NY issuer) | TRAVEL | James's T3 verifies at TSA |
| 2 | Agency 4 (TSA federal) | Agency 3 (CA issuer) | TRAVEL | Maria's T2 (CA-issued) at TSA |
| 3 | Agency 4 (TSA federal) | Agency 2 (PA issuer) | TRAVEL | Cross-state TRAVEL |
| 4 | Agency 5 (bank) | Agency 1 (federal NY issuer) | BANKING | T3 banking verifications |
| 5 | Agency 5 (bank) | Agency 3 (CA issuer) | BANKING | T2 banking verifications |
| 6 | Agency 5 (bank) | Agency 2 (PA issuer) | BANKING | Cross-state BANKING |

No HEALTHCARE attestations — Maria's T2 is the only token with
HEALTHCARE permissions, and HEALTHCARE verifications happen at
same-agency (CA) checkpoints in the demo data.

This seed makes the existing 8 verification events in sample data
*explicable through the federation graph* rather than implicit
hard-coded trust.

## Future extensions (out of v8.22 scope, but path noted)

### Anchoring attestations themselves

Parallel to R10-2's `committed_to_chain` future-field on `AnchorBatch`:
attestations are high-value cryptographic commitments and could
themselves be batched into a Merkle log for external verifiability.

The path:
- Add `batch_id INTEGER REFERENCES AttestationBatch(batch_id)` to
  `AgencyTrustAttestation` (or extend `AnchorBatch` to carry
  attestation hashes alongside token-anchor hashes).
- Add a `close_attestation_batch` procedure mirroring
  `close_anchor_batch`.
- v1 does NOT ship this; the column-level scaffold is left out
  entirely so the schema doesn't carry placeholders. A future
  increment can add it cleanly because the append-only invariant
  means existing rows are stable across the ALTER TABLE.

### Agency-signed attestations (v2 cryptographic upgrade)

See R4 above. The path is named, the schema is ready, the cryptographic
signing infrastructure is the bottleneck.

### Trust-graph anchoring proofs

A verifier presented with a token from a foreign agency could request a
cryptographic proof that the relevant attestation exists. With v2
agency-signed attestations + Merkle anchoring, this becomes a standard
inclusion-proof flow.

## Flask routes

| Route | Method | Role | Purpose |
|---|---|---|---|
| `POST /api/federation/attest` | POST | admin | Wraps `uc10_attest_trust` |
| `POST /api/federation/revoke` | POST | admin | Wraps `uc10_revoke_attestation` |
| `POST /verifications/new` | POST | admin / operator | Federation check fires on SUCCESS outcome |

The JSON routes accept the CSRF token via the `X-CSRFToken` header (v8.22
added this to `validate_csrf` alongside the existing `csrf_token` form
field, to support AJAX/JSON callers).

## Adversary walk

1. **Defender's claim:** Federation trust is *explicit only* — agency A
   trusts agency B if and only if a row in `AgencyTrustAttestation`
   with status='ACTIVE' exists where `attesting_agency_id=A` and
   `target_agency_id=B`. There is no transitive trust: A→B→C does
   NOT imply A→C. Verification gates SUCCESS outcomes on
   `_federation_trust_holds()` returning true for the (requesting
   agency, issuing agency) pair.
2. **Attacker's optimal response:** Compromise an agency the
   target already trusts directly. The attacker controls that
   agency's signing surface and can issue/attest as them. This
   *is* the original threat from PDF §9's "issuer trust
   concentration" — federation does not eliminate it; federation
   confines the blast radius to exactly the explicitly-trusted set.
3. **Equilibrium:** The defender forces the attacker to compromise
   *each* edge of the trust graph independently. No edge buys the
   attacker any other edge. Compromising N agencies grants
   verification authority over N edges, not over the N-clique
   closure. This is the Schelling-point that PDF §9 names: trust
   concentration is bounded by the count of explicit attestations,
   not the transitive reach.
4. **Second-best attack:** Forge an attestation row directly via
   compromised database access. Defeated by
   `enforce_attestation_immutability` trigger (rejects UPDATE post-
   row; only the canonical procedures `uc10_attest_trust` /
   `uc10_revoke_attestation` can insert/transition state) and by
   the per-attesting-agency advisory lock (5th catalog entry) that
   serializes attestations from a single agency. Tested by
   `ConcurrencyTests.test_uc10_*`. The shell-access pivot still
   bypasses the trigger, but at that point the attacker has root
   and federation is the least of the defender's problems.
5. **Defender's cost:** Explicit-only trust means new federation
   relationships require an explicit attestation per pair — N agencies
   wanting full pairwise trust pay O(N²) attestations. Accepted: this
   is the *correct* trade for the threat model. A future
   "trust group" abstraction (Sanctum-class) could amortize the cost
   without weakening the no-transitivity invariant.
6. **Mechanism-design note:** The schema records *facts* (this
   agency attests this target); agencies *decide* what to do with
   those facts. Polaris does not arbitrate trust policy beyond
   refusing to assume relationships agencies haven't declared. This
   is the same boundary discipline as C10 (identity ≠ money):
   Polaris answers "did A attest B?", not "should A trust B?".

## Cross-references

- `polaris_sql/01_schema.sql` — `AgencyTrustAttestation` table + 3 CHECK constraints.
- `polaris_sql/02_indexes.sql` — `uq_active_attestation` partial unique index + `idx_attestation_revoked`.
- `polaris_sql/05_procedures.sql` — `uc10_attest_trust` and `uc10_revoke_attestation`.
- `polaris_sql/06_triggers.sql` — `enforce_attestation_immutability`.
- `polaris_sql/08_tests.sql` — Section P (5 self-tests).
- `polaris_sql/10_auth.sql` — 6-row seed graph.
- `polaris_web/app.py` — `_federation_trust_holds()` helper +
  `verifications_new` extension + `/api/federation/*` routes.
- `polaris_web/test_app.py` — `IssuerFederationTests` (15 tests) +
  `ConcurrencyTests.test_uc10_*` (2 tests).
- `DEVNOTES/audit-of-record.md` — `AgencyTrustAttestation` is the 6th instance.
- `DEVNOTES/concurrency.md` — per-attesting-agency advisory-lock is the 5th catalog entry.
- `MISSION.md` — M2-8 marked ✅ in the v2 done-list.
- `sanctum/2026-05-11-r11-3-issuer-federation.md` — the consultation that authorized this work.
- `proposals/R11-3-issuer-federation.md` — the audited proposal.
