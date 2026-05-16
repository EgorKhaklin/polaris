# scripts/ — the cognitive + operator command surface

Two families of scripts live here:

- **`ai-*.sh`** (39 scripts) — the cognitive layer: how the agent
  primes a session, proposes moves, runs HYDRA, journals decisions,
  reflects at end-of-session. Read by humans + agents alike.
- **`polaris-*.sh`** (30 scripts) — the operator layer: deploy,
  backup, restore, archive, purge, rotate secrets, generate
  recovery codes. Used by the human running Polaris in production.

Plus a few `*.py` helpers that scripts shell out to (`ai_brain_map.py`,
`ai_swarm_bloom.py`, `polaris_load_gen.py`).

---

## Quick reference (the load-bearing eight)

| Script | What it does |
|---|---|
| [`ai-prime.sh`](ai-prime.sh) | 80-line session primer — run this first |
| [`ai-status.sh`](ai-status.sh) | Where Polaris is vs MISSION.md (constraints + done-list) |
| [`ai-propose.sh`](ai-propose.sh) | Top-N next moves from ROADMAP / BACKLOG |
| [`ai-architect.sh`](ai-architect.sh) | Architect-persona brief (with `--save` / `--reflect` modes) |
| [`ai-hydra.sh`](ai-hydra.sh) | HYDRA swarm synthesis (v9.04: `--full / --actions / --save / --diff`) |
| [`ai-sanctum.sh`](ai-sanctum.sh) | Open / close strategic-consultation sessions |
| [`ai-journal.sh`](ai-journal.sh) | Episodic memory: capture decisions / learnings / bugs |
| [`ai-done.sh`](ai-done.sh) | Pre-ship 14-check gate |

The full inventory is one command away:

```bash
bash scripts/ai-help.sh           # index of every ai-* script with one-line + flags
bash scripts/ai-help.sh hydra     # full doc for one script
```

---

## ai-* scripts (cognitive layer; 39 scripts)

Grouped by lifecycle (matches `ai-help.sh` output):

### Onboarding & planning
- [`ai-prime.sh`](ai-prime.sh) — single-command session primer
- [`ai-mission.sh`](ai-mission.sh) — re-ground on what Polaris is + isn't
- [`ai-status.sh`](ai-status.sh) — constraints + done-list state
- [`ai-propose.sh`](ai-propose.sh) — top-N next moves
- [`ai-bootstrap.sh`](ai-bootstrap.sh) — sanity check + spin-up

### Working & shipping
- [`ai-test.sh`](ai-test.sh) — full test suite (handles env + redis + venv)
- [`ai-done.sh`](ai-done.sh) — 14-check pre-ship gate
- [`ai-cache-bust.sh`](ai-cache-bust.sh) — bump CSS/JS `?v=` hashes
- [`ai-link-check.sh`](ai-link-check.sh) — Markdown + cross-ref resolution
- [`ai-impact.sh`](ai-impact.sh) — what depends on this file/symbol?

### Memory & journaling
- [`ai-where.sh`](ai-where.sh) — triggered associative recall for a file
- [`ai-recall.sh`](ai-recall.sh) — search the knowledge corpus
- [`ai-journal.sh`](ai-journal.sh) — capture decisions / learnings / bugs
- [`ai-reflect.sh`](ai-reflect.sh) — end-of-session consolidation

### Cognitive lenses
- [`ai-pattern.sh`](ai-pattern.sh) — 22-pattern catalog
- [`ai-lattice.sh`](ai-lattice.sh) — walk the C1-C10 constraint lattice
- [`ai-adversary.sh`](ai-adversary.sh) — game-theoretic walk per constraint

### Diagnostics
- [`ai-loop-check.sh`](ai-loop-check.sh) — stuck-loop / scope-creep detector
- [`ai-coherence.sh`](ai-coherence.sh) — structural ↔ codebase coherence
- [`ai-coverage.sh`](ai-coverage.sh) — C1-C10 ↔ test-coverage map
- [`ai-test-counts.sh`](ai-test-counts.sh) — MISSION.md test-count drift detector
- [`ai-meta.sh`](ai-meta.sh) — cognitive-layer self-monitor (CM)
- [`ai-treasury-report.sh`](ai-treasury-report.sh) — Treasury ledger diagnostic
- [`ai-authz-audit.sh`](ai-authz-audit.sh) — authorization-matrix audit
- [`ai-watcher-coverage.sh`](ai-watcher-coverage.sh) — HYDRA watcher coverage map
- [`ai-swarm-health.sh`](ai-swarm-health.sh) — Mycelium swarm health probe
- [`ai-swarm-validate.sh`](ai-swarm-validate.sh) — swarm structural validation

### Synthesis & reporting
- [`ai-architect.sh`](ai-architect.sh) — Architect-persona brief
- [`ai-anti-architect.sh`](ai-anti-architect.sh) — Anti-Architect contest pass
- [`ai-sanctum.sh`](ai-sanctum.sh) — Sanctum open/close protocol
- [`ai-hydra.sh`](ai-hydra.sh) — HYDRA hybrid intelligence
- [`ai-foresight.sh`](ai-foresight.sh) — Foresight surface brief (v9.12)
- [`ai-swarm-bloom.sh`](ai-swarm-bloom.sh) — Mycelium pheromone heatmap
- [`ai-swarm-map.sh`](ai-swarm-map.sh) — Mycelium tier graph
- [`ai-dashboard.sh`](ai-dashboard.sh) — single-screen dashboard (v9.07)
- [`ai-brain-map.sh`](ai-brain-map.sh) — regenerate the visual brain-map

### Snapshots & meta
- [`ai-snapshot.sh`](ai-snapshot.sh) — full state in one document
- [`ai-context-digest.sh`](ai-context-digest.sh) — compact state dump
- [`ai-help.sh`](ai-help.sh) — index of every ai-* script

---

## polaris-* scripts (operator layer; 30 scripts)

Grouped by lifecycle stage:

### Deploy
- [`polaris-deploy.sh`](polaris-deploy.sh) — idempotent deploy with rollback
- [`polaris-generate-secrets.sh`](polaris-generate-secrets.sh) — `secrets/` lifecycle
- [`polaris-rotate-secret.sh`](polaris-rotate-secret.sh) — rotate one secret
- [`polaris-create-operator.sh`](polaris-create-operator.sh) — admin/operator account
- [`polaris-generate-recovery-code.sh`](polaris-generate-recovery-code.sh) — printed mnemonic
- [`polaris-recover-admin.sh`](polaris-recover-admin.sh) — emergency admin recovery
- [`polaris-doctor.sh`](polaris-doctor.sh) — read-only diagnostic (wraps launcher)
- [`polaris-cron-install.sh`](polaris-cron-install.sh) — install operator cron jobs
- [`polaris-set-webauthn-deadline.sh`](polaris-set-webauthn-deadline.sh) — WebAuthn enforcement-date setter

### Migrate
- [`polaris-migrate.sh`](polaris-migrate.sh) — schema migrations (v8.95 framework)

### Backup + restore
- [`polaris-backup.sh`](polaris-backup.sh) — manifest-hashed tarball backup
- [`polaris-restore.sh`](polaris-restore.sh) — verified restore with rollback

### Archive + purge (audit-log)
- [`polaris-archive.sh`](polaris-archive.sh) — export-only archive (v8.84)
- [`polaris-purge.sh`](polaris-purge.sh) — sanctioned purge w/ checkpoint (v8.87)
- [`polaris-rotate-logs.sh`](polaris-rotate-logs.sh) — yearly archive+verify+purge cron pipeline

### Archive + purge (Pheromone) — v9.07
- [`polaris-pheromone-archive.sh`](polaris-pheromone-archive.sh) — Pheromone export-only
- [`polaris-pheromone-purge.sh`](polaris-pheromone-purge.sh) — sanctioned Pheromone purge

### Monitoring + diagnostics
- [`polaris-ct-monitor.sh`](polaris-ct-monitor.sh) — Certificate Transparency watch
- [`polaris-load-test.sh`](polaris-load-test.sh) — async load harness wrapper
- [`polaris-loadtest-tokens.sh`](polaris-loadtest-tokens.sh) — generate load-test tokens
- [`polaris-concurrency-harness.sh`](polaris-concurrency-harness.sh) — concurrency stress harness
- [`polaris-chaos-test.sh`](polaris-chaos-test.sh) — chaos-test wrapper (INCONCLUSIVE-aware)
- [`polaris-idempotency-test.sh`](polaris-idempotency-test.sh) — schema idempotency proof
- [`polaris-pqc-status.sh`](polaris-pqc-status.sh) — post-quantum-signing status probe
- [`polaris-oracle-runner.sh`](polaris-oracle-runner.sh) — operator-tier macro probe

### Swarm + Sanctum
- [`polaris-ant-ranking.sh`](polaris-ant-ranking.sh) — ant ranking diagnostic
- [`polaris-swarm-killtest.sh`](polaris-swarm-killtest.sh) — kill-test coverage probe
- [`polaris-swarm-mttr.sh`](polaris-swarm-mttr.sh) — finding MTTR raise/resolve ledger
- [`polaris-swarm-scorecard.sh`](polaris-swarm-scorecard.sh) — per-ship TP/FP scorecard
- [`polaris-sanctum-scorecard.sh`](polaris-sanctum-scorecard.sh) — per-Sanctum scorecard
- [`polaris-sanctum-status.sh`](polaris-sanctum-status.sh) — Sanctum lifecycle + archive sweep

---

## Helper Python modules

| File | Purpose |
|---|---|
| `ai_brain_map.py` | Generates `meta/brain-map/brain-map.html` |
| `ai_brain_map_analyze.py` | Brain-map gap analysis |
| `ai_swarm_bloom.py` | Renders Mycelium pheromone heatmap |
| `polaris_load_gen.py` | Stdlib-only async load harness |
| `test_implants.sh` | Smoke tests for the cognitive layer |

---

## Conventions

- **Naming.** `ai-*.sh` = cognitive layer (read by agents); `polaris-*.sh` = operator layer (read by humans). Helper Python is `<name>.py` (no prefix).
- **Doc-comment.** Every script's first comment block explains: purpose, usage examples, exit codes, env vars. `ai-help.sh` parses this.
- **Exit codes.** Operator scripts use named greppable codes (e.g. `EXIT_SHA_MISMATCH=4`). `0` = success; `1` = unspecified failure; `2+` = specific failure modes.
- **Idempotency.** Operator scripts must be safe to re-run. Mutations check current state first.
- **Read-only by default.** Cognitive scripts never modify Polaris state (with the explicit exceptions of `ai-journal.sh` writing to journal/, `ai-architect.sh --save` writing to journal/, `ai-hydra.sh --save` writing to journal/hydra/).

See [`docs/CONVENTIONS.md`](../docs/CONVENTIONS.md) for the project-wide naming + structural conventions.
