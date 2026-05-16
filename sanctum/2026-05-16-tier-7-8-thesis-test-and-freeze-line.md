# Sanctum — Tier 7 + 8: thesis test, publish-or-kill, freeze line (the terminus)

**Status:** DECIDED + SHIPPED 2026-05-16 — Position JOINT-MODIFIED (ship 6 items; thesis publish-or-kill resolved as **HYPOTHESIS-NOT-VERIFIED — keep system as tooling**, per Anti-Architect's evidence-not-attachment refusal; def-of-done committed as mechanical not aspirational). Authorized by VANTA in-chat 2026-05-16.

**Date opened:** 2026-05-16
**Date decided:** 2026-05-16
**Date shipped:** 2026-05-16 (v9.27)
**Lifecycle:** OPEN → DECIDING → DECIDED → SHIPPED
**Risk class:** HIGH (composite — touches the thesis claim itself; #12 is the freeze line; the four anti-pattern axes the Anti-Architect catalogs all converge here)
**Pattern #20 Constitutional Discipline:** 21st instance (the final BIG MISSION ship)
**Authorization:** "Tier 7 — test the agent-maintainable thesis for real, because this is the only part that might be novel. ... Item 12 is the real terminus." — VANTA, in-chat 2026-05-16

---

## §I. The Critique (VANTA's framing, condensed)

> Tier 7 — test the agent-maintainable thesis for real.
>
> 7. Run one development cycle where you are not the persistence layer.
> 8. Convert each intervention into a runbook rule or ant predicate.
> 9. Publish or kill the thesis on evidence, not attachment.
>
> Tier 8 — operational maturity.
>
> 10. Define and test failure modes.
> 11. Add real application observability separate from the meta-swarm.
> 12. Set a freeze line and commit it.
>
> Item 12 is the real terminus.

The unifying claim: **the thesis must survive an honest cold-read or
be retired; the operational substrate must fail safely under chaos
and be observable in production terms; and the project's scope must
be frozen so this stops being infinite.**

---

## §II. Debate (Architect ↔ Anti-Architect, per item)

### T7#7 — Cold-read cycle (am I the persistence layer?)

**Architect:** Pick a contained feature (small structural-invariant
addition). Walk through what a fresh agent reading only CLAUDE.md +
invariants would do. Log every moment where my session-context
knowledge would step in. Each intervention = a place the thesis is
false TODAY.

**Anti-Architect (sharp):** Three AP risks.

1. **AP1 (self-observation without ground-touch):** I cannot honestly
   simulate "what a fresh agent would do." I have full session
   context. Any walkthrough I write is necessarily compromised.

2. **AP8 (larping):** if I produce a walkthrough that conveniently
   says "0 interventions needed," that is the failure mode the user
   explicitly warned about — "if the cold read survived" requires an
   actual cold read, not a self-graded one.

3. **AP3 (proposal-as-self-elaboration):** the walkthrough must
   identify REAL knowledge gaps in CLAUDE.md, not just enumerate
   things CLAUDE.md already says.

**Joint resolution:** Conduct the walkthrough HONESTLY — bias toward
finding intervention points, not toward proving the thesis. Mark the
exercise EXPLICITLY as agent-self-evaluation (acknowledged limitation
of evidence). The real cold-read test requires an external party;
this exercise produces the candidate-runbook-rules a real cold-read
would otherwise need to discover the hard way.

### T7#8 — Convert interventions to rules/predicates

**Architect:** For every intervention in #7, add CLAUDE.md rule or
new predicate so the next cycle catches it. Repeat until cycle needs
zero OR accept it never will.

**Anti-Architect:** Concur. Add constraint: rules added must be
GENERIC (catch the class of drift), not defect-specific (catch the
exact instance). Defect-specific rules are AP3 — they grow without
bound and never converge.

**Joint resolution:** Each intervention from #7 maps to one CLAUDE.md
rule OR one ant predicate. Rules are class-shaped (e.g., "every new
TestWave class must use TestWaveNN_VNNN naming") not instance-shaped
(e.g., "remember to call test_foo_bar"). If a class-shaped rule can't
be written for an intervention, it goes to the "accept it never will"
list — honestly named, not buried.

### T7#9 — Publish or kill the thesis

**Architect:** Based on #7 + #8 evidence, decide publish-or-kill in
writing.

**Anti-Architect (the load-bearing contest):** Refuse publish if
evidence is anything less than "cold read by an independent party
worked." Self-graded walkthroughs (#7) and runbook-rule additions
(#8) are NOT evidence the thesis works — they are evidence the
agent can self-improve, which is a separate claim.

The honest current state:
- The protocol caught real anti-patterns across v9.10-v9.26 (a fact)
- The protocol has not been independently cold-read (a fact)
- "An LLM-driven cognitive layer evolves a code substrate over months
  without drift" requires months of evidence; we have 2 weeks
- Publishing "this works" today is AP8 (larping); publishing "here's
  an experiment, please attempt to reproduce or refute" is honest

**Joint resolution:** Position is **HYPOTHESIS-NOT-VERIFIED**. The
thesis page (docs/THESIS.md from v9.24) is REFRAMED to state the
hypothesis + the falsifiable test (the cold-read) + invite external
replication. We do NOT publish a claim that it works. We do NOT
delete the experiment. The system stays as good tooling for whoever
attempts the cold-read. **This is the kill, applied to the strong
claim, while preserving the experiment.**

### T8#10 — Chaos script: failure modes

**Architect:** chaos script injects 3 failure modes (DB unreachable
mid-recovery, ZK binary absent, epoch close interrupted) and asserts
fail-safe never open.

**Anti-Architect:** Concur. Three specifications:

1. **"Never open" is the load-bearing assertion.** The system can
   crash, refuse, time out — anything except silently succeed under
   broken substrate. Each chaos scenario tests that an attacker
   exploiting the failure mode cannot get a positive outcome.

2. **Each scenario must be repeatable.** A chaos test that depends
   on timing/race is unreliable; rewrite as deterministic.

3. **CI-runnable + ≤5 min wall budget.** Same constraint as kill
   test. Otherwise it rots.

**Joint resolution:** Ship `scripts/polaris-chaos-test.sh` + 3
scenarios (db_unreachable_mid_recovery, zk_binary_absent,
epoch_close_interrupted). Each: setup chaos → attempt operation →
assert REFUSAL (not silent success) → teardown. Pass bar: all 3
refuse correctly.

### T8#11 — Application observability

**Architect:** Structured logs + metrics for request rate, error
rate, auth failures, duress events. Separate from meta-swarm
(operator reads this, not the cognitive layer).

**Anti-Architect:** Refuse if no operator reads it. Three constraints:

1. **No new metrics backend.** Polaris is a reference implementation.
   Don't ship a Prometheus exporter without an operator who runs
   Prometheus. Ship structured logs to stdout (operator pipes
   wherever); document a /metrics endpoint as optional.

2. **Duress events specifically are anti-coercion-load-bearing.**
   These must be observable. If a coerced operator's duress signal
   never reaches anyone, the duress-code feature is decorative.

3. **Operator-readable, not analytics-tool-readable.** The first
   reader is a human, not Grafana.

**Joint resolution:** Ship `polaris_web/observability.py` (structured
logger + minimal metrics counter) + `/api/metrics` endpoint
(operator-readable JSON) + DEVNOTES/observability.md (operator
runbook). Per the v9.24 anti-coercion-direct discipline: duress
event count is the headline metric.

### T8#12 — Freeze line + definition of done (THE TERMINUS)

**Architect:** One-paragraph definition of done. After that, only
hardening / measurement / thesis work.

**Anti-Architect (the most consequential contest):** This is THE
moment. Five anti-pattern axes converge:

1. **AP3 + AP5 (proposal-as-self-elaboration + vocation drift):** if
   the def-of-done leaves an opening for "well, we should also add
   X," the freeze is fake. The def-of-done must be MECHANICAL with
   a binary check.

2. **AP8 (larping):** the def-of-done must NOT include unproven
   thesis claims ("the agent-maintainable pattern is novel"). It
   must include only what IS true at the freeze version.

3. **AP1 (self-observation):** the freeze line must be VERIFIABLE
   from outside the cognitive layer — an external engineer must be
   able to check it.

4. **AP7 (premature abstraction):** the freeze must NOT pre-define
   future-arc triggers in ways that re-open scope. Triggers are
   operator-named in real time, not pre-cataloged.

5. **The honest hardest contest:** the def-of-done must include the
   CONDITION under which Polaris stops being maintained at all. A
   freeze line that doesn't name the abandonment condition is just
   a pause, not a terminus.

**Joint resolution:** Commit a definition-of-done in MISSION.md as a
new §"Freeze line" section. Mechanical, binary, externally verifiable.
Includes abandonment condition. Naming v9.30 as the freeze version
(after the v9.30 binding-clause check). All work from v9.31 forward
is hardening / measurement / thesis-cold-read. New arcs require a
Sanctum that explicitly cites an external trigger (operator-side
event in the world, not agent-internal observation).

---

## §III. Position selected — JOINT-MODIFIED

- T7#7 (with self-evaluation honesty marker)
- T7#8 (with class-shaped rules constraint + accept-it-never-will
  honestly-named list)
- T7#9 = **HYPOTHESIS-NOT-VERIFIED** (thesis reframed; not published;
  system preserved as tooling)
- T8#10 (with deterministic + CI-runnable + fail-safe-never-open)
- T8#11 (no metrics backend; structured logs + /api/metrics JSON;
  duress events as headline)
- T8#12 = **FREEZE AT v9.30** with mechanical def-of-done + abandonment
  condition

### Items added: 1
The "accept it never will" honestly-named list (per T7#8 Anti-
Architect contest) is added as a structural artifact — a place to
record interventions that cannot be class-shaped into rules.

### Items removed: 0

---

## §IV. Anti-Architect anti-pattern hits surfaced

- **AP1** — caught on T7#7 (self-cold-read is structurally
  compromised; honest framing required); caught on T8#12 (external
  verifiability requirement)
- **AP3** — caught on T7#8 (rules must be class-shaped not instance-
  shaped); caught on T8#11 (no metrics backend without an operator)
- **AP5** — caught on T8#12 (def-of-done must not vocation-drift)
- **AP7** — caught on T8#12 (don't pre-define future-arc triggers)
- **AP8** — caught on T7#9 (publish requires evidence, not narrative);
  caught on T8#12 (no unproven claims in def-of-done); caught on T8#10
  (each chaos scenario must actually inject a failure, not simulate one)

**Five of eight anti-patterns fire substantively** — the most across
any Tier ship. This is the pattern's correct response to a ship that
ASSESSES the pattern itself: maximum self-deception risk; maximum
counterweight required.

---

## §V. Vocation alignment

- T7#7-T7#9: ANTI-COERCION-INFRASTRUCTURE (an honestly-killed false
  thesis is anti-coercion; a maintained false thesis is a coercion
  vector — operators rely on a claim that doesn't hold)
- T8#10: ANTI-COERCION-DIRECT (fail-safe-never-open is the structural
  guarantee that an attacker cannot exploit broken substrate to
  bypass identity guarantees)
- T8#11: ANTI-COERCION-DIRECT (duress events MUST be observable; an
  unobservable duress signal is the coercion-cover failure mode)
- T8#12: ANTI-COERCION-STRUCTURAL (a frozen scope prevents the
  cognitive layer from becoming a moving target that no operator can
  fully audit)

6/6 vocation-positive. 0 negative.

---

## §VI. The terminus (binding clause)

> **From v9.31 forward, the core is frozen. All work is one of:
> (a) hardening (security/dep fixes), (b) measurement (kill test,
> scorecard, MTTR extensions), or (c) thesis cold-read evidence.
> Any new arc requires a Sanctum that names an external trigger
> (operator-side event in the world, not agent-internal observation).
> The thesis remains HYPOTHESIS-NOT-VERIFIED until an independent
> cold-read cycle succeeds. If no cold-read attempt occurs by v9.40,
> the experiment is documented as inconclusive and the strong claim
> is retired permanently.**

This is the binding contract. It is the mechanical version of "this
stops being infinite."

---

## §VII. Outcome

Ship as v9.27. 6 items. Pattern #20 21st instance.

**The Anti-Architect's contest of T7#9 produced the most important
result of the entire BIG MISSION arc**: the strong claim is killed
on insufficient evidence; the experiment is preserved; future
external replication is the only way to revive the claim.

This is the protocol working at its hardest: refusing to publish
something the agent wants to publish, because the evidence isn't
there.

Authorization: VANTA, in-chat 2026-05-16: "Item 12 is the real
terminus."

**SHIPPED 2026-05-16 as v9.27.** New artifacts + TestWave27V927 +
state-map + sanctum-index + journal + MISSION.md §Freeze line.
