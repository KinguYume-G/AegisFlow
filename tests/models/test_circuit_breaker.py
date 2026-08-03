from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from aegisflow_core.models.circuit_breaker import (
    CircuitBreaker,
    InMemoryCircuitStateStore,
)


@dataclass
class MutableClock:
    instant: datetime

    def now(self) -> datetime:
        return self.instant


@pytest.mark.asyncio
async def test_closed_opens_at_threshold_and_half_open_success_closes() -> None:
    tenant = uuid4()
    clock = MutableClock(datetime(2026, 8, 3, tzinfo=timezone.utc))
    store = InMemoryCircuitStateStore()
    breaker = CircuitBreaker(store, clock, failure_threshold=2, open_seconds=30)

    first = await breaker.acquire(tenant, "primary")
    await breaker.failure(tenant, "primary", first)
    assert (await breaker.acquire(tenant, "primary")).allowed
    second = await breaker.acquire(tenant, "primary")
    await breaker.failure(tenant, "primary", second)
    assert not (await breaker.acquire(tenant, "primary")).allowed

    clock.instant += timedelta(seconds=31)
    probe = await breaker.acquire(tenant, "primary")
    assert probe.allowed and probe.status == "half_open" and probe.probe_token
    assert not (await breaker.acquire(tenant, "primary")).allowed
    await breaker.success(tenant, "primary", probe)
    assert (await breaker.acquire(tenant, "primary")).status == "closed"


@pytest.mark.asyncio
async def test_half_open_failure_reopens_and_stale_probe_is_rejected() -> None:
    tenant = uuid4()
    clock = MutableClock(datetime(2026, 8, 3, tzinfo=timezone.utc))
    store = InMemoryCircuitStateStore()
    breaker = CircuitBreaker(store, clock, failure_threshold=1, open_seconds=1)
    permit = await breaker.acquire(tenant, "primary")
    await breaker.failure(tenant, "primary", permit)
    clock.instant += timedelta(seconds=2)
    probe = await breaker.acquire(tenant, "primary")
    await breaker.failure(tenant, "primary", probe)
    assert not (await breaker.acquire(tenant, "primary")).allowed
    with pytest.raises(RuntimeError, match="stale"):
        await store.record_success(tenant, "primary", probe_token=probe.probe_token)


@pytest.mark.asyncio
async def test_circuit_state_is_tenant_scoped() -> None:
    tenant_a, tenant_b = uuid4(), uuid4()
    clock = MutableClock(datetime(2026, 8, 3, tzinfo=timezone.utc))
    store = InMemoryCircuitStateStore()
    breaker = CircuitBreaker(store, clock, failure_threshold=1)
    permit = await breaker.acquire(tenant_a, "primary")
    await breaker.failure(tenant_a, "primary", permit)
    assert not (await breaker.acquire(tenant_a, "primary")).allowed
    assert (await breaker.acquire(tenant_b, "primary")).allowed
