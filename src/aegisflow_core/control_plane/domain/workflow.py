"""Immutable, versioned workflow persistence model."""

from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column

from aegisflow_core.control_plane.domain.base import (
    Base,
    CreatedAtMixin,
    UUIDPrimaryKeyMixin,
)


class Workflow(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """A single immutable workflow version."""

    __tablename__ = "workflows"
    __table_args__ = (
        CheckConstraint(
            "status IN ('active', 'superseded')",
            name="status",
        ),
        CheckConstraint("version > 0", name="version_positive"),
        UniqueConstraint(
            "tenant_id",
            "name",
            "version",
            name="uq_workflows_tenant_name_version",
        ),
        UniqueConstraint(
            "tenant_id",
            "id",
            "version",
            name="uq_workflows_tenant_id_version",
        ),
        Index(
            "uq_workflows_tenant_name_active",
            "tenant_id",
            "name",
            unique=True,
            postgresql_where=text("status = 'active'"),
        ),
    )

    tenant_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="RESTRICT"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    definition_hash: Mapped[str] = mapped_column(Text, nullable=False)
    definition: Mapped[dict[str, object] | None] = mapped_column(
        JSONB, nullable=True
    )
    status: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        server_default=text("'active'"),
    )
