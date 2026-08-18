"""Opaque Console sessions preserve OIDC identity and database authorization."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest

from aegisflow_core.control_plane.identity import Principal, VerifiedIdentity
from aegisflow_core.control_plane.identity.sessions import (
    ConsoleSessionManager,
    ConsoleSessionRecord,
    SessionAuthenticationError,
    SessionAuthorizationError,
)


NOW = datetime(2026, 8, 18, 5, 0, tzinfo=timezone.utc)
RAW_TOKEN = "afs_cs_" + "A" * 43


class MemorySessionRepository:
    def __init__(self, *, member: bool = True) -> None:
        self.member = member
        self.records: dict[str, ConsoleSessionRecord] = {}
        self.created: list[ConsoleSessionRecord] = []

    async def has_active_membership(self, principal: Principal) -> bool:
        return self.member

    async def create(self, record: ConsoleSessionRecord) -> None:
        self.records[record.token_digest] = record
        self.created.append(record)

    async def get(self, token_digest: str) -> ConsoleSessionRecord | None:
        return self.records.get(token_digest)

    async def revoke(self, token_digest: str, revoked_at: datetime) -> bool:
        record = self.records.get(token_digest)
        if record is None or record.revoked_at is not None:
            return False
        self.records[token_digest] = replace(record, revoked_at=revoked_at)
        return True


def manager(
    repository: MemorySessionRepository,
    *,
    now: datetime = NOW,
    ttl_seconds: int = 900,
) -> ConsoleSessionManager:
    return ConsoleSessionManager(
        repository,
        clock=lambda: now,
        token_factory=lambda: RAW_TOKEN,
        max_lifetime_seconds=ttl_seconds,
    )


@pytest.mark.anyio
async def test_create_persists_only_digest_and_bounds_expiry() -> None:
    repository = MemorySessionRepository()
    identity = VerifiedIdentity(
        Principal("https://issuer.example.test", "developer-1"),
        NOW + timedelta(hours=1),
    )

    created = await manager(repository).create(identity)

    assert created.token == RAW_TOKEN
    assert created.expires_at == NOW + timedelta(minutes=15)
    assert len(repository.created) == 1
    record = repository.created[0]
    assert record.issuer == identity.principal.issuer
    assert record.subject == identity.principal.subject
    assert record.expires_at == created.expires_at
    assert record.created_at == NOW
    assert record.revoked_at is None
    assert record.token_digest != RAW_TOKEN
    assert len(record.token_digest) == 64
    assert RAW_TOKEN not in repr(record)


@pytest.mark.anyio
async def test_create_uses_provider_expiry_when_shorter() -> None:
    repository = MemorySessionRepository()
    provider_expiry = NOW + timedelta(minutes=3)

    created = await manager(repository).create(
        VerifiedIdentity(
            Principal("https://issuer.example.test", "developer-1"),
            provider_expiry,
        )
    )

    assert created.expires_at == provider_expiry


@pytest.mark.anyio
async def test_create_requires_active_membership_and_live_identity() -> None:
    identity = VerifiedIdentity(
        Principal("https://issuer.example.test", "unknown-user"),
        NOW + timedelta(minutes=5),
    )
    with pytest.raises(SessionAuthorizationError, match="session_membership_required"):
        await manager(MemorySessionRepository(member=False)).create(identity)

    expired = VerifiedIdentity(identity.principal, NOW)
    with pytest.raises(SessionAuthenticationError, match="oidc_identity_expired"):
        await manager(MemorySessionRepository()).create(expired)


@pytest.mark.anyio
async def test_authenticate_reconstructs_principal_without_provider_claims() -> None:
    repository = MemorySessionRepository()
    created = await manager(repository).create(
        VerifiedIdentity(
            Principal("https://issuer.example.test", "reviewer-1"),
            NOW + timedelta(minutes=10),
        )
    )

    principal = await manager(repository).authenticate(created.token)

    assert principal == Principal("https://issuer.example.test", "reviewer-1")


@pytest.mark.anyio
async def test_missing_malformed_expired_and_revoked_sessions_fail_closed() -> None:
    repository = MemorySessionRepository()
    active_manager = manager(repository)
    created = await active_manager.create(
        VerifiedIdentity(
            Principal("https://issuer.example.test", "developer-1"),
            NOW + timedelta(minutes=5),
        )
    )

    for raw in ("", "not-a-session", "afs_cs_short", "afs_cs_" + "!" * 43):
        with pytest.raises(SessionAuthenticationError, match="invalid_session"):
            await active_manager.authenticate(raw)

    with pytest.raises(SessionAuthenticationError, match="invalid_session"):
        await active_manager.authenticate("afs_cs_" + "B" * 43)

    with pytest.raises(SessionAuthenticationError, match="session_expired"):
        await manager(repository, now=NOW + timedelta(minutes=6)).authenticate(
            created.token
        )

    assert await active_manager.revoke(created.token) is True
    assert await active_manager.revoke(created.token) is False
    with pytest.raises(SessionAuthenticationError, match="session_revoked"):
        await active_manager.authenticate(created.token)
