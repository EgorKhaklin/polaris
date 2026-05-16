# sanctum/ — strategic-consultation records

Each file in this directory is one Sanctum session: a structured record
of a strategic agent-operator consultation. The protocol is defined in
`meta/sanctum-protocol.md`; the entry/close script is
`scripts/ai-sanctum.sh`.

## Naming

`YYYY-MM-DD-<topic-slug>.md` — one session per file, named by date and
topic. The slug is lowercased and hyphenated (e.g.,
`2026-05-11-r11-1-multisig-transitional.md`).

## Lifecycle

```
ai-sanctum.sh open <topic>      →  OPEN     (§VI Decision empty)
                                    ↓
                                  VANTA writes Decision in chat
                                    ↓
                                  agent executes
                                    ↓
ai-sanctum.sh close <topic>     →  CLOSED   (§VI + §VII filled)
   --decision "..."                 ↓
   --outcome "..."                indexed in meta/sanctum-index.md
```

## When NOT to open a session

The Sanctum is reserved for strategic moments. Do NOT open one for:

- LOW-risk autonomous work (per `meta/autonomy-architecture.md`)
- Routine implementation following an approved Sanctum
- Status reports, journal entries, link-check fixes
- Tactical questions ("which file path?", "what's the test name?")
- In-session course corrections mid-task

The test: does VANTA need to step out of the flow and *decide*? If
yes, Sanctum. If no, regular work.

## What lives here vs the journal

- **`journal/`** — fact-capture, one-liners, dated by day, append-only.
- **`sanctum/`** — long-form decision-with-context, one per strategic
  matter, lifecycle-tracked.
- **`meta/sanctum-index.md`** — chronological index of closed sessions.

A Sanctum session typically produces *several* journal entries during
execution; the Sanctum is the structured precondition, the journal
captures the milestones.

## For new agents

If you're a future agent in a fresh session:

1. Read `meta/sanctum-protocol.md` for the WHAT.
2. Read `scripts/ai-sanctum.sh --help` for the HOW.
3. Read `meta/sanctum-index.md` for past sessions — the patterns that
   recur there are the ones the Polaris cognitive layer has
   internalized.
4. The v8.15–v8.18 ships (R11-6, R11-4, R11-2, R11-1) all went through
   *de facto* Sanctum loops before the protocol was named. Their
   canonical Sanctum records are in this directory, backfilled.
