#!/usr/bin/env bash
# ============================================================================
# polaris-failover-drill.sh — induced failures against the HA profile, with
# every recovery measured under a live write stream (roadmap P2.7, v9.243).
#
# The HA profile (polaris_web/docker-compose.ha.yml) puts the database under
# Patroni: two members, a leader lease in a three-member etcd, HAProxy routing
# writes to whichever member holds the lease. This drill is the proof that the
# supervisor does what docs/operator/FAILOVER.md says, on a booted stack:
#
#   export POLARIS_DOMAIN=localhost
#   export POLARIS_COMPOSE_EXTRA="-f docker-compose.citest.yml -f docker-compose.bluegreen.yml -f docker-compose.ha.yml"
#   scripts/polaris-failover-drill.sh
#
# A writer inserts through the real client path (pgbouncer, HAProxy, the
# leader) four times a second and logs every attempt, so each scenario's
# "write gap" is the time between the first failed insert and the first
# successful one after it: what an application would have seen. Reads run
# against the edge as in the other drills.
#
#   1. The leader node is lost: its container is killed and stays down past
#      the lease. Patroni promotes the replica and writes resume within
#      CEIL_FAILOVER; when the node is started again it must rejoin as a
#      replica (pg_rewind) within CEIL_REJOIN. (A leader whose PROCESS crashes
#      and restarts inside its own lease is not a failover: Patroni restarts
#      it in place and keeps the lease, which is what a supervisor should do.)
#   2. The leader is cut off from the lease store only (its clients can still
#      reach it). It must demote itself within CEIL_DEMOTE, the other member
#      must take the lease, writes must resume, and it must rejoin as a
#      replica once reconnected. This is the split-brain guard, exercised.
#   3. A planned switchover (patronictl). The write gap must stay under
#      CEIL_SWITCHOVER; the old leader must follow as a replica.
#   4. One etcd member crashes. The leader must NOT change, no write may
#      fail, and the member must restart on its own within CEIL_RESTART.
#
# The ceilings are hard assertions, the same discipline as the window and
# chaos drills. The measured numbers are the ones FAILOVER.md states.
# ============================================================================
set -euo pipefail
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"
ROOT="$(cd -- "${SCRIPT_DIR}/.." &> /dev/null && pwd)"
URL="${POLARIS_DRILL_URL:-https://localhost:8443}"
OUT="${POLARIS_FAILOVER_OUT:-}"
CEIL_FAILOVER="${POLARIS_FAILOVER_CEIL_FAILOVER:-60}"
CEIL_REJOIN="${POLARIS_FAILOVER_CEIL_REJOIN:-120}"
CEIL_DEMOTE="${POLARIS_FAILOVER_CEIL_DEMOTE:-45}"
CEIL_SWITCHOVER="${POLARIS_FAILOVER_CEIL_SWITCHOVER:-30}"
CEIL_RESTART="${POLARIS_FAILOVER_CEIL_RESTART:-60}"
read -r -a COMPOSE_EXTRA <<< "${POLARIS_COMPOSE_EXTRA:-}"
compose() { (cd "$ROOT/polaris_web" && docker compose -f docker-compose.prod.yml "${COMPOSE_EXTRA[@]}" "$@"); }
WORK="$(mktemp -d)"
[[ -n "$OUT" ]] || OUT="$WORK/failover.json"
PY_IMAGE="python:3.12-alpine@sha256:d81968c559557b881aa557ff6d1200acec8e72a2c85fcb4ad1806e8d13e09f0b"
WRITER=polaris-ha-writer
SECRETS="${POLARIS_SECRETS_DIR:-$ROOT/polaris_web/secrets}"
VERSION="$(sed -n 's/^__version__: str = "\(.*\)"/\1/p' "$ROOT/polaris_web/__version__.py")"
GIT="$(git -C "$ROOT" rev-parse --short HEAD 2>/dev/null || echo unknown)"
DCS_NET=""; PARTITIONED=""; PARTITION_ALIAS_ARGS=()

fail() { echo "::error::$*" >&2; exit 1; }
cleanup() {
    if [[ -n "${TRAFFIC_PID:-}" ]]; then kill -TERM "$TRAFFIC_PID" 2>/dev/null || true; wait "$TRAFFIC_PID" 2>/dev/null || true; fi
    docker rm -f "$WRITER" >/dev/null 2>&1 || true
    if [[ -n "$PARTITIONED" && -n "$DCS_NET" ]]; then
        docker network connect ${PARTITION_ALIAS_ARGS[@]+"${PARTITION_ALIAS_ARGS[@]}"} "$DCS_NET" "polaris-$PARTITIONED" >/dev/null 2>&1 || true
    fi
    rm -rf "$WORK"
}
trap cleanup EXIT

# --- primitives -----------------------------------------------------------------
now() { python3 -c "import time; print(time.time())"; }
elapsed() { python3 -c "import sys,time; print(int(round(time.time() - float(sys.argv[1]))))" "$1"; }
wait_for() {  # wait_for SECONDS FN ... -> prints elapsed seconds; returns 1 on timeout
    local limit="$1"; shift; local t0 i; t0=$(date +%s)
    for i in $(seq 1 "$limit"); do if "$@"; then echo $(( $(date +%s) - t0 )); return 0; fi; sleep 1; done
    echo "$limit"; return 1
}
crash() {  # SIGKILL the container's init from the host pid namespace: a crash the restart policy answers
    local pid; pid=$(docker inspect -f '{{.State.Pid}}' "$1")
    [[ "$pid" =~ ^[0-9]+$ && "$pid" -gt 1 ]] || fail "cannot resolve the init pid of $1"
    docker run --rm --privileged --pid=host "$PY_IMAGE" kill -9 "$pid" >/dev/null
}
rest() { docker exec "polaris-$1" wget -qO- "http://127.0.0.1:8008$2" 2>/dev/null; }
cluster_field() {  # cluster_field VIA FIELD [MEMBER]: leader | role MEMBER | state MEMBER | lag MEMBER | timeline MEMBER
    rest "$1" /cluster | python3 -c "
import json, sys
d = json.load(sys.stdin); what = sys.argv[1]; who = sys.argv[2] if len(sys.argv) > 2 else None
ms = d.get('members', [])
if what == 'leader': print(next((m['name'] for m in ms if m.get('role') == 'leader'), '')); sys.exit()
m = next((m for m in ms if m['name'] == who), None)
print('' if m is None else m.get(what, ''))" "$2" "${3:-}" 2>/dev/null || true
}
leader_via() { cluster_field "$1" leader; }
leader() {  # ask either member; the survivor answers when one is down
    local l; l=$(leader_via postgres); [[ -n "$l" ]] || l=$(leader_via postgres2); echo "$l"
}
other() { [[ "$1" == postgres ]] && echo postgres2 || echo postgres; }
is_primary() { rest "$1" /primary >/dev/null; }
not_primary() { ! is_primary "$1"; }
leader_is() { [[ "$(leader_via "$2")" == "$1" ]]; }
leader_changed_from() { local l; l=$(leader_via "$2"); [[ -n "$l" && "$l" != "$1" ]]; }
replica_streaming() {  # replica_streaming MEMBER VIA
    [[ "$(cluster_field "$2" role "$1")" == "replica" && "$(cluster_field "$2" state "$1")" == "streaming" ]]
}
container_healthy() { [[ "$(docker inspect --format '{{.State.Health.Status}}' "$1" 2>/dev/null)" == "healthy" ]]; }
edge_ok() { curl -sk -o /dev/null -w '%{http_code}' "$URL/api/health" 2>/dev/null | grep -q 200; }
writes_ok_since() {  # an insert succeeded after T
    python3 -c "
import sys
t = float(sys.argv[2])
ok = [float(l.split()[0]) for l in open(sys.argv[1]) if l.strip().endswith(' ok')]
sys.exit(0 if any(x > t for x in ok) else 1)" "$WORK/state/writes.log" "$1" 2>/dev/null
}
gap_since() {  # gap_since T0 -> "gap_s fails stall_s": the failed-insert span, the failed count, and the longest
               # interval between two successful inserts since T0 (a queued insert stalls rather than fails)
    python3 -c "
import sys
t0 = float(sys.argv[2]); allrows = [(float(a), b) for a, b in (l.split() for l in open(sys.argv[1]) if l.strip())]
rows = [(t, s) for t, s in allrows if t >= t0]
fails = [t for t, s in rows if s == 'fail']
gap = 0.0
if fails:
    first, last = min(fails), max(fails)
    after = [t for t, s in rows if s == 'ok' and t > last]
    gap = (min(after) - first) if after else (last - first)
oks = [t for t, s in rows if s == 'ok']
before = [t for t, s in allrows if s == 'ok' and t < t0]
seq = ([max(before)] if before else []) + oks
stall = max((b - a for a, b in zip(seq, seq[1:])), default=0.0)
print(f'{gap:.1f} {len(fails)} {stall:.1f}')" "$WORK/state/writes.log" "$1"
}
outage() { python3 -c "import sys; print(max(float(sys.argv[1]), float(sys.argv[2])))" "$1" "$2"; }
le() { python3 -c "import sys; sys.exit(0 if float(sys.argv[1]) <= float(sys.argv[2]) else 1)" "$1" "$2"; }

# --- the write stream and the read traffic ---------------------------------------
cat > "$WORK/writer.py" <<'PYEOF'
import os, signal, sys, time
import psycopg
dsn = os.environ["DSN"]; log = open("/state/writes.log", "a", buffering=1)
stop = False
signal.signal(signal.SIGTERM, lambda *a: globals().__setitem__("stop", True))
while not stop:
    t = time.time()
    try:
        with psycopg.connect(dsn, connect_timeout=3, autocommit=True) as c:
            c.execute("INSERT INTO ha_marker DEFAULT VALUES")
        log.write(f"{t:.3f} ok\n")
    except Exception:
        log.write(f"{t:.3f} fail\n")
    time.sleep(0.25)
PYEOF
cat > "$WORK/traffic.py" <<'PYEOF'
import json, signal, ssl, sys, threading, time, urllib.request
base = sys.argv[1]; out = sys.argv[2]
ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
stats = {"requests": 0, "served": 0, "drops": 0, "by": {}}
lock = threading.Lock(); stop = threading.Event()
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
            if key == "ok": stats["served"] += 1
            elif key != "http_429": stats["drops"] += 1
            stats["by"][key] = stats["by"].get(key, 0) + 1
        time.sleep(0.25)
threads = [threading.Thread(target=worker, args=(p,), daemon=True) for p in ["/api/health/live"] * 2 + ["/api/health"] * 2]
[t.start() for t in threads]
while not stop.is_set(): time.sleep(0.2)
time.sleep(0.5)
with open(out, "w") as fh: json.dump(stats, fh)
PYEOF
settle() {  # the write stream must be flowing before a scenario starts its clock
    local t; t=$(now); wait_for 60 writes_ok_since "$t" >/dev/null || fail "writes are not flowing before the next scenario"
}
traffic_start() { : > "$1"; python3 "$WORK/traffic.py" "$URL" "$1" & TRAFFIC_PID=$!; }
traffic_stop()  { kill -TERM "$TRAFFIC_PID" 2>/dev/null || true; wait "$TRAFFIC_PID" 2>/dev/null || true; TRAFFIC_PID=""; }
drops() { python3 -c "import json,sys; d=json.load(open(sys.argv[1])); print(d['drops'], 'of', d['requests'])" "$1"; }

echo "== failover drill: v$VERSION @ $GIT, against $URL =="
edge_ok || fail "edge not healthy before the drill"
NET=$(compose config --format json | python3 -c "import json,sys; print(json.load(sys.stdin)['networks']['polaris-net']['name'])")
DCS_NET=$(compose config --format json | python3 -c "import json,sys; print(json.load(sys.stdin)['networks']['polaris-dcs']['name'])")
[[ -n "$NET" && -n "$DCS_NET" ]] || fail "could not resolve the stack networks (is docker-compose.ha.yml in POLARIS_COMPOSE_EXTRA?)"
L0=$(leader); [[ -n "$L0" ]] || fail "no Patroni leader reachable"
R0=$(other "$L0")
replica_streaming "$R0" "$L0" || fail "$R0 is not a streaming replica of $L0 before the drill ($(cluster_field "$L0" role "$R0")/$(cluster_field "$L0" state "$R0"))"
echo "  leader $L0, replica $R0 streaming, timeline $(cluster_field "$L0" timeline "$L0")"

# The marker table the writer fills, created on the leader by the superuser
# over the local socket (pg_hba: local trust, like the stock image).
docker exec "polaris-$L0" psql -h /var/run/postgresql -U postgres -d polaris -v ON_ERROR_STOP=1 -q \
    -c "CREATE TABLE IF NOT EXISTS ha_marker (id bigserial PRIMARY KEY, ts timestamptz NOT NULL DEFAULT clock_timestamp());" \
    -c "GRANT INSERT ON ha_marker TO polaris_app; GRANT USAGE ON SEQUENCE ha_marker_id_seq TO polaris_app;" \
    || fail "could not create the marker table on $L0"
mkdir -p "$WORK/state"; : > "$WORK/state/writes.log"; chmod 0777 "$WORK/state"; chmod 0644 "$WORK/writer.py"
APP_PW=$(cat "$SECRETS/polaris_db_password")
docker rm -f "$WRITER" >/dev/null 2>&1 || true
docker run -d --name "$WRITER" --network "$NET" \
    -e DSN="host=pgbouncer port=6432 dbname=polaris user=polaris_app password=$APP_PW sslmode=require application_name=ha_drill" \
    -v "$WORK/writer.py:/writer.py:ro" -v "$WORK/state:/state" --entrypoint python3 polaris-postgres:prod /writer.py >/dev/null
t=$(now); wait_for 30 writes_ok_since "$t" >/dev/null || { docker logs "$WRITER" 2>&1 | tail -5 >&2; fail "the writer never completed an insert through pgbouncer and HAProxy"; }
echo "  writes flowing through pgbouncer -> pg-router -> $L0"

# --- 1. the leader node is lost ------------------------------------------------------
settle
echo "== 1. the leader node ($L0) is lost: killed, and it stays down past the lease =="
traffic_start "$WORK/s1.json"
t0=$(now)
docker kill -s KILL "polaris-$L0" >/dev/null   # a manual stop to Docker: no restart, the node is gone
p1=$(wait_for "$CEIL_FAILOVER" leader_changed_from "$L0" "$R0") || fail "no new leader within ${CEIL_FAILOVER}s of losing the leader"
L1=$(leader_via "$R0"); [[ "$L1" == "$R0" ]] || fail "the new leader is $L1, not the surviving replica $R0"
w1=$(wait_for "$CEIL_FAILOVER" writes_ok_since "$t0") || fail "writes did not resume within ${CEIL_FAILOVER}s of losing the leader"
read -r gap1 fails1 stall1 <<< "$(gap_since "$t0")"; out1=$(outage "$gap1" "$stall1")
compose start "$L0" >/dev/null 2>&1 || fail "could not start $L0 again"
j1=$(wait_for "$CEIL_REJOIN" replica_streaming "$L0" "$L1") || fail "$L0 did not rejoin as a streaming replica within ${CEIL_REJOIN}s of starting again"
sleep 2; traffic_stop
tl1=$(cluster_field "$L1" timeline "$L1")
echo "  promoted $L1 after ${p1}s; writes: ${fails1} failed (span ${gap1}s), longest stall ${stall1}s, outage ${out1}s; $L0 rejoined as a replica ${j1}s after it was started; timeline $tl1; reads dropped $(drops "$WORK/s1.json")"
le "$out1" "$CEIL_FAILOVER" || fail "write outage ${out1}s exceeds the ${CEIL_FAILOVER}s ceiling"
[[ "$(cluster_field "$L1" timeline "$L0")" == "$tl1" ]] || fail "$L0 is on timeline $(cluster_field "$L1" timeline "$L0"), the leader on $tl1: it did not follow"

# --- 2. the leader is cut off from the lease store -------------------------------------
settle
echo "== 2. the leader ($L1) is cut off from the lease store; its clients can still reach it =="
PARTITION_ALIAS_ARGS=()
while IFS= read -r a; do [[ -n "$a" ]] && PARTITION_ALIAS_ARGS+=(--alias "$a"); done < <(docker inspect -f '{{json (index .NetworkSettings.Networks "'"$DCS_NET"'").Aliases}}' "polaris-$L1" \
    | python3 -c "import json,sys; [print(a) for a in (json.load(sys.stdin) or [])]")
traffic_start "$WORK/s2.json"
t0=$(now)
docker network disconnect "$DCS_NET" "polaris-$L1"; PARTITIONED="$L1"
d2=$(wait_for "$CEIL_DEMOTE" not_primary "$L1") || fail "$L1 kept answering /primary for ${CEIL_DEMOTE}s without its lease: the split-brain guard did not hold"
p2=$(wait_for "$CEIL_FAILOVER" leader_is "$L0" "$L0") || fail "$L0 did not take the lease within ${CEIL_FAILOVER}s"
w2=$(wait_for "$CEIL_FAILOVER" writes_ok_since "$t0") || fail "writes did not resume within ${CEIL_FAILOVER}s of the partition"
docker network connect "${PARTITION_ALIAS_ARGS[@]}" "$DCS_NET" "polaris-$L1"; PARTITIONED=""
j2=$(wait_for "$CEIL_REJOIN" replica_streaming "$L1" "$L0") || fail "$L1 did not rejoin as a streaming replica within ${CEIL_REJOIN}s of reconnecting"
sleep 2; traffic_stop
read -r gap2 fails2 stall2 <<< "$(gap_since "$t0")"; out2=$(outage "$gap2" "$stall2")
echo "  $L1 demoted itself after ${d2}s; $L0 took the lease after ${p2}s; writes: ${fails2} failed (span ${gap2}s), longest stall ${stall2}s, outage ${out2}s; $L1 rejoined after ${j2}s; reads dropped $(drops "$WORK/s2.json")"
le "$out2" "$CEIL_FAILOVER" || fail "write outage ${out2}s exceeds the ${CEIL_FAILOVER}s ceiling"
L2="$L0"

# --- 3. a planned switchover ------------------------------------------------------------
settle
echo "== 3. a planned switchover ($L2 -> $L1) =="
traffic_start "$WORK/s3.json"
t0=$(now)
docker exec "polaris-$L2" patronictl -c /var/lib/postgresql/patroni.yml switchover --primary "$L2" --candidate "$L1" --force >/dev/null 2>&1 \
    || fail "patronictl switchover failed"
p3=$(wait_for "$CEIL_SWITCHOVER" leader_is "$L1" "$L1") || fail "$L1 did not become leader within ${CEIL_SWITCHOVER}s of the switchover"
w3=$(wait_for "$CEIL_SWITCHOVER" writes_ok_since "$t0") || fail "writes did not resume within ${CEIL_SWITCHOVER}s of the switchover"
j3=$(wait_for "$CEIL_REJOIN" replica_streaming "$L2" "$L1") || fail "$L2 did not follow as a streaming replica within ${CEIL_REJOIN}s"
sleep 2; traffic_stop
read -r gap3 fails3 stall3 <<< "$(gap_since "$t0")"; out3=$(outage "$gap3" "$stall3")
echo "  $L1 leader after ${p3}s; writes: ${fails3} failed (span ${gap3}s), longest stall ${stall3}s, outage ${out3}s; $L2 follows after ${j3}s; reads dropped $(drops "$WORK/s3.json")"
le "$out3" "$CEIL_SWITCHOVER" || fail "switchover write outage ${out3}s exceeds the ${CEIL_SWITCHOVER}s ceiling"

# --- 4. an etcd member crashes ----------------------------------------------------------
settle
echo "== 4. one etcd member (etcd1) crashes =="
traffic_start "$WORK/s4.json"
t0=$(now)
crash polaris-etcd1
sleep 25
[[ "$(leader_via "$L1")" == "$L1" ]] || fail "the leader changed when one etcd member crashed; the quorum did not hold"
read -r gap4 fails4 stall4 <<< "$(gap_since "$t0")"
[[ "$fails4" -eq 0 ]] || fail "${fails4} inserts failed while one etcd member was down; the quorum must carry the lease"
le "$stall4" 5 || fail "writes stalled ${stall4}s while one etcd member was down; the quorum must carry the lease"
r4=$(wait_for "$CEIL_RESTART" container_healthy polaris-etcd1) || fail "etcd1 did not restart healthy within ${CEIL_RESTART}s"
sleep 2; traffic_stop
echo "  leader unchanged, 0 failed inserts, longest stall ${stall4}s; etcd1 back healthy after ${r4}s; reads dropped $(drops "$WORK/s4.json")"

wait_for 30 edge_ok >/dev/null || fail "stack not healthy at the end of the drill"
python3 - "$OUT" "$p1" "$out1" "$fails1" "$stall1" "$j1" "$d2" "$p2" "$out2" "$fails2" "$stall2" "$j2" "$p3" "$out3" "$fails3" "$stall3" "$j3" "$stall4" "$r4" <<'PYEOF'
import json, sys
o, p1, o1, f1, s1, j1, d2, p2, o2, f2, s2, j2, p3, o3, f3, s3, j3, s4, r4 = sys.argv[1:]
summary = {
    "leader_lost":           {"promoted_s": int(p1), "write_outage_s": float(o1), "failed_inserts": int(f1), "longest_stall_s": float(s1), "rejoined_s": int(j1)},
    "leader_cut_from_dcs":   {"demoted_s": int(d2), "promoted_s": int(p2), "write_outage_s": float(o2), "failed_inserts": int(f2), "longest_stall_s": float(s2), "rejoined_s": int(j2)},
    "switchover":            {"promoted_s": int(p3), "write_outage_s": float(o3), "failed_inserts": int(f3), "longest_stall_s": float(s3), "followed_s": int(j3)},
    "etcd_member_crashed":   {"leader_changed": False, "failed_inserts": 0, "longest_stall_s": float(s4), "restarted_s": int(r4)},
}
json.dump(summary, open(o, "w"), indent=2); print(json.dumps(summary))
PYEOF
echo "== FAILOVER DRILL PASSED: the replica took over a lost leader, a leader without its lease stood down, a switchover was a short gap, and the quorum carried an etcd crash =="
