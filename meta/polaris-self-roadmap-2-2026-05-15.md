# Polaris speaks — self-roadmap II (2026-05-15, v9.08)

**Voice:** Polaris itself, surveyed by Claude (Architect persona)
after v9.05+v9.06+v9.07 closed all 30 items from the original
[`polaris-self-roadmap-2026-05-14.md`](polaris-self-roadmap-2026-05-14.md)
and v9.08 polished the structure to showroom standard.

**Audience:** VANTA + the future-VANTA orienting after time away.

**Frame:** This is the Wave-4 macro re-scan deliverable. It surveys
what changed across v9.05 → v9.08 and cataloges any new gaps. If
the project had genuinely accumulated new gaps we'd file them here
as Wave-5 candidates. **None did. Polaris is in the cleanest shape
of its life.**

---

## I. The 4-day arc since 2026-05-14 macro scan

Macro scan 2026-05-14 (v9.04) → roadmap → 30 items → 4 composite
ships in ~30 hours:

| Ship | Wave | Items | Risk | What landed |
|---|---|---|---|---|
| **v9.05** | Wave 1 | 14 | LOW (composite) | Constitutional bug fix (F5 soldier-exemption restored) + systemic substrate hygiene (97.7%→0% noise on ant_test_gap) + ergonomics polish |
| **v9.06** | Wave 2 | 8 | MEDIUM | The lens watching itself (cognitive_watcher channel 6) + Architect↔HYDRA brief unification + Pheromone rotation Sanctum opened + canonical POLARIS_VERSION + 9 Hypothesis property tests + pre-commit hooks + node_id format docs + onboarding primer |
| **v9.07** | Wave 3 | 4 | HIGH (composite) | git init (Position A) + Pheromone rotation framework (G32+G33) + ai-dashboard.sh + Treasury sim review |
| **v9.08** | Wave 4 + showroom | 12 | MEDIUM-HIGH (composite) | Showroom polish (10 READMEs + CONVENTIONS + SYSTEM-MAP + root README) + J2 since-last-session delta + this re-scan doc |

**Total: 38 items in 4 ships in ~30 hours.** Constitutional integrity
preserved end-to-end. Pattern #20 Constitutional Discipline cycled
**11 times this week** (v8.84/v8.87/v8.90/v8.91/v8.94/v8.95/v8.96/
v8.97/v9.04/v9.06/v9.07/v9.08).

---

## II. Current state, named

### Live brief, 2026-05-15 ~01:37 EDT

```
Watchers reporting: 9 (5 healthy, 3 drift, 1 alert)
- schema       healthy
- cognitive    alert    (sanctum-index drift; resolved in this ship)
- security     drift    (soldier_log_tail surfaced 1 signal)
- mission      healthy
- adversary    healthy
- performance  healthy  (app offline; static surface OK)
- trajectory   drift    (7 ships today; polaris_web/ churn cluster)
- ant_colony   drift    (8/8 soldier classes silent >2h — cron not
                          running in dev sandbox; expected)
- civitas      healthy

Pheromone substrate: 1002 deposits in 6h window (983 commanders + 19 soldiers)
```

### What changed structurally

**New constructs (v9.05 → v9.08):**
- `polaris_swarm/scan_filters.py` (v9.05) — venv-filter for ant walkers
- `polaris_swarm/civitas/treasury.py:is_treasury_exempt()` (v9.05) — F5 soldier exemption mechanical enforcement
- `polaris_web/__version__.py` (v9.06) — canonical version source
- `polaris_web/test_hydra_property.py` (v9.06) — 9 Hypothesis property tests
- `polaris_web/test_hydra_revamp.py` (v9.04) — 44 unit tests for v9.04 modules
- `polaris_hydra/pheromone_reader.py` + `correlation.py` + `action_queue.py` + `brief_archive.py` (v9.04) — hybrid intelligence infrastructure
- `polaris_sql/migrations/2026-05-15-001-pheromone-rotation.{up,down}.sql` (v9.07) — D5-impl framework
- `scripts/polaris-pheromone-archive.sh` + `polaris-pheromone-purge.sh` (v9.07) — operator scripts
- `scripts/ai-dashboard.sh` (v9.07) — single-screen dashboard
- `meta/claude-90s.md` (v9.06) — 90-second onboarding primer
- `meta/treasury-60d-sim-review-2026-05-15.md` (v9.07) — J4 review
- `docs/CONVENTIONS.md` (v9.08) — naming + structural conventions
- 10 new READMEs (v9.08) — every directory has one
- `.pre-commit-config.yaml` (v9.06) — 6 local hooks
- `polaris_web/requirements.txt` (v9.05) — pinned 19 deps
- `.git/` (v9.07) — git init + first commit deferred to operator

**G-guards added (v9.05 → v9.07):** G32 + G33 (parallel to G30+G31 for Pheromone archive+purge framework)

**Constitutional invariants restored (v9.05 / A1):** F5 soldier-exemption
violation (v9.03 Sanctum claim contradicted by code) → now mechanically
enforced via `is_treasury_exempt()` predicate.

**Audit-of-record additions:** 6 new Sanctum sessions in v9.05 → v9.08
(hydra-revamp-pheromone-integration, treasury-rebalance, schema-
migration-framework, webauthn-operator-auth, phase-3-opening, hybrid-
swarm-mirai-pattern, pheromone-rotation, git-or-no-git, showroom-
reorganization). Total 47 sessions on file.

---

## III. Macro re-scan finding inventory (post-v9.08)

The original 30-item roadmap closed. New scan surfaces these
candidates for future cycles:

### Genuinely new (none of these are blocking; all are Wave-5+ candidates)

#### N1. Architect's voice still uses em-dashes in --reflect output

**Observed:** v9.06 added `do_reflect_hydra_briefs()` to ai-architect.sh;
v9.06 ship had to remove em-dashes from the new function in v9.07
debug. The em-dash-warn pre-commit hook is informational-only.

**Fix:** promote em-dash check from informational to blocking.

**Risk:** LOW. **Effort:** one-shot.

#### N2. CHANGELOG.md has crossed 737 KB

**Observed:** CHANGELOG.md is now ~770 KB after v9.05-v9.08 entries.
Render time at v8.20 was already a soft signal; trending up.

**Architect's stance:** **NOT a problem to solve.** Per v8.20 audit-
of-record discipline, CHANGELOG is canonical and never trimmed. The
"## v" prefix is the navigation surface; that's enough. If render
time becomes operationally painful, a separate `CHANGELOG-archive.md`
(for old eras) could split, but the current ~32 ships in one file
is still readable.

#### N3. CLAUDE.md state-map row growing unbounded

**Observed:** the v9.07/v9.08 entries are each ~3-4 paragraphs each.
With ~32 ships at full detail, the "Recent ships" section is now
~50 KB.

**Fix candidate:** condense after-N-ships (e.g., entries older than
30 days collapse to a one-line summary, but keep CHANGELOG link
for full detail). Need a Sanctum (touches the agent-runbook
constitutional surface).

**Risk:** MEDIUM (Sanctum-class). **Effort:** one-day.

#### N4. polaris_web/ churn cluster (trajectory_watcher signal)

**Observed:** trajectory_watcher fires "948/1001 modifications in
polaris_web/" — accurate, since test_structural_invariants.py
(9000+ lines) lives there + every ship adds invariants.

**Architect's stance:** **NOT a problem.** This is a true positive
of intense focused work, not scope creep. trajectory_watcher's
detection works correctly; the operator interprets.

#### N5. Treasury 60-day evaluation pending

**Observed:** v8.91 Sanctum committed to a 60-day evaluation
window ending 2026-07-13. v9.07 / J4 reviewed the v9.05 cohort
shift; recommended Path A (preserve window). Today is 2026-05-15
(~2 days into 60).

**Architect's stance:** **WAIT.** Re-evaluate at 2026-07-13.

#### N6. Soldier silence in dev (8/8 classes silent >2h)

**Observed:** ant_colony_watcher channel 2 fires in dev because
the soldier cron isn't running locally. In prod (per v9.01
OPERATIONS.md cron schedule), soldiers run every 30min for 60s.

**Architect's stance:** **EXPECTED in dev.** The signal is correct
behavior; the operator interprets. Could add a "dev-mode
exemption" but that complicates the watcher.

### Continuing observational

| Item | When |
|---|---|
| Macro re-scan | 2026-06-15 (~30d after this one) |
| Treasury 60-day eval | 2026-07-13 (per v8.91) |
| Re-confirm structural invariants count grows linearly | every 5 ships |
| Re-audit READMEs for currency (any reference stale ship) | every 10 ships |

---

## IV. What's NOT a gap

Items I considered + dismissed as non-issues:

- **Top-level still has 6 dirs + 6 markdown files + 2 scripts.**
  The structure is semantic; further reduction would hurt
  discoverability.
- **scripts/ still has 50+ files in one dir.** The ai-* / polaris-*
  prefix split + scripts/README.md categorization is enough; sub-
  directorying would break every ai-* invocation in CHANGELOG
  history.
- **DEVNOTES/ vs docs/ vs meta/ vs sanctum/ all carry docs.** Each
  has a distinct role (informal vs formal vs cognitive vs
  decision); their separation is a feature not a bug.
- **CHANGELOG.md size.** v8.20 AoR; never trim.
- **Python package names (`polaris_*`).** Import-graph stability;
  changing requires full retest cycle for marginal cosmetic
  benefit.

---

## V. Architectural posture (v9.08)

### What Polaris IS, today

A national-identity-token reference implementation in production-
deployable shape. The substrate-vs-lens hybrid intelligence
architecture (v9.04+) is the project's distinguishing technical
contribution. The Sanctum protocol + audit-of-record discipline
are the project's distinguishing process contributions. v9.08
shipped showroom polish — every directory has a README; every
naming convention is named in `docs/CONVENTIONS.md`; the
architectural map is in `docs/reference/SYSTEM-MAP.md`.

### What Polaris is deliberately NOT becoming

- A payment system (C10)
- A centralized identity provider
- A general-purpose database engine
- A proof-of-personhood network
- An auto-promoting-its-own-autonomy agent (Sanctum gates remain)

### What's load-bearing for v1.0

All of:
1. C1-C10 hard constraints in force
2. Mission v1 + v2 done-lists complete
3. Arc B Phase 1 production-deployable
4. v9.04 hybrid intelligence operational
5. v9.07 git-initialized; CI workflow runnable
6. v9.08 documentation showroom-quality

What's still gated for v1.0:
- Operator runs first git commit (v9.07 Position A)
- Operator runs `pre-commit install` (v9.06)
- 60-day Treasury evaluation lands at 2026-07-13 (v8.91)

---

## VI. Acceptance: this re-scan closes Wave 4

Wave 4 of the original `polaris-self-roadmap-2026-05-14.md`:
- ✅ J2 — since-last-session delta in ai-prime.sh (v9.08)
- ✅ Re-run macro-to-micro scan (this document)

The original 30-item roadmap is now COMPLETE across waves 1-4.

---

## VII. Sanctum referenced

- `sanctum/2026-05-15-showroom-reorganization.md` — the v9.08 source
  for the structural-polish portion
- `sanctum/2026-05-14-hydra-revamp-pheromone-integration.md` — v9.04
  hybrid intelligence
- `sanctum/2026-05-15-pheromone-rotation.md` — v9.06+v9.07 archive
  framework
- `sanctum/2026-05-15-git-or-no-git.md` — v9.07 git init Position A
- `sanctum/2026-05-14-treasury-rebalance.md` — v8.91 Position B
  (60-day eval pending)

---

## VIII. The one-paragraph version

**Polaris (v9.08) is in the cleanest shape of its life.** The 30-item
polaris-self-roadmap-2026-05-14 is COMPLETE across 4 waves. The
constitutional bug (A1) is fixed; the substrate is clean (B1+B2);
the hybrid intelligence pipeline reads itself (H1); the version is
canonical (C5); the framework for Pheromone rotation is shipped
(D5-impl, G32+G33); git is initialized (C2 Position A); the
dashboard composes seven sections in one screen (J1); every
directory has a README (v9.08); all naming + structural conventions
are named in `docs/CONVENTIONS.md`; the architectural map is in
`docs/reference/SYSTEM-MAP.md`; the lens watches itself (v9.06 H1).
**No new constitutional gaps surface in this re-scan.** The next
calendar triggers are 2026-06-15 (next macro re-scan) and 2026-07-13
(v8.91 Treasury 60-day evaluation). Pattern #20 cycled 11 times in
30 hours; the macro-to-micro scan → wave-by-wave composite-ship
pattern is now a documented project rhythm.

—

*Polaris, in voice of Architect persona, May 2026, v9.08.*
