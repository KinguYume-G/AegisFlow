"""Safe, provider-neutral tracing contracts and Langfuse adapter."""

from __future__ import annotations

from decimal import Decimal
from hashlib import sha256
import logging
import re
from typing import Any, Callable, Literal, Protocol
from uuid import UUID, uuid5

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from pydantic import (
    BaseModel,
    ConfigDict,
    NonNegativeFloat,
    StrictInt,
    field_validator,
    model_validator,
)

from aegisflow_core.settings import Settings

logger = logging.getLogger(__name__)

_EVENT_NAMESPACE = UUID("8d1b81f9-346e-5e56-88eb-88fe8bd1229f")
_MAX_PROMPT_CHARS = 100_000
_REDACTED = "[REDACTED]"

_PEM_PATTERN = re.compile(
    r"-----BEGIN [^-\r\n]+-----.*?-----END [^-\r\n]+-----",
    re.IGNORECASE | re.DOTALL,
)
_BEARER_PATTERN = re.compile(r"(?i)(\bbearer\s+)[^\s,;]+")
_KEY_TOKEN_PATTERN = re.compile(r"(?i)\b(?:sk|pk)-(?:lf-)?[a-z0-9_-]{8,}\b")
_URI_CREDENTIAL_PATTERN = re.compile(
    r"(?i)(\b[a-z][a-z0-9+.-]*://)([^\s/@:]+):([^\s/@]+)@"
)
_EMAIL_PATTERN = re.compile(
    r"(?i)\b[a-z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?"
    r"(?:\.[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)+\b"
)
_SECRET_ASSIGNMENT_PATTERN = re.compile(
    r"(?i)(\b(?:api[_-]?key|secret|client[_-]?secret|password|token)\b\s*[:=]\s*)"
    r"(?:\"[^\"]*\"|'[^']*'|[^\s,;]+)"
)


class TokenMeasurement(BaseModel):
    """One honest token measurement, including an explicit unavailable state."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    status: Literal["measured", "not_available"]
    value: StrictInt | None = None

    @model_validator(mode="after")
    def state_must_be_consistent(self) -> "TokenMeasurement":
        if self.status == "not_available" and self.value is not None:
            raise ValueError("not_available token measurement cannot contain a value")
        if self.status == "measured" and (self.value is None or self.value < 0):
            raise ValueError("measured token value must be a non-negative integer")
        return self


class TokenUsage(BaseModel):
    """Input, output, and total token measurements for one step."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    input_tokens: TokenMeasurement
    output_tokens: TokenMeasurement
    total_tokens: TokenMeasurement

    @model_validator(mode="after")
    def measurements_must_be_consistent(self) -> "TokenUsage":
        statuses = {
            self.input_tokens.status,
            self.output_tokens.status,
            self.total_tokens.status,
        }
        if len(statuses) != 1:
            raise ValueError("token measurements must share one availability state")
        if self.total_tokens.status == "measured":
            assert self.input_tokens.value is not None
            assert self.output_tokens.value is not None
            assert self.total_tokens.value is not None
            if self.total_tokens.value != (
                self.input_tokens.value + self.output_tokens.value
            ):
                raise ValueError("total tokens must equal input plus output tokens")
        return self


class CostUsage(BaseModel):
    """A finite monetary amount or an explicit unavailable state."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    amount: Decimal | None = None
    currency: str | None = None
    source: Literal["provider_reported", "estimated", "not_available"]

    @field_validator("amount")
    @classmethod
    def amount_must_be_finite_and_non_negative(
        cls, value: Decimal | None
    ) -> Decimal | None:
        if value is not None and (not value.is_finite() or value < 0):
            raise ValueError("cost amount must be finite and non-negative")
        return value

    @field_validator("currency")
    @classmethod
    def currency_must_be_iso_4217_shaped(cls, value: str | None) -> str | None:
        if value is not None and not re.fullmatch(r"[A-Z]{3}", value):
            raise ValueError("currency must be a three-letter uppercase code")
        return value

    @model_validator(mode="after")
    def state_must_be_consistent(self) -> "CostUsage":
        if self.source == "not_available":
            if self.amount is not None or self.currency is not None:
                raise ValueError("not_available cost cannot contain amount or currency")
        else:
            if self.amount is None or self.currency is None:
                raise ValueError("measured cost requires amount and currency")
        return self


class StepTraceRecord(BaseModel):
    """Redacted, correlated telemetry for one DeliveryPack agent step."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    tenant_id: UUID | None
    workflow_id: UUID | None
    workflow_version: StrictInt | None
    run_id: UUID
    step_id: UUID | None
    trace_id: UUID
    event_id: UUID
    agent: Literal["intake", "clarifier", "context", "planner", "executor", "reviewer"]
    prompt: str
    model: str
    token_usage: TokenUsage
    cost: CostUsage
    latency_ms: NonNegativeFloat

    @field_validator("workflow_version")
    @classmethod
    def integer_fields_must_be_non_negative(cls, value: int | None) -> int | None:
        if value is not None and value < 0:
            raise ValueError("integer telemetry fields must be non-negative")
        return value

    @field_validator("model")
    @classmethod
    def model_must_contain_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("model must contain text")
        return normalized


def unavailable_token_usage() -> TokenUsage:
    """Return token usage that truthfully states no measurement was available."""
    return TokenUsage(
        input_tokens=TokenMeasurement(status="not_available"),
        output_tokens=TokenMeasurement(status="not_available"),
        total_tokens=TokenMeasurement(status="not_available"),
    )


def unavailable_cost_usage() -> CostUsage:
    """Return cost usage that truthfully states no measurement was available."""
    return CostUsage(source="not_available")


def redact(value: str) -> str:
    """Bound and remove common credentials and personal identifiers from prompt text."""
    bounded = value[:_MAX_PROMPT_CHARS]
    bounded = _PEM_PATTERN.sub(_REDACTED, bounded)
    bounded = _BEARER_PATTERN.sub(r"\1[REDACTED]", bounded)
    bounded = _KEY_TOKEN_PATTERN.sub(_REDACTED, bounded)
    bounded = _URI_CREDENTIAL_PATTERN.sub(r"\1[REDACTED]@", bounded)
    bounded = _EMAIL_PATTERN.sub(_REDACTED, bounded)
    bounded = _SECRET_ASSIGNMENT_PATTERN.sub(r"\1[REDACTED]", bounded)
    if len(value) > _MAX_PROMPT_CHARS:
        bounded += "[TRUNCATED]"
    return bounded


def make_event_id(
    *, run_id: UUID, step_id: UUID | None, agent: str, trace_id: UUID
) -> UUID:
    """Derive stable AegisFlow metadata without claiming a provider observation ID."""
    step_key = str(step_id) if step_id is not None else agent
    return uuid5(_EVENT_NAMESPACE, f"{run_id}:{step_key}:{trace_id}")


def build_step_trace_record(
    *,
    tenant_id: UUID | None,
    workflow_id: UUID | None,
    workflow_version: int | None,
    run_id: UUID,
    step_id: UUID | None,
    trace_id: UUID,
    agent: Literal["intake", "clarifier", "context", "planner", "executor", "reviewer"],
    raw_prompt: str,
    model: str,
    token_usage: TokenUsage,
    cost: CostUsage,
    latency_ms: float,
) -> StepTraceRecord:
    """Redact untrusted prompt text before constructing the immutable trace record."""
    return StepTraceRecord(
        tenant_id=tenant_id,
        workflow_id=workflow_id,
        workflow_version=workflow_version,
        run_id=run_id,
        step_id=step_id,
        trace_id=trace_id,
        event_id=make_event_id(
            run_id=run_id, step_id=step_id, agent=agent, trace_id=trace_id
        ),
        agent=agent,
        prompt=redact(raw_prompt),
        model=model,
        token_usage=token_usage,
        cost=cost,
        latency_ms=latency_ms,
    )


class TraceRecorder(Protocol):
    """Port for best-effort step telemetry."""

    def record(self, step: StepTraceRecord) -> None:
        """Attempt to record one already-redacted step."""


class NoOpTraceRecorder:
    """Disabled tracing adapter."""

    def record(self, step: StepTraceRecord) -> None:
        del step


class InMemoryTraceRecorder:
    """Deterministic recorder for unit tests and local composition."""

    def __init__(self) -> None:
        self._records: list[StepTraceRecord] = []

    @property
    def records(self) -> tuple[StepTraceRecord, ...]:
        return tuple(record.model_copy(deep=True) for record in self._records)

    def record(self, step: StepTraceRecord) -> None:
        self._records.append(step.model_copy(deep=True))

    def records_for_tenant(self, tenant_id: UUID) -> tuple[StepTraceRecord, ...]:
        if not isinstance(tenant_id, UUID):
            raise ValueError("tenant_id is required")
        return tuple(
            record.model_copy(deep=True)
            for record in self._records
            if record.tenant_id == tenant_id
        )


class PostgresTraceRecorder:
    """Persist redacted trace measurements without storing prompt text."""

    _SEQUENCE = {
        "intake": 1,
        "clarifier": 2,
        "context": 3,
        "planner": 4,
        "executor": 6,
        "reviewer": 7,
    }

    def __init__(self, database_url: str) -> None:
        normalized = database_url.replace(
            "postgresql+asyncpg://", "postgresql://", 1
        )
        if not normalized.startswith(("postgresql://", "postgres://")):
            raise ValueError("trace database URL must be PostgreSQL")
        self._database_url = normalized

    def record(self, step: StepTraceRecord) -> None:
        if step.tenant_id is None or step.step_id is None:
            raise ValueError("PostgreSQL traces require tenant and step identity")
        sequence = self._SEQUENCE[step.agent]
        with psycopg.connect(self._database_url, row_factory=dict_row) as connection:
            with connection.transaction():
                stored_step = connection.execute(
                    """
                    INSERT INTO steps
                        (id, tenant_id, run_id, name, sequence, status, completed_at)
                    VALUES (%s, %s, %s, %s, %s, 'completed', now())
                    ON CONFLICT (run_id, sequence) DO UPDATE SET
                        status='completed', completed_at=COALESCE(
                            steps.completed_at, EXCLUDED.completed_at
                        )
                    RETURNING id
                    """,
                    (
                        step.step_id,
                        step.tenant_id,
                        step.run_id,
                        step.agent,
                        sequence,
                    ),
                ).fetchone()
                assert stored_step is not None
                connection.execute(
                    """
                    INSERT INTO run_traces
                        (tenant_id, run_id, step_id, trace_id, event_id, agent,
                         model, prompt_digest, token_usage, cost_usage, latency_ms)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (tenant_id, event_id) DO NOTHING
                    """,
                    (
                        step.tenant_id,
                        step.run_id,
                        stored_step["id"],
                        step.trace_id,
                        step.event_id,
                        step.agent,
                        step.model,
                        sha256(step.prompt.encode("utf-8")).hexdigest(),
                        Jsonb(step.token_usage.model_dump(mode="json")),
                        Jsonb(step.cost.model_dump(mode="json")),
                        step.latency_ms,
                    ),
                )


class _Observation(Protocol):
    def end(self) -> None: ...


class _LangfuseClient(Protocol):
    def create_trace_id(self, *, seed: str) -> str: ...

    def start_observation(self, **kwargs: Any) -> _Observation: ...


class LangfuseTraceRecorder:
    """One-attempt Langfuse adapter; telemetry failure never changes business results."""

    def __init__(self, client: _LangfuseClient) -> None:
        self._client = client

    def record(self, step: StepTraceRecord) -> None:
        try:
            trace_id = self._client.create_trace_id(seed=str(step.trace_id))
            usage_details: dict[str, int] | None = None
            if step.token_usage.total_tokens.status == "measured":
                assert step.token_usage.input_tokens.value is not None
                assert step.token_usage.output_tokens.value is not None
                assert step.token_usage.total_tokens.value is not None
                usage_details = {
                    "input": step.token_usage.input_tokens.value,
                    "output": step.token_usage.output_tokens.value,
                    "total": step.token_usage.total_tokens.value,
                }
            cost_details: dict[str, float] | None = None
            if step.cost.source != "not_available":
                assert step.cost.amount is not None
                cost_details = {"total": float(step.cost.amount)}

            metadata = {
                "tenant_id": str(step.tenant_id) if step.tenant_id else None,
                "workflow_id": str(step.workflow_id) if step.workflow_id else None,
                "workflow_version": step.workflow_version,
                "run_id": str(step.run_id),
                "step_id": str(step.step_id) if step.step_id else None,
                "trace_id": str(step.trace_id),
                "event_id": str(step.event_id),
                "agent": step.agent,
                "latency_ms": step.latency_ms,
                "token_status": step.token_usage.total_tokens.status,
                "cost_status": (
                    "not_available"
                    if step.cost.source == "not_available"
                    else "measured"
                ),
                "cost_source": step.cost.source,
                "cost_currency": step.cost.currency,
            }
            observation = self._client.start_observation(
                name=f"aegisflow.{step.agent}",
                as_type="generation",
                trace_context={"trace_id": trace_id},
                input=step.prompt,
                model=step.model,
                usage_details=usage_details,
                cost_details=cost_details,
                metadata=metadata,
            )
            observation.end()
        except Exception as exc:  # telemetry is deliberately best-effort
            logger.warning(
                "langfuse_trace_record_failed error_type=%s", type(exc).__name__
            )


LangfuseFactory = Callable[..., _LangfuseClient]


def build_trace_recorder(
    settings: Settings, *, client_factory: LangfuseFactory | None = None
) -> TraceRecorder:
    """Compose disabled or Langfuse tracing from all-or-none validated settings."""
    if settings.langfuse_base_url is None:
        return NoOpTraceRecorder()

    if client_factory is None:
        from langfuse import Langfuse

        client_factory = Langfuse

    assert settings.langfuse_public_key is not None
    assert settings.langfuse_secret_key is not None
    assert settings.langfuse_tracing_environment is not None
    client = client_factory(
        base_url=settings.langfuse_base_url,
        public_key=settings.langfuse_public_key,
        secret_key=settings.langfuse_secret_key,
        environment=settings.langfuse_tracing_environment,
    )
    return LangfuseTraceRecorder(client)
