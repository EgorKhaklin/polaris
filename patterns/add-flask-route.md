# patterns/add-flask-route.md

## Trigger

- "add an endpoint", "expose X via HTTP"
- "I need a new route for Y"
- "API for Z"

## Recipe

### 1. Decide: HTML page, JSON API, or form?

| Type | URL prefix | Auth | Returns |
|---|---|---|---|
| HTML page (`tokens_list`, `dashboard`) | `/something` | `@security.login_required` | `render_template(...)` |
| JSON API (`/api/atlas/...`) | `/api/...` | `@security.login_required` | `jsonify(...)` |
| Form action (issue, transition) | `/uc1/issue`, `/tokens/.../transition` | `@security.login_required + @security.require_role + @security.csrf_protect` | `redirect()` |

### 2. Find the right insertion point

Routes are grouped in `app.py` by entity. Search for the section
header that matches your concern:

```bash
grep -n "^# ====.*=====" polaris_web/app.py
```

Add the new route inside the appropriate section. Don't sprinkle
random routes around the file.

### 3. Write the route

Skeleton for a JSON API endpoint:

```python
@app.route('/api/foo/bar')
@security.login_required
def api_foo_bar():
    """One-line description of the endpoint."""
    try:
        # Validate inputs — raise ValueError with a CLEAN error message
        # for anything bad. Don't let bad input reach SQL.
        param = request.args.get('param', '')
        if not param:
            raise ValueError("param is required")
    except ValueError as e:
        return jsonify(error=str(e)), 400

    rows = query("""
        SELECT col_a, col_b, col_c
        FROM SomeTable
        WHERE …
        LIMIT %s
    """, (LIMIT_CONST,))

    return jsonify(
        param=param,
        count=len(rows),
        items=[dict(r) for r in rows],
    )
```

Skeleton for a paginated list page:

```python
@app.route('/things')
@security.login_required
def things_list():
    page      = max(1, int(request.args.get('page', '1')))
    page_size = min(500, max(10, int(request.args.get('page_size', '100'))))
    offset    = (page - 1) * page_size

    rows = query("""
        SELECT … FROM Thing ORDER BY thing_id LIMIT %s OFFSET %s
    """, (page_size + 1, offset))
    has_next = len(rows) > page_size
    rows = rows[:page_size]

    return render_template('things_list.html',
        rows=rows, page=page, page_size=page_size,
        has_next=has_next, has_prev=page > 1)
```

The template uses the shared `_pager.html` macro:
```jinja
{% from "_pager.html" import render_pager %}
…
{{ render_pager(page, has_prev, has_next, page_size) }}
```

### 4. Hard caps + bounds check

Any limit/page_size from the user must clamp to a sane upper bound.
JSON arrays bigger than ~5000 elements lock up browsers; HTML tables
bigger than ~1000 rows are unscrollable.

Constants in `app.py`:
```python
_ATLAS_MAX_CLUSTERS = 5000
_ATLAS_MAX_POINTS   = 2000
_ATLAS_MAX_EVENTS   = 500
```

Match the convention if your endpoint is similar.

### 5. Test it

Add tests to `test_app.py` in the appropriate test class. Minimum:
- Authenticated 200 with sane args
- 401/302 for unauthenticated access
- 400 for bad input (each validation branch)
- Hard cap respected when user requests N > cap

### 6. CHANGELOG entry

Add a one-line entry under the current version section.

## Pre-known gotchas

- **CSRF**: state-changing routes (POST that mutates DB) need
  `@security.csrf_protect`. The form template must include `<input
  type="hidden" name="csrf_token" value="{{ csrf_token() }}">`.
- **CSP**: don't add inline `<script>` tags to templates. The CSP is
  `script-src 'self'`. Use external `.js` files only.
- **psycopg2 RealDictCursor** is configured at the connection level;
  `query()` returns dicts, not tuples. Don't index by integer.
- **Errors** propagate to the user via `db_error_to_message()` which
  redacts internal detail. If your error needs to be user-readable,
  raise a clean `ValueError` BEFORE calling SQL.
- **Routes that return HTML** must set `Cache-Control: no-store` for
  authenticated content (already done globally in `secure_headers`).

## Completion check

- [ ] Route follows the section grouping in `app.py`
- [ ] Auth decorator(s) applied
- [ ] Inputs validated; bad input returns 400 with clean message
- [ ] Hard cap on any list-shaped output
- [ ] Tests for: 200, auth gate, validation 400s, cap respected
- [ ] If state-changing: CSRF protected and tested
- [ ] CHANGELOG one-liner added
