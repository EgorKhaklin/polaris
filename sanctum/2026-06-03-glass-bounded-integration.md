# Sanctum: glass-bounded-integration

**Date:** 2026-06-03
**Petitioner:** agent (Claude, Opus 4.8)
**Principal:** VANTA
**Trigger:** VANTA proposed reworking Polaris with the Glass language: *"lets use glass to completly rework polaris because glass perfectly suits the needs of Polaris. (dont change anything in the glass folder itself.) whatchu think?"* A complete rework is a new-mission-scope, HIGH-risk event that the post-v2 steady-state posture routes to decline-and-surface.
**Risk class:** HIGH (adjudicates a complete-rework / chassis-replacement request). Shipped outcome is bounded hardening within the v9.31 freeze envelope.
**Status:** CLOSED — DECIDED + SHIPPED (v9.44)

---

## I. The Matter

Glass (`/Users/vanta/Desktop/Glass`, kept untouched per VANTA's instruction) is a
self-hosting, effect-typed, zero-knowledge-native research language with a
from-scratch STARK prover and a double-verifier ("Pentecost") discipline. Its
thesis — *you should never have to take the code's word for it* — genuinely
rhymes with Polaris (zero-knowledge identity, audit-of-record, anti-coercion).
The proposal: rework Polaris using Glass because it "perfectly suits" Polaris.

The question is whether that fit justifies a **complete rework**, or only a
**bounded, additive** use of Glass.

## II. Preparation

An adversarial fit-analysis workflow ran first (4 evidence probes, then steelman
briefs for both YES-rework and NO-bounded, then a judge). Key findings, each
verified against source:

- **Glass disavows the production role in its own banner.** `docs/soundness.md`:
  *"Do not use Glass to protect real value."* `LANG.md`: *"Self-hosting research
  language (not production-hardened)."* Routing identity crypto through an
  explicitly-educational substrate while presenting it as trustworthy would
  violate C7 and the Vocation's trustworthiness clause (refused on sight).
- **Polaris's security boundary is Postgres, not portable app code.** C1-C10 are
  partial unique indexes, CHECK constraints, and plpgsql triggers depending on
  MVCC, row locks, and partial-index uniqueness under contention. Glass's entire
  effect surface is `read_file/write_file/run_command/print/random_int/model_call`
  — no socket, HTTP, SQL driver, sessions, WebAuthn, or CSP. It cannot host a
  single invariant without first rebuilding a transactional relational store.
- **The one pure-functional component (the Rust ZK crate) is already the right
  tool**: memory-safe, audited `plonky2` 0.2, transparent FRI, no trusted setup.
  Re-expressing it in Glass trades that for from-scratch C output — a strict
  downgrade.
- **The genuinely transferable assets are a method, not the crate**: the Pentecost
  two-witness discipline and the soundness-ledger honesty. The convergence is
  real and verified: Polaris's crate and Glass both live on Goldilocks (2^64) with
  the Poseidon hash family, which makes a Polaris-side second verifier a
  known-shaped task rather than research.
- **Governance independently bars the rework as a default action.** It is HIGH-risk
  new scope touching `06_triggers.sql`, `01_schema.sql` DROP/ALTER, and
  `security.py` simultaneously; it collides with the committed v9.31 freeze line;
  and chassis replacement was already rejected once (v9.08 showroom Sanctum,
  `sanctum-index.md:29`) for forking the v8.20 audit-of-record into before/after
  eras.

**Blast radius of the shipped (bounded) work:**
- `polaris_zk/witness2/` — new independent Python verifier package (poseidon,
  merkle, verifier, constants, unit tests).
- `polaris_web/test_zk_second_witness.py` — Rust-vs-Python verdict differential.
- `DEVNOTES/zk-soundness.md`, `DEVNOTES/two-witness-principle.md` — new docs.
- `polaris_web/test_structural_invariants.py` — one new TestWave class.
- Version/CHANGELOG/journal/scorecard per the ship runbook. No engine, schema,
  trigger, security, or web-route change.

## III. Alternatives considered

1. **Complete rework on Glass (chassis replacement).** Rejected. Routes production
   identity crypto through an explicitly-educational substrate (C7 / Vocation
   violation), cannot host the Postgres-enforced invariants, downgrades the one
   pure-functional component, and breaks freeze + AoR governance. Glass's own
   ledger forbids it.
2. **Re-express only the Rust ZK crate in Glass.** Rejected. Strict downgrade:
   loses audited `plonky2`, memory safety, and performance; gains nothing the
   second-witness pattern does not already give.
3. **Bounded integration — adopt the Pentecost method, not the Glass crate
   (recommended).** Build an independent second witness for the existing Plonky2
   proof, add the soundness ledger, and document the two-witness principle. All
   additive, offline, reversible; captures the real value with none of the
   substrate-rebuild or unaudited-crypto-on-the-trust-path risk. Mirrors the
   standing "banking as a separate repo consuming Polaris over HTTP" posture.
4. **v9.40 claim-retirement** (retire the strong production claim, keep Polaris as
   tooling). Honest and available, but a separate doc/posture decision; not
   required by this Sanctum and not bundled into it.

## IV. Recommendation

Decline the complete rework. Ship Alternative 3 as v9.44 hardening. The complete
rework remains available to VANTA only via the explicit heavy-production override
("boil the ocean" / "Vanta Sanctum authorized") plus a v9.31 freeze amendment
with written cost — none of which were invoked.

## V. Decision

VANTA, 2026-06-03: *"go ahead with the bounded integration plan."*

DECIDED: bounded integration. SHIPPED in v9.44.

- The verdict of `polaris_zk::verify` is now two-witnessed by `polaris_zk/witness2/`
  (independent Python Goldilocks+Poseidon+Merkle, anchored on Plonky2's published
  vectors, agreeing bit-for-bit with the live Rust binary on root computation and
  ACCEPT/REJECT across the honest + adversary corpus; abstaining only on
  proof-byte integrity, which it documents).
- `DEVNOTES/zk-soundness.md` is the honest ledger (demo-scale `TREE_DEPTH=4`,
  placeholder PQC, statement-level witness scope).
- `DEVNOTES/two-witness-principle.md` makes "every cryptographic verdict must be
  two-witnessed" a standing Polaris obligation.

The Glass folder was not modified. No production substrate was touched. The
complete-rework path is recorded here as available-but-not-taken.
