"""Provider-neutral, opaque and revocable Console session domain service."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from re import compile as compile_pattern
from secrets import token_urlsafe
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aegisflow_core.control_plane.domain import (
    AuditEvent,
    ConsoleSession,
    TenantMembership,
)
from aegisflow_core.control_plane.identity.oidc import Principal, VerifiedIdentity

_SESSION_PATTERN = compile_pattern(r"^afs_cs_[A-Za-z0-9_-]{43}$")


class SessionAuthenticationError(PermissionError):
    """A stable rejection that never contains raw credential material."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


class SessionAuthorizationError(PermissionError):
    """A verified identity that cannot enter an AegisFlow tenant."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


@dataclass(frozen=True, slots=True)
class ConsoleSessionRecord:
    token_digest: str
    issuer: str
    subject: str
    created_at: datetime
    expires_at: datetime
    revoked_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class CreatedConsoleSession:
    token: str
    expires_at: datetime
    principal: Principal


class ConsoleSessionRepository(Protocol):
    async def has_active_membership(self, principal: Principal) -> bool: ...

    async def create(self, record: ConsoleSessionRecord) -> None: ...

    async def get(self, token_digest: str) -> ConsoleSessionRecord | None: ...

    async def revoke(self, token_digest: str, revoked_at: datetime) -> bool: ...


def _default_clock() -> datetime:
    return datetime.now(timezone.utc)


def _default_token_factory() -> str:
    return f"afs_cs_{token_urlsafe(32)}"


class ConsoleSessionManager:
    """Create and verify sessions without persisting their raw bearer value."""

    def __init__(
        self,
        repository: ConsoleSessionRepository,
        *,
        clock: Callable[[], datetime] = _default_clock,
        token_factory: Callable[[], str] = _default_token_factory,
        max_lifetime_seconds: int = 900,
    ) -> None:
        if not 60 <= max_lifetime_seconds <= 3600:
            raise ValueError("session lifetime must be between 60 and 3600 seconds")
        self._repository = repository
        self._clock = clock
        self._token_factory = token_factory
        self._max_lifetime = timedelta(seconds=max_lifetime_seconds)

    async def create(self, identity: VerifiedIdentity) -> CreatedConsoleSession:
        now = self._aware_now()
        if identity.expires_at <= now:
            raise SessionAuthenticationError("oidc_identity_expired")
        if not await self._repository.has_active_membership(identity.principal):
            raise SessionAuthorizationError("session_membership_required")
        token = self._token_factory()
        token_digest = self._digest(token)
        expires_at = min(identity.expires_at, now + self._max_lifetime)
        await self._repository.create(
            ConsoleSessionRecord(
                token_digest=token_digest,
                issuer=identity.principal.issuer,
                subject=identity.principal.subject,
                created_at=now,
                expires_at=expires_at,
            )
        )
        return CreatedConsoleSession(token, expires_at, identity.principal)

    async def authenticate(self, token: str) -> Principal:
        record = await self._repository.get(self._digest(token))
        if record is None:
            raise SessionAuthenticationError("invalid_session")
        if record.revoked_at is not None:
            raise SessionAuthenticationError("session_revoked")
        if record.expires_at <= self._aware_now():
            raise SessionAuthenticationError("session_expired")
        return Principal(record.issuer, record.subject)

    async def revoke(self, token: str) -> bool:
        return await self._repository.revoke(self._digest(token), self._aware_now())

    def _aware_now(self) -> datetime:
        now = self._clock()
        if now.tzinfo is None or now.utcoffset() is None:
            raise ValueError("session clock must be timezone-aware")
        return now

    @staticmethod
    def _digest(token: str) -> str:
        return digest_session_token(token)


def digest_session_token(token: str) -> str:
    if not isinstance(token, str) or _SESSION_PATTERN.fullmatch(token) is None:
        raise SessionAuthenticationError("invalid_session")
    return sha256(token.encode("ascii")).hexdigest()


class PostgresConsoleSessionRepository:
    """SQLAlchemy adapter for session facts within the caller transaction."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def has_active_membership(self, principal: Principal) -> bool:
        membership = await self._session.scalar(
            select(TenantMembership.id)
            .where(
                TenantMembership.issuer == principal.issuer,
                TenantMembership.subject == principal.subject,
            )
            .limit(1)
        )
        return membership is not None

    async def create(self, record: ConsoleSessionRecord) -> None:
        row = ConsoleSession(
            token_digest=record.token_digest,
            issuer=record.issuer,
            subject=record.subject,
            created_at=record.created_at,
            expires_at=record.expires_at,
            revoked_at=record.revoked_at,
        )
        self._session.add(row)
        await self._session.flush()
        await self._record_audit(row, "auth.session.created")

    async def get(self, token_digest: str) -> ConsoleSessionRecord | None:
        row = await self._session.scalar(
            select(ConsoleSession).where(ConsoleSession.token_digest == token_digest)
        )
        return self._record(row) if row is not None else None

    async def revoke(self, token_digest: str, revoked_at: datetime) -> bool:
        row = await self._session.scalar(
            select(ConsoleSession)
            .where(ConsoleSession.token_digest == token_digest)
            .with_for_update()
        )
        if row is None or row.revoked_at is not None:
            return False
        row.revoked_at = revoked_at
        await self._session.flush()
        await self._record_audit(row, "auth.session.revoked")
        return True

    @staticmethod
    def digest_for_lookup(token: str) -> str:
        return digest_session_token(token)

    @staticmethod
    def _record(row: ConsoleSession) -> ConsoleSessionRecord:
        return ConsoleSessionRecord(
            token_digest=row.token_digest,
            issuer=row.issuer,
            subject=row.subject,
            created_at=row.created_at,
            expires_at=row.expires_at,
            revoked_at=row.revoked_at,
        )

    async def _record_audit(self, row: ConsoleSession, action: str) -> None:
        tenant_ids = list(
            await self._session.scalars(
                select(TenantMembership.tenant_id).where(
                    TenantMembership.issuer == row.issuer,
                    TenantMembership.subject == row.subject,
                )
            )
        )
        actor = Principal(row.issuer, row.subject).actor_reference
        for tenant_id in tenant_ids:
            self._session.add(
                AuditEvent(
                    tenant_id=tenant_id,
                    actor=actor,
                    action=action,
                    resource_type="console_session",
                    resource_id=str(row.id),
                    decision="allow",
                    reason=None,
                )
            )
        await self._session.flush()
