"""AF-405 append-only, tenant-scoped audit tests."""

import os
from uuid import uuid4

import pytest
from sqlalchemy import delete, update
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from aegisflow_core.control_plane.audit import AuditService
from aegisflow_core.control_plane.domain import AuditEvent, Tenant
from aegisflow_core.control_plane.tenants.scope import TenantScope, TenantScopeViolation


@pytest.mark.database
@pytest.mark.anyio
async def test_audit_is_complete_redacted_tenant_scoped_and_immutable() -> None:
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        pytest.skip("DATABASE_URL is required")
    engine = create_async_engine(database_url)
    async with engine.connect() as connection:
        transaction = await connection.begin()
        sessions = async_sessionmaker(connection, expire_on_commit=False, join_transaction_mode="create_savepoint")
        try:
            async with sessions.begin() as session:
                tenant_a = Tenant(slug=f"audit-a-{uuid4()}", name="A")
                tenant_b = Tenant(slug=f"audit-b-{uuid4()}", name="B")
                session.add_all([tenant_a, tenant_b])
                await session.flush()
                writer = AuditService(session)
                event = await writer.append(
                    tenant_id=tenant_a.id,
                    actor="issuer|subject",
                    action="policy.evaluate",
                    resource_type="tool",
                    resource_id="repository_read",
                    decision="deny",
                    reason="authorization=Bearer secret-value",
                    trace_id="trace-1",
                )
                await AuditService(session).append(
                    tenant_id=tenant_b.id,
                    actor="other",
                    action="policy.evaluate",
                    resource_type="tool",
                    resource_id="repository_read",
                    decision="allow",
                    reason="allowed",
                    trace_id="trace-2",
                )
                assert "secret-value" not in event.reason
                assert "[REDACTED]" in event.reason
                service = AuditService(session, TenantScope(tenant_a.id, "issuer|subject"))
                assert [row.id for row in await service.list_for_tenant(tenant_a.id)] == [event.id]
                with pytest.raises(TenantScopeViolation):
                    await service.list_for_tenant(tenant_b.id)
                with pytest.raises(TenantScopeViolation):
                    await writer.list_for_tenant(tenant_a.id)
                with pytest.raises(DBAPIError):
                    async with session.begin_nested():
                        await session.execute(update(AuditEvent).where(AuditEvent.id == event.id).values(reason="changed"))
                with pytest.raises(DBAPIError):
                    async with session.begin_nested():
                        await session.execute(delete(AuditEvent).where(AuditEvent.id == event.id))
        finally:
            await transaction.rollback()
    await engine.dispose()


@pytest.mark.anyio
async def test_audit_rejects_missing_or_oversized_fields() -> None:
    class Session:
        def add(self, _value: object) -> None:
            raise AssertionError("invalid audit must fail before persistence")

    service = AuditService(Session())  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="actor"):
        await service.append(
            tenant_id=uuid4(), actor="", action="x", resource_type="x",
            resource_id="x", decision="deny", reason="x", trace_id="x",
        )
    with pytest.raises(ValueError, match="reason"):
        await service.append(
            tenant_id=uuid4(), actor="a", action="x", resource_type="x",
            resource_id="x", decision="deny", reason="x" * 4097, trace_id="x",
        )


@pytest.mark.parametrize("credential", [
    "ghp_123456789012345678901234567890123456",
    "sk-1234567890abcdef",
    "AKIA1234567890ABCDEF",
    "postgresql://user:password@example.test/db",
    "-----BEGIN PRIVATE KEY-----\nfixture\n-----END PRIVATE KEY-----",
])
def test_audit_redacts_standalone_credential_signatures(credential: str) -> None:
    from aegisflow_core.control_plane.audit import redact_audit_text

    assert credential not in redact_audit_text(f"failure: {credential}")
    assert "[REDACTED]" in redact_audit_text(f"failure: {credential}")
