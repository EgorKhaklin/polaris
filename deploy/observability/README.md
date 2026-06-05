# Polaris observability config (v9.115)

Ready-to-deploy Prometheus config for scraping Polaris and alerting on its
health. This is the **buildable** half; the alerting backend (Alertmanager + the
pager/notification target) is **operator-provided**.

## Files

| File | What it is |
|---|---|
| [`prometheus.yml`](prometheus.yml) | Scrape config (the `polaris` job hitting `/metrics`) + `rule_files` loading the alerts. |
| [`polaris-alerts.yml`](polaris-alerts.yml) | Five alerting rules, severity-labelled to the `docs/operator/DR.md` SEV ladder. |

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

## The alerts

| Alert | Severity | Fires when |
|---|---|---|
| `PolarisAppDown` | SEV-1 | the scrape target is down for 2m |
| `PolarisAppInfoAbsent` | SEV-1 | `polaris_app_info` is absent for 5m |
| `PolarisHigh5xx` | SEV-2 | the 5xx share of requests exceeds 1% for 10m |
| `PolarisHighDBLatency` | SEV-2 | DB round-trip p99 exceeds 5s for 5m |
| `PolarisHighRequestLatency` | SEV-3 | request p99 exceeds 2s for 10m |

## Metric-aggregation caveat (honest)

The app's `/metrics` uses a per-worker Prometheus registry, so **absolute
counters are per-gunicorn-worker** until multiprocess aggregation lands (a known
Wave 4 follow-up in `docs/PRODUCTION-READINESS.md`). The rules above are
deliberately **ratios** (`PolarisHigh5xx`) and **quantiles** (the latency
alerts), which stay valid per worker — they do not depend on summing across
workers. Do not add absolute-count thresholds (e.g. "more than N requests")
until aggregation is in place; they would read low by the worker count.
