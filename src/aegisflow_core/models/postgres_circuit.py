"""PostgreSQL circuit store with row locking and fenced half-open probes."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from aegisflow_core.control_plane.domain.model_routing import ModelCircuitState
from aegisflow_core.models.circuit_breaker import CircuitPermit


class PostgresCircuitStateStore:
    def __init__(self, session_factory: Callable[[], AsyncSession]) -> None:
        self._factory = session_factory

    async def acquire(
        self,
        tenant_id: UUID,
        route: str,
        *,
        now: datetime,
        probe_lease: timedelta,
    ) -> CircuitPermit:
        async with self._factory() as session, session.begin():
            await session.execute(
                insert(ModelCircuitState)
                .values(
                    tenant_id=tenant_id,
                    route=route,
                    status="closed",
                    failure_count=0,
                    updated_at=now,
                )
                .on_conflict_do_nothing(index_elements=["tenant_id", "route"])
            )
            row = await self._locked(session, tenant_id, route)
            if row.status == "closed":
                return CircuitPermit(True, "closed")
            if row.status == "open" and row.open_until is not None and now < row.open_until:
                return CircuitPermit(False, "open")
            if (
                row.status == "half_open"
                and row.probe_lease_expires_at is not None
                and now < row.probe_lease_expires_at
            ):
                return CircuitPermit(False, "half_open")
            token = uuid4()
            row.status = "half_open"
            row.probe_token = token
            row.probe_lease_expires_at = now + probe_lease
            row.updated_at = now
            return CircuitPermit(True, "half_open", token)

    async def record_success(
        self,
        tenant_id: UUID,
        route: str,
        *,
        probe_token: UUID | None,
    ) -> None:
        async with self._factory() as session, session.begin():
            row = await self._locked(session, tenant_id, route)
            self._require_probe(row, probe_token)
            row.status = "closed"
            row.failure_count = 0
            row.open_until = None
            row.probe_token = None
            row.probe_lease_expires_at = None

    async def record_failure(
        self,
        tenant_id: UUID,
        route: str,
        *,
        now: datetime,
        threshold: int,
        open_duration: timedelta,
        probe_token: UUID | None,
    ) -> None:
        async with self._factory() as session, session.begin():
            row = await self._locked(session, tenant_id, route)
            self._require_probe(row, probe_token)
            row.failure_count += 1
            if row.status == "half_open" or row.failure_count >= threshold:
                row.status = "open"
                row.open_until = now + open_duration
            else:
                row.status = "closed"
                row.open_until = None
            row.probe_token = None
            row.probe_lease_expires_at = None
            row.updated_at = now

    async def _locked(
        self, session: AsyncSession, tenant_id: UUID, route: str
    ) -> ModelCircuitState:
        row = await session.scalar(
            select(ModelCircuitState)
            .where(
                ModelCircuitState.tenant_id == tenant_id,
                ModelCircuitState.route == route,
            )
            .with_for_update()
        )
        if row is None:
            raise RuntimeError("model circuit state disappeared")
        return row

    @staticmethod
    def _require_probe(row: ModelCircuitState, token: UUID | None) -> None:
        if row.status == "half_open" and row.probe_token != token:
            raise RuntimeError("half-open probe token is stale")
        if row.status != "half_open" and token is not None:
            raise RuntimeError("half-open probe token is stale")
