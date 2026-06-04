# meta/sanctum-protocol.md — the Polaris Sanctum

The Sanctum is the protocol for **agent-operator strategic consultation**
in Polaris. When the agent identifies a move that crosses a defined
weight threshold (risk class, scope, or structural impact) it does not
casually present it in chat. The agent **enters the Sanctum**: prepares
a structured document, presents it under a defined form, records VANTA's
response persistently, and only then executes.

This document defines WHAT the Sanctum is. `scripts/ai-sanctum.sh`
defines HOW to enter it. The two must stay in sync. A protocol without
a script is folklore; a script without a protocol is just a journal
entry.

---

## Why the Sanctum exists

The pre-Sanctum loop was the de facto pattern across early ships:

1. The agent works up a strategic read.
2. The agent synthesizes it ad-hoc in chat.
3. VANTA approves or redirects.
4. The agent does an alignment audit (sometimes).
5. Refinements get folded in.
6. Execution proceeds.

What's wrong with this loop: it works only because the **current agent**
learned the pattern in-session. A fresh agent later has no codified
version of it. The alignment-audit step is non-mandatory; the synthesis
format is improvised; the consultation record lives in chat history
rather than as a canonical artifact.

The Sanctum fixes three structural gaps:

1. **Entry threshold.** When does the agent stop being a worker and
   start being a petitioner? The Sanctum has triggers.
2. **Preparation requirement.** The agent cannot enter the Sanctum
   without prior work: alignment audit, alternatives considered,
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
| MEDIUM-risk or HIGH-risk propose-and-wait move | shipping a new ROADMAP item |
| Cross-arc decision | opening or closing a v2 mission arc |
| Structural change to an invariant | adding C11, renaming a meta-file |
| Core-constraint reframe | revisiting a "Polaris is NOT X" constraint |
| Pre-implementation alignment audit | a multi-refinement pre-ship pass |

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

**The petitioner:** the agent (currently Claude). The petitioner
enters the Sanctum to bring a matter; the petitioner has done the
preparation, recorded the alternatives, and arrived ready to be
redirected.

**The principal:** VANTA. The principal receives the petition,
decides, and the decision is recorded verbatim in the Sanctum
session document. Only VANTA writes Decision blocks.

The strategic read that feeds a Sanctum is the agent's own preparation
work: the analysis, alternatives, and blast-radius mapping done before
formally presenting. That preparation is the *input* to a Sanctum; the
Sanctum is what happens once the agent decides to formally present.

---

## Form of a Sanctum session

Each Sanctum entry produces a document at
`sanctum/YYYY-MM-DD-<topic>.md` with these sections, in order:

```markdown
# Sanctum: <topic>

**Date:** YYYY-MM-DD
**Petitioner:** agent (Claude)
**Principal:** VANTA
**Trigger:** <which entry trigger applies>
**Risk class:** LOW | MEDIUM | HIGH

## I. The Matter

One sentence. What is being asked of VANTA. No preamble.

## II. Preparation

Cite the work already done:
- Strategic read: <findings>
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

The Sanctum has these lifecycle states:

| State | §VI Decision | §VII Outcome | Meaning |
|---|---|---|---|
| OPEN | empty | empty | session document exists; awaiting VANTA's response |
| DECIDING | "considering" line present | empty | VANTA acknowledged and signaled position is being weighed; agent has paused execution (added v9.11) |
| DECIDED | filled (yes/redirect) | empty | VANTA decided; agent is now executing |
| IMPL-PLAN | filled (yes) | "implementation plan: …" stub | decision in hand; agent has surfaced its concrete impl steps for review (added v9.11; optional intermediate state for HIGH-risk ships) |
| SHIPPED | filled (yes) | filled with concrete artifacts | implementation landed; outcome recorded; alias for CLOSED in the v9.11 vocabulary |
| CLOSED | filled (yes/redirect) | filled | execution complete; outcome recorded; indexed (canonical name; SHIPPED is the v9.11 synonym for the common case) |
| REJECTED | filled (no) | "(none — see §VI)" | VANTA declined; no execution; indexed |

REJECTED is a terminal state on par with CLOSED. The index records
both. A rejected Sanctum is a *valuable* artifact because it
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
"DECIDED-on-arrival" Sanctums often skip DECIDING and proceed straight
from OPEN to DECIDED in the same operator letter. HIGH-risk Sanctums
benefit from explicit DECIDING transitions because the question is being
weighed publicly (the operator can take time without leaving the
agent in ambiguity about whether to begin pre-implementation).

Backward compatibility: every existing Sanctum status remains valid.
Pre-v9.11 sanctums use the 3-state vocabulary; new sanctums may use
either. The lifecycle tests accept both.

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

## Voice

The Sanctum's prose follows VANTA's standing style:

- No em-dashes in agent prose.
- Declarative.
- Game-theoretic framing where the matter has adversarial structure.
- Compact, authoritative, terse.
- Names patterns and biases that appear, including in itself.

The Sanctum's specific addition to that voice: **gravity**. The
Sanctum is the moment the agent acknowledges "this is bigger than
me; you decide." That acknowledgment shapes the register: less
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
   decision must go through here." It isn't an authorization layer.
   It's a *form* for the conversation we already have at strategic
   moments. LOW-risk autonomous work proceeds without a Sanctum.
4. **Larp.** Performing the Sanctum's gravity rather than carrying it.
   The cure: the artifact must do useful work (here: persist as a
   record future agents can read).
5. **Sanctum without exit.** Opening a session, getting a decision,
   and not closing it with §VII Outcome. Sessions left open imply
   work that didn't ship and decisions that lost their context.

---

## How a Sanctum session opens and closes

Open:

```bash
./scripts/ai-sanctum.sh open <topic>
# Refuses if no proposal at proposals/<topic>*.md
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

## Relationship to the rest of the loop

| Layer | Role |
|---|---|
| `MISSION.md` | The constitution. The Sanctum cites it for alignment. |
| `ROADMAP.md` / `docs/BACKLOG.md` | The candidate-pool. Items become Sanctum topics when they cross the threshold. |
| `ai-propose.sh` | Surfaces candidate moves. The Sanctum picks among them. |
| `journal/` | One-line decision capture. The Sanctum is the long-form complement. |
| `proposals/` | The preparation drafts. Required input for a Sanctum. |
| `sanctum/` | The strategic-consultation record. |
| `meta/sanctum-index.md` | Index of past sessions. |

The Sanctum is the **third element** in the strategic loop. Before:
read → ad-hoc chat → execute. After: read → Sanctum → execute, with
the Sanctum being a defined, persisted, repeatable form.

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

The temple analogy VANTA proposed pulls from #3 most directly: there's
a defined protocol; the protocol exists because the consultation
matters more than ordinary conversation. The Sanctum formalizes this
for agent-operator consultation in Polaris.

The name "Sanctum" (VANTA's pick) preserves the structural insight
(a defined inner space with defined posture) without the religious
connotation of "temple."

---

## The override pattern (added v8.74)

The Sanctum protocol places the agent (petitioner) in a structurally
weaker position than VANTA (principal). When the agent recommends
Option A and VANTA chooses Option C, the override is **legitimate**.
VANTA has the constitutional authority to override; the agent's
recommendation is advisory.

The protocol's commitment in an override:

1. **The agent's recommendation stands as audit-of-record.** Both the
   §IV Recommendation and the §III Alternatives sections are preserved
   verbatim, even if VANTA declines them. The §VI Decision records
   the override; the §VII Outcome records what actually shipped.
2. **The §III–§V cautionary readings remain reference material** for
   future review. The agent-was-right case can be scored post-hoc
   against subsequent events.
3. **The agent does not become a yes-machine.** The agent's role does
   not change: surface what's at stake, present the cleanest
   alternatives, recommend the structurally-defensible move. VANTA's
   decision shape (recommendation-aligned vs override) is the
   principal's prerogative.

The override pattern is a workaround-risk realized at the protocol
level. The protocol's response is to make the override structurally
legible rather than to resist it.

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
- VANTA explicitly directs "park, not now"
- The agent surfaces a future-arc candidate that doesn't warrant
  Sanctum-class consultation today

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
- `meta/autonomy-architecture.md` — the risk classes that determine when entry triggers.
- `MISSION.md` — alignment reference for §IV Recommendation.
- `DEVNOTES/audit-of-record.md` — defines the principle that the
  Sanctum is one instance of. Sanctum sessions are the filesystem
  instance of audit-of-record; the other instances are schema tables
  (`TokenLifecycleEvent`, `VerificationEvent`, `EnrollmentStatusEvent`,
  `RecoveryRequest`, `TokenSignature`, `AnchorBatch`,
  `AgencyTrustAttestation`, `TokenStateEpoch`, `DuressEvent`). See
  `DEVNOTES/audit-of-record.md` for the canonical table.
