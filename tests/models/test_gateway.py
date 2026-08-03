from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pytest

from aegisflow_core.models.circuit_breaker import CircuitBreaker, InMemoryCircuitStateStore
from aegisflow_core.models.contracts import (
    ModelMessage,
    ModelRequest,
    ModelRoute,
    ProviderResult,
)
from aegisflow_core.models.gateway import (
    BudgetExceededError,
    ModelGateway,
    ModelGatewayError,
    ProviderError,
)
from aegisflow_core.runtime.tracing import unavailable_cost_usage, unavailable_token_usage


@dataclass
class Clock:
    def now(self) -> datetime:
        return datetime(2026, 8, 3, tzinfo=timezone.utc)


class Secrets:
    def resolve(self, environment_name: str) -> str:
        assert environment_name in {"PRIMARY_KEY", "FALLBACK_KEY"}
        return f"secret-for-{environment_name}"


class Adapter:
    def __init__(self, failures: dict[str, ProviderError] | None = None) -> None:
        self.failures = failures or {}
        self.calls: list[tuple[str, str]] = []

    async def complete(self, request, route, *, api_key):
        del request
        self.calls.append((route.name, api_key))
        if route.name in self.failures:
            raise self.failures[route.name]
        return ProviderResult(
            content=f"result:{route.name}",
            resolved_model=f"{route.model}:resolved",
            token_usage=unavailable_token_usage(),
            cost=unavailable_cost_usage(),
            latency_ms=1,
        )


def _request(*, budget=None, estimate=None) -> ModelRequest:
    return ModelRequest(
        tenant_id=uuid4(),
        run_id=uuid4(),
        trace_id=uuid4(),
        messages=(ModelMessage("user", "non-sensitive fixture"),),
        budget_limit_usd=budget,
        estimated_cost_usd=estimate,
    )


def _gateway(adapter: Adapter) -> ModelGateway:
    return ModelGateway(
        adapter,
        CircuitBreaker(InMemoryCircuitStateStore(), Clock(), failure_threshold=1),
        Secrets(),
        primary=ModelRoute("primary", "provider/model-a", "PRIMARY_KEY"),
        fallback=ModelRoute("fallback", "provider/model-b", "FALLBACK_KEY"),
    )


@pytest.mark.asyncio
async def test_primary_success_records_route_and_model() -> None:
    adapter = Adapter()
    response = await _gateway(adapter).complete(_request())
    assert response.content == "result:primary"
    assert response.resolved_model.endswith(":resolved")
    assert [item.route for item in response.route_chain] == ["primary"]
    assert adapter.calls == [("primary", "secret-for-PRIMARY_KEY")]


@pytest.mark.asyncio
async def test_availability_failure_falls_back_once() -> None:
    adapter = Adapter({"primary": ProviderError("timeout", availability_failure=True)})
    response = await _gateway(adapter).complete(_request())
    assert response.content == "result:fallback"
    assert [item.outcome for item in response.route_chain] == ["failed", "succeeded"]
    assert [item.route for item in response.route_chain] == ["primary", "fallback"]


@pytest.mark.asyncio
async def test_final_provider_error_does_not_fallback() -> None:
    adapter = Adapter({"primary": ProviderError("authentication", availability_failure=False)})
    with pytest.raises(ModelGatewayError) as captured:
        await _gateway(adapter).complete(_request())
    assert len(captured.value.attempts) == 1
    assert [call[0] for call in adapter.calls] == ["primary"]


@pytest.mark.asyncio
async def test_budget_denial_makes_zero_provider_calls() -> None:
    adapter = Adapter()
    with pytest.raises(BudgetExceededError):
        await _gateway(adapter).complete(
            _request(budget=Decimal("0.01"), estimate=Decimal("0.02"))
        )
    assert adapter.calls == []


@pytest.mark.asyncio
async def test_both_routes_fail_without_recursion() -> None:
    failure = ProviderError("timeout", availability_failure=True)
    adapter = Adapter({"primary": failure, "fallback": failure})
    with pytest.raises(ModelGatewayError) as captured:
        await _gateway(adapter).complete(_request())
    assert len(captured.value.attempts) == 2
    assert len(adapter.calls) == 2


@pytest.mark.asyncio
async def test_budget_with_unknown_estimate_fails_closed() -> None:
    adapter = Adapter()
    with pytest.raises(BudgetExceededError, match="estimate"):
        await _gateway(adapter).complete(_request(budget=Decimal("1")))
    assert adapter.calls == []


def test_environment_secret_resolver_never_invents_missing_value(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from aegisflow_core.models.gateway import EnvironmentSecretResolver

    monkeypatch.delenv("MISSING_PROVIDER_KEY", raising=False)
    with pytest.raises(ProviderError) as captured:
        EnvironmentSecretResolver().resolve("MISSING_PROVIDER_KEY")
    assert captured.value.availability_failure is False
