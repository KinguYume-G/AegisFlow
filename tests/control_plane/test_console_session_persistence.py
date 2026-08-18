"""PostgreSQL persists only revocable opaque Console session facts."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import os
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from aegisflow_core.control_plane.domain import (
    AuditEvent,
    ConsoleSession,
    Tenant,
    TenantMembership,
)
from aegisflow_core.control_plane.identity import Principal, VerifiedIdentity
from aegisflow_core.control_plane.identity.sessions import (
    ConsoleSessionManager,
    PostgresConsoleSessionRepository,
    SessionAuthenticationError,
)


NOW = datetime(2026, 8, 18, 5, 30, tzinfo=timezone.utc)
RAW_TOKEN = "afs_cs_" + "C" * 43


def test_console_session_model_has_no_raw_token_or_provider_token_columns() -> None:
    columns = set(ConsoleSession.__table__.columns.keys())

    assert columns == {
        "id",
        "token_digest",
        "issuer",
        "subject",
        "created_at",
        "expires_at",
        "revoked_at",
    }
    assert ConsoleSession.__table__.c.token_digest.unique is True
    assert "token" not in columns
    assert "access_token" not in columns
    assert "refresh_token" not in columns


@pytest.mark.database
@pytest.mark.anyio
async def test_postgres_session_repository_requires_membership_and_revokes() -> None:
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        pytest.skip("DATABASE_URL is required")
    engine = create_async_engine(database_url)
    async with engine.connect() as connection:
        transaction = await connection.begin()
        sessions = async_sessionmaker(
            connection,
            expire_on_commit=False,
            join_transaction_mode="create_savepoint",
        )
        try:
            async with sessions.begin() as session:
                principal = Principal("https://issuer.example.test", f"user-{uuid4()}")
                tenant = Tenant(slug=f"session-{uuid4()}", name="Session tenant")
                session.add(tenant)
                await session.flush()
                session.add(
                    TenantMembership(
                        tenant_id=tenant.id,
                        issuer=principal.issuer,
                        subject=principal.subject,
                    )
                )
                await session.flush()

                repository = PostgresConsoleSessionRepository(session)
                manager = ConsoleSessionManager(
                    repository,
                    clock=lambda: NOW,
                    token_factory=lambda: RAW_TOKEN,
                    max_lifetime_seconds=900,
                )
                created = await manager.create(
                    VerifiedIdentity(principal, NOW + timedelta(minutes=10))
                )
                persisted = await session.scalar(
                    select(ConsoleSession).where(
                        ConsoleSession.token_digest
                        == repository.digest_for_lookup(created.token)
                    )
                )

                assert persisted is not None
                assert persisted.issuer == principal.issuer
                assert persisted.subject == principal.subject
                assert persisted.expires_at == NOW + timedelta(minutes=10)
                assert RAW_TOKEN not in repr(persisted)
                assert await manager.authenticate(created.token) == principal
                assert await manager.revoke(created.token) is True
                assert await manager.revoke(created.token) is False
                with pytest.raises(SessionAuthenticationError, match="session_revoked"):
                    await manager.authenticate(created.token)
                audit_actions = list(
                    await session.scalars(
                        select(AuditEvent.action)
                        .where(
                            AuditEvent.tenant_id == tenant.id,
                            AuditEvent.actor == principal.actor_reference,
                            AuditEvent.action.in_(
                                ["auth.session.created", "auth.session.revoked"]
                            ),
                        )
                        .order_by(AuditEvent.created_at)
                    )
                )
                assert audit_actions == [
                    "auth.session.created",
                    "auth.session.revoked",
                ]
        finally:
            await transaction.rollback()
    await engine.dispose()
