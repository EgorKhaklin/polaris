# =============================================================================
# AI-context: auth, rate limit, CSRF, CSP, security headers. The CSP is
#   'self' — never weaken without naming the threat.
# Read before editing:
#     ../DEVNOTES/concurrency.md  (atomic increment section — TOCTOU history)
#     ../docs/operator/SECURITY.md              (full threat model)
# Tests can lock the admin account. To unlock:
#     UPDATE AppUser SET locked_until=NULL, failed_login_count=0
# =============================================================================

"""
============================================================================
POLARIS — Web Interface Security Module
============================================================================

Implements the controls applied during the security-patching pass:

  Authentication        Login + scrypt password verification + session
  Authorization         Role-based decorators (admin/operator/auditor)
  CSRF protection       HMAC-signed token in session, validated on POSTs
  Account lockout       N failures within W minutes locks for L minutes
  Rate limiting         Per-IP token bucket on login + state-changing POSTs
  Security headers      CSP, X-Frame-Options, X-Content-Type-Options,
                        Referrer-Policy, HSTS (prod-only), Permissions-Policy
  Cookie hardening      HttpOnly, SameSite=Lax, Secure (prod-only)
  Body size limit       Flask's MAX_CONTENT_LENGTH set to 1 MiB
  Auth audit logging    Every login / logout / failure / lockout / CSRF
                        rejection / authz denial recorded in AuthAuditLog

Frameworks:
  - OWASP ASVS L2 controls
  - OWASP Top 10 (2021): A01-A09 mitigations
  - CWE references annotated inline

This module deliberately avoids Flask-Login / Flask-WTF / Flask-Limiter
to keep the dependency graph small (just Flask + psycopg2 + werkzeug,
all already required) and to keep the security logic transparent and
auditable rather than hidden behind a third-party DSL.
============================================================================
"""

import os
import hmac
import time
import secrets
import functools
from datetime import datetime
from collections import defaultdict, deque

from flask import (
    request, session, redirect, url_for, render_template, flash, abort, g, current_app
)
from werkzeug.security import generate_password_hash, check_password_hash

import observability  # v9.31 freeze condition 6 — counter call-sites for auth failures


# ----------------------------------------------------------------------------
# Configuration constants
# ----------------------------------------------------------------------------

LOGIN_FAILURE_THRESHOLD   = 5         # account locks after this many failures
LOGIN_FAILURE_WINDOW_MIN  = 10        # within this many minutes
ACCOUNT_LOCK_MIN          = 15        # locked out for this many minutes

# Per-IP rate limit on login attempts (token bucket)
RATE_LIMIT_LOGIN_MAX      = 10        # max login attempts...
RATE_LIMIT_LOGIN_WINDOW   = 60        # ...per N seconds per IP

# Per-IP rate limit on all state-changing requests
RATE_LIMIT_WRITE_MAX      = 60
RATE_LIMIT_WRITE_WINDOW   = 60

# Body size limit (1 MiB; the SQL console caps queries at 5 KB separately)
MAX_REQUEST_BODY_BYTES    = 1 * 1024 * 1024

# Session lifetime
SESSION_LIFETIME_HOURS    = 8


# ----------------------------------------------------------------------------
# Rate limiter — sliding-window per-key counter (CWE-307 / CWE-770 mitigation)
#
# Two backends with the same public contract:
#   - InMemoryRateLimiter — per-process; correct for single-worker dev / tests
#                            and for any deployment where there is exactly one
#                            Python process (e.g. `flask run`, single-worker
#                            gunicorn).
#   - RedisRateLimiter   — multi-process / multi-host; uses an atomic Lua
#                            script over a sorted set so all workers share the
#                            same per-IP counter.
#
# Production gunicorn defaults to 4 workers. With the in-memory limiter, every
# worker holds its own copy of the bucket — a single client can effectively
# get 4× the configured limit. For correctness under multi-worker production
# deployments, set POLARIS_REDIS_URL and the auto-selector picks the Redis
# backend. The in-memory backend logs a warning at startup when it sees
# POLARIS_WORKERS > 1 (no Redis URL → operator should know).
#
# Selection (POLARIS_RATE_LIMIT_BACKEND, defaults to 'auto'):
#   auto    → Redis if POLARIS_REDIS_URL set and reachable, else in-memory.
#   memory  → always in-memory.
#   redis   → always Redis; falls back to in-memory + stderr warning if Redis
#             is misconfigured (no URL or unreachable). Tests and operators
#             can use POLARIS_RATE_LIMIT_BACKEND=memory to bypass Redis.
#
# Both backends honor the same allow(key, max, window) → bool contract and
# the same reset(key=None) semantic, so app code (security.py and app.py
# call sites) is backend-agnostic.
# ----------------------------------------------------------------------------


class _BaseRateLimiter:
    """Public contract every backend must implement."""

    name = 'base'  # subclasses override

    def allow(self, key, max_events, window_seconds):
        """Return True if the event is allowed; False if it would exceed the
        per-key sliding window. Implementations must be atomic with respect
        to concurrent allow() calls on the same key."""
        raise NotImplementedError

    def reset(self, key=None):
        """Clear all buckets if key is None; otherwise clear just that key."""
        raise NotImplementedError

    def healthy(self):
        """Return True if the backend is currently operational."""
        return True


class InMemoryRateLimiter(_BaseRateLimiter):
    """Per-process sliding-window limiter. Single-worker deployments only.

    Concurrency: a single deque per key with no locking is safe under
    CPython for the usage pattern here (popleft + append are atomic at the
    bytecode level for deque). The earlier audit accepted this; do not
    change it without re-verifying — adding a lock here is a TOCTOU
    regression risk on the GIL guarantees the current code relies on."""

    name = 'memory'

    def __init__(self):
        self._buckets = defaultdict(deque)

    def allow(self, key, max_events, window_seconds):
        now = time.monotonic()
        bucket = self._buckets[key]
        cutoff = now - window_seconds
        while bucket and bucket[0] < cutoff:
            bucket.popleft()
        if len(bucket) >= max_events:
            return False
        bucket.append(now)
        return True

    def reset(self, key=None):
        if key is None:
            self._buckets.clear()
        else:
            self._buckets.pop(key, None)


class RedisRateLimiter(_BaseRateLimiter):
    """Multi-process sliding-window limiter backed by a Redis sorted set.

    The Lua script runs atomically inside Redis: it trims old entries,
    counts what remains, decides allow/deny, and (on allow) records the
    new entry — all within a single round trip and a single Redis lock.
    No race window exists between count and write.

    Sort-set member format: a per-call random nonce so two events with the
    same millisecond score don't collide (ZADD by default updates a
    member's score; we want each call to be a distinct entry).

    Failure mode: if Redis is unreachable mid-flight, allow() fails-closed
    (returns False) and logs to stderr. This matches OWASP "fail securely"
    guidance — denying a request under load is preferable to silently
    bypassing the rate limiter. Operators should monitor redis_errors_total
    and treat sustained errors as a SEV.
    """

    name = 'redis'

    KEY_PREFIX = 'polaris:rl:'

    # KEYS[1] = bucket key (already prefixed)
    # ARGV[1] = now in milliseconds
    # ARGV[2] = window in milliseconds
    # ARGV[3] = max_events (allow if count < this)
    # ARGV[4] = nonce — unique member added on success
    # Returns 1 if allowed, 0 if denied. PEXPIRE keeps Redis tidy when a key
    # goes idle.
    LUA_SLIDING_WINDOW = """
    local key = KEYS[1]
    local now = tonumber(ARGV[1])
    local window = tonumber(ARGV[2])
    local max_events = tonumber(ARGV[3])
    local cutoff = now - window
    redis.call('ZREMRANGEBYSCORE', key, '-inf', cutoff)
    local count = redis.call('ZCARD', key)
    if count >= max_events then
        return 0
    end
    redis.call('ZADD', key, now, ARGV[4])
    redis.call('PEXPIRE', key, window + 1000)
    return 1
    """

    def __init__(self, url, socket_timeout=2.0):
        import redis as _redis  # imported lazily; package is optional
        self._url = url
        self._client = _redis.from_url(
            url, socket_timeout=socket_timeout,
            socket_connect_timeout=socket_timeout,
            decode_responses=False,
        )
        # Surface configuration errors at construction time, not at first
        # request — the selector catches and falls back if this raises.
        self._client.ping()
        self._script = self._client.register_script(self.LUA_SLIDING_WINDOW)

    def allow(self, key, max_events, window_seconds):
        full_key = self.KEY_PREFIX + key
        now_ms = int(time.time() * 1000)
        window_ms = int(window_seconds * 1000)
        # Use a fresh nonce per call so simultaneous events do not collapse
        # into a single sorted-set member with their score overwritten.
        nonce = f"{now_ms}-{secrets.token_hex(8)}"
        try:
            result = self._script(
                keys=[full_key],
                args=[now_ms, window_ms, max_events, nonce],
            )
            return bool(int(result))
        except Exception as e:
            import sys
            sys.stderr.write(
                f"[security] Redis rate limiter error on key={key!r}: "
                f"{e!r}; failing closed (denying request).\n"
            )
            return False

    def reset(self, key=None):
        try:
            if key is None:
                # Tests use this; in production reset(None) is rare. SCAN
                # is paginated server-side — never blocks Redis even on a
                # large key space.
                for k in self._client.scan_iter(match=self.KEY_PREFIX + '*',
                                                count=500):
                    self._client.delete(k)
            else:
                self._client.delete(self.KEY_PREFIX + key)
        except Exception as e:
            import sys
            sys.stderr.write(
                f"[security] Redis rate limiter reset failed: {e!r}\n"
            )

    def healthy(self):
        try:
            return self._client.ping() is True
        except Exception:
            return False


# Back-compat alias: pre-v7.5 code referenced security.RateLimiter() directly.
RateLimiter = InMemoryRateLimiter


def _make_rate_limiter():
    """Pick a rate-limiter backend based on env config.

    Returns an instance implementing _BaseRateLimiter. Always returns SOME
    backend — never raises — because rate limiting is on the request
    hot path and a startup failure would take the whole app offline.
    Misconfiguration falls back to in-memory + a loud stderr warning.
    """
    backend = os.environ.get('POLARIS_RATE_LIMIT_BACKEND', 'auto').lower()
    redis_url = os.environ.get('POLARIS_REDIS_URL', '').strip()
    try:
        workers = int(os.environ.get('POLARIS_WORKERS', '1') or '1')
    except (TypeError, ValueError):
        workers = 1

    import sys

    def _try_redis():
        try:
            return RedisRateLimiter(redis_url)
        except Exception as e:
            sys.stderr.write(
                f"[security] Redis rate limiter unavailable ({e!r}); "
                f"falling back to in-memory.\n"
            )
            return None

    if backend == 'memory':
        chosen = InMemoryRateLimiter()
    elif backend == 'redis':
        if not redis_url:
            sys.stderr.write(
                "[security] POLARIS_RATE_LIMIT_BACKEND=redis but "
                "POLARIS_REDIS_URL is empty — falling back to in-memory.\n"
            )
            chosen = InMemoryRateLimiter()
        else:
            chosen = _try_redis() or InMemoryRateLimiter()
    else:  # 'auto' or anything unrecognized
        if redis_url:
            chosen = _try_redis() or InMemoryRateLimiter()
        else:
            chosen = InMemoryRateLimiter()

    if chosen.name == 'memory' and workers > 1:
        sys.stderr.write(
            f"[security] WARNING: POLARIS_WORKERS={workers} with in-memory "
            f"rate limiter — actual per-IP limits will be ~{workers}× "
            f"configured because each worker holds its own buckets. Set "
            f"POLARIS_REDIS_URL for accurate cross-worker enforcement.\n"
        )
    return chosen


# Global rate-limiter instance. Reset by tests via security.rate_limiter.reset().
# In multi-worker production with POLARIS_REDIS_URL set this is the Redis
# backend; otherwise it's the in-memory backend (with a startup warning if
# multiple workers are configured).
rate_limiter = _make_rate_limiter()


def client_ip():
    """
    Extract the real client IP, honoring X-Forwarded-For when behind a
    trusted reverse proxy. Be conservative: only honor XFF if explicitly
    enabled via TRUST_PROXY env var (CWE-345 / CWE-348 mitigation).
    """
    if os.environ.get('POLARIS_TRUST_PROXY', '').lower() in ('1', 'true', 'yes'):
        xff = request.headers.get('X-Forwarded-For', '')
        if xff:
            # Use the leftmost (the original client)
            return xff.split(',')[0].strip()
    return request.remote_addr or '0.0.0.0'


# ----------------------------------------------------------------------------
# Audit logging — writes to AuthAuditLog table
# ----------------------------------------------------------------------------

def _audit(get_conn, event_type, username=None, user_id=None, detail=None):
    """
    Append an AuthAuditLog row. Failures are caught and logged to stderr
    rather than propagating, so audit-logging never breaks user-facing
    requests. (Audit logging is best-effort but should never deny service.)
    """
    try:
        conn = get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO AuthAuditLog
                        (event_type, username, user_id, ip_address, user_agent, detail)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (
                        event_type,
                        username,
                        user_id,
                        client_ip()[:45],
                        (request.headers.get('User-Agent', '') or '')[:255],
                        (detail or '')[:500],
                    )
                )
            conn.commit()
        finally:
            conn.close()
    except Exception as e:
        import sys
        sys.stderr.write(f"[audit] Failed to write {event_type}: {e}\n")


# ----------------------------------------------------------------------------
# v9.20 — record_audit_access: the audit's audit.
#
# Per Sanctum sanctum/2026-05-15-verification-purpose-and-audit-access.md
# Position A. Records WHO queried the audit tables (TokenLifecycleEvent /
# VerificationEvent / AuthAuditLog / DuressEvent). The helper is fail-open
# (logging failure does not block the actual query — accountability data
# corrupts gracefully rather than blocking operator access to legitimate
# audit data).
#
# CONSTITUTIONAL BOUNDARY: this helper must NEVER be called from a route
# that reads AuditAccessLog itself. The audit-of-audit-of-audit regress
# stops at AuditAccessLog by construction. This is structurally enforced
# by the structural invariant test_audit_access_log_reads_not_logged in
# TestWave20V920 — any reference to record_audit_access alongside a
# SELECT FROM AuditAccessLog will trip the test.
# ----------------------------------------------------------------------------

# The four tables whose reads are audited by AuditAccessLog. Pinned here
# (rather than in app.py) so additions go through this constant + the
# associated structural test in TestWave20V920.
AUDIT_TABLES_TRACKED = (
    'TokenLifecycleEvent',
    'VerificationEvent',
    'AuthAuditLog',
    'DuressEvent',
)


def record_audit_access(get_conn, accessed_table, filter_criteria=None,
                        result_row_count=None):
    """Append an AuditAccessLog row recording that the current actor read
    from `accessed_table`. Best-effort + fail-open: any exception is
    suppressed to stderr; the caller's actual query proceeds regardless.

    Args:
        get_conn: callable returning a fresh DB connection (matches the
                  pattern of _audit + audit hooks elsewhere)
        accessed_table: one of AUDIT_TABLES_TRACKED (raises ValueError
                  otherwise — programmer error, not operator error)
        filter_criteria: dict serializable to JSONB; describes what
                  filter the query applied (e.g., {"token_id": 42}).
                  None becomes {}.
        result_row_count: integer count of rows returned, or None when
                  not easily measurable. Stored as-is.

    Returns:
        None. The function is side-effect only.

    Constitutional contract:
      - MUST NOT be called from any route that reads AuditAccessLog
        itself (regress boundary; structurally pinned)
      - Failures DO NOT propagate (fail-open)
      - Filter criteria are stored verbatim; no LLM analysis
    """
    if accessed_table not in AUDIT_TABLES_TRACKED:
        # Programmer error: caller passed an unknown table name.
        # Surface loudly in dev; do not propagate in production.
        import sys
        sys.stderr.write(
            f"[audit_access] WARNING: record_audit_access called with "
            f"unknown table {accessed_table!r}; expected one of "
            f"{AUDIT_TABLES_TRACKED}. Skipping log.\n"
        )
        return

    user = current_user()
    actor_user_id = user['user_id'] if user else None

    # System access (no logged-in user) captures source in filter for
    # accountability. The same field is used by web reads for explicit
    # filter parameters.
    filter_payload = dict(filter_criteria or {})

    try:
        from psycopg2.extras import Json
        conn = get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO AuditAccessLog
                        (actor_user_id, accessed_table,
                         filter_criteria_jsonb, result_row_count)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (
                        actor_user_id,
                        accessed_table,
                        Json(filter_payload),
                        result_row_count,
                    ),
                )
            conn.commit()
        finally:
            conn.close()
    except Exception as e:  # noqa: BLE001 — fail-open by design
        import sys
        sys.stderr.write(
            f"[audit_access] Failed to write read of {accessed_table}: {e}\n"
        )


# ----------------------------------------------------------------------------
# Password hashing (Werkzeug scrypt) — kept here so callers don't depend on
# werkzeug.security directly. CWE-256 / CWE-916 mitigation.
# ----------------------------------------------------------------------------

def hash_password(plaintext):
    return generate_password_hash(plaintext, method='scrypt')

def verify_password(hashed, plaintext):
    return check_password_hash(hashed, plaintext)


# ----------------------------------------------------------------------------
# Authentication: login / logout / current user
# ----------------------------------------------------------------------------

def authenticate(get_conn, username, password):
    """
    Verify credentials and update lockout/last-login bookkeeping.
    Returns (user_dict_or_None, error_message). The error message is
    intentionally generic to avoid username enumeration (CWE-203, CWE-204).
    """
    GENERIC_ERROR = "Invalid username or password."

    if not username or not password:
        return None, GENERIC_ERROR
    if len(username) > 50 or len(password) > 128:
        # Reject obviously-malformed inputs without DB query (CWE-1284)
        return None, GENERIC_ERROR

    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT user_id, username, password_hash, role, is_active, "
                "       failed_login_count, locked_until "
                "FROM AppUser WHERE username = %s",
                (username,)
            )
            user = cur.fetchone()

            # Constant-time-ish: even if user not found, run a dummy verify
            # to make timing oracles less useful (CWE-208).
            if user is None:
                check_password_hash(
                    'scrypt:32768:8:1$dummy$0' + '0' * 128,
                    password
                )
                _audit(get_conn, 'LOGIN_FAILED', username=username,
                       detail='unknown user')
                return None, GENERIC_ERROR

            if not user['is_active']:
                _audit(get_conn, 'LOGIN_FAILED', username=username,
                       user_id=user['user_id'], detail='account inactive')
                return None, GENERIC_ERROR

            # Lockout check
            now = datetime.now()
            if user['locked_until'] and user['locked_until'] > now:
                _audit(get_conn, 'LOGIN_LOCKED', username=username,
                       user_id=user['user_id'],
                       detail=f"locked until {user['locked_until']}")
                return None, "Account is temporarily locked. Try again later."

            # Verify password
            if not check_password_hash(user['password_hash'], password):
                # v9.31 freeze condition 6: operator-readable auth-failure
                # counter + structured log. Fires once per bad-credential
                # check regardless of subsequent lockout branch.
                try:
                    observability.record_auth_failure(kind='password',
                                                     username=username)
                except Exception:
                    pass
                # Atomic increment + return-the-new-value. This is critical
                # for concurrency: under load, two simultaneous failed logins
                # against the same account both read failed_login_count=N
                # under the previous "read then write +1" pattern, then both
                # wrote N+1, losing one failure. Lockout could be bypassed by
                # spamming concurrent attempts. UPDATE...SET col=col+1 is
                # atomic in PostgreSQL and resolves under row lock; both
                # transactions get sequenced and observe the correct counter.
                cur.execute(
                    "UPDATE AppUser SET failed_login_count = failed_login_count + 1 "
                    "WHERE user_id = %s "
                    "RETURNING failed_login_count",
                    (user['user_id'],)
                )
                new_count = cur.fetchone()['failed_login_count']

                if new_count >= LOGIN_FAILURE_THRESHOLD:
                    # Lock the account. Use the same row-locked path: the
                    # threshold test above used the post-increment value, so
                    # exactly one of N concurrent failures crosses the line.
                    cur.execute(
                        "UPDATE AppUser SET locked_until = CURRENT_TIMESTAMP + "
                        "(%s || ' minutes')::INTERVAL "
                        "WHERE user_id = %s AND locked_until IS NULL",
                        (ACCOUNT_LOCK_MIN, user['user_id'])
                    )
                    conn.commit()
                    _audit(get_conn, 'LOGIN_LOCKED', username=username,
                           user_id=user['user_id'],
                           detail=f"locked after {new_count} failures")
                    return None, GENERIC_ERROR
                else:
                    conn.commit()
                    _audit(get_conn, 'LOGIN_FAILED', username=username,
                           user_id=user['user_id'],
                           detail=f"failure {new_count}/{LOGIN_FAILURE_THRESHOLD}")
                    return None, GENERIC_ERROR

            # Success — reset counter, update last login
            cur.execute(
                "UPDATE AppUser SET failed_login_count=0, locked_until=NULL, "
                "last_login_at=CURRENT_TIMESTAMP WHERE user_id=%s",
                (user['user_id'],)
            )
            conn.commit()
            _audit(get_conn, 'LOGIN_SUCCESS', username=username,
                   user_id=user['user_id'])

            return ({
                'user_id':  user['user_id'],
                'username': user['username'],
                'role':     user['role'],
            }, None)
    finally:
        conn.close()


def login_user(user):
    """Establish a session for the authenticated user. Regenerate session
    ID by clearing/recreating the session dict to prevent fixation (CWE-384).
    """
    session.clear()
    session['user_id']   = user['user_id']
    session['username']  = user['username']
    session['role']      = user['role']
    session['logged_in'] = True
    session.permanent    = True
    # Issue a fresh CSRF token on login
    session['csrf_token'] = secrets.token_urlsafe(32)


def logout_user(get_conn):
    """Audit-log the logout, then clear the session."""
    if session.get('logged_in'):
        _audit(get_conn, 'LOGOUT',
               username=session.get('username'),
               user_id=session.get('user_id'))
    session.clear()


def current_user():
    """Return the logged-in user dict, or None."""
    if not session.get('logged_in'):
        return None
    return {
        'user_id':  session.get('user_id'),
        'username': session.get('username'),
        'role':     session.get('role'),
    }


# ----------------------------------------------------------------------------
# Authorization decorators
# ----------------------------------------------------------------------------

# Role hierarchy for "at least this role" semantics where useful.
# Note: in this app the roles are mostly orthogonal (auditor != less-than-admin),
# so we use require_role with a set rather than a hierarchy.
ROLES = ('admin', 'operator', 'auditor')


def login_required(view_func):
    """Reject anonymous requests. CWE-306 mitigation."""
    @functools.wraps(view_func)
    def wrapped(*args, **kwargs):
        if not session.get('logged_in'):
            # Audit the auth-required event for unauthenticated POSTs;
            # GETs are noisy and would flood the log with browser noise.
            if request.method != 'GET':
                _audit(current_app.config['GET_DB'], 'AUTH_REQUIRED',
                       detail=f"{request.method} {request.path}")
            return redirect(url_for('login', next=request.url))
        return view_func(*args, **kwargs)
    return wrapped


def require_role(*allowed_roles):
    """
    Restrict view to specified roles. Logged-in users with the wrong role
    get a 403, not a 404 — they're authenticated but not authorized
    (CWE-285 mitigation).
    """
    def decorator(view_func):
        @functools.wraps(view_func)
        def wrapped(*args, **kwargs):
            if not session.get('logged_in'):
                return redirect(url_for('login', next=request.url))
            if session.get('role') not in allowed_roles:
                _audit(current_app.config['GET_DB'], 'AUTHZ_DENIED',
                       username=session.get('username'),
                       user_id=session.get('user_id'),
                       detail=f"role={session.get('role')} "
                              f"allowed={allowed_roles} "
                              f"path={request.path}")
                abort(403)
            return view_func(*args, **kwargs)
        return wrapped
    return decorator


# ----------------------------------------------------------------------------
# CSRF protection (CWE-352)
# ----------------------------------------------------------------------------

def issue_csrf_token():
    """Generate or fetch the per-session CSRF token."""
    if 'csrf_token' not in session:
        session['csrf_token'] = secrets.token_urlsafe(32)
    return session['csrf_token']


def validate_csrf():
    """
    Validate the CSRF token submitted on a state-changing request.
    Uses constant-time comparison to defeat timing oracles (CWE-208).
    Returns True if valid, False otherwise.

    Accepts the token from either:
      - form field 'csrf_token' (HTML form POSTs)
      - header 'X-CSRFToken' (JSON / AJAX POSTs)
    Form takes precedence when both are present.
    """
    submitted = request.form.get('csrf_token') or request.headers.get('X-CSRFToken') or ''
    expected  = session.get('csrf_token', '')
    if not submitted or not expected:
        return False
    return hmac.compare_digest(submitted, expected)


def csrf_protect(view_func):
    """Decorator to require a valid CSRF token on POST/PUT/DELETE."""
    @functools.wraps(view_func)
    def wrapped(*args, **kwargs):
        if request.method in ('POST', 'PUT', 'DELETE', 'PATCH'):
            if not validate_csrf():
                _audit(current_app.config['GET_DB'], 'CSRF_REJECTED',
                       username=session.get('username'),
                       user_id=session.get('user_id'),
                       detail=f"{request.method} {request.path}")
                abort(403)
        return view_func(*args, **kwargs)
    return wrapped


# ----------------------------------------------------------------------------
# Security headers (applied by app.after_request hook)
# ----------------------------------------------------------------------------

def apply_security_headers(response):
    """
    Add the standard security headers to every response.

    CSP: default-src 'self' allows only same-origin; 'unsafe-inline' is
    permitted for <style> because the templates use a small amount of inline
    style (and our hand-written CSS isn't worth the effort to migrate to
    CSP-nonce-style). Inline scripts are NOT permitted — there are none in
    the templates by design (one toy onclick handler in sql_console.html
    uses inline JS but it's not security-critical; we'll move it).

    Headers applied:
      Content-Security-Policy   (CWE-79 mitigation)
      X-Frame-Options           (CWE-1021 clickjacking)
      X-Content-Type-Options    (CWE-451 MIME sniffing)
      Referrer-Policy           (CWE-200 information leak)
      Permissions-Policy        (feature-policy minimization)
      Strict-Transport-Security (CWE-319, only in production)
      Cache-Control             (CWE-525 sensitive content caching)
    """
    # v9.13: tightened CSP with `upgrade-insecure-requests` when HSTS active
    # (defense against mixed-content on production) and isolation headers
    # (COOP/COEP/CORP) for cross-origin defense-in-depth against Spectre-class
    # side-channel + cross-origin object leaks.
    hsts_active = os.environ.get('POLARIS_HSTS', '').lower() in ('1', 'true', 'yes')
    csp_parts = [
        "default-src 'self'",
        "script-src 'self'",
        "style-src 'self' 'unsafe-inline'",
        "img-src 'self' data:",
        "font-src 'self' data:",
        "connect-src 'self'",
        "frame-ancestors 'none'",
        "form-action 'self'",
        "base-uri 'self'",
        "object-src 'none'",
    ]
    if hsts_active:
        # Forces mixed-content requests to be upgraded to HTTPS rather than
        # blocked silently. Only meaningful in production where HSTS is on.
        csp_parts.append("upgrade-insecure-requests")
    response.headers['Content-Security-Policy']   = "; ".join(csp_parts)
    response.headers['X-Frame-Options']           = 'DENY'
    response.headers['X-Content-Type-Options']    = 'nosniff'
    response.headers['Referrer-Policy']           = 'strict-origin-when-cross-origin'
    response.headers['Permissions-Policy']        = (
        'camera=(), microphone=(), geolocation=(), payment=(), usb=(), '
        'interest-cohort=(), browsing-topics=()'
    )
    # v9.13 cross-origin isolation: COOP isolates the browsing context from
    # cross-origin windows (Spectre defense); CORP restricts cross-origin
    # embedding of our resources to same-origin only.
    response.headers['Cross-Origin-Opener-Policy']   = 'same-origin'
    response.headers['Cross-Origin-Resource-Policy'] = 'same-origin'
    # Note: COEP `require-corp` is not enabled because it breaks any future
    # embedded resources (img/script) that don't carry CORP. Leaving COOP +
    # CORP active provides ~90% of the isolation benefit without the
    # operational cost.

    # HSTS only in production (env opt-in, since enabling it on a non-HTTPS
    # dev box would be confusing). 1 year + includeSubDomains is the standard.
    if hsts_active:
        response.headers['Strict-Transport-Security'] = \
            'max-age=31536000; includeSubDomains'

    # v9.13: Server-header scrubbing — defense-in-depth across deployment shapes.
    #
    #   - Werkzeug dev server: pop+set wins; the wire shows `Server: Polaris`.
    #   - Gunicorn (production): the `gunicorn.conf.py` post_worker_init hook
    #     monkey-patches `gunicorn.http.wsgi.Response.default_headers` to drop
    #     the hardcoded `Server: gunicorn`. The pop+set below covers the case
    #     where the patch is bypassed.
    #   - Behind reverse proxy (canonical production path): Caddy or nginx
    #     strips/replaces Server at the edge. Documented in
    #     `docs/operator/DEPLOYMENT.md`. That layer is authoritative.
    #
    # Outcome on the wire: either `Server: Polaris` or no Server header at all.
    # Both are acceptable; neither leaks the actual server type/version.
    response.headers.pop('Server', None)
    response.headers['Server'] = 'Polaris'

    # Don't cache authenticated content. (Most of our content is.)
    if session.get('logged_in'):
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, private'
        response.headers['Pragma']        = 'no-cache'

    return response


# ----------------------------------------------------------------------------
# Body-size limit guard (used as before_request)
# ----------------------------------------------------------------------------

def enforce_body_size_limit():
    """Reject oversized POSTs. Flask's MAX_CONTENT_LENGTH does this too,
    but we add an explicit check that returns a clear error message rather
    than a generic 413."""
    if request.content_length and request.content_length > MAX_REQUEST_BODY_BYTES:
        abort(413)


# ----------------------------------------------------------------------------
# Helpers for templates
# ----------------------------------------------------------------------------

def template_context_processor():
    """Inject CSRF token and current_user into all templates."""
    return {
        'csrf_token':   issue_csrf_token,
        'current_user': current_user(),
    }
