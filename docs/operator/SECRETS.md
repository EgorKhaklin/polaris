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
# Sets file permissions to 0600
# Sets directory permissions to 0700
```

This script is idempotent: it refuses to overwrite existing
secrets unless `--force` is passed.

### 2.2 Manual generation (if you prefer)

For Flask session key (256-bit hex):

```bash
openssl rand -hex 32 > secrets/polaris_secret_key
chmod 0600 secrets/polaris_secret_key
```

OR via Python:

```bash
python3 -c "import secrets; print(secrets.token_hex(32))" > secrets/polaris_secret_key
chmod 0600 secrets/polaris_secret_key
```

For Postgres passwords (32-char alphanumeric, no special chars
to avoid shell-quoting issues in connection strings):

```bash
LC_ALL=C tr -dc 'A-Za-z0-9' < /dev/urandom | head -c 32 > secrets/polaris_db_password
chmod 0600 secrets/polaris_db_password
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
# All files should be -rw------- (owner-only)
# Directory should be drwx------ (owner-only)

stat -c '%a %n' secrets/* 2>/dev/null || stat -f '%A %N' secrets/*
# Each should report 600 (file) or 700 (dir)
```

If any permission is wrong, fix it:

```bash
chmod 0700 secrets/
chmod 0600 secrets/*
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
2. Writes it to `secrets/polaris_secret_key` (preserves 0600)
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
- `POLARIS_GUNICORN_WORKERS` (tuning; not secret)
- `POLARIS_BACKUP_DIR` (path; not secret)
- `POLARIS_ZK_BINARY` (path; not secret)

The Polaris app code reads secrets from `/run/secrets/<name>`
inside the container (Docker secrets file-mount), NOT from
environment variables. This is enforced by `polaris_web/security.py`
and verified by structural-invariant `test_no_secrets_in_compose_env`.

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
  the `polaris_app` connection password — that's in `secrets/`)
- `treasury-roll.json` + `census-roll.json` (no secrets)
- `sanctum/` + `journal/` (audit-of-record; review for any prose
  that named a secret)

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

Polaris's security architecture provides several structural
guarantees about secret handling. These are tested by the
structural-invariant suite (`polaris_web/test_structural_invariants.py`):

### 5.1 G28 — No secrets in production env vars

`docker-compose.prod.yml` uses Docker secrets (file-mounted at
`/run/secrets/<name>`) for all sensitive values. The compose
file MUST NOT have `POLARIS_SECRET_KEY:` as an env-var literal.

Enforced by: `test_no_secrets_in_compose_env` (added v8.77;
G-guard G28).

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

The structural-invariant suite scans test files for hardcoded
secrets (regex: `polaris_secret_key`, `polaris_dev_password`,
etc.). Tests use ephemeral test-only credentials that never
match production secret formats.

### 5.4 Logged secrets are flagged by HYDRA

The HYDRA SecurityWatcher (post-v8.39) scans recent log lines
for patterns that look like leaked secrets (high-entropy 64+
character hex strings outside of expected fields like
`pheromone_id`). If found, fires `alert` severity.

This is detection, not prevention; the prevention is in the
redaction logic. SecurityWatcher is the safety net.

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
| Insider with prior secret access | Rotate on departure; track rotation in journal |
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
admin accounts per Sanctum 2026-05-14-webauthn-operator-auth.md.

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
column (deferred per Sanctum §V — the v8.97 ship lands the mnemonic
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

## 8. HSM / KMS integration (v9.01 / Phase 3 Wave 1)

The default v8.77 deployment file-mounts secrets at mode 0600 on
host disk. That's adequate for single-host deployments under the
operator's full control. For deployments that need:

- **Encryption-at-rest with a hardware root of trust** (the secret
  never exists in plaintext outside of an HSM)
- **Cross-machine secret sharing** (same Polaris deployment running
  on multiple hosts that all need the same SECRET_KEY without
  synchronizing files)
- **Automated key rotation** (compliance regimes that mandate
  90-day rotation cycles)
- **Auditable secret access** (every read of the secret is logged
  with timestamp + caller identity)

… you want a KMS-backed secret store. Three operator-pick paved
paths follow. **Pick one based on your cloud / compliance regime;
do not mix.**

### 8.1 HashiCorp Vault Transit Engine

**When to pick:** multi-cloud / on-prem / no cloud-vendor lock-in.
Vault is open-source + self-hostable; Transit Engine is its
encryption-as-a-service primitive (Polaris secrets are encrypted
under a Vault-held key; Polaris fetches the decrypted value at
startup).

```bash
# 1. Install Vault (one-time, on a separate host or HA cluster)
brew install vault    # macOS dev; production = official binary or container

# 2. Initialize + unseal (separate operator runbook; one-time)
vault server -config=/etc/vault.d/vault.hcl
vault operator init    # produces unseal keys; store offline + split per Shamir
vault operator unseal  # repeat with N of M unseal keys

# 3. Enable Transit + create the polaris-secret-key
vault secrets enable transit
vault write -f transit/keys/polaris-secret-key

# 4. Encrypt the SECRET_KEY (one-time, per Polaris deployment)
SECRET=$(openssl rand -hex 32)
ENCRYPTED=$(vault write transit/encrypt/polaris-secret-key \
                   plaintext=$(echo -n "$SECRET" | base64) \
                   -format=json | jq -r '.data.ciphertext')
echo "$ENCRYPTED" > /run/polaris/secret_key.vault-encrypted

# 5. Polaris launch wrapper decrypts at startup:
cat > /usr/local/bin/polaris-launch-vault <<'EOF'
#!/bin/bash
set -euo pipefail
ENCRYPTED=$(cat /run/polaris/secret_key.vault-encrypted)
SECRET_B64=$(vault write transit/decrypt/polaris-secret-key \
                    ciphertext="$ENCRYPTED" \
                    -format=json | jq -r '.data.plaintext')
export POLARIS_SECRET_KEY=$(echo "$SECRET_B64" | base64 -d)
exec /usr/bin/polaris-deploy.sh prod
EOF
chmod +x /usr/local/bin/polaris-launch-vault
```

**Key rotation** (90-day cycle):

```bash
# Vault rotates the underlying key without breaking decryption of
# old ciphertexts (versioned encryption keys per Vault Transit spec).
vault write -f transit/keys/polaris-secret-key/rotate

# Polaris ciphertext stays valid; on next launch it decrypts under
# the new version. To force re-encryption under the latest version:
vault write transit/rewrap/polaris-secret-key \
            ciphertext="$(cat /run/polaris/secret_key.vault-encrypted)" \
            -format=json | jq -r '.data.ciphertext' > /run/polaris/secret_key.vault-encrypted
```

**Audit trail:** Vault's audit device logs every encrypt/decrypt
operation with caller identity + timestamp; cite this in the SOC 2
CC6.1 evidence package.

**Cost:** self-hosted Vault is FOSS; HA cluster recommended for
production (3 nodes minimum for Raft consensus). HashiCorp Cloud
Platform offers Vault-as-a-Service if self-hosting is too operationally
heavy.

### 8.2 AWS KMS envelope encryption

**When to pick:** AWS-native deployment; existing AWS account; want
the strongest hardware-root-of-trust without operating Vault.
KMS keys are FIPS 140-3 Level 3 (HSM-backed).

```bash
# 1. Create a KMS Customer Managed Key (CMK) for Polaris
aws kms create-key \
    --description "Polaris session-secret encryption key" \
    --key-usage ENCRYPT_DECRYPT \
    --tags TagKey=Service,TagValue=Polaris

# Note the KeyId; use it as POLARIS_KMS_KEY_ID below.

# 2. Encrypt SECRET_KEY (one-time, per Polaris deployment)
SECRET=$(openssl rand -hex 32)
echo -n "$SECRET" | aws kms encrypt \
    --key-id "$POLARIS_KMS_KEY_ID" \
    --plaintext fileb:///dev/stdin \
    --output text \
    --query CiphertextBlob > /run/polaris/secret_key.kms-encrypted

# 3. Polaris launch wrapper decrypts at startup:
cat > /usr/local/bin/polaris-launch-kms <<'EOF'
#!/bin/bash
set -euo pipefail
ENCRYPTED=$(cat /run/polaris/secret_key.kms-encrypted)
export POLARIS_SECRET_KEY=$(echo "$ENCRYPTED" | base64 -d | aws kms decrypt \
    --ciphertext-blob fileb:///dev/stdin \
    --output text \
    --query Plaintext | base64 -d)
exec /usr/bin/polaris-deploy.sh prod
EOF
chmod +x /usr/local/bin/polaris-launch-kms
```

**IAM policy for the Polaris EC2 instance role:**

```json
{
    "Version": "2012-10-17",
    "Statement": [{
        "Effect": "Allow",
        "Action": "kms:Decrypt",
        "Resource": "arn:aws:kms:us-east-1:<account>:key/<polaris-cmk-id>"
    }]
}
```

(Decrypt only — the host should NEVER need Encrypt; encryption
happens once during deployment by an admin role with a separate
IAM principal.)

**Key rotation** (automatic): AWS KMS rotates Customer Managed
Keys annually if `--key-rotation-status enabled` is set.
Ciphertexts encrypted under old versions remain decryptable
indefinitely; new ciphertexts use the latest version. To force
re-encryption: re-run step 2 above.

**Audit trail:** CloudTrail logs every kms:Decrypt with caller
identity, timestamp, and source IP. Cite this in SOC 2 CC6.1
evidence.

**Cost:** $1/month per CMK + $0.03 per 10K decrypts. For a
single-instance Polaris deployment (decrypt once per launch ≈ ~30
launches/month), monthly cost is ~$1.

### 8.3 GCP Secret Manager

**When to pick:** GCP-native deployment; existing GCP project;
want managed secret storage without envelope-encryption complexity.
Secret Manager stores the plaintext in Google's HSM-backed
infrastructure; Polaris fetches at startup.

```bash
# 1. Create the secret (one-time, per Polaris deployment)
SECRET=$(openssl rand -hex 32)
echo -n "$SECRET" | gcloud secrets create polaris-secret-key \
    --replication-policy=automatic \
    --data-file=-

# 2. Polaris launch wrapper fetches at startup:
cat > /usr/local/bin/polaris-launch-gsm <<'EOF'
#!/bin/bash
set -euo pipefail
export POLARIS_SECRET_KEY=$(gcloud secrets versions access latest \
    --secret=polaris-secret-key)
exec /usr/bin/polaris-deploy.sh prod
EOF
chmod +x /usr/local/bin/polaris-launch-gsm
```

**IAM binding for the Polaris GCE VM service account:**

```bash
gcloud secrets add-iam-policy-binding polaris-secret-key \
    --member=serviceAccount:polaris-prod@<project>.iam.gserviceaccount.com \
    --role=roles/secretmanager.secretAccessor
```

(Accessor only — the VM should NEVER need to write the secret;
write happens during deployment by an admin SA with separate
permissions.)

**Key rotation** (manual cycle):

```bash
# Add a new secret version (Polaris automatically picks up "latest"
# on next launch; old versions remain accessible for rollback).
NEW_SECRET=$(openssl rand -hex 32)
echo -n "$NEW_SECRET" | gcloud secrets versions add polaris-secret-key \
    --data-file=-

# Disable the old version after verifying the new one works:
gcloud secrets versions disable <old-version-id> \
    --secret=polaris-secret-key
```

**Audit trail:** Cloud Audit Logs records every secrets.versions.access
call with caller identity + timestamp. Cite this in SOC 2 CC6.1
evidence.

**Cost:** $0.06/month per secret + $0.03 per 10K accesses. For a
single-instance Polaris deployment, monthly cost is < $1.

### 8.4 Comparison matrix

| Factor | Vault Transit | AWS KMS | GCP Secret Manager |
|---|---|---|---|
| **Cloud lock-in** | None (self-hosted) | AWS | GCP |
| **Operational burden** | High (HA cluster + unseal protocol) | Low (managed) | Low (managed) |
| **Hardware root of trust** | Yes (HSM cluster optional, FIPS 140-2 L3) | Yes (HSM-backed FIPS 140-3 L3) | Yes (HSM-backed) |
| **Automated rotation** | CLI-driven | Annual auto + on-demand | Manual versioning |
| **Cost (single instance)** | FOSS + ops cost | ~$1/month | < $1/month |
| **Audit logging** | Vault audit devices | CloudTrail | Cloud Audit Logs |
| **Ransomware resistance** | Trust-boundary protected | Cross-account + MFA-delete | Project-scope IAM |

### 8.5 Migration from file-mounted to KMS-backed

A running Polaris deployment migrating from v8.77 file-mounted
secrets to KMS-backed:

```bash
# 1. Pick a KMS path (Vault / AWS KMS / GCP SM); follow §§ 8.1-8.3
#    setup steps EXCEPT do NOT generate a new SECRET_KEY in step 1.
#    Instead, use the existing secret from /run/secrets/polaris_secret_key
#    so existing user sessions stay valid across the migration:
EXISTING_SECRET=$(cat /run/secrets/polaris_secret_key)

# 2. Encrypt + persist via your chosen path (AWS KMS example):
echo -n "$EXISTING_SECRET" | aws kms encrypt \
    --key-id "$POLARIS_KMS_KEY_ID" \
    --plaintext fileb:///dev/stdin \
    --output text \
    --query CiphertextBlob > /run/polaris/secret_key.kms-encrypted

# 3. Switch the launcher to use the KMS-decrypt wrapper instead of
#    the file-mount path. Restart Polaris.

# 4. Verify a known-good user session survives the cut:
#    - Open https://${POLARIS_DOMAIN}/dashboard in your browser
#    - You should NOT be logged out; the cookie still validates
#    - If you ARE logged out, the wrapper isn't exporting POLARIS_SECRET_KEY
#      correctly — debug before declaring the migration done

# 5. Once verified, remove the plaintext file-mounted secret:
shred -u /run/secrets/polaris_secret_key
docker compose down && docker compose up -d
```

Document the migration in `journal/<date>-secrets-migration.md`
per the filesystem AoR convention; this becomes evidence for the
next SOC 2 audit cycle (CC8.1 — change management).

### 8.6 Cross-references for KMS path

- [DR.md](DR.md) § 4.7 — ransomware recovery (KMS-backed secrets
  are NOT exfiltrable from the host alone; the cloud account
  trust boundary holds even if the host is compromised)
- [SOC2.md](SOC2.md) § 7 (CC6.1) + § 12 (C1.1) — KMS satisfies
  the hardware-root-of-trust requirements for Confidentiality TSC
- [PENTEST.md](PENTEST.md) — pen-test scope includes "secrets
  not exfiltrable from compromised host" (KMS path passes; file-
  mounted path fails for hosts without disk encryption)
- `polaris_web/security.py` — the consumer of POLARIS_SECRET_KEY
  (no code change needed for the KMS migration; the launcher
  wrapper exports the env var, security.py reads it as today)

---

## 9. Cross-references

- `docs/operator/OPERATIONS.md` — operations runbook (this doc's parent)
- `polaris_web/docker-compose.prod.yml` — where Docker secrets are referenced
- `polaris_web/security.py` — runtime secret loading
- `DEVNOTES/threat-model.md` — STRIDE analysis
- `MISSION.md` C-constraints — C1 (audit append-only), C5 (CSP), C7 (algorithm metadata) all touch secret-handling discipline
- `sanctum/2026-05-13-launcher-fixes-v8-51-v8-56-v8-58.md` (if exists; or the relevant Sanctums) — historical record of session-secret rotation fixes
- `meta/arc-b-production.md` — Arc B (production deployment) strategic record
