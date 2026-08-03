from __future__ import annotations

from collections.abc import Awaitable, Callable
from uuid import uuid4

import pytest
from temporalio.exceptions import ApplicationError

from aegisflow_core.packs.delivery.contracts.idempotency import (
    Execute,
    FinalFailure,
    InProgress,
    Reuse,
)
from aegisflow_core.runtime.temporal.idempotent_activity import (
    ExternalEffectRequest,
    IdempotentActivityRunner,
)
from aegisflow_core.runtime.temporal.policies import AuthorizationFailure


class FakeLedger:
    def __init__(self, claim) -> None:
        self.claim = claim
        self.completed: list[tuple] = []
        self.failed: list[tuple] = []

    async def begin(self, **kwargs):
        self.begin_kwargs = kwargs
        return self.claim

    async def complete(self, key, **kwargs):
        self.completed.append((key, kwargs))

    async def fail(self, key, **kwargs):
        self.failed.append((key, kwargs))


def request() -> ExternalEffectRequest:
    return ExternalEffectRequest(
        uuid4(), uuid4(), uuid4(), "github.create_draft_pr", "effect:1", "sha256:abc"
    )


@pytest.mark.asyncio
async def test_execute_completes_once_and_reuse_skips_effect() -> None:
    token = uuid4()
    ledger = FakeLedger(Execute(token))
    calls = 0

    async def effect() -> str:
        nonlocal calls
        calls += 1
        return "pr:42"

    runner = IdempotentActivityRunner(ledger)  # type: ignore[arg-type]
    assert await runner.run(request(), effect) == "pr:42"
    assert calls == 1
    assert ledger.completed[0][1]["claim_token"] == token

    ledger.claim = Reuse("pr:42")
    assert await runner.run(request(), effect) == "pr:42"
    assert calls == 1


@pytest.mark.asyncio
async def test_in_progress_and_final_failure_never_execute_effect() -> None:
    calls = 0

    async def effect() -> str:
        nonlocal calls
        calls += 1
        return "unexpected"

    for claim in (InProgress(5), FinalFailure("denied")):
        runner = IdempotentActivityRunner(FakeLedger(claim))  # type: ignore[arg-type]
        with pytest.raises(ApplicationError):
            await runner.run(request(), effect)
    assert calls == 0


@pytest.mark.asyncio
async def test_nonretryable_failure_is_recorded_before_propagation() -> None:
    ledger = FakeLedger(Execute(uuid4()))

    async def effect() -> str:
        raise AuthorizationFailure("missing scope")

    runner = IdempotentActivityRunner(ledger)  # type: ignore[arg-type]
    with pytest.raises(ApplicationError) as captured:
        await runner.run(request(), effect)
    assert captured.value.non_retryable
    assert ledger.failed[0][1]["retryable"] is False
