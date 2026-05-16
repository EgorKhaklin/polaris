# meta/cognitive-architecture-v2.md — what changed and why (v8.5)

## v1 → v2 of the cognitive layer

The original cognitive layer (`meta/cognitive-loop.md`) defined an
opinionated architecture: MISSION as constitution, ROADMAP as backlog,
journal as episodic memory, DEVNOTES + patterns as semantic + procedural
memory. That structure is still right. v8.5 (this pass) extends it
with three meta-tools that solve specific friction the agent kept
hitting.

## What was hurting

| Pain point | Frequency | Friction per occurrence |
|---|---|---|
| Ceremony-heavy test runs (8 env vars + redis-up + venv path) | every code change | ~15 s typing + 10 s mental switching |
| Onboarding a fresh session (read MISSION + ROADMAP + bootstrap + status) | every session | 3-5 min |
| Broken cross-references after a reorg | every reorg + invisible until grep | ?? until caught |
| Stale test counts in docs | every release | drift accumulates silently |

## What v8.5 added

### `scripts/ai-prime.sh` — single-command session primer

Wraps `ai-bootstrap.sh --quick` + `ai-status.sh` + `ai-propose.sh 3` +
journal tail + `find -mtime -1` into a ≤80-line cohesive output. A
fresh session reads `CLAUDE.md`, runs `ai-prime.sh`, and is oriented
in ~30 seconds. The four sub-scripts still exist for when the agent
wants only one part.

Output blocks:
1. Header (date, OS)
2. Mission state — C1-C10 rollup + v1/v2 done-list count
3. Top moves — top 3 from propose, with risk class + score
4. Recent journal — last 5 decisions/learnings
5. Recently modified — files touched in last 24h
6. Suggested next — one-line recommendation

### `scripts/ai-test.sh` — one-shot test runner

Wraps the test ceremony. Auto-discovers a working python venv (checks
`POLARIS_TEST_PYTHON`, then repo-local venv, then the codex venv at
`/private/tmp/polaris-codex-venv312/bin/python`, then system python3).
Brings up redis on :6399 with a per-invocation pidfile so failures
don't leave stale state. Clears the admin lockout before running.
Tears down redis on exit via `trap`.

Three call shapes:
- `ai-test.sh` — full suite
- `ai-test.sh quick` — skip the slow concurrency/property tests
- `ai-test.sh ClassName.method` — single test by name

Output is a single line: `PASS  196 tests in 61.7s` or a 40-line
failure tail.

### `scripts/ai-link-check.sh` — proactive cross-reference validator

Scans every Markdown file for inline links and every code file for
relative-path string literals (the kind of comment header in `app.py`
that points at a sibling doc). Reports broken references with
file:line. Skips `journal/` (historical entries
legitimately reference old paths) and `CHANGELOG.md` at root (release
history can name old paths).

Two modes:
- `ai-link-check.sh` — human-readable report, exit 0 always
- `ai-link-check.sh --ci` — exit 1 on any broken link (for pre-commit /
  CI integration)

The v8.4 reorg moved 9 docs into `docs/` and updated 31 cross-references.
This script is the safety net for the next reorg.

## What v8.5 did NOT change

The core cognitive-layer architecture is unchanged:

- MISSION → constitution; ROADMAP → backlog; BACKLOG → unsorted candidates
- Risk-class system (LOW autonomous-eligible / MEDIUM propose-and-wait /
  HIGH explicit-approval) is unchanged
- DEVNOTES (semantic memory) + patterns (procedural memory) split
  is unchanged
- Journal as episodic memory, with ai-journal.sh appending entries,
  unchanged

What changed is the **interface** to that architecture, not the
architecture itself.

## What's still missing (next pass candidates)

These are real friction points but I'm not building them right now —
each is meaningful work that should be its own session:

- **Cache-buster automation** — content-hash-based `?v=` query strings
  on CSS/JS so the manual bump is gone. Would need either a build
  step or runtime computation.
- **Auto-promote journal entries to DEVNOTES** — `ai-reflect.sh` exists
  but doesn't recognize recurring patterns. Needs heuristics.
- **Pre-commit hook integration** — `ai-status.sh --ci` and
  `ai-link-check.sh --ci` in a git pre-commit. Currently no git hooks.
- **Active session-goal tracking** — a sub-file the agent writes at
  session start with the user's verbatim ask. Avoids losing track of
  intent when multiple goals stack up.

## Re-evaluation triggers

This document should be revisited when:

- A friction point in the table at the top moves out of the "every
  session" frequency category, OR a new pain point joins it.
- One of the v8.5 scripts becomes load-bearing for CI / pre-commit.
- The structure of the cognitive layer itself changes (new memory
  type, new risk class, new mission epoch).
- An observation accumulates in the journal that contradicts the
  v8.5 design rationale above.
