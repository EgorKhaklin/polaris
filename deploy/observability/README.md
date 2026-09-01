# Polaris observability config (v9.175)

Ready-to-deploy Prometheus + Alertmanager config for scraping Polaris,
alerting on its health, and paging a human. Polaris ships the rules, the
routing, and the receiver template, and proves in CI that a duress event
reaches the pager webhook. What stays yours: the pager product and its URL.

## Files

| File | What it is |
|---|---|
| [`prometheus.yml`](prometheus.yml) | Scrape config (the `polaris` job hitting `/metrics`), `rule_files` loading the alerts, and `alerting` pointing at the Alertmanager below. |
| [`polaris-alerts.yml`](polaris-alerts.yml) | Six alerting rules, severity-labelled to the `docs/operator/DR.md` SEV ladder. |
| [`alertmanager.yml`](alertmanager.yml) | Routing (duress: no wait, re-page every 15m; other SEV-1: immediate; SEV-2/3: batched) and the `pager` webhook receiver, whose URL is read from a mounted secret file. |

## Deploy

1. Edit `prometheus.yml`: set `scrape_configs[0].static_configs.targets` to your
   deployment's `host:port` (the app behind Caddy). If your Alertmanager is not
   reachable as `alertmanager:9093`, change the `alerting` target too.
2. Write the pager URL (one line) to a file that is NOT committed and mount it
   into Alertmanager at `/etc/alertmanager/secrets/pager_webhook_url`. Any
   webhook a pager accepts works: PagerDuty Events v2, Opsgenie, Splunk On-Call,
   a Slack/Teams incoming webhook. Prefer a native integration? Uncomment one of
   the `*_configs` blocks in `alertmanager.yml`; their keys are mounted files
   too (`routing_key_file`, `api_key_file`, `api_url_file`), never inline.
3. Validate before (re)loading:
   ```
   promtool check config prometheus.yml
   promtool check rules polaris-alerts.yml
   amtool check-config alertmanager.yml
   ```
   CI runs exactly these on every push (`scripts/polaris-page-drill.sh`).
4. Send yourself a synthetic duress page through the real receiver, before you
   need it for real:
   ```
   amtool --alertmanager.url=http://alertmanager:9093 alert add \
     alertname=PolarisDuressEvent severity=sev1 job=polaris \
     --annotation=summary="Drill: synthetic duress page"
   ```
   The `pager` receiver should notify within seconds (no grouping wait on that
   route). If it does not, the problem is between Alertmanager and your pager
   product, not in Polaris.

## The page path is proven, not asserted

`scripts/polaris-page-drill.sh` (run by the `page-drill` CI job) starts the real
Prometheus and Alertmanager binaries (digest-pinned) on the shipped rules and
config, points them at a stub `/metrics` and a webhook sink, flips
`polaris_duress_events_total` from 0 to 1, and asserts the `PolarisDuressEvent`
page arrives at the webhook (receiver `pager`, severity `sev1`, firing), with no
page beforehand. The app half, a duress-code match incrementing that counter,
is `test_duress_increments_prometheus_counter` in the product suite. Together
they cover the whole path from a holder's duress code to the pager URL.

## Access control (required)

`/metrics` is unauthenticated by design (Prometheus scrapes it), but as of v9.128
it carries the **duress signal** (`polaris_duress_events_total`). A party who can
scrape `/metrics` can observe that, and roughly when, a duress alarm fired.
**`/metrics` MUST be reachable only by your monitoring**, never the public
internet: restrict it at the reverse proxy (Caddy) or the network layer to the
Prometheus host. That is the same audience that needs it to page, so the control
is *who can reach `/metrics`*, not the metric itself.

## The alerts

| Alert | Severity | Fires when | Route |
|---|---|---|---|
| `PolarisAppDown` | SEV-1 | the scrape target is down for 2m | immediate, re-page hourly |
| `PolarisAppInfoAbsent` | SEV-1 | `polaris_app_info` is absent for 5m | immediate (inhibited while AppDown fires) |
| `PolarisDuressEvent` | SEV-1 | a duress-code match recorded a `DuressEvent` (fires immediately) | no wait, re-page every 15m |
| `PolarisHigh5xx` | SEV-2 | the 5xx share of requests exceeds 1% for 10m | batched 30s, re-page 4h |
| `PolarisHighDBLatency` | SEV-2 | DB round-trip p99 exceeds 5s for 5m | batched 30s, re-page 4h |
| `PolarisHighRequestLatency` | SEV-3 | request p99 exceeds 2s for 10m | batched 30s, re-page 4h |

## Metric aggregation

As of v9.120 the app's `/metrics` aggregates across all gunicorn workers
(Prometheus multiprocess mode: `PROMETHEUS_MULTIPROC_DIR` is set in the prod
compose, each worker file-backs its samples, and the scrape sums them via a
`MultiProcessCollector`). So absolute counters reflect the whole app, and
absolute-count thresholds are safe to add. The rules above remain **ratios**
(`PolarisHigh5xx`) and **quantiles** (the latency alerts) because those are the
right shapes for these conditions, not because of a per-worker limitation.
