import os
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from aegisflow_core.control_plane.domain import AuditEvent, Run, Step, Tenant, Workflow
from aegisflow_core.control_plane.runtime_uow import PostgresRuntimeUnitOfWork


@pytest.mark.database
@pytest.mark.asyncio
async def test_runtime_uow_records_steps_audit_and_run_status() -> None:
    url = os.environ.get("DATABASE_URL")
    if not url:
        pytest.skip("DATABASE_URL is required")
    engine = create_async_engine(url)
    connection = await engine.connect()
    transaction = await connection.begin()
    sessions = async_sessionmaker(
        connection, expire_on_commit=False, join_transaction_mode="create_savepoint"
    )
    tenant_id, workflow_id, run_id, step_id = uuid4(), uuid4(), uuid4(), uuid4()
    async with sessions.begin() as session:
        session.add(Tenant(id=tenant_id, slug=f"uow-{tenant_id.hex}", name="UOW"))
        await session.flush()
        session.add(Workflow(
            id=workflow_id, tenant_id=tenant_id, name="gate1b", version=1,
            definition_hash="hash", status="active",
        ))
        await session.flush()
        session.add(Run(
            id=run_id, tenant_id=tenant_id, workflow_id=workflow_id,
            workflow_version=1, status="running",
        ))
    try:
        async with PostgresRuntimeUnitOfWork(sessions()) as uow:
            returned = await uow.record_step(
                tenant_id=tenant_id, run_id=run_id, step_id=step_id,
                name="policy_gate", sequence=5, status="completed",
            )
            await uow.record_audit(
                tenant_id=tenant_id, actor="policy_gate", action="evaluate",
                resource_type="run", resource_id=str(run_id), decision="allow",
                reason=None, trace_id=uuid4(),
            )
            await uow.set_run_status(tenant_id=tenant_id, run_id=run_id, status="waiting_approval")
        assert returned == step_id
        async with sessions() as session:
            run = await session.get(Run, run_id)
            step = await session.get(Step, step_id)
            audit = await session.scalar(select(AuditEvent).where(AuditEvent.tenant_id == tenant_id))
            assert run is not None and run.status == "waiting_approval"
            assert step is not None and step.status == "completed"
            assert audit is not None and audit.decision == "allow"

        replacement_id = uuid4()
        async with PostgresRuntimeUnitOfWork(sessions()) as uow:
            assert await uow.record_step(
                tenant_id=tenant_id, run_id=run_id, step_id=replacement_id,
                name="policy_gate", sequence=5, status="failed",
            ) == step_id
        async with PostgresRuntimeUnitOfWork(sessions()) as uow:
            with pytest.raises(KeyError):
                await uow.set_run_status(tenant_id=tenant_id, run_id=uuid4(), status="failed")
    finally:
        await transaction.rollback()
        await connection.close()
        await engine.dispose()
