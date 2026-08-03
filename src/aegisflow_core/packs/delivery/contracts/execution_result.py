"""Structured Executor output contracts."""

from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator

from aegisflow_core.packs.delivery.contracts.measurement import Measurement


def _not_available() -> Measurement:
    return Measurement(status="not_available")


class TestOutcome(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    schema_version: Literal[1] = 1
    status: Literal["passed", "failed", "timeout", "error"]
    passed_count: Measurement = Field(default_factory=_not_available)
    failed_count: Measurement = Field(default_factory=_not_available)
    output_excerpt: str = Field(max_length=8000)


class ExecutionResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    schema_version: Literal[1] = 1
    status: Literal["completed", "failed"]
    patch: str = Field(max_length=1_000_000)
    changed_files: list[str] = Field(max_length=100)
    test_outcome: TestOutcome
    reasoner_id: str

    @field_validator("changed_files")
    @classmethod
    def unique_files(cls, value: list[str]) -> list[str]:
        if len(value) != len(set(value)):
            raise ValueError("changed_files must not contain duplicates")
        return value
