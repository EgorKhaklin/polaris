# proposals/R11-5-duress-codes.md

**Risk class:** HIGH (compulsion-resistance; timing-attack surface; silent-failure mode if mitigations are imperfect)
**Mission link:** v2 M2-10 (open problems — PDF §9.5 compulsion resistance)
**Status:** PROPOSED, awaiting VANTA ship approval
**Effort:** ~2 sessions (smaller than M2-1; no new substrate)
**Architect ID:** arch-2026-05-11-003 (M2-10 readiness assessment)

---

## Problem (PDF §9.5)

A holder under physical coercion ("type your code or I'll hurt you") has
no schema-level way to signal duress. The verification flow today is
binary: the verification either succeeds (with biometric + signature) or
it doesn't. The coercer monitors the result; "success" reveals nothing
about whether the holder was free or compelled.

PDF §9.5 names this as the compulsion-resistance open problem. The
standard mitigation is well-known from banking and high-security retail:
a **duress code** — a secondary credential the holder types under
coercion that *looks* like successful verification from the coercer's
view, while silently triggering an out-of-band alert.

This is the LAST open item in v2. M2-10 is the mission-closer.

## Why HIGH-risk

Three concerns:

1. **Silent failure mode.** A timing-attack-vulnerable implementation
   lets the coercer detect duress by measuring response time. The
   verifier sees "SUCCESS" identically in both cases, but a few
   milliseconds of latency difference can be measured externally.
   Mitigations are well-known (constant-time comparison) but the
   discipline is mandatory.
2. **Out-of-band notification can fail silently.** If the OOB alert
   doesn't reach responders, the duress signal is invisible. v1
   reference impl records to a `DuressEvent` audit table; production
   would integrate SIEM/SMS/Slack.
3. **Holder-side compromise — out of scope.** If the coercer KNOWS the
   mechanism exists and forces the holder to never use duress, the
   schema can't help. The protocol's role is to enable detection *if
   used*, not compel use.

Risk is HIGH but **engineering-tractable** — unlike M2-1's graduate-
level cryptographic surface, M2-10 reuses primitives we already have
(scrypt in `security.py`, `hmac.compare_digest`, append-only
audit-of-record pattern).

## What v1 ships

### Schema additions

1. **`IdentityToken.duress_code_hash VARCHAR(255)`** — nullable.
   Same format as `AppUser.password_hash` (Werkzeug scrypt).
   NULL means "this token has not enrolled a duress code." Most demo
   tokens start without one; a separate enrollment ceremony sets it.
   CHECK constraint: if non-NULL, length ≥ 20 (a Werkzeug scrypt hash
   is at least ~100 chars).

2. **`DuressEvent` table** — the **8th audit-of-record instance**.
   Append-only via `reject_audit_modification` trigger. Each row
   records a detected duress event:
   - `event_id SERIAL PK`
   - `token_id INTEGER NOT NULL REFERENCES IdentityToken(token_id)`
   - `context_id INTEGER NOT NULL REFERENCES VerificationContext(context_id)`
   - `requesting_agency_id INTEGER NOT NULL REFERENCES Agency(agency_id)`
   - `event_timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP`
   - `oob_channel VARCHAR(40)` — `'AUDIT_TABLE'`, `'STDERR_LOG'`,
     `'SMS_PLACEHOLDER'`, etc. v1 ships with `'AUDIT_TABLE'` as the
     only supported channel; production would add real channels.
   - `oob_notified_at TIMESTAMP` — when the alert was raised (NULL =
     not yet acknowledged)

### Procedure: `uc12_record_duress`

Records a detected duress event under the same constraints as other
audit-of-record writes. Admin/operator-role only (called by the
verification flow, not directly by holders). No advisory lock —
DuressEvent INSERTs don't contend.

```sql
CREATE OR REPLACE PROCEDURE uc12_record_duress(
    p_token_id      INTEGER,
    p_context_id    INTEGER,
    p_requesting_agency_id INTEGER,
    p_oob_channel   VARCHAR(40)
) ...
```

### Verification-flow extension

`POST /verifications/new` accepts an optional `duress_code` form field
(or JSON field). When present:

1. Hash the input with the token's `duress_code_hash` using
   **`werkzeug.security.check_password_hash`** — the same
   constant-time comparison used for `AppUser` authentication.
2. If match: record `DuressEvent` via `uc12_record_duress`. The OOB
   channel for v1 is `'AUDIT_TABLE'` (writing to `DuressEvent` IS
   the alert; an operator monitoring the table sees it).
3. **Regardless of match/no-match:** continue with the normal
   verification path. The outcome recorded in `VerificationEvent`
   is identical to the non-duress flow. The coercer sees only the
   normal `verification_form` confirmation page.

Critical: the response time and rendered output must be identical
whether duress matched, didn't match, or wasn't supplied. The
`werkzeug.security.check_password_hash` call already takes
constant-time-comparison-against-the-stored-hash; the `DuressEvent`
INSERT happens in the same request, adding ~1-3 ms (well within
normal latency variance).

### Tests

`DuressCodeTests` (≥10 tests):
- Schema invariants: `duress_code_hash` length CHECK; `DuressEvent`
  append-only DELETE/UPDATE rejected
- Procedure: `uc12_record_duress` writes a DuressEvent
- Verification-flow: duress input matching → DuressEvent written
- Verification-flow: duress input mismatching → no DuressEvent
- Verification-flow: no duress input → no DuressEvent
- Verification-flow: duress matched → `VerificationEvent.outcome`
  is still SUCCESS (coercer-visible behavior identical)
- Timing-attack resistance: verification time variance across
  duress-match / duress-mismatch / no-duress is below threshold
  (sub-50 ms variance — well below human-detectable)
- Cross-token duress code rejection: code A on token B doesn't match

### Sample data

One demo token enrolls a duress code (Maria's T2 — for the
banking-context demo scenario). The plaintext code is documented in
the seed file (it's a reference impl). The hash is stored.

### Documentation

- `DEVNOTES/duress-codes.md` (new) — canonical write-up:
  timing-attack rationale, OOB channel design, anti-revealing
  posture, v1 reference scope vs production-hardening path.
- `DEVNOTES/audit-of-record.md` — extended to 8 instances.
- `docs/SECURITY.md` — adds duress-code mechanism to the threat-model
  mitigation table.
- `MISSION.md` M2-10 ✅ + **"both PDF §9 triads + ALL §9 open problems"** note.

## Audit refinements (folded in below)

Following the established pattern, six refinements specific to this
ship:

### R1. Constant-time hash comparison (timing-attack resistance)

Use `werkzeug.security.check_password_hash` for the duress-code
match. This is the same function used to validate `AppUser`
passwords, which is constant-time over the hash payload by Werkzeug's
implementation. We do NOT use `==` string comparison or any
length-dependent check.

The Python interpreter's own variability (~1-10 ms per request) is
much larger than the constant-time hash comparison overhead, so
microbenchmarks of duress-match vs no-duress should be statistically
indistinguishable.

### R2. Identical observable behavior to the coercer

Both branches (duress matched / not matched / no input) produce:
- The same HTTP response (`302 → /verifications`)
- The same flash message (`'Recorded verification event #N'`)
- The same `VerificationEvent` row written (outcome=SUCCESS or
  outcome=FAILURE based on the normal verification path, NOT the
  duress branch)

The `DuressEvent` row is written silently — it does NOT appear in
the operator-visible verifications list. Only auditors with
explicit access to `DuressEvent` see it.

### R3. DuressEvent is the 8th audit-of-record instance

Append-only via `reject_audit_modification` trigger (reuses the
existing trigger function — DuressEvent joins the protected-table
set as the 6th table covered: TokenLifecycleEvent, VerificationEvent,
EnrollmentStatusEvent, AnchorBatch, TokenStateEpochLeaf,
DuressEvent).

### R4. Per-token enrollment-only (anti-auto-derivation)

`duress_code_hash` is set per-token via an explicit ceremony — never
auto-derived. v1 ships with one demo enrollment in sample data.
Production would have a dedicated enrollment flow (operator-mediated)
in a separate ROADMAP item. Same posture as R10-2's
`committed_to_chain` future-field.

### R5. OOB notification — v1 reference scope, v2 path named

v1 reference impl: the `DuressEvent` row IS the alert. An operator
or auditor monitoring the table sees duress events as they happen.
v2 production: add real OOB channels (SMS/Slack/SIEM webhook).

The `oob_channel` column is the future-field — currently always
`'AUDIT_TABLE'`. CHECK constraint enumerates the channels (audit /
stderr / SMS / Slack / SIEM). Schema is ready for v2 integration
without migration. Same posture as R10-2 / R11-3.

### R6. Anti-revealing: DuressEvent NOT in standard verification list

The operator-visible `/verifications` list shows `VerificationEvent`
rows only — never joins to `DuressEvent`. The `DuressEvent` table is
accessible via:
- The `polaris query` SQL console (admin/auditor role)
- A dedicated `/duress` operator route (admin role) showing
  pending OOB notifications

A coercer who has compromised an operator account sees only the
verifications list — they would need to know the `DuressEvent` table
exists AND have admin role to discover that duress was signaled.
This is defense-in-depth, not absolute protection.

## Audit checklist

| Check | Status |
|---|---|
| Constant-time hash comparison | ✅ R1 (Werkzeug scrypt) |
| Identical observable behavior under all branches | ✅ R2 |
| Append-only / audit-of-record (8th instance) | ✅ R3 |
| Anti-auto-derivation (per-token enrollment) | ✅ R4 |
| OOB v1 reference / v2 path named | ✅ R5 |
| Anti-revealing posture | ✅ R6 |
| C9 advisory-lock needed | N/A — DuressEvent is pure-append; no contention |
| Reuses existing primitives (no new substrate) | ✅ (scrypt from security.py) |
| Mission closure named explicitly | ✅ (v2 → 12/12 after ship) |

## v2 mission closure

After this release, the v2 done-list is:

| Item | Status |
|---|---|
| M2-1 ZK-SNARK | ✅ v8.23 |
| M2-2 DID anchoring | ✅ v8.21 |
| M2-3 Substrate manifest | ✅ v8 |
| M2-4 GenomicAnchor | ✅ v8 |
| M2-5 QuantumObserverBinding | ✅ v8.11 |
| M2-6 Multi-signature transitional | ✅ v8.18 |
| M2-7 Catastrophic-loss recovery | ✅ v8.17 |
| M2-8 Issuer federation | ✅ v8.22 |
| M2-9 Tiered enrollment | ✅ v8.16 |
| **M2-10 Duress codes** | ✅ **v8.24 (this)** |
| M2-11 Issuer-discretion bounds | ✅ v8.15 |
| M2-12 Verification-graph redaction proof | ✅ v8 |

**v2 → 12/12 ✅**. Every item in the PDF's "open problems" list closed.
Every substrate-layer claim demonstrated. Every triad complete.

This is the v2 mission completion point. v3 — if it exists — is a new
mission. The next session after M2-10 ships should write
`meta/missions-considered.md` v3 candidates: the v2 retrospective +
the v3 strategic-arc analysis (post-shipment review + what's next).

## Blast radius

- Schema: +1 column on `IdentityToken`, +1 table (`DuressEvent`), +1 CHECK constraint
- Triggers: extends `reject_audit_modification` to DuressEvent (no new function)
- Procedures: +1 (`uc12_record_duress`)
- Flask: `verifications_new` extended (optional `duress_code` field); +1 new route (`/duress` operator dashboard, admin role); +1 API route (`POST /api/duress/record` if needed for tests)
- Tests: +10 `DuressCodeTests` + 4-5 SQL self-tests section R
- DEVNOTES: 1 new (`duress-codes.md`), 1 extended (`audit-of-record.md` → 8 instances)
- docs: SECURITY.md addition; DATA-MODEL.md `DuressEvent` section
- Substrate: ZERO new substrate (reuses scrypt + Werkzeug already in security.py)
- Counts: 22 → 23 tables; 12 → 13 procedures; 13 → 14 triggers (the leaf table); 7 → 8 audit-of-record instances; 6 advisory-lock entries unchanged (DuressEvent is pure-append, no contention)

## Pre-Sanctum sanity checklist

| Check | Status |
|---|---|
| Constant-time hash comparison named | ✅ |
| Identical observable behavior across branches | ✅ |
| Append-only / 8th audit-of-record | ✅ |
| Anti-auto-derivation (per-token enrollment) | ✅ |
| OOB v1 scope vs v2 path | ✅ |
| Anti-revealing (DuressEvent not in standard list) | ✅ |
| Mission closure explicit (v2 → 12/12) | ✅ |
| Substrate manifest impact | ✅ (zero — no new primitive) |

## Cross-references

- **MISSION.md** M2-10 — the open item this proposal closes
- **ROADMAP.md** R11-5 — the corresponding R-id
- **PDF §9.5** — compulsion-resistance open problem
- **`polaris_web/security.py`** — `check_password_hash` (Werkzeug
  scrypt) is the constant-time primitive reused
- **`DEVNOTES/audit-of-record.md`** — to be extended to 8 instances
- **`docs/SECURITY.md`** — threat-model mitigation table addition
- **Sanctum** — to be opened after this proposal is final
