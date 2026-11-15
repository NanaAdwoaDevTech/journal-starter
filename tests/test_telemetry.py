"""Tests for the telemetry helpers: no network and no global OpenTelemetry state."""

from datetime import UTC, datetime

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import InMemoryMetricReader, Sum
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.trace import StatusCode

from api import telemetry
from api.main import app
from api.models.entry import Entry
from api.routers import journal_router
from api.routers.journal_router import get_entry_service


@pytest.fixture
def spans(monkeypatch):
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    monkeypatch.setattr(telemetry, "_tracer", provider.get_tracer("test"))
    return exporter


def test_setup_is_a_noop_without_configuration(monkeypatch):
    monkeypatch.delenv("OTEL_EXPORTER_OTLP_ENDPOINT", raising=False)
    monkeypatch.delenv("OTEL_CONSOLE_EXPORT", raising=False)
    assert telemetry.setup_telemetry(FastAPI()) is False


async def test_traced_records_a_span(spans):
    @telemetry.traced("demo.ok")
    async def work(x: int) -> int:
        return x * 2

    assert await work(2) == 4
    [span] = spans.get_finished_spans()
    assert span.name == "demo.ok"
    assert span.status.status_code == StatusCode.UNSET


async def test_traced_marks_errors_without_leaking_the_message(spans):
    @telemetry.traced("demo.fail")
    async def boom() -> None:
        raise ValueError("secret journal text")

    with pytest.raises(ValueError, match="secret journal text"):
        await boom()

    [span] = spans.get_finished_spans()
    assert span.status.status_code == StatusCode.ERROR
    assert span.attributes is not None
    assert span.attributes["error.type"] == "ValueError"
    assert span.events == ()
    assert "secret" not in str(span.status.description)


async def test_creating_an_entry_increments_the_counter(monkeypatch):
    reader = InMemoryMetricReader()
    counter = (
        MeterProvider(metric_readers=[reader])
        .get_meter("test")
        .create_counter("journal.entries.created")
    )
    monkeypatch.setattr(journal_router, "ENTRIES_CREATED", counter)

    class FakeService:
        async def create_entry(self, data):
            now = datetime.now(UTC)
            return Entry(
                id="entry-1",
                work=data.work,
                struggle=data.struggle,
                intention=data.intention,
                created_at=now,
                updated_at=now,
            )

    app.dependency_overrides[get_entry_service] = lambda: FakeService()
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/entries",
                json={"work": "a", "struggle": "b", "intention": "c"},
            )
    finally:
        app.dependency_overrides.pop(get_entry_service, None)

    assert response.status_code == 201
    data = reader.get_metrics_data()
    assert data is not None
    metric = data.resource_metrics[0].scope_metrics[0].metrics[0]
    assert metric.name == "journal.entries.created"
    assert isinstance(metric.data, Sum)
    assert metric.data.data_points[0].value == 1
