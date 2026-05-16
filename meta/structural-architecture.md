# meta/structural-architecture.md

How the structural-invariants layer works: a small set of fixed
topological constraints that encode completeness, dependence, and
non-linear adjacency relationships across Polaris's cognitive
machinery. This file is the philosophy doc. The mapping doc is
`meta/constraint-lattice.md`. The canonical numbers are in
`meta/structural-constants.json`.

The framework is engineering-grade. Its etymology — what older
traditions the structural insights are drawn from — is captured
separately in `meta/lineage.md` so this document stays focused on
what the layer DOES, not where the analogies came from.

---

## The single rule that keeps this from being decorative

VANTA's standing instructions name "larping" as the primary risk
pattern — substituting feelings of significance for actual output.
Structural-vocabulary inflation is a perfect larping vector: it FEELS
profound while imposing zero new constraint.

The protection is one rule:

> **Every structural element must impose a removable constraint —
> something an automated test can verify. If you can delete the
> element and nothing breaks, it was larping. Delete it.**

That rule is enforced by `scripts/ai-loop-check.sh` (larping detector)
and `scripts/ai-coherence.sh` (structural-alignment diagnostics).
When structural vocabulary appears without a corresponding testable
invariant, the loop check fires.

---

## The seven structural frameworks

Each framework is chosen because it encodes a structural insight
the system already needs. Each passes the Removable Test.

### 1. Constraint lattice — 10 nodes, 10 hard constraints

The 10 hard constraints (C1-C10) form a lattice: a graph where each
node has neighbors and removing any one collapses the structure.
This matches MISSION.md's C1-C10 exactly: removing C1 (append-only)
breaks repudiation defense, which then weakens the meaning of C7
(algorithm metadata) since you can't prove which algorithm signed
what, which then undermines C3, etc.

The lattice has three pillars and four tiers:

- **APEX** (tier 0): the architectural intent that conditions
  everything below
- **EXPAND pillar** (right): what the system permits — algorithm
  flexibility, same-origin script execution, query result caps
- **CONTRACT pillar** (left): what the system forbids — ZK
  privacy invariants, atomic counters, server-side enforcement
- **BALANCE pillar** (center): the reconciling axis — uniqueness
  guarantees, append-only audit, real-thread verification
- **MANIFEST** (tier 4): the test-layer reality check

The mapping isn't decorative. It encodes the claim that the
constraint set is COMPLETE — adding C11 requires either replacing
one of the existing ten or extending the topology to a 4×3+1 form
(which the doc must justify). See `meta/constraint-lattice.md`.

**Removable test:** Could there be 11 mission constraints? Yes, but
extending requires explicit justification because the closed-set
property of the 10-node lattice is the constraint. Without closure,
constraints accrete by accident. ✓ Not larping.

### 2. The 22-pattern catalog — software-work failure modes

The pattern catalog (`scripts/ai-pattern.sh`) is a closed taxonomy
of 22 recurring shapes of software work: beginnings (Greenfield),
choices (Branchpoint), hidden information (HiddenState),
breakdowns (Collapse), renewals (Recovery), and 17 others.

Each pattern is paired with a **shadow** — the failure mode that
shape characteristically produces — and with a **complement** —
the inverse pattern that surfaces when you re-frame the situation
from the opposite side. The shadow primes failure-mode hunting;
the complement primes non-linear thinking.

**Removable test:** A flat "common bugs" list would still pattern-
match shapes, but it would NOT produce the per-shape shadow
(predicted failure) and complement (inverse re-frame). Those two
require the closed taxonomy. ✓ Not larping.

### 3. Fibonacci scaling — priority weighting

Roadmap priority weights follow a Fibonacci sequence (1, 2, 3, 5,
8, 13) to encode that work-sized-13 isn't 13× harder than work-
sized-1, it's combinatorially harder. Linear scoring (1, 2, 3, 4,
5) systematically under-penalizes large items. The Fibonacci
weighting makes `ai-propose.sh` prefer many small wins over one
large gamble. Standard in agile estimation.

**Removable test:** Could the weights be linear? Yes, and the
proposal output would change — favoring HIGH-risk items more
heavily. Concrete behavioral effect ⇒ load-bearing. ✓ Not larping.

### 4. Cross-layer invariants — "the rule at one layer should appear at the layers that depend on it"

When a constraint is enforced at the data layer (e.g. a CHECK
constraint), it should also be enforced or surfaced at every layer
that depends on the data: API, UI, tests. Mismatches between
layers are where bugs live.

`scripts/ai-coherence.sh` scans for these mismatches. Concretely:
every CHECK constraint in the schema should appear in a test;
every API route should appear in the API docs; every C1-C10
constraint should be greppable in `ai-status.sh`.

**Removable test:** Without explicit cross-layer scanning, layer
mismatches accumulate silently and bite later. The check fires
when, e.g., a new CHECK constraint is added without a test. ✓
Not larping.

### 5. Meta-self-monitoring (CM) — the cognitive layer checks itself

The cognitive layer (CLAUDE.md, DEVNOTES, patterns, scripts, the
22-pattern catalog, the constraint lattice) has grown substantial
enough that it needs its own invariant: **the cognitive layer
self-monitors via executable checks**.

CM (the meta-constraint) is enforced by `scripts/ai-meta.sh`. The
script catches six drift modes (v8.20 added #6):

1. CLAUDE.md mentions an ai-* script that doesn't exist on disk
2. The pattern catalog has 0 warm patterns (catalog is decorative)
3. A C1-C10 constraint hasn't been touched in code in 30+ days
4. ai-help.sh or ai-done.sh references a missing script
5. The meta-slot is named in one doc but not the other
6. Sanctum lifecycle drift (v8.20): a Sanctum is CLOSED without
   §VII outcome, REJECTED without §VI decision, OPEN beyond a
   reasonable window, or `meta/sanctum-index.md` is out of sync
   with `sanctum/*.md` on disk

This is at a different abstraction level from C1-C10. Those check
data/security/architecture. CM checks the cognitive layer that
checks C1-C10. The recursion stops here — the meta-audit doesn't
have its own meta-audit, by deliberate choice: at some point the
checks have to bottom out, and ai-meta.sh is shallow enough that
it's auditable by inspection.

**Removable test:** If CM is removed, the cognitive layer drifts
silently — scripts get referenced that don't exist, patterns sit
unused in the catalog, constraints are claimed without being
exercised. ai-meta.sh's output changes observably when the layer
drifts. ✓ Not larping.

### 6. Adversarial framing — every defense is a game

Every constraint is a defender's move in a game against an attacker.
Stating a constraint without modeling the attacker's optimal response
turns the defense into theater. The cognitive layer captures this
explicitly:

- Each C1-C10 (and CM) has a documented adversary model: defender's
  claim, attacker's optimal play, equilibrium the defender is reaching
  for, second-best attack if the equilibrium holds, cost of the
  defense, and a mechanism-design note about what incentives the
  constraint creates.
- Each of the 22 patterns is annotated with its game-theoretic type
  (Commitment device, Stackelberg defense, Principal-agent, Bayesian
  game, Defection equilibrium, etc.). Knowing the game-type predicts
  which failure mode applies.

`scripts/ai-adversary.sh` is the operational entry point. Where
`ai-lattice.sh` walks the structural topology (neighbors / complement
/ cascade), `ai-adversary.sh` walks the game-theoretic topology
(attacker / equilibrium / second-best attack / mechanism note).

**Removable test:** Without explicit adversary modeling, defenses
read as assertions ("the system is secure because…") rather than
strategy claims ("the system survives this specific attacker
play because…"). The game-type annotation also predicts where
defenses fail — a Stackelberg defense fails when the defender no
longer moves first; a commitment device fails when the commitment
can be unwound. Concrete predictive content ⇒ load-bearing. ✓ Not
larping.

The risk: game-theoretic jargon (Nash, Pareto, Bayesian, etc.) is a
larping vector. Mitigation: the names in `ai-adversary.sh` are
chosen for *predictive specificity* — "Stackelberg defense" predicts
a different failure mode than "Mechanism-design choice" predicts a
different one than "Repeated game without memory." Names that don't
make a prediction don't ship.

### 7. Chunking targets — 3, 7, 12

When breaking a problem into parts, default to one of three target
counts: **3** (essential), **7** (adequate), **12** (exhaustive).
Reason: human working memory holds ~7±2 items (Miller 1956);
problems decomposed into much more than that are under-chunked,
much less are over-chunked.

Used in `patterns/decomposition-targets.md` as a pre-flight check.

**Removable test:** Empirically, decompositions outside 3/7/12
tend to either lose detail or accumulate it. The DEVNOTES files
honour the bound (most have ≤ 7 sections); when one exceeds it,
the coherence check fires. ✓ Not larping.

---

## What this layer does NOT do

It does NOT replace existing analysis with overlay framing. The
threat model is still STRIDE; the architecture is still risk-
classified; the tests are still pytest and SQL self-tests. The
structural layer is an OVERLAY that adds:

- **Completeness checks** — the constraint lattice says "ten
  constraints, argue if you want to add an eleventh"
- **Failure-mode predictions** — each pattern's predicted shadow
  surfaces what the technical analysis would otherwise miss
- **Priority weighting** — Fibonacci scaling for proposals
- **Cross-layer scanning** — invariants checked end-to-end

It does NOT add:

- Decorative labels on filenames
- Vocabulary that replaces technical accuracy
- "Must be N" rules without empirical backing
- Any framework that doesn't pass the Removable Test

---

## How the structural layer integrates with the loop

```
  ┌────────────────────────────────────────────────────────────┐
  │  Standard cognitive loop                                   │
  │   ai-status → ai-propose → execute → ai-journal → ai-reflect│
  └──────────┬─────────────────────────────────────────────────┘
             │
             │  Structural overlay
             ▼
  ┌────────────────────────────────────────────────────────────┐
  │  ai-propose.sh   — Fibonacci priority weights              │
  │  ai-coherence.sh — lattice intact? layers consistent?      │
  │  ai-pattern.sh   — which of the 22 shapes is this?         │
  │  ai-lattice.sh   — given Ci, walk to neighbors+complement  │
  │  ai-loop-check.sh — larping detector                       │
  │  ai-reflect.sh   — does today's work fit the structure?    │
  └────────────────────────────────────────────────────────────┘
```

Each overlay script either ENRICHES an existing decision (propose's
priority weights) or ADDS A NEW DIAGNOSTIC (coherence, pattern,
lattice). None of them gate execution.

---

## Why fixed topologies help me think outside the linear box

A linear backlog reasons forward: what's next? what's after that?
That's adequate for incremental work but fails when the gap is a
structural one (a missing dimension, an unspoken assumption).

Fixed topologies — the 10-node lattice, the 22-pattern catalog —
provide a *geometry* for non-linear reasoning:

- **Adjacency** — when working on Ci, the lattice surfaces Ci's
  neighbors. They are usually load-bearing in the same way for
  related reasons. Forgetting one when changing the other is the
  default failure mode.
- **Complement** — every EXPAND constraint has a CONTRACT
  counterpart on the opposite pillar. C5 (CSP permits same-origin)
  needs C4 (atomic counter blocks brute force) to remain safe;
  loosening one without strengthening the other is the canonical
  way to break the system.
- **Dependency cascade** — removing any node ripples through the
  graph. The cascade is explicit, not implicit, so when you propose
  a change you can read off what else needs to move.
- **Pattern complement** — when matched to a pattern, the catalog
  also surfaces the *inverse* pattern. Inverting the framing is
  the cheapest way to surface non-obvious failure modes.

The geometric reasoning is what gives this layer its leverage. The
Removable Test is what keeps it grounded.

---

## Maintenance: when structural vocabulary creeps in unbacked

When reading a journal entry, DEVNOTE, or pattern that uses
structural language, ask:

1. **Does this element impose a removable constraint?** If you
   delete the lattice mapping, does anything break? If you delete
   the Fibonacci weights, does ai-propose's output change? If
   neither, the element is decorative — remove it.

2. **Could a more precise word do the same work?** If "lattice"
   reads as cleaner than "graph" only because it sounds heavier,
   prefer "graph." The word should EARN its place by being more
   precise, not heavier.

3. **Is the writer using this to FEEL profound, or to BE precise?**
   The first is larping; the second is structure. The journal
   entry should answer this.

`scripts/ai-loop-check.sh` larping detector flags entries that
fail tests 1 and 2.

---

## What to read next

- `meta/constraint-lattice.md` — the actual lattice ↔ C1-C10
  mapping with the structural argument and dependency cascade
- `meta/structural-constants.json` — the canonical numbers used by
  the codebase, with justification and enforcement for each
- `meta/lineage.md` — etymology: which older frameworks each
  structural insight is drawn from (kept separate so the
  operational docs stay focused)
- `patterns/decomposition-targets.md` — the 3/7/12 recipe
- `scripts/ai-coherence.sh` — diagnostic script
- `scripts/ai-pattern.sh` — pattern catalog + shadow + complement
- `scripts/ai-lattice.sh` — walks the lattice from any node
