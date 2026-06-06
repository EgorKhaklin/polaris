# docs/operator/ — runbooks for operators

Polaris's deployment + day-2 operations + compliance documentation.
For developers contributing to Polaris, see
[`DEVNOTES/`](../../DEVNOTES/).

---

## What's here

| Doc | When you need it |
|---|---|
| [`INSTALL.md`](INSTALL.md) | Initial environment setup; system requirements |
| [`DEPLOYMENT.md`](DEPLOYMENT.md) | Three deployment paths (dev / staging / prod) |
| [`OPERATIONS.md`](OPERATIONS.md) | **Day-2 runbook (~1700 lines)** — backup, restore, scaling, monitoring, archive, purge, pre-commit, certificate transparency |
| [`SECRETS.md`](SECRETS.md) | Env-var matrix + rotation cadence + KMS paved paths |
| [`SECURITY.md`](SECURITY.md) | Cybersecurity posture + audit + controls |
| [`PRIVACY.md`](PRIVACY.md) | Data minimization + operational privacy posture |
| [`DR.md`](DR.md) | Disaster recovery procedures (RPO ≤1min / RTO ≤30min) |
| [`FAILOVER.md`](FAILOVER.md) | Streaming replication + hot standby + promotion runbook; the HA complement to DR.md (standby host operator-supplied) |
| [`ENCRYPTION-AT-REST.md`](ENCRYPTION-AT-REST.md) | At-rest posture: what is plaintext on disk, what is already encrypted, and the operator-gated host volume encryption path |
| [`SLOS.md`](SLOS.md) | Reference SLO targets (availability / request-latency / DB-latency) + error budget, grounded in exposed metrics; backend operator-gated |
| [`RUNBOOKS.md`](RUNBOOKS.md) | One alert-response runbook per shipped Prometheus alert (Trigger / Diagnosis / Remediation) |

---

## Reading order

**First-time deploy:**
1. [INSTALL.md](INSTALL.md) — get the deps right
2. [DEPLOYMENT.md](DEPLOYMENT.md) — pick a path
3. [SECRETS.md](SECRETS.md) — generate + rotate
4. [OPERATIONS.md](OPERATIONS.md) §"Quick start (5 min)" — actual deploy
5. [OPERATIONS.md](OPERATIONS.md) §"Verify" — confirm

**Compliance audit:**
1. [SECURITY.md](SECURITY.md) — STRIDE + controls
2. [PRIVACY.md](PRIVACY.md) — data minimization posture
3. [DR.md](DR.md) — RPO/RTO targets + drills

**Production incident:**
1. [OPERATIONS.md](OPERATIONS.md) §"Incident response"
2. [OPERATIONS.md](OPERATIONS.md) §"Common errors"
3. [DR.md](DR.md) §"Failure-class procedures" (8 named classes)

**Day-to-day:**
- Cron rows: [OPERATIONS.md](OPERATIONS.md) §"Day-2 operations"
- Health: `curl /api/health` (structured JSON)
- Metrics: `curl /metrics` (Prometheus; v8.93)

---

## Conventions

- Each doc opens with a one-paragraph purpose statement
- Tables prefer "When you need it" framing over "What it covers"
- Code blocks prefer copy-pasteable shell over prose recipes
- Cron schedules + retention windows are explicit
- Exit codes are named (`EXIT_OK=0`, `EXIT_SHA_MISMATCH=4`, etc.)

See [`docs/CONVENTIONS.md`](../CONVENTIONS.md) for project-wide
naming + structural conventions.

---

## What this directory is NOT

- Not technical reference (that's in [`../reference/`](../reference/))
- Not narrative (that's in [`../story/`](../story/))
- Not the academic write-up (that's in [`../paper/`](../paper/))
- Not informal developer notes (that's in [`../../DEVNOTES/`](../../DEVNOTES/))
- Not strategic decision records

`docs/operator/` is **what an operator needs to deploy and run
Polaris in production**, written so the operator never has to
read the source code to do their job.
