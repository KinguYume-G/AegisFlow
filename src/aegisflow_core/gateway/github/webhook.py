"""Authenticated GitHub repository-dispatch webhook boundary."""

import asyncio
from collections import OrderedDict
from collections.abc import Callable
from enum import StrEnum
import hashlib
import hmac
import time
from typing import Any, Protocol

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from aegisflow_core.control_plane.bootstrap import get_or_create_bootstrap_tenant
from aegisflow_core.control_plane.domain import AuditEvent
from aegisflow_core.settings import Settings


class WebhookRejectionReason(StrEnum):
    """Stable public rejection classes without sensitive detail."""

    INVALID_SIGNATURE = "invalid_signature"
    SCHEMA_REJECTED = "schema_rejected"
    DUPLICATE_DELIVERY = "duplicate_delivery"


class WebhookVerificationResult(BaseModel):
    """Pure signature and payload validation result."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    accepted: bool
    delivery_id: str
    event: str | None
    installation_id: str | None = None
    repository: str | None = None
    rejection_reason: WebhookRejectionReason | None
    payload: dict[str, Any] | None = Field(default=None, exclude=True)


class _Installation(BaseModel):
    model_config = ConfigDict(extra="ignore", frozen=True)
    id: int


class _Repository(BaseModel):
    model_config = ConfigDict(extra="ignore", frozen=True)
    full_name: str = Field(min_length=3, max_length=300, pattern=r"^[^/]+/[^/]+$")


class _RepositoryDispatch(BaseModel):
    model_config = ConfigDict(extra="ignore", frozen=True)
    action: str = Field(min_length=1, max_length=100)
    installation: _Installation
    repository: _Repository
    client_payload: dict[str, Any] = Field(default_factory=dict)


def verify_webhook(
    *,
    raw_body: bytes,
    signature_header: str | None,
    event_header: str | None,
    delivery_id_header: str | None,
    webhook_secret: str,
    allowed_events: frozenset[str],
) -> WebhookVerificationResult:
    """Verify signature first, then the event header and payload schema."""
    delivery_id = delivery_id_header or ""
    expected = "sha256=" + hmac.new(
        webhook_secret.encode("utf-8"), raw_body, hashlib.sha256
    ).hexdigest()
    supplied = signature_header or ""
    if not hmac.compare_digest(expected, supplied):
        return WebhookVerificationResult(
            accepted=False,
            delivery_id=delivery_id,
            event=event_header,
            rejection_reason=WebhookRejectionReason.INVALID_SIGNATURE,
        )

    if not delivery_id or event_header not in allowed_events:
        return _schema_rejection(delivery_id, event_header)
    try:
        parsed = _RepositoryDispatch.model_validate_json(raw_body)
    except ValidationError:
        return _schema_rejection(delivery_id, event_header)

    return WebhookVerificationResult(
        accepted=True,
        delivery_id=delivery_id,
        event=event_header,
        installation_id=str(parsed.installation.id),
        repository=parsed.repository.full_name,
        rejection_reason=None,
        payload=parsed.model_dump(mode="json"),
    )


def _schema_rejection(
    delivery_id: str,
    event_header: str | None,
) -> WebhookVerificationResult:
    return WebhookVerificationResult(
        accepted=False,
        delivery_id=delivery_id,
        event=event_header,
        rejection_reason=WebhookRejectionReason.SCHEMA_REJECTED,
    )


class ReplayClaim(StrEnum):
    """Result of atomically claiming a delivery within the bounded window."""

    CLAIMED = "claimed"
    DUPLICATE = "duplicate"


class ReplayGuard(Protocol):
    async def claim(self, installation_id: str, delivery_id: str) -> ReplayClaim: ...


class InMemoryReplayGuard:
    """Concurrency-safe bounded TTL guard, replaced by AF-209's Ledger."""

    def __init__(
        self,
        *,
        ttl_seconds: int = 600,
        max_entries: int = 10_000,
        monotonic: Callable[[], float] = time.monotonic,
    ) -> None:
        if ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be positive")
        if max_entries <= 0:
            raise ValueError("max_entries must be positive")
        self._ttl_seconds = ttl_seconds
        self._max_entries = max_entries
        self._monotonic = monotonic
        self._entries: OrderedDict[tuple[str, str], float] = OrderedDict()
        self._lock = asyncio.Lock()

    @property
    def entry_count(self) -> int:
        return len(self._entries)

    async def claim(self, installation_id: str, delivery_id: str) -> ReplayClaim:
        key = (installation_id, delivery_id)
        async with self._lock:
            now = self._monotonic()
            self._purge_expired(now)
            existing = self._entries.get(key)
            if existing is not None and now - existing <= self._ttl_seconds:
                return ReplayClaim.DUPLICATE
            self._entries[key] = now
            self._entries.move_to_end(key)
            while len(self._entries) > self._max_entries:
                self._entries.popitem(last=False)
            return ReplayClaim.CLAIMED

    def _purge_expired(self, now: float) -> None:
        while self._entries:
            _, inserted_at = next(iter(self._entries.items()))
            if now - inserted_at <= self._ttl_seconds:
                break
            self._entries.popitem(last=False)


class WebhookDispatcher(Protocol):
    async def dispatch(self, event: WebhookVerificationResult) -> None: ...


class NoOpWebhookDispatcher:
    """AF-201 seam that AF-209/AF-210 replace with durable dispatch."""

    async def dispatch(self, _event: WebhookVerificationResult) -> None:
        return None


router = APIRouter(prefix="/webhooks", tags=["github-webhooks"])


@router.post("/github")
async def github_webhook(request: Request) -> JSONResponse:
    """Authenticate, claim, audit, and accept one repository dispatch."""
    settings: Settings = request.app.state.settings
    if not settings.github_app_configured:
        return JSONResponse(
            status_code=503,
            content={"status": "unavailable", "reason": "github_app_not_configured"},
        )

    raw_body = await request.body()
    result = verify_webhook(
        raw_body=raw_body,
        signature_header=request.headers.get("X-Hub-Signature-256"),
        event_header=request.headers.get("X-GitHub-Event"),
        delivery_id_header=request.headers.get("X-GitHub-Delivery"),
        webhook_secret=settings.github_webhook_secret or "",
        allowed_events=frozenset({"repository_dispatch"}),
    )
    if not result.accepted:
        await _audit(request, result, decision="deny")
        status = (
            401
            if result.rejection_reason is WebhookRejectionReason.INVALID_SIGNATURE
            else 400
        )
        return _rejected(status, result.rejection_reason)

    if result.installation_id != settings.github_installation_id:
        rejected = _schema_rejection(result.delivery_id, result.event)
        await _audit(request, rejected, decision="deny")
        return _rejected(400, WebhookRejectionReason.SCHEMA_REJECTED)

    replay_guard: ReplayGuard = request.app.state.github_replay_guard
    claim = await replay_guard.claim(result.installation_id or "", result.delivery_id)
    if claim is ReplayClaim.DUPLICATE:
        duplicate = result.model_copy(
            update={
                "accepted": False,
                "rejection_reason": WebhookRejectionReason.DUPLICATE_DELIVERY,
            }
        )
        await _audit(request, duplicate, decision="deny")
        return _rejected(409, WebhookRejectionReason.DUPLICATE_DELIVERY)

    await _audit(request, result, decision="allow")
    dispatcher: WebhookDispatcher = request.app.state.github_webhook_dispatcher
    await dispatcher.dispatch(result)
    return JSONResponse(status_code=202, content={"status": "accepted"})


def _rejected(
    status_code: int,
    reason: WebhookRejectionReason | None,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "status": "rejected",
            "reason": reason.value if reason is not None else "schema_rejected",
        },
    )


async def _audit(
    request: Request,
    result: WebhookVerificationResult,
    *,
    decision: str,
) -> None:
    session_factory: async_sessionmaker[AsyncSession] = (
        request.app.state.session_factory
    )
    async with session_factory.begin() as session:
        tenant = await get_or_create_bootstrap_tenant(
            session,
            request.app.state.settings.aegisflow_bootstrap_tenant_slug,
        )
        session.add(
            AuditEvent(
                tenant_id=tenant.id,
                actor="github_webhook",
                action="verify",
                resource_type="webhook_delivery",
                resource_id=result.delivery_id or None,
                decision=decision,
                reason=(
                    result.rejection_reason.value
                    if result.rejection_reason is not None
                    else "allow"
                ),
                trace_id=None,
            )
        )
