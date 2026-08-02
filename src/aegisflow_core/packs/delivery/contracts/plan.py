"""Version 1 deterministic plan schemas for DeliveryPack."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

from aegisflow_core.packs.delivery.contracts.measurement import Measurement


TOOL_CAPABILITIES = (
    "repository_read",
    "repository_write",
    "test_execute",
    "sandbox_execute",
    "pull_request_write",
)
ToolCapability = Literal[
    "repository_read",
    "repository_write",
    "test_execute",
    "sandbox_execute",
    "pull_request_write",
]
TaskDescription = Annotated[str, StringConstraints(min_length=1, max_length=1_000)]
PlanSummary = Annotated[str, StringConstraints(min_length=1, max_length=5_000)]


class ToolRequirement(BaseModel):
    """One stable v1 capability required by a plan task."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1] = 1
    tool_name: ToolCapability


class PlanTask(BaseModel):
    """One ordered, bounded unit of work with structured capabilities."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1] = 1
    description: TaskDescription
    required_tools: list[ToolRequirement] = Field(min_length=1, max_length=10)

    @field_validator("description")
    @classmethod
    def description_must_contain_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("task description must contain non-whitespace text")
        return value

    @field_validator("required_tools")
    @classmethod
    def required_tools_must_be_unique(
        cls, value: list[ToolRequirement]
    ) -> list[ToolRequirement]:
        names = [requirement.tool_name for requirement in value]
        if len(names) != len(set(names)):
            raise ValueError("required tool capabilities must be unique per task")
        return value


class Plan(BaseModel):
    """A stable plan, risk classification, and evidence-backed budget state."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1] = 1
    summary: PlanSummary
    tasks: list[PlanTask] = Field(min_length=1, max_length=100)
    risk_level: Literal["L1", "L2", "L3"]
    budget_estimate: Measurement
    reasoner_id: str

    @field_validator("summary", "reasoner_id")
    @classmethod
    def text_must_contain_non_whitespace(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("plan text fields must contain non-whitespace text")
        return value
