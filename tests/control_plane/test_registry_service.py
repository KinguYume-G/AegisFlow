"""AF-406 persisted immutable tool-registry tests."""

import os
from uuid import uuid4

import pytest
from sqlalchemy import delete, update
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from aegisflow_core.control_plane.domain import ToolDisablement, ToolRegistration, Tenant
from aegisflow_core.control_plane.registries import ToolRegistryService


@pytest.mark.database
@pytest.mark.anyio
async def test_registration_is_tenant_local_immutable_audited_and_disableable() -> None:
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        pytest.skip("DATABASE_URL is required")
    engine = create_async_engine(database_url)
    async with engine.connect() as connection:
        transaction = await connection.begin()
        sessions = async_sessionmaker(connection, expire_on_commit=False, join_transaction_mode="create_savepoint")
        try:
            async with sessions.begin() as session:
                tenant = Tenant(slug=f"registry-{uuid4()}", name="Registry")
                session.add(tenant); await session.flush()
                service = ToolRegistryService(session)
                values = dict(
                    tenant_id=tenant.id, owner_scope="tenant", canonical_name="repository_read",
                    version="1.0.0", adapter_identifier="internal.github.read",
                    input_schema_hash="a" * 64, output_schema_hash="b" * 64,
                    allowed_scopes=frozenset({"repository:read"}), risk_level="L1",
                    actor="issuer|admin", trace_id="trace-register",
                )
                registration = await service.register(**values)
                assert (await service.register(**values)).id == registration.id
                assert (await service.get_active(tenant.id, "repository_read", "1.0.0")).id == registration.id
                with pytest.raises(ValueError, match="immutable"):
                    await service.register(**(values | {"input_schema_hash": "c" * 64}))
                disabled = await service.disable(
                    tenant.id, registration.id, actor="issuer|admin",
                    reason="security review", trace_id="trace-disable",
                )
                assert isinstance(disabled, ToolDisablement)
                assert await service.get_active(tenant.id, "repository_read", "1.0.0") is None
                with pytest.raises(DBAPIError):
                    async with session.begin_nested():
                        await session.execute(update(ToolRegistration).where(ToolRegistration.id == registration.id).values(risk_level="L3"))
                with pytest.raises(DBAPIError):
                    async with session.begin_nested():
                        await session.execute(delete(ToolDisablement).where(ToolDisablement.id == disabled.id))
        finally:
            await transaction.rollback()
    await engine.dispose()


@pytest.mark.anyio
async def test_invalid_registration_fails_before_database_access() -> None:
    class Session:
        async def scalar(self, _value: object) -> object:
            raise AssertionError("invalid registration must fail before SQL")

    service = ToolRegistryService(Session())  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="canonical"):
        await service.register(
            tenant_id=uuid4(), owner_scope="tenant", canonical_name="Bad Name", version="1",
            adapter_identifier="internal", input_schema_hash="a" * 64,
            output_schema_hash="b" * 64, allowed_scopes=frozenset({"read"}),
            risk_level="L1", actor="actor", trace_id="trace",
        )
