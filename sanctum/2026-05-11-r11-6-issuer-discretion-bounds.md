# Sanctum: R11-6 — Issuer-discretion bounds

**Date:** 2026-05-11
**Petitioner:** agent (Claude, Opus 4.7)
**Principal:** VANTA
**Trigger:** MEDIUM-risk propose-and-wait + alignment audit
**Risk class:** MEDIUM
**Status:** CLOSED
**Note:** Backfilled retroactively. The Sanctum protocol did not
exist at the time of this consultation; this record was
reconstructed from chat history after v8.19 shipped. The form
reflects the protocol's structure better than the actual ad-hoc
conversation did — alternatives, audit findings, and refinement
counts were considered in the original flow but not formally
enumerated. Treat as a fair reconstruction, not a verbatim record.

---

## I. The Matter

Implement a schema-level cap on issuer-driven revocation velocity to
defend against denaturalization-style mass revocation (PDF §9 "Issuer
trust concentration" — constitutional-limits leg).

## II. Preparation

- Architect brief: arch-2026-05-11-001 recommended R11-6 as top move
- Proposal draft: [proposals/R11-6-issuer-discretion-bounds.md](../proposals/R11-6-issuer-discretion-bounds.md)
- Alignment audit: 3 refinements identified
  - RevocationList integration (UC-4 pattern)
  - C9 advisory-lock per agency_id
  - "Constitutional limits, not authority" framing section
- Blast radius: 9 files (schema, indexes, procedure, trigger, grants, sample data, SQL tests, Flask routes, tests)
- Tests planned: 11 IssuerDiscretionBoundsTests + 2 ConcurrencyTests + 7 SQL section K

## III. Alternatives considered

1. **No rate limit, audit-only** — rejected: catches abuse only after the fact, doesn't deter
2. **Hard cap with no co-signer escape** — rejected: would block legitimate bulk hardware recalls
3. **SERIALIZABLE isolation instead of advisory-lock** — rejected: needs app-side retry; advisory-lock is per-agency, cleaner
4. **Single fixed co-signer authority** — rejected: single point of failure; recommend co-signer-set (any BOTH agency ≠ actor)

## IV. Recommendation

Implement R11-6 as proposed with the three refinements folded in.
N=5% / W=30d defaults via `ALTER DATABASE` GUCs; per-agency overrides
via `IssuerDiscretionPolicy`. Belt-and-suspenders trigger
`enforce_revocation_velocity_bound` rejects raw UPDATEs.

## V. What's needed from VANTA

"Yes do R11-6" plus answers to five open questions: N value (recommend
5%), W value (recommend 30d), co-signer eligibility (recommend any
BOTH agency ≠ actor), whether to gate LOST events too (recommend no),
where defaults live (recommend ALTER DATABASE GUCs).

## VI. Decision

"yes do R11-6" — VANTA approved all five recommended defaults.

## VII. Outcome

Shipped v8.15 (2026-05-11). 11 + 2 + 7 = 20 new tests, all green.
ai-done 9/2/0. PDF §9 "constitutional limits on issuer discretion"
leg closed. R11-6 became the intersection point of two PDF §9 triads
(exit-leg of holder-protection + constitutional-limits leg of
issuer-trust). Journal: 2026-05-11 entry 21.
[CHANGELOG v8.15](../CHANGELOG.md#v815--2026-05-11-r11-6--m2-11-issuer-discretion-bounds).
