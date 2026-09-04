# QuantumObserverBinding

**Reader:** an engineer or assessor who found an empty table named after
quantum measurement and wants to know whether Polaris claims to do something
it does not. **Job:** state exactly what the table is, what it is not, and
what would have to be true before anyone built on it.

**Status: reserved, not planned.** The table exists. Nothing writes to it, no
row has ever left the `SCAFFOLD` state, and no stored procedure references it.

## What is in the schema

`polaris_sql/01_schema.sql` defines `QuantumObserverBinding` with a foreign key
to `IdentityToken`, a `binding_status` constrained to `SCAFFOLD`, `OPERATIONAL`
or `DEPRECATED` and defaulting to `SCAFFOLD`, and three nullable fields that
are deliberately unpopulated: the measurement protocol, the witness hash, and
the hash algorithm. The status enum is the record that the substrate is
unfinished, in the schema itself rather than in a comment.

The idea it reserves is narrow: a token could one day be bound to a physical
measurement event at issuance, so that the enrolment ceremony leaves a record
that cannot be copied. Whether that is ever useful depends on hardware that
does not exist as deployable infrastructure.

## Why it is not built

- **There is no threat to defend against yet.** Building a rotation path for a
  hypothetical successor algorithm, whose triggering conditions cannot be
  named, is abstraction without grounding.
- **The name is grander than the thing.** What the table would hold is a
  future algorithm-rotation binding. Implementing it under this name would
  make the operator-facing surface sound more built than it is, which is the
  failure this project refuses.

The scaffold stays because it documents the intended shape for whoever
eventually needs it, and because an empty table with an honest status enum
costs nothing at runtime. What is deliberately absent is any write path.

## What would reopen the decision

1. A successor post-quantum signature standard reaching at least draft
   maturity with a deployment timeline that intersects a Polaris deployment's
   service life. ML-DSA-65, which ships today, is FIPS 204 ratified.
2. A deployment that must rotate algorithms without invalidating existing
   tokens, in a way the `TokenSignature` multi-signature migration path cannot
   express.
3. A demonstrated cryptographically relevant quantum attack against the
   lattice assumptions ML-DSA-65 rests on.

Absent all three, the scaffold stays scaffolded.

## For an operator

Leave the table read-only for the application role. The default grants already
are: no procedure writes to it, so no grant was ever added. If a future pass
widens the grants, exclude this table explicitly until the status is
`OPERATIONAL` in a shipped, reviewed change.

## If it is ever removed

Removing the table rather than promoting it needs a migration that drops it, a
note here explaining why the substrate is no longer needed, and an update to
the substrate catalogue in [substrate.md](substrate.md), which lists this slot
as reserved. The default action is to leave it alone.
