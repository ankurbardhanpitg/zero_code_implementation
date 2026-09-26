"""Manual tracing pipeline.

Same shape as trace_solution (resource, TracerProvider, BatchSpanProcessor,
global tracer), with an OTLP HTTP exporter instead of the console exporter
so spans reach the local collector.
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
    traces = os.environ.get("OTEL_EXPORTER_OTLP_TRACES_ENDPOINT")
    if traces:
        return traces.rstrip("/")
    base = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4318").rstrip("/")
    if base.endswith("/v1/traces"):
        return base
    return base + "/v1/traces"


def create_resource(name: str, version: str) -> Resource:
    return Resource.create(
        {
            "service.name": name,
            "service.version": version,
            "host.name": socket.gethostname(),
            "deployment.environment": os.environ.get("DEPLOYMENT_ENVIRONMENT", "local"),
        }
    )


def init_tracing(name: str = SERVICE_NAME, version: str = SERVICE_VERSION) -> None:
    provider = TracerProvider(resource=create_resource(name, version))
    exporter = OTLPSpanExporter(endpoint=_traces_endpoint())
    provider.add_span_processor(
        BatchSpanProcessor(exporter, schedule_delay_millis=1000)
    )
    trace.set_tracer_provider(provider)


def _http_tracer() -> trace.Tracer:
    return trace.get_tracer("app4.http", SERVICE_VERSION)


def response_status_code(response) -> int:
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
    """Open a SERVER span for one Flask view. route is the http.route template."""

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
