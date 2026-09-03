# meta/: invariant architecture and decision records

This directory holds the documents that explain how Polaris is constrained:
the structural reasoning beneath the ten hard constraints C1-C10 in
`MISSION.md`, and the proofs and mappings that justify them.

If `MISSION.md` says **what** Polaris is and which invariants hold, `meta/`
records **why those invariants are structured the way they are and how they are
verified.**

---

## What's here

### Architecture

| File | Purpose |
|---|---|
| [`structural-architecture.md`](structural-architecture.md) | The Removable Test discipline |
| [`constraint-lattice.md`](constraint-lattice.md) | C1-C10 ↔ 10-node lattice mapping |

The live constitutional constants are the ten hard constraints C1-C10 in
[`MISSION.md`](../MISSION.md), enforced at the database level and checked by
[`polaris_checks/`](../polaris_checks/).

### Domain models

| File | Purpose |
|---|---|
| [`redaction-proof.md`](redaction-proof.md) | M2-12 verification-graph redaction proof + adversary model |

### Formal specifications

| File | Purpose |
|---|---|
| [`tla/`](tla/) | TLA+ specs for invariants (e.g. C3 one-active-token) |

---

## How to navigate

**Fresh agent session?** Start with [`CLAUDE.md`](../CLAUDE.md)
(the canonical agent runbook).

**Want the constitution itself?** Read [`MISSION.md`](../MISSION.md): the ten
hard constraints C1-C10 and the anti-coercion Vocation above them.

---

## What this directory is NOT

- Not source code (that's in `polaris_*/`)
- Not operator documentation (that's in `docs/operator/`)
- Not informal developer notes (that's in `DEVNOTES/`)

`meta/` is the invariant-architecture record, named explicitly so the
reasoning behind C1-C10 can be audited, version-controlled, and updated when the
constitutional landscape shifts.
