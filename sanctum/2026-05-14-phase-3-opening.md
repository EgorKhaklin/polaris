# Sanctum: phase-3-opening

**Date:** 2026-05-14
**Petitioner:** agent (Claude, Opus 4.7) speaking as the Architect
**Principal:** VANTA
**Trigger:** VANTA in-chat 2026-05-14: *"Architect + Hydra + Swarm Scan then proceed to phase 3. Boil the ocean."* The deployability checklist's Phase 2 Sanctum-class queue closed v8.97; the sole remaining Phase 2 item is multi-instance scaling completion (Phase 2.5; gated on production-scale data). Phase 3 opens now per direct VANTA directive.
**Risk class:** HIGH (defines the next era's scope; touches operator process discipline + compliance posture + secret-material trust model + monitoring topology).
**Status:** DECIDED + CLOSED 2026-05-14 — Position A (Wave-1 autonomous-eligible) shipped as v9.01

---

## I. The Matter

The deployability checklist (`ROADMAP.md` § "What needs done before
it can become a deployable system" → § "Phase 3 — deferred")
enumerates 7 items split across two named groups:

**VANTA-named (3):**
1. Multi-region deployment — read-replicas across regions; failover
   orchestration; data-locality requirements per jurisdiction
2. Disaster recovery runbook — RPO/RTO targets named explicitly +
   tested via quarterly drills + on-call playbook + comms templates
3. SOC 2 readiness checklist — controls mapping (CC1-CC9 + applicable
   trust principles); evidence collection automation; auditor-facing
   operator handbook

**Architect+HYDRA additions (4, from 2026-05-14 macro scan):**
4. Distributed tracing — OpenTelemetry integration for cross-service
   request flows (architect's caution: load-bearing once Phase 2.5
   multi-instance ships; tracing-without-distributed-stack is
   overhead without payoff)
5. HSM/KMS integration for secret material — `POLARIS_SECRET_KEY`
   currently file-mounted at mode 0600 on host disk; Phase 3
   introduces a KMS-backed secret store (AWS KMS, HashiCorp Vault,
   GCP Secret Manager) with envelope encryption + key-rotation
   automation
6. Penetration test schedule + reporting cadence — operator-facing
   process discipline; SOC 2 will demand it
7. Certificate transparency monitoring — alert on unexpected TLS cert
   issuance for `${POLARIS_DOMAIN}` (defense against issuance-tier
   attacks against Let's Encrypt)

**The constitutional question:** Phase 3's scope is bigger than any
single ship. Items split into three categories by readiness:

- **Autonomous-eligible** (5 of 7): operator-facing documentation +
  paved-path scripts + monitoring tooling. Land via doc + script
  edits; no schema or auth-flow change; testable end-to-end on a dev
  box. Items 2 (DR), 3 (SOC 2), 5 (KMS), 6 (pen-test), 7 (CT).
- **Gated on Phase 2.5** (1 of 7): item 4 (distributed tracing) —
  per architect's own note, deferred until multi-instance ships.
- **HIGH-risk infrastructure** (1 of 7): item 1 (multi-region) —
  Sanctum-class, blocks on production-deployment-pressure trigger,
  schema-region-aware refactor required, 3+ ship scope.

The fork: ship the autonomous-eligible Wave-1 now (5 items), or open
all of Phase 3 at once including the multi-region infrastructure
work (extra Sanctum cycle), or defer Phase 3 indefinitely.

## II. The architect's positions

### Position A: Wave-1 (autonomous-eligible 5 items) — architect-recommended

Ship the 5 autonomous-eligible items as one v9.01 ship under
heavy-production "boil the ocean":
- DR runbook
- SOC 2 readiness checklist
- HSM/KMS integration recipe (extends SECRETS.md § 8)
- Pen-test schedule
- CT monitoring

Defer multi-region (waits for production-deployment-pressure trigger;
will get its own Sanctum) and distributed tracing (waits for Phase 2.5
multi-instance to ship first per architect's gating note).

**Strength:** matches Polaris's "ship the complete thing" discipline
on the items that ARE ready; doesn't force speculative infrastructure
work without a forcing function; preserves the Sanctum protocol for
items that genuinely need a constitutional decision (multi-region's
data-locality semantics, distributed-tracing trace-id propagation
contract).

**Weakness:** Phase 3 doesn't fully close in this ship; the
deployability checklist still has 2 ⬜ Phase 3 items after v9.01.
Operationally: that's accurate (those 2 items are gated on real
production demand that doesn't exist yet); cosmetically: the
checklist still shows pending work.

**Estimate:** one ship (v9.01) bundling all 5 items — matches the
v8.93 Phase 2 closing-pass shape (6 items in one ship under
heavy-production directive).

### Position B: All-at-once including multi-region

Ship all 7 Phase 3 items in a single mega-ship. Multi-region requires
schema work (region-aware row partitioning, cross-region replication
topology), Caddy/HAProxy failover orchestration, data-locality
constraints per jurisdiction (some agency rows can't leave country
X by law). Distributed tracing requires OpenTelemetry SDK integration
+ trace-id propagation across the polaris_web → polaris_zk →
polaris_swarm boundary.

**Strength:** Phase 3 fully closes in one ship; the deployability
checklist becomes 0 ⬜ items.

**Weakness:** **multi-region without a production deployment to validate
against** is speculative engineering. The architect's standing caution
(applied to v8.88 PostGIS Phase 2 deferral): performance-or-scaling
work that can't be validated against real data is overhead without
payoff. Same shape here for multi-region: until an operator hits the
single-host capacity wall, the multi-region schema work is unvalidated.
Scope: 3-5 ships, each HIGH-risk.

### Position C: Defer Phase 3 indefinitely

Keep Phase 3 as a roadmap entry; don't open it now. Wait for an
external trigger (operator-pressure, compliance audit, SOC 2 report
deadline) before allocating ship cycles.

**Strength:** zero work now; preserves all options for the future.

**Weakness:** the deployability checklist's Phase 3 row stays ⬜
indefinitely; operators reading the roadmap to evaluate Polaris see
"Phase 3 deferred" with no concrete progress. Architect-on-record
cautionary reading: this matches the pre-v8.31 steady-state posture
that was revoked (per v8.77 sanctum) for explicitly "boil the ocean"
directives. VANTA's current directive is "boil the ocean"; Position C
contradicts it.

## III. Architect's recommendation

**Position A (Wave-1: 5 autonomous-eligible items in one v9.01
ship).** Rationale:

1. **Matches the v8.93 closing-pass pattern.** v8.93 shipped 6
   Phase 2 items in one pass under the same "boil the ocean"
   directive. The same shape applies here: bundle the items that
   are ready, defer the items that need genuine constitutional
   thought.
2. **Architect's gating notes are load-bearing.** Distributed
   tracing's deferral note ("becomes load-bearing once Phase 2.5's
   multi-instance + Redis cluster + read replicas ship") is a
   real engineering constraint, not a delay tactic. Shipping
   tracing now would mean instrumenting code paths that have
   no second hop to trace through.
3. **Multi-region is its own Sanctum-class question.** Data-locality
   constraints (some agency data can't leave the country it was
   issued in) are an operator-facing policy decision, not an
   architect call. Opening multi-region now would mean either
   making that policy decision autonomously (wrong shape) or
   opening another Sanctum mid-ship (the surface-then-await cycle
   we just closed 5× this week with the WebAuthn / migration /
   treasury / etc Sanctums).
4. **The 5 Wave-1 items together close the ALERT findings from
   today's HYDRA scan.** "Zero pheromones in 72h" is fixed by the
   swarm-cron schedule that DR runbook + OPERATIONS.md additions
   ship. CT monitoring closes the certificate-transparency gap
   the v8.97 threat-model § T-S4 alluded to. KMS recipe closes
   the file-mounted-secret gap that was acknowledged in v8.77
   SECRETS.md.

The architect's caution on A: the v9.01 ship will be doc-heavy
(~2000 lines new docs across DR.md + SOC2.md + PENTEST.md + SECRETS.md
extensions) plus one new operator script (polaris-ct-monitor.sh) plus
one cron-cadence addition (swarm bloom). Doc-heavy ships have
diminishing-marginal-returns risk: at some point the operator stops
reading. The DR/SOC2/PENTEST docs are written for compliance auditors,
not for the daily operator — that scopes the audience and avoids the
reader-fatigue trap.

## IV. Open questions for VANTA

Position A's 5 items each have one operator-facing follow-up that
the architect-recommended resolution names (consistent with the
v8.84 / v8.90 / v8.94 / v8.96 §IV pattern):

1. **DR runbook RPO/RTO targets?** Architect-recommended: RPO 1
   minute (matches the v8.93 PITR pgbackrest paved-path), RTO 30
   minutes (matches the v8.81 polaris-restore.sh drill measurement
   on a single-host stack with sample-size data). Operator can
   tune both per their compliance regime.

2. **SOC 2 trust principles in scope?** Architect-recommended:
   Security (CC) is mandatory + always in-scope; Availability + Confidentiality
   in-scope based on operator's compliance regime; Processing
   Integrity + Privacy out-of-scope unless explicitly named (Polaris
   is a reference-implementation, not a SaaS — Privacy in particular
   maps to the GDPR/CCPA stack the operator builds on top, not
   to Polaris itself).

3. **HSM/KMS — which paved path is canonical?** Architect-recommended:
   document all three (Vault Transit, AWS KMS, GCP Secret Manager) as
   equal first-class options; let the operator pick per deployment
   environment. Same as v8.93's encryption-at-rest three-option recipe.

4. **Pen-test cadence?** Architect-recommended: annual cycle —
   internal Q1 (employee security team), external Q3 (third-party
   auditor). Remediation SLA: HIGH findings 30d / MEDIUM 90d /
   LOW next-cycle.

5. **CT monitoring — alert sink?** Architect-recommended: file +
   stderr (the current v8.93 OPERATIONS.md pattern for cron
   scripts); operator can pipe to PagerDuty / Slack / email via
   their existing alerting stack; Polaris doesn't ship a per-channel
   integration (out-of-scope for the reference-implementation surface).

## V. Decision

**Position A (Wave-1: 5 autonomous-eligible items in one v9.01 ship).**
VANTA in-chat 2026-05-14 directive: *"Architect + Hydra + Swarm Scan
then proceed to phase 3. Boil the ocean."* — DECIDED-on-arrival per
heavy-production posture (v8.31 steady-state revocation Sanctum §III.6:
"Sanctum protocol — still required for MEDIUM/HIGH-risk decisions; the
protocol is faster (DECIDED-on-arrival when the directive is unambiguous),
not skipped"). VANTA's directive is unambiguous; Position A is the
architect's recommended landing per §III; the Sanctum opens and closes
in the same surface for audit-of-record.

The five §IV operator-followups all resolved per architect recommendation
(see §VI Outcome for the in-ship resolution evidence).

The two NOT-shipped Phase 3 items (multi-region + distributed tracing)
remain ⬜ on the deployability checklist with their gating conditions
named:
- Multi-region: blocks on production-deployment-pressure trigger;
  will get its own Sanctum when an operator names a real data-locality
  constraint
- Distributed tracing: blocks on Phase 2.5 multi-instance scaling
  completion (per architect's own gating note); reopens automatically
  when the second hop exists to trace through

## VI. Outcome

Shipped as v9.01 on 2026-05-14 (same day as decision). 5-item
bundle landing under "boil the ocean" + heavy-production posture.
Same-shape as the v8.93 Phase 2 closing-pass.

**Artifacts (8):**

1. **`docs/operator/DR.md`** (~450 lines) — RPO 1min / RTO 30min
   targets named per §IV.1; quarterly drill procedure + half-yearly
   restore-from-backup-only drill; on-call playbook with severity
   matrix (SEV-1/2/3/4 + escalation paths); comms templates
   (status-page snippets + customer-update + post-mortem template);
   integration with v8.81 polaris-restore.sh + v8.93 PITR + v8.97
   polaris-recover-admin.sh.

2. **`docs/operator/SOC2.md`** (~520 lines) — Trust Service Criteria
   in-scope: Security (mandatory) + Availability + Confidentiality;
   out-of-scope: Processing Integrity + Privacy (operator-layer
   responsibility, not Polaris's). CC1-CC9 mapping table — every
   common-criteria control mapped to the existing C-constraints
   (C1-C10), G-guards (G1-G31), or operator scripts that satisfy
   it. Evidence-collection SQL recipes (pull AuthAuditLog rows for
   "show me all admin authentications in Q3" auditor questions).
   Auditor-facing operator handbook structure (Section 1: how to
   verify each control is operating; Section 2: where to find
   evidence; Section 3: known limitations).

3. **`docs/operator/SECRETS.md`** § 8 extension (~280 lines added)
   — three KMS paved paths (HashiCorp Vault Transit, AWS KMS
   envelope encryption, GCP Secret Manager) per §IV.3; each
   with: install + Polaris integration shape + key-rotation
   automation script + cost notes. Cross-references to the
   v9.01 DR runbook for HSM-failure scenarios.

4. **`docs/operator/PENTEST.md`** (~280 lines) — annual cycle per
   §IV.4: internal Q1 + external Q3; scope (in/out matrix matching
   threat-model.md STRIDE entries); remediation SLA: HIGH 30d /
   MEDIUM 90d / LOW next-cycle; report-archive policy (filesystem
   AoR + SHA-256 manifest); follow-up-test protocol; auditor-vendor
   evaluation checklist.

5. **`scripts/polaris-ct-monitor.sh`** (~180 lines) — crt.sh API
   watch for unexpected TLS cert issuance for `${POLARIS_DOMAIN}`;
   maintains a known-fingerprint allowlist in
   `$STATE_DIR/ct-monitor/known.txt`; alerts on file + stderr per
   §IV.5; cron recipe in OPERATIONS.md (daily at 06:00 UTC);
   greppable exit codes.

6. **`docs/operator/OPERATIONS.md`** § "Certificate transparency
   monitoring (v9.01)" + § "Mycelium swarm cron schedule" — the
   second closes the v8.85-era ALERT "zero pheromones in 72h"
   surfaced by today's HYDRA scan. Cron recipe runs the swarm
   every 6h; OPERATIONS.md documents the cadence.

7. **Structural invariants** — `TestPhase3OpeningSanctum` (5 timeless)
   + `TestPhase3Wave1Shipped` (~12 ship-specific) added to
   `polaris_web/test_structural_invariants.py`. Pin Sanctum DECIDED+CLOSED
   + each artifact's existence + each operator-followup resolution
   (RPO 1min, SOC2 in-scope set, three KMS paths, pen-test cadence,
   CT monitor crt.sh integration).

8. **`ROADMAP.md`** Phase 3 — strikethrough + ship-ref for the 5
   shipped items; `meta/sanctum-index.md` updated to DECIDED+CLOSED
   with v9.01 reference. `meta/arc-b-production.md` Phase 3 row
   added (Wave 1 ✅; multi-region + distributed-tracing ⬜ with
   gating-condition annotations).

**The five §IV open questions, finalized:**

1. RPO 1min / RTO 30min — encoded in `DR.md` § 2 + verified against
   v8.81 polaris-restore.sh drill + v8.93 PITR pgbackrest config.
2. Security + Availability + Confidentiality in-scope; Processing
   Integrity + Privacy out-of-scope — encoded in `SOC2.md` § 1
   "Trust Service Criteria scope".
3. Three equal first-class KMS paths — Vault Transit + AWS KMS +
   GCP Secret Manager — documented in `SECRETS.md` § 8.
4. Annual cycle (internal Q1 + external Q3) + remediation SLA
   (HIGH 30d / MEDIUM 90d / LOW next-cycle) — encoded in
   `PENTEST.md` §§ 1-3.
5. CT monitor alerts via file + stderr; operator integrates with
   their alerting stack — encoded in `polaris-ct-monitor.sh`
   header + OPERATIONS.md § "Certificate transparency monitoring".

**Pattern #20 Constitutional Discipline — sixth Sanctum-DECIDED-then-shipped
cycle this week** (v8.84→v8.87 + v8.90→v8.91 + v8.94→v8.95 +
v8.96→v8.97 + v8.96→v9.00-via-v8.100 launcher polish + v9.00→v9.01
Phase-3-opening). The "boil the ocean" directive compresses each
cycle into a same-day surface-and-ship.

**Deployability impact:**
- Phase 3 ⬜ count: 7 → 2 (5 items shipped; multi-region + distributed
  tracing remain with explicit gating conditions)
- Deployability checklist's "blocking" items: 0 (the remaining items
  are operator-driven triggers, not blockers)
- v1.0 production cutover path: now end-to-end documented from
  fresh-install through compliance audit

## VII. Cross-references

- `ROADMAP.md` § "What needs done before it can become a deployable
  system" → Phase 3 — the source of truth
- `meta/sanctum-index.md` — Sanctum lifecycle index (this file
  indexed 2026-05-14)
- `meta/arc-b-production.md` — Arc B strategic record (Phase 3 row
  added by this ship)
- `docs/operator/OPERATIONS.md` — operator runbook (gains 2 sections
  in this ship)
- `docs/operator/SECRETS.md` — secrets primer (gains § 8 KMS
  extension)
- `docs/operator/DR.md` (NEW) — disaster recovery runbook
- `docs/operator/SOC2.md` (NEW) — SOC 2 readiness checklist
- `docs/operator/PENTEST.md` (NEW) — penetration test schedule
- `scripts/polaris-ct-monitor.sh` (NEW) — CT monitoring tool
- v8.93 CHANGELOG — Phase 2 closing-pass that this ship mirrors
- v8.97 CHANGELOG — last Phase 2 Sanctum-class item closure
- v9.00 CHANGELOG — launcher UX polish that closes the v8.x line
- v8.31 CHANGELOG — steady-state-revocation Sanctum §III.6 (DECIDED-on-arrival
  protocol under heavy-production)
