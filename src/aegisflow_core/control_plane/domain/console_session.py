"""Revocable opaque Console session facts; raw credentials are never persisted."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Index, Text
from sqlalchemy.orm import Mapped, mapped_column

from aegisflow_core.control_plane.domain.base import (
    Base,
    CreatedAtMixin,
    UUIDPrimaryKeyMixin,
)


class ConsoleSession(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "console_sessions"
    __table_args__ = (
        CheckConstraint(
            "token_digest ~ '^[0-9a-f]{64}$'", name="token_digest_format"
        ),
        CheckConstraint(
            "issuer <> '' AND length(issuer) <= 2048", name="issuer_bounded"
        ),
        CheckConstraint(
            "subject <> '' AND length(subject) <= 255", name="subject_bounded"
        ),
        CheckConstraint("expires_at > created_at", name="expiry_after_creation"),
        CheckConstraint(
            "revoked_at IS NULL OR revoked_at >= created_at",
            name="revocation_after_creation",
        ),
        Index("ix_console_sessions_principal", "issuer", "subject"),
        Index("ix_console_sessions_expires_at", "expires_at"),
    )

    token_digest: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    issuer: Mapped[str] = mapped_column(Text, nullable=False)
    subject: Mapped[str] = mapped_column(Text, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
