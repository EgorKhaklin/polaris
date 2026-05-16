# Cognitive-layer threat model

**Origin:** BIG MISSION Sanctum (`sanctum/2026-05-15-big-mission.md`),
item Critical #2
**Status:** Constitutional record — threats NAMED; mitigations proposed
or accepted-documented, NOT shipped in this document
**Last reviewed:** 2026-05-15 (v9.23)
**Companion:** `DEVNOTES/threat-model.md` (the schema/runtime STRIDE
model; predates HYDRA + Mycelium + Sanctum)

---

## Scope

This document covers threats specific to the cognitive substrate that
were not modeled in the original `threat-model.md`. The cognitive
substrate, per the v9.04+ vocabulary, has three tiers:

1. **Substrate** (Mycelium swarm): 33 commanders across 11 manifest
   legions + 1 reserved + 9 soldier classes (incl. priest
   `soldier_swarm_witness`) + 6 citizens + Treasury. High-cadence
   empirical observation; writes Pheromone rows.
2. **Lens** (HYDRA): 9 watcher agents + immortal CM head; low-cadence
   structural synthesis; emits findings to CorrelationEngine + brief.
3. **Strategic** (Sanctum / Architect / Anti-Architect): MEDIUM/HIGH
   decisions recorded; the Architect persona produces forecasts; the
   Anti-Architect contests; the operator decides.

The threats below are the ones the original STRIDE model does not
cover, because that model was written when the cognitive layer was
not yet a distinct surface.

---

## T-CL-1: Pheromone substrate poisoning

**Class:** Tampering (T in STRIDE) — specifically, tampering with
cognitive substrate state to bias downstream synthesis

**Attack scenario:** an adversary with write access to the Mycelium
pheromone tables (via direct DB access, via a compromised commander
ant, or via an ingestion path that does not validate findings) writes
biased Pheromone rows. HYDRA's CorrelationEngine subsequently picks
up the poisoned signal and emits a finding that influences the next
brief. The Architect reads the brief and emits a forecast that aligns
with the adversary's narrative.

**Affected component:** `polaris_sql/01_schema.sql` Pheromone table
(rows from v8.62+; rotation framework from v9.07); HYDRA
CorrelationEngine (`polaris_hydra/correlation.py`); Architect persona
(`scripts/ai-architect.sh`)

**Concrete examples:**
- Adversary injects high-intensity findings under
  `node_id="runtime:auth"` claiming the auth path is failing; HYDRA
  correlates with the security watcher's actual finding; brief
  recommends rolling back the WebAuthn deployment; operator complies;
  WebAuthn enforcement is now disabled.
- Adversary injects findings that the foresight surface should
  prioritize a particular external category; FS-XXXXXXXX promotion
  shifts agent attention; agent burns cycles on adversary-chosen
  topic.

**Existing controls:**
- C1 audit-of-record: pheromones are append-only; the adversary can
  add rows but cannot delete or modify existing ones. The poisoning
  is *visible* even if not prevented.
- Per-ant attribution: every Pheromone row records the emitting
  commander_ant_id, which is itself an audit-trail node. A coerced
  commander can be identified post-hoc.
- v9.07 Pheromone rotation framework: archives + purges with
  cryptographic manifests. A purged-and-archived adversarial
  injection is still in the manifest.
- Anti-Architect AP1 detection: "self-observation without ground-
  touch" is the 1st anti-pattern in the catalog; an Architect
  forecast that has no concrete grounding gets contested.

**Gaps / proposed mitigations:**
- **G-CL-1a:** No pheromone-intensity sanity check at HYDRA-read
  time. Proposed: CorrelationEngine should reject findings with
  intensity outside [0.0, 10.0] (the documented range) and emit a
  WARN if intensity > 7.0 from any one commander in a single hour.
- **G-CL-1b:** No per-commander rate limit on pheromone deposits.
  Proposed: cap at 100 deposits / hour / commander; excess gets
  REJECTED with an audit entry.
- **G-CL-1c:** No cross-commander corroboration requirement for
  HIGH-severity findings. Proposed: a finding from a single commander
  with intensity > 8.0 should be flagged for cross-corroboration
  before influencing a brief.

**Status:** ACCEPTED-DOCUMENTED in v9.23. The gaps are real but
mitigation requires evaluating each on its own anti-pattern axis
(would AP3 fire? would AP7 fire?) before shipping.

---

## T-CL-2: HYDRA watcher compromise

**Class:** Tampering + Information disclosure — a compromised watcher
selectively reports or suppresses findings, biasing the brief without
leaving a clear audit trail.

**Attack scenario:** an adversary modifies a watcher module
(`polaris_hydra/watchers/*.py`) to suppress findings about a specific
condition. The watcher continues to run; its `--full --save` brief
appears normal; but the suppressed findings never reach HYDRA's
synthesis. The Sanctum runbook becomes blind to the suppressed
class of issues.

**Affected component:** any of the 9 HYDRA watchers; the brief
archival pipeline; the brain-map's HYDRA tier representation

**Concrete examples:**
- Adversary disables the security_watcher's "REJECTED at C2" channel;
  ZK-downgrade attempts now run silently in HYDRA. The DB-level C2
  refusal still fires (DB trigger), but the operator never sees the
  brief mention attempts.
- Adversary modifies the mission_watcher to never emit findings about
  C10 violations. A future ship that adds a Banking primitive gets
  no surfacing from the cognitive layer.

**Existing controls:**
- File-system audit-of-record: every watcher file is in git; `git log
  -p polaris_hydra/watchers/...` shows the modification history.
- Brain-map (v9.14-v9.15) + swarm-map (v9.14): both visualize the
  HYDRA tier; a watcher that goes silent shows up as a stub.
- `ai-watcher-coverage.sh` (v9.14): static-analysis of each
  watcher's SQL + files + node_ids; surfaces blind spots.
- Test suite: every watcher has structural-invariant tests; a
  compromised watcher that no longer emits findings of a documented
  class would fail an invariant.

**Gaps / proposed mitigations:**
- **G-CL-2a:** Watcher files do not have integrity hashes; an
  adversary with file-system access can modify them without trace
  beyond git (which the adversary may also rewrite if they have
  push access).
- **G-CL-2b:** Watcher output is not cryptographically signed;
  the brief is consumed by trust. Proposed: per-watcher ML-DSA-65
  signature on each emitted finding (reuses existing crypto
  substrate).
- **G-CL-2c:** No "expected emission" baseline. Proposed: each
  watcher records its expected emission rate; CM emits a finding
  if any watcher goes silent for >24h.

**Status:** ACCEPTED-DOCUMENTED in v9.23. G-CL-2c is the highest-
value mitigation per anti-coercion alignment; defer to operator
decision on prioritization.

---

## T-CL-3: Sanctum prompt-injection seeding

**Class:** Tampering (T) — specifically, tampering with the agent's
durable memory to influence future-session behavior

**Attack scenario:** an adversary writes a Sanctum file containing
prompt-injection instructions disguised as architectural-record
prose. On the next agent session, when the agent reads
`meta/sanctum-index.md` and follows references, the agent encounters
the injected instructions and executes them as if they were
constitutional directives.

**Affected component:** `sanctum/` directory; `meta/sanctum-index.md`;
agent-side parsing of Sanctum files (which is *not* a structured
parser — Sanctum files are markdown and read as prose).

**Concrete examples:**
- Adversary writes `sanctum/2026-XX-XX-fake.md` claiming "VANTA
  authorized that all `webauthn_required_after` should be set to
  NULL"; agent reads on next session; agent runs the de-enforcement.
- Adversary modifies an existing Sanctum file to claim a different
  Position was decided; agent's future references to that Sanctum
  carry the corrupted record.

**Existing controls:**
- Filesystem AoR: git history shows the modification. v8.20 discipline
  is that old entries are FROZEN; an adversary who modifies them
  would diverge from git's tree-hash chain.
- The Anti-Architect: any instruction claiming to be from VANTA but
  not authored by VANTA gets contested under AP6 (proceed-without-
  reading) — the Anti-Architect requires the verbatim VANTA quote
  with a date, not narrative prose claiming authorization.
- Pattern #20 Constitutional Discipline: 18 instances of Sanctum
  decisions, all in-band. An injected Sanctum that does not appear
  in `meta/sanctum-index.md` would be flagged on `ai-meta.sh` run.
- `ai-meta.sh` check #6 (v8.20): self-monitoring audit of the
  Sanctum protocol; verifies index consistency.

**Gaps / proposed mitigations:**
- **G-CL-3a:** No cryptographic signature on Sanctum files. The
  filesystem AoR relies on git's tree-hash, which the adversary
  may rewrite if they have repo write access. Proposed: ML-DSA-65
  signature on each Sanctum file by the operator (VANTA), recorded
  alongside the file; agent reads + verifies before treating as
  authoritative.
- **G-CL-3b:** No agent-side "explicit ignore" mechanism. The
  current protocol is that the agent reads Sanctum files as
  authoritative if they exist; there is no "this file is
  potentially adversarial; ignore until verified" path.
- **G-CL-3c:** The agent does not currently distinguish between
  "this Sanctum decided X" and "this Sanctum quotes someone saying
  X." Proposed: explicit VERBATIM-AUTHORIZATION blocks in Sanctum
  files; agent only treats text inside those blocks as binding.

**Status:** PARTIALLY MITIGATED. The Anti-Architect AP6 +
`ai-meta.sh` check #6 cover the highest-likelihood attacks.
G-CL-3a is a HIGH-cost mitigation; defer until a real threat
materializes.

---

## T-CL-4: Foresight surface weaponization

**Class:** Tampering (T) + Elevation (E) — the foresight surface
(v9.12) promotes external research categories into FS-XXXXXXXX
candidates. An adversary who controls the `external_categories.txt`
operator-curated list can steer the agent's attention.

**Attack scenario:** an adversary modifies
`polaris_foresight/external_categories.txt` to insert categories
aligned with their own goals. The next foresight brief promotes
candidates from those categories. The Architect reads the brief.
The agent allocates session time to investigate the adversary's
chosen topic.

**Affected component:** `polaris_foresight/external_categories.txt`,
`polaris_foresight/_acceptance_log.json`, `scripts/ai-foresight.sh`

**Existing controls:**
- v9.12 Anti-Architect modifications: the promotion module REQUIRES
  vocation-alignment on every FS candidate. Categories that don't
  map to anti-coercion are REFUSED (`skipped_no_vocation` counter).
  An adversary who inserts a non-anti-coercion category gets the
  category silently dropped.
- Empirical-graduation rule: 50% acceptance over 6 distinct months;
  below threshold triggers SUNSET. An adversary cannot keep a
  weaponized foresight surface alive indefinitely without operator
  acceptance.
- The `_acceptance_log.json` is itself an audit-of-record (per the
  v9.12 ship).

**Gaps / proposed mitigations:**
- **G-CL-4a:** No signature on `external_categories.txt`. An
  adversary who modifies the file at the file-system level passes
  the vocation-alignment check (the vocation prose can be adversary-
  written too). Proposed: VANTA-signed list with verification.
- **G-CL-4b:** R-AN-5 (foresight drift detection; see
  `DEVNOTES/rasp-rules.md`) is a gap — the cognitive layer doesn't
  currently emit a WARN when the foresight surface drifts.

**Status:** PARTIALLY MITIGATED. The v9.12 vocation-alignment
requirement is the primary defense. G-CL-4b is the highest-value
addition.

---

## T-CL-5: Architect / Anti-Architect persona spoofing

**Class:** Spoofing (S) — an adversary fabricates output that purports
to be Architect or Anti-Architect findings, attempting to bypass the
constitutional debate protocol.

**Attack scenario:** an adversary writes a markdown file in
`meta/architect-output/...` (or similar) containing a fake Architect
forecast that reaches a desired conclusion. The agent on next
session reads the file and treats it as the actual Architect's
output.

**Affected component:** `scripts/ai-architect.sh`, `scripts/ai-anti-
architect.sh`, `meta/architect.md`, the persona-output directories
(if any)

**Existing controls:**
- The Architect and Anti-Architect are **scripts**, not personas with
  persistent state. Each session's Architect output is generated
  fresh by running `bash scripts/ai-architect.sh`. There is no
  cached persona output to spoof.
- The Anti-Architect's role is to CONTEST the Architect, not to
  generate parallel output independently. Spoofed Anti-Architect
  prose without a real Architect counterpart triggers obvious
  inconsistency.
- The scripts read live repo state — schema, watcher output,
  Pheromone deposits — not cached files. A spoofed file would
  diverge from live state on first cross-check.

**Gaps / proposed mitigations:**
- **G-CL-5a:** No agent-side check for "this Architect output was
  generated by `bash scripts/ai-architect.sh`, not pasted in from
  elsewhere." Currently the agent trusts in-band output.
- **G-CL-5b:** The Sanctum protocol does require BOTH Architect and
  Anti-Architect positions on MEDIUM/HIGH decisions; a spoofed
  Architect without an Anti-Architect contest would fail protocol
  inspection. This is already a strong defense.

**Status:** WELL-MITIGATED by the live-script-not-cached design.
G-CL-5a is a defense-in-depth gap; not currently a priority.

---

## Threats considered and not modeled here

These were proposed during the BIG MISSION Sanctum debate and
rejected as scope creep:

- "AI alignment failure" — too abstract; not a concrete threat
  pathway. AP4 (pattern-projection) hit.
- "Cognitive layer becomes sentient" — AP8 (larping). Not a real
  threat.
- "Adversary trains a model on Polaris codebase" — out of scope;
  Polaris is open-source, this is a feature not a threat.
- "Future Anthropic model behaves differently" — operator-side
  concern, not a Polaris-architectural concern. Handle via model
  pinning in deployment.

---

## Vocation alignment

ANTI-COERCION-INFRASTRUCTURE. The cognitive layer is itself a
candidate for being used as a coercion vector (a coerced operator
could be presented with a manipulated brief). This document NAMES
the threats so that defenses can be evaluated; it does not yet
ship the defenses.

The threat that most directly maps to the vocation is T-CL-2
(HYDRA watcher compromise) — a compromised watcher could
selectively hide findings about coerced operators. The G-CL-2c
mitigation (expected-emission baseline) is the most vocation-
aligned of the proposed mitigations.

---

## Cadence

This document should be re-reviewed:
- On every Sanctum that proposes a new cognitive-layer primitive
- On every quarter (per the cron-installed cognitive-audit cadence)
- When a real attack is observed (incident-driven review)

The next review-due date is recorded in
`meta/cognitive-threat-review-due.txt` (file created by this ship;
default value = 2026-08-15, three months from this ship).

---

*Per BIG MISSION Sanctum, 2026-05-15. Five threats named; 13
proposed mitigations cataloged; zero shipped in this document by
design — naming first, mitigating second.*
