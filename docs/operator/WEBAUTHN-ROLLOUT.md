# WebAuthn rollout

**Reader:** the operator who turns on WebAuthn MFA for the admin and
operator accounts of a Polaris deployment. **Job:** enroll credentials, set
enforcement deadlines, escalate the authenticator policy, recover a
locked-out admin, and know how to lift the requirement on one account.

**Last reviewed:** 2026-09-02

The implementation is
[`polaris_web/webauthn_auth.py`](../../polaris_web/webauthn_auth.py); the
`/login` route in [`polaris_web/app.py`](../../polaris_web/app.py) consults it
on every password login. Test coverage is `WebAuthnCeremonyTests` and
`WebAuthnCredentialLookupTests` in
[`polaris_web/test_app.py`](../../polaris_web/test_app.py). The infrastructure
is complete; what the operator decides is WHEN enforcement begins for each
account.

---

## Architecture

- **Mandatory for the admin role once a deadline is set.** The
  `AppUser.webauthn_required_after` column governs enforcement: NULL means
  never enforced; a timestamp means the state machine below applies.
  `polaris-create-operator.sh` sets it to now + 30 days for every new admin.
- **Optional for the operator role.** An operator who enrolls a credential
  must present it from then on; one who has not enrolled logs in with the
  password alone.
- **Exempt for the auditor role** (`ROLES_EXEMPT_WEBAUTHN`). Auditors are
  read-only; single-factor for a read-only role is the accepted risk.
- **Post-quantum ready.** Registration options offer ML-DSA-65 (COSE -49)
  first, then ES256, EdDSA, and RS256. An authenticator that implements
  ML-DSA enrolls a post-quantum credential and `/settings/webauthn` labels it
  "ML-DSA-65 (post-quantum)"; every shipping authenticator today enrolls a
  classical one.

The four states `webauthn_status_for_user` can return:

| State | `webauthn_required_after` | credential count | Login behavior |
|---|---|---|---|
| `not_required` | NULL, or the auditor role, or an operator with no credential | 0 | completes with the password |
| `grace_period` | in the future | 0 | completes, with a warning banner naming the days left |
| `mfa_required` | any | 1 or more | forwards to `/auth/webauthn/assert` |
| `mfa_overdue` | in the past | 0 | refused with HTTP 401; audited as `LOGIN_FAILED` with detail `WebAuthn enrollment deadline passed; no credential enrolled` |

---

## Environment knobs

Every knob is read at start from the environment (the production compose
file passes each one through from the shell or `/etc/polaris/polaris.env`;
[`deploy/linux/polaris.env.example`](../../deploy/linux/polaris.env.example)
lists them commented out). A bad value refuses the boot.

| Variable | Values | Effect |
|---|---|---|
| `POLARIS_DOMAIN` | hostname | the WebAuthn relying-party ID; assertions are origin-bound to it. Falls back to `localhost` in dev |
| `POLARIS_WEBAUTHN_RP_NAME` | text, default `Polaris` | the relying-party display name the browser shows during the ceremony |
| `POLARIS_WEBAUTHN_HARDWARE_ONLY` | `1` or unset | at registration, ask the browser for a cross-platform authenticator only (YubiKey class), so platform authenticators (Touch ID, Windows Hello, Android biometric) are not offered; the server does not verify attachment. Default: both |
| `POLARIS_WEBAUTHN_ATTESTATION` | `none` (default), `indirect`, `direct`, `enterprise` | the attestation conveyance asked of the browser at enrollment |
| `POLARIS_WEBAUTHN_USER_VERIFICATION` | `preferred` (default), `required`, `discouraged` | whether the PIN or biometric is demanded; `required` is checked server-side on enrollment AND every assertion |
| `POLARIS_WEBAUTHN_REQUIRE_ATTESTATION` | `1` or unset | refuse an enrollment whose attestation format is `none`; pair with `direct` |
| `POLARIS_WEBAUTHN_ALLOWED_AAGUIDS` | comma-separated UUIDs | refuse any authenticator model not on the list at enrollment |

Phase 6 below explains how the last four combine.

---

## Phase 0: pre-flight

```bash
# Confirm the WebAuthn substrate is present
psql -d polaris -c "\d OperatorWebauthnCredential"
psql -d polaris -c "\d AppUser" | grep -E "webauthn_required_after|recovery_code_hash"

# Confirm /settings/webauthn serves (login required)
curl -fsS -o /dev/null -w '%{http_code}\n' "https://${POLARIS_DOMAIN}/settings/webauthn"
# expect 302 to /login when not logged in
# (on the mac dev launcher the app listens on http://localhost:2222 instead;
#  in the compose stack the app is reachable only through Caddy)

# Confirm the WebAuthn ceremony tests pass (needs the 3.12 venv, Postgres, Redis)
cd /path/to/polaris && ./scripts/ai-test.sh quick 2>&1 | grep -i webauthn

# Confirm the structural invariants pass
cd /path/to/polaris && python3 -m polaris_checks.run
```

If any of these fail: stop. Run `./scripts/polaris-migrate.sh --up` first
(the WebAuthn credential table and the recovery-code column are migrations
`2026-05-14-002` and `2026-05-14-003`; the `WEBAUTHN_REGISTRATION_REFUSED`
event type that Phase 6 audits is admitted by `2026-09-01-001`, and without it
the refusal audit row silently fails the `chk_authaudit_event_type` CHECK).
If still failing, file an issue per
[SECURITY.md](SECURITY.md).

---

## Phase 1: enroll yourself

The operator running the rollout enrolls first, so the recovery flow in
Phase 2 never has to start from a fully locked-out system.

1. Sign in with the password as the admin (allowed while the account is in
   `grace_period`).
2. Open `/settings/webauthn`.
3. Click **Enroll WebAuthn credential**. The browser prompts for a hardware
   security key or a platform authenticator, subject to
   `POLARIS_WEBAUTHN_HARDWARE_ONLY`.
4. Give the device a label (for example `YubiKey 5C work-laptop`) and
   confirm. The credential is stored in `OperatorWebauthnCredential`.
5. Verify the audit row landed:

   ```sql
   SELECT event_timestamp, event_type, username
     FROM AuthAuditLog
    WHERE event_type = 'WEBAUTHN_REGISTERED'
    ORDER BY event_timestamp DESC LIMIT 5;
   ```

6. Log out and log in again. The login now passes through
   `/auth/webauthn/assert`. Confirm this works end to end before moving on.

Enroll a second credential on your own account: one platform authenticator
and one external key. Hardware loss is the most common operator-side lockout
cause, and two credentials remove the single point of failure. A lost
authenticator whose credential row still exists keeps the account in
`mfa_required`; the emergency window in [Recovery](#recovery) does not lift
that state, so delete the lost credential's row first.

---

## Phase 2: a second admin

Before enforcing on your own account, make sure a second admin exists who can
authorize an emergency window for you
([Recovery: second-admin pairing](#recovery-second-admin-pairing)).

```bash
# Confirm a second admin exists
psql -d polaris -c "SELECT user_id, username, role FROM AppUser
                    WHERE role = 'admin' ORDER BY user_id"

# If only one admin exists, create another (password read from stdin or a file, never argv)
./scripts/polaris-create-operator.sh --username second-admin --role admin
```

Have the second admin complete Phase 1 for their own account.

A deployment that will only ever have one admin binds a printed recovery
mnemonic instead
([Recovery: solo admin with a printed mnemonic](#recovery-solo-admin-with-a-printed-mnemonic)).
Do this in Phase 2 as well; it is the only self-service recovery path.

---

## Phase 3: set the deadline

[`scripts/polaris-set-webauthn-deadline.sh`](../../scripts/polaris-set-webauthn-deadline.sh)
sets `webauthn_required_after`. The default is 30 days from now; override
with `--days N`. The script has no `--target=docker-stack` option: it runs
`psql -h $POLARIS_DB_HOST -U $POLARIS_DB_USER -d $POLARIS_DB_NAME` (defaults
`localhost`, `polaris_app`, `polaris`) and exits 3 when the database is
unreachable. On the compose stack, where Postgres publishes no host port,
export those variables for a reachable Postgres or set `POLARIS_PSQL` to a
command that runs `psql` inside the postgres container.

```bash
# Your own account (enrolled in Phase 1)
./scripts/polaris-set-webauthn-deadline.sh --username your-admin --days 30

# The second admin (Phase 2)
./scripts/polaris-set-webauthn-deadline.sh --username second-admin --days 30

# Every admin, or every operator
./scripts/polaris-set-webauthn-deadline.sh --all-admins --days 60
./scripts/polaris-set-webauthn-deadline.sh --all-operators --days 60

# Dry run: show what would change
./scripts/polaris-set-webauthn-deadline.sh --all-admins --days 60 --dry-run
```

The script:

- refuses `--days 0`, with or without `--force` (exit 5); a negative or
  non-numeric value is a usage error (exit 2), and there is no way to pass an
  absolute past date;
- refuses a deadline shorter than 7 days unless `--force` (exit 6);
- refuses to shorten an existing deadline that still has more than 7 days
  remaining unless `--force` (exit 7); a deadline with 7 days or fewer left
  can be shortened freely;
- refuses a target whose role is not admin or operator (exit 8);
- writes an `AuditAccessLog` row (`access_type` `WEBAUTHN_DEADLINE_SET`,
  `accessed_table` `AppUser`, `access_context` `set by: <user> | new_deadline:
  ...`), not an `AuthAuditLog` row; `--by USER` names the admin running it
  (default `$USER`);
- returns non-zero on any failure, so cron logs are greppable.

The past-deadline refusal is deliberate: a deadline in the past locks the
target out immediately, so an attacker who briefly holds an admin session
could otherwise lock out every other admin with one command.

---

## Phase 4: enforce

When the deadline arrives:

- Accounts that enrolled continue to log in through WebAuthn
  (`mfa_required`).
- Accounts that did not enroll become `mfa_overdue` and are refused. The
  login page tells them to have a second admin run
  `polaris-recover-admin.sh`, or to use a printed recovery code. Both paths
  are in [Recovery](#recovery) below.

Watch the audit log for `LOGIN_FAILED` rows whose detail begins `WebAuthn
enrollment deadline passed`. Each one is an operator who did not finish
enrollment in time.

---

## Phase 5: hardware-only (optional)

After Phase 4 has been stable for a month or two, restrict new enrollments to
external security keys:

```bash
# In /etc/polaris/polaris.env (or the deploying shell)
POLARIS_WEBAUTHN_HARDWARE_ONLY=1

# Restart the stack
./scripts/polaris-deploy.sh prod
```

With the flag set, the registration options ask the browser for a
cross-platform authenticator, so the browser does not offer platform
authenticators at enrollment; the server does not verify attachment, so a
modified client can still enroll a platform credential. Pair the flag with
`POLARIS_WEBAUTHN_ALLOWED_AAGUIDS` (Phase 6) for a server-enforced fleet
restriction. The flag does not touch the assertion ceremony: existing credentials, platform ones
included, keep working. To force re-enrollment on hardware, delete the
credentials that enrolled without an attestation statement:

```bash
psql -d polaris -c "DELETE FROM OperatorWebauthnCredential
                    WHERE attestation_format = 'none'"
# a rough filter: with the default attestation policy every credential is 'none'
```

This is destructive. Every affected admin drops back to `grace_period` or
`mfa_overdue` depending on their deadline; every affected operator-role
account drops to `not_required` (password-only) until it re-enrolls. Confirm
a recovery path is in place first.

---

## Phase 6: attestation policy (optional)

Phase 5 restricts the KIND of authenticator. Phase 6 restricts what the
authenticator must PROVE. Each refusal is audited as
`WEBAUTHN_REGISTRATION_REFUSED` with `policy:` in the detail.

1. **Require user verification.** `POLARIS_WEBAUTHN_USER_VERIFICATION=required`
   makes the PIN or biometric mandatory on enrollment AND on every assertion
   (the UV flag is checked server-side in both ceremonies), so a security key
   lifted from a desk cannot complete the second factor without its PIN.
   `preferred` asks for it but accepts a key that did not perform it;
   `discouraged` never asks.
2. **Ask for a real attestation.** `POLARIS_WEBAUTHN_ATTESTATION=direct` asks
   the browser to pass the authenticator's own attestation statement through
   (`indirect` lets the client anonymise it; `enterprise` requests the
   enterprise attestation an authenticator may hold; `none` asks for nothing).
   The library verifies packed, TPM, FIDO-U2F, Android-key, Android-SafetyNet,
   and Apple statements against their roots.
3. **Refuse enrollments without one.** `POLARIS_WEBAUTHN_REQUIRE_ATTESTATION=1`
   refuses a registration whose attestation format is `none`, which is what a
   browser returns when the authenticator cannot or will not attest. Only
   meaningful together with `direct`.
4. **Pin the fleet.** `POLARIS_WEBAUTHN_ALLOWED_AAGUIDS=<uuid>,<uuid>` refuses
   any authenticator model not on the list. An AAGUID is only trustworthy
   inside a verified attestation (under `none` the client zeroes it, so the
   list would refuse everything), so this step presumes steps 2 and 3.

Existing enrollments are not re-examined when a knob changes; the policy
applies to new registrations and, for user verification, to every assertion.
Credential rows store the attestation format as the wire name (`none`,
`packed`, ...), which is what the Phase 5 filter matches; rows enrolled
before the wire name was adopted may hold the enum repr
`AttestationFormat.NONE` instead, so widen the filter with `OR
attestation_format = 'AttestationFormat.NONE'` when the table predates it.

---

## Recovery

[`scripts/polaris-recover-admin.sh`](../../scripts/polaris-recover-admin.sh)
opens a short emergency window during which one admin may log in with the
password alone. It sets the target's `webauthn_required_after` to now plus
the window (1 to 60 minutes, default 15), clears the failed-login counter and
lockout, and writes an `EMERGENCY_PASSWORD_LOGIN_AUTHORIZED` row to
`AuthAuditLog` in the same transaction. It does not change the password,
insert a credential, or bypass anything else. It refuses to run at all when
the database call fails (exit 5), rather than open a window it cannot audit.

Inside the window the target logs in (the account is back in
`grace_period`), opens `/settings/webauthn`, and enrolls a new credential,
which returns the account to `mfa_required`. If the window closes first, the
next login is refused again.

The window only lifts `mfa_overdue`. `webauthn_status_for_user` returns
`mfa_required` whenever the account holds a credential row, before it looks
at `webauthn_required_after`, and the script never touches
`OperatorWebauthnCredential`. If the lost authenticator's credential row
still exists, delete it first, then open the window:

```sql
DELETE FROM OperatorWebauthnCredential
 WHERE user_id = <target user_id> AND credential_id = <lost credential_id>;
```

Authorization comes from exactly one of two sources.

### Recovery: second-admin pairing

A different active admin runs, on the host:

```bash
./scripts/polaris-recover-admin.sh \
    --target locked-out-admin \
    --authorizing-user-id <second admin's AppUser.user_id> \
    --window-minutes 15
# add --target=docker-stack to reach the compose Postgres; --dry-run to rehearse
```

The authorizer must be an active admin (exit 3 otherwise) and must not be
the target: self-authorization is refused with exit 3
(`check_recover_admin_refuses_self_pairing` in
[`polaris_checks/checks.py`](../../polaris_checks/checks.py) pins this). The
audit detail records `authorized_by=user_id_<N>`.

### Recovery: solo admin with a printed mnemonic

When no second admin exists, bind a recovery mnemonic to the account ahead
of time, with
[`scripts/polaris-generate-recovery-code.sh`](../../scripts/polaris-generate-recovery-code.sh):

```bash
./scripts/polaris-generate-recovery-code.sh --bind-to your-admin > recovery-code.txt
# Print recovery-code.txt on paper, store the print in a safe, then:
shred -u recovery-code.txt
```

The script emits a 16-word mnemonic plus its SHA-256 digest, and with
`--bind-to` stores the digest in `AppUser.recovery_code_hash`. The server
never holds the words. Generating a new code for the same account replaces
the bound hash.

When the authenticator is lost, the operator SSHes to the host, deletes the
lost credential's row as above if one exists, and supplies the mnemonic on
stdin. The script accepts only `-` (stdin) for
`--recovery-code`; passing the words as an argument is rejected so they never
appear in `ps` output or `/proc/<pid>/cmdline`.

```bash
./scripts/polaris-recover-admin.sh --target your-admin --recovery-code -
#   type the 16 words, then Ctrl+D
# or, non-interactively:
echo "<the 16 words>" | ./scripts/polaris-recover-admin.sh --target your-admin --recovery-code -
```

The supplied words are lowercased, whitespace-collapsed, SHA-256 hashed, and
compared with the bound hash; a mismatch, or an account with no bound code,
exits 6. `--recovery-code` and `--authorizing-user-id` are mutually
exclusive. The audit detail records `recovered_via=printed_recovery_code`.
There is no web route for the recovery code; it is consumed on the host.

### No second admin and no bound mnemonic

With shell access to the host you can still clear the requirement outright,
which the deadline script treats as a sensitive, audited change:

```bash
./scripts/polaris-set-webauthn-deadline.sh --username your-admin --clear --force-clear
# log in with the password, enroll at /settings/webauthn, then set a deadline again:
./scripts/polaris-set-webauthn-deadline.sh --username your-admin --days 30
```

Then bind a recovery mnemonic so the next loss does not need this path.

---

## Disabling MFA on an account

Lifting the requirement for one account (for example a legacy account that
cannot use WebAuthn) means setting `AppUser.webauthn_required_after` to NULL.
Use the script, which refuses without `--force-clear` and writes the audit
row:

```bash
./scripts/polaris-set-webauthn-deadline.sh --username specific-admin --clear --force-clear
```

The raw equivalent, if you must:

```sql
UPDATE AppUser
   SET webauthn_required_after = NULL
 WHERE username = 'specific-admin';
```

An enrolled credential still gates login after the deadline is cleared
(`mfa_required` depends on the credential count, not the deadline); delete
the credential on `/settings/webauthn` as well to return the account to
password-only. The auditor role is exempt without any change. Do not do this
routinely; it removes the phishing-resistant layer. Record the reason in the
operator change log.

---

## Why the refusals exist

A hardware second factor raises the cost of coercion: an attacker can extort
a password from an operator, but cannot extort physical possession of a key
without physical presence. Second-admin pairing keeps the property that no
single admin can authorize their own bypass. The deadline script's refusal
to set a past deadline keeps a briefly compromised admin session from being
used to lock out every other admin.

---

## Structural invariants

- `check_session_origin_hardening`: `webauthn_auth.py` reads all four policy
  knobs, offers ML-DSA-65, applies the user-verification policy in both
  ceremonies, and this document names `POLARIS_WEBAUTHN_ATTESTATION`.
- `check_recover_admin_refuses_self_pairing`: the recovery script compares
  the authorizer with the target.
- `check_operator_scripts_validate_argv`: `--target` must match the
  `AppUser` username format before it reaches SQL.

All three live in [`polaris_checks/checks.py`](../../polaris_checks/checks.py)
and run with `python -m polaris_checks.run`.

---

## Related

- [`polaris_web/webauthn_auth.py`](../../polaris_web/webauthn_auth.py): the implementation
- [`scripts/polaris-recover-admin.sh`](../../scripts/polaris-recover-admin.sh): the emergency window
- [`scripts/polaris-set-webauthn-deadline.sh`](../../scripts/polaris-set-webauthn-deadline.sh): deadlines and `--clear`
- [`scripts/polaris-generate-recovery-code.sh`](../../scripts/polaris-generate-recovery-code.sh): the printed mnemonic
- [SECRETS.md](SECRETS.md): the secrets matrix and rotation
- [HARDENING.md](HARDENING.md): session and network-policy knobs that ship alongside the attestation policy
