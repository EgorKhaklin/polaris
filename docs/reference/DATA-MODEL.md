# DATA-MODEL.md — schema reference

The Polaris schema is **27 tables** organized into six functional groups:

- **Entities** (Individual, Agency, AppUser, CryptographicAlgorithm,
  VerificationContext) — the things that exist in the world
- **Identity tokens** (IdentityToken, RevocationList) — the canonical
  state-bearing objects
- **Audit log** (TokenLifecycleEvent, VerificationEvent) — append-only
  history. Constraint C1.
- **Records & substrate** (DeviceBinding, BlockchainAnchor,
  GenomicAnchor, QuantumObserverBinding) — non-mutable commitments
  recorded alongside the token at issuance time. GenomicAnchor (M2-4)
  and QuantumObserverBinding (M2-5) are the substrate-arc additions
  from v2.
- **Junctions** (AgencyAlgorithmAuth, TokenPermission) — M:N
  resolutions with composite primary keys
- **Operational** (AuthAuditLog) — the auth audit log; append-only
  by trigger

Schema is in `polaris_sql/01_schema.sql`. Indexes in
`polaris_sql/02_indexes.sql`. Triggers (state machine, append-only,
audit) in `polaris_sql/06_triggers.sql`. The reserved future
primitive (`QuantumObserverBinding`) is in scaffold state — see
`DEVNOTES/ships/quantum-observer.md`.

---

## Entity tables

### `Individual`

The natural person to whom an identity token may be issued.

| column | type | notes |
|---|---|---|
| `individual_id` | SERIAL PK | |
| `legal_name` | VARCHAR(120) NOT NULL | full name as on supporting documents |
| `dob` | DATE NOT NULL | date of birth |
| `country_code` | CHAR(2) | ISO 3166-1 alpha-2 |
| `external_ref` | VARCHAR(64) UNIQUE | optional cross-reference to upstream system |

Soft-delete not supported: an individual cannot be deleted if any
IdentityToken references them, by FK.

### `Agency`

A government body or authorized organization that may issue,
deactivate, or verify tokens.

| column | type | notes |
|---|---|---|
| `agency_id` | SERIAL PK | |
| `agency_name` | VARCHAR(120) NOT NULL | |
| `agency_type` | VARCHAR(40) NOT NULL | `ISSUING` \| `VERIFYING` \| `DEPLOYMENT` etc. |
| `country_code` | CHAR(2) | |
| `accreditation_status` | VARCHAR(20) | |

### `CryptographicAlgorithm`

Algorithm metadata; constraint C7 says algorithm choice flows
through this table, never hardcoded in app code.

| column | type | notes |
|---|---|---|
| `algorithm_id` | SERIAL PK | |
| `name` | VARCHAR(40) NOT NULL UNIQUE | e.g. `ML-DSA-65`, `SLH-DSA-128` |
| `family` | VARCHAR(20) NOT NULL | e.g. `LATTICE`, `HASH-BASED`, `RSA`, `ECDSA` |
| `is_post_quantum` | BOOLEAN NOT NULL | default `FALSE` |
| `key_size` | INTEGER NOT NULL | bits |
| `is_active` | BOOLEAN NOT NULL | when FALSE, no new tokens may be issued under this algorithm |

### `VerificationContext`

Defines a permitted purpose for verification (HEALTHCARE, BANKING,
TRAVEL, etc.). The context determines which disclosure levels are
permitted for that purpose.

| column | type | notes |
|---|---|---|
| `context_id` | SERIAL PK | |
| `context_type` | VARCHAR(40) NOT NULL UNIQUE | |
| `description` | TEXT | |
| `permitted_disclosure` | VARCHAR(20)[] | which disclosure levels are allowed |

### `AppUser`

Operator credentials for the web app. NOT the same as Individual —
this is who logs in to use the system, not who holds tokens.

| column | type | notes |
|---|---|---|
| `username` | VARCHAR(64) PK | |
| `password_hash` | VARCHAR(255) NOT NULL | argon2id |
| `role` | VARCHAR(20) NOT NULL | `admin` \| `operator` \| `auditor` |
| `agency_id` | INTEGER | FK to Agency, optional |
| `failed_login_count` | INTEGER NOT NULL DEFAULT 0 | atomic increment via `col = col + 1 RETURNING ...`; constraint C4 |
| `locked_until` | TIMESTAMP | |

---

## Identity token tables

### `IdentityToken`

The core state-bearing object.

| column | type | notes |
|---|---|---|
| `token_id` | SERIAL PK | |
| `token_value` | VARCHAR(128) NOT NULL UNIQUE | canonical token serial |
| `physical_serial` | VARCHAR(64) NOT NULL UNIQUE | hardware serial |
| `hardware_model` | VARCHAR(50) | |
| `biometric_binding_type` | VARCHAR(20) NOT NULL | `NONE` \| `FINGERPRINT` \| `FACE` \| `IRIS` |
| `individual_id` | INTEGER NOT NULL FK | the holder |
| `issuing_agency_id` | INTEGER NOT NULL FK | |
| `algorithm_id` | INTEGER NOT NULL FK | constraint C7 |
| `predecessor_token_id` | INTEGER FK self | succession; `NULL` for first token |
| `activation_sequence` | INTEGER NOT NULL DEFAULT 1 | |
| `status` | VARCHAR(20) NOT NULL DEFAULT 'RESERVE' | state machine in `06_triggers.sql` |
| `issued_date` | TIMESTAMP NOT NULL DEFAULT now() | |
| `activated_date` | TIMESTAMP | required if status=ACTIVE (trigger) |

**Indexes:**

- `uq_one_active_per_person` — partial unique on `(individual_id)
  WHERE status = 'ACTIVE'`. Constraint C3.
- `idx_token_individual_status` — composite on
  `(individual_id, status)` for per-holder status lookups.
- `idx_token_status` — single-column for global status filtering.

**Triggers:**

- `trg_token_state_machine` (BEFORE UPDATE OF status) — rejects
  illegal transitions; legal set is in `06_triggers.sql`.
- `trg_token_audit` (AFTER UPDATE) — emits a TokenLifecycleEvent for
  every status change, automatically.

### `RevocationList`

Records revocations distinct from the token's own status, used for
external-facing revocation publication.

| column | type | notes |
|---|---|---|
| `revocation_id` | SERIAL PK | |
| `revoked_token_id` | INTEGER NOT NULL FK | must reference a token whose status is REVOKED, LOST, or EXPIRED (constraint enforced in `01_schema.sql`) |
| `revocation_reason` | VARCHAR(40) NOT NULL | |
| `effective_date` | TIMESTAMP NOT NULL | |
| `published_at` | TIMESTAMP | NULL means not yet published |

---

## Audit tables (constraint C1: append-only)

### `TokenLifecycleEvent`

Every state transition of an IdentityToken.

| column | type | notes |
|---|---|---|
| `event_id` | SERIAL PK | |
| `token_id` | INTEGER NOT NULL FK | |
| `actor_agency_id` | INTEGER FK | nullable (device events have no agency) |
| `event_type` | VARCHAR(20) NOT NULL | `ISSUED` \| `ACTIVATED` \| `DEACTIVATED` \| `DEVICE_BOUND` \| `DEVICE_REVOKED` \| `REVOKED` \| `LOST` \| `EXPIRED` \| `REPLACED` |
| `event_timestamp` | TIMESTAMP NOT NULL DEFAULT now() | |
| `reason_code` | VARCHAR(60) | |
| `latitude`, `longitude` | DOUBLE PRECISION | nullable |

**Trigger:** `trg_lifecycle_append_only` (BEFORE UPDATE OR DELETE)
raises `insufficient_privilege`. Constraint C1.

### `VerificationEvent`

Every verification attempt.

| column | type | notes |
|---|---|---|
| `event_id` | SERIAL PK | |
| `token_id` | INTEGER FK | **NULLABLE** — must be NULL for ZERO_KNOWLEDGE; constraint C2 |
| `requesting_agency_id` | INTEGER NOT NULL FK | |
| `context_id` | INTEGER NOT NULL FK | |
| `event_timestamp` | TIMESTAMP NOT NULL DEFAULT now() | |
| `outcome` | VARCHAR(20) NOT NULL | `SUCCESS` \| `FAILURE` \| `EXPIRED` \| `UNAUTHORIZED` |
| `disclosure_level` | VARCHAR(20) NOT NULL | `ZERO_KNOWLEDGE` \| `SELECTIVE` \| `FULL` |
| `proof_commitment` | VARCHAR(128) | ZK commitment hash |
| `requestor_location` | VARCHAR(200) | |
| `latitude`, `longitude` | DOUBLE PRECISION | nullable |

**CHECK constraint** `chk_disclosure_token_consistency`:
- `ZERO_KNOWLEDGE` → `token_id IS NULL`
- `FULL` → `token_id IS NOT NULL`
- `SELECTIVE` — either is permitted

**Trigger:** `trg_verification_append_only` (BEFORE UPDATE OR DELETE)
raises `insufficient_privilege`. Constraint C1.

---

## Operational tables

### `AuthAuditLog`

| column | type |
|---|---|
| `auth_id` | SERIAL PK |
| `username` | VARCHAR(64) NOT NULL FK |
| `event_type` | VARCHAR(20) NOT NULL — `LOGIN_SUCCESS` \| `LOGIN_FAIL` \| `LOGOUT` |
| `ip_address` | INET |
| `event_timestamp` | TIMESTAMP NOT NULL DEFAULT now() |
| `extra` | JSONB |

---

## Records & substrate tables

### `DeviceBinding`

Hardware-token binding records (UC-5). One row per device bound to
a token — phone, watch, tablet — with `binding_method` ∈
{SECURE_ENCLAVE, TITAN_SECURITY, TRUSTED_PLATFORM_MODULE}.

### `BlockchainAnchor`

Optional anchoring of tokens with per-token DID + commitment hash.
`ledger_network` enum restricted to chains with credible post-quantum
migration paths (ALGORAND_PQ, HYPERLEDGER_INDY, CUSTOM_LATTICE). One
row per anchored token. As of v8.21 / R10-2 / M2-2, extended with
`batch_id` (FK to `AnchorBatch`) and `merkle_proof` (JSONB), with a
co-NULL CHECK constraint — pending anchors carry NULL, batched
anchors carry both.

### `AnchorBatch` (M2-2 / R10-2, added v8.21)

Per-batch Merkle commitment of `BlockchainAnchor` leaves. One row per
`close_anchor_batch` invocation. The Polaris schema is the off-chain
audit-of-record (5th instance of the principle — see
`DEVNOTES/audit-of-record.md`); append-only via
`trg_anchor_batch_append_only`. `committed_to_chain` /
`external_chain` / `external_chain_tx` are operator-set future-fields
for the eventual external-PQ-ledger integration. See
`DEVNOTES/ships/anchoring.md`.

### `DuressEvent` (M2-10 / R11-5, added v8.24)

Compulsion-resistance audit-of-record (PDF §9.5). The **8th
audit-of-record instance**. Each row is a detected duress signal —
the holder typed their secondary duress code (a Werkzeug scrypt
hash stored in `IdentityToken.duress_code_hash`) under coercion,
and the verification flow silently fired this alert while the
coercer-visible response page proceeded identically. Append-only
via `reject_audit_modification` trigger.

The `oob_channel` field is the v1/v2 future-field: v1 ships with
`'AUDIT_TABLE'` only; v2 production would integrate SMS/Slack/SIEM.
The `oob_notified_at` field stays NULL until a responder
acknowledges the alert.

R6 anti-revealing posture: the `/verifications` operator dashboard
does NOT join to `DuressEvent`. Only admins/auditors with explicit
access (via `/api/duress/events` or SQL console) can see duress
events. See `DEVNOTES/ships/duress-codes.md`.

### `TokenStateEpoch` (M2-1 / R10-1, added v8.23)

Per-epoch Merkle commitment over the active-token set. The 7th
audit-of-record instance. Append-only via
`enforce_epoch_immutability` — once an epoch is closed, its
`merkle_root` cannot change because every ZK proof issued against it
depends on its immutability. The `valid_until` field bounds proof
validity; the verifier checks this before accepting a proof. The
Merkle root is a Poseidon hash (not SHA3-256 — Poseidon is
SNARK-friendly for the Plonky2 circuit). See `DEVNOTES/ships/zk-snark.md`.

### `TokenStateEpochLeaf` (M2-1 / R10-1, added v8.23)

Per-token witness within an epoch. Each row stores the
(epoch_id, token_id, leaf_hash, proof_path) tuple — the prover
reads its row to generate a ZK proof. Append-only (inherits
`reject_audit_modification`). Unique on (epoch_id, token_id) — one
witness per token per epoch. v1 stores `proof_path` in plaintext;
v2 would encrypt under the holder's key. See `DEVNOTES/ships/zk-snark.md`.

### `AgencyTrustAttestation` (M2-8 / R11-3, added v8.22)

Federation trust graph: directional edges of the form "verifying
agency V accepts issuing agency I for context C, valid until D." The
verification flow consults this table when V ≠ I; same-agency
verification is implicit and requires no row. NO transitive trust —
the lookup is single-row, not transitive-closure (R1 audit
refinement).

The 6th audit-of-record instance — append-only via
`enforce_attestation_immutability`, with bounded mutation limited to
the `(revocation_date, revocation_reason)` pair (set together
one-way, never un-set). Three CHECK constraints:
- `attestation_no_self_attestation` — same-agency rows rejected
- `attestation_validity_floor` — `valid_until > attested_date::DATE`
- `attestation_revocation_consistency` — fields move together;
  revocation_reason ≥ 8 chars

A partial unique index on `(attesting, attested, context_id) WHERE
revocation_date IS NULL` enforces "at most one active attestation per
triple" and serves the read path. Revoked rows fall out of the index
and the audit trail accumulates. v1 ships with operator-logged
attestations (`signed_by AppUser`); v2 path is cryptographic
agency-signed attestations (left out of v8.22 by design — see
`DEVNOTES/ships/federation.md`'s "v1 vs v2 split").

### `GenomicAnchor` (M2-4 / R10-4)

Hash-only commitment to a genomic identifier per token. Three CHECK
constraints enforce the privacy invariant: (1) hash must be hex,
(2) hash length must match the algorithm, (3) hash cannot consist
solely of {A,C,G,T,U,N} characters (i.e., cannot be plaintext
genomic data). See `DEVNOTES/substrate.md`.

### `QuantumObserverBinding` (M2-5 / R10-5, scaffold)

Substrate-level reservation for a quantum-measurement attestation
primitive (Appendix F.2). Every current row has `binding_status =
'SCAFFOLD'` with functional fields NULL. Two CHECK constraints
enforce the SCAFFOLD ↔ OPERATIONAL state transition structurally.
See `DEVNOTES/ships/quantum-observer.md`.

### `IssuerDiscretionPolicy` (M2-11 / R11-6)

Per-agency overrides for the rolling-window revocation rate cap
enforced by `uc8_revoke_token`. Absence of a row for an agency
inherits the system-wide defaults (5.00% / 30 days), set as
`ALTER DATABASE` GUCs in `09_grants.sql`. Three CHECK constraints:
`max_revoke_percent` in (0, 100], `window_days` in [1, 365], and
a `justification` length floor of 20 characters so any loosening
is auditable from the row alone. Implements the PDF §9
*"constitutional limits on issuer discretion"* leg of the
issuer-trust-concentration triad. See `DEVNOTES/ships/issuer-discretion.md`.

### `EnrollmentStatusEvent` (M2-9 / R11-4)

Append-only log of enrollment-state transitions per `Individual`.
Five-status CHECK enum (`NOT_ENROLLED`, `PENDING_ENROLLMENT`,
`ENROLLED`, `EXEMPT`, `LAPSED`). The seed trigger
`trg_seed_default_enrollment_status` emits a `NOT_ENROLLED` event
for every new `Individual` row so the default state is materialized
rather than inferred. The append-only invariant is enforced by the
extension of `reject_audit_modification` to this table. State-machine
sequencing is NOT trigger-enforced — application policy enforces
order where it matters. Implements the PDF §9 *Population coverage*
open problem; see `DEVNOTES/ships/tiered-enrollment.md` for the asymmetric
design rationale (EXEMPT frictionless, mass-NOT_ENROLLED enumeration
deliberate).

The companion view `IndividualCurrentEnrollment` (defined in
`03_view.sql`) returns the latest event per individual with a
`COALESCE` fallback to `NOT_ENROLLED`. The companion function
`civic_enrollment_summary(jurisdiction)` (in `07_queries.sql`)
returns per-jurisdiction × status counts only — per-individual
enumeration of `NOT_ENROLLED` is deliberately not first-class.

### `RecoveryRequest` (M2-7 / R11-2)

Two-phase out-of-band recovery ceremony for catastrophic token loss
(PDF §9.1). Four CHECK constraints encode the mechanism: cool-down ≥
48h (`cooldown_window_minimum`), three OOB channels required for
APPROVED (`approved_requires_three_channels`), decided_at after
cool-down (`approved_after_cooldown`), approver ≠ requester
(`approver_differs_from_requester`). The partial unique index
`uq_one_pending_recovery_per_individual` (in `02_indexes.sql`)
enforces at most one PENDING per individual at a time.

Implements PDF §9.1; the third leg of the *"schema doesn't
weaponize itself against the holder"* triad alongside R11-4 (entry)
and R11-6 (exit). The procedure `uc9_complete_recovery` enforces
admin-only completion (operator initiates, admin decides) and uses
`pg_advisory_xact_lock` on `claimed_individual_id` for C9
correctness. See `DEVNOTES/ships/recovery-ceremony.md` for the adversary
walk and the administrative-vs-operational grace-period framing.

### `TokenSignature` (M2-6 / R11-1)

M:N resolution of `IdentityToken → signature`. A token can carry
signatures from multiple algorithms during a cryptographic-migration
window. `IdentityToken.algorithm_id` is preserved as "originally
issued under" audit metadata; verification reads from
`TokenSignature`. Two triggers enforce the invariants:
`enforce_token_has_active_signature` (every token has ≥ 1
non-deprecated signature at all times) and
`enforce_token_signature_immutability` (write-once except for
one-way `deprecation_date`: NULL → timestamp allowed; un-set or
backdate forbidden).

UNIQUE composite key `(token_id, algorithm_id)` blocks
duplicate-algorithm migrations on a token. The
`uc6_migrate_algorithm` procedure is the single sanctioned path;
it serializes per-token via `pg_advisory_xact_lock`. The partial
index `idx_token_signature_active (token_id) WHERE
deprecation_date IS NULL` keeps verification O(1) effectively even
as the deprecated-history accumulates indefinitely.

Implements PDF §9.4 multi-signature transitional state. Closes the
cryptographic-diversity leg of the issuer-trust-concentration triad
(alongside R11-6 = constitutional limits ✅ and M2-8 = federation,
open). See `DEVNOTES/ships/multi-sig-migration.md` for the adversary
walk and the verification consistency model.

---

## Junction tables

### `AgencyAlgorithmAuth`

Resolves the M:N AUTHORIZED relationship between Agency and
CryptographicAlgorithm. Composite PK (`agency_id`, `algorithm_id`).
`authorization_type` ∈ {ISSUE, VERIFY, BOTH}.

### `TokenPermission`

Resolves the M:N relationship between IdentityToken and
VerificationContext. Composite PK (`token_id`, `context_id`).
Controls which contexts a token is permitted in.

---

## Database functions (`11_atlas.sql`)

These are STABLE functions (no side effects) that drive the
operational atlas API. Constraint C8: each has a `LIMIT` cap that
the caller cannot exceed.

| function | returns | purpose |
|---|---|---|
| `atlas_clusters_verifications(...)` | TABLE | spatial bins of VerificationEvent |
| `atlas_clusters_lifecycles(...)` | TABLE | spatial bins of TokenLifecycleEvent |
| `atlas_points_verifications(...)` | TABLE | individual verification rows |
| `atlas_points_lifecycles(...)` | TABLE | individual lifecycle rows |
| `atlas_stats(...)` | row | HUD signals (active tokens, anomalies, PQ %, ZK %) |
| `atlas_recent_events(limit)` | TABLE | paginated recent feed |
| `atlas_timeline(window, ...)` | TABLE | histogram-strip data for the temporal lens (v8.3) |

All functions use the wrap-aware longitude predicate (v7) so they
work for antimeridian-spanning bboxes. The cluster, points, stats,
and recent-events functions accept optional filter parameters
(`since`, `outcomes`, `disclosure`, `contexts`, `event_types`) added
in v8.3 for server-side filter-chip support.

---

## Mycelium substrate (Arc E / E1 / v8.62)

The 11th audit-of-record instance. Cognitive-layer metadata; carries
no identity-layer payloads.

### `Pheromone`

Mycelium's stigmergic substrate. Each row is one deposit by one ant
onto one brain-map node. Append-only via `trg_pheromone_append_only`
(rejects UPDATE and DELETE). Decay is computed at READ time via
`effective_intensity = intensity * exp(-ln(2) * age_hours / half_life_hours)` —
the table never stores decayed values, so the audit-of-record is
preserved verbatim.

Columns:

- `pheromone_id` — SERIAL primary key
- `deposited_at` — TIMESTAMP, default NOW()
- `deposited_by` — ant module name (e.g. `ant_api_doc_coverage`)
- `node_id` — brain-map node id (e.g. `route:/api/zk/verify`)
- `intensity` — NUMERIC(6,3), `0 < x <= 10`, the raw deposit strength
- `kind` — `drift` | `alert` | `info` | `curious`
- `half_life_hours` — NUMERIC(6,2), default 24.0, max 720 (30 days)
- `evidence` — JSONB, ant-specific payload (`{message, file, fix_hint, ...}`)
- `seed` — BIGINT, ant's deterministic seed for replay

Indexes: `idx_pheromone_recent` (deposited_at DESC),
`idx_pheromone_by_node` (node_id, deposited_at DESC),
`idx_pheromone_by_ant` (deposited_by, deposited_at DESC).

Read it via `scripts/ai-swarm-bloom.sh`. Authorized by
`sanctum/2026-05-13-arc-e-swarm-intelligence-opening.md`.

### `LifecycleArchiveCheckpoint` (Arc B Phase 2b / v8.87)

Audit-of-record for archive-then-delete purges (the
constitutional carve-out closed by
`sanctum/2026-05-14-audit-log-deletion-from-hot.md`, Position B).
Every successful `uc_archive_purge()` invocation appends exactly
one row here.

```
checkpoint_id              BIGSERIAL PRIMARY KEY
purged_at                  TIMESTAMPTZ  NOT NULL DEFAULT now()
cutoff_timestamp           TIMESTAMPTZ  NOT NULL  -- older-than threshold for the purge
archive_uri                VARCHAR(512) NOT NULL  -- operator-set; opaque to the schema
archive_sha256             VARCHAR(64)  NOT NULL  -- 64-char hex; CHECK-enforced
actor_user_id              INTEGER      NOT NULL  -- AppUser.user_id (must have role='admin')
rows_purged_lifecycle      INTEGER      NOT NULL DEFAULT 0
rows_purged_verification   INTEGER      NOT NULL DEFAULT 0
rows_purged_enrollment     INTEGER      NOT NULL DEFAULT 0
rows_purged_authaudit      INTEGER      NOT NULL DEFAULT 0
rows_purged_anchorbatch    INTEGER      NOT NULL DEFAULT 0    -- always 0 in v8.87 (Phase 2c)
rows_purged_attestation    INTEGER      NOT NULL DEFAULT 0    -- always 0 in v8.87 (Phase 2c)
rows_purged_duress         INTEGER      NOT NULL DEFAULT 0    -- always 0 in v8.87 (Phase 2c)
rows_purged_total          INTEGER      NOT NULL DEFAULT 0

CHECK (archive_sha256 ~ '^[0-9a-fA-F]{64}$')   -- archive_sha256_is_hex
CHECK (cutoff_timestamp <= now())              -- cutoff_in_past
CHECK (rows_purged_total >= 0)                 -- rows_purged_total_nonneg
```

**Append-only at full strictness (G30).** The trigger
`trg_checkpoint_append_only` (function:
`reject_checkpoint_modification`) rejects every UPDATE and
DELETE unconditionally — no GUC carve-out applies at this layer
because the checkpoint chain IS the audit-of-record for the
deletion carve-out.

**Privacy claim preserved** (`docs/operator/PRIVACY.md` §
Append-only audit): any purge produces an append-only checkpoint
row, so attempted tidying still leaves a permanent record.

---

## Stored procedures (`05_procedures.sql`)

The state-changing operations of the system. Each maps to a use case.
Each sets the `polaris.*` GUCs before its UPDATE so the audit trigger
captures the actor and reason.

See `API.md` for the use case → procedure mapping.

---

## Operational support (not tables)

Some operator concerns map to columns or views rather than
dedicated tables. The structural invariant
`test_no_phantom_tables_in_doc` catches doc-only mentions of
tables that don't exist; this section names the affordances
explicitly so operators don't go looking for the wrong shape.

- **Biometric enrollment** is *not* a separate table. The
  binding *type* (FINGERPRINT, FACE, IRIS) lives as a column on
  the relevant token / device-binding rows; the template itself
  never enters Polaris (lives on-device). See
  `docs/operator/PRIVACY.md` § "About holders (Individuals)".
- **Operator-lockout state** is *not* a separate table. The
  brute-force-defense counters live as columns on `AppUser`
  (`failed_login_count`, `locked_until`). Cleared on successful
  auth or admin reset.
- **Per-issuance provenance** is recorded via
  `TokenLifecycleEvent` (with `event_type = 'ISSUED'`) plus
  `IdentityToken.issuing_agency_id` + `algorithm_id`. There is
  no separate issuance-record table; the lifecycle stream is
  authoritative for birth context.
- **Substrate dependencies** (M2-3 / v8.5) live in the
  `SystemDependency` **view** (not table), defined in
  `polaris_sql/13_substrate.sql`. Queryable via `SELECT * FROM
  SystemDependency`; mirrors `DEVNOTES/substrate.md`.

---

## Filesystem audit-of-record (Arc E / Arc F)

Three filesystem-AoR instances complement the schema's 9. They
live outside the database because they describe the cognitive
layer's own state rather than the identity-system state.

### `sanctum/*.md` — Strategic-consultation sessions

Each Sanctum is a structured Markdown file with sections
(Matter / Phase scope / Design / Recommendation / Alternatives /
Decision / Outcome). Filename:
`sanctum/<YYYY-MM-DD>-<topic-slug>.md`. Lifecycle status is
embedded as `**Status:** DECIDED | CLOSED | OPEN | REJECTED |
PARKED`. Index: `meta/sanctum-index.md` (regenerated by
`ai-sanctum.sh close`).

**Audit invariant:** Sanctums are never deleted. A REJECTED or
PARKED Sanctum stays on file as the record of the decision
*not* to do something.

### `polaris_swarm/civitas/treasury-roll.json` — Denarii ledger

Arc F / v8.68. Every Treasury event (reward, penalty,
multiplier-engagement) appended as a JSON record. The treasury
in-memory state is reconstructed from this ledger on reload.

### `polaris_swarm/civitas/census-roll.json` — Citizen registry

Arc E / v8.66. Every citizen activation/recognition event
appended as a JSON record. Records when ants/citizens come
online; supports ant-churn surfacing.

---

## Migration policy

There are no `up`/`down` migration scripts yet (BACKLOG schema
section). Schema reload is via `polaris_sql/00_load_all.sql` which
runs `DROP TABLE … CASCADE` and reloads from scratch — destructive.
Production deployments that need non-destructive migrations should
introduce versioned migrations (Alembic-style) before going live.

The test database (`polaris_test`) is reloaded fresh on every test
run via `_test_reload_sample_data()`.
