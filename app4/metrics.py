"""Manual metrics pipeline for this process.

Nothing in Flask is auto-instrumented. Values exist only where application
code records them: app.py for the HTTP counter and histogram, and the
callbacks in this module for process gauges.

Startup wiring, called once from app.py next to init_tracing():

  Resource
      Same identity as traces (service.name = manual-python). Built by
      tracing.create_resource so both signals share one resource definition.
      tracing.py itself is not modified.
  MeterProvider
      Owns that resource and the reader below it.
  OTLPMetricExporter
      POST metrics as OTLP/HTTP to the collector's /v1/metrics endpoint.
  PeriodicExportingMetricReader
      Collects and exports on a timer (here, every 5000 ms).
  metrics.set_meter_provider
      Publishes the provider globally. Later metrics.get_meter(...) calls
      in this process return meters bound to it.

The meter scope name is app4.metrics. It is independent of the app4.http
and app4.house tracers.
"""

from __future__ import annotations

import os
from typing import Any

import psutil
from opentelemetry import metrics
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader

from tracing import SERVICE_NAME, SERVICE_VERSION, create_resource


def _metrics_endpoint() -> str:
    """Resolve the OTLP/HTTP metrics URL the exporter will POST to.

    OTEL_EXPORTER_OTLP_METRICS_ENDPOINT wins when it is set.
    Otherwise OTEL_EXPORTER_OTLP_ENDPOINT is used, defaulting to
    http://localhost:4318, and /v1/metrics is appended when the base URL
    does not already end with that path.
    """

    explicit = os.environ.get("OTEL_EXPORTER_OTLP_METRICS_ENDPOINT")
    if explicit:
        return explicit.rstrip("/")
    base = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4318").rstrip("/")
    if base.endswith("/v1/metrics"):
        return base
    if base.endswith("/v1/traces"):
        base = base[: -len("/v1/traces")]
    return base + "/v1/metrics"


def _create_request_instruments(meter: metrics.Meter) -> dict[str, Any]:
    """Counters and histogram recorded by the Flask hooks in app.py.

    traffic_volume counts requests. error_rate counts responses whose
    status is 400 or higher. http.server.request.duration is the latency
    histogram, in seconds, following the HTTP semantic convention.
    """

    traffic_volume = meter.create_counter(
        name="traffic_volume",
        unit="request",
        description="total volume of requests to an endpoint",
    )
    error_rate = meter.create_counter(
        name="error_rate",
        unit="request",
        description="rate of failed requests",
    )
    request_latency = meter.create_histogram(
        name="http.server.request.duration",
        unit="s",
        description="latency for a request to be served",
    )
    return {
        "traffic_volume": traffic_volume,
        "error_rate": error_rate,
        "request_latency": request_latency,
    }


def _create_resource_instruments(meter: metrics.Meter) -> None:
    """Process gauges sampled by the reader when it exports.

    These are pull instruments. Nothing in the request path calls them.
    cpu_percent(interval=None) returns the utilization since the previous
    call and does not block the export thread.
    """

    meter.create_observable_gauge(
        name="process.cpu.utilization",
        callbacks=[
            lambda _options: [
                metrics.Observation(psutil.cpu_percent(interval=None) / 100)
            ]
        ],
        unit="1",
        description="CPU utilization",
    )
    meter.create_observable_up_down_counter(
        name="process.memory.usage",
        callbacks=[
            lambda _options: [metrics.Observation(psutil.virtual_memory().used)]
        ],
        unit="By",
        description="total amount of memory used",
    )


def init_metrics(
    name: str = SERVICE_NAME, version: str = SERVICE_VERSION
) -> dict[str, Any]:
    """Install the global MeterProvider and return the HTTP instruments.

    Call once, before the first request. The returned dict is what app.py
    records into. Process gauges are registered on the meter and are not
    part of the return value.
    """

    reader = PeriodicExportingMetricReader(
        exporter=OTLPMetricExporter(endpoint=_metrics_endpoint()),
        export_interval_millis=5000,
    )
    provider = MeterProvider(
        metric_readers=[reader],
        resource=create_resource(name, version),
    )
    metrics.set_meter_provider(provider)
    meter = metrics.get_meter("app4.metrics", version)
    _create_resource_instruments(meter)
    return _create_request_instruments(meter)
