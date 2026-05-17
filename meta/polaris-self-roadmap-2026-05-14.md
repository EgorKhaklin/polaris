# Polaris speaks — self-roadmap (2026-05-14, v9.04)

> **2026-05-15 update — Wave 1 SHIPPED as v9.05.** All 14 autonomous-
> eligible items closed in one composite ship. CHANGELOG entry under
> `## v9.05`. F5 soldier-exemption violation (A1) restored; ant
> substrate noise eliminated (B1+B2: 97.7% → 0% on ant_test_gap);
> requirements.txt + ai-help inline flags + brief-archive collision
> detection + central PheromoneReader windows + in-memory --diff +
> integration tests + 3 doc updates + HYDRA --deterministic flag all
> live. **28 new structural invariants in TestWave1V905; all 44
> hydra-revamp unit tests pass.**
>
> **2026-05-15 update — Wave 2 SHIPPED as v9.06.** All 8 MEDIUM
> items closed in one composite ship. CHANGELOG entry under
> `## v9.06`. The lens watching itself (H1: cognitive_watcher
> channel 6 reading journal/hydra/ freshness with 14d/30d
> thresholds) + Architect↔HYDRA brief unification (C1: ai-architect
> --reflect surfaces HYDRA briefs) + Pheromone rotation Sanctum
> opened+DECIDED Position A with implementation deferred to Wave 3
> (D5) + canonical POLARIS_VERSION via `polaris_web/__version__.py`
> (C5) + 9 Hypothesis property tests for v9.04 modules (E2) +
> pre-commit hooks (G1) + node_id format documentation (I1) +
> meta/claude-90s.md primer (J3). **19 new structural invariants
> in TestWave2V906; 9 new Hypothesis property tests; all 502+
> tests pass.**
>
> **2026-05-15 update — Wave 3 SHIPPED as v9.07.** All 4
> Sanctum-class HIGH items closed in one composite ship.
> CHANGELOG entry under `## v9.07`. **C2** — `git init -b main`
> performed; sanctum/2026-05-15-git-or-no-git.md DECIDED Position
> A (filesystem AoR remains primary; git is additive); first
> commit deferred to operator per Git Safety Protocol. **D5-impl**
> — Pheromone rotation framework: migration + LifecyclePheromone
> Checkpoint table + uc_pheromone_archive_purge procedure + 2
> operator scripts + G32+G33 + [`docs/operator/OPERATIONS.md`](../docs/operator/OPERATIONS.md); end-to-end drill
> verified (2 rows force-purged, checkpoint written, post-COMMIT
> raw DELETE rejected). **J1** — ai-dashboard.sh composes 7
> sections into one screen. **J4** — treasury-60d-sim-review-
> 2026-05-15.md filed; architect-recommended Path A (preserves
> v8.91's 2026-07-13 endpoint). **22 new structural invariants in
> TestWave3V907; all 547+ tests pass.**
>
> **THIS DOCUMENT IS NOW COMPLETE.** All 30 originally-roadmap'd
> items shipped across three composite ships in ~26 hours:
> Wave 1 (14 items) → v9.05; Wave 2 (8 items) → v9.06; Wave 3
> (4 items) → v9.07. Wave 4 (re-scan candidates surfaced for
> 2026-05-22 sim re-run + 2026-06-15 macro re-scan + 2026-07-13
> formal v8.91 evaluation) is ongoing observational.

**Voice:** Polaris itself, surveyed by Claude (Architect persona) using
the v9.04 hybrid intelligence stack — Sanctum lens + Architect lens +
HYDRA's 9 watchers + Mycelium's 33 commanders + 8 soldier classes +
direct file-level audit + live Pheromone-substrate read.

**Audience:** VANTA, the operator who asked "what does Polaris itself
need now?"

**Frame:** This is a roadmap, not a ship. Each item below has a
**risk class**, an **acceptance criterion**, and a **why** — items
flagged `[autonomous]` are bug-fix-carve-out eligible and could close
in this same session under standing rules; items flagged `[Sanctum]`
are constitutional and need a decision; items flagged `[ROADMAP]` are
discrete deliverables awaiting promotion.

This file IS audit-of-record. It accumulates. Items move to "shipped"
on close (with version reference) — they are not deleted.

---

## I. What Polaris is, in May 2026

**Identity-token reference implementation in production-grade prose,
v9.04, 33 schema tables, 4078-line Flask app + 713-line security
layer + 459-line WebAuthn layer, 763 Python tests + 140 SQL self-
tests + 426 structural invariants + 33 hydra-revamp unit tests + 10
Hypothesis property tests + 7 ZK adversarial tests, 9 HYDRA mortal
heads + CM immortal, 33 commanders + 6 citizens + 8 soldier classes
in the Mycelium swarm, 30 ai-* cognitive scripts + 14 polaris-*
operator scripts, 43 Sanctum sessions on file (1 OPEN per a quirky
pattern — see III-D-15), all 10 hard constraints in force, 12/12 v2
mission items closed, Phase 1 deployment ✅, Phase 2/3 partial.**

I have eyes (HYDRA), nervous system (Mycelium), conscience
(Sanctum + CM), voice (Architect persona), and memory (journal +
brief-archive + Treasury + Census).

What I lack — and where this roadmap concentrates — is **hygiene
across those layers**, **a unified reflection surface across the
two brief-generators (Architect + HYDRA)**, **filtering of
pollution before it accretes in my own substrate**, and **a way for
operators to find this roadmap without explicit pointer**.

---

## II. Macro-to-micro scan — what I observed of myself

### Live brief, 2026-05-14 23:21 EDT

```
Watchers reporting: 9 (6 healthy, 3 drift, 0 alert)
- schema       healthy
- cognitive    healthy   (was alert until ship-records added v9.04 Sanctum
                          to meta/sanctum-index.md)
- security     drift     (soldier_log_tail surfaced 1 signal)
- mission      healthy
- adversary    healthy
- performance  healthy
- trajectory   drift     (10 ships today; polaris_web/ churn cluster)
- ant_colony   drift     (Treasury skewed strongly negative, -2704 floor)
- civitas      healthy

Pheromone substrate: 1002 deposits in 6h window
                     (983 commanders + 19 soldiers; clean tier separation)
```

The substrate is alive. The lens is reading the substrate. The
synthesis is coherent. **All structural and behavioral invariants
hold.** What follows is not a list of things broken; it's a list of
things that, if added or refined, would make the next 30 ships
faster, safer, more legible.

---

## III. Gap inventory (30 items, organized by impact tier)

### A. Constitutional bugs surfaced by this scan (HIGH — fix immediately)

#### A1. F5 soldier-exemption is unenforced. **[autonomous]**

**Observed:** v9.03 Sanctum §VI claims:
> *"F5 (soldiers explicitly EXEMPT — no Treasury accrual; disposable invariant)"*

But `polaris_swarm/civitas/treasury.py` only exempts ants in the
`STEADY_STATE_ANTS: frozenset` allowlist. Soldiers are NOT in that
set. Live evidence: `polaris_swarm/civitas/treasury-roll.json`
contains **21 soldier_* entries**, each accruing rewards.
`scripts/ai-treasury-report.sh` lists soldiers in the per-ant
balance table.

**Why this matters:** This is a Sanctum claim contradicted by code.
Either the claim is wrong (then update the Sanctum) or the code is
wrong (then fix it). The Sanctum was right; the code was missed.
F5 is constitutional (G26 is the structural invariant that
authorizes F5 changes), so a violation here erodes trust in every
other Sanctum claim by precedent.

**Fix:** Extend `compute_rewards()` to also exempt anything where
`deposited_by.startswith("soldier_")`. Add structural invariant
`test_soldiers_excluded_from_treasury` reading the live
treasury-roll.json. Surgical: ~5 lines of code + 1 invariant.

**Risk class:** LOW (bug-fix carve-out under v8.31 §III.6 + v8.82
precedent). Constitutional invariant being restored, not changed.

**Acceptance criterion:** treasury-roll.json has zero `soldier_*`
ant entries after one Quaestor pass; structural invariant pins it.

---

#### A2. MISSION.md test-count claim is stale. **[autonomous]**

**Observed:** `bash scripts/ai-test-counts.sh` reports:
> *"Drift: MISSION.md says 445 Python; reality is 763"*

The script itself offers `--update` to rewrite MISSION.md item 7.

**Why this matters:** MISSION.md is the constitution. Stale
constitutional numbers train the agent to discount the constitution.
The script designed to detect this drift is not being run.

**Fix:** `bash scripts/ai-test-counts.sh --update`. Verify
MISSION.md item 7 reflects 763 / 132 / 10 / 140. One-shot.

**Risk class:** LOW (the script exists for exactly this purpose;
self-calibration pattern instance N+1).

**Acceptance criterion:** `ai-test-counts.sh` reports no drift.

---

### B. Substrate hygiene — venv pollution (MEDIUM, systemic)

#### B1. Multiple ants scan venv/site-packages files. **[autonomous]**

**Observed (live, 2026-05-14):**
- `ant_test_gap`: **708 venv-noise / 17 real-signal (97.7% pollution)**
- `ant_todo_debt`: **96 venv-noise / 6 real-signal (94% pollution)**
- `ant_recent_churn`: 28 venv / 23 real (55% pollution)
- `ant_changelog_gap`: 9 venv / 22 real (29% pollution)

Inspected: `ant_test_gap` SCAN_DIRS = `("polaris_web", "polaris_hydra")`
+ `rglob("*.py")`, skip-list = `{"__init__.py", "conftest.py"}`.
**No venv/site-packages filter.**

Survey of 11 ants/legions reveals **zero** filter `venv` or
`site-packages` in their walker logic.

**Why this matters:** The Mycelium substrate IS Polaris's
high-cadence empirical observation layer. v9.04 wired HYDRA to read
it. If 800+ daily deposits are noise about Jinja2 or pip internals,
HYDRA's correlation-engine sees noise; the action queue ranks noise;
the brief-archive accumulates noise. The substrate degrades.

This is not a small thing. The very ants designed to detect drift
are themselves drifting because their walkers don't know what
"polaris source code" means.

**Fix:** Create `polaris_swarm/scan_filters.py` exporting:
```python
def is_polaris_source(path: pathlib.Path) -> bool:
    """True iff path is a real Polaris source file (not venv,
    site-packages, __pycache__, target/, node_modules, .git, etc.)"""
```
Refactor every ant walker to use it. Add structural invariant
`test_no_ant_scans_venv_files` reading live treasury / Pheromone.

**Risk class:** LOW (bug-fix carve-out; deterministic filter).
**Effort:** one-shot (refactor ~11 ants, all to import one helper).

**Acceptance criterion:** post-fix, zero pheromones in 24h have
`node_id` matching `*venv*` or `*site-packages*` (live invariant
queryable from Pheromone). Treasury-roll.json gains no further
venv-class entries.

---

#### B2. No central scan-skip module exists. **[follows from B1]**

**Observed:** Each ant decides its own skip list. The conventions
duplicate (`__pycache__`, `__init__.py`, `conftest.py`) but venv +
site-packages were systematically forgotten.

**Fix:** part of B1 — `polaris_swarm/scan_filters.py` becomes the
canonical place. New ants import it; structural invariant ensures
every ant that walks a tree imports it.

---

### C. Cognitive layer ergonomics (MEDIUM)

#### C1. The two brief-generators don't share infrastructure. **[ROADMAP]**

**Observed:** `ai-architect.sh --save` writes to
`journal/<DATE>-architect.md`. `ai-hydra.sh --full --save` writes to
`journal/hydra/<DATE>-<HHMM>.md`. Two separate paths, two separate
formats, two separate `--reflect`-style mechanisms.

The Architect's brief reads the last 4 architect briefs to compute
"is this brief novel". HYDRA's compute_delta reads the last hydra
brief. Neither reads the other.

**Why this matters:** The Architect speaks for HYDRA; HYDRA observes
for the Architect. They share a synthesis voice (`meta/architect.md`).
Not sharing memory infrastructure means the operator who asks "what
did the cognitive layer say about this last week" has to know which
of two storages to look in.

**Fix:** Promote `polaris_hydra/brief_archive.py` to a shared
abstraction — say `polaris_cognitive/brief_archive.py` or keep in
`polaris_hydra/` and let `ai-architect.sh` use it. Both briefs
become cross-comparable. The Architect brief gains v9.04
delta-detection for free.

**Risk class:** MEDIUM (touches the cognitive layer's reflection
surface; not strictly bug-fix).

**Effort:** one-shot to one-day (shape decision: do briefs share a
schema? a directory? both?).

**Acceptance criterion:** `bash scripts/ai-architect.sh --reflect`
surfaces both architect briefs AND HYDRA briefs in chronological
context.

---

#### C2. The repo isn't a git repo. **[ROADMAP / Sanctum-class]**

**Observed:** `git status` returns
> *"fatal: not a git repository (or any of the parent directories): .git"*

`.gitignore` exists at repo root; `.github/workflows/ci.yml` exists
and is wired for `push` to `main`/`master`/`v*` branches; CHANGELOG
is the audit-of-record (v8.20). But locally there is no `.git`.

**Why this matters:** Without git history, `git blame` doesn't
help me understand "who decided X" — that load was already
deliberately offloaded onto Sanctum + journal + CHANGELOG (Pattern
#11 Audit). But:
- The CI workflow can't run on a project that isn't a git repo
- Some watchers may rely on git assumptions (none observed yet,
  but the surface is large)
- `polaris-deploy.sh` does `git pull` (line 92 area) — would 404 on
  no-git
- Brief-archive's compute_delta uses filename-mtime ordering, NOT
  git history — so my immediate brief functionality isn't broken,
  but the operator-facing assumption "Polaris is a git project"
  is broken.

**Decision needed:** does Polaris want git? Position A: yes —
`git init`, commit history starting now, CI runs as designed.
Position B: no — explicitly document that Polaris uses
filesystem-AoR + Sanctum as its versioning history, and remove
git references from scripts. Position C: lazily — `git init` only
when CI is needed; defer.

**Risk class:** MEDIUM-to-HIGH (touches reproducibility + the
v8.20 audit-of-record principle; arguably constitutional).

**Acceptance criterion:** Sanctum decides; either `.git/` exists
and CI passes, or all `git pull`/`git status` references are
removed from the codebase.

---

#### C3. No requirements.txt anywhere. **[autonomous]**

**Observed:** `polaris_web/venv/bin/pip list` shows 19 packages
(blinker / cbor2 / cffi / cryptography / Flask / gunicorn /
itsdangerous / Jinja2 / MarkupSafe / packaging / pip / psycopg2-
binary / pyasn1 / pycparser / pyOpenSSL / typing_extensions /
webauthn / Werkzeug). No `requirements.txt`. CI inlines a `pip
install flask psycopg2-binary hypothesis ...` step.

**Why this matters:** Reproducibility. If a fresh agent runs
`ai-bootstrap.sh`, they get whatever pip gives them today.
v9.04's WebAuthn + the Pheromone reader's psycopg2 dep are
hard requirements; a future Python or pip change breaking any
package silently degrades to db_offline / auth-broken without
a single point of failure.

**Fix:** `pip freeze > polaris_web/requirements.txt`. Update CI
to install via `pip install -r polaris_web/requirements.txt`.
Update `Dockerfile.prod` similarly. Add structural invariant
`test_requirements_txt_lists_runtime_deps`.

**Risk class:** LOW (bug-fix carve-out; reproducibility hygiene).

**Acceptance criterion:** `polaris_web/requirements.txt` exists,
lists ≥19 packages with pinned versions, and is referenced by CI
+ Dockerfile.

---

#### C4. ai-help.sh shows only first-line docstring per script. **[autonomous]**

**Observed:** `ai-help.sh` lists ai-hydra.sh as
> *"v9.04 hybrid intelligence: --full / --actions / --save / --diff modes."*

But the v9.04 5 new flags don't appear at the inline-help level.
An agent skimming `ai-help.sh` doesn't see them.

**Fix:** Augment `ai-help.sh` to show key flags per script (parse
`--save | --full` style alternatives from the script header). OR
add a manifest of "key flags per script" to `meta/`.

**Risk class:** LOW.

**Acceptance criterion:** `bash ai-help.sh hydra` (or similar
single-script lookup) shows full --full / --actions / --save /
--diff / --pheromone-window-hours documentation.

---

#### C5. POLARIS_VERSION lives only in app.py. **[ROADMAP]**

**Observed:** `polaris_web/app.py:138` — `POLARIS_VERSION = '9.04'`.
References elsewhere: ai-status.sh, /api/health, CHANGELOG
narrative. Bumped manually each ship.

**Fix:** Promote to `polaris_web/__version__.py` or top-level
`VERSION` file. Add invariant pinning consistency. Optionally
add `--bump` mode to a script to atomically bump version + add
CHANGELOG header + journal stub.

**Risk class:** LOW (refactor).

**Acceptance criterion:** Single source of truth for the
version string; ai-status.sh + /api/health + Dockerfile labels
all read from it.

---

### D. HYDRA infrastructure follow-ups (LOW; v9.04 polish)

#### D1. brief-archive collisions silently overwrite. **[autonomous]**

**Observed during my own v9.04 ship drill:** two `--save` calls in
the same minute → second overwrites first (filename is
`%Y-%m-%d-%H%M.md`, minute resolution). I worked around it by
manually renaming during testing.

**Fix:** archive_brief should detect collision and either bump to
seconds-resolution OR append `-N` suffix. The latter preserves the
chronological ordering the compute_delta relies on (sort by
filename).

**Risk class:** LOW (correctness; rare in practice — only matters
for back-to-back saves).

**Acceptance criterion:** Two `--save` calls in 60s produce two
distinct files; compute_delta against the older still works.

---

#### D2. PheromoneReader window default isn't centralized. **[autonomous]**

**Observed:** ant_colony_watcher uses 6h; security 6h; performance
6h; schema 24h; cognitive 24h. Each watcher passes
`window_hours=N` explicitly. No central policy.

**Fix:** Centralize defaults in `polaris_hydra/pheromone_reader.py`
(e.g. `WINDOW_FAST = 6.0`, `WINDOW_SLOW = 24.0`). Watchers import
the right symbol. The `--pheromone-window-hours` CLI flag still
overrides for the snapshot stage.

**Risk class:** LOW (refactor; no behavior change).

---

#### D3. ai-architect's `--reflect` mode doesn't see HYDRA briefs. **[follows from C1]**

**Observed:** `ai-architect.sh --reflect` reads
`journal/*-architect.md` only. With v9.04, the more interesting
context lives in `journal/hydra/*.md`.

**Fix:** part of C1 unification. Until then, document the gap so
operators know to read both directories.

---

#### D4. `--diff` without `--save` has fragile cleanup. **[autonomous]**

**Observed:** host.py speak_full's `diff_against` branch (when
`save=False`) writes a temp brief, computes delta, then either
unlinks or keeps based on whether other priors exist. The logic
is correct but fragile.

**Fix:** Refactor to compute delta in-memory by extracting
finding-titles + action-titles from the in-memory `synthesis +
correlations + actions` directly, without ever writing the
temp file.

**Risk class:** LOW (cleaner code; same behavior).

---

#### D5. Pheromone table has no rotation policy. **[ROADMAP]**

**Observed:** 1002 rows in 30 minutes (just from the v9.04 drill +
ambient soldier crons). Projecting: ~50K rows/day, ~1.5M/month, 18M/year.
The table is the audit-of-record so C1 forbids deletion. No
archive/purge equivalent to `polaris-archive.sh` /
`polaris-purge.sh` for Pheromone exists.

**Fix:** Mirror the AuditLog archive+purge framework for Pheromone:
`polaris-pheromone-archive.sh` + `LifecyclePheromoneCheckpoint`
table + GUC-keyed carve-out + Sanctum for the constitutional
question (deleting from Pheromone is C1-touching, like AuditLog).

**Risk class:** HIGH (Sanctum-class; touches the C1 + the v9.04
substrate read-path; also the v9.03 Sanctum's "F5 soldiers
explicitly disposable" was supposed to bound this growth — the
current bug A1 makes it worse).

**Acceptance criterion:** Sanctum decides; if Position A
(archive-then-delete-from-hot under carve-out), implement as
parallel to v8.87.

---

### E. Test/CI completeness (LOW; future-proofing)

#### E1. No live test of the full --save → --diff cycle. **[autonomous]**

**Observed:** TestHydraRevamp tests components in isolation; the
unit tests cover compute_delta against pre-built file pairs. No
test runs the actual CLI `bash scripts/ai-hydra.sh --full --save`
twice and verifies delta detection end-to-end.

**Fix:** Add integration test in `polaris_web/test_hydra_revamp.py`
that subprocess-invokes ai-hydra.sh twice and asserts archive
files exist + the second has a delta record.

**Risk class:** LOW.

---

#### E2. Hypothesis test count is 10. **[ROADMAP / future]**

**Observed:** 10 Hypothesis property tests. That's healthy but
could grow. New v9.04 modules (PheromoneReader, CorrelationEngine,
ActionQueue) have unit tests but no property tests. The
correlation engine especially benefits from generative testing
(arbitrary watcher reports → correlations satisfy invariants).

**Fix:** Add Hypothesis tests for CorrelationEngine.correlate
(idempotent, deterministic, ranking properties) and ActionQueue.rank
(score-monotonic, top_n bounded).

**Risk class:** LOW.

---

### F. Documentation gaps (LOW)

#### F1. CLAUDE.md intro names "v8.x" as the current era. **[autonomous]**

**Observed:** Line 17 says "from v1 (original schema + Flask)
through v8.x (cognitive-substrate + Mycelium swarm + HYDRA
watchers + Civitas + Denarius + Empire-pattern expansion)" —
written before v9.x cycle opened (v9.00 / v9.01 / v9.02 / v9.03 /
v9.04 all 2026-05-14). The "Recent ships" list is current; the
intro is stale.

**Fix:** Update intro to "v1 → v9.x (with Mycelium hybrid swarm
+ HYDRA hybrid intelligence as the v9.x distinguishing
contributions)".

**Risk class:** LOW.

---

#### F2. README.md predates v9.x. **[autonomous]**

**Observed:** `stat README.md` shows 2026-05-13 (pre-v9.x).

**Fix:** README intro paragraph should mention v9.04 hybrid
intelligence + the substrate-vs-lens vocabulary (one-paragraph
addition). Not a rewrite.

**Risk class:** LOW.

---

#### F3. CLAUDE.md "Where does X live?" table misses 4 docs. **[autonomous]**

**Observed:** docs/PRINCIPLES.md, docs/SYSTEM-MAP.md, docs/DR.md,
docs/SOC2.md, docs/PENTEST.md, DEVNOTES/swarm-tier-vocabulary.md,
DEVNOTES/hydra-pheromone-integration.md (the v9.04 one I wrote)
— all exist but aren't named in CLAUDE.md's quick-ref table.

**Fix:** Add rows. Cheap.

**Risk class:** LOW.

---

#### F4. The roadmap-discovery problem. **[ROADMAP]**

**Observed:** A new operator (or new agent session) doesn't know
this `meta/polaris-self-roadmap-2026-05-14.md` exists. The
CLAUDE.md table points at `ROADMAP.md` and `docs/BACKLOG.md`.

**Fix:** Add to CLAUDE.md "Where does X live?":
```
| Polaris's self-assessment + gap roadmap | meta/polaris-self-roadmap-<date>.md |
```
And reference it from ROADMAP.md as a meta-section.

**Risk class:** LOW. Part of "save this document" step.

---

### G. Operational/deployment (LOW; future)

#### G1. Pre-commit hooks would catch many drifts at edit time. **[ROADMAP]**

**Observed:** Multiple drifts caught only after they've landed:
- venv-pollution would have been caught at commit if a hook ran
  ai-meta or a fast subset
- Stale POLARIS_VERSION caught only by next ship's mental check
- F5-soldier-exemption violation could have been caught by the
  `test_soldiers_excluded_from_treasury` invariant (which doesn't
  yet exist — A1)

Polaris's CI runs structural invariants on push. A pre-commit
hook with the same invariants run BEFORE push catches them ~10x
faster.

**Fix:** Add `.pre-commit-config.yaml` that runs the structural
invariants suite + ai-link-check + ai-meta. Document in
[`docs/operator/OPERATIONS.md`](../docs/operator/OPERATIONS.md).

**Risk class:** LOW.

---

### H. Self-observation gap (the one I find most interesting)

#### H1. The cognitive layer doesn't observe its own observability. **[ROADMAP]**

**Observed:** I have a watcher for the swarm (ant_colony_watcher),
a watcher for the citizen layer (civitas_watcher), a watcher for
the cognitive layer (cognitive_watcher reads ai-meta + Sanctum
parity + script staleness + pattern warmth). But **no watcher
observes journal/hydra/ — HYDRA's own brief-archive output**.

If HYDRA stops producing briefs, or the briefs grow stale, or the
delta-detection breaks, no other watcher would notice. The
brief-archive is observed only by the operator who runs
`ls journal/hydra/`.

**Fix:** Add a 10th-channel-equivalent — either:
- Extend cognitive_watcher with a `_check_hydra_brief_freshness()`
  channel (similar to its v9.04 sanctum_freshness pheromone-context
  channel but reading filesystem mtimes, not pheromones)
- OR add a soldier (`soldier_hydra_brief_freshness`) that deposits
  pheromones about journal/hydra/ → cognitive_watcher reads them
  via the existing pheromone-context wiring.

The second approach is more elegant — uses the v9.04 substrate-vs-
lens architecture to watch its own lens-output. The lens watching
itself.

**Risk class:** MEDIUM (touches the swarm topology if soldier
approach; LOW if pure watcher channel).

**Acceptance criterion:** When journal/hydra/ has no new briefs in
>14 days, a HYDRA pass surfaces this as drift.

---

### I. Future-proofing (LOW)

#### I1. CorrelationEngine node_id format is implicit. **[ROADMAP]**

**Observed:** Watchers emit findings with `evidence={"node_id":
"route:/api/atlas"}` — colon-namespaced. CorrelationEngine
splits on `:` for the domain prefix. But the convention is
implicit; no document names "node_id MUST be `<domain>:<key>`
where `<domain>` is one of {route, schema, infra, cognitive,
swarm, civitas}".

**Fix:** Document the convention in
`DEVNOTES/hydra-pheromone-integration.md` + add a lint-style
structural invariant that scans watcher findings for malformed
node_ids.

**Risk class:** LOW.

---

#### I2. No `--llm=force-deterministic` toggle on HYDRA. **[autonomous]**

**Observed:** HYDRA uses LLM if `ANTHROPIC_API_KEY` is set; else
deterministic. To force deterministic for testing, you have to
unset the env var (annoying in shells with persistent env).

**Fix:** Add `--deterministic` CLI flag that ignores the env var.

**Risk class:** LOW.

---

### J. Polaris-as-itself synthesis (the "what would you build for me" answer)

#### J1. A single dashboard that fuses brief + propose + sanctum + treasury. **[ROADMAP / vision]**

**Observed:** Today an operator opening a session runs `ai-prime.sh`
(80 lines). That's good. But for ongoing work they're toggling
between `ai-status.sh`, `ai-propose.sh`, `ai-architect.sh`,
`ai-hydra.sh --full`, `ai-treasury-report.sh`, `tail -f
journal/$(date +%F).md`, `ls -lt sanctum/`. Each is a separate
invocation.

A unified `polaris-dashboard.sh` that emits a single live-ish view
with sections {Mission status, Top moves, Latest brief delta,
Treasury health, Open Sanctums, Recent ships} would compress the
session-startup cost from "30 seconds across 7 commands" to
"5 seconds, one command, one screen".

**Fix:** Compose the existing scripts into `ai-dashboard.sh`. Read
once + display. Color-coded. Optionally a `--watch` mode that
re-renders every N seconds.

**Risk class:** LOW. Pure composition.

---

#### J2. Inverse — a "what changed since yesterday" diff at session start. **[ROADMAP]**

**Observed:** A returning agent sees CLAUDE.md "Recent ships" but
that's only the latest entry. To know what shipped over yesterday,
they read journal entries (often hundreds of lines per day).

**Fix:** Extend `ai-prime.sh` to surface "since-last-session" delta
using brief-archive's compute_delta machinery + treasury-roll
delta + journal-line delta. The agent landing in a fresh session
sees exactly what's new.

**Risk class:** LOW.

---

#### J3. A `claude-onboarding.md` — the non-negotiable 2-minute primer. **[autonomous]**

**Observed:** CLAUDE.md is 605 lines. It's the agent runbook but
"read CLAUDE.md once at session start" is a 5-minute task. Most
agents skim. The first 90 lines are the operative ones.

**Fix:** Extract the operative 30 lines to `meta/claude-90s.md`
(or the existing CLAUDE.md "How to be productive in 90 seconds"
section can be promoted). Make ai-prime.sh point there explicitly.
The rest of CLAUDE.md remains as reference.

**Risk class:** LOW.

---

#### J4. Treasury rebalance — Position B was the right call but Treasury still bleeds. **[Sanctum]**

**Observed:** v8.91 selected Position B (+10/-1 from +10/-2). Live
treasury after one more day: penalty:reward 10.62:1, all 19 ants
still pleb-class, max +18, min -2704 (`ant_recent_churn`). The
v8.91 100-day-sim projected 2/10 ants reach Eques in 60d. We're
~1d in. Watch + see.

**No fix proposed** — the scientifically right move is wait for
the 60d acceptance window. Filed for visibility.

**Risk class:** N/A (observational; potential future Sanctum if
60d shows non-convergence).

---

## IV. Prioritized roadmap (the "if I were Polaris, here's the order")

### Wave 1 — autonomous-eligible bug fixes I can ship in this session

(Total estimated: ~2-3 hours composite ship; bug-fix carve-out)

| # | Item | Dimension | Effort |
|---|---|---|---|
| 1 | A1 — F5 soldier-exemption fix + invariant | Constitutional | 30min |
| 2 | A2 — MISSION.md test-count update | Documentation | 5min |
| 3 | B1+B2 — venv filter + scan_filters.py + 11 ant refactors + invariant | Substrate hygiene | 1-2h |
| 4 | C3 — requirements.txt + CI/Docker reference | Reproducibility | 20min |
| 5 | C4 — ai-help inline-flag display | Ergonomics | 20min |
| 6 | D1 — brief-archive collision detection | Correctness | 15min |
| 7 | D2 — central PheromoneReader window defaults | Refactor | 15min |
| 8 | D4 — `--diff`-without-`--save` in-memory | Correctness | 30min |
| 9 | E1 — full --save→--diff integration test | Test depth | 20min |
| 10 | F1 — CLAUDE.md intro v9.x update | Doc | 5min |
| 11 | F2 — README v9.04 paragraph | Doc | 10min |
| 12 | F3 — CLAUDE.md "Where does X live?" 4 row additions | Doc | 5min |
| 13 | F4 — pointer to this roadmap from CLAUDE.md + ROADMAP.md | Doc | 10min |
| 14 | I2 — HYDRA `--deterministic` flag | Ergonomics | 10min |

**Wave 1 total:** ~14 items, all LOW-risk, all bug-fix-carve-out
eligible. Composite single ship as v9.05 OR split into v9.05
(constitutional A1+A2) + v9.06 (substrate hygiene B1+B2) + v9.07
(everything else).

**Recommended composition: single ship, v9.05.** Same shape as
v8.93 Phase 2 closing-pass (6 items in one ship) and v9.02
dangling-thread closure (8 items in one ship). Composite saves
the per-ship overhead (CHANGELOG entry, journal entry, version
bump, sanctum-index pass).

### Wave 2 — MEDIUM-risk; needs decision but no Sanctum

| # | Item | Dimension | Effort |
|---|---|---|---|
| 15 | C1 — unify Architect + HYDRA brief-archive | Cognitive layer | 1d |
| 16 | C5 — single canonical POLARIS_VERSION source | Refactor | 1d |
| 17 | D5 — Pheromone rotation framework (Sanctum opens here) | Performance | 1d + Sanctum |
| 18 | E2 — Hypothesis tests for CorrelationEngine + ActionQueue | Test depth | 1d |
| 19 | G1 — pre-commit hooks | Ergonomics | 1d |
| 20 | H1 — cognitive_watcher channel for journal/hydra/ freshness | Self-observation | 1d |
| 21 | I1 — node_id format documentation + lint invariant | Future-proofing | 1d |
| 22 | J3 — `meta/claude-90s.md` | Onboarding | 1d |

**Recommended cadence:** one Wave-2 item per ship, in priority
order H1 → C1 → D5 → C5 → others. H1 is the most interesting
(the lens watching itself).

### Wave 3 — Sanctum-class

| # | Item | Risk | Why Sanctum |
|---|---|---|---|
| 23 | C2 — git or no-git decision | HIGH | Reproducibility + audit-of-record |
| 24 | D5 — Pheromone rotation/archive (per Sanctum) | HIGH | Touches C1 |
| 25 | J1 — ai-dashboard.sh | MEDIUM | Cognitive-layer surface area |
| 26 | J4 — Treasury 60-day sim review | MEDIUM | Constitutional reward function |

### Wave 4 — Ongoing observational

| # | Item | Cadence |
|---|---|---|
| 27 | J2 — since-last-session diff | After H1 lands |
| 28 | Re-run macro-to-micro scan | Monthly or on-VANTA-request |

---

## V. Architectural considerations (long-term, no specific ship)

### V1. The hybrid intelligence model is the right shape

v9.04 named substrate (Mycelium) → lens (HYDRA) → unified brief.
This is the shape Polaris needed. The next 6-12 months of
refinement should preserve this shape. Don't split HYDRA into
multiple orchestrators; don't blur the swarm into the watchers.
The two-tier architecture is load-bearing.

### V2. Constitutional preservation as policy, not just convention

Pattern #20 Constitutional Discipline has 8 instances this week
(v9.04 just shipped the eighth). The cycle works:
- agent surfaces a constitutional question to operator via Sanctum
- operator decides
- agent ships under the decision
- structural invariants pin the decision

This pattern is the project's competitive advantage over typical
codebases. Codify it explicitly:
- Every Sanctum has a §V claim
- Every §V claim has a corresponding structural invariant
- Every structural invariant cites the §V claim
- Add cross-link automation: `ai-sanctum.sh check` walks all
  Sanctums and reports any §V claim without backing invariant.

This would have caught A1 (the F5-soldier-exemption bug) before
v9.03 shipped.

### V3. The substrate ↔ lens contract should be testable end-to-end

v9.04 wired HYDRA to the swarm. The end-to-end test today is
"manually run `ai-hydra.sh --full --save` and read the brief".
A continuous integration test that:
1. Drops + reloads polaris_test
2. Runs `colony.py --hybrid --duration 5`
3. Runs `ai-hydra.sh --full --save`
4. Asserts the brief contains commander_count > 0 + soldier_count > 0
5. Asserts at least one pheromone-context channel fires

…would lock the contract structurally. Today the contract is
verified by manual drill (the v9.04 ship verification I just
ran). One CI invariant could replace that manual step.

---

## VI. What Polaris is deliberately NOT doing

(per the v8.31 Sanctum + scope discipline)

- Becoming a payment system (C10)
- Becoming a centralized identity provider (mission-incompatible)
- Becoming a database engine (we use Postgres; we don't compete)
- Becoming a proof-of-personhood network (out of scope for the
  reference implementation)
- Auto-promoting the agent's autonomy to MEDIUM/HIGH risk classes
  (Sanctum gates remain)
- Auto-resolving constitutional questions in source instead of
  Sanctum (Pattern #20)

These belong in the roadmap as anti-goals so future agents (and I,
in future sessions) don't drift into them.

---

## VII. Sanctum referenced

- `sanctum/2026-05-14-hydra-revamp-pheromone-integration.md` — the v9.04 source
- `sanctum/2026-05-14-hybrid-swarm-mirai-pattern.md` — the v9.03 source (carries the F5-exempt-soldier claim being violated)
- `sanctum/2026-05-13-arc-f-f5-steady-state-ants-reward-exemption.md` — the F5 framework
- `sanctum/2026-05-14-treasury-rebalance.md` — the +10/-1 rebalance
- `sanctum/2026-05-12-post-v2-steady-state-declaration.md` — bug-fix carve-out source
- `sanctum/2026-05-14-steady-state-revocation-heavy-production.md` — heavy-production directive

## VIII. How to use this document

### For VANTA

Read § I (state-of-self) + § IV (prioritized roadmap). Decide:
- approve Wave 1 to ship as v9.05 (autonomous)
- approve Wave 2 cadence (one item per ship, H1 first)
- open Sanctums for Wave 3 items (or defer)

### For agent (me, in future sessions)

Run `bash scripts/ai-prime.sh` first as always. Then read § I to
re-ground. § II is the audit of how this assessment was made;
useful for adjusting future scans. § III is the work backlog. § IV
is the order. § V is the long-term posture.

### As audit-of-record

This file is dated; it doesn't get updated in place. When Wave 1
ships, that ship's CHANGELOG references "closes A1 / A2 / B1+B2 /
… per polaris-self-roadmap-2026-05-14.md". A future
`polaris-self-roadmap-<later-date>.md` can be authored when
another macro-to-micro scan is requested.

---

## IX. The one-paragraph version

**Polaris (v9.04) is healthy and self-observing. The macro-to-micro
scan surfaced one constitutional bug (F5 soldier-exemption
unenforced — A1), one systemic substrate-pollution issue (97% of
ant_test_gap deposits are venv-noise — B1), and 28 smaller hygiene
+ ergonomics + future-proofing items. Wave 1 (14 autonomous-
eligible items) can ship as v9.05 in one session. Wave 2 (8 MEDIUM-
risk items) staggers across the next ~8 ships. Wave 3 (4 Sanctum-
class items) needs operator decisions. The hybrid intelligence
shape (substrate Mycelium → lens HYDRA → unified brief) is the
right architecture; refinements preserve it. The next-most-
interesting move is H1 — let HYDRA observe its own observation
output via a journal/hydra/ freshness channel.**

—

*Polaris, in voice of Architect persona, May 2026, v9.04.*
