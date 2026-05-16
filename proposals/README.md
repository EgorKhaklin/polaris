# proposals/ — long-form proposal drafts

This directory holds full-length proposals for ROADMAP items at MEDIUM
or HIGH risk class. The ROADMAP entry is the one-paragraph summary;
the proposal here is the detailed design — what's being changed, why,
trade-offs considered, what could break.

A proposal is the artifact that converts "MEDIUM risk → propose-and-wait"
into "MEDIUM risk → user-reviewed proposal → execute." Without it, the
agent and the user are negotiating intent through scattered messages.
With it, both sides reference the same document.

## Convention

- One file per ROADMAP item, named `<item-id>-<short-slug>.md`.
- Open with the item's mission link, risk class, effort estimate.
- Body sections: **What** / **Why** / **Trade-offs** / **What can break**.
- Close with explicit acceptance criteria the agent can self-check against.

## Current contents

| File | Item | Status |
|---|---|---|
| [R10-2-did-anchoring.md](R10-2-did-anchoring.md) | R10-2 functional DID anchoring | PROPOSED 2026-05-11; M2-2 (substrate arc) |
| [R11-1-multisig-transitional.md](R11-1-multisig-transitional.md) | R11-1 multi-signature transitional state | PROPOSED 2026-05-11; M2-6 (open problems §9.4) |
| [R11-2-catastrophic-loss-recovery.md](R11-2-catastrophic-loss-recovery.md) | R11-2 catastrophic-loss recovery (UC-8) | PROPOSED 2026-05-11; M2-7 (open problems §9.1) |
| [R8-3-oidc-integration.md](R8-3-oidc-integration.md) | R8-3 OIDC | ⏸ DEFERRED 2026-05-09 by user |
| [R8-4-postgis-migration.md](R8-4-postgis-migration.md) | R8-4 PostGIS migration | open, MEDIUM, not on active arc |
| [R9-1-banking-on-polaris.md](R9-1-banking-on-polaris.md) | R9-1 banking-on-polaris (separate repo) | ⏸ DEFERRED 2026-05-09 by user |

Items with corresponding proposals here are also in `ROADMAP.md`. The
proposal does not replace the ROADMAP entry; it elaborates it.

Shipped items (R7-3, R8-2) had their proposals pruned in v8.10. The
code in main, the CHANGELOG entry, and the tests are the truth. The
proposal artifact is only useful before shipping.

## When to write a proposal

- **MEDIUM risk** ROADMAP item the user has indicated interest in but
  hasn't authorized yet
- **HIGH risk** item — always, before any work
- Schema changes, auth changes, or public-API surface changes —
  always, regardless of risk class label
- A LOW-risk item if it touches three or more files or has more than
  one reasonable design

## When NOT to write a proposal

- A LOW-risk item that's a one-file change
- A typo or broken-link fix
- A refactor that doesn't change behavior
