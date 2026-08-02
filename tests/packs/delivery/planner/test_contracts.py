"""Contract tests for AF-107 measurement and plan schemas."""

from decimal import Decimal

import pytest
from pydantic import ValidationError

from aegisflow_core.packs.delivery.contracts.measurement import Measurement
from aegisflow_core.packs.delivery.contracts.plan import (
    TOOL_CAPABILITIES,
    Plan,
    PlanTask,
    ToolRequirement,
)


def test_measurement_not_available_invariant() -> None:
    measurement = Measurement(status="not_available", unit=None)

    assert measurement.value is None
    assert measurement.unit is None
    with pytest.raises(ValidationError):
        Measurement(status="not_available", value=Decimal("1"), unit="USD")
    with pytest.raises(ValidationError):
        Measurement(status="not_available", unit="USD")


def test_measurement_measured_invariant() -> None:
    measurement = Measurement(status="measured", value=Decimal("12.50"), unit="USD")

    assert measurement.value == Decimal("12.50")
    assert measurement.unit == "USD"
    with pytest.raises(ValidationError):
        Measurement(status="measured", value=Decimal("1"))
    with pytest.raises(ValidationError):
        Measurement(status="measured", unit="USD")
    with pytest.raises(ValidationError):
        Measurement(status="measured", value=Decimal("1"), unit="   ")
    with pytest.raises(ValidationError):
        Measurement(status="measured", value=Decimal("1"), unit="x" * 65)


@pytest.mark.parametrize("value", [Decimal("-0.01"), Decimal("NaN"), Decimal("Infinity"), Decimal("-Infinity")])
def test_measurement_rejects_negative_nan_infinity(value: Decimal) -> None:
    with pytest.raises(ValidationError):
        Measurement(status="measured", value=value, unit="USD")


def test_tool_capability_v1_exact_set() -> None:
    assert TOOL_CAPABILITIES == (
        "repository_read",
        "repository_write",
        "test_execute",
        "sandbox_execute",
        "pull_request_write",
    )
    for capability in TOOL_CAPABILITIES:
        assert ToolRequirement(tool_name=capability).tool_name == capability

    with pytest.raises(ValidationError):
        ToolRequirement(tool_name="github")
    with pytest.raises(ValidationError):
        ToolRequirement(tool_name="openai")


def test_plan_task_requires_structured_tools() -> None:
    task = PlanTask(
        description="Read repository evidence.",
        required_tools=[ToolRequirement(tool_name="repository_read")],
    )

    assert task.required_tools[0].tool_name == "repository_read"
    with pytest.raises(ValidationError):
        PlanTask(
            description="Read repository evidence.",
            required_tools=["repository_read"],  # type: ignore[list-item]
        )


def test_plan_text_and_task_capability_invariants() -> None:
    requirement = ToolRequirement(tool_name="repository_read")
    task = PlanTask(description="Read evidence.", required_tools=[requirement])

    with pytest.raises(ValidationError):
        PlanTask(description="   ", required_tools=[requirement])
    with pytest.raises(ValidationError):
        PlanTask(
            description="Read evidence.",
            required_tools=[requirement, requirement],
        )
    with pytest.raises(ValidationError):
        Plan(
            summary="   ",
            tasks=[task],
            risk_level="L1",
            budget_estimate=Measurement(status="not_available"),
            reasoner_id="test-reasoner",
        )
    with pytest.raises(ValidationError):
        Plan(
            summary="Evidence available.",
            tasks=[task],
            risk_level="L1",
            budget_estimate=Measurement(status="not_available"),
            reasoner_id="   ",
        )
