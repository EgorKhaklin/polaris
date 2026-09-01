# SECRETS.md — Polaris production secrets reference

This document is the secrets-management primer for Polaris in
production. It defines:

1. Every secret Polaris needs
2. How to generate each
3. How to rotate each
4. How NOT to leak them
5. The structural guarantees Polaris provides about secret handling

**Audience:** SREs, security engineers, operators. **Not** for
end users.

For dev / local secrets (the launcher's `polaris_dev_password`
default, etc.), see `polaris_mac_launch.sh` directly. This doc
is for production.

---

## 1. The secrets matrix

| Secret | Type | Required | Where used | Rotation cadence |
|---|---|---|---|---|
| `polaris_secret_key` | 256-bit hex | YES | Flask session signing | Every 90 days OR on suspected compromise |
| `polaris_db_password` | 32-char alnum | YES | Postgres `polaris_app` user | Every 90 days |
| `polaris_db_root_password` | 32-char alnum | YES (initial) | Postgres superuser; only for migrations | Every 180 days |
| `redis_password` | 32-char alnum | NO (optional) | Redis AUTH | Every 90 days when used |
| `polaris_operator_email` | RFC 5321 | YES | Let's Encrypt expiration alerts | When operator changes |
| Caddy ACME private key | auto | YES | TLS automation | Caddy auto-rotates |
| Postgres TLS cert | PEM | NO (optional, recommended) | Encrypted Postgres connections | Annual |

All secrets except the Caddy ACME key + the optional Postgres
TLS cert are **operator-managed**. Caddy + Polaris handle their
own rotation logic; the operator handles the rest.

---

## 2. Generation recipes

### 2.1 The `polaris-generate-secrets.sh` script

The recommended path:

```bash
./scripts/polaris-generate-secrets.sh
# Generates all required secrets in secrets/
# Sets directory permissions to 0700 (the host boundary)
# File modes: 0600 for secrets only ROOT reads (postgres root + replicator
#   passwords), 0644 for secrets a NON-ROOT container reads directly (the Flask
#   secret key, the DB password, the signing key — read by the app/pgbouncer at
#   uid 1000). 0644 is required because docker compose mounts file secrets with
#   the source file's perms, and on Linux a 0600 host-owned file is unreadable by
#   the different-uid container user (the stack will not boot). The 0700 directory
#   keeps a 0644 file reachable only by the owner host-side.
```

This script is idempotent: it refuses to overwrite existing
secrets unless `--force` is passed.

### 2.2 Manual generation (if you prefer)

For Flask session key (256-bit hex):

```bash
openssl rand -hex 32 > secrets/polaris_secret_key
chmod 0644 secrets/polaris_secret_key
```

OR via Python:

```bash
python3 -c "import secrets; print(secrets.token_hex(32))" > secrets/polaris_secret_key
chmod 0644 secrets/polaris_secret_key
```

For Postgres passwords (32-char alphanumeric, no special chars
to avoid shell-quoting issues in connection strings):

```bash
LC_ALL=C tr -dc 'A-Za-z0-9' < /dev/urandom | head -c 32 > secrets/polaris_db_password
chmod 0644 secrets/polaris_db_password
echo  # add trailing newline if your file expects it
```

For Redis password (when enabled):

```bash
LC_ALL=C tr -dc 'A-Za-z0-9' < /dev/urandom | head -c 32 > secrets/redis_password
chmod 0600 secrets/redis_password
```

### 2.3 Verification

After generation:

```bash
ls -la secrets/
# Directory should be drwx------ (0700, owner-only) — this is the host boundary.
# 0644 (-rw-r--r--): polaris_secret_key, polaris_db_password, polaris_signing_key,
#   polaris_replicator_password, and the TLS certs/keys — read by NON-ROOT
#   container processes (the app/pgbouncer at uid 1000; postgres's docker-init runs
#   as the postgres user and reads the replicator password + copies the server key).
# 0600 (-rw-------): polaris_db_root_password only — read by the postgres entrypoint
#   as root before it drops privileges.

stat -c '%a %n' secrets/* 2>/dev/null || stat -f '%A %N' secrets/*
```

If a permission is wrong, fix it (do NOT blanket `chmod 0600 secrets/*` — that
makes the container-read secrets unreadable by the non-root containers on Linux
and the stack will not boot):

```bash
chmod 0700 secrets/
chmod 0644 secrets/polaris_secret_key secrets/polaris_db_password \
           secrets/polaris_signing_key secrets/polaris_replicator_password \
           secrets/postgres_server.crt secrets/postgres_server.key \
           secrets/pgbouncer_server.crt secrets/pgbouncer_server.key
chmod 0600 secrets/polaris_db_root_password
# Or simply re-run ./scripts/polaris-generate-secrets.sh which sets them correctly.
```

---

## 3. Rotation

### 3.1 Rotation cadence (recommended)

| Secret | Cadence | Trigger conditions for off-cycle rotation |
|---|---|---|
| `polaris_secret_key` | 90 days | Suspected breach; departing operator with prior access |
| `polaris_db_password` | 90 days | Suspected breach; departing operator |
| `polaris_db_root_password` | 180 days | Same |
| `redis_password` | 90 days | Same |
| TLS cert | 60-90 days | Caddy automatic (Let's Encrypt 90-day default) |

### 3.2 Rotating `polaris_secret_key`

```bash
./scripts/polaris-rotate-secret.sh polaris_secret_key
```

What this does:
1. Generates a new 256-bit hex secret
2. Writes it to `secrets/polaris_secret_key` (mode 0644 in the 0700 dir, so the
   non-root app container can read it; see Verification above)
3. Restarts the app container only (Postgres + Redis stay running)
4. Re-runs the smoke test
5. Reports success or rollback

**Side effect:** all existing user sessions are invalidated.
Users will need to re-login. This is intentional (the rotation
is meaningful) and unavoidable (Flask signs cookies with the
secret key).

To avoid user-visible disruption, schedule rotations during low-
traffic windows.

### 3.3 Rotating `polaris_db_password`

```bash
./scripts/polaris-rotate-secret.sh polaris_db_password
```

What this does:
1. Connects to Postgres as superuser using `polaris_db_root_password`
2. Generates a new password
3. Updates the `polaris_app` user's password in Postgres
4. Writes the new password to `secrets/polaris_db_password`
5. Restarts the app container (which re-reads the secret on startup)
6. Smoke test + report

If step 3 fails (Postgres unreachable), the rotation aborts and
the old password remains in `secrets/`. No state divergence.

> **pgbouncer (v8.83+)** generates its `userlist.txt` from this secret at container
> start, so the script recreates pgbouncer BEFORE the app; recreating only the
> app leaves pgbouncer authenticating with the old password and every app
> connection fails with `SASL authentication failed` (found by the live
> rotation drill, v9.182). If you rotate by hand, do the same.

### 3.4 Rotating `polaris_db_root_password`

This one is more involved (it changes the superuser, which is
how every other DB rotation works):

```bash
./scripts/polaris-rotate-secret.sh polaris_db_root_password
# Will prompt for confirmation since this is the bootstrap secret
```

What this does:
1. Connects to Postgres as the current superuser
2. Generates a new password
3. `ALTER USER postgres PASSWORD ...`
4. Writes the new password to `secrets/polaris_db_root_password`
5. Validates by reconnecting with the new password
6. Reports success

If step 5 fails, rolls back the `ALTER USER` (re-sets the old
password) and aborts.

### 3.5 Rotating Caddy TLS cert

You don't. Caddy handles this via Let's Encrypt automatic
renewal (default: renew when ≤30 days remain). Verify Caddy is
healthy:

```bash
docker compose -f polaris_web/docker-compose.prod.yml exec caddy \
    caddy validate --config /etc/caddy/Caddyfile
```

If Caddy reports issues, check:
- Outbound 80/443 reachable (ACME challenge)
- DNS records still correct
- `POLARIS_OPERATOR_EMAIL` set (Let's Encrypt sends warnings)

---

## 4. Leak prevention

### 4.1 What goes in version control

**NOTHING.** The `secrets/` directory is gitignored
(`.gitignore` rule). Verify:

```bash
git check-ignore secrets/polaris_secret_key
# Should output: secrets/polaris_secret_key
```

If a secret was ever committed:

1. Rotate it immediately (the secret IS leaked; assume worst)
2. Use `git filter-repo` or `git filter-branch` to remove it from history
3. Force-push (if the repo is private and you control all clones); if public, the secret stays in history forever and rotation is the only safe response
4. Audit downstream for any consumer caching the old value

### 4.2 What goes in environment variables

**Non-secret config only.** Specifically:

- `POLARIS_DOMAIN` (TLS configuration; not secret)
- `POLARIS_OPERATOR_EMAIL` (Let's Encrypt; not secret)
- `POLARIS_WORKERS` (gunicorn worker count; not secret)
- `POLARIS_BACKUP_DIR` (path; not secret)
- `POLARIS_ZK_BINARY` (path; not secret)

The Polaris app code reads secrets from `/run/secrets/<name>`
inside the container (Docker secrets file-mount), NOT from
environment variables. This is enforced by `polaris_web/security.py`
and verified by the `polaris_checks/` invariant layer (no secret
literals in the compose env).

### 4.3 What goes in logs

The Polaris app + Caddy + Postgres should all redact secrets
from logs:

- **Polaris app:** `polaris_web/security.py` strips `Cookie` +
  `Authorization` headers from any structured log line
- **Caddy:** access log includes only request line + status +
  duration; bodies are not logged
- **Postgres:** statement log (if enabled) records SQL but
  parameterized queries hide the parameter values; verify with
  `log_statement = 'mod'` not `'all'`

If you suspect a log line contains a secret:

1. Stop the affected service immediately
2. Rotate the leaked secret
3. Audit log destinations (file, syslog, central aggregator) and purge
4. Review redaction logic for the gap

### 4.4 What goes in backups

Backups created by `polaris-backup.sh` contain:

- Postgres dump (includes hashed passwords for AppUser, but NOT
  the `polaris_app` connection password, which is in `secrets/`)
- The development record (CHANGELOG and decision history; review
  for any prose that named a secret)

Backups do **NOT** include the `secrets/` directory. Backup
encryption is the operator's responsibility (use `gpg` or
`age` on the tarball before off-site sync).

To encrypt a backup:

```bash
gpg --symmetric --cipher-algo AES256 --output \
    polaris-20260514.tar.gz.gpg polaris-20260514.tar.gz

# Decrypt for restore:
gpg --decrypt polaris-20260514.tar.gz.gpg > polaris-20260514.tar.gz
```

### 4.5 What goes in CI/CD

If Polaris is deployed via CI/CD (GitHub Actions, GitLab CI, etc.):

- Use the platform's secret store (GitHub Encrypted Secrets,
  GitLab CI/CD Variables, etc.); NEVER inline in workflow YAML
- Mask secrets in logs (most platforms do this automatically when
  the secret is in their store)
- Audit who can read the secret store; principle of least
  privilege
- Rotate any secret that may have been exposed via a workflow
  failure log

---

## 5. Structural guarantees

Polaris's security architecture provides several guarantees
about secret handling. These are tested by the `polaris_checks/`
invariant layer and the DB-backed suites in `polaris_web/`:

### 5.1 No secrets in production env vars

`docker-compose.prod.yml` uses Docker secrets (file-mounted at
`/run/secrets/<name>`) for all sensitive values. The compose
file MUST NOT have `POLARIS_SECRET_KEY:` as an env-var literal.

Enforced by: the `polaris_checks/` invariant layer (no secret
literals in the compose env).

### 5.2 Session-secret rotation on every relaunch

The dev launcher (`polaris_mac_launch.sh`) regenerates
`POLARIS_SECRET_KEY` on every launch unless the operator
explicitly sets `POLARIS_SECRET_KEY` in the shell. This was
added v8.56 to fix a session-cookie-survives-relaunch bug;
preserved in production via the rotation script.

In production, rotation is operator-triggered (no auto-rotation
on container restart, since that would invalidate user sessions
unpredictably). Schedule rotations explicitly per §3.

### 5.3 No secret references in tests

The `polaris_checks/` invariant layer scans for hardcoded
secrets (regex: `polaris_secret_key`, `polaris_dev_password`,
etc.). Tests use ephemeral test-only credentials that never
match production secret formats.

### 5.4 Log scanning for leaked secrets

Operators should scan recent log lines for patterns that look
like leaked secrets (high-entropy 64+ character hex strings
outside of expected fields). If found, treat as an incident:
rotate, audit, postmortem.

This is detection, not prevention; the prevention is in the
redaction logic (§4.3). The log scan is the safety net.

### 5.5 Audit-of-record never carries secrets

The audit-of-record tables (`TokenLifecycleEvent`,
`VerificationEvent`, etc.) do NOT carry password fields,
session tokens, or signing keys. Schema-level enforcement (no
columns of those types).

`DuressEvent` (R11-5) carries a hashed duress code (Werkzeug
scrypt commitment); the plaintext is never stored. Verified by
`test_duress_code_storage_is_hash_only`.

---

## 6. Threat model summary

The full threat model is in `DEVNOTES/threat-model.md`. For
secrets specifically, the relevant scenarios:

| Threat | Mitigation |
|---|---|
| Operator laptop stolen with `secrets/` mounted | Disk encryption (operator responsibility); rotation immediately on incident |
| Backup tarball intercepted | Encrypt backups (gpg/age) before off-site sync; rotate any secret that might be in older backups |
| Compromised CI/CD pipeline | Use platform secret store; audit access; rotate on suspicion |
| Insider with prior secret access | Rotate on departure; track rotation in the operator change log |
| Postgres logs leak password via misconfig | `log_statement = 'mod'` (not `'all'`); review log redaction quarterly |
| Compromised dev environment promoting bad secrets to prod | Separate dev secrets from prod (use different generation seed; never reuse) |
| Caddy compromise → TLS private key leaked | Caddy auto-rotates ACME keys; rotate other secrets that may have been in TLS-terminated traffic |
| Memory dump of running gunicorn process | Limit access to host (no shared production tenancy); use `madvise(MADV_DONTDUMP)` for memory-resident secrets in future Phase 2 |

For each threat, the response is the same: **rotate, audit,
postmortem.** Speed of rotation matters more than perfect
forensics.

---

## 7. Generation script reference

`scripts/polaris-generate-secrets.sh` is the canonical entry
point for first-time setup:

```bash
#!/usr/bin/env bash
# Idempotent: refuses to overwrite existing secrets unless --force
set -euo pipefail

mkdir -p secrets
chmod 0700 secrets

generate() {
    local name="$1" cmd="$2"
    local path="secrets/$name"
    if [[ -f "$path" && "${1:-}" != "--force" ]]; then
        echo "  skip: $name (exists)"
        return
    fi
    eval "$cmd" > "$path"
    chmod 0600 "$path"
    echo "  wrote: $name ($(wc -c < "$path") bytes)"
}

generate polaris_secret_key       'openssl rand -hex 32'
generate polaris_db_password      'LC_ALL=C tr -dc A-Za-z0-9 < /dev/urandom | head -c 32'
generate polaris_db_root_password 'LC_ALL=C tr -dc A-Za-z0-9 < /dev/urandom | head -c 32'
# redis_password is OPTIONAL; uncomment if Redis AUTH enabled
# generate redis_password         'LC_ALL=C tr -dc A-Za-z0-9 < /dev/urandom | head -c 32'

echo "Secrets generated in secrets/"
echo "Verify: ls -la secrets/"
```

The actual script ships with additional safety: pre-flight
disk-space check; refuses if running as root (operator should
own the secrets, not root); checks for entropy availability
(`/dev/urandom` is universally available; OpenSSL is preferred).

---

## 7. WebAuthn-MFA enrollment & recovery (v8.97 / Position B)

Operator authentication adds a phishing-resistant second factor for
admin accounts.

### 7.1 First-time enrollment

1. Sign in with password as the admin (still allowed during the
   30-day grace period after the account was created).
2. Navigate to `/settings/webauthn`.
3. Click **Enroll WebAuthn credential**. The browser prompts for
   either a hardware security key (YubiKey, SoloKey, Nitrokey) or
   a platform authenticator (Touch ID / Windows Hello / Android
   biometric). To restrict to hardware-only set the env knob:
   `POLARIS_WEBAUTHN_HARDWARE_ONLY=1`.
4. Label the device (e.g. *"YubiKey 5C work-laptop"*); confirm the
   prompt. The credential is persisted in
   `OperatorWebauthnCredential`.
5. Verify the audit row landed:
   ```sql
   SELECT event_timestamp, event_type, username
     FROM AuthAuditLog
    WHERE event_type='WEBAUTHN_REGISTERED'
    ORDER BY event_timestamp DESC LIMIT 5;
   ```

Once enrolled, every subsequent admin login requires:
1. correct password
2. successful WebAuthn assertion against an enrolled credential

Enroll a second credential as backup. Two credentials = no single
point of failure if one is lost.

### 7.2 Recovery — lost device, second-admin pairing

A second admin can open a short emergency-login window:

```bash
# As the second admin (NOT the locked-out one), SSH to the host:
./scripts/polaris-recover-admin.sh \
    --target locked-out-admin \
    --authorizing-user-id <your_admin_user_id> \
    --window-minutes 15
```

The target may then log in with password only for the window
length. They MUST enroll a new credential at `/settings/webauthn`
before the window closes, otherwise the `mfa_overdue` refusal
returns at the next login. The grant is itself audited as
`EMERGENCY_PASSWORD_LOGIN_AUTHORIZED`.

### 7.3 Recovery — solo-admin deployment, printed mnemonic

For deployments where no second admin exists (single-admin Polaris
instance), generate a printed recovery mnemonic at enrollment time:

```bash
./scripts/polaris-generate-recovery-code.sh > /tmp/recovery-code.txt
# Print /tmp/recovery-code.txt on real paper.
# Store the print in a physical safe.
rm /tmp/recovery-code.txt          # do not leave on disk
```

The page shows the cleartext mnemonic AND a SHA-256 digest. Future
work will extend `polaris-recover-admin.sh` with a `--recovery-code`
argument that verifies the mnemonic against an `AppUser.recovery_code_hash`
column (deferred by decision — the v8.97 ship lands the mnemonic
generator + threat-model coverage; the in-app verification flow is
a follow-up gated on operator demand).

### 7.4 Environment knobs

- `POLARIS_WEBAUTHN_HARDWARE_ONLY=1` — refuse platform authenticators,
  accept hardware tokens only (YubiKey class). Default: both allowed.
- `POLARIS_WEBAUTHN_RP_NAME` — display name shown to the user during
  the WebAuthn prompt. Default: `Polaris`.
- `POLARIS_DOMAIN` — used as the WebAuthn relying-party ID;
  assertions are origin-bound to this domain.

### 7.5 Disabling MFA on an account

Set `AppUser.webauthn_required_after = NULL` to lift the requirement
(e.g., for a legacy account that cannot use WebAuthn). The auditor
role is exempt by default (§IV.1).

```sql
UPDATE AppUser
SET webauthn_required_after = NULL
WHERE username = 'specific-admin-username';
```

Do NOT do this routinely — it removes the defense-in-depth layer.
Document the reason in the operator runbook.

---

## 8. The sealed secret store (v9.180, roadmap P1.3)

Production secrets are no longer files in a directory. `polaris_web/secrets/`
is the MATERIALIZED form, written into a root-only tmpfs at start; the source
of truth is a sealed store, `polaris_web/secrets.sealed/`, whose contents are
useless without a key that is not on the disk beside them.

| `POLARIS_SECRETS_BACKEND` | Sealed with | Unsealed by | Use when |
|---|---|---|---|
| `file` (default) | nothing: the plaintext dir is the store | n/a | development; the pre-P1.3 layout |
| `age` | the operator's age recipients (`POLARIS_SECRETS_AGE_RECIPIENTS`) | an age identity file (`POLARIS_SECRETS_AGE_IDENTITY`), root-only, or an age plugin for a hardware token | on-premises; no cloud dependency; the identity can live on a YubiKey |
| `awskms` | envelope encryption: per file, KMS `GenerateDataKey` (AES-256) + AES-256-GCM with the file name as AAD; the KMS-wrapped data key stored beside the ciphertext | `kms:Decrypt` on `POLARIS_SECRETS_AWSKMS_KEY_ID`, an IAM decision rather than a file | AWS-hosted authorities |

The issuer SIGNING key has its own custody layer with HSM/PKCS#11 and KMS
drivers ([`KEY-CEREMONY.md`](KEY-CEREMONY.md)); this section is about
everything else in the matrix in section 1.

### 8.1 Adopting a sealed store

```bash
# one-time: the plaintext is generated exactly as before, then sealed
./scripts/polaris-generate-secrets.sh
age-keygen -o /root/polaris-age.identity          # keep OUT of the repo; back it up sealed
grep -i "public key:" <(age-keygen -y /root/polaris-age.identity 2>&1) | sed 's/.*: *//' > /root/polaris-age.recipients
export POLARIS_SECRETS_BACKEND=age POLARIS_SECRETS_AGE_RECIPIENTS=/root/polaris-age.recipients \
       POLARIS_SECRETS_AGE_IDENTITY=/root/polaris-age.identity
./scripts/polaris-secrets.sh seal                 # -> polaris_web/secrets.sealed/ (+ MANIFEST.json)
./scripts/polaris-secrets.sh verify               # every blob decrypts and matches its sha256
shred -u polaris_web/secrets/* && rmdir polaris_web/secrets   # the plaintext directory goes away
```

Put the four `POLARIS_SECRETS_*` lines in `/etc/polaris/polaris.env`
([`LINUX-SERVER.md`](LINUX-SERVER.md)). From then on
`polaris.service` runs `polaris-secrets.sh unseal-if-configured` before
`docker compose up` and `polaris-deploy.sh` does the same before its preflight:
the store is unsealed into `POLARIS_SECRETS_DIR` (default
`/run/polaris/secrets`, a `tmpfs` mounted `mode=0700,nosuid,nodev,noexec`),
file modes restored from the manifest, and compose reads every secret and
certificate from there. Nothing plaintext touches the disk.

For `awskms`: `POLARIS_SECRETS_BACKEND=awskms POLARIS_SECRETS_AWSKMS_KEY_ID=<key arn>
POLARIS_SECRETS_AWSKMS_REGION=<region>`, host `python3` with boto3
(`pip install -r polaris_web/requirements-custody.txt`), and an instance role
allowed `kms:GenerateDataKey` and `kms:Decrypt` on that key. The store can be
kept in a PRIVATE ops repository or an object bucket; it is gitignored here.

### 8.2 Rotation

**A secret** (the session key, a DB password): `polaris-rotate-secret.sh
<name>` exactly as in section 3. It rotates the materialized copy, updates the
database role, recreates the affected container, and WRITES THROUGH to the
sealed store, keeping the previous blob as `<name>.age.prev` (or `.kms.prev`).
The store never lags the running stack, so a reboot re-unseals the new value.
`polaris-secrets.sh verify` asserts that invariant (sealed == materialized).

**The wrapping key** (a new age identity, or a new KMS key), without changing
any secret's value:

```bash
./scripts/polaris-secrets.sh rotate-wrapping --new-recipients /root/polaris-age-2.recipients
#   or: --new-key-id <new kms key arn>
```

The previous generation is kept as `polaris_web/secrets.sealed.prev/` until you
remove it; the old identity or key no longer opens the live store (the KMS
driver pins `KeyId` on `Decrypt`, so a stale key is refused, not silently
accepted). Then update `polaris.env` to the new identity or key and run
`polaris-secrets.sh verify`.

### 8.3 What is drilled in CI

`prod-stack-boot` seals the generated secrets to a throwaway age identity,
DELETES the plaintext directory, unseals into a tmpfs, boots the full
production stack from it, asserts health through the TLS edge, then runs
`polaris-rotate-secret.sh` for `polaris_db_password` and `polaris_secret_key`
against the live stack, asserts health again, verifies the sealed store
matches the tmpfs, and proves a fresh unseal returns the rotated password.
`test_secretstore.py` covers both backends (age through the real CLI, KMS
through the wire-faithful stand-in), wrapping-key rotation, tamper and drift
detection, and mode restoration.

### 8.4 External alternatives

HashiCorp Vault, GCP Secret Manager, and Azure Key Vault are not built in.
They fit the same shape: an `unseal-if-configured` that materializes the
secrets into `POLARIS_SECRETS_DIR` from your store before the stack starts.
Write that hook in place of `polaris-secrets.sh` and keep the rest identical;
the compose file only ever sees the directory.

## 9. Cross-references

- `docs/operator/OPERATIONS.md` — operations runbook (this doc's parent)
- `polaris_web/docker-compose.prod.yml` — where Docker secrets are referenced
- `polaris_web/security.py` — runtime secret loading
- `DEVNOTES/threat-model.md` — STRIDE analysis
- `MISSION.md` C-constraints — C1 (audit append-only), C5 (CSP), C7 (algorithm metadata) all touch secret-handling discipline
- `docs/operator/OPERATIONS.md` — production deployment runbook
