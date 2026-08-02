"""Tests for Clarifier Agent orchestration and answer resolution."""

from datetime import datetime, timezone
import inspect

import pytest
from pydantic import ValidationError

from aegisflow_core.packs.delivery.clarifier.agent import (
    ClarifierAgent,
    IncompleteClarificationAnswersError,
)
from aegisflow_core.packs.delivery.contracts.clarification import (
    Clarification,
    ClarificationQuestion,
)
from aegisflow_core.packs.delivery.contracts.normalized_request import NormalizedRequest


def _request() -> NormalizedRequest:
    return NormalizedRequest(
        source_type="bug",
        source_ref="BUG-1",
        title="Export fails",
        body="The export requirements are incomplete.",
        idempotency_key="b" * 64,
        received_at=datetime(2026, 8, 2, tzinfo=timezone.utc),
    )


def _pending() -> Clarification:
    return Clarification(
        questions=[
            ClarificationQuestion(field="time_range", question="What range?"),
            ClarificationQuestion(field="authorized_roles", question="Which roles?"),
        ],
        is_sufficient=False,
        reasoner_id="spy-reasoner",
    )


class SpyReasoner:
    def __init__(self, result: Clarification | None = None) -> None:
        self.result = result or _pending()
        self.calls = 0

    def identify_gaps(self, request: NormalizedRequest) -> Clarification:
        self.calls += 1
        return self.result


class ExplodingReasoner:
    def identify_gaps(self, request: NormalizedRequest) -> Clarification:
        raise RuntimeError("reasoner unavailable")


def test_agent_requires_reasoner_and_propagates_error() -> None:
    assert tuple(inspect.signature(ClarifierAgent).parameters) == ("reasoner",)
    with pytest.raises(TypeError):
        ClarifierAgent()  # type: ignore[call-arg]
    with pytest.raises(RuntimeError, match="reasoner unavailable"):
        ClarifierAgent(ExplodingReasoner()).clarify(_request())


def test_clarify_delegates_once() -> None:
    reasoner = SpyReasoner()

    result = ClarifierAgent(reasoner).clarify(_request())

    assert result == reasoner.result
    assert reasoner.calls == 1


def test_resolve_complete_answers() -> None:
    reasoner = SpyReasoner()
    agent = ClarifierAgent(reasoner)
    pending = agent.clarify(_request())
    answers = {
        "time_range": "Default 7 days, maximum 90 days.",
        "authorized_roles": "Only administrators.",
    }

    resolved = agent.resolve(pending, answers)

    assert resolved.questions == []
    assert resolved.is_sufficient is True
    assert resolved.answers == answers
    assert resolved.reasoner_id == pending.reasoner_id


@pytest.mark.parametrize(
    ("answers", "missing"),
    [
        ({}, ("authorized_roles", "time_range")),
        ({"time_range": "7 days"}, ("authorized_roles",)),
        ({"time_range": "  ", "authorized_roles": "admin"}, ("time_range",)),
    ],
)
def test_resolve_missing_or_blank_answers(
    answers: dict[str, str], missing: tuple[str, ...]
) -> None:
    with pytest.raises(IncompleteClarificationAnswersError) as caught:
        ClarifierAgent(SpyReasoner()).resolve(_pending(), answers)

    assert caught.value.missing_fields == missing
    assert str(caught.value) == f"missing clarification answers: {', '.join(missing)}"


def test_resolve_preserves_bounded_extras() -> None:
    answers = {
        "time_range": "7 days",
        "authorized_roles": "admin",
        "supporting_note": "Reviewed by security.",
    }

    resolved = ClarifierAgent(SpyReasoner()).resolve(_pending(), answers)

    assert resolved.answers == answers


def test_resolve_enforces_answer_schema_limits() -> None:
    answers = {
        "time_range": "7 days",
        "authorized_roles": "admin",
        "supporting_note": "x" * 8_193,
    }

    with pytest.raises(ValidationError):
        ClarifierAgent(SpyReasoner()).resolve(_pending(), answers)


def test_resolve_never_reinvokes_reasoner() -> None:
    reasoner = SpyReasoner()
    agent = ClarifierAgent(reasoner)
    pending = agent.clarify(_request())

    agent.resolve(
        pending,
        {"time_range": "7 days", "authorized_roles": "admin"},
    )

    assert reasoner.calls == 1
