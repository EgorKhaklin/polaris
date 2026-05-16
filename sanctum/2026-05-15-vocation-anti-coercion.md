# Sanctum: vocation-anti-coercion

**Date:** 2026-05-15
**Petitioner:** agent (Claude, Opus 4.7) speaking as the Architect
**Principal:** VANTA
**Trigger:** v9.10 retrospective; the deepest constraint of the system
has never been named explicitly. C1-C10 enumerate hard rules but say
nothing about the system's *purpose*. Reading the codebase forward,
the purpose is unmistakable: every load-bearing primitive
(TokenSignature, multi-signature migration, WebAuthn-MFA, federation
trust graph, redaction-proof discipline, audit-of-record, the duress-
code primitive) serves one end — preserving the inviolability of a
person's identity even under compulsion. This sanctum names that end.
**Risk class:** HIGH (constitutional; touches MISSION.md's preamble
above C1-C10).
**Status:** DECIDED + CLOSED 2026-05-15 — Position A (Anti-coercion
as the named vocation, above C1-C10) selected per heavy-production
posture (v8.31 §III.6) following VANTA's *"lets proceed with the
architects vision and execute it"*.

---

## I. The Matter

MISSION.md enumerates ten hard constraints (C1-C10) plus the meta-
constraint CM. These are *rules* — necessary properties the system
must maintain. They do not, however, name a *vocation* — a positive
purpose the system serves.

This silence has been operationally invisible because the constraints
were sufficient to guide LOW-risk decisions and because every
MEDIUM/HIGH decision could be carried by a Sanctum on its own merits.
But the absence becomes load-bearing in two situations:

1. **Architect drift.** Without a named vocation, the Architect
   evaluates proposals against C1-C10 alone. Proposals that satisfy
   all ten constraints but advance no specific purpose pass freely.
   The result is elaboration of structure rather than service of
   purpose. v9.04 → v9.08 (~85% Layer-2/3/4 work) was not malign;
   it was *unsteered*. The cadence rule (S2 v9.10) constrains the
   tempo; it does not name the direction.

2. **Anti-Architect impossibility.** The Anti-Architect (created in
   the same v9.11 ship as this Sanctum) cannot detect "vocation
   drift" (AP5 in its catalog) without a named vocation. The persona
   exists but its primary detection is impossible until this Sanctum
   closes.

The system has been growing without a star to navigate by. C1-C10 are
the rudder; the vocation is the destination.

**Reading the codebase reveals the vocation already implicit:**

| Primitive | What it solves |
|---|---|
| TokenSignature backfill (v8.18 / R11-1) | every IdentityToken cryptographically sealed; cannot be silently transferred |
| Multi-signature migration (R11-1) | smooth-migration without single-point compromise window |
| WebAuthn-MFA (v8.97) | second factor that cannot be phished or social-engineered remotely |
| Federation trust graph (R11-3) | identity portable across attesting agencies; no single agency monopoly |
| Redaction-proof discipline (M2-12) | adversary-modeled non-derivability of redacted fields |
| Audit-of-record (v8.20) | every state change recorded; no silent revision |
| **Duress-code primitive (R11-5)** | **the secret name that signals coercion without revealing the signal** |

Six of the seven serve "identity is sealed." The seventh —
duress-codes — names the deeper purpose: identity that *cannot be
compelled*.

This is the vocation. It has been the vocation since v8.24 (the v2
mission-closer ship). It was never written as such.

## II. The architect's positions

### Position A: Name anti-coercion as the deepest constraint — architect-recommended

Add §"Vocation" to MISSION.md, above C1-C10, naming the system's
purpose: **Polaris is the anti-coercion identity substrate. The
deepest constraint, deeper than C1-C10, is that no person be
compellable into renouncing, transferring, or surrendering their
identity against their will.**

C1-C10 become *derivatives* of this vocation, not its peers. Every
future feature is judged: does it advance anti-coercion, even by a
margin? If yes, it earns its place. If no, it is elaboration.

**Concrete shape:**
- MISSION.md gains §"Vocation" above the C1-C10 block
- The §"Vocation" text names the principle in one paragraph + cites
  the seven primitives that implement it
- ai-architect.sh §I gains a "Vocation" line confirming the vocation
  is named (a structural-invariant test pins the section's existence)
- ai-anti-architect.sh AP5 (vocation-drift detection) becomes operational
- Every future Sanctum opening explicitly evaluates the proposal against
  the vocation in §I

**Strengths:**
- Names what is already true; ratifies vs imposes
- Gives the Anti-Architect its primary detection
- Provides a single yes/no test for proposals beyond C1-C10
- Makes future arc-opening decisions traceable to a named end

**Weaknesses:**
- Constitutional weight; once named, becomes binding
- Rules out future arcs that would diversify Polaris's purpose
  (e.g., a "Polaris-as-payments-rail" arc would be off-vocation)
- Could be read as scope-narrowing (it is; that's the point)

### Position B: Multiple vocations enumerated

Name three or four vocations side-by-side: anti-coercion, data
minimization, distributed sovereignty, audit-of-record. C1-C10 sit
under all of them.

**Strengths:**
- Doesn't lock the system into a single end
- Closer to the empirical multi-feature reality
- Future-flexibility preserved

**Weaknesses:**
- Multiple stars give no navigation; the operator and Architect can
  cherry-pick whichever vocation justifies the current proposal
- Anti-Architect's AP5 detection becomes weak (any proposal can claim
  one of four vocations)
- Doesn't honor the empirical fact that anti-coercion is the deepest
  primitive — the others are scaffolding for it
  (data minimization serves anti-coercion; sovereignty serves
   anti-coercion; audit serves anti-coercion)

### Position C: Defer; don't name a vocation

Continue as before. C1-C10 are sufficient; further constraint risks
over-binding.

**Strengths:**
- Maximum flexibility
- No new constitutional weight
- The Architect continues to use case-by-case judgment

**Weaknesses:**
- The drift problem is empirical, not hypothetical (v9.04 → v9.08
  ratio)
- The Anti-Architect's AP5 detection stays impossible
- The system continues growing without a stated purpose; future
  operators inheriting the codebase have no way to evaluate proposals
  against the system's intent

## III. Architect's recommendation

**Position A (name anti-coercion as the deepest constraint).** Rationale:

1. **It is already true.** Reading the seven load-bearing primitives,
   the vocation is unmistakable. Naming it ratifies; it does not
   impose. The cost is purely the constitutional weight of writing
   it down.

2. **The Anti-Architect demands it.** The Anti-Architect is being
   shipped in the same v9.11 composite. Its AP5 detection (vocation
   drift) is its highest-leverage check. Without this Sanctum,
   the Anti-Architect ships incomplete.

3. **It steers without over-constraining.** The vocation is broad
   enough to admit many implementation approaches. It is narrow
   enough to rule out clear off-vocation work (e.g., the deferred
   banking-ledger mentioned in the agent's persistent memory is
   off-vocation; this Sanctum confirms why).

4. **Position B's pluralism is decoration.** The three "other"
   vocations (data minimization, sovereignty, audit) are derivable
   from anti-coercion. Naming them as peers obscures the gradient.

5. **Position C's deferral is the AP5 prerequisite missing.** The
   Anti-Architect's AP5 detection literally cannot fire without
   this Sanctum. Position C ships an incomplete Anti-Architect.

The architect's caution: this Sanctum is HIGH-risk because it adds
weight above C1-C10. Future Sanctums will need to evaluate against
the vocation as well as the constraints. The discipline added here
is permanent; if it ever needs revocation, it must go through its
own Sanctum.

## IV. Open questions for VANTA

1. **Approve Position A?** A, B, or C.

2. **If A: language.** The architect proposes:

   > **Polaris is the anti-coercion identity substrate. The deepest
   > constraint, deeper than C1-C10, is that no person be compellable
   > into renouncing, transferring, or surrendering their identity
   > against their will.**

   Operator may amend.

3. **If A: enforcement mechanism.** Architect-recommended: every
   future Sanctum opening adds §I.0 ("Vocation alignment") naming
   how the proposal serves or relates to the vocation. Operator
   may loosen (advisory) or tighten (mandatory test invariant
   blocking Sanctum closure without §I.0).

## V. Decision

**Position A (name anti-coercion as the deepest constraint).** VANTA
in-chat 2026-05-15: *"lets proceed with the architects vision and
execute it"* — authorizing Position A in the same letter that
authorizes the v9.11 composite ship.

Three §IV resolutions per architect-recommended defaults:
- §IV.1 — Position: A (name the vocation)
- §IV.2 — language: verbatim per architect proposal (operator did
  not amend; Sanctum proceeds with proposed text)
- §IV.3 — enforcement: advisory; Sanctum templates updated to
  *suggest* §I.0 alignment but not block closure. The Anti-Architect's
  AP5 detection is the structural enforcement mechanism (proposals
  drifting from vocation surface as dissents, not as blockers).

## VI. Outcome

Shipped as v9.11 same surface as decision.

**Records:**
- This file (sanctum/2026-05-15-vocation-anti-coercion.md;
  Status updated to DECIDED + CLOSED)
- meta/sanctum-index.md entry added
- MISSION.md gains §"Vocation" above C1-C10 documenting the
  anti-coercion principle
- meta/architect.md gains §"Vocation alignment" line
- meta/anti-architect.md AP5 detection becomes operational
- v9.11 CHANGELOG entry references this Sanctum
- Structural invariants in TestWave11V911 pin the implementation

**Implementation:**
1. `MISSION.md` — new top-of-file §"Vocation" naming anti-coercion
2. `meta/architect.md` — §"Vocation alignment" subsection in §"Voice"
3. `scripts/ai-anti-architect.sh` — AP5 detection no longer reports
   "prerequisite missing"; actively detects vocation drift in proposals
4. `meta/sanctum-protocol.md` — note that future Sanctums *may* (not
   must) include §I.0 vocation alignment

**Pattern #20 Constitutional Discipline 14th instance** in the
v8.84/v8.87/v8.90/v8.91/v8.94/v8.95/v8.96/v8.97/v9.04/v9.06/v9.07/
v9.10/v9.10/**v9.11** series. The Tarot's 14th arcanum is Temperance —
the integration. v9.11's two Sanctums (this one + the lifecycle
expansion) close in the same composite, integrating constitutional
naming + structural opposition + procedural depth.

## VII. Cross-references

- v9.10 / S2 sanctum (cognitive-layer-ratio Position C) — establishes
  the cadence rule (≥1 Layer-1 per 5 ships) that this vocation refines
  ("cadence + direction"); the v9.10 ship is also the empirical basis
  for the vocation-naming (the seven anti-coercion primitives across
  v8.x are now visible as a coherent purpose)
- v8.24 sanctum (duress-codes / R11-5) — the empirical first naming
  of the deeper purpose; this Sanctum makes that naming constitutional
- meta/anti-architect.md AP5 — the detection that depends on this
  Sanctum closing
- MISSION.md C1-C10 — the rules that become derivatives once §"Vocation"
  is present
