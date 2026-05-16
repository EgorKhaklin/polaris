# docs/CONVENTIONS.md — naming + structural conventions

The implicit conventions that make Polaris's structure coherent,
named explicitly so future contributors (and future agents) can
follow them without re-deriving.

If the convention isn't named here, it isn't a convention — it's
just an emergent pattern. Codify or change.

---

## 1. Top-level directory naming

**Pattern:** `polaris_<domain>/` for Python packages and the SQL bundle;
unprefixed nouns for everything else.

| Pattern | Example | Why |
|---|---|---|
| `polaris_<domain>/` | `polaris_web/`, `polaris_sql/`, `polaris_hydra/`, `polaris_swarm/`, `polaris_zk/`, `polaris_cli/` | Python package convention; namespaced; unambiguous when `pip install`'d |
| Unprefixed singular | `assets/`, `journal/` | Doesn't grow plural ("we have 1 logo" / "we have 1 journal-stream") |
| Unprefixed plural | `docs/`, `scripts/`, `meta/`, `patterns/`, `proposals/`, `sanctum/`, `archives/`, `DEVNOTES/` | Container of similar items |
| ALL_CAPS | `DEVNOTES/` | Historical (v8.x); preserved per v8.20 AoR |

**Rule:** never rename a top-level directory without a Sanctum
(touches v8.20 AoR + thousands of cross-references).

---

## 2. Top-level file naming

**Pattern:** `ALL_CAPS.md` for constitutional docs; `Title.md` for
governance docs; `lowercase.<ext>` for everything else.

| Pattern | Example | What |
|---|---|---|
| `ALL_CAPS.md` | `MISSION.md`, `ROADMAP.md`, `CHANGELOG.md`, `LICENSE`, `NOTICE` | Constitutional / legal — the load-bearing docs |
| `Title.md` | `README.md`, `CLAUDE.md` | Conventional + agent-runbook |
| `lowercase.ext` | `polaris_mac_launch.sh`, `Polaris.command` | Executables (note: `Polaris.command` is the macOS double-click convention) |
| Hidden | `.gitignore`, `.pre-commit-config.yaml`, `.github/`, `.git/` | Tooling config |

---

## 3. Script naming

| Family | Pattern | Read by |
|---|---|---|
| Cognitive layer | `scripts/ai-<verb>.sh` | Agents (Claude) |
| Operator layer | `scripts/polaris-<verb>.sh` | Humans (operators) |
| Helpers | `scripts/<name>.py` | Other scripts (shell-out) |

**Rule:** every script's first comment block (after shebang) is
the doc-comment that `ai-help.sh` parses. Format:

```bash
#!/bin/bash
# =============================================================================
# scripts/<name>.sh — <one-line purpose>
#
# <multi-paragraph context>
#
# Usage:
#     <name>.sh [--flag] [--another-flag VALUE]
#
# Exit codes:
#   0  success
#   2  usage error
#   3  <specific failure>
# =============================================================================
```

Exit codes are NAMED in the script body:
```bash
EXIT_OK=0
EXIT_USAGE=2
EXIT_SHA_MISMATCH=4
```

---

## 4. Python package layout

```
polaris_<domain>/
├── README.md                # required (audited by ant_readme_counts)
├── __init__.py              # may be empty; package marker
├── <module>.py              # one module per concept; lowercase + _-separated
└── <subpkg>/
    ├── README.md            # required for any subpkg
    ├── __init__.py
    └── <module>.py
```

**Rules:**
- Every top-level package has a README.md
- Every subpkg has a README.md
- `test_<module>.py` is colocated with the module under test (or
  cross-referenced in the module's docstring if not — `ant_test_gap`
  surfaces violations)

---

## 5. SQL files

`polaris_sql/` follows the `NN_<purpose>.sql` numeric prefix
convention so `00_load_all.sql` can `\i` them in order:

```
00_migrations_table.sql       # FIRST — the schema_version registry (v8.95)
00_load_all.sql               # entry point — \i each file in order
01_schema.sql                 # DDL (tables + constraints)
02_indexes.sql                # indexes (incl. R10-2/R11-* indexes)
03_view.sql                   # views
04_data.sql                   # sample data
05_procedures.sql             # UC-1..UC-12 + helpers
06_triggers.sql               # append-only + state-machine triggers
07_queries.sql                # analytical queries
08_tests.sql                  # SQL self-tests (sections A-R)
09_grants.sql                 # role + grants
10_auth.sql                   # AppUser + auth seed
11_atlas.sql                  # v6 atlas + filter functions
12_v7_constraints.sql         # v7 schema-hardening
13_postgis.sql                # optional-dependency PostGIS
13_substrate.sql              # SystemDependency view (M2-3)

migrations/                   # paired up/down per v8.95 framework
├── README.md
└── <YYYY-MM-DD-NNN-slug>.{up,down}.sql
```

---

## 6. Test files

| Path | Scope |
|---|---|
| `polaris_web/test_app.py` | App-level + route tests |
| `polaris_web/test_check_constraints.py` | SQL CHECK constraint regression |
| `polaris_web/test_structural_invariants.py` | Project-wide structural pins |
| `polaris_web/test_invariants_property.py` | Hypothesis property tests (C1/C2/C3) |
| `polaris_web/test_redaction_property.py` | M2-12 redaction-proof property tests |
| `polaris_web/test_hydra_revamp.py` | v9.04 modules unit tests |
| `polaris_web/test_hydra_property.py` | v9.06 / E2 Hypothesis property tests |
| `polaris_cli/test_cli.py` | CLI tests |

**Test class naming:** `TestPascalCaseDescriptor` (e.g.,
`TestArcBProductionDeploymentStack`). For per-ship invariants:
`Test<ShipID><ShipFeatureName>` (e.g., `TestWave3V907`).

**Test function naming:** `test_snake_case_descriptor`.

---

## 7. Sanctum sessions

Path: `sanctum/<YYYY-MM-DD>-<short-slug>.md`.

**Required structure** (per `meta/sanctum-protocol.md`):
- Frontmatter: Date, Petitioner, Principal, Trigger, Risk class, Status
- §I The Matter
- §II The architect's positions (≥2; ≤4)
- §III Architect's recommendation
- §IV Open questions for VANTA (resolutions if architect-recommended)
- §V Decision (when DECIDED)
- §VI Outcome (records + cross-references; when shipped)
- §VII Cross-references

**Status field values:**
- `OPEN` — awaiting decision
- `DECIDED` — Position selected, not yet shipped
- `DECIDED + CLOSED` — shipped; §VI Outcome filled
- `REJECTED` — declined; preserved per v8.20

**v8.20 AoR pin:** every Sanctum session is filesystem-AoR; `meta/sanctum-index.md` is the chronological index; both never auto-deleted.

---

## 8. Journal entries

Path: `journal/<YYYY-MM-DD>.md` (per-day flat-list).
Optional: `journal/<YYYY-MM-DD>-architect.md` (Architect brief; via `ai-architect.sh --save`).
Optional: `journal/hydra/<YYYY-MM-DD>-<HHMM>.md` (HYDRA brief; via `ai-hydra.sh --full --save`; v9.04+).

**Entry format:**
```markdown
- **decision** HH:MM — <ship-version SHIPPED — title; risk class; description>
- **learning** HH:MM — <what was learned + cross-ref>
- **bug** HH:MM — <bug found + fix landed>
```

`ai-journal.sh` provides the canonical entry interface.

---

## 9. CHANGELOG entries

`CHANGELOG.md` at repo root. New entries at TOP of file (newest first).

**Header format:**
```markdown
## v<N.NN> — <YYYY-MM-DD> (<one-line title with sections separated by ·>)
```

**Body sections** (when applicable):
- **Risk class:** LOW / MEDIUM / HIGH (composite or specific)
- **Why this ship:** the directive that triggered it
- **Source:** Sanctum reference if applicable
- Per-item subsections with structural invariant counts
- **Constitutional preservation** verified
- **Live drill** verified
- `POLARIS_VERSION` bump line

**v8.20 AoR pin:** old CHANGELOG entries are NEVER edited
retroactively. Corrections land as new entries cross-referencing
the prior.

---

## 10. node_id format (Pheromone substrate)

`<domain>:<key>` — colon-prefixed. Used by ants + soldiers when
depositing Pheromones; HYDRA's CorrelationEngine splits on `:` for
domain-prefix matching (Strategy 2).

Canonical domains (see `DEVNOTES/hydra-pheromone-integration.md`
for the full table):
- `route:` — HTTP routes
- `schema:` — DB tables
- `infra:` — infrastructure (logs, db, routes)
- `cognitive:` — cognitive layer (sanctum, hydra_brief)
- `swarm:` — swarm cohort (commander, soldier)
- `civitas:` — citizen layer (treasury, census)
- `mission:` — mission-doc surfaces
- `build:` — build artifacts (reserved)

**Historical (kept for backwards-compat; new code prefers canonical):**
- `file:`, `module:`

---

## 11. Versioning

`POLARIS_VERSION` lives in [`polaris_web/__version__.py`](../polaris_web/__version__.py)
(canonical source as of v9.06 / C5). Format: `MAJOR.MINOR` (e.g., `9.08`).

**Bump procedure** (codified in `__version__.py` doc-comment):
1. Edit `__version__` literal
2. Add CHANGELOG entry
3. Add CLAUDE.md state-map row
4. Add journal entry
5. Run final verification

---

## 12. Documentation cross-references

**Markdown links must resolve.** `bash scripts/ai-link-check.sh`
walks every Markdown link of shape `[text]` followed by `(path)` and
confirms target exists. CI runs this on every push.

**Cross-references prefer relative paths:**
- `[X](../meta/architect.md)` — relative ✓
- `[X](/Users/vanta/Desktop/polaris/meta/architect.md)` — absolute ✗
- `[X](https://github.com/.../meta/architect.md)` — URL ✗ (would
  rot when fork count grows)

**Cross-arc references are typed:**
- "Sanctum-decided in `sanctum/2026-05-14-<topic>.md`" (placeholder format; real refs use real paths)
- "v8.95 (CHANGELOG) — schema migration framework"
- "v9.04 / Wave 1 / A1" — for ship + wave + item identification

---

## 13. Em-dashes

**Forbidden in own-prose Markdown** per `DEVNOTES/style.md` (VANTA
standing instruction). The `em-dash-warn` pre-commit hook surfaces
violations informationally.

**Allowed exceptions:**
- CHANGELOG entries (audit-of-record; can't be retroactively
  edited per v8.20)
- journal/ entries (already-shipped historical record)
- Direct quotes from VANTA / external sources

**Substitutes:** `:` (colon), `,` (comma), `(` `)` (parens),
sentence break.

---

## 14. Comments + docstrings

**Code comments default to none.** Only add a comment when the WHY
is non-obvious: a hidden constraint, a subtle invariant, a
workaround for a specific bug, behavior that would surprise a
reader.

**Don't:**
- Explain what the code does (the code does that)
- Reference the current task ("added for the X flow")
- Reference callers ("used by module Y")

**Do:**
- Reference the constitutional source ("per v9.05 / A1 — F5
  soldier exemption")
- Reference the Sanctum if the choice was Sanctum-decided
- Name the surprising-to-a-reader fact ("SET LOCAL evaporates at
  COMMIT — that's intentional carve-out closure")

---

## 15. Backwards-compat removals

**When deleting code that may have callers:**

1. Sanctum if MEDIUM/HIGH-risk
2. Add a CHANGELOG entry under the deletion ship
3. Add a structural invariant pinning the deletion if the deletion
   is itself load-bearing
4. Update `meta/sanctum-index.md` if Sanctum-decided
5. NEVER silently delete from CHANGELOG/sanctum/journal/treasury-
   roll — those are v8.20 AoR

---

## 16. Where these conventions live

This file (`docs/CONVENTIONS.md`) is the single source of truth.
Changes happen here, then propagate by reference. Other docs that
mention conventions cross-reference here rather than redefining.

For the project-wide architecture map, see [`reference/SYSTEM-MAP.md`](reference/SYSTEM-MAP.md).

For the constitutional principles beneath these conventions, see
[`story/PRINCIPLES.md`](story/PRINCIPLES.md).
