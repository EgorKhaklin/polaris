# Athena: an assessment of an operational ontology for Polaris

**Status:** study, not a commitment. **Audience:** VANTA and any reviewer
deciding whether Polaris should build an ontology layer. **Method:** reasoned
from the repository as it stands (schema, invariants, Atlas, federation,
retention, verification, the vocation), adversarially, trying to falsify the
idea. Facts drawn from the tree are marked as such; everything else is proposal.

Naming: this document calls the proposed layer **Athena** (institutional wisdom
and law) to distinguish it from **Atlas** (the bounded event map) and from the
existing `15_ontology.sql` view layer, which it partly supersedes.

---

## 0. What already exists (facts, not proposal)

The idea is not landing on empty ground. The tree already contains most of it:

- **`polaris_sql/15_ontology.sql` (v9.19)** — a read-only "semantic ontology"
  of VIEWS over the tables: `v_ontology_individual`, `v_ontology_token`,
  `v_ontology_agency`, `v_ontology_verification`, plus link views
  `v_ontology_token_timeline` and `v_ontology_individual_tokens`. Its own header
  states the discipline: "READ-ONLY over existing tables … single-entity-focused
  by construction — there are NO views that aggregate across individuals (the
  surveillance pattern is constitutionally refused)." **It nonetheless includes
  a person object** (`v_ontology_individual`, with lifetime token/verification
  counts) and a person→tokens link (`v_ontology_individual_tokens`).
- **The authority substrate already lives as tables:** `Agency`,
  `AgencyAuthorization` (which agency may issue under which algorithm),
  `AgencyTrustAttestation` (the federation trust graph, non-transitive, append-
  only, see `docs/design/federation.md`), `CryptographicAlgorithm` (C7 agility),
  `VerificationContext` + `TokenPermission` (which context may request what),
  `IssuerDiscretionPolicy` (per-agency revocation bounds / abuse controls),
  `RetentionPolicy` (retention as data with a floor).
- **C1–C10 are NOT data.** They live in `MISSION.md` (prose) and
  `meta/constraint-lattice.md` (prose), and are *enforced* by triggers, partial
  unique indexes, CHECKs, and the `polaris_checks` layer. There is no
  `ConstitutionalRule` row anywhere.

So the honest framing is not "should Polaris build an ontology" — it already has
a thin one — but **"should Polaris (a) pivot the ontology from nouns-about-people
to power-and-rules, and (b) make the constitution itself queryable, while (c)
retiring or hard-constraining the person views that already exist."**

---

## 1. Verdict

**Build a constrained version.** Build **Athena**: a read-only semantic and
provenance layer over the *existing* authority tables, plus a first-class,
machine-readable model of C1–C10 and the mechanisms that enforce them. It earns
its complexity by answering governance questions the tree cannot answer cleanly
today — *why is this agency allowed to issue this class; what rule bounds this
action; which component mechanically enforces it; what breaks if this algorithm
or key is retired; which authorities depend on this trust edge.* It is safe only
if person-legibility is made **structurally impossible**, not merely discouraged:
no natural-person node, no globally linkable person surrogate, no cross-context
person edge, no unbounded traversal, and the ontology is **non-sovereign** (it
may describe and orchestrate authority; the database and its constitution remain
the source of authority). The same ship must reckon with the *existing*
`v_ontology_individual` person view: constrain it to the single-entity,
already-authorized investigate path or remove it. If those constraints cannot be
made mechanically true and tested, do not build it.

---

## 2. Why this idea exists — the problem it solves

The gap is **governance explainability and impact analysis**, and it is real:

- *Provenance of authority.* Today, "why may Agency A issue credential class C?"
  is answered by joining `AgencyAuthorization`, `CryptographicAlgorithm`,
  `Agency.jurisdiction`, and reading `federation.md` and `MISSION.md`. The answer
  exists but is assembled by hand, differently by each operator, with no trace.
- *The constitution is not introspectable.* C8 bounds the Atlas; but nothing in
  the running system can be *asked* "which rule bounds this query, and which
  trigger/index enforces it?" The link from a rule to its enforcement mechanism
  is prose in `constraint-lattice.md`. An auditor cannot mechanically verify that
  every constitutional rule still resolves to a live enforcement.
- *Blast-radius questions have no answer.* "If ML-DSA-65 is deprecated tomorrow,
  which agencies, contexts, and stored signatures are affected?" and "if this
  signing key is retired, which authorities stop working?" are exactly the
  questions an operator needs during an incident, and today they require a human
  to reconstruct the dependency graph from memory.
- *The existing ontology solves the wrong half.* `15_ontology.sql` made *people*
  more legible (token/verification counts per individual) — the half that is
  off-vocation — and did nothing for *power*.

None of these justify a graph database or a person graph. They justify a small,
authoritative, queryable model of institutions and rules.

---

## 3. Best-case architecture (the strongest Polaris-aligned form)

Athena is a **materialized-but-derived semantic layer in PostgreSQL** — the
smallest thing that works:

- **Typed object views** over the authoritative tables: `Jurisdiction`,
  `Agency`, `CredentialClass` (from `CryptographicAlgorithm` + issuance policy),
  `ProofPolicy` / `DisclosurePolicy` (from `VerificationContext` +
  `TokenPermission` + the C2/C6 disclosure enforcement), `Algorithm`,
  `KeyCustody` (from the custody-driver config), `RetentionPolicy`, `RateLimit` /
  `Quota` (from `IssuerDiscretionPolicy` + the limiter config), `TrustAgreement`
  (from `AgencyTrustAttestation`), `RelyingPartyClass`, `DeploymentComponent`,
  `IncidentClass`, `RecoveryProcedure`, and `ConstitutionalRule` (**new**: C1–C10
  as rows).
- **Typed edge views**: `authorizes`, `may_issue`, `may_request`, `bounded_by`,
  `approved_by`, `relies_on`, `constrains`, `enforced_by`, `supersedes`,
  `affects`, `responds_to`. Every edge is a `SELECT` over existing keys — e.g.
  `may_issue` is `AgencyAuthorization`; `relies_on` is `AgencyTrustAttestation`;
  `constrains` and `enforced_by` are a **new curated table** linking a
  `ConstitutionalRule` to the SQL object (trigger / index / check / `check_*`
  name) that enforces it.
- **Read-only "Athena functions"** — bounded, parameterized, C8-style capped:
  `athena_authority_chain(agency, class)`, `athena_explain_proof(context)`,
  `athena_affected_by_algorithm(alg)`, `athena_affected_by_key(key)`,
  `athena_rule_enforcement(rule)`. Each returns a bounded set; none takes a
  person as input or emits one.
- **Provenance**: every authority/constitution edge carries a `source` (the
  table + row, or the migration/CHANGELOG that introduced it) so an auditor can
  reconstruct *where* an authority came from.

The one genuinely new *state* is the curated `ConstitutionalRule` /
`RuleEnforcement` mapping, which is small (tens of rows), append-mostly, and
itself gated by a `check_*` that fails if a rule points at an enforcement object
that no longer exists — closing the "prose drifted from code" gap that
`constraint-lattice.md` has today.

---

## 4. Worst-case inversion (concrete, how it becomes surveillance)

The same machinery, three plausible steps at a time, becomes population
intelligence:

1. Someone adds `athena_agency_activity(agency, since)` — bounded, innocuous.
2. Then `athena_context_activity(context)`, then a join helper "for
   convenience." Now there is a query surface that groups *events* by dimension —
   which the Atlas already bounds (C8), but Athena's join layer is not yet under
   that ceiling.
3. A maintainer adds `Subject` as an object "so incidents can reference the
   affected holder," keyed on `IdentityToken.individual_id`. It is single-entity
   at first. Then an incident-triage view joins `Subject` to `verification`
   events "to show the holder's recent activity," and now there is
   `Person → verified-at → context → time`. ZK events (C2/C6, no `token_id`)
   are excluded — so the graph is *incomplete*, which is worse: it silently
   represents only the disclosing verifications as if they were the whole truth.
4. Trust-graph centrality (`AgencyTrustAttestation`) is mined: an agency that
   many others attest becomes a hub; the hub's verification patterns, joined to
   jurisdiction, become a de-facto map of where a population's credentials are
   used. No `Person` type is required for this; the edges reconstruct it.
5. An "eligibility" function appears: `athena_agency_may_serve(agency, subject)`
   that resolves a person's active-credential and jurisdiction state — a rights
   decision computed by the graph. From there, risk scoring is one requirements
   doc away.

Every step is individually defensible and collectively catastrophic. The
existing `v_ontology_individual` is already step 3's seed. **This is why the
constraints below must be mechanical, and why the person views must be dealt with
in the same ship.**

---

## 5. Person-object decision

**Recommended rule (accept, with teeth):** *Athena SHALL NOT expose a persistent
natural-person object, a globally linkable person surrogate, or any edge whose
endpoint is a natural person or whose primary purpose is interpersonal
association.* The person abstraction is **not** unavoidable for the authority
ontology — power, rules, agencies, algorithms, and policies contain no person.
The only place Polaris legitimately needs a single person in view is the existing
**Investigate** surface (`/investigate/individual/<id>`), which is already
login-gated, single-entity, audited, and constitutionally forbidden from
cross-entity aggregation. That path should remain the *only* person view, and it
should live in the app tier, not in Athena.

Consequences:
- `SubjectRef` renamed from `Person` solves nothing if it is globally linkable;
  the rule is about **linkability and traversal**, not naming. So Athena carries
  no subject handle at all — not even opaque — because an opaque handle that is
  stable across contexts is a universal identifier.
- A ZK verification (C2/C6) leaves **no** Athena trace beyond an aggregate count
  of a *proposition* satisfied (see §ZK). It creates no node.
- The existing `v_ontology_individual` and `v_ontology_individual_tokens` views
  are the counter-example to this rule and must be removed from the ontology
  layer (the single-entity data they offer is already available on the audited
  Investigate path). Keeping them while claiming the rule would be dishonest.

Re-identification realism: even without a person type, joins over low-cardinality
dimensions (a rare jurisdiction × a rare context × a narrow time bucket) can
isolate an individual. That is a property of the *event* data, which is why C8
and the Atlas ceilings exist. Athena must inherit those ceilings on any function
that touches `VerificationEvent`, and must prefer to touch the *authority* tables
(which contain no person) instead.

---

## 6. Authority model — where Athena ends and the constitution begins

**Athena describes and orchestrates authority; it does not manufacture it.** This
is the load-bearing principle and it must be mechanical:

- An Athena *observation* ("the graph says agency A may issue class C") is only
  ever a **restatement** of a row that already exists in `AgencyAuthorization`.
  If the row is gone, the observation is gone. Athena has no independent store of
  authority — its object/edge views are `SELECT`s, so they cannot outlive their
  source.
- An Athena *action* (if any are ever built — §14) must resolve through the
  existing path: resolve actor → verify authorization against the DB → check
  jurisdiction → check quota/rate limit → invoke the existing stored procedure
  (e.g. `uc8_revoke_token`, which already enforces the revocation bound and
  co-signer) → the append-only audit trigger writes the evidence. Athena
  contributes the *explanation* and the *provenance*, never the *permission*.
  "graph says revoke → revoked" is prohibited.
- The `ConstitutionalRule`/`RuleEnforcement` table is the one exception where
  Athena holds curated state, and it is deliberately **descriptive**: it names
  which trigger/index/check enforces a rule. It cannot enforce anything itself; a
  row claiming "C6 enforced by X" is only true if `check_*` confirms X exists and
  does what it says. The map is not the territory, and a `check_*` proves it.

---

## 7. Data model (proposed)

Object views (all read-only over existing tables unless marked new):

| Object | Source |
|---|---|
| `Jurisdiction` | `Agency.jurisdiction` distinct + reference data |
| `Agency` | `Agency` |
| `CredentialClass` | `CryptographicAlgorithm` × issuance policy |
| `Algorithm` | `CryptographicAlgorithm` |
| `KeyCustody` | custody-driver configuration (file/PKCS#11/KMS) |
| `ProofPolicy` / `DisclosurePolicy` | `VerificationContext` + `TokenPermission` |
| `RetentionPolicy` | `RetentionPolicy` |
| `RateLimit` / `Quota` | `IssuerDiscretionPolicy` + limiter config |
| `TrustAgreement` | `AgencyTrustAttestation` |
| `RelyingPartyClass` | `VerificationContext` (requesting side) |
| `DeploymentComponent` | curated (new, small) — the five services + edge |
| `IncidentClass` / `RecoveryProcedure` | curated (new) — from the runbooks |
| `ConstitutionalRule` | **new** — C1–C10 + the vocation as rows |

Edge views: `authorizes`, `may_issue`, `may_request`, `bounded_by`,
`approved_by`, `relies_on`, `constrains`, `enforced_by`, `supersedes`,
`affects`, `responds_to`. Properties: names, jurisdictions, algorithm labels,
policy limits, effective dates, `source`/provenance. **No property is a natural
person, a location history, or a behavioral attribute.** Actions: none in the
MVP (read-only). Provenance: every authority/constitution edge carries the
originating row or migration/CHANGELOG reference.

Storage: **plain PostgreSQL views + one or two small curated tables.** No Neo4j,
no RDF, no triple store, no graph engine, no ontology framework. Bounded
"traversals" (authority chains) are recursive CTEs with a hard depth and row cap.
The graph here has tens of object *types* and, for authority, thousands of rows —
relational structures express it directly. Polaris deleted the v9.55 apparatus
for being harder to reason about than what it governed; a graph engine here would
repeat that mistake.

---

## 8. Privacy analysis

- **Linkability:** Athena's authority objects contain no person, so its own
  surface adds no linkability. The risk is entirely in functions that reach
  `VerificationEvent`; those must be capped like the Atlas (C8) and must never
  return per-event rows keyed to a subject. Prefer authority-only functions.
- **Inference / re-identification:** covered in §5 — low-cardinality joins over
  events can re-identify regardless of a person type. Mitigation is structural:
  Athena functions that touch events inherit `_ATLAS_MAX_*` ceilings and the
  bounded-aggregate discipline; a detection test proves an unbounded one fails.
- **ZK (C2/C6):** a zero-knowledge verification carries no `token_id` and no
  location. Athena must model the **proposition and policy**, never the subject:
  `ProofPolicy{predicate: age>=21}`, and at most an aggregate
  `propositions_satisfied_count`. No `Subject → proof → context` edge may exist,
  because for ZK it cannot (the data is absent) and for disclosing events it
  would rebuild the surveillance graph. This is the sharpest line: **ZK
  verifications leave no Athena trace but a count.**
- **Aggregation / Atlas interaction:** Athena must not become a second,
  unbounded aggregation surface beside the Atlas. Any event-touching Athena
  function routes through the same bounded roll-ups (`atlas_*`) and the same C8
  ceilings, or it is not built.
- **Retention:** Athena is derived, so it retains nothing of its own beyond the
  curated rule/component/incident tables (which are policy, not personal data).
  It must never cache event rows.

---

## 9. Security / threat model (abuse cases → mitigation)

| Abuse case | Path | Affected guarantee | Current mitigation | Missing / structural fix |
|---|---|---|---|---|
| Honest operator over-queries | easy joins invite broad reads | C8, vocation | Atlas bounds; login/RBAC | Athena event-functions inherit C8 caps; **no** generic join surface exposed |
| Malicious admin builds a population graph | adds views/functions joining events to dimensions | C2/C6/C8 | none in Athena today | `check_athena_no_person_and_bounded` fails the build on a person node, a subject-keyed edge, or an uncapped event function |
| Mission drift (Person/Household/RiskScore added) | "operationally convenient" new object/edge | vocation, C2/C6 | prose refusal in `15_ontology.sql` | schema-diff check: a new object/edge type requires an allow-list entry; a person-shaped type fails; the allow-list change is a governance event (§10) |
| Government pressure for "temporary" graph | new edge type under a flag | vocation | none | no runtime flag can add an object/edge type; only a reviewed migration can, and the check blocks person shapes regardless |
| Emergency exception widens joins | a crisis "temporary" function | C8 | none | prohibited: there is no bypass path; the ceilings are not env-configurable downward |
| Relying-party proof creep | contexts request broader proofs | C2/C6 | server-side disclosure enforcement | Athena makes creep *visible* (a `may_request` diff over time) — a benefit — but cannot itself widen a proof |
| Inference via non-person joins | low-cardinality event joins | re-identification | C8 | event-functions capped + no per-subject rows; authority-only default |
| Trust-graph centrality reveals individuals | mine `relies_on` hubs + events | C2/C6 | federation non-transitive | Athena exposes trust topology (institutions only); it must not join trust to events at subject grain |
| AI-agent traversal/inference | an agent walks Athena and infers/acts | all | the standing agent-authority boundary | Athena is read-only + bounded; any action path (§14) requires the full resolve-and-authorize chain and human review; an agent cannot exceed underlying DB permissions |
| Ontology→action escalation | a semantic observation is wired to execute | all, esp. C10/anti-coercion | none (no actions today) | actions are out of the MVP; if ever added, each maps 1:1 to a named procedure + rule + audit event, gated by a check |

The recurring structural mitigation: **no person shape, bounded event access,
and no independent authority store** — all three machine-checked.

---

## 10. Governance model

Treat an ontology-schema change like a new API endpoint or a constitutional
amendment, because a relationship type can be as dangerous as either:

- **Who may add an object/edge type:** only a reviewed migration to
  `15_ontology.sql`/Athena, never a runtime configuration. New types must be
  added to an explicit allow-list that the check reads.
- **Population-affecting change = elevated review.** Any new object, edge, or
  function that can touch `VerificationEvent` or reference `individual_id`
  requires the same scrutiny as a schema change to an audit table, and should be
  called out in the CHANGELOG as constitution-adjacent.
- **Adding an edge whose endpoint could be a person is a constitutional
  amendment**, i.e. it requires the MISSION.md amendment process, not an ordinary
  ship — and the check refuses it regardless, so the amendment would first have
  to relax the check (visible, reviewable).
- **Provenance is reconstructable:** every authority edge names its source, so an
  external reviewer can independently verify that Athena claims no authority the
  DB does not already grant.
- **After the founder leaves:** the value of Athena is precisely that it makes
  "who authorized this" mechanical rather than tribal knowledge — but only if the
  person-prohibition is a check, not a norm. The checks are the succession plan.

---

## 11. Invariants (machine-checkable) + mandatory detection tests

Every rule below is worthless without a detection test that introduces the
violation and proves the check turns red. Proposed `check_*`:

1. **No person object/edge.** No Athena view/table/function name or body
   introduces a `person`/`subject`/`individual` *node* or an edge referencing
   `IdentityToken.individual_id` or `Individual.*`. *Detection:* add a
   `v_athena_subject` view / an edge on `individual_id` → check FAILs.
2. **No globally linkable surrogate.** No Athena column is a stable
   cross-context per-person identifier. *Detection:* add a `subject_handle`
   column → FAIL.
3. **Bounded event access.** Any Athena function that reads `VerificationEvent`
   or `TokenLifecycleEvent` applies an `_ATLAS_MAX_*`-style cap and a `since`
   window. *Detection:* add an uncapped event function → FAIL.
4. **No independent authority store.** Every authority edge view resolves to an
   existing table row (no Athena table grants authority). *Detection:* a curated
   authority row with no backing source → FAIL.
5. **Every action maps to a named procedure + rule + audit.** (Vacuously true in
   a read-only MVP; the check exists so the first action added must comply.)
   *Detection:* add an action calling a non-audited path → FAIL.
6. **Rule→enforcement resolves.** Every `ConstitutionalRule` `enforced_by` edge
   names a trigger/index/check that actually exists in the tree. *Detection:*
   point a rule at a deleted trigger → FAIL. (This one also *strengthens* the
   existing prose lattice.)
7. **Superseded authority is not executable.** A revoked/superseded authority
   row does not appear in the "current" object views. *Detection:* a superseded
   trust attestation still surfaced as `relies_on` → FAIL.
8. **Ontology permissions ≤ DB permissions.** Athena grants nothing beyond the
   underlying table grants (it already inherits them, being views). *Detection:*
   a `SECURITY DEFINER` Athena function → FAIL.

These join the existing 130 checks; each ships with its adversarial test, as the
discipline requires.

---

## 12. MVP (smallest thing that proves the idea earns its complexity)

Read-only, authority-and-rules only, no person data, no actions:

- **Objects:** `Jurisdiction`, `Agency`, `CredentialClass`, `ProofPolicy`,
  `DisclosurePolicy`, `Algorithm`, `KeyCustody`, `TrustAgreement`,
  `RelyingPartyClass`, `ConstitutionalRule`.
- **Edges:** `authorizes`, `may_issue`, `may_request`, `relies_on`,
  `approved_by`, `constrains`, `enforced_by`, `supersedes`.
- **Four functions:** `athena_authority_chain(agency, class)` (why may A issue
  C), `athena_explain_proof(context)` (what policy permits this proof, bounded by
  which disclosure rule), `athena_affected_by_algorithm(alg)` (impact of a
  deprecation), `athena_rule_enforcement(rule)` (which mechanism enforces a
  constitutional rule).
- **The `ConstitutionalRule`/`RuleEnforcement` curated table** for C1–C10 +
  vocation, with check #6 keeping it honest.
- **Ship #0 in the same MVP:** remove `v_ontology_individual` and
  `v_ontology_individual_tokens` (fold any genuine need into the audited
  Investigate route), so the person-prohibition is true from the first commit.

Success criterion: an operator can answer the §2 questions from one function call
with provenance, and the eight checks are green with red detection tests. If, after
that, the functions are used less than the hand-written joins they replace, the
idea has not earned its keep (see §15).

---

## 13. Things explicitly NOT to build

Person / Household / Employer / Relationship / Associate objects; any subject
handle (opaque or not) that is stable across contexts; cross-context identity
graphs; relationship discovery or centrality over people; population segmentation,
behavioral profiles, eligibility/risk scoring; graph traversal over ZK subjects
(there is nothing there to traverse, and building the join implies disclosing
events stand in for all); a generic ad-hoc join/query console; automated
revocation from inferred properties; any commercial/advertising use; a graph
database, RDF, or ontology framework; runtime flags that add object/edge types;
downward-configurable C8 ceilings; `SECURITY DEFINER` Athena functions.

---

## 14. Migration / evolution path toward actions (if ever justified)

Read-only stays read-only until there is an overwhelming reason. If an action is
ever justified (e.g. an orchestrated multi-step revocation an operator performs
today by hand), it evolves like this: (1) the action is *simulated* first —
`athena_simulate(action)` shows the resolved actor, the authorizing rule, the
jurisdiction and quota checks, and the exact stored procedure it would call, with
no side effect; (2) the executable form calls only the existing audited procedure
(never new SQL), gated by `@security.csrf_protect` + `login_required` + the
role/quota checks; (3) check #5 turns from vacuous to binding, refusing any action
that does not map to a named procedure + rule + audit event; (4) the addition is
a CHANGELOG-called-out, constitution-adjacent ship. At every step the DB remains
the source of authority.

---

## 15. Kill criteria (abandon Athena entirely if…)

- A person node, subject handle, or `individual_id` edge is ever *needed* to make
  a feature work — the prohibition is load-bearing; if it blocks the feature, the
  feature is off-vocation and Athena has become the vector.
- Any Athena function needs to exceed the Atlas C8 ceilings to be useful.
- The `ConstitutionalRule` mapping cannot be kept honest by a check (drifts from
  code faster than it is corrected) — then it is prose with extra steps, worse
  than `constraint-lattice.md`.
- Operators route around Athena (keep hand-writing the joins) — no value, retire
  it, keep the rule→enforcement check alone.
- A governance request arrives to relax the person-prohibition "temporarily" — the
  correct response is to refuse and, if refusal is impossible, to delete Athena
  rather than let it become the requested capability.

---

## 16. Recommendation to VANTA

Build **Athena** as a read-only authority-and-constitution layer, MVP-first, in
plain PostgreSQL, over the tables that already exist. Its demonstrated value is
governance explainability and blast-radius/provenance queries the current tree
answers only by hand; its projected value (a live, checked map from every C-rule
to its enforcement mechanism) is worth having and is currently prose. Gate it on
eight machine-checkable invariants whose defining property is that
person-legibility is *structurally impossible* — no person node, no linkable
surrogate, no ZK-subject traversal, bounded event access, no independent authority
store — each with an adversarial detection test. In the same ship, remove the
existing `v_ontology_individual`/`_tokens` person views so the prohibition is true
from day one. Keep it non-sovereign: it explains and orchestrates authority; the
database and its constitution remain the source. Do not add actions, a graph
engine, or any person shape. If the person-prohibition ever obstructs a feature,
that is the signal to stop, not to relax it.

The one-line test this whole design must pass: **it makes power easier to inspect
without making people easier to control.** For the authority-and-rules scope
above, that can be made mechanically true and tested. For anything person-shaped,
it cannot — so that half is not built.
