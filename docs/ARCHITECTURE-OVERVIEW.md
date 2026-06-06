# Polaris architecture overview

**Audience:** an engineer or auditor evaluating Polaris.
**Goal:** understand what Polaris IS, what it is NOT, what the layers
are, and how to navigate the codebase.

This document pairs with `docs/QUICKSTART.md` (operator quickstart).
Quickstart gets a stack running; this document explains why each piece
looks the way it does.

---

## §I. What Polaris is

Polaris is a reference implementation of a national identity token
system. It demonstrates a substrate where:

- **One identity per person** is enforced by a partial unique index,
  not by application logic.
- **Audit-of-record** is enforced by append-only triggers, not by
  developer discipline.
- **Zero-knowledge verification** is enforced by a server-side trigger,
  not by client-side cooperation.
- **Post-quantum cryptography** is at the substrate, not as a future
  migration path.

The phrase "by construction" appears throughout. It is shorthand for:
the system cannot be operated in a way that violates the constraint,
because the constraint is enforced before any application code runs.

Polaris is built for SCS-230 (Database Management Systems) at Seton
Hill University, by Egor Khaklin (VANTA). The version trajectory is
v1 (course assignment: schema + Flask) through the current reference
implementation: the product plus a flat invariant-check layer
(`polaris_checks/`).

---

## §II. What Polaris is NOT

Equally important. Polaris does not:

- **Hold money.** No transactions, no balances, no merchant codes.
  C10 ("Identity is not money") is constitutional.
- **Aggregate across individuals.** The ontology layer refuses
  cross-individual aggregation primitives with a structural
  regression guard. Object Cards are single-entity-focused.
- **Provide notebook authoring or predictive scoring.** These patterns
  are refused.
- **Run with multi-region failover.** Single-region only.
- **Carry a state-level surveillance API.** The verification graph is
  structurally inaccessible at the ZERO_KNOWLEDGE disclosure level
  (C2 trigger enforces `token_id IS NULL`).

Each of these is a deliberate constitutional decision. The Vocation
(anti-coercion) sits above C1-C10 and refuses any drift toward these
patterns on sight.

---

## §III. The vocation

Above the ten hard constraints (C1-C10) sits the vocation:
**anti-coercion**. Every constraint serves this vocation:

- C1 (audit-of-record): a coerced operator's actions leave evidence
- C2 (zero-knowledge): the verification graph is not a coercion
  surface
- C3 (one identity per person): a coerced individual cannot be
  duplicated to bypass quotas
- C4 (atomic failed-login counter): a coerced operator cannot be
  used as a credential-stuffing oracle without trace
- C5 (CSP forbids inline scripts): a coerced operator's session is
  not exploitable via injection
- C6 (server-side disclosure enforcement): a coerced client cannot
  unilaterally upgrade their disclosure level
- C7 (no hardcoded crypto): a coerced operator can rotate algorithms
  without invalidating existing identity claims
- C8 (bounded result sets): a coerced operator cannot extract the
  whole population via /api/atlas/* endpoints
- C9 (concurrency hazards tested with real threading): a coerced
  operator cannot rely on race-condition exploits documented in
  the test suite
- C10 (identity is not money): a coerced operator cannot be used to
  forge financial state via the identity rail

Anti-coercion is the deepest constraint, explicitly above C1-C10 in
`MISSION.md §"Vocation"`. Any proposal that moves the system away from
this alignment is refused.

---

## §IV. The layers

Polaris has the product (three concentric layers) and a flat
invariant-check layer that gates CI.

### Layer 1: Data substrate (`polaris_sql/`)

PostgreSQL 16. 28 tables, stored procedures, triggers, append-only
audit-of-record tables, and schema-level guards. Migrations framework
records SHA-256 hashes; append-only by trigger.

The schema is the constitution. The Flask application is a UI on top
of the schema. The schema can be operated via raw SQL (the
`/sql` route is an authenticated console) and the constraints still
hold; they are not mediated by the application.

Key tables (28 total, partial list):
- `IdentityToken` — the central object
- `Individual` — the person an identity is bound to
- `Agency` — the issuer of an identity
- `CryptographicAlgorithm` — algorithm-rotation substrate (C7)
- `TokenLifecycleEvent` — append-only audit (C1)
- `VerificationEvent` — append-only audit (C1, C2)
- `EnrollmentStatusEvent` — append-only audit (R11-4)
- `TokenSignature` — multi-sig migration substrate (R11-1)
- `AnchorBatch` — Merkle anchoring substrate (R10-2)
- `AgencyTrustAttestation` — federation substrate (R11-3)
- `DuressEvent` — duress code substrate (R11-5)
- `QuantumObserverBinding` — SCAFFOLD; RESERVED-NOT-PLANNED (v9.23)
- `AuditAccessLog` — meta-audit (v9.20); append-only
- `OperatorWebauthnCredential` — operator MFA substrate (v8.97)
- `schema_version` — migration registry (v8.95)
- ...

### Layer 2: Application (`polaris_web/`)

Python 3 / Flask / gunicorn. ~4,298 lines of `app.py`. ~851 lines of
`security.py`. ~459 lines of `webauthn_auth.py`. Templates use Jinja2.
CSS is hand-rolled (no Tailwind), navy/gold intelligence-report
aesthetic. JavaScript is external-only (no inline scripts; CSP
enforces). The atlas globe uses D3 + topojson, no CDN dependency.

Application architecture is straightforward: routes map to UC stored
procedures; the application does authentication, CSRF, rate-limiting,
and rendering; the SQL layer enforces correctness.

### Layer 3: ZK crate + second witness (`polaris_zk/`)

The Plonky2 Merkle-inclusion ZK crate in Rust (`polaris_zk/src/lib.rs`)
proves epoch membership without revealing which token. An independent
Python second witness (`polaris_zk/witness2/`) re-derives the same
result by a different code path, so a single implementation bug cannot
silently pass both checks.

### The check layer (`polaris_checks/`)

`polaris_checks/checks.py` is the flat invariant layer: one
`check_*(repo_root)` function per constraint, with tested detection
correctness in `polaris_checks/test_checks.py`. It gates CI via
`python3 -m polaris_checks.run`, which fails on any FAIL. The checks
are the machine-checkable enforcement of most of C1-C10 (the rest are
enforced at the DB level via triggers, partial unique indexes, and
CHECK constraints).

### Operator scripts (`scripts/`)

The `polaris-*.sh` scripts mediate operator-system collaboration.
They are documented one-per-file with full usage in the script header.
Examples:
- `polaris-deploy.sh` — bring up production stack
- `polaris-backup.sh` — atomic full-system backup
- `polaris-restore.sh` — recovery from backup
- `polaris-migrate.sh` — apply or roll back migrations
- `polaris-rotate-secret.sh` — rotate secrets without downtime
- `polaris-archive.sh` — export audit-log rows to cold storage
- `polaris-recover-admin.sh` — emergency unlock for locked-out admin
- `polaris-cron-install.sh` (v9.23) — install operator crontab
- `polaris-set-webauthn-deadline.sh` (v9.23) — set WebAuthn deadline
- `polaris-loadtest-tokens.sh` (v9.23) — token-volume load simulator

---

## §V. Identity flow (concrete walkthrough)

The five stages of an identity:

1. **Enrollment** (`uc4_activate_reserve`): an individual is added
   to the system; their `IdentityToken` row starts in `RESERVED`
   state. Tier-A vs Tier-B enrollment (R11-4) determines the
   level of attestation required.

2. **Issuance** (`uc1_issue_and_activate`): the token transitions
   from `RESERVED` to `ACTIVE`. A signing key from
   `CryptographicAlgorithm` is bound. A `TokenLifecycleEvent` row
   is written (C1).

3. **Verification**: a relying party submits a verification request.
   The disclosure level is one of `ZERO_KNOWLEDGE`, `EXISTS_AT_ALL`,
   `PARTIAL`, `FULL`. Server-side enforcement (C6) sets
   `token_id` to NULL on ZERO_KNOWLEDGE events (C2). A
   `VerificationEvent` row is written (C1). The new
   `requesting_purpose_text` column (v9.20) records the stated
   purpose.

4. **Revocation** (`uc8_revoke_token`): the token transitions from
   `ACTIVE` to `REVOKED`. Issuer-discretion bounds (R11-6) apply.
   A `TokenLifecycleEvent` row is written (C1).

5. **Anchoring** (R10-2 / M2-2): periodically, the running set of
   active tokens is hashed into a Merkle tree; the root is anchored
   to an external substrate; each token gets an inclusion proof.
   The ZK-SNARK (R10-1 / M2-1) proves epoch membership without
   revealing which token.

The duress flow (R11-5 / M2-10): an individual under coercion
provides their duress code instead of their primary code; the
verification appears to succeed to the coercer but a `DuressEvent`
row appears in the audit table.

---

## §VI. Cryptographic substrate

- **ML-DSA-65** (NIST FIPS 204): lattice-based signatures.
  Post-quantum secure under the Module-LWE assumption.
- **Plonky2 ZK-SNARK** (FRI-based, transparent setup, hash-only
  commitments): proves epoch membership.
- **SHA3-256 Merkle commitments**: anchor-set batching with
  logarithmic-per-leaf inclusion proofs.
- **M-of-N multi-sig migration** (R11-1): per-token signature
  schemes; algorithm rotation without invalidating existing tokens.
- **Constant-time duress code check** (R11-5): coercer-visible flow
  is identical to legitimate flow.
- **Per-context trust attestations** (R11-3 federation): Agency V
  accepts agency I for context C until date D; no transitive trust.

The crypto is REAL, not stubbed. The Plonky2 SNARK has a working
prover/verifier in Rust (`polaris_zk/`). Signature verification is a
live FIPS 204 path. The Merkle anchoring batches actual tokens.

The constraint C7 (no hardcoded cryptography) means algorithm
parameters flow through the `CryptographicAlgorithm` table. To
rotate, an operator updates the table; no schema migration required.

---

## §VII. The check layer in depth

### `polaris_checks/`

`polaris_checks/checks.py` holds one `check_*(repo_root)` function per
invariant. Each function scans the repository and returns a PASS/FAIL
result. `python3 -m polaris_checks.run` runs them all and gates on any
FAIL. `polaris_checks/test_checks.py` proves each check actually
detects the violation it claims to (tested detection correctness), so
a check that silently passes on a real violation is itself caught.

This flat layer is the machine-checkable enforcement of most of
C1-C10. The remainder are enforced at the DB level: append-only
triggers (C1), the ZERO_KNOWLEDGE `token_id IS NULL` trigger (C2), the
partial unique index for one-identity-per-person (C3), the atomic
failed-login counter (C4), and CHECK constraints. The checks verify
that the codebase keeps the shape those guarantees depend on (for
example, that CSP forbids inline scripts (C5) and that cryptographic
algorithms flow through the `CryptographicAlgorithm` table (C7)).

---

## §VIII. What the test suite covers

- The `polaris_checks` layer: one `check_*` per invariant, plus the
  detection-correctness tests in `polaris_checks/test_checks.py`,
  gated by `python3 -m polaris_checks.run`.
- DB-backed product suites: `polaris_web/test_check_constraints`,
  `test_invariants_property`, `test_redaction_property`, `test_app`,
  and `polaris_cli/test_cli`.
- Hypothesis property tests for C1, C2, C3.
- Schema-CHECK regression tests.
- SQL self-tests in `08_tests.sql` and section T in
  `12_v7_constraints.sql`.

Run the check layer via `python3 -m polaris_checks.run`; the DB-backed
suites via `./scripts/ai-test.sh` (which wraps the env).

Some of these tests verify that the codebase IS A CERTAIN SHAPE, not
just that it does the right thing on a given input. Examples:

- `test_polaris_version_is_canonical`: app.py imports version from
  `__version__.py` rather than redefining
- `test_dockerfile_covers_all_runtime_app_modules`: every
  top-level import in app.py is COPY'd by both Dockerfiles
- `test_ontology_refuses_cross_entity_aggregation`: the cross-entity
  surveillance pattern refusal is pinned

---

## §IX. Deployment

Three deployment paths (see `docs/DEPLOYMENT.md`):

1. **Single-host Docker (the reference path)**: Docker Compose
   orchestrates Caddy + Postgres + Redis + gunicorn. The
   `polaris-deploy.sh prod` script automates this end-to-end.
2. **Kubernetes**: Helm chart deferred.
3. **Bare-metal**: documented but not automated.

For each path: TLS via Caddy + Let's Encrypt; secrets via
`polaris-generate-secrets.sh`; backup via `polaris-backup.sh`;
restore via `polaris-restore.sh` (see `DR-SINGLE-REGION.md`).

Production checklist:
- Change all demo passwords
- Set `webauthn_required_after` on all admin accounts
- Configure backup destination + cron
- Set up off-host backup replication
- Configure quarterly DR drill (in crontab)
- Subscribe to security advisories
- Review the threat model (`DEVNOTES/threat-model.md`)

---

## §X. The "by construction" insight

The governing philosophy: every claim Polaris makes is enforced by a
structural primitive (trigger, constraint, index), not by a policy
primitive (developer discipline, review process). The test to apply
is: "if I remove this primitive, does the claim still hold?" If yes,
the primitive is redundant; if no, the primitive is load-bearing.

The C1-C10 constraints map to a 10-node lattice
(`meta/constraint-lattice.md`), and the `polaris_checks/` layer is the
machine-checkable record of which primitives are load-bearing.

---

## §XI. Steady state

Polaris reached steady-state on 2026-05-12. The default posture for
ambiguous requests is DECLINE-AND-SURFACE: the system does not silently
expand into new mission scope. New scope requires explicit operator
authorization.

This is itself an anti-coercion primitive: a coerced operator cannot
direct the system into unbounded mission expansion. The constraint
binds scope expansion, not the operator; the operator may authorize
new scope at any time.

---

## §XII. Where the project stands

The current trajectory closed the gap between architectural
sophistication and operational reality: production deployment and the
flat `polaris_checks/` layer that gates CI.

The vocation (anti-coercion) is named and sits above C1-C10. The
ontology layer refuses cross-individual aggregation. Operator-facing
rollout, DR, and GitHub conventions are in place.

The next iteration's scope depends on which operational triggers fire:
production-deployment incident, partner integration, federation
requirement, or a large jump in verification volume.

---

## Further reading

- `MISSION.md` — the constitution
- `CLAUDE.md` — agent runbook (doubles as developer onboarding)
- `polaris_checks/checks.py` — the flat C1-C10 invariant layer
- `meta/constraint-lattice.md` — the C1-C10 constraint lattice
- `meta/structural-architecture.md` — structural enforcement primitives
- `DEVNOTES/style.md` — VANTA's standing instructions
- `DEVNOTES/threat-model.md` — schema/runtime STRIDE model
- `docs/operator/OPERATIONS.md` — day-2 runbook
- `docs/operator/DR-SINGLE-REGION.md` (v9.23) — disaster recovery
- `docs/operator/WEBAUTHN-ROLLOUT.md` (v9.23) — WebAuthn rollout
- `docs/RED-TEAM-SCOPE.md` (v9.23) — external red-team scope
