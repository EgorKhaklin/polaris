# Runtime application self-protection

**Reader:** an engineer or an assessor. **Job:** The runtime self-protection rules, which are implemented and which are gaps.

---

## Framing

"RASP" is a vendor marketing term for a cluster of techniques that all
boil down to: detect anomalous behavior at runtime, and respond with
something more granular than "drop the request". This document refuses
the framework framing and instead catalogs the *concrete rules* and their
implementation status.

Three rule classes:

1. **Rate-limit rules**: bound the rate at which a principal can take
   an action
2. **Anomaly rules**: detect deviation from baseline and emit a HYDRA
   finding
3. **Edge rules**: Caddy-layer protections that run before requests
   reach the app

---

## Rate-limit rules

### R-RL-1: per-IP rate limit on auth endpoints
**Surface:** `/login`, `/auth/webauthn/assert/*`
**Limit:** 10 requests / minute / IP
**Backend:** Redis atomic INCR + EXPIRE)
**Gap:** none

### R-RL-2: per-IP rate limit on verification endpoints
**Surface:** `/verifications`, `/api/atlas/*`
**Limit:** 60 requests / minute / IP
**Backend:** Redis
**Gap:** none

### R-RL-3: per-(agency, individual) rate limit on verification
**Status:** ⚠️ GAP, exists at app layer; not at DB layer
**Surface:** verification recording in `uc_record_verification`
**Limit (proposed):** 30 verifications / hour / (agency_id, individual_id)
**Backend:** PostgreSQL advisory locks + ring-buffer; alternative is
Redis with a composite key
**Vocation:** ANTI-COERCION-DIRECT, caps the rate at which a
single agency can verify a single individual, preventing coercer-driven
bulk-attestation patterns
**Implementation note:** see `polaris_sql/05_procedures.sql`
`uc_record_verification` for the insertion path; the new rate-check
would run inside the same transaction so race conditions are sealed.

### R-RL-4: per-issuer revocation-rate cap
**Status:** ✅ IMPLEMENTED (v8.15, issuer-discretion bounds)
**Surface:** `uc8_revoke_token`
**Limit:** policy-configurable in `IssuerDiscretionPolicy`
**Mechanism:** trigger-enforced; row insertion in
`TokenLifecycleEvent` cross-checks against the policy
**Gap:** none

---

## Anomaly rules

### R-AN-1: unusually high verification volume per individual
**Status:** ⚠️ GAP, adversary_watcher emits NO finding for this
**Surface:** HYDRA's adversary_watcher
**Trigger (proposed):** if any individual receives >50 verifications in
the last hour, emit `{node_id: "adversary:high-verify-rate", level:
"WARN", individual_id: ...}`, does NOT block, just surfaces
**Implementation:** add channel to `polaris_hydra/watchers/adversary_watcher.py`;
reads `VerificationEvent` GROUP BY individual_id WHERE created_at >
now() - INTERVAL '1 hour'

### R-AN-2: failed-login spike from a single IP
**Status:** ⚠️ GAP, security_watcher counts globally, not per-IP
**Trigger (proposed):** if any IP produces >20 failed-logins in
10 minutes, emit `{node_id: "adversary:auth-spike", level: "WARN",
src_ip: ...}`. Distinct from R-RL-1 (which throttles), this signals
*pattern*, not enforces *throughput*.

### R-AN-3: enrollment-event burst from a single agency
**Status:** ⚠️ GAP
**Trigger (proposed):** if a single agency produces >5 enrollment
events in 5 minutes, emit a HYDRA finding. Vocation: anti-coercion:
coerced bulk enrollment is detectable.

### R-AN-4: ZK-disclosure-level downgrade attempts
**Status:** ✅ IMPLEMENTED, the C2 CHECK constraint (`chk_disclosure_token_consistency`) refuses at DB level; logged
in `TokenLifecycleEvent` as REJECTED operation
**Trigger:** any verification request with disclosure-level FULL on
a token whose policy is ZERO_KNOWLEDGE, C6 server-side enforcement
**Watcher coverage:** security_watcher channel 3 (v8.x) scans for
REJECTED rows
**Gap:** none (this is constitutionally enforced)

### R-AN-5: foresight category drift
**Status:** ⚠️ GAP, foresight surface (v9.12) has no off-mission
detection
**Trigger (proposed):** if `_acceptance_log.json` shows >2 FS-XXXXXXXX
candidates with `vocation_alignment != anti-coercion-*`, emit
WARN: the foresight surface is drifting from its constitutional
purpose
**Implementation:** new channel in adversary_watcher or extend
foresight promotion to refuse non-anti-coercion candidates outright
(Anti-Architect would likely prefer the refuse path; this is a
non-decided sub-question)

---

## Edge rules (Caddy layer)

The Caddy proxy serves TLS and forwards to the gunicorn upstream. Beyond
TLS, Caddy can enforce:

### R-ED-1: HTTP security headers
**Status:** ✅ IMPLEMENTED at app layer (v9.13)
**Surface:** `polaris_web/security.py:apply_security_headers`
- Strict-Transport-Security: max-age=31536000; includeSubDomains; preload
- Content-Security-Policy: default-src 'self'; script-src 'self';
  style-src 'self' 'sha256-{...}'; img-src 'self' data: blob:;
  upgrade-insecure-requests (v9.13)
- X-Content-Type-Options: nosniff
- X-Frame-Options: DENY
- Referrer-Policy: same-origin
- Cross-Origin-Opener-Policy: same-origin (v9.13)
- Cross-Origin-Resource-Policy: same-origin (v9.13)
- Permissions-Policy: camera=(), microphone=(), geolocation=(),
  payment=(), usb=(), bluetooth=(), interest-cohort=() (v9.13),
  browsing-topics=() (v9.13)
- Server: scrubbed (v9.13)
**Gap:** none

### R-ED-2: connection-rate limit at Caddy
**Status:** ⚠️ GAP, Caddy can apply `rate_limit` directive but the
Caddyfile in `polaris_web/deploy/` does not include one
**Proposed:**
```caddy
{
    order rate_limit before reverse_proxy
}
polaris.example.com {
    rate_limit {
        zone auth_zone {
            key {remote_host}
            events 30
            window 1m
        }
        zone api_zone {
            key {remote_host}
            events 300
            window 1m
        }
        path /login /auth/* @auth_zone
        path /api/* @api_zone
    }
    reverse_proxy localhost:5000
}
```
Caddy's `rate_limit` is an additional defense-in-depth layer; the app
Redis rate-limiter is the primary. Both should be enabled in
production.

### R-ED-3: WAF rule for common injection patterns
**Status:** ⚠️ GAP, Caddy does not ship a WAF; commercial WAFs
(Cloudflare, AWS WAF) can be in front but are deployment-specific
**Note:** the app is parameterized-SQL throughout (psycopg2 bind
parameters); injection at the SQL boundary is structurally impossible.
A WAF would catch upstream attempts pre-app, but the structural
defense is the primary line.

### R-ED-4: TLS configuration
**Status:** ✅ IMPLEMENTED, Caddy handles Let's Encrypt + modern
TLS suite by default; no `tls_min_version` override needed
**Gap:** none

---

## Implementation cadence

This document is a catalog, not a one-shot implementation list. It does
NOT in-line a new framework for all gaps. Each gap (R-RL-3, R-AN-1,
R-AN-2, R-AN-3, R-AN-5, R-ED-2, R-ED-3) is a candidate for a future
incremental ship; operator priority + vocation alignment determines order.

Recommended order (vocation-weighted):
1. R-RL-3 (per-agency-individual rate limit): anti-coercion direct
2. R-AN-1 (high-verify-rate finding): anti-coercion-indirect
3. R-AN-3 (enrollment burst): anti-coercion-indirect
4. R-ED-2 (Caddy rate-limit): anti-coercion-indirect (DoS defense)
5. R-AN-2 (auth-spike finding): security hardening
6. R-AN-5 (foresight drift detection): constitutional self-monitoring
7. R-ED-3 (WAF in front): deployment-specific; operator decision

---

## Vocation alignment summary

7 of 12 rules in this catalog are ANTI-COERCION-DIRECT or
ANTI-COERCION-INDIRECT (R-RL-3, R-RL-4, R-AN-1, R-AN-3, R-AN-4,
R-AN-5, R-ED-2). 5 are infrastructure-hardening (R-RL-1, R-RL-2,
R-AN-2, R-ED-1, R-ED-3, R-ED-4). Zero are anti-coercion-negative.

The RASP rule-set as a whole strengthens the anti-coercion vocation
by making coercion-shaped patterns (bulk verification, burst
enrollment, downgraded-disclosure attempts) detectable and rate-
limited.

---

*Rule status as of v9.23.*
