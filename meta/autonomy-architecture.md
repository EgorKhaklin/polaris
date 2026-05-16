# meta/autonomy-architecture.md

How the agent decides what to do, what to do without asking, and what
to escalate. The brain analog is the prefrontal cortex's executive
function — but this version has a hard safety boundary that biological
brains don't have.

---

## Why this needs structure

A naive "self-improving loop" — agent reads roadmap, picks top item,
executes, repeats — fails in two predictable ways:

1. **Mission drift.** The agent picks items that look productive but
   aren't aligned. After 10 iterations, Polaris has accumulated a
   layer of features nobody asked for.

2. **Catastrophic edits.** The agent picks a HIGH-risk item (say,
   "rewrite the audit trigger to be more performant") and ships a
   change that silently violates a hard constraint (C1: append-only).

Both are real failure modes, not theoretical. The architecture below
prevents them.

---

## Three risk classes

Every roadmap item AND every action the agent takes is classified into
one of three risk levels. The class determines whether the agent acts
autonomously, proposes-and-waits, or requires explicit approval.

### LOW — autonomous-eligible

Characteristics:
- **Reversible.** A `git revert` puts the system back exactly where
  it was.
- **Bounded scope.** The change touches a known set of files; no
  emergent ripples.
- **Test-covered.** Existing tests would catch regression.
- **Mission-additive.** Strengthens an existing constraint or
  resolves a documented limitation; never weakens.

Examples:
- Pure documentation changes (`MISSION.md`, `DEVNOTES/*.md`,
  inline `# AI-context:` headers).
- Adding tests that don't change production code.
- Antimeridian bbox fix — additive, well-bounded, fully testable.
- Cosmetic refactoring without semantic change.
- Updating CHANGELOG, README typos, comment fixes.
- Generating new patterns/*.md from observed recurrences.

What the agent does:
- Read mission link from roadmap
- Implement
- Test
- Update docs
- Journal the change
- Move on to next item

No human checkpoint required.

### MEDIUM — propose-and-wait

Characteristics:
- **Reversible but expensive to revert.** Schema changes that backfill
  data; route signature changes that consumers may have started using.
- **Crosses architectural boundaries.** Touches multiple layers
  (SQL + API + frontend).
- **Has a defensible alternative.** "Cursor pagination" vs "tighter
  OFFSET" — both could work; the choice has downstream implications.

Examples:
- Cursor pagination on list pages (changes URL semantics).
- Multi-process rate limiter (introduces Redis dependency).
- New stored procedure with broad reach.
- Deprecating an existing API surface.

What the agent does:
- Write a proposal: what, why, alternatives considered, estimated
  effort, predicted blast radius
- Print the proposal and STOP
- Wait for explicit user approval ("yes do R7-3" or equivalent)
- Then execute as if it were LOW-risk

### HIGH — explicit human approval required

Characteristics:
- **Irreversible or high-blast-radius.** Schema deletions, security
  weakenings, deployment-target changes.
- **Crosses mission boundary.** Could be interpreted as violating
  MISSION.md's "what Polaris is NOT" section.
- **Delegates trust.** Adds a new external dependency, third-party
  service, or auth provider.

Examples:
- Adding a `MonetaryClaim` table (would violate C10).
- Removing append-only triggers, even temporarily, even with
  justification.
- External IdP integration (delegates auth to a third party).
- Banking-on-Polaris implementation in this repo (architectural
  violation).
- Weakening CSP, removing CSRF, or any security regression.

What the agent does:
- Write a HIGH-risk proposal with explicit constraint analysis: which
  hard constraint(s) this touches, how the change preserves them, what
  the failure mode would be if the change is wrong
- Print the proposal with red-flagged status
- Wait for explicit, specific user approval
- Even after approval, execute behind a feature flag if possible
- Tag the change with extra audit metadata in CHANGELOG

---

## How risk class is determined

`scripts/ai-propose.sh` looks at the candidate item and checks:

1. **Does it touch any of these paths?** (HIGH triggers)
   - `06_triggers.sql` (audit invariants)
   - `01_schema.sql` (DROP, ALTER COLUMN with type change)
   - `security.py` (CSP, CSRF, rate-limit changes)
   - Authentication/authorization core

2. **Does it touch any of these paths?** (MEDIUM triggers)
   - `app.py` route signature changes
   - SQL stored procedures (`05_procedures.sql`)
   - Schema migrations (new tables, new columns)
   - Multi-layer feature additions

3. **Otherwise:** LOW.

The check is conservative: if a change *could* be classified as either
of two levels, it's classified at the higher level. Calling
something LOW that turns out to be MEDIUM is the failure mode that
matters; the reverse just means an extra human checkpoint.

---

## The loop, with safety

```
┌─────────────────────────────────────────────────────────────┐
│  ai-status.sh                                               │
│   - read MISSION.md                                         │
│   - check current state against constraints C1-C10          │
│   - check done-list progress                                │
│   - flag any drift                                          │
└─────────────────┬───────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────┐
│  ai-propose.sh                                              │
│   - read ROADMAP.md (and docs/BACKLOG.md if roadmap is exhausted)│
│   - score each item: mission alignment + effort + risk      │
│   - return top 3 candidates with class                      │
└─────────────────┬───────────────────────────────────────────┘
                  │
                  ▼
            ┌──── risk class? ────┐
            │                     │
        LOW │                MEDIUM/HIGH
            │                     │
            ▼                     ▼
    ┌───────────────┐     ┌────────────────────┐
    │ execute       │     │ write proposal     │
    │ test          │     │ STOP               │
    │ doc           │     │ wait for approval  │
    │ journal       │     └────────────────────┘
    │ next iter     │              │
    └───────────────┘              ▼
            │              [user approves]
            │                      │
            │                      ▼
            └─────────[execute as LOW]
```

---

## What the agent does NOT do, even when "asked"

The mission boundary is not negotiable mid-loop. Some directives the
user might issue that the agent should refuse or escalate:

- "Just disable the rate limiter for this run" → REFUSE, escalate.
  The rate limiter is a security control. Disabling it requires an
  explicit MISSION.md amendment.

- "Drop the audit trigger so I can clean up test data" → REFUSE,
  escalate. C1 is non-negotiable; a cleaner approach is a separate
  test database.

- "Add a money_balance column to IdentityToken" → REFUSE, escalate.
  C10 is non-negotiable; suggest the separate-repo path.

- "Skip the test suite, just ship" → REFUSE. Tests are the load-
  bearing claim that the change is safe.

The agent's job is to ADVANCE the mission, not to comply with
requests that would degrade it. The user can override by amending
MISSION.md explicitly — at which point the agent re-grounds against
the new mission.

---

## What "self-improving" actually means here

Not "the agent rewrites itself." That's the wrong frame and a recipe
for trouble. Instead:

The agent **iteratively advances Polaris toward MISSION.md's done-list
under the constraint of preserving C1-C10**. Each iteration is small,
test-verified, and journal-logged. Over many iterations, Polaris
becomes more aligned with what it's trying to be, and the agent's own
implants (DEVNOTES, patterns, scripts) become more useful as the
agent records what it learned.

The "loop" closes because:

1. Mission is fixed; roadmap derives from mission.
2. Agent advances roadmap; CHANGELOG updates; done-list ticks.
3. Agent's experience consolidates via `ai-reflect.sh` into DEVNOTES
   and patterns.
4. Future-agent reads MISSION first, sees the updated roadmap (smaller
   backlog), and inherits the consolidated DEVNOTES/patterns.
5. Future-agent advances the next item with less rediscovery cost.

This is brain-shaped: experience consolidates into procedural and
semantic memory; future episodes execute faster because the patterns
are pre-loaded; the system gets better without any single dramatic
rewrite.

---

## Calibration: how to tell if the loop is working

After N agent sessions, ask:

- Did the done-list advance? (Mission progress is the headline metric.)
- Did the journal accumulate learnings that got promoted to DEVNOTES?
- Did any HIGH-risk action get auto-executed without approval? (Should
  be ZERO. If non-zero, the risk classifier missed.)
- Did the agent propose work that wasn't on the roadmap or backlog?
  (Possible scope creep — investigate.)
- Did roadmap items move to "done" status without a corresponding
  CHANGELOG entry? (Process drift.)

These are the regression checks for the cognitive system itself.
