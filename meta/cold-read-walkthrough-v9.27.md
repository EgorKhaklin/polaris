# Cold-read walkthrough — v9.27 / T7#7

**Origin:** BIG MISSION Tier 7 Sanctum (`sanctum/2026-05-16-tier-7-8-thesis-test-and-freeze-line.md`), item #7.
**Status:** Self-evaluation. **Acknowledged limitation:** I am the
agent that built v9.10-v9.26. I cannot honestly simulate a fresh
session; I have full context. This document errs toward finding
intervention points, not toward proving the thesis. The actual
cold-read test requires an external party reading only CLAUDE.md +
the invariants from a fresh process.

---

## The contained feature

**Spec (the level CLAUDE.md + invariants would expose):**

> Add a new structural invariant that pins the `meta/swarm-mttr.json`
> schema_version field to exactly "v9.25" (the schema's first version).
> This catches accidental schema_version mutation that would invalidate
> downstream trend computation.

Small. Single-file change. LOW-risk per the autonomy architecture.
No new arc; no Sanctum required.

---

## Honest walkthrough — what would a fresh agent do

### Step 1: read CLAUDE.md

A fresh agent opens CLAUDE.md. It says: "For per-task scripts:
`./scripts/ai-test.sh`". OK, agent knows how to test.

CLAUDE.md mentions "structural invariants" in the loop-wiring section
but does NOT explicitly say HOW to add a new invariant. Agent has to
infer from existing patterns.

**Intervention point #1:** CLAUDE.md does not tell the agent the
TestWave naming convention. A fresh agent reading the file would
either grep `test_structural_invariants.py` to discover the pattern
OR ship under a different convention. I (the current agent) know
the pattern by session-memory.

### Step 2: identify the test class to add to

A fresh agent opens `polaris_web/test_structural_invariants.py`. The
file is ~13,000 lines. Agent has to find: "what's the current latest
TestWave class? Should I add to it or create a new one?"

CLAUDE.md does NOT say "every new ship gets its own TestWaveNN_VNNN
class." A fresh agent might add the test to TestWave26V926 (the
most-recent) without realizing the convention is "one class per
ship version."

**Intervention point #2:** CLAUDE.md doesn't document the
"one-TestWave-per-ship" convention. Fresh agent could easily violate it.

### Step 3: write the test

Agent writes a test:

```python
def test_mttr_schema_version_is_v9_25(self):
    import json
    with open('meta/swarm-mttr.json') as f:
        ledger = json.load(f)
    self.assertEqual(ledger.get("schema_version"), "v9.25")
```

The agent ran it from where? CLAUDE.md doesn't pin the cwd
expectation. The path "meta/swarm-mttr.json" is relative — relative
to what?

**Intervention point #3:** Path-resolution convention. Existing tests
use `self.ROOT` + `os.path.join`. A fresh agent might not discover
this and would file an absolute-path-bug.

### Step 4: bump version

A fresh agent has added a test. Does the version need to bump?

CLAUDE.md says: "**Current version:** v9.24". It doesn't say "bump
on every ship." It doesn't say "ships are tagged by version." A
fresh agent might add the test, run the suite, and conclude "done"
without touching `__version__.py`.

**Intervention point #4:** CLAUDE.md doesn't say WHEN to bump the
version. Pre-commit hook (scope-check) doesn't catch this. ai-done.sh
might catch via a check, but a fresh agent might not run ai-done.sh
(CLAUDE.md says it exists but doesn't enforce running it).

### Step 5: CHANGELOG

Does the change need a CHANGELOG entry? CLAUDE.md says: "**What just
shipped?** → CHANGELOG.md (curated last 10 ships)". So fresh agent
might infer "I should add an entry." But what shape? Length? Where
in the file?

**Intervention point #5:** CHANGELOG entry format is undocumented in
CLAUDE.md. Fresh agent has to infer from existing entries.

### Step 6: journal

CLAUDE.md says: "Capture decisions during the session: `./scripts/ai-journal.sh`"
but doesn't say "every ship needs a journal entry." Fresh agent might
skip.

**Intervention point #6:** Journal entry convention is implicit.

### Step 7: scorecard

CLAUDE.md doesn't mention `polaris-swarm-scorecard.sh append <version>`
as a per-ship requirement. Fresh agent never runs it. The scorecard
silently drifts out of sync.

**Intervention point #7:** Scorecard append is invisible to a fresh
agent. The cognitive layer's load-bearing metric goes stale.

### Step 8: ai-done.sh

Even if the fresh agent finds ai-done.sh in CLAUDE.md and runs it,
the agent won't know that the structural-invariant gate (step 14)
requires a journal/hydra brief to exist within the last day. A fresh
agent who just adds a test + runs `./scripts/ai-done.sh` might get
either a NOTE (no recent brief) or a misleading READY when nothing
about the swarm has been exercised.

**Intervention point #8:** Pre-ship gate dependencies (HYDRA brief
freshness; scorecard freshness; MTTR ledger updates) are not
documented as a single "ship sequence."

### Step 9: pre-commit scope hook

The scope-check might fail if the new test class adds too much
narrative mass. Fresh agent gets the failure and might respond by
either trimming the test docstring (correct) OR running
`pre-commit-scope-check.sh --rebase-baseline` (incorrect — that
moves the goalposts).

**Intervention point #9:** Scope-rebase is a load-bearing decision
(adding narrative or rebasing-after-intentional-shift). CLAUDE.md
doesn't say "rebase ONLY after a Sanctum decision." Fresh agent
could silently inflate the budget.

### Step 10: deciding the work is done

Even with all gates passing, when does the fresh agent know it can
stop? CLAUDE.md doesn't have a "definition of shipped." A fresh
agent might over-elaborate, under-deliver, or stop too early.

**Intervention point #10:** Definition-of-shipped is implicit; the
fresh agent has no mechanical "this is done" check at the work-item
level (vs ai-done.sh which is the pre-ship gate).

---

## Summary

**10 intervention points** in a single contained-feature ship. Every
one is a place where my session-context fills a gap that CLAUDE.md
does not.

**Reading the evidence honestly:**

- The thesis ("LLM-driven cognitive layer can maintain a code
  substrate without operator-as-persistence") is FALSE today at the
  rule-completeness level — 10 of 10 ship steps require knowledge
  not in CLAUDE.md.
- The 10 interventions are mostly INFRASTRUCTURE-shape (conventions
  like TestWave naming, version bump, CHANGELOG format), not
  VALUE-shape (the feature itself was correctly conceived from the
  spec). The thesis isn't refuted — but the runbook is incomplete.
- The agent CAN do this work because session memory closes the gap.
  An external engineer reading CLAUDE.md cold cannot.
- T7#8 must convert as many of these 10 into CLAUDE.md rules as
  possible, then honestly name what can't be converted.

The walkthrough is a self-evaluation. **The real cold-read remains
the unconducted test.** This document is the candidate-rules
preparation; it is not evidence the thesis works.

---

*Per BIG MISSION Tier 7 Sanctum 2026-05-16, item #7. Self-evaluation
limitation acknowledged in §preamble.*
