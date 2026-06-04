# meta/lineage.md

Appendix. Where each structural insight in Polaris's structural
layer is drawn from. Kept separate from the operational docs so
they can stay focused on what the layer DOES, not where the
analogies came from.

This file is for the curious. Reading it is optional. The
operational docs (`meta/structural-architecture.md`,
`meta/constraint-lattice.md`) do not reference it.

The point of recording lineage: when a future reader asks "why
these specific shapes? where did the 10-node lattice come from?"
the answer is here, not implicit in the names.

---

## The 10-node constraint lattice

**Drawn from:** the Kabbalistic *Tree of Life*, a 10-node graph
arranged in three columns and four tiers, used in Hebrew
mysticism to model emanation from the divine into the manifest
world.

**What survived in Polaris:**
- The fixed 10-node count (closure as a forcing function)
- The three-pillar structure (expansion, contraction, balance,
  originally "Mercy / Severity / Equilibrium")
- The dependency cascade across nodes (removing one node breaks
  the others, originally the doctrine that emanations depend on
  upstream emanations)

**What didn't:**
- The Hebrew names (Keter / Chokmah / Binah / Chesed / Gevurah /
  Tiferet / Netzach / Hod / Yesod / Malkuth), replaced with
  structural position names (APEX / EXPAND·N / CONTRACT·N /
  BALANCE·N / MANIFEST)
- The theology
- Any "divine" or "sacred" framing

**Why the analogy worked:** the Sefirot encode the structural
claim that a small set of categories can be COMPLETE,
INTERDEPENDENT, and BALANCED across opposites. Engineering needs
exactly this for hard constraints: the C1-C10 set must close
(no ad-hoc additions), must depend on each other (so removing
one cascades), and must balance permissive against restrictive
forces (expansion needs contraction to remain safe).

---

## The 22-pattern catalog

**Drawn from:** the *Major Arcana* of the Tarot, a 22-card
sequence representing recurring human-scale situations
(beginnings, choices, hidden information, breakdowns, renewals).

**What survived in Polaris:**
- The closed 22-pattern count
- The per-pattern *shadow* (predicted failure mode), originally
  the Tarot's "reversed meaning"
- The per-pattern *complement* (inverse re-frame), originally
  Tarot card pairings
- The structural insight that recurring shapes have characteristic
  failure modes that are obvious in retrospect but missed when
  focused on the happy path

**What didn't:**
- The card names (Fool, Magician, High Priestess, etc.),
  replaced with engineering pattern names (Greenfield,
  Composition, HiddenState, etc.)
- Imagery, divination, suit symbolism

**Why the analogy worked:** 22 is empirically the right size for
a catalog of software-work shapes. Smaller taxonomies over-
generalize; larger ones fragment. And the Tarot's reversed-
meaning convention is exactly the *shadow* concept that gives
the catalog its predictive power: knowing a shape primes you
for its characteristic failure.

---

## The Fibonacci priority weights

**Drawn from:** Fibonacci's sequence (1, 2, 3, 5, 8, 13, …)
and its asymptotic limit φ ≈ 1.618 (the golden ratio).

**What survived:** the weighting itself. Used directly in
`scripts/ai-propose.sh`.

**What didn't:** anything mystical. The Fibonacci sequence is
already standard in agile story-point estimation (Fibonacci is
the canonical "planning poker" scale) because the geometric
growth captures combinatorial cost-scaling better than linear
estimation. No translation needed; this is engineering vocabulary
already.

---

## The 7-element chunking target

**Drawn from:** Miller (1956), "The Magical Number Seven, Plus or
Minus Two." Working-memory psychology.

**What survived:** the number 7 as an upper bound for sections
in a doc the reader must hold in mind.

**What didn't:** anything else. Miller's law is engineering
vocabulary already.

---

## The 7 cross-layer principles

**Drawn from:** the *Kybalion* (1908) and Hermetic philosophy.

**What survived:**
- The use of "Correspondence" (one layer reflects another) as the
  primary structural-consistency check
- A catalog of 7 cross-layer concerns

**What didn't:**
- The original Hermetic names (Mentalism / Correspondence /
  Vibration / Polarity / Rhythm / Cause-Effect / Gender),
  replaced with structural names (Intent / Correspondence /
  Symmetry / Polarity / Cadence / CauseEffect / Duality)
- Any metaphysical claims

**Why the analogy worked:** the Hermetic principle of
correspondence, "as above, so below", is precisely the rule
that a constraint at one layer (schema CHECK) should be reflected
at the layers that depend on it (API validation, UI form,
documentation). It's a useful catalog of layer-consistency
concerns regardless of the framework's origin.

---

## The 3 / 7 / 12 decomposition targets

**Drawn from:** various traditions where 3, 7, and 12 recur:
- Trinity (3-fold structure ubiquitous in folklore)
- Seven (chakras, Hermetic principles, deadly sins, days of
  creation, weekly cycle)
- Twelve (zodiac, calendar months, twelve disciples, Jungian
  function-types)

**What survived:** the three target counts as decomposition
defaults, used in `patterns/decomposition-targets.md`.

**What didn't:** the traditional readings. The empirical
justification (Miller's law at 7, "essential" at 3, "exhaustive
but bounded" at 12) does all the work.

---

## Why keep the lineage at all?

Two reasons:

1. **Reproducibility.** If a future agent ever needs to rebuild
   the structural layer from scratch, knowing where the
   inspirations came from makes it easier to evaluate which
   ones to keep, modify, or drop.
2. **Honesty.** The structural insights *were* drawn from older
   frameworks. Pretending otherwise, claiming the lattice was
   designed from first principles, would be a different kind
   of intellectual dishonesty. The frameworks survived because
   they encoded real structure; recognizing that lineage isn't
   weakness, it's accurate attribution.

The operational docs don't reference this file because they
don't need to. The structural insights stand on their Removable
Test (do they impose a testable constraint?), not on their
lineage.

---

## What to read instead

- `meta/structural-architecture.md`: the operational philosophy
- `meta/constraint-lattice.md`: the C1-C10 mapping
- `MISSION.md`: the C1-C10 constitution, the canonical constraints
- `patterns/decomposition-targets.md`: the 3/7/12 recipe
