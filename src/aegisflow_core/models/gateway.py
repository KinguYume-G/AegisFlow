"""Bounded primary/fallback model routing with explicit evidence."""

from __future__ import annotations

import os
from typing import Protocol

from aegisflow_core.models.circuit_breaker import CircuitBreaker
from aegisflow_core.models.contracts import (
    ModelRequest,
    ModelResponse,
    ModelRoute,
    ProviderResult,
    RouteAttempt,
)


class ProviderError(RuntimeError):
    def __init__(self, category: str, *, availability_failure: bool) -> None:
        super().__init__(category)
        self.category = category
        self.availability_failure = availability_failure


class ModelGatewayError(RuntimeError):
    def __init__(self, message: str, attempts: tuple[RouteAttempt, ...]) -> None:
        super().__init__(message)
        self.attempts = attempts


class BudgetExceededError(ModelGatewayError):
    pass


class ModelAdapter(Protocol):
    async def complete(
        self, request: ModelRequest, route: ModelRoute, *, api_key: str
    ) -> ProviderResult: ...


class SecretResolver(Protocol):
    def resolve(self, environment_name: str) -> str: ...


class EnvironmentSecretResolver:
    def resolve(self, environment_name: str) -> str:
        value = os.environ.get(environment_name)
        if not value:
            raise ProviderError("configuration", availability_failure=False)
        return value


class ModelGateway:
    def __init__(
        self,
        adapter: ModelAdapter,
        breaker: CircuitBreaker,
        secrets: SecretResolver,
        *,
        primary: ModelRoute,
        fallback: ModelRoute,
    ) -> None:
        if primary.name == fallback.name:
            raise ValueError("primary and fallback routes must have distinct names")
        self._adapter = adapter
        self._breaker = breaker
        self._secrets = secrets
        self._routes = (primary, fallback)

    async def complete(self, request: ModelRequest) -> ModelResponse:
        if request.budget_limit_usd is not None:
            if request.estimated_cost_usd is None:
                raise BudgetExceededError("cost estimate required", ())
            if request.estimated_cost_usd > request.budget_limit_usd:
                raise BudgetExceededError("request exceeds budget", ())

        attempts: list[RouteAttempt] = []
        for route in self._routes:
            permit = await self._breaker.acquire(request.tenant_id, route.name)
            if not permit.allowed:
                attempts.append(
                    RouteAttempt(route.name, route.model, "circuit_open", "availability")
                )
                continue
            try:
                api_key = self._secrets.resolve(route.api_key_env)
                result = await self._adapter.complete(
                    request, route, api_key=api_key
                )
            except ProviderError as error:
                attempts.append(
                    RouteAttempt(route.name, route.model, "failed", error.category)
                )
                if error.availability_failure:
                    await self._breaker.failure(request.tenant_id, route.name, permit)
                    continue
                # A final request/configuration error proves the provider path is
                # reachable and must release a possible half-open probe lease.
                await self._breaker.success(request.tenant_id, route.name, permit)
                raise ModelGatewayError("model request failed final", tuple(attempts)) from None
            await self._breaker.success(request.tenant_id, route.name, permit)
            attempts.append(RouteAttempt(route.name, route.model, "succeeded"))
            return ModelResponse(
                content=result.content,
                resolved_model=result.resolved_model,
                token_usage=result.token_usage,
                cost=result.cost,
                latency_ms=result.latency_ms,
                route_chain=tuple(attempts),
            )
        raise ModelGatewayError("all model routes unavailable", tuple(attempts))
