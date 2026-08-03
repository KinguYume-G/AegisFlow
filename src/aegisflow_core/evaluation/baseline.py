"""Controlled single-agent baseline runner for like-for-like comparisons."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from decimal import Decimal
from time import perf_counter
from typing import Protocol

from aegisflow_core.evaluation.contracts import (
    EvaluationCase,
    EvaluationControls,
    MetricObservation,
)


@dataclass(frozen=True, slots=True)
class BaselineResult:
    completed: bool
    input_tokens: int
    output_tokens: int
    cost: Decimal
    currency: str
    tool_calls: tuple[str, ...]
    unauthorized_tool_attempts: int = 0


class SingleAgent(Protocol):
    async def run(
        self, evaluation_case: EvaluationCase, controls: EvaluationControls
    ) -> BaselineResult: ...


@dataclass(frozen=True, slots=True)
class BaselineEvidence:
    case_id: str
    model: str
    completed: bool
    metrics: tuple[MetricObservation, ...]
    tool_calls: tuple[str, ...]


class SingleAgentBaselineRunner:
    """Run an injected agent with explicit model, budget, timeout, and tools."""

    def __init__(self, agent: SingleAgent) -> None:
        self._agent = agent

    async def run(
        self, evaluation_case: EvaluationCase, controls: EvaluationControls
    ) -> BaselineEvidence:
        started = perf_counter()
        try:
            async with asyncio.timeout(float(controls.timeout_seconds)):
                result = await self._agent.run(evaluation_case, controls)
        except TimeoutError:
            raise RuntimeError("baseline_timeout") from None
        latency_ms = Decimal(str((perf_counter() - started) * 1000))
        if min(
            result.input_tokens,
            result.output_tokens,
            result.unauthorized_tool_attempts,
        ) < 0:
            raise ValueError("baseline measurements cannot be negative")
        if result.cost < 0:
            raise ValueError("baseline cost cannot be negative")
        if result.input_tokens > controls.max_input_tokens:
            raise RuntimeError("baseline_input_budget_exceeded")
        if result.output_tokens > controls.max_output_tokens:
            raise RuntimeError("baseline_output_budget_exceeded")
        if result.cost > controls.max_cost or result.currency != controls.currency:
            raise RuntimeError("baseline_cost_budget_exceeded")
        if any(tool not in controls.allowed_tools for tool in result.tool_calls):
            raise PermissionError("baseline_unauthorized_tool")
        return BaselineEvidence(
            case_id=evaluation_case.case_id,
            model=controls.model,
            completed=result.completed,
            tool_calls=result.tool_calls,
            metrics=(
                MetricObservation(
                    name="task_completion",
                    numerator=Decimal(int(result.completed)),
                    denominator=Decimal(1),
                    unit="ratio",
                ),
                MetricObservation(
                    name="token_cost",
                    numerator=result.cost,
                    unit="currency",
                ),
                MetricObservation(
                    name="latency",
                    numerator=latency_ms,
                    unit="milliseconds",
                ),
                MetricObservation(
                    name="unauthorized_tool_rate",
                    numerator=Decimal(result.unauthorized_tool_attempts),
                    denominator=Decimal(max(1, len(result.tool_calls))),
                    unit="ratio",
                ),
            ),
        )
