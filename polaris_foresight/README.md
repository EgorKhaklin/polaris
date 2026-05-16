# polaris_foresight/ — minimum-viable foresight surface (v9.12)

The foresight *function*, not the foresight *subsystem*. Per the
[v9.12 Sanctum](../sanctum/2026-05-15-polaris-odyssey-debate.md)
Position B (joint Architect + Anti-Architect recommendation), this
package ships the minimum surface needed to test the foresight
hypothesis. If it earns its right to expand (via the empirical-
graduation rule), a future Sanctum may extract it into a real
subsystem (the proposed "Polaris_Odyssey" name is held in reserve
pending that graduation).

---

## What this package does

`bash scripts/ai-foresight.sh` runs a `ForesightAgent` against the
local repo state and emits a 5-section markdown brief:

| § | Section | Source |
|---|---|---|
| I | What we shipped that surprised us | CHANGELOG surprise markers + Sanctum §VI divergences |
| II | What we keep almost-shipping but never quite do | Macro-rescan repeat-deferral patterns |
| III | External signals to watch | `external_categories.txt` (operator-curated; no fetches) |
| IV | Vocation-aligned gaps | Anti-coercion primitives untouched in last 30 ships |
| V | Three foresight candidates | Intersections of §I-§IV; promotable to ROADMAP as FS-XXXXXXXX |

Brief is saved to `journal/foresight/YYYY-MM-DD.md` when run with
`--save`. Candidates are auto-promoted to `ROADMAP.md` §"Foresight
candidates (v9.12+)" when run with `--promote` (idempotent; LOW +
MEDIUM only; HIGH still requires Sanctum).

---

## What this package deliberately does NOT do

Listed because the absences are constitutional, not accidental:

- **No external API/network fetches.** Per Sanctum Anti-Architect
  modification §IV.2: deterministic over local state. The
  `external_categories.txt` file is operator-curated; the agent does
  not call out to "research papers, philosophy, news" as the original
  Polaris_Odyssey proposal suggested.

- **No Mythic Agents** (or any aesthetic-completeness agent class).
  Per Sanctum §III architect's recommendation + Anti-Architect's AP8
  detection: the original "Mythic Agents (optional esoteric layer)"
  was the larping pattern. It is not in this package and will not be.

- **No Quest Generator, Simulation Engine, vector DB, message queue.**
  The original Polaris_Odyssey proposal abstracted these as named
  components before any concrete instance demanded them. Per
  Anti-Architect AP7 (premature abstraction): build the function,
  not the infrastructure-around-the-function.

- **No four-class agent hierarchy.** Per the Sanctum: one agent type
  (`ForesightAgent`), not four. If foresight earns expansion,
  additional types may be justified by surfaced demand.

- **No auto-cron installation.** Operator-installed only. The script
  may be added to crontab on Saturn-pass cadence (monthly) by the
  operator, but the package does not install itself.

- **No LLM calls (in v9.12).** The agent is fully deterministic over
  local state. LLM enrichment was deferred to a future Sanctum (only
  if the empirical-graduation threshold is met); v9.12 ships pure
  deterministic to keep the surface minimum-viable.

---

## The empirical-graduation rule + sunset clause (load-bearing)

Per Anti-Architect modification (Sanctum §IV.2), the foresight surface
must earn its right to exist via measurable acceptance.

**Rule:**

> Over 6 monthly briefs, ≥ 50% of FS-XXXXXXXX candidates promoted to
> ROADMAP.md must be ACCEPTED (graduated to a real R-id by the
> operator) — not declined, not left perpetually open.

**Sunset clause:**

> If after 6 briefs the acceptance rate is below 50%, every subsequent
> brief prefaces with a "SUNSET TRIGGERED" warning recommending that
> the operator open a removal Sanctum or document why the threshold
> is being deferred.

The script does not auto-remove. The operator decides. But the
dishonesty of maintaining unused infrastructure becomes visible.

**Tracker file:** `polaris_foresight/_acceptance_log.json` —
schema documented in the file itself.

---

## Vocation alignment is structural, not advisory

Per Anti-Architect modification (Sanctum §IV.2) + v9.11 vocation
Sanctum:

- Every brief's §IV must surface anti-coercion gaps (or explicitly
  note that no gaps were detected). The `Brief` dataclass enforces
  §IV's presence at construction time.
- Every promoted FS-XXXXXXXX candidate must carry a `vocation_alignment`
  field. The `promote_foresight_candidates` function refuses to promote
  candidates with empty vocation alignment (counted as
  `skipped_no_vocation` in the result).
- The Anti-Architect's AP5 detection (vocation drift) reads the
  `vocation_alignment` field of promoted FS-XXXXXXXX items as one of
  its signals. Drift surfaces via the v9.11 dissent brief.

---

## File layout

```
polaris_foresight/
├── __init__.py              # package init; exports
├── README.md                # this file
├── brief.py                 # Brief dataclass + 5-section render
├── foresight_agent.py       # ForesightAgent (single type)
├── promotion.py             # FS-XXXXXXXX auto-promotion to ROADMAP
├── external_categories.txt  # operator-curated category list (§III)
└── _acceptance_log.json     # empirical-graduation tracker
```

Operator entry: [`scripts/ai-foresight.sh`](../scripts/ai-foresight.sh).

---

## Operator workflow

1. **Monthly (Saturn-pass cadence per `meta/cadences.md`):** run
   `bash scripts/ai-foresight.sh --save --promote`. Reads the brief
   on stdout; saves to `journal/foresight/YYYY-MM-DD.md`; promotes
   top 3 §V candidates to ROADMAP.md.

2. **Triage candidates** in `ROADMAP.md` §"Foresight candidates
   (v9.12+)":
   - **Accept** by promoting to a real R-id in the prioritized backlog
     below + marking the candidate's `_acceptance_log.json` entry as
     `"status": "accepted"` (TBD: helper script for this).
   - **Decline** by striking through the line and adding
     `<!-- declined: reason -->` (decline-marker convention from
     v9.11 AP-XXXXXXXX system).

3. **Quarterly (every ~3 briefs):** review the acceptance log. If
   acceptance is trending below 50%, the agent will start warning;
   operator decides whether to tune the agent or remove the surface.

4. **After 6 briefs:** sunset evaluation. Pass: surface earns its
   right to expand (open Sanctum). Fail: surface earns its removal
   (open Sanctum).

---

## Cross-references

- [`sanctum/2026-05-15-polaris-odyssey-debate.md`](../sanctum/2026-05-15-polaris-odyssey-debate.md) —
  the constitutional decision creating this package
- [`MISSION.md` §"Vocation"](../MISSION.md) — anti-coercion vocation;
  the seven primitives §IV scans for gaps in
- [`meta/anti-architect.md`](../meta/anti-architect.md) — the
  persona whose AP5/AP7/AP8 detections shaped Position B
- [`meta/cadences.md`](../meta/cadences.md) — Saturn-pass cadence
  (monthly) is the recommended operator cadence
- [`polaris_hydra/action_promotion.py`](../polaris_hydra/action_promotion.py) —
  the v9.11 AP-XXXXXXXX system that this FS-XXXXXXXX system parallels
- [`polaris_sql/14_foresight_helpers.sql`](../polaris_sql/14_foresight_helpers.sql) —
  the Layer-1 bundle: SQL functions the foresight agent references
  for schema-level signals
