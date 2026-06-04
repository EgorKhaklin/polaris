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

## v9.55 — 2026-06-03 (the swap · sever the whole apparatus web at once)

scope: cognitive-rebuild · ship_marker: apparatus-swap · vocation: trustworthiness — the product is the thesis; the theater was never load-bearing · pattern20_instance: build-the-replacement-then-swap (v9.54 built the replacement; v9.55 severs the web)

v9.54 built the clean replacement (`polaris_checks/`). v9.55 is the Alexander cut:
with the replacement standing and CI wired onto it, the entire legacy apparatus is
**deleted wholesale in one stroke** — no surgical extraction, no cascade, because
nothing in the product imports it and it all leaves together.

**Deleted (~18,150 LOC + the mythology):**

- `polaris_swarm/`, `polaris_hydra/`, `polaris_foresight/` — the ant swarm, the nine
  HYDRA watchers + CM, the foresight engine.
- `polaris_web/test_structural_invariants.py`, `test_hydra_property.py`,
  `test_hydra_revamp.py` — the ~900 self-referential invariants that asserted the
  apparatus's claims about itself (Sanctum integrity, HYDRA shape, freeze line).
- 36 `ai-swarm-*` / `ai-hydra` / `ai-meta` / `ai-coherence` / `polaris-swarm-*`
  scripts.
- The mythology docs: `meta/civitas.md`, `meta/denarius.md`, `meta/twelfth-legion.md`,
  `meta/ant-predicates.md`, the arc-D/E/F/G files, `DEVNOTES/threat-model-cognitive.md`,
  `DEVNOTES/swarm-tier-vocabulary.md`, and the pheromone/observer/cadence notes.

**Rewired onto the product + the flat layer:**

- `.github/workflows/ci.yml` — product-only: schema load, `polaris_checks` + its
  detection-correctness tests, the CHECK-constraint regression suite, the Hypothesis
  property tests, `test_app` + `test_cli`, link-check, the ZK crate + the independent
  second-witness differential. Every apparatus step removed.
- `scripts/ai-done.sh` — a thin, honest gate: `polaris_checks.run` + link-check, with
  a reminder to run the DB-backed product suites. The HYDRA findings-gate, the swarm
  scorecard, and the `ai-meta`/`ai-coherence`/CM steps are gone.
- `CLAUDE.md`, `README.md`, `MISSION.md` — de-larped to the real product: identity
  tokens, zero-knowledge verification, post-quantum signing, the schema-level
  constraint lattice, and `polaris_checks` as the one invariant layer.

**What stood unchanged through the cut:** the product — `polaris_web/` (Flask app, the
use cases, the atlas API), `polaris_cli/`, `polaris_sql/` (the C1-C10 constraints,
triggers, partial unique indexes), `polaris_zk/` (the Plonky2 SNARK + the Python
second witness). All product test suites stayed green across the swap. The thesis was
always the product; the apparatus was scaffolding, and the scaffolding is down.

---

## v9.54 — 2026-06-03 (polaris_checks · the flat, themeless check layer — the apparatus-rebuild anchor)

scope: cognitive-rebuild · ship_marker: polaris-checks-anchor · vocation: trustworthiness — a check is a check; legibility is honesty · pattern20_instance: build-the-replacement-then-swap (cut the whole knot, do not untie it strand by strand)

VANTA authorized breaking the audit-of-record discipline and redoing the cognitive
layer ("take any radical approach ... like Alexander cutting the knot"). Two surgical
attempts (the de-theme rename and the civitas deletion) were executed and **reverted**:
they proved the apparatus is one self-referential web (code ↔ tests ↔ docs ↔ frozen-AoR
↔ pinned counts) where any single cut cascades endlessly. That entanglement IS the larp.

The Alexander move is not to untie the knot strand by strand — it is to build the clean
replacement and sever the whole web at once. **v9.54 builds the replacement:**

`polaris_checks/` — a flat, themeless module. Each check is a plain `check_*(repo_root)
-> list[Finding]` function mapping to the C1-C10 constitution (CSP/C5, one-active-token/
C3, append-only-AoR/C1, crypto-as-data/C7, FK-discipline, version-canonical, secrets
hygiene, the ZK two-witness, debug-artifact hygiene). No legions, no pheromones, no
treasury, no mythology. ~350 legible LOC doing the conceptual job of ~18k LOC of
apparatus. `python3 -m polaris_checks.run` gates CI directly (exit non-zero on FAIL).

**Detection correctness is TESTED** — each check provably FAILs on a broken fixture
(`polaris_checks/test_checks.py`), the gap the old apparatus never closed. The build
loop itself caught two real bugs in the checks (a version-regex and a CSP false-positive
that would have flagged the acceptable `style-src 'unsafe-inline'`), which the fixtures
now pin.

**Next (the swap):** wire callers onto polaris_checks, then delete the entire old
apparatus (swarm/HYDRA/civitas/legions/soldiers/foresight + their ~400 tests + the
mythology docs) wholesale — the cut with no cascade because it all goes together.

**Tests** (TestWave54V954, 3 cases): polaris_checks present + clean on the repo; the
layer is themeless (no mythology vocabulary); detection tests + CI wiring present.

**Personas.** Architect: build-replacement-then-swap is the correct refactor for a
self-referential web. Anti-Architect: ~350 LOC that a second engineer reads in minutes
vs 18k LOC of in-joke — this is the de-larp. Risk LOW (new module + CI step; nothing
deleted yet). Authorized under the 2026-06-03 heavy-production + take-over directive.

## v9.53 — 2026-06-03 (Apparatus-reduction · remove the orphaned economy tier-counting from HYDRA)

scope: apparatus-reduction · ship_marker: hydra-tier-counting-removed · vocation: trustworthiness — finish the cut; orphaned theater left behind is still theater · pattern20_instance: complete-the-removal (the economy cut in v9.50, finished in its HYDRA consumer)

Completes v9.50's economy removal. HYDRA's `ant_colony_watcher` kept its OWN copy of
the tier thresholds (DENARII_PLEB_MAX/EQUES_MAX), counted ants into
pleb/eques/patrician, and emitted a dead "patrician-class ant(s)" finding that
referenced the F4 Cursus Honorum multiplier retired in v9.50 and never fired (no ant
ever approached the threshold — max balance 50 vs 10,001). v9.53 removes that orphaned
theater.

KEPT (the load-bearing parts the audit flagged): the treasury-roll **integrity probe**
(missing/malformed -> `alert`), which is HYDRA's liveness wire into the ship gate; and
the "skewed strongly negative (post-rebalance)" drift signal, which reads balance
values (not tiers) and reflects the reward ledger v9.50 preserved. HYDRA keeps its name
per VANTA — only the dead economy references inside it are gone.

**Tests** (TestWave53V953, 2 cases): the tier thresholds + pleb/eques/patrician keys
stay removed from the watcher; the roll-integrity alert path survives.

**Personas.** Anti-Architect (reviewer of record): a partial cut that leaves orphaned
references is half-honest; finish it. Architect: complete-the-removal. Risk LOW
(removed a dead finding + orphaned constants; watcher + hydra suites + structural suite
all verified green). Heavy-production authorized.

## v9.52 — 2026-06-03 (Apparatus-reduction Phase 2 · the HYDRA findings-gate now actually gates)

scope: apparatus-reduction · ship_marker: findings-gate-freshness · vocation: trustworthiness — a gate that does not gate is worse than no gate · pattern20_instance: harden-the-real-thing (the part of the apparatus that IS load-bearing, made honest)

Phase 2 of the apparatus-reduction arc: the genuinely product-improving part. The
audit found `ai-done.sh`'s step-14 HYDRA findings-gate grepped the newest
`journal/hydra/*.md` brief by mtime with **no freshness check** — so a long-stale
brief (the audit found an 18-day-old one) reported "0 ALERT" as if it described the
current state. A gate passing vacuously off stale data.

v9.52 adds a freshness guard (portable `find -mtime`, not `stat -f/-c` per gotcha #4):
a brief older than 24h can no longer confirm a clean gate — it warns ("0 ALERT is
NOT confirmed against current state; run ai-hydra.sh --full --save") instead of
falsely passing. The positive path is preserved: a fresh brief with 0 ALERT still
reports ok.

The fix is self-demonstrating: with the genuinely-stale brief on disk, the gate now
honestly WARNS. And a fresh `ai-hydra.sh` run confirms why the honesty matters — the
current state actually carries findings the vacuous gate was hiding (incl. a
`trajectory: ship-rate burst (mission-creep signal)` — the watcher independently
corroborating the v9.51-repaired release-velocity ant).

**Tests** (TestWave52V952, 2 cases): the gate has a freshness check (find -mtime;
stale → NOT confirmed); the fresh-brief positive path still reports ok.

**Personas.** Anti-Architect (reviewer of record): harden the part of the apparatus
that earns its place rather than only cutting. Architect: a measurement that lies is
worse than none. Risk LOW (gate is honest-er; warns don't block; the ship machinery
is verified by running ai-done.sh). Heavy-production authorized.

## v9.51 — 2026-06-03 (Apparatus-reduction Phase 1b · repair the bit-rotted version regexes — repair, not delete)

scope: apparatus-reduction · ship_marker: changelog-ant-regex-repair · vocation: trustworthiness — a dead check wearing live-check costume is its own larping; make it real or remove it · pattern20_instance: verify-before-cut (the audit said delete 5; live verification found 2 functional + 3 fixable)

Phase 1b of the apparatus-reduction arc. The audit flagged "5 bit-rotted ants" for
deletion. Live verification corrected it: `ant_unbumped_version` (hunts stale v8.X
refs — its job) and `ant_sanctum_outcome` (accepts CHANGELOG/journal links) are
**correctly silent and still functional** — deleting them would have cut working
checks. The genuinely bit-rotted three hardcoded `## v8\.` to parse CHANGELOG
headers and silently matched NOTHING once CHANGELOG went all-v9.x:
`ant_changelog_gap`, `ant_release_velocity`, `ant_ship_burst`.

**Repaired, not deleted** — repointed each to a version-agnostic `## v\d+\.` pattern.
This restores real function AND avoids the load-bearing 33-ant count cascade (the
count is pinned across MISSION/ROADMAP/CHANGELOG/sanctum-index). The repair is
self-validating: on the current repo `release_velocity` and `ship_burst` immediately
and correctly fire a **mission-creep signal** — "7 ships landed on 2026-06-03
(threshold 6)" and "median inter-ship gap 0.00d; sustained mission-creep territory."
The swarm now honestly observes its own heavy-production cadence; before, it was dead.

**Tests** (TestWave51V951, 2 cases): the three ants' HEADER_RE matches the current
vMAJOR.MINOR scheme; a regression guard forbids re-anchoring a CHANGELOG-header regex
to a single major.

**Personas.** Anti-Architect (reviewer of record): "repair-not-delete" is the
loyal-opposition refinement — the audit's "delete 5" over-reached; verify each before
cutting. Architect: the bit-rot was itself a form of the larping the arc targets (the
illusion that all 33 ants are live). Risk LOW (regex repair + behavioral test; no
count change). Heavy-production authorized.

## v9.50 — 2026-06-03 (Apparatus-reduction Phase 1a · retire the inert Denarius "Cursus Honorum" economy)

scope: apparatus-reduction · ship_marker: cursus-economy-retired · vocation: trustworthiness — elaborate machinery whose load-bearing output is permanently zero is theater; name it and cut it · pattern20_instance: cut-deeper (the project's own apparatus-DOMINANT signal, acted on)

First ship of the apparatus-reduction arc (Sanctum `2026-06-03-apparatus-reduction`),
opened after VANTA questioned whether the ants/citizens/Roman-tactics layer earns its
place. A function-vs-theme audit confirmed the project's own standing "cut-deeper"
signal (`polaris-sanctum-status.sh` ratio 0.29, APPARATUS-DOMINANT). Scope chosen by
VANTA: **dead-weight + harden + de-theme the swarm layer; HYDRA keeps its name.**

**Phase 1a — the clearest larping instance, removed:** the Denarius "Cursus Honorum"
tier economy was provably inert. Across all operation the maximum ant balance ever
reached was **50 against a 1001 tier threshold**, so every intensity multiplier was
permanently 1.0x, no ant ever rose above pleb, and Sanctum-chair eligibility was never
met. The project's own journal already called it "vestigial" and "empirically broken."

Removed: `multiplier_for` / `property_class` / `is_sanctum_chair_eligible` /
`patrician_ants` / `CURSUS_MULTIPLIER` / the tier thresholds from `civitas/treasury.py`;
the cosmetic Cursus multiplier from `ai_swarm_bloom.py`; the `property_class` display
from `quaestor_treasurer.py`; and **`denarii_scheduler.py`** — the one attempt to make
the economy load-bearing, which was dead (zero non-test callers) AND broken (read JSON
keys that don't exist). Kept: the reward **ledger** (the +10/-1 drift signal + the roll)
as the swarm's activity/liveness record, which HYDRA's ant_colony_watcher reads as an
integrity probe (the load-bearing wire the audit flagged — cut the economy, keep the
liveness signal).

**Tests** (TestWave50V950, 3 cases): the inert Cursus apparatus stays removed; the dead
scheduler stays deleted; the reward ledger + roll (HYDRA's liveness input) survive.
Removed 4 now-orphaned tests (F4 G19 multipliers, F4 G20 chair-eligibility, 2 scheduler
existence tests).

**Constitutional clearance:** C1-C10 + the Vocation never move (the apparatus only
OBSERVES them; grep confirms no core code imports the swarm). Audit-of-record preserved
(forward-only deletion; the treasury-roll history stays).

**Personas.** Anti-Architect is reviewer of record — it pre-named AP8 "Larping" and AP1
"loving the cognitive layer's growth more than the product's"; this cut is the
loyal-opposition position. Architect: cut-deeper, acted on the project's own signal.
Risk MEDIUM (touches the civitas + a HYDRA-read liveness file; verified import-clean +
full structural suite green). Heavy-production authorized.

## v9.49 — 2026-06-03 (Swarm coverage · every ant's scan() contract is tested, not just the E10 cohort)

scope: test-coverage · ship_marker: all-ants-scan-contract · vocation: trustworthiness — an unobserved watcher is an untrusted watcher · pattern20_instance: close-the-coverage-gap (smoke loop over ALL_ANTS, not a subset)

The gap audit found 14 of the 33 ants had no individual behavioral coverage: the
only blanket smoke test looped over the 10-ant ACCELERATION+CONSCIOUSNESS cohort
(`ALL_E10_ANTS`), not `ALL_ANTS`. v9.49 extends the `scan()` contract to every
registered ant.

- `TestWave49V949` instantiates every ant in `ALL_ANTS` with the repo root and
  asserts `scan()` returns a `list[AntFinding]` and does not raise.
- Verified DB-free: all 33 ants' `scan()` pass with no Postgres, so the test is
  CI-safe (no new service dependency). This supersedes the E10-only smoke loop.
- Plus a registry-hygiene guard: no duplicate ant `NAME`s in `ALL_ANTS`.

**Tests** (TestWave49V949, 2 cases): all-33-ant scan() contract; unique ant names.

**Personas.** Architect: close the coverage gap with a structural invariant, not a
one-off. Anti-Architect: kept it DB-free and verified (33/33 pass locally) rather
than blind-adding a fragile suite. Risk LOW (test-only). Heavy-production authorized.

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

