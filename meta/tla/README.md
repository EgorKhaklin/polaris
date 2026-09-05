# meta/tla/: the formal-verification demonstrator

**Reader:** an assessor who found a TLA+ spec and wants to know how much weight
it carries. **Job:** one spec, one constraint, checked once to show the
technique. This is not maintained verification infrastructure, and nothing in
CI re-checks it.

## What the spec models

`c3-one-active-token.tla` models C3, one active token per person: the
schema-level partial unique index and the `FOR UPDATE` locking inside
`uc1_issue_and_activate`, and shows the invariant holding under every
interleaving of concurrent issue and revoke operations.

- **State:** the `IdentityToken` rows (id, individual, status) and the locks
  held by the transactions in flight.
- **Actions:** acquire a lock, issue a token, revoke a token, release a lock.
- **Invariant:** no two ACTIVE tokens share an individual, in any reachable
  state.

It does not model the PostgreSQL implementation of the index itself, which
`08_tests.sql` exercises against a real database, nor any cryptography, nor the
other nine constraints.

## Why there is only one

A standing set of specs would have to be kept in step with the schema on every
change, and a model that has drifted from the schema it claims to describe is
worse than no model. Meanwhile the properties are already covered where they
bind: Hypothesis property tests over C1, C2 and C3 with randomised inputs, the
CHECK constraints and partial unique indexes in the database, and one
`check_*` per invariant in the check layer with a detection test.

Specs for C1, C2 or C7 would each be a deliberate ship, taken with that
maintenance cost accepted. The default is to leave this as the one
demonstrator.

## Running it

Requires the TLA+ tools (`brew install tla-plus-tools`, or the Toolbox). The
spec ships without a TLC configuration file; the one it expects is written out
in a comment at the foot of the spec, so create it first:

```bash
cd meta/tla
cat > c3-one-active-token.cfg <<'CFG'
SPECIFICATION Spec
CONSTANTS
    Individuals = {1, 2}
    MaxTokens = 4
    MaxOperations = 12
INVARIANT C3_OneActiveTokenPerIndividual
INVARIANT TypeOK
CFG
tlc -config c3-one-active-token.cfg c3-one-active-token.tla
```

A passing run reports model checking completed with no error found, after
generating a few thousand states. The configuration is not committed because
nothing re-runs it: writing it is part of choosing to check the spec.
