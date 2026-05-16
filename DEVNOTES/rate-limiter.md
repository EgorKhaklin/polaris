# DEVNOTES/rate-limiter.md

Per-IP rate limiting (CWE-307 / CWE-770 mitigation) is the front-line defense
against credential-stuffing, brute-force login, and form-spam abuse. The
limiter is invoked from `_security_before_request` in `app.py` for both login
and write paths. This note exists because the wrong choice of backend silently
multiplies the configured cap by worker count — a quiet, dangerous failure
mode that doesn't surface until the security audit asks how the cap is
actually enforced.

## Backends

| Backend | Where defined | Correct for | Failure mode |
|---|---|---|---|
| `InMemoryRateLimiter` | `security.py` | single-worker dev / tests / `flask run` | bucket lives in process memory; multi-worker = `workers ×` configured cap |
| `RedisRateLimiter` | `security.py` | multi-worker / multi-host production | fails closed (deny) on Redis error; logs to stderr |

Both implement the same `_BaseRateLimiter` contract:
`allow(key, max_events, window_seconds) -> bool`,
`reset(key=None) -> None`,
`healthy() -> bool`.

## Selection

`_make_rate_limiter()` runs at module import. Reads:

- `POLARIS_RATE_LIMIT_BACKEND` — `auto` / `memory` / `redis` (default `auto`)
- `POLARIS_REDIS_URL` — required for Redis backend
- `POLARIS_WORKERS` — used only for the warning when in-memory is selected
  with > 1 worker. `gunicorn.conf.py` re-exports the resolved worker count
  to the env so the warning fires under the default config.

Auto behavior: pick Redis if `POLARIS_REDIS_URL` is set and reachable; else
in-memory. Misconfiguration falls back to in-memory + a loud stderr warning
— the application must not refuse to start over a rate-limiter config issue
because that takes the whole service offline.

## Atomicity

The Redis backend is the load-bearing part. Naive implementations (read
count → decide → write) have a TOCTOU window that lets bursts slip past
the cap. `RedisRateLimiter` runs the entire decision inside a single Lua
script (`LUA_SLIDING_WINDOW`), which Redis evaluates as one atomic operation
under its single-threaded execution model. The script:

1. `ZREMRANGEBYSCORE` — drop entries older than (now - window)
2. `ZCARD` — count what remains
3. If count >= max: return 0 (deny)
4. Else: `ZADD` a unique nonce-keyed entry; `PEXPIRE` the key for housekeeping; return 1

The contract test `test_concurrent_allows_respect_limit_atomically` runs 50
threads against a single key with max=10 and asserts exactly 10 wins. A
non-atomic implementation will let some wins slip past — and the test will
catch it.

## Operability

- `/api/health` reports `{rate_limiter: {backend, ok}}`. Monitors should page
  on `ok: false` for over 60 s.
- App returns `degraded` (not `unhealthy`) when the rate-limiter Redis is
  down — the rest of the app keeps serving and allow() fails-closed.
- Sustained `degraded` means new logins and writes are returning 429s.
  Operators can set `POLARIS_RATE_LIMIT_BACKEND=memory` as an emergency
  stopgap, but remember the cap multiplication.

## Common gotchas

- The startup warning is on stderr, not the audit log. If you're tailing
  audit only, you'll miss it. Watch journalctl in production.
- `reset()` in Redis uses `SCAN` with `MATCH polaris:rl:*`. Don't share a
  Redis instance with other apps using the same prefix.
- `secrets.token_hex(8)` provides the per-call nonce so two events at the
  same millisecond don't collapse into one sorted-set member. Don't try to
  "save space" by reusing the timestamp as the member — the score-tied entry
  would silently overwrite.
- The in-memory backend relies on CPython GIL guarantees for deque atomicity.
  This was accepted in the v4 audit. Adding a lock here is a regression risk
  — re-verify before changing.

## Tests

`test_app.py` has the full picture:
- `_RateLimiterContractMixin` — 7 invariants both backends must satisfy
- `InMemoryRateLimiterTests` / `RedisRateLimiterTests` — apply the mixin
- `MultiProcessRateLimiterTests` — proves the bug exists in-memory AND that
  Redis fixes it (two limiter instances sharing one Redis URL)
- `RateLimiterSelectionTests` — env → backend matrix, including fallback paths
- `HealthEndpointTests.test_health_reports_rate_limiter_backend`

Redis tests skip if the test Redis (default `redis://localhost:6399/0`) is
not reachable. Set `POLARIS_TEST_REDIS_URL` to override.
