"""Immutable tenant-local tool registration and disablement facts."""

from uuid import UUID

from sqlalchemy import CheckConstraint, ForeignKey, ForeignKeyConstraint, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import ARRAY, UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column

from aegisflow_core.control_plane.domain.base import Base, CreatedAtMixin, UUIDPrimaryKeyMixin


class ToolRegistration(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "tool_registrations"
    __table_args__ = (
        UniqueConstraint("tenant_id", "canonical_name", "version", name="uq_tool_registrations_tenant_name_version"),
        UniqueConstraint("tenant_id", "id", name="uq_tool_registrations_tenant_id"),
        CheckConstraint("canonical_name ~ '^[a-z][a-z0-9_]{0,127}$'", name="canonical_name"),
        CheckConstraint("owner_scope <> '' AND length(owner_scope) <= 255", name="owner_scope"),
        CheckConstraint("version <> '' AND length(version) <= 64", name="version"),
        CheckConstraint("adapter_identifier <> '' AND length(adapter_identifier) <= 255", name="adapter_identifier"),
        CheckConstraint("input_schema_hash ~ '^[0-9a-f]{64}$'", name="input_schema_hash"),
        CheckConstraint("output_schema_hash ~ '^[0-9a-f]{64}$'", name="output_schema_hash"),
        CheckConstraint("cardinality(allowed_scopes) > 0", name="allowed_scopes"),
        CheckConstraint("risk_level IN ('L1','L2','L3')", name="risk_level"),
        CheckConstraint("registered_by <> '' AND length(registered_by) <= 2304", name="registered_by"),
    )

    tenant_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False
    )
    owner_scope: Mapped[str] = mapped_column(Text, nullable=False)
    canonical_name: Mapped[str] = mapped_column(Text, nullable=False)
    version: Mapped[str] = mapped_column(Text, nullable=False)
    adapter_identifier: Mapped[str] = mapped_column(Text, nullable=False)
    input_schema_hash: Mapped[str] = mapped_column(Text, nullable=False)
    output_schema_hash: Mapped[str] = mapped_column(Text, nullable=False)
    allowed_scopes: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False)
    risk_level: Mapped[str] = mapped_column(Text, nullable=False)
    registered_by: Mapped[str] = mapped_column(Text, nullable=False)


class ToolDisablement(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "tool_disablements"

    tenant_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False
    )
    registration_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    disabled_by: Mapped[str] = mapped_column(Text, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)

    __table_args__ = (
        UniqueConstraint("tenant_id", "registration_id", name="uq_tool_disablements_registration"),
        CheckConstraint("disabled_by <> '' AND length(disabled_by) <= 2304", name="disabled_by"),
        CheckConstraint("reason <> '' AND length(reason) <= 4096", name="reason"),
        ForeignKeyConstraint(
            ["tenant_id", "registration_id"],
            ["tool_registrations.tenant_id", "tool_registrations.id"],
            name="fk_tool_disablements_tenant_registration",
            ondelete="RESTRICT",
        ),
    )
