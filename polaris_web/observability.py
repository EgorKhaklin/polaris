"""polaris_web/observability.py — operator-readable application metrics.

v9.27 / BIG MISSION Tier 8 #11. Separate from the meta-swarm
(which observes the cognitive layer); this module observes the
RUNNING APPLICATION in production terms.

**Anti-Architect constraints (per Sanctum 2026-05-16 §II T8#11):**

1. No new metrics backend. No Prometheus exporter, no StatsD, no
   tracing system. Polaris is a reference implementation; operators
   pipe stdout structured logs wherever they like.
   (Amended v9.187 / roadmap P1.6: an OPT-IN OpenTelemetry tracing
   layer now lives in tracing.py — off by default, announced in the
   log stream when on, nothing identity-derived, nothing persisted
   to the DB. This module stays backend-free; tracing.py registers
   the trace-context hook below so structured_log lines can carry
   trace_id/span_id while a span is recording.)

2. Duress events are the headline metric. An unobservable duress
   signal is the coercion-cover failure mode (a coerced operator's
   duress code raises a row that no one reads → the duress feature
   is decorative).

3. Operator-readable first, analytics-tool-readable second. JSON
   shape that grep + jq handle directly.

**What this module provides:**

- `Counter` class: thread-safe in-process counters (no external deps)
- `structured_log(event, **fields)`: emits one JSON object per line
  to stdout. operator pipes to journald / CloudWatch / file rotation.
- `MetricsSnapshot.collect()`: returns a dict of current counter values
  suitable for serving at `/api/metrics`.

The four headline metrics (per Sanctum joint resolution):
- `request_rate_per_minute`     — operational throughput
- `error_rate_per_minute`       — 5xx + uncaught exceptions
- `auth_failures_per_minute`    — failed-login + WebAuthn rejections
- `duress_events_total`         — count since process start

These are integration points for app.py + security.py to call. They
are NOT auto-instrumented at import time — explicit call sites only,
because hidden instrumentation is itself a coercion risk (a coerced
operator can't disable what they can't see).
"""

from __future__ import annotations

import contextvars
import json
import os
import re
import sys
import threading
import time
import uuid
from collections import deque
from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Request-correlation id (v9.122).
#
# A single ephemeral id per HTTP request so an operator can match a structured
# log line to the response a caller saw. This is deliberately NOT a tracing
# system (no spans, no cross-service propagation, no backend) — it is one field
# stamped into the existing stdout JSON stream, consistent with the
# anti-architect constraints above. (v9.187 / P1.6: tracing.py adds the
# OPT-IN tracing layer on top; this id becomes the join key between the log
# stream and the trace — its own semantics are unchanged.)
#
# Vocation (anti-coercion): the id is per-request and ephemeral. It lives only
# in the contextvar below and the X-Request-ID response header. It is NEVER
# derived from identity and is NEVER written to a DB row — in particular not the
# append-only audit-of-record, where the C1 trigger would make it a permanent,
# reconstructable cross-request linkage key. That asymmetry (useful for live
# debugging in the moment, inert as a retention/aggregation vector) is the point.
#
# Accepted inbound ids are bounded to a safe charset and length so a hostile
# X-Request-ID cannot inject newlines/control bytes into logs or grow unbounded
# (the v9.83 "bound unbounded resources" posture). \A and \Z (not ^ / $) anchor
# the whole string, so a trailing-newline payload cannot slip through.
_REQUEST_ID_RE = re.compile(r"\A[A-Za-z0-9-]{8,64}\Z")
_request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar(
    "polaris_request_id", default="-"
)


def validate_or_new_request_id(raw) -> str:
    """Return ``raw`` only if it is a well-formed inbound id, else mint a fresh one.

    This is the ONLY function that is allowed to trust inbound bytes. A value is
    accepted only when it is a ``str`` matching ``\\A[A-Za-z0-9-]{8,64}\\Z``;
    anything else (None, wrong type, bad charset, too short/long, embedded
    control char) is dropped in favour of ``uuid4().hex`` (32 hex chars, a strict
    subset of the accepted charset).
    """
    if isinstance(raw, str) and _REQUEST_ID_RE.fullmatch(raw):
        return raw
    return uuid.uuid4().hex


def set_request_id(value: str) -> contextvars.Token:
    """Bind ``value`` as the current request id; returns the reset token."""
    return _request_id_var.set(value)


def get_request_id() -> str:
    """The current request id, or the sentinel ``'-'`` outside any request."""
    return _request_id_var.get()


def reset_request_id(token: contextvars.Token) -> None:
    """Clear the request id back to its prior value.

    Tolerates a token created in a different context or already spent (Flask can
    pop a shared-``g`` request context more than once, and a ``Token`` may only
    reset once): this must never crash teardown. As a backstop, drop the var
    back to the sentinel so a reset that could not be honoured still cannot leak
    the id into the next request a worker serves.
    """
    try:
        _request_id_var.reset(token)
    except (ValueError, LookupError, RuntimeError):
        _request_id_var.set("-")


# ---------------------------------------------------------------------------
# Trace-context hook (v9.187 / roadmap P1.6). tracing.py registers a callable
# returning {'trace_id': ..., 'span_id': ...} while a span is recording, or
# None. This module never imports opentelemetry (backend-free by charter);
# the hook is how structured_log joins the log stream to traces without a
# dependency. Default None = tracing off = logs exactly as before.
_trace_context_provider = None


def set_trace_context_provider(fn) -> None:
    """Install (or clear, with None) the trace-context callable."""
    global _trace_context_provider
    _trace_context_provider = fn


class Counter:
    """Thread-safe monotonically-increasing counter."""

    def __init__(self):
        self._value = 0
        self._lock = threading.Lock()

    def inc(self, n: int = 1) -> None:
        with self._lock:
            self._value += n

    def value(self) -> int:
        with self._lock:
            return self._value


class RateWindow:
    """Per-minute rolling counter. Keeps the last `window_minutes`
    minutes of per-minute samples + returns the trailing rate.

    Cheap: O(window_minutes) per .rate() call. Default window = 5 min.
    """

    def __init__(self, window_minutes: int = 5):
        self._window_minutes = window_minutes
        self._samples = deque(maxlen=window_minutes)
        self._current_minute = self._minute_now()
        self._current_count = 0
        self._lock = threading.Lock()

    def inc(self, n: int = 1) -> None:
        with self._lock:
            now_min = self._minute_now()
            if now_min != self._current_minute:
                self._samples.append(self._current_count)
                gap = now_min - self._current_minute - 1
                for _ in range(min(gap, self._window_minutes)):
                    self._samples.append(0)
                self._current_minute = now_min
                self._current_count = n
            else:
                self._current_count += n

    def rate_per_minute(self) -> float:
        with self._lock:
            now_min = self._minute_now()
            sample_total = sum(self._samples)
            if now_min == self._current_minute:
                sample_total += self._current_count
            total_minutes = len(self._samples) + 1
            if total_minutes == 0:
                return 0.0
            return round(sample_total / total_minutes, 2)

    @staticmethod
    def _minute_now() -> int:
        return int(time.time() // 60)


@dataclass
class _Registry:
    requests: RateWindow = field(default_factory=lambda: RateWindow(5))
    errors: RateWindow = field(default_factory=lambda: RateWindow(5))
    auth_failures: RateWindow = field(default_factory=lambda: RateWindow(5))
    duress_events: Counter = field(default_factory=Counter)
    process_started_at: float = field(default_factory=time.time)
    process_id: int = field(default_factory=os.getpid)


_REGISTRY = _Registry()


def record_request() -> None:
    """Call from a Flask after_request hook. One inc per request."""
    _REGISTRY.requests.inc()


def record_error() -> None:
    """Call from a Flask errorhandler. One inc per 5xx / uncaught."""
    _REGISTRY.errors.inc()


def record_auth_failure(*, kind: str = "password", username: str = "") -> None:
    """Call from security.py:authenticate on a bad-credential path,
    AND from webauthn_auth on a failed assertion.

    `kind` is one of: 'password', 'webauthn', 'recovery_code'.
    """
    _REGISTRY.auth_failures.inc()
    structured_log("auth_failure", kind=kind, username=username)


def record_duress_event(*, individual_id: int = 0, agency_id: int = 0) -> None:
    """Call from app.py:duress handler. Increments the headline
    duress counter + emits a structured log line. The OPERATOR is
    expected to alert on this.

    Per the v9.27 Sanctum: this is the load-bearing anti-coercion
    observability primitive. If this never fires when it should,
    the duress-code mechanism (R11-5) is decorative.
    """
    _REGISTRY.duress_events.inc()
    structured_log("duress_event",
                   individual_id=individual_id,
                   agency_id=agency_id)


def structured_log(event: str, **fields) -> None:
    """Emit one JSON object per line to stdout.

    Format: `{"ts": "ISO8601", "pid": NNNN, "event": "...", ...fields}`.
    """
    record = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "pid": _REGISTRY.process_id,
        "event": event,
        "request_id": get_request_id(),
    }
    # v9.187 (P1.6) — the log half of the correlation join: while a span is
    # recording, every log line carries the trace/span ids. The hook must
    # never break logging (tracing is an accessory, the log stream is not).
    if _trace_context_provider is not None:
        try:
            _ids = _trace_context_provider()
            if _ids:
                record.update(_ids)
        except Exception:
            pass
    record.update(fields)
    try:
        sys.stdout.write(json.dumps(record, default=str) + "\n")
        sys.stdout.flush()
    except (OSError, ValueError):
        # Refuse to crash the request path on logging failure.
        pass


@dataclass(frozen=True)
class MetricsSnapshot:
    """The structure returned by /api/metrics."""
    request_rate_per_minute: float
    error_rate_per_minute: float
    auth_failures_per_minute: float
    duress_events_total: int
    uptime_seconds: int
    process_id: int

    @classmethod
    def collect(cls) -> "MetricsSnapshot":
        return cls(
            request_rate_per_minute=_REGISTRY.requests.rate_per_minute(),
            error_rate_per_minute=_REGISTRY.errors.rate_per_minute(),
            auth_failures_per_minute=_REGISTRY.auth_failures.rate_per_minute(),
            duress_events_total=_REGISTRY.duress_events.value(),
            uptime_seconds=int(time.time() - _REGISTRY.process_started_at),
            process_id=_REGISTRY.process_id,
        )

    def to_dict(self) -> dict:
        return {
            "request_rate_per_minute": self.request_rate_per_minute,
            "error_rate_per_minute": self.error_rate_per_minute,
            "auth_failures_per_minute": self.auth_failures_per_minute,
            "duress_events_total": self.duress_events_total,
            "uptime_seconds": self.uptime_seconds,
            "process_id": self.process_id,
        }
