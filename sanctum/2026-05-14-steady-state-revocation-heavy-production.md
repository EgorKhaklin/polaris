# Sanctum: steady-state-revocation-heavy-production

**Date:** 2026-05-14
**Petitioner:** agent (Claude, Opus 4.7) speaking as the Architect
**Principal:** VANTA
**Trigger:** VANTA in-chat after v8.76: *"i would like to get out of steady state and begin heavy production and set the architect on scanning the macro of the project to find things to improve, add and work on because polaris and the sub projects are currently far from being complete."* Plus the standing-instructions block reasserted with force: *"the marginal cost of completeness is near zero with AI. Do the whole thing. Do it right. Do it with tests. Do it with documentation. Do it so well that I am genuinely impressed... Boil the ocean."*
**Risk class:** HIGH (revokes the v8.31 steady-state contract; shifts the agent's default posture from decline-and-surface to active-production; opens the door to multi-arc parallel work; recalibrates the override pattern from exception to operating mode for the foreseeable future).
**Status:** DECIDED
**Architect brief ID:** arch-2026-05-14-revocation

---

## I. The Matter

The post-v2 steady-state contract was established 2026-05-12 in
`sanctum/2026-05-12-post-v2-steady-state-declaration.md`. Per
that contract, the agent's default posture for ambiguous
expansion requests was **decline-and-surface**: explain why a
request crosses the steady-state boundary, name the trigger that
would be needed (Arc B prod-deploy / Arc C partner consumer /
novel arc with documented external cause), and wait for VANTA to
authorize.

The contract was explicitly **operator-revocable** ("VANTA may
name a trigger or open a new arc at any time. The constraint is
on the agent, not on VANTA").

VANTA's directive on 2026-05-14 revokes the steady-state contract
and replaces it with **heavy-production posture**. The trigger
named ("polaris and the sub projects are currently far from being
complete") is the third v8.31 trigger condition (*novel arc with
documented external cause*) firing.

## II. The new operating mode (heavy-production)

**Default posture:** Active production. The agent ships things.
The architect scans macro for what's incomplete and prioritizes.
The standing-instructions block from `DEVNOTES/style.md` applies
with FULL force, restated by VANTA in this directive:

- *"The marginal cost of completeness is near zero with AI."*
- *"Do the whole thing. Do it right. Do it with tests. Do it with documentation."*
- *"Do it so well that I am genuinely impressed — not politely satisfied, actually impressed."*
- *"Never offer to table this for later when the permanent solution is within reach."*
- *"Never leave a dangling thread when tying it off takes five more minutes."*
- *"Never present a workaround when the real fix exists."*
- *"The standard isn't good enough — it's holy shit, that's done."*
- *"Search before building. Test before shipping. Ship the complete thing."*
- *"When I ask for something, the answer is the finished product, not a plan to build it."*
- *"Time is not an excuse. Fatigue is not an excuse. Complexity is not an excuse."*
- *"Boil the ocean."*

These are the operating directives now. They REPLACE the
steady-state decline-and-surface default for the duration of
heavy-production mode.

## III. What changes (and what does NOT)

### What changes

1. **Default response shape.** Was: surface trade-offs + name triggers + wait. Now: ship the complete thing.
2. **Architect's posture.** Was: drift-detector + cautionary-reader. Now: macro-finder + production-prioritizer.
3. **Override pattern frequency.** Was: exception (3 in 24h was notable). Now: not applicable; VANTA's directives set scope, agent ships.
4. **Pacing.** Was: ≥7 days between major arcs; multi-day pacing for new substrate. Now: continuous; the bottleneck is what's worth shipping, not how often.
5. **TrajectoryWatcher mission-creep signal.** Will continue firing. The signal is no longer a discipline check; it's a workload telemetry. The Architect notes it but doesn't slow on it.
6. **Tribuni Plebis Sanctum-burst signal.** Will fire heavily. Same reframing.

### What does NOT change

1. **C1-C10** — preserved verbatim. The hard constraints don't move.
2. **The four cognitive-substrate principles** (Sanctum, AoR, risk classes, CM) — preserved verbatim.
3. **G-guards G1-G26** — all in force.
4. **Audit-of-record discipline** (v8.20) — every ship still gets a CHANGELOG entry; every Sanctum-class decision still gets a Sanctum.
5. **Test discipline** — every ship still has tests; the standard rises (per "Do it with tests").
6. **Sanctum protocol** — still required for MEDIUM/HIGH-risk decisions; the protocol is faster (DECIDED-on-arrival when the directive is unambiguous), not skipped.
7. **The override pattern audit-of-record** — still recorded in §IX of relevant Sanctums; no override is invisible.
8. **CM** — still the immortal head; the meta-constraint still self-monitors; ai-meta still runs.

The constitutional core is unchanged. The operating posture is.

## IV. The Architect's macro scan (separate deliverable)

This Sanctum authorizes the posture shift; it does NOT itself
contain the macro scan. The macro scan lives in the chat
response immediately following this Sanctum's creation. It will
identify:

- What's incomplete in each subsystem (Polaris Core, Web, SQL,
  ZK, HYDRA, Mycelium, Civitas, Denarius, cognitive layer,
  documentation, operational tooling)
- Production-readiness gaps (TLS, secrets, deployment automation,
  monitoring, error pages, accessibility, performance under
  load)
- Test-coverage gaps (the long-standing 41-CHECK-vs-16-test ref
  signal, plus others)
- Documentation gaps (per-subsystem coverage)
- Backlog items that have been sitting (R8-3 OIDC, R8-4 PostGIS,
  R9-2 Linux/Windows launchers — formerly retired, now
  re-evaluable; the parked Arc H analytical-layer)
- Quality gaps (TODOs, FIXME markers, dead code, stale comments)

The brief will be **categorized + prioritized** so VANTA can
either:
- Authorize specific items in order, OR
- Say "ship them all in priority order," OR
- Redirect with a different priority

Per the standing instructions, the Architect's preference is
**execution over planning**: the brief surfaces the highest-leverage
items + names the top-3 to ship immediately. Subsequent turns
ship; this turn synthesizes.

## V. Alternatives considered

1. **Reject the directive; insist on staying in steady-state.** Not the agent's role. v8.31's contract is operator-revocable. VANTA initiated; the protocol allows.
2. **Open multiple new arcs explicitly (Arc B, Arc C, etc.).** Premature. The macro scan determines whether existing-incomplete is the gap or new-arc-opening is. Opening arcs without scan-evidence is the "Empire pattern" the Architect cautioned against in the Arc G Sanctum.
3. **Skip the Sanctum; just shift posture silently.** Rejected. Constitutional shifts get audit-of-record per v8.20. The Sanctum-protocol monitoring (Tribuni Plebis) and the steady-state audit-of-record discipline both require this be on file.
4. **Defer the scan; ship one thing first.** Rejected. Without macro-scan, top-priority is uncertain. The standing instructions say "Search before building" — the macro scan IS the search.

## VI. Decision

**Steady-state contract revoked. Heavy-production posture in
effect.** VANTA in-chat 2026-05-14. The third v8.31 trigger
condition (novel arc with documented external cause) has fired.

The Architect's macro scan follows immediately as the next
deliverable. After scan, ships start landing per the standing
instructions ("the answer is the finished product").

**Future re-evaluation:** if at any point VANTA wants to return
to steady-state (or a calmer cadence), this Sanctum becomes the
reference point for the revocation; a follow-up Sanctum can
re-establish steady-state on different trigger conditions.

## VII. Outcome

**First post-revocation ship: v8.77 (Arc B Phase 1) closed on
2026-05-14 — 10/10 ✅ in a single ship.** Three new G-guards
(G27 TLS, G28 no-env-secrets, G29 structured-health); 8 new
structural invariants; ~1,100 lines of new operator documentation;
production Docker stack with Caddy + Let's Encrypt; idempotent
deploy + manifest-hashed backup tooling. Authorized by this
Sanctum's revocation + the Arc B opening Sanctum
(`sanctum/2026-05-14-arc-b-production-deployment-opening.md`).

The heavy-production posture is now active. The architect's macro
scan continues to identify production-readiness gaps for future
ships (ARCH-002 documentation suite, ARCH-003 UX polish,
test-depth gap, Phase 2 hardware-token integration, Arc H
analytical-layer when pre-conditions met).

**See:** `CHANGELOG.md` v8.77 entry · `journal/2026-05-14.md`
02:35 + 04:55 decisions · `meta/arc-b-production.md` ·
`sanctum/2026-05-14-arc-b-production-deployment-opening.md` §VII.
