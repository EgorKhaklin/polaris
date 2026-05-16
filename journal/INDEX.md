# journal/INDEX.md — per-arc summary

Per-day session logs accumulate fast (35+ entries on 2026-05-11 alone).
This index summarizes by *strategic arc* — the v2 mission item or
cognitive-layer change being shipped — so future sessions can grep
the right day without paging through every entry.

Maintenance: when a new arc closes, add a row here. Auto-generation
from `ai-journal.sh` summaries is a future-backlog item.

---

## 2026-05-09 — v2 opening + cognitive-layer maturity

| File | Arc |
|---|---|
| `2026-05-09.md` | v2 mission opened (D + A arc); ai-* script-group reorganization; first cognitive-layer reflection cycle. R8-3 OIDC + R9-1 banking + R9-2 launcher variants explicitly deferred. |
| `2026-05-10.md` | (continuation; light day) |

## 2026-05-11 — v2 shipping rampage (12 mission items × 6 Sanctums)

The vast majority of v2 shipped in a single day. Each ship followed
the established audit-then-Sanctum pattern.

| Arc | Ship | Sanctum | Audit refinements |
|---|---|---|---|
| R10-2 / M2-2 | DID anchoring (`AnchorBatch` + Merkle helper) | `sanctum/2026-05-11-r10-2-functional-did-anchoring.md` | 6 (R1–R6) |
| v8.19 | The Sanctum protocol itself | (backfilled; first under-protocol Sanctum is v8.20) | — |
| v8.20 | Sanctum self-monitoring + audit-of-record principle | `sanctum/2026-05-11-v8-20-sanctum-self-monitoring-audit-of-record-architect-reflection.md` | — |
| R11-3 / M2-8 | Issuer federation (`AgencyTrustAttestation`) | `sanctum/2026-05-11-r11-3-issuer-federation.md` | 6 (R1–R6) |
| R10-1 / M2-1 | ZK-SNARK over Plonky2 — **two-Sanctum design**: exploration first, then ship | `sanctum/2026-05-11-m2-1-snark-exploration.md` (exploration), `sanctum/2026-05-11-m2-1-zk-snark-plonky2-merkle.md` (ship) | 9 (R1–R9) |
| R11-5 / M2-10 | Duress codes (compulsion resistance — v2 mission-closer) | `sanctum/2026-05-11-r11-5-duress-codes.md` | 6 (R1–R6) |
| v8.25 | UI catch-up — duress field on `/verifications/new` + `/duress` admin/auditor dashboard | (LOW-risk autonomous; no Sanctum) | — |
| v8.26 | Cognitive-layer folder reorganization (this day) | (LOW-risk autonomous; no Sanctum) | — |

### Detailed day logs

| File | Hours | Highlights |
|---|---|---|
| `2026-05-11.md` | start-of-day → mid-day | early R10-2 ship; v8.19/v8.20 Sanctum protocol; R11-3 federation work |
| `2026-05-11-architect.md` | mid-day → end-of-day | Architect persona consultations across M2-1 exploration → ship; M2-10 duress; UI catch-up; folder reorganization |

## 2026-05-12 — cognitive maturity + publish-readiness + Arc D + maintenance

The longest single-day arc in Polaris history. Started in steady-state
maintenance, walked through constitutional elevation + steady-state
resolution + publication gate, opened and closed an entire new arc
(Arc D — Swarm / HYDRA), and ended with prior-art-driven defense
guards. Six Sanctums opened or referenced; eight ships (v8.27 → v8.45).

| Arc | Ship | Sanctum | Notes |
|---|---|---|---|
| v8.27 | Cognitive-layer self-tightening | (LOW-risk) | v1 deferred trio → ✗ RETIRED |
| v8.28 | UI graduation phase — v2 substrate exposure | (LOW-risk) | `/anchors`, `/epochs`, `/federation` viewers; dashboard tiles |
| v8.29 | Cognitive-layer audit | (LOW-risk) | Closed soft signals via 12-layer audit |
| v8.30 | Cognitive-layer constitutional elevation | `sanctum/2026-05-12-cognitive-layer-constitutional-elevation.md` | The four-principle constitution: Sanctum, AoR, risk classes, CM |
| v8.31 | Post-v2 strategic moment resolved as steady-state | `sanctum/2026-05-12-post-v2-steady-state-declaration.md` | Three external triggers for future arcs named |
| v8.32 | Full systems maintenance pass (12-layer audit) | (LOW-risk) | Surfaced + fixed silent gap in test-DB load |
| v8.33 | Hypothesis property tests restored | (env-only) | 355 → 365 active tests |
| v8.34 | CHANGELOG full check + optimization | (LOW-risk) | Reordered scrambled bottom, added version-index table |
| v8.35 | First publish-readiness pass | `sanctum/2026-05-12-first-publish-readiness-declaration.md` | Apache 2.0 attached; repo 335 MB → 6.3 MB |
| v8.36 | Final pre-publish approval | `sanctum/2026-05-12-final-pre-publish-approval.md` | 10-layer audit passed; FINAL-GATE APPROVED |
| v8.37 | Arc D opened — Swarm / HYDRA Phase 1 | `sanctum/2026-05-12-new-chapter-swarm-hydra-arc-opening.md` | HYDRA host + SchemaWatcher (H1+H2) |
| v8.38 | CognitiveWatcher (H3) | (LOW-risk) | Phase 2 begins |
| v8.39 | SecurityWatcher (H4) | (LOW-risk) | Self-calibrated baseline |
| v8.40 | MissionWatcher (H5) | (LOW-risk) | Caught real arrearage (H1+H2 emoji backfill) |
| v8.41 | AdversaryWatcher (H6) | (LOW-risk) | 6-section walk parser |
| v8.42 | PerformanceWatcher (H7) — Phase 2 closes 6/6 watchers live | (LOW-risk) | 5-consecutive-self-calibration pattern named |
| v8.43 | Arc D CLOSED — Phase 3 constitutional integration (H8) | `sanctum/2026-05-12-hydra-constitutional-integration.md` | HYDRA named in MISSION.md; substitutability preserved |
| v8.44 | Mode I prior-art defense — 5 HYDRA architectural guards | (LOW-risk) | G1 randomness · G2 eval · G3 watcher read-only · G4 shared schema · G5 file-tailing |
| v8.45 | Multi-agent + meta-agent scan drift closure | (LOW-risk) | Closes count drift, arc-header drift, stale watcher heuristic, ai-hydra entrypoint orphan |

### Detailed day logs

| File | Hours | Highlights |
|---|---|---|
| `2026-05-12.md` | full day | Every ship listed above |
| `2026-05-12-architect.md` | full day | Architect consultations across constitutional elevation, steady-state declaration, publish gate, Arc D opening + closing, prior-art reverse-engineering, deep multi+meta scans |

## 2026-05-13 — post-Arc-D iteration protocol + bug fixes + brain map + auth hygiene + publication polish

**Fifteen ships in one day** under VANTA's iteration protocol (each ship
closes a parked item and surfaces the next). Started with M2/L1 from
v8.45 backlog (CSP externalization + schema CHECK constraints); proceeded
through three meta-defense channels; opened and closed the brain-map
arc (visualization of the entire architecture); shipped three bug-fix
iterations on the localhost-refused-to-connect / session-cookie
symptom; ended with publication polish (full-system doc-drift closure,
clutter cleanup, and a deep professional reorganization).

| Arc | Ship | Sanctum | Notes |
|---|---|---|---|
| v8.46 | CSP externalization + schema CHECK constraints (M3 + L1 from v8.45 scan) | (LOW-risk) | 8 inline-JS sites → 4 external files; 5 new DB CHECKs |
| v8.47 | SecurityWatcher 6th channel — template inline-JS scan | (LOW-risk) | Self-calibration #6: G2 false-positive on re.compile fixed mid-ship |
| v8.48 | M2 adversary-walk coverage 9/9 v2 ships | (LOW-risk) | 5 missing walks added (anchoring, federation, zk-snark, duress, quantum); soft property test |
| v8.49 | TrajectoryWatcher — HYDRA's 7th watcher | `sanctum/2026-05-13-trajectory-watcher-7th-channel.md` | Rejected "StrategicAdvisor" full-shape; Architect's shape-A authorized |
| v8.50 | Housekeeping batch — L2 + L5 + gotcha #5 + no-FK-CASCADE guard | (LOW-risk) | 5 atlas endpoints (was 3); audit-of-record CASCADE rule named; 2 new tests |
| v8.51 | Bug fix v1 — heartbeat foreground listeners + threshold 45s → 180s | (bug-fix carve-out) | Browser-background setInterval throttling × stale-heartbeat watch interaction |
| v8.52 | Polaris brain map — D3 force-directed visualization | (LOW-risk) | 216 nodes / 126 links; `meta/brain-map/brain-map.html` + `ai-brain-map.sh`; auto-regen on every ai-done |
| v8.53 | Brain-map parser v2 — 6 new edge extractors | (LOW-risk) | 126 → 243 links (+93%); cognitive-layer mean degree 0.0 → 5.1; ai-help is new top hub |
| v8.54 | Brain-map trigger parser fix + `--analyze` gap-surfacer | (LOW-risk) | UPDATE OF column regex; non-agentic Shape A over neuro-surgeon framing |
| v8.55 | Bug fix v2 — removed pagehide/beforeunload listeners from heartbeat.js | (bug-fix carve-out) | sendBeacon('/api/quit') was firing on EVERY navigation, not just tab-close |
| v8.56 | Session-secret rotation on every launcher up/rebuild — auth hygiene | (LOW-risk) | `rotate_session_secret_if_unset` helper wired into 3 launch paths; existing tab cookies invalidated on new instance |
| v8.57 | Full-system doc-drift closure — 20-ship reconciliation | (LOW-risk) | 4 parallel deep-audit agents; ~65 findings; ~15 high-leverage fixes across 3 tiers |
| v8.58 | Bug fix v3 — launcher early-return bypass of secret rotation | (bug-fix carve-out) | Both `launch_docker` and `launch_native` had early-returns skipping the v8.56 rotation; fixed with `--force-recreate --no-deps app` + native pid kill |
| v8.59 | Publication cleanup — maximum aura, no clutter | (LOW-risk) | Tier 1 caches + Tier 2 `.claude/launch.json` + Tier 3 /tmp scratch; tree 8.4 → 7.4 MB |
| v8.60 | Deep professional reorganization | `sanctum/2026-05-13-v8-60-deep-reorganization.md` | 20 file moves + 235 ref-site fixes; docs/ subdivided into story/reference/operator; assets/ + docs/paper/; meta/brain-map/ grouped |

### Detailed day logs

| File | Hours | Highlights |
|---|---|---|
| `2026-05-13.md` | full day | Every ship listed above; iteration-protocol cadence |

## Patterns surfaced across the arc

Recurring observations recorded in the journal (and promoted to
DEVNOTES when load-bearing):

- **Audit-then-Sanctum cadence**: 6–9 refinements per ship. R10-2: 6.
  R11-3: 6. R11-1: 7. R10-1: 9. R11-5: 6. The refinement count tracks
  the cryptographic surface, not the engineering surface.
- **Audit-of-record principle generalizes**: every new schema-touching
  ship adds an instance. v2 added 5 (TokenSignature, AnchorBatch,
  AgencyTrustAttestation, TokenStateEpoch, DuressEvent), bringing the
  total to 8.
- **Advisory-lock catalog grows by ship granularity**: R10-2 added
  per-algorithm (4th), R11-3 added per-attesting-agency (5th), R10-1
  added per-procedure (6th — first non-per-entity). R11-5 added zero
  (DuressEvent is pure-append, no contention).
- **Exploration Sanctum is a real variant**: M2-1 used it because the
  cryptographic design space (4 SNARK families × 3 circuits × 3 setup
  postures = 36 combinations) was too wide for a single ship-Sanctum
  to be honest about. The first Sanctum surveyed; VANTA picked
  C3+A4+B3; the second Sanctum shipped within the narrowed space.
- **Schema-load ordering caught at Docker first-run**: pre-existing
  FK-to-AppUser forward references in 01_schema.sql (silently lurking
  since v8.17) only manifested when the user ran `Polaris.command`
  fresh. Fixed in v8.25 by promoting AppUser DDL into 01_schema.sql.

## How to use this index

- Looking for a specific ship → match the version (v8.X) or mission
  item (M2-X / R-id) in the table above, then open the named Sanctum
  for the formal record or the named journal day for the working log.
- Looking for a pattern recurrence → see "Patterns surfaced across
  the arc" section.
- Looking for a deferral → grep journal/*.md for "deferred" or check
  the relevant Sanctum's §III Alternatives.
