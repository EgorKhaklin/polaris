# PRIVACY.md

How Polaris handles personal information. This is distinct from
`SECURITY.md` (which covers attacks) and `DEVNOTES/threat-model.md`
(which covers the architectural defenses). PRIVACY focuses on what
data is collected, what's retained, how the architecture enforces
minimization, and what users (or holders) can expect.

---

## What Polaris collects

### About holders (Individuals)

| Data | Purpose | Retention |
|---|---|---|
| `legal_name` | Identity attestation | Permanent (audit invariant C1) |
| `date_of_birth` | Identity attestation | Permanent |
| `country_code` | Jurisdiction routing | Permanent |
| `external_ref` | Cross-reference to upstream | Permanent (optional column) |

These are the irreducible minimum to issue an identity token. No
biometric data is stored in the schema (only the type of binding,
e.g. "FINGERPRINT" — the template lives on the device, not in
Polaris).

### About operators (AppUsers)

| Data | Purpose | Retention |
|---|---|---|
| `username` | Authentication | Until account removed |
| `password_hash` (argon2id) | Authentication | Until rotation |
| `role` | Authorization | Until role change |
| `agency_id` | Scope of access | Until reassignment |
| `failed_login_count`, `locked_until` | Brute-force defense | Cleared on successful login or admin reset |

Operator data is operational and rotatable. A removed operator's
authentication state is removed; their agency-attributed audit
events stay (the action is permanent, even when the actor is gone).

### About events

| Event type | What's recorded | Retention |
|---|---|---|
| `TokenLifecycleEvent` | token_id, agency, type, timestamp, reason, geo (optional) | Permanent (C1) |
| `VerificationEvent` (FULL) | token_id, requesting agency, context, timestamp, geo | Permanent (C1) |
| `VerificationEvent` (SELECTIVE) | token_id, requesting agency, context, timestamp, geo, attribute set | Permanent (C1) |
| `VerificationEvent` (ZERO_KNOWLEDGE) | requesting agency, context, timestamp, geo | Permanent (C1) — note `token_id IS NULL` (C2) |
| `AuthAuditLog` | username, event_type, ip_address, timestamp | Permanent for non-repudiation |

The audit invariant (C1) means events are permanent. This is a
deliberate trade-off: the system's repudiation defense (R-R1, R-R2
in `DEVNOTES/threat-model.md`) requires that events cannot be
deleted, even at the holder's request.

---

## What Polaris does NOT collect

- **Biometric templates.** The biometric is bound at the device
  level; Polaris stores only the binding type (FINGERPRINT, FACE,
  IRIS) and the enrollment date.
- **Holder addresses, phone numbers, email.** Not in the schema.
  If an upstream system needs these, they live there, not here.
- **Verification request payloads.** A verification records THAT
  it happened, not what was inside. The relying party stores its
  own request data.
- **Browser fingerprinting / tracking pixels / cookies beyond the
  Flask session cookie.** No analytics, no third-party scripts (CSP
  enforces this, C5).
- **Real-time geolocation.** Latitude/longitude are recorded for
  events at the time of the event for audit purposes. Holders are
  not tracked between events.

---

## Architectural enforcement of minimization

Polaris's architecture makes some forms of data leakage
structurally impossible:

### ZERO_KNOWLEDGE verifications

Constraint C2 enforces that ZK events have `token_id IS NULL`. The
verification graph for ZK events cannot be reconstructed from the
event log — there's no link back to the holder. This is enforced
at three layers:

1. **Trigger** (`enforce_zk_typing`) rejects writes that violate
2. **CHECK constraint** at the column level
3. **Form coercion** at the application layer

Even a malicious DBA cannot insert ZK events with a token_id; the
trigger raises before commit.

### Append-only audit

Constraint C1 makes lifecycle and verification events immutable.
This is the basis for non-repudiation — but it's also the basis for
a privacy claim: an operator cannot "tidy up" a holder's history
without leaving a permanent record of the attempted tidying.

**Encryption at rest (v8.93):** the production stack supports
encryption at rest at the storage layer via LUKS on bare-metal,
TDE on managed Postgres, or filesystem-level encryption
(eCryptfs / fscrypt). See `docs/operator/OPERATIONS.md` §
"Encryption at rest" for the three concrete recipes. The
application-layer privacy posture documented in this file
(append-only audit, C2 ZK-NULL coupling, the new constitutional
carve-out for archived rows) is independent of and complementary
to disk-level encryption — both layers protect different attack
surfaces (the application against operator-side mistakes; the
filesystem against host-side reads).

**Constitutional carve-out (v8.87 / Phase 2b):** for four
high-volume audit tables (`TokenLifecycleEvent`,
`VerificationEvent`, `EnrollmentStatusEvent`, `AuthAuditLog`),
rows older than the retention floor (operator-configured, default
5 years) can be moved from hot storage to a manifest-hashed
archive tarball via `uc_archive_purge()`. The hot row is deleted;
a `LifecycleArchiveCheckpoint` row recording cutoff + SHA-256 +
operator user_id is written in the same transaction. The
checkpoint table is strictly append-only (G30); the procedure is
the only DELETE path (G31). **Non-repudiation is preserved at
the constitutional level**: every event is reconstructible from
hot table OR (older than cutoff) from the archive tarball
referenced by the checkpoint. The privacy claim — "an operator
cannot disappear a holder's history" — is also preserved: any
purge produces an append-only checkpoint row, so attempted
tidying still leaves a permanent record.

This manifest-hashed-archive design was selected over a literal
no-deletions-ever policy (operationally infeasible past ~5 years)
and over PostgreSQL partitioning (non-trivial migration).

### Identity ≠ money (C10)

Polaris's deliberate refusal to carry value (C10) means it's
structurally not a financial-surveillance database. There's no
schema for transactions, balances, spending patterns, or merchant
codes. Adding any of those would require schema changes that the
Vocation (anti-coercion, in `MISSION.md`) refuses on sight.

### CSP `script-src 'self'` (C5)

No third-party scripts run in the operator UI. No CDNs, no
analytics, no tracking beacons. The only network requests from the
operator's browser are to the Polaris instance.

---

## Holder rights

### Right to access

A holder can request all data Polaris has about them. The query is
straightforward:

```sql
SELECT * FROM Individual WHERE individual_id = $1;
SELECT * FROM IdentityToken WHERE individual_id = $1;
SELECT * FROM TokenLifecycleEvent WHERE token_id IN
    (SELECT token_id FROM IdentityToken WHERE individual_id = $1);
SELECT * FROM VerificationEvent WHERE token_id IN
    (SELECT token_id FROM IdentityToken WHERE individual_id = $1);
```

(This request itself should be authenticated and audited; out-of-
scope for the schema.)

### Right to rectification

Updates to `Individual` are permitted via the operator UI. Updates
write a `TokenLifecycleEvent` if a token state is affected;
updates to non-token fields are not currently audited (BACKLOG:
audit non-token Individual changes).

### Right to erasure (limited)

Polaris does NOT support deleting holder data. The audit invariant
(C1) is non-negotiable. What CAN happen:

- Mark tokens REVOKED or LOST (the tokens stay; status is recorded)
- Anonymize `Individual.legal_name` to a pseudonym (the row stays;
  the name is replaced) — this is operationally supported

The pseudonymization is a real, shipped mechanism (v9.125): the stored
procedure `uc_pseudonymize_individual(individual_id, actor_user_id, reason)`
replaces `legal_name` with a `PSEUDONYMIZED-<id>` marker and records the act
in the append-only `IndividualErasureEvent` (who, when, why — never the prior
name or a hash of it, which would defeat the erasure). It is admin-gated and
issues no `DELETE`, so it cannot become a path around C1. Operators invoke it
via `scripts/polaris-pseudonymize-individual.sh`. The Individual row and every
audit/token reference to its `individual_id` survive, preserving
non-repudiation; only the plaintext name is gone.

The architectural inability to delete is itself a privacy claim of
a kind: Polaris cannot be coerced into "disappearing" a person's
identity history. This is intentional; without it, the system
cannot make non-repudiation guarantees.

A jurisdiction with a "right to be forgotten" law that requires
hard deletion is structurally incompatible with Polaris's audit
invariant. Such a deployment would need a MISSION amendment
(weakening C1) and the corresponding loss of non-repudiation.

### Right to portability

Holder data can be exported as a JSON document via a (future)
`/api/individuals/<id>/export` endpoint (BACKLOG). The audit log
fragments referencing the holder are included; the holder cannot
take with them an audit trail that references actions by other
agencies.

---

## Data sharing

Polaris does NOT share data with external systems by default.
Possible cross-system flows:

- **Verification events** — when an external relying party calls a
  Polaris verification endpoint, the event is recorded in Polaris.
  The relying party gets back a proof of the result; they do not
  receive holder PII (unless disclosure_level is `FULL`, in which
  case the holder consented to that level for that context).

- **Revocation list** — `RevocationList` rows can be published
  externally (CRL distribution). Published data: token_id (an
  opaque integer), revocation reason, effective date. No holder
  PII.

- **Aggregated atlas data** — `/api/atlas/*` endpoints return
  spatially-aggregated counts. They do NOT return holder identifiers
  for clusters; only for individual events at high zoom (`/api/atlas/points`).

There is no third-party tracking or telemetry. No data goes to
Anthropic, Google, AWS, or any other vendor by default.

---

## Logs and PII

The application log (`/tmp/polaris_app.log` in development; configurable
in production) records:

- HTTP method + path + status code + timing
- Outcome of authentication attempts (success/failure)
- IP address (for AuthAuditLog only; access log per gunicorn config)

The application log does NOT record:

- Form bodies (so passwords and PII don't end up in logs)
- Cookie values
- Token values

If logging configuration is changed to capture more (e.g. to debug
an issue), revert immediately after — and document the reversion in
`DEVNOTES/known-gotchas.md` so it doesn't regress.

---

## Cookies

Polaris uses one cookie:

- `session` — Flask session cookie. `HttpOnly`, `Secure`,
  `SameSite=Lax`. Contents are a signed (and optionally encrypted)
  payload representing the authenticated operator. No third-party
  cookies.

---

## What changes between development and production

Development uses `polaris_dev_password` for the database, the
default secret key, and HTTP rather than HTTPS. None of these are
acceptable in production:

- Secret key MUST be rotated to a random 32-byte value
- Database password MUST be unique
- HTTPS MUST be enforced (HSTS recommended)
- `Secure` cookie attribute MUST be set (default in Flask when
  HTTPS is detected)

See `OPERATIONS.md` pre-flight checklist.

---

## Operational privacy posture in production (Arc B / v8.77)

Polaris's production deployment (Arc B Phase 1) ships with three
privacy-relevant architectural choices that go beyond the
schema-level invariants above. These narrow the attack surface
through which holder or operator data could leak.

### File-mounted secrets (G28)

Production runs with **Docker secrets** rather than environment
variables for sensitive credentials. The Flask session signing
key (`POLARIS_SECRET_KEY`), the database password
(`POLARIS_DB_PASSWORD`), and the Postgres superuser password are
all mounted at `/run/secrets/<name>` from
`polaris_web/secrets/<name>` on the host (mode 0600). The app
reads them via the `*_FILE` env-var convention.

Practical implications for privacy:

- **`docker inspect` does not show secret values.** A bystander
  with `docker` group membership but no filesystem read access
  cannot read the secrets via container introspection.
- **Process listings (`ps -ef`) do not show secret values.**
  Environment variables can leak via `/proc/<pid>/environ`;
  file-mounted secrets do not.
- **Container logs cannot accidentally include secrets**
  because the app never accepts the secret through stdin or
  argv.
- **Backups skip the secrets directory** by default. The
  `polaris-backup.sh` tarball never includes `secrets/` — keys
  are rotated separately and would need to be re-generated on
  restore-to-new-host.

This is enforced structurally by G28
(`test_g28_no_sensitive_env_in_prod_compose`): the production
compose file cannot declare a literal value for
`POLARIS_SECRET_KEY`, `POLARIS_DB_PASSWORD`, or
`POLARIS_DB_ROOT_PASSWORD`.

### TLS at the edge (G27)

All operator and holder-facing traffic is terminated by Caddy
(`caddy:2-alpine`) using Let's Encrypt-issued certificates for
the configured `POLARIS_DOMAIN`. Caddy auto-renews ~30 days
before expiry. The Caddyfile sets the canonical security-header
set:

| Header | Value | Privacy effect |
|---|---|---|
| `Strict-Transport-Security` | `max-age=63072000; includeSubDomains; preload` | Browsers refuse to downgrade to HTTP for 2 years |
| `Referrer-Policy` | `strict-origin-when-cross-origin` | Outbound links don't leak the path the operator was on |
| `Permissions-Policy` | `geolocation=(), microphone=(), camera=(), payment=(), usb=()` | Polaris doesn't ask for any sensitive browser API |
| `X-Frame-Options` | `DENY` | Polaris pages can't be iframed (clickjacking + UI redress) |
| `Cross-Origin-Opener-Policy` | `same-origin` | Window-handle isolation |
| `Cross-Origin-Resource-Policy` | `same-origin` | Resource loading isolated |

Internal traffic (Caddy → app → Postgres/Redis) is plaintext
over the isolated Docker network. The privacy claim is that
nothing leaves the host without TLS termination first.

This is enforced structurally by G27
(`test_g27_caddyfile_declares_tls`).

### What gets logged in production

The production stack writes three log streams:

1. **`./logs/caddy/access.log`** — Caddy access log (JSON
   format). Records: timestamp, client IP, host, method, path,
   status code, bytes, request duration. **Does NOT record:**
   request bodies, response bodies, cookies, headers other than
   user-agent.

2. **`./logs/caddy/caddy.log`** — Caddy system log (JSON).
   Records ACME / TLS / config events. **Does NOT record:**
   client requests.

3. **App logs** — gunicorn access + error log (configurable via
   `gunicorn.conf.py`). Records HTTP method + path + status +
   timing. **Does NOT record:** form bodies, cookie values, or
   token values (see "Logs and PII" above).

Postgres + Redis logs are container-stdout by default; the
operator routes them to their log aggregator. The schema's audit
tables (`TokenLifecycleEvent`, `VerificationEvent`,
`AuthAuditLog`, `EnrollmentStatusEvent`, `DuressEvent`,
`AnchorBatch`, `AgencyTrustAttestation`, `TokenStateEpoch`) are
the system's *durable* privacy-relevant record; the log streams
above are *operational* and may be aggressively rotated.

### Rotation cadence (privacy half-life)

Per `docs/operator/SECRETS.md`:

| Secret | Rotation cadence | Privacy rationale |
|---|---|---|
| `POLARIS_SECRET_KEY` | 180 days | Bounds the session-cookie-replay window |
| `POLARIS_DB_PASSWORD` | 180 days | Bounds the database-credential blast radius |
| `POLARIS_DB_ROOT_PASSWORD` | 180 days | Bounds the superuser blast radius |
| TLS certificate | ~60 days (Caddy auto-renews) | Standard Web PKI rotation |
| Admin operator password | 90 days | Operator-account compromise bound |

Rotation is operator-driven via
`./scripts/polaris-rotate-secret.sh <name>`. The prior value is
archived under `polaris_web/secrets/.archive/<name>.<timestamp>`
(mode 0600) so an operator can investigate if a rotation breaks
production.

### What Arc B does NOT change

- **Schema invariants C1-C10 are untouched.** Append-only audit,
  ZK-NULL coupling, identity ≠ money — all preserved verbatim.
- **No new data is collected.** Arc B is operational, not
  schema. Holder data, operator data, and event data are
  exactly as before.
- **No new third-party data flows.** Caddy talks to Let's
  Encrypt for TLS issuance only. No analytics, no telemetry, no
  vendor-bound data egress.

---

## Population coverage (R11-4 / M2-9)

The PDF §9 names a sociotechnical risk: a national identity system
that assumes universal enrollment can become a coercion gradient.
Newborns, undocumented residents, unhoused people, those without
reliable access to reissuance infrastructure, and those whose
biometrics don't register reliably with available hardware would
all be outside the system. The schema must be honest about this.

R11-4 (v8.16) adds a five-status enrollment vocabulary
(`NOT_ENROLLED`, `PENDING_ENROLLMENT`, `ENROLLED`, `EXEMPT`,
`LAPSED`) recorded in the append-only `EnrollmentStatusEvent` table.
Three things matter for privacy:

1. **`NOT_ENROLLED` is the default, not a positive flag.** Every
   new `Individual` row gets a `NOT_ENROLLED` event from the seed
   trigger. The absence of enrollment is materialized only so it
   can be transitioned out of cleanly; it is not a tag the schema
   imposes.

2. **`civic_enrollment_summary` returns counts only.** The
   per-jurisdiction × status rollup is a first-class query.
   Per-individual enumeration of `NOT_ENROLLED` is *not* exposed
   as a function — an admin who needs it writes the join against
   `IndividualCurrentEnrollment` directly, which leaves a trace in
   `AuthAuditLog`.

3. **`EXEMPT` is the positive vocabulary** for "civic participant
   recognized without token." Recording an individual as EXEMPT is
   frictionless: a single INSERT. The PDF §9 second-clause "accepted
   path without tokens" gets first-class affordance.

The asymmetric design — EXEMPT frictionless, mass-NOT_ENROLLED
enumeration deliberate — is the privacy stance. The schema cannot
prevent misuse, but it can make the misuse named. Naming is the
precondition for governance catching it.

See `DEVNOTES/ships/tiered-enrollment.md` for the full adversary walk and
mechanism-design rationale.

---

## What this document does NOT cover

- Compliance frameworks (GDPR, CCPA, etc.) — those are deployment-
  specific and depend on your jurisdiction
- Subprocessors / hosting providers — depends on your deployment
- Children's data — Polaris has no special handling for minors;
  the deployment is responsible for any age-related restrictions

This file describes Polaris's architectural posture, not a legal
privacy notice. A real privacy notice would be drafted by counsel
with knowledge of the deployment context.
