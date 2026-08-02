"""Framework-independent Clarifier Agent."""

from collections.abc import Mapping

from aegisflow_core.packs.delivery.clarifier.ports import ClarificationReasoner
from aegisflow_core.packs.delivery.contracts.clarification import Clarification
from aegisflow_core.packs.delivery.contracts.normalized_request import NormalizedRequest


class IncompleteClarificationAnswersError(ValueError):
    """Raised when one or more requested fields have no meaningful answer."""

    def __init__(self, missing_fields: list[str]) -> None:
        self.missing_fields = tuple(sorted(missing_fields))
        super().__init__(
            f"missing clarification answers: {', '.join(self.missing_fields)}"
        )


class ClarifierAgent:
    """Delegate gap identification and deterministically resolve human answers."""

    def __init__(self, reasoner: ClarificationReasoner) -> None:
        self._reasoner = reasoner

    def clarify(self, request: NormalizedRequest) -> Clarification:
        """Identify missing information using the explicitly injected reasoner."""
        return self._reasoner.identify_gaps(request)

    def resolve(
        self,
        clarification: Clarification,
        answers: Mapping[str, str],
    ) -> Clarification:
        """Validate required answers without invoking the reasoner again."""
        missing = [
            question.field
            for question in clarification.questions
            if not isinstance(answers.get(question.field), str)
            or not answers[question.field].strip()
        ]
        if missing:
            raise IncompleteClarificationAnswersError(missing)

        return Clarification(
            questions=[],
            is_sufficient=True,
            reasoner_id=clarification.reasoner_id,
            answers=dict(answers),
        )
