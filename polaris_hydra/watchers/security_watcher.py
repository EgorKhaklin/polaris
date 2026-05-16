"""SecurityWatcher — H4 of Arc D.

Monitors Polaris's security surface from the cognitive layer:

  1. CSP integrity — the literal in `security.py::secure_headers()`
     names `script-src 'self'`, no `'unsafe-inline'` for scripts,
     `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`.
  2. CSRF mechanism — `security.py` exposes `validate_csrf` and
     accepts both the form-field path and the `X-CSRFToken` header
     path (the v8.22 fix).
  3. Rate-limiter health — hits `/api/health` if the app is running
     on the dev port. Graceful: if not reachable, emits `info`,
     not `alert` (the watcher does not require the app to be live).
  4. Role-gating coverage — counts `@security.require_role(...)`
     and `@security.login_required` decorators in `app.py`. Flags
     drift if the count drops below the v8.x baseline.
  5. R6 anti-revealing — greps operator-visible templates for
     `duress` / `compulsion` strings. The /verifications list MUST
     NOT mention duress to non-admin/auditor roles (canonical R6
     audit refinement from R11-5 / v8.24).
  6. Template inline-JS scan (added v8.47) — scans
     `polaris_web/templates/*.html` for inline event-handler
     attributes (`onclick=`, `onsubmit=`, `onchange=`, `on*=`)
     and executable inline `<script>` blocks. Filters allowed
     data-island MIME types (`application/json`, `text/template`,
     similar). Severity: drift (CSP would block at runtime;
     misalignment between policy intent and template implementation).
  7. **Pheromone-context: log_tail signal (v9.04).** Reads recent
     soldier_log_tail deposits via PheromoneReader. If the soldier
     surfaced ERROR-level entries from `/tmp/polaris_app.log` (or
     similar), surfaces them as drift (operator should see them
     alongside the CSP/CSRF static check). The static surface is
     unchanged; the new channel just adds runtime context.

All seven channels are read-only. The watcher does not poke at live
state beyond an optional HTTP GET that times out fast.
"""

from __future__ import annotations

import os
import pathlib
import re
import urllib.error
import urllib.request
from typing import Any

from polaris_hydra.pheromone_reader import PheromoneReader, WINDOW_FAST

from .base import Finding, Watcher, WatcherReport


# Baseline counts pinned at v8.39 by direct observation of the current
# app.py. The watcher flags any DROP below these values, since drops
# indicate a route may have lost its auth gate. Increases are fine
# (more gating, not less).
ROLE_GATE_BASELINE = {
    "@security.login_required":    47,  # observed at v8.39
    "@security.require_role":      25,  # observed at v8.39
}

# Templates that operators see. R6 says these MUST NOT mention duress
# in *rendered* output (i.e., the user-visible text on screen).
# - duress_queue.html / nav link to /duress → admin/auditor only, by design
# - verifications_form.html → MUST have a duress_code form field
#   (the v8.24 mechanism design); the visible label is neutral
#   ("Holder verification code"), but the field's `name=` attribute
#   IS `duress_code` (the backend needs that to read the value, and
#   form `name=` attributes are not part of the rendered text). The
#   watcher's R6 scan therefore exempts this file with a documented
#   rationale; all OTHER operator-visible templates must be clean of
#   duress/compulsion mentions in BOTH rendered text and source.
OPERATOR_VISIBLE_TEMPLATES = [
    "verifications_list.html",
    # verifications_form.html — exempted; see comment above
    "tokens_list.html",
    "individuals_list.html",
    "agencies_list.html",
    "uc1_issue.html",
    "uc4_activate.html",
    "uc5_bind.html",
    "uc6_migrate.html",
    "uc8_revoke.html",
]

# verifications_form.html gets a separate, stricter scan: rendered
# text only (Jinja comments stripped; HTML attribute values ignored).
R6_RENDERED_SCAN_TEMPLATE = "verifications_form.html"

# Default health endpoint. Watcher tries this; if it fails, surfaces
# as info (not alert) since the app being offline is not a security
# regression.
HEALTH_URL = "http://localhost:2223/api/health"
HEALTH_TIMEOUT_SECS = 1.5


class SecurityWatcher(Watcher):
    name = "security"
    domain = ("CSP + CSRF + rate-limiter + role-gating + R6 anti-revealing "
              "+ template inline-JS scan")

    # v9.28 / Hydra #4 — runtime-grounded security probe.
    # Hits a protected route on the running app and verifies it returns
    # HTTP 403 (or 302→/login) to an UNAUTHENTICATED request. INCONCLUSIVE
    # if app not running per Anti-Architect honest-accounting.
    def probe_running_app(self, base_url: str | None = None) -> list[Finding]:
        """Probe the running app's auth-gating from outside.

        Predicate (per meta/watcher-predicates.md): "A protected route
        returns HTTP 403 to an unauthenticated request."
        External record: live HTTP response code from a deployed
        Polaris instance.

        Returns:
          [] if probe succeeded and the gate held.
          [Finding(severity='inconclusive', ...)] if app unreachable.
          [Finding(severity='alert', ...)] if a protected route returned
            200 to an unauthenticated probe (auth gate broken).
        """
        import os, socket
        import urllib.request, urllib.error
        url = base_url or os.environ.get("POLARIS_PROBE_URL",
                                          "http://localhost:2222")
        # Protected route candidate. /dashboard is the canonical post-
        # login landing page; should redirect or 403 anonymously.
        probe_path = "/dashboard"
        full = url.rstrip("/") + probe_path

        try:
            socket.setdefaulttimeout(2)
            req = urllib.request.Request(full, method="GET")
            with urllib.request.urlopen(req, timeout=2) as resp:
                status = resp.status
                # 200 to an anonymous request on /dashboard = auth broken
                if status == 200:
                    return [Finding(
                        severity="alert",
                        title=f"security_watcher: /dashboard returned 200 anonymously",
                        detail=(f"Probe to {full} returned HTTP 200 without "
                                f"auth — the @login_required gate is "
                                f"missing or bypassed. C-grade regression."),
                        evidence={
                            "node_id": "runtime:auth",
                            "additional_node_ids": ["security:auth-gate"],
                            "probe_url": full,
                            "probe_status": 200,
                        },
                    )]
                return []   # 302/401/403 — auth gate held
        except urllib.error.HTTPError as e:
            if e.code in (302, 401, 403):
                return []   # Expected gate
            return [Finding(
                severity="drift",
                title=f"security_watcher probe unexpected HTTP {e.code}",
                detail=(f"Probe to {full} returned {e.code}; expected "
                        f"200 / 302 / 401 / 403."),
                evidence={"node_id": "security:auth-gate",
                          "probe_status": e.code},
            )]
        except (urllib.error.URLError, socket.timeout, ConnectionRefusedError) as e:
            return [Finding(
                severity="drift",
                title="security_watcher probe INCONCLUSIVE",
                detail=(f"App unreachable at {url}; cannot verify "
                        f"auth-gate from outside. Run with the app "
                        f"started + POLARIS_PROBE_URL set for runtime "
                        f"coverage."),
                evidence={
                    "node_id": "runtime:auth",
                    "status": "inconclusive",
                    "probe_url": full,
                    "error": str(e)[:100],
                },
            )]

    def _observe(self) -> WatcherReport:
        repo_root = self._repo_root()
        findings: list[Finding] = []
        evidence: dict[str, Any] = {}

        security_py = repo_root / "polaris_web" / "security.py"
        app_py = repo_root / "polaris_web" / "app.py"
        templates_dir = repo_root / "polaris_web" / "templates"

        # ---- 1. CSP integrity --------------------------------------------
        csp_findings, csp_evidence = self._check_csp(security_py)
        findings.extend(csp_findings)
        evidence.update(csp_evidence)

        # ---- 2. CSRF mechanism -------------------------------------------
        csrf_findings, csrf_evidence = self._check_csrf(security_py)
        findings.extend(csrf_findings)
        evidence.update(csrf_evidence)

        # ---- 3. Rate-limiter health --------------------------------------
        rl_findings, rl_evidence = self._check_rate_limiter_health()
        findings.extend(rl_findings)
        evidence.update(rl_evidence)

        # ---- 4. Role-gating coverage -------------------------------------
        gate_findings, gate_evidence = self._check_role_gating(app_py)
        findings.extend(gate_findings)
        evidence.update(gate_evidence)

        # ---- 5. R6 anti-revealing ----------------------------------------
        r6_findings, r6_evidence = self._check_r6(templates_dir)
        findings.extend(r6_findings)
        evidence.update(r6_evidence)

        # ---- 6. Template inline-JS scan (v8.47) --------------------------
        # CSP literal scan (channel 1) confirms `script-src 'self'` is set
        # in security.py. But templates can still contain `onclick=`,
        # `onsubmit=`, inline `<script>` blocks etc. that the policy
        # silently blocks at runtime. v8.45 scan surfaced this gap;
        # v8.46 fixed every template; v8.47 adds the watcher channel
        # so the gap can never recur undetected.
        ijs_findings, ijs_evidence = self._check_template_inline_js(
            templates_dir
        )
        findings.extend(ijs_findings)
        evidence.update(ijs_evidence)

        # ---- 7. Pheromone-context: log_tail signal (v9.04) ---------------
        # Static checks above prove the SURFACE is correct. The log_tail
        # soldier proves the RUNTIME isn't bleeding errors that the static
        # surface can't see.
        log_findings, log_evidence = self._check_pheromone_log_tail()
        findings.extend(log_findings)
        evidence.update(log_evidence)

        # ---- Status aggregate --------------------------------------------
        if any(f.severity == "alert" for f in findings):
            status = "alert"
        elif sum(1 for f in findings if f.severity == "drift") >= 2:
            status = "drift"
        elif any(f.severity == "drift" for f in findings):
            status = "drift"
        else:
            status = "healthy"

        if not findings:
            findings.append(Finding(
                severity="info",
                title="security surface intact",
                detail=("CSP literal correct; CSRF accepts both form-field "
                        "and X-CSRFToken header paths; rate-limiter "
                        "responsive; role-gating coverage at or above the "
                        "v8.x baseline; R6 anti-revealing posture intact "
                        "across operator-visible templates; templates "
                        "free of inline event handlers and executable "
                        "inline <script> blocks."),
                evidence={
                    "csp_ok": evidence.get("csp_ok"),
                    "csrf_ok": evidence.get("csrf_ok"),
                    "role_gates": evidence.get("role_gate_total"),
                    "r6_clean": evidence.get("r6_clean"),
                    "templates_inline_js_clean":
                        evidence.get("templates_inline_js_clean"),
                },
            ))

        return WatcherReport(
            watcher_name=self.name,
            domain=self.domain,
            status=status,
            findings=findings,
            evidence_summary=evidence,
        )

    # ------------------------------------------------------------------
    # Channel implementations
    # ------------------------------------------------------------------

    def _repo_root(self) -> pathlib.Path:
        here = pathlib.Path(__file__).resolve()
        return here.parent.parent.parent

    def _check_csp(
        self, security_py: pathlib.Path
    ) -> tuple[list[Finding], dict[str, Any]]:
        findings: list[Finding] = []
        evidence: dict[str, Any] = {"csp_ok": False}

        if not security_py.is_file():
            findings.append(Finding(
                severity="alert",
                title="security.py missing",
                detail=("polaris_web/security.py is not present. The CSP "
                        "+ CSRF + rate-limiter + auth surface lives there; "
                        "without it the security posture is undefined."),
                evidence={"path": str(security_py)},
            ))
            return findings, evidence

        text = security_py.read_text(errors="replace")

        # Required CSP fragments (C5 — script-src 'self', no inline).
        required = {
            "script-src 'self'":           "script-src 'self' directive",
            "X-Frame-Options":             "X-Frame-Options header",
            "X-Content-Type-Options":      "X-Content-Type-Options header",
            "Content-Security-Policy":     "Content-Security-Policy header",
        }
        missing = [label for fragment, label in required.items()
                   if fragment not in text]
        if missing:
            findings.append(Finding(
                severity="alert",
                title="CSP fragment(s) missing",
                detail=("security.py is missing one or more required CSP "
                        "fragments. C5 enforcement may be weakened."),
                evidence={"missing": missing},
            ))

        # No 'unsafe-inline' for scripts. The string can legitimately
        # appear in style-src (e.g. style-src 'self' 'unsafe-inline'),
        # but it must NEVER appear within script-src.
        script_src_unsafe = re.search(
            r"script-src[^;]*'unsafe-inline'", text, flags=re.IGNORECASE
        )
        if script_src_unsafe:
            findings.append(Finding(
                severity="alert",
                title="script-src contains 'unsafe-inline'",
                detail=("C5 says script-src must NOT include 'unsafe-inline'. "
                        "Found it in the script-src directive — this "
                        "weakens XSS protection. Remove and use external "
                        "<script src=\"...\"> tags instead."),
                evidence={"match": script_src_unsafe.group(0)[:120]},
            ))

        evidence["csp_ok"] = not (missing or script_src_unsafe)
        return findings, evidence

    def _check_csrf(
        self, security_py: pathlib.Path
    ) -> tuple[list[Finding], dict[str, Any]]:
        findings: list[Finding] = []
        evidence: dict[str, Any] = {"csrf_ok": False}

        if not security_py.is_file():
            return findings, evidence  # already alerted by CSP check

        text = security_py.read_text(errors="replace")

        # validate_csrf must exist.
        if "def validate_csrf" not in text and "validate_csrf" not in text:
            findings.append(Finding(
                severity="alert",
                title="validate_csrf not found",
                detail=("CSRF validation entry point is missing from "
                        "security.py. Forms posting to the app may not "
                        "be protected."),
                evidence={},
            ))
            return findings, evidence

        # The v8.22 fix: validate_csrf accepts both form field + header.
        accepts_form = "csrf_token" in text
        accepts_header = "X-CSRFToken" in text
        if not (accepts_form and accepts_header):
            severity = "drift"
            findings.append(Finding(
                severity=severity,
                title="CSRF accepts only one transport",
                detail=("CSRF validation should accept the token from "
                        "BOTH the form field (`csrf_token`) AND the "
                        "X-CSRFToken header (the v8.22 fix for AJAX/JSON "
                        "callers). One of these is missing."),
                evidence={"accepts_form_field": accepts_form,
                          "accepts_header": accepts_header},
            ))

        evidence["csrf_ok"] = accepts_form and accepts_header
        return findings, evidence

    def _check_rate_limiter_health(
        self,
    ) -> tuple[list[Finding], dict[str, Any]]:
        findings: list[Finding] = []
        evidence: dict[str, Any] = {"rate_limiter_status": "unknown"}

        try:
            req = urllib.request.Request(
                HEALTH_URL,
                headers={"User-Agent": "polaris-hydra-security-watcher"},
            )
            with urllib.request.urlopen(
                req, timeout=HEALTH_TIMEOUT_SECS
            ) as resp:
                body = resp.read().decode("utf-8", errors="replace")
        except (urllib.error.URLError, TimeoutError, OSError):
            # App not running locally — that's a normal CI / offline
            # condition for the watcher.
            evidence["rate_limiter_status"] = "app_offline"
            findings.append(Finding(
                severity="info",
                title="app not reachable for live rate-limiter check",
                detail=(f"GET {HEALTH_URL} failed within "
                        f"{HEALTH_TIMEOUT_SECS}s. The app is not running "
                        f"locally. This is not a security regression; the "
                        f"watcher confirms the CSP+CSRF+role-gating "
                        f"surface from static analysis."),
                # v9.10 / S1: shared-surface node_id `runtime:health`.
                # performance_watcher emits the same node_id for its
                # own /api/health probe; CorrelationEngine fires when
                # both watchers see the app offline.
                evidence={
                    "url": HEALTH_URL,
                    "additional_node_ids": ["runtime:health"],
                },
            ))
            return findings, evidence

        # Parse the rate-limiter line.
        import json as _json
        try:
            health = _json.loads(body)
        except _json.JSONDecodeError:
            evidence["rate_limiter_status"] = "malformed_response"
            findings.append(Finding(
                severity="drift",
                title="health endpoint returned non-JSON",
                detail=("GET /api/health did not return parseable JSON. "
                        "The health surface may have regressed."),
                evidence={"body_head": body[:200]},
            ))
            return findings, evidence

        rl = health.get("checks", {}).get("rate_limiter", {})
        evidence["rate_limiter_status"] = (
            "ok" if rl.get("ok") else "not_ok"
        )
        evidence["rate_limiter_backend"] = rl.get("backend", "unknown")
        if not rl.get("ok"):
            findings.append(Finding(
                severity="alert",
                title="rate-limiter reports unhealthy",
                detail=("The live rate-limiter is reporting ok=false on "
                        "/api/health. Either Redis is unreachable (if the "
                        "Redis backend is in use) or the limiter "
                        "configuration is broken."),
                evidence={"backend": rl.get("backend"),
                          "raw": rl},
            ))
        return findings, evidence

    def _check_role_gating(
        self, app_py: pathlib.Path
    ) -> tuple[list[Finding], dict[str, Any]]:
        findings: list[Finding] = []
        evidence: dict[str, Any] = {}

        if not app_py.is_file():
            findings.append(Finding(
                severity="alert",
                title="app.py missing",
                detail=("polaris_web/app.py is not present. Route-level "
                        "role-gating coverage cannot be verified."),
                evidence={"path": str(app_py)},
            ))
            return findings, evidence

        text = app_py.read_text(errors="replace")
        login_required_count = text.count("@security.login_required")
        require_role_count = text.count("@security.require_role")
        evidence["role_gate_login_required"] = login_required_count
        evidence["role_gate_require_role"] = require_role_count
        evidence["role_gate_total"] = login_required_count + require_role_count

        if login_required_count < ROLE_GATE_BASELINE["@security.login_required"]:
            findings.append(Finding(
                severity="drift",
                title="login_required decorator count dropped",
                detail=(f"@security.login_required appears "
                        f"{login_required_count} time(s) in app.py; the "
                        f"v8.x baseline is "
                        f"{ROLE_GATE_BASELINE['@security.login_required']}. "
                        f"A drop could mean a route lost its auth gate."),
                evidence={"current": login_required_count,
                          "baseline": ROLE_GATE_BASELINE["@security.login_required"]},
            ))
        if require_role_count < ROLE_GATE_BASELINE["@security.require_role"]:
            findings.append(Finding(
                severity="drift",
                title="require_role decorator count dropped",
                detail=(f"@security.require_role appears "
                        f"{require_role_count} time(s); the v8.x baseline "
                        f"is {ROLE_GATE_BASELINE['@security.require_role']}. "
                        f"A drop could mean a role-restricted route lost "
                        f"its gate."),
                evidence={"current": require_role_count,
                          "baseline": ROLE_GATE_BASELINE["@security.require_role"]},
            ))
        return findings, evidence

    def _check_r6(
        self, templates_dir: pathlib.Path
    ) -> tuple[list[Finding], dict[str, Any]]:
        findings: list[Finding] = []
        evidence: dict[str, Any] = {"r6_clean": False}

        if not templates_dir.is_dir():
            findings.append(Finding(
                severity="alert",
                title="templates/ directory missing",
                detail=("polaris_web/templates/ is not present. R6 anti-"
                        "revealing cannot be verified."),
                evidence={"path": str(templates_dir)},
            ))
            return findings, evidence

        offenders: list[dict[str, Any]] = []

        # Strict scan: operator-visible templates must be completely
        # free of duress/compulsion in source.
        for filename in OPERATOR_VISIBLE_TEMPLATES:
            path = templates_dir / filename
            if not path.is_file():
                continue  # not all templates may exist in every variant
            try:
                content = path.read_text(errors="replace").lower()
            except OSError:
                continue
            for keyword in ("duress", "compulsion"):
                if keyword in content:
                    offenders.append({
                        "template": filename,
                        "keyword": keyword,
                        "scan": "strict",
                    })
                    break

        # Lenient scan: verifications_form.html legitimately needs a
        # duress_code form field. The scan strips Jinja comments
        # (`{# ... #}`, stripped at render) and HTML attribute values
        # (`name="..."`, `id="..."`, etc.) and only checks the rendered
        # text surface.
        form_path = templates_dir / R6_RENDERED_SCAN_TEMPLATE
        if form_path.is_file():
            try:
                raw = form_path.read_text(errors="replace")
                rendered = self._strip_jinja_and_attrs(raw).lower()
                for keyword in ("duress", "compulsion"):
                    if keyword in rendered:
                        offenders.append({
                            "template": R6_RENDERED_SCAN_TEMPLATE,
                            "keyword": keyword,
                            "scan": "rendered-text",
                            "note": ("This keyword appears in user-visible "
                                     "text, not just in Jinja comments or "
                                     "HTML attributes. The v8.24 design "
                                     "kept the label neutral; if rendered "
                                     "text now says 'duress', R6 is "
                                     "broken on this form."),
                        })
                        break
            except OSError:
                pass

        evidence["r6_templates_scanned"] = (
            len(OPERATOR_VISIBLE_TEMPLATES) +
            (1 if form_path.is_file() else 0)
        )
        evidence["r6_offenders"] = len(offenders)
        evidence["r6_clean"] = (len(offenders) == 0)

        if offenders:
            findings.append(Finding(
                severity="alert",
                title="R6 anti-revealing violation",
                detail=("Operator-visible template(s) mention `duress` or "
                        "`compulsion`. R6 says these strings must NOT "
                        "appear in templates accessible to operator role — "
                        "the entire mechanism's plausible-deniability "
                        "rests on operators not seeing the keyword."),
                evidence={"offenders": offenders[:5]},
            ))
        return findings, evidence

    # ------------------------------------------------------------------
    # Channel 6 (v8.47): template inline-JS scan
    # ------------------------------------------------------------------

    # Standard DOM event-handler attributes that, when used inline in
    # HTML (`<button onclick="…">`), execute JavaScript. Under CSP
    # `script-src 'self'` (without `unsafe-inline`) these are blocked
    # at runtime. The list is the standard DOM event set (HTML5 +
    # touch + drag + media). Adding new ones is harmless; missing one
    # creates a false-negative.
    _INLINE_EVENT_HANDLER_PATTERN = re.compile(
        r"<[a-zA-Z][^>]*?\s(on[a-z]+)\s*=",
        re.IGNORECASE,
    )

    # An executable inline <script> is `<script>...</script>` or
    # `<script type="text/javascript">...</script>` with no `src=`
    # attribute. The pattern matches the opening tag; the caller then
    # filters allowed `type="application/json"` (and similar
    # non-executable types) and `src=`.
    _SCRIPT_OPEN_TAG_PATTERN = re.compile(
        r"<script\b([^>]*)>",
        re.IGNORECASE,
    )

    # MIME types that mark a `<script>` block as non-executable data.
    # `application/json`, `application/ld+json`, `text/template`,
    # `text/x-handlebars-template`, etc. The atlas data-island uses
    # `application/json` (atlas.html:157 — documented in CLAUDE.md
    # gotcha #5).
    _NON_EXECUTABLE_SCRIPT_TYPES = (
        "application/json",
        "application/ld+json",
        "text/template",
        "text/x-template",
        "text/x-handlebars-template",
        "text/x-mustache-template",
    )

    def _check_template_inline_js(
        self, templates_dir: pathlib.Path
    ) -> tuple[list[Finding], dict[str, Any]]:
        """Scan every .html in templates/ for runtime-blocked patterns.

        Detects:
          1. Inline event-handler attributes (`onclick=`, `onsubmit=`,
             `onchange=`, etc.) — the v8.46 finding class.
          2. Executable inline `<script>` blocks (no `src=` AND not
             a `type="application/json"`-style data island).

        Skips:
          - Jinja comments `{# ... #}` (stripped at render).
          - The documented `<script id="atlas-globe-data"
            type="application/json">` data-island.

        Returns drift severity if any violation is found. Failing on
        this channel is a real signal: the runtime is misaligned with
        the documented CSP intent, and the template-edit pattern that
        introduced the violation should be rewritten via the
        attribute-driven opt-in convention v8.46 established
        (`data-confirm`, `data-submit-on-change`, external `.js`).
        """
        findings: list[Finding] = []
        evidence: dict[str, Any] = {
            "templates_inline_js_clean": False,
            "templates_inline_js_scanned": 0,
        }

        if not templates_dir.is_dir():
            findings.append(Finding(
                severity="alert",
                title="templates/ directory missing for inline-JS scan",
                detail=("polaris_web/templates/ is not present. Inline-JS "
                        "scan cannot be verified."),
                evidence={"path": str(templates_dir)},
            ))
            return findings, evidence

        offenders: list[dict[str, Any]] = []
        templates_scanned = 0

        for path in sorted(templates_dir.glob("*.html")):
            templates_scanned += 1
            try:
                raw = path.read_text(errors="replace")
            except OSError:
                continue

            # Strip Jinja comments first — they can mention `onclick=`
            # or `<script>` as documentation without it being executable.
            stripped = re.sub(r"\{#.*?#\}", "", raw, flags=re.DOTALL)

            # Check 1: inline event-handler attributes.
            for match in self._INLINE_EVENT_HANDLER_PATTERN.finditer(stripped):
                handler = match.group(1).lower()
                line_no = stripped.count("\n", 0, match.start()) + 1
                offenders.append({
                    "template": path.name,
                    "line": line_no,
                    "kind": "inline_event_handler",
                    "attribute": handler,
                    "fix": ("Replace with data-* attribute + external .js "
                            "(see static/confirm-submit.js for the pattern)."),
                })

            # Check 2: executable inline <script> blocks.
            for match in self._SCRIPT_OPEN_TAG_PATTERN.finditer(stripped):
                attrs = match.group(1)
                # `src=` makes it an external load — fine.
                if re.search(r"\bsrc\s*=", attrs, re.IGNORECASE):
                    continue
                # Non-executable types are data-islands — fine.
                type_match = re.search(
                    r"""type\s*=\s*['"]([^'"]+)['"]""",
                    attrs,
                    re.IGNORECASE,
                )
                if type_match:
                    mime = type_match.group(1).lower().strip()
                    if mime in self._NON_EXECUTABLE_SCRIPT_TYPES:
                        continue
                line_no = stripped.count("\n", 0, match.start()) + 1
                offenders.append({
                    "template": path.name,
                    "line": line_no,
                    "kind": "inline_executable_script",
                    "fix": ("Move script body to polaris_web/static/<name>.js "
                            "and load via <script src='...' defer>."),
                })

        evidence["templates_inline_js_scanned"] = templates_scanned
        evidence["templates_inline_js_offenders"] = len(offenders)
        evidence["templates_inline_js_clean"] = (len(offenders) == 0)

        if offenders:
            findings.append(Finding(
                severity="drift",
                title="template contains inline JS blocked by CSP",
                detail=(f"{len(offenders)} inline-JS site(s) found across "
                        f"{templates_scanned} template(s). CSP "
                        f"`script-src 'self'` blocks these at runtime — "
                        f"the silent breakage v8.46 fixed for 8 sites. "
                        f"Use the data-* attribute convention "
                        f"(see polaris_web/static/confirm-submit.js)."),
                evidence={"offenders": offenders[:10],
                          "total_offenders": len(offenders)},
            ))

        return findings, evidence

    # ------------------------------------------------------------------
    # Channel 7 (v9.04): pheromone-context — soldier_log_tail signal
    # ------------------------------------------------------------------

    def _check_pheromone_log_tail(
        self,
    ) -> tuple[list[Finding], dict[str, Any]]:
        """Read recent soldier_log_tail deposits + surface error counts.

        The soldier_log_tail class (v9.03) tails app log files for
        ERROR / WARNING patterns and deposits with kind='alert' or
        kind='drift'. SecurityWatcher's static checks (CSP/CSRF/role
        gating) can't see runtime errors; this channel adds them.

        Graceful: if PheromoneReader returns empty (DB offline OR no
        log_tail deposits in the window), surfaces as info, not drift.
        """
        findings: list[Finding] = []
        evidence: dict[str, Any] = {"pheromone_log_tail_status": "unknown"}

        try:
            reader = PheromoneReader(window_hours=WINDOW_FAST)
            deposits = reader.deposits_by_class("soldier_log_tail",
                                                window_hours=WINDOW_FAST)
        except Exception as exc:  # noqa: BLE001 — graceful
            evidence["pheromone_log_tail_status"] = (
                f"reader_error:{type(exc).__name__}"
            )
            return findings, evidence

        if not deposits:
            evidence["pheromone_log_tail_status"] = "no_deposits_in_window"
            return findings, evidence

        evidence["pheromone_log_tail_status"] = "ok"
        evidence["pheromone_log_tail_count"] = len(deposits)

        # Categorize by kind. Surface alerts/drift as drift (the
        # security watcher's claim is "static surface OK but runtime
        # is bleeding"); info-level deposits stay quiet.
        alert_count = sum(1 for d in deposits if d.kind == "alert")
        drift_count = sum(1 for d in deposits if d.kind == "drift")
        evidence["pheromone_log_tail_alert"] = alert_count
        evidence["pheromone_log_tail_drift"] = drift_count

        if alert_count > 0 or drift_count > 0:
            sample_node_ids = sorted({
                d.node_id for d in deposits
                if d.kind in ("alert", "drift")
            })[:5]
            findings.append(Finding(
                severity="drift",
                title=(f"soldier_log_tail surfaced "
                       f"{alert_count + drift_count} signal(s)"),
                detail=(
                    f"In the last {WINDOW_FAST:.0f}h the soldier_log_tail "
                    f"soldier deposited {alert_count} alert + {drift_count} "
                    f"drift pheromone(s). The static security surface "
                    f"(CSP/CSRF/role-gating) is unchanged, but the "
                    f"runtime log stream contains ERROR/WARNING entries "
                    f"worth investigating. Sample node_ids: "
                    f"{sample_node_ids}"
                ),
                evidence={
                    "alert_count": alert_count,
                    "drift_count": drift_count,
                    "sample_node_ids": sample_node_ids,
                    "node_id": "infra:logs",
                    "pheromone_context": "soldier_log_tail",
                },
            ))

        return findings, evidence

    def _strip_jinja_and_attrs(self, text: str) -> str:
        """Return only the user-rendered portion of a Jinja template.

        Strips:
          - Jinja comments `{# ... #}` (stripped at render time)
          - HTML attribute values `="..."` and `='...'` (these are
            source-only; the user sees the rendered text + content
            of `name=`/`id=`/etc. is invisible)
          - HTML tags themselves `<...>` (only the text content
            between tags matters for rendered output)

        Order: strip Jinja first (it can contain `>` characters that
        confuse tag stripping), then attribute values, then tags.
        """
        # Strip Jinja comments first.
        text = re.sub(r"\{#.*?#\}", "", text, flags=re.DOTALL)
        # Strip HTML attribute values (double + single quoted).
        text = re.sub(r'=\s*"[^"]*"', "", text)
        text = re.sub(r"=\s*'[^']*'", "", text)
        # Strip HTML tags (anything in angle brackets).
        text = re.sub(r"<[^>]+>", " ", text)
        return text
