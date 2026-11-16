"""OpenTelemetry setup: traces, metrics and logs.

Telemetry is off by default, so tests and local runs never try to reach a collector.
  * OTEL_EXPORTER_OTLP_ENDPOINT=<collector url> exports over OTLP/HTTP
  * OTEL_CONSOLE_EXPORT=1 prints spans and metrics locally (no collector needed)

Never put journal text, settings, or credentials in span attributes or metrics.
"""

import functools
import logging
import os
from collections.abc import Awaitable, Callable, Coroutine
from typing import Any

from fastapi import FastAPI
from opentelemetry import metrics, trace
from opentelemetry._logs import set_logger_provider
from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import (
    ConsoleMetricExporter,
    PeriodicExportingMetricReader,
)
from opentelemetry.sdk.resources import SERVICE_NAME, SERVICE_VERSION, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.trace import Status, StatusCode

from api.logging_config import configure_logging

_NAME = "journal-api"
_tracer = trace.get_tracer(_NAME)
_meter = metrics.get_meter(_NAME)

# Custom metric: how many journal entries have been created
ENTRIES_CREATED = _meter.create_counter(
    "journal.entries.created",
    unit="{entry}",
    description="Journal entries created through the API",
)


def setup_telemetry(app: FastAPI) -> bool:
    """Configure exporters and instrument FastAPI. Returns False when telemetry is off."""
    console = os.environ.get("OTEL_CONSOLE_EXPORT") == "1"
    if not console and not os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT"):
        return False

    # Install the normal log handler first, so adding the OTel handler keeps stdout logs
    configure_logging()

    resource = Resource.create(
        {SERVICE_NAME: _NAME, SERVICE_VERSION: os.environ.get("GIT_SHA", "unknown")}
    )

    tracer_provider = TracerProvider(resource=resource)
    tracer_provider.add_span_processor(
        BatchSpanProcessor(ConsoleSpanExporter() if console else OTLPSpanExporter())
    )
    trace.set_tracer_provider(tracer_provider)

    reader = PeriodicExportingMetricReader(
        ConsoleMetricExporter() if console else OTLPMetricExporter(),
        export_interval_millis=15_000,
    )
    metrics.set_meter_provider(MeterProvider(resource=resource, metric_readers=[reader]))

    if not console:
        logger_provider = LoggerProvider(resource=resource)
        logger_provider.add_log_record_processor(BatchLogRecordProcessor(OTLPLogExporter()))
        set_logger_provider(logger_provider)
        logging.getLogger().addHandler(
            LoggingHandler(level=logging.INFO, logger_provider=logger_provider)
        )

    # Probe traffic would drown real requests in the request-count and latency charts
    FastAPIInstrumentor.instrument_app(app, excluded_urls="version")
    return True


def traced[**P, R](
    name: str,
) -> Callable[[Callable[P, Awaitable[R]]], Callable[P, Coroutine[Any, Any, R]]]:
    """Wrap an async function in a span.

    Only the error type is recorded, never the message or arguments, because
    exception messages can echo journal text.
    """

    def decorator(func: Callable[P, Awaitable[R]]) -> Callable[P, Coroutine[Any, Any, R]]:
        @functools.wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            with _tracer.start_as_current_span(
                name, record_exception=False, set_status_on_exception=False
            ) as span:
                try:
                    return await func(*args, **kwargs)
                except Exception as exc:
                    span.set_attribute("error.type", type(exc).__name__)
                    span.set_status(Status(StatusCode.ERROR))
                    raise

        return wrapper

    return decorator
