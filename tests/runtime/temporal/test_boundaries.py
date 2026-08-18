from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from temporalio.exceptions import ApplicationError

from aegisflow_core.runtime.temporal import client as client_module
from aegisflow_core.runtime.temporal import worker as worker_module
from aegisflow_core.runtime.temporal.activities import (
    DeliveryActivities,
    UnconfiguredGraphPort,
)
from aegisflow_core.runtime.temporal.contracts import (
    AdvanceRequest,
    AdvanceResult,
    DeliveryWorkflowInput,
    HumanSignal,
)
from aegisflow_core.runtime.temporal.policies import safe_failure_reference
from tests.runtime.temporal.test_contracts import identity


class StubGraph:
    def __init__(self, result: AdvanceResult | Exception) -> None:
        self.result = result
        self.failures = []

    async def advance(self, request: AdvanceRequest) -> AdvanceResult:
        if isinstance(self.result, Exception):
            raise self.result
        return self.result

    async def fail(self, identity, failure_reference: str) -> str:
        self.failures.append((identity, failure_reference))
        return f"run:{identity.run_id}:failed"


@pytest.mark.asyncio
async def test_activity_boundary_returns_result_and_classifies_failure() -> None:
    request = AdvanceRequest(identity())
    expected = AdvanceResult("completed", "result:1")
    assert await DeliveryActivities(StubGraph(expected)).advance_gate1b(request) == expected
    failed_graph = StubGraph(ValueError("sensitive input must not escape"))
    failed = await DeliveryActivities(failed_graph).advance_gate1b(request)
    assert failed == AdvanceResult("failed", f"run:{request.identity.run_id}:failed")
    assert failed_graph.failures == [
        (request.identity, "invalid_input:ValueError")
    ]
    with pytest.raises(ApplicationError) as captured:
        await DeliveryActivities(StubGraph(ConnectionError("temporary"))).advance_gate1b(
            request
        )
    assert captured.value.type == "transient"
    with pytest.raises(RuntimeError, match="not configured"):
        await UnconfiguredGraphPort().advance(request)


def test_failure_reference_uses_only_stable_error_types() -> None:
    error = type(
        "NodeFailure",
        (RuntimeError,),
        {"node": "clarifier", "cause_type": "StructuredReasoningError"},
    )("must never be persisted")

    assert safe_failure_reference(error) == (
        "irreversible:clarifier:StructuredReasoningError"
    )
    assert "persisted" not in safe_failure_reference(error)


@pytest.mark.asyncio
async def test_client_validates_start_and_typed_signals(monkeypatch) -> None:
    with pytest.raises(ValueError):
        await client_module.connect_temporal("", "default")
    connected = object()
    connect = AsyncMock(return_value=connected)
    monkeypatch.setattr(client_module.Client, "connect", connect)
    assert await client_module.connect_temporal("temporal:7233", "default") is connected

    temporal_client = AsyncMock()
    temporal_client.start_workflow.return_value = object()
    workflow_input = DeliveryWorkflowInput(identity())
    with pytest.raises(ValueError):
        await client_module.start_delivery_workflow(
            temporal_client, workflow_input, task_queue=""
        )
    await client_module.start_delivery_workflow(
        temporal_client, workflow_input, task_queue="delivery"
    )
    temporal_client.start_workflow.assert_awaited_once()

    handle = AsyncMock()
    clarification = HumanSignal(
        "s1", "clarification", workflow_input.identity.tenant_id,
        workflow_input.identity.run_id, "question:1", "answer", "human", "now",
    )
    approval = HumanSignal(
        "s2", "approval", workflow_input.identity.tenant_id,
        workflow_input.identity.run_id, "approval:1", "approved", "human", "now",
    )
    await client_module.signal_clarification(handle, clarification)
    await client_module.signal_approval(handle, approval)
    with pytest.raises(ValueError):
        await client_module.signal_clarification(handle, approval)
    with pytest.raises(ValueError):
        await client_module.signal_approval(handle, clarification)
    assert handle.signal.await_count == 2


@pytest.mark.asyncio
async def test_worker_bootstrap_initializes_checkpoints_and_runs(monkeypatch) -> None:
    with pytest.raises(ValueError):
        worker_module.build_worker(object(), StubGraph(AdvanceResult("completed")), task_queue="")
    constructed = object()
    monkeypatch.setattr(worker_module, "Worker", lambda *args, **kwargs: constructed)
    assert worker_module.build_worker(
        object(), StubGraph(AdvanceResult("completed")), task_queue="delivery"
    ) is constructed

    setup = AsyncMock()
    manager = AsyncMock()
    manager.setup = setup
    monkeypatch.setattr(worker_module, "PostgresCheckpointManager", lambda _: manager)
    temporal_client = object()
    monkeypatch.setattr(
        worker_module, "connect_temporal", AsyncMock(return_value=temporal_client)
    )
    run = AsyncMock()
    monkeypatch.setattr(worker_module, "build_worker", lambda *args, **kwargs: type(
        "WorkerStub", (), {"run": run}
    )())
    monkeypatch.setenv("DATABASE_URL", "postgresql://db")
    await worker_module.run_worker(StubGraph(AdvanceResult("completed")))
    setup.assert_awaited_once()
    run.assert_awaited_once()

    captured_graphs = []
    monkeypatch.setattr(
        worker_module,
        "get_settings",
        lambda: SimpleNamespace(local_mvp_profile_enabled=False),
    )
    monkeypatch.setattr(
        worker_module,
        "create_database_engine",
        lambda _: pytest.fail("non-local worker must not construct local MVP storage"),
    )
    monkeypatch.setattr(
        worker_module,
        "build_worker",
        lambda _client, graph, **_kwargs: (
            captured_graphs.append(graph)
            or type("WorkerStub", (), {"run": AsyncMock()})()
        ),
    )
    await worker_module.run_worker()
    assert isinstance(captured_graphs[-1], UnconfiguredGraphPort)

    monkeypatch.delenv("DATABASE_URL")
    monkeypatch.delenv("LANGGRAPH_DATABASE_URL", raising=False)
    with pytest.raises(RuntimeError, match="DATABASE_URL"):
        await worker_module.run_worker()


@pytest.mark.asyncio
async def test_worker_builds_delivery_adapter_only_for_explicit_local_profile(
    monkeypatch,
) -> None:
    manager = SimpleNamespace(setup=AsyncMock())
    manager_calls = []

    def manager_factory(url, **kwargs):
        manager_calls.append((url, kwargs))
        return manager

    settings = SimpleNamespace(local_mvp_profile_enabled=True)
    engine = SimpleNamespace(dispose=AsyncMock())
    sessions = object()
    adapter = StubGraph(AdvanceResult("completed"))
    adapter_calls = []

    def adapter_factory(**kwargs):
        adapter_calls.append(kwargs)
        return adapter

    captured_graphs = []
    worker = SimpleNamespace(run=AsyncMock())
    monkeypatch.delenv("LANGGRAPH_DATABASE_URL", raising=False)
    monkeypatch.setenv("DATABASE_URL", "postgresql://db")
    monkeypatch.setattr(worker_module, "PostgresCheckpointManager", manager_factory)
    monkeypatch.setattr(worker_module, "get_settings", lambda: settings)
    monkeypatch.setattr(worker_module, "create_database_engine", lambda _: engine)
    monkeypatch.setattr(
        worker_module, "create_session_factory", lambda _: sessions
    )
    monkeypatch.setattr(
        worker_module, "PostgresDeliveryGraphAdapter", adapter_factory
    )
    monkeypatch.setattr(
        worker_module, "connect_temporal", AsyncMock(return_value=object())
    )
    monkeypatch.setattr(
        worker_module,
        "build_worker",
        lambda _client, graph, **_kwargs: (
            captured_graphs.append(graph) or worker
        ),
    )
    monkeypatch.setattr(
        worker_module,
        "configure_tracer",
        lambda **_kwargs: SimpleNamespace(shutdown=lambda: None),
    )

    await worker_module.run_worker()

    assert captured_graphs == [adapter]
    assert manager_calls == [
        (
            "postgresql://db",
            {"allowed_types": worker_module.CHECKPOINT_ALLOWED_TYPES},
        )
    ]
    assert adapter_calls == [
        {
            "settings": settings,
            "session_factory": sessions,
            "checkpoint_manager": manager,
        }
    ]
    manager.setup.assert_awaited_once()
    worker.run.assert_awaited_once()
    engine.dispose.assert_awaited_once()
