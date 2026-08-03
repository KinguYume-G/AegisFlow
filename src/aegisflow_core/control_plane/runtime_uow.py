"""Transactional PostgreSQL unit of work for Gate 1B facts."""

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from aegisflow_core.control_plane.domain import AuditEvent, Run, Step


class PostgresRuntimeUnitOfWork:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._transaction = None

    async def __aenter__(self) -> "PostgresRuntimeUnitOfWork":
        self._transaction = self._session.begin()
        await self._transaction.__aenter__()
        return self

    async def __aexit__(self, exc_type: object, exc: object, traceback: object) -> None:
        assert self._transaction is not None
        await self._transaction.__aexit__(exc_type, exc, traceback)
        await self._session.close()

    async def record_step(
        self,
        *,
        tenant_id: UUID,
        run_id: UUID,
        step_id: UUID,
        name: str,
        sequence: int,
        status: str,
    ) -> UUID:
        statement = (
            insert(Step)
            .values(
                id=step_id,
                tenant_id=tenant_id,
                run_id=run_id,
                name=name,
                sequence=sequence,
                status=status,
                completed_at=(datetime.now(timezone.utc) if status == "completed" else None),
            )
            .on_conflict_do_update(
                index_elements=["run_id", "sequence"],
                set_={
                    "status": status,
                    "completed_at": (
                        datetime.now(timezone.utc) if status == "completed" else None
                    ),
                },
            )
            .returning(Step.id)
        )
        return (await self._session.execute(statement)).scalar_one()

    async def record_audit(
        self,
        *,
        tenant_id: UUID,
        actor: str,
        action: str,
        resource_type: str,
        resource_id: str,
        decision: str,
        reason: str | None,
        trace_id: UUID,
    ) -> None:
        self._session.add(
            AuditEvent(
                tenant_id=tenant_id,
                actor=actor,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                decision=decision,
                reason=reason,
                trace_id=str(trace_id),
            )
        )

    async def set_run_status(
        self, *, tenant_id: UUID, run_id: UUID, status: str
    ) -> None:
        result = await self._session.execute(
            update(Run)
            .where(Run.tenant_id == tenant_id, Run.id == run_id)
            .values(status=status, updated_at=datetime.now(timezone.utc))
        )
        if result.rowcount != 1:
            raise KeyError("run does not exist in the tenant scope")
