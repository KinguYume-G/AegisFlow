"""AF-403 fixed tenant-local RBAC tests."""

from __future__ import annotations

import os
from uuid import uuid4

import pytest
from sqlalchemy import delete, select, update
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from aegisflow_core.control_plane.domain import AuditEvent, RoleAssignment, Tenant, TenantMembership
from aegisflow_core.control_plane.identity import Principal
from aegisflow_core.control_plane.rbac import (
    Capability,
    Role,
    RbacService,
    capability_matrix,
)


def principal(subject: str) -> Principal:
    return Principal("https://issuer.example.test", subject)


def test_fixed_matrix_has_explicit_positive_and_negative_cases() -> None:
    matrix = capability_matrix()
    assert set(matrix) == set(Role)
    assert Capability.TENANT_ADMIN in matrix[Role.ADMIN]
    assert Capability.RUN_EXECUTE in matrix[Role.DEVELOPER]
    assert Capability.APPROVAL_DECIDE in matrix[Role.REVIEWER]
    assert Capability.SECURITY_READ in matrix[Role.SECURITY]
    assert Capability.DEPLOYMENT_OPERATE in matrix[Role.DEVOPS]
    assert matrix[Role.VIEWER] == frozenset({Capability.RUN_READ})
    assert Capability.TENANT_ADMIN not in matrix[Role.DEVELOPER]
    assert Capability.SANDBOX_EXECUTE not in matrix[Role.VIEWER]


@pytest.mark.database
@pytest.mark.anyio
async def test_roles_are_tenant_local_audited_and_self_approval_denies() -> None:
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        pytest.skip("DATABASE_URL is required")
    engine = create_async_engine(database_url)
    async with engine.connect() as connection:
        transaction = await connection.begin()
        sessions = async_sessionmaker(connection, expire_on_commit=False, join_transaction_mode="create_savepoint")
        try:
            async with sessions.begin() as session:
                tenant_a = Tenant(slug=f"rbac-a-{uuid4()}", name="A")
                tenant_b = Tenant(slug=f"rbac-b-{uuid4()}", name="B")
                session.add_all([tenant_a, tenant_b])
                await session.flush()
                admin = TenantMembership(tenant_id=tenant_a.id, issuer=principal("admin").issuer, subject=principal("admin").subject)
                developer = TenantMembership(tenant_id=tenant_a.id, issuer=principal("dev").issuer, subject=principal("dev").subject)
                other = TenantMembership(tenant_id=tenant_b.id, issuer=principal("dev").issuer, subject=principal("dev").subject)
                session.add_all([admin, developer, other])
                await session.flush()
                session.add(RoleAssignment(tenant_id=tenant_a.id, membership_id=admin.id, role=Role.ADMIN.value, assigned_by="bootstrap"))
                await session.flush()

                service = RbacService(session)
                grant = await service.assign_role(tenant_a.id, principal("admin"), developer.id, Role.DEVELOPER)
                assert grant.role == Role.DEVELOPER.value
                assert (await service.assign_role(tenant_a.id, principal("admin"), developer.id, Role.DEVELOPER)).id == grant.id
                with pytest.raises(LookupError):
                    await service.assign_role(tenant_a.id, principal("admin"), other.id, Role.DEVELOPER)
                allowed = await service.authorize(tenant_a.id, principal("dev"), Capability.RUN_EXECUTE)
                denied_other = await service.authorize(tenant_b.id, principal("dev"), Capability.RUN_EXECUTE)
                assert allowed.allowed and allowed.reason_code == "rbac_allowed"
                assert not denied_other.allowed and denied_other.reason_code == "rbac_capability_denied"

                session.add(RoleAssignment(tenant_id=tenant_a.id, membership_id=developer.id, role=Role.REVIEWER.value, assigned_by="bootstrap"))
                await session.flush()
                self_review = await service.authorize(
                    tenant_a.id,
                    principal("dev"),
                    Capability.APPROVAL_DECIDE,
                    target_actor_reference=principal("dev").actor_reference,
                )
                assert not self_review.allowed and self_review.reason_code == "rbac_self_approval_forbidden"

                audits = list(await session.scalars(select(AuditEvent).where(AuditEvent.tenant_id == tenant_a.id, AuditEvent.action == "rbac.role.assigned")))
                assert len(audits) == 1 and audits[0].actor == principal("admin").actor_reference

                revoked = await service.revoke_role(tenant_a.id, principal("admin"), grant.id)
                assert revoked.revoked_at is not None
                after_revoke = await service.authorize(tenant_a.id, principal("dev"), Capability.RUN_EXECUTE)
                assert not after_revoke.allowed
                revoked_audits = list(await session.scalars(select(AuditEvent).where(AuditEvent.tenant_id == tenant_a.id, AuditEvent.action == "rbac.role.revoked")))
                assert len(revoked_audits) == 1

                with pytest.raises(DBAPIError):
                    async with session.begin_nested():
                        await session.execute(update(RoleAssignment).where(RoleAssignment.id == grant.id).values(role=Role.ADMIN.value))
                with pytest.raises(DBAPIError):
                    async with session.begin_nested():
                        await session.execute(delete(RoleAssignment).where(RoleAssignment.id == grant.id))
        finally:
            await transaction.rollback()
    await engine.dispose()


@pytest.mark.database
@pytest.mark.anyio
async def test_missing_membership_unknown_values_and_non_admin_assignment_deny() -> None:
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        pytest.skip("DATABASE_URL is required")
    engine = create_async_engine(database_url)
    async with engine.connect() as connection:
        transaction = await connection.begin()
        sessions = async_sessionmaker(connection, expire_on_commit=False, join_transaction_mode="create_savepoint")
        try:
            async with sessions.begin() as session:
                tenant = Tenant(slug=f"rbac-deny-{uuid4()}", name="Deny")
                session.add(tenant)
                await session.flush()
                member = TenantMembership(tenant_id=tenant.id, issuer=principal("member").issuer, subject=principal("member").subject)
                session.add(member)
                await session.flush()
                service = RbacService(session)
                missing = await service.authorize(tenant.id, principal("missing"), Capability.RUN_READ)
                assert not missing.allowed and missing.reason_code == "rbac_membership_missing"
                with pytest.raises(ValueError):
                    await service.authorize(tenant.id, principal("member"), "unknown")  # type: ignore[arg-type]
                with pytest.raises(PermissionError, match="rbac_capability_denied"):
                    await service.assign_role(tenant.id, principal("member"), member.id, Role.ADMIN)
        finally:
            await transaction.rollback()
    await engine.dispose()
