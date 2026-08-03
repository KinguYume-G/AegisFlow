"""Reviewer findings, approval, and terminal outcome contracts."""

from typing import Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, model_validator


class ReviewFinding(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    schema_version: Literal[1] = 1
    severity: Literal["info", "warning", "blocking"]
    message: str


class ReviewDecision(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    schema_version: Literal[1] = 1
    findings: list[ReviewFinding]
    approval_status: Literal["not_required", "pending", "approved", "rejected"]
    outcome: Literal["draft_pr", "rework", "rejected"] | None = None
    reasoner_id: str

    @model_validator(mode="after")
    def state_is_consistent(self) -> "ReviewDecision":
        if self.approval_status == "pending" and self.outcome is not None:
            raise ValueError("outcome must be absent while approval is pending")
        if self.approval_status != "pending" and self.outcome is None:
            raise ValueError("non-pending decisions require an outcome")
        return self


class ApprovalOutcome(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    schema_version: Literal[1] = 1
    approval_id: UUID
    decision: Literal["approved", "rejected"]
    decided_by: str
    reason: str | None = None
