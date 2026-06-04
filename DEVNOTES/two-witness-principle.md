# The two-witness principle

> Any cryptographic verdict Polaris ships must be checkable by a second,
> independent implementation. A verdict only one program can produce is a
> promise, not a proof.

Adopted v9.44 from the Glass language's Pentecost discipline, as the transferable
half of the 2026-06-03 Glass bounded-integration decision
(`sanctum/2026-06-03-glass-bounded-integration.md`). Glass's own ledger states it
plainly: a proof you cannot independently check is just a promise, and a verifier
you trust because it agrees with itself is not a verifier.

## The rule

When Polaris ships a component that renders a cryptographic **verdict** (valid /
invalid, member / non-member, accept / reject), that verdict must be reproducible
by a **second witness** that satisfies all of:

1. **Independent implementation.** Written separately from the primary verifier,
   ideally in a different language.
2. **Different representation.** Not a copy with the same number model; e.g.
   plain `int mod p` against the primary's limb arithmetic. Shared representation
   hides shared bugs.
3. **Shares no code** with the primary verifier (and, where the lineage matters,
   no code with any third system it is meant to cross-check).
4. **Must agree on the verdict** across the full honest and adversarial corpus,
   or **ABSTAIN explicitly** on any axis it cannot faithfully model. Silent
   non-coverage is forbidden: an abstention is logged, not hidden.

## What it buys, and what it does not

It catches **implementation divergence**: a bug in one verifier that the other
does not share. It is a differential check, not an audit. It does **not** catch a
shared misreading of the spec or threat model (both witnesses can be wrong about
the same thing), and it never substitutes for external review. Name the boundary
every time, the way `DEVNOTES/zk-soundness.md` and Glass's Pentecost README both
do.

## Why this fits Polaris

It is the cryptographic-verifier instance of a discipline Polaris already runs
elsewhere:

- **C9** requires concurrency hazards to be tested with real threading, not
  asserted. Same spirit: prove the property, do not claim it.
- The **oracle-runner** (`scripts/polaris-oracle-runner.sh`) already cross-checks
  computed results against an independent reference.
- The **HYDRA** watchers are deliberately redundant observers of the same system.

The two-witness principle extends that posture to the one place it was missing:
the ZK verdict, which until v9.44 rested on a single Rust verifier.

## Current instances

| Verdict | Primary witness | Second witness | Coverage |
|---|---|---|---|
| ZK Merkle-inclusion (membership + binding) | `polaris_zk` Rust crate (`verify`) | `polaris_zk/witness2/` (Python) | Statement-level; abstains on proof-byte integrity (`DEVNOTES/zk-soundness.md`) |
| PQC signature (ML-DSA-65, `pqc_signing.verify`) | liboqs / `oqs` (single impl) | **ABSTAIN — none yet** | Recorded per rule 4: a lone verifier, acknowledged not hidden. As of v9.58 the signing path is wired into issuance (`uc1_issue` calls `pqc_signing.signature_bytes_for_token`), but the real ML-DSA path is OFF by default (`POLARIS_USE_REAL_PQC`) and the verify path remains a single liboqs implementation, so it renders no production verdict today. Add a second witness (or an explicit ABSTAIN ledger) before it goes live. |

This is rule 4 in practice: a lone verifier is not silently shipped. The PQC
row is an ABSTAIN on record so the gap is visible until closed. See the
ROADMAP §OPEN NOW item for the second-witness / wiring work.

## The standing obligation

Any future verifier Polaris ships (a wider-tree SNARK, a real PQC signature
check, a recursive proof) inherits this rule. Shipping a lone verifier is a
finding, not a feature.
