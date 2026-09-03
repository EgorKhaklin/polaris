# SYSTEM-MAP: the shape of the repository

**Reader:** anyone opening the repository for the first time. **Job:** every
directory's role, every package's purpose, every CI job, and who reads what.
Naming and structural conventions are in [../CONVENTIONS.md](../CONVENTIONS.md).

---

## At a glance

```
polaris/
│
├── README.md                     ← the front page
├── MISSION.md                    ← the constitution (C1-C10 and the vocation)
├── ROADMAP.md                    ← the build plan, P0 to P7
├── CHANGELOG.md                  ← every ship, never edited retroactively
├── CLAUDE.md                     ← the developer and agent runbook
├── CONTRIBUTING.md / SECURITY.md ← contributor guide; vulnerability disclosure
├── LICENSE / NOTICE              ← Apache 2.0; provenance and third-party notices
│
├── Polaris.command               ← double-click launcher (macOS)
├── polaris_mac_launch.sh         ← launcher logic
│
├── polaris_web/        ← the Flask application
│   ├── app.py / security.py / webauthn_auth.py / custody.py / pqc_signing.py
│   ├── templates/ static/                         ← Jinja2 templates; external-only JS and CSS
│   ├── Dockerfile / docker-compose.yml            ← dev image and dev stack
│   ├── Dockerfile.prod / docker-compose.prod.yml  ← prod image and the five-service stack
│   ├── docker-compose.bluegreen.yml               ← the zero-downtime profile
│   ├── Dockerfile.caddy / Caddyfile               ← self-built TLS edge (rate_limit compiled in)
│   ├── Dockerfile.pgbouncer / pgbouncer.ini       ← self-built connection pooler
│   ├── Dockerfile.postgres / pgbackrest.conf      ← database image with WAL archiving
│   └── gunicorn.conf.py                           ← prod WSGI config
├── polaris_sql/        ← schema, procedures, triggers, atlas functions, migrations/
├── polaris_zk/         ← Plonky2 ZK-SNARK Rust crate; witness2/ is the independent second witness
├── polaris_cli/        ← the operator CLI
├── polaris_checks/     ← the flat invariant layer that gates CI
│
├── deploy/
│   ├── helm/polaris/   ← the Kubernetes reference profile (plus kind-config.yaml for CI)
│   ├── linux/          ← install.sh and the systemd units and timers
│   └── observability/  ← Prometheus, Alertmanager, alert rules and their tests, Grafana dashboards, Tempo
├── docs/
│   ├── ARCHITECTURE-OVERVIEW.md, PRODUCTION-READINESS.md, RED-TEAM-SCOPE.md, THESIS.md, SEED_DATA.md, CONVENTIONS.md
│   ├── operator/       ← the runbooks (seventeen documents and an index)
│   ├── reference/      ← this directory
│   └── paper/          ← the academic report (TeX and PDF)
├── DEVNOTES/           ← design notes, the project record, per-ship notes under ships/
├── meta/               ← structural records (redaction proof, structural architecture, the TLA+ model)
├── scripts/            ← operator tools (polaris-*) and the workflow scripts (ai-*)
├── assets/             ← the logo and the Atlas captures
├── site/               ← the demo website (GitHub Pages)
│
├── .github/workflows/  ← ci.yml (14 jobs), dr-drill.yml (monthly), sbom.yml (per release), pages.yml (the site)
├── .github/dependabot.yml, .pre-commit-config.yaml, .gitignore, .coveragerc, .trivyignore
```

**CI jobs** ([`.github/workflows/ci.yml`](../../.github/workflows/ci.yml)):

- `test`: the product suite against Postgres 16 and Redis; the checks layer, the DB suites, the ZK build and prove-verify round trip, the encrypted backup and restore round trip, the abuse drill, the performance smoke.
- `docker-image`: builds and smoke-boots the dev and prod images; PgBouncer, verify-ca pinning, streaming replication and pgBackRest round trips, including the off-site S3 drill.
- `caddy-edge`: builds the self-built Caddy image, validates the real prod Caddyfile, proves the X25519MLKEM768 post-quantum hybrid KEX.
- `page-drill`: the duress page path, Prometheus rules through Alertmanager to the pager webhook.
- `trace-drill`: the tracing wire drill and dashboards-as-code validation.
- `dr-drill`: kills the primary, restores from the WAL archive, measures RPO and RTO against the targets in DR.md.
- `linux-install`: the Linux server install, systemd on the runner plus Debian 12 and Rocky 9 package stages.
- `custody-pkcs11`: key custody through PKCS#11 (Kryoptic token, ML-DSA-65 in-token, two-witness verified).
- `rolling-deploy`: a rolling deploy under traffic drops zero requests (blue-green profile and control).
- `helm-kind`: the Kubernetes reference profile boots to healthy on kind with Calico-enforced policies and restricted PSS.
- `pqc-real`: real ML-DSA-65 sign and verify (liboqs), cross-checked by the cryptography second witness.
- `cve-scan`: dependency CVE audit (pip-audit) plus SAST (bandit).
- `image-cve-scan`: Trivy scan of the self-built prod images; gates on fixable CRITICALs.
- `prod-stack-boot`: boots the full prod compose end to end and asserts `/api/health` serves through the TLS edge.

`dr-drill.yml` runs the same drill monthly and commits the measured row to
[`docs/operator/DR-DRILLS.md`](../operator/DR-DRILLS.md). `sbom.yml` attaches
SPDX bills of materials with SLSA provenance to every release. `pages.yml`
publishes `site/`.

---

## The three layers

### Layer 1: the product

| Directory | What |
|---|---|
| [`polaris_sql/`](../../polaris_sql/) | The schema (29 tables, 33 in a migrated deployment), procedures, triggers, atlas functions, migrations. The security boundary. |
| [`polaris_web/`](../../polaris_web/) | The Flask application: every route, the security layer, WebAuthn, custody and signing, tracing, the Atlas. |
| [`polaris_zk/`](../../polaris_zk/) | The Plonky2 Merkle-inclusion prover and verifier in Rust, and `witness2/`, the independent Python re-derivation. |
| [`polaris_cli/`](../../polaris_cli/) | The operator CLI: the same operations without a browser. |

### Layer 2: enforcement and tooling

| Directory | What |
|---|---|
| [`polaris_checks/`](../../polaris_checks/) | The flat invariant layer: plain `check_*(repo_root)` functions with detection tests; `python3 -m polaris_checks.run` gates CI. |
| [`scripts/`](../../scripts/) | Operator tools (`polaris-*`): deploy, backup, restore, drills, migration, secrets, recovery. Workflow scripts (`ai-*`): the ship gate, the link checker, the test wrapper, coverage. |
| [`deploy/`](../../deploy/) | The Helm profile, the Linux install and units, the observability configuration. |
| [`meta/`](../../meta/) | Structural records: the redaction proof, the structural-architecture note, the TLA+ model of C3. |

### Layer 3: documentation

| Directory | What |
|---|---|
| [`docs/operator/`](../operator/README.md) | INSTALL, DEPLOYMENT, LINUX-SERVER, KUBERNETES, HARDENING, OPERATIONS, SECRETS, KEY-CEREMONY, SECURITY, PRIVACY, DR, DR-DRILLS (ledger), FAILOVER, ENCRYPTION-AT-REST, SLOS, RUNBOOKS, WEBAUTHN-ROLLOUT |
| [`docs/reference/`](README.md) | API, DATA-MODEL, PQC-POSTURE, PERFORMANCE-BASELINE, SCALING, GLOSSARY, this map |
| [`docs/`](../README.md) | ARCHITECTURE-OVERVIEW, PRODUCTION-READINESS (the bound on every claim), RED-TEAM-SCOPE, THESIS, SEED_DATA, CONVENTIONS |
| [`docs/paper/`](../paper/) | The academic report |
| [`DEVNOTES/`](../../DEVNOTES/) | Design notes (audit of record, concurrency, threat model, substrate, ZK soundness, the two-witness principle, style), the project record, and one note per major ship under `ships/` |

---

## The constitutional spine

```
MISSION.md                         the constitution: C1-C10 and the vocation
polaris_checks/checks.py           the machine-checkable enforcement, gating CI
docs/PRODUCTION-READINESS.md       the bound on every claim: what is open, and who decides it
ROADMAP.md                         what comes next, phase by phase
CHANGELOG.md                       every ship, never edited retroactively
```

---

## Where do I look for X?

| Question | Look here |
|---|---|
| What is Polaris? What is it not? | [`MISSION.md`](../../MISSION.md) |
| Can it hold real identity data yet? | [`docs/PRODUCTION-READINESS.md`](../PRODUCTION-READINESS.md) |
| What is next? | [`ROADMAP.md`](../../ROADMAP.md) |
| What just shipped? | [`CHANGELOG.md`](../../CHANGELOG.md) (top entry is the latest) |
| How do I work on it? | [`CLAUDE.md`](../../CLAUDE.md), [`CONTRIBUTING.md`](../../CONTRIBUTING.md) |
| How is it built, layer by layer? | [`docs/ARCHITECTURE-OVERVIEW.md`](../ARCHITECTURE-OVERVIEW.md) |
| A cross-cutting design question (audit of record, concurrency, threat model) | [`DEVNOTES/`](../../DEVNOTES/README.md) |
| How does ship X work? | [`DEVNOTES/ships/`](../../DEVNOTES/ships/) |
| Naming and structural conventions | [`docs/CONVENTIONS.md`](../CONVENTIONS.md) |
| The checks | [`polaris_checks/checks.py`](../../polaris_checks/checks.py) |

---

## Who reads what

| Reader | Order |
|---|---|
| An operator deploying Polaris | [INSTALL.md](../operator/INSTALL.md) or [LINUX-SERVER.md](../operator/LINUX-SERVER.md) or [KUBERNETES.md](../operator/KUBERNETES.md), then [OPERATIONS.md](../operator/OPERATIONS.md), [SECRETS.md](../operator/SECRETS.md), [DR.md](../operator/DR.md) |
| An assessor | [PRODUCTION-READINESS.md](../PRODUCTION-READINESS.md), [SECURITY.md](../operator/SECURITY.md), [PRIVACY.md](../operator/PRIVACY.md), [PQC-POSTURE.md](PQC-POSTURE.md), [RED-TEAM-SCOPE.md](../RED-TEAM-SCOPE.md) |
| An integrator | [API.md](API.md), then [DATA-MODEL.md](DATA-MODEL.md) |
| A contributor, human or agent | [CLAUDE.md](../../CLAUDE.md), [MISSION.md](../../MISSION.md), then `python3 -m polaris_checks.run` |
| An academic reviewer | [the report](../paper/README.md), then [THESIS.md](../THESIS.md) |

Last regenerated: 2026-09-02 (v9.198).
