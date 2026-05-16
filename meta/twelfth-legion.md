# meta/twelfth-legion.md — the held silence

## What this document is

This is the constitutional notice that the twelfth legion slot in
Polaris's Mycelium swarm is **deliberately reserved** as of v9.11. It
is not a deferred feature; it is not a TODO. It is a **held silence** —
a structural reservation made on the principle that the system should
hold space for what it does not yet know it needs.

The current legion registry (in
[`polaris_swarm/legions/__init__.py`](../polaris_swarm/legions/__init__.py))
contains 11 legions:

- **Republican (9):** Schema, Cognitive, Security, Mission, Adversary,
  Performance, Trajectory, Substrate, Docs
- **Imperial (2):** Praetorian, Engineer

Eleven is structurally unstable in tiling-geometry. Twelve is the
natural completion. Rather than create the twelfth preemptively, v9.11
formalizes the reservation.

## Why a reserve, not a feature

A legion exists to organize commander ants around a shared operational
domain. Creating a twelfth legion preemptively would mean either:

1. **Splitting an existing domain** — fracturing a coherent legion just
   to reach 12. This would not improve the swarm; it would just inflate
   the count.

2. **Inventing a new domain** — adding work that the system does not
   currently need. This is exactly the kind of self-elaboration the
   Anti-Architect (`meta/anti-architect.md`) AP3 detection refuses.

The principled path is to **wait for the operational need to surface**.
When a future ship genuinely demands a new legion (a new domain that
deserves its own commander hierarchy), the twelfth slot exists to
receive it.

## Manifestation protocol

When the twelfth legion's need surfaces:

1. **Operator or HYDRA identifies the operational gap** — typically a
   pattern of findings that don't fit cleanly into any existing
   legion's domain.

2. **Open a Sanctum** — `sanctum/<date>-twelfth-legion-<topic>.md`.
   §I documents the operational need; §II proposes the legion's name
   + scope; §V (decision) authorizes addition.

3. **Implementation:**
   - Create `polaris_swarm/legions/legio_<name>.py` following the
     pattern of existing legions
   - Add to `ALL_LEGIONS` in `polaris_swarm/legions/__init__.py`
     (typically appended to `IMPERIAL_LEGIONS` unless mythologically
     a Republican addition; operator decides)
   - Flip `RESERVED_TWELFTH_LEGION_SLOT["manifested"]` to `True`
   - Update structural invariant (`TestWave11V911` →
     `len(ALL_LEGIONS) == 12`)
   - CHANGELOG entry naming the vocation-alignment of the new legion

## Naming convention

The twelfth legion's name is **not pre-assigned**. Pre-naming would
constrain the manifestation. The name emerges from the operational need:

- If the need is treasury-specific: `LegioFiscalia`
- If a second constitutional guard: `LegioPraetoriaSecunda`
- If a third Imperial legion focused on something new: `Legio<X>`
- If a tenth Republican legion (very unlikely; would require Sanctum
  arguing the Republican count should grow from 9 to 10):
  `Legio<DomainName>`

## Why this is documented (not just left implicit)

The Architect's vision named "honor the geometry" as one of three
pillars. Honoring the geometry means *not breaking patterns when they
emerge*. The 11/12 asymmetry is felt — it has been mentioned in prior
analyses as structural dissonance. Without explicit reservation, the
gap is mistaken for an oversight; with reservation, it is recognized
as deliberate.

The reservation also gives the Anti-Architect a precedent. Future
proposals to "add a legion" must demonstrate that the operational need
is genuine; the existence of this reserve makes the question
legitimate (and the AP3 detection — proposal-as-self-elaboration —
fires when the proposal is just for completion's sake).

## Cross-references

- [`polaris_swarm/legions/__init__.py`](../polaris_swarm/legions/__init__.py) —
  `RESERVED_TWELFTH_LEGION_SLOT` constant
- [`polaris_swarm/legions/README.md`](../polaris_swarm/legions/README.md) —
  the legion registry README
- [`MISSION.md` §"Vocation"](../MISSION.md) — the vocation any new
  legion must serve
- [`meta/anti-architect.md`](anti-architect.md) — AP3 (self-elaboration)
  + AP5 (vocation drift) — the dissents that gate new-legion proposals
- v8.71 sanctum (Arc G Roman Empire opening) — the precedent for
  Imperial legion additions; the shape any twelfth-legion Sanctum
  follows
