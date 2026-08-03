import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import os
from uuid import UUID, uuid4

import pytest
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from aegisflow_core.control_plane.domain import IdempotencyRecord, Tenant
from aegisflow_core.control_plane.idempotency_ledger import (
    ClaimLostError,
    IdempotencyArgumentsMismatchError,
    IdempotencyLedger,
)
from aegisflow_core.packs.delivery.contracts.idempotency import (
    Execute,
    FinalFailure,
    InProgress,
    Reuse,
)


@dataclass
class MutableClock:
    instant: datetime

    def now(self) -> datetime:
        return self.instant


async def _ledger() -> tuple[object, async_sessionmaker, UUID, MutableClock, IdempotencyLedger]:
    url = os.environ.get("DATABASE_URL")
    if not url:
        pytest.skip("DATABASE_URL is required")
    engine = create_async_engine(url)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    tenant_id = uuid4()
    async with sessions.begin() as session:
        session.add(Tenant(id=tenant_id, slug=f"ledger-{tenant_id.hex}", name="Ledger Test"))
    clock = MutableClock(datetime(2026, 8, 3, tzinfo=timezone.utc))
    return engine, sessions, tenant_id, clock, IdempotencyLedger(sessions, clock, lease_seconds=30)


async def _cleanup(engine: object, sessions: async_sessionmaker, tenant_id: UUID) -> None:
    async with sessions.begin() as session:
        await session.execute(delete(IdempotencyRecord).where(IdempotencyRecord.tenant_id == tenant_id))
        await session.execute(delete(Tenant).where(Tenant.id == tenant_id))
    await engine.dispose()  # type: ignore[attr-defined]


@pytest.mark.database
@pytest.mark.asyncio
async def test_ledger_lifecycle_returns_all_explicit_claim_results() -> None:
    engine, sessions, tenant, clock, ledger = await _ledger()
    try:
        first = await ledger.begin(
            scope="tool_call", idempotency_key="key", tenant_id=tenant,
            arguments_hash="args", run_id=uuid4(), step_id=uuid4(), tool_name="github.create_draft_pr",
        )
        assert isinstance(first, Execute)
        assert isinstance(await ledger.begin(
            scope="tool_call", idempotency_key="key", tenant_id=tenant,
            arguments_hash="args", run_id=None, step_id=None, tool_name=None,
        ), InProgress)
        await ledger.complete("key", claim_token=first.claim_token, result_reference="result")
        reused = await ledger.begin(
            scope="tool_call", idempotency_key="key", tenant_id=tenant,
            arguments_hash="args", run_id=None, step_id=None, tool_name=None,
        )
        assert isinstance(reused, Reuse) and reused.result_reference == "result"

        final = await ledger.begin(
            scope="webhook_delivery", idempotency_key="delivery", tenant_id=tenant,
            arguments_hash="payload", run_id=None, step_id=None, tool_name=None,
        )
        assert isinstance(final, Execute)
        await ledger.fail("delivery", claim_token=final.claim_token, retryable=False, reason="invalid")
        assert isinstance(await ledger.begin(
            scope="webhook_delivery", idempotency_key="delivery", tenant_id=tenant,
            arguments_hash="payload", run_id=None, step_id=None, tool_name=None,
        ), FinalFailure)
    finally:
        await _cleanup(engine, sessions, tenant)


@pytest.mark.database
@pytest.mark.asyncio
async def test_expired_lease_fences_stale_executor_and_arguments() -> None:
    engine, sessions, tenant, clock, ledger = await _ledger()
    try:
        first = await ledger.begin(
            scope="tool_call", idempotency_key="fence", tenant_id=tenant,
            arguments_hash="v1", run_id=None, step_id=None, tool_name="tool",
        )
        assert isinstance(first, Execute)
        with pytest.raises(IdempotencyArgumentsMismatchError):
            await ledger.begin(
                scope="tool_call", idempotency_key="fence", tenant_id=tenant,
                arguments_hash="v2", run_id=None, step_id=None, tool_name="tool",
            )
        clock.instant += timedelta(seconds=31)
        second = await ledger.begin(
            scope="tool_call", idempotency_key="fence", tenant_id=tenant,
            arguments_hash="v1", run_id=None, step_id=None, tool_name="tool",
        )
        assert isinstance(second, Execute) and second.claim_token != first.claim_token
        with pytest.raises(ClaimLostError):
            await ledger.complete("fence", claim_token=first.claim_token, result_reference="stale")
        await ledger.complete("fence", claim_token=second.claim_token, result_reference="current")
    finally:
        await _cleanup(engine, sessions, tenant)


@pytest.mark.database
@pytest.mark.asyncio
async def test_concurrent_begin_has_exactly_one_executor() -> None:
    engine, sessions, tenant, clock, ledger = await _ledger()
    try:
        results = await asyncio.gather(*(
            ledger.begin(
                scope="webhook_delivery", idempotency_key="same-delivery", tenant_id=tenant,
                arguments_hash="same-payload", run_id=None, step_id=None, tool_name=None,
            )
            for _ in range(10)
        ))
        assert sum(isinstance(result, Execute) for result in results) == 1
        assert sum(isinstance(result, InProgress) for result in results) == 9
    finally:
        await _cleanup(engine, sessions, tenant)


@pytest.mark.database
@pytest.mark.asyncio
async def test_succeeded_tool_effect_can_be_marked_compensated_once() -> None:
    engine, sessions, tenant, clock, ledger = await _ledger()
    try:
        claim = await ledger.begin(
            scope="tool_call",
            idempotency_key="effect-to-compensate",
            tenant_id=tenant,
            arguments_hash="args",
            run_id=None,
            step_id=None,
            tool_name="github.create_draft_pr",
        )
        assert isinstance(claim, Execute)
        await ledger.complete(
            "effect-to-compensate",
            claim_token=claim.claim_token,
            result_reference="created",
        )
        await ledger.mark_compensated(
            "effect-to-compensate", tenant_id=tenant, result_reference="closed"
        )
        await ledger.mark_compensated(
            "effect-to-compensate", tenant_id=tenant, result_reference="closed"
        )
        result = await ledger.begin(
            scope="tool_call",
            idempotency_key="effect-to-compensate",
            tenant_id=tenant,
            arguments_hash="args",
            run_id=None,
            step_id=None,
            tool_name=None,
        )
        assert isinstance(result, FinalFailure)
    finally:
        await _cleanup(engine, sessions, tenant)
