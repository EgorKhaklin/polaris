"""PerformanceWatcher — H7 of Arc D.

Monitors Polaris's atlas performance surface from the cognitive
layer:

  1. Atlas API latency — times GET against /api/atlas/stats,
     /api/atlas/clusters, /api/atlas/points (and as of v8.50,
     /api/atlas/timeline + /api/atlas/events — all five touch
     VerificationEvent over bounded windows with equivalent
     regression risk at scale). Thresholds:
       < 200 ms  = healthy
       200ms–1s  = drift
       > 1s      = alert
     App offline = info (graceful; no live data to time against).
  2. Health endpoint — GETs /api/health and confirms the overall
     `status` field is "healthy" (not "degraded" or "unhealthy").
  3. EXPLAIN ANALYZE spot-check — runs `EXPLAIN ANALYZE` on a
     canonical atlas query (the points endpoint's underlying SQL)
     and looks for `Seq Scan on verificationevent` — the canonical
     index-miss regression signal. Requires DB access; degrades to
     info when unreachable.
  4. **Pheromone-context: route_pinger latency distribution
     (v9.04).** Reads recent soldier_route_pinger deposits via
     PheromoneReader. Where channel 1 takes a single-shot timing,
     channel 4 reads a continuous distribution of timings the
     soldier already gathered. Surfaces drift if the soldier
     itself flagged any route as slow.

Read-only on both the HTTP and DB sides. The watcher invokes GETs
and EXPLAIN-without-actual-side-effects.
"""

from __future__ import annotations

import os
import pathlib
import time
import urllib.error
import urllib.request
from typing import Any

from polaris_hydra.pheromone_reader import PheromoneReader, WINDOW_FAST

from .base import Finding, Watcher, WatcherReport


# Latency thresholds (milliseconds). Calibrated against the v8.x
# baseline (atlas APIs typically <50 ms under seed load; >200ms is
# already a signal something has shifted).
LATENCY_DRIFT_MS = 200
LATENCY_ALERT_MS = 1000

# Atlas endpoints to time. Each carries a small synthetic query that
# exercises the spatial path without blowing past the hard caps.
ATLAS_ENDPOINTS = [
    ("/api/atlas/stats",    "?bbox=-180,-90,180,90"),
    ("/api/atlas/clusters", "?bbox=-180,-90,180,90&grid=4"),
    ("/api/atlas/points",   "?bbox=-180,-90,180,90&limit=100"),
    # v8.50: added per v8.45 adversary-scan finding. Equivalent
    # regression risk at scale to the three above; both touch
    # VerificationEvent over a bounded window.
    ("/api/atlas/timeline", "?bbox=-180,-90,180,90"),
    ("/api/atlas/events",   "?bbox=-180,-90,180,90&limit=50"),
]

# Health endpoint + HTTP timeout for any single GET.
HEALTH_URL = "http://localhost:2223/api/health"
HTTP_TIMEOUT_SECS = 2.0
BASE_URL = "http://localhost:2223"

# The canonical atlas query to EXPLAIN ANALYZE. This is approximately
# what /api/atlas/points runs at the SQL layer — we don't import the
# Flask code; we just verify the plan against a representative shape.
CANONICAL_ATLAS_SQL = """
EXPLAIN ANALYZE
SELECT event_id, longitude, latitude, outcome, disclosure_level
  FROM VerificationEvent
 WHERE longitude BETWEEN -180 AND 180
   AND latitude  BETWEEN -90  AND 90
 ORDER BY event_id DESC
 LIMIT 100
"""

# Patterns in the EXPLAIN output that indicate the index miss we want
# to catch. A bare `Seq Scan on verificationevent` without any
# filtering/limiting clause is the canonical regression.
SEQ_SCAN_REGRESSION_MARKER = "Seq Scan on verificationevent"

# Row-count threshold: below this, a Seq Scan is the OPTIMAL plan
# (Postgres correctly skips the index when the table is small). The
# watcher only flags Seq Scan as a regression when the table is large
# enough that an index scan would matter.
SEQ_SCAN_REGRESSION_ROW_THRESHOLD = 1000


class PerformanceWatcher(Watcher):
    name = "performance"
    domain = "atlas latency + health endpoint + index-miss regression"

    def _observe(self) -> WatcherReport:
        findings: list[Finding] = []
        evidence: dict[str, Any] = {
            "endpoints_timed": 0,
            "endpoints_healthy": 0,
            "endpoints_drift": 0,
            "endpoints_alert": 0,
            "latencies_ms": {},
            "app_reachable": False,
        }

        # ---- 1. Atlas API latency ----------------------------------------
        app_reachable = self._app_reachable()
        evidence["app_reachable"] = app_reachable
        if not app_reachable:
            findings.append(Finding(
                severity="info",
                title="app not reachable for live performance check",
                detail=("The Polaris Flask app is not running on port 2223. "
                        "Live latency timing and health probe are skipped. "
                        "Static performance posture is not at risk — this "
                        "is a CI/offline condition, not a regression."),
                # v9.10 / S1: shared-surface node_id `runtime:health`.
                # security_watcher emits the same when its rate-limiter
                # probe finds the app offline; CorrelationEngine fires.
                evidence={
                    "base_url": BASE_URL,
                    "timeout_secs": HTTP_TIMEOUT_SECS,
                    "additional_node_ids": ["runtime:health"],
                },
            ))
        else:
            for path, query in ATLAS_ENDPOINTS:
                url = f"{BASE_URL}{path}{query}"
                ms = self._time_get(url)
                evidence["endpoints_timed"] += 1
                evidence["latencies_ms"][path] = ms
                if ms is None:
                    evidence["endpoints_alert"] += 1
                    findings.append(Finding(
                        severity="alert",
                        title=f"atlas endpoint timed out: {path}",
                        detail=(f"GET {url} did not return within "
                                f"{HTTP_TIMEOUT_SECS}s. The C8 hard caps "
                                f"should bound result-set size, but the "
                                f"endpoint itself shouldn't time out at "
                                f"the seed scale."),
                        evidence={"url": url},
                    ))
                elif ms > LATENCY_ALERT_MS:
                    evidence["endpoints_alert"] += 1
                    findings.append(Finding(
                        severity="alert",
                        title=f"{path} > {LATENCY_ALERT_MS} ms",
                        detail=(f"GET {path} returned in {ms:.0f} ms, above "
                                f"the {LATENCY_ALERT_MS} ms alert threshold. "
                                f"Atlas pages will feel unresponsive."),
                        evidence={"latency_ms": ms},
                    ))
                elif ms > LATENCY_DRIFT_MS:
                    evidence["endpoints_drift"] += 1
                    findings.append(Finding(
                        severity="drift",
                        title=f"{path} latency drift",
                        detail=(f"GET {path} returned in {ms:.0f} ms, above "
                                f"the {LATENCY_DRIFT_MS} ms drift threshold "
                                f"but below alert. At v8.x seed scale this "
                                f"is unusual; investigate."),
                        evidence={"latency_ms": ms,
                                  "drift_threshold": LATENCY_DRIFT_MS},
                    ))
                else:
                    evidence["endpoints_healthy"] += 1

            # ---- 2. Health endpoint ----------------------------------
            health_status = self._fetch_health()
            evidence["health_status"] = health_status
            if health_status not in ("healthy", "degraded"):
                findings.append(Finding(
                    severity="alert",
                    title=f"/api/health reports {health_status!r}",
                    detail=("The application's overall health endpoint "
                            "did not return 'healthy' or 'degraded'. "
                            "Investigate the unhealthy subsystem."),
                    evidence={"status": health_status},
                ))
            elif health_status == "degraded":
                findings.append(Finding(
                    severity="drift",
                    title="/api/health reports 'degraded'",
                    detail=("The application is serving but with at least "
                            "one subsystem unhealthy. Pull the full "
                            "/api/health JSON for detail."),
                    evidence={"status": health_status},
                ))

        # ---- 3. EXPLAIN ANALYZE spot-check -------------------------------
        plan_check = self._check_query_plan()
        evidence["query_plan_status"] = plan_check["status"]
        if plan_check["finding"]:
            findings.append(plan_check["finding"])

        # ---- 4. Pheromone-context: route_pinger distribution (v9.04) -----
        rp_findings, rp_evidence = self._check_pheromone_route_pinger()
        findings.extend(rp_findings)
        evidence.update(rp_evidence)

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
                title="performance posture intact",
                detail=("Atlas endpoints respond within drift threshold "
                        f"({LATENCY_DRIFT_MS} ms); health endpoint reports "
                        "'healthy'; canonical atlas query plan does not "
                        "show a sequential-scan regression on "
                        "VerificationEvent."),
                evidence={
                    "endpoints_healthy": evidence["endpoints_healthy"],
                    "endpoints_timed": evidence["endpoints_timed"],
                    "query_plan_status": evidence["query_plan_status"],
                },
            ))

        return WatcherReport(
            watcher_name=self.name, domain=self.domain,
            status=status, findings=findings,
            evidence_summary=evidence,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _app_reachable(self) -> bool:
        """Quick liveness probe. 1-second timeout."""
        try:
            req = urllib.request.Request(
                HEALTH_URL,
                headers={"User-Agent": "polaris-hydra-performance-watcher"},
            )
            with urllib.request.urlopen(req, timeout=1.0) as resp:
                return resp.status == 200
        except (urllib.error.URLError, TimeoutError, OSError):
            return False

    def _time_get(self, url: str) -> float | None:
        """GET the URL and return elapsed ms, or None on failure.

        The Polaris app requires login for the /api/atlas/* endpoints
        in normal operation, so a 401 or 302 is still a valid timing
        measurement (the server processed the request quickly enough
        to reject it). What we time is response latency, not response
        body usefulness.
        """
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "polaris-hydra-performance-watcher"},
        )
        start = time.monotonic()
        try:
            with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT_SECS) as resp:
                _ = resp.read(0)  # don't drain body; we only want headers
        except urllib.error.HTTPError:
            # 4xx/5xx still gives us a valid timing.
            pass
        except (urllib.error.URLError, TimeoutError, OSError):
            return None
        return (time.monotonic() - start) * 1000.0

    def _fetch_health(self) -> str:
        """Get the overall health status string."""
        import json as _json
        try:
            req = urllib.request.Request(
                HEALTH_URL,
                headers={"User-Agent": "polaris-hydra-performance-watcher"},
            )
            with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT_SECS) as resp:
                body = resp.read().decode("utf-8", errors="replace")
            data = _json.loads(body)
            return data.get("status", "unknown")
        except (urllib.error.URLError, TimeoutError, OSError,
                _json.JSONDecodeError):
            return "unreachable"

    def _check_query_plan(self) -> dict[str, Any]:
        """Run EXPLAIN ANALYZE against the canonical atlas query.

        Returns {"status": "healthy"|"drift"|"alert"|"skipped",
                 "finding": Finding|None}.
        Skipped means DB unreachable; that's not a regression.
        """
        try:
            import psycopg2
        except ImportError:
            return {
                "status": "skipped",
                "finding": Finding(
                    severity="info",
                    title="psycopg2 not importable",
                    detail=("PerformanceWatcher cannot run the EXPLAIN "
                            "ANALYZE spot-check without psycopg2. The "
                            "atlas latency channel still ran."),
                    evidence={},
                ),
            }

        db_config = {
            "host":     os.environ.get("POLARIS_DB_HOST", "localhost"),
            "dbname":   os.environ.get("POLARIS_DB_NAME", "polaris_test"),
            "user":     os.environ.get("POLARIS_DB_USER", "polaris_app"),
            "password": os.environ.get("POLARIS_DB_PASSWORD",
                                       "polaris_dev_password"),
        }
        try:
            conn = psycopg2.connect(**db_config)
        except psycopg2.OperationalError as exc:
            return {
                "status": "skipped",
                "finding": Finding(
                    severity="info",
                    title="cannot reach DB for query-plan spot-check",
                    detail=("PerformanceWatcher could not connect to the "
                            "Polaris DB. The plan check is skipped; the "
                            "atlas latency channel ran independently."),
                    evidence={"db_host": db_config["host"],
                              "error": str(exc)[:200]},
                ),
            }

        try:
            with conn, conn.cursor() as cur:
                # First: how many rows? Below threshold, Seq Scan is the
                # correct plan and we shouldn't flag it.
                cur.execute("SELECT count(*) FROM VerificationEvent")
                row = cur.fetchone()
                row_count = row[0] if row else 0
                cur.execute(CANONICAL_ATLAS_SQL)
                plan_rows = cur.fetchall()
                plan_text = "\n".join(r[0] for r in plan_rows)
        except Exception as exc:  # noqa: BLE001
            conn.close()
            return {
                "status": "skipped",
                "finding": Finding(
                    severity="info",
                    title="EXPLAIN ANALYZE failed",
                    detail=("Could not run the canonical atlas query "
                            "plan check. Inspect manually."),
                    evidence={"error": str(exc)[:200]},
                ),
            }
        finally:
            conn.close()

        # Look for the regression marker — but only flag if row count
        # is high enough that an index would actually matter. Below the
        # threshold, Seq Scan is the optimal plan and not a signal.
        has_seq_scan = SEQ_SCAN_REGRESSION_MARKER in plan_text
        if has_seq_scan and row_count >= SEQ_SCAN_REGRESSION_ROW_THRESHOLD:
            return {
                "status": "alert",
                "finding": Finding(
                    severity="alert",
                    title="canonical atlas query uses Seq Scan on VerificationEvent at scale",
                    detail=(f"EXPLAIN ANALYZE shows a sequential scan on "
                            f"VerificationEvent for the canonical atlas "
                            f"query, AND the table has {row_count:,} rows "
                            f"(above the {SEQ_SCAN_REGRESSION_ROW_THRESHOLD} "
                            f"threshold where an index should be used). "
                            f"An expected spatial index or cursor index "
                            f"has been dropped."),
                    evidence={
                        "plan_head": plan_text[:400],
                        "row_count": row_count,
                        "threshold": SEQ_SCAN_REGRESSION_ROW_THRESHOLD,
                    },
                ),
            }
        if has_seq_scan:
            # Seq Scan present but row count is low — this is expected
            # optimizer behavior, not a regression.
            return {
                "status": "healthy",
                "finding": Finding(
                    severity="info",
                    title=f"VerificationEvent uses Seq Scan ({row_count} rows; correct at this scale)",
                    detail=(f"At {row_count} rows (< "
                            f"{SEQ_SCAN_REGRESSION_ROW_THRESHOLD}), "
                            f"Postgres correctly chooses a sequential "
                            f"scan over any index scan. This becomes a "
                            f"regression signal only at higher row counts."),
                    evidence={"row_count": row_count},
                ),
            }
        return {"status": "healthy", "finding": None}

    # ------------------------------------------------------------------
    # Channel 4 (v9.04): pheromone-context — soldier_route_pinger
    # ------------------------------------------------------------------

    def _check_pheromone_route_pinger(
        self,
    ) -> tuple[list[Finding], dict[str, Any]]:
        """Read recent soldier_route_pinger deposits + surface latency drift.

        Channel 1 takes ONE timing per atlas endpoint per HYDRA pass.
        soldier_route_pinger pings continuously (every few minutes) and
        deposits a pheromone per result. This channel reads what the
        soldier already gathered: a continuous distribution rather
        than a point sample.

        The soldier's own kind classification is the signal:
          - alert deposit → route returned 5xx OR latency > alert thresh
          - drift deposit → latency above drift threshold but below alert
          - info deposit  → healthy ping

        Graceful: if PheromoneReader is empty (DB offline OR no recent
        pings), the channel surfaces no findings.
        """
        findings: list[Finding] = []
        evidence: dict[str, Any] = {
            "pheromone_route_pinger_status": "unknown",
        }

        try:
            reader = PheromoneReader(window_hours=WINDOW_FAST)
            deposits = reader.deposits_by_class("soldier_route_pinger",
                                                window_hours=WINDOW_FAST)
        except Exception as exc:  # noqa: BLE001 — graceful
            evidence["pheromone_route_pinger_status"] = (
                f"reader_error:{type(exc).__name__}"
            )
            return findings, evidence

        if not deposits:
            evidence["pheromone_route_pinger_status"] = "no_deposits_in_window"
            return findings, evidence

        evidence["pheromone_route_pinger_status"] = "ok"
        evidence["pheromone_route_pinger_count"] = len(deposits)

        # Group by node_id (each route gets a node_id like
        # 'route:/api/atlas/points'); summarize alert/drift/info per route.
        per_route: dict[str, dict[str, int]] = {}
        for d in deposits:
            bucket = per_route.setdefault(
                d.node_id, {"alert": 0, "drift": 0, "info": 0}
            )
            bucket[d.kind] = bucket.get(d.kind, 0) + 1

        problematic = {
            node_id: counts for node_id, counts in per_route.items()
            if counts.get("alert", 0) > 0 or counts.get("drift", 0) > 0
        }
        evidence["pheromone_route_pinger_problematic"] = len(problematic)

        if problematic:
            # Pick the worst few for the finding detail.
            ranked = sorted(
                problematic.items(),
                key=lambda kv: -(kv[1].get("alert", 0) * 7
                                 + kv[1].get("drift", 0) * 3),
            )[:5]
            top_node = ranked[0][0] if ranked else "(unknown)"
            findings.append(Finding(
                severity="drift",
                title=(f"soldier_route_pinger flagged "
                       f"{len(problematic)} route(s)"),
                detail=(
                    f"In the last {WINDOW_FAST:.0f}h soldier_route_pinger "
                    f"surfaced alert/drift on {len(problematic)} route(s) — "
                    f"distinct from channel 1's single-shot timing. "
                    f"Worst route: {top_node}. Top-5: "
                    f"{[(n, c) for n, c in ranked]}"
                ),
                evidence={
                    "problematic_count": len(problematic),
                    "top": [(n, c) for n, c in ranked],
                    "node_id": top_node,
                    "pheromone_context": "soldier_route_pinger",
                },
            ))

        return findings, evidence
