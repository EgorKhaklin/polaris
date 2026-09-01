# WebAuthn rollout runbook

**Status:** Phased rollout procedure for operator-facing WebAuthn-MFA
**Last reviewed:** 2026-05-15 (v9.23)

This document is the operator-facing rollout procedure for the
WebAuthn-MFA infrastructure shipped in v8.97. The infrastructure is
complete: registration, assertion, the four-state status machine
(`not_required` / `grace_period` / `mfa_required` / `mfa_overdue`),
and the `_hardware_only()` policy hook all exist. What the operator
must do is decide *when* enforcement begins for each admin/operator
account, and walk them through the enrollment.

The implementation reference is `polaris_web/webauthn_auth.py`. The
login-flow integration is `polaris_web/app.py:495-575` (the `/login`
route). The end-to-end test coverage is in
`polaris_web/test_app.py::Webauthn*` test classes.

---

## Architecture (5-minute brief)

As of v8.97, WebAuthn is:

- **Mandatory for admin role.** The `AppUser.webauthn_required_after`
  column governs enforcement: if NULL, never enforced; if set, the
  state machine enforces based on time-remaining and credential
  presence.
- **Optional for operator role.** If the operator enrolls a credential,
  it's required from that point. If they don't, login completes with
  password alone.
- **Exempt for auditor role.** Auditors are read-only; the threat
  model assesses that single-factor for read-only is acceptable.
- **Hardware-only mode available.** Set `POLARIS_WEBAUTHN_HARDWARE_ONLY=1`
  in the environment to reject software authenticators (require
  external security key like YubiKey). Default: software authenticators
  permitted (lets the operator self-bootstrap with platform
  authenticator before procuring hardware keys).
- **Attestation policy (v9.189).** `POLARIS_WEBAUTHN_ATTESTATION`,
  `POLARIS_WEBAUTHN_USER_VERIFICATION`, `POLARIS_WEBAUTHN_REQUIRE_ATTESTATION`,
  and `POLARIS_WEBAUTHN_ALLOWED_AAGUIDS` raise the bar step by step
  (Phase 6 below). Defaults reproduce the pre-v9.189 behaviour exactly.
- **Post-quantum ready (v9.189).** The registration options offer ML-DSA-65
  (COSE -49) first, the same parameter set as the token signature, then
  ES256, EdDSA, and RS256. An authenticator that implements ML-DSA enrolls
  a post-quantum credential and the settings page labels it; every
  shipping authenticator today enrolls a classical one. The relying party
  is ready before the hardware is.

The four states the system can be in for a given user:

| State           | webauthn_required_after | credential count | Login behavior |
|-----------------|--------------------------|------------------|----------------|
| `not_required` | NULL OR operator-no-cred | 0 (operator)     | Login completes with password |
| `grace_period` | future                   | 0                | Login completes with banner reminding to enroll |
| `mfa_required` | (any)                    | ≥ 1              | Login forwards to /auth/webauthn/assert |
| `mfa_overdue`  | past                     | 0                | Login REFUSED with recovery guidance |

---

## Phase 0: pre-flight

```bash
# Confirm WebAuthn substrate is present
psql -d polaris -c "\d OperatorWebauthnCredential"
psql -d polaris -c "\d AppUser" | grep webauthn_required_after

# Confirm /settings/webauthn route serves (operator-only)
curl -fsS http://localhost:2222/settings/webauthn
# expect 302 → /login if not logged in

# Confirm structural invariants pass
cd /path/to/polaris && ./scripts/ai-test.sh quick 2>&1 | grep -i webauthn
```

If any of these fail: stop. Run `./scripts/polaris-migrate.sh --up`
first. If still failing, file an issue per `SECURITY.md`.

---

## Phase 1: enroll yourself

The operator (you) enrolls first. This is so that the recovery-flow
(Phase 2) does not lock the entire system out.

```bash
# 1. Log in to Polaris as admin (password only, no WebAuthn yet)
# 2. Navigate to /settings/webauthn
# 3. Click "Add a new credential"
# 4. Browser prompts for authenticator (platform OR external)
# 5. Confirm the enrollment in the browser
# 6. Polaris shows the credential with a device label of your choice
```

After enrollment, log out and log in again. The login flow now goes
through `/auth/webauthn/assert`. Verify this works end-to-end before
proceeding.

**Recommendation:** enroll *two* credentials on your account — one
platform (Touch ID / Windows Hello) and one external (YubiKey or
similar). Hardware loss is the single most common operator-side
lockout cause.

---

## Phase 2: set the deadline on a *second* admin account

Before enabling enforcement for your own account, ensure there is a
second admin you can recover via. This is the
`scripts/polaris-recover-admin.sh` (v8.97) pairing flow — a second
admin can authorize a short emergency-login window for the first
admin who lost their authenticator.

```bash
# Confirm a second admin exists
psql -d polaris -c "SELECT user_id, username, role FROM AppUser
                    WHERE role='admin' ORDER BY user_id"

# If only one admin exists, create another:
./scripts/polaris-create-operator.sh second-admin admin
```

Have the second admin enroll their credential (Phase 1 for them).

---

## Phase 3: set the deadline (the new artifact in v9.23)

`scripts/polaris-set-webauthn-deadline.sh` (v9.23) sets the
`webauthn_required_after` column. Defaults to 30 days from now;
override with `--days N`.

```bash
# Set deadline for your own account (the user enrolled in Phase 1)
./scripts/polaris-set-webauthn-deadline.sh --username your-admin --days 30

# Set deadline for the second admin (Phase 2)
./scripts/polaris-set-webauthn-deadline.sh --username second-admin --days 30

# Set deadline for all operators (organization-wide rollout)
./scripts/polaris-set-webauthn-deadline.sh --all-admins --days 60

# Dry-run (show what would change)
./scripts/polaris-set-webauthn-deadline.sh --all-admins --days 60 --dry-run
```

The script:

- Refuses to set a deadline shorter than 7 days unless `--force`
  (prevents accidental same-day lockouts)
- Refuses to set a deadline on a role that is not admin/operator
- Refuses to lower an existing deadline below 7 days remaining
  (operator-protection invariant)
- Writes an audit row to the audit log:
  `WEBAUTHN_DEADLINE_SET (by=$ADMIN target=$TARGET deadline=$DEADLINE)`
- Returns non-zero on any failure; greppable from cron logs

Operator vocation note: the script REFUSES to set a deadline in the
past. Setting a deadline in the past would immediately lock out the
target admin, which is a coercion vector (an attacker who briefly
compromises the admin role could set deadlines in the past on all
other admins). Anti-coercion invariant.

---

## Phase 4: enforce

When the deadline arrives:

- Users who enrolled (Phase 1) continue to log in via WebAuthn (state
  `mfa_required`).
- Users who did NOT enroll get state `mfa_overdue` and are refused
  login. They must contact a second admin and run
  `scripts/polaris-recover-admin.sh` for emergency-login,
  OR use a printed recovery code from
  `scripts/polaris-generate-recovery-code.sh`.

Monitor the audit log for `LOGIN_FAILED` rows with detail
`WebAuthn enrollment deadline passed`. Each one represents an
operator who did not complete enrollment in time.

---

## Phase 5: hardware-only escalation (optional)

After Phase 4 stabilizes (default: 30-60 days), the operator may
choose to escalate to hardware-only:

```bash
# In production env file
POLARIS_WEBAUTHN_HARDWARE_ONLY=1

# Restart the stack
./scripts/polaris-deploy.sh prod
```

This rejects software authenticators (platform Touch ID / Windows
Hello / etc.) at registration time and rejects assertions from
authenticators that the browser reports as not user-verifiable
hardware. External security keys (YubiKey, SoloKey, etc.) continue
to work.

Existing enrollments are NOT invalidated when this flag flips; only
new registrations are constrained. To force re-enrollment with
hardware-only credentials:

```bash
psql -d polaris -c "DELETE FROM OperatorWebauthnCredential
                    WHERE attestation_format = 'none'"
# (rough heuristic; actual filter depends on attestation policy)
```

This is a destructive operation: it invalidates existing credentials
and forces every affected operator to re-enroll. Confirm a recovery
path (second admin or printed recovery code) is in place first.

---

## Phase 6: attestation policy (optional, v9.189)

Phase 5 restricts the KIND of authenticator. Phase 6 restricts what the
authenticator must PROVE. Each step is one environment variable, read at
start (a bad value refuses the boot), and each refusal is audited as
`WEBAUTHN_REGISTRATION_REFUSED` with `policy:` in the detail.

1. **Require user verification.** `POLARIS_WEBAUTHN_USER_VERIFICATION=required`
   makes the PIN or biometric mandatory on enrollment AND on every
   assertion (the UV flag is checked server-side on both ceremonies), so a
   security key lifted from a desk cannot complete the second factor without
   its PIN. `preferred` (the default) asks for it but accepts a key that did
   not perform it; `discouraged` never asks.
2. **Ask for a real attestation.** `POLARIS_WEBAUTHN_ATTESTATION=direct`
   asks the browser to pass the authenticator's own attestation statement
   through (`indirect` lets the client anonymise it; `enterprise` requests
   the enterprise attestation an authenticator may hold; `none`, the
   default, asks for nothing). The library verifies packed, TPM, FIDO-U2F,
   Android-key, Android-SafetyNet, and Apple statements against their roots.
3. **Refuse enrollments without one.**
   `POLARIS_WEBAUTHN_REQUIRE_ATTESTATION=1` refuses a registration whose
   attestation format is `none`, which is what a browser returns when the
   authenticator cannot or will not attest. Only meaningful together with
   `direct`.
4. **Pin the fleet.** `POLARIS_WEBAUTHN_ALLOWED_AAGUIDS=<uuid>,<uuid>` refuses
   any authenticator model not on the list. An AAGUID is only trustworthy
   inside a verified attestation (under `none` the client zeroes it, so the
   list would refuse everything), so this step presumes steps 2 and 3.

Existing enrollments are not re-examined when a knob changes; the policy
applies to new registrations and, for user verification, to every assertion.
The pre-v9.189 credential rows stored the attestation format as the enum
repr (`AttestationFormat.NONE`); v9.189 stores the wire name (`none`,
`packed`, ...), which is what the Phase 5 filter above matches.

The credential's algorithm is visible on `/settings/webauthn`
("ML-DSA-65 (post-quantum)" or "ES256 (ECDSA P-256)" and so on), so an
operator can see which enrollments are already post-quantum once such
authenticators exist.

---

## Recovery procedures

### Operator lost their authenticator + deadline passed

```bash
# Run from a *different* admin's account
./scripts/polaris-recover-admin.sh --target $LOCKED_USERNAME --window-minutes 15

# Inside the 15-minute window, the locked operator logs in with their
# password. They land in grace_period state. They enroll a new
# credential at /settings/webauthn. State returns to mfa_required.
```

### Operator lost their authenticator AND no second admin available

Use a printed recovery code:

```bash
# (Generated at initial deploy via scripts/polaris-generate-recovery-code.sh)
# Operator enters the printed code at /auth/recovery
# Single-use; logs in once; must enroll a new credential before logging out
```

If neither recovery path is available, the operator must rebuild from
backup:

```bash
./scripts/polaris-restore.sh /var/backups/polaris-{latest}.tar.gz \
  --skip-fs  # keeps the current on-disk filesystem state
# Then re-deploy with WEBAUTHN_REQUIRED_AFTER reset to NULL for that user
```

A recovery from backup is an audit-of-record event. The append-only
audit tables (C1) record the restore; confirm those rows are present
after recovery.

---

## Vocation alignment

ANTI-COERCION-DIRECT. Hardware-token requirements raise coercion
cost: an attacker can extort a password from a coerced operator;
they cannot extort the physical possession of a hardware key without
physical presence. The `polaris-recover-admin.sh` two-admin pairing
preserves the "no single admin can be coerced into action" property
that aligns with the vocation.

The `polaris-set-webauthn-deadline.sh` refuses-to-set-past-deadline
invariant is itself an anti-coercion structural guarantee — it
prevents a briefly-coerced admin from being weaponized to lock out
all other admins.

---

## Structural invariants

`TestWave23V923` (v9.23) adds:

- `test_webauthn_set_deadline_script_exists`
- `test_webauthn_set_deadline_refuses_past`
- `test_webauthn_rollout_doc_exists_and_references_recover_admin`

These verify the operator runbook + script ship together.

---

## Related

- `polaris_web/webauthn_auth.py` (full implementation; v9.189 adds the
  attestation policy and the ML-DSA-65 offer)
- `scripts/polaris-recover-admin.sh` (v8.97 recovery flow)
- `scripts/polaris-set-webauthn-deadline.sh` (v9.23 deadline-set
  helper)
- `scripts/polaris-generate-recovery-code.sh` (recovery code path)
