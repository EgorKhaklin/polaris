# SYSTEM-MAP — the architectural centerpiece

**Polaris's complete structure, named.** Every directory's role, every
package's purpose, every cross-reference made explicit. This is the
single best entry point for understanding the project's shape.

For naming + structural conventions see [`../CONVENTIONS.md`](../CONVENTIONS.md).
For the philosophical principles beneath the structure, see
[`../story/PRINCIPLES.md`](../story/PRINCIPLES.md).

---

## At a glance

```
polaris/                          ← repo root
│
├── README.md                     ← portfolio front-page
├── MISSION.md                    ← constitution (C1-C10 + Vocation)
├── ROADMAP.md                    ← prioritized backlog (R-* items)
├── CHANGELOG.md                  ← audit-of-record (every ship)
├── CLAUDE.md                     ← agent runbook
├── CONTRIBUTING.md / SECURITY.md ← contributor guide + vulnerability disclosure
├── LICENSE / NOTICE              ← legal
│
├── Polaris.command               ← double-click launcher (macOS)
├── polaris_mac_launch.sh         ← launcher logic
│
├── polaris_web/        ← Flask app (app.py + WebAuthn + ZK wrapper)
│   ├── Dockerfile / docker-compose.yml            ← dev image + dev stack
│   ├── Dockerfile.prod / docker-compose.prod.yml  ← prod image + full prod stack
│   ├── Dockerfile.caddy / Caddyfile               ← self-built TLS edge (rate_limit compiled in)
│   ├── Dockerfile.pgbouncer / pgbouncer.ini       ← self-built connection pooler
│   ├── Dockerfile.postgres / pgbackrest.conf      ← DB image + WAL-archiving config
│   └── gunicorn.conf.py                           ← prod WSGI config
├── polaris_sql/        ← schema, procedures, triggers, atlas, migrations
├── polaris_zk/         ← Plonky2 ZK-SNARK Rust crate + witness2/ second witness
├── polaris_cli/        ← CLI utilities
├── polaris_checks/     ← flat C1-C10 invariant layer
│
├── deploy/             ← observability configs (prometheus.yml + polaris-alerts.yml)
├── docs/               ← all documentation (operator runbooks + reference + story + paper + PRODUCTION-READINESS.md)
├── meta/               ← structural records (constraint lattice, redaction proof, TLA+)
├── DEVNOTES/           ← informal developer notes
├── scripts/            ← operator (polaris-*) + workflow (ai-*) scripts
├── assets/             ← branding (logo)
│
├── .git/               ← genesis 2026-05-15
├── .github/workflows/  ← CI (ci.yml; 7 jobs, named below)
├── .gitignore          ← venv, caches, secrets, .DS_Store, .hypothesis
└── .pre-commit-config.yaml  ← local hooks (link-check, invariants)
```

**CI jobs** ([`.github/workflows/ci.yml`](../../.github/workflows/ci.yml)):

- `test`: the product suite against Postgres 16; checks layer, DB suites, ZK build + prove-verify roundtrip, encrypted backup/restore round-trip.
- `docker-image`: builds + smoke-boots the dev and prod images; pgbouncer, verify-ca pinning, streaming-replication, and pgBackRest round-trips.
- `caddy-edge`: builds the self-built Caddy image, validates the real prod Caddyfile, proves the X25519MLKEM768 post-quantum hybrid KEX.
- `pqc-real`: real ML-DSA-65 sign + verify (liboqs), cross-checked by the cryptography second witness.
- `cve-scan`: dependency CVE audit (pip-audit) + SAST (bandit).
- `image-cve-scan`: Trivy scan of the self-built prod images; gates on fixable CRITICALs.
- `prod-stack-boot`: boots the full prod compose end to end on Linux and asserts `/api/health` serves through the TLS edge.

---

## The three layers

Polaris is built in **three layers**, each with a distinct role.
Understanding the layer-of-the-thing tells you 90% of what you need.

### Layer 1: Polaris itself (the identity-token system)

The actual product — the thing being built.

| Layer-1 dir | What |
|---|---|
| [`polaris_web/`](../../polaris_web/) | Flask web app — routes; 28 schema tables; ZK wrapper; WebAuthn |
| [`polaris_sql/`](../../polaris_sql/) | DDL + procedures + triggers + atlas functions + migrations |
| [`polaris_zk/`](../../polaris_zk/) | Rust crate — Plonky2 ZK-SNARK prover/verifier + `witness2/` independent second witness |
| [`polaris_cli/`](../../polaris_cli/) | CLI utilities |

### Layer 2: Checks and structural records

The flat invariant layer plus the structural records.

| Layer-2 dir | What |
|---|---|
| [`polaris_checks/`](../../polaris_checks/) | Flat C1-C10 invariant layer — one `check_*(repo_root)` per constraint; gates CI via `python3 -m polaris_checks.run` |
| [`scripts/`](../../scripts/) | operator (polaris-*) + workflow (ai-*) scripts |
| [`meta/`](../../meta/) | Structural records (constraint lattice, redaction proof, structural architecture, TLA+ models) |

### Layer 3: Documentation (for humans)

What the operator + developer + auditor needs to read.

| Layer-3 dir | What |
|---|---|
| [`docs/operator/`](../operator/) | Runbooks (INSTALL, DEPLOYMENT, OPERATIONS, DR, FAILOVER, SECRETS, SECURITY, PRIVACY, RUNBOOKS, SLOS, ENCRYPTION-AT-REST, WEBAUTHN-ROLLOUT) |
| [`docs/reference/`](../reference/) | Technical reference (API, DATA-MODEL, GLOSSARY, SCALING, PQC-POSTURE, **this SYSTEM-MAP**) |
| [`docs/story/`](../story/) | Principles (PRINCIPLES) |
| [`docs/paper/`](../paper/) | Academic write-up |
| [`DEVNOTES/`](../../DEVNOTES/) | Informal developer notes (cross-cutting + per-ship in `ships/`) |

---

## The constitutional spine

These documents are the load-bearing constitutional surfaces.

```
MISSION.md (constitution)
    ├── C1-C10 hard constraints (enforced at the DB level)
    ├── The Vocation (anti-coercion)
    └── Mission v1 + v2 done-lists

polaris_checks/checks.py (machine-checkable enforcement of C1-C10)
meta/constraint-lattice.md (how C1-C10 compose and depend on each other)

CHANGELOG.md (every ship; never edited retroactively)
```

---

## Cross-reference quick map

**"Where do I look for X?"** (matches CLAUDE.md's table; replicated
here for self-contained navigation):

| Question | Look here |
|---|---|
| What is Polaris? What is it NOT? | [`MISSION.md`](../../MISSION.md) |
| What's next? | [`ROADMAP.md`](../../ROADMAP.md) |
| What just shipped? | [`CHANGELOG.md`](../../CHANGELOG.md) (top entry = latest) |
| Agent runbook / onboarding | [`CLAUDE.md`](../../CLAUDE.md) |
| How do C1-C10 compose? | [`meta/constraint-lattice.md`](../../meta/constraint-lattice.md) |
| Cross-cutting principle (AoR, concurrency, threat-model, style) | [`DEVNOTES/<name>.md`](../../DEVNOTES/) |
| How does ship X work? | [`DEVNOTES/ships/<short-name>.md`](../../DEVNOTES/ships/) |
| Naming + structural conventions | [`docs/CONVENTIONS.md`](../CONVENTIONS.md) |
| Architectural map (this doc) | [`docs/reference/SYSTEM-MAP.md`](SYSTEM-MAP.md) |
| The C1-C10 checks | [`polaris_checks/checks.py`](../../polaris_checks/checks.py) |

---

## Who reads what

| Audience | Primary reading order |
|---|---|
| **Agent (Claude) starting a fresh session** | [`CLAUDE.md`](../../CLAUDE.md) → [`MISSION.md`](../../MISSION.md) → `python3 -m polaris_checks.run` |
| **Operator deploying Polaris** | [`docs/operator/INSTALL.md`](../operator/INSTALL.md) → [`docs/operator/DEPLOYMENT.md`](../operator/DEPLOYMENT.md) → [`docs/operator/OPERATIONS.md`](../operator/OPERATIONS.md) |
| **Developer contributing** | [`README.md`](../../README.md) → [`docs/CONVENTIONS.md`](../CONVENTIONS.md) → [`DEVNOTES/style.md`](../../DEVNOTES/style.md) → relevant `polaris_*/README.md` |
| **Compliance auditor** | [`docs/operator/SECURITY.md`](../operator/SECURITY.md) → [`docs/operator/PRIVACY.md`](../operator/PRIVACY.md) → [`docs/operator/DR.md`](../operator/DR.md) |
| **Academic reviewer** | `docs/paper/polaris_project_report.pdf` → [`docs/THESIS.md`](../THESIS.md) → [`docs/story/PRINCIPLES.md`](../story/PRINCIPLES.md) |

---

## What this document is NOT

- Not source code (that's in `polaris_*/`)
- Not the constitution (that's `MISSION.md`)
- Not informal notes (those are `DEVNOTES/`)
- Not the structural records (those are in `meta/`)

`SYSTEM-MAP.md` is **the architectural centerpiece** — the single
document that, if read in full, gives a complete sense of how
Polaris's many parts fit together.

Last refreshed: 2026-06-10 (v9.142, production-surface refresh).
