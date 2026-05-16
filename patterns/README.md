# patterns/

Chunked recipes for recurring task shapes. The brain analog is
**procedural chunking** — when a chess master sees a board, they don't
compute moves from first principles; they recognize "this is a
king-side attack pattern" and execute a learned response.

Each pattern file is:
- a short **trigger** description (when this pattern applies)
- the **canonical sequence** of steps (with file paths)
- **pre-known gotchas** for this specific pattern
- the **completion check** (how I know I'm done)

When `ai-recall.sh` matches a query against a pattern filename, it
surfaces the pattern. When `ai-where.sh` runs against a file that's
within a pattern's scope, it surfaces the pattern.

---

## Available patterns

| Pattern                        | Triggers                                            |
|--------------------------------|-----------------------------------------------------|
| `add-flask-route.md`           | "add endpoint", "new route", "expose X via API"     |
| `add-list-page-pagination.md`  | "list page slow", "X 2M rows", route returns table  |
| `add-sql-aggregation.md`       | "aggregate", "cluster", "summary", performance work |
| `concurrency-fix.md`           | "race", "TOCTOU", parallel, locked, atomic          |
| `decomposition-targets.md`     | "how many sections?", "is this list complete?", chunking |
| `new-uc-procedure.md`          | "use case", "UC-N", new stored procedure            |
| `scaling-investigation.md`     | "slow query", "EXPLAIN", "p95 latency", N rows      |
| `schema-change.md`             | "add column", "new table", "alter constraint"       |
| `security-fix.md`              | "CSP", "XSS", "CSRF", "lockout", "rate limit"       |
| `visual-feature-on-atlas.md`   | "atlas globe", "reticle", "HUD", "filter chip"      |

The pattern catalog complements `scripts/ai-pattern.sh` — that script
holds the 22-element *failure-mode* catalog (Greenfield, Composition,
HiddenState, …) for shape-recognition. This directory holds
**procedural recipes**: step-by-step playbooks for known
Polaris-specific task shapes.

---

## Adding a new pattern

If you do something three times, write the pattern. Format:

```markdown
# patterns/my-pattern.md

## Trigger
When user says: ...
Or when file changes touch: ...

## Recipe
1. ...
2. ...
3. ...

## Pre-known gotchas
- ...

## Completion check
- [ ] tests pass
- [ ] docs updated
- [ ] ...
```

Then update the table above so `ai-recall.sh` can find it.
