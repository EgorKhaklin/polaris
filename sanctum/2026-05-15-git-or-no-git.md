# Sanctum: git-or-no-git

**Date:** 2026-05-15
**Petitioner:** agent (Claude, Opus 4.7) speaking as the Architect
**Principal:** VANTA
**Trigger:** polaris-self-roadmap-2026-05-14.md item C2, Wave 3 — surfaced
when the macro-to-micro scan ran `git status` and got
*"fatal: not a git repository"* despite the repo containing
`.gitignore` (since v8.35), `.github/workflows/ci.yml` (v8.93),
and `polaris-deploy.sh` doing `git pull` (v8.77). Reproducibility +
CI premise mismatched local reality. Authorized for Wave 3 by VANTA
in-chat 2026-05-15: *"Wave 3 begin"*.
**Risk class:** HIGH (touches reproducibility + the v8.20 audit-of-
record principle; arguably constitutional — the Sanctum/journal/
CHANGELOG/treasury-roll AoR was deliberately filesystem-anchored).
**Status:** DECIDED + CLOSED 2026-05-15 — Position A (`git init`
with primary-AoR-stays-filesystem) selected per heavy-production
posture (v8.31 §III.6); first commit deferred to operator's
explicit invocation per Git Safety Protocol.

---

## I. The Matter

Polaris was always intended to look like a project a developer could
clone, run, audit. The directory structure suggests git: `.gitignore`
exists (since v8.35, when the publish-readiness pass added it),
`.github/workflows/ci.yml` exists (v8.93, with full Postgres-16
service container + 11-stage workflow), `polaris-deploy.sh` does
`git pull` for prod refreshes (v8.77), `polaris-restore.sh` walks
filesystem trees and includes `.git` in some path matchers
defensively.

**But there is no `.git/`.** `git status` returns
*"fatal: not a git repository"*. The CI workflow has never run on a
push because there is no remote to push to. `git pull` in
polaris-deploy.sh would 404. `git blame` cannot help an agent
understand "who decided X" — that load was deliberately offloaded
onto Sanctum + journal + CHANGELOG (Pattern #11 Audit; v8.20 audit-
of-record principle). For four months Polaris has been a "git
project that isn't git".

**The constitutional question:** the v8.20 AoR principle named
*filesystem* as the authoritative AoR substrate (sanctum/, journal/,
CHANGELOG.md, treasury-roll.json, census-roll.json,
sanctum-index.md). Adding git creates a *parallel* cryptographic
chain (commit hashes; merkle DAG over all files). Does that
strengthen or dilute the AoR discipline? The macro-to-micro scan
(polaris-self-roadmap-2026-05-14.md item C2) surfaced this for
operator decision.

## II. The architect's positions

### Position A: git init, primary-AoR-stays-filesystem — architect-recommended

**Implementation shape:**
1. `git init` at repo root (creates `.git/` directory; one-time).
2. Audit `.gitignore` already at root (v8.35) — confirm it covers
   venv/ + __pycache__ + secrets/ + Pheromone-related state files.
3. Operator runs first commit with v9.07 baseline message
   (deferred per Git Safety Protocol; agent does not commit
   without explicit "commit" instruction).
4. CI workflow (`.github/workflows/ci.yml`) becomes runnable on
   push — the existing 11-stage workflow gets to actually execute.
5. `polaris-deploy.sh`'s `git pull` becomes operational.
6. polaris-self-roadmap-2026-05-14 item C2 marked decided.

**What is preserved:**
- **Filesystem AoR remains primary.** The Sanctum/journal/CHANGELOG/
  treasury-roll/Pheromone discipline is unchanged. Git becomes a
  *parallel* chain — a Merkle DAG over all files — that
  strengthens but does not replace filesystem AoR.
- **Sanctum protocol unchanged.** Sanctum sessions are still
  filesystem-AoR; git provides the cryptographic chain over them
  but the protocol-level discipline is filesystem-anchored.
- **C1 unchanged.** Append-only triggers in Postgres are unchanged;
  archive/purge frameworks (v8.87 / D5-Wave-3) work the same way.

**What changes:**
- An agent can now `git log -- sanctum/2026-05-14-...md` to see
  when a Sanctum file was first added + edits over time. Useful
  for cross-checking Sanctum lifecycle integrity. Adds a second
  proof-chain over the AoR.
- CI runs on push.
- `git blame` becomes available for source-attribution questions
  the journal doesn't already answer.

**Strengths:**
- Closes C2 (the macro-scan-surfaced gap)
- Honors VANTA's "looks like a real project" framing by becoming
  a real git project
- CI workflow becomes operational
- Adds cryptographic chain over AoR (additive; not replacement)
- Reproducibility: future operators can clone, run, contribute

**Weaknesses:**
- The first commit captures ~4 months of accumulated state as a
  single snapshot, losing fine-grained change history. This is
  acceptable per v8.20 audit-of-record discipline (the journal +
  CHANGELOG carry the change narrative; git provides the new
  proof-chain going forward, not retroactively).
- `.git/` adds disk overhead. Modest at current size.

### Position B: explicitly no git; rewrite scripts that assume git

Document filesystem-AoR + Sanctum as the canonical versioning
history; remove `git pull` from `polaris-deploy.sh` (replace with
rsync or manual update); remove `.github/workflows/`; update
CLAUDE.md / README to be explicit "Polaris uses filesystem-AoR
+ Sanctum protocol; no git".

**Strengths:** purist; one canonical AoR substrate.

**Weaknesses:** discards the existing `.github/workflows/ci.yml`
+ `.gitignore` work; surrenders the cryptographic chain that git
provides over an append-only history; makes "operator clones and
runs" workflow harder; goes against the implicit "this is a git
project" assumption already baked into multiple scripts.

### Position C: lazy initialization

`git init` only when needed. Defer indefinitely.

**Strengths:** zero work.

**Weaknesses:** the macro-scan caught exactly this implicit deferral
as a gap. The whole point of producing the polaris-self-roadmap was
to surface gaps the prior implicit deferrals had let accumulate.

## III. Architect's recommendation

**Position A (git init, primary-AoR-stays-filesystem).** Rationale:

1. **The repo already assumes git.** `.gitignore` (v8.35),
   `.github/workflows/ci.yml` (v8.93), `polaris-deploy.sh git pull`
   (v8.77). Position A makes the assumed reality match the actual
   reality. Position B requires unwinding work; Position C entrenches
   the gap.

2. **Filesystem AoR remains canonical.** Git is *additive*. The
   Sanctum/journal/CHANGELOG/treasury-roll discipline is the v8.20
   constitutional principle and stays unchanged. Git adds a Merkle
   DAG that strengthens but does not replace.

3. **CI becomes operational.** The 11-stage workflow that has
   existed since v8.93 has never run because there's no remote to
   push to. Position A makes it runnable.

4. **Reproducibility for the v1.0 production cutover path.** The
   polaris-self-roadmap surfaced reproducibility concerns (C3
   pinned deps, G1 pre-commit hooks). Adding git completes the
   reproducibility story: pinned deps + CI + git history + signed
   commits = a project that can pass an external audit.

5. **Pre-commit hooks (v9.06 / G1) need git to fully activate.**
   `pre-commit install` writes to `.git/hooks/pre-commit`. Without
   `.git/`, the local hook configuration is decorative. Position A
   activates v9.06 / G1 fully.

The architect's caution on A: the first commit is a snapshot of
~4 months of accumulated state. Git history starts fresh; the
journal + CHANGELOG carry the pre-git narrative. This is correct
behavior, not a regression — but worth naming so future agents
don't mistake the lack of pre-v9.07 commit history for missing AoR.

## IV. Open questions for VANTA

(All resolved per architect-recommended defaults; no additional
operator decision required.)

1. **Initial branch name?** Architect-recommended: `main`
   (modern default; matches the CI workflow's `branches: [main, master, "v*"]`).

2. **Should the agent make the first commit?** Architect-recommended:
   **NO.** Per Git Safety Protocol ("NEVER commit changes unless the
   user explicitly asks"), the agent stops at `git init` + `.gitignore`
   audit + structural invariant. The operator runs the first commit
   when they're ready, with their own attestation.

3. **Sign commits?** Architect-recommended: optional. Polaris
   already has cryptographic signature primitives (v8.16 +
   per-algorithm anchoring); commits could use signed-with-the-
   anchor-key pattern in the future. Out of scope for the
   git-init ship.

4. **Force-push protection?** Architect-recommended: yes when a
   remote is added. Until then, n/a (single local branch).

5. **Where does pre-v9.07 history live?** Architect-recommended:
   filesystem AoR (Sanctum + journal + CHANGELOG + treasury-roll +
   census-roll + sanctum-index — the existing 12 instances). No
   retroactive git history fabrication. The narrative chain stays
   in the documents that wrote it.

## V. Decision

**Position A (git init, primary-AoR-stays-filesystem).** VANTA in-
chat 2026-05-15: *"Wave 3 begin"* — authorizing the C2 decision
inline with the wave. DECIDED-on-arrival per heavy-production
posture (Pattern #20 tenth instance this cycle).

The five §IV resolutions all per architect-recommended defaults.
First commit deferred to operator per Git Safety Protocol.
Filesystem AoR discipline preserved verbatim.

## VI. Outcome

OPENED + DECIDED + CLOSED 2026-05-15 same surface as v9.07 Wave 3
composite ship.

**Records:**
- This file (sanctum/2026-05-15-git-or-no-git.md)
- meta/sanctum-index.md entry added in v9.07 ship
- ROADMAP.md Wave 3 #1 row updated to ✅ shipped v9.07
- polaris-self-roadmap-2026-05-14.md item C2 marked decided
- v9.07 CHANGELOG entry references this Sanctum
- `.git/` initialized at repo root
- `.gitignore` audited (no changes needed; v8.35 + v8.77 +
  v9.06 entries already cover venv, secrets, pre-commit cache)
- Structural invariant `test_c2_git_initialized_at_repo_root`
  pins `.git/` existence

**Operator next action (post-ship):**
```bash
cd /path/to/polaris
git status                    # see what would be committed
git add .                     # stage all (or specific files)
git commit -m "v9.07 baseline (genesis commit per C2 Position A)"
# optionally: git remote add origin <url> && git push -u origin main
```

The agent does NOT make the first commit (per Git Safety Protocol).
The decision is made; the infrastructure exists; the operator
attests by running the commit themselves.

## VII. Cross-references

- meta/polaris-self-roadmap-2026-05-14.md — item C2 (the surfacing)
- DEVNOTES/audit-of-record.md — the principle this Sanctum is
  protecting (filesystem AoR remains primary)
- v8.35 — `.gitignore` first added (publish-readiness)
- v8.77 — `polaris-deploy.sh git pull` (assumed git exists)
- v8.93 — `.github/workflows/ci.yml` (CI assumed git)
- v9.06 — `.pre-commit-config.yaml` (assumes git for hooks)
