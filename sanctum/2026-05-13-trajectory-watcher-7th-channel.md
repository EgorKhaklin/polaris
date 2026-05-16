# Sanctum: trajectory-watcher-7th-channel

**Date:** 2026-05-13
**Petitioner:** agent (Claude, Opus 4.7)
**Principal:** VANTA
**Trigger:** structural change to the cognitive layer — expands the
HYDRA registry from 6 to 7 watchers and amends MISSION.md's
"cognitive substrate" section enumeration. MEDIUM-risk per
`meta/autonomy-architecture.md`; same shape as v8.43's HYDRA
constitutional integration. Triggered by VANTA's "proceed with
recommendation" on the Architect's StrategicAdvisor-feedback
analysis (recommended shape A: TrajectoryWatcher as 7th HYDRA
watcher).
**Risk class:** MEDIUM
**Status:** CLOSED
**Architect brief ID:** n/a — structural (inline analysis in §III)

---

## I. The Matter

The Architect was asked for feedback on a "StrategicAdvisor"
proposal (separate component or Strategic Council). The analysis
found that the proposal would duplicate ~80% of what Architect +
HYDRA already do, and that the genuine 20% gap is
**trajectory-drift detection** — pattern signals over the recent
shipping history that no current watcher surfaces:

- ship-rate anomalies (mission creep / stagnation),
- repeated parking of the same items (avoidance),
- file-churn clusters (rework / scope creep).

The Architect recommended shape A: a 7th HYDRA watcher named
**TrajectoryWatcher**, fitting the existing watcher contract
(read-only, deterministic, graceful-failure) and substitutable per
v8.30.

VANTA must decide **whether to expand the HYDRA registry from 6 to
7 watchers, and if so under what scope.**

## II. Preparation

- **Architect brief:** the StrategicAdvisor feedback analysis was
  delivered inline in chat before this Sanctum. It surveyed 7
  existing mechanisms that already cover macro-strategic
  reasoning (HYDRA, Architect persona, Sanctum protocol,
  `ai-propose.sh`, `ai-prime.sh`, iteration protocol, `--reflect`
  mode) and identified the trajectory-drift gap as the unique
  20%.
- **Proposal draft:** none required (structural change; scope is
  one new watcher file + one MISSION.md sentence + one structural
  test).
- **Alignment audit:**
  - **v8.30** — cognitive-substrate elevation. Established that the
    constitutional layer names principles, not implementations.
    The implementation list (currently including HYDRA + 6
    watchers) is substitutable. Adding a 7th watcher is not a
    principle change; it is an implementation extension to the
    same substitutable list.
  - **v8.37** — Arc D opening. Authorized H1–H8 (HYDRA host +
    5 watchers + constitutional integration). Arc D scope was the
    initial 6 watchers; this 7th watcher is **outside Arc D**, hence
    needs its own authorization.
  - **v8.43** — HYDRA constitutional integration. Named the 6
    watchers in MISSION.md's cognitive-substrate section with the
    substitutability qualifier ("A future agent may replace the
    HYDRA swarm with a different synthesis pattern without
    amending this section, provided the four principles still
    hold"). Adding a 7th watcher does not replace the swarm; it
    extends it. The enumeration ("six watchers (schema, cognitive,
    security, mission, adversary, performance)") needs the
    smallest possible textual update (six → seven, comma-add the
    new name).
  - **v8.31** — post-v2 steady state. Default posture is
    decline-and-surface. This ship was triggered by VANTA's
    explicit go on the Architect's recommendation, which counts
    as the operator-authorization mechanism the contract
    contemplates for MEDIUM-risk work.
- **Blast radius (if approved as recommended):**
  - `polaris_hydra/watchers/trajectory_watcher.py` — new file,
    new class `TrajectoryWatcher(Watcher)`. Read-only,
    deterministic, graceful-failure (the contract enforced by
    v8.44 G1–G5 guards).
  - `polaris_hydra/watchers/__init__.py` — +1 import / +1 export.
  - `polaris_hydra/host.py` `ALL_WATCHERS` dict — +1 entry
    `"trajectory": TrajectoryWatcher`.
  - `MISSION.md` cognitive-substrate section — "six watchers" →
    "seven watchers", comma-add `trajectory`. Cross-reference
    updated to point at this Sanctum + the v8.43 antecedent.
  - `polaris_web/test_structural_invariants.py` — +1 class
    `TestTrajectoryWatcher` (3–5 soft-check tests for file exists
    + report shape + registry inclusion + 7-watcher count).
  - `CHANGELOG.md` — v8.49 entry.
  - `CLAUDE.md` — state-map row.
  - `ROADMAP.md` — no new R-id (this ship is outside Arc D and is
    not a new arc; it's a post-arc extension to existing
    substrate). Optional: a brief retrospective entry referencing
    this Sanctum.
  - `journal/2026-05-13.md` — decision + outcome.
- **Tests planned:** +4 to +5 structural-invariant tests.
  Target: 95 → ~100. Includes a count-pin test
  (`test_hydra_registry_has_seven_watchers`) that pins the new
  expected count, making any future addition explicit.
- **What's NOT changed by this ship:**
  - No constitutional principle changes. The four named
    principles (Sanctum, AoR, risk classes, CM) are untouched.
  - No watcher contract change. TrajectoryWatcher honors the same
    read-only / deterministic / graceful-failure shape as the
    existing 6 + the v8.44 G1–G5 guards.
  - No new Architect-voice surface. TrajectoryWatcher reports
    structured findings to HYDRA host; the host synthesizes (LLM
    or deterministic) as it does for the other 6.

## III. Alternatives considered

### A. Ship TrajectoryWatcher as 7th HYDRA watcher (recommended)

**Move:** new watcher file + registry entry + MISSION.md
six→seven update + structural tests. Three channels:

1. **Ship-rate analysis.** Parse `CHANGELOG.md` for recent version
   headers; compute the inter-ship wall-clock gap distribution
   over the last N=10 entries. Flag if any of:
   - 3+ ships in <2 hours → mission-creep warning,
   - 0 ships in 7+ days when prior cadence was higher → stagnation
     warning.

2. **Parking-pattern detection.** Scan the last N CHANGELOG
   entries for "surfaced but parked" / "still parked" /
   "deferred" / "park" tokens; cluster items that recur across
   ≥3 ships. Flag if any item parked 3+ times without closure
   (the avoidance signal).

3. **File-churn cluster.** `git`-or-mtime-based check (filesystem
   mtime fallback since the repo may or may not have `.git/`):
   files modified ≥4 times in the last 24 hours. Flag if any
   single file dominates recent churn (rework / scope-creep
   signal).

**Pro:**
- Fits the existing pattern exactly (push-not-pull,
  deterministic, graceful-failure).
- Substitutable per v8.30: future agents can replace the
  trajectory pattern without amending the constitution.
- Closes the genuine 20% gap the Architect identified.
- Runs only when HYDRA runs (operator-invoked or end-of-ship);
  no decline-and-surface posture violation.
- Smallest constitutional surface area consistent with extending
  the substrate.

**Con:**
- MISSION.md enumeration is now seven instead of six. Future
  additions will keep extending this list; eventually it should
  either bound (count-pin via structural test, already planned)
  or be referenced indirectly (e.g., "the watchers in
  `polaris_hydra/watchers/`" — but that's a separate
  amendment, not in this ship's scope).
- Each new channel adds ~0.1–0.5s to a HYDRA sweep depending on
  CHANGELOG size and filesystem mtime walks. Acceptable for now
  (current sweep is ~1.2s with 6 watchers).

**Verdict:** recommended.

### B. Extend `ai-architect.sh` with `--strategic` mode

**Move:** add a flag that asks the Architect to surface
trajectory questions without HYDRA involvement. Operator invokes
on demand; output is prose, not structured findings.

**Pro:** lighter constitutional surface (no registry change, no
MISSION.md amendment); operator-controlled timing.

**Con:** loses the "every HYDRA pass surfaces drift signals"
property; doesn't integrate with the structured `WatcherReport`
flow that other tooling can consume; trajectory signals are best
expressed as drift/alert findings, not prose. Also doesn't satisfy
the v8.30 separation: Architect is the *voice*, HYDRA is the
*observation surface*. Trajectory drift is observation, not voice.

**Verdict:** rejected. Wrong layer.

### C. Codify the iteration protocol as a structural invariant

**Move:** add a structural-invariant test asserting "every recent
CHANGELOG entry's tail mentions the next recommendation."

**Pro:** lightest possible change; pins the runtime convention
this conversation has established.

**Con:** doesn't address trajectory drift; only addresses the
*end-of-ship-pivot* pattern which is already happening reliably.
The named felt need is trajectory-level (across multiple ships),
not per-ship.

**Verdict:** rejected. Addresses a different (and largely already-
solved) problem.

### D. Do nothing; reject the StrategicAdvisor idea entirely

**Move:** mark "no action; Architect + HYDRA + iteration protocol
are sufficient."

**Pro:** maximally conservative; preserves the 6-watcher
enumeration verbatim.

**Con:** leaves the trajectory-drift gap unaddressed. The
Architect's analysis surfaced this as a real 20% gap, not a fake
one. The first time the ship cadence becomes a problem
(over-shipping → mission creep, or under-shipping → stagnation),
no surface will catch it.

**Verdict:** rejected. The gap is real and the cost of addressing
it via shape A is small.

## IV. Recommendation

**Option A — ship TrajectoryWatcher as HYDRA's 7th watcher.**
Three channels (ship-rate analysis, parking-pattern detection,
file-churn cluster). Read-only / deterministic / graceful-failure
contract preserved. MISSION.md updated minimally
("six watchers" → "seven watchers", comma-add `trajectory`).
Four to five structural-invariant tests including a count-pin
on the 7-watcher registry.

**Verification path post-ship:**
1. TrajectoryWatcher reports `healthy` on the current corpus
   (likely with one drift signal: the last 22 ships happened in
   ~36 hours, which is exactly the mission-creep signal this
   watcher should flag — surfacing it is the point).
2. HYDRA smoke shows 7 watchers reporting.
3. Structural-invariant count goes from 95 to ~100.
4. ai-link-check + ai-meta + Sanctum integrity all stay green.

### Specific MISSION.md amendment text (preview)

Currently (post-v8.43):

> The HYDRA swarm (`polaris_hydra/`) and its six watchers
> (schema, cognitive, security, mission, adversary, performance)
> are the operative synthesis implementation, also substitutable
> under the same principle: a future agent may replace the HYDRA
> swarm with a different synthesis pattern without amending this
> section, provided the four principles still hold.

Proposed amendment:

> The HYDRA swarm (`polaris_hydra/`) and its seven watchers
> (schema, cognitive, security, mission, adversary, performance,
> trajectory) are the operative synthesis implementation, also
> substitutable under the same principle: a future agent may
> replace the HYDRA swarm with a different synthesis pattern
> without amending this section, provided the four principles
> still hold.

Substitutability clause preserved verbatim. Only the count and
the comma-list change.

## V. What's needed from VANTA

**One decision:**

- **Option A (recommended)** — ship TrajectoryWatcher; six→seven;
  three channels as specified.
- **Option B** — extend `ai-architect.sh` instead.
- **Option C** — codify iteration protocol instead.
- **Option D** — do nothing.
- **Other** — name a different shape.

VANTA's prior "proceed with recommendation" on the Architect's
chat-surface analysis named Option A as the recommended shape.
This Sanctum is the formal record of that decision; presenting it
here for the audit-of-record + explicit acknowledgment per the
Sanctum protocol.

## VI. Decision

Proceed with recommendation (Option A — TrajectoryWatcher as 7th HYDRA watcher). VANTA's chat-surface approval on the Architect's StrategicAdvisor-feedback analysis is the §VI decision; this Sanctum is the audit-of-record artifact.

## VII. Outcome

Shipped as v8.49. polaris_hydra/watchers/trajectory_watcher.py created with three channels (ship-rate analysis, parking-pattern detection, file-churn cluster). Registered in __init__.py + ALL_WATCHERS. MISSION.md cognitive-substrate section amended (six watchers → seven; trajectory added to comma-list; Sanctum cross-reference). TestTrajectoryWatcher class added with 5 tests including 7-count pin + G3 read-only contract test (95 → 100). HYDRA registry = 7; first-run TrajectoryWatcher fires expected drift signal (9 ships on 2026-05-12 exceeds burst threshold — exactly the mission-creep signal the watcher is designed to surface). v8.30 substitutability principle preserved verbatim.

**See:** [CHANGELOG `## v8.49 (TrajectoryWatcher H7)`](../CHANGELOG.md) · [`journal/2026-05-13.md`](../journal/2026-05-13.md). Cross-ref added v8.61 per Architect-reflection finding.
