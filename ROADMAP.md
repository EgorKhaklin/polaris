# ROADMAP.md - from reference implementation to national deployment

This is the build plan. It is written to be executed: an agent (or a human) in a
fresh session reads [CLAUDE.md](CLAUDE.md), then this file, picks the first
unblocked item in the active phase, and ships it under the standing ship
discipline. Shipped history lives in [CHANGELOG.md](CHANGELOG.md), not here.

**Decision record.** MISSION.md's v9.32 freeze line limited work to hardening,
measurement, and thesis evidence, and required a named operator trigger to open
a new arc. That trigger occurred: on 2026-08-31 the project owner (VANTA)
directed a complete plan to real national deployment. This roadmap is that
recorded decision. The constitution (C1-C10 and the vocation) is not softened
by it; every phase below carries the constitution as a hard gate, and several
previously retired scope decisions are explicitly reopened here with reasons,
rather than silently.

**Status marks:** `[ ]` pending · `[>]` in progress · `[x]` done ·
`[EXT]` blocked on an external actor (funding, law, vendor, institution).
Update marks in place as part of each ship; never delete rows.

**Sizing:** S (under one session) · M (1-3 sessions) · L (an arc, 3-10) ·
XL (multi-arc). Risk is delivery risk, not security risk.

---

## Where we are (honest inventory, v9.157)

**Have, working, CI-proven:** a 28-table constraint-enforced schema with
append-only audit; 72-route application with WebAuthn operator MFA and the
Atlas; operator CLI; Plonky2 ZK Merkle-inclusion with an independent Python
second witness; real ML-DSA-65 signing two-witnessed (liboqs + OpenSSL);
five-service hardened production stack behind a post-quantum TLS edge
(X25519MLKEM768, proven in CI); pgBackRest backup/restore and streaming
replication, both CI-round-tripped; 77 invariant checks each with a detection
test; CVE gates on dependencies and images; operator tooling for backup,
restore, archive, purge (archive-bound), migrate, account recovery; twelve
operator runbooks; an honest gap ledger in
[docs/PRODUCTION-READINESS.md](docs/PRODUCTION-READINESS.md).

**Do not have:** hardware tokens (the physical artifact is modeled, not built);
holder-facing surfaces (everything today is operator-facing); identity-proofing
evidence flows mapped to NIST 800-63; scale beyond a single node (no
partitioning, no HA automation, no multi-region); a relying-party ecosystem
(no stable public API contract, no SDKs, no conformance suite); offline
verification; status/revocation distribution at scale; inter-authority
federation as deployed topology (the schema supports it; no protocol spec or
second instance exists); key custody beyond files (no HSM/KMS); certified
cryptography (liboqs is not FIPS-validated); artifact signing, SBOM, or build
provenance; accessibility conformance; any external audit, pen test, or pilot;
and every institutional prerequisite of a national system (statute, funding,
enrollment workforce, manufacturing, authorization to operate).

**Carrying debts (known, dated):** the Rust toolchain floats on an undated
nightly; `test_e2e_atlas.py` runs in no CI job; roughly twenty Dependabot PRs
sit unmerged; `polaris-rotate-secret.sh`, `polaris-chaos-test.sh`,
`polaris-load-test.sh`, and `polaris-ct-monitor.sh` have never been exercised
(the ops-sweep lesson: exercise them, do not read them); the ZK tree depth is
demo-scale by default ([DEVNOTES/zk-soundness.md](DEVNOTES/zk-soundness.md));
the internal TLS hops are classical pending OpenSSL 3.5 in those images.

---

## Phase map

| Phase | Objective | Scale target | Exit gate |
|---|---|---|---|
| P0 | Foundation closure | n/a | Every claim reproducible by command; supply chain signed; zero known debts |
| P1 | Single-authority production | 10k-100k persons, one org | A non-author operator runs it from docs alone; pen test closed; SLOs met |
| P2 | Scale architecture | 1-10M persons (state) | 10M load profile green on HA topology through a rolling deploy and a failover |
| P3 | Federation and relying parties | Many authorities, third-party verifiers | Two instances interoperate in CI; an external team integrates docs-only |
| P4 | Hardware token and enrollment | Field-ready issuance kit | Enroll, personalize, verify online+offline, revoke, recover: end to end on AoR |
| P5 | Pilots | Real, consenting users | Two completed pilots with public reports, zero constitutional violations |
| P6 | Certification and assurance | Authorization-ready | Validated crypto option, 800-63 mapping, audit and red team published |
| P7 | National rollout | 350M persons | First state live; a national program office assumes ownership |

P4 runs in parallel from P1 onward. P5-P7 are gated on external actors; the
buildable machinery for each is listed so no external gate is ever waiting on
us.

---

## P0 - Foundation closure

Objective: a stranger can clone the repo, verify every stated claim with a
command, and reproduce every artifact. Nothing on the known-debt list survives.

| ID | Item | Size | Risk | Blocked by | Definition of done |
|---|---|---|---|---|---|
| [x] P0.1 | Pin the Rust toolchain to a dated nightly (v9.160) | S | low | - | `rust-toolchain.toml` pins nightly-2026-05-10 (build + tests proven on it); CI derives the toolchain from the file; `check_rust_toolchain_pinned` enforces the dated form |
| [x] P0.2 | Wire `test_e2e_atlas.py` into CI (v9.160) | S | low | - | The suite was modernized first (it had rotted against the v9.146 MapLibre surface), proven to fail on a sabotaged page and pass on a healthy one, then wired into the docker-image job under POLARIS_E2E_REQUIRE=1 so skips cannot read as green; `check_ci_runs_atlas_e2e` pins the wiring |
| [x] P0.3 | Clear the Dependabot backlog and set policy (v9.161) | M | low | - | 15 safe bumps batch-applied and verified (cargo build+test, CLI suite, pip-audit clean, both images rebuilt); 4 foundation majors declined with recorded reasons and `ignore` rules (postgres 18, python 3.14, plonky2/plonky2_field 1.x); the merge policy is documented in dependabot.yml |
| [x] P0.4 | Exercise the un-swept operator tools: rotate-secret, chaos-test, load-test, ct-monitor (v9.166) | L | med | - | All four exercised end to end; four real defects found and fixed, each pinned: load-gen double-counted failures + exited green on 100% 5xx; the chaos zk_binary_absent scenario was VACUOUS (ran bare python3, mistook the import failure for a verifier refusal, missed a planted fail-open binary); ct-monitor was untestable offline + would parse a crt.sh error page as certs; rotate-secret regressed 0644 container-readable secrets to 0600 (the v9.140 crash-loop). Four detection-tested checks added |
| [x] P0.5 | SBOM per release (pip + all four images) (v9.167) | M | low | - | `.github/workflows/sbom.yml` fires on published release, generates SPDX-2.3 SBOMs for the Python surface + all four self-built images (via the same Trivy the CVE scanner pins), and attaches them; both surfaces exercised locally (20 + 60 packages); `check_sbom_workflow` and `check_sbom_trivy_matches_scan` pin the job and the version match |
| [x] P0.6 | Signed artifacts and provenance (v9.168) | M | med | P0.5 | Release SBOMs carry a keyless SLSA build-provenance attestation (Sigstore/Fulcio/Rekor via GitHub OIDC, `actions/attest-build-provenance@v4`); `gh attestation verify` documented in SECURITY.md. DoD amended: image signing at a registry digest is DEFERRED to P1.5 because the four images are not published to any registry, so there is no ref to sign today; `check_release_provenance` pins the attestation + permissions + verify doc |
| [x] P0.7 | ZK production profile + plonky2 major (v9.169 + v9.170) | M | med | - | Tree depth parameterized (v9.169): runtime `POLARIS_ZK_TREE_DEPTH`, default 14, prover + Python witness both read it (parity 31/31); prove/verify/size benchmarked across depths 10-24, zk-soundness ledger updated with measured numbers (verify + size constant, prove superlinear via full-tree reconstruction, sibling-path witness named as the next optimization). Plonky2 0.2->1.x taken (v9.170): roots bit-identical across the major, two-witness 31/31 + Rust 8/8 re-passing, seven new must-use-Result warnings handled with `?` (not silenced), Poseidon constants proven still-valid. `check_zk_tree_depth_synced` pins prover/witness depth agreement. A national-scale (depth 24+) anonymity set is verify/size-viable but gated on the sibling-path witness optimization, now a named follow-up |
| [ ] P0.8 | Coverage measured and gated | M | low | - | Python and Rust coverage published per release; a floor gate fails CI on regression |
| [ ] P0.9 | Offsite backup, one command | M | low | - | pgBackRest S3-compatible offsite repo configured by env alone; a restore-from-offsite drill scripted and CI-exercised |
| [ ] P0.10 | Pager integration for alerts | S | low | - | An Alertmanager webhook receiver template plus runbook; the duress>0 page path tested end to end |
| [ ] P0.11 | Internal-hop hybrid PQ KEX | M | ext | OpenSSL 3.5 in the pgbouncer/postgres images | Both internal hops negotiate hybrid KEX; the CI handshake proof extends to them; PQC-POSTURE updated |

Exit gate: every P0 row `[x]` (P0.11 may remain `[EXT]` if still
vendor-blocked); the known-debt paragraph above is rewritten empty.

---

## P1 - Single-authority production

Objective: one real issuing authority (a university, a county office) could run
Polaris for its population, on Linux, around the clock, without the author.

| ID | Item | Size | Risk | Blocked by | Definition of done |
|---|---|---|---|---|---|
| [ ] P1.1 | First-class Linux server deployment | L | med | P0 | systemd units, an install script, a hardening guide; a fresh Debian or RHEL box reaches a healthy prod stack from the docs alone. Deliberately reopens the retired "Linux launcher" scope: that retirement was about desktop demo launchers, and a server deployment is a deployment necessity |
| [ ] P1.2 | Key custody abstraction (HSM/KMS) | L | high | - | Signing and epoch keys behind a custody interface: PKCS#11 and cloud-KMS drivers, a file driver for dev; a key ceremony and rotation runbook; two-witness verification unchanged |
| [ ] P1.3 | Secrets lifecycle to KMS | M | med | P1.2 | Production secrets sourced from KMS or age, not files in a directory; rotation drills automated and CI-exercised |
| [ ] P1.4 | Zero-downtime deploys | L | med | - | An expand-contract migration policy, documented and checked; a blue-green profile; a CI job proves a rolling deploy under traffic with zero dropped requests |
| [ ] P1.5 | Kubernetes/Helm reference profile | L | med | P1.4 | A Helm chart with network policies and pod security that boots to healthy on a stock cluster; compose remains the single-node path |
| [ ] P1.6 | Distributed tracing and dashboards-as-code | M | low | - | OTel traces across app and DB; Grafana dashboards committed; the correlation id joins logs to traces |
| [ ] P1.7 | Session and origin hardening pass | M | low | - | WebAuthn attestation policy options, per-role network policy hooks, admin session limits; each new control pinned by a check. Amended at v9.163: also take the webauthn 2.x to 3.x library major here with its own test pass, declined as a blind merge in P0.3 |
| [ ] P1.8 | Abuse controls | M | med | - | Per-agency quotas and velocity anomaly alerts on issuance, revocation, and verification; exercised with the load generator. Amended at v9.163: also take the redis-py major (rate-limiter backend) here, declined as a blind merge in P0.3 |
| [ ] P1.9 | Performance baseline v1, published | M | low | P0.4 | Reference-hardware numbers for issuance/s, verification/s, and atlas p95, committed as a doc CI can re-run |
| [ ] P1.10 | DR to targets, on a schedule | M | low | P0.9 | RTO <= 4h and RPO <= 5min proven by an automated monthly drill with committed results |
| [ ] P1.11 | Retention and lifecycle engine | M | med | - | Per-table-class retention configuration with jurisdiction templates; the archive/purge chain drives it; the C1 carve-out rules unchanged |
| [ ] P1.12 | External penetration test | M | ext | P1.1-P1.8 | [EXT: funding, firm] The readiness pack is ours to build; findings triaged, fixed, and pinned; a summary published |

Exit gate: a non-author operator performs a witnessed clean install and a
simulated month of operations (issuance, revocation, recovery, backup, restore,
failover, rotation) using only the docs, and the
[SLOs](docs/operator/SLOS.md) hold on reference hardware.

---

## P2 - Scale architecture

Objective: a state-scale deployment (1-10M persons) with high availability,
horizontal read scaling, and operational headroom, proven by load.

Planning targets (to be validated by P2.9, not asserted): 10M persons;
sustained 1,000 verifications/s with 10x peak headroom; 50 issuances/s
sustained during enrollment surge; p95 online verification under 150ms
server-side; 99.95% availability.

| ID | Item | Size | Risk | Blocked by | Definition of done |
|---|---|---|---|---|---|
| [ ] P2.1 | Event-table partitioning | L | high | P1.4 | Time-range partitions on the event tables with lifecycle tooling; C1 append-only semantics preserved across attach and detach; the migration executes zero-downtime |
| [ ] P2.2 | Read-replica routing | M | med | P2.1 | Read-only surfaces (atlas, reports, exports) route to replicas under an explicit staleness contract; failback tested |
| [ ] P2.3 | Atlas v2 on PostGIS | L | med | P2.1 | Server-side clustering at scale replaces the bespoke binning; 10M-event map interaction inside p95 targets; the C8 caps retained |
| [ ] P2.4 | Bulk enrollment pipeline | L | med | P2.1 | COPY-based batch issuance for authority migrations, benchmarked; every imported row still passes the full constraint set |
| [ ] P2.5 | Epoch pipeline at scale | L | high | P0.7 | Incremental Merkle maintenance, parallel proving, witness parity at production depth; an epoch cadence spec published |
| [ ] P2.6 | Status distribution v1 | L | high | P2.5 | Signed, versioned, short-lived status artifacts (revocation and validity) distributable via CDN and verifiable offline; freshness rules specified; this is the backbone of P3.6 |
| [ ] P2.7 | HA automation | L | high | P1.10 | Supervisor-managed automated failover replaces the manual runbook; an induced-failure drill passes; the split-brain analysis is documented |
| [ ] P2.8 | Multi-region DR | L | med | P2.7 | An async standby region and a region-evacuation drill with measured RTO/RPO |
| [ ] P2.9 | 10M-profile load certification | L | med | P2.1-P2.7 | The published harness drives the planning targets above against the HA topology during a rolling deploy and one induced failover; the numbers are committed |
| [ ] P2.10 | Cost model | S | low | P2.9 | Infrastructure cost per 1M persons per year, derived from P2.9, committed |
| [ ] P2.11 | Standing chaos program | M | low | P0.4 | Scheduled chaos runs against the staging profile with paging verified; findings feed checks |

Exit gate: P2.9 green and published.

---

## P3 - Federation and the relying-party ecosystem

Objective: multiple independent issuing authorities interoperate, and third
parties verify against Polaris without talking to us.

| ID | Item | Size | Risk | Blocked by | Definition of done |
|---|---|---|---|---|---|
| [ ] P3.1 | Topology decision record | M | low | - | An ADR choosing federated per-authority instances (the schema's explicit-attestation model) over a central instance; the threat-model delta documented |
| [ ] P3.2 | Inter-authority protocol v1 | L | high | P3.1 | A versioned spec: attestation exchange, anchor cross-publication, epoch alignment, revocation propagation; conformance vectors included |
| [ ] P3.3 | Transparency service | L | med | P3.2 | A public append-only anchor log, mirrored; `ct-monitor` productized as an independent daemon anyone can run; a tampering drill proves detection |
| [ ] P3.4 | Relying-party API v1 | M | med | P2.6 | A stable versioned verification API; RP organizations authenticate via mTLS or OAuth2 client credentials. This is API access auth only: identity never becomes a login product, per the vocation. Deliberately reopens the retired "OIDC" scope in that narrow form |
| [ ] P3.5 | RP SDKs and conformance suite | L | med | P3.4 | Server-side verify SDKs (Python, TypeScript) with a public conformance suite; passing it is the integration contract |
| [ ] P3.6 | Offline verification protocol v1 | L | high | P2.6 | A short-lived signed presentation plus status bundle verifiable with no connectivity; replay and freshness bounds specified; a reference verifier CLI ships |
| [ ] P3.7 | mDL / ISO 18013-5 bridge | L | med | P3.4 | Read-only derived mdoc presentment from a Polaris token for mDL-reader interop; no new trust semantics |
| [ ] P3.8 | W3C VC issuance endpoint | M | low | P3.4 | An optional VC representation of a verification result; explicitly a format, not a trust model |
| [ ] P3.9 | Per-authority isolation review | L | med | P3.1 | Operator RBAC and data isolation reviewed for the federated topology; row-level security added where the review demands it |
| [ ] P3.10 | Federation proven in CI | M | med | P3.2 | A CI job boots two instances as two authorities and proves cross-verification, attestation revocation, and anchor cross-checks end to end |

Exit gate: P3.10 green, plus one external team completing an SDK integration
using only the public docs and the conformance suite.

---

## P4 - Hardware token and enrollment field kit

Objective: the physical layer. Runs in parallel from P1. The schema already
models the card (serials, biometric binding type, duress hash, succession);
this phase makes the card real.

An honest constraint, stated up front: ML-DSA on secure elements is
bleeding-edge silicon. The card profile therefore targets the schema's own
UC-6 dual-signature model: a classical signature on today's certified silicon
plus a post-quantum binding, migrating on-card as FIPS 204 hardware certifies.
That is exactly the migration the database was built to express.

| ID | Item | Size | Risk | Blocked by | Definition of done |
|---|---|---|---|---|---|
| [ ] P4.1 | Card profile spec v0 | L | high | - | The on-card data model, dual-signature layout, PIN and duress semantics, and succession handling, reviewed against the threat model |
| [ ] P4.2 | Software token emulator and vectors | L | med | P4.1 | An emulator implementing the profile plus published test vectors; everything downstream develops against it |
| [ ] P4.3 | Personalization service | L | high | P4.2, P1.2 | A secure key-injection flow bound to the audit-of-record; every personalization is an AoR event |
| [ ] P4.4 | Enrollment station reference | XL | high | P4.3 | A kiosk build: locked-down browser, vendor-neutral biometric capture abstraction, document authentication hooks, and the 800-63A evidence flow; produces a complete IAL-mapped enrollment record |
| [ ] P4.5 | Verifier device reference | L | med | P4.2, P3.6 | An NFC/QR read path with online and offline verification, running the P3.6 protocol |
| [ ] P4.6 | Silicon tracking and eval | M | ext | - | [EXT: vendor availability] A FIPS 140-3 SE vendor matrix, ML-DSA-on-SE status, and eval-kit results as they exist; refreshed quarterly |
| [ ] P4.7 | Duress-on-card interaction spec | M | med | P4.1 | The duress entry method specified with a safety review; indistinguishability preserved end to end at the physical layer |

Exit gate: enroll a person, personalize a token (emulator or eval silicon),
verify online and offline, revoke, and recover, with every step on the AoR and
every guarantee holding.

---

## P5 - Pilots [EXTERNAL GATES]

Objective: real, consenting users. Institutions decide; our job is to make
saying yes cheap and safe.

| ID | Item | Size | Risk | Blocked by | Definition of done |
|---|---|---|---|---|---|
| [ ] P5.1 | Pilot-in-a-box | L | med | P1, P4.2 | A one-command pilot deployment profile: ops pack, metrics and reporting bundle, DPIA template, consent flow, and a rollback-and-erasure plan |
| [ ] P5.2 | Campus pilot | M | ext | P5.1 | [EXT: university MOU, IRB] An opt-in campus credential shadow pilot; our part is support engineering and the public exit report |
| [ ] P5.3 | Agency pilot | L | ext | P5.2 | [EXT: county or agency MOU] Shadow verification alongside an existing credential at a real agency, to the same reporting bar |
| [ ] P5.4 | Post-pilot fix arcs | L | med | each pilot | Every pilot finding triaged, fixed, and pinned; the report published |

Exit gate: two completed pilots, public reports, zero constitutional
violations under real use, and erasure honored on request and proven.

---

## P6 - Certification and assurance [EXTERNAL-HEAVY]

Objective: the assurance envelope a government sponsor requires. External
certifications are theirs to grant; readiness is ours to build.

| ID | Item | Size | Risk | Blocked by | Definition of done |
|---|---|---|---|---|---|
| [ ] P6.1 | Validated-crypto option | M | ext | P1.2 | [EXT: module certification] The custody interface drives a FIPS 140-3 validated module; the two-witness discipline is retained; the toggle documented |
| [ ] P6.2 | NIST 800-63-4 mapping | L | med | P4.4 | An IAL/AAL/FAL mapping with evidence per control; gaps closed or explicitly waived with reasons |
| [ ] P6.3 | FedRAMP/StateRAMP-ready profile | L | ext | P1.5 | [EXT: authorization] A GovCloud IaC reference, a control-mapping SSP skeleton, inheritance documented |
| [ ] P6.4 | SOC 2 evidence automation | M | ext | P1 | [EXT: audit] Continuous evidence collection wired to the ops stack |
| [ ] P6.5 | Accessibility to WCAG 2.2 AA / Section 508 | L | med | - | Every surface audited and conformant; automated accessibility checks added to CI |
| [ ] P6.6 | Independent audit, public red team, bug bounty | M | ext | P1.12 | [EXT: funding] Scoped from [RED-TEAM-SCOPE](docs/RED-TEAM-SCOPE.md); results published unredacted where safe |
| [ ] P6.7 | Formal-methods expansion | L | med | P0.7 | Specs for C1, C2, and the epoch/status protocol; the purge coverage property proven; [meta/tla](meta/tla/README.md) graduates from demonstrator to maintained |

Exit gate: a sponsoring authority accepts the authorization package [EXT].

---

## P7 - National rollout [EXTERNAL-DOMINATED]

Objective: the machinery of scale-out. Statute, funding, and program authority
belong to government; every buildable artifact is ready before it is asked for.

Planning targets (to be validated, not asserted): 350M persons; 5,000
sustained and 50,000 peak verifications/s nationally across federated
instances; an enrollment surge of 200,000/day sustained during rollout years;
99.99% availability on the verification path.

| ID | Item | Size | Risk | Blocked by | Definition of done |
|---|---|---|---|---|---|
| [ ] P7.1 | Institutional prerequisites register | M | ext | - | [EXT: statute, SORN, funding] The complete list of legal instruments and decisions national operation requires, maintained as a living document |
| [ ] P7.2 | Authority onboarding factory | L | med | P3, P6.3 | Instance-per-authority provisioning automation plus an onboarding playbook; a new authority reaches interoperating-live in days |
| [ ] P7.3 | National capacity model | L | med | P2.9 | The targets above validated by extrapolation from measured P2 numbers plus staged federation load tests; published |
| [ ] P7.4 | 24/7 operations design | M | ext | P2.11 | [EXT: staffing] SOC integration, on-call structure, public status and incident communications, all specified and tool-ready |
| [ ] P7.5 | Coexistence and migration spec | M | med | P3.7 | Phased coexistence with Real ID and legacy credentials, cutover and sunset criteria, no flag-day |
| [ ] P7.6 | Quantum-event readiness | L | med | P2.5 | A mass UC-6 migration drill at scale: the measured time to re-sign a population when an algorithm falls; runbook committed |
| [ ] P7.7 | Public transparency program | M | low | P3.3 | Anchors, availability, audit results, and aggregate warrant-audit statistics published on a standing cadence |

Exit gate: the first state authority live at scale on its own instance; a
national program office assumes ownership; the project transitions to steward
of the reference implementation.

---

## Standing rules (every phase, every ship)

1. **The constitution gates everything.** No item ships if it erodes C1-C10 or
   the vocation. Anything touching them carries a constitutional note in its
   CHANGELOG entry.
2. **The ship discipline is unchanged** (see [CLAUDE.md](CLAUDE.md)): edit,
   test, check, bump, CHANGELOG, gate READY.
3. **Every new capability ships with its checks.** A capability without a
   detection-tested check is not done.
4. **Exercise, never just read.** Ten of ten defects found in the 2026-08-31
   sweeps were invisible to reading. Anything operational is run against a
   scratch stack before it is called done.
5. **Numbers carry stamps.** Any stated count or benchmark names the version
   it was measured at.
6. **External gates never wait on us.** For every [EXT] row, the buildable
   readiness artifact is listed and built before the external actor is
   engaged.
7. **Reopened decisions are recorded.** This file reopens Linux deployment
   (P1.1) and narrow RP API authentication (P3.4) against earlier
   retirements, with reasons inline. Banking and payments stay out
   permanently: C10 is not a phase.

## Permanent non-goals

No payment rails or monetary claims (C10). No central biometric database. No
population-scale attribute filtering or analytics. No social scoring. No
commercial or advertising use of verification data. No real personal data
before the P5 consent framework exists. These do not expire with any phase.

## Execution protocol for the next session

1. Read [CLAUDE.md](CLAUDE.md), then this file. The active phase is the lowest
   phase with pending rows.
2. Pick the first row whose Blocked-by column is satisfied; prefer S and M
   rows when resuming cold.
3. One row is one ship (S rows may batch). Mark `[>]` on start; mark `[x]`
   with a version stamp when the definition of done is verifiably true.
4. If a definition of done proves wrong or underspecified, amend the row in
   the same ship and say so in the CHANGELOG entry.
5. When a phase's exit gate is met, record it in the CHANGELOG and move to
   the next phase.
