# proposals/R11-2-catastrophic-loss-recovery.md

**Risk class:** MEDIUM (propose-and-wait)
**Mission link:** v2 M2-7 (open problems, PDF §9.1)
**Status:** PROPOSED, awaiting VANTA approval
**Effort:** ~2 sessions
**UC slot:** UC-9 (originally drafted as UC-8; renumbered in v8.15
after R11-6 / Bounded Revocation took the UC-8 slot)

## Problem

When a holder loses their ACTIVE token AND all RESERVE tokens, today
the only path is full reissuance from scratch — which loses the
predecessor chain and the audit history's continuity. The PDF
explicitly names this as an open problem at §9.1.

Realistic-deployment frequency: rare per holder, but **inevitable at
scale.** If Polaris is deployed to a population of N, roughly N × p
holders per year will hit total loss (house fire, theft + reserve also
compromised, etc.). The system needs a non-restart path.

## Why MEDIUM

The recovery procedure is the most adversary-exposed flow in Polaris.
A successful false-recovery attack means an impostor receives a
legitimate-looking token. Every design decision here is a defender's
move in a game against a determined attacker who is well-resourced
enough to attempt social engineering plus channel compromise.

HIGH would be defensible (it touches identity issuance, the most
sovereign-grade operation). MEDIUM is justified because the three-
channel out-of-band verification design (below) makes the attacker's
cost concrete and bounds the trust model.

LOW would be wrong; this is exactly the kind of change that needs
explicit user authorization before code.

## "Schema constrains the shape, agencies make the decision"

This is the third leg of the "schema doesn't weaponize itself against
the holder" triad (entry: R11-4 tiered enrollment; exit: R11-6
bounded revocation; recovery: this proposal). Each leg follows the
same architectural posture: **the schema adds vocabulary and
structural constraints, the agencies make the actual decision.**

In R11-2 specifically:

- The four `CHECK` constraints (cool-down ≥ 48h, three channels
  required, approver ≠ requester, status enum) constrain the
  **shape** of any successful recovery.
- The agencies — requesting and witnessing — make the **decision**
  about whether the claimed identity is genuine.
- Polaris refuses to record an APPROVED recovery that doesn't pass
  the structural gates. Polaris does NOT decide whether the holder
  *deserves* recovery; that decision belongs to the agencies and the
  out-of-band verification processes they run.

This puts R11-2 in the same category as **C3** (one ACTIVE per
individual: a constraint on issuance behavior, not a holder verdict),
**C7** (algorithm metadata via table: constraint on what an agency
may sign with), R11-6 (constitutional limits on issuer discretion:
constraint on revocation velocity), and R11-4 (tiered enrollment
vocabulary: constraint on how non-enrollment is recorded). The
MISSION constraint *"Polaris is NOT an authority"* is preserved
because Polaris remains a recording and constraint-enforcement
surface, not a deciding one.

The PDF §9.1 phrase the proposal anchors against is *"a recovery
protocol involving the issuing agency and out-of-band identity
verification, with a defined grace period."* All three elements
appear in this design (issuing-agency involvement, three-channel
OOB verification, defined administrative window).

## On the PDF's "grace period" — administrative vs operational

The PDF §9.1 phrase *"a defined grace period during which the
holder retains access to essential services"* admits two readings:

1. **Administrative grace period** — a procedural window during
   which the recovery request is processed (no premature approval).
   This is what the proposal's `cooldown_expires_at >= requested_at
   + INTERVAL '48 hours'` CHECK enforces.

2. **Operational grace period** — a substitute civic-access
   credential (a temporary attestation enabling continued use of
   essential services *during PENDING*) so the holder is not
   civically dark while their recovery is processed.

This proposal implements (1) — the administrative window. (2) is
**deferred to a follow-up** because it requires an external
verification path that downstream services would accept as a
temporary credential. The schema would need a `TemporaryAttestation`
table and verifier integration that's out of scope here.

When (2) lands, it should be additive: the PENDING `RecoveryRequest`
row would gain a child `TemporaryAttestation` with a strict
expiration tied to `cooldown_expires_at`, and verifiers would
accept the attestation only for the explicitly-flagged "essential
services" context. A small follow-up proposal.

The cool-down CHECK retains both meanings simultaneously: it's the
administrative window AND the maximum lifetime of any future
operational attestation. The proposal records the deferral
explicitly so the PDF's full intent is documented, not silently
narrowed.

## Game-theoretic structure

- **Game type:** Principal-agent with adversarial input. The recovery
  requester is the agent; Polaris is the principal. The requester may
  be the legitimate holder or an impostor.
- **Defender's claim:** Recovery requires successful verification
  through THREE independent out-of-band channels (biometric, sworn
  statement, witness-agency co-sign).
- **Attacker's optimal response:** Compromise one of the three
  channels and bet on procedural laxity.
- **Equilibrium:** Triple-channel commitment. To succeed, the attacker
  must compromise ALL THREE channels simultaneously — these are
  designed to be governed by independent failure modes.
- **Second-best attack:** Compromise just enough of the OOB
  verification to slip past a tired operator (social engineering on
  the witness agency, e.g.). Defended by:
  - Mandatory cool-down window (recovery requests sit PENDING for ≥ 48h)
  - Public-disclosure path: a notification mechanism for the claimed
    holder to discover and abort their own recovery (out of scope for
    v1 but reserved in the schema)
  - Required co-sign from a second AppUser before APPROVED status
- **Mechanism-design note:** triple-channel + cool-down + co-sign
  shifts attacker cost from "fake one signature" to "compromise three
  channels AND defeat the cool-down AND defeat the co-sign."
  Multiplicative cost, not additive.

Touches **C3** (one ACTIVE per individual) — recovery must preserve
this invariant. Touches **C1** (append-only audit) — every recovery
decision is forever in the audit trail.

## Recommended approach

Two-phase ceremony:

1. **`uc9_initiate_recovery(...)`** creates a `RecoveryRequest` row
   with `status = 'PENDING'`. Does NOT issue a token. Triggers
   notification to the security-officer pool (out of scope for v1
   beyond the AuthAuditLog record). Rejects if an ACTIVE token
   already exists for the individual (UC-4 is the right path then).
2. **`uc9_complete_recovery(...)`** (called by a different AppUser
   than the one who initiated) transitions the request to APPROVED
   or REJECTED. Acquires `pg_advisory_xact_lock` on the individual
   id so two threads racing the completion of the same PENDING
   request serialize cleanly (C9 — same pattern as UC-8's per-agency
   lock; see "Concurrency: C9" below). If APPROVED:
   - All currently non-terminal tokens for the individual transition
     to LOST via direct UPDATE; the auto-audit trigger emits the
     lifecycle event with `[RECOVERY:<recovery_id>]` tag in
     `reason_code`.
   - Each LOST token is **also published to `RevocationList`** in
     the same transaction (UC-4 pattern — without this, verifiers
     would continue accepting the lost tokens until the next CRL
     refresh).
   - A new IdentityToken is inserted with `status=ACTIVE`,
     `predecessor_token_id=NULL` (the chain was lost), and a
     lifecycle event tagged `RECOVERY_ISSUED [RECOVERY:<recovery_id>]`.

Both procedures set the `polaris.actor_agency_id` and
`polaris.reason_code` GUCs so the auto-audit trigger captures the
recovery context.

### Concurrency: C9

The advisory-lock pattern is the same one used by UC-8
(`uc8_revoke_token`) — see `DEVNOTES/concurrency.md`. Two threads
both calling `uc9_complete_recovery(p_recovery_id=X)` on the same
PENDING request would each pass the cool-down + three-channel CHECKs
before either UPDATE landed; one would commit, the other would also
attempt the UPDATE and the resulting INSERT of a new IdentityToken,
violating C3 (one ACTIVE per individual). The partial unique index
`uq_one_pending_recovery_per_individual` only protects INSERT, not
the completion phase.

```sql
PERFORM pg_advisory_xact_lock(
    hashtext('polaris.recovery.' ||
        (SELECT claimed_individual_id::TEXT
         FROM RecoveryRequest WHERE recovery_id = p_recovery_id)));
```

Cross-individual recoveries don't conflict; the lock is per-claimed-
individual. Transaction-scoped, releases at COMMIT/ROLLBACK.

## Implementation sketch

### Schema

```sql
CREATE TABLE RecoveryRequest (
    recovery_id              SERIAL       PRIMARY KEY,
    claimed_individual_id    INTEGER      NOT NULL
                             REFERENCES Individual(individual_id),
    requested_at             TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    requesting_agency_id     INTEGER      NOT NULL REFERENCES Agency(agency_id),
    requesting_user_id       INTEGER      NOT NULL REFERENCES AppUser(user_id),

    status                   VARCHAR(20)  NOT NULL DEFAULT 'PENDING'
                             CHECK (status IN ('PENDING','APPROVED','REJECTED','EXPIRED')),

    -- Three independent OOB channels. Each NULL until verified.
    biometric_verified       BOOLEAN      NOT NULL DEFAULT FALSE,
    sworn_statement_hash     VARCHAR(128),   -- hash-only commitment (per GenomicAnchor pattern)
    witness_agency_id        INTEGER      REFERENCES Agency(agency_id),
    witness_co_sign_user_id  INTEGER      REFERENCES AppUser(user_id),

    -- Approval ceremony
    decided_at               TIMESTAMP,
    decided_by_user_id       INTEGER      REFERENCES AppUser(user_id),
    decision_reason          TEXT,
    resulting_token_id       INTEGER      REFERENCES IdentityToken(token_id),

    -- Cool-down enforcement (48 hours minimum between request and decision)
    cooldown_expires_at      TIMESTAMP    NOT NULL,

    CONSTRAINT cooldown_window_minimum CHECK (
        cooldown_expires_at >= requested_at + INTERVAL '48 hours'
    ),

    CONSTRAINT approved_requires_three_channels CHECK (
        status != 'APPROVED' OR (
            biometric_verified = TRUE AND
            sworn_statement_hash IS NOT NULL AND
            witness_agency_id IS NOT NULL AND
            witness_co_sign_user_id IS NOT NULL
        )
    ),

    CONSTRAINT approved_after_cooldown CHECK (
        status != 'APPROVED' OR decided_at >= cooldown_expires_at
    ),

    CONSTRAINT approver_differs_from_requester CHECK (
        decided_by_user_id IS NULL OR
        decided_by_user_id != requesting_user_id
    )
);

-- One PENDING request per individual at a time
CREATE UNIQUE INDEX uq_one_pending_recovery_per_individual
    ON RecoveryRequest(claimed_individual_id)
    WHERE status = 'PENDING';
```

The four CHECK constraints encode the entire mechanism-design in the
schema layer. An attacker cannot bypass the cool-down, cannot self-
approve, cannot skip the three channels — the database refuses.

### Stored procedures

```sql
CREATE PROCEDURE uc9_initiate_recovery(
    p_individual_id      INTEGER,
    p_requesting_agency  INTEGER,
    p_requesting_user    INTEGER
);

CREATE PROCEDURE uc9_complete_recovery(
    p_recovery_id        INTEGER,
    p_deciding_user      INTEGER,
    p_decision           VARCHAR,    -- 'APPROVED' or 'REJECTED'
    p_reason             TEXT,
    p_new_token_value    VARCHAR,    -- only used if APPROVED
    p_new_serial         VARCHAR,
    p_algorithm_id       INTEGER,
    p_biometric_binding  VARCHAR,
    p_liveness_check     VARCHAR
);
```

`uc9_complete_recovery`'s APPROVED branch:

1. Acquire `pg_advisory_xact_lock` keyed on the claimed individual id (C9).
2. Pre-checks: cooldown expired, three-channel evidence present, approver
   holds `security-officer` role (see "Co-signer role" below), approver
   user_id != requester user_id (also schema-enforced).
3. Set `polaris.actor_agency_id` and `polaris.reason_code` GUCs.
   `reason_code` for the lost tokens: `LOST_BY_RECOVERY [RECOVERY:<recovery_id>]`.
4. For each currently non-terminal token of the individual:
   - `UPDATE IdentityToken SET status='LOST'` — auto-audit trigger emits
     the lifecycle row with the tagged `reason_code`.
   - `INSERT INTO RevocationList` so verifiers see the revocation through
     the CRL freshness path (UC-4 pattern; without this the token state
     would diverge from the published CRL).
5. Insert the new IdentityToken with `status='ACTIVE'`,
   `predecessor_token_id=NULL` (the prior chain was lost — distinct from
   UC-4's reserve activation, which DOES set predecessor).
6. Update the `polaris.reason_code` GUC to `RECOVERY_ISSUED
   [RECOVERY:<recovery_id>]` and UPDATE the new token's status (the
   `IDENTITY_ISSUED` lifecycle row carrying the recovery tag is generated
   by the auto-audit trigger).
7. Update `RecoveryRequest.status='APPROVED'`, `decided_at`,
   `decided_by_user_id`, `resulting_token_id`.

### Co-signer role (refinement of original "co-sign requirement strength")

The original "What this needs from you" item 2 asked whether the
deciding user must hold a distinct role. **Recommendation lifted into
acceptance:** initiation and completion split across the existing
role enum (`admin` / `operator` / `auditor`) rather than introducing
a new role:

| Step | Required role |
|---|---|
| Initiate (`uc9_initiate_recovery` + `/uc9/initiate-recovery`) | `operator` or `admin` |
| Complete (`uc9_complete_recovery` + `/uc9/decide/<id>`) | `admin` only |
| View queue (`/uc9/queue`) | any authenticated role |

This keeps the existing three-role schema unchanged (no migration
needed). `operator` and `admin` can both initiate; only `admin` can
complete. Two `operator` accounts colluding to fake a recovery
cannot succeed — the completion step is structurally above their
role. The `auditor` role remains read-only by design (can view the
queue and the audit trail of past decisions, cannot initiate or
complete).

```sql
-- inside uc9_complete_recovery:
IF NOT EXISTS (
    SELECT 1 FROM AppUser
    WHERE user_id = p_deciding_user
      AND role = 'admin'
      AND is_active = TRUE
) THEN
    RAISE EXCEPTION 'Recovery decision requires admin role';
END IF;
```

The Flask routes enforce the same shape via `@security.require_role`.
The schema-level CHECK is belt-and-suspenders: even if the app layer
were bypassed (SQL Console with admin credentials), the procedure
still refuses to complete a recovery for a non-admin user_id.

### App routes

| Route | Method | Purpose |
|---|---|---|
| `/uc9/initiate-recovery` | POST | Form-driven; requesting operator |
| `/uc9/queue` | GET | List PENDING recoveries (security-officer dashboard) |
| `/uc9/decide/<recovery_id>` | POST | Approve or reject; co-sign required |

### Tests

`CatastrophicLossRecoveryTests` class:

- Initiate creates PENDING row with `cooldown_expires_at` correctly set
- Cannot initiate when ACTIVE token exists (use UC-4 instead)
- Cannot decide before cooldown expires
- Cannot self-approve (`requesting_user_id == deciding_user_id`)
- Cannot decide as `operator` role — admin required (procedural and
  schema-level CHECK both rejected)
- Cannot decide as `auditor` role
- APPROVED requires all three channels
- APPROVED transitions all of the individual's non-terminal tokens
  to LOST
- APPROVED publishes each LOST token to `RevocationList` (UC-4
  pattern; verifier CRL stays consistent with token state)
- APPROVED issues new token with `status=ACTIVE`,
  `predecessor_token_id=NULL`
- The new token's `TokenLifecycleEvent.reason_code` carries
  `RECOVERY_ISSUED [RECOVERY:<recovery_id>]`
- The LOST tokens' lifecycle rows carry
  `LOST_BY_RECOVERY [RECOVERY:<recovery_id>]`
- C3 preserved: exactly one ACTIVE token per individual after
  recovery completes
- REJECTED flow: no new token, no `RevocationList` rows, decision
  logged on the `RecoveryRequest` row
- Cannot have two PENDING requests for same individual (partial
  unique index)
- AuthAuditLog captures every state transition

**Concurrency tests (C9, in `ConcurrencyTests`):**

- **Race the completion with real threads.** Set up a PENDING
  recovery request past its cool-down. Spawn `T` threads (T ≥ 4),
  each calling `uc9_complete_recovery(recovery_id)` with valid
  approver credentials. Expected outcome: **exactly one** thread
  succeeds (status → APPROVED, one new ACTIVE token). The others
  see the post-commit state and either find the request no longer
  PENDING (status check) or fail the partial-unique-index
  constraint on the new ACTIVE token (C3 backstop).
- **Cross-individual recoveries run in parallel.** Two threads,
  two different PENDING recoveries for different individuals,
  both with valid approvers. Both should succeed in parallel
  (advisory-lock key is per-individual, not global). Assert
  wall-clock time < (single-thread time × 1.5).

## Predicted blast radius

- `polaris_sql/01_schema.sql` — `RecoveryRequest` table + partial
  unique index (~80 lines). Schema goes to 17 tables.
- `polaris_sql/02_indexes.sql` — index on
  `RecoveryRequest(status, claimed_individual_id)` to support the
  queue route (~5 lines).
- `polaris_sql/05_procedures.sql` — `uc9_initiate_recovery` (~50
  lines), `uc9_complete_recovery` with advisory-lock + role check +
  RevocationList integration (~180 lines). Procedure count goes to
  7 (was 5).
- `polaris_sql/06_triggers.sql` — no new trigger; the existing
  state-machine and auto-audit triggers handle the ACTIVE → LOST
  transitions on their own once `uc9_complete_recovery` issues the
  UPDATEs with the right GUCs set.
- `polaris_sql/04_data.sql` — one example `RecoveryRequest` in
  PENDING state for the queue demo (~10 lines).
- `polaris_sql/08_tests.sql` — section M: 4–5 SQL self-tests for the
  CHECK constraints, partial unique index, and the
  pg_advisory_xact_lock invocation pattern (~70 lines).
- `polaris_web/app.py` — three routes (~150 lines).
- `polaris_web/templates/` — `uc9_initiate.html`, `uc9_queue.html`,
  `uc9_decide.html` (~180 lines combined).
- `polaris_web/test_app.py` — `CatastrophicLossRecoveryTests` (~350
  lines) + 2 new tests in `ConcurrencyTests` for the advisory-lock
  behavior (~90 lines).
- `polaris_sql/13_substrate.sql` — `out_of_band_verification` row
  already listed in `SystemDependency`; cross-reference the new
  recovery procedure in the row's `notes` column.
- `DEVNOTES/recovery-ceremony.md` (new) — the three-channel design
  rationale, adversary walk, advisory-lock rationale (per-individual
  granularity), administrative-vs-operational grace-period framing,
  what breaks if any of the four CHECK constraints is removed.
- `DEVNOTES/concurrency.md` — append a brief note about the
  per-individual advisory-lock pattern (mirrors the per-agency
  pattern already documented for UC-8).
- `MISSION.md` — mark M2-7 ✅.
- `ROADMAP.md` — mark R11-2 ✅.
- `docs/DATA-MODEL.md` — new `RecoveryRequest` section.
- `docs/SECURITY.md` — recovery threat model subsection.
- `docs/API.md` — three new endpoints documented.

## Acceptance criteria

- ✅ `RecoveryRequest` table with all four CHECK constraints (cool-down,
  three-channel, approver ≠ requester, status enum).
- ✅ Partial unique index enforces one PENDING per individual.
- ✅ `uc9_initiate_recovery` + `uc9_complete_recovery` procedures.
- ✅ Cool-down window of ≥ 48h is structurally unbypassable.
- ✅ Requesting user cannot be the deciding user (schema-enforced).
- ✅ **Deciding user must hold `admin` role** — checked both at the
  Flask route (`@security.require_role('admin')`) and inside the
  procedure (RAISE EXCEPTION on non-admin). Belt-and-suspenders.
- ✅ **C9 advisory-lock**: `uc9_complete_recovery` opens with
  `pg_advisory_xact_lock(hashtext('polaris.recovery.' ||
  claimed_individual_id::TEXT))`. Two threads racing completion of
  the same PENDING request serialize cleanly; final state has
  exactly one ACTIVE token. Cross-individual recoveries run in
  parallel.
- ✅ **RevocationList integration**: every LOST token from APPROVED
  recovery gets a `RevocationList` row in the same transaction.
  Mirrors UC-4 pattern; verifier-facing CRL stays consistent.
- ✅ **Audit-row tagging**: the LOST tokens' lifecycle rows carry
  `LOST_BY_RECOVERY [RECOVERY:<recovery_id>]` in `reason_code`; the
  new ACTIVE token's lifecycle row carries `RECOVERY_ISSUED
  [RECOVERY:<recovery_id>]`. Audit replay can reconstruct the full
  recovery context from the lifecycle log alone.
- ✅ C3 (one ACTIVE per individual) preserved through the ceremony.
- ✅ C1 (audit append-only) preserved; every recovery decision
  immutable.
- ✅ ≥ 13 new tests in `CatastrophicLossRecoveryTests` + ≥ 2 new
  tests in `ConcurrencyTests` (race completion, cross-individual
  parallelism).
- ✅ `DEVNOTES/recovery-ceremony.md` documents the adversary walk,
  the three-channel design, the cool-down-vs-grace-period
  distinction (administrative window v1; operational
  TemporaryAttestation deferred), and what breaks if any of the
  four CHECK constraints is removed.
- ✅ The proposal in `BACKLOG.md`'s "Operator-AI assistant" note
  references recovery as an example where the assistant must NOT
  auto-execute (mechanism-design symmetry; same boundary).

## What this is NOT

- **Not Polaris deciding who deserves recovery.** Polaris constrains
  the *shape* of the decision via four CHECK constraints; the agencies
  and OOB verification processes make the decision. Same posture as
  R11-4 (tiered enrollment vocabulary), R11-6 (constitutional limits
  on issuer discretion), C3 (one ACTIVE per individual), C7
  (algorithm metadata).
- **Not the PDF §9.1 operational grace period.** v1 implements the
  administrative window (≥48h between request and decision). The
  operational version — a `TemporaryAttestation` that lets the
  holder retain essential-services access during PENDING — is a
  documented follow-up. See "On the PDF's 'grace period'" section.
- Not OIDC-or-similar external-IDP recovery (that's R8-3 OIDC,
  deferred).
- Not biometric enrollment infrastructure (the `biometric_verified`
  flag is set by an OOB process; this proposal does not specify how
  that process works, only that its result is recorded).
- Not key escrow (private signing keys remain not held by the issuer
  per architectural-soul section 5 of MISSION.md).
- Not silent recovery; every transition logs to `AuthAuditLog` AND
  to `TokenLifecycleEvent`.
- Not auto-derivation of recovery state from token state. A token
  going LOST does NOT automatically trigger a `RecoveryRequest` —
  the request must be initiated by a human operator as a policy
  event. Same anti-auto-derivation posture as R11-4.

## What this needs from you

"Yes do R11-2" plus three remaining decisions (down from three in
the original draft, with the co-sign-strength decision answered by
the alignment audit):

1. **Cool-down window length.** Default **48 hours**. Trade-off:
   shorter window = faster legitimate recovery, larger attacker
   exploitation surface; longer window = legitimate holders
   frustrated. The 48h floor is a CHECK; per-deployment overrides
   would need a `RecoveryDiscretionPolicy` table (deferred — out
   of scope for v1, but the design is forward-compatible).
2. **Whether to surface PENDING-recovery notifications to other
   parties.** The "claimed holder must be notified before their
   recovery is approved" is a strong defense but requires an
   external notification channel. Recommend out-of-scope for v1
   but **reserve a `notification_method` column** for future use.
3. **TemporaryAttestation deferral acceptance.** The PDF §9.1
   "operational grace period" is deferred to a follow-up proposal.
   This proposal records the deferral explicitly (rather than
   silently narrowing the PDF intent to administrative-only). OK?
   Or do you want the operational grace mechanism in v1?

The original "co-sign requirement strength" question (was item 2 in
the unrefined draft) is now answered by the audit: `admin` role
required for completion, schema-enforced via RAISE EXCEPTION.
