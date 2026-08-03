"""Ledger-backed, fenced compensation Activity adapter."""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping
import hashlib
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from aegisflow_core.control_plane.domain.audit import AuditEvent
from aegisflow_core.control_plane.idempotency_ledger import IdempotencyLedger
from aegisflow_core.packs.delivery.contracts.idempotency import (
    Execute,
    FinalFailure,
    InProgress,
    Reuse,
)
from aegisflow_core.runtime.temporal.policies import is_retryable
from aegisflow_core.runtime.temporal.saga import (
    CompensationAttempt,
    CompensationReceipt,
)


CompensationHandler = Callable[[CompensationReceipt], Awaitable[str]]


class PostgresCompensationAudit:
    """Append one tenant-scoped fact for every compensation attempt."""

    def __init__(
        self, session_factory: Callable[[], AsyncSession], *, tenant_id: UUID
    ) -> None:
        self._factory = session_factory
        self._tenant_id = tenant_id

    async def record(self, attempt: CompensationAttempt) -> None:
        async with self._factory() as session, session.begin():
            session.add(
                AuditEvent(
                    tenant_id=self._tenant_id,
                    actor="temporal",
                    action="saga.compensation",
                    resource_type=attempt.receipt.kind,
                    resource_id=attempt.receipt.resource_reference,
                    decision=attempt.status,
                    reason=None,
                    trace_id=None,
                )
            )


class LedgerCompensationExecutor:
    """Run known compensation handlers once and mark the original effect."""

    def __init__(
        self,
        ledger: IdempotencyLedger,
        *,
        tenant_id: UUID,
        run_id: UUID,
        handlers: Mapping[str, CompensationHandler],
    ) -> None:
        self._ledger = ledger
        self._tenant_id = tenant_id
        self._run_id = run_id
        self._handlers = dict(handlers)

    async def execute(self, receipt: CompensationReceipt) -> CompensationAttempt:
        handler = self._handlers.get(receipt.kind)
        if handler is None:
            return CompensationAttempt(receipt, "final_failed")
        key = f"compensate:{receipt.effect_key}"
        arguments_hash = hashlib.sha256(
            (
                f"{receipt.effect_key}\0{receipt.kind}\0"
                f"{receipt.resource_reference}\0{receipt.arguments_hash}"
            ).encode("utf-8")
        ).hexdigest()
        claim = await self._ledger.begin(
            scope="compensation",
            idempotency_key=key,
            tenant_id=self._tenant_id,
            arguments_hash=arguments_hash,
            run_id=self._run_id,
            step_id=None,
            tool_name=f"compensate.{receipt.kind}",
        )
        if isinstance(claim, Reuse):
            return CompensationAttempt(
                receipt, "already_compensated", claim.result_reference
            )
        if isinstance(claim, InProgress):
            return CompensationAttempt(receipt, "retryable_failed")
        if isinstance(claim, FinalFailure):
            return CompensationAttempt(receipt, "final_failed")
        if not isinstance(claim, Execute):
            raise RuntimeError("unsupported compensation claim")
        try:
            result = await handler(receipt)
        except Exception as error:
            retryable = is_retryable(error)
            await self._ledger.fail(
                key,
                claim_token=claim.claim_token,
                retryable=retryable,
                reason=type(error).__name__,
            )
            return CompensationAttempt(
                receipt, "retryable_failed" if retryable else "final_failed"
            )
        await self._ledger.complete(
            key, claim_token=claim.claim_token, result_reference=result
        )
        await self._ledger.mark_compensated(
            receipt.effect_key,
            tenant_id=self._tenant_id,
            result_reference=result,
        )
        return CompensationAttempt(receipt, "compensated", result)
