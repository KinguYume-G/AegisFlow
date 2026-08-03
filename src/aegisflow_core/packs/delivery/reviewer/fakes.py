"""Deterministic Reviewer and approval fakes."""

from typing import Literal
from uuid import UUID, uuid4
from aegisflow_core.packs.delivery.contracts.execution_result import ExecutionResult
from aegisflow_core.packs.delivery.contracts.plan import Plan
from aegisflow_core.packs.delivery.contracts.review_decision import ApprovalOutcome, ReviewFinding


class DeterministicReviewReasoner:
    def summarize(self, plan: Plan, result: ExecutionResult) -> list[ReviewFinding]:
        del plan
        return [ReviewFinding(severity="info", message=f"reviewed {len(result.changed_files)} changed files")]


class DuplicateApprovalDecisionError(RuntimeError): pass
class ApprovalRunMismatchError(RuntimeError): pass


class InMemoryApprovalGateway:
    def __init__(self) -> None:
        self._records: dict[UUID, dict[str, object]] = {}
        self._keys: dict[tuple[UUID, UUID, UUID], UUID] = {}

    async def request_approval(self, tenant_id: UUID, run_id: UUID, step_id: UUID,
                               findings: list[ReviewFinding]) -> UUID:
        key = tenant_id, run_id, step_id
        if key in self._keys:
            return self._keys[key]
        approval_id = uuid4()
        self._keys[key] = approval_id
        self._records[approval_id] = {"run_id": run_id, "status": "pending", "findings": tuple(findings)}
        return approval_id

    async def submit_decision(self, approval_id: UUID, run_id: UUID,
                              decision: Literal["approved", "rejected"], decided_by: str,
                              reason: str | None = None) -> ApprovalOutcome:
        record = self._records[approval_id]
        if record["run_id"] != run_id:
            raise ApprovalRunMismatchError
        if record["status"] != "pending":
            raise DuplicateApprovalDecisionError
        record["status"] = decision
        return ApprovalOutcome(approval_id=approval_id, decision=decision, decided_by=decided_by, reason=reason)

    async def get_status(self, approval_id: UUID) -> Literal["pending", "approved", "rejected"]:
        return self._records[approval_id]["status"]  # type: ignore[return-value]
