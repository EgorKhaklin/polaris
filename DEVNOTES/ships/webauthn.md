# DEVNOTES/ships/webauthn.md

**Introduced:** v8.97. Shipped end-to-end same-day; first non-example
migration via the v8.95 framework.

This file is the canonical write-up for Polaris's WebAuthn-MFA operator
authentication: how operator credentials are registered, how MFA is
enforced, what the grace period actually buys, and which surfaces an
attacker has to break to bypass it.

---

## What WebAuthn-MFA enforces

Operator login (`/login`) is password-only by default, BUT every
`AppUser` row has a `webauthn_required_after` timestamp (nullable). Once
that timestamp passes, the login flow refuses to proceed past password
verification until the operator presents a valid WebAuthn assertion
against a credential they previously registered. The flow has three
states:

| State | Condition | Behavior |
|---|---|---|
| **no_mfa** | `webauthn_required_after IS NULL` | Password is sufficient |
| **grace_period** | NOW < `webauthn_required_after` | Password works; warning banner urges enrollment |
| **mfa_required** | NOW ≥ `webauthn_required_after` AND credentials registered | Password + WebAuthn assertion both required |
| **mfa_overdue** | NOW ≥ `webauthn_required_after` AND no credentials | Login REFUSED with admin-recovery instructions |

New operators created via `scripts/polaris-create-operator.sh` get a
30-day grace period. Existing operators have no deadline unless
`scripts/polaris-set-webauthn-deadline.sh` sets one.

## Architecture

| File | Role |
|---|---|
| `polaris_web/webauthn_auth.py` (~458 lines) | Registration + assertion ceremonies; wraps the Duo Labs `webauthn` Python package |
| `polaris_web/app.py` | 7 routes: `/auth/webauthn/{register/begin,register/finish,assert/begin,assert/finish}`, `/settings/webauthn`, `/settings/webauthn/credentials/<id>/delete` |
| `polaris_web/templates/webauthn_assert.html` + `webauthn_settings.html` | UI surfaces |
| `polaris_web/static/webauthn-{register,assert}.js` | Browser-side ceremony (calls `navigator.credentials.create/get`) |
| Schema migration `2026-05-14-002-operator-webauthn` | Adds `OperatorWebauthnCredential` table + `AppUser.webauthn_required_after` column + 5 new `AuthAuditLog` event types |

## Test coverage

- `polaris_web/test_app.py::WebAuthnTests` — end-to-end ceremony tests
  (register → assert → mfa_required state machine)
- `polaris_web/test_app.py::WebAuthnAdversarialTests` — forged-assertion
  rejection, register-without-login rejection, begin-without-pending
  rejection
- `polaris_web/test_structural_invariants.py` — schema invariants on
  `OperatorWebauthnCredential` (FK to AppUser, public_key bytes
  required, transports JSONB)
- Round-trip drill verified at v8.97 ship-time (10-step manual drill).

## Operator-recovery path

The single-credential-loss attack is mitigated by a paired-admin
recovery:

1. `scripts/polaris-recover-admin.sh` requires TWO admins to be present;
   one (the locked-out one) cannot recover themselves.
2. `scripts/polaris-generate-recovery-code.sh` emits a printed mnemonic
   at operator-creation time. This is the second factor for the
   recovery ceremony itself.

By design, there is NO bypass path. A single-admin deployment with the
only admin locked out is by-design unrecoverable without restoring from
backup. The constitutional clause "identity is
not money" extends here: the operator-auth surface is intentionally
non-monetary in its blast radius.

## What this primitive does NOT do

- It does NOT cover holder-side authentication (Polaris holders don't
  log in; they're identified by their `Individual` row + token).
- It does NOT support U2F (legacy non-WebAuthn). The schema requires a
  CTAP2 / FIDO2 credential.
- It does NOT support biometric-only auth — every credential requires
  a hardware authenticator (resident or roaming key).
- It does NOT solve the "lost both admins simultaneously" problem
  (operator-side procedural; out of scope for this primitive).

## Maintenance posture

Stable. Three known classes of future work:
1. **Attestation verification** — currently the server records the
   attestation statement but does not verify the AAGUID against a
   metadata service. A future hardening pass could enforce
   FIDO-Metadata-Service certification.
2. **Cross-device passkey support** — the current credential schema
   assumes per-device credentials; syncing platforms (iCloud Keychain,
   Google Password Manager) work today but the audit log doesn't
   distinguish them.
3. **Conditional UI** — using `mediation: 'conditional'` to surface
   credentials at password-field focus rather than after submit;
   pure UX improvement.

## Cross-references

- `polaris_web/webauthn_auth.py` — the implementation
- `polaris_sql/migrations/2026-05-14-002-operator-webauthn.up.sql` — the
  schema migration
- `MISSION.md` §Vocation — the anti-coercion rationale (operator
  compulsion resistance)
