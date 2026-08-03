"""Application-layer OpenTelemetry composition."""

from fastapi import FastAPI
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.sdk.trace import TracerProvider
from sqlalchemy.ext.asyncio import AsyncEngine

from aegisflow_core.runtime.observability import configure_tracer


def configure_telemetry(
    app: FastAPI,
    engine: AsyncEngine,
    *,
    service_name: str,
    endpoint: str | None,
) -> TracerProvider:
    provider = configure_tracer(service_name=service_name, endpoint=endpoint)
    FastAPIInstrumentor.instrument_app(
        app,
        tracer_provider=provider,
        excluded_urls="health,metrics",
    )
    sqlalchemy = SQLAlchemyInstrumentor()
    if not sqlalchemy.is_instrumented_by_opentelemetry:
        sqlalchemy.instrument(
            engine=engine.sync_engine,
            tracer_provider=provider,
            enable_commenter=False,
        )
    return provider
