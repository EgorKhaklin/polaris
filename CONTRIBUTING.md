# Contributing to Polaris

Polaris is a national identity token system reference implementation. It is
maintained as a coherent single-author codebase by Egor Khaklin / VANTA,
with the assistance of a Claude-driven cognitive layer that orchestrates
sessions against `MISSION.md`. Contributions are welcome, but this is not
a typical open-source project; the bar is unusual, and the process
documented here reflects that.

If you're here from the GitHub navigation chrome looking for the "how do I
file a PR" page: read the **Quick path** below. If you're considering a
substantive change to architecture or constitutional constraints, read the
whole document.

---

## Quick path (small fixes)

- Typo, link rot, bare reference fix, missed test case, documentation gap.
- Open an issue first; submit a PR with a clear before/after.
- PR description must include: motivation, change, blast radius.
- No need to invoke the Sanctum for LOW-risk changes.

---

## Constitutional constraints

Polaris has ten hard constraints (C1–C10) documented in `MISSION.md`.
**These are not policies. They are triggers, CHECK constraints, partial
unique indexes, and append-only audit trails enforced at the database
level.** A PR that violates any of C1–C10 will be refused without
discussion. A PR that adds a new structural invariant gets fast-tracked.

The vocation `MISSION.md §"Vocation"` (anti-coercion) sits above C1–C10.
Changes that strengthen anti-coercion are welcomed. Changes that move
the system toward becoming a coercion vector (centralized surveillance,
unbounded data retention, cross-individual aggregation primitives) will
be refused on sight.

---

## Risk classes

`meta/autonomy-architecture.md` defines three risk classes:

- **LOW** — additive, reversible, single-surface. Doc, test, ai-script
  refactor, isolated bug fix.
- **MEDIUM** — multi-surface, requires regression coverage, may change
  documented behavior.
- **HIGH** — touches the cognitive layer itself, the constitutional
  constraints, or the agent's autonomy boundaries.

LOW PRs follow the Quick path. MEDIUM PRs need a proposal in
`proposals/`. **HIGH PRs require a Sanctum session** — see below.

---

## The Sanctum protocol

For MEDIUM/HIGH-risk strategic decisions — opening a new arc, modifying
the cognitive layer, changing what Polaris IS or IS NOT — open a Sanctum
session:

```bash
./scripts/ai-sanctum.sh open <topic>
# ... agent records positions; operator decides; agent ships ...
./scripts/ai-sanctum.sh close <topic> --position A --decision ...
```

Full spec: `meta/sanctum-protocol.md`. Index of all past sessions:
`meta/sanctum-index.md`. Sanctum sessions live in `sanctum/` and are
themselves a filesystem audit-of-record instance.

When proposing a HIGH-risk change as an external contributor, file an
issue first with the Sanctum invocation request. The agent will draft
Architect + Anti-Architect positions; VANTA decides; the resulting
Sanctum file is the constitutional record.

---

## Test discipline

```bash
./scripts/ai-test.sh              # full suite
./scripts/ai-test.sh quick        # skip slow concurrency/property tests
./scripts/ai-done.sh              # pre-ship 10-check gate
```

A PR is not ready to merge if any of the following hold:

- Any test in `polaris_web/test_app.py` fails.
- Any Hypothesis property test in `test_invariants_property.py` fails.
- Any structural invariant in `test_structural_invariants.py` fails.
- Any SQL self-test in `polaris_sql/08_tests.sql` fails.
- `./scripts/ai-link-check.sh --ci` finds broken links.
- `./scripts/ai-done.sh` returns a non-zero exit code.

For new features, add at least one new test that would fail in the
absence of your change. For new structural invariants — properties that
must hold across the system — add them to `test_structural_invariants.py`
under a new `TestWaveNN_VNNN` class.

---

## Style

VANTA's standing instructions: read `DEVNOTES/style.md`. Summary:

- Declarative style, no filler.
- "Holy shit, that's done" — no workarounds, no tabling.
- When something feels like cosmic-significance framing instead of
  concrete building, name the pattern and back off.
- Audit-of-record by construction (every shipped instance documented in
  `DEVNOTES/audit-of-record.md`).
- See `DEVNOTES/known-gotchas.md` before debugging anything that feels
  weird; many things that look like new bugs are documented gotchas.

---

## What we will NOT accept

- Banking, payments, transactions, balances, merchant codes. C10
  ("Identity is not money") is constitutional. Build that on top of
  Polaris as a separate consumer over the HTTP boundary; do not merge it
  in.
- Cross-individual aggregation, link analysis, predictive scoring, or
  any surveillance primitive. v9.19 ontology refused these patterns
  explicitly with a regression guard.
- Inline JavaScript in templates. CSP enforces `script-src 'self'`
  with no `'unsafe-inline'`; external `static/*.js` files are the
  pattern. See gotcha #5 in `CLAUDE.md`.
- Adding a fourth uniqueness-pattern convention (we have `uq_*` and
  `idx_*`; match the surrounding convention).
- Documentation prose generated without reading the codebase. The
  Architect + Anti-Architect protocol exists to catch this; see
  `meta/architect.md` § "The Architect's shadow" (8 anti-patterns).

---

## Reporting security issues

Do NOT file a public issue for security vulnerabilities. See
`SECURITY.md` (top-level) for the disclosure policy.

---

## Communication

Polaris is maintained primarily through agent-operator collaboration. The
typical flow:

1. Operator (VANTA) names a need or pastes an error.
2. Agent (Claude) surfaces options + opens a Sanctum if MEDIUM/HIGH.
3. Operator authorizes a position.
4. Agent ships the implementation + tests + documentation in one pass.
5. Pattern #20 Constitutional Discipline records the cycle.

For external contributors, file an issue describing the need in concrete
terms, including the constraint or vocation alignment. Acknowledge
that the Sanctum protocol governs MEDIUM/HIGH decisions; you cannot
bypass it by submitting a large PR cold.

---

## License

See `LICENSE` (top-level). Polaris is a reference implementation; using
it as the basis for a production identity system is encouraged provided
the constitutional constraints (C1–C10) are not weakened in derivative
deployments.

VANTA's preference is that derivative deployments document themselves
to the same audit-of-record standard. This is a preference, not a
license condition.

---

*Maintainer: VANTA / Egor Khaklin*
*Cognitive-layer agent: Claude (Anthropic)*
*Last updated: 2026-05-15 (v9.23)*
