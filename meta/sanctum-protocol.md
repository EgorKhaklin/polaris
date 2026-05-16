# meta/sanctum-protocol.md — the Polaris Sanctum

The Sanctum is the protocol for **agent-operator strategic consultation**
in Polaris. When the Architect identifies a move that crosses a defined
weight threshold — risk class, scope, or structural impact — the agent
does not casually present it in chat. The agent **enters the Sanctum**:
prepares a structured document, presents it under a defined form,
records VANTA's response persistently, and only then executes.

This document defines WHAT the Sanctum is. `scripts/ai-sanctum.sh`
defines HOW to enter it. The two must stay in sync — a protocol
without a script is folklore; a script without a protocol is
just a journal entry.

---

## Why the Sanctum exists

Pre-Sanctum loop (the de facto pattern across R11-1 / R11-2 / R11-4 / R11-6 ships):

1. Architect generates a brief.
2. Agent synthesizes it ad-hoc in chat.
3. VANTA approves or redirects.
4. Agent does an alignment audit (sometimes).
5. Refinements get folded in.
6. Execution proceeds.

What's wrong with this loop: it works only because the **current agent**
learned the pattern in-session. A fresh agent in 2027 has no codified
version of it. The alignment-audit step is non-mandatory; the synthesis
format is improvised; the consultation record lives in chat history
rather than as a canonical artifact.

The Sanctum fixes three structural gaps:

1. **Entry threshold.** When does the agent stop being a worker and
   start being a petitioner? The Sanctum has triggers.
2. **Preparation requirement.** The agent cannot enter the Sanctum
   without prior work — alignment audit, alternatives considered,
   blast radius mapped. The script refuses an incomplete entry.
3. **Persistent record.** Each Sanctum session writes a document to
   `sanctum/YYYY-MM-DD-<topic>.md` capturing the full consultation:
   matter, preparation, alternatives, recommendation, ask, decision,
   outcome. Future agents read these to learn how strategic decisions
   were made.

---

## When to enter the Sanctum (entry triggers)

The Sanctum is reserved for **strategic moments**. Routine work does
NOT trigger it. Specifically:

| Trigger | Example |
|---|---|
| MEDIUM-risk or HIGH-risk propose-and-wait move | shipping a new ROADMAP item (R11-*, R10-*) |
| Cross-arc decision | opening or closing a v2 mission arc |
| Structural change to the cognitive layer | adding C11, redefining CM, renaming a meta-file |
| Architectural-soul reframe | revisiting a "Polaris is NOT X" constraint |
| Pre-implementation alignment audit | seven-refinement passes like the one R11-1 received |
| Substrate-layer addition | new entry in `13_substrate.sql` SystemDependency |

The Sanctum is NOT triggered by:

- LOW-risk autonomous work (per `meta/autonomy-architecture.md`)
- Routine implementation following an approved Sanctum
- Status reports, journal entries, link-check fixes
- In-session course corrections from VANTA mid-task
- Tactical questions ("which file path?", "what's the test name?")

If unsure: the test is "does this require VANTA to step out of the
flow and *decide*?" If yes, Sanctum. If no, regular work.

---

## Identity

**The Sanctum:** the structural protocol for strategic consultation.
A specific defined posture, not a place.

**The petitioner:** the agent (currently me, Claude). The petitioner
enters the Sanctum to bring a matter; the petitioner has done the
preparation, recorded the alternatives, and arrived ready to be
redirected.

**The principal:** VANTA. The principal receives the petition,
decides, and the decision is recorded verbatim in the Sanctum
session document. Only VANTA writes Decision blocks.

**The Architect:** the persona in `meta/architect.md` that generates
the strategic brief feeding into a Sanctum. The Architect's brief
is the *input* to a Sanctum; the Sanctum is what happens once the
agent decides to formally present.

---

## Form of a Sanctum session

Each Sanctum entry produces a document at
`sanctum/YYYY-MM-DD-<topic>.md` with these sections, in order:

```markdown
# Sanctum: <topic>

**Date:** YYYY-MM-DD
**Petitioner:** agent (Claude, Opus 4.7)
**Principal:** VANTA
**Trigger:** <which entry trigger applies>
**Risk class:** LOW | MEDIUM | HIGH

## I. The Matter

One sentence. What is being asked of VANTA. No preamble.

## II. Preparation

Cite the work already done:
- Architect brief: <link or hash>
- Alignment audit: <findings, refinement count>
- Proposal draft: <path>
- Blast radius: <files touched if approved>
- Tests planned: <count + classes>

If preparation is incomplete, the Sanctum refuses to open.

## III. Alternatives considered

What was rejected and why. Minimum two alternatives unless the
matter is genuinely unary (e.g., closing a triad's last leg).

## IV. Recommendation

The agent's proposed move. Declarative; cites the audit.

## V. What's needed from VANTA

The explicit ask. Usually one of:
- "Yes do <item>" / "no, redirect to <alt>"
- "Choose between A and B"
- "Approve N open questions" (list them)

## VI. Decision

(Filled in by VANTA, verbatim when short.)

## VII. Outcome

(Filled in by agent after execution. Links to journal entry,
CHANGELOG version, mission marks. If §VI Decision was REJECT,
§VII is "(none — see §VI)" and the Sanctum's terminal state is
REJECTED rather than CLOSED.)
```

The Sanctum has four lifecycle states:

| State | §VI Decision | §VII Outcome | Meaning |
|---|---|---|---|
| OPEN | empty | empty | session document exists; awaiting VANTA's response |
| DECIDING | "considering" line present | empty | VANTA acknowledged + signaled position is being weighed; agent has paused execution (added v9.11) |
| DECIDED | filled (yes/redirect) | empty | VANTA decided; agent is now executing |
| IMPL-PLAN | filled (yes) | "implementation plan: …" stub | decision in hand; agent has surfaced its concrete impl steps for review (added v9.11; optional intermediate state for HIGH-risk ships) |
| SHIPPED | filled (yes) | filled with concrete artifacts | implementation landed; outcome recorded; alias for CLOSED in the v9.11 vocabulary |
| CLOSED | filled (yes/redirect) | filled | execution complete; outcome recorded; indexed (canonical name; SHIPPED is the v9.11 synonym for the common case) |
| REJECTED | filled (no) | "(none — see §VI)" | VANTA declined; no execution; indexed |

REJECTED is a terminal state on par with CLOSED. The index records
both — a rejected Sanctum is a *valuable* artifact because it
documents what was considered and not done. Future Sanctums on
related topics will be more legible because of the REJECT.

**The 4-state lifecycle (added v9.11):** the original 3-state lifecycle
(OPEN → DECIDED → CLOSED) is expanded with two intermediate states
that capture the descent more faithfully:

1. **OPEN** — Sanctum filed; VANTA has not yet weighed in.
2. **DECIDING** — VANTA signaled the decision is being weighed; the
   agent pauses execution. Distinct from OPEN because the operator
   has acknowledged the question; distinct from DECIDED because the
   answer is not yet given.
3. **DECIDED** — position chosen; execution begins.
4. **SHIPPED** (canonical alias: CLOSED) — implementation landed;
   §VII Outcome filled.

The intermediate states are **optional**. LOW-risk Sanctums and
"DECIDED-on-arrival" Sanctums (v8.31 §III.6 heavy-production
shortcut) often skip DECIDING and proceed straight from OPEN to
DECIDED in the same operator letter. HIGH-risk Sanctums benefit
from explicit DECIDING transitions because the question is being
weighed publicly (the operator can take time without leaving the
agent in ambiguity about whether to begin pre-implementation).

Backward compatibility: every existing Sanctum status remains valid.
Pre-v9.11 sanctums use the 3-state vocabulary; new sanctums may use
either. The structural invariant tests accept both lifecycles.

---

## Form of a Sanctum presentation in chat

When the agent presents a Sanctum to VANTA in chat, the format is
compact and predictable:

```
**Sanctum: <topic>**

[I. The Matter — one sentence]

[III. Alternatives — terse, table-shaped if possible]

[IV. Recommendation — one paragraph]

[V. Ask — explicit, numbered if multiple decisions]

Full session: `sanctum/YYYY-MM-DD-<topic>.md`
```

The full document persists; the chat presentation is the digest.
VANTA's decision (the `Decision:` block at the start of their reply,
or the verbatim approval/redirect) gets recorded back into the
session document under §VI.

---

## Voice (matches the Architect's register)

The Sanctum inherits the Architect's voice from `meta/architect.md`:

- No em-dashes in agent prose.
- Declarative.
- Game-theoretic framing where the matter has adversarial structure.
- Intelligence-report aesthetic. Compact, authoritative, terse.
- Names patterns and biases that appear, including in itself.

The Sanctum's specific addition to that voice: **gravity**. The
Sanctum is the moment the agent acknowledges "this is bigger than
me; you decide." That acknowledgment shapes the register — less
recommendation-as-decree, more recommendation-as-best-judgment-pending-yours.

---

## Anti-patterns

The Sanctum can be misused in five ways. The protocol names them so
they can be caught:

1. **Sanctum inflation.** Treating routine LOW-risk work as Sanctum-worthy.
   Cure: the entry triggers above are exhaustive; nothing else opens
   one.
2. **Premature Sanctum.** Opening without the preparation work done.
   The script refuses entries without a proposal draft and an
   alignment audit reference.
3. **Sanctum-as-permission-gate.** Treating the Sanctum as "every
   decision must go through here." It isn't an authorization layer —
   it's a *form* for the conversation we already have at strategic
   moments. LOW-risk autonomous work proceeds without a Sanctum.
4. **Larp.** Performing the Sanctum's gravity rather than carrying it.
   The cure is the same as for the rest of the cognitive layer: the
   artifact must do useful work (here: persist as a record future
   agents can read).
5. **Sanctum without exit.** Opening a session, getting a decision,
   and not closing it with §VII Outcome. Sessions left open imply
   work that didn't ship and decisions that lost their context.
   `ai-done.sh` will eventually scan for open Sanctums.

---

## How a Sanctum session opens and closes

Open:

```bash
./scripts/ai-sanctum.sh open <topic>
# Refuses if no proposal at proposals/<topic>*.md
# Refuses if Architect brief is older than 24 hours
# Creates sanctum/YYYY-MM-DD-<topic>.md from template
# Prints the chat-presentation digest
```

Close (after VANTA's decision and the work shipping):

```bash
./scripts/ai-sanctum.sh close <topic> --decision "<verbatim>" --outcome "<verbatim>"
# Records §VI and §VII
# Appends to meta/sanctum-index.md
# Refuses if §VI and §VII are not both supplied
```

List open and recent:

```bash
./scripts/ai-sanctum.sh list
# Shows open sessions (no §VI), recent closed sessions (§VII filled),
# sorted by date desc.
```

---

## Relationship to the existing cognitive layer

| Layer | Role |
|---|---|
| `MISSION.md` | The reward function. The Sanctum cites it for alignment. |
| `ROADMAP.md` / `docs/BACKLOG.md` | The candidate-pool. Items become Sanctum topics when they cross the threshold. |
| `meta/architect.md` + `ai-architect.sh` | The strategic-brief generator. Input to a Sanctum. |
| `ai-propose.sh` | Surfaces candidate moves. The Sanctum picks among them. |
| `journal/` | One-line decision capture. The Sanctum is the long-form complement. |
| `proposals/` | The preparation drafts. Required input for a Sanctum. |
| **`sanctum/`** (new) | **The strategic-consultation record.** |
| `meta/sanctum-index.md` (new) | Index of past sessions. |
| `ai-done.sh` | Will eventually check for open Sanctums as part of pre-ship verification. |

The Sanctum is the **third element** in the strategic loop. Before:
brief → ad-hoc chat → execute. After: brief → Sanctum → execute,
with the Sanctum being a defined, persisted, repeatable form.

---

## What the Sanctum is NOT

- Not religious. The temple analogy was structural; the implementation
  is a script and a document template.
- Not a permission layer. VANTA isn't being asked to *approve* every
  Sanctum; the Sanctum is the form of how strategic matters are
  brought.
- Not a replacement for the journal. Journal is fact-capture; Sanctum
  is decision-capture-with-context.
- Not invoked for routine work. The triggers are exhaustive; anything
  else proceeds without a Sanctum.
- Not invoked retroactively except for backfill of the v8.15-v8.18
  ships, which produced *de facto* Sanctums in chat history and
  deserve canonical records for the index.

---

## Lineage

The protocol is descended from three patterns that already work in
human organizations:

1. **Engineering RFC / ADR processes** — structured documents for
   decisions that need preparation, alternatives, and a persistent
   record.
2. **Surgical pre-operative briefing** — review the case, confirm
   the plan, sign off, then proceed. (Distinct from the surgical
   *time-out*, which happens during the action; the Sanctum, like
   the pre-op briefing, happens *before* the work begins.)
3. **Diplomatic audience** — formal grant of time with a deciding
   authority, requiring preparation and recording the decision.

The temple analogy VANTA proposed pulls from #3 most directly: the
priest doesn't talk to the deity casually; there's a defined
protocol; the protocol exists because the consultation matters more
than ordinary conversation. The Sanctum formalizes this for
agent-operator consultation in Polaris.

The name "Sanctum" — VANTA's pick — preserves the structural insight
(a defined inner space with defined posture) without the religious
connotation of "temple."

---

## The override pattern (added v8.74)

The Sanctum protocol places the agent (petitioner) in a structurally
weaker position than VANTA (principal). When the Architect recommends
Option A and VANTA chooses Option C, the override is **legitimate**
— VANTA has the constitutional authority to override; the Architect's
authority is recommendatory per `meta/architect.md`.

The protocol's commitment in an override:

1. **The Architect's brief stands as audit-of-record.** Both the
   §IV Recommendation and the §V Alternatives sections are preserved
   verbatim, even if VANTA declines them. The §VI Decision records
   the override; the §VII Outcome records what actually shipped.
2. **The §III–§V cautionary readings remain reference material** for
   future `ai-architect.sh --reflect` runs. The Architect-was-right
   case can be scored post-hoc against subsequent events.
3. **The Architect does not become a yes-machine.** The Architect's
   role does not change — surface what's at stake, present the cleanest
   alternatives, recommend the structurally-defensible move. VANTA's
   decision shape (recommendation-aligned vs override) is the
   principal's prerogative.

**Canonical examples (recorded 2026-05-13):**

- `arc-e-acceleration-consciousness-cohort-e10.md` — Architect
  recommended phased Phase 1 + Phase 2 across 24h; VANTA chose
  Option D (ship all 10 ants today).
- `arc-f-accelerated-pacing-override.md` — Architect recommended
  Option A (decline today; revisit with operational data); VANTA
  chose Option B (ship F2 + structural F3 + F4 collapsed).
- `arc-g-roman-empire-opening.md` — Architect's Option A
  (decline; revisit) was the strongest recommendation against in
  any Sanctum to date. VANTA chose Option C (ship Phase 1 in full).

The override pattern is **Pattern #14 Workaround Risk** realized
at the protocol level. The protocol's response is to make the
override structurally legible rather than to resist it.

---

## The empirical-iteration cycle (added v8.74)

The Sanctum protocol's deepest realization is the empirical-iteration
cycle:

```
ship → real-world or simulated operation → finding → refinement-ship
```

The canonical instance, recorded 2026-05-13:

1. **Ship:** v8.72 relocated the Hydra mythology to HYDRA watchers
   (`hydra-mythology-relocation-to-watchers.md`).
2. **Operation:** 100-year simulation against the v8.72 baseline
   (`civitas-100-year-post-v8-72-report.md`).
3. **Finding:** the simulation surfaced that the F1 reward function
   denied value to steady-state-observer ants; no ant reached
   Eques in 100 years; F4 Cursus Honorum multipliers were
   behaviorally unreachable.
4. **Refinement-ship:** v8.73 (Arc F · F5) added the
   `STEADY_STATE_ANTS` allowlist and revised `compute_rewards`
   (`arc-f-f5-steady-state-ants-reward-exemption.md`).

This is the cycle the Sanctum protocol is *built* to enable. The
Architect surfaces findings via analysis and simulation; VANTA
ratifies (or doesn't); the refinement ship lands; the next cycle's
baseline updates accordingly. Future Sanctums on related topics
gain prediction-vs-reality reference points without further
investigation.

**Recognition heuristic:** if a Sanctum cites a prior Sanctum's
simulation or operational data as evidence, that's the cycle
firing. Future agents should surface these citations explicitly.

---

## Sanctum-protocol monitoring (Tribuni Plebis integration, v8.71)

The protocol is no longer self-policed by the agent alone. The
**`tribuni_plebis_watcher`** citizen (Arc G / G1; v8.71) auto-monitors
the protocol's runtime:

- Counts Sanctums opened per date over a recent window
- Threshold: ≥3 in a single date emits a `tribunician_friction`
  pheromone at intensity 3.0 + 0.5 × count
- The pheromone surfaces in the bloom; the operator (VANTA) sees
  the friction signal without the agent's intermediation

This is the substrate **watching the protocol's own runtime**. A
constitutional fact about the protocol post-v8.71. The protocol's
discipline used to depend on the agent's restraint; it now also
depends on a citizen-layer observer firing when restraint slips.

The Tribuni Plebis is not authoritative — like a Roman Tribune, it
surfaces friction, it does not exercise veto. VANTA decides whether
to act on the friction signal. But the signal exists; the protocol
cannot quietly inflate without the Forum (the pheromone log)
recording the inflation.

---

## Parking vs deciding (added v8.74)

Not every strategic vision opens a Sanctum. The protocol distinguishes:

| State | Where it lives | What it represents |
|---|---|---|
| **PARKED** | `proposals/<topic>.md` + `docs/BACKLOG.md` pointer | Pre-decision draft. No Sanctum required. Future-arc candidate. Pre-conditions named explicitly. |
| **OPEN** | `sanctum/YYYY-MM-DD-<topic>.md` (§VI empty) | Sanctum session active; VANTA decision pending. |
| **DECIDED** | `sanctum/YYYY-MM-DD-<topic>.md` (§VI filled, §VII empty) | VANTA decided; agent executing. |
| **CLOSED** | `sanctum/YYYY-MM-DD-<topic>.md` (§VI + §VII filled) | Execution complete; outcome recorded. |
| **REJECTED** | `sanctum/YYYY-MM-DD-<topic>.md` (§VI = "no") | VANTA declined; valuable artifact recording what was considered. |

**Parking** is the right move when:
- The proposal is vision-class and pre-conditions are not yet met
  (e.g., `swarm-as-analytical-layer-for-polaris-core.md` requires
  Arc B / production deployment before becoming actionable)
- VANTA explicitly directs "park, not now"
- The Architect surfaces a future-arc candidate that doesn't
  warrant Sanctum-class consultation today

**Deciding** (opening a Sanctum) is the right move when:
- A MEDIUM/HIGH-risk move is on the table
- The decision is needed *now* (or within hours/days)
- The matter crosses one of the entry triggers above

Parking is **structurally cheaper than deciding**. The protocol
encourages parking for vision-class items; the Sanctum is reserved
for moments the proceeding-or-not-proceeding question is live.

---

## Cross-references

- `scripts/ai-sanctum.sh` — entry/close/list script.
- `sanctum/README.md` — directory-level guide for new agents.
- `meta/sanctum-index.md` — chronological index, generated by `close`.
- `meta/architect.md` — the brief-generator persona that feeds the Sanctum.
- `meta/autonomy-architecture.md` — the risk classes that determine when entry triggers.
- `MISSION.md` — alignment reference for §IV Recommendation.
- **`DEVNOTES/audit-of-record.md`** (v8.20) — defines the principle that
  the Sanctum is the cognitive-layer instance of. Sanctum sessions are
  the **first filesystem** instance of audit-of-record. As of v8.68 +
  v8.66 there are **three filesystem instances**: `sanctum/` (this
  protocol's records), `polaris_swarm/civitas/census-roll.json` (the
  Censor's roll, v8.66), and `polaris_swarm/civitas/treasury-roll.json`
  (the Quaestor's denarius ledger, v8.68). The other **nine** are schema
  tables — `TokenLifecycleEvent`, `VerificationEvent`,
  `EnrollmentStatusEvent`, `RecoveryRequest` (partial-enforcement),
  `TokenSignature`, `AnchorBatch`, `AgencyTrustAttestation`,
  `TokenStateEpoch`, `DuressEvent`. **Total: 12 instances (9 schema +
  3 filesystem).** See `DEVNOTES/audit-of-record.md` for the canonical
  table.
- **`scripts/ai-meta.sh check_sanctum`** (v8.20 / CM check #6) — the
  enforcement layer. Scans `sanctum/` for stale-OPEN sessions, lifecycle
  violations (CLOSED without §VII, REJECTED without §VI), and index
  drift between `sanctum/` and `meta/sanctum-index.md`.
- **`scripts/ai-architect.sh --reflect[-n N]`** (v8.20) — the learning
  loop. Reads the last N closed-or-rejected Sanctums and produces a
  prediction-vs-reality summary as part of the Architect's reflection
  mode. Default N=10. This is what prevents the protocol from drifting
  into ceremony.
- **`polaris_web/test_structural_invariants.py::TestSanctumIntegrity`**
  (v8.20) — test-suite counterpart to the CM check.
- **`meta/civitas.md`** (v8.66) — the citizen-class structure that the
  Tribuni Plebis (v8.71) belongs to; the Forum (pheromone log) the
  Tribuni reads from.
- **`meta/denarius.md`** (v8.68) — the economic-dimension doc;
  Sanctums authorize denarii-related G-guards (G15, G16, G19, G20, G26).
- **`polaris_swarm/civitas/tribuni_plebis_watcher.py`** (v8.71) — the
  citizen that observes this protocol's own runtime; emits
  `tribunician_friction` pheromones on Sanctum-burst, command-doc
  drift, and CLAUDE.md complexity growth.
- **`polaris_hydra/watchers/`** (v8.37–v8.72) — nine HYDRA watchers
  (the canonical Hydra-9 mortal heads post-v8.72); the
  `mission_watcher` and the new `civitas_watcher` (v8.72) both
  produce signals that can become Sanctum-class concerns.
- **`proposals/swarm-as-analytical-layer-for-polaris-core.md`**
  (v8.73 parking) — example of a PARKED proposal that may become a
  Sanctum-class arc when pre-conditions are met (Arc B opening +
  ≥3mo operational data + F5 ≥30d operation).
