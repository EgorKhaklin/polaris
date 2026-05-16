# Sanctum: r11-3-issuer-federation

**Date:** 2026-05-11
**Petitioner:** agent (Claude, Opus 4.7)
**Principal:** VANTA
**Trigger:** HIGH-risk propose-and-wait; mission-arc closer (issuer-trust-concentration triad 2/3 → 3/3); verification-flow change.
**Risk class:** HIGH
**Status:** CLOSED
**Architect brief ID:** arch-2026-05-11-001 (R11-3 surfaced as #3 in the brief; promoted over the #1 MEDIUM by strategic synthesis — triad-closing leg)

> **Prep-check note:** `ai-sanctum.sh open` reported "no proposal found"; the case-insensitive matcher in the script missed `proposals/R11-3-issuer-federation.md` (uppercase R). The proposal IS in place. Filed as a minor follow-up tooling fix; not a structural gap.

---

## I. The Matter

VANTA's approval to ship **R11-3 — Issuer federation model** (M2-8 from PDF §9.2), closing the issuer-trust-concentration triad to 3/3.

## II. Preparation

- **Architect brief:** today (2026-05-11) — surfaced R11-3 as one of three remaining ⬜ v2 items; strategic synthesis promoted it from #3 by score to #1 by arc-closure value.
- **Proposal draft:** [`proposals/R11-3-issuer-federation.md`](../proposals/R11-3-issuer-federation.md) — first pass written today, alignment audit completed today, six refinements folded in before this Sanctum entry.
- **Alignment audit:** ran the established checklist from R10-2 / R11-1 / R11-6. Six substantive refinements surfaced:
  1. **R1** — Commit to NO transitive trust at schema level (anti-auto-derivation applied to the trust graph).
  2. **R2** — "Schema records, agencies decide" framing for revocation propagation (no retroactive `VerificationEvent` invalidation).
  3. **R3** — Note attestations as future-field candidate `AnchorBatch` leaves (path-forward without wiring).
  4. **R4** — Name the v1 operator-driven-attestation limitation; v2 path = agency-signed signatures.
  5. **R5** — Commit to schema-layer self-attestation rejection (vs. semantic no-op).
  6. **R6** — Concrete 6-row seed graph matching existing demo verification events.
- **Blast radius if approved:**
  - Schema: +1 table (`AgencyTrustAttestation`), +1 partial unique index, +3 CHECK constraints, +1 trigger (`enforce_attestation_immutability`)
  - Procedures: +2 (`uc10_attest_trust`, `uc10_revoke_attestation`) with per-attesting-agency advisory lock (5th catalog entry)
  - Verification path: 1 helper function in `app.py`; existing `verifications_new` extended
  - Optional Flask routes: `/api/federation/attest` + `/api/federation/revoke` (admin)
  - Tests: +15 `IssuerFederationTests` + 2 `ConcurrencyTests` + 5 SQL self-tests (section P)
  - DEVNOTES: 1 new (`federation.md`), 2 extended (`audit-of-record.md` → 6 instances, `concurrency.md` → 5 entries)
  - Counts: 19 → 20 tables; 9 → 11 procedures; 1 → 2 triggers added; 5 → 6 audit-of-record instances; 4 → 5 advisory-lock entries
- **Tests planned:** 22 (15 federation + 2 concurrency + 5 SQL section P).

## III. Alternatives considered

1. **Ship R8-4 (PostGIS migration) instead.** The Architect's #1 by score. Safe MEDIUM, performance-positive, ~1-2 sessions. Rejected for this Sanctum because R8-4 doesn't advance the v2 arc; it can be scheduled after R11-3 without loss of momentum, but a triad-closing move has higher mission-leverage right now.
2. **Open Sanctum for M2-1 ZK-SNARK (R10-1) instead.** Closes Substrate-D arc to 5/5. Rejected because ZK-SNARK is the most-bounded HIGH-risk *cryptographically* — a deep math rabbit hole — and the alignment audit surface is much larger (circuit design, trusted-setup ceremony, Groth16 vs. PLONK choice). Federation has more sociopolitical surface but a more tractable cryptographic surface.
3. **Open Sanctum for M2-10 duress codes (R11-5) instead.** Standalone HIGH-risk open problem. Rejected because it doesn't close a triad; M2-10 is a single-leg item, so the mission-leverage is lower than R11-3 which completes the issuer-trust set.
4. **Defer R11-3 until v2 has more samples for pattern analysis.** Rejected because the pattern set is already mature (6 Sanctums across R10-2 / R11-1 / R11-2 / R11-4 / R11-6 / v8.20), and the audit-refinement count (6) is in line with R10-2's pattern. Further deferral would be over-caution.

## IV. Recommendation

Approve R11-3 with all six audit refinements folded in. The proposal is ready to ship without further redrafting; the audit checklist (proposal §"Pre-Sanctum sanity checklist") is fully green.

The strategic case rests on three observations:

1. **Triad closure has the highest mission-leverage among remaining ⬜ items.** Holder-protection triad closed at R11-2; issuer-trust-concentration closes at R11-3. Closing a second triad in v2 demonstrates the schema's structural coherence — every "what could go wrong" leg the PDF names has a relational answer.
2. **The audit-then-Sanctum pattern is now well-established.** R10-2's six refinements + R11-1's seven set the cadence; R11-3's six fits the curve. The schema-touching invariants (advisory-lock, append-only, anti-auto-derivation, schema-records-agencies-decide) are now checklist items rather than discovered each time.
3. **The cryptographic surface is bounded.** v1 federation is operator-logged attestation, not agency-signed; the v2 cryptographic-signature extension is named in the proposal §"R4" as a clean future path. This is the same posture R10-2 took with `committed_to_chain` — schema-records-the-structure, future-fields-leave-the-cryptographic-leg-open.

## V. What's needed from VANTA

Choose one:

- **"yes do R11-3"** — proceed with the audited proposal as written; all six refinements folded in.
- **"yes with changes: X, Y"** — proceed with specified modifications.
- **"defer; do R8-4 first"** — clean MEDIUM ship first, return to R11-3 later.
- **"defer; reconsider arc priority"** — different HIGH-risk move (M2-1 ZK-SNARK or M2-10 duress codes) instead.
- **"reject"** — R11-3 is not the right shape; the proposal needs deeper revision before Sanctum re-entry.

## VI. Decision

proceed with recommendation.

## VII. Outcome

Shipped end-to-end: AgencyTrustAttestation table (6th audit-of-record), enforce_attestation_immutability trigger, uc10_attest_trust + uc10_revoke_attestation procedures with per-attesting-agency advisory lock (5th catalog entry), 6-row seed graph, _federation_trust_holds() helper extending verifications_new, two /api/federation/* routes, X-CSRFToken header support in validate_csrf, 5 SQL self-tests section P, 15 IssuerFederationTests + 2 ConcurrencyTests — all passing. M2-8 ✅; issuer-trust-concentration triad closed 3/3; both PDF §9 triads now structurally complete. Six audit refinements (R1–R6) folded in. Canonical execution links: see CHANGELOG.md v8.22 entry; ROADMAP.md R11-3 marked ✅; MISSION.md M2-8 marked ✅; DEVNOTES/federation.md (new); DEVNOTES/audit-of-record.md (extended to 6 instances); DEVNOTES/concurrency.md (extended to 5 advisory-lock entries); docs/API.md (federation routes); docs/DATA-MODEL.md (AgencyTrustAttestation section); docs/SECURITY.md (triad table updated).

