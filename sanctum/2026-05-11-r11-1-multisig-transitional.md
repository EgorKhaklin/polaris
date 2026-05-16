# Sanctum: R11-1 — Multi-signature transitional state (UC-6)

**Date:** 2026-05-11
**Petitioner:** agent (Claude, Opus 4.7)
**Principal:** VANTA
**Trigger:** MEDIUM-risk propose-and-wait + seven-refinement alignment audit + issuer-trust-triad-closing move
**Risk class:** MEDIUM
**Status:** CLOSED
**Note:** Backfilled retroactively. The Sanctum protocol did not
exist at the time of this consultation; this record was
reconstructed from chat history after v8.19 shipped. Treat as a
fair reconstruction, not a verbatim record. This was the
most-invasive ship of the v8.15–v8.18 arc (verification path is
touched).

---

## I. The Matter

Implement M:N multi-signature relation between IdentityToken and
CryptographicAlgorithm (PDF §9.4 cryptographic-migration leg) —
the cryptographic-diversity leg of the issuer-trust-concentration
triad.

## II. Preparation

- Architect brief: 2026-05-11 brief, R11-1 ranked #1 after R11-2 ship
- Proposal draft: [proposals/R11-1-multisig-transitional.md](../proposals/R11-1-multisig-transitional.md)
  (originally drafted ~v8.10; predated the R11-6 / R11-4 / R11-2 patterns)
- Alignment audit: **seven refinements** identified:
  1. C9 advisory-lock per-token on `uc6_migrate_algorithm`
  2. `TokenSignature` append-only invariant (narrower than `reject_audit_modification`: write-once + one-way `deprecation_date`)
  3. Concurrent verify+migrate consistency-model test (snapshot isolation contract)
  4. Issuer-trust-concentration triad framing
  5. "Schema records, agencies decide" framing section
  6. Anti-auto-derivation explicit (TokenSignature.deprecation_date NOT auto-set from CryptographicAlgorithm.deprecation_date)
  7. TokenSignature row IS the migration audit-of-record (no separate `TokenMigrationEvent` table)
- Blast radius: 13 files (the most of any ship in this arc — verification path touched)
- Tests planned: 16 MultiSignatureTests + 3 ConcurrencyTests + 5 SQL section N

## III. Alternatives considered

1. **Simultaneous mass reissuance** (the PDF's other named option) — rejected: not viable at population scale
2. **Keep IdentityToken.algorithm_id as the single signature column, add a deprecation flag** — rejected: doesn't support multiple algorithms coexisting during migration window
3. **`TokenMigrationEvent` audit table** — rejected: redundant with TokenSignature row's own append-only invariant; would duplicate state
4. **Auto-deprecation when CryptographicAlgorithm.deprecation_date fires** — rejected: the two columns serve different purposes (algorithm-wide vs per-signature); operator policy is the only path
5. **Threshold signatures (multi-party)** — out of scope; different problem

## IV. Recommendation

Implement R11-1 with all seven refinements folded in. `TokenSignature`
M:N table with UNIQUE composite key, two triggers
(`enforce_token_has_active_signature` + `enforce_token_signature_immutability`),
per-token advisory-lock in `uc6_migrate_algorithm`, UC-1 and UC-9
extended to insert TokenSignature alongside new IdentityToken,
backfill block for v1 sample tokens.

## V. What's needed from VANTA

"Yes do R11-1" plus answers to three remaining open questions:
default algorithm priority order (recommend highest algorithm_id
first), whether to expose priority to verifier (recommend accept-any
for v1), backfill strategy for sample data (recommend
`BACKFILL_PLACEHOLDER` tag).

## VI. Decision

"yes do R11-1" — VANTA approved with all seven refinements and the
three recommended defaults.

## VII. Outcome

Shipped v8.18 (2026-05-11). 16 + 3 + 5 = 24 new tests, all green.
The issuer-trust-concentration triad is now 2/3 done (cryptographic
diversity R11-1 + constitutional limits R11-6); M2-8 federation is
the only unbuilt leg across both PDF §9 triads. v2 done-list 7/12 →
8/12. C7 (algorithm metadata via table) strengthened from 1:1 to M:N.
[CHANGELOG v8.18](../CHANGELOG.md#v818--2026-05-11-r11-1--m2-6-multi-signature-transitional-state--uc-6).
