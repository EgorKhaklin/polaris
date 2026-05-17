# Sanctum: watcher-coverage-completion

**Date:** 2026-05-17
**Petitioner:** agent (Claude, Opus 4.7) — joint Architect / Anti-Architect petition
**Principal:** VANTA
**Trigger:** ai-watcher-coverage surfaced 27 schema tables with no watcher
reading them (HYDRA / Mycelium blind spot). Surfaced during self-improvement
loop 2026-05-17, item #6 of the MEDIUM/HIGH dispatch list. VANTA's earlier
scope answer (this session) deferred this HIGH item for explicit operator
authorization.
**Risk class:** HIGH (structural — touches HYDRA watcher inventory and/or
the schema-watcher's `expected_tables` set; choice between three positions
has materially different ship costs).
**Status:** DECIDED + CLOSED (Position C+B-trigger selected by VANTA in-chat 2026-05-17 via AskUserQuestion; shipped same-day under heavy-production loop directive)
**Architect brief ID:** n/a — structural; surfaced by ai-watcher-coverage,
not a per-ship Architect brief.

---

## I. The Matter

Of 40 tables in the `polaris_test` schema, 27 are not read by any HYDRA
watcher (per `scripts/ai-watcher-coverage.sh §III`). The cognitive layer
therefore makes claims about "watching the substrate" that — at the
table-level — are 67.5% incomplete. The question is what to do about
the gap: build coverage for all 27, prioritize a subset, or accept the
gap with explicit per-table rationale.

## II. Preparation

- **Architect brief:** journal/2026-05-17-architect.md (in-session) +
  prior brief at journal/2026-05-16-architect.md.
- **Self-improvement loop journal:** journal/2026-05-17.md (decisions
  recorded earlier this session: bare-ref cleanup, treasury display fix,
  predicate strengthening, Foresight tightening, Miller's-7 exemption).
- **The 27 unwatched tables** (full inventory, per
  ai-watcher-coverage.sh §III):

  **Identity-layer (HIGH-priority — auth and token surface):**
  AppUser, AuthAuditLog, AuditAccessLog, IdentityToken, Individual,
  TokenSignature, TokenLifecycleEvent, TokenPermission,
  OperatorWebauthnCredential, DeviceBinding, RecoveryRequest,
  EnrollmentStatusEvent, IndividualCurrentEnrollment, DuressEvent (14)

  **Agency-federation surface (MEDIUM-priority):**
  Agency, AgencyAlgorithmAuth, AgencyTrustAttestation,
  IssuerDiscretionPolicy (4)

  **Cryptographic / anchoring surface (MEDIUM-priority):**
  CryptographicAlgorithm, BlockchainAnchor, AnchorBatch, RevocationList,
  GenomicAnchor, QuantumObserverBinding (6)

  **Verification surface (HIGH-priority):**
  VerificationContext, VerificationEvent, ActiveTokens (3)

- **Architect's prior position** (from in-session dialogue):
  Coverage-completion is a 1-week arc; not steady-state work; must be
  scoped explicitly. Reject implicit-expansion via the loop.
- **Anti-Architect's prior position:** AP2 (Sanctum-overuse: 59 in 7
  days). Opening this Sanctum is itself a measured cost. If the
  decision is "C: accept the gap," no further ceremony required and
  the cost is bounded. If "A: build all 27," the work compounds the
  file-churn signal trajectory_watcher is already flagging.
- **Blast radius (per position):**
  - **Position A:** ~27 new ant files in polaris_swarm/ants/ +
    updates to legio_*.py registrations + 27 new structural-invariant
    tests + meta/ant-predicates.md additions + CHANGELOG entries.
    Estimated ~1500-2000 lines added across ~30 files.
  - **Position B:** ~10-14 new ant files (auth-surface priority).
    Estimated ~600-800 lines across ~15 files.
  - **Position C:** Update ai-watcher-coverage.sh to recognize a
    per-table exemption marker (in 01_schema.sql comments); annotate
    each of the 27 tables with the rationale. ~50 lines code change +
    27 schema-comment additions.
- **Tests planned:**
  - Position A: 27 new ants × ~3 tests each = ~81 new test functions
  - Position B: ~10-14 new ants × ~3 tests each = ~30-42 new tests
  - Position C: 1 new test (exemption marker is parseable) + 1
    invariant (every unwatched table has a marker)

---

## III. Alternatives considered

### Position A — Build watchers for all 27 tables ("complete coverage")

For every unwatched table, write a watcher (or extend an existing
watcher's `expected_tables` set + add the matching domain-specific
checks). Result: ai-watcher-coverage.sh reports 0 blind spots; HYDRA's
"watching the substrate" claim becomes literally true at the
table-level.

**Strength.** Closes the structural gap. Eliminates the entire class
of "cognitive layer makes a coverage claim it can't substantiate."

**Weakness.** Compounds three signals the swarm is currently flagging:
- trajectory_watcher's file-churn cluster (`polaris_web/` 86% — adding
  ~30 files in polaris_swarm/ would partially redirect churn but the
  net effect is still a churn-burst).
- Anti-Architect AP2 (process-burst).
- The Architect's own observation from earlier in this session: "the
  Architect surfaces drift, not opportunities." 27 new watchers is an
  opportunity-driven expansion, not drift-correction.

**Estimated time.** ~1 week of focused work. Crosses the steady-state
contract; needs explicit operator authorization to commission.

### Position B — Prioritized coverage (10-14 auth/token tables)

Build coverage for the identity-layer subset only (AppUser,
AuthAuditLog, IdentityToken, Individual, TokenSignature, etc.). These
are the surface where C2 (zero-knowledge), C3 (one identity per
person), and C4 (atomic failed-login) live. The verification surface
(VerificationEvent, VerificationContext, ActiveTokens) is also HIGH-
priority. Defer the agency-federation + crypto-anchoring tables
(MEDIUM-priority) to a future arc.

**Strength.** Closes the load-bearing half of the gap. Aligns with
the vocation (anti-coercion) because the unwatched identity surface
is precisely where coercion would manifest. Bounded scope (~3 days).

**Weakness.** Leaves the structural claim partially true — HYDRA can
still say "watches the substrate" but the operator must remember which
14 of 27 tables are actually watched. AP6 (incomplete-but-claimed) is
the failure mode.

**Compounding.** If Position B ships, the remaining 13 tables are by
implication "exempt by current choice" — close to Position C's posture
on the remaining set, just without the per-table rationale yet
recorded.

### Position C — Accept the gap with explicit per-table exemption rationale

The 27 tables have varying load-bearing-ness. Some (Agency,
SystemDependency) are essentially configuration — drift on those is
caught by schema migrations, not by runtime watchers. Some
(LifecycleArchiveCheckpoint, schema_version) are watched implicitly
because the schema-watcher checks for their existence and the
trigger-set that depends on them. For each of the 27, write a one-line
rationale in 01_schema.sql comment that explains either "intentionally
unwatched because X" or "watched indirectly via Y."

Extend ai-watcher-coverage.sh to parse these markers. Tables with a
rationale become "exempt with rationale" (positive signal) rather than
"blind spot" (negative signal). The structural claim becomes "every
table is either watched or has a recorded reason for not being
watched."

**Strength.** Closes the structural claim with the least churn.
Surfaces the operator's actual mental model (some tables don't need
direct watchers because they're caught upstream). LOW-effort; ~50
lines of code + 27 schema comments. Doesn't trigger the file-churn
signal. The drift→test discipline is preserved: every claim has a
test (the marker parse).

**Weakness.** The cognitive layer's coverage *claim* becomes weaker —
"every table is either watched or exempt" is a softer guarantee than
"every table is watched." A future regression where a load-bearing
table gets accidentally added to the exempt list would be silently
permitted. (Mitigation: the exemption rationale text must be
non-empty AND non-template, checked by the parser.)

**Compounding.** Doesn't preclude Position B in the future — exempt
tables can be re-classified to watched in a later ship if drift on
them emerges.

---

## IV. Recommendation

**Position C, with an opening clause toward future Position B work on
the identity-layer subset specifically.**

The recommendation rests on five observations from this session's
joint dialogue:

1. **The gap is not currently producing drift.** No load-bearing
   table is actively suffering from unwatched-ness in the operational
   record — failure modes on AppUser are caught by `tg_appuser_*`
   triggers (C4 atomic failed-login); failure modes on
   IdentityToken are caught by `uq_one_active_per_person` (C3);
   AuthAuditLog is enforced append-only at the trigger layer. The
   coverage gap is at the *cognitive-layer claim* level, not at the
   *runtime safety* level.

2. **The Anti-Architect's AP2 warning is current** (59 Sanctums in
   the trailing 7 days, 0 ships). Opening a multi-week coverage arc
   would compound rather than resolve the process burst.

3. **The Architect's own drift→test discipline** says: every drift
   catch should be testable. Position C makes the per-table exemption
   testable (parser + invariant); Position A makes coverage testable
   per-table but commissions much more work.

4. **MISSION.md §Vocation** is the load-bearing test. Position C
   does not weaken anti-coercion guarantees because the existing
   trigger / unique-index / constraint layer ALREADY enforces the
   load-bearing claims at the schema engine. The watchers are a
   cognitive-layer secondary surface, not the primary defense.

5. **Future-Position-B is preserved.** If a specific identity-layer
   blind spot manifests as real drift, the exemption can be flipped
   to a real watcher in a focused future ship. Position C doesn't
   close the door; it just doesn't force-open it now.

**The Architect's vote:** C with reservation. "I would prefer A
philosophically — coverage SHOULD be complete — but the trajectory
signal says now is not the time."

**The Anti-Architect's vote:** C strongly. "The 27 tables have been
in this state for the entire v9.x cycle without producing a single
production-class drift signal. The gap is theoretical, not
operational. Don't ship theory."

**Joint reconciliation:** C. The 27 tables get rationales in the
schema; ai-watcher-coverage becomes the executable check that every
table has either a watcher OR a recorded exemption. If a specific
table's rationale ever becomes false, that's a Sanctum trigger for a
focused B-style fix on just that table.

---

## V. What's needed from VANTA

Choose one of:

- **A** (build all 27 watchers — commission the arc)
- **B** (build the identity-layer subset; ~3 days)
- **C** (accept gap with per-table exemption rationale; ~1 hour)
- **C+B-trigger** (C now, with named conditions under which we'd
  upgrade to B — e.g., if any identity-layer table starts producing
  drift findings the schema-watcher misses)
- **defer** (close this Sanctum without decision; reopen when drift
  surfaces or operator commissions Phase 4 production hardening)

The agent recommends **C+B-trigger** as the maximally-honest
position. Architect philosophical preference is A; Anti-Architect
strong preference is C; the named-trigger clause is the bridge.

---

## VI. Decision

**Position C+B-trigger** selected by VANTA in-chat 2026-05-17
("C+B-trigger (Recommended)" via AskUserQuestion).

**Operative clauses:**

1. Each of the 27 unwatched tables receives a per-table exemption
   rationale, recorded as a structured SQL comment in
   `polaris_sql/01_schema.sql` using the marker
   `-- coverage:exempt — <rationale>` directly above the
   `CREATE TABLE` line. The rationale text must be non-empty and
   non-template (the parser rejects placeholders like "TODO" or
   "fill in").
2. `scripts/ai-watcher-coverage.sh` is extended to parse these
   markers and report "exempt with rationale" as a positive signal
   distinct from "blind spot."
3. A new structural invariant is added asserting that for every
   table without a watcher, an exemption rationale exists. This
   converts the cognitive-layer claim from "every table is watched"
   to the testable "every table is either watched or has a recorded
   reason for not being watched."
4. **B-trigger clause:** any identity-layer table that subsequently
   produces real drift findings the schema-watcher misses promotes
   to Position B — a focused watcher build for that specific table,
   under its own Sanctum decision.

## VII. Outcome

**Shipped 2026-05-17 in-session (no version bump — session-level
hygiene under the heavy-production-loop directive; bundles into a
future v9.25 ship along with the predicate-strengthening and
DEVNOTES work from the same loop).**

**Implementation:**

1. **`polaris_sql/01_schema.sql`** — added 26 `-- coverage:exempt —
   <rationale>` markers, one per unwatched table (the 27th apparent
   "blind spot" was a `CREATE TABLE so that` false positive in a
   comment, fixed at parse-time by stripping line-comments before
   regex extraction). Rationales are domain-specific: AoR (C1)
   triggers, partial unique indexes (C3), atomic procedures (C4),
   trigger-layer constraints (C7), atlas-cap enforcement (C8), and
   scaffold tables (M2-4, M2-5). Each rationale names the trigger or
   procedure that holds the constitutional claim.

2. **`scripts/ai-watcher-coverage.sh`** — parser hardened against
   the comment false positive (CREATE TABLE extraction now strips
   `--` line-comments before regex match). New §III logic
   distinguishes:
   - **Tables no watcher reads AND no exempt marker** (true blind
     spot — would fail the structural invariant)
   - **Tables exempt-with-rationale (Position C, 2026-05-17)** —
     positive coverage signal, NOT a blind spot

3. **`polaris_web/test_structural_invariants.py`** — new test class
   `TestSanctum_WatcherCoverageCompletion_2026_05_17` with 4
   structural invariants:
   - `test_every_table_watched_or_exempt` — the contract
   - `test_no_placeholder_rationales` — Anti-Architect's marker-honesty
     clause; rejects TODO/TBD/<10-char rationales
   - `test_exempt_markers_reference_real_tables` — orphan-marker
     regression guard
   - `test_sanctum_file_exists_and_decided` — provenance check on this
     Sanctum file itself

4. **B-trigger named:** any identity-layer table that produces real
   drift findings the schema-watcher misses promotes to a focused
   watcher-build under its own Sanctum. The trigger is operator-named:
   "I see a coverage gap on table X that the schema-watcher missed in
   incident Y" → opens
   `sanctum/<date>-watcher-buildout-<table>.md` with Position B scope.

**Drill verification:**

```
$ scripts/ai-watcher-coverage.sh | grep "III\." -A2
§III. Coverage blind spots
  Every schema table is either watched or exempt with rationale.
  Tables exempt-with-rationale (Position C, 2026-05-17): 26

$ python -m unittest test_structural_invariants.TestSanctum_WatcherCoverageCompletion_2026_05_17 -v
Ran 4 tests in 0.015s — OK
```

**Mission marks:**
- CM (cognitive-layer self-monitoring): claim "watches the substrate"
  is now operationally true (every table is either watched or has a
  recorded reason for not being watched).
- C1 (AoR): preserved — no triggers modified; the exemption
  rationales merely SURFACE the existing trigger-layer enforcement.
- Vocation (anti-coercion): preserved — identity-layer rationales
  explicitly name the constitutional clause each table satisfies
  (C2, C3, C4, C6, C7).

**Pattern alignment:** Architect's drift→test promotion (the catch is
testable: 4 new structural invariants). Anti-Architect's "don't ship
theory" honored (no new watchers built; just made the existing claim
testable). Joint reconciliation achieved.

**Journal:** journal/2026-05-17.md (final decision entry of the
self-improvement loop iter-2).

**Closing line:** Status transitions OPEN → DECIDED + CLOSED.
