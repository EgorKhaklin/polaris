# `meta/tla/` — formal-verification demonstrator

**Status:** Demonstrator artifact, NOT maintained verification
infrastructure.
**Origin:** BIG MISSION Sanctum (`sanctum/2026-05-15-big-mission.md`),
item High #1
**Last reviewed:** 2026-05-15 (v9.23)

## What this directory IS

A demonstration of the TLA+ technique applied to ONE Polaris
constraint (C3 — one identity per person). The spec
`c3-one-active-token.tla` models the schema-level partial unique
index + the application-layer FOR UPDATE locking, and shows that
the C3 invariant holds under all interleavings of concurrent
issue/revoke operations.

## What this directory is NOT

Ongoing verification infrastructure. The Anti-Architect (BIG MISSION
Sanctum, §II High #1) refused the broader scope of "ship TLA+ specs
for C1, C2, C3" on AP7 grounds (premature abstraction). The
maintenance burden of keeping multiple specs in sync with schema
changes outweighs the marginal value when:

- Hypothesis property tests (`test_invariants_property.py`) already
  cover C1, C2, C3 with randomized inputs
- Schema-level CHECK constraints and partial unique indexes enforce
  the constraints at the database level
- Structural invariants (`test_structural_invariants.py`) pin the
  enforcement primitives in place

This single spec is shipped as a demonstrator artifact. If a future
Sanctum decides formal verification should become a maintained
surface, that's a separate ship.

## Running the spec

Requires TLA+ Toolbox or TLC command-line. With TLC:

```bash
# Install TLA+ tools
brew install tla-plus-tools   # macOS
# or download from https://lamport.azurewebsites.net/tla/tla.html

# Run TLC with a config file
tlc -config C3OneActiveToken.cfg C3OneActiveToken.tla
```

Expected output (abbreviated):

```
TLC2 Version 2.18 ...
Computing initial states...
Finished computing initial states: 1 distinct state.
Progress(N) at ... — 9,847 states generated, 2,103 distinct states.
...
Model checking completed. No error has been found.
```

## What the spec covers

- **State:** the set of `IdentityToken` rows (id, individual_id,
  status) + the set of FOR UPDATE locks held by active transactions
- **Actions:** AcquireLock, IssueToken, RevokeToken, ReleaseLock
- **Invariant:** C3_OneActiveTokenPerIndividual — no two ACTIVE
  tokens may share an individual_id at any reachable state

## What the spec does NOT cover

- The PostgreSQL-internal implementation of the partial unique
  index (the spec models the constraint; the implementation is
  checked in `08_tests.sql`)
- Cryptographic verification (signing, ZK proofs, anchoring)
- The application-layer authentication
- Other constraints C1, C2, C4-C10

## Future specs (NOT planned in v9.23)

The Anti-Architect's refusal stands until a Sanctum reopens it.
Candidates if reopened:

- C1 audit-of-record: state machine of append-only behaviors
- C2 zero-knowledge: information-flow proof of disclosure separation
- C7 cryptographic-rotation: state machine of algorithm transitions

Each would require a separate Sanctum + ship. Default action: leave
this directory as the one demonstrator.

---

*Per BIG MISSION Sanctum, 2026-05-15.*
