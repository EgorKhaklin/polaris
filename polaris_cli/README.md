# polaris-cli

Command-line interface to the Polaris Identity Token System.

A scriptable wrapper around the use-case stored procedures
(`uc1_issue_and_activate`, `uc4_activate_reserve`, `uc5_bind_device`,
`uc6_migrate_algorithm`, `uc7_warrant_audit`, `uc8_revoke_token`,
`uc9_initiate_recovery`, `uc9_complete_recovery`) plus utility
commands for health checks, listing, token inspection, ad-hoc
queries, state-machine transitions, and application-user management
(create / passwd / deactivate / audit-log).

The v2 substrate procedures shipped through Flask routes only (not yet
wrapped here): `close_anchor_batch` (R10-2), `uc10_attest_trust` /
`uc10_revoke_attestation` (R11-3), `uc11_close_epoch` (R10-1),
`uc12_record_duress` (R11-5). To invoke these from the CLI, use
`polaris query` with explicit `CALL` statements, or the Flask API
endpoints via `curl`. Direct CLI subcommands for them are a future
backlog item.

## Install

```bash
pip3 install --break-system-packages psycopg2-binary
chmod +x polaris.py
# Optional: put on PATH
sudo ln -s "$(pwd)/polaris.py" /usr/local/bin/polaris
```

## Configuration

Same environment variables as the web app:

| Variable               | Default                |
|------------------------|------------------------|
| `POLARIS_DB_HOST`      | `localhost`            |
| `POLARIS_DB_NAME`      | `polaris_test`         |
| `POLARIS_DB_USER`      | `polaris_app`          |
| `POLARIS_DB_PASSWORD`  | `polaris_dev_password` |
| `NO_COLOR`             | unset (color enabled)  |

## Commands

### `polaris health`

System-wide statistics: row counts per table, token-status breakdown, PQ vs
classical migration status, disclosure posture distribution. Mirrors the
Atlas health strip in the web UI.

### `polaris list <entity>`

Browse principal entities. Supports filters where appropriate.

```bash
polaris list individuals
polaris list agencies
polaris list tokens --status ACTIVE
polaris list verifications --context BANKING --outcome SUCCESS --limit 20
polaris list algorithms
polaris list contexts
```

### `polaris inspect <token-id>`

Full detail for a single token: record, lifecycle history, verification
events, device bindings.

```bash
polaris inspect 2
```

### `polaris query "SQL"`

Read-only SQL console (SELECT or WITH only). Same hardening as the web SQL
console: 5,000-character limit, 5-second statement timeout, no DDL.

```bash
polaris query "SELECT context_type, COUNT(*) FROM VerificationEvent ve JOIN VerificationContext vc USING(context_id) GROUP BY context_type ORDER BY 2 DESC"
```

### `polaris issue ...` (UC-1)

Atomic token issuance: creates Individual record, provisions IdentityToken,
performs hardware-binding ceremony, transitions to ACTIVE, grants permissions.

```bash
polaris issue \
    --legal-name "A. Holder" \
    --dob 1990-01-15 \
    --jurisdiction US-PA \
    --agency 1 \
    --algorithm 1 \
    --token-value TKN-PA-2026-100 \
    --serial SN-PA-100 \
    --biometric IRIS \
    --liveness MULTI_MODAL \
    --witness 2 \
    --hardware TitanQ-3 \
    --contexts 1,4,6
```

### `polaris activate-reserve ...` (UC-4)

Lose an active token, promote a reserve.

```bash
polaris activate-reserve \
    --lost-token 4 \
    --reserve-token 7 \
    --actor-agency 1 \
    --reason LOST \
    --crl-url "https://crl.idtoken.gov/2026/05/T4-LOST.crl"
```

### `polaris bind-device ...` (UC-5)

Bind a device to an active token.

```bash
polaris bind-device \
    --token 2 \
    --device-type PHONE \
    --fingerprint "SE-AAPL-A19-newdevice12345" \
    --binding-method SECURE_ENCLAVE \
    --validity-months 24
```

### `polaris warrant-audit ...` (UC-7)

Warrant-authorized verification history reconstruction. ZK events are
excluded by design (token_id was never stored, so they cannot be linked
to the individual).

```bash
polaris warrant-audit \
    --individual 3 \
    --context BANKING \
    --window-start "2026-01-01 00:00:00" \
    --window-end   "2026-12-31 23:59:59"
```

### `polaris transition <token-id> <new-status>`

Apply a state-machine transition. Sets the audit-trigger context GUCs so the
auto-audit trigger writes a properly-attributed lifecycle event.

```bash
polaris transition 2 DORMANT --actor 3 --reason QUARTERLY_REVIEW
polaris transition 4 LOST    --actor 1 --reason HOLDER_REPORTED_THEFT
```

### `polaris user-list`

List the application user accounts (web-app authentication accounts).
Shows username, role, active/inactive status, last login time, and lockout
state. Password hashes are NEVER displayed.

```bash
polaris user-list
```

### `polaris user-create <username> <role>`

Create a new application user. Username must match `[a-z0-9._-]{3,50}` (the
CLI lowercases automatically). Role must be `admin`, `operator`, or `auditor`.

Password is read interactively (no echo) by default, with confirmation.
Pass `--password` for scripting (less secure — visible in process listings).

Password complexity is enforced: ≥12 characters, at least one digit, one
letter, and one symbol.

```bash
# Interactive (recommended):
polaris user-create alice operator

# Scripted (avoid in shared shells):
polaris user-create alice operator --password 'StrongPass123!'
```

### `polaris user-passwd <username>`

Rotate a user's password. Also resets `failed_login_count` and
`locked_until`, so a locked-out user is unlocked. Same complexity rules as
`user-create`.

```bash
# Interactive:
polaris user-passwd alice

# After detecting a credential leak — rotate immediately:
polaris user-passwd admin --password 'NewStrongPass456!'
```

### `polaris user-deactivate <username>`

Soft-deletes a user account by setting `is_active = FALSE`. The user can no
longer log in, but their AuthAuditLog history is preserved (foreign keys
remain valid). To reactivate, run a SQL update directly.

```bash
polaris user-deactivate alice
```

### `polaris audit-log`

Tail the authentication audit log. Captures every login attempt (success
and failure), every CSRF rejection, every authorization denial, every
account lockout, and every rate-limit trigger. The schema-level append-only
trigger means these rows can never be modified.

```bash
# Last 50 events (default):
polaris audit-log

# Recent failed logins:
polaris audit-log --event-type LOGIN_FAILED --limit 20

# Brute-force detection:
polaris audit-log --event-type LOGIN_FAILED --since-minutes 60

# Activity for one user:
polaris audit-log --username alice --limit 100

# Per-IP analysis (chain via query):
polaris query "SELECT ip_address, COUNT(*) FROM AuthAuditLog
               WHERE event_type='LOGIN_FAILED'
                 AND event_timestamp > CURRENT_TIMESTAMP - INTERVAL '1 hour'
               GROUP BY ip_address ORDER BY 2 DESC"
```

## Exit Codes

| Code | Meaning                                                      |
|------|--------------------------------------------------------------|
| 0    | Success                                                      |
| 1    | Usage / argument error / record not found / weak password    |
| 2    | Database connection or generic SQL error                     |
| 3    | Procedure rejected the operation (constraint or business rule) |
| 130  | Interrupted (Ctrl-C)                                         |

## Testing

```bash
python3 test_cli.py
```

The CLI test suite has 53 integration tests covering every command, including
the user-management workflow (create → authenticate → rotate → deactivate),
audit-log filtering, and constraint-violation paths. Tests reset the database
to pristine sample state before each test.

Expected output: `Ran 53 tests in ~23s. OK`

## Examples for Scripting

```bash
# Bulk-issue tokens from a CSV
while IFS=, read name dob jur token serial; do
    polaris issue \
        --legal-name "$name" --dob "$dob" --jurisdiction "$jur" \
        --agency 1 --algorithm 1 --biometric IRIS \
        --token-value "$token" --serial "$serial" \
        --contexts 1,4
done < holders.csv

# Find all active tokens issued by a specific agency
polaris query "SELECT t.token_id, i.legal_name FROM IdentityToken t
               JOIN Individual i ON t.individual_id = i.individual_id
               WHERE t.issuing_agency_id = 1 AND t.status = 'ACTIVE'
               ORDER BY t.token_id"

# Pipe inspection JSON-style output to jq via the query command
polaris query "SELECT row_to_json(t) FROM IdentityToken t WHERE token_id = 2"

# Daily audit cron
polaris query "SELECT date_trunc('day', event_timestamp) AS day, COUNT(*)
               FROM VerificationEvent
               WHERE event_timestamp > CURRENT_DATE - INTERVAL '7 days'
               GROUP BY day ORDER BY day"
```
