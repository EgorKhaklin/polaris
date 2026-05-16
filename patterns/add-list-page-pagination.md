# patterns/add-list-page-pagination.md

## Trigger

- A `/something` route returns `<table>` with `{% for r in rows %}` over an unbounded query
- "list page slow", "table OOMs the browser"
- New table approaching 10k+ rows
- Endpoint exists that does `SELECT * FROM Big ORDER BY x` with no LIMIT

## Recipe

### 1. Pick the pagination strategy

| Strategy | When to use |
|---|---|
| **OFFSET** (`LIMIT N OFFSET (page-1)*N`) | Random page jumps required. Acceptable to ~page 100. |
| **Cursor / keyset** (`WHERE col > last_seen ORDER BY col LIMIT N`) | Default for list pages with deep paging. Append-only feeds. No random page jumps. |
| **Time-bucket** (`WHERE created BETWEEN day_a AND day_b`) | Audit logs, time-series with predictable density |

For Polaris (v7.4+): `/tokens` and `/verifications` support **both modes** — cursor is preferred and rendered by the pager; page mode is back-compat for bookmarked URLs. `/api/atlas/events` uses cursor exclusively. Match the precedent unless you have a reason.

Single-column vs composite cursor:
- Use a **single-column** cursor when the sort key is itself unique (a primary key, or a strictly-monotonic timestamp). `/tokens` uses `token_id`.
- Use a **composite** cursor (`ts~id` or similar) when the leading sort column can have ties. `/verifications` orders by `(event_timestamp, event_id)` because two events can share a timestamp; a single-column cursor on timestamp would silently drop or duplicate boundary rows. Encode as `f"{ts.isoformat()}~{id}"` and decode with `(datetime.fromisoformat, int)`.

### 2. Add the pagination params (route)

**Page mode (legacy / quick implementation):**

```python
@app.route('/things')
@security.login_required
def things_list():
    page      = max(1, int(request.args.get('page', '1')))
    page_size = min(500, max(1, int(request.args.get('page_size', '100'))))
    offset    = (page - 1) * page_size

    # Build WHERE conditions for filters first
    where_sql = ''
    params = []
    if some_filter:
        where_sql += ' AND col = %s'
        params.append(some_filter)

    # Fetch one EXTRA row to detect next page without count(*)
    sql = """
        SELECT … FROM Thing
        WHERE TRUE """ + where_sql + """
        ORDER BY thing_id
        LIMIT %s OFFSET %s
    """
    rows = query(sql, params + [page_size + 1, offset])
    has_next = len(rows) > page_size
    rows = rows[:page_size]

    return render_template('things_list.html',
        rows=rows,
        page=page, page_size=page_size,
        has_next=has_next, has_prev=page > 1)
```

The `LIMIT N+1` trick avoids a `SELECT count(*)` query (which itself
gets slow at 2M rows).

**Cursor mode (preferred for deep-paging tables):**

Replace the OFFSET branch with a keyset walk. Use the helpers in
`app.py` (`_parse_cursor_int`, `_parse_cursor_composite`,
`_format_cursor_composite`) and follow this shape — see
`tokens_list` (`app.py:1297`) and `verifications_list`
(`app.py:1644`) for full working examples that handle both modes
with cursor-takes-precedence semantics.

```python
cursor_raw      = request.args.get('cursor')
prev_cursor_raw = request.args.get('prev_cursor')
cursor_mode = (cursor_raw is not None) or (prev_cursor_raw is not None)
cursor      = _parse_cursor_int(cursor_raw)
prev_cursor = _parse_cursor_int(prev_cursor_raw)

if cursor_mode:
    if prev_cursor is not None:
        # Walking backward: rows with key < prev_cursor in DESC order,
        # then reverse for display.
        sql = base_select + where_sql + (
            " AND key < %s ORDER BY key DESC LIMIT %s")
        rows = query(sql, params + [prev_cursor, page_size + 1])
        has_prev = len(rows) > page_size
        rows = rows[:page_size]
        rows.reverse()
        has_next = True  # we came from a Next click
    else:
        cursor_sql = ' AND key > %s' if cursor is not None else ''
        cursor_param = [cursor] if cursor is not None else []
        sql = base_select + where_sql + cursor_sql + " ORDER BY key ASC LIMIT %s"
        rows = query(sql, params + cursor_param + [page_size + 1])
        has_next = len(rows) > page_size
        rows = rows[:page_size]
        has_prev = (cursor is not None and rows and
                    query("SELECT 1 FROM ... WHERE key < %s LIMIT 1",
                          params + [rows[0]['key']], fetch='one') is not None)

    first_cursor = rows[0]['key'] if rows else None
    last_cursor  = rows[-1]['key'] if rows else None
    return render_template(..., cursor_mode=True,
                           first_cursor=first_cursor, last_cursor=last_cursor,
                           page=None, has_next=has_next, has_prev=has_prev)
```

### 3. Wire the pager macro into the template

At the top of `templates/things_list.html`:

```jinja
{% extends "base.html" %}
{% from "_pager.html" import render_pager %}
```

At the end (before `{% endblock %}`):

```jinja
{{ render_pager(page, has_prev, has_next, page_size,
                cursor_mode=cursor_mode|default(false),
                first_cursor=first_cursor|default(none),
                last_cursor=last_cursor|default(none)) }}
```

The macro at `templates/_pager.html` handles all the navigation —
preserves filter querystring, disables the prev/next links at
boundaries, and renders cursor links (`?cursor=`, `?prev_cursor=`)
when `cursor_mode=true`, otherwise legacy page links (`?page=N`). The
template fallback `|default(false)` / `|default(none)` keeps page-mode
callers working without naming new kwargs.

### 4. Test it

In `test_app.py`, append to `ListPaginationTests`:

```python
def test_things_list_paginates(self):
    r = self.client.get('/things')
    self.assertEqual(r.status_code, 200)
    self.assertHTML(r, 'pager', 'Page 1')

def test_things_list_clamps_oversize_page(self):
    # page_size > 500 should be clamped silently
    r = self.client.get('/things?page_size=99999')
    self.assertEqual(r.status_code, 200)
```

### 5. CHANGELOG one-liner

Under the current version: "Pagination on `/things` (default 100, max 500)."

## Pre-known gotchas

- **OFFSET is O(offset).** Page 1 = 60 ms; page 1000 = 1.6 s; page 20000 = 13 s. The PostgreSQL planner has to scan past skipped rows. If your users will paginate deep, switch to cursor (or filter narrows the working set first).

- **Cursor on a non-unique sort key duplicates or skips boundary rows.** If two rows share the cursor's value (e.g. two `event_timestamp` rows on the same second), `WHERE col > last_seen` either drops the second one (if you used `>`) or repeats it on the next page (if you used `>=`). Use a composite cursor — encode (timestamp, primary_key) and compare with row-value `(ts, id) < (last_ts, last_id)`. PostgreSQL evaluates the comparison left-to-right and rides a multi-column index in one shot.

- **HTML-entity escapes break round-tripped cursors in tests.** Jinja renders `?a=1&b=2` as `?a=1&amp;b=2` in href attributes. A real browser unescapes; Werkzeug's test_client does NOT — `&amp;` is parsed as `&` followed by `amp;b` (a wrong key). Tests that scrape pager hrefs must `html.unescape()` before passing the URL back through `client.get()`.

- **The `int()` calls will throw on garbage input** like `?page=abc`. Wrap in try/except or use `int(... or '1')` defensively. Currently Polaris lets the 500 happen because the filter chips are the realistic input path.

- **`LIMIT %s OFFSET %s` parameter order matters.** psycopg2 substitutes positionally — `params + [page_size + 1, offset]` not `[offset, page_size + 1]`.

- **Filter querystring preservation** is in the `_pager.html` macro via `request.args.to_dict()`. If you build a custom pager, you must preserve filter params or pagination drops the user's filter on every click.

- **Templates rendering 100 rows of complex HTML still take time.** If individual rows are heavy (lots of joined data, deeply nested elements), even page 1 can be slow. Profile with the browser devtools, not just the API timing.

## Completion check

- [ ] Route accepts `page` and `page_size`; clamps to [10, 500]
- [ ] `LIMIT N+1` trick, `has_next` derived from result length
- [ ] Template imports `_pager.html` and calls `render_pager()`
- [ ] Tests for: renders with pager, clamps oversize page_size
- [ ] CHANGELOG one-liner under current version
