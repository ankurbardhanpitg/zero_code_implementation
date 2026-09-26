# Grafana dashboards

This folder is mounted into Grafana. Two dashboards are provisioned into the **OpenTelemetry** folder:

| File | Title | What it shows |
| --- | --- | --- |
| `zero-code-node.json` | **OpenTelemetry services** | Any app that exports OTLP. Multi-service RED, Node.js runtime, Tempo, and Loki. |
| `manual-python.json` | **Manual instrumentation — houses** | Only `app4` (`service.name` = `manual-python`). Server spans and the child spans written in code. No runtime metrics and no logs. |

## OpenTelemetry services

`zero-code-node.json` (uid `zero-code-node`) is the multi-service view.

It is a **multi-service** view: any app that exports OTLP to the collector can appear here. Use the **Service** and **Route** dropdowns at the top to filter almost every panel (for example `zero-code-node`, `zero-code-node-houses`, `zero-code-python`, or **All**).

Grafana dashboard JSON is strict JSON, so comments cannot live in the file itself. Each panel instead has a **description** (the `i` icon in Grafana). This README lists every metric and what it is for.

## Datasources

| Datasource | Used for |
|---|---|
| **Prometheus** | RED metrics, HTTP semantics, Node.js/process runtime |
| **Tempo** | Recent traces table and “Explore traces” link |
| **Loki** | Application logs panel and “Explore logs” link |

Spanmetrics (RED) come from the OpenTelemetry Collector **spanmetrics connector**, which turns traces into Prometheus series. Runtime and `http.server.*` series come from the app’s own OpenTelemetry metrics export (zero-code Node SDK / runtime instrumentation).

## Template variables

Both variables are populated from spanmetrics so a service only appears after it has sent at least one server span.

| Variable | Query | Purpose |
|---|---|---|
| `$service` | `label_values(traces_spanmetrics_calls_total, service_name)` | Filter panels by OTEL `service.name`. **All** is `.*`. |
| `$route` | `label_values(traces_spanmetrics_calls_total{service_name=~"$service", span_kind="SPAN_KIND_SERVER"}, http_route)` | Filter HTTP route. **All** is `.*`. |

Most PromQL queries also keep `span_kind="SPAN_KIND_SERVER"` so **inbound HTTP** is counted, not outbound client calls.

---

## Metric catalog

### 1. `traces_spanmetrics_calls_total`

**What it is:** Counter of finished spans, produced by the collector spanmetrics connector. Labels include `service_name`, `span_kind`, `http_route`, `http_request_method`, and `http_response_status_code`.

**What it is used for:** The **R** (Rate) and **E** (Errors) in RED.

| Panel | How it is used |
|---|---|
| Request rate (stat, top-left) | `sum(rate(...))` → requests per second for the selected service and route |
| Error rate (4xx + 5xx) | 4xx/5xx rate divided by total rate |
| Request rate by service (all apps) | `sum by (service_name)` — **not** filtered by `$service`, so every app is visible |
| Request rate (timeseries) | Same as the stat; series named `spanmetrics` |
| Error rate (timeseries) | Same ratio as the error-rate stat, over time |
| Request rate by route | `sum by (method, route, status)` so you can see which endpoint and status code drive traffic |
| Status codes | `sum by (http_response_status_code)` stacked bars |
| Service / Route dropdowns | `label_values(...)` to populate the variables |

**Typical PromQL (rate):**

```promql
sum(rate(traces_spanmetrics_calls_total{
  service_name=~"$service",
  span_kind="SPAN_KIND_SERVER",
  http_route=~"$route"
}[$__rate_interval]))
```

**Typical PromQL (errors):** 4xx and 5xx only, then divide by the total rate (`clamp_min(..., 1e-9)` avoids divide-by-zero when there is no traffic).

---

### 2. `traces_spanmetrics_duration_milliseconds_bucket`

**What it is:** Histogram buckets of server-span duration (milliseconds), also from the spanmetrics connector. The `_bucket` suffix is what `histogram_quantile()` needs.

**What it is used for:** The **D** (Duration) in RED — latency percentiles.

| Panel | How it is used |
|---|---|
| Latency p95 (stat) | `histogram_quantile(0.95, ...)` — yellow ≥ 50 ms, red ≥ 200 ms |
| Latency p99 (stat) | `histogram_quantile(0.99, ...)` — yellow ≥ 100 ms, red ≥ 500 ms |
| Latency (p50 / p95 / p99) | Same histogram, three quantiles over time. Exemplars jump to Tempo. |
| p95 latency by route | Quantile grouped by `http_route` so a slow endpoint stands out |

**Typical PromQL:**

```promql
histogram_quantile(0.95, sum by (le) (
  rate(traces_spanmetrics_duration_milliseconds_bucket{
    service_name=~"$service",
    span_kind="SPAN_KIND_SERVER",
    http_route=~"$route"
  }[$__rate_interval])
))
```

---

### 3. `http_server_request_duration_seconds_count`

**What it is:** Counter side of the OpenTelemetry **HTTP server** duration histogram (`http.server.request.duration`). Exported by the app itself (semantic conventions), not by spanmetrics.

**What it is used for:** Overlay on the **Request rate** timeseries (legend `http server`) next to spanmetrics, so you can confirm collector-derived rate matches the SDK metric. Filtered by `job=~"$service"` (Prometheus job label is usually the service name).

Only the `_count` series is used here (rate of requests). The `_bucket` / `_sum` series exist in Prometheus but are not plotted on this dashboard.

---

### 4. `nodejs_eventloop_delay_p50_seconds` and `nodejs_eventloop_delay_p99_seconds`

**What they are:** Node.js runtime metrics for event-loop lag (how long a queued callback waits before the loop can run it).

**What they are used for:** **Event loop delay** panel. High p99 delay usually means the process is blocked (CPU-heavy work, sync I/O, GC pauses). These series only exist for Node.js services; Python apps will leave this panel empty.

---

### 5. `process_resident_memory_bytes`

**What it is:** OS resident set size (RSS) of the process — memory actually held in RAM.

**What it is used for:** **Memory** panel, series `RSS`. Useful for leak detection and container limit planning. Available for Node and typically for other runtimes that export process metrics.

---

### 6. `v8js_memory_heap_used_bytes`

**What it is:** V8 heap currently in use (JavaScript objects). Smaller than RSS because RSS also includes native memory, stacks, and mapped files.

**What it is used for:** **Memory** panel, series `heap used`. A rising heap with a rising RSS often points to a JS leak; a rising RSS with a flat heap often points to native buffers or external memory. Node.js only.

---

### 7. `process_cpu_seconds_total`

**What it is:** Cumulative CPU time consumed by the process (counter).

**What it is used for:** **CPU and event-loop utilization** panel. `rate(...)` turns the counter into a utilization-style ratio (1.0 ≈ one full core). High CPU with high event-loop delay usually means the loop is busy with JS work.

---

### 8. `nodejs_eventloop_utilization_ratio`

**What it is:** Fraction of time the Node.js event loop was **not idle** (ELU).

**What it is used for:** Same panel as CPU (`event loop` series). ELU near 1.0 means the loop has almost no idle time even if OS CPU looks moderate (or the reverse). Complements delay metrics: delay is “how late”, utilization is “how busy”.

---

## Non-metric panels (traces and logs)

These are not Prometheus metrics.

| Panel | Query | Purpose |
|---|---|---|
| Recent traces | Tempo TraceQL `{ resource.service.name =~ "${service}" }` | Last 30 traces for the selected service; click a Trace ID for the waterfall |
| Application logs | Loki `{service_name=~"$service"}` | OTLP logs. `console.log` is **not** captured; use pino, winston, or another instrumented logger |

Dashboard links at the top open Grafana Explore with the same service filter.

---

## Panel map (layout)

```
[ Request rate ] [ Error rate 4xx+5xx ] [ Latency p95 ] [ Latency p99 ]
[ Request rate by service (all apps)                                      ]

── Selected service — Prometheus metrics ──
[ Request rate (spanmetrics + http) ] [ Error rate ] [ Latency p50/p95/p99 ]
[ Request rate by route             ] [ p95 by route] [ Status codes       ]

── Runtime (Node.js / process) ──
[ Event loop delay ] [ Memory (RSS + heap) ] [ CPU + event-loop utilization ]

── Tempo traces and Loki logs ──
[ Recent traces                    ] [ Application logs ]
```

---

## Quick “which metric for what” cheat sheet

| Goal | Metric |
|---|---|
| How busy is the HTTP API? | `traces_spanmetrics_calls_total` (and optionally `http_server_request_duration_seconds_count`) |
| Are clients or the server failing? | `traces_spanmetrics_calls_total` with `http_response_status_code=~"[45].."` |
| How slow are requests? | `traces_spanmetrics_duration_milliseconds_bucket` |
| Which route is hot or slow? | same two spanmetrics series, grouped by `http_route` |
| Is Node blocked? | `nodejs_eventloop_delay_p50_seconds` / `_p99_seconds` |
| Is the loop saturated? | `nodejs_eventloop_utilization_ratio` |
| CPU load | `process_cpu_seconds_total` |
| Memory growth / leaks | `process_resident_memory_bytes`, `v8js_memory_heap_used_bytes` |
| Why was this request slow? | Tempo traces (and spanmetrics exemplars on latency graphs) |
| What did the app log? | Loki `{service_name=~"$service"}` |

---

## Manual instrumentation — houses

`manual-python.json` (uid `manual-python`) is only for **app4**. The service name is fixed to `manual-python`, so other apps do not appear here.

The same spanmetrics series are used (`traces_spanmetrics_calls_total` and `traces_spanmetrics_duration_milliseconds_bucket`), but the panels split **server** spans from **internal** spans created in `app4/modules/house/store.py`.

| Variable | Query | Purpose |
|---|---|---|
| `$route` | `http_route` on `SPAN_KIND_SERVER` for `manual-python` | Filter inbound HTTP panels |
| `$span` | `span_name` on `SPAN_KIND_INTERNAL` for `manual-python` | Filter `houses.list`, `houses.get_by_id`, and `houses.read` |

| Panel | What it shows |
|---|---|
| Server request rate / 404 / p95 | Inbound spans from `server_span()` |
| Manual child spans | Internal span rate |
| Rate by span name | Server and child span names together |
| Server spans by route and status | Method, route template, status code |
| Child span rate / p95 | `houses.list`, `houses.get_by_id`, `houses.read` |
| Recent server traces | Tempo, filtered by route |
| Traces containing the manual span | Tempo, filtered by child span name |

`house.id` and `house.found` are attributes on the `houses.get_by_id` span. They show up in the Tempo waterfall. They are not Prometheus labels. This app does not export logs.
