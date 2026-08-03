"""Deterministic Reviewer rules and human decision resolution."""

from aegisflow_core.packs.delivery.contracts.execution_result import ExecutionResult
from aegisflow_core.packs.delivery.contracts.plan import Plan
from aegisflow_core.packs.delivery.contracts.review_decision import ApprovalOutcome, ReviewDecision, ReviewFinding
from aegisflow_core.packs.delivery.reviewer.ports import ReviewReasoner


class InvalidApprovalDecisionError(ValueError): pass


class ReviewerAgent:
    def __init__(self, reasoner: ReviewReasoner) -> None:
        self._reasoner = reasoner

    def review(self, plan: Plan, execution_result: ExecutionResult) -> ReviewDecision:
        reasoner_id = type(self._reasoner).__name__
        if execution_result.status == "failed":
            return ReviewDecision(findings=[ReviewFinding(severity="blocking", message="execution failed: tests did not pass")],
                                  approval_status="not_required", outcome="rework", reasoner_id=reasoner_id)
        return ReviewDecision(findings=self._reasoner.summarize(plan, execution_result),
                              approval_status="pending", outcome=None, reasoner_id=reasoner_id)

    def resolve(self, decision: ReviewDecision, approval: ApprovalOutcome) -> ReviewDecision:
        if decision.approval_status != "pending" or decision.outcome is not None:
            raise ValueError("resolve only applies to a pending decision")
        if approval.decision not in {"approved", "rejected"}:
            raise InvalidApprovalDecisionError(approval.decision)
        return decision.model_copy(update={"approval_status": approval.decision,
                                           "outcome": "draft_pr" if approval.decision == "approved" else "rejected"})
