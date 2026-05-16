# DEVNOTES/ships/quantum-observer.md — M2-5 / R10-5

**Mission link:** v2 M2-5 (substrate arc) / R10-5 / Appendix F.2 of
the project report.

**Status:** SCAFFOLD. The `QuantumObserverBinding` table exists in
`polaris_sql/01_schema.sql` with all functional fields explicitly
deferred. This document explains what the binding *becomes* when
quantum-observer hardware exists, and why scaffolding it now is the
right move even though no row will be OPERATIONAL for years.

---

## What the binding becomes when the hardware exists

A QuantumObserverBinding row is a commitment that a specific identity
token was bound to a physical quantum-measurement event at issuance
time. The binding is rooted in the **no-cloning theorem**: a quantum
state cannot be copied without disturbing it. This means the
measurement record at issuance is, in principle, uncopiable —
producing the strongest form of "this token came from this enrollment
ceremony, not a forgery."

The current substrate (`GenomicAnchor` for biometric identity,
`DeviceBinding` for hardware-enclave attestation) provides commitment
to *classical* primitives that are forgeable given enough resources.
The quantum-observer binding is the substrate-level upgrade for an
era when quantum measurement becomes a routine cryptographic
primitive — currently a research frontier, not deployed infrastructure.

### Expected protocols (Appendix F.2)

Per the project report, the anticipated `observer_protocol` values are:

- **BB84-WITNESS** — a BB84 quantum-key-distribution session captured
  the entropy that conditioned the token's signature. The witness
  hash commits to the measurement basis sequence.
- **E91-ENTANGLEMENT-WITNESS** — Ekert's entanglement protocol. The
  binding asserts that two parties measured an entangled pair, and the
  Bell-inequality statistic is part of the witness.
- **MEASUREMENT-INDEPENDENT-QKD** — MDI-QKD, which removes detector
  side-channels from the trust model.
- **CONTINUOUS-VARIABLE-QKD** — CV-QKD using coherent-state
  measurements.

The enum is intentionally NOT a CHECK constraint yet. Quantum-network
protocol vocabulary is unsettled; locking it in via CHECK now risks
forcing a schema migration when the field deploys. The scaffold-state
invariant (below) ensures the field stays NULL until the protocol set
stabilizes.

---

## Why scaffold now, not later

Three reasons, in order of leverage:

### 1. Reserves the namespace before it's contested

Once the hardware exists and the first deployment needs the binding,
adding a table is a schema migration with downtime. Reserving the
table now — empty, with status=SCAFFOLD — means the eventual
deployment is `UPDATE`-only, not DDL. The cost today is one table
definition. The cost without it is a coordinated schema migration
across all Polaris-using systems.

This is a **commitment device**: by committing to the table now, we
prevent a future failure mode where the spec writers and the
schema writers diverge on what fields the binding needs.

### 2. Makes the substrate manifest complete

The `SystemDependency` view (`polaris_sql/13_substrate.sql`) and the
prose mirror (`DEVNOTES/substrate.md`) catalog every primitive Polaris
depends on. Listing quantum-observer measurement as a *future*
primitive — with its current scaffold state — closes the loop on
what's currently in the substrate and what's reserved.

### 3. Forces the scaffold/operational distinction

Two CHECK constraints encode the state distinction:

- `qob_scaffold_defers_functional` — SCAFFOLD rows must have NULL
  functional fields. Catches premature population.
- `qob_operational_requires_functional` — OPERATIONAL rows must
  populate the functional fields. Can't claim functional binding
  without the data.

The constraints make the state transition reviewable: moving a row
from SCAFFOLD to OPERATIONAL requires populating the fields, which
will fire all the integrity checks. There's no quiet "well it's sort
of operational" intermediate state.

---

## Adversary walk

The walk has two regimes — *today* (SCAFFOLD) and *future*
(OPERATIONAL). Both are present because the scaffold is itself a
commitment device, and the commitment claim has adversaries even
before the hardware exists.

1. **Defender's claim:** Today, the schema reserves a slot for the
   future primitive with two CHECK constraints
   (`qob_scaffold_requires_null` + `qob_operational_requires_functional`)
   that make the scaffold↔operational transition explicit and
   one-way-auditable. Future, the OPERATIONAL row records a
   classical hash commitment to a quantum measurement, gated by
   `AgencyAlgorithmAuth` so the protocol vocabulary is authority-
   controlled.
2. **Attacker's optimal response:** Today, there is no attacker —
   every row is SCAFFOLD by definition; the deferred functional
   fields are enforced NULL by CHECK. The mechanism cannot be
   exploited today because it isn't doing anything yet. Future
   (operational regime), the attacker either breaks the no-cloning
   theorem (currently no known path) or forges the
   `collapse_witness_hash` without performing the underlying
   measurement.
3. **Equilibrium:** Today's equilibrium is schema readiness without
   functional commitment — when hardware deploys, no breaking
   migration. Future equilibrium reduces forgery resistance to
   classical hash-collision resistance under the chosen
   `collapse_hash_algorithm`, which is C7's algorithm-metadata
   table's responsibility (substitutable per the v8.30 principle).
4. **Second-best attack:** Today, the attacker attacks the
   *commitment-device* itself — e.g., pressure to reuse the
   reserved namespace for a different primitive, leaving the
   binding semantically orphaned. Mitigated by the explicit
   CHECK pair that pins SCAFFOLD vs. OPERATIONAL semantics in
   schema; any namespace repurposing would have to ship a Sanctum-
   class amendment. Future, the attacker attacks the measurement-
   to-hash boundary (the hardware-side protocol) rather than the
   hash itself.
5. **Defender's cost:** One table, two CHECK constraints, eleven
   scaffold-state rows in the test suite. Storage cost is
   dominated by the CONSTRAINT overhead per row (~µs per insert).
   The deeper cost is the cognitive overhead of carrying a
   scaffolded primitive in the codebase before its referent exists
   — accepted as the price of the commitment device.
6. **Mechanism-design note:** The scaffold is a **commitment
   device** for the future schema. Reserving namespace today
   prevents the political cost of a contested migration later.
   This is the same logic as v8.30's substitutability principle
   applied prospectively: name the future binding now, with
   substitutable implementation, so when hardware arrives the
   constitution doesn't need to be amended.

---

## State transitions

Two transitions, each a deliberate act:

```
SCAFFOLD → OPERATIONAL
  Requires populating observer_protocol, collapse_witness_hash,
  collapse_hash_algorithm. The qob_operational_requires_functional
  CHECK fires if any are missing. Should only happen when:
    (a) quantum-observer hardware is deployed in a real ceremony, AND
    (b) the protocol vocabulary has been agreed by the standards body
        Polaris is tracking (NIST PQC follow-on or successor), AND
    (c) AgencyAlgorithmAuth carries the new protocol authorization.

OPERATIONAL → DEPRECATED
  When a protocol is retired post-migration. Keep the row for audit;
  block new bindings under that protocol via WHERE binding_status='OPERATIONAL'
  filters in the issuance procedures.
```

A SCAFFOLD row that's never transitioned is fine — it's the resting
state until the hardware exists.

---

## What this binding does NOT do

- It does not store the quantum state itself (impossible by
  no-cloning, even if we wanted to).
- It does not perform a measurement at verification time. The binding
  is *issuance-time* commitment; verification reads the binding row.
- It does not replace `GenomicAnchor` or `DeviceBinding`. It's a
  parallel substrate primitive, not a successor.
- It does not couple to monetary or spending semantics. The C10
  invariant (identity ≠ money) holds; quantum-attestation strengthens
  identity, not value.

---

## Tests

`polaris_web/test_app.py::QuantumObserverBindingTests` covers:

1. Table exists and is empty by default.
2. SCAFFOLD-state insert with NULL functional fields succeeds.
3. SCAFFOLD-state insert with any populated functional field fails
   (qob_scaffold_defers_functional CHECK fires).
4. OPERATIONAL-state insert with NULL functional fields fails
   (qob_operational_requires_functional CHECK fires).
5. OPERATIONAL-state insert with all functional fields populated
   succeeds — proves the scaffold doesn't block the eventual
   functional state.
6. Invalid binding_status fails the enum CHECK.

The tests verify the scaffold is enforceable as a state, not just
a placeholder name. Without them the SCAFFOLD/OPERATIONAL distinction
would be advisory only.

---

## Re-evaluation triggers

This document should be revisited when:

- Quantum-observer hardware achieves deployment-grade maturity (years
  out as of 2026)
- NIST or successor publishes a quantum-network attestation standard
- The first OPERATIONAL row is created (the scaffold becomes functional)
- A successor primitive supersedes quantum-observer attestation
  before it deploys (in which case this scaffold may be DEPRECATED
  pre-deployment)
