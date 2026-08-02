"""Ports consumed by the Planner Agent."""

from typing import Protocol

from aegisflow_core.packs.delivery.contracts.clarification import Clarification
from aegisflow_core.packs.delivery.contracts.context_package import ContextPackage
from aegisflow_core.packs.delivery.contracts.normalized_request import NormalizedRequest
from aegisflow_core.packs.delivery.contracts.plan import Plan


class PlanReasoner(Protocol):
    """Create a structured plan from validated demand-to-plan inputs."""

    def create_plan(
        self,
        request: NormalizedRequest,
        clarification: Clarification,
        context: ContextPackage,
    ) -> Plan:
        """Return a complete plan without performing external side effects."""
