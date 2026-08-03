from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from aegisflow_core.gateway.github.idempotency_guard import (
    LedgerWebhookDispatcher,
    PostgresIdempotencyGuard,
)
from aegisflow_core.gateway.github.webhook import WebhookVerificationResult
from aegisflow_core.packs.delivery.contracts.idempotency import (
    Execute,
    FinalFailure,
    IdempotentCommand,
    InProgress,
    Reuse,
)


def command() -> IdempotentCommand:
    return IdempotentCommand(
        scope="tool_call", idempotency_key="key", arguments_hash="args",
        tenant_id=uuid4(), run_id=uuid4(), step_id=uuid4(), tool_name="tool",
    )


@pytest.mark.asyncio
async def test_postgres_guard_maps_and_completes_claim() -> None:
    token = uuid4()
    ledger = AsyncMock()
    ledger.begin.return_value = Execute(token)
    guard = PostgresIdempotencyGuard(ledger)
    assert await guard.begin(command()) == Execute(token)
    await guard.complete(token, "result")
    ledger.complete.assert_awaited_once_with("key", claim_token=token, result_reference="result")


@pytest.mark.asyncio
async def test_postgres_guard_fails_claim_and_rejects_unknown_token() -> None:
    token = uuid4()
    ledger = AsyncMock()
    ledger.begin.return_value = Execute(token)
    guard = PostgresIdempotencyGuard(ledger)
    await guard.begin(command())
    await guard.fail(token, True, "timeout")
    ledger.fail.assert_awaited_once_with(
        "key", claim_token=token, retryable=True, reason="timeout"
    )
    with pytest.raises(KeyError):
        await guard.complete(uuid4(), "x")
    with pytest.raises(KeyError):
        await guard.fail(uuid4(), False, "x")


def event() -> WebhookVerificationResult:
    return WebhookVerificationResult(
        accepted=True, delivery_id="delivery", event="repository_dispatch",
        installation_id="42", repository="owner/repo", rejection_reason=None,
        payload={"action": "gate1b"},
    )


@pytest.mark.asyncio
async def test_ledger_webhook_dispatcher_claims_completes_and_deduplicates() -> None:
    token = uuid4()
    ledger, inner = AsyncMock(), AsyncMock()
    ledger.begin.side_effect = [Execute(token), Reuse("done"), InProgress(1)]
    dispatcher = LedgerWebhookDispatcher(ledger=ledger, tenant_id=uuid4(), inner=inner)
    await dispatcher.dispatch(event())
    await dispatcher.dispatch(event())
    await dispatcher.dispatch(event())
    assert inner.dispatch.await_count == 1
    ledger.complete.assert_awaited_once()


@pytest.mark.asyncio
async def test_ledger_webhook_dispatcher_marks_failure_and_final_failure() -> None:
    token = uuid4()
    ledger, inner = AsyncMock(), AsyncMock()
    ledger.begin.return_value = Execute(token)
    inner.dispatch.side_effect = RuntimeError("untrusted")
    dispatcher = LedgerWebhookDispatcher(ledger=ledger, tenant_id=uuid4(), inner=inner)
    with pytest.raises(RuntimeError, match="untrusted"):
        await dispatcher.dispatch(event())
    ledger.fail.assert_awaited_once()

    ledger.begin.return_value = FinalFailure("denied")
    inner.dispatch.side_effect = None
    with pytest.raises(RuntimeError, match="failed permanently"):
        await dispatcher.dispatch(event())
