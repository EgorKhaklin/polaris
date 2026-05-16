# Sanctum: first-publish-readiness-declaration

**Date:** 2026-05-12
**Petitioner:** agent (Claude, Opus 4.7)
**Principal:** VANTA
**Trigger:** External event — first external publication of Polaris.
Crosses the steady-state boundary established by Sanctum
`2026-05-12-post-v2-steady-state-declaration` (publication is the
Arc-B trigger condition explicitly named there). VANTA-authorized.
**Risk class:** MEDIUM
**Status:** CLOSED
**Architect brief ID:** arch-2026-05-12-002 (publish-readiness brief,
in-chat 2026-05-12)

---

## I. The Matter

Whether Polaris is ready for its first external publication, given the
v8.32–v8.35 maintenance + cleanup + license-attachment pass.

## II. Preparation

### Discovery + cleanup (this turn)

Repo-wide scan + cleanup executed:

- **Build artifacts:** `polaris_zk/target/` (328 MB), `polaris_web/
  __pycache__/` (680 KB), 5 `.DS_Store` files — all removed. Repo
  size: 335 MB → 6.3 MB.
- **`.gitignore`:** absent before this pass. Created with macOS /
  Python / Rust / Node / IDE / runtime-state coverage.
- **`LICENSE`:** absent. **Created as Apache License 2.0** per
  Architect brief recommendation + VANTA's "yes Apache" decision.
- **`NOTICE`:** absent. Created with author attribution +
  component-level notices for Plonky2 / D3 / TopoJSON / Flask
  dependencies + the PDF report inheritance clause.
- **README:** 292 lines, 8 sections. Gained a `## License` section
  citing Apache 2.0 + LICENSE + NOTICE + patent-grant + attribution
  requirement. The legacy "License + attribution" section split into
  "License" and "Attribution + context".
- **Hardcoded secrets:** 0 in source.
- **Personal info / email / phone leaks:** 0 in source.
- **Demo credentials:** disclosed explicitly in README + SEED_DATA +
  launcher. SEED_DATA notes "production deployments must rotate."
- **Debug code:** 0 `console.log` / `print('DEBUG')` / `breakpoint()`
  in production source.
- **TODO/FIXME/XXX:** 2 occurrences, both inside `ai-*` script
  comments describing what those scripts check FOR (not actual debt).

### UI polish (this turn)

Three small fixes per VANTA request, browser-verified end-to-end:

1. **Quick Actions** block removed from dashboard (duplicate of
   USE CASES nav).
2. **SUBSTRATE ↔ USE CASES dropdowns** made mutually exclusive via
   new `polaris_web/static/nav-dropdown.js` (CSP-compliant external
   script). Opening one closes the other; click-outside closes all.
3. **Footer** pinned to viewport bottom via flex-column body layout.
   Replaces the legacy `min-height: calc(100vh - 200px)` magic-number
   on `.content` that floated the footer slightly off-bottom on
   short-content pages.

### Standard audit layers (still green)

| Layer | Reading |
|---|---|
| Cognitive scripts | 27/27 clean |
| Test suite | 365 active Python (incl. 10 Hypothesis property tests) + 56 structural invariants + 78 SQL self-tests + 3 V7 hardening tests |
| Constraints | C1–C10 all green; CM healthy |
| Mission | v1 12 ✅ + 3 ✗ retired · v2 12 ✅ · post-v2 steady-state resolved (v8.31) |
| Sanctum | 12 sessions indexed, no stale-OPEN, no drift; this Sanctum will be the 13th |
| Cross-refs | `ai-link-check` 60/60 resolved |
| Live application | 11/11 pages serve 200; R6 anti-revealing verified |
| Security | CSP `script-src 'self'`, no `'unsafe-inline'`; CSRF; rate-limiter; role-gating |
| Performance | Atlas APIs < 50 ms; health < 60 ms |

### Blast radius if approved

This Sanctum *records* the readiness determination. The act of
publishing (e.g., `git init && git push` to a public remote) is a
follow-up the agent will **not** initiate without VANTA's explicit
post-Sanctum command. Pre-publication state has not been altered
beyond the four file additions (LICENSE, NOTICE, .gitignore,
nav-dropdown.js) and the listed UI polish.

## III. Alternatives considered

### A. Defer publication

Ship more polish first (additional reviewer feedback, larger test
corpus, formal external security audit, versioned release pipeline).

- **For:** Lower risk of finding a publish-time defect under load.
- **Against:** This is a portfolio piece, not a production service.
  The audit-layer pass is comprehensive (12 layers green). Indefinite
  polish is Pattern #15 (Workaround); the steady-state contract
  forbids it.

### B. Publish without LICENSE

Push the code now, add LICENSE later.

- **For:** Removes a step from the publish path.
- **Against:** No-LICENSE = all-rights-reserved by default. Anyone
  reading the repo would assume they cannot use the code. The audit
  found this gap explicitly; fixing it before publish costs one file.

### C. Publish with Apache 2.0 attached *(recommended)*

The four-file addition (LICENSE, NOTICE, .gitignore, nav-dropdown.js)
plus three UI polish fixes; everything else green. Polaris is in the
state the Architect declared publish-ready conditional on LICENSE.

- **For:** All publish-readiness preconditions satisfied. Apache 2.0
  meets the Architect's analysis (patent grant + attribution +
  no copyleft + industry-standard). LICENSE + NOTICE preserve
  provenance, matching Polaris's own audit-of-record discipline.
- **Against:** Publication is irrevocable in practice (the internet
  remembers). Any defect found post-publish must be fixed in-place.
  Mitigation: every audit layer pre-publish is green, and the
  steady-state contract handles post-publish reactions through the
  external-trigger mechanism.

### D. Publish with a different license

MIT, CC BY-SA, GPL, etc. The Architect's analysis (in-chat brief
`arch-2026-05-12-002`) ranks Apache 2.0 first; alternatives all have
tradeoffs that Apache covers.

- **For:** VANTA's prerogative.
- **Against:** VANTA already chose Apache 2.0. This option only fires
  if VANTA changes their mind.

## IV. Recommendation

**Option C — publish with Apache 2.0 attached.**

Concrete execution if §VI approves:

1. The agent records §VII outcome and ships **v8.35** in CHANGELOG,
   CLAUDE.md state map, journal.
2. The agent emits an end-of-session report naming what was
   accomplished and what readiness state was reached.
3. **The act of publishing (`git init`, remote push, etc.) is
   VANTA's**, not the agent's. The Sanctum records readiness; it
   does not initiate the push. The agent will assist if VANTA asks
   ("now push to github.com/vanta/polaris"), but only after explicit
   instruction.

This separation preserves the principle from MISSION's "What Polaris
IS NOT" §6: the agent does not initiate user-visible external actions
(publication, broadcast, deployment) without explicit user direction.
The Sanctum closes the readiness assessment; the publication itself
is a separate, operator-driven step.

## V. What's needed from VANTA

One of:

1. **"yes proceed"** / **"yes C"** — approve publish-readiness
   declaration; ship v8.35 with this Sanctum recording the
   determination. After §VI, VANTA executes the actual publication
   step at a time of their choosing.
2. **"yes proceed and push to <remote>"** — approve readiness AND
   authorize the agent to perform `git init` + first push. The agent
   will then ask which remote URL and which initial branch.
3. **"yes with edits"** — approve readiness with a specific change
   first (e.g., "add a CONTRIBUTING.md before publish", "drop the PDF
   report from the repo", etc.).
4. **"hold"** — defer publication; surface remaining concerns.

## VI. Decision

Option C.

## VII. Outcome

Shipped v8.35 (first publish-readiness pass). LICENSE (Apache 2.0, Copyright 2026 Egor Khaklin) + NOTICE + .gitignore + nav-dropdown.js added. README gained ## License section. UI polish: Quick Actions removed, dropdowns mutually exclusive, footer pinned via flex-column layout. Build artifacts purged (335MB → 6.3MB). All 12 audit layers green. Per §IV, agent does NOT initiate the actual git push; that step is VANTA's. Sanctum integrity: 13 sessions, no drift.

**See:** [CHANGELOG `## v8.35`](../CHANGELOG.md) · [`journal/2026-05-12.md`](../journal/2026-05-12.md). Cross-ref added v8.61 per Architect-reflection finding.
