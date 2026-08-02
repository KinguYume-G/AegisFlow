"""Ports consumed by the Context Agent."""

from typing import Protocol

from aegisflow_core.packs.delivery.contracts.context_package import ContextPackage
from aegisflow_core.packs.delivery.contracts.normalized_request import NormalizedRequest


class ContextRetriever(Protocol):
    """Retrieve cited evidence for a normalized request."""

    def retrieve(self, request: NormalizedRequest) -> ContextPackage:
        """Return bounded evidence without inventing unsupported snippets."""
