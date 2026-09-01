# RUNBOOKS.md: alert response runbooks

One runbook per shipped Prometheus alert. When an alert in
[`../../deploy/observability/polaris-alerts.yml`](../../deploy/observability/polaris-alerts.yml)
fires, find its section here by the exact alert name and work the
Trigger / Likely cause / Diagnosis / Remediation steps.

> **Status (v9.175).** Polaris ships the alert rules, the metrics they read,
> and the Alertmanager routing + receiver template
> ([`../../deploy/observability/alertmanager.yml`](../../deploy/observability/alertmanager.yml)),
> and CI proves that a duress increment reaches the pager webhook
> (`scripts/polaris-page-drill.sh`). What Polaris does not ship is the pager
> itself: the on-call product and its URL are yours, wired as described in
> [Paging](#paging-wiring-the-receiver). Until that file is mounted, these are
> reference procedures, not a claim that Polaris is paging anyone.

The severity labels (`sev1`/`sev2`/`sev3`) map to the SEV ladder in
[`DR.md`](DR.md) §2. The SLO thresholds these alerts
relate to are in [`SLOS.md`](SLOS.md).

`check_alert_runbooks` (in `polaris_checks`) asserts that every alert in
`polaris-alerts.yml` has exactly one section here and that no section here
names an alert that no longer exists. Keep that one-to-one mapping when you
edit either file.

---

## Table of contents

1. [PolarisAppDown](#polarisappdown)
2. [PolarisAppInfoAbsent](#polarisappinfoabsent)
3. [PolarisDuressEvent](#polarisduressevent)
4. [PolarisHigh5xx](#polarishigh5xx)
5. [PolarisHighDBLatency](#polarishighdblatency)
6. [PolarisHighRequestLatency](#polarishighrequestlatency)
7. [Paging: wiring the receiver](#paging-wiring-the-receiver)
8. [Cross-references](#cross-references)

---

## PolarisAppDown

**Severity:** SEV-1 · **Expression:** `up{job="polaris"} == 0` · **For:** 2m

**Trigger.** Prometheus has failed to scrape the `polaris` job for 2 minutes.
The target is down: the app is unreachable or the process has crashed.

**Likely cause.**
- The app container/process exited or is crash-looping (bad deploy, OOM kill,
  an import error after an upgrade).
- The reverse proxy (Caddy) is up but the app behind it is not, so `/metrics`
  is unreachable.
- A network/firewall change broke Prometheus's path to the scrape target.
- `prometheus.yml` points at the wrong `host:port` (misconfiguration, usually
  right after a move).

**Diagnosis.**
1. Hit liveness directly, bypassing Prometheus: `curl -fsS http://<target>/api/health/live`.
   A 200 with `{"status":"alive"}` means the process is up and the scrape path,
   not the app, is the problem; no response means the process is down.
2. Check the container state: `docker compose -f polaris_web/docker-compose.prod.yml ps`
   and `docker compose ... logs --tail=200 app`. Look for a crash loop or an
   OOM kill (exit 137).
3. Confirm Prometheus is aimed correctly: in the Prometheus UI, Status →
   Targets, find the `polaris` job and read the scrape error.

**Remediation.**
- Process down / crash-looping → treat as DR §4.1 (application crash). Read the
  last log lines, fix the cause (roll back the bad image, raise the memory
  limit if OOM), and restart: `docker compose ... up -d app`.
- App up but unreachable to the scraper → fix the network path or correct the
  `targets` in `prometheus.yml` and reload Prometheus.
- Confirm recovery: the alert clears once `up{job="polaris"} == 1` and
  `/api/health/ready` returns 200.

---

## PolarisAppInfoAbsent

**Severity:** SEV-1 · **Expression:** `absent(polaris_app_info)` · **For:** 5m

**Trigger.** The `polaris_app_info` gauge has been missing from scrapes for 5
minutes. The scrape is succeeding (otherwise `PolarisAppDown` would fire) but
the app is not serving its metadata gauge, so it is not serving `/metrics`
normally.

**Likely cause.**
- `/metrics` is returning 503 because `prometheus_client` is not installed in
  the running image (the endpoint degrades to 503 by design when the library is
  absent).
- In a multiprocess (gunicorn) deployment, `PROMETHEUS_MULTIPROC_DIR` is unset
  or unwritable, so the `MultiProcessCollector` has no samples to aggregate and
  `polaris_app_info` never appears.
- Something is proxying `/metrics` to a different process or a stale cache.

**Diagnosis.**
1. Scrape `/metrics` by hand: `curl -fsS http://<target>/metrics | head`. A 503
   confirms the endpoint is degraded; a 200 without a `polaris_app_info` line
   confirms the gauge specifically is missing.
2. If 503: check whether `prometheus_client` is importable in the running
   container (`docker compose ... exec app python -c "import prometheus_client"`).
3. If 200 but no gauge: check `PROMETHEUS_MULTIPROC_DIR` is set and the
   directory is writable inside the container; check the gunicorn worker count
   and that `child_exit` reaping is configured (see
   [`OPERATIONS.md`](OPERATIONS.md) metrics section).

**Remediation.**
- Missing library → rebuild/redeploy the image with `requirements.txt`
  installed; `prometheus_client` is a runtime dependency.
- Multiproc dir unset/unwritable → set `PROMETHEUS_MULTIPROC_DIR` to a writable
  tmpfs path in the prod compose and restart the app.
- Confirm recovery: `curl -fsS http://<target>/metrics | grep polaris_app_info`
  returns a line with the current `version` label.

---

## PolarisDuressEvent

**Severity:** SEV-1 · **Expression:** `increase(polaris_duress_events_total[5m]) > 0` · **For:** immediate

**This is not a system fault.** A token holder entered their enrolled DURESS
code during a verification: the system silently recorded a `DuressEvent` (the
coercer did not see anything unusual, by design) and incremented
`polaris_duress_events_total`. This alert exists so a human learns of the signal,
because an unread duress event is the coercion-cover failure mode (the whole
mechanism is decorative if no one reads the row). Treat it as a person signalling
they may be acting under coercion.

**Trigger.** `polaris_duress_events_total` increased in the last 5 minutes (at
least one duress-code match). The alert pages immediately (no `for` window):
duress cannot wait out a debounce. The shipped Alertmanager route matches it
with `group_wait: 0s` and re-pages every 15 minutes until a human resolves
the situation (see [Paging](#paging-wiring-the-receiver)).

**Likely cause.**
- A genuine duress-code entry: a holder forced to authenticate under coercion
  used their duress code to raise a silent alarm.
- A drill or an accidental duress-code entry (still investigate; do not assume).

**Diagnosis (out of band, never in front of the subject).**
1. Read the event on the operator duress dashboard (`/duress`): the `token_id`,
   `context_id`, `requesting_agency_id`, and timestamp of the `DuressEvent`.
2. Correlate with the verification context (which agency/where) to understand the
   situation the holder is signalling about. The append-only audit-of-record (C1)
   holds the surrounding events.
3. Do NOT contact the subject through the channel that may be compromised, and do
   NOT take any visible action that could reveal the alarm to a coercer.

**Remediation.** The response is a HUMAN safety/legal procedure, not a system
change — and the procedure itself is **operator-defined** (who is notified, how
the subject's safety is confirmed, what law-enforcement or welfare path applies).
Polaris's job ends at recording + paging; do not script an automated action
against the holder or the token. Do NOT revoke, lock, or alter the holder's
record in reaction (that could endanger them and corrupts the evidentiary
trail). Preserve the `DuressEvent` and the surrounding audit (they are
append-only). The alert clears on its own once no new event arrives in the
window; clearing is not "resolved" — the human response is.

---

## PolarisHigh5xx

**Severity:** SEV-2 · **For:** 10m
**Expression:** `sum(rate(polaris_requests_total{status=~"5.."}[5m])) / sum(rate(polaris_requests_total[5m])) > 0.01`

**Trigger.** The server-error (5xx) share of requests has exceeded 1% for 10
minutes. This is the alert-window version of the availability SLI in
[`SLOS.md`](SLOS.md) §2; sustained firing is burning the availability error
budget an order of magnitude faster than the 0.1% monthly budget allows.

**Likely cause.**
- A dependency the request path needs is failing: database unreachable/slow,
  Redis down, the ZK verifier binary missing or erroring.
- A bad deploy introduced an uncaught exception on a hot route (the
  after-request hook records uncaught exceptions as 5xx).
- Resource saturation (CPU/memory/connection-pool exhaustion) turning slow
  requests into errors.

**Diagnosis.**
1. Find which routes are erroring: in Prometheus,
   `sum by (route, status) (rate(polaris_requests_total{status=~"5.."}[5m]))`.
   A single route points at a code path; broad spread points at a shared
   dependency.
2. Check dependency health: `curl -fsS http://<target>/api/health/ready` and
   read the `checks` block (`database`, `redis`, `zk_binary`, `disk`). A
   `503` with one unhealthy check localizes the cause.
3. Correlate with `PolarisHighDBLatency`: if both are firing, the database is
   the likely root cause.
4. Pull recent error log lines by `X-Request-ID` (every response carries one;
   every `structured_log` line is tagged) to read the actual exception.

**Remediation.**
- Dependency down → follow the matching DR procedure (database → DR §4.2/§4.3,
  disk → DR §4.4, redis → restart the container; see DR §3 decision tree).
- Bad deploy → roll back to the previous image tag and confirm the 5xx share
  falls back under 1%.
- Saturation → scale workers (`WEB_CONCURRENCY`/`POLARIS_WORKERS`) or the
  database connection pool; see [`SCALING.md`](../reference/SCALING.md).
- Confirm recovery: the ratio query falls below 0.01 and the alert clears after
  the `for` window.

---

## PolarisHighDBLatency

**Severity:** SEV-2 · **For:** 5m
**Expression:** `histogram_quantile(0.99, sum(rate(polaris_db_query_latency_seconds_bucket[5m])) by (le)) > 5`

**Trigger.** The p99 of the `/api/health` database round-trip has exceeded 5
seconds for 5 minutes. The database is slow or saturated as the health probe
sees it. This matches the DB-latency SLO boundary in [`SLOS.md`](SLOS.md) §4
and the SEV-2 threshold in [`DR.md`](DR.md).

**Likely cause.**
- A long-running or blocking query/transaction holding locks (a migration
  without `lock_timeout`, a runaway analytical query).
- Connection-pool exhaustion: the probe waits for a free pgbouncer/Postgres
  connection.
- Database resource saturation (CPU, IO, memory) or a checkpoint/vacuum storm.
- The DB host is degraded (failing disk, noisy neighbour).

**Diagnosis.**
1. Confirm it is the database, not the probe: `curl -fsS http://<target>/api/health`
   and read the `database` check's latency field.
2. On the database, look for blocking:
   `SELECT pid, state, wait_event_type, query_start, query FROM pg_stat_activity
   WHERE state <> 'idle' ORDER BY query_start;` and inspect `pg_locks` for long
   waits.
3. Check pgbouncer pool saturation (`SHOW POOLS;` on the pgbouncer admin
   console); a full pool serializes the probe.
4. Check host-level IO/CPU on the database node.

**Remediation.**
- Blocking query → terminate it (`SELECT pg_terminate_backend(<pid>)`) once
  confirmed safe; if it is a migration, see DR + the migration-timeout guard
  (migrations SET LOCAL `lock_timeout`/`statement_timeout`).
- Pool exhausted → raise pool size or `WEB_CONCURRENCY` per
  [`SCALING.md`](../reference/SCALING.md); investigate connection leaks.
- Saturation → add IO/CPU or move the noisy workload; if the host is degraded,
  treat as a DR database-corruption/failover scenario (DR §4.2/§4.3).
- Confirm recovery: the p99 quantile falls back under 5s and the alert clears.

---

## PolarisHighRequestLatency

**Severity:** SEV-3 · **For:** 10m
**Expression:** `histogram_quantile(0.99, sum(rate(polaris_request_latency_seconds_bucket[5m])) by (le)) > 2`

**Trigger.** The p99 of per-route request latency has exceeded 2 seconds for 10
minutes. The service is degraded (slow), not down, which is why this is SEV-3.
This matches the latency SLO boundary in [`SLOS.md`](SLOS.md) §3.

**Likely cause.**
- Database latency bleeding into request latency (often firing alongside
  `PolarisHighDBLatency`).
- A slow downstream call or an expensive route (large `/api/atlas` viewport,
  ZK verification under load).
- Worker saturation: too few gunicorn workers for the offered load, so requests
  queue.
- A garbage-collection or cold-cache effect right after a deploy/restart.

**Diagnosis.**
1. Localize by route: `histogram_quantile(0.99, sum by (le, route)
   (rate(polaris_request_latency_seconds_bucket[5m])))`. One slow route points
   at that handler; broad slowness points at a shared resource.
2. Check whether `PolarisHighDBLatency` is also firing. If so, fix the database
   first (its runbook), and request latency usually follows.
3. Check worker saturation: request rate vs. worker count
   (`WEB_CONCURRENCY`/`POLARIS_WORKERS`) and CPU on the app node.

**Remediation.**
- Database-driven → work `PolarisHighDBLatency` first.
- Hot/expensive route → check for a missing bound or index; `/api/atlas` routes
  are hard-capped, so an uncapped expensive path is a regression worth a fix.
- Worker saturation → scale workers per [`SCALING.md`](../reference/SCALING.md).
- Post-deploy cold cache → if the p99 is trending back down on its own within
  the `for` window after a restart, monitor rather than act.
- Confirm recovery: the p99 quantile falls back under 2s and the alert clears.

---

## Paging: wiring the receiver

Alerts page through the `pager` receiver in
[`alertmanager.yml`](../../deploy/observability/alertmanager.yml): a generic
webhook whose URL is read from a mounted file, never written into config (the
URL usually embeds the integration key).

**Wire it.**
1. Create the pager integration in your on-call product and copy its webhook
   URL (PagerDuty Events v2, Opsgenie, Splunk On-Call, or a Slack/Teams incoming
   webhook all work; a bridge of your own works too).
2. Write the URL, one line, to a file outside the repo, and mount it read-only
   at `/etc/alertmanager/secrets/pager_webhook_url` in the Alertmanager
   container. Native `pagerduty_configs` / `opsgenie_configs` / `slack_configs`
   blocks are sketched in the file; their keys are mounted files as well.
3. `amtool check-config alertmanager.yml`, then reload Alertmanager.

**Prove it, before a real page.** Send a synthetic `PolarisDuressEvent`
through the real receiver and confirm the on-call is paged within seconds:
```bash
amtool --alertmanager.url=http://alertmanager:9093 alert add \
  alertname=PolarisDuressEvent severity=sev1 job=polaris \
  --annotation=summary="Drill: synthetic duress page"
```
Tell the on-call it is a drill first. Repeat after any change to the routing or
the pager product.

**What a PolarisDuressEvent page carries.** The webhook body is Alertmanager's
standard JSON: `receiver: pager`, `status: firing`, and an `alerts[]` entry with
`labels.alertname = PolarisDuressEvent`, `labels.severity = sev1`, and the
summary "Duress code matched". It does NOT carry the token or the holder; read
those out of band on the operator duress dashboard, as the
[PolarisDuressEvent](#polarisduressevent) runbook directs.

**Routing, as shipped.** `PolarisDuressEvent`: no grouping wait, re-page every
15 minutes. Other SEV-1: immediate, re-page hourly. SEV-2/3: 30s grouping,
re-page every 4 hours. `PolarisAppInfoAbsent` is inhibited while
`PolarisAppDown` fires (one page for one fact). Everything falls through to
`pager` by default: an alert with no route is the wrong failure mode.

**How this is verified.** `scripts/polaris-page-drill.sh` (the `page-drill` CI
job) runs the real Prometheus and Alertmanager on the shipped rules and config,
flips `polaris_duress_events_total` from 0 to 1 on a stub `/metrics`, and asserts
the page arrives at a webhook sink, with none arriving before the flip. The
product suite's `test_duress_increments_prometheus_counter` proves the app
increments that counter on a duress-code match.

---

## Cross-references

- [`../../deploy/observability/polaris-alerts.yml`](../../deploy/observability/polaris-alerts.yml): the shipped alert rules these runbooks respond to.
- [`../../deploy/observability/README.md`](../../deploy/observability/README.md): the Prometheus scrape config + how to wire the operator-gated Alertmanager backend.
- [`SLOS.md`](SLOS.md): the SLO targets and error budget the alert thresholds relate to.
- [`DR.md`](DR.md): the SEV ladder and the failure-class procedures referenced above.
- [`OPERATIONS.md`](OPERATIONS.md): the day-2 metrics reference.
- [`SCALING.md`](../reference/SCALING.md): worker/pool/index scaling levers.
