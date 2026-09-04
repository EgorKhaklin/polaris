# The recovery ceremony

**Reader:** an engineer or an assessor. **Job:** How a holder recovers an identity without a single point of compromise.

---

## What this is

The third leg of the **"schema doesn't weaponize itself against the
holder"** triad: a structural defense against permanent civic
exclusion after catastrophic token loss.

| Leg | Threat blocked | Item | Status |
|---|---|---|---|
| Entry | Forced non-enrollment as exclusion gradient | | ✅ v8.16 |
| Exit | Mass denaturalization without co-signature | | ✅ v8.15 |
| **Recovery** | **Catastrophic loss → permanent exclusion** | **** | **✅ v8.17** |

The PDF §9.1 phrase the proposal anchors against:

> *"Catastrophic-loss risk. Reserve tokens and device bindings
> mitigate single-token loss, but a catastrophic event that destroys
> all of a holder's tokens and devices simultaneously (fire, theft,
> flood affecting both primary wallet and reserve storage) still
> leaves the holder without civic identity until reissuance. A
> production system would require a recovery protocol involving the
> issuing agency and out-of-band identity verification, with a
> defined grace period during which the holder retains access to
> essential services."*

## What this is NOT is **not Polaris deciding who deserves recovery.** The four
`CHECK` constraints on `RecoveryRequest` constrain the *shape* of
the decision; the agencies and out-of-band verification processes
make the decision. Same posture as C3 (one ACTIVE per individual:
constraint on issuance behavior, not a holder verdict), C7
(algorithm metadata: constraint on what agencies may sign with), (issuer-discretion bounds: constraint on revocation velocity),
and (tiered enrollment vocabulary: constraint on how
non-enrollment is recorded).

## The two-phase ceremony

### Phase 1 — `uc9_initiate_recovery`

Operator role required. INSERTs a `PENDING` row. Does NOT issue
a token. The 48-hour cool-down clock starts here.

Rejects:

1. If the individual already holds an `ACTIVE` token (UC-4 reserve
   activation is the right path for partial loss).
2. If a `PENDING` recovery already exists for this individual (the
   partial unique index `uq_one_pending_recovery_per_individual`
   would also catch this; the procedure rejects first for a clearer
   error message).

Out-of-band verification of the three channels (biometric, sworn
statement, witness agency) happens between phase 1 and phase 2 in
the real world. For tests we shortcut by inserting rows with
channels already filled.

### Phase 2 — `uc9_complete_recovery`

**Admin role required.** Belt-and-suspenders enforcement:
`@security.require_role('admin')` at the Flask route AND a
`RAISE EXCEPTION` inside the procedure if the deciding user's
`AppUser.role` is not `'admin'`. Operator can initiate (phase 1)
but cannot complete (phase 2); auditor is read-only.

Steps:

1. `pg_advisory_xact_lock(hashtext('polaris.recovery.' ||
   claimed_individual_id::TEXT))` — C9 correctness; serializes
   concurrent completions for the same individual.
2. Validate deciding user holds `admin` role.
3. `SELECT … FOR UPDATE` on the `RecoveryRequest` row; check it's
   still `PENDING`.
4. Validate `decided_by_user_id != requesting_user_id` (also
   schema CHECK).
5. If `APPROVED`:
   a. Verify cool-down expired (also schema CHECK).
   b. Verify all three OOB channels (also schema CHECK).
   c. Validate new-token parameters.
   d. Set `polaris.actor_agency_id` + `polaris.reason_code='LOST_BY_RECOVERY
      [RECOVERY:<id>]'`. UPDATE every non-terminal token of the
      individual to `status='LOST'`. The auto-audit trigger emits
      a tagged lifecycle event. **Each LOST token also INSERTs to
      `RevocationList`** (UC-4 pattern; without this, verifier-side
      freshness checks would not see the revocation).
   e. INSERT the new IdentityToken as RESERVE (state-machine trigger
      only allows RESERVE → ACTIVE) with `predecessor_token_id=NULL`
      (the prior chain was lost — distinct from UC-4's reserve
      activation, which DOES set predecessor).
   f. Set `polaris.reason_code='RECOVERY_ISSUED [RECOVERY:<id>]'`.
      UPDATE the new token to ACTIVE. The auto-audit trigger emits
      a tagged lifecycle event.
   g. UPDATE the `RecoveryRequest` row to APPROVED with
      `decided_at`, `decided_by_user_id`, `resulting_token_id`.
6. If `REJECTED`: just UPDATE the `RecoveryRequest` row to REJECTED.
   No token issuance, no RevocationList writes.

## Audit-row tagging

Every transition during APPROVED recovery is tagged with
`[RECOVERY:<recovery_id>]` in the lifecycle event's `reason_code`:

| Event type | Token | reason_code format |
|---|---|---|
| `LOST` | old tokens being abandoned | `LOST_BY_RECOVERY [RECOVERY:<id>]` |
| `ACTIVATED` (or whatever the state-machine emits for RESERVE→ACTIVE) | new token | `RECOVERY_ISSUED [RECOVERY:<id>]` |

Audit replay can reconstruct the full recovery context from the
lifecycle log alone — the tag is the join key back to the
`RecoveryRequest` row that drove the transition.

## Adversary walk

1. **Defender's claim:** Recovery requires successful verification
   through THREE independent out-of-band channels (biometric, sworn
   statement, witness agency co-sign).
2. **Attacker's optimal response:** Compromise one of the three
   channels and bet on procedural laxity.
3. **Equilibrium:** Triple-channel commitment. To succeed, the
   attacker must compromise ALL THREE channels simultaneously —
   these are designed to be governed by independent failure modes
   (biometric is local hardware + person; sworn statement is
   legal + paper; witness agency is institutional).
4. **Second-best attack:** Compromise just enough OOB verification
   to slip past a tired admin. Defended by:
   - Mandatory 48-hour cool-down between phase 1 and phase 2.
   - Admin role required for phase 2 (operator alone cannot
     complete; two-operator collusion fails at the role gate).
   - Approver ≠ requester (both schema CHECK and procedure check).
   - `RecoveryRequest` row is queryable in real time by other
     admins (`/uc9/queue`), so a suspicious pattern is visible
     before the decision lands.
5. **Defender's cost:** Legitimate recovery takes ≥48 hours; the
   holder is civically dark during this window (until v2 lands
   the operational `TemporaryAttestation`). This is a real cost
   that operators may want to weight against the bound. A future
   `RecoveryDiscretionPolicy` table could allow per-jurisdiction
   tuning, mirroring's `IssuerDiscretionPolicy`.
6. **Mechanism-design note:** Triple-channel + cool-down + admin
   co-sign shifts attacker cost from "fake one signature" to
   "compromise three channels AND defeat the cool-down AND get an
   admin to sign." **Multiplicative cost, not additive.**

## Administrative cool-down vs operational grace period

The PDF §9.1 phrase *"a defined grace period during which the
holder retains access to essential services"* admits two readings:

1. **Administrative grace period** — a procedural window during
   which the recovery request is processed (no premature approval).
   The proposal's 48-hour `cooldown_expires_at >= requested_at +
   INTERVAL '48 hours'` CHECK enforces this.

2. **Operational grace period** — a substitute civic-access
   credential (a temporary attestation enabling continued use of
   essential services *during PENDING*) so the holder is not
   civically dark while their recovery is processed.

**v8.17 implements (1).** The operational version (2) is deferred
to a follow-up because it requires verifier-side integration that
downstream services would accept as a temporary credential. The
schema would need a `TemporaryAttestation` table with a strict
expiration tied to `cooldown_expires_at`, plus a verifier-side
acceptance rule scoped to a flagged "essential services" context.

When (2) lands it should be additive: a child row on the PENDING
`RecoveryRequest`, with the attestation lifetime equal to the
cool-down window. The schema is forward-compatible.

## What breaks if any CHECK is removed

- **Remove `cooldown_window_minimum`** → recoveries can be
  approved instantly, no time for civic awareness or for the
  claimed holder to discover and abort an impersonation attempt.
- **Remove `approved_requires_three_channels`** → APPROVED status
  no longer guarantees that all three OOB channels were verified;
  single-channel compromise becomes sufficient.
- **Remove `approved_after_cooldown`** → procedural cool-down can
  be bypassed by setting `decided_at` before `cooldown_expires_at`.
- **Remove `approver_differs_from_requester`** → a single user can
  initiate and self-approve, collapsing the two-operator separation
  the ceremony depends on.

Each CHECK is load-bearing. None can be relaxed without weakening
the ceremony's mechanism.

## Concurrency: the per-individual advisory lock

The `pg_advisory_xact_lock` pattern follows's per-agency lock
shape. Two threads calling `uc9_complete_recovery(recovery_id=X)`
on the same PENDING request would each pass the cool-down +
three-channel CHECKs before either UPDATE landed. The first to
acquire the lock commits; the second sees the post-commit `APPROVED`
state and refuses ("not PENDING").

Lock key: `hashtext('polaris.recovery.' || claimed_individual_id)`.
Per-individual, transaction-scoped. Cross-individual recoveries
remain parallel. Test `ConcurrencyTests
.test_uc9_advisory_lock_serializes_concurrent_completes` exercises
the race with real `psycopg2` threads (C9 honored).

## Cross-references

- PDF §9.1 "Catastrophic-loss risk" — original problem statement.
- `MISSION.md` *Polaris is NOT an authority* — the constraint calibrates against.
- `proposals/-catastrophic-loss-recovery.md` — original
  proposal with the alignment-audit refinements.
- `docs/design/issuer-discretion.md` — (exit leg, same
  advisory-lock pattern).
- `docs/design/tiered-enrollment.md` — (entry leg).
- `docs/design/concurrency.md` — the advisory-lock pattern catalog.
- `docs/operator/SECURITY-CONTROLS.md` — recovery threat-model subsection.
