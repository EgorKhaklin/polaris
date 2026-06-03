# Changelog (last 10 ships)

This file is the **curated index** of Polaris's recent ships. The full
audit-of-record — every entry from v1.0 through v9.23 byte-identical
— lives at [`archive/CHANGELOG-FULL.md`](archive/CHANGELOG-FULL.md).
v9.24 (BIG MISSION Tier 4 #12) compressed this file from 17,946 lines
to a 10-ship summary; the Anti-Architect's joint resolution in
`sanctum/2026-05-16-cognitive-substrate-must-bite.md` preserved the
full record at the archive path so v8.20 audit-of-record discipline
holds (the file moved; no entry was edited or deleted).

For per-ship deep detail, read the archive. For the active-decision
record, read [`meta/sanctum-index.md`](meta/sanctum-index.md).

---

## v9.48 — 2026-06-03 (Honest-accounting · ai-swarm-validate.sh header matches its body)

scope: honest-accounting · ship_marker: swarm-validate-dangling-deadline · vocation: trustworthiness — a script must not claim a computation it does not perform · pattern20_instance: drift→test promotion (dangling-deadline overclaim becomes a standing guard)

`scripts/ai-swarm-validate.sh`'s header claimed it "reports precision + recall per
ant" and "auto-flags PREDICATE_PENDING for sub-threshold ants". The body does
neither: it emits only the EXPECTED-firing matrix and deferred the observed pass
(run_colony() + Pheromone reads -> precision/recall) to "v9.25" — a follow-through
that never landed (we are at v9.48). `observed_*` counts are 0 by construction.

v9.48 rewrites the header to the honest scope (fixture inventory + expected-firing
matrix; observed precision/recall NOT computed) and removes the dangling "v9.25"
version promise from the header, the JSON `note`, and the status print.

**Tests** (TestWave48V948, 2 cases): no dangling "v9.25" version promise survives;
the header states the honest scope. The first is a class-shaped guard against
re-introducing a deadline that has already passed.

**Personas.** Architect: drift→test promotion — same honest-accounting discipline
as v9.47 (PQC ABSTAIN), applied to a swarm script. Anti-Architect: the right fix
was (b) honest header, not (a) implement-the-deferred-feature, under the v9.31
freeze. Risk LOW (docstring + test). Heavy-production authorized.

## v9.47 — 2026-06-03 (Honest-accounting · the PQC verdict is a recorded two-witness ABSTAIN)

scope: crypto-honesty · ship_marker: pqc-lone-verifier-abstain · vocation: trustworthiness — name the gap, do not let a lone verifier ship silently · pattern20_instance: drift→test promotion (the island-claim is now a standing invariant)

The two-witness principle (v9.44) says shipping a lone cryptographic verifier is
a finding, not a feature. The ML-DSA-65 signature verdict (`pqc_signing.verify`)
has a single liboqs impl and no independent second witness. v9.47 records it as
an explicit **ABSTAIN** instance (rule 4) in `DEVNOTES/two-witness-principle.md`
rather than leaving the gap silent.

It also corrects a docstring overclaim: `pqc_signing`'s activation procedure
implied that flag-on (`POLARIS_USE_REAL_PQC=1`) makes issuance write real
signatures. In fact `app.py` never imports the module and the issuance route
(`uc1_issue`) never calls `sign()` — the module is an integration *island*, so
flag-on enables the `sign()`/`verify()` primitive but does not change issuance
behavior. The docstring now says so plainly.

**Tests** (TestWave47V947, 3 cases): PQC verdict recorded as ABSTAIN; docstring
states the wiring status; and an island-guard that FAILS ON PURPOSE if
`pqc_signing` is ever imported by `app.py` — forcing whoever wires it to update
the honesty note and promote the verdict from ABSTAIN to two-witnessed.

**Personas.** Architect: drift→test promotion — the "island" claim becomes a
standing invariant. Anti-Architect: this is exactly the AP8 (larping) discipline
the PQC module itself cites — the honest move is to name the gap, not paper over
it. Risk LOW (docs + test). Heavy-production authorized.

## v9.46 — 2026-06-03 (CI hardening · the ZK two-witness differential now gates CI)

scope: ci-hardening · ship_marker: ci-two-witness-wiring · vocation: trustworthiness — a verifier that never runs in CI is not a safety net · pattern20_instance: close-the-loop (ship a check, then make it gate)

The flagship v9.44 deliverable — `test_zk_second_witness.py`, the differential
that cross-checks the Rust ZK verdict against the independent `witness2`
implementation — never ran in CI, even though CI already builds the exact
`polaris-zk` binary it needs. v9.46 wires it in.

- **pytest** added to `requirements.txt`. The header comment already promised
  it but it was absent, so the pytest-style ZK suites (`witness2/test_witness2.py`,
  `test_zk_second_witness.py`) ImportError'd on a clean install / in CI.
- **CI steps added** (`.github/workflows/ci.yml`): the ZK two-witness
  differential (after the existing prove-verify roundtrip, reusing the built
  binary via `POLARIS_ZK_BINARY`), and the pure HYDRA watcher suites
  (`test_hydra_property`, `test_hydra_revamp`; verified locally 44 pass / 9 skip).
- Refreshed the stale CI header (claimed "273 tests / 7 ZK adversarial tests";
  now descriptive, not a drifting hardcoded count).

**Follow-up (ROADMAP §OPEN NOW):** wire `test_app.py` + `test_cli.py` into CI
once confirmed green against the CI sample DB (deferred: not verifiable from the
local env, which lacks psycopg2).

**Tests** (TestWave46V946, 3 cases): pytest is a declared dependency; CI runs the
ZK two-witness differential + witness2 self-tests; CI runs the HYDRA suites.

**Personas.** Architect: close-the-loop — a shipped check that never gates is
half a ship. Anti-Architect: held the wiring to suites verified locally (ZK +
hydra), refusing to blind-add the DB-backed suites I cannot confirm from here.
Risk LOW (CI config + test). Authorized under the 2026-06-03 heavy-production
directive.

## v9.45 — 2026-06-03 (Repo hygiene · secret-leak gitignore fix · foresight log integrity)

scope: hygiene-security · ship_marker: gitignore-secret-leak · vocation: trustworthiness — operator secrets must not be one `git add` from disclosure · pattern20_instance: drift→test promotion (security regression guard)

Heavy-production session cleanup (Sanctum `2026-06-03-heavy-production-authorization`).
A repo audit surfaced a latent **secret-leak**: `.gitignore` used trailing inline
comments on `polaris.env` (operator secrets) and `.claude/`:

    polaris.env   # v9.34: sourced by polaris-mycelium-wake.sh

git does NOT honor trailing inline comments — the `# ...` becomes part of the
pattern, so `polaris.env` matched nothing and was NOT ignored by the repo. The
file holds operator secrets; a `git add -A` with it present would have committed
them. Only the file's non-existence saved the tree. v9.45 moves the comments to
their own lines above bare patterns. Verified with `git check-ignore`.

**Other hygiene:**
- `.playwright-mcp/` (158 stale browser-console logs) gitignored + removed.
- Foresight acceptance-log path parameterized: `promote_foresight_candidates`
  now takes `acceptance_log_path`, so the idempotency test stops leaking the
  fixture `"Test idempotent candidate xyz123"` into the real empirical-graduation
  tracker (`promotion.py` previously hardcoded `_REPO_ROOT`). Scrubbed the leaked
  FS-FBAEC2B8 entry.

**Tests** (TestWave45V945, 6 cases): security regression guards (polaris.env +
.claude gitignored via `git check-ignore`; no trailing-comment patterns in
.gitignore), .playwright-mcp ignored, acceptance-log path parameterized, no
fixture in the real log.

**Personas.** Architect: drift→test promotion — the secret-leak becomes a
standing invariant, not a one-time fix. Anti-Architect: no scope dissent; pure
hygiene + integrity. Risk class LOW (hygiene + test; security-positive).
Authorized under the 2026-06-03 heavy-production directive.

## v9.44 — 2026-06-03 (Glass bounded-integration · the ZK verdict is two-witnessed · decline the complete rework)

scope: zk-substrate · ship_marker: glass-bounded-integration · vocation: trustworthiness — a cryptographic verdict only one program can produce is a promise, not a proof · pattern20_instance: import-the-method-not-the-chassis (additive cross-check beside the audited substrate)

VANTA proposed reworking Polaris with the Glass language. An adversarial
fit analysis (Sanctum `2026-06-03-glass-bounded-integration`) found the
philosophical rhyme real but the rework wrong: Glass's own ledger says
*"do not use Glass to protect real value"* and it is *"not
production-hardened"*; Polaris's security boundary is the Postgres engine
(C1-C10 as triggers / partial-unique-indexes / CHECK), which Glass's
pure-functional, compile-to-C effect surface cannot host. The
decline-and-surface posture held; VANTA authorized the bounded plan:
*"go ahead with the bounded integration plan."*

**What shipped.** The one genuinely transferable asset. Glass and
`polaris_zk` both live on the Goldilocks field (2^64) with the Poseidon
hash family, which makes a second, independent verifier known-shaped
rather than research. `polaris_zk/witness2/` is a from-scratch Python
Goldilocks + Poseidon + Merkle witness that re-derives the
Merkle-inclusion verdict and must agree with the Rust `verify()`:

- Shares no code with the Rust crate or with Glass; plain `int mod p`,
  not the crate's limbs (the Pentecost discipline, borrowed from Glass).
- Anchored independently on Plonky2's own published Poseidon test vectors
  (all-zeros, 0..11, all -1) in `poseidon_constants.py`.
- Agrees bit-for-bit with the live Rust binary on root computation across
  every cohort size 1..16, and on ACCEPT/REJECT across the honest +
  adversary corpus (nonce / epoch / context / root tamper, multi-field
  replay).
- ABSTAINS, by construction, on proof-byte integrity (that axis stays
  with the Rust decoder) and says so rather than bluffing.

**Docs.** `DEVNOTES/zk-soundness.md` is the honest ledger (demo-scale
`TREE_DEPTH = 4`, placeholder PQC by default, statement-level witness
scope), modeled on Glass's own `docs/soundness.md`.
`DEVNOTES/two-witness-principle.md` makes "every cryptographic verdict
must be two-witnessed" a standing Polaris obligation.

**Tests** (TestWave44V944, 9 cases, no Rust binary needed at CI time):
package presence; 360 Poseidon constants + MDS matrices; Plonky2 vector
self-test; golden root bit-for-bit vs Rust; verdict ACCEPT/REJECT; ledger
+ principle docs honest; Sanctum recorded + indexed; no Glass coupling.
The full Rust-vs-Python differential is
`polaris_web/test_zk_second_witness.py` (18 cases; runs when the binary is
built).

**Personas.** Architect: import the method, not the chassis — the
additive cross-check strengthens C2/C7 without touching the substrate.
Anti-Architect: held the line against chassis replacement (the v9.08
showroom precedent) and against routing identity crypto through an
educational substrate (the Vocation). Risk class: HIGH Sanctum
(adjudicated a complete-rework request); the shipped work is hardening
within the v9.31 freeze envelope. Glass folder untouched; no production
substrate changed.

## v9.43 — 2026-05-18 (Post-freeze hardening · class-shaped bash bug · `grep -c ... || echo 0` double-emits 0)

scope: cognitive-layer · ship_marker: grep-c-double-output · vocation: cognitive-layer self-coherence (CM #6) · pattern20_instance: drift→test promotion loop + class-shaped vs instance-shaped fix

Surfaced 2026-05-18 by `bash scripts/ai-reflect.sh` against a fresh
journal with no `^## SESSION` lines:

    scripts/ai-reflect.sh: line 114: [: 0\n0: integer expression expected

The idiom `grep -c <pattern> file 2>/dev/null || echo 0` is broken.
`grep -c` always prints a count to stdout — including `0` on no
match — and exits 1 only in that case. The fallback fires AFTER the
count is already printed, double-emitting `0`. The variable receives
`0\n0`, which breaks any subsequent `[ "$var" -ge N ]` integer
compare. The cognitive-layer self-reflection script's session-count
check therefore failed silently on every journal day with no
SESSION markers (every day this session).

**Class-shaped fix** — same anti-pattern existed in **10 places
across 6 scripts**:

- `scripts/ai-reflect.sh` × 7 (the surfacer)
- `scripts/ai-status.sh` × 2 (routes + tests counts)
- `scripts/ai-coherence.sh` × 2 (schema_checks + routes)
- `scripts/ai-context-digest.sh` × 1 (test_count)
- `scripts/polaris-ct-monitor.sh` × 1 (local_count)
- `scripts/ai-architect.sh` × 1 (decisions per journal)

Replaced all with `|| true`. `grep -c` already prints the count;
`|| true` only neutralizes the non-zero exit code without re-emitting.

**Tests** (TestWave43V943, 2 cases):
- `test_v943_no_grep_c_double_output_pattern` — class-shaped
  regression guard scanning `scripts/*.sh`; refuses any new
  `grep -c ... || echo 0` form
- `test_v943_reflect_runs_without_integer_error` — end-to-end:
  `bash ai-reflect.sh` must emit zero `integer expression expected`
  lines on stderr+stdout

**CM tie-in.** CM #6: cognitive-layer claims must be auditable. When
`ai-reflect.sh` produced `0\n0` garble, the self-reflection surface
was degraded silently. Fixing it (a) restores the surface and (b)
adds a class-shaped test so the next instance is caught at CI time,
not at HYDRA-pass time three days later.

**Personas.** Architect: drift→test promotion (arch-2026-05-18-003)
applied again — every cognitive-layer self-defect should become a
class-shaped invariant if the class is more than one. Anti-Architect:
no dissent on scope. Risk class LOW (maintenance fix to scripts;
zero constitutional surface; zero behavioral change for callers
because `grep -c` already prints the count).

## v9.42 — 2026-05-18 (Post-freeze hardening · HYDRA watcher false-positive cleanup · two drift-in-the-watcher fixes)

scope: cognitive-layer · ship_marker: hydra-watcher-cleanup · vocation: anti-surveillance (watcher honesty) · pattern20_instance: drift→test promotion loop (arch-2026-05-18-003)

The 2026-05-17 HYDRA pass surfaced 4 drift signals. Two of them were
not drift in the system being observed; they were drift in the
watchers themselves. v9.42 closes both, both with behavioral tests
under the Architect's drift→test promotion principle.

**Finding 1 — `soldier_log_tail` phantom alerts after Docker switch.**
The soldier reads `/tmp/polaris_app.log` with no staleness check. Under
the Docker runtime that file is frozen at the moment the last native
gunicorn shutdown wrote to it (2026-05-15 04:54 in this case); the
soldier kept emitting 5 alert pheromones every 6h reading the same
frozen ERROR + 4 WARNING lines (all about the in-memory rate limiter,
which v9.39 actually fixed at the root). **Fix:** add
`STALE_THRESHOLD_SECONDS = 600`. If mtime > threshold, return one
KIND_INFO observation flagging the source as dormant. Phantom-signal
storm stops within one cycle.

**Finding 2 — `ant_colony` watcher graded F5 on the wrong window.**
The watcher's `_summarize_balances` reduced ALL events from
`treasury-roll.json` into per-ant balances and graded the
"Treasury skewed strongly negative" finding on the aggregate
min/max. The aggregate is forever-polluted by pre-v8.91 frozen -2
penalties (G15 keeps them in the ledger). `scripts/ai-treasury-report.sh`
already splits "post-rebalance (since v8.91, +10/-1 in operation)"
distinctly from aggregate; the report's verdict reads ✓ in-band, but
the HYDRA watcher read ✗ skewed. **Fix:** mirror the report's split.
The watcher now exposes `post_rebalance_min_negative` /
`post_rebalance_max_positive` (filtered to amounts in {+10, -1}, the
current policy) and grades the F5 drift finding on the post-rebalance
subset. The aggregate is still exposed in evidence_summary for
operator visibility, but no longer drives the finding.

**Tests** (TestWave42V942, 5 cases):
- `test_v942_log_tail_has_stale_guard` — source-level invariant
- `test_v942_log_tail_returns_info_on_stale_file` — behavioral; stale
  file with ERROR content emits KIND_INFO, not KIND_ALERT
- `test_v942_log_tail_still_alerts_on_fresh_errors` — negative test;
  guard is not over-broad
- `test_v942_ant_colony_uses_post_rebalance` — source-level invariant
- `test_v942_ant_colony_summarize_filters_pre_rebalance` — behavioral;
  fake roll with -2 (pre-rebalance) + -1 (post) + +10 confirms only
  {+10, -1} amounts enter the post-rebalance subset

**Personas weighed in.** Architect: invoked arch-2026-05-18-003
(drift→test promotion loop) — every drift catch should become an
executable test. Done. Anti-Architect: silent on the scope (no
structured proposal dissent); flagged v9.39 already closed a
soldier_log_tail finding at the **root cause** (Redis env wired),
but didn't close the **failure mode** (stale-file phantom signal) —
v9.42 closes the latter, mirroring the v8.12 drift→test pattern.

Risk class: LOW (drift maintenance under heavy-production steady-state;
both edits are watcher-bug fixes, no constitutional surface touched).

## v9.41 — 2026-05-17 (AoR reclassification · canonical set 12 → 10 · two derived caches dropped · v9.x release)

The published-release ship for v9.x. Closes the constitutional gap
opened by v9.40's `.gitignore` polish commit (e56b310): three files
were untracked as auto-gen state (`meta/brain-map/brain-map.html`,
`polaris_swarm/civitas/census-roll.json`,
`polaris_swarm/civitas/treasury-roll.json`), but the constitution still
claimed all three as filesystem audit-of-record instances #10/#11/#12.
CI caught the divergence: structural invariants expected those files
present on origin.

**Architect + Anti-Architect adjudication:** the v8.66 + v8.68 ships
that classified census-roll/treasury-roll as filesystem-AoR failed the
AoR criterion ("fully reconstructs operation history without joining
elsewhere"). Census-roll is a cached projection over the actual
presence of `polaris_swarm/ants/ant_*.py` modules + civitas modules.
Treasury-roll is a cached sum over Pheromone-table deposits (already
schema-AoR #2) plus the reward function. Both are derived; neither is
source-of-truth. **Reclassification:** 12 total → **10 total (9 schema
+ 1 filesystem)**. The brain-map.html was the third reclassified file
(generator-marker invariant survives at the generator level).

**Documents updated** (canonical-count cascade):
DEVNOTES/audit-of-record.md (header + table rows #11/#12 + new
"v9.41 reclassification" subsection); MISSION.md §Principle 2;
CLAUDE.md C1 invariant; README.md "Twelve instances" prose;
DEVNOTES/README.md; docs/README.md; meta/sanctum-protocol.md;
docs/ARCHITECTURE-OVERVIEW.md; docs/operator/DR-SINGLE-REGION.md;
docs/reference/GLOSSARY.md; polaris_swarm/__init__.py docstring.

**Tests:** 2 renamed (`test_sanctum_protocol_aor_count_is_ten`,
`test_glossary_acknowledges_aor_count_is_ten` — regex now matches
`r"10 instances\s*\(9 schema\s*\+\s*1 filesystem\)"` + asserts the two
reclassified files are named in the protocol doc); 6 retired with
`@unittest.skip` decorators naming the replacing invariant
(test_brain_map_html_present, test_census_roll_json_exists_with_append_only_marker,
test_treasury_roll_is_filesystem_aor, test_a1_treasury_roll_has_v905_audit_marker,
test_brain_map_output_grows_with_mycelium, test_brain_map_has_auto_generated_marker);
1 adapted (`test_denarii_never_reference_polaris_identity` — dataclass
shape check always runs; file-scan portion wrapped in
`if os.path.isfile(roll_path):`). The class-shape claims are preserved
at the generator level; only instance-level file-presence checks
retired.

**Followup commit:** repointed 2 broken markdown links to the
generator script (`README.md:126` and `docs/story/STORY.md:73`) that
ai-link-check caught after the c1f0ea6 push went green on tests but
red on link discipline. Historical narrative numbers (222 nodes / 248
edges in STORY.md May-13 snapshot) preserved.

Final live counts: 937 tests, OK (skipped=6); 633 link references
resolved; `/api/version` reports v9.41.

Per-ship archive-move: v9.30 byte-identical to "Post-v9.24" section
in archive. CHANGELOG = 10 stable (v9.40..v9.31) + v9.41 in-flight.

## v9.40 — 2026-05-17 (Post-freeze hardening · operational completeness · v9.31+v9.39 cascade)

Three coupled defects surfaced when the v9.39 container rebuild
exposed them:

1. **`observability.py` (v9.31) missing from both Dockerfiles.**
   Container failed to boot: `ModuleNotFoundError: No module named
   'observability'`. The v9.17 regression-guard test was supposed
   to catch exactly this (it caught v8.97 webauthn_auth.py
   omission). But its regex `^\\s*import\\s+(\\w+)\\s*$` required
   nothing after the module name; my v9.31 edit had
   `import observability  # v9.31 ...` — trailing comment invisible
   to the regex. **Both the Dockerfiles AND the regex fixed.**
2. **Regression-guard only scanned `app.py`**, not `security.py`.
   v9.31 added `import observability` to security.py too. The new
   regex pattern (with trailing-comment tolerance) now applies to
   both files.
3. **`redis` Python lib missing from `requirements.txt`** →
   v9.39's `POLARIS_REDIS_URL` env-pass-through silently degraded
   to in-memory backend even when the URL was correctly set
   (`security.py` auto-selector requires the lib to be importable).

Live verified post-rebuild: `/api/version` reports v9.40,
`/api/metrics` returns real counters (was 404 in v9.30 container),
observability.py imports cleanly.

Per-ship archive-move: v9.29 byte-identical to Post-v9.24 section
in archive. CHANGELOG = 10 stable (v9.39..v9.30) + v9.40 in-flight.

`TestWave40V940` × 4 invariants: observability in both Dockerfiles;
regex tolerates trailing comments; regression-guard scans
security.py; `redis>=` in requirements.txt. Plus the underlying
regression-guard now catches future occurrences of this class.

## v9.39 — 2026-05-17 (Post-freeze hardening · POLARIS_REDIS_URL wired into docker-compose · soldier-log-tail finding closed)

Closes shakedown finding C: `soldier_log_tail` correctly flagged the
runtime warning "POLARIS_WORKERS=4 with in-memory rate limiter —
actual per-IP limits will be ~4× configured because each worker
holds its own buckets." Real defect surface (multi-worker dev
convenience).

Fix: `polaris_web/docker-compose.yml` now declares
`POLARIS_REDIS_URL: ${POLARIS_REDIS_URL:-}` in the app service
environment. Empty default preserves backward compat (security.py
auto-selects in-memory if URL empty). Operator sets the env var in
shell to activate, e.g.:

    brew services start redis
    POLARIS_REDIS_URL=redis://host.docker.internal:6379/0 \
        ./polaris_mac_launch.sh rebuild

After rebuild, `/api/health` will report `redis.backend = "redis"`
instead of `"memory"`, and the soldier_log_tail signals about
multi-worker bucket fragmentation should clear.

Per-ship archive-move pattern (established v9.38): v9.28 entry moved
byte-identical from CHANGELOG.md → "Post-v9.24 ships" section in
archive/CHANGELOG-FULL.md. CHANGELOG holds 10 stable (v9.38..v9.29)
+ this v9.39 in-flight = 11.

`TestWave39V939` × 1 invariant pins the env-pass-through declaration
in docker-compose.yml with the empty-default backward-compat
pattern.

## v9.38 — 2026-05-17 (Post-freeze hardening · archive-extension Sanctum · CHANGELOG = last 10 honestly)

Decided in `sanctum/2026-05-17-changelog-archive-extension.md`
(HIGH — amends v9.24's "no entry was edited or deleted" archive
claim). Pre-authorized by VANTA: "have the changelog at 10 latest
ships, the other ones move to the archive changelog."

The v9.24 compression committed "last 10 ships" in CHANGELOG.md
with byte-frozen pre-v9.24 history in
`archive/CHANGELOG-FULL.md`. As v9.25+ accumulated, the convention
needed entries to age OUT of CHANGELOG.md, but the archive's
byte-frozen claim forbade growth. v9.34 + v9.36 deferred via cap
relaxation (12→14). v9.38 closes it properly.

- **Amendment:** archive grows APPENDS-only (no edits or deletions
  of existing rows). New section `## Post-v9.24 ships` marks the
  boundary. v9.24–v9.27 moved byte-identical from CHANGELOG.md →
  archive's new section.
- **CHANGELOG.md state:** 10 ships + this in-flight v9.38 entry = 11.
  Cap restored 14 → 11.
- **ROADMAP.md** entry transitioned "NOW RIPE" → "DONE in v9.38."

`TestWave38V938` × 5 invariants: archive has post-v9.24 section;
v9.24–v9.27 in archive; v9.24–v9.27 NOT in CHANGELOG.md; CHANGELOG
has exactly 11 ships; Sanctum closed + indexed.

