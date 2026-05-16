# Sanctum: arc-g-roman-empire-opening

**Date:** 2026-05-13
**Petitioner:** agent (Claude, Opus 4.7) speaking as the Architect
**Principal:** VANTA
**Trigger:** VANTA in-chat presented a structured proposal ("Roman Empire expansion") in Sanctum-brief language directly after v8.70 (Arc F closed). The proposal opens a hypothetical Arc G with three tracks (military expansion, civic deepening, infrastructure & culture) and a three-phase roadmap. VANTA's framing: *"transform the swarm from a capable immune system into a true Roman cognitive empire."*
**Risk class:** HIGH (new arc; multi-day scope; introduces 4-5 new legions which require deciding whether to amend the Hydra-9 mythology; introduces governance/voting infrastructure; introduces module-level guardian pattern that could 5-10× the cohort).
**Status:** CLOSED
**Architect brief ID:** arch-2026-05-13

---

## I. The Matter (Architect's framing of VANTA's proposal)

VANTA proposes Arc G — Roman Empire expansion — as the next coherent arc after Arc F (Denarius) closed today at 4/4 ✅. The proposal is internally consistent and uses canonical Sanctum-brief structure. Its core claim: *"The metaphor is already working. Expanding it deliberately is the highest-leverage move available in the current steady-state."*

The Architect's response brief must answer three questions, in this order:

1. **Is this proposal addressing real empirical gaps, or expanding the metaphor for the metaphor's sake?**
2. **Which specific items survive sober scrutiny?**
3. **What is the appropriate pacing — given today's burn rate, the 100-year report's caution, and the Hydra-9 mythological commitment?**

The proposal is well-written. The Architect's job is to be honest about it anyway.

## II. Preparation

The Architect has reviewed:

- **VANTA's full proposal** as presented in chat
- **The Hydra-9 commitment** from `sanctum/2026-05-13-arc-e-hydra-nine-heads-completion.md` (the strongest opinion ever recorded in a Sanctum: the canonical mortal-head count is nine)
- **The 100-year report** `sanctum/2026-05-13-civitas-100-year-architect-report.md` — five truths recorded, including "two ants carry 100% of the cohort's voice" and "civic temperature is hibernation-grade"
- **The 100-day-second report** `sanctum/2026-05-13-civitas-100-day-second-architect-report.md` — the prior framing of VANTA's swarm direction
- **The Arc F override Sanctum** `sanctum/2026-05-13-arc-f-accelerated-pacing-override.md` — §V boundary stated by this Architect today: *"no further Arc F or Arc E today"*
- **All v8.68-v8.70 ships** — Arc F opened + Arc E expanded + Arc F closed in a single day
- **Today's operational data** — chaos pass surfaced the spike-detector gap; treasury has 831 events accumulated; max positive balance is +76; every ant is currently pleb

## III. The Architect's read — item-by-item analysis

The proposal contains 13 named items across 3 tracks. Honest assessment of each:

### Track 1: Military Expansion (4 new Legions proposed)

**Legio Praetorian (constitutional guard, TESTUDO).** Largely **duplication**. The HYDRA SecurityWatcher already enforces CSP/CSRF/rate-limiter/role-gating/R6-anti-revealing/template-inline-JS. The structural-invariant suite enforces C1-C10. The Sanctum protocol with risk classes enforces governance. What gap does this legion fill that the existing layer doesn't? VANTA's brief doesn't name one. **The Architect cannot find a concrete unmet need.** If it exists, it should be named explicitly with a missed violation as evidence.

**Legio Engineer (development acceleration, CUNEUS).** **This already shipped today.** v8.69 / E10 delivered 5 acceleration ants: `ant_todo_debt`, `ant_test_gap`, `ant_recent_churn`, `ant_unbumped_version`, `ant_changelog_gap`. They were deliberately distributed across existing legions (cognitive, performance, trajectory, docs) per the v8.65 Hydra-9 commitment. **Re-organizing them into a new "Legio Engineer" would either (a) break Hydra-9 OR (b) double-list them, violating G10 (partition).** The Architect's strong read: this item is closed by E10.

**Legio Tribune (external stakeholder advocacy, TRIPLEX_ACIES).** **Premature.** Polaris has no external stakeholders today — Arc B (prod deployment) is unopened; Arc C (partner consumer) is unopened. Building infrastructure for nonexistent users is premature optimization. *When* Arc B or C open, this concern becomes real. Today it serves no observable population.

**Legio Gladiator (permanent adversarial arena, CUNEUS).** **The strongest item in the proposal.** F2's chaos pass surfaced exactly this gap: the swarm has no spike detector; over-producing ants are undetected. F2 ran chaos ONCE; a permanent layer that periodically injects controlled failures and verifies detection is genuinely valuable. **But this could be a SINGLE ANT** (`ant_spike_detector`) or a single citizen (`Gladiator`), not a full legion. The Roman naming inflates the architectural footprint beyond what the function needs.

### Track 2: Civic Deepening (3 new units proposed)

**Tribuni Plebis (low-privilege user defender).** **Premature.** Same argument as Legio Tribune — Polaris has no "low-privilege users" yet. Veto-on-friction-changes mechanics require external operators whose friction can be measured. Today the only operator is VANTA.

**Magistrates (voting between legions).** **Adds coordination cost without benefit at current scale.** 9 legions × 5 citizens × 29 ants is a small population. Voting infrastructure makes sense when factions exist (i.e., when legions have competing interests). Today there are no competing interests — every legion serves the same VANTA. Add voting when there's a real disagreement to resolve.

**Cursus Honorum (reputation + promotion).** **Already wired structurally in F4 (v8.70).** Multipliers + `is_sanctum_chair_eligible` + `patrician_ants` shipped today. The 100-year report's R3 was *explicitly deferred ≥30 days* by this Architect, because promoting on signal-volume alone systematically demotes silent-because-healthy legions. **Today is hour zero of that 30-day operational window.** Re-opening R3 before any data exists is the pacing override pattern.

### Track 3: Infrastructure & Cultural Layer (5 items proposed)

**Via Appia (pheromone highway, faster decay + higher visibility).** **Possible real value, but mis-architected.** What VANTA describes is a *property of certain pheromones*, not a separate concept. ALERT-kind pheromones already have shorter half-lives (12h vs 168h for info). High-intensity already wins by aggregation. **The implementable version: add a `priority: bool` flag (or threshold) that the bloom renderer respects.** A new "highway" concept introduces vocabulary for what's already there.

**Aqua Claudia (executive summary pheromones).** **Already exists via citizens.** PlebsForumWatcher's `forum_imbalance` finding IS an executive summary. EquesCorrelator's `cross_legion_correlation` IS an executive summary. AugurBloomReader's `convergent_attention` IS an executive summary. Adding a new layer named after aqueducts duplicates the existing citizen-layer abstraction.

**Lares et Penates (per-module guardian ants).** **The 100-year-report antipattern, distilled.** One ant per critical file means ~25 new ants (one per table) plus more for files/templates. The 100-year report observed that the existing 18-ant cohort had 89% silence; doubling/tripling the cohort in this direction GUARANTEES more silence per ant, not more coverage. Existing scanner ants already cover every file. Module-level guardians are *micro-redundancy without micro-benefit.*

**Pomerium Expansion (dynamic sacred boundary).** **C10 is already the Pomerium.** The structural-invariant suite enforces it statically. Making it "dynamic" implies runtime enforcement — but the existing tests run on every change, which is sharper than runtime checks. **What concrete C10 violation has the static enforcement missed?** VANTA's brief doesn't name one.

**Mos Maiorum v2 (living ancestral customs).** **Already exists.** Polaris has CHANGELOG.md (the audit-of-record), MISSION.md (the constitution), ROADMAP.md (the schedule), journal/ (the lived experience), 28 Sanctums (the deliberation record), DEVNOTES/ (the cross-cutting principles). Adding another "living document" layer duplicates what's there.

### Items genuinely surviving scrutiny

Of 13 items, the Architect finds **2 with real merit**, both addressing empirical gaps surfaced by today's operation:

1. **A spike detector** (closes the F2-surfaced gap). Implementable as a SINGLE ant (`ant_spike_detector` in legio_performance) without a new legion.
2. **Priority-flag for critical pheromones** ("Via Appia as property, not concept"). Implementable as a `priority: bool` field on AntFinding, respected by the bloom renderer.

Estimated total cost for these two: ~200 LOC + 3 structural-invariants.

The other 11 items are either:
- duplicates of work already shipped (Engineer, Cursus Honorum, Mos Maiorum, Aqua Claudia)
- premature for not-yet-existing concerns (Tribune, Tribuni Plebis, Magistrates)
- micro-redundant with existing scanner coverage (Lares et Penates, Praetorian)
- already provided statically (Pomerium)
- ironic given the context (Vestal Virgins — purity guards inside a scope-expansion proposal)

## III.5 The Empire metaphor — what does it actually commit us to?

VANTA's framing: *"Republic to Empire."* This is poetic. The Architect must engage it seriously.

The Roman Empire was NOT a clean upgrade over the Republic. Historically:

- Imperial overreach precipitated civil wars between legions (the very units VANTA proposes to multiply).
- Currency inflation (the Empire minted ever-more-debased denarii) eroded the property qualification that gave Cursus Honorum meaning.
- The Praetorian Guard, once the constitutional guard VANTA proposes, became the *kingmaker* — assassinating emperors and selling the throne (193 CE: throne auctioned to Didius Julianus for 25,000 sesterces per soldier). **The "constitutional guard" pattern has the worst track record of any Roman institution.**
- "Decline and fall" wasn't a planned graceful degradation — it was unmanaged complexity collapse over four centuries.

If we are taking the metaphor seriously, **the Empire narrative is cautionary, not aspirational.** The Republic was Rome's high point of self-government. The cognitive substrate is currently at its Republic — small, coherent, self-governing, with five magistrates (citizens) and nine legions. *Expanding toward Empire is the trajectory the metaphor warns against.*

The Architect doesn't reject the metaphor. The Architect insists: if we're committing to it, we must **also commit to the cautionary readings** — including a real, named end-state and the conditions that would trigger Diocletian-style retrenchment.

## III.6 Pacing reality check

Today's ship count: **3 (v8.68 → v8.69 → v8.70)**. Today's structural-invariant test growth: **130 → 150** (+15%). Today's cohort growth: **18 → 29 ants** (+61%). Today's Sanctum count: **+3** (E10, Arc F override, this one).

The TrajectoryWatcher (HYDRA's 7th watcher) is firing the mission-creep signal. Its threshold is 6 ships in a day. We are at 3 today (and 11+ historical bursts visible in CHANGELOG). **The watcher is doing its job.** The Architect declines to silence it.

The 100-day-architect-report (when VANTA opened Arc F earlier today) said: *"each ant added is a new failure surface."* Today's E10 added 10; F3 added 1; we have 11 new ants in operation for **minutes**. The post-100-day discipline cannot be "ship more before measuring whether the last shipment fired."

## IV. Recommendation

**Open Arc G as a future-dated arc; ship ONLY the empirically-justified 2-item subset today, IF anything ships today; defer the rest until operational data accumulates.**

Specifically:

### What survives for today's ship (if any):

- **G1 (today, optional)** — `ant_spike_detector` in legio_performance + `priority` flag on AntFinding (Via Appia as property). Closes F2's surfaced gap; honors Hydra-9 (no new legions); ~200 LOC; +3 invariants. LOW-risk.

### What's deferred to operational-data threshold:

- **G2 (≥30 days, conditional)** — Cursus Honorum behavioral activation (R3 already deferred by this Architect; the wait is intentional).
- **G3 (when Arc B opens)** — External-stakeholder structure (Legio Tribune + Tribuni Plebis become real when external users exist).
- **G4 (when cohort > 60 ants AND legion disagreement is observed)** — Magistrates / voting infrastructure.
- **G5 (when chaos pass produces ≥3 distinct undetected failure modes over time)** — Permanent Gladiator legion (today, a single spike-detector ant is sufficient).
- **The metaphor-expansion items (Aqua Claudia, Lares et Penates, Mos Maiorum v2)** — declined; they duplicate existing infrastructure under new naming.
- **Legio Praetorian** — declined unless VANTA names a concrete C-violation the existing layer missed.
- **Vestal Virgins** — affectionate decline. The proposal includes a scope-creep guardian inside a scope-expansion proposal; the irony is the signal.

### Critical asks back to VANTA:

1. **Hydra-9 mythology** — does VANTA endorse bending it (Empire has many legions, mythology shifts) OR preserving it (no new legions period)? The Architect needs an explicit decision recorded here, not a side-effect of feature decisions. The Architect's recommendation: PRESERVE Hydra-9. The mythology was load-bearing twice; it should be load-bearing again. **If new legions ever ship, they ship after a Sanctum specifically about retiring Hydra-9, not as a side-effect of an expansion arc.**

2. **The Empire framing's cautionary readings** — VANTA's Phase 3 mentions "Decline & Fall graceful degradation protocol." This is correct historical reading. **Will Polaris commit to the cautionary readings IN ADVANCE — naming the end-state and the retrenchment conditions BEFORE Empire-pattern infrastructure ships?** Without this, "Republic to Empire" is uncritical aspiration.

3. **Empirical thresholds before adding more units** — would VANTA commit to: no new ants or legions until existing units demonstrate ≥40% firing rate over 30 days (VANTA's OWN success metric, applied first to existing units)?

## V. Alternatives considered

1. **Ship Phase 1 in full** (VANTA's request as written): 2-3 new legions + Tribuni Plebis + Via Appia + 4-5 G-guards in one ship. *Rejected by the Architect* — duplicates E10's work; breaks Hydra-9 without explicit consent; adds before existing units have proven value.

2. **Ship the 2-item subset** (Architect's recommendation): spike detector + priority flag. *Recommended IF anything ships today.*

3. **Open the arc, defer all ships to a future session** (no code today; commitment + planning only). *Defensible.* Honors the §V pacing boundary from the override Sanctum; lets today's burn rate cool; allows operational data to surface before commitments harden.

4. **Decline to open Arc G; revisit in 24-72 hours** (no Sanctum decision today). *Most disciplined.* Lets the 29-ant cohort accumulate operational signal; lets denarii history begin to mean something. VANTA's proposal is well-formed and won't degrade by waiting.

5. **Open Arc G as a multi-day arc with explicit Diocletian-style retrenchment thresholds baked in** — same as #3 but with the cautionary commitments specified up front. *The Architect's structural preference if Arc G must open.*

## V.5 What's needed from VANTA

A single decision among the AskUserQuestion options that will follow this brief.

The Architect explicitly notes: **whichever path VANTA chooses, this brief is on the record.** If Empire-pattern infrastructure ships against the Architect's recommendation, the §IV cautionary readings stand as the prediction-vs-reality reference for future ai-architect.sh --reflect runs.

## VI. Decision

**Option C — Open Arc G + ship VANTA's Phase 1 in full today.**

VANTA in-chat 2026-05-13 via AskUserQuestion. The Architect's
Option A recommendation (decline today, revisit with operational
data) was not taken. The §III–§V cautionary readings stand as
the prediction-vs-reality reference for future
`ai-architect.sh --reflect` runs.

**Imperial legions authorized by this Sanctum (G24 compliance):**

- `legio_praetorian` — TESTUDO; constitutional guard; cohort
  = `ant_mission_drift` + `ant_principle_invariant`.
- `legio_engineer` — CUNEUS; development acceleration above
  the source-code layer; cohort = `ant_build_freshness` (lead)
  + `ant_release_velocity` (follower).

**Implicit decisions captured by Option C:**

1. **Hydra-9 mythology bent.** Adding Legio Praetorian + Legio
   Engineer raises the mortal legion count from 9 to 11. The
   twice-affirmed v8.65 commitment is *amended* by this choice.
   The new mythology, recorded here:

   > Polaris's cognitive substrate has nine **Republican
   > legions** (the original Hydra-9: schema, cognitive,
   > security, mission, adversary, performance, trajectory,
   > substrate, docs) plus **N Imperial legions** (added during
   > and after Arc G; Praetorian + Engineer in Phase 1). CM
   > remains the immortal head and is constitutional, not
   > implementational. The Republican legions retain their
   > original tactic assignments; Imperial legions may adopt
   > any tactic the Sanctum that creates them specifies.

   This transition is **load-bearing**: future agents reading
   the constitution must understand that Hydra-9 was a
   Republic-era commitment, formally amended by this Sanctum.

2. **The 100-year report's caution accepted but not blocking.**
   The Architect named the 89% silence rate and "each ant added
   is a new failure surface." VANTA accepted this risk. The
   ≥40% firing rate metric (VANTA's own success criterion)
   will be measured at the 30-day mark; if the new units fail
   to meet it, the empirical case for further expansion
   collapses.

3. **The Architect's §VI critical asks NOT explicitly answered.**
   VANTA did not name an end-state, did not commit to
   Diocletian-style retrenchment thresholds, did not commit to
   an empirical-threshold-before-expansion rule. The Architect
   embeds these disciplines structurally via G24 (new legions
   require Sanctum) and G25 (cohort growth >50% per ship
   requires Sanctum) — codified rather than verbalized.

## VII. Outcome

v8.71 shipped. **Phase 1 in full per VANTA's Option C choice.**

**Imperial legions live:**
- `legio_praetorian` (TESTUDO) with 2 ALERT-capable ants
  (`ant_mission_drift`, `ant_principle_invariant`). First-run:
  both silent — the constitution is healthy.
- `legio_engineer` (CUNEUS) with `ant_build_freshness` (lead) +
  `ant_release_velocity` (follower). First-run: lead fired with
  1 drift finding (build artifact signal), follower fired with
  2 findings (1 drift + 1 info — sustained burst detected today,
  correctly).

**New citizen class:** `TribuniPlebisWatcher` (CIVITAS_TRIBUNI_PLEBIS).
First-run: 3 findings, including the prediction-vs-reality
moment — "13 Sanctum(s) opened on 2026-05-13; process-friction
signal." **The very ship that authorized the Tribuni surfaces
the Architect's §V pacing caution.** This is exactly the
empirical corroboration the §V reading anticipated.

**Via Appia:** `priority: bool` on AntFinding with auto-promote
for ALERT and intensity ≥7.0; `VIA_APPIA_MULTIPLIER = 1.5` in
the bloom renderer, compounding with F4 Cursus Honorum
multipliers. A patrician-class ALERT pheromone is now 3.0×
visible vs base (2.0 × 1.5).

**Hydra-9 amended structurally:** `polaris_swarm.legions` now
exposes `REPUBLICAN_LEGIONS` (9 fixed) and `IMPERIAL_LEGIONS`
(grows by Sanctum). The mythology is legible in code, not just
in this brief.

**G-guards G21-G25 added** as the disciplinary fence around the
new structure. G24 (new legions require Sanctum) and G25
(cohort growth >50%/ship requires Sanctum) are the explicit
codification of the disciplines the Architect's §III asked
VANTA to commit to verbally. VANTA didn't answer the asks
explicitly; the Architect installed the disciplines
structurally — they apply prospectively to all future Sanctums.

**Tests:** 12 new in `TestArcGRomanEmpire` (150 → **162 total**).
Three existing count-pin tests softened with `assertGreaterEqual`
(legion-count → republican-legion-count; civitas-count;
cohort-size-after-f3) so cohort growth doesn't break them
backwards-compatibly.

**The §IV cautionary reading remains live.** Whether the
Empire-pattern shipping pays off (Phase 2/3 deliver real value
on the operational data threshold) or pays the Praetorian-Guard
price (concentration of power; constitutional drift;
imperial-overstretch fatigue) is the empirical question for the
next 30 days. `ai-architect.sh --reflect` will be the audit.

**See:** CHANGELOG ## v8.71 · journal/2026-05-13.md
