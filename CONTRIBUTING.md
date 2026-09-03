# Contributing to Polaris

Polaris is a national identity token system reference implementation. It is
maintained as a coherent single-author codebase by Egor Khaklin / VANTA,
with the assistance of Claude (the agent), working session by session
against `MISSION.md`. Contributions are welcome, but this is not
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
- Small fixes do not need a design discussion first.

---

## Constitutional constraints

Polaris has ten hard constraints (C1–C10) documented in `MISSION.md`.
**These are not policies. They are triggers, CHECK constraints, partial
unique indexes, and append-only audit trails enforced at the database
level.** A PR that violates any of C1–C10 will be refused without
discussion. A PR that adds a new check to `polaris_checks` gets fast-tracked.

The vocation `MISSION.md §"Vocation"` (anti-coercion) sits above C1–C10.
Changes that strengthen anti-coercion are welcomed. Changes that move
the system toward becoming a coercion vector (centralized surveillance,
unbounded data retention, cross-individual aggregation primitives) will
be refused on sight.

---

## Change review

Changes are sized by blast radius:

- **Small**: docs, tests, a dev-script tweak, an isolated bug fix. Follow the
  Quick path above: open an issue, submit a focused PR with a clear before/after.
- **Substantive**: multi-surface work, new behavior, or anything touching the
  schema, the security boundary, or the C1-C10 constraints. Open an issue first
  describing the change and its constraint/vocation alignment; the maintainer
  reviews the approach before you build it.

---

## Test discipline

```bash
./scripts/ai-test.sh              # full suite
./scripts/ai-test.sh quick        # skip slow concurrency/property tests
./scripts/ai-done.sh              # pre-ship gate
```

A PR is not ready to merge if any of the following hold:

- Any test in `polaris_web/test_app.py` fails.
- Any Hypothesis property test in `test_invariants_property.py` fails.
- Any check in `polaris_checks` fails (`python3 -m polaris_checks.run`).
- Any SQL self-test in `polaris_sql/08_tests.sql` fails.
- `./scripts/ai-link-check.sh --ci` finds broken links.
- `./scripts/ai-done.sh` returns a non-zero exit code.

For new features, add at least one new test that would fail in the
absence of your change. For a new constitutional invariant: a property
that must hold across the system: add a `check_*` to
`polaris_checks/checks.py` with a detection test in
`polaris_checks/test_checks.py`.

---

## Pre-commit hooks

`.pre-commit-config.yaml` at the repo root wires a fast local safety net.
CI (`.github/workflows/ci.yml`) runs the full suite on every push and PR;
the hooks catch the common regressions before a commit leaves the clone.
Every hook is a `repo: local` entry (no network) and is also runnable by
hand from `scripts/`.

Install once per clone:

```bash
pip install pre-commit        # in the dev venv
pre-commit install            # writes .git/hooks/pre-commit
```

What runs on every commit:

| Hook | What it does |
|---|---|
| `polaris-checks` | `python3 -m polaris_checks.run`, the flat C1-C10 invariant layer; non-zero on any FAIL |
| `ai-link-check` | `bash scripts/ai-link-check.sh --ci`, every Markdown link and code path must resolve |
| `no-secret-in-prod-compose` | refuses a literal `POLARIS_SECRET_KEY:` value in `polaris_web/docker-compose.prod.yml` |
| `em-dash-block-new` | refuses a new em-dash on a staged line of `CLAUDE.md`, `MISSION.md`, `ROADMAP.md`, `README.md`, or `CONTRIBUTING.md` (`DEVNOTES/style.md`); `CHANGELOG.md` is exempt as audit-of-record |

Run the whole set by hand:

```bash
pre-commit run --all-files
```

Upstream `repos:` entries (ruff, black, and the like) are a contributor's
local choice; the committed configuration stays local-only so it works in a
clone with no network.

---

## Style

VANTA's standing instructions: read `DEVNOTES/style.md`. Summary:

- Declarative style, no filler.
- "Holy shit, that's done": no workarounds, no tabling.
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
- A third index-naming convention (we have `uq_*` and `idx_*`; match the
  surrounding one).
- Documentation prose generated without reading the codebase. Every doc
  claim must be traceable to the code or schema it describes.

---

## Reporting security issues

Do NOT file a public issue for security vulnerabilities. See
`SECURITY.md` (top-level) for the disclosure policy.

---

## Communication

Polaris is maintained by a single author with AI assistance. For a
substantive change, the typical flow is:

1. Open an issue describing the need in concrete terms, including its
   constraint or vocation alignment.
2. The maintainer surfaces options and tradeoffs and picks a direction.
3. The change ships in one pass: implementation, tests, and documentation
   together.

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

*Maintainer: Egor Khaklin (VANTA), with Claude as the working agent.*
*Last updated: 2026-09-02 (v9.200)*
