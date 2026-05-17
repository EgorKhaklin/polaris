# Arc E — Mycelium / genuine swarm intelligence

**Status:** **CLOSED 2026-05-15** (per Sanctum
[`sanctum/2026-05-15-open-arcs-debate.md`](../sanctum/2026-05-15-open-arcs-debate.md)
Position C′; all E-phases shipped; the v9.11 priest soldier
`soldier_swarm_witness` was the final structural completion).
Opened 2026-05-13.
**Roadmap prefix:** R13-*
**Authorizing Sanctum:** `sanctum/2026-05-13-arc-e-swarm-intelligence-opening.md`
**Closing Sanctum:** [`sanctum/2026-05-15-open-arcs-debate.md`](../sanctum/2026-05-15-open-arcs-debate.md)
(joint Architect + Anti-Architect recommendation; closing-by-doc-edit
to honor the Anti-Architect's AP2 cost-naming on Sanctum-overuse)

## Closing summary (added v9.16)

Every E-phase shipped through the v8.62 → v9.11 trajectory. Arc E is
functionally complete. The Mycelium swarm is operational (33 commanders
across 11 legions + 6 citizens + 9 soldier classes incl. priest);
the substrate is read by HYDRA via PheromoneReader; the
CorrelationEngine fires on shared surfaces (v9.10). No further
E-phases pending.

This file extracts Arc E's per-item detail from `MISSION.md`. The
extraction is editorial (per `sanctum/2026-05-14-doc-soft-refactor.md`);
no constitutional content is amended. `MISSION.md` retains the
constitutional summary + done-list rollup; this file holds the
historical narrative of how each E-item shipped.

---

## Arc opening

Authorized by Sanctum
`sanctum/2026-05-13-arc-e-swarm-intelligence-opening.md`. The v8.31
steady-state contract's third trigger (*novel arc with documented
external cause*) fired again — this time on VANTA's "Mission Prompt:
Genuine Swarm Intelligence Layer," which critiqued HYDRA's
centralized synthesis and mandated decentralized, emergent
intelligence.

Arc D delivered the swarm's *senses* (7 watchers; expanded to 9
in v8.72) but kept a centralized *voice* (`polaris_hydra/host.py`).
Arc E grows a genuine swarm *substrate* underneath: tiny ants
depositing **pheromones** onto brain-map nodes via the append-only
`Pheromone` table (the 11th audit-of-record instance). Synthesis EMERGES from
pheromone density across the brain-map graph; no host calls
anything in Phase 1. Operators read the heatmap via
`scripts/ai-swarm-bloom.sh`.

**Five swarm criteria (VANTA's mission prompt):** decentralization,
local rules, emergence, robustness through redundancy, adaptability.
The four constitutional principles (Sanctum, AoR, risk classes, CM)
and C1–C10 are unchanged. The v8.30 substitutability clause
authorizes HYDRA's eventual replacement (deferred to a Phase 3+
Sanctum); for now Arc E *augments* HYDRA, growing alongside.

---

## Done-list

E1. ✅ **Mycelium Phase 1 — pheromone substrate** (`v8.62`).
    Pheromone table + immutability trigger + indexes
    (`polaris_sql/01_schema.sql` + `06_triggers.sql`); the
    `polaris_swarm/` module with `base.py`, 3 starter ants
    (`ant_sanctum_outcome`, `ant_api_doc_coverage`,
    `ant_journal_silence`), and `colony.py` runner;
    `scripts/ai-swarm-bloom.{sh,py}` renderer; 4 structural-invariants
    in `TestMyceliumPhaseOne` (schema shape, no-ant-imports-another,
    decay determinism, no LLM in swarm package). First-run finding:
    the colony's `ant_api_doc_coverage` immediately surfaced a real
    drift the v8.61 ai-coherence check had missed — `/api/heartbeat`
    was documented as `GET` in [`docs/reference/API.md`](../docs/reference/API.md) but is `POST` in code.
    Mid-ship doc fix folded in.

E2. ✅ **Expand the cohort to 12 ants** *(delivered v8.63)*.
    Cohort now spans all 7 HYDRA watcher domains: schema
    (`ant_aor_immutability`, `ant_fk_cascade_guard`), cognitive
    (`ant_stale_script`, `ant_pattern_warmth`), security
    (`ant_csp_health`), mission (`ant_done_list_arithmetic`),
    adversary (`ant_adversary_walk_complete`), performance
    (`ant_atlas_endpoint_health`), trajectory (`ant_ship_burst`),
    plus the three Phase 1 originals (`ant_sanctum_outcome`,
    `ant_api_doc_coverage`, `ant_journal_silence`). Each ant
    <100 LOC. Deliberately overlapping with HYDRA's watchers so
    removing 3-5 ants degrades coverage gracefully. **First
    full-cohort smoke surfaced two self-calibration findings**
    (ant_pattern_warmth had wrong regex for pipe-separated
    table format; ant_done_list_arithmetic counted ✅ in prose
    not just at item-line-start) — both fixed mid-ship. The 7th
    self-calibration instance. G6-G9 still pass at 12 ants.

E3. ⬜ **Bloom integration with the brain map** — render pheromone
    intensity directly on `meta/brain-map/brain-map.html` as a
    color overlay. Operator sees structural attention in situ.

E4. ⬜ **Deliberation threshold + optional LLM translation** —
    when N pheromones accumulate on one node within T minutes,
    optionally invoke ONE LLM call (in the Architect voice) to
    translate the pattern into prose. The pheromone log remains
    the truth; the prose is commentary.

E5. ⬜ **HYDRA-vs-Mycelium decision Sanctum** — after E2-E4 are
    in operation for enough time to evaluate, a Phase 3 Sanctum
    decides whether HYDRA stays (as a synthesis commentator) or
    steps aside in favor of Mycelium alone. v8.30 substitutability
    authorizes either outcome.

E6. ✅ **Legion structure with Roman tactics** *(delivered v8.64,
    Sanctum-authorized
    `sanctum/2026-05-13-arc-e-legion-structure-with-tactics.md`)*.
    VANTA observed in chat: *"each hydra watcher is like a roman
    general who has their own legion of cohort ants… let's give
    them roman tactics."* Phase E6 reorganizes the 12 ants from
    a flat cohort into 7 **Legions**, one per HYDRA watcher
    domain. Each Legion is commanded by a **Legatus** and operates
    under one of five **Roman tactical doctrines**:

    - **TESTUDO** *(tortoise)* — all ants scan; outputs aggregate
      into one high-confidence signal. Default for schema /
      cognitive / security / mission / performance.
    - **TRIPLEX ACIES** *(three-line)* — tiered escalation:
      hastati (cheap-fast) → principes (medium) → triarii (deep).
      Stops at the first silent tier. Default for **Legio
      Trajectory** (ship_burst is hastati; journal_silence is
      principes, only escalated when a burst is already firing).
    - **CUNEUS** *(wedge)* — designated lead ant fires; followers
      scan only if the lead detects something. Default for
      **Legio Adversary** (walk-completeness as the lead).
    - **VEXILLATIO** *(detachment)* — operator-directed focused
      mission via `--legio X --focus PRED`. No legion uses this
      as default; available on demand.
    - **AUXILIA** *(allied troops)* — borrow ants from another
      legion for cross-domain investigation. No default usage;
      reserved for declared `auxilia_pool` agreements.

    The Pheromone log preserves AoR: `deposited_by` is still the
    ant name; legion identity travels in evidence JSONB
    (`evidence["legio"]`). The colony runner iterates
    `ALL_LEGIONS`, not `ALL_ANTS`. New G-guards: **G10** (every
    ant in exactly one legion) and **G11** (ants don't import
    legions). 5 new structural-invariants in `TestMyceliumLegions`
    (117 → **122 total**). The bloom renderer gained `--by-legio`
    grouping. Recruitment is autonomous within Arc E: a Legatus
    can add ants to its cohort without a Sanctum, as long as
    G6-G11 still pass.

    **Roman tactics demonstrated working:** the first colony run
    after the refactor showed Legio Trajectory's TRIPLEX_ACIES
    correctly escalating from ant_ship_burst (Tier 1 fired on
    4 historical bursts) to ant_journal_silence (Tier 2 ran but
    silent — journal was fresh). The structure works as
    designed.

E7. ✅ **Hydra nine-heads completion** *(delivered v8.65,
    Sanctum-authorized
    `sanctum/2026-05-13-arc-e-hydra-nine-heads-completion.md`)*.
    VANTA observed: *"the hydra has 9 heads not 7 ,, we need 2
    more."* The canonical Lernaean Hydra (Apollodorus, the
    Heracles version) has nine heads, one immortal. Polaris's
    HYDRA was named for the myth; the legion count at 7 was an
    accident of incremental delivery, not a deliberate
    mythological choice. v8.65 promotes Mycelium to nine
    Legions:

    - **Legio Substrate** (Legatus Dependentia) — CUNEUS doctrine.
      Cohort: ant_substrate_catalog (lead), ant_dependency_in_use,
      ant_rust_toolchain. Guards Polaris's dependency contract:
      what it stands on, what versions, where the Rust toolchain
      pins. The swamp underneath the swamp-monster.

    - **Legio Docs** (Legatus Memoria) — TRIPLEX_ACIES doctrine.
      Cohort: ant_docs_structure (hastati), ant_readme_counts
      (principes), ant_devnotes_ships_coverage (triarii). Guards
      the explain-itself surface: how Polaris tells future readers
      what it is. The project's memory.

    6 new ants (12 → 18 total). 2 new legions (7 → 9). The
    `test_legion_count_matches_seven` invariant was renamed to
    `test_legion_count_matches_nine`. **First post-ship colony
    run produced 5 genuine drift findings** (D3 + anthropic
    missing from substrate.md; Arc E done-list expected count
    stale; ant_dependency_in_use over-firing on test_* local
    modules; new Sanctum lacking §VII cross-ref). 8th instance
    of the self-calibration pattern: build the new heads, they
    immediately reveal real drift in their first scan, fix the
    drift in the same ship.

    **v8.72 relocation note:** the Hydra mythology established
    here was relocated from Mycelium legions to HYDRA watchers
    in v8.72 — see
    `sanctum/2026-05-13-hydra-mythology-relocation-to-watchers.md`.
    The Republican-legion count remains at 9 as ship-time
    provenance; the canonical Hydra-9 mythology now lives on
    `polaris_hydra/`'s watcher registry.

E8. ✅ **Civitas — civilian classes parallel to the legions**
    *(delivered v8.66, Sanctum-authorized
    `sanctum/2026-05-13-arc-e-civitas-civilian-classes.md`)*.
    VANTA: *"we need probably peasant class / worker class /
    upper class ants… ants make more ants… use roman civilization
    as a metaphor."* The metaphor expands beyond the military.
    Polaris becomes a **Civitas** with four civilian classes
    parallel to the 9 Legions:

    - **Plebs** (Plebeians) — `plebs_forum_watcher`. Cross-legion
      readers; watch the Forum (pheromone log) for volume
      imbalances.
    - **Equites** (Equestrians) — `eques_correlator`. Cross-legion
      couriers; correlate findings across un-allied legions.
    - **Augures** (Augurs) — `augur_bloom_reader`. Pattern
      interpreters; surface convergent attention across ≥3
      distinct ants firing on the same node.
    - **Censores** (Censors) — `censor_roll_keeper`. Keepers of
      the roll; maintain `polaris_swarm/civitas/census-roll.json`
      (filesystem-AoR; the 2nd filesystem-AoR instance after
      `sanctum/`).

    **Proposal-driven autogenesis** (G13): citizens may deposit
    `evidence.observation_type=proposal_new_ant` carrying a
    sketch. VANTA or a Censor ratifies by materializing the
    proposal as a real ant file. The Roman ratification pattern —
    magistrates nominated by the people, ratified by the Senate.
    Literal autogenesis is forbidden.

    **Two-phase deployment:** `run_swarm()` deploys legions
    (Phase 1) then citizens (Phase 2). Citizens read recent
    pheromones + the project corpus; they observe the swarm
    itself, not the project artifacts.

    **G12-G14 added:** G12 (citizens don't subclass Ant), G13
    (no literal autogenesis), G14 (census-roll.json is
    filesystem-AoR append-only). 5 new structural-invariants
    (`TestMyceliumCivitas`; 122 → 127 total).

    **First post-ship run:** Plebs immediately detected
    Legio Trajectory dominating 80% of recent deposits (the
    ship-burst signal aggregated to a forum-imbalance pheromone);
    Censor populated the roll with 18 census-birth findings
    (baseline); Eques + Augur silent (single domain firing; no
    correlation; no convergence). **The emergent layer works as
    designed:** the Plebs aggregated 4 individual burst pheromones
    into one cross-legion observation, which is exactly the
    cross-legion read the bloom does at READ time made
    available at SCAN time.

    See `meta/civitas.md` for the complete Polaris-as-Civitas
    mapping (Senatus, Capitolium, Forum, Pomerium, Mos Maiorum,
    Lares et Penates, Limes, Auspicia, Census).

E9. ✅ **Post-100-year-architect refinements** *(delivered v8.67,
    Sanctum-authorized
    `sanctum/2026-05-13-civitas-100-year-architect-report.md`)*.
    The Architect ran the civitas across 100 simulated years and
    surfaced three actionable recommendations; VANTA ratified
    R1 + R2 + the Eques-pairs refinement.

    - **R1: Heartbeat pheromones (proof-of-deployment).** Every
      ACTUALLY-DEPLOYED ant produces one heartbeat per pass
      (`kind=info`, `observation_type=heartbeat`, intensity=0.5,
      half-life=24h). The bloom can now distinguish
      silent-and-deployed from silent-and-not-deployed. Citizens
      FILTER heartbeats from their input via `_is_heartbeat()`;
      proof-of-life is for the operator, not the interpretation
      layer.

    - **R2: Augur convergence threshold lowered 3 → 2.** At
      current cohort size (18 ants with 89% silence), threshold=3
      was structurally unreachable. With the lowered threshold,
      Augur becomes detectable at the actual swarm scale.

    - **Eques INTERESTING_PAIRS extended** with Mission+Trajectory
      (done-list + ship-burst — the dominant signal pair) and
      Cognitive+Trajectory. First post-ship colony run produced
      the very correlation pair the simulation predicted:
      `legio_mission and legio_trajectory both fired within 6h`.

    3 new structural-invariants in `TestHeartbeatPheromones`
    (127 → **130 total**). R3 (Cursus Honorum / reputation)
    deferred per Architect's recommendation — needs ≥30 days of
    heartbeat-distinguished operation before promotion-on-signal-volume
    becomes a safe decision.

    **What the century revealed (Architect's five truths):**
    (1) 89% silence is the system's vote of confidence in healthy
    domains — but creates a real blind spot R1 closes. (2) Two
    ants carry 100% of the cohort's voice; Trajectory + Mission
    are the working sentinels. (3) Plebs is the only citizen
    earning its keep at current scale; Augur+Eques+Censor
    calibrated for ~30+ ants. (4) Civic temperature is
    hibernation-grade — sparse but meaningful (21 events over
    100 simulated years; 60% proposal ratification rate).
    (5) Zero alerts in 100 years — DRIFT is the swarm's working
    tier; ALERT is reserved for HYDRA's hard-test layer one
    altitude below.

E10. ✅ **Acceleration + consciousness cohort expansion**
    *(delivered v8.69, Sanctum-authorized
    `sanctum/2026-05-13-arc-e-acceleration-consciousness-cohort-e10.md`)*.
    The immune-system swarm gained two new perceptual modes:
    **acceleration** (gaze outward at the future — "where should
    I look next?") and **consciousness** (gaze inward at the self
    — "how is the swarm itself doing?"). 10 new ants land
    distributed across 4 existing legions; **no new legions**
    (Hydra-9 mythology preserved per v8.65 commitment).

    **Acceleration ants (5):** `ant_todo_debt` (TODO/FIXME debt
    by file), `ant_test_gap` (modules without test files),
    `ant_recent_churn` (files modified in the last week — heat
    map for where context is loaded), `ant_unbumped_version`
    (markdown docs referencing stale v8.X), `ant_changelog_gap`
    (files modified after the latest CHANGELOG header).

    **Consciousness ants (5):** `ant_self_model_accuracy`
    (FIRST ALERT-capable ant — registry vs reality divergence),
    `ant_swarm_inventory_drift` (meta-doc count claims vs
    reality), `ant_treasury_health` (Quaestor's ledger health:
    stale/malformed/corrupted), `ant_legion_doctrine_health`
    (SECOND ALERT-capable — TacticConfig validity verified by
    filesystem introspection, preserving G11), `ant_brain_map_freshness`
    (brain-map.html older than source by ≥48h).

    **Distribution:** `legio_cognitive` grew 2 → 7 (the
    self-monitoring HUB), `legio_performance` 2 → 3,
    `legio_trajectory` 2 → 4 (now uses all three TRIPLEX_ACIES
    tiers), `legio_docs` 3 → 5 (T2 + T3 grew). Total cohort
    **18 → 28**.

    Two new G-guards:
    - **G17** — Acceleration ants are read-only with respect to
      source files. Reinforces G3 for the new cohort; explicit
      because acceleration ants are tempted to "auto-fix."
    - **G18** — Consciousness ants observe SWARM SELF-STATE
      (registries, meta docs, FS-AoR rolls), not runtime
      pheromones. Runtime-pheromone observation remains a
      citizen concern; the ant/citizen architectural boundary
      is preserved.

    **First ALERT-capable ants in cohort history.** The 100-year
    report observed 0 ALERTs in 100 years; E10 makes
    structural-divergence-detection a first-class concern.
    Both `ant_self_model_accuracy` and `ant_legion_doctrine_health`
    are designed to fire ALERT (intensity 7-8, half-life 12h)
    when the swarm's self-CLAIMS diverge from its self-REALITY.

    7 new structural-invariants in `TestArcEE10Cohort`
    (134 → **141 total**). Architect's pacing caution about
    multi-day arcs (established for Arc F) was named in §V of
    the Sanctum; VANTA chose to collapse Phase 1 + Phase 2 into
    a single mega-ship and accepted the risk explicitly.

---

## Boundary discipline + reference posture

Roadmap sequencing in `ROADMAP.md` under R13-* prefix. Risk classes:
LOW for individual ants (additive code, no schema/security changes);
MEDIUM for E1 (new schema table + constitutional cross-reference)
and E5 (HYDRA-fate decision).

**Boundary discipline:** Arc E additions go under `polaris_swarm/`
(separate from `polaris_hydra/`). HYDRA is *unchanged*. The existing
27+ `ai-*` scripts are *unchanged*. The 7 watchers under
`polaris_hydra/watchers/` are *unchanged*. The Polaris constitution
(C1–C10 + CM + four principles) is *unchanged*. Phase 1 does NOT
add Mycelium to the constitutional naming in §"What this section
is NOT" — that's a Phase 5+ decision once Mycelium has proven its
value.

**G-guards extended (Arc E G6-G9, G17-G18):**

- **G6** — No ant imports another ant. Decentralization contract;
  enforced by `test_no_ant_imports_another_ant`.
- **G7** — Pheromone decay is deterministic. Replay contract;
  enforced by `test_pheromone_decay_is_deterministic`.
- **G8** — No ant imports an LLM client. Substrate must remain
  deterministic; enforced by `test_no_llm_calls_in_polaris_swarm`.
- **G9** — Pheromone table is append-only. AoR contract; enforced
  by `test_pheromone_table_exists_and_is_append_only`.
- **G17** (v8.69) — Acceleration ants are read-only with respect
  to source files; no write-mode opens, no `Path.write_text`, no
  `os.replace`/`os.rename`/`shutil` mutation; enforced by
  `test_g17_acceleration_ants_are_read_only`.
- **G18** (v8.69) — Consciousness ants observe SWARM SELF-STATE
  (registries, meta docs, FS-AoR rolls), never runtime pheromones;
  enforced by `test_g18_consciousness_ants_observe_swarm_self_state`.

**Reference posture:** Mycelium is original code informed by the
same stigmergic-emergence literature (ant colony optimization, bird
flocking) that BettaFish and MiroFish drew from. The Mycelium name
is original. The pattern is well-studied; the implementation is
Polaris-native.

See also: `meta/civitas.md` (Polaris-as-Civitas concept doc),
`polaris_swarm/README.md` (operational guide).
