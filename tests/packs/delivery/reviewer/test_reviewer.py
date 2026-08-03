from decimal import Decimal
from uuid import uuid4
import pytest

from aegisflow_core.packs.delivery.contracts.execution_result import ExecutionResult, TestOutcome as Outcome
from aegisflow_core.packs.delivery.contracts.measurement import Measurement
from aegisflow_core.packs.delivery.contracts.plan import Plan, PlanTask, ToolRequirement
from aegisflow_core.packs.delivery.reviewer.agent import ReviewerAgent
from aegisflow_core.packs.delivery.reviewer.fakes import DeterministicReviewReasoner, DuplicateApprovalDecisionError, InMemoryApprovalGateway
from aegisflow_core.packs.delivery.contracts.review_decision import ApprovalOutcome, ReviewDecision


def plan(): return Plan(summary="x",tasks=[PlanTask(description="x",required_tools=[ToolRequirement(tool_name="repository_read")])],risk_level="L1",budget_estimate=Measurement(status="measured",value=Decimal(1),unit="step"),reasoner_id="x")


def test_success_requires_human_and_failure_reworks() -> None:
    reviewer = ReviewerAgent(DeterministicReviewReasoner())
    ok = ExecutionResult(status="completed",patch="",changed_files=[],test_outcome=Outcome(status="passed",output_excerpt=""),reasoner_id="x")
    bad = ok.model_copy(update={"status":"failed","test_outcome":Outcome(status="failed",output_excerpt="")})
    assert reviewer.review(plan(), ok).approval_status == "pending"
    assert reviewer.review(plan(), bad).outcome == "rework"


@pytest.mark.asyncio
async def test_approval_gateway_is_idempotent_and_terminal() -> None:
    gateway = InMemoryApprovalGateway(); tenant, run, step = uuid4(), uuid4(), uuid4()
    first = await gateway.request_approval(tenant, run, step, [])
    assert first == await gateway.request_approval(tenant, run, step, [])
    await gateway.submit_decision(first, run, "approved", "human")
    with pytest.raises(DuplicateApprovalDecisionError): await gateway.submit_decision(first, run, "rejected", "human")


def test_reviewer_resolves_only_pending_human_decisions() -> None:
    reviewer = ReviewerAgent(DeterministicReviewReasoner())
    pending = ReviewDecision(findings=[],approval_status="pending",outcome=None,reasoner_id="fixture")
    approval = ApprovalOutcome(approval_id=uuid4(),decision="approved",decided_by="human")
    assert reviewer.resolve(pending, approval).outcome == "draft_pr"
    with pytest.raises(ValueError): reviewer.resolve(pending.model_copy(update={"approval_status":"approved","outcome":"draft_pr"}),approval)
