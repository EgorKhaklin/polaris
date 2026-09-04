# Issuer discretion

**Reader:** an engineer or an assessor. **Job:** The limits on what an issuing agency can do at scale, and where they bind.

---

## What this is

A schema-level cap on how fast a single issuing agency can revoke its own
tokens. Above the cap, a co-signer from a different agency holding `BOTH`
on the token's algorithm is required. The cap is per-agency and rolling.

The PDF's §9 "Issuer trust concentration" names three production-system
requirements: cryptographic diversity, federation, and
*constitutional limits on issuer discretion*. is the third leg.

## What it is NOT is **not** Polaris becoming an authority over the holder. The
agency still makes the revocation decision. Polaris only constrains the
*shape* of agency behavior — the same category as C3 (one ACTIVE per
individual: a constraint on issuance behavior) and C7 (algorithm
metadata via table: a constraint on what an agency may sign with).

## N and W: the policy choices

System defaults:

| Knob | Default | Rationale |
|---|---|---|
| `polaris.default_max_revoke_percent` | **5.00** | Caps a single agency at ~60% of its outstanding population per year if revocations are spread evenly. Below this, denaturalization-style mass revocation is impossible without co-sign; at this level, slow long-tail abuse is still operationally observable through audit. |
| `polaris.default_window_days` | **30** | Matches monthly operational reporting cadence. A 30-day rolling window is short enough to catch a coordinated mass-revocation campaign within useful time horizon, long enough to absorb legitimate-but-bursty hardware recall workflows. |

Per-agency overrides live in `IssuerDiscretionPolicy`. Absence of a row
inherits the system default. The sample data ships with two overrides
demonstrating both directions:

- Agency 1 (US National Identity Service, FEDERAL) → 7.00% / 30d, looser
  to accommodate coordinated federal-scale hardware recall workflows.
- Agency 6 (Allegheny County Health Auth., COUNTY) → 3.00% / 30d,
  tighter as a defense-in-depth measure against sub-state mass action.

Tuning is operator policy. The `justification` field has a 20-character
length floor so any loosening is auditable from the row alone.

## Co-signer eligibility

A co-signer must:

1. Differ from the actor agency.
2. Hold `BOTH` authorization on the token's algorithm (via
   `AgencyAlgorithmAuth`).

This is *broader* than naming a single fixed co-signer authority. The
second-best attack (after the rate-limit equilibrium holds) is to
compromise the co-signer. A *set* of eligible co-signers means an
attacker must compromise *all* candidate co-signers, which scales
poorly. The co-signer's identity is recorded in the lifecycle event's
`reason_code` as `[COSIGN:<agency_id>]` — a third-party auditor can
detect a single co-signer appearing repeatedly across mass-revocation
events.

## Advisory-lock rationale (C9)

The procedure opens with:

```sql
PERFORM pg_advisory_xact_lock(
    hashtext('polaris.revoke.' ||
        (SELECT issuing_agency_id::TEXT FROM IdentityToken WHERE token_id = p_token_id)));
```

This serializes concurrent revocations *by the same agency* so the
read-then-write rate check is atomic. Two threads racing the (N+1)th
revocation block each other on this lock; the loser sees the winner's
row when its rate read runs and gets the bound-exceeded error.

Chosen over alternatives:

- **`SERIALIZABLE` isolation:** would require application-side retry
  logic on serialization failures (40001 errcode). The advisory lock
  keeps the rest of the schema in READ COMMITTED.
- **`SELECT … FOR UPDATE` on a row:** there is no single row to lock —
  the rate query joins TokenLifecycleEvent ⨝ IdentityToken across many
  rows. An advisory lock on a derived key (the agency id) is the
  natural granularity.
- **A global lock:** would block cross-agency revocations needlessly.
  The current key is `hashtext('polaris.revoke.' || agency_id)`, so two
  different agencies do not serialize. `ConcurrencyTests
  .test_uc8_cross_agency_revocations_do_not_block` asserts this.

The lock is transaction-scoped (`_xact_` in the function name) — it
releases automatically at COMMIT or ROLLBACK with no application-side
unlock required.

## RevocationList integration

`uc8_revoke_token` mirrors the UC-4 pattern: it updates
`IdentityToken.status='REVOKED'` *and* inserts into `RevocationList` in
the same transaction. Without the CRL row, verifier-side freshness
checks would not see the revocation; the token state would diverge
from the published CRL.

The `RevocationList.reason_code` column is `VARCHAR(40)` with a CHECK
constraint over the canonical vocabulary
(`COMPROMISED`/`LOST`/`STOLEN`/`SUPERSEDED`/`ADMINISTRATIVE`/`DEATH`).
The co-signer tag lives in the lifecycle event's `reason_code` only,
which is `VARCHAR(60)` and not domain-checked. This keeps the
verifier-facing CRL canonical while the audit trail carries the
procedural metadata.

## Belt-and-suspenders trigger

`enforce_revocation_velocity_bound` is a BEFORE-UPDATE trigger on
`IdentityToken.status`. It refuses any UPDATE that transitions a token
to `REVOKED` unless the per-transaction GUC `polaris.revoke_check_done`
was set by `uc8_revoke_token`.

The trigger does NOT re-do the rate math. Its job is to make
`uc8_revoke_token` the *only* path. Direct UPDATEs from `psql`, the
SQL Console, or app code that bypassed the procedure all get rejected
with an `insufficient_privilege` error.

## Adversary walk

1. **Defender's claim:** No single agency can revoke more than N% of
   its outstanding issued tokens in any W-day window without a
   higher-authority co-signer.
2. **Attacker's optimal response:** Spread revocations evenly to stay
   just under N% per window indefinitely. At N=5% / W=30 days, an
   agency can still revoke ~60% of its outstanding population per year
   slowly. The bound shifts the attack from a surprise to an
   observable trend.
3. **Equilibrium:** Mass revocation requires either co-sign (traceable
   to two agencies, not one) or rate-limited slow-burn (catchable by
   downstream audit and reporting before completion).
4. **Second-best attack:** Compromise the co-signer. Mitigated by
   making co-signer eligibility a *set* (any BOTH agency ≠ actor) and
   recording the co-signer in the audit row so repeated patterns are
   detectable.
5. **Defender's cost:** The bound can reject legitimate bulk
   revocations (e.g., a coordinated hardware recall). Mitigated by
   per-agency policy override (`IssuerDiscretionPolicy`) and by the
   co-signer escape hatch.
6. **Mechanism-design note:** N and W are Schelling-point choices.
   Lower N or shorter W = stronger bound but more friction on
   legitimate workflows. The chosen defaults (5% / 30 days) prioritize
   denaturalization resistance over operational latitude.

## What does NOT protect against

- **Slow long-tail abuse** under the bound. An agency that revokes
  4.99% / month for a year still gets ~60%. Counter-mechanism: audit
  reporting + civic surveillance of revocation rates, not the schema.
- **System-wide collusion** (every agency captured). The schema's
  leverage ends when every authorized signer is compromised.
- **`LOST` and `EXPIRED` events.** These are individual-scale
  lifecycle transitions, not bulk operational ones. If a real abuse
  pattern emerged using `LOST` as a laundered revocation, a follow-up
  would extend the bound there.
- **Cryptographic forgery** of the co-signer's identity. v1 records
  the co-signer procedurally, not cryptographically. R12+ can layer
  hardware-attested signing on top.

## Cross-references

- `meta/redaction-proof.md` —, the other PDF §9 leg already
  closed (verification-graph redaction proof).
- `proposals/-multisig-transitional.md` —, the
  cryptographic-diversity leg.
- The PDF, §9 "Issuer trust concentration" — original problem
  statement.
- `docs/design/concurrency.md` — the advisory-lock pattern added to the
  catalog there.
- `MISSION.md` — C5 (audit-trail completeness) and C7 (algorithm
  metadata via table) are the constraints strengthens.
