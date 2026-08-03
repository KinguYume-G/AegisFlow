"""OpenTelemetry composition and bounded correlation attributes."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from time import perf_counter
from typing import Iterator

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

_active_provider: TracerProvider | None = None


@dataclass(frozen=True, slots=True)
class Correlation:
    tenant_id: str | None = None
    run_id: str | None = None
    trace_id: str | None = None
    workflow_version: int | None = None
    step_id: str | None = None

    def attributes(self) -> dict[str, str | int]:
        values: dict[str, str | int | None] = {
            "aegisflow.tenant.id": self.tenant_id,
            "aegisflow.run.id": self.run_id,
            "aegisflow.trace.id": self.trace_id,
            "aegisflow.workflow.version": self.workflow_version,
            "aegisflow.step.id": self.step_id,
        }
        return {key: value for key, value in values.items() if value is not None}


@contextmanager
def operation_span(name: str, correlation: Correlation) -> Iterator[None]:
    """Create a span without recording inputs, credentials, or exception text."""
    tracer = (
        _active_provider.get_tracer("aegisflow.system")
        if _active_provider is not None
        else trace.get_tracer("aegisflow.system")
    )
    started = perf_counter()
    outcome = "success"
    with tracer.start_as_current_span(name, attributes=correlation.attributes()) as span:
        try:
            yield
        except Exception as exc:
            outcome = (
                "denied"
                if isinstance(exc, PermissionError)
                else "timeout"
                if isinstance(exc, TimeoutError)
                else "failure"
            )
            span.set_attribute("error.type", type(exc).__name__)
            span.set_status(trace.Status(trace.StatusCode.ERROR))
            raise
        finally:
            from aegisflow_core.runtime.metrics import observe_active_operation

            observe_active_operation(name.split(".", 1)[0], name, outcome, perf_counter() - started)


def configure_tracer(*, service_name: str, endpoint: str | None) -> TracerProvider:
    global _active_provider
    provider = TracerProvider(resource=Resource.create({"service.name": service_name}))
    if endpoint is not None:
        provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint)))
    _active_provider = provider
    return provider
