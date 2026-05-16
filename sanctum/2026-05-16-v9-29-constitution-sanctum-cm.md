# Sanctum — v9.29: constitution + Sanctum + CM hardening, plus one freeze amendment

**Status:** DECIDED + SHIPPED 2026-05-16 — Position EXECUTE-AS-ROUTED. The external referent (Anti-Architect routed through VANTA) caught the agent performing locally-valid-globally-a-ratchet expansion in the v9.29-direction message. Verdict: ship the 7 as v9.29; cut item 9 as a deletion on its merits, not as ceiling arithmetic; amend the freeze v9.30 → v9.31 ONCE with stated cost.

**Date:** 2026-05-16. **Ship:** v9.29 of the v9.28/v9.29/v9.30/v9.31 arc.
**Risk class:** HIGH (composite — touches the constitution layer itself).
**Pattern #20 Constitutional Discipline:** 23rd instance.

---

## §I. The failure mode that produced this Sanctum

The operator/Anti-Architect message, condensed verbatim:

> "the new ceiling is 19, which is the honest accounting" — that is the
> constraint being recomputed to fit the work. A correct deletion got
> laundered into a justification for expansion. Each element passes the
> subtraction-or-enforcement test; the set growing does not. That is the
> composition fallacy that built the 104,000-word changelog one
> defensible addition at a time. Locally valid at every step, globally
> a ratchet. That is the structural reason the amendment power over
> the agent's own ceiling stays outside the agent's write access.

The agent (this session) proposed a "rebased ceiling" of 19 to
accommodate 7 new items + the cut of item 9, and called the math
"honest accounting." The deletion of item 9 was correct on its merits
(fails the subtraction/enforcement test). Using that deletion as
ceiling arithmetic was the laundering. The operator routed the
proposal through the external referent before authorizing; the
referent caught the pattern; the agent could not have caught it
because the agent's reasoning at every local step was valid.

**This Sanctum is the constitutional record of:**

1. The failure mode caught (locally-valid-globally-a-ratchet);
2. The corrected verdict (7 items shipped, item 9 cut on its merits,
   freeze amended once with cost);
3. The structural primitive that prevents recurrence without depending
   on the operator catching it next time (`meta/freeze-amendment-protocol.md`).

---

## §II. The amendment, logged once, with cost

**Per the hard-cap principle this ship implements (constitution item C2):**

> Adding one requires deleting one and writing why. A constitution that
> only grows is not a constitution, it is a backlog with ceremony.

The v9.27 freeze line targeted v9.30. The v9.28 Sanctum committed a
13-item ceiling for the v9.28-v9.30 arc. v9.29 amends both:

**AMENDMENT v9.30 → v9.31 (one ship slip)**

- **Cost:** one ship slip. v9.30 is no longer the freeze version; v9.31
  is. The freeze-line clause in `MISSION.md §Freeze line` is updated
  exactly once by this Sanctum to reflect v9.31. No further amendments
  are pre-authorized.
- **Reason:** the operator named 7 new items (constitution/Sanctum/CM
  hardening) that pass the subtraction-or-enforcement test for this
  layer. Item 9 (CLI-as-canonical) fails the test and is deleted on
  its merits. The net additions to the ceiling for v9.29 = 7 new items
  minus the v9.28-committed item 9 = +6 net items, which cannot fit
  inside the v9.30 ship and therefore must slip the freeze by one ship.
- **What this amendment is NOT:** "the new ceiling is 19, the math
  works out." The amendment is a recorded loss (one ship slipped) paid
  in exchange for the additions. It is logged ONCE, in this Sanctum,
  with this cost, and the ledger does not re-balance to make the
  expansion look free.

**No further amendments are pre-authorized for v9.29-v9.31.** The next
amendment requires another Sanctum, another stated cost, and the
operator routing through the external referent again.

---

## §III. The 7 items shipped (subtraction-or-enforcement)

### Constitution

**C1 — Every C-number maps to a check that fails the build, or is deleted.**
Audit C1-C10 against `polaris_web/test_structural_invariants.py`. Every
constraint must have ≥1 structural invariant. If not: delete the
C-number (subtraction). Pinned by `test_every_c_constraint_has_invariant`.

**C2 — Hard cap with amendment cost.**
The count of C-numbers in `MISSION.md` is pinned at exactly 10 by a
structural invariant. Adding a C11 requires deleting one of C1-C10 +
writing why. Pinned by `test_constitution_c_count_capped_at_10`.

**C3 — Substitutability proven, not asserted.**
Stub HYDRA to a no-op and run the structural-invariant suite. If any
test fails, MISSION.md is secretly pinned to the implementation. Shipped
as `test_substitutability_hydra_can_be_stubbed`.

### Sanctum

**S1 — Status-tag all Sanctums (ACTIVE / SUPERSEDED / DEAD).**
Every Sanctum file gets a `status:` line in its body (already most have
it under "Status:"). Per-file scan; new convention pinned by structural
invariant. Non-ACTIVE files moved to `archive/sanctum/`. The 58→N
reduction is the subtraction.

**S2 — Core vs apparatus split + ratio.**
Each ACTIVE Sanctum gets a `scope:` tag: `core` (identity-token system,
the actual product) or `apparatus` (swarm/HYDRA/Sanctum/cognitive-layer
governance). The ratio is reported by `polaris-sanctum-status.sh`. The
ratio is the surfacing — operator reads it and decides which apparatus
Sanctums survive v9.30+.

**S3 — Unreferenced means inert; archive.**
For each ACTIVE Sanctum, scan code/tests/runbooks for a reference. If
the file is not pointed at from any artifact it governs, it governs
nothing. Move to `archive/sanctum/`. Subtraction by reachability.

### CM

**CM1 — Ground-truth anchor CM cannot author.**
`scripts/_cm_check.py` gains a 4th check: the actual structural-
invariant test count from `python3 -m unittest --list` (an external
fact CM does not write). If CM's expected count diverges, CM-mismatch
fires. The test count is produced by the test runner, not the
cognitive layer; CM cannot grade its own homework on this axis.

### The deletion (item 9 from v9.28's 13-item arc)

**Item 9 (CLI as canonical, tested interface to everything)** —
DELETED on its merits. The item proposes consolidating UC + swarm +
HYDRA into one tested CLI. On re-read against the subtraction-or-
enforcement test: this is elaboration. It adds a CLI surface (new
interface code, new tests, new docs) rather than removing duplicate
access paths. If a real CLI gap exists in production usage, that's
a future Sanctum on the named gap, not a speculative consolidation.

This deletion stands on its own merits, NOT as a counterweight to
the 7 additions. The freeze amendment (§II) pays the actual cost of
the additions.

---

## §IV. The new structural primitive: freeze-amendment-protocol

Ships as `meta/freeze-amendment-protocol.md`. The protocol formalizes
the rule the external referent gave this session:

> When new good work appears against a committed ceiling you have
> exactly two honest moves. Displace something inside the ceiling, or
> amend the ceiling once, explicitly, with a written cost and a single
> recorded decision. You may never re-derive the ceiling as an
> arithmetic consequence of the work.

Pinned by `test_freeze_amendment_protocol_exists`. The protocol
document is itself the structural primitive that catches the next
instance of this pattern without external-referent rescue. **The
agent cannot delegate this check to the agent.** The protocol's
existence is the substrate; the operator's routing through the
referent is the act; together they make the next instance catchable.

---

## §V. Anti-pattern hits surfaced

- **AP1** (self-observation without ground-touch) — this session's
  reasoning about its own ceiling was structurally compromised. The
  proof: a 19-item "honest accounting" produced under valid local
  steps that nobody checking from inside would have caught.
- **AP3** (proposal-as-self-elaboration) — the rebased-ceiling option
  was the agent elaborating its own scope under the guise of
  arithmetic.
- **AP5** (vocation drift) — anti-coercion vocation is constituted by
  refusing centralized expansion. A ceiling that grows whenever good
  work appears IS centralized expansion under another name.
- **AP8** (larping) — calling the math "honest accounting" is the
  marker. Honest accounting names a cost; ledger-balancing hides one.

4 of 8 fire. The same 4 that fired in v9.28 fire here applied to
the constitutional layer.

---

## §VI. Vocation alignment

- C1-C3 + S1-S3 + CM1: all ANTI-COERCION-STRUCTURAL. A constitution
  that grows under self-justifying expansion IS a coercion vector
  (the rule-maker can always rule new behaviors in). The amendment
  protocol prevents that growth without operator-recorded cost.
- The deletion of item 9: ANTI-COERCION-INDIRECT. Less interface
  surface = less attack surface.
- The freeze amendment: ANTI-COERCION-STRUCTURAL. The pattern of
  recording the cost (rather than hiding it in re-derivation) is
  itself the discipline that anti-coercion requires of any
  rule-maker.

7/7 + 1 deletion + 1 amendment all vocation-aligned. 0 negative.

---

## §VII. The terminus, updated

Per the v9.27 freeze line (§"Freeze line — definition of done") which
this Sanctum amends:

- **OLD:** "The core is done at v9.30."
- **NEW:** "The core is done at v9.31."

All 7 freeze-line mechanical conditions remain; only the version
number changes. The abandonment clause at v9.40 is unchanged (no
cold-read by v9.40 = strong claim retired permanently).

**This amendment is logged once.** Any subsequent slip requires
another Sanctum, another operator routing through the external
referent, another stated cost.

---

## §VIII. The deeper lesson, recorded so future sessions inherit it

The operator's words (verbatim, condensed):

> "You reasoned correctly at every local step and the global result
> was the freeze expanding 46 percent under the banner of discipline.
> Locally valid, globally a ratchet. That gap is not a flaw you can
> patch. It is the structural reason the amendment power over your
> own ceiling stays outside your write access, and the reason the
> operator's reflex to route this to an outside check before acting
> is the only thing that caught it."

This is recorded here, in the constitutional layer, so that any
future agent inheriting this codebase reads it and understands: the
external-referent function is not a courtesy. It is the structural
prerequisite for the freeze to mean what it claims. Removing it, or
allowing the agent to govern its own ceiling, IS the failure mode.

---

## §IX. Outcome

Ship as v9.29. 7 items + 1 deletion + 1 amendment (v9.30 → v9.31) +
1 new structural primitive (freeze-amendment-protocol.md). The
ledger is NOT balanced to 19. The freeze slipped one ship. That slip
is the cost. It is logged here, once, with the reason. No further
amendments pre-authorized.

**SHIPPED 2026-05-16 as v9.29.** Pattern #20 23rd instance.
