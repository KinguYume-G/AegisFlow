"""Tenant-bound PostgreSQL clarification gateway for durable graph resumes."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from types import MappingProxyType
from uuid import UUID, uuid5

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from aegisflow_core.packs.delivery.clarifier.hitl import (
    ClarificationOutcome,
    ClarificationRunMismatchError,
    ClarificationStatus,
    DuplicateClarificationResponseError,
    UnknownClarificationRequestError,
)
from aegisflow_core.packs.delivery.contracts.clarification import (
    ClarificationQuestion,
)


_CLARIFICATION_NAMESPACE = UUID("fa791acf-bdd0-447f-917d-7a660eb82e4e")
_STEP_NAMESPACE = UUID("2dd2ba1e-11e1-4c03-9ea1-d20c0aac76b5")


class PostgresClarificationGateway:
    """Persist one clarification per tenant/run/step and its human receipt."""

    def __init__(self, database_url: str, *, tenant_id: UUID) -> None:
        if not isinstance(tenant_id, UUID):
            raise TypeError("tenant_id must be a UUID")
        self._database_url = _psycopg_url(database_url)
        self._tenant_id = tenant_id

    def request_clarification(
        self,
        run_id: UUID,
        step_key: str,
        questions: Sequence[ClarificationQuestion],
    ) -> UUID:
        normalized = _questions(questions)
        request_id = uuid5(
            _CLARIFICATION_NAMESPACE,
            f"{self._tenant_id}:{run_id}:{step_key}",
        )
        step_id = uuid5(
            _STEP_NAMESPACE,
            f"{self._tenant_id}:{run_id}:2:clarifier",
        )
        with psycopg.connect(self._database_url, row_factory=dict_row) as connection:
            with connection.transaction():
                _lock_run(connection, self._tenant_id, run_id)
                inserted = connection.execute(
                    """
                    INSERT INTO clarification_requests
                        (id, tenant_id, run_id, step_key, questions, status)
                    VALUES (%s, %s, %s, %s, %s, 'pending')
                    ON CONFLICT (tenant_id, run_id, step_key) DO NOTHING
                    RETURNING id
                    """,
                    (request_id, self._tenant_id, run_id, step_key, Jsonb(normalized)),
                ).fetchone()
                row = connection.execute(
                    """
                    SELECT id, questions FROM clarification_requests
                    WHERE tenant_id=%s AND run_id=%s AND step_key=%s
                    """,
                    (self._tenant_id, run_id, step_key),
                ).fetchone()
                if row is None:
                    raise RuntimeError("clarification request disappeared")
                if row["questions"] != normalized:
                    raise PermissionError(
                        "clarification replay did not match the original questions"
                    )
                connection.execute(
                    """
                    INSERT INTO steps (id, tenant_id, run_id, name, sequence, status)
                    VALUES (%s, %s, %s, 'clarifier', 2, 'running')
                    ON CONFLICT (run_id, sequence) DO UPDATE SET
                        status=CASE WHEN steps.status='completed'
                            THEN steps.status ELSE 'running' END
                    """,
                    (step_id, self._tenant_id, run_id),
                )
                connection.execute(
                    """
                    UPDATE runs SET status='waiting_clarification', updated_at=now()
                    WHERE tenant_id=%s AND id=%s
                      AND status NOT IN ('completed','failed','cancelled')
                    """,
                    (self._tenant_id, run_id),
                )
                if inserted is not None:
                    _append_event(
                        connection,
                        self._tenant_id,
                        run_id,
                        "clarification.requested",
                        "agent:clarifier",
                        {
                            "request_id": str(row["id"]),
                            "question_count": len(normalized),
                        },
                    )
                return row["id"]

    def submit_response(
        self,
        request_id: UUID,
        run_id: UUID,
        answers: Mapping[str, str],
        *,
        answered_by: str = "human",
    ) -> ClarificationOutcome:
        normalized_answers = _answers(answers)
        actor = answered_by.strip()
        if not actor or len(actor) > 512:
            raise ValueError("answered_by must contain bounded text")
        with psycopg.connect(self._database_url, row_factory=dict_row) as connection:
            with connection.transaction():
                _lock_run(connection, self._tenant_id, run_id)
                row = connection.execute(
                    """
                    SELECT id, run_id, step_key, questions, status, answers, answered_by
                    FROM clarification_requests
                    WHERE tenant_id=%s AND id=%s
                    FOR UPDATE
                    """,
                    (self._tenant_id, request_id),
                ).fetchone()
                if row is None:
                    raise UnknownClarificationRequestError(request_id)
                if row["run_id"] != run_id:
                    raise ClarificationRunMismatchError(
                        request_id,
                        expected_run_id=row["run_id"],
                        actual_run_id=run_id,
                    )
                if row["status"] != "pending":
                    raise DuplicateClarificationResponseError(request_id)
                expected_fields = {
                    str(question["field"]) for question in row["questions"]
                }
                if set(normalized_answers) != expected_fields:
                    raise ValueError("answers must match the requested fields exactly")
                connection.execute(
                    """
                    UPDATE clarification_requests
                    SET status='answered', answers=%s, answered_by=%s, answered_at=now()
                    WHERE tenant_id=%s AND id=%s AND status='pending'
                    """,
                    (Jsonb(normalized_answers), actor, self._tenant_id, request_id),
                )
                connection.execute(
                    """
                    UPDATE steps SET status='completed', completed_at=now()
                    WHERE tenant_id=%s AND run_id=%s AND sequence=2
                    """,
                    (self._tenant_id, run_id),
                )
                connection.execute(
                    """
                    UPDATE runs SET status='running', updated_at=now()
                    WHERE tenant_id=%s AND id=%s
                      AND status='waiting_clarification'
                    """,
                    (self._tenant_id, run_id),
                )
                _append_event(
                    connection,
                    self._tenant_id,
                    run_id,
                    "clarification.answered",
                    actor,
                    {"request_id": str(request_id)},
                )
        return ClarificationOutcome(
            request_id=request_id,
            run_id=run_id,
            step_key=row["step_key"],
            questions=tuple(
                ClarificationQuestion.model_validate(question)
                for question in row["questions"]
            ),
            status=ClarificationStatus.ANSWERED,
            answers=MappingProxyType(dict(normalized_answers)),
        )

    def get_status(self, request_id: UUID) -> ClarificationStatus:
        with psycopg.connect(self._database_url, row_factory=dict_row) as connection:
            row = connection.execute(
                """
                SELECT status FROM clarification_requests
                WHERE tenant_id=%s AND id=%s
                """,
                (self._tenant_id, request_id),
            ).fetchone()
        if row is None:
            raise UnknownClarificationRequestError(request_id)
        return ClarificationStatus(row["status"])


def _lock_run(connection: psycopg.Connection[dict[str, object]], tenant_id: UUID, run_id: UUID) -> None:
    row = connection.execute(
        "SELECT id FROM runs WHERE tenant_id=%s AND id=%s FOR UPDATE",
        (tenant_id, run_id),
    ).fetchone()
    if row is None:
        raise KeyError(run_id)


def _append_event(
    connection: psycopg.Connection[dict[str, object]],
    tenant_id: UUID,
    run_id: UUID,
    event_type: str,
    actor: str,
    payload: dict[str, object],
) -> None:
    sequence = connection.execute(
        """
        SELECT COALESCE(MAX(sequence), 0) + 1 AS next_sequence
        FROM run_events WHERE tenant_id=%s AND run_id=%s
        """,
        (tenant_id, run_id),
    ).fetchone()
    assert sequence is not None
    connection.execute(
        """
        INSERT INTO run_events
            (tenant_id, run_id, sequence, event_type, actor, payload)
        VALUES (%s, %s, %s, %s, %s, %s)
        """,
        (
            tenant_id,
            run_id,
            sequence["next_sequence"],
            event_type,
            actor,
            Jsonb(payload),
        ),
    )


def _questions(
    questions: Sequence[ClarificationQuestion],
) -> list[dict[str, object]]:
    copied = tuple(questions)
    if not copied or len(copied) > 50:
        raise ValueError("questions must contain 1 to 50 items")
    if not all(isinstance(question, ClarificationQuestion) for question in copied):
        raise TypeError("questions must contain ClarificationQuestion values")
    fields = [question.field for question in copied]
    if len(fields) != len(set(fields)):
        raise ValueError("clarification question fields must be unique")
    return [question.model_dump(mode="json") for question in copied]


def _answers(answers: Mapping[str, str]) -> dict[str, str]:
    if not isinstance(answers, Mapping):
        raise TypeError("answers must be a mapping")
    copied = dict(answers)
    if not copied or len(copied) > 50:
        raise ValueError("answers must contain 1 to 50 items")
    if not all(isinstance(key, str) and isinstance(value, str) for key, value in copied.items()):
        raise TypeError("answers must contain string keys and values")
    if any(not value.strip() or len(value) > 8_192 for value in copied.values()):
        raise ValueError("answer values must contain bounded text")
    return copied


def _psycopg_url(database_url: str) -> str:
    normalized = database_url.replace("postgresql+asyncpg://", "postgresql://", 1)
    if not normalized.startswith(("postgresql://", "postgres://")):
        raise ValueError("clarification database URL must be PostgreSQL")
    return normalized
