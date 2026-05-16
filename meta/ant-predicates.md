# meta/ant-predicates.md — falsifiable predicate per commander ant

**Origin:** BIG MISSION Sanctum (`sanctum/2026-05-16-cognitive-substrate-must-bite.md`), Tier 1 #2.
**Status:** Enumeration complete for v9.24. DEPRECATION_CANDIDATE marks
those whose predicate could not be made falsifiable on first pass —
operator has one grace cycle (v9.25) to add a predicate before deletion.
**Cadence:** Re-audit on every ant added or modified.

---

## Rule (Tier 1 #2 from the v9.24 Sanctum)

> Rewrite each ant's rule from "differs from the v8.39 snapshot" to
> "X is true and must be false." First step: go ant by ant, write the
> one-sentence predicate. No predicate, no ant.

A predicate is **falsifiable** if there exists an observable system
state that would refute it. "X drifts" is not falsifiable; "the count
of X equals N" is. Predicates that can only be tested against an
internal HYDRA snapshot are AP1 hits (self-observation without
ground-touch) — they get DEPRECATION_CANDIDATE until the operator
either grounds the predicate or accepts the ant's deletion in v9.25.

---

## The 33 commander ants — per-ant predicates

### Republican legions

#### legio_schema

**ant_aor_immutability** — `Audit-class tables (TokenLifecycleEvent,
VerificationEvent, EnrollmentStatusEvent, AnchorBatch, AuditAccessLog,
LifecycleArchiveCheckpoint, LifecyclePheromoneCheckpoint, schema_version)
have zero rows where the actor attempted an UPDATE or DELETE without
going through uc_archive_purge() or uc_pheromone_archive_purge().`
Falsifiable by `psql` query against pg_stat_user_tables + trigger event log.

**ant_fk_cascade_guard** — `Every FOREIGN KEY in polaris_sql/01_schema.sql
explicitly declares ON DELETE CASCADE, ON DELETE SET NULL, or ON DELETE
RESTRICT (no default behaviors).` Falsifiable by grep + AST parse of
01_schema.sql.

**ant_substrate_catalog** — `The count of distinct SystemDependency
rows in polaris_sql/13_substrate.sql matches the count of bullet items
in DEVNOTES/substrate.md.` Falsifiable by line-count comparison.

#### legio_security

**ant_csp_health** — `polaris_web/security.py's secure_headers() does
not emit a Content-Security-Policy header containing 'unsafe-inline',
'unsafe-eval', or 'data:' in script-src or style-src.` Falsifiable by
grep against the generated header string.

**ant_atlas_endpoint_health** — `Every /api/atlas/* route responds 200
to a request with valid bbox parameters within 2 seconds, and 400 to
a request without bbox.` Falsifiable by live HTTP probe (the oracle
runner exercises this).

#### legio_mission

**ant_mission_drift** — `Every C1-C10 constraint line in MISSION.md
present at v8.0 (cog-commit hash recorded in meta/structural-constants.json)
is present byte-identical in the current MISSION.md.` Falsifiable by
sha256 of the constraint block.

**ant_principle_invariant** — `Every numbered PRINCIPLE in
docs/PRINCIPLES.md is referenced by name in at least one TestCase class
docstring or test method name within test_structural_invariants.py.`
Falsifiable by grep across both files.

**ant_done_list_arithmetic** — `The count of ✅ markers in MISSION.md
done-list equals the count of done items declared in the line "Status:
N/M done".` Falsifiable by regex count.

#### legio_adversary

**ant_adversary_walk_complete** — `meta/oracle-state.json's
adversary.per_constraint_exit dict has all ten keys C1..C10 AND the
last_run_utc is within 7 days.` Falsifiable by JSON read.

**ant_unbumped_version** — `polaris_web/__version__.py's POLARIS_VERSION
literal equals the version portion of the most-recent "## vX.Y" header
in CHANGELOG.md.` Falsifiable by string compare.

#### legio_performance

**ant_release_velocity** — `The count of "## v9.\d+" headers in
CHANGELOG.md added since polaris_web/__version__.py git mtime is ≤ 1
(no skipped versions).` Falsifiable by git log + grep count.
**DEPRECATION_CANDIDATE** — predicate weak; "skipped versions" is
plausible but not load-bearing. Operator: replace with a load-bearing
release-cadence predicate OR delete in v9.25.

**ant_ship_burst** — `Per-day count of CHANGELOG ship headers is ≤ 5
(empirically chosen ceiling for the v9.x trajectory; exceeding it is
the v9.04→v9.07 burst pattern that historically preceded scope drift).`
Falsifiable by grep + date parse.

#### legio_trajectory

**ant_proposal_stagnation** — `Every proposals/R-XX-*.md file has
either DECIDED status in its frontmatter OR a git-log entry within the
last 30 days.` Falsifiable by file scan + git log.

**ant_changelog_gap** — `The most-recent CHANGELOG.md "## v" entry
date is within 7 days of the polaris_web/__version__.py mtime.`
Falsifiable by date parse.

**ant_recent_churn** — `Git log --since='7 days ago' shows ≥1 commit
OR sanctum/2026-05-12-post-v2-steady-state-declaration.md flags
steady-state mode active.` Falsifiable by git log + file presence.
**DEPRECATION_CANDIDATE** — predicate's "steady-state mode active"
clause is operator-dependent and currently doesn't reflect VANTA's
post-v2 trajectory accurately (the steady-state declaration is
overridden by the v8.31 heavy-production posture). Operator: rewrite
or delete in v9.25.

#### legio_cognitive

**ant_self_model_accuracy** — `For every watcher in ALL_WATCHERS, the
count of expected-emission node_ids declared in the watcher class
matches the count of distinct node_ids emitted in the last 24h of
Pheromone rows.` Falsifiable by SQL aggregation + class inspection.

**ant_brain_map_freshness** — `meta/brain-map/brain-map.html mtime is
newer than any source file under polaris_swarm/, polaris_hydra/,
polaris_foresight/.` Falsifiable by mtime compare.

**ant_pattern_warmth** — `Every patterns/*.md file has been git-touched
(any commit modifying it) within the last 180 days.` Falsifiable by
git log per file.
**DEPRECATION_CANDIDATE** — "warmth via git touch" is a heuristic
not a load-bearing claim. A pattern can be load-bearing AND untouched.
Operator: replace with referenced-by-N predicate OR delete in v9.25.

#### legio_docs

**ant_api_doc_coverage** — `Every Flask route declared in
polaris_web/app.py (@app.route('...')) appears in
docs/reference/API.md, and every API.md entry has a corresponding
route.` Falsifiable by grep + diff.

**ant_devnotes_ships_coverage** — `Every CHANGELOG ## v entry for v8.x
or v9.x has either a DEVNOTES/ships/<name>.md file OR a comment in
DEVNOTES/README.md explicitly listing it as excluded.` Falsifiable by
ls + grep.

**ant_docs_structure** — `Every immediate subdirectory under docs/ has
a README.md.` Falsifiable by ls.

**ant_readme_counts** — `The "Status · vX.Y · N ships · M structural
invariants" line in README.md matches POLARIS_VERSION + the ship count
from CHANGELOG headers + the structural-invariant test count from
ai-test-counts.sh.` Falsifiable by parse + compare.

#### legio_substrate

**ant_dependency_in_use** — `Every package in polaris_web/requirements.txt
has at least one matching `import` or `from` line in polaris_web/.`
Falsifiable by grep.

**ant_journal_silence** — `If git log --since='today 00:00 UTC' shows
≥1 commit, journal/YYYY-MM-DD.md exists and has at least one '- **decision**'
or '- **learning**' line.` Falsifiable by file scan + git log.

**ant_sanctum_outcome** — `Every sanctum/*.md file has a '**Status:**'
line in the first 30 lines AND the status value is in the set {OPEN,
DECIDING, DECIDED, SHIPPED, CLOSED, DECIDED + SHIPPED, DECIDED + CLOSED}.`
Falsifiable by grep.

### Imperial legions

#### legio_praetorian

**ant_legion_doctrine_health** — `Every polaris_swarm/legions/legio_*.py
file: (a) imports `Legion` from `polaris_swarm.legions.base`; (b)
declares a class inheriting `Legion`; (c) declares ≥1 ant in its
TACTIC.` Falsifiable by AST parse.

**ant_swarm_inventory_drift** — `The count of polaris_swarm/ants/ant_*.py
files matches the sum of ant counts declared across legio_*.py
__init_subclass__ banner.` Falsifiable by ls + grep.

#### legio_engineer

**ant_build_freshness** — `polaris_zk/target/release/polaris-zk binary
exists AND is newer than any .rs file under polaris_zk/src/.`
Falsifiable by mtime + file existence.
**DEPRECATION_CANDIDATE** — the binary often doesn't exist in fresh
clones (cargo build hasn't run). Operator: either build-in-CI guarantees
this (T2#9) OR rewrite as conditional ("if target/release exists, then
freshness invariant holds") OR delete in v9.25.

**ant_stale_script** — `Every scripts/ai-*.sh and scripts/polaris-*.sh
has been invoked (per shell history OR git-touch) within the last 90
days OR has a `# DEPRECATED` marker in the first 10 lines.` Falsifiable
by grep + git log.

**ant_test_gap** — `Every constraint C1..C10 has ≥1 test function in
test_structural_invariants.py OR test_app.py whose name or docstring
contains "C1"..."C10" respectively.` Falsifiable by grep.

**ant_treasury_health** — `Sum of all Treasury ledger entries (per
treasury-roll.json) equals zero (conservation invariant: every credit
has a corresponding debit).` Falsifiable by JSON sum.

**ant_todo_debt** — `Count of `# TODO` / `# FIXME` / `# XXX` / `# HACK`
markers in core code paths (polaris_web/, polaris_sql/, polaris_hydra/,
polaris_swarm/, polaris_foresight/, polaris_zk/) is zero. DEVNOTES/ is
exempt (it's allowed to document known debt).` Falsifiable by grep.

**ant_rust_toolchain** — `polaris_zk/rust-toolchain.toml's `channel`
value is a Rust toolchain that exists on rustup's stable + nightly
manifest within the last 30 days.` Falsifiable by file read + manifest
check.
**DEPRECATION_CANDIDATE** — "rustup manifest within last 30 days" is
network-dependent. Either rewrite as offline ("toolchain matches the
pin in cargo.lock") OR delete in v9.25.

---

## Summary

- **Predicates written:** 33 of 33 (100%)
- **DEPRECATION_CANDIDATE flagged:** 5 (ant_release_velocity,
  ant_recent_churn, ant_pattern_warmth, ant_build_freshness,
  ant_rust_toolchain)
- **Operator grace cycle:** v9.25 — operator either rewrites the 5
  flagged predicates as falsifiable OR deletes the corresponding ant.
- **Structural invariant:**
  `test_every_commander_ant_has_predicate_in_index` verifies that the
  count of `ant_*.py` files matches the count of named ants in this
  document. (See `polaris_web/test_structural_invariants.py`
  TestWave24V924.)

---

*Per BIG MISSION Sanctum 2026-05-16, Tier 1 #2.*
