"""Framework-independent Planner Agent."""

from aegisflow_core.packs.delivery.contracts.clarification import Clarification
from aegisflow_core.packs.delivery.contracts.context_package import ContextPackage
from aegisflow_core.packs.delivery.contracts.normalized_request import NormalizedRequest
from aegisflow_core.packs.delivery.contracts.plan import Plan
from aegisflow_core.packs.delivery.planner.ports import PlanReasoner


class InsufficientClarificationError(ValueError):
    """Raised when planning is attempted before the Clarifier gate passes."""


class PlannerAgent:
    """Enforce the Clarifier gate before delegating to an injected reasoner."""

    def __init__(self, reasoner: PlanReasoner) -> None:
        self._reasoner = reasoner

    def plan(
        self,
        request: NormalizedRequest,
        clarification: Clarification,
        context: ContextPackage,
    ) -> Plan:
        """Create a plan only from a sufficient clarification state."""
        if not clarification.is_sufficient:
            raise InsufficientClarificationError(
                "planner requires a sufficient clarification"
            )
        return self._reasoner.create_plan(request, clarification, context)
