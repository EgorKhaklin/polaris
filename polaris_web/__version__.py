"""polaris_web/__version__.py — single canonical version string.

v9.06 / Wave 2 / C5 — Sanctum-equivalent:
`meta/polaris-self-roadmap-2026-05-14.md` item C5.

Pre-v9.06 the version literal lived only in `polaris_web/app.py:138`
(`POLARIS_VERSION = '9.05'`) — bumped manually each ship. References
spread across ai-status.sh greps, `/api/health`, CHANGELOG narrative,
Dockerfile labels. No invariant ensured the literal stayed in sync
across surfaces.

v9.06 promotes the version to its own module. `app.py` imports from
here; future surfaces (CLI, Dockerfile labels, OpenAPI docs, etc.)
also import from here. The structural invariant
`test_polaris_version_is_canonical` asserts `app.py` imports rather
than redefines.

The string format is `MAJOR.MINOR` — same as before. Never modify
historical CHANGELOG entries to match a future bump (per v8.20 audit-
of-record discipline; old entries are frozen).

Bump procedure:
    1. Edit `__version__` below
    2. Add CHANGELOG entry under `## v<NEW> — <date> (...)`
    3. Add CLAUDE.md state-map row at top of "Recent ships"
    4. Add journal entry for the date
    5. Run final verification (tests + link-check + meta + coherence)
"""

__version__: str = "9.56"


# Backwards-compat alias for code that imported `POLARIS_VERSION`
# directly from app.py before the v9.06 promotion. Both names point
# at the same string; the structural invariant rejects any
# divergence.
POLARIS_VERSION: str = __version__
