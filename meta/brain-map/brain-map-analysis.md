# Polaris brain-map analysis — v8.54

Generated: 2026-05-13T07:18:48+00:00
Map: `meta/brain-map/brain-map.html`

## I. Topology

| Metric | Value |
|---|---|
| Nodes | 222 |
| Edges | 246 |
| Connected components | 72 |
| Largest component | 82 (36.9%) |
| Isolated singletons | 56 |
| Graph density | 0.0100 |
| Mean degree | 2.01 |
| Median degree | 1 |
| Max degree | 27 |

## II. Layer distribution

| Layer | Nodes | Mean degree |
|---|---|---|
| behavior | 70 | 0.43 |
| schema | 65 | 2.54 |
| cognitive | 29 | 5.10 |
| knowledge | 18 | 0.83 |
| decision | 17 | 2.00 |
| constitution | 15 | 2.27 |
| observation | 8 | 2.50 |

## III. Top-10 hubs

| Degree | Group | Type | Label |
|---|---|---|---|
| 27 | cognitive | ai_script | `ai-help` |
| 22 | schema | schema_table | `IdentityToken` |
| 17 | constitution | principle | `Sanctum protocol` |
| 12 | schema | schema_table | `Agency` |
| 11 | cognitive | ai_script | `ai-architect` |
| 10 | schema | schema_table | `VerificationEvent` |
| 10 | cognitive | ai_script | `ai-done` |
| 9 | cognitive | ai_script | `ai-propose` |
| 8 | schema | schema_table | `TokenLifecycleEvent` |
| 8 | cognitive | ai_script | `ai-meta` |

## IV. Orphans by layer

Nodes with degree 0 (no connections) or degree 1 (single connection). High d0 counts in a layer indicate parser miss OR genuinely isolated nodes (e.g., the schema's `AuthAuditLog` admin-log).

### behavior  (d0=42, d1=26)

- d0: (procedure) `close_anchor_batch`
- d0: (route) `/api/heartbeat`
- d0: (route) `/api/quit`
- d0: (route) `/api/since-heartbeat`
- d0: (route) `/login`
- d0: (route) `/logout`
- d0: ... +36 more
- d1: (function) `uc1_issue_and_activate` → (route) `/uc1/issue`
- d1: (function) `uc4_activate_reserve` → (route) `/uc4/activate-reserve`
- d1: (function) `uc5_bind_device` → (route) `/uc5/bind-device`
- d1: (function) `uc7_warrant_audit` → (route) `/uc7/warrant-audit`
- d1: (procedure) `uc8_revoke_token` → (route) `/uc8/revoke`
- d1: (procedure) `uc9_initiate_recovery` → (route) `/uc9/initiate-recovery`
- d1: ... +20 more

### cognitive  (d0=0, d1=3)

- d1: (ai_script) `ai-coverage` → (ai_script) `ai-help`
- d1: (ai_script) `ai-mission` → (ai_script) `ai-help`
- d1: (ai_script) `ai-sanctum` → (ai_script) `ai-help`

### constitution  (d0=4, d1=5)

- d0: (constraint) `C2`
- d0: (constraint) `C6`
- d0: (principle) `Audit-of-record`
- d0: (principle) `Risk classes`
- d1: (constraint) `C4` → (module) `security.py`
- d1: (constraint) `C7` → (schema_table) `CryptographicAlgorithm`
- d1: (constraint) `C9` → (module) `test_app.py`
- d1: (constraint) `C10` → (watcher) `AdversaryWatcher`
- d1: (principle) `CM (meta-constraint)` → (constraint) `CM`

### decision  (d0=0, d1=4)

- d1: (sanctum) `R11-1 — Multi-signature transitional state (UC-6)` → (principle) `Sanctum protocol`
- d1: (sanctum) `R11-2 — Catastrophic-loss recovery (UC-9)` → (principle) `Sanctum protocol`
- d1: (sanctum) `hydra-constitutional-integration` → (principle) `Sanctum protocol`
- d1: (sanctum) `trajectory-watcher-7th-channel` → (principle) `Sanctum protocol`

### knowledge  (d0=10, d1=4)

- d0: (ship) `quantum-observer`
- d0: (devnote) `atlas-scaling`
- d0: (devnote) `audit-of-record`
- d0: (devnote) `concurrency`
- d0: (devnote) `known-gotchas`
- d0: (devnote) `prior-art-analysis`
- d0: ... +4 more
- d1: (ship) `anchoring` → (sanctum) `R10-2 functional DID anchoring`
- d1: (ship) `duress-codes` → (sanctum) `r11-5-duress-codes`
- d1: (ship) `federation` → (sanctum) `r11-3-issuer-federation`
- d1: (ship) `multi-sig-migration` → (ship) `issuer-discretion`

### observation  (d0=0, d1=2)

- d1: (watcher) `MissionWatcher` → (hydra_host) `HYDRA host`
- d1: (watcher) `TrajectoryWatcher` → (hydra_host) `HYDRA host`

### schema  (d0=0, d1=42)

- d1: (schema_table) `AuthAuditLog` → (trigger) `trg_authaudit_append_only`
- d1: (schema_table) `DeviceBinding` → (schema_table) `IdentityToken`
- d1: (schema_table) `IssuerDiscretionPolicy` → (schema_table) `Agency`
- d1: (index) `idx_identitytoken_individual` → (schema_table) `IdentityToken`
- d1: (index) `idx_identitytoken_status` → (schema_table) `IdentityToken`
- d1: (index) `idx_verificationevent_timestamp` → (schema_table) `VerificationEvent`
- d1: ... +36 more

## V. Cross-layer edges

### Intra-layer (edges within a single layer)

- `schema`: 85
- `cognitive`: 75
- `behavior`: 22
- `observation`: 7
- `knowledge`: 4
- `decision`: 2
- `constitution`: 1

### Inter-layer (top 10 cross-layer edges)

- `constitution` ↔ `decision`: 17
- `decision` ↔ `knowledge`: 11
- `constitution` ↔ `schema`: 6
- `cognitive` ↔ `decision`: 6
- `constitution` ↔ `observation`: 6
- `behavior` ↔ `constitution`: 4

## VI. Edge-type distribution

| Type | Count |
|---|---|
| `invokes` | 75 |
| `fk` | 45 |
| `indexes` | 25 |
| `calls` | 22 |
| `realizes` | 17 |
| `links_to` | 17 |
| `fires_on` | 15 |
| `reports_to` | 7 |
| `authorized` | 6 |
| `enforced_by` | 6 |
| `monitors` | 6 |
| `constrains` | 4 |
| `is_constraint` | 1 |

## VII. Missing-edge suggestions

**6 potential edges surfaced by heuristic.** Each is a *suggestion for human review*, not a recommendation to auto-add. The system grows by VANTA's deliberate decisions, not by agent inference. Review and either:

- (a) accept the suggestion → extend the parser to extract this edge class deterministically next time;
- (b) reject as not-a-real-connection → no action;
- (c) add explicit `# brain-map:` annotation in the source file to make the relationship machine-readable.

### sanctum→ship mentions not yet linked  (5)

- `sanctum/2026-05-11-m2-1-snark-exploration` mentions ship `zk-snark` but no `authorized` edge
- `sanctum/2026-05-11-r10-2-functional-did-anchoring` mentions ship `zk-snark` but no `authorized` edge
- `sanctum/2026-05-11-r11-1-multisig-transitional` mentions ship `federation` but no `authorized` edge
- `sanctum/2026-05-11-r11-3-issuer-federation` mentions ship `zk-snark` but no `authorized` edge
- `sanctum/2026-05-12-new-chapter-swarm-hydra-arc-opening` mentions ship `zk-snark` but no `authorized` edge

### ship→sanctum references not yet linked  (1)

- `ships/zk-snark.md` references `sanctum/2026-05-11-m2-1-snark-exploration` but no `authorized` edge

## VIII. Architect's read

Graph is sparse — many singletons and small components. Either the parser is missing edge classes, the system is genuinely fragmented, or (most likely) some node types are reference material that doesn't naturally cite outward.

**Connectivity progress over time:**
- v8.52: 216 nodes / 126 links / 113 components
- v8.53: 219 nodes / 243 links / 72 components
- v8.54: 222 nodes / 246 links / 72 components (largest = 82 = 36.9%)
