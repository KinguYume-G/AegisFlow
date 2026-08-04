"""Bounded local vLLM smoke; prints metadata only and never prompt/model output."""

from __future__ import annotations
import asyncio
import json
from uuid import uuid4
from aegisflow_core.models.contracts import ModelMessage, ModelRequest, ModelRoute
from aegisflow_core.models.gateway import EnvironmentSecretResolver
from aegisflow_core.models.litellm_adapter import LiteLLMAdapter
from aegisflow_core.settings import ConfigurationError, get_settings


async def run() -> None:
    settings = get_settings()
    if not settings.model_local_fallback_configured:
        raise ConfigurationError("enabled local model fallback configuration is required")
    assert settings.model_local_fallback_name and settings.model_local_fallback_api_key_env
    assert settings.model_local_fallback_base_url
    route = ModelRoute("local_fallback", settings.model_local_fallback_name,
                       settings.model_local_fallback_api_key_env, settings.model_local_fallback_base_url)
    result = await LiteLLMAdapter().complete(
        ModelRequest(uuid4(), uuid4(), uuid4(), (ModelMessage("user", "Return exactly: AegisFlow local smoke OK"),), max_output_tokens=16),
        route, api_key=EnvironmentSecretResolver().resolve(route.api_key_env),
    )
    print(json.dumps({
        "status": "ok", "route": route.name, "resolved_model": result.resolved_model,
        "latency_ms": round(result.latency_ms, 3),
        "token_status": result.token_usage.total_tokens.status,
        "total_tokens": result.token_usage.total_tokens.value,
        "cost_source": result.cost.source,
    }, sort_keys=True))


def main() -> None: asyncio.run(run())
if __name__ == "__main__": main()
