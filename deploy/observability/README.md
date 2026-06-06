# Polaris observability config (v9.115)

Ready-to-deploy Prometheus config for scraping Polaris and alerting on its
health. This is the **buildable** half; the alerting backend (Alertmanager + the
pager/notification target) is **operator-provided**.

## Files

| File | What it is |
|---|---|
| [`prometheus.yml`](prometheus.yml) | Scrape config (the `polaris` job hitting `/metrics`) + `rule_files` loading the alerts. |
| [`polaris-alerts.yml`](polaris-alerts.yml) | Six alerting rules, severity-labelled to the `docs/operator/DR.md` SEV ladder. |

## Deploy

1. Edit `prometheus.yml`: set `scrape_configs[0].static_configs.targets` to your
   deployment's `host:port` (the app behind Caddy).
2. Wire your Alertmanager: uncomment the `alerting:` block and point it at your
   Alertmanager, which routes to your pager/on-call (operator-provided — Polaris
   does not ship a notification backend).
3. Validate before reloading Prometheus:
   ```
   promtool check config prometheus.yml
   promtool check rules polaris-alerts.yml
   ```
   (Both pass as shipped.)

## Access control (required)

`/metrics` is unauthenticated by design (Prometheus scrapes it), but as of v9.128
it carries the **duress signal** (`polaris_duress_events_total`). A party who can
scrape `/metrics` can observe that — and roughly when — a duress alarm fired.
**`/metrics` MUST be reachable only by your monitoring**, never the public
internet: restrict it at the reverse proxy (Caddy) or the network layer to the
Prometheus host. That is the same audience that needs it to page, so the control
is *who can reach `/metrics`*, not the metric itself.

## The alerts

| Alert | Severity | Fires when |
|---|---|---|
| `PolarisAppDown` | SEV-1 | the scrape target is down for 2m |
| `PolarisAppInfoAbsent` | SEV-1 | `polaris_app_info` is absent for 5m |
| `PolarisDuressEvent` | SEV-1 | a duress-code match recorded a `DuressEvent` (fires immediately) |
| `PolarisHigh5xx` | SEV-2 | the 5xx share of requests exceeds 1% for 10m |
| `PolarisHighDBLatency` | SEV-2 | DB round-trip p99 exceeds 5s for 5m |
| `PolarisHighRequestLatency` | SEV-3 | request p99 exceeds 2s for 10m |

## Metric aggregation

As of v9.120 the app's `/metrics` aggregates across all gunicorn workers
(Prometheus multiprocess mode: `PROMETHEUS_MULTIPROC_DIR` is set in the prod
compose, each worker file-backs its samples, and the scrape sums them via a
`MultiProcessCollector`). So absolute counters reflect the whole app, and
absolute-count thresholds are safe to add. The rules above remain **ratios**
(`PolarisHigh5xx`) and **quantiles** (the latency alerts) because those are the
right shapes for these conditions, not because of a per-worker limitation.
