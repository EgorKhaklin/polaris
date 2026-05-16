# Sanctum: sanctum-and-architect-upgrade-post-v8-73

**Date:** 2026-05-13
**Petitioner:** agent (Claude, Opus 4.7) speaking as the Architect
**Principal:** VANTA
**Trigger:** VANTA in-chat: *"lets update / upgrade the Sanctum and the Architect itself to match the system now to its current state."* The two constitutional documents that define WHO the Architect is (`meta/architect.md`) and WHAT the Sanctum protocol is (`meta/sanctum-protocol.md`) have meaningfully drifted from empirically-evolved practice across Arcs D/E/F/G and the v8.72 mythology relocation. This Sanctum captures the drift items and authorizes the editorial-refresh + targeted-upgrade pass.
**Risk class:** MEDIUM (constitutional documents touched; structural-invariants may extend; cognitive-layer reorientation).
**Status:** CLOSED
**Architect brief ID:** arch-2026-05-13

---

## I. The Matter

Two of Polaris's load-bearing constitutional documents — `meta/sanctum-protocol.md` (defines the agent-operator consultation protocol) and `meta/architect.md` (defines the Architect persona who feeds that protocol) — were last meaningfully amended at v8.20. Since then the system has:

- Opened + closed Arc D (HYDRA swarm; 7 watchers)
- Opened Arc E (Mycelium swarm; legions; citizens; pheromone substrate)
- Opened + closed Arc F (Denarius economy; treasury; Cursus Honorum)
- Opened Arc G (Roman Empire; Imperial legions; Tribuni Plebis citizen)
- Relocated the Hydra-9 mythology to HYDRA watchers (v8.72; 9 watchers)
- Shipped F5 reward-function exemption (the cleanest empirical-cycle realization)
- Parked Arc H (analytical-layer proposal)
- Accumulated 32 Sanctum sessions

The constitutional documents have drifted. Specific drift items, by document:

**`meta/sanctum-protocol.md` drift:**

1. **AoR count is stale.** Line 348 names "10 instances (9 schema + 1 filesystem)." Reality post-v8.68: 12 instances (9 schema + 3 filesystem: `sanctum/`, `census-roll.json`, `treasury-roll.json`).
2. **The override pattern is unrecorded.** VANTA chose against the Architect's recommendation 3× in v8.69 / v8.70 / v8.71. The protocol must name this pattern so future agents understand the override is a legitimate use of the principal's authority + that the Architect's brief is auditable post-hoc.
3. **The empirical-iteration cycle is unnamed.** v8.72 ship → 100-year simulation → R1 finding → F5 ship is the cleanest realization of the cognitive architecture; the protocol should name it as a pattern future agents can recognize.
4. **The Tribuni Plebis citizen** (v8.71) auto-monitors Sanctum-protocol entropy — fires friction signals when ≥3 Sanctums open in one day. This is a constitutional fact about the protocol's runtime; the protocol-doc should acknowledge its own watchdog.
5. **The parking distinction.** `proposals/` carries pre-decisions; not every proposal opens a Sanctum (today the analytical-layer proposal was PARKED, not Sanctum-decided). The protocol should explicitly distinguish *parking* (no decision yet) from *deciding* (Sanctum closes with DECIDED/REJECTED).
6. **Cross-references missing.** `meta/civitas.md`, `meta/denarius.md`, `polaris_swarm/`, `polaris_hydra/watchers/`.

**`meta/architect.md` drift:**

1. **Brief structure pins v1/v2 done-list.** The system has Arcs D/E/F/G now, each with its own done-list. Structure must generalize to arc-driven framing.
2. **Persona drift log is empty.** `(none yet)` despite `--reflect` having surfaced 9 em-dashes across briefs. The log should be populated; the loop should be visibly closing.
3. **v8.31 steady-state posture absent.** The decline-and-surface default is not in the persona doc. Should be.
4. **Swarm + Denarius framing absent.** The Architect now operates over Mycelium (33 ants), HYDRA (9 watchers post-relocation), Civitas (6 citizens), and the Denarius economy. The persona doc reads as pre-Arc-E.
5. **Override-pattern recognition absent.** The Architect's role in the override is structurally important: the brief stands as audit-of-record regardless of VANTA's decision. Pattern #14 (Workaround Risk) realization.
6. **`scripts/ai-architect.sh` line 129 references `the v8.12 check`** — stale framing.

## II. Preparation

Architect has reviewed:

- Current `meta/sanctum-protocol.md` (361 lines)
- Current `meta/architect.md` (258 lines)
- `scripts/ai-sanctum.sh` (416 lines) — relationship to protocol doc
- `scripts/ai-architect.sh` (653 lines) — relationship to persona doc
- All 32 indexed Sanctums (for pattern observation)
- Recent `ai-architect.sh --reflect` output (9 em-dashes drift detected)
- The override sequence v8.69 / v8.70 / v8.71 (the Pattern #14 realization)
- The empirical-cycle sequence v8.72 / 100yr sim / F5 (the Pattern #21 realization)

## III. The upgrade — what changes

### `meta/sanctum-protocol.md` edits

1. **AoR count corrected** to 12 instances (9 schema + 3 filesystem) with explicit enumeration.
2. **New §"The override pattern"** — names the post-v2 reality that VANTA, as principal, may decline the Architect's recommendation, and the Architect's brief stands as audit-of-record regardless. Cross-references v8.69 / v8.70 / v8.71 Sanctums as the empirical record.
3. **New §"The empirical-iteration cycle"** — names ship → simulation → finding → refinement-ship as a first-class Sanctum-pattern. v8.72 → 100yr-sim → F5 is the canonical instance.
4. **New §"Sanctum-protocol monitoring (Tribuni Plebis integration)"** — acknowledges that the Tribuni Plebis citizen (v8.71) observes Sanctum-burst as a friction signal; >3 Sanctums in one day triggers `tribunician_friction` pheromone. This is the substrate watching the protocol's own runtime; a constitutional fact.
5. **New §"Parking vs deciding"** — distinguishes `proposals/` (pre-decision drafts; PARKED state; no Sanctum required) from `sanctum/` (consultation records; DECIDED/REJECTED states; required for MEDIUM/HIGH-risk).
6. **Cross-references updated** — adds `meta/civitas.md`, `meta/denarius.md`, `polaris_swarm/`, `polaris_hydra/watchers/`, `proposals/swarm-as-analytical-layer-for-polaris-core.md`.

### `meta/architect.md` edits

1. **Brief structure generalized to arcs.** Replace "v1/v2 done-list" with arc-aware language: "active-arcs done-list rollup + arc-specific risk surface." Cite current arcs (D/E/F/G).
2. **Persona drift log populated** with the canonical reflect findings:
   - 9 em-dashes across briefs (rule reinforcement needed)
   - Override-acknowledgment language should be more consistent
   - Stale-recommendation pattern recurrence count
3. **New §"Post-v2 steady-state posture"** — names the v8.31 decline-and-surface default; the Architect's role for ambiguous expansion requests is to push back, not to silently expand.
4. **New §"The override pattern"** — mirrors the sanctum-protocol §; names the Architect's structural role when VANTA overrides.
5. **§"Brief structure" updated** to reflect: arcs not v-numbers, Mycelium + HYDRA + Civitas + Denarius lenses, watcher-mythology relocation as constitutional fact.
6. **Cross-references expanded.**

### Scripts (lightest possible touch)

`scripts/ai-sanctum.sh` — no functional changes today. The doc updates establish new framings the script doesn't need to enforce yet. (If future ships want to programmatically enforce e.g. parking-vs-deciding, that earns its own Sanctum.)

`scripts/ai-architect.sh` — possibly a one-line stale-reference fix in line 129's "v8.12 check" comment. Same restraint as above.

### Structural-invariants

Three new tests in `TestSanctumAndArchitectUpgradePostV8_73`:

1. `test_sanctum_protocol_aor_count_is_twelve` — AoR count pinned at 12 (9 schema + 3 filesystem). Future additions earn their own update.
2. `test_architect_persona_drift_log_is_populated` — the drift log section is NO LONGER empty. Specific anchor text (e.g., "em-dash") must be present.
3. `test_both_docs_reference_v8_72_mythology_relocation` — both docs must cite the v8.72 relocation Sanctum (anchors the mythology shift).

## IV. Recommendation

**Ship as v8.74 (constitutional-document maintenance).**

The edits are textually substantive but structurally conservative:
- No new G-guards (existing G1-G26 sufficient)
- No new sections in either MISSION.md or ROADMAP.md (this is constitutional-document refresh, not new arc)
- No changes to ai-sanctum.sh or ai-architect.sh behavior
- 3 new structural-invariants (174 → 177)

The risk is in NOT shipping this: the constitutional docs become increasingly disconnected from empirical practice, and fresh agents in 2027 read pre-Arc-E framings as the canonical state. The maintenance pass is overdue.

## V. Alternatives considered

1. **Wait until end-of-month batch refresh.** Rejected — VANTA asked now, and the drift is real now; deferring is just future debt.
2. **Full rewrite of both docs.** Rejected — the structural insights (Sanctum-as-form; Architect-as-chief-of-staff) are sound. Editorial refresh + targeted upgrades are the surgical move; full rewrite is over-engineering.
3. **Script-level changes** (ai-sanctum.sh / ai-architect.sh behavioral updates). Rejected today — the doc updates establish new framings; if/when we need to enforce them programmatically, that earns its own Sanctum.
4. **Constitutional Sanctum (HIGH-risk; touches the four cognitive-substrate principles).** Rejected — the four principles (Sanctum, AoR, risk classes, CM) are not being amended. The protocol-doc and persona-doc are the IMPLEMENTATION of the Sanctum principle; per v8.30 substitutability, they can be refreshed without amending the principle itself.

## VI. Decision

**Ship as v8.74 — constitutional-document maintenance for sanctum-protocol.md + architect.md.**

VANTA in-chat 2026-05-13. Architect's editorial-refresh-plus-targeted-upgrade scope authorized; full rewrite rejected per §V.

## VII. Outcome

v8.74 shipped. Both constitutional documents refreshed.

**`meta/sanctum-protocol.md`:**
- AoR count corrected: 10 → 12 instances (9 schema + 3 filesystem
  enumerated by name)
- 4 new sections added: override pattern, empirical-iteration cycle,
  Tribuni Plebis integration, parking-vs-deciding
- Cross-references extended with Civitas / Denarius / Mycelium /
  HYDRA / proposals/

**`meta/architect.md`:**
- Identity refreshed (Mycelium + HYDRA + Civitas + Denarius surfaces)
- v8.31 decline-and-surface posture named explicitly
- Brief structure generalized from v1/v2 to all-arcs (D/E/F/G)
- 2 new sections: override pattern + empirical-iteration cycle
- **Persona drift log POPULATED** (3 dated entries; the loop's
  closure mechanism is now visibly closing)
- Cross-references extended

**Structural-invariants:** 3 new tests in
`TestSanctumAndArchitectUpgradePostV8_73` (174 → 177 total). Two
test design bugs caught + fixed mid-ship (markdown line wrapping +
missing direct Sanctum reference). Self-calibration pattern 12th
instance.

**Scripts unchanged.** ai-sanctum.sh + ai-architect.sh behavioral
shape preserved; the doc updates establish new framings the scripts
don't need to enforce yet. If/when programmatic enforcement of
parking-vs-deciding or override-acknowledgment-language becomes
desirable, those earn their own Sanctums.

**No constitutional principles amended.** The four cognitive-substrate
principles (Sanctum, AoR, risk classes, CM) are untouched. The
protocol-doc and persona-doc are the IMPLEMENTATION of those
principles; per v8.30 substitutability, they can be refreshed
without amending the principles themselves.

**See:** CHANGELOG ## v8.74 · journal/2026-05-13.md
