"""Persistence boundary used by the Gate 1B runtime graph."""

from typing import Protocol
from uuid import UUID


class AsyncUnitOfWork(Protocol):
    async def __aenter__(self) -> "AsyncUnitOfWork": ...
    async def __aexit__(self, exc_type: object, exc: object, traceback: object) -> None: ...

    async def record_step(
        self,
        *,
        tenant_id: UUID,
        run_id: UUID,
        step_id: UUID,
        name: str,
        sequence: int,
        status: str,
    ) -> UUID: ...

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
    ) -> None: ...

    async def set_run_status(
        self, *, tenant_id: UUID, run_id: UUID, status: str
    ) -> None: ...
