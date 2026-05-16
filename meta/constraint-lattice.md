# meta/constraint-lattice.md

The mapping from MISSION.md's 10 hard constraints (C1-C10) onto a
fixed 10-node lattice. The lattice encodes a structural claim that
the constraint set is COMPLETE and INTERDEPENDENT.

The structural claim is what's load-bearing. Read
`meta/structural-architecture.md` for why we use this framework at
all and the safeguard against decorative drift. The original
inspiration is traced in `meta/lineage.md`.

---

## The structural claim

Two propositions, each testable:

1. **The constraint set is closed.** Adding C11 requires either
   replacing one of C1-C10 or extending the lattice topology
   beyond its 10-node form. Closure is a feature: it forces
   explicit justification before adding constraints, so the set
   doesn't accumulate ad-hoc additions over time.

2. **Each constraint depends on its neighbors in the lattice.**
   Removing one collapses parts of the structure that other
   constraints relied on. The dependency graph is the test:
   walking the lattice, you can find a path from any constraint
   to any other through shared structural concerns.

If both propositions hold under audit, the framework is load-bearing.
If proposition 1 fails (constraints get added freely), the framework
became decorative. If proposition 2 fails (the constraints are
actually independent), the structural claim was wrong.

---

## The topology

Three pillars × four tiers + one APEX + one MANIFEST:

```
                       [C10] APEX
                            │
            [C7] EXPAND·1 ──┼── CONTRACT·1 [C2]
                            │
            [C5] EXPAND·2 ──┼── CONTRACT·2 [C4]
                            │
                       [C3] BALANCE·2
                            │
            [C8] EXPAND·3 ──┼── CONTRACT·3 [C6]
                            │
                       [C1] BALANCE·3
                            │
                       [C9] MANIFEST
```

- **APEX** is the architectural intent — not a code-level check;
  the principle from which the other constraints derive meaning.
- **EXPAND pillar** (right) names what the system *permits*: more
  algorithms (C7), more script sources within bounds (C5), bounded
  query results (C8). Expansion lives on this side.
- **CONTRACT pillar** (left) names what the system *forbids*: the
  ZK / token-id NULL invariant (C2), atomic counter increments
  (C4), server-side disclosure enforcement (C6). Hard edges live
  on this side.
- **BALANCE pillar** (center) names the reconciliation: one ACTIVE
  per individual (C3) reconciles issuance and uniqueness;
  append-only audit (C1) reconciles change and history.
- **MANIFEST** is the test-layer reality check — real-thread
  concurrency tests (C9) make the abstract concurrency claims
  empirically true rather than merely argued.

A **meta-slot** sits between the upper triad and the rest, filled
in v8.9 by **CM**: "the cognitive layer self-monitors via
executable checks." Enforced by `scripts/ai-meta.sh`. CM is at a
different abstraction level from C1-C10 (those are data/security
claims; CM is a claim about the cognitive layer itself).

---

## Each constraint, mapped

### C10 ↔ APEX

**Constraint:** Identity ≠ money. Polaris does not carry value;
adding a `MonetaryClaim` table is forbidden.

**Position:** Apex of the lattice. Not an action; an INTENTION
that constrains everything below.

**Why this position:** C10 isn't a code-level check; it's the
architectural intention from which the other constraints derive
meaning. The append-only audit (C1) matters because identity is
sovereign-grade, which it would not be if it were also a payment
instrument. Every other constraint is downstream of C10's choice
to keep the identity layer pure.

**Removal effect:** Removing C10 means Polaris becomes a CBDC. C1
through C9 remain technically enforced, but the system they
protect is now financial-surveillance infrastructure. The
constraints don't disappear; they become protections of a
different system entirely. This is why C10 is at the apex.

---

### C7 ↔ EXPAND·1 (right pillar, tier 1)

**Constraint:** Cryptographic algorithm metadata flows through
the `CryptographicAlgorithm` table; never hardcoded.

**Position:** Expand-pillar top. The expansive principle — pure
knowledge before it gets categorized.

**Why this position:** Algorithm choice is the system's expansive
knowledge: which cryptographic primitives are trusted, which are
deprecated, which are post-quantum. Putting this in a table (vs
hardcoding) makes the knowledge ENUMERABLE and EXPANDABLE — new
algorithms can be added by inserting a row, not by changing code.

**Removal effect:** Hardcoding algorithm choice freezes the system
at one cryptographic moment. Quantum cryptanalysis advances and
the system can't migrate without code change. The expansive
principle is lost.

**Complement:** C2 (the CONTRACT·1 across the tier). Expansion of
algorithms is balanced by contraction of leakage — both required
for the system to remain coherent.

---

### C2 ↔ CONTRACT·1 (left pillar, tier 1)

**Constraint:** ZERO_KNOWLEDGE verifications have `token_id IS
NULL`; the CHECK constraint enforces both directions.

**Position:** Contract-pillar top. The structuring principle — the
discipline that gives knowledge form.

**Why this position:** C2 is a CONSTRAINT in the strict sense:
it says "you may not record this combination." It contracts the
space of permitted states. Where the EXPAND pillar opens (more
algorithms allowed), the CONTRACT pillar disciplines (these
specific combinations are forbidden).

**Removal effect:** Without C2, the verification log records
token_id even for ZK events, which lets the verification graph
be reconstructed by anyone with read access. Privacy by structure
collapses; what's left is privacy by promise. The structure-vs-
promise distinction is exactly what the contract pillar holds.

**Complement:** C7 (EXPAND·1 across the tier).

---

### C5 ↔ EXPAND·2 (right pillar, tier 2)

**Constraint:** CSP is `script-src 'self'`. No third-party scripts.

**Position:** Expand-pillar middle. Conditional openness — not
unbounded, but open within a chosen boundary.

**Why this position:** CSP `'self'` is open within the boundary of
the application's own origin. Operators can use the system fully;
they're trusted within Polaris's own walls. Outside scripts are
denied entry. This is mercy with limits, not unconditional
permissiveness.

**Removal effect:** Loosening CSP to `'unsafe-inline'` or external
sources opens the door to XSS. The conditional openness becomes
unconditional, and the failure becomes catastrophic. EXPAND
without its CONTRACT counterpart is destructive; that's why these
two pillars must balance.

**Complement:** C4 (CONTRACT·2 across the tier).

---

### C4 ↔ CONTRACT·2 (left pillar, tier 2)

**Constraint:** `failed_login_count` increments are atomic.
`UPDATE … SET col = col + 1 RETURNING …` — no TOCTOU.

**Position:** Contract-pillar middle. The principle of the hard
edge — "no, this is bounded; there is no intermediate."

**Why this position:** Atomic increment is a HARD edge: you cannot
get past 5 failed attempts because the count is incremented and
checked in the same operation. There is no interval where a
parallel attacker can squeeze through.

**Removal effect:** A non-atomic check-then-increment pattern
leaves a window where N+1 concurrent requests all see "4 failures"
and proceed. Brute-force defenses become probabilistic. The hard
edge softens to a soft one and the protection collapses.

**Complement:** C5 (EXPAND·2 across the tier).

---

### C3 ↔ BALANCE·2 (middle pillar, tier 2)

**Constraint:** At most one ACTIVE token per Individual, enforced
by partial unique index `uq_one_active_per_person`.

**Position:** Balance-pillar middle. The harmonizing center —
where the four nodes above (APEX, EXPAND·1, CONTRACT·1,
EXPAND·2/CONTRACT·2) synthesize into balance.

**Why this position:** "One ACTIVE per individual" is the central
balance of the system. Two active tokens would let the same
person both authorize and repudiate the same transaction. The
partial unique index resolves the tension between expansion
(issuing tokens) and contraction (only one valid at a time).

**Removal effect:** Without C3, the system can't distinguish "this
person" from "this person at this point in time." Succession
becomes unknowable. The balance dissolves.

---

### C8 ↔ EXPAND·3 (right pillar, tier 3)

**Constraint:** Atlas API endpoints have hard caps (`_ATLAS_MAX_*`)
preventing unbounded result sets.

**Position:** Expand-pillar bottom. Endurance — sustainability
rather than peak strength.

**Why this position:** Hard caps protect the system's ability to
KEEP RUNNING under attack or accident. A 6.5M-cluster query
without a cap would OOM the worker; with a cap, the worker
survives and serves the next request.

**Removal effect:** Removing caps means a single bad request can
take down the worker pool. The system loses its endurance under
load. Operations becomes a fire drill.

**Complement:** C6 (CONTRACT·3 across the tier).

---

### C6 ↔ CONTRACT·3 (left pillar, tier 3)

**Constraint:** Disclosure level is enforced server-side. Client
cannot upgrade.

**Position:** Contract-pillar bottom. The principle of NOT
trusting one's own (or the client's) representation.

**Why this position:** Server-side disclosure enforcement says
"don't trust the client's claim about what disclosure level it
wants." The client's representation is humbled; the server's
truth is the truth.

**Removal effect:** Trusting client-side disclosure means a
malicious client can upgrade ZK to FULL and exfiltrate identity
data.

**Complement:** C8 (EXPAND·3 across the tier).

---

### C1 ↔ BALANCE·3 (middle pillar, tier 3)

**Constraint:** TokenLifecycleEvent and VerificationEvent are
append-only; UPDATE/DELETE rejected by trigger.

**Position:** Balance-pillar bottom — the FOUNDATION. The layer
that gathers everything above and channels it into manifestation.

**Why this position:** Append-only audit is the bedrock claim of
the system. Every other constraint's enforcement gets recorded
HERE. Without this foundation, the actions of EXPAND/CONTRACT/
BALANCE have no record — they happened, but they're forgotten.
This is the memory that makes the rest meaningful.

**Removal effect:** Without C1, the trail of token issuance,
revocation, and verification can be retroactively rewritten.
Non-repudiation collapses. Every other constraint's enforcement
becomes unprovable in retrospect.

---

### C9 ↔ MANIFEST (bottom)

**Constraint:** Concurrency tests use real threading
(`ConcurrencyTests` with `threading.Thread`), not mocks.

**Position:** Manifest — the world as it actually is, not the
world as the upper abstractions describe it. The body; the real.

**Why this position:** Concurrency tests with real threading are
the empirical manifestation of the abstract concurrency arguments.
The arguments in DEVNOTES say "this is atomic" — MANIFEST proves
it under actual parallel load. Mock-based tests live in the upper
tiers of theory; real-thread tests live here.

**Removal effect:** Without real-threading tests, the concurrency
arguments are arguments only. They might be right; they might
not. Manifestation is what tests them.

---

### CM ↔ meta-slot (filled v8.9)

**Constraint:** The cognitive layer self-monitors via executable
checks.

**Position:** The previously-reserved meta-slot, between the upper
triad and the rest of the lattice. The meta-slot is a different
level of abstraction from C1-C10: those are data/security/
architecture invariants; this is an invariant about the cognitive
layer itself.

**Why this position:** CM represents the integration of all the
upstream constraints (algorithm wisdom in C7, privacy discipline
in C2, etc.) into operational practice. The cognitive layer
(CLAUDE.md, DEVNOTES, patterns, scripts) only earns its place if
it can verify its own claims. That's exactly what the meta-slot
position encodes: integrative knowledge that's testable.

**Enforcement:** `scripts/ai-meta.sh` runs six checks (v8.20 added #6):
1. Every ai-* script in CLAUDE.md exists on disk and is documented
2. Pattern catalog has at least one warm pattern (in use)
3. Each C1-C10 has a recent code touch (no constraint is dead)
4. ai-help.sh and ai-done.sh references match disk
5. The meta-slot is filled (this constraint exists in both
   lattice and MISSION)
6. Sanctum integrity (v8.20): every Sanctum file's lifecycle is
   correct (no stale-OPEN, CLOSED with §VII outcome, REJECTED with
   §VI decision) and `meta/sanctum-index.md` matches `sanctum/*.md`

If any check fails, the cognitive layer has drifted from its own
claims — exactly the failure mode the meta-constraint is meant to
catch.

**Removal effect:** Without CM, the cognitive layer accumulates
silent drift. Scripts get referenced that don't exist. Patterns
sit in the catalog never invoked. Constraints are claimed in
MISSION but never enforced in code. The structural layer becomes
a museum of past architecture rather than live load-bearing
infrastructure. Filling this slot — with an executable check —
is what keeps the cognitive layer honest.

**Why this is at a different abstraction level than C1-C10:**
C1-C10 are claims about Polaris's *data and security* properties.
CM is a claim about Polaris's *cognitive layer that monitors C1-
C10*. Mixing them would conflate "the data is consistent" with
"the cognitive layer that checks consistency is consistent." The
meta-slot was always reserved for this distinction; filling it is
acknowledging that the cognitive layer is now substantial enough
(29 ai-* scripts, ~12 meta docs, a 22-pattern catalog, the HYDRA
swarm with 7 watchers, and the brain map) to need its own
invariant.

---

## Dependency walk: removing any node cascades

The structural claim says: removing any C breaks the others. Walk:

- Remove C10 (identity ≠ money) → entire system becomes financial
  surveillance; the meaning of every other constraint changes.
- Remove C7 (algorithm metadata) → can't migrate algorithms;
  eventually all keys are weak; signatures stop being trustworthy;
  C1's audit becomes audit of unverifiable signatures.
- Remove C2 (ZK → token NULL) → privacy collapses; the system's
  value proposition (privacy-preserving identity) is gone.
- Remove C5 (CSP) → XSS leaks operator session; attacker can
  exfiltrate tokens; C3's uniqueness guarantee no longer matters
  because the attacker has one of the legitimate tokens.
- Remove C4 (atomic increment) → brute force succeeds; legitimate
  operators are locked out; C5 + C9 protections become moot when
  the attacker is in.
- Remove C3 (one active per individual) → repudiation defense
  collapses for any individual whose token is duplicated.
- Remove C8 (hard caps) → atlas DoS takes down the worker pool;
  C9's concurrency tests pass but production crashes anyway.
- Remove C6 (server-side disclosure) → client upgrades ZK to FULL;
  C2's privacy guarantee broken at the application layer (even
  though the trigger still enforces).
- Remove C1 (append-only) → audit history is mutable; non-
  repudiation collapses; every other constraint's enforcement
  becomes retroactively deniable.
- Remove C9 (real-threading tests) → concurrency arguments are
  unverified; production failures will reveal them eventually,
  expensively.

The point: this isn't a list. It's a graph. Removing any node
ripples through the others.

---

## Complement pairs (across tiers)

The structural insight that gives the lattice its leverage is
that every EXPAND constraint has a CONTRACT complement on the
opposite pillar at the same tier. When you change one, check the
other.

- **Tier 1**: C7 (EXPAND: algorithm flexibility) ↔ C2 (CONTRACT:
  ZK leakage forbidden)
- **Tier 2**: C5 (EXPAND: same-origin scripts allowed) ↔ C4
  (CONTRACT: atomic counter blocks brute force)
- **Tier 3**: C8 (EXPAND: bounded result sets, system endures) ↔
  C6 (CONTRACT: client cannot upgrade disclosure)

If you loosen C5 (allow more script sources), you almost certainly
need to strengthen C4 (or related defenses) or the loosening turns
catastrophic. The complement is the early-warning system.

---

## How this gets used

`scripts/ai-coherence.sh` checks the lattice mapping holds:

- All 10 nodes have a corresponding constraint
- All 10 constraints have a corresponding node
- The meta-slot is acknowledged as unfilled (or has a documented
  reason it was filled)
- Adding C11 requires updating this document

`scripts/ai-lattice.sh <constraint>` walks the lattice from any
node, surfacing its neighbors, complement, and dependency
cascade. Use this when you're about to change a constraint and
want to know what else might need to move.

`scripts/ai-status.sh` reports the lattice position when listing
constraints, so each C-N is named with its position — giving the
reader an immediate sense of WHY that constraint is structurally
important.

`scripts/ai-loop-check.sh` flags any session where the mapping
was changed without updating both this file AND `MISSION.md`.
The two must stay in sync.

---

## Adding C11 (or beyond)

If a future audit finds a missing constraint, the addition process:

1. Justify why the constraint is needed (what threat does it
   address, what test would fail without it?).
2. Map the new constraint to a lattice position. Either:
   - Reserved meta-slot — and document why it's the integrative
     meta-constraint
   - Replace an existing constraint's position if the new one fits
     better (rare; requires re-justifying the old one's location)
   - Extend BEYOND the 10-node lattice — and document what new
     topology supplements it (the lattice has 10 nodes; if you
     need 12, you've moved to a different framework, and that
     needs justification).
3. Update both this document and `MISSION.md`.
4. The lattice mapping is now the test that the addition was
   justified, not arbitrary.

This is the protection against drift. C1-C10 close because the
lattice closes. Closing-then-extending is a deliberate act, not
an accidental drift.
