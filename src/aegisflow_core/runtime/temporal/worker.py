"""Temporal worker bootstrap with explicit Activity dependency injection."""

from __future__ import annotations

import asyncio
import os
from temporalio.client import Client
from temporalio.worker import Worker

from aegisflow_core.runtime.checkpoint import PostgresCheckpointManager
from aegisflow_core.runtime.temporal.activities import (
    DeliveryActivities,
    DurableGraphPort,
)
from aegisflow_core.runtime.temporal.client import connect_temporal
from aegisflow_core.runtime.temporal.workflow import DeliveryWorkflow
from aegisflow_core.runtime.observability import configure_tracer
from aegisflow_core.control_plane.domain.session import (
    create_database_engine,
    create_session_factory,
)
from aegisflow_core.runtime.temporal.graph_adapter import (
    CHECKPOINT_ALLOWED_TYPES,
    PostgresDeliveryGraphAdapter,
)
from aegisflow_core.settings import get_settings


def build_worker(
    client: Client,
    graph: DurableGraphPort,
    *,
    task_queue: str,
) -> Worker:
    if not task_queue:
        raise ValueError("Temporal task queue is required")
    activities = DeliveryActivities(graph)
    return Worker(
        client,
        task_queue=task_queue,
        workflows=[DeliveryWorkflow],
        activities=[activities.advance_gate1b],
    )


async def run_worker(graph: DurableGraphPort | None = None) -> None:
    address = os.environ.get("TEMPORAL_ADDRESS") or "localhost:7233"
    namespace = os.environ.get("TEMPORAL_NAMESPACE") or "default"
    task_queue = os.environ.get("TEMPORAL_TASK_QUEUE") or "aegisflow-delivery"
    checkpoint_url = os.environ.get("LANGGRAPH_DATABASE_URL") or os.environ.get(
        "DATABASE_URL"
    )
    if not checkpoint_url:
        raise RuntimeError("LANGGRAPH_DATABASE_URL or DATABASE_URL is required")
    provider = configure_tracer(
        service_name="aegisflow-temporal-worker",
        endpoint=os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT") or None,
    )
    settings = None
    database_engine = None
    if graph is None:
        settings = get_settings()
        manager = PostgresCheckpointManager(
            checkpoint_url, allowed_types=CHECKPOINT_ALLOWED_TYPES
        )
        database_engine = create_database_engine(settings)
        graph = PostgresDeliveryGraphAdapter(
            settings=settings,
            session_factory=create_session_factory(database_engine),
            checkpoint_manager=manager,
        )
    else:
        manager = PostgresCheckpointManager(checkpoint_url)
    await manager.setup()
    client = await connect_temporal(address, namespace)
    worker = build_worker(
        client,
        graph,
        task_queue=task_queue,
    )
    try:
        await worker.run()
    finally:
        if database_engine is not None:
            await database_engine.dispose()
        provider.shutdown()


def main() -> None:
    asyncio.run(run_worker())


if __name__ == "__main__":
    main()
