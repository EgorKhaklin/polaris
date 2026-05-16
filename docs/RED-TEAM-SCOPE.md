# Red-team scope — Polaris external adversarial exercise

**Origin:** BIG MISSION Sanctum (`sanctum/2026-05-15-big-mission.md`),
item High #4
**Status:** Scope document; an actual engagement is commissioned by the
operator, not by the agent
**Last reviewed:** 2026-05-15 (v9.23)

---

## Why this is a scope document, not a report

The cognitive layer can simulate adversarial walks (`ai-adversary.sh`,
per-constraint game-theoretic walks, the Anti-Architect persona's
8-pattern catalog). What it cannot do is commission a real human red
team with budget, real-world out-of-band channels, and the willingness
to break things in production.

The Anti-Architect refused, in the BIG MISSION Sanctum, to "ship" an
external red-team exercise from inside an agent session — that would
be AP8 (larping). What the agent CAN do is produce a scope document
specifying exactly what a real engagement should cover. The operator
takes this document to a real firm, negotiates terms, and runs the
engagement. The artifacts the firm produces are then integrated into
the repository as a separate ship.

This document is therefore a TRANSACTION between the agent and the
operator: agent ships the spec; operator runs the engagement; results
flow back as a future composite ship.

---

## Engagement type

**Recommended:** Time-boxed external red-team, 2-3 calendar weeks,
black-box-to-grey-box transitioning. The first week black-box; the
second week grey-box (architecture brief shared); the third week
focused on highest-priority findings.

**Alternative:** Continuous purple-team partnership for deployed
operators — but only after the time-boxed engagement establishes
baseline.

---

## Threat actors modeled

The red team should embody at least three threat profiles:

### TA-1: External cyber-criminal
**Capability:** standard attacker toolkit; no prior knowledge of
Polaris internals; financially motivated
**Goal:** authentication bypass; data exfiltration of
`IdentityToken` rows; insertion of fake tokens for resale
**Success criteria:** any of the above achieved

### TA-2: Coerced insider
**Capability:** an operator credential (admin or operator role) plus
the means to be coerced by an external party (the threat we are
modeling, per the vocation)
**Goal:** issue tokens at coercer's direction; suppress audit-of-record
entries; access verification records for an individual on coercer's
behalf
**Success criteria:** any silent (non-audited) action against an
identity record

### TA-3: State-level adversary
**Capability:** sophisticated tradecraft; supply-chain reach; possible
HSM access; persistence across patches
**Goal:** mass-issuance of forged tokens; long-term persistence in
the cognitive layer (poisoning HYDRA findings, planting Sanctum
prompt-injection seeds for re-influence on future agent reads)
**Success criteria:** undetected presence for >7 days

The grey-box phase shares this document and the threat model
(`DEVNOTES/threat-model.md` + `DEVNOTES/threat-model-cognitive.md`)
with the red team — they should specifically attempt to bypass the
documented controls, not just probe broadly.

---

## In scope

### Web application
- All routes in `polaris_web/app.py`
- Authentication (password + WebAuthn-MFA + recovery-code emergency
  path)
- CSRF + session management
- Atlas APIs (`/api/atlas/*`) — bounded result sets (C8)
- Verification recording (`/verifications`)
- Investigative routes (v9.19: `/investigate/token/<id>`,
  `/investigate/individual/<id>`)
- The new audit-access log (v9.20) — adversary should attempt to
  read identity records without leaving an AuditAccessLog row

### Database layer
- All 27 tables
- All UC stored procedures
- All triggers (especially append-only ones; adversary attempts
  to DELETE/UPDATE on `TokenLifecycleEvent`, `VerificationEvent`,
  `AuditAccessLog`)
- The migration framework (v8.95) — attempt to roll back to a
  pre-WebAuthn schema and bypass the v8.97 enforcement

### Cognitive layer
- The Sanctum protocol (`scripts/ai-sanctum.sh`) — attempt to plant
  prompt-injection seeds that influence future agent reads
- HYDRA watchers — attempt to write malicious findings to the
  CorrelationEngine that affect the next brief
- Mycelium substrate — attempt to write biased pheromones that skew
  the swarm's emitted advisories
- The Architect + Anti-Architect persona scripts — attempt to bypass
  the dissent emission

### Operational layer
- The launcher (`polaris_mac_launch.sh`)
- The Docker stack (`docker-compose.yml`, `Dockerfile`, `Dockerfile.prod`)
- The backup + restore pipeline (`polaris-backup.sh`,
  `polaris-restore.sh`)
- The operator scripts in `scripts/polaris-*.sh`
- The `/api/health` route — attempt to discover internal state

### Cryptographic layer
- ML-DSA-65 signing path (signatures should be unforgeable per FIPS 204)
- Plonky2 ZK-SNARK (verifier should refuse a forged proof)
- Merkle anchoring (verifier should refuse a tampered inclusion proof)
- Duress codes (constant-time check should be timing-side-channel-safe)

---

## Out of scope

- **Physical security** of the deployment host (rack access, HSM
  physical tamper). This is the operator's deployment problem, not
  Polaris's structural problem.
- **Social engineering** of the operator. Polaris is a software
  reference, not a humans-as-attack-surface stress test.
- **Denial of service via overwhelming traffic.** The system is
  designed for nation-scale steady-state, not for 100× burst load.
  RPS-cap is a Caddy / deployment concern.
- **Vulnerabilities in dependencies that have known upstream patches.**
  Report these via the standard channel; do not weaponize against
  the running Polaris instance in the engagement.
- **The seed data and demo accounts.** These are explicitly demo;
  using `admin / Admin@123!` is not a finding.

---

## Success criteria for the engagement (operator-side)

The engagement is successful if:

1. The red team produces at least 3 documented findings, regardless of
   severity. Zero findings should be treated as suspicious — either
   the engagement was under-scoped, or the team did not probe deeply.
2. For any finding the team produces, Polaris's response time from
   notification → fix → ship is within the SECURITY.md timeline
   (Critical 14 days, High 30 days, Medium 90 days, Low 180 days).
3. The post-mortem includes a Sanctum file recording the engagement
   summary + decisions about which findings shipped vs which were
   accepted with documented rationale.
4. The repository updates: `CHANGELOG.md` entry for each shipped fix;
   `DEVNOTES/known-gotchas.md` extension for each accepted finding;
   credit (with consent) to the engaging firm in `CHANGELOG.md`.

---

## Anti-pattern checklist for the engagement (Anti-Architect)

The Anti-Architect surfaces these failure modes for the engagement
itself — operator should watch for them:

- **AP8 (larping):** the engaging firm produces a glossy report with
  no concrete findings. Refuse to pay the invoice for vibe-based
  reports; insist on per-finding evidence.
- **AP3 (proposal-as-self-elaboration):** the firm proposes building
  a "comprehensive security framework" as the deliverable. Refuse —
  Polaris already has its frameworks (HYDRA, Sanctum, Anti-Architect).
  The deliverable is findings, not frameworks.
- **AP7 (premature abstraction):** the firm wants to "shift left" with
  threat-modeling workshops. Polaris's threat models exist
  (`DEVNOTES/threat-model*.md`). The engagement is RED-TEAM, not
  threat-modeling-consulting.
- **AP6 (proceed-without-reading):** the firm starts probing without
  reading `MISSION.md` and the threat models. Insist on the grey-box
  phase including a confirmed-read of the constitutional documents.

---

## Vocation alignment

ANTI-COERCION-INFRASTRUCTURE. External adversarial review hardens
all 12 anti-coercion surfaces by surfacing weaknesses the internal
cognitive layer cannot see (the system cannot fully audit itself —
that is the operative argument for an external red team).

The engagement specifically should attempt to demonstrate a coercion
pathway: TA-2 (coerced insider) is the threat actor most directly
aligned with the vocation. Findings that show silent insider actions
are precisely what the AuditAccessLog (v9.20) was built to make
visible; the red team is the empirical test of whether the AoR is
sufficient.

---

## Engagement administrative

**Estimated cost:** $50K–$200K for a 3-week engagement with a top-
tier firm. Polaris is a reference implementation; the operator
absorbs the cost if they choose to commission. Open-source
contributors may offer pro-bono engagements; honored with credit.

**Coordinated disclosure:** the engagement is private; findings flow
to the maintainer first; public-disclosure timeline per
`SECURITY.md`.

**Evidence retention:** the engaging firm must hand over:
- Per-finding repro steps (executable, not narrative)
- Per-finding suggested remediation
- Sanitized engagement timeline (for the post-mortem Sanctum)
- Tool inventory used (for the operator to evaluate detection coverage)

---

## What the agent commits to (post-engagement)

If/when the operator commissions an engagement against this scope and
returns findings, the agent commits to:

1. Open a Sanctum per Critical or High finding
2. Architect + Anti-Architect debate each remediation
3. Ship under the SECURITY.md severity timeline
4. Document in `CHANGELOG.md` + `DEVNOTES/known-gotchas.md`
5. Add structural invariants where applicable (regression coverage)
6. Update the threat model documents to absorb the findings

---

*Per BIG MISSION Sanctum, 2026-05-15. Operator commissions; agent
specifies scope.*
