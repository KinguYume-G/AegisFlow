"""Framework-independent Context Agent."""

from aegisflow_core.packs.delivery.context.ports import ContextRetriever
from aegisflow_core.packs.delivery.contracts.context_package import ContextPackage
from aegisflow_core.packs.delivery.contracts.normalized_request import NormalizedRequest


class ContextAgent:
    """Gather cited context through an explicitly injected retriever."""

    def __init__(self, retriever: ContextRetriever) -> None:
        self._retriever = retriever

    def gather(self, request: NormalizedRequest) -> ContextPackage:
        """Delegate retrieval and propagate any adapter failure."""
        return self._retriever.retrieve(request)
