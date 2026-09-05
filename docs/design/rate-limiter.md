# Rate limiting

**Reader:** an engineer or an assessor. **Job:** The per-IP defence, its backend, and its failure mode.

Per-IP rate limiting is the front-line defence against credential stuffing,
brute-force login and form spam (CWE-307, CWE-770). `_security_before_request`
in `app.py` invokes it on the login path and on every write path.

The backend choice is load-bearing in a way that is easy to miss: an in-process
limiter multiplies the configured cap by the worker count, and nothing in the
application's behaviour says so. The cap looks enforced until someone asks how.

## Two backends, one contract

| Backend | Defined in | Correct for | Failure mode |
|---|---|---|---|
| `InMemoryRateLimiter` | `security.py` | a single worker: development, tests, `flask run` | the bucket lives in process memory, so N workers enforce N times the cap |
| `RedisRateLimiter` | `security.py` | multiple workers, or multiple hosts | fails closed on a Redis error, and logs to stderr |

Both implement `_BaseRateLimiter`: `allow(key, max_events, window_seconds)`
returning a boolean, `reset(key=None)`, and `healthy()`.

## Selection

`_make_rate_limiter()` runs at module import and reads three variables:

- `POLARIS_RATE_LIMIT_BACKEND`: `auto`, `memory` or `redis`, defaulting to `auto`.
- `POLARIS_REDIS_URL`: required by the Redis backend.
- `POLARIS_WORKERS`: used only to decide whether to warn. `gunicorn.conf.py`
  re-exports the resolved worker count into the environment so the warning
  fires under the default configuration.

Under `auto`, Redis is chosen when `POLARIS_REDIS_URL` is set and reachable,
and the in-process limiter otherwise. A misconfiguration falls back to the
in-process limiter with a loud warning on stderr rather than refusing to start:
a rate-limiter configuration error must not take the whole service offline.

## Atomicity

The Redis backend is where the correctness lives. The naive shape, read the
count, decide, then write, has a window in which a burst slips past the cap.
`RedisRateLimiter` puts the whole decision in one Lua script,
`LUA_SLIDING_WINDOW`, which Redis evaluates atomically under its
single-threaded execution model:

1. `ZREMRANGEBYSCORE` drops entries older than the window.
2. `ZCARD` counts what remains.
3. At or above the maximum, it returns 0 and the request is denied.
4. Otherwise it `ZADD`s an entry under a unique nonce, sets `PEXPIRE` for
   housekeeping, and returns 1.

`test_concurrent_allows_respect_limit_atomically` runs fifty threads against a
single key with a maximum of ten and asserts exactly ten winners. A
non-atomic implementation lets extra winners through, and the test fails.

## Operating it

- `/api/health` reports `{rate_limiter: {backend, ok}}`. A monitor should page
  on `ok: false` sustained beyond a minute.
- When the limiter's Redis is down the application reports `degraded` rather
  than `unhealthy`: the rest of it keeps serving, and `allow()` fails closed.
- Sustained `degraded` therefore means new logins and writes are being refused
  with 429. Setting `POLARIS_RATE_LIMIT_BACKEND=memory` is an emergency
  stopgap, at the cost of multiplying the cap by the worker count.

## Details that have caused trouble

- The startup warning goes to stderr, not the audit log. Anyone watching only
  the audit trail will not see it; on a systemd host it is in the journal.
- `reset()` on Redis uses `SCAN` with `MATCH polaris:rl:*`, so a Redis
  instance shared with another application using that prefix is not safe.
- `secrets.token_hex(8)` supplies the per-call nonce, so two events in the
  same millisecond do not collapse into one sorted-set member. Reusing the
  timestamp as the member instead would silently overwrite the tied entry.
- The in-process backend relies on CPython's global interpreter lock for
  deque atomicity. That is a deliberate acceptance, not an oversight: adding a
  lock there changes the behaviour under contention and needs re-verification.

## Tests

In `test_app.py`:

- `_RateLimiterContractMixin`: seven invariants both backends must satisfy.
- `InMemoryRateLimiterTests` and `RedisRateLimiterTests` apply the mixin.
- `MultiProcessRateLimiterTests` proves the cap multiplication exists
  in-process and that Redis removes it, using two limiter instances against
  one Redis URL.
- `RateLimiterSelectionTests` covers the environment-to-backend matrix,
  including the fallback paths.
- `HealthEndpointTests.test_health_reports_rate_limiter_backend`.

The Redis tests skip when the test Redis is unreachable; it defaults to
`redis://localhost:6399/0` and `POLARIS_TEST_REDIS_URL` overrides it.
