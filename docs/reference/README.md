# docs/reference/ — technical reference

Authoritative reference material for Polaris's technical surfaces:
HTTP API, schema, scaling characteristics, defined terms, and the
master architectural map.

For operator runbooks see [`../operator/`](../operator/). For
narrative + principles see [`../story/`](../story/).

---

## What's here

| Doc | What it covers |
|---|---|
| [`SYSTEM-MAP.md`](SYSTEM-MAP.md) | **The master architectural map** — every directory, every Python package, every script family, the cross-references between them |
| [`API.md`](API.md) | HTTP endpoint reference (20 routes; G29 health contract) |
| [`DATA-MODEL.md`](DATA-MODEL.md) | Schema table-by-table prose; per-table semantics + invariants |
| [`SCALING.md`](SCALING.md) | v6 scaling architecture: B-tree indexes, viewport-aware globe, /api/atlas hard caps |
| [`GLOSSARY.md`](GLOSSARY.md) | Defined terms (~470 lines; covers v1 → v9.x vocabulary) |
| [`PQC-POSTURE.md`](PQC-POSTURE.md) | Post-quantum audit: which primitives are PQ-secure (token signature, hashing, ZK proof) vs still classical (TLS key exchange, WebAuthn), mapped to the NIST 2030/2035 timeline |

---

## Reading order

**Architecture overview:** [SYSTEM-MAP.md](SYSTEM-MAP.md) is the
single best entry point.

**Building against the API:** [API.md](API.md) for endpoints, then
[DATA-MODEL.md](DATA-MODEL.md) for the schema behind them.

**Scaling investigation:** [SCALING.md](SCALING.md) for the v6
architecture, then `DEVNOTES/atlas-scaling.md` for the original
performance investigation, then OPERATIONS.md §"Scaling" for the
operator-facing inflection-point recipes.

**Vocabulary check:** [GLOSSARY.md](GLOSSARY.md) for any term you
encounter in the CHANGELOG that's unfamiliar.

---

## Conventions

- One file = one reference surface (no multi-topic monoliths)
- Tables over prose where the structure is repetitive
- Cross-references via Markdown links (catchable by `ai-link-check`)
- Versioning markers: `(v9.04+)` for additions; `(deprecated v8.X)`
  for removals; historical content stays with the marker

See [`../CONVENTIONS.md`](../CONVENTIONS.md) for project-wide
naming + structural conventions.

---

## What this directory is NOT

- Not operator runbooks (that's in [`../operator/`](../operator/))
- Not narrative (that's in [`../story/`](../story/))
- Not informal developer notes (that's in [`../../DEVNOTES/`](../../DEVNOTES/))
- Not auto-generated (each file is human-authored + maintained)

`docs/reference/` is **the source of truth for technical claims
about Polaris's interfaces**, written so a third-party integrator
can ship against Polaris without reading the source.
