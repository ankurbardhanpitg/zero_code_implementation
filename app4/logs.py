"""Manual logs pipeline for this process.

Nothing in Flask is auto-instrumented. A log record exists only where
application code calls the standard logging module. LoggingHandler turns
each of those records into an OpenTelemetry log and hands it to the
LoggerProvider, the same bridge used in logs_solution.

Startup wiring, called once from app.py next to init_tracing():

  Resource
      Same identity as traces (service.name = manual-python). Built by
      tracing.create_resource so both signals share one resource definition.
      tracing.py itself is not modified.
  LoggerProvider
      Owns that resource and the processor below it.
  OTLPLogExporter
      POST log records as OTLP/HTTP to the collector's /v1/logs endpoint.
      The collector already forwards that pipeline to Loki.
  BatchLogRecordProcessor
      Queues records and flushes them on a timer instead of exporting one
      record per logging call.
  LoggingHandler
      Attached to the root logger. A logging call made while a span is
      current copies that span's context, so Loki receives the trace id
      and span id.

logs_solution exports with ConsoleLogExporter. This process exports with
OTLP so the same records show up in Grafana.
"""

from __future__ import annotations

import logging
import os

from opentelemetry._logs import set_logger_provider
from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor

from tracing import SERVICE_NAME, SERVICE_VERSION, create_resource


def _logs_endpoint() -> str:
    """Resolve the OTLP/HTTP logs URL the exporter will POST to.

    OTEL_EXPORTER_OTLP_LOGS_ENDPOINT wins when it is set.
    Otherwise OTEL_EXPORTER_OTLP_ENDPOINT is used, defaulting to
    http://localhost:4318, and /v1/logs is appended when the base URL
    does not already end with that path.
    """

    explicit = os.environ.get("OTEL_EXPORTER_OTLP_LOGS_ENDPOINT")
    if explicit:
        return explicit.rstrip("/")
    base = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4318").rstrip("/")
    if base.endswith("/v1/logs"):
        return base
    for suffix in ("/v1/traces", "/v1/metrics"):
        if base.endswith(suffix):
            base = base[: -len(suffix)]
            break
    return base + "/v1/logs"


def init_logging(name: str = SERVICE_NAME, version: str = SERVICE_VERSION) -> None:
    """Install the LoggerProvider and bridge the root logger to it.

    Call once, after init_tracing() and before the first request.
    logging.basicConfig keeps a console handler, matching logs_solution.
    The OpenTelemetry handler is added beside it. Level INFO drops DEBUG
    records before they are exported.
    """

    provider = LoggerProvider(resource=create_resource(name, version))
    provider.add_log_record_processor(
        BatchLogRecordProcessor(OTLPLogExporter(endpoint=_logs_endpoint()))
    )
    set_logger_provider(provider)

    logging.basicConfig(level=logging.INFO)
    handler = LoggingHandler(level=logging.INFO, logger_provider=provider)
    logging.getLogger().addHandler(handler)
