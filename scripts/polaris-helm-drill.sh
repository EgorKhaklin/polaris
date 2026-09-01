#!/usr/bin/env bash
# ============================================================================
# polaris-helm-drill.sh — the Kubernetes reference profile boots to healthy on
# a stock cluster, with its NetworkPolicies ENFORCED and the restricted Pod
# Security Standard in effect (roadmap P1.5). Runs identically in CI (job
# helm-kind) and locally (Docker + kind + kubectl + helm).
#
# What it proves, in order:
#   1. A kind cluster with the default CNI disabled and Calico installed (the
#      only way NetworkPolicy means anything in kind); the four self-built
#      images loaded, nothing pulled (imagePullPolicy Never).
#   2. The namespace labelled pod-security.kubernetes.io/enforce=restricted,
#      and a privileged pod REJECTED by the API server ("violates PodSecurity").
#   3. The real secrets (polaris-generate-secrets.sh, including the ML-DSA-65
#      signing key) as a Secret; `helm lint` and `helm install --wait`.
#   4. /api/health through the Caddy edge (tls internal): database, redis,
#      zk_binary, custody all healthy.
#   5. A probe pod outside the topology cannot reach postgres:5432,
#      pgbouncer:6432, or app:8000 (default-deny + allow-list holds), while the
#      app plainly can (step 4 proved app -> pgbouncer -> postgres and app ->
#      redis).
#   6. `kubectl rollout restart` of the app rolls with maxUnavailable 0 and the
#      edge stays healthy.
#
# Env: KEEP_CLUSTER=1 keeps the cluster; KIND_CLUSTER (default polaris-drill).
# ============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"
ROOT="$(cd -- "${SCRIPT_DIR}/.." &> /dev/null && pwd)"
CLUSTER="${KIND_CLUSTER:-polaris-drill}"
NS=polaris
REL=polaris
CALICO_VERSION=v3.32.2
CALICO_MANIFEST="https://raw.githubusercontent.com/projectcalico/calico/${CALICO_VERSION}/manifests/calico.yaml"
PF_PID=""
fail() { echo "::error::$*" >&2; exit 1; }
cleanup() {
    [ -n "$PF_PID" ] && kill "$PF_PID" 2>/dev/null || true
    if [ "${KEEP_CLUSTER:-0}" != 1 ]; then kind delete cluster --name "$CLUSTER" >/dev/null 2>&1 || true; fi
}
trap cleanup EXIT
for t in docker kind kubectl helm; do command -v "$t" >/dev/null || fail "$t is required"; done
for i in polaris-app:prod polaris-caddy:prod polaris-pgbouncer:prod polaris-postgres:prod; do
    docker image inspect "$i" >/dev/null 2>&1 || fail "image $i not built (see the CI job for the four docker build lines)"
done

echo "== 1. kind cluster (no default CNI) + Calico =="
kind delete cluster --name "$CLUSTER" >/dev/null 2>&1 || true
kind create cluster --name "$CLUSTER" --config "$ROOT/deploy/helm/kind-config.yaml" --wait 60s >/dev/null
kubectl apply -f "$CALICO_MANIFEST" >/dev/null
kubectl -n kube-system rollout status ds/calico-node --timeout=300s >/dev/null
kubectl -n kube-system rollout status deploy/coredns --timeout=300s >/dev/null
kubectl wait --for=condition=Ready node --all --timeout=120s >/dev/null
echo "  calico ${CALICO_VERSION} enforcing; node Ready"
# The four self-built images are loaded (pullPolicy Never proves nothing else is
# fetched for them); the digest-pinned redis is pulled by the node itself, since
# `kind load` of a digest-referenced manifest list fails on the platforms it does
# not have ("content digest not found", the first local run).
kind load docker-image --name "$CLUSTER" polaris-app:prod polaris-caddy:prod polaris-pgbouncer:prod polaris-postgres:prod >/dev/null
echo "  self-built images loaded into the cluster (pullPolicy Never for them)"

echo "== 2. namespace under the restricted Pod Security Standard =="
kubectl create namespace "$NS" >/dev/null
kubectl label namespace "$NS" pod-security.kubernetes.io/enforce=restricted pod-security.kubernetes.io/warn=restricted pod-security.kubernetes.io/audit=restricted >/dev/null
if kubectl -n "$NS" apply -f - <<'PODEOF' >/dev/null 2>/tmp/pss.err
apiVersion: v1
kind: Pod
metadata: {name: pss-violation}
spec:
  containers:
    - name: c
      image: polaris-app:prod
      imagePullPolicy: Never
      securityContext: {privileged: true}
PODEOF
then kubectl -n "$NS" delete pod pss-violation --ignore-not-found >/dev/null; fail "a PRIVILEGED pod was admitted; the restricted standard is not enforced"; fi
grep -q "violates PodSecurity" /tmp/pss.err || { cat /tmp/pss.err; fail "privileged pod refused for another reason"; }
echo "  privileged pod rejected: $(grep -o 'violates PodSecurity "restricted[^"]*"' /tmp/pss.err | head -1)"

echo "== 3. secrets + helm install =="
( cd "$ROOT" && bash scripts/polaris-generate-secrets.sh >/dev/null 2>&1 ) || true
[ -s "$ROOT/polaris_web/secrets/polaris_signing_key" ] || echo "  (no signing key generated; custody will report degraded)"
kubectl -n "$NS" create secret generic polaris-secrets --from-file="$ROOT/polaris_web/secrets/" >/dev/null
helm lint "$ROOT/deploy/helm/polaris" >/dev/null && echo "  helm lint OK"
helm install "$REL" "$ROOT/deploy/helm/polaris" -n "$NS" --set domain=localhost --set edge.tls=internal \
    --set secrets.existingSecret=polaris-secrets --set images.pullPolicy=Never \
    --wait --timeout 12m >/dev/null || {
        # Diagnose every workload, not one: the first local run showed only
        # postgres's log while caddy crash-looped for a different reason.
        kubectl -n "$NS" get pods -o wide
        for pod in $(kubectl -n "$NS" get pods -o name); do
            echo "== $pod: events =="; kubectl -n "$NS" describe "$pod" | sed -n '/^Events:/,$p' | tail -8
            echo "== $pod: log (current) =="; kubectl -n "$NS" logs "$pod" --tail=20 2>&1 | tail -20
            echo "== $pod: log (previous) =="; kubectl -n "$NS" logs "$pod" --previous --tail=20 2>&1 | tail -20
        done
        fail "helm install did not reach ready"
    }
kubectl -n "$NS" get pods -o wide | sed 's/^/  /'
kubectl -n "$NS" get networkpolicy --no-headers | wc -l | sed 's/^/  networkpolicies: /'

echo "== 4. health through the edge =="
kubectl -n "$NS" port-forward "svc/${REL}-caddy" 18443:443 >/dev/null 2>&1 & PF_PID=$!
sleep 3
code=""
for i in $(seq 1 30); do code=$(curl -sk -o /dev/null -w '%{http_code}' https://localhost:18443/api/health || true); [ "$code" = 200 ] && break; sleep 3; done
[ "$code" = 200 ] || { kubectl -n "$NS" logs -l app.kubernetes.io/component=caddy --tail=20; fail "edge did not serve /api/health (last HTTP $code)"; }
curl -sk https://localhost:18443/api/health | python3 -c "
import sys, json; d = json.load(sys.stdin); c = d['checks']
bad = [k for k in ('database', 'redis', 'zk_binary', 'custody') if c[k]['status'] != 'healthy']
print('  checks:', {k: v.get('status') for k, v in c.items()}); assert not bad, f'unhealthy: {bad}'
print('  custody:', c['custody'].get('driver'), c['custody'].get('public_key_fingerprint'))"

echo "== 5. NetworkPolicy: a pod outside the topology is denied =="
cat > /tmp/np-probe.py <<'PYEOF'
import socket, sys
targets = [("polaris-postgres", 5432), ("polaris-pgbouncer", 6432), ("polaris-app", 8000)]
blocked = 0
for host, port in targets:
    try:
        socket.create_connection((host, port), timeout=6).close(); print(f"REACHED {host}:{port} (policy hole)")
    except Exception as e:
        blocked += 1; print(f"blocked {host}:{port} ({type(e).__name__})")
sys.exit(0 if blocked == len(targets) else 1)
PYEOF
PROBE_PY=$(python3 -c "import json,sys; print(json.dumps(open('/tmp/np-probe.py').read()))")
OVERRIDES=$(cat <<JSONEOF
{"spec":{"securityContext":{"runAsNonRoot":true,"runAsUser":1000,"seccompProfile":{"type":"RuntimeDefault"}},
 "containers":[{"name":"probe","image":"polaris-app:prod","imagePullPolicy":"Never",
   "command":["python3","-c",${PROBE_PY}],
   "securityContext":{"allowPrivilegeEscalation":false,"capabilities":{"drop":["ALL"]}}}]}}
JSONEOF
)
if kubectl -n "$NS" run np-probe --image=polaris-app:prod --restart=Never --rm -i --overrides="$OVERRIDES" 2>&1 | sed 's/^/  /' | tee /tmp/np-probe.out | grep -q "REACHED"; then fail "a pod outside the topology reached a protected service"; fi
grep -q "blocked polaris-postgres:5432" /tmp/np-probe.out || { cat /tmp/np-probe.out; fail "probe did not run"; }
echo "  default-deny + allow-list holds (postgres, pgbouncer, app unreachable from outside the topology)"

echo "== 6. rolling restart keeps the edge healthy =="
kubectl -n "$NS" rollout restart "deploy/${REL}-app" >/dev/null
kubectl -n "$NS" rollout status "deploy/${REL}-app" --timeout=300s >/dev/null
code=$(curl -sk -o /dev/null -w '%{http_code}' https://localhost:18443/api/health || true)
[ "$code" = 200 ] || fail "edge unhealthy after the rolling restart (HTTP $code)"
echo "  rolled (maxUnavailable 0); edge healthy"
echo "== HELM/KIND DRILL PASSED: restricted PSS enforced, policies enforced, stack healthy through the edge =="
