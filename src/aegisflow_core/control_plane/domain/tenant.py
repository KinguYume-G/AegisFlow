"""Tenant persistence model."""

from sqlalchemy import Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from aegisflow_core.control_plane.domain.base import (
    Base,
    CreatedAtMixin,
    UUIDPrimaryKeyMixin,
)


class Tenant(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """Root ownership boundary for tenant-scoped business facts."""

    __tablename__ = "tenants"
    __table_args__ = (UniqueConstraint("slug", name="uq_tenants_slug"),)

    slug: Mapped[str] = mapped_column(Text, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
