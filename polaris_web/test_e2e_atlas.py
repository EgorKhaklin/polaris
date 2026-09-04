"""polaris_web/test_e2e_atlas.py — Atlas end-to-end smoke tests.

**Why end-to-end for the Atlas.** The Atlas (`/atlas`) is the operational
investigation surface: a MapLibre map rendered by `atlas-map.js`, with
server-side clustering, individual event markers at high zoom, and
click-through into token records. None of that is exercised by the
structural-invariant suite, which reads source, or by the route tests, which
only confirm the page returns 200. The defects that reach this surface are
CSS-class drift, script load failures, JSON data-island parse errors and CSP
violations against a new source, and every one of them needs a real browser to
see. Playwright drives Chromium against a live server; the tests skip, rather
than fail, when Playwright or its browser is not installed.
"""

import os
import socket
import unittest
import urllib.error
import urllib.request


POLARIS_HOST = os.environ.get("POLARIS_E2E_HOST", "localhost")
POLARIS_PORT = int(os.environ.get("POLARIS_E2E_PORT", "2222"))
POLARIS_URL = f"http://{POLARIS_HOST}:{POLARIS_PORT}"


def _app_reachable() -> bool:
    """Return True iff something is listening on POLARIS_PORT AND serves
    the login page (i.e., it's actually Polaris, not just any process on
    that port)."""
    try:
        with socket.create_connection((POLARIS_HOST, POLARIS_PORT), timeout=1):
            pass
    except OSError:
        return False
    try:
        urllib.request.urlopen(f"{POLARIS_URL}/login", timeout=2).read()
        return True
    except (urllib.error.URLError, socket.timeout, OSError):
        return False


def _playwright_available() -> bool:
    """Return True iff `playwright.sync_api` imports AND a chromium
    binary is installed (the `launch()` call fails fast if not)."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return False
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            browser.close()
        return True
    except Exception:
        # Browser not installed, or platform mismatch, or any other launch
        # failure. Treat as "skip" rather than "fail" — operator action
        # required to activate, not a regression.
        return False


_REQUIRE = os.environ.get("POLARIS_E2E_REQUIRE") == "1"
_APP_OK = _app_reachable()
_PW_OK = _playwright_available()


@unittest.skipUnless(_REQUIRE or _APP_OK,
    f"Polaris app not reachable at {POLARIS_URL} — start it via "
    f"`./polaris_mac_launch.sh up --detach` to exercise these tests")
@unittest.skipUnless(_REQUIRE or _PW_OK,
    "Playwright not available — `pip install playwright && "
    "playwright install chromium` to exercise these tests")
class TestAtlasGlobeE2E(unittest.TestCase):
    """Headless-Chromium smoke tests for the Atlas globe surface.

    Three tests; each completes in <5s with a warm browser cache. The
    suite is deliberately small — measurement, not exhaustive coverage.
    Per the v9.27 Anti-Architect constraint on the chaos test: each
    scenario must catch a real failure mode the static suite cannot.
    """

    @classmethod
    def setUpClass(cls):
        if _REQUIRE:
            # CI mode: an unavailable prerequisite is a failure, not a skip.
            if not _APP_OK:
                raise AssertionError(
                    f"POLARIS_E2E_REQUIRE=1 but no Polaris app is reachable "
                    f"at {POLARIS_URL}; the suite must RUN, not skip")
            if not _PW_OK:
                raise AssertionError(
                    "POLARIS_E2E_REQUIRE=1 but Playwright/chromium is "
                    "unavailable; the suite must RUN, not skip")
        from playwright.sync_api import sync_playwright
        cls._playwright = sync_playwright().start()
        cls._browser = cls._playwright.chromium.launch(headless=True)
        cls._context = cls._browser.new_context(
            # Match the launcher's default viewport so the globe sizing
            # matches what a real operator sees.
            viewport={"width": 1280, "height": 800},
        )

    @classmethod
    def tearDownClass(cls):
        cls._context.close()
        cls._browser.close()
        cls._playwright.stop()

    def _login_and_goto(self, page, path: str = "/atlas") -> None:
        """Log in as admin (seeded role from polaris_sql/04_data.sql) +
        navigate to the requested path. Uses `domcontentloaded` per
        gotcha #6 — `networkidle` never resolves because of the 10s
        heartbeat POST."""
        page.goto(f"{POLARIS_URL}/login", wait_until="domcontentloaded")
        # Pages share one browser context, so a previous test's login cookie
        # survives here and /login redirects straight past the form. Filling
        # unconditionally then times out waiting for a field that never
        # renders; only authenticate when the form is actually present.
        if page.query_selector('input[name="username"]'):
            page.fill('input[name="username"]', "admin")
            page.fill('input[name="password"]', "Admin@123!")
            page.click('button[type="submit"]')
        # After login, /atlas requires admin role (which the seeded
        # admin has). Navigate explicitly rather than relying on a
        # redirect target.
        page.goto(f"{POLARIS_URL}{path}", wait_until="domcontentloaded")

    def test_atlas_page_loads_with_map_and_data_island(self):
        """The /atlas page must serve 200 AND contain the MapLibre map
        container plus the JSON data island. Catches: route regression
        (404/500), template rename (the element id moves), CSP block
        (script-src refuses atlas-map.js).

        v9.160: this test originally selected #atlas-globe, which the
        v9.146 MapLibre rewrite renamed to #atlas-map. The suite was
        wired to no CI job, so it rotted unnoticed: exactly the failure
        mode it exists to catch, suffered by the test itself."""
        page = self._context.new_page()
        try:
            self._login_and_goto(page)
            self.assertIsNotNone(page.query_selector("#atlas-map"),
                "atlas.html must render the #atlas-map container")
            self.assertIsNotNone(page.query_selector("#atlas-globe-data"),
                "atlas.html must render the #atlas-globe-data JSON island")
        finally:
            page.close()

    def test_atlas_hud_renders_four_headline_figures(self):
        """The HUD (`#atlas-hud`) must render the four headline figures
        (Active Tokens, Anomalies, Post-Quantum %, Zero-Knowledge %).
        Catches: data-island parse failure (no figures rendered), HUD
        element rename, atlas-stats endpoint regression."""
        page = self._context.new_page()
        try:
            self._login_and_goto(page)
            # The four headline figures ride the data-* hooks the JS
            # updates live (the v9.142 test-pinned-markup contract):
            # rename-resistant in a way class names are not. First paint
            # includes server-rendered values, so no async wait races.
            page.wait_for_selector("[data-atlas-active-tokens]", timeout=3000)
            for hook in ("data-atlas-active-tokens", "data-atlas-failures",
                         "data-atlas-pq-pct", "data-atlas-zk-pct"):
                el = page.query_selector(f"[{hook}]")
                self.assertIsNotNone(el,
                    f"Atlas HUD must render the [{hook}] figure")
                self.assertNotEqual((el.text_content() or "").strip(), "",
                    f"[{hook}] must carry a server-rendered value on first paint")
        finally:
            page.close()

    def test_atlas_page_has_no_inline_script_csp_violations(self):
        """The page must not log any CSP violations to the console.
        Per CLAUDE.md C5 + pre-known-gotcha #5: script-src 'self' is
        load-bearing; any inline `<script>` or event-handler attribute
        triggers a CSP report-uri (or console error). The only
        legitimate inline script is the `application/json` data-island
        at atlas.html:157 (which is type=application/json, not
        executable). Any new inline script-src violation indicates
        someone weakened CSP or added a script tag improperly."""
        page = self._context.new_page()
        violations = []
        page.on("console", lambda msg:
            violations.append(msg.text) if "Content Security Policy" in msg.text
            else None)
        try:
            self._login_and_goto(page)
            # Give the page a beat to settle (atlas-map.js initializes
            # asynchronously after DOMContentLoaded).
            page.wait_for_timeout(500)
            self.assertEqual(violations, [],
                f"Atlas page must produce no CSP violations; "
                f"got: {violations}")
        finally:
            page.close()


if __name__ == "__main__":
    unittest.main(verbosity=2)
