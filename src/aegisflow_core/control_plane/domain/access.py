"""Tenant membership and revocable fixed-role assignment facts."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, ForeignKeyConstraint, Index, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column

from aegisflow_core.control_plane.domain.base import Base, CreatedAtMixin, UUIDPrimaryKeyMixin

_ROLE_VALUES = "'Admin','Developer','Reviewer','Security','DevOps','Viewer'"


class TenantMembership(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "tenant_memberships"
    __table_args__ = (
        CheckConstraint("issuer <> '' AND length(issuer) <= 2048", name="issuer_bounded"),
        CheckConstraint("subject <> '' AND length(subject) <= 255", name="subject_bounded"),
        UniqueConstraint("tenant_id", "issuer", "subject", name="uq_tenant_memberships_principal"),
        UniqueConstraint("tenant_id", "id", name="uq_tenant_memberships_tenant_id"),
    )

    tenant_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False)
    issuer: Mapped[str] = mapped_column(Text, nullable=False)
    subject: Mapped[str] = mapped_column(Text, nullable=False)


class RoleAssignment(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "role_assignments"
    __table_args__ = (
        CheckConstraint(f"role IN ({_ROLE_VALUES})", name="role"),
        CheckConstraint("assigned_by <> '' AND length(assigned_by) <= 2304", name="actor_bounded"),
        CheckConstraint(
            "(revoked_at IS NULL AND revoked_by IS NULL) OR (revoked_at IS NOT NULL AND revoked_by IS NOT NULL)",
            name="revocation_pair",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "membership_id"],
            ["tenant_memberships.tenant_id", "tenant_memberships.id"],
            name="fk_role_assignments_tenant_membership",
            ondelete="RESTRICT",
        ),
        Index(
            "uq_role_assignments_active_role",
            "tenant_id",
            "membership_id",
            "role",
            unique=True,
            postgresql_where=text("revoked_at IS NULL"),
        ),
    )

    tenant_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False)
    membership_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    role: Mapped[str] = mapped_column(Text, nullable=False)
    assigned_by: Mapped[str] = mapped_column(Text, nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_by: Mapped[str | None] = mapped_column(Text, nullable=True)
