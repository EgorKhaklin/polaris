# DEVNOTES — agent semantic memory

Concise notes for AI agents working on Polaris in a fresh session.
Two tiers:

- **Cross-cutting** (this directory) — principles, conventions, and
  operational reference that apply across the whole system. Read these
  when learning *how Polaris is built*.
- **Per-ship** (`ships/` subdirectory) — one file per major shipped
  feature. Read these when investigating *a specific v2 primitive*.

If you don't know which file you want, this README is the answer.

---

## Cross-cutting (in this directory)

| File | What it covers |
|---|---|
| [`audit-of-record.md`](audit-of-record.md) | The principle: schema element + append-only/bounded-mutation invariants fully reconstruct operation history without a separate event-log table. **Ten current instances (9 schema + 1 filesystem)** — v9.41 reclassification dropped two derived caches (`census-roll.json`, `treasury-roll.json`). |
| [`concurrency.md`](concurrency.md) | Every race that exists, every advisory-lock that seals it. **Six per-entity / per-procedure lock granularities** in the catalog. |
| [`substrate.md`](substrate.md) | The manifest of every primitive Polaris depends on (NIST, W3C, ML-DSA, Plonky2, Rust toolchain, etc.). 27 rows across 7 layers. Mirrored in `polaris_sql/13_substrate.sql`. |
| [`threat-model.md`](threat-model.md) | STRIDE-categorized threats and their controls. The map between MISSION's C1–C10 constraints and concrete attacks. |
| [`style.md`](style.md) | VANTA's standing instructions. No em-dashes in prose, declarative tone, game-theoretic framing, "holy shit, that's done" quality bar. |
| [`known-gotchas.md`](known-gotchas.md) | Things that have bitten me before. Re-read at session start to skip the rediscovery cost. |
| [`rate-limiter.md`](rate-limiter.md) | R8-2 backend selection (in-memory vs Redis), atomicity notes, contract-mixin pattern. |
| [`atlas-scaling.md`](atlas-scaling.md) | v6 scaling architecture for the operational atlas — server-side bin aggregation, viewport-aware fetches, hard caps. |
| [`zk-soundness.md`](zk-soundness.md) | The honest ledger for the ZK layer: what the Merkle-inclusion proof actually guarantees (strong differential/two-witness consistency) vs. what is still limited (placeholder PQC by default, statement-level witness). Modeled on Glass's `docs/soundness.md`. v9.44. |
| [`two-witness-principle.md`](two-witness-principle.md) | Standing obligation: every cryptographic verdict Polaris ships must be checkable by a second, independent implementation (different language/representation, no shared code), or it ABSTAINS explicitly. Adopted v9.44 from Glass's Pentecost discipline. |
| [`presentation-plan.md`](presentation-plan.md) | The sub-roadmap for the presentation pass (P1.13 to P1.17): every ship, its status, and the ordered changes each carries. |
| [`record.md`](record.md) | The project record: the v1 and v2 done-lists, the retired arcs and the production-deployment phase log, moved out of MISSION.md at v9.195. |

## Per-ship — `ships/` subdirectory

One file per major v2 primitive. Read these when investigating that
specific ship.

| File | Ship | Version |
|---|---|---|
| [`ships/quantum-observer.md`](ships/quantum-observer.md) | M2-5 scaffold | v8.11 |
| [`ships/issuer-discretion.md`](ships/issuer-discretion.md) | R11-6 / M2-11 — `IssuerDiscretionPolicy` + revocation-velocity bound | v8.15 |
| [`ships/tiered-enrollment.md`](ships/tiered-enrollment.md) | R11-4 / M2-9 — `EnrollmentStatusEvent` + civic-query | v8.16 |
| [`ships/recovery-ceremony.md`](ships/recovery-ceremony.md) | R11-2 / M2-7 — `RecoveryRequest` + UC-9 two-phase ceremony | v8.17 |
| [`ships/multi-sig-migration.md`](ships/multi-sig-migration.md) | R11-1 / M2-6 — `TokenSignature` M:N + UC-6 | v8.18 |
| [`ships/anchoring.md`](ships/anchoring.md) | R10-2 / M2-2 — `AnchorBatch` + Merkle helper + 3 `/api/anchor/*` routes | v8.21 |
| [`ships/federation.md`](ships/federation.md) | R11-3 / M2-8 — `AgencyTrustAttestation` + UC-10 (attest + revoke) | v8.22 |
| [`ships/zk-snark.md`](ships/zk-snark.md) | R10-1 / M2-1 — `TokenStateEpoch` + Plonky2 + `polaris_zk/` Rust crate | v8.23 |
| [`ships/duress-codes.md`](ships/duress-codes.md) | R11-5 / M2-10 — `DuressEvent` + UC-12 (v2 mission-closer) | v8.24 |

## Where does X live?

| Question | Look here |
|---|---|
| "What's the principle behind append-only X?" | `audit-of-record.md` |
| "What's the right advisory-lock granularity for a new procedure?" | `concurrency.md` |
| "Does Polaris depend on Y?" | `substrate.md` |
| "How does the federation graph work?" | `ships/federation.md` |
| "How does the duress code mechanism resist timing attacks?" | `ships/duress-codes.md` |
| "Why did we pick Plonky2 over Groth16?" | `ships/zk-snark.md` |
| "How does the verification flow handle revoked attestations?" | `ships/federation.md` (R2 audit refinement) |
| "What's VANTA's quality bar?" | `style.md` |

## When to add a file

- **A new cross-cutting principle** that touches >2 ships → top-level
  file here. Update this README's table.
- **A new ship** → `ships/<short-name>.md`. Update this README's per-ship
  table.
- **A new operational concern** (rate limiter, atlas scaling, etc.) →
  top-level here.

---

## v8.26 reorganization note

Files in this directory were reorganized in **v8.26** (2026-05-11) to
separate cross-cutting principles from per-ship reference docs. The
9 per-ship files were moved into `ships/`. Cross-cutting files stayed
at this directory's root.

**Historical references** in older `CHANGELOG.md` entries may still
reference `DEVNOTES/foo.md` (the pre-v8.26 paths). This is by design —
those entries are audit-of-record artifacts and are not rewritten. The
9 moved files are:

```
anchoring.md  → ships/anchoring.md
duress-codes.md → ships/duress-codes.md
federation.md → ships/federation.md
issuer-discretion.md → ships/issuer-discretion.md
multi-sig-migration.md → ships/multi-sig-migration.md
quantum-observer.md → ships/quantum-observer.md
recovery-ceremony.md → ships/recovery-ceremony.md
tiered-enrollment.md → ships/tiered-enrollment.md
zk-snark.md → ships/zk-snark.md
```
