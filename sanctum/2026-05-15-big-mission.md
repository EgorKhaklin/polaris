# Sanctum — BIG MISSION (12-item Architect + Anti-Architect debate)

**Status:** DECIDED + SHIPPED 2026-05-15 — Position JOINT-MODIFIED (ship all 12 items with Architect + Anti-Architect debate-applied modifications). Authorized by VANTA in-chat 2026-05-15 ("Vanta Sanctum authorized"). Shipped as v9.23.

**Date opened:** 2026-05-15
**Date decided:** 2026-05-15
**Date shipped:** 2026-05-15 (v9.23)
**Lifecycle:** OPEN → DECIDING → DECIDED → SHIPPED
**Risk class:** HIGH (composite — touches Critical, High, Medium tiers across operator security, formal methods, infrastructure docs)
**Pattern #20 Constitutional Discipline:** 18th instance
**Authorization:** "Vanta Sanctum authorized" — VANTA, in-chat 2026-05-15

---

## §I. The Request (verbatim, abridged)

> BIG MISSION. (Architect + Antiarchitect Agents discusses each one, improve
> them / add on to them, maybe do more things, maybe dont do some. If you
> find anything, you can also add to the mission list, and remove from the
> mission list if you dont think its the right fit. You can use the HYdra
> and the swarm, and everything in polaris, Vanta Sanctum authorized
>
> **CRITICAL:**
> 1. Operator WebAuthn + Hardware Token for admin/operator (Arc B Phase 2)
> 2. Dedicated cognitive-layer threat model
> 3. polaris-restore.sh validation with cryptographic checks
>
> **HIGH:**
> 1. Formal verification (TLA+/Lean) for C1, C2, C3 invariants
> 2. Multi-region deployment + DR runbook with RPO/RTO targets
> 3. RASP capabilities + anomaly detection
> 4. External adversarial red-team exercise
>
> **MEDIUM:**
> 1. QuantumObserverBinding functional impl OR clear deferral doc
> 2. 10M+ active tokens load testing
> 3. External onboarding guides (Getting Started + architecture overview)
> 4. Audit log archival to cold storage with retention rules
> 5. CONTRIBUTING.md + security vulnerability disclosure policy

---

## §II. Debate (Architect ↔ Anti-Architect on each item)

### CRITICAL #1 — Operator WebAuthn + Hardware Token

**Architect:** This is Arc B Phase 2 from the production roadmap. The
substrate already exists: `webauthn_auth.py` at 459 lines (v8.97 ship,
Position B of an earlier Sanctum) implements registration, assertion,
the four-state status machine (`not_required` / `grace_period` /
`mfa_required` / `mfa_overdue`), and the `_hardware_only()` policy hook
that rejects software authenticators when set. The `OperatorWebauthnCredential`
table is migrated, the `AppUser.webauthn_required_after` column is migrated
(v8.97 migration), and the login flow already enforces all four states.

**Anti-Architect:** Then what is this BIG MISSION item asking us to BUILD?
The infrastructure is already done. Re-implementing what exists would be
AP3 (proposal-as-self-elaboration) and AP7 (premature abstraction). The
HONEST gap is operator-policy: `webauthn_required_after` defaults to NULL,
which means no enforcement deadline. The operator must set the column for
enforcement to fire. There is no helper script. There is no runbook entry.
That is the gap — not the cryptography.

**Joint resolution:** Audit confirms 100% of infrastructure is in place.
Ship: `scripts/polaris-set-webauthn-deadline.sh` (operator helper that sets
the deadline for an admin/operator account, with confirmation prompt and
audit-trail). Ship: `docs/operator/WEBAUTHN-ROLLOUT.md` (runbook for
phased rollout: enroll → grace-period → enforce). Do NOT rebuild what
exists. Do NOT add hardware-only-by-default — that is policy and should
remain operator-configurable via the existing `_hardware_only()` env var.

### CRITICAL #2 — Cognitive-layer threat model

**Architect:** `DEVNOTES/threat-model.md` exists (487 lines, STRIDE-categorized)
but predates HYDRA + Mycelium + Sanctum. Threats specific to the cognitive
substrate are not modeled: pheromone poisoning (adversary writes biased
findings into the Mycelium substrate to skew HYDRA's CorrelationEngine
output), watcher compromise (adversary modifies a HYDRA watcher to suppress
findings before they reach the brief), Sanctum prompt injection (adversary
plants instructions in a Sanctum file that re-influence agent behavior on
next read), Architect/Anti-Architect persona spoofing, Foresight surface
weaponization (FS-XXXXXXXX promotion of off-mission categories). Ship:
`DEVNOTES/threat-model-cognitive.md`.

**Anti-Architect:** Concur. But contest two scope creeps. (a) Do NOT propose
new infrastructure to mitigate every threat — that is AP3. Threats below the
mitigation-cost threshold should be ACCEPTED-DOCUMENTED with rationale,
mirroring v8.20 audit-of-record discipline. (b) Do NOT include speculative
threats with no concrete attack path ("AI alignment" type framing) — that is
AP4 (pattern-projection) and AP8 (larping). Threats must be concrete and
testable.

**Joint resolution:** `DEVNOTES/threat-model-cognitive.md` covering 5
threat classes (pheromone poisoning, watcher compromise, Sanctum injection,
Foresight weaponization, Architect/Anti-Architect spoofing). Each threat
gets affected component + control(s) + ACCEPTED vs MITIGATED status. NO
new infrastructure proposed in this ship — the document NAMES the threats;
mitigations stay in the proposal queue for separate evaluation.

### CRITICAL #3 — polaris-restore.sh validation

**Architect:** `polaris-restore.sh` exists (348 lines, v8.81). Need to audit
what cryptographic-integrity checks it does. Backup files should be hashed
(SHA-256) at backup time; restore should verify hash before applying. Schema
version after restore should match the recorded schema_version. Restore
should be a no-op if the target DB is non-empty (refuse to overwrite).

**Anti-Architect:** Read it before proposing changes. AP6 (proceed-without-
reading) is the most common Architect failure mode.

**Joint resolution:** Audit current state of polaris-restore.sh + polaris-backup.sh.
Add SHA-256 manifest written at backup time + verified at restore time.
Add schema_version sanity check after restore. Add refuse-if-non-empty
default guarded by `--force` flag. Do NOT add online verification (that's
the Audit table's job; restore is offline).

### HIGH #1 — Formal verification (TLA+/Lean) for C1, C2, C3

**Architect:** TLA+ models give machine-checked proofs that a state-machine
specification refuses to violate a named invariant. C1 (audit-of-record),
C2 (zero-knowledge), C3 (one-identity-per-person) are good candidates — all
three already have Hypothesis property tests and structural invariants.
A TLA+ spec would be the third layer: schema-level CHECK constraints +
property tests + formal model.

**Anti-Architect (strong refusal):** AP7 (premature abstraction) and AP1
(self-observation without ground-touch) hit hard here. We already have
Hypothesis property tests (test_invariants_property.py runs 19 property
tests across C1/C2/C3). We already have schema-level CHECK constraints.
We already have structural invariants. Adding TLA+ adds a maintenance
burden no one in this org is qualified to maintain. The TLA+ model would
drift from the actual code on the first schema change. The cost is high;
the marginal value is low. **REFUSE the broad scope.** If anything,
ship ONE spec for ONE constraint as a demonstrator — not as ongoing
verification infrastructure. C3 is the most subtle invariant (the
partial unique index on ACTIVE tokens; the concurrent-write race);
that's the one worth modeling.

**Joint resolution:** ONE TLA+ spec for C3 at `meta/tla/c3-one-active-token.tla`,
shipped as a *demonstrator artifact*. README explicitly states this is NOT
ongoing verification infrastructure — it is a one-time formal model
illustrating that C3 holds under concurrent writes. The model is NOT
required to stay in sync with future schema changes. If a future Sanctum
decides formal verification should become a maintained surface, that's a
separate ship. This ship documents the technique, not the commitment.

### HIGH #2 — Multi-region + DR with RPO/RTO

**Architect:** Multi-region deployment closes a real availability gap.
RPO < 1 hour, RTO < 4 hours are reasonable targets for a national identity
system reference implementation.

**Anti-Architect (strong refusal):** v9.16 EXPLICITLY closed multi-region
as RESERVED-NOT-PLANNED. The Sanctum on open-arcs (2026-05-15) resolved
that Arc G is held in reserve until external triggers (≥10× verification
volume / partner deployment / federation requirement). Proposing multi-region
NOW would VIOLATE the v9.16 resolution. AP7 (premature abstraction): we
don't have ONE production deployment yet; building for multi-region without
even one region is pure speculation. **REFUSE multi-region.** What can ship
honestly is a single-region DR runbook: documented RPO/RTO targets for the
*current* single-region deployment, the backup/restore procedure (existing
scripts), the recovery-code procedure (existing), and the time-to-recovery
budget. That is the v9.16-compliant deliverable.

**Joint resolution:** Ship `docs/operator/DR-SINGLE-REGION.md` covering:
RPO target = 24 hours (daily backup cadence), RTO target = 1 hour
(documented restore procedure), backup verification cadence, recovery-code
distribution policy. EXPLICITLY scoped to single-region; explicitly defers
multi-region to v9.16's RESERVED-NOT-PLANNED clause.

### HIGH #3 — RASP + anomaly detection

**Architect:** Runtime Application Self-Protection: rules that detect anomalous
behavior at runtime and respond. Rate-limits per (agency, individual) pair;
WAF rules at Caddy; anomalous verification-rate alerting.

**Anti-Architect:** "RASP" is a vendor marketing term. What is being asked
is concretely: rate-limit per principal, anomaly-detection on verification
rates, and a WAF in front. We already have a rate-limiter (R8-2). We already
have anomaly detection in HYDRA's adversary_watcher. The honest gap is:
(a) the rate-limiter is per-IP not per-(agency,individual); (b) Caddy serves
TLS but doesn't have a security-rule layer above the app; (c) no per-route
anomaly thresholds documented. Do NOT ship a "RASP framework" — that would
be AP3 + AP7. Ship the specific gaps as a documented rule-set.

**Joint resolution:** Ship `DEVNOTES/rasp-rules.md` documenting concrete
runtime-protection rules: rate-limit thresholds, Caddy security headers
(many already in place from v9.13), per-route anomaly thresholds that
the adversary_watcher should flag, and the *gap list* of rules NOT yet
implemented. Operator can prioritize which to wire next. No new framework.

### HIGH #4 — External red-team exercise

**Architect:** A red-team exercise stress-tests assumptions in ways
internal review cannot. Should commission one.

**Anti-Architect:** The AGENT cannot commission a red-team. The agent can
SIMULATE adversarial walks (`ai-adversary.sh` already does this per
constraint), but a real red-team requires real humans with budget. AP8
(larping) if we "ship" an external red-team exercise from inside this
session. What the agent CAN ship is a SCOPE DOCUMENT — what an external
red-team would test, what's in scope vs out of scope, what evidence the
operator should retain. The operator then commissions an actual firm.

**Joint resolution:** Ship `docs/RED-TEAM-SCOPE.md` defining what a real
external red-team engagement against Polaris should cover (scope, threat
actors, success criteria, evidence retention). Agent does NOT claim to
run the engagement. Operator commissions a real firm against this document.

### MEDIUM #1 — QuantumObserverBinding (functional OR deferred)

**Architect:** The table is SCAFFOLD-only since v8.11. Either build the
quantum-observer-binding logic or document why we're not.

**Anti-Architect:** Strongly favor the deferral document. AP7: we have no
deployed quantum threat to defend against. AP8: "quantum observer" is a
naming flourish; the underlying concept is a future migration substrate
for post-quantum algorithm rotation. Mirror v9.16 Position C′ pattern:
RESERVED-NOT-PLANNED with manifestation triggers documented.

**Joint resolution:** Ship `DEVNOTES/quantum-observer-deferred.md` (mirrors
v9.16 RESERVED-NOT-PLANNED framing). Triggers documented for when this
becomes worth building. Schema scaffold remains in place — the SCAFFOLD
status of the table IS the constitutional record that this is unfinished.

### MEDIUM #2 — 10M+ active tokens load testing

**Architect:** `scripts/polaris-load-test.sh` exists (v8.80) for HTTP-RPS
load. Doesn't simulate token-volume scaling. Ship a complementary script
that bulk-inserts and verifies at scale.

**Anti-Architect:** Don't replace the existing script. Don't claim 10M+
without running it. Ship the script, document the volume tested, name
the volume NOT tested. Anything else is AP8.

**Joint resolution:** Ship `scripts/polaris-loadtest-tokens.sh` — token-
volume simulator that bulk-inserts N tokens (parameterized; default 100K,
flag for 10M+) and times atlas + verification queries against the resulting
DB. Documents what was actually verified locally vs claimed for production.

### MEDIUM #3 — External onboarding guides

**Architect:** First-time-reader onboarding is real-world weak. We need a
fast-path for an operator who has never seen Polaris, and an architecture
brief for someone evaluating it.

**Anti-Architect:** Concur. These are documentation gaps, not architectural
holes. Two documents. Keep them under 5000 words each.

**Joint resolution:** Ship `docs/QUICKSTART.md` (operator onboarding — clone
to running stack in 90 seconds) and `docs/ARCHITECTURE-OVERVIEW.md`
(architecture brief — what Polaris is, what the layers are, how to navigate
the codebase, what's deferred). Both linked from README.md.

### MEDIUM #4 — Audit log archival to cold storage

**Architect:** Audit logs grow unboundedly. Cold storage with retention
policy is needed.

**Anti-Architect:** We already have archival surfaces: v8.84 (archive
script), v8.87 (purge script), v9.07 (Pheromone rotation with audit-of-
record). What's missing is the cron-install glue. Ship that, not new
archival.

**Joint resolution:** Ship `scripts/polaris-cron-install.sh` — installs
crontab entries wiring the existing archive+purge+rotation scripts at
documented cadences. Idempotent. Documented retention policy.

### MEDIUM #5 — CONTRIBUTING.md + SECURITY.md

**Architect:** Top-level GitHub convention. Both missing.

**Anti-Architect:** Concur, but they should be honest. CONTRIBUTING.md
should set the Sanctum protocol expectation. SECURITY.md should set
the disclosure process. Both should be terse.

**Joint resolution:** Ship top-level `CONTRIBUTING.md` (development
expectations, Sanctum protocol pointer, test discipline) and `SECURITY.md`
(vulnerability disclosure policy, contact, scope, response timeline).

---

## §III. Position selected — JOINT MODIFIED (ship all 12 with debate-applied modifications)

**Items shipped as-requested:** 3 (Critical #2, Medium #3, Medium #5)
**Items shipped scoped-down per Anti-Architect:** 6 (Critical #1, Critical #3,
High #1, High #3, High #4, Medium #4)
**Items shipped refused-as-stated-shipped-as-corrected:** 2 (High #2 →
single-region DR; Medium #1 → deferred doc)
**Items shipped extended:** 1 (Medium #2 — script + honest accounting)

**Items added by agent (per VANTA's "you can also add to the mission list"):** 0
The 12 items as scoped by the joint resolution already cover the major
v9.23 gaps. No items removed.

---

## §IV. Anti-Architect anti-pattern hits surfaced in this debate

- AP1 (self-observation without ground-touch) — caught on TLA+ broad scope
- AP3 (proposal-as-self-elaboration) — caught on WebAuthn rebuild attempt
- AP4 (pattern-projection) — caught on speculative cognitive threats
- AP6 (proceed-without-reading) — caught on polaris-restore.sh proposed changes
- AP7 (premature abstraction) — caught on TLA+, multi-region, RASP, Quantum
- AP8 (larping) — caught on red-team simulation, 10M+ unverified claim

Six of eight catalogued anti-patterns surfaced. Pattern #20 17th instance
(v9.20) saw 4 anti-patterns; v9.12 saw 6. This composite hits 6. The
constitutional discipline is working as designed.

---

## §V. Vocation alignment (per v9.11)

Anti-coercion vocation alignment per item:
- C1 WebAuthn: hardware-token requirement raises coercion cost (must steal
  the physical key, not just the password) → ANTI-COERCION-DIRECT
- C2 Cognitive threat model: prevents the cognitive substrate from becoming
  a coercion vector (a compromised watcher could selectively hide findings
  about coerced operators) → ANTI-COERCION-INDIRECT-STRUCTURAL
- C3 Restore validation: ensures backup integrity, preventing tampered-
  backup-restore as a coercion path → ANTI-COERCION-INDIRECT
- H1 TLA+: formal proof of C3 hardens the one-identity-per-person guarantee
  that is the structural prerequisite for anti-coercion → ANTI-COERCION-INDIRECT
- H2 DR runbook: availability under attack is itself anti-coercion
  (coerced operators cannot be told "the system is down, do it manually")
  → ANTI-COERCION-INDIRECT
- H3 RASP: rate-limits prevent coercer-driven bulk operations → ANTI-COERCION-INDIRECT
- H4 Red-team scope: external adversarial review hardens all of the above
  → ANTI-COERCION-INFRASTRUCTURE
- M1 Quantum deferred: explicit non-commitment is anti-larping → ANTI-COERCION-NEUTRAL
- M2 Load test: ANTI-COERCION-NEUTRAL (performance)
- M3 Onboarding: lower barrier to inspection is anti-coercion (more eyes
  on the system make hidden coercion harder) → ANTI-COERCION-INDIRECT
- M4 Cron install: archived audit logs preserve coercion-evidence beyond
  online retention → ANTI-COERCION-INDIRECT
- M5 CONTRIBUTING+SECURITY: published disclosure policy is anti-coercion-
  by-disclosure (coercion is harder when researchers have a documented
  path to surface evidence) → ANTI-COERCION-INDIRECT

11 of 12 items have positive anti-coercion alignment; 1 is neutral. ZERO
items are anti-coercion-negative. The mission as a whole is vocation-aligned.

---

## §VI. Outcome

Ship as v9.23. Composite. 12 items. Debate documented above is the
constitutional record. Pattern #20 18th instance.

Authorization: VANTA, in-chat 2026-05-15: "Vanta Sanctum authorized".

**SHIPPED 2026-05-15 as v9.23.** 13 new artifacts + TestWave23V923
invariants + state-map + CHANGELOG + journal + sanctum-index.
