"""AF-401 tenant-aware persistence boundary tests."""

import os
from uuid import uuid4

import pytest
from sqlalchemy import select, text, update
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from aegisflow_core.control_plane.domain import Tenant, Workflow
from aegisflow_core.control_plane.tenants import (
    TenantScope,
    TenantScopeRequired,
    TenantScopeViolation,
    TenantSession,
)


def test_tenant_scope_requires_identity_and_actor() -> None:
    with pytest.raises(TenantScopeRequired):
        TenantScope(None, "actor")  # type: ignore[arg-type]
    with pytest.raises(TenantScopeRequired):
        TenantScope(uuid4(), " ")


@pytest.mark.database
@pytest.mark.anyio
async def test_tenant_session_filters_reads_and_rejects_cross_tenant_writes() -> None:
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        pytest.skip("DATABASE_URL is required")
    engine = create_async_engine(database_url)
    async with engine.connect() as connection:
        transaction = await connection.begin()
        sessions = async_sessionmaker(
            connection, expire_on_commit=False, join_transaction_mode="create_savepoint"
        )
        try:
            async with sessions() as raw:
                tenant_a = Tenant(slug=f"tenant-a-{uuid4()}", name="A")
                tenant_b = Tenant(slug=f"tenant-b-{uuid4()}", name="B")
                raw.add_all([tenant_a, tenant_b])
                await raw.flush()
                workflow_a = Workflow(
                    tenant_id=tenant_a.id,
                    name="delivery",
                    version=1,
                    definition_hash="a" * 64,
                    definition={"entrypoint": "aegisflow.delivery.v1"},
                    status="active",
                )
                workflow_b = Workflow(
                    tenant_id=tenant_b.id,
                    name="delivery",
                    version=1,
                    definition_hash="b" * 64,
                    definition={"entrypoint": "aegisflow.delivery.v1"},
                    status="active",
                )
                raw.add_all([workflow_a, workflow_b])
                await raw.flush()
                raw.expunge_all()

                scoped = TenantSession(raw, TenantScope(tenant_a.id, "subject:test"))
                visible = list(await scoped.scalars(select(Workflow)))
                assert [item.tenant_id for item in visible] == [tenant_a.id]
                assert await scoped.get(Workflow, workflow_b.id) is None

                allowed = Workflow(
                    tenant_id=tenant_a.id,
                    name="allowed",
                    version=1,
                    definition_hash="d" * 64,
                    definition={},
                    status="active",
                )
                scoped.add(allowed)
                await scoped.flush()
                assert allowed.id is not None

                with pytest.raises(TenantScopeViolation):
                    scoped.add(
                        Workflow(
                            tenant_id=tenant_b.id,
                            name="forbidden",
                            version=1,
                            definition_hash="c" * 64,
                            definition={},
                            status="active",
                        )
                    )
                with pytest.raises(TenantScopeViolation):
                    await scoped.execute(select(Tenant))
                with pytest.raises(TenantScopeViolation):
                    await scoped.execute(text("SELECT 1"))

                await scoped.execute(
                    update(Workflow).values(status="superseded")
                )
                await scoped.flush()
                raw.expunge_all()
                status_rows = await raw.execute(
                    select(Workflow.id, Workflow.status)
                )
                statuses = {row.id: row.status for row in status_rows}
                assert statuses[workflow_a.id] == "superseded"
                assert statuses[workflow_b.id] == "active"
        finally:
            await transaction.rollback()
    await engine.dispose()
