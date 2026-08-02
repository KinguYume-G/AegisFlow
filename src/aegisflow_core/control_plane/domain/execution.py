"""Run and step persistence models for durable business facts."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column

from aegisflow_core.control_plane.domain.base import (
    Base,
    CreatedAtMixin,
    UUIDPrimaryKeyMixin,
)


class Run(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """Durable projection of a workflow run."""

    __tablename__ = "runs"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'running', 'waiting_clarification', "
            "'waiting_approval', 'completed', 'failed', 'cancelled')",
            name="status",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "workflow_id", "workflow_version"],
            ["workflows.tenant_id", "workflows.id", "workflows.version"],
            name="fk_runs_tenant_workflow_version",
            ondelete="RESTRICT",
        ),
        UniqueConstraint("tenant_id", "id", name="uq_runs_tenant_id"),
    )

    tenant_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="RESTRICT"),
        nullable=False,
    )
    workflow_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), nullable=False
    )
    workflow_version: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class Step(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """Ordered execution step belonging to one run and tenant."""

    __tablename__ = "steps"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'running', 'completed', 'failed', 'skipped')",
            name="status",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "run_id"],
            ["runs.tenant_id", "runs.id"],
            name="fk_steps_tenant_run",
            ondelete="RESTRICT",
        ),
        UniqueConstraint("run_id", "sequence", name="uq_steps_run_sequence"),
        UniqueConstraint(
            "tenant_id",
            "run_id",
            "id",
            name="uq_steps_tenant_run_id",
        ),
    )

    tenant_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="RESTRICT"),
        nullable=False,
    )
    run_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), nullable=False
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
