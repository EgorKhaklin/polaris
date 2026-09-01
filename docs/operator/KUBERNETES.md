# KUBERNETES.md: the Helm reference profile

The production topology on a Kubernetes cluster (roadmap P1.5):
[`deploy/helm/polaris`](../../deploy/helm/polaris). Docker Compose on one Linux
host ([`LINUX-SERVER.md`](LINUX-SERVER.md)) remains the single-node path; this
profile is for an authority whose platform is a cluster. It is a reference
profile, not an operator: one PostgreSQL replica, the cluster's own storage,
backups through pgBackRest exactly as on compose.

## What the chart deploys

| Workload | Kind | Runs as | Notes |
|---|---|---|---|
| `caddy` | Deployment | uid 1000 | the TLS edge on 8080/8443 (Service 80/443); `tls: internal` or ACME; 200 req/min/IP; retries onto another app pod for 15s; polls `/api/health/live` every 2s |
| `app` | Deployment, 2 replicas | uid 1000 | `maxUnavailable: 0`, readiness on `/api/health/live`, PodDisruptionBudget `minAvailable: 1` |
| `pgbouncer` | Deployment | uid 1000 | transaction pooling, TLS to postgres (verify-ca) and from the app |
| `postgres` | StatefulSet + PVCs | uid 70 | the self-contained image (schema, migrations, init, pgBackRest config baked in); `PGDATA` in a subdirectory of the volume; TLS on |
| `redis` | StatefulSet + PVC | uid 999 | sessions and rate-limit state |

Every pod satisfies the **restricted** Pod Security Standard: non-root with a
numeric uid, `seccompProfile: RuntimeDefault`, all capabilities dropped, no
privilege escalation. **NetworkPolicies** default-deny both directions for
every pod, then allow only the topology: internet to caddy, caddy to app, app
to pgbouncer and redis, pgbouncer to postgres, DNS for all, ACME egress for
caddy only with `edge.tls=acme`, S3 egress for postgres only with pgBackRest
enabled.

## Prerequisites

- Kubernetes 1.29+ with a CNI that **enforces** NetworkPolicy (Calico, Cilium,
  Antrea, most managed clusters). kind's default kindnet does not; the drill
  installs Calico.
- A default StorageClass (three PVCs: postgres data, pgBackRest repo, redis).
- For `edge.tls=acme`: a LoadBalancer Service reachable on 80/443 and the
  domain's DNS pointing at it before the first install.
- The four images in a registry your nodes can pull from (`images.*` in
  values), or `kind load docker-image` for a local cluster. Polaris publishes
  no registry images yet (P0.6 deferred image signing for that reason), so
  build and push them yourself:
  ```bash
  docker build -f polaris_web/Dockerfile.prod      -t REGISTRY/polaris-app:9.186       .
  docker build -f polaris_web/Dockerfile.caddy     -t REGISTRY/polaris-caddy:9.186     polaris_web
  docker build -f polaris_web/Dockerfile.pgbouncer -t REGISTRY/polaris-pgbouncer:9.186 polaris_web
  docker build -f polaris_web/Dockerfile.postgres  -t REGISTRY/polaris-postgres:9.186  .
  ```

## Install

```bash
kubectl create namespace polaris
kubectl label namespace polaris pod-security.kubernetes.io/enforce=restricted \
  pod-security.kubernetes.io/warn=restricted pod-security.kubernetes.io/audit=restricted

# Secrets: the same generator as compose (it mints the ML-DSA-65 signing key
# through the built app image), then one Secret holding every file.
./scripts/polaris-generate-secrets.sh
kubectl -n polaris create secret generic polaris-secrets --from-file=polaris_web/secrets/

helm install polaris deploy/helm/polaris -n polaris \
  --set domain=polaris.example.org --set edge.tls=acme --set edge.service.type=LoadBalancer \
  --set secrets.existingSecret=polaris-secrets \
  --set images.app=REGISTRY/polaris-app:9.186 --set images.caddy=REGISTRY/polaris-caddy:9.186 \
  --set images.pgbouncer=REGISTRY/polaris-pgbouncer:9.186 --set images.postgres=REGISTRY/polaris-postgres:9.186 \
  --wait --timeout 12m
```

Without `secrets.existingSecret` the chart generates random passwords and
self-signed PostgreSQL/pgbouncer certificates (kept across upgrades), but it
cannot mint a signing key, so `/api/health` reports custody degraded until you
add `polaris_signing_key` to the Secret ([`KEY-CEREMONY.md`](KEY-CEREMONY.md);
the PKCS#11 and KMS custody drivers work here too, through the same env).

The v9.189 session and origin controls (`POLARIS_NETWORK_POLICY_<ROLE>`,
`POLARIS_SESSION_MAX_<ROLE>`, `POLARIS_SESSION_IDLE_MINUTES_<ROLE>`, and the
`POLARIS_WEBAUTHN_*` attestation policy) go in `app.extraEnv` as
`{name, value}` pairs; a malformed value refuses the pod's boot, which the
startup probe surfaces. [`HARDENING.md`](HARDENING.md) section 13.

## Verify

```bash
kubectl -n polaris get pods
kubectl -n polaris port-forward svc/polaris-caddy 8443:443 &
curl -k https://localhost:8443/api/health | python3 -m json.tool     # database, redis, zk_binary, custody: healthy
```

## Operate

- **Upgrade** (a new image tag or chart change): `helm upgrade polaris
  deploy/helm/polaris -n polaris --reuse-values --set images.app=...`. The app
  Deployment rolls with `maxUnavailable: 0` and readiness gating, the
  Kubernetes-native form of the P1.4 zero-downtime deploy; the edge retries
  onto the remaining pod while one is replaced.
- **Migrations** follow the expand-contract policy
  (`polaris_sql/migrations/README.md`); the postgres image applies pending
  migrations at init and `scripts/polaris-migrate.sh` can be run against the
  pod (`kubectl exec`).
- **Rotate a secret**: update the Secret (`kubectl create secret ... --dry-run
  -o yaml | kubectl apply -f -`), then `kubectl rollout restart` the consumers
  (app, pgbouncer for the DB password; postgres needs the role updated first,
  as `polaris-rotate-secret.sh` does on compose).
- **Backups**: `pgbackrest.enabled=true` with the S3 values and the key pair in
  the Secret's `pgbackrest_repo_creds.conf` ([`DR.md`](DR.md)).
- **Observability**: `/metrics` is served by the app pods; scrape it from
  inside the cluster (the NetworkPolicy allows ingress to the app only from
  caddy; add a rule for your Prometheus namespace). Alerting and paging:
  [`deploy/observability/`](../../deploy/observability/README.md).

## How this is tested

`scripts/polaris-helm-drill.sh`, run by the `helm-kind` CI job on every push:
a kind cluster with the default CNI disabled and Calico installed, the four
self-built images loaded (pull policy Never; redis pulled by its pinned digest),
the namespace labelled restricted and a
privileged pod rejected by the API server, the real secrets as a Secret,
`helm lint` and `helm install --wait`, `/api/health` through the edge with
database, redis, zk_binary, and custody healthy, a probe pod outside the
topology denied by policy on postgres, pgbouncer, and app, and a rolling
restart that keeps the edge healthy. Stated limits: single-node kind, one
postgres replica, `tls: internal`; HA PostgreSQL, multi-node placement, and
ACME are P2 and operator-environment concerns.
