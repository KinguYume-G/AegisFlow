"""Deterministic Saga compensation contracts and reverse-order coordinator."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol


CompensationStatus = Literal[
    "compensated", "already_compensated", "retryable_failed", "final_failed"
]


@dataclass(frozen=True, slots=True)
class CompensationReceipt:
    """Exact identity of an owned external effect that can be compensated."""

    effect_key: str
    kind: str
    resource_reference: str
    arguments_hash: str

    def __post_init__(self) -> None:
        if not all(
            (self.effect_key, self.kind, self.resource_reference, self.arguments_hash)
        ):
            raise ValueError("compensation receipt fields must be non-empty")


@dataclass(frozen=True, slots=True)
class CompensationAttempt:
    receipt: CompensationReceipt
    status: CompensationStatus
    result_reference: str | None = None


@dataclass(frozen=True, slots=True)
class CompensationOutcome:
    status: Literal["completed", "manual_intervention_required"]
    attempts: tuple[CompensationAttempt, ...]
    remaining: tuple[CompensationReceipt, ...] = ()


class RetryableCompensationError(RuntimeError):
    """A compensation attempt may be retried by the Temporal Activity policy."""


class CompensationExecutor(Protocol):
    async def execute(self, receipt: CompensationReceipt) -> CompensationAttempt: ...


class CompensationAuditPort(Protocol):
    async def record(self, attempt: CompensationAttempt) -> None: ...


class SagaCompensator:
    """Compensate completed effects in reverse order without guessing cleanup."""

    def __init__(
        self, executor: CompensationExecutor, audit: CompensationAuditPort
    ) -> None:
        self._executor = executor
        self._audit = audit

    async def compensate(
        self, receipts: tuple[CompensationReceipt, ...]
    ) -> CompensationOutcome:
        attempts: list[CompensationAttempt] = []
        ordered = tuple(reversed(receipts))
        for index, receipt in enumerate(ordered):
            attempt = await self._executor.execute(receipt)
            if attempt.receipt != receipt:
                raise ValueError("compensation executor returned a mismatched receipt")
            attempts.append(attempt)
            await self._audit.record(attempt)
            if attempt.status == "retryable_failed":
                raise RetryableCompensationError(
                    f"retryable compensation failure for {receipt.kind}"
                )
            if attempt.status == "final_failed":
                return CompensationOutcome(
                    status="manual_intervention_required",
                    attempts=tuple(attempts),
                    remaining=ordered[index:],
                )
        return CompensationOutcome(status="completed", attempts=tuple(attempts))
