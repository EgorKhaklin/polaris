# meta/ — governance and decision records

This directory holds the documents that govern how the agent and the
developer reason about Polaris. It is the governance layer beneath
`MISSION.md` / `ROADMAP.md` / `CLAUDE.md` at the repo root.

If `MISSION.md` says **what** Polaris is, `meta/` records **how
decisions about it are made and audited.**

---

## What's here

### Governance and architecture

| File | Purpose |
|---|---|
| [`autonomy-architecture.md`](autonomy-architecture.md) | LOW / MEDIUM / HIGH risk classes; what the agent can do autonomously |
| [`structural-architecture.md`](structural-architecture.md) | The Removable Test discipline |
| [`constraint-lattice.md`](constraint-lattice.md) | C1-C10 ↔ 10-node lattice mapping |
| [`freeze-amendment-protocol.md`](freeze-amendment-protocol.md) | How frozen invariants may be amended |

The live constitutional constants are the ten hard constraints C1-C10 in
[`MISSION.md`](../MISSION.md), enforced at the database level and checked by
[`polaris_checks/`](../polaris_checks/).

### Protocols

| File | Purpose |
|---|---|
| [`sanctum-protocol.md`](sanctum-protocol.md) | Strategic-consultation protocol (the Sanctum) |

### Domain models

| File | Purpose |
|---|---|
| [`redaction-proof.md`](redaction-proof.md) | M2-12 verification-graph redaction proof + adversary model |

---

## How to navigate

**Fresh agent session?** Start with [`CLAUDE.md`](../CLAUDE.md)
(the canonical agent runbook).

**Need to make a strategic decision?** Read
[`sanctum-protocol.md`](sanctum-protocol.md), then `bash
scripts/ai-sanctum.sh open <topic>`.

---

## What this directory is NOT

- Not source code (that's in `polaris_*/`)
- Not operator documentation (that's in `docs/operator/`)
- Not informal developer notes (that's in `DEVNOTES/`)

`meta/` is the governance and decision record, named explicitly so the
reasoning can be audited, version-controlled, and updated when the
constitutional landscape shifts.
