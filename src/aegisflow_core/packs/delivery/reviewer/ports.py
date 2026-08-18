"""Reviewer and approval ports."""

from typing import Literal, Protocol
from uuid import UUID
from aegisflow_core.packs.delivery.contracts.execution_result import ExecutionResult
from aegisflow_core.packs.delivery.contracts.plan import Plan
from aegisflow_core.packs.delivery.contracts.review_decision import ApprovalOutcome, ReviewFinding


class ReviewReasoner(Protocol):
    def summarize(self, plan: Plan, result: ExecutionResult) -> list[ReviewFinding]: ...


class ApprovalGateway(Protocol):
    async def request_approval(
        self,
        tenant_id: UUID,
        run_id: UUID,
        step_id: UUID,
        findings: list[ReviewFinding],
        *,
        action_preview: dict[str, object] | None = None,
        action_digest: str | None = None,
    ) -> UUID: ...
    async def submit_decision(self, approval_id: UUID, run_id: UUID,
                              decision: Literal["approved", "rejected"], decided_by: str,
                              reason: str | None = None) -> ApprovalOutcome: ...
    async def get_status(self, approval_id: UUID) -> Literal["pending", "approved", "rejected"]: ...
