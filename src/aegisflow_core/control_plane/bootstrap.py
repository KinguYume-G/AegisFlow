"""Idempotent creation of bootstrap tenants, workflows, and local identities."""

from dataclasses import dataclass
from hashlib import sha256
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from aegisflow_core.control_plane.domain import (
    RoleAssignment,
    Tenant,
    TenantMembership,
    Workflow,
)
from aegisflow_core.control_plane.identity import Principal
from aegisflow_core.control_plane.rbac import Role


@dataclass(frozen=True, slots=True)
class LocalBootstrap:
    tenant_id: UUID
    workflow_id: UUID
    workflow_version: int
    developer_membership_id: UUID
    reviewer_membership_id: UUID


@dataclass(frozen=True, slots=True)
class OidcDevelopmentBootstrap:
    tenant_id: UUID
    workflow_id: UUID
    workflow_version: int
    developer_membership_id: UUID
    reviewer_membership_id: UUID
    admin_membership_id: UUID


async def get_or_create_bootstrap_tenant(
    session: AsyncSession,
    slug: str,
) -> Tenant:
    """Return one tenant for a slug, safely under concurrent callers."""
    statement = (
        insert(Tenant)
        .values(slug=slug, name=slug)
        .on_conflict_do_nothing(index_elements=[Tenant.slug])
        .returning(Tenant)
    )
    tenant = (await session.execute(statement)).scalar_one_or_none()
    if tenant is not None:
        return tenant
    existing = await session.scalar(select(Tenant).where(Tenant.slug == slug))
    if existing is None:
        raise RuntimeError("bootstrap tenant could not be loaded after conflict")
    return existing


async def get_or_create_bootstrap_workflow(
    session: AsyncSession,
    tenant_id: UUID,
    name: str,
    version: int,
    definition_hash: str,
) -> Workflow:
    """Return one immutable workflow version under concurrent callers."""
    statement = (
        insert(Workflow)
        .values(
            tenant_id=tenant_id,
            name=name,
            version=version,
            definition_hash=definition_hash,
            status="active",
        )
        .on_conflict_do_nothing(
            index_elements=[Workflow.tenant_id, Workflow.name, Workflow.version]
        )
        .returning(Workflow)
    )
    workflow = (await session.execute(statement)).scalar_one_or_none()
    if workflow is not None:
        return workflow
    existing = await session.scalar(
        select(Workflow).where(
            Workflow.tenant_id == tenant_id,
            Workflow.name == name,
            Workflow.version == version,
        )
    )
    if existing is None:
        raise RuntimeError("bootstrap workflow could not be loaded after conflict")
    if existing.definition_hash != definition_hash:
        raise ValueError("bootstrap workflow definition hash does not match")
    return existing


async def bootstrap_local_mvp(
    session: AsyncSession,
    *,
    slug: str,
    developer: Principal,
    reviewer: Principal,
) -> LocalBootstrap:
    """Create the two-person local tenant and fixed Delivery workflow once."""
    if developer.actor_reference == reviewer.actor_reference:
        raise ValueError("local bootstrap principals must be distinct")
    tenant = await get_or_create_bootstrap_tenant(session, slug)
    definition_hash = sha256(b"aegisflow.delivery.v1").hexdigest()
    workflow = await get_or_create_bootstrap_workflow(
        session,
        tenant.id,
        "delivery",
        1,
        definition_hash,
    )
    developer_membership = await _get_or_create_membership(session, tenant.id, developer)
    reviewer_membership = await _get_or_create_membership(session, tenant.id, reviewer)
    await _get_or_create_role(
        session, tenant.id, developer_membership.id, Role.DEVELOPER
    )
    await _get_or_create_role(
        session, tenant.id, reviewer_membership.id, Role.REVIEWER
    )
    return LocalBootstrap(
        tenant_id=tenant.id,
        workflow_id=workflow.id,
        workflow_version=workflow.version,
        developer_membership_id=developer_membership.id,
        reviewer_membership_id=reviewer_membership.id,
    )


async def bootstrap_oidc_development(
    session: AsyncSession,
    *,
    slug: str,
    principals: dict[str, Principal],
) -> OidcDevelopmentBootstrap:
    """Provision three fixed local-IdP subjects; never called in production."""
    required = {Role.DEVELOPER.value, Role.REVIEWER.value, Role.ADMIN.value}
    if set(principals) != required:
        raise ValueError("OIDC development bootstrap requires fixed roles")
    if len({principal.actor_reference for principal in principals.values()}) != 3:
        raise ValueError("OIDC development bootstrap principals must be distinct")
    tenant = await get_or_create_bootstrap_tenant(session, slug)
    workflow = await get_or_create_bootstrap_workflow(
        session,
        tenant.id,
        "delivery",
        1,
        sha256(b"aegisflow.delivery.v1").hexdigest(),
    )
    memberships: dict[Role, TenantMembership] = {}
    for role in (Role.DEVELOPER, Role.REVIEWER, Role.ADMIN):
        membership = await _get_or_create_membership(
            session, tenant.id, principals[role.value]
        )
        await _get_or_create_role(
            session,
            tenant.id,
            membership.id,
            role,
            assigned_by="bootstrap:oidc-development",
        )
        memberships[role] = membership
    return OidcDevelopmentBootstrap(
        tenant_id=tenant.id,
        workflow_id=workflow.id,
        workflow_version=workflow.version,
        developer_membership_id=memberships[Role.DEVELOPER].id,
        reviewer_membership_id=memberships[Role.REVIEWER].id,
        admin_membership_id=memberships[Role.ADMIN].id,
    )


async def _get_or_create_membership(
    session: AsyncSession, tenant_id: UUID, principal: Principal
) -> TenantMembership:
    statement = (
        insert(TenantMembership)
        .values(
            tenant_id=tenant_id,
            issuer=principal.issuer,
            subject=principal.subject,
        )
        .on_conflict_do_nothing(
            index_elements=[
                TenantMembership.tenant_id,
                TenantMembership.issuer,
                TenantMembership.subject,
            ]
        )
        .returning(TenantMembership)
    )
    row = (await session.execute(statement)).scalar_one_or_none()
    if row is not None:
        return row
    existing = await session.scalar(
        select(TenantMembership).where(
            TenantMembership.tenant_id == tenant_id,
            TenantMembership.issuer == principal.issuer,
            TenantMembership.subject == principal.subject,
        )
    )
    if existing is None:
        raise RuntimeError("local membership could not be loaded after conflict")
    return existing


async def _get_or_create_role(
    session: AsyncSession,
    tenant_id: UUID,
    membership_id: UUID,
    role: Role,
    *,
    assigned_by: str = "bootstrap:local-mvp",
) -> RoleAssignment:
    existing = await session.scalar(
        select(RoleAssignment).where(
            RoleAssignment.tenant_id == tenant_id,
            RoleAssignment.membership_id == membership_id,
            RoleAssignment.role == role.value,
            RoleAssignment.revoked_at.is_(None),
        )
    )
    if existing is not None:
        return existing
    row = RoleAssignment(
        tenant_id=tenant_id,
        membership_id=membership_id,
        role=role.value,
        assigned_by=assigned_by,
    )
    session.add(row)
    await session.flush()
    return row
