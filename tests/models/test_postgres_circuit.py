from datetime import datetime, timedelta, timezone
import os
from uuid import UUID, uuid4

import pytest
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from aegisflow_core.control_plane.domain import ModelCircuitState, Tenant
from aegisflow_core.models.postgres_circuit import PostgresCircuitStateStore


async def _store() -> tuple[object, async_sessionmaker, UUID, PostgresCircuitStateStore]:
    url = os.environ.get("DATABASE_URL")
    if not url:
        pytest.skip("DATABASE_URL is required")
    engine = create_async_engine(url)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    tenant_id = uuid4()
    async with sessions.begin() as session:
        session.add(Tenant(id=tenant_id, slug=f"circuit-{tenant_id.hex}", name="Circuit Test"))
    return engine, sessions, tenant_id, PostgresCircuitStateStore(sessions)


@pytest.mark.database
@pytest.mark.asyncio
async def test_postgres_store_persists_open_half_open_and_close() -> None:
    engine, sessions, tenant, store = await _store()
    now = datetime(2026, 8, 3, tzinfo=timezone.utc)
    try:
        permit = await store.acquire(tenant, "primary", now=now, probe_lease=timedelta(seconds=10))
        await store.record_failure(
            tenant,
            "primary",
            now=now,
            threshold=1,
            open_duration=timedelta(seconds=30),
            probe_token=permit.probe_token,
        )
        assert not (
            await store.acquire(tenant, "primary", now=now, probe_lease=timedelta(seconds=10))
        ).allowed
        probe = await store.acquire(
            tenant,
            "primary",
            now=now + timedelta(seconds=31),
            probe_lease=timedelta(seconds=10),
        )
        assert probe.status == "half_open" and probe.probe_token
        await store.record_success(tenant, "primary", probe_token=probe.probe_token)
        closed = await store.acquire(
            tenant,
            "primary",
            now=now + timedelta(seconds=31),
            probe_lease=timedelta(seconds=10),
        )
        assert closed.allowed and closed.status == "closed"
    finally:
        async with sessions.begin() as session:
            await session.execute(delete(ModelCircuitState).where(ModelCircuitState.tenant_id == tenant))
            await session.execute(delete(Tenant).where(Tenant.id == tenant))
        await engine.dispose()  # type: ignore[attr-defined]
