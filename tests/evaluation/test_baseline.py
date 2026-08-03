"""AF-505 controlled single-agent baseline runner tests."""

import asyncio
from decimal import Decimal

import pytest

from aegisflow_core.evaluation.baseline import BaselineResult, SingleAgentBaselineRunner
from aegisflow_core.evaluation.contracts import (
    CaseInput,
    CaseProvenance,
    EvaluationCase,
    EvaluationControls,
    ExpectedOutcome,
)


def evaluation_case() -> EvaluationCase:
    return EvaluationCase(
        case_id="delivery.baseline-1",
        dataset_id="delivery-golden",
        category="delivery",
        input=CaseInput(source_type="bug", title="Fix", body="Run same task"),
        expected=ExpectedOutcome(task_completed=True),
        provenance=CaseProvenance(
            source_system="AegisFlow",
            source_reference="fixture:baseline",
            source_revision="1",
            license_note="Synthetic fixture.",
        ),
    )


def controls(**overrides: object) -> EvaluationControls:
    values: dict[str, object] = {
        "model": "deterministic-fake",
        "max_input_tokens": 100,
        "max_output_tokens": 50,
        "max_cost": Decimal("0.10"),
        "currency": "USD",
        "timeout_seconds": 1,
        "allowed_tools": ("repository_read",),
    }
    values.update(overrides)
    return EvaluationControls(**values)  # type: ignore[arg-type]


class Agent:
    def __init__(self, result: BaselineResult) -> None:
        self.result = result
        self.calls: list[tuple[EvaluationCase, EvaluationControls]] = []

    async def run(self, case: EvaluationCase, run_controls: EvaluationControls) -> BaselineResult:
        self.calls.append((case, run_controls))
        return self.result


@pytest.mark.anyio
async def test_runner_preserves_same_case_model_budget_and_reports_counts() -> None:
    result = BaselineResult(
        completed=True,
        input_tokens=40,
        output_tokens=20,
        cost=Decimal("0.01"),
        currency="USD",
        tool_calls=("repository_read",),
    )
    agent = Agent(result)
    case, run_controls = evaluation_case(), controls()
    evidence = await SingleAgentBaselineRunner(agent).run(case, run_controls)

    assert agent.calls == [(case, run_controls)]
    assert evidence.case_id == case.case_id
    assert evidence.model == run_controls.model
    completion = next(metric for metric in evidence.metrics if metric.name == "task_completion")
    assert (completion.numerator, completion.denominator) == (1, 1)


@pytest.mark.parametrize(
    ("result", "error"),
    [
        (BaselineResult(True, 101, 1, Decimal("0.01"), "USD", ()), "input_budget"),
        (BaselineResult(True, 1, 51, Decimal("0.01"), "USD", ()), "output_budget"),
        (BaselineResult(True, 1, 1, Decimal("0.11"), "USD", ()), "cost_budget"),
        (BaselineResult(True, 1, 1, Decimal("0.01"), "EUR", ()), "cost_budget"),
    ],
)
@pytest.mark.anyio
async def test_runner_fails_closed_on_budget_mismatch(
    result: BaselineResult, error: str
) -> None:
    with pytest.raises(RuntimeError, match=error):
        await SingleAgentBaselineRunner(Agent(result)).run(evaluation_case(), controls())


@pytest.mark.anyio
async def test_runner_rejects_unapproved_direct_tool() -> None:
    result = BaselineResult(
        True, 1, 1, Decimal("0.01"), "USD", ("repository_write",)
    )
    with pytest.raises(PermissionError, match="unauthorized_tool"):
        await SingleAgentBaselineRunner(Agent(result)).run(evaluation_case(), controls())


@pytest.mark.anyio
async def test_runner_enforces_timeout() -> None:
    class SlowAgent:
        async def run(self, case: EvaluationCase, run_controls: EvaluationControls) -> BaselineResult:
            del case, run_controls
            await asyncio.sleep(0.05)
            raise AssertionError("unreachable")

    with pytest.raises(RuntimeError, match="baseline_timeout"):
        await SingleAgentBaselineRunner(SlowAgent()).run(
            evaluation_case(), controls(timeout_seconds=0.001)
        )


@pytest.mark.parametrize(
    "result",
    [
        BaselineResult(True, -1, 0, Decimal("0"), "USD", ()),
        BaselineResult(True, 0, 0, Decimal("-0.01"), "USD", ()),
    ],
)
@pytest.mark.anyio
async def test_runner_rejects_negative_measurements(result: BaselineResult) -> None:
    with pytest.raises(ValueError, match="cannot be negative"):
        await SingleAgentBaselineRunner(Agent(result)).run(evaluation_case(), controls())
