# DEVNOTES: the working notes

**Reader:** a contributor about to change something. **Job:** the four notes
that are genuinely internal, kept out of the published documentation set
because nobody evaluating Polaris needs them.

The design records that used to live here, the threat model, the concurrency
catalogue, the substrate manifest, the ZK soundness ledger and one record per
mechanism, moved to [docs/design/](../docs/design/README.md) at v9.224. They
are assessor-facing material and were filed where an assessor would not look.

| File | What it holds |
|---|---|
| [style.md](style.md) | The house style: declarative prose, no em-dashes, no cosmic framing, and the quality bar a ship has to clear |
| [known-gotchas.md](known-gotchas.md) | Things that have already cost an hour: environment quirks, tool behaviour, and the traps in this codebase |
| [record.md](record.md) | The project record: the completed arcs and the deployment phase log, moved out of MISSION.md at v9.195 |
| [presentation-plan.md](presentation-plan.md) | The sub-roadmap for the presentation pass: every ship, its status, and the ordered changes it carries |
| [athena-ontology-assessment.md](athena-ontology-assessment.md) | The adversarial assessment of an operational ontology (Athena): model power and rules, never a graph of people; verdict, constraints, MVP, and kill criteria (roadmap P6.8) |
| [operational-learning-assessment-brief.md](operational-learning-assessment-brief.md) | A captured, NOT-STARTED brief for a future assessment: an advisory ML subsystem that learns Polaris itself (never natural persons); central hypothesis, hard boundary, constitutional candidate, invariants, MVP, and a naming note (proposed "Metis", not "Prometheus") |
| [production-readiness-review.md](production-readiness-review.md) | Assessment of an external model's ~35 pre-deployment suggestions: what the tree already does, what to adopt, what to push back on, mapped to the P1.18 consolidation arc (claim honesty, constitution layering, dead-schema removal, external validation, honest scale/detection testing) |

## Where does something new go

- A design record for a mechanism, or a cross-cutting principle an assessor
  would want: [docs/design/](../docs/design/README.md), with a row in its
  index.
- An operational procedure: [docs/operator/](../docs/operator/README.md).
- A technical reference an integrator reads: [docs/reference/](../docs/reference/README.md).
- Something only a contributor working in this repository needs: here, with a
  row in the table above.
