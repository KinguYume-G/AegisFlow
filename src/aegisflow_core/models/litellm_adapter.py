"""Narrow LiteLLM SDK adapter; AegisFlow owns retry and fallback."""

from __future__ import annotations

from decimal import Decimal
from time import monotonic
from typing import Any, Awaitable, Callable

from aegisflow_core.models.contracts import ModelRequest, ModelRoute, ProviderResult
from aegisflow_core.models.gateway import ProviderError
from aegisflow_core.runtime.tracing import (
    CostUsage,
    TokenMeasurement,
    TokenUsage,
    unavailable_cost_usage,
    unavailable_token_usage,
)


Completion = Callable[..., Awaitable[Any]]


class LiteLLMAdapter:
    def __init__(self, completion: Completion | None = None) -> None:
        if completion is None:
            from litellm import acompletion

            completion = acompletion
        self._completion = completion

    async def complete(
        self, request: ModelRequest, route: ModelRoute, *, api_key: str
    ) -> ProviderResult:
        started = monotonic()
        try:
            response = await self._completion(
                model=route.model,
                messages=[
                    {"role": message.role, "content": message.content}
                    for message in request.messages
                ],
                api_key=api_key,
                num_retries=0,
            )
        except Exception as error:
            raise _safe_provider_error(error) from None
        latency_ms = (monotonic() - started) * 1000
        content = _read(_read(response, "choices", [None])[0], "message", {})
        content = _read(content, "content", "")
        if not isinstance(content, str):
            raise ProviderError("malformed_response", availability_failure=False)
        model = _read(response, "model", route.model)
        usage = _usage(response)
        cost = _cost(response)
        return ProviderResult(content, str(model), usage, cost, latency_ms)


def _read(value: Any, name: str, default: Any = None) -> Any:
    if isinstance(value, dict):
        return value.get(name, default)
    return getattr(value, name, default)


def _usage(response: Any) -> TokenUsage:
    usage = _read(response, "usage")
    if usage is None:
        return unavailable_token_usage()
    prompt = _read(usage, "prompt_tokens")
    completion = _read(usage, "completion_tokens")
    total = _read(usage, "total_tokens")
    if not all(isinstance(value, int) and value >= 0 for value in (prompt, completion, total)):
        return unavailable_token_usage()
    if total != prompt + completion:
        return unavailable_token_usage()
    return TokenUsage(
        input_tokens=TokenMeasurement(status="measured", value=prompt),
        output_tokens=TokenMeasurement(status="measured", value=completion),
        total_tokens=TokenMeasurement(status="measured", value=total),
    )


def _cost(response: Any) -> CostUsage:
    hidden = _read(response, "_hidden_params", {}) or {}
    value = _read(hidden, "response_cost")
    if value is None:
        return unavailable_cost_usage()
    try:
        amount = Decimal(str(value))
        return CostUsage(amount=amount, currency="USD", source="provider_reported")
    except (ArithmeticError, ValueError):
        return unavailable_cost_usage()


def _safe_provider_error(error: Exception) -> ProviderError:
    name = type(error).__name__.lower()
    status = getattr(error, "status_code", None)
    if status == 429 or any(token in name for token in ("ratelimit", "timeout", "connection")):
        return ProviderError("availability", availability_failure=True)
    if isinstance(status, int) and status >= 500:
        return ProviderError("availability", availability_failure=True)
    if any(token in name for token in ("authentication", "permission", "badrequest")):
        return ProviderError("configuration", availability_failure=False)
    return ProviderError("provider_error", availability_failure=False)
