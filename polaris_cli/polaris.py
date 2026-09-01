#!/usr/bin/env python3
"""
============================================================================
polaris-cli — Command-line interface to the Polaris Identity Token System
============================================================================

A scriptable wrapper around the four use-case stored procedures
(uc1_issue_and_activate, uc4_activate_reserve, uc5_bind_device,
uc7_warrant_audit) plus the relational-algebra queries from the report.

Usage:
    polaris <command> [options]

Commands:
    issue              UC-1: issue and activate a new token (atomic procedure)
    activate-reserve   UC-4: lose an active token, promote a reserve
    bind-device        UC-5: bind a device to an active token
    warrant-audit      UC-7: warrant-authorized verification history
    list               Browse principal entities (individuals/agencies/tokens)
    inspect            Detail view of a single token (record + history)
    query              Run any SELECT against the database (read-only)
    transition         Apply a state-machine transition to a token
    health             Schema-wide statistics (mirrors the Atlas health strip)
    user-list          List application users (web-app auth accounts)
    user-create        Create a new application user
    user-passwd        Change an application user's password
    user-deactivate    Deactivate an application user (soft-delete)
    audit-log          Tail the authentication audit log
    --help / -h        Show help for any command

Connection is configured via the same environment variables as the web app:
    POLARIS_DB_HOST, POLARIS_DB_NAME, POLARIS_DB_USER, POLARIS_DB_PASSWORD

Examples:
    polaris health
    polaris list tokens --status ACTIVE
    polaris inspect 2
    polaris issue --legal-name "A. Holder" --dob 1990-01-15 --jurisdiction US-PA \\
                  --agency 1 --algorithm 1 --token-value TKN-PA-NEW-001 \\
                  --serial SN-PA-NEW --biometric IRIS --contexts 1,4
    polaris warrant-audit --individual 3 --context BANKING
    polaris query "SELECT context_type, COUNT(*) FROM VerificationEvent GROUP BY context_type"

Exit codes:
    0  success
    1  usage / argument error
    2  database error
    3  procedure rejected the operation (constraint or business-rule violation)
============================================================================
"""

import argparse
import os
import sys
from datetime import datetime

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
except ImportError:
    sys.stderr.write("ERROR: psycopg2 is required. Install with:\n")
    sys.stderr.write("    pip install psycopg2-binary\n")
    sys.exit(1)

# werkzeug is only required for user-management commands. Import lazily so the
# CLI's read-only commands (health, list, inspect, query, etc.) work without it.
def _require_werkzeug():
    try:
        from werkzeug.security import generate_password_hash
        return generate_password_hash
    except ImportError:
        sys.stderr.write("ERROR: werkzeug is required for user-management commands.\n")
        sys.stderr.write("    pip install Flask  (werkzeug ships with Flask)\n")
        sys.exit(1)


# ----------------------------------------------------------------------------
# ANSI color helpers (auto-disabled when stdout isn't a TTY or NO_COLOR is set)
# ----------------------------------------------------------------------------

USE_COLOR = sys.stdout.isatty() and not os.environ.get('NO_COLOR')

def _c(code, text):
    return f"\033[{code}m{text}\033[0m" if USE_COLOR else text

def navy(s):  return _c('34', s)
def gold(s):  return _c('33', s)
def green(s): return _c('32', s)
def red(s):   return _c('31', s)
def dim(s):   return _c('2', s)
def bold(s):  return _c('1', s)


# ----------------------------------------------------------------------------
# Database connection (matches the Flask app's defaults)
# ----------------------------------------------------------------------------

def get_db_config():
    return {
        'host':     os.environ.get('POLARIS_DB_HOST',     'localhost'),
        'database': os.environ.get('POLARIS_DB_NAME',     'polaris_test'),
        'user':     os.environ.get('POLARIS_DB_USER',     'polaris_app'),
        'password': os.environ.get('POLARIS_DB_PASSWORD', 'polaris_dev_password'),
    }


def connect():
    try:
        return psycopg2.connect(cursor_factory=RealDictCursor, **get_db_config())
    except psycopg2.Error as e:
        sys.stderr.write(red(f"Database connection failed: {e}\n"))
        cfg = get_db_config()
        sys.stderr.write(dim(f"  host={cfg['host']} db={cfg['database']} user={cfg['user']}\n"))
        sys.exit(2)


def db_error_message(e):
    """Mirror of the web app's error-message translation."""
    msg = str(e).strip()
    if 'duplicate key value' in msg and 'uq_one_active_per_person' in msg:
        return "Cannot create a second ACTIVE token for this individual."
    if 'violates check constraint' in msg and 'chk_disclosure_token_consistency' in msg:
        return "Disclosure level inconsistent with token reference."
    if 'Illegal token state transition' in msg:
        for line in msg.split('\n'):
            if 'Illegal token state transition' in line:
                return line.replace('ERROR:', '').strip()
    if 'is forbidden' in msg and 'append-only' in msg:
        return "This table is append-only (audit invariant). UPDATE/DELETE rejected."
    if 'violates foreign key constraint' in msg:
        return "Referential integrity violation."
    return msg.split('\n')[0].replace('ERROR:', '').strip() or msg


# ----------------------------------------------------------------------------
# Output formatting: pretty tables for terminal output
# ----------------------------------------------------------------------------

def print_table(rows, columns=None, title=None):
    """Render a list of dict rows as an aligned ASCII table."""
    if not rows:
        if title:
            print(bold(title))
        print(dim("(no rows)"))
        return

    if columns is None:
        columns = list(rows[0].keys())

    # Compute widths
    widths = {c: max(len(str(c)), max(len(_fmt(r.get(c))) for r in rows)) for c in columns}

    if title:
        print(bold(title))

    # Header
    sep = '─' * (sum(widths.values()) + 3 * len(columns) - 1)
    print(navy(sep))
    print(navy('  ' + '   '.join(c.ljust(widths[c]) for c in columns)))
    print(navy(sep))

    # Rows
    for r in rows:
        cells = []
        for c in columns:
            val = _fmt(r.get(c))
            # Color-code status pills if present
            if c == 'status' or c.endswith('_status'):
                val = _color_status(val).ljust(widths[c] + (5 if USE_COLOR else 0))
            elif c == 'outcome':
                val = _color_outcome(val).ljust(widths[c] + (5 if USE_COLOR else 0))
            elif c == 'disclosure_level':
                val = _color_disclosure(val).ljust(widths[c] + (5 if USE_COLOR else 0))
            else:
                val = val.ljust(widths[c])
            cells.append(val)
        print('  ' + '   '.join(cells))
    print(navy(sep))
    print(dim(f"  ({len(rows)} row{'s' if len(rows) != 1 else ''})"))


def _fmt(v):
    if v is None: return '—'
    if isinstance(v, datetime): return v.strftime('%Y-%m-%d %H:%M')
    return str(v)


def _color_status(s):
    if not USE_COLOR: return s
    return {'ACTIVE':  green(s), 'RESERVE': navy(s),
            'REVOKED': red(s),   'LOST':    gold(s),
            'EXPIRED': dim(s),   'DORMANT': dim(s)}.get(s, s)


def _color_outcome(s):
    if not USE_COLOR: return s
    return {'SUCCESS': green(s), 'FAILURE': red(s),
            'EXPIRED': dim(s),   'UNAUTHORIZED': gold(s)}.get(s, s)


def _color_disclosure(s):
    if not USE_COLOR: return s
    return {'FULL': gold(s), 'SELECTIVE': navy(s),
            'ZERO_KNOWLEDGE': green(s)}.get(s, s)


def print_kv(items, title=None):
    """Render a dict-like object as aligned key:value pairs."""
    if title:
        print(bold(title))
        print(navy('─' * len(title)))
    width = max(len(k) for k, _ in items) if items else 0
    for k, v in items:
        print(f"  {dim(k.ljust(width))}  {_fmt(v)}")


# ----------------------------------------------------------------------------
# COMMAND: health
# ----------------------------------------------------------------------------

def cmd_health(args):
    conn = connect()
    with conn.cursor() as cur:
        # Per-table counts
        tables = ['Individual', 'Agency', 'CryptographicAlgorithm', 'VerificationContext',
                  'IdentityToken', 'TokenLifecycleEvent', 'VerificationEvent',
                  'DeviceBinding', 'BlockchainAnchor', 'RevocationList',
                  'AgencyAlgorithmAuth', 'TokenPermission']
        counts = {}
        for tbl in tables:
            cur.execute(f"SELECT COUNT(*) AS n FROM {tbl}")
            counts[tbl] = cur.fetchone()['n']

        # State breakdown
        cur.execute("SELECT status, COUNT(*) AS n FROM IdentityToken GROUP BY status")
        states = {r['status']: r['n'] for r in cur.fetchall()}

        # Disclosure breakdown
        cur.execute("""
            SELECT disclosure_level, COUNT(*) AS n
            FROM VerificationEvent GROUP BY disclosure_level
        """)
        disc = {r['disclosure_level']: r['n'] for r in cur.fetchall()}
        total_verifs = sum(disc.values()) or 1

        # PQ active tokens
        cur.execute("""
            SELECT alg.quantum_resistant, COUNT(*) AS n
            FROM IdentityToken t
            JOIN CryptographicAlgorithm alg ON t.algorithm_id = alg.algorithm_id
            WHERE t.status = 'ACTIVE'
            GROUP BY alg.quantum_resistant
        """)
        pq = {r['quantum_resistant']: r['n'] for r in cur.fetchall()}
        pq_active = pq.get(True, 0)
        cl_active = pq.get(False, 0)
        total_active = pq_active + cl_active or 1

    conn.close()

    print()
    print(bold(gold("  POLARIS  ") + navy("Identity Token System")))
    print(dim("  ────────────────────────────────────────"))
    print()
    print(bold("  Schema Statistics"))
    cols = max(len(t) for t in counts)
    for tbl in tables:
        bar = '█' * min(counts[tbl], 40)
        print(f"    {dim(tbl.ljust(cols))}  {str(counts[tbl]).rjust(4)}  {dim(bar)}")
    print(f"    {bold('TOTAL'.ljust(cols))}  {bold(str(sum(counts.values())).rjust(4))}")

    print()
    print(bold("  Token Status"))
    for s in ['ACTIVE', 'RESERVE', 'DORMANT', 'REVOKED', 'LOST', 'EXPIRED']:
        n = states.get(s, 0)
        if n:
            print(f"    {_color_status(s).ljust(20)}  {n}")

    print()
    print(bold("  Post-Quantum Migration"))
    print(f"    {green('PQ active'.ljust(20))}  {pq_active} ({100*pq_active//total_active}%)")
    if cl_active:
        print(f"    {red('Classical active'.ljust(20))}  {cl_active} ({100*cl_active//total_active}%)")

    print()
    print(bold("  Disclosure Posture"))
    for d in ['FULL', 'SELECTIVE', 'ZERO_KNOWLEDGE']:
        n = disc.get(d, 0)
        print(f"    {_color_disclosure(d).ljust(25)}  {n} ({100*n//total_verifs}%)")
    print()


# ----------------------------------------------------------------------------
# COMMAND: list
# ----------------------------------------------------------------------------

def cmd_list(args):
    entity = args.entity.lower()
    conn = connect()
    with conn.cursor() as cur:
        if entity == 'individuals':
            cur.execute("""
                SELECT individual_id, legal_name, date_of_birth, jurisdiction, enrollment_date
                FROM Individual ORDER BY individual_id
            """)
            print_table(cur.fetchall(), title="Individuals")
        elif entity == 'agencies':
            cur.execute("""
                SELECT agency_id, name, agency_type, jurisdiction, authorization_level
                FROM Agency ORDER BY agency_id
            """)
            print_table(cur.fetchall(), title="Agencies")
        elif entity == 'tokens':
            sql = """
                SELECT t.token_id, t.token_value, i.legal_name AS holder,
                       ag.name AS issuer, alg.name AS algorithm, t.status
                FROM IdentityToken t
                JOIN Individual i  ON t.individual_id = i.individual_id
                JOIN Agency    ag  ON t.issuing_agency_id = ag.agency_id
                JOIN CryptographicAlgorithm alg ON t.algorithm_id = alg.algorithm_id
            """
            params = []
            if args.status:
                sql += " WHERE t.status = %s"
                params.append(args.status)
            sql += " ORDER BY t.token_id"
            cur.execute(sql, params)
            print_table(cur.fetchall(), title="Identity Tokens")
        elif entity == 'algorithms':
            cur.execute("""
                SELECT algorithm_id, name, family, security_level_bits, quantum_resistant, deprecation_date
                FROM CryptographicAlgorithm ORDER BY algorithm_id
            """)
            print_table(cur.fetchall(), title="Cryptographic Algorithms")
        elif entity == 'contexts':
            cur.execute("""
                SELECT context_id, context_type, requires_biometric, min_security_level
                FROM VerificationContext ORDER BY context_id
            """)
            print_table(cur.fetchall(), title="Verification Contexts")
        elif entity == 'verifications':
            sql = """
                SELECT ve.event_id, ve.event_timestamp, vc.context_type,
                       ag.name AS verifier, ve.outcome, ve.disclosure_level,
                       i.legal_name AS holder
                FROM VerificationEvent ve
                JOIN VerificationContext vc ON ve.context_id = vc.context_id
                JOIN Agency ag              ON ve.requesting_agency_id = ag.agency_id
                LEFT JOIN IdentityToken t   ON ve.token_id = t.token_id
                LEFT JOIN Individual i      ON t.individual_id = i.individual_id
            """
            params = []
            wheres = []
            if args.context:
                wheres.append("vc.context_type = %s")
                params.append(args.context)
            if args.outcome:
                wheres.append("ve.outcome = %s")
                params.append(args.outcome)
            if wheres:
                sql += " WHERE " + " AND ".join(wheres)
            sql += " ORDER BY ve.event_timestamp DESC LIMIT %s"
            params.append(args.limit)
            cur.execute(sql, params)
            print_table(cur.fetchall(), title="Verification Events (most recent first)")
        else:
            sys.stderr.write(red(f"Unknown entity: {entity}\n"))
            sys.stderr.write(dim("Valid: individuals, agencies, tokens, algorithms, contexts, verifications\n"))
            sys.exit(1)
    conn.close()


# ----------------------------------------------------------------------------
# COMMAND: inspect
# ----------------------------------------------------------------------------

def cmd_inspect(args):
    tok_id = args.token_id
    conn = connect()
    with conn.cursor() as cur:
        cur.execute("""
            SELECT t.*, i.legal_name, ag.name AS issuer_name, alg.name AS algorithm_name,
                   alg.quantum_resistant
            FROM IdentityToken t
            JOIN Individual i  ON t.individual_id = i.individual_id
            JOIN Agency    ag  ON t.issuing_agency_id = ag.agency_id
            JOIN CryptographicAlgorithm alg ON t.algorithm_id = alg.algorithm_id
            WHERE t.token_id = %s
        """, (tok_id,))
        token = cur.fetchone()
        if not token:
            sys.stderr.write(red(f"Token #{tok_id} not found.\n"))
            sys.exit(1)

        print()
        print(bold(f"  Token #{tok_id}  ") + _color_status(token['status']))
        print(navy('  ' + '─' * 50))
        print_kv([
            ('Token Value',       token['token_value']),
            ('Physical Serial',   token['physical_serial']),
            ('Hardware Model',    token['hardware_model']),
            ('Holder',            f"{token['legal_name']} (#{token['individual_id']})"),
            ('Issuer',            token['issuer_name']),
            ('Algorithm',         f"{token['algorithm_name']} {'[PQ]' if token['quantum_resistant'] else '[CLASSICAL]'}"),
            ('Biometric Binding', token['biometric_binding_type']),
            ('Liveness Check',    token['liveness_check_type']),
            ('Issued',            token['issued_date']),
            ('Activated',         token['activated_date']),
            ('Expires',           token['expiration_date']),
            ('Activation Seq',    token['activation_sequence']),
            ('Predecessor',       (f"#{token['predecessor_token_id']}" if token['predecessor_token_id'] else None)),
        ])

        # Lifecycle
        cur.execute("""
            SELECT le.event_id, le.event_type, le.event_timestamp,
                   ag.name AS actor, le.reason_code
            FROM TokenLifecycleEvent le
            LEFT JOIN Agency ag ON le.actor_agency_id = ag.agency_id
            WHERE le.token_id = %s ORDER BY le.event_timestamp
        """, (tok_id,))
        events = cur.fetchall()
        print()
        print_table(events, title=f"Lifecycle History ({len(events)} events)")

        # Verifications
        cur.execute("""
            SELECT ve.event_id, ve.event_timestamp, vc.context_type,
                   ag.name AS verifier, ve.outcome, ve.disclosure_level
            FROM VerificationEvent ve
            JOIN VerificationContext vc ON ve.context_id = vc.context_id
            JOIN Agency ag              ON ve.requesting_agency_id = ag.agency_id
            WHERE ve.token_id = %s ORDER BY ve.event_timestamp DESC
        """, (tok_id,))
        print()
        print_table(cur.fetchall(), title="Verification Events")

        # Devices
        cur.execute("""
            SELECT binding_id, device_type, status, authorized_date, expires_date
            FROM DeviceBinding WHERE token_id = %s ORDER BY binding_id
        """, (tok_id,))
        print()
        print_table(cur.fetchall(), title="Device Bindings")

    conn.close()


# ----------------------------------------------------------------------------
# COMMAND: query
# ----------------------------------------------------------------------------

def cmd_query(args):
    sql = args.sql
    if not sql.strip():
        sys.stderr.write(red("Empty SQL.\n"))
        sys.exit(1)
    first = sql.strip().split()[0].upper()
    if first not in ('SELECT', 'WITH'):
        sys.stderr.write(red("Only SELECT and WITH queries are accepted.\n"))
        sys.exit(1)
    if len(sql) > 5000:
        sys.stderr.write(red(f"Query too long ({len(sql)} > 5000 chars).\n"))
        sys.exit(1)

    try:
        conn = psycopg2.connect(**get_db_config())  # plain cursor for tuples
    except psycopg2.Error as e:
        sys.stderr.write(red(f"Database connection failed: {db_error_message(e)}\n"))
        cfg = get_db_config()
        sys.stderr.write(dim(f"  host={cfg['host']} db={cfg['database']} user={cfg['user']}\n"))
        sys.exit(2)
    # Enforce read-only at the ENGINE level. The SELECT/WITH prefix check above
    # does NOT stop data-modifying CTEs — `WITH x AS (UPDATE ... RETURNING ...)
    # SELECT * FROM x` passes the prefix guard and PostgreSQL runs the UPDATE.
    # Today only the absence of a commit keeps that from persisting; a read-only
    # transaction rejects any write outright, regardless of commit behavior.
    conn.set_session(readonly=True)
    try:
        with conn.cursor() as cur:
            cur.execute("SET statement_timeout = 5000")
            cur.execute(sql)
            if not cur.description:
                print(dim("Query returned no result set."))
                return
            columns = [c.name for c in cur.description]
            rows = cur.fetchall()
            dict_rows = [dict(zip(columns, r)) for r in rows]
            print_table(dict_rows, columns=columns)
    except psycopg2.errors.QueryCanceled:
        sys.stderr.write(red("Query timed out (5s limit).\n"))
        sys.exit(2)
    except psycopg2.Error as e:
        sys.stderr.write(red(f"Query failed: {db_error_message(e)}\n"))
        sys.exit(2)
    finally:
        conn.close()


# ----------------------------------------------------------------------------
# COMMAND: issue (UC-1)
# ----------------------------------------------------------------------------

def cmd_issue(args):
    try:
        contexts = [int(c.strip()) for c in args.contexts.split(',')]
    except ValueError:
        sys.stderr.write(red(
            "--contexts must be a comma-separated list of integers (e.g. 1,4,6).\n"))
        sys.exit(1)
    conn = connect()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT uc1_issue_and_activate(
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                ) AS token_id
            """, (
                args.legal_name, args.dob, args.jurisdiction,
                args.agency, args.algorithm,
                args.biometric, args.witness,
                args.liveness, args.token_value, args.serial,
                args.hardware, contexts,
            ))
            new_id = cur.fetchone()['token_id']
            conn.commit()
        print(green(f"✓ Issued and activated token #{new_id}"))
        # Show the new record
        args.token_id = new_id
        cmd_inspect(args)
    except psycopg2.Error as e:
        conn.rollback()
        sys.stderr.write(red(f"UC-1 rejected: {db_error_message(e)}\n"))
        sys.exit(3)
    finally:
        conn.close()


# ----------------------------------------------------------------------------
# COMMAND: activate-reserve (UC-4)
# ----------------------------------------------------------------------------

def cmd_activate_reserve(args):
    conn = connect()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT uc4_activate_reserve(%s, %s, %s, %s, %s) AS token_id
            """, (
                args.lost_token, args.actor_agency,
                args.reason, args.reserve_token,
                args.crl_url,
            ))
            promoted = cur.fetchone()['token_id']
            conn.commit()
        print(green(f"✓ Promoted reserve token #{promoted} to ACTIVE"))
        print(green(f"✓ Demoted lost token #{args.lost_token} (reason: {args.reason})"))
    except psycopg2.Error as e:
        conn.rollback()
        sys.stderr.write(red(f"UC-4 rejected: {db_error_message(e)}\n"))
        sys.exit(3)
    finally:
        conn.close()


# ----------------------------------------------------------------------------
# COMMAND: bind-device (UC-5)
# ----------------------------------------------------------------------------

def cmd_bind_device(args):
    conn = connect()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT uc5_bind_device(%s, %s, %s, %s, %s) AS binding_id
            """, (
                args.token, args.device_type, args.fingerprint,
                args.binding_method, args.validity_months,
            ))
            binding_id = cur.fetchone()['binding_id']
            conn.commit()
        print(green(f"✓ Created device binding #{binding_id}"))
    except psycopg2.Error as e:
        conn.rollback()
        sys.stderr.write(red(f"UC-5 rejected: {db_error_message(e)}\n"))
        sys.exit(3)
    finally:
        conn.close()


# ----------------------------------------------------------------------------
# COMMAND: migrate-algorithm (UC-6)
# ----------------------------------------------------------------------------

def cmd_migrate_algorithm(args):
    """UC-6 / R11-1 / M2-6: migrate a token to a new cryptographic algorithm.

    Calls uc6_migrate_algorithm(token_id, new_algorithm_id,
    new_signature_bytes, deprecate_old). Reads signature from --signature-hex
    (raw hex) or --signature-file (binary bytes). Optionally deprecates the
    old signature(s) with --deprecate-old.
    """
    if args.signature_hex:
        sig_bytes = bytes.fromhex(args.signature_hex)
    else:
        with open(args.signature_file, 'rb') as f:
            sig_bytes = f.read()
    conn = connect()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                CALL uc6_migrate_algorithm(%s, %s, %s, %s)
            """, (args.token, args.new_algorithm, sig_bytes, args.deprecate_old))
            conn.commit()
        action = "migrated + deprecated old" if args.deprecate_old else "migrated"
        print(green(f"✓ Token #{args.token}: {action} to algorithm #{args.new_algorithm}"))
    except psycopg2.Error as e:
        conn.rollback()
        sys.stderr.write(red(f"UC-6 rejected: {db_error_message(e)}\n"))
        sys.exit(3)
    finally:
        conn.close()


# ----------------------------------------------------------------------------
# COMMAND: revoke (UC-8)
# ----------------------------------------------------------------------------

def cmd_revoke(args):
    """UC-8 / R11-6: revoke an ACTIVE token.

    Calls uc8_revoke_token(token_id, actor_agency, reason_code,
    published_location, cosigner_agency). Enforces per-issuer revocation-
    rate bounds (5% / 30-day default per IssuerDiscretionPolicy).
    """
    conn = connect()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                CALL uc8_revoke_token(%s, %s, %s, %s, %s)
            """, (
                args.token, args.actor_agency, args.reason,
                args.published_location, args.cosigner_agency,
            ))
            conn.commit()
        print(green(f"✓ Revoked token #{args.token} (reason: {args.reason})"))
    except psycopg2.Error as e:
        conn.rollback()
        sys.stderr.write(red(f"UC-8 rejected: {db_error_message(e)}\n"))
        sys.exit(3)
    finally:
        conn.close()


# ----------------------------------------------------------------------------
# COMMAND: recovery-initiate (UC-9 phase 1)
# ----------------------------------------------------------------------------

def cmd_recovery_initiate(args):
    """UC-9 phase 1 / R11-2 / M2-9: open a catastrophic-loss recovery
    ceremony for an individual with no ACTIVE token. Returns the
    recovery_id via NOTICE; the CLI extracts it for the operator.
    """
    conn = connect()
    try:
        with conn.cursor() as cur:
            # Capture NOTICE so we can extract the recovery_id
            notices = []
            try:
                conn.notices.clear()
            except AttributeError:
                pass
            cur.execute("""
                CALL uc9_initiate_recovery(%s, %s, %s, %s)
            """, (
                args.individual, args.requesting_agency,
                args.requesting_user, args.cooldown_hours,
            ))
            conn.commit()
            # Surface NOTICE messages so the recovery_id is visible
            for n in (conn.notices or []):
                notices.append(n.strip())
        print(green(f"✓ Recovery initiated for individual #{args.individual}"))
        for n in notices:
            print(dim(f"  {n}"))
    except psycopg2.Error as e:
        conn.rollback()
        sys.stderr.write(red(f"UC-9 initiate rejected: {db_error_message(e)}\n"))
        sys.exit(3)
    finally:
        conn.close()


# ----------------------------------------------------------------------------
# COMMAND: recovery-complete (UC-9 phase 2)
# ----------------------------------------------------------------------------

def cmd_recovery_complete(args):
    """UC-9 phase 2 / R11-2 / M2-9: approve or reject a pending recovery
    request. APPROVED issues a new token bound to the individual;
    REJECTED closes the request with the supplied reason.
    """
    conn = connect()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                CALL uc9_complete_recovery(
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
            """, (
                args.recovery_id, args.deciding_user, args.decision,
                args.reason, args.new_token_value, args.new_serial,
                args.algorithm, args.biometric_binding,
                args.liveness_check, args.published_location,
            ))
            conn.commit()
        print(green(f"✓ Recovery #{args.recovery_id}: {args.decision}"))
    except psycopg2.Error as e:
        conn.rollback()
        sys.stderr.write(red(f"UC-9 complete rejected: {db_error_message(e)}\n"))
        sys.exit(3)
    finally:
        conn.close()


# ----------------------------------------------------------------------------
# COMMAND: warrant-audit (UC-7)
# ----------------------------------------------------------------------------

def cmd_warrant_audit(args):
    conn = connect()
    with conn.cursor() as cur:
        cur.execute("""
            SELECT * FROM uc7_warrant_audit(%s, %s, %s, %s)
            ORDER BY event_timestamp
        """, (
            args.individual,
            args.window_start or '1970-01-01 00:00:00',
            args.window_end   or '2099-12-31 23:59:59',
            args.context,
        ))
        rows = cur.fetchall()
    conn.close()
    print_table(rows, title=f"Warrant Audit — Individual #{args.individual}")
    if rows:
        zk = sum(1 for r in rows if r['disclosure_level'] == 'ZERO_KNOWLEDGE')
        print(dim(f"\n  Note: {zk} ZK events excluded by design (token_id was never stored)."))


# ----------------------------------------------------------------------------
# COMMAND: user-list (browse AppUser accounts)
# ----------------------------------------------------------------------------

def cmd_user_list(args):
    """List application users with role, status, last login, lockout state.

    Pulled directly from AppUser. Hashes are never displayed, even briefly."""
    conn = connect()
    with conn.cursor() as cur:
        cur.execute("""
            SELECT user_id, username, role, is_active,
                   last_login_at, failed_login_count,
                   locked_until,
                   CASE WHEN locked_until IS NOT NULL AND locked_until > CURRENT_TIMESTAMP
                        THEN 'YES' ELSE 'no' END AS locked,
                   created_at
              FROM AppUser
             ORDER BY user_id
        """)
        rows = cur.fetchall()
    conn.close()

    print()
    print(bold("  Application Users"))
    print(dim("  ─────────────────"))
    if not rows:
        print(dim("  (no users)"))
        return

    for r in rows:
        status = green('active') if r['is_active'] else red('inactive')
        role_color = {'admin': gold, 'operator': green, 'auditor': navy}.get(r['role'], lambda x: x)
        last_login = r['last_login_at'].strftime('%Y-%m-%d %H:%M') if r['last_login_at'] else dim('never')
        lock_str = ''
        if r['locked'] == 'YES':
            lock_str = '  ' + red(f"[LOCKED until {r['locked_until'].strftime('%H:%M')}]")
        elif r['failed_login_count'] > 0:
            lock_str = '  ' + dim(f"({r['failed_login_count']} recent failures)")

        print(f"  #{r['user_id']:<2}  {bold(r['username']):20}  "
              f"{role_color(r['role'].upper()):20}  {status}  "
              f"last login: {last_login}{lock_str}")
    print()


# ----------------------------------------------------------------------------
# COMMAND: user-create (provision a new AppUser)
# ----------------------------------------------------------------------------

def _validate_password(pw):
    """Enforce the same complexity gate the docker-init script uses."""
    if len(pw) < 12:
        return "Password must be at least 12 characters."
    if not any(c.isdigit() for c in pw):
        return "Password must contain at least one digit."
    if not any(c.isalpha() for c in pw):
        return "Password must contain at least one letter."
    if not any(not c.isalnum() for c in pw):
        return "Password must contain at least one symbol."
    return None


def _read_password_interactively(prompt='New password: '):
    """Read a password without echoing, confirm by reading twice."""
    import getpass
    while True:
        pw1 = getpass.getpass(prompt)
        pw2 = getpass.getpass('Confirm:        ')
        if pw1 != pw2:
            sys.stderr.write(red("Passwords do not match. Try again.\n"))
            continue
        err = _validate_password(pw1)
        if err:
            sys.stderr.write(red(err + " Try again.\n"))
            continue
        return pw1


def cmd_user_create(args):
    generate_password_hash = _require_werkzeug()

    # Read password — from --password (insecure, only for scripts) or interactively.
    if args.password:
        pw = args.password
        err = _validate_password(pw)
        if err:
            sys.stderr.write(red(err + "\n"))
            sys.exit(1)
    else:
        pw = _read_password_interactively()

    pw_hash = generate_password_hash(pw, method='scrypt')

    conn = connect()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO AppUser (username, password_hash, role)
                VALUES (%s, %s, %s)
                RETURNING user_id
            """, (args.username.lower(), pw_hash, args.role))
            new_id = cur.fetchone()['user_id']
            conn.commit()
        print(green(f"✓ Created user #{new_id}: {args.username} ({args.role})"))
    except psycopg2.errors.UniqueViolation:
        conn.rollback()
        sys.stderr.write(red(f"User {args.username!r} already exists.\n"))
        sys.exit(3)
    except psycopg2.errors.CheckViolation as e:
        conn.rollback()
        msg = str(e)
        if 'chk_appuser_username_format' in msg:
            sys.stderr.write(red(
                "Username must match [a-z0-9._-]{3,50} "
                "(lowercase letters, digits, dots, underscores, hyphens; 3-50 chars).\n"
            ))
        elif 'chk_appuser_role' in msg:
            sys.stderr.write(red(
                "Role must be one of: admin, operator, auditor.\n"
            ))
        else:
            sys.stderr.write(red(f"Constraint violation: {msg.split(chr(10))[0]}\n"))
        sys.exit(3)
    except psycopg2.Error as e:
        conn.rollback()
        sys.stderr.write(red(f"Database error: {db_error_message(e)}\n"))
        sys.exit(2)
    finally:
        conn.close()


# ----------------------------------------------------------------------------
# COMMAND: user-passwd (rotate a user's password)
# ----------------------------------------------------------------------------

def cmd_user_passwd(args):
    generate_password_hash = _require_werkzeug()

    if args.password:
        pw = args.password
        err = _validate_password(pw)
        if err:
            sys.stderr.write(red(err + "\n"))
            sys.exit(1)
    else:
        pw = _read_password_interactively(f"New password for {args.username}: ")

    pw_hash = generate_password_hash(pw, method='scrypt')

    conn = connect()
    try:
        with conn.cursor() as cur:
            # Reset failed-login count and lock so the user isn't locked out
            # post-rotation. This is the operator's call: they're touching the
            # account anyway.
            cur.execute("""
                UPDATE AppUser
                   SET password_hash = %s,
                       failed_login_count = 0,
                       locked_until = NULL
                 WHERE username = %s
                RETURNING user_id
            """, (pw_hash, args.username.lower()))
            row = cur.fetchone()
            if row is None:
                sys.stderr.write(red(f"No such user: {args.username}\n"))
                sys.exit(1)
            # v9.189 (P1.7): a rotated password ends every live web session of
            # the account; the app treats the revoked registry rows as anonymous
            # on their next request.
            cur.execute("""
                UPDATE OperatorSession
                   SET revoked_at = now(), revoke_reason = 'password_changed'
                 WHERE user_id = %s AND revoked_at IS NULL
            """, (row['user_id'],))
            revoked = cur.rowcount
            conn.commit()
        print(green(f"✓ Password updated for {args.username} (#{row['user_id']})"))
        print(dim(f"  Revoked {revoked} live web session(s)."))
    except psycopg2.Error as e:
        conn.rollback()
        sys.stderr.write(red(f"Database error: {db_error_message(e)}\n"))
        sys.exit(2)
    finally:
        conn.close()


# ----------------------------------------------------------------------------
# COMMAND: user-deactivate (soft-delete an account)
# ----------------------------------------------------------------------------

def cmd_user_deactivate(args):
    """Set is_active=false. The user can no longer log in, but their audit
    history is preserved (foreign keys from AuthAuditLog still resolve)."""
    conn = connect()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE AppUser SET is_active = FALSE WHERE username = %s
                RETURNING user_id, role
            """, (args.username.lower(),))
            row = cur.fetchone()
            if row is None:
                sys.stderr.write(red(f"No such user: {args.username}\n"))
                sys.exit(1)
            # v9.189 (P1.7): deactivation ends the account's live web sessions
            # now (the app would also catch is_active on their next request).
            cur.execute("""
                UPDATE OperatorSession
                   SET revoked_at = now(), revoke_reason = 'deactivated'
                 WHERE user_id = %s AND revoked_at IS NULL
            """, (row['user_id'],))
            revoked = cur.rowcount
            conn.commit()
        print(green(f"✓ Deactivated {args.username} (#{row['user_id']}, role={row['role']})"))
        print(dim(f"  Revoked {revoked} live web session(s)."))
        print(dim(f"  Audit history preserved. To reactivate:"))
        print(dim(f"    polaris query \"UPDATE AppUser SET is_active=TRUE WHERE username='{args.username.lower()}'\""))
    except psycopg2.Error as e:
        conn.rollback()
        sys.stderr.write(red(f"Database error: {db_error_message(e)}\n"))
        sys.exit(2)
    finally:
        conn.close()


# ----------------------------------------------------------------------------
# COMMAND: audit-log (tail authentication audit events)
# ----------------------------------------------------------------------------

def cmd_audit_log(args):
    """Recent rows from AuthAuditLog with optional filters.

    The web app's @login_required, @csrf_protect, lockout, and rate-limiter
    decorators all write here. This command is the operator's view into who
    is trying to log in, who is being denied, and when CSRF rejections happen.
    """
    conn = connect()
    with conn.cursor() as cur:
        sql = """
            SELECT audit_id, event_timestamp, event_type,
                   username, user_id, ip_address, detail
              FROM AuthAuditLog
        """
        params = []
        wheres = []
        if args.event_type:
            wheres.append("event_type = %s")
            params.append(args.event_type)
        if args.username:
            wheres.append("username = %s")
            params.append(args.username.lower())
        if args.since_minutes:
            wheres.append("event_timestamp > CURRENT_TIMESTAMP - (%s || ' minutes')::INTERVAL")
            params.append(str(args.since_minutes))
        if wheres:
            sql += " WHERE " + " AND ".join(wheres)
        sql += " ORDER BY audit_id DESC LIMIT %s"
        params.append(args.limit)
        cur.execute(sql, params)
        rows = cur.fetchall()
    conn.close()

    if not rows:
        print(dim("  (no events match)"))
        return

    print()
    print(bold(f"  Authentication Audit ({len(rows)} most recent)"))
    print(dim("  " + "─" * 68))
    for r in rows:
        ts = r['event_timestamp'].strftime('%Y-%m-%d %H:%M:%S')
        et = r['event_type']
        # Color-code by severity
        if et == 'LOGIN_SUCCESS':
            et_str = green(et)
        elif et in ('LOGIN_FAILED', 'LOGIN_LOCKED', 'CSRF_REJECTED', 'AUTHZ_DENIED', 'RATE_LIMITED'):
            et_str = red(et)
        elif et == 'LOGOUT':
            et_str = dim(et)
        else:
            et_str = navy(et)
        user_str = r['username'] or dim('—')
        ip_str = r['ip_address'] or dim('—')
        print(f"  {dim(ts)}  {et_str:25}  {user_str:15}  {ip_str:15}  {r['detail'] or ''}")
    print()


# ----------------------------------------------------------------------------
# COMMAND: transition (token state machine)
# ----------------------------------------------------------------------------

def cmd_transition(args):
    conn = connect()
    try:
        with conn.cursor() as cur:
            # Set the audit-trigger context GUCs
            if args.actor:
                cur.execute("SELECT set_config('polaris.actor_agency_id', %s, true)",
                            (str(args.actor),))
            cur.execute("SELECT set_config('polaris.reason_code', %s, true)",
                        (args.reason,))

            if args.new_status == 'ACTIVE':
                cur.execute("""
                    UPDATE IdentityToken
                       SET status=%s, activated_date=CURRENT_TIMESTAMP
                     WHERE token_id=%s
                """, (args.new_status, args.token_id))
            else:
                cur.execute("""
                    UPDATE IdentityToken SET status=%s WHERE token_id=%s
                """, (args.new_status, args.token_id))

            if cur.rowcount == 0:
                sys.stderr.write(red(f"Token #{args.token_id} not found.\n"))
                sys.exit(1)
            conn.commit()
        print(green(f"✓ Transitioned token #{args.token_id} to {args.new_status}"))
    except psycopg2.Error as e:
        conn.rollback()
        sys.stderr.write(red(f"Transition rejected: {db_error_message(e)}\n"))
        sys.exit(3)
    finally:
        conn.close()


# ----------------------------------------------------------------------------
# Argument parser
# ----------------------------------------------------------------------------

def build_parser():
    p = argparse.ArgumentParser(
        prog='polaris',
        description='Command-line interface to the Polaris Identity Token System.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='Connection via env vars: POLARIS_DB_HOST, POLARIS_DB_NAME, POLARIS_DB_USER, POLARIS_DB_PASSWORD'
    )
    sub = p.add_subparsers(dest='command', metavar='COMMAND')

    # health
    sub.add_parser('health', help='Schema-wide statistics (mirrors Atlas health strip)')

    # list
    p_list = sub.add_parser('list', help='Browse principal entities')
    p_list.add_argument('entity', choices=['individuals', 'agencies', 'tokens',
                                            'algorithms', 'contexts', 'verifications'])
    p_list.add_argument('--status', help='(tokens) filter by status')
    p_list.add_argument('--context', help='(verifications) filter by context type')
    p_list.add_argument('--outcome', help='(verifications) filter by outcome')
    p_list.add_argument('--limit', type=int, default=50, help='(verifications) max rows')

    # inspect
    p_insp = sub.add_parser('inspect', help='Detailed token view with full history')
    p_insp.add_argument('token_id', type=int, help='Token ID to inspect')

    # query
    p_q = sub.add_parser('query', help='Run a read-only SELECT against the database')
    p_q.add_argument('sql', help='The SQL query (must start with SELECT or WITH)')

    # issue (UC-1)
    p_i = sub.add_parser('issue', help='UC-1: issue and activate a new token')
    p_i.add_argument('--legal-name',  required=True)
    p_i.add_argument('--dob',         required=True, help='YYYY-MM-DD')
    p_i.add_argument('--jurisdiction', required=True, help='e.g. US-PA')
    p_i.add_argument('--agency',      type=int, required=True, help='Issuing agency ID')
    p_i.add_argument('--algorithm',   type=int, required=True, help='Cryptographic algorithm ID')
    p_i.add_argument('--biometric',   default='IRIS',
                     choices=['NONE', 'FINGERPRINT', 'FACE', 'IRIS'])
    p_i.add_argument('--witness',     type=int, help='Witness agency ID (optional)')
    p_i.add_argument('--liveness',    default='MULTI_MODAL',
                     choices=['PASSIVE', 'ACTIVE_CHALLENGE', 'MULTI_MODAL'])
    p_i.add_argument('--token-value', required=True)
    p_i.add_argument('--serial',      required=True)
    p_i.add_argument('--hardware',    default='TitanQ-3')
    p_i.add_argument('--contexts',    required=True,
                     help='Comma-separated context IDs (e.g. 1,4,6)')

    # activate-reserve (UC-4)
    p_4 = sub.add_parser('activate-reserve', help='UC-4: activate a reserve after loss')
    p_4.add_argument('--lost-token',    type=int, required=True, help='ACTIVE token being lost')
    p_4.add_argument('--reserve-token', type=int, required=True, help='RESERVE token to promote')
    p_4.add_argument('--actor-agency',  type=int, required=True)
    p_4.add_argument('--reason',        default='LOST',
                     choices=['LOST', 'STOLEN', 'COMPROMISED', 'SUPERSEDED', 'ADMINISTRATIVE'])
    p_4.add_argument('--crl-url',       required=True, help='CRL distribution URL')

    # bind-device (UC-5)
    p_5 = sub.add_parser('bind-device', help='UC-5: bind a device to an active token')
    p_5.add_argument('--token',           type=int, required=True)
    p_5.add_argument('--device-type',     default='PHONE',
                     choices=['PHONE', 'TABLET', 'WATCH'])
    p_5.add_argument('--fingerprint',     required=True)
    p_5.add_argument('--binding-method',  default='SECURE_ENCLAVE',
                     choices=['SECURE_ENCLAVE', 'TITAN_SECURITY', 'TRUSTED_PLATFORM_MODULE'])
    p_5.add_argument('--validity-months', type=int, default=12)

    # warrant-audit (UC-7)
    p_7 = sub.add_parser('warrant-audit', help='UC-7: warrant-authorized verification history')
    p_7.add_argument('--individual',  type=int, required=True)
    p_7.add_argument('--window-start', help='YYYY-MM-DD HH:MM:SS')
    p_7.add_argument('--window-end',   help='YYYY-MM-DD HH:MM:SS')
    p_7.add_argument('--context',      help='Restrict to one context type')

    # migrate-algorithm (UC-6)
    p_6 = sub.add_parser('migrate-algorithm',
        help='UC-6: migrate a token to a new cryptographic algorithm')
    p_6.add_argument('--token',         type=int, required=True)
    p_6.add_argument('--new-algorithm', type=int, required=True,
        help='New CryptographicAlgorithm ID (must be non-deprecated)')
    sig = p_6.add_mutually_exclusive_group(required=True)
    sig.add_argument('--signature-hex',  help='New signature as raw hex string')
    sig.add_argument('--signature-file', help='Path to file containing signature bytes')
    p_6.add_argument('--deprecate-old', action='store_true',
        help='Also deprecate prior signatures (one-way operation)')

    # revoke (UC-8)
    p_8 = sub.add_parser('revoke', help='UC-8: revoke an ACTIVE token')
    p_8.add_argument('--token',              type=int, required=True)
    p_8.add_argument('--actor-agency',       type=int, required=True,
        help='Agency performing the revocation (may differ from issuer)')
    p_8.add_argument('--reason', required=True,
        choices=['POLICY_VIOLATION', 'FRAUD_DETECTED', 'COMPROMISE',
                 'SUPERSEDED', 'ADMINISTRATIVE', 'INDIVIDUAL_REQUEST'],
        help='Reason code (per UC-8 enum)')
    p_8.add_argument('--published-location', required=True,
        help='CRL or revocation-list URL where this revocation is published')
    p_8.add_argument('--cosigner-agency', type=int, default=None,
        help='Optional co-signer agency ID (R11-6 high-bar revocations)')

    # recovery-initiate (UC-9 phase 1)
    p_9i = sub.add_parser('recovery-initiate',
        help='UC-9 phase 1: open a catastrophic-loss recovery ceremony')
    p_9i.add_argument('--individual',        type=int, required=True,
        help='Individual ID claiming recovery (must have NO ACTIVE token)')
    p_9i.add_argument('--requesting-agency', type=int, required=True)
    p_9i.add_argument('--requesting-user',   type=int, required=True)
    p_9i.add_argument('--cooldown-hours',    type=int, default=48,
        help='Cooldown window before phase 2 may complete (default: 48)')

    # recovery-complete (UC-9 phase 2)
    p_9c = sub.add_parser('recovery-complete',
        help='UC-9 phase 2: approve or reject a pending recovery request')
    p_9c.add_argument('--recovery-id',   type=int, required=True)
    p_9c.add_argument('--deciding-user', type=int, required=True)
    p_9c.add_argument('--decision', required=True,
        choices=['APPROVED', 'REJECTED'])
    p_9c.add_argument('--reason', required=True,
        help='Free-text reason for the decision (audited)')
    p_9c.add_argument('--new-token-value',
        help='(APPROVED only) Token value for the newly-issued token')
    p_9c.add_argument('--new-serial',
        help='(APPROVED only) Serial for the newly-issued token')
    p_9c.add_argument('--algorithm', type=int,
        help='(APPROVED only) CryptographicAlgorithm ID')
    p_9c.add_argument('--biometric-binding',
        help='(APPROVED only) Biometric binding modality')
    p_9c.add_argument('--liveness-check',
        help='(APPROVED only) Liveness-check modality')
    p_9c.add_argument('--published-location',
        help='(APPROVED only) CRL/publish URL for the new token')

    # transition
    p_t = sub.add_parser('transition', help='Apply a state-machine transition to a token')
    p_t.add_argument('token_id', type=int)
    p_t.add_argument('new_status', choices=['ACTIVE', 'DORMANT', 'REVOKED', 'LOST', 'EXPIRED'])
    p_t.add_argument('--actor',  type=int, help='Actor agency ID for the audit row')
    p_t.add_argument('--reason', default='CLI_TRANSITION')

    # user-list
    sub.add_parser('user-list', help='List application users (web auth accounts)')

    # user-create
    p_uc = sub.add_parser('user-create', help='Create a new application user')
    p_uc.add_argument('username', help='Username (lowercase, [a-z0-9._-], 3-50 chars)')
    p_uc.add_argument('role', choices=['admin', 'operator', 'auditor'])
    p_uc.add_argument('--password',
                      help='Password (interactive prompt if omitted; using --password '
                           'puts the value in process listings — prefer interactive)')

    # user-passwd
    p_up = sub.add_parser('user-passwd', help="Change a user's password (also clears lockout)")
    p_up.add_argument('username')
    p_up.add_argument('--password', help='Skip interactive prompt (insecure for shared shells)')

    # user-deactivate
    p_ud = sub.add_parser('user-deactivate', help='Deactivate (soft-delete) a user account')
    p_ud.add_argument('username')

    # audit-log
    p_al = sub.add_parser('audit-log', help='Tail the authentication audit log')
    p_al.add_argument('--event-type',
                      choices=['LOGIN_SUCCESS', 'LOGIN_FAILED', 'LOGIN_LOCKED',
                               'LOGOUT', 'PASSWORD_CHANGED', 'ACCOUNT_CREATED',
                               'ACCOUNT_DEACTIVATED', 'CSRF_REJECTED',
                               'AUTH_REQUIRED', 'AUTHZ_DENIED', 'RATE_LIMITED',
                               # v8.97 WebAuthn lifecycle
                               'WEBAUTHN_REGISTERED', 'WEBAUTHN_ASSERTED',
                               'WEBAUTHN_ASSERTION_FAILED', 'WEBAUTHN_DEREGISTERED',
                               'EMERGENCY_PASSWORD_LOGIN_AUTHORIZED',
                               # v9.189 session/origin hardening
                               'NETWORK_POLICY_DENIED', 'SESSION_EVICTED',
                               'SESSION_EXPIRED', 'SESSION_REVOKED',
                               'WEBAUTHN_REGISTRATION_REFUSED'],
                      help='Filter by event type')
    p_al.add_argument('--username', help='Filter by username')
    p_al.add_argument('--since-minutes', type=int,
                      help='Only show events from the last N minutes')
    p_al.add_argument('--limit', type=int, default=50, help='Max rows (default 50)')

    return p


HANDLERS = {
    'health':           cmd_health,
    'list':             cmd_list,
    'inspect':          cmd_inspect,
    'query':            cmd_query,
    'issue':            cmd_issue,
    'activate-reserve': cmd_activate_reserve,
    'bind-device':      cmd_bind_device,
    'warrant-audit':    cmd_warrant_audit,
    'migrate-algorithm': cmd_migrate_algorithm,
    'revoke':           cmd_revoke,
    'recovery-initiate': cmd_recovery_initiate,
    'recovery-complete': cmd_recovery_complete,
    'transition':       cmd_transition,
    'user-list':        cmd_user_list,
    'user-create':      cmd_user_create,
    'user-passwd':      cmd_user_passwd,
    'user-deactivate':  cmd_user_deactivate,
    'audit-log':        cmd_audit_log,
}


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    if not args.command:
        parser.print_help()
        sys.exit(1)
    handler = HANDLERS[args.command]
    handler(args)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        sys.stderr.write("\nInterrupted.\n")
        sys.exit(130)
