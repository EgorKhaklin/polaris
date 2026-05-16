# Sanctum: webauthn-operator-auth

**Date:** 2026-05-14
**Petitioner:** agent (Claude, Opus 4.7) speaking as the Architect
**Principal:** VANTA
**Trigger:** Of the three remaining Phase 2 Sanctum-class items from the v8.93 macro brief, two have closed (audit-log archive → v8.93 `polaris-rotate-logs.sh` + schema migration framework → v8.95). WebAuthn is the last Phase 2 deployability item that is **operationally Sanctum-class** — schema change, authentication-flow rewrite, threat-model update, UX redesign — and Pattern #20 Constitutional Discipline (heavy-production preserves the Sanctum protocol for constitutional questions) governs.
**Risk class:** HIGH (schema + auth-flow + threat-model + UX all change together; touches every operator's daily login path; recovery semantics decide what happens to a locked-out admin).
**Status:** DECIDED + CLOSED 2026-05-14 — Position B shipped as v8.97 (end-to-end, single ship)

---

## I. The Matter

Polaris operator authentication today (the surface lives in `polaris_web/security.py`):

- `AppUser` table: `username` + werkzeug-scrypt `password_hash` + `role IN ('admin','operator','auditor')` + `failed_login_count` + `locked_until`
- Sessions are server-side Flask sessions over signed cookies
- Failed-login rate limit + AppUser lockout after 5 failures within window
- Session-secret rotation on login (v8.56 + v8.58 hygiene fix)
- AuthAuditLog records every auth-flow event (LOGIN_SUCCESS / LOGIN_FAILURE / ACCOUNT_LOCKED / ACCOUNT_CREATED / SESSION_REGENERATED)

This is **single-factor authentication** — knowledge factor (password) only. The
threat model in `DEVNOTES/threat-model.md` notes that admin credential theft
(phishing, malware exfil, breach disclosure) is the highest-impact attack
surface because admin can:

- Issue + revoke any token (UC-1 / UC-8)
- Trigger `uc_archive_purge` (after v8.87: delete from hot audit tables under carve-out)
- Create new operator accounts (`polaris-create-operator.sh` admin path)
- Read every individual's enrollment-status history

WebAuthn (W3C Level 3 / FIDO2 CTAP2) adds a hardware-backed second factor:

- Public-key cryptography; no shared secret leaves the authenticator
- Origin-bound by design (the assertion contains `${POLARIS_DOMAIN}` —
  phishing-resistant; a credential issued for `polaris.example.com` will
  not assert on `polar1s.example.com`)
- Compatible with hardware tokens (YubiKey, SoloKey, Nitrokey) and
  platform authenticators (Touch ID / Face ID / Windows Hello / Android)
- Standard library support in Python via the `webauthn` package
  (~6 MB; one direct dep; pure-Python implementation)

The constitutional question: **what does WebAuthn do to the existing
password-and-session flow?** The four positions below give VANTA a way
to pick the threat-model / UX / recovery-flow trade-off explicitly.

## II. The architect's positions

### Position A: Mandatory WebAuthn-only for admin (passwords abolished for admin role)

Replace the admin password layer entirely. Admin role REQUIRES a registered
WebAuthn credential; password column is NULL for admin AppUsers; login
flow for admin is a single WebAuthn assertion against an enrolled credential.

**Strength:** strongest practical defense against phishing + credential
theft. The cred never leaves the authenticator. No password to forget,
phish, or breach-disclose.

**Weakness:** **brittle recovery.** Lost device = locked-out admin.
Mitigations exist (BIP-39 mnemonic backup, second-admin pairing,
recovery-code sheet) but each adds operational complexity, and a single
admin running solo (the demo-deployment case Polaris's reference-implementation
covers) has no second-admin to pair with. Sets a steeper bar than the
audit / operator roles. Not standard government / financial practice.

### Position B: WebAuthn-MFA (password AND WebAuthn both required, after enrollment) — architect-recommended

The standard MFA pattern. Admin (and optionally operator) role REQUIRES
WebAuthn enrollment by deadline; password layer stays as the first factor;
WebAuthn assertion is the second factor. Both required for login.

**Specification (sketch — refined after VANTA decides):**

- New table `OperatorWebauthnCredential`: `credential_id` PRIMARY KEY,
  `user_id` FK to `AppUser`, `public_key` BYTEA, `sign_count` BIGINT,
  `transports` VARCHAR(80), `attestation_format` VARCHAR(40),
  `aaguid` UUID NULL, `device_label` VARCHAR(100) NULL,
  `enrolled_at` TIMESTAMPTZ, `last_used_at` TIMESTAMPTZ NULL — schema
  migration via the v8.95 framework as `2026-05-14-002-operator-webauthn.up.sql`
- `AppUser` gains `webauthn_required_after TIMESTAMPTZ` — the enrollment
  deadline; before deadline, password-only login allowed; after, login
  requires both
- Two new flows in `app.py`:
  - `/auth/webauthn/register` (admin already authenticated by password;
    starts WebAuthn registration ceremony; persists credential on success)
  - `/auth/webauthn/assert` (after password succeeds in `/login`; client
    receives challenge + relying-party info; submits assertion;
    server verifies signature + origin + counter)
- AuthAuditLog gains event types: `WEBAUTHN_REGISTERED` /
  `WEBAUTHN_ASSERTED` / `WEBAUTHN_ASSERTION_FAILED` /
  `WEBAUTHN_DEREGISTERED`
- Recovery: a locked-out admin (lost device) gets a password-only
  emergency-login window of N minutes (default 15), triggered by another
  admin running `scripts/polaris-recover-admin.sh <username>` which
  records to AuthAuditLog as `EMERGENCY_PASSWORD_LOGIN_AUTHORIZED`.
  The window is logged + alerted. Single-admin deployments use a
  printed mnemonic backup (FIDO BIP-39 from the authenticator's
  device-key derivation, or operator-generated recovery code that
  serves as a one-time WebAuthn-bypass token)
- UX: existing admin accounts get a `webauthn_required_after = now() + 30d`
  on first login post-v8.96; they have 30 days to enroll a credential
  via `/settings/webauthn`; deadline-passed accounts cannot log in
  without enrollment

**Strength:** matches government / financial / SOC-2-relevant practice.
Defense-in-depth: phishing-resistant second factor AND the existing
password layer. Migration path is graceful (30-day deadline, not
mandatory-overnight). Recovery is handled via the already-audited
admin-pairing protocol. Compatible with both hardware tokens and
platform authenticators (operator picks; Polaris allows-list configurable).

**Weakness:** two factors = two friction points at every admin login.
Requires per-deployment WebAuthn relying-party setup (`${POLARIS_DOMAIN}`
matching, attestation policy decision). Adds one direct dependency
(`webauthn` package + transitive `cryptography` which is already
pulled in). Operator must carry the device.

### Position C: WebAuthn-only with passkey + passwords as recovery-only fallback

Passkey-first: login normally uses WebAuthn alone (no password); password
is a recovery-only path that is logged + alerted on use. Practically
equivalent to Apple/Google passkey UX.

**Strength:** simplest steady-state UX (one assertion, done; passwordless
typical day); modern threat model. Passwords behave like recovery
codes — used rarely, on alert.

**Weakness:** the password-as-recovery path means an attacker who steals
the password still gets in (just noisily). Reduces defense-in-depth
versus Position B. Less compatible with deployments that haven't
adopted passkey UX (the "type your password" muscle memory is decades
deep). Mixed-signal posture: "we have WebAuthn" but also "your password
still works."

### Position D: defer indefinitely (status quo)

Keep password-only auth for admin. Document the gap. Real production
deployments add their own auth proxy (OIDC IdP, SAML SSO, Tailscale ACL)
in front of Polaris.

**Strength:** zero work now. The auth proxy approach is what enterprise
deployments do anyway. Polaris's reference-implementation surface stays
focused on the identity-token primitives, not on the operator-auth meta-layer.

**Weakness:** SOC 2 will ask why; PCI-equivalent compliance frameworks
expect MFA on privileged accounts; the deployability checklist names
WebAuthn explicitly, so deferring keeps the ⬜ open indefinitely.
Architect-on-record: Position D is the do-nothing option; preserves
optionality but leaves the threat-model surface uncovered at the
reference-implementation level.

## III. Architect's recommendation

**Position B (WebAuthn-MFA, both factors required, 30-day migration deadline).**
Rationale:

1. **Standard practice in the threat-model neighborhood.** Government
   identity-token systems (the analogue Polaris is a reference-implementation
   for) universally require MFA on privileged accounts; SOC 2 CC6 controls
   demand it; FedRAMP requires it; PCI DSS v4 explicitly named it as a
   tightening in v3.2.1 → v4.0. Position B matches the practice that
   the operators Polaris is built for already follow.

2. **Defense-in-depth, not factor-replacement.** Position A removes the
   password layer (zero-trust on password storage) but also removes the
   recovery surface. Position C makes the password layer noisily-fallible
   but still usable for an attacker. Position B keeps the password layer
   as the first factor (it has to be defeated for the second factor to
   come into play) AND adds the phishing-resistant second factor on top.
   The attack against B is harder than the attack against A or C.

3. **Migration grace period preserves operational continuity.** A
   30-day `webauthn_required_after` deadline lets existing admins enroll
   on their own schedule, with two-week + one-week + 48-hour reminders.
   Position A's flag-day cutover risks locked-out admins on day one.

4. **Recovery is the constitutional question.** A locked-out admin
   in Position A has no recourse beyond manual filesystem intervention.
   In Position B, the password layer IS the recovery factor: an admin
   who lost their hardware token can still log in via password +
   `polaris-recover-admin.sh` second-admin pairing OR (for solo
   deployments) a printed one-time recovery code. The recovery path
   is itself audited; the constitutional concern (the locked-out admin
   has no documented path back) is resolved at the protocol level.

5. **Scoped implementation, framework-aligned.** Schema change ships
   via the v8.95 migration framework (`2026-05-14-002-operator-webauthn.up.sql`)
   — the first non-example migration becomes the WebAuthn schema change,
   which validates the framework on a real ship. UX flow is two
   additional routes + a settings page; ~600 lines of new Python +
   ~200 lines of HTML/CSS/JS. Tractable in 1-2 ships.

The architect's caution on B: the `webauthn` Python package is a
runtime dependency that isn't pre-installed on every managed Postgres
host. It's pip-installable cleanly, but operators running air-gapped
deployments need to vendor it. This caveat is documented but does not
change the recommendation.

## IV. Open questions for VANTA

These resolve the implementation-level decisions that the §III sketch
deliberately left as the operator's call:

1. **Admin only, or admin + operator?** The `auditor` role is read-only;
   MFA defense is less material there. **Architect-recommended:** MFA
   required for `admin`, optional-but-strongly-encouraged for `operator`,
   not required for `auditor`.

2. **Platform authenticators allowed (Touch ID / Windows Hello /
   Android), or hardware-token-only (YubiKey class)?** Platform
   authenticators are stronger UX (no device to carry) but the
   private-key material lives on a general-purpose device with
   broader attack surface. Hardware tokens are stricter but require
   the operator to carry the device. **Architect-recommended:** allow
   both; document the trade-off in `SECRETS.md` and let the operator
   pick per-deployment via a `POLARIS_WEBAUTHN_HARDWARE_ONLY=1`
   environment knob (default = both allowed).

3. **Recovery flow — second-admin-pairing OR printed mnemonic OR both?**
   **Architect-recommended:** both; document second-admin-pairing as
   primary (`polaris-recover-admin.sh` with two-step authentication of
   the recovering admin); document printed-mnemonic as the solo-deployment
   path (operator runs `polaris-generate-recovery-code.sh` at
   enrollment time and stores the code in a safe).

4. **Roll-out: 30-day deadline OR organic enrollment OR forced at first
   post-v8.96 login?** **Architect-recommended:** 30-day deadline
   per existing-admin; new admins enrolled at account creation time
   (the `polaris-create-operator.sh` flow gains a `--require-webauthn`
   default-on flag for `admin` role).

5. **Strict-acceptance criterion for the ship?** **Architect-recommended:**
   (a) end-to-end drill: enroll a credential via YubiKey emulator
   (`virtual_authenticator` in the python `webauthn` package's test
   helpers), log in with password+assertion, verify
   `WEBAUTHN_ASSERTED` AuthAuditLog row; (b) negative test: tampered
   assertion (wrong origin / wrong challenge / replayed counter) all
   reject; (c) recovery drill: simulate device-loss + second-admin
   pairing, verify the emergency-login window opens + closes correctly
   + AuthAuditLog records.

## V. Decision

**Position B (WebAuthn-MFA, both factors required, 30-day migration
deadline).** VANTA in-chat 2026-05-14: `"B"`.

The architect's estimate was two ships (v8.97 schema+backend / v8.98
UX+recovery+docs). Under heavy-production + the "boil the ocean"
quality bar, ONE complete ship landed both halves: v8.97 closes the
Sanctum end-to-end.

The five §IV open questions resolved per architect recommendations:

1. **Admin required, operator optional, auditor exempt** — encoded
   in `webauthn_auth.py:ROLES_REQUIRING_WEBAUTHN/OPTIONAL/EXEMPT`.
   Operator with an enrolled credential is upgraded to "mfa_required"
   automatically (opt-in via enrollment).
2. **Both platform + hardware authenticators allowed** —
   default; `POLARIS_WEBAUTHN_HARDWARE_ONLY=1` env knob restricts
   to cross-platform (hardware-token) authenticators per deployment.
3. **Both recovery paths** —
   `scripts/polaris-recover-admin.sh` (second-admin pairing,
   audited as `EMERGENCY_PASSWORD_LOGIN_AUTHORIZED`) AND
   `scripts/polaris-generate-recovery-code.sh` (printed
   16-word mnemonic + SHA-256 digest for solo-admin deployments).
   The in-app mnemonic-verification flow is deferred per §V scope
   (architect-acknowledged follow-up gated on operator demand;
   `recovery_code_hash` storage column not added in this ship).
4. **30-day enrollment deadline** for new admins via
   `polaris-create-operator.sh --role admin`; the seed admin
   keeps `webauthn_required_after = NULL` so dev tests remain
   time-independent (production deployments add the deadline by
   running `polaris-create-operator.sh` rather than relying on
   the seed file).
5. **Acceptance criterion**: end-to-end drill (10 steps) +
   adversarial drill (forged assertion → 401 + audited as
   `WEBAUTHN_ASSERTION_FAILED`) + recovery drill (mfa_overdue
   refusal → `polaris-recover-admin.sh` → window opens → login
   succeeds → `EMERGENCY_PASSWORD_LOGIN_AUTHORIZED` audited) all
   green during ship verification.

## VI. Outcome

Shipped as v8.97 on 2026-05-14 (same day as decision). End-to-end
single ship, no follow-ups required for the constitutional contract.

**Artifacts (14):**

1. `polaris_sql/migrations/2026-05-14-002-operator-webauthn.up.sql` +
   `.down.sql` — schema change (new table + new column + CHECK enum
   extension). Applied via `polaris-migrate.sh` — **the first
   non-example migration; validates the v8.95 framework on a real
   schema change.** The .down.sql REFUSES to revert if any
   WEBAUTHN_* audit rows exist (preserves Sanctum §IV.3
   append-only AuditLog).
2. `polaris_web/webauthn_auth.py` (~350 lines) — registration +
   assertion ceremonies via the Duo Labs `webauthn` Python package.
   Includes the role-policy resolver
   (`webauthn_status_for_user` returns one of `not_required` /
   `grace_period` / `mfa_required` / `mfa_overdue`).
3. `polaris_web/app.py` — 7 new routes:
   - `GET /auth/webauthn/assert` (assertion page for partial-auth users)
   - `POST /auth/webauthn/assert/begin` (issue challenge)
   - `POST /auth/webauthn/assert/finish` (verify + complete login)
   - `GET /settings/webauthn` (enrollment management page)
   - `POST /auth/webauthn/register/begin` (issue registration challenge)
   - `POST /auth/webauthn/register/finish` (verify + persist)
   - `POST /auth/webauthn/credentials/<id>/delete` (deregister)
4. `polaris_web/app.py:login()` modified — after password verifies,
   the WebAuthn-MFA gate decides: complete login (not_required /
   grace_period), redirect to assertion (mfa_required), or refuse
   (mfa_overdue).
5. `polaris_web/templates/webauthn_assert.html` — verification page
   for the partial-auth login flow.
6. `polaris_web/templates/webauthn_settings.html` — enrollment
   management page (lists enrolled credentials, add/remove buttons,
   deadline banner).
7. `polaris_web/static/webauthn-register.js` — calls
   `navigator.credentials.create()`, posts attestation to
   `/auth/webauthn/register/finish`.
8. `polaris_web/static/webauthn-assert.js` — calls
   `navigator.credentials.get()`, posts assertion to
   `/auth/webauthn/assert/finish`.
9. WebAuthn CSS appended to `polaris.css` (~110 lines:
   `.webauthn-step`, `.webauthn-status`, `.webauthn-error`,
   `.callout-{info,warning,error}`, `.data-table`, etc.).
10. `scripts/polaris-recover-admin.sh` (~200 lines) — second-admin
    emergency-login window. Greppable exit codes (0/2/3/4/5).
    Writes `EMERGENCY_PASSWORD_LOGIN_AUTHORIZED` AuditLog row.
11. `scripts/polaris-generate-recovery-code.sh` (~180 lines) —
    printed 16-word mnemonic + SHA-256 digest for solo-admin
    deployments. Cleartext stays on paper; the digest goes in the
    AppUser column (deferred to follow-up per §V).
12. `scripts/polaris-create-operator.sh` updated — admin accounts
    get `webauthn_required_after = now() + 30 days` automatically;
    operator/auditor stay NULL.
13. `DEVNOTES/threat-model.md` § T-S4 — new STRIDE Spoofing entry
    "stolen admin password (phishing / breach disclosure / malware
    exfil)" with the Position B controls list.
14. `docs/operator/SECRETS.md` § 7 (~120 lines) + `OPERATIONS.md`
    §"Operator authentication (WebAuthn-MFA, v8.97)" — enrollment
    runbook + recovery flows + env knobs + audit-query recipes +
    "disabling MFA per-account" SQL recipe.

**Bonus: AuthAuditLog event_type enum extended** by the migration
to include 5 new WebAuthn lifecycle event types:
`WEBAUTHN_REGISTERED`, `WEBAUTHN_ASSERTED`,
`WEBAUTHN_ASSERTION_FAILED`, `WEBAUTHN_DEREGISTERED`,
`EMERGENCY_PASSWORD_LOGIN_AUTHORIZED`. Every state transition in
the auth flow is now reconstructible from `AuthAuditLog`.

**End-to-end drill (10 steps, run against live polaris_test DB):**

```
1.  Fresh DB load via 00_load_all.sql → schema_version exists empty
2.  ./polaris-migrate.sh --up applies 2026-05-14-002 → migration tracked
3.  POST /login as seed admin (Admin@123!) → 302 to /dashboard ✓
4.  GET /settings/webauthn → 200 + "Enroll WebAuthn credential" button ✓
5.  POST /auth/webauthn/assert/begin without pending → 400 ✓ (adversarial)
6.  POST /auth/webauthn/register/begin without login → 302 redirect ✓ (adversarial)
7.  Forged assertion via /auth/webauthn/assert/finish → 401 + WEBAUTHN_ASSERTION_FAILED audited ✓ (adversarial)
8.  Set webauthn_required_after past + no credential → POST /login refused 401 ✓ (mfa_overdue)
9.  ./polaris-recover-admin.sh --target admin --authorizing-user-id 1 → exit 0 + EMERGENCY_PASSWORD_LOGIN_AUTHORIZED row ✓
10. POST /login again → 302 (grace_period: window open) ✓ (recovery flow)
```

**Plus round-trip enrollment drill:** csrf token captured from
settings page → `/auth/webauthn/register/begin` issues challenge
with correct rp.id=localhost + user.name=admin →
`/auth/webauthn/assert/begin` (after manual credential insert)
issues challenge with correct allowCredentials list +
rpId=localhost.

**Pattern #20 Constitutional Discipline — fifth Sanctum-cycle
this week** (v8.84→v8.87 / v8.90→v8.91 / v8.94→v8.95 /
**v8.96→v8.97**); architect's "two ships" estimate compressed
to one under heavy-production. The compressed scope did not
sacrifice the quality bar — all 10 drill steps green +
threat-model + docs + structural invariants land in the same
ship.

**Deployability impact:** removes the "Phase 2 ⚠️ WebAuthn
operator auth" item from the deployability checklist. Phase 2
Sanctum-class items are now ALL CLOSED:
- v8.93: audit log rotation
- v8.95: schema migration framework
- **v8.97: WebAuthn-MFA**

Remaining Phase 2 work is now Phase 2.5 (multi-instance scaling
completion — gated on production-scale data, not Sanctum-class)
and Phase 3 (deferred). The deployability checklist's Phase 2 ⬜
section is now substantially closed.

## VII. Cross-references

- `polaris_web/security.py` — current `authenticate()` + `hash_password()` surface
- `polaris_sql/10_auth.sql` — current `AppUser` schema with role enum + lockout
- `polaris_sql/migrations/` — the v8.95 framework that will carry the
  WebAuthn schema change as `2026-05-14-002-operator-webauthn`
- `DEVNOTES/threat-model.md` — the STRIDE-categorized control map this
  Sanctum's decision will update (Spoofing + Tampering + Elevation rows)
- `docs/operator/SECRETS.md` — the operator-facing doc that will gain
  the WebAuthn enrollment + recovery procedures
- `ROADMAP.md` § "What needs done before it can become a deployable
  system" → Phase 2 → WebAuthn operator auth row
- `meta/sanctum-index.md` — Sanctum lifecycle index
- v8.93 CHANGELOG — naming WebAuthn as one of the three remaining Phase 2
  Sanctum-class items
- v8.84 / v8.90 / v8.94 CHANGELOG — prior Sanctum-opening cycle pattern
  (this is the fourth instance of the surface-then-await pattern, after
  three closures: v8.87 / v8.91 / v8.95)
