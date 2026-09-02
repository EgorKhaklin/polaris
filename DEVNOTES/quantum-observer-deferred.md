# QuantumObserverBinding — RESERVED-NOT-PLANNED

**Status:** RESERVED-NOT-PLANNED
**Origin:** M2-5 substrate scaffold shipped v8.11
**Decision:** v9.23
**Last reviewed:** 2026-05-15

---

## What the scaffold is

The `QuantumObserverBinding` table exists in `polaris_sql/01_schema.sql`:

```sql
CREATE TABLE QuantumObserverBinding (
    binding_id          SERIAL       PRIMARY KEY,
    token_id            INTEGER      NOT NULL REFERENCES IdentityToken(token_id),
    binding_status      VARCHAR(20)  NOT NULL DEFAULT 'SCAFFOLD'
        CHECK (binding_status IN ('SCAFFOLD', 'OPERATIONAL', 'DEPRECATED')),
    -- ...
);
```

The `SCAFFOLD` CHECK enum value is the constitutional record that this
substrate is unfinished. Every row that exists today has
`binding_status = 'SCAFFOLD'`. No code path writes `OPERATIONAL`.

The intent at v8.11 was to model a future post-quantum migration where
some tokens are bound to a quantum-observer signature scheme (a
hypothetical NIST PQC successor) and others are not. The substrate
would allow per-token algorithm rotation without invalidating the
existing token corpus.

---

## Why we are NOT building it

Two problems argue against implementing it now:

- **Premature abstraction:** there is no deployed quantum threat
  to defend against. Building infrastructure for a hypothetical
  algorithm-rotation event whose triggering conditions cannot be
  named is the textbook abstraction-without-grounding failure mode.
- **Honest naming:** "QuantumObserverBinding" is a naming flourish.
  The underlying concept is "future post-quantum algorithm rotation
  table". Calling it Quantum Observer Binding makes it sound more
  built than it is, which the operator-facing demo would inherit if
  we implemented it. The demo must not lie about what Polaris does.

The substrate stays in the schema because it documents the migration
model so future implementers know the schema shape. What we are NOT
doing is implementing the write path or coupling it to any code that
fires today.

---

## Triggers for promotion to OPERATIONAL

The following operational triggers would justify reopening this decision:

1. **NIST PQC successor algorithm finalized** with a deployment
   timeline that intersects Polaris's expected service life. ML-DSA-65
   (currently deployed; v8.x) is FIPS 204 ratified; a successor would
   need to be at least at draft-standard maturity.
2. **A deployed Polaris instance must rotate algorithms** without
   invalidating extant tokens, and the existing `TokenSignature`
   table's multi-sig migration path (R11-1) is insufficient (e.g.,
   the rotation involves a fundamentally different signature scheme
   geometry, not just an algorithm change).
3. **Documented quantum threat materialization** affecting current
   ML-DSA-65 deployments (cryptographically-relevant quantum computer
   demonstrated against lattice-based schemes, etc.).

Absent any of these, the scaffold remains scaffolded.

---

## What the operator should do

For any deployment, set `QuantumObserverBinding` to read-only for the
application role:

```sql
REVOKE INSERT, UPDATE, DELETE ON QuantumObserverBinding FROM polaris_app;
```

This is not currently in `polaris_sql/09_grants.sql` because the
default v8.11 grant was already read-only for this table (the procedure
that would write to it was never shipped, so no grant was added). If a
future operator extends the grants, they should *exclude* this table
explicitly until the OPERATIONAL state is reached.

The structural invariant `test_quantum_observer_binding_is_scaffold_only`
(TestWave23V923) verifies that no row exists with
`binding_status != 'SCAFFOLD'` in the seed data, and that no UC
stored procedure writes to this table.

---

## Vocation alignment

ANTI-COERCION-NEUTRAL. This is a future-cryptography substrate, not a
direct anti-coercion primitive. The explicit deferral *is* anti-larping,
which is itself a small anti-coercion contribution (an operator
inspecting Polaris sees an honest accounting of what is and is not
built; this honest accounting is itself coercion-resistant — a
coercer cannot leverage an inflated capability claim against the
operator if the capability is documented as unbuilt).

---

## Related decisions

- v9.16 — RESERVED-NOT-PLANNED framing originated here
- v8.11 — M2-5 scaffold shipped
- v8.20 — old documents are frozen; the v8.11 ship's SCAFFOLD status
  is not retroactively edited

---

## Removal

If the table is removed entirely (rather than promoted to OPERATIONAL),
the record of the removal must include:

- A note explaining why the substrate is no longer needed
- A migration that DROP TABLEs `QuantumObserverBinding`
- Update to this document marking it CLOSED-REMOVED
- Update to the v2 done-list in [`record.md`](record.md) (currently lists
  M2-5 as "scaffold shipped"; would move to "removed")

The default action is to leave the substrate in place.
