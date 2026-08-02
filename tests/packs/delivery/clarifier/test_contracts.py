"""Schema tests for the AF-105 clarification contract."""

import pytest
from pydantic import ValidationError

from aegisflow_core.packs.delivery.contracts.clarification import (
    Clarification,
    ClarificationQuestion,
)


def _question(field: str = "authorized_roles") -> ClarificationQuestion:
    return ClarificationQuestion(field=field, question="Which roles are authorized?")


@pytest.mark.parametrize(
    "field",
    ["AuthorizedRoles", "authorized-roles", "_authorized_roles", "authorized_roles_", "a" * 65],
)
def test_question_validates_field_and_length(field: str) -> None:
    with pytest.raises(ValidationError):
        ClarificationQuestion(field=field, question="Valid question?")

    assert ClarificationQuestion(field="a", question="q").schema_version == 1
    assert ClarificationQuestion(field="a" * 64, question="q" * 1_000)
    with pytest.raises(ValidationError):
        ClarificationQuestion(field="valid_field", question="")
    with pytest.raises(ValidationError):
        ClarificationQuestion(field="valid_field", question="   ")
    with pytest.raises(ValidationError):
        ClarificationQuestion(field="valid_field", question="q" * 1_001)


def test_clarification_rejects_duplicate_fields() -> None:
    with pytest.raises(ValidationError, match="unique"):
        Clarification(
            questions=[_question(), _question()],
            is_sufficient=False,
            reasoner_id="test-reasoner",
        )


@pytest.mark.parametrize(
    "values",
    [
        {"questions": [_question()], "is_sufficient": True, "answers": None},
        {"questions": [_question()], "is_sufficient": False, "answers": {}},
        {"questions": [], "is_sufficient": False, "answers": None},
        {"questions": [], "is_sufficient": False, "answers": {"field": "answer"}},
    ],
)
def test_clarification_state_invariants(values: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        Clarification(reasoner_id="test-reasoner", **values)


def test_answers_limits() -> None:
    answers = {f"field_{index}": "x" * 8_192 for index in range(50)}
    clarification = Clarification(
        questions=[],
        is_sufficient=True,
        reasoner_id="test-reasoner",
        answers=answers,
    )

    assert clarification.answers == answers
    with pytest.raises(ValidationError):
        Clarification(
            questions=[],
            is_sufficient=True,
            reasoner_id="test-reasoner",
            answers={**answers, "overflow": "value"},
        )
    with pytest.raises(ValidationError):
        Clarification(
            questions=[],
            is_sufficient=True,
            reasoner_id="test-reasoner",
            answers={"field": "x" * 8_193},
        )


def test_contracts_forbid_unknown_fields_and_blank_reasoner() -> None:
    with pytest.raises(ValidationError):
        ClarificationQuestion(field="valid_field", question="Valid?", extra="no")
    with pytest.raises(ValidationError):
        Clarification(questions=[], is_sufficient=True, reasoner_id="   ")
