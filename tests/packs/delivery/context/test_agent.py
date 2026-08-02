"""Tests for Context Agent dependency injection."""

from datetime import datetime, timezone
import inspect

import pytest

from aegisflow_core.packs.delivery.context.agent import ContextAgent
from aegisflow_core.packs.delivery.contracts.context_package import ContextPackage
from aegisflow_core.packs.delivery.contracts.normalized_request import NormalizedRequest


def _request() -> NormalizedRequest:
    return NormalizedRequest(
        source_type="bug",
        source_ref="BUG-2",
        title="Missing evidence",
        body="Find repository context.",
        idempotency_key="d" * 64,
        received_at=datetime(2026, 8, 2, tzinfo=timezone.utc),
    )


class SpyRetriever:
    def __init__(self) -> None:
        self.calls = 0
        self.result = ContextPackage(
            snippets=[],
            unsupported_notes=["No evidence."],
            scanned_file_count=0,
            skipped_file_count=0,
            security_skip_count=0,
        )

    def retrieve(self, request: NormalizedRequest) -> ContextPackage:
        self.calls += 1
        return self.result


class ExplodingRetriever:
    def retrieve(self, request: NormalizedRequest) -> ContextPackage:
        raise RuntimeError("retrieval failed")


def test_context_agent_requires_retriever() -> None:
    assert tuple(inspect.signature(ContextAgent).parameters) == ("retriever",)
    with pytest.raises(TypeError):
        ContextAgent()  # type: ignore[call-arg]

    retriever = SpyRetriever()
    assert ContextAgent(retriever).gather(_request()) == retriever.result
    assert retriever.calls == 1

    with pytest.raises(RuntimeError, match="retrieval failed"):
        ContextAgent(ExplodingRetriever()).gather(_request())
