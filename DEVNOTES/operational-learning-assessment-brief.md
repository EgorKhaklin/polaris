# Operational-learning subsystem: assessment brief (NOT STARTED)

**Status:** a captured request for a *future* adversarial assessment, on the model
of [athena-ontology-assessment.md](athena-ontology-assessment.md). Nothing here is
built, endorsed, or decided. It "needs thought" (VANTA). Do the assessment first;
do not write code from this brief.

## The proposed subsystem

An ML subsystem that learns **Polaris itself** — its infrastructure, authorities,
and system behaviour — so operators can detect anomalies, forecast capacity,
diagnose failures, catch regressions, and understand institutional abuse patterns.

**Central hypothesis (to be falsified, not assumed):** Polaris may use machine
learning to infer properties of *the system*, but must **not** use machine
learning to infer, rank, score, predict, or determine the rights of *natural
persons*. Renaming `Person` to `Subject`/`Entity`/`IdentityVector` does not solve
this if the data stays linkable to a person; reason about information flows, not
labels.

**Absolute boundary (presumptively prohibited):** fraud/risk scores for
individuals, behavioural profiles, relationship/social-graph inference,
eligibility or likelihood-of-revocation scoring, person-level clustering or
embeddings, population segmentation, model-driven denial of rights. The final
reasoning test, applied repeatedly: *is it learning how the identity system
behaves, or how people behave?* If the latter, stop.

## Naming (open; final name deferred to the assessment)

The brief floated the codename **Prometheus** (forethought) and gave explicit
latitude to choose a better one. **Recommendation: do NOT use "Prometheus"** —
Polaris already depends on `prometheus_client` and runs a Prometheus +
Alertmanager metrics/alerting stack, so the name would collide with live
observability infrastructure and confuse every operator. Proposed instead:
**Metis** (practical wisdom / forethought — a near-synonym without the
collision), which pairs cleanly with **Athena** (in myth, Metis is Athena's
mother): *Metis learns how the system behaves; Athena understands its structure;
Atlas sees what is happening; Themis constrains them all.* Not final.

## Scope to evaluate (each use case assessed separately)

Infrastructure anomaly detection, capacity forecasting (with uncertainty
intervals), performance-regression intelligence (possibly in CI), chaos-learning
(which conditions correlate with poor recovery; propose experiments, never inject
autonomously), root-cause assistance (telemetry + Athena's dependency graph),
**aggregate** institutional/agency anomaly detection ("Agency A normally revokes
0.8%/month, now 4.9%" — never "Person X looks suspicious"), and security anomaly
detection that supplements, never replaces, deterministic rules. Compare every ML
approach against a deterministic baseline; if a rule works as well, use the rule.

## Primary design law

Advisory only: OBSERVE -> MODEL -> PREDICT -> EXPLAIN -> RECOMMEND. Never
PREDICT -> {REVOKE, DENY, CHANGE RIGHTS, ISSUE, MODIFY CONSTITUTION, SILENTLY
CHANGE PRODUCTION CONFIG}. A recommendation is evidence, never authority; every
consequential action still resolves through named authorization, deterministic
policy, a DB constraint, human approval where required, and the append-only
audit — exactly as Athena's non-sovereignty already requires.

## Constitutional candidate (evaluate as a new invariant)

> Machine learning may infer properties of Polaris, its infrastructure, and
> institution-level behaviour. It may not infer properties of natural persons for
> authorization, eligibility, revocation, ranking, prediction, or rights
> decisions.

## Training data & MLOps sketch (for the assessment to design)

Approved-feature pipeline only (authoritative systems -> telemetry extractor ->
privacy/schema gate -> feature store -> model); every feature carries provenance,
aggregation level, sensitivity, and person-linkability (person-linked defaults to
forbidden). Prefer aggregates/histograms/rates over raw events. Synthetic-nation
ground truth (`polaris_sim`) is the primary training/eval ground: inject a known
condition, measure precision/recall against the known truth, never claim success
from anecdotes. Reproducibility from committed config + dataset manifest + seeds;
never commit sensitive datasets, only provenance. Model promotion is a controlled
release with rollback; models never silently retrain in production.

## Candidate invariants (each needs an adversarial detection test)

No feature references `Person.id` or persistent token-level identity; no
person-level model artifacts; no model output is accepted by issuance/revocation
procedures; no ML score determines eligibility or alters constitutional state;
every feature has provenance + classification; every production model has a
signed/versioned manifest; no ZK-subject linkage enters the pipeline; training
retention is bounded; raw-feature access is least-privilege. Detection tests must
introduce a prohibited person feature and prove the build turns red, and attempt
to wire a prediction into revocation and prove the build turns red.

## MVP (if the verdict is build-a-constrained-version)

Smallest useful, advisory-only, no person data: infrastructure anomaly detection
OR capacity forecasting OR release-regression detection OR Athena-assisted
root-cause suggestions. Define baselines, measure improvement, and keep "delete
it" a legitimate outcome.

## Required assessment output (23 sections, per the brief)

Verdict; problem statement; current data inventory (real/synthetic/aggregate/
sensitive); best use cases ranked; where ML is unnecessary; architecture;
Athena integration; feature policy; person-data boundary; model choices; security
threat model; privacy analysis; governance; explainability; MLOps; synthetic-
national training strategy; invariants; MVP; evaluation plan; future autonomy;
things never to build; kill criteria; recommendation to VANTA.

## Kill criteria

Abandon if deterministic rules do as well, person-level data becomes necessary,
false positives overwhelm operators, models can't be explained, training-data
governance costs more than the benefit, Athena/telemetry alone solves it, drift
makes it unreliable, it adds unacceptable attack surface, predictions start being
used as authority, or it becomes population intelligence under another name.
