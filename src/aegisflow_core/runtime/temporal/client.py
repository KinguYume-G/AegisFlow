"""Validated client boundary for starting and signalling durable workflows."""

from __future__ import annotations

from temporalio.client import Client, WorkflowHandle

from aegisflow_core.runtime.temporal.contracts import (
    DeliveryWorkflowInput,
    HumanSignal,
    WorkflowResult,
)
from aegisflow_core.runtime.temporal.workflow import DeliveryWorkflow


async def connect_temporal(address: str, namespace: str) -> Client:
    if not address or not namespace:
        raise ValueError("Temporal address and namespace are required")
    return await Client.connect(address, namespace=namespace)


async def start_delivery_workflow(
    client: Client,
    workflow_input: DeliveryWorkflowInput,
    *,
    task_queue: str,
) -> WorkflowHandle[DeliveryWorkflow, WorkflowResult]:
    if not task_queue:
        raise ValueError("Temporal task queue is required")
    return await client.start_workflow(
        DeliveryWorkflow.run,
        workflow_input,
        id=workflow_input.identity.temporal_workflow_id,
        task_queue=task_queue,
    )


async def signal_clarification(
    handle: WorkflowHandle[DeliveryWorkflow, WorkflowResult],
    signal: HumanSignal,
) -> None:
    if signal.kind != "clarification":
        raise ValueError("clarification endpoint requires a clarification signal")
    await handle.signal(DeliveryWorkflow.clarification, signal)


async def signal_approval(
    handle: WorkflowHandle[DeliveryWorkflow, WorkflowResult],
    signal: HumanSignal,
) -> None:
    if signal.kind != "approval":
        raise ValueError("approval endpoint requires an approval signal")
    await handle.signal(DeliveryWorkflow.approval, signal)
