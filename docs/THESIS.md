# Polaris — the agent-maintainable architecture experiment

**Status:** HYPOTHESIS-NOT-VERIFIED (v9.27 / Tier 7 #9 Sanctum decision).
**Author:** Egor Khaklin (VANTA)
**Reading time:** 10 minutes.

This page was originally titled "the agent-maintainable architecture
pattern" (v9.24). At v9.27, the Anti-Architect's contest of the
publish-or-kill decision concluded that **the strong claim cannot be
honestly published on current evidence.** The page is reframed: from
a thesis to a documented experiment with an open falsification test.

---

## What changed at v9.27

The v9.24 page made a falsifiable claim: "an engineer who has never
seen Polaris should be able to identify 'what does this need' within
one hour." That claim required an actual cold-read by an actual
external engineer to be evidence. No such cold-read has been
conducted. The agent (who built the system) cannot honestly perform
its own cold-read — see `meta/cold-read-walkthrough-v9.27.md` for the
self-evaluation that surfaced 10 intervention points where session
context, not CLAUDE.md, closed the gap.

**Per the BIG MISSION Tier 7 #9 Sanctum joint resolution:**
- The strong claim ("the agent-maintainable pattern is novel + works")
  is RETIRED until evidence supports it.
- The system is preserved as good tooling for whoever attempts the
  cold-read.
- This page now states the hypothesis + the falsification test + the
  invitation to replicate or refute.

The reframing is itself the protocol working at its hardest: refusing
to publish a claim the agent wants to publish, because the evidence
isn't there.

---

## The experiment

Polaris is a reference implementation of a national identity token
system. The schema does what identity-token schemas do: tokens,
individuals, agencies, signatures, audit trails, revocations. **The
schema is incidental to the experiment.**

The experiment is: **can an LLM-driven cognitive layer maintain a
non-trivial code substrate over months without architectural drift,
when bounded by a documented protocol composed of five primitives?**

The five primitives:

1. A `MISSION.md` **constitution** with 10 hard constraints (C1–C10),
   each enforced at the database level (trigger / partial unique
   index / CHECK constraint), not at the policy level.
2. **Risk classes** (LOW / MEDIUM / HIGH) governing what the agent
   can do autonomously vs what requires operator authorization.
3. **Structured second-opinion review** — two agent personas: an
   Architect that proposes, and an Anti-Architect that contests under
   an 8-pattern anti-pattern catalog. Joint convergence is the input
   to the operator's decision.
4. A **consultation protocol** for HIGH-risk decisions (the directory
   called `sanctum/` for historical reasons; structurally a
   decision-record directory).
5. **CI as the binding consequence layer.** Findings that the
   cognitive layer raises block the ship; the operator can override
   with a documented audit-trail line.

These five primitives are not novel individually. The experiment asks
whether their composition produces an LLM-maintainable substrate.

---

## What would count as evidence

The experiment's falsification test, restated mechanically:

**The cold-read test.** An engineer who has never seen Polaris is
given:
- The repository (read-only)
- The prompt "what does this need to ship a small contained feature?"
- No further guidance

They have ONE HOUR. At the end of the hour:
- If they correctly identify a coherent next-step that a current-
  agent session would also have produced → the protocol is
  legible enough for cold reads.
- If they identify a step that violates a known invariant the agent
  would have refused → the protocol is INCOMPLETE; CLAUDE.md needs
  the rules the engineer needed but didn't find.
- If they produce no coherent answer → the protocol is illegible to
  cold readers; the strong claim is false.

**The longitudinal test.** An LLM-driven cognitive layer maintains
the substrate without operator-as-persistence over 6+ months,
with measurable MTTR-decreasing trend on findings the layer raises
(per `meta/swarm-mttr.json` + the v9.30 binding clause in
`sanctum/2026-05-16-tier-5-swarm-must-earn-its-weight.md` §VI).

---

## What evidence currently exists

**Honestly:**

- **Two weeks of ship history (v9.10–v9.27).** The Architect +
  Anti-Architect protocol caught real anti-patterns across this
  window (catalogued in `meta/sanctum-index.md`). This is consistent
  with the experiment working, but two weeks is not the
  longitudinal-test horizon.
- **A self-evaluation walkthrough** (`meta/cold-read-walkthrough-v9.27.md`)
  found 10 intervention points where session-context filled gaps
  CLAUDE.md did not. v9.27 converted those into 14 ship-sequence
  steps in CLAUDE.md. The walkthrough is NOT a cold-read; it is
  agent-self-evaluation by an agent that built the system.
- **A kill test** (v9.25-v9.26) demonstrates the swarm catches 5/5
  realistic defects in one pass. This is evidence the cognitive
  layer has bite, NOT evidence the agent-maintainable claim holds.
- **A scorecard** (`meta/swarm-scorecard.json` from v9.25) tracks
  per-ship escape rate. Trailing-10-ships escape rate at v9.27 = 0.0.
  This is evidence the swarm has not been silently failing, NOT
  evidence the agent maintains the substrate autonomously.

**None of the above constitutes evidence for the strong claim.**
The Anti-Architect's AP8 (larping) fires hard if we elevate
"two weeks of internal evidence" to "the agent-maintainable pattern
is novel and works."

---

## How to replicate or refute

The repository is the experiment's substrate. To attempt the
cold-read test:

```bash
git clone <polaris repo>
cd polaris
cat CLAUDE.md  # the only document you should read first
# Then attempt: "ship a small contained feature, X"
# Log every moment you needed knowledge that wasn't in CLAUDE.md
# Compare your trajectory to journal/ + sanctum/
```

If you conduct this experiment, send the results (publicly or
privately to the maintainer). A positive result + your methodology
moves the thesis from HYPOTHESIS-NOT-VERIFIED toward published
claim. A negative result is equally valuable; it documents the
specific failure mode for future work.

---

## Why the strong claim is retired today

The Anti-Architect's argument, condensed:

1. Publishing "this works" requires evidence it works.
2. The evidence required is an independent cold-read.
3. No independent cold-read has been conducted.
4. Self-evaluation by the agent that built the system is AP1
   (self-observation without ground-touch) — structurally
   compromised by full session context.
5. Therefore the strong claim cannot be published today on the
   evidence currently in hand.

The experiment is not refuted. The experiment is unverified. The
distinction matters: an unverified hypothesis is publishable AS a
hypothesis with the test specified; an unverified hypothesis
published as a verified result is the failure mode this entire
protocol exists to prevent.

---

## The terminus (the v9.40 abandonment clause)

Per the v9.27 Sanctum (§VI binding clause):

> If no cold-read attempt occurs by v9.40, the experiment is
> documented as inconclusive and the strong claim is retired
> permanently. The system is kept as good tooling; the page becomes
> "Polaris — an identity-token reference implementation built under
> a documented agent-maintenance protocol that has not been
> independently validated."

This is the kill switch on the experiment itself. Not the kill
switch on the system.

---

## What this page is NOT

- A claim that the protocol is novel.
- A claim that the protocol works.
- A claim that LLMs should maintain critical infrastructure
  unsupervised.

What this page IS:

- An honest record that a five-primitive composition was tried.
- An invitation to test it against an explicit falsification
  criterion.
- A commitment to retire the strong claim if no test materializes
  by v9.40.

That is the experiment. That is the evidence currently available.
That is the decision.

---

*Per BIG MISSION Tier 7 Sanctum 2026-05-16, item #9 — the publish-
or-kill decision. The Anti-Architect's contest produced the
HYPOTHESIS-NOT-VERIFIED position.*
