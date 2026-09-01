#!/usr/bin/env bash
# ============================================================================
# polaris-rolling-drill.sh — prove a rolling deploy drops ZERO requests
# (roadmap P1.4), with a negative control so "zero" cannot be vacuous.
#
# Run against a production stack already up with the blue-green overlay
# (and, in CI or locally without a public domain, the internal-CA edge):
#
#   export POLARIS_DOMAIN=localhost
#   export POLARIS_COMPOSE_EXTRA="-f docker-compose.citest.yml -f docker-compose.bluegreen.yml"
#   scripts/polaris-rolling-drill.sh            # POLARIS_DRILL_URL defaults to https://localhost:8443
#
# What it does:
#   1. Starts a traffic generator (8 threads, continuous GETs against the edge:
#      /api/health/live and /api/health; every non-200 and every transport
#      error is a DROP) and records the container ids of both app colours.
#   2. Runs `polaris-deploy.sh prod --no-pull` under that traffic: infra up,
#      migrations, app-green recreated and health-waited, then app.
#   3. Stops the traffic and asserts drops == 0 with a meaningful request
#      count, and that BOTH app containers were replaced (new ids).
#   4. Negative control: stops both colours for 20s under the same traffic
#      (longer than Caddy's lb_try_duration) and asserts drops > 0, then
#      starts them again and asserts health. A generator that cannot see an
#      outage would make step 3 meaningless (the P0.4 vacuous-scenario lesson).
# ============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"
ROOT="$(cd -- "${SCRIPT_DIR}/.." &> /dev/null && pwd)"
URL="${POLARIS_DRILL_URL:-https://localhost:8443}"
read -r -a COMPOSE_EXTRA <<< "${POLARIS_COMPOSE_EXTRA:-}"
compose() { (cd "$ROOT/polaris_web" && docker compose -f docker-compose.prod.yml "${COMPOSE_EXTRA[@]}" "$@"); }
WORK="$(mktemp -d)"
fail() { echo "::error::$*" >&2; exit 1; }

cat > "$WORK/traffic.py" <<'PYEOF'
import json, os, signal, ssl, sys, threading, time, urllib.request
base = sys.argv[1]; out = sys.argv[2]
ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
stats = {"requests": 0, "drops": 0, "by": {}}; lock = threading.Lock(); stop = threading.Event()
signal.signal(signal.SIGTERM, lambda *a: stop.set())
def worker(path):
    while not stop.is_set():
        key = "ok"
        try:
            with urllib.request.urlopen(base + path, timeout=5, context=ctx) as r:
                if r.status != 200: key = f"http_{r.status}"
        except urllib.error.HTTPError as e: key = f"http_{e.code}"
        except Exception as e: key = "transport:" + type(e).__name__
        with lock:
            stats["requests"] += 1
            # 429 is the edge's own rate limiter enforcing policy (the CI Caddyfile
            # allows 1000/min); it is neither a served request nor a drop.
            if key == "ok": stats["served"] = stats.get("served", 0) + 1
            elif key != "http_429": stats["drops"] += 1
            stats["by"][key] = stats["by"].get(key, 0) + 1
        time.sleep(0.35)
# 4 threads x ~2.5 rps stays well under the edge rate limit for a multi-minute drill.
threads = [threading.Thread(target=worker, args=(p,), daemon=True) for p in ["/api/health/live"] * 3 + ["/api/health"]]
[t.start() for t in threads]
while not stop.is_set(): time.sleep(0.2)
time.sleep(0.5)
with open(out, "w") as fh: json.dump(stats, fh)
PYEOF

traffic_start() { : > "$1"; python3 "$WORK/traffic.py" "$URL" "$1" & TRAFFIC_PID=$!; sleep 3; }
traffic_stop()  { kill -TERM "$TRAFFIC_PID" 2>/dev/null || true; wait "$TRAFFIC_PID" 2>/dev/null || true; cat "$1"; echo; }
cid() { compose ps -q "$1" | head -1; }

echo "== preflight: both colours up and the edge answers =="
compose config --services | grep -qx app-green || fail "the blue-green overlay is not active (set POLARIS_COMPOSE_EXTRA)"
for i in $(seq 1 30); do curl -sk -o /dev/null -w '%{http_code}' "$URL/api/health" | grep -q 200 && break; sleep 2; done
curl -sk -o /dev/null -w '%{http_code}\n' "$URL/api/health" | grep -q 200 || fail "edge not healthy before the drill"
BLUE0=$(cid app); GREEN0=$(cid app-green); [ -n "$BLUE0" ] && [ -n "$GREEN0" ] || fail "app containers not found"
echo "  app=$BLUE0 app-green=$GREEN0"

echo "== 1-2. rolling deploy under traffic =="
traffic_start "$WORK/deploy.json"
# Full output, unfiltered: the first local run hid the deploy's fatal error
# behind a grep for the lines I expected to see.
( cd "$ROOT" && POLARIS_DOMAIN="${POLARIS_DOMAIN:-localhost}" bash scripts/polaris-deploy.sh prod --no-pull ) 2>&1 | sed 's/^/    deploy: /' || true
sleep 3
traffic_stop "$WORK/deploy.json"
BLUE1=$(cid app); GREEN1=$(cid app-green)
python3 - "$WORK/deploy.json" "$BLUE0" "$BLUE1" "$GREEN0" "$GREEN1" <<'PYEOF'
import json, sys
s = json.load(open(sys.argv[1])); b0, b1, g0, g1 = sys.argv[2:6]
print(f"  during the rolling deploy: {s['requests']} requests, {s.get('served', 0)} served, {s['drops']} drops, breakdown {s['by']}")
assert s.get("served", 0) >= 150, "too few served requests to mean anything"
assert b0 != b1 and g0 != g1, "both app containers must have been replaced"
assert s["drops"] == 0, f"{s['drops']} requests dropped during the rolling deploy"
print("  ZERO dropped requests; both colours replaced")
PYEOF

echo "== 4. negative control: both colours stopped for 20s under traffic =="
traffic_start "$WORK/control.json"
compose stop -t 1 app app-green >/dev/null 2>&1
sleep 20
compose start app app-green >/dev/null 2>&1
sleep 3
traffic_stop "$WORK/control.json"
python3 - "$WORK/control.json" <<'PYEOF'
import json, sys
s = json.load(open(sys.argv[1]))
print(f"  during the outage: {s['requests']} requests, {s.get('served', 0)} served, {s['drops']} drops, breakdown {s['by']}")
assert s["drops"] > 0, "the traffic generator saw no drops during a 20s outage: it cannot detect drops"
print("  the generator detects an outage (control valid)")
PYEOF
for i in $(seq 1 45); do curl -sk -o /dev/null -w '%{http_code}' "$URL/api/health" | grep -q 200 && break; sleep 2; done
curl -sk -o /dev/null -w '%{http_code}\n' "$URL/api/health" | grep -q 200 || fail "stack not healthy after the control"
rm -rf "$WORK"
echo "== ROLLING DEPLOY DRILL PASSED: zero drops under traffic, control detected the outage =="
