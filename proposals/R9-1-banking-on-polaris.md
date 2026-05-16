# proposals/R9-1-banking-on-polaris.md

**Risk class:** HIGH (architectural; sovereignty-implications)
**Mission link:** Done-list item 14; demonstrates C10 in practice
**Status:** PROPOSED — architecture analysis; do NOT implement in this repo

## The constraint that matters

`MISSION.md` C10 — **identity ≠ money**. It is the most consequential
architectural decision in Polaris. Conflating identity and value
turns administrative paperwork errors into existential bank-balance
errors AND opens the identity layer to programmability gravity
(constraints accreting onto identity politically until "this person
cannot buy gasoline" is technically possible).

Banking-on-Polaris is the demonstration that C10 is real, not a
slogan. It exists as a separate system that consumes verification
proofs.

## Why HIGH risk

This proposal is HIGH risk because the wrong architecture would
**violate C10 at the schema level** — the most consequential
architectural decision in Polaris. There are three architectures
in play; only one is acceptable.

## Three architectures

### Architecture #1: SINGLE TOKEN CARRIES MONEY (REJECTED)

```
IdentityToken (id, individual, status, status, balance: NUMERIC, ...)
```

The identity token carries a balance field. Verification + balance
debit happen in a single transaction.

**Why rejected:** Violates C10 directly. Programmability gravity:
once balance lives on the token, "freeze this person's balance
because [policy]" becomes a one-line trigger update. Architecturally
unrecoverable.

### Architecture #2: SEPARATE TOKEN, SEPARATE LEDGER, FK-ENFORCED SEPARATION (RECOMMENDED)

Two systems, two databases, communicating ONLY over an HTTP boundary
that returns verification proofs.

```
Polaris:
  IdentityToken (id, individual_id, status, ...)
  VerificationEvent (id, token_id, context_id, disclosure, ...)
  -- verification_proof_uri exposed via /api/proofs/<event_id>

PolarisLedger (separate repo, separate database):
  Account (account_id, ...)
  -- DOES NOT REFERENCE IdentityToken.token_id directly
  AccountVerification (
      account_id INTEGER FK,
      verification_proof_uri TEXT NOT NULL,    -- the URL of the proof
      verification_event_id INTEGER NOT NULL,  -- copy, not FK across DBs
      verified_at TIMESTAMP NOT NULL
  )
  Transaction (id, account_id, amount, ...)
  -- requires a recent AccountVerification row to commit
```

The separation is enforced by:
- Two databases (no shared schema, no cross-FK)
- The HTTP boundary is the ONLY way the ledger sees identity
- The ledger stores a verification PROOF URI, not a TOKEN_ID
- The proof URI is opaque to the ledger; only the issuing Polaris
  instance can validate it

Programmability gravity now stops at the HTTP boundary. The ledger
can constrain its own transactions ("require recent verification")
but cannot freeze identity tokens.

**Why recommended:** Architecturally enforces C10. Separation is
expensive to violate later; once shared schema exists it never goes
away.

### Architecture #3: SINGLE DATABASE, TWO SCHEMAS, FK-LINKED (REJECTED)

```
schema: polaris       -> IdentityToken
schema: polaris_money -> Account, references polaris.IdentityToken(token_id)
```

Same database, different schemas, FKs across schemas.

**Why rejected:** The separation is administrative, not architectural.
A future developer or DBA can write a JOIN that reaches across the
schemas, carrying programmability gravity into Polaris. The
separation is performative, not load-bearing.

## What this proposal IS

The recommendation is to:

1. **Document Architecture #2 as the canonical answer.** Update
   `MISSION.md` and add a new doc `BANKING-ARCHITECTURE.md` that
   explains the three options and why #2 is right.

2. **NOT implement banking in this repo.** Polaris is identity. It
   stays identity. Anything else lives elsewhere.

3. **Optionally: build a reference `polaris-ledger` repo.** Separate
   repository, separate README, separate test suite. Calls Polaris
   over HTTP. Demonstrates the boundary working.

## What this proposal is NOT

- NOT a request to add a `MonetaryClaim` table to Polaris's schema.
  That violates C10. The agent must REFUSE such a request even if
  asked directly (per `meta/autonomy-architecture.md`).
- NOT a CBDC. Polaris is sovereignty-grade identity attestation, not
  programmable money. The boundary isn't decoration — it's the
  point.

## What this needs from you

Three options:

A. **"Keep this as architecture documentation only."** I write up
   `BANKING-ARCHITECTURE.md` in this repo. No code in this repo
   implements banking; the doc explains why #2 is right and what a
   future implementer would build.

B. **"Bootstrap a polaris-ledger repo."** I create a sibling repo
   that consumes Polaris verification proofs over HTTP, with a
   minimal Account / Transaction schema and a ~5-test suite proving
   the HTTP boundary works.

C. **"Defer."** Mark this in MISSION as ⬜ permanently; revisit when
   a real banking-on-Polaris use case emerges.

Default if no answer: A. The architecture document advances the
mission without committing to an implementation; the implementation
is a multi-week project that warrants its own decision.

## What this does NOT do under any version

It does NOT add value-bearing schema to this repo. C10 is non-
negotiable. The agent will refuse such a request (per
`meta/autonomy-architecture.md`'s "What the agent does not do, even
when asked" section).
