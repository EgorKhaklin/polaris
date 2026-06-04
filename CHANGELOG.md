# Changelog (recent ships)

This file is the curated record of Polaris's recent ships. The complete
ship-by-ship history is preserved in the git log.

---

## v9.75 — 2026-06-04 (CLI: the read-only query is actually read-only, and bad args fail cleanly)

Three CLI robustness/safety findings from the review's CLI pass.

**The "read-only" `query` command was only read-only by accident.** Its sole
enforcement was a prefix check (`first in ('SELECT','WITH')`), but PostgreSQL
allows data-modifying CTEs, so `WITH x AS (UPDATE ... RETURNING ...) SELECT * FROM
x` passed the guard and the UPDATE executed. Only the absence of a `commit()` in
`cmd_query` kept it from persisting — a future edit adding a commit would silently
turn it into an authenticated arbitrary-write hole (the CLI's `polaris_app` role
has full DML). The command now runs in a `set_session(readonly=True)` transaction,
so the engine rejects any write outright, regardless of commit behavior.

**Two uncaught-traceback paths.** `cmd_query` connected with a bare
`psycopg2.connect` outside any try block, so a connection failure dumped a full
traceback instead of the documented exit-2 error; it now mirrors the `connect()`
helper's clean message + exit 2. And `cmd_issue` parsed `--contexts` with
`[int(c) for c in ...]` before its try block, so a non-integer value raised an
uncaught `ValueError`; it now exits 1 with a usage message.

- `polaris_cli/polaris.py` — `query` runs read-only; `query`/`issue` connection
  and `--contexts` parsing fail cleanly.
- `polaris_cli/test_cli.py` — a writable CTE is rejected by the read-only
  transaction (and leaves no write); a non-integer `--contexts` exits 1 with no
  traceback.

## v9.74 — 2026-06-04 (the lockout message is no longer a username oracle)

`authenticate()` returned the generic "Invalid username or password." for an
unknown user, an inactive user, and a wrong password — but a distinct "Account is
temporarily locked. Try again later." for a known user whose `locked_until` was in
the future. Since an unknown user never enters the locked state (it returns before
any failure counter is touched), an attacker could enumerate usernames: send a few
wrong-password attempts to trip the lockout on a real account, and the distinct
"locked" string on the next attempt confirmed the account exists. `SECURITY.md`
affirmatively claims username enumeration is prevented, so this was an unmet
documented invariant.

Fix: verify the password *before* the lockout check, and reveal the lockout only
to a caller who supplied the correct password. A wrong-password attacker — whether
the account is unknown, wrong-password, or locked — now gets the identical generic
string, so the response no longer distinguishes a real account. A legitimate user
who types the right password still learns the account is temporarily locked. The
account stays locked either way (no login, no counter bump), and every known user
now runs one password hash, which also evens out the timing side channel.

- `polaris_web/security.py` — password verified before the lockout branch; locked
  response is generic unless the password is correct.
- `polaris_web/test_app.py` — `test_locked_account_is_not_an_enumeration_oracle`:
  the locked + wrong-password response equals the unknown-user response and never
  says "lock"; the correct-password caller still sees the lockout.

## v9.73 — 2026-06-04 (uc4 / uc10: validate under the lock, not before it)

Two validate-before-lock TOCTOU races from the concurrency review pass. Both
procedures took a lock for serialization but read the state they guard on
*before* the lock, so the guard ran against a stale snapshot.

**uc4_activate_reserve** validated the lost/reserve token statuses at the top,
then acquired its per-holder `Individual` lock and never re-read. Two concurrent
calls on the same tokens both passed the pre-lock check; the second then re-ran
`UPDATE ... LOST` (a no-op the state machine waves through on
`OLD.status = NEW.status`) and inserted a SECOND `RevocationList` row for the
already-revoked token (the table has no unique constraint on `token_id`). The
status reads now happen again UNDER the lock with the token rows `FOR UPDATE`, so
a stale second caller fails cleanly with "Token N is not ACTIVE" and publishes no
duplicate CRL row.

**uc10_revoke_attestation** checked "already revoked" before taking its
per-agency advisory lock — unlike `uc8_revoke_token`, which locks first. Two
concurrent revokes both passed the pre-lock guard and the second silently
overwrote the first's reason and timestamp. Reordered to lock first, then re-read
`revocation_date` under the lock (row `FOR UPDATE`) and reject the double-revoke.

- `polaris_sql/05_procedures.sql` — uc4 re-validates under the lock; uc10 is
  lock-first then guard.
- `polaris_web/test_app.py` —
  `test_uc4_concurrent_same_tokens_one_winner_no_duplicate_crl` races the actual
  procedure (the prior uc4 concurrency test raced raw UPDATEs) and asserts one
  winner, a clean loser, and exactly one CRL row.

## v9.72 — 2026-06-04 (WebAuthn second factor can actually complete)

The deeper review's WebAuthn pass found that the assertion (second-factor login)
ceremony could never complete for a real authenticator. Registration stores the
credential id as `_b64url_encode(raw)`, which keeps base64url padding, so the
stored primary key carries a trailing `=` for any credential whose byte length is
not a multiple of 3 — i.e. essentially every real authenticator (16/20/32/64/65
bytes). But at assertion the browser sends `PublicKeyCredential.id` / `rawId`
WITHOUT padding (the WebAuthn spec, and `webauthn-assert.js`, strip it), and
`fetch_credential` did an exact-equality lookup. The padded stored key never
matched the unpadded browser id, so the row was not found and the route returned
401 "invalid credential". Net effect: any admin who enrolled a credential became
permanently locked out, and a control meant to add a second factor became a hard
denial-of-service against the privileged role. No WebAuthn integration test
existed, so it shipped undetected.

Fix: a `_canonical_credential_id` helper round-trips any incoming id (padded or
unpadded) through the padding-tolerant decoder back to the stored padded form,
applied in `fetch_credential`, `update_credential_after_use`, and
`delete_credential`. No migration needed (no credential is seeded; new rows are
unchanged).

- `polaris_web/webauthn_auth.py` — `_canonical_credential_id`, applied to all
  three credential lookups.
- `polaris_web/test_app.py` — `WebAuthnCredentialLookupTests`: the helper maps
  both forms to the padded key, and a padded-store / unpadded-lookup round trip
  resolves (the exact-match path misses, proving the regression).

## v9.71 — 2026-06-04 (recovery ceremony: works for reserve-only holders, and three channels means three actors)

A deeper second review pass (procedure suite + compulsion-resistance dimensions)
found two HIGH issues in the UC-9 catastrophic-loss recovery ceremony.

**Recovery aborted for the exact holder it serves.** `uc9_complete_recovery`'s
APPROVED loop transitioned *every* non-terminal token to `LOST`, but the state
machine only permits `ACTIVE→LOST`; `RESERVE→LOST` is illegal and raised, aborting
the whole recovery. And `uc9_initiate_recovery` requires that no ACTIVE token
exist — so the realistic catastrophic-loss case is a holder whose only surviving
token is a RESERVE, which is exactly the case the blanket `→LOST` loop broke. (Same
class as the v9.64 uc4 bug: a procedure driving a transition the state machine
forbids.) The loop now transitions by source status: `ACTIVE→LOST`,
`RESERVE→REVOKED` (the only legal terminal edge from RESERVE, with the
velocity-bound opt-out uc4/uc8 use). A reserve-only holder now recovers cleanly.

**The "three independent channels" collapsed to one actor.** The ceremony's
anti-impersonation guarantee rests on three independent out-of-band channels:
biometric, sworn statement, and a witness co-signer. But nothing required
`witness_co_sign_user_id` to differ from the approver or the requester — so one
compromised admin could self-witness *and* self-approve, reducing the
"multiplicative cost" to a single actor. `uc8_revoke_token` already enforces
co-signer-must-differ on the revocation leg; recovery (the entry leg) omitted it.
Added the check in `uc9_complete_recovery` plus a `witness_differs_from_parties`
CHECK on `RecoveryRequest` (mirroring `approver_differs_from_requester`), and moved
the demo seed and test helpers to a distinct third actor (auditor) for the witness.

- `polaris_sql/05_procedures.sql` — uc9 loop transitions by status; witness
  separation-of-duties check.
- `polaris_sql/01_schema.sql` — `witness_differs_from_parties` CHECK.
- `polaris_sql/10_auth.sql` — demo recovery witness is now the auditor, distinct
  from the operator requester and the admin approver.
- `polaris_web/test_app.py` — reserve-only recovery succeeds; witness≠approver and
  witness≠requester both rejected. `CatastrophicLossRecoveryTests` is now 18 tests.

## v9.70 — 2026-06-04 (close the cross-site drive-by on the launcher control endpoints)

The last finding from the auth-security pass. `/api/quit` and `/api/heartbeat`
are unauthenticated launcher-control endpoints — no session, no CSRF token (the
launcher beacon is anonymous by design). `/api/quit` writes the file the desktop
launcher polls to tear the stack down. So any page the user merely visited could
`fetch('http://localhost:2222/api/quit', {method:'POST', mode:'no-cors'})` and
shut down their local instance (a cross-site drive-by; low impact for a
single-user dev tool, but a real gap).

Added `security.reject_cross_site`, applied to both endpoints. It rejects only
requests whose `Sec-Fetch-Site` header is `cross-site` (a header browsers set on
every request). Same-origin browser calls (`same-origin` — the heartbeat beacon
sends this) and header-less callers (the native launcher, curl, an operator) are
unaffected, so nothing breaks. `CrossSiteGuardTests` covers all four cases.

- `polaris_web/security.py` — `reject_cross_site` decorator.
- `polaris_web/app.py` — applied to `/api/quit` and `/api/heartbeat`.
- `polaris_web/test_app.py` — `CrossSiteGuardTests` (cross-site rejected;
  same-origin and header-absent allowed).

## v9.69 — 2026-06-04 (ZK verify route: local-clock epoch boundary, honest replay scope)

Completing the review by re-running the two dimensions that had hit a session
limit (crypto-soundness, app-disclosure). Both surfaced a real issue in the ZK
verify route.

**Epoch boundary used the wrong clock (R4).** `/api/zk/verify` rejected proofs
against expired epochs with `epoch['valid_until'] < datetime.utcnow()`, but
`TokenStateEpoch.valid_until` is a `TIMESTAMP`-without-zone stored as local wall
clock (app and DB are co-located), and every other Python boundary in `app.py`
compares against `datetime.now()` — the atlas code even carries a comment that
`utcnow()` is the wrong reference here. On any server not in UTC the epoch
boundary shifted by the server's offset: valid proofs rejected early, or expired
epochs accepted late. Fixed to `datetime.now()`, and added
`check_local_clock_convention` (app.py must not reference `utcnow`) so the
convention can't drift back. The check layer is now 21.

**The "replay resistance" claim was an overclaim.** `zk-snark.md` R2 was titled
"Replay resistance via nonce binding" and said "each verification request includes
a fresh nonce," and `lib.rs` claimed the binding "defeats within-epoch replay." But
the verifier reads the nonce from the same request that carries the proof and never
issues or consumes nonces, so the identical bundle resubmitted verifies again. The
binding prevents proof *substitution* (re-labelling a proof under a different
`(epoch, context, nonce)`), not bundle replay — which the project's own
`threat-model.md` T-T2 already lists as deferred. Corrected R2, the `lib.rs`
header, and `zk-soundness.md` to state exactly what the binding does, and added the
single-use nonce store to `ROADMAP.md` as the concrete hardening that would make
the claim hold in code.

- `polaris_web/app.py` — epoch-boundary check uses `datetime.now()`.
- `polaris_checks/checks.py` — `check_local_clock_convention` + detection test.
- `DEVNOTES/ships/zk-snark.md`, `polaris_zk/src/lib.rs`, `DEVNOTES/zk-soundness.md`
  — replay claim scoped to proof substitution; bundle replay noted as deferred.
- `ROADMAP.md` — ZK verify single-use nonce store added under Next ships.

## v9.68 — 2026-06-04 (consistency: a true table count, a version module that points only at live things)

The review's recent-regressions pass found two honesty gaps the earlier cleanups
left, both the kind a cold reader trips on.

- **`docs/ARCHITECTURE-OVERVIEW.md` said "27 tables"; the schema defines 26.**
  Every other doc that states a count says 26, and the SQL self-tests are built
  around 26. Fixed the doc, and added `check_table_count_matches_doc`: it counts
  `CREATE TABLE` in the schema and fails if the architecture doc states a
  different number, so this exact drift cannot recur. The check layer is now 20.
- **`polaris_web/__version__.py` still cited deleted things.** Its docstring named
  the deleted `meta/polaris-self-roadmap-2026-05-14.md` as a provenance pointer,
  the deleted `ai-status.sh`, a deleted `test_polaris_version_is_canonical`, and a
  bump procedure with steps (journal entry, meta + coherence run) for tooling that
  no longer exists. Rewrote the docstring to reference only what is live: the
  `polaris_checks` version/changelog checks and the `ai-done.sh` gate. The v9.63
  ship claimed "no source comment points at a deleted file"; this makes that true.
- Reworded two historical mentions (`scripts/ai-done.sh`,
  `polaris_web/test_check_constraints.py`) so they describe the removed checks
  without naming deleted scripts.

## v9.67 — 2026-06-04 (test rigor: fail-loud PQC and an externally-anchored second witness)

Two test-coverage gaps the review's test-rigor pass found, where a test could
pass while the thing it implies was broken.

**PQC fail-loud was untested.** `pqc_signing`'s load-bearing safety property —
with `POLARIS_USE_REAL_PQC=1` but liboqs missing, raise rather than silently
downgrade to the deterministic placeholder — had no direct test. Only the
flag-unset DB path was exercised (via `test_app`) and the static wiring grep
(`check_pqc_signing_wired`). A regression that let the flag-set-but-unavailable
branch fall through to the placeholder digest — a silent downgrade of an operator
who asked for real PQC — would have passed the whole suite. New
`polaris_web/test_pqc_signing.py` (9 cases, no DB, no liboqs needed): the
placeholder is exactly `sha3_256(token_value)` with the non-signature label, and
every entry point (`signature_bytes_for_token`, `sign`, `verify`) raises
`PQCUnavailableError` when the flag is set but liboqs is forced unavailable. Wired
into CI alongside `test_app`.

**The second witness's positive Merkle tests were self-referential.**
`test_witness2.py`'s membership/ACCEPT cases computed the committed root with the
same `root_from_path` they then checked against — `f(x) == f(x)`, true for any
deterministic implementation including a wrong one (wrong MDS, flipped index bits,
wrong padding). The only value anchor (`test_root_agreement_bit_identical`) is
gated behind the Rust binary, so when the differential is skipped the standalone
suite could not catch a wrong-but-deterministic Python witness. Added value-pinned
tests against roots produced by the **independent Rust witness** (captured
constants): `build_root` for a fixed multi-leaf and single-leaf set, and a
membership check whose committed root is the external anchor constant, not a
self-recompute. The Python witness's Merkle math is now anchored to external
ground truth even with no binary present.

- `polaris_web/test_pqc_signing.py` — new (9 tests).
- `polaris_zk/witness2/test_witness2.py` — 4 externally-anchored Merkle tests
  (13 total); the weak length-only single-leaf assertion now pins the value.
- `.github/workflows/ci.yml` — runs `test_pqc_signing` in the app-suite step.

## v9.66 — 2026-06-04 (harden the login redirect and the session cookie)

Two security findings from the review's auth-security pass.

**Open redirect (CWE-601).** All three post-login redirect sites (password
login, the WebAuthn partial-auth redirect, and the assertion completion)
validated the attacker-controlled `?next=` with `startswith('/') and not
startswith('//')`. That misses backslash variants like `/\evil.com`: browsers
normalize a backslash to a forward slash when parsing a URL or `Location`
header, so it becomes the protocol-relative `//evil.com`, but werkzeug emits the
backslash verbatim, so the guard passed it and the browser navigated off-site. A
victim who clicked `…/login?next=/\evil.com` and authenticated was redirected to
the attacker's domain.

The three sites now route `?next=` through one helper,
`security.is_safe_next_url`, which rejects backslashes, protocol-relative URLs,
anything `urlsplit()` reads as carrying a scheme or netloc, and embedded control
characters (CR/LF header-splitting). `NextUrlSafetyTests` (6 cases) pins the
attacks the old guard let through.

**Session cookie Secure flag (CWE-614).** `SESSION_COOKIE_SECURE` was set only
from `POLARIS_COOKIE_SECURE`, independent of `POLARIS_ENV=production`. An operator
who set production but forgot the cookie flag shipped `polaris_session` without
`Secure`, so a single downgraded request could leak the session over plaintext.
It is now forced on in production (`_PRODUCTION or …`), mirroring the secret-key
guard — production removes the foot-gun rather than trusting the operator.

- `polaris_web/security.py` — new `is_safe_next_url` helper.
- `polaris_web/app.py` — three redirect sites use it; `SESSION_COOKIE_SECURE`
  forced on under `_PRODUCTION`.
- `polaris_checks/checks.py` — `check_open_redirect_guard` (the naive `//`-only
  guard must not survive) and `check_cookie_secure_in_production`, with detection
  tests. The check layer is now 19 checks.

## v9.65 — 2026-06-04 (the demo ZK epoch verifies, and CI proves it)

The same review surfaced a second regression, this one hidden from CI. When the
ZK anonymity set grew from a 16-leaf demo to a full epoch (v9.60, `TREE_DEPTH`
4 to 14), `zk.py`, `merkle.py`, and `lib.rs` all moved to depth 14, but the
hardcoded demo epoch in `polaris_sql/10_auth.sql` was left at depth 4: a stale
Merkle root and three 4-sibling inclusion paths where depth 14 needs 14 siblings.
The demo ZK verification (`test_demo_epoch_root_verifies_via_python`) actually
failed at depth 14.

It stayed invisible because CI ran `test_app` *before* building the Rust ZK
binary, and the whole `ZKSnarkTests` class skips when the binary is absent. So the
masking hid not just this stale-data bug but every ZK proof round-trip test:
honest-prover acceptance, cross-epoch / cross-context / wrong-nonce rejection, and
the demo-epoch verification, 20 tests, none of them running in CI.

- `polaris_sql/10_auth.sql` — regenerated the demo epoch's root and the three
  per-leaf proof paths at depth 14 via the Rust witness (`zk.compute_epoch_leaves`).
  The leaf hashes are `derive_leaf_seed` (plain SHA3-256, depth-independent) and
  were already correct; only the root and the path lengths were stale.
- `.github/workflows/ci.yml` — set up Rust and build the ZK binary *before* the
  app suite, with `POLARIS_ZK_BINARY` in the job env so `zk._binary_path()` finds
  it. `ZKSnarkTests` now runs in CI instead of skipping. The reorder un-masks 20
  ZK tests; the demo-epoch verification is the standing guard against future depth
  or seed drift.

Verified: the full `test_app` suite is green with the binary present (all 20
`ZKSnarkTests` pass, demo epoch verifies), and the two-witness differential still
agrees at depth 14.

## v9.64 — 2026-06-04 (uc4 reserve activation works for every reason code)

A multi-agent review of the schema boundary found a HIGH-severity functional
regression in `uc4_activate_reserve`. The v8.15 belt-and-suspenders trigger
`enforce_revocation_velocity_bound` refuses any `UPDATE` that transitions an
`IdentityToken` into `REVOKED` unless the session GUC `polaris.revoke_check_done`
is set, so that the rate-limited `uc8_revoke_token` is the only entry point. But
`uc4_activate_reserve` also transitions the lost token to `REVOKED` whenever the
reason code is `COMPROMISED`, `SUPERSEDED`, or `ADMINISTRATIVE` (the terminal-status
`CASE` maps all three to `REVOKED`), and it never set the GUC. The trigger therefore
aborted the whole procedure with `Direct UPDATE to status=REVOKED is not allowed`,
so three of the five reason codes the UC-4 page offers were unusable. `LOST` and
`STOLEN` map to terminal status `LOST` and dodge the trigger, which is why nothing
caught it.

The fix: `uc4_activate_reserve` now sets `polaris.revoke_check_done` on its REVOKED
branch, opting the sanctioned 1-for-1 reserve swap out of the velocity bound exactly
the way `uc8_revoke_token` does. uc4 is inherently bounded (it consumes one
pre-provisioned reserve and produces one active token per call), so it is not a
mass-revocation vector and the anti-coercion property the bound protects is intact.

- `polaris_sql/05_procedures.sql` — guarded `set_config('polaris.revoke_check_done',
  '1', true)` on the REVOKED branch, before the lost-token `UPDATE`.
- `polaris_web/test_check_constraints.py` — new `TestUC4ReserveActivation` runs uc4
  end to end for all four reason codes and asserts the lost token reaches its correct
  terminal status. The three REVOKED-mapping cases fail against the unfixed schema
  (detection proven) and pass against the fix. Suite is 66 tests, all green.

## v9.63 — 2026-06-04 (reference-clean: no source comment points at a deleted file)

The de-larp and the cleanups deleted a lot, but ~30 source-code comments still cited
the deleted record by path: `sanctum/<date>.md` decision files, the `patterns/`
how-to playbook, `ai-where.sh`, and `test_structural_invariants.py`. Those are dead
references that a reviewer cloning the repo would find pointing at nothing.

Scrubbed them across 27 source files (Python, SQL, JS, HTML, shell):

- `sanctum/<date>-<name>.md` path citations in comments, docstrings, and the
  backup-manifest field became "a recorded decision" (the substance stays; the dead
  path is gone). These only ever appeared in comments and string literals, never in
  executable logic.
- The "Read before editing" / "canonical recipe" header blocks dropped their dead
  `patterns/*.md` and `ai-where.sh` lines, keeping the surviving doc pointers
  (`DEVNOTES/concurrency.md`, `docs/reference/SCALING.md`, `DEVNOTES/atlas-scaling.md`).
- The one `test_structural_invariants.py` reference (in a `test_check_constraints`
  docstring) was reworded to the surviving `pg_constraint` catalog check.

Verified after the scrub: the schema loads (78/78 SQL self-tests), the app imports
and `/dashboard` `/atlas` `/demo` render, `test_check_constraints` 62 OK,
`polaris_checks` 17 ok READY, `ai-link-check` resolves all 222 references. No logic
changed. The tree now references no deleted file anywhere, in docs or in source.

---

## v9.62 — 2026-06-04 (ROADMAP: a forward roadmap, not a ship archive)

`ROADMAP.md` had grown to 862 lines, but only the OPEN-NOW backlog and three gated
deferred items were forward-looking. The other ~770 lines were a shipped-items
archive (R7-* through R16-*, all ✅) that duplicates the CHANGELOG. A roadmap is
where the project is going, not a log of what shipped.

Cut it to ~75 lines: the flagged decision item, the next ships (PQC second witness,
the PQC-posture audit, the GitHub Actions deprecation), the production-scale deferred
items (multi-instance scaling, multi-region, distributed tracing, each gated), and
the explicitly out-of-scope items (OIDC, banking-on-Polaris, cross-platform
launchers). Shipped history stays in the CHANGELOG and the git log.

`ai-link-check` resolves all 222 references; `polaris_checks` 17 ok READY.

---

## v9.61 — 2026-06-04 (polaris_checks: complete the C1-C10 coverage)

The flat invariant layer directly checked C1, C3, C5, and C7; the other
constitutional constraints were enforced in the schema and app but not asserted by
the check layer. Added five checks, so 9 of the 10 constraints are now directly
machine-checked, each with tested detection correctness:

- **C2** — a CHECK constraint forbids `ZERO_KNOWLEDGE` verifications from carrying a
  `token_id`.
- **C4** — the failed-login counter increments atomically in a single UPDATE (no
  TOCTOU read-then-write).
- **C8** — the `/api/atlas/*` endpoints carry hard result-set caps.
- **C9** — concurrency hazards are tested with real threading (`ConcurrencyTests`).
- **C10** — the schema carries no monetary primitives (identity is not money).

C6 (server-side disclosure enforcement) stays covered behaviorally by the
redaction-property test, where it is meaningfully exercised rather than
string-matched.

`polaris_checks` is now 17 checks; each new check provably FAILs on a broken fixture
(`polaris_checks/test_checks.py`, now 13 detection tests). Verified: 17 ok / READY,
all detection tests pass.

---

## v9.60 — 2026-06-04 (ZK anonymity set: from a 16-leaf demo to a full epoch)

The zero-knowledge Merkle-inclusion circuit shipped at `TREE_DEPTH=4` (a 16-leaf
tree) while the schema caps an epoch at 10,000 leaves, so the proof's anonymity set
was at most 16 — far smaller than a real epoch. This raises the circuit to
`TREE_DEPTH=14` (16,384 leaves), which covers the 10,000-leaf cap, so the anonymity
set is now a full epoch.

Plonky2 is a transparent SNARK (FRI-based, no trusted setup), so the change is a
single constant in two files (`polaris_zk/src/lib.rs` and the Python second witness
`polaris_zk/witness2/merkle.py`) plus a recompile — no ceremony, no key
regeneration.

Verified at depth 14: the 7 Rust circuit tests pass, and the independent two-witness
differential (the Python re-checker vs the Rust prover) passes all 27 of its cases
bit-for-bit, including prove-verify roundtrips and tampered-root rejection. That
differential is exactly what would fail if the two implementations disagreed on the
new depth.

Docs updated: the ZK soundness ledger (`DEVNOTES/zk-soundness.md`) no longer lists
tree size as a demo-scale limitation (the not-audited and placeholder-PQC caveats
stand), the ship note, and the ROADMAP backlog item is closed.

---

## v9.59 — 2026-06-04 (professional cleanup: cut the agent-governance scaffolding)

Made the repository a clean, normal software project: removed the apparatus cruft,
fixed the broken tooling, pruned the dev-script sprawl, and cut the remaining
"how-an-AI-built-this" governance scaffolding that made it read as unusual rather
than professional. The thesis is untouched: C1-C10 and the anti-coercion Vocation,
the product, and the `polaris_checks` invariant layer.

**Removed:**

- Apparatus cruft left on disk: `polaris_swarm/` (the orphaned civitas JSON), plus
  `.DS_Store` and `.pytest_cache` (gitignored; were never tracked).
- 15 vestigial / methodology scripts (`scripts/` went 43 to 29): the session
  helpers (`ai-prime`, `ai-help`, `ai-recall`, `ai-snapshot`, `ai-cache-bust`,
  `ai-coverage`, `ai-where`, `ai-journal`), the agent-governance scripts
  (`ai-sanctum`, `ai-propose`, `ai-mission`, `ai-status`, `ai-test-counts`), and
  the `polaris-ai-done-hook` wrapper.
- The agent-governance meta docs: `meta/sanctum-protocol.md`,
  `meta/autonomy-architecture.md`, `meta/freeze-amendment-protocol.md`.

**Fixed:**

- `.pre-commit-config.yaml` was broken: it invoked three deleted scripts (`ai-meta`,
  `ai-coherence`, the structural-invariants suite) and a deleted doc. Rewritten to
  run `polaris_checks` + `ai-link-check` + the real hooks.
- `MISSION.md` (793 to 589 lines): cut the "agent contract" and "agent's
  relationship to this mission" methodology sections and the strategic-posture
  subsection. The constitution (C1-C10, the Vocation, the freeze line, the
  architectural soul, the done-lists) is unchanged.
- `CONTRIBUTING.md`: replaced the Sanctum / risk-class governance with a normal
  change-review process.
- De-methodologized the rest of the doc tree (`CLAUDE`, `SECURITY`, `README`,
  `ROADMAP`, and ~32 docs via two parallel cleanup passes): removed the dead
  Sanctum / risk-class references and the provenance citations to the deleted
  record.
- Corrected two now-false items in the live backlog (the full product suite is in
  CI as of v9.56; PQC issuance is wired as of v9.58).

Verified: `polaris_checks` 12 ok READY, `ai-link-check` resolves all 225
references, every script parses, the pre-commit config is valid YAML.

---

## v9.58 — 2026-06-04 (post-quantum signing wired into issuance)

Closes the one honesty gap the codebase itself flagged as "the most damning
critique" (`pqc_signing.py`'s own docstring): the headline post-quantum claim was,
at the data level, a hardcoded SQL string. The `uc1_issue_and_activate` procedure
wrote `TokenSignature.signature_bytes = 'UC1_ISSUE_PLACEHOLDER_<id>'`, and the
real-signing module was an unused island.

**The wiring.** The `uc1_issue` route now calls the new
`pqc_signing.signature_bytes_for_token(token_value)` and passes the result to the
procedure via a new trailing `p_signature_bytes BYTEA DEFAULT NULL` parameter. So
every token issued through the app gets its signature from the signing module:

- **Default (flag unset, including CI):** a deterministic SHA3-256 binding of the
  token value. Not a cryptographic signature (no private key), but a real binding
  produced by the signing module, single-sourced and reproducible, not a magic
  string.
- **`POLARIS_USE_REAL_PQC=1` + liboqs:** a real ML-DSA-65 (FIPS 204) signature.
- **Flag set but liboqs missing:** the route fails loud (`PQCUnavailableError`),
  never silently downgrading an operator who asked for real PQC.

**Backward-compatible.** The new parameter defaults to NULL, and the procedure
`COALESCE`s to the legacy placeholder string when no signature is supplied, so
every existing SQL caller and test is unchanged (the 12-argument call still works;
the function is dropped and recreated because adding a parameter changes its
signature).

**Guarded.** A new flat check, `polaris_checks.check_pqc_signing_wired`, asserts the
procedure accepts `p_signature_bytes` and the app routes issuance through
`signature_bytes_for_token`, with a detection test that FAILs if either regresses.
A DB-backed `test_app` test issues a token through the route and asserts the stored
`signature_bytes` equals `sha3_256(token_value)`, proving the path end to end.

Verified: schema loads (78/78 SQL self-tests), `test_check_constraints` 62 OK, the
issuance/signature suites green, `polaris_checks` 12 ok READY.

---

## v9.57 — 2026-06-04 (documentation prune: less is more)

The de-larp removed the apparatus *code*; this removes the documentation bloat it
left behind. The repository went from 216 markdown files (~66.7k lines) to 72
(~26k lines) by deleting what is no longer needed to understand, run, or extend
Polaris.

**Deleted (143 files):**

- The build-history audit-of-record: `sanctum/` (68 decision records), `journal/`
  (30 daily logs), and `archive/CHANGELOG-FULL.md` (the 18.8k-line full changelog).
  The complete history remains in the git log.
- The design-and-methodology record: `proposals/` (14 shipped-feature design docs)
  and `patterns/` (the 11-file how-to playbook).
- The apparatus-era meta snapshots: the three `polaris-self-roadmap-*` files,
  `cognitive-architecture-v2`/`v3`, `cold-read-walkthrough-v9.27`,
  `missions-considered`, `lineage`, `sanctum-index`, `arc-b-production`, the
  leftover `brain-map/`, and `cognitive-threat-review-due.txt`.
- `DEVNOTES/prior-art-analysis.md` + `DEVNOTES/plugin-policy.md`, `docs/BACKLOG.md`
  (ROADMAP covers it), `docs/story/STORY.md`, and the over-elaborate compliance/ops
  docs `docs/operator/{SOC2,PENTEST,DR-SINGLE-REGION}.md`.

**Kept:** the constitution (`MISSION.md`), `ROADMAP.md`, `CHANGELOG.md`, `CLAUDE.md`,
`CONTRIBUTING.md`, `SECURITY.md`; the `docs/reference` set, the operator runbooks,
the `DEVNOTES` engineering notes and ship records, the `meta/` constitution-support
docs (constraint-lattice, sanctum-protocol, autonomy-architecture, redaction-proof,
the TLA+ spec), `docs/story/PRINCIPLES.md`, and `docs/THESIS.md`.

**Re-linked:** every broken reference left by the prune was fixed across README,
MISSION, CLAUDE, ROADMAP, the CHANGELOG header, the landing page, and the surviving
`docs/`/`meta/`/`DEVNOTES` index and map files. The landing footer was repointed off
the deleted story doc and onto the real GitHub repo. `ai-link-check --ci` resolves
all 225 remaining references.

---

## v9.56 — 2026-06-03 (residual de-larp sweep + the full product suite goes green in CI)

Two things close here: the residual apparatus references left in the documentation
and dev scripts, and the CI regression that v9.55 introduced.

**Residual de-larp sweep.** v9.55 cut the apparatus code; this sweep cuts its
shadow in the docs and scripts. Deleted 15 more pure-apparatus files with no
surviving purpose: `meta/architect.md`, `meta/anti-architect.md`,
`meta/cognitive-loop.md`, `meta/watcher-predicates.md`,
`meta/foresight-predicate-audit.md`, `meta/swarm-mttr.json`,
`meta/swarm-scorecard.json`, `meta/sanctum-scorecard.json`,
`meta/structural-constants.json`, `meta/claude-90s.md`, `meta/swarm-map/`,
`meta/brain-map/`, plus `scripts/pre-commit-scope-check.sh` +
`meta/scope-rule-baseline.json` (rule-b referenced the deleted `polaris_swarm/`)
and `scripts/test_implants.sh` (smoke-tested the deleted scripts). De-larped the
surviving active-reference surface in place: the active `meta/` docs, the `ai-*`
and `polaris-*` dev/ops scripts, `ROADMAP.md`, and the `docs/` tree (the glossary,
operations runbook, architecture overview, system map, the story, the data model,
and the rest). The dated historical snapshots (the self-roadmaps,
`cognitive-architecture-v2/v3`, the cold-read walkthrough) and the development
record (`journal/`, `sanctum/`, `archive/`, prior `CHANGELOG` entries) are kept
as history.

**CI: the full product suite now runs green.** v9.55's rewritten `ci.yml` added an
"Application + CLI suites" step that ran `test_app` + `test_cli` for the first time
(v9.54's workflow never ran them), and they failed: `reload_sample_data()` shelled
out via `su - postgres -c`, which cannot authenticate against a service-container
Postgres. Fixed by reloading through the `POLARIS_DB_*` connection settings with
`psql` directly (works in CI, on macOS, and on Linux; `POLARIS_TEST_RELOAD_VIA=su`
still forces the legacy path). Added the missing "Apply migrations" CI step so
`webauthn_required_after` exists at test time. Then fixed the long-standing stale
tests the step surfaced: the dashboard / RBAC / substrate-UI tests that GET `/`
while logged in (where `home()` correctly 302-redirects authenticated users to
`/dashboard`), the health-check assertions that expected the old `db` /
`rate_limiter` keys instead of `database` / `redis`, the logout test that pulled
its CSRF token from a redirecting `/`, and the anchor-batch tests whose
`commitment_hash` test data did not satisfy the hex CHECK constraint. `test_app`
(329 tests) and `test_cli` (62 tests) now pass end to end.

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

