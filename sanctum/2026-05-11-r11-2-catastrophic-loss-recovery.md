# Sanctum: R11-2 — Catastrophic-loss recovery (UC-9)

**Date:** 2026-05-11
**Petitioner:** agent (Claude, Opus 4.7)
**Principal:** VANTA
**Trigger:** MEDIUM-risk propose-and-wait + six-refinement alignment audit + holder-protection-triad-closing move
**Risk class:** MEDIUM
**Status:** CLOSED
**Note:** Backfilled retroactively. The Sanctum protocol did not
exist at the time of this consultation; this record was
reconstructed from chat history after v8.19 shipped. Treat as a
fair reconstruction, not a verbatim record. Pre-cleanup also
renamed the proposal's UC-8 → UC-9 references (R11-6 had claimed
UC-8 in v8.15).

---

## I. The Matter

Implement two-phase out-of-band recovery ceremony for catastrophic
token loss (PDF §9.1) — the recovery leg that closes the
holder-protection triad (entry R11-4 + exit R11-6 + recovery R11-2).

## II. Preparation

- Architect brief: 2026-05-11 brief, R11-2 ranked #1 after R11-4 ship
- Proposal draft: [proposals/R11-2-catastrophic-loss-recovery.md](../proposals/R11-2-catastrophic-loss-recovery.md)
- Alignment audit: **six refinements** identified:
  1. C9 advisory-lock on `claimed_individual_id`
  2. RevocationList INSERTs for each LOST token in APPROVED branch (UC-4 pattern)
  3. Administrative vs operational grace-period framing per PDF §9.1
  4. "Schema constrains shape, agencies decide" framing section
  5. Audit-row tag format `[RECOVERY:<id>]`
  6. Admin role required for deciding-user (schema CHECK + Flask @require_role); reuse existing admin role instead of new security-officer
- Blast radius: 12 files
- Tests planned: 13 CatastrophicLossRecoveryTests + 2 ConcurrencyTests + 5 SQL section M

## III. Alternatives considered

1. **HIGH risk** — defensible (identity issuance is sovereign-grade) but the three-channel + cool-down + co-sign mechanism makes the attacker cost concrete enough for MEDIUM
2. **Single-phase ceremony (no cool-down)** — rejected: removes the
   surprise-element defense; attacker can social-engineer one operator
   fast
3. **New `security-officer` role for completion** — rejected: requires schema migration; existing admin role is the cleaner role-split (operator initiates, admin completes)
4. **Operational grace credential (TemporaryAttestation) in v1** — rejected: requires verifier-side integration outside R11-2's scope; deferred to follow-up with explicit rationale recorded
5. **Auto-derive recovery state from token state** — rejected: same anti-auto-derivation posture as R11-4

## IV. Recommendation

Implement R11-2 with all six refinements folded in. Two-phase
ceremony: `uc9_initiate_recovery` (operator) + `uc9_complete_recovery`
(admin only, RAISE EXCEPTION enforced). Four CHECK constraints on
`RecoveryRequest` (cool-down ≥ 48h, three OOB channels for APPROVED,
decided_at after cool-down, approver ≠ requester). Per-individual
advisory-lock for C9.

## V. What's needed from VANTA

"Yes do R11-2" plus answers to three remaining open questions:
cool-down length (recommend 48h), notification path (recommend
deferred), TemporaryAttestation deferral acceptance (recommend
explicit deferral with rationale recorded).

## VI. Decision

"yes do R11-2" — VANTA approved with all refinements and the three
recommended deferrals.

## VII. Outcome

Shipped v8.17 (2026-05-11). 13 + 2 + 5 = 20 new tests, all green.
The "schema-doesn't-weaponize-itself-against-the-holder" triad is
now structurally complete (entry R11-4 + exit R11-6 + recovery R11-2).
v2 done-list 6/12 → 7/12.
[CHANGELOG v8.17](../CHANGELOG.md#v817--2026-05-11-r11-2--m2-7-catastrophic-loss-recovery--uc-9).
