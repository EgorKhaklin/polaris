# journal/ — episodic memory

Per-day session logs. The cognitive layer's third memory tier
(after `MISSION.md` semantic memory + Sanctum decision-record).
v8.20 audit-of-record location pin: `journal/<YYYY-MM-DD>.md`.

---

## What's here

| Pattern | Purpose |
|---|---|
| `<YYYY-MM-DD>.md` | One file per active development day; flat-list of decisions + learnings + bugs |
| `<YYYY-MM-DD>-architect.md` | Daily Architect brief (`ai-architect.sh --save`); voice-of-the-day |
| `INDEX.md` | Per-arc summary across all days (added v8.26) |
| [`hydra/`](hydra/) | HYDRA hybrid intelligence brief archive (v9.04+; `<YYYY-MM-DD>-<HHMM>.md`) |

---

## How entries land here

```bash
./scripts/ai-journal.sh start "what I'm trying to do"
./scripts/ai-journal.sh decision "<the decision + WHY>"
./scripts/ai-journal.sh learning "<the learning + cross-ref>"
./scripts/ai-journal.sh bug "<the bug + the fix>"
```

Daily Architect briefs:
```bash
bash scripts/ai-architect.sh --save     # also writes journal/<DATE>-architect.md
```

HYDRA hybrid briefs:
```bash
bash scripts/ai-hydra.sh --full --save  # also writes journal/hydra/<DATE>-<HHMM>.md
```

---

## How agents read it

- **Where Polaris was yesterday:** `tail journal/$(date -v-1d +%F).md`
- **What's the operative thread today:** `bash scripts/ai-prime.sh`
  (surfaces the most recent decisions inline)
- **What did the Architect think on day X:** `cat journal/<X>-architect.md`
- **Cross-arc activity over the last week:** `cat journal/INDEX.md`

---

## Constitutional contract

- **G15 (filesystem-AoR)**: every entry stays. The journal is
  audit-of-record; entries are append-only-discipline. Old days
  are not retroactively edited (corrections land as new entries
  cross-referencing the prior).
- **C1 (audit append-only)**: enforced by convention + every
  agent's instruction to never delete.

---

## What this directory is NOT

- Not formal Sanctum decisions (those go in `sanctum/`)
- Not durable doc (those go in `DEVNOTES/`)
- Not constitutional principles (those go in `MISSION.md` /
  `meta/`)

journal/ is the **moment-by-moment narrative** — what happened,
what was decided, what was learned, what surprised us. The
strategic record + the durable docs both build on it.
