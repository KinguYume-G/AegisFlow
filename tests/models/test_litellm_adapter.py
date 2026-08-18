from uuid import uuid4

import pytest

from aegisflow_core.models.contracts import ModelMessage, ModelRequest, ModelRoute
from aegisflow_core.models.litellm_adapter import LiteLLMAdapter
from aegisflow_core.models.gateway import ProviderError


@pytest.mark.asyncio
async def test_adapter_disables_sdk_retry_and_extracts_usage_cost() -> None:
    captured = {}

    async def completion(**kwargs):
        captured.update(kwargs)
        return {
            "model": "provider/resolved-v1",
            "choices": [{"message": {"content": "ok"}}],
            "usage": {"prompt_tokens": 2, "completion_tokens": 3, "total_tokens": 5},
            "_hidden_params": {"response_cost": "0.001"},
        }

    request = ModelRequest(
        uuid4(), uuid4(), uuid4(), (ModelMessage("user", "fixture"),)
    )
    result = await LiteLLMAdapter(completion).complete(
        request, ModelRoute("primary", "provider/model", "KEY"), api_key="secret"
    )
    assert captured["num_retries"] == 0
    assert captured["max_tokens"] == 512
    assert captured["timeout"] == 60
    assert captured["temperature"] == 0
    assert captured["api_key"] == "secret"
    assert result.resolved_model == "provider/resolved-v1"
    assert result.token_usage.total_tokens.value == 5
    assert str(result.cost.amount) == "0.001"


@pytest.mark.asyncio
async def test_missing_usage_and_cost_are_explicitly_unavailable() -> None:
    async def completion(**kwargs):
        del kwargs
        return {"choices": [{"message": {"content": "ok"}}]}

    request = ModelRequest(
        uuid4(), uuid4(), uuid4(), (ModelMessage("user", "fixture"),)
    )
    result = await LiteLLMAdapter(completion).complete(
        request, ModelRoute("primary", "provider/model", "KEY"), api_key="secret"
    )
    assert result.token_usage.total_tokens.status == "not_available"
    assert result.cost.source == "not_available"


@pytest.mark.asyncio
async def test_local_route_forwards_only_explicit_api_base() -> None:
    captured = {}
    async def completion(**kwargs):
        captured.update(kwargs)
        return {"choices": [{"message": {"content": "local"}}]}
    request = ModelRequest(uuid4(), uuid4(), uuid4(), (ModelMessage("user", "fixture"),))
    route = ModelRoute("local_fallback", "openai/Qwen/Qwen3-0.6B", "LOCAL_KEY", "http://127.0.0.1:8000/v1")
    await LiteLLMAdapter(completion).complete(request, route, api_key="not-logged")
    assert captured["api_base"] == "http://127.0.0.1:8000/v1"
    assert captured["num_retries"] == 0


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("error", "availability"),
    [
        (TimeoutError(), True),
        (type("AuthenticationError", (Exception,), {})(), False),
        (RuntimeError(), False),
    ],
)
async def test_raw_sdk_errors_are_redacted_and_classified(error, availability) -> None:
    async def completion(**kwargs):
        del kwargs
        raise error

    request = ModelRequest(
        uuid4(), uuid4(), uuid4(), (ModelMessage("user", "fixture"),)
    )
    with pytest.raises(ProviderError) as captured:
        await LiteLLMAdapter(completion).complete(
            request, ModelRoute("primary", "provider/model", "KEY"), api_key="secret"
        )
    assert captured.value.availability_failure is availability
    assert "secret" not in str(captured.value)


@pytest.mark.parametrize("value", [0, 4097, True])
def test_model_request_rejects_unbounded_output(value) -> None:
    with pytest.raises(ValueError, match="max_output_tokens"):
        ModelRequest(
            uuid4(), uuid4(), uuid4(), (ModelMessage("user", "fixture"),),
            max_output_tokens=value,
        )
