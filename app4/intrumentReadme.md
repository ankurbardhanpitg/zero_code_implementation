# Trace instrumentation in app4

app4 records traces by hand. No Flask instrumentor is installed, and the process does not start an OpenTelemetry agent. Spans exist only where this code opens them.

| File | Role |
| --- | --- |
| `tracing.py` | Builds the SDK pipeline and the `server_span` decorator |
| `app.py` | Installs that pipeline, propagates incoming trace context, spans `GET /` |
| `modules/house/routes.py` | Wraps each house view with `server_span` |
| `modules/house/store.py` | Opens the child spans around reading `data/houses.json` |
| `modules/house/controller.py` | No spans. The `(body, 404)` return is what the server span reads for status |

`scripts/seed_houses.py` and `scripts/traffic_houses.py` do not create spans. The traffic script only sends HTTP requests so the API has something to record.

## SDK pipeline

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

## Two tracers, one provider

Both tracers share the provider, so they share the resource and the exporter. They differ by instrumentation scope name, which shows up on the span as the instrumentation library:

| Tracer | Scope name | What it records |
| --- | --- | --- |
| `_http_tracer()` in `tracing.py` | `app4.http` | Incoming HTTP server spans |
| module-level `tracer` in `store.py` | `app4.house` | Internal spans around the JSON file |

The HTTP tracer is resolved inside the request, when the view runs. The house tracer is resolved when `store.py` is imported.

## One request

Flask runs the hooks in this order.

### 1. Attach incoming context

`attach_context_with_trace_header` is a `before_request` hook. It runs before the view.

`extract(request.headers)` reads W3C `traceparent` and `tracestate` from the incoming headers. `context.attach(...)` pushes that context onto the current thread's OpenTelemetry context stack and returns a token. The token is stored on the WSGI environ under `previous_ctx_token`, because `before_request` and `teardown_request` are separate functions and cannot share a local variable.

`server_span` does not take a parent span argument. `start_as_current_span()` parents the new span on whatever context is current. With a `traceparent`, the server span continues the caller's trace. With no `traceparent`, the extracted context is empty and the server span starts a new trace.

### 2. Open the server span

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

### 3. Open child spans

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

### 4. Record the HTTP status

After the view returns, `response_status_code()` reads the status from whatever Flask view shape came back:

- a response object, via `status_code`
- a tuple such as `(body, 404)` or `(body, 404, headers)`, via the integer piece, or a string like `"404 NOT FOUND"`

That number is written to `http.response.status_code`. Status 500 and above also calls `span.set_status(Status(StatusCode.ERROR))`.

A missing house returns `(jsonify({"error": "house not found"}), 404)` from `controller.py`. The server span records `http.response.status_code` = 404 and leaves the span status unset. Backends display an unset status as successful. A 404 is an answer the handler produced on purpose.

If the view raises, the wrapper sets `http.response.status_code` to 500 and re-raises. Leaving the `with` block still ends the span. `start_as_current_span` records the exception on the span and sets the span status to `ERROR` on the way out.

### 5. Detach the context

`restore_context_on_teardown` is a `teardown_request` hook. Flask runs it after the response and also when an exception escapes the view. `context.detach(token)` pops the stack back to the context that was current before `attach()`. The next request on this worker thread does not inherit this request's trace.

## What gets exported

A span is eligible for export when its `with` block ends. `BatchSpanProcessor` holds those spans and the `OTLPSpanExporter` POSTs them to the collector. With the default endpoint that is `http://localhost:4318/v1/traces`. Spans can show up in Grafana about a second after the request, because of the batch delay.

This process exports traces only. There is no meter provider, no log pipeline, and no outbound `inject()` call, because the house API does not make an outbound HTTP request of its own.
