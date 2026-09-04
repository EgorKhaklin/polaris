# Abuse controls

**Reader:** an engineer or an assessor. **Job:** The per-agency quotas, where they are enforced, and what an operator sees when one refuses a write.

---

## What this is

Two controls on the SHAPE of agency behaviour, in the lineage
(`issuer-discretion.md`): a hard bound (quotas) and an early signal
(velocity alerts).

- **Quotas** are opt-in, per agency, per kind, in rolling windows, and live in
  the database as a BEFORE trigger. A cap holds on every path: the stored
  procedures, the SQL console, a bulk loader. There is deliberately no opt-out
  GUC (unlike the raw-UPDATE guard of: a sanctioned procedure is still
  the agency doing the thing the cap bounds.
- **Velocity alerts** compare each agency against ITS OWN trailing week, not
  against a global number, so a large agency's normal day never trips a small
  agency's threshold; an absolute floor keeps a young or quiet agency's first
  actions from paging.

## Choices, and why

- **Opt-in, not default caps.** The revocation bound has a default because
  revocation is destructive. Issuance and verification volumes are legitimate
  functions of an agency's size; a default absolute cap would break a large
  legitimate agency on day one and protect nobody in the meantime. The
  always-on control is the alert; the cap is the operator's answer to it.
- **Count-based caps, next to the percentage bound.** bounds revocation
  as a share of an agency's issued base; a share says nothing about absolute
  rate, and a percentage bound cannot exist for issuance (no denominator) or
  verification (not the agency's own tokens). Counts per window compose with
  the percentage; whichever trips first refuses.
- **Windows from the audit-of-record tables.** The count is computed from
  IdentityToken.issued_date, TokenLifecycleEvent REVOKED rows, and
  VerificationEvent.event_timestamp, never from a separate counter that could
  drift from the truth it summarises.
- **Exact under concurrency.** A per-(kind, agency) transaction-scoped
  advisory lock serializes the count-then-write; the C9 test races twelve
  writers at a cap of five and gets exactly five. Without the lock the cap
  is "about five".
- **The uncapped path is the hot path.** One primary-key lookup on
  AgencyQuota, then RETURN NEW, before any lock or count: the bulk loader and
  every unconfigured deployment pay nothing measurable.
- **Per agency, never per person.** Both the counters' labels and the caps'
  keys are agency ids (bounded cardinality). Nothing here filters or scores
  the population; the vocation line is the design line.
- **The refusal is loud everywhere.** The trigger's sentence reaches the
  operator (HTTP 429), the log (`quota_refused`, with the request id), the
  metric (`polaris_quota_refusals_total`), and the pager
  (`PolarisQuotaRefusals`). A cap that refuses silently would be
  indistinguishable from a bug.

## Adversary walk

- *An operator scripts the issuance form at 3 a.m.* PolarisIssuanceVelocity
  pages within the hour (the floor of 20 and 4x the agency's baseline); the
  operator's session is ended (`user-passwd` / `user-deactivate`, v9.189) and
  a cap set; the tokens already issued are revoked through the bounded
  procedure, never by editing history.
- *A verifier sweeps the population.* PolarisVerificationVelocity pages at
  200/h and 4x baseline; `quota-set --verify-per-hour` stops the sweep at the
  database on the next write; the federation attestation can be revoked.
- *Someone bypasses the app with psql.* The trigger fires on the raw insert;
  the SQL console runs as the same role.
- *Concurrent writers race the cap.* The advisory lock makes the loser see
  the winner's row. Tested.
- *A cap is set too low and real operators are refused.* PolarisQuotaRefusals
  pages at SEV-3 for exactly this; the runbook's first step is
  `polaris quota-show`, whose justification says why the cap exists.

## What it is NOT

Not a rate limiter on requests (that is per IP, in `security.py`, and stays).
Not analytics on holders. Not a default. Not a policy Polaris decides: the
caps and their justifications are the authority's rows.
