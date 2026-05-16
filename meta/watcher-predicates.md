# meta/watcher-predicates.md — falsifiable predicate per HYDRA watcher

**Origin:** v9.28 Sanctum (`sanctum/2026-05-16-v9-28-hydra-revamp.md`), Hydra item #1. Mirrors v9.24 T1#2 `meta/ant-predicates.md` one layer up.
**Status:** Enumeration complete. DEPRECATION_CANDIDATE marks watchers whose only claim is about narrative or internal HYDRA state. Operator has one grace cycle (v9.30) to ground the predicate against an external record OR accept the watcher's removal.
**Cadence:** Re-audit on every watcher added or modified. Re-evaluate DEPRECATION_CANDIDATEs at v9.30.

---

## Rule (Hydra #1, with VANTA's external-record refinement)

> Schema, security, performance, adversary watch real things. Cognitive,
> mission, trajectory, civitas mostly watch the narrative. For each
> watcher write the single falsifiable claim it makes about code or
> runtime; any watcher whose only claims are about MISSION.md or
> drift-from-snapshot gets demoted to optional or cut.
>
> **VANTA's external-record refinement (2026-05-16):** each predicate
> must name the `external_record` — the outside-the-cognitive-layer
> artifact that confirms the predicate's truth. A predicate whose only
> witness is internal HYDRA snapshot/state is AP1 (self-observation
> without ground-touch); flag DEPRECATION_CANDIDATE.

---

## Schema for each entry

```
**<watcher_name>** — STATUS (KEEP / DEPRECATION_CANDIDATE / OPTIONAL)
  Predicate:        <one-sentence falsifiable claim>
  External record:  <artifact outside HYDRA that confirms truth>
  AP risk:          <which anti-pattern fires if external record absent>
  Notes:            <optional)
```

---

## The 9 watchers + CM — per-watcher predicates

### KEEP — runtime-grounded (4 of 9 + CM)

**schema_watcher** — KEEP (v9.28 #4 adds runtime grounding)
- Predicate: *Every table declared in `polaris_sql/01_schema.sql`
  exists in the live database with matching column types, and every
  partial unique index in the schema file is present in `pg_indexes`.*
- External record: `psql -d polaris -c "\d <table>"` for declared
  tables; `SELECT * FROM pg_indexes WHERE indexname = ...` for
  indexes. Pre-v9.28: file-only check. v9.28: adds live-DB diff via
  `schema_watcher.query_live_schema()`.
- AP risk: pre-v9.28, AP1 risk (file only) — closed in v9.28.
- Notes: this is one of the two watchers ground in runtime per Hydra #4.

**security_watcher** — KEEP (v9.28 #4 adds runtime grounding)
- Predicate: *`polaris_web/security.py`'s `secure_headers()` returns a
  CSP without `'unsafe-inline'` AND a protected route returns HTTP 403
  to an unauthenticated request.*
- External record: file content for CSP check; live HTTP request via
  `security_watcher.probe_running_app()` for the protected-route
  check. v9.28: adds the live HTTP probe (with INCONCLUSIVE fallback
  if app not running).
- AP risk: closed in v9.28 by adding live probe.
- Notes: second of two runtime-grounded watchers per Hydra #4.

**performance_watcher** — KEEP
- Predicate: *Every query in
  `polaris_web/test_app.py::TestPerformanceBudget` (and equivalents)
  completes within its documented budget (default: p95 < 200ms for
  atlas; p95 < 50ms for verifications).*
- External record: live query timing via `EXPLAIN ANALYZE` against
  the running DB; the test suite's own assertions.
- AP risk: low. The predicate is grounded in DB-side timing.

**adversary_watcher** — KEEP
- Predicate: *Zero rows in `TokenLifecycleEvent` were inserted with
  the `EMERGENCY_PASSWORD_LOGIN_AUTHORIZED` event_type in the last 24h
  that lack a corresponding `recover-admin.sh` audit row.*
- External record: DB query against `TokenLifecycleEvent` joined
  against the recovery-admin audit log.
- AP risk: low. Grounded in DB rows.

**ant_colony_watcher** — KEEP (review at v9.30 #13 for overlap)
- Predicate: *Mycelium pheromone table has rows from at least one
  commander ant in the last 6 hours, AND no soldier class has been
  silent for >2 hours during business windows.*
- External record: DB query against `Pheromone` table (live row
  freshness; per-soldier-class deposit timestamps).
- AP risk: low (grounded in DB). **v9.30 #13 review:** overlaps with
  adversary_watcher for some pheromone-class-anomaly detection;
  deduplicate which is canonical for swarm-health vs swarm-anomaly.

**CM (constitutional meta-constraint)** — KEEP + ENFORCE (v9.28 #5)
- Predicate: *Every claim CM makes about the system's structural
  invariants (test count ≥ N for each constraint; predicate-count
  matches ant-count; freeze-line conditions hold at the named version)
  is true at the moment of the brief.*
- External record: counts from `python3 -m unittest --list`; ant
  enumeration from `polaris_swarm/`; freeze-line file content from
  `MISSION.md`.
- AP risk: was AP1 pre-v9.28 (CM observed itself without consequence);
  v9.28 #5 wires CM-mismatch into `ai-done.sh` as a hard gate (override
  `POLARIS_ALLOW_CM_MISMATCH=1` with audit-trail line).
- Notes: this is the watcher that gets the bite per Hydra #5.

---

### DEPRECATION_CANDIDATE — narrative-only (4 of 9)

**cognitive_watcher** — DEPRECATION_CANDIDATE
- Predicate attempt: *Cognitive layer artifacts exist and are reachable.*
- External record: NONE that isn't itself a HYDRA snapshot.
- AP risk: AP1 (self-observation without ground-touch). Only claims
  the cognitive layer exists and is described by other cognitive-layer
  artifacts.
- Honest reading: this watcher's findings ("brain-map count drifted",
  "scripts/ai-* invocation declined") are interesting but not
  load-bearing for any operator-side decision. v9.30 disposition:
  ground in an external artifact (commit-rate? operator-facing
  metric?) or cut.

**mission_watcher** — DEPRECATION_CANDIDATE
- Predicate attempt: *`MISSION.md` document is reachable + the
  state-map section matches the current version.*
- External record: NONE outside the document itself; the
  state-map-vs-version check is a self-consistency assertion within
  the cognitive layer's own narrative.
- AP risk: AP1. The predicate's witness IS the document the predicate
  is about.
- Honest reading: mission_watcher caught real drift in v9.13 + v9.18
  (test counts in MISSION.md got stale). But that drift is now caught
  by `scripts/ai-test-counts.sh --update` directly. v9.30 disposition:
  cut OR fold into ai-test-counts.sh as a pre-commit hook.

**trajectory_watcher** — DEPRECATION_CANDIDATE
- Predicate attempt: *Ship-rate over trailing 7 days is within the
  expected band (1-5 ships/day); file-churn cluster does not exceed
  a documented threshold.*
- External record: git log for ship-rate; git diff for file-churn.
  Technically external, BUT the "expected band" is itself a narrative
  choice — there is no operational consequence to ship-rate burst
  beyond the cognitive-layer's own "mission-creep signal."
- AP risk: AP3 (proposal-as-self-elaboration). The bands exist
  because the watcher invented them, not because they map to real
  operator decisions.
- Honest reading: scope-rule from v9.24 T4 captures the real
  trajectory concern (narrative/core ratio with a hard ceiling).
  v9.30 disposition: cut; scope-rule replaces it.

**civitas_watcher** — DEPRECATION_CANDIDATE
- Predicate attempt: *Treasury balance is non-negative; citizen counts
  per class are within configured bounds.*
- External record: `polaris_swarm/civitas/treasury-roll.json` content
  for Treasury; `census-roll.json` for citizens. **These artifacts are
  also watched by ant_treasury_balance (Mycelium) + ant_census_drift
  (Mycelium).** Per item #13 (v9.30 deduplication), one of the three
  observation paths is redundant.
- AP risk: REDUNDANCY (not AP-catalog hit; v9.30 #13 territory).
- Honest reading: civitas_watcher overlaps with Mycelium ants
  watching the same artifacts. v9.30 #13 will decide: which observer
  is canonical (probably the ant) and the others get removed. v9.28
  flags this for v9.30 #13 work.

---

## Summary

| Watcher              | Status                  | v9.30 Action |
|----------------------|-------------------------|--------------|
| schema_watcher       | KEEP                    | +runtime probe (v9.28 #4) |
| security_watcher     | KEEP                    | +runtime probe (v9.28 #4) |
| performance_watcher  | KEEP                    | none |
| adversary_watcher    | KEEP                    | none |
| CM                   | KEEP + ENFORCE          | +ai-done.sh gate (v9.28 #5) |
| cognitive_watcher    | DEPRECATION_CANDIDATE   | ground or cut |
| mission_watcher      | DEPRECATION_CANDIDATE   | cut (replaced by ai-test-counts.sh) |
| trajectory_watcher   | DEPRECATION_CANDIDATE   | cut (replaced by scope-rule) |
| civitas_watcher      | DEPRECATION_CANDIDATE   | deduplicated by #13 |

**Count:** 5 KEEP (4 watchers + CM), 4 DEPRECATION_CANDIDATE.

This matches VANTA's framing: "Schema, security, performance,
adversary watch real things. Cognitive, mission, trajectory, civitas
mostly watch the narrative." The enumeration confirms the framing
from external evidence (each watcher's predicate + external_record).

---

## Operator disposition (v9.30)

The DEPRECATION_CANDIDATE list is binding. At v9.30, each candidate
must either:

1. Have its predicate grounded in an external artifact (operator names
   one in MISSION.md or as a new structural invariant), OR
2. Be removed from `polaris_hydra/watchers/` with the corresponding
   line removed from `polaris_hydra/host.py`'s watcher registry, OR
3. Be moved to `polaris_hydra/watchers/optional/` (operator-toggle;
   not in default brief composition).

The default disposition if no operator decision by v9.30 is **cut**
(per the Sanctum's "no predicate, no watcher" rule).

---

*Per v9.28 Sanctum, Hydra #1 + VANTA's external-record refinement
2026-05-16.*
