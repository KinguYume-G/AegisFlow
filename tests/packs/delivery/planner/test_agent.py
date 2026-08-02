"""Planner Agent gate and injection tests."""

from datetime import datetime, timezone
import inspect

import pytest

from aegisflow_core.packs.delivery.contracts.clarification import (
    Clarification,
    ClarificationQuestion,
)
from aegisflow_core.packs.delivery.contracts.context_package import ContextPackage
from aegisflow_core.packs.delivery.contracts.measurement import Measurement
from aegisflow_core.packs.delivery.contracts.normalized_request import NormalizedRequest
from aegisflow_core.packs.delivery.contracts.plan import Plan, PlanTask, ToolRequirement
from aegisflow_core.packs.delivery.planner.agent import (
    InsufficientClarificationError,
    PlannerAgent,
)


def _request() -> NormalizedRequest:
    return NormalizedRequest(
        source_type="bug",
        source_ref="BUG-107",
        title="Export planning",
        body="Create a deterministic plan.",
        idempotency_key="b" * 64,
        received_at=datetime(2026, 8, 2, tzinfo=timezone.utc),
    )


def _context() -> ContextPackage:
    return ContextPackage(
        snippets=[],
        unsupported_notes=["No evidence."],
        scanned_file_count=0,
        skipped_file_count=0,
        security_skip_count=0,
    )


def _plan() -> Plan:
    return Plan(
        summary="repository evidence unavailable",
        tasks=[
            PlanTask(
                description="Read evidence.",
                required_tools=[ToolRequirement(tool_name="repository_read")],
            )
        ],
        risk_level="L1",
        budget_estimate=Measurement(status="not_available"),
        reasoner_id="spy-planner",
    )


class SpyReasoner:
    def __init__(self) -> None:
        self.calls = 0

    def create_plan(
        self,
        request: NormalizedRequest,
        clarification: Clarification,
        context: ContextPackage,
    ) -> Plan:
        self.calls += 1
        return _plan()


class ExplodingReasoner:
    def create_plan(
        self,
        request: NormalizedRequest,
        clarification: Clarification,
        context: ContextPackage,
    ) -> Plan:
        raise RuntimeError("planner unavailable")


def test_planner_rejects_insufficient_clarification() -> None:
    pending = Clarification(
        questions=[ClarificationQuestion(field="scope", question="What scope?")],
        is_sufficient=False,
        reasoner_id="test-clarifier",
    )
    reasoner = SpyReasoner()

    with pytest.raises(InsufficientClarificationError):
        PlannerAgent(reasoner).plan(_request(), pending, _context())

    assert reasoner.calls == 0


def test_agent_requires_reasoner_and_propagates_error() -> None:
    sufficient = Clarification(
        questions=[],
        is_sufficient=True,
        reasoner_id="test-clarifier",
    )

    assert tuple(inspect.signature(PlannerAgent).parameters) == ("reasoner",)
    with pytest.raises(TypeError):
        PlannerAgent()  # type: ignore[call-arg]
    with pytest.raises(RuntimeError, match="planner unavailable"):
        PlannerAgent(ExplodingReasoner()).plan(_request(), sufficient, _context())
