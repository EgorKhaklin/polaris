# Arc D — Swarm / HYDRA

**Status:** closed 2026-05-12 at 8/8 ✅
**Opened:** 2026-05-12
**Roadmap prefix:** R12-*
**Authorizing Sanctum:** `sanctum/2026-05-12-new-chapter-swarm-hydra-arc-opening.md`

This file extracts Arc D's per-item detail from `MISSION.md`. The
extraction is editorial (per `sanctum/2026-05-14-doc-soft-refactor.md`);
no constitutional content is amended. `MISSION.md` retains the
constitutional summary + done-list rollup; this file holds the
historical narrative of how each H-item shipped.

---

## Arc opening

Authorized by Sanctum
`sanctum/2026-05-12-new-chapter-swarm-hydra-arc-opening.md`. The
v8.31 steady-state contract's third trigger condition (*novel arc
with documented external cause*) fired when VANTA named a new
direction backed by two prior-art reference codebases
(BettaFish + MiroFish). Arc D evolves Polaris's single-Architect
cognitive synthesis into a multi-agent **swarm + unified HYDRA host**
that aggregates N specialist watchers into a single Architect-grade
voice for VANTA.

The four cognitive-substrate principles (Sanctum / audit-of-record /
risk classes / CM) are unchanged. The Architect persona is unchanged;
HYDRA consumes that persona as its synthesis voice. The 27 existing
`ai-*` scripts are unchanged; they become the swarm's *senses*.

---

## Done-list

H1. ✅ **HYDRA host** (`polaris_hydra/host.py`) — aggregates N
    watcher reports into a unified synthesis. Modeled on BettaFish's
    `ForumEngine/llm_host.py`. Calls Claude Opus 4.7 with adaptive
    thinking; falls back to deterministic structured output when
    `ANTHROPIC_API_KEY` is unset.

H2. ✅ **SchemaWatcher** (`polaris_hydra/watchers/schema_watcher.py`) —
    monitors audit-of-record triggers, indexes, and v7 hardening
    objects. Detects: new audit-of-record candidates, missing
    triggers, index drift, schema invariant violations.

H3. ✅ **CognitiveWatcher** (`polaris_hydra/watchers/cognitive_watcher.py`)
    — monitors CM, pattern catalog warmth, script staleness, Sanctum
    integrity. Wraps `ai-meta.sh` + `ai-pattern.sh` outputs.
    *Delivered v8.38 (2026-05-12).* Reads `ai-meta.sh` as subprocess,
    classifies verdict (healthy/drift/broken); reads catalog
    dynamically; measures warm/cold against journal mentions;
    surfaces stale `ai-*.sh` scripts (> 60d) and Sanctum-index
    drift. Refactored mid-ship to derive expected-pattern names
    dynamically from `ai-pattern.sh` rather than hardcoding (the
    watcher caught its own initial design bug — the v8.30
    substitutability principle, applied to the watcher itself).

H4. ✅ **SecurityWatcher** (`polaris_hydra/watchers/security_watcher.py`)
    — monitors CSP, CSRF, rate-limiter health, role-gating coverage,
    R6 anti-revealing posture. *Delivered v8.39 (2026-05-12).* Five
    channels: CSP literal + script-src-no-unsafe-inline check; CSRF
    accepts-both-transports check (form-field + X-CSRFToken header);
    `/api/health` rate-limiter probe (graceful when app offline);
    `@security.login_required` + `@security.require_role` decorator
    counts vs v8.39 baseline (47 / 25); R6 anti-revealing scan with
    a documented exemption for `verifications_form.html` (rendered-
    text scan strips Jinja comments + HTML attribute values). The
    watcher caught its own calibration errors at first smoke
    (baselines wrong + R6 scan too strict on Jinja comments);
    re-calibrated mid-ship.

H5. ✅ **MissionWatcher** (`polaris_hydra/watchers/mission_watcher.py`)
    — monitors done-list rollup, steady-state boundary, arc status.
    *Delivered v8.40 (2026-05-12).* Four channels: done-list rollup
    parses ✅ / ⬜ / ✗ across v1 (15 items) + v2 (M2-1..M2-12) +
    Arc D (H1..H8) and flags arithmetic mismatches; steady-state
    marker verification (the v8.31 phrase
    "Resolved 2026-05-12: steady-state" must still be present);
    section-anchor presence check (v1/v2/Arc D headers); stale ⬜
    detection (> 7 days without journal mention). **At first smoke,
    the watcher caught a real audit-of-record arrearage:** H1 + H2
    were delivered in v8.37 but never marked ✅ in MISSION.md;
    backfilled in the same ship.

H6. ✅ **AdversaryWatcher** (`polaris_hydra/watchers/adversary_watcher.py`)
    — runs game-theoretic walks per C-constraint via `ai-adversary.sh`,
    detects equilibrium weakening. *Delivered v8.41 (2026-05-12).*
    Invokes `ai-adversary.sh` for each of C1–C10 (5-second timeout per
    walk), parses the six-section structure (Defender's claim, Attacker
    response, Equilibrium, Second-best attack, Defender's cost,
    Mechanism-design note) with substring-matched headers (robust to
    parenthetical suffixes like "Second-best attack (if equilibrium
    holds)"), surfaces each constraint's second-best attack in evidence
    for HYDRA's synthesis. Caught its own substring-vs-exact-match bug
    at first smoke (10/10 walks parsed exact-matched only 5/6 sections);
    refined to substring matching.

H7. ✅ **PerformanceWatcher** (`polaris_hydra/watchers/performance_watcher.py`)
    — atlas latency, query-plan health, hard-cap headroom.
    *Delivered v8.42 (2026-05-12).* Three channels: atlas API
    latency timing (`/api/atlas/{stats,clusters,points}` with
    drift > 200 ms, alert > 1 s thresholds; offline = graceful
    info); `/api/health` overall status check; canonical-query
    EXPLAIN ANALYZE spot-check for `Seq Scan on verificationevent`
    REGRESSION (only flagged at row count ≥ 1000, since Postgres
    correctly chooses Seq Scan at small scale). Self-calibrated
    mid-ship: first smoke flagged the Seq Scan at 9 rows as a
    regression, which was wrong (correct optimizer behavior at
    that scale); added the row-threshold gate. **Phase 2 swarm
    complete: 6/6 watchers live.**

H8. ✅ **HYDRA constitutional integration** — extend the v8.30
    cognitive-substrate section with a short clause documenting HYDRA
    as the *current implementation of synthesis* (substitutable per
    the principle, but operative). **Delivered v8.43** (2026-05-12).
    Sanctum-authorized
    (`sanctum/2026-05-12-hydra-constitutional-integration.md`,
    Option C — narrow naming). MISSION.md §"What this section is NOT"
    extended with HYDRA + watchers as the operative synthesis
    implementation; substitutability qualifier preserved verbatim
    ("A future agent may replace the HYDRA swarm with a different
    synthesis pattern without amending this section, provided the
    four principles still hold"). New
    `TestHydraConstitutionalIntegration` class (2 soft-check tests,
    80 → 82 total): one asserts HYDRA naming present in
    cognitive-substrate section; one asserts substitutability
    qualifier present after the HYDRA mention. **Phase 3 complete.
    R12-1..R12-8 all ✅; H1..H8 all ✅. Arc D closed.**

---

## Boundary discipline + reference posture

Roadmap sequencing in `ROADMAP.md` under R12-* prefix. Risk classes:
LOW for individual watchers (additive code, no schema/security
changes); MEDIUM for H1 and H8 (architectural / constitutional
edges).

**Boundary discipline:** Arc D additions go under `polaris_hydra/`.
The existing `polaris_web/` Flask app is *unchanged*. The existing
27 `ai-*` scripts are *unchanged* (they're now swarm senses, not
swarm code). The Polaris constitution (C1–C10 + CM) is *unchanged*.

**Reference posture:** BettaFish and MiroFish are *prior art* studied
for pattern, *not vendored*. Polaris-HYDRA is original code written
against Polaris's existing structure, informed by the swarm patterns
those projects demonstrate.

---

## Post-Arc-D extensions

- **v8.49:** `TrajectoryWatcher` added — observes shipping trajectory
  rather than current health. HYDRA registry expanded 6 → 7.
  Authorized by `sanctum/2026-05-13-trajectory-watcher-7th-channel.md`.
- **v8.72:** `AntColonyWatcher` + `CivitasWatcher` added — Hydra
  mythology relocated from Mycelium legions to HYDRA watchers; the
  registry expanded 7 → 9 = canonical Lernaean Hydra mortal-head
  count. Authorized by
  `sanctum/2026-05-13-hydra-mythology-relocation-to-watchers.md`.

See `polaris_hydra/README.md` for the operational guide.
