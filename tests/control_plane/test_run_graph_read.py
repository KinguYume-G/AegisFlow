from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest

from aegisflow_core.control_plane.run_graph import load_run_graph


class FakeSession:
    def __init__(self, run: object | None, steps: tuple[object, ...], audits: tuple[object, ...]):
        self.run = run
        self.results = iter((steps, audits))

    async def scalar(self, _statement):  # type: ignore[no-untyped-def]
        return self.run

    async def scalars(self, _statement):  # type: ignore[no-untyped-def]
        return next(self.results)


@pytest.mark.anyio
async def test_run_graph_orders_nodes_and_exposes_failure_evidence() -> None:
    tenant_id, run_id, workflow_id, step_id = uuid4(), uuid4(), uuid4(), uuid4()
    started = datetime.now(timezone.utc)
    run = SimpleNamespace(
        id=run_id, workflow_id=workflow_id, workflow_version=3, status="failed"
    )
    step = SimpleNamespace(
        id=step_id,
        name="executor",
        sequence=2,
        status="failed",
        created_at=started,
        completed_at=started + timedelta(milliseconds=125),
    )
    audit = SimpleNamespace(
        resource_id=str(step_id), trace_id="trace-safe", reason="sandbox_timeout"
    )
    graph = await load_run_graph(
        FakeSession(run, (step,), (audit,)),  # type: ignore[arg-type]
        tenant_id=tenant_id,
        run_id=run_id,
    )
    assert graph is not None
    assert graph.nodes[0].duration_ms == 125
    assert graph.nodes[0].trace_id == "trace-safe"
    assert graph.nodes[0].failure_reason == "sandbox_timeout"


@pytest.mark.anyio
async def test_run_graph_returns_none_without_tenant_scoped_run() -> None:
    assert await load_run_graph(
        FakeSession(None, (), ()),  # type: ignore[arg-type]
        tenant_id=uuid4(),
        run_id=uuid4(),
    ) is None
