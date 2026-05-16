# Sanctum: r11-5-duress-codes

**Date:** 2026-05-11
**Petitioner:** agent (Claude, Opus 4.7)
**Principal:** VANTA
**Trigger:** HIGH-risk ship-Sanctum (PDF §9.5 compulsion resistance); the **v2 mission-closer** — the last ⬜ in the v2 done-list.
**Risk class:** HIGH (timing-attack surface; silent-failure mode if mitigations imperfect; reusing well-known primitives but still load-bearing)
**Status:** CLOSED
**Architect brief ID:** arch-2026-05-11-003 (from the M2-10 readiness assessment immediately preceding this Sanctum)

---

## I. The Matter

VANTA's approval to ship **R11-5 / M2-10 — duress codes (compulsion resistance, PDF §9.5)**, the **last unbuilt v2 item**. After ship, v2 done-list = **12/12 ✅**.

## II. Preparation

- **Architect brief:** today (2026-05-11) — readiness assessment compared M2-10 to M2-1 on six dimensions and concluded M2-10 is engineering-tractable without exploration-Sanctum (well-bounded design space, reuses Werkzeug scrypt + constant-time comparison already in security.py).
- **Proposal draft:** [`proposals/R11-5-duress-codes.md`](../proposals/R11-5-duress-codes.md) — scoped within the standard pattern; **six audit refinements (R1–R6)** folded in before this Sanctum entry.
- **Alignment audit:** ran the established checklist plus three duress-specific items:
  - R1 — Constant-time hash comparison (Werkzeug `check_password_hash`)
  - R2 — Identical observable behavior to the coercer across all branches
  - R3 — DuressEvent is the 8th audit-of-record instance
  - R4 — Per-token enrollment-only (anti-auto-derivation)
  - R5 — OOB notification v1 reference scope; v2 path named (SMS/Slack/SIEM)
  - R6 — Anti-revealing: DuressEvent NOT in standard verifications list
- **Blast radius if approved:**
  - Schema: +1 column on `IdentityToken` (`duress_code_hash`), +1 table (`DuressEvent`), +1 CHECK constraint
  - Procedures: +1 (`uc12_record_duress`)
  - Triggers: extends `reject_audit_modification` to DuressEvent (no new function)
  - Flask: `verifications_new` extended with optional `duress_code` field; +1 operator route `/duress` (admin); +1 JSON route `POST /api/duress/record` (admin) for test/automation paths
  - Tests: +10 `DuressCodeTests` + 4–5 SQL self-tests section R
  - DEVNOTES: 1 new (`duress-codes.md`), 1 extended (`audit-of-record.md` → 8 instances)
  - docs: `SECURITY.md` threat-model addition; `DATA-MODEL.md` `DuressEvent` section
  - **Substrate: ZERO new primitive** (reuses Werkzeug scrypt from `security.py`)
  - Counts: 22 → 23 tables; 12 → 13 procedures; 7 → 8 audit-of-record instances; advisory-lock catalog unchanged at 6 (DuressEvent is pure-append, no contention)
- **Tests planned:** ~15 (10 DuressCodeTests + 4–5 SQL section R).

## III. Alternatives considered

1. **No duress mechanism at all** — close v2 at 11/12. Rejected: M2-10 is on the v2 done-list because PDF §9.5 names it as an open problem. Leaving the schema without compulsion resistance would be the only PDF §9 problem not structurally addressed.
2. **Biometric-coercion-resistant mechanism instead** — a separate ROADMAP item that detects forced biometric (e.g., heart-rate-derived liveness). Rejected because it requires hardware integration outside Polaris's reference-impl scope. Duress codes are a software-level mitigation that works today; biometric coercion-resistance is a v3 candidate.
3. **Out-of-band-only signaling (no in-schema state)** — holder presses a panic button on their device that fires SMS, no Polaris involvement. Rejected because: (a) the holder's device might be the coercer's tool; (b) Polaris needs the audit-of-record for the duress signal, not just the alert.
4. **Use existing `proof_commitment` field for duress** — overload the hash field to mean "duress" when it matches a specific pattern. Rejected: this is the type of overloading the Polaris quality bar refuses. Add a clean column for a clean purpose.

## IV. Recommendation

Approve M2-10 ship as scoped in the proposal. All six audit refinements folded in. The "Pre-Sanctum sanity checklist" is fully green.

Three strategic points:

1. **This closes v2.** After M2-10 ships, the v2 done-list is 12/12. Every PDF §9 open problem has a structural answer. Every triad is complete. Every substrate-layer claim is demonstrated.
2. **Engineering complexity is much lower than M2-1.** No new substrate. The Werkzeug `check_password_hash` constant-time comparison is the same primitive used for AppUser authentication — battle-tested. The schema additions are minimal.
3. **The mission's "what's next" naturally surfaces after closure.** Once v2 is 12/12, the next session should be a v2 retrospective + v3 strategic-arc consideration (`meta/missions-considered.md` v3 candidates). This Sanctum's outcome will explicitly note that transition.

## V. What's needed from VANTA

Choose one:

- **"yes do M2-10"** — proceed with the audited proposal as scoped. v2 closes at v8.24.
- **"yes with changes: X, Y"** — proceed with modifications.
- **"phase differently"** — split the ship (schema-only first; verification-flow second).
- **"defer indefinitely"** — close v2 at 11/12; M2-10 stays open.
- **"reject"** — proposal needs deeper revision.

## VI. Decision

proceed with the architects recommendation

## VII. Outcome

Shipped end-to-end: IdentityToken.duress_code_hash (Werkzeug scrypt) + chk_duress_hash_well_formed CHECK, DuressEvent table (8th audit-of-record, append-only via reject_audit_modification), uc12_record_duress procedure, _check_and_record_duress helper using werkzeug.security.check_password_hash (constant-time R1), verifications_new extension with identical observable behavior across all four branches (R2), demo seed (Maria's T2 with plaintext '911911'), /api/duress/events (admin/auditor) + /api/duress/record (admin/operator) routes, 5 SQL self-tests section R, 13 DuressCodeTests — all passing on full clean reload. Six audit refinements R1-R6 folded in. **v2 mission-closer — v2 done-list = 12/12 ✅**. Every PDF §9 open problem now structurally answered. Canonical execution links: CHANGELOG.md v8.24 entry; MISSION.md M2-10 marked ✅; ROADMAP.md R11-5 marked ✅; DEVNOTES/duress-codes.md (new); DEVNOTES/audit-of-record.md extended to 8 instances; docs/SECURITY.md compulsion-resistance section; docs/API.md duress routes documented; docs/DATA-MODEL.md DuressEvent section.

