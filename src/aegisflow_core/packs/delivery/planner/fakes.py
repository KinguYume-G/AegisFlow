"""Deterministic Planner reasoner used before model-provider integration."""

from collections.abc import Iterable

from aegisflow_core.packs.delivery.contracts.clarification import Clarification
from aegisflow_core.packs.delivery.contracts.context_package import ContextPackage
from aegisflow_core.packs.delivery.contracts.measurement import Measurement
from aegisflow_core.packs.delivery.contracts.normalized_request import NormalizedRequest
from aegisflow_core.packs.delivery.contracts.plan import Plan, PlanTask, ToolRequirement


_REASONER_ID = "deterministic-planner-v1"
_SENSITIVE_MARKERS = ("tenant", "权限", "secret", "支付", "审计")
_TASKS = (
    ("Read cited repository evidence.", "repository_read"),
    ("Implement the smallest scoped change.", "repository_write"),
    ("Run the required tests and quality gates.", "test_execute"),
    ("Prepare a Draft pull request for human review.", "pull_request_write"),
)


def _all_input_text(
    request: NormalizedRequest,
    clarification: Clarification,
    context: ContextPackage,
) -> Iterable[str]:
    yield request.title
    yield request.body
    if clarification.answers:
        yield from clarification.answers.values()
    yield from (snippet.content for snippet in context.snippets)
    yield from context.unsupported_notes


class DeterministicPlanReasoner:
    """Apply the approved fixed planning algorithm without external I/O."""

    def create_plan(
        self,
        request: NormalizedRequest,
        clarification: Clarification,
        context: ContextPackage,
    ) -> Plan:
        input_text = "\n".join(_all_input_text(request, clarification, context)).lower()
        risk_level = (
            "L3" if any(marker in input_text for marker in _SENSITIVE_MARKERS) else "L1"
        )
        if context.snippets:
            sources = ", ".join(snippet.relative_path for snippet in context.snippets)
            summary = f"Plan grounded in repository evidence from: {sources}."
        else:
            summary = "Plan created with repository evidence unavailable."

        tasks = [
            PlanTask(
                description=description,
                required_tools=[ToolRequirement(tool_name=capability)],
            )
            for description, capability in _TASKS
        ]
        return Plan(
            summary=summary,
            tasks=tasks,
            risk_level=risk_level,
            budget_estimate=Measurement(status="not_available"),
            reasoner_id=_REASONER_ID,
        )
