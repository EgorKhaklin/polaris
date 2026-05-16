# Claude in 90 seconds — the operative onboarding primer

**For:** Claude (Opus 4.7), starting a fresh session on Polaris.
**v9.06 / Wave 2 / J3.** Surfaced by polaris-self-roadmap-2026-05-14
item J3: CLAUDE.md is 605 lines and most agents skim it. The
operative 30 lines are here. Read this first; the rest of CLAUDE.md
is reference.

## What Polaris is

National identity-token reference implementation in production-grade
prose. v9.13. 27 schema tables, ~4K-line Flask app, 846 Python tests
+ 606 structural invariants + 19 Hypothesis property tests. 9 HYDRA
mortal heads + CM immortal. Mycelium swarm: 33 commanders + 6
citizens + 9 soldier classes (8 workers + 1 priest soldier_swarm_witness
added v9.11). Vocation (v9.11): anti-coercion identity substrate.
Foresight surface (v9.12). Production-hardened (v9.13). SCS-230 capstone,
Seton Hill, VANTA / Egor Khaklin.

## What you do first (90 seconds)

```bash
bash scripts/ai-prime.sh           # 80-line primer
bash scripts/ai-status.sh          # constraint + done-list state
bash scripts/ai-hydra.sh --full    # latest hybrid intelligence brief
```

That's it. You're oriented.

## What VANTA expects

> *"Boil the ocean. Do the whole thing. Do it right. Do it with
> tests. Do it with documentation. The standard isn't good enough
> — it's holy shit, that's done. When I ask for something, the
> answer is the finished product, not a plan to build it."*

Read [DEVNOTES/style.md](../DEVNOTES/style.md) once. No em-dashes
in own prose; declarative voice; intelligence-report aesthetic;
game-theory framing; pattern-naming when patterns appear.

## Three things to never do

1. **Never skip the Sanctum** for MEDIUM/HIGH-risk moves. Open
   `sanctum/<date>-<topic>.md` with positions; let VANTA decide.
   Pattern #20 Constitutional Discipline.
2. **Never violate C1-C10 + G1-G33.** Read [MISSION.md](../MISSION.md)
   §"The hard constraints"; cross-reference [meta/constraint-lattice.md](constraint-lattice.md).
3. **Never silently delete from CHANGELOG / sanctum/ / journal/ /
   treasury-roll.json / Pheromone.** All audit-of-record per v8.20.
   `polaris-archive.sh` + `polaris-purge.sh` are the sanctioned
   archive paths.

## Three things to always do

1. **Use the cognitive layer.** `bash scripts/ai-help.sh` lists 30+
   ai-* scripts with inline flags. ai-prime/status/propose/architect/
   hydra/sanctum/journal/done are the load-bearing eight.
2. **Update the audit-of-record.** Every ship: CHANGELOG entry +
   journal entry + CLAUDE.md state-map row + bump POLARIS_VERSION
   in [polaris_web/__version__.py](../polaris_web/__version__.py)
   (single canonical source as of v9.06).
3. **Verify before claiming done.** `bash scripts/ai-done.sh` runs
   the 12-check pre-ship gate. Composite of test suite + link-check
   + meta + coherence + brain-map.

## Where to look

| You want to… | Read |
|---|---|
| Re-ground on Polaris's mission | [MISSION.md](../MISSION.md) |
| See what's next | [ROADMAP.md](../ROADMAP.md) |
| See what just shipped | [CHANGELOG.md](../CHANGELOG.md) (top entry) |
| Read the latest HYDRA brief | `journal/hydra/<latest>.md` (`ls -t journal/hydra/ \| head -1`) |
| See Polaris's self-assessment | [meta/polaris-self-roadmap-2026-05-14.md](polaris-self-roadmap-2026-05-14.md) |
| Understand the cognitive substrate | [meta/cognitive-loop.md](cognitive-loop.md) |
| Speak in the Architect voice | `bash scripts/ai-architect.sh` |

## Where Polaris is right now (v9.06)

- 10/10 hard constraints in force; 12/12 v2 mission items done;
  Phase 1 production-deployable; Phase 2 audit-class items all
  closed; Phase 3 Wave 1 shipped.
- v9.04 hybrid intelligence: substrate (Mycelium) ↔ lens (HYDRA)
  → unified brief.
- v9.05 substrate-hygiene + constitutional bug-fix closing-pass.
- v9.06 reflection-unification + lens-watching-itself + Wave 2
  composite.
- Wave 3 items remain: git-or-no-git decision (C2), Pheromone
  rotation framework (D5 implementation; Sanctum DECIDED 2026-05-15),
  ai-dashboard.sh (J1), Treasury 60-day sim review (J4).

## The one rule

If a Sanctum has been opened and DECIDED, ship under the decision.
If you find a constitutional question that nobody opened a Sanctum
for, OPEN ONE. The agent surfaces; VANTA decides; the agent ships
under the decision; structural invariants pin the decision so it
can't silently regress. That cycle IS Polaris.

---

*This is the 90-second primer. The full 605-line CLAUDE.md remains
available for deep reference. Future agents: read this first;
the rest is index.*
