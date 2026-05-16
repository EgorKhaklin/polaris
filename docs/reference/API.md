# API.md — endpoint reference

Polaris exposes two API surfaces: the HTML routes (server-rendered
operator UI) and the JSON API (`/api/...`). This document covers the
JSON API; HTML routes are documented in their templates and in
`README.md`.

All `/api/*` endpoints except `/api/health` require authentication
via the session cookie established by `POST /login`.

---

## Authentication

### `POST /login`

Form-encoded:

| field | type | required |
|---|---|---|
| `username` | string | yes |
| `password` | string | yes |
| `csrf_token` | string | yes (in form) |

On success: 302 to `/`. On failure: 200 with the form re-rendered;
`failed_login_count` increments atomically (constraint C4).

After 5 failed attempts in a sliding window the account is locked
for 15 minutes. To unlock administratively:

```sql
UPDATE AppUser
SET locked_until = NULL, failed_login_count = 0
WHERE username = '...';
```

### `POST /logout`

Invalidates the session.

---

## Health

### `GET /api/health`

**No authentication required.** Consumed by Caddy's upstream
health check, load-balancer probes, and external uptime monitors.

Structured JSON contract (G29 / v8.77 / Arc B Phase 1):

```json
{
  "status": "healthy",
  "version": "8.77",
  "uptime_seconds": 3600,
  "checks": {
    "database": {"status": "healthy", "latency_ms": 4, "table_count": 25},
    "redis":    {"status": "healthy", "backend": "redis", "latency_ms": 1},
    "zk_binary": {"status": "healthy", "path": "/opt/polaris/zk", "version": "0.2.0"},
    "disk":     {"status": "healthy", "free_gb": 42.7, "used_pct": 23.1},
    "atlas_cache": {"status": "healthy", "entries": 8, "hits": 142, "misses": 23}
  },
  "timestamp": "2026-05-14T12:34:56.789Z"
}
```

**Top-level fields:**

| Field | Type | Meaning |
|---|---|---|
| `status` | string | Overall = worst per-component status. One of `healthy` / `degraded` / `unhealthy` |
| `version` | string | `POLARIS_VERSION` constant in `app.py` |
| `uptime_seconds` | int | Seconds since the Python module was imported |
| `checks` | object | Per-component status reports (see below) |
| `timestamp` | string | ISO 8601 UTC with millisecond precision and `Z` suffix |

**Per-component checks:**

| Component | Healthy means | Degraded means | Unhealthy means |
|---|---|---|---|
| `database` | round-trip <500ms; ≥20 tables found | round-trip >500ms or 1-19 tables | unreachable or 0 tables |
| `redis` | rate-limiter backend reachable; or in-memory backend (always healthy) | Redis backend unreachable (allow() fails closed) | (not used today; redis failure is degraded) |
| `zk_binary` | binary exists, executable, `--version` returns within 2s | binary missing, not executable, or `--version` timed out | (not used today; ZK absence is degraded) |
| `disk` | <85% used AND >5GB free | <85% used but <5GB free, OR >85% used | <500MB free |
| `atlas_cache` | always healthy (informational only) | n/a | n/a |

`atlas_cache` does NOT contribute to the overall status — it's
preserved for backwards compatibility with operational
dashboards that were built against the v7.5 contract.

**Status codes:**

- `200` — overall status is `healthy` or `degraded`
- `503` — overall status is `unhealthy` (at least one critical
  check is unhealthy)

**Enforced structurally by:** G29 /
`test_g29_health_endpoint_contract` in
`polaris_web/test_structural_invariants.py`.

**Operator guidance:** see
[`docs/operator/OPERATIONS.md` § Monitoring](../operator/OPERATIONS.md#monitoring--alerting)
for the recommended alert thresholds.

---

## Atlas API

The atlas API (`/api/atlas/*`) supports the operational situational-
awareness page. All endpoints take a `bbox` query parameter:
`min_lat,min_lon,max_lat,max_lon` (decimal degrees).

Antimeridian-spanning bboxes (where `min_lon > max_lon`) are
supported; they cover `[min_lon, 180] ∪ [-180, max_lon]`.

All endpoints have hard caps (constraint C8). Responses past the cap
are silently truncated; the caller cannot bypass.

### `GET /api/atlas/clusters`

Spatial aggregation over a grid.

| param | type | default | notes |
|---|---|---|---|
| `bbox` | csv-floats | required | min_lat,min_lon,max_lat,max_lon |
| `grid` | float | `5` | grid size in decimal degrees, ∈ (0, 90] |
| `kind` | enum | `verification` | `verification` \| `lifecycle` |

Response (verification kind):

```json
{
  "kind": "verification",
  "bbox": [10, 20, 30, 40],
  "grid": 5.0,
  "count": 12,
  "clusters": [
    {"lat": 12.5, "lon": 22.5, "n_total": 145, "n_failure": 3,
     "n_pq": 142, "n_zk": 21, "n_full": 18}
  ]
}
```

Cap: `_ATLAS_MAX_CLUSTERS = 5000`. Cached for `_ATLAS_CACHE_TTL_SECONDS`
(default 30s); R8-5.

### `GET /api/atlas/points`

Individual events in the bbox. Used at high zoom when cluster count
falls below the cluster→point threshold.

| param | type | default | notes |
|---|---|---|---|
| `bbox` | csv-floats | required | as above |
| `limit` | int | `500` | clamped to `_ATLAS_MAX_POINTS = 2000` |
| `kind` | enum | `verification` | as above |

Response shape mirrors clusters but with `points` array instead.

### `GET /api/atlas/stats`

Four HUD signals scoped to the visible bbox.

```json
{
  "bbox": [-90, -180, 90, 180],
  "n_active_tokens": 1932451,
  "n_anomalies": 12,
  "n_failures": 1453,
  "n_full": 7,
  "pq_pct": 99,
  "zk_pct": 11,
  "n_verifs": 1942000,
  "n_lifecycles": 17234
}
```

Cached; R8-5.

### `GET /api/atlas/events`

Paginated event feed for the right rail. Cursor pagination supported
via `?cursor=…`.

### `GET /api/atlas/timeline`

Histogram-strip bucket counts below the toolbar. Returns
`{ts, n_total, n_anomaly}` points over a `?window=` range with
`?buckets=N` slices (hard-capped at 240). Honors the same
outcome/disclosure/context/event_types filters as
`/api/atlas/clusters`. Added v8.50; covered by PerformanceWatcher.

### `GET /api/atlas/cache-stats`

Cache observability for R8-5. Returns hit/miss/expired/evicted
counters and current cache size.

```json
{
  "ttl_seconds": 30.0,
  "max_entries": 256,
  "current_entries": 12,
  "hits": 142,
  "misses": 23,
  "expired": 4,
  "evicted": 0,
  "hit_ratio": 0.860
}
```

---

## Verification API (use cases UC-1 through UC-8)

Each use case is reachable through the operator UI (HTML form) AND
through a corresponding stored procedure callable via the
`/verifications/new` POST endpoint.

### `POST /verifications/new`

Records a verification event. Form-encoded:

| field | type | required | notes |
|---|---|---|---|
| `token_id` | int | conditional | required for SELECTIVE/FULL; MUST be empty for ZERO_KNOWLEDGE |
| `requesting_agency_id` | int | yes | |
| `context_id` | int | yes | |
| `disclosure_level` | enum | yes | `ZERO_KNOWLEDGE` \| `SELECTIVE` \| `FULL` |
| `outcome` | enum | yes | `SUCCESS` \| `FAILURE` \| `EXPIRED` \| `UNAUTHORIZED` |
| `latitude`, `longitude` | float | optional | |
| `csrf_token` | string | yes | |

The form coerces `token_id` to NULL when `disclosure_level=ZERO_KNOWLEDGE`
(constraint C2 client-side); the CHECK constraint enforces it
server-side regardless.

### Stored procedures (see `polaris_sql/05_procedures.sql`)

| Use case | Procedure | Purpose |
|---|---|---|
| UC-1 | `issue_token(...)` | Issue a new token |
| UC-2 | `verify_token(...)` | Record verification event |
| UC-3 | `bind_device(...)` | Bind hardware device to token |
| UC-4 | `revoke_token(...)` | Revoke (terminal) |
| UC-5 | `report_lost(...)` | Report lost (terminal) |
| UC-6 | `lookup_active_for(individual_id)` | Lookup the holder's active token |
| UC-7 | `succession(...)` | Issue successor; predecessor stays in DB |
| UC-8 | `uc8_revoke_token(...)` | **Bounded revocation** — see below |

All procedures use `SECURITY INVOKER`. The audit trigger on
`IdentityToken` reads `polaris.actor_agency_id`,
`polaris.reason_code`, `polaris.event_lat`, `polaris.event_lon` GUCs;
procedures set them via `SET LOCAL`.

### `POST /uc8/revoke` (UC-8, R11-6 / M2-11)

The single sanctioned revocation path. Wraps `uc8_revoke_token`:
serializes per-issuing-agency via `pg_advisory_xact_lock`, enforces
the rolling-window N%/W-day cap, validates the optional co-signer,
transitions the token to `REVOKED`, and inserts into
`RevocationList` in the same transaction.

| field | type | required | notes |
|---|---|---|---|
| `token_id` | int | yes | must be in a non-terminal state |
| `actor_agency_id` | int | yes | the agency performing the revocation |
| `reason_code` | enum | yes | `COMPROMISED`/`LOST`/`STOLEN`/`SUPERSEDED`/`ADMINISTRATIVE`/`DEATH` |
| `published_location` | string | yes | URL where the CRL entry will be reachable (max 300 chars) |
| `cosigner_agency_id` | int | conditional | required when the rate would exceed the bound; must differ from actor; must hold `BOTH` on the token's algorithm |
| `csrf_token` | string | yes | |

Errors (PostgreSQL SQLSTATE):

- `23514` `check_violation` — rate exceeds bound, no co-signer.
- `42501` `insufficient_privilege` — raw UPDATE that bypassed the
  procedure (caught by the belt-and-suspenders trigger).
- Free-form RAISE EXCEPTION — invalid co-signer, already-terminal
  token, missing authorization.

See `DEVNOTES/ships/issuer-discretion.md` for the policy choices (N=5.00%,
W=30 days defaults; per-agency overrides via
`IssuerDiscretionPolicy`).

### `GET /individuals/enrollment` (R11-4 / M2-9)

Civic enrollment summary. Returns per-jurisdiction × status counts of
individuals in each enrollment state. Implements the PDF §9
*Population coverage* "civic queries can answer 'is this person known'
without requiring an active token" requirement at the aggregate level.

| query param | type | required | notes |
|---|---|---|---|
| `jurisdiction` | string | optional | ISO 3166-2 jurisdiction filter (e.g., `US-PA`); omit for all jurisdictions |

The page renders a pivot table (jurisdiction down the side, status
across the top) plus the five-status vocabulary glossary.
Per-individual enumeration of `NOT_ENROLLED` is deliberately NOT
exposed as a route — an admin who needs it writes the join against
`IndividualCurrentEnrollment` directly, which leaves an
`AuthAuditLog` trace.

See `DEVNOTES/ships/tiered-enrollment.md` for the asymmetric-design
rationale.

### UC-9 routes (R11-2 / M2-7)

Two-phase out-of-band recovery ceremony for catastrophic loss
(PDF §9.1). Implements the third leg of the "schema doesn't
weaponize itself against the holder" triad.

#### `POST /uc9/initiate-recovery`

Phase 1. Operator or admin role required. INSERT a PENDING
RecoveryRequest. Rejects if the individual has an ACTIVE token
(UC-4 is the right path) or already has a PENDING recovery.

| field | type | required | notes |
|---|---|---|---|
| `individual_id` | int | yes | claimant; must have no ACTIVE token |
| `requesting_agency_id` | int | yes | agency initiating the recovery |
| `csrf_token` | string | yes | |

The requesting `user_id` is taken from the session (the
authenticated operator).

#### `GET /uc9/queue`

Read-only queue of all recovery requests (PENDING first, then
terminal states). Any authenticated role can view; only admin can
act on PENDING rows. Renders the three OOB channels (Biometric /
Sworn statement / Witness agency) as compact tick indicators.

#### `POST /uc9/decide/<recovery_id>`

Phase 2. **Admin role required.** Belt-and-suspenders: enforced at
the Flask route AND inside `uc9_complete_recovery` via RAISE
EXCEPTION on non-admin.

| field | type | required | notes |
|---|---|---|---|
| `decision` | enum | yes | `APPROVED` \| `REJECTED` |
| `reason` | text | optional | free-text justification |
| `new_token_value`, `new_serial`, `algorithm_id`, `biometric_binding`, `liveness_check`, `published_location` | various | required if APPROVED | new-token specification |
| `csrf_token` | string | yes | |

Errors:

- `42501` `insufficient_privilege` — deciding user lacks admin role.
- `23514` `check_violation` — cool-down not expired, three channels
  not present, or approved/cool-down arithmetic violation.
- Free-form RAISE EXCEPTION — recovery not PENDING (already
  decided), approver = requester, missing new-token parameters on
  APPROVED.

See `DEVNOTES/ships/recovery-ceremony.md` for the full adversary walk and
mechanism design.

### `POST /uc6/migrate` (R11-1 / M2-6)

Algorithm migration via the multi-signature scheme. Adds a new
`TokenSignature` row under a new algorithm; optionally deprecates
existing active signatures on the same token. Closes the
cryptographic-diversity leg of the PDF §9 issuer-trust-concentration
triad. Implements PDF §9.4.

| field | type | required | notes |
|---|---|---|---|
| `token_id` | int | yes | must be RESERVE or ACTIVE |
| `new_algorithm` | int | yes | must not already be present on this token (UNIQUE blocks dupes); must not itself be deprecated |
| `deprecate_old` | bool | optional | when checked, sets `deprecation_date` on every other active signature for this token |
| `csrf_token` | string | yes | |

The signature bytes are inserted as a deterministic placeholder
(reference implementation). Production deployments would derive
`signature_bytes` from a hardware-attested signing ceremony.

Errors:

- `23505` `unique_violation` — token already has an active signature
  under the requested algorithm.
- Free-form RAISE EXCEPTION — token does not exist, algorithm does
  not exist or is itself deprecated.
- `42501` `insufficient_privilege` — direct UPDATE/DELETE on
  `TokenSignature` that bypasses the procedure.

See `DEVNOTES/ships/multi-sig-migration.md` for the verification
consistency model and the no-auto-derivation argument.

---

## Token CRUD (admin)

### `GET /tokens`, `GET /tokens/<id>`, `POST /tokens/new`, `POST /tokens/<id>/edit`, `POST /tokens/<id>/delete`

Standard CRUD. Edit only allowed for the columns that are not
covered by a state-machine transition; status changes go through the
state-machine trigger (`enforce_token_state_machine`) which rejects
illegal transitions.

DELETE is allowed only for RESERVE and DORMANT tokens that have no
TokenLifecycleEvent rows referencing them (no audit trail to
preserve). Tokens with audit history cannot be deleted; mark them
REVOKED instead.

---

## Anchor batch API (R10-2 / M2-2 — v8.21)

Three endpoints back the DID-anchoring Merkle batch layer. The Polaris
schema is the off-chain audit-of-record; an external PQ-capable
ledger is an optional operator-discretion destination for the
committed Merkle root. See `DEVNOTES/ships/anchoring.md` for the design
write-up.

### `POST /api/anchor/batch` (admin)

Closes a Merkle batch for the pending `BlockchainAnchor` rows of a
given signature algorithm. The Python helper `polaris_web/anchoring.py`
computes the root + per-leaf proofs; the SQL procedure
`close_anchor_batch` holds a per-algorithm advisory lock for the
transaction, inserts the `AnchorBatch` row, and fills `batch_id +
merkle_proof` on every matched anchor.

Request:

```json
{"algorithm_id": 1}
```

Response:

```json
{
  "batch_id": 3,
  "merkle_root": "c0c80566eb6e53e48717eb10de4e742a2c79795a093d9877c80243578a15cd1f",
  "batch_size": 1
}
```

Errors: `400` if `algorithm_id` is missing or not an int; `404` if
no pending anchors exist for that algorithm; `400` with a sanitized
message for any constraint or procedure-level rejection (unknown
algorithm, deprecated algorithm, 10,000-leaf cap exceeded).

### `GET /api/anchor/<token_id>`

Returns the `BlockchainAnchor` row plus its `AnchorBatch` (if
batched) for the given token. Useful when a client needs the root +
proof to verify off-line.

Response (batched anchor):

```json
{
  "anchor_id": 1,
  "token_id": 2,
  "did": "did:polaris:algopq:1z9f...",
  "commitment_hash": "0x3f8a...",
  "ledger_network": "ALGORAND_PQ",
  "anchored_date": "2026-01-23T11:00:00",
  "status": "ACTIVE",
  "batch_id": 1,
  "merkle_proof": [],
  "merkle_root": "1944806ae3e8a2aa72659d909f7e43fe043714a920491eff05ba0a33e30bc5c8",
  "batch_algorithm_id": 1,
  "committed_to_chain": false,
  "external_chain": null,
  "external_chain_tx": null
}
```

Returns `404` if the token has no `BlockchainAnchor` row.

### `GET /api/anchor/verify/<token_id>`

Server-side proof verification: reconstructs the Merkle root from
the stored leaf + proof and compares it to the claimed root on the
`AnchorBatch` row. A tampered log (e.g., somebody flipped a byte in
`BlockchainAnchor.commitment_hash` post-batch) fails verification.

Response (success):

```json
{
  "verified": true,
  "anchor_id": 1,
  "batch_id": 1,
  "merkle_root": "1944806a...",
  "leaf": "1944806a..."
}
```

Response (pending — not yet batched):

```json
{
  "verified": false,
  "status": "PENDING",
  "anchor_id": 7
}
```

Returns `404` if the token has no `BlockchainAnchor` row.

---

## Federation API (R11-3 / M2-8 — v8.22)

Two endpoints manage the federation trust graph (`AgencyTrustAttestation`).
Both are admin-only and CSRF-protected. The federation flow is described in
`DEVNOTES/ships/federation.md`.

### CSRF for JSON callers

v8.22 added `X-CSRFToken` header support to `validate_csrf`
(`security.py`). JSON / AJAX callers should:

1. Issue an authenticated GET to any page rendering a CSRF-protected
   form (e.g., `/verifications/new`) to populate the session's
   `csrf_token`.
2. Read the value from a form input or from the session.
3. POST to `/api/federation/*` with the JSON body, setting the
   request header `X-CSRFToken: <the token>`.

Form fields still work the same way: include `csrf_token` in form-data
and the standard validation path picks it up.

### `POST /api/federation/attest` (admin)

Records a federation trust edge: "Agency V (attesting) accepts Agency
I (attested) for context C, valid until D." Wraps `uc10_attest_trust`,
which holds a per-attesting-agency advisory lock (5th catalog entry).

Request body:

```json
{
  "attesting_agency_id": 4,
  "attested_agency_id":  1,
  "context_id":          4,
  "valid_until":         "2027-01-15"
}
```

Response:

```json
{"attestation_id": 7, "status": "active"}
```

Errors:
- `400` — required fields missing / unknown agencies or context / signer not admin / zero-or-negative-duration validity / duplicate active attestation for this triple
- `401` — session missing user_id (should not happen if `login_required` decorator ran)
- `403` — operator role lacks federation-attestation privilege

### `POST /api/federation/revoke` (admin)

Revokes an active attestation. The revocation is forward-looking
(C1-aligned): past `VerificationEvent` rows that occurred while the
attestation was active are NOT retroactively invalidated.

Request body:

```json
{
  "attestation_id":    7,
  "revocation_reason": "ALGORITHM_COMPROMISE"
}
```

Note: `revocation_reason` must be ≥ 8 characters (enforced by the
`attestation_revocation_consistency` CHECK constraint). A shorter
reason returns `400`.

Response:

```json
{"attestation_id": 7, "status": "revoked"}
```

Errors:
- `400` — required fields missing / attestation already revoked / reason too short
- `403` — operator role lacks federation-revocation privilege
- `404` — attestation_id does not exist

### Federation check at verification time

The `POST /verifications/new` endpoint silently consults the
attestation graph for SUCCESS outcomes (admin / operator). A token
whose issuing agency is not trusted by the verifying agency for the
given context is rejected with a flash message; the operator must
either record outcome=UNAUTHORIZED (which proceeds normally) or create
the missing attestation. See the federation check helper
`_federation_trust_holds()` in `app.py`. NO transitive trust: the
helper inspects exactly one row in `AgencyTrustAttestation`.

---

## Duress code API (R11-5 / M2-10 — v8.24)

Compulsion-resistance per PDF §9.5. The `DuressEvent` table is the
8th audit-of-record. See `DEVNOTES/ships/duress-codes.md` for the full
write-up.

The main interaction is implicit: when the holder types a duress
code into `POST /verifications/new`'s optional `duress_code` field,
the system silently records a DuressEvent if the code matches the
token's enrolled `duress_code_hash` (Werkzeug constant-time
comparison). The coercer-visible response is identical to a normal
verification (R2 audit refinement — identical observable behavior).

### `GET /api/duress/events` (admin/auditor)

Returns up to 200 recent duress events. **NOT** accessible to the
operator role — R6 anti-revealing posture means only admins and
auditors can see the duress dashboard.

Response:

```json
{
  "count": 1,
  "events": [{
    "event_id": 1,
    "token_id": 2,
    "holder_name": "Maria Santos",
    "context_type": "BANKING",
    "verifying_agency": "First National Bank",
    "event_timestamp": "2026-05-11 12:34:56",
    "oob_channel": "AUDIT_TABLE",
    "oob_notified_at": null,
    "acknowledged": false
  }]
}
```

### `POST /api/duress/record` (admin/operator)

Direct-call recording endpoint, used by tests and automation.
The normal flow is for `verifications_new` to call this silently on
duress-code match; this route exists for explicit-record use cases.

Request body:

```json
{
  "token_id": 2,
  "context_id": 1,
  "requesting_agency_id": 5
}
```

Response:

```json
{"event_id": 1}
```

Errors:
- `400` — required fields missing or token has no enrolled duress code
- `403` — auditor role lacks write privilege

### Duress flow at the verification path

When `POST /verifications/new` is called with an optional `duress_code`
field set:

1. The verification path runs normally (federation check, SUCCESS
   gating, etc.) — completely identical to a non-duress call.
2. If `token_id` is set AND the token has a non-NULL
   `duress_code_hash` AND `werkzeug.security.check_password_hash`
   matches: `uc12_record_duress` is invoked, writing a row to
   `DuressEvent`.
3. The user-visible response is identical to step 1 — same flash,
   same redirect, same `VerificationEvent` row.

The duress mechanism is purely additive: the coercer cannot
distinguish a duress signal from a normal verification.

---

## ZK-SNARK API (R10-1 / M2-1 — v8.23)

Plonky2-backed Merkle-inclusion proofs over `TokenStateEpoch`
snapshots. The Rust prover lives in `polaris_zk/`; this layer is the
schema + route bridge. See `DEVNOTES/ships/zk-snark.md` for the full
write-up.

### `POST /api/zk/epoch/close` (admin)

Closes a ZK epoch: snapshots currently-valid `ACTIVE` tokens with
their `TokenPermission` for the given context, derives per-token
leaf seeds, computes the Merkle root via the Rust prover, and
calls `uc11_close_epoch` (per-procedure advisory lock — 6th catalog
entry; v8.23).

Request body:

```json
{
  "context_id": 42,
  "valid_until": "2026-06-30 23:59:59"
}
```

Response:

```json
{
  "epoch_id": 17,
  "merkle_root": "a1b2c3...",
  "committed_count": 142
}
```

Errors: `400` on missing/invalid fields or DB constraint violation;
`404` if no eligible tokens for the given context; `401` if session
is missing `user_id`.

### `GET /api/zk/epoch/<epoch_id>`

Returns the `TokenStateEpoch` row for inspection (no witness data
disclosed). Used by the operator UI to show epoch state and check
`valid_until`.

Response:

```json
{
  "epoch_id": 17,
  "merkle_root": "a1b2c3...",
  "valid_from": "2026-05-13 14:00:00",
  "valid_until": "2026-06-30 23:59:59",
  "committed_count": 142,
  "closed_at": "2026-05-13 14:01:23",
  "closed_by_user_id": 1
}
```

### `POST /api/zk/verify`

Verifies a ZK-SNARK proof bundle against a specified
`(epoch_id, context_id, nonce)`. The caller supplies the proof
bundle from a prover; the verifier (1) loads the epoch's
`merkle_root` from `TokenStateEpoch`, (2) checks
`valid_until >= now()` (R4 epoch-boundary), and (3) invokes the
Rust verifier via `zk.verify_proof_against_epoch`.

Request body:

```json
{
  "epoch_id": 17,
  "context_id": 42,
  "nonce": 1234567890,
  "proof": { ... }
}
```

Response: `{"valid": true}` or `{"valid": false, "reason": "..."}`.
CSRF-protected.

---

## Error semantics

All `/api/*` JSON endpoints return errors as:

```json
{"error": "human-readable message"}
```

Error messages are sanitized through `db_error_to_message()` in
`security.py`; raw psycopg2 errors are NOT surfaced (constraint
mitigates I-I3 in `DEVNOTES/threat-model.md`).

Status codes:
- `200` — success
- `400` — bad input (validation failure)
- `401` — not authenticated
- `403` — authenticated but insufficient role
- `429` — rate limited
- `500` — server error (sanitized)

---

## Rate limits

| route pattern | limit |
|---|---|
| `POST /login` | 5 / 60s per IP |
| `POST /verifications/new` | 60 / 60s per session |
| `POST /tokens/*` | 60 / 60s per session |
| `GET /api/atlas/*` | 600 / 60s per session |
| `GET /api/health` | unlimited |

Limits are in-process (per gunicorn worker). A multi-worker
deployment that needs precise limits should switch to the Redis
backend (R8-2 — backlog).

---

## Versioning

There is currently no `/api/v1/` prefix. Adding versioning is on the
backlog (`docs/BACKLOG.md` API section). When introduced, the current
unprefixed routes will alias to `/api/v1/...` for compatibility.

---

## Updating this document

When a new `/api/*` route is added or an existing one's signature
changes, update this file in the same change. The pre-commit hook
(`docs/BACKLOG.md` tooling section) checks that `/api/*` routes in `app.py`
are documented here.

---

## Internal endpoints (operator UI plumbing)

These endpoints support the Polaris operator UI and the macOS launcher.
They are NOT intended for external consumption.

### `POST /api/heartbeat`

Returns the timestamp of the most recent operator activity. Used by
the launcher's `--watch` mode to detect idle.

### `GET /api/since-heartbeat`

Returns seconds elapsed since the last `/api/heartbeat` call.

### `POST /api/quit`

Graceful shutdown. Authenticated; admin-only. Used by the launcher's
"quit polaris" button.
