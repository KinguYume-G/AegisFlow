"""Persistent fencing records for webhook and tool-call idempotency."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column

from aegisflow_core.control_plane.domain.base import Base, CreatedAtMixin, UUIDPrimaryKeyMixin


class IdempotencyRecord(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "idempotency_records"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "scope", "idempotency_key",
            name="uq_idempotency_records_tenant_scope_key",
        ),
        UniqueConstraint("claim_token", name="uq_idempotency_records_claim_token"),
        CheckConstraint(
            "scope IN ('webhook_delivery','tool_call','compensation')", name="scope"
        ),
        CheckConstraint(
            "status IN ('executing','succeeded','failed_retryable','failed_final','compensated')",
            name="status",
        ),
        CheckConstraint("attempt >= 1", name="attempt"),
    )

    tenant_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False
    )
    scope: Mapped[str] = mapped_column(Text, nullable=False)
    idempotency_key: Mapped[str] = mapped_column(Text, nullable=False)
    arguments_hash: Mapped[str] = mapped_column(Text, nullable=False)
    run_id: Mapped[UUID | None] = mapped_column(PostgreSQLUUID(as_uuid=True))
    step_id: Mapped[UUID | None] = mapped_column(PostgreSQLUUID(as_uuid=True))
    tool_name: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    claim_token: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    attempt: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    lease_expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    result_reference: Mapped[str | None] = mapped_column(Text)
    failure_reason: Mapped[str | None] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
