"""Fenced Activity execution over the canonical PostgreSQL ledger."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from uuid import UUID

from temporalio.exceptions import ApplicationError

from aegisflow_core.control_plane.idempotency_ledger import IdempotencyLedger
from aegisflow_core.packs.delivery.contracts.idempotency import (
    Execute,
    FinalFailure,
    InProgress,
    Reuse,
)
from aegisflow_core.runtime.temporal.policies import (
    as_application_error,
    is_retryable,
)


@dataclass(frozen=True, slots=True)
class ExternalEffectRequest:
    tenant_id: UUID
    run_id: UUID
    step_id: UUID
    tool_name: str
    idempotency_key: str
    arguments_hash: str

    def __post_init__(self) -> None:
        if not all((self.tool_name, self.idempotency_key, self.arguments_hash)):
            raise ValueError("effect identity fields must be non-empty")


class IdempotentActivityRunner:
    def __init__(self, ledger: IdempotencyLedger) -> None:
        self._ledger = ledger

    async def run(
        self,
        request: ExternalEffectRequest,
        effect: Callable[[], Awaitable[str]],
    ) -> str:
        claim = await self._ledger.begin(
            scope="tool_call",
            idempotency_key=request.idempotency_key,
            tenant_id=request.tenant_id,
            arguments_hash=request.arguments_hash,
            run_id=request.run_id,
            step_id=request.step_id,
            tool_name=request.tool_name,
        )
        if isinstance(claim, Reuse):
            return claim.result_reference
        if isinstance(claim, InProgress):
            raise ApplicationError(
                "external effect is already in progress",
                type="transient",
                next_retry_delay=max_retry_delay(claim.retry_after_seconds),
            )
        if isinstance(claim, FinalFailure):
            raise ApplicationError(
                "external effect previously failed final",
                type="irreversible",
                non_retryable=True,
            )
        if not isinstance(claim, Execute):
            raise RuntimeError("unsupported idempotency claim")

        try:
            result = await effect()
        except Exception as error:
            await self._ledger.fail(
                request.idempotency_key,
                claim_token=claim.claim_token,
                retryable=is_retryable(error),
                reason=type(error).__name__,
            )
            raise as_application_error(error) from None
        await self._ledger.complete(
            request.idempotency_key,
            claim_token=claim.claim_token,
            result_reference=result,
        )
        return result


def max_retry_delay(seconds: float):
    from datetime import timedelta

    return timedelta(seconds=max(0.1, min(float(seconds), 30.0)))
