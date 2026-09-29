# Instrumentation in app4

app4 records traces, metrics, and logs by hand. No Flask instrumentor is installed, and the process does not start an OpenTelemetry agent. A span, a metric point, or a log record exists only where this code creates it.

`app.py` installs the three pipelines once, before the first request:

1. `init_tracing()` — `TracerProvider`, so spans can be opened
2. `init_logging()` — `LoggerProvider`, so `logging` calls become OpenTelemetry log records
3. `init_metrics()` — `MeterProvider`, and the HTTP instruments the request hooks record into

All three copy the same resource from `tracing.create_resource()` (`service.name` = `manual-python`). `metrics.py` and `logs.py` import that helper. They do not modify `tracing.py`.

## Trace instrumentation

Spans exist only where this code opens them.

| File | Role |
| --- | --- |
| `tracing.py` | Builds the SDK pipeline and the `server_span` decorator |
| `app.py` | Installs that pipeline, propagates incoming trace context, spans `GET /` |
| `modules/house/routes.py` | Wraps each house view with `server_span` |
| `modules/house/store.py` | Opens the child spans around reading `data/houses.json` |
| `modules/house/controller.py` | No spans. The `(body, 404)` return is what the server span reads for status. House lookups also emit logs; see [Log instrumentation](#log-instrumentation) |

`scripts/seed_houses.py` and `scripts/traffic_houses.py` do not create spans. The traffic script only sends HTTP requests so the API has something to record.

### SDK pipeline

`app.py` calls `init_tracing()` once, before the house blueprint is imported. `store.py` calls `trace.get_tracer()` at import time. If the provider is not installed yet, that call receives the API's default proxy tracer.

`init_tracing()` in `tracing.py` wires four objects:

1. **Resource.** Identity copied onto every span from this process.

   - `service.name` = `manual-python` (the manual-python dashboard filters on this)
   - `service.version` = `1.0.0`
   - `host.name` = the machine hostname
   - `deployment.environment` = `DEPLOYMENT_ENVIRONMENT`, or `local`

2. **TracerProvider.** Owns the resource and the processors added to it.

3. **OTLPSpanExporter.** POSTs ended spans as OTLP over HTTP. The URL is resolved by `_traces_endpoint()`:

   - `OTEL_EXPORTER_OTLP_TRACES_ENDPOINT` when that variable is set
   - otherwise `OTEL_EXPORTER_OTLP_ENDPOINT`, default `http://localhost:4318`
   - `/v1/traces` is appended when the base URL does not already end with it

4. **BatchSpanProcessor.** Ended spans sit in a queue. The processor flushes the queue on a timer (`schedule_delay_millis=1000`), about once a second, instead of exporting once per span.

`trace.set_tracer_provider(provider)` publishes that provider on the process-wide hook. Later `trace.get_tracer(...)` calls in this process return tracers bound to it.

`app.run(..., debug=True, use_reloader=False)` keeps a single process. The Werkzeug reloader would import `app.py` again in a child process and install a second provider.

### Two tracers, one provider

Both tracers share the provider, so they share the resource and the exporter. They differ by instrumentation scope name, which shows up on the span as the instrumentation library:

| Tracer | Scope name | What it records |
| --- | --- | --- |
| `_http_tracer()` in `tracing.py` | `app4.http` | Incoming HTTP server spans |
| module-level `tracer` in `store.py` | `app4.house` | Internal spans around the JSON file |

The HTTP tracer is resolved inside the request, when the view runs. The house tracer is resolved when `store.py` is imported.

### One request

Flask runs the hooks in this order.

#### 1. Attach incoming context

`attach_context_with_trace_header` is a `before_request` hook. It runs before the view.

`extract(request.headers)` reads W3C `traceparent` and `tracestate` from the incoming headers. `context.attach(...)` pushes that context onto the current thread's OpenTelemetry context stack and returns a token. The token is stored on the WSGI environ under `previous_ctx_token`, because `before_request` and `teardown_request` are separate functions and cannot share a local variable.

`server_span` does not take a parent span argument. `start_as_current_span()` parents the new span on whatever context is current. With a `traceparent`, the server span continues the caller's trace. With no `traceparent`, the extracted context is empty and the server span starts a new trace.

#### 2. Open the server span

`server_span(route)` returns a decorator. It is applied in two equivalent ways:

```python
@server_span("/")
def health(): ...
```

```python
view_func=server_span("/houses")(house_controller.fetch_houses)
```

The house views are wrapped at `add_url_rule` time because the functions live in `controller.py`. The string passed in is both the span-name suffix and the `http.route` attribute. It includes the `/houses` prefix, because the decorator does not see `url_prefix="/houses"` from `register_blueprint`.

The wrapper calls:

```python
_http_tracer().start_as_current_span(
    f"{request.method} {route}",
    kind=SpanKind.SERVER,
    attributes={
        "http.request.method": request.method,
        "http.route": route,
        "url.path": request.path,
    },
)
```

`SpanKind.SERVER` marks this span as the service's view of an inbound request. `http.route` is the template (`/houses/<int:house_id>`). `url.path` is the concrete path (`/houses/3` or `/houses/999`), so those two requests share a route and differ by path.

The `with` block does two things: it makes this span the current span, and it ends the span when the block exits. The view, the controller, and the store all run inside that block.

#### 3. Open child spans

`store.py` also uses `start_as_current_span()`, with no parent argument and with the default kind, `INTERNAL`. Because those calls happen while the server span is current, the new spans become its children. A span opened inside another `with` block becomes current for nested calls, then the parent becomes current again when the inner block ends.

`GET /houses`:

```
GET /houses                         SERVER   server_span("/houses")
  └── houses.list                   INTERNAL store.get_all
        └── houses.read             INTERNAL store._read_houses
```

`GET /houses/<id>`:

```
GET /houses/<int:house_id>          SERVER   server_span("/houses/<int:house_id>")
  └── houses.get_by_id              INTERNAL store.get_by_id
        └── houses.read             INTERNAL store._read_houses
```

`GET /` has only the server span. The health view does not touch the store.

Attributes written on the child spans:

| Span | Attributes |
| --- | --- |
| `houses.list` | `house.count` |
| `houses.get_by_id` | `house.id`, `house.found` (`true` or `false`) |
| `houses.read` | `house.count` (`0` when `houses.json` is missing) |

Returning from inside a `with` block still exits it. `house.found` is set before `houses.get_by_id` ends.

#### 4. Record the HTTP status

After the view returns, `response_status_code()` reads the status from whatever Flask view shape came back:

- a response object, via `status_code`
- a tuple such as `(body, 404)` or `(body, 404, headers)`, via the integer piece, or a string like `"404 NOT FOUND"`

That number is written to `http.response.status_code`. Status 500 and above also calls `span.set_status(Status(StatusCode.ERROR))`.

A missing house returns `(jsonify({"error": "house not found"}), 404)` from `controller.py`. The server span records `http.response.status_code` = 404 and leaves the span status unset. Backends display an unset status as successful. A 404 is an answer the handler produced on purpose.

If the view raises, the wrapper sets `http.response.status_code` to 500 and re-raises. Leaving the `with` block still ends the span. `start_as_current_span` records the exception on the span and sets the span status to `ERROR` on the way out.

#### 5. Detach the context

`restore_context_on_teardown` is a `teardown_request` hook. Flask runs it after the response and also when an exception escapes the view. `context.detach(token)` pops the stack back to the context that was current before `attach()`. The next request on this worker thread does not inherit this request's trace.

### What gets exported

A span is eligible for export when its `with` block ends. `BatchSpanProcessor` holds those spans and the `OTLPSpanExporter` POSTs them to the collector. With the default endpoint that is `http://localhost:4318/v1/traces`. Spans can show up in Grafana about a second after the request, because of the batch delay.

There is no outbound `inject()` call, because the house API does not make an outbound HTTP request of its own. Metrics and logs use their own providers, described below.

## Metric instrumentation

Metrics are pull-and-push instruments on a `MeterProvider`. Nothing in Flask is auto-instrumented. `app.py` records the HTTP counter and histogram. `metrics.py` registers process gauges that the exporter samples on a timer.

| File | Role |
| --- | --- |
| `metrics.py` | Builds the SDK pipeline, creates the instruments, returns the HTTP ones to `app.py` |
| `app.py` | Counts each request, then records latency and errors from the response |

`scripts/seed_houses.py` and `scripts/traffic_houses.py` do not record metrics. The traffic script only sends HTTP requests so the API has something to record.

### SDK pipeline

`app.py` calls `init_metrics()` once, after `init_tracing()` and `init_logging()`. The call returns a dict of instruments. `app.py` keeps that dict as `request_instruments` and writes into it from the request hooks.

`init_metrics()` in `metrics.py` wires four objects:

1. **Resource.** The same identity as traces, from `tracing.create_resource()`. `service.name` is `manual-python`. The **Manual metrics — houses** dashboard filters on Prometheus `job="manual-python"`, which the collector sets from that resource attribute.

2. **MeterProvider.** Owns the resource and the reader below it.

3. **OTLPMetricExporter.** POSTs metrics as OTLP over HTTP. The URL is resolved by `_metrics_endpoint()`:

   - `OTEL_EXPORTER_OTLP_METRICS_ENDPOINT` when that variable is set
   - otherwise `OTEL_EXPORTER_OTLP_ENDPOINT`, default `http://localhost:4318`
   - `/v1/metrics` is appended when the base URL does not already end with it
   - a base that already ends in `/v1/traces` has that suffix removed first, so a traces URL is not turned into `/v1/traces/v1/metrics`

4. **PeriodicExportingMetricReader.** Collects every instrument and asks the exporter to POST, every `5000` ms. Request code never exports a metric itself. It only updates in-memory instruments. The reader is what sends them.

`metrics.set_meter_provider(provider)` publishes that provider on the process-wide hook. `metrics.get_meter("app4.metrics", version)` then returns a meter bound to it. The scope name `app4.metrics` is independent of the `app4.http` and `app4.house` tracers.

### Instruments

`_create_request_instruments` builds the three instruments `app.py` records. They are returned to the caller. Process gauges are registered on the same meter and are not part of that return value.

| Instrument | Kind | Unit | Who records it |
| --- | --- | --- | --- |
| `traffic_volume` | counter | `request` | `before_request`, once per request that reaches the hook |
| `error_rate` | counter | `request` | `after_request` or `teardown_request`, when the status is 400 or higher |
| `http.server.request.duration` | histogram | `s` | same hooks, duration of that request |
| `process.cpu.utilization` | observable gauge | `1` | reader callback, `psutil.cpu_percent(interval=None) / 100` |
| `process.memory.usage` | observable up-down counter | `By` | reader callback, `psutil.virtual_memory().used` |

The histogram name follows the HTTP semantic convention. The collector's Prometheus exporter turns these names into series such as `traffic_volume_request_total`, `error_rate_request_total`, `http_server_request_duration_seconds_bucket`, `process_cpu_utilization_ratio`, and `process_memory_usage_bytes`.

The two process instruments are pull instruments. The request path never calls them. When the reader exports, it invokes each callback and takes the `Observation` it returns. `cpu_percent(interval=None)` returns utilization since the previous call and does not block the export thread. Dividing by 100 stores a ratio in `0..1`, matching unit `1`.

### One request

The HTTP instruments are recorded from the same Flask hooks as trace context. The view itself does not call the meter.

1. **`before_request`** stores `time.time_ns()` on the WSGI environ under `request_start_ns`, then adds `1` to `traffic_volume` with attribute `http.route`. The route comes from `_http_route()`: the matched pattern (`/houses/<int:house_id>`), or the concrete path when nothing matched. A trailing slash is stripped so the list route is `/houses`, the same value `server_span` records. Failed requests are counted here too, because this hook runs before the view.

2. **`after_request`** calls `_record_http_metrics(response.status_code)`. The histogram records `(now - start) / 1_000_000_000` seconds, with `http.request.method`, `http.route`, and `http.response.status_code`. Status 400 and above also adds `1` to `error_rate` with `http.route` and `http.response.status_code`. A missing house is a 404, so it increments `error_rate`.

3. **`teardown_request`** calls `_record_http_metrics(500)` only when the view raised. Flask skips `after_request` in that case, so the 500 would otherwise never be recorded.

`after_request` and `teardown_request` can both run for one successful request. `_record_http_metrics` sets `http_metrics_recorded` on the environ and returns immediately on the second call, so latency is recorded once.

### What gets exported

The reader exports every 5 seconds to `http://localhost:4318/v1/metrics` by default. The collector's metrics pipeline writes those series to Prometheus. The **Manual metrics — houses** dashboard (`manual-python-metrics`) reads them. Panels can stay empty for a few seconds after the first request, until the next export.

## Log instrumentation

Logs use the standard library `logging` module. `LoggingHandler` turns each log record into an OpenTelemetry log and hands it to a `LoggerProvider`. That is the same bridge as `logs_solution`. `logs_solution` prints records with `ConsoleLogExporter`. This process POSTs them with `OTLPLogExporter` so they show up in Loki.

| File | Role |
| --- | --- |
| `logs.py` | Builds the SDK pipeline and attaches `LoggingHandler` to the root logger |
| `app.py` | Calls `init_logging()`, and logs an INFO line from `GET /` |
| `modules/house/controller.py` | Logs INFO for a found house or list, and WARN when the id is missing |

`store.py` does not log. Its work stays on the child spans.

### SDK pipeline

`app.py` calls `init_logging()` once, after `init_tracing()` and before `init_metrics()`. The provider has to be installed before the first `logging` call that should be exported. The house blueprint is imported after that call.

`init_logging()` in `logs.py` wires four objects:

1. **Resource.** The same identity as traces, from `tracing.create_resource()`. Loki stores `service.name` as the label `service_name`. The **Manual logs — houses** dashboard filters on `service_name="manual-python"`.

2. **LoggerProvider.** Owns the resource and the processor below it.

3. **OTLPLogExporter.** POSTs log records as OTLP over HTTP. The URL is resolved by `_logs_endpoint()`:

   - `OTEL_EXPORTER_OTLP_LOGS_ENDPOINT` when that variable is set
   - otherwise `OTEL_EXPORTER_OTLP_ENDPOINT`, default `http://localhost:4318`
   - `/v1/logs` is appended when the base URL does not already end with it
   - a base that already ends in `/v1/traces` or `/v1/metrics` has that suffix removed first

4. **BatchLogRecordProcessor.** Records sit in a queue and are flushed on the processor's timer, instead of one HTTP POST per `logging` call.

`set_logger_provider(provider)` publishes that provider on the process-wide hook.

The bridge onto Python logging is two handlers on the root logger:

- `logging.basicConfig(level=logging.INFO)` adds a console handler, the same as `logs_solution`, so lines still print in the terminal.
- `LoggingHandler(level=logging.INFO, logger_provider=provider)` copies each record into the OpenTelemetry pipeline.

Level INFO drops DEBUG before either handler sees it. Loggers created with `logging.getLogger(__name__)` propagate to the root logger, so the handler covers `app` and `modules.house.controller` without attaching a handler to each one.

`LoggingHandler` sets the log record's context from the current OpenTelemetry context. A `logging` call made inside `server_span`'s `with` block therefore carries that server span's trace id and span id. Loki keeps them as `trace_id` and `span_id`. The Grafana Loki datasource turns `trace_id` into a link to Tempo.

### Where lines are emitted

The calls sit inside the view, which runs inside the server span. `after_request` runs after that span has ended, so the log lines are not written there.

| Call | Level | When | `extra` attributes |
| --- | --- | --- | --- |
| `logger.info("House API health check")` in `health()` | INFO | `GET /` | none |
| `logger.info("Found %s houses", ...)` in `fetch_houses` | INFO | `GET /houses` | `house.count` |
| `logger.info("Found house %s", ...)` in `fetch_house_by_id` | INFO | the id exists | `house.id` |
| `logger.warning("Could not find house with id %s", ...)` | WARN | the id is missing (HTTP 404) | `house.id` |

`extra` keys are copied onto the OpenTelemetry log record as attributes. Loki stores `house.count` as `house_count` and `house.id` as `house_id`. Python's `WARNING` level is exported as severity text `WARN`, which Loki labels `detected_level`.

### What gets exported

A record is eligible for export when `LoggingHandler.emit` runs, which is the `logging` call itself. `BatchLogRecordProcessor` holds those records and the `OTLPLogExporter` POSTs them to the collector. With the default endpoint that is `http://localhost:4318/v1/logs`. The collector's logs pipeline forwards them to Loki. The **Manual logs — houses** dashboard (`manual-python-logs`) reads that stream. The **Level** dropdown filters `detected_level` (`INFO`, `WARN`, `ERROR`, `FATAL`). Lines can show up a few seconds after the request, because of the batch delay on the processor and on the collector.
