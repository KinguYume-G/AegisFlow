from dataclasses import dataclass, field

import pytest

from aegisflow_core.runtime.temporal.saga import (
    CompensationAttempt,
    CompensationReceipt,
    RetryableCompensationError,
    SagaCompensator,
)


def _receipt(key: str) -> CompensationReceipt:
    return CompensationReceipt(key, "workspace", f"owned:{key}", f"hash:{key}")


@dataclass
class FakeExecutor:
    statuses: dict[str, str]
    calls: list[str] = field(default_factory=list)

    async def execute(self, receipt: CompensationReceipt) -> CompensationAttempt:
        self.calls.append(receipt.effect_key)
        return CompensationAttempt(receipt, self.statuses.get(receipt.effect_key, "compensated"))  # type: ignore[arg-type]


@dataclass
class FakeAudit:
    attempts: list[CompensationAttempt] = field(default_factory=list)

    async def record(self, attempt: CompensationAttempt) -> None:
        self.attempts.append(attempt)


@pytest.mark.asyncio
async def test_compensation_is_reverse_ordered_and_fully_audited() -> None:
    executor = FakeExecutor({})
    audit = FakeAudit()
    outcome = await SagaCompensator(executor, audit).compensate(
        (_receipt("one"), _receipt("two"), _receipt("three"))
    )
    assert outcome.status == "completed"
    assert executor.calls == ["three", "two", "one"]
    assert [attempt.receipt.effect_key for attempt in audit.attempts] == executor.calls


@pytest.mark.asyncio
async def test_already_compensated_is_repeatable_success() -> None:
    executor = FakeExecutor({"one": "already_compensated"})
    outcome = await SagaCompensator(executor, FakeAudit()).compensate((_receipt("one"),))
    assert outcome.status == "completed"
    assert outcome.attempts[0].status == "already_compensated"


@pytest.mark.asyncio
async def test_final_failure_escalates_and_preserves_remaining_receipts() -> None:
    executor = FakeExecutor({"two": "final_failed"})
    outcome = await SagaCompensator(executor, FakeAudit()).compensate(
        (_receipt("one"), _receipt("two"), _receipt("three"))
    )
    assert outcome.status == "manual_intervention_required"
    assert executor.calls == ["three", "two"]
    assert [item.effect_key for item in outcome.remaining] == ["two", "one"]


@pytest.mark.asyncio
async def test_retryable_failure_is_returned_to_temporal_retry_policy() -> None:
    executor = FakeExecutor({"one": "retryable_failed"})
    with pytest.raises(RetryableCompensationError):
        await SagaCompensator(executor, FakeAudit()).compensate((_receipt("one"),))


@pytest.mark.asyncio
async def test_executor_cannot_swap_receipt_identity() -> None:
    class BadExecutor:
        async def execute(self, receipt: CompensationReceipt) -> CompensationAttempt:
            return CompensationAttempt(_receipt("other"), "compensated")

    with pytest.raises(ValueError, match="mismatched"):
        await SagaCompensator(BadExecutor(), FakeAudit()).compensate((_receipt("one"),))
