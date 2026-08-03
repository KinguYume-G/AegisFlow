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
    UnconfiguredGraphPort,
)
from aegisflow_core.runtime.temporal.client import connect_temporal
from aegisflow_core.runtime.temporal.workflow import DeliveryWorkflow


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
    await PostgresCheckpointManager(checkpoint_url).setup()
    client = await connect_temporal(address, namespace)
    worker = build_worker(client, graph or UnconfiguredGraphPort(), task_queue=task_queue)
    await worker.run()


def main() -> None:
    asyncio.run(run_worker())


if __name__ == "__main__":
    main()
