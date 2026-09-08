# Production-readiness review: a claim-and-proof season

**What this is.** Two external models (call them A and B) reviewed Polaris before
real deployment. A produced ~36 suggestions; B sharpened them and, correctly,
warned against treating all 36 as first-class work — that recreates the original
problem (internally sophisticated, externally unread). This document reconciles
both, credits what the tree already does, and commits a **short, sequenced
season** rather than a backlog of virtues. It is the design of record for
**P1.18**. It changes no code itself.

The governing point (from B): *manage eight, not thirty-six.* The goal of this
work is **less public machinery and more externally-checkable evidence.** Do not
make the cleanup more Polaris than Polaris — items about the constitution, the
ontology, and the ML subsystem can each grow into a second product about the
first. They must not.

Standing acceptance test, adopted verbatim as a ship gate: *does this make Polaris
more capable while keeping people no more legible, no more coercible, and the
authority itself more inspectable? If it cannot be made mechanically true, do not
ship it.* Keep it as one sentence; do not turn it into another constitution file.

## Already shipped (both reviewers lacked the context)

- **Two-witness issuance fails closed** (v9.264): `verify_both(require_witness=
  True)` + an up-front `second_witness_available()` guard. What is still missing
  is the explicit *availability clause* for the fast path (item 5 below).
- **Authenticity is read separately from authorization** (v9.264): the verify
  endpoint reads `status` from the primary (`query(primary=True)`,
  `status_source='primary'`). The split exists; the *stated contract* (item 4)
  does not yet.
- **Athena cannot become a population graph** (v9.266): five checks with
  detection tests forbid a person node/surrogate/edge, ZK-subject traversal, an
  independent authority store, and any non-descriptive table; read-only,
  non-sovereign. This is the "write the prohibition as a check now" that B asks
  for — done, and without a second product around it.
- **Prometheus boundary captured** (P6.9 brief): learn Polaris, never persons;
  advisory-only; candidate invariants. Locked as one page + the intent of a
  check, not an ML-ethics program.
- **Benchmark nouns already split three ways** (v9.257): enrollment vs event
  ingestion vs cryptographic verification. Extend the precision; do not restart.

## The season: eight items, in order (P1.18)

Cheapest-highest-integrity first, because claim honesty is free and compounding.
Freeze *product surface* after item 7 lands (a named milestone, not a mood);
keep fixing semantic checks during the freeze.

1. **Public claim pass.** Split the zero-knowledge claim into three precise
   nouns and **ban the umbrella phrase "zero-knowledge identity system" from the
   README title**: *unlinkable verification records* (a ZERO_KNOWLEDGE event
   carries no token_id — schema property, C2), *Merkle-membership proof* (the
   current Plonky2 SNARK), *selective disclosure / anonymous credentials* (NOT
   implemented). If a sentence needs all three, it is three sentences. Same class
   of fix for "certification" (rename P2.9 to a capacity model / scale exercise)
   and for benchmark nouns inheriting each other's numbers (no ~62k/s that is a
   one-core figure times eight). Label every claim measured / simulated /
   projected / aspirational. Cut the README to three core claims; demote
   mythology, freeze-line history, and "350M / national rollout" off the first
   screen; lead with the next externally-falsifiable milestone. Fix the nouns
   before adding features.
2. **Schema quarantine.** GenomicAnchor and QuantumObserverBinding are wired
   (anchoring.py + tests), so this is a real deprecation, not a delete: confirm
   no current guarantee needs them, migrate them out of the live schema into an
   explicitly experimental area, drop the DNA / "quantum observer" vocabulary,
   and add a check that they cannot return. Continues the v9.55 discipline.
3. **Guarantee split (two levels, then stop).** Rewrite C1-C10 once into
   **constitutional** (C1 audit/accountability, C2 anti-linkability, C3 identity
   uniqueness, C6 disclosure sovereignty, C10 identity != money) vs **engineering
   invariant** (C4 atomic counter, C5 CSP, C8 result caps, C9 concurrency
   methodology, production posture). Athena already models the rules as rows, so
   this is a `layer` attribute + the MISSION.md wording. Do **not** build a
   four-tier hierarchy with amendment rules yet — that is ceremony until there is
   a pilot and a second authority.
4. **Semantic checks + replica semantics.** This is the real engineering upgrade.
   Keep adding property checks with adversarial fixtures: a stored signature must
   *verify under its declared algorithm* (not merely exist), a stale ACTIVE must
   be rejected, mismatched algorithm ids caught, an absent second witness caught,
   the benchmark path proven correct. **The single most important backend change:
   split the verify API** into `signature_valid` (immutable, cacheable,
   replica-safe) and `currently_authoritative` (primary or a bounded-staleness
   contract with explicit `as_of` / `max_lag`). "Replica said ACTIVE" is not
   "revocation is fresh."
5. **Two-witness contract, with the availability clause.** Issuance fails closed
   (done). High-throughput verify-at-use may be single-witness **iff**: the fast
   path cannot change authorization state; continuous sampling replays a random
   percentage through the second implementation and is mandatory; a disagreement
   is a paging SEV, not a log line; and every "verified" response carries which
   witness set ran. Two witnesses that are optional are one witness with extra
   docs.
6. **One measured HA/verification report.** Take the ~7.8k/core single-witness
   figure to the actual topology (multiple gunicorn workers, replicas, load
   balancer, rolling deploy, induced primary failure, recovery, sustained
   traffic) and publish real p50/p95/p99, throughput, CPU, replica lag, failures,
   timeout rate, scaling efficiency. One honest report, not a national-looking
   observatory, and not a one-core number multiplied by eight. Use the synthetic
   nation as the harness (inject known faults, measure precision / recall /
   latency-to-detection), as a method, not a department.
7. **Proof-of-life artifacts.** A 15-minute scripted demo (issue -> real ML-DSA
   signature -> ZK verification -> DB row with no token_id -> illegal audit
   mutation rejected -> disable a guarantee, its invariant turns red -> failover,
   requests recover) and the **non-author operator session**: a clean machine,
   the public docs, someone who did not build it installs / operates / recovers /
   rotates / revokes / restores with no author help, and every failure is
   recorded. These leave "the author's mental model" behind as the compiler; put
   them above almost every P3 item.
8. **External-review packet.** A compact per-subsystem threat-model matrix for
   the subsystems that *exist* (Atlas, Athena, federation, relying-party API,
   revocation), a blunt known-limitations page (external validation incomplete,
   national scale extrapolated, ZK scope narrow, founder governance centralized,
   relying-party ecosystem not deployed), and guarantee-attack prompts against
   C1, C2, C10, Athena, and revocation freshness. Plus one interviewable
   walkthrough (threat -> SQL -> app -> invariant -> test -> limitation) and a
   short honest note on where human judgment lives and how agent disagreement is
   caught. One page each, not a workstream.

## Deferred to one-page principles (not this season)

- **Ecosystem anti-coercion** ("right to alternate path," non-exclusivity,
  revocation-not-cross-domain-exclusion). These are relying-party and legal-regime
  problems; PostgreSQL cannot enforce "a bank must accept a paper fallback."
  Write a short **ecosystem-posture note** and refuse APIs that make exclusivity
  easy (no "sole authenticator" flag, scoped revocation, no cross-context
  fan-out). Do **not** add C11-C18 until an institution is actually integrating.
- **Founder-governance amendment mechanism.** Matters before a pilot with real
  people; name it plainly as a known limitation now (item 8), design the
  overrule/amendment process before P5. No constitutional court this semester.
- **Full constitutional hierarchy, ML-ethics program, national observatory.**
  All are the "second product about the first" failure mode. Refused until the
  thing they govern actually exists at scale.

## The test of whether this worked

An outsider can answer these without the author talking: What does "ZK" mean here
exactly? What is measured vs projected? What can the database *not* be made to do?
Who can become recognizable in Atlas/Athena? What happens when a replica is stale?
What happens when one witness is wrong? Can someone other than the author bring it
up and revoke a token? If those are crisp, Polaris stops reading as a private
cosmology with excellent CI and starts reading as an ambitious system that knows
its own evidence class.
