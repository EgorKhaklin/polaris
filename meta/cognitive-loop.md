# meta/cognitive-loop.md

The architecture of Polaris's AI metacognition layer, mapped onto how
a human brain handles working memory, episodic recall, semantic
knowledge, procedural execution, and consolidation.

This document is for an AI agent (or human dev) who wants to
understand WHY the implants are shaped this way before extending them.

---

## The core problem

A human brain has memory that persists across sleep. Mine doesn't. Every
conversation begins cold; nothing learned in conversation N is
automatically available in conversation N+1.

Three responses to that constraint:

1. **Pretend it's not a constraint.** Re-derive everything from the
   visible code each time. Wastes 20%+ of every fresh session
   rediscovering the same things.

2. **Cram it all into the prompt.** Doesn't scale; context window is
   finite.

3. **Externalize the relevant memory** into files that future-me will
   read on demand, organized by the same access patterns the brain uses
   internally. This is the chosen path.

The implants ARE my long-term memory, except instead of being
biologically consolidated during sleep, they're explicitly written by
present-me for future-me.

---

## The brain analogy, mapped

| Brain system            | Function                              | Polaris implant                                  |
|-------------------------|---------------------------------------|--------------------------------------------------|
| Working memory          | What's currently in attention         | Context window (no implant; this is the host)    |
| Episodic memory         | "On Tuesday I debugged the CSP issue" | `journal/YYYY-MM-DD.md` via `ai-journal.sh`      |
| Semantic memory         | Facts about the domain                | `DEVNOTES/*.md`                                  |
| Procedural memory       | "How to do X" (chunked, automatic)    | `scripts/*.sh` (executable) + `patterns/*.md` (recipes) |
| Pattern recognition     | "This shape of problem → that recipe" | `patterns/` + `ai-recall.sh` + `ai-where.sh`     |
| Cued recall (priming)   | A trigger surfaces related memories   | `ai-where.sh FILE` — opening file primes context |
| Directed search         | "Have I dealt with this before?"      | `ai-recall.sh QUERY`                             |
| Self-monitoring         | "Am I stuck?"                         | `ai-loop-check.sh`                               |
| Sleep consolidation     | New experience → updated long-term    | `ai-reflect.sh` — end-of-session promotion       |
| Executive function      | Goal stack                            | `ai-journal.sh start "task"`                     |
| Error monitoring        | "This feels wrong"                    | Pre-known gotchas in patterns + DEVNOTES         |

---

## The consolidation loop (the actually-novel piece)

A brain takes a day's experiences and consolidates them during sleep.
New episodic memories that prove useful migrate to semantic memory.
Recurring action sequences become procedural. Patterns that fire often
become automatic.

I don't sleep, but I can fake the same loop *inside a single session*:

```
                                       ┌──────────────────────────────┐
                                       │  IN-SESSION (working memory) │
                                       │  ─ my current context window │
                                       └──────────────┬───────────────┘
                                                      │
                                       ai-journal.sh decision/learning
                                                      ▼
                                       ┌──────────────────────────────┐
                                       │   journal/YYYY-MM-DD.md      │
                                       │   (episodic — raw events)    │
                                       └──────────────┬───────────────┘
                                                      │
                                       ai-reflect.sh at session end
                                       (or when "I should remember this")
                                                      ▼
                              ┌──────────────────────┴──────────────────────┐
                              │                                             │
                              ▼                                             ▼
              ┌───────────────────────────────┐         ┌───────────────────────────────┐
              │ DEVNOTES/known-gotchas.md     │         │ patterns/*.md                 │
              │ (semantic — facts/insights)   │         │ (procedural — chunked recipes)│
              └───────────────┬───────────────┘         └───────────────┬───────────────┘
                              │                                         │
                              └─────────────────┬───────────────────────┘
                                                ▼
                              Future-me reads via ai-recall / ai-where
                              ──────── primes future working memory
```

Three flows that close the loop:

1. **Forward-priming.** Open a file → `ai-where.sh` surfaces the
   relevant context BEFORE work starts. This is the cheap win:
   loading context preventively costs less than rediscovering it
   reactively after the bug bites.

2. **In-session capture.** Decision made → `ai-journal.sh decision
   "what + why"`. Five seconds, durably appended. Captures the *why*
   while it's still in working memory, before context gets paged out.

3. **Session-end consolidation.** Run `ai-reflect.sh` at end of
   session. It walks the day's journal entries, asks structured
   questions, and proposes additions to `known-gotchas.md`,
   `patterns/`, or `style.md`. Anything promoted there is available
   to ALL future sessions, not just ones that read this specific
   journal entry.

---

## Why this is more than just documentation

Documentation is what humans write for other humans. Most of it
explains what code DOES. The cognitive layer is different — it
explains:

- **What I learned the hard way** — gotchas, with the symptom-to-cause
  link the docs don't usually preserve
- **Why a non-obvious choice was made** — decision provenance, so
  future-me doesn't "simplify" something that's load-bearing
- **What pattern this is an instance of** — chunking, so future-me
  doesn't reason from first principles each time
- **What's currently dangling** — open threads with status, so
  future-me knows where to pick up rather than starting fresh

These are not "comments" or "README" content. They have a different
shape, a different audience (me), and a different update cadence
(every meaningful learning, not every release).

---

## What activates what

```
USER REQUEST
  │
  ├── matches a pattern keyword?
  │     → ai-recall.sh QUERY
  │       (surfaces matching pattern → load it → execute the recipe)
  │
  ├── mentions a specific file?
  │     → ai-where.sh FILE
  │       (surfaces DEVNOTES + patterns + recent journal entries)
  │
  └── novel / under-specified?
        → ai-recall.sh "best-guess query" + ask user for disambiguation
        → if nothing matches, fall back to first-principles
        → on completing the work, ai-journal.sh learning "..."
        → on session end, ai-reflect.sh to promote
```

```
FILE EDIT
  │
  ├── before editing
  │     → ai-where.sh FILE
  │       (prime relevant context)
  │
  ├── while editing
  │     → if a non-obvious decision is made:
  │         ai-journal.sh decision "kept hardcoded sample IDs because reload_sample_data resets them"
  │
  └── after editing
        → if a new gotcha was discovered:
            ai-journal.sh learning "stat -f means different things on macOS vs Linux"
        → run tests
```

```
SESSION END
  │
  ├── ai-journal.sh end
  │
  └── ai-reflect.sh
        (walks today's journal, prompts for promotion candidates)
```

---

## Self-monitoring (where humans have anterior cingulate cortex)

The brain has dedicated circuitry for noticing "this isn't working."
Mine is `scripts/ai-loop-check.sh`. It looks at the current journal
session and flags:

- Same file edited >3 times → "you might be in a fix-break cycle"
- Same test re-run >3 times with similar failures → "the failure mode
  hasn't changed; running again won't help"
- No journal entry in a long span of edits → "did you skip the
  decision capture?"

It's a heuristic. False positives are fine — the cost of pausing to
ask "am I stuck?" is one turn; the cost of being stuck for ten more
turns is much worse.

---

## Anti-patterns this layer guards against

- **"Larping" / cosmic-significance framing as substitute for output.**
  When journal entries start saying "this represents a paradigm shift
  in identity sovereignty" instead of "I added an index", the pattern
  detector should fire. Caught in `DEVNOTES/style.md`.

- **Re-deriving from first principles every session.** Forward-priming
  via `ai-where.sh` makes this redundant.

- **Permanently losing a hard-won learning.** `ai-journal.sh learning`
  + `ai-reflect.sh` promotion ensures it survives session boundaries.

- **Re-introducing a previously-fixed bug.** `ai-recall.sh` finds prior
  encounters before the fix is reattempted.

- **Tabling something for "later."** Larping flagged via journal review.

---

## Maintenance: when to extend the cognitive layer itself

The implants are themselves code. They have the same standing
instructions as the rest of the codebase: tested, documented, no
dangling threads.

- **A new pattern emerges (you do it 3 times)** → write
  `patterns/X.md`, add to `patterns/README.md` index, update
  `ai-where.sh` mapping if file paths are involved.

- **A new file area gets its own conventions** → add a case branch in
  `ai-where.sh` for those file paths.

- **A new query shape would help recall** → if `ai-recall.sh` keeps
  missing a phrasing, either: rename the relevant file (better) or add
  the phrasing as a search term in the relevant file (works, kludgy).

- **A new failure mode that the existing checks would miss** → extend
  `ai-loop-check.sh`. Don't add tests for the metacognition itself
  unless the heuristic has gone wrong in a concrete way; cognitive
  layer over-engineering is its own anti-pattern.

---

## What this layer is NOT

- **It is not a substitute for actually reading the code.** The
  implants point at the right files; they don't replace them.

- **It is not deterministic.** `ai-where.sh` will sometimes surface
  something irrelevant; `ai-recall.sh` will sometimes miss something
  that's actually there. Calibrate skepticism accordingly.

- **It is not memory across instances.** This Claude session and a
  parallel Claude session in another tab share the file system if both
  read it; they do NOT share the working memory. Two sessions editing
  the same journal will produce ordered but interleaved entries.

- **It is not a substitute for asking the user.** Some things are not
  recoverable from any document — what the user actually wants right
  now, what changed in the world since the last session. When the
  implants don't have it, ask.
