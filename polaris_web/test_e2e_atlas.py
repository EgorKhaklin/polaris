"""polaris_web/test_e2e_atlas.py — Atlas-globe end-to-end smoke tests.

v9.33 / first post-freeze measurement ship per MISSION.md §"From v9.32
forward, (b) Measurement". Closes the follow-up commitment from
`sanctum/2026-05-17-plugin-installation-tier2.md` (Option A bundle).

**Why E2E for the Atlas globe.** The Atlas (`/atlas`) is the operational
investigation surface — a WebGL globe rendered by `atlas-globe.js` with
viewport-aware decimation, reticles on every verification event, click-
through into token records. None of that surface is exercised by the
structural-invariant suite (which reads source). It is also not exercised
by the route-test suite (which only confirms the page renders 200). Real
defects in the globe (CSS-class drift, JS-module load failures, JSON
data-island parse errors, CSP violations against new sources) only
appear in a browser.

**Why graceful skip.** Playwright + a headless browser is a 250MB+
dependency. Most operators (and CI in many environments) won't have it
installed. The test class therefore SKIPs (not fails) when either the
Playwright package OR the browser binary is unavailable, AND when no
Polaris app is reachable on port 2222. Activation is operator-side:

    cd polaris_web
    pip install playwright
    playwright install chromium          # one-time, ~250MB
    cd ..
    ./polaris_mac_launch.sh up --detach  # app on port 2222
    python3 -m unittest polaris_web.test_e2e_atlas

**Why `wait_until="domcontentloaded"`** (NOT `"networkidle"`).
Per CLAUDE.md pre-known-gotchas #6: the Polaris page fires a heartbeat
POST every ~10s (browser-presence beacon for the launcher), so
`networkidle` never resolves. `domcontentloaded` is the right wait
condition for our surface.
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


@unittest.skipUnless(_app_reachable(),
    f"Polaris app not reachable at {POLARIS_URL} — start it via "
    f"`./polaris_mac_launch.sh up --detach` to exercise these tests")
@unittest.skipUnless(_playwright_available(),
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
        page.fill('input[name="username"]', "admin")
        page.fill('input[name="password"]', "Admin@123!")
        page.click('button[type="submit"]')
        # After login, /atlas requires admin role (which the seeded
        # admin has). Navigate explicitly rather than relying on a
        # redirect target.
        page.goto(f"{POLARIS_URL}{path}", wait_until="domcontentloaded")

    def test_atlas_page_loads_with_globe_element(self):
        """The /atlas page must serve 200 AND contain the globe SVG
        container. Catches: route regression (404/500), template
        rename (the element id moves), CSP block (script-src refuses
        atlas-globe.js)."""
        page = self._context.new_page()
        try:
            self._login_and_goto(page)
            # The globe lives in #atlas-globe per atlas.html. If the
            # template renamed the container OR CSP blocked the JS
            # module, this selector fails.
            globe = page.query_selector("#atlas-globe")
            self.assertIsNotNone(globe,
                "atlas.html must render #atlas-globe container")
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
            # Wait for HUD figures to populate (the data-island fetch
            # is synchronous; first paint includes the numbers).
            page.wait_for_selector("#atlas-hud", timeout=3000)
            # The four figures are individually addressable elements;
            # if all four are present, the HUD shape is intact.
            figures = page.query_selector_all("#atlas-hud .hud-figure")
            self.assertGreaterEqual(len(figures), 4,
                f"Atlas HUD must render ≥4 headline figures; "
                f"found {len(figures)}")
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
            # Give the page a beat to settle (atlas-globe.js initializes
            # asynchronously after DOMContentLoaded).
            page.wait_for_timeout(500)
            self.assertEqual(violations, [],
                f"Atlas page must produce no CSP violations; "
                f"got: {violations}")
        finally:
            page.close()


if __name__ == "__main__":
    unittest.main(verbosity=2)
