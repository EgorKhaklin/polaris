# meta/cognitive-architecture-v3.md — full-spectrum cognitive pass (v8.6)

## What v8.6 added

v8.5 introduced `ai-prime.sh`, `ai-test.sh`, `ai-link-check.sh`
(documented in `cognitive-architecture-v2.md`). v8.6 is the broader
pass — six more meta-tools plus durable memory updates, addressing
every recurring friction the agent has surfaced across the v8.x
sessions.

| New tool | Solves | Frequency of pain |
|---|---|---|
| `ai-help.sh` | "which script does what?" — discoverability | every session |
| `ai-mission.sh` | re-grounding (and fixes a doc lie — MISSION.md claimed it existed) | every session start |
| `ai-test-counts.sh` | stale test counts in MISSION.md | every release |
| `ai-impact.sh` | reverse of link-check ("what depends on X?") | every refactor |
| `ai-cache-bust.sh` | manual `?v=vN` bumps on every visual edit | every CSS/JS change |
| `ai-snapshot.sh` | full state dump for handoff / long-context priming | rare but high-value |
| `ai-done.sh` | pre-ship 10-check sanity gate | every PR-shape change |

## Why these specific tools

I asked: what wasted my time across v8.0 through v8.5? The answer was
remarkably consistent — small repeated tasks that should be one
command but weren't:

- The cache-bust pattern (manual `?v=v8.2 → v8.3 → v8.4`) recurred on
  every visual edit
- "Which ai-* script does X?" required `ls scripts/ + open each`
- MISSION.md's test count silently drifted from 134 → 200+ across
  three releases
- "Before I rename this, what depends on it?" required ad-hoc grep
- Pre-PR checks were a mental list (test? journal? CHANGELOG?
  cache-bust? link-check?) and easy to skip steps

Each new tool is the smallest script that makes the corresponding
task one command.

## Tool-by-tool intent

### `scripts/ai-help.sh`
Index of every `ai-*` script with a one-liner pulled from the script's
own doc-comment. Four groups: onboarding & planning / working &
shipping / memory & introspection / snapshots & meta. `ai-help.sh
<name>` shows the full doc-block for one script.

### `scripts/ai-mission.sh`
The script MISSION.md had been claiming exists for months. Wraps
`cat MISSION.md` with optional sub-sections (`constraints`, `done`,
`isnot`, `is`, `why`). The `isnot` section is the most-forgotten part
— surfacing it as `ai-mission.sh isnot` is the fastest way to
re-ground when tempted to add money/authority/surveillance to the
schema.

### `scripts/ai-test-counts.sh`
Counts `def test_*` patterns across `polaris_web/test_*.py`, counts
SQL self-tests (`PERFORM _record(...)` invocations), compares to the
claim in MISSION.md item 7. `--update` rewrites the line.

Caught a 134 → 203 drift on first run plus 39 → 126 on the SQL side.

### `scripts/ai-impact.sh`
Inverse of `ai-link-check.sh`. Given a file or symbol, lists every
other file that references it. Crucial for scope assessment — pre-
v8.6 a "should I rename this?" question needed an ad-hoc grep
ceremony.

### `scripts/ai-cache-bust.sh`
Computes a SHA-256 prefix of each tracked static file, rewrites the
matching `?v=…` query string in the templates. Same content → same
hash → cache stays useful when nothing changed; different content →
different hash → forces refresh. Eliminates the manual bump that
recurred every visual edit through v8.2-v8.5.

### `scripts/ai-snapshot.sh`
Single self-contained Markdown document covering the full operational
state: constraints, done-list, roadmap, recent decisions, substrate,
file map, test counts, recently-modified files. Designed to fit in
≤8000 tokens — usable as a long-context primer or session handoff.

The companion to `ai-prime.sh`: prime is the 80-line quick-onboard,
snapshot is the 8000-token complete-picture.

### `scripts/ai-done.sh`
Ten-check pre-ship gate. Aggregates `ai-status` + `ai-link-check`
+ `ai-cache-bust` + `ai-test-counts` + journal-has-entry +
CHANGELOG-from-today + no-debug-code + no-stale-`?v=` + no-bare-doc-
refs. Single verdict: READY / READY-with-caveats / NOT-READY.

## Memory updates

### `DEVNOTES/known-gotchas.md`
Extended with five session-discovered patterns:
- d3 `enter.merge(sel).classed()` silent failures
- Browser cache + `?v=` query string nuances
- Postgres function-overloading after signature changes
- TIMESTAMP-without-zone vs `datetime.utcnow()`
- Backticks inside heredoc'd Python in `$( )` substitutions

These were each rediscovered painfully during v8.x. Codifying them in
known-gotchas means the next agent reads them in 30 seconds instead
of debugging for 30 minutes.

## What v8.6 deliberately did NOT do

- **Pre-commit / git hooks** — would tighten the loop further, but
  there's no git repo configured in this dev env, so no place to
  install them.
- **Cache-bust hash → URL hash for production** — the content-hash
  approach also makes server-side cache invalidation cleaner, but
  v8.6 only addresses the dev-time rebuild loop.
- **Auto-promote journal → DEVNOTES** — heuristic-heavy and still
  better done by hand; left for a future pass when there's enough
  signal to know what "promote" means.
- **Session-goal tracking** — at the end of v8.5 I considered a
  `meta/current-session.md` file the agent writes at start. Concluded
  that journals already serve this role: `ai-journal.sh start "..."`
  records the goal verbatim, and `ai-prime.sh` surfaces it.

## What "full spectrum" actually meant

The user asked for "full spectrum improvement." I read this as:
**every pain point I can name, fix the highest-leverage version of**.
Not "add 50 scripts" — the architecture's value is in coherence, not
volume. Each new tool is one command that replaces 5-30 seconds of
mental ceremony, run dozens of times per session.

The total surface added: 7 scripts (≈ 700 lines), 1 DEVNOTES
extension (≈ 100 lines), 1 architecture doc (this file). Multiplied
by per-session uses: hours saved per future session.

## Re-evaluation triggers

This document should be revisited when:

- Any ai-* script's intended pain becomes recurrent again — meaning
  the tool didn't actually solve the friction
- A new high-frequency friction emerges that none of the v8.6 tools
  address
- The cognitive layer gets a new memory type, risk class, or mission
  epoch
- One of the v8.6 tools needs to become load-bearing for CI / pre-
  commit

## Re-running the v8.6 build

If the cognitive layer ever needs to be re-bootstrapped from scratch:
all v8.6 scripts are self-contained, no dependencies between them
beyond bash + python3 + standard Unix tools. Each can be removed and
re-added without affecting the others. The architecture is composable
by intent.
