"""Human approval persistence model."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
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


class Approval(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """Run- or step-level human decision fact."""

    __tablename__ = "approvals"
    __table_args__ = (
        CheckConstraint(
            "decision IN ('pending', 'approved', 'rejected')",
            name="decision",
        ),
        CheckConstraint(
            "(action_preview IS NULL AND action_digest IS NULL) OR "
            "(action_preview IS NOT NULL AND action_digest ~ '^[0-9a-f]{64}$')",
            name="action_pair",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "run_id"],
            ["runs.tenant_id", "runs.id"],
            name="fk_approvals_tenant_run",
            ondelete="RESTRICT",
        ),
        UniqueConstraint(
            "tenant_id", "run_id", "step_id", name="uq_approvals_tenant_run_step"
        ),
        ForeignKeyConstraint(
            ["tenant_id", "run_id", "step_id"],
            ["steps.tenant_id", "steps.run_id", "steps.id"],
            name="fk_approvals_tenant_run_step",
            ondelete="RESTRICT",
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
    step_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True), nullable=True
    )
    decision: Mapped[str] = mapped_column(Text, nullable=False)
    decided_by: Mapped[str | None] = mapped_column(Text, nullable=True)
    decided_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    action_preview: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
    action_digest: Mapped[str | None] = mapped_column(Text, nullable=True)
