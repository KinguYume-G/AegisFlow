"""Immutable prompt-version and run-binding persistence facts."""

from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column

from aegisflow_core.control_plane.domain.base import (
    Base,
    CreatedAtMixin,
    UUIDPrimaryKeyMixin,
)


class PromptSeries(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """Mutable allocator for one tenant-owned immutable prompt history."""

    __tablename__ = "prompt_series"
    __table_args__ = (
        UniqueConstraint("tenant_id", "name", name="uq_prompt_series_tenant_name"),
        CheckConstraint("latest_version >= 0", name="latest_version_non_negative"),
    )

    tenant_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="RESTRICT"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    latest_version: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )


class PromptVersion(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """One immutable prompt template version."""

    __tablename__ = "prompt_versions"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "name", "version", name="uq_prompt_versions_tenant_name_version"
        ),
        UniqueConstraint("tenant_id", "id", name="uq_prompt_versions_tenant_id"),
        CheckConstraint("version > 0", name="version_positive"),
        CheckConstraint(
            "content_hash ~ '^[0-9a-f]{64}$'", name="content_hash_sha256"
        ),
        ForeignKeyConstraint(
            ["tenant_id", "source_version_id"],
            ["prompt_versions.tenant_id", "prompt_versions.id"],
            name="fk_prompt_versions_tenant_source",
            ondelete="RESTRICT",
        ),
    )

    tenant_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="RESTRICT"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    template: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(Text, nullable=False)
    created_by: Mapped[str] = mapped_column(Text, nullable=False)
    source_version_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True), nullable=True
    )


class RunPromptVersion(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """Immutable binding between a Run and one named prompt version."""

    __tablename__ = "run_prompt_versions"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "run_id", "prompt_name", name="uq_run_prompt_versions_binding"
        ),
        ForeignKeyConstraint(
            ["tenant_id", "run_id"],
            ["runs.tenant_id", "runs.id"],
            name="fk_run_prompt_versions_tenant_run",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "prompt_version_id"],
            ["prompt_versions.tenant_id", "prompt_versions.id"],
            name="fk_run_prompt_versions_tenant_prompt",
            ondelete="RESTRICT",
        ),
    )

    tenant_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="RESTRICT"),
        nullable=False,
    )
    run_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    prompt_name: Mapped[str] = mapped_column(Text, nullable=False)
    prompt_version_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), nullable=False
    )
    bound_by: Mapped[str] = mapped_column(Text, nullable=False)
