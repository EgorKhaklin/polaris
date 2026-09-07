#!/usr/bin/env python3
"""
polaris-verify-load.py — authenticated verify-AT-USE load for the HA drills
(roadmap P2.9, v9.259). Pure stdlib — no external deps, so it runs on a bare
CI runner exactly like scripts/polaris_load_gen.py and the drills' traffic.py.

It exercises the login-gated, replica-routed cryptographic verification
endpoint `GET /api/tokens/<id>/verify` (v9.258) the way a relying party would:
log in ONCE, keep the session cookie, and re-verify a set of known-active
tokens at a steady rate. The drills run this alongside their health traffic so
the certification is about the REAL verification path, not just a liveness ping.

Two modes:

  --continuous (default): N threads hit the endpoint until SIGTERM, then a
      {requests, served, drops, by} summary is written to --out. This is the
      SAME JSON shape the drills' traffic.py emits, so a drill's drops() helper
      reads it unchanged.

  --once: log in, issue ONE verification, exit 0 iff it returned HTTP 200
      (retrying a few times first). This is the post-failover RECOVERY probe:
      "is verification being served again?" A fresh login each call also proves
      the auth write-path recovered.

Strict accounting, matching the drills' traffic.py: only HTTP 200 is "served".
429 is the edge's own rate limiter enforcing policy (not a served request and
not a drop) and is tolerated. EVERYTHING else is a DROP: a 302 (the session was
lost, so it bounced to /login), a 5xx (a backend gap during a failover), a
transport error. A rolling deploy must drop ZERO; a database failover will drop
for the failover window and then recover, which is what the drills assert
respectively.

The demo operator accounts are disabled in production (docker-init.sh), so the
drill bootstraps a real admin first and passes it here as --login USER:PASS.
"""
import argparse
import http.cookiejar
import json
import signal
import ssl
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """Do not follow 3xx: a 302 to /login means the session was lost, which is a
    DROP, not a success. Suppressing the redirect surfaces the 302 as an
    HTTPError the caller ledgers by code (same contract as polaris_load_gen.py)."""
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def build_opener():
    """One opener with a shared cookie jar (so a --login session persists across
    every worker thread) and TLS verification off (the drills use Caddy's
    internal CA on localhost, exactly like their traffic.py)."""
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    jar = http.cookiejar.CookieJar()
    return urllib.request.build_opener(
        urllib.request.HTTPCookieProcessor(jar),
        urllib.request.HTTPSHandler(context=ctx),
        _NoRedirect())


def _post_login(opener, base, user, password, timeout=10.0):
    """POST /login; return the HTTP status. A 302 is success (the session cookie
    is now in the opener's jar). The suppressed redirect arrives as HTTPError."""
    body = urllib.parse.urlencode(
        {"username": user, "password": password}).encode("utf-8")
    req = urllib.request.Request(base + "/login", data=body, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    try:
        with opener.open(req, timeout=timeout) as resp:
            return resp.status
    except urllib.error.HTTPError as e:
        return e.code
    except (urllib.error.URLError, ConnectionError, TimeoutError):
        return None


def _get_status(opener, url, timeout=5.0):
    """GET url; return its HTTP status, or None on a transport failure."""
    try:
        with opener.open(url, timeout=timeout) as resp:
            resp.read(64 * 1024)
            return resp.status
    except urllib.error.HTTPError as e:
        return e.code
    except (urllib.error.URLError, ConnectionError, TimeoutError):
        return None


def classify(status):
    """Map an HTTP status (None = transport failure) to (outcome, ledger_key),
    outcome in {'served', 'tolerated', 'drop'}. This is the whole accounting
    policy, factored out so it is directly testable: ONLY 200 is served; 429 is
    the edge's rate limiter (tolerated, neither served nor dropped); EVERYTHING
    else is a drop — a 302 (session lost -> bounced to /login), a 5xx (a backend
    gap during a failover), or a transport error."""
    if status == 200:
        return "served", "ok"
    if status == 429:
        return "tolerated", "http_429"
    if status is None:
        return "drop", "transport"
    return "drop", f"http_{status}"


def run_once(base, user, password, token_ids, retries=5, sleep_s=1.0):
    """Recovery probe: log in and verify one token, retrying so a just-recovered
    stack (write path back a beat after reads) still passes. 0 iff a 200."""
    tok = token_ids[0]
    for attempt in range(1, retries + 1):
        opener = build_opener()
        if _post_login(opener, base, user, password) == 302:
            if _get_status(opener, base + f"/api/tokens/{tok}/verify") == 200:
                print(f"verify recovered: /api/tokens/{tok}/verify = 200 "
                      f"(attempt {attempt})")
                return 0
        if attempt < retries:
            time.sleep(sleep_s)
    print(f"verify did NOT recover after {retries} attempts", file=sys.stderr)
    return 1


def run_continuous(base, user, password, token_ids, out, threads, interval):
    """Hold a steady verify load until SIGTERM, then write the served/drops
    ledger to `out`. Login failure is fatal (exit 2) so a drill fails loudly
    rather than silently measuring an unauthenticated 302 storm."""
    opener = build_opener()
    code = _post_login(opener, base, user, password)
    if code != 302:
        sys.stderr.write(
            f"verify-load: login as {user!r} failed: HTTP {code} "
            f"(the drill must bootstrap a real admin first)\n")
        return 2

    stats = {"requests": 0, "served": 0, "drops": 0, "by": {}}
    lock = threading.Lock()
    stop = threading.Event()
    signal.signal(signal.SIGTERM, lambda *a: stop.set())
    signal.signal(signal.SIGINT, lambda *a: stop.set())

    def worker(start_idx):
        i = start_idx
        while not stop.is_set():
            tok = token_ids[i % len(token_ids)]
            i += 1
            status = _get_status(opener, base + f"/api/tokens/{tok}/verify")
            outcome, key = classify(status)
            with lock:
                stats["requests"] += 1
                if outcome == "served":
                    stats["served"] += 1
                elif outcome == "drop":
                    stats["drops"] += 1
                stats["by"][key] = stats["by"].get(key, 0) + 1
            time.sleep(interval)

    ts = [threading.Thread(target=worker, args=(w,), daemon=True)
          for w in range(threads)]
    for t in ts:
        t.start()
    while not stop.is_set():
        time.sleep(0.2)
    time.sleep(0.5)   # let in-flight requests land in the ledger
    with open(out, "w") as fh:
        json.dump(stats, fh)
    print(f"verify-load: {stats['served']} served, {stats['drops']} dropped "
          f"of {stats['requests']} ({stats['by']})")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="Authenticated verify-at-use load.")
    ap.add_argument("--url", required=True,
                    help="base origin, e.g. https://localhost:8443")
    ap.add_argument("--login", required=True, metavar="USER:PASS")
    ap.add_argument("--token-ids", default="2,3,4",
                    help="comma-separated active token ids to verify (default 2,3,4)")
    ap.add_argument("--out", default=None, help="JSON summary path (continuous mode)")
    ap.add_argument("--threads", type=int, default=4)
    ap.add_argument("--interval", type=float, default=0.25,
                    help="seconds between a worker's requests (default 0.25)")
    ap.add_argument("--once", action="store_true",
                    help="single recovery probe: exit 0 iff one verify returns 200")
    args = ap.parse_args(argv)

    base = args.url.rstrip("/")
    user, _, password = args.login.partition(":")
    token_ids = [s.strip() for s in args.token_ids.split(",") if s.strip()]
    if not token_ids:
        ap.error("--token-ids must name at least one token id")

    if args.once:
        return run_once(base, user, password, token_ids)
    if not args.out:
        ap.error("--out is required in continuous mode")
    return run_continuous(base, user, password, token_ids,
                          args.out, args.threads, args.interval)


if __name__ == "__main__":
    raise SystemExit(main())
