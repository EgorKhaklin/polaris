# Polaris Security Audit & Patching Report

**Engagement:** Cybersecurity-patching pass on the Polaris Identity Token System
**Scope:** Web application (`polaris_web/`), CLI (`polaris_cli/`), database (`polaris_sql/`),
container runtime (`Dockerfile`, `docker-compose.yml`, `docker-init.sh`), and operational
configuration.
**Frameworks:** OWASP Top 10 (2021), CWE (Common Weakness Enumeration), NIST SP 800-53.
**Result:** 14 findings identified, 14 findings patched, 35 automated tests added
for the patches at the time. Current suite sizes are in the Test Coverage section
below, stamped at the version they were measured.

---

## Executive Summary

Pre-engagement, the Polaris web interface had **no authentication, no CSRF protection,
no rate limiting, and no security headers** — every endpoint was anonymously reachable
and every state-changing form was vulnerable to cross-site request forgery. The patching
pass introduced a complete authentication layer (username + scrypt-hashed password,
session-backed, role-based, lockout-protected), CSRF tokens on every form, security
headers on every response, per-IP rate limiting on login + writes, hardened cookies,
sanitized error messages, an append-only authentication audit log, and tightened the
Docker and shell-script attack surfaces.

The schema-level invariants from the original Polaris design (state-machine triggers,
append-only audit tables, partial unique indexes, FK constraints, role-based grants
with no-DDL polaris_app role) were already strong; this engagement focused on the
application and operational layers above them.

---

## Threat Model

The Polaris system stores national-scale identity data: holder names, dates of birth,
biometric binding metadata, verification history, device bindings, and audit chains.
Pre-patching, an attacker on the same network as the web server could:

1. Read every individual's complete identity record without credentials.
2. Issue, transition, or delete tokens via unprotected POST endpoints.
3. Trigger UC-7 warrant audits to extract verification history for arbitrary individuals.
4. Run arbitrary read SQL via the unauthenticated `/sql` console.
5. Forge state-changing requests via CSRF on a victim's logged-in session (had any
   such session existed; pre-patching there was no session at all).

Post-patching, an attacker without valid credentials sees only `/login`. An attacker
who has compromised an `auditor` account can read but not mutate state. An attacker
who has compromised an `operator` account can perform lifecycle operations but cannot
manage user records or run SQL queries. Compromise of the `admin` account is treated
as worst-case; defense-in-depth measures (audit logging, CSRF, CSP, no-DDL DB role)
remain effective even there.

---

## Finding Catalogue

Each finding is identified F-NN, mapped to OWASP Top 10 / CWE, given a severity, and
includes the patch description and the test(s) that verify the patch.

### F-01 — No Authentication on Any Endpoint **CRITICAL**

| OWASP | A01:2021 — Broken Access Control |
|-------|----------------------------------|
| CWE   | CWE-306 (Missing Authentication for Critical Function) |

**Finding:** Every route in `app.py` was anonymously reachable. The dashboard, Atlas
operational view, all CRUD routes, all four use-case workflows, the SQL console, and
the verification log all responded to requests without any session check.

**Patch:**
- New SQL file `10_auth.sql` adds `AppUser` and `AuthAuditLog` tables.
- Three seed accounts: `admin / Admin@123!`, `operator / Operator@123!`, `auditor / Auditor@123!`.
  Passwords stored as Werkzeug-generated scrypt hashes (CWE-916 mitigation).
- New `security.py` module with `@login_required` decorator applied to every protected route.
- `/login` endpoint with safe `?next=` redirect (rejects double-slash and external URLs to
  mitigate CWE-601 open redirect).
- Account lockout: 5 failures within 10 minutes locks the account for 15 minutes
  (CWE-307 mitigation).
- Username enumeration prevented: identical generic error message for unknown user vs
  wrong password, plus a constant-time-ish dummy hash check on the unknown-user path
  (CWE-203 / CWE-204).
- Session fixation defense: `session.clear()` on login (CWE-384).
- Logout requires POST + CSRF, defeating drive-by logout via image tags.

**Tests:** `F01_AuthenticationTests` — 13 tests covering anonymous redirect on every
protected route, login success/failure, generic error on unknown user, audit trail on
login events, account lockout, logout, GET-logout rejection, open-redirect resistance,
session fixation resistance.

---

### F-02 — No CSRF Protection on State-Changing Forms **HIGH**

| OWASP | A01:2021 — Broken Access Control |
|-------|----------------------------------|
| CWE   | CWE-352 (Cross-Site Request Forgery) |

**Finding:** Pre-patching, every POST endpoint accepted requests without any token check.
A logged-in user (had auth existed) could be tricked into issuing or revoking tokens via
a hidden form on an attacker-controlled page.

**Patch:**
- `security.issue_csrf_token()` generates a 32-byte URL-safe random token bound to the
  session; `validate_csrf()` compares it with `hmac.compare_digest()` (CWE-208 timing-attack
  mitigation).
- `@csrf_protect` decorator applied to every state-changing route.
- All 12 templates with `<form method="post">` were modified to include
  `<input type="hidden" name="csrf_token" value="{{ csrf_token() }}">`.
- The login form is exempt (no session yet to bind a token to); login is rate-limited as
  the alternative protection.
- CSRF rejection writes a `CSRF_REJECTED` row to `AuthAuditLog`.

**Tests:** `F02_CSRFTests` — 5 tests covering POST without token (403), POST with wrong
token (403), POST with valid token (302), CSRF rejections audited, CSRF input present
in every rendered form.

---

### F-03 — No Rate Limiting on Login or Writes **HIGH**

| OWASP | A04:2021 — Insecure Design |
|-------|----------------------------|
| CWE   | CWE-307 (Improper Restriction of Excessive Authentication Attempts), CWE-770 (Allocation of Resources Without Limits) |

**Finding:** No throttling on login attempts (separate from per-account lockout, which only
helps if the attacker concentrates on one account) or on state-changing endpoints generally.

**Patch:**
- `security.RateLimiter` class — sliding-window per-key counter.
- Login endpoint: 10 attempts per IP per 60 seconds. The 11th returns 429.
- All state-changing endpoints (POST/PUT/PATCH/DELETE): 60 requests per IP per 60 seconds.
- Rate-limit hits are audited as `RATE_LIMITED` events.
- The current implementation is per-process; a multi-worker deployment behind a real load
  balancer should swap the in-memory backend for a Redis-backed one (noted in
  `DEPLOYMENT.md`).
- v9.191: the limits read `POLARIS_RATE_LIMIT_LOGIN_MAX`, `POLARIS_RATE_LIMIT_WRITE_MAX`,
  and `POLARIS_RATE_LIMIT_WRITE_WINDOW` with the defaults above pinned by
  `check_performance_baseline`; the override exists so the performance baseline can
  drive one scratch server from one address, and a production stack that raises it has
  lowered this control on purpose.

**Tests:** `F03_RateLimitingTests::test_excessive_login_attempts_rate_limited`.

**Residual risk:** The in-memory limiter does not coordinate across workers. A 4-worker
gunicorn deployment effectively gives an attacker 4× the documented limit. For the
current single-host scope this is acceptable; production deployments should swap in a
Redis backend.

---

### F-04 — Missing Security Headers **MEDIUM**

| OWASP | A05:2021 — Security Misconfiguration |
|-------|--------------------------------------|
| CWE   | CWE-693 (Protection Mechanism Failure) |

**Finding:** No CSP, X-Frame-Options, X-Content-Type-Options, Referrer-Policy,
Permissions-Policy, or HSTS on any response.

**Patch (`security.apply_security_headers`, registered as `@app.after_request`):**

| Header | Value | Mitigates |
|--------|-------|-----------|
| `Content-Security-Policy` | `default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; ...; frame-ancestors 'none'; object-src 'none'` | XSS, clickjacking, MIME confusion, plugin-based attacks |
| `X-Frame-Options` | `DENY` | Clickjacking (CWE-1021) — legacy browser fallback for `frame-ancestors` |
| `X-Content-Type-Options` | `nosniff` | MIME sniffing (CWE-451) |
| `Referrer-Policy` | `strict-origin-when-cross-origin` | Information disclosure via Referer (CWE-200) |
| `Permissions-Policy` | `camera=(), microphone=(), geolocation=(), payment=(), usb=()` | Explicit denial of sensitive browser APIs |
| `Strict-Transport-Security` | `max-age=31536000; includeSubDomains` (production only) | Protocol downgrade (CWE-319) |
| `Cache-Control: no-store` | (authenticated content only) | Sensitive content caching (CWE-525) |

CSP is intentionally strict: no inline scripts, no eval, no remote sources. The lone
inline event handler in `tokens_detail.html` (a `confirm()` on the delete form) is the
only allowance and is not security-critical.

**Tests:** `F04_SecurityHeadersTests` — 6 tests covering CSP, X-Frame-Options, MIME
sniffing, Referrer-Policy, Permissions-Policy, no-cache on authenticated content.

---

### F-05 — Default Secret Key Warning Is Non-Fatal in Production **HIGH**

| OWASP | A05:2021 — Security Misconfiguration |
|-------|--------------------------------------|
| CWE   | CWE-798 (Use of Hard-coded Credentials) |

**Finding:** The Flask session secret falls back to a hardcoded development value. The
pre-patching code only printed a warning to stderr, which could easily be missed in
production logs. Sessions signed with a known key are forgeable end-to-end.

**Patch:**
- New environment variable `POLARIS_ENV`. When set to `production` AND the secret key is at
  its development default, the app calls `sys.exit(2)` at startup with a fatal message.
  Production deployments cannot accidentally start with a known-bad key.
- The non-production warning is preserved for development convenience.

**Tests:** `F05_ProductionSecretGuardTests::test_dev_default_secret_rejected_in_production`.

---

### F-06 — Database Password Fallback Default **MEDIUM**

| OWASP | A05:2021 — Security Misconfiguration |
|-------|--------------------------------------|
| CWE   | CWE-798 (Use of Hard-coded Credentials) |

**Finding:** The DB connection string falls back to `polaris_dev_password` if
`POLARIS_DB_PASSWORD` is unset. While this is appropriate for dev, the `polaris_app` role
itself can read every row in the schema; a default password in production is a credential
bypass.

**Patch:** `docker-init.sh` validates any custom `POLARIS_APP_PASSWORD` against complexity
rules (16+ chars, at least one digit, letter, and symbol); rejects with exit code 2 if the
custom password is weak. Passwords passed via env var are no longer echoed in psql output.
The dev default itself is unchanged — operators rotating the password go through the
docker-init script which enforces the gates.

**Tests:** Manual verification (the docker-init script's checks are tested via shell-level
verification, not the Python test suite).

**Residual risk:** The dev default `polaris_dev_password` is documented and intentional.
Production deployments are expected to rotate it via the env-var override path. Defense
in depth: the polaris_app role has no DDL privileges (verified via SQL test suite), so
even a credential-stuffed connection cannot drop tables.

---

### F-07 — Cookies Not Marked Secure / HttpOnly / SameSite **MEDIUM**

| OWASP | A02:2021 — Cryptographic Failures |
|-------|-----------------------------------|
| CWE   | CWE-614 (Sensitive Cookie Without 'Secure' Flag), CWE-1004 (Sensitive Cookie Without HttpOnly Flag) |

**Finding:** Pre-patching, there was no session cookie at all (no auth). With the F-01
patch introducing one, cookie hardening became mandatory.

**Patch:** Flask session cookie configured with:
- `SESSION_COOKIE_HTTPONLY = True` — JavaScript cannot read the cookie (XSS-via-token-theft mitigation)
- `SESSION_COOKIE_SAMESITE = 'Lax'` — cross-site requests don't carry the cookie (additional CSRF defense)
- `SESSION_COOKIE_SECURE = True` (when `POLARIS_COOKIE_SECURE=1`) — cookie not sent over HTTP
- `SESSION_COOKIE_NAME = 'polaris_session'` — branded for log searchability
- `PERMANENT_SESSION_LIFETIME = 8 hours` — automatic expiry

**Tests:** `F06_CookieHardeningTests::test_session_cookie_httponly` (parses the
`Set-Cookie` header on the login response and asserts `HttpOnly` and `SameSite=Lax`).

---

### F-08 — Database Errors Leak Internal Details **LOW**

| OWASP | A09:2021 — Security Logging and Monitoring Failures |
|-------|-----------------------------------------------------|
| CWE   | CWE-209 (Information Exposure Through Error Message) |

**Finding:** The original `db_error_to_message` returned the first line of any unhandled
psycopg2 error, which could include column names, table names, query fragments, or
internal SQL state. An attacker probing constraints could map the schema.

**Patch:** Hardened error mapping:
- Known constraints (state-machine trigger, append-only trigger, unique constraint on
  active tokens, disclosure-consistency check) get explicit user-friendly messages.
- Generic uniqueness, NOT-NULL, type-mismatch, and length errors get generic friendly
  messages without revealing column names.
- CHECK constraint names matching `chk_*` are surfaced (these are deliberate schema-author
  documentation); other CHECK violations get a generic message.
- Trigger-raised exceptions (which the schema authors designed to be user-facing) are
  passed through if they start with one of the expected verbs.
- Anything else gets a generic `"An internal database error occurred"` message and the
  full psycopg2 error is logged to stderr for operator diagnostics.

**Tests:** `F08_ErrorMessageSanitizationTests` — proves unknown errors don't leak internal
fragments and known constraints still return readable messages.

---

### F-09 — No Input Length Limits **LOW** (mitigated by existing layered defenses)

| OWASP | A04:2021 — Insecure Design |
|-------|----------------------------|
| CWE   | CWE-20 (Improper Input Validation) |

**Finding:** No application-level length validation on free-text form fields.

**Mitigation review:** The schema already enforces VARCHAR length limits at the column
level (legal_name VARCHAR(200), name VARCHAR(150), etc.) plus CHECK constraints for the
specific format requirements. Flask's `MAX_CONTENT_LENGTH` (1 MiB, set as part of F-14)
caps the entire request body. Client-side `maxlength` attributes on form inputs guide
legitimate users. The combined layered defense is adequate; adding redundant Python-level
length checks would duplicate the constraint logic without strengthening it.

**Patch:** No additional code; existing layers sufficient. Documented as such in
SECURITY.md to avoid future regressions.

---

### F-10 — SQL Console Doesn't Roll Back Failed Transactions **LOW**

| OWASP | A04:2021 — Insecure Design |
|-------|----------------------------|
| CWE   | (no specific CWE — operational hygiene) |

**Finding:** On a failed query, the SQL console's connection wasn't explicitly rolled back
or closed in all error paths. This wasn't exploitable in the current per-request connection
model but would become one if connection pooling were ever introduced.

**Patch:** Wrapped the connection in `try/finally`; the `finally` clause always rolls back
and closes regardless of which exception path was taken.

**Tests:** Implicitly covered by all SQL console tests passing under the new structure.

---

### F-11 — No Audit Log of Authentication / Admin Actions **HIGH**

| OWASP | A09:2021 — Security Logging and Monitoring Failures |
|-------|-----------------------------------------------------|
| CWE   | CWE-778 (Insufficient Logging) |

**Finding:** No audit trail existed for authentication events (because no authentication
existed). With auth in place this becomes mandatory for forensics and compliance.

**Patch:** New `AuthAuditLog` table with append-only trigger (reusing the existing
`reject_audit_modification` function). Captures:

| Event Type        | When |
|-------------------|------|
| `LOGIN_SUCCESS`   | Successful authentication |
| `LOGIN_FAILED`    | Wrong password, unknown user, inactive account |
| `LOGIN_LOCKED`    | Account hit lockout threshold |
| `LOGOUT`          | Explicit logout (POST /logout) |
| `CSRF_REJECTED`   | POST without valid CSRF token |
| `AUTHZ_DENIED`    | Logged-in user with wrong role |
| `AUTH_REQUIRED`   | Non-GET request without session |
| `RATE_LIMITED`    | IP exceeded login or write rate limit |
| `WEBAUTHN_REGISTERED` / `WEBAUTHN_ASSERTED` / `WEBAUTHN_ASSERTION_FAILED` / `WEBAUTHN_DEREGISTERED` / `EMERGENCY_PASSWORD_LOGIN_AUTHORIZED` | v8.97 WebAuthn lifecycle |
| `NETWORK_POLICY_DENIED` | v9.189. A correct password from outside the role's `POLARIS_NETWORK_POLICY_<ROLE>` (answered with the generic error), or a live session presented from outside it (ended) |
| `SESSION_EVICTED` | v9.189. A login exceeded `POLARIS_SESSION_MAX_<ROLE>`; the least-recently-seen session was revoked |
| `SESSION_EXPIRED` | v9.189. A session idled past `POLARIS_SESSION_IDLE_MINUTES_<ROLE>` |
| `SESSION_REVOKED` | v9.189. A live session of a deactivated account was ended on its next request |
| `WEBAUTHN_REGISTRATION_REFUSED` | v9.189. An enrollment the library rejected, or one the attestation policy refused (`policy:` in the detail) |

Each row records IP address (honoring X-Forwarded-For only when `POLARIS_TRUST_PROXY=1`,
mitigating CWE-345/348 IP-spoofing), user agent (truncated), and free-text detail.

**Tests:** `F11_AuditLoggingTests` — login success audited, authz denial audited, audit
log is append-only (UPDATE/DELETE rejected by trigger).

---

### F-12 — Docker Compose Exposes Postgres Port to Host **MEDIUM**

| OWASP | A05:2021 — Security Misconfiguration |
|-------|--------------------------------------|
| CWE   | CWE-668 (Exposure of Resource to Wrong Sphere) |

**Finding:** `docker-compose.yml` published the database container's 5432 port on the host,
exposing Postgres on every host network interface to anyone who could reach the host.

**Patch:** The `ports:` block is commented out. The app container reaches the db container
via the internal compose network using the service name `db`. Operators who want direct
psql access for debugging can uncomment the block; the change is one line and the comment
documents the security tradeoff.

**Tests:** Static review — the YAML now passes through `python -c "import yaml; yaml.safe_load(...)"`
and produces no published ports for the db service.

---

### F-13 — `docker-init.sh` Doesn't Validate Password Complexity **LOW**

| OWASP | A05:2021 — Security Misconfiguration |
|-------|--------------------------------------|
| CWE   | CWE-521 (Weak Password Requirements) |

**Finding:** Operators rotating the polaris_app password via `POLARIS_APP_PASSWORD` could
choose anything, including obviously weak passwords like `password123`.

**Patch:** `docker-init.sh` enforces:
- Minimum 16 characters
- At least one digit
- At least one letter
- At least one symbol

Failure exits with code 2 and a clear error message, before any database operation.
Additionally, the `ALTER ROLE ... PASSWORD '...'` invocation now redirects stdout to
`/dev/null` to prevent psql from echoing the password into container logs.

**Tests:** Verified via shell-level testing.

---

### F-14 — No Request Body Size Limit **LOW**

| OWASP | A04:2021 — Insecure Design |
|-------|----------------------------|
| CWE   | CWE-770 (Allocation of Resources Without Limits) |

**Finding:** Flask's default has no upper bound on request body size. A malicious POST
of an arbitrarily large payload could exhaust memory.

**Patch:**
- `app.config['MAX_CONTENT_LENGTH']` set to 1 MiB (1,048,576 bytes).
- Before-request hook also explicitly checks `request.content_length` and aborts with 413
  for a clearer error message.
- Custom 413 error page rendered.
- The SQL console additionally caps queries at 5,000 characters as a finer-grained limit.

**Tests:** Implicit via the working state of the app under MAX_CONTENT_LENGTH; explicit
test addition deferred (the test machinery for forging an oversized request through the
Flask test client is non-trivial and the layered defenses make this a low-priority gap).

---

## Summary Matrix

| ID    | Severity   | OWASP | CWE              | Status   | Test Class                  |
|-------|------------|-------|------------------|----------|-----------------------------|
| F-01  | CRITICAL   | A01   | CWE-306          | ✅ Patched | F01_AuthenticationTests     |
| F-02  | HIGH       | A01   | CWE-352, CWE-208 | ✅ Patched | F02_CSRFTests               |
| F-03  | HIGH       | A04   | CWE-307, CWE-770 | ✅ Patched | F03_RateLimitingTests       |
| F-04  | MEDIUM     | A05   | CWE-693          | ✅ Patched | F04_SecurityHeadersTests    |
| F-05  | HIGH       | A05   | CWE-798          | ✅ Patched | F05_ProductionSecretGuardTests |
| F-06  | MEDIUM     | A05   | CWE-798          | ✅ Patched | (manual)                    |
| F-07  | MEDIUM     | A02   | CWE-614, CWE-1004 | ✅ Patched | F06_CookieHardeningTests   |
| F-08  | LOW        | A09   | CWE-209          | ✅ Patched | F08_ErrorMessageSanitizationTests |
| F-09  | LOW        | A04   | CWE-20           | ✅ Mitigated (existing layers) | — |
| F-10  | LOW        | A04   | —                | ✅ Patched | (implicit)                  |
| F-11  | HIGH       | A09   | CWE-778          | ✅ Patched | F11_AuditLoggingTests       |
| F-12  | MEDIUM     | A05   | CWE-668          | ✅ Patched | (static review)             |
| F-13  | LOW        | A05   | CWE-521          | ✅ Patched | (manual)                    |
| F-14  | LOW        | A04   | CWE-770          | ✅ Patched | (implicit)                  |

Plus the `RoleBasedAccessControlTests` and `PasswordHashingTests` classes for cross-cutting verification.

---

## Test Coverage

Measured at v9.194 (the README's "Verified, not asserted" table is the
canonical statement and is re-stamped on every ship that changes it):

```
SQL self-tests : 78 assertions in 08_tests.sql, plus 12_v7_constraints.sql and 13_substrate.sql
Web            : 462 (test_app.py, 12 skipped without optional backends) + 72 constraint tests + 16 property tests + 19 secret-store tests
CLI            : 71 (test_cli.py)
Crypto         : 76 passing of 80 collected across the signing, custody and ZK witness suites (4 need AWS KMS)
Invariants     : 107 checks, each with a detection test (polaris_checks)
```

Run with:
```bash
cd polaris_sql && psql -d polaris_test -f 08_tests.sql
cd polaris_web && python3 -m pytest test_app.py test_check_constraints.py test_secretstore.py -q
cd polaris_cli && python3 -m pytest test_cli.py -q
python3 -m polaris_checks.run
```

---

## Denaturalization Resistance (R11-6 / M2-11)

The Polaris project report (§9, *Limitations and Open Problems*,
"Issuer trust concentration") names three production-system
requirements for the issuer-trust-concentration failure mode:

1. Cryptographic diversity across issuers — addressed by M2-6 / R11-1
   (multi-signature transitional state).
2. A federation model with mutual recognition between independent
   authorities — addressed by M2-8 / R11-3 (✅ v8.22:
   `AgencyTrustAttestation`).
3. **Constitutional limits on issuer discretion** — addressed by R11-6.

R11-6 implements the third leg at the schema level. `uc8_revoke_token`
is the single sanctioned revocation path. It enforces a rolling-window
N%/W-day cap on the rate at which a single issuing agency can revoke
its own tokens. Above the cap, a co-signer from a different agency
holding `BOTH` on the token's algorithm is required. The co-signer's
identity is recorded in the audit row as `[COSIGN:<id>]`, so a
third-party auditor can detect a single co-signer being used
repeatedly across mass-revocation events.

System defaults: N=5.00%, W=30 days. Per-agency overrides live in
`IssuerDiscretionPolicy` and require a justification string (≥20
chars) so any loosening is auditable.

What R11-6 protects against:

- Single-agency mass revocation (denaturalization-style abuse) — the
  PDF's named historical case study.
- Bypassing the procedure via raw UPDATE — caught by a
  belt-and-suspenders trigger on `IdentityToken.status`.

v9.190 (roadmap P1.8) extends the same leg to issuance and verification.
`AgencyQuota` holds opt-in per-agency caps (issuances and revocations per
rolling day, verifications per rolling hour) that the `enforce_agency_quota`
trigger binds on every write path with no bypass, exact under concurrent
writers; a refused write is an HTTP 429, a `quota_refused` log line, and a
`polaris_quota_refusals_total` increment. Alongside, per-agency velocity
counters feed `PolarisIssuanceVelocity`, `PolarisRevocationVelocity`, and
`PolarisVerificationVelocity`, which page when one agency's hour exceeds an
absolute floor and four times its own trailing weekly mean. Mass verification
is the dragnet shape the vocation refuses; these controls bound what an
agency may do and count what it does, never what a person is.
- Race conditions at the boundary — `pg_advisory_xact_lock` keyed on
  agency_id serializes concurrent revocations by the same agency.

What R11-6 does NOT protect against:

- Slow long-tail abuse under the bound (4.99% / month for a year ≈
  60%). Counter-mechanism: civic audit reporting, not the schema.
- System-wide collusion (every agency captured).
- Cryptographic forgery of co-signer identity. v1 records the
  co-signer procedurally; R12+ would add hardware-attested signing.

See `DEVNOTES/ships/issuer-discretion.md` for the full mechanism design
walk and adversary analysis.

---

## Catastrophic-Loss Recovery (R11-2 / M2-7)

The PDF §9.1 "Catastrophic-loss risk" open problem: a holder loses
ALL of their tokens and devices simultaneously (fire, theft, flood
affecting primary and reserve storage). Without a recovery path,
the holder is civically dark until full reissuance from scratch —
which loses the predecessor chain and the audit-history continuity.

R11-2 implements a **two-phase out-of-band recovery ceremony** at
the schema level. Four CHECK constraints on `RecoveryRequest`
encode the mechanism:

| Constraint | What it enforces |
|---|---|
| `cooldown_window_minimum` | At least 48 hours between request and decision (administrative window per PDF §9.1) |
| `approved_requires_three_channels` | APPROVED status requires biometric verification + sworn statement hash + witness agency co-sign |
| `approved_after_cooldown` | Decision timestamp must be at or after cool-down expiry |
| `approver_differs_from_requester` | The deciding `AppUser` cannot be the requesting one |

Plus a partial unique index (`uq_one_pending_recovery_per_individual`)
that ensures at most one PENDING recovery per individual at a time.

**Role split:** operator initiates (phase 1), admin completes
(phase 2). Auditor is read-only. The procedure `uc9_complete_recovery`
RAISEs `insufficient_privilege` if the deciding user is not admin;
the Flask route `/uc9/decide/<id>` also enforces this via
`@security.require_role('admin')`. Belt-and-suspenders.

**Concurrency:** `pg_advisory_xact_lock` keyed on
`claimed_individual_id` prevents two threads from both completing
the same PENDING request. Cross-individual recoveries run in
parallel.

**Audit trail:** every transition during APPROVED recovery is
tagged with `[RECOVERY:<recovery_id>]` in the lifecycle event's
`reason_code`. Audit replay can reconstruct the full recovery
context from the lifecycle log alone.

**What R11-2 does NOT protect against:**

- An attacker who compromises all three OOB channels simultaneously
  AND defeats the cool-down (the structural defense becomes the
  social-engineering surface at that point).
- The "operational grace period" reading of PDF §9.1 — v1
  implements the administrative window only; the holder is
  civically dark during the 48-hour PENDING window. A follow-up
  `TemporaryAttestation` mechanism is the planned operational
  grace credential.

The third leg of the "schema doesn't weaponize itself against the
holder" triad: R11-4 (entry — non-enrollment) + R11-6 (exit —
denaturalization) + R11-2 (recovery — catastrophic loss). See
`DEVNOTES/ships/recovery-ceremony.md` for the full mechanism-design walk
and adversary analysis.

---

## Cryptographic Migration (R11-1 / M2-6)

The PDF §9.4 "Cryptographic migration during transitions" problem:
how do tokens transition between post-quantum primitives when one
of them is later weakened or superseded? The PDF names two
production options — simultaneous mass reissuance, or a
multi-signature scheme. R11-1 implements the multi-signature
scheme.

`TokenSignature` is the M:N resolution of `IdentityToken →
signature`. A token can carry signatures from multiple algorithms
during a migration window. Two triggers enforce the invariants:

| Trigger | Invariant |
|---|---|
| `enforce_token_has_active_signature` | Every token has ≥ 1 non-deprecated signature at all times. |
| `enforce_token_signature_immutability` | Row is write-once except for one-way `deprecation_date` (NULL → timestamp allowed once; un-setting or backdating forbidden). |

Plus a UNIQUE composite key `(token_id, algorithm_id)` blocking
duplicate-algorithm migrations on a token, and the partial index
`idx_token_signature_active` keeping verification O(1) effectively.

**Procedure:** `uc6_migrate_algorithm` is the single sanctioned
path. Uses `pg_advisory_xact_lock` on `token_id` for C9 correctness;
cross-token migrations remain parallel.

**The issuer-trust-concentration triad** named in PDF §9:

| Leg | Item | Status |
|---|---|---|
| Cryptographic diversity | R11-1 | ✅ v8.18 |
| Federation | R11-3 / M2-8 | ✅ v8.22 |
| Constitutional limits | R11-6 | ✅ v8.15 |

R11-6 sits at the intersection of both triads (issuer-trust +
holder-protection). After R11-3 shipped in v8.22, **both PDF §9
triads are structurally complete** — every leg has a relational
answer enforced at the schema layer.

**What R11-1 does NOT protect against:**

- An attacker who compromises a not-yet-deprecated algorithm and
  forges signatures under it. The mechanism allows orderly
  deprecation but cannot retroactively reject signatures that were
  valid when produced.
- Auto-deprecation cascading from
  `CryptographicAlgorithm.deprecation_date`. By design — the two
  columns serve different purposes (algorithm-wide vs per-signature).
  Operator policy via UC-6 is the only path.

See `DEVNOTES/ships/multi-sig-migration.md` for the full mechanism design,
verification consistency model, and adversary walk.

---

## Compulsion Resistance — Duress Codes (R11-5 / M2-10)

**Status:** ✅ Shipped v8.24 — the v2 mission-closer.
**PDF §:** §9.5 — compulsion-resistance open problem.

The mechanism. A holder under coercion ("type your code or I'll hurt
you") types a *secondary* code — the duress code. The verification
flow:

1. Performs constant-time hash comparison against
   `IdentityToken.duress_code_hash` (Werkzeug scrypt, same primitive
   as AppUser password validation).
2. On match: silently writes a `DuressEvent` row (the 8th
   audit-of-record instance).
3. **Regardless of match/no-match/no-enrollment:** the coercer-visible
   response page is identical — same HTTP 302, same flash message,
   same `VerificationEvent` row written.

The duress signal is invisible to the coercer. Only admins and
auditors monitoring the DuressEvent table (via `/api/duress/events` or
direct SQL) see it.

| Property | How enforced |
|---|---|
| **Constant-time hash comparison** | `werkzeug.security.check_password_hash` (R1 audit refinement) |
| **Identical observable behavior** | Same response shape across all four branches (R2) |
| **Audit-of-record append-only** | `reject_audit_modification` trigger; 8th instance (R3) |
| **Per-token enrollment-only** | No auto-derivation; explicit ceremony required (R4) |
| **OOB v1 reference scope** | `oob_channel` field with future-fields for SMS/Slack/SIEM (R5) |
| **Anti-revealing posture** | `/verifications` operator list does NOT join to DuressEvent (R6) |

**What this does NOT protect against:**

- The coercer knows the duress mechanism exists and forces the holder
  to NEVER use it. Schema can't help if the holder is too constrained
  to act. The protocol enables detection *if used*.
- Holder typo: a small mistake (typing 911910 instead of 911911) won't
  trigger duress and may make the coercer suspicious. Mitigation:
  duress codes are designed to be distinct from verify codes by enough
  characters that typos are unlikely to collide.
- Timing analysis over many requests: an attacker measuring duress-event
  rates across many holders could potentially infer aggregate duress
  frequency. Out of scope for v1.

See `DEVNOTES/ships/duress-codes.md` for the full mechanism design.

---

## Operational Recommendations

1. **Rotate seed passwords immediately on any non-development deployment.** Use:
   ```python
   from werkzeug.security import generate_password_hash
   print(generate_password_hash('YourStrongPassword!', method='scrypt'))
   ```
   then `UPDATE AppUser SET password_hash = '...' WHERE username = 'admin';`

2. **Set `POLARIS_ENV=production` in production deployments** so the app refuses to start
   with a default secret key.

3. **Enable HSTS** by setting `POLARIS_HSTS=1` once you're certain HTTPS-only.

4. **Set `POLARIS_COOKIE_SECURE=1`** in production so the session cookie is HTTPS-only.

5. **Trust X-Forwarded-For only when behind a known proxy:** set `POLARIS_TRUST_PROXY=1`
   only after confirming nginx/load-balancer headers are present and untampered.

6. **Replace the in-memory rate limiter with Redis** for multi-worker production deployments.

7. **Feed `AuthAuditLog` into a SIEM** for centralized alerting on lockouts, repeated CSRF
   rejections from the same IP, and AUTHZ_DENIED bursts.

8. **Periodically audit `AppUser`** — remove inactive accounts, rotate passwords, review
   role assignments. The schema makes this easy:
   ```sql
   SELECT username, role, last_login_at,
          CURRENT_DATE - last_login_at::date AS days_idle
     FROM AppUser
    WHERE is_active
    ORDER BY last_login_at NULLS FIRST;
   ```

9. **Pin admin sessions to the networks they should come from (v9.189).** Set
   `POLARIS_NETWORK_POLICY_ADMIN` to the office / VPN / bastion ranges; a correct
   password from anywhere else is answered with the generic error and audited as
   `NETWORK_POLICY_DENIED`, and a live session that moves outside the range ends
   on its next request. Keep the default admin cap (3 concurrent sessions) and
   idle timeout (30 minutes) unless the operation needs otherwise; review live
   sessions and end one by hand when needed:
   ```sql
   SELECT session_id, u.username, s.role, s.client_ip, s.created_at, s.last_seen_at
     FROM OperatorSession s JOIN AppUser u USING (user_id)
    WHERE s.revoked_at IS NULL ORDER BY s.last_seen_at DESC;
   UPDATE OperatorSession SET revoked_at = now(), revoke_reason = 'operator'
    WHERE session_id = '<id>';
   ```
   `polaris user-passwd` and `polaris user-deactivate` revoke the account's
   sessions themselves. [HARDENING.md](HARDENING.md) section 13 has the full model.

10. **Raise the WebAuthn bar once every operator has a hardware key (v9.189):**
    `POLARIS_WEBAUTHN_USER_VERIFICATION=required` (PIN or biometric on every
    assertion), then `POLARIS_WEBAUTHN_ATTESTATION=direct` with
    `POLARIS_WEBAUTHN_REQUIRE_ATTESTATION=1` and, for a fixed fleet,
    `POLARIS_WEBAUTHN_ALLOWED_AAGUIDS`. [WEBAUTHN-ROLLOUT.md](WEBAUTHN-ROLLOUT.md)
    Phase 6.

---

## Compliance Mapping (Selected)

| Control | Standard | Implementation |
|---------|----------|----------------|
| Identification & Authentication | NIST SP 800-53 IA-2 | AppUser table, username + scrypt password |
| Access Enforcement | NIST SP 800-53 AC-3 | `@require_role` decorators per route |
| Account Management | NIST SP 800-53 AC-2 | AppUser is_active flag, account lockout |
| Audit Generation | NIST SP 800-53 AU-2 | AuthAuditLog + TokenLifecycleEvent + VerificationEvent |
| Audit Protection | NIST SP 800-53 AU-9 | Append-only triggers reject UPDATE/DELETE |
| Boundary Protection | NIST SP 800-53 SC-7 | CSP, X-Frame-Options, body size limit |
| Transmission Confidentiality | NIST SP 800-53 SC-8 | HSTS + Secure cookie (production) |
| Cryptographic Key Management | NIST SP 800-53 SC-12 | scrypt for password storage; PG MD5/SCRAM for DB |
| Resource Availability | NIST SP 800-53 SC-5 | Per-IP rate limiting, body size limit, statement timeout |

---

*Polaris Identity Token System · Cybersecurity Patching Engagement · Schema v1.0*
