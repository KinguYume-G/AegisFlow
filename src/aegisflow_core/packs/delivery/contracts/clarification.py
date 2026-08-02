"""Version 1 clarification schemas for DeliveryPack."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator, model_validator


QuestionField = Annotated[
    str,
    StringConstraints(
        min_length=1,
        max_length=64,
        pattern=r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$",
    ),
]
QuestionText = Annotated[str, StringConstraints(min_length=1, max_length=1_000)]
AnswerText = Annotated[str, StringConstraints(max_length=8_192)]


class ClarificationQuestion(BaseModel):
    """One stable field/question pair requiring a human answer."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1] = 1
    field: QuestionField
    question: QuestionText

    @field_validator("question")
    @classmethod
    def question_must_contain_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("question must contain non-whitespace text")
        return value


class Clarification(BaseModel):
    """Validated clarification state before or after human resolution."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1] = 1
    questions: list[ClarificationQuestion] = Field(max_length=50)
    is_sufficient: bool
    reasoner_id: str
    answers: dict[str, AnswerText] | None = Field(default=None, max_length=50)

    @field_validator("reasoner_id")
    @classmethod
    def reasoner_id_must_contain_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("reasoner_id must contain non-whitespace text")
        return value

    @model_validator(mode="after")
    def validate_state(self) -> "Clarification":
        fields = [question.field for question in self.questions]
        if len(fields) != len(set(fields)):
            raise ValueError("clarification question fields must be unique")

        if self.questions:
            if self.is_sufficient:
                raise ValueError("clarification with questions cannot be sufficient")
            if self.answers is not None:
                raise ValueError("pending clarification cannot contain answers")
        elif not self.is_sufficient:
            raise ValueError("clarification without questions must be sufficient")
        return self
