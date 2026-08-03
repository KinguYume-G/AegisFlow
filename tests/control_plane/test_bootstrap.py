"""PostgreSQL idempotency tests for M2 bootstrap facts."""

import asyncio
import os
from uuid import uuid4

import pytest
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from aegisflow_core.control_plane.bootstrap import (
    get_or_create_bootstrap_tenant,
    get_or_create_bootstrap_workflow,
)
from aegisflow_core.control_plane.domain import Tenant, Workflow


@pytest.mark.database
@pytest.mark.anyio
async def test_bootstrap_get_or_create_is_idempotent() -> None:
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        pytest.skip("DATABASE_URL is required")
    engine = create_async_engine(database_url)
    slug = f"af201-{uuid4()}"

    async with engine.connect() as connection:
        transaction = await connection.begin()
        sessions = async_sessionmaker(
            connection,
            expire_on_commit=False,
            join_transaction_mode="create_savepoint",
        )
        try:
            async with sessions.begin() as session:
                first = await get_or_create_bootstrap_tenant(session, slug)
            async with sessions.begin() as session:
                second = await get_or_create_bootstrap_tenant(session, slug)
                workflow = await get_or_create_bootstrap_workflow(
                    session, second.id, "gate1b", 1, "definition-hash"
                )
            async with sessions.begin() as session:
                same_workflow = await get_or_create_bootstrap_workflow(
                    session, second.id, "gate1b", 1, "definition-hash"
                )

            assert first.id == second.id
            assert workflow.id == same_workflow.id
        finally:
            await transaction.rollback()
    await engine.dispose()


@pytest.mark.database
@pytest.mark.anyio
async def test_concurrent_bootstrap_tenant_has_one_row() -> None:
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        pytest.skip("DATABASE_URL is required")
    engine = create_async_engine(database_url)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    slug = f"af201-concurrent-{uuid4()}"

    async def create() -> object:
        async with sessions.begin() as session:
            return await get_or_create_bootstrap_tenant(session, slug)

    try:
        tenants = await asyncio.gather(*(create() for _ in range(10)))
        assert len({tenant.id for tenant in tenants}) == 1
        async with sessions() as session:
            rows = list(await session.scalars(select(Tenant).where(Tenant.slug == slug)))
            assert len(rows) == 1
    finally:
        async with sessions.begin() as session:
            await session.execute(delete(Tenant).where(Tenant.slug == slug))
        await engine.dispose()
