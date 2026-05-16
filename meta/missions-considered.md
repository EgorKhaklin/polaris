# meta/missions-considered.md — strategic arcs weighed at v2 (2026-05-09)

When the v1 done-list closed (12 of 15 shipped, 3 deferred), four candidate
arcs were on the table for what comes next. This file preserves all four —
chosen and unchosen — so a later session can re-weigh the tradeoffs without
rebuilding the analysis from scratch. The chosen arc (D + A) is in
`MISSION.md`; the others sit here as future options.

---

## v1 retrospective — what played out

| Item | Status as of 2026-05-09 | Notes |
|---|---|---|
| 1. Schema models full lifecycle | ✅ v1 | |
| 2. Stored procedures UC-1..UC-7 | ✅ v1 | |
| 3. Application-layer context-scoped verification | ✅ v3 | |
| 4. Cybersecurity controls | ✅ v4 | |
| 5. Concurrency hazards sealed with tests | ✅ v6 | |
| 6. Scales to 2M+ events with bounded responses | ✅ v6 | |
| 7. Test coverage (Python + SQL) | ✅ v6/v7 | |
| 8. STRIDE threat model | ✅ v7 | |
| 9. Antimeridian-spanning bbox | ✅ v7 | |
| 10. Cursor pagination | ✅ v7.4 | |
| 11. Property-based tests for invariants | ✅ v7 | |
| 12. Multi-process rate limiter (Redis) | ✅ v7.5 | |
| 13. External IdP (OIDC) | ⏸ DEFERRED 2026-05-09 by user | |
| 14. Banking-on-Polaris (separate repo) | ⏸ DEFERRED 2026-05-09 by user | |
| 15. Linux + Windows launchers | ⏸ DEFERRED 2026-05-09 by user | |

The mission framework worked: each item shipped with tests, docs, and
mission-level acceptance, and ai-status.sh confirms the C1–C10 hard
constraints all green. The scaffolding (MISSION/ROADMAP/BACKLOG +
ai-status/ai-propose) is a keeper for v2.

---

## Arc A — The PDF's open problems (§9 of docs/paper/polaris_project_report.pdf) [CHOSEN, paired with D]

The report itself names six failure modes the schema does not yet model.
This arc closes the loops the report explicitly opens.

| § | Problem | v2 done-list item |
|---|---|---|
| §9.1 | Catastrophic-loss recovery (all tokens & devices destroyed) | M2-7. Catastrophic-loss recovery (UC-8) |
| §9.2 | Issuer trust concentration / federation | M2-8. Issuer federation model |
| §9.3 | Population coverage (newborns, unhoused, biometric-incompatible) | M2-9. Tiered enrollment / Individual without token |
| §9.4 | Cryptographic migration during transitions (multi-sig) | M2-6. Multi-signature transitional state |
| §9.5 | Compulsion resistance (duress codes, attestation delays) | M2-10. Duress codes |
| §9.6 | Centralized trust assumption / DID anchoring | covered by D's M2-2 |

**Why chosen:** the report's own conclusion is that these are the open
problems. Closing them is mission-aligned in a way no roadmap-derived item
can be — the ground truth is the report itself.

**Tradeoff accepted:** each is substantial design work, several touch
the schema (which means migration script discipline). v2 is multi-session.

---

## Arc B — Adversarial hardening [NOT CHOSEN — reconsider when prod-deploying]

A maturity track that proves what's already built rather than building
new. Treats Polaris as system-under-attack.

| Item | Sketch | Risk class |
|---|---|---|
| B1. Mutation testing | Run mutmut (or cosmic-ray) over polaris_web; CI gate at 70% kill rate | LOW |
| B2. Chaos tests | kill -9 mid-transaction; verify C1 audit invariant holds; pkill postgres mid-write | MEDIUM |
| B3. Formal model-check | TLA+ or Alloy spec of the state machine (Appendix A); machine-checked legal-transition set | LOW |
| B4. Self-pen-test | OWASP ZAP automated; auth bypass / SQLi / XSS regression suite | MEDIUM |
| B5. 10M+ event load test | locust or k6 driving sustained 1000 RPS for 5 min, p95 latency target | MEDIUM |
| B6. Coverage report integration | CI publishes coverage HTML; ratchet floor on regression | LOW |

**When to pick this up:** before the first real production deployment, OR
when an external security audit is on the calendar, OR when v2's substrate
work has introduced enough new attack surface that hardening becomes the
constraint.

---

## Arc C — Polaris-as-platform [NOT CHOSEN — reconsider when a partner is consuming Polaris]

A productization track. Makes Polaris consumable by external systems —
turns the reference impl into something a partner could actually build
against.

| Item | Sketch | Risk class |
|---|---|---|
| C1. OpenAPI 3.1 spec | Auto-generate from app.py routes; serve at /openapi.json | LOW |
| C2. API versioning | /api/v1 prefix, deprecation header policy, per-version test suites | MEDIUM |
| C3. Lifecycle webhooks | POST to subscriber URL on REVOKE/LOST/EXPIRED with HMAC signature | MEDIUM |
| C4. Bulk import | CSV upload with dry-run + commit; preserves audit trail | MEDIUM |
| C5. Streaming export | Server-sent CSV chunks for 10M+ row exports without OOM | MEDIUM |
| C6. First-party clients | Python + TypeScript client libraries with examples | MEDIUM |
| C7. Request-ID propagation | UUID per request through logs and webhook deliveries | LOW |

**When to pick this up:** when an external system (banking-on-Polaris,
a partner agency, a downstream verifier) is genuinely about to consume
Polaris. Without that pull, the work is over-built.

---

## Arc D — Substrate-level demonstrations [CHOSEN, paired with A]

The architectural arguments in Appendices E and F are currently prose. D
makes them code. The `proof_commitment` column on VerificationEvent is a
placeholder string today; under D it carries a real ZK-SNARK proof. The
`BlockchainAnchor` table records hashes today; under D those hashes resolve
to actual verifiable on-ledger entries.

| Item | Sketch | Risk class |
|---|---|---|
| D1. Real ZK-SNARK for ZERO_KNOWLEDGE | Groth16 over a circuit proving "I hold an ACTIVE token in registered set" without revealing token_id | HIGH |
| D2. Functional DID anchoring | Append-only Merkle log + per-anchor inclusion-proof endpoint | MEDIUM |
| D3. Substrate-dependency manifest | Every primitive Polaris depends on, with fail-mode + replacement plan | LOW |
| D4. GenomicAnchor schema | Appendix F.1 — hash-only genomic anchor; constraint refuses plaintext | LOW |
| D5. QuantumObserverBinding scaffold | Appendix F.2 — schema scaffold + DEFERRED markers; rationale doc | LOW |

**Why chosen:** D is the work that makes Polaris distinct from any other
identity reference impl. Anyone can build the schema; few build the proof
that the schema's claims survive substrate attacks. D is the unique
contribution.

**Tradeoff accepted:** D1 is a cryptographic rabbit hole — Groth16 wiring,
trusted setup, witness generation. The reward is that "ZERO_KNOWLEDGE
verification" stops being a marketing label and becomes a checkable claim.

---

## The chosen v2 arc — D + A

Twelve items, mixed risk classes, mixed effort. Five from D (substrate),
seven from A (open problems). See `MISSION.md` for the active done-list
with full acceptance criteria, and `ROADMAP.md` for the prioritized
sequence (R10-* for D items, R11-* for A items).

The case for the combination: D proves the architectural argument; A
closes the report's named gaps. Together they're the work that takes
Polaris from "the schema implements the design" to "the system stands
behind the design's claims."

---

## Re-evaluation triggers

This file should be revisited when any of these happen:

- **v2 done-list closes ≥ 75%** — time to plan v3 against the same arc set.
- **Production deployment is committed** — Arc B becomes load-bearing.
- **An external partner consumes Polaris** — Arc C becomes load-bearing.
- **A cryptographic primitive Polaris depends on is publicly broken** —
  Arc D's substrate manifest is the response surface.
- **The user explicitly resurrects a deferred item (13/14/15)** — those
  items move back into ROADMAP and out of `memory/deferred_items.md`.

The agent should propose re-evaluation; the user decides.
