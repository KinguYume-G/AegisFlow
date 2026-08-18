"""Durable Run request, human interaction, evidence, and evaluation facts."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    Numeric,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column

from aegisflow_core.control_plane.domain.base import (
    Base,
    CreatedAtMixin,
    UUIDPrimaryKeyMixin,
)


class RunRequest(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """Immutable, idempotent input that caused one Run."""

    __tablename__ = "run_requests"
    __table_args__ = (
        CheckConstraint("source_type IN ('prd','issue','bug')", name="source_type"),
        CheckConstraint("length(title) BETWEEN 1 AND 200", name="title_bounded"),
        CheckConstraint("length(body) BETWEEN 20 AND 50000", name="body_bounded"),
        CheckConstraint("input_hash ~ '^[0-9a-f]{64}$'", name="input_hash"),
        CheckConstraint("base_sha ~ '^[0-9a-f]{40}$'", name="base_sha"),
        ForeignKeyConstraint(
            ["tenant_id", "run_id"],
            ["runs.tenant_id", "runs.id"],
            name="fk_run_requests_tenant_run",
            ondelete="RESTRICT",
        ),
        UniqueConstraint("tenant_id", "run_id", name="uq_run_requests_tenant_run"),
        UniqueConstraint(
            "tenant_id", "idempotency_key", name="uq_run_requests_tenant_idempotency"
        ),
    )

    tenant_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False
    )
    run_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    source_type: Mapped[str] = mapped_column(Text, nullable=False)
    source_ref: Mapped[str | None] = mapped_column(Text, nullable=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    repository_owner: Mapped[str] = mapped_column(Text, nullable=False)
    repository_name: Mapped[str] = mapped_column(Text, nullable=False)
    base_ref: Mapped[str] = mapped_column(Text, nullable=False)
    base_sha: Mapped[str] = mapped_column(Text, nullable=False)
    requested_by: Mapped[str] = mapped_column(Text, nullable=False)
    idempotency_key: Mapped[str] = mapped_column(Text, nullable=False)
    input_hash: Mapped[str] = mapped_column(Text, nullable=False)
    trace_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    temporal_workflow_id: Mapped[str] = mapped_column(Text, nullable=False)


class ClarificationRequest(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """Durable clarification request reconstructed independently of the Worker."""

    __tablename__ = "clarification_requests"
    __table_args__ = (
        CheckConstraint("status IN ('pending','answered')", name="status"),
        ForeignKeyConstraint(
            ["tenant_id", "run_id"],
            ["runs.tenant_id", "runs.id"],
            name="fk_clarification_requests_tenant_run",
            ondelete="RESTRICT",
        ),
        UniqueConstraint(
            "tenant_id", "run_id", "step_key", name="uq_clarification_requests_run_step"
        ),
    )

    tenant_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False
    )
    run_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    step_key: Mapped[str] = mapped_column(Text, nullable=False)
    questions: Mapped[list[dict[str, str]]] = mapped_column(JSONB, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    answers: Mapped[dict[str, str] | None] = mapped_column(JSONB, nullable=True)
    answered_by: Mapped[str | None] = mapped_column(Text, nullable=True)
    answered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class RunEvent(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """Append-only event used for polling and user-visible activity."""

    __tablename__ = "run_events"
    __table_args__ = (
        CheckConstraint("sequence > 0", name="sequence_positive"),
        ForeignKeyConstraint(
            ["tenant_id", "run_id"],
            ["runs.tenant_id", "runs.id"],
            name="fk_run_events_tenant_run",
            ondelete="RESTRICT",
        ),
        UniqueConstraint("tenant_id", "run_id", "sequence", name="uq_run_events_sequence"),
    )

    tenant_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False
    )
    run_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    event_type: Mapped[str] = mapped_column(Text, nullable=False)
    actor: Mapped[str] = mapped_column(Text, nullable=False)
    payload: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)


class RunTrace(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """Append-only redacted step trace and model measurement."""

    __tablename__ = "run_traces"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "run_id"],
            ["runs.tenant_id", "runs.id"],
            name="fk_run_traces_tenant_run",
            ondelete="RESTRICT",
        ),
        UniqueConstraint("tenant_id", "event_id", name="uq_run_traces_event"),
    )

    tenant_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False
    )
    run_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    step_id: Mapped[UUID | None] = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=True)
    trace_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    event_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    agent: Mapped[str] = mapped_column(Text, nullable=False)
    model: Mapped[str] = mapped_column(Text, nullable=False)
    prompt_digest: Mapped[str] = mapped_column(Text, nullable=False)
    token_usage: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    cost_usage: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    latency_ms: Mapped[float] = mapped_column(Float, nullable=False)


class RunArtifact(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """Append-only bounded evidence or terminal result artifact."""

    __tablename__ = "run_artifacts"
    __table_args__ = (
        CheckConstraint(
            "kind IN ('context','plan','sandbox','diff','draft_pr_candidate','failure')",
            name="kind",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "run_id"],
            ["runs.tenant_id", "runs.id"],
            name="fk_run_artifacts_tenant_run",
            ondelete="RESTRICT",
        ),
        UniqueConstraint("tenant_id", "run_id", "kind", name="uq_run_artifacts_kind"),
    )

    tenant_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False
    )
    run_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    kind: Mapped[str] = mapped_column(Text, nullable=False)
    content_digest: Mapped[str] = mapped_column(Text, nullable=False)
    payload: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)


class RunEvaluation(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """Immutable terminal quality and efficiency summary."""

    __tablename__ = "run_evaluations"
    __table_args__ = (
        CheckConstraint("outcome IN ('completed','failed','cancelled')", name="outcome"),
        CheckConstraint("tool_success_rate BETWEEN 0 AND 1", name="tool_success_rate"),
        ForeignKeyConstraint(
            ["tenant_id", "run_id"],
            ["runs.tenant_id", "runs.id"],
            name="fk_run_evaluations_tenant_run",
            ondelete="RESTRICT",
        ),
        UniqueConstraint("tenant_id", "run_id", name="uq_run_evaluations_tenant_run"),
    )

    tenant_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False
    )
    run_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    outcome: Mapped[str] = mapped_column(Text, nullable=False)
    task_success: Mapped[bool] = mapped_column(Boolean, nullable=False)
    tool_success_rate: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    total_steps: Mapped[int] = mapped_column(Integer, nullable=False)
    completed_steps: Mapped[int] = mapped_column(Integer, nullable=False)
    input_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    output_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cost_usd: Mapped[Decimal | None] = mapped_column(Numeric(12, 6), nullable=True)
    detail: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
