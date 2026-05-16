# meta/cadences.md — Polaris cron-tempo vocabulary

Polaris's automated operations run on multiple time scales. Pre-v9.11
each cadence was named ad hoc ("the every-6h pass," "the daily HYDRA").
This document gives the cadences a **shared operator vocabulary** —
names that map cleanly to memory and to the natural rhythms of system
observation.

The vocabulary is rooted in the seven traditional planetary tempos:
each historic civilization mapped its operational rhythms to the
seven moving celestial bodies (Saturn → Moon, slowest to fastest).
The mapping is mnemonic, not literal — using planetary names because
seven names with distinct character is faster to recall than "the
every-6-hours pass" + "the every-5-min pass" + "the daily pass."

The point is operator legibility. When an operator hears "the Saturn
pass," they immediately know it is slow + structuring (monthly
review). When they hear "Mars cycle is hot," they know alerts are
firing on the every-6h alarm-tempo. Vocabulary becomes mnemonic.

---

## The seven cadences

| Tempo | Planet | Name | Period | Character | Polaris instance |
|---|---|---|---|---|---|
| 1 | Saturn | Saturn-pass | monthly | slowest, structuring | macro-to-micro re-scan; constitutional review |
| 2 | Jupiter | Jupiter-pass | weekly | expansive, reviewing | weekly architect-reflect; backlog grooming |
| 3 | Mars | Mars-cycle | every 6h | martial, alarm-tempo | HYDRA `--full` (default); alert-surface |
| 4 | Sun | Sun-pass | daily | the heartbeat, central | daily HYDRA brief; ai-architect daily run |
| 5 | Venus | Venus-cycle | hourly | relational, balancing | hourly heartbeat checks; treasury rebalance hooks |
| 6 | Mercury | Mercury-cycle | every 5min | messenger, fast | soldier-tier observations (route_pinger, etc.) |
| 7 | Moon | Moon-cycle | every minute | closest, fastest | per-minute heartbeats; high-frequency soldiers |

The naming inherits no mystical claim — it inherits **distinct
characters**. The seven planets have distinct mythological characters
that humans memorize easily; the cron cadences inherit that
memorability without inheriting any claim about celestial influence.

---

## Operational mapping

Below: the actual Polaris artifacts that run on each cadence (when
operator-installed; many Polaris cron paths are operator-optional).

### Saturn-pass (monthly)

Used for:
- Macro-to-micro architectural re-scan (the polaris-self-roadmap
  doc series; runs ~monthly per the v9.04 / v9.08 / v9.09 cadence)
- Treasury 60-day sim review (J4)
- Constitutional review opportunity (Sanctum: should any C1-C10
  be amended? almost always: no.)

### Jupiter-pass (weekly)

Used for:
- `bash scripts/ai-architect.sh --reflect` (the persona-drift
  detection loop)
- `bash scripts/ai-anti-architect.sh --save` (the dissent brief
  archived for retrospective comparison)
- Weekly backlog grooming: ROADMAP.md review, auto-promoted
  candidate triage

### Mars-cycle (every 6 hours)

Used for:
- `bash scripts/ai-hydra.sh --full --save` (the full hybrid-intelligence
  pass; archives to journal/hydra/)
- The alarm-tempo: alerts surface here first

### Sun-pass (daily)

Used for:
- Daily ai-architect brief (run + read by operator)
- `bash scripts/ai-hydra.sh --gc` (rotate journal/hydra/; v9.09 / H)
- Pheromone rotation evaluation (when wired; v9.07 framework)
- Brain-map regeneration (`bash scripts/ai-brain-map.sh --auto`;
  v9.09 / E)

### Venus-cycle (hourly)

Used for:
- `bash scripts/ai-hydra.sh` (default lighter pass; no `--full`)
- Heartbeat health checks for the running Polaris app
- Treasury micro-rebalance hooks (when operator chooses to
  enable)

### Mercury-cycle (every 5 minutes)

Used for:
- Soldier-tier observations (the eight workers + the priest,
  per `polaris_swarm/soldiers/`)
- Route pinger: HEAD `/`, `/login`, `/demo`, `/api/health`
- Fast soldiers: process_alive, heartbeat_freshness

### Moon-cycle (every minute)

Used for:
- The Polaris app's own internal heartbeat
- Highest-frequency soldiers when operator demands sub-5-minute
  observation (rare; default is Mercury-cycle)

---

## When to use the vocabulary

Use the names when the cadence is the **important variable** in
operator communication:

- **Yes:** "the Saturn-pass surfaced a structural drift this month"
- **Yes:** "Mars-cycle is hot — three alerts in last 24h"
- **Yes:** "we're running below the cadence rule on the Sun-pass
  layer-ratio"
- **No:** "I ran the Mercury-cycle at 14:32" — just say "I ran the
  soldier pass." The cadence isn't the point; the operation is.

The vocabulary is for **rhythm-naming**, not for tagging every
operation. Naming everything would dilute the names.

---

## Adding a new cadence

If a future operational need requires a tempo not on this table
(e.g., bi-monthly, every 12h, every 30min), do NOT extend this list
arbitrarily. Either:

1. Round to the nearest existing cadence (every 12h → Mars-cycle
   ×2, communicated as "the doubled Mars-cycle")
2. Or add the cadence with explicit Sanctum justification, naming
   the operational gap that demanded a new tempo

The seven cadences have characters because there are seven of
them. Adding an eighth dilutes; eight planetary names would not
have distinct enough characters to be useful mnemonics.

---

## Cross-references

- [`scripts/`](../scripts/) — most ai-* scripts can run on any
  cadence; the operator chooses what to install in cron
- [`polaris_swarm/soldiers/`](../polaris_swarm/soldiers/) — the
  Mercury-cycle workers
- [`polaris_hydra/`](../polaris_hydra/) — the Mars-cycle alarm-tempo
  + Sun-pass daily hybrid intelligence
- [`docs/operator/`](../docs/operator/) — the operator-facing
  installation docs for any of these cron paths
