"""PostgreSQL-backed idempotency claims with lease fencing."""

from __future__ import annotations

from collections.abc import Callable
from datetime import timedelta
from typing import Literal
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from aegisflow_core.control_plane.domain.idempotency import IdempotencyRecord
from aegisflow_core.packs.delivery.contracts.determinism import Clock
from aegisflow_core.packs.delivery.contracts.idempotency import Execute, FinalFailure, InProgress, Reuse


class ClaimLostError(RuntimeError):
    """A stale executor attempted to overwrite a newer fenced claim."""


class IdempotencyArgumentsMismatchError(RuntimeError):
    """The canonical key was reused with different arguments."""


class IdempotencyLedger:
    def __init__(
        self,
        session_factory: Callable[[], AsyncSession],
        clock: Clock,
        *,
        lease_seconds: int = 120,
    ) -> None:
        if lease_seconds <= 0:
            raise ValueError("lease_seconds must be positive")
        self._factory = session_factory
        self._clock = clock
        self._lease = timedelta(seconds=lease_seconds)

    async def begin(
        self,
        *,
        scope: Literal["webhook_delivery", "tool_call"],
        idempotency_key: str,
        tenant_id: UUID,
        arguments_hash: str,
        run_id: UUID | None,
        step_id: UUID | None,
        tool_name: str | None,
    ) -> Execute | Reuse | InProgress | FinalFailure:
        if not idempotency_key or not arguments_hash:
            raise ValueError("idempotency_key and arguments_hash are required")
        now = self._clock.now()
        token = uuid4()
        async with self._factory() as session, session.begin():
            statement = (
                insert(IdempotencyRecord)
                .values(
                    tenant_id=tenant_id,
                    scope=scope,
                    idempotency_key=idempotency_key,
                    arguments_hash=arguments_hash,
                    run_id=run_id,
                    step_id=step_id,
                    tool_name=tool_name,
                    status="executing",
                    claim_token=token,
                    attempt=1,
                    lease_expires_at=now + self._lease,
                    updated_at=now,
                )
                .on_conflict_do_nothing(
                    index_elements=["tenant_id", "scope", "idempotency_key"]
                )
                .returning(IdempotencyRecord.claim_token)
            )
            created = await session.scalar(statement)
            if created is not None:
                return Execute(created)

            row = await session.scalar(
                select(IdempotencyRecord)
                .where(
                    IdempotencyRecord.tenant_id == tenant_id,
                    IdempotencyRecord.scope == scope,
                    IdempotencyRecord.idempotency_key == idempotency_key,
                )
                .with_for_update()
            )
            if row is None:
                raise RuntimeError("idempotency claim disappeared")
            if row.arguments_hash != arguments_hash:
                raise IdempotencyArgumentsMismatchError(
                    "idempotency key is bound to different arguments"
                )
            if row.status == "succeeded":
                return Reuse(row.result_reference or "")
            if row.status in {"failed_final", "compensated"}:
                return FinalFailure(row.failure_reason or row.status)
            if row.status == "executing" and row.lease_expires_at > now:
                retry_after = max(0.0, (row.lease_expires_at - now).total_seconds())
                return InProgress(retry_after)
            if row.status not in {"executing", "failed_retryable"}:
                return FinalFailure(row.failure_reason or row.status)
            row.status = "executing"
            row.claim_token = token
            row.attempt += 1
            row.lease_expires_at = now + self._lease
            row.failure_reason = None
            row.updated_at = now
            return Execute(token)

    async def complete(
        self,
        idempotency_key: str,
        *,
        claim_token: UUID,
        result_reference: str,
    ) -> None:
        await self._transition(
            idempotency_key,
            claim_token=claim_token,
            status="succeeded",
            result_reference=result_reference,
            failure_reason=None,
        )

    async def fail(
        self,
        idempotency_key: str,
        *,
        claim_token: UUID,
        retryable: bool,
        reason: str | None = None,
    ) -> None:
        await self._transition(
            idempotency_key,
            claim_token=claim_token,
            status="failed_retryable" if retryable else "failed_final",
            result_reference=None,
            failure_reason=reason,
        )

    async def _transition(
        self,
        idempotency_key: str,
        *,
        claim_token: UUID,
        status: str,
        result_reference: str | None,
        failure_reason: str | None,
    ) -> None:
        async with self._factory() as session, session.begin():
            row = await session.scalar(
                select(IdempotencyRecord)
                .where(
                    IdempotencyRecord.idempotency_key == idempotency_key,
                    IdempotencyRecord.claim_token == claim_token,
                    IdempotencyRecord.status == "executing",
                )
                .with_for_update()
            )
            if row is None:
                raise ClaimLostError("claim token is stale or no longer executing")
            row.status = status
            row.result_reference = result_reference
            row.failure_reason = failure_reason
            row.updated_at = self._clock.now()
