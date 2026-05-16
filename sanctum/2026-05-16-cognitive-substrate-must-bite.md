# Sanctum — Cognitive substrate must bite (14-item Architect + Anti-Architect debate)

**Status:** DECIDED + SHIPPED 2026-05-16 — Position JOINT-MODIFIED (ship all 14 items with debate-applied scope per Anti-Architect contests). Authorized by VANTA in-chat 2026-05-16. Shipped as v9.24.

**Date opened:** 2026-05-16
**Date decided:** 2026-05-16
**Date shipped:** 2026-05-16 (v9.24)
**Lifecycle:** OPEN → DECIDING → DECIDED → SHIPPED
**Risk class:** HIGH (composite — touches cognitive layer wiring, real cryptographic substrate, CI, narrative-mass + runbook governance)
**Pattern #20 Constitutional Discipline:** 19th instance
**Authorization:** "Mission for the architect / anti architect" — VANTA, in-chat 2026-05-16

---

## §I. The Critique (VANTA's framing — abridged verbatim)

> Here is the full list, ordered so each tier unblocks the next.
>
> **Tier 1 — make the observability apparatus actually function. Until
> this is done the swarm is dead weight.**
>
> 1. Wire findings to consequence (severity threshold blocks ai-done)
> 2. Every ant has a falsifiable predicate or delete it
> 3. Use the treasury as the selection oracle (cut bottom + no-predicate)
> 4. Close the stigmergic loop (deposit biases next pass)
> 5. Balance buys scan attention (denarii → scheduler frequency)
> 6. One external oracle the model must reconcile against
>
> **Tier 2 — harden the core, because the core is the genuinely good
> part and worth making real.**
>
> 7. Replace placeholder signature with real signing path
> 8. Measured numbers under load (verify/sec + lock contention)
> 9. Build + exercise ZK binary in CI
> 10. Validate swarm against ground truth (fixtures + precision/recall)
>
> **Tier 3 — extract the one thing that might be a real contribution.**
>
> 11. Agent-maintainable-architecture thesis (one page, falsifiable)
>
> **Tier 4 — hygiene.**
>
> 12. Collapse narrative mass (CHANGELOG <2000 words, archive)
> 13. Mechanical scope rule (pre-commit hook)
> 14. CLAUDE.md = invariants + predicates + loop wiring (trim hard)
>
> Item 1 most urgent. Item 13 determines whether any of this holds
> six months from now.

The critique is unmistakable: **the swarm is dead weight, the headline
crypto is a stub, and the narrative mass is regulating nothing.** Three
class-of-charge: (a) instrumentation produces no consequence; (b) the
core's headline claim is unsubstantiated; (c) the cognitive overhead
is now larger than the thing it observes.

---

## §II. Debate (Architect ↔ Anti-Architect, per item)

### TIER 1 — observability apparatus

#### T1#1 — Wire findings to ai-done.sh consequence

**Architect:** Add gate to `ai-done.sh` after step 13. Threshold =
finding `level=ALERT` from any HYDRA watcher in the most-recent
`--full --save` brief blocks the ship. Lower severity (drift / info)
emit warnings, not fails.

**Anti-Architect:** Concur. Specify the gate is **opt-out-able via
`POLARIS_ALLOW_ALERT_SHIPS=1`** for documented incident-response cases
(e.g., shipping the FIX for the alerting condition itself). Refuse
opt-out by default — that would defeat the point. AP1 (self-observation
without ground-touch) fires hard if findings remain advisory.

**Joint:** Ship gate as `ai-done.sh` step 14. Threshold = ALERT.
Default = blocking. Override = `POLARIS_ALLOW_ALERT_SHIPS=1` with
audit-trail line printed.

#### T1#2 — Predicate-or-delete per ant

**Architect:** Enumerate every commander ant. Write per-ant one-
sentence predicate of the form "X must be Y." Where the existing rule
is "differs from v8.39 snapshot," the predicate becomes "schema_version
table is monotonically appending" or "n_active_tokens > 0 in last 24h."
Ants without predicate get DEPRECATED tag.

**Anti-Architect:** Refuse immediate deletion (AP-destructive without
operator review). Joint pattern: enumerate + write predicates + mark
`PREDICATE_PENDING` or `DEPRECATION_CANDIDATE` on those without; emit
a `polaris-ant-predicates.md` index. Operator has one cycle to add
predicates before the deletion ship fires. **AP4 (pattern-projection)
detection becomes operational** via the predicate enumeration —
findings without falsifiable predicates ARE pattern-projection by
definition.

**Joint:** Ship `meta/ant-predicates.md` enumerating every commander
ant + per-ant predicate (or DEPRECATION_CANDIDATE flag). Ship structural
invariant `test_every_ant_has_predicate_or_deprecation_mark`. Defer
actual deletion to v9.25 (gives operator predicate-grace window).

#### T1#3 — Treasury as selection oracle

**Architect:** The Treasury already ranks ants by denarii-balance. Add
`scripts/polaris-ant-ranking.sh` that emits the ranking + flags bottom
N% + flags PREDICATE_PENDING. Backfill not strictly needed — current
balances are already a usable signal.

**Anti-Architect:** Backfill IS needed if the current balances reflect
v8.91 rebalance-era data, not the predicate-aware era. But Anti-
Architect concedes: the ranking is the operational thing; backfill
can come in a v9.25 follow-up. Refuse over-scope.

**Joint:** Ship `scripts/polaris-ant-ranking.sh` emitting per-ant
rank + recent activity + predicate status. Cuts deferred to v9.25
(operator-decided after seeing ranking + grace window).

#### T1#4 — Close the stigmergic loop

**Architect:** This is the change that makes "swarm" + "emergent"
true. New module `polaris_swarm/stigmergy.py`: `next_scan_priorities()`
reads recent Pheromone deposits, scores recurring + decayed-but-
returning marks, and emits an ordered list of (legion, node_id) tuples
that the next colony pass should examine first.

**Anti-Architect:** Concur. Specify: "recurring" = same `node_id`
emitted by ≥2 distinct commander ants in the last 24h; "decayed-but-
returning" = same `node_id` absent for ≥48h then re-emitted. Refuse
the term "emergent" in any code or docs (AP8 — vocabulary larping).
Use "recurrence-weighted" instead. The colony scheduler then reorders
deployments to investigate recurrence-weighted nodes first.

**Joint:** Ship `polaris_swarm/stigmergy.py` + integrate in
`colony.py`. Vocabulary: "recurrence-weighted ordering"; no
"emergent" / "swarm intelligence" claims in code.

#### T1#5 — Denarii-driven scheduling

**Architect:** Builds on T1#4. The `colony.py` scheduler should
consult Treasury balances when choosing per-ant cycle frequency:
ants in top-quartile balance get N cycles; bottom-quartile get N/4.
Broke ants (negative balance) get sampled minimally.

**Anti-Architect:** Concur, but pin a floor: NO ant gets sampled to
zero (that's deletion-by-proxy without Sanctum review). Minimum =
1 cycle per Saturn-pass (24h). Above floor, weight by quartile.

**Joint:** Ship denarii-weighted cycle allocation in `colony.py`
with hard floor = 1 cycle/24h per ant.

#### T1#6 — External oracle

**Architect:** Pipe two external signals into the HYDRA brief as
nodes the synthesis must reconcile: (a) `polaris_mac_launch.sh
status` exit code; (b) `ai-adversary.sh` exit code per constraint.
Both surface as `oracle:launcher` and `oracle:adversary:<C>` nodes
in the brief; the brief must explicitly state agreement or
divergence vs internal HYDRA findings.

**Anti-Architect:** Concur. "Oracle" framing is honest (these are
external truth-witnesses). The reconciliation requirement is the
load-bearing part — without it the oracle is decoration.

**Joint:** Ship external-oracle reading in `polaris_hydra/host.py`
(or new `polaris_hydra/oracles.py`) + brief synthesis must include
reconciliation block.

### TIER 2 — core hardening

#### T2#7 — Real signing path

**Architect:** Install `oqs-python` or `pqcrypto` in the venv;
integrate ML-DSA-65 (FIPS 204) behind `POLARIS_USE_REAL_PQC=1` env
flag; new `polaris_web/pqc_signing.py` module; smoke test that a
signed token verifies; document the migration path from current
deterministic strings to real signatures.

**Anti-Architect:** REFUSE half-implementation. If we ship the flag
+ scaffold but the flag doesn't work end-to-end, AP8 fires (larping
post-quantum readiness). Two acceptable scopes: (a) ship the
INTEGRATION with passing smoke test → "yes, behind flag, defaulting
OFF until operator opts in"; (b) ship NOTHING and Sanctum-defer with
explicit "real signing not shipped; current implementation is
deterministic" honest accounting. Anti-Architect prefers (a) if
oqs-python is installable in CI; (b) otherwise.

**Joint:** Attempt (a). If oqs-python install fails in CI in this
session, fall back to (b) with constitutional record. Either way,
the `token_value` documentation MUST be updated to honestly describe
the current state — no more "post-quantum signing" claim without a
working code path.

#### T2#8 — Concurrency harness

**Architect:** New `scripts/polaris-concurrency-harness.sh` (or
extension to existing `polaris-loadtest-tokens.sh`): N concurrent
threads issuing tokens for the same individual; measure
verifications/sec + record lock-contention events on
`uq_one_active_token_per_individual` partial unique index. Results
committed to `meta/load-results/YYYY-MM-DD.json` + summary in
ARCHITECTURE-OVERVIEW.md.

**Anti-Architect:** Concur. Specify the harness must report
**failures separately** from latency (e.g., "100 threads, 1 succeeded,
99 lost the race deterministically" is C3's success criterion, not a
failure). Don't measure-throughput-in-isolation; measure C3 behavior.

**Joint:** Ship harness; results committed; ARCHITECTURE-OVERVIEW.md
gets concrete throughput + contention numbers.

#### T2#9 — ZK build + exercise in CI

**Architect:** Verify the existing `.github/workflows/ci.yml` builds
`polaris_zk` and runs a prove-verify roundtrip. If not, add it.

**Anti-Architect:** Concur. Specify the roundtrip must be a REAL
proof — generating a Merkle commitment, proving membership of one
leaf, verifying. Not just `cargo test`. The CI failure mode if the
prover or verifier breaks must be loud and obvious.

**Joint:** Audit current CI; if prove-verify roundtrip not exercised,
add it. Ship the workflow YAML diff.

#### T2#10 — Swarm validation against ground truth

**Architect:** New `polaris_swarm/fixtures/` directory with
deliberately-broken schema + app states (e.g., schema with C3
violated, app with C5 inline script, audit table with mid-row
deletion). New `scripts/ai-swarm-validate.sh` runs the swarm against
each fixture and asserts which ants fire (true positive) + which
don't fire on healthy state (true negative). Outputs
precision + recall per ant.

**Anti-Architect:** Concur. This is the most directly Popperian
addition. The fixtures themselves are the operational falsifiability
machinery — an ant whose precision is < 0.5 against fixtures fails
T1#2 retroactively. Joint should formalize: precision threshold
< 0.5 OR recall < 0.5 → ant gets PREDICATE_PENDING flag.

**Joint:** Ship fixtures + validation harness. Ants below threshold
get auto-flagged.

### TIER 3 — the contribution

#### T3#11 — Agent-maintainable-architecture thesis

**Architect:** One-page document at `docs/THESIS.md` arguing: the
genuine novelty in Polaris is not the identity-token schema (those
exist) nor the post-quantum crypto (NIST-standardized); it is the
documented, structured, agent-maintainable architecture pattern
where: a `MISSION.md` constitution + risk classes + Sanctum protocol
+ Architect/Anti-Architect personas allow an LLM-driven cognitive
layer to safely evolve a code substrate without architectural drift.
Compare to: bare spec + context file + CI (the alternative). The
falsifiable claim: an engineer who has never seen Polaris should be
able to identify "what does this need" within an hour.

**Anti-Architect:** Concur on framing. REFUSE mythology vocabulary
(no "cognitive substrate" / "constitutional discipline" / "the
Sanctum" — those are insider terms). Use plain-English: "documented
agreement protocol," "explicit risk gates," "structured second-
opinion review." The page must read flat to a stranger.

**Joint:** Ship `docs/THESIS.md` one page, no mythology vocab,
falsifiable closing claim.

### TIER 4 — hygiene

#### T4#12 — Collapse narrative mass

**Architect:** Move full CHANGELOG to `archive/CHANGELOG-FULL.md`
(preserves AoR byte-identical). Slim `CHANGELOG.md` to a curated
index of last 10 ships + pointer to archive. Move journal/ + old
sanctum/ entries to `archive/` similarly.

**Anti-Architect:** SHARP refuse on archiving journal/ + sanctum/.
Those ARE the constitutional record per v8.20 audit-of-record
discipline. Moving them out of the working tree (operator-visible)
to an archive directory is a one-way pressure-reducer that the
agent will then never restore. The drift, six months out, is
predictable. Joint pattern: ONLY compress CHANGELOG.md (it's already
a fully-narrative summary; the per-ship detail is in git log + the
Sanctum files). Leave journal/ + sanctum/ in-place.

**Joint:** ARCHIVE CHANGELOG only. Move full content to
`archive/CHANGELOG-FULL.md`; new `CHANGELOG.md` is ~2000 words
covering the last 10 ships as one-paragraph summaries + pointer to
archive. Journal/ + sanctum/ untouched (they ARE the AoR).

#### T4#13 — Mechanical scope rule

**Architect:** Pre-commit hook check: total word count under
`meta/` + `DEVNOTES/` + `journal/` + `sanctum/` (narrative mass)
must not exceed N× word count under `polaris_sql/` + `polaris_web/`
+ `polaris_hydra/` + `polaris_swarm/` + `polaris_foresight/`
(core mass). Initial N = 2.0 (narrative may be 2× core; anything
beyond fails the hook with a printed ratio).

**Anti-Architect:** Concur on shape. Pin N empirically to the
current ratio + 0.1 (so the next ship has a small budget; future
ships compress). Also pin: any commit touching `polaris_swarm/`
without a corresponding edit to `meta/ant-predicates.md` fails the
hook (predicate-or-no-commit rule).

**Joint:** Ship `scripts/pre-commit-scope-check.sh`; add to
`.pre-commit-config.yaml`. Initial N = current ratio + 0.1.

#### T4#14 — CLAUDE.md = invariants + predicates + loop wiring

**Architect:** Trim CLAUDE.md hard. Keep: state-map header (current
version + recent 5 ships ONLY), constitutional invariants (C1-C10
one-line each), where-does-X-live pointer table, pre-known gotchas.
Move: full per-ship history (currently dominant), file-map prose,
patterns + recipes (already in patterns/), v2 done-list narrative.
Target: 200 lines.

**Anti-Architect:** Concur. Refuse the move from CLAUDE.md to a NEW
file (would just create CLAUDE-NARRATIVE.md and shift the bloat).
Joint pattern: things that move out of CLAUDE.md get DELETED from
CLAUDE.md and pointed to their existing home (CHANGELOG.md, file-
map already in docs/SYSTEM-MAP.md, patterns already in patterns/).
Net deletion, not net move.

**Joint:** Trim CLAUDE.md to ≤250 lines. Move references to
existing files where they live. Net delete; no new files.

---

## §III. Position selected — JOINT-MODIFIED (ship all 14 with debate-applied modifications)

### Items shipped per Architect proposal:

- T1#1 (with opt-out flag), T1#3 (without backfill), T1#4 (with vocab refusal), T1#5 (with floor), T1#6, T2#8, T2#9, T2#10, T3#11 (with vocab refusal), T4#13

### Items shipped with Anti-Architect scope reduction:

- T1#2 (predicate audit + deprecation mark, NOT immediate deletion)
- T2#7 (real signing scaffold; full integration depends on oqs install)
- T4#12 (CHANGELOG only; journal + sanctum NOT archived)
- T4#14 (net delete; no new narrative file created)

### Items added by agent: 0

### Items removed: 0

---

## §IV. Anti-Architect anti-pattern hits surfaced

- **AP1** (self-observation without ground-touch) — caught throughout; T1#1 fixes
- **AP4** (pattern-projection) — caught on ants without predicates; T1#2 operationalizes detection
- **AP7** (premature abstraction) — caught on "shift everything to archive" reflex; T4#12 scoped
- **AP8** (larping) — caught on "post-quantum" claim without real signing path; T2#7 forces honest accounting either way; caught on "emergent" vocabulary in stigmergy; T1#4 banned the term

Four of eight catalogued anti-patterns fire substantively. The pattern
itself — VANTA's critique surfacing four AP-class violations the
cognitive layer was missing — is the operational proof that the
Anti-Architect was an undershipped construct in v9.11 and the BIG
MISSION (v9.23) Anti-Architect work continues here.

---

## §V. Vocation alignment

Per v9.11 vocation:

- T1#1: ANTI-COERCION-INFRASTRUCTURE (a coerced operator cannot ship
  past an ALERT-level finding without leaving an opt-out audit trail)
- T1#2-T1#6: ANTI-COERCION-INDIRECT (predicate-based observation
  prevents narrative-cover; recurrence-weighted scanning surfaces
  patterns a coercer might want hidden)
- T2#7: ANTI-COERCION-DIRECT-or-honest-accounting (either real PQ
  signing protects against future-quantum coerced re-signing OR
  honest accounting prevents reliance on a stub)
- T2#8: ANTI-COERCION-NEUTRAL (performance characterization)
- T2#9, T2#10: ANTI-COERCION-INFRASTRUCTURE
- T3#11: ANTI-COERCION-INDIRECT (lowering inspection barrier;
  documented agent-maintainable pattern = more eyes on the system)
- T4#12, T4#13, T4#14: ANTI-COERCION-INFRASTRUCTURE (narrative-mass
  bounded prevents a coerced operator/agent from drowning a signal
  in noise; pre-commit gate prevents silent scope creep)

11/14 anti-coercion positive; 3 infrastructure-hygiene; 0 negative.

---

## §VI. Outcome

Ship as v9.24. 14 items. The cognitive substrate moves from
*advisory* to *binding*; the core's headline crypto claim gets
either substantiated or honestly accounted; the narrative mass
gets bounded by mechanical rule.

**The Anti-Architect's critique above is the constitutional record
that the work was done with the contest, not around it.**

Authorization: VANTA, in-chat 2026-05-16: "Mission for the architect /
anti architect."

**SHIPPED 2026-05-16 as v9.24.** New artifacts + invariants pinned +
state-map + sanctum-index + journal.
