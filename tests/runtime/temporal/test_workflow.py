from __future__ import annotations

from collections import deque
import asyncio
import os
from uuid import uuid4

import pytest
from temporalio import activity
from temporalio.client import Client, WorkflowFailureError
from temporalio.worker import Replayer, Worker

from aegisflow_core.runtime.temporal.contracts import (
    AdvanceRequest,
    AdvanceResult,
    DeliveryWorkflowInput,
    HumanSignal,
    RuntimeIdentity,
    WorkflowResult,
)
from aegisflow_core.runtime.temporal.workflow import DeliveryWorkflow


pytestmark = pytest.mark.temporal


def runtime_input(*, approval_timeout_seconds: int = 60) -> DeliveryWorkflowInput:
    return DeliveryWorkflowInput(
        RuntimeIdentity(str(uuid4()), str(uuid4()), str(uuid4()), 1),
        approval_timeout_seconds=approval_timeout_seconds,
    )


async def temporal_client() -> Client:
    return await Client.connect(os.environ.get("TEMPORAL_ADDRESS") or "localhost:7233")


class ScriptedAdvance:
    def __init__(self, *results: AdvanceResult) -> None:
        self.results = deque(results)
        self.requests: list[AdvanceRequest] = []

    @activity.defn(name="advance_gate1b")
    async def advance(self, request: AdvanceRequest) -> AdvanceResult:
        self.requests.append(request)
        return self.results.popleft()


@pytest.mark.asyncio
async def test_workflow_starts_worker_completes_and_replays() -> None:
    scripted = ScriptedAdvance(AdvanceResult("completed", "draft-pr:1"))
    value = runtime_input()
    client = await temporal_client()
    async with Worker(
            client,
            task_queue="durable-test",
            workflows=[DeliveryWorkflow],
            activities=[scripted.advance],
        ):
            result = await client.execute_workflow(
                DeliveryWorkflow.run,
                value,
                id=value.identity.temporal_workflow_id,
                task_queue="durable-test",
            )
            handle = client.get_workflow_handle(value.identity.temporal_workflow_id)
            history = await handle.fetch_history()
    assert result == WorkflowResult("completed", "draft-pr:1")
    assert scripted.requests == [AdvanceRequest(value.identity)]
    await Replayer(workflows=[DeliveryWorkflow]).replay_workflow(history)


@pytest.mark.asyncio
async def test_clarification_signal_survives_duplicate_delivery() -> None:
    scripted = ScriptedAdvance(
        AdvanceResult("waiting_clarification", wait_reference="question:1"),
        AdvanceResult("completed", "plan:1"),
    )
    value = runtime_input()
    signal = HumanSignal(
        "signal-1", "clarification", value.identity.tenant_id,
        value.identity.run_id, "question:1", "answer", "human:1", "2026-01-01T00:00:00Z",
    )
    client = await temporal_client()
    async with Worker(
            client, task_queue="clarification-test",
            workflows=[DeliveryWorkflow], activities=[scripted.advance],
        ):
            handle = await client.start_workflow(
                DeliveryWorkflow.run, value, id=value.identity.temporal_workflow_id,
                task_queue="clarification-test",
            )
            await handle.signal(DeliveryWorkflow.clarification, signal)
            await handle.signal(DeliveryWorkflow.clarification, signal)
            assert await handle.result() == WorkflowResult("completed", "plan:1")
    assert scripted.requests[-1].signal == signal


@pytest.mark.asyncio
async def test_conflicting_duplicate_signal_fails_closed() -> None:
    scripted = ScriptedAdvance(
        AdvanceResult("waiting_approval", wait_reference="approval:1")
    )
    value = runtime_input()
    first = HumanSignal(
        "decision-1", "approval", value.identity.tenant_id, value.identity.run_id,
        "approval:1", "approved", "human:1", "2026-01-01T00:00:00Z",
    )
    second = HumanSignal(
        "decision-1", "approval", value.identity.tenant_id, value.identity.run_id,
        "approval:1", "rejected", "human:1", "2026-01-01T00:00:00Z",
    )
    client = await temporal_client()
    async with Worker(
            client, task_queue="conflict-test",
            workflows=[DeliveryWorkflow], activities=[scripted.advance],
        ):
            handle = await client.start_workflow(
                DeliveryWorkflow.run, value, id=value.identity.temporal_workflow_id,
                task_queue="conflict-test",
            )
            await handle.signal(DeliveryWorkflow.approval, first)
            await handle.signal(DeliveryWorkflow.approval, second)
            with pytest.raises(WorkflowFailureError):
                await handle.result()


@pytest.mark.asyncio
async def test_approval_expiry_is_a_durable_resume_input() -> None:
    scripted = ScriptedAdvance(
        AdvanceResult("waiting_approval", wait_reference="approval:expiry"),
        AdvanceResult("failed", "approval_expired"),
    )
    value = runtime_input(approval_timeout_seconds=1)
    client = await temporal_client()
    async with Worker(
            client, task_queue="expiry-test",
            workflows=[DeliveryWorkflow], activities=[scripted.advance],
        ):
            result = await client.execute_workflow(
                DeliveryWorkflow.run, value, id=value.identity.temporal_workflow_id,
                task_queue="expiry-test",
            )
    assert result == WorkflowResult("failed", "approval_expired")
    assert scripted.requests[-1].signal is not None
    assert scripted.requests[-1].signal.value == "expired"


@pytest.mark.asyncio
async def test_waiting_workflow_resumes_after_worker_reconstruction() -> None:
    first_worker_activities = ScriptedAdvance(
        AdvanceResult("waiting_approval", wait_reference="approval:restart")
    )
    value = runtime_input()
    client = await temporal_client()
    handle = None
    async with Worker(
        client,
        task_queue="worker-reconstruction-test",
        workflows=[DeliveryWorkflow],
        activities=[first_worker_activities.advance],
    ):
        handle = await client.start_workflow(
            DeliveryWorkflow.run,
            value,
            id=value.identity.temporal_workflow_id,
            task_queue="worker-reconstruction-test",
        )
        for _ in range(100):
            if first_worker_activities.requests:
                break
            await asyncio.sleep(0.02)
        assert first_worker_activities.requests

    reconstructed_activities = ScriptedAdvance(AdvanceResult("completed", "pr:42"))
    signal = HumanSignal(
        "decision-restart",
        "approval",
        value.identity.tenant_id,
        value.identity.run_id,
        "approval:restart",
        "approved",
        "human:1",
        "2026-01-01T00:00:00Z",
    )
    async with Worker(
        client,
        task_queue="worker-reconstruction-test",
        workflows=[DeliveryWorkflow],
        activities=[reconstructed_activities.advance],
    ):
        await handle.signal(DeliveryWorkflow.approval, signal)
        assert await handle.result() == WorkflowResult("completed", "pr:42")
    assert reconstructed_activities.requests == [AdvanceRequest(value.identity, signal)]
