# Security Policy

Polaris is a national identity token system reference implementation. The
substrate is intentionally hardened: every constraint is enforced at the
database level rather than at the policy layer, and the cognitive layer
monitors itself via HYDRA + the Sanctum protocol.

This document covers vulnerability disclosure: how to report a finding,
what's in scope, and what response timeline to expect.

The threat model itself lives in `DEVNOTES/threat-model.md` (STRIDE
categorization) and `DEVNOTES/threat-model-cognitive.md` (cognitive-
substrate threats). The reference operator runbook for incident
response is `docs/operator/OPERATIONS.md`.

---

## Reporting a vulnerability

**Do not** file a public GitHub issue for security vulnerabilities.

**Email:** PolarisID@protonmail.com 

**Include in the report:**

- Affected component (web app / SQL schema / migration / cognitive layer
  script / launcher / Docker image / dependency)
- Affected version (`/api/health` returns the running version; the
  canonical version is in `polaris_web/__version__.py`)
- Reproduction steps
- Impact assessment (which of C1–C10 is at risk, if any; which vocation
  surface is affected)
- Suggested remediation (optional)
- Whether you've published anywhere (we strongly prefer pre-disclosure
  coordination)

**Acknowledge timeline:** initial response within 5 business days.

**Triage timeline:** severity assessment within 10 business days.

**Fix timeline:** depends on severity:

- **Critical** (breaks C1–C10 in a deployable configuration): patch
  within 14 days, coordinated disclosure
- **High** (auth bypass, data exposure not covered by C2, denial of
  service against the live stack): patch within 30 days
- **Medium** (information leak that does not violate C2; misconfiguration
  default; weakened-but-not-broken cryptography): patch within 90 days
- **Low** (defense-in-depth gap; documentation error that could lead to
  insecure deployment): patch within 180 days

**Coordinated disclosure:** we'll work with you on a disclosure date
that allows operators time to patch. Default: 90 days from initial
report, extended for Critical findings as the patch warrants.

---

## Scope

### In scope

- The Flask application (`polaris_web/`)
- The SQL schema, procedures, triggers, indexes (`polaris_sql/`)
- The Rust ZK prover/verifier (`polaris_zk/`)
- The HYDRA + Mycelium cognitive layer (`polaris_hydra/`, `polaris_swarm/`)
- The foresight surface (`polaris_foresight/`)
- The Sanctum protocol implementation (`scripts/ai-sanctum.sh`,
  `meta/sanctum-protocol.md`)
- The operator scripts in `scripts/polaris-*.sh`
- The Dockerfiles and `docker-compose*.yml`
- The launcher (`polaris_mac_launch.sh`, `Polaris.command`)
- Reference documentation in `docs/`
- The migration framework (v8.95+)

### Out of scope

- **Demo data and seed accounts.** The `admin / Admin@123!` default
  account is for demonstration only; it is not a vulnerability.
- **Self-DoS via misconfiguration.** Setting `POLARIS_STATE_DIR` to a
  full disk and complaining the launcher fails is not a vulnerability.
- **Banking / payments / merchant codes.** These are excluded by C10.
  A finding that "Polaris doesn't have feature X" where X is a
  transaction-handling primitive is by design.
- **External hosted infrastructure** unless you control the deployment.
  Reports against `polaris.example.com` (a hypothetical example domain)
  are out of scope; reports against a self-hosted deployment you control
  are in scope.
- **Third-party dependencies' upstream vulnerabilities** that have not
  yet been pinned in `polaris_web/requirements.txt`. File those upstream
  first; we'll pick them up at the next dependency-rotation pass.
- **Issues with the cognitive layer's recommendations.** The Architect
  + Anti-Architect protocol is explicitly designed to surface contested
  positions; "Architect said X and Anti-Architect said Y" is the protocol
  working as designed, not a vulnerability. A genuine cognitive-layer
  vulnerability is one that allows an attacker to manipulate the
  Sanctum / HYDRA / Mycelium state without authorization — see
  `DEVNOTES/threat-model-cognitive.md`.

---

## Vocation alignment

Vulnerability disclosure is itself anti-coercion-aligned. A coerced
operator cannot use a defended security disclosure channel to surface
evidence. A coerced engineer cannot publish a finding without retaliation.
This policy commits to:

- Coordinated disclosure (no retaliation against good-faith researchers)
- A documented response timeline (not "we'll get to it")
- Pre-disclosure embargo coordination (not "we'll publish first")

If you are reporting under duress, indicate this in the initial message.
We will treat the report as a duress-channel event (mirrors C2 / C9
reasoning) and respond accordingly. **There is no "duress code" for
this channel** — the cryptographic duress-codes mechanism is for
end-users authenticating into Polaris, not for security researchers
reporting vulnerabilities — but the operator commits to the same
spirit: a coerced report should not entail retaliation against the
researcher.

---

## Hall of fame

Researchers who report Critical or High vulnerabilities and coordinate
disclosure will be credited (with consent) in `CHANGELOG.md` at the
patch ship. If you prefer to remain anonymous, that is honored.

---

## Bug-bounty program

There is no formal bug-bounty payout. Polaris is a reference
implementation, not a deployed service. Operators of deployed Polaris
instances may run their own bounty programs against their deployments,
referencing this policy.

---

*Maintainer: VANTA / Egor Khaklin*
*Last updated: 2026-05-15 (v9.23)*
*Per RFC 9116 / live `/security.txt` route shipped v9.13*
