"""Checkpointed state contract for the in-process Gate 1A LangGraph."""

from typing import Required, TypedDict
from uuid import UUID

from aegisflow_core.packs.delivery.contracts.clarification import Clarification
from aegisflow_core.packs.delivery.contracts.context_package import ContextPackage
from aegisflow_core.packs.delivery.contracts.normalized_request import (
    NormalizedRequest,
    SourceType,
)
from aegisflow_core.packs.delivery.contracts.plan import Plan
from aegisflow_core.packs.delivery.contracts.execution_result import ExecutionResult
from aegisflow_core.packs.delivery.contracts.policy_decision import PolicyDecision
from aegisflow_core.packs.delivery.contracts.review_decision import ReviewDecision
from aegisflow_core.gateway.github.pull_request import DraftPullRequestResult
from aegisflow_core.gateway.policy.gate import RepositoryTarget
from aegisflow_core.gateway.sandbox.runner import TestProfile


class AgentState(TypedDict, total=False):
    """Serializable state owned by LangGraph for one Gate 1A run."""

    run_id: Required[UUID]
    trace_id: Required[UUID]
    source_type: SourceType
    source_ref: str | None
    title: str
    body: str
    request: NormalizedRequest
    clarification: Clarification | None
    context: ContextPackage | None
    plan: Plan | None
    tenant_id: UUID
    repository_target: RepositoryTarget
    base_sha: str
    workspace_path: str
    test_profile: TestProfile
    policy_decision: PolicyDecision | None
    execution_result: ExecutionResult | None
    review_decision: ReviewDecision | None
    approval_reference: UUID | None
    review_step_id: UUID | None
    draft_pr_result: DraftPullRequestResult | None
    rework_count: int
    run_status: str
