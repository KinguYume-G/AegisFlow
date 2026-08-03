"""Tenant-scoped deterministic circuit breaker state machine."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from typing import Literal, Protocol
from uuid import UUID, uuid4

from aegisflow_core.packs.delivery.contracts.determinism import Clock


CircuitStatus = Literal["closed", "open", "half_open"]


@dataclass(frozen=True, slots=True)
class CircuitState:
    status: CircuitStatus = "closed"
    failure_count: int = 0
    open_until: datetime | None = None
    probe_token: UUID | None = None
    probe_lease_expires_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class CircuitPermit:
    allowed: bool
    status: CircuitStatus
    probe_token: UUID | None = None


class CircuitStateStore(Protocol):
    async def acquire(
        self,
        tenant_id: UUID,
        route: str,
        *,
        now: datetime,
        probe_lease: timedelta,
    ) -> CircuitPermit: ...

    async def record_success(
        self,
        tenant_id: UUID,
        route: str,
        *,
        probe_token: UUID | None,
    ) -> None: ...

    async def record_failure(
        self,
        tenant_id: UUID,
        route: str,
        *,
        now: datetime,
        threshold: int,
        open_duration: timedelta,
        probe_token: UUID | None,
    ) -> None: ...


class InMemoryCircuitStateStore:
    """Concurrency-safe deterministic store for tests and local composition."""

    def __init__(self) -> None:
        self._states: dict[tuple[UUID, str], CircuitState] = {}
        self._lock = asyncio.Lock()

    async def acquire(
        self,
        tenant_id: UUID,
        route: str,
        *,
        now: datetime,
        probe_lease: timedelta,
    ) -> CircuitPermit:
        async with self._lock:
            key = (tenant_id, route)
            state = self._states.get(key, CircuitState())
            if state.status == "closed":
                return CircuitPermit(True, "closed")
            if state.status == "open" and state.open_until is not None and now < state.open_until:
                return CircuitPermit(False, "open")
            if (
                state.status == "half_open"
                and state.probe_lease_expires_at is not None
                and now < state.probe_lease_expires_at
            ):
                return CircuitPermit(False, "half_open")
            token = uuid4()
            self._states[key] = replace(
                state,
                status="half_open",
                probe_token=token,
                probe_lease_expires_at=now + probe_lease,
            )
            return CircuitPermit(True, "half_open", token)

    async def record_success(
        self,
        tenant_id: UUID,
        route: str,
        *,
        probe_token: UUID | None,
    ) -> None:
        async with self._lock:
            key = (tenant_id, route)
            state = self._states.get(key, CircuitState())
            _require_probe_owner(state, probe_token)
            self._states[key] = CircuitState()

    async def record_failure(
        self,
        tenant_id: UUID,
        route: str,
        *,
        now: datetime,
        threshold: int,
        open_duration: timedelta,
        probe_token: UUID | None,
    ) -> None:
        async with self._lock:
            key = (tenant_id, route)
            state = self._states.get(key, CircuitState())
            _require_probe_owner(state, probe_token)
            failures = state.failure_count + 1
            if state.status == "half_open" or failures >= threshold:
                self._states[key] = CircuitState(
                    status="open",
                    failure_count=failures,
                    open_until=now + open_duration,
                )
            else:
                self._states[key] = CircuitState(failure_count=failures)

    async def snapshot(self, tenant_id: UUID, route: str) -> CircuitState:
        async with self._lock:
            return self._states.get((tenant_id, route), CircuitState())


class CircuitBreaker:
    def __init__(
        self,
        store: CircuitStateStore,
        clock: Clock,
        *,
        failure_threshold: int = 3,
        open_seconds: int = 30,
        probe_lease_seconds: int = 10,
    ) -> None:
        if min(failure_threshold, open_seconds, probe_lease_seconds) <= 0:
            raise ValueError("circuit breaker settings must be positive")
        self._store = store
        self._clock = clock
        self._threshold = failure_threshold
        self._open_duration = timedelta(seconds=open_seconds)
        self._probe_lease = timedelta(seconds=probe_lease_seconds)

    async def acquire(self, tenant_id: UUID, route: str) -> CircuitPermit:
        return await self._store.acquire(
            tenant_id, route, now=self._clock.now(), probe_lease=self._probe_lease
        )

    async def success(
        self, tenant_id: UUID, route: str, permit: CircuitPermit
    ) -> None:
        await self._store.record_success(
            tenant_id, route, probe_token=permit.probe_token
        )

    async def failure(
        self, tenant_id: UUID, route: str, permit: CircuitPermit
    ) -> None:
        await self._store.record_failure(
            tenant_id,
            route,
            now=self._clock.now(),
            threshold=self._threshold,
            open_duration=self._open_duration,
            probe_token=permit.probe_token,
        )


def _require_probe_owner(state: CircuitState, token: UUID | None) -> None:
    if state.status == "half_open" and state.probe_token != token:
        raise RuntimeError("half-open probe token is stale")
    if state.status != "half_open" and token is not None:
        raise RuntimeError("half-open probe token is stale")
