# The story of Polaris

A non-technical account of how the system was built. Read for context; read [MISSION.md](../../MISSION.md) for the constitution and [CHANGELOG.md](../../CHANGELOG.md) for the audit-of-record.

Covers v1 (April 30, 2026) through v8.58 (May 13, 2026).

---

## I. The setup

Polaris was a database course project. SCS-230, Seton Hill University, Spring 2026. Egor Khaklin, the author, set out to build a national identity token reference implementation: one physical artifact per person, consolidating the six to eight credentials Americans currently carry across unrelated authorities.

The brief was modest. A relational schema. A handful of stored procedures. A web application that showed every use case. A few diagrams in a LaTeX report.

The first version arrived as expected. Twenty-three tables. Seven core use cases. Sample data for eight notional individuals across four jurisdictions. A Flask application with the Gotham aesthetic of an operational intelligence surface rather than a portal. A 36-page LaTeX report. Everything tested.

Then the cybersecurity audit happened.

v4 was supposed to be a small pass. Add CSRF tokens. Set a Content Security Policy. Rate-limit the login form. The audit surfaced fifteen issues. Half of them were straightforward. The other half exposed a category of problem the schema had not been built for: cryptographic compulsion. Coercion. Loss. Issuer overreach. Threat models that existing identity systems do not answer, that real adversaries do reach for, that an academic project could have ignored but the author would not.

The decision to expand scope arrived implicitly. v5 added a self-healing macOS launcher and the operational atlas with its live globe. v6 scaled the system to two million synthetic events, found and sealed every race condition the design had not anticipated. v7 added cursor pagination, swapped the in-memory rate limiter for Redis, hardened a dozen schema invariants the test suite had been silent about.

By v8.0 the surface was stable. The system loaded clean, ran clean, tested clean. The author had a Spring 2026 portfolio piece that exceeded the course brief by an order of magnitude.

He could have stopped there.

---

## II. The substrate problem

On May 9, 2026, the author opened **v2**: a second mission, layered on top of the first.

The PDF accompanying the project report had named six open problems in §9. Cryptographic compulsion. Catastrophic loss. Issuer concentration. Quantum migration. Public auditability without privacy loss. Issuer overreach. The author had answered them rhetorically in the report. v2 would answer them structurally, in code, with tests.

He listed twelve work items as M2-1 through M2-12 and indexed them against five strategic arcs labeled A through D. Arc A was the open-problems triad (PDF §9 directly). Arc D was the cryptographic substrate the answers would rest on: real Merkle anchoring, real ZK-SNARKs, real federation primitives, real duress mechanisms.

On May 11, 2026, twelve ships shipped in a single day.

The launcher and journal logs both survive. The first ship landed at the beginning of the day with R10-2, functional DID anchoring, a Merkle batch layer whose schema commitment was binding immediately and whose external-ledger push was operator discretion rather than auto-derivation. By mid-day the issuer federation had landed with explicit-only trust attestations and no transitive inheritance. By evening a Plonky2 ZK-SNARK prover compiled in Rust under the nightly toolchain was producing proofs of Merkle inclusion over closed token-state epochs.

The duress mechanism shipped near midnight. It is the substrate's most delicate piece: a second secret embedded in the holder's enrollment that produces an indistinguishable verification when supplied under coercion, silently recording a DuressEvent that the operator's screen cannot reveal. The R6 audit refinement, named at the Sanctum that authorized the ship, became a structural test in the codebase: no operator-visible template may join to the DuressEvent table. The check runs on every continuous-integration pass.

By the end of May 11, the v2 done list was 11 of 12. The last item, R11-5 / M2-10 / duress codes, had been the closer. Six Sanctums had been opened and closed that day. Eight new schema tables. Six advisory-lock granularities now exist in the catalog, one for each ship-touching contention class.

The author called the day a rampage in the changelog, not as celebration but as warning. Days like that produce drift faster than the documentation can absorb. The next morning would have to be reconciliation.

---

## III. The governance layer

The reconciliation became the third project.

The first project was the identity system. The second was the cryptographic substrate. The third was the discipline that kept either of them from collapsing under their own complexity.

It already existed in fragments by v8.0. A `MISSION.md` constitution that named ten hard constraints. A `ROADMAP.md` backlog by risk class. Per-day journals capturing decisions as they happened.

v8.19 formalized what had been ad-hoc. The **Sanctum protocol**: every non-routine decision (MEDIUM or HIGH risk, cross-arc, touching governance itself) produces a structured record. The agent surfaces options. The operator chooses. The record is written. Reading the Sanctum sessions in order, indexed at [`meta/sanctum-index.md`](../../meta/sanctum-index.md), is reading the system's strategic biography.

v8.20 introduced the **audit-of-record principle**: every consequential decision writes its evidence at the moment of decision, in append-only structures, with no rewriting or back-dating. Schema tables and filesystem directories both serve as audit-of-record instances. The CHANGELOG itself is one. The journal is another. The Sanctum directory is the third. The append-only triggers on TokenLifecycleEvent, VerificationEvent, EnrollmentStatusEvent, AnchorBatch, AgencyTrustAttestation, TokenStateEpoch, DuressEvent are the schema instances. The principle is documented at [`DEVNOTES/audit-of-record.md`](../../DEVNOTES/audit-of-record.md).

v8.30 elevated all of this into the constitution proper. MISSION.md named the governance contract: the Sanctum protocol, audit-of-record, and three risk classes (LOW / MEDIUM / HIGH). These principles are stable; the tools that enforce them are substitutable. A future agent may replace any of the enforcement machinery without amending the constitution, provided the principles still hold.

v8.31 resolved the post-v2 strategic moment. With the v2 done list closed at 12 of 12 and the publication gate not yet open, the question arose: open v3 or hold steady-state? The decision favored steady-state on game-theoretic grounds: no external trigger had fired, autonomously inventing v3 would risk drift, and reversibility favored holding. VANTA approved. MISSION.md was amended. Three external triggers were named that could open a future arc: production deployment, a partner consumer, or a novel arc with documented external cause. The default posture for ambiguous requests became **decline-and-surface**: explain why a request crosses the steady-state boundary, name the trigger that would be needed, wait for explicit authorization.

The discipline that survives today is leaner than what grew here through May 2026. C1 through C10 plus the anti-coercion Vocation are the constraints; they are enforced at the database level via triggers, partial unique indexes, and CHECK constraints. The flat check layer in [`polaris_checks/`](../../polaris_checks/) is the machine-checkable enforcement of most of them, one `check_*(repo_root)` function per constraint, gating CI via `python3 -m polaris_checks.run`, with tested detection correctness. The Sanctum protocol, audit-of-record, and the risk classes remain the live agent contract.

---

## IV. Publication

On May 12, v8.35 ran the first publish-readiness pass. A license recommendation was worked through. Three were on the table: MIT (permissive, no patent grant), Apache 2.0 (permissive, patent grant, attribution), GPL (copyleft). Apache 2.0 won out: patent grant for the cryptographic substrate, preservation of attribution for the architectural patterns, industry-standard for academic publication, no copyleft friction for downstream integrators. VANTA replied "yes Apache."

The publish-readiness pass added `LICENSE` (the full Apache 2.0 text), `NOTICE` (author attribution plus Plonky2 / D3 / TopoJSON / Flask component notices plus the PDF inheritance clause), `.gitignore` (macOS, Python, Rust, Node, IDE, runtime state), a CSP-compliant dropdown coordinator at `polaris_web/static/nav-dropdown.js`. The repository purged 328 MB of `polaris_zk/target/` Rust build artifacts plus 680 KB of Python `__pycache__` plus five `.DS_Store` files. The repo size went from 335 MB to 6.3 MB.

v8.36 ran the final pre-publish gate. A ten-layer audit. README test counts updated. The ZK prover build instructions added to README. A redis environment-flake resolved on a fresh container. Three build artifacts regenerated by the test runner were re-cleaned. The Sanctum titled _final pre-publish approval_ closed with VANTA's verdict: _proceed with recommendation_. The fourteenth Sanctum. Polaris was final-gate approved.

Per the §IV clause of the publish-readiness Sanctum, the agent does not initiate the actual `git push`. Publication is the operator's step, on the operator's terms. The agent prepares; VANTA ships.

What followed was the post-publication maintenance era. Iteration protocol: every ship closes a parked item and surfaces the next. The pattern realized seven times across v8.44 through v8.50. CSP externalization (eight inline-JS sites moved to external files). Five new schema CHECK constraints. A no-FK-CASCADE structural guard. A duress-event append-only test.

Two bug-fix iterations came in from real-user reports. v8.51 fixed half of "localhost refused to connect" (browser-background `setInterval` throttling combined with a 45-second stale-heartbeat threshold producing false-positive teardowns). v8.55 fixed the other half (`pagehide` and `beforeunload` listeners firing `sendBeacon('/api/quit')` on every page navigation, not just tab close). v8.56 closed the auth-hygiene gap (session cookies surviving container restarts; rotate `POLARIS_SECRET_KEY` on every launch). v8.58 closed the launcher's early-return loophole that bypassed rotation when the stack was already healthy.

Each bug-fix ship added a new test guarding the regression. The launcher-watch-mode family of guards is now five tests deep, pinning every load-bearing property the launcher relies on.

---

## V. What the system is now

A working national identity infrastructure. Twenty-five tables, thirteen stored procedures, fifty-three HTTP routes, an operational atlas with a live globe, a Plonky2 ZK-SNARK prover in Rust, a duress mechanism that recovers under coercion, a recovery ceremony that handles catastrophic loss, a federation primitive that resists issuer concentration, a multi-signature transitional state that survives quantum migration.

Layered testing. SQL self-tests; Python integration tests; Hypothesis property tests against C1, C2, C3 and the M2-12 redaction proof; the flat invariant checks in `polaris_checks/` guarding C1 through C10.

A governance contract. The Sanctum protocol, audit-of-record, and three risk classes (LOW / MEDIUM / HIGH). The C1-C10 constraints plus the anti-coercion Vocation, enforced at the database level and machine-checked by `polaris_checks/`.

A publishable repository. Apache 2.0 licensed. A double-click launcher that gets all of it running on a Mac with Docker Desktop installed.

Sixty ships across thirteen days. Two single-day rampages. Many formal strategic-consultation records. One academic project that decided, at v4, to take the threat models seriously and never stopped.

---

## Arc B — production opens (May 14)

The architectural sophistication was outpacing the deployment story. Polaris had ML-DSA-65, Plonky2 ZK-SNARK, multi-sig migration, duress codes, federation, anchor batches, many audit-of-record instances, and a Mac-only dev launcher.

A reference implementation that no real operator could deploy was not actually a reference.

VANTA revoked the v8.31 steady-state contract. The third trigger condition (novel arc with documented external cause) fired. **Arc B, production deployment,** opened. Phase 1 was ten deliverables, shipped in one day:

- A 700-line operator runbook and a 400-line secrets primer
- A multi-stage `Dockerfile.prod` (Rust ZK builder, Python deps builder, slim non-root runtime) bundling the Plonky2 prover at `/opt/polaris/zk`
- A `docker-compose.prod.yml` with Caddy + app + Postgres + Redis, file-mounted secrets, internal network with only TLS exposed
- A `Caddyfile` declaring auto-TLS via Let's Encrypt, the canonical security-header set, edge rate-limit, HTTP→HTTPS redirect
- `/api/health` rewritten to a structured-JSON contract: per-component checks (database, redis, zk_binary, disk) with overall status as worst-of, HTTP 503 on unhealthy
- An idempotent `polaris-deploy.sh` with smoke + rollback
- A manifest-hashed `polaris-backup.sh` with `--verify-latest`
- Secret lifecycle scripts: `polaris-generate-secrets.sh` + `polaris-rotate-secret.sh`
- A strategic record at `meta/arc-b-production.md`
- Three new structural guards: TLS required, no env-secrets in prod, structured `/api/health`

The governance contract was preserved verbatim. C1-C10 preserved. Only the operating posture changed, from decline-and-surface to active-production. The macro scan identified the next ships (documentation completeness, UX polish, WebAuthn for operator auth, audit-log archive policy).

---

## The day after Arc B opened — five waves in twelve hours

The Arc B opening was supposed to be the day's ship. It became the day's seed.

### Wave 1 — completeness (v8.78, v8.79, v8.80)

ARCH-002 closed the documentation gap that opened the moment Arc B Phase 1 shipped. The data model missed four affordances. The API doc predated the structured-JSON health contract. PRIVACY didn't acknowledge file-mounted secrets. New tests made all of that mechanically enforced going forward.

ARCH-003 closed the first-impression gap. The root URL had been a bare login form. New landing page; new demo page (a four-step walkthrough of a token's life, issue, activate, verify, revoke, naming the constraint enforced at each step); refreshed error template; six hundred lines of CSS; the `dashboard()` route moved from `/` to `/dashboard` so first-time visitors landed in narrative rather than authentication. New tests kept the public surface from regressing.

ARCH-004 closed the longest-standing soft signal in the project: a coherence check had flagged "schema has forty-one CHECK constraints; tests reference sixteen" since the v8.20-era audit-of-record discipline shipped. The regression suite that closed the gap was sixty-two tests across twenty-one classes, one transaction per test, rolled back at teardown, no state surviving. The two most-important were the dedicated C2-enforcement tests on `chk_disclosure_token_consistency`: zero-knowledge events must have null token IDs, full disclosure events must not. Without those tests, the privacy invariant the project's reference-implementation claim depends on was *claimed* but not *verified*.

### Wave 2 — backup-restore loop closure (v8.81, v8.82)

`polaris-restore.sh` was the inverse of v8.77's `polaris-backup.sh`. Manifest verification, transaction-protected restore, refusal to clobber non-empty databases without `--force`, dry-run mode that listed components without applying. The drill that proved it: real backup of the test database, real restore into a fresh one, identity tokens and lifecycle events all matching the seed.

The drill also surfaced two bugs in the v8.77 backup script's verify mode: a MANIFEST.json lookup at the wrong directory level and an argparse antipattern where `shift` inside `for arg in "$@"` doesn't advance the iterator. Both fixed same-commit. A broken verifier trains operators to ignore output, so a verifier that lies is worse than no verifier at all.

### Wave 3 — scaling foundations + the constitutional question (v8.83, v8.84)

pgbouncer slipped between the app and Postgres. Transaction-pooling mode, sensible defaults, no host-port exposure. The production stack now multiplexes thousands of short-lived app connections onto a handful of long-lived backend ones, the connection-saturation safety net every real deployment needs above fifty concurrent operators. OPERATIONS gained a Scaling section that named five concrete inflection points with concrete recipes.

Then `polaris-archive.sh` shipped, and surfaced the constitutional question. Polaris's storage-growth section had named "audit-log archive policy" as a future Phase 2 ship. The policy has two halves: *export* old audit rows to durable cold storage, and *delete* the exported rows from hot tables to bound `pg_data` growth. The export half was mechanical and shipped, eleven audit tables CSV-exported into manifest-hashed tarballs with explicit `deletion_from_hot: false` field. The delete half touched C1's append-only invariant.

Rather than ship the deletion half autonomously, the agent surfaced the question via OPEN Sanctum with three positions on file: A (literal C1, no deletions ever), B (archive-then-delete carve-out with a `LifecycleArchiveCheckpoint` audit-of-record), C (PostgreSQL partitioning). The strategic review recommended B; the Sanctum waited for VANTA.

This was constitutional discipline in action. Heavy-production accelerates execution; it does not skip Sanctum.

### Wave 4 — the strategic turn (v8.85, v8.86, v8.87, v8.88)

VANTA asked what the strategic review recommended. The diagnostic surfaced:

- A staleness: the strategic brief still framed moves in v8.31 *steady-state* language ten ships into heavy-production. The revocation hadn't been threaded through the brief generator. v8.86 wired `is_heavy_production()` keyed on the revocation Sanctum's file presence (audit-of-record-anchored, not env-var-flagged); the Strategic Outlook section now surfaces "ship the complete thing" as the default response shape under heavy-production.
- The constitutional question. VANTA selected Position B. v8.87 shipped the carve-out end-to-end: `LifecycleArchiveCheckpoint` table strictly append-only at full strictness (no carve-out at this layer because the checkpoint chain IS the audit-of-record); `reject_audit_modification()` trigger function rewritten with a GUC-keyed DELETE carve-out (UPDATE still rejects unconditionally); `uc_archive_purge()` procedure that validates admin role + cutoff + SHA-256 then sets `LOCAL polaris.purge_in_progress='TRUE'` for one transaction; `polaris-purge.sh` operator wrapper that computes the SHA-256 and reports the resulting checkpoint. The drill purged thirty-seven rows from a sixty-row archive while a parallel DELETE attempt on a non-purged audit table was still rejected, the carve-out re-closing at the transaction boundary exactly as designed.

Then v8.88 closed the last queued recommendation: R8-4 PostGIS migration Phase 1 foundation. The optional-dependency design, a DO-block that checks `pg_available_extensions` before `CREATE EXTENSION` and emits a NOTICE if not available, let the schema deploy cleanly with AND without PostGIS. Generated `geography(Point, 4326)` columns on the two lat/lon-bearing audit tables. GiST indexes ready for the Phase 2 atlas function rewrite when a 10M-event benchmark environment exists.

### Wave 5 — the day's macro scan + this brief (v8.89)

The strategic priority queue is now empty for the first time since the v2 close. v8.89 is the cleanup pass: a real `bigint out of range` bug discovered and fixed in the seed-generation path; STORY.md continued through the day's ledger; the prior-recommendation tracking refreshed to the current cycle.

## Where the story stands

**Fourteen ships in eighteen hours.** Sanctums opened and closed in a single day. Schema audit-of-record instances plus filesystem instances plus the new constitutional `LifecycleArchiveCheckpoint`. Three new structural guards for production deploy plus the constitutional carve-out.

The production-deployment story begins with `./scripts/polaris-generate-secrets.sh && ./scripts/polaris-deploy.sh prod`. The day-two-operations story ends with `polaris-backup.sh` → `polaris-restore.sh` → `polaris-archive.sh` → `polaris-purge.sh` → `polaris-rotate-secret.sh`, every operator workflow scripted, manifest-verified, structurally enforced, documented end-to-end.

The constraints enforce themselves: C1 through C10 hold at the database level via triggers, partial unique indexes, and CHECK constraints, and the flat `polaris_checks/` layer machine-checks them on every CI pass. The Sanctum protocol, audit-of-record, and the risk classes keep decisions on the record.

Heavy-production posture remains active. What comes next will follow from one of three things: real production usage with real operators surfacing real gaps; a fresh VANTA directive; or a documented external cause for a new arc.

---

## Postscript

The trick of Polaris, if there is one, is that the three projects (the identity system, the cryptographic substrate, the governance layer) are not three projects. They are one project with one quality bar.

The bar is the author's, recorded in [`DEVNOTES/style.md`](../../DEVNOTES/style.md): _holy shit, that's done_. No workarounds. No tabling for later. Tests and documentation alongside code. The marginal cost of completeness is near zero when the work is in flight; the cost of an unfixed thread compounds across sessions.

A system built to that bar produces, at sufficient scale, its own infrastructure. The governance layer did not arrive as a deliberate goal; it arrived as the answer to "how do we keep doing this without drifting from what we said we were doing."

The system is small enough that one person plus an AI agent can hold all of it. The Sanctum records, the `polaris_checks/` invariant layer, the audit-of-record principle: each of those is a hedge against the moment they cannot.

If you build on Polaris, build to that bar.
