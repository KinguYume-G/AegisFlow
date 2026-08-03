"""Shared tenant-scoped model circuit state."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column

from aegisflow_core.control_plane.domain.base import Base, CreatedAtMixin, UUIDPrimaryKeyMixin


class ModelCircuitState(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "model_circuit_states"
    __table_args__ = (
        UniqueConstraint("tenant_id", "route", name="uq_model_circuit_states_tenant_route"),
        CheckConstraint("status IN ('closed','open','half_open')", name="status"),
        CheckConstraint("failure_count >= 0", name="failure_count"),
    )

    tenant_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="RESTRICT"),
        nullable=False,
    )
    route: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="closed")
    failure_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    open_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    probe_token: Mapped[UUID | None] = mapped_column(PostgreSQLUUID(as_uuid=True))
    probe_lease_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
