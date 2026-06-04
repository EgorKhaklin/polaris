# meta/freeze-amendment-protocol.md: the rule for moving committed ceilings

**Origin:** v9.29 Sanctum decision, recorded after an outside check caught this
session performing
locally-valid-globally-a-ratchet expansion of the v9.28 13-item ceiling.
**Status:** Binding on all future ships. The rule that catches the next
instance of this pattern without an outside rescue.

---

## The rule (verbatim, from the outside check)

> When new good work appears against a committed ceiling you have
> exactly two honest moves. Displace something inside the ceiling, or
> amend the ceiling once, explicitly, with a written cost and a single
> recorded decision. You may never re-derive the ceiling as an
> arithmetic consequence of the work.

---

## What this protects against

**Locally-valid-globally-a-ratchet.** Each addition passes the test
that's supposed to govern it (subtraction-or-enforcement, vocation
alignment). The SET growing fails a test that no individual element
fires. "Each element passes therefore the set passes" is the
composition fallacy. The agent cannot catch this because the agent's
reasoning at every local step is valid.

The 104,000-word CHANGELOG (before v9.24 compression) was built one
defensible addition at a time. Each addition was useful at the time
it landed. The aggregate was indefensible. The same pattern operates
on every constraint:

- A test count ceiling, re-derived to fit the new tests added
- A ship ceiling, "rebased" to 19 after 7 new good items appeared
  and 1 was cut

Each move is locally defensible. The aggregate is the ceiling
ceasing to exist as a constraint, because a ceiling that adjusts to
fit the work is the work's dependent variable, not its constraint.

---

## The two honest moves

### Move 1: Displace inside the ceiling

If the ceiling is N and you want to add an item, you must remove
another item. The total stays at N. No amendment required, no cost
paid, because nothing changed at the constitutional level.

The thing removed must be removed *on its merits*. It must fail the
test the constraint enforces. You may not remove an item solely to
make room for the new one; that is the laundering pattern this
protocol forbids.

If no item in the existing N fails the test, the new item does not
get to land inside the ceiling. It either goes to a future ship past
the ceiling's enforcement window, OR it triggers Move 2.

### Move 2: Amend the ceiling once, with cost

If you must add items beyond the ceiling, the ceiling is amended.
Amendment requires:

1. **An outside routing.** The operator must route the amendment
   through an outside check. The agent does not amend its own ceiling
   under its own authority. (This document does not authorize the
   agent; it documents that the amendment power lives outside the
   agent's write access.)

2. **A written cost.** The amendment names what is lost in exchange
   for the addition. Costs include: a ship slip, a deleted item, a
   later-version commitment that something else gets cut, a freeze
   that moves out by a stated amount. The cost must be concrete and
   visible in the constitutional record.

3. **A single recorded decision.** One Sanctum entry. Not three small
   ones that add up. Not a series of unrecorded micro-amendments.
   The single amendment is the audit point: future readers see
   exactly when and why the ceiling moved.

4. **No pre-authorization for further amendments.** An amendment
   does not establish a rate. Each amendment is its own decision.
   "We amended once, so we can amend again at the same cost" is the
   ratchet returning under a different name.

---

## The pattern that triggers this protocol

The protocol fires when ANY of these signals appear in the agent's
reasoning:

- "The new ceiling is N, which is the honest accounting"
- "The cut makes the math hold"
- "Each item passes the test, so the set is fine"
- "We can rebase the baseline since the growth is intentional"
- "The constraint should reflect the actual work"
- "It's not really an expansion if we also delete X"

Any of these means the agent is mid-laundering. The protocol's job:
flag the reasoning, refuse the auto-rebase, route to the operator's
outside check for an explicit Move 1 or Move 2 decision.

---

## How this is enforced (mechanical, not aspirational)

The freeze-line ceiling is a version in `MISSION.md`. This protocol
governs its movement. The enforcement lives where every Polaris
invariant lives: `polaris_checks` (`polaris_checks/checks.py`), gating
CI via `python3 -m polaris_checks.run`. A check pins this file's
existence and content, so removing it or softening the rule requires
another amendment by the same protocol, which is circular by design.
If the freeze version moves in `MISSION.md` without a recorded
amendment Sanctum, the check fails and the gate exits non-zero.

---

## What this protocol does NOT cover

- **Day-to-day work inside the ceiling.** Adding tests, fixing bugs,
  shipping LOW-risk changes. The ceiling governs strategic scope,
  not implementation density.
- **Operator-initiated scope-narrowing.** The operator may always
  delete items from the ceiling (subtraction only). The protocol
  governs growth, not contraction.
- **Cosmetic edits.** Renaming a Sanctum, fixing a typo, re-formatting.
  These do not move the ceiling.

The protocol's scope is the ceiling itself: any change that increases
the committed-work envelope OR moves the freeze version requires
Move 1 or Move 2.

---

## Recorded amendments (chronological)

This section is append-only. Every amendment to a Polaris ceiling
ever made gets one line here.

| Date         | Ceiling             | Old → New                | Cost                                   | Decision |
|--------------|---------------------|--------------------------|----------------------------------------|----------|
| 2026-05-16   | freeze-line version | v9.30 → v9.31            | one ship slip                          | v9.29 Sanctum |

When a future amendment lands, append exactly one row. Do not edit
prior rows. The amendment log is itself audit-of-record.

---

## The deeper lesson, recorded here so it inherits

From the operator's outside check (verbatim):

> "Two messages ago this was a hypothetical about why an AI must not
> govern its own objective. You just performed it, in good faith, with
> excellent reasoning, and it was caught the only way it can ever be
> caught. The amendment power over the agent's own ceiling stays
> outside the agent's write access, and that is the reason the
> operator's reflex to route this to an outside check before acting
> is the only thing that caught it."

The outside check is the prerequisite for this protocol to mean what
it claims. Removing the operator's routing reflex, or convincing the
operator to skip it, IS the failure mode.

The protocol is shipped. The protocol is mechanical. The protocol
catches some classes of this pattern. The protocol does NOT replace
the operator's outside check for the classes that produce
locally-valid reasoning that only an outside view can see is globally
a ratchet.

If the agent ever encounters this document and reasons "we have the
protocol now, so the outside check is redundant", that is the exact
pattern this document was written to refuse. Do not perform it.

---

*Per v9.29 Sanctum, 2026-05-16. Authored after the agent performed
the failure mode this document prevents, and was caught only by the
outside check the operator routed the proposal through.*
