"""Worker process intentionally terminated by the Gate 2 harness."""

from __future__ import annotations

import asyncio
import os

from temporalio.client import Client
from temporalio.worker import Worker

from aegisflow_core.runtime.fault_probe import FaultProbeWorkflow, gate2_fault_effect


async def run() -> None:
    address = os.environ.get("TEMPORAL_ADDRESS") or "localhost:7233"
    namespace = os.environ.get("TEMPORAL_NAMESPACE") or "default"
    task_queue = os.environ.get("AEGISFLOW_FAULT_TASK_QUEUE") or "aegisflow-gate2-fault"
    client = await Client.connect(address, namespace=namespace)
    worker = Worker(
        client,
        task_queue=task_queue,
        workflows=[FaultProbeWorkflow],
        activities=[gate2_fault_effect],
        # Disable sticky queues so an abrupt worker loss is immediately visible
        # to a replacement worker instead of waiting for the default 10s sticky timeout.
        max_cached_workflows=0,
    )
    await worker.run()


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
