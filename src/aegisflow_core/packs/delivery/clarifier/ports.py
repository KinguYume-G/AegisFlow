"""Ports consumed by the Clarifier Agent."""

from typing import Protocol

from aegisflow_core.packs.delivery.contracts.clarification import Clarification
from aegisflow_core.packs.delivery.contracts.normalized_request import NormalizedRequest


class ClarificationReasoner(Protocol):
    """Identify missing information in a normalized request."""

    def identify_gaps(self, request: NormalizedRequest) -> Clarification:
        """Return a structured and internally consistent clarification state."""
