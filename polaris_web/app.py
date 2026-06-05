# =============================================================================
# AI-context: ~3,450 line Flask app. Routes are GROUPED by entity — search
#   for '# ====.*=====' to find the right section before adding routes.
# Read before editing:
#     ../DEVNOTES/known-gotchas.md          (CSP, Jinja {{}} in HTML comments)
#     ../docs/CONVENTIONS.md                (route + template conventions)
# =============================================================================

"""
============================================================================
POLARIS — IDENTITY TOKEN SYSTEM
Web Interface (Flask backend)

A web interface to the Polaris identity-token database. Implements query,
add, update, and delete operations across the schema's principal entities,
plus 13 use-case stored procedures + functions:
  - UC-1 issue_and_activate (function)
  - UC-4 activate_reserve (function)
  - UC-5 bind_device (function)
  - UC-7 warrant_audit (function)
  - UC-6 migrate_algorithm (procedure, v8.18 R11-1 multi-sig)
  - UC-8 revoke_token (procedure, v8.15 R11-6 issuer-discretion)
  - UC-9 initiate_recovery + complete_recovery (procedures, v8.17 R11-2)
  - UC-10 attest_trust + revoke_attestation (procedures, v8.22 R11-3 federation)
  - UC-11 close_epoch (procedure, v8.23 R10-1 ZK-SNARK)
  - UC-12 record_duress (procedure, v8.24 R11-5 duress codes)
  - close_anchor_batch (procedure, v8.21 R10-2 Merkle anchoring)

Design notes:
- Server-side rendering with Jinja2 templates. No SPA complexity.
- All database operations go through psycopg2; parameterized queries
  prevent SQL injection (NEVER use f-strings or string concat in queries).
- Schema-level constraints (CHECK, FK, partial unique index, state-machine
  trigger, append-only triggers) are surfaced as user-readable error
  messages on the result page rather than dumping psycopg2 stack traces.
- The append-only invariant on TokenLifecycleEvent and VerificationEvent is
  respected: the UI offers ADD-only on those tables, no UPDATE/DELETE.

Security controls (see security.py for implementation, docs/operator/SECURITY.md for the
audit findings + patches):
- Authentication: username + scrypt-hashed password, session-backed
- Authorization: three roles (admin / operator / auditor), enforced via
  @require_role decorators
- CSRF protection: HMAC-signed token validated on all POSTs
- Account lockout: 5 failures in 10 min → 15 min lockout
- Rate limiting: token-bucket per IP on login + state-changing routes
- Security headers: CSP, X-Frame-Options, Referrer-Policy, HSTS (prod)
- Body size limit: 1 MiB
- Audit logging: every login/logout/failure/CSRF rejection/authz denial

Run: python3 app.py
Test: python3 test_app.py
============================================================================
"""

import os
import sys
import time
import shutil
import pathlib
import subprocess
from datetime import datetime, timedelta, timezone

from flask import (
    Flask, render_template, request, redirect, url_for,
    flash, abort, session, g, jsonify, Response, make_response
)
import psycopg2
from psycopg2.extras import RealDictCursor, Json
from werkzeug.security import check_password_hash

import security
import anchoring
import zk
import webauthn_auth
import observability  # v9.31 freeze condition 6 — operator-readable metrics surface
import pqc_signing    # v9.58 — issuance signature comes from the signing module

# v8.93 — Prometheus-compatible /metrics endpoint. The dependency is
# optional at runtime: if prometheus_client is unavailable, /metrics
# returns 503 with a stub message and the rest of the app still serves.
# The production Dockerfile installs it; ad-hoc dev environments may
# not. Graceful failure preserved.
try:
    import prometheus_client
    from prometheus_client import (
        Counter as _PromCounter,
        Histogram as _PromHistogram,
        Gauge as _PromGauge,
        CollectorRegistry as _PromRegistry,
        generate_latest as _prom_generate_latest,
        CONTENT_TYPE_LATEST as _PROM_CONTENT_TYPE,
    )
    _PROM_AVAILABLE = True
    # Use a dedicated registry so we don't collide with anything else
    # that might import prometheus_client in the same process.
    _METRICS_REGISTRY = _PromRegistry()
    _METRICS_REQUESTS = _PromCounter(
        'polaris_requests_total',
        'Total HTTP requests by route + method + status',
        labelnames=('route', 'method', 'status'),
        registry=_METRICS_REGISTRY,
    )
    _METRICS_REQUEST_LATENCY = _PromHistogram(
        'polaris_request_latency_seconds',
        'Request latency in seconds, by route',
        labelnames=('route',),
        registry=_METRICS_REGISTRY,
    )
    _METRICS_VERIFICATIONS = _PromCounter(
        'polaris_verifications_total',
        'VerificationEvent rows by disclosure_level',
        labelnames=('disclosure_level',),
        registry=_METRICS_REGISTRY,
    )
    _METRICS_DB_LATENCY = _PromHistogram(
        'polaris_db_query_latency_seconds',
        'Database round-trip from /api/health probe',
        registry=_METRICS_REGISTRY,
    )
    _METRICS_APP_INFO = _PromGauge(
        'polaris_app_info',
        'Polaris app metadata (always 1; labels carry the data)',
        labelnames=('version',),
        registry=_METRICS_REGISTRY,
    )
except ImportError:
    _PROM_AVAILABLE = False


# Polaris version — single source of truth for the running build.
# Read by /api/health (G29); incremented per ship in CHANGELOG.md.
# v9.06 / Wave 2 / C5 — single canonical source. Was a string literal
# here; promoted to polaris_web/__version__.py so future surfaces
# (CLI, Dockerfile labels, OpenAPI docs) import from one place.
try:
    from polaris_web.__version__ import POLARIS_VERSION  # type: ignore
except Exception:  # noqa: BLE001 — graceful (allows app.py to load
                   # standalone when sys.path is at polaris_web/)
    from __version__ import POLARIS_VERSION  # type: ignore

# Module-load epoch (used by /api/health uptime). Set once at import time.
_APP_STARTED_AT = time.time()


def _read_secret_file(env_name, fallback_env_name=None, default=None):
    """Read a secret from a file path, with env-var fallback (G28).

    Production stack (docker-compose.prod.yml) sets ``POLARIS_X_FILE`` to a
    path under ``/run/secrets/`` mounted from ``./secrets/`` on the host.
    Dev stack sets ``POLARIS_X`` directly for ergonomics. This helper
    returns the file contents if ``*_FILE`` is set and readable; otherwise
    falls back to ``*`` (env var) or ``default``.
    """
    file_path = os.environ.get(env_name)
    if file_path:
        try:
            with open(file_path, 'r') as fh:
                return fh.read().strip()
        except OSError:
            sys.stderr.write(f"WARN: {env_name}={file_path} unreadable; "
                             "falling back to env var\n")
    if fallback_env_name:
        v = os.environ.get(fallback_env_name)
        if v is not None:
            return v
    return default


app = Flask(__name__)


# ----------------------------------------------------------------------------
# Application configuration — secret key + session/cookie hardening
# ----------------------------------------------------------------------------

app.secret_key = _read_secret_file(
    'POLARIS_SECRET_KEY_FILE',
    fallback_env_name='POLARIS_SECRET_KEY',
    default='dev-key-change-in-production',
)

# Session lifetime: 8 hours of inactivity then re-login required.
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=security.SESSION_LIFETIME_HOURS)

# Cookie hardening (CWE-614, CWE-1004). HTTPS-only is opt-in for dev but
# MANDATORY in production: forgetting POLARIS_COOKIE_SECURE there would let a
# single downgraded request leak polaris_session over plaintext. _PRODUCTION
# removes that foot-gun rather than trusting the operator to set the flag,
# mirroring the secret-key guard below.
_PRODUCTION = os.environ.get('POLARIS_ENV', '').lower() == 'production'
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_SECURE']   = _PRODUCTION or (
    os.environ.get('POLARIS_COOKIE_SECURE', '').lower() in ('1', 'true', 'yes')
)
app.config['SESSION_COOKIE_NAME']     = 'polaris_session'

# Hard limit on request body size (CWE-770). The SQL console caps at 5KB
# separately; this is the outer limit for everything else.
app.config['MAX_CONTENT_LENGTH'] = security.MAX_REQUEST_BODY_BYTES

# Refuse to start in production with the default secret key (_PRODUCTION is
# computed above, with the cookie hardening).
if app.secret_key in ('dev-key-change-in-production', 'dev-secret-rotate-in-production'):
    if _PRODUCTION:
        sys.stderr.write(
            "\n  FATAL: POLARIS_SECRET_KEY is at its development default but\n"
            "         POLARIS_ENV=production. Refusing to start.\n"
            "         Generate a key:  python3 -c 'import secrets; print(secrets.token_hex(32))'\n\n"
        )
        sys.exit(2)
    sys.stderr.write(
        "\n  ⚠  POLARIS_SECRET_KEY is unset or using a known default value.\n"
        "      Generate a real key:  python3 -c 'import secrets; print(secrets.token_hex(32))'\n"
        "      and set POLARIS_SECRET_KEY before deploying to production.\n\n"
    )


# ----------------------------------------------------------------------------
# Database connection
# ----------------------------------------------------------------------------

DB_CONFIG = {
    'host':     os.environ.get('POLARIS_DB_HOST',     'localhost'),
    'port':     int(os.environ.get('POLARIS_DB_PORT', '5432')),
    'database': os.environ.get('POLARIS_DB_NAME',     'polaris_test'),
    'user':     os.environ.get('POLARIS_DB_USER',     'polaris_app'),
    # G28: prefer POLARIS_DB_PASSWORD_FILE (file-mounted secret) over env var
    'password': _read_secret_file(
        'POLARIS_DB_PASSWORD_FILE',
        fallback_env_name='POLARIS_DB_PASSWORD',
        default='polaris_dev_password',
    ),
}


def get_db():
    """
    Open a fresh connection per request. For production we would use a
    connection pool (e.g. psycopg2.pool.SimpleConnectionPool) but for this
    interface a per-request connection is simpler and adequate.
    """
    return psycopg2.connect(cursor_factory=RealDictCursor, **DB_CONFIG)


def query(sql, params=None, fetch='all'):
    """
    Run a parameterized query and return results.
    fetch: 'all' returns list of dicts; 'one' returns single dict or None;
           'none' returns rowcount (for INSERT/UPDATE/DELETE).
    """
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params or ())
            if fetch == 'all':
                return cur.fetchall()
            elif fetch == 'one':
                return cur.fetchone()
            elif fetch == 'none':
                conn.commit()
                return cur.rowcount
            elif fetch == 'returning':
                conn.commit()
                return cur.fetchone()
    finally:
        conn.close()


def db_error_to_message(e):
    """
    Convert a psycopg2 error into a user-readable message. We surface
    informative messages for known constraints (the schema's constraint
    names are designed to be readable), but for UNKNOWN errors we return
    a generic message — leaking internal column names, table names, or
    SQL fragments in a 500 response is CWE-209 (Information Exposure
    Through Error Message). The full error is logged server-side via
    sys.stderr for operator diagnostics.
    """
    msg = str(e).strip()

    # Known, intentional, user-friendly mappings -----------------------------
    if 'duplicate key value' in msg and 'uq_one_active_per_person' in msg:
        return "Cannot create a second ACTIVE token for this individual. Each individual may hold only one active token at a time."
    if 'violates check constraint' in msg and 'chk_disclosure_token_consistency' in msg:
        return "Disclosure level is inconsistent with token reference. ZERO_KNOWLEDGE events must have no token; FULL events must reference a token."
    if 'Illegal token state transition' in msg:
        # Pull out just the trigger's message (no SQL details)
        for line in msg.split('\n'):
            if 'Illegal token state transition' in line:
                return line.replace('ERROR:', '').strip()
    if 'is forbidden' in msg and 'append-only' in msg:
        return "This table is append-only (audit invariant). UPDATE and DELETE are not permitted."
    if 'violates foreign key constraint' in msg:
        return "Referential integrity violation: the referenced record does not exist (or is being referenced by another record)."
    if 'duplicate key value' in msg:
        # Generic uniqueness violation without leaking the index name
        return "A record with that unique value already exists."
    if 'value too long for type' in msg:
        return "One of the input values exceeds the maximum allowed length."
    if 'invalid input syntax' in msg:
        return "Input value has an invalid format for the expected type."
    if 'not-null constraint' in msg:
        return "A required field was left blank."

    # CHECK constraint with a known schema-level name → expose the name
    # because the schema authors deliberately made these readable.
    if 'violates check constraint' in msg:
        # e.g. "violates check constraint chk_disclosure_token_consistency"
        import re
        m = re.search(r'check constraint "(chk_[a-zA-Z0-9_]+)"', msg)
        if m:
            return f"Constraint violation: {m.group(1)}"
        return "Constraint violation."

    # Trigger-raised exceptions: these come from our schema and are designed
    # to be user-readable (no internal column/SQL leakage).
    first_line = msg.split('\n')[0].replace('ERROR:', '').strip()
    if first_line.startswith(('Cannot ', 'Agency ', 'Token ', 'Reserve ',
                              'Lost ', 'Verification ', 'No ', 'The ',
                              'Active ', 'Permission ')):
        return first_line

    # Unknown error path — DON'T leak internal details. Log server-side.
    import sys
    sys.stderr.write(f"[db_error] Unhandled: {msg[:500]}\n")
    return "An internal database error occurred. The administrator has been notified."


# ============================================================================
# SECURITY WIRING
# ============================================================================
# Wire security.py into the Flask app: register hooks, expose helpers to
# templates, register the login/logout/admin routes. See security.py for
# the actual implementations and docs/operator/SECURITY.md for the audit findings.

# Make get_db reachable from security.py via app.config (decorators need it
# but can't import from app.py without circular imports).
app.config['GET_DB'] = get_db


@app.before_request
def _security_before_request():
    """
    Runs before every request. Enforces:
      - Body size limit (CWE-770)
      - Per-IP rate limit on login + state-changing routes (CWE-307, CWE-770)
    """
    security.enforce_body_size_limit()

    # Rate-limit login attempts (per IP)
    if request.path == '/login' and request.method == 'POST':
        if not security.rate_limiter.allow(
            f"login:{security.client_ip()}",
            security.RATE_LIMIT_LOGIN_MAX,
            security.RATE_LIMIT_LOGIN_WINDOW
        ):
            security._audit(get_db, 'RATE_LIMITED',
                            detail=f"login from {security.client_ip()}")
            abort(429)

    # Rate-limit all state-changing requests (per IP) — but exempt the
    # heartbeat / quit endpoints, which fire every 10s by design and are
    # not user-initiated state changes.
    if request.method in ('POST', 'PUT', 'PATCH', 'DELETE') \
            and not request.path.startswith('/api/heartbeat') \
            and not request.path.startswith('/api/quit'):
        if not security.rate_limiter.allow(
            f"write:{security.client_ip()}",
            security.RATE_LIMIT_WRITE_MAX,
            security.RATE_LIMIT_WRITE_WINDOW
        ):
            security._audit(get_db, 'RATE_LIMITED',
                            username=session.get('username'),
                            user_id=session.get('user_id'),
                            detail=f"{request.method} {request.path}")
            abort(429)


@app.after_request
def _security_after_request(response):
    """Apply security headers (CSP, HSTS, etc.) to every response."""
    return security.apply_security_headers(response)


# v8.93 — Prometheus metrics request-tagging hooks. Tag every served
# request with the route + method + status code so /metrics can report
# `polaris_requests_total{route="/api/health",method="GET",status="200"}`.
# Also record per-route latency. Both are no-op if prometheus_client
# is unavailable.
@app.before_request
def _metrics_before_request():
    if _PROM_AVAILABLE:
        g._metrics_t0 = _time.time()


@app.after_request
def _metrics_after_request(response):
    if _PROM_AVAILABLE:
        # Label only by the matched endpoint (a bounded set, one per registered
        # route). NEVER fall back to request.path: on a 404 request.endpoint is
        # None and request.path is the raw, attacker-controlled URL, so every
        # GET to a fresh path would mint a new Prometheus label series and grow
        # the in-process registry without bound (memory-exhaustion DoS, CWE-400).
        route = request.endpoint or 'unmatched'
        method = request.method or 'GET'
        status = str(response.status_code)
        try:
            _METRICS_REQUESTS.labels(route=route, method=method, status=status).inc()
            t0 = getattr(g, '_metrics_t0', None)
            if t0 is not None:
                _METRICS_REQUEST_LATENCY.labels(route=route).observe(_time.time() - t0)
        except Exception:
            # Metrics MUST never break the response path. Swallow.
            pass
    # v9.31 freeze condition 6: operator-readable observability (separate
    # from Prometheus; no-backend by design). Counts every served request
    # and tags 5xx as errors. No-op if observability module fails to load.
    try:
        observability.record_request()
        if response.status_code >= 500:
            observability.record_error()
    except Exception:
        pass
    return response


@app.context_processor
def _inject_security_context():
    """Make csrf_token() and current_user available in templates."""
    return security.template_context_processor()


# ----------------------------------------------------------------------------
# Liveness: browser-presence beacon for the macOS launcher
# ----------------------------------------------------------------------------
# The launcher script can run in foreground "watch" mode. While the browser
# tab is open, JavaScript fires POST /api/heartbeat every ~10s. On tab close,
# it fires a sendBeacon to /api/quit. The launcher polls this state and tears
# the stack down when the user closes the tab.
#
# State lives in /tmp/polaris-state, mounted into the container via
# docker-compose so the host launcher can read the same files.

POLARIS_STATE_DIR = os.environ.get('POLARIS_STATE_DIR', '/tmp/polaris-state')
HEARTBEAT_FILE = os.path.join(POLARIS_STATE_DIR, 'heartbeat')
QUIT_FILE      = os.path.join(POLARIS_STATE_DIR, 'quit')


def _ensure_state_dir():
    try:
        os.makedirs(POLARIS_STATE_DIR, exist_ok=True)
        os.chmod(POLARIS_STATE_DIR, 0o777)
    except (OSError, PermissionError):
        pass


@app.route('/api/heartbeat', methods=['POST'])
@security.reject_cross_site
def api_heartbeat():
    """Browser is still alive; refresh the heartbeat timestamp."""
    _ensure_state_dir()
    try:
        pathlib.Path(HEARTBEAT_FILE).touch()
    except (OSError, PermissionError):
        pass
    return ('', 204)


@app.route('/api/quit', methods=['POST'])
@security.reject_cross_site
def api_quit():
    """Browser tab is closing; explicit shutdown signal for the launcher."""
    _ensure_state_dir()
    try:
        pathlib.Path(QUIT_FILE).touch()
    except (OSError, PermissionError):
        pass
    return ('', 204)


@app.route('/api/since-heartbeat')
def api_since_heartbeat():
    """Returns seconds since last heartbeat. The launcher polls this when
    the host filesystem mount isn't available (e.g. native mode where the
    state dir is shared directly). Anyone can call this; no auth."""
    if not os.path.exists(HEARTBEAT_FILE):
        return {'since_s': None, 'quit_requested': os.path.exists(QUIT_FILE)}, 200
    age = time.time() - os.path.getmtime(HEARTBEAT_FILE)
    return {'since_s': age, 'quit_requested': os.path.exists(QUIT_FILE)}, 200


# ----------------------------------------------------------------------------
# Login / logout / unauthorized handler
# ----------------------------------------------------------------------------

@app.route('/login', methods=['GET', 'POST'])
def login():
    """
    Login page. POST validates credentials via security.authenticate(), which
    handles lockout bookkeeping and audit logging internally.

    v8.97 / Position B: after password succeeds, the WebAuthn-MFA gate
    decides whether to complete the login, redirect to the WebAuthn
    assertion step, or refuse (deadline passed without enrollment).
    """
    if request.method == 'POST':
        # Login form is exempt from full CSRF (no session yet for unauth users),
        # but we still validate that the submission is form-encoded and small.
        username = (request.form.get('username') or '').strip().lower()
        password =  request.form.get('password') or ''

        user, error = security.authenticate(get_db, username, password)
        if user is None:
            flash(error, 'error')
            return render_template('login.html', username=username), 401

        # WebAuthn-MFA gate (v8.97 / Position B)
        conn = get_db()
        try:
            status = webauthn_auth.webauthn_status_for_user(
                conn, user['user_id'], user['role'])
            deadline_days = webauthn_auth.days_until_webauthn_deadline(
                conn, user['user_id'])
        finally:
            conn.close()

        if status == 'mfa_overdue':
            # Refuse login; password was correct but the WebAuthn
            # enrollment deadline has passed and no credential is on file.
            security._audit(get_db, 'LOGIN_FAILED', username=username,
                user_id=user['user_id'],
                detail='WebAuthn enrollment deadline passed; no credential enrolled')
            flash(
                'WebAuthn enrollment deadline has passed. Contact a '
                'second admin to run scripts/polaris-recover-admin.sh, '
                'or use a printed recovery code from polaris-generate-'
                'recovery-code.sh to authorize emergency password login.',
                'error')
            return render_template('login.html', username=username), 401

        if status == 'mfa_required':
            # Partial-auth: stage the user but DO NOT mark session as
            # logged_in until the WebAuthn assertion succeeds. The
            # /auth/webauthn/assert/* routes consume this state.
            session.clear()
            session['webauthn_pending_user'] = user
            # Preserve ?next= across the assertion redirect
            next_url = request.args.get('next', '')
            if security.is_safe_next_url(next_url):
                session['webauthn_pending_next'] = next_url
            return redirect(url_for('webauthn_assert_page'))

        # status is 'not_required' or 'grace_period' — complete the login
        security.login_user(user)

        if status == 'grace_period' and deadline_days is not None:
            flash(
                f'WebAuthn enrollment required within {deadline_days} day(s). '
                f'Enroll at /settings/webauthn before the deadline to avoid '
                f'being locked out.',
                'warning')

        # Honor ?next= but only if it's a same-origin path (CWE-601 open redirect).
        next_url = request.args.get('next', '')
        if security.is_safe_next_url(next_url):
            return redirect(next_url)
        return redirect(url_for('dashboard'))

    if session.get('logged_in'):
        return redirect(url_for('dashboard'))
    return render_template('login.html', username='')


@app.route('/logout', methods=['POST'])
@security.csrf_protect
def logout():
    """Logout requires POST + CSRF — prevents drive-by logout via image tags."""
    security.logout_user(get_db)
    flash("You have been logged out.", 'success')
    return redirect(url_for('login'))


# ----------------------------------------------------------------------------
# WebAuthn-MFA routes (v8.97 / Position B of webauthn-operator-auth Sanctum)
# ----------------------------------------------------------------------------

@app.route('/auth/webauthn/assert', methods=['GET'])
def webauthn_assert_page():
    """Render the WebAuthn assertion page for users in partial-auth state
    (password verified but assertion still pending)."""
    pending = session.get('webauthn_pending_user')
    if pending is None:
        return redirect(url_for('login'))
    return render_template('webauthn_assert.html',
                           username=pending.get('username', ''))


@app.route('/auth/webauthn/assert/begin', methods=['POST'])
def webauthn_assert_begin():
    """Issue a WebAuthn assertion challenge for the partial-auth user."""
    pending = session.get('webauthn_pending_user')
    if pending is None:
        return jsonify(error='no pending authentication'), 400

    conn = get_db()
    try:
        allowed = webauthn_auth.existing_credential_ids_for_user(
            conn, pending['user_id'])
    finally:
        conn.close()

    if not allowed:
        return jsonify(error='no enrolled credentials for this user'), 400

    result = webauthn_auth.build_authentication_options(allowed)
    session['webauthn_assert_challenge'] = result['challenge_b64url']
    return Response(result['options_json'], mimetype='application/json')


@app.route('/auth/webauthn/assert/finish', methods=['POST'])
def webauthn_assert_finish():
    """Verify the assertion + complete the login."""
    pending = session.get('webauthn_pending_user')
    challenge = session.get('webauthn_assert_challenge')
    if pending is None or challenge is None:
        return jsonify(error='no pending authentication'), 400
    # One-shot challenge: clear immediately so a replay can't re-use it
    session.pop('webauthn_assert_challenge', None)

    body = request.get_json(silent=True) or {}
    cred_id = body.get('id') or body.get('rawId')
    if not cred_id:
        return jsonify(error='missing credential id'), 400

    conn = get_db()
    try:
        stored = webauthn_auth.fetch_credential(conn, cred_id)
        if stored is None or stored['user_id'] != pending['user_id']:
            security._audit(get_db, 'WEBAUTHN_ASSERTION_FAILED',
                username=pending.get('username'),
                user_id=pending['user_id'],
                detail='credential not found or wrong user')
            try:
                observability.record_auth_failure(
                    kind='webauthn', username=pending.get('username', ''))
            except Exception:
                pass
            return jsonify(error='invalid credential'), 401

        try:
            v = webauthn_auth.verify_authentication(
                body, challenge,
                stored['public_key'], stored['sign_count'])
        except Exception as e:
            security._audit(get_db, 'WEBAUTHN_ASSERTION_FAILED',
                username=pending.get('username'),
                user_id=pending['user_id'],
                detail=str(e)[:480])
            try:
                observability.record_auth_failure(
                    kind='webauthn', username=pending.get('username', ''))
            except Exception:
                pass
            return jsonify(error='invalid assertion'), 401

        webauthn_auth.update_credential_after_use(
            conn, cred_id, v['new_sign_count'])
        conn.commit()
    finally:
        conn.close()

    security._audit(get_db, 'WEBAUTHN_ASSERTED',
        username=pending.get('username'),
        user_id=pending['user_id'],
        detail=f'cred_id={cred_id[:16]}')

    # Promote partial-auth to full session
    next_url = session.get('webauthn_pending_next')
    security.login_user(pending)

    # Decide where to send the browser. Same ?next= rules as /login.
    if security.is_safe_next_url(next_url):
        target = next_url
    else:
        target = url_for('dashboard')
    return jsonify(ok=True, redirect=target)


@app.route('/settings/webauthn', methods=['GET'])
@security.login_required
def webauthn_settings():
    """Per-user enrollment management page."""
    user = security.current_user()
    conn = get_db()
    try:
        creds = webauthn_auth.list_credentials_for_user(conn, user['user_id'])
        deadline_days = webauthn_auth.days_until_webauthn_deadline(
            conn, user['user_id'])
    finally:
        conn.close()
    return render_template('webauthn_settings.html',
                           credentials=creds,
                           deadline_days=deadline_days,
                           current_role=user['role'])


@app.route('/auth/webauthn/register/begin', methods=['POST'])
@security.login_required
@security.csrf_protect
def webauthn_register_begin():
    """Issue a registration challenge for the logged-in user."""
    user = security.current_user()
    conn = get_db()
    try:
        existing = webauthn_auth.existing_credential_ids_for_user(
            conn, user['user_id'])
    finally:
        conn.close()
    result = webauthn_auth.build_registration_options(
        user['user_id'], user['username'], existing)
    session['webauthn_register_challenge'] = result['challenge_b64url']
    return Response(result['options_json'], mimetype='application/json')


@app.route('/auth/webauthn/register/finish', methods=['POST'])
@security.login_required
@security.csrf_protect
def webauthn_register_finish():
    """Verify the registration response + persist the credential."""
    user = security.current_user()
    challenge = session.get('webauthn_register_challenge')
    if not challenge:
        return jsonify(error='no pending registration'), 400
    session.pop('webauthn_register_challenge', None)

    body = request.get_json(silent=True) or {}
    device_label = (body.get('device_label') or '').strip() or 'unnamed'

    try:
        cred = webauthn_auth.verify_registration(body, challenge)
    except Exception as e:
        return jsonify(error=f'registration verification failed: {e}'), 400

    conn = get_db()
    try:
        webauthn_auth.insert_credential(
            conn, user['user_id'], cred, device_label)
        conn.commit()
    finally:
        conn.close()

    security._audit(get_db, 'WEBAUTHN_REGISTERED',
        username=user['username'], user_id=user['user_id'],
        detail=f'label={device_label[:32]} cred_id={cred["credential_id"][:16]}')

    return jsonify(ok=True, credential_id=cred['credential_id'])


@app.route('/auth/webauthn/credentials/<credential_id>/delete',
           methods=['POST'])
@security.login_required
@security.csrf_protect
def webauthn_delete_credential(credential_id):
    """Remove an enrolled credential. Only the owner can delete their own."""
    user = security.current_user()
    conn = get_db()
    try:
        deleted = webauthn_auth.delete_credential(
            conn, user['user_id'], credential_id)
        conn.commit()
    finally:
        conn.close()

    if deleted:
        security._audit(get_db, 'WEBAUTHN_DEREGISTERED',
            username=user['username'], user_id=user['user_id'],
            detail=f'cred_id={credential_id[:16]}')
        flash('WebAuthn credential removed.', 'success')
    else:
        flash('Credential not found.', 'error')
    return redirect(url_for('webauthn_settings'))


@app.errorhandler(403)
def forbidden(e):
    return render_template('error.html',
                           code=403,
                           message='Forbidden — your account does not have '
                                   'permission for this action.'), 403


@app.errorhandler(413)
def request_entity_too_large(e):
    return render_template('error.html',
                           code=413,
                           message='Request body too large. The maximum is '
                                   f'{security.MAX_REQUEST_BODY_BYTES // 1024} KB.'), 413


@app.errorhandler(429)
def too_many_requests(e):
    return render_template('error.html',
                           code=429,
                           message='Too many requests. Please slow down and '
                                   'try again in a minute.'), 429


# ============================================================================
# PUBLIC ROUTES (Arc B Phase 1 / ARCH-003 — UX polish, v8.79)
# ============================================================================

@app.route('/')
def home():
    """Public landing page.

    Anonymous visitors see a one-screen explanation of what Polaris
    is, the key constraints (C1, C2, C3, C10), the substrate, the
    cognitive layer, and how to deploy. Logged-in users are
    redirected to /dashboard.

    First-impression real-estate. No login_required: this is the
    page that explains why Polaris exists.
    """
    if security.current_user():
        return redirect(url_for('dashboard'))
    return render_template(
        'landing.html',
        polaris_version=POLARIS_VERSION,
    )


@app.route('/demo')
def demo():
    """Public synthetic walkthrough.

    Four-step token lifecycle (ISSUE → ACTIVATE → VERIFY → REVOKE)
    showing the procedure called, the effect, and the constraint
    enforced at each step. No real holder data; no auth required.
    """
    return render_template('demo.html')


# ============================================================================
# DASHBOARD
# ============================================================================

@app.route('/dashboard')
@security.login_required
def dashboard():
    """Landing page: schema-wide statistics, ActiveTokens view, and the analytical
    panels that explain how the system is configured (Authorization Matrix,
    PQ Migration, Disclosure Posture, Verification by Context, Lineage,
    Recent Audit Events). The Atlas page is reserved for live operational
    investigation; aggregate analytics live here."""
    stats = {}
    tables = ['Individual', 'Agency', 'CryptographicAlgorithm', 'VerificationContext',
              'IdentityToken', 'TokenLifecycleEvent', 'VerificationEvent',
              'DeviceBinding', 'BlockchainAnchor', 'RevocationList',
              'AgencyAlgorithmAuth', 'TokenPermission']
    for tbl in tables:
        stats[tbl] = query(f'SELECT COUNT(*) AS n FROM {tbl}', fetch='one')['n']

    # Snapshot, not an enumeration: cap the active-token table so the dashboard
    # (the default post-login landing page, hit on every login) does not
    # materialize every active token on every load. At national scale the
    # unbounded fetch would be a DoS — the exact hazard individuals_list
    # documents and paginates against. Show the 200 most recent active tokens.
    active_tokens = query(
        'SELECT * FROM ActiveTokens ORDER BY token_id DESC LIMIT 200')
    status_breakdown = query("""
        SELECT status, COUNT(*) AS n
        FROM IdentityToken
        GROUP BY status
        ORDER BY n DESC
    """)

    analytics = _polaris_analytics()
    v2_substrate = _v2_substrate_tiles()

    return render_template('dashboard.html',
                           stats=stats,
                           active_tokens=active_tokens,
                           status_breakdown=status_breakdown,
                           total=sum(stats.values()),
                           v2_substrate=v2_substrate,
                           **analytics)


def _v2_substrate_tiles():
    """v8.28 — dashboard tiles for the v2 substrate primitives.

    Returns counts + latest-event timestamps for the four v2 substrate
    audit-of-record tables: AnchorBatch, TokenStateEpoch,
    AgencyTrustAttestation, DuressEvent. Duress is exposed in the dict
    unconditionally; the template gates the tile to admin/auditor via
    `current_user.role` (R6 anti-revealing posture preserved)."""
    anchor = query("""
        SELECT COUNT(*) AS n, MAX(created_at) AS latest
          FROM AnchorBatch
    """, fetch='one')
    epoch = query("""
        SELECT COUNT(*) AS n, MAX(closed_at) AS latest
          FROM TokenStateEpoch
    """, fetch='one')
    attest = query("""
        SELECT COUNT(*) AS total,
               SUM(CASE WHEN revocation_date IS NULL
                         AND valid_until >= CURRENT_DATE THEN 1 ELSE 0 END) AS active,
               MAX(attested_date) AS latest
          FROM AgencyTrustAttestation
    """, fetch='one')
    duress = query("""
        SELECT COUNT(*) AS n, MAX(event_timestamp) AS latest
          FROM DuressEvent
    """, fetch='one')
    sig = query("""
        SELECT COUNT(*) AS total,
               SUM(CASE WHEN deprecation_date IS NULL THEN 1 ELSE 0 END) AS active
          FROM TokenSignature
    """, fetch='one')
    return dict(
        anchor_batch_count=anchor['n'] or 0,
        anchor_batch_latest=anchor['latest'],
        epoch_count=epoch['n'] or 0,
        epoch_latest=epoch['latest'],
        attestation_total=attest['total'] or 0,
        attestation_active=attest['active'] or 0,
        attestation_latest=attest['latest'],
        duress_count=duress['n'] or 0,
        duress_latest=duress['latest'],
        signature_total=sig['total'] or 0,
        signature_active=sig['active'] or 0,
    )


# ============================================================================
# ATLAS — Operational investigation surface (Gotham-style)
# ============================================================================

def _polaris_analytics():
    """Shared analytical aggregates: Authorization Matrix, PQ migration,
    verification activity by context, disclosure posture, succession lineage,
    recent audit events. Used by the dashboard. Atlas does NOT consume these,
    Atlas only needs operational state for the globe and HUD."""
    agencies = query("SELECT agency_id, name, agency_type FROM Agency ORDER BY agency_id")
    algorithms = query("""
        SELECT algorithm_id, name, quantum_resistant, deprecation_date
        FROM CryptographicAlgorithm ORDER BY algorithm_id
    """)
    auth_grants = query("""
        SELECT agency_id, algorithm_id, authorization_type
        FROM AgencyAlgorithmAuth
    """)
    auth_matrix = {}
    for g in auth_grants:
        auth_matrix[(g['agency_id'], g['algorithm_id'])] = g['authorization_type']

    # R11-1 / M2-6: PQ breakdown now counts tokens with ≥ 1 ACTIVE
    # (non-deprecated) signature under each algorithm, via the M:N
    # TokenSignature relation. A token mid-migration with both ML-DSA-65
    # and ML-DSA-87 active signatures contributes to BOTH algorithm
    # totals — this is the correct accounting for the dashboard:
    # "how many tokens are still verifiable under algorithm X?"
    pq_breakdown = query("""
        SELECT alg.name, alg.quantum_resistant, COUNT(DISTINCT t.token_id) AS n
        FROM CryptographicAlgorithm alg
        LEFT JOIN TokenSignature s ON alg.algorithm_id = s.algorithm_id
                                  AND s.deprecation_date IS NULL
        LEFT JOIN IdentityToken t ON s.token_id = t.token_id
                                 AND t.status = 'ACTIVE'
        GROUP BY alg.algorithm_id, alg.name, alg.quantum_resistant
        ORDER BY alg.algorithm_id
    """)
    pq_active_total = sum(r['n'] for r in pq_breakdown if r['quantum_resistant'])
    classical_active_total = sum(r['n'] for r in pq_breakdown if not r['quantum_resistant'])

    context_activity = query("""
        SELECT vc.context_type, COUNT(ve.event_id) AS vol,
               SUM(CASE WHEN ve.outcome='SUCCESS'  THEN 1 ELSE 0 END) AS succ,
               SUM(CASE WHEN ve.outcome='FAILURE'  THEN 1 ELSE 0 END) AS fail
        FROM VerificationContext vc
        LEFT JOIN VerificationEvent ve ON vc.context_id = ve.context_id
        GROUP BY vc.context_type
        ORDER BY vol DESC, vc.context_type
    """)
    max_vol = max((r['vol'] for r in context_activity), default=1) or 1

    disclosure_breakdown = query("""
        SELECT disclosure_level, COUNT(*) AS n
        FROM VerificationEvent
        GROUP BY disclosure_level
        ORDER BY disclosure_level
    """)
    total_verifs = sum(r['n'] for r in disclosure_breakdown) or 1

    lineages = query("""
        SELECT t1.token_id AS current_id, t1.status AS current_status,
               t1.activation_sequence,
               t2.token_id AS pred_id, t2.status AS pred_status,
               i.legal_name
        FROM IdentityToken t1
        LEFT JOIN IdentityToken t2 ON t1.predecessor_token_id = t2.token_id
        JOIN Individual i ON t1.individual_id = i.individual_id
        WHERE t1.predecessor_token_id IS NOT NULL
           OR t1.activation_sequence > 1
        ORDER BY t1.activation_sequence DESC, t1.token_id
        LIMIT 10
    """)

    recent_events = query("""
        SELECT le.event_id, le.event_type, le.event_timestamp,
               le.token_id, i.legal_name, ag.name AS actor_name,
               le.reason_code
        FROM TokenLifecycleEvent le
        JOIN IdentityToken t ON le.token_id = t.token_id
        JOIN Individual i ON t.individual_id = i.individual_id
        LEFT JOIN Agency ag ON le.actor_agency_id = ag.agency_id
        ORDER BY le.event_timestamp DESC
        LIMIT 12
    """)

    return dict(
        agencies=agencies, algorithms=algorithms, auth_matrix=auth_matrix,
        pq_breakdown=pq_breakdown,
        pq_active_total=pq_active_total,
        classical_active_total=classical_active_total,
        context_activity=context_activity, max_vol=max_vol,
        disclosure_breakdown=disclosure_breakdown, total_verifs=total_verifs,
        lineages=lineages, recent_events=recent_events,
    )


@app.route('/atlas')
@security.login_required
def atlas():
    """Atlas is a live operational investigation surface, not a dashboard.
    The globe IS the page. Everything else (HUD, event feed, detail panel)
    exists to drive selection and explain a single event when the operator
    clicks one. Aggregate analytics live on the dashboard."""

    # --- Health snapshot for HUD chrome -----------------------------------
    table_counts = {}
    for tbl in ['Individual', 'Agency', 'IdentityToken',
                'TokenLifecycleEvent', 'VerificationEvent', 'DeviceBinding']:
        table_counts[tbl] = query(f'SELECT COUNT(*) AS n FROM {tbl}', fetch='one')['n']

    state_pop = {row['status']: row['n'] for row in query("""
        SELECT status, COUNT(*) AS n FROM IdentityToken GROUP BY status
    """)}
    for s in ['ACTIVE', 'RESERVE', 'DORMANT', 'REVOKED', 'LOST', 'EXPIRED']:
        state_pop.setdefault(s, 0)

    pq_active = query("""
        SELECT alg.quantum_resistant, COUNT(t.token_id) AS n
        FROM CryptographicAlgorithm alg
        LEFT JOIN IdentityToken t ON alg.algorithm_id = t.algorithm_id AND t.status='ACTIVE'
        GROUP BY alg.quantum_resistant
    """)
    pq_n = sum(r['n'] for r in pq_active if r['quantum_resistant'])
    cls_n = sum(r['n'] for r in pq_active if not r['quantum_resistant'])

    disc = {r['disclosure_level']: r['n'] for r in query("""
        SELECT disclosure_level, COUNT(*) AS n
        FROM VerificationEvent GROUP BY disclosure_level
    """)}
    disc_total = sum(disc.values()) or 1

    # --- Anomaly indicators visible from the globe ------------------------
    anomalies = query("""
        SELECT
          SUM(CASE WHEN outcome != 'SUCCESS' THEN 1 ELSE 0 END) AS fail_n,
          SUM(CASE WHEN disclosure_level = 'FULL' THEN 1 ELSE 0 END) AS full_n
        FROM VerificationEvent
    """, fetch='one')

    # --- Predecessor lookup so each globe node can show its lineage chain --
    pred_rows = query("""
        SELECT t1.token_id   AS current_id,
               t1.activation_sequence,
               t2.token_id   AS pred_id,
               t2.status     AS pred_status
        FROM IdentityToken t1
        LEFT JOIN IdentityToken t2 ON t1.predecessor_token_id = t2.token_id
        WHERE t1.predecessor_token_id IS NOT NULL
    """)
    pred_map = {r['current_id']: r for r in pred_rows}

    # --- Live event stream: verifications + recent lifecycle events --------
    globe_events = query("""
        SELECT ve.event_id, ve.event_timestamp, ve.outcome, ve.disclosure_level,
               -- C6: redact location for ZERO_KNOWLEDGE verifications. With this
               -- NULL, _coords() falls back to a non-identifying (jurisdiction /
               -- context) position and the subtitle shows the region, so a ZK
               -- event is never plotted at — or labelled with — its real place.
               CASE WHEN ve.disclosure_level = 'ZERO_KNOWLEDGE'
                    THEN NULL ELSE ve.requestor_location END AS requestor_location,
               vc.context_type,
               t.token_id, t.status, t.activation_sequence,
               i.legal_name, i.jurisdiction,
               alg.name AS algorithm_name, alg.quantum_resistant,
               ag.name AS agency_name
        FROM VerificationEvent ve
        JOIN VerificationContext vc ON ve.context_id = vc.context_id
        LEFT JOIN IdentityToken t ON ve.token_id = t.token_id
        LEFT JOIN Individual i ON t.individual_id = i.individual_id
        LEFT JOIN CryptographicAlgorithm alg ON t.algorithm_id = alg.algorithm_id
        LEFT JOIN Agency ag ON ve.requesting_agency_id = ag.agency_id
        ORDER BY ve.event_timestamp DESC, ve.event_id DESC
        LIMIT 14
    """)

    recent_lifecycle = query("""
        SELECT le.event_id, le.event_type, le.event_timestamp,
               le.token_id, le.reason_code,
               i.legal_name, i.jurisdiction,
               alg.name AS algorithm_name, alg.quantum_resistant,
               ag.name AS actor_name
        FROM TokenLifecycleEvent le
        JOIN IdentityToken t ON le.token_id = t.token_id
        JOIN Individual i ON t.individual_id = i.individual_id
        LEFT JOIN CryptographicAlgorithm alg ON t.algorithm_id = alg.algorithm_id
        LEFT JOIN Agency ag ON le.actor_agency_id = ag.agency_id
        ORDER BY le.event_timestamp DESC
        LIMIT 12
    """)

    # --- Geographic projection (city → context → jurisdiction fallback) ----
    location_points = [
        ('San Francisco', (-122.4194, 37.7749, 'San Francisco')),
        ('New York',      (-74.0060, 40.7128, 'New York')),
        ('JFK Airport',   (-73.7781, 40.6413, 'JFK Airport')),
        ('Houston',       (-95.3698, 29.7604, 'Houston')),
        ('Philadelphia',  (-75.1652, 39.9526, 'Philadelphia')),
        ('Pittsburgh',    (-79.9959, 40.4406, 'Pittsburgh')),
        ('Los Angeles',   (-118.2437, 34.0522, 'Los Angeles')),
        ('Miami',         (-80.1918, 25.7617, 'Miami')),
    ]
    jurisdiction_points = {
        'US-CA': (-119.4179, 36.7783, 'California'),
        'US-NY': (-75.0000, 43.0000, 'New York'),
        'US-PA': (-77.1945, 41.2033, 'Pennsylvania'),
        'US-TX': (-99.9018, 31.9686, 'Texas'),
        'US-FL': (-81.5158, 27.6648, 'Florida'),
        'US':    (-98.5795, 39.8283, 'United States'),
    }
    context_points = {
        'BANKING':             (-74.0060, 40.7128, 'Banking rail'),
        'EMPLOYMENT':          (-122.4194, 37.7749, 'Employment rail'),
        'HEALTHCARE':          (-87.6298, 41.8781, 'Healthcare rail'),
        'TRAVEL':              (-73.7781, 40.6413, 'Travel rail'),
        'VOTING':              (-77.0369, 38.9072, 'Voting rail'),
        'MOTOR_VEHICLE':       (-89.3985, 40.6331, 'Motor vehicle rail'),
        'GOVERNMENT_BENEFITS': (-95.3698, 29.7604, 'Benefits rail'),
    }

    def _coords(location, jurisdiction, context_type, offset=0):
        lon, lat, region = context_points.get(context_type, (-98.5795, 39.8283, 'United States'))
        loc_lc = (location or '').lower()
        for needle, point in location_points:
            if needle.lower() in loc_lc:
                lon, lat, region = point
                break
        else:
            if jurisdiction in jurisdiction_points:
                lon, lat, region = jurisdiction_points[jurisdiction]
        lon += ((offset % 3) - 1) * 1.4
        lat += (((offset // 3) % 3) - 1) * 0.9
        return lon, lat, region

    def _context_label(raw):
        return (raw or '').replace('GOVERNMENT_BENEFITS', 'GOV_BENEFITS')

    def _tone(outcome=None, disclosure=None, event_type=None):
        if outcome and outcome != 'SUCCESS':
            return 'alert'
        if event_type in ('REVOKED', 'LOST', 'EXPIRED', 'DEVICE_REVOKED'):
            return 'alert'
        if event_type in ('ACTIVATED', 'DEVICE_BOUND'):
            return 'zk'
        return {
            'ZERO_KNOWLEDGE': 'zk',
            'SELECTIVE': 'selective',
            'FULL': 'full',
        }.get(disclosure, 'full' if event_type == 'ISSUED' else 'selective')

    def _pred_for(token_id):
        p = pred_map.get(token_id)
        if not p:
            return None
        return {
            'predecessorId': p['pred_id'],
            'predecessorStatus': p['pred_status'],
            'sequence': p['activation_sequence'],
        }

    globe_nodes = []
    for idx, ev in enumerate(globe_events):
        lon, lat, region = _coords(
            ev.get('requestor_location'),
            ev.get('jurisdiction'),
            ev.get('context_type'),
            idx,
        )
        ctx = _context_label(ev['context_type'])
        node = {
            'id': f"verif-{ev['event_id']}",
            'kind': 'verification',
            'lon': lon, 'lat': lat,
            'tone': _tone(ev.get('outcome'), ev.get('disclosure_level')),
            'title': f"{ctx} verification",
            'subtitle': ev.get('requestor_location') or region,
            'context': ctx,
            'tokenId': ev.get('token_id'),
            'holder': ev.get('legal_name'),
            'agency': ev.get('agency_name'),
            'algorithm': ev.get('algorithm_name'),
            'algorithmPq': bool(ev.get('quantum_resistant')),
            'outcome': ev.get('outcome'),
            'disclosure': ev.get('disclosure_level'),
            'href': url_for('tokens_detail', tok_id=ev['token_id']) if ev.get('token_id') else '',
            'timestamp': ev['event_timestamp'].strftime('%Y-%m-%d %H:%M'),
            'pq': bool(ev.get('quantum_resistant')),
            'filterKeys': ['verification']
                          + (['tokens'] if ev.get('token_id') else [])
                          + (['pq'] if ev.get('quantum_resistant') else [])
                          + (['failure'] if ev.get('outcome') and ev.get('outcome') != 'SUCCESS' else []),
            'lineage': _pred_for(ev.get('token_id')),
        }
        globe_nodes.append(node)

    for idx, ev in enumerate(recent_lifecycle):
        lon, lat, region = _coords(None, ev.get('jurisdiction'), 'BANKING', idx + 4)
        node = {
            'id': f"life-{ev['event_id']}",
            'kind': 'lifecycle',
            'lon': lon, 'lat': lat,
            'tone': _tone(event_type=ev['event_type']),
            'title': f"{ev['event_type']} token #{ev['token_id']}",
            'subtitle': ev.get('legal_name') or region,
            'context': 'LIFECYCLE',
            'tokenId': ev['token_id'],
            'holder': ev.get('legal_name'),
            'agency': ev.get('actor_name'),
            'algorithm': ev.get('algorithm_name'),
            'algorithmPq': bool(ev.get('quantum_resistant')),
            'outcome': None,
            'disclosure': None,
            'eventType': ev['event_type'],
            'reason': ev.get('reason_code'),
            'href': url_for('tokens_detail', tok_id=ev['token_id']),
            'timestamp': ev['event_timestamp'].strftime('%Y-%m-%d %H:%M'),
            'pq': bool(ev.get('quantum_resistant')),
            'filterKeys': ['tokens', 'lifecycle']
                          + (['pq'] if ev.get('quantum_resistant') else []),
            'lineage': _pred_for(ev['token_id']),
        }
        globe_nodes.append(node)

    globe_notifications = []
    for ev in recent_lifecycle[:8]:
        globe_notifications.append({
            'nodeId': f"life-{ev['event_id']}",
            'tone': _tone(event_type=ev['event_type']),
            'eventType': ev['event_type'],
            'title': f"token #{ev['token_id']} / {ev['legal_name']}",
            'time': ev['event_timestamp'].strftime('%m-%d %H:%M'),
        })

    health = {
        'tokens_total':       table_counts['IdentityToken'],
        'tokens_active':      state_pop.get('ACTIVE', 0),
        'tokens_reserve':     state_pop.get('RESERVE', 0),
        'tokens_terminal':    (state_pop.get('REVOKED', 0)
                               + state_pop.get('LOST', 0)
                               + state_pop.get('EXPIRED', 0)),
        'pq_pct': (100 * pq_n // (pq_n + cls_n)) if (pq_n + cls_n) else 0,
        'zk_pct': (100 * disc.get('ZERO_KNOWLEDGE', 0) // disc_total) if disc_total else 0,
        'agencies':           table_counts['Agency'],
        'individuals':        table_counts['Individual'],
        'verif_events':       table_counts['VerificationEvent'],
        'lifecycle_events':   table_counts['TokenLifecycleEvent'],
        'device_binds':       table_counts['DeviceBinding'],
        'failures':           int(anomalies['fail_n'] or 0),
        'full_disclosures':   int(anomalies['full_n'] or 0),
    }

    return render_template('atlas.html',
                           globe_nodes=globe_nodes,
                           globe_notifications=globe_notifications,
                           health=health)


# ============================================================================
# ATLAS API — server-side spatial aggregation for scaling to millions of events
#
# The Atlas frontend used to receive every event inline as JSON in the
# template, which was fine for the 17-row sample but cannot scale: at 100k
# events the page is slow, at 1M it's OOM. These endpoints implement the
# proper architecture:
#
#   GET /api/atlas/clusters?bbox=...&grid=...&kind=...
#       Server-side bin aggregation. At low zoom the world resolves into
#       O(100) clusters with summary counts; at high zoom the grid shrinks
#       and each cluster is small enough that the client switches to points.
#
#   GET /api/atlas/points?bbox=...&kind=...&limit=...
#       Individual events in the bbox, hard-capped at limit. Used at high
#       zoom (city / neighborhood) when cluster count is below threshold.
#
#   GET /api/atlas/stats?bbox=...
#       The four operational ratios (Active Tokens, Anomalies, PQ%, ZK%)
#       scoped to the visible bounding box.
#
#   GET /api/atlas/events?cursor=...&limit=...
#       Paginated unified feed for the right rail.
#
# Bounding-box parameter format: "min_lat,min_lon,max_lat,max_lon" decimal
# degrees, all four required. Out-of-range or NaN values yield 400.
# ============================================================================

# Hard caps to protect the server. Even with a maximally-zoomed-out bbox
# the cluster count is bounded by the grid; here we limit the upper bound
# of any single response.
_ATLAS_MAX_CLUSTERS = 5000
_ATLAS_MAX_POINTS   = 2000
_ATLAS_MAX_EVENTS   = 500


# =============================================================================
# Atlas TTL cache (R8-5)
# =============================================================================
# In-process TTL cache for atlas API responses. Keys are computed from the
# request parameters (bbox, grid, kind, limit) and values are tuples of
# (timestamp, response_dict). Hot atlas queries — the same bbox/grid being
# polled by multiple operators — hit the cache instead of the SQL
# aggregation function.
#
# This is the in-memory variant. R8-2 (Redis-backed limiter) introduces
# the multi-worker dependency; once Redis is available, this cache should
# migrate to a Redis backend so cache hits work across gunicorn workers.
# Until then, each worker has its own cache (acceptable: cache hits on
# the same worker still help; the worst case is cold-start across all
# workers, which is no worse than no cache at all).
#
# Cache invalidation: pure TTL. Atlas data changes when verifications or
# lifecycle events are written, but for a 30-second TTL the staleness is
# bounded and matches the typical operator polling interval.
import threading
import time as _time

_ATLAS_CACHE_TTL_SECONDS = float(os.environ.get('POLARIS_ATLAS_CACHE_TTL', '30'))
_ATLAS_CACHE_MAX_ENTRIES = int(os.environ.get('POLARIS_ATLAS_CACHE_MAX', '256'))
_atlas_cache = {}                               # dict[key, tuple[float, dict]]
_atlas_cache_lock = threading.Lock()
_atlas_cache_stats = {'hits': 0, 'misses': 0, 'expired': 0, 'evicted': 0}


def _atlas_cache_get(key):
    """Return the cached payload if fresh, else None. Thread-safe."""
    if _ATLAS_CACHE_TTL_SECONDS <= 0:
        return None
    now = _time.time()
    with _atlas_cache_lock:
        entry = _atlas_cache.get(key)
        if entry is None:
            _atlas_cache_stats['misses'] += 1
            return None
        ts, payload = entry
        if now - ts > _ATLAS_CACHE_TTL_SECONDS:
            del _atlas_cache[key]
            _atlas_cache_stats['expired'] += 1
            _atlas_cache_stats['misses'] += 1
            return None
        _atlas_cache_stats['hits'] += 1
        return payload


def _atlas_cache_set(key, payload):
    """Store payload with current timestamp. Evict oldest if at capacity."""
    if _ATLAS_CACHE_TTL_SECONDS <= 0:
        return
    now = _time.time()
    with _atlas_cache_lock:
        if len(_atlas_cache) >= _ATLAS_CACHE_MAX_ENTRIES:
            # Evict the oldest entry — simple LRU-ish behavior without ordereddict
            oldest_key = min(_atlas_cache, key=lambda k: _atlas_cache[k][0])
            del _atlas_cache[oldest_key]
            _atlas_cache_stats['evicted'] += 1
        _atlas_cache[key] = (now, payload)


def _atlas_cache_clear():
    """Used by tests and admin endpoints."""
    with _atlas_cache_lock:
        _atlas_cache.clear()
        for k in _atlas_cache_stats:
            _atlas_cache_stats[k] = 0


def _parse_cursor_int(val):
    """Parse a cursor expected to be a single integer.

    Returns the integer, or None if the input is missing, empty, or non-numeric.
    Used by /tokens (token_id is a clean monotonic key)."""
    if val is None or val == '':
        return None
    try:
        return int(val)
    except (ValueError, TypeError):
        return None


def _parse_cursor_composite(val):
    """Parse a composite cursor of form 'isoformat~int' → (datetime, int).

    Returns None if the input is missing or malformed. Used by /verifications
    where the sort key is (event_timestamp, event_id) — single-column cursor
    is insufficient because two events can share a timestamp."""
    if val is None or val == '':
        return None
    try:
        ts_part, id_part = val.split('~', 1)
        return (datetime.fromisoformat(ts_part), int(id_part))
    except (ValueError, AttributeError, TypeError):
        return None


def _format_cursor_composite(ts, id_):
    """Inverse of _parse_cursor_composite. ts is a datetime, id_ is an int."""
    return f"{ts.isoformat()}~{id_}"


def _parse_bbox(s):
    """Parse 'min_lat,min_lon,max_lat,max_lon' → 4-tuple of floats.
    Validates ranges and ordering. Raises ValueError on bad input."""
    if not s:
        raise ValueError("bbox required (format: min_lat,min_lon,max_lat,max_lon)")
    parts = s.split(',')
    if len(parts) != 4:
        raise ValueError("bbox must have exactly four comma-separated values")
    try:
        min_lat, min_lon, max_lat, max_lon = (float(p) for p in parts)
    except ValueError:
        raise ValueError("bbox values must be numeric")
    if not (-90 <= min_lat <= 90 and -90 <= max_lat <= 90):
        raise ValueError("latitudes must be in [-90, 90]")
    if not (-180 <= min_lon <= 180 and -180 <= max_lon <= 180):
        raise ValueError("longitudes must be in [-180, 180]")
    if min_lat > max_lat:
        raise ValueError("min_lat must be <= max_lat")
    # Antimeridian-spanning bboxes (min_lon > max_lon) are supported as
    # of v7. The atlas SQL functions in 11_atlas.sql use a wrap-aware
    # longitude predicate: when min_lon > max_lon, the bbox covers
    # [min_lon, 180] ∪ [-180, max_lon] (i.e. wraps across the date line).
    return min_lat, min_lon, max_lat, max_lon


# Window labels → timedelta. The schema stores event_timestamp as
# TIMESTAMP-without-zone (local wall clock) and the Polaris app+DB are
# co-located; therefore Python's `datetime.now()` (also local) is the
# right reference. Using a UTC clock here would silently
# shift the boundary by the server's TZ offset — caught during the
# v8.3 smoke test against a window=1h query that returned 0 rows for
# events inserted 30 minutes ago.
_ATLAS_TIME_WINDOWS = {
    '1h':   timedelta(hours=1),
    '24h':  timedelta(hours=24),
    '7d':   timedelta(days=7),
    '30d':  timedelta(days=30),
    'all':  None,                     # no time filter
}

# Outcome alias: "anomalies" = the union the operator typically wants when
# they're investigating a security incident. Anchored here (not in JS) so
# the SQL parameter is the same set across UI versions.
_ATLAS_OUTCOME_ALIASES = {
    'anomalies': 'FAILURE,UNAUTHORIZED,EXPIRED',
}

def _parse_atlas_filters(args):
    """Pull the v8.3 / A+C filter parameters off the request and return a
    dict of the SQL-ready values: since (TIMESTAMP or None), outcomes (CSV
    or None), disclosure (CSV or None), contexts (CSV or None),
    event_types (lifecycle, CSV or None), window_label (str). Raises
    ValueError on any malformed input so the route returns 400."""
    window = (args.get('window') or '24h').strip().lower()
    if window not in _ATLAS_TIME_WINDOWS:
        raise ValueError(
            f"window must be one of {sorted(_ATLAS_TIME_WINDOWS.keys())}; got {window!r}"
        )
    delta = _ATLAS_TIME_WINDOWS[window]
    since = (datetime.now() - delta) if delta is not None else None

    outcomes_raw = (args.get('outcomes') or '').strip()
    if outcomes_raw in _ATLAS_OUTCOME_ALIASES:
        outcomes_raw = _ATLAS_OUTCOME_ALIASES[outcomes_raw]
    outcomes = outcomes_raw or None
    # Whitelist outcome values to prevent SQL string-list smuggling
    if outcomes:
        valid = {'SUCCESS', 'FAILURE', 'EXPIRED', 'UNAUTHORIZED'}
        for v in outcomes.split(','):
            if v.strip() not in valid:
                raise ValueError(f"unknown outcome: {v!r}")

    disclosure_raw = (args.get('disclosure') or '').strip()
    disclosure = disclosure_raw or None
    if disclosure:
        valid = {'ZERO_KNOWLEDGE', 'SELECTIVE', 'FULL'}
        for v in disclosure.split(','):
            if v.strip() not in valid:
                raise ValueError(f"unknown disclosure level: {v!r}")

    contexts_raw = (args.get('contexts') or '').strip()
    contexts = contexts_raw or None
    if contexts:
        valid = {'BANKING', 'EMPLOYMENT', 'HEALTHCARE', 'TRAVEL',
                 'VOTING', 'MOTOR_VEHICLE', 'GOVERNMENT_BENEFITS'}
        for v in contexts.split(','):
            if v.strip() not in valid:
                raise ValueError(f"unknown context: {v!r}")

    event_types_raw = (args.get('event_types') or '').strip()
    event_types = event_types_raw or None
    if event_types:
        valid = {'ISSUED', 'ACTIVATED', 'DEACTIVATED', 'DEVICE_BOUND',
                 'DEVICE_REVOKED', 'REVOKED', 'LOST', 'EXPIRED', 'REPLACED'}
        for v in event_types.split(','):
            if v.strip() not in valid:
                raise ValueError(f"unknown event_type: {v!r}")

    return {
        'window': window,
        'since': since,
        'outcomes': outcomes,
        'disclosure': disclosure,
        'contexts': contexts,
        'event_types': event_types,
    }


def _filter_cache_key(filters):
    """Reduce a filter dict to a hashable cache key fragment."""
    return (filters['window'], filters['outcomes'], filters['disclosure'],
            filters['contexts'], filters['event_types'])


@app.route('/api/atlas/clusters')
@security.login_required
def api_atlas_clusters():
    """Spatial aggregation endpoint. Returns ≤ _ATLAS_MAX_CLUSTERS bins.
    R8-5: result cached for _ATLAS_CACHE_TTL_SECONDS to absorb hot polling.

    v8.3 (A+C): accepts ?window= (1h/24h/7d/30d/all), ?outcomes= (CSV
    incl. 'anomalies' alias), ?disclosure= (CSV), ?contexts= (CSV) for
    verification kind, and ?event_types= (CSV) for lifecycle kind. The
    cache key includes the filter-set so different filter combinations
    do NOT collide."""
    try:
        min_lat, min_lon, max_lat, max_lon = _parse_bbox(request.args.get('bbox'))
        grid = float(request.args.get('grid', '5'))
        if grid <= 0 or grid > 90:
            raise ValueError("grid must be in (0, 90] decimal degrees")
        kind = request.args.get('kind', 'verification')
        if kind not in ('verification', 'lifecycle'):
            raise ValueError("kind must be 'verification' or 'lifecycle'")
        f = _parse_atlas_filters(request.args)
    except ValueError as e:
        return jsonify(error=str(e)), 400

    cache_key = ('clusters', kind, min_lat, min_lon, max_lat, max_lon, grid,
                 _filter_cache_key(f))
    cached = _atlas_cache_get(cache_key)
    if cached is not None:
        return jsonify(cached)

    if kind == 'verification':
        rows = query("""
            SELECT lat, lon, n_total, n_failure, n_pq, n_zk, n_full
            FROM atlas_clusters_verifications(%s, %s, %s, %s, %s, %s, %s, %s, %s)
            LIMIT %s
        """, (min_lat, min_lon, max_lat, max_lon, grid,
              f['since'], f['outcomes'], f['disclosure'], f['contexts'],
              _ATLAS_MAX_CLUSTERS))
    else:
        rows = query("""
            SELECT lat, lon, n_total, n_revoked, n_lost, n_issued, n_activated
            FROM atlas_clusters_lifecycles(%s, %s, %s, %s, %s, %s, %s)
            LIMIT %s
        """, (min_lat, min_lon, max_lat, max_lon, grid,
              f['since'], f['event_types'],
              _ATLAS_MAX_CLUSTERS))

    payload = dict(
        kind=kind,
        bbox=[min_lat, min_lon, max_lat, max_lon],
        grid=grid,
        window=f['window'],
        count=len(rows),
        clusters=[dict(r) for r in rows],
    )
    _atlas_cache_set(cache_key, payload)
    return jsonify(payload)


@app.route('/api/atlas/points')
@security.login_required
def api_atlas_points():
    """Individual event points in the bbox. Used at high zoom when the
    cluster count is below the cluster→point threshold. v8.3 honors the
    same filter parameter set as /clusters."""
    try:
        min_lat, min_lon, max_lat, max_lon = _parse_bbox(request.args.get('bbox'))
        limit = min(int(request.args.get('limit', '500')), _ATLAS_MAX_POINTS)
        if limit <= 0:
            raise ValueError("limit must be positive")
        kind = request.args.get('kind', 'verification')
        if kind not in ('verification', 'lifecycle'):
            raise ValueError("kind must be 'verification' or 'lifecycle'")
        f = _parse_atlas_filters(request.args)
    except ValueError as e:
        return jsonify(error=str(e)), 400

    if kind == 'verification':
        rows = query("""
            SELECT event_id, lat, lon,
                   to_char(event_timestamp, 'YYYY-MM-DD HH24:MI') AS event_timestamp,
                   token_id, holder_name, agency_name, context_type,
                   outcome, disclosure_level, algorithm_name, pq, requestor_location
            FROM atlas_points_verifications(%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (min_lat, min_lon, max_lat, max_lon, limit,
              f['since'], f['outcomes'], f['disclosure'], f['contexts']))
    else:
        rows = query("""
            SELECT event_id, lat, lon,
                   to_char(event_timestamp, 'YYYY-MM-DD HH24:MI') AS event_timestamp,
                   token_id, event_type, reason_code, holder_name,
                   agency_name, algorithm_name, pq
            FROM atlas_points_lifecycles(%s, %s, %s, %s, %s, %s, %s)
        """, (min_lat, min_lon, max_lat, max_lon, limit,
              f['since'], f['event_types']))

    return jsonify(
        kind=kind,
        bbox=[min_lat, min_lon, max_lat, max_lon],
        limit=limit,
        window=f['window'],
        count=len(rows),
        points=[dict(r) for r in rows],
    )


@app.route('/api/atlas/stats')
@security.login_required
def api_atlas_stats():
    """The four HUD signals scoped to the visible bbox.
    R8-5: cached for _ATLAS_CACHE_TTL_SECONDS.

    v8.3 (A): also accepts ?window= so the HUD numbers reflect the
    operator's selected time slice, not just lifetime."""
    try:
        min_lat, min_lon, max_lat, max_lon = _parse_bbox(request.args.get('bbox'))
        f = _parse_atlas_filters(request.args)
    except ValueError as e:
        return jsonify(error=str(e)), 400

    cache_key = ('stats', min_lat, min_lon, max_lat, max_lon, f['window'])
    cached = _atlas_cache_get(cache_key)
    if cached is not None:
        return jsonify(cached)

    row = query("""
        SELECT n_active_tokens, n_anomalies, n_failures, n_full,
               pq_pct, zk_pct, n_verifs, n_lifecycles
        FROM atlas_stats(%s, %s, %s, %s, %s)
    """, (min_lat, min_lon, max_lat, max_lon, f['since']), fetch='one')

    payload = dict(
        bbox=[min_lat, min_lon, max_lat, max_lon],
        window=f['window'],
        n_active_tokens=int(row['n_active_tokens']),
        n_anomalies=int(row['n_anomalies']),
        n_failures=int(row['n_failures']),
        n_full=int(row['n_full']),
        pq_pct=int(row['pq_pct']),
        zk_pct=int(row['zk_pct']),
        n_verifs=int(row['n_verifs']),
        n_lifecycles=int(row['n_lifecycles']),
    )
    _atlas_cache_set(cache_key, payload)
    return jsonify(payload)


@app.route('/api/atlas/timeline')
@security.login_required
def api_atlas_timeline():
    """Bucket counts for the histogram strip below the toolbar.

    Returns N points where each point is `{ts: ISO-8601, n_total, n_anomaly}`
    over the requested `?window=` time range, with `?buckets=` slices.
    Honors the same outcome / disclosure / context / event_types filters as
    the cluster endpoint so the strip reflects the operator's full filter
    state. Hard-capped at 240 buckets so a misconfigured client can't ask
    for 100k pixels of histogram. v8.3 / A."""
    try:
        min_lat, min_lon, max_lat, max_lon = _parse_bbox(request.args.get('bbox'))
        buckets = int(request.args.get('buckets', '60'))
        if buckets <= 0 or buckets > 240:
            raise ValueError("buckets must be in (0, 240]")
        kind = request.args.get('kind', 'verification')
        if kind not in ('verification', 'lifecycle'):
            raise ValueError("kind must be 'verification' or 'lifecycle'")
        f = _parse_atlas_filters(request.args)
    except ValueError as e:
        return jsonify(error=str(e)), 400

    # 'all' window has no fixed start; default to 30d in that case so the
    # histogram has a meaningful x-range. The HUD reads 'all'; the
    # histogram reads '30d-strip' so both can be honest about scope.
    since = f['since'] or (datetime.now() - _ATLAS_TIME_WINDOWS['30d'])

    cache_key = ('timeline', kind, min_lat, min_lon, max_lat, max_lon,
                 buckets, _filter_cache_key(f))
    cached = _atlas_cache_get(cache_key)
    if cached is not None:
        return jsonify(cached)

    rows = query("""
        SELECT to_char(bucket_ts, 'YYYY-MM-DD"T"HH24:MI:SS') AS ts,
               n_total, n_anomaly
        FROM atlas_timeline(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ORDER BY bucket_ts
    """, (min_lat, min_lon, max_lat, max_lon, since, buckets, kind,
          f['outcomes'], f['disclosure'], f['contexts']))

    payload = dict(
        bbox=[min_lat, min_lon, max_lat, max_lon],
        window=f['window'],
        kind=kind,
        buckets=buckets,
        since=since.isoformat(),
        until=datetime.now().isoformat(),
        points=[
            {'ts': r['ts'], 'n_total': int(r['n_total']),
             'n_anomaly': int(r['n_anomaly'])}
            for r in rows
        ],
    )
    _atlas_cache_set(cache_key, payload)
    return jsonify(payload)


@app.route('/api/atlas/cache-stats')
@security.login_required
def api_atlas_cache_stats():
    """Cache observability — hit/miss/expired/evicted counters and current size.
    Useful for verifying R8-5 effectiveness in production."""
    with _atlas_cache_lock:
        return jsonify(
            ttl_seconds=_ATLAS_CACHE_TTL_SECONDS,
            max_entries=_ATLAS_CACHE_MAX_ENTRIES,
            current_entries=len(_atlas_cache),
            hits=_atlas_cache_stats['hits'],
            misses=_atlas_cache_stats['misses'],
            expired=_atlas_cache_stats['expired'],
            evicted=_atlas_cache_stats['evicted'],
            hit_ratio=(
                _atlas_cache_stats['hits'] /
                (_atlas_cache_stats['hits'] + _atlas_cache_stats['misses'])
                if (_atlas_cache_stats['hits'] + _atlas_cache_stats['misses']) > 0
                else 0.0
            ),
        )


def _health_check_database():
    """Check Postgres reachability and basic schema integrity."""
    try:
        t0 = _time.time()
        row = query(
            "SELECT count(*) AS n FROM information_schema.tables "
            "WHERE table_schema = 'public'",
            fetch='one',
        )
        latency_ms = round((_time.time() - t0) * 1000.0, 1)
        table_count = int(row['n']) if row else 0
        status = 'healthy'
        if latency_ms > 500:
            status = 'degraded'
        if table_count < 20:
            # We expect 26 tables in a fully-loaded schema; anything below 20
            # suggests a partial / broken load.
            status = 'unhealthy' if table_count == 0 else 'degraded'
        return {
            'status': status,
            'latency_ms': latency_ms,
            'table_count': table_count,
        }
    except Exception as exc:
        return {'status': 'unhealthy', 'error': str(exc)[:160]}


def _health_check_redis():
    """Check Redis reachability via the rate-limiter backend.

    The rate-limiter wraps Redis; using its ``healthy()`` probe keeps the
    health endpoint coupled to the same connection the app uses, so a
    rate-limiter failure surfaces immediately rather than waiting for the
    first /api/atlas/* call.
    """
    rl = security.rate_limiter
    try:
        t0 = _time.time()
        ok = rl.healthy()
        latency_ms = round((_time.time() - t0) * 1000.0, 1)
        if rl.name == 'memory':
            # In-memory limiter is always up; report as healthy + 0ms.
            return {'status': 'healthy', 'backend': 'memory', 'latency_ms': 0.0}
        if not ok:
            return {
                'status': 'degraded',
                'backend': rl.name,
                'latency_ms': latency_ms,
                'note': 'rate-limiter backend unreachable; allow() fails closed',
            }
        return {
            'status': 'healthy',
            'backend': rl.name,
            'latency_ms': latency_ms,
        }
    except Exception as exc:
        return {'status': 'degraded', 'backend': rl.name, 'error': str(exc)[:160]}


def _health_check_zk_binary():
    """Check the Plonky2 ZK prover binary's presence and reachability.

    The binary is bundled at /opt/polaris/zk in the production image
    (Dockerfile.prod). For dev, the launcher sets POLARIS_ZK_BINARY to a
    cargo-built target. Absence is NOT unhealthy at the overall level — ZK
    is an optional Arc D primitive — but it is reported as degraded so
    operators see it.
    """
    path = os.environ.get('POLARIS_ZK_BINARY', '/opt/polaris/zk')
    if not os.path.isfile(path):
        return {
            'status': 'degraded',
            'path': path,
            'note': 'zk binary not present; epoch closes will fail',
        }
    if not os.access(path, os.X_OK):
        return {
            'status': 'degraded',
            'path': path,
            'note': 'zk binary present but not executable',
        }
    try:
        proc = subprocess.run(
            [path, '--version'],
            capture_output=True, text=True, timeout=2.0,
        )
        version = (proc.stdout or proc.stderr or '').strip().splitlines()[0] if (proc.stdout or proc.stderr) else 'unknown'
        return {'status': 'healthy', 'path': path, 'version': version[:80]}
    except subprocess.TimeoutExpired:
        return {'status': 'degraded', 'path': path, 'note': '--version timed out'}
    except Exception as exc:
        return {'status': 'degraded', 'path': path, 'error': str(exc)[:160]}


def _health_check_disk():
    """Check free disk space at the application's state-dir mountpoint.

    Returns degraded < 5GB free OR > 85% used; unhealthy < 500MB free.
    """
    target = os.environ.get('POLARIS_STATE_DIR', '/tmp/polaris-state')
    # Probe the deepest existing ancestor (state-dir may not exist yet).
    probe = target
    while probe and not os.path.exists(probe):
        parent = os.path.dirname(probe)
        if parent == probe:
            break
        probe = parent
    try:
        usage = shutil.disk_usage(probe or '/')
        free_gb = round(usage.free / (1024 ** 3), 2)
        used_pct = round((usage.used / usage.total) * 100.0, 1) if usage.total else 0.0
        status = 'healthy'
        if free_gb < 0.5:
            status = 'unhealthy'
        elif free_gb < 5.0 or used_pct > 85.0:
            status = 'degraded'
        return {
            'status': status,
            'free_gb': free_gb,
            'used_pct': used_pct,
            'mount_probe': probe,
        }
    except Exception as exc:
        return {'status': 'degraded', 'error': str(exc)[:160]}


# Per-component health keys that carry operator-only detail: raw exception text
# (a psycopg2 connection error embeds the DB host / port / database name) and
# absolute filesystem paths (the zk binary, the state-dir probe). /api/health is
# unauthenticated (load-balancer + uptime probes), so these are logged to stderr
# for operators but stripped from the response (CWE-209 information exposure).
_HEALTH_SENSITIVE_KEYS = ('error', 'path', 'mount_probe')


def _sanitize_health_checks(checks):
    """Return a copy of `checks` with operator-only detail removed (logged to
    stderr). The per-component `status` token, which conveys health, is kept."""
    safe = {}
    for name, check in checks.items():
        leaked = {k: check[k] for k in _HEALTH_SENSITIVE_KEYS if k in check}
        if leaked:
            sys.stderr.write(f"[health] {name}: {leaked}\n")
        safe[name] = {k: v for k, v in check.items()
                      if k not in _HEALTH_SENSITIVE_KEYS}
    return safe


# Severity ordering used by /api/health to roll component statuses up to
# the overall status. Higher number = worse.
_HEALTH_SEVERITY = {'healthy': 0, 'degraded': 1, 'unhealthy': 2}


def _compute_readiness():
    """Run the dependency health checks and roll them up to an overall status.

    Returns ``(body, code)``. This is the READINESS signal: can the app serve
    traffic right now? Shared by /api/health (kept for backwards compatibility)
    and /api/health/ready. Strips operator-only detail (raw error text, absolute
    paths) from the unauthenticated payload (CWE-209); the status tokens convey
    health. atlas_cache is informational and does not affect the overall status.
    """
    checks = {
        'database':  _health_check_database(),
        'redis':     _health_check_redis(),
        'zk_binary': _health_check_zk_binary(),
        'disk':      _health_check_disk(),
    }

    # Roll up worst-of per-component status as the overall status.
    overall = 'healthy'
    for component in checks.values():
        component_status = component.get('status', 'unhealthy')
        if _HEALTH_SEVERITY.get(component_status, 2) > _HEALTH_SEVERITY[overall]:
            overall = component_status

    # Backwards-compatible atlas_cache observability (informational only)
    with _atlas_cache_lock:
        checks['atlas_cache'] = {
            'status': 'healthy',
            'entries': len(_atlas_cache),
            'hits': _atlas_cache_stats['hits'],
            'misses': _atlas_cache_stats['misses'],
        }

    body = {
        'status': overall,
        'version': POLARIS_VERSION,
        'uptime_seconds': int(_time.time() - _APP_STARTED_AT),
        'checks': _sanitize_health_checks(checks),
        'timestamp': datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z'),
    }
    code = 503 if overall == 'unhealthy' else 200
    return body, code


@app.route('/api/health')
def api_health():
    """Structured health endpoint (G29 / v8.77) — the dependency roll-up.

    No auth required (load balancers, Caddy upstream probes, uptime monitors).
    Kept unchanged for backwards compatibility. Semantically this is the
    READINESS probe; /api/health/ready is its canonical alias and
    /api/health/live is the cheap liveness counterpart (v9.108).

    Status codes:
        200 — healthy or degraded
        503 — unhealthy (at least one critical dependency failed)
    """
    body, code = _compute_readiness()
    return jsonify(body), code


@app.route('/api/health/ready')
def api_health_ready():
    """Readiness probe (v9.108): can THIS instance serve traffic right now?

    Runs the dependency checks (database, redis, zk binary, disk). Returns 503
    if a critical dependency is down, so an orchestrator stops routing traffic
    to this instance WITHOUT restarting it (a restart would not bring the
    dependency back). Same payload as /api/health.
    """
    body, code = _compute_readiness()
    return jsonify(body), code


@app.route('/api/health/live')
def api_health_live():
    """Liveness probe (v9.108): is the process alive and answering requests?

    Deliberately CHEAP — it touches NO external dependency. A liveness probe
    that checked the database would restart the container every time the DB
    blipped, a restart storm that cannot help; dependency health belongs in
    readiness. Always 200 unless the worker is wedged (in which case it cannot
    answer at all, which is exactly what an orchestrator should act on).
    """
    return jsonify({
        'status': 'alive',
        'version': POLARIS_VERSION,
        'uptime_seconds': int(_time.time() - _APP_STARTED_AT),
        'timestamp': datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z'),
    }), 200


@app.route('/api/metrics')
def api_metrics():
    """Operator-readable application metrics (v9.31 freeze condition 6).

    No metrics backend by design (no Prometheus exporter, no StatsD).
    Operators pipe stdout structured logs wherever they like; this
    endpoint exposes the in-process counters as JSON for grep + jq.

    Headline fields per `polaris_web/observability.py` (v9.27 / Tier 8 #11):

        request_rate_per_minute    — trailing-5-minute average throughput
        error_rate_per_minute      — trailing-5-minute 5xx + uncaught
        auth_failures_per_minute   — trailing-5-minute failed-login + WebAuthn
        duress_events_total        — monotonic count since process start
        uptime_seconds             — seconds since process started
        process_id                 — OS pid

    `duress_events_total` is the load-bearing anti-coercion alarm. A
    coerced operator's duress code raises a row that no one reads is
    the failure mode the v9.27 Sanctum joint resolution called out;
    this endpoint makes the signal observable. **NON-ZERO IS THE
    ANTI-COERCION ALARM. Page immediately.**

    No auth required — uptime monitors + operator scripts need access
    without secrets, and the four counters expose no per-user data.
    """
    snapshot = observability.MetricsSnapshot.collect()
    return jsonify(snapshot.to_dict()), 200


@app.route('/.well-known/security.txt')
@app.route('/security.txt')
def security_txt():
    """RFC 9116 security disclosure surface (v9.13 production hardening).

    Both `/security.txt` and `/.well-known/security.txt` resolve here so
    automated tooling and humans converge on the same content. No auth
    required (the whole point is reachability for vulnerability disclosure).
    The contact + signature policy is read from environment variables so
    operators do not need to edit code to publish their own contact info.
    """
    contact = os.environ.get('POLARIS_SECURITY_CONTACT',
                             'mailto:security@example.invalid')
    # RFC 9116 mandates that expiration_iso be in the future; default to 1 year out.
    from datetime import datetime as _dt, timedelta as _td, timezone as _tz
    expires_default = (_dt.now(_tz.utc) + _td(days=365)).strftime('%Y-%m-%dT%H:%M:%SZ')
    expires = os.environ.get('POLARIS_SECURITY_EXPIRES', expires_default)
    preferred_lang = os.environ.get('POLARIS_SECURITY_LANG', 'en')
    body_lines = [
        f"Contact: {contact}",
        f"Expires: {expires}",
        f"Preferred-Languages: {preferred_lang}",
        f"Canonical: /security.txt",
        # Polaris-specific addenda
        "Policy: This is a reference implementation. Vulnerabilities should",
        "Policy: be reported privately to the contact above. The maintainers",
        "Policy: aim to acknowledge within 72 hours.",
    ]
    response = make_response("\n".join(body_lines) + "\n")
    response.headers['Content-Type'] = 'text/plain; charset=utf-8'
    # security.txt is public + cacheable.
    response.headers['Cache-Control'] = 'public, max-age=3600'
    return response


@app.route('/metrics')
def metrics():
    """Prometheus-compatible /metrics endpoint (v8.93 / G32).

    Returns the canonical Prometheus text-format exposition of the
    registry built at import time. Per-request hooks (`_metrics_before_request`
    / `_metrics_after_request`) tag every served request with route +
    method + status, so this endpoint reports cumulative HTTP traffic
    out-of-the-box.

    Liveness signals refreshed at scrape time:
      - polaris_app_info: version metadata

    No authentication required (consumed by Prometheus scrapers running
    in the cluster network or behind operator-internal ACLs). If the
    deployment exposes /metrics to the public internet without an ACL,
    that's a configuration choice the operator makes deliberately at
    the reverse-proxy layer (Caddy can rate-limit or route this path
    differently than user-facing routes).

    Graceful fallback: if prometheus_client isn't installed (ad-hoc
    dev environment), returns HTTP 503 with a plain-text message.
    """
    if not _PROM_AVAILABLE:
        return (
            "prometheus_client not installed; /metrics unavailable.\n"
            "Install via the production Dockerfile or `pip install prometheus_client`.\n",
            503,
            {'Content-Type': 'text/plain; charset=utf-8'},
        )

    # Refresh dynamic gauges at scrape time.
    try:
        _METRICS_APP_INFO.labels(version=POLARIS_VERSION).set(1)
    except Exception:
        pass

    payload = _prom_generate_latest(_METRICS_REGISTRY)
    return payload, 200, {'Content-Type': _PROM_CONTENT_TYPE}


@app.route('/api/atlas/events')
@security.login_required
def api_atlas_events():
    """Paginated unified event feed (verifications + lifecycle), most-recent
    first. Cursor format: 'TIMESTAMP|EVENT_ID' (URL-encoded)."""
    try:
        limit = min(int(request.args.get('limit', '50')), _ATLAS_MAX_EVENTS)
        if limit <= 0:
            raise ValueError("limit must be positive")
    except ValueError as e:
        return jsonify(error=str(e)), 400

    cursor_ts, cursor_id = None, None
    cursor_param = request.args.get('cursor', '')
    if cursor_param:
        try:
            ts_str, id_str = cursor_param.split('|')
            cursor_ts = ts_str          # let Postgres parse the timestamp
            cursor_id = int(id_str)
        except (ValueError, TypeError):
            return jsonify(error="cursor must be 'TIMESTAMP|EVENT_ID'"), 400

    rows = query("""
        SELECT kind, event_id,
               to_char(event_timestamp, 'YYYY-MM-DD HH24:MI:SS') AS event_timestamp,
               -- Full-microsecond timestamp for the keyset cursor. The display
               -- column above floors to whole seconds; building the cursor from
               -- it would skip every event in the (S.0, S.f) sub-second band at
               -- a page boundary, since atlas_recent_events filters with a
               -- strict `< (cursor_ts, cursor_id)`. Cursor must be full-precision.
               to_char(event_timestamp, 'YYYY-MM-DD HH24:MI:SS.US') AS event_ts_cursor,
               token_id, holder_name, agency_name, label, detail, tone, lat, lon
        FROM atlas_recent_events(%s::timestamp, %s, %s)
    """, (cursor_ts, cursor_id, limit))

    next_cursor = None
    if rows and len(rows) == limit:
        last = rows[-1]
        next_cursor = f"{last['event_ts_cursor']}|{last['event_id']}"

    return jsonify(
        count=len(rows),
        next_cursor=next_cursor,
        # event_ts_cursor is the internal full-precision keyset value; the JSON
        # exposes only the human-readable whole-second event_timestamp.
        events=[{k: v for k, v in r.items() if k != 'event_ts_cursor'} for r in rows],
    )


# ---------------------------------------------------------------------------
# Anchor batch endpoints (R10-2 / M2-2)
# ---------------------------------------------------------------------------

@app.route('/api/anchor/batch', methods=['POST'])
@security.login_required
@security.require_role('admin')
@security.csrf_protect
def api_anchor_batch_close():
    """Close a Merkle batch for the pending BlockchainAnchor rows of a
    given signature algorithm. The Merkle root + per-leaf proofs are
    pre-computed by anchoring.py, then handed to close_anchor_batch
    (which holds a per-algorithm advisory lock for the transaction).

    Request: JSON { "algorithm_id": <int> }
    Response: { "batch_id": <int>, "merkle_root": <hex>, "batch_size": <int> }
    """
    payload = request.get_json(silent=True) or {}
    try:
        algorithm_id = int(payload['algorithm_id'])
    except (KeyError, ValueError, TypeError):
        return jsonify(error="algorithm_id (int) is required"), 400

    pending = query("""
        SELECT a.anchor_id, a.commitment_hash
          FROM BlockchainAnchor a
          JOIN IdentityToken    t ON a.token_id = t.token_id
         WHERE a.batch_id IS NULL
           AND t.algorithm_id = %s
         ORDER BY a.anchor_id
    """, (algorithm_id,))

    if not pending:
        return jsonify(error="no pending anchors for that algorithm"), 404

    leaves = [(int(r['anchor_id']), r['commitment_hash']) for r in pending]
    merkle_root, proofs = anchoring.compute_batch(leaves, 'SHA3-256')

    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("CALL close_anchor_batch(%s, %s, %s)",
                        (algorithm_id, merkle_root, Json(proofs)))
            conn.commit()
            cur.execute("""
                SELECT batch_id, batch_size FROM AnchorBatch
                 WHERE merkle_root = %s AND algorithm_id = %s
                 ORDER BY batch_id DESC LIMIT 1
            """, (merkle_root, algorithm_id))
            row = cur.fetchone()
    except psycopg2.Error as e:
        conn.rollback()
        return jsonify(error=db_error_to_message(e)), 400
    finally:
        conn.close()

    return jsonify(
        batch_id=row['batch_id'],
        merkle_root=merkle_root,
        batch_size=row['batch_size'],
    )


@app.route('/api/anchor/<int:token_id>')
@security.login_required
def api_anchor_get(token_id):
    """Return the BlockchainAnchor row plus the AnchorBatch (if batched)
    for a given token. Useful for clients that need the inclusion proof
    + root to verify off-line."""
    row = query("""
        SELECT a.anchor_id, a.token_id, a.did, a.commitment_hash,
               a.ledger_network, a.anchored_date, a.status,
               a.batch_id, a.merkle_proof,
               b.merkle_root, b.algorithm_id AS batch_algorithm_id,
               b.committed_to_chain, b.external_chain, b.external_chain_tx
          FROM BlockchainAnchor a
          LEFT JOIN AnchorBatch b ON a.batch_id = b.batch_id
         WHERE a.token_id = %s
    """, (token_id,), fetch='one')

    if not row:
        return jsonify(error="no anchor for that token"), 404

    return jsonify(dict(row))


@app.route('/api/anchor/verify/<int:token_id>')
@security.login_required
def api_anchor_verify(token_id):
    """Server-side proof verification: reconstruct the Merkle root from
    the stored leaf + proof and compare to the AnchorBatch root. Returns
    {"verified": true|false, ...}. A pending (not-yet-batched) anchor
    returns verified=false with status='PENDING'."""
    row = query("""
        SELECT a.anchor_id, a.commitment_hash, a.batch_id, a.merkle_proof,
               b.merkle_root
          FROM BlockchainAnchor a
          LEFT JOIN AnchorBatch b ON a.batch_id = b.batch_id
         WHERE a.token_id = %s
    """, (token_id,), fetch='one')

    if not row:
        return jsonify(error="no anchor for that token"), 404

    if row['batch_id'] is None:
        return jsonify(
            verified=False,
            status='PENDING',
            anchor_id=row['anchor_id'],
        )

    leaf = anchoring.leaf_hash(int(row['anchor_id']), row['commitment_hash'])
    proof = row['merkle_proof'] or []
    ok = anchoring.verify_proof(leaf, proof, row['merkle_root'])

    return jsonify(
        verified=bool(ok),
        anchor_id=row['anchor_id'],
        batch_id=row['batch_id'],
        merkle_root=row['merkle_root'],
        leaf=leaf,
    )


# ---------------------------------------------------------------------------
# Federation API endpoints (R11-3 / M2-8)
# ---------------------------------------------------------------------------

@app.route('/api/federation/attest', methods=['POST'])
@security.login_required
@security.require_role('admin')
@security.csrf_protect
def api_federation_attest():
    """Record a federation trust attestation. Admin-only — federation is
    an agency-level decision, not an operator's. Wraps uc10_attest_trust,
    which holds a per-attesting-agency advisory lock (5th catalog entry).

    Request: JSON { "attesting_agency_id", "attested_agency_id",
                    "context_id", "valid_until" (YYYY-MM-DD) }
    Response: { "attestation_id": <int>, "status": "active" }
    """
    payload = request.get_json(silent=True) or {}
    try:
        attesting_id = int(payload['attesting_agency_id'])
        attested_id = int(payload['attested_agency_id'])
        context_id = int(payload['context_id'])
        valid_until = payload['valid_until']  # YYYY-MM-DD string
    except (KeyError, ValueError, TypeError):
        return jsonify(error="required fields: attesting_agency_id, "
                             "attested_agency_id, context_id, valid_until"), 400

    signed_by = session.get('user_id')
    if signed_by is None:
        return jsonify(error="session missing user_id"), 401

    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("CALL uc10_attest_trust(%s, %s, %s, %s, %s)",
                        (attesting_id, attested_id, context_id, valid_until, signed_by))
            conn.commit()
            cur.execute("""
                SELECT attestation_id FROM AgencyTrustAttestation
                 WHERE attesting_agency_id = %s
                   AND attested_agency_id  = %s
                   AND context_id          = %s
                   AND revocation_date IS NULL
            """, (attesting_id, attested_id, context_id))
            row = cur.fetchone()
    except psycopg2.Error as e:
        conn.rollback()
        return jsonify(error=db_error_to_message(e)), 400
    finally:
        conn.close()

    return jsonify(attestation_id=row['attestation_id'], status='active')


@app.route('/api/federation/revoke', methods=['POST'])
@security.login_required
@security.require_role('admin')
@security.csrf_protect
def api_federation_revoke():
    """Revoke an active federation attestation. Admin-only. Wraps
    uc10_revoke_attestation. The revocation is forward-looking: past
    VerificationEvent rows are NOT retroactively invalidated.

    Request: JSON { "attestation_id", "revocation_reason" (≥ 8 chars) }
    Response: { "attestation_id", "status": "revoked" }
    """
    payload = request.get_json(silent=True) or {}
    try:
        attestation_id = int(payload['attestation_id'])
        reason = str(payload['revocation_reason'])
    except (KeyError, ValueError, TypeError):
        return jsonify(error="required fields: attestation_id, revocation_reason"), 400

    signed_by = session.get('user_id')
    if signed_by is None:
        return jsonify(error="session missing user_id"), 401

    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("CALL uc10_revoke_attestation(%s, %s, %s)",
                        (attestation_id, reason, signed_by))
            conn.commit()
    except psycopg2.Error as e:
        conn.rollback()
        return jsonify(error=db_error_to_message(e)), 400
    finally:
        conn.close()

    return jsonify(attestation_id=attestation_id, status='revoked')


# ---------------------------------------------------------------------------
# ZK-SNARK epoch + verification endpoints (R10-1 / M2-1 / v8.23)
#
# C3 + A4 + B3 — transparent setup, Plonky2 SNARK, hybrid-Merkle circuit
# reusing R10-2 infrastructure. The Rust binary `polaris-zk` provides the
# crypto; this layer is the schema + route bridge.
# ---------------------------------------------------------------------------

@app.route('/api/zk/epoch/close', methods=['POST'])
@security.login_required
@security.require_role('admin')
@security.csrf_protect
def api_zk_epoch_close():
    """Close a ZK epoch: snapshot currently-valid ACTIVE tokens with
    their context-permissions, derive per-token leaf seeds, compute the
    Merkle root via the Rust prover, and CALL uc11_close_epoch which
    writes TokenStateEpoch + TokenStateEpochLeaf rows under a
    per-procedure advisory lock.

    Request: JSON { "context_id": <int>, "valid_until": "YYYY-MM-DD HH:MM:SS" }
    Response: { "epoch_id": <int>, "merkle_root": <hex>, "committed_count": <int> }
    """
    payload = request.get_json(silent=True) or {}
    try:
        context_id = int(payload['context_id'])
        valid_until = payload['valid_until']
    except (KeyError, ValueError, TypeError):
        return jsonify(error="required fields: context_id (int), valid_until (timestamp)"), 400

    signed_by = session.get('user_id')
    if signed_by is None:
        return jsonify(error="session missing user_id"), 401

    # Snapshot the active tokens that have permission for the given context.
    rows = query("""
        SELECT t.token_id, t.token_value
          FROM IdentityToken t
          JOIN TokenPermission p ON p.token_id = t.token_id
         WHERE t.status = 'ACTIVE'
           AND p.context_id = %s
           AND NOT EXISTS (SELECT 1 FROM RevocationList r WHERE r.token_id = t.token_id)
         ORDER BY t.token_id
    """, (context_id,))
    if not rows:
        return jsonify(error="no eligible tokens for the given context"), 404

    # Derive per-token leaf seeds (deterministic).
    leaves = [zk.derive_leaf_seed(r['token_id'], r['token_value'], context_id) for r in rows]
    root_hex, leaf_info = zk.compute_epoch_leaves(leaves)

    # Construct the JSONB payload uc11_close_epoch expects.
    token_leaves = []
    for r, li in zip(rows, leaf_info):
        token_leaves.append({
            'token_id': r['token_id'],
            'leaf_hash': li['leaf_hash'],
            'proof_path': li['proof_path'],
        })

    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "CALL uc11_close_epoch(%s, %s, %s, %s)",
                (root_hex, valid_until, signed_by, Json(token_leaves)),
            )
            conn.commit()
            cur.execute("""
                SELECT epoch_id, committed_count FROM TokenStateEpoch
                 WHERE merkle_root = %s ORDER BY epoch_id DESC LIMIT 1
            """, (root_hex,))
            row = cur.fetchone()
    except psycopg2.Error as e:
        conn.rollback()
        return jsonify(error=db_error_to_message(e)), 400
    finally:
        conn.close()

    return jsonify(
        epoch_id=row['epoch_id'],
        merkle_root=root_hex,
        committed_count=row['committed_count'],
    )


@app.route('/api/zk/epoch/<int:epoch_id>')
@security.login_required
def api_zk_epoch_get(epoch_id):
    """Return the TokenStateEpoch row for inspection (no witness data)."""
    row = query("""
        SELECT epoch_id, merkle_root, valid_from, valid_until,
               committed_count, closed_at, closed_by_user_id
          FROM TokenStateEpoch
         WHERE epoch_id = %s
    """, (epoch_id,), fetch='one')
    if not row:
        return jsonify(error="epoch not found"), 404
    # Coerce timestamps for JSON.
    return jsonify({
        'epoch_id': row['epoch_id'],
        'merkle_root': row['merkle_root'],
        'valid_from': str(row['valid_from']),
        'valid_until': str(row['valid_until']),
        'committed_count': row['committed_count'],
        'closed_at': str(row['closed_at']),
        'closed_by_user_id': row['closed_by_user_id'],
    })


@app.route('/api/zk/verify', methods=['POST'])
@security.login_required
@security.csrf_protect
def api_zk_verify():
    """Verify a ZK-SNARK proof bundle against a specified epoch + context
    + nonce. The caller supplies the proof bundle (from a prover) and
    states which (epoch_id, context_id, nonce) the proof is supposed to
    be bound to. The verifier:
      1. Loads the epoch's merkle_root from TokenStateEpoch.
      2. Checks valid_until >= now (R4 epoch-boundary).
      3. Calls the Rust verifier via zk.verify_proof_against_epoch.

    Request: JSON {
        "epoch_id": <int>,
        "context_id": <int>,
        "nonce": <int>,
        "proof_bundle": <ProofBundle dict>
    }
    Response: { "verified": <bool>, "reason": <optional str> }
    """
    payload = request.get_json(silent=True) or {}
    try:
        epoch_id = int(payload['epoch_id'])
        context_id = int(payload['context_id'])
        nonce = int(payload['nonce'])
        proof_bundle = payload['proof_bundle']
        if not isinstance(proof_bundle, dict):
            raise TypeError("proof_bundle must be a dict")
    except (KeyError, ValueError, TypeError) as e:
        return jsonify(error=f"required fields: epoch_id, context_id, nonce, proof_bundle ({e})"), 400

    epoch = query("""
        SELECT merkle_root, valid_until
          FROM TokenStateEpoch
         WHERE epoch_id = %s
    """, (epoch_id,), fetch='one')
    if not epoch:
        return jsonify(verified=False, reason="epoch not found"), 404

    # R4: epoch-boundary check. valid_until is a TIMESTAMP-without-zone stored
    # as local wall clock (app+DB co-located), so compare against datetime.now()
    # like every other boundary in this module — a UTC clock would shift the
    # boundary by the server's offset.
    if epoch['valid_until'] < datetime.now():
        return jsonify(verified=False, reason="epoch expired")

    try:
        ok = zk.verify_proof_against_epoch(
            proof_bundle,
            expected_root_hex=epoch['merkle_root'],
            expected_epoch_id=epoch_id,
            expected_context_id=context_id,
            expected_nonce=nonce,
        )
    except Exception as e:
        return jsonify(verified=False, reason=f"verifier error: {e}"), 400

    if not ok:
        return jsonify(verified=False)

    # R2 anti-replay (T-T2): the (epoch, context, nonce) binding stops proof
    # SUBSTITUTION, but the identical bundle would otherwise verify again. Consume
    # the nonce as single-use: the INSERT succeeds on first verified use; a replay
    # hits the PK and ON CONFLICT DO NOTHING returns no row, so we reject it. The
    # INSERT is atomic, so two concurrent replays of the same bundle serialize on
    # the PK and exactly one wins. We consume only AFTER a true verify, so a failed
    # proof never burns a nonce a legitimate later proof might use.
    consumed = query("""
        INSERT INTO ZkVerificationNonce (epoch_id, context_id, nonce)
        VALUES (%s, %s, %s)
        ON CONFLICT ON CONSTRAINT pk_zk_verification_nonce DO NOTHING
        RETURNING consumed_at
    """, (epoch_id, context_id, nonce), fetch='returning')
    if consumed is None:
        return jsonify(verified=False, reason="nonce already consumed (replay)")

    return jsonify(verified=True)


# ---------------------------------------------------------------------------
# Duress code endpoints (R11-5 / M2-10 / v8.24)
#
# Compulsion resistance per PDF §9.5. The DuressEvent table is the 8th
# audit-of-record. The /duress route is the admin-only operator dashboard
# showing unacknowledged duress signals; /api/duress/record is the
# direct-call entrypoint used by automation and test paths (the normal
# duress path is invoked silently by verifications_new on a code match).
# ---------------------------------------------------------------------------

@app.route('/duress')
@security.login_required
@security.require_role('admin', 'auditor')
def duress_dashboard():
    """Admin/auditor HTML dashboard for the DuressEvent audit-of-record
    (R11-5 / M2-10 / v8.24). Operators are denied access — R6 audit
    refinement means the duress dashboard is for incident responders
    only, not for the operators who might be standing next to a
    coercer.

    Renders the same data `/api/duress/events` serves, plus the
    enrolled-token counter so admins can see how many tokens have
    duress codes configured."""
    rows = query("""
        SELECT d.event_id, d.token_id, d.context_id, d.requesting_agency_id,
               d.event_timestamp, d.oob_channel, d.oob_notified_at,
               i.legal_name AS holder_name,
               a.name AS verifying_agency_name,
               vc.context_type
          FROM DuressEvent d
          JOIN IdentityToken t ON d.token_id = t.token_id
          JOIN Individual i ON t.individual_id = i.individual_id
          JOIN Agency a ON d.requesting_agency_id = a.agency_id
          JOIN VerificationContext vc ON d.context_id = vc.context_id
         ORDER BY d.event_timestamp DESC
         LIMIT 200
    """)
    # v9.20 audit-access logging: who looked at the duress dashboard?
    security.record_audit_access(
        get_db, 'DuressEvent',
        filter_criteria={'route': '/duress', 'limit': 200},
        result_row_count=len(rows),
    )
    enrolled_count = query(
        "SELECT count(*) AS n FROM IdentityToken WHERE duress_code_hash IS NOT NULL",
        fetch='one'
    )['n']
    active_token_count = query(
        "SELECT count(*) AS n FROM IdentityToken WHERE status = 'ACTIVE'",
        fetch='one'
    )['n']
    return render_template(
        'duress_queue.html',
        rows=rows,
        enrolled_count=enrolled_count,
        active_token_count=active_token_count,
    )


@app.route('/api/duress/events')
@security.login_required
@security.require_role('admin', 'auditor')
def api_duress_events():
    """Return unacknowledged duress events (admin/auditor only). The
    operator-visible verifications list does NOT join to DuressEvent —
    this is the dedicated path for incident responders. R6 audit
    refinement: anti-revealing posture."""
    rows = query("""
        SELECT d.event_id, d.token_id, d.context_id, d.requesting_agency_id,
               d.event_timestamp, d.oob_channel, d.oob_notified_at,
               i.legal_name AS holder_name,
               a.name AS verifying_agency_name,
               vc.context_type
          FROM DuressEvent d
          JOIN IdentityToken t ON d.token_id = t.token_id
          JOIN Individual i ON t.individual_id = i.individual_id
          JOIN Agency a ON d.requesting_agency_id = a.agency_id
          JOIN VerificationContext vc ON d.context_id = vc.context_id
         ORDER BY d.event_timestamp DESC
         LIMIT 200
    """)
    return jsonify(
        count=len(rows),
        events=[{
            'event_id': r['event_id'],
            'token_id': r['token_id'],
            'holder_name': r['holder_name'],
            'context_type': r['context_type'],
            'verifying_agency': r['verifying_agency_name'],
            'event_timestamp': str(r['event_timestamp']),
            'oob_channel': r['oob_channel'],
            'oob_notified_at': str(r['oob_notified_at']) if r['oob_notified_at'] else None,
            'acknowledged': r['oob_notified_at'] is not None,
        } for r in rows]
    )


@app.route('/api/duress/record', methods=['POST'])
@security.login_required
@security.require_role('admin', 'operator')
@security.csrf_protect
def api_duress_record():
    """Record a duress event directly (admin/operator). Wraps
    uc12_record_duress for tests and automation paths. The normal flow
    is for verifications_new to call this silently on duress-code match;
    this route exists for explicit-record use cases.

    Request: JSON { "token_id", "context_id", "requesting_agency_id" }
    Response: { "event_id": <int> }
    """
    payload = request.get_json(silent=True) or {}
    try:
        token_id = int(payload['token_id'])
        context_id = int(payload['context_id'])
        requesting_agency_id = int(payload['requesting_agency_id'])
    except (KeyError, ValueError, TypeError):
        return jsonify(error="required fields: token_id, context_id, requesting_agency_id"), 400

    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "CALL uc12_record_duress(%s, %s, %s, %s)",
                (token_id, context_id, requesting_agency_id, 'AUDIT_TABLE'),
            )
            conn.commit()
            cur.execute("""
                SELECT event_id FROM DuressEvent
                 WHERE token_id = %s AND context_id = %s
                   AND requesting_agency_id = %s
                 ORDER BY event_id DESC LIMIT 1
            """, (token_id, context_id, requesting_agency_id))
            row = cur.fetchone()
    except psycopg2.Error as e:
        conn.rollback()
        return jsonify(error=db_error_to_message(e)), 400
    finally:
        conn.close()

    return jsonify(event_id=row['event_id'])


# ============================================================================
# v2 SUBSTRATE READ-ONLY VIEWS (v8.28 — UI catch-up, graduation phase)
# ============================================================================
# Three read-only HTML surfaces for the v2 substrate that v8.21–v8.24 added
# at the backend but never exposed in the UI: anchor batches (R10-2),
# ZK epochs (R10-1), and the federation attestation graph (R11-3). All three
# are operator+ (no special role gate beyond login_required) — they're
# informational. Duress remains admin/auditor-only via the existing /duress.

@app.route('/anchors')
@security.login_required
def anchors_list():
    """AnchorBatch list (R10-2 / M2-2). Read-only view of the Merkle
    batches that group BlockchainAnchor rows under a per-algorithm
    advisory lock at close. The dashboard's "Anchor Batches" tile links
    here. Order is by created_at DESC (newest first), capped at 200 —
    seed has 2, prod-scale would still keep a single screen useful."""
    rows = query("""
        SELECT b.batch_id, b.merkle_root, b.batch_size, b.created_at,
               b.committed_to_chain, b.external_chain, b.external_chain_tx,
               alg.name AS algorithm_name, alg.quantum_resistant,
               (SELECT COUNT(*) FROM BlockchainAnchor a WHERE a.batch_id = b.batch_id) AS member_count
          FROM AnchorBatch b
          JOIN CryptographicAlgorithm alg ON b.algorithm_id = alg.algorithm_id
         ORDER BY b.created_at DESC, b.batch_id DESC
         LIMIT 200
    """)
    pending_anchors = query(
        "SELECT COUNT(*) AS n FROM BlockchainAnchor WHERE batch_id IS NULL",
        fetch='one')['n']
    return render_template('anchors_list.html', rows=rows,
                           pending_anchors=pending_anchors)


@app.route('/epochs')
@security.login_required
def epochs_list():
    """TokenStateEpoch list (R10-1 / M2-1). Read-only view of the closed
    ZK epochs. Each row carries the Plonky2 Merkle root the SNARK proves
    inclusion against, plus the committed_count (number of token leaves
    rolled into the epoch). Click-through shows the per-token leaves."""
    epoch_id_filter = request.args.get('epoch_id', type=int)
    rows = query("""
        SELECT e.epoch_id, e.merkle_root, e.valid_from, e.valid_until,
               e.committed_count, e.closed_at,
               u.username AS closed_by_username,
               (SELECT COUNT(*) FROM TokenStateEpochLeaf l
                 WHERE l.epoch_id = e.epoch_id) AS leaf_count
          FROM TokenStateEpoch e
          JOIN AppUser u ON e.closed_by_user_id = u.user_id
         ORDER BY e.closed_at DESC, e.epoch_id DESC
         LIMIT 200
    """)
    leaves = []
    if epoch_id_filter is not None:
        leaves = query("""
            SELECT l.leaf_id, l.epoch_id, l.token_id, l.leaf_hash,
                   i.legal_name AS holder_name,
                   t.status AS token_status
              FROM TokenStateEpochLeaf l
              JOIN IdentityToken t ON l.token_id = t.token_id
              JOIN Individual i ON t.individual_id = i.individual_id
             WHERE l.epoch_id = %s
             ORDER BY l.leaf_id
        """, (epoch_id_filter,))
    return render_template('epochs_list.html', rows=rows,
                           leaves=leaves, selected_epoch=epoch_id_filter)


@app.route('/federation')
@security.login_required
def federation_viewer():
    """AgencyTrustAttestation viewer (R11-3 / M2-8). Read-only view of
    the issuer-federation trust graph. Each row is an explicit
    attestation: attesting agency vouches that attested agency may
    verify in this context, until valid_until or until explicitly
    revoked. NO transitive trust — the v8.22 ship is explicit-only.
    Status pills (ACTIVE / EXPIRED / REVOKED) make state legible."""
    rows = query("""
        SELECT att.attestation_id, att.attested_date, att.valid_until,
               att.revocation_date, att.revocation_reason,
               ag1.name AS attesting_name,
               ag1.agency_type AS attesting_type,
               ag2.name AS attested_name,
               ag2.agency_type AS attested_type,
               vc.context_type,
               u.username AS signed_by_username,
               CASE
                   WHEN att.revocation_date IS NOT NULL THEN 'REVOKED'
                   WHEN att.valid_until < CURRENT_DATE  THEN 'EXPIRED'
                   ELSE 'ACTIVE'
               END AS state
          FROM AgencyTrustAttestation att
          JOIN Agency ag1 ON att.attesting_agency_id = ag1.agency_id
          JOIN Agency ag2 ON att.attested_agency_id  = ag2.agency_id
          JOIN VerificationContext vc ON att.context_id = vc.context_id
          JOIN AppUser u ON att.signed_by = u.user_id
         ORDER BY att.attested_date DESC, att.attestation_id DESC
         LIMIT 500
    """)
    counts = query("""
        SELECT
            SUM(CASE WHEN revocation_date IS NOT NULL THEN 1 ELSE 0 END) AS revoked,
            SUM(CASE WHEN revocation_date IS NULL
                      AND valid_until <  CURRENT_DATE THEN 1 ELSE 0 END) AS expired,
            SUM(CASE WHEN revocation_date IS NULL
                      AND valid_until >= CURRENT_DATE THEN 1 ELSE 0 END) AS active
          FROM AgencyTrustAttestation
    """, fetch='one')
    return render_template('federation_viewer.html', rows=rows, counts=counts)


@app.route('/individuals')
@security.login_required
def individuals_list():
    """List of individuals with pagination. At national scale (millions of
    holders) the unpaginated list would crash any browser; the (individual_id)
    primary key already serves the ORDER BY here, so paging is O(1)."""
    page      = max(1, int(request.args.get('page',     '1')))
    page_size = min(500, max(10, int(request.args.get('page_size', '100'))))
    offset    = (page - 1) * page_size
    rows = query(
        'SELECT * FROM Individual ORDER BY individual_id LIMIT %s OFFSET %s',
        (page_size + 1, offset)
    )
    has_next = len(rows) > page_size
    rows = rows[:page_size]
    return render_template('individuals_list.html',
                           rows=rows,
                           page=page, page_size=page_size,
                           has_next=has_next, has_prev=page > 1)


@app.route('/individuals/new', methods=['GET', 'POST'])
@security.login_required
@security.require_role('admin')
@security.csrf_protect
def individuals_new():
    if request.method == 'POST':
        try:
            new_id = query("""
                INSERT INTO Individual (legal_name, date_of_birth, jurisdiction)
                VALUES (%s, %s, %s) RETURNING individual_id
            """, (request.form['legal_name'],
                  request.form['date_of_birth'],
                  request.form['jurisdiction']),
                fetch='returning')['individual_id']
            flash(f'Created individual #{new_id}', 'success')
            return redirect(url_for('individuals_list'))
        except psycopg2.Error as e:
            flash(db_error_to_message(e), 'error')
    return render_template('individuals_form.html', row=None, action='Create')


@app.route('/individuals/<int:ind_id>/edit', methods=['GET', 'POST'])
@security.login_required
@security.require_role('admin')
@security.csrf_protect
def individuals_edit(ind_id):
    if request.method == 'POST':
        try:
            query("""
                UPDATE Individual
                   SET legal_name=%s, date_of_birth=%s, jurisdiction=%s
                 WHERE individual_id=%s
            """, (request.form['legal_name'],
                  request.form['date_of_birth'],
                  request.form['jurisdiction'],
                  ind_id),
                fetch='none')
            flash(f'Updated individual #{ind_id}', 'success')
            return redirect(url_for('individuals_list'))
        except psycopg2.Error as e:
            flash(db_error_to_message(e), 'error')
    row = query('SELECT * FROM Individual WHERE individual_id=%s',
                (ind_id,), fetch='one')
    if not row:
        abort(404)
    return render_template('individuals_form.html', row=row, action='Update')


@app.route('/individuals/<int:ind_id>/delete', methods=['POST'])
@security.login_required
@security.require_role('admin')
@security.csrf_protect
def individuals_delete(ind_id):
    try:
        n = query('DELETE FROM Individual WHERE individual_id=%s',
                  (ind_id,), fetch='none')
        if n:
            flash(f'Deleted individual #{ind_id}', 'success')
        else:
            flash(f'Individual #{ind_id} not found', 'error')
    except psycopg2.Error as e:
        flash(db_error_to_message(e), 'error')
    return redirect(url_for('individuals_list'))


# ============================================================================
# CIVIC ENROLLMENT VIEW (R11-4 / M2-9)
#
# Per-jurisdiction × status rollup. Counts only — per-individual enumeration
# of NOT_ENROLLED is NOT a first-class query, by deliberate design. An
# admin who needs it must write the join directly, leaving an audit trace.
# See DEVNOTES/ships/tiered-enrollment.md for the asymmetric-design rationale.
# ============================================================================

@app.route('/individuals/enrollment')
@security.login_required
def enrollment_summary():
    """Civic enrollment summary — counts by (jurisdiction, status).
    Implements the PDF §9 'civic queries can answer "is this person known"
    without requiring an active token' requirement at the aggregate level."""
    jurisdiction_filter = (request.args.get('jurisdiction') or '').strip() or None
    rows = query(
        "SELECT * FROM civic_enrollment_summary(%s)",
        (jurisdiction_filter,)
    )

    # Jurisdiction list for the filter dropdown, sourced from Individual
    # so empty jurisdictions don't appear (they wouldn't in the rollup anyway).
    jurisdictions = query(
        "SELECT DISTINCT jurisdiction FROM Individual ORDER BY jurisdiction"
    )

    # Pivot for display: status across the top, jurisdiction down the side.
    statuses = ['NOT_ENROLLED', 'PENDING_ENROLLMENT', 'ENROLLED',
                'EXEMPT', 'LAPSED']
    pivot = {}
    for r in rows:
        pivot.setdefault(r['jurisdiction'], {})[r['status']] = r['n_individuals']

    return render_template('individuals_enrollment.html',
                           rows=rows,
                           pivot=pivot,
                           statuses=statuses,
                           jurisdictions=jurisdictions,
                           jurisdiction_filter=jurisdiction_filter)


# ============================================================================
# AGENCIES
# ============================================================================

@app.route('/agencies')
@security.login_required
def agencies_list():
    rows = query('SELECT * FROM Agency ORDER BY agency_id')
    return render_template('agencies_list.html', rows=rows)


@app.route('/agencies/new', methods=['GET', 'POST'])
@security.login_required
@security.require_role('admin')
@security.csrf_protect
def agencies_new():
    if request.method == 'POST':
        try:
            new_id = query("""
                INSERT INTO Agency (name, agency_type, jurisdiction, authorization_level)
                VALUES (%s, %s, %s, %s) RETURNING agency_id
            """, (request.form['name'],
                  request.form['agency_type'],
                  request.form['jurisdiction'],
                  int(request.form['authorization_level'])),
                fetch='returning')['agency_id']
            flash(f'Created agency #{new_id}', 'success')
            return redirect(url_for('agencies_list'))
        except (psycopg2.Error, ValueError) as e:
            flash(db_error_to_message(e), 'error')
    return render_template('agencies_form.html', row=None, action='Create')


@app.route('/agencies/<int:ag_id>/edit', methods=['GET', 'POST'])
@security.login_required
@security.require_role('admin')
@security.csrf_protect
def agencies_edit(ag_id):
    if request.method == 'POST':
        try:
            query("""
                UPDATE Agency
                   SET name=%s, agency_type=%s, jurisdiction=%s, authorization_level=%s
                 WHERE agency_id=%s
            """, (request.form['name'],
                  request.form['agency_type'],
                  request.form['jurisdiction'],
                  int(request.form['authorization_level']),
                  ag_id),
                fetch='none')
            flash(f'Updated agency #{ag_id}', 'success')
            return redirect(url_for('agencies_list'))
        except (psycopg2.Error, ValueError) as e:
            flash(db_error_to_message(e), 'error')
    row = query('SELECT * FROM Agency WHERE agency_id=%s', (ag_id,), fetch='one')
    if not row:
        abort(404)
    return render_template('agencies_form.html', row=row, action='Update')


@app.route('/agencies/<int:ag_id>/delete', methods=['POST'])
@security.login_required
@security.require_role('admin')
@security.csrf_protect
def agencies_delete(ag_id):
    try:
        n = query('DELETE FROM Agency WHERE agency_id=%s', (ag_id,), fetch='none')
        if n:
            flash(f'Deleted agency #{ag_id}', 'success')
        else:
            flash(f'Agency #{ag_id} not found', 'error')
    except psycopg2.Error as e:
        flash(db_error_to_message(e), 'error')
    return redirect(url_for('agencies_list'))


# ============================================================================
# IDENTITY TOKENS
# ============================================================================

@app.route('/tokens')
@security.login_required
def tokens_list():
    """
    Token list with holder, issuer, and algorithm joined in.
    Supports filtering by status via query string (?status=ACTIVE).

    Pagination (R7-3, v7): two modes.
      - Cursor mode (preferred): ?cursor=N walks forward, ?prev_cursor=N walks
        backward. Sort key is t.token_id ASC; a single int cursor is sufficient
        because token_id is the primary key. Cost is O(log n + page_size)
        regardless of depth — page 20000-equivalent runs in <100ms vs 13.6s
        with OFFSET on the 2M-row stress dataset.
      - Page mode (legacy): ?page=N. Backward-compatible. OFFSET-bound and
        slow at depth, retained so that bookmarked URLs still work.
      Cursor params take precedence over page when both are supplied.
    Page size clamped to [10, 500] in both modes.
    """
    status_filter = request.args.get('status', '')
    individual_filter = request.args.get('individual_id', '')
    # Page size: hard cap at 500 (browser OOM); floor at 1 (clamping below
    # protects against negative or zero values that would corrupt OFFSET
    # arithmetic, but does not punish legitimate small-page requests).
    page_size = min(500, max(1, int(request.args.get('page_size', '100'))))

    cursor_raw      = request.args.get('cursor')
    prev_cursor_raw = request.args.get('prev_cursor')
    cursor_mode = (cursor_raw is not None) or (prev_cursor_raw is not None)
    cursor      = _parse_cursor_int(cursor_raw)
    prev_cursor = _parse_cursor_int(prev_cursor_raw)

    where_sql = ''
    params = []
    if status_filter:
        where_sql += ' AND t.status = %s'
        params.append(status_filter)
    if individual_filter:
        where_sql += ' AND t.individual_id = %s'
        params.append(int(individual_filter))

    base_select = """
        SELECT t.*, i.legal_name, ag.name AS issuer_name, alg.name AS alg_name
        FROM   IdentityToken t
        JOIN   Individual i ON t.individual_id = i.individual_id
        JOIN   Agency    ag ON t.issuing_agency_id = ag.agency_id
        JOIN   CryptographicAlgorithm alg ON t.algorithm_id = alg.algorithm_id
        WHERE  TRUE """

    if cursor_mode:
        if prev_cursor is not None:
            # Walk backward: rows with token_id < prev_cursor in DESC order,
            # then reverse so display order remains ASC. The +1 trick tells
            # us whether more rows exist further back.
            sql = base_select + where_sql + (
                " AND t.token_id < %s ORDER BY t.token_id DESC LIMIT %s")
            rows = query(sql, params + [prev_cursor, page_size + 1])
            has_prev = len(rows) > page_size
            rows = rows[:page_size]
            rows.reverse()
            # We arrived here from a forward (Next) click, so the page we
            # just left exists and a "Next" must be available.
            has_next = True
        else:
            cursor_sql = ' AND t.token_id > %s' if cursor is not None else ''
            cursor_param = [cursor] if cursor is not None else []
            sql = base_select + where_sql + cursor_sql + (
                " ORDER BY t.token_id ASC LIMIT %s")
            rows = query(sql, params + cursor_param + [page_size + 1])
            has_next = len(rows) > page_size
            rows = rows[:page_size]
            if cursor is not None and rows:
                # Cheap probe: is there at least one row before the first
                # visible row? O(log n) on the primary-key index.
                first_id = rows[0]['token_id']
                probe = query(
                    "SELECT 1 FROM IdentityToken t WHERE TRUE " + where_sql +
                    " AND t.token_id < %s LIMIT 1",
                    params + [first_id], fetch='one')
                has_prev = probe is not None
            else:
                has_prev = False

        first_cursor = rows[0]['token_id'] if rows else None
        last_cursor  = rows[-1]['token_id'] if rows else None

        return render_template('tokens_list.html',
                               rows=rows,
                               status_filter=status_filter,
                               individual_filter=individual_filter,
                               page=None,
                               page_size=page_size,
                               cursor_mode=True,
                               first_cursor=first_cursor,
                               last_cursor=last_cursor,
                               has_next=has_next,
                               has_prev=has_prev)

    page   = max(1, int(request.args.get('page', '1')))
    offset = (page - 1) * page_size
    sql = base_select + where_sql + " ORDER BY t.token_id ASC LIMIT %s OFFSET %s"
    rows = query(sql, params + [page_size + 1, offset])
    has_next = len(rows) > page_size
    rows = rows[:page_size]

    return render_template('tokens_list.html',
                           rows=rows,
                           status_filter=status_filter,
                           individual_filter=individual_filter,
                           page=page,
                           page_size=page_size,
                           cursor_mode=False,
                           has_next=has_next,
                           has_prev=page > 1)


@app.route('/tokens/<int:tok_id>')
@security.login_required
def tokens_detail(tok_id):
    """
    Detail view of a single token: full record, lifecycle history,
    verification events, device bindings, blockchain anchor, revocation.
    """
    token = query("""
        SELECT t.*, i.legal_name, ag.name AS issuer_name, alg.name AS alg_name,
               alg.quantum_resistant, alg.deprecation_date
        FROM   IdentityToken t
        JOIN   Individual i  ON t.individual_id = i.individual_id
        JOIN   Agency    ag  ON t.issuing_agency_id = ag.agency_id
        JOIN   CryptographicAlgorithm alg ON t.algorithm_id = alg.algorithm_id
        WHERE  t.token_id = %s
    """, (tok_id,), fetch='one')
    if not token:
        abort(404)

    lifecycle = query("""
        SELECT le.*, ag.name AS actor_name
        FROM   TokenLifecycleEvent le
        LEFT JOIN Agency ag ON le.actor_agency_id = ag.agency_id
        WHERE  le.token_id = %s
        ORDER BY le.event_timestamp
    """, (tok_id,))

    verifications = query("""
        SELECT ve.*, vc.context_type, ag.name AS verifier_name
        FROM   VerificationEvent ve
        JOIN   VerificationContext vc ON ve.context_id = vc.context_id
        JOIN   Agency ag              ON ve.requesting_agency_id = ag.agency_id
        WHERE  ve.token_id = %s
        ORDER BY ve.event_timestamp DESC
    """, (tok_id,))

    devices = query('SELECT * FROM DeviceBinding WHERE token_id=%s ORDER BY binding_id',
                    (tok_id,))
    anchors = query('SELECT * FROM BlockchainAnchor WHERE token_id=%s', (tok_id,))
    revocations = query("""
        SELECT rl.*, ag.name AS revoker_name
        FROM   RevocationList rl
        JOIN   Agency ag ON rl.revoked_by_agency_id = ag.agency_id
        WHERE  rl.token_id = %s
    """, (tok_id,))
    permissions = query("""
        SELECT tp.*, vc.context_type
        FROM   TokenPermission tp
        JOIN   VerificationContext vc ON tp.context_id = vc.context_id
        WHERE  tp.token_id = %s
        ORDER BY vc.context_type
    """, (tok_id,))

    # v8.28 — v2 substrate state for this token:
    #   - TokenSignature rows (M:N, R11-1)
    #   - AnchorBatch membership (R10-2 — via BlockchainAnchor join)
    #   - TokenStateEpochLeaf rows (R10-1 — latest first)
    #   - Duress-enrollment flag (R11-5; non-revealing — boolean only)
    v2_signatures = query("""
        SELECT s.signature_id, s.signed_at, s.deprecation_date,
               alg.name AS algorithm_name, alg.quantum_resistant
          FROM TokenSignature s
          JOIN CryptographicAlgorithm alg ON s.algorithm_id = alg.algorithm_id
         WHERE s.token_id = %s
         ORDER BY (s.deprecation_date IS NOT NULL), s.signed_at DESC
    """, (tok_id,))
    v2_anchor_batches = query("""
        SELECT a.anchor_id, a.commitment_hash AS leaf_hash,
               a.anchored_date AS anchor_timestamp,
               b.batch_id, b.merkle_root AS batch_root,
               b.committed_to_chain, b.external_chain,
               alg.name AS algorithm_name
          FROM BlockchainAnchor a
          LEFT JOIN AnchorBatch b ON a.batch_id = b.batch_id
          LEFT JOIN CryptographicAlgorithm alg ON b.algorithm_id = alg.algorithm_id
         WHERE a.token_id = %s
         ORDER BY a.anchored_date DESC
    """, (tok_id,))
    v2_epoch_leaves = query("""
        SELECT l.leaf_id, l.leaf_hash,
               e.epoch_id, e.valid_from, e.valid_until, e.closed_at,
               e.merkle_root AS epoch_root
          FROM TokenStateEpochLeaf l
          JOIN TokenStateEpoch e ON l.epoch_id = e.epoch_id
         WHERE l.token_id = %s
         ORDER BY e.closed_at DESC
    """, (tok_id,))
    duress_enrolled = bool(token.get('duress_code_hash'))

    return render_template('tokens_detail.html',
                           token=token,
                           lifecycle=lifecycle,
                           verifications=verifications,
                           devices=devices,
                           anchors=anchors,
                           revocations=revocations,
                           permissions=permissions,
                           v2_signatures=v2_signatures,
                           v2_anchor_batches=v2_anchor_batches,
                           v2_epoch_leaves=v2_epoch_leaves,
                           duress_enrolled=duress_enrolled)


# ============================================================================
# INVESTIGATE — Object Card UX (v9.19)
# ============================================================================
#
# Two routes that render a single-entity *investigation* surface:
#   - /investigate/token/<id>       single token + its chronological timeline
#   - /investigate/individual/<id>  single individual + tokens they hold
#
# Distinct from /tokens/<id> + /individuals/<id> which are OPERATIONAL views
# (current state + edit links). The investigate routes are INVESTIGATIVE —
# they emphasize chronology, related-entity links, and audit-grade history.
#
# Single-entity focused by design. There is NO cross-entity aggregation surface
# (the surveillance pattern is constitutionally refused). Authorized operators
# get context; unauthorized cross-token correlation remains constitutionally
# blocked.
#
# Reads from the v9.19 ontology views (polaris_sql/15_ontology.sql) for the
# semantic data; no new mutation paths.
# ============================================================================

@app.route('/investigate/token/<int:tok_id>')
@security.login_required
def investigate_token(tok_id):
    """Object Card for a single token.

    Renders the token's full chronological timeline (lifecycle + verification
    events unioned via v_ontology_token_timeline) alongside the token's
    semantic record (v_ontology_token) and the holding individual's
    semantic record (v_ontology_individual). Single-entity focused.
    """
    token = query(
        "SELECT * FROM v_ontology_token WHERE token_id = %s",
        (tok_id,), fetch='one',
    )
    if not token:
        abort(404)

    individual = query(
        "SELECT * FROM v_ontology_individual WHERE individual_id = %s",
        (token['individual_id'],), fetch='one',
    )

    # Timeline: lifecycle + verification events chronologically.
    timeline = query("""
        SELECT t.*,
               aa.name AS actor_agency_name,
               ra.name AS requesting_agency_name,
               vc.context_type
          FROM v_ontology_token_timeline t
     LEFT JOIN Agency               aa ON t.actor_agency_id      = aa.agency_id
     LEFT JOIN Agency               ra ON t.requesting_agency_id = ra.agency_id
     LEFT JOIN VerificationContext  vc ON (t.detail_jsonb->>'context_id')::int = vc.context_id
         WHERE t.token_id = %s
      ORDER BY t.event_timestamp DESC, t.event_id DESC
    """, (tok_id,))
    # v9.20 audit-access logging: investigate-token reads TLE + VE.
    # Record both reads; the ontology view unions them so we log both
    # tables the underlying SELECT touched.
    security.record_audit_access(
        get_db, 'TokenLifecycleEvent',
        filter_criteria={'route': '/investigate/token', 'token_id': tok_id},
        result_row_count=sum(1 for r in timeline if r['event_kind'] == 'lifecycle'),
    )
    security.record_audit_access(
        get_db, 'VerificationEvent',
        filter_criteria={'route': '/investigate/token', 'token_id': tok_id},
        result_row_count=sum(1 for r in timeline if r['event_kind'] == 'verification'),
    )

    # Predecessor + successor links (the succession chain)
    predecessor = None
    if token.get('predecessor_token_id'):
        predecessor = query(
            "SELECT token_id, token_value, status, issued_date "
            "FROM v_ontology_token WHERE token_id = %s",
            (token['predecessor_token_id'],), fetch='one',
        )
    successor = query(
        "SELECT token_id, token_value, status, issued_date "
        "FROM v_ontology_token WHERE predecessor_token_id = %s",
        (tok_id,), fetch='one',
    )

    return render_template(
        'investigate_token.html',
        token=token, individual=individual, timeline=timeline,
        predecessor=predecessor, successor=successor,
    )


@app.route('/investigate/individual/<int:ind_id>')
@security.login_required
def investigate_individual(ind_id):
    """Object Card for a single individual.

    Renders the individual's semantic record (v_ontology_individual) +
    every token they have held (v_ontology_individual_tokens) + a summary
    of recent verifications across all their tokens. Single-individual
    focused; no cross-individual aggregation.
    """
    individual = query(
        "SELECT * FROM v_ontology_individual WHERE individual_id = %s",
        (ind_id,), fetch='one',
    )
    if not individual:
        abort(404)

    tokens = query("""
        SELECT *
          FROM v_ontology_individual_tokens
         WHERE individual_id = %s
      ORDER BY activation_sequence DESC, issued_date DESC
    """, (ind_id,))

    # Recent verifications across all this individual's tokens.
    # Bounded LIMIT (C8: hard cap on result sets).
    verifications = query("""
        SELECT v.*, ra.name AS requesting_agency_name, vc.context_type
          FROM v_ontology_verification v
     LEFT JOIN Agency               ra ON v.requesting_agency_id = ra.agency_id
     LEFT JOIN VerificationContext  vc ON v.context_id            = vc.context_id
         WHERE v.individual_id = %s
      ORDER BY v.event_timestamp DESC
         LIMIT 100
    """, (ind_id,))
    # v9.20 audit-access logging: investigate-individual reads VE.
    security.record_audit_access(
        get_db, 'VerificationEvent',
        filter_criteria={'route': '/investigate/individual', 'individual_id': ind_id},
        result_row_count=len(verifications),
    )

    return render_template(
        'investigate_individual.html',
        individual=individual, tokens=tokens,
        verifications=verifications,
    )


@app.route('/tokens/<int:tok_id>/transition', methods=['POST'])
@security.login_required
@security.require_role('admin', 'operator')
@security.csrf_protect
def tokens_transition(tok_id):
    """
    UPDATE a token's status. The state-machine trigger validates the transition;
    the auto-audit AFTER UPDATE trigger writes the TokenLifecycleEvent row
    automatically, eliminating the two-statement race the application used to
    have. We set polaris.actor_agency_id and polaris.reason_code as session
    GUCs so the trigger can write attribution into the audit row.
    """
    new_status = request.form['new_status']
    actor_id = request.form.get('actor_agency_id')  # optional
    reason = request.form.get('reason') or 'WEB_INTERFACE_TRANSITION'

    conn = get_db()
    try:
        with conn.cursor() as cur:
            # SET LOCAL keeps the GUC scoped to this transaction. The audit
            # trigger reads them when it fires AFTER UPDATE.
            if actor_id:
                cur.execute("SELECT set_config('polaris.actor_agency_id', %s, true)",
                            (str(int(actor_id)),))
            cur.execute("SELECT set_config('polaris.reason_code', %s, true)",
                        (reason,))

            # If transitioning to ACTIVE, also set activated_date (the
            # state-machine trigger requires this).
            if new_status == 'ACTIVE':
                cur.execute("""
                    UPDATE IdentityToken
                       SET status=%s, activated_date=CURRENT_TIMESTAMP
                     WHERE token_id=%s
                """, (new_status, tok_id))
            else:
                cur.execute('UPDATE IdentityToken SET status=%s WHERE token_id=%s',
                            (new_status, tok_id))

            conn.commit()
        flash(f'Transitioned token #{tok_id} to {new_status}', 'success')
    except psycopg2.Error as e:
        conn.rollback()
        flash(db_error_to_message(e), 'error')
    finally:
        conn.close()
    return redirect(url_for('tokens_detail', tok_id=tok_id))


@app.route('/tokens/<int:tok_id>/delete', methods=['POST'])
@security.login_required
@security.require_role('admin')
@security.csrf_protect
def tokens_delete(tok_id):
    """
    Tokens are normally never deleted (audit invariant); this is here for
    completeness and will fail if any audit records reference the token.
    """
    try:
        n = query('DELETE FROM IdentityToken WHERE token_id=%s', (tok_id,), fetch='none')
        if n:
            flash(f'Deleted token #{tok_id}', 'success')
        else:
            flash(f'Token #{tok_id} not found', 'error')
    except psycopg2.Error as e:
        flash(db_error_to_message(e), 'error')
    return redirect(url_for('tokens_list'))


# ============================================================================
# UC-1: NEW TOKEN ISSUANCE (uses stored procedure)
# ============================================================================

@app.route('/uc1/issue', methods=['GET', 'POST'])
@security.login_required
@security.require_role('admin', 'operator')
@security.csrf_protect
def uc1_issue():
    """Wraps the uc1_issue_and_activate stored procedure."""
    if request.method == 'POST':
        try:
            contexts = [int(c) for c in request.form.getlist('contexts')]
            # v9.58: the issuance signature comes from the signing module —
            # a real ML-DSA-65 signature when POLARIS_USE_REAL_PQC=1 + liboqs
            # are present, a deterministic SHA3-256 placeholder otherwise —
            # rather than a hardcoded SQL string. Passed as p_signature_bytes.
            sig_bytes, _sig_alg = pqc_signing.signature_bytes_for_token(
                request.form['token_value'])
            new_token_id = query("""
                SELECT uc1_issue_and_activate(
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                ) AS token_id
            """, (
                request.form['legal_name'],
                request.form['date_of_birth'],
                request.form['jurisdiction'],
                int(request.form['issuing_agency_id']),
                int(request.form['algorithm_id']),
                request.form['biometric_binding_type'],
                int(request.form['witness_agency_id']) if request.form.get('witness_agency_id') else None,
                request.form.get('liveness_check_type') or None,
                request.form['token_value'],
                request.form['physical_serial'],
                request.form.get('hardware_model') or None,
                contexts,
                psycopg2.Binary(sig_bytes),
            ), fetch='returning')['token_id']  # 'returning' commits the transaction
            flash(f'Issued and activated token #{new_token_id}', 'success')
            return redirect(url_for('tokens_detail', tok_id=new_token_id))
        except pqc_signing.PQCUnavailableError as e:
            flash(f'Issuance blocked: {e}', 'error')
        except (psycopg2.Error, ValueError, KeyError) as e:
            flash(db_error_to_message(e), 'error')

    agencies = query("SELECT * FROM Agency WHERE authorization_level >= 4 ORDER BY agency_id")
    algorithms = query("SELECT * FROM CryptographicAlgorithm WHERE quantum_resistant = TRUE ORDER BY algorithm_id")
    contexts = query("SELECT * FROM VerificationContext ORDER BY context_id")
    return render_template('uc1_issue.html',
                           agencies=agencies,
                           algorithms=algorithms,
                           contexts=contexts)


# ============================================================================
# UC-4: RESERVE ACTIVATION (uses stored procedure)
# ============================================================================

@app.route('/uc4/activate-reserve', methods=['GET', 'POST'])
@security.login_required
@security.require_role('admin', 'operator')
@security.csrf_protect
def uc4_activate_reserve():
    """Wraps the uc4_activate_reserve stored procedure."""
    if request.method == 'POST':
        try:
            promoted = query("""
                SELECT uc4_activate_reserve(%s, %s, %s, %s, %s) AS token_id
            """, (
                int(request.form['lost_token_id']),
                int(request.form['actor_agency_id']),
                request.form['reason_code'],
                int(request.form['reserve_token_id']),
                request.form['published_location'],
            ), fetch='returning')['token_id']  # 'returning' commits
            flash(f'Activated reserve token #{promoted}', 'success')
            return redirect(url_for('tokens_detail', tok_id=promoted))
        except (psycopg2.Error, ValueError) as e:
            flash(db_error_to_message(e), 'error')

    active_tokens = query("""
        SELECT t.token_id, i.legal_name, t.token_value
        FROM   IdentityToken t JOIN Individual i ON t.individual_id = i.individual_id
        WHERE  t.status = 'ACTIVE'
        ORDER BY t.token_id
    """)
    reserve_tokens = query("""
        SELECT t.token_id, i.legal_name, t.token_value
        FROM   IdentityToken t JOIN Individual i ON t.individual_id = i.individual_id
        WHERE  t.status = 'RESERVE'
        ORDER BY t.token_id
    """)
    agencies = query("SELECT * FROM Agency ORDER BY agency_id")
    return render_template('uc4_activate.html',
                           active_tokens=active_tokens,
                           reserve_tokens=reserve_tokens,
                           agencies=agencies)


# ============================================================================
# UC-5: DEVICE BINDING (uses stored procedure)
# ============================================================================

@app.route('/uc5/bind-device', methods=['GET', 'POST'])
@security.login_required
@security.require_role('admin', 'operator')
@security.csrf_protect
def uc5_bind_device():
    """Wraps the uc5_bind_device stored procedure."""
    if request.method == 'POST':
        try:
            binding_id = query("""
                SELECT uc5_bind_device(%s, %s, %s, %s, %s) AS binding_id
            """, (
                int(request.form['token_id']),
                request.form['device_type'],
                request.form['device_fingerprint'],
                request.form['binding_method'],
                int(request.form.get('validity_months', 12)),
            ), fetch='returning')['binding_id']  # 'returning' commits
            flash(f'Created device binding #{binding_id}', 'success')
            return redirect(url_for('tokens_detail', tok_id=int(request.form['token_id'])))
        except (psycopg2.Error, ValueError) as e:
            flash(db_error_to_message(e), 'error')

    active_tokens = query("""
        SELECT t.token_id, i.legal_name, t.token_value
        FROM   IdentityToken t JOIN Individual i ON t.individual_id = i.individual_id
        WHERE  t.status = 'ACTIVE'
        ORDER BY t.token_id
    """)
    return render_template('uc5_bind.html', active_tokens=active_tokens)


# ============================================================================
# UC-7: WARRANT-AUTHORIZED VERIFICATION HISTORY (uses stored procedure)
# ============================================================================

@app.route('/uc7/warrant-audit', methods=['GET', 'POST'])
@security.login_required
@security.require_role('admin', 'auditor')
@security.csrf_protect
def uc7_warrant_audit():
    """Wraps the uc7_warrant_audit stored procedure with disclosure-aware redaction."""
    results = None
    individual_id = None
    if request.method == 'POST':
        try:
            individual_id = int(request.form['individual_id'])
            results = query("""
                SELECT * FROM uc7_warrant_audit(%s, %s, %s, %s)
                ORDER BY event_timestamp
            """, (
                individual_id,
                request.form.get('window_start') or '1970-01-01 00:00:00',
                request.form.get('window_end')   or '2099-12-31 23:59:59',
                request.form.get('context_filter') or None,
            ))
        except (psycopg2.Error, ValueError) as e:
            flash(db_error_to_message(e), 'error')

    individuals = query("SELECT * FROM Individual ORDER BY individual_id")
    return render_template('uc7_warrant.html',
                           individuals=individuals,
                           results=results,
                           individual_id=individual_id)


# ============================================================================
# UC-8: BOUNDED REVOCATION (R11-6 / M2-11)
#   The single sanctioned revocation path. Enforces the per-agency rolling
#   N%/W-day rate bound; over the bound a co-signer is required.
#   The procedure also publishes to RevocationList in the same transaction.
# ============================================================================

@app.route('/uc8/revoke', methods=['GET', 'POST'])
@security.login_required
@security.require_role('admin', 'operator')
@security.csrf_protect
def uc8_revoke():
    """Wraps the uc8_revoke_token stored procedure."""
    if request.method == 'POST':
        try:
            token_id = int(request.form['token_id'])
            actor_agency_id = int(request.form['actor_agency_id'])
            cosigner_raw = (request.form.get('cosigner_agency_id') or '').strip()
            cosigner_agency_id = int(cosigner_raw) if cosigner_raw else None

            # CALL form for procedures (vs SELECT for functions). The
            # procedure modifies token status + audit row + RevocationList
            # in one transaction; commit explicitly after CALL succeeds.
            conn = get_db()
            try:
                with conn.cursor() as cur:
                    cur.execute("""
                        CALL uc8_revoke_token(%s, %s, %s, %s, %s)
                    """, (
                        token_id,
                        actor_agency_id,
                        request.form['reason_code'],
                        request.form['published_location'],
                        cosigner_agency_id,
                    ))
                conn.commit()
            finally:
                conn.close()
            flash(
                f'Revoked token #{token_id}'
                + (' with co-signer' if cosigner_agency_id else ''),
                'success')
            return redirect(url_for('tokens_detail', tok_id=token_id))
        except (psycopg2.Error, ValueError) as e:
            flash(db_error_to_message(e), 'error')

    active_tokens = query("""
        SELECT t.token_id, i.legal_name, t.token_value,
               t.issuing_agency_id, ag.name AS issuing_agency_name,
               ca.name AS algorithm_name, t.algorithm_id
        FROM   IdentityToken t
        JOIN   Individual              i  ON t.individual_id = i.individual_id
        JOIN   Agency                  ag ON t.issuing_agency_id = ag.agency_id
        JOIN   CryptographicAlgorithm  ca ON t.algorithm_id = ca.algorithm_id
        WHERE  t.status = 'ACTIVE'
        ORDER BY t.token_id
    """)
    agencies = query("""
        SELECT agency_id, name, agency_type FROM Agency ORDER BY agency_id
    """)
    return render_template('uc8_revoke.html',
                           active_tokens=active_tokens,
                           agencies=agencies)


# ============================================================================
# UC-9: CATASTROPHIC-LOSS RECOVERY (R11-2 / M2-7)
#
# Two-phase out-of-band ceremony. Operator initiates a PENDING request;
# admin reviews and decides (APPROVED or REJECTED) after the 48h cool-down.
# Implements PDF §9.1 catastrophic-loss-risk open problem.
# ============================================================================

@app.route('/uc9/initiate-recovery', methods=['GET', 'POST'])
@security.login_required
@security.require_role('admin', 'operator')
@security.csrf_protect
def uc9_initiate():
    """Phase 1 of UC-9: open a PENDING RecoveryRequest."""
    if request.method == 'POST':
        try:
            individual_id = int(request.form['individual_id'])
            agency_id = int(request.form['requesting_agency_id'])

            conn = get_db()
            try:
                with conn.cursor() as cur:
                    cur.execute("""
                        CALL uc9_initiate_recovery(%s, %s, %s, %s)
                    """, (
                        individual_id, agency_id,
                        session.get('user_id'), 48,
                    ))
                conn.commit()
            finally:
                conn.close()
            flash(
                f'Recovery request opened for individual #{individual_id}. '
                'Cool-down: 48 hours.',
                'success')
            return redirect(url_for('uc9_queue'))
        except (psycopg2.Error, ValueError) as e:
            flash(db_error_to_message(e), 'error')

    # Build the form. Individuals without an ACTIVE token are the legitimate
    # candidates for recovery (UC-4 is the right path otherwise).
    individuals = query("""
        SELECT i.individual_id, i.legal_name, i.jurisdiction,
               COALESCE(ice.current_status, 'NOT_ENROLLED') AS enrollment_status
        FROM   Individual i
        LEFT JOIN IndividualCurrentEnrollment ice
               ON i.individual_id = ice.individual_id
        WHERE  NOT EXISTS (
                 SELECT 1 FROM IdentityToken t
                 WHERE t.individual_id = i.individual_id AND t.status='ACTIVE')
        ORDER BY i.individual_id
    """)
    agencies = query("""
        SELECT agency_id, name, agency_type FROM Agency ORDER BY agency_id
    """)
    return render_template('uc9_initiate.html',
                           individuals=individuals,
                           agencies=agencies)


@app.route('/uc9/queue')
@security.login_required
def uc9_queue():
    """Read-only queue of PENDING (and recent terminal) recovery requests.
    Any authenticated role can view; only admin can decide."""
    rows = query("""
        SELECT r.recovery_id, r.claimed_individual_id, i.legal_name,
               r.requested_at, r.cooldown_expires_at, r.status,
               r.requesting_agency_id, a.name AS requesting_agency_name,
               r.requesting_user_id, ru.username AS requesting_username,
               r.biometric_verified,
               r.sworn_statement_hash IS NOT NULL AS sworn_statement_present,
               r.witness_agency_id IS NOT NULL AS witness_present,
               r.decided_at, r.decided_by_user_id,
               du.username AS decided_by_username,
               CURRENT_TIMESTAMP >= r.cooldown_expires_at AS cooldown_passed
        FROM   RecoveryRequest r
        JOIN   Individual i ON r.claimed_individual_id = i.individual_id
        JOIN   Agency     a ON r.requesting_agency_id  = a.agency_id
        JOIN   AppUser    ru ON r.requesting_user_id   = ru.user_id
        LEFT JOIN AppUser du ON r.decided_by_user_id   = du.user_id
        ORDER BY CASE r.status WHEN 'PENDING' THEN 0 ELSE 1 END,
                 r.recovery_id DESC
    """)
    return render_template('uc9_queue.html', rows=rows)


@app.route('/uc9/decide/<int:recovery_id>', methods=['GET', 'POST'])
@security.login_required
@security.require_role('admin')
@security.csrf_protect
def uc9_decide(recovery_id):
    """Phase 2 of UC-9: admin decision (APPROVED or REJECTED) on a PENDING
    request. Admin-only — operator can initiate but not complete; auditor
    can view the queue but not act."""
    if request.method == 'POST':
        try:
            decision = request.form['decision']
            reason = (request.form.get('reason') or '').strip()
            if decision not in ('APPROVED', 'REJECTED'):
                raise ValueError('Decision must be APPROVED or REJECTED')

            new_token_value = (request.form.get('new_token_value') or '').strip() or None
            new_serial      = (request.form.get('new_serial')      or '').strip() or None
            algorithm_raw   = (request.form.get('algorithm_id')    or '').strip()
            algorithm_id    = int(algorithm_raw) if algorithm_raw else None
            biometric_binding = (request.form.get('biometric_binding') or '').strip() or None
            liveness_check    = (request.form.get('liveness_check')    or '').strip() or None
            published_location = (request.form.get('published_location') or '').strip() or None

            conn = get_db()
            try:
                with conn.cursor() as cur:
                    cur.execute("""
                        CALL uc9_complete_recovery(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        recovery_id, session.get('user_id'), decision, reason,
                        new_token_value, new_serial, algorithm_id,
                        biometric_binding, liveness_check, published_location,
                    ))
                conn.commit()
            finally:
                conn.close()

            flash(f'Recovery #{recovery_id} marked {decision}.', 'success')
            return redirect(url_for('uc9_queue'))
        except (psycopg2.Error, ValueError) as e:
            flash(db_error_to_message(e), 'error')

    req = query("""
        SELECT r.*, i.legal_name, a.name AS requesting_agency_name,
               wa.name AS witness_agency_name,
               ru.username AS requesting_username,
               CURRENT_TIMESTAMP >= r.cooldown_expires_at AS cooldown_passed,
               (r.biometric_verified
                AND r.sworn_statement_hash IS NOT NULL
                AND r.witness_agency_id IS NOT NULL
                AND r.witness_co_sign_user_id IS NOT NULL) AS three_channels_present
        FROM   RecoveryRequest r
        JOIN   Individual i  ON r.claimed_individual_id = i.individual_id
        JOIN   Agency     a  ON r.requesting_agency_id  = a.agency_id
        LEFT JOIN Agency  wa ON r.witness_agency_id     = wa.agency_id
        JOIN   AppUser    ru ON r.requesting_user_id    = ru.user_id
        WHERE  r.recovery_id = %s
    """, (recovery_id,), fetch='one')
    if not req:
        flash(f'Recovery #{recovery_id} not found', 'error')
        return redirect(url_for('uc9_queue'))

    algorithms = query("""
        SELECT algorithm_id, name, quantum_resistant
        FROM CryptographicAlgorithm
        WHERE deprecation_date IS NULL OR deprecation_date > CURRENT_DATE
        ORDER BY algorithm_id
    """)
    return render_template('uc9_decide.html', req=req, algorithms=algorithms)


# ============================================================================
# UC-6: ALGORITHM MIGRATION (R11-1 / M2-6)
#
# Multi-signature transitional state: a token can carry signatures from
# multiple algorithms during a migration window. UC-6 adds a new signature
# under a new algorithm and optionally deprecates the old one. The
# TokenSignature row IS the audit-of-record for the migration.
# ============================================================================

@app.route('/uc6/migrate', methods=['GET', 'POST'])
@security.login_required
@security.require_role('admin', 'operator')
@security.csrf_protect
def uc6_migrate():
    """Migrate a token to a new algorithm — add a new TokenSignature row,
    optionally deprecate the old."""
    if request.method == 'POST':
        try:
            token_id = int(request.form['token_id'])
            new_algorithm = int(request.form['new_algorithm'])
            deprecate_old = bool(request.form.get('deprecate_old'))

            # Placeholder signature_bytes for the reference implementation.
            # Production would derive these from a hardware-attested signing
            # ceremony external to the database.
            sig_bytes = f"UC6_OPERATOR_MIGRATE_{token_id}_{new_algorithm}".encode()

            conn = get_db()
            try:
                with conn.cursor() as cur:
                    cur.execute("""
                        CALL uc6_migrate_algorithm(%s, %s, %s, %s)
                    """, (token_id, new_algorithm, sig_bytes, deprecate_old))
                conn.commit()
            finally:
                conn.close()

            flash(
                f'Migrated token #{token_id} to algorithm #{new_algorithm}'
                + (' (old deprecated)' if deprecate_old else ''),
                'success')
            return redirect(url_for('tokens_detail', tok_id=token_id))
        except (psycopg2.Error, ValueError) as e:
            flash(db_error_to_message(e), 'error')

    tokens = query("""
        SELECT t.token_id, t.token_value, t.status,
               i.legal_name,
               ag.name AS issuing_agency_name,
               ARRAY(SELECT alg.name FROM TokenSignature s
                     JOIN CryptographicAlgorithm alg ON s.algorithm_id = alg.algorithm_id
                     WHERE s.token_id = t.token_id
                       AND s.deprecation_date IS NULL
                     ORDER BY alg.algorithm_id) AS active_algorithms
        FROM IdentityToken t
        JOIN Individual i  ON t.individual_id     = i.individual_id
        JOIN Agency     ag ON t.issuing_agency_id = ag.agency_id
        WHERE t.status IN ('RESERVE','ACTIVE')
        ORDER BY t.token_id
    """)
    algorithms = query("""
        SELECT algorithm_id, name, quantum_resistant
        FROM CryptographicAlgorithm
        WHERE deprecation_date IS NULL OR deprecation_date > CURRENT_DATE
        ORDER BY algorithm_id
    """)
    return render_template('uc6_migrate.html',
                           tokens=tokens,
                           algorithms=algorithms)


# ============================================================================
# VERIFICATION EVENT QUERY (read-only browser for the high-volume table)
# ============================================================================

@app.route('/verifications')
@security.login_required
def verifications_list():
    """
    Browse VerificationEvent with filters. UPDATE/DELETE not exposed
    because the append-only trigger forbids them anyway.

    Pagination (R7-3, v7): two modes, identical to /tokens but with a
    composite cursor.
      - Cursor mode: sort key is (event_timestamp DESC, event_id DESC).
        Single-column would not be safe — the schema permits two events
        with the same timestamp distinguished only by event_id, so the
        cursor encodes both as 'isoformat~event_id'. Row-value comparison
        '(ts, id) < cursor' rides the idx_verificationevent_time_id index
        directly, keeping per-page cost O(log n + page_size).
      - Page mode (legacy): ?page=N, OFFSET-bound. Slow at depth.
      Cursor params take precedence over page when both are supplied.
    """
    context    = request.args.get('context', '')
    outcome    = request.args.get('outcome', '')
    disclosure = request.args.get('disclosure', '')
    # See note on tokens_list: floor=1, cap=500.
    page_size  = min(500, max(1, int(request.args.get('page_size', '100'))))

    cursor_raw      = request.args.get('cursor')
    prev_cursor_raw = request.args.get('prev_cursor')
    cursor_mode = (cursor_raw is not None) or (prev_cursor_raw is not None)
    cursor      = _parse_cursor_composite(cursor_raw)
    prev_cursor = _parse_cursor_composite(prev_cursor_raw)

    where_sql = ''
    params = []
    if context:
        where_sql += ' AND vc.context_type = %s'
        params.append(context)
    if outcome:
        where_sql += ' AND ve.outcome = %s'
        params.append(outcome)
    if disclosure:
        where_sql += ' AND ve.disclosure_level = %s'
        params.append(disclosure)

    # C6: ZERO_KNOWLEDGE verifications must not reveal their location on ANY read
    # path. uc7_warrant_audit redacts requestor_location for ZK rows; this list
    # (any authenticated user, no role gate) must do the same, so it projects an
    # explicit column set with the same CASE rather than `ve.*` (which would leak
    # requestor_location, latitude, longitude). holder_name is already NULL for ZK
    # because token_id is NULL (C2), so the IdentityToken/Individual join yields
    # nothing identifying.
    base_select = """
        SELECT ve.event_id, ve.event_timestamp, ve.outcome, ve.disclosure_level,
               CASE WHEN ve.disclosure_level = 'ZERO_KNOWLEDGE'
                    THEN NULL ELSE ve.requestor_location END AS requestor_location,
               vc.context_type,
               ag.name AS verifier_name,
               i.legal_name AS holder_name
        FROM   VerificationEvent ve
        JOIN   VerificationContext vc ON ve.context_id = vc.context_id
        JOIN   Agency ag              ON ve.requesting_agency_id = ag.agency_id
        LEFT JOIN IdentityToken t     ON ve.token_id = t.token_id
        LEFT JOIN Individual i        ON t.individual_id = i.individual_id
        WHERE  TRUE """

    contexts = query('SELECT * FROM VerificationContext ORDER BY context_type')

    if cursor_mode:
        if prev_cursor is not None:
            # Walk backward in display order: rows with key > prev_cursor.
            # Pull in ASC, reverse for display.
            ts, eid = prev_cursor
            sql = base_select + where_sql + (
                " AND (ve.event_timestamp, ve.event_id) > (%s, %s)"
                " ORDER BY ve.event_timestamp ASC, ve.event_id ASC LIMIT %s")
            rows = query(sql, params + [ts, eid, page_size + 1])
            has_prev = len(rows) > page_size
            rows = rows[:page_size]
            rows.reverse()
            has_next = True
        else:
            cursor_sql = ''
            cursor_param = []
            if cursor is not None:
                ts, eid = cursor
                cursor_sql = " AND (ve.event_timestamp, ve.event_id) < (%s, %s)"
                cursor_param = [ts, eid]
            sql = base_select + where_sql + cursor_sql + (
                " ORDER BY ve.event_timestamp DESC, ve.event_id DESC LIMIT %s")
            rows = query(sql, params + cursor_param + [page_size + 1])
            has_next = len(rows) > page_size
            rows = rows[:page_size]
            if cursor is not None and rows:
                # Probe: any row with key > first visible row's key?
                first_ts = rows[0]['event_timestamp']
                first_id = rows[0]['event_id']
                probe = query(
                    "SELECT 1 FROM VerificationEvent ve "
                    "JOIN VerificationContext vc ON ve.context_id = vc.context_id "
                    "WHERE TRUE " + where_sql +
                    " AND (ve.event_timestamp, ve.event_id) > (%s, %s) LIMIT 1",
                    params + [first_ts, first_id], fetch='one')
                has_prev = probe is not None
            else:
                has_prev = False

        first_cursor = (_format_cursor_composite(rows[0]['event_timestamp'],
                                                 rows[0]['event_id'])
                        if rows else None)
        last_cursor  = (_format_cursor_composite(rows[-1]['event_timestamp'],
                                                 rows[-1]['event_id'])
                        if rows else None)

        # v9.20 audit-access logging on the cursor-mode branch.
        security.record_audit_access(
            get_db, 'VerificationEvent',
            filter_criteria={
                'route': '/verifications', 'mode': 'cursor',
                'context': context, 'outcome': outcome,
                'disclosure': disclosure, 'page_size': page_size,
            },
            result_row_count=len(rows),
        )
        return render_template('verifications_list.html',
                               rows=rows,
                               contexts=contexts,
                               context=context,
                               outcome=outcome,
                               disclosure=disclosure,
                               page=None,
                               page_size=page_size,
                               cursor_mode=True,
                               first_cursor=first_cursor,
                               last_cursor=last_cursor,
                               has_next=has_next,
                               has_prev=has_prev)

    page   = max(1, int(request.args.get('page', '1')))
    offset = (page - 1) * page_size
    sql = base_select + where_sql + (
        " ORDER BY ve.event_timestamp DESC, ve.event_id DESC LIMIT %s OFFSET %s")
    rows = query(sql, params + [page_size + 1, offset])
    has_next = len(rows) > page_size
    rows = rows[:page_size]

    # v9.20 audit-access logging on the page-mode branch.
    security.record_audit_access(
        get_db, 'VerificationEvent',
        filter_criteria={
            'route': '/verifications', 'mode': 'page',
            'context': context, 'outcome': outcome,
            'disclosure': disclosure, 'page': page,
            'page_size': page_size,
        },
        result_row_count=len(rows),
    )
    return render_template('verifications_list.html',
                           rows=rows,
                           contexts=contexts,
                           context=context,
                           outcome=outcome,
                           disclosure=disclosure,
                           page=page,
                           page_size=page_size,
                           cursor_mode=False,
                           has_next=has_next,
                           has_prev=page > 1)


def _federation_trust_holds(verifier_agency_id, token_id, context_id):
    """Returns True if the verifier_agency_id is allowed to verify token_id in
    context_id under the federation trust graph. Same-agency verification is
    always permitted (implicit trust). Cross-agency verification requires an
    active (unrevoked, unexpired) attestation row.

    NO transitive trust: this function looks for exactly one row in
    AgencyTrustAttestation; it does not recurse. R1 audit refinement from
    proposals/R11-3-issuer-federation.md.

    Returns True for missing data (no token, ZK event) — federation only
    applies when there's a concrete (verifier, issuer, context) triple.
    """
    if token_id is None:
        return True  # ZERO_KNOWLEDGE event has no token / no issuer
    row = query("""
        SELECT t.issuing_agency_id
          FROM IdentityToken t
         WHERE t.token_id = %s
    """, (token_id,), fetch='one')
    if not row:
        return True  # let the FK fail downstream with a proper error
    issuer_id = row['issuing_agency_id']
    if verifier_agency_id == issuer_id:
        return True  # same-agency: implicit trust
    match = query("""
        SELECT 1
          FROM AgencyTrustAttestation
         WHERE attesting_agency_id = %s
           AND attested_agency_id  = %s
           AND context_id          = %s
           AND revocation_date IS NULL
           AND valid_until >= CURRENT_DATE
         LIMIT 1
    """, (verifier_agency_id, issuer_id, context_id), fetch='one')
    return match is not None


def _record_duress_async(token_id, context_id, requesting_agency_id):
    """Write the silent DuressEvent + bump the operator alert counter. Runs on a
    background daemon thread by default (see _check_and_record_duress) so the
    request's response latency does not depend on whether a duress code matched.
    Self-contained (fresh connection, no Flask context); best-effort and never
    raises into the caller — the coercer must never see a duress recording fail."""
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "CALL uc12_record_duress(%s, %s, %s, %s)",
                (token_id, context_id, requesting_agency_id, 'AUDIT_TABLE'),
            )
            conn.commit()
        try:
            observability.record_duress_event(
                individual_id=token_id, agency_id=requesting_agency_id)
        except Exception:
            pass
    except psycopg2.Error:
        conn.rollback()
        sys.stderr.write(f"DURESS RECORD FAILED for token_id={token_id}\n")
    finally:
        conn.close()


def _check_and_record_duress(token_id, context_id, requesting_agency_id, duress_input):
    """R11-5 / M2-10: compulsion-resistance check (PDF §9.5).

    If the token has an enrolled duress_code_hash AND the supplied
    duress_input matches it via Werkzeug's constant-time
    check_password_hash, record a silent DuressEvent via the
    uc12_record_duress procedure.

    R1 audit refinement: check_password_hash IS the constant-time
    comparison; the timing-attack-resistance is delegated to the
    same primitive that validates AppUser passwords.

    R2 audit refinement: regardless of match/no-match/no-enrollment,
    this helper returns nothing and the caller's verification flow
    proceeds identically. The earlier claim that timing variance was
    "dominated by Flask overhead" understated the cost — the match branch
    opened a SECOND connection and committed (a WAL fsync), a
    deterministic added latency a coercer could measure. The recording
    now runs off the request thread (see the match branch below), so the
    synchronous response time no longer depends on the match outcome.

    Returns nothing — duress is silent by design.
    """
    if not duress_input:
        return
    row = query(
        "SELECT duress_code_hash FROM IdentityToken WHERE token_id = %s",
        (token_id,), fetch='one'
    )
    if not row or not row['duress_code_hash']:
        return
    # Constant-time hash comparison. This is the same primitive used
    # for AppUser password validation in security.py (lines 392, 427, 449).
    if not check_password_hash(row['duress_code_hash'], duress_input):
        return
    # MATCH — record the silent alert OFF the request thread by default, so the
    # synchronous response latency is identical to a non-match. The recording
    # opens a second connection and commits (a WAL fsync) — a deterministic,
    # measurable cost; doing it on the request thread let a coercer who timed the
    # response distinguish a duress code from a real one. Moving it to a daemon
    # thread removes that signal (the request returns after a microsecond-scale
    # thread spawn regardless of outcome). Operators who prefer the alarm to be
    # committed before the response returns (durability over the timing property)
    # set POLARIS_DURESS_SYNC=1; tests use it for deterministic assertions.
    if os.environ.get('POLARIS_DURESS_SYNC') == '1':
        _record_duress_async(token_id, context_id, requesting_agency_id)
    else:
        threading.Thread(
            target=_record_duress_async,
            args=(token_id, context_id, requesting_agency_id),
            daemon=True,
        ).start()


@app.route('/verifications/new', methods=['GET', 'POST'])
@security.login_required
@security.require_role('admin', 'operator')
@security.csrf_protect
def verifications_new():
    """
    Append a verification event. The disclosure-consistency CHECK constraint
    enforces: ZERO_KNOWLEDGE -> token_id NULL, FULL -> token_id NOT NULL.

    R11-3: SUCCESS outcomes are gated by the federation trust graph — a
    verifier cannot legitimately record SUCCESS on a token whose issuing
    agency it does not trust for the given context.
    """
    if request.method == 'POST':
        try:
            disclosure = request.form['disclosure_level']
            token_id = request.form.get('token_id')
            # Coerce empty/zero to NULL for ZERO_KNOWLEDGE; let constraint check anything else
            if disclosure == 'ZERO_KNOWLEDGE' or not token_id:
                token_id_val = None
            else:
                token_id_val = int(token_id)

            verifier_id = int(request.form['requesting_agency_id'])
            context_id = int(request.form['context_id'])
            outcome = request.form['outcome']

            # R11-3 federation check: only gates SUCCESS outcomes. FAILURE,
            # UNAUTHORIZED, EXPIRED already represent denied verifications;
            # blocking those would prevent the audit log from recording them.
            if outcome == 'SUCCESS' and not _federation_trust_holds(
                    verifier_id, token_id_val, context_id):
                flash(
                    'Federation trust missing: verifier agency has no active '
                    'attestation toward the token\'s issuing agency for this '
                    'context. Either record outcome=UNAUTHORIZED, or create '
                    'the attestation via /api/federation/attest first.',
                    'error')
                return redirect(url_for('verifications_new'))

            # R11-5 / M2-10 duress-code check (compulsion resistance, PDF §9.5).
            # If a duress_code is supplied AND the token has an enrolled
            # duress_code_hash AND check_password_hash returns true (constant-
            # time comparison), record a silent DuressEvent. The coercer-visible
            # verification flow proceeds normally — the outcome below is recorded
            # as whatever was requested.
            #
            # Duress is inherently TOKEN-BOUND: the silent alarm has to identify
            # the token to look up its enrolled duress_code_hash. A pure
            # ZERO_KNOWLEDGE verification deliberately does NOT reveal the token to
            # the verifier (token_id_val is None here), so a duress code cannot be
            # tied to a token without breaking the ZK property — the duress field
            # therefore has no effect on ZK flows (and the form labels it as
            # requiring a token reference, so a holder is not given false
            # assurance). This is a deliberate limitation, not a silent drop.
            duress_input = request.form.get('duress_code') or ''
            if token_id_val is not None and duress_input:
                _check_and_record_duress(token_id_val, context_id, verifier_id,
                                         duress_input)

            # v9.20 verification-purpose lineage (Sanctum:
            # a recorded decision
            # Position A). Operator-supplied free-text reason for THIS
            # verification. NULL = no purpose supplied (legacy paths +
            # ZERO_KNOWLEDGE flows without operator-provided context).
            # CHECK in the migration enforces 1..280 chars when present.
            purpose_text = request.form.get('requesting_purpose_text', '').strip()
            purpose_text_val = purpose_text if purpose_text else None

            event_id = query("""
                INSERT INTO VerificationEvent
                    (token_id, requesting_agency_id, context_id, outcome,
                     disclosure_level, proof_commitment, requestor_location,
                     requesting_purpose_text)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING event_id
            """, (
                token_id_val,
                verifier_id,
                context_id,
                outcome,
                disclosure,
                request.form.get('proof_commitment') or None,
                request.form.get('requestor_location') or None,
                purpose_text_val,
            ), fetch='returning')['event_id']
            flash(f'Recorded verification event #{event_id}', 'success')
            return redirect(url_for('verifications_list'))
        except (psycopg2.Error, ValueError) as e:
            flash(db_error_to_message(e), 'error')

    tokens = query("""
        SELECT t.token_id, i.legal_name, t.token_value, t.status
        FROM   IdentityToken t JOIN Individual i ON t.individual_id = i.individual_id
        ORDER BY t.token_id
    """)
    agencies = query('SELECT * FROM Agency ORDER BY agency_id')
    contexts = query('SELECT * FROM VerificationContext ORDER BY context_id')
    return render_template('verifications_form.html',
                           tokens=tokens,
                           agencies=agencies,
                           contexts=contexts)


# ============================================================================
# RAW SQL QUERY INTERFACE (read-only)
# ============================================================================

@app.route('/sql', methods=['GET', 'POST'])
@security.login_required
@security.require_role('admin', 'auditor')
@security.csrf_protect
def sql_query():
    """
    Read-only SQL console. The polaris_app role only has SELECT/INSERT/UPDATE/DELETE,
    not DDL, so users can't drop tables. We additionally refuse anything that's
    not a SELECT to keep this strictly read-only from this page.

    Hardening:
        - Query length capped at 5000 chars to prevent pasting huge payloads
        - Statement timeout of 5 seconds so a runaway query can't hang the worker
        - The session is set READ ONLY (`set_session(readonly=True)`) before any
          statement opens a transaction, so the engine itself refuses every write.
          This is the real boundary: the first-keyword whitelist below is only a
          friendly early error, and it is bypassable by a data-modifying CTE
          (`WITH t AS (DELETE ... RETURNING *) SELECT * FROM t` starts with WITH).
          The read-only session makes Postgres reject that CTE with "cannot
          execute DELETE in a read-only transaction" regardless.
        - Whitelist on first keyword (SELECT or WITH only) — UX, not security
        - EXPLAIN ANALYZE button surfaces query plans (still read-only)
    """
    SQL_MAX_LENGTH = 5000
    SQL_TIMEOUT_MS = 5000  # 5 seconds

    results = None
    columns = None
    error = None
    explain_mode = bool(request.form.get('explain'))
    sql = request.form.get('sql', '') if request.method == 'POST' else ''

    if request.method == 'POST' and sql.strip():
        # Length check first - cheap to evaluate, prevents pathological inputs
        if len(sql) > SQL_MAX_LENGTH:
            error = (f"Query length {len(sql)} exceeds the {SQL_MAX_LENGTH}-character limit. "
                     f"Save complex queries as stored procedures instead.")
        else:
            # Whitelist: must start with SELECT or WITH
            first_word = sql.strip().split()[0].upper() if sql.strip() else ''
            if first_word not in ('SELECT', 'WITH'):
                error = "This console is read-only. Only SELECT and WITH queries are accepted."
            else:
                conn = None
                try:
                    # Use a plain cursor here (NOT RealDictCursor) so cur.fetchall()
                    # returns tuples we can zip with column names.
                    conn = psycopg2.connect(**DB_CONFIG)
                    # The security boundary: make the whole session read-only at
                    # the engine level, BEFORE any statement opens a transaction.
                    # `set_session(readonly=True)` must be issued outside a
                    # transaction, so it goes here, immediately after connect and
                    # before the first execute — `SET default_transaction_read_only`
                    # issued mid-transaction would NOT bind the query's own
                    # (already-started) transaction. Now any write — including one
                    # smuggled past the first-keyword whitelist via a data-modifying
                    # CTE (`WITH t AS (DELETE ... RETURNING *) SELECT * FROM t`) — is
                    # refused by Postgres ("cannot execute DELETE in a read-only
                    # transaction"), not just discouraged by the keyword gate.
                    conn.set_session(readonly=True)
                    # Set statement_timeout BEFORE starting our query. SET of a
                    # runtime parameter is permitted inside a read-only transaction;
                    # it lasts until this connection closes — scoped to the request.
                    with conn.cursor() as cur:
                        cur.execute(f"SET statement_timeout = {SQL_TIMEOUT_MS}")

                        # If EXPLAIN ANALYZE was requested, wrap the query
                        actual_sql = f"EXPLAIN ANALYZE {sql}" if explain_mode else sql
                        cur.execute(actual_sql)

                        if cur.description:
                            columns = [c.name for c in cur.description]
                            results = [dict(zip(columns, row)) for row in cur.fetchall()]
                        else:
                            error = "Query returned no result set."
                except psycopg2.errors.QueryCanceled:
                    error = (f"Query timed out after {SQL_TIMEOUT_MS}ms. "
                             f"Add LIMIT, narrow WHERE conditions, or use the appropriate index.")
                except psycopg2.Error as e:
                    error = db_error_to_message(e)
                finally:
                    # F-10 patch: always rollback any partial transaction and
                    # close the connection. Without this, a failed query could
                    # leave the connection in 'aborted' state for any subsequent
                    # request that picked it up (only relevant if we ever pool
                    # connections, but the discipline matters either way).
                    if conn is not None:
                        try:
                            conn.rollback()
                        except Exception:
                            pass
                        conn.close()

    examples = [
        ("Active tokens with PQ algorithms (Q2)",
         "SELECT t.token_id, i.legal_name, alg.name AS algorithm\n"
         "FROM IdentityToken t\n"
         "JOIN Individual i ON t.individual_id = i.individual_id\n"
         "JOIN CryptographicAlgorithm alg ON t.algorithm_id = alg.algorithm_id\n"
         "WHERE alg.quantum_resistant = TRUE AND t.status = 'ACTIVE'\n"
         "ORDER BY t.token_id;"),
        ("Verification volume by context (Q5)",
         "SELECT vc.context_type, COUNT(ve.event_id) AS vol\n"
         "FROM VerificationEvent ve\n"
         "JOIN VerificationContext vc ON ve.context_id = vc.context_id\n"
         "GROUP BY vc.context_type\n"
         "ORDER BY vol DESC;"),
        ("Agencies with BOTH grants on ML-DSA-65 (Q3)",
         "SELECT ag.name, ag.jurisdiction\n"
         "FROM CryptographicAlgorithm CA\n"
         "JOIN AgencyAlgorithmAuth aaa ON CA.algorithm_id = aaa.algorithm_id\n"
         "JOIN Agency ag ON aaa.agency_id = ag.agency_id\n"
         "WHERE CA.name = 'ML-DSA-65' AND aaa.authorization_type = 'BOTH';"),
        ("Token succession lineage (Q6)",
         "SELECT t1.token_id AS current_token,\n"
         "       t1.activation_sequence,\n"
         "       t2.token_id AS predecessor_token,\n"
         "       t2.status AS predecessor_status\n"
         "FROM IdentityToken t1\n"
         "JOIN IdentityToken t2 ON t1.predecessor_token_id = t2.token_id\n"
         "WHERE t1.status = 'ACTIVE'\n"
         "ORDER BY t1.activation_sequence DESC;"),
    ]

    return render_template('sql_console.html',
                           sql=sql,
                           results=results,
                           columns=columns,
                           error=error,
                           examples=examples,
                           explain_mode=explain_mode,
                           max_length=SQL_MAX_LENGTH,
                           timeout_ms=SQL_TIMEOUT_MS)


# ============================================================================
# ERROR HANDLERS
# ============================================================================

@app.errorhandler(404)
def page_not_found(e):
    return render_template('error.html',
                           code=404,
                           message='Page not found'), 404


@app.errorhandler(500)
def server_error(e):
    return render_template('error.html',
                           code=500,
                           message='Internal server error'), 500


# ============================================================================
# MAIN
# ============================================================================

if __name__ == '__main__':
    port = int(os.environ.get('POLARIS_PORT', 5000))
    print(f"Polaris web interface starting on http://0.0.0.0:{port}")
    print(f"Database: {DB_CONFIG['database']} @ {DB_CONFIG['host']}")
    app.run(host='0.0.0.0', port=port, debug=False)
