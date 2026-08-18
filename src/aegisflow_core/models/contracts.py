"""Provider-neutral model gateway contracts with no Secret values."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Literal
from uuid import UUID

from aegisflow_core.runtime.tracing import CostUsage, TokenUsage


@dataclass(frozen=True, slots=True)
class ModelRoute:
    name: str
    model: str
    api_key_env: str
    api_base: str | None = None

    def __post_init__(self) -> None:
        if not all((self.name, self.model, self.api_key_env)):
            raise ValueError("model route fields must be non-empty")
        if self.api_base is not None and not self.api_base.strip():
            raise ValueError("api_base must contain text when configured")


@dataclass(frozen=True, slots=True)
class ModelMessage:
    role: Literal["system", "user", "assistant"]
    content: str

    def __post_init__(self) -> None:
        if not self.content:
            raise ValueError("model message content must be non-empty")


@dataclass(frozen=True, slots=True)
class ModelRequest:
    tenant_id: UUID
    run_id: UUID
    trace_id: UUID
    messages: tuple[ModelMessage, ...]
    max_output_tokens: int = 512
    budget_limit_usd: Decimal | None = None
    estimated_cost_usd: Decimal | None = None
    response_format: Literal["text", "json_object"] = "text"

    def __post_init__(self) -> None:
        if not self.messages:
            raise ValueError("at least one model message is required")
        if type(self.max_output_tokens) is not int or not 1 <= self.max_output_tokens <= 4096:
            raise ValueError("max_output_tokens must be an integer from 1 through 4096")
        for amount in (self.budget_limit_usd, self.estimated_cost_usd):
            if amount is not None and (not amount.is_finite() or amount < 0):
                raise ValueError("budget values must be finite and non-negative")


@dataclass(frozen=True, slots=True)
class ProviderResult:
    content: str
    resolved_model: str
    token_usage: TokenUsage
    cost: CostUsage
    latency_ms: float


@dataclass(frozen=True, slots=True)
class RouteAttempt:
    route: str
    model: str
    outcome: Literal["succeeded", "failed", "circuit_open"]
    error_category: str | None = None


@dataclass(frozen=True, slots=True)
class ModelResponse:
    content: str
    resolved_model: str
    token_usage: TokenUsage
    cost: CostUsage
    latency_ms: float
    route_chain: tuple[RouteAttempt, ...]
