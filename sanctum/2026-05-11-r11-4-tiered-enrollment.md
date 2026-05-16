# Sanctum: R11-4 — Tiered enrollment / population coverage

**Date:** 2026-05-11
**Petitioner:** agent (Claude, Opus 4.7)
**Principal:** VANTA
**Trigger:** MEDIUM-risk propose-and-wait + sociotechnical-surface decision
**Risk class:** MEDIUM
**Status:** CLOSED
**Note:** Backfilled retroactively. The Sanctum protocol did not
exist at the time of this consultation; this record was
reconstructed from chat history after v8.19 shipped. Treat as a
fair reconstruction, not a verbatim record.

---

## I. The Matter

Add schema-level vocabulary for non-enrolled persons (PDF §9
"Population coverage") — the entry leg of the
"schema-doesn't-weaponize-itself-against-the-holder" triad.

## II. Preparation

- Architect brief: 2026-05-11 brief recommended R11-4 after R11-6 ship
- Proposal draft: [proposals/R11-4-tiered-enrollment.md](../proposals/R11-4-tiered-enrollment.md)
- Alignment audit: written into the proposal itself before approval
  (asymmetric design — EXEMPT frictionless, mass-NOT_ENROLLED enumeration deliberate)
- Blast radius: 11 files (schema, indexes, view, trigger, civic-query function, sample data, SQL tests, Flask route, template, Python tests, DEVNOTES + docs)
- Tests planned: 10 TieredEnrollmentTests + 5 SQL section L

## III. Alternatives considered

1. **Column on Individual** — rejected: status changes overwrite history (violates succession-by-reference posture)
2. **Auto-derive enrollment from token state** — rejected: conflates "token lost" with "civic enrollment ended", and clobbers EXEMPT marker
3. **Trigger-enforced state machine** — rejected: makes the schema a policy participant; same posture as TokenLifecycleEvent (record, don't enforce sequencing)
4. **6-state enum splitting ENROLLED_RESERVE / ENROLLED_ACTIVE** — rejected: duplicates IdentityToken.status

## IV. Recommendation

Five-state enum (`NOT_ENROLLED`, `PENDING_ENROLLMENT`, `ENROLLED`,
`EXEMPT`, `LAPSED`) recorded in append-only `EnrollmentStatusEvent`.
Seed trigger materializes NOT_ENROLLED as default. Civic-query
function `civic_enrollment_summary` returns *counts only*; per-individual
NOT_ENROLLED enumeration is deliberately not first-class. Asymmetric
design defends against the surveillance-marker second-best attack.

## V. What's needed from VANTA

"Yes do R11-4" plus answers to five open questions: five-status enum
(recommend keeping it five), auto-derivation policy (recommend none),
state-machine enforcement (recommend application-layer), sociotechnical
doc tone (recommend naming the failure mode explicitly), EXEMPT
reason vocabulary (recommend free-text).

## VI. Decision

"yes do R11-4" — VANTA approved all five recommended defaults.

## VII. Outcome

Shipped v8.16 (2026-05-11). 10 + 5 = 15 new tests, all green.
PDF §9 "Population coverage" leg closed. v2 done-list 5/12 → 6/12.
Asymmetric NOT_ENROLLED/EXEMPT design persisted to DEVNOTES.
[CHANGELOG v8.16](../CHANGELOG.md#v816--2026-05-11-r11-4--m2-9-tiered-enrollment--population-coverage).
