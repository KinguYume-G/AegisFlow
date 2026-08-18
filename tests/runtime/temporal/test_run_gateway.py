"""Temporal Run gateway uses stable workflow IDs and typed Human Signals."""

from uuid import UUID

import pytest

from aegisflow_core.runtime.temporal.contracts import (
    DeliveryWorkflowInput,
    HumanSignal,
    RuntimeIdentity,
)
from aegisflow_core.runtime.temporal.run_gateway import TemporalRunGateway


IDENTITY = RuntimeIdentity(
    tenant_id="10000000-0000-0000-0000-000000000001",
    run_id="20000000-0000-0000-0000-000000000002",
    trace_id="30000000-0000-0000-0000-000000000003",
    workflow_version=1,
)


class Handle:
    def __init__(self) -> None:
        self.signals = []

    async def signal(self, method, value) -> None:
        self.signals.append((method, value))


class Client:
    def __init__(self) -> None:
        self.started = []
        self.handles: dict[str, Handle] = {}

    async def start_workflow(self, method, value, **kwargs):
        self.started.append((method, value, kwargs))
        return self.handles.setdefault(kwargs["id"], Handle())

    def get_workflow_handle(self, workflow_id: str):
        return self.handles.setdefault(workflow_id, Handle())


@pytest.mark.anyio
async def test_gateway_starts_and_signals_the_derived_workflow() -> None:
    client = Client()

    async def connect(address: str, namespace: str):
        assert address == "temporal:7233"
        assert namespace == "default"
        return client

    gateway = TemporalRunGateway(
        address="temporal:7233",
        namespace="default",
        task_queue="aegisflow-delivery",
        connector=connect,
    )
    workflow_input = DeliveryWorkflowInput(IDENTITY)
    clarification = HumanSignal(
        signal_id="clarification-signal-001",
        kind="clarification",
        tenant_id=IDENTITY.tenant_id,
        run_id=IDENTITY.run_id,
        target_reference=str(UUID("40000000-0000-0000-0000-000000000004")),
        value='{"answers":{"scope":"bounded"}}',
        actor_reference="urn:aegisflow:local-mvp|developer",
        received_at="2026-08-17T00:00:00+00:00",
    )
    approval = HumanSignal(
        signal_id="approval-signal-001",
        kind="approval",
        tenant_id=IDENTITY.tenant_id,
        run_id=IDENTITY.run_id,
        target_reference=str(UUID("50000000-0000-0000-0000-000000000005")),
        value='{"decision":"approved","reason":"verified"}',
        actor_reference="urn:aegisflow:local-mvp|reviewer",
        received_at="2026-08-17T00:01:00+00:00",
    )

    await gateway.start(workflow_input)
    await gateway.signal_clarification(IDENTITY, clarification)
    await gateway.signal_approval(IDENTITY, approval)

    assert client.started[0][2] == {
        "id": IDENTITY.temporal_workflow_id,
        "task_queue": "aegisflow-delivery",
    }
    handle = client.handles[IDENTITY.temporal_workflow_id]
    assert [item[1] for item in handle.signals] == [clarification, approval]
    assert gateway.client is client
