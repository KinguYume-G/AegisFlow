from uuid import uuid4

import pytest

from aegisflow_core.packs.delivery.contracts.idempotency import (
    Execute,
    FinalFailure,
    InProgress,
    Reuse,
)
from aegisflow_core.runtime.temporal.policies import TransientFailure
from aegisflow_core.runtime.temporal.saga import CompensationReceipt
from aegisflow_core.runtime.temporal.saga_ledger import LedgerCompensationExecutor


class FakeLedger:
    def __init__(self, claim) -> None:
        self.claim = claim
        self.completed = []
        self.failed = []
        self.compensated = []

    async def begin(self, **kwargs):
        self.begin_kwargs = kwargs
        return self.claim

    async def complete(self, key, **kwargs):
        self.completed.append((key, kwargs))

    async def fail(self, key, **kwargs):
        self.failed.append((key, kwargs))

    async def mark_compensated(self, key, **kwargs):
        self.compensated.append((key, kwargs))


def _receipt() -> CompensationReceipt:
    return CompensationReceipt("original-effect", "workspace", "owned:path", "hash")


def _executor(ledger, handler=None):
    async def default(receipt):
        del receipt
        return "removed"

    return LedgerCompensationExecutor(
        ledger,
        tenant_id=uuid4(),
        run_id=uuid4(),
        handlers={"workspace": handler or default},
    )


@pytest.mark.asyncio
async def test_execute_completes_compensation_claim_and_original_effect() -> None:
    ledger = FakeLedger(Execute(uuid4()))
    result = await _executor(ledger).execute(_receipt())
    assert result.status == "compensated"
    assert ledger.begin_kwargs["scope"] == "compensation"
    assert ledger.completed[0][0] == "compensate:original-effect"
    assert ledger.compensated[0][0] == "original-effect"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("claim", "status"),
    [
        (Reuse("done"), "already_compensated"),
        (InProgress(1), "retryable_failed"),
        (FinalFailure("final"), "final_failed"),
    ],
)
async def test_existing_claims_map_to_explicit_attempts(claim, status) -> None:
    result = await _executor(FakeLedger(claim)).execute(_receipt())
    assert result.status == status


@pytest.mark.asyncio
async def test_unknown_compensation_kind_fails_without_ledger_write() -> None:
    ledger = FakeLedger(Execute(uuid4()))
    executor = LedgerCompensationExecutor(
        ledger, tenant_id=uuid4(), run_id=uuid4(), handlers={}
    )
    assert (await executor.execute(_receipt())).status == "final_failed"
    assert not hasattr(ledger, "begin_kwargs")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("error", "status", "retryable"),
    [
        (TransientFailure("down"), "retryable_failed", True),
        (ValueError("invalid"), "final_failed", False),
    ],
)
async def test_handler_failure_is_classified_and_recorded(error, status, retryable) -> None:
    async def failing(receipt):
        del receipt
        raise error

    ledger = FakeLedger(Execute(uuid4()))
    result = await _executor(ledger, failing).execute(_receipt())
    assert result.status == status
    assert ledger.failed[0][1]["retryable"] is retryable
