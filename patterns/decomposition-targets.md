# patterns/decomposition-targets.md

## Trigger

- Decomposing a problem, feature, or document into parts
- "How many sections should this have?"
- "Is this list complete?"
- "Am I over- or under-fragmenting?"

## The recipe

Default to one of three target counts based on depth: **3**
(essential), **7** (adequate), **12** (exhaustive). Decompositions
outside these sweet spots tend to either lose detail (≤2) or
fragment (8–11, 13+).

The triple is empirically supported by working-memory bounds
(Miller's 7±2) and structurally cross-validated by independent
taxonomies that converge on the same counts (3-fold dialectics,
7-fold checklists, 12-fold complete classifications). Both
readings give the same answer; that's the test of a load-bearing
target count.

### When to pick 3

- The problem has an essential triadic shape (cause / effect /
  feedback; thesis / antithesis / synthesis; risk LOW / MEDIUM /
  HIGH)
- Quick-reference: an executive summary, a tagline, a 3-bullet
  status update
- Forced choice: when more than 3 options paralyzes the reader

Example in Polaris:
- Risk classes: LOW / MEDIUM / HIGH (`meta/autonomy-architecture.md`)
- Disclosure levels: ZERO_KNOWLEDGE / SELECTIVE / FULL
- Document priority weights: high / medium / low

### When to pick 7

- Working-memory checklist a human will hold in mind during work
- The structure has natural seven-fold shape (cross-layer principles,
  STRIDE-minus-one, days of the week)
- Detailed-but-scannable: each item gets ~2–4 sentences

Example in Polaris:
- DEVNOTES section count target (max 7 per file before split)
- Cross-layer principles checklist in `ai-coherence.sh`
- Patterns/ minimum size (7 to be a discoverable set)

### When to pick 12

- Exhaustive-and-still-bounded: month-by-month cadence,
  comprehensive classification, function-type taxonomy
- Reference taxonomy where you'd otherwise sprawl to 30+
- The structure has natural 12-fold shape

Example use elsewhere:
- Calendar months as a planning cadence
- Personality typologies (Jungian function-types)
- 12-step recovery taxonomy

Polaris doesn't currently use 12 anywhere; if a future taxonomy
needs more granularity than 7, 12 is the next stop before
considering whether a smaller subset would do.

### What about 22?

22 is the next bounded count above 12. Polaris uses 22 ONCE, in
`ai-pattern.sh`, because that's the catalog size for the closed
set of software-work shapes and shrinking it would force merging
genuinely distinct patterns.

Don't reach for 22 unless the structure is a true classification
taxonomy. For a checklist, 7 is the limit; for a list, 12.

## Decomposition decision tree

```
Is the structure a checklist a human will hold in mind during work?
    YES → use 7 (working memory)
    NO  → next question

Is the structure a complete classification taxonomy?
    YES → 12 if natural, 22 if pattern-catalog scale, else 7 if possible
    NO  → next question

Does the structure have an essential triadic shape?
    YES → 3
    NO  → 7 by default
```

## When the natural count is OUTSIDE 3-7-12

Sometimes a real-world structure has 6 things, or 10. The recipe
is NOT to force them to 7 or 12 by inventing or merging. The
recipe is to ASK whether the count fits one of these patterns:

- **6:** a "missing one" situation (e.g., 6 STRIDE categories —
  note whether one was historically split off, like Information
  Disclosure splitting from Tampering).
- **8:** the 8-bit byte; sometimes a true octave. If the structure
  earns its 8, keep it.
- **10:** the constraint-lattice case. 10 is the working-memory
  upper bound where the structural argument (interdependence)
  earns its place. Polaris's C1-C10 are exactly this.

The point: don't FORCE 3-7-12. Use them as DEFAULTS to fall back
to, and use them as FLAGS when the count is far off (3 components
feels thin; 19 components feels bloated — either is a signal to
revisit).

## Pre-known gotchas

- **Lazy padding.** Adding "and other" or "miscellaneous" to hit a
  target count is a tell that the decomposition is wrong. The
  miscellaneous bucket means you stopped thinking too early.

- **Forced merging.** If you have 8 distinct things and merge two
  to get to 7, you've lost information. Either accept 8, find a
  TRULY-redundant pair (rare), or split the structure into two
  views (e.g., 7 + 1 footnote).

- **Convenient naming.** Calling something "the seven pillars"
  doesn't make seven the right count. The number must be empirical
  (working memory) AND structurally cross-validated (recurring in
  independent taxonomies) for the doubled justification.

- **Confusing checklists with taxonomies.** A checklist is items
  you go through; cap at 7. A taxonomy is a classification you
  refer to; can be 12, 22, or more.

## Pre-flight check

Before publishing a decomposition, ask:

1. **Does the count match the structural shape?** (Checklist → 7;
   classification → 12 or 22; essential → 3)

2. **If NOT in {3, 7, 12, 22}: is the count empirically justified?**
   ("There are exactly 10 mission constraints because the lattice
   topology requires 10 nodes" counts; "there are 9 because it's
   a nice number" doesn't.)

3. **Could a smaller decomposition capture the same structure?**
   If 12 components could be 7 with no loss, prefer 7.

4. **Is the structure interdependent (like the C1-C10 lattice) or
   independent (like a checklist)?** Interdependent decompositions
   close at their natural count; checklists are flexible.

## Completion check

- [ ] Count is one of {3, 7, 12} OR has documented empirical/
      structural justification for being outside
- [ ] No "miscellaneous" or "other" buckets that hide thinking gaps
- [ ] No forced merges that lose distinct items
- [ ] If checklist: ≤ 7 (working memory)
- [ ] If classification: ≤ 22 (discoverability)
- [ ] If essential: 3
- [ ] If extending an existing decomposition, the existing count's
      justification still holds
