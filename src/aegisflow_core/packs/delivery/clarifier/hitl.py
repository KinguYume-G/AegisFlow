"""Replay-safe in-memory clarification HITL gateway for Gate 1A demos."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from threading import RLock
from types import MappingProxyType
from typing import Protocol, cast
from uuid import UUID

from aegisflow_core.packs.delivery.contracts.clarification import ClarificationQuestion
from aegisflow_core.packs.delivery.contracts.determinism import IdGenerator


class ClarificationStatus(StrEnum):
    """Lifecycle states owned by the in-memory clarification gateway."""

    PENDING = "pending"
    ANSWERED = "answered"


class UnknownClarificationRequestError(KeyError):
    """Raised when a request identifier is not present in this process."""

    def __init__(self, request_id: UUID) -> None:
        self.request_id = request_id
        super().__init__(f"unknown clarification request: {request_id}")


class ClarificationRunMismatchError(ValueError):
    """Raised when a response attempts to cross a run boundary."""

    def __init__(
        self,
        request_id: UUID,
        expected_run_id: UUID,
        actual_run_id: UUID,
    ) -> None:
        self.request_id = request_id
        self.expected_run_id = expected_run_id
        self.actual_run_id = actual_run_id
        super().__init__(f"clarification request {request_id} belongs to another run")


class DuplicateClarificationResponseError(RuntimeError):
    """Raised when an answered request receives another response."""

    def __init__(self, request_id: UUID) -> None:
        self.request_id = request_id
        super().__init__(f"clarification request already answered: {request_id}")


class ClarificationRequestIdCollisionError(RuntimeError):
    """Raised if an injected generator repeats an active request identifier."""

    def __init__(self, request_id: UUID) -> None:
        self.request_id = request_id
        super().__init__(f"clarification request identifier collision: {request_id}")


class ClarificationGateway(Protocol):
    def request_clarification(
        self,
        run_id: UUID,
        step_key: str,
        questions: Sequence[ClarificationQuestion],
    ) -> UUID: ...

    def submit_response(
        self,
        request_id: UUID,
        run_id: UUID,
        answers: Mapping[str, str],
        *,
        answered_by: str = "human",
    ) -> "ClarificationOutcome": ...


@dataclass(frozen=True, slots=True)
class ClarificationOutcome:
    """Immutable snapshot returned after a successful response transition."""

    request_id: UUID
    run_id: UUID
    step_key: str
    questions: tuple[ClarificationQuestion, ...]
    status: ClarificationStatus
    answers: Mapping[str, str]


@dataclass(slots=True)
class _ClarificationRecord:
    request_id: UUID
    run_id: UUID
    step_key: str
    questions: tuple[ClarificationQuestion, ...]
    status: ClarificationStatus = ClarificationStatus.PENDING
    answers: dict[str, str] | None = None


class InMemoryClarificationGateway:
    """Store replay-safe clarification requests within one Python process."""

    def __init__(self, id_generator: IdGenerator) -> None:
        self._id_generator = id_generator
        self._request_ids_by_key: dict[tuple[UUID, str], UUID] = {}
        self._records_by_id: dict[UUID, _ClarificationRecord] = {}
        self._lock = RLock()

    @property
    def request_count(self) -> int:
        """Return the current bounded-process record count for verification."""
        with self._lock:
            return len(self._records_by_id)

    def request_clarification(
        self,
        run_id: UUID,
        step_key: str,
        questions: Sequence[ClarificationQuestion],
    ) -> UUID:
        """Create once per run/step or return the original request identifier."""
        _validate_run_id(run_id)
        _validate_step_key(step_key)
        idempotency_key = (run_id, step_key)

        with self._lock:
            existing = self._request_ids_by_key.get(idempotency_key)
            if existing is not None:
                return existing

            stored_questions = _copy_questions(questions)
            request_id = self._id_generator.new_id()
            if not isinstance(request_id, UUID):
                raise TypeError("id_generator must return UUID values")
            if request_id in self._records_by_id:
                raise ClarificationRequestIdCollisionError(request_id)

            record = _ClarificationRecord(
                request_id=request_id,
                run_id=run_id,
                step_key=step_key,
                questions=stored_questions,
            )
            self._records_by_id[request_id] = record
            self._request_ids_by_key[idempotency_key] = request_id
            return request_id

    def submit_response(
        self,
        request_id: UUID,
        run_id: UUID,
        answers: Mapping[str, str],
        *,
        answered_by: str = "human",
    ) -> ClarificationOutcome:
        """Atomically answer one pending request after enforcing run isolation."""
        del answered_by
        _validate_run_id(request_id, field="request_id")
        _validate_run_id(run_id)
        with self._lock:
            record = self._records_by_id.get(request_id)
            if record is None:
                raise UnknownClarificationRequestError(request_id)
            if record.run_id != run_id:
                raise ClarificationRunMismatchError(
                    request_id,
                    expected_run_id=record.run_id,
                    actual_run_id=run_id,
                )
            if record.status is ClarificationStatus.ANSWERED:
                raise DuplicateClarificationResponseError(request_id)

            stored_answers = _copy_answers(answers)
            record.answers = stored_answers
            record.status = ClarificationStatus.ANSWERED
            return _snapshot(record)

    def get_status(self, request_id: UUID) -> ClarificationStatus:
        """Return current status or reject an unknown request identifier."""
        _validate_run_id(request_id, field="request_id")
        with self._lock:
            record = self._records_by_id.get(request_id)
            if record is None:
                raise UnknownClarificationRequestError(request_id)
            return record.status


def _validate_run_id(value: UUID, *, field: str = "run_id") -> None:
    if not isinstance(value, UUID):
        raise TypeError(f"{field} must be a UUID")


def _validate_step_key(value: str) -> None:
    if not isinstance(value, str):
        raise TypeError("step_key must be a string")
    if not value.strip() or len(value) > 128:
        raise ValueError("step_key must contain 1 to 128 characters")


def _copy_questions(
    questions: Sequence[ClarificationQuestion],
) -> tuple[ClarificationQuestion, ...]:
    copied = tuple(questions)
    if not copied or len(copied) > 50:
        raise ValueError("questions must contain 1 to 50 items")
    if not all(isinstance(question, ClarificationQuestion) for question in copied):
        raise TypeError("questions must contain ClarificationQuestion values")
    fields = [question.field for question in copied]
    if len(fields) != len(set(fields)):
        raise ValueError("clarification question fields must be unique")
    return copied


def _copy_answers(answers: Mapping[str, str]) -> dict[str, str]:
    if not isinstance(answers, Mapping):
        raise TypeError("answers must be a mapping")
    copied = dict(answers)
    if len(copied) > 50:
        raise ValueError("answers must not exceed 50 items")
    if not all(isinstance(key, str) for key in copied):
        raise TypeError("answer keys must be strings")
    if not all(isinstance(value, str) for value in copied.values()):
        raise TypeError("answer values must be strings")
    if any(len(value) > 8_192 for value in copied.values()):
        raise ValueError("answer values must not exceed 8192 characters")
    return copied


def _snapshot(record: _ClarificationRecord) -> ClarificationOutcome:
    answers = cast(dict[str, str], record.answers)
    return ClarificationOutcome(
        request_id=record.request_id,
        run_id=record.run_id,
        step_key=record.step_key,
        questions=record.questions,
        status=record.status,
        answers=MappingProxyType(dict(answers)),
    )
