"""Idempotent creation of the single M2 bootstrap tenant and workflow."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from aegisflow_core.control_plane.domain import Tenant, Workflow


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
