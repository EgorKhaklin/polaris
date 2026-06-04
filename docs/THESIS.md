# Polaris — identity cannot outrun its primitives

**Status:** HYPOTHESIS-NOT-VERIFIED.
**Author:** Egor Khaklin (VANTA)
**Reading time:** 8 minutes.

This page states the thesis behind Polaris, the test that would confirm
or refute it, and an honest account of the evidence currently in hand.
It is a documented experiment with an open falsification test, not a
victory lap.

---

## The thesis

A national identity-token system is only as trustworthy as the
primitives underneath it. Policy promises ("we will not aggregate," "we
will not retain forever," "we will enforce one identity per person") are
worthless if the only thing holding them up is policy. They have to be
enforced where they cannot be talked around: in the schema, in the
triggers, in the partial unique indexes, in the CHECK constraints.

Polaris is the claim made concrete. The ten constitutional invariants
(C1-C10 in `MISSION.md`) are each enforced at the database level, not
the policy level. The Vocation (anti-coercion) sits above them: changes
toward surveillance, centralized aggregation, or unbounded retention are
refused on sight. The schema does what identity-token schemas do
(tokens, individuals, agencies, signatures, audit trails, revocations),
but the security boundary is the database, and the invariants are
machine-checked by `polaris_checks/` before any change ships.

The strong form of the thesis: **a reference implementation can make its
own constraints legible enough that a stranger can read the repository
and correctly infer what it needs.** If the primitives are honest, the
system explains itself. That is the claim this page does not yet get to
publish as proven.

---

## What would count as evidence

**The cold-read test.** An engineer who has never seen Polaris is given:

- The repository (read-only)
- The prompt "what does this need to ship a small contained feature?"
- No further guidance

They have ONE HOUR. At the end of the hour:

- If they correctly identify a coherent next step that the maintainer
  would also have produced, the repository is legible enough for cold
  reads.
- If they identify a step that violates a known invariant the maintainer
  would have refused, the documentation is INCOMPLETE; `CLAUDE.md` and
  `MISSION.md` need the rules the engineer needed but did not find.
- If they produce no coherent answer, the repository is illegible to
  cold readers and the strong claim is false.

This is the falsification test. It requires an actual cold read by an
actual external engineer to count as evidence. No such cold read has
been conducted, which is why the status above is
HYPOTHESIS-NOT-VERIFIED.

---

## What evidence currently exists

Honestly, the standing evidence is internal and limited:

- **The invariants are enforced where it matters.** C1-C10 live in the
  schema and triggers (`polaris_sql/`), and `polaris_checks/` gates CI
  on them with tested detection correctness. This is evidence that the
  primitives are real, not that a stranger can read them cold.
- **A self-evaluation walkthrough** found intervention points where
  session context filled gaps the docs did not. A walkthrough by the
  person who built the system is not a cold read; it is self-evaluation
  by someone who already has full context. It can only surface
  candidate gaps, never prove legibility.

None of the above constitutes evidence for the strong claim. Elevating
"internal review by the author" to "a stranger can read this cold and
get it right" is exactly the inference this page refuses to make.

---

## How to replicate or refute

The repository is the experiment's substrate. To attempt the cold-read
test:

```bash
git clone <polaris repo>
cd polaris
cat CLAUDE.md  # the document you should read first
# Then attempt: "ship a small contained feature, X"
# Log every moment you needed knowledge that wasn't in the docs
# Compare your trajectory to journal/ + sanctum/
```

If you conduct this experiment, send the results (publicly or privately
to the maintainer). A positive result plus your methodology moves the
thesis from HYPOTHESIS-NOT-VERIFIED toward a published claim. A negative
result is equally valuable: it documents the specific failure mode for
future work.

---

## Why the strong claim is not published

The argument against publishing "this works," condensed:

1. Publishing "this works" requires evidence it works.
2. The evidence required is an independent cold read.
3. No independent cold read has been conducted.
4. Self-evaluation by the author is structurally compromised by full
   context; it cannot stand in for the test.
5. Therefore the strong claim cannot be published today on the evidence
   currently in hand.

The thesis is not refuted. It is unverified. The distinction matters: an
unverified hypothesis is publishable AS a hypothesis with the test
specified; an unverified hypothesis published as a verified result is
the failure mode this whole project exists to avoid.

---

## What this page is NOT

- A claim that the system has been independently validated.
- A claim that reading the repository cold is proven to work.
- A claim that the schema is novel.

What this page IS:

- An honest statement that identity has to be enforced at its
  primitives, and that Polaris tries to do exactly that.
- An invitation to test the repository's legibility against an explicit
  falsification criterion.
- A commitment to keep the status honest until a real cold read happens.

That is the thesis. That is the evidence currently available. That is
the decision.
