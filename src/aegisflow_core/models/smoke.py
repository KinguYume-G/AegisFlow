"""Protected real-provider smoke that prints metadata, never model content."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import json
from uuid import uuid4

from aegisflow_core.models.circuit_breaker import CircuitBreaker, InMemoryCircuitStateStore
from aegisflow_core.models.contracts import ModelMessage, ModelRequest, ModelRoute
from aegisflow_core.models.gateway import EnvironmentSecretResolver, ModelGateway
from aegisflow_core.models.litellm_adapter import LiteLLMAdapter
from aegisflow_core.settings import ConfigurationError, get_settings


class UtcClock:
    def now(self) -> datetime:
        return datetime.now(timezone.utc)


async def run() -> None:
    settings = get_settings()
    if not settings.model_gateway_configured:
        raise ConfigurationError("protected model gateway configuration is required")
    assert settings.model_primary_name and settings.model_primary_api_key_env
    assert settings.model_fallback_name and settings.model_fallback_api_key_env
    local_route = None
    if settings.model_local_fallback_configured:
        assert settings.model_local_fallback_name
        assert settings.model_local_fallback_api_key_env
        assert settings.model_local_fallback_base_url
        local_route = ModelRoute(
            "local_fallback", settings.model_local_fallback_name,
            settings.model_local_fallback_api_key_env,
            settings.model_local_fallback_base_url,
        )
    gateway = ModelGateway(
        LiteLLMAdapter(),
        CircuitBreaker(InMemoryCircuitStateStore(), UtcClock()),
        EnvironmentSecretResolver(),
        primary=ModelRoute(
            "primary", settings.model_primary_name, settings.model_primary_api_key_env
        ),
        fallback=ModelRoute(
            "fallback", settings.model_fallback_name, settings.model_fallback_api_key_env
        ),
        local_fallback=local_route,
    )
    response = await gateway.complete(
        ModelRequest(
            tenant_id=uuid4(),
            run_id=uuid4(),
            trace_id=uuid4(),
            messages=(
                ModelMessage(
                    "user", "Return the exact words: AegisFlow model smoke OK"
                ),
            ),
        )
    )
    print(
        json.dumps(
            {
                "status": "ok",
                "resolved_model": response.resolved_model,
                "token_status": response.token_usage.total_tokens.status,
                "cost_source": response.cost.source,
                "route_chain": [
                    {"route": item.route, "model": item.model, "outcome": item.outcome}
                    for item in response.route_chain
                ],
            },
            sort_keys=True,
        )
    )


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
