# docs/ — Polaris reference docs

Reference material organized by audience. Cognitive-layer documents
(`CLAUDE.md`, `MISSION.md`, `ROADMAP.md`, `docs/BACKLOG.md`, `CHANGELOG.md`,
`README.md`) live at the project root because every script in
`scripts/` greps them; moving them would break the agent's status /
propose / journal pipeline. Everything else that's "documentation
about Polaris, not its source of truth" lives here.

## Orientation (start here)

Three documents that together cover the why, the what, and the how. Added v8.59 as the public-presentation entry layer.

| File | When to read |
|---|---|
| [STORY.md](story/STORY.md) | The non-technical narrative of how Polaris was built (v1 → v8.58). Read this if you want context before paging the audit-of-record. |
| [SYSTEM-MAP.md](reference/SYSTEM-MAP.md) | A single page naming every meaningful file in the repository with one line on what it is for. Use this when you do not know where to start. |
| [PRINCIPLES.md](story/PRINCIPLES.md) | The four constitutional principles distilled. Read before changing anything load-bearing. |

## Operator-facing

| File | When to read |
|---|---|
| [INSTALL.md](operator/INSTALL.md) | Setting up Polaris from scratch — Postgres, role, schema, web app. The exhaustive form (the README's quickstart is the abridged form). |
| [DEPLOYMENT.md](operator/DEPLOYMENT.md) | Three deployment paths (Docker Compose / local Python / production systemd+nginx+TLS). Includes the rate-limiter backend / Redis section (R8-2). |
| [OPERATIONS.md](operator/OPERATIONS.md) | Day-2 operational runbook: backup, restore, secret rotation, audit-log review, incident triage. |

## Architecture / design

| File | When to read |
|---|---|
| [DATA-MODEL.md](reference/DATA-MODEL.md) | ER overview + table-by-table prose for the 23 tables (includes M2-1 TokenStateEpoch + Leaf, M2-2 AnchorBatch, M2-5 QuantumObserverBinding, M2-6 TokenSignature, M2-7 RecoveryRequest, M2-8 AgencyTrustAttestation, M2-9 EnrollmentStatusEvent, M2-10 DuressEvent, M2-11 IssuerDiscretionPolicy). The complement to `polaris_sql/01_schema.sql` for readers who want narrative rather than DDL. |
| [SCALING.md](reference/SCALING.md) | The v6 scaling architecture. How the 2M+ event capacity actually works (server-side cluster aggregation, viewport-aware fetches, hard caps). |
| [SECURITY.md](operator/SECURITY.md) | The cybersecurity audit and the controls applied. Pairs with `DEVNOTES/threat-model.md` (STRIDE) and `meta/redaction-proof.md` (the privacy claim). |
| [PRIVACY.md](operator/PRIVACY.md) | What data is collected, retained, shared, and how the architecture enforces minimization. Distinct from `SECURITY.md` — that's about defending data, this is about not collecting more than necessary. |

## API / interface reference

| File | When to read |
|---|---|
| [API.md](reference/API.md) | The HTTP endpoint reference. Auth-required vs anonymous, request shapes, response shapes, status codes. |
| [GLOSSARY.md](reference/GLOSSARY.md) | Defined terms: token, holder, individual, agency, context, disclosure level, lifecycle event, etc. The vocabulary the rest of the docs assume. |

## What lives elsewhere (not here)

- **Agent runbook** → `CLAUDE.md` at root.
- **Mission constitution + done-list** → `MISSION.md` at root.
- **Active backlog** → `ROADMAP.md` and `docs/BACKLOG.md` at root.
- **Release log** → `CHANGELOG.md` at root.
- **Agent semantic memory** (concurrency, atlas-scaling, known-gotchas, rate-limiter, threat-model, substrate) → `DEVNOTES/`.
- **Procedural recipes** (add-flask-route, scaling-investigation, etc.) → `patterns/`.
- **Cognitive-layer architecture itself** (autonomy, constraint lattice, structural constants, redaction proof, missions-considered) → `meta/`.
- **Per-day decision log** → `journal/`.
- **Strategic option proposals** → `proposals/`.
- **Sanctum strategic-consultation records** (v8.19+) → `sanctum/`, indexed at `meta/sanctum-index.md`. Each major decision (MEDIUM/HIGH risk, cross-arc, or cognitive-layer structural change) is recorded here. Protocol at `meta/sanctum-protocol.md`; entry script `scripts/ai-sanctum.sh`.
- **Audit-of-record principle** (v8.20) → `DEVNOTES/audit-of-record.md`. Defines the cross-cutting pattern shared by TokenLifecycleEvent, VerificationEvent, EnrollmentStatusEvent, RecoveryRequest, TokenSignature, AnchorBatch (v8.21), AgencyTrustAttestation (v8.22), TokenStateEpoch (v8.23), DuressEvent (v8.24), and the Sanctum directory; **10 instances total (9 schema + 1 filesystem)**.

## Re-evaluation triggers

This split should be revisited when:

- A doc grows large enough to warrant its own subdirectory (e.g.
  `docs/api/v1/`, `docs/api/v2/` if API versioning lands).
- A new audience appears (e.g., compliance officer needing a dedicated
  doc set distinct from operator/architect/developer).
- Cross-references between docs/ and the cognitive layer become so
  numerous that consolidation is cleaner than separation.
