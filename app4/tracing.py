"""Manual trace pipeline for this process.

Nothing in Flask is auto-instrumented. Spans exist only where application
code opens them: server_span() for the incoming HTTP span, and store.py for
the child spans under it.

Startup wiring, called once from app.py:

  Resource
      Identity copied onto every span (service.name = manual-python).
  TracerProvider
      Owns that resource and the processors below it.
  OTLPSpanExporter
      POST finished spans as OTLP/HTTP to the collector's /v1/traces endpoint.
  BatchSpanProcessor
      Queues ended spans and flushes them on a timer (here, every 1000 ms)
      instead of exporting one span per request.
  trace.set_tracer_provider
      Publishes the provider globally. Later trace.get_tracer(...) calls in
      this process return tracers bound to it.

Two tracers share that provider, so they share the resource and the exporter.
They differ only by instrumentation scope name:

  app4.http    SERVER spans opened by server_span()
  app4.house   INTERNAL spans opened by store.py

Parenting is implicit. start_as_current_span() parents the new span on the
current OTel context and then makes the new span current for the duration of
the with-block. app.py attaches any incoming traceparent before the view runs,
so a SERVER span nests under that caller when the header is present. store.py
runs inside the SERVER span's with-block, so its spans nest under the SERVER span.
"""

from __future__ import annotations

import os
import socket
from functools import wraps

from flask import request
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.trace import SpanKind, Status, StatusCode

SERVICE_NAME = "manual-python"
SERVICE_VERSION = "1.0.0"


def _traces_endpoint() -> str:
    """Resolve the OTLP/HTTP traces URL the exporter will POST to.

    OTEL_EXPORTER_OTLP_TRACES_ENDPOINT wins when it is set.
    Otherwise OTEL_EXPORTER_OTLP_ENDPOINT is used, defaulting to
    http://localhost:4318, and /v1/traces is appended when the base URL
    does not already end with that path.
    """

    traces = os.environ.get("OTEL_EXPORTER_OTLP_TRACES_ENDPOINT")
    if traces:
        return traces.rstrip("/")
    base = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4318").rstrip("/")
    if base.endswith("/v1/traces"):
        return base
    return base + "/v1/traces"


def create_resource(name: str, version: str) -> Resource:
    """Resource attributes attached to every span from this process.

    service.name is what the manual-python dashboard filters on.
    """

    return Resource.create(
        {
            "service.name": name,
            "service.version": version,
            "host.name": socket.gethostname(),
            "deployment.environment": os.environ.get("DEPLOYMENT_ENVIRONMENT", "local"),
        }
    )


def init_tracing(name: str = SERVICE_NAME, version: str = SERVICE_VERSION) -> None:
    """Install the global TracerProvider. Call once, before get_tracer()."""

    provider = TracerProvider(resource=create_resource(name, version))
    exporter = OTLPSpanExporter(endpoint=_traces_endpoint())
    provider.add_span_processor(
        BatchSpanProcessor(exporter, schedule_delay_millis=1000)
    )
    trace.set_tracer_provider(provider)


def _http_tracer() -> trace.Tracer:
    """Tracer for incoming HTTP spans. Resolved per request, after init_tracing()."""

    return trace.get_tracer("app4.http", SERVICE_VERSION)


def response_status_code(response) -> int:
    """Pull the HTTP status out of a Flask view return value.

    A view may return a Response, or a tuple such as (body, 404) or
    (body, 404, headers). The integer (or a status string like "404 NOT FOUND")
    is what gets written to http.response.status_code on the SERVER span.
    When no status is present, Flask would send 200, and so does this helper.
    """

    if isinstance(response, tuple):
        for part in response:
            if isinstance(part, int):
                return part
            if isinstance(part, str) and part[:3].isdigit():
                return int(part[:3])
        body = response[0]
        return int(getattr(body, "status_code", 200))
    return int(getattr(response, "status_code", 200))


def server_span(route: str):
    """Decorator that opens one SERVER span around a Flask view.

    route is the path template recorded as http.route, for example
    "/houses/<int:house_id>". The span name is "{method} {route}".
    url.path is the concrete request path, so /houses/3 and /houses/999
    share a route and differ by path.

    Applied two ways, with the same result:

        @server_span("/")                         # health(), in app.py
        def health(): ...

        server_span("/houses")(fetch_houses)      # at blueprint registration

    On entry the span is started as the current span, kind SERVER, with
    http.request.method, http.route, and url.path. The view then runs inside
    that context, which is what makes store.py spans children of this one.

    After a normal return, http.response.status_code is set from the view's
    return value. Status 500 and above also marks the span status ERROR.
    A 404 only sets the attribute; the span status stays unset, which
    backends display as successful.

    If the view raises, the attribute is set to 500 and the exception is
    re-raised. Exiting the with-block still ends the span; the SDK also
    records the exception and sets span status ERROR because
    start_as_current_span does that on the way out.
    """

    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            with _http_tracer().start_as_current_span(
                f"{request.method} {route}",
                kind=SpanKind.SERVER,
                attributes={
                    "http.request.method": request.method,
                    "http.route": route,
                    "url.path": request.path,
                },
            ) as span:
                try:
                    response = view(*args, **kwargs)
                except Exception:
                    span.set_attribute("http.response.status_code", 500)
                    raise

                status = response_status_code(response)
                span.set_attribute("http.response.status_code", status)
                if status >= 500:
                    span.set_status(Status(StatusCode.ERROR))
                return response

        return wrapped

    return decorator
