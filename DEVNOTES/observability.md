# DEVNOTES/observability.md — operator runbook for application metrics

**Origin:** BIG MISSION Tier 8 #11 Sanctum (`sanctum/2026-05-16-tier-7-8-thesis-test-and-freeze-line.md`).
**Audience:** operator running a deployed Polaris instance.
**Scope:** this document covers OBSERVING THE RUNNING APPLICATION.
An operator should be able to monitor production behavior with
nothing more than the running stack.

---

## The four headline metrics

`/api/metrics` returns these as JSON. They are operator-readable; no
metrics backend is required.

| Metric                          | What it measures                                     | What an operator should do if anomalous |
|---------------------------------|------------------------------------------------------|-----------------------------------------|
| `request_rate_per_minute`       | trailing-5-minute average request throughput        | Sudden spike = traffic shift or attack; sudden drop = stack-down |
| `error_rate_per_minute`         | trailing-5-minute average 5xx + uncaught responses  | Any non-zero is worth investigating; ≥1/min is a paging signal |
| `auth_failures_per_minute`      | trailing-5-minute average failed-login + WebAuthn  | Spike = credential-stuffing or coerced-operator probe |
| `duress_events_total`           | monotonic count of duress-code-triggered logins     | **NON-ZERO IS THE ANTI-COERCION ALARM.** Page immediately. |

Per the v9.27 Sanctum joint resolution: **duress events are the
headline.** An unobservable duress signal is the coercion-cover
failure mode — the duress-code feature (R11-5 / M2-10) becomes
decorative if no one alerts on it.

---

## How to monitor

### Minimal (single-host, dev or small-prod)

```bash
# Poll /api/metrics directly
watch -n 60 'curl -fsS http://localhost:5000/api/metrics | jq .'

# Tail structured logs for duress events specifically
docker compose -f polaris_web/docker-compose.prod.yml logs gunicorn -f \
  | jq -c 'select(.event == "duress_event")'
```

### Production (operator-side aggregation)

The Polaris process emits structured logs to stdout, one JSON object
per line. Pipe them wherever you already collect logs:

- **journald / systemd:** logs land in journald automatically; query with `journalctl -u polaris.service`
- **CloudWatch / GCP Logging:** standard JSON-log collectors handle the format
- **Loki + Grafana:** promtail's `json` parser handles the format directly
- **ELK stack:** Filebeat's `json` decoder handles the format

The `/api/metrics` endpoint is intended for periodic-poll scraping. If
you run Prometheus and want it natively, write a tiny exporter that
polls `/api/metrics` and exports the four counters. Polaris does NOT
ship a Prometheus exporter — per the v9.27 Sanctum joint resolution:
no metrics backend without an operator who runs it.

---

## Alert recommendations

If you have an alerting system, the baseline alerts (in increasing
severity):

```yaml
# Pseudocode — adapt to your alerting tool

- name: polaris-stack-down
  condition: request_rate_per_minute == 0 for 5m
  severity: warning
  runbook: docs/operator/DR-SINGLE-REGION.md

- name: polaris-error-spike
  condition: error_rate_per_minute > 1 for 5m
  severity: high
  runbook: docs/operator/OPERATIONS.md "Error spike"

- name: polaris-auth-failure-spike
  condition: auth_failures_per_minute > 10 for 5m
  severity: high
  runbook: "Suspected credential-stuffing or coerced-operator probe"

- name: polaris-duress-event
  condition: duress_events_total > 0 since last_check
  severity: CRITICAL
  runbook: "Coercion may be in progress. Contact operator immediately."
  notification: phone + sms + email
```

The duress alert is the load-bearing one. The others are
defense-in-depth.

---

## Structured-log event taxonomy

Every line emitted is `{"ts": ..., "pid": ..., "event": ..., ...fields}`.

| Event                  | When emitted                                  | Fields                                    |
|------------------------|-----------------------------------------------|-------------------------------------------|
| `auth_failure`         | bad password / WebAuthn / recovery-code      | `kind`, `username`                        |
| `duress_event`         | duress-code login succeeded                  | `individual_id`, `agency_id`              |
| (future)               | additional events added per ship             |                                           |

The taxonomy is deliberately minimal: events should be the
operator's load-bearing signals, not noise.

---

## What this is NOT

- A general-purpose APM (use your existing one).
- A tracing system (use OpenTelemetry separately if needed).
- A metrics-storage layer (use Prometheus / VictoriaMetrics / whatever
  you already run).

What this IS:

- A small operator-readable surface (JSON over HTTP + structured logs)
- A clear contract on the four metrics that matter
- A specific call-out that the duress-event signal is anti-coercion-
  load-bearing

---

## Integration points (for app.py + security.py)

```python
from polaris_web import observability

# In app.py:
@app.after_request
def _instrument_request(resp):
    observability.record_request()
    if resp.status_code >= 500:
        observability.record_error()
    return resp

@app.route('/api/metrics')
def metrics_endpoint():
    return jsonify(observability.MetricsSnapshot.collect().to_dict())

# In security.py:authenticate, on bad credentials:
observability.record_auth_failure(kind='password', username=username)

# In app.py:duress handler, after successful duress-code login:
observability.record_duress_event(individual_id=..., agency_id=...)
```

These are the call-sites the v9.27 ship wires in. Adding new
call-sites requires a Sanctum decision (per the v9.30 freeze line) —
the metric taxonomy is part of the constitutional record from v9.31
forward.

---

*Per BIG MISSION Tier 8 Sanctum 2026-05-16, item #11.*
