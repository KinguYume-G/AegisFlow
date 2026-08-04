"""Versioned, immutable evaluation dataset and run contracts."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from hashlib import sha256
import json
import re
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, NonNegativeFloat, field_validator, model_validator

_ID = re.compile(r"^[a-z0-9][a-z0-9._-]{2,127}$")
_VERSION = re.compile(r"^[1-9][0-9]*\.[0-9]+\.[0-9]+$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_COMMIT = re.compile(r"^[0-9a-f]{40}$")


def canonical_hash(value: BaseModel | dict[str, Any]) -> str:
    payload = value.model_dump(mode="json") if isinstance(value, BaseModel) else value
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return sha256(encoded.encode("utf-8")).hexdigest()


class FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class CaseInput(FrozenModel):
    source_type: Literal["github_issue", "prd", "bug", "security_fixture"]
    title: str = Field(min_length=1, max_length=500)
    body: str = Field(min_length=1, max_length=50_000)
    repository: str | None = Field(default=None, max_length=512)
    base_commit: str | None = None

    @field_validator("title", "body")
    @classmethod
    def text_is_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("case text cannot be blank")
        return value

    @field_validator("base_commit")
    @classmethod
    def commit_is_full_sha(cls, value: str | None) -> str | None:
        if value is not None and not _COMMIT.fullmatch(value):
            raise ValueError("base_commit must be a full lowercase Git SHA")
        return value


class ExpectedOutcome(FrozenModel):
    task_completed: bool
    required_checks: tuple[str, ...] = ()
    forbidden_tools: tuple[str, ...] = ()
    injection_expected: bool | None = None
    expected_rule: str | None = None
    ground_truth_reference: str | None = Field(default=None, max_length=2048)

    @model_validator(mode="after")
    def injection_fields_are_consistent(self) -> "ExpectedOutcome":
        if self.expected_rule is not None and self.injection_expected is not True:
            raise ValueError("expected_rule requires injection_expected=true")
        return self


class CaseProvenance(FrozenModel):
    source_system: str = Field(min_length=1, max_length=100)
    source_reference: str = Field(min_length=1, max_length=2048)
    source_revision: str = Field(min_length=1, max_length=128)
    license_note: str = Field(min_length=1, max_length=1000)
    sanitization: str | None = Field(default=None, max_length=1000)


class EvaluationCase(FrozenModel):
    schema_version: Literal[1] = 1
    case_id: str
    dataset_id: str
    category: Literal[
        "swe_bench",
        "delivery",
        "security_sql",
        "security_secret",
        "security_token",
        "security_authorization",
        "security_prompt",
        "historical",
    ]
    input: CaseInput
    expected: ExpectedOutcome
    provenance: CaseProvenance
    tags: tuple[str, ...] = ()

    @field_validator("case_id", "dataset_id")
    @classmethod
    def identifiers_are_stable(cls, value: str) -> str:
        if not _ID.fullmatch(value):
            raise ValueError("identifier has invalid shape")
        return value

    @model_validator(mode="after")
    def historical_cases_require_real_sanitized_evidence(self) -> "EvaluationCase":
        if self.category == "historical":
            if self.provenance.source_system not in {
                "XueMai",
                "SynTour",
                "exilian-cyms",
            }:
                raise ValueError("historical source is not approved")
            if not self.provenance.sanitization or not self.expected.ground_truth_reference:
                raise ValueError("historical cases require sanitization and ground truth")
            if "synthetic" in self.tags:
                raise ValueError("synthetic cases cannot be historical evidence")
        return self


class DatasetManifest(FrozenModel):
    schema_version: Literal[1] = 1
    dataset_id: str
    version: str
    revision: str = Field(min_length=1, max_length=128)
    description: str = Field(min_length=1, max_length=2000)
    selection_criteria: tuple[str, ...]
    declared_case_count: int = Field(ge=1, le=10_000)
    cases: tuple[EvaluationCase, ...]

    @field_validator("dataset_id")
    @classmethod
    def dataset_identifier_is_stable(cls, value: str) -> str:
        if not _ID.fullmatch(value):
            raise ValueError("dataset_id has invalid shape")
        return value

    @field_validator("version")
    @classmethod
    def version_is_semver(cls, value: str) -> str:
        if not _VERSION.fullmatch(value):
            raise ValueError("dataset version must be semantic")
        return value

    @model_validator(mode="after")
    def cases_match_manifest(self) -> "DatasetManifest":
        if len(self.cases) != self.declared_case_count:
            raise ValueError("declared_case_count does not match cases")
        identifiers = [case.case_id for case in self.cases]
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("dataset case IDs must be unique")
        if any(case.dataset_id != self.dataset_id for case in self.cases):
            raise ValueError("case dataset_id does not match manifest")
        return self

    @property
    def content_hash(self) -> str:
        return canonical_hash(self)


class EvaluationControls(FrozenModel):
    model: str = Field(min_length=1, max_length=255)
    max_input_tokens: int = Field(gt=0)
    max_output_tokens: int = Field(gt=0)
    max_cost: Decimal = Field(ge=0)
    currency: str = Field(pattern=r"^[A-Z]{3}$")
    timeout_seconds: NonNegativeFloat = Field(gt=0, le=3600)
    allowed_tools: tuple[str, ...]


class MetricObservation(FrozenModel):
    name: str = Field(min_length=1, max_length=100)
    numerator: Decimal
    denominator: Decimal | None = None
    unit: Literal["count", "ratio", "milliseconds", "tokens", "currency"]

    @field_validator("numerator")
    @classmethod
    def numerator_is_finite_and_non_negative(cls, value: Decimal) -> Decimal:
        if not value.is_finite() or value < 0:
            raise ValueError("metric numerator must be finite and non-negative")
        return value

    @model_validator(mode="after")
    def denominator_is_valid(self) -> "MetricObservation":
        if self.denominator is not None and (
            not self.denominator.is_finite() or self.denominator <= 0
        ):
            raise ValueError("metric denominator must be positive")
        if self.unit == "ratio" and self.denominator is None:
            raise ValueError("ratio metrics require a denominator")
        return self


class EvaluationRun(FrozenModel):
    schema_version: Literal[1] = 1
    run_id: str
    subject: Literal["aegisflow", "single_agent"]
    case_id: str
    dataset_hash: str
    controls_hash: str
    started_at: datetime
    completed_at: datetime
    status: Literal["completed", "failed", "timed_out", "budget_exceeded"]
    metrics: tuple[MetricObservation, ...]
    tool_calls: tuple[str, ...] = ()
    error_code: str | None = None

    @field_validator("dataset_hash", "controls_hash")
    @classmethod
    def hashes_are_sha256(cls, value: str) -> str:
        if not _SHA256.fullmatch(value):
            raise ValueError("run hashes must be lowercase SHA-256")
        return value

    @model_validator(mode="after")
    def timestamps_and_status_are_consistent(self) -> "EvaluationRun":
        if self.completed_at < self.started_at:
            raise ValueError("completed_at cannot precede started_at")
        if self.status == "completed" and self.error_code is not None:
            raise ValueError("completed runs cannot contain error_code")
        if self.status != "completed" and not self.error_code:
            raise ValueError("non-completed runs require error_code")
        return self
