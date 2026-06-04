# docs/story/ — narrative + principles

The story of how Polaris came to look the way it does, and the
principles that drive its design. Read this when you want to know
**why**, not **what** or **how**.

---

## What's here

| Doc | What it covers |
|---|---|
| [`STORY.md`](STORY.md) | The arc-by-arc narrative: how Polaris grew from the v1 origin to the v2 mission, through production hardening, to the present product plus flat check layer |
| [`PRINCIPLES.md`](PRINCIPLES.md) | The architectural principles beneath the constraints (audit-of-record discipline, constitutional decision-making, substrate-vs-lens, etc.) |

---

## Reading order

**Skim first:** [STORY.md](STORY.md) — chronological narrative of
how Polaris grew.

**Deep-read:** [PRINCIPLES.md](PRINCIPLES.md) — the design
philosophy + why each principle exists.

**Cross-references:**
- For the formal constitution → [`../../MISSION.md`](../../MISSION.md)
- For technical reference → [`../reference/`](../reference/)
- For operator runbooks → [`../operator/`](../operator/)
- For session-by-session decisions → [`../../journal/`](../../journal/)
- For strategic decision records → [`../../sanctum/`](../../sanctum/)

---

## Why this directory exists

A reference implementation isn't just code — it's the *story* of
choices made and not made. The MISSION names the **what**;
PRINCIPLES names the **why**; STORY names the **how it became**.
A reader who only reads `MISSION.md` knows the destination; a
reader who reads STORY + PRINCIPLES knows the path + the ground
that makes the path the right one.

---

## What this directory is NOT

- Not the formal constitution (`MISSION.md` is)
- Not technical reference (that's in `../reference/`)
- Not the journal (that's in `../../journal/` — moment-by-moment)
- Not the academic write-up (that's in `../paper/`)

`docs/story/` is **how an outside reader makes sense of Polaris's
shape** — written for the curious developer, the architecture
reviewer, the future-VANTA-orienting-themselves-after-three-months-
away.
